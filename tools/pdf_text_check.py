#!/usr/bin/env python3
"""Check what PDF viewers will *copy* from the book, and that a change to the
PDF text pipeline did not move a single glyph.

Companion of theme/pdf-copytext.lua (visual-order glyph streams, real letters in
ToUnicode, ZWNJ kept). Two modes:

  1) Text quality of one PDF page, through every extraction engine installed
     (PyMuPDF always; pypdfium2 = the Chrome/Edge engine if installed):

        python tools/pdf_text_check.py _book/BOOK.pdf --page 40

     Reports, per engine, how many Arabic *presentation-form* code points
     (U+FB50-FDFF, U+FE70-FEFF: the "non-standard letters" symptom), how many
     ZWNJ (U+200C) and how many bidi control characters the text contains, and
     prints the first characters so the reading order can be judged. Good output:
     presentation-forms=0, zwnj>0 for a Persian page, text reads in logical order.

     NOTE: these libraries are only a first approximation of what a *viewer*
     copies. The applications differ from them and from each other (Chrome's
     PDFium build, Edge's own engine, Firefox's pdf.js): after a change to the
     text pipeline, open the PDF in the browsers and paste a few lines with
     ezafe marks, Latin words and inline math.

  2) Geometry equivalence of two renders of the same source (before/after a
     change that is only supposed to alter the content stream, not the layout):

        python tools/pdf_text_check.py before.pdf after.pdf --geometry [--pages 50]

     Every glyph of BEFORE is looked up on the same baseline (same font and size)
     in AFTER and the displacement distribution is printed. LuaTeX accumulates
     up to ~0.5 pt of rounding along a long line, so buckets above 0.5 pt are the
     ones that matter. Combining marks that PyMuPDF fails to report are verified
     by pixels instead. The dots of dotted leaders (table of contents) are
     skipped: TeX anchors their grid to the box's start edge, so converting a box
     from TRT to TLT shifts the whole dot pattern by less than one dot spacing
     (spacing and vertical alignment are unchanged).
"""
from __future__ import annotations

import argparse
import bisect
import collections
import re
import sys
import unicodedata

try:
    import pymupdf as fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    sys.exit("pip install pymupdf")

PRES_A, PRES_B = (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)
BIDI_CTRL = {0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069}


def stats(text: str) -> str:
    pres = sum(1 for c in text if PRES_A[0] <= ord(c) <= PRES_A[1] or PRES_B[0] <= ord(c) <= PRES_B[1])
    return (f"presentation-forms={pres} zwnj={text.count(chr(0x200C))} "
            f"bidi-controls={sum(1 for c in text if ord(c) in BIDI_CTRL)}")


def text_mode(path: str, page: int, width: int) -> None:
    engines = [("PyMuPDF", lambda: fitz.open(path)[page].get_text())]
    try:
        import pypdfium2 as pdfium  # type: ignore

        engines.append(("PDFium", lambda: pdfium.PdfDocument(path)[page].get_textpage().get_text_range()))
    except ImportError:
        print("(pypdfium2 not installed: `pip install pypdfium2` to also test the Chrome/Edge engine)")
    for name, fn in engines:
        t = re.sub(r"\s+", " ", fn()).strip()
        print(f"[{name:8s}] {stats(t)}")
        print("   ", t[:width])


def glyph_rows(page):
    rows = collections.defaultdict(list)
    for blk in page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]:
        for ln in blk.get("lines", []):
            for sp in ln["spans"]:
                for ch in sp["chars"]:
                    c = ch["c"]
                    # U+200B: the *ink* of a combining mark (theme/pdf-copytext.lua maps
                    # it to ZERO WIDTH SPACE; its text is carried by a blank glyph next
                    # to the base, which is reported under the mark's own code point).
                    if c.strip() == "" or ord(c) in (0x200B, 0x200C, 0x200D):
                        continue
                    rows[(sp["font"], round(sp["size"], 1), round(ch["origin"][1], 1))].append((ch["origin"][0], c))
    for k in rows:
        rows[k].sort()
    return rows


