#!/usr/bin/env python3
"""Trim whitespace adjacent to inline-math $ delimiters.

Pandoc treats `$...$` as math only if there is NO space just inside the
delimiters. Authors sometimes wrote `$\\cos(x) $` (space before closing $),
which Pandoc then renders as literal text (escaping _, {, $ ...) and breaks the
PDF. This rewrites `$<sp>core<sp>$` -> `$core$` for inline math. Fenced/inline
code and display math ($$...$$) are masked and never touched.

Usage: python tools/source-fixes/fix_math_spacing.py
"""
import re, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILES = glob.glob(os.path.join(ROOT, "chapters", "*.qmd")) + \
        glob.glob(os.path.join(ROOT, "appendices", "*.qmd"))

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")
DISPLAY = re.compile(r"\$\$.*?\$\$", re.S)
# inline math: unescaped single $ ... unescaped single $ (no newlines)
IMATH = re.compile(r"(?<!\\)\$(?!\$)[ \t]*(.+?)[ \t]*(?<!\\)\$(?!\$)")

def main():
    changed = total = 0
    for f in FILES:
        t0 = open(f, encoding="utf-8").read()
        store = []
        def rp(m):
            store.append(m.group(0)); return "\x00%d\x00" % (len(store) - 1)
        t = FENCE.sub(rp, t0)
        t = INLINE.sub(rp, t)
        t = DISPLAY.sub(rp, t)
        t, n = IMATH.subn(lambda m: "$" + m.group(1) + "$", t)
        for i, s in enumerate(store):
            t = t.replace("\x00%d\x00" % i, s)
        if t != t0:
            open(f, "w", encoding="utf-8", newline="\n").write(t)
            changed += 1
            total += n
    print(f"Trimmed inline-math delimiters in {changed} files ({total} spans seen).")

if __name__ == "__main__":
    main()
