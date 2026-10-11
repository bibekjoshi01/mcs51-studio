# Using the workbench

The logo, small learning-workbench tagline, and file/debugger commands share one
compact top row, leaving more vertical space for the editor and bottom tools.
The workspace keeps source, machine state, and peripherals in separate areas.
The editor and virtual board share the central tab area. The processor inspector
shows the next instruction, registers, and flags; register values are hexadecimal.
Edit a value and press Enter to apply it.

## Panels and navigation

Drag the horizontal or vertical dividers to resize areas. Use the status-bar
Sidebar, Inspector, and Bottom controls, or the View menu, to hide them.
**Focus editor** hides supporting panels; press it again to show them.
**View → Reset layout** restores the standard layout if a pane becomes too small.
Pane visibility and divider positions are saved with application settings.

The sidebar opens the editor, board, listing, memory explorer, and tools.
Open **Instruction Reference** from the footer for the 8051 instruction catalog. The LED counter button restores the starter program after
checking for unsaved edits. Narrow or short sidebar, inspector, and board views
can be scrolled.

The bottom tools contain:

- **Listing:** addresses, encoded bytes, and corresponding source statements.
- **Memory:** internal RAM, SFRs, and code memory. Select a region or enter a code
  address and press Enter. Double-click a RAM byte to edit it.
- **Activity:** assembly results and diagnostics. Assembly errors open this tab.

## Editor and files

New/Open check for unsaved source and offer Save, Discard, or Cancel. Assembling
never marks a modified file as saved. A dot on the editor tab indicates unsaved
source. Editing pauses execution and requires assembly before the next run.

The editor supports assembly highlighting, line numbers, horizontal/vertical
scrolling, automatic indentation, multiline indentation, comment toggling,
find/replace, and a context menu. Find is case-insensitive, wraps at the end of
the document, and treats the search text literally. Replace-all is one undoable
operation. Escape closes the search controls.

Intel HEX images contain machine code without original assembly source. Opening
one displays an explanatory buffer and loads the image into the debugger; use
Listing and Memory to inspect it. Editing that buffer starts a new assembly
program. Export Intel HEX writes the current assembled program.

## Keyboard shortcuts

Use Command on macOS wherever Ctrl is shown below. Function keys may require
Fn depending on your keyboard settings.

- Ctrl+N, Ctrl+O, Ctrl+S: New, Open, Save.
- Ctrl+Shift+S: Save as.
- Ctrl+Z, Ctrl+Shift+Z (or Ctrl+Y): Undo, Redo in the editor.
- Ctrl+X, Ctrl+C, Ctrl+V, Ctrl+A: Cut, Copy, Paste, Select all.
- Ctrl+F: Find and replace. Ctrl+H also opens it on Windows/Linux;
  use Command+Option+F on macOS.
- Ctrl+G: Go to line.
- Ctrl+/: Toggle comments on the selected lines or current line.
- Tab / Shift+Tab: Indent / unindent. Enter preserves leading indentation.
- Ctrl+B / Ctrl+J: Toggle sidebar / bottom tools.
- F6: Assemble. F7: Step one instruction. F5: Run or pause.
- Shift+F5: Reset machine state. F1: Shortcut reference.

After assembly, click an editor line number or double-click a listing row to
toggle a breakpoint. A pink gutter dot marks the breakpoint; a mint arrow and
line highlight mark the next source instruction. The toolbar batch value limits
work per UI update; it is not an oscillator-frequency setting.

## Visual conventions

The shared theme uses dark navy surfaces, mint actions and execution indicators,
lavender syntax/focus accents, and muted secondary labels. Technical values use
Menlo or an available monospace fallback; interface text uses Avenir Next,
Segoe UI, or an available sans-serif fallback. Native Tk/ttk controls retain
platform behavior, including native file dialogs. Colors and text styles are
centralized in `ui/theme.py` for subsequent iterations.
