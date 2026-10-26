"""Build and smoke-test a native installer on its target operating system."""

import hashlib
import json
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcs51_studio.metadata import APP_ID, APP_NAME, VERSION

ROOT = Path(__file__).resolve().parents[1]


def run(*arguments, **kwargs):
    subprocess.run([str(a) for a in arguments], check=True, **kwargs)


def architecture():
    value = platform.machine().lower()
    if value in ("amd64", "x86_64"):
        return "x64"
    if value in ("arm64", "aarch64"):
        return "arm64"
    raise RuntimeError(f"Unsupported architecture: {value}")


def require_tool(name):
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"Required packaging tool not found: {name}")
    return found


def smoke_test(executable):
    with tempfile.TemporaryDirectory(prefix="mcs51-release-smoke-") as temporary:
        report = Path(temporary) / "report.json"
        environment = {**os.environ, "MCS51_STUDIO_SMOKE_REPORT": str(report)}
        run(executable, "--smoke-test", env=environment, timeout=60)
        if not report.exists() or not json.loads(
            report.read_text(encoding="utf-8")
        ).get("ok"):
            raise RuntimeError(f"Frozen application smoke test failed: {report}")


def freeze():
    name = "mcs51-studio" if sys.platform == "linux" else APP_NAME
    arguments = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--name",
        name,
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build" / "pyinstaller"),
        "--specpath",
        str(ROOT / "build"),
        "--paths",
        str(ROOT / "src"),
        "--add-data",
        f"{ROOT / 'src/mcs51_studio/data'}:mcs51_studio/data",
    ]
    if sys.platform == "darwin":
        arguments += [
            "--icon",
            str(ROOT / "packaging/icons/mcs51-studio.icns"),
            "--osx-bundle-identifier",
            APP_ID,
        ]
        identity = os.environ.get("MCS51_MAC_APPLICATION_IDENTITY")
        if identity:
            arguments += ["--codesign-identity", identity]
    if sys.platform == "win32":
        arguments += ["--icon", str(ROOT / "packaging/icons/mcs51-studio.ico")]
    arguments.append(str(ROOT / "launch.py"))
    run(*arguments, cwd=ROOT)
    bundle = ROOT / "dist" / name
    executable = bundle / (f"{name}.exe" if sys.platform == "win32" else name)
    if sys.platform == "darwin":
        bundle = bundle.with_suffix(".app")
        executable = bundle / "Contents" / "MacOS" / name
        # Installer upgrades must see the package version in the app bundle too.
        info_path = bundle / "Contents" / "Info.plist"
        with info_path.open("rb") as stream:
            info = plistlib.load(stream)
        info.update(CFBundleShortVersionString=VERSION, CFBundleVersion=VERSION)
        with info_path.open("wb") as stream:
            plistlib.dump(info, stream)
        identity = os.environ.get("MCS51_MAC_APPLICATION_IDENTITY")
        signing = [require_tool("codesign"), "--force", "--sign", identity or "-"]
        if identity:
            signing += ["--options", "runtime", "--timestamp"]
        run(*signing, bundle)
    smoke_test(executable)
    return bundle


def windows_installer(bundle, output, arch):
    if arch != "x64":
        raise RuntimeError("Windows installers currently target x64")
    compiler = shutil.which("ISCC")
    if not compiler:
        compiler = str(
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
            / "Inno Setup 6"
            / "ISCC.exe"
        )
    if not Path(compiler).is_file():
        raise RuntimeError(
            "Install Inno Setup 6 and make ISCC available before building"
        )
    name = f"MCS51-Studio-{VERSION}-windows-{arch}-setup"
    run(
        compiler,
        f"/DAppVersion={VERSION}",
        f"/DBundleDir={bundle}",
        f"/DOutputDir={output}",
        f"/DOutputName={name}",
        f"/DIconFile={ROOT / 'packaging/icons/mcs51-studio.ico'}",
        f"/DAppUserModelID={APP_ID}",
        ROOT / "packaging/windows/setup.iss",
    )
    return output / f"{name}.exe"


def macos_installer(bundle, output, arch):
    installer = output / f"MCS51-Studio-{VERSION}-macos-{arch}.pkg"
    arguments = [
        require_tool("pkgbuild"),
        "--component",
        str(bundle),
        "--install-location",
        "/Applications",
        "--identifier",
        "org.mcs51studio.desktop",
        "--version",
        VERSION,
        "--ownership",
        "recommended",
    ]
    identity = os.environ.get("MCS51_MAC_INSTALLER_IDENTITY")
    if identity:
        arguments += ["--sign", identity]
    run(*arguments, installer)
    notary = os.environ.get("MCS51_MAC_NOTARY_PROFILE")
    if notary:
        run(
            "xcrun",
            "notarytool",
            "submit",
            installer,
            "--keychain-profile",
            notary,
            "--wait",
        )
        run("xcrun", "stapler", "staple", installer)
    return installer


def linux_installer(bundle, output, arch):
    deb_arch = "amd64" if arch == "x64" else "arm64"
    installer = output / f"MCS51-Studio-{VERSION}-linux-{deb_arch}.deb"
    with tempfile.TemporaryDirectory(prefix="mcs51-deb-") as temporary:
        staging = Path(temporary)
        shutil.copytree(bundle, staging / "opt/mcs51-studio", symlinks=True)
        (staging / "usr/bin").mkdir(parents=True)
        (staging / "usr/bin/mcs51-studio").symlink_to("/opt/mcs51-studio/mcs51-studio")
        applications = staging / "usr/share/applications"
        applications.mkdir(parents=True)
        shutil.copy2(ROOT / "packaging/linux/mcs51-studio.desktop", applications)
        for size, source in (
            ("512x512", ROOT / "src/mcs51_studio/data/icon.png"),
            ("scalable", ROOT / "packaging/icons/mcs51-studio.svg"),
        ):
            icons = staging / "usr/share/icons/hicolor" / size / "apps"
            icons.mkdir(parents=True)
            shutil.copy2(source, icons / f"mcs51-studio{source.suffix}")
        control = staging / "DEBIAN"
        control.mkdir()
        maintainer = os.environ.get("MCS51_DEB_MAINTAINER", "MCS51 Studio contributors")
        if "\n" in maintainer or "\r" in maintainer:
            raise ValueError("Maintainer must be a single line")
        (control / "control").write_text(
            f"Package: mcs51-studio\nVersion: {VERSION}\nSection: education\nPriority: optional\n"
            f"Architecture: {deb_arch}\nMaintainer: {maintainer}\n"
            "Depends: libc6 (>= 2.35), libgcc-s1, libstdc++6, libfontconfig1, "
            "libx11-6, libxext6, libxrender1, libxft2, libxss1, libxcb1\n"
            "Description: 8051 desktop assembly workbench\n"
            " Assembly editor, debugger, and virtual microcontroller training board.\n",
            encoding="utf-8",
        )
        run(
            require_tool("dpkg-deb"),
            "--root-owner-group",
            "--build",
            staging,
            installer,
        )
    return installer


def main():
    builders = {
        "win32": windows_installer,
        "darwin": macos_installer,
        "linux": linux_installer,
    }
    if sys.platform not in builders:
        raise SystemExit(f"Unsupported operating system: {sys.platform}")
    arch = architecture()
    output = ROOT / "release"
    output.mkdir(exist_ok=True)
    bundle = freeze()
    installer = builders[sys.platform](bundle, output, arch)
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    installer.with_name(installer.name + ".sha256").write_text(
        f"{digest}  {installer.name}\n", encoding="utf-8"
    )
    print(f"Installer: {installer}")


if __name__ == "__main__":
    main()
