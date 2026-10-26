"""Portable document validation and atomic recovery-file storage."""

import copy
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from mcs51_studio.engine.cpu import CPU
from mcs51_studio.hardware.board import Board
from mcs51_studio.project import PROCESSOR, read_project, save_project, validate_project


def document():
    board = Board(CPU())
    return {
        "format": "mcs51-studio",
        "version": 1,
        "source": "; portable ✓\nMOV A,#42H\n",
        "processor": dict(PROCESSOR),
        "wiring": {
            "mapping": board.mapping,
            "enabled": board.enabled,
            "key_gate": True,
        },
        "experiment": asdict(board.experiment),
        "inputs": {"switches": [False, True] * 4, "analogue": 2.75, "keys": [[0, 1]]},
        "uart": {"baud": 9600, "parity": 2, "data_bits": 8, "stop_bits": 2},
        "instruments": {
            "probes": ["P1.0", "P3.2"],
            "trigger": "P3.2",
            "edge": "Falling",
            "duration": 10000,
        },
        "watches": [{"expression": "XDATA[1234]", "break_on_change": True}],
    }


class PortableProjects(unittest.TestCase):
    def test_unicode_roundtrip_in_arbitrary_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Lesson One.mcs51"
            data = document()
            save_project(path, data)
            self.assertEqual(read_project(path), data)
            self.assertNotIn(str(folder), path.read_text())
            self.assertEqual(set(Path(folder).iterdir()), {path})

    def test_reject_unsupported_or_ambiguous_settings(self):
        cases = [
            (["version"], 2),
            (["processor", "profile"], "8052"),
            (["processor", "oscillator_hz"], 24000000),
            (["processor", "clocks_per_cycle"], 12.0),
            (["inputs", "analogue"], float("nan")),
            (["inputs", "analogue"], 5.1),
            (["inputs", "switches"], [True]),
            (["inputs", "keys"], [[4, 0]]),
            (["inputs", "keys"], [[0, 1], [0, 1]]),
            (["uart", "data_bits"], 9),
            (["uart", "baud"], 12345),
            (["uart", "parity"], True),
            (["experiment", "keypad_mode"], "Magic"),
            (["experiment", "bounce_us"], 0),
            (["watches"], [{"expression": "RAM[80]", "break_on_change": True}]),
            (["wiring", "mapping", "leds"], ["P9.0"] * 8),
            (["source"], 42),
        ]
        for keys, value in cases:
            with self.subTest(keys=keys, value=value):
                data = document()
                field = data
                for key in keys[:-1]:
                    field = field[key]
                field[keys[-1]] = value
                with self.assertRaises(ValueError):
                    validate_project(data)
        data = document()
        data["experiment"]["keypad_mode"] = "Radio"
        data["inputs"]["keys"] = [[0, 0], [1, 1]]
        with self.assertRaises(ValueError):
            validate_project(data)

    def test_missing_unknown_and_malformed_files(self):
        for key in document():
            data = document()
            del data[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_project(data)
        data = document()
        data["run_shell"] = "echo nope"
        with self.assertRaises(ValueError):
            validate_project(data)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.mcs51"
            for contents in [
                "{",
                "[]",
                "null",
                '{"version":1,"version":2}',
                "[" * 1500 + "]" * 1500,
                json.dumps({"version": 1}),
                " " * 2097153,
            ]:
                path.write_text(contents)
                with self.assertRaises(ValueError):
                    read_project(path)

    def test_failed_replace_preserves_previous_document(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "recovery.mcs51"
            before = document()
            save_project(path, before)
            after = copy.deepcopy(before)
            after["source"] = "NOP"
            with patch(
                "mcs51_studio.source_files.os.replace",
                side_effect=OSError("disk unavailable"),
            ):
                with self.assertRaises(OSError):
                    save_project(path, after)
            self.assertEqual(read_project(path), before)
            self.assertEqual(set(Path(folder).iterdir()), {path})


if __name__ == "__main__":
    unittest.main()
