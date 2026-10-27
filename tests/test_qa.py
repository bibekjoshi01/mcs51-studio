"""Deterministic adversarial and generated acceptance tests for release QA."""

import random
import unittest

from mcs51_studio.engine.assembler import (
    AssemblyError,
    assemble,
    export_hex,
    import_hex,
)
from mcs51_studio.engine.cpu import CPU
from mcs51_studio.engine.debugger import Debugger
from mcs51_studio.hardware.board import Board
from mcs51_studio.hardware.uart import UARTEndpoint


class AssemblerQA(unittest.TestCase):
    def test_1000_generated_programs_exact_bytes_and_execution(self):
        rng = random.Random(8051)
        for case in range(1000):
            initial = rng.randrange(256)
            source = [f"MOV A,#{initial}"]
            expected = [0x74, initial]
            result = initial
            for _ in range(12):
                value = rng.randrange(256)
                op = rng.choice(("ADD", "XRL", "ANL", "ORL"))
                source.append(f"{op}\tA, #{value}")
                expected += [
                    {"ADD": 0x24, "XRL": 0x64, "ANL": 0x54, "ORL": 0x44}[op],
                    value,
                ]
                result = {
                    "ADD": (result + value) & 255,
                    "XRL": result ^ value,
                    "ANL": result & value,
                    "ORL": result | value,
                }[op]
            source += ["MOV 30H,A", "SJMP $"]
            expected += [0xF5, 0x30, 0x80, 0xFE]
            program = assemble("\r\n".join(source))
            self.assertEqual(
                bytes(program.code[: len(expected)]), bytes(expected), case
            )
            cpu = CPU()
            cpu.code[:] = program.code
            for _ in range(14):
                cpu.step()
            self.assertEqual(
                (cpu.a, cpu.ram[0x30], cpu.cycles), (result, result, 14), case
            )
            self.assertEqual(cpu.ram[0xD0] & 1, result.bit_count() & 1)
            self.assertEqual(import_hex(export_hex(program)).code, program.code)

    def test_forward_aliases_expressions_and_set_scope(self):
        cases = [
            ("MOV A,#X\nX EQU Y\nY EQU 42", [0x74, 42]),
            ("MOV A,#LOW 1234H", [0x74, 0x34]),
            ("MOV A,#HIGH(1234H)", [0x74, 0x12]),
            ("MOV A,#(3 SHL 2) OR 1", [0x74, 13]),
            ("MOV A,#15 AND 7", [0x74, 7]),
            ("X SET 1\nMOV A,#X\nX SET X+1\nMOV R0,#X", [0x74, 1, 0x78, 2]),
            ("SJMP DEST\nDEST EQU finish\nfinish:NOP", [0x80, 0, 0]),
            ("SJMP $+2", [0x80, 0]),
            ("JMP\t$", [0x80, 0xFE]),
            ("MOV A,#''''", [0x74, 39]),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(list(assemble(source).code[: len(expected)]), expected)
        for source in [
            "X EQU Y\nY EQU X",
            "X SET X+1",
            "MOV A,#X\nX SET 1",
            "ORG later\nlater:NOP",
            "END garbage",
            "MOV -1,#1",
            "SETB -1",
            "MOV A,-1",
        ]:
            with self.subTest(source=source), self.assertRaises(AssemblyError):
                assemble(source)

    def test_many_symbols_and_bounded_dependency_depth(self):
        source = (
            "\n".join(f"VALUE{i} EQU {i}" for i in range(10000))
            + "\nMOV DPTR,#VALUE9999"
        )
        self.assertEqual(list(assemble(source).code[:3]), [0x90, 0x27, 0x0F])
        chain = (
            "\n".join(f"VALUE{i} EQU VALUE{i + 1}" for i in range(200))
            + "\nVALUE200 EQU 5"
        )
        with self.assertRaisesRegex(AssemblyError, "depth exceeds"):
            assemble(chain)

    def test_relative_offsets_do_not_wrap_invalid_input(self):
        for instruction in ("SJMP", "JNZ", "JC", "DJNZ R0,", "CJNE A,#1,", "JB P1.0,"):
            for value in (-65536, -129, 128, 65536, 65537):
                with (
                    self.subTest(instruction=instruction, value=value),
                    self.assertRaises(AssemblyError),
                ):
                    assemble(f"{instruction} {value}")
        self.assertEqual(
            list(assemble("ORG 0FFFEH\nSJMP zero\nORG 0\nzero:NOP").code[-2:]),
            [0x80, 0],
        )

    def test_expression_resource_limits(self):
        for expression in [
            "1" + "+1" * 1500,
            "(" * 300 + "1" + ")" * 300,
            "1 SHL 65",
            "(1 SHL 63)*(1 SHL 63)",
            "9" * 5000,
            "A.__class__",
            "__import__(1)",
            "[1]*8",
        ]:
            with (
                self.subTest(expression=expression[:30]),
                self.assertRaises(AssemblyError),
            ):
                assemble("MOV A,#" + expression)
        with self.assertRaises(AssemblyError):
            assemble(";" * 524289)

    def test_3000_mutated_sources_never_raise_internal_errors(self):
        rng = random.Random(51)
        seeds = [
            "MOV A,#42",
            "CJNE R0,#4,loop\nloop:NOP",
            'DB "hello"',
            "ORG 100H\nLCALL 1234H",
            "X EQU 2\nMOV A,#X",
        ]
        alphabet = "#,'\";@()[]+*/-\t\n0129AZ_\0"
        for _ in range(3000):
            source = rng.choice(seeds)
            for _ in range(rng.randrange(1, 5)):
                offset = rng.randrange(len(source) + 1)
                source = source[:offset] + rng.choice(alphabet) + source[offset + 1 :]
            try:
                program = assemble(source)
                self.assertTrue(all(0 <= address <= 65535 for address in program.used))
            except AssemblyError as error:
                self.assertIsNotNone(error.line)

    def test_hex_record_shapes_and_full_memory_roundtrip(self):
        for record in (
            ":0100000100FE",
            ":00000101FE",
            ":00000003FD",
            ":00000005FB",
            ":020001040000F9",
        ):
            with self.subTest(record=record), self.assertRaises(AssemblyError):
                import_hex(
                    record + "\n:00000001FF\n"
                    if "01" not in record[7:9]
                    else record + "\n"
                )
        program = assemble("DB " + ",".join(str(i & 255) for i in range(65536)))
        decoded = import_hex(export_hex(program))
        self.assertEqual(decoded.used, set(range(65536)))
        self.assertEqual(decoded.code, bytes(range(256)) * 256)


class IntegratedHardwareQA(unittest.TestCase):
    def machine(self, source, *devices):
        cpu = CPU()
        cpu.code[:] = assemble(source).code
        board = Board(cpu)
        board.enabled = {name: name in devices for name in board.enabled}
        board.update()
        return cpu, board

    def test_motor_uses_elapsed_cycles_without_losing_remainder(self):
        for direction, latch in [(1, 0xFD), (-1, 0xFE)]:
            for chunks in ([1] * 700, [2] * 350, [4] * 175, [700], [3, 4] * 100):
                cpu, board = self.machine("SJMP $", "motor")
                cpu.write(0xB0, latch)
                for elapsed in chunks:
                    cpu.cycles += elapsed
                    board.update()
                self.assertEqual(
                    (board.motor_position, board.motor_count),
                    ((2 + 100 * direction) % 8, 7),
                )
                before = board.motor_position
                for _ in range(100):
                    board.update()
                self.assertEqual(board.motor_position, before)

    def test_shared_pin_consumers_observe_resolved_state(self):
        cpu, board = self.machine("NOP", "motor", "display", "leds", "dac")
        board.mapping["motor_sensor"] = ["P1.0"]
        board.mapping["dac_wr"] = ["P2.0"]
        cpu.write(0xA0, 0xFE)
        board.motor_position = 0
        board.update()
        self.assertEqual(cpu.read(0x90), 254)
        self.assertEqual(board.led_mask, 1)
        self.assertEqual(board.digits[3], 254)
        self.assertEqual(board.dac_value, 254)
        cpu, board = self.machine("NOP", "uart")
        board.receive("{55}")
        for _ in range(500):
            cpu.step()
            board.update()
            self.assertEqual(cpu.bit(0xB0), board.uart.tx_line)

    def test_50000_instruction_led_debugger_soak(self):
        cpu, board = self.machine(
            "MOV A,#0FFH\nloop:MOV P1,A\nDEC A\nSJMP loop", "leds"
        )
        debug = Debugger(cpu)
        debug.add_watch("ACC")
        for _ in range(50000):
            debug.step(board)
        self.assertEqual(cpu.cycles, 1 + ((49999 // 3) * 4) + (49999 % 3))
        self.assertEqual(cpu.ram[0x90], (255 - ((49999 - 1) // 3)) & 255)
        self.assertEqual(board.led_mask, 255 ^ cpu.ram[0x90])
        self.assertEqual(debug.frames, [])
        self.assertLessEqual(len(board.scope), 600)

    def test_uart_end_to_end_timer_driven_both_directions(self):
        setup = "MOV TMOD,#20H\nMOV TH1,#0F3H\nMOV TL1,#0F3H\nSETB TR1\nMOV SCON,#50H\n"
        for receive in (False, True):
            for value in (0, 1, 0x55, 0xAA, 0xFF):
                source = setup + (
                    "wait:JNB RI,wait\nMOV A,SBUF\nSJMP $"
                    if receive
                    else f"MOV SBUF,#{value}\nwait:JNB TI,wait\nSJMP $"
                )
                cpu, board = self.machine(source, "uart")
                board.uart.configure(2400)
                for _ in range(5):
                    cpu.step()
                    board.update()
                if receive:
                    board.receive("{" + f"{value:02X}" + "}")
                for _ in range(3000):
                    cpu.step()
                    board.update()
                self.assertEqual(
                    cpu.a if receive else board.uart.received,
                    value if receive else [value],
                )
                self.assertEqual(sum(board.uart.errors.values()), 0)


class PersistenceAndRetentionQA(unittest.TestCase):
    def test_serial_histories_remain_bounded(self):
        cpu, uart = CPU(), UARTEndpoint()
        for i in range(100000):
            uart.record_received(i & 255)
            cpu.write(0x99, i & 255)
        self.assertLessEqual(len(cpu.serial_tx), 8192)
        self.assertLessEqual(len(uart.received), 65536)
        self.assertEqual(uart.received_dropped + len(uart.received), 100000)
        self.assertEqual(uart.received[-1], 99999 & 255)
        self.assertEqual(cpu.serial_tx[-1], 99999 & 255)


if __name__ == "__main__":
    unittest.main()
