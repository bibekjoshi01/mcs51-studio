# Supported features and simulation limits

This guide defines the processor and peripheral behavior supported by the current
version of MCS51 Studio. The simulator models digital behavior; it does not provide
complete cycle-accurate or electrical circuit simulation.

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
tests exercise assembly, Intel HEX round trips, interrupts, and every board
peripheral. Additional binary-reference fixtures cover 2,048 LED/display states,
150 ADC steps, and a 30,000-instruction LED-counter trace. Checks include all
switch patterns, keypad connections, DAC hold/scope behavior, comparator thresholds,
motor sensing, LCD bus/address handling, and 512 UART byte/parity combinations.
See [fixture notes](../tests/fixtures/README.md) for evidence and intentional differences. These detect unintended changes; they do not prove hardware
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
- Sub-instruction shared-pin timing, keypad modes, switch/key bounce, LCD busy timing and custom
  glyph rendering, and varied-clock UART framing need further work.
- The external UART uses 8 data bits without parity and 7 data bits plus odd/even
  parity. It does not model all framing errors or an arbitrary physical link.
- Broader assembler syntax remains planned.
- Guided lessons and exercise assessment are not implemented. Windows/Linux visual review remains pending.

See [architecture.md](architecture.md) for the development direction.
