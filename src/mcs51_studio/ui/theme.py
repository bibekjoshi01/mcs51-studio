"""Shared desktop palette, typography, and native Tk/ttk styling."""

from tkinter import font, ttk

BG = "#101723"
PANEL = "#182131"
INPUT = "#121B29"
TEXT = "#E7EDF8"
MUTED = "#92A1B9"
MINT = "#78E4BB"
FOCUS = "#A598F8"
BORDER = "#303D55"
SELECTION = "#303A58"
ERROR = "#F0949D"


def apply_theme(root):
    families = set(font.families(root))
    interface = next(
        (f for f in ("Avenir Next", "Segoe UI", "DejaVu Sans") if f in families),
        "TkDefaultFont",
    )
    technical = next(
        (
            f
            for f in ("Menlo", "Cascadia Mono", "Consolas", "DejaVu Sans Mono")
            if f in families
        ),
        "TkFixedFont",
    )
    # Negative Tk sizes are pixels, keeping the intended density across platforms.
    font.nametofont("TkDefaultFont").configure(family=interface, size=-12)
    font.nametofont("TkTextFont").configure(family=interface, size=-12)
    font.nametofont("TkFixedFont").configure(family=technical, size=-12)
    root.configure(background=BG)
    for option, value in {
        "*background": PANEL,
        "*foreground": TEXT,
        "*insertBackground": MINT,
        "*selectBackground": SELECTION,
        "*selectForeground": TEXT,
        "*Entry.background": INPUT,
        "*Text.background": INPUT,
        "*Menu.activeBackground": SELECTION,
        "*Menu.activeForeground": TEXT,
        "*Listbox.background": INPUT,
        "*Listbox.foreground": TEXT,
        "*highlightColor": FOCUS,
        "*highlightBackground": BORDER,
    }.items():
        root.option_add(option, value)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        ".",
        background=PANEL,
        foreground=TEXT,
        font=(interface, -12),
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        focuscolor=FOCUS,
    )
    style.configure("TFrame", background=PANEL)
    style.configure("Shell.TFrame", background=BG)
    style.configure("TLabel", background=PANEL, foreground=TEXT)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("Section.TLabel", foreground=MUTED, font=(interface, -10, "bold"))
    style.configure("Title.TLabel", font=(interface, -20, "bold"))
    style.configure("Mono.TLabel", font=(technical, -12))
    style.configure("TLabelframe", borderwidth=1, relief="solid", padding=8)
    style.configure(
        "TLabelframe.Label", foreground=MUTED, font=(interface, -10, "bold")
    )
    style.configure("TButton", padding=(10, 6), borderwidth=1, relief="flat")
    style.map(
        "TButton",
        background=[("active", SELECTION), ("pressed", BORDER)],
        foreground=[("disabled", MUTED)],
    )
    style.configure("Primary.TButton", background=MINT, foreground=BG)
    style.map(
        "Primary.TButton",
        background=[("active", "#9CEFCF"), ("pressed", "#58C9A0")],
        foreground=[("active", BG)],
    )
    style.configure(
        "TEntry",
        fieldbackground=INPUT,
        foreground=TEXT,
        insertcolor=MINT,
        padding=5,
        borderwidth=1,
    )
    style.configure(
        "TCombobox", fieldbackground=INPUT, foreground=TEXT, arrowcolor=MUTED, padding=4
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", INPUT)],
        foreground=[("readonly", TEXT)],
        selectbackground=[("readonly", INPUT)],
        selectforeground=[("readonly", TEXT)],
    )
    style.configure("TCheckbutton", padding=3, indicatorbackground=INPUT)
    style.map(
        "TCheckbutton",
        background=[("active", PANEL)],
        indicatorbackground=[("selected", MINT)],
    )
    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", padding=(16, 8), background=BG, foreground=MUTED)
    style.map(
        "TNotebook.Tab",
        background=[("selected", PANEL)],
        foreground=[("selected", MINT)],
    )
    style.configure(
        "Treeview",
        background=INPUT,
        fieldbackground=INPUT,
        foreground=TEXT,
        rowheight=25,
        borderwidth=0,
        font=(technical, -12),
    )
    style.configure(
        "Treeview.Heading",
        background=PANEL,
        foreground=MUTED,
        font=(interface, -10, "bold"),
        padding=6,
        relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", SELECTION)],
        foreground=[("selected", TEXT)],
    )
    style.configure("TPanedwindow", background=BG, sashwidth=6)
    style.configure(
        "Vertical.TScrollbar",
        background=BORDER,
        troughcolor=PANEL,
        arrowcolor=MUTED,
        borderwidth=0,
    )
    style.configure(
        "Horizontal.TScrollbar",
        background=BORDER,
        troughcolor=PANEL,
        arrowcolor=MUTED,
        borderwidth=0,
    )
    style.configure(
        "TNotebook.Tab",
        borderwidth=0,
        lightcolor=PANEL,
        darkcolor=PANEL,
        bordercolor=PANEL,
    )
    style.map(
        "TNotebook.Tab",
        lightcolor=[("selected", PANEL), ("!selected", BG)],
        darkcolor=[("selected", PANEL), ("!selected", BG)],
        bordercolor=[("selected", PANEL), ("!selected", BG)],
    )
    for orientation, sticky in (("Vertical", "ns"), ("Horizontal", "ew")):
        name = f"{orientation}.TScrollbar"
        style.layout(
            name,
            [
                (
                    f"{orientation}.Scrollbar.trough",
                    {
                        "sticky": sticky,
                        "children": [
                            (
                                f"{orientation}.Scrollbar.thumb",
                                {"expand": "1", "sticky": "nswe"},
                            )
                        ],
                    },
                )
            ],
        )
        style.configure(
            name,
            background=BORDER,
            troughcolor=INPUT,
            bordercolor=INPUT,
            lightcolor=BORDER,
            darkcolor=BORDER,
            width=8,
            borderwidth=0,
            gripcount=0,
        )
        style.map(name, background=[("active", MUTED), ("pressed", FOCUS)])
    return interface, technical
