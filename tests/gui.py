"""Desktop integration tests. Run explicitly with a graphical session."""

import faulthandler
import os
import tempfile
import unittest
from pathlib import Path
from tkinter import TclError, Tk, filedialog, messagebox, ttk
from types import SimpleNamespace
from unittest.mock import patch

from mcs51_studio.ui.application import App
from mcs51_studio.ui.icon import prepare_process_identity


class WorkbenchUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="mcs51-ui-")
        cls.addClassCleanup(cls.temporary.cleanup)
        environment = patch.dict(
            os.environ,
            {"MCS51_STUDIO_SETTINGS": str(Path(cls.temporary.name) / "settings.json")},
        )
        environment.start()
        cls.addClassCleanup(environment.stop)

        def fail(title, text, **kwargs):
            raise AssertionError(f"{title}: {text}")

        dialogs = patch.object(messagebox, "showerror", fail)
        dialogs.start()
        cls.addClassCleanup(dialogs.stop)
        prepare_process_identity()
        cls.root = Tk(className="MCS51Studio")
        cls.addClassCleanup(cls.root.destroy)
        cls.root.withdraw()
        cls.app = App(cls.root)
        cls.root.update()

    def setUp(self):
        from mcs51_studio.resources import LED_COUNTER

        self.root.withdraw()
        if self.app.instruments is not None:
            self.app.instruments.close()
        self.app.instrument_settings = {
            "probes": ["P1.0", "P1.1", "P3.0", "P3.1"],
            "trigger": "Free Run",
            "edge": "Rising",
            "duration": 1000,
        }
        view = self.app.editor_view
        view.close_completion()
        view.hide_find()
        view.search_panel.query.set("")
        view.search_panel.match_case.set(False)
        view.search_panel.whole_word.set(False)
        view.change_zoom(reset=True)
        self.app.layout_settings = {}
        self.app.board_scroll.windowing_system = self.root.tk.call(
            "tk", "windowingsystem"
        )
        self.app.replace_source(LED_COUNTER)
        self.app.reset()
        self.app.reset_layout()
        self.app.peripheral_tabs.select(0)
        self.root.update()

    def test_scroll_container_preserves_tk_methods_and_cleans_up(self):
        from mcs51_studio.ui.widgets import ScrollableFrame

        root = self.root
        errors = []
        previous = root.report_callback_exception
        root.report_callback_exception = lambda *error: errors.append(error)
        self.addCleanup(setattr, root, "report_callback_exception", previous)
        unrelated = root.bind("<MouseWheel>", lambda event: None, add=True)
        self.addCleanup(root.unbind, "<MouseWheel>", unrelated)
        for _ in range(5):
            frame = ScrollableFrame(root)
            frame.pack()
            self.assertTrue(callable(frame._root))
            self.assertIs(frame.nametowidget(str(root)), root)
            self.assertIs(frame._root(), root)
            # Exercise event substitution and destruction, including pending work.
            frame.event_generate("<Configure>", width=400, height=300)
            bindings = dict(frame._bindings)
            frame._schedule_extent()
            frame.destroy()
            root.update()
            for sequence, binding in bindings.items():
                self.assertNotIn(binding, root.bind(sequence))
            self.assertIn(unrelated, root.bind("<MouseWheel>"))
        self.assertEqual(errors, [])

    def test_external_memory_and_processor_errors(self):
        app = self.app
        app.replace_source(
            "MOV DPTR,#1234H\nMOV A,#5AH\nMOVX @DPTR,A\nCLR A\nMOVX A,@DPTR"
        )
        self.assertTrue(app.assemble())
        for _ in range(5):
            app.step()
        self.assertEqual(app.cpu.a, 0x5A)
        app.memory_kind.set("XDATA")
        app.memory_start.set("1234")
        app.refresh()
        self.assertEqual(app.memory.item("4656", "values")[5], "5A")
        with (
            patch.object(app.memory, "identify_row", return_value="4656"),
            patch.object(app.memory, "identify_column", return_value="#6"),
            patch(
                "mcs51_studio.ui.application.simpledialog.askstring", return_value="A5"
            ),
        ):
            app.edit_memory(SimpleNamespace(x=0, y=0))
        self.assertEqual(app.cpu.xram[0x1234], 0xA5)
        self.assertEqual(app.cpu.code[0x1234], 0)
        app.memory_start.set("FFFF")
        app.refresh()
        self.assertEqual(app.memory.get_children()[-1], "65520")
        app.memory_kind.set("RAM")
        app.refresh()
        self.assertEqual(app.memory.get_children()[-1], "112")
        app.replace_source("MOV R0,#90H\nMOV @R0,#55H")
        self.assertTrue(app.assemble())
        app.step()
        with patch.object(messagebox, "showerror") as error:
            app.step()
        self.assertIn("outside Classic 8051 RAM", error.call_args.args[1])
        self.assertEqual(app.cpu.ram[0x90], 255)

    def test_wiring_and_measurement_tools(self):
        import copy

        from mcs51_studio.hardware.wiring import shared_connections

        app, root = self.app, self.root
        old_mapping = copy.deepcopy(app.board.mapping)
        old_enabled = app.board.enabled.copy()
        old_gate = app.board.key_gate
        try:
            app.wiring_window("leds")
            root.update()
            tools = app.instruments
            self.assertEqual(tools.selected_device, "leds")
            self.assertTrue(tools.pinout.find_all())
            tools.select_pin("P1.0")
            self.assertIn("LED Bank", tools.detail.get("1.0", "end"))
            tools.preset.set("LED Counter")
            tools.apply_preset()
            self.assertEqual(shared_connections(app.board), [])
            with patch(
                "mcs51_studio.ui.instruments.simpledialog.askstring",
                return_value="My Experiment",
            ):
                tools.save_preset()
            app.wiring_presets.clear()
            app.load_settings()
            self.assertIn("My Experiment", app.wiring_presets)
            app.replace_source("CLR P1.0\nLOOP: SETB P1.0\nNOP\nCLR P1.0\nSJMP LOOP")
            app.show_instruments("Logic Analyzer")
            tools.logic.duration.set("100")
            tools.logic.arm()
            for _ in range(90):
                app.step_once()
            tools.logic.draw()
            self.assertEqual(app.capture.state, "Complete")
            self.assertIn("Duty 40 %", tools.logic.metrics.get())
            tools.logic.zoom(0.5)
            self.assertLess(tools.logic.bounds[1] - tools.logic.bounds[0], 100)
            tools.logic.place_cursor(SimpleNamespace(x=150, y=50))
            tools.logic.place_cursor(SimpleNamespace(x=250, y=50))
            self.assertIn("Δt=", tools.logic.metrics.get())
            app.show_instruments("DAC Scope")
            app.board.enabled["dac"] = True
            app.cpu.write(0x80, 0x7F)
            for value in (0, 64, 128, 255):
                app.cpu.write(0x90, value)
                app.cpu.cycles += 10
                app.board.update()
            tools.dac.draw()
            tools.dac.freeze()
            self.assertEqual(len(tools.dac.frozen), 4)
            tools.dac.place_cursor(SimpleNamespace(x=150, y=50))
            tools.dac.place_cursor(SimpleNamespace(x=250, y=50))
            self.assertIn("ΔV=", tools.dac.metrics.get())
            tools.window.geometry("900x640")
            root.update()
            self.assertLessEqual(tools.logic.canvas.winfo_reqwidth(), 900)
            app.reset()
            self.assertEqual(app.capture.state, "Idle")
            self.assertIsNone(tools.dac.frozen)
        finally:
            if app.instruments:
                app.instruments.close()
            app.board.mapping, app.board.enabled, app.board.key_gate = (
                old_mapping,
                old_enabled,
                old_gate,
            )
            for name, variable in app.enabled_vars.items():
                variable.set(old_enabled[name])
            app.key_gate_var.set(old_gate)
            app.board.update()

    def test_editor_and_workspace(self):
        verify_editor_workflow(self.app, self.root, Path(self.temporary.name))

    def test_board_scrolling_and_hardware_rows(self):
        app, root = self.app, self.root
        root.deiconify()
        root.geometry("960x640")
        root.update()
        app.reset_layout()
        app.workspace.select(app.board_tab)
        root.update()
        scroll = app.board_scroll
        scroll.canvas.focus_force()
        root.update()
        self.assertGreater(
            scroll.content.winfo_reqheight(), scroll.canvas.winfo_height()
        )
        # Leave enough travel for both wheel deltas, regardless of the native
        # font metrics and the resulting board height.
        spacer = ttk.Frame(scroll.content, height=200)
        spacer.pack()
        self.addCleanup(spacer.destroy)
        root.update()
        scroll.canvas.yview_moveto(0)
        start = scroll.canvas.canvasy(0)
        event = SimpleNamespace(widget=app.led_canvas, num=None, delta=0)
        scroll.wheel(event)
        self.assertEqual(scroll.canvas.canvasy(0), start)
        scroll.windowing_system = "aqua"
        event.delta = -1
        self.assertEqual(
            scroll.wheel(event),
            "break",
            f"mapped={scroll.canvas.winfo_ismapped()}, "
            f"tab={app.workspace.select()}, "
            f"heights={scroll.content.winfo_reqheight()}/{scroll.canvas.winfo_height()}",
        )
        self.assertEqual(scroll.canvas.canvasy(0) - start, 1)
        start = scroll.canvas.canvasy(0)
        scroll.windowing_system = "win32"
        event.delta = -120
        scroll.wheel(event)
        self.assertEqual(scroll.canvas.canvasy(0) - start, 40)
        event.delta, event.num = 0, 4
        scroll.wheel(event)
        self.assertEqual(scroll.canvas.canvasy(0), start)
        event.widget, event.num, event.delta = app.uart_output, None, -120
        scroll.wheel(event)
        self.assertEqual(scroll.canvas.canvasy(0), start)
        app.peripheral_tabs.select(app.hardware_tab)
        root.update()
        columns = {
            int(toggle.grid_info()["column"]) for toggle in app.hardware_toggles.items
        }
        self.assertGreater(len(columns), 1)
        self.assertEqual(len(app.hardware_toggles.items), len(app.board.enabled))
        first_name = next(iter(app.enabled_vars))
        before = app.board.enabled[first_name]
        app.hardware_toggles.items[0].invoke()
        self.assertEqual(app.board.enabled[first_name], not before)
        app.hardware_toggles.items[0].invoke()
        root.geometry("1370x900")
        app.reset_layout()
        root.update()
        wide_columns = {
            int(toggle.grid_info()["column"]) for toggle in app.hardware_toggles.items
        }
        self.assertGreaterEqual(len(wide_columns), len(columns))
        last = app.hardware_toggles.items[-1]
        self.assertLessEqual(
            app.hardware_toggles.winfo_y() + last.winfo_y() + last.winfo_height(),
            app.hardware_tab.winfo_height(),
        )
        scroll.canvas.yview_moveto(0)
        event.widget, event.delta = app.hardware_toggles.items[0], 12000
        scroll.wheel(event)
        self.assertGreaterEqual(scroll.canvas.canvasy(0), 0)

    def test_board_feedback_and_controls(self):
        app = self.app
        self.root.deiconify()
        app.workspace.select(app.board_tab)
        self.root.update()
        app.enabled_vars["switches"].set(True)
        app.hardware_changed()
        before = app.switch_vars[0].get()
        app.switch_buttons[0].invoke()
        self.assertEqual(app.board.switches[0], not before)
        self.assertIn(str(int(not before)), app.switch_buttons[0].cget("text"))
        app.switch_buttons[0].invoke()
        for name in ("display", "leds", "keypad"):
            app.enabled_vars[name].set(False)
        app.hardware_changed()
        app.board.digits = [0] * 4
        app.refresh()
        self.assertEqual(app.board_badges["display"].cget("text"), "○ Disabled")
        for item in app.segment_canvas.find_all():
            if app.segment_canvas.type(item) in ("line", "oval"):
                self.assertEqual(app.segment_canvas.itemcget(item, "fill"), "#303D55")
        app.key((0, 0), True)
        self.assertFalse(app.board.keys)
        self.assertTrue(app.keypad_buttons[0].instate(["disabled"]))
        for name in ("display", "leds", "keypad"):
            app.enabled_vars[name].set(True)
        app.hardware_changed()
        app.key((0, 0), True)
        self.assertIn((0, 0), app.board.keys)
        app.key((0, 0), False)
        app.analogue.set(2.5)
        app.analogue_changed(2.5)
        app.key_gate_var.set(True)
        app.key_gate_changed()
        app.reset()
        self.assertEqual(app.board.analogue, 2.5)
        self.assertTrue(app.board.key_gate)
        app.board.uart.received.extend([65, 66])
        app.refresh()
        self.assertEqual(app.uart_output.get("1.0", "end-1c"), "AB")
        app.clear_uart_output()
        app.refresh()
        self.assertEqual(app.uart_output.get("1.0", "end-1c"), "")
        self.assertEqual(app.board.uart.received[-2:], [65, 66])
        self.assertEqual(len(app.port_values), 4)
        app.analogue.set(0)
        app.key_gate_var.set(False)

    def test_layout_waits_for_mapping_and_survives_resize(self):
        root, app = self.root, self.app
        root.withdraw()
        root.update()
        app._layout_initialized = False
        app.layout_settings = {}
        app.queue_layout()
        root.update()
        self.assertFalse(app._layout_initialized)
        # Do not call Reset Layout after mapping: startup must work by itself.
        root.geometry("960x640")
        root.deiconify()
        root.update()
        self.assertTrue(app._layout_initialized)
        for geometry in ("960x640", "1370x900", "1024x768", "960x640"):
            root.geometry(geometry)
            root.update()
            self.assertGreaterEqual(app.horizontal.winfo_height(), 280)
            self.assertGreaterEqual(app.center.winfo_width(), 400)
            self.assertGreaterEqual(app.inspector.winfo_width(), 240)
            self.assertGreaterEqual(app.bottom.winfo_height(), 140)
        # Resizing must not keep restoring defaults over the user's split.
        app.vertical.sashpos(0, 310)
        root.update()
        self.assertEqual(app.vertical.sashpos(0), 310)

    def test_collapsed_saved_layout_is_recovered(self):
        root, app = self.root, self.app
        root.deiconify()
        root.update()
        for position in (0, -1000, 100000):
            app.layout_settings = {
                "version": 2,
                "horizontal": [position],
                "vertical": position,
            }
            app.restore_layout()
            root.update()
            self.assertGreaterEqual(app.horizontal.winfo_height(), 280)
            self.assertGreaterEqual(app.center.winfo_width(), 400)
            self.assertGreaterEqual(app.inspector.winfo_width(), 240)
            self.assertGreaterEqual(app.bottom.winfo_height(), 140)
        app.layout_settings = {
            "version": 2,
            "visible": {"inspector": False, "bottom": False},
        }
        app.restore_layout()
        root.update()
        self.assertEqual(len(app.horizontal.panes()), 1)
        self.assertEqual(len(app.vertical.panes()), 1)

    def test_inspector_and_legacy_layout(self):
        app = self.app
        self.assertFalse(hasattr(app, "sidebar"))
        self.assertEqual(set(app.capture_layout()["visible"]), {"inspector", "bottom"})
        app.cpu.ram[0xD0] = 0xDC
        app.refresh()
        self.assertEqual(app.flag_values["CY"].get(), "1")
        self.assertEqual(app.flag_values["P"].get(), "0")
        self.assertEqual(app.flag_values["BANK"].get(), "3")
        self.assertTrue(app.assemble())
        self.assertEqual(app.instruction_address.get(), "0000")
        self.assertEqual(app.instruction_bytes.get(), "74 FF")
        app.layout_settings = {
            "horizontal": [175, 1100],
            "visible": {"sidebar": True, "inspector": False, "bottom": True},
        }
        app.restore_layout()
        self.assertEqual(len(app.horizontal.panes()), 1)
        self.assertFalse(app.inspector_visible.get())

    def test_native_popup_focus(self):
        root, app = self.root, self.app
        root.deiconify()
        # Tcl-created popup windows are absent from Tkinter's widget registry,
        # just like the list inside a ttk combobox's native popdown.
        popup = ".native_focus_popup"
        root.tk.call("toplevel", popup)
        self.addCleanup(root.tk.call, "destroy", popup)
        root.update()
        root.tk.call("focus", "-force", popup)
        root.update()
        with self.assertRaises(KeyError):
            root.focus_get()
        app.cpu.a = 42
        app.refresh()
        self.assertEqual(app.reg_vars["ACC"].get(), "2A")
        with patch.object(app.editor_view, "paste") as paste:
            app.edit_action("<<Paste>>")
            paste.assert_not_called()

    def test_clipboard_paste_and_execution(self):
        app, view = self.app, self.app.editor_view
        app.replace_source("MOV A,#9\n")
        self.assertTrue(app.assemble())
        app.editor.tag_add("sel", "1.7", "1.8")
        with patch.object(app.editor, "clipboard_get", return_value="\ufeff3\r\nINC A"):
            app.editor.event_generate("<<Paste>>")
        self.assertEqual(app.editor.get("1.0", "end-1c"), "MOV A,#3\nINC A\n")
        self.assertTrue(app.dirty)
        app.step()
        app.step()
        self.assertEqual(app.cpu.a, 4)
        view.undo()
        self.assertEqual(app.editor.get("1.0", "end-1c"), "MOV A,#9\n")
        view.redo()
        self.assertEqual(app.editor.get("1.0", "end-1c"), "MOV A,#3\nINC A\n")
        view.select_all()
        with (
            patch.object(app.editor, "clipboard_clear"),
            patch.object(app.editor, "clipboard_append") as copied,
        ):
            app.editor.event_generate("<<Copy>>")
            copied.assert_called_once_with("MOV A,#3\nINC A\n")
            app.editor.event_generate("<<Cut>>")
        self.assertEqual(app.editor.get("1.0", "end-1c"), "")
        view.undo()
        self.assertEqual(app.editor.get("1.0", "end-1c"), "MOV A,#3\nINC A\n")

    def test_clipboard_failures_keep_source(self):
        app, view = self.app, self.app.editor_view
        source = "MOV A,#1\n"
        app.replace_source(source)
        view.select_all()
        with patch.object(
            app.editor, "clipboard_get", side_effect=TclError("non-text")
        ):
            view.paste()
        self.assertEqual(app.editor.get("1.0", "end-1c"), source)
        for value in ("", "NOP\0"):
            with patch.object(app.editor, "clipboard_get", return_value=value):
                view.paste()
            self.assertEqual(app.editor.get("1.0", "end-1c"), source)
        with patch.object(app.editor, "clipboard_clear", side_effect=TclError("busy")):
            view.cut()
        self.assertEqual(app.editor.get("1.0", "end-1c"), source)
        self.assertFalse(app.document_modified)

    def test_line_editing_and_zoom_boundaries(self):
        app, view = self.app, self.app.editor_view
        source = "    MOV A,#1\n    INC A"
        app.replace_source(source)
        app.editor.mark_set("insert", "2.end")
        view.duplicate_lines()
        self.assertEqual(app.editor.get("1.0", "end-1c"), source + "\n    INC A")
        view.undo()
        self.assertEqual(app.editor.get("1.0", "end-1c"), source)
        app.editor.mark_set("insert", "2.0")
        view.delete_lines()
        self.assertEqual(app.editor.get("1.0", "end-1c"), "    MOV A,#1")
        view.undo()
        app.editor.mark_set("insert", "2.0")
        view.move_lines(-1)
        self.assertEqual(app.editor.get("1.0", "end-1c"), "    INC A\n    MOV A,#1")
        view.undo()
        app.editor.tag_remove("sel", "1.0", "end")
        app.editor.tag_add("sel", "1.0", "2.0")
        view.indent()
        self.assertEqual(app.editor.get("1.0", "end-1c"), "        MOV A,#1\n    INC A")
        view.undo()
        app.editor.tag_remove("sel", "1.0", "end")
        app.editor.mark_set("insert", "1.4")
        view.backspace()
        self.assertEqual(app.editor.get("1.0", "end-1c"), "MOV A,#1\n    INC A")
        view.undo()
        app.editor.mark_set("insert", "1.7")
        view.smart_home()
        self.assertEqual(app.editor.index("insert"), "1.4")
        view.smart_home()
        self.assertEqual(app.editor.index("insert"), "1.0")
        app.editor.tag_add("sel", "1.4", "1.end")
        view.newline()
        view.undo()
        self.assertEqual(app.editor.get("1.0", "end-1c"), source)
        for _ in range(30):
            view.change_zoom(1)
        self.assertEqual(view.font_size, 24)
        for _ in range(30):
            view.change_zoom(-1)
        self.assertEqual(view.font_size, 10)
        view.change_zoom(reset=True)
        self.assertEqual(view.zoom.get(), "100%")
        self.assertEqual(app.editor.get("1.0", "end-1c"), source)

    def test_search_options_unicode_and_atomic_replacement(self):
        app, view = self.app, self.app.editor_view
        search = view.search_panel
        source = "; 😀 MOV movers MOV\nMOV A,#1\n"
        app.replace_source(source)
        app.editor.mark_set("insert", "1.0")
        search.query.set("mov")
        search.whole_word.set(True)
        self.assertTrue(search.find_next())
        self.assertEqual(app.editor.get(*app.editor.tag_ranges("search")), "MOV")
        self.assertEqual(search.result.get(), "1 of 3")
        search.match_case.set(True)
        self.assertFalse(search.find_next())
        search.query.set("MOV")
        search.replacement.set("INC")
        search.replace_all()
        self.assertEqual(app.editor.get("1.0", "end-1c"), source.replace("MOV", "INC"))
        view.undo()
        self.assertEqual(app.editor.get("1.0", "end-1c"), source)
        search.whole_word.set(False)
        app.replace_source("DB 'a.b','axb'\n")
        search.query.set("a.b")
        search.replacement.set(r"\1")
        search.replace_all()
        self.assertEqual(app.editor.get("1.0", "end-1c"), "DB '\\1','axb'\n")
        view.undo()
        self.assertEqual(app.editor.get("1.0", "end-1c"), "DB 'a.b','axb'\n")
        app.replace_source("NOP")
        app.editor.mark_set("insert", "1.0")
        search.query.set("NOP")
        self.assertTrue(search.find_next(True))
        self.assertTrue(search.find_next(True))
        search.query.set("")
        self.assertFalse(search.find_next())

    def test_completion_produces_assembled_code(self):
        app, view = self.app, self.app.editor_view
        self.root.deiconify()
        app.replace_source("MO")
        app.editor.mark_set("insert", "end-1c")
        app.editor.focus_force()
        self.root.update()
        view.complete()
        self.assertIsNotNone(view.completion)
        words = list(view.completion.list.get(0, "end"))
        self.assertIn("MOV", words)
        view.completion.list.selection_clear(0, "end")
        view.completion.list.selection_set(words.index("MOV"))
        view.completion.accept()
        view.insert_text(" A,#1\nMOV R0,A\n")
        self.assertTrue(app.assemble())
        app.step()
        app.step()
        self.assertEqual((app.cpu.a, app.cpu.reg(0)), (1, 1))
        app.replace_source("loop:NOP\nSJMP lo")
        app.editor.mark_set("insert", "end-1c")
        view.complete()
        self.assertEqual(view.completion.list.get(0), "loop")
        view.completion.accept()
        self.assertTrue(app.assemble())

    def test_assembly_errors_block_stale_execution(self):
        app, view = self.app, self.app.editor_view
        app.replace_source("MOV A,#1")
        self.assertTrue(app.assemble())
        app.step()
        before = app.cpu.instructions
        # Do not drain the event queue: execution must also detect a pending edit.
        app.editor.delete("1.0", "end")
        app.editor.insert("1.0", "; 😀 café\nNOP\nMOV A,#999")
        app.toggle_run()
        self.assertIsNone(app.program)
        self.assertFalse(app.running)
        self.assertEqual(app.cpu.instructions, before)
        self.assertEqual(view.error_line, 3)
        self.assertEqual(app.editor.index("insert"), "3.0")
        self.assertTrue(app.editor.tag_ranges("error"))
        app.replace_source("MOV A,#2")
        app.step()
        self.assertEqual(app.cpu.a, 2)
        self.assertIsNone(view.error_line)
        for source in ("", "\n; comments only\n"):
            app.replace_source(source)
            self.assertFalse(app.assemble())
            app.toggle_run()
            self.assertFalse(app.running)
            self.assertIsNone(app.program)

    def test_failed_save_as_keeps_path_and_dirty_state(self):
        app, view = self.app, self.app.editor_view
        path = Path(self.temporary.name) / "old.asm"
        path.write_text("NOP", encoding="utf-8")
        app.replace_source("NOP", path)
        app.editor.mark_set("insert", "end-1c")
        view.insert_text("\nINC A")
        chosen = Path(self.temporary.name) / "new.asm"
        with (
            patch.object(filedialog, "asksaveasfilename", return_value=str(chosen)),
            patch(
                "mcs51_studio.ui.application.write_source",
                side_effect=OSError("full disk"),
            ),
            patch.object(messagebox, "showerror") as error,
        ):
            self.assertFalse(app.save_source(True))
            error.assert_called_once()
        self.assertEqual(app.path, path)
        self.assertTrue(app.document_modified)
        self.assertEqual(path.read_text(), "NOP")
        self.assertFalse(chosen.exists())

    def test_large_document_and_unicode_highlighting(self):
        app, view = self.app, self.app.editor_view
        self.root.deiconify()
        app.replace_source("; 😀 unicode\n" + "NOP\n" * 5000)
        self.root.update()
        view.highlight()
        self.assertEqual(
            app.editor.get(*app.editor.tag_ranges("instruction")[:2]), "NOP"
        )
        app.editor.see("4500.0")
        self.root.update()
        view.highlight()
        self.assertIn("instruction", app.editor.tag_names("4500.0"))
        self.assertTrue(app.assemble())
        self.assertEqual(len(app.program.used), 5000)

    def test_program_termination_preserves_results_until_reset(self):
        app = self.app
        app.debugger.watches.clear()
        app.replace_source("ORG 0000H\nMOV A,#25H\nMOV B,#15H\nADD A,B\nEND")
        self.assertTrue(app.assemble())
        for action in (app.toggle_run, app.step):
            with self.subTest(action=action.__name__):
                app.reset()
                if action == app.step:
                    app.step()
                    app.step()
                action()
                while app.running:
                    self.root.update()
                self.assertEqual((app.cpu.a, app.cpu.ram[0xF0]), (0x3A, 0x15))
                self.assertEqual((app.cpu.pc, app.cpu.instructions), (7, 3))
                self.assertIsNone(app.run_after)
                self.assertIn("Program terminated", app.status.get())
                self.assertEqual(app.machine_state.get(), "TERMINATED")
                self.assertEqual(app.current_instruction.get(), "Program terminated")
                self.assertEqual(app.instruction_state.get(), "Reset to run again")
                self.assertEqual(app.instruction_timing.get(), "No next instruction")
                self.assertEqual(app.instruction_bytes.get(), "—")
                self.assertEqual(app.run_button.cget("text"), "Run  F5")
                self.assertEqual(app.reg_vars["ACC"].get(), "3A")
                for _ in range(2):
                    app.toggle_run()
                    app.step()
                self.assertEqual(
                    (app.cpu.pc, app.cpu.instructions, app.cpu.a), (7, 3, 0x3A)
                )
                self.assertIsNone(app.run_after)
                app.reset()
                self.assertEqual(app.machine_state.get(), "READY")
                self.assertEqual(app.instruction_state.get(), "Ready to execute")
                self.assertEqual((app.cpu.pc, app.cpu.a), (0, 0))
                app.step()
                self.assertEqual((app.cpu.a, app.cpu.instructions), (0x25, 1))

    def test_visible_output_transitions(self):
        app = self.app
        app.replace_source("loop: CPL P1.0\nSJMP loop")
        app.assemble()
        app.speed.set("1000")
        app.observe_outputs.set(True)
        masks = []
        for _ in range(4):
            app.running = True
            app.run_batch()
            app.pause_execution()
            masks.append(app.board.led_mask)
        self.assertEqual(masks, [1, 0, 1, 0])
        app.cpu.write(0x90, 0xFC)
        app.board.update()
        app.refresh()
        self.assertIn("0000 0011", app.led_readout.cget("text"))
        self.assertIn("3 decimal", app.led_readout.cget("text"))
        self.assertEqual(app.cpu.instructions, 7)
        app.observe_outputs.set(False)
        with patch("mcs51_studio.ui.application.time.monotonic", return_value=0):
            app.running = True
            app.run_batch()
            app.pause_execution()
        self.assertEqual(app.cpu.instructions, 1007)
        app.observe_outputs.set(True)

    def test_debugger_controls_watches_and_stack(self):
        app = self.app
        app.debugger.watches.clear()
        app.observe_outputs.set(False)
        app.replace_source("LCALL sub\nINC A\nSJMP $\nsub: INC A\nRET")
        self.assertTrue(app.assemble())
        app.debug_run("over")
        self.assertFalse(app.running)
        self.assertEqual((app.cpu.pc, app.cpu.a), (3, 1))
        self.assertIn("Target reached", app.status.get())
        self.assertIn("Cost:", app.debug_explanation.get("1.0", "end"))
        app.reset()
        app.step()
        self.assertIn("Return 0003", app.stack_text.get("1.0", "end"))
        app.debug_run("out")
        self.assertEqual(app.cpu.pc, 3)
        app.watch_expression.insert(0, "ACC")
        app.watch_stop.set(True)
        app.add_watch()
        app.toggle_run()
        self.assertFalse(app.running)
        self.assertEqual(app.cpu.a, 2)
        self.assertIn("ACC changed", app.status.get())
        self.assertEqual(app.reg_entries["ACC"].cget("style"), "Changed.TEntry")
        app.reset()
        app.editor.mark_set("insert", "2.0")
        app.debugger.watches.clear()
        app.debug_run("cursor")
        self.assertEqual(app.cpu.pc, 3)
        app.reset()
        app.speed.set("1")
        app.debug_run("over")
        self.assertTrue(app.running)
        self.assertIsNotNone(app.debugger.target)
        app.pause_execution()
        self.assertIsNone(app.debugger.target)
        self.assertIsNone(app.run_after)
        app.speed.set("1000")
        app.observe_outputs.set(True)

    def test_portable_project_recovery_and_invalid_open(self):
        from mcs51_studio.project import read_project

        app = self.app
        app.debugger.watches.clear()
        app.replace_source("MOV A,#42H\nSJMP $")
        app.board.experiment.keypad_mode = "Standard"
        app.board.experiment.switch_bounce = True
        app.board.keys = {(1, 2)}
        app.board.mapping["leds"] = [f"P2.{i}" for i in range(8)]
        app.board.enabled["lcd"] = True
        app.enabled_vars["lcd"].set(True)
        app.board.analogue = 2.5
        app.analogue.set(2.5)
        app.board.uart.reset_link()
        app.board.uart.configure(9600, 2, data_bits=8, stop_bits=2)
        app.debugger.add_watch("RAM[30]", True)
        expected = app.project_data()
        path = Path(self.temporary.name) / "lesson.mcs51"
        with patch.object(filedialog, "asksaveasfilename", return_value=str(path)):
            self.assertTrue(app.save_project_file())
        self.assertEqual(read_project(path), expected)
        app.reset()
        app.board.experiment.keypad_mode = "Pulse"
        app.board.analogue = 0
        with patch.object(messagebox, "askyesnocancel", return_value=False):
            self.assertTrue(app.open_project_file(path))
        self.assertEqual(app.project_data(), expected)
        self.assertEqual(app.data_bits.get(), "8")
        self.assertEqual(app.parity.get(), "Even")
        self.assertEqual(app.stop_bits.get(), "2")
        app.editor.insert("end-1c", "\n; unsaved edit")
        self.root.update()
        app.autosave()
        recovery = app.recovery_path
        self.assertTrue(recovery.exists())
        self.assertIn("unsaved edit", read_project(recovery)["source"])
        bad = Path(self.temporary.name) / "invalid.mcs51"
        bad.write_text('{"version":999}')
        before = app.project_data()
        with patch.object(messagebox, "showerror") as error:
            self.assertFalse(app.open_project_file(bad))
            error.assert_called_once()
        self.assertEqual(app.project_data(), before)
        # Loading recovery must not erase its source before it is safely saved.
        with patch.object(messagebox, "askyesnocancel", return_value=False):
            self.assertTrue(app.open_project_file(recovery, recovery=True))
        self.assertIsNone(app.project_path)
        self.assertTrue(app.document_modified)
        self.assertEqual(app.project_data(), before)
        with patch.object(filedialog, "asksaveasfilename", return_value=str(path)):
            self.assertTrue(app.save_project_file())
        self.assertFalse(recovery.exists())
        self.assertFalse(app.project_changed())
        # Restore defaults for other tests sharing this workbench.
        from mcs51_studio.hardware.board import DEFAULT_MAPPING
        from mcs51_studio.hardware.experiment import ExperimentSettings

        app.board.mapping = {k: list(v) for k, v in DEFAULT_MAPPING.items()}
        app.board.experiment = ExperimentSettings()
        app.board.keys.clear()
        app.debugger.watches.clear()
        app.board.enabled["lcd"] = False
        app.enabled_vars["lcd"].set(False)
        app.analogue.set(0)
        app.board.uart.reset_link()
        app.board.uart.configure(4800, 0, data_bits=8)
        app.sync_uart_controls()
        app.replace_source("NOP")

    def test_cursor_data_rejection_and_project_instrument_settings(self):
        app = self.app
        app.replace_source("NOP\nbytes: DB 22H\nSJMP $")
        app.assemble()
        app.editor.mark_set("insert", "2.0")
        app.debug_run("cursor")
        self.assertEqual(app.cpu.instructions, 0)
        self.assertIn("assembled instruction", app.status.get())
        app.show_instruments()
        app.instruments.logic.probes.set("P0.0, P3.2")
        self.assertTrue(app.instruments.logic.apply_probes())
        app.instruments.logic.trigger.set("P3.2")
        app.instruments.logic.edge.set("Falling")
        app.instruments.logic.duration.set("10000")
        data = app.project_data()
        app.instruments.close()
        self.assertEqual(app.project_data(), data)
        app.apply_project(data)
        app.show_instruments()
        self.assertEqual(app.instruments.logic.channels, ["P0.0", "P3.2"])
        self.assertEqual(app.instruments.logic.trigger.get(), "P3.2")
        self.assertEqual(app.instruments.logic.duration.get(), "10000")
        app.instruments.close()
        app.editor.insert("end-1c", "\n; recover me")
        with patch(
            "mcs51_studio.ui.project_view.save_project",
            side_effect=OSError("Full Disk"),
        ):
            app.autosave()
        self.assertIn("Autosave unavailable", app.status.get())
        self.assertIsNotNone(app.autosave_after)

    def test_teaching_controls_and_lcd_rendering(self):
        app = self.app
        app.experiment_window()
        self.root.update()
        self.assertTrue(app.experiment_dialog.winfo_exists())
        app.experiment_dialog.destroy()
        app.board.lcd.byte(0x0F, 0)
        app.board.lcd.byte(0x40, 0)
        for _ in range(8):
            app.board.lcd.byte(31, 1)
        app.board.lcd.byte(0x80, 0)
        app.board.lcd.byte(0, 1)
        app.refresh()
        self.assertGreater(len(app.lcd_canvas.find_all()), 40)
        app.data_bits.set("7")
        app.parity.set("Odd")
        app.stop_bits.set("2")
        self.assertTrue(app.apply_uart())
        self.assertIn("7O2", app.uart_status.cget("text"))
        app.uart_input.insert(0, "{FF}")
        with patch.object(messagebox, "showerror") as error:
            app.uart_receive()
            error.assert_called_once()
        self.assertEqual(app.uart_input.get(), "{FF}")
        app.uart_input.delete(0, "end")
        app.reset_uart_link()
        app.data_bits.set("8")
        app.parity.set("None")
        app.stop_bits.set("1")
        self.assertTrue(app.apply_uart())


