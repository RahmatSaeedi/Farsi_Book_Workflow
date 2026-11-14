#!/usr/bin/env python3
"""Normalize LaTeX-style math delimiters to Pandoc math, outside code regions.

Some agents wrote inline math as \\( ... \\) and display math as \\[ ... \\],
and used \\* (e.g. T_2^\\*). Pandoc passes \\( as raw TeX, which breaks inside
the LTR spans / babel. This converts them to $...$ / $$...$$ and \\* -> *,
masking fenced and inline code so code containing backslashes is untouched.

Idempotent. Usage: python tools/source-fixes/normalize_math.py
"""
import re, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILES = glob.glob(os.path.join(ROOT, "chapters", "*.qmd")) + \
        glob.glob(os.path.join(ROOT, "appendices", "*.qmd"))

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")

def mask(t):
    store = []
    def repl(m):
        store.append(m.group(0))
        return "\x00%d\x00" % (len(store) - 1)
    t = FENCE.sub(repl, t)
    t = INLINE.sub(repl, t)
    return t, store

def unmask(t, store):
    for i, s in enumerate(store):
        t = t.replace("\x00%d\x00" % i, s)
    return t

def main():
    changed = 0
    for f in FILES:
        t0 = open(f, encoding="utf-8").read()
        t, store = mask(t0)
        t = t.replace("\\*", "*")          # escaped asterisk (e.g. T_2^\* -> T_2^*)
        t = t.replace("$\\(", "$").replace("\\)$", "$")  # collapse nested wraps
        # Convert LaTeX math delimiters to Pandoc math, but NEVER touch the
        # double-backslash line breaks \\[ \\] \\( \\) (negative lookbehind).
        t = re.sub(r"(?<!\\)\\\[", "$$", t)
        t = re.sub(r"(?<!\\)\\\]", "$$", t)
        t = re.sub(r"(?<!\\)\\\(", "$", t)
        t = re.sub(r"(?<!\\)\\\)", "$", t)
        t = unmask(t, store)
        if t != t0:
            with open(f, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(t)
            changed += 1
    print(f"Normalized math delimiters in {changed} files.")

if __name__ == "__main__":
    main()
