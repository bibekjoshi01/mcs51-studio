"""External UART endpoint for the virtual board."""


class UARTEndpoint:
    """External 8-bit UART, sampled on the board's instruction clock."""

    def __init__(self):
        self.baud = 4800
        self.parity = 0
        self.period = 208
        self.rx_clock = self.tx_clock = self.period
        self.receiving = False
        self.previous_rx = 1
        self.rx_bit = 0
        self.rx_data = 0
        self.tx_bit = -1
        self.tx_line = 1
        self.pending = []
        self.received = []

    def configure(self, baud, parity=0, cycle_us=1):
        self.baud = baud
        self.parity = parity
        self.period = max(1, int(1_000_000 / cycle_us / baud + 0.5))
        self.rx_clock = self.tx_clock = self.period

    def start(self, text):
        if not text:
            return
        if text.startswith("{") and text.endswith("}"):
            try:
                self.pending = [
                    int(x.strip(), 16) & 255 for x in text[1:-1].split(",") if x.strip()
                ]
            except ValueError:
                self.pending = list((text + "\r").encode("latin1", "replace"))
        else:
            self.pending = list((text + "\r").encode("latin1", "replace"))

    def parity_byte(self, value):
        even = value.bit_count() % 2 == 0
        if self.parity == 1 and even or self.parity == 2 and not even:
            value |= 128
        return value

    def pulse(self, rx_line):
        self.rx_clock -= 1
        if self.rx_clock <= 0:
            self.rx_clock = self.period
            if self.receiving:
                if self.rx_bit == 8:
                    even = self.rx_data.bit_count() % 2 == 0
                    if (
                        not self.parity
                        or self.parity == 1
                        and not even
                        or self.parity == 2
                        and even
                    ):
                        self.received.append(
                            self.rx_data if not self.parity else self.rx_data & 127
                        )
                    self.rx_bit = 0
                    self.rx_data = 0
                    self.receiving = False
                else:
                    self.rx_data += rx_line << self.rx_bit
                    self.rx_bit += 1
            elif self.previous_rx == 1 and rx_line == 0:
                self.receiving = True
            self.previous_rx = rx_line
        self.tx_clock -= 1
        if self.tx_clock <= 0:
            self.tx_clock = self.period
            if self.pending:
                if self.tx_bit == -1:
                    self.tx_line = 0
                    self.tx_bit = 0
                elif self.tx_bit == 8:
                    self.tx_line = 1
                    self.tx_bit = -1
                    self.pending.pop(0)
                else:
                    self.tx_line = self.parity_byte(self.pending[0]) >> self.tx_bit & 1
                    self.tx_bit += 1
