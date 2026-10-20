"""Peripheral signal, timing, and assembled-program regression checks."""

import gzip
import json
import unittest
from pathlib import Path

from mcs51_studio.engine.assembler import assemble
from mcs51_studio.engine.cpu import CPU
from mcs51_studio.hardware.board import Board
from mcs51_studio.hardware.lcd import LCD
from mcs51_studio.hardware.uart import UARTEndpoint


class BoardBehavior(unittest.TestCase):
    def board(self, *enabled):
        cpu = CPU()
        board = Board(cpu)
        board.enabled = {name: name in enabled for name in board.enabled}
        return cpu, board

    def test_digital_outputs_against_reference(self):
        path = Path(__file__).with_name("fixtures") / "board-outputs.json.gz"
        with gzip.open(path, "rt") as stream:
            cases = json.load(stream)
        cpu, board = self.board("leds", "display")
        for case in cases:
            cpu.write(0x90, case["value"])
            cpu.write(0x80, case["cs"] << 7)
            cpu.write(0xB0, case["select"] << 3)
            board.update()
            self.assertEqual(board.led_mask, case["leds"], case)
            self.assertEqual(board.digits, case["digits"], case)

    def test_adc_against_reference(self):
        path = Path(__file__).with_name("fixtures") / "board-adc.json.gz"
        with gzip.open(path, "rt") as stream:
            cases = json.load(stream)
        for case in cases:
            step = case["step"]
            if step == 0:
                cpu, board = self.board("adc")
                board.analogue = case["input"] * 5 / 255
            cpu.write(0xB0, 191 if step == 0 else 63 if step == 23 else 127)
            if step == 24:
                board.enabled["adc"] = False
            if 2 <= step <= 21:
                cpu.cycles += 1
            board.update()
            self.assertEqual(board.adc_value, case["value"], case)
            self.assertEqual(cpu.read(0xB0), case["pins3"], case)
            # Disabled hardware must release its bus, even if the reference
            # leaves its last output driving the pins until the next read.
            self.assertEqual(cpu.read(0xA0), 255 if step == 24 else case["pins2"], case)

    def test_blink_program_cycle_trace_and_mapping(self):
        cpu, board = self.board("leds")
        cpu.code[:] = assemble("CLR P1.0\nCPL P1.0\nCPL P1.0\nSETB P1.0").code
        trace = []
        for _ in range(4):
            cpu.step()
            board.update()
            trace.append((cpu.cycles, board.led_mask))
        self.assertEqual(trace, [(1, 1), (2, 0), (3, 1), (4, 0)])
        board.mapping["leds"] = [f"P2.{bit}" for bit in reversed(range(8))]
        cpu.write(0xA0, 0x7F)
        board.update()
        self.assertEqual(board.led_mask, 1)
        board.enabled["leds"] = False
        self.assertEqual(board.led_mask, 0)

    def test_counter_trace_against_reference(self):
        from mcs51_studio.resources import LED_COUNTER

        cpu, board = self.board("leds")
        cpu.code[:] = assemble(LED_COUNTER).code
        transitions, previous = [], 0
        for instruction in range(1, 30001):
            cpu.step()
            board.update()
            if board.led_mask != previous:
                transitions.append([instruction, cpu.cycles, board.led_mask])
                previous = board.led_mask
        path = Path(__file__).with_name("fixtures") / "led-counter-trace.json"
        self.assertEqual(transitions, json.loads(path.read_text()))

    def test_port_latch_read_modify_write(self):
        cpu, board = self.board("switches")
        board.mapping["switches"][0] = "P1.0"
        board.switches[0] = False
        board.update()
        self.assertEqual(cpu.bit(0x90), 0)
        cpu.execute(0xB2, 0x90)  # CPL reads the latch, not the held-low pin.
        self.assertEqual(cpu.ram[0x90], 254)
        cpu.execute(0xB2, 0x90)
        self.assertEqual(cpu.ram[0x90], 255)
        cpu.pc = 0
        cpu.execute(0x10, 0x90, 5)  # JBC tests/clears the latch.
        self.assertEqual((cpu.pc, cpu.ram[0x90]), (8, 254))
        cpu.execute(0xE5, 0x90)  # MOV reads effective pin levels.
        self.assertEqual(cpu.a, 254)

    def test_switches_all_bits_release_and_latch(self):
        cpu, board = self.board("switches")
        for pattern in range(256):
            board.switches = [bool(pattern & 1 << bit) for bit in range(8)]
            board.update()
            self.assertEqual(cpu.read(0xA0), pattern)
            self.assertEqual(cpu.ram[0xA0], 255)
        cpu.write(0xA0, 0)
        board.update()
        self.assertEqual(cpu.read(0xA0), 0)
        cpu.write(0xA0, 255)
        board.enabled["switches"] = False
        board.update()
        self.assertEqual(cpu.read(0xA0), 255)

    def test_keypad_each_key_and_connected_group(self):
        cpu, board = self.board("keypad")
        for row in range(4):
            for column in range(3):
                cpu.write(0x80, 255 ^ (1 << (column + 4)))
                board.keys = {(row, column)}
                board.update()
                self.assertFalse(cpu.read(0x80) & 1 << row)
                board.keys.clear()
                board.update()
                self.assertTrue(cpu.read(0x80) & 1 << row)
        cpu.write(0x80, 0xEF)
        board.keys = {(0, 0), (0, 1), (1, 1), (1, 2), (2, 2)}
        board.key_gate = True
        board.update()
        self.assertEqual(cpu.read(0x80) & 0x77, 0)
        self.assertEqual(cpu.bit(0xB3), 0)
        board.enabled["keypad"] = False
        board.update()
        self.assertEqual(cpu.bit(0xB3), 1)

    def test_adc_restart_releases_interrupt_immediately(self):
        cpu, board = self.board("adc")
        for _ in range(2):
            cpu.write(0xB0, 0xBF)
            board.update()
            cpu.write(0xB0, 255)
            board.update()
            self.assertEqual(cpu.bit(0xB2), 1)
            self.assertEqual(board.adc_remaining, 20)
            cpu.cycles += 20
            board.update()
            self.assertEqual(cpu.bit(0xB2), 0)
        board.enabled["adc"] = False
        board.update()
        self.assertEqual((board.adc_remaining, cpu.bit(0xB2)), (0, 1))

    def test_dac_hold_scope_and_comparator(self):
        cpu, board = self.board("dac", "comparator")
        cpu.write(0x80, 0x7F)
        cpu.write(0x90, 128)
        board.update()
        self.assertEqual(board.dac_value, 128)
        threshold = 128 * 5 / 255
        for voltage, expected in (
            (threshold - 0.01, 0),
            (threshold, 0),
            (threshold + 0.01, 1),
        ):
            board.analogue = voltage
            board.update()
            self.assertEqual(cpu.bit(0xB7), expected)
        cpu.write(0x80, 255)
        cpu.write(0x90, 0)
        cpu.cycles += 4
        board.update()
        self.assertEqual(board.dac_value, 128)
        self.assertEqual(list(board.scope), [(0, threshold), (4, threshold)])
        board.analogue = 0
        board.enabled["adc"] = True
        board.update()
        self.assertEqual(cpu.bit(0xB7), 1)

    def test_motor_direction_sensor_and_disable(self):
        cpu, board = self.board("motor")
        cpu.write(0xB0, 0xFD)
        for position in (3, 4, 5, 6, 7, 0):
            cpu.cycles += 7
            board.update()
            self.assertEqual(board.motor_position, position)
            self.assertEqual(cpu.bit(0xB5), int(position != 0))
        cpu.write(0xB0, 0xFE)
        cpu.cycles += 7
        board.update()
        self.assertEqual((board.motor_position, board.motor_direction), (7, -1))
        board.enabled["motor"] = False
        cpu.cycles += 7
        board.update()
        self.assertEqual(
            (board.motor_position, board.motor_direction, cpu.bit(0xB5)), (7, 0, 1)
        )

    def test_lcd_four_bit_bus_and_disable(self):
        cpu, board = self.board("lcd")

        def nibble(value, rs=0):
            cpu.write(0x90, value | rs << 3 | 4)
            board.update()
            cpu.write(0x90, value | rs << 3)
            board.update()

        def byte(value, rs=0):
            nibble(value & 240, rs)
            nibble((value & 15) << 4, rs)

        nibble(0x20)
        byte(0x28)
        byte(0x0C)
        byte(0x80)
        for char in "HELLO":
            byte(ord(char), 1)
        self.assertEqual(board.lcd.lines()[0], "HELLO           ")
        board.enabled["lcd"] = False
        byte(ord("!"), 1)
        self.assertEqual(board.lcd.lines()[0], "HELLO           ")

    def test_lcd_address_wrap_and_clear_from_cgram(self):
        lcd = LCD()
        lcd.byte(0x0C, 0)
        lcd.byte(0xA7, 0)
        lcd.byte(ord("X"), 1)
        self.assertEqual(lcd.address, 0x40)
        lcd.byte(ord("Y"), 1)
        self.assertEqual(lcd.lines()[1][0], "Y")
        lcd.byte(0x18, 0)
        lcd.byte(0x1C, 0)
        self.assertEqual(lcd.lines()[1][0], "Y")
        lcd.byte(0x40, 0)
        lcd.byte(0x1F, 1)
        lcd.byte(1, 0)
        lcd.byte(ord("A"), 1)
        self.assertEqual(lcd.lines()[0][0], "A")
        self.assertEqual(lcd.cgram[0], 31)
        lcd.byte(7, 0)
        lcd.byte(ord("B"), 1)
        self.assertEqual(lcd.shift, 1)

    def test_uart_all_bytes_and_parity(self):
        for parity in range(3):
            for value in range(256 if parity == 0 else 128):
                tx, rx = UARTEndpoint(), UARTEndpoint()
                tx.configure(19200, parity)
                rx.configure(19200, parity)
                tx.start("{%02X}" % value)
                for _ in range(tx.period * 12):
                    tx.pulse(1)
                    rx.pulse(tx.tx_line)
                self.assertEqual(rx.received, [value], (parity, value))

    def test_uart_board_wiring(self):
        cpu, board = self.board("uart")
        board.uart.configure(19200)
        board.receive("{55}")
        bits = []
        for _ in range(board.uart.period * 11):
            cpu.cycles += 1
            board.update()
            bits.append(cpu.bit(0xB0))
        self.assertIn(0, bits)
        self.assertEqual(cpu.ram[0xB0], 255)
        board.enabled["uart"] = False
        board.update()
        self.assertEqual(cpu.bit(0xB0), 1)

    def test_uart_queued_sends_and_parity_mask(self):
        uart = UARTEndpoint()
        uart.start("{41}")
        uart.start("{42}")
        self.assertEqual(uart.pending, [65, 66])
        for parity in (1, 2):
            uart.configure(4800, parity)
            for value in range(256):
                encoded = uart.parity_byte(value)
                self.assertEqual(encoded & 127, value & 127)
                self.assertEqual(encoded.bit_count() % 2, 1 if parity == 1 else 0)
        with self.assertRaises(ValueError):
            uart.configure(0)
