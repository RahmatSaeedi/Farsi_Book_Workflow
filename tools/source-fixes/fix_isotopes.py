#!/usr/bin/env python3
"""Render isotopes correctly: $^13C$ -> ${}^{13}\\mathrm{C}$ (mass superscript,
element symbol upright at baseline).

Authors wrote isotopes as `$^13C$`, `$^23Na$`, `$^{19F}$` etc. In math `^13C`
superscripts only the first digit ("¹3C"); `^{23Na}` raises the whole thing.
The correct notation is a pre-superscript mass number with an upright element
symbol. We match `^<digits><Element>` INSIDE math and rewrite ONLY when
(mass, element) is a real isotope — so exponents like d^3r, \\nabla^2 M, b^{2G}
are never touched (the element must be a capitalized real symbol in the list).

Usage: python tools/source-fixes/fix_isotopes.py
"""
import re, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILES = glob.glob(os.path.join(ROOT, "chapters", "*.qmd")) + \
        glob.glob(os.path.join(ROOT, "appendices", "*.qmd"))

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")
MATH = re.compile(r"\$\$.*?\$\$|\$[^$\n]*?\$", re.S)
# ^ then optional {, digits, an element symbol (Cap + optional lower), optional }
ISO = re.compile(r"\^\{?(\d{1,3})([A-Z][a-z]?)\}?(?![A-Za-z])")

KNOWN = {
    ("1","H"),("2","H"),("3","H"),("3","He"),("4","He"),("6","Li"),("7","Li"),
    ("9","Be"),("10","B"),("11","B"),("12","C"),("13","C"),("14","N"),("15","N"),
    ("16","O"),("17","O"),("18","O"),("19","F"),("21","Ne"),("23","Na"),("25","Mg"),
    ("27","Al"),("29","Si"),("31","P"),("33","S"),("35","Cl"),("37","Cl"),("39","K"),
    ("40","K"),("43","Ca"),("51","V"),("57","Fe"),("63","Cu"),("65","Cu"),("77","Se"),
    ("79","Br"),("81","Br"),("87","Rb"),("129","Xe"),("131","Xe"),("133","Cs"),
    ("195","Pt"),("207","Pb"),
}

def fix_block(block):
    def rep(m):
        mass, el = m.group(1), m.group(2)
        if (mass, el) in KNOWN:
            return "{}^{" + mass + "}\\mathrm{" + el + "}"
        return m.group(0)
    return ISO.sub(rep, block.group(0))

def main():
    changed = 0
    for f in FILES:
        t0 = open(f, encoding="utf-8").read()
        store = []
        def rp(m):
            store.append(m.group(0)); return "\x00%d\x00" % (len(store) - 1)
        t = FENCE.sub(rp, t0)
        t = INLINE.sub(rp, t)
        t = MATH.sub(fix_block, t)
        for i, s in enumerate(store):
            t = t.replace("\x00%d\x00" % i, s)
        if t != t0:
            open(f, "w", encoding="utf-8", newline="\n").write(t)
            changed += 1
    print(f"Fixed isotopes in {changed} files.")

if __name__ == "__main__":
    main()
