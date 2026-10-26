"""Undoable text editing commands for the assembly editor."""

import re
import tkinter as tk
from contextlib import contextmanager

from ..engine.source import normalize_source


class EditorActions:
    def selection(self):
        ranges = self.text.tag_ranges("sel")
        return tuple(str(index) for index in ranges) if ranges else None

    def copy_selection(self):
        selection = self.selection()
        if not selection:
            return False
        value = self.text.get(*selection)
        try:
            self.text.clipboard_clear()
            self.text.clipboard_append(value)
        except tk.TclError:
            self.notice.set("Clipboard unavailable; source was kept")
            return False
        self.notice.set(f"Copied {len(value)} characters")
        return True

    def copy(self, event=None):
        self.copy_selection()
        return "break"

    def cut(self, event=None):
        selection = self.selection()
        if selection and self.copy_selection():
            with self.edit_transaction():
                self.text.delete(*selection)
        return "break"

    def paste(self, event=None):
        try:
            value = self.text.clipboard_get()
        except tk.TclError:
            self.notice.set("Clipboard has no text")
            return "break"
        self.insert_text(value)
        return "break"

    def insert_text(self, value):
        if "\0" in value:
            self.notice.set("Paste rejected: NUL characters are not valid source")
            return False
        value = normalize_source(value)
        if not value:
            return False
        with self.edit_transaction():
            selection = self.selection()
            if selection:
                start, end = selection
                self.text.delete(start, end)
                self.text.mark_set("insert", start)
            self.text.insert("insert", value)
        self.text.see("insert")
        self.text.focus_set()
        self.notice.set(f"Inserted {len(value)} characters")
        return True

    def selected_lines(self):
        selection = self.selection()
        if selection:
            start = self.text.index(f"{selection[0]} linestart")
            end = selection[1]
            if end.endswith(".0") and end != start:
                end = self.text.index(f"{end}-1c")
            return start, self.text.index(f"{end} lineend")
        return self.text.index("insert linestart"), self.text.index("insert lineend")

    @contextmanager
    def edit_transaction(self):
        previous = self.text.cget("autoseparators")
        self.text.edit_separator()
        self.text.configure(autoseparators=False)
        try:
            yield
        finally:
            self.text.configure(autoseparators=previous)
            self.text.edit_separator()
            self.changed()

    def transform_lines(self, transform):
        start, end = self.selected_lines()
        original = self.text.get(start, end)
        replacement = "\n".join(transform(line) for line in original.split("\n"))
        if original != replacement:
            with self.edit_transaction():
                self.text.delete(start, end)
                self.text.insert(start, replacement)
            self.text.tag_remove("sel", "1.0", "end")
            self.text.tag_add("sel", start, self.index_after(start, replacement))
        return "break"

    def index_after(self, start, value):
        line, column = map(int, self.text.index(start).split("."))
        parts = value.split("\n")
        if len(parts) > 1:
            line += len(parts) - 1
            column = 0
        column += int(self.tk.call("string", "length", parts[-1]))
        return self.text.index(f"{line}.{column}")

    def indent(self, event=None, reverse=False):
        if self.completion:
            return self.completion.accept()
        if reverse:
            return self.transform_lines(
                lambda line: (
                    line[1:]
                    if line.startswith("\t")
                    else line[min(len(line) - len(line.lstrip(" ")), 4) :]
                )
            )
        if self.selection():
            return self.transform_lines(lambda line: "    " + line)
        column = int(self.text.index("insert").split(".")[1])
        self.insert_text(" " * (4 - column % 4))
        return "break"

    def newline(self, event=None):
        if self.completion:
            return self.completion.accept()
        with self.edit_transaction():
            selection = self.selection()
            if selection:
                self.text.delete(*selection)
                self.text.mark_set("insert", selection[0])
            prefix = self.text.get("insert linestart", "insert")
            self.text.insert("insert", "\n" + re.match(r"[ \t]*", prefix).group())
        self.text.see("insert")
        return "break"

    def backspace(self, event=None):
        if self.selection():
            return None
        prefix = self.text.get("insert linestart", "insert")
        if prefix and not prefix.strip(" "):
            amount = len(prefix) % 4 or 4
            with self.edit_transaction():
                self.text.delete(f"insert-{amount}c", "insert")
            return "break"
        return None

    def smart_home(self, event=None):
        line = self.text.get("insert linestart", "insert lineend")
        indent = len(line) - len(line.lstrip(" \t"))
        target = self.text.index(f"insert linestart+{indent}c")
        if self.text.index("insert") == target:
            target = self.text.index("insert linestart")
        self.text.mark_set("insert", target)
        self.text.tag_remove("sel", "1.0", "end")
        self.redraw()
        return "break"

    def toggle_comment(self, event=None):
        start, end = self.selected_lines()
        lines = self.text.get(start, end).split("\n")
        uncomment = all(
            not line.strip() or line.lstrip().startswith(";") for line in lines
        )

        def change(line):
            if uncomment:
                return re.sub(r"^([ \t]*); ?", r"\1", line)
            return (
                re.sub(r"^([ \t]*)", r"\1; ", line, count=1) if line.strip() else line
            )

        return self.transform_lines(change)

    def duplicate_lines(self, event=None):
        start, end = self.selected_lines()
        has_newline = self.text.compare(f"{end}+1c", "<=", "end-1c")
        content = self.text.get(start, f"{end}+1c" if has_newline else end)
        insertion = self.text.index(f"{end}+1c") if has_newline else end
        with self.edit_transaction():
            self.text.insert(insertion, content if has_newline else "\n" + content)
        self.text.tag_remove("sel", "1.0", "end")
        new_start = insertion if has_newline else self.text.index(f"{insertion}+1c")
        self.text.mark_set("insert", new_start)
        self.text.see("insert")
        return "break"

    def delete_lines(self, event=None):
        start, end = self.selected_lines()
        if self.text.compare(f"{end}+1c", "<=", "end-1c"):
            end = self.text.index(f"{end}+1c")
        elif self.text.compare(start, ">", "1.0"):
            start = self.text.index(f"{start}-1c")
        if start != end:
            with self.edit_transaction():
                self.text.delete(start, end)
        self.text.see("insert")
        return "break"

    def move_lines(self, direction):
        start, end = self.selected_lines()
        first, last = int(start.split(".")[0]) - 1, int(end.split(".")[0]) - 1
        lines = self.text.get("1.0", "end-1c").split("\n")
        if (direction < 0 and first == 0) or (direction > 0 and last == len(lines) - 1):
            return "break"
        block = lines[first : last + 1]
        if direction < 0:
            lines[first - 1 : last + 1] = block + [lines[first - 1]]
        else:
            lines[first : last + 2] = [lines[last + 1]] + block
        with self.edit_transaction():
            self.text.delete("1.0", "end")
            self.text.insert("1.0", "\n".join(lines))
        start, end = f"{first + direction + 1}.0", f"{last + direction + 1}.end"
        self.text.tag_add("sel", start, end)
        self.text.mark_set("insert", start)
        self.text.see("insert")
        return "break"

    def undo(self, event=None):
        self.close_completion()
        try:
            self.text.edit_undo()
            self.changed()
        except tk.TclError:
            pass
        return "break"

    def redo(self, event=None):
        self.close_completion()
        try:
            self.text.edit_redo()
            self.changed()
        except tk.TclError:
            pass
        return "break"

    def select_all(self, event=None):
        self.text.tag_add("sel", "1.0", "end-1c")
        self.text.mark_set("insert", "1.0")
        self.redraw()
        return "break"
