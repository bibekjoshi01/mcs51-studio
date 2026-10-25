"""Wiring metadata, experiment presets, and shared-signal explanations."""

import re
from collections import defaultdict
from itertools import combinations

from .board import DEFAULT_MAPPING

DEVICES = {
    "leds": ("LED Bank", ("leds",)),
    "switches": ("Switch Bank", ("switches",)),
    "display": ("Display", ("segments", "display_cs", "display_select")),
    "keypad": ("Keypad", ("key_rows", "key_columns", "key_gate")),
    "adc": ("ADC", ("adc_data", "adc_rd", "adc_wr", "adc_intr")),
    "dac": ("DAC", ("dac_data", "dac_wr")),
    "motor": ("Motor", ("motor_control", "motor_sensor")),
    "comparator": ("Comparator", ("comparator_output",)),
    "uart": ("UART", ("uart_tx", "uart_rx")),
    "lcd": ("LCD", ("lcd_data", "lcd_rs", "lcd_e")),
}
DRIVERS = {
    "switches",
    "adc_data",
    "adc_intr",
    "motor_sensor",
    "comparator_output",
    "uart_tx",
    "key_rows",
    "key_columns",
    "key_gate",
}
PRESET_DEVICES = {
    "LED Counter": ("leds",),
    "Switch Input": ("leds", "switches"),
    "Multiplexed Display": ("display",),
    "Keypad Scan": ("keypad",),
    "ADC Sampling": ("adc",),
    "DAC Waveform": ("dac",),
    "UART Link": ("uart",),
    "Timer / PWM": ("leds",),
    "LCD Text": ("lcd",),
    "Motor Control": ("motor",),
}


def validate_preset(data):
    """Validate the entire preset before changing any live board state."""
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("mapping"), dict)
        or set(data["mapping"]) != set(DEFAULT_MAPPING)
    ):
        raise ValueError("Preset must include every wiring role.")
    mapping = {}
    for role, default in DEFAULT_MAPPING.items():
        pins = data["mapping"][role]
        if not isinstance(pins, list) or len(pins) != len(default):
            raise ValueError(f"Incorrect pin count for {role}.")
        if any(
            not isinstance(p, str) or not re.fullmatch(r"P[0-3]\.[0-7]", p.upper())
            for p in pins
        ):
            raise ValueError("Pins must be P0.0 through P3.7.")
        mapping[role] = [p.upper() for p in pins]
    enabled = data.get("enabled")
    if (
        not isinstance(enabled, dict)
        or set(enabled) != set(DEVICES)
        or any(type(v) is not bool for v in enabled.values())
    ):
        raise ValueError("Preset must include every device enable state.")
    gate = data.get("key_gate", False)
    if type(gate) is not bool:
        raise ValueError("Invalid keypad gate state.")
    return {"mapping": mapping, "enabled": dict(enabled), "key_gate": gate}


def built_in_presets():
    return {
        name: validate_preset(
            {"mapping": DEFAULT_MAPPING, "enabled": {d: d in devices for d in DEVICES}}
        )
        for name, devices in PRESET_DEVICES.items()
    }


def connections(board):
    result = defaultdict(list)
    for device, (_, roles) in DEVICES.items():
        if not board.enabled[device]:
            continue
        for role in roles:
            if role == "key_gate" and not board.key_gate:
                continue
            for index, pin in enumerate(board.mapping[role]):
                result[pin].append((device, role, index))
    return dict(result)


def shared_connections(board):
    """Group shared pins by device pair, distinguishing loads from drivers."""
    pairs = defaultdict(set)
    driven = set()
    for pin, endpoints in connections(board).items():
        for left, right in combinations(endpoints, 2):
            if left[0] == right[0]:
                continue
            pair = tuple(sorted((left[0], right[0])))
            pairs[pair].add(pin)
            if left[1] in DRIVERS or right[1] in DRIVERS:
                driven.add(pair)
    messages = []
    aliases = defaultdict(set)
    for pin, endpoints in connections(board).items():
        for device in {endpoint[0] for endpoint in endpoints}:
            signals = [
                (role, index) for owner, role, index in endpoints if owner == device
            ]
            if len(signals) > 1 and device != "lcd":
                aliases[device].add(pin)
    for device, pins in sorted(aliases.items()):
        messages.append(
            DEVICES[device][0]
            + " has multiple signals mapped to "
            + ", ".join(sorted(pins))
            + ". These signals cannot be controlled or read independently; check the experiment wiring."
        )
    for pair, pins in sorted(pairs.items()):
        names = [DEVICES[d][0] for d in pair]
        location = ", ".join(sorted(pins))
        consequence = (
            "An input device can pull these lines low, changing reads and other connected devices. Release the MCU latch high before reading; disable or remap unused devices."
            if pair in driven
            else "Both devices observe the same output writes. Activity intended for one can appear on the other; use chip-select controls or disable/remap the unused device."
        )
        messages.append(f"{names[0]} and {names[1]} share {location}. {consequence}")
    if board.enabled["adc"] and board.enabled["comparator"]:
        messages.append(
            "ADC takes precedence: the comparator is inactive while ADC is enabled, even if remapped."
        )
    if board.enabled["lcd"]:
        overlap = set(board.mapping["lcd_data"]) & set(
            board.mapping["lcd_rs"] + board.mapping["lcd_e"]
        )
        if overlap:
            messages.append(
                "LCD data and control share "
                + ", ".join(sorted(overlap))
                + ". Use the supported 4-bit wiring sequence or remap control pins for an 8-bit bus."
            )
    return messages


# Classic 8051 40-pin DIP, viewed from above. Non-port pins are labels only.
PINOUT = {
    **{i + 1: f"P1.{i}" for i in range(8)},
    9: "RST",
    **{i + 10: f"P3.{i}" for i in range(8)},
    18: "XTAL2",
    19: "XTAL1",
    20: "GND",
    **{i + 21: f"P2.{i}" for i in range(8)},
    29: "PSEN",
    30: "ALE",
    31: "EA",
    **{39 - i: f"P0.{i}" for i in range(8)},
    40: "VCC",
}
ALTERNATE = dict(
    zip(
        (f"P3.{i}" for i in range(8)),
        ("RXD", "TXD", "INT0", "INT1", "T0", "T1", "WR", "RD"),
    )
)
