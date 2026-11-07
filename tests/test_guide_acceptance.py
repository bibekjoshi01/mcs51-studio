"""Independent acceptance checks derived from the EdSim51 user's guide.

Source: https://edsim51.com/users-guide-2/ (reviewed 2026-11-07).
Programs exercise the public assembler, CPU, and board together.
"""

import unittest

from mcs51_studio.engine.assembler import assemble, export_hex, import_hex
from mcs51_studio.engine.cpu import CPU
from mcs51_studio.hardware.board import Board
from mcs51_studio.hardware.experiment import ExperimentSettings
from mcs51_studio.hardware.lcd import LCD
from mcs51_studio.hardware.uart import UARTEndpoint


class GuideAcceptance(unittest.TestCase):
    def machine(self, source, *devices):
        program = assemble(source)
        cpu = CPU()
        cpu.code[:] = program.code
        board = Board(cpu)
        board.enabled = {name: name in devices for name in board.enabled}
        board.update()
        return cpu, board

    def steps(self, cpu, board, count):
        for _ in range(count):
            cpu.step()
            board.update()

    def test_assembler_directives_aliases_and_number_formats(self):
        program = assemble(
            "value EQU 1234H\ncount SET 10\nUSING 2\nORG 30H\n"
            "start: mov AR3,#count\nMOV DPTR,#value\n"
            "MOV A,#HIGH(value)\nMOV B,#LOW(value)\n"
            "count SET 1010B\nMOV P1,#count\nMOV P2,#0x0a\n"
            "SETB CY\nCALL sub\nJMP done\nsub: INC A\nRET\n"
            "done: SJMP done\nEND\nMOV A,#99"
        )
        cpu = CPU()
        cpu.code[:] = program.code
        cpu.pc = 0x30
        for _ in range(12):
            cpu.step()
        self.assertEqual(cpu.ram[0x13], 10)
        self.assertEqual(cpu.dptr, 0x1234)
        self.assertEqual(cpu.a, 0x13)
        self.assertEqual(cpu.ram[0xF0], 0x34)
        self.assertEqual((cpu.ram[0x90], cpu.ram[0xA0]), (10, 10))
        self.assertEqual(cpu.carry, 1)
        self.assertEqual(cpu.pc, program.symbols["DONE"])
        restored = import_hex(export_hex(program))
        self.assertEqual(restored.used, program.used)
        self.assertEqual(restored.code, program.code)

    def test_keypad_interrupt_uses_columns_with_no_false_row_interrupt(self):
        cpu, board = self.machine("SJMP $", "keypad")
        board.key_gate = True
        # All rows low is the documented idle configuration for interrupt input.
        cpu.write(0x80, 0xF0)
        board.update()
        self.assertEqual(cpu.bit(0xB3), 1, "No key must leave INT1 high")
        for row in range(4):
            for column in range(3):
                with self.subTest(row=row, column=column):
                    board.keys = {(row, column)}
                    board.update()
                    self.assertEqual(cpu.bit(0xB3), 0)
                    self.assertFalse(cpu.read(0x80) & (1 << (column + 4)))
                    board.keys.clear()
                    board.update()
                    self.assertEqual(cpu.bit(0xB3), 1)
        # A column driven low must assert the gate even with every row released.
        cpu.write(0x80, 0xEF)
        board.update()
        self.assertEqual(cpu.bit(0xB3), 0)
        board.key_gate = False
        board.update()
        self.assertEqual(cpu.bit(0xB3), 1)

    def test_keypad_interrupt_executes_handler_and_returns(self):
        cpu, board = self.machine(
            "LJMP main\nORG 13H\nINC A\nRETI\nORG 30H\n"
            "main: MOV P0,#0F0H\nSETB IT1\nMOV IE,#84H\nwait: SJMP wait",
            "keypad",
        )
        board.key_gate = True
        self.steps(cpu, board, 8)
        self.assertEqual(cpu.a, 0)
        board.keys.add((2, 1))
        board.update()
        self.steps(cpu, board, 8)
        self.assertEqual(cpu.a, 1)
        self.assertEqual(cpu.ram[0x81], 7)
        self.assertFalse(cpu.interrupt_stack)

    def test_adc_tristate_shared_switches_and_completion(self):
        cpu, board = self.machine(
            "CLR P3.6\nSETB P3.6\nwait: JB P3.2,wait\n"
            "CLR P3.7\nMOV A,P2\nSETB P3.7\nMOV B,P2\nSJMP $",
            "adc",
            "switches",
        )
        board.analogue = 2.5
        board.switches[7] = False
        self.steps(cpu, board, 30)
        self.assertEqual(board.adc_value, 128)
        self.assertEqual(cpu.a, 0, "A closed switch must override the ADC bit")
        self.assertEqual(cpu.ram[0xF0], 0x7F, "RD high must release the ADC bus")
        self.assertEqual(cpu.bit(0xB2), 0)
        board.enabled["adc"] = False
        board.update()
        self.assertEqual(cpu.bit(0xB2), 1)

    def test_dac_display_selection_hold_and_comparator(self):
        cpu, board = self.machine(
            "CLR P0.7\nMOV P1,#128\nSETB P0.7\nMOV P1,#0C0H\nSJMP $",
            "leds",
            "display",
            "dac",
            "comparator",
        )
        board.analogue = 2.0
        self.steps(cpu, board, 4)
        self.assertEqual(board.dac_value, 128)
        self.assertEqual(board.led_mask, 0x3F)
        self.assertEqual(board.digits, [255, 255, 255, 0xC0])
        self.assertEqual(cpu.bit(0xB7), 0)
        for selected in range(4):
            cpu.write(0xB0, (0xFF & ~0x18) | selected << 3)
            board.update()
            self.assertEqual(board.digits[selected], 0xC0)
            self.assertEqual(sum(value != 255 for value in board.digits), 1)
        board.analogue = 3.0
        board.update()
        self.assertEqual(cpu.bit(0xB7), 1)

    def test_lcd_eight_bit_bus_after_remapping(self):
        cpu, board = self.machine("SJMP $", "lcd")
        board.mapping["lcd_rs"] = ["P2.0"]
        board.mapping["lcd_e"] = ["P2.1"]
        board.experiment.lcd_timing = False
        cpu.write(0xA0, 0)
        board.update()

        def send(value, rs=0):
            cpu.write(0x90, value)
            cpu.write(0xA0, rs | 2)
            board.update()
            cpu.write(0xA0, rs)
            board.update()

        for command in (0x38, 0x0F, 0x80):
            send(command)
        for character in "HELLO":
            send(ord(character), 1)
        send(0xC0)
        send(ord("!"), 1)
        self.assertEqual(board.lcd.lines(), ["HELLO           ", "!               "])
        self.assertEqual(board.lcd.cursor_cell(), (1, 1))
        self.assertTrue(board.lcd.blink)
        self.assertFalse(board.lcd.four_bit)

    def test_lcd_entry_shift_does_not_shift_when_writing_cgram(self):
        lcd = LCD()
        lcd.byte(0x0C, 0)
        lcd.byte(0x07, 0)
        lcd.byte(0x40, 0)
        pattern = (0, 16, 8, 4, 2, 1, 0, 0)
        for row in pattern:
            lcd.byte(row, 1)
        self.assertEqual(lcd.shift, 0)
        self.assertEqual(lcd.glyph(0), pattern)
        lcd.byte(0x80, 0)
        lcd.byte(0, 1)
        self.assertEqual(lcd.shift, 1)
        lcd.byte(2, 0)
        self.assertEqual(lcd.cursor_cell(), (0, 0))

    def test_lcd_reports_unsupported_function_set_and_recovers(self):
        lcd = LCD()
        for command in (0x20, 0x30, 0x2C, 0x3C):
            lcd.byte(command, 0)
            self.assertIn("2 lines", lcd.configuration_error)
        for command in (0x28, 0x38):
            lcd.byte(command, 0)
            self.assertEqual(lcd.configuration_error, "")

    def test_motor_sensor_counts_revolutions_with_timer_one(self):
        cpu, board = self.machine("MOV TMOD,#50H\nSETB TR1\nCLR P3.1\nSJMP $", "motor")
        self.steps(cpu, board, 120)
        self.assertEqual(cpu.ram[0x8B], 4)
        self.assertEqual(board.motor_direction, 1)
        board.enabled["motor"] = False
        board.update()
        self.assertEqual(board.motor_direction, 0)
        self.assertEqual(cpu.bit(0xB5), 1)

    def test_uart_documented_text_hex_escape_and_validation(self):
        uart = UARTEndpoint()
        for text, expected in (
            ("abc", [0x61, 0x62, 0x63, 0x0D]),
            ("{56, 3a, 23, e7}", [0x56, 0x3A, 0x23, 0xE7]),
            (r"\{56, 3a}", list(b"{56, 3a}\r")),
        ):
            uart.reset_link()
            uart.start(text)
            self.assertEqual(uart.pending, expected)
        for invalid in ("{100}", "{-1}", "{GG}", "{12,}", "{12", "😊"):
            with self.subTest(invalid=invalid):
                previous = list(uart.pending)
                with self.assertRaises(ValueError):
                    uart.start(invalid)
                self.assertEqual(uart.pending, previous)

    def test_keypad_modes_and_bounce_follow_simulated_time(self):
        cpu, board = self.machine("SJMP $", "keypad")
        self.assertEqual(board.experiment.keypad_mode, "Standard")
        board.experiment.keypad_bounce = True
        cpu.write(0x80, 0xF0)
        board.key_event((0, 0), True)
        board.key_event((0, 0), False)
        for cycle, closed in (
            (0, False),
            (3000, True),
            (6000, False),
            (29999, True),
            (30000, True),
        ):
            cpu.cycles = cycle
            board.update()
            self.assertEqual(not bool(cpu.read(0x80) & 0x10), closed)
            before = cpu.read(0x80)
            for _ in range(10):
                board.update()
            self.assertEqual(cpu.read(0x80), before, "Pause must also pause bounce")
        self.assertFalse(board.stimulus.key_bounces)
        for mode in ("Pulse", "Radio"):
            board.set_keypad_mode(mode)
            self.assertFalse(board.keys)
            board.key_event((1, 1), True)
            board.update()
            self.assertIn((1, 1), board.key_contacts())
            self.assertFalse(board.stimulus.key_bounces)
            board.key_event((1, 1), False)
        board.key_event((2, 2), True)
        board.key_event((2, 2), False)
        self.assertEqual(board.keys, {(2, 2)})

    def test_motor_speed_and_legacy_experiment_settings(self):
        cycles_for_revolution = []
        for speed in (100, 50, 10):
            cpu, board = self.machine("CLR P3.1\nSJMP $", "motor")
            board.experiment.motor_speed = speed
            self.steps(cpu, board, 1)
            original = board.motor_position
            changes = 0
            previous = original
            for _ in range(10000):
                self.steps(cpu, board, 1)
                if board.motor_position != previous:
                    changes += 1
                    previous = board.motor_position
                if changes == 8:
                    break
            else:
                self.fail("Motor did not complete a revolution")
            cycles_for_revolution.append(cpu.cycles)
        self.assertLess(cycles_for_revolution[0], cycles_for_revolution[1])
        self.assertLess(cycles_for_revolution[1], cycles_for_revolution[2])
        legacy = {
            "keypad_mode": "Pulse",
            "switch_bounce": False,
            "bounce_us": 30000,
            "lcd_timing": True,
            "interrupt_pin": "P3.2",
            "interrupt_width_us": 10,
        }
        settings = ExperimentSettings.validated(legacy)
        self.assertFalse(settings.keypad_bounce)
        self.assertEqual(settings.motor_speed, 100)
        for key, value in (
            ("motor_speed", 0),
            ("motor_speed", 101),
            ("keypad_bounce", "true"),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                ExperimentSettings.validated({**legacy, key: value})


if __name__ == "__main__":
    unittest.main()
