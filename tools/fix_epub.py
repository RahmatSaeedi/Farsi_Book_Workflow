#!/usr/bin/env python3
"""Repair the two EPUB3 conformance defects Pandoc/texmath leave in the book.

Run as a Quarto post-render step (wired in _quarto.yml), so every `quarto render`
produces an EPUB that passes epubcheck / Apple Books ingestion. Both defects come
out of Pandoc's writer, not our sources, so they can only be fixed on the built
container -- there is no template or Lua-filter hook for either.

  1. [OPF-014] "The property 'mathml' should be declared in the OPF file."
     Section titles contain math, so EPUB/nav.xhtml carries <math> elements, but
     Pandoc computes the `mathml` manifest property only for content documents --
     the nav item gets a bare properties="nav". EPUB3 requires every property a
     document actually uses to be declared. Fix: add the missing `mathml` (and
     `svg`) property to any XHTML manifest item whose file really uses it.
     Only ever ADDS a property: a declared-but-unused property is itself an error
     (OPF-015), and Pandoc's existing declarations are all correct.

  2. [RSC-005] attribute "stretchy"/"minsize"/"maxsize" not allowed here.
     `\\big/` and `\\Big/` in the math sources become
         <mi minsize="120%" maxsize="120%" stretchy="true">/</mi>
     texmath applies the \\big sizing attributes to whatever element the delimiter
     maps to, and `/` maps to <mi>; those three attributes are <mo>-only, so the
     MathML fails validation. Fix: retag such a token as <mo>, which is what a
     sized delimiter is anyway -- same rendering, valid MathML. (The PDF and the
     MathJax HTML never see this: both consume the original TeX.)

Usage:
    python tools/fix_epub.py [EPUB ...]   # default: every .epub in the output dir
    python tools/fix_epub.py --check      # report only, exit 1 if fixes are needed
"""

from __future__ import annotations

import argparse
import base64
import glob
import hashlib
import os
import posixpath
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

# Attributes the MathML content model allows on <mo> and nowhere else. A token
# element carrying any of them is a mis-tagged operator.
MO_ONLY_ATTRS = {
    "stretchy", "minsize", "maxsize", "form", "fence", "separator",
    "largeop", "symmetric", "movablelimits",
}

OPEN_TOKEN_RE = re.compile(r"<(mi|mn)\b([^>]*)>")
ATTR_NAME_RE = re.compile(r"([A-Za-z_:][-.\w:]*)\s*=")
ITEM_RE = re.compile(r"<item\b[^>]*?/?>")
# Properties we can detect reliably from the document text, and the markup that
# proves the document uses them.
DETECTABLE_PROPS = (("mathml", "<math"), ("svg", "<svg"))


def report(line: str) -> None:
    """Print progress without ever letting the console encoding abort the run."""
    try:
        print(line)
    except UnicodeEncodeError:  # e.g. Windows cp1252 vs the Persian file name
        enc = sys.stdout.encoding or "ascii"
        print(line.encode(enc, "replace").decode(enc, "replace"))


def retag_mo_only_tokens(text: str) -> tuple[str, int]:
    """Retag <mi>/<mn> tokens that carry <mo>-only attributes as <mo>."""
    edits = []  # (start, end, replacement)
    for m in OPEN_TOKEN_RE.finditer(text):
        tag, attrs = m.group(1), m.group(2)
        if attrs.rstrip().endswith("/"):
            continue  # self-closing: no content, no closing tag to rewrite
        if not (set(ATTR_NAME_RE.findall(attrs)) & MO_ONLY_ATTRS):
            continue
        # Token elements hold text only, so the next closing tag is ours.
        close = text.find(f"</{tag}>", m.end())
        if close < 0:
            continue
        edits.append((m.start(), m.end(), f"<mo{attrs}>"))
        edits.append((close, close + len(tag) + 3, "</mo>"))
    if not edits:
        return text, 0
    out, prev = [], 0
    for start, end, repl in sorted(edits):
        out.append(text[prev:start])
        out.append(repl)
        prev = end
    out.append(text[prev:])
    return "".join(out), len(edits) // 2


def declare_used_properties(opf_text: str, opf_name: str,
                            files: dict[str, bytes]) -> tuple[str, list[str]]:
    """Add manifest properties that the referenced documents actually use."""
    base = posixpath.dirname(opf_name)
    added: list[str] = []

    def fix_item(m: re.Match) -> str:
        item = m.group(0)
        href_m = re.search(r'href="([^"]*)"', item)
        if not href_m:
            return item
        href = urllib.parse.unquote(href_m.group(1))
        if not href.endswith((".xhtml", ".html")):
            return item
        data = files.get(posixpath.normpath(posixpath.join(base, href)))
        if data is None:
            return item
        text = data.decode("utf-8", "replace")
        props_m = re.search(r'properties="([^"]*)"', item)
        props = props_m.group(1).split() if props_m else []
        new = [p for p, marker in DETECTABLE_PROPS
               if marker in text and p not in props]
        if not new:
            return item
        added.extend(f"{href}: {p}" for p in new)
        value = " ".join(props + new)
        if props_m:
            return item[:props_m.start(1)] + value + item[props_m.end(1):]
        # No properties attribute yet: insert one before the tag's end.
        stripped = item.rstrip()
        if stripped.endswith("/>"):
            return f'{stripped[:-2].rstrip()} properties="{value}" />'
        return f'{stripped[:-1].rstrip()} properties="{value}">'

    return ITEM_RE.sub(fix_item, opf_text), added


