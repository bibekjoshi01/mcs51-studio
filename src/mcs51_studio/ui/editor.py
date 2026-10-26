"""Assembly editor with line numbers, syntax, navigation, and editing commands."""

import re
import tkinter as tk
from contextlib import contextmanager
from tkinter import simpledialog, ttk

from . import theme


class AssemblyEditor(ttk.Frame):
    def __init__(self, parent, mono_font, on_change, on_breakpoint):
        super().__init__(parent)
        self.on_change = on_change
        self.on_breakpoint = on_breakpoint
        self.pending = None
        self.mono_font = mono_font
        self.breakpoint_lines = set()
        self.execution_line = None
        self.search_term = tk.StringVar()
        self.position = tk.StringVar(value="Ln 1, Col 1")
        self.searchbar = ttk.Frame(self, padding=(8, 5))
        search_controls = ttk.Frame(self.searchbar)
        search_controls.pack(fill="x")
        ttk.Label(search_controls, text="Find").pack(side="left")
        self.search = ttk.Entry(
            search_controls, textvariable=self.search_term, width=24
        )
        self.search.pack(side="left", padx=8, fill="x", expand=True)
        self.search.bind("<Return>", lambda e: self.find_next())
        self.search.bind("<Escape>", lambda e: self.hide_find())
        ttk.Button(
            search_controls, text="Previous", command=lambda: self.find_next(True)
        ).pack(side="left", padx=2)
        ttk.Button(search_controls, text="Next", command=self.find_next).pack(
            side="left", padx=2
        )
        ttk.Button(search_controls, text="Close", command=self.hide_find).pack(
            side="left", padx=2
        )
        self.search_result = ttk.Label(search_controls, style="Muted.TLabel")
        self.search_result.pack(side="left", padx=6)
        replace_controls = ttk.Frame(self.searchbar)
        replace_controls.pack(fill="x", pady=(5, 0))
        ttk.Label(replace_controls, text="With").pack(side="left")
        self.replace_term = tk.StringVar()
        ttk.Entry(replace_controls, textvariable=self.replace_term).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(replace_controls, text="Replace", command=self.replace_next).pack(
            side="left", padx=2
        )
        ttk.Button(replace_controls, text="Replace all", command=self.replace_all).pack(
            side="left", padx=2
        )
        self.body = ttk.Frame(self)
        self.body.pack(fill="both", expand=True)
        self.gutter = tk.Canvas(
            self.body, width=52, background=theme.PANEL, highlightthickness=0
        )
        self.gutter.grid(row=0, column=0, sticky="ns")
        self.text = tk.Text(
            self.body,
            undo=True,
            maxundo=200,
            autoseparators=True,
            wrap="none",
            font=(mono_font, -13),
            background=theme.INPUT,
            foreground=theme.TEXT,
            insertbackground=theme.MINT,
            selectbackground=theme.SELECTION,
            selectforeground=theme.TEXT,
            highlightthickness=0,
            borderwidth=0,
            padx=12,
            pady=12,
            tabs=(32,),
            spacing1=2,
            spacing3=2,
            exportselection=False,
        )
        self.text.grid(row=0, column=1, sticky="nsew")
        vertical = ttk.Scrollbar(self.body, orient="vertical", command=self.text.yview)
        vertical.grid(row=0, column=2, sticky="ns")
        horizontal = ttk.Scrollbar(
            self.body, orient="horizontal", command=self.text.xview
        )
        horizontal.grid(row=1, column=1, sticky="ew")
        self.text.configure(
            yscrollcommand=lambda a, b: (vertical.set(a, b), self.redraw()),
            xscrollcommand=horizontal.set,
        )
        self.body.columnconfigure(1, weight=1)
        self.body.rowconfigure(0, weight=1)
        footer = ttk.Frame(self, padding=(12, 5))
        footer.pack(fill="x")
        ttk.Label(
            footer, text="8051 Assembly  ·  UTF-8  ·  4 spaces", style="Muted.TLabel"
        ).pack(side="left")
        ttk.Label(footer, textvariable=self.position, style="Muted.TLabel").pack(
            side="right"
        )
        self.text.tag_configure("instruction", foreground=theme.MINT)
        self.text.tag_configure("number", foreground="#E9C887")
        self.text.tag_configure("label", foreground=theme.FOCUS)
        self.text.tag_configure("comment", foreground=theme.MUTED)
        self.text.tag_configure("string", foreground="#DBADDB")
        self.text.tag_configure("search", background=theme.SELECTION)
        self.text.tag_configure("pc", background="#23413E")
        self.search_term.trace_add(
            "write", lambda *_: self.text.tag_remove("search", "1.0", "end")
        )
        self.text.bind("<<Modified>>", self.changed)
        self.text.bind("<KeyRelease>", self.redraw, add=True)
        self.text.bind("<ButtonRelease-1>", self.redraw, add=True)
        self.text.bind("<Configure>", self.redraw, add=True)
        self.text.bind("<Tab>", self.indent)
        self.text.bind("<Shift-Tab>", lambda e: self.indent(e, True))
        self.text.bind("<Return>", self.newline)
        self.gutter.bind("<Button-1>", self.gutter_click)
        self.gutter.bind("<Configure>", self.redraw)
        self.menu = tk.Menu(self.text, tearoff=False)
        for label, action in [
            ("Undo", self.undo),
            ("Redo", self.redo),
            ("Cut", lambda: self.text.event_generate("<<Cut>>")),
            ("Copy", lambda: self.text.event_generate("<<Copy>>")),
            ("Paste", lambda: self.text.event_generate("<<Paste>>")),
            ("Select all", self.select_all),
            ("Toggle comment", self.toggle_comment),
            ("Find…", self.show_find),
            ("Go to line…", self.goto_line),
        ]:
            self.menu.add_command(label=label, command=action)
        self.text.bind("<Button-3>", self.context_menu)
        if self.tk.call("tk", "windowingsystem") == "aqua":
            self.text.bind("<Button-2>", self.context_menu)

    def context_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def changed(self, event=None):
        if not self.text.edit_modified():
            return
        self.on_change()
        self.text.edit_modified(False)
        if self.pending:
            self.after_cancel(self.pending)
        self.pending = self.after(120, self.highlight)
        self.redraw()

    def highlight(self):
        self.pending = None
        source = self.text.get("1.0", "end-1c")
        for tag in ("instruction", "number", "label", "comment", "string"):
            self.text.tag_remove(tag, "1.0", "end")
        pattern = r"(?P<comment>;[^\n]*)|(?P<string>'[^'\n]*'|\"[^\"\n]*\")|(?P<label>\b[A-Za-z_]\w*\s*:)|(?P<number>\b(?:[0-9][0-9A-Fa-f]*[Hh]|[01]+[Bb]|\d+)\b)|(?P<instruction>\b(?:MOVX?|MOVC|ADD|ADDC|SUBB|INC|DEC|MUL|DIV|DA|ANL|ORL|XRL|CLR|CPL|SETB|RL|RLC|RR|RRC|SWAP|PUSH|POP|XCHD?|NOP|AJMP|LJMP|SJMP|JMP|ACALL|LCALL|CALL|RET|RETI|JZ|JNZ|JC|JNC|JB|JNB|JBC|CJNE|DJNZ|ORG|END|EQU|DB|DW|DS|BIT|ACC|PSW|DPTR|SP|R[0-7])\b)"
        for match in re.finditer(pattern, source, re.IGNORECASE):
            self.text.tag_add(
                match.lastgroup, f"1.0+{match.start()}c", f"1.0+{match.end()}c"
            )
        self.text.tag_raise("sel")

    def redraw(self, event=None):
        if not self.text.winfo_exists():
            return
        self.gutter.delete("all")
        index = self.text.index("@0,0")
        while True:
            info = self.text.dlineinfo(index)
            if info is None:
                break
            line = int(index.split(".")[0])
            self.gutter.create_text(
                40,
                info[1] + info[3] / 2,
                text=str(line),
                anchor="e",
                fill=theme.MUTED,
                font=(self.mono_font, -11),
            )
            y = info[1] + info[3] / 2
            if line in self.breakpoint_lines:
                self.gutter.create_oval(
                    5, y - 4, 13, y + 4, fill=theme.ERROR, outline=""
                )
            if line == self.execution_line:
                self.gutter.create_polygon(16, y - 4, 22, y, 16, y + 4, fill=theme.MINT)
            index = self.text.index(f"{index}+1line")
        line, column = self.text.index("insert").split(".")
        self.position.set(f"Ln {line}, Col {int(column) + 1}")

    def gutter_click(self, event):
        line = int(self.text.index(f"@0,{event.y}").split(".")[0])
        self.on_breakpoint(line)

    def selected_lines(self):
        try:
            start = self.text.index("sel.first linestart")
            end = self.text.index("sel.last")
            if end.endswith(".0") and end != start:
                end = self.text.index(f"{end}-1c")
            end = self.text.index(f"{end} lineend")
        except tk.TclError:
            start, end = (
                self.text.index("insert linestart"),
                self.text.index("insert lineend"),
            )
        return start, end

    @contextmanager
    def edit_transaction(self):
        self.text.edit_separator()
        self.text.configure(autoseparators=False)
        try:
            yield
        finally:
            self.text.configure(autoseparators=True)
            self.text.edit_separator()

    def transform_lines(self, transform):
        start, end = self.selected_lines()
        content = self.text.get(start, end)
        replacement = "\n".join(transform(line) for line in content.split("\n"))
        with self.edit_transaction():
            self.text.delete(start, end)
            self.text.insert(start, replacement)
        self.text.tag_remove("sel", "1.0", "end")
        self.text.tag_add("sel", start, f"{start}+{len(replacement)}c")
        return "break"

    def indent(self, event=None, reverse=False):
        if reverse:
            return self.transform_lines(
                lambda line: (
                    line[1:]
                    if line.startswith("\t")
                    else line[min(len(line) - len(line.lstrip(" ")), 4) :]
                )
            )
        if self.text.tag_ranges("sel"):
            return self.transform_lines(lambda line: "    " + line)
        column = int(self.text.index("insert").split(".")[1])
        self.text.insert("insert", " " * (4 - column % 4))
        return "break"

    def newline(self, event=None):
        if self.text.tag_ranges("sel"):
            self.text.delete("sel.first", "sel.last")
        line = self.text.get("insert linestart", "insert")
        indent = re.match(r"[ \t]*", line).group()
        self.text.insert("insert", "\n" + indent)
        return "break"

    def toggle_comment(self, event=None):
        start, end = self.selected_lines()
        lines = self.text.get(start, end).split("\n")
        uncomment = all(
            not line.strip() or line.lstrip().startswith(";") for line in lines
        )

        def change(line):
            if uncomment:
                return re.sub(r"^(\s*); ?", r"\1", line)
            return "; " + line if line.strip() else line

        return self.transform_lines(change)

    def undo(self, event=None):
        try:
            self.text.edit_undo()
        except tk.TclError:
            pass
        return "break"

    def redo(self, event=None):
        try:
            self.text.edit_redo()
        except tk.TclError:
            pass
        return "break"

    def select_all(self, event=None):
        self.text.tag_add("sel", "1.0", "end-1c")
        return "break"

    def show_find(self, event=None):
        self.searchbar.pack(before=self.body, fill="x")
        self.search.focus_set()
        self.search.selection_range(0, "end")
        return "break"

    def hide_find(self):
        self.searchbar.pack_forget()
        self.text.tag_remove("search", "1.0", "end")
        self.text.focus_set()
        return "break"

    def find_next(self, reverse=False):
        term = self.search_term.get()
        if not term:
            return
        start = self.text.index("insert-1c" if reverse else "insert")
        index = self.text.search(
            term,
            start,
            stopindex="1.0" if reverse else "end",
            nocase=True,
            backwards=reverse,
        )
        if not index:
            index = self.text.search(
                term,
                "end-1c" if reverse else "1.0",
                stopindex=start,
                nocase=True,
                backwards=reverse,
            )
        self.text.tag_remove("search", "1.0", "end")
        self.search_result.configure(text="" if index else "No matches")
        if index:
            end = f"{index}+{len(term)}c"
            self.text.tag_add("search", index, end)
            self.text.mark_set("insert", index if reverse else end)
            self.text.see(index)
            self.redraw()

    def goto_line(self, event=None):
        line = simpledialog.askinteger(
            "Go to line",
            "Line number",
            parent=self,
            minvalue=1,
            maxvalue=int(self.text.index("end-1c").split(".")[0]),
        )
        if line:
            self.text.mark_set("insert", f"{line}.0")
            self.text.see("insert")
            self.text.focus_set()
            self.redraw()
        return "break"

    def replace_next(self):
        ranges = self.text.tag_ranges("search")
        if not ranges:
            self.find_next()
            ranges = self.text.tag_ranges("search")
        if ranges:
            start, end = ranges
            with self.edit_transaction():
                self.text.delete(start, end)
                self.text.insert(start, self.replace_term.get())
            self.text.mark_set("insert", f"{start}+{len(self.replace_term.get())}c")
            self.find_next()

    def replace_all(self):
        term = self.search_term.get()
        if not term:
            return
        source = self.text.get("1.0", "end-1c")
        updated, count = re.subn(
            re.escape(term),
            lambda m: self.replace_term.get(),
            source,
            flags=re.IGNORECASE,
        )
        if count:
            with self.edit_transaction():
                self.text.delete("1.0", "end")
                self.text.insert("1.0", updated)
        self.search_result.configure(text=f"{count} replaced")
