---
title: UART communication
description: Match the MCU serial configuration to the virtual terminal and diagnose framing errors.
---

UART sends bytes as timed serial bits. MCS51 Studio provides the processor's on-chip serial model and an external UART terminal on the virtual board.

## Connect the terminal

Apply **UART Link** in Wiring. With the default mapping:

- Terminal TX drives **P3.0 / RXD**, the MCU receive pin.
- Terminal RX reads **P3.1 / TXD**, the MCU transmit pin.

The directions are from the terminal's point of view. Disable the motor, which shares these default pins.

## Match the configuration

The MCU's SCON register selects its serial mode. In asynchronous modes, the MCU's baud generator must agree with the external terminal's baud rate. The terminal controls support 7/8 data bits, None/Odd/Even parity, and 1/2 stop bits.

1. Configure the serial mode and Timer 1 baud generator in your program.
2. Select compatible terminal framing and baud.
3. Choose **Apply Framing**.
4. Assemble and run the program.
5. Send text or valid hexadecimal byte values from the terminal, or write SBUF from the MCU.

Available terminal framing choices do not mean every processor serial mode can receive every combination. Match the on-chip mode and any parity handling in your program.

The [UART transmit example](../../examples/#send-one-uart-character) uses MCU mode 1, Timer 1 mode 2, SMOD = 0, and reload `0F3H`. At the fixed 12 MHz clock, this is approximately **2404 baud**; set the terminal to **2400, 8 data bits, no parity, 1 stop bit**.

## Watch transmit and receive flags

Writing SBUF begins transmission. TI indicates transmit completion; RI indicates reception. Clear the relevant flag in software before waiting for the next event.

The UART transcript scrolls vertically and horizontally. **Clear Output** clears the visible view without erasing the underlying received simulation data.

## Change an active link

An active framing change requires **Reset Link**. It discards queued and in-flight data, while retaining the transcript and diagnostic counts. **Reset Machine** clears those as well.

Invalid hex lists or values outside the selected data width are rejected before any part of the list is sent. For seven-bit framing, values must fit in seven bits.

## Read diagnostics

The terminal counts short start pulses, parity mismatches, and low stop bits. Invalid frames are discarded.

If text is missing or corrupted:

1. Check SCON, Timer 1 mode, reload, TR1, and SMOD.
2. Match baud and framing at both ends.
3. Check that the correct device is enabled and the motor is disabled.
4. Reset the link after a configuration change.
5. Inspect RXD/TXD with the Logic Analyzer if you need to see the transitions.

## Timing and retention limits

External bit periods are rounded on a fixed **1 µs** sampling grid. This is a digital teaching model, not an arbitrary physical link.

Received history keeps up to 65,536 bytes, evicting in 1,024-byte blocks. The visible transcript keeps 131,072 characters and the internal transmit trace keeps up to 8,192 bytes. Save any results you need before a long experiment overwrites older output.
