# Supported Features And Simulation Limits

This guide defines the processor and peripheral behavior supported by the current
version of MCS51 Studio. The simulator models digital behavior; it does not provide
complete cycle-accurate or electrical circuit simulation.

## Available Now

- Assembly editor, two-pass assembler, source listing, and Intel HEX import/export.
- Classic 12-clock 8051 stepping, breakpoints, registers, internal RAM, and interrupts.
- MOVX with 64 KB external RAM and an editable XDATA memory view.
- Timer and on-chip serial models.
- Configurable virtual board: LEDs, switches, keypad, seven-segment displays,
  character LCD, ADC/DAC, motor, comparator, and external UART.
- Wiring diagrams, shared-pin explanations, and persistent experiment presets.
- Instruction-boundary digital capture with edge triggers and measurements; DAC cursors.
- Native installer build targets for Windows, Linux, and macOS.

## Validation

The [Classic 8051 profile](processor.md) defines CPU behavior and independent
specification tests. Historical fixtures still check 6,836 compatible instruction cases,
192 serial cases, and 260 assembly inputs. Old timer expectations are retained as
evidence but no longer used as a hardware oracle: specification tests replace them.
Binary-reference board fixtures cover 2,048 LED/display states, 150 ADC steps,
and a 30,000-instruction LED-counter trace. Integration checks cover all virtual
peripherals. See [fixture notes](../tests/fixtures/README.md) for intentional changes.

GUI smoke tests assemble the bundled example, step and run it, and save settings.
Windows/Linux native installer and GUI validation is configured in CI; successful
runs on those systems and a complete visual review remain pending.

## Known Limits

- The simulated machine cycle is fixed at one microsecond; oscillator selection
  is not exposed in the interface.
- Sub-instruction shared-pin timing, keypad modes, switch/key bounce, LCD busy timing and custom
  glyph rendering, and varied-clock UART framing need further work.
- The external UART uses 8 data bits without parity and 7 data bits plus odd/even
  parity. It does not model all framing errors or an arbitrary physical link.
- Broader assembler syntax remains planned.
- Guided lessons and exercise assessment are not implemented. Windows/Linux visual review remains pending.

See [architecture.md](architecture.md) for the development direction.
