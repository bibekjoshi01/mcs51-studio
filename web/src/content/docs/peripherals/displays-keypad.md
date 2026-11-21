---
title: Displays and keypad
description: Use the multiplexed display, scan a keypad, and understand LCD wiring and timing.
---

These peripherals turn port writes and reads into more structured interactions. Start with one device enabled so shared pins do not distract from the experiment.

## Four-digit seven-segment display

Apply **Multiplexed Display** in Wiring. By default, P1 carries the eight active-low segment bits, P0.7 enables the display when high, and P3.3/P3.4 select a digit.

To display a pattern:

1. Set the two digit-select bits.
2. Write the segment pattern to P1.
3. Keep P0.7 high to enable the display.
4. Change selection and pattern to multiplex between digits.

The digit selection is `P3.3 + 2 × P3.4`. A simple check is to set both selection bits low and write `00H` to P1: all segments of the selected digit should light.

The display shows the **instantaneous** selected state. There is no hidden persistence effect combining multiple digit writes. Show Transitions changes playback visibility, not the simulated display state.

LED programs write raw bit patterns. They do not automatically encode decimal digits for the display.

## Matrix keypad

Apply **Keypad Scan**. The 4 × 3 keypad defaults to rows on P0.0–P0.3 and columns on P0.4–P0.6. An optional gate uses P3.3.

A scanning program drives a row low and reads the column pins to find a closed key. Release input bits high before reading them. Check the wiring and gate setting if the program sees no key.

Open Experiment Settings to choose an interaction mode:

- **Standard:** independent keys toggle open and closed.
- **Pulse:** a key closes while held. Use the mouse, or Space when the key has focus.
- **Radio:** one key can remain latched; pressing it again releases it.

Changing mode releases all keys. Optional **Keypad Bounce** adds a repeatable 30 ms pattern in Standard mode only. Pulse and Radio do not bounce.

## Character LCD

Apply **LCD Text**. The simulated LCD has two lines of 16 characters. By default, data uses P1, RS uses P1.3, and E uses P1.2.

:::caution[Check the data/control overlap]
The default RS and E signals overlap P1 data bits. Use the supported **4-bit initialization and transfer sequence**, sending the high nibble then the low nibble on the upper data pins. An independent 8-bit bus requires remapping the control pins.
:::

The LCD samples transfers on E's falling edge. RS chooses command or character data. R/W is grounded, so the processor cannot read the busy flag.

With busy timing enabled, wait at least:

- **1,520 µs** after Clear or Home.
- **37 µs** after other completed commands and data writes.

Writes during the busy interval are ignored and counted on the LCD card. Use simulated instruction costs to build delays. Increasing Batch does not shorten the LCD's required simulated delay. Timing can be disabled explicitly in Experiment Settings for a simplified exercise.

## Glyphs and display limits

The LCD supports eight programmable 5 × 8 CGRAM glyphs, cursor underline, and simulated-time blinking. Character codes 0–7 select custom glyphs and 8–15 alias them.

ASCII and the documented yen/right/left-arrow substitutions are supported; other character-ROM glyphs appear as placeholders. Function Set configurations outside two-line, 5 × 8 mode are reported beside the display.

For missing text, check initialization, the selected data width, RS/E mappings, and the ignored-write count before changing the program's character data.
