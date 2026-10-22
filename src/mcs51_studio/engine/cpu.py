"""8051 CPU state, instruction execution, interrupts, and timer stepping.

Opcode sizes and cycle counts are loaded from the bundled instruction catalog.
Known simulation limits are documented in docs/compatibility.md.
"""

from ..resources import ISA
from .profile import CLASSIC_8051
from .serial import Serial

SFR = dict(
    P0=0x80,
    SP=0x81,
    DPL=0x82,
    DPH=0x83,
    PCON=0x87,
    TCON=0x88,
    TMOD=0x89,
    TL0=0x8A,
    TL1=0x8B,
    TH0=0x8C,
    TH1=0x8D,
    P1=0x90,
    SCON=0x98,
    SBUF=0x99,
    P2=0xA0,
    IE=0xA8,
    P3=0xB0,
    IP=0xB8,
    PSW=0xD0,
    ACC=0xE0,
    B=0xF0,
)
BITS = dict(
    IT0=0x88,
    IE0=0x89,
    IT1=0x8A,
    IE1=0x8B,
    TR0=0x8C,
    TF0=0x8D,
    TR1=0x8E,
    TF1=0x8F,
    RI=0x98,
    TI=0x99,
    RB8=0x9A,
    TB8=0x9B,
    REN=0x9C,
    SM2=0x9D,
    SM1=0x9E,
    SM0=0x9F,
    EX0=0xA8,
    ET0=0xA9,
    EX1=0xAA,
    ET1=0xAB,
    ES=0xAC,
    EA=0xAF,
    PX0=0xB8,
    PT0=0xB9,
    PX1=0xBA,
    PT1=0xBB,
    PS=0xBC,
    P=0xD0,
    OV=0xD2,
    RS0=0xD3,
    RS1=0xD4,
    F0=0xD5,
    AC=0xD6,
    CY=0xD7,
)


def signed(v):
    return v - 256 if v > 127 else v


class ProcessorError(ValueError):
    """A program used an undefined or unsupported processor operation."""


