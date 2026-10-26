"""Focused execution explanation, watches, and stack inspection."""

import tkinter as tk
from tkinter import messagebox, ttk

from ..engine.debugger import Watch
from . import theme


class DebugView:
    def build_debug(self, parent):
        actions = ttk.Frame(parent)
        actions.pack(fill="x")
        for label, action in [
            ("Step Over  F8", lambda: self.debug_run("over")),
            ("Step Out  ⇧F8", lambda: self.debug_run("out")),
            ("Run To Cursor  F9", lambda: self.debug_run("cursor")),
        ]:
            ttk.Button(actions, text=label, command=action).pack(
                side="left", padx=(0, 6)
            )
        tabs = ttk.Notebook(parent)
        tabs.pack(fill="both", expand=True, pady=(6, 0))
        explanation, watches, stack = (ttk.Frame(tabs) for _ in range(3))
        for frame, title in [
            (explanation, "Last Instruction"),
            (watches, "Watches"),
            (stack, "Stack"),
        ]:
            tabs.add(frame, text=title)
        self.debug_explanation = self.debug_text(explanation)
        self.stack_text = self.debug_text(stack)
        form = ttk.Frame(watches)
        form.pack(fill="x")
        self.watch_expression = ttk.Entry(form, width=22)
        self.watch_expression.pack(side="left", padx=(0, 8))
        self.watch_stop = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="Break On Change", variable=self.watch_stop).pack(
            side="left"
        )
        ttk.Button(form, text="Add Watch", command=self.add_watch).pack(
            side="left", padx=8
        )
        ttk.Button(form, text="Remove", command=self.remove_watch).pack(side="right")
        ttk.Label(
            watches,
            text="Registers / flags or RAM[30], XDATA[1234], SFR[90], BIT[90] · Hex addresses",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=4)
        self.watch_table = ttk.Treeview(
            watches, columns=("expression", "value", "stop"), show="headings", height=4
        )
        for name, label in [
            ("expression", "Expression"),
            ("value", "Hex / Decimal"),
            ("stop", "Break On Change"),
        ]:
            self.watch_table.heading(name, text=label)
        self.watch_table.pack(fill="both", expand=True)
        self.watch_table.bind("<Double-1>", self.toggle_watch_stop)
        ttk.Style().configure("Changed.TEntry", foreground=theme.MINT)

    def debug_text(self, parent):
        text = tk.Text(
            parent,
            height=6,
            font=(self.mono_font, -12),
            wrap="word",
            state="disabled",
            padx=8,
            pady=8,
        )
        scroll = ttk.Scrollbar(parent, command=text.yview)
        scroll.pack(side="right", fill="y")
        text.configure(yscrollcommand=scroll.set)
        text.pack(fill="both", expand=True)
        return text

    def add_watch(self):
        try:
            self.debugger.add_watch(self.watch_expression.get(), self.watch_stop.get())
            self.watch_expression.delete(0, "end")
            self.refresh_debug()
        except ValueError as error:
            messagebox.showerror("Invalid Watch", str(error), parent=self.root)

    def remove_watch(self):
        for index in sorted(
            (int(i) for i in self.watch_table.selection()), reverse=True
        ):
            del self.debugger.watches[index]
        self.refresh_debug()

    def toggle_watch_stop(self, event=None):
        for item in self.watch_table.selection():
            index = int(item)
            watch = self.debugger.watches[index]
            self.debugger.watches[index] = Watch(
                watch.expression, not watch.break_on_change
            )
        self.refresh_debug()

    def refresh_debug(self):
        if not hasattr(self, "debug_explanation"):
            return
        if hasattr(self, "saved_project"):
            self.update_document_title()
        sp = self.cpu.ram[0x81]
        frames = (
            "\n".join(
                f"{i + 1}. {f['kind'].title()} · Return {f['return']:04X} · Saved SP {f['sp']:02X}"
                for i, f in enumerate(self.debugger.frames)
            )
            or "No tracked call frames."
        )
        raw = (
            "SP is outside internal RAM."
            if sp >= 128
            else "  ".join(
                f"{a:02X}:{self.cpu.ram[a]:02X}"
                for a in range(sp, max(-1, sp - 32), -1)
            )
        )
        stack = f"SP {sp:02X} · Raw RAM, Top First (Up To 32 Bytes)\n{raw}\n\nTracked Calls And Interrupts\n{frames}\n{self.debugger.frame_warning}"
        for widget, text in [
            (self.debug_explanation, self.debugger.explanation()),
            (self.stack_text, stack),
        ]:
            if widget.get("1.0", "end-1c") != text:
                widget.configure(state="normal")
                widget.delete("1.0", "end")
                widget.insert("1.0", text)
                widget.configure(state="disabled")
        selection = self.watch_table.selection()
        self.watch_table.delete(*self.watch_table.get_children())
        for i, watch in enumerate(self.debugger.watches):
            value = watch.read(self.cpu)
            self.watch_table.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    watch.expression,
                    f"{value:02X} / {value}",
                    "Yes" if watch.break_on_change else "No",
                ),
            )
        self.watch_table.selection_set(
            [i for i in selection if self.watch_table.exists(i)]
        )
        for name, entry in getattr(self, "reg_entries", {}).items():
            entry.configure(
                style="Changed.TEntry" if name in self.debugger.changed else "TEntry"
            )

    def debug_run(self, action):
        self.pause_execution()
        if self.source_is_stale() or not self.program:
            if not self.assemble():
                return
        try:
            cursor = None
            if action == "cursor":
                line = int(self.editor.index("insert").split(".")[0])
                cursor = next(
                    (
                        address
                        for address, loc in self.program.locations.items()
                        if loc["line"] == line and loc.get("instruction", True)
                    ),
                    None,
                )
            if not self.debugger.plan(action, cursor):
                if action == "over":
                    self.step()
                else:
                    self.status.set(self.debugger.reason)
                return
            self.show_bottom("Debug")
            self.running = True
            self.run_batch()
        except ValueError as error:
            self.status.set(str(error))
