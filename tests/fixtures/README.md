# Regression fixtures

The instruction, timer, serial, and assembly fixtures were rechecked against the
installed reference JAR on 2026-10-26. Its SHA-256 is
`36d9fde20620db862358a842ed1174d1a7fc389558e453b3eddfbd406a9ef42d`.
REA identified the container; Java probes executed the original bytecode.
The Python application does not load that binary.

- `board-outputs`: all 256 port patterns × 2 chip-select states × 4 digits.
- `board-adc`: six input levels through conversion, readout, restart, and disable.
- `led-counter-trace`: instruction number, machine cycles, and illuminated LED mask
  at each output change in the bundled program's first 30,000 instructions.

The board probes supply controlled pin levels and stub UI notifications. They
validate device logic, not the original Swing UI or complete shared-pin timing.
Additional behavioral tests cover switches, keypad, DAC, comparator, motor, LCD,
and UART. Those are contract checks, not exhaustive binary equivalence claims.

Intentional corrections: disabling ADC releases its data pins instead of retaining
an old bus drive; queued UART sends append, and parity is calculated over seven
payload bits. LCD address wrapping and CGRAM exit are tested separately. CPL and
JBC use port latches for read-modify-write, as specified by the
[8051 hardware manual](https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/UserGuides/doc4316.pdf).

Matching sampled reference states is not proof of hardware accuracy. See
[known limits](../../docs/compatibility.md), including MOVX and timer/flag gaps.
