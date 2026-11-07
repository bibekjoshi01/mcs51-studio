# EdSim51 Guide Acceptance Review

Reviewed **2026-11-07** against the [EdSim51 user guide](https://edsim51.com/users-guide-2/).
This review checks MCS51 Studio; it does not certify identical UI or a bug-free app.

## Results

On macOS, Python 3.12/Tk 8.6: **128 unit/integration tests, 25 existing GUI tests,
12 new guide GUI tests, and 7 stress tests passed**. Stress coverage includes
1,000 control actions, 41 menu commands, repeated windows, and a 65,536-row listing.
No assertion failures or captured callback exceptions remained.

The local Ruff binary is 0.16.9; CI installs the repository's pinned version.
Windows/Linux are configured in CI but were not run locally. Installers were not
rebuilt. The installed app received limited visual/assembly-shortcut inspection;
new changes were tested from source with native Tk controls and real temporary
files. Automated file dialogs and expected error prompts are stubbed.

## Reproduced Defects Fixed

- Keypad INT1 fired with no key pressed when rows were low. The gate now resolves
  columns; a program test checks that a real press invokes the handler once.
- Run skipped an initial-PC breakpoint. Stop-before-execute, resume, and Reset
  are now tested.
- Code edits left stale Listing bytes and were lost on HEX export. Listing marks
  modified code, export uses current bytes, and execution descriptions avoid
  attributing changed bytes to the original source literal.
  Newly edited code regions also remain executable/exportable until Reset,
  including intentional zero-valued NOP bytes outside the original image.
- Zero/negative batches could leave Run active without progress. Counts are now
  validated; uncommitted input cannot disrupt a running batch.
- Reset Link left a paused UART transmit pin low; reset now releases it immediately.
- File dialogs omitted `.a` and forgot the last directory. Source/HEX/project
  dialogs now retain the folder across sessions.
- Memory Go silently accepted invalid addresses; it now rejects them. Horizontal
  scrolling makes memory columns reachable when a pane is narrow.

## Complete Section Checklist

References are test names or test modules. A passing equivalent workflow does not
mean identical button placement. Gaps below are explicitly excluded from passes.

1. **Microcontroller panel:** all implemented SFRs now have editable inspector
   entries/address hints. `tests/gui.py` covers register edits/ranges and pins
   versus latches; pins remain controlled by external inputs.
2. **Bitfield:** added SFR/RAM selection, live bits, named hints, and addressability
   enforcement. `guide_gui.test_bitfield_edits_only_bit_addressable_locations`
   covers editable/read-only bytes and a held-low port input.
3. **Data/code memory:** existing RAM/SFR/XDATA tests plus new navigation and
   patched-code export tests. Pages contain 128 bytes including the requested
   address, rather than beginning at that exact byte.
4. **Update frequency:** custom positive batches and 50,000 are supported. Enter
   applies a typed count while paused/running. `test_custom_batch_validation_and_saved_settings`
   covers validation, execution count, and persistence. Time limits/Show Transitions
   may yield before that maximum count.
5. **Assembly panel:** GUI tests cover syntax, typing, error messages/lines, and
   stale-code blocking. Editing pauses execution and requires reassembly, rather
   than locking the source editor.
6. **Source expansion:** focus mode, pane visibility/dividers/recovery, small-window
   layout, and zoom through 185% have GUI coverage. There is no detached editor.
7. **Load/save:** source/project GUI and source-file tests cover real files, cancel,
   atomic failure, BOM/newlines, unsaved changes, and remembered directories.
8. **Intel HEX:** workflow/QA/termination/GUI tests cover validation, round trips,
   import/execution, end of loaded code, and export of edited machine bytes.
9. **Clipboard:** existing GUI tests cover copy/cut/paste, selection, undo, line
   endings, invalid data, and unavailable clipboard contents.
10. **Assembler:** `test_assembler_directives_aliases_and_number_formats` executes
    a combined directives/banks/aliases/numbers/call/END program. Independent CPU
    specification tests and fixtures cover instructions. MOVX is also supported.
11. **Debugging:** GUI/teaching suites cover listing, next/last instructions,
    stepping, source position, watches, and tracked call stacks.
12. **Breakpoints:** new GUI tests cover the initial instruction, resume/reset,
    typed addresses, toggle, invalid targets, and clear-all. Existing source-gutter
    and listing interactions remain covered.
13. **Peripheral panel:** GUI tests cover enables, badges, pins, scrolling,
    responsive hardware controls, and tabs. Color customization is a gap.
14. **Dynamic interface:** instrument/project tests cover remapping, validation,
    presets, persistence, connections, and sharing. Changes apply while paused;
    restarting is not required.
15. **Port connection zoom:** Wiring offers separate-window pin/connection
    inspection, with a different arrangement from the reference's port buttons.
16. **LEDs/display/DAC:** all 2,048 reference output cases plus new program checks
    cover active-low signals, four digits/chip select, shared buses, and DAC hold.
    Individual LED color selection is a gap.
17. **DAC scope:** instrument/GUI tests cover voltage/time, cursors, freeze/live,
    zoom/history, and retention. Labeled microseconds replace division tooltips;
    arbitrary oscillator selection is unsupported.
18. **LCD bus/initialization:** board/new acceptance tests cover four-bit nibble
    order, remapped eight-bit transfer, RS/E, display/cursor, disabled hardware,
    and unsupported Function Set diagnostics.
19. **LCD instructions/CGRAM:** tests cover clear/home, addressing/wrap, entry
    modes/shifts, custom glyphs, timing, cursor, rendering, and yen/arrow symbols.
    The complete controller character ROM is not implemented.
20. **Switches/ADC:** all 256 switch patterns, reference ADC traces, and an executed
    conversion/read program cover shared data, tri-state readout, restart,
    interrupt completion, and disable/release behavior.
21. **Switch labels:** right-click label customization is absent; gap.
22. **Comparator:** threshold tests cover below/equal/above reference, DAC hold,
    and ADC exclusion. Enables are separate; comparator drives with ADC disabled.
23. **Motor:** tests cover both directions, stop/disable, speed, simulated elapsed
    time, and actual Timer 1 revolution counting. The graphic now meets its top
    sensor when T1 is low; direction text remains visible at fast update rates.
24. **UART:** MCU/endpoint/GUI suites cover bytes, baud/framing/parity, back-to-back
    transfers, diagnostics, sharing, reset, and retained output. The UI queues
    sends instead of locking input. Active framing changes require Reset Link.
25. **UART text/HEX:** new acceptance tests check text terminators, unmodified byte
    lists, escaped braces, ranges, parsing, and no partial enqueue on invalid input.
26. **Keypad/gate:** every key, connected groups, default-off gate, no-key idle,
    and an executed interrupt handler have explicit checks.
27. **Key bounce:** added optional Standard-mode 30 ms simulated-time bounce.
    Refresh while paused does not advance it; Pulse/Radio remain unaffected.
28. **Keypad modes:** Standard is now the default. Teaching/acceptance tests cover
    Standard/Pulse/Radio, repeated presses, and release on mode changes.
29. **Key labels:** right-click relabeling/automatic resize is absent; gap.
30. **Saved settings:** GUI/stress tests cover batch/folder/experiment/UART,
    wiring/presets/layout, malformed fallback, and backward-compatible projects
    without the new optional bounce/speed fields. Preferences use platform paths.

## Outstanding Validation And Differences

Color/label controls, arbitrary clocks, and full LCD ROM must not be counted as
passes. Native file-dialog interaction, all visual/accessibility paths, and local
Windows/Linux execution remain unverified. Sub-instruction electrical behavior
is outside the model. This audit therefore does **not** establish full EdSim51
parity or prove the absence of further bugs.

## Repeatable Checks

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 tests/gui.py
PYTHONPATH=src python3 tests/guide_gui.py
PYTHONPATH=src python3 tests/stress_gui.py
python3 -m ruff check .
python3 -m ruff format --check .
```

Desktop tests require a graphical session; use `xvfb-run -a` on headless Linux.
Normal and release CI workflows both include the guide GUI suite.
