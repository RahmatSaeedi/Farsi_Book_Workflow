#!/usr/bin/env python3
"""Build every edition of the book, in the right order, and check the results.

    python tools/build_all.py                     # the whole pipeline (minutes for a small book,
                                                  # 1-1.5 h for a 2,900-page one)
    python tools/build_all.py --kindle-previewer  # + Amazon's own conversion check (+1 h)
    python tools/build_all.py --skip-render       # only the Kindle edition, cover and checks

Steps (docs/BUILD.md explains each one):
  1. check the toolchain                     tools/check_env.py
  2. figures whose .tex changed -> PDF + SVG tools/build_diagrams.py
     (and the cover, if cover/cover.pdf|png is missing: tools/build_cover.py)
  3. HTML site + PDF + EPUB in ONE render    quarto render
     (the project post-render hook runs tools/fix_epub.py on the EPUB)
  4. Kindle edition                          tools/build_kindle_epub.py
  5. Kindle marketing cover (JPEG + TIFF)    tools/make_kindle_cover.py
  6. validation                              tools/verify_epub.py
  7. git: report anything the build changed outside the ignored output folders

Why one `quarto render` and not one per format: Quarto empties _book/ at the
start of every render, so `quarto render --to pdf` deletes the HTML site and
the EPUBs built a minute earlier (and the Kindle files derived from them).
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
BOOK = os.path.join(ROOT, "_book")
sys.path.insert(0, TOOLS)
import check_env  # noqa: E402

PY = sys.executable
TIMES: list[tuple[str, float]] = []


def step(title: str) -> float:
    print(f"\n=== {title} ===", flush=True)
    return time.time()


def done(title: str, t0: float) -> None:
    TIMES.append((title, time.time() - t0))


def run(cmd: list[str], env: dict) -> None:
    exe = shutil.which(cmd[0], path=env.get("PATH")) or cmd[0]
    print("$ " + " ".join(cmd), flush=True)
    code = subprocess.run([exe] + cmd[1:], cwd=ROOT, env=env).returncode
    if code != 0:
        sys.exit(f"build_all: `{' '.join(cmd)}` failed (exit {code}) -- see the output above")


def stale_figures() -> list[str]:
    """Figures whose PDF or SVG is missing or older than their .tex source, or
    whose PDF was never cropped.

    The last case is what an interrupted build_diagrams.py leaves behind: a
    fresh lualatex PDF (newer than the .tex, so dates look fine) that is still
    the whole 3402 pt canvas with the drawing in one corner. Cropping sets the
    CropBox, so CropBox == MediaBox means the crop never ran.
    """
    import pymupdf
    out = []
    for tex in sorted(glob.glob(os.path.join(ROOT, "diagrams", "*.tex"))):
        base = os.path.splitext(os.path.basename(tex))[0]
        if base.startswith("_"):
            continue
        src = os.path.getmtime(tex)
        for ext in (".pdf", ".svg"):
            built = os.path.join(ROOT, "diagrams", base + ext)
            if not os.path.exists(built) or os.path.getmtime(built) < src:
                out.append(base)
                break
        else:
            try:
                page = pymupdf.open(os.path.join(ROOT, "diagrams", base + ".pdf"))[0]
                if page.cropbox == page.mediabox:
                    out.append(base)
            except Exception:
                out.append(base)
    return out


def git_status() -> set[str] | None:
    try:
        p = subprocess.run(["git", "-c", "core.quotepath=false", "status", "--porcelain",
                            "--untracked-files=all"], cwd=ROOT, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
    except OSError:
        return None
    return set(p.stdout.splitlines()) if p.returncode == 0 else None


def book_unlocked() -> bool:
    if not os.path.isdir(BOOK):
        return True
    probe = BOOK + ".locktest"
    try:
        os.rename(BOOK, probe)
        os.rename(probe, BOOK)
        return True
    except OSError:
        return False


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force-diagrams", action="store_true", help="rebuild every figure")
    ap.add_argument("--skip-render", action="store_true",
                    help="reuse the HTML/PDF/EPUB already in _book/")
    ap.add_argument("--no-kindle", action="store_true", help="skip the Kindle edition and cover")
    ap.add_argument("--no-verify", action="store_true", help="skip epubcheck and the audits")
    ap.add_argument("--kindle-previewer", action="store_true",
                    help="also convert with Kindle Previewer (Windows/macOS, ~1 h)")
    args = ap.parse_args()
    env = check_env.tex_env()   # TinyTeX on PATH + repo fonts in OSFONTDIR
    before = git_status()
    t_all = time.time()

    t0 = step("1/7 toolchain")
    report = check_env.check(quick=True)
    if report.missing():
        sys.exit("build_all: fix the missing items above first "
                 "(new computer: tools/setup_windows.ps1, see docs/BUILD.md)")
    if not args.no_verify and not (check_env_has(report, "Java") and check_env_has(report, "epubcheck")):
        sys.exit("build_all: the verify step needs Java + epubcheck: "
                 "python tools/verify_epub.py --install-tools   (or pass --no-verify)")
    done("toolchain", t0)

    if not args.skip_render:
        t0 = step("2/7 figures (diagrams/*.tex -> PDF + SVG)")
        if args.force_diagrams:
            run([PY, "tools/build_diagrams.py"], env)
        else:
            todo = stale_figures()
            if not todo:
                print("all figures up to date")
            elif len(todo) > 20:
                print(f"{len(todo)} figures to build")
                run([PY, "tools/build_diagrams.py"], env)
            else:
                for base in todo:
                    run([PY, "tools/build_diagrams.py", base], env)
        import build_cover
        if build_cover.missing():
            run([PY, "tools/build_cover.py"], env)
        done("figures", t0)

        t0 = step("3/7 quarto render (HTML + PDF + EPUB)")
        if not book_unlocked():
            sys.exit("build_all: _book/ is in use by another program, so Quarto could not "
                     "replace it. Close Explorer windows, terminals that are cd'ed into "
                     "_book/ and PDF/EPUB viewers showing a file from it, then retry.")
        run(["quarto", "render"], env)
        for pattern in ("index.html", "*.pdf", "*.epub"):
            if not glob.glob(os.path.join(BOOK, pattern)):
                sys.exit(f"build_all: quarto render produced no _book/{pattern}")
        done("quarto render", t0)

    if not args.no_kindle:
        t0 = step("4/7 Kindle edition")
        run([PY, "tools/build_kindle_epub.py"], env)
        done("Kindle edition", t0)
        t0 = step("5/7 Kindle marketing cover")
        run([PY, "tools/make_kindle_cover.py"], env)
        done("Kindle cover", t0)

    if not args.no_verify:
        t0 = step("6/7 validation")
        run([PY, "tools/verify_epub.py", "--epubcheck-only"], env)
        if not args.no_kindle:
            run([PY, "tools/kindle_audit.py", "-q"], env)
            if args.kindle_previewer:
                # the Kindle edition only: on a math-heavy book Previewer chews
                # on the main EPUB's MathML for hours without finishing
                for kindle in sorted(glob.glob(os.path.join(BOOK, "*-kindle.epub"))):
                    run([PY, "tools/verify_epub.py", "--previewer-only",
                         os.path.relpath(kindle, ROOT)], env)
        done("validation", t0)

    step("7/7 git working tree")
    after = git_status()
    if before is None or after is None:
        print("not a git checkout -- skipped")
    else:
        changed = sorted(after - before)
        if changed:
            print("the build changed these tracked/unignored files (review before committing):")
            for line in changed:
                print("   " + line)
        else:
            print("the build left the git working tree as it found it "
                  "(all outputs are in ignored folders)")

    print("\n=== outputs (_book/) ===")
    for path in sorted(glob.glob(os.path.join(BOOK, "*.*")) +
                       glob.glob(os.path.join(BOOK, "kindle-preview", "*.kpf"))):
        if path.endswith((".pdf", ".epub", ".jpg", ".tif", ".kpf")) or path.endswith("index.html"):
            print(f"  {os.path.getsize(path) / 2**20:7.1f} MB  {os.path.relpath(path, ROOT)}")
    print("\n=== time ===")
    for title, secs in TIMES:
        print(f"  {title:16s} {secs / 60:6.1f} min")
    print(f"  {'total':16s} {(time.time() - t_all) / 60:6.1f} min")
    return 0


def check_env_has(report: "check_env.Report", what: str) -> bool:
    return any(r[1] == what and r[0] == "ok" for r in report.rows)


if __name__ == "__main__":
    sys.exit(main())
