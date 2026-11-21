---
title: Wiring and presets
description: Understand the virtual board, choose an experiment preset, and inspect or change pin mappings.
---

Each virtual peripheral connects to one or more port pins. An instruction affects a device only when the program and its wiring agree.

## Start with a preset

Open **Wiring** in the command row. Built-in presets use the default pin mappings and enable the devices needed for a particular experiment:

- **LED Counter:** LED bank.
- **Switch Input:** LEDs and switches.
- **Multiplexed Display:** four-digit display.
- **Keypad Scan:** keypad.
- **ADC Sampling:** ADC.
- **DAC Waveform:** DAC.
- **UART Link:** external UART.
- **Timer / PWM:** LEDs.
- **LCD Text:** LCD.
- **Motor Control:** motor.

Applying a preset pauses execution and clears captures. It does **not** replace the program in the editor. Open a matching example or adapt your source afterward.

## Read the wiring view

The view shows a labeled 40-pin MCU, enabled devices, and their connections.

1. Select a device to highlight its pins in mint.
2. Look for amber pins: multiple enabled devices share them.
3. Select a port pin to inspect all connected signals.
4. Read the shared-pin explanation before running.

Non-port package pins, including power and oscillator pins, are labels. They are not simulated controls.

## Default connections

These descriptions apply to the default mappings. Check Wiring when using a custom project.

- **LEDs and display segments:** P1.0–P1.7.
- **Switches:** P2.0–P2.7.
- **Display:** chip select P0.7; digit selection P3.3 and P3.4.
- **Keypad:** rows P0.0–P0.3; columns P0.4–P0.6; optional gate P3.3.
- **ADC:** data P2; read P3.7; write/start P3.6; completion P3.2.
- **DAC:** data P1; write P0.7.
- **Motor:** control P3.0 and P3.1; sensor P3.5.
- **Comparator:** output P3.7.
- **UART:** terminal transmit connects to MCU RXD/P3.0; terminal receive connects to MCU TXD/P3.1.
- **LCD:** data P1; RS P1.3; E P1.2. The default overlap requires the supported 4-bit sequence.

## Understand shared pins

Two output devices can observe the same writes. For example, the LED bank and display segments both use P1. An LED counter therefore produces segment patterns, not decimal digits, if the display is also enabled.

An input device can pull a shared line low, changing the value read by the MCU and by other connected devices. Release the MCU latch high before reading an input. Disable or remap unused hardware to isolate the experiment.

The explanations describe logical coupling. They do not model electrical contention, current, or damaged hardware.

## Change a mapping

Choose **Edit Pin Mappings**, select valid pins from `P0.0` through `P3.7`, and apply the changes. Update your program to use the new addresses. Moving a signal on screen does not rewrite source instructions.

For the LCD, remap control signals if you want an independent 8-bit bus. For UART, changing board connections does not move the processor's fixed RXD/TXD functions.

## Keep a useful setup

Use **Save As** in Wiring to save the current pin mappings, enabled devices, and keypad gate under a custom experiment name. Custom presets persist across sessions.

Use a [`.mcs51` project](../../workbench/projects/) when you also want to keep source, inputs, watches, and instrument settings with that setup.
