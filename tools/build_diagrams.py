#!/usr/bin/env python3
"""Build the book's TikZ figures.

Pipeline (replaces the old XeLaTeX -> dvisvgm route):
    LuaLaTeX (babel bidi=basic, Renderer=Node)  ->  big-page PDF
    PyMuPDF  ->  crop to content bbox  ->  tight  <base>.pdf  +  <base>.svg

Why this route: the figures carry Persian (RTL) labels mixed with LTR math/code.
XeLaTeX + the `bidi` package mis-ordered multi-line nodes (first line of
text-width boxes, and whole `align` boxes, came out left-to-right). Compiling
with the *same* engine as the book body -- LuaLaTeX + babel `bidi=basic` --
renders Persian correctly; the picture is wrapped in `\\babelsublr` so the RTL
page does not mirror the geometry. SVGs are emitted as outlined glyphs
(`text_as_path`), which also avoids browsers re-applying bidi to <text>.

Usage:
    python tools/build_diagrams.py [GLOB]      # default GLOB='*'
    python tools/build_diagrams.py '33-*'
"""
import os, sys, glob, fnmatch, shutil, subprocess

try:
    import fitz  # PyMuPDF
    import numpy as np
except ImportError:
    sys.exit("PyMuPDF + numpy required:  pip install pymupdf numpy")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAG = os.path.join(ROOT, "diagrams")
BORDER = 4.0  # pt margin around the cropped content

# TinyTeX (the LaTeX that Quarto installs) lives per-user and is frequently NOT
# on PATH for non-interactive invocations: under %APPDATA% on Windows, and under
# ~/.TinyTeX on Linux/macOS. (On GitHub Actions the CI workflow exports it
# explicitly, because `run:` steps use a no-rc shell.) If `lualatex` isn't
# already resolvable, prepend the first standard TinyTeX bin dir we can find so
# the subprocess call below behaves the same everywhere.
if shutil.which("lualatex") is None:
    _home = os.path.expanduser("~")
    _appdata = os.environ.get("APPDATA", "")
    for _bin in (os.path.join(_appdata, "TinyTeX", "bin", "windows"),
                 os.path.join(_home, ".TinyTeX", "bin", "x86_64-linux"),
                 os.path.join(_home, ".TinyTeX", "bin", "aarch64-linux"),
                 os.path.join(_home, ".TinyTeX", "bin", "universal-darwin"),
                 os.path.join(_home, "Library", "TinyTeX", "bin", "universal-darwin")):
        if shutil.which("lualatex", path=_bin):
            os.environ["PATH"] = _bin + os.pathsep + os.environ.get("PATH", "")
            break


def build_one(base):
    """Compile base.tex, crop to content, write tight base.pdf + base.svg."""
    proc = subprocess.run(
        ["lualatex", "-interaction=nonstopmode", "-halt-on-error", base + ".tex"],
        cwd=DIAG, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace")
    pdf = os.path.join(DIAG, base + ".pdf")
    if not os.path.exists(pdf):
        # No PDF -> lualatex errored. Its output is captured (normally hidden);
        # surface the LaTeX error lines + a tail so CI logs say *why* instead of
        # a bare "PDF-FAIL" -- e.g. a missing .sty to add to the workflow's
        # tlmgr step. (-halt-on-error puts the first error near the end.)
        out = (proc.stdout or "").splitlines()
        flagged = [ln for ln in out
                   if ln[:1] == "!" or ln[:2] == "l." or "not found" in ln or "Error" in ln]
        sys.stderr.write(f"\n===== {base}.tex FAILED (lualatex exit {proc.returncode}) =====\n")
        if flagged:
            sys.stderr.write("\n".join(flagged[-25:]) + "\n--- output tail ---\n")
        sys.stderr.write("\n".join(out[-25:]) + f"\n===== end {base} =====\n")
        return "PDF-FAIL"
    doc = fitz.open(pdf)
    page = doc[0]
    # Content bbox by *rendered pixels*, not vector ops: TikZ/pgfplots sometimes
    # emit an invisible full-page element (clip path, etc.) that fools a
    # get_drawings()/get_text() bbox into spanning the whole page (-> figure
    # ends up a tiny speck on a huge canvas). Non-white pixels are the truth.
    pm = page.get_pixmap(dpi=100)
    a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)
    mask = (a[:, :, :3] < 248).any(axis=2)
    ys, xs = np.where(mask)
    if len(xs) == 0:
        doc.close()
        return "EMPTY"
    sc = pm.width / page.rect.width  # pixels per pt (square DPI)
    x0, x1 = xs.min() / sc, xs.max() / sc
    y0, y1 = ys.min() / sc, ys.max() / sc
    cr = fitz.Rect(x0 - BORDER, y0 - BORDER, x1 + BORDER, y1 + BORDER) & page.rect
    # CropBox only. Do NOT also set_mediabox: it re-frames the page coordinates
    # and clips the content out (top-anchored figures render blank). \includegraphics
    # and all viewers honour the CropBox, so this crops correctly everywhere.
    page.set_cropbox(cr)
    svg = page.get_svg_image(text_as_path=True)
    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    with open(pdf, "wb") as f:
        f.write(pdf_bytes)
    with open(os.path.join(DIAG, base + ".svg"), "w", encoding="utf-8") as f:
        f.write(svg)
    return "ok"


def main():
    filt = sys.argv[1] if len(sys.argv) > 1 else "*"
    bases = sorted(os.path.splitext(os.path.basename(f))[0]
                   for f in glob.glob(os.path.join(DIAG, "*.tex"))
                   if not os.path.basename(f).startswith("_"))
    bases = [b for b in bases if fnmatch.fnmatch(b, filt)]
    fails = []
    for i, b in enumerate(bases, 1):
        st = build_one(b)
        if st != "ok":
            fails.append((b, st))
        print(f"[{i:3d}/{len(bases)}] {b}: {st}")
    # tidy LaTeX intermediates (gitignored anyway)
    for ext in ("aux", "log", "out"):
        for f in glob.glob(os.path.join(DIAG, "*." + ext)):
            if not os.path.basename(f).startswith("_"):
                try: os.remove(f)
                except OSError: pass
    print(f"=== {len(bases)} figures built, {len(fails)} failure(s): {fails} ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