def mark_in_place(page_a, page_b, x: float, y: float) -> bool:
    """Pixel check for a combining mark reported at (x, y): render a small window
    around it in both PDFs at 600 dpi and compare the ink centroid and amount."""
    try:
        import numpy as np
    except ImportError:
        return False
    clip = fitz.Rect(x - 5, y - 9, x + 5, y + 6.5)

    def ink(page):
        pm = page.get_pixmap(dpi=600, clip=clip, colorspace=fitz.csGRAY)
        arr = 255 - np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width).astype(float)
        if arr.sum() < 1:
            return None
        xs = np.indices(arr.shape)[1]
        return (xs * arr).sum() / arr.sum() / pm.width * 10, arr.sum()

    ia, ib = ink(page_a), ink(page_b)
    if not ia or not ib:
        return False
    return abs(ia[0] - ib[0]) < 0.5 and abs(ib[1] / ia[1] - 1) < 0.25


def geometry_mode(before: str, after: str, max_pages: int) -> int:
    da, db = fitz.open(before), fitz.open(after)
    n = min(len(da), len(db), max_pages)
    hist = collections.Counter()
    worst = []
    missing = total = 0
    for i in range(n):
        ga, gb = glyph_rows(da[i]), glyph_rows(db[i])
        for key, lst in ga.items():
            other = (gb.get(key) or gb.get((key[0], key[1], round(key[2] + 0.1, 1)))
                     or gb.get((key[0], key[1], round(key[2] - 0.1, 1))) or [])
            xs = [x for x, _ in other]
            dotted_leader = sum(1 for _, c in lst if c == ".") >= 8
            for x, c in lst:
                if dotted_leader and c == ".":
                    continue
                total += 1
                if not xs:
                    if unicodedata.category(c) == "Mn" and mark_in_place(da[i], db[i], x, key[2]):
                        hist["<0.05"] += 1   # drawn at the same place; only the extractor lost it
                        continue
                    missing += 1
                    worst.append((float("inf"), i, c, x, key[2]))
                    continue
                j = bisect.bisect_left(xs, x)
                d = min(abs(xs[k] - x) for k in (j - 1, j) if 0 <= k < len(xs))
                if d >= 0.3 and unicodedata.category(c) == "Mn":
                    # PyMuPDF often drops or mis-assigns combining marks; trust the pixels instead
                    if mark_in_place(da[i], db[i], x, key[2]):
                        d = 0.0
                b = "<0.05" if d < 0.05 else "<0.15" if d < 0.15 else "<0.5" if d < 0.5 else "<1" if d < 1 else "<5" if d < 5 else ">=5"
                hist[b] += 1
                if d >= 0.5:
                    worst.append((d, i, c, x, key[2]))
    print(f"pages compared: {n} (of {len(da)} / {len(db)}) | glyphs: {total} | without a same-baseline counterpart: {missing}")
    for b in ("<0.05", "<0.15", "<0.5", "<1", "<5", ">=5"):
        print(f"  displacement {b:5s}: {hist[b]}")
    worst.sort(reverse=True)
    for d, i, c, x, y in worst[:12]:
        print(f"  check: page {i} char {c!r} U+{ord(c):04X} at x={x:.2f} y={y} -> {'missing' if d == float('inf') else f'{d:.2f} pt'}")
    bad = hist["<1"] + hist["<5"] + hist[">=5"] + missing
    print("RESULT:", "layout unchanged (every glyph within 0.5 pt)" if bad == 0 else f"{bad} glyph(s) moved by 0.5 pt or more (or missing)")
    return 0 if bad == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", help="PDF to check (or the BEFORE render with --geometry)")
    ap.add_argument("after", nargs="?", help="AFTER render (with --geometry)")
    ap.add_argument("--page", type=int, default=0, help="0-based page for the text check (default 0)")
    ap.add_argument("--width", type=int, default=400, help="characters of text to print per engine")
    ap.add_argument("--geometry", action="store_true", help="compare glyph positions of two PDFs")
    ap.add_argument("--pages", type=int, default=10**9, help="max pages to compare with --geometry")
    args = ap.parse_args()
    if getattr(sys.stdout, "reconfigure", None):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.geometry:
        if not args.after:
            ap.error("--geometry needs BEFORE.pdf AFTER.pdf")
        return geometry_mode(args.pdf, args.after, args.pages)
    text_mode(args.pdf, args.page, args.width)
    return 0


if __name__ == "__main__":
    sys.exit(main())