HTML_TAG_RE = re.compile(r"<html\b[^>]*>")
LTR_ISLAND_RE = re.compile(r"<(code|kbd|samp|pre|math)\b([^>]*)>")
DATA_URI_RE = re.compile(
    r"""url\(\s*(['"]?)(data:image/(?P<ext>[a-z]+)[^;]*;base64,(?P<b64>[A-Za-z0-9+/=\s]+?))\1\s*\)""")


def externalize_data_uris(files: dict[str, bytes], base: str) -> list[str]:
    """Turn `url(data:image/png;base64,...)` into references to real files.

    Quarto inlines its callout icons as base64 data URIs in a <style> block that
    goes into EVERY document. Amazon's converter cannot digest them: it reports
    "conversion successful", writes no book, and KDP answers "We couldn't
    convert your HTML file to Kindle format" (verified by bisection against
    Kindle Previewer -- removing these is what makes conversion produce output,
    and it also restores Enhanced Typesetting support).

    Extracting rather than deleting keeps the callout icons -- the book uses
    2,400+ callouts -- and drops ~1.4 MB of base64 repeated across 90 files.
    The href is computed per file: documents live in EPUB/text/ and the
    stylesheet in EPUB/styles/ ("../media/NAME"), but nav.xhtml sits at the
    package root, where "../media/NAME" would point outside the container.
    """
    media_dir = f"{base}/media" if base else "media"
    extracted: dict[str, str] = {}   # base64 payload -> file name
    touched: list[str] = []

    def replace(m: re.Match, prefix: str) -> str:
        payload = m.group("b64")
        name = extracted.get(payload)
        if name is None:
            raw = base64.b64decode("".join(payload.split()), validate=False)
            ext = "jpg" if m.group("ext") == "jpeg" else m.group("ext")
            name = f"callout-{hashlib.sha1(raw).hexdigest()[:8]}.{ext}"
            extracted[payload] = name
            files[f"{media_dir}/{name}"] = raw
        return f"url({prefix}{name})"

    for name in [n for n in files if n.endswith((".xhtml", ".html", ".css"))]:
        text = files[name].decode("utf-8")
        prefix = posixpath.relpath(media_dir, posixpath.dirname(name)) + "/"
        fixed, n = DATA_URI_RE.subn(lambda m: replace(m, prefix), text)
        if n:
            files[name] = fixed.encode("utf-8")
            touched.append(f"{name}: externalized {n} data: URI(s)")

    if extracted:
        opf_name = next(n for n in files if n.endswith(".opf"))
        opf = files[opf_name].decode("utf-8")
        items = "".join(
            f'\n    <item id="{os.path.splitext(n)[0]}" href="media/{n}" '
            f'media-type="image/{"jpeg" if n.endswith("jpg") else n.rsplit(".",1)[1]}" />'
            for n in sorted(set(extracted.values())))
        files[opf_name] = opf.replace(
            "</manifest>", f"{items}\n  </manifest>").encode("utf-8")
        touched.append(
            f"{opf_name}: added {len(set(extracted.values()))} extracted icon(s)")
    return touched


def enforce_bidi_attributes(text: str) -> tuple[str, int]:
    """Carry the page's direction on `dir` attributes instead of CSS.

    The EPUB 3 CSS profile prohibits `direction` and `unicode-bidi` in a style
    sheet (epubcheck CSS-001), so theme/epub.css cannot set them and the
    direction has to live on the content. Pandoc emits neither:

      * <html> gets only lang="fa", so without this the whole Persian book
        depends on a CSS property the spec forbids -- strip it and the text
        reflows left-to-right.
      * code/kbd/samp/pre and MathML are LTR islands inside RTL prose; without
        dir="ltr" the bidi algorithm reorders them (a code line ending in a
        semicolon is the classic giveaway).

    Elements that already carry a dir -- ltr.lua's [..]{.ltr} spans -- are left
    exactly as they are.
    """
    count = 0

    def fix_html(m: re.Match) -> str:
        nonlocal count
        tag = m.group(0)
        if "dir=" in tag:
            return tag
        count += 1
        return tag[:-1].rstrip() + ' dir="rtl">'

    def fix_island(m: re.Match) -> str:
        nonlocal count
        tag, attrs = m.group(1), m.group(2)
        if "dir=" in attrs:
            return m.group(0)
        count += 1
        closing = "/>" if attrs.rstrip().endswith("/") else ">"
        body = attrs.rstrip()[:-1].rstrip() if closing == "/>" else attrs.rstrip()
        return f"<{tag}{body} dir=\"ltr\"{closing}"

    text = HTML_TAG_RE.sub(fix_html, text, count=1)
    text = LTR_ISLAND_RE.sub(fix_island, text)
    return text, count


