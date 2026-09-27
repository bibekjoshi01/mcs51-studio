"""Load package data in source installs, wheels, and frozen applications."""

import json
from importlib.resources import files

DATA = files("mcs51_studio").joinpath("data")
ISA = json.loads(DATA.joinpath("isa.json").read_text(encoding="utf-8"))
LED_COUNTER = DATA.joinpath("led_counter.asm").read_text(encoding="utf-8")
