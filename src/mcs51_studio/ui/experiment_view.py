"""Teaching controls and LCD rendering, kept outside the main toolbar."""

import tkinter as tk
from tkinter import messagebox, ttk

from ..hardware.experiment import ExperimentSettings


class ExperimentView:
    def experiment_window(self):
        existing = getattr(self, "experiment_dialog", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            return
        window = self.experiment_dialog = tk.Toplevel(self.root)
        window.title("Experiment Settings")
        window.transient(self.root)
        body = ttk.Frame(window, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(
            body,
            text="Classic 8051 · 12 MHz · 12 Clocks / Cycle",
            style="Section.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))
        variables = {}
        fields = [
            ("keypad_mode", "Keypad Mode", ["Standard", "Pulse", "Radio"]),
            ("switch_bounce", "Switch Bounce", None),
            ("bounce_us", "Bounce Duration (µs)", []),
            ("lcd_timing", "Enforce LCD Busy Timing", None),
            ("interrupt_pin", "Interrupt Pin", ["P3.2", "P3.3"]),
            ("interrupt_width_us", "Low Pulse Width (µs)", []),
        ]
        for row, (key, title, choices) in enumerate(fields, 1):
            value = getattr(self.board.experiment, key)
            var = (
                tk.BooleanVar(value=value)
                if type(value) is bool
                else tk.StringVar(value=str(value))
            )
            variables[key] = var
            ttk.Label(body, text=title).grid(
                row=row, column=0, sticky="w", padx=(0, 24), pady=6
            )
            widget = (
                ttk.Checkbutton(body, variable=var)
                if choices is None
                else ttk.Combobox(
                    body, textvariable=var, values=choices, state="readonly", width=18
                )
                if choices
                else ttk.Entry(body, textvariable=var, width=20)
            )
            widget.grid(row=row, column=1, sticky="w")
        ttk.Label(
            body,
            text="Standard: Toggle Keys · Pulse: Hold To Close · Radio: One Key\nBounce and pulses advance with simulated time. LCD R/W is grounded.\nProjects preserve these settings. Processor and clock are fixed for this profile.",
            style="Muted.TLabel",
            justify="left",
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=14)

        def apply(pulse=False):
            try:
                data = {k: v.get() for k, v in variables.items()}
                for key in ("bounce_us", "interrupt_width_us"):
                    data[key] = int(data[key])
                settings = ExperimentSettings.validated(data)
                self.board.set_keypad_mode(settings.keypad_mode)
                self.board.experiment = settings
                if pulse:
                    self.board.stimulus.pulse(
                        settings.interrupt_pin,
                        self.cpu.cycles,
                        settings.interrupt_width_us,
                    )
                self.board.update()
                self.refresh()
                self.status.set(
                    "Interrupt Pulse Armed · Run or step to advance time"
                    if pulse
                    else "Experiment Settings Applied"
                )
            except ValueError as error:
                messagebox.showerror(
                    "Invalid Experiment Setting", str(error), parent=window
                )

        buttons = ttk.Frame(body)
        buttons.grid(row=8, column=0, columnspan=2, sticky="ew")
        ttk.Button(buttons, text="Apply", command=apply).pack(side="left")
        ttk.Button(buttons, text="Apply And Pulse", command=lambda: apply(True)).pack(
            side="left", padx=8
        )
        ttk.Button(buttons, text="Close", command=window.destroy).pack(side="right")

    def sync_uart_controls(self):
        uart = self.board.uart
        self.baud.set(str(uart.baud))
        self.parity.set(["None", "Odd", "Even"][uart.parity])
        self.data_bits.set(str(uart.data_bits))
        self.stop_bits.set(str(uart.stop_bits))

    def apply_uart(self):
        try:
            self.board.uart.configure(
                int(self.baud.get()),
                ["None", "Odd", "Even"].index(self.parity.get()),
                self.board.cycle_us,
                int(self.data_bits.get()),
                int(self.stop_bits.get()),
            )
            self.refresh()
            return True
        except ValueError as error:
            messagebox.showerror("UART Configuration", str(error), parent=self.root)
            return False

    def reset_uart_link(self):
        self.board.uart.reset_link()
        self.refresh()

    def draw_lcd(self):
        canvas, lcd = self.lcd_canvas, self.board.lcd
        canvas.delete("all")
        color = "#A9E7C9" if self.board.enabled["lcd"] else "#92A1B9"
        width = max(320, canvas.winfo_width())
        cell = (width - 20) / 16
        cursor = lcd.cursor_cell()
        for row, line in enumerate(lcd.lines()):
            for col, char in enumerate(line):
                x, y = 10 + col * cell, 9 + row * 30
                glyph = lcd.glyph(ord(char)) if lcd.display else None
                block = (
                    cursor == (row, col)
                    and lcd.blink
                    and (self.cpu.cycles // 409600) % 2 == 1
                )
                if glyph is not None or block:
                    for gy, bits in enumerate((31,) * 8 if block else glyph):
                        for gx in range(5):
                            if bits & (1 << (4 - gx)):
                                canvas.create_rectangle(
                                    x + gx * cell / 6,
                                    y + gy * 3,
                                    x + (gx + 1) * cell / 6 - 1,
                                    y + gy * 3 + 2,
                                    fill=color,
                                    outline="",
                                )
                else:
                    canvas.create_text(
                        x,
                        y,
                        anchor="nw",
                        text=char if 32 <= ord(char) < 127 else "□",
                        fill=color,
                        font=(self.mono_font, -21),
                    )
                if cursor == (row, col) and lcd.cursor:
                    canvas.create_line(
                        x, y + 25, x + cell * 5 / 6, y + 25, fill=color, width=2
                    )
        state = "Busy" if self.cpu.cycles < lcd.busy_until else "Ready"
        self.lcd_status.configure(
            text=f"{state} · {lcd.ignored_writes} ignored writes"
            + (f" · {lcd.last_error}" if lcd.last_error else "")
        )
