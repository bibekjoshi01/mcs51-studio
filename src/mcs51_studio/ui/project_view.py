"""Portable experiment documents and independent autosave recovery."""

from dataclasses import asdict
from pathlib import Path
from tkinter import filedialog, messagebox
from uuid import uuid4

from ..hardware.experiment import ExperimentSettings
from ..project import PROCESSOR, read_project, save_project, validate_project


class ProjectView:
    def init_projects(self):
        self.project_path = None
        self.hex_loaded = False
        self.saved_project = self.project_data()
        self.recovery_path = self.settings_path.parent / f"recovery-{uuid4().hex}.mcs51"
        self.recovered_from = None
        self.autosave_after = self.root.after(15000, self.autosave)
        if any(self.settings_path.parent.glob("recovery-*.mcs51")):
            self.status.set("Autosave Available · File → Recover Autosave")

    def instrument_data(self):
        if self.instruments is None:
            return {
                **self.instrument_settings,
                "probes": list(self.instrument_settings["probes"]),
            }
        logic = self.instruments.logic
        return {
            "probes": list(logic.channels),
            "trigger": logic.trigger.get(),
            "edge": logic.edge.get(),
            "duration": int(logic.duration.get()),
        }

    def project_data(self):
        board = self.board
        return {
            "format": "mcs51-studio",
            "version": 1,
            "source": self.editor.get("1.0", "end-1c"),
            "processor": dict(PROCESSOR),
            "wiring": {
                "mapping": {k: list(v) for k, v in board.mapping.items()},
                "enabled": dict(board.enabled),
                "key_gate": board.key_gate,
            },
            "experiment": asdict(board.experiment),
            "inputs": {
                "switches": list(board.switches),
                "analogue": board.analogue,
                "keys": [list(k) for k in sorted(board.keys)],
            },
            "uart": {
                k: getattr(board.uart, k)
                for k in ("baud", "parity", "data_bits", "stop_bits")
            },
            "watches": [asdict(w) for w in self.debugger.watches],
            "instruments": self.instrument_data(),
        }

    def project_changed(self):
        return (
            hasattr(self, "saved_project") and self.project_data() != self.saved_project
        )

    def configuration_changed(self):
        if not getattr(self, "saved_project", None):
            return True
        current = self.project_data()
        return any(
            current[key] != self.saved_project[key]
            for key in current
            if key != "source"
        )

    def save_project_file(self, save_as=False):
        if getattr(self, "hex_loaded", False):
            messagebox.showerror(
                "Source Required",
                "An imported HEX image has no assembly source. Export Intel HEX to preserve it; open assembly source before saving a project.",
                parent=self.root,
            )
            return False
        path = self.project_path
        if path is None or save_as:
            chosen = filedialog.asksaveasfilename(
                defaultextension=".mcs51",
                filetypes=[("MCS51 Studio Project", "*.mcs51")],
            )
            if not chosen:
                return False
            path = Path(chosen)
        try:
            data = self.project_data()
            save_project(path, data)
        except (OSError, ValueError) as error:
            messagebox.showerror("Save Project Failed", str(error), parent=self.root)
            return False
        self.project_path = Path(path)
        self.saved_project = data
        self.saved_source = data["source"]
        self.document_modified = False
        self.clear_recovery()
        self.update_document_title()
        self.status.set(f"Saved Project · {Path(path).name}")
        return True

    def open_project_file(self, path=None, recovery=False):
        self.pause_execution()
        if path is None:
            path = filedialog.askopenfilename(
                filetypes=[("MCS51 Studio Project", "*.mcs51")]
            )
        if not path:
            return False
        try:
            data = read_project(path)
        except (OSError, ValueError) as error:
            messagebox.showerror("Open Project Failed", str(error), parent=self.root)
            return False
        if not self.confirm_discard():
            return False
        self.apply_project(data, None if recovery else Path(path))
        if recovery:
            self.recovered_from = Path(path)
            self.saved_source = ""
            self.saved_project = None
            self.document_modified = True
            self.update_document_title()
        self.status.set(
            "Recovered Experiment · Save Project to keep it"
            if recovery
            else f"Opened Project · {Path(path).name}"
        )
        return True

    def apply_project(self, data, path=None):
        data = validate_project(data)
        self.replace_source(data["source"])
        if self.instruments is not None:
            self.instruments.close()
        experiment_window = getattr(self, "experiment_dialog", None)
        if experiment_window is not None and experiment_window.winfo_exists():
            experiment_window.destroy()
        self.instrument_settings = data["instruments"]
        self.board.mapping = data["wiring"]["mapping"]
        self.board.enabled = dict(data["wiring"]["enabled"])
        self.board.experiment = ExperimentSettings.validated(data["experiment"])
        self.board.uart.reset_link()
        self.board.uart.configure(**data["uart"])
        self.key_gate_var.set(data["wiring"]["key_gate"])
        for name, value in self.board.enabled.items():
            self.enabled_vars[name].set(value)
        for variable, value in zip(self.switch_vars, data["inputs"]["switches"]):
            variable.set(value)
        self.analogue.set(data["inputs"]["analogue"])
        self.debugger.watches.clear()
        for watch in data["watches"]:
            self.debugger.add_watch(watch["expression"], watch["break_on_change"])
        self.reset()
        self.board.keys = {tuple(k) for k in data["inputs"]["keys"]}
        self.sync_uart_controls()
        self.board.update()
        self.project_path = path
        self.saved_project = self.project_data()
        self.update_document_title()
        self.refresh()

    def autosave(self):
        if self.autosave_after is not None:
            self.root.after_cancel(self.autosave_after)
        self.autosave_after = None
        try:
            if self.project_changed() and not self.hex_loaded:
                self.recovery_path.parent.mkdir(parents=True, exist_ok=True)
                save_project(self.recovery_path, self.project_data())
            elif self.recovery_path.exists():
                self.recovery_path.unlink()
        except (OSError, ValueError) as error:
            self.status.set(f"Autosave unavailable · {error}")
        self.autosave_after = self.root.after(15000, self.autosave)

    def recover_project(self):
        candidates = sorted(
            self.settings_path.parent.glob("recovery-*.mcs51"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            self.status.set("No autosave recovery files available")
            return
        path = filedialog.askopenfilename(
            title="Recover Experiment",
            initialdir=self.settings_path.parent,
            initialfile=candidates[0].name,
            filetypes=[("Recovery Project", "recovery-*.mcs51")],
        )
        if path:
            self.open_project_file(path, recovery=True)

    def clear_recovery(self):
        for path in (
            getattr(self, "recovery_path", None),
            getattr(self, "recovered_from", None),
        ):
            if path and path != self.project_path:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
        self.recovered_from = None
