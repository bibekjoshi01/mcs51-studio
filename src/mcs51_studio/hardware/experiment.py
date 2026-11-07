"""Deterministic teaching controls, separate from electrical pin resolution."""

from dataclasses import asdict, dataclass


@dataclass
class ExperimentSettings:
    keypad_mode: str = "Standard"
    keypad_bounce: bool = False
    motor_speed: int = 100
    switch_bounce: bool = False
    bounce_us: int = 30000
    lcd_timing: bool = True
    interrupt_pin: str = "P3.2"
    interrupt_width_us: int = 10

    @classmethod
    def validated(cls, data):
        fields = set(asdict(cls()))
        optional = {"keypad_bounce", "motor_speed"}
        if not isinstance(data, dict) or not fields - optional <= set(data) <= fields:
            raise ValueError("Experiment settings are incomplete or unsupported.")
        result = cls(**data)
        if result.keypad_mode not in ("Standard", "Pulse", "Radio"):
            raise ValueError("Keypad mode must be Standard, Pulse, or Radio.")
        if (
            type(result.switch_bounce) is not bool
            or type(result.keypad_bounce) is not bool
            or type(result.lcd_timing) is not bool
        ):
            raise ValueError("Bounce and LCD timing must be true or false.")
        if type(result.motor_speed) is not int or not 1 <= result.motor_speed <= 100:
            raise ValueError("Motor speed must be from 1 to 100 percent.")
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
        self.previous_keys = set()
        self.key_bounces = {}

    def key_levels(self, desired, time, settings):
        desired = set(desired)
        if settings.keypad_bounce and settings.keypad_mode == "Standard":
            for key in desired - self.previous_keys:
                self.key_bounces[key] = time
        else:
            self.key_bounces.clear()
        self.previous_keys = set(desired)
        contacts = set(desired)
        for key, started in list(self.key_bounces.items()):
            elapsed = time - started
            if key not in desired or elapsed >= 30000:
                del self.key_bounces[key]
            elif elapsed // 3000 % 2 == 0:
                contacts.discard(key)
        return contacts

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
