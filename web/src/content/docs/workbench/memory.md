---
title: Registers and memory
description: Inspect and edit registers, internal RAM, SFRs, program memory, and external RAM.
---

The processor inspector is useful for a few registers. The **Memory** tab is useful when you need a range of addresses. Pause the program before editing values.

## Edit a register

1. Find the register in the Processor Inspector.
2. Enter a hexadecimal value.
3. Press **Enter** to apply it.

Hover over the register label for its SFR address. Flag tiles show individual PSW bits and the active register bank. The Bitfield section accepts an SFR name or hexadecimal RAM address; click a bit when the byte is bit-addressable.

## Internal RAM

Select **RAM** to inspect addresses **00–7FH**. Double-click a byte to edit it.

- `00–1FH`: four banks of eight working registers.
- `20–2FH`: bit-addressable RAM.
- `30–7FH`: other internal RAM locations, also available for the stack.

The stack is in internal RAM. SP resets to `07H`, so the first pushed byte uses `08H`. Plan stack placement when using multiple register banks or larger programs.

## Special function registers

Select **SFR** for implemented registers at addresses **80–FFH**, such as ports, timer controls, PSW, ACC, and B.

Direct addressing above `7FH` selects SFRs. Indirect `@R0` / `@R1` addressing selects internal RAM only. On this Classic 8051 profile, an indirect access to upper internal RAM stops with an error; it does not reach the SFR at the same numeric address.

## Code memory

Select **Code** to inspect program bytes. Enter a hexadecimal address and press Enter to navigate.

Code has a 64 KB address space, but only loaded bytes belong to your current program. `MOVC` reads code memory. Execution into an unloaded address terminates the program.

Editing code bytes changes the machine image and marks Listing as modified. It does not rewrite the assembly source. Export HEX to keep the edited image; Reset or Assemble restores the original assembled bytes.

## External RAM: XDATA

Select **XDATA**, enter a hexadecimal address, and choose **Go**. The board provides a separate **64 KB** external-data address space. Double-click a byte to edit it while paused.

Use `MOVX` to access it:

```asm
        MOV DPTR,#1234H
        MOV A,#42H
        MOVX @DPTR,A
        CLR A
        MOVX A,@DPTR
```

After executing these instructions, XDATA address `1234H` and A both contain `42H`. For `MOVX @R0` / `@R1`, P2 supplies the high address byte. `MOVX` releases the P0 latch to `FFH`; external-bus waveforms are not drawn.

## Latches and effective pins

A port's stored latch can be high while a connected switch holds the effective pin low. The board displays both. Register and SFR watches show the latch; `BIT` watches on ports show resolved pins.

This distinction is useful when reading switches, scanning a keypad, or investigating shared connections. Read [Wiring and presets](../../peripherals/wiring/) before changing mappings.

## What Reset clears

Reset clears simulated internal and external RAM for repeatable exercises. This is a simulator convention; it is not a promise about physical hardware power-on contents. [Projects](../projects/) save the experiment configuration, not the current memory contents.
