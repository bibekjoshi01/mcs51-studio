"""Independent checks against the classic 8051 instruction/hardware manuals.

See docs/processor.md for references, timing resolution, and undefined behavior.
"""

import unittest
from unittest.mock import Mock

from mcs51_studio.engine.assembler import assemble
from mcs51_studio.engine.cpu import CPU, ProcessorError
from mcs51_studio.resources import ISA


class Classic8051(unittest.TestCase):
    def test_profile_and_reset(self):
        c = CPU()
        self.assertEqual(
            (c.profile.oscillator_hz, c.profile.clocks_per_cycle), (12000000, 12)
        )
        self.assertEqual(
            (
                c.profile.internal_ram_bytes,
                c.profile.timers,
                c.profile.interrupt_sources,
            ),
            (128, 2, 5),
        )
        self.assertEqual(c.ram[0x81], 7)
        self.assertEqual([c.read(p) for p in (0x80, 0x90, 0xA0, 0xB0)], [255] * 4)
        self.assertEqual((len(c.code), len(c.xram)), (65536, 65536))
        c.xram[65535] = 99
        c.reset()
        self.assertEqual(c.xram[65535], 0)
        for address in (0xC8, 0xCA, 0xCB, 0xCC, 0xCD):
            with self.assertRaises(ProcessorError):
                c.write(address, 1)

    def test_arithmetic_exhaustive(self):
        c = CPU()
        for op in (0x24, 0x34, 0x94):
            for a in range(256):
                for b in range(256):
                    for carry in (0,) if op == 0x24 else (0, 1):
                        c.ram[0xE0], c.ram[0xD0] = a, 0x38 | (carry << 7)
                        c.execute(op, b)
                        result = a - b - carry if op == 0x94 else a + b + carry
                        r = result & 255
                        cy = result < 0 if op == 0x94 else result > 255
                        ac = (
                            (a & 15) < (b & 15) + carry
                            if op == 0x94
                            else (a & 15) + (b & 15) + carry > 15
                        )
                        ov = bool(((a ^ b) if op == 0x94 else ~(a ^ b)) & (a ^ r) & 128)
                        flags = (
                            0x38
                            | (cy << 7)
                            | (ac << 6)
                            | (ov << 2)
                            | (r.bit_count() & 1)
                        )
                        self.assertEqual(
                            (c.a, c.ram[0xD0]), (r, flags), (op, a, b, carry)
                        )

    def test_decimal_adjust_valid_bcd(self):
        c = CPU()
        for a in range(100):
            for b in range(100):
                for carry in (0, 1):
                    c.a = (a // 10) * 16 + a % 10
                    c.carry = carry
                    c.execute(0x34, (b // 10) * 16 + b % 10)
                    acov = c.ram[0xD0] & 0x44
                    c.execute(0xD4)
                    expected = (a + b + carry) % 100
                    self.assertEqual(
                        (c.a, c.carry),
                        (
                            (expected // 10) * 16 + expected % 10,
                            int(a + b + carry >= 100),
                        ),
                    )
                    self.assertEqual(c.ram[0xD0] & 0x44, acov)

    def test_multiply_divide_exhaustive(self):
        c = CPU()
        for a in range(256):
            for b in range(256):
                c.a, c.ram[0xF0], c.ram[0xD0] = a, b, 0xC0
                c.execute(0xA4)
                self.assertEqual(
                    (c.a, c.ram[0xF0], c.carry, c.bit(0xD2), c.bit(0xD6)),
                    (a * b & 255, a * b >> 8, 0, int(a * b > 255), 1),
                )
                c.a, c.ram[0xF0] = a, b
                c.execute(0x84)
                self.assertEqual((c.carry, c.bit(0xD2)), (0, int(b == 0)))
                if b:
                    self.assertEqual((c.a, c.ram[0xF0]), divmod(a, b))

    def test_parity_after_psw_bit_and_byte_writes(self):
        c = CPU()
        for a in range(256):
            for op, x, y in (
                (0x00, 0, 0),
                (0x75, 0xD0, 255),
                (0xD2, 0xD0, 0),
                (0xC2, 0xD0, 0),
                (0xB2, 0xD0, 0),
            ):
                c.a = a
                c.execute(op, x, y)
                self.assertEqual(c.bit(0xD0), a.bit_count() & 1)

    def test_indirect_operations_never_alias_sfr(self):
        ops = [
            0x06,
            0x16,
            0x26,
            0x36,
            0x46,
            0x56,
            0x66,
            0x76,
            0x86,
            0x96,
            0xA6,
            0xB6,
            0xC6,
            0xD6,
            0xE6,
            0xF6,
        ]
        for base in ops:
            for r in (0, 1):
                c = CPU()
                c.set_reg(r, 0x90)
                before = bytes(c.ram)
                with self.assertRaisesRegex(ProcessorError, "00–7FH"):
                    c.execute(base + r, 0x30, 0)
                self.assertEqual(bytes(c.ram), before)
                c.set_reg(r, 0x7F)
                c.execute(base + r, 0x30, 0)

    def test_register_banks_and_bit_ram(self):
        c = CPU()
        for bank in range(4):
            c.write(0xD0, bank << 3)
            for r in range(8):
                c.set_reg(r, bank * 8 + r)
                self.assertEqual(c.ram[bank * 8 + r], bank * 8 + r)
        for bit in range(128):
            c.set_bit(bit, 1)
            self.assertEqual(c.ram[0x20 + bit // 8] >> (bit % 8) & 1, 1)
        self.assertEqual(c.ram[0x20:0x30], bytes([255]) * 16)

    def test_stack_calls_and_special_sp(self):
        c = CPU()
        c.pc = 0x1234
        c.execute(0x12, 0x56, 0x78)
        self.assertEqual(
            (c.pc, c.ram[8:10], c.ram[0x81]), (0x5678, bytes([0x37, 0x12]), 9)
        )
        c.execute(0x22)
        self.assertEqual((c.pc, c.ram[0x81]), (0x1237, 7))
        c.execute(0xC0, 0x81)
        self.assertEqual((c.ram[8], c.ram[0x81]), (8, 8))
        c.ram[8] = 0x30
        c.execute(0xD0, 0x81)
        self.assertEqual(c.ram[0x81], 0x30)
        c.ram[0x81] = 0x7E
        before = bytes(c.ram)
        with self.assertRaises(ProcessorError):
            c.execute(0x12, 0, 0)
        self.assertEqual(bytes(c.ram), before)
        c.push(0xAB)
        with self.assertRaises(ProcessorError):
            c.push(0xCD)
        self.assertEqual((c.ram[0x81], c.ram[0x7F], c.ram[0x80]), (0x7F, 0xAB, 255))
        c.ram[0x81] = 0
        c.ram[0] = 42
        self.assertEqual(c.pop(), 42)
        self.assertEqual(c.ram[0x81], 255)
        with self.assertRaises(ProcessorError):
            c.pop()

    def test_movx_all_forms_and_memory_separation(self):
        c = CPU()
        for address in (0, 0x7F, 0x80, 0xFF, 0x100, 0x1234, 0xFFFF):
            c.dptr, c.a = address, address & 255
            c.execute(0xF0)
            c.a = 0
            c.execute(0xE0)
            self.assertEqual(c.a, address & 255)
            self.assertEqual(ISA[0xE0]["cycles"], 2)
        for r in (0, 1):
            c.write(0xA0, 0xAB)
            c.port_inputs[0xA0] = 0
            c.set_reg(r, 0xFE)
            c.a = 0x42 + r
            c.execute(0xF2 + r)
            c.a = 0
            c.execute(0xE2 + r)
            self.assertEqual(
                (c.a, c.xram[0xABFE], c.ram[0xA0]), (0x42 + r, 0x42 + r, 0xAB)
            )
        self.assertEqual(c.ram[0x80], 255)
        c.xram[0x20], c.code[0x20], c.ram[0x20] = 1, 2, 3
        c.dptr = 0x20
        c.execute(0xE0)
        self.assertEqual(c.a, 1)
        c.a = 0
        c.execute(0x93)
        self.assertEqual(c.a, 2)
        c.execute(0xE5, 0x20)
        self.assertEqual(c.a, 3)

    def test_movx_assembled_program(self):
        c = CPU()
        c.code[:] = assemble(
            "MOV DPTR,#1234H\nMOV A,#5AH\nMOVX @DPTR,A\nCLR A\nMOVX A,@DPTR\nMOV 30H,A"
        ).code
        for _ in range(6):
            c.step()
        self.assertEqual((c.ram[0x30], c.xram[0x1234], c.cycles), (0x5A, 0x5A, 9))

    def test_reserved_opcode_fault(self):
        with self.assertRaisesRegex(ProcessorError, "Reserved opcode A5H"):
            CPU().execute(0xA5)

    def test_timers_overflow_and_reload(self):
        for timer in (0, 1):
            for mode in (0, 1, 2):
                c = CPU()
                c.ram[0x89] = mode << (4 * timer)
                c.set_bit(0x8C + 2 * timer, 1)
                c.ram[0x8A + timer], c.ram[0x8C + timer] = (
                    0xFF,
                    0xFF if mode != 2 else 0xA0,
                )
                c.tick_timers(1)
                self.assertEqual(c.bit(0x8D + 2 * timer), 1)
                self.assertEqual(
                    c.ram[0x8A + timer], 0xE0 if mode == 0 else 0xA0 if mode == 2 else 0
                )
                self.assertEqual(c.ram[0x8C + timer], 0xA0 if mode == 2 else 0)
                c.tick_timers(3)
                self.assertEqual(
                    c.ram[0x8A + timer], 0xE3 if mode == 0 else 0xA3 if mode == 2 else 3
                )

    def test_timer_gate_counter_and_stop(self):
        for timer in (0, 1):
            c = CPU()
            c.ram[0x89] = 0xD << (4 * timer)
            c.set_bit(0x8C + 2 * timer, 1)
            gate, pin = 1 << (2 + timer), 1 << (4 + timer)
            c.port_inputs[0xB0] &= ~gate
            c.tick_timers(1)
            c.port_inputs[0xB0] &= ~pin
            c.tick_timers(1)
            self.assertEqual(c.ram[0x8A + timer], 0)
            c.port_inputs[0xB0] |= gate
            c.tick_timers(1)
            self.assertEqual(c.ram[0x8A + timer], 0)
            c.port_inputs[0xB0] |= pin
            c.tick_timers(1)
            c.port_inputs[0xB0] &= ~pin
            c.tick_timers(5)
            self.assertEqual(c.ram[0x8A + timer], 1)
            c.set_bit(0x8C + 2 * timer, 0)
            c.port_inputs[0xB0] |= pin
            c.tick_timers(1)
            c.port_inputs[0xB0] &= ~pin
            c.tick_timers(1)
            c.set_bit(0x8C + 2 * timer, 1)
            c.tick_timers(1)
            self.assertEqual(c.ram[0x8A + timer], 1)

    def test_split_timer_independent_controls(self):
        c = CPU()
        c.ram[0x89] = 0x3F  # T1 halted, TL0 gated counter, TH0 timer
        c.ram[0x8A], c.ram[0x8C] = 255, 255
        c.port_inputs[0xB0] = 0
        c.set_bit(0x8E, 1)
        c.tick_timers(1)
        self.assertEqual(
            (c.ram[0x8A], c.ram[0x8C], c.bit(0x8D), c.bit(0x8F)), (255, 0, 0, 1)
        )
        c.set_bit(0x8E, 0)
        c.set_bit(0x8C, 1)
        c.ram[0x89] = 0x33
        c.tick_timers(1)
        self.assertEqual((c.ram[0x8A], c.ram[0x8C], c.bit(0x8D)), (0, 0, 1))

    def test_timer1_baud_clock_only_on_full_overflow(self):
        for mode in (0, 1, 2):
            c = CPU()
            c.ram[0x98] = 0x40
            c.ram[0x89] = mode << 4
            c.set_bit(0x8E, 1)
            c.serial.pulse_clock = Mock()
            c.ram[0x8B], c.ram[0x8D] = 30 if mode == 0 else 254, 0
            c.tick_timers(2)
            self.assertEqual(c.serial.pulse_clock.call_count, int(mode == 2))
            c.ram[0x8B], c.ram[0x8D] = 31 if mode == 0 else 255, 255
            c.tick_timers(1)
            self.assertEqual(c.serial.pulse_clock.call_count, 1 + int(mode == 2))
        c = CPU()
        c.ram[0x98], c.ram[0x89], c.ram[0x8B], c.ram[0x8D] = 0x40, 0x23, 255, 0xFC
        c.serial.pulse_clock = Mock()
        c.tick_timers(1)  # T1 runs in split mode even with TR1 clear
        self.assertEqual(
            (c.ram[0x8B], c.bit(0x8F), c.serial.pulse_clock.call_count), (0xFC, 0, 1)
        )
        c.ram[0x89] = 0x33
        c.tick_timers(20)
        self.assertEqual(c.ram[0x8B], 0xFC)

    def test_interrupt_priority_nesting_and_reti(self):
        c = CPU()
        c.ram[0xA8] = 0x8A
        c.set_bit(0x8D, 1)
        c.step()
        self.assertEqual((c.pc, c.cycles, c.interrupt_stack), (0xB, 3, [0]))
        c.set_bit(0x8F, 1)
        c.step()
        self.assertEqual(c.interrupt_stack, [0])
        c.ram[0xB8] = 8
        c.step()
        self.assertEqual((c.pc, c.interrupt_stack, c.ram[0x81]), (0x1B, [0, 1], 11))
        c.code[0x1B] = 0x32
        c.step()
        self.assertEqual((c.pc, c.interrupt_stack, c.ram[0x81]), (0xD, [0], 9))
        c.code[0xD] = 0x32
        c.set_bit(0x8D, 1)
        c.step()
        self.assertEqual((c.pc, c.interrupt_stack), (1, []))
        c.step()
        self.assertEqual((c.pc, c.ram[8]), (0xB, 2))

    def test_interrupt_fixed_order_and_flags(self):
        for expected in (3, 11, 19, 27, 35):
            c = CPU()
            c.ram[0xA8], c.ram[0x88], c.ram[0x98] = 0x9F, 0xAF, 3
            index = (3, 11, 19, 27, 35).index(expected)
            c.ram[0xA8] &= ~((1 << index) - 1)
            c.poll_interrupts()
            self.assertEqual((c.pc, c.cycles), (expected, 2))
            if expected == 35:
                self.assertEqual(c.ram[0x98] & 3, 3)
            else:
                self.assertFalse(c.bit((0x89, 0x8D, 0x8B, 0x8F)[index]))

    def test_ie_ip_access_defers_interrupt(self):
        for op, x, y in (
            (0x75, 0xA8, 0x82),
            (0xE5, 0xB8, 0),
            (0xA2, 0xA9, 0),
            (0xD2, 0xB9, 0),
        ):
            c = CPU()
            c.ram[0xA8] = 0x82
            c.set_bit(0x8D, 1)
            c.code[:4] = bytes([op, x, y, 0])
            c.step()
            self.assertEqual(c.pc, ISA[op]["size"])
            c.step()
            self.assertEqual(c.pc, 11)

    def test_external_interrupt_sampling_and_level_release(self):
        c = CPU()
        c.ram[0xA8] = 0x81
        c.port_inputs[0xB0] &= ~4
        c.step()
        self.assertEqual(c.pc, 1)
        c.step()
        self.assertEqual((c.pc, c.cycles), (3, 4))
        c.port_inputs[0xB0] |= 4
        c.tick_timers(1)
        self.assertEqual(c.bit(0x89), 0)
        c = CPU()
        c.set_bit(0x88, 1)
        c.port_inputs[0xB0] &= ~4
        c.tick_timers(1)
        self.assertEqual(c.bit(0x89), 1)
        c.port_inputs[0xB0] |= 4
        c.tick_timers(1)
        self.assertEqual(c.bit(0x89), 1)

    def test_interrupt_entry_advances_timers(self):
        c = CPU()
        c.ram[0x89], c.ram[0xA8] = 1, 0x82
        c.set_bit(0x8C, 1)
        c.set_bit(0x8D, 1)
        c.step()
        self.assertEqual((c.cycles, c.ram[0x8A]), (3, 3))

    def test_instruction_catalog_timing(self):
        # Classic 12-clock table, Atmel instruction manual pp. 2-72–2-75.
        cycles = (
            "1221111111111111"
            "2221111111111111"
            "2221111111111111"
            "2221111111111111"
            "2212111111111111"
            "2212111111111111"
            "2212111111111111"
            "2212121111111111"
            "2211422222222222"
            "2221111111111111"
            "2212412222222222"
            "2211222222222222"
            "2211111111111111"
            "2211121122222222"
            "2222111111111111"
            "2222111111111111"
        )
        for op in range(256):
            if op != 0xA5:
                self.assertEqual(ISA[op]["cycles"], int(cycles[op]), f"{op:02X}")
        c = CPU()
        c.code[:5] = bytes([0xA0, 0x20, 0xB0, 0x20, 0xA3])
        for _ in range(3):
            c.step()
        self.assertEqual((c.pc, c.cycles, c.dptr), (5, 6, 1))

    def test_arithmetic_addressing_forms(self):
        for family in (0x20, 0x30, 0x90):
            for bank in range(4):
                for mode in range(5, 16):
                    c = CPU()
                    c.write(0xD0, bank << 3)
                    c.a, c.carry = 0x80, 1
                    c.ram[0x30] = 0xFF
                    if mode in (6, 7):
                        c.set_reg(mode & 1, 0x30)
                    elif mode >= 8:
                        c.set_reg(mode & 7, 0xFF)
                    expected = CPU()
                    expected.ram[:] = c.ram
                    expected.execute(family + 4, 0xFF)
                    c.execute(family + mode, 0x30)
                    self.assertEqual(
                        (c.a, c.ram[0xD0]), (expected.a, expected.ram[0xD0])
                    )

    def test_full_timer_periods(self):
        for timer in (0, 1):
            for mode, period in ((0, 8192), (1, 65536), (2, 256)):
                c = CPU()
                c.ram[0x89] = mode << (4 * timer)
                c.set_bit(0x8C + 2 * timer, 1)
                c.tick_timers(period - 1)
                self.assertEqual(c.bit(0x8D + 2 * timer), 0)
                c.tick_timers(1)
                self.assertEqual(
                    (c.ram[0x8A + timer], c.ram[0x8C + timer], c.bit(0x8D + 2 * timer)),
                    (0, 0, 1),
                )

    def test_interrupt_masking_and_ret_does_not_end_service(self):
        c = CPU()
        c.set_bit(0x8D, 1)
        c.step()
        self.assertEqual(c.pc, 1)
        c.ram[0xA8] = 0x80  # EA without ET0
        c.step()
        self.assertEqual(c.pc, 2)
        c.ram[0xA8] = 0x82
        c.step()
        self.assertEqual(c.pc, 11)
        c.code[11] = 0x22  # RET leaves priority in service
        c.step()
        c.set_bit(0x8D, 1)
        c.step()
        self.assertEqual((c.pc, c.interrupt_stack), (4, [0]))

    def test_priority_beats_polling_order_and_high_cannot_nest(self):
        c = CPU()
        c.ram[0xA8], c.ram[0xB8], c.ram[0x88] = 0x9F, 0x10, 0xAF
        c.ram[0x98] = 3
        c.poll_interrupts()
        self.assertEqual((c.pc, c.interrupt_stack), (35, [1]))
        c.poll_interrupts()
        self.assertEqual((c.pc, c.ram[0x81]), (35, 9))

    def test_pending_request_can_disappear_while_blocked(self):
        c = CPU()
        c.ram[0xA8] = 0x81
        c.interrupt_stack = [0]
        c.port_inputs[0xB0] &= ~4
        c.step()
        c.port_inputs[0xB0] |= 4
        c.step()
        c.interrupt_stack.clear()
        c.step()
        self.assertEqual(c.pc, 3)
        self.assertEqual(c.interrupt_stack, [])

    def test_high_priority_can_preempt_interrupt_entry(self):
        c = CPU()
        c.ram[0xA8], c.ram[0xB8], c.ram[0x89] = 0x8A, 8, 0x10
        c.ram[0x8B], c.ram[0x8D] = 0xFE, 0xFF
        c.set_bit(0x8E, 1)
        c.set_bit(0x8D, 1)
        c.step()
        self.assertEqual(
            (c.pc, c.cycles, c.instructions, c.interrupt_stack), (27, 5, 1, [0, 1])
        )
        self.assertEqual(c.ram[8:12], bytes([1, 0, 11, 0]))
