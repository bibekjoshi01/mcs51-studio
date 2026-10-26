"""On-chip 8051 serial state, framing, and clock-driven transfers."""


class Serial:
    def __init__(self, cpu):
        self.cpu = cpu
        self.sbuf = 0
        self.previous_rxd = True
        self.shift = [False] * 8
        self.reset()

    def reset(self):
        self.tx_clock = self.rx_clock = 0
        self.tx_multiple = self.rx_multiple = 0
        self.tx_count = self.rx_count = 0
        self.tx_index = self.rx_index = 0
        self.sending = self.receiving = False
        self.start_count = 0
        self.tx_address = 0xB1

    @property
    def mode(self):
        return self.cpu.ram[0x98] >> 6 & 3

    @property
    def smod(self):
        return self.cpu.ram[0x87] >> 7

    @property
    def word_size(self):
        return 9 if self.mode >= 2 else 8

    @property
    def multiples(self):
        return (2, 3, 2, 3, 2, 3) if self.smod else (5, 5, 6, 5, 5, 6)

    def pulse_clock(self):
        self.tx_clock += 1
        self.rx_clock += 1

    def send(self):
        self.sending = True
        self.tx_index = 0

    def rx_bit(self):
        return bool(self.cpu.bit(0xB0))

    def move_to_sbuf(self):
        self.sbuf = sum(int(b) << i for i, b in enumerate(self.shift))

    def receive_data_bit(self, index):
        if index < 8:
            self.shift[index] = self.rx_bit()

    def receive_bit(self):
        c = self.cpu
        if (
            self.rx_index == 8
            and not c.bit(0x98)
            and (not c.bit(0x9D) or self.rx_bit())
        ):
            bit = self.rx_bit()
            c.set_bit(0x9A, bit)
            self.move_to_sbuf()
            c.set_bit(0x98, 1)
            self.receiving = False
            self.rx_index = 0
            self.previous_rxd = bit
        else:
            self.receive_data_bit(self.rx_index)
            self.rx_index += 1

    def transmit_data_bit(self, index):
        self.cpu.set_bit(self.tx_address, self.cpu.ram[0x99] >> index & 1)

    def transmit_bit(self):
        c = self.cpu
        if self.tx_index == 0:
            c.set_bit(0xB1, 0)
            self.tx_index += 1
        elif self.tx_index == self.word_size + 1:
            c.set_bit(0xB1, 1)
            c.set_bit(0x99, 1)
            self.sending = False
        else:
            if self.tx_index == 8 and self.mode in (2, 3):
                c.set_bit(0xB1, c.bit(0x9B))
            else:
                self.transmit_data_bit(self.tx_index - 1)
            self.tx_index += 1

    def poll(self):
        c = self.cpu
        if c.bit(0x9C):
            if self.mode == 0:
                if not c.bit(0x98):
                    self.receive_data_bit(self.rx_index)
                    self.rx_index += 1
                    if self.rx_index == 8:
                        self.move_to_sbuf()
                        c.set_bit(0x98, 1)
                        self.rx_index = 0
            else:
                if not self.receiving:
                    probe = False
                    if self.mode == 2:
                        self.rx_count += 1
                        if self.rx_count >= self.multiples[self.rx_multiple] // 2:
                            self.rx_count = 0
                            probe = True
                    elif self.rx_clock >= 16 // (self.smod + 1):
                        self.rx_clock = 0
                        probe = True
                    if probe and not self.rx_bit() and self.previous_rxd:
                        self.start_count += 1
                    if self.start_count == 2:
                        self.start_count = 0
                        self.receiving = True
                if self.receiving:
                    if self.mode == 2:
                        self.rx_count += 1
                        if self.rx_count >= self.multiples[self.rx_multiple]:
                            self.rx_count = 0
                            self.rx_multiple = (self.rx_multiple + 1) % 6
                            self.receive_bit()
                    elif self.rx_clock >= 32 // (self.smod + 1):
                        self.rx_clock = 0
                        self.receive_bit()
        if self.sending:
            if self.mode == 0:
                self.tx_address = 0xB0
                self.transmit_data_bit(self.tx_index)
                self.tx_index += 1
                if self.tx_index == 8:
                    self.tx_index = 0
                    c.set_bit(0x99, 1)
                    self.sending = False
            else:
                self.tx_address = 0xB1
                if self.mode == 2:
                    self.tx_count += 1
                    if self.tx_count >= self.multiples[self.tx_multiple]:
                        self.tx_count = 0
                        self.tx_multiple = (self.tx_multiple + 1) % 6
                        self.transmit_bit()
                elif self.tx_clock >= 32 // (self.smod + 1):
                    self.tx_clock = 0
                    self.transmit_bit()
