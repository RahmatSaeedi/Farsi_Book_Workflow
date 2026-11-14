#!/usr/bin/env python3
"""Unwrap pure-math .ltr spans:  [$...$]{.ltr}  ->  $...$

Math is already left-to-right in both HTML (MathJax) and PDF (LaTeX math mode),
so an .ltr wrapper around math is redundant. Worse, Pandoc renders inline math
inside a span as \\(...\\), and \\babelsublr{\\(...\\)} breaks under babel/lualatex
for some content (e.g. operators like \\max). Dropping the wrapper fixes the
whole class. Only spans whose ENTIRE content is one math run are unwrapped;
mixed text+math spans are left untouched. Code regions are masked.

Usage: python tools/source-fixes/unwrap_math_ltr.py
"""
import re, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILES = glob.glob(os.path.join(ROOT, "chapters", "*.qmd")) + \
        glob.glob(os.path.join(ROOT, "appendices", "*.qmd"))

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")
MATHSPAN = re.compile(r"\[\s*(\$[^$\n]+\$)\s*\]\{\.ltr\}")

def main():
    changed = total = 0
    for f in FILES:
        t0 = open(f, encoding="utf-8").read()
        store = []
        def rp(m):
            store.append(m.group(0)); return "\x00%d\x00" % (len(store) - 1)
        t = FENCE.sub(rp, t0)
        t = INLINE.sub(rp, t)
        t, n = MATHSPAN.subn(r"\1", t)
        for i, s in enumerate(store):
            t = t.replace("\x00%d\x00" % i, s)
        if t != t0:
            open(f, "w", encoding="utf-8", newline="\n").write(t)
            changed += 1
            total += n
    print(f"Unwrapped {total} math .ltr spans across {changed} files.")

if __name__ == "__main__":
    main()
