---
title: Logic Analyzer and DAC Scope
description: Capture digital transitions, measure pulses, and inspect analogue output over simulated time.
---

Instruments help you inspect changes that are too fast or repetitive to follow on the board. Their time axes use **simulated microseconds**, independently of Batch or playback speed.

## Capture digital signals

1. Open **Instruments → Logic Analyzer**.
2. Enter **1–8 port pins**, separated by commas, such as `P1.0,P1.1`.
3. Choose **Apply**.
4. Select **Free Run**, or choose a trigger pin and Rising, Falling, or Either edge.
5. For triggered capture, choose a post-trigger duration.
6. Select **Arm**, then run or step your program.

Arm assembles first if necessary. **Stop Capture** stops recording without stopping the processor. Reset clears the capture.

Try the [timer toggle example](../../examples/#wait-for-a-timer) with P1.0 as a probe and a falling-edge trigger.

## Inspect a capture

Use **Fit**, **Zoom In**, **Zoom Out**, and **History** to choose the visible time range. Select a lane for its measurements.

- Complete observed pulses provide high/low width.
- Complete rising-edge cycles provide period, frequency, and duty cycle.
- A dash means there are not enough edges in the visible range.

Click once to place cursor A, then again to place B. The cursor readout provides Δt and its reciprocal. The reciprocal is a signal frequency only when your cursors are exactly one full period apart.

## Understand capture resolution

The analyzer records effective pin levels after each instruction. Capture is independent of UI batch size and retains up to **8,192 transition samples**, with bounded pre-trigger history. A full buffer stops recording explicitly.

These are instruction-boundary observations. They do not reveal sub-instruction transitions, electrical rise times, or MOVX external-bus waveforms.

## View DAC output

1. Apply **DAC Waveform** in Wiring or enable DAC in Hardware.
2. Run a program that changes its output.
3. Open **Instruments → DAC Scope**.
4. Inspect the stepped waveform on a 0–5 V scale.

Use zoom and history to navigate. **Freeze** holds a snapshot while the processor keeps running. **Live** resumes updates. Click twice for A/B cursors showing time, voltage, Δt, and ΔV.

The scope retains the latest **600 samples**. Freeze when you see the portion you want to study.

## If the capture is empty

- Confirm the device is enabled and mapped to the pins your program writes.
- Confirm you pressed Arm before generating the event.
- Start with Free Run to check that capture works, then add a trigger.
- Make sure the trigger edge actually occurs after arming.
- Run or step the CPU; time does not progress merely because the window is open.

For unexpected levels, inspect [shared-pin connections](../wiring/#understand-shared-pins).
