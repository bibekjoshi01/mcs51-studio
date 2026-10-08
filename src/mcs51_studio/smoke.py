"""Exercise the real UI in both source and frozen release builds."""

import json
import os
import tempfile
import traceback
from pathlib import Path
from tkinter import Tk, filedialog, messagebox
from unittest.mock import patch

from .metadata import APP_NAME
from .ui.application import App


def run_smoke_test():
    root = None
    report = {"ok": False}

    def fail(title, text, **kwargs):
        raise RuntimeError(f"{title}: {text}")

    try:
        with tempfile.TemporaryDirectory(prefix="mcs51-smoke-") as temporary:
            with (
                patch.dict(
                    os.environ,
                    {"MCS51_STUDIO_SETTINGS": str(Path(temporary) / "settings.json")},
                ),
                patch.object(messagebox, "showerror", fail),
            ):
                root = Tk()
                root.withdraw()
                app = App(root)
                root.update()
                if root.title() != f"{APP_NAME} — 8051 Workbench":
                    raise RuntimeError("Application title mismatch")
                if not app.assemble():
                    raise RuntimeError("Bundled example failed to assemble")
                app.step()
                app.toggle_run()
                app.running = False
                root.update()
                if app.cpu.instructions <= 1:
                    raise RuntimeError("Debugger did not run")
                app.pause_execution()
                verify_editor_workflow(app, root, Path(temporary))
                app.save_settings()
                report = {
                    "ok": True,
                    "application": APP_NAME,
                    "windowing_system": root.tk.call("tk", "windowingsystem"),
                    "instructions": app.cpu.instructions,
                }
    except Exception:
        report["error"] = traceback.format_exc()
    finally:
        if root is not None:
            root.destroy()

    destination = os.environ.get("MCS51_STUDIO_SMOKE_REPORT")
    if destination:
        Path(destination).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1


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
    for name in ("sidebar", "inspector", "bottom"):
        app.toggle_pane(name)
        app.toggle_pane(name)
    app.focus_editor()
    if any(
        getattr(app, f"{name}_visible").get()
        for name in ("sidebar", "inspector", "bottom")
    ):
        raise RuntimeError("Focus editor did not hide supporting panes")
    app.reset_layout()
    root.update()
    if len(app.horizontal.panes()) != 3 or len(app.vertical.panes()) != 2:
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
        if app.editor.winfo_width() < 250 or app.bottom.winfo_height() < 100:
            raise RuntimeError(f"Workspace panes were not usable at {geometry}")
        app.workspace.select(app.board_tab)
        root.update()
        app.workspace.select(app.editor_tab)
    root.withdraw()
