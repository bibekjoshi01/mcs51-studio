"""Application identity and window icons for source and packaged launches."""

import base64
import sys
import tkinter as tk

from ..metadata import APP_ID
from ..resources import DATA


def prepare_process_identity():
    """Match the installed Windows shortcut before creating a native window."""
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)


def apply_icon(root):
    # Keep the PhotoImage alive for the lifetime of the root window. Default also
    # supplies this icon to subsequent tool and dialog windows.
    encoded = base64.b64encode(DATA.joinpath("icon.png").read_bytes())
    root._app_icon = tk.PhotoImage(master=root, data=encoded)
    root.iconphoto(True, root._app_icon)
