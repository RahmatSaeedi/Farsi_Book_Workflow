#!/usr/bin/env python3
"""Fix Pandoc-superscript-style double carets INSIDE math (e.g. $T2^*^$).

Authors sometimes wrote T2-star as `$T2^*^$` (Pandoc ^...^ superscript syntax),
which in LaTeX math is a "double superscript" error. INSIDE $...$ / $$...$$ we
collapse only the misuse pattern  ^X^  ->  ^{X}  where X is a SHORT token of
alphanumerics/asterisk and NO operators/spaces — so legitimate expressions like
`a^2 + b^2` (separate superscripts) are never merged. Code is masked.

Usage: python tools/source-fixes/fix_math_supersub.py
"""
import re, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILES = glob.glob(os.path.join(ROOT, "chapters", "*.qmd")) + \
        glob.glob(os.path.join(ROOT, "appendices", "*.qmd"))

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")
MATH = re.compile(r"\$\$.*?\$\$|\$[^$\n]*?\$", re.S)
# an operator/space-free alphanumeric token between two carets = the Pandoc
# superscript misuse (e.g. ^*^, ^2^, ^23Na^). Legitimate separate superscripts
# like `a^2 + b^2` always have a space/operator between, so are never matched.
MISUSE = re.compile(r"\^([A-Za-z0-9*]+)\^")

def fix_math(block):
    return MISUSE.sub(r"^{\1}", block.group(0))

def main():
    changed = 0
    for f in FILES:
        t0 = open(f, encoding="utf-8").read()
        store = []
        def rp(m):
            store.append(m.group(0)); return "\x00%d\x00" % (len(store) - 1)
        t = FENCE.sub(rp, t0)
        t = INLINE.sub(rp, t)
        t = MATH.sub(fix_math, t)
        for i, s in enumerate(store):
            t = t.replace("\x00%d\x00" % i, s)
        if t != t0:
            open(f, "w", encoding="utf-8", newline="\n").write(t)
            changed += 1
    print(f"Fixed math superscripts in {changed} files.")

if __name__ == "__main__":
    main()
