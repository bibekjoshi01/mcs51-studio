"""Guard established simulator behavior with baseline regression fixtures."""

import gzip
import hashlib
import json
import unittest
from pathlib import Path

from mcs51_studio.engine.assembler import assemble
from mcs51_studio.engine.cpu import CPU, SFR

FIXTURES = Path(__file__).with_name("fixtures")


def fixtures(name):
    with gzip.open(FIXTURES / f"{name}.json.gz", "rt", encoding="utf-8") as stream:
        return json.load(stream)


def compatible_instruction(case):
    """Select defined, unchanged behavior from the historical oracle.

    Changed families have independent specification tests. Keep golden files
    unchanged; their invalid RAM/SFR inputs do not define this processor.
    """
    op, x, y, ram = case["opcode"], case["operand0"], case["operand1"], case["before"]
    if (
        op in (0xA5, 0xC0, 0xD0, 0xE0, 0xE2, 0xE3, 0xF0, 0xF2, 0xF3)
        or 0x94 <= op <= 0x9F
    ):
        return False
    direct = []
    if (
        op
        in (
            0x05,
            0x15,
            0x25,
            0x35,
            0x42,
            0x43,
            0x45,
            0x52,
            0x53,
            0x55,
            0x62,
            0x63,
            0x65,
            0x75,
            0x86,
            0x87,
            0xA6,
            0xA7,
            0xB5,
            0xC5,
            0xD5,
            0xE5,
            0xF5,
        )
        or 0x88 <= op <= 0x8F
        or 0xA8 <= op <= 0xAF
    ):
        direct.append(x)
    if op == 0x85:
        direct.extend((x, y))
    if op in (0x10, 0x20, 0x30, 0x72, 0x82, 0x92, 0xA0, 0xA2, 0xB0, 0xB2, 0xC2, 0xD2):
        direct.append(0x20 + x // 8 if x < 128 else x & 0xF8)
    if any(address >= 128 and address not in SFR.values() for address in direct):
        return False
    if op & 0xFE in (
        0x06,
        0x16,
        0x26,
        0x36,
        0x46,
        0x56,
        0x66,
        0x76,
        0x86,
        0xA6,
        0xB6,
        0xC6,
        0xD6,
        0xE6,
        0xF6,
    ):
        if ram[((ram[0xD0] >> 3) & 3) * 8 + (op & 1)] >= 128:
            return False
    sp = ram[0x81]
    if op & 31 == 17 or op == 0x12:
        if ((sp + 1) & 255) >= 128 or ((sp + 2) & 255) >= 128:
            return False
    if op in (0x22, 0x32) and (sp >= 128 or ((sp - 1) & 255) >= 128):
        return False
    return True


class BaselineRegression(unittest.TestCase):
    def test_compatible_instructions_against_baseline(self):
        cpu = CPU()
        cpu.code[:] = bytes((p * 17 + 3) & 255 for p in range(65536))
        compared = 0
        for name in ("instructions", "instructions-wide"):
            for case in fixtures(name):
                if not compatible_instruction(case):
                    continue
                compared += 1
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
                    expected = list(case["after"])
                    # P reflects ACC at every instruction boundary, even when
                    # a legacy input randomized P independently of ACC.
                    expected[0xD0] = (expected[0xD0] & 254) | (
                        expected[0xE0].bit_count() & 1
                    )
                    self.assertEqual(list(cpu.ram), expected)

        self.assertEqual(compared, 6836)

    def test_serial_modes_against_baseline(self):
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

    def test_assembler_against_baseline(self):
        cases = json.loads((FIXTURES / "assembler.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(source=case["source"]):
                digest = hashlib.sha256(assemble(case["source"]).code).hexdigest()
                self.assertEqual(digest, case["sha256"])
