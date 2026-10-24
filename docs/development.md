# Development

Run from Python source using the commands below. End users should use the
installers described in the [README](../README.md).

## Setup And Run

Use Python 3.10+ with Tk and a graphical desktop. `python -m tkinter` should open
a test window. Debian/Ubuntu may need `python3-tk`; Windows/macOS Python builds
must include matching Tcl/Tk support. The app uses the standard library and Tk.

Windows PowerShell, from the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m mcs51_studio
```

Linux/macOS:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m mcs51_studio
```

With a suitable Python/Tk already installed, `python3 scripts/launch.py` also runs
from a checkout (`py -3 scripts/launch.py` on Windows).

## Checks

Use the virtual environment's Python, or activate it first:

```sh
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
python tests/gui.py
```

The first command is headless, covering CPU regression cases, assembler boundaries,
quoted data, malformed source, and atomic saves. `tests/gui.py` exercises clipboard
commands, grouped undo, completion, Unicode, large documents, search/replace,
inline errors, stale-code protection, file safety,
breakpoints, execution controls, scrolling, hardware rows, inspector values,
and layout at two window sizes; it requires a
display. On headless Linux, use `xvfb-run -a python tests/gui.py`. CI runs headless
checks on Windows/Linux/macOS with Python 3.10, 3.12, and 3.13, and desktop checks
on Python 3.12. Frozen release builds run their own minimal startup check.

## Contributing

Read the [architecture](architecture.md) and [known limits](compatibility.md).
Open an issue for larger changes; keep pull requests focused, describe the user
impact, and include relevant validation. Use Ruff for formatting. Add tests for
behavior changes without duplicating implementation details.

Contributions must be your own work or material you have permission to submit.
The [license](../LICENSE) permits the maintainer to distribute contributions under
both the educational terms and separately agreed commercial licenses. Confirm
you have that authority before submitting a contribution. For sensitive security
reports or commercial permission, contact the maintainer through the
[GitHub profile](https://github.com/bibekjoshi01).

## Settings

Settings stay outside the checkout and installed application:

- Windows: `%APPDATA%/mcs51-studio/settings.json`.
- macOS: `~/Library/Application Support/mcs51-studio/settings.json`.
- Linux: `$XDG_CONFIG_HOME/mcs51-studio/settings.json`, defaulting to `~/.config`.

`MCS51_STUDIO_SETTINGS` overrides the settings file for isolated runs. Source and
settings use UTF-8; Intel HEX output uses ASCII. Name, ID, and version live in
`metadata.py`. See [releases](releases.md) for packaging and signing.
