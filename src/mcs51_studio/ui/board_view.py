"""Virtual board presentation; machine behavior stays in hardware/."""

import math
import tkinter as tk
from tkinter import ttk


class BoardView:
    def build_board(self, parent):
        top = ttk.LabelFrame(parent, text="Virtual training board", padding=8)
        top.pack(fill="x", pady=(0, 8))
        self.led_canvas = tk.Canvas(
            top, height=49, background="#182131", highlightthickness=0
        )
        self.led_canvas.pack(fill="x")
        switch = ttk.Frame(top)
        switch.pack(fill="x")
        self.switch_vars = []
        for bit in range(7, -1, -1):
            var = tk.BooleanVar(value=True)
            self.switch_vars.insert(0, var)
            ttk.Checkbutton(
                switch, text=f"SW{bit}", variable=var, command=self.switch_changed
            ).pack(side="left")
        self.segment_canvas = tk.Canvas(
            top, height=92, background="#182131", highlightthickness=0
        )
        self.segment_canvas.pack(fill="x", pady=5)
        tabs = ttk.Notebook(parent)
        tabs.pack(fill="both", expand=True)
        peripherals, terminal, hardware = (
            ttk.Frame(tabs, padding=10),
            ttk.Frame(tabs, padding=10),
            ttk.Frame(tabs, padding=10),
        )
        tabs.add(peripherals, text="Peripherals")
        tabs.add(terminal, text="UART")
        tabs.add(hardware, text="Hardware")
        keypad = ttk.LabelFrame(
            peripherals, text="4 × 3 keypad · hold a key to press", padding=5
        )
        keypad.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        labels = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["*", "0", "#"]]
        for row in range(4):
            for col in range(3):
                button = ttk.Button(keypad, text=labels[row][col], width=4)
                button.grid(row=row, column=col, padx=3, pady=3)
                # Map visual keypad order to the board row/column wiring.
                key = (3 - row, 2 - col)
                button.bind("<ButtonPress-1>", lambda e, k=key: self.key(k, True))
                button.bind("<ButtonRelease-1>", lambda e, k=key: self.key(k, False))
        gate = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            keypad,
            text="Interrupt gate",
            variable=gate,
            command=lambda: setattr(self.board, "key_gate", gate.get()),
        ).grid(row=4, column=0, columnspan=3)
        motor = ttk.LabelFrame(peripherals, text="DC motor", padding=5)
        motor.grid(row=0, column=1, sticky="nsew")
        self.motor_canvas = tk.Canvas(
            motor, width=170, height=155, background="#182131", highlightthickness=0
        )
        self.motor_canvas.pack()
        self.motor_text = ttk.Label(motor, text="Stopped")
        self.motor_text.pack()
        analogue = ttk.LabelFrame(
            peripherals, text="Analogue input / comparator", padding=8
        )
        analogue.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)
        self.analogue = tk.DoubleVar(value=0)
        ttk.Scale(
            analogue,
            from_=0,
            to=5,
            variable=self.analogue,
            command=self.analogue_changed,
        ).pack(fill="x")
        self.analogue_text = ttk.Label(analogue, text="0.00 V")
        self.analogue_text.pack(anchor="w")
        lcd = ttk.LabelFrame(
            peripherals, text="LCD · enable in Hardware before use", padding=8
        )
        lcd.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.lcd_text = tk.Label(
            lcd,
            text=" " * 16 + "\n" + " " * 16,
            font=(self.mono_font, -21),
            background="#233C37",
            foreground="#A9E7C9",
            padx=10,
            pady=10,
            anchor="w",
        )
        self.lcd_text.pack(fill="x")
        self.dac_text = ttk.Label(peripherals, text="DAC 0.00 V")
        self.dac_text.grid(row=3, column=0, columnspan=2, sticky="w", pady=10)
        ttk.Button(
            peripherals, text="Open oscilloscope", command=self.scope_window
        ).grid(row=4, column=0, columnspan=2, sticky="ew")
        peripherals.columnconfigure(1, weight=1)
        self.uart_output = tk.Text(
            terminal,
            height=14,
            font=(self.mono_font, -12),
            state="disabled",
            wrap="word",
        )
        self.uart_output.pack(fill="both", expand=True)
        send = ttk.Frame(terminal)
        send.pack(fill="x", pady=8)
        self.uart_input = ttk.Entry(send)
        self.uart_input.pack(side="left", fill="x", expand=True)
        self.uart_input.bind("<Return>", lambda event: self.uart_receive())
        ttk.Button(send, text="Transmit to 8051", command=self.uart_receive).pack(
            side="left", padx=5
        )
        uart_controls = ttk.Frame(terminal)
        uart_controls.pack(fill="x")
        ttk.Label(uart_controls, text="Baud").pack(side="left")
        self.baud = tk.StringVar(value="4800")
        self.parity = tk.StringVar(value="None")
        ttk.Combobox(
            uart_controls,
            textvariable=self.baud,
            values=["1200", "2400", "4800", "9600", "19200"],
            width=8,
            state="readonly",
        ).pack(side="left", padx=5)
        ttk.Combobox(
            uart_controls,
            textvariable=self.parity,
            values=["None", "Odd", "Even"],
            width=7,
            state="readonly",
        ).pack(side="left")
        ttk.Label(
            terminal,
            text="Enable UART in Hardware. Text appends CR; {41,42} sends hexadecimal bytes.",
            wraplength=400,
        ).pack(anchor="w", pady=8)
        ttk.Label(
            hardware,
            text="Enable the peripherals used by your program. Shared pins can affect each other.",
            wraplength=420,
        ).pack(anchor="w", pady=(0, 10))
        for name, value in self.board.enabled.items():
            var = tk.BooleanVar(value=value)
            self.enabled_vars[name] = var
            ttk.Checkbutton(
                hardware,
                text=name.replace("_", " ").title(),
                variable=var,
                command=self.hardware_changed,
            ).pack(anchor="w")
        ttk.Button(
            hardware, text="Configure pin mappings…", command=self.mapping_dialog
        ).pack(anchor="w", pady=10)
        for n in range(4):
            label = ttk.Label(hardware, text="", font=(self.mono_font, -12))
            label.pack(anchor="w", pady=2)
            self.port_labels[n] = label

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
            x = 40 + digit * 105
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
                fill="#78E4BB" if not v & 128 else "#303D55",
                outline="",
            )
            c.create_text(
                x + 23,
                83,
                text=f"Display {3 - digit}",
                font=(self.ui_font, -10),
                fill="#92A1B9",
            )

    def draw_motor(self):
        c = self.motor_canvas
        c.delete("all")
        c.create_oval(30, 15, 140, 125, fill="#121B29", outline="#303D55", width=2)
        a = math.radians(self.board.motor_angle)
        x = 85 + 45 * math.cos(a)
        y = 70 + 45 * math.sin(a)
        c.create_line(85, 70, x, y, width=5, fill="#A598F8")
        c.create_oval(79, 64, 91, 76, fill="#92A1B9", outline="")
        self.motor_text.configure(
            text={-1: "Counterclockwise", 0: "Stopped", 1: "Clockwise"}[
                self.board.motor_direction
            ]
        )
