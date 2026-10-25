"""Wiring contracts and independent pulse/trigger capture tests."""

import unittest

from mcs51_studio.engine.assembler import assemble
from mcs51_studio.engine.cpu import CPU
from mcs51_studio.hardware.analyzer import LogicCapture, held_value, port_mask
from mcs51_studio.hardware.board import Board
from mcs51_studio.hardware.wiring import (
    DEVICES,
    PINOUT,
    built_in_presets,
    connections,
    shared_connections,
    validate_preset,
)


class InstrumentsTests(unittest.TestCase):
    def test_pinout(self):
        self.assertEqual(set(PINOUT), set(range(1, 41)))
        self.assertEqual(
            (PINOUT[10], PINOUT[17], PINOUT[32], PINOUT[39]),
            ("P3.0", "P3.7", "P0.7", "P0.0"),
        )
        self.assertEqual(
            len({p for p in PINOUT.values() if p.startswith("P") and "." in p}), 32
        )

    def test_sharing_tracks_enabled_devices_and_remapping(self):
        board = Board(CPU())
        text = "\n".join(shared_connections(board))
        self.assertIn("Display and LED Bank share P1.0", text)
        self.assertIn("Both devices observe", text)
        board.enabled["display"] = False
        self.assertNotIn("Display and LED Bank", "\n".join(shared_connections(board)))
        board.enabled["uart"] = True
        text = "\n".join(shared_connections(board))
        self.assertIn("Motor and UART share", text)
        self.assertIn("pull these lines low", text)
        board.mapping["uart_tx"], board.mapping["uart_rx"] = ["P2.0"], ["P2.1"]
        self.assertNotIn("Motor and UART", "\n".join(shared_connections(board)))
        self.assertNotIn(("keypad", "key_gate", 0), connections(board).get("P3.3", []))
        board.key_gate = True
        self.assertIn(("keypad", "key_gate", 0), connections(board)["P3.3"])

    def test_same_device_signal_aliases_are_explained(self):
        board = Board(CPU())
        board.mapping["display_select"] = ["P3.3", "P3.3"]
        self.assertIn(
            "Display has multiple signals mapped to P3.3",
            "\n".join(shared_connections(board)),
        )

    def test_presets_are_complete_and_independent(self):
        presets = built_in_presets()
        for data in presets.values():
            self.assertEqual(set(data["enabled"]), set(DEVICES))
            self.assertEqual(validate_preset(data), data)
        presets["LED Counter"]["mapping"]["leds"][0] = "P0.0"
        self.assertEqual(presets["Timer / PWM"]["mapping"]["leds"][0], "P1.0")
        self.assertEqual(
            built_in_presets()["LED Counter"]["mapping"]["leds"][0], "P1.0"
        )

    def test_invalid_presets_are_rejected(self):
        for bad in (None, {}, {"mapping": {}}, {"mapping": None}):
            with self.assertRaises((ValueError, TypeError)):
                validate_preset(bad)
        for value in ("P4.0", "P0.8", "P0.0 trailing", 42):
            data = built_in_presets()["LED Counter"]
            data["mapping"]["leds"][0] = value
            with self.assertRaises(ValueError):
                validate_preset(data)
        data = built_in_presets()["LED Counter"]
        data["enabled"]["leds"] = "false"
        with self.assertRaises(ValueError):
            validate_preset(data)

    def test_rising_falling_and_either_triggers(self):
        for edge, initial, changed in [
            ("Rising", 0, 1),
            ("Falling", 1, 0),
            ("Either", 0, 1),
            ("Either", 1, 0),
        ]:
            capture = LogicCapture()
            capture.arm(0, initial, "P0.0", edge, 10)
            capture.sample(2, initial)
            self.assertEqual(capture.state, "Armed")
            capture.sample(3, changed)
            self.assertEqual((capture.state, capture.trigger_time), ("Capturing", 3))
            capture.sample(12, changed)
            self.assertEqual(capture.state, "Capturing")
            capture.sample(13, changed)
            self.assertEqual(capture.state, "Complete")
            capture.sample(15, initial)
            self.assertEqual(capture.end, 13)

    def test_trigger_ignores_other_pins_and_wrong_edge(self):
        capture = LogicCapture()
        capture.arm(0, 1, "P0.0", "Rising")
        capture.sample(1, 3)
        capture.sample(2, 2)
        self.assertEqual(capture.state, "Armed")
        capture.sample(3, 3)
        self.assertEqual(capture.trigger_time, 3)

    def test_pulse_measurements(self):
        capture = LogicCapture()
        capture.arm(0, 0, duration=100)
        for time, value in [(10, 1), (14, 0), (20, 1), (24, 0), (30, 1), (35, 1)]:
            capture.sample(time, value)
        metrics = capture.measurements("P0.0")
        self.assertEqual(
            metrics,
            {
                "high_us": 4,
                "low_us": 6,
                "period_us": 10,
                "frequency_hz": 100000,
                "duty_percent": 40,
            },
        )
        self.assertEqual(capture.measurements("P0.0", 15, 25), {"high_us": 4})
        self.assertEqual(capture.measurements("P0.1"), {})
        self.assertEqual(held_value(list(capture.samples), 12), 1)
        self.assertIsNone(held_value(list(capture.samples), -1))

    def test_bounded_capture_and_pretrigger(self):
        capture = LogicCapture(capacity=8)
        capture.arm(0, 0, "P0.1", "Rising")
        for time in range(1, 100):
            capture.sample(time, time % 2)
        self.assertLessEqual(len(capture.samples), 4)
        capture.sample(100, 2)
        self.assertEqual(capture.trigger_time, 100)
        for time in range(101, 120):
            capture.sample(time, time % 2 | 2)
        self.assertEqual(capture.state, "Buffer Full")
        self.assertEqual(len(capture.samples), 8)

    def test_same_timestamp_stop_and_reset(self):
        capture = LogicCapture()
        capture.arm(0, 0)
        capture.sample(0, 1)
        self.assertEqual(list(capture.samples), [(0, 1)])
        capture.stop()
        capture.sample(1, 0)
        self.assertEqual(capture.end, 0)
        capture.arm(10, 0)
        capture.sample(0, 1)
        self.assertEqual((capture.state, len(capture.samples)), ("Idle", 0))

    def test_instruction_capture_is_independent_of_ui_batch(self):
        cpu = CPU()
        board = Board(cpu)
        capture = LogicCapture()
        cpu.code[:] = assemble(
            "CLR P1.0\nLOOP: SETB P1.0\nNOP\nCLR P1.0\nSJMP LOOP"
        ).code
        capture.arm(0, port_mask(cpu), duration=100)
        board.on_sample = lambda: capture.sample(cpu.cycles, port_mask(cpu))
        for _ in range(30):
            cpu.step()
            board.update()
        metric = capture.measurements("P1.0")
        self.assertEqual(
            (
                metric["high_us"],
                metric["low_us"],
                metric["period_us"],
                metric["duty_percent"],
            ),
            (2, 3, 5, 40),
        )
        board.switches[0] = False
        board.update()
        self.assertEqual(port_mask(cpu) >> 16 & 1, 0)
