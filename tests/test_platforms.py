"""Platform contracts that can be checked without a desktop session."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from mcs51_studio.config import save_shortcut, settings_path


class PlatformSettings(unittest.TestCase):
    def test_platform_configuration_directories(self):
        home = Path("test-home")
        cases = {
            "darwin": home / "Library" / "Application Support",
            "win32": home / "AppData" / "Roaming",
            "linux": home / ".config",
        }
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=home),
        ):
            for platform, directory in cases.items():
                with self.subTest(platform=platform), patch("sys.platform", platform):
                    self.assertEqual(
                        settings_path(), directory / "mcs51-studio" / "settings.json"
                    )

    def test_environment_configuration_directories(self):
        base = Path("custom-config")
        for platform, variable in (("win32", "APPDATA"), ("linux", "XDG_CONFIG_HOME")):
            with (
                self.subTest(platform=platform),
                patch("sys.platform", platform),
                patch.dict(os.environ, {variable: str(base)}, clear=True),
            ):
                self.assertEqual(
                    settings_path(), base / "mcs51-studio" / "settings.json"
                )

    def test_explicit_settings_file(self):
        file = Path("portable") / "settings.json"
        with patch.dict(os.environ, {"MCS51_STUDIO_SETTINGS": str(file)}):
            self.assertEqual(settings_path(), file)

    def test_native_save_shortcut(self):
        self.assertEqual(save_shortcut("aqua"), "<Command-s>")
        self.assertEqual(save_shortcut("win32"), "<Control-s>")
        self.assertEqual(save_shortcut("x11"), "<Control-s>")
