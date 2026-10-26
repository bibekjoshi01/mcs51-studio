"""Exercise the real UI in both source and frozen release builds."""

import json
import os
import tempfile
import traceback
from pathlib import Path
from tkinter import Tk, messagebox
from unittest.mock import patch

from .ui.application import App
from .metadata import APP_NAME


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
