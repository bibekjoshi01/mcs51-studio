# Development

## Local setup

Use Python 3.10+ and a virtual environment. Install with `python -m pip install -e '.[dev]'`.
The runtime has no third-party Python dependencies. Tk is required only for the UI;
`python -m tkinter` opens its installation check window.

Run tests with `python -m unittest discover -s tests -v`. Use `ruff check .` and `ruff format --check .` for code style. The test suite stays
headless and uses fixtures under `tests/fixtures`. GitHub Actions runs this same
command for Python 3.10, 3.12, and 3.13.

## macOS application

```sh
python -m pip install '.[build]'
sh scripts/build_macos.sh
```

The output is `dist/MCS51 Studio.app`, built for the current machine's architecture.
Generated bundles, caches, and build metadata are ignored by Git.

## Settings

Settings are stored outside the repository:

- macOS: `~/Library/Application Support/mcs51-studio/settings.json`
- Windows: `%APPDATA%/mcs51-studio/settings.json`
- Linux: `$XDG_CONFIG_HOME/mcs51-studio/settings.json`, defaulting to `~/.config`.

Set `MCS51_STUDIO_SETTINGS` to an explicit file path for testing or a portable setup.
Existing settings can be copied into the new location; automatic import from the
earlier project name is not performed.

## Layout

The `mcs51_studio` package owns simulator code and resource loading. `data/` holds
the instruction inventory and the default LED program. Tests and compatibility
notes remain outside the installed package. App identity is centralized in
`metadata.py`; packaging reads its version.
