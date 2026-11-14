#!/usr/bin/env python3
"""Make agent-written chapters render-safe under LuaLaTeX + babel.

The writers sometimes put raw LaTeX math (\\mathbf, \\gamma, B_0, ...) inside an
[...]{.ltr} span. That becomes \\babelsublr{...} which is OUTSIDE math mode and
breaks the PDF build. This script rewrites such spans so they are always either
math ($...$) or inline code (`...`) — both safe for backslashes and underscores.

Rules for an [INNER]{.ltr} span (only when INNER has no $ and no backtick):
  * INNER contains a backslash            -> math:  [$INNER$]{.ltr}
  * INNER has _ or ^ and looks math-like  -> math:  [$INNER$]{.ltr}
      (math-like = base before first _/^ is <=2 chars, OR INNER has { or ^)
  * INNER has _ or ^ but looks like code  -> code:  `INNER`

Usage: python tools/source-fixes/fix_ltr_math.py
"""
import re, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILES = glob.glob(os.path.join(ROOT, "chapters", "*.qmd")) + \
        glob.glob(os.path.join(ROOT, "appendices", "*.qmd"))

SPAN = re.compile(r"\[([^\]]*?)\]\{\.ltr\}")

def math_like(inner):
    if "{" in inner or "^" in inner:
        return True
    # base = token before the first _ or ^
    cut = len(inner)
    for ch in ("_", "^"):
        p = inner.find(ch)
        if p != -1:
            cut = min(cut, p)
    base = inner[:cut]
    return len(base) <= 2

def fix_span(m):
    inner = m.group(1)
    if "$" in inner or "`" in inner:
        return m.group(0)
    has_bs = "\\" in inner
    has_ss = ("_" in inner) or ("^" in inner)
    if not (has_bs or has_ss):
        return m.group(0)
    if has_bs or math_like(inner):
        return "[$" + inner + "$]{.ltr}"
    # underscore/caret but code-like (e.g. solve_ivp) -> inline code
    return "`" + inner + "`"

def main():
    total_spans = 0
    changed_files = 0
    for f in FILES:
        t = open(f, encoding="utf-8").read()
        orig = t
        t, n = SPAN.subn(fix_span, t)
        # count actual changes (subn counts all matches; recompute changed)
        if t != orig:
            with open(f, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(t)
            changed_files += 1
            total_spans += n
    print(f"Rewrote spans in {changed_files} files.")

if __name__ == "__main__":
    main()
