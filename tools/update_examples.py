#!/usr/bin/env python3
"""Refresh examples/: the committed outputs of the sample book.

    python tools/build_all.py          # build everything into _book/ first
    python tools/update_examples.py    # copy the results into examples/

examples/ shows what the workflow produces without installing anything: the
PDF (select and copy the Persian text in it), the EPUB, the Kindle edition
and its cover, and PNG previews of the PDF pages and of the website.

It is NOT part of the normal build: _book/ stays git-ignored and build_all.py
never touches examples/, because every render changes the bytes of a PDF or
EPUB and would otherwise show up as a change in every commit. Run this only
when the template itself changes (theme/, tools/, the sample chapter), and
delete examples/ in your own book's repository.
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOK = os.path.join(ROOT, "_book")
OUT = os.path.join(ROOT, "examples")
PAGE_WIDTH = 900          # px, PDF page previews


def one(pattern: str, exclude: str = "") -> str:
    hits = [p for p in sorted(glob.glob(os.path.join(BOOK, pattern)))
            if not exclude or exclude not in os.path.basename(p)]
    if not hits:
        sys.exit(f"update_examples: no _book/{pattern} -- run python tools/build_all.py first")
    return hits[0]


def find_browser() -> str | None:
    """A Chromium-based browser for the website screenshot (optional)."""
    for name in ("msedge", "chrome", "google-chrome", "chromium", "chromium-browser"):
        exe = shutil.which(name)
        if exe:
            return exe
    for base in (os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", "")):
        for rel in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"):
            exe = os.path.join(base, rel)
            if base and os.path.exists(exe):
                return exe
    mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    return mac if os.path.exists(mac) else None


def main() -> int:
    import pymupdf

    pdf = one("*.pdf")
    epub = one("*.epub", exclude="-kindle")
    kindle = one("*-kindle.epub")
    cover = one("*-kindle-cover.jpg")

    if os.path.isdir(OUT):
        for old in glob.glob(os.path.join(OUT, "*")):
            if not old.endswith("README.md"):
                os.remove(old)
    os.makedirs(OUT, exist_ok=True)

    # ASCII names: the built files carry the (Persian) book title
    for src, name in ((pdf, "sample-book.pdf"), (epub, "sample-book.epub"),
                      (kindle, "sample-book-kindle.epub"), (cover, "sample-book-kindle-cover.jpg")):
        shutil.copyfile(src, os.path.join(OUT, name))
        print(f"update_examples: examples/{name}  ({os.path.getsize(src) / 1024:.0f} kB)")

    doc = pymupdf.open(pdf)
    for i, page in enumerate(doc, 1):
        zoom = PAGE_WIDTH / page.rect.width
        page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False).save(
            os.path.join(OUT, f"pdf-page-{i:02d}.png"))
    print(f"update_examples: examples/pdf-page-01..{len(doc):02d}.png")

    browser = find_browser()
    chapters = sorted(glob.glob(os.path.join(BOOK, "chapters", "*.html")))
    if browser and chapters:
        shot = os.path.join(OUT, "website.png")
        url = "file:///" + chapters[0].replace("\\", "/")
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--window-size=1280,1600", "--virtual-time-budget=20000",  # let MathJax finish
                        f"--screenshot={shot}", url],
                       capture_output=True, timeout=120)
        print("update_examples: examples/website.png" if os.path.exists(shot)
              else "update_examples: the browser made no screenshot (website.png skipped)")
    else:
        print("update_examples: no Edge/Chrome found (website.png skipped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
