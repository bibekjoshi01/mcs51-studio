"""On-demand wiring and measurement tools; capture logic remains headless."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from ..hardware.wiring import (
    ALTERNATE,
    DEVICES,
    PINOUT,
    built_in_presets,
    connections,
    shared_connections,
    validate_preset,
)
from . import theme
from .waveform import Waveform


class Instruments:
    def __init__(self, app):
        self.app = app
        self.window = tk.Toplevel(app.root)
        self.window.title("Instruments — MCS51 Studio")
        self.window.geometry("1060x740")
        self.window.minsize(900, 640)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.tabs = ttk.Notebook(self.window)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)
        self.frames = {}
        for name in ("Wiring", "Logic Analyzer", "DAC Scope"):
            frame = ttk.Frame(self.tabs, padding=12)
            self.tabs.add(frame, text=name)
            self.frames[name] = frame
        self.selected_device = None
        self.wiring_signature = None
        self.build_wiring(self.frames["Wiring"])
        self.logic = Waveform(self.frames["Logic Analyzer"], app, digital=True)
        self.dac = Waveform(self.frames["DAC Scope"], app, digital=False)
        self.after = None
        self.refresh()

    def show(self, tab, device=None):
        self.tabs.select(self.frames[tab])
        if device:
            self.selected_device = device
            self.wiring_signature = None
            self.refresh_wiring()
        self.window.deiconify()
        self.window.lift()

    def close(self):
        self.app.instrument_settings = self.app.instrument_data()
        if self.after:
            self.window.after_cancel(self.after)
        self.window.destroy()
        self.app.instruments = None

    def refresh(self):
        self.refresh_wiring()
        current = self.tabs.select()
        if current == str(self.frames["Logic Analyzer"]):
            self.logic.draw()
        elif current == str(self.frames["DAC Scope"]):
            self.dac.draw()
        self.after = self.window.after(150, self.refresh)

    def build_wiring(self, parent):
        bar = ttk.Frame(parent)
        bar.pack(fill="x", pady=(0, 12))
        ttk.Label(bar, text="Experiment Preset").pack(side="left")
        self.preset = tk.StringVar(value="LED Counter")
        self.presets = ttk.Combobox(
            bar, textvariable=self.preset, state="readonly", width=25
        )
        self.presets.pack(side="left", padx=8)
        ttk.Button(bar, text="Apply", command=self.apply_preset).pack(side="left")
        ttk.Button(bar, text="Save As…", command=self.save_preset).pack(
            side="left", padx=4
        )
        ttk.Button(
            bar, text="Edit Pin Mappings…", command=self.app.mapping_dialog
        ).pack(side="right")
        self.preset_status = tk.StringVar(
            value="Applying a preset changes wiring and enabled devices; it does not load a program."
        )
        ttk.Label(
            parent,
            textvariable=self.preset_status,
            style="Muted.TLabel",
            wraplength=850,
        ).pack(anchor="w", pady=(0, 8))
        split = ttk.Panedwindow(parent, orient="horizontal")
        split.pack(fill="both", expand=True)
        diagram = ttk.Frame(split)
        details = ttk.Frame(split, padding=(12, 0))
        split.add(diagram, weight=3)
        split.add(details, weight=2)
        self.pinout = tk.Canvas(
            diagram, background=theme.INPUT, highlightthickness=0, width=550, height=490
        )
        self.pinout.pack(fill="both", expand=True)
        self.pinout.bind("<Configure>", lambda e: self.draw_pinout())
        ttk.Label(
            diagram,
            text="40-Pin DIP · Top View · Select a device or a port pin",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=6)
        ttk.Label(details, text="Enabled Devices", style="Section.TLabel").pack(
            anchor="w"
        )
        self.devices = ttk.Treeview(
            details,
            columns=("pins",),
            show="tree headings",
            height=7,
            selectmode="browse",
        )
        self.devices.heading("#0", text="Peripheral")
        self.devices.heading("pins", text="Ports")
        self.devices.column("#0", width=140)
        self.devices.column("pins", width=100)
        self.devices.pack(fill="x", pady=6)
        self.devices.bind("<<TreeviewSelect>>", self.select_device)
        self.detail = tk.Text(
            details,
            height=6,
            width=36,
            wrap="word",
            background=theme.INPUT,
            borderwidth=0,
            padx=10,
            pady=8,
        )
        self.detail.pack(fill="both", expand=True)
        ttk.Label(
            details, text="Shared Pins And Consequences", style="Section.TLabel"
        ).pack(anchor="w", pady=(12, 6))
        conflict_box = ttk.Frame(details)
        conflict_box.pack(fill="both", expand=True)
        self.conflicts = tk.Text(
            conflict_box,
            height=5,
            width=36,
            wrap="word",
            background=theme.INPUT,
            borderwidth=0,
            padx=10,
            pady=8,
        )
        self.conflicts.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(conflict_box, command=self.conflicts.yview)
        self.conflicts.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

    @staticmethod
    def text(widget, value):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")

    def preset_data(self):
        return {**built_in_presets(), **self.app.wiring_presets}

    def apply_preset(self):
        try:
            data = validate_preset(self.preset_data()[self.preset.get()])
            self.app.pause_execution()
            self.app.capture.clear()
            self.app.board.scope.clear()
            self.dac.frozen = None
            self.dac.freeze_button.configure(text="Freeze")
            self.app.board.mapping = data["mapping"]
            self.app.board.enabled = data["enabled"]
            self.app.board.key_gate = data["key_gate"]
            self.app.key_gate_var.set(data["key_gate"])
            self.app.board.keys.clear()
            for name, variable in self.app.enabled_vars.items():
                variable.set(data["enabled"][name])
            self.app.board.update()
            self.app.save_settings()
            self.app.refresh()
            self.preset_status.set(
                f"{self.preset.get()} applied. Update your program’s pin addresses to match this wiring."
            )
            self.refresh_wiring()
        except (ValueError, KeyError, OSError) as error:
            messagebox.showerror("Preset Error", str(error), parent=self.window)

    def save_preset(self):
        name = simpledialog.askstring(
            "Save Wiring Preset", "Experiment name:", parent=self.window
        )
        if not name or not name.strip():
            return
        name = name.strip()[:80]
        if name in built_in_presets():
            messagebox.showerror(
                "Reserved Preset Name",
                "Choose a different name for your experiment.",
                parent=self.window,
            )
            return
        if name in self.app.wiring_presets and not messagebox.askyesno(
            "Replace Preset", f"Replace “{name}”?", parent=self.window
        ):
            return
        data = validate_preset(
            {
                "mapping": self.app.board.mapping,
                "enabled": self.app.board.enabled,
                "key_gate": self.app.board.key_gate,
            }
        )
        self.app.wiring_presets[name] = data
        try:
            self.app.save_settings()
        except OSError as error:
            messagebox.showerror("Save Failed", str(error), parent=self.window)
            return
        self.preset.set(name)
        self.presets.configure(values=list(self.preset_data()))
        self.preset_status.set(f"Saved “{name}” for future sessions.")

    def refresh_wiring(self):
        board = self.app.board
        signature = (
            repr(board.mapping),
            repr(board.enabled),
            board.key_gate,
            self.selected_device,
        )
        if signature == self.wiring_signature:
            return
        self.wiring_signature = signature
        self.presets.configure(values=list(self.preset_data()))
        self.devices.delete(*self.devices.get_children())
        for device, (label, roles) in DEVICES.items():
            if board.enabled[device]:
                ports = sorted(
                    {p.split(".")[0] for role in roles for p in board.mapping[role]}
                )
                self.devices.insert(
                    "", "end", iid=device, text=label, values=(", ".join(ports),)
                )
        if self.selected_device and self.devices.exists(self.selected_device):
            self.devices.selection_set(self.selected_device)
        self.draw_pinout()
        self.show_device_details()
        warnings = shared_connections(board)
        self.text(
            self.conflicts,
            "\n\n".join(warnings) or "No shared device pins in this configuration.",
        )

    def select_device(self, event=None):
        selected = self.devices.selection()
        if selected and selected[0] != self.selected_device:
            self.selected_device = selected[0]
            self.wiring_signature = None
            self.draw_pinout()
            self.show_device_details()

    def show_device_details(self):
        if self.selected_device not in DEVICES:
            self.text(
                self.detail,
                "Select a peripheral to highlight every connected pin. Shared connections are amber; selected connections are mint.",
            )
            return
        name, roles = DEVICES[self.selected_device]
        board = self.app.board
        lines = [
            name
            + (" · Enabled" if board.enabled[self.selected_device] else " · Disabled"),
            "",
        ]
        for role in roles:
            label = role.replace("_", " ").title()
            lines.append(label + ": " + ", ".join(board.mapping[role]))
        self.text(self.detail, "\n".join(lines))

    def select_pin(self, pin):
        endpoints = connections(self.app.board).get(pin, [])
        self.text(
            self.detail,
            pin
            + (" · " + ALTERNATE[pin] if pin in ALTERNATE else "")
            + "\n\n"
            + (
                "\n".join(
                    f"{DEVICES[d][0]} → {role.replace('_', ' ')} [{index}]"
                    for d, role, index in endpoints
                )
                or "No enabled peripheral is connected."
            ),
        )

    def draw_pinout(self):
        c = self.pinout
        c.delete("all")
        width, height = max(400, c.winfo_width()), max(460, c.winfo_height())
        left, right = width * 0.32, width * 0.68
        top, bottom = 38, height - 24
        c.create_rectangle(
            left, top, right, bottom, fill=theme.PANEL, outline=theme.BORDER
        )
        c.create_text(width / 2, 21, text="Classic 8051 · 12 MHz", fill=theme.TEXT)
        c.create_arc(
            width / 2 - 12,
            top - 12,
            width / 2 + 12,
            top + 12,
            start=180,
            extent=180,
            outline=theme.MUTED,
        )
        links = connections(self.app.board)
        selected = {
            p
            for role in DEVICES.get(self.selected_device, ("", ()))[1]
            for p in self.app.board.mapping[role]
        }
        for number, pin in PINOUT.items():
            is_left = number <= 20
            row = number - 1 if is_left else 40 - number
            y = top + 16 + row * (bottom - top - 32) / 19
            x = left if is_left else right
            direction = -1 if is_left else 1
            endpoints = links.get(pin, [])
            shared = len({d for d, _, _ in endpoints}) > 1
            color = (
                theme.MINT if pin in selected else "#E6B870" if shared else theme.MUTED
            )
            c.create_line(
                x,
                y,
                x + direction * 22,
                y,
                fill=color,
                width=3 if pin in selected else 1,
            )
            c.create_text(
                x - direction * 8,
                y,
                text=str(number),
                anchor="w" if is_left else "e",
                fill=theme.MUTED,
                font=(self.app.mono_font, -10),
            )
            tag = f"pin-{number}"
            label = pin + (" / " + ALTERNATE[pin] if pin in ALTERNATE else "")
            c.create_text(
                x + direction * 27,
                y,
                text=label,
                anchor="e" if is_left else "w",
                fill=color,
                font=(self.app.mono_font, -11),
                tags=(tag,),
            )
            c.tag_bind(tag, "<Button-1>", lambda e, p=pin: self.select_pin(p))
        if self.selected_device:
            c.create_text(
                width / 2,
                height / 2,
                text=DEVICES[self.selected_device][0]
                + "\n\nHighlighted Pins\n"
                + str(len(selected)),
                fill=theme.MINT,
                width=right - left - 20,
                justify="center",
            )
