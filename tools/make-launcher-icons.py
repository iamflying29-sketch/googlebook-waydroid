#!/usr/bin/env python3
"""Make the two 32-pixel panel icons for the Waydroid launcher buttons.

Waydroid ships only a 512-pixel icon, which is far too big for a button on the Weston panel. This script
shrinks that icon to 32 pixels for the "Waydroid" button and adds a small restart badge for the
"Restart Waydroid" button. The icons are made on your own machine from the Waydroid package's icon, so
this repository does not redistribute Waydroid's artwork.

Usage: python3 -I make-launcher-icons.py [OUTPUT_DIR]
       OUTPUT_DIR defaults to ~/.local/share/icons
Needs Pillow: sudo apt install python3-pil
"""
import os
import sys

from PIL import Image, ImageDraw

SOURCE = "/usr/share/icons/hicolor/512x512/apps/waydroid.png"


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.local/share/icons")
    os.makedirs(out_dir, exist_ok=True)
    src = Image.open(SOURCE).convert("RGBA")

    # Plain icon for the "Waydroid" button.
    src.resize((32, 32), Image.LANCZOS).save(os.path.join(out_dir, "waydroid-32.png"))

    # Same icon with a dark circular badge and a white circular arrow for "Restart Waydroid".
    big = src.resize((128, 128), Image.LANCZOS)
    draw = ImageDraw.Draw(big)
    draw.ellipse((56, 56, 128, 128), fill=(40, 40, 40, 255))
    draw.arc((70, 70, 114, 114), start=300, end=210, fill=(255, 255, 255, 255), width=9)
    draw.polygon([(58, 88), (82, 88), (70, 104)], fill=(255, 255, 255, 255))
    big.resize((32, 32), Image.LANCZOS).save(os.path.join(out_dir, "waydroid-restart-32.png"))

    print("Wrote waydroid-32.png and waydroid-restart-32.png to " + out_dir)


if __name__ == "__main__":
    main()
