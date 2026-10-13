"""Reusable collapsible and scrollable Tk containers."""

import tkinter as tk
from tkinter import ttk

from . import theme


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
