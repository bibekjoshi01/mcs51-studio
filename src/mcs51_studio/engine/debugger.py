"""Execution explanations, tracked call frames, watches, and temporary stops."""

import re
from dataclasses import dataclass

from ..resources import ISA
from .cpu import BITS, SFR


@dataclass(frozen=True)
class Watch:
    expression: str
    break_on_change: bool = False

    def read(self, cpu):
        text = self.expression.strip().upper()
        if text in ("A", "ACC"):
            return cpu.a
        if text == "PC":
            return cpu.pc
        if text == "DPTR":
            return cpu.dptr
        if re.fullmatch(r"R[0-7]", text):
            return cpu.reg(int(text[1]))
        if text in SFR:
            return cpu.read(SFR[text], latch=True)
        if text in BITS:
            return cpu.bit(BITS[text])
        match = re.fullmatch(r"(RAM|SFR|XDATA|CODE|BIT)\[([0-9A-F]{1,4})\]", text)
        if not match:
            raise ValueError(
                "Use a register, flag, or RAM[30], SFR[90], XDATA[1234], CODE[0100], BIT[90]. Addresses are hexadecimal."
            )
        space, address = match[1], int(match[2], 16)
        if space == "RAM":
            return cpu.read_indirect(address)
        if space == "SFR":
            if address not in SFR.values():
                raise ValueError("Choose an implemented Classic 8051 SFR.")
            return cpu.read(address, latch=True)
        if space == "BIT":
            return cpu.bit(address)
        return (cpu.xram if space == "XDATA" else cpu.code)[address]


def registers(cpu):
    return {
        "PC": cpu.pc,
        "DPTR": cpu.dptr,
        **{n: cpu.ram[a] for n, a in SFR.items()},
        **{f"R{i}": cpu.reg(i) for i in range(8)},
    }


