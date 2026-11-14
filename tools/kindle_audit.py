#!/usr/bin/env python3
"""Static audit of a Kindle EPUB against the Amazon Kindle Publishing Guidelines.

Kindle Previewer answers "does it convert, and with Enhanced Typesetting?".
This script answers the other half: the rules of the guidelines that the
converter does NOT report but that KDP rejects on, or that make an upload die
with the catch-all "internal error". Every check names the guideline section it
enforces, as numbered in version 2026.3 (October 2026) of
https://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf

    python tools/kindle_audit.py                    # _book/*-kindle.epub
    python tools/kindle_audit.py path/to/book.epub
    python tools/kindle_audit.py --strict           # warnings fail the run too

FAIL  = a rule the guidelines state as a requirement or list as a known cause of
        conversion failure;
WARN  = a recommendation ("Amazon recommends ...") worth a human look.
Exit status is 1 when anything FAILs.
"""

from __future__ import annotations

import argparse
import glob
import io
import os
import posixpath
import re
import struct
import sys
import zipfile
from urllib.parse import unquote
from xml.etree import ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NS = {
    "c": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "ncx": "http://www.daisy.org/z3986/2005/ncx/",
    "x": "http://www.w3.org/1999/xhtml",
    "epub": "http://www.idpf.org/2007/ops",
}
XHTML = "{http://www.w3.org/1999/xhtml}"

# 17.5 (list updated in 2026.3: Hebrew, Latin and Persian were added)
ET_LANGUAGES = {
    "af", "gsw", "ar", "eu", "nb", "br", "ca", "zh", "kw", "co", "da", "nl", "frs",
    "en", "fi", "fr", "fy", "gl", "de", "he", "is", "ga", "it", "ja", "la", "lb",
    "gv", "frr", "no", "nn", "fa", "pt", "oc", "rm", "ru", "sco", "gd", "es", "sw",
    "sv", "cy", "ml", "ta", "hi", "gu", "mr",
}
# A phone-sized Kindle page holds about this many monospaced characters; a
# longer <pre> line runs off the screen (see rewrite_code in build_kindle_epub.py).
PRE_MAX_CHARS = 40
MATHML_UNSUPPORTED =("maction", "mglyph", "mlongdiv", "msgroup", "mstack")   # 11.6


class Audit:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str, str]] = []

    def add(self, level: str, section: str, what: str, detail: str = "") -> None:
        self.rows.append((level, section, what, detail))

    def check(self, ok: bool, section: str, what: str, detail: str = "",
              level: str = "FAIL") -> bool:
        self.add("ok" if ok else level, section, what, "" if ok else detail)
        return ok

    def count(self, level: str) -> int:
        return sum(1 for r in self.rows if r[0] == level)


