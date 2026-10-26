"""Exact execution stops, teaching timing, and serial framing contracts."""

import unittest

from mcs51_studio.engine.assembler import assemble
from mcs51_studio.engine.cpu import CPU
from mcs51_studio.engine.debugger import Debugger, Watch
from mcs51_studio.hardware.board import Board
from mcs51_studio.hardware.experiment import ExperimentSettings, InputStimulus
from mcs51_studio.hardware.lcd import LCD
from mcs51_studio.hardware.uart import UARTEndpoint


class Debugging(unittest.TestCase):
    def machine(self, source):
        cpu = CPU()
        cpu.code[:] = assemble(source).code
        board = Board(cpu)
        board.enabled = dict.fromkeys(board.enabled, False)
        return cpu, board, Debugger(cpu)

    def finish(self, debugger, board, limit=100):
        for _ in range(limit):
            debugger.step(board)
            if debugger.reason:
                return
        self.fail("Temporary run did not stop")

    def test_nested_step_over_and_out(self):
        cpu, board, debug = self.machine(
            "LCALL outer\nINC A\nSJMP $\nouter: LCALL inner\nINC A\nRET\ninner: INC A\nRET"
        )
        self.assertTrue(debug.plan("over"))
        self.finish(debug, board)
        self.assertEqual((cpu.pc, cpu.a, cpu.ram[0x81], debug.frames), (3, 2, 7, []))
        cpu.pc = 0
        debug.step(board)
        debug.step(board)
        self.assertEqual(len(debug.frames), 2)
        debug.plan("out")
        self.finish(debug, board)
        self.assertEqual((len(debug.frames), cpu.a), (1, 3))
        debug.plan("out")
        self.finish(debug, board)
        self.assertEqual((cpu.pc, len(debug.frames), cpu.a), (3, 0, 4))
        with self.assertRaises(ValueError):
            debug.plan("out")

    def test_recursive_calls_do_not_stop_at_inner_return(self):
        cpu, board, debug = self.machine(
            "MOV R0,#3\nLCALL sub\nSJMP $\nsub: DJNZ R0,recurse\nRET\nrecurse: LCALL sub\nRET"
        )
        debug.step(board)
        debug.plan("over")
        self.finish(debug, board)
        self.assertEqual((cpu.pc, cpu.reg(0), len(debug.frames)), (5, 0, 0))

    def test_cursor_budget_and_wraparound(self):
        cpu, board, debug = self.machine("SJMP $")
        self.assertFalse(debug.plan("cursor", 0))
        debug.plan("cursor", 10)
        debug.target["budget"] = 3
        self.finish(debug, board)
        self.assertEqual(cpu.instructions, 3)
        self.assertIn("not reached", debug.reason)
        cpu.pc = 65534
        cpu.code[65534:65536] = bytes([0x11, 0x10])  # ACALL wraps return to 0000
        cpu.code[16] = 0x22
        debug.plan("over")
        self.finish(debug, board)
        self.assertEqual(cpu.pc, 0)

    def test_interrupt_frames_and_step_out(self):
        cpu, board, debug = self.machine("NOP\nSJMP $\nORG 000BH\nINC A\nRETI")
        cpu.write(0xA8, 0x82)
        cpu.write(0x88, 0x20)
        debug.step(board)
        self.assertEqual(cpu.pc, 0xB)
        self.assertEqual(debug.frames[-1]["kind"], "interrupt")
        self.assertEqual(debug.last["cycles"], 3)
        debug.plan("out")
        self.finish(debug, board)
        self.assertEqual((cpu.pc, cpu.a, cpu.ram[0x81]), (1, 1, 7))

    def test_mismatched_return_stops_and_explains(self):
        cpu, board, debug = self.machine("LCALL sub\nSJMP $\nsub: MOV 08H,#20H\nRET")
        debug.plan("over")
        self.finish(debug, board)
        self.assertIn("Stack return", debug.reason)
        self.assertIsNone(debug.target)
        self.assertEqual(debug.frames, [])

    def test_memory_watch_and_instruction_explanation(self):
        cpu, board, debug = self.machine(
            "MOV 30H,#0\nMOV 30H,#55H\nMOV DPTR,#1234H\nMOV A,#0FFH\nADD A,#1\nMOVX @DPTR,A"
        )
        debug.add_watch("ram[30]", True)
        debug.step(board)
        self.assertEqual(debug.reason, "")
        debug.step(board)
        self.assertIn("00 → 55", debug.reason)
        for _ in range(3):
            debug.step(board)
        self.assertEqual((cpu.a, cpu.carry, cpu.ram[0xD0] & 0x40), (0, 1, 0x40))
        self.assertIn("ACC", debug.changed)
        self.assertIn("CY 0→1", debug.explanation())
        self.assertIn("1 instruction machine cycles", debug.explanation())
        cpu.xram[0x1234] = 99
        debug.add_watch("XDATA[1234]", True)
        debug.step(board)
        self.assertIn("XDATA[1234]", debug.reason)
        self.assertEqual(debug.last["xdata"], (0x1234, 99, 0))

    def test_watch_validation_no_evaluation(self):
        cpu = CPU()
        for expr in [
            "RAM[80]",
            "SFR[84]",
            "BIT[100]",
            '__import__("os")',
            "A+1",
            "XDATA[10000]",
            "R8",
        ]:
            with self.subTest(expr=expr), self.assertRaises(ValueError):
                Watch(expr).read(cpu)
        for expr in [
            "ACC",
            "DPTR",
            "R0",
            "CY",
            "RAM[7F]",
            "BIT[7F]",
            "CODE[FFFF]",
            "XDATA[FFFF]",
        ]:
            self.assertIsInstance(Watch(expr).read(cpu), int)
        debugger = Debugger(cpu)
        debugger.add_watch("ACC")
        with self.assertRaises(ValueError):
            debugger.add_watch("acc")
        cpu.reset()
        debugger.reset()
        self.assertEqual(len(debugger.watches), 1)

    def test_timer_watch_and_preempted_call(self):
        cpu, board, debug = self.machine(
            "LCALL sub\nSJMP $\nORG 000BH\nRETI\nORG 0030H\nsub: INC A\nRET"
        )
        cpu.write(0x89, 1)
        cpu.write(0x88, 0x10)
        debug.add_watch("TL0", True)
        debug.step(board)
        self.assertIn("TL0 changed", debug.reason)
        self.assertEqual(cpu.ram[0x8A], 2)
        debug.watches.clear()
        cpu.write(0xA8, 0x82)
        cpu.write(0x88, 0x20)
        debug.plan("out")
        debug.step(board)
        self.assertEqual([f["kind"] for f in debug.frames], ["call", "interrupt"])
        self.assertIsNotNone(debug.target)
        self.finish(debug, board)
        self.assertEqual((cpu.pc, cpu.a, debug.frames), (3, 1, []))


