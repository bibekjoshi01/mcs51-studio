"""Virtual Board presentation; machine behavior stays in hardware/."""

import math
import tkinter as tk
from tkinter import ttk

from . import theme
from .widgets import FlowGrid


class BoardView:
    def board_card(self, parent, title, subtitle, device=None):
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        header = ttk.Frame(card, style="Board.TFrame")
        header.pack(fill="x", pady=(0, 4))
        if device:
            ttk.Button(
                header,
                text=title,
                style="Footer.TButton",
                command=lambda: self.wiring_window(device),
            ).pack(side="left")
        else:
            ttk.Label(header, text=title, style="BoardTitle.TLabel").pack(side="left")
        if device:
            badge = ttk.Label(header, style="BoardMuted.TLabel")
            badge.pack(side="right")
            self.board_badges[device] = badge
        description = ttk.Label(
            card, text=subtitle, style="BoardMuted.TLabel", wraplength=300, width=1
        )
        description.pack(fill="x", pady=(0, 10))
        card.bind(
            "<Configure>",
            lambda event: description.configure(wraplength=max(100, event.width - 26)),
        )
        body = ttk.Frame(card, style="Board.TFrame")
        body.pack(fill="both", expand=True)
        return card, body

    def build_board(self, parent):
        self.board_badges = {}
        heading = ttk.Frame(parent)
        heading.pack(fill="x", pady=(0, 12))
        ttk.Label(heading, text="Virtual Board", font=(self.ui_font, -18, "bold")).pack(
            side="left"
        )
        self.observe_outputs = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            heading, text="Show Transitions", variable=self.observe_outputs
        ).pack(side="right", padx=(10, 0))
        self.board_summary = ttk.Label(heading, style="Muted.TLabel")
        self.board_summary.pack(side="right")
        card, top = self.board_card(
            parent,
            "Digital I/O",
            "LEDs light on a low signal. Switches set high (1) or low (0).",
            "leds",
        )
        card.pack(fill="x", pady=(0, 10))
        self.led_readout = ttk.Label(top, style="BoardValue.TLabel", anchor="center")
        self.led_canvas = tk.Canvas(
            top, height=60, background=theme.INPUT, highlightthickness=0
        )
        self.led_canvas.pack(fill="x")
        self.led_readout.pack(fill="x", pady=(6, 4))
        self.led_canvas.bind("<Configure>", lambda event: self.draw_leds())
        switch = ttk.Frame(top, style="Board.TFrame")
        switch.pack(fill="x", pady=(4, 0))
        self.switch_vars = []
        self.switch_buttons = {}
        for column, bit in enumerate(range(7, -1, -1)):
            switch.columnconfigure(column, weight=1, uniform="switches")
            var = tk.BooleanVar(value=True)
            self.switch_vars.insert(0, var)
            button = ttk.Checkbutton(
                switch,
                text=f"{bit} · 1",
                variable=var,
                command=self.switch_changed,
                style="Switch.TCheckbutton",
            )
            button.grid(row=0, column=column, sticky="ew", padx=2)
            self.switch_buttons[bit] = button
        card, top = self.board_card(
            parent,
            "7-Segment Display",
            "Four multiplexed digits · only the selected digit is driven",
            "display",
        )
        card.pack(fill="x", pady=(0, 12))
        self.segment_canvas = tk.Canvas(
            top, height=98, background=theme.INPUT, highlightthickness=0
        )
        self.segment_canvas.pack(fill="x")
        self.segment_canvas.bind("<Configure>", lambda event: self.draw_segments())
        tabs = ttk.Notebook(parent)
        self.peripheral_tabs = tabs
        tabs.pack(fill="both", expand=True)
        peripherals, terminal, hardware = (
            ttk.Frame(tabs, padding=10),
            ttk.Frame(tabs, padding=10),
            ttk.Frame(tabs, padding=10),
        )
        tabs.add(peripherals, text="Peripherals")
        tabs.add(terminal, text="UART")
        tabs.add(hardware, text="Hardware")
        self.hardware_tab = hardware
        devices = FlowGrid(peripherals, min_width=220, max_columns=2)
        devices.pack(fill="x")
        card, keypad = self.board_card(
            devices,
            "Keypad",
            "Choose Hold, Toggle, or Radio in Experiment Settings.",
            "keypad",
        )
        devices.add(card)
        self.keypad_buttons = []
        labels = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["*", "0", "#"]]
        for row in range(4):
            for col in range(3):
                button = ttk.Button(
                    keypad, text=labels[row][col], width=4, style="Keypad.TButton"
                )
                button.grid(row=row, column=col, padx=3, pady=3)
                self.keypad_buttons.append(button)
                # Map visual keypad order to the board row/column wiring.
                key = (3 - row, 2 - col)
                button.bind("<ButtonPress-1>", lambda e, k=key: self.key(k, True))
                button.bind("<ButtonRelease-1>", lambda e, k=key: self.key(k, False))
                button.bind("<KeyPress-space>", lambda e, k=key: self.key(k, True))
                button.bind("<KeyRelease-space>", lambda e, k=key: self.key(k, False))
                button.bind("<FocusOut>", lambda e, k=key: self.key(k, False))
        gate = tk.BooleanVar(value=self.board.key_gate)
        self.key_gate_var = gate
        ttk.Checkbutton(
            keypad,
            text="Interrupt Gate",
            variable=gate,
            command=self.key_gate_changed,
        ).grid(row=4, column=0, columnspan=3, pady=(8, 0))
        for column in range(3):
            keypad.columnconfigure(column, weight=1)
        card, motor = self.board_card(
            devices, "DC Motor", "Direction and shaft position", "motor"
        )
        devices.add(card)
        self.motor_canvas = tk.Canvas(
            motor, width=150, height=140, background=theme.INPUT, highlightthickness=0
        )
        self.motor_canvas.pack(fill="x")
        self.motor_canvas.bind("<Configure>", lambda event: self.draw_motor())
        self.motor_text = ttk.Label(
            motor, text="Stopped", style="BoardValue.TLabel", anchor="center"
        )
        self.motor_text.pack(fill="x")
        card, analogue = self.board_card(
            peripherals,
            "Analogue Signals",
            "Input: 0–5 V · comparator reference follows DAC output",
            "adc",
        )
        card.pack(fill="x", pady=10)
        self.analogue = tk.DoubleVar(value=0)
        ttk.Scale(
            analogue,
            from_=0,
            to=5,
            variable=self.analogue,
            command=self.analogue_changed,
        ).pack(fill="x")
        self.analogue_text = ttk.Label(
            analogue, text="0.00 V", style="BoardValue.TLabel"
        )
        self.analogue_text.pack(anchor="w")
        self.dac_text = ttk.Label(analogue, text="", style="BoardMuted.TLabel")
        self.dac_text.pack(anchor="w", pady=(8, 0))
        self.dac_text.configure(cursor="hand2")
        self.dac_text.bind("<Button-1>", lambda event: self.wiring_window("dac"))
        card, lcd = self.board_card(
            peripherals, "LCD", "16 × 2 character display · enable in Hardware", "lcd"
        )
        card.pack(fill="x")
        self.lcd_canvas = tk.Canvas(
            lcd, height=78, background="#233C37", highlightthickness=0
        )
        self.lcd_canvas.pack(fill="x")
        self.lcd_canvas.bind("<Configure>", lambda event: self.draw_lcd())
        self.lcd_status = ttk.Label(
            lcd, text="Ready", style="Muted.TLabel", wraplength=400
        )
        self.lcd_status.pack(fill="x", pady=5)
        ttk.Button(
            terminal,
            text="Serial Terminal",
            style="Footer.TButton",
            command=lambda: self.wiring_window("uart"),
        ).pack(anchor="w")
        ttk.Label(terminal, text="Received From 8051", style="Muted.TLabel").pack(
            anchor="w", pady=(4, 8)
        )
        transcript = ttk.Frame(terminal)
        transcript.pack(fill="both", expand=True)
        self.uart_output = tk.Text(
            transcript,
            height=12,
            font=(self.mono_font, -12),
            state="disabled",
            wrap="none",
        )
        horizontal = ttk.Scrollbar(
            transcript, orient="horizontal", command=self.uart_output.xview
        )
        horizontal.pack(side="bottom", fill="x")
        self.uart_output.configure(xscrollcommand=horizontal.set)
        output_scroll = ttk.Scrollbar(transcript, command=self.uart_output.yview)
        output_scroll.pack(side="right", fill="y")
        self.uart_output.configure(
            yscrollcommand=output_scroll.set, borderwidth=0, padx=10, pady=10
        )
        self.uart_output.pack(side="left", fill="both", expand=True)
        send = ttk.Frame(terminal)
        send.pack(fill="x", pady=8)
        self.uart_input = ttk.Entry(send)
        self.uart_input.pack(side="left", fill="x", expand=True)
        self.uart_input.bind("<Return>", lambda event: self.uart_receive())
        ttk.Button(send, text="Transmit To 8051", command=self.uart_receive).pack(
            side="left", padx=5
        )
        uart_controls = ttk.Frame(terminal)
        uart_controls.pack(fill="x")
        ttk.Label(uart_controls, text="Baud").pack(side="left")
        ttk.Button(
            uart_controls,
            text="Clear Output",
            command=self.clear_uart_output,
            style="Footer.TButton",
        ).pack(side="right")
        self.baud = tk.StringVar(value="4800")
        self.parity = tk.StringVar(value="None")
        ttk.Combobox(
            uart_controls,
            textvariable=self.baud,
            values=["1200", "2400", "4800", "9600", "19200"],
            width=8,
            state="readonly",
        ).pack(side="left", padx=5)
        ttk.Label(uart_controls, text="Parity").pack(side="left", padx=(8, 4))
        ttk.Combobox(
            uart_controls,
            textvariable=self.parity,
            values=["None", "Odd", "Even"],
            width=7,
            state="readonly",
        ).pack(side="left")
        framing = ttk.Frame(terminal)
        framing.pack(fill="x", pady=6)
        self.data_bits = tk.StringVar(value="8")
        self.stop_bits = tk.StringVar(value="1")
        for label, var, values in [
            ("Data Bits", self.data_bits, ["7", "8"]),
            ("Stop Bits", self.stop_bits, ["1", "2"]),
        ]:
            ttk.Label(framing, text=label).pack(side="left", padx=(0, 4))
            ttk.Combobox(
                framing, textvariable=var, values=values, width=3, state="readonly"
            ).pack(side="left", padx=(0, 8))
        ttk.Button(framing, text="Apply Framing", command=self.apply_uart).pack(
            side="left"
        )
        ttk.Button(framing, text="Reset Link", command=self.reset_uart_link).pack(
            side="left", padx=6
        )
        self.uart_status = ttk.Label(
            terminal, text="", style="Muted.TLabel", wraplength=420
        )
        self.uart_status.pack(anchor="w")
        ttk.Label(
            terminal,
            text="Sending enables UART. Text appends CR; {41,42} sends hexadecimal bytes.",
            wraplength=400,
        ).pack(anchor="w", pady=8)
        ttk.Label(
            hardware,
            text="Enable the peripherals used by your program. Shared pins can affect each other.",
            wraplength=420,
        ).pack(anchor="w", pady=(0, 10))
        ttk.Button(
            hardware, text="Experiment Settings…", command=self.experiment_window
        ).pack(anchor="w", pady=(0, 10))
        self.hardware_toggles = FlowGrid(hardware)
        self.hardware_toggles.pack(fill="x", pady=(0, 12))
        labels = {
            "leds": "LEDs",
            "display": "7-Segment",
            "adc": "ADC",
            "dac": "DAC",
            "lcd": "LCD",
            "uart": "UART",
        }
        for name, value in self.board.enabled.items():
            var = tk.BooleanVar(value=value)
            self.enabled_vars[name] = var
            toggle = ttk.Checkbutton(
                self.hardware_toggles,
                text=labels.get(name, name.replace("_", " ").title()),
                variable=var,
                command=self.hardware_changed,
                style="Hardware.TCheckbutton",
            )
            self.hardware_toggles.add(toggle)
        ttk.Button(
            hardware, text="Wiring And Shared Pins…", command=self.wiring_window
        ).pack(anchor="w", pady=10)
        card, ports = self.board_card(
            hardware,
            "Port Signals",
            "Latch is the written value; pins show the effective input level. Bits run 7 → 0.",
        )
        card.pack(fill="x", pady=(4, 0))
        for column, title in enumerate(("Port", "Latch", "Pins")):
            ttk.Label(ports, text=title, style="BoardMuted.TLabel").grid(
                row=0, column=column, sticky="w", padx=8, pady=(0, 6)
            )
            ports.columnconfigure(column, weight=1 if column else 0)
        self.port_values = {}
        for n in range(4):
            ttk.Label(ports, text=f"P{n}", style="BoardValue.TLabel").grid(
                row=n + 1, column=0, padx=8, pady=8
            )
            values = []
            for column in (1, 2):
                label = ttk.Label(ports, style="BoardValue.TLabel")
                label.grid(row=n + 1, column=column, sticky="w", padx=8, pady=8)
                values.append(label)
            self.port_values[n] = values

        def size_selected_tab(event=None):
            selected = tabs.select()
            if selected:
                height = tabs.nametowidget(selected).winfo_reqheight()
                if int(tabs.cget("height")) != height:
                    tabs.configure(height=height)

        tabs.bind(
            "<<NotebookTabChanged>>", lambda event: tabs.after_idle(size_selected_tab)
        )
        self.hardware_toggles.bind(
            "<<FlowLayoutChanged>>", lambda event: tabs.after_idle(size_selected_tab)
        )
        devices.bind(
            "<<FlowLayoutChanged>>", lambda event: tabs.after_idle(size_selected_tab)
        )
        tabs.after_idle(size_selected_tab)

    def key_gate_changed(self):
        self.board.key_gate = self.key_gate_var.get()
        self.board.update()
        self.refresh()

    def clear_uart_output(self):
        self.uart_output.configure(state="normal")
        self.uart_output.delete("1.0", "end")
        self.uart_output.configure(state="disabled")
        self.uart_position = self.board.uart.received_dropped + len(
            self.board.uart.received
        )

    def update_board(self):
        enabled = sum(self.board.enabled.values())
        self.board_summary.configure(
            text=f"{enabled} / {len(self.board.enabled)} enabled"
        )
        for device, badge in self.board_badges.items():
            active = self.board.enabled[device]
            badge.configure(
                text="● Enabled" if active else "○ Disabled",
                foreground=theme.MINT if active else theme.MUTED,
            )
        for bit, button in self.switch_buttons.items():
            button.configure(text=f"{bit} · {int(self.switch_vars[bit].get())}")
            button.state(
                ["!disabled" if self.board.enabled["switches"] else "disabled"]
            )
        for index, button in enumerate(self.keypad_buttons):
            key = (3 - index // 3, 2 - index % 3)
            button.state(["pressed" if key in self.board.keys else "!pressed"])
            button.state(["!disabled" if self.board.enabled["keypad"] else "disabled"])
        self.draw_leds()
        self.draw_segments()
        self.draw_motor()
        self.draw_lcd()
        uart = self.board.uart
        self.uart_status.configure(
            text=f"{uart.baud} Baud · {uart.framing} · Errors {sum(uart.errors.values())}"
            + (f" · {uart.last_error}" if uart.last_error else "")
        )
        adc = (
            f"{self.board.adc_value:02X} · {'Converting' if self.board.adc_remaining else 'Idle'}"
            if self.board.enabled["adc"]
            else "Disabled"
        )
        dac = (
            f"{self.board.dac_value * 5 / 255:.3f} V"
            if self.board.enabled["dac"]
            else "Disabled"
        )
        self.dac_text.configure(text=f"ADC  {adc}     DAC  {dac}")
        for n, labels in self.port_values.items():
            address = 0x80 + n * 16
            for label, value in zip(
                labels, (self.cpu.ram[address], self.cpu.read(address))
            ):
                bits = f"{value:08b}"
                label.configure(text=f"{bits[:4]} {bits[4:]}  · {value:02X}")

    def draw_leds(self):
        canvas = self.led_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1)
        pattern = self.board.led_mask
        bits = f"{pattern:08b}"
        self.led_readout.configure(
            text=f"Lit LEDs  {bits[:4]} {bits[4:]}  ·  {pattern} decimal"
        )
        for column, bit in enumerate(range(7, -1, -1)):
            x = (column + 0.5) * width / 8
            active = bool(self.board.led_mask & (1 << bit))
            canvas.create_oval(
                x - 10,
                3,
                x + 10,
                23,
                fill=theme.MINT if active else theme.BORDER,
                outline="",
            )
            canvas.create_text(
                x,
                38,
                text=f"LED {bit}",
                fill=theme.TEXT if active else theme.MUTED,
                font=(self.ui_font, -10),
            )
            canvas.create_text(
                x,
                52,
                text=self.board.mapping["leds"][bit],
                fill=theme.MUTED,
                font=(self.mono_font, -9),
            )

    def draw_segments(self):
        c = self.segment_canvas
        c.delete("all")
        lines = [
            (9, 3, 35, 3),
            (38, 6, 38, 28),
            (38, 34, 38, 56),
            (9, 59, 35, 59),
            (6, 34, 6, 56),
            (6, 6, 6, 28),
            (9, 31, 35, 31),
        ]
        for digit in range(4):
            x = (digit + 0.5) * max(c.winfo_width(), 1) / 4 - 26
            v = self.board.digits[3 - digit]
            for bit, (a, b, d, e) in enumerate(lines):
                c.create_line(
                    x + a,
                    b + 8,
                    x + d,
                    e + 8,
                    width=5,
                    fill="#78E4BB"
                    if not v >> bit & 1 and self.board.enabled["display"]
                    else "#303D55",
                    capstyle="round",
                )
            c.create_oval(
                x + 45,
                62,
                x + 51,
                68,
                fill=theme.MINT
                if not v & 128 and self.board.enabled["display"]
                else theme.BORDER,
                outline="",
            )
            c.create_text(
                x + 23,
                83,
                text=f"D{3 - digit}",
                font=(self.ui_font, -10),
                fill="#92A1B9",
            )

    def draw_motor(self):
        c = self.motor_canvas
        c.delete("all")
        c.create_oval(30, 15, 140, 125, fill="#121B29", outline="#303D55", width=2)
        offset = (max(c.winfo_width(), 170) - 170) / 2
        a = math.radians(self.board.motor_angle)
        x = 85 + 45 * math.cos(a)
        y = 70 + 45 * math.sin(a)
        c.create_line(85, 70, x, y, width=5, fill="#A598F8")
        c.create_oval(79, 64, 91, 76, fill="#92A1B9", outline="")
        c.move("all", offset, 0)
        self.motor_text.configure(
            text={-1: "↶ Counterclockwise", 0: "Stopped", 1: "↷ Clockwise"}[
                self.board.motor_direction
            ]
            if self.board.enabled["motor"]
            else "Disabled"
        )
