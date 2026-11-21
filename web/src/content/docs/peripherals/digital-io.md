---
title: LEDs and switches
description: Control active-low LEDs, read switch inputs, and understand latch versus pin values.
---

LEDs make output values visible. Switches provide simple input values that your program can read.

## Turn on an LED

Apply the **LED Counter** preset in Wiring. The LED bank uses P1 by default.

```asm
        ORG 0000H
        MOV P1,#0FFH
        CLR P1.0
hold:   SJMP hold
        END
```

Assemble and step twice. P1 changes from `FF` to `FE`, lighting LED 0.

The LEDs are **active-low**: 0 lights a device, 1 turns it off. The board's lit-bit readout reverses that viewpoint: a 1 means a lit LED. LED 0 contributes 1, LED 1 contributes 2, LED 2 contributes 4, and so on.

## Read the switch bank

Apply the **Switch Input** preset. Switches use P2 and LEDs use P1.

```asm
        ORG 0000H
        MOV P2,#0FFH   ; Release input latches high
again:  MOV A,P2       ; Read effective input levels
        MOV P1,A      ; Show the same levels on LEDs
        SJMP again
        END
```

Run and change switch 0 on the board. When the switch reads 0, LED 0 lights. When it reads 1, LED 0 turns off. Try combinations and inspect A or the P2 pin readout.

Switches show their bit number and current 0/1 level. Use the displayed level instead of assuming that a visual position means high or low.

## Why release inputs high?

A connected input can pull a pin low. If your program also writes zero into its port latch, the pin stays low even when the input is released. Writing ones lets the external input determine the effective level.

The board shows **port latch** and **effective pin** values in binary and hexadecimal. Register/SFR watches show the latch; a port `BIT` watch shows the resolved pin. This explains why a switch can change a pin without changing the stored latch.

## Experiment with bounce

Open **Tools → Experiment Settings** or **Virtual Board → Hardware**. Enable switch bounce and choose a duration.

The simulator uses a repeatable ten-phase contact pattern, then settles at the desired level. It advances only as simulated time advances. Changing a switch while paused does not play the whole bounce sequence in wall-clock time.

Capture the input with the [Logic Analyzer](../instruments/) to study the transitions. This is a teaching model, not an analogue model of a mechanical contact.

## Troubleshooting

- **An LED is inverted:** active-low output is expected. Check the port value and lit-bit readout separately.
- **The display changes too:** LEDs and display segments share P1. Apply the LED preset or disable unused hardware.
- **A switch always reads low:** release its latch high and inspect shared-pin warnings.
- **Changes are hard to see:** keep Show Transitions enabled, or pause and step.

Continue with [Displays and keypad](../displays-keypad/) or download the [switch mirror example](../../examples/#read-switches).
