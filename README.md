# MCS51 Studio

**8051 development and simulation for Windows, Linux, and macOS.**

MCS51 Studio brings assembly editing, debugging, and peripheral simulation into
one desktop application. Inspect registers and memory, trace program execution,
and work with a configurable virtual board.

## Install And Run

Get the installer from [Releases](https://github.com/bibekjoshi01/mcs51-studio/releases).
Installers include everything needed to run the application; no separate runtime
installation is required. Public installers are not yet published.

- **Windows 10/11, x64:** run `*-windows-x64-setup.exe`, then open MCS51 Studio
  from the Start menu.
- **macOS:** install `*-macos-arm64.pkg` for Apple Silicon or `*-macos-x64.pkg`
  for Intel, then open MCS51 Studio from Applications.
- **Debian/Ubuntu:** install the matching `amd64` or `arm64` package, then open
  MCS51 Studio from the applications menu or run `mcs51-studio`:

  ```sh
  sudo apt install ./MCS51-Studio-*-linux-amd64.deb
  ```

  Replace `amd64` with `arm64` when needed. The Linux baseline is Ubuntu 22.04
  with an X11 or XWayland desktop.

## First Program

The editor opens with an LED counter. **F6** assembles, **F7** steps, and **F5**
runs or pauses. Save with **Ctrl+S**, or **Command+S** on macOS. Press **F1** for
shortcuts. Resize panes by dragging dividers; **View → Reset Layout** restores them.

## Capabilities

- Assembly editor with syntax highlighting, completion, and find/replace.
- Classic 12-clock 8051 with stepping, breakpoints, registers, and flags.
- 128-byte internal RAM and 64 KB external RAM with MOVX and XDATA inspection.
- LEDs, switches, multiplexed displays, keypad, LCD, ADC/DAC, motor, and UART.
- Visible wiring, shared-pin explanations, and saved experiment presets.
- Digital logic analyzer with edge triggers and pulse measurements; DAC scope with cursors.
- Assembly source files and Intel HEX import/export.

See [supported features and limits](docs/compatibility.md) for the processor model
and peripheral behavior supported by this version.

## Development And Documentation

- [Development](docs/development.md): source setup, testing, and contribution.
- [Workbench guide](docs/workbench.md): editor, debugger, panels, and shortcuts.
- [Processor Profile](docs/processor.md): exact configuration and validation.
- [Architecture](docs/architecture.md): code layout and dependency boundaries.
- [Releases](docs/releases.md): native builds, artwork, and signing.

## License

Source is available for free educational use and private modification under the
[educational license](LICENSE). Redistribution is restricted. Commercial use
requires a separate written license, which may involve a fee. Contact
[Bibek Joshi](https://github.com/bibekjoshi01) to request commercial permission.
