# MCS51 Studio

A desktop workbench for writing, stepping through, and inspecting 8051 assembly
programs on **Windows, Linux, and macOS**.

Includes an assembler, register and memory views, breakpoints, Intel HEX files,
and a virtual board with LEDs, switches, keypad, displays, ADC/DAC, motor, and UART.

## Install and Run

Download the installer for your computer from [Releases](https://github.com/bibekjoshi01/mcs51-studio/releases).
**The installers include Python and Tk. You do not need to install Python.**
Public installers have not been published yet; native builds are prepared by the
release workflow and remain drafts until reviewed.

### Windows

1. Download `*-windows-x64-setup.exe` for Windows 10 or 11 (64-bit).
2. Run the installer and follow the setup wizard.
3. Open **MCS51 Studio** from the Start menu.

### macOS

1. Download `*-macos-arm64.pkg` for Apple Silicon or `*-macos-x64.pkg` for Intel.
2. Open the package and follow the installer.
3. Open **MCS51 Studio** from Applications.

### Linux

Debian/Ubuntu packages are provided for `amd64` (x64) and `arm64` desktops.
The build baseline is Ubuntu 22.04; a graphical X11 or XWayland session is required.

Download the matching `.deb`, open a terminal in its folder, and install it:

```sh
sudo apt install ./MCS51-Studio-*-linux-amd64.deb
```

For ARM64, replace `amd64` with `arm64`. Open **MCS51 Studio** from the applications
menu, or run `mcs51-studio` in a terminal. Other Linux package formats are not yet provided.

## First Program

The app opens with an LED counter example. Click **Assemble**, then **Step** (F7)
or **Run / Pause** (F5). Double-click a listing row to toggle a breakpoint.
Save with **Ctrl+S** on Windows/Linux or **Command+S** on macOS.

## Project Status

MCS51 Studio is an early-stage 8051 learning workbench. The current focus is a
clear debugger and virtual board; guided lessons and a redesigned interface are
planned. See [supported features and limits](docs/compatibility.md) and the
[code structure and learning roadmap](docs/architecture.md).

For running from Python and contributing, see [development](docs/development.md).
Maintainers can find native packaging and signing details in [releases](docs/releases.md).
