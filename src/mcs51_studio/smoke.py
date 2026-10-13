"""Minimal self-check for a frozen application and its bundled resources."""

import json
import os
import tempfile
import traceback
from pathlib import Path
from tkinter import Tk, messagebox

from .metadata import APP_NAME
from .ui.application import App
from .ui.icon import prepare_process_identity


def run_smoke_test():
    root = None
    report = {"ok": False}
    previous_settings = os.environ.get("MCS51_STUDIO_SETTINGS")
    previous_error = messagebox.showerror

    def fail(title, text, **kwargs):
        raise RuntimeError(f"{title}: {text}")

    try:
        with tempfile.TemporaryDirectory(prefix="mcs51-smoke-") as temporary:
            os.environ["MCS51_STUDIO_SETTINGS"] = str(Path(temporary) / "settings.json")
            messagebox.showerror = fail
            prepare_process_identity()
            root = Tk(className="MCS51Studio")
            root.withdraw()
            app = App(root)
            root.update()
            if (
                root.title() != f"{APP_NAME} — 8051 Workbench"
                or root._app_icon.width() != 512
            ):
                raise RuntimeError("Application metadata or bundled icon is missing")
            if not app.assemble():
                raise RuntimeError("Bundled example failed to assemble")
            app.step()
            app.toggle_run()
            app.pause_execution()
            if app.cpu.instructions <= 1:
                raise RuntimeError("Debugger did not run")
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
        messagebox.showerror = previous_error
        if previous_settings is None:
            os.environ.pop("MCS51_STUDIO_SETTINGS", None)
        else:
            os.environ["MCS51_STUDIO_SETTINGS"] = previous_settings
    destination = os.environ.get("MCS51_STUDIO_SMOKE_REPORT")
    if destination:
        Path(destination).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1
