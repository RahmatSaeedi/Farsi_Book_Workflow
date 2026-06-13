#!/usr/bin/env python3
"""Scaffold a new figure from diagrams/figure-template.tex.

    python tools/new_figure.py 03-my-diagram
    python tools/new_figure.py 03-my-diagram --build   # also build it

Then draw inside diagrams/03-my-diagram.tex and (re)build with
`python tools/build_diagrams.py '03-my-diagram'`.
"""
import os, sys, shutil, subprocess

DIAG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "diagrams")

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_build = "--build" in sys.argv
    if not args:
        sys.exit("usage: python tools/new_figure.py <name> [--build]")
    name = args[0]
    if name.endswith(".tex"):
        name = name[:-4]
    dst = os.path.join(DIAG, name + ".tex")
    if os.path.exists(dst):
        sys.exit(f"refusing to overwrite existing {dst}")
    shutil.copyfile(os.path.join(DIAG, "figure-template.tex"), dst)
    print(f"created diagrams/{name}.tex (from figure-template.tex)")
    if do_build:
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "build_diagrams.py"), name])

if __name__ == "__main__":
    main()
