# Native Releases

The installer bundles the Python interpreter, Tk, application code, data, and
project license. Windows setup displays the license; Linux also installs it in
`/usr/share/doc/mcs51-studio/copyright`.
Build each OS/architecture on its own native machine; PyInstaller is not a
cross-compiler. The release workflow covers Windows x64, Linux amd64/arm64, and
macOS Intel/Apple Silicon.

## Automated Builds

Run **Build installers** from GitHub Actions for test artifacts. Each job runs the
tests, freezes the app, smoke-tests the frozen executable, and creates its native
installer and SHA-256 checksum. Download them from that workflow's artifacts.

For a release, update `VERSION` in `metadata.py`, then push the corresponding
`v<version>` tag. After all five native builds succeed, the workflow creates a
**draft GitHub Release** containing the installers. Review, test installation on
clean machines, and publish the draft explicitly. No release has been published
from the current local repository.

Outputs are:

- `MCS51-Studio-<version>-windows-x64-setup.exe`
- `MCS51-Studio-<version>-macos-arm64.pkg` and `*-macos-x64.pkg`
- `MCS51-Studio-<version>-linux-amd64.deb` and `*-linux-arm64.deb`
- One `.sha256` file beside each installer.

## Local Packaging

Use the virtual environment from [development](development.md):

```sh
python -m pip install '.[build]'
python scripts/build_release.py
```

On Linux without a display, run the build command through `xvfb-run -a`.
Installers are written to `release/`; frozen applications and temporary build
data are written to `dist/` and `build/`. These directories are ignored by Git.

Platform tools:

- Windows: Inno Setup 6 (`ISCC.exe`). It is included in the selected GitHub runner.
- macOS: Apple command line tools providing `pkgbuild`.
- Linux: `dpkg-deb`, Tcl/Tk, X11 libraries, and `xvfb`/`xauth` for headless smoke tests.

The Windows installer installs per user and adds a Start-menu shortcut. The
macOS package installs in `/Applications`. The Debian package installs under
`/opt/mcs51-studio`, adds an applications-menu entry and a `mcs51-studio` command,
and declares system-library dependencies. Set `MCS51_DEB_MAINTAINER` to the
release maintainer identity when preparing public Debian packages.

## Signing And Release Validation

Default CI artifacts are **unsigned test installers**. Production Windows code
signing and Apple signing/notarization require the maintainer's certificates;
none are configured in this repository.

For a macOS build on a machine with the certificates already installed, the build
script accepts `MCS51_MAC_APPLICATION_IDENTITY`, `MCS51_MAC_INSTALLER_IDENTITY`,
and `MCS51_MAC_NOTARY_PROFILE`. A notary profile must already exist in that
machine's keychain. Windows signing should be configured in the release
environment before publication.

Frozen startup tests do not prove installer upgrades or OS trust acceptance.
Validate installation, launch, save, upgrades, and uninstall on clean target
machines before publishing. Windows/Linux native runs await the first CI run;
they cannot be validated natively on the current Mac.

## Application Artwork

The editable vector master is `packaging/icons/mcs51-studio.svg`. Native icon
assets are committed, so normal development and release builds do not require
image-conversion tools. The Windows executable and setup wizard use the ICO;
macOS uses the ICNS bundle resource; Linux installs SVG/PNG icons in the hicolor
icon theme. The UI loads its bundled PNG for window and running-app icons.
Windows shortcuts and the running process share the application ID in
`metadata.py` so taskbar grouping identifies the same application.

To update the artwork, edit the SVG and export a transparent 1024×1024 PNG with
a vector editor. Then install the optional artwork tools and generate all sizes:

```sh
python -m pip install -e '.[artwork]'
python scripts/build_icons.py path/to/exported-1024.png
```

Commit the SVG, ICO, ICNS, and `src/mcs51_studio/data/icon.png` together and rebuild
native installers. The generator uses Pillow only during artwork preparation;
Pillow is not a runtime dependency.
