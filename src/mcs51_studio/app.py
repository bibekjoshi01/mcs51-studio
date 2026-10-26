"""Local Python/Tk desktop workbench for the reconstructed simulator."""

import json
import math
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font, messagebox, simpledialog, ttk

from .assembler import AssemblyError, assemble, export_hex, import_hex
from .board import DEFAULT_MAPPING, Board, pin
from .config import save_shortcut, settings_path
from .core import CPU, ISA, SFR
from .metadata import APP_NAME, VERSION
from .resources import LED_COUNTER


class App:
    def __init__(self, root):
        self.root = root
        root.title(f"{APP_NAME} — 8051 Workbench")
        width = max(800, min(1370, root.winfo_screenwidth() - 80))
        height = max(600, min(900, root.winfo_screenheight() - 100))
        root.geometry(f"{width}x{height}")
        root.minsize(min(1120, width), min(750, height))
        self.ui_font = font.nametofont("TkDefaultFont").actual("family")
        self.mono_font = font.nametofont("TkFixedFont").actual("family")
        self.cpu = CPU()
        self.board = Board(self.cpu)
        self.program = None
        self.running = False
        self.breakpoints = set()
        self.path = None
        self.dirty = False
        self.uart_position = 0
        self.settings_path = settings_path()
        self.load_settings()
        self.status = tk.StringVar(value="Ready · assemble the example to begin")
        self.speed = tk.StringVar(value="1000")
        self.reg_vars = {}
        self.port_labels = {}
        self.enabled_vars = {}
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f2f4f7")
        style.configure("TLabel", background="#f2f4f7", foreground="#172b42")
        style.configure("TLabelframe", background="#f2f4f7")
        style.configure(
            "TLabelframe.Label",
            background="#f2f4f7",
            foreground="#172b42",
            font=(self.ui_font, 11, "bold"),
        )
        style.configure("TButton", padding=5)
        self.build_menu()
        self.build_toolbar()
        content = ttk.Panedwindow(root, orient="horizontal")
        content.pack(fill="both", expand=True, padx=10, pady=5)
        left, right = ttk.Frame(content), ttk.Frame(content)
        content.add(left, weight=5)
        content.add(right, weight=4)
        self.build_editor(left)
        self.build_machine(left)
        self.build_board(right)
        ttk.Label(root, textvariable=self.status, padding=(12, 7)).pack(fill="x")
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<F5>", lambda e: self.toggle_run())
        root.bind("<F7>", lambda e: self.step())
        root.bind(
            save_shortcut(root.tk.call("tk", "windowingsystem")), self.save_shortcut
        )
        self.editor.insert("1.0", LED_COUNTER)
        self.editor.edit_modified(False)
        self.refresh()

    def save_shortcut(self, event=None):
        self.save_source()
        return "break"

    def build_menu(self):
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)
        file = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="File", menu=file)
        for text, command in [
            ("Open assembly / HEX…", self.open_file),
            ("Save assembly", self.save_source),
            ("Save assembly as…", lambda: self.save_source(True)),
            ("Export Intel HEX…", self.export),
        ]:
            file.add_command(label=text, command=command)
        file.add_separator()
        file.add_command(label="Quit", command=self.close)
        tools = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Tools", menu=tools)
        tools.add_command(label="Pin mappings…", command=self.mapping_dialog)
        tools.add_command(label="Oscilloscope", command=self.scope_window)
        tools.add_command(label="Instruction inventory", command=self.isa_window)
        help_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About and verification scope", command=self.about)

    def build_toolbar(self):
        bar = ttk.Frame(self.root, padding=10)
        bar.pack(fill="x")
        ttk.Label(bar, text=APP_NAME.upper(), font=(self.ui_font, 15, "bold")).pack(
            side="left", padx=(0, 25)
        )
        for text, command in [
            ("Open", self.open_file),
            ("Assemble", self.assemble),
            ("Step  F7", self.step),
            ("Run / Pause  F5", self.toggle_run),
            ("Reset", self.reset),
        ]:
            ttk.Button(bar, text=text, command=command).pack(side="left", padx=3)
        ttk.Label(bar, text="Instructions / batch").pack(side="left", padx=(20, 5))
        ttk.Combobox(
            bar,
            textvariable=self.speed,
            values=["1", "10", "100", "1000", "10000"],
            width=7,
            state="readonly",
        ).pack(side="left")

    def build_editor(self, parent):
        box = ttk.LabelFrame(parent, text="Assembly editor", padding=8)
        box.pack(fill="both", expand=True, pady=(0, 6))
        self.editor = tk.Text(
            box,
            undo=True,
            wrap="none",
            font=(self.mono_font, 12),
            background="#ffffff",
            foreground="#152b42",
            insertbackground="#152b42",
            height=19,
        )
        self.editor.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(box, command=self.editor.yview)
        scroll.pack(side="right", fill="y")
        self.editor.configure(yscrollcommand=scroll.set)
        self.editor.tag_configure("pc", background="#d9edff")
        self.editor.bind("<<Modified>>", self.edited)
        listing = ttk.LabelFrame(
            parent,
            text="Program listing · double-click a row to toggle a breakpoint",
            padding=5,
        )
        listing.pack(fill="x", pady=5)
        self.listing = ttk.Treeview(
            listing, columns=("pc", "bytes", "source"), show="headings", height=5
        )
        for col, width in [("pc", 75), ("bytes", 100), ("source", 450)]:
            self.listing.heading(col, text=col.upper())
            self.listing.column(col, width=width, stretch=col == "source")
        self.listing.pack(fill="x")
        self.listing.bind("<Double-1>", self.breakpoint)
        self.listing.tag_configure("pc", background="#d9edff")
        self.listing.tag_configure("break", foreground="#b33b30")

    def build_machine(self, parent):
        registers = ttk.LabelFrame(
            parent, text="Processor · edit a value and press Enter", padding=5
        )
        registers.pack(fill="x", pady=5)
        names = ["PC", "ACC", "B", "PSW", "SP", "DPL", "DPH"] + [
            f"R{i}" for i in range(8)
        ]
        for i, name in enumerate(names):
            col, row = i % 8, (i // 8) * 2
            ttk.Label(registers, text=name).grid(row=row, column=col, padx=5)
            var = tk.StringVar()
            self.reg_vars[name] = var
            entry = ttk.Entry(
                registers, textvariable=var, width=5, font=(self.mono_font, 11)
            )
            entry.grid(row=row + 1, column=col, padx=5, pady=2)
            entry.bind("<Return>", lambda e, n=name: self.edit_register(n))
        self.flags = ttk.Label(registers, text="")
        self.flags.grid(row=4, column=0, columnspan=8, pady=4)
        mem = ttk.LabelFrame(
            parent, text="Memory · double-click a byte to edit RAM", padding=5
        )
        mem.pack(fill="both", expand=True)
        head = ttk.Frame(mem)
        head.pack(fill="x")
        self.memory_kind = tk.StringVar(value="RAM")
        ttk.Combobox(
            head,
            textvariable=self.memory_kind,
            values=["RAM", "SFR", "Code"],
            width=7,
            state="readonly",
        ).pack(side="left")
        self.memory_start = tk.StringVar(value="0000")
        ttk.Label(head, text="Code start (hex)").pack(side="left", padx=8)
        ttk.Entry(head, textvariable=self.memory_start, width=7).pack(side="left")
        ttk.Button(head, text="Refresh", command=self.refresh).pack(side="left", padx=5)
        self.memory = ttk.Treeview(
            mem,
            columns=["addr"] + [str(i) for i in range(16)],
            show="headings",
            height=6,
        )
        self.memory.heading("addr", text="ADDR")
        self.memory.column("addr", width=48, stretch=False)
        for i in range(16):
            self.memory.heading(str(i), text=f"{i:X}")
            self.memory.column(str(i), width=32, stretch=True)
        self.memory.pack(fill="both", expand=True)
        self.memory.bind("<Double-1>", self.edit_memory)

    def build_board(self, parent):
        top = ttk.LabelFrame(parent, text="Virtual training board", padding=8)
        top.pack(fill="x", pady=(0, 6))
        self.led_canvas = tk.Canvas(
            top, height=49, background="#f2f4f7", highlightthickness=0
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
            top, height=92, background="#f2f4f7", highlightthickness=0
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
                # Physical row/column order in the recovered board is reversed.
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
            motor, width=170, height=155, background="#f2f4f7", highlightthickness=0
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
            font=(self.mono_font, 20),
            background="#dce7ba",
            foreground="#263522",
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
            font=(self.mono_font, 12),
            state="disabled",
            wrap="word",
        )
        self.uart_output.pack(fill="both", expand=True)
        send = ttk.Frame(terminal)
        send.pack(fill="x", pady=8)
        self.uart_input = ttk.Entry(send)
        self.uart_input.pack(side="left", fill="x", expand=True)
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
            label = ttk.Label(hardware, text="", font=(self.mono_font, 11))
            label.pack(anchor="w", pady=2)
            self.port_labels[n] = label

    def edited(self, event=None):
        if self.editor.edit_modified():
            self.dirty = True
            self.running = False
            self.editor.edit_modified(False)
            self.status.set("Source changed · assemble before execution")

    def assemble(self):
        self.running = False
        try:
            self.program = assemble(self.editor.get("1.0", "end-1c"))
        except AssemblyError as e:
            messagebox.showerror("Assembly error", str(e))
            return False
        self.reset()
        self.dirty = False
        self.populate_listing()
        self.refresh()
        self.status.set(
            f"Assembled {len(self.program.used)} bytes · {len(self.program.locations)} source statements"
        )
        return True

    def reset(self):
        self.running = False
        mapping = self.board.mapping
        enabled = self.board.enabled.copy()
        self.cpu.reset()
        self.board = Board(self.cpu, mapping)
        self.board.enabled.update(enabled)
        if self.program:
            self.cpu.code[:] = self.program.code
        self.uart_position = 0
        self.board.switches = [v.get() for v in self.switch_vars]
        self.board.update()
        self.refresh()
        self.status.set("Reset · PC 0000")

    def step_once(self):
        op = self.cpu.step()
        self.board.update()
        return op

    def step(self):
        self.running = False
        if self.dirty or not self.program:
            if not self.assemble():
                return
        try:
            op = self.step_once()
            self.status.set(
                f"{ISA[op]['display']} · {self.cpu.instructions:,} instructions · {self.cpu.cycles:,} machine cycles"
            )
        except Exception as e:
            messagebox.showerror("Execution stopped", str(e))
        self.refresh()

    def toggle_run(self):
        if self.running:
            self.running = False
            self.status.set("Paused")
            self.refresh()
            return
        if self.dirty or not self.program:
            if not self.assemble():
                return
        self.running = True
        self.run_batch()

    def run_batch(self):
        if not self.running:
            return
        try:
            deadline = time.monotonic() + 0.025
            for _ in range(int(self.speed.get())):
                self.step_once()
                if self.cpu.pc in self.breakpoints:
                    self.running = False
                    break
                if time.monotonic() > deadline:
                    break
            self.status.set(
                f"{'Running' if self.running else 'Breakpoint'} · PC {self.cpu.pc:04X} · {self.cpu.instructions:,} instructions · {self.cpu.cycles:,} machine cycles"
            )
        except Exception as e:
            self.running = False
            messagebox.showerror("Execution stopped", str(e))
        self.refresh()
        if self.running:
            self.root.after(10, self.run_batch)

    def populate_listing(self):
        self.listing.delete(*self.listing.get_children())
        if not self.program:
            return
        entries = self.program.locations or {
            p: {
                "source": ISA[self.cpu.code[p]]["display"],
                "size": ISA[self.cpu.code[p]]["size"],
                "line": 0,
            }
            for p in sorted(self.program.used)[:2000]
        }
        for address, entry in entries.items():
            data = " ".join(
                f"{b:02X}" for b in self.cpu.code[address : address + entry["size"]]
            )
            self.listing.insert(
                "",
                "end",
                iid=str(address),
                values=(f"{address:04X}", data, entry["source"]),
            )

    def breakpoint(self, event):
        row = self.listing.identify_row(event.y)
        if row:
            address = int(row)
            if address in self.breakpoints:
                self.breakpoints.remove(address)
            else:
                self.breakpoints.add(address)
            self.refresh()

    def edit_register(self, name):
        self.running = False
        try:
            value = int(self.reg_vars[name].get(), 16)
            if name == "PC":
                if not 0 <= value <= 65535:
                    raise ValueError()
                self.cpu.pc = value
            else:
                if not 0 <= value <= 255:
                    raise ValueError()
                if name.startswith("R") and name[1:].isdigit():
                    self.cpu.set_reg(int(name[1:]), value)
                else:
                    self.cpu.write(SFR[name], value)
            self.board.update()
            self.refresh()
        except ValueError:
            messagebox.showerror(
                "Invalid value", "Enter a hexadecimal value within the register range."
            )

    def edit_memory(self, event):
        if self.running:
            return
        row = self.memory.identify_row(event.y)
        col = self.memory.identify_column(event.x)
        if not row or not col or col == "#1":
            return
        address = int(row) + int(col[1:]) - 2
        value = simpledialog.askstring(
            "Edit memory",
            f"Address {address:04X}, new hexadecimal byte:",
            parent=self.root,
        )
        if value is None:
            return
        try:
            n = int(value, 16)
            if not 0 <= n <= 255:
                raise ValueError()
            if self.memory_kind.get() == "Code":
                self.cpu.code[address] = n
            else:
                self.cpu.write(address, n)
            self.board.update()
            self.refresh()
        except ValueError:
            messagebox.showerror("Invalid byte", "Use a value from 00 to FF.")

    def refresh(self):
        if not hasattr(self, "memory"):
            return
        focus = self.root.focus_get()
        for name, var in self.reg_vars.items():
            if isinstance(focus, ttk.Entry) and str(focus.cget("textvariable")) == str(
                var
            ):
                continue
            value = (
                self.cpu.pc
                if name == "PC"
                else self.cpu.reg(int(name[1:]))
                if name.startswith("R") and name[1:].isdigit()
                else self.cpu.ram[SFR[name]]
            )
            var.set(f"{value:04X}" if name == "PC" else f"{value:02X}")
        self.flags.configure(
            text="   ".join(
                f"{n}={(self.cpu.ram[0xD0] >> b) & 1}"
                for n, b in [
                    ("CY", 7),
                    ("AC", 6),
                    ("F0", 5),
                    ("RS1", 4),
                    ("RS0", 3),
                    ("OV", 2),
                    ("P", 0),
                ]
            )
        )
        kind = self.memory_kind.get()
        try:
            start = (
                int(self.memory_start.get(), 16) & 0xFF80
                if kind == "Code"
                else 128
                if kind == "SFR"
                else 0
            )
        except ValueError:
            start = 0
        self.memory.delete(*self.memory.get_children())
        for addr in range(start, min(start + 128, 65536), 16):
            data = (
                self.cpu.code[addr : addr + 16]
                if kind == "Code"
                else self.cpu.ram[addr : addr + 16]
            )
            self.memory.insert(
                "",
                "end",
                iid=str(addr),
                values=[f"{addr:04X}"] + [f"{b:02X}" for b in data],
            )
        for row in self.listing.get_children():
            addr = int(row)
            self.listing.item(
                row,
                tags=("pc",)
                if addr == self.cpu.pc
                else ("break",)
                if addr in self.breakpoints
                else (),
            )
            values = list(self.listing.item(row, "values"))
            values[0] = ("● " if addr in self.breakpoints else "") + f"{addr:04X}"
            self.listing.item(row, values=values)
        self.editor.tag_remove("pc", "1.0", "end")
        if self.program and self.cpu.pc in self.program.locations:
            line = self.program.locations[self.cpu.pc]["line"]
            self.editor.tag_add("pc", f"{line}.0", f"{line}.end")
            if str(self.cpu.pc) in self.listing.get_children():
                self.listing.see(str(self.cpu.pc))
        canvas = self.led_canvas
        canvas.delete("all")
        for i in range(8):
            bit = 7 - i
            high = self.board.read_pin(self.board.mapping["leds"][bit])
            x = 12 + i * 58
            canvas.create_oval(
                x,
                4,
                x + 22,
                26,
                fill="#d84435"
                if not high and self.board.enabled["leds"]
                else "#b8c0c8",
                outline="",
            )
            canvas.create_text(
                x + 11, 39, text=f"LED{bit}", fill="#34465a", font=(self.ui_font, 9)
            )
        self.draw_segments()
        self.draw_motor()
        self.lcd_text.configure(text="\n".join(self.board.lcd.lines()))
        self.dac_text.configure(
            text=f"DAC {self.board.dac_value * 5 / 255:.3f} V  ·  ADC {self.board.adc_value:02X}  ·  {'Converting' if self.board.adc_remaining else 'Idle'}"
        )
        for n, label in self.port_labels.items():
            addr = 0x80 + n * 16
            label.configure(
                text=f"P{n}  latch {self.cpu.ram[addr]:08b}   pins {self.cpu.read(addr):08b}"
            )
        if self.uart_position < len(self.board.uart.received):
            data = self.board.uart.received[self.uart_position :]
            self.uart_position = len(self.board.uart.received)
            self.uart_output.configure(state="normal")
            self.uart_output.insert(
                "end",
                "".join(
                    chr(v) if 32 <= v < 127 or v in (10, 13) else f"<{v:02X}>"
                    for v in data
                ),
            )
            self.uart_output.see("end")
            self.uart_output.configure(state="disabled")

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
                    fill="#d84435"
                    if not v >> bit & 1 and self.board.enabled["display"]
                    else "#d5dbe0",
                    capstyle="round",
                )
            c.create_oval(
                x + 45,
                62,
                x + 51,
                68,
                fill="#d84435" if not v & 128 else "#d5dbe0",
                outline="",
            )
            c.create_text(
                x + 23,
                83,
                text=f"Display {3 - digit}",
                font=(self.ui_font, 9),
                fill="#34465a",
            )

    def draw_motor(self):
        c = self.motor_canvas
        c.delete("all")
        c.create_oval(30, 15, 140, 125, fill="#e1e7ed", outline="#76899a", width=2)
        a = math.radians(self.board.motor_angle)
        x = 85 + 45 * math.cos(a)
        y = 70 + 45 * math.sin(a)
        c.create_line(85, 70, x, y, width=5, fill="#246b9e")
        c.create_oval(79, 64, 91, 76, fill="#34465a", outline="")
        self.motor_text.configure(
            text={-1: "Counterclockwise", 0: "Stopped", 1: "Clockwise"}[
                self.board.motor_direction
            ]
        )

    def switch_changed(self):
        self.board.switches = [v.get() for v in self.switch_vars]
        self.board.update()
        self.refresh()

    def key(self, key, pressed):
        if pressed:
            self.board.keys.add(key)
        else:
            self.board.keys.discard(key)
        self.board.update()
        self.refresh()

    def hardware_changed(self):
        self.board.enabled.update({k: v.get() for k, v in self.enabled_vars.items()})
        self.board.update()
        self.refresh()

    def analogue_changed(self, value):
        self.board.analogue = float(value)
        self.analogue_text.configure(
            text=f"{float(value):.2f} V · comparator reference = DAC"
        )

    def uart_receive(self):
        self.board.enabled["uart"] = True
        self.enabled_vars["uart"].set(True)
        self.board.uart.configure(
            int(self.baud.get()),
            ["None", "Odd", "Even"].index(self.parity.get()),
            self.board.cycle_us,
        )
        text = self.uart_input.get()
        self.board.receive(text)
        if text:
            self.uart_input.delete(0, "end")
        self.refresh()

    def open_file(self):
        self.running = False
        path = filedialog.askopenfilename(
            filetypes=[("8051 programs", "*.asm *.a51 *.hex *.txt"), ("All files", "*")]
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
            if path.lower().endswith(".hex"):
                self.program = import_hex(text)
                self.dirty = False
                self.reset()
                self.populate_listing()
                self.status.set(f"Loaded {len(self.program.used)} HEX bytes")
                return
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", text)
            self.path = Path(path)
            self.dirty = True
            self.status.set(f"Opened {self.path.name}")
        except (OSError, ValueError) as e:
            messagebox.showerror("Open failed", str(e))

    def save_source(self, save_as=False):
        if self.path is None or save_as:
            path = filedialog.asksaveasfilename(
                defaultextension=".asm", filetypes=[("8051 assembly", "*.asm")]
            )
            if not path:
                return
            self.path = Path(path)
        try:
            self.path.write_text(self.editor.get("1.0", "end-1c"), encoding="utf-8")
            self.status.set(f"Saved {self.path.name}")
        except OSError as e:
            messagebox.showerror("Save failed", str(e))

    def export(self):
        if self.dirty or not self.program:
            if not self.assemble():
                return
        path = filedialog.asksaveasfilename(
            defaultextension=".hex", filetypes=[("Intel HEX", "*.hex")]
        )
        if path:
            try:
                Path(path).write_text(export_hex(self.program), encoding="ascii")
                self.status.set("Intel HEX exported")
            except OSError as e:
                messagebox.showerror("Export failed", str(e))

    def mapping_dialog(self):
        self.running = False
        window = tk.Toplevel(self.root)
        window.title("Pin mappings")
        window.geometry("650x650")
        canvas = tk.Canvas(window, highlightthickness=0)
        scroll = ttk.Scrollbar(window, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas, padding=10)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.create_window((0, 0), window=frame, anchor="nw")
        frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        entries = {}
        ttk.Label(
            frame,
            text="Comma-separated pins, low bit first. Example: P1.0, P1.1",
            wraplength=550,
        ).grid(row=0, column=0, columnspan=2, pady=10)
        for row, (name, pins) in enumerate(self.board.mapping.items(), 1):
            ttk.Label(frame, text=name).grid(
                row=row, column=0, sticky="w", padx=5, pady=3
            )
            entry = ttk.Entry(frame, width=48)
            entry.insert(0, ", ".join(pins))
            entry.grid(row=row, column=1, pady=3)
            entries[name] = entry

        def save():
            try:
                mapping = {
                    k: [p.strip().upper() for p in e.get().split(",")]
                    for k, e in entries.items()
                }
                for k, values in mapping.items():
                    if len(values) != len(DEFAULT_MAPPING[k]):
                        raise ValueError(f"{k} needs {len(DEFAULT_MAPPING[k])} pins")
                    for p in values:
                        pin(p)
                self.board.mapping = mapping
                self.save_settings()
                self.board.update()
                self.refresh()
                window.destroy()
            except ValueError as e:
                messagebox.showerror("Invalid mapping", str(e), parent=window)

        ttk.Button(frame, text="Apply and save", command=save).grid(
            row=len(entries) + 1, column=1, pady=15
        )

    def scope_window(self):
        window = tk.Toplevel(self.root)
        window.title("DAC oscilloscope")
        window.geometry("740x330")
        c = tk.Canvas(window, background="#ffffff")
        c.pack(fill="both", expand=True)

        def draw():
            if not window.winfo_exists():
                return
            c.delete("all")
            w, h = max(200, c.winfo_width()), max(150, c.winfo_height())
            c.create_line(45, 20, 45, h - 40, w - 20, h - 40, fill="#566675")
            for v in range(6):
                y = h - 40 - v * (h - 60) / 5
                c.create_text(24, y, text=str(v))
                c.create_line(45, y, w - 20, y, fill="#e3e7eb")
            c.create_text(w / 2, h - 15, text="Machine cycles · recent DAC samples")
            c.create_text(22, 10, text="Volts")
            data = list(self.board.scope)
            if len(data) > 1:
                lo, hi = data[0][0], data[-1][0]
                coords = []
                for t, v in data:
                    coords.extend(
                        (
                            45 + (t - lo) / max(1, hi - lo) * (w - 65),
                            h - 40 - v / 5 * (h - 60),
                        )
                    )
                c.create_line(*coords, fill="#246b9e", width=2)
            window.after(100, draw)

        draw()

    def isa_window(self):
        w = tk.Toplevel(self.root)
        w.title("Recovered instruction inventory")
        w.geometry("670x500")
        text = tk.Text(w, font=(self.mono_font, 11))
        text.pack(fill="both", expand=True)
        text.insert("end", "Opcode  Bytes  Cycles  Instruction\n\n")
        for row in ISA:
            text.insert(
                "end",
                f"{row['opcode']:02X}      {row['size']}      {row['cycles']}       {row['display']}\n",
            )
        text.configure(state="disabled")

    def load_settings(self):
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if set(data.get("mapping", {})) == set(DEFAULT_MAPPING):
                for key, values in data["mapping"].items():
                    if len(values) != len(DEFAULT_MAPPING[key]):
                        raise ValueError()
                    for value in values:
                        pin(value)
                self.board.mapping = data["mapping"]
            self.board.enabled.update(
                {
                    k: bool(v)
                    for k, v in data.get("enabled", {}).items()
                    if k in self.board.enabled
                }
            )
        except (OSError, ValueError, TypeError):
            pass

    def save_settings(self):
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps(
                {"mapping": self.board.mapping, "enabled": self.board.enabled}, indent=2
            ),
            encoding="utf-8",
        )

    def about(self):
        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME} {VERSION}\n"
            "A Python desktop workbench for the 8051.\n\n"
            "Reference-tested processor, assembler, timers, and serial engine. "
            "Peripheral and interface compatibility is still in progress.\n\n"
            "See docs/compatibility.md for scope and verification.\n\n"
            "Based on investigation of EdSim51 by James Rogers. "
            "See NOTICE.txt for attribution.",
        )

    def close(self):
        if self.dirty and not messagebox.askyesno(
            "Close", "Close with unassembled changes in the editor?"
        ):
            return
        self.running = False
        try:
            self.save_settings()
        except OSError:
            pass
        self.root.destroy()


def main():
    import argparse

    parser = argparse.ArgumentParser(description=f"{APP_NAME}: 8051 desktop workbench")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.smoke_test:
        from .smoke import run_smoke_test

        raise SystemExit(run_smoke_test())
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
