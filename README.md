# MCS51 Studio

A Python desktop workbench for writing, stepping through, and inspecting 8051 assembly programs.

Includes an assembler, register and memory views, breakpoints, Intel HEX import/export,
and a virtual board with LEDs, switches, keypad, displays, ADC/DAC, motor, and UART.
The processor runs in Python; Java is not required.

## Run

Requires **Python 3.10+ with Tk**. Check Tk with `python3 -m tkinter`.

```sh
python3 launch.py
```

On macOS, you can also double-click **MCS51 Studio.command**.
Click **Assemble**, then **Step** (F7) or **Run / Pause** (F5) to try the included LED counter.
Double-click a listing row to toggle a breakpoint.

For an installed command:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
mcs51-studio
```

On Windows, activate the environment with `.venv\Scripts\activate`.

## Develop

```sh
python -m unittest discover -s tests -v
```

The tests compare the Python engine with preserved reference fixtures, covering
8,192 instruction cases, 1,024 timer cases, 192 serial cases, and 260 assembler inputs.
They run without a display, Tk, or the original Java app.

```text
src/mcs51_studio/   Application, simulator, and bundled data
tests/             Reference fixtures and integration tests
docs/              Compatibility and development notes
scripts/           Native app packaging
```

See [development](docs/development.md) for packaging and settings.

## Status

This is an experimental reconstruction informed by EdSim51. The processor has
reference coverage; full peripheral and interface parity is still in progress.
See [compatibility](docs/compatibility.md) for the verified scope and remaining work.

EdSim51 was created by James Rogers. Attribution and rights details are preserved
in [NOTICE.txt](NOTICE.txt).
