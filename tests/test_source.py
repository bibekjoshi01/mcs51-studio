"""Source editing inputs, assembler boundaries, and safe source-file writes."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcs51_studio.engine.assembler import AssemblyError, assemble
from mcs51_studio.engine.cpu import CPU
from mcs51_studio.engine.source import normalize_source
from mcs51_studio.source_files import write_source


class SourceAssembly(unittest.TestCase):
    def test_pasted_source_executes(self):
        source = "\ufeff; copied program\r\nmov a,#5\rinc a\r\nmov r0,a\r\n"
        program = assemble(source)
        self.assertEqual(bytes(program.code[:5]), bytes([0x74, 5, 4, 0xF8, 0]))
        cpu = CPU()
        cpu.code[:] = program.code
        for _ in range(3):
            cpu.step()
        self.assertEqual((cpu.a, cpu.reg(0)), (6, 6))
        self.assertNotIn("\r", normalize_source(source))

    def test_quoted_punctuation_and_data(self):
        for character in (",", ";", "#", "@", "a", " "):
            with self.subTest(character=character):
                self.assertEqual(
                    bytes(assemble(f"MOV A,#'{character}'").code[:2]),
                    bytes([0x74, ord(character)]),
                )
        source = """DB "a;b", ';', ',', '#', '@', 'it''s' ; comment with an unmatched '
"""
        program = assemble(source)
        self.assertEqual(bytes(program.code[:11]), b"a;b;,#@it's")

    def test_bad_data_lists_report_the_source_line(self):
        for value in ("", "1,,2", "1,", ",1", "'unfinished", "'a' 'b'", '"a" "b"'):
            with self.subTest(value=value), self.assertRaises(AssemblyError) as failure:
                assemble(f"NOP\nDB {value}")
            self.assertEqual(failure.exception.line, 2)

    def test_symbol_redefinition_and_forward_symbols(self):
        for source in (
            "X EQU 1\nx EQU 2",
            "loop:NOP\nLOOP:NOP",
            "P1 EQU 1",
            "X SET 1\nX EQU 2",
        ):
            with self.subTest(source=source), self.assertRaises(AssemblyError):
                assemble(source)
        self.assertEqual(assemble("X SET 1\nX SET 2\nMOV A,#X").code[1], 2)
        self.assertEqual(
            bytes(assemble("TARGET EQU finish\nLJMP TARGET\nfinish:NOP").code[:3]),
            bytes([2, 0, 3]),
        )

    def test_relative_branch_boundaries(self):
        for amount, valid in ((127, True), (128, False)):
            source = "SJMP target\nDB " + ",".join(["0"] * amount) + "\ntarget:NOP"
            if valid:
                self.assertEqual(assemble(source).code[1], 127)
            else:
                with self.assertRaises(AssemblyError):
                    assemble(source)
        for amount, valid in ((125, True), (126, False)):
            source = "start:NOP\nDB " + ",".join(["0"] * amount) + "\nSJMP start"
            if valid:
                self.assertEqual(assemble(source).code[amount + 2], 128)
            else:
                with self.assertRaises(AssemblyError):
                    assemble(source)

    def test_memory_and_operand_limits(self):
        self.assertEqual(assemble("ORG 0FFFFH\nDB 255").code[65535], 255)
        for source in (
            "ORG 0FFFFH\nMOV A,#1",
            "AJMP 10000H",
            "MOV A,#256",
            "MOV A,#-129",
            "ORG -1",
            "ORG 0\nDB 1\nORG 0\nDB 2",
        ):
            with self.subTest(source=source), self.assertRaises(AssemblyError):
                assemble(source)

    def test_errors_include_line_and_empty_programs_remain_empty(self):
        for source, line in (
            ("; 😀 café\nNOP\nMOV A,#999", 3),
            ("NOP\nDB 1/0", 2),
            ("NOP\n\0", 2),
            ("DB '😀'", 1),
        ):
            with (
                self.subTest(source=source),
                self.assertRaises(AssemblyError) as failure,
            ):
                assemble(source)
            self.assertEqual(failure.exception.line, line)
            self.assertTrue(str(failure.exception).startswith(f"Line {line}:"))
        self.assertEqual(assemble("\n; comments only\n").used, set())
        self.assertEqual(assemble("NOP\nEND\ninvalid text").used, {0})


class SourceFiles(unittest.TestCase):
    def test_unicode_save_and_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "café.asm"
            path.write_text("old", encoding="utf-8")
            if os.name == "posix":
                path.chmod(0o640)
            write_source(path, "; π and 😀\nNOP\n")
            self.assertEqual(path.read_bytes(), "; π and 😀\nNOP\n".encode())
            if os.name == "posix":
                self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_failed_save_preserves_file_and_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "program.asm"
            path.write_text("original", encoding="utf-8")
            with patch(
                "mcs51_studio.source_files.os.replace",
                side_effect=PermissionError("locked"),
            ):
                with self.assertRaises(PermissionError):
                    write_source(path, "replacement")
            self.assertEqual(path.read_text(), "original")
            self.assertEqual(list(Path(directory).iterdir()), [path])
