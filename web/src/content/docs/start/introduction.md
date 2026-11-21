---
title: What is MCS51 Studio?
description: Meet the desktop application, understand what it simulates, and choose a starting point.
---

MCS51 Studio is a desktop application for learning how an **8051 microcontroller** works. Write assembly instructions, run them on a simulated processor, and see what happens to registers, memory, and connected devices.

You do not need a physical development board to follow these guides. You do need the desktop application: this website explains the software; it does not run the simulator in your browser.

## What can I do with it?

- **Write a program.** The editor highlights assembly code and the assembler turns it into machine instructions.
- **Follow execution.** Step through a program one instruction at a time, set breakpoints, and inspect changes.
- **Experiment with hardware.** Connect virtual LEDs, switches, displays, a keypad, an LCD, ADC/DAC, a motor, and UART.
- **Measure signals.** Capture digital transitions with the Logic Analyzer or view DAC output on the scope.
- **Save an experiment.** Keep source and board configuration together in a portable `.mcs51` project.

## A good first session

1. [Install the application](../installation/) for your operating system.
2. Follow [Your first program](../first-program/) to assemble and step through a small example.
3. Read [8051 essentials](../8051-basics/) when a term such as register, port, or hexadecimal is unfamiliar.
4. Take the [workbench tour](../../workbench/interface/) to find the tools around the editor.
5. Try the [example programs](../../examples/) when you are ready to experiment.

Each guide states what to do and what you should observe. Go at your own pace; pausing and inspecting state is part of the learning process.

## Which processor does it simulate?

The current profile is **Classic 8051**, with a 12 MHz oscillator and 12 clocks per machine cycle. One machine cycle takes one simulated microsecond. The processor has 128 bytes of internal RAM, two timer/counters, and one data pointer.

The virtual board also provides separate 64 KB code and external-data address spaces. It does not enable 8052 features such as Timer 2 or upper internal RAM. Read the [processor reference](../../reference/processor/) for the exact model.

## For teachers

Use a built-in experiment preset to enable the relevant peripherals, add source and watches, then save a `.mcs51` project. Students can open that project and assemble it on their own machine. Projects preserve the experiment configuration; they do not preserve a running processor snapshot.

The website's examples are practice material. The application does not provide an integrated lesson runner or automatic exercise grading.

## Use and availability

MCS51 Studio is available for Windows, macOS, and Debian/Ubuntu Linux. Personal learning and noncommercial teaching are free under the project's educational license. See [license and credits](../../reference/license/) for redistribution and commercial-use terms.