def repack(path: str, infos: list[zipfile.ZipInfo], files: dict[str, bytes]) -> None:
    """Write `files` back to `path` as an OCF-conformant EPUB container.

    Entry order and per-entry compression are preserved so the only difference
    from the original is the changed bytes. OCF requires `mimetype` to be the
    first entry, stored uncompressed and with no extra field. Entries absent
    from `files` are dropped, and names in `files` that were not in `infos`
    (new images, for instance) are appended.
    """
    known = {i.filename for i in infos}
    added = [zipfile.ZipInfo(n, date_time=(1980, 1, 1, 0, 0, 0))
             for n in files if n not in known]
    for zi in added:
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
    entries = [i for i in infos if i.filename in files] + added

    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w") as out:
        for info in sorted(entries, key=lambda i: i.filename != "mimetype"):
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = (zipfile.ZIP_STORED if info.filename == "mimetype"
                                else info.compress_type)
            zi.external_attr = info.external_attr
            zi.internal_attr = info.internal_attr
            zi.create_system = info.create_system
            out.writestr(zi, files[info.filename])
    os.replace(tmp, path)


def fix_epub(path: str, check_only: bool = False) -> bool:
    """Apply both fixes to one EPUB. Returns True if anything needed changing."""
    with zipfile.ZipFile(path) as zf:
        infos = zf.infolist()
        files = {i.filename: zf.read(i) for i in infos}

    changed: list[str] = []

    for name, data in list(files.items()):
        if not name.endswith((".xhtml", ".html")):
            continue
        text = data.decode("utf-8")
        fixed, n = retag_mo_only_tokens(text)
        notes = []
        if n:
            notes.append(f"retagged {n} mis-tagged operator(s) as <mo>")
        fixed, d = enforce_bidi_attributes(fixed)
        if d:
            notes.append(f"set dir on {d} element(s)")
        if notes:
            files[name] = fixed.encode("utf-8")
            changed.append(f"{name}: " + "; ".join(notes))

    opf_name = next((n for n in files if n.endswith(".opf")), "")
    changed += externalize_data_uris(files, posixpath.dirname(opf_name))

    for name in [n for n in files if n.endswith(".opf")]:
        text = files[name].decode("utf-8")
        fixed, added = declare_used_properties(text, name, files)
        if added:
            files[name] = fixed.encode("utf-8")
            changed += [f"{name}: declared {a}" for a in added]

    label = os.path.basename(path)
    if not changed:
        report(f"fix_epub: {label}: already conformant, nothing to do")
        return False
    if check_only:
        for line in changed:
            report(f"fix_epub: {label}: {line}")
        return True

    # Repack FIRST, report after: the summary names the (Persian) EPUB file, and
    # a console that cannot encode it must never be what decides whether the fix
    # was applied. (Quarto runs post-render scripts with the Windows ANSI code
    # page, where printing the name raised UnicodeEncodeError mid-run.)

    # Every file we touched must still be well-formed XML before it is repacked.
    for name in {c.split(":", 1)[0] for c in changed}:
        try:
            ET.fromstring(files[name].decode("utf-8"))
        except ET.ParseError as exc:  # pragma: no cover - guards against bad edits
            report(f"fix_epub: {label}: {name} is malformed after fixing: {exc}")
            raise SystemExit(1)

    repack(path, infos, files)
    for line in changed:
        report(f"fix_epub: {label}: {line}")
    report(f"fix_epub: {label}: applied {len(changed)} fix(es)")
    return True


def main() -> int:
    # Quarto runs post-render scripts with the platform's ANSI code page on
    # Windows; UTF-8 keeps the Persian EPUB name readable in the render log.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("epubs", nargs="*", help="EPUB files (default: the output dir's)")
    parser.add_argument("--check", action="store_true",
                        help="report needed fixes without writing; exit 1 if any")
    args = parser.parse_args()

    epubs = args.epubs
    if not epubs:
        out_dir = os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_book")
        epubs = sorted(glob.glob(os.path.join(out_dir, "*.epub")))
    if not epubs:
        report("fix_epub: no .epub found -- nothing to do")
        return 0

    needed = [fix_epub(p, args.check) for p in epubs]
    return 1 if (args.check and any(needed)) else 0


if __name__ == "__main__":
    sys.exit(main())
