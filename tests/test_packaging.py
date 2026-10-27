"""Installer destination and upgrade contract."""

import importlib.util
import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class MacInstallerContract(unittest.TestCase):
    def test_installer_replaces_only_the_application_at_its_destination(self):
        script = Path(__file__).resolve().parents[1] / "scripts/build_release.py"
        spec = importlib.util.spec_from_file_location("release_builder", script)
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        calls = []

        def inspect(*arguments):
            calls.append(arguments)
            args = list(arguments)
            self.assertEqual(
                args[args.index("--install-location") + 1], "/Applications"
            )
            root = Path(args[args.index("--root") + 1])
            self.assertTrue((root / "MCS51 Studio.app/Contents/marker").is_file())
            with Path(args[args.index("--component-plist") + 1]).open("rb") as stream:
                component = plistlib.load(stream)[0]
            self.assertFalse(component["BundleIsRelocatable"])
            self.assertTrue(component["BundleIsVersionChecked"])
            self.assertTrue(component["BundleHasStrictIdentifier"])
            self.assertEqual(component["BundleOverwriteAction"], "upgrade")

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            bundle = base / "MCS51 Studio.app"
            (bundle / "Contents").mkdir(parents=True)
            (bundle / "Contents/marker").touch()
            with (
                patch.object(builder, "run", side_effect=inspect),
                patch.object(builder, "require_tool", return_value="pkgbuild"),
                patch.dict("os.environ", {}, clear=True),
            ):
                result = builder.macos_installer(bundle, base, "arm64")
            self.assertEqual(len(calls), 1)
            self.assertEqual(
                result.name, f"MCS51-Studio-{builder.VERSION}-macos-arm64.pkg"
            )
