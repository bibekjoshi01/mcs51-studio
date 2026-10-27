"""Native desktop stress acceptance tests; run separately from headless discovery."""

import faulthandler
import json
import tempfile
import time
import unittest
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from unittest.mock import patch

import gui


class StressWorkbench(unittest.TestCase):
    setUpClass = classmethod(gui.WorkbenchUI.setUpClass.__func__)
    setUp = gui.WorkbenchUI.setUp

    def test_malformed_settings_cannot_crash_startup(self):
        with tempfile.TemporaryDirectory() as folder:
            app = gui.App.__new__(gui.App)
            app.settings_path = Path(folder) / "settings.json"
            app.wiring_presets = {}
            app.layout_settings = {}
            app.board = self.app.board
            for contents in (
                "[]",
                "null",
                "42",
                "{",
                '{"enabled":[]}',
                '{"enabled":{"leds":"false"}}',
                '{"mapping":null}',
                "[" * 1500 + "]" * 1500,
            ):
                with self.subTest(contents=contents[:60]):
                    app.settings_path.write_text(contents)
                    app.load_settings()
                    self.assertTrue(app.board.enabled["leds"])

    def test_1000_control_actions_no_callbacks_after_pause(self):
        app, root = self.app, self.root
        errors = []
        root.report_callback_exception = lambda *error: errors.append(str(error))
        app.replace_source("MOV A,#0FFH\nloop:MOV P1,A\nDEC A\nSJMP loop")
        app.assemble()
        controls = [
            app.step,
            app.toggle_run,
            app.pause_execution,
            app.reset,
            lambda: app.switch_buttons[0].invoke(),
            lambda: app.toggle_pane("bottom"),
            lambda: app.toggle_pane("inspector"),
            app.focus_editor,
            lambda: app.hardware_toggles.items[0].invoke(),
            app.refresh,
        ]
        started = time.monotonic()
        for i in range(1000):
            controls[i % len(controls)]()
            root.update()
        app.pause_execution()
        count = app.cpu.instructions
        for _ in range(10):
            root.update()
        self.assertEqual(app.cpu.instructions, count)
        self.assertIsNone(app.run_after)
        self.assertEqual(errors, [])
        print(
            json.dumps(
                {
                    "control_actions": 1000,
                    "seconds": round(time.monotonic() - started, 3),
                }
            )
        )

    def test_full_memory_listing_refresh_and_heartbeat(self):
        app, root = self.app, self.root
        app.replace_source("NOP\n" * 65536)
        start = time.monotonic()
        self.assertTrue(app.assemble())
        assembled = time.monotonic() - start
        self.assertEqual(len(app.listing.get_children()), 65536)
        measurements = []
        for _ in range(20):
            start = time.monotonic()
            app.step()
            root.update()
            measurements.append(time.monotonic() - start)
        self.assertLess(
            max(measurements), 0.5, "A single step froze the large-program UI"
        )
        self.assertEqual(app.listing.item("20", "tags"), ("pc",))
        self.assertFalse(app.listing.item("19", "tags"))
        app.breakpoints = {21, 60000}
        app.refresh()
        self.assertIn("●", app.listing.item("60000", "values")[0])
        app.breakpoints.clear()
        app.refresh()
        self.assertNotIn("●", app.listing.item("60000", "values")[0])
        app.observe_outputs.set(False)
        app.speed.set("1000")
        beats = []

        def heartbeat():
            beats.append(time.monotonic())
            if len(beats) < 20:
                root.after(10, heartbeat)

        root.after(10, heartbeat)
        app.toggle_run()
        deadline = time.monotonic() + 3
        while len(beats) < 20 and time.monotonic() < deadline:
            root.update()
            time.sleep(0.001)
        app.pause_execution()
        self.assertEqual(len(beats), 20)
        latency = max(b - a for a, b in zip(beats, beats[1:]))
        self.assertLess(latency, 0.5)
        print(
            json.dumps(
                {
                    "listing_rows": 65536,
                    "assembly_seconds": round(assembled, 3),
                    "max_step_ms": round(max(measurements) * 1000, 2),
                    "max_heartbeat_gap_ms": round(latency * 1000, 2),
                }
            )
        )
        app.observe_outputs.set(True)

    def test_all_main_menu_commands_and_shortcuts(self):
        app, root = self.app, self.root
        errors, exercised = [], []
        root.report_callback_exception = lambda *error: errors.append(str(error))
        menu = root.nametowidget(root.cget("menu"))
        with (
            patch.object(messagebox, "showinfo"),
            patch.object(messagebox, "askyesnocancel", return_value=None),
            patch.object(simpledialog, "askstring", return_value=None),
            patch.object(simpledialog, "askinteger", return_value=None),
            patch.object(filedialog, "asksaveasfilename", return_value=""),
            patch.object(filedialog, "askopenfilename", return_value=""),
            patch("webbrowser.open"),
        ):
            for i in range(menu.index("end") + 1):
                if menu.type(i) != "cascade":
                    continue
                submenu = root.nametowidget(menu.entrycget(i, "menu"))
                for j in range(submenu.index("end") + 1):
                    if submenu.type(j) not in ("command", "checkbutton"):
                        continue
                    label = submenu.entrycget(j, "label")
                    app.replace_source("NOP\nSJMP $")
                    app.assemble()
                    if label == "Quit":
                        app.editor.insert("end-1c", "\n; unsaved")
                    with patch.object(app.editor, "clipboard_get", return_value="NOP"):
                        submenu.invoke(j)
                    app.pause_execution()
                    root.update()
                    exercised.append(label)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(len(exercised), 40)
        app.isa_window()
        reference = app.reference_window
        for _ in range(30):
            app.isa_window()
            self.assertIs(app.reference_window, reference)
        app.replace_source("NOP\nSJMP $")
        root.deiconify()
        root.focus_force()
        root.update()
        root.event_generate("<F6>")
        root.update()
        self.assertIsNotNone(app.program)
        root.event_generate("<F7>")
        root.update()
        self.assertEqual(app.cpu.instructions, 1)
        print(
            json.dumps(
                {"main_menu_commands": len(exercised), "shortcuts": ["F6", "F7"]}
            )
        )

    def test_retained_output_survives_history_eviction(self):
        app = self.app
        app.clear_uart_output()
        for i in range(100000):
            app.board.uart.record_received(65 + i % 26)
        app.refresh()
        self.assertLessEqual(
            int(app.uart_output.count("1.0", "end-1c", "chars")[0]), 131072
        )
        self.root.deiconify()
        app.workspace.select(app.board_tab)
        app.peripheral_tabs.select(1)
        self.root.update()
        app.clear_uart_output()
        app.board.uart.record_received(90)
        app.refresh()
        self.assertEqual(app.uart_output.get("1.0", "end-1c"), "Z")
        for _ in range(1100):
            app.log_activity("test")
        self.assertLessEqual(int(app.activity.index("end-1c").split(".")[0]), 1001)

    def test_window_lifecycle_and_buttons(self):
        app, root = self.app, self.root
        root.deiconify()
        errors = []
        root.report_callback_exception = lambda *error: errors.append(str(error))
        labels = set()

        def widgets(parent):
            for child in parent.winfo_children():
                yield child
                yield from widgets(child)

        with (
            patch.object(messagebox, "showinfo"),
            patch.object(simpledialog, "askstring", return_value=None),
            patch.object(simpledialog, "askinteger", return_value=None),
            patch.object(filedialog, "asksaveasfilename", return_value=""),
            patch.object(filedialog, "askopenfilename", return_value=""),
            patch("webbrowser.open"),
        ):
            for iteration in range(10):
                app.show_instruments()
                app.experiment_window()
                app.about()
                root.update()
                for window in [
                    app.instruments.window,
                    app.experiment_dialog,
                    app.about_window,
                ]:
                    for widget in list(widgets(window)):
                        if isinstance(widget, ttk.Button):
                            label = widget.cget("text")
                            # Close via each window's lifecycle method after exercising its controls.
                            if label in (
                                "Close",
                                "Save As",
                                "Edit Pin Mappings",
                                "Apply",
                            ):
                                continue
                            if label == "Arm":
                                app.replace_source("NOP\nSJMP $")
                            widget.invoke()
                            labels.add(label)
                            app.pause_execution()
                            root.update()
                app.instruments.close()
                app.experiment_dialog.destroy()
                app.about_window.destroy()
                root.update()
            self.assertEqual(errors, [])
        print(json.dumps({"window_cycles": 10, "exercised_buttons": sorted(labels)}))

    def test_project_failure_cancel_and_running_dialog_safety(self):
        app = self.app
        app.replace_source("SJMP $")
        app.assemble()
        app.observe_outputs.set(False)
        app.toggle_run()
        with patch.object(filedialog, "askopenfilename", return_value=""):
            app.open_project_file()
        self.assertFalse(app.running)
        self.assertIsNone(app.run_after)
        path = Path(self.temporary.name) / "stress.mcs51"
        with patch.object(filedialog, "asksaveasfilename", return_value=str(path)):
            self.assertTrue(app.save_project_file())
        app.editor.insert("end-1c", "\n; changed")
        with patch.object(messagebox, "askyesnocancel", return_value=None):
            self.assertFalse(app.open_project_file(path))
        self.assertIn("changed", app.editor.get("1.0", "end"))
        before = path.read_bytes()
        with (
            patch(
                "mcs51_studio.source_files.os.replace",
                side_effect=PermissionError("locked"),
            ),
            patch.object(messagebox, "showerror") as error,
        ):
            self.assertFalse(app.save_project_file())
            error.assert_called_once()
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue(app.project_changed())
        app.observe_outputs.set(True)


if __name__ == "__main__":
    # A blocked native dialog or Tk event loop must leave a traceback in CI.
    faulthandler.enable()
    faulthandler.dump_traceback_later(180, exit=True)
    try:
        unittest.main(verbosity=2)
    finally:
        faulthandler.cancel_dump_traceback_later()
