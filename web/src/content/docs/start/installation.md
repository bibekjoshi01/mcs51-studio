---
title: Install MCS51 Studio
description: Download and install MCS51 Studio on Windows, macOS, or Debian/Ubuntu Linux.
---

**You will need:** a supported desktop computer and an installer from the official repository. Installers include the runtime; you do not need to install Python separately.

## Download the right installer

Open the [official GitHub Releases page](https://github.com/bibekjoshi01/mcs51-studio/releases). Read the release notes and choose the file for your operating system and processor. Use an installer asset rather than GitHub's automatically generated source-code archive.

Files ending in `.sha256` contain optional checksums. They are not installers.

## Windows

Windows 10 or 11 on an x64 computer is supported.

1. Download the file ending in **`-windows-x64-setup.exe`**.
2. Run it and choose the installation folder and Start-menu folder.
3. Choose whether to add a desktop shortcut, then select **Install**.
4. Launch MCS51 Studio from the final setup page or the Start menu.

The default location installs for your account without administrator access.

## macOS

1. Open **Apple menu → About This Mac**. An Apple chip uses the Apple Silicon installer; an Intel processor uses the Intel installer.
2. Download **`-macos-arm64.pkg`** for Apple Silicon or **`-macos-x64.pkg`** for Intel.
3. Open the package and follow the installer.
4. Open **MCS51 Studio** from Applications.

Depending on your keyboard settings, hold **Fn** while pressing function-key shortcuts. You can always use the application's buttons instead.

## Debian / Ubuntu Linux

The baseline is Ubuntu 22.04 with an X11 or XWayland desktop. Choose `amd64` for x64 or `arm64` for ARM64.

1. Download the matching `.deb` package.
2. Open a terminal in the download folder.
3. Install it, replacing the example filename with the file you downloaded:

```sh
sudo apt install ./MCS51-Studio-VERSION-linux-amd64.deb
```

For ARM64, use the `arm64` file instead. Launch from the applications menu or run:

```sh
mcs51-studio
```

## Check that it opens

The application opens with an LED-counter program in the editor. You should see **Assemble**, **Step**, and **Run** in the command row, plus a processor inspector.

Choose **Assemble** or press **F6**. A successful result appears in Activity and a source listing becomes available. You are ready for [Your first program](../first-program/).

If the window opens but a panel is missing, use **View → Reset Layout**. For other problems, see [Troubleshooting](../../reference/troubleshooting/).

## Running from source

Developers can run the application with Python 3.10+ and Tk. Follow the repository's [development guide](https://github.com/bibekjoshi01/mcs51-studio/blob/main/docs/development.md) for platform-specific setup and checks. The website itself has its own setup in `web/README.md`.
