# Architecture and learning roadmap

MCS51 Studio separates machine behavior from presentation so the interface and
teaching material can evolve without rewriting instruction execution.

## Code structure

```text
src/mcs51_studio/
  engine/
    cpu.py          CPU state, instructions, interrupts, and timers
    assembler.py    Assembly parsing, source mapping, and Intel HEX
    serial.py       On-chip serial controller
  hardware/
    board.py        Wiring, peripheral integration, and board stepping
    lcd.py          Character LCD controller
    uart.py         External UART endpoint
  ui/
    application.py  Tk editor, debugger, board views, and dialogs
  data/             Instruction catalog and runnable example
  config.py         Platform settings paths and keyboard conventions
  resources.py      Bundled data loading
  metadata.py       Application name and version
  smoke.py          Source and packaged GUI smoke check
```

`engine` must remain usable without Tk, display access, or settings files.
`hardware` works with CPU state and pins; it must not import UI code. `ui` owns
user interaction and composes the engine and virtual board. Shared resource and
metadata modules stay outside these layers. Tests instantiate CPU and board
models directly; the GUI smoke check exercises their integration through the UI.

The desktop view is currently a single module. As the redesign starts, extract
editor, debugger, board, and lesson views into `ui/` modules. Put run/pause/step
coordination into a shared session/controller when multiple views need it, so
widget callbacks do not become a second CPU implementation. Avoid creating
placeholder modules until they have working behavior.

## Learning direction

Build the curriculum in small, executable stages:

1. Number formats, registers, flags, internal RAM, SFRs, and addressing modes.
2. Arithmetic, logic, branches, stack, subroutines, and instruction tracing.
3. Port I/O, bit operations, switches, LEDs, keypad, and multiplexed displays.
4. Timer/counter modes, interrupts, priorities, serial communication, and baud rates.
5. LCD, ADC/DAC, waveform exploration, and integrated board projects.
6. External memory and MOVX after external-memory execution is implemented.

Each lesson should include an assembly example, an observable machine-state
change, a short explanation, and an exercise with a deterministic expected
result. Introduce a `learning/` package when the first lesson runner is built;
keep lesson content and assessment rules independent of Tk. The existing LED
counter is a starter example, not a complete curriculum.

## Implementation priorities

First validate known CPU and timing limits against manufacturer documentation.
Then add a reusable simulation session and focused UI views, followed by lesson
navigation and assessments. Extend headless tests for machine changes and use
GUI smoke checks for view integration. Installer builds remain native to each
operating system; development commands live in [development.md](development.md)
and distribution commands in [releases.md](releases.md).
