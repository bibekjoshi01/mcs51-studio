# Classic 8051 Processor

MCS51 Studio currently supports one processor profile: **Classic 8051**, with a
12 MHz oscillator and 12 clocks per machine cycle (1 µs). It has 128 bytes of
internal RAM, two timer/counters, five interrupt sources, and two priority levels.
There is one DPTR. The board supplies a 64 KB code address space and 64 KB of
external RAM. These are separate memories, not additional on-chip RAM.

8052 and AT89S52 are future profiles. Their upper internal RAM, Timer 2, and other
derivative features are not enabled by this profile.

## Memory And Stack

- Direct addresses 00–7FH select internal RAM; implemented addresses 80–FFH select
  SFRs. Register banks occupy 00–1FH; bit-addressable RAM occupies 20–2FH.
- Indirect `@R0`/`@R1` accesses and the stack select internal RAM only. They never
  select SFRs. SP resets to 07H, increments before PUSH, and decrements before
  the POP destination is written. Calls push the return PC low byte then high.
- `MOVC` reads code memory. All six `MOVX` encodings read/write external RAM.
  `@DPTR` uses a 16-bit address; `@Ri` uses the P2 latch as the high byte and the
  selected register as the low byte. MOVX releases the P0 latch to FFH and leaves
  the P2 latch unchanged. ALE/RD/WR bus waveforms are not rendered.
- Inspect or edit external memory under **Memory → XDATA**; enter a hexadecimal
  address and select **Go**. RAM shows only 00–7FH.

Undefined upper indirect RAM, unimplemented SFRs, and reserved opcode A5H stop
execution with an explanatory error. This is a teaching safeguard, not a claim
that physical silicon raises an exception. Reset clears simulated RAM/XDATA for
repeatable exercises; physical RAM power-on contents are not guaranteed.

## Flags, Timers, And Interrupts

ADD/ADDC/SUBB update CY, AC, and OV. MUL/DIV and decimal adjustment follow their
instruction-specific flag rules. Parity reflects ACC at each instruction boundary.
DIV by zero sets OV and clears CY; ACC/B are retained as a deterministic choice
for the undefined result. Mode 0 timer TL upper bits are ignored and preserved.

Timer modes 0, 1, and 2 implement 13-bit counting, 16-bit counting, and 8-bit
reload. Counter inputs count sampled falling edges; GATE and TR control counting.
In Timer 0 mode 3, TL0 uses its own controls while TH0 uses TR1/TF1 independently.
Timer 1 can continue as a baud generator without TF1; its own mode 3 halts it.
Only full Timer 1 overflows clock serial modes 1 and 3.

Interrupt polling uses the preceding machine-cycle sample at instruction
boundaries. EA, individual enables, priority, and in-service nesting determine
acceptance. Equal-priority requests use INT0, Timer 0, INT1, Timer 1, serial order.
RETI releases the active priority; RET does not. RETI and IE/IP accesses allow one
following instruction before another interrupt can be accepted. Hardware entry
pushes PC, preserves PSW, and costs two machine cycles during which timers run.
Timer and edge-triggered external flags clear on acceptance; RI/TI require software
clearing. Level-triggered external flags follow sampled pins.

## Validation And Resolution

`tests/test_classic_8051.py` checks all ADD/ADDC/SUBB operand combinations and
carry inputs, all MUL/DIV operands, valid BCD sums, addressing, stack limits,
MOVX assembly/execution, instruction durations, timer periods/gates/counters/split
operation, and interrupt masking/order/nesting/return behavior. Desktop tests
exercise XDATA display and processor errors through the editor/debugger.

Instructions commit at machine-cycle boundaries. Pin transitions within a cycle,
S-state/P-phase timing, electrical behavior, and contention on the external bus
are outside this model. Virtual board devices update after each instruction;
these tests do not certify silicon-level timing or complete UART fidelity.

## References

- [Atmel 8051 Instruction Set](https://www.keil.com/dd/docs/datashts/atmel/at_c51ism.pdf):
  instruction definitions, flags, stack ordering, and classic cycle counts.
- [Atmel 8051 Hardware Manual](https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/UserGuides/doc4316.pdf):
  addressing and read-modify-write rules; Sections 2.10–2.11 timers and 2.16 interrupts.
  Derivative extensions and X2 timing in this family manual do not apply here.
- [AT89S52 Datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/doc1919.pdf):
  documents the additional RAM and third timer that require a separate profile.
