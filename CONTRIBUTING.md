# Contributing

Bug reports, documentation improvements, and focused fixes are welcome. Open an
issue before starting a larger feature or changing simulator behavior.

## Get Started

1. Fork the repository and create a branch from `main`.
2. Install Python 3.10+ with Tk. Follow the [development setup](docs/development.md)
   to create and activate a virtual environment, then run:

   ```sh
   python -m pip install -e ".[dev]"
   python -m mcs51_studio
   ```

3. Keep changes focused. Check the [architecture](docs/architecture.md) and
   [supported behavior](docs/compatibility.md), and add regression coverage for
   behavior changes.

## Check Your Changes

```sh
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
```

For UI or simulator changes, also run these in a graphical session:

```sh
python tests/gui.py
python tests/guide_gui.py
python tests/stress_gui.py
```

## Submit A Pull Request

Target `main`. Explain the problem, what changed, and which checks passed. Link
related issues and include screenshots for visible UI changes.

For bug reports, include your OS/app version, steps to reproduce, expected and
actual behavior, and a small assembly example when relevant.

Read the [license](LICENSE) before contributing. Submit only work you own or have
permission to contribute, including permission for the maintainer to distribute
it under the project's educational and separately agreed commercial terms.
