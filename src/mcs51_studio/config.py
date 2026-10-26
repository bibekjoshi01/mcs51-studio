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
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return base / "mcs51-studio" / "settings.json"
