"""External UART endpoint with explicit framing and receive diagnostics."""


class UARTEndpoint:
    def __init__(self):
        self.baud, self.parity, self.data_bits, self.stop_bits = 4800, 0, 8, 1
        self.period = 208
        self.pending, self.received = [], []
        self.errors = {"parity": 0, "framing": 0, "start": 0}
        self.last_error = ""
        self.reset_link()

    def reset_link(self):
        self.pending.clear()
        self.tx_line, self.previous_rx = 1, 1
        self.tx_clock = self.period
        self.tx_frame = []
        self.rx_clock = 0
        self.receiving = False
        self.rx_bits = []
        self.rx_stage = "idle"

    @property
    def framing(self):
        return f"{self.data_bits}{('N', 'O', 'E')[self.parity]}{self.stop_bits}"

    def configure(self, baud, parity=0, cycle_us=1, data_bits=None, stop_bits=1):
        data_bits = (7 if parity else 8) if data_bits is None else data_bits
        if (
            baud not in (1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200)
            or cycle_us <= 0
            or parity not in (0, 1, 2)
            or data_bits not in (7, 8)
            or stop_bits not in (1, 2)
        ):
            raise ValueError(
                "Use a supported baud rate, 7/8 data bits, None/Odd/Even parity, and 1/2 stop bits."
            )
        period = max(1, round(1_000_000 / cycle_us / baud))
        configuration = baud, parity, data_bits, stop_bits, period
        if configuration == (
            self.baud,
            self.parity,
            self.data_bits,
            self.stop_bits,
            self.period,
        ):
            return
        if self.pending or self.tx_frame or self.receiving:
            raise ValueError("UART is busy. Reset Link before changing framing.")
        self.baud, self.parity, self.data_bits, self.stop_bits, self.period = (
            configuration
        )
        self.reset_link()

    def start(self, text):
        if not text:
            return
        if text.startswith("{"):
            if not text.endswith("}"):
                raise ValueError("Close the hexadecimal byte list with }.")
            try:
                values = [int(x.strip(), 16) for x in text[1:-1].split(",")]
            except ValueError as error:
                raise ValueError("Use hexadecimal bytes such as {41,42}.") from error
        else:
            if text.startswith("\\{"):
                text = text[1:]
            try:
                values = list((text + "\r").encode("latin1"))
            except UnicodeEncodeError as error:
                raise ValueError(
                    "UART text supports Latin-1; use a byte list for explicit data."
                ) from error
        if any(not 0 <= value < 1 << self.data_bits for value in values):
            raise ValueError(
                f"Values must fit the selected {self.data_bits}-bit frame."
            )
        if len(self.pending) + len(values) > 65536:
            raise ValueError("UART queue is full (65536 bytes).")
        self.pending.extend(values)

    def parity_byte(self, value):
        value &= (1 << self.data_bits) - 1
        if self.parity:
            parity_bit = (value.bit_count() & 1) ^ (self.parity == 1)
            value |= parity_bit << self.data_bits
        return value

    def error(self, kind, message):
        self.errors[kind] += 1
        self.last_error = message

    def pulse(self, rx_line):
        rx_line = int(bool(rx_line))
        if not self.receiving and self.previous_rx and not rx_line:
            self.receiving = True
            self.rx_stage = "start"
            self.rx_clock = max(1, self.period // 2)
            self.rx_bits = []
        elif self.receiving:
            self.rx_clock -= 1
            if self.rx_clock <= 0:
                self.rx_clock = self.period
                if self.rx_stage == "start":
                    if rx_line:
                        self.error("start", "Start pulse was shorter than half a bit.")
                        self.receiving = False
                    else:
                        self.rx_stage = "data"
                else:
                    self.rx_bits.append(rx_line)
                    size = self.data_bits + bool(self.parity) + self.stop_bits
                    if len(self.rx_bits) == size:
                        data = self.rx_bits[: self.data_bits]
                        valid = True
                        if self.parity and (
                            sum(data) + self.rx_bits[self.data_bits]
                        ) % 2 != (self.parity == 1):
                            self.error(
                                "parity",
                                "Parity mismatch; received frame was discarded.",
                            )
                            valid = False
                        if not all(self.rx_bits[self.data_bits + bool(self.parity) :]):
                            self.error(
                                "framing",
                                "Stop bit was low; check baud, stop bits, and shared pins.",
                            )
                            valid = False
                        if valid:
                            self.received.append(
                                sum(bit << i for i, bit in enumerate(data))
                            )
                        self.receiving = False
        self.previous_rx = rx_line
        self.tx_clock -= 1
        if self.tx_clock <= 0:
            self.tx_clock = self.period
            if not self.tx_frame and self.pending:
                value = self.parity_byte(self.pending.pop(0))
                self.tx_frame = (
                    [0]
                    + [
                        (value >> i) & 1
                        for i in range(self.data_bits + bool(self.parity))
                    ]
                    + [1] * self.stop_bits
                )
            self.tx_line = self.tx_frame.pop(0) if self.tx_frame else 1
