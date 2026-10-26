# Development

These instructions run the application **from Python source**. End users should
use the installers described in the [README](../README.md).

## Requirements

- Python 3.10 or newer with Tk available.
- Git and a graphical desktop session for the UI.
- No Java runtime or third-party Python GUI framework is needed.

Check Tk with `python -m tkinter` (or `python3 -m tkinter`). It should open a test
window. On Debian/Ubuntu, install `python3-tk` if needed. On Windows/macOS, use a
Python distribution with matching Tcl/Tk support.

## Windows — PowerShell

From the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m mcs51_studio
```

Calling the virtual environment's Python directly avoids requiring a PowerShell
activation-policy change.

## Linux and macOS

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m mcs51_studio
```

With a suitable Python/Tk already installed, `python3 launch.py` also runs directly
from a checkout (`py -3 launch.py` on Windows).

## Tests and code style

Using the same virtual environment:

```sh
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
```

Substitute `.venv/bin/python` on Linux/macOS or `.\.venv\Scripts\python.exe` on
Windows if the environment is not activated. Headless tests do not need Tk or a
display and cover the preserved reference fixtures plus platform settings.

For a real GUI startup and debugger check, run `python -m mcs51_studio --smoke-test`.
On headless Linux, use `xvfb-run -a python -m mcs51_studio --smoke-test`.
GitHub Actions runs tests on all three operating systems and performs GUI smoke
checks on Python 3.12.

## Settings and layout

Settings remain outside the checkout and installed application:

- macOS: `~/Library/Application Support/mcs51-studio/settings.json`
- Windows: `%APPDATA%/mcs51-studio/settings.json`
- Linux: `$XDG_CONFIG_HOME/mcs51-studio/settings.json`, defaulting to `~/.config`.

Set `MCS51_STUDIO_SETTINGS` to an explicit file for an isolated or portable setup.
Files use UTF-8; Intel HEX output uses ASCII.

`src/mcs51_studio/` contains the application and bundled data, `tests/` contains
reference and integration tests, and `packaging/` contains installer assets.
Version and application name are defined in `metadata.py`.
Native installers are documented separately in [releases.md](releases.md).
