"""Literal find/replace with consistent case and whole-word options."""

import re
import tkinter as tk
from tkinter import ttk

from ..engine.source import normalize_source


class SearchPanel(ttk.Frame):
    def __init__(self, parent, editor):
        super().__init__(parent, padding=(8, 5))
        self.editor = editor
        self.text = editor.text
        self.query, self.replacement = tk.StringVar(), tk.StringVar()
        self.match_case, self.whole_word = tk.BooleanVar(), tk.BooleanVar()
        self.result = tk.StringVar()
        self.current = None
        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Label(row, text="Find").pack(side="left")
        self.entry = ttk.Entry(row, textvariable=self.query, width=20)
        self.entry.pack(side="left", padx=8, fill="x", expand=True)
        self.entry.bind("<Return>", lambda event: self.find_next())
        self.entry.bind("<Shift-Return>", lambda event: self.find_next(True))
        self.entry.bind("<Escape>", lambda event: editor.hide_find())
        for text, command in [
            ("Previous", lambda: self.find_next(True)),
            ("Next", self.find_next),
            ("Close", editor.hide_find),
        ]:
            ttk.Button(row, text=text, command=command, width=0).pack(
                side="left", padx=2
            )
        options = ttk.Frame(self)
        options.pack(fill="x", pady=3)
        ttk.Checkbutton(options, text="Match Case", variable=self.match_case).pack(
            side="left"
        )
        ttk.Checkbutton(options, text="Whole Word", variable=self.whole_word).pack(
            side="left", padx=6
        )
        ttk.Label(options, textvariable=self.result, style="Muted.TLabel").pack(
            side="right"
        )
        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Label(row, text="With").pack(side="left")
        self.replace_entry = ttk.Entry(row, textvariable=self.replacement)
        self.replace_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.replace_entry.bind("<Return>", lambda event: self.replace_next())
        self.replace_entry.bind("<Escape>", lambda event: editor.hide_find())
        ttk.Button(row, text="Replace", command=self.replace_next, width=0).pack(
            side="left", padx=2
        )
        ttk.Button(row, text="Replace All", command=self.replace_all, width=0).pack(
            side="left", padx=2
        )
        for variable in (self.query, self.match_case, self.whole_word):
            variable.trace_add("write", self.invalidate)

    def invalidate(self, *args):
        self.current = None
        self.text.tag_remove("search", "1.0", "end")
        self.result.set("")

    def pattern(self):
        term = self.query.get()
        if not term:
            return None
        escaped = re.escape(term)
        if self.whole_word.get():
            escaped = r"(?<!\w)" + escaped + r"(?!\w)"
        return re.compile(escaped, 0 if self.match_case.get() else re.IGNORECASE)

    def index(self, source, offset):
        # Tcl and Python can count supplementary Unicode characters differently.
        # Resolve the line first, then ask this Tcl interpreter for its column.
        line = source.count("\n", 0, offset) + 1
        column_start = source.rfind("\n", 0, offset) + 1
        column = self.tk.call("string", "length", source[column_start:offset])
        return f"{line}.{column}"

    def find_next(self, reverse=False):
        self.editor.flush_changes()
        pattern = self.pattern()
        if pattern is None:
            self.invalidate()
            return False
        source = self.text.get("1.0", "end-1c")
        matches = list(pattern.finditer(source))
        if not matches:
            self.invalidate()
            self.result.set("No matches")
            return False
        cursor = len(self.text.get("1.0", "insert"))
        if reverse:
            anchor = self.current[0] if self.current else cursor
            found = [match for match in matches if match.start() < anchor]
            match = found[-1] if found else matches[-1]
        else:
            match = next(
                (item for item in matches if item.start() >= cursor), matches[0]
            )
        self.current = match.span()
        start, end = self.index(source, match.start()), self.index(source, match.end())
        self.text.tag_remove("search", "1.0", "end")
        self.text.tag_add("search", start, end)
        self.text.mark_set("insert", start if reverse else end)
        self.text.see(start)
        self.editor.redraw()
        self.result.set(f"{matches.index(match) + 1} of {len(matches)}")
        return True

    def replace_next(self):
        self.editor.flush_changes()
        if self.current is None and not self.find_next():
            return
        source = self.text.get("1.0", "end-1c")
        start, end = self.current
        pattern = self.pattern()
        if pattern is None or not pattern.fullmatch(source[start:end]):
            self.invalidate()
            return
        start_index, end_index = self.index(source, start), self.index(source, end)
        value = normalize_source(self.replacement.get())
        if "\0" in value:
            self.result.set("Replacement cannot contain NUL")
            return
        with self.editor.edit_transaction():
            self.text.delete(start_index, end_index)
            self.text.insert(start_index, value)
            self.text.mark_set("insert", self.editor.index_after(start_index, value))
        self.find_next()

    def replace_all(self):
        pattern = self.pattern()
        if pattern is None:
            return
        source = self.text.get("1.0", "end-1c")
        value = normalize_source(self.replacement.get())
        if "\0" in value:
            self.result.set("Replacement cannot contain NUL")
            return
        updated, count = pattern.subn(lambda match: value, source)
        if count:
            with self.editor.edit_transaction():
                self.text.delete("1.0", "end")
                self.text.insert("1.0", updated)
        self.result.set(f"{count} replaced")
