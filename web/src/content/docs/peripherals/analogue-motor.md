---
title: ADC, DAC, and motor
description: Explore analogue input/output, comparator behavior, and the virtual motor.
---

The board provides simplified devices for studying digital control of analogue values and motion. All timing comes from the simulated processor.

## Analogue-to-digital converter

Apply **ADC Sampling**. The analogue slider supplies a value between 0 and 5 V. The ADC turns it into an unsigned eight-bit sample between 0 and 255.

Default signals are data on P2, RD on P3.7, WR on P3.6, and INTR on P3.2.

1. Release P2 high so the ADC can drive the data pins.
2. Pulse WR low then high to start a conversion.
3. Execute instructions while the conversion progresses.
4. Wait for INTR to go low, indicating completion.
5. Drive RD low and read P2.
6. Return RD high when finished reading.

The model takes **20 simulated microseconds** to convert. At about 2.5 V, the completed sample is approximately 128 (`80H`). Disable switches or other drivers on P2 during the experiment; the ADC preset does this for you.

INTR shares the default INT0 pin. Poll it for a first exercise, then configure interrupts when you want to study interrupt-driven sampling.

## Digital-to-analogue converter

Apply **DAC Waveform**. P1 supplies the byte and P0.7 is the active-low write signal.

While P0.7 is low, writes to P1 update the DAC value. The output scale is `byte × 5 / 255` volts: `00H` gives 0 V and `FFH` gives 5 V.

Open **Instruments → DAC Scope** to see output against simulated time. Try the [DAC ramp example](../../examples/#make-a-dac-ramp), then freeze the scope and place measurement cursors.

## Comparator

The comparator compares the analogue input with the retained DAC output value. Its default output is P3.7. It pulls that output low when the analogue input is less than or equal to the DAC voltage.

Set a known DAC threshold before testing. The **ADC takes precedence**: the comparator is inactive whenever ADC is enabled, even if the signals have been remapped. Disable ADC to use the comparator.

## Motor

Apply **Motor Control**. By default, P3.0 and P3.1 control direction, and P3.5 provides the position sensor.

- Equal control levels stop the motor.
- Different levels choose opposite directions.
- The sensor goes low at the model's reference position.

Use the motor card's speed slider or the percentage in Experiment Settings. The supported range is 1–100%. Motion advances with simulated time; it is not tied to how often the window redraws.

The motor shares its default control pins with serial RXD/TXD. Use the motor preset or disable UART while investigating it.

## What these models do not show

The board does not simulate currents, electrical noise, motor load/torque, or full analogue circuitry. Devices update at instruction boundaries. Use the model to understand program behavior, and consult real component specifications before transferring a design to hardware.
