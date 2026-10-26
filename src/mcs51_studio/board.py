"""Python peripheral board using the recovered EdSim51 default pin mappings.

Peripheral timing fidelity is tracked separately from instruction conformance.
"""

from collections import deque

from .serial import UARTEndpoint

DEFAULT_MAPPING = {
    "leds": ["P1." + str(i) for i in range(8)],
    "switches": ["P2." + str(i) for i in range(8)],
    "segments": ["P1." + str(i) for i in range(8)],
    "display_cs": ["P0.7"],
    "display_select": ["P3.3", "P3.4"],
    "key_rows": ["P0." + str(i) for i in range(4)],
    "key_columns": ["P0." + str(i) for i in range(4, 7)],
    "key_gate": ["P3.3"],
    "adc_data": ["P2." + str(i) for i in range(8)],
    "adc_rd": ["P3.7"],
    "adc_wr": ["P3.6"],
    "adc_intr": ["P3.2"],
    "dac_data": ["P1." + str(i) for i in range(8)],
    "dac_wr": ["P0.7"],
    "motor_control": ["P3.0", "P3.1"],
    "motor_sensor": ["P3.5"],
    "comparator_output": ["P3.7"],
    "uart_tx": ["P3.0"],
    "uart_rx": ["P3.1"],
    "lcd_data": ["P1." + str(i) for i in range(8)],
    "lcd_rs": ["P1.3"],
    "lcd_e": ["P1.2"],
}


def pin(pin_name):
    p, b = pin_name.upper().split(".")
    port, bit = int(p[1:]), int(b)
    if port not in range(4) or bit not in range(8):
        raise ValueError("Use P0.0 through P3.7")
    return 0x80 + port * 16, bit


class LCD:
    def __init__(self):
        self.ddram = [" "] * 128
        self.cgram = bytearray(64)
        self.address = 0
        self.cg = False
        self.increment = True
        self.shift = 0
        self.display = False
        self.cursor = False
        self.blink = False
        self.four_bit = False
        self.nibble = None

    def accept(self, value, rs):
        if self.four_bit:
            if self.nibble is None:
                self.nibble = value & 240
                return
            value, self.nibble = self.nibble | (value >> 4), None
        elif not rs and value >> 4 == 2:
            self.four_bit = True
        self.byte(value, rs)

    def byte(self, value, rs):
        if rs:
            if self.cg:
                self.cgram[self.address & 63] = value & 31
            else:
                self.ddram[self.address & 127] = chr(value)
            self.address = (self.address + (1 if self.increment else -1)) & 127
        elif value & 128:
            self.address = value & 127
            self.cg = False
        elif value & 64:
            self.address = value & 63
            self.cg = True
        elif value & 32:
            self.four_bit = not bool(value & 16)
        elif value & 16:
            if value & 8:
                self.shift += -1 if value & 4 else 1
            else:
                self.address = (self.address + (1 if value & 4 else -1)) & 127
        elif value & 8:
            self.display = bool(value & 4)
            self.cursor = bool(value & 2)
            self.blink = bool(value & 1)
        elif value & 4:
            self.increment = bool(value & 2)
        elif value & 2:
            self.address = 0
            self.shift = 0
        elif value & 1:
            self.ddram = [" "] * 128
            self.address = 0
            self.shift = 0

    def lines(self):
        if not self.display:
            return [" " * 16] * 2
        return [
            "".join(self.ddram[(base + i + self.shift) % 128] for i in range(16))
            for base in (0, 64)
        ]


