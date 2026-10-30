"""Program completion preserves results without executing unloaded memory."""

import unittest

from mcs51_studio.engine.assembler import assemble, export_hex, import_hex
from mcs51_studio.engine.cpu import CPU
from mcs51_studio.engine.debugger import Debugger
from mcs51_studio.hardware.board import Board


class ProgramTermination(unittest.TestCase):
    def machine(self, program):
        cpu = CPU()
        cpu.code[:] = program.code
        board = Board(cpu)
        board.enabled = dict.fromkeys(board.enabled, False)
        return cpu, board, Debugger(cpu)

    def test_addition_stops_after_three_instructions(self):
        source = "ORG 0000H\nMOV A,#25H\nMOV B,#15H\nADD A,B\n"
        for ending in ("", "END\ninvalid text"):
            for hex_image in (False, True):
                with self.subTest(ending=ending, hex_image=hex_image):
                    program = assemble(source + ending)
                    if hex_image:
                        program = import_hex(export_hex(program))
                    cpu, board, debug = self.machine(program)
                    for index in range(3):
                        debug.step(board, program=program)
                        self.assertEqual(debug.terminated, index == 2)
                    self.assertEqual((cpu.a, cpu.ram[0xF0]), (0x3A, 0x15))
                    self.assertEqual((cpu.pc, cpu.instructions, cpu.cycles), (7, 3, 4))
                    self.assertEqual(debug.reason, "Program terminated")
                    last = debug.last
                    ram = bytes(cpu.ram)
                    debug.plan("cursor", 0)
                    for _ in range(3):
                        self.assertIsNone(debug.step(board, program=program))
                    self.assertIs(debug.last, last)
                    self.assertEqual(bytes(cpu.ram), ram)
                    self.assertEqual((cpu.pc, cpu.instructions, cpu.cycles), (7, 3, 4))
                    self.assertIsNone(debug.target)
                    cpu.reset()
                    debug.reset()
                    self.assertFalse(debug.terminated)
                    debug.step(board, program=program)
                    self.assertEqual((cpu.a, cpu.instructions), (0x25, 1))

    def test_explicit_loops_and_loaded_nops_keep_running(self):
        program = assemble("loop: NOP\nINC A\nSJMP loop\nEND")
        cpu, board, debug = self.machine(program)
        for _ in range(300):
            debug.step(board, program=program)
            self.assertFalse(debug.terminated)
            self.assertEqual(debug.reason, "")
        self.assertEqual((cpu.a, cpu.instructions), (100, 300))

    def test_last_source_instruction_return_is_not_termination(self):
        program = assemble("LCALL sub\nINC A\nORG 100H\nsub: INC A\nRET\nEND")
        cpu, board, debug = self.machine(program)
        debug.plan("over")
        for _ in range(3):
            debug.step(board, program=program)
            self.assertFalse(debug.terminated)
        self.assertEqual((cpu.pc, cpu.a, debug.frames), (3, 1, []))
        self.assertIn("Target reached", debug.reason)
        debug.step(board, program=program)
        self.assertTrue(debug.terminated)
        self.assertEqual((cpu.pc, cpu.a, cpu.instructions), (4, 2, 4))

    def test_jump_across_gap_continues_at_loaded_destination(self):
        program = assemble("LJMP main\nORG 100H\nmain: MOV A,#42H\nEND")
        cpu, board, debug = self.machine(program)
        debug.step(board, program=program)
        self.assertFalse(debug.terminated)
        self.assertEqual(cpu.pc, 0x100)
        debug.step(board, program=program)
        self.assertTrue(debug.terminated)
        self.assertEqual((cpu.a, cpu.instructions), (0x42, 2))

    def test_unloaded_jump_destination_stops_before_fetch(self):
        program = assemble("LJMP 1234H\nEND")
        cpu, board, debug = self.machine(program)
        debug.step(board, program=program)
        self.assertTrue(debug.terminated)
        self.assertEqual((cpu.pc, cpu.instructions), (0x1234, 1))
        self.assertIsNone(debug.step(board, program=program))
        self.assertEqual(cpu.instructions, 1)

    def test_unloaded_start_does_not_execute(self):
        program = assemble("ORG 100H\nNOP\nEND")
        cpu, board, debug = self.machine(program)
        self.assertIsNone(debug.step(board, program=program))
        self.assertTrue(debug.terminated)
        self.assertIsNone(debug.last)
        self.assertEqual((cpu.pc, cpu.instructions, cpu.cycles), (0, 0, 0))
        cpu.pc = 0x100
        debug.step(board, program=program)
        self.assertEqual((cpu.pc, cpu.instructions), (0x101, 1))

    def test_address_wrap_continues_only_into_loaded_memory(self):
        for loaded_zero in (False, True):
            with self.subTest(loaded_zero=loaded_zero):
                program = assemble(
                    ("LJMP 0FFFFH\n" if loaded_zero else "") + "ORG 0FFFFH\nNOP"
                )
                cpu, board, debug = self.machine(program)
                cpu.pc = 0xFFFF
                debug.step(board, program=program)
                self.assertEqual(cpu.pc, 0)
                self.assertEqual(debug.terminated, not loaded_zero)

    def test_interrupt_handler_at_end_returns_to_main_program(self):
        program = assemble("NOP\nSJMP $\nORG 000BH\nINC A\nRETI\nEND")
        cpu, board, debug = self.machine(program)
        cpu.write(0xA8, 0x82)
        cpu.write(0x88, 0x20)
        for _ in range(3):
            debug.step(board, program=program)
            self.assertFalse(debug.terminated)
        self.assertEqual((cpu.pc, cpu.a, debug.frames), (1, 1, []))
