"""Versioned, portable experiment documents. No executable project metadata."""

import json
import math
from dataclasses import asdict
from pathlib import Path

from .engine.cpu import CPU
from .engine.debugger import Debugger
from .hardware.analyzer import PINS
from .hardware.experiment import ExperimentSettings
from .hardware.uart import UARTEndpoint
from .hardware.wiring import validate_preset
from .source_files import write_source

PROCESSOR = {
    "profile": "classic-8051",
    "oscillator_hz": 12000000,
    "clocks_per_cycle": 12,
}
FIELDS = {
    "format",
    "version",
    "source",
    "processor",
    "wiring",
    "experiment",
    "inputs",
    "uart",
    "watches",
    "instruments",
}


def validate_project(data):
    if not isinstance(data, dict) or set(data) != FIELDS:
        raise ValueError(
            "Invalid project fields. Open a complete MCS51 Studio project."
        )
    if (
        data["format"] != "mcs51-studio"
        or type(data["version"]) is not int
        or data["version"] != 1
    ):
        raise ValueError("Unsupported project format or version.")
    if (
        data["processor"] != PROCESSOR
        or not isinstance(data["processor"], dict)
        or any(
            type(data["processor"].get(k)) is not type(v) for k, v in PROCESSOR.items()
        )
    ):
        raise ValueError(
            "Unsupported processor or clock. Choose Classic 8051, 12 MHz, 12 clocks per cycle."
        )
    if (
        not isinstance(data["source"], str)
        or len(data["source"].encode("utf-8")) > 524288
    ):
        raise ValueError("Project source must be text, at most 512 KB.")
    if not isinstance(data["wiring"], dict) or set(data["wiring"]) != {
        "mapping",
        "enabled",
        "key_gate",
    }:
        raise ValueError(
            "Project wiring must include mapping, enabled devices, and keypad gate."
        )
    wiring = validate_preset(data["wiring"])
    experiment = ExperimentSettings.validated(data["experiment"])
    inputs = data["inputs"]
    if not isinstance(inputs, dict) or set(inputs) != {"switches", "analogue", "keys"}:
        raise ValueError("Invalid experiment inputs.")
    if (
        not isinstance(inputs["switches"], list)
        or len(inputs["switches"]) != 8
        or any(type(v) is not bool for v in inputs["switches"])
    ):
        raise ValueError("Eight switch states are required.")
    voltage = inputs["analogue"]
    if (
        type(voltage) not in (int, float)
        or not math.isfinite(voltage)
        or not 0 <= voltage <= 5
    ):
        raise ValueError("Analogue voltage must be from 0 to 5 V.")
    keys = inputs["keys"]
    if (
        not isinstance(keys, list)
        or len(keys) > 12
        or any(
            not isinstance(k, list)
            or len(k) != 2
            or any(type(v) is not int for v in k)
            or not 0 <= k[0] < 4
            or not 0 <= k[1] < 3
            for k in keys
        )
    ):
        raise ValueError("Invalid keypad state.")
    if len({tuple(k) for k in keys}) != len(keys) or (
        experiment.keypad_mode == "Radio" and len(keys) > 1
    ):
        raise ValueError("Keypad state conflicts with its selected mode.")
    uart = data["uart"]
    if (
        not isinstance(uart, dict)
        or set(uart) != {"baud", "parity", "data_bits", "stop_bits"}
        or any(type(v) is not int for v in uart.values())
    ):
        raise ValueError("Invalid UART framing.")
    UARTEndpoint().configure(**uart)
    instruments = data["instruments"]
    if not isinstance(instruments, dict) or set(instruments) != {
        "probes",
        "trigger",
        "edge",
        "duration",
    }:
        raise ValueError("Invalid instrument settings.")
    probes = instruments["probes"]
    if (
        not isinstance(probes, list)
        or not 1 <= len(probes) <= 8
        or any(not isinstance(p, str) or p not in PINS for p in probes)
        or len(set(probes)) != len(probes)
    ):
        raise ValueError("Choose 1–8 distinct port probes.")
    if (
        instruments["trigger"] not in ("Free Run", *PINS)
        or instruments["edge"] not in ("Rising", "Falling", "Either")
        or type(instruments["duration"]) is not int
        or instruments["duration"] not in (100, 1000, 10000, 100000)
    ):
        raise ValueError("Unsupported analyzer trigger or duration.")
    watches = data["watches"]
    if not isinstance(watches, list) or len(watches) > 64:
        raise ValueError("Invalid watch list.")
    debugger = Debugger(CPU())
    for watch in watches:
        if (
            not isinstance(watch, dict)
            or set(watch) != {"expression", "break_on_change"}
            or not isinstance(watch["expression"], str)
            or type(watch["break_on_change"]) is not bool
        ):
            raise ValueError("Invalid watch entry.")
        debugger.add_watch(watch["expression"], watch["break_on_change"])
    return {
        **data,
        "wiring": wiring,
        "experiment": asdict(experiment),
        "watches": [asdict(w) for w in debugger.watches],
    }


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate project field: {key}")
        result[key] = value
    return result


def read_project(path):
    path = Path(path)
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Project exceeds the 2 MB file limit.")
    try:
        data = json.loads(
            path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_fields
        )
        return validate_project(data)
    except (TypeError, KeyError, IndexError, UnicodeError, RecursionError) as error:
        raise ValueError(f"Invalid project: {error}") from error


def save_project(path, data):
    write_source(
        Path(path),
        json.dumps(validate_project(data), ensure_ascii=False, indent=2) + "\n",
    )
