# Architecture

```text
src/mcs51_studio/
  engine/      Processor profile, CPU, assembler, interrupts, timers, serial
  hardware/    Virtual board, LCD, external UART, and wiring
  ui/          Application, workspace, editor, inspector, board views, theme, icons, widgets
  data/        Instruction catalog, example assembly, runtime icon
  config.py    Platform settings paths
  metadata.py  Application name, ID, and version
  resources.py Bundled data loading
  source_files.py Atomic source saves
  smoke.py     Minimal packaged-app self-check
scripts/       Source launcher, installer builds, icon generation
packaging/     Native installer definitions and master icon assets
tests/         Headless tests, explicit desktop checks, regression fixtures
docs/          Development, usage, architecture, limits, and releases
```

## Boundaries

- `engine` runs without Tk, a display, settings files, or UI imports.
- `hardware` models devices against CPU state and pins; it does not import UI code.
- `ui/application.py` owns machine state, files, and execution coordination.
  `workspace.py` arranges panes, navigation, menus, and document actions.
  `editor.py`, `inspector.py`, `board_view.py`, and `widgets.py` handle presentation
  and interaction. The editor delegates grouped edits to `editor_actions.py`,
  literal search to `search.py`, and explicit completion to `completion.py`.
  `engine/source.py` handles source normalization and quoted data parsing.
- Shared resources, metadata, and platform settings stay outside these layers.
- Detailed editor and layout checks live in `tests/gui.py`. Installed apps keep
  only a small self-check for release validation.

Unsaved source is separate from assembly validity. Pending execution callbacks
are canceled on pause, edit, reset, and close. Changes to CPU behavior require
focused headless tests; presentation changes use desktop integration checks.

## Next Steps

Keep the [Classic 8051 contract](processor.md) covered by specification tests.
Add a shared simulation session when multiple documents or lessons need it.
Build lessons around runnable examples and observable state changes: registers
and addressing, control flow and stack, ports and displays, timers and interrupts,
serial, and integrated board projects. External-memory lessons can use MOVX and the XDATA inspector. Add modules when they contain working behavior, not placeholders.
