#!/usr/bin/env python3
r"""Build the Kindle edition of the book from the shipped EPUB.

Why a second EPUB at all
------------------------
The primary `_book/*.epub` is an EPUB3 with MathML math and SVG figures: the
right thing for Apple Books, Kobo and the web, which render both natively.
Kindle is a different matter:

  * MathML does not scale here. Amazon's converter was measured on the
    2,900-page book this workflow was developed for:
    Kindle Previewer chewed on the 39,843 MathML expressions for over two
    hours of CPU without producing a book, while a ten-chapter subset of the
    rasterised edition converted in minutes. KDP fails the same way, which is
    the "We couldn't convert your HTML file to Kindle format" rejection. Every
    expression also carries an `<annotation encoding="application/x-tex">`, so
    a converter that strips MathML can spill raw LaTeX into the text.
    (Guideline 11.6 files MathML under Enhanced Typesetting, and 17.5's ET
    language list omits Persian -- but do not trust that as the reason: a
    minimal Persian book reports ET "Supported", so the list is out of date.)
  * 11.4.11 -- "eBooks with more than 25 SVG images are not supported in
    Enhanced Typesetting"; that book has 227, all using transforms beyond the
    permitted translate(0 0).

So this script rewrites those two things and leaves everything else alone:

  math    -> real Unicode text where it can be written faithfully (see
             tools/kindle_math.py), otherwise a PNG rendered by LuaLaTeX with
             the book's own preamble, sized in em with the true baseline so it
             scales with the reader's font (guideline 11.4.8 prefers text).
  figures -> PNG at >=1200px from the diagram PDFs the repo already builds
             (guideline 11.4.6 wants PNG for line art), with alt text taken
             from each figure's caption (11.4.1, and accessibility section 8).

Everything the audit already found compliant -- NCX + nav + landmarks + guide,
no scripting, ASCII filenames, TTF fonts, cover size -- is carried over intact.

Usage:
    python tools/build_kindle_epub.py                 # _book/<book>.epub -> -kindle.epub
    python tools/build_kindle_epub.py IN.epub -o OUT.epub
    python tools/build_kindle_epub.py --limit 200     # quick partial run for testing
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import html
import io
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fix_epub import repack, report  # noqa: E402
from kindle_math import mathml_to_unicode  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Rendering constants. BASE_PT must match the \documentclass font size below:
# an image of a snippet whose total height is H pt is emitted as H/BASE_PT em,
# so it tracks the reader's font size instead of being pinned to pixels.
BASE_PT = 12.0
MATH_ZOOM = 5.0      # 5 px/pt = 360 ppi at nominal size, over the 300 ppi floor (11.4.2)
FIGURE_MIN_PX = 1400  # >= the 1200 px the guidelines want for a 100% layout
FIGURE_MAX_PIXELS = 5_500_000  # Apple Books rejects images above 5.6 megapixels
                               # (ITMS-9000); Kindle's 300 ppi full page is 2.2 MP
# Math is black on white: 4 grey levels of antialiasing are visually identical
# to 32 at this resolution (checked against a full multi-line derivation) and
# cut the equation payload roughly in half -- which matters, because KDP bills
# a per-MB delivery fee on the 70% royalty plan.
PNG_COLORS = 4

MATH_RE = re.compile(r"<math\b[^>]*>.*?</math>", re.S)
ANNOTATION_RE = re.compile(
    r'<annotation encoding="application/x-tex">(.*?)</annotation>', re.S)
FIGURE_RE = re.compile(r"<figure\b.*?</figure>", re.S)
TAG_RE = re.compile(r"<[^>]+>")
ITEM_RE = re.compile(r"<item\b[^>]*?/?>")


# --------------------------------------------------------------------------
# LaTeX snippet document
# --------------------------------------------------------------------------
# Geometry notes, all established by measurement (see the comments in \snip):
#  * LaTeX's shipout hooks already normalise the origin -- moving it with
#    \hoffset pushes content a full inch off the page.
#  * The class overrides \pagewidth set in the preamble, so the paper is set
#    with `geometry`, and made huge so no display equation can overflow it.
#  * babel's main language is Persian (RTL), so a shipped box is placed against
#    the RIGHT margin and its left edge depends on its own width.
# Hence the calibration page: one solid 10pt square, shipped exactly like a
# snippet, from which the crop origin (right edge, top) is read back.
SNIPPET_PREAMBLE = r"""
\documentclass[12pt]{article}
\usepackage[paperwidth=200cm,paperheight=60cm,margin=10mm]{geometry}
% Quarto's LaTeX template loads amsmath+amssymb for the book, so chapters use
% \checkmark, \gtrsim, \lesssim, ... freely; mathtools alone (which is all
% theme/preamble.tex adds) leaves them undefined and the run dies at 100 errors.
\usepackage{amsmath,amssymb}
\usepackage{mathtools}
\usepackage[bidi=basic]{babel}
\babelprovide[import]{english}
\babelprovide[main, import]{persian}
\babelfont{rm}[Renderer=Node, Path=fonts/, Extension=.ttf,
  UprightFont=*-Regular, BoldFont=*-Bold]{Vazirmatn}
