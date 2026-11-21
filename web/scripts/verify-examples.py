"""Check website programs against the actual simulator, without starting Tk."""

import re
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB.parent / "src"))

from mcs51_studio.engine.assembler import assemble  # noqa: E402
from mcs51_studio.engine.cpu import CPU  # noqa: E402
from mcs51_studio.hardware.board import Board  # noqa: E402
from mcs51_studio.hardware.wiring import built_in_presets  # noqa: E402


def load(name, preset="LED Counter"):
    program = assemble((WEB / "public/examples" / f"{name}.asm").read_text())
    cpu = CPU()
    cpu.code[:] = program.code
    board = Board(cpu)
    setup = built_in_presets()[preset]
    board.mapping = setup["mapping"]
    board.enabled = setup["enabled"]
    board.update()
    return cpu, board, program


def steps(cpu, board, count):
    for _ in range(count):
        cpu.step()
        board.update()


# Every downloadable program and Markdown assembly fragment must assemble.
for file in (WEB / "public/examples").glob("*.asm"):
    assemble(file.read_text())
fragments = 0
for file in (WEB / "src/content/docs").rglob("*.md*"):
    for source in re.findall(r"```asm[^\n]*\n(.*?)```", file.read_text(), re.S):
        assemble(source)
        fragments += 1

cpu, board, _ = load("first-led")
steps(cpu, board, 2)
assert cpu.ram[0x90] == 0xFE, "First LED example must produce FEH"

cpu, board, _ = load("led-counter")
steps(cpu, board, 12000)
assert cpu.a < 255 and cpu.ram[0x90] < 255, "Bundled counter must advance"

cpu, board, _ = load("switch-mirror", "Switch Input")
board.switches[0] = False
board.update()
steps(cpu, board, 3)
assert cpu.ram[0x90] == 0xFE, "Low switch must light its corresponding LED"
assert cpu.ram[0xA0] == 0xFF, "Input latch must remain released"

cpu, board, program = load("registers-memory")
steps(cpu, board, 3)
assert cpu.a == 8 and cpu.ram[0x30] == 8
assert cpu.pc not in program.used, "Memory example must end after three instructions"

cpu, board, _ = load("timer-toggle", "Timer / PWM")
transitions = []
previous = 1
for _ in range(4000):
    steps(cpu, board, 1)
    level = cpu.ram[0x90] & 1
    if level != previous:
        transitions.append(cpu.cycles)
        previous = level
assert len(transitions) >= 3, "Timer example must toggle repeatedly"
assert all(1000 <= b - a < 1050 for a, b in zip(transitions, transitions[1:])), (
    transitions
)

cpu, board, _ = load("dac-ramp", "DAC Waveform")
values = []
for _ in range(800):
    steps(cpu, board, 1)
    values.append(board.dac_value)
assert min(values) == 0 and max(values) == 255, "DAC ramp must span the output range"

cpu, board, _ = load("uart-character", "UART Link")
board.uart.configure(2400, parity=0, data_bits=8, stop_bits=1)
steps(cpu, board, 12000)
assert list(board.uart.received) == [ord("A")], "UART must transmit exactly one A"

print(f"Verified 7 downloadable programs and {fragments} assembly fragments.")
intervals = [b - a for a, b in zip(transitions, transitions[1:])]
print(f"Timer toggle intervals: {intervals} simulated microseconds.")