class Board:
    def __init__(self, cpu, mapping=None):
        self.cpu = cpu
        self.mapping = {k: list(v) for k, v in (mapping or DEFAULT_MAPPING).items()}
        self.enabled = dict(
            leds=True,
            switches=True,
            keypad=True,
            adc=False,
            dac=False,
            motor=True,
            display=True,
            lcd=False,
            comparator=False,
            uart=False,
        )
        self.switches = [True] * 8
        self.keys = set()
        self.key_gate = False
        self.analogue = 0.0
        self.comparator_reference = 2.5
        self.adc_value = 255
        self.adc_snapshot = 0
        self.adc_remaining = 0
        self.adc_intr = True
        self.dac_value = 0
        self.scope = deque(maxlen=600)
        self.digits = [255] * 4
        self.motor_angle = 90.0
        self.motor_direction = 0
        self.motor_position = 2
        self.motor_current = 7
        self.motor_count = 7
        self.uart = UARTEndpoint()
        self.cycle_us = 1.0
        self.lcd = LCD()
        self.previous_e = False
        self.previous_wr = True
        self.last_cycles = 0

    def read_pin(self, name):
        a, b = pin(name)
        return self.cpu.read(a) >> b & 1

    def get(self, role, index=0):
        return self.read_pin(self.mapping[role][index])

    def data(self, role):
        return sum(self.read_pin(p) << i for i, p in enumerate(self.mapping[role]))

    def hold_low(self, name):
        a, b = pin(name)
        self.cpu.port_inputs[a] &= ~(1 << b)

    def update(self):
        c = self.cpu
        elapsed = c.cycles - self.last_cycles
        self.last_cycles = c.cycles
        for a in c.port_inputs:
            c.port_inputs[a] = 255
        if self.enabled["switches"]:
            for i, high in enumerate(self.switches):
                if not high:
                    self.hold_low(self.mapping["switches"][i])
        if self.enabled["keypad"]:
            # A closed key joins its selected column to the corresponding row.
            for row, column in self.keys:
                r, col = (
                    self.mapping["key_rows"][row],
                    self.mapping["key_columns"][column],
                )
                if not self.read_pin(r) or not self.read_pin(col):
                    self.hold_low(r)
                    self.hold_low(col)
            if self.key_gate and any(
                not self.read_pin(p) for p in self.mapping["key_rows"]
            ):
                self.hold_low(self.mapping["key_gate"][0])
        if self.enabled["adc"]:
            if self.adc_remaining and elapsed:
                self.adc_remaining = max(
                    0, self.adc_remaining - int(elapsed * self.cycle_us + 0.5)
                )
                converted = 8 * (20 - self.adc_remaining) // 20
                mask = (255 << (8 - converted)) & 255 if converted else 0
                self.adc_value = (self.adc_snapshot & mask) | (255 ^ mask)
                if not self.adc_remaining:
                    self.adc_intr = False
            if not self.adc_intr:
                self.hold_low(self.mapping["adc_intr"][0])
            if not self.get("adc_rd"):
                for i, p in enumerate(self.mapping["adc_data"]):
                    if not self.adc_value >> i & 1:
                        self.hold_low(p)
            wr = self.get("adc_wr")
            if not self.previous_wr and wr:
                self.adc_remaining = 20
                self.adc_intr = True
                self.adc_value = 255
                self.adc_snapshot = min(255, max(0, int(self.analogue / 5 * 255 + 0.5)))
            self.previous_wr = bool(wr)
        if self.enabled["display"] and self.get("display_cs"):
            selected = (
                self.get("display_select", 0) | self.get("display_select", 1) << 1
            )
            self.digits[selected] = self.data("segments")
        if self.enabled["dac"] and not self.get("dac_wr"):
            self.dac_value = self.data("dac_data")
            self.scope.append((c.cycles, self.dac_value * 5 / 255))
        if self.enabled["motor"]:
            first, second = self.get("motor_control", 0), self.get("motor_control", 1)
            self.motor_direction = 0 if first == second else 1 if first else -1
            if self.motor_direction:
                self.motor_count -= elapsed * self.cycle_us
            if self.motor_count <= 0:
                self.motor_count = self.motor_current
                self.motor_position = (self.motor_position + self.motor_direction) % 8
            self.motor_angle = self.motor_position * 45
            if self.motor_position == 0:
                self.hold_low(self.mapping["motor_sensor"][0])
        if self.enabled["lcd"]:
            e = bool(self.get("lcd_e"))
            if self.previous_e and not e:
                self.lcd.accept(self.data("lcd_data"), self.get("lcd_rs"))
            self.previous_e = e
        if self.enabled["comparator"] and self.analogue <= self.dac_value * 5 / 255:
            self.hold_low(self.mapping["comparator_output"][0])
        if self.enabled["uart"]:
            rx = self.get("uart_rx")
            if not self.uart.tx_line:
                self.hold_low(self.mapping["uart_tx"][0])
            for _ in range(elapsed):
                self.uart.pulse(rx)

    def receive(self, text):
        self.uart.start(text)
