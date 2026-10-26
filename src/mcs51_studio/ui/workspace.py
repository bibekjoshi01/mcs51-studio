"""Resizable workbench layout, navigation, menus, and document commands."""

import tkinter as tk
from tkinter import messagebox, ttk

from ..metadata import APP_NAME
from ..resources import LED_COUNTER
from . import theme
from .editor import AssemblyEditor


class CollapsibleSection(ttk.Frame):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.title = title
        self.open = True
        self.button = ttk.Button(self, text=f"▾  {title}", command=self.toggle)
        self.button.pack(fill="x")
        self.body = ttk.Frame(self, padding=(8, 8))
        self.body.pack(fill="x")

    def toggle(self):
        self.open = not self.open
        self.button.configure(text=f"{'▾' if self.open else '▸'}  {self.title}")
        if self.open:
            self.body.pack(fill="x")
        else:
            self.body.pack_forget()


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, background=theme.PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.content = ttk.Frame(self.canvas, padding=12)
        window = self.canvas.create_window(0, 0, anchor="nw", window=self.content)
        self.canvas.bind(
            "<Configure>", lambda e: self.canvas.itemconfigure(window, width=e.width)
        )
        self.content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.winfo_toplevel().bind("<MouseWheel>", self.wheel, add=True)
        self.winfo_toplevel().bind("<Button-4>", self.wheel, add=True)
        self.winfo_toplevel().bind("<Button-5>", self.wheel, add=True)

    def wheel(self, event):
        if str(event.widget).startswith(str(self)) and self.canvas.yview() != (
            0.0,
            1.0,
        ):
            direction = (
                -1
                if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0
                else 1
            )
            self.canvas.yview_scroll(direction * 2, "units")


