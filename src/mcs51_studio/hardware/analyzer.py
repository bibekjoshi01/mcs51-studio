"""Bounded instruction-boundary signal capture and waveform measurements."""

from collections import deque

PINS = tuple(f"P{port}.{bit}" for port in range(4) for bit in range(8))


class LogicCapture:
    def __init__(self, capacity=8192):
        if capacity < 4:
            raise ValueError("Capture capacity must be at least four samples.")
        self.capacity = capacity
        self.clear()

    def clear(self):
        self.samples = deque(maxlen=self.capacity)
        self.state = "Idle"
        self.trigger_time = None
        self.end = 0
        self.previous = None
        self.trigger_pin = None
        self.edge = "Either"
        self.duration = 1000

    def arm(self, time, value, trigger_pin=None, edge="Either", duration=1000):
        if trigger_pin is not None and trigger_pin not in PINS:
            raise ValueError("Choose a valid port pin.")
        if edge not in ("Rising", "Falling", "Either") or duration <= 0:
            raise ValueError("Choose an edge and a positive capture duration.")
        self.clear()
        self.trigger_pin, self.edge, self.duration = trigger_pin, edge, duration
        self.state = "Armed" if trigger_pin else "Capturing"
        self.trigger_time = None if trigger_pin else time
        self.samples.append((time, value))
        self.previous = value
        self.end = time

    def sample(self, time, value):
        if self.state not in ("Armed", "Capturing"):
            return
        if time < self.end:
            self.clear()
            return
        if self.state == "Armed":
            bit = PINS.index(self.trigger_pin)
            old, new = self.previous >> bit & 1, value >> bit & 1
            matched = old != new and (
                self.edge == "Either" or new == (self.edge == "Rising")
            )
            if matched:
                self.trigger_time = time
                self.state = "Capturing"
            else:
                while len(self.samples) > self.capacity // 4:
                    self.samples.popleft()
        if value != self.previous:
            if self.samples and self.samples[-1][0] == time:
                self.samples[-1] = (time, value)
            elif len(self.samples) == self.capacity:
                self.state = "Buffer Full"
                self.end = time
                return
            else:
                self.samples.append((time, value))
        self.previous = value
        self.end = time
        if self.trigger_time is not None and time - self.trigger_time >= self.duration:
            self.state = "Complete"

    def stop(self):
        if self.state in ("Armed", "Capturing"):
            self.state = "Stopped"

    def measurements(self, pin, start=None, end=None):
        """Return only complete observed pulses/cycles, never inferred edges."""
        bit = PINS.index(pin)
        edges = []
        previous = None
        for time, mask in self.samples:
            value = mask >> bit & 1
            if previous is not None and value != previous:
                if (start is None or time >= start) and (end is None or time <= end):
                    edges.append((time, value))
            previous = value
        result = {}
        for (a, level), (b, _) in zip(edges, edges[1:]):
            result["high_us" if level else "low_us"] = b - a
        for i in range(len(edges) - 2):
            (a, level), (b, _), (c, _) = edges[i : i + 3]
            if level == 1 and c > a:
                result.update(
                    period_us=c - a,
                    frequency_hz=1_000_000 / (c - a),
                    duty_percent=100 * (b - a) / (c - a),
                )
        return result


def port_mask(cpu):
    return sum(cpu.read(0x80 + 16 * port) << (8 * port) for port in range(4))


def held_value(samples, time):
    value = None
    for timestamp, sample in samples:
        if timestamp > time:
            break
        value = sample
    return value
