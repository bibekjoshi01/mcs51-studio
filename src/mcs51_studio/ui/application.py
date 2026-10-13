"""MCS51 Studio desktop editor, debugger, and virtual board views."""

import json
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from ..config import settings_path
from ..engine.assembler import AssemblyError, assemble, export_hex, import_hex
from ..engine.cpu import CPU, ISA, SFR
from ..hardware.board import DEFAULT_MAPPING, Board, pin
from ..metadata import APP_NAME, VERSION
from ..resources import LED_COUNTER
from .board_view import BoardView
from .icon import apply_icon, prepare_process_identity
from .theme import apply_theme
from .workspace import WorkspaceView


class App(WorkspaceView, BoardView):
    def __init__(self, root):
        self.root = root
        apply_icon(root)
        root.title(f"{APP_NAME} — 8051 Workbench")
        width = max(800, min(1370, root.winfo_screenwidth() - 80))
        height = max(600, min(900, root.winfo_screenheight() - 100))
        root.geometry(f"{width}x{height}")
        root.minsize(960, 640)
        self.ui_font, self.mono_font = apply_theme(root)
        self.cpu = CPU()
        self.board = Board(self.cpu)
        self.program = None
        self.running = False
        self.run_after = None
        self.breakpoints = set()
        self.path = None
        self.dirty = False
        self.uart_position = 0
        self.saved_source = LED_COUNTER
        self.document_modified = False
        self.layout_settings = {}
        self.settings_path = settings_path()
        self.load_settings()
        self.status = tk.StringVar(value="Ready · assemble the example to begin")
        self.speed = tk.StringVar(value="1000")
        self.reg_vars = {}
        self.port_labels = {}
        self.enabled_vars = {}
        self.build_workspace()
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.bind_shortcuts()
        self.editor.insert("1.0", LED_COUNTER)
        self.editor.edit_modified(False)
        self.editor_view.highlight()
        self.refresh()
        self.root.after_idle(self.restore_layout)

    def pause_execution(self):
        self.running = False
        if self.run_after is not None:
            self.root.after_cancel(self.run_after)
            self.run_after = None

    def edited(self, event=None):
        self.dirty = True
        self.pause_execution()
        self.document_modified = self.editor.get("1.0", "end-1c") != self.saved_source
        self.update_document_title()
        self.run_button.configure(text="Run  F5")
        self.machine_state.set("EDITING")
        self.editor.tag_remove("pc", "1.0", "end")
        self.editor_view.execution_line = None
        self.editor_view.breakpoint_lines.clear()
        self.status.set("Source changed · assemble before execution")

    def assemble(self):
        self.pause_execution()
        try:
            self.program = assemble(self.editor.get("1.0", "end-1c"))
        except AssemblyError as e:
            self.log_activity(f"Assembly failed: {e}")
            self.show_bottom("Activity")
            messagebox.showerror("Assembly error", str(e))
            return False
        self.reset()
        self.dirty = False
        self.populate_listing()
        self.refresh()
        self.log_activity(f"Assembled {len(self.program.used)} bytes successfully.")
        self.status.set(
            f"Assembled {len(self.program.used)} bytes · {len(self.program.locations)} source statements"
        )
        return True

    def reset(self):
        self.pause_execution()
        mapping = self.board.mapping
        enabled = self.board.enabled.copy()
        self.cpu.reset()
        self.board = Board(self.cpu, mapping)
        self.board.enabled.update(enabled)
        if self.program:
            self.cpu.code[:] = self.program.code
        self.uart_position = 0
        self.board.switches = [v.get() for v in self.switch_vars]
        self.board.update()
        self.refresh()
        self.status.set("Reset · PC 0000")

    def step_once(self):
        op = self.cpu.step()
        self.board.update()
        return op

    def step(self):
        self.pause_execution()
        if self.dirty or not self.program:
            if not self.assemble():
                return
        try:
            op = self.step_once()
            self.status.set(
                f"Stepped opcode {op:02X} · {self.cpu.instructions:,} instructions · {self.cpu.cycles:,} machine cycles"
            )
        except Exception as e:
            messagebox.showerror("Execution stopped", str(e))
        self.refresh()

    def toggle_run(self):
        if self.running:
            self.pause_execution()
            self.status.set("Paused")
            self.refresh()
            return
        if self.dirty or not self.program:
            if not self.assemble():
                return
        self.running = True
        self.run_batch()

    def run_batch(self):
        self.run_after = None
        if not self.running:
            return
        try:
            deadline = time.monotonic() + 0.025
            for _ in range(int(self.speed.get())):
                self.step_once()
                if self.cpu.pc in self.breakpoints:
                    self.pause_execution()
                    break
                if time.monotonic() > deadline:
                    break
            self.status.set(
                f"{'Running' if self.running else 'Breakpoint'} · PC {self.cpu.pc:04X} · {self.cpu.instructions:,} instructions · {self.cpu.cycles:,} machine cycles"
            )
        except Exception as e:
            self.pause_execution()
            messagebox.showerror("Execution stopped", str(e))
        self.refresh()
        if self.running:
            self.run_after = self.root.after(10, self.run_batch)

    def populate_listing(self):
        self.listing.delete(*self.listing.get_children())
        if not self.program:
            return
        entries = self.program.locations or {
            p: {
                "source": ISA[self.cpu.code[p]]["display"],
                "size": ISA[self.cpu.code[p]]["size"],
                "line": 0,
            }
            for p in sorted(self.program.used)[:2000]
        }
        for address, entry in entries.items():
            data = " ".join(
                f"{b:02X}" for b in self.cpu.code[address : address + entry["size"]]
            )
            self.listing.insert(
                "",
                "end",
                iid=str(address),
                values=(f"{address:04X}", data, entry["source"]),
            )

    def breakpoint(self, event):
        row = self.listing.identify_row(event.y)
        if row:
            address = int(row)
            if address in self.breakpoints:
                self.breakpoints.remove(address)
            else:
                self.breakpoints.add(address)
            self.refresh()

    def edit_register(self, name):
        self.pause_execution()
        try:
            value = int(self.reg_vars[name].get(), 16)
            if name == "PC":
                if not 0 <= value <= 65535:
                    raise ValueError()
                self.cpu.pc = value
            else:
                if not 0 <= value <= 255:
                    raise ValueError()
                if name.startswith("R") and name[1:].isdigit():
                    self.cpu.set_reg(int(name[1:]), value)
                else:
                    self.cpu.write(SFR[name], value)
            self.board.update()
            self.refresh()
        except ValueError:
            messagebox.showerror(
                "Invalid value", "Enter a hexadecimal value within the register range."
            )

    def edit_memory(self, event):
        if self.running:
            return
        row = self.memory.identify_row(event.y)
        col = self.memory.identify_column(event.x)
        if not row or not col or col == "#1":
            return
        address = int(row) + int(col[1:]) - 2
        value = simpledialog.askstring(
            "Edit memory",
            f"Address {address:04X}, new hexadecimal byte:",
            parent=self.root,
        )
        if value is None:
            return
        try:
            n = int(value, 16)
            if not 0 <= n <= 255:
                raise ValueError()
            if self.memory_kind.get() == "Code":
                self.cpu.code[address] = n
            else:
                self.cpu.write(address, n)
            self.board.update()
            self.refresh()
        except ValueError:
            messagebox.showerror("Invalid byte", "Use a value from 00 to FF.")

    def refresh(self):
        if not hasattr(self, "memory"):
            return
        focus = self.root.focus_get()
        for name, var in self.reg_vars.items():
            if isinstance(focus, ttk.Entry) and str(focus.cget("textvariable")) == str(
                var
            ):
                continue
            value = (
                self.cpu.pc
                if name == "PC"
                else self.cpu.reg(int(name[1:]))
                if name.startswith("R") and name[1:].isdigit()
                else self.cpu.ram[SFR[name]]
            )
            var.set(f"{value:04X}" if name == "PC" else f"{value:02X}")
        self.flags.configure(
            text="   ".join(
                f"{n}={(self.cpu.ram[0xD0] >> b) & 1}"
                for n, b in [
                    ("CY", 7),
                    ("AC", 6),
                    ("F0", 5),
                    ("RS1", 4),
                    ("RS0", 3),
                    ("OV", 2),
                    ("P", 0),
                ]
            )
        )
        opcode = self.cpu.code[self.cpu.pc]
        size = ISA[opcode]["size"]
        encoded = bytes(self.cpu.code[(self.cpu.pc + i) & 0xFFFF] for i in range(size))
        location = self.program.locations.get(self.cpu.pc) if self.program else None
        source_matches = self.program and encoded == bytes(
            self.program.code[self.cpu.pc : self.cpu.pc + size]
        )
        description = (
            location["source"].split(";", 1)[0].strip()
            if location and source_matches and not self.dirty
            else ISA[opcode]["mnemonic"].split()[0]
        )
        self.current_instruction.set(
            f"{self.cpu.pc:04X}  {encoded.hex(' ').upper()}\n{description}"
        )
        kind = self.memory_kind.get()
        try:
            start = (
                int(self.memory_start.get(), 16) & 0xFF80
                if kind == "Code"
                else 128
                if kind == "SFR"
                else 0
            )
        except ValueError:
            start = 0
        self.memory.delete(*self.memory.get_children())
        for addr in range(start, min(start + 128, 65536), 16):
            data = (
                self.cpu.code[addr : addr + 16]
                if kind == "Code"
                else self.cpu.ram[addr : addr + 16]
            )
            self.memory.insert(
                "",
                "end",
                iid=str(addr),
                values=[f"{addr:04X}"] + [f"{b:02X}" for b in data],
            )
        for row in self.listing.get_children():
            addr = int(row)
            self.listing.item(
                row,
                tags=("pc",)
                if addr == self.cpu.pc
                else ("break",)
                if addr in self.breakpoints
                else (),
            )
            values = list(self.listing.item(row, "values"))
            values[0] = ("● " if addr in self.breakpoints else "") + f"{addr:04X}"
            self.listing.item(row, values=values)
        self.run_button.configure(text="Pause  F5" if self.running else "Run  F5")
        self.machine_state.set(
            "RUNNING"
            if self.running
            else "READY"
            if self.program and not self.dirty
            else "EDITING"
        )
        self.editor_view.breakpoint_lines = {
            location["line"]
            for address, location in (
                self.program.locations.items() if self.program else []
            )
            if address in self.breakpoints and location["line"] > 0
        }
        self.editor_view.execution_line = None
        self.editor.tag_remove("pc", "1.0", "end")
        if self.program and self.cpu.pc in self.program.locations:
            line = self.program.locations[self.cpu.pc]["line"]
            if line > 0 and not self.dirty:
                self.editor.tag_add("pc", f"{line}.0", f"{line}.end")
                self.editor_view.execution_line = line
            if str(self.cpu.pc) in self.listing.get_children():
                self.listing.see(str(self.cpu.pc))
        self.editor_view.redraw()
        canvas = self.led_canvas
        canvas.delete("all")
        for i in range(8):
            bit = 7 - i
            high = self.board.read_pin(self.board.mapping["leds"][bit])
            x = 16 + i * max(40, (canvas.winfo_width() - 48) / 8)
            canvas.create_oval(
                x,
                4,
                x + 22,
                26,
                fill="#78E4BB"
                if not high and self.board.enabled["leds"]
                else "#303D55",
                outline="",
            )
            canvas.create_text(
                x + 11, 39, text=f"LED{bit}", fill="#92A1B9", font=(self.ui_font, -10)
            )
        self.draw_segments()
        self.draw_motor()
        self.lcd_text.configure(text="\n".join(self.board.lcd.lines()))
        self.dac_text.configure(
            text=f"DAC {self.board.dac_value * 5 / 255:.3f} V  ·  ADC {self.board.adc_value:02X}  ·  {'Converting' if self.board.adc_remaining else 'Idle'}"
        )
        for n, label in self.port_labels.items():
            addr = 0x80 + n * 16
            label.configure(
                text=f"P{n}  latch {self.cpu.ram[addr]:08b}   pins {self.cpu.read(addr):08b}"
            )
        if self.uart_position < len(self.board.uart.received):
            data = self.board.uart.received[self.uart_position :]
            self.uart_position = len(self.board.uart.received)
            self.uart_output.configure(state="normal")
            self.uart_output.insert(
                "end",
                "".join(
                    chr(v) if 32 <= v < 127 or v in (10, 13) else f"<{v:02X}>"
                    for v in data
                ),
            )
            self.uart_output.see("end")
            self.uart_output.configure(state="disabled")

    def switch_changed(self):
        self.board.switches = [v.get() for v in self.switch_vars]
        self.board.update()
        self.refresh()

    def key(self, key, pressed):
        if pressed:
            self.board.keys.add(key)
        else:
            self.board.keys.discard(key)
        self.board.update()
        self.refresh()

    def hardware_changed(self):
        self.board.enabled.update({k: v.get() for k, v in self.enabled_vars.items()})
        self.board.update()
        self.refresh()

    def analogue_changed(self, value):
        self.board.analogue = float(value)
        self.analogue_text.configure(
            text=f"{float(value):.2f} V · comparator reference = DAC"
        )

    def uart_receive(self):
        self.board.enabled["uart"] = True
        self.enabled_vars["uart"].set(True)
        self.board.uart.configure(
            int(self.baud.get()),
            ["None", "Odd", "Even"].index(self.parity.get()),
            self.board.cycle_us,
        )
        text = self.uart_input.get()
        self.board.receive(text)
        if text:
            self.uart_input.delete(0, "end")
        self.refresh()

    def open_file(self):
        if not self.confirm_discard():
            return
        self.pause_execution()
        path = filedialog.askopenfilename(
            filetypes=[("8051 programs", "*.asm *.a51 *.hex *.txt"), ("All files", "*")]
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
            if path.lower().endswith(".hex"):
                program = import_hex(text)
                self.replace_source(
                    "; Intel HEX image loaded. Original assembly source is unavailable.\n; Use Listing and Memory to inspect the executable.\n"
                )
                self.program = program
                self.dirty = False
                self.reset()
                self.populate_listing()
                self.status.set(f"Loaded {len(self.program.used)} HEX bytes")
                self.show_bottom("Listing")
                return
            self.replace_source(text, Path(path))
            self.status.set(f"Opened {self.path.name}")
        except (OSError, ValueError) as e:
            messagebox.showerror("Open failed", str(e))

    def save_source(self, save_as=False):
        if self.path is None or save_as:
            path = filedialog.asksaveasfilename(
                defaultextension=".asm", filetypes=[("8051 assembly", "*.asm")]
            )
            if not path:
                return False
            self.path = Path(path)
        try:
            self.path.write_text(self.editor.get("1.0", "end-1c"), encoding="utf-8")
            self.saved_source = self.editor.get("1.0", "end-1c")
            self.document_modified = False
            self.update_document_title()
            self.status.set(f"Saved {self.path.name}")
            return True
        except OSError as e:
            messagebox.showerror("Save failed", str(e))
            return False

    def export(self):
        if self.dirty or not self.program:
            if not self.assemble():
                return
        path = filedialog.asksaveasfilename(
            defaultextension=".hex", filetypes=[("Intel HEX", "*.hex")]
        )
        if path:
            try:
                Path(path).write_text(export_hex(self.program), encoding="ascii")
                self.status.set("Intel HEX exported")
            except OSError as e:
                messagebox.showerror("Export failed", str(e))

    def mapping_dialog(self):
        self.pause_execution()
        window = tk.Toplevel(self.root)
        window.title("Pin mappings")
        window.geometry("650x650")
        canvas = tk.Canvas(window, highlightthickness=0)
        scroll = ttk.Scrollbar(window, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas, padding=10)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.create_window((0, 0), window=frame, anchor="nw")
        frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        entries = {}
        ttk.Label(
            frame,
            text="Comma-separated pins, low bit first. Example: P1.0, P1.1",
            wraplength=550,
        ).grid(row=0, column=0, columnspan=2, pady=10)
        for row, (name, pins) in enumerate(self.board.mapping.items(), 1):
            ttk.Label(frame, text=name).grid(
                row=row, column=0, sticky="w", padx=5, pady=3
            )
            entry = ttk.Entry(frame, width=48)
            entry.insert(0, ", ".join(pins))
            entry.grid(row=row, column=1, pady=3)
            entries[name] = entry

        def save():
            try:
                mapping = {
                    k: [p.strip().upper() for p in e.get().split(",")]
                    for k, e in entries.items()
                }
                for k, values in mapping.items():
                    if len(values) != len(DEFAULT_MAPPING[k]):
                        raise ValueError(f"{k} needs {len(DEFAULT_MAPPING[k])} pins")
                    for p in values:
                        pin(p)
                self.board.mapping = mapping
                self.save_settings()
                self.board.update()
                self.refresh()
                window.destroy()
            except ValueError as e:
                messagebox.showerror("Invalid mapping", str(e), parent=window)

        ttk.Button(frame, text="Apply and save", command=save).grid(
            row=len(entries) + 1, column=1, pady=15
        )

    def scope_window(self):
        window = tk.Toplevel(self.root)
        window.title("DAC oscilloscope")
        window.geometry("740x330")
        c = tk.Canvas(window, background="#121B29")
        c.pack(fill="both", expand=True)

        def draw():
            if not window.winfo_exists():
                return
            c.delete("all")
            w, h = max(200, c.winfo_width()), max(150, c.winfo_height())
            c.create_line(45, 20, 45, h - 40, w - 20, h - 40, fill="#566675")
            for v in range(6):
                y = h - 40 - v * (h - 60) / 5
                c.create_text(24, y, text=str(v), fill="#92A1B9")
                c.create_line(45, y, w - 20, y, fill="#303D55")
            c.create_text(
                w / 2,
                h - 15,
                text="Machine cycles · recent DAC samples",
                fill="#92A1B9",
            )
            c.create_text(22, 10, text="Volts", fill="#92A1B9")
            data = list(self.board.scope)
            if len(data) > 1:
                lo, hi = data[0][0], data[-1][0]
                coords = []
                for t, v in data:
                    coords.extend(
                        (
                            45 + (t - lo) / max(1, hi - lo) * (w - 65),
                            h - 40 - v / 5 * (h - 60),
                        )
                    )
                c.create_line(*coords, fill="#78E4BB", width=2)
            window.after(100, draw)

        draw()

    def isa_window(self):
        w = tk.Toplevel(self.root)
        w.title("8051 instruction reference")
        w.geometry("670x500")
        text = tk.Text(w, font=(self.mono_font, -12))
        text.pack(fill="both", expand=True)
        text.insert("end", "Opcode  Bytes  Cycles  Instruction\n\n")
        for row in ISA:
            text.insert(
                "end",
                f"{row['opcode']:02X}      {row['size']}      {row['cycles']}       {row['display']}\n",
            )
        text.configure(state="disabled")

    def load_settings(self):
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            layout = data.get("layout", {})
            self.layout_settings = layout if isinstance(layout, dict) else {}
            if set(data.get("mapping", {})) == set(DEFAULT_MAPPING):
                for key, values in data["mapping"].items():
                    if len(values) != len(DEFAULT_MAPPING[key]):
                        raise ValueError()
                    for value in values:
                        pin(value)
                self.board.mapping = data["mapping"]
            self.board.enabled.update(
                {
                    k: bool(v)
                    for k, v in data.get("enabled", {}).items()
                    if k in self.board.enabled
                }
            )
        except (OSError, ValueError, TypeError):
            pass

    def save_settings(self):
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps(
                {
                    "mapping": self.board.mapping,
                    "enabled": self.board.enabled,
                    "layout": self.capture_layout(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def about(self):
        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME} {VERSION}\n"
            "A Python desktop workbench for the 8051.\n\n"
            "Explore assembly, registers, memory, and virtual peripherals.\n\n"
            "An evolving learning workbench. See docs/compatibility.md "
            "for supported features and simulation limits.\n\n"
            "Free for noncommercial learning. Commercial use and redistribution "
            "require permission; see LICENSE.",
        )

    def close(self):
        if not self.confirm_discard():
            return
        self.pause_execution()
        try:
            self.save_settings()
        except OSError:
            pass
        self.root.destroy()


def main():
    import argparse

    parser = argparse.ArgumentParser(description=f"{APP_NAME}: 8051 desktop workbench")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.smoke_test:
        from ..smoke import run_smoke_test

        raise SystemExit(run_smoke_test())
    prepare_process_identity()
    root = tk.Tk(className="MCS51Studio")
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
