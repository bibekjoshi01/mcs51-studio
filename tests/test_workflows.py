"""Headless integration checks for complete simulator workflows."""

import unittest

from mcs51_studio.engine.assembler import AssemblyError, assemble, export_hex, import_hex
from mcs51_studio.hardware.board import Board
from mcs51_studio.hardware.lcd import LCD
from mcs51_studio.engine.cpu import CPU
from mcs51_studio.resources import LED_COUNTER


class SimulatorWorkflows(unittest.TestCase):
    def test_hex_round_trip(self):
        program = assemble(LED_COUNTER)
        restored = import_hex(export_hex(program))
        self.assertEqual(program.code, restored.code)
        self.assertEqual(program.used, restored.used)

    def test_led_counter_program(self):
        cpu = CPU()
        cpu.code[:] = assemble(LED_COUNTER).code
        board = Board(cpu)
        for _ in range(12000):
            cpu.step()
            board.update()
        self.assertLess(cpu.a, 255)
        self.assertLess(cpu.ram[0x90], 255)

    def test_invalid_programs(self):
        for source in (
            "MOV A,#256",
            "SJMP distant\nORG 300H\ndistant: NOP",
            "ORG 10000H",
        ):
            with self.subTest(source=source), self.assertRaises(AssemblyError):
                assemble(source)

    def test_adc_conversion(self):
        cpu = CPU()
        board = Board(cpu)
        board.enabled["adc"] = True
        board.analogue = 2.5
        cpu.write(0xB0, 0xBF)
        board.update()
        cpu.write(0xB0, 255)
        board.update()
        self.assertEqual(board.adc_remaining, 20)
        cpu.cycles += 20
        board.update()
        self.assertEqual(board.adc_value, 128)
        self.assertFalse(board.adc_intr)

    def test_switch_changes_input_pin(self):
        cpu = CPU()
        board = Board(cpu)
        board.switches[0] = False
        board.update()
        self.assertEqual(cpu.read(0xA0) & 1, 0)

    def test_lcd_write_and_clear(self):
        lcd = LCD()
        lcd.byte(0x0C, False)
        lcd.byte(0x80, False)
        for character in "HELLO":
            lcd.byte(ord(character), True)
        self.assertTrue(lcd.lines()[0].startswith("HELLO"))
        lcd.byte(1, False)
        self.assertEqual(lcd.lines()[0], " " * 16)

    def test_interrupt_and_return(self):
        cpu = CPU()
        cpu.write(0xA8, 0x82)
        cpu.set_bit(0x8D, 1)
        cpu.step()
        self.assertEqual((cpu.pc, cpu.ram[0x81]), (11, 9))
        cpu.code[11] = 0x32
        cpu.step()
        self.assertEqual((cpu.pc, cpu.ram[0x81]), (1, 7))
