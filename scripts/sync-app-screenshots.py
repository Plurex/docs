#!/usr/bin/env python3
"""Copy the web app screenshots the docs use from the pinned plurex checkout into images/app.

plurex keeps a screenshot of every page of the app in docs/screenshots, listed in its README and captured by a tour of
the real app. This script takes the ones listed in SHOTS, crops any that show one dialog, scales them to 2x and writes
them to images/app/<name>.png. Images there that SHOTS no longer lists are removed.

It fails when a shot is missing upstream, when the upstream README no longer lists it, or when a whole window image is
not the size the README promises, so a renamed or dropped screen is noticed at the refresh.
"""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".upstream/plurex/docs/screenshots"
DEST = ROOT / "images/app"

# Upstream captures 1440x900 logical pixels at 3x.
LOGICAL = (1440, 900)
CAPTURE_SCALE = 3
OUTPUT_SCALE = 2

# Upstream name -> crop box (left, top, right, bottom) in logical pixels, or None for the whole window.
# A crop is checked by eye at each refresh: a dialog that grows or moves needs a new box.
SHOTS = {
    "auth/register": (520, 228, 920, 672),
    "terminal/overview": None,
    "accounts/list": (0, 0, 1440, 300),
    "accounts/account/overview": None,
    "settings/general": (0, 0, 880, 310),
    "settings/security": (0, 0, 880, 660),
    "devtools/overview": (0, 0, 880, 450),
    "devtools/new-api-key-full": (440, 113, 1000, 787),
    "devtools/new-api-key-custom": (440, 77, 1000, 823),
    "devtools/new-api-key-specific-account": (440, 77, 1000, 823),
}


def main() -> int:
    readme = (SOURCE / "README.md").read_text()
    errors = []
    written = set()
    for name, crop in SHOTS.items():
        source = SOURCE / f"{name}.png"
        if f"`{name}`" not in readme:
            errors.append(f"{name}: no longer listed in the upstream screenshots README")
        if not source.exists():
            errors.append(f"{name}: missing upstream at {source.relative_to(ROOT)}")
            continue
        image = Image.open(source)
        expected = tuple(d * CAPTURE_SCALE for d in LOGICAL)
        if image.size != expected:
            errors.append(f"{name}: is {image.size[0]}x{image.size[1]}, expected {expected[0]}x{expected[1]}")
            continue
        if crop is not None:
            image = image.crop(tuple(c * CAPTURE_SCALE for c in crop))
        size = tuple(round(d * OUTPUT_SCALE / CAPTURE_SCALE) for d in image.size)
        image = image.convert("RGB").resize(size, Image.Resampling.LANCZOS)
        target = DEST / f"{name}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, optimize=True)
        written.add(target)

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    for stale in sorted(DEST.rglob("*.png")):
        if stale not in written:
            stale.unlink()
    for directory in sorted((d for d in DEST.rglob("*") if d.is_dir()), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()

    print(f"Synced {len(written)} screenshots into {DEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
