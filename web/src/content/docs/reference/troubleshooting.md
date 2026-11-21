---
title: Troubleshooting
description: Resolve common assembly, execution, board, timing, and recovery problems.
---

Start by pausing the simulation. Read **Activity** and the current stop reason, then check the source and board setup before changing several things at once.

## The program will not assemble

Read the error in Activity and find the marked source line. Check instruction spelling, operand forms, undefined labels, and numeric ranges. Hexadecimal values beginning with A–F need a leading zero: `0FFH`.

Examples from another assembler may use unsupported directives or macros. Compare them with [Assembly syntax](../assembly/). A failed assembly blocks execution of old code until the current source assembles successfully.

## F5 or F7 seems to do nothing

Check whether the source is empty, assembly failed, or the program has terminated. Use F6 to assemble and Reset to restart a terminated program. Your keyboard may require **Fn+F5/F7**; try the visible buttons.

If a breakpoint is set at the initial PC, the first Run stops before that instruction. Run again to continue.

## Program terminated appears

The next address has no loaded code or data. This is normal at the end of a straight-line program. Final state remains available for inspection.

Use Reset to start again. If the stop is unexpected, inspect the last jump/return, SP, and loaded code regions. `END` ends assembly; use an explicit loop when you want the program to keep running.

## The wrong LED lights, or the display changes too

LEDs are active-low. Zero lights a device. Check P1 and the board's lit-bit readout separately.

The LEDs and display share P1 by default. Apply the **LED Counter** preset, or disable/remap unused hardware in Wiring. The LED counter produces segment patterns if the display is also enabled.

## A pin always reads low

Release the MCU's port latch high before reading an external input. Inspect both latch and effective-pin values. Open Wiring, select the pin, and check for another enabled device driving it low.

## The program runs too quickly to watch

Keep **Show Transitions** enabled. Use Step, breakpoints, or the Logic Analyzer for precise observations. Lowering Batch may make interface updates more frequent, but it does not change simulated instruction timing.

## LCD characters are missing

Check the 4-bit initialization sequence and high/low nibble order for the default overlapping wiring. Inspect the ignored-write count and wait long enough after commands: Clear/Home require 1,520 µs, other completed writes 37 µs when timing is enabled. R/W is grounded; do not wait for a readable busy flag.

## UART output is missing or corrupted

Match baud, data bits, parity, and stop bits with the MCU configuration. Check Timer 1, TR1, SCON, SMOD, and TI/RI handling. Disable the motor on shared pins. Use Reset Link after an active framing change, then inspect diagnostic counts.

## A panel disappeared

Choose **View → Reset Layout**. You can also toggle Inspector and Bottom from the status bar or use Focus Editor to restore supporting panels.

## Step Out is unavailable

The debugger needs a tracked call or interrupt observed since Reset. It is unavailable at the top level. Manual register or memory edits clear tracked frames. A mismatched return should be investigated through SP, PUSH/POP balance, and RET/RETI.

## My latest work is missing

Check **File → Recover Autosave** if the startup message reports recovery data. Save the recovered experiment as a project. Autosave runs every 15 seconds for changed experiments; it is separate from your explicit saved file.

## I still need help

Open an issue in the [official issue tracker](https://github.com/bibekjoshi01/mcs51-studio/issues). Include your operating system, app version, a minimal source example, steps to reproduce, expected result, and the actual Activity/stop message. Include the `.mcs51` experiment when its wiring matters, after checking that it contains only material you intend to share.
