"""Keep user settings outside the source checkout and application bundle."""

import os
import sys
from pathlib import Path


def settings_path():
    override = os.environ.get("MCS51_STUDIO_SETTINGS")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = (
            Path(os.environ["APPDATA"])
            if "APPDATA" in os.environ
            else Path.home() / "AppData" / "Roaming"
        )
    else:
        base = (
            Path(os.environ["XDG_CONFIG_HOME"])
            if "XDG_CONFIG_HOME" in os.environ
            else Path.home() / ".config"
        )
    return base / "mcs51-studio" / "settings.json"
