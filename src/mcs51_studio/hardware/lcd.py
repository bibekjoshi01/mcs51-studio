"""Character LCD controller state and command handling."""


class LCD:
    def __init__(self):
        self.ddram = [" "] * 128
        self.cgram = bytearray(64)
        self.address = 0
        self.cg = False
        self.increment = True
        self.entry_shift = False
        self.shift = 0
        self.display = False
        self.cursor = False
        self.blink = False
        self.four_bit = False
        self.nibble = None

    def accept(self, value, rs):
        if self.four_bit:
            if self.nibble is None:
                self.nibble = value & 240
                return
            value, self.nibble = self.nibble | (value >> 4), None
        elif not rs and value >> 4 == 2:
            self.four_bit = True
        self.byte(value, rs)

    def byte(self, value, rs):
        if rs:
            if self.cg:
                self.cgram[self.address & 63] = value & 31
            else:
                self.ddram[self.address & 127] = chr(value)
            self.advance(self.increment)
            if not self.cg and self.entry_shift:
                self.shift = (self.shift + (1 if self.increment else -1)) % 40
        elif value & 128:
            self.address = value & 127
            self.cg = False
        elif value & 64:
            self.address = value & 63
            self.cg = True
        elif value & 32:
            self.four_bit = not bool(value & 16)
        elif value & 16:
            if value & 8:
                self.shift = (self.shift + (-1 if value & 4 else 1)) % 40
            else:
                self.cg = False
                self.advance(bool(value & 4))
        elif value & 8:
            self.display = bool(value & 4)
            self.cursor = bool(value & 2)
            self.blink = bool(value & 1)
        elif value & 4:
            self.increment = bool(value & 2)
            self.entry_shift = bool(value & 1)
        elif value & 2:
            self.cg = False
            self.address = 0
            self.shift = 0
        elif value & 1:
            self.cg = False
            self.increment = True
            self.ddram = [" "] * 128
            self.address = 0
            self.shift = 0

    def advance(self, increment):
        delta = 1 if increment else -1
        if self.cg:
            self.address = (self.address + delta) & 63
            return
        address = self.address + delta
        if increment:
            self.address = 0 if address > 103 else 64 if 40 <= address < 64 else address
        else:
            self.address = 103 if address < 0 else 39 if 40 <= address < 64 else address

    def lines(self):
        if not self.display:
            return [" " * 16] * 2
        return [
            "".join(self.ddram[base + (i + self.shift) % 40] for i in range(16))
            for base in (0, 64)
        ]