def image_size(data: bytes) -> tuple[int, int] | None:
    """Pixel size of a PNG/JPEG/GIF without decoding it."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", data[6:10])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB,
                          0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


def some(items: list[str], n: int = 4) -> str:
    items = list(dict.fromkeys(items))
    tail = f" ... (+{len(items) - n} more)" if len(items) > n else ""
    return "; ".join(items[:n]) + tail


def nav_depth(ol: ET.Element) -> int:
    deepest = 0
    for li in ol.findall(f"{XHTML}li"):
        for sub in li.findall(f"{XHTML}ol"):
            deepest = max(deepest, nav_depth(sub))
    return 1 + deepest


def ncx_depth(node: ET.Element) -> int:
    kids = node.findall("ncx:navPoint", NS)
    return (1 + max(ncx_depth(k) for k in kids)) if kids else 0


def audit(path: str) -> Audit:
    a = Audit()
    zf = zipfile.ZipFile(path)
    names = zf.namelist()
    infos = {i.filename: i for i in zf.infolist()}

    # ---- container ------------------------------------------------------
    a.check(re.fullmatch(r"[A-Za-z0-9._ -]+", os.path.basename(path)) is not None,
            "21.1.12", "file name has no special characters", os.path.basename(path))
    a.check(names and names[0] == "mimetype"
            and infos["mimetype"].compress_type == zipfile.ZIP_STORED,
            "EPUB OCF", "mimetype is the first entry and stored uncompressed")
    bad_names = [n for n in names if not re.fullmatch(r"[A-Za-z0-9._/+-]+", n)]
    a.check(not bad_names, "6.5 / 6.7", "internal file names are plain ASCII", some(bad_names))
    size_mb = os.path.getsize(path) / 1024 / 1024
    a.check(size_mb <= 650, "KDP upload", f"EPUB is {size_mb:.1f} MB (KDP limit 650 MB)")

    container = ET.fromstring(zf.read("META-INF/container.xml"))
    rootfiles = container.findall(".//c:rootfile", NS)
    a.check(len(rootfiles) == 1, "18.2.1 E21027", "exactly one OPF package file",
            f"{len(rootfiles)} rootfiles")
    opf_path = rootfiles[0].get("full-path")
    opf_dir = posixpath.dirname(opf_path)
    opf = ET.fromstring(zf.read(opf_path))

    def full(href: str) -> str:
        return posixpath.normpath(posixpath.join(opf_dir, unquote(href)))

    # ---- metadata (11.1, 18.2) --------------------------------------------
    meta = opf.find("opf:metadata", NS)
    titles = meta.findall("dc:title", NS)
    langs = [e.text.strip() for e in meta.findall("dc:language", NS) if e.text]
    a.check(bool(titles), "11.1", "<dc:title> present")
    if len(titles) > 1:
        mains = [m for m in meta.findall("opf:meta", NS)
                 if m.get("property") == "title-type" and (m.text or "").strip() == "main"]
        a.check(len(mains) == 1, "18.2.1 E20006",
                "several <dc:title>: exactly one refined as title-type=main",
                f"{len(titles)} titles, {len(mains)} marked main")
    a.check(len(langs) == 1, "11.1 / 18.2.2", "exactly one <dc:language>", str(langs))
    lang = (langs[0] if langs else "").split("-")[0].lower()
    a.check(lang in ET_LANGUAGES, "17.5",
            f"language '{lang}' is in the Enhanced Typesetting list", level="WARN",
            detail="Enhanced Typesetting may be refused for this language")
    a.check(bool(meta.findall("dc:identifier", NS)) and opf.get("unique-identifier"),
            "EPUB OPF", "unique identifier declared")
    a.check(bool(meta.findall("dc:creator", NS)), "11.1", "<dc:creator> present", level="WARN")

    manifest = {i.get("id"): i for i in opf.find("opf:manifest", NS)}
    spine = opf.find("opf:spine", NS)
    by_href = {full(i.get("href")): i for i in manifest.values()}
    missing = [h for h in by_href if h not in infos]
    a.check(not missing, "6.5", "every manifest item exists in the archive (exact case)",
            some(missing))

    rtl = lang in ("fa", "ar", "he", "ur", "yi")
    if rtl:
        ppd = spine.get("page-progression-direction")
        pwm = [m.get("content") for m in meta.findall("opf:meta", NS)
               if m.get("name") == "primary-writing-mode"]
        a.check(ppd == "rtl" or "horizontal-rl" in pwm, "11.1",
                "right-to-left page progression declared (spine or primary-writing-mode)",
                f"spine page-progression-direction={ppd!r}, primary-writing-mode={pwm}")

    # ---- cover (4.2, 18.2.1 "Cover not built") ----------------------------
    cover_items = [i for i in manifest.values() if "cover-image" in (i.get("properties") or "").split()]
    cover_meta = [m.get("content") for m in meta.findall("opf:meta", NS) if m.get("name") == "cover"]
    a.check(len(cover_items) == 1, "4.2", "one manifest item with properties=\"cover-image\"",
            f"{len(cover_items)} found")
    if cover_meta:
        a.check(cover_meta[0] in manifest and (not cover_items or cover_items[0].get("id") == cover_meta[0]),
                "18.2.1", "<meta name=\"cover\"> points at the cover-image item's id",
                f"meta content={cover_meta[0]!r}")
    if cover_items:
        item = cover_items[0]
        data = zf.read(full(item.get("href")))
        wh = image_size(data)
        a.check(item.get("media-type") in ("image/jpeg", "image/png", "image/gif"),
                "4.1", "cover is JPEG/PNG/GIF (not SVG/TIFF)", item.get("media-type"))
        if wh:
            a.check(max(wh) >= 1200, "11.4 (cover)",
                    f"cover is {wh[0]}x{wh[1]} px (at least 1200 px on the long side)")
            a.check(max(wh) >= 2500, "4.1", "cover long side >= 2500 px (ideal 2560x1600)",
                    f"{wh[0]}x{wh[1]}", level="WARN")
            a.check(max(wh) <= 10000, "4.1", "cover is at most 10,000 px on each side")
        a.check(len(data) <= 50 * 1024 * 1024, "4.1", "cover file is under 50 MB")

    # ---- navigation (5) ---------------------------------------------------
    nav_items = [i for i in manifest.values() if "nav" in (i.get("properties") or "").split()]
    a.check(len(nav_items) == 1, "5.2.1", "one EPUB3 nav document (properties=\"nav\")")
    ncx_id = spine.get("toc")
    ncx_item = manifest.get(ncx_id) if ncx_id else None
    a.check(ncx_item is not None and ncx_item.get("media-type") == "application/x-dtbncx+xml",
            "5.2.2", "NCX declared in the manifest and referenced by <spine toc=...>")
    spine_hrefs = [full(manifest[r.get("idref")].get("href")) for r in spine
                   if r.get("idref") in manifest]

    docs: dict[str, str] = {}
    for href, item in by_href.items():
        if item.get("media-type") == "application/xhtml+xml" and href in infos:
            docs[href] = zf.read(href).decode("utf-8", "replace")
    ids: dict[str, set[str]] = {h: set(re.findall(r'\bid="([^"]+)"', t)) for h, t in docs.items()}
    body_ids = {h: set(re.findall(r'<body\b[^>]*\bid="([^"]+)"', t)) for h, t in docs.items()}
    hidden_ids = {h: set(re.findall(
        r'<[^>]*\bid="([^"]+)"[^>]*style="[^"]*(?:display\s*:\s*none|visibility\s*:\s*hidden)',
        t)) | set(re.findall(
            r'<[^>]*style="[^"]*(?:display\s*:\s*none|visibility\s*:\s*hidden)[^"]*"[^>]*\bid="([^"]+)"',
            t)) for h, t in docs.items()}

    def resolve(base: str, href: str) -> tuple[str, str]:
        target, _, frag = href.partition("#")
        doc = posixpath.normpath(posixpath.join(posixpath.dirname(base), unquote(target))) if target else base
        return doc, unquote(frag)

    toc_targets: list[tuple[str, str, str]] = []      # (where, doc, fragment)
    if nav_items:
        nav_href = full(nav_items[0].get("href"))
        nav = ET.fromstring(zf.read(nav_href))
        toc_nav = next((n for n in nav.iter(f"{XHTML}nav")
                        if n.get(f"{{{NS['epub']}}}type") == "toc"), None)
        a.check(toc_nav is not None, "5.2.1", "<nav epub:type=\"toc\"> present")
        if toc_nav is not None:
            ol = toc_nav.find(f"{XHTML}ol")
            depth = nav_depth(ol) if ol is not None else 0
            a.check(1 <= depth <= 2, "5.2 / 18.2.1 E24011",
                    f"toc nav nests {depth} level(s) (Kindle supports two)")
            for link in toc_nav.iter(f"{XHTML}a"):
                if link.get("href"):
                    toc_targets.append(("nav", *resolve(nav_href, link.get("href"))))
        landmarks = next((n for n in nav.iter(f"{XHTML}nav")
                          if n.get(f"{{{NS['epub']}}}type") == "landmarks"), None)
        guide = opf.find("opf:guide", NS)
        a.check(landmarks is not None or guide is not None, "5.3",
                "landmarks nav or <guide> defines cover/toc", level="WARN")
        nav_text = docs.get(nav_href, "")
        a.check(not re.search(r"<body\b[^>]*(display\s*:\s*none|hidden)", nav_text),
                "18.2.3", "ToC document body is not hidden")
    if ncx_item is not None:
        ncx_href = full(ncx_item.get("href"))
        ncx = ET.fromstring(zf.read(ncx_href))
        navmap = ncx.find("ncx:navMap", NS)
        depth = ncx_depth(navmap)
        a.check(1 <= depth <= 2, "5.2 / 18.2.1 E24011",
                f"NCX nests {depth} level(s) (Kindle supports two)")
        order = []
        for content in navmap.iter(f"{{{NS['ncx']}}}content"):
            doc, frag = resolve(ncx_href, content.get("src"))
            toc_targets.append(("ncx", doc, frag))
            order.append(doc)
        pos = [spine_hrefs.index(d) for d in order if d in spine_hrefs]
        a.check(pos == sorted(pos), "5.2.2", "NCX entries follow the reading order of the book")

    unresolved = [f"{w}:{posixpath.basename(d)}#{f}" for w, d, f in toc_targets
                  if d not in docs or (f and f not in ids[d])]
    a.check(not unresolved, "18.2.1 E24010", "every ToC link resolves", some(unresolved))
    on_body = [f"{posixpath.basename(d)}#{f}" for _, d, f in toc_targets
               if d in docs and f and f in body_ids[d]]
    a.check(not on_body, "18.2.1 E24010", "no ToC link targets an id on <body>", some(on_body))
    on_hidden = [f"{posixpath.basename(d)}#{f}" for _, d, f in toc_targets
                 if d in docs and f and f in hidden_ids[d]]
    a.check(not on_hidden, "18.2.1 E24010", "no ToC link targets a hidden element", some(on_hidden))

    # ---- fonts (11.3.8, 18.2.2) -------------------------------------------
    fonts = [h for h, i in by_href.items()
             if h.lower().endswith((".ttf", ".otf", ".woff", ".woff2", ".pfb", ".eot"))]
    empty = [h for h in fonts if h in infos and infos[h].file_size == 0]
    a.check(not empty, "18.2.2", "no 0-byte font file", some(empty))
    wrong = [h for h in fonts if not h.lower().endswith((".ttf", ".otf"))]
    a.check(not wrong, "11.3.8", "embedded fonts are OpenType/TrueType (OTF/TTF)", some(wrong))

    # ---- images (11.4, 18.2.2, 18.2.3) --------------------------------------
    images = {h: i for h, i in by_href.items() if (i.get("media-type") or "").startswith("image/")}
    kinds = sorted({i.get("media-type") for i in images.values()})
    unsupported = [h for h, i in images.items()
                   if i.get("media-type") not in ("image/jpeg", "image/png", "image/gif", "image/svg+xml")]
    a.check(not unsupported, "11.4.1", f"image formats are supported ({', '.join(kinds)})",
            some(unsupported))
    svgs = [h for h, i in images.items() if i.get("media-type") == "image/svg+xml"]
    a.check(len(svgs) <= 25, "11.4.11",
            f"{len(svgs)} SVG image(s) (more than 25 blocks Enhanced Typesetting)")
    tiny, huge, transparent = [], [], 0
    for h in images:
        if h not in infos or h in svgs:
            continue
        data = zf.read(h)
        wh = image_size(data)
        if wh and min(wh) <= 1:
            tiny.append(f"{posixpath.basename(h)} {wh[0]}x{wh[1]}")
        if len(data) > 5 * 1024 * 1024 or (wh and wh[0] * wh[1] > 25_000_000):
            huge.append(f"{posixpath.basename(h)} {len(data) // 1024} kB {wh}")
    a.check(not tiny, "18.2.2", "no image is 1 px wide or high", some(tiny))
    a.check(not huge, "11.4.2", "no image above 5 MB / 25 megapixels", some(huge), level="WARN")

    # ---- XHTML content ------------------------------------------------------
    all_text_len = 0
    problems: dict[str, list[str]] = {}

    def hit(key: str, where: str) -> None:
        problems.setdefault(key, []).append(posixpath.basename(where))

    img_total = img_noalt = 0
    for href, text in docs.items():
        all_text_len += len(text)
        base = posixpath.basename(href)
        if re.search(r"<script\b", text):
            hit("script", href)
        if re.search(r"""(?:src|href)\s*=\s*["']data:|url\(\s*["']?data:""", text):
            hit("base64", href)
        if re.search(r"<math\b", text):
            hit("mathml", href)
            if re.search(r"<(?:%s)\b" % "|".join(MATHML_UNSUPPORTED), text):
                hit("mathml-unsupported", href)
        if re.search(r"<svg\b", text) or re.search(r"<svg:\w+", text):
            hit("inline-svg", href)
        if re.search(r"<\w+:svg\b|<svg:\w+|\bxlink:href=", text):
            hit("svg-prefix", href)
        if re.search(r"<table\b(?:(?!</table>).)*?<caption\b", text, re.S):
            hit("table-caption", href)
        if re.search(r"<table\b(?:(?!</table>).)*?<table\b", text, re.S):
            hit("nested-table", href)
        if re.search(r"<(?:video|audio|iframe|form|embed|object|canvas)\b", text):
            hit("media", href)
        if re.search(r"<p\b[^>]*>(?:(?!</p>).)*?<p\b", text, re.S):
            hit("nested-p", href)
        if re.search(r"<font\b", text):
            hit("font-tag", href)
        for pre in re.findall(r"<pre\b[^>]*>(.*?)</pre>", text, re.S):
            widest = max((len(line) for line in re.sub(r"<[^>]+>", "", pre).split("\n")), default=0)
            if widest > PRE_MAX_CHARS:
                hit("pre-long", f"{href} ({widest} chars)")
        for tag in re.findall(r"<img\b[^>]*>", text):
            img_total += 1
            if not re.search(r'\balt="', tag) and 'role="presentation"' not in tag:
                img_noalt += 1
                hit("img-noalt", href)
            src = re.search(r'\bsrc="([^"]+)"', tag)
            if src and not src.group(1).startswith(("http:", "https:", "data:")):
                target, _ = resolve(href, src.group(1))
                if target not in infos:
                    hit("img-missing", href)
        m = re.search(r"<html\b[^>]*>", text)
        if m and not re.search(r'\b(?:xml:)?lang="', m.group(0)):
            hit("no-lang", href)
        for link in re.findall(r'<a\b[^>]*\bhref="([^"]+)"', text):
            if re.match(r"[a-z][a-z0-9+.-]*:", link, re.I):
                continue
            doc, frag = resolve(href, link)
            if doc not in infos or (doc in docs and frag and frag not in ids[doc]):
                hit("broken-link", href + " -> " + link)

    def none(key: str, section: str, what: str, level: str = "FAIL") -> None:
        found = problems.get(key, [])
        a.check(not found, section, what, f"{len(found)} occurrence(s): {some(found)}", level)

    none("script", "6.3", "no scripting")
    none("base64", "18.2.3", "no Base64-embedded images")
    none("svg-prefix", "18.2.3", "no SVG namespace prefix (svg:, xlink:)")
    none("table-caption", "18.2.2", "no <caption> inside <table> (\"not supported for rasterization\")")
    none("nested-table", "11.5.2", "no nested tables (unsupported in Enhanced Typesetting)")
    none("media", "18.2.3 / 15", "no audio/video/forms/embedded objects")
    none("nested-p", "6.4", "no nested <p>")
    none("pre-long", "18.1", f"no <pre> line longer than {PRE_MAX_CHARS} characters "
         "(Kindle cannot wrap <pre>: white-space supports only normal/nowrap, so it is cut off)")
    none("img-missing", "6.5", "every <img> source exists (exact case)")
    none("broken-link", "7.1", "every internal hyperlink resolves")
    a.check(img_noalt == 0, "11.4.1 / 8", f"all {img_total} <img> carry alt text",
            f"{img_noalt} without alt: {some(problems.get('img-noalt', []))}")
    none("no-lang", "8", "every document declares its language", level="WARN")
    none("font-tag", "11.3.2", "no <font> tags", level="WARN")
    none("inline-svg", "11.4.11", "no inline <svg> (use <img>)", level="WARN")
    if problems.get("mathml"):
        n = len(problems["mathml"])
        a.add("WARN", "11.6", f"MathML present in {n} document(s)",
              "supported only with Enhanced Typesetting; a large book's 39,843 expressions "
              "did not convert at all -- build the Kindle edition without MathML")
        none("mathml-unsupported", "11.6", "no unsupported MathML tags")
    else:
        a.add("ok", "11.6", "no MathML left for the converter", "")
    big = [f"{posixpath.basename(h)} {len(t) // 1024} kB" for h, t in docs.items() if len(t) > 30 * 1024 * 1024]
    a.check(not big, "6.1", "no single HTML file above 30 MB", some(big))

    # ---- CSS (11.3, 18.2.2, 18.2.3) -----------------------------------------
    css = ""
    for href, item in by_href.items():
        if item.get("media-type") == "text/css" and href in infos:
            css += zf.read(href).decode("utf-8", "replace") + "\n"
    inline = "\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", "\n".join(docs.values()), re.S))
    style_attrs = "\n".join(re.findall(r'\bstyle="([^"]*)"', "\n".join(docs.values())))
    styles = re.sub(r"/\*.*?\*/", "", css + "\n" + inline, flags=re.S)
    everything = styles + "\n" + style_attrs

    def css_none(pattern: str, section: str, what: str, level: str = "FAIL") -> None:
        found = re.findall(pattern, everything, re.I)
        a.check(not found, section, what, f"{len(found)} occurrence(s), e.g. {found[0]!r}" if found else "", level)

    css_none(r"\b(?:height|width)\s*:\s*inherit", "18.2.2 / 18.2.3", "no height/width: inherit")
    css_none(r"text-decoration[a-z-]*\s*:[^;}]*line-through", "18.2.3", "no text-decoration: line-through")
    css_none(r"linear-gradient", "18.2.3", "no linear-gradient backgrounds")
    css_none(r"visibility\s*:\s*collapse", "18.2.3", "no visibility: collapse")
    css_none(r"caption-side\s*:\s*bottom", "18.2.3", "no caption-side: bottom", level="WARN")
    css_none(r"position\s*:\s*(?:absolute|fixed)", "11.2", "no CSS positioning for layout", level="WARN")
    # 6.2: a negative value is a problem when nothing compensates for it (content
    # is then cut off at the edge); a negative line-height is never supported.
    # Pandoc's own boilerplate (hanging bibliography indent, wrapped code lines)
    # pairs every negative text-indent with a margin/padding and is fine.
    neg = r"(?<![\w.#(-])-\d*\.?\d+(?:em|px|pt|%|rem)?"
    css_none(r"line-height\s*:\s*" + neg, "6.2", "no negative line-height")
    uncompensated = []
    blocks = re.findall(r"\{([^{}]*)\}", styles) + style_attrs.split("\n")
    for block in blocks:
        if re.search(r"text-indent\s*:\s*" + neg, block) and not re.search(
                r"(?:padding|margin)(?:-left|-right|-inline-start)?\s*:\s*[^;}]*[1-9]", block):
            uncompensated.append(re.sub(r"\s+", " ", block.strip())[:70])
        m = re.search(r"margin-(?:left|right)\s*:\s*" + neg, block)
        if m:
            uncompensated.append(m.group(0))
    a.check(not uncompensated, "6.2", "no uncompensated negative indent / side margin",
            some(uncompensated), level="WARN")
    hidden_chars = 0
    for h, text in docs.items():
        for m in re.finditer(r'<(\w+)\b[^>]*style="[^"]*display\s*:\s*none[^"]*"[^>]*>(.*?)</\1>', text, re.S):
            hidden_chars += len(re.sub(r"<[^>]+>", "", m.group(2)))
    a.check(hidden_chars <= 10000, "18.2.1 E3013",
            f"{hidden_chars} characters hidden with display:none (limit 10,000)")
    body_rules = " ".join(re.findall(r"(?:^|[},])\s*(?:html\s*,\s*)?body\s*\{([^}]*)\}", styles))
    for prop, section in (("font-size", "11.3.2"), ("line-height", "11.3.2"), ("color", "11.3.2"),
                          ("background-color", "11.3.2"), ("background", "11.3.2")):
        m = re.search(r"(?<![\w-])%s\s*:\s*([^;}]+)" % prop, body_rules)
        a.check(m is None, section, f"body text does not force {prop}",
                m.group(0).strip() if m else "", level="WARN")
    m = re.search(r"(?<![\w-])margin(?:-left|-right)?\s*:\s*([^;}]+)", body_rules)
    forced = bool(m and re.search(r"[1-9]", m.group(1)))
    a.check(not forced, "11.3.5", "body text has no forced left/right margin",
            m.group(0).strip() if m else "", level="WARN")
    return a


def print_report(path: str, a: Audit, verbose: bool) -> None:
    print(f"\n=== {os.path.basename(path)} ===")
    for level, section, what, detail in a.rows:
        if level == "ok" and not verbose:
            continue
        line = f"  {level:4s} [{section}] {what}"
        print(line + (f"\n         {detail}" if detail else ""))
    print(f"  -> {a.count('ok')} passed, {a.count('WARN')} warning(s), {a.count('FAIL')} failure(s)")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("epubs", nargs="*")
    ap.add_argument("--strict", action="store_true", help="warnings also fail the run")
    ap.add_argument("-q", "--quiet", action="store_true", help="only show warnings and failures")
    args = ap.parse_args()
    epubs = args.epubs or sorted(glob.glob(os.path.join(ROOT, "_book", "*-kindle.epub")))
    if not epubs:
        print("kindle_audit: no *-kindle.epub in _book/ (run tools/build_kindle_epub.py)")
        return 1
    bad = False
    for path in epubs:
        a = audit(path)
        print_report(path, a, verbose=not args.quiet)
        bad |= a.count("FAIL") > 0 or (args.strict and a.count("WARN") > 0)
    print("\nkindle_audit:", "problems found (above)" if bad else "no guideline violation found")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