class WorkspaceView:
    def build_workspace(self):
        self.sidebar_visible = tk.BooleanVar(value=True)
        self.inspector_visible = tk.BooleanVar(value=True)
        self.bottom_visible = tk.BooleanVar(value=True)
        self.machine_state = tk.StringVar(value="EDITING")
        self.current_instruction = tk.StringVar(value="0000  NOP")
        self.build_menu()
        header = ttk.Frame(self.root, padding=(12, 8))
        self.header = header
        header.pack(fill="x", pady=(0, 6))
        brand = ttk.Frame(header)
        brand.pack(side="left", padx=(0, 14))
        self.header_icon = self.root._app_icon.subsample(16, 16)
        ttk.Label(brand, image=self.header_icon).pack(side="left", padx=(0, 8))
        identity = ttk.Frame(brand)
        identity.pack(side="left")
        ttk.Label(identity, text=APP_NAME, font=(self.ui_font, -17, "bold")).pack(
            anchor="w"
        )
        ttk.Label(
            identity,
            text="8051 learning workbench",
            foreground=theme.MUTED,
            font=(self.ui_font, -9),
        ).pack(anchor="w")
        toolbar = ttk.Frame(header)
        self.commandbar = toolbar
        toolbar.pack(side="left", fill="x", expand=True)
        for label, action, primary in [
            ("Open", self.open_file, False),
            ("Save", self.save_source, False),
            ("Assemble  F6", self.assemble, True),
            ("Step  F7", self.step, False),
        ]:
            ttk.Button(
                toolbar,
                text=label,
                command=action,
                width=0,
                style="Primary.TButton" if primary else "TButton",
            ).pack(side="left", padx=2)
        self.run_button = ttk.Button(
            toolbar, text="Run  F5", command=self.toggle_run, width=0
        )
        self.run_button.pack(side="left", padx=2)
        ttk.Button(toolbar, text="Reset", command=self.reset, width=0).pack(
            side="left", padx=2
        )
        ttk.Label(toolbar, text="Batch", style="Muted.TLabel").pack(
            side="left", padx=(10, 6)
        )
        ttk.Combobox(
            toolbar,
            textvariable=self.speed,
            values=["1", "10", "100", "1000", "10000"],
            width=7,
            state="readonly",
        ).pack(side="left")
        ttk.Button(
            toolbar, text="Focus editor", command=self.focus_editor, width=0
        ).pack(side="right", padx=2)
        self.vertical = ttk.Panedwindow(self.root, orient="vertical")
        self.vertical.pack(fill="both", expand=True, padx=10)
        self.horizontal = ttk.Panedwindow(self.vertical, orient="horizontal")
        self.vertical.add(self.horizontal, weight=4)
        self.sidebar = ttk.Frame(self.horizontal, padding=12, width=165)
        self.center = ttk.Frame(self.horizontal)
        self.inspector = ttk.Frame(self.horizontal, padding=10, width=235)
        for frame, weight in [(self.sidebar, 0), (self.center, 5), (self.inspector, 0)]:
            self.horizontal.add(frame, weight=weight)
        self.build_sidebar()
        self.workspace = ttk.Notebook(self.center)
        self.workspace.pack(fill="both", expand=True)
        self.editor_tab = ttk.Frame(self.workspace)
        self.board_tab = ttk.Frame(self.workspace)
        self.workspace.add(self.editor_tab, text="untitled.asm")
        self.workspace.add(self.board_tab, text="Virtual board")
        self.editor_view = AssemblyEditor(
            self.editor_tab, self.mono_font, self.edited, self.breakpoint_at_line
        )
        self.editor_view.pack(fill="both", expand=True)
        self.editor = self.editor_view.text
        board_scroll = ScrollableFrame(self.board_tab)
        board_scroll.pack(fill="both", expand=True)
        self.build_board(board_scroll.content)
        self.build_inspector()
        self.bottom = ttk.Frame(self.vertical)
        self.vertical.add(self.bottom, weight=1)
        bottom_header = ttk.Frame(self.bottom, padding=(10, 2))
        bottom_header.pack(fill="x")
        ttk.Label(bottom_header, text="DEBUG TOOLS", style="Section.TLabel").pack(
            side="left"
        )
        ttk.Button(
            bottom_header, text="Hide panel", command=lambda: self.toggle_pane("bottom")
        ).pack(side="right")
        self.tools = ttk.Notebook(self.bottom)
        self.tools.pack(fill="both", expand=True)
        self.tool_tabs = {}
        for name in ("Listing", "Memory", "Activity"):
            frame = ttk.Frame(self.tools, padding=8)
            self.tools.add(frame, text=name)
            self.tool_tabs[name] = frame
        self.build_listing(self.tool_tabs["Listing"])
        self.build_memory(self.tool_tabs["Memory"])
        self.activity = tk.Text(
            self.tool_tabs["Activity"],
            height=5,
            font=(self.mono_font, -12),
            borderwidth=0,
            highlightthickness=0,
            wrap="word",
            state="disabled",
            padx=8,
            pady=8,
        )
        self.activity.pack(fill="both", expand=True)
        statusbar = ttk.Frame(self.root, padding=(12, 5))
        self.statusbar = statusbar
        statusbar.pack(side="bottom", fill="x", before=self.vertical)
        for name in ("sidebar", "inspector", "bottom"):
            ttk.Checkbutton(
                statusbar,
                text=name.title(),
                variable=getattr(self, f"{name}_visible"),
                command=lambda n=name: self.apply_pane(n),
            ).pack(side="right", padx=4)
        ttk.Button(
            statusbar,
            text="Instruction Reference",
            command=self.isa_window,
            style="Footer.TButton",
            width=0,
        ).pack(side="right", padx=(4, 10))
        self.state_label = ttk.Label(
            statusbar, textvariable=self.machine_state, foreground=theme.MINT
        )
        self.state_label.pack(side="left", padx=(0, 12))
        ttk.Label(statusbar, textvariable=self.status, style="Muted.TLabel").pack(
            side="left", fill="x", expand=True
        )
        self.log_activity(
            "Ready. Assemble the example, then step through the instructions. F1 opens keyboard shortcuts."
        )

    def build_sidebar(self):
        scroll = ScrollableFrame(self.sidebar)
        scroll.content.configure(padding=0)
        scroll.pack(fill="both", expand=True)
        parent = scroll.content
        ttk.Label(parent, text="WORKSPACE", style="Section.TLabel").pack(
            anchor="w", pady=(2, 10)
        )
        for label, action in [
            ("Assembly editor", lambda: self.workspace.select(self.editor_tab)),
            ("Virtual board", lambda: self.workspace.select(self.board_tab)),
            ("Program listing", lambda: self.show_bottom("Listing")),
            ("Memory explorer", lambda: self.show_bottom("Memory")),
        ]:
            ttk.Button(parent, text=label, command=action).pack(fill="x", pady=3)
        ttk.Separator(parent).pack(fill="x", pady=18)
        ttk.Label(parent, text="STARTER PROGRAM", style="Section.TLabel").pack(
            anchor="w", pady=(0, 8)
        )
        ttk.Button(parent, text="LED counter", command=self.load_example).pack(fill="x")
        ttk.Label(
            parent,
            text="Observe the ports and\nstep through a loop.",
            style="Muted.TLabel",
            justify="left",
        ).pack(anchor="w", pady=8)
        ttk.Separator(parent).pack(fill="x", pady=12)
        ttk.Button(parent, text="Pin mappings…", command=self.mapping_dialog).pack(
            fill="x", pady=3
        )
        ttk.Button(parent, text="Oscilloscope", command=self.scope_window).pack(
            fill="x", pady=3
        )

    def build_inspector(self):
        scroll = ScrollableFrame(self.inspector)
        scroll.content.configure(padding=0)
        scroll.pack(fill="both", expand=True)
        parent = scroll.content
        ttk.Label(parent, text="PROCESSOR INSPECTOR", style="Section.TLabel").pack(
            anchor="w", pady=(2, 10)
        )
        ttk.Label(parent, text="NEXT INSTRUCTION", style="Section.TLabel").pack(
            anchor="w", pady=(8, 4)
        )
        ttk.Label(
            parent,
            textvariable=self.current_instruction,
            style="Mono.TLabel",
            wraplength=220,
        ).pack(anchor="w", pady=(0, 16))
        self.register_section = CollapsibleSection(parent, "REGISTERS")
        self.register_section.pack(fill="x")
        registers = self.register_section.body
        names = ["PC", "ACC", "B", "PSW", "SP", "DPL", "DPH"] + [
            f"R{i}" for i in range(8)
        ]
        for i, name in enumerate(names):
            row, column = divmod(i, 3)
            cell = ttk.Frame(registers)
            cell.grid(row=row, column=column, sticky="ew", padx=3, pady=4)
            registers.columnconfigure(column, weight=1)
            ttk.Label(cell, text=name, style="Section.TLabel").pack(anchor="w")
            var = tk.StringVar()
            self.reg_vars[name] = var
            entry = ttk.Entry(
                cell, textvariable=var, width=5, font=(self.mono_font, -12)
            )
            entry.pack(fill="x", pady=(3, 0))
            entry.bind("<Return>", lambda e, n=name: self.edit_register(n))
        ttk.Label(
            parent, text="Hexadecimal · Enter to apply", style="Muted.TLabel"
        ).pack(anchor="w", pady=10)
        self.flag_section = CollapsibleSection(parent, "STATUS FLAGS")
        self.flag_section.pack(fill="x", pady=6)
        self.flags = ttk.Label(
            self.flag_section.body,
            text="",
            style="Mono.TLabel",
            wraplength=205,
            justify="left",
        )
        self.flags.pack(anchor="w")

    def build_listing(self, parent):
        ttk.Label(
            parent,
            text="Double-click a row or click an editor line number to toggle a breakpoint.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 5))
        self.listing = ttk.Treeview(
            parent, columns=("pc", "bytes", "source"), show="headings", height=4
        )
        for col, width in [("pc", 90), ("bytes", 130), ("source", 450)]:
            self.listing.heading(
                col, text={"pc": "ADDRESS", "bytes": "BYTES", "source": "SOURCE"}[col]
            )
            self.listing.column(col, width=width, stretch=col == "source")
        scroll = ttk.Scrollbar(parent, command=self.listing.yview)
        scroll.pack(side="right", fill="y")
        self.listing.configure(yscrollcommand=scroll.set)
        self.listing.pack(fill="both", expand=True)
        self.listing.bind("<Double-1>", self.breakpoint)
        self.listing.tag_configure("pc", background="#23413E", foreground=theme.MINT)
        self.listing.tag_configure("break", foreground=theme.ERROR)

    def build_memory(self, parent):
        header = ttk.Frame(parent)
        header.pack(fill="x", pady=(0, 5))
        self.memory_kind = tk.StringVar(value="RAM")
        kind = ttk.Combobox(
            header,
            textvariable=self.memory_kind,
            values=["RAM", "SFR", "Code"],
            width=7,
            state="readonly",
        )
        kind.pack(side="left")
        kind.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.memory_start = tk.StringVar(value="0000")
        ttk.Label(header, text="Code address (hex)", style="Muted.TLabel").pack(
            side="left", padx=8
        )
        entry = ttk.Entry(header, textvariable=self.memory_start, width=7)
        entry.pack(side="left")
        entry.bind("<Return>", lambda e: self.refresh())
        ttk.Button(header, text="Go", command=self.refresh).pack(side="left", padx=5)
        ttk.Label(
            header, text="Double-click to edit a RAM byte", style="Muted.TLabel"
        ).pack(side="right")
        self.memory = ttk.Treeview(
            parent,
            columns=["addr"] + [str(i) for i in range(16)],
            show="headings",
            height=4,
        )
        for name, label, width in [("addr", "ADDRESS", 85)] + [
            (str(i), f"{i:X}", 36) for i in range(16)
        ]:
            self.memory.heading(name, text=label)
            self.memory.column(name, width=width, minwidth=30, stretch=name != "addr")
        scrollbar = ttk.Scrollbar(parent, command=self.memory.yview)
        scrollbar.pack(side="right", fill="y")
        self.memory.configure(yscrollcommand=scrollbar.set)
        self.memory.pack(fill="both", expand=True)
        self.memory.bind("<Double-1>", self.edit_memory)

    def build_menu(self):
        menu = tk.Menu(self.root)
        self.root.configure(menu=menu)
        file = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="File", menu=file)
        modifier = (
            "⌘" if self.root.tk.call("tk", "windowingsystem") == "aqua" else "Ctrl+"
        )
        for label, action, accelerator in [
            ("New program", self.new_file, modifier + "N"),
            ("Open assembly / HEX…", self.open_file, modifier + "O"),
            ("Save", self.save_source, modifier + "S"),
            ("Save as…", lambda: self.save_source(True), modifier + "Shift+S"),
            ("Export Intel HEX…", self.export, ""),
        ]:
            file.add_command(label=label, command=action, accelerator=accelerator)
        file.add_separator()
        file.add_command(label="Quit", command=self.close)
        edit = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Edit", menu=edit)
        # Callbacks resolve editor_view after workspace construction.
        for label, method, shortcut in [
            ("Undo", "undo", "Z"),
            ("Redo", "redo", "Shift+Z"),
            ("Find…", "show_find", "F"),
            ("Go to line…", "goto_line", "G"),
            ("Toggle comment", "toggle_comment", "/"),
        ]:
            edit.add_command(
                label=label,
                command=lambda m=method: getattr(self.editor_view, m)(),
                accelerator=modifier + shortcut,
            )
        edit.add_separator()
        for label, event, shortcut in [
            ("Cut", "<<Cut>>", "X"),
            ("Copy", "<<Copy>>", "C"),
            ("Paste", "<<Paste>>", "V"),
            ("Select all", "<<SelectAll>>", "A"),
        ]:
            edit.add_command(
                label=label,
                command=lambda e=event: self.edit_action(e),
                accelerator=modifier + shortcut,
            )
        view = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="View", menu=view)
        for name in ("sidebar", "inspector", "bottom"):
            view.add_checkbutton(
                label=name.title(),
                variable=getattr(self, f"{name}_visible"),
                command=lambda n=name: self.apply_pane(n),
            )
        view.add_separator()
        view.add_command(label="Focus editor", command=self.focus_editor)
        view.add_command(label="Reset layout", command=self.reset_layout)
        run = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Run", menu=run)
        for label, action, key in [
            ("Assemble", self.assemble, "F6"),
            ("Run / Pause", self.toggle_run, "F5"),
            ("Step instruction", self.step, "F7"),
            ("Reset machine", self.reset, "Shift+F5"),
        ]:
            run.add_command(label=label, command=action, accelerator=key)
        tools = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Tools", menu=tools)
        for label, action in [
            ("Pin mappings…", self.mapping_dialog),
            ("Oscilloscope", self.scope_window),
            ("8051 instruction reference", self.isa_window),
        ]:
            tools.add_command(label=label, command=action)
        help_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(
            label="Keyboard shortcuts", command=self.shortcuts_help, accelerator="F1"
        )
        help_menu.add_command(label="About MCS51 Studio", command=self.about)

    def bind_shortcuts(self):
        modifier = (
            "Command"
            if self.root.tk.call("tk", "windowingsystem") == "aqua"
            else "Control"
        )
        commands = {
            "n": self.new_file,
            "o": self.open_file,
            "s": self.save_source,
            "Shift-S": lambda: self.save_source(True),
            "f": self.editor_view.show_find,
            "g": self.editor_view.goto_line,
            ("Alt-f" if modifier == "Command" else "h"): self.editor_view.show_find,
            "b": lambda: self.toggle_pane("sidebar"),
            "j": lambda: self.toggle_pane("bottom"),
        }

        def invoke(action):
            def callback(event):
                action()
                return "break"

            return callback

        for key, action in commands.items():
            self.root.bind(f"<{modifier}-{key}>", invoke(action))
        for key, action in {
            "F1": self.shortcuts_help,
            "F5": self.toggle_run,
            "F6": self.assemble,
            "F7": self.step,
            "Shift-F5": self.reset,
        }.items():
            self.root.bind(f"<{key}>", invoke(action))
        for key, action in {
            "z": self.editor_view.undo,
            "Shift-Z": self.editor_view.redo,
            "y": self.editor_view.redo,
            "a": self.editor_view.select_all,
            "slash": self.editor_view.toggle_comment,
        }.items():
            self.editor.bind(f"<{modifier}-{key}>", invoke(action))
        self.editor.bind("<Escape>", lambda e: self.editor_view.hide_find())

    def toggle_pane(self, name):
        variable = getattr(self, f"{name}_visible")
        variable.set(not variable.get())
        self.apply_pane(name)

    def apply_pane(self, name):
        pane = getattr(self, name)
        manager = self.vertical if name == "bottom" else self.horizontal
        visible = getattr(self, f"{name}_visible").get()
        if visible and str(pane) not in manager.panes():
            if name == "sidebar":
                manager.insert(0, pane, weight=0)
            else:
                manager.add(pane, weight=1 if name == "bottom" else 0)
        elif not visible and str(pane) in manager.panes():
            manager.forget(pane)

    def show_bottom(self, tab):
        self.bottom_visible.set(True)
        self.apply_pane("bottom")
        self.tools.select(self.tool_tabs[tab])

    def focus_editor(self):
        focus = (
            self.sidebar_visible.get()
            or self.inspector_visible.get()
            or self.bottom_visible.get()
        )
        for name in ("sidebar", "inspector", "bottom"):
            getattr(self, f"{name}_visible").set(not focus)
            self.apply_pane(name)
        self.workspace.select(self.editor_tab)
        self.editor.focus_set()

    def reset_layout(self):
        for name in ("sidebar", "inspector", "bottom"):
            getattr(self, f"{name}_visible").set(True)
            self.apply_pane(name)
        self.root.update_idletasks()
        self.horizontal.sashpos(0, 175)
        self.horizontal.sashpos(1, max(600, self.horizontal.winfo_width() - 255))
        self.vertical.sashpos(0, max(300, self.vertical.winfo_height() - 260))

    def capture_layout(self):
        return {
            "visible": {
                name: getattr(self, f"{name}_visible").get()
                for name in ("sidebar", "inspector", "bottom")
            },
            "horizontal": [
                self.horizontal.sashpos(i)
                for i in range(len(self.horizontal.panes()) - 1)
            ],
            "vertical": self.vertical.sashpos(0) if self.bottom_visible.get() else None,
        }

    def restore_layout(self):
        self.reset_layout()
        visible = self.layout_settings.get("visible", {})
        if isinstance(visible, dict):
            for name in ("sidebar", "inspector", "bottom"):
                if isinstance(visible.get(name), bool):
                    getattr(self, f"{name}_visible").set(visible[name])
                    self.apply_pane(name)
        positions = self.layout_settings.get("horizontal", [])
        if isinstance(positions, list):
            for i, value in enumerate(positions[: len(self.horizontal.panes()) - 1]):
                if isinstance(value, int):
                    self.horizontal.sashpos(
                        i, max(100, min(value, self.horizontal.winfo_width() - 100))
                    )
        vertical = self.layout_settings.get("vertical")
        if self.bottom_visible.get() and isinstance(vertical, int):
            self.vertical.sashpos(
                0, max(180, min(vertical, self.vertical.winfo_height() - 100))
            )

    def log_activity(self, message):
        self.activity.configure(state="normal")
        self.activity.insert("end", message + "\n")
        self.activity.see("end")
        self.activity.configure(state="disabled")

    def update_document_title(self):
        name = self.path.name if self.path else "untitled.asm"
        self.workspace.tab(
            self.editor_tab, text=("● " if self.document_modified else "") + name
        )

    def confirm_discard(self):
        # Compare the buffer too: Tk's modified event can still be queued.
        if self.editor.get("1.0", "end-1c") == self.saved_source:
            return True
        answer = messagebox.askyesnocancel(
            "Unsaved program", "Save your program before continuing?", parent=self.root
        )
        if answer is None:
            return False
        return self.save_source() if answer else True

    def replace_source(self, source, name=None):
        self.pause_execution()
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", source)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.saved_source = source
        self.path = name
        self.document_modified = False
        self.dirty = True
        self.program = None
        self.breakpoints.clear()
        self.populate_listing()
        self.editor_view.highlight()
        self.update_document_title()
        self.workspace.select(self.editor_tab)
        self.editor.focus_set()
        self.refresh()

    def new_file(self):
        if self.confirm_discard():
            self.replace_source("")
            self.status.set(
                "New program · write assembly or open the LED counter example"
            )

    def load_example(self):
        if self.confirm_discard():
            self.replace_source(LED_COUNTER)
            self.status.set("LED counter example loaded")

    def breakpoint_at_line(self, line):
        if self.dirty or not self.program:
            self.status.set("Assemble first to set a source breakpoint")
            return
        addresses = [
            address
            for address, location in self.program.locations.items()
            if location["line"] == line
        ]
        if addresses:
            address = addresses[0]
            if address in self.breakpoints:
                self.breakpoints.remove(address)
            else:
                self.breakpoints.add(address)
            self.refresh()
            self.status.set(
                f"Breakpoint {'set' if address in self.breakpoints else 'removed'} · {address:04X}"
            )

    def shortcuts_help(self):
        modifier = (
            "Command"
            if self.root.tk.call("tk", "windowingsystem") == "aqua"
            else "Ctrl"
        )
        replace_key = "Command+Option+F" if modifier == "Command" else "Ctrl+H"
        messagebox.showinfo(
            "Keyboard shortcuts",
            f"{modifier}+N / O / S     New / Open / Save\n{modifier}+Shift+S       Save as\n{modifier}+Z / Shift+Z   Undo / Redo\n{modifier}+F / G         Find / Go to line\n{modifier}+/             Toggle line comments\n{replace_key}             Find and replace\nTab / Shift+Tab         Indent / Unindent\n{modifier}+B / J         Toggle sidebar / bottom panel\nF6                      Assemble\nF5                      Run / Pause\nF7                      Step instruction\nShift+F5                Reset machine\n\nClick a line number to toggle a breakpoint after assembly.\nDrag dividers to resize panes. View → Reset layout restores them.",
            parent=self.root,
        )

    def edit_action(self, event):
        target = self.root.focus_get()
        if isinstance(target, (tk.Text, ttk.Entry)):
            target.event_generate(event)
        else:
            self.editor.focus_set()
            self.editor.event_generate(event)
