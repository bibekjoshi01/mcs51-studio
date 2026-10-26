"""Processor inspector presentation, separate from workspace and CPU behavior."""

import tkinter as tk
from tkinter import ttk

from ..engine.cpu import ISA
from . import theme
from .widgets import CollapsibleSection, ScrollableFrame

FLAGS = (("CY", 7), ("AC", 6), ("OV", 2), ("P", 0), ("F0", 5), ("RS1", 4), ("RS0", 3))


class InspectorView:
    def build_inspector(self):
        scroll = ScrollableFrame(self.inspector)
        scroll.content.configure(padding=0)
        scroll.pack(fill="both", expand=True)
        parent = scroll.content
        ttk.Label(parent, text="Processor Inspector", style="Section.TLabel").pack(
            anchor="w", pady=(2, 12)
        )
        ttk.Label(
            parent,
            text=f"{self.cpu.profile.name} · 12 MHz · 12 Clocks",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 10))
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        card.pack(fill="x", pady=(0, 14))
        ttk.Label(
            card,
            text="Next Instruction",
            style="Card.TLabel",
            foreground=theme.MUTED,
            font=(self.ui_font, -10, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        self.current_instruction = tk.StringVar()
        self.instruction_address = tk.StringVar()
        self.instruction_bytes = tk.StringVar()
        self.instruction_timing = tk.StringVar()
        self.instruction_state = tk.StringVar()
        source = tk.Label(
            card,
            textvariable=self.current_instruction,
            background=theme.INPUT,
            foreground=theme.MINT,
            height=2,
            anchor="w",
            borderwidth=0,
            font=(self.mono_font, -14, "bold"),
            wraplength=230,
            justify="left",
        )
        source.pack(fill="x", pady=(0, 12))
        for label, variable in (
            ("Address", self.instruction_address),
            ("Bytes", self.instruction_bytes),
        ):
            row = ttk.Frame(card, style="Card.TFrame", borderwidth=0)
            row.pack(fill="x", pady=4)
            ttk.Label(
                row,
                text=label,
                style="Card.TLabel",
                foreground=theme.MUTED,
                font=(self.ui_font, -10),
            ).pack(side="left")
            ttk.Label(
                row,
                textvariable=variable,
                style="Card.TLabel",
                font=(self.mono_font, -12),
            ).pack(side="right")
        ttk.Label(
            card,
            textvariable=self.instruction_timing,
            style="Card.TLabel",
            foreground=theme.MUTED,
        ).pack(anchor="w", pady=(10, 3))
        ttk.Label(
            card,
            textvariable=self.instruction_state,
            style="Card.TLabel",
            foreground=theme.FOCUS,
        ).pack(anchor="w", pady=(3, 0))
        card.bind(
            "<Configure>",
            lambda event: source.configure(wraplength=max(100, event.width - 26)),
        )
        self.flag_section = CollapsibleSection(parent, "Status Flags")
        self.flag_section.pack(fill="x", pady=6)
        self.flag_values = {}
        self.flag_labels = {}
        for index, name in enumerate([name for name, bit in FLAGS] + ["BANK"]):
            row, column = divmod(index, 4)
            tile = ttk.Frame(
                self.flag_section.body, style="Card.TFrame", padding=(5, 8)
            )
            tile.grid(row=row, column=column, sticky="nsew", padx=3, pady=4)
            self.flag_section.body.columnconfigure(column, weight=1, uniform="flags")
            ttk.Label(
                tile,
                text=name,
                style="Card.TLabel",
                foreground=theme.MUTED,
                font=(self.ui_font, -10, "bold"),
                anchor="center",
            ).pack(fill="x")
            variable = tk.StringVar(value="0")
            value = ttk.Label(
                tile,
                textvariable=variable,
                style="Card.TLabel",
                font=(self.mono_font, -18, "bold"),
                anchor="center",
            )
            value.pack(fill="x", pady=(7, 0))
            self.flag_values[name] = variable
            self.flag_labels[name] = value
        ttk.Label(
            self.flag_section.body,
            text="Mint = set · BANK = active register bank",
            style="Muted.TLabel",
            wraplength=240,
            justify="left",
        ).grid(row=2, column=0, columnspan=4, sticky="w", padx=3, pady=(10, 4))

        self.register_section = CollapsibleSection(parent, "Registers")
        self.register_section.pack(fill="x")
        registers = self.register_section.body
        names = ["PC", "ACC", "B", "PSW", "SP", "DPL", "DPH"] + [
            f"R{i}" for i in range(8)
        ]
        for i, name in enumerate(names):
            row, column = divmod(i, 3)
            cell = ttk.Frame(registers)
            cell.grid(row=row, column=column, sticky="ew", padx=3, pady=5)
            registers.columnconfigure(column, weight=1)
            ttk.Label(cell, text=name, style="Section.TLabel").pack(anchor="w")
            var = tk.StringVar()
            self.reg_vars[name] = var
            entry = ttk.Entry(
                cell, textvariable=var, width=5, font=(self.mono_font, -12)
            )
            self.reg_entries[name] = entry
            entry.pack(fill="x", pady=(5, 0))
            entry.bind("<Return>", lambda event, n=name: self.edit_register(n))
        ttk.Label(
            parent, text="Hexadecimal · Enter to apply", style="Muted.TLabel"
        ).pack(anchor="w", pady=10)

    def update_inspector(self, opcode, encoded, description):
        psw = self.cpu.ram[0xD0]
        for name, bit in FLAGS:
            value = (psw >> bit) & 1
            self.flag_values[name].set(str(value))
            self.flag_labels[name].configure(
                foreground=theme.MINT if value else theme.MUTED
            )
        self.flag_values["BANK"].set(str((psw >> 3) & 3))
        self.flag_labels["BANK"].configure(foreground=theme.FOCUS)
        self.current_instruction.set(description)
        self.instruction_address.set(f"{self.cpu.pc:04X}")
        self.instruction_bytes.set(encoded.hex(" ").upper())
        cycles = ISA[opcode]["cycles"]
        self.instruction_timing.set(
            f"{len(encoded)} byte{'s' if len(encoded) != 1 else ''} · {cycles} machine cycle{'s' if cycles != 1 else ''}"
        )
        self.instruction_state.set(
            "Assemble to refresh source"
            if self.dirty
            else "Ready to execute"
            if self.program
            else "No program assembled"
        )
