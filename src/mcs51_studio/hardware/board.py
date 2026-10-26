"""Virtual learning board, configurable wiring, and peripheral stepping."""

from collections import deque

from .experiment import ExperimentSettings, InputStimulus
from .lcd import LCD
from .uart import UARTEndpoint

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
        self.held_keys = set()
        self.experiment = ExperimentSettings()
        self.stimulus = InputStimulus()
        self.key_gate = False
        self.analogue = 0.0
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
        self.on_sample = None

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
            for i, high in enumerate(
                self.stimulus.switch_levels(self.switches, c.cycles, self.experiment)
            ):
                if not high:
                    self.hold_low(self.mapping["switches"][i])
        for name in self.stimulus.active_pins(c.cycles):
            self.hold_low(name)
        self.settle_keys()
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
            wr = self.get("adc_wr")
            if not self.previous_wr and wr:
                self.adc_remaining = 20
                self.adc_intr = True
                self.adc_value = 255
                self.adc_snapshot = min(255, max(0, int(self.analogue / 5 * 255 + 0.5)))
            self.previous_wr = bool(wr)
            if not self.adc_intr:
                self.hold_low(self.mapping["adc_intr"][0])
            if not self.get("adc_rd"):
                for i, p in enumerate(self.mapping["adc_data"]):
                    if not self.adc_value >> i & 1:
                        self.hold_low(p)
        else:
            self.adc_remaining = 0
            self.adc_value = 255
            self.adc_intr = True
            self.previous_wr = True
        self.digits = [255] * 4

        if self.enabled["display"] and self.get("display_cs"):
            selected = (
                self.get("display_select", 0) | self.get("display_select", 1) << 1
            )
            self.digits[selected] = self.data("segments")
        if self.enabled["dac"]:
            if not self.get("dac_wr"):
                self.dac_value = self.data("dac_data")
            sample = (c.cycles, self.dac_value * 5 / 255)
            if self.scope and self.scope[-1][0] == c.cycles:
                self.scope[-1] = sample
            else:
                self.scope.append(sample)
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
        else:
            self.motor_direction = 0
        if self.enabled["lcd"]:
            e = bool(self.get("lcd_e"))
            if self.previous_e and not e:
                self.lcd.accept(
                    self.data("lcd_data"),
                    self.get("lcd_rs"),
                    c.cycles,
                    self.experiment.lcd_timing,
                )
            self.previous_e = e
        else:
            self.previous_e = False
        if (
            self.enabled["comparator"]
            and not self.enabled["adc"]
            and self.analogue <= self.dac_value * 5 / 255
        ):
            self.hold_low(self.mapping["comparator_output"][0])
        if self.enabled["uart"]:
            rx = self.get("uart_rx")
            if not self.uart.tx_line:
                self.hold_low(self.mapping["uart_tx"][0])
            for _ in range(elapsed):
                self.uart.pulse(rx)

        self.settle_keys()
        if self.on_sample:
            self.on_sample()

    @property
    def led_mask(self):
        """Active-low LED outputs, bit 0 representing LED 0."""
        return (255 ^ self.data("leds")) if self.enabled["leds"] else 0

    def output_state(self):
        return self.led_mask, tuple(self.digits)

    def settle_keys(self):
        if not self.enabled["keypad"]:
            return
        # A connected key group must settle regardless of set iteration order.
        for _ in range(7):
            before = tuple(self.cpu.port_inputs.values())
            for row, column in self.keys:
                r = self.mapping["key_rows"][row]
                col = self.mapping["key_columns"][column]
                if not self.read_pin(r) or not self.read_pin(col):
                    self.hold_low(r)
                    self.hold_low(col)
            if tuple(self.cpu.port_inputs.values()) == before:
                break
        if self.key_gate and any(
            not self.read_pin(p) for p in self.mapping["key_rows"]
        ):
            self.hold_low(self.mapping["key_gate"][0])

    def key_event(self, key, pressed):
        if pressed and not self.enabled["keypad"]:
            return
        if pressed and key in self.held_keys:
            return
        if pressed:
            self.held_keys.add(key)
        else:
            self.held_keys.discard(key)
        if not self.enabled["keypad"]:
            return
        mode = self.experiment.keypad_mode
        if mode == "Pulse":
            if pressed:
                self.keys.add(key)
            else:
                self.keys.discard(key)
        elif pressed:
            active = key in self.keys
            if mode == "Radio":
                self.keys.clear()
            if active:
                self.keys.discard(key)
            else:
                self.keys.add(key)

    def set_keypad_mode(self, mode):
        if mode not in ("Standard", "Pulse", "Radio"):
            raise ValueError("Unknown keypad mode")
        if mode != self.experiment.keypad_mode:
            self.keys.clear()
            self.held_keys.clear()
        self.experiment.keypad_mode = mode

    def receive(self, text):
        self.uart.start(text)
