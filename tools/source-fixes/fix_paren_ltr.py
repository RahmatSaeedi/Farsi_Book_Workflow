#!/usr/bin/env python3
"""Fix `(English){.ltr}` -> `[(English)]{.ltr}` (a proper Pandoc LTR span).

Agents attached the .ltr attribute to a PARENTHESIZED group: `(b-value){.ltr}`.
Parens are not a Pandoc span, so the attribute leaks as literal text and can
break the LaTeX build. We move the parens inside a real bracketed span.
Non-nested parens only; code masked.

Usage: python tools/source-fixes/fix_paren_ltr.py
"""
import re, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILES = glob.glob(os.path.join(ROOT, "chapters", "*.qmd")) + \
        glob.glob(os.path.join(ROOT, "appendices", "*.qmd"))

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")
PAREN_LTR = re.compile(r"\(([^()\n]+)\)\{\.ltr\}")

def main():
    changed = total = 0
    for f in FILES:
        t0 = open(f, encoding="utf-8").read()
        store = []
        def rp(m):
            store.append(m.group(0)); return "\x00%d\x00" % (len(store) - 1)
        t = FENCE.sub(rp, t0)
        t = INLINE.sub(rp, t)
        t, n = PAREN_LTR.subn(r"[(\1)]{.ltr}", t)
        for i, s in enumerate(store):
            t = t.replace("\x00%d\x00" % i, s)
        if t != t0:
            open(f, "w", encoding="utf-8", newline="\n").write(t)
            changed += 1
            total += n
    print(f"Fixed {total} (..){{.ltr}} spans across {changed} files.")

if __name__ == "__main__":
    main()
