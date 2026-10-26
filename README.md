# MCS51 Studio

A desktop 8051 learning workbench for **Windows, Linux, and macOS**. Write assembly,
inspect registers and memory, step through instructions, and explore a virtual
board with LEDs, switches, displays, keypad, ADC/DAC, motor, and UART.

## Install and Run

Get the installer from [Releases](https://github.com/bibekjoshi01/mcs51-studio/releases).
Python and Tk are included. Public installers are not yet published; automated
builds produce test artifacts and draft releases.

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
shortcuts. Resize panes by dragging dividers; **View → Reset layout** restores them.

The app is under active development. Guided lessons are planned, and some CPU
and peripheral behavior still needs hardware validation. Read the
[supported features and limits](docs/compatibility.md) before designing exercises.

## Development and Documentation

- [Development](docs/development.md): run from Python, test, and contribute.
- [Workbench guide](docs/workbench.md): editor, debugger, panels, and shortcuts.
- [Architecture](docs/architecture.md): code layout and dependency boundaries.
- [Releases](docs/releases.md): native builds, artwork, and signing.

## License

Source is available for free educational use and private modification under the
[educational license](LICENSE). Redistribution is restricted. Commercial use
requires a separate written license, which may involve a fee. Contact
[Bibek Joshi](https://github.com/bibekjoshi01) to request commercial permission.
