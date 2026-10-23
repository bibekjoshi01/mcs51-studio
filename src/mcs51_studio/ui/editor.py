"""Assembly editor with line numbers, syntax, navigation, and editing commands."""

import re
import tkinter as tk
from tkinter import font, simpledialog, ttk

from . import theme
from .completion import CompletionPopup, completion_words
from .editor_actions import EditorActions
from .search import SearchPanel


class AssemblyEditor(EditorActions, ttk.Frame):
    def __init__(self, parent, mono_font, on_change, on_breakpoint):
        super().__init__(parent)
        self.on_change = on_change
        self.on_breakpoint = on_breakpoint
        self.pending = None
        self.highlight_top = None
        self.mono_font = mono_font
        self.breakpoint_lines = set()
        self.execution_line = None
        self.notice = tk.StringVar()
        self.position = tk.StringVar(value="Ln 1, Col 1")
        self.zoom = tk.StringVar(value="100%")
        self.font_size = 13
        self.editor_font = font.Font(family=mono_font, size=-self.font_size)
        self.completion = None
        self.error_line = None
        self.action_buttons = {}
        toolbar = ttk.Frame(self, padding=(8, 4))
        toolbar.pack(fill="x")
        for label, command in [
            ("Undo", self.undo),
            ("Redo", self.redo),
            ("Cut", self.cut),
            ("Copy", self.copy),
            ("Paste", self.paste),
        ]:
            button = ttk.Button(
                toolbar, text=label, command=command, width=0, style="Footer.TButton"
            )
            button.pack(side="left", padx=2)
            self.action_buttons[label] = button
        ttk.Button(
            toolbar,
            text="Find / Replace",
            command=self.show_find,
            width=0,
            style="Footer.TButton",
        ).pack(side="right")
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
            font=self.editor_font,
            background=theme.INPUT,
            foreground=theme.TEXT,
            insertbackground=theme.MINT,
            selectbackground=theme.SELECTION,
            selectforeground=theme.TEXT,
            highlightthickness=0,
            borderwidth=0,
            padx=12,
            pady=12,
            tabs=(self.editor_font.measure("    "),),
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

        def scrolled(first, last):
            vertical.set(first, last)
            self.redraw()
            top = self.text.index("@0,0 linestart")
            if top != self.highlight_top:
                self.highlight_top = top
                self.schedule_highlight()

        self.text.configure(yscrollcommand=scrolled, xscrollcommand=horizontal.set)
        self.body.columnconfigure(1, weight=1)
        self.body.rowconfigure(0, weight=1)
        self.search_panel = SearchPanel(self, self)
        self.diagnostic = ttk.Frame(self, padding=(12, 7))
        self.diagnostic_text = tk.StringVar()
        ttk.Label(
            self.diagnostic,
            textvariable=self.diagnostic_text,
            foreground=theme.ERROR,
            wraplength=500,
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(
            self.diagnostic,
            text="Go To Error",
            command=self.goto_error,
            width=0,
            style="Footer.TButton",
        ).pack(side="right")
        self.footer = ttk.Frame(self, padding=(12, 5))
        footer = self.footer
        footer.pack(fill="x")
        ttk.Label(footer, text="8051 ASM · UTF-8", style="Muted.TLabel").pack(
            side="left"
        )
        ttk.Label(footer, textvariable=self.position, style="Muted.TLabel").pack(
            side="right"
        )
        ttk.Button(
            footer,
            text="−",
            command=lambda: self.change_zoom(-1),
            width=0,
            style="Footer.TButton",
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            footer,
            textvariable=self.zoom,
            command=lambda: self.change_zoom(reset=True),
            width=0,
            style="Footer.TButton",
        ).pack(side="left")
        ttk.Button(
            footer,
            text="+",
            command=lambda: self.change_zoom(1),
            width=0,
            style="Footer.TButton",
        ).pack(side="left")
        ttk.Label(footer, textvariable=self.notice, style="Muted.TLabel").pack(
            side="left", padx=8
        )
        self.text.tag_configure("currentline", background="#172638")
        self.text.tag_lower("currentline")
        self.text.tag_configure("error", background="#4A2835")
        self.text.tag_configure("instruction", foreground=theme.MINT)
        self.text.tag_configure("number", foreground="#E9C887")
        self.text.tag_configure("label", foreground=theme.FOCUS)
        self.text.tag_configure("comment", foreground=theme.MUTED)
        self.text.tag_configure("string", foreground="#DBADDB")
        self.text.tag_configure("search", background=theme.SELECTION)
        self.text.tag_configure("pc", background="#23413E")
        self.text.bind("<<Modified>>", self.changed)
        self.text.bind("<KeyRelease>", self.key_released, add=True)
        self.text.bind("<<Selection>>", self.redraw, add=True)
        self.text.bind("<BackSpace>", self.backspace)
        self.text.bind("<Home>", self.smart_home)
        self.text.bind("<<Cut>>", self.cut)
        self.text.bind("<<Copy>>", self.copy)
        self.text.bind("<<Paste>>", self.paste)
        self.text.bind("<<SelectAll>>", self.select_all)
        self.text.bind("<Control-space>", self.complete)
        self.text.bind(
            "<Up>", lambda event: self.completion.move(-1) if self.completion else None
        )
        self.text.bind(
            "<Down>", lambda event: self.completion.move(1) if self.completion else None
        )
        self.text.bind("<FocusOut>", lambda event: self.close_completion())
        self.bind("<Destroy>", self.cleanup, add=True)
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
            ("Cut", self.cut),
            ("Copy", self.copy),
            ("Paste", self.paste),
            ("Select All", self.select_all),
            ("Duplicate Lines", self.duplicate_lines),
            ("Delete Lines", self.delete_lines),
            ("Toggle Comment", self.toggle_comment),
            ("Complete Symbol", self.complete),
            ("Find…", self.show_find),
            ("Go To Line…", self.goto_line),
        ]:
            self.menu.add_command(label=label, command=action)
        self.text.bind("<Button-3>", self.context_menu)
        if self.tk.call("tk", "windowingsystem") == "aqua":
            self.text.bind("<Button-2>", self.context_menu)

    def context_menu(self, event):
        self.close_completion()
        for label in ("Cut", "Copy"):
            self.menu.entryconfigure(
                label, state="normal" if self.selection() else "disabled"
            )
        self.menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def changed(self, event=None):
        if not self.text.edit_modified():
            return
        self.close_completion()
        self.clear_diagnostic()
        self.search_panel.invalidate()
        self.on_change()
        self.text.edit_modified(False)
        self.schedule_highlight()
        self.redraw()

    def schedule_highlight(self):
        if self.pending:
            self.after_cancel(self.pending)
        self.pending = self.after(120, self.highlight)

    def highlight(self):
        if self.pending:
            self.after_cancel(self.pending)
        self.pending = None
        start = self.text.index("@0,0 linestart")
        end = self.text.index(
            f"@0,{max(self.text.winfo_height(), 1)} lineend +200lines"
        )
        source = self.text.get(start, end)
        for tag in ("instruction", "number", "label", "comment", "string"):
            self.text.tag_remove(tag, start, end)
        pattern = r"(?P<comment>;[^\n]*)|(?P<string>'[^'\n]*'|\"[^\"\n]*\")|(?P<label>\b[A-Za-z_]\w*\s*:)|(?P<number>\b(?:[0-9][0-9A-Fa-f]*[Hh]|[01]+[Bb]|\d+)\b)|(?P<instruction>\b(?:MOVX?|MOVC|ADD|ADDC|SUBB|INC|DEC|MUL|DIV|DA|ANL|ORL|XRL|CLR|CPL|SETB|RL|RLC|RR|RRC|SWAP|PUSH|POP|XCHD?|NOP|AJMP|LJMP|SJMP|JMP|ACALL|LCALL|CALL|RET|RETI|JZ|JNZ|JC|JNC|JB|JNB|JBC|CJNE|DJNZ|ORG|END|EQU|SET|DB|USING|ACC|PSW|DPTR|SP|R[0-7])\b)"
        for match in re.finditer(pattern, source, re.IGNORECASE):
            self.text.tag_add(
                match.lastgroup,
                self.index_after(start, source[: match.start()]),
                self.index_after(start, source[: match.end()]),
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
            if line == self.error_line:
                self.gutter.create_text(
                    10,
                    y,
                    text="!",
                    fill=theme.ERROR,
                    font=(self.mono_font, -12, "bold"),
                )
            if line in self.breakpoint_lines:
                self.gutter.create_oval(
                    5, y - 4, 13, y + 4, fill=theme.ERROR, outline=""
                )
            if line == self.execution_line:
                self.gutter.create_polygon(16, y - 4, 22, y, 16, y + 4, fill=theme.MINT)
            index = self.text.index(f"{index}+1line")
        line, column = self.text.index("insert").split(".")
        selected = self.selection()
        count = len(self.text.get(*selected)) if selected else 0
        self.position.set(
            f"Ln {line}, Col {int(column) + 1}"
            + (f" · {count} selected" if count else "")
        )
        self.text.tag_remove("currentline", "1.0", "end")
        self.text.tag_add("currentline", f"{line}.0", f"{line}.0+1line")
        for label in ("Cut", "Copy"):
            self.action_buttons[label].configure(
                state="normal" if selected else "disabled"
            )
        for label, query in (("Undo", "canundo"), ("Redo", "canredo")):
            enabled = self.tk.getboolean(self.tk.call(self.text._w, "edit", query))
            self.action_buttons[label].configure(
                state="normal" if enabled else "disabled"
            )

    def gutter_click(self, event):
        line = int(self.text.index(f"@0,{event.y}").split(".")[0])
        self.on_breakpoint(line)

    def show_find(self, event=None):
        self.close_completion()
        selected = self.selection()
        if selected:
            value = self.text.get(*selected)
            if "\n" not in value and len(value) < 120:
                self.search_panel.query.set(value)
        self.search_panel.pack(before=self.body, fill="x")
        self.search_panel.entry.focus_set()
        self.search_panel.entry.selection_range(0, "end")
        return "break"

    def hide_find(self):
        if self.completion:
            self.close_completion()
            return "break"
        self.search_panel.pack_forget()
        self.search_panel.invalidate()
        self.text.focus_set()
        return "break"

    def goto_line(self, event=None):
        line = simpledialog.askinteger(
            "Go To Line",
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

    def flush_changes(self):
        self.changed()

    def key_released(self, event):
        if self.completion and event.keysym not in (
            "Up",
            "Down",
            "Control_L",
            "Control_R",
            "space",
        ):
            self.close_completion()
        self.redraw()

    def complete(self, event=None):
        self.close_completion()
        prefix = self.text.get("insert linestart", "insert")
        if ";" in prefix or prefix.count("'") % 2 or prefix.count('"') % 2:
            return "break"
        match = re.search(r"[A-Za-z_]\w*$", prefix)
        if not match:
            self.notice.set("Type a mnemonic, register, or label first")
            return "break"
        words = completion_words(self.text.get("1.0", "end-1c"), match.group())
        if not words:
            self.notice.set("No matching symbols")
            return "break"
        start = self.text.index(f"insert-{len(match.group())}c")
        self.completion = CompletionPopup(self, start, words)
        return "break"

    def close_completion(self):
        if self.completion:
            window = self.completion.window
            self.completion = None
            window.destroy()

    def change_zoom(self, amount=0, reset=False):
        self.font_size = 13 if reset else max(10, min(24, self.font_size + amount))
        self.editor_font.configure(size=-self.font_size)
        self.text.configure(tabs=(self.editor_font.measure("    "),))
        self.zoom.set(f"{round(self.font_size / 13 * 100)}%")
        self.redraw()
        return "break"

    def clear_diagnostic(self):
        self.error_line = None
        self.text.tag_remove("error", "1.0", "end")
        self.diagnostic.pack_forget()

    def show_diagnostic(self, message, line=None):
        self.clear_diagnostic()
        self.error_line = line
        self.diagnostic_text.set(f"Line {line}: {message}" if line else message)
        self.diagnostic.pack(before=self.footer, fill="x")
        if line:
            self.text.tag_add("error", f"{line}.0", f"{line}.0+1line")
            self.goto_error()
        self.redraw()

    def goto_error(self):
        if self.error_line:
            self.text.mark_set("insert", f"{self.error_line}.0")
            self.text.see("insert")
            self.text.focus_set()
        return "break"

    def cleanup(self, event):
        if event.widget is self:
            if self.pending:
                self.after_cancel(self.pending)
            self.close_completion()
