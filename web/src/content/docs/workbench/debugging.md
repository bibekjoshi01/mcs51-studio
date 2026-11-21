---
title: Stepping and debugging
description: Follow instructions, use breakpoints and watches, and understand calls, returns, and program termination.
---

Debugging means stopping at useful points and inspecting what your program actually did. Assemble with **F6**, then start with **F7** and the processor inspector.

## Choose an execution control

- **Step (F7):** execute one instruction, including entering a subroutine call.
- **Run / Pause (F5):** execute continuously or stop continuous execution.
- **Step Over (F8):** run a call until it returns. For an ordinary instruction, execute it once.
- **Step Out (Shift+F8):** return from the current tracked call or interrupt.
- **Run To Cursor (F9):** stop before the assembled instruction on the cursor's source line.
- **Reset (Shift+F5):** restore the initial machine state and reload the program.

Step Out needs a call or interrupt frame observed since Reset. It is unavailable at the top level. Blank lines and `DB` data are not Run To Cursor targets.

Temporary runs respect ordinary and change breakpoints. Pause, source edits, or Reset cancels them. A target that is never reached stops after one million instructions.

## Set a breakpoint

1. Assemble the program.
2. Click an editor line number beside an instruction, or double-click its Listing row.
3. Check that a pink dot appears.
4. Run with F5. Execution pauses before that instruction.

Click again to remove the breakpoint. Listing also accepts a hexadecimal breakpoint address and offers **Clear All Breakpoints**. A breakpoint at the initial PC stops before the first instruction; Run resumes from it and Reset makes it stop there again.

The mint arrow marks what runs **next**. It does not mark an instruction that has already completed.

## Explain the last instruction

Open **Debug → Last Instruction**. It shows the executed address and bytes, observed input values, register results, memory changes, and flags before and after the instruction.

Timing includes the instruction cost and any interrupt-entry cost. Timer and peripheral changes during the instruction are included in its result. All costs are simulated time, independent of screen playback.

## Watch a value

In **Debug → Watches**, add an explicit location such as:

- `ACC`, `R0`, `DPTR`, or `CY`.
- `RAM[30]` for indirect internal RAM address 30H.
- `SFR[90]` for the P1 latch.
- `BIT[90]` for the resolved P1.0 pin level.
- `XDATA[1234]` or `CODE[0100]` for another memory space.

Addresses inside brackets are **hexadecimal**. These are locations, not expressions: `ACC + 1` is not a supported watch. Up to 64 watches are available.

Enable **Break On Change**, or double-click a watch to toggle it. The debugger compares its value before and after a complete instruction, including timer and peripheral updates. Writing the same value does not stop execution.

## Inspect calls and the stack

**Stack** shows raw internal RAM below SP alongside tracked calls and interrupts. Tracked frames come from observed execution; the debugger does not reconstruct arbitrary frames from RAM.

A mismatched return stops execution with an explanation. Check PUSH/POP balance, SP, and whether an interrupt handler uses `RETI` instead of `RET`. Editing registers or memory clears tracked frames; it leaves watches intact.

## Understand a stop

**Program terminated** means the next PC points to an unloaded address. Final state remains available, and pressing Run or Step again retains that result. Use Reset to restart.

An explicit loop keeps executing. `END` ends assembly, not a running loop. Execution history and reverse stepping are not currently available.

Try the [registers and memory example](../../examples/#registers-and-memory), which provides simple values to inspect.
