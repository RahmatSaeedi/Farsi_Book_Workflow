#!/usr/bin/env python3
"""Build the book cover from cover/cover.tex.

    python tools/build_cover.py      # -> cover/cover.pdf (print) + cover/cover.png (web, EPUB)

Same pipeline as the figures: LuaLaTeX + babel bidi=basic, then PyMuPDF crops
the oversized page to the painted area. Both outputs are COMMITTED (unlike the
figures), because the cover changes rarely and every format needs it:

  cover/cover.pdf  page 1 of the PDF edition (theme/preamble.tex) and the source
                   of the Kindle marketing cover (tools/make_kindle_cover.py)
  cover/cover.png  `cover-image` / `epub-cover-image` in _quarto.yml, 2560 px high

Run it again whenever you edit cover/cover.tex, and commit the two outputs.
tools/build_all.py only runs it when an output is missing.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVER = os.path.join(ROOT, "cover")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_env  # noqa: E402

PNG_HEIGHT = 2560            # Kindle guideline 4.1; 1781 x 2560 is under Apple's 5.6 MP limit
MAX_PIXELS = 5_600_000


def missing() -> bool:
    """True when cover.tex exists but cover.pdf or cover.png does not.

    Deliberately not a date comparison: both outputs are committed, and a fresh
    clone gives every file the same checkout time, so "older than the .tex"
    would rebuild (and so modify) tracked files on every new computer.
    """
    if not os.path.exists(os.path.join(COVER, "cover.tex")):
        return False
    return not all(os.path.exists(os.path.join(COVER, n)) for n in ("cover.pdf", "cover.png"))


def main() -> int:
    import numpy as np
    import pymupdf

    tex = os.path.join(COVER, "cover.tex")
    if not os.path.exists(tex):
        print("build_cover: no cover/cover.tex (using cover/cover.pdf + cover.png as they are)")
        return 0
    pdf = os.path.join(COVER, "cover.pdf")
    r = subprocess.run(["lualatex", "-interaction=nonstopmode", "-halt-on-error", "cover.tex"],
                       cwd=COVER, capture_output=True, text=True, errors="replace",
                       env=check_env.tex_env())
    if r.returncode != 0 or not os.path.exists(pdf):
        print("--- lualatex FAILED for cover/cover.tex ---")
        print("\n".join((r.stdout or "").splitlines()[-25:]))
        return 1

    doc = pymupdf.open(pdf)
    page = doc[0]
    # crop to the painted pixels (see tools/build_diagrams.py for why pixels)
    pm = page.get_pixmap(dpi=100)
    a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)
    ys, xs = np.where((a[:, :, :3] < 248).any(axis=2))
    if len(xs) == 0:
        print("build_cover: the cover rendered blank")
        return 1
    sc = pm.width / page.rect.width
    # +1 px on the far edges: xs.max() is the last painted pixel, not its right edge
    crop = pymupdf.Rect(xs.min() / sc, ys.min() / sc, (xs.max() + 1) / sc, (ys.max() + 1) / sc)
    crop = pymupdf.Rect(crop.x0 + 0.5, crop.y0 + 0.5, crop.x1 - 0.5, crop.y1 - 0.5) & page.rect
    page.set_cropbox(crop)            # CropBox only, as for the figures
    data = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    with open(pdf, "wb") as fh:
        fh.write(data)

    page = pymupdf.open(pdf)[0]
    zoom = PNG_HEIGHT / page.rect.height
    pm = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False, colorspace=pymupdf.csRGB)
    png = os.path.join(COVER, "cover.png")
    pm.save(png)
    for ext in ("aux", "log", "out"):
        try:
            os.remove(os.path.join(COVER, "cover." + ext))
        except OSError:
            pass
    print(f"build_cover: cover/cover.pdf ({page.rect.width:.0f} x {page.rect.height:.0f} pt), "
          f"cover/cover.png ({pm.width} x {pm.height} px)")
    if pm.width * pm.height > MAX_PIXELS:
        print("build_cover: WARNING cover.png is over 5.6 megapixels (Apple Books rejects it)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