\pagestyle{empty}
\newwrite\dimsout
\immediate\openout\dimsout=snippets-dims.txt
\newcommand{\calibrate}{\shipout\hbox{\vrule width 10pt height 10pt depth 0pt}}
\newcommand{\snip}[2]{%
  \setbox0=\hbox{#2}%
  \immediate\write\dimsout{#1,\the\wd0,\the\ht0,\the\dp0}%
  \shipout\box0
}
\begin{document}
\calibrate
"""


def clean_tex(tex: str) -> str:
    """Make an annotation's TeX safe to put inside \\hbox{...}.

    Blank lines would start a new paragraph and break the box, and display
    equations arrive wrapped in newlines.
    """
    tex = html.unescape(tex).strip()
    return re.sub(r"\n\s*\n+", "\n", tex)


def write_snippet_tex(path: str, snippets: list[tuple[bool, str]]) -> None:
    """One \\snip per distinct expression; display math gets \\displaystyle.

    `\\[...\\]` cannot appear inside an \\hbox, so display style is requested
    explicitly instead -- it renders identically for our purposes.
    """
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(SNIPPET_PREAMBLE)
        for i, (display, tex) in enumerate(snippets):
            body = f"$\\displaystyle {tex}$" if display else f"${tex}$"
            fh.write(f"\\snip{{{i}}}{{{body}}}\n")
        fh.write("\\immediate\\closeout\\dimsout\n\\end{document}\n")


def run_lualatex(tex_path: str, workdir: str, expected_pages: int) -> str:
    """Compile the snippet document and insist on one page per snippet.

    A stale PDF from an earlier run must not be mistaken for success, and TeX
    gives up after 100 errors, so the page count is the check that matters --
    an undefined command in one snippet would otherwise silently lose many.
    """
    pdf_path = os.path.splitext(tex_path)[0] + ".pdf"
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    cmd = ["lualatex", "-interaction=nonstopmode", "-output-directory", workdir,
           tex_path]
    log = os.path.join(workdir, "lualatex.log")
    # Vazirmatn must be in luaotfload's index or the embed step fails with
    # "cannot find file ''" (see docs/BUILD.md, OSFONTDIR)
    env = dict(os.environ)
    fonts = os.path.join(ROOT, "fonts")
    if fonts not in env.get("OSFONTDIR", ""):
        env["OSFONTDIR"] = fonts + (os.pathsep + env["OSFONTDIR"] if env.get("OSFONTDIR") else "")
    with open(log, "w", encoding="utf-8", errors="replace") as fh:
        proc = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, env=env)

    pages = 0
    if os.path.exists(pdf_path):
        import pymupdf as fitz
        with fitz.open(pdf_path) as doc:
            pages = doc.page_count
    if pages == expected_pages + 1:  # +1 for the calibration page
        return pdf_path

    report(f"build_kindle_epub: LuaLaTeX exit {proc.returncode}, "
           f"{pages} pages, expected {expected_pages + 1}")
    for err in latex_errors(log)[:10]:
        report(f"  {err}")
    report(f"  full log: {log}")
    raise SystemExit(1)


def latex_errors(log_path: str) -> list[str]:
    """First line of each TeX error, with the snippet it came from when known."""
    out, pending = [], None
    with open(log_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("! "):
                pending = line
            elif pending and line.startswith("l."):
                m = re.search(r"\\snip\{(\d+)\}", line)
                where = f" (snippet {m.group(1)})" if m else ""
                out.append(f"{pending}{where}")
                pending = None
            elif pending and out and len(out) > 40:
                break
    return out


def render_snippets(pdf_path: str, dims_path: str, count: int):
    """Crop each snippet page to its exact box; yield (index, png, height_em, depth_em)."""
    import pymupdf as fitz  # PyMuPDF
    from PIL import Image

    doc = fitz.open(pdf_path)
    # Calibration page: render at 1x (the paper is huge) and read its ink box.
    pm = doc[0].get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
    cal = Image.open(io.BytesIO(pm.tobytes("png"))).convert("L")
    import numpy as np
    a = np.asarray(cal)
    ys, xs = np.where(a < 200)
    if len(xs) == 0:
        report("build_kindle_epub: calibration page is blank -- cannot locate the crop origin")
        raise SystemExit(1)
    right, top = float(xs.max()) + 1.0, float(ys.min())

    dims = {}
    with open(dims_path, encoding="utf-8") as fh:
        for line in fh:
            idx, wd, ht, dp = line.strip().split(",")
            dims[int(idx)] = tuple(float(v.replace("pt", "")) for v in (wd, ht, dp))
    if len(dims) != count:
        report(f"build_kindle_epub: LaTeX recorded {len(dims)} snippets, expected {count}")
        raise SystemExit(1)

    for idx in range(count):
        wd, ht, dp = dims[idx]
        total = ht + dp
        rect = fitz.Rect(right - wd, top, right, top + total)
        pm = doc[idx + 1].get_pixmap(matrix=fitz.Matrix(MATH_ZOOM, MATH_ZOOM),
                                     clip=rect, alpha=False)
        im = Image.open(io.BytesIO(pm.tobytes("png"))).convert("L")
        im = im.quantize(colors=PNG_COLORS)
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        yield idx, buf.getvalue(), total / BASE_PT, dp / BASE_PT
    doc.close()


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------
def figure_sources() -> dict[str, str]:
    """Map the sha256 of each diagrams/*.svg to its sibling PDF, when present.

    The EPUB renames media to file0.svg, file1.svg, ... so the original is
    recovered by content hash; rasterising the PDF beats rasterising the SVG.
    """
    out = {}
    for svg in glob.glob(os.path.join(ROOT, "diagrams", "*.svg")):
        pdf = os.path.splitext(svg)[0] + ".pdf"
        if os.path.exists(pdf):
            with open(svg, "rb") as fh:
                out[hashlib.sha256(fh.read()).hexdigest()] = pdf
    return out


def rasterize_figure(svg_bytes: bytes, sources: dict[str, str]) -> bytes:
    import pymupdf as fitz
    from PIL import Image

    digest = hashlib.sha256(svg_bytes).hexdigest()
    pdf = sources.get(digest)
    if pdf:
        doc = fitz.open(pdf)
    else:  # not one of ours (or the SVG was post-processed): render it directly
        doc = fitz.open(stream=svg_bytes, filetype="svg")
    page = doc[0]
    zoom = max(1.0, FIGURE_MIN_PX / max(page.rect.width, 1.0))
    # ... but never so large that a big or very tall diagram exceeds the
    # pixel limit of the other stores the same file may be sent to
    area = max(page.rect.width * page.rect.height, 1.0)
    zoom = min(zoom, (FIGURE_MAX_PIXELS / area) ** 0.5)
    pm = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    im = Image.open(io.BytesIO(pm.tobytes("png"))).convert("RGB")
    doc.close()
    # Line art: a small palette is both sharper and far smaller than JPEG.
    im = im.quantize(colors=64, method=Image.MEDIANCUT)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def caption_text(figure_html: str) -> str:
    """Plain-text caption of a <figure>, for the img's alt attribute."""
    m = re.search(r"<figcaption\b[^>]*>(.*?)</figcaption>", figure_html, re.S)
    if not m:
        return ""
    text = html.unescape(TAG_RE.sub(" ", m.group(1)))
    return re.sub(r"\s+", " ", text).strip()[:250]


# --------------------------------------------------------------------------
# Document rewriting
# --------------------------------------------------------------------------
def flatten_math(fragment: str) -> str:
    """Token text of a MathML expression -- the last resort for the nav.

    Images inside table-of-contents labels convert badly, so navigation keeps
    plain text even when the expression is not perfectly representable.
    """
    body = ANNOTATION_RE.sub("", fragment)
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub("", body))).strip()


def rewrite_math(text: str, plan: dict, images: dict, nav: bool) -> tuple[str, dict]:
    """Replace every <math> with Unicode text or an <img>; count what happened."""
    stats = {"unicode": 0, "image": 0, "flattened": 0}

    def repl(m: re.Match) -> str:
        fragment = m.group(0)
        display = 'display="block"' in fragment[:fragment.find(">")]
        tex_m = ANNOTATION_RE.search(fragment)
        tex = clean_tex(tex_m.group(1)) if tex_m else ""
        unicode_text = None if display else mathml_to_unicode(fragment)
        if unicode_text is not None:
            stats["unicode"] += 1
            return html.escape(unicode_text)
        if nav:
            stats["flattened"] += 1
            return html.escape(flatten_math(fragment))
        entry = images.get((display, tex))
        if entry is None:  # --limit run, or the snippet failed to render
            stats["flattened"] += 1
            return html.escape(flatten_math(fragment))
        name, height_em, depth_em = entry
        stats["image"] += 1
        alt = html.escape(tex, quote=True)
        if display:
            style = f"height:{height_em:.3f}em;max-width:100%"
            cls = "eq-display"
        else:
            style = (f"height:{height_em:.3f}em;vertical-align:-{depth_em:.3f}em;"
                     "max-width:100%")
            cls = "eq-inline"
        return (f'<img src="../media/{name}" alt="{alt}" '
                f'class="{cls}" style="{style}" />')

    return MATH_RE.sub(repl, text), stats


def rewrite_figures(text: str, renamed: dict[str, str]) -> tuple[str, int]:
    """Point every figure at its PNG and give it alt text from its caption."""
    filled = 0

    def in_figure(m: re.Match) -> str:
        block = m.group(0)
        alt = caption_text(block)
        if not alt:
            return block

        def fix_img(im: re.Match) -> str:
            nonlocal filled
            tag = im.group(0)
            if 'alt=""' not in tag:
                return tag
            filled += 1
            return tag.replace('alt=""', f'alt="{html.escape(alt, quote=True)}"')

        return re.sub(r"<img\b[^>]*>", fix_img, block)

    text = FIGURE_RE.sub(in_figure, text)
    for old, new in renamed.items():
        text = text.replace(old, new)
    return text, filled


# Inline equations carry their own height/vertical-align, but the display ones
# still need to be centred blocks. Kept minimal: guideline 11.3.2 wants body
# text left to the reader's defaults.
EQUATION_CSS = """
/* Kindle edition: math rendered as images (see tools/build_kindle_epub.py). */
img.eq-inline { display: inline; vertical-align: baseline; }
img.eq-display { display: block; margin: 0.7em auto; }
"""


# --------------------------------------------------------------------------
# Code blocks
# --------------------------------------------------------------------------
# Kindle cannot wrap a <pre>. Guideline 18.1 lists the supported values of
# `white-space` as "nowrap, normal" and of `display` without inline-block: the
# `pre-wrap` that theme/epub.css uses for every other reader is dropped, so a
# code line longer than the screen simply runs off its edge (seen in Kindle
# Previewer: listings cut off on the right, on a phone after ~45 characters,
# while the book has lines of up to 154). So for Kindle each line of a listing
# becomes an ordinary paragraph that wraps like text:
#   * leading indentation and runs of spaces are kept with no-break spaces
#     (the last space of a run stays a normal one, so the line can still break);
#   * a wrapped line continues with a hanging indent, which tells a
#     continuation from a new line of code;
#   * a line holding one long unbreakable token (a URL, a path) may break
#     anywhere -- `word-break: break-all` is supported;
#   * Pandoc's per-line <span id="cbN-M"> and the highlighting spans stay, so
#     colours and links to a line keep working. The <code> wrapper keeps the
#     monospaced face (11.3.8).
PRE_RE = re.compile(r"<pre\b([^>]*)>(.*?)</pre>", re.S)
LONG_TOKEN = 28
CODE_CSS = """
/* Kindle edition: listings as wrapping lines (see rewrite_code in
   tools/build_kindle_epub.py). */
div.kcode { margin: 1em 0; padding: 0.5em 0.6em; text-align: left; font-size: 0.8em;
            color: #003b4f; background-color: #f1f3f5; }
/* A listing with a highlighted language sits in Pandoc's div.sourceCode, which
   carries the grey panel; one without (Gmsh .geo, Elmer .sif, GetDP .pro,
   plain text) has no wrapper, so the panel is drawn by div.kcode itself. */
div.sourceCode div.kcode { margin: 0; }
p.kline { margin: 0; padding-left: 6%; text-indent: -6%; text-align: left; white-space: normal; }
p.kline code { white-space: normal; }
p.kbreak { word-break: break-all; }
"""


def _code_spaces(text: str, at_line_start: bool) -> str:
    """Make the spaces of a text node survive `white-space: normal`."""
    text = text.replace("\t", "    ")
    if at_line_start:
        lead = len(text) - len(text.lstrip(" "))
        text = "\u00a0" * lead + text[lead:]
    return re.sub(r" {2,}", lambda m: "\u00a0" * (len(m.group(0)) - 1) + " ", text)


def _code_line(line: str, carry: list[str]) -> tuple[str, list[str]]:
    """One source line -> balanced inline HTML; `carry` = spans left open before it."""
    out = list(carry)
    stack = list(carry)
    seen_text = False
    for part in re.split(r"(<[^>]+>)", line):
        if not part:
            continue
        if part.startswith("<"):
            if part.startswith("</span"):
                if stack:
                    stack.pop()
                    out.append(part)
            elif part.startswith("<span"):
                stack.append(part)
                out.append(part)
            else:
                out.append(part)
        else:
            out.append(_code_spaces(part, not seen_text))
            if part.strip(" \t"):
                seen_text = True
            elif not seen_text and part:
                seen_text = len(part.strip(" \t")) > 0
    out.append("</span>" * len(stack))
    return "".join(out), stack


def rewrite_code(text: str) -> tuple[str, int]:
    """Turn every <pre> listing into wrapping lines; returns (text, blocks)."""
    count = 0

    def one(m: re.Match) -> str:
        nonlocal count
        body = m.group(2)
        inner = re.fullmatch(r"\s*<code\b[^>]*>(.*)</code>\s*", body, re.S)
        if inner:
            body = inner.group(1)
        # the empty per-line anchors only serve the web version's line numbers
        body = re.sub(r'<a\b[^>]*aria-hidden="true"[^>]*>\s*</a>', "", body)
        body = body.strip("\n")
        lines, carry = [], []
        for raw in body.split("\n"):
            html_line, carry = _code_line(raw.rstrip(), carry)
            plain = html.unescape(TAG_RE.sub("", raw))
            if not plain.strip():
                html_line = html_line + "\u00a0" if not TAG_RE.sub("", html_line) else html_line
            longest = max((len(tok) for tok in plain.split()), default=0)
            cls = "kline kbreak" if longest > LONG_TOKEN else "kline"
            lines.append(f'<p class="{cls}" dir="ltr"><code dir="ltr">{html_line}</code></p>')
        count += 1
        return '<div class="kcode" dir="ltr">\n' + "\n".join(lines) + "\n</div>"

    return PRE_RE.sub(one, text), count


def body_defaults(css: str) -> tuple[str, list[str]]:
    """Hand the body text back to the reader's settings (guideline 11.3.2).

    "Body text must use the default font size (1em) and line height", must not
    be force-aligned (11.3.1), and the main font belongs on <body> only
    (11.3.9: a font-family repeated on every element is an "override conflict",
    for which the converter strips the embedded fonts altogether). theme/epub.css
    sets all three for Apple Books, where they are wanted, so only the Kindle
    copy is changed:
      * `line-height` and `text-align` leave the `html, body` rule (headings
        keep their own alignment, as 11.3.1 asks);
      * a rule that does nothing but repeat the body's font-family on the
        text elements is dropped -- they inherit it.
    """
    notes: list[str] = []

    def strip_body(m: re.Match) -> str:
        decls = m.group(2)
        for prop in ("line-height", "text-align"):
            new = re.sub(r"\s*(?<![\w-])%s\s*:[^;}]*;?" % prop, "", decls)
            if new != decls:
                notes.append(f"{prop} removed from body")
                decls = new
        return m.group(1) + decls + "}"

    css = re.sub(r"((?:^|(?<=\}))\s*(?:html\s*,\s*)?body\s*\{)([^}]*)\}", strip_body, css,
                 flags=re.M)
    body = re.search(r"(?:^|\})\s*(?:html\s*,\s*)?body\s*\{[^}]*?font-family\s*:\s*([^;}]+)", css,
                     flags=re.M)
    if body:
        family = re.sub(r"\s+", " ", body.group(1).strip())

        def drop_repeat(m: re.Match) -> str:
            selectors = [s.strip() for s in m.group(1).split(",")]
            decls = [d.strip() for d in m.group(2).split(";") if d.strip()]
            repeats = (len(decls) == 1 and decls[0].startswith("font-family")
                       and re.sub(r"\s+", " ", decls[0].split(":", 1)[1].strip()) == family)
            if repeats and "p" in selectors and "body" not in selectors:
                notes.append("font-family repeated on text elements dropped")
                return ""
            return m.group(0)

        css = re.sub(r"(?<=\})\s*([^{}@/]+)\{([^{}]*)\}", drop_repeat, css)
    return css, notes


XHTML_NS = "http://www.w3.org/1999/xhtml"
NCX_NS = "http://www.daisy.org/z3986/2005/ncx/"


def flatten_navigation(files: dict[str, bytes], base: str, max_depth: int = 2) -> str:
    """Cut the table of contents down to `max_depth` levels.

    Kindle supports two levels of nesting (guideline 5.2), and a deeper one is
    a documented cause of conversion failure: 18.2.1 E24011 says to "reduce the
    number of levels created using unordered list or ordered list tags up to 2
    levels". The book's nav is parts > chapters > sections -- three deep and
    3,450 entries. Only the Kindle edition is trimmed; the EPUB for Apple and
    Kobo keeps section-level navigation.
    """
    ET.register_namespace("", XHTML_NS)
    ET.register_namespace("epub", "http://www.idpf.org/2007/ops")
    ET.register_namespace("", NCX_NS)

    def prune(parent: ET.Element, tag: str, depth: int) -> None:
        for child in list(parent):
            if child.tag == tag:
                if depth >= max_depth:
                    parent.remove(child)
                    continue
                prune(child, tag, depth + 1)
            else:
                prune(child, tag, depth)

    note = []
    nav_name = f"{base}/nav.xhtml" if base else "nav.xhtml"
    if nav_name in files:
        ET.register_namespace("", XHTML_NS)
        ET.register_namespace("epub", "http://www.idpf.org/2007/ops")
        root = ET.fromstring(files[nav_name].decode("utf-8"))
        before = sum(1 for _ in root.iter(f"{{{XHTML_NS}}}li"))
        prune(root, f"{{{XHTML_NS}}}ol", 0)
        after = sum(1 for _ in root.iter(f"{{{XHTML_NS}}}li"))
        files[nav_name] = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            + ET.tostring(root, encoding="unicode")).encode("utf-8")
        note.append(f"nav {before} -> {after} entries")

    ncx_name = f"{base}/toc.ncx" if base else "toc.ncx"
    if ncx_name in files:
        ET.register_namespace("", NCX_NS)
        root = ET.fromstring(files[ncx_name].decode("utf-8"))
        prune(root, f"{{{NCX_NS}}}navPoint", 0)
        files[ncx_name] = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            + ET.tostring(root, encoding="unicode")).encode("utf-8")

    return f"flattened navigation to {max_depth} levels ({', '.join(note)})"


def simplify_cover(files: dict[str, bytes], base: str) -> str:
    """Replace Pandoc's SVG-wrapped cover with a plain <img>.

    Guideline 18.2.3 lists an "SVG namespace prefix" as unsupported and tells
    you to remove it; Pandoc's cover uses xlink:href inside an <svg> wrapper.
    A plain <img> carries the cover just as well and avoids the whole issue.
    """
    name = f"{base}/text/cover.xhtml" if base else "text/cover.xhtml"
    if name not in files:
        return ""
    text = files[name].decode("utf-8")
    m = re.search(r'xlink:href="([^"]+)"', text)
    if not m:
        return ""
    src = m.group(1)
    body = (f'<body id="cover"><div id="cover-image">'
            f'<img src="{src}" alt="Cover" style="max-width:100%;height:auto" />'
            f"</div></body>")
    text = re.sub(r"<body.*?</body>", body, text, flags=re.S)
    files[name] = text.encode("utf-8")
    # the page no longer uses SVG, so the manifest property must go
    opf_name = next(n for n in files if n.endswith(".opf"))
    opf = files[opf_name].decode("utf-8")
    files[opf_name] = re.sub(
        r'(<item[^>]*href="text/cover\.xhtml"[^>]*?)\s*properties="svg"',
        r"\1", opf).encode("utf-8")
    return "replaced the SVG cover wrapper with a plain <img>"


def sync_properties(opf: str, files: dict[str, bytes], base: str) -> str:
    """Recompute manifest properties: mathml and svg are gone, so drop them.

    fix_epub only ever adds a property; here they must also be removed, because
    a declared-but-unused property is itself an error (OPF-015).
    """
    def fix(m: re.Match) -> str:
        item = m.group(0)
        href_m = re.search(r'href="([^"]*)"', item)
        props_m = re.search(r'properties="([^"]*)"', item)
        if not href_m or not props_m:
            return item
        href = href_m.group(1)
        if not href.endswith((".xhtml", ".html")):
            return item
        data = files.get(f"{base}/{href}" if base else href, b"")
        text = data.decode("utf-8", "replace")
        props = [p for p in props_m.group(1).split()
                 if p not in ("mathml", "svg")]
        for prop, marker in (("mathml", "<math"), ("svg", "<svg")):
            if marker in text and prop not in props:
                props.append(prop)
        if not props:
            # An empty properties="" is not a valid manifest attribute; the
            # attribute has to go, not just its value.
            return re.sub(r'\s+properties="[^"]*"', "", item)
        return item[:props_m.start(1)] + " ".join(props) + item[props_m.end(1):]

    return ITEM_RE.sub(fix, opf)


def default_output(src: str) -> str:
    """An ASCII output name beside the source.

    The book's own file name is Persian, and guideline 21.1.12 says "do not
    include special characters ... in the file path or file name" -- KDP's
    uploader is the first thing that sees it. The reader never sees this name
    (KDP shows the metadata title), so ASCII costs nothing here.
    """
    stem = os.path.splitext(os.path.basename(src))[0]
    ascii_stem = re.sub(r"-{2,}", "-", re.sub(r"[^A-Za-z0-9]+", "-", stem)).strip("-")
    if len(re.sub(r"[^A-Za-z0-9]", "", ascii_stem)) < 3:
        ascii_stem = "book"
    return os.path.join(os.path.dirname(src), f"{ascii_stem}-kindle.epub")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("epub", nargs="?", help="source EPUB (default: the one in _book/)")
    ap.add_argument("-o", "--output", help="output path (default: <source>-kindle.epub)")
    ap.add_argument("--limit", type=int, default=0,
                    help="only rasterise the first N distinct snippets (testing)")
    ap.add_argument("--reuse-latex", action="store_true",
                    help="skip the LaTeX pass if the workdir already has snippets.pdf")
    ap.add_argument("--workdir", help="keep LaTeX intermediates here")
    args = ap.parse_args()

    src = args.epub
    if not src:
        found = [p for p in glob.glob(os.path.join(ROOT, "_book", "*.epub"))
                 if "-kindle" not in os.path.basename(p)]
        if not found:
            report("build_kindle_epub: no source .epub in _book/")
            return 1
        src = found[0]
    out = args.output or default_output(src)

    # Outside _book/: that directory is published to GitHub Pages as-is, and the
    # LaTeX intermediates (a multi-thousand-page PDF) have no business there.
    workdir = args.workdir or os.path.join(ROOT, ".kindle-build")
    os.makedirs(workdir, exist_ok=True)

    with zipfile.ZipFile(src) as zf:
        infos = zf.infolist()
        files = {i.filename: zf.read(i) for i in infos}
    opf_name = next(n for n in files if n.endswith(".opf"))
    base = os.path.dirname(opf_name).replace("\\", "/")
    docs = [n for n in files if n.endswith((".xhtml", ".html"))]

    # --- 1. plan the math -------------------------------------------------
    wanted: dict[tuple[bool, str], None] = {}
    for name in docs:
        if name.endswith("nav.xhtml"):
            continue
        text = files[name].decode("utf-8")
        for m in MATH_RE.finditer(text):
            frag = m.group(0)
            display = 'display="block"' in frag[:frag.find(">")]
            if not display and mathml_to_unicode(frag) is not None:
                continue
            tex_m = ANNOTATION_RE.search(frag)
            wanted[(display, clean_tex(tex_m.group(1)) if tex_m else "")] = None
    snippets = list(wanted)
    if args.limit:
        snippets = snippets[:args.limit]
    report(f"build_kindle_epub: {len(snippets)} distinct expressions to rasterise")

    # --- 2. render them ---------------------------------------------------
    images: dict[tuple[bool, str], tuple[str, float, float]] = {}
    if snippets:
        tex_path = os.path.join(workdir, "snippets.tex")
        pdf_path = os.path.join(workdir, "snippets.pdf")
        if args.reuse_latex and os.path.exists(pdf_path):
            report("build_kindle_epub: reusing the snippets.pdf already in the workdir")
        else:
            write_snippet_tex(tex_path, snippets)
            report("build_kindle_epub: running LuaLaTeX ...")
            run_lualatex(tex_path, workdir, len(snippets))
        report("build_kindle_epub: cropping pages ...")
        for idx, png, height_em, depth_em in render_snippets(
                os.path.join(workdir, "snippets.pdf"),
                os.path.join(workdir, "snippets-dims.txt"), len(snippets)):
            name = f"eq{idx:05d}.png"
            files[f"{base}/media/{name}"] = png
            images[snippets[idx]] = (name, height_em, depth_em)

    # --- 3. figures -------------------------------------------------------
    sources = figure_sources()
    renamed: dict[str, str] = {}
    svg_names = [n for n in files if n.endswith(".svg")]
    report(f"build_kindle_epub: rasterising {len(svg_names)} figures ...")
    for name in svg_names:
        png_name = re.sub(r"\.svg$", ".png", name)
        files[png_name] = rasterize_figure(files.pop(name), sources)
        renamed[os.path.basename(name)] = os.path.basename(png_name)

    # --- 4. rewrite the documents ----------------------------------------
    totals = {"unicode": 0, "image": 0, "flattened": 0}
    alts = 0
    code_blocks = 0
    for name in docs:
        text = files[name].decode("utf-8")
        text, stats = rewrite_math(text, wanted, images,
                                   nav=name.endswith("nav.xhtml"))
        text, filled = rewrite_figures(text, renamed)
        text, listings = rewrite_code(text)
        code_blocks += listings
        files[name] = text.encode("utf-8")
        for k in totals:
            totals[k] += stats[k]
        alts += filled

    # --- 5. Kindle-only navigation and cover ------------------------------
    # Both are documented causes of "Kindle conversion internal error"
    # (guidelines 18.2.1 E24011 and 18.2.3); neither applies to the EPUB that
    # goes to Apple, so they are fixed here rather than in fix_epub.py.
    for note in (flatten_navigation(files, base), simplify_cover(files, base)):
        if note:
            report(f"build_kindle_epub: {note}")

    # --- 6. stylesheet ----------------------------------------------------
    for name in [n for n in files if n.endswith(".css")]:
        css, notes = body_defaults(files[name].decode("utf-8"))
        files[name] = (css.rstrip() + "\n" + EQUATION_CSS + CODE_CSS).encode("utf-8")
        if notes:
            report(f"build_kindle_epub: {os.path.basename(name)}: body text left to "
                   f"the reader's defaults ({', '.join(notes)})")

    # --- 7. manifest ------------------------------------------------------
    opf = files[opf_name].decode("utf-8")
    for old, new in renamed.items():
        opf = opf.replace(f'href="media/{old}"', f'href="media/{new}"')
    opf = re.sub(r'(<item\b[^>]*href="media/[^"]*\.png"[^>]*media-type=")image/svg\+xml(")',
                 r"\1image/png\2", opf)
    new_items = "".join(
        f'\n    <item id="eq{i:05d}" href="media/eq{i:05d}.png" media-type="image/png" />'
        for i in range(len(images)))
    opf = opf.replace("</manifest>", f"{new_items}\n  </manifest>")
    opf = sync_properties(opf, files, base)
    files[opf_name] = opf.encode("utf-8")

    # --- 8. write it out --------------------------------------------------
    if os.path.exists(out):
        os.remove(out)
    with open(out, "wb"):
        pass
    repack(out, infos, files)

    size = os.path.getsize(out) / 1024 / 1024
    report(f"build_kindle_epub: math -> {totals['unicode']} Unicode, "
           f"{totals['image']} images, {totals['flattened']} flattened")
    report(f"build_kindle_epub: {alts} figure alt texts filled from captions")
    report(f"build_kindle_epub: {code_blocks} code listings rewritten as wrapping lines")
    report(f"build_kindle_epub: wrote {os.path.basename(out)} ({size:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
