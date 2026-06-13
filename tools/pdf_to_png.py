#!/usr/bin/env python3
"""Rasterize PDF page(s) to PNG using PDFium (self-contained, no Ghostscript).

Usage:
  python tools/pdf_to_png.py INPUT.pdf OUTPUT_PREFIX [--pages 1,2,5] [--scale 2.0]

Writes OUTPUT_PREFIX-pNN.png for each requested page (1-based). Default: page 1.
"""
from __future__ import annotations
import argparse
import sys

try:
    import pypdfium2 as pdfium
except ImportError:
    sys.exit("pip install pypdfium2")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("prefix")
    ap.add_argument("--pages", default="1", help="comma list, 1-based, or 'all'")
    ap.add_argument("--scale", type=float, default=2.0, help="72*scale DPI")
    a = ap.parse_args()

    doc = pdfium.PdfDocument(a.pdf)
    n = len(doc)
    pages = range(1, n + 1) if a.pages == "all" else [int(x) for x in a.pages.split(",")]
    for p in pages:
        if p < 1 or p > n:
            print(f"skip page {p} (doc has {n})")
            continue
        img = doc[p - 1].render(scale=a.scale).to_pil()
        out = f"{a.prefix}-p{p:02d}.png"
        img.save(out)
        print(f"wrote {out}  ({img.width}x{img.height})")


if __name__ == "__main__":
    main()
