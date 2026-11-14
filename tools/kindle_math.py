#!/usr/bin/env python3
"""MathML -> Unicode text, for the Kindle edition of the book.

Kindle renders MathML only under Enhanced Typesetting, and Enhanced Typesetting
does not support Persian (Kindle Publishing Guidelines 11.6 + 17.5). So the
Kindle EPUB cannot ship MathML at all. Every expression becomes either

  * real Unicode text  -- when it can be written faithfully with characters an
    e-reader font actually has (this module), so it still reflows, resizes with
    the reader's font, and is readable by a screen reader; or
  * a PNG image        -- everything else (tools/build_kindle_epub.py).

Text is strongly preferred: guideline 11.4.8 says "Prefer HTML to Images", and
an inline image that cannot follow the reader's font size looks wrong at every
setting but one. This module is deliberately conservative -- it returns None
(meaning "rasterize it") for anything it cannot render exactly.

Run directly to self-test the conversion table:  python tools/kindle_math.py
"""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET

MATHML_NS = "http://www.w3.org/1998/Math/MathML"

# Unicode subscript/superscript forms, restricted to the ones an e-reader font
# can be relied on to have: the Latin-1 powers (¹²³) and the Superscripts and
# Subscripts block (U+2070..U+209C). The alphabetic forms outside that block --
# ˣ ʰ ʲ (Spacing Modifier Letters) and ᵃ ᵇ ᶜ ᵢ ᵣ (Phonetic Extensions) -- are
# deliberately absent: they are real Unicode but patchily supported, and a
# missing glyph shows as tofu. Anything they would be needed for is rasterized.
SUBSCRIPTS = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆",
    "7": "₇", "8": "₈", "9": "₉", "+": "₊", "-": "₋", "−": "₋",
    "=": "₌", "(": "₍", ")": "₎", "a": "ₐ", "e": "ₑ", "h": "ₕ", "k": "ₖ",
    "l": "ₗ", "m": "ₘ", "n": "ₙ", "o": "ₒ", "p": "ₚ", "s": "ₛ", "t": "ₜ",
    "x": "ₓ", "ə": "ₔ",
}
SUPERSCRIPTS = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶",
    "7": "⁷", "8": "⁸", "9": "⁹", "+": "⁺", "-": "⁻", "−": "⁻",
    "=": "⁼", "(": "⁽", ")": "⁾", "i": "ⁱ", "n": "ⁿ",
}

# Token elements we can emit verbatim, and the containers we can flatten.
TOKENS = {"mi", "mn", "mo", "mtext", "ms"}
SCRIPTS = {"msub", "msup", "msubsup"}
TRANSPARENT = {"mrow", "mstyle", "semantics", "math", "mpadded"}

# mspace widths, in em, mapped to a real space or nothing. texmath emits thin
# negative kerns around delimiters that carry no meaning in flowing text.
# A plain U+0020, not U+2009 THIN SPACE: every font has the former, and the
# latter is outside the safe ranges below, so it would send a whole
# expression to the rasteriser over nothing more than a kern.
THIN_SPACE = " "

# Relations read as cramped without space around them ("T2<=2T1"). Relations
# only: a binary +, - or x can be unary, where a leading space would be wrong.
RELATIONS = set("=≠≈≃≅≤≥<>≪≫→←↔⇒⇐⇔∝≡∼≲≳∈∉⊂⊆")

# Characters that are safe to put in an e-book: an e-reader font must actually
# have the glyph, or the reader sees tofu. Mathematical Alphanumeric Symbols
# (bold/script/fraktur letters, U+1D400..U+1D7FF) are the notable trap -- most
# reading-system fonts lack them -- so an expression using them is rasterized.
SAFE_RANGES = (
    (0x0020, 0x007E),  # ASCII
    (0x00A0, 0x00FF),  # Latin-1 supplement (µ, °, ±, ×, ÷, superscript 1/2/3)
    (0x0370, 0x03FF),  # Greek
    (0x0600, 0x06FF),  # Arabic/Persian
    (0x200C, 0x200D),  # ZWNJ / ZWJ (Persian needs them)
    (0x2010, 0x201F),  # dashes and quotes
    (0x2030, 0x205E),  # per-mille, primes, thin space, bullet
    (0x2070, 0x209F),  # super/subscripts
    (0x20A0, 0x20BF),  # currency
    (0x2100, 0x214F),  # letterlike (ℏ, ℓ, ℝ, ™)
    (0x2190, 0x21FF),  # arrows
    (0x2200, 0x22FF),  # mathematical operators
    (0x2300, 0x23FF),  # misc technical (⌈ ⌉ ⌊ ⌋)
    (0x25A0, 0x25FF),  # geometric shapes
    (0x2A00, 0x2AFF),  # supplemental operators
)


def is_safe(text: str) -> bool:
    """True when every character is one an e-reader font is likely to have."""
    return all(any(lo <= ord(c) <= hi for lo, hi in SAFE_RANGES) for c in text)


