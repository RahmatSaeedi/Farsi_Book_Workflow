#!/usr/bin/env python3
"""Make the Kindle *marketing* cover (the image uploaded to KDP next to the book).

Kindle Publishing Guidelines 4.1: 2560 px high, at least 300 DPI, RGB (no
CMYK), 5 MB or less, JPEG preferred. The cover is rendered from the vector
cover/cover.pdf, so it is sharp at any size -- never enlarge cover/cover.png
(guidelines: "do not stretch the image"). The book's own 1:1.44 proportions
are kept; KDP only reminds about covers *smaller* than 1600 x 2560.

    python tools/make_kindle_cover.py              # -> _book/<book>-kindle-cover.jpg + .tif
    python tools/make_kindle_cover.py --out DIR
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEIGHT = 2560
DPI = 300


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=os.path.join(ROOT, "cover", "cover.pdf"))
    ap.add_argument("--out", default=os.path.join(ROOT, "_book"))
    ap.add_argument("--name", help="output base name (default: <Kindle EPUB name>-cover)")
    args = ap.parse_args()
    if not args.name:
        # sit next to the Kindle edition it belongs to: book-kindle.epub -> book-kindle-cover.jpg
        kindle = sorted(glob.glob(os.path.join(ROOT, "_book", "*-kindle.epub")))
        stem = os.path.splitext(os.path.basename(kindle[0]))[0] if kindle else "book-kindle"
        args.name = stem + "-cover"
    if not os.path.exists(args.src):
        print(f"make_kindle_cover: no {os.path.relpath(args.src, ROOT)} -- skipped "
              "(build it with: python tools/build_cover.py)")
        return 0

    import pymupdf
    from PIL import Image, ImageCms

    page = pymupdf.open(args.src)[0]
    zoom = HEIGHT / page.rect.height
    pm = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False,
                         colorspace=pymupdf.csRGB)
    im = Image.open(io.BytesIO(pm.tobytes("png"))).convert("RGB")
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()

    os.makedirs(args.out, exist_ok=True)
    jpg = os.path.join(args.out, args.name + ".jpg")
    tif = os.path.join(args.out, args.name + ".tif")
    # 4:4:4 chroma keeps the thin title strokes clean
    im.save(jpg, "JPEG", quality=95, subsampling=0, optimize=True,
            dpi=(DPI, DPI), icc_profile=srgb)
    im.save(tif, "TIFF", compression="tiff_lzw", dpi=(DPI, DPI), icc_profile=srgb)
    for path in (jpg, tif):
        mb = os.path.getsize(path) / 2**20
        print(f"make_kindle_cover: {os.path.relpath(path, ROOT)}  "
              f"{im.width}x{im.height} px, {DPI} DPI, sRGB, {mb:.2f} MB")
        if mb > 5:
            print("make_kindle_cover: WARNING over the 5 MB the guidelines allow")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
