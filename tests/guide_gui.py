"""User-guide desktop acceptance tests; run explicitly with a graphical session."""

import faulthandler
import json
import unittest
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog
from types import SimpleNamespace
from unittest.mock import patch

import gui

from mcs51_studio.engine.assembler import import_hex
from mcs51_studio.hardware.board import Board


class GuideWorkbench(unittest.TestCase):
    setUpClass = classmethod(gui.WorkbenchUI.setUpClass.__func__)

    def setUp(self):
        app = self.app
        app.board = Board(app.cpu)
        for name, value in app.board.enabled.items():
            app.enabled_vars[name].set(value)
        for variable in app.switch_vars:
            variable.set(True)
        app.key_gate_var.set(False)
        app.analogue.set(0)
        app.speed.set("1000")
        gui.WorkbenchUI.setUp(self)
        self.errors = []
        previous = self.root.report_callback_exception
        self.root.report_callback_exception = lambda *error: self.errors.append(error)
        self.addCleanup(setattr, self.root, "report_callback_exception", previous)

    def tearDown(self):
        self.app.pause_execution()
        self.assertEqual(self.errors, [])

    def edit_byte(self, kind, address, value):
        app = self.app
        app.memory_kind.set(kind)
        app.memory_start.set(f"{address:04X}")
        app.refresh()
        with (
            patch.object(app.memory, "identify_row", return_value=str(address & ~15)),
            patch.object(
                app.memory, "identify_column", return_value=f"#{address % 16 + 2}"
            ),
            patch.object(simpledialog, "askstring", return_value=f"{value:02X}"),
        ):
            app.edit_memory(SimpleNamespace(x=0, y=0))

    def test_code_memory_patch_survives_hex_export(self):
        app = self.app
        app.replace_source("MOV A,#1\nINC A\nSJMP $")
        self.assertTrue(app.assemble())
        self.edit_byte("Code", 1, 0x42)
        self.assertEqual(app.cpu.code[1], 0x42)
        self.assertEqual(app.listing.item("0", "values")[1], "74 42")
        self.assertIn("modified", app.listing.item("0", "values")[2].lower())
        path = Path(self.temporary.name) / "patched.hex"
        with patch.object(filedialog, "asksaveasfilename", return_value=str(path)):
            app.export()
        self.assertEqual(import_hex(path.read_text()).code[1], 0x42)
        app.step()
        self.assertEqual(app.cpu.a, 0x42)
        self.assertIn("MOV A,#1", app.editor.get("1.0", "end-1c"))

    def test_breakpoint_stops_before_first_instruction_then_resumes(self):
        app = self.app
        app.replace_source("INC A\nINC A\nSJMP $")
        self.assertTrue(app.assemble())
        app.breakpoint_at_line(1)
        app.toggle_run()
        self.assertFalse(app.running)
        self.assertEqual((app.cpu.pc, app.cpu.a, app.cpu.instructions), (0, 0, 0))
        self.assertIn("Breakpoint", app.status.get())
        app.breakpoint_at_line(2)
        app.toggle_run()
        self.assertFalse(app.running)
        self.assertEqual((app.cpu.pc, app.cpu.a, app.cpu.instructions), (1, 1, 1))
        app.step()
        self.assertEqual((app.cpu.pc, app.cpu.a), (2, 2))
        app.reset()
        app.toggle_run()
        self.assertEqual(app.cpu.instructions, 0)

    def test_new_code_bytes_are_loaded_exported_and_cleared_by_reset(self):
        app = self.app
        app.replace_source("LJMP 100H")
        self.assertTrue(app.assemble())
        for address, value in (
            (0x100, 0x00),
            (0x101, 0x74),
            (0x102, 0x42),
            (0x103, 0x80),
            (0x104, 0xFE),
        ):
            self.edit_byte("Code", address, value)
        self.assertTrue(app.listing.exists(str(0x100)))
        path = Path(self.temporary.name) / "extended.hex"
        with patch.object(filedialog, "asksaveasfilename", return_value=str(path)):
            app.export()
        loaded = import_hex(path.read_text())
        self.assertTrue(set(range(0x100, 0x105)) <= loaded.used)
        self.assertEqual(
            loaded.code[0x100:0x105], bytes((0x00, 0x74, 0x42, 0x80, 0xFE))
        )
        app.step()
        self.assertEqual(app.cpu.pc, 0x100)
        self.assertFalse(app.debugger.terminated)
        app.step()
        self.assertEqual(app.cpu.pc, 0x101)
        app.step()
        self.assertEqual(app.cpu.a, 0x42)
        app.breakpoint_address.set("0103")
        app.toggle_address_breakpoint()
        self.assertIn(0x103, app.breakpoints)
        app.reset()
        self.assertNotIn(0x100, app.runtime_program.used)
        self.assertEqual(app.cpu.code[0x100], 0)

    def test_uart_link_reset_releases_paused_transmit_pin(self):
        app = self.app
        app.enabled_vars["uart"].set(True)
        app.enabled_vars["motor"].set(False)
        app.hardware_changed()
        app.board.uart.tx_line = 0
        app.board.update()
        self.assertEqual(app.cpu.bit(0xB0), 0)
        app.reset_uart_link()
        self.assertEqual(app.cpu.bit(0xB0), 1)

    def test_file_dialog_remembers_last_directory_and_plain_a_files(self):
        app = self.app
        folder = Path(self.temporary.name) / "lessons"
        folder.mkdir(exist_ok=True)
        source = folder / "lesson.a"
        source.write_text("MOV A,#42H\n")
        with patch.object(
            filedialog, "askopenfilename", return_value=str(source)
        ) as dialog:
            app.open_file()
        self.assertIn("*.a", dialog.call_args.kwargs["filetypes"][0][1].split())
        self.assertEqual(app.editor.get("1.0", "end-1c"), source.read_text())
        with patch.object(filedialog, "asksaveasfilename", return_value="") as dialog:
            app.save_source(save_as=True)
        self.assertEqual(Path(dialog.call_args.kwargs["initialdir"]), folder)

    def test_custom_batch_validation_and_saved_settings(self):
        app = self.app
        app.replace_source("INC A\nSJMP $")
        self.assertTrue(app.assemble())
        app.observe_outputs.set(False)
        self.addCleanup(app.observe_outputs.set, True)
        for invalid in ("", "0", "-1", "abc", "1.5", "1000001"):
            app.speed.set(invalid)
            with patch.object(messagebox, "showerror") as dialog:
                app.toggle_run()
            self.assertFalse(app.running, invalid)
            self.assertEqual(app.cpu.instructions, 0)
            dialog.assert_called_once()
        app.speed.set("7")
        app.toggle_run()
        self.assertTrue(app.running)
        self.assertEqual(app.cpu.instructions, 7)
        app.pause_execution()
        app.save_settings()
        settings = json.loads(app.settings_path.read_text())
        self.assertEqual(settings["batch_size"], 7)

    def test_bitfield_edits_only_bit_addressable_locations(self):
        app = self.app
        for target, address, editable in (
            ("ACC", 0xE0, True),
            ("PSW", 0xD0, True),
            ("20", 0x20, True),
            ("2F", 0x2F, True),
            ("TMOD", 0x89, False),
            ("30", 0x30, False),
        ):
            with self.subTest(target=target):
                app.bitfield_target.set(target)
                app.select_bitfield()
                before = app.cpu.ram[address]
                app.bitfield_buttons[7].invoke()
                self.assertEqual(
                    app.cpu.ram[address], before ^ (0x80 if editable else 0)
                )
                self.assertEqual(
                    app.bitfield_buttons[7].instate(["disabled"]), not editable
                )
        before = app.bitfield_address
        for target in ("80FF", "80+1", "UNKNOWN", "-1", "84"):
            with patch.object(messagebox, "showerror") as dialog:
                app.bitfield_target.set(target)
                app.select_bitfield()
                dialog.assert_called_once()
            self.assertEqual(app.bitfield_address, before)
        # Editing the port latch must not bypass a closed external switch.
        app.bitfield_target.set("P2")
        app.select_bitfield()
        app.switch_vars[0].set(False)
        app.switch_changed()
        app.bitfield_buttons[0].invoke()
        app.bitfield_buttons[0].invoke()
        self.assertEqual(app.cpu.ram[0xA0], 255)
        self.assertEqual(app.cpu.bit(0xA0), 0)

    def test_address_breakpoint_toggle_validation_and_clear(self):
        app = self.app
        app.replace_source("MOV A,#1\nINC A\nSJMP $\nDB 0")
        self.assertTrue(app.assemble())
        for address in ("0000", "0002"):
            app.breakpoint_address.set(address)
            app.toggle_address_breakpoint()
        self.assertEqual(app.breakpoints, {0, 2})
        app.toggle_address_breakpoint()
        self.assertEqual(app.breakpoints, {0})
        for invalid in ("0001", "0005", "FFFF", "-1", "xyz"):
            app.breakpoint_address.set(invalid)
            with patch.object(messagebox, "showerror") as dialog:
                app.toggle_address_breakpoint()
                dialog.assert_called_once()
        self.assertEqual(app.breakpoints, {0})
        app.clear_breakpoints()
        self.assertEqual(app.breakpoints, set())

    def test_memory_go_rejects_invalid_addresses(self):
        app = self.app
        app.memory_kind.set("Code")
        app.memory_start.set("1234")
        app.goto_memory()
        self.assertEqual(app.memory.get_children()[0], str(0x1200))
        for invalid in ("-1", "10000", "", "garbage"):
            before = app.memory.get_children()
            app.memory_start.set(invalid)
            with patch.object(messagebox, "showerror") as dialog:
                app.goto_memory()
                dialog.assert_called_once()
            self.assertEqual(app.memory.get_children(), before)

    def test_settings_restore_experiment_uart_batch_and_directory(self):
        app = self.app
        app.batch_size = 321
        app.last_directory = self.temporary.name
        app.board.set_keypad_mode("Radio")
        app.board.experiment.switch_bounce = True
        app.board.uart.configure(9600, 2, data_bits=7, stop_bits=2)
        app.save_settings()
        app.board = Board(app.cpu)
        app.batch_size = 1000
        app.last_directory = None
        app.load_settings()
        self.assertEqual(app.board.experiment.keypad_mode, "Radio")
        self.assertTrue(app.board.experiment.switch_bounce)
        self.assertEqual(app.board.uart.framing, "7E2")
        self.assertEqual(app.batch_size, 321)
        self.assertEqual(app.last_directory, self.temporary.name)

    def test_lcd_rom_symbols_and_motor_sensor_are_visible(self):
        app = self.app
        app.board.lcd.byte(0x0C, 0)
        for code in (92, 126, 127):
            app.board.lcd.byte(code, 1)
        app.draw_lcd()
        text = [
            app.lcd_canvas.itemcget(item, "text")
            for item in app.lcd_canvas.find_all()
            if app.lcd_canvas.type(item) == "text"
        ]
        self.assertEqual(text[:3], ["¥", "→", "←"])
        app.motor_speed_changed("25")
        self.assertEqual(app.board.experiment.motor_speed, 25)
        app.reset()
        self.assertEqual(app.board.experiment.motor_speed, 25)
        # The shaft points at the top sensor precisely when T1 is held low.
        app.board.motor_position = 0
        app.board.update()
        app.draw_motor()
        lines = [
            item
            for item in app.motor_canvas.find_all()
            if app.motor_canvas.type(item) == "line"
        ]
        shaft = app.motor_canvas.coords(lines[0])
        self.assertAlmostEqual(shaft[0], shaft[2])
        self.assertLess(shaft[3], shaft[1])

    def test_new_controls_fit_at_minimum_window_size(self):
        app = self.app
        self.root.deiconify()
        self.addCleanup(self.root.withdraw)
        self.root.geometry("960x640")
        self.root.update()
        app.reset_layout()
        app.show_bottom("Listing")
        self.root.update()
        controls = app.listing_controls
        for child in controls.pack_slaves():
            self.assertTrue(child.winfo_ismapped())
            self.assertEqual(child.winfo_width(), child.winfo_reqwidth())
            self.assertLessEqual(
                child.winfo_x() + child.winfo_width(), controls.winfo_width()
            )
        for button in app.bitfield_buttons.values():
            self.assertLessEqual(
                button.winfo_x() + button.winfo_width(), button.master.winfo_width()
            )


if __name__ == "__main__":
    faulthandler.enable()
    faulthandler.dump_traceback_later(180, exit=True)
    try:
        unittest.main(verbosity=2)
    finally:
        faulthandler.cancel_dump_traceback_later()