class TeachingPeripherals(unittest.TestCase):
    def test_keypad_modes_and_repeat(self):
        board = Board(CPU())
        board.enabled["keypad"] = True
        a, b = (0, 0), (1, 2)
        board.key_event(a, True)
        self.assertEqual(board.keys, {a})
        board.key_event(a, False)
        self.assertFalse(board.keys)
        board.set_keypad_mode("Standard")
        board.key_event(a, True)
        board.key_event(a, True)
        board.key_event(a, False)
        board.key_event(b, True)
        board.key_event(b, False)
        self.assertEqual(board.keys, {a, b})
        board.key_event(a, True)
        board.key_event(a, False)
        self.assertEqual(board.keys, {b})
        board.set_keypad_mode("Radio")
        self.assertFalse(board.keys)
        for key in (a, b):
            board.key_event(key, True)
            board.key_event(key, False)
        self.assertEqual(board.keys, {b})
        board.key_event(b, True)
        board.key_event(b, False)
        self.assertFalse(board.keys)
        with self.assertRaises(ValueError):
            board.set_keypad_mode("Other")

    def test_bounce_is_simulated_time_and_settles(self):
        stimulus = InputStimulus()
        settings = ExperimentSettings(switch_bounce=True, bounce_us=100)
        desired = [False] + [True] * 7
        self.assertTrue(stimulus.switch_levels(desired, 0, settings)[0])
        self.assertTrue(stimulus.switch_levels(desired, 0, settings)[0])
        self.assertFalse(stimulus.switch_levels(desired, 10, settings)[0])
        self.assertTrue(stimulus.switch_levels(desired, 20, settings)[0])
        self.assertFalse(stimulus.switch_levels(desired, 100, settings)[0])
        self.assertFalse(stimulus.bounces)
        settings.switch_bounce = False
        self.assertEqual(stimulus.switch_levels([True] * 8, 101, settings), [True] * 8)

    def test_interrupt_pulse_pin_levels_and_edge_request(self):
        for pin, bit, request in [("P3.2", 0xB2, 0x02), ("P3.3", 0xB3, 0x08)]:
            cpu = CPU()
            board = Board(cpu)
            board.enabled = dict.fromkeys(board.enabled, False)
            cpu.write(0x88, 0x05)  # falling edge modes
            board.update()
            cpu.step()
            board.update()
            board.stimulus.pulse(pin, cpu.cycles, 3)
            board.update()
            self.assertEqual(cpu.bit(bit), 0)
            cpu.step()
            board.update()
            self.assertTrue(cpu.ram[0x88] & request)
            cpu.cycles += 2
            board.update()
            self.assertEqual(cpu.bit(bit), 1)
        with self.assertRaises(ValueError):
            board.stimulus.pulse("P1.0", 0, 1)

    def test_lcd_busy_boundaries_cursor_and_cgram(self):
        lcd = LCD()
        lcd.accept(0x0F, 0, 0)
        self.assertFalse(lcd.accept(ord("A"), 1, 36))
        self.assertTrue(lcd.accept(ord("A"), 1, 37))
        self.assertEqual(lcd.lines()[0], "A" + " " * 15)
        self.assertEqual(lcd.cursor_cell(), (0, 1))
        lcd.accept(1, 0, 74)
        self.assertEqual(lcd.busy_until, 1594)
        self.assertFalse(lcd.accept(0x80, 0, 1593))
        self.assertTrue(lcd.accept(0x40, 0, 1594))
        for i in range(8):
            lcd.byte(0xFF if i % 2 else i, 1)
        self.assertEqual(lcd.glyph(0), (0, 31, 2, 31, 4, 31, 6, 31))
        self.assertEqual(lcd.glyph(8), lcd.glyph(0))
        self.assertIsNone(lcd.glyph(16))
        lcd.byte(0xC0, 0)
        self.assertEqual(lcd.cursor_cell(), (1, 0))
        lcd.byte(0x08, 0)
        self.assertIsNone(lcd.cursor_cell())
        self.assertEqual(lcd.lines(), [" " * 16] * 2)

    def test_lcd_four_bit_busy_and_relaxed_mode(self):
        lcd = LCD()
        lcd.accept(0x20, 0, 0)
        self.assertIsNone(lcd.accept(0x00, 0, 37))
        self.assertTrue(lcd.accept(0xC0, 0, 37))
        self.assertTrue(lcd.display)
        self.assertFalse(lcd.accept(0x40, 1, 38))
        lcd.accept(0x40, 1, 74)
        lcd.accept(0x10, 1, 74)
        self.assertEqual(lcd.lines()[0][0], "A")
        lcd.accept(0x40, 1, 74, False)
        lcd.accept(0x20, 1, 74, False)
        self.assertEqual(lcd.lines()[0][:2], "AB")

    def test_uart_all_framing_combinations_back_to_back(self):
        for bits in (7, 8):
            for parity in (0, 1, 2):
                for stops in (1, 2):
                    with self.subTest(bits=bits, parity=parity, stops=stops):
                        uart = UARTEndpoint()
                        uart.configure(115200, parity, data_bits=bits, stop_bits=stops)
                        expected = [0, 1, 0x55, (1 << bits) - 1]
                        uart.start("{" + ",".join(f"{v:X}" for v in expected) + "}")
                        for _ in range(uart.period * 60):
                            uart.pulse(uart.tx_line)
                        self.assertEqual(uart.received, expected)
                        self.assertEqual(sum(uart.errors.values()), 0)

    def test_uart_transmit_bits_have_exact_framing(self):
        uart = UARTEndpoint()
        uart.configure(9600, 2, data_bits=8, stop_bits=2)
        uart.start("{81}")
        observed = []
        for _ in range(13):
            for _ in range(uart.period):
                uart.pulse(1)
            observed.append(uart.tx_line)
        # Start, 81H least-significant bit first, even parity, two stop bits, idle.
        self.assertEqual(observed, [0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1])

    def test_uart_errors_and_atomic_queue(self):
        uart = UARTEndpoint()
        uart.configure(9600, 2, data_bits=8)

        def bit(value):
            for _ in range(uart.period):
                uart.pulse(value)

        # 8E1: 01 needs parity 1; bad parity and bad stop must discard it.
        for value in [1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]:
            bit(value)
        self.assertEqual(uart.received, [])
        self.assertEqual(uart.errors["parity"], 1)
        self.assertEqual(uart.errors["framing"], 1)
        uart.pulse(0)
        for _ in range(uart.period):
            uart.pulse(1)
        self.assertEqual(uart.errors["start"], 1)
        uart.start("{41}")
        for invalid in ["{100}", "{GG}", "{41", "λ"]:
            with self.assertRaises(ValueError):
                uart.start(invalid)
            self.assertEqual(uart.pending, [65])
        with self.assertRaisesRegex(ValueError, "busy"):
            uart.configure(4800)
        uart.reset_link()
        uart.configure(4800, 1, data_bits=7, stop_bits=2)
        self.assertEqual(uart.framing, "7O2")
        with self.assertRaises(ValueError):
            uart.start("{80}")


if __name__ == "__main__":
    unittest.main()
