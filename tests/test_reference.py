"""Compare simulator behavior with preserved Java oracle fixtures."""

import gzip
import hashlib
import json
import unittest
from pathlib import Path

from mcs51_studio.assembler import assemble
from mcs51_studio.core import CPU

FIXTURES = Path(__file__).with_name("fixtures")


def fixtures(name):
    with gzip.open(FIXTURES / f"{name}.json.gz", "rt", encoding="utf-8") as stream:
        return json.load(stream)


class ReferenceConformance(unittest.TestCase):
    def test_all_opcodes_against_original(self):
        cpu = CPU()
        cpu.code[:] = bytes((p * 17 + 3) & 255 for p in range(65536))
        for name in ("instructions", "instructions-wide"):
            for case in fixtures(name):
                with self.subTest(
                    fixture=name, opcode=case["opcode"], seed=case["seed"]
                ):
                    cpu.reset()
                    cpu.ram[:] = bytes(case["before"])
                    cpu.pc = case["pc"]
                    error = None
                    try:
                        cpu.execute(case["opcode"], case["operand0"], case["operand1"])
                    except Exception as exc:
                        error = exc
                    self.assertEqual(bool(error), bool(case["error"]))
                    self.assertEqual(cpu.pc, case["nextPc"])
                    self.assertEqual(list(cpu.ram), case["after"])

    def test_timer_modes_against_original(self):
        for case in fixtures("timers"):
            with self.subTest(mode=case["before"][0x89], steps=case["steps"]):
                cpu = CPU()
                cpu.ram[:] = bytes(case["before"])
                cpu.tick_timers(case["steps"])
                self.assertEqual(list(cpu.ram), case["after"])

    def test_serial_modes_against_original(self):
        for case in fixtures("serial"):
            with self.subTest(mode=case["before"][0x98], steps=case["steps"]):
                cpu = CPU()
                for address in (0x98, 0x87, 0x99):
                    cpu.write(address, case["before"][address])
                for _ in range(case["steps"]):
                    cpu.serial.pulse_clock()
                    cpu.serial.poll()
                self.assertEqual(list(cpu.ram), case["after"])
                self.assertEqual(cpu.serial.sbuf, case["sbuf"])

    def test_assembler_against_original(self):
        cases = json.loads((FIXTURES / "assembler.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(source=case["source"]):
                digest = hashlib.sha256(assemble(case["source"]).code).hexdigest()
                self.assertEqual(digest, case["sha256"])
