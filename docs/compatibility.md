# Supported features and simulation limits

MCS51 Studio is an educational simulator under active development. It is not yet
a cycle-accurate hardware model. Use the limits below when designing exercises.

## Available now

- Assembly editor, two-pass assembler, source listing, and Intel HEX import/export.
- CPU stepping, running, breakpoints, registers, internal memory, and interrupts.
- Timer and on-chip serial models.
- Configurable virtual board: LEDs, switches, keypad, seven-segment displays,
  character LCD, ADC/DAC, motor, comparator, and external UART.
- Native installer build targets for Windows, Linux, and macOS.

## Validation

Baseline regression fixtures cover all 256 opcode values over 8,192 sampled CPU
states, 1,024 timer cases, 192 serial cases, and 260 assembly inputs. Integration
tests exercise assembly, Intel HEX round trips, interrupts, and selected board
interactions. These detect unintended changes; they do not prove hardware
correctness. Independent hardware-spec validation is still needed.

GUI smoke tests assemble the bundled example, step and run it, and save settings.
Windows/Linux native installer and GUI validation is configured in CI; successful
runs on those systems and a complete visual review remain pending.

## Known limits

- External data memory is not modeled: MOVX currently does nothing. Reserved A5
  also does nothing. This must be made explicit in lessons using external memory.
- Some arithmetic flags, parity writes, split timer modes, and 13-bit timer
  overflows retain baseline behavior and need independent hardware-spec checks.
- The simulated machine cycle is fixed at one microsecond; oscillator selection
  is not exposed in the interface.
- Shared-pin timing, keypad modes, switch/key bounce, LCD busy timing and custom
  glyph rendering, and varied-clock UART framing need further work.
- Broader assembler syntax and clearer diagnostics are planned.
- Guided lessons and exercise assessment are not implemented. The redesigned
  workbench is available; Windows/Linux visual review remains pending.

See [architecture.md](architecture.md) for the development direction.
