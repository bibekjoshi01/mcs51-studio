---
title: Projects and recovery
description: Save portable experiments, choose the right file format, and recover unsaved work.
---

A `.mcs51` project keeps your program and its experiment setup together. Use it when an exercise depends on particular wiring, inputs, or debugger settings.

## Save a project

1. Write or open assembly source.
2. Configure the board, experiment settings, and any watches.
3. Choose **File → Save Project**.
4. Select a name and location for the `.mcs51` file.

Once a project is open, ordinary **Save / Ctrl+S** saves the complete project. **Save Project As** creates a copy. A plain assembly file continues to use source-only Save until you create or open a project.

## What travels with it?

Projects contain source, the supported processor/clock profile, pin mappings, enabled peripherals, keypad gate, switch/key/analogue inputs, teaching settings, UART framing, watches, and Logic Analyzer probe/trigger settings.

They do not need external source files or absolute paths. Students can open the same project on another supported platform.

:::note[Configuration, not a live snapshot]
Opening a project resets RAM, active pulses, serial queues, and captured waveforms. It restores the experiment setup, not the exact point where execution was paused. Layout and platform fonts remain local preferences.
:::

## Open a project

Choose **File → Open Project**, select the file, and press **F6** to assemble the restored source. Settings are validated before the current experiment is replaced.

Only the Classic 8051 at 12 MHz with 12 clocks per cycle is supported. An unsupported profile/clock or malformed settings is rejected; change the file using the version of the application that created it or correct the source configuration.

## Pick a file format

- **`.asm`:** editable assembly source. Use for small programs whose setup is described separately.
- **`.mcs51`:** source plus portable experiment configuration. Use for a reproducible lab or teaching exercise.
- **Intel HEX:** machine bytes and addresses. Use to exchange assembled code. Original source is not included.

A HEX-only import cannot become a source project. Export HEX or open assembly source first.

## Recover unsaved work

Changed experiments are autosaved every **15 seconds** to a separate recovery file in the application settings directory.

1. On startup, look for a recovery message in the status area.
2. Choose **File → Recover Autosave**.
3. Inspect the recovered experiment.
4. Save it as a project to keep it.

Recovery opens unsaved work. A successful save or confirmed normal close removes that session's recovery file. Atomic writes help protect the previous saved version if a write fails.

## Settings locations

- **Windows:** `%APPDATA%/mcs51-studio/settings.json`
- **macOS:** `~/Library/Application Support/mcs51-studio/settings.json`
- **Linux:** `$XDG_CONFIG_HOME/mcs51-studio/settings.json`, defaulting to `~/.config/mcs51-studio/settings.json`

The `MCS51_STUDIO_SETTINGS` environment variable overrides the settings path for isolated development runs. Malformed settings fall back to defaults.
