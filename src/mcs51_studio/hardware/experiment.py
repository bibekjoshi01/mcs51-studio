"""Deterministic teaching controls, separate from electrical pin resolution."""

from dataclasses import asdict, dataclass


@dataclass
class ExperimentSettings:
    keypad_mode: str = "Pulse"
    switch_bounce: bool = False
    bounce_us: int = 30000
    lcd_timing: bool = True
    interrupt_pin: str = "P3.2"
    interrupt_width_us: int = 10

    @classmethod
    def validated(cls, data):
        if not isinstance(data, dict) or set(data) != set(asdict(cls())):
            raise ValueError("Experiment settings are incomplete or unsupported.")
        result = cls(**data)
        if result.keypad_mode not in ("Standard", "Pulse", "Radio"):
            raise ValueError("Keypad mode must be Standard, Pulse, or Radio.")
        if (
            type(result.switch_bounce) is not bool
            or type(result.lcd_timing) is not bool
        ):
            raise ValueError("Bounce and LCD timing must be true or false.")
        if type(result.bounce_us) is not int or not 1 <= result.bounce_us <= 100000:
            raise ValueError("Bounce duration must be 1–100000 µs.")
        if result.interrupt_pin not in ("P3.2", "P3.3"):
            raise ValueError("Interrupt pulses use P3.2 / INT0 or P3.3 / INT1.")
        if (
            type(result.interrupt_width_us) is not int
            or not 1 <= result.interrupt_width_us <= 1000000
        ):
            raise ValueError("Pulse width must be 1–1000000 µs.")
        return result


class InputStimulus:
    def __init__(self):
        self.previous_switches = [True] * 8
        self.bounces = {}
        self.pulses = {}

    def switch_levels(self, desired, time, settings):
        for index, (old, new) in enumerate(zip(self.previous_switches, desired)):
            if old != new and settings.switch_bounce:
                self.bounces[index] = time
        self.previous_switches = list(desired)
        levels = list(desired)
        for index, started in list(self.bounces.items()):
            elapsed = time - started
            if not settings.switch_bounce or elapsed >= settings.bounce_us:
                del self.bounces[index]
            else:
                # A repeatable alternating contact, independent of wall-clock/UI rate.
                phase = elapsed * 10 // settings.bounce_us
                levels[index] = desired[index] if phase % 2 else not desired[index]
        return levels

    def pulse(self, pin, time, width):
        if pin not in ("P3.2", "P3.3") or type(width) is not int or width < 1:
            raise ValueError("Choose INT0/INT1 and a positive integer pulse width.")
        self.pulses[pin] = max(self.pulses.get(pin, time), time + width)

    def active_pins(self, time):
        self.pulses = {pin: end for pin, end in self.pulses.items() if time < end}
        return tuple(self.pulses)
