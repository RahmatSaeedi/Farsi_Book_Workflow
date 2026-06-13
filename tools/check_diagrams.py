#!/usr/bin/env python3
"""Quality check for built figures.

`build_diagrams.py` reporting "ok" only means a PDF was produced — it does NOT
guarantee the content actually shows. This renders every figure PDF to a pixmap
and flags any that come out (near-)blank or with a suspicious page size, which
is how a clipped/mis-cropped figure (e.g. a coordinate-frame bug) reveals itself.

    python tools/check_diagrams.py

Exit code is non-zero if anything looks wrong, so it can gate CI.
"""
import fitz, glob, os, sys
import numpy as np

DIAG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "diagrams")

def main():
    pdfs = sorted(f for f in glob.glob(os.path.join(DIAG, "*.pdf"))
                  if not os.path.basename(f).startswith("_"))
    blanks, tiny = [], []
    for f in pdfs:
        p = fitz.open(f)[0]
        w, h = p.rect.width, p.rect.height
        pm = p.get_pixmap(dpi=60)
        a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)
        nonwhite = (a[:, :, :3] < 240).any(axis=2).mean()
        base = os.path.basename(f)
        if nonwhite < 0.004:
            blanks.append((base, round(float(nonwhite), 4), f"{w:.0f}x{h:.0f}"))
        if w < 12 or h < 12 or w > 2000 or h > 2000:
            tiny.append((base, f"{w:.0f}x{h:.0f}"))
    print(f"checked {len(pdfs)} figure PDFs")
    if blanks:
        print(f"NEAR-BLANK ({len(blanks)}):")
        for b in blanks: print("   ", b)
    if tiny:
        print(f"SUSPICIOUS SIZE ({len(tiny)}):")
        for t in tiny: print("   ", t)
    ok = not blanks and not tiny
    print("=== OK ===" if ok else "=== NEEDS ATTENTION ===")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
