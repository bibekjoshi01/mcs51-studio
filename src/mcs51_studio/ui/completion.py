"""Explicit 8051 mnemonic, register, directive, and label completion."""

import re
import tkinter as tk

from ..engine.cpu import BITS, ISA, SFR
from . import theme

WORDS = (
    {row["display"].split()[0] for row in ISA}
    | set(SFR)
    | set(BITS)
    | {"ORG", "END", "EQU", "SET", "DB", "USING", "A", "C", "AB", "DPTR"}
    | {f"R{i}" for i in range(8)}
)


class CompletionPopup:
    def __init__(self, editor, start, words):
        self.editor = editor
        self.start = start
        self.window = tk.Toplevel(editor)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.list = tk.Listbox(
            self.window,
            height=min(8, len(words)),
            width=max(16, min(32, max(map(len, words)) + 2)),
            font=(editor.mono_font, -12),
            background=theme.PANEL,
            foreground=theme.TEXT,
            selectbackground=theme.SELECTION,
            selectforeground=theme.MINT,
            exportselection=False,
            takefocus=False,
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
        )
        self.list.pack(fill="both", expand=True)
        for word in words:
            self.list.insert("end", word)
        self.list.selection_set(0)
        self.list.bind("<Button-1>", self.click)
        editor.text.see("insert")
        editor.text.update_idletasks()
        bbox = editor.text.bbox("insert") or (0, 0, 0, 20)
        self.window.update_idletasks()
        x = editor.text.winfo_rootx() + bbox[0]
        y = editor.text.winfo_rooty() + bbox[1] + bbox[3]
        x = max(
            0, min(x, self.window.winfo_screenwidth() - self.window.winfo_reqwidth())
        )
        if y + self.window.winfo_reqheight() > self.window.winfo_screenheight():
            y = editor.text.winfo_rooty() + bbox[1] - self.window.winfo_reqheight()
        self.window.geometry(f"+{x}+{max(0, y)}")
        self.window.deiconify()

    def move(self, direction):
        index = int(self.list.curselection()[0])
        index = (index + direction) % self.list.size()
        self.list.selection_clear(0, "end")
        self.list.selection_set(index)
        self.list.see(index)
        return "break"

    def click(self, event):
        index = self.list.nearest(event.y)
        self.list.selection_clear(0, "end")
        self.list.selection_set(index)
        return self.accept()

    def accept(self):
        word = self.list.get(self.list.curselection()[0])
        editor, start = self.editor, self.start
        editor.close_completion()
        with editor.edit_transaction():
            editor.text.delete(start, "insert")
            editor.text.insert(start, word)
        editor.text.focus_set()
        return "break"


def completion_words(source, prefix):
    labels = re.findall(
        r"^\s*([A-Za-z_]\w*)\s*(?::|\s+(?:EQU|SET)\b)",
        source,
        re.MULTILINE | re.IGNORECASE,
    )
    words = {word.upper(): word for word in labels}
    words.update({word: word for word in WORDS})
    return sorted(
        (
            word
            for word in words.values()
            if word.casefold().startswith(prefix.casefold())
        ),
        key=str.casefold,
    )
