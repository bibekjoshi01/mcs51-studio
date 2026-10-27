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
    """Pixel-based wheel scrolling, confined to this view's descendants."""

    def __init__(self, parent):
        super().__init__(parent)
        self.windowing_system = self.tk.call("tk", "windowingsystem")
        self._wheel_remainder = 0.0
        self._layout_job = None
        self.canvas = tk.Canvas(
            self, background=theme.PANEL, highlightthickness=0, yscrollincrement=1
        )
        scrollbar = ttk.Scrollbar(self, command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.content = ttk.Frame(self.canvas, padding=12)
        self._window = self.canvas.create_window(0, 0, anchor="nw", window=self.content)
        self.canvas.bind("<Configure>", self._resize)
        self.content.bind("<Configure>", self._schedule_extent)
        self._wheel_window = self.winfo_toplevel()
        self._bindings = {
            sequence: self._wheel_window.bind(sequence, self.wheel, add=True)
            for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>")
        }
        self.bind("<Destroy>", self._cleanup, add=True)

    def _resize(self, event):
        if int(float(self.canvas.itemcget(self._window, "width"))) != event.width:
            self.canvas.itemconfigure(self._window, width=event.width)
        self._schedule_extent()

    def _schedule_extent(self, event=None):
        if self._layout_job is None:
            self._layout_job = self.after_idle(self._sync_extent)

    def _sync_extent(self):
        self._layout_job = None
        height = max(self.canvas.winfo_height(), self.content.winfo_reqheight())
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), height))

    def _cleanup(self, event):
        if event.widget is not self:
            return
        if self._layout_job is not None:
            self.after_cancel(self._layout_job)
            self._layout_job = None
        for sequence, binding in self._bindings.items():
            # Older Tkinter releases clear all callbacks even with a function ID.
            # Remove only our script and preserve other scrollable views.
            script = self._wheel_window.bind(sequence)
            remaining = "\n".join(
                line
                for line in script.splitlines()
                if not line.startswith(f'if {{"[{binding} ')
            )
            self.tk.call("bind", self._wheel_window._w, sequence, remaining)
            self._wheel_window.deletecommand(binding)
        self._bindings.clear()

    def wheel(self, event):
        widget_path = str(event.widget)
        if not (widget_path == str(self) or widget_path.startswith(str(self) + ".")):
            return None
        if not self.canvas.winfo_ismapped():
            return None
        # Text, lists, and selectors already process wheel input in their class
        # bindings. Let them scroll once without also moving the surrounding page.
        if event.widget.winfo_class() in {
            "Text",
            "Listbox",
            "Treeview",
            "TCombobox",
            "Spinbox",
            "TSpinbox",
        }:
            return None
        if self.content.winfo_reqheight() <= self.canvas.winfo_height():
            return None
        button = getattr(event, "num", None)
        delta = getattr(event, "delta", 0)
        if button in (4, 5):
            pixels = -40 if button == 4 else 40
        elif not delta:
            return None
        elif self.windowing_system == "aqua":
            pixels = -delta
        else:
            pixels = -delta / 120 * 40
        self._wheel_remainder += pixels
        movement = int(self._wheel_remainder)
        self._wheel_remainder -= movement
        if movement:
            self.canvas.yview_scroll(movement, "units")
        return "break"


class FlowGrid(ttk.Frame):
    """Even-width horizontal rows that wrap only when the column count changes."""

    def __init__(self, parent, min_width=132, max_columns=5):
        super().__init__(parent)
        self.items = []
        self.min_width = min_width
        self.max_columns = max_columns
        self.columns = 0
        self._job = None
        self.bind("<Configure>", self._schedule)
        self.bind("<Destroy>", self._cleanup, add=True)

    def add(self, widget):
        self.items.append(widget)
        self._schedule()

    def _schedule(self, event=None):
        if self._job is None:
            self._job = self.after_idle(self._layout)

    def _layout(self):
        self._job = None
        columns = min(self.max_columns, max(1, self.winfo_width() // self.min_width))
        if columns == self.columns:
            return
        for column in range(max(columns, self.columns)):
            self.columnconfigure(
                column,
                weight=1 if column < columns else 0,
                uniform="toggles" if column < columns else "",
            )
        self.columns = columns
        for index, widget in enumerate(self.items):
            widget.grid(
                row=index // columns,
                column=index % columns,
                sticky="ew",
                padx=3,
                pady=4,
            )
        self.event_generate("<<FlowLayoutChanged>>", when="tail")

    def _cleanup(self, event):
        if event.widget is self and self._job is not None:
            self.after_cancel(self._job)
