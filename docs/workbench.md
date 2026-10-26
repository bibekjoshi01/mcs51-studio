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
the listing, memory explorer, execution debugger, and activity.
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
- **Debug:** Last Instruction, Watches, and Stack, with execution controls.
- **Activity:** assembly results and diagnostics. Assembly errors open this tab.

## Editor And Files

New/Open check for unsaved source and offer Save, Discard, or Cancel. Assembling
never marks a modified file as saved. A dot on the editor tab indicates unsaved
source or project settings. Editing pauses execution and requires assembly before the next run.

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
- F8: Step Over. Shift+F8: Step Out. F9: Run To Cursor.
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


## Explain Execution

Open **Debug** in the bottom panel. **Step Over (F8)** runs a call and stops at
its return; other instructions execute once. **Step Out (Shift+F8)** returns from
the current tracked call or interrupt. **Run To Cursor (F9)** stops before the
assembled instruction on the editor cursor's line. Blank lines and DB data are
not execution targets. All three respect ordinary and change breakpoints. Pause,
editing, or Reset cancels a temporary run; an unreached target stops after one
million instructions. Step Out requires a call frame observed since Reset.

**Last Instruction** shows address/bytes, observed data inputs, register results,
CY/AC/OV/P before and after, memory changes, and instruction/interrupt-entry costs.
Changed register values are mint. Costs use simulated time, not UI playback time.
The result includes timer and peripheral updates during that instruction.
**Stack** separates raw internal RAM below SP from tracked calls and interrupts.
A mismatched return stops execution with a stack explanation. Manually editing
registers or memory clears tracked frames; watches remain.

Add watches for `ACC`, `R0`, `DPTR`, `CY`, or `RAM[30]`, `SFR[90]`, `BIT[90]`,
`XDATA[1234]`, and `CODE[0100]`. Addresses are hexadecimal; RAM means indirect
internal RAM, 00–7F. Register/SFR watches show latch values; BIT port watches show
resolved pin levels. **Break On Change** compares values before/after each complete
instruction, including timer/peripheral changes. It does not stop on a write of
the same value. Double-click a watch to toggle its change breakpoint. Expressions
are explicit locations, not arbitrary calculations. Up to 64 watches are supported.
Execution history and reverse stepping are not available yet.

## Teaching Peripheral Controls

Open **Tools → Experiment Settings**, also available in **Virtual Board → Hardware**.
Keypad **Standard** toggles independent keys, **Pulse** closes while held, and
**Radio** permits one latched key; pressing that key again releases it. Changing
mode releases all keys. Held keys are visually pressed. Optional switch bounce
uses a repeatable ten-phase contact pattern over the chosen duration, then settles.
It advances only with simulated time. Bounce applies to switches, not the keypad.

Choose **P3.2 / INT0** or **P3.3 / INT1** and a low-pulse width, then **Apply And Pulse**.
Configure TCON/IE in your program to observe an interrupt. Pulses hold the resolved
pin low without changing its latch. Shared devices can also hold it low. Pulses
and bounce are observed at instruction boundaries; sub-instruction widths and
analogue electrical behavior are not modeled.

The LCD renders eight programmable 5×8 CGRAM glyphs (codes 0–7, aliased at 8–15),
a cursor underline, and simulated-time blinking. ASCII text is supported; other
controller-ROM glyphs appear as placeholders. With busy timing enabled, Clear/Home
need 1,520 µs and other completed commands/data writes need 37 µs. Writes during
busy time are ignored and counted visibly. R/W is grounded, so programs must wait;
they cannot read a busy flag. Disabling timing is an explicit teaching option.

The UART tab exposes baud, 7/8 data bits, None/Odd/Even parity, and 1/2 stop bits.
**Apply Framing** validates settings; changing an active link requires **Reset Link**,
which discards queued/in-flight data. It retains the transcript and error counts;
Reset Machine clears those. Invalid hex lists or values outside the selected data
width are rejected without sending partial data. Receive diagnostics count short
start pulses, parity mismatch, and low stop bits; invalid frames are discarded.
Match the MCU configuration and baud generator to the terminal. The fixed 1 µs
sampling grid rounds external bit periods; this is not an arbitrary electrical link.
Instantaneous pin/display state is independent of the **Show Transitions** playback
option; there is no hidden display-persistence effect.

## Portable Projects And Recovery

Use **File → Save Project** to create one `.mcs51` file. It contains assembly source,
the exact processor/clock profile, pin mappings, enabled peripherals, keypad gate,
switch/key/analogue inputs, teaching settings, UART framing, watches, and logic
analyzer probe/trigger settings. No absolute paths or external source files are
required. Send this file to students; **File → Open Project** restores the experiment,
then **F6** assembles it. The supported processor is Classic 8051 at 12 MHz with
12 clocks per cycle; unsupported profiles/clocks and malformed settings are
rejected before replacing the current experiment.

Once a project is open, **Save / Ctrl+S** saves the complete project. **Save Project As**
creates a copy. Ordinary assembly files still use ordinary source Save. Projects
store experiment configuration, not a paused-machine snapshot: RAM, active pulses,
serial queues, and captured waveforms are reset. HEX-only imports cannot become
source projects; export HEX or open assembly source first.

Changed experiments are autosaved every 15 seconds to an independent recovery file
in the application settings directory. A startup status message points to
**File → Recover Autosave** when files exist. Recovery opens an unsaved experiment;
save it as a project to keep it. Successful saves and confirmed normal closing
remove that session's recovery file. Writes are atomic; a failed save leaves the
previous file intact. Layout and platform fonts remain local preferences.
