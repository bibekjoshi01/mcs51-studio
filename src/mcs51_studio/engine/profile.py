"""The processor and memory configuration supported by this release."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessorProfile:
    name: str
    oscillator_hz: int
    clocks_per_cycle: int
    internal_ram_bytes: int
    code_bytes: int
    external_ram_bytes: int
    timers: int
    interrupt_sources: int


CLASSIC_8051 = ProcessorProfile(
    name="Classic 8051",
    oscillator_hz=12_000_000,
    clocks_per_cycle=12,
    internal_ram_bytes=128,
    code_bytes=65536,
    external_ram_bytes=65536,
    timers=2,
    interrupt_sources=5,
)
