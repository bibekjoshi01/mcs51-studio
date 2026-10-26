# MCS51 Studio User Guide

The application identity and file/debugger commands share one
compact top row, leaving more vertical space for the editor and bottom tools.
The workspace keeps source, machine state, and peripherals in separate areas.
The editor and virtual board share the central tab area. The processor inspector
shows a next-instruction card, individual status-flag tiles, and editable registers.
The card separates source, address, bytes, and timing; the flag grid shows the
active register bank alongside the PSW bits. Register values are hexadecimal.
Edit a value and press Enter to apply it.

## Panels And Navigation

Drag the horizontal or vertical dividers to resize areas. Use the status-bar
Inspector and Bottom controls, or the View menu, to hide them.
**Focus editor** hides supporting panels; press it again to show them.
**View → Reset layout** restores the standard layout if a pane becomes too small.
Pane visibility and divider positions are saved with application settings.

Use the workspace tabs for the editor and virtual board, and bottom tabs for
the listing, memory explorer, and activity.
**Wiring** and **Instruments → DAC Scope** are in the top command row.
Open **Instruction Reference** from the footer for the 8051 instruction catalog.
The inspector and board can be scrolled when their contents exceed the window.
Board scrolling respects trackpad movement size; scrolling over the UART text
area moves the text without also moving the board. Hardware enables are arranged
in horizontal rows that wrap to fit the available width.

The board separates digital I/O, the four-digit display, and peripheral cards.
Mint LEDs indicate active-low outputs; each LED shows its mapped pin. The readout
shows illuminated bits (1 = lit) and their decimal value. In the default counter,
LED 0 means 1, LED 1 means 2, and both mean 3. The 7-segment display shares P1;
this program produces segment patterns, not decimal digits, on that display. Switches
show their bit number and current 0/1 level. **Show transitions** is enabled by default: execution yields briefly after each
LED or display change so fast loops remain visible. Turn it off for throughput;
then the screen shows snapshots and can skip intermediate patterns. This affects
wall-clock playback speed, not instruction order or simulated cycle counts.

Device badges distinguish disabled
hardware from an enabled device that is idle. Keypad keys support mouse hold or
Space while focused. Keypad and motor cards stack when space is limited.

UART has its own scrollable transcript and Clear output action; clearing the view
does not erase received simulation data. Hardware shows port latch and effective
pin values in both binary and hexadecimal. Reset clears the terminal and machine
state while retaining the analogue slider, switch, and interrupt-gate inputs.

The bottom tools contain:

- **Listing:** addresses, encoded bytes, and corresponding source statements.
- **Memory:** internal RAM, SFRs, and code memory. Select a region or enter a code
  address and press Enter. Double-click a RAM byte to edit it.
- **Activity:** assembly results and diagnostics. Assembly errors open this tab.

## Editor And Files

New/Open check for unsaved source and offer Save, Discard, or Cancel. Assembling
never marks a modified file as saved. A dot on the editor tab indicates unsaved
source. Editing pauses execution and requires assembly before the next run.

The editor toolbar and context menu provide Undo, Redo, Cut, Copy, Paste, and
Find/Replace. Editing supports assembly highlighting, line numbers, indentation,
comment toggling, line duplication/movement/deletion, and adjustable text size.
Ctrl+Space completes instruction names, registers, and program symbols.

Find/Replace offers case-sensitive and whole-word matching, forward/backward
navigation, and match counts. Search and replacement text are literal;
replace-all is one undoable operation. Escape closes the search controls.
Pasted source accepts Windows or Unix line endings. Saves replace files atomically
so a failed write does not truncate the previous file.

Assembly errors appear beside the source with a marked line and in Activity.
Editing clears the old diagnostic. Failed assembly blocks execution of the
previous program until the source assembles successfully. Empty or comments-only
buffers cannot run.

Intel HEX images contain machine code without original assembly source. Opening
one displays an explanatory buffer and loads the image into the debugger; use
Listing and Memory to inspect it. Editing that buffer starts a new assembly
program. Export Intel HEX writes the current assembled program.

## Keyboard Shortcuts

Use Command on macOS wherever Ctrl is shown below. Function keys may require
Fn depending on your keyboard settings.