class Debugger:
    def __init__(self, cpu):
        self.cpu = cpu
        self.watches = []
        self.reset()

    def reset(self):
        self.frames = []
        self.last = None
        self.changed = set()
        self.target = None
        self.reason = ""
        self.frame_warning = ""
        self.serial = 0
        self.cpu.on_frame = self.frame_event
        self.cpu.on_read = self.read_event
        self.reads = {}

    def read_event(self, space, address, value):
        self.reads.setdefault((space, address), value)

    def frame_event(self, kind, return_pc, sp):
        if kind in ("call", "interrupt"):
            self.serial += 1
            self.frames.append(
                {"id": self.serial, "kind": kind, "return": return_pc, "sp": sp}
            )
        elif self.frames:
            frame = self.frames[-1]
            if (
                frame["return"] == return_pc
                and frame["sp"] - 2 == sp
                and (kind == "reti") == (frame["kind"] == "interrupt")
            ):
                self.frames.pop()
            else:
                self.frames.clear()
                self.target = None
                self.frame_warning = "Stack return does not match tracked frames. Check SP, PUSH/POP balance, and RET/RETI."

    def add_watch(self, expression, stop=False):
        watch = Watch(expression.strip().upper(), stop)
        watch.read(self.cpu)
        if len(self.watches) >= 64:
            raise ValueError("At most 64 watches are supported.")
        if any(w.expression == watch.expression for w in self.watches):
            raise ValueError("That watch already exists.")
        self.watches.append(watch)
        return watch

    def plan(self, action, cursor=None):
        cpu = self.cpu
        self.reason = ""
        if action == "cursor":
            if cursor is None or not 0 <= cursor <= 65535:
                raise ValueError("Place the cursor on an assembled instruction.")
            if cursor == cpu.pc:
                self.reason = "Already at cursor"
                return False
            self.target = {"address": cursor, "depth": None, "budget": 1_000_000}
        elif action == "out":
            if not self.frames:
                raise ValueError(
                    "No tracked call or interrupt frame. Step Out is unavailable at top level."
                )
            self.target = {
                "address": self.frames[-1]["return"],
                "depth": len(self.frames) - 1,
                "budget": 1_000_000,
            }
        elif action == "over":
            op = cpu.code[cpu.pc]
            if op != 0x12 and op & 31 != 17:
                return False
            self.target = {
                "address": (cpu.pc + ISA[op]["size"]) & 65535,
                "depth": len(self.frames),
                "budget": 1_000_000,
            }
        return True

    def step(self, board, source=""):
        cpu = self.cpu
        before, ram, start_cycles = registers(cpu), bytes(cpu.ram), cpu.cycles
        pc, op = cpu.pc, cpu.code[cpu.pc]
        encoded = bytes(cpu.code[(pc + i) & 65535] for i in range(ISA[op]["size"]))
        values = [watch.read(cpu) for watch in self.watches]
        xaddress = (
            cpu.dptr
            if op in (0xE0, 0xF0)
            else (cpu.ram[0xA0] << 8 | cpu.reg(op & 1))
            if op in (0xE2, 0xE3, 0xF2, 0xF3)
            else None
        )
        xbefore = cpu.xram[xaddress] if xaddress is not None else None
        self.reads = {}
        previous_warning = self.frame_warning
        cpu.step()
        board.update()
        after = registers(cpu)
        self.changed = {name for name, value in before.items() if value != after[name]}
        changes = [
            (address, value, cpu.ram[address])
            for address, value in enumerate(ram)
            if value != cpu.ram[address]
        ]
        self.last = {
            "pc": pc,
            "source": source or ISA[op]["mnemonic"].strip(),
            "bytes": encoded.hex(" ").upper(),
            "before": before,
            "after": after,
            "changes": changes,
            "reads": dict(self.reads),
            "cycles": cpu.cycles - start_cycles,
            "instruction_cycles": ISA[op]["cycles"],
            "flags_before": ram[0xD0],
            "flags_after": cpu.ram[0xD0],
            "xdata": None
            if xaddress is None
            else (xaddress, xbefore, cpu.xram[xaddress]),
        }
        self.reason = (
            self.frame_warning if self.frame_warning != previous_warning else ""
        )
        for watch, previous in zip(self.watches, values):
            current = watch.read(cpu)
            if watch.break_on_change and current != previous:
                self.reason = (
                    f"{watch.expression} changed: {previous:02X} → {current:02X}"
                )
                break
        if self.target:
            self.target["budget"] -= 1
            if cpu.pc == self.target["address"] and (
                self.target["depth"] is None or len(self.frames) <= self.target["depth"]
            ):
                self.reason = self.reason or f"Target reached at {cpu.pc:04X}"
            elif self.target["budget"] <= 0:
                self.reason = (
                    self.reason
                    or "Temporary run stopped after 1,000,000 instructions; target was not reached."
                )
        if self.reason:
            self.target = None
        return op

    def explanation(self):
        if not self.last:
            return "Step an instruction to inspect its inputs, result, flags, and cycle cost."
        r = self.last
        reads = (
            ", ".join(
                f"{space}[{address:04X}]={value:02X}"
                for (space, address), value in r["reads"].items()
            )
            or "No data-memory reads"
        )
        result = (
            ", ".join(
                f"{name}: {r['before'][name]:02X} → {r['after'][name]:02X}"
                for name in sorted(self.changed)
            )
            or "No register changes"
        )
        flags = " · ".join(
            f"{name} {r['flags_before'] >> bit & 1}→{r['flags_after'] >> bit & 1}"
            for name, bit in [("CY", 7), ("AC", 6), ("OV", 2), ("P", 0)]
        )
        writes = (
            ", ".join(
                f"{'RAM' if addr < 128 else 'SFR'}[{addr:02X}] {old:02X}→{new:02X}"
                for addr, old, new in r["changes"]
            )
            or "None"
        )
        if r["xdata"]:
            addr, old, new = r["xdata"]
            writes += f"; XDATA[{addr:04X}] {old:02X}→{new:02X}"
        return f"{r['pc']:04X}  {r['source']}\nBytes: {r['bytes']}\n\nInputs: {reads}\n\nResult: {result}\n\nFlags: {flags}\n\nState Changes: {writes}\n\nCost: {r['instruction_cycles']} instruction machine cycles + {r['cycles'] - r['instruction_cycles']} interrupt-entry cycles = {r['cycles']} µs.\nState changes include timers and peripherals during this step."
