#!/usr/bin/env python3
"""Second-pass render-safety fix: [...]{.ltr} spans whose CONTENT contains
square brackets (e.g. \\big[...\\big], commutators [A,B], \\left[...\\right]).

A naive regex stops at the first inner ']'; here we match the span by walking
left from ']{.ltr}' with a bracket-depth counter to find the true opener, then
wrap raw-LaTeX content in $...$ (or convert code-like underscores to inline code).

Usage: python tools/source-fixes/fix_ltr_brackets.py
"""
import re, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILES = glob.glob(os.path.join(ROOT, "chapters", "*.qmd")) + \
        glob.glob(os.path.join(ROOT, "appendices", "*.qmd"))
CLOSER = re.compile(r"\]\{\.ltr\}")

def math_like(inner):
    if "{" in inner or "^" in inner:
        return True
    cut = len(inner)
    for ch in ("_", "^"):
        p = inner.find(ch)
        if p != -1:
            cut = min(cut, p)
    return len(inner[:cut]) <= 2

def find_spans(t):
    spans = []
    for m in CLOSER.finditer(t):
        j = m.start()           # index of the closing ']'
        depth, i = 1, j - 1
        while i >= 0:
            c = t[i]
            if c == "]":
                depth += 1
            elif c == "[":
                depth -= 1
                if depth == 0:
                    break
            i -= 1
        if depth == 0 and i >= 0:
            spans.append((i, j, m.end()))   # '[' at i, ']' at j, end after '}'
    return spans

def main():
    changed = 0
    for f in FILES:
        t = open(f, encoding="utf-8").read()
        spans = find_spans(t)
        edits = []
        for (i, j, e) in spans:
            content = t[i + 1:j]
            # skip only if already real math (an UNescaped $) or inline code;
            # an escaped \$ (a literal dollar sign, e.g. money) is NOT math.
            if re.search(r"(?<!\\)\$", content) or "`" in content:
                continue
            has_bs = "\\" in content
            has_ss = ("_" in content) or ("^" in content)
            # a leading sign followed by a NON-digit (e.g. +x, -y) makes babel's
            # \babelsublr scan a number and fail; render it as math instead.
            lead_sign = bool(re.match(r"\s*[+-][^0-9.\s]", content))
            if not (has_bs or has_ss or lead_sign):
                continue
            if has_bs or lead_sign or math_like(content):
                repl = "[$" + content + "$]{.ltr}"
            else:
                repl = "`" + content + "`"
            edits.append((i, e, repl))
        if not edits:
            continue
        # apply right-to-left so indices stay valid
        edits.sort(key=lambda x: -x[0])
        for (i, e, repl) in edits:
            t = t[:i] + repl + t[e:]
        with open(f, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(t)
        changed += 1
    print(f"Fixed bracketed .ltr spans in {changed} files.")

if __name__ == "__main__":
    main()
