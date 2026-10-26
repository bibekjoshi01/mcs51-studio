"""Desktop integration tests. Run explicitly with a graphical session."""

import os
import tempfile
import unittest
from pathlib import Path
from tkinter import Tk, filedialog, messagebox
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
        self.app.layout_settings = {}
        self.app.board_scroll.windowing_system = self.root.tk.call(
            "tk", "windowingsystem"
        )
        self.app.replace_source(LED_COUNTER)
        self.app.reset()
        self.app.reset_layout()
        self.app.peripheral_tabs.select(0)
        self.root.update()

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
        self.assertGreater(
            scroll.content.winfo_reqheight(), scroll.canvas.winfo_height()
        )
        scroll.canvas.yview_moveto(0.3)
        start = scroll.canvas.canvasy(0)
        event = SimpleNamespace(widget=app.led_canvas, num=None, delta=0)
        scroll.wheel(event)
        self.assertEqual(scroll.canvas.canvasy(0), start)
        scroll.windowing_system = "aqua"
        event.delta = -1
        scroll.wheel(event)
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
    view.search_term.set("mov")
    view.find_next()
    view.search_term.set("inc")
    view.find_next()
    view.replace_term.set("DEC")
    view.replace_next()
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
    unittest.main()
