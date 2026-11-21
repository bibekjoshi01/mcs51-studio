---
title: 8051 essentials
description: A beginner's guide to instructions, registers, ports, hexadecimal numbers, and simulated time.
---

An 8051 is a small processor commonly studied in embedded-systems courses. A program is a sequence of instructions that moves data, performs calculations, tests conditions, and controls pins.

## Bits, bytes, and numbers

A **bit** holds 0 or 1. A **byte** contains eight bits and can represent an unsigned value from 0 to 255.

Assembly often uses hexadecimal, or base 16. The digits are `0–9` and `A–F`. In source, an `H` suffix marks a hexadecimal number: `10H` means 16 in decimal, while `10` means ten. Add a leading zero if the first digit is a letter: write `0FFH` for 255.

Binary uses a `B` suffix: `00000001B` means 1. The inspector displays register values in hexadecimal.

## Registers hold working values

- **A / ACC:** the accumulator, used for many calculations and data transfers.
- **R0–R7:** eight working registers in the active register bank.
- **PC:** the program counter, which points to the next instruction.
- **DPTR:** a 16-bit data pointer, made from DPH and DPL.
- **SP:** the stack pointer, used by calls, returns, PUSH, and POP.
- **PSW:** status flags and register-bank selection bits.

The inspector shows these values. Mint highlights indicate a change during the last instruction.

## Read a line of assembly

```asm
        MOV A,#5
        ADD A,#3
        MOV 30H,A
```

`MOV` copies a value. `#5` is an **immediate** value: the number five itself. After the first instruction, A is 5. `ADD` makes it 8. The final instruction stores 8 at internal RAM address `30H`.

The `#` matters: `MOV A,#30H` loads the number 48, while `MOV A,30H` reads the byte at RAM address `30H`.

## Ports connect to the board

P0, P1, P2, and P3 are eight-bit ports. `P1.0` means bit 0 of Port 1. An instruction can change a complete port or one bit:

```asm
        MOV P1,#0FFH
        CLR P1.0
```

Which device reacts depends on the current [wiring](../../peripherals/wiring/). A port's stored **latch** value can differ from its effective pin value when a connected input device pulls the line low. Release a port bit high before reading an external input.

## Labels and loops

A label names a location. A jump changes where execution continues:

```asm
        MOV R0,#3
again:  DJNZ R0,again
```

`DJNZ` decrements R0 and jumps if the result is nonzero. Here the instruction executes three times, ending with R0 equal to zero.

Use labels for jump destinations. They remain understandable when other instructions move.

## Memory is split into spaces

Internal RAM holds working data. Special function registers (**SFRs**) control the processor and ports. **Code** holds the program. **XDATA** is separate external RAM, accessed with `MOVX`.

An address has meaning within a memory space. Code address `0030H` and RAM address `30H` are separate locations. The [memory guide](../../workbench/memory/) explains how to inspect each space.

## Simulated time and playback

At the supported 12 MHz, 12-clock profile, one machine cycle is **1 µs**. Instructions take different numbers of cycles. The inspector and debugger report those simulated costs.

**Batch** sets the amount of execution work per interface update. **Show Transitions** makes board changes easier to see. These settings affect playback on your computer; they do not change instruction order or the processor's simulated cycle counts.

Continue with the [workbench tour](../../workbench/interface/) or try the [memory example](../../examples/#registers-and-memory).
