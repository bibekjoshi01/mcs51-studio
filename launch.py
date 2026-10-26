"""Run directly from a checkout without installing the package."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mcs51_studio.ui.application import main

if __name__ == "__main__":
    main()