class CPU:
    profile = CLASSIC_8051

    def __init__(self):
        self.code = bytearray(self.profile.code_bytes)
        self.reset()

    def reset(self):
        # Direct address space: lower RAM followed by SFR addresses.
        # Indirect accesses must go through read_indirect/write_indirect.
        self.ram = bytearray(256)
        self.xram = bytearray(self.profile.external_ram_bytes)
        self.ram[0x81] = 7
        for a in (0x80, 0x90, 0xA0, 0xB0):
            self.ram[a] = 255
        self.pc = self.cycles = self.instructions = 0
        self.port_inputs = {a: 255 for a in (0x80, 0x90, 0xA0, 0xB0)}
        self.serial_rx = 0
        self.serial_tx = []
        self.serial_pending = 0
        self.serial = Serial(self)
        self.external_previous = [True, True]
        self.timer_previous = [True, True]
        self.interrupt_stack = []
        self.reti = False
        self.on_write = None
        self.executing = False
        self.interrupt_access = False

    def check_direct(self, address):
        if address >= 128 and address not in SFR.values():
            raise ProcessorError(f"Unimplemented SFR {address:02X}H on Classic 8051")
        if self.executing and address in (0xA8, 0xB8):
            self.interrupt_access = True

    def check_indirect(self, address):
        if not 0 <= address < self.profile.internal_ram_bytes:
            raise ProcessorError(
                f"Internal RAM address {address:02X}H is outside Classic 8051 RAM (00–7FH)"
            )

    def read_indirect(self, address):
        self.check_indirect(address)
        return self.ram[address]

    def write_indirect(self, address, value):
        self.check_indirect(address)
        self.ram[address] = value & 255

    def read(self, address, latch=False):
        address &= 255
        self.check_direct(address)
        if address in self.port_inputs and not latch:
            return self.ram[address] & self.port_inputs[address]
        if address == 0x99 and not latch:
            return self.serial.sbuf
        return self.ram[address]

    def write(self, address, value):
        address &= 255
        self.check_direct(address)
        if address == 0x98 and self.ram[address] >> 6 != (value & 255) >> 6:
            self.serial.reset()
        self.ram[address] = value & 255
        if address in (0xE0, 0xD0):
            self.parity()
        if address == 0x99:
            self.serial_tx.append(value & 255)
            self.serial.send()
        if self.on_write:
            self.on_write(address, value & 255)

    def parity(self):
        self.ram[0xD0] = (self.ram[0xD0] & 254) | (self.ram[0xE0].bit_count() & 1)

    @property
    def a(self):
        return self.ram[0xE0]

    @a.setter
    def a(self, value):
        self.write(0xE0, value)

    @property
    def carry(self):
        return self.ram[0xD0] >> 7

    @carry.setter
    def carry(self, value):
        self.flag(7, value)

    @property
    def dptr(self):
        return self.ram[0x82] | self.ram[0x83] << 8

    @dptr.setter
    def dptr(self, value):
        self.ram[0x82] = value & 255
        self.ram[0x83] = value >> 8 & 255

    def flag(self, bit, value):
        self.ram[0xD0] = (self.ram[0xD0] & ~(1 << bit)) | (bool(value) << bit)

    def reg_address(self, n):
        return ((self.ram[0xD0] >> 3) & 3) * 8 + n

    def reg(self, n):
        return self.read(self.reg_address(n))

    def set_reg(self, n, value):
        self.write(self.reg_address(n), value)

    def bit_address(self, bit):
        if not 0 <= bit <= 255:
            raise ValueError("BitAddressAccessException")
        a = 0x20 + bit // 8 if bit < 128 else bit & 0xF8
        self.check_direct(a)
        return a, bit & 7

    def bit(self, bit, latch=False):
        a, n = self.bit_address(bit)
        return self.read(a, latch) >> n & 1

    def set_bit(self, bit, value):
        a, n = self.bit_address(bit)
        if bit in (0x9E, 0x9F) and self.bit(bit) != bool(value):
            self.serial.reset()
        self.ram[a] = (self.ram[a] & ~(1 << n)) | (bool(value) << n)
        if a == 0xE0:
            self.parity()

    def push(self, value):
        address = (self.ram[0x81] + 1) & 255
        self.write_indirect(address, value)
        self.ram[0x81] = address

    def pop(self):
        value = self.read_indirect(self.ram[0x81])
        self.ram[0x81] = self.ram[0x81] - 1 & 255
        return value

    def source(self, op, operand):
        mode = op & 15
        if mode == 4:
            return operand
        if mode == 5:
            return self.read(operand)
        if mode in (6, 7):
            return self.read_indirect(self.reg(mode & 1))
        return self.reg(mode & 7)

    def execute(self, op, x=0, y=0):
        """Execute exactly one instruction, without peripheral/interrupt polling."""
        # Check both stack bytes before calls/returns to avoid partial frames.
        sp = self.ram[0x81]
        if op & 31 == 17 or op == 0x12:
            for address in ((sp + 1) & 255, (sp + 2) & 255):
                self.check_indirect(address)
        elif op in (0x22, 0x32):
            for address in (sp, (sp - 1) & 255):
                self.check_indirect(address)
        start = self.pc
        next_pc = (start + ISA[op]["size"]) & 65535
        a = self.a
        if op & 31 in (1, 17):
            if op & 31 == 17:
                self.push(next_pc & 255)
                self.push(next_pc >> 8)
            next_pc = (next_pc & 0xF800) | ((op & 0xE0) << 3) | x
        elif op in (0x02, 0x12):
            if op == 0x12:
                self.push(next_pc & 255)
                self.push(next_pc >> 8)
            next_pc = x << 8 | y
        elif op in (0x22, 0x32):
            hi = self.pop()
            next_pc = hi << 8 | self.pop()
            if op == 0x32:
                self.reti = True
                if self.interrupt_stack:
                    self.interrupt_stack.pop()
        elif op == 0x00:
            pass
        elif op in (0x03, 0x13, 0x23, 0x33):
            if op == 3:
                self.a = a >> 1 | (a & 1) << 7
            elif op == 0x23:
                self.a = a << 1 | a >> 7
            elif op == 0x13:
                c = self.carry
                self.carry = a & 1
                self.a = a >> 1 | c << 7
            else:
                c = self.carry
                self.carry = a >> 7
                self.a = a << 1 | c
        elif 0x04 <= op <= 0x0F or 0x14 <= op <= 0x1F:
            delta = 1 if op < 0x10 else -1
            mode = op & 15
            if mode == 4:
                self.a = a + delta
            elif mode == 5:
                self.write(x, self.read(x, True) + delta)
            elif mode in (6, 7):
                addr = self.reg(mode & 1)
                self.write_indirect(addr, self.read_indirect(addr) + delta)
            else:
                self.set_reg(mode & 7, self.reg(mode & 7) + delta)
        elif 0x24 <= op <= 0x2F or 0x34 <= op <= 0x3F:
            v = self.source(op, x)
            c = self.carry if op >= 0x34 else 0
            result = a + v + c
            self.a = result
            self.carry = result > 255
            self.flag(2, not -128 <= signed(a) + signed(v) + c <= 127)
            self.flag(6, (a & 15) + (v & 15) + c > 15)
        elif 0x94 <= op <= 0x9F:
            v, c = self.source(op, x), self.carry
            self.a = a - v - c
            self.carry = a < v + c
            self.flag(2, not -128 <= signed(a) - signed(v) - c <= 127)
            self.flag(6, (a & 15) < (v & 15) + c)
        elif op in (0x10, 0x20, 0x30):
            b = self.bit(x, latch=op == 0x10)
            take = b if op != 0x30 else not b
            if take:
                if op == 0x10:
                    self.set_bit(x, 0)
                next_pc = next_pc + signed(y) & 65535
        elif op in (0x40, 0x50, 0x60, 0x70, 0x80):
            take = {
                0x40: self.carry,
                0x50: not self.carry,
                0x60: not a,
                0x70: bool(a),
                0x80: True,
            }[op]
            if take:
                next_pc = next_pc + signed(x) & 65535
        elif (
            op in (0x42, 0x43, 0x52, 0x53, 0x62, 0x63)
            or 0x44 <= op <= 0x4F
            or 0x54 <= op <= 0x5F
            or 0x64 <= op <= 0x6F
        ):
            group = op >> 4
            calc = lambda u, v: u | v if group == 4 else u & v if group == 5 else u ^ v
            if op & 15 in (2, 3):
                self.write(x, calc(self.read(x, True), a if op & 15 == 2 else y))
            else:
                self.a = calc(a, self.source(op, x))
        elif op in (0x72, 0x82, 0xA0, 0xB0):
            v = self.bit(x)
            if op in (0xA0, 0xB0):
                v = not v
            self.carry = (self.carry | v) if op in (0x72, 0xA0) else (self.carry & v)
        elif op == 0x73:
            next_pc = self.dptr + a & 65535
        elif op == 0x74:
            self.a = x
        elif op == 0x75:
            self.write(x, y)
        elif op in (0x76, 0x77):
            self.write_indirect(self.reg(op & 1), x)
        elif 0x78 <= op <= 0x7F:
            self.set_reg(op & 7, x)
        elif op in (0x83, 0x93):
            self.a = self.code[((next_pc if op == 0x83 else self.dptr) + a) & 65535]
        elif op == 0x84:
            b = self.ram[0xF0]
            if b:
                self.a = a // b
                self.write(0xF0, a % b)
            self.flag(2, b == 0)
            self.carry = 0
        elif op == 0x85:
            self.write(y, self.read(x))
        elif op in (0x86, 0x87):
            self.write(x, self.read_indirect(self.reg(op & 1)))
        elif 0x88 <= op <= 0x8F:
            self.write(x, self.reg(op & 7))
        elif op == 0x90:
            self.dptr = x << 8 | y
        elif op == 0x92:
            self.set_bit(x, self.carry)
        elif op == 0xA2:
            self.carry = self.bit(x)
        elif op == 0xA3:
            self.dptr = self.dptr + 1
        elif op == 0xA4:
            result = a * self.ram[0xF0]
            self.a = result
            self.write(0xF0, result >> 8)
            self.flag(2, result > 255)
            self.carry = 0
        elif op in (0xA6, 0xA7):
            self.write_indirect(self.reg(op & 1), self.read(x))
        elif 0xA8 <= op <= 0xAF:
            self.set_reg(op & 7, self.read(x))
        elif op in (0xB2, 0xC2, 0xD2):
            self.set_bit(x, 1 - self.bit(x, latch=True) if op == 0xB2 else op == 0xD2)
        elif op in (0xB3, 0xC3, 0xD3):
            self.carry = 1 - self.carry if op == 0xB3 else op == 0xD3
        elif 0xB4 <= op <= 0xBF:
            if op == 0xB4:
                u, v = a, x
            elif op == 0xB5:
                u, v = a, self.read(x)
            elif op in (0xB6, 0xB7):
                u, v = self.read_indirect(self.reg(op & 1)), x
            else:
                u, v = self.reg(op & 7), x
            self.carry = u < v
            if u != v:
                next_pc = next_pc + signed(y) & 65535
        elif op == 0xC0:
            # PUSH SP stores the incremented SP, per the instruction operation.
            self.push((self.ram[0x81] + 1) & 255 if x == 0x81 else self.read(x))
        elif op == 0xC4:
            self.a = a >> 4 | a << 4
        elif 0xC5 <= op <= 0xCF:
            addr = (
                x
                if op == 0xC5
                else self.reg(op & 1)
                if op < 0xC8
                else self.reg_address(op & 7)
            )
            indirect = op in (0xC6, 0xC7)
            value = self.read_indirect(addr) if indirect else self.read(addr)
            if indirect:
                self.write_indirect(addr, a)
            else:
                self.write(addr, a)
            self.a = value
        elif op == 0xD0:
            self.check_direct(x)
            self.write(x, self.pop())
        elif op == 0xD4:
            v = a
            if (v & 15) > 9 or self.bit(0xD6):
                v += 6
            if v > 255:
                v -= 256
                self.carry = 1
            if v >> 4 > 9 or self.carry:
                v += 96
                if v > 255:
                    v -= 256
                    self.carry = 1
            self.a = v
        elif op == 0xD5 or 0xD8 <= op <= 0xDF:
            addr = x if op == 0xD5 else self.reg_address(op & 7)
            value = self.read(addr, True) - 1 & 255
            self.write(addr, value)
            if value:
                next_pc = next_pc + signed(y if op == 0xD5 else x) & 65535
        elif op in (0xD6, 0xD7):
            addr = self.reg(op & 1)
            value = self.read_indirect(addr)
            self.write_indirect(addr, (value & 240) | (a & 15))
            self.a = (a & 240) | (value & 15)
        elif op in (0xE0, 0xE2, 0xE3, 0xF0, 0xF2, 0xF3):
            address = (
                self.dptr
                if op in (0xE0, 0xF0)
                else (self.ram[0xA0] << 8 | self.reg(op & 1))
            )
            if op < 0xF0:
                self.a = self.xram[address]
            else:
                self.xram[address] = a
            # External memory cycles release the P0 latch. P2 is unchanged.
            self.write(0x80, 255)
        elif op == 0xE4:
            self.a = 0
        elif op == 0xE5:
            self.a = self.read(x)
        elif op in (0xE6, 0xE7):
            self.a = self.read_indirect(self.reg(op & 1))
        elif 0xE8 <= op <= 0xEF:
            self.a = self.reg(op & 7)
        elif op == 0xF4:
            self.a = a ^ 255
        elif op == 0xF5:
            self.write(x, a)
        elif op in (0xF6, 0xF7):
            self.write_indirect(self.reg(op & 1), a)
        elif 0xF8 <= op <= 0xFF:
            self.set_reg(op & 7, a)
        else:
            raise ProcessorError(f"Reserved opcode {op:02X}H on Classic 8051")
        self.parity()
        self.pc = next_pc
        return next_pc

    def increment_timer(self, timer, kind):
        """Advance one timer count and return whether the whole timer overflowed."""
        low, high = 0x8A + timer, 0x8C + timer
        lo, hi = self.ram[low], self.ram[high]
        if kind == 0:
            value = ((hi << 5) | (lo & 31)) + 1
            self.ram[low] = (lo & 0xE0) | (value & 31)
            self.ram[high] = (value >> 5) & 255
            return value == 8192
        if kind == 1:
            value = ((hi << 8) | lo) + 1
            self.ram[low], self.ram[high] = value & 255, (value >> 8) & 255
            return value == 65536
        self.ram[low] = hi if kind == 2 and lo == 255 else (lo + 1) & 255
        return lo == 255

    def tick_timers(self, count):
        """Sample pins and advance peripherals once per 12-clock machine cycle."""
        for _ in range(count):
            split = self.ram[0x89] & 3 == 3
            for t in (0, 1):
                mode = self.ram[0x89] >> (t * 4) & 15
                kind = mode & 3
                current = bool(self.bit(0xB4 + t))
                falling = self.timer_previous[t] and not current
                self.timer_previous[t] = current
                running = (t == 1 and split) or self.bit(0x8C + 2 * t)
                if t == 1 and kind == 3:
                    continue
                if not running or (mode & 8 and not self.bit(0xB2 + t)):
                    continue
                if mode & 4 and not falling:
                    continue
                if self.increment_timer(t, kind):
                    if t == 1 and self.serial.mode in (1, 3):
                        self.serial.pulse_clock()
                    if not (t == 1 and split):
                        self.set_bit(0x8D + 2 * t, 1)
            if split and self.bit(0x8E):
                self.ram[0x8C] = (self.ram[0x8C] + 1) & 255
                if self.ram[0x8C] == 0:
                    self.set_bit(0x8F, 1)
            self.serial.poll()
            for source in (0, 1):
                current = bool(self.bit(0xB2 + source))
                edge_mode = self.bit(0x88 + source * 2)
                if not edge_mode:
                    self.set_bit(0x89 + source * 2, not current)
                elif not current and self.external_previous[source]:
                    self.set_bit(0x89 + source * 2, 1)
                self.external_previous[source] = current

    def interrupt_requests(self):
        return [
            self.bit(0x89),
            self.bit(0x8D),
            self.bit(0x8B),
            self.bit(0x8F),
            self.bit(0x98) or self.bit(0x99),
        ]

    def poll_interrupts(self, pending=None):
        if not self.bit(0xAF):
            return
        if pending is None:
            pending = self.interrupt_requests()
        active = self.interrupt_stack[-1] if self.interrupt_stack else -1
        for level in (1, 0):
            if level <= active:
                continue
            for n, requested in enumerate(pending):
                if (
                    not requested
                    or not self.bit(0xA8 + n)
                    or self.bit(0xB8 + n) != level
                ):
                    continue
                self.check_indirect((self.ram[0x81] + 1) & 255)
                self.check_indirect((self.ram[0x81] + 2) & 255)
                self.push(self.pc & 255)
                self.push(self.pc >> 8)
                self.pc = (3, 11, 19, 27, 35)[n]
                self.interrupt_stack.append(level)
                if n in (1, 3):
                    self.set_bit(0x8D if n == 1 else 0x8F, 0)
                elif n in (0, 2) and self.bit(0x88 + n):
                    self.set_bit(0x89 + n, 0)
                # Hardware LCALL consumes two machine cycles, including timers.
                for _ in range(2):
                    entry_pending = self.interrupt_requests()
                    self.tick_timers(1)
                    self.cycles += 1
                # A high-priority request can preempt the low-priority entry
                # before its first ISR instruction. At most two levels exist.
                self.poll_interrupts(entry_pending)
                return

    def step(self):
        op = self.code[self.pc]
        x, y = self.code[(self.pc + 1) & 65535], self.code[(self.pc + 2) & 65535]
        cycles = ISA[op]["cycles"]
        # The final cycle polls the preceding cycle's interrupt sample.
        for _ in range(cycles):
            pending = self.interrupt_requests()
            self.tick_timers(1)
        self.interrupt_access = False
        self.executing = True
        try:
            self.execute(op, x, y)
        finally:
            self.executing = False
        self.cycles += cycles
        self.instructions += 1
        if self.reti:
            self.reti = False
        elif not self.interrupt_access:
            self.poll_interrupts(pending)
        return op
