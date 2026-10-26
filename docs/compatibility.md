# Compatibility

MCS51 Studio is an independent Python desktop reconstruction informed by
EdSim51DI 2.1.39 and EdSim51SH 1.2.32. It is not an official EdSim51 release.

## Verified scope

Preserved fixtures from the original Java application compare:

- All 256 opcode values over 8,192 sampled states, including PC and all memory bytes.
- Timer behavior over 1,024 cases.
- Serial behavior over 192 cases across serial modes and SMOD settings.
- The full code-memory digest for 260 assembly inputs.

Integration tests exercise the example program, Intel HEX round trips, invalid
programs, ADC, switches, LCD commands, and interrupt/RETI behavior.
Finite fixtures do not establish complete equivalence.

## Remaining work

- Differential tests for shared pins and peripheral timing.
- Switch/key bounce and additional keypad modes.
- LCD busy timing and custom glyph rendering.
- External UART framing over varied clocks.
- Broader assembler syntax and diagnostics compatibility.
- Original wiring-editor and floating-panel features.
- Import of legacy Java serialized settings.
- Full oscillator settings in the interface.
- Windows/Linux GUI validation and complete visual review.

The current simulated machine cycle is one microsecond. MOVX and the reserved
A5 opcode preserve the original simulator's no-op behavior. Some additional DB
syntax is accepted by Python that the reference application rejects.

## Provenance

REA 6.8.0 provided artifact inventory. CFR 0.152 and javap were used to inspect
the original Java application. The Python code and tests were developed from
that investigation; REA did not automatically generate or validate the app.
The recovered Java source, original binaries, and historical build outputs are
kept outside this Python repository.
