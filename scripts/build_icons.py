"""Generate native application icons from a 1024px PNG export of the SVG master."""

import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source", type=Path, help="Square PNG export, at least 1024×1024"
    )
    args = parser.parse_args()
    with Image.open(args.source) as source:
        if (
            source.format != "PNG"
            or source.width != source.height
            or source.width < 1024
        ):
            parser.error("Export the SVG as a square PNG at least 1024×1024 pixels")
        image = source.convert("RGBA").resize((1024, 1024), Image.Resampling.LANCZOS)
    icons = ROOT / "packaging/icons"
    icons.mkdir(parents=True, exist_ok=True)
    image.save(
        icons / "mcs51-studio.ico",
        sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)],
    )
    image.save(icons / "mcs51-studio.icns")
    image.resize((512, 512), Image.Resampling.LANCZOS).save(
        ROOT / "src/mcs51_studio/data/icon.png"
    )


if __name__ == "__main__":
    main()