- Ctrl+N, Ctrl+O, Ctrl+S: New, Open, Save.
- Ctrl+Shift+S: Save as.
- Ctrl+Z, Ctrl+Shift+Z (or Ctrl+Y): Undo, Redo in the editor.
- Ctrl+X, Ctrl+C, Ctrl+V, Ctrl+A: Cut, Copy, Paste, Select all.
- Ctrl+F: Find and replace. Ctrl+H also opens it on Windows/Linux;
  use Command+Option+F on macOS.
- Ctrl+G: Go to line.
- Ctrl+D: Duplicate lines. Ctrl+Shift+K: Delete lines.
- Alt+Up / Alt+Down: Move lines.
- Ctrl+Space: Complete an instruction or symbol (Control+Space on macOS).
- Ctrl++ / Ctrl+- / Ctrl+0: Increase, decrease, or reset editor text size.
- Ctrl+/: Toggle comments on the selected lines or current line.
- Tab / Shift+Tab: Indent / unindent. Enter preserves leading indentation.
- Ctrl+J: Toggle bottom tools.
- F6: Assemble. F7: Step one instruction. F5: Run or pause.
- Shift+F5: Reset machine state. F1: Shortcut reference.

After assembly, click an editor line number or double-click a listing row to
toggle a breakpoint. A pink gutter dot marks the breakpoint; a mint arrow and
line highlight mark the next source instruction. The toolbar batch value limits
work per UI update; it is not an oscillator-frequency setting.

## Visual Conventions

The shared theme uses dark navy surfaces, mint actions and execution indicators,
lavender syntax/focus accents, and muted secondary labels. Technical values use
Menlo or an available monospace fallback; interface text uses Avenir Next,
Segoe UI, or an available sans-serif fallback. File dialogs follow the conventions of your operating system.

The processor inspector identifies **Classic 8051 · 12 MHz · 12 Clocks**.
In Memory, select **XDATA** to inspect external RAM used by MOVX. Enter a hex
address and choose **Go**; double-click a byte to edit it while paused. **RAM**
contains only 00–7FH; **SFR** and **Code** are separate views.


## Wiring And Experiment Presets

Open **Wiring** in the header or click a peripheral’s title on the virtual board.
The Wiring tab shows a labeled 40-pin MCU, enabled devices, and their connections.
Select a device to highlight its pins in mint; amber marks pins shared by devices.
Click a port pin to inspect every connected signal. Non-port package pins are
labels, not simulated power or oscillator controls.

Shared-pin explanations describe coupled outputs and input drivers that can pull
a shared line low. These are wiring warnings, not an electrical contention model.
Use **Edit Pin Mappings** to remap signals. Programs must use the new pin addresses.
Built-in experiment presets enable only the relevant devices. **Save As** stores
current wiring, device enables, and keypad gate state under your experiment name;
custom presets persist across sessions. Applying a preset pauses execution and
clears captures, but does not replace your program.

## Logic Analyzer

Open **Instruments → Logic Analyzer**. Enter 1–8 port pins separated by commas,
then select **Apply**. Choose **Free Run**, or a trigger pin and Rising/Falling/Either
edge, and a post-trigger duration. Select **Arm**, then run or step your program.
Arm assembles first if necessary. Stop Capture stops recording without stopping
the processor. Reset clears the capture.

Capture records effective pin levels after each instruction, independently of UI
batch size. It keeps up to 8,192 transition samples, with bounded pre-trigger
history; a full buffer stops recording explicitly. These are instruction-boundary
observations, not sub-cycle measurements or MOVX bus waveforms.

Use **Fit**, **Zoom In/Out**, and **History** to inspect a time range. Click a lane
to select its measurements and place cursor A, then click again for B. Complete
observed pulses yield high/low width; complete rising-edge cycles yield period,
frequency, and duty cycle. A dash means insufficient edges in the visible range.
A/B cursors show Δt and its reciprocal; the reciprocal is only a frequency if you
place the cursors one period apart. All times are simulated microseconds.

## DAC Scope

The **DAC Scope** tab retains the recent DAC output with a stepped waveform,
labeled microsecond time axis, 0–5 V scale, zoom, and history navigation. Enable DAC
in Hardware and run a program to record data. **Freeze** holds a snapshot while the
simulation continues; **Live** resumes updates. Click twice for A/B cursors showing
time, voltage, Δt, and ΔV. The DAC buffer retains the latest 600 samples.
