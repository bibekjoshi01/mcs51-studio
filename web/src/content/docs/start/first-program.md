---
title: Your first program
description: Assemble a small LED program, step through each instruction, and understand exactly what changes.
---

**Goal:** turn on one LED and understand how a line of assembly changes the board.

**Before you start:** [install MCS51 Studio](../installation/). No physical hardware is needed.

## 1. Prepare the experiment

1. Open MCS51 Studio. The editor initially contains an LED counter.
2. Choose **File → New**. Save the existing source if you want to keep changes.
3. Open **Wiring** and apply the **LED Counter** preset. This enables the LED bank with its default pin mappings.
4. Return to the editor tab.

Using a preset makes the wiring predictable. The LED bank is connected to Port 1: LED 0 uses `P1.0`, LED 1 uses `P1.1`, and so on.

## 2. Enter a small program

Paste this complete program into the editor:

```asm title="first-led.asm"
        ORG 0000H
        MOV P1,#0FFH   ; All LEDs off
        CLR P1.0       ; Turn LED 0 on
hold:   SJMP hold      ; Stay here
        END
```

Choose **Save** and name the file `first-led.asm`.

The text after `;` is a comment. It explains the program but does not become an instruction. `ORG` sets where code is assembled. `END` ends the assembly source.

:::note[Why does zero turn a light on?]
The LEDs are **active-low**. A pin value of `0` lights an LED; `1` turns it off. `0FFH` is eight binary ones, so writing it to P1 turns all eight LEDs off.
:::

## 3. Assemble

Press **F6** or select **Assemble**. The assembler converts the source into bytes the simulated processor can execute.

You should see a successful assembly message. The processor inspector shows the next instruction, and **Listing** shows addresses and bytes. If assembly fails, the marked source line and **Activity** explain the error. Correct it and assemble again.

`ORG` and `END` do not execute. The first instruction to execute is `MOV P1,#0FFH`.

## 4. Step and observe

1. Press **F7** once. `MOV P1,#0FFH` executes. P1 is `FF` in the inspector and all LEDs are off.
2. Press **F7** again. `CLR P1.0` executes. P1 becomes `FE` and LED 0 lights.
3. Open **Virtual Board** to inspect the LED bank. Its lit-bit readout is **1**, because LED 0 represents the value 1.
4. Press **F7** again. `SJMP hold` jumps back to itself. The LED stays on.

The highlighted source line marks the **next** instruction. Open **Debug → Last Instruction** to see what just executed, including register and memory changes.

:::tip[Keep two values separate]
P1 contains `FE` (254), while the LED readout shows 1. The port reports electrical logic levels; the LED readout reports which active-low LEDs are lit.
:::

## 5. Run, pause, and reset

- Press **F5** to run. This example loops indefinitely at `hold`.
- Press **F5** again to pause.
- Press **Shift+F5** or choose **Reset** to restore the initial machine state and start from the beginning.

`END` does not stop a running loop. A program stops with **Program terminated** when its next address contains no loaded code or data. Our explicit loop always jumps to a loaded instruction.

## 6. Make a small change

Change `CLR P1.0` to `CLR P1.1`, assemble with **F6**, and step twice. LED 1 should light and the LED readout should show **2**.

Try adding both `CLR` instructions. What readout do you expect? With LEDs 0 and 1 lit, it should show **3**.

Editing pauses execution. Assemble again after every source change; saving a file does not assemble it.

## Keep learning

Read [8051 essentials](../8051-basics/) for registers, ports, and number notation. Then try the [LED counter and other examples](../../examples/), or learn how to stop at a specific instruction in [Stepping and debugging](../../workbench/debugging/).