def local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _script(text: str, table: dict[str, str]) -> str | None:
    """Render `text` as sub/superscript characters, or None if impossible."""
    if not text:
        return None
    # 90^\circ: texmath makes the ring an <mo>, but the degree sign is exactly
    # what it means and every font has it.
    if table is SUPERSCRIPTS and text.strip() in ("∘", "◦", "°"):
        return "°"
    out = []
    for ch in text:
        if ch not in table:
            return None
        out.append(table[ch])
    return "".join(out)


def _convert(el: ET.Element) -> str | None:
    """Recursively convert one MathML element; None means "not representable"."""
    tag = local(el.tag)

    if tag == "annotation":
        return ""  # the TeX source is metadata, never displayed text
    if tag == "mspace":
        width = el.get("width", "0")
        try:
            em = float(re.sub(r"[a-z%]+$", "", width))
        except ValueError:
            em = 0.0
        return THIN_SPACE if em >= 0.2 else ""
    if tag in TOKENS:
        text = (el.text or "") + "".join(
            (c.text or "") + (c.tail or "") for c in el
        )
        if tag == "mo" and text.strip() in RELATIONS:
            return f" {text.strip()} "
        return text
    if tag in TRANSPARENT:
        parts = [(el.text or "").strip()]
        for child in el:
            piece = _convert(child)
            if piece is None:
                return None
            parts.append(piece)
            parts.append((child.tail or "").strip())
        return "".join(parts)
    if tag in SCRIPTS:
        kids = list(el)
        if tag == "msubsup":
            if len(kids) != 3:
                return None
            base, sub, sup = (_convert(k) for k in kids)
            if base is None or sub is None or sup is None:
                return None
            s, p = _script(sub, SUBSCRIPTS), _script(sup, SUPERSCRIPTS)
            return None if s is None or p is None else base + s + p
        if len(kids) != 2:
            return None
        base, script = _convert(kids[0]), _convert(kids[1])
        if base is None or script is None:
            return None
        table = SUBSCRIPTS if tag == "msub" else SUPERSCRIPTS
        rendered = _script(script, table)
        return None if rendered is None else base + rendered

    return None  # mfrac, msqrt, mtable, mover, menclose, ... -> rasterize


def mathml_to_unicode(fragment: str) -> str | None:
    """Convert one <math>...</math> fragment to text, or None to rasterize it.

    Returns None whenever the expression uses a construction Unicode cannot
    carry (fractions, radicals, matrices, over/underscripts) or a character an
    e-reader font is unlikely to have.
    """
    try:
        root = ET.fromstring(fragment)
    except ET.ParseError:
        return None
    text = _convert(root)
    if text is None:
        return None
    text = re.sub(r" {2,}", " ", unicodedata.normalize("NFC", text)).strip()
    if not text or not is_safe(text):
        return None
    return text


def _selftest() -> int:
    cases = [
        ('<math xmlns="%s"><semantics><msub><mi>B</mi><mn>0</mn></msub>'
         '<annotation encoding="application/x-tex">B_0</annotation>'
         "</semantics></math>" % MATHML_NS, "B₀"),
        ('<math xmlns="%s"><semantics><msub><mi>T</mi><mn>1</mn></msub>'
         "</semantics></math>" % MATHML_NS, "T₁"),
        ('<math xmlns="%s"><mi>λ</mi></math>' % MATHML_NS, "λ"),
        ('<math xmlns="%s"><msup><mi>x</mi><mn>2</mn></msup></math>' % MATHML_NS, "x²"),
        ('<math xmlns="%s"><msup><mn>10</mn><mrow><mi>−</mi><mn>3</mn></mrow>'
         "</msup></math>" % MATHML_NS, "10⁻³"),
        # superscript letters have unreliable glyph coverage -> rasterize
        ('<math xmlns="%s"><msup><mi>e</mi><mrow><mi>−</mi><mi>x</mi></mrow>'
         "</msup></math>" % MATHML_NS, None),
        # not representable -> None
        ('<math xmlns="%s"><mfrac><mn>1</mn><mn>2</mn></mfrac></math>' % MATHML_NS, None),
        ('<math xmlns="%s"><msqrt><mn>2</mn></msqrt></math>' % MATHML_NS, None),
        # bold math letter: valid Unicode but missing from e-reader fonts
        ('<math xmlns="%s"><mi>\U0001D400</mi></math>' % MATHML_NS, None),
        # superscript with no Unicode form (T_2^*)
        ('<math xmlns="%s"><msubsup><mi>T</mi><mn>2</mn><mo>∗</mo></msubsup>'
         "</math>" % MATHML_NS, None),
    ]
    failed = 0
    for src, want in cases:
        got = mathml_to_unicode(src)
        ok = got == want
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {got!r:12} expected {want!r}")
    print("all passed" if not failed else f"{failed} failure(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