def verify_editor_workflow(app, root, temporary):
    """Check editing, unsaved-file safety, debugger controls, and pane recovery."""
    source = "MOV A,#1\nINC A\nSJMP $\n"
    app.replace_source(source)
    root.update()
    view = app.editor_view
    view.highlight()
    if not app.editor.tag_ranges("instruction"):
        raise RuntimeError("Assembly syntax highlighting is missing")
    app.editor.insert("end-1c", "; change\n")
    root.update()
    if not app.document_modified:
        raise RuntimeError("Edited document was not marked unsaved")
    if not app.assemble() or not app.document_modified:
        raise RuntimeError("Assembly incorrectly cleared unsaved document state")
    with patch.object(
        filedialog, "asksaveasfilename", return_value=str(temporary / "program.asm")
    ):
        if not app.save_source() or app.document_modified:
            raise RuntimeError("Save did not clear unsaved document state")
    if (temporary / "program.asm").read_text(encoding="utf-8") != app.saved_source:
        raise RuntimeError("Saved source does not match the editor")
    app.replace_source(source)
    app.editor.tag_add("sel", "1.0", "3.0")
    view.toggle_comment()
    root.update()
    if not app.editor.get("1.0", "2.end").startswith("; MOV"):
        raise RuntimeError("Comment command did not modify selected lines")
    view.undo()
    root.update()
    if app.editor.get("1.0", "end-1c") != source:
        raise RuntimeError("Undo did not restore a grouped edit")
    view.redo()
    root.update()
    view.undo()
    root.update()
    app.editor.tag_remove("sel", "1.0", "end")
    app.editor.tag_add("sel", "1.0", "3.0")
    view.indent()
    view.indent(reverse=True)
    root.update()
    if app.editor.get("1.0", "end-1c") != source:
        raise RuntimeError("Indent/unindent did not preserve source")
    app.editor.tag_remove("sel", "1.0", "end")
    app.editor.mark_set("insert", "1.0")
    view.search_panel.query.set("mov")
    view.search_panel.find_next()
    view.search_panel.query.set("inc")
    view.search_panel.find_next()
    view.search_panel.replacement.set("DEC")
    view.search_panel.replace_next()
    root.update()
    if "DEC A" not in app.editor.get("1.0", "end-1c"):
        raise RuntimeError("Find/replace did not update the matching instruction")
    view.undo()
    root.update()
    if app.editor.get("1.0", "end-1c") != source:
        raise RuntimeError("Replace undo did not restore source")
    app.editor.insert("end-1c", "; unsaved")
    root.update()
    with (
        patch.object(messagebox, "askyesnocancel", return_value=None),
        patch.object(filedialog, "askopenfilename") as open_dialog,
    ):
        app.open_file()
        if open_dialog.called:
            raise RuntimeError(
                "Canceling the unsaved prompt still opened a file dialog"
            )
    app.replace_source(source)
    root.update()
    if not app.assemble():
        raise RuntimeError("Editor workflow produced an invalid program")
    if "#1" not in app.current_instruction.get():
        raise RuntimeError("Instruction preview did not show the actual source operand")
    app.breakpoint_at_line(2)
    if not app.breakpoints:
        raise RuntimeError("Source breakpoint was not created")
    app.breakpoint_at_line(2)
    app.toggle_run()
    app.pause_execution()
    if app.run_after is not None:
        raise RuntimeError("Pausing left a scheduled execution callback")
    for name in ("inspector", "bottom"):
        app.toggle_pane(name)
        app.toggle_pane(name)
    app.focus_editor()
    if any(getattr(app, f"{name}_visible").get() for name in ("inspector", "bottom")):
        raise RuntimeError("Focus editor did not hide supporting panes")
    app.reset_layout()
    root.update()
    if len(app.horizontal.panes()) != 2 or len(app.vertical.panes()) != 2:
        raise RuntimeError("Reset layout failed to recover all panes")
    root.deiconify()
    for geometry in ("960x640", "1370x900"):
        root.geometry(geometry)
        root.update()
        app.reset_layout()
        root.update()
        if (
            not app.statusbar.winfo_ismapped()
            or app.statusbar.winfo_y() + app.statusbar.winfo_height()
            > root.winfo_height()
        ):
            raise RuntimeError(f"Status controls were clipped at {geometry}")
        if app.header.winfo_height() > 70 or any(
            not child.winfo_ismapped()
            or child.winfo_x() + child.winfo_width() > app.commandbar.winfo_width()
            for child in app.commandbar.pack_slaves()
        ):
            raise RuntimeError(f"Single-row commands were clipped at {geometry}")
        if app.editor.winfo_width() < 250 or app.bottom.winfo_height() < 100:
            raise RuntimeError(f"Workspace panes were not usable at {geometry}")
        app.workspace.select(app.board_tab)
        root.update()
        app.workspace.select(app.editor_tab)
    root.withdraw()


if __name__ == "__main__":
    # A blocked native dialog or Tk event loop must leave a traceback in CI.
    faulthandler.enable()
    faulthandler.dump_traceback_later(180, exit=True)
    try:
        unittest.main(verbosity=2)
    finally:
        faulthandler.cancel_dump_traceback_later()
