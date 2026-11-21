---
title: Features and limits
description: What the current simulator supports, what it simplifies, and what is not yet available.
---

MCS51 Studio models digital processor and peripheral behavior for learning. Use this page to decide whether an experiment fits the current implementation.

## Available now

- Assembly editor with completion, find/replace, diagnostics, and a two-pass assembler.
- Intel HEX import/export and source listings.
- Classic 8051 execution, registers, flags, breakpoints, timers, interrupts, and serial.
- 128-byte internal RAM and separate 64 KB code/XDATA spaces.
- Step Over/Out, Run To Cursor, explicit watches, change breakpoints, and tracked call frames.
- LEDs, switches, keypad, multiplexed display, LCD, ADC, DAC, comparator, motor, and UART.
- Editable wiring, shared-pin explanations, and saved experiment presets.
- Logic Analyzer with triggers and measurements; DAC Scope with cursors.
- Portable `.mcs51` projects and autosave recovery.
- Deterministic switch/keypad bounce, interrupt input pulses, LCD timing/custom glyphs, and UART diagnostics.

## Processor and timing limits

Only the Classic 8051 at 12 MHz and 12 clocks per machine cycle is supported. There is no Timer 2 or upper internal RAM.

Board devices and captures observe instruction boundaries. The simulator does not provide full electrical or sub-instruction timing, arbitrary oscillator clocks, external-bus waveforms, or analogue contact physics.

Batch and Show Transitions control playback. They do not alter cycle counts.

## Peripheral simplifications

- **Keypad bounce:** 30 ms deterministic pattern in Standard mode only.
- **Switch bounce:** repeatable pattern over the chosen simulated duration.
- **LCD:** eight custom glyphs and selected ROM substitutions; the complete ROM is not provided. R/W is grounded, so there is no readable busy flag.
- **UART:** external framing is sampled on a 1 µs grid; it is not a complete arbitrary electrical link.
- **Displays:** instantaneous output state, without a hidden persistence effect.
- **Motor and analogue devices:** teaching models rather than physical circuit simulations.

## Debugger and project limits

Change breakpoints compare values around a complete instruction. Tracked frames come from observed execution and are cleared after manual state edits. Reverse stepping and execution history are not available.

Projects preserve configuration and source, not live RAM, in-flight serial traffic, or captures. The application does not include guided lesson execution or exercise assessment.

## Retention bounds

- Logic Analyzer: up to 8,192 transition samples.
- DAC Scope: latest 600 samples.
- UART receive history: up to 65,536 bytes, evicted in 1,024-byte blocks.
- UART visible transcript: 131,072 characters.
- Internal transmit trace: up to 8,192 bytes.
- Activity: approximately 1,000 lines.
- Watches: up to 64 explicit locations.

These bounds keep long sessions from growing memory indefinitely.

## Validation status

The repository includes processor specification tests, historical regression fixtures, program-level checks, and desktop smoke tests. Historical instruction fixtures cover 6,836 compatible cases; separate specification tests cover arithmetic, addressing, timer, interrupt, and timing behavior.

Native Windows/Linux installer and GUI checks are configured in CI. The repository documentation still records complete native visual review as pending; this website does not claim that review is complete.

See the maintained [compatibility guide](https://github.com/bibekjoshi01/mcs51-studio/blob/main/docs/compatibility.md) for implementation and validation details.
