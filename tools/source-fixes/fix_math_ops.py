#!/usr/bin/env python3
"""Brace bare operator macros used as sub/superscripts, INSIDE math.

`\\max` (and other \\mathop operators) cannot be a bare subscript: `G_\\max`
raises "Missing { inserted". The fix is `G_{\\max}`. Operators take no argument,
so adding braces is always safe. We do NOT touch argument-taking macros
(\\frac, \\sqrt, \\hat, ...) or single-symbol macros (\\gamma) — only the
explicit operator list. Inside $...$ / $$...$$ only; code is masked.

Usage: python tools/source-fixes/fix_math_ops.py
"""
import re, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILES = glob.glob(os.path.join(ROOT, "chapters", "*.qmd")) + \
        glob.glob(os.path.join(ROOT, "appendices", "*.qmd"))

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")
MATH = re.compile(r"\$\$.*?\$\$|\$[^$\n]*?\$", re.S)
OPS = ("max|min|det|lim|sup|inf|arg|gcd|deg|dim|ker|exp|log|ln|"
       "sin|cos|tan|cot|sec|csc|sinh|cosh|tanh|coth|Pr|liminf|limsup")
OPSUB = re.compile(r"([_^])\\(" + OPS + r")\b")

def fix_math(block):
    return OPSUB.sub(r"\1{\\\2}", block.group(0))

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
    print(f"Braced operator sub/superscripts in {changed} files.")

if __name__ == "__main__":
    main()
