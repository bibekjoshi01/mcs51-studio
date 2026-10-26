"""Digital and DAC waveform controls, scales, cursors, and rendering."""

import tkinter as tk
from tkinter import messagebox, ttk

from ..hardware.analyzer import PINS, held_value, port_mask
from . import theme


class Waveform:
    def __init__(self, parent, app, digital):
        self.app, self.digital = app, digital
        self.probes = tk.StringVar(value="P1.0, P1.1, P3.0, P3.1")
        self.trigger = tk.StringVar(value="Free Run")
        self.edge = tk.StringVar(value="Rising")
        self.duration = tk.StringVar(value="1000")
        self.measure_pin = tk.StringVar(value="P1.0")
        self.span = None
        self.pan = tk.DoubleVar(value=100)
        self.cursors = [None, None]
        self.next_cursor = 0
        self.frozen = None
        bar = ttk.Frame(parent)
        bar.pack(fill="x")
        if digital:
            ttk.Label(bar, text="Probes").pack(side="left")
            ttk.Entry(bar, textvariable=self.probes, width=32).pack(side="left", padx=6)
            ttk.Button(bar, text="Apply", command=self.apply_probes).pack(side="left")
            ttk.Button(bar, text="Arm", command=self.arm).pack(side="right")
            ttk.Button(bar, text="Stop Capture", command=app.capture.stop).pack(
                side="right", padx=4
            )
            triggerbar = ttk.Frame(parent)
            triggerbar.pack(fill="x", pady=8)
            for label, variable, values, width in (
                ("Trigger", self.trigger, ["Free Run", *PINS], 10),
                ("Edge", self.edge, ["Rising", "Falling", "Either"], 8),
                (
                    "Post-Trigger µs",
                    self.duration,
                    ["100", "1000", "10000", "100000"],
                    9,
                ),
            ):
                ttk.Label(triggerbar, text=label).pack(side="left", padx=(0, 4))
                ttk.Combobox(
                    triggerbar,
                    textvariable=variable,
                    values=values,
                    state="readonly",
                    width=width,
                ).pack(side="left", padx=(0, 12))
            ttk.Button(triggerbar, text="Run / Pause", command=app.toggle_run).pack(
                side="right"
            )
        else:
            ttk.Label(bar, text="DAC Output · 0–5 V").pack(side="left")
            self.freeze_button = ttk.Button(bar, text="Freeze", command=self.freeze)
            self.freeze_button.pack(side="right")
        nav = ttk.Frame(parent)
        nav.pack(fill="x", pady=8)
        for label, command in [
            ("Fit", self.fit),
            ("Zoom In", lambda: self.zoom(0.5)),
            ("Zoom Out", lambda: self.zoom(2)),
            ("Clear Cursors", self.clear_cursors),
        ]:
            ttk.Button(nav, text=label, command=command).pack(side="left", padx=(0, 4))
        ttk.Label(nav, text="History").pack(side="left", padx=(8, 4))
        ttk.Scale(
            nav, from_=0, to=100, variable=self.pan, command=lambda _: self.draw()
        ).pack(side="left", fill="x", expand=True)
        self.status = tk.StringVar()
        ttk.Label(
            parent, textvariable=self.status, style="Muted.TLabel", wraplength=880
        ).pack(anchor="w")
        self.canvas = tk.Canvas(
            parent, background=theme.INPUT, highlightthickness=0, height=360
        )
        self.canvas.pack(fill="both", expand=True, pady=8)
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.canvas.bind("<Button-1>", self.place_cursor)
        self.metrics = tk.StringVar()
        ttk.Label(
            parent, textvariable=self.metrics, wraplength=880, font=(app.mono_font, -12)
        ).pack(anchor="w", pady=6)
        ttk.Label(
            parent,
            text="Click twice to place A/B cursors. Digital measurements use complete pulses in the visible range.\nInstruction-boundary samples · 1 µs machine cycle · no electrical or sub-instruction glitches.",
            style="Muted.TLabel",
        ).pack(anchor="w")
        self.channels = ["P1.0", "P1.1", "P3.0", "P3.1"]
        self.bounds = (0, 1)
        if digital:
            config = app.instrument_settings
            self.channels = list(config["probes"])
            self.probes.set(", ".join(self.channels))
            self.trigger.set(config["trigger"])
            self.edge.set(config["edge"])
            self.duration.set(str(config["duration"]))
            self.measure_pin.set(self.channels[0])

    def apply_probes(self):
        channels = [
            p.strip().upper() for p in self.probes.get().split(",") if p.strip()
        ]
        if (
            not 1 <= len(channels) <= 8
            or len(set(channels)) != len(channels)
            or any(p not in PINS for p in channels)
        ):
            messagebox.showerror(
                "Invalid Probes",
                "Choose 1–8 distinct pins, separated by commas, from P0.0 to P3.7.",
                parent=self.canvas.winfo_toplevel(),
            )
            return False
        self.channels = channels
        self.measure_pin.set(channels[0])
        self.draw()
        return True

    def arm(self):
        if not self.apply_probes():
            return
        if self.app.source_is_stale() or not self.app.program:
            if not self.app.assemble():
                return
        self.app.capture.arm(
            self.app.cpu.cycles,
            port_mask(self.app.cpu),
            None if self.trigger.get() == "Free Run" else self.trigger.get(),
            self.edge.get(),
            int(self.duration.get()),
        )
        self.fit()

    def freeze(self):
        self.frozen = list(self.app.board.scope) if self.frozen is None else None
        self.freeze_button.configure(
            text="Live" if self.frozen is not None else "Freeze"
        )
        self.draw()

    def fit(self):
        self.span = None
        self.pan.set(100)
        self.clear_cursors()

    def zoom(self, factor):
        self.span = max(1, (self.bounds[1] - self.bounds[0]) * factor)
        self.draw()

    def clear_cursors(self):
        self.cursors = [None, None]
        self.next_cursor = 0
        self.draw()

    def place_cursor(self, event):
        a, b = self.bounds
        fraction = min(
            1, max(0, (event.x - 85) / max(1, self.canvas.winfo_width() - 105))
        )
        self.cursors[self.next_cursor] = a + fraction * (b - a)
        self.next_cursor = 1 - self.next_cursor
        if self.digital:
            lane = int(
                (event.y - 30)
                / max(1, (self.canvas.winfo_height() - 65) / len(self.channels))
            )
            if 0 <= lane < len(self.channels):
                self.measure_pin.set(self.channels[lane])
        self.draw()

    def draw(self):
        c = self.canvas
        c.delete("all")
        capture = self.app.capture
        samples = (
            list(capture.samples)
            if self.digital
            else list(self.app.board.scope)
            if self.frozen is None
            else self.frozen
        )
        end = capture.end if self.digital else samples[-1][0] if samples else 0
        start = samples[0][0] if samples else 0
        total = max(1, end - start)
        span = min(total, self.span or total)
        start += (total - span) * self.pan.get() / 100
        end = start + span
        self.bounds = start, end
        w, h = max(300, c.winfo_width()), max(180, c.winfo_height())
        x = lambda time: 85 + (time - start) / span * (w - 105)
        for i in range(11):
            xx = 85 + i * (w - 105) / 10
            c.create_line(xx, 25, xx, h - 35, fill=theme.BORDER)
            c.create_text(
                xx,
                h - 18,
                text=f"{start + i * span / 10:g}",
                fill=theme.MUTED,
                font=(self.app.mono_font, -10),
            )
        c.create_text(10, h - 18, text="Time µs", anchor="w", fill=theme.MUTED)
        if self.digital:
            self.status.set(
                f"{capture.state} · {len(samples):,}/{capture.capacity:,} samples · {span / 10:g} µs/div · Click a lane to measure it"
            )
            for index, pin in enumerate(self.channels):
                lane = (h - 65) / len(self.channels)
                base = 30 + index * lane
                bit = PINS.index(pin)
                y = lambda value: base + lane * (0.75 - 0.5 * (value >> bit & 1))
                c.create_text(
                    10,
                    base + lane * 0.5,
                    text=pin,
                    anchor="w",
                    fill=theme.MINT if pin == self.measure_pin.get() else theme.TEXT,
                )
                self.trace(samples, start, end, x, y, theme.MINT)
            if (
                capture.trigger_time is not None
                and start <= capture.trigger_time <= end
            ):
                xx = x(capture.trigger_time)
                c.create_line(xx, 10, xx, h - 35, fill="#E6B870", dash=(4, 3))
                c.create_text(xx + 4, 12, text="Trigger", anchor="w", fill="#E6B870")
            measurements = capture.measurements(self.measure_pin.get(), start, end)
            fields = [
                ("high_us", "High", "µs"),
                ("low_us", "Low", "µs"),
                ("period_us", "Period", "µs"),
                ("frequency_hz", "Frequency", "Hz"),
                ("duty_percent", "Duty", "%"),
            ]
            metric = (
                self.measure_pin.get()
                + "  "
                + " · ".join(
                    f"{label} {measurements[key]:.3g} {unit}"
                    if key in measurements
                    else f"{label} —"
                    for key, label, unit in fields
                )
            )
        else:
            self.status.set(
                ("Frozen" if self.frozen is not None else "Live")
                + f" · {span / 10:g} µs/div · 1 V/div"
                + (
                    " · Enable DAC in Hardware to record output"
                    if not self.app.board.enabled["dac"]
                    else ""
                )
            )
            y = lambda value: h - 35 - value / 5 * (h - 65)
            for voltage in range(6):
                yy = y(voltage)
                c.create_line(85, yy, w - 20, yy, fill=theme.BORDER)
                c.create_text(60, yy, text=f"{voltage} V", fill=theme.MUTED)
            self.trace(samples, start, end, x, y, theme.MINT)
            metric = ""
        for label, timestamp in zip(("A", "B"), self.cursors):
            if timestamp is not None:
                if start <= timestamp <= end:
                    c.create_line(
                        x(timestamp),
                        25,
                        x(timestamp),
                        h - 35,
                        fill=theme.FOCUS,
                        dash=(3, 3),
                    )
                    c.create_text(x(timestamp), 12, text=label, fill=theme.FOCUS)
                metric += f"  {label}={timestamp:.3g} µs"
                if not self.digital:
                    value = held_value(samples, timestamp)
                    if value is not None:
                        metric += f"/{value:.3f} V"
        if all(v is not None for v in self.cursors):
            delta = abs(self.cursors[1] - self.cursors[0])
            metric += f"  Δt={delta:.3g} µs"
            if delta:
                metric += f"  1/Δt={1_000_000 / delta:.3g} Hz"
            if not self.digital:
                values = [held_value(samples, t) for t in self.cursors]
                if all(v is not None for v in values):
                    metric += f"  ΔV={values[1] - values[0]:.3f} V"
        self.metrics.set(metric or "No measurements yet.")
        if not samples:
            c.create_text(
                w / 2,
                h / 2,
                text="Arm a capture, then run or step your program."
                if self.digital
                else "Enable DAC and run a program to see its output.",
                fill=theme.MUTED,
            )

    def trace(self, samples, start, end, x, y, color):
        previous = held_value(samples, start)
        if previous is None:
            return
        coords = [x(start), y(previous)]
        for time, value in samples:
            if start < time <= end:
                coords.extend((x(time), y(previous), x(time), y(value)))
                previous = value
        coords.extend((x(end), y(previous)))
        self.canvas.create_line(*coords, fill=color, width=2)
