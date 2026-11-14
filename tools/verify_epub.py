#!/usr/bin/env python3
"""Run the two validators a store runs, over the books in _book/.

  epubcheck        the EPUB 3 conformance checker. KDP and Apple both reject on
                   its errors -- this is the "verifier" that fails an upload.
  Kindle Previewer Amazon's own converter. It reports the conversion status,
                   the error/quality counts, and whether the title qualifies for
                   Enhanced Typesetting.

Both are external tools; see the README for one-line installs. This script only
locates them, and fetches epubcheck into .tools/ if it is not already there.

    python tools/verify_epub.py                # every _book/*.epub
    python tools/verify_epub.py path/to.epub   # a specific file
    python tools/verify_epub.py --epubcheck-only

IMPORTANT (the reason this script exists rather than a one-line command): the
book's file name is Persian, and both tools are Java/JVM-based. On Windows the
JVM decodes command-line paths with the ANSI code page, so a non-ASCII name
arrives as "????" and the tool reports "File not found" -- which reads exactly
like a corrupt book. Each EPUB is therefore copied to an ASCII temporary name
before being checked. Kindle Publishing Guidelines 21.1.12 says the same thing
from the other side: keep special characters out of the file name.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, ".tools")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
EPUBCHECK_LATEST = "https://github.com/w3c/epubcheck/releases/latest"
# Some download servers (the Adoptium API) answer 403 to Python's default
# "Python-urllib" user agent, so every request names this generic client.
USER_AGENT = "farsi-book-build/1.0"


def download(url: str, dest: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as fh:
        shutil.copyfileobj(resp, fh)


JAVA_FEATURE = 25   # LTS release fetched by --install-tools


def find_portable_java() -> str | None:
    """Newest JRE unpacked into .tools/ by --install-tools (any OS layout)."""
    hits = []
    for pattern in (("jdk-*", "bin", "java.exe"), ("jdk-*", "bin", "java"),
                    ("jdk-*", "Contents", "Home", "bin", "java")):
        hits += glob.glob(os.path.join(TOOLS, *pattern))
    if not hits:
        return None

    def version(path: str) -> list[int]:
        name = os.path.relpath(path, TOOLS).split(os.sep)[0]
        return [int(n) for n in re.findall(r"\d+", name)]
    return max(hits, key=version)


def find_java() -> str | None:
    exe = shutil.which("java")
    if exe:
        return exe
    # a portable JRE unzipped into .tools/ (no system install needed)
    portable = find_portable_java()
    if portable:
        return portable
    for base in (r"C:\Program Files\Eclipse Adoptium",
                 r"C:\Program Files\Java",
                 r"C:\Program Files (x86)\Eclipse Adoptium"):
        for path in glob.glob(os.path.join(base, "*", "bin", "java.exe")):
            return path
    return None


def find_epubcheck() -> str | None:
    hits = glob.glob(os.path.join(TOOLS, "epubcheck-*", "epubcheck.jar"))
    if not hits:
        return None

    # several versions may be unpacked side by side: use the newest, not the
    # first in directory order (that would be the oldest)
    def version(path: str) -> tuple[int, ...]:
        name = os.path.basename(os.path.dirname(path))
        return tuple(int(n) for n in re.findall(r"\d+", name))
    return max(hits, key=version)


def fetch_epubcheck() -> str | None:
    """Download the newest epubcheck into .tools/ (resolved via the redirect)."""
    os.makedirs(TOOLS, exist_ok=True)
    try:
        req = urllib.request.Request(EPUBCHECK_LATEST, method="HEAD",
                                     headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req) as resp:
            ver = resp.url.rstrip("/").rsplit("/v", 1)[-1]
        url = (f"https://github.com/w3c/epubcheck/releases/download/"
               f"v{ver}/epubcheck-{ver}.zip")
        print(f"verify_epub: downloading epubcheck {ver} ...")
        zip_path = os.path.join(TOOLS, "epubcheck.zip")
        download(url, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(TOOLS)
        os.remove(zip_path)
    except Exception as exc:  # offline, proxy, GitHub down ...
        print(f"verify_epub: could not fetch epubcheck ({exc})")
        return None
    return find_epubcheck()


def fetch_java() -> str | None:
    """Download a portable Eclipse Temurin JRE into .tools/ (no admin rights).

    Uses the Adoptium API's "latest GA build" redirect for this OS/CPU; the
    archive unpacks to a single jdk-<version>-jre folder.
    """
    import platform
    import tarfile
    osname = {"win32": "windows", "darwin": "mac"}.get(sys.platform, "linux")
    machine = platform.machine().lower()
    arch = "aarch64" if machine in ("arm64", "aarch64") else "x64"
    url = (f"https://api.adoptium.net/v3/binary/latest/{JAVA_FEATURE}/ga/"
           f"{osname}/{arch}/jre/hotspot/normal/eclipse")
    os.makedirs(TOOLS, exist_ok=True)
    try:
        print(f"verify_epub: downloading a portable Java {JAVA_FEATURE} runtime ({osname}/{arch}) ...")
        archive = os.path.join(TOOLS, "jre-download")
        download(url, archive)
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(TOOLS)
        else:
            with tarfile.open(archive) as tf:
                tf.extractall(TOOLS)
        os.remove(archive)
    except Exception as exc:  # offline, proxy ...
        print(f"verify_epub: could not fetch Java ({exc})")
        return None
    java = find_portable_java()
    if java and not java.endswith(".exe"):
        os.chmod(java, 0o755)
    return java


def install_tools() -> bool:
    """Make sure Java and epubcheck are available; fetch what is missing."""
    java = find_java() or fetch_java()
    jar = find_epubcheck() or fetch_epubcheck()
    print(f"verify_epub: java      -> {java or 'NOT AVAILABLE'}")
    print(f"verify_epub: epubcheck -> {jar or 'NOT AVAILABLE'}")
    return bool(java and jar)


def find_previewer() -> str | None:
    """Kindle Previewer 4 if present (guidelines 2026.3, section 2.2.1), else 3.

    Version 4 is an MSIX app: there is no "Amazon\\Kindle Previewer" folder any
    more, only the command-line aliases kindlepreviewer4.exe / kpr4.exe in
    %LOCALAPPDATA%\\Microsoft\\WindowsApps, and its options take two dashes.
    (Version 3 upgrades itself to 4 the next time it is started, removing its
    own folder -- a missing "Kindle Previewer 3.exe" usually means exactly that.)
    """
    alias = shutil.which("kindlepreviewer4") or shutil.which("kpr4")
    if not alias:
        cand = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft",
                            "WindowsApps", "kindlepreviewer4.exe")
        alias = cand if os.path.lexists(cand) else None
    if alias:
        return alias
    for base in (os.environ.get("LOCALAPPDATA", ""),
                 r"C:\Program Files", r"C:\Program Files (x86)"):
        if not base:
            continue
        exe = os.path.join(base, "Amazon", "Kindle Previewer 3",
                           "Kindle Previewer 3.exe")
        if os.path.exists(exe):
            return exe
    return None


def ascii_copy(src: str, tmpdir: str) -> str:
    """Copy to an ASCII name so the JVM can actually open it (see module docs)."""
    stem = os.path.splitext(os.path.basename(src))[0]
    safe = re.sub(r"-{2,}", "-", re.sub(r"[^A-Za-z0-9]+", "-", stem)).strip("-")
    if len(re.sub(r"[^A-Za-z0-9]", "", safe)) < 3:
        safe = "book"
    dst = os.path.join(tmpdir, safe + ".epub")
    shutil.copy2(src, dst)
    return dst


APPLE_MAX_PIXELS = 5_600_000


def check_image_pixels(epub: str) -> bool:
    """Apple Books rejects any raster image above 5.6 megapixels (ITMS-9000).

    epubcheck does not test this, so a book that passes it can still bounce at
    upload. Checked for every EPUB, since either file may end up there.
    """
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    big = []
    with zipfile.ZipFile(epub) as zf:
        for name in zf.namelist():
            if re.search(r"\.(png|jpe?g|gif|webp)$", name, re.I):
                with zf.open(name) as fh:
                    w, h = Image.open(fh).size
                if w * h > APPLE_MAX_PIXELS:
                    big.append(f"{name} {w}x{h} ({w * h / 1e6:.1f} MP)")
    for line in big:
        print(f"    ERROR {line}")
    print(f"    {'no image' if not big else f'{len(big)} image(s)'} above 5.6 megapixels")
    return not big


def run_epubcheck(java: str, jar: str, epub: str) -> bool:
    proc = subprocess.run([java, "-jar", jar, epub],
                          capture_output=True, text=True, errors="replace")
    out = (proc.stdout or "") + (proc.stderr or "")
    problems = [l for l in out.splitlines()
                if l.startswith(("ERROR", "FATAL", "WARNING"))]
    for line in problems[:25]:
        print(f"    {line}")
    if len(problems) > 25:
        print(f"    ... and {len(problems) - 25} more")
    tally = next((l for l in out.splitlines() if l.startswith("Messages:")), "")
    print(f"    {tally.strip() or out.strip().splitlines()[-1:]}")
    return not any(l.startswith(("ERROR", "FATAL")) for l in problems)


def run_previewer(exe: str, epub: str, outdir: str, keep_dir: str | None = None) -> bool:
    # Kindle Previewer will not create its own output directory; given a missing
    # one it exits 0 having done nothing, which looks like a failed conversion.
    os.makedirs(outdir, exist_ok=True)
    # A conversion that was killed leaves %TEMP%\kpr_cli_<name>_epub behind, and
    # every later conversion of a file with that name then fails in
    # "Pre-processing" within seconds. Only one conversion may run at a time
    # anyway, so the folder is always stale here.
    stem = os.path.splitext(os.path.basename(epub))[0]
    shutil.rmtree(os.path.join(tempfile.gettempdir(), f"kpr_cli_{stem}_epub"),
                  ignore_errors=True)
    v4 = "4" in os.path.basename(exe)
    cmd = ([exe, epub, "--convert", "--output", outdir, "--locale", "en"] if v4
           else [exe, epub, "-convert", "-output", outdir, "-log", "info"])
    print(f"    (Kindle Previewer {'4' if v4 else '3'}; a full book takes tens of minutes)")
    subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    summary = os.path.join(outdir, "Summary_Log.csv")
    if not os.path.exists(summary):
        print("    Kindle Previewer wrote no summary log -- conversion did not run")
        return False
    with open(summary, encoding="utf-8-sig") as fh:
        rows = [r for r in fh.read().splitlines() if r.strip()]
    if len(rows) < 2:
        print("    Kindle Previewer summary is empty")
        return False
    cols = [c.strip('"') for c in re.findall(r'"[^"]*"|[^,]+', rows[1])]
    keys = [c.strip('"') for c in re.findall(r'"[^"]*"|[^,]+', rows[0])]
    info = dict(zip(keys, cols))
    for k in ("Conversion Status", "Error Count", "Quality Issue Count",
              "Enhanced Typesetting Status"):
        if k in info:
            print(f"    {k}: {info[k]}")
    # the per-book log lists the errors/warnings behind the counts
    for log in glob.glob(os.path.join(outdir, "Logs", "*.csv")):
        with open(log, encoding="utf-8-sig", errors="replace") as fh:
            for row in fh.read().splitlines()[1:21]:
                print(f"    log: {row}")
    ok = (info.get("Conversion Status", "").lower().startswith("success")
          and info.get("Error Count", "0").strip() in ("0", ""))
    if ok and keep_dir:
        # the converted book is what Kindle Previewer opens (and KDP accepts)
        os.makedirs(keep_dir, exist_ok=True)
        for kpf in glob.glob(os.path.join(outdir, "KPF", "*.kpf")):
            dst = os.path.join(keep_dir, os.path.basename(kpf))
            shutil.copy2(kpf, dst)
            print(f"    kept {os.path.relpath(dst, ROOT)}")
    return ok


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("epubs", nargs="*")
    ap.add_argument("--epubcheck-only", action="store_true")
    ap.add_argument("--previewer-only", action="store_true")
    ap.add_argument("--install-tools", action="store_true",
                    help="only fetch a portable Java + epubcheck into .tools/ and exit")
    args = ap.parse_args()

    if args.install_tools:
        return 0 if install_tools() else 1

    epubs = args.epubs or sorted(glob.glob(os.path.join(ROOT, "_book", "*.epub")))
    if not epubs:
        print("verify_epub: no .epub found in _book/")
        return 1

    java = find_java()
    jar = find_epubcheck() or fetch_epubcheck()
    previewer = find_previewer()

    want_ec = not args.previewer_only
    want_kp = not args.epubcheck_only
    ok = True
    if want_ec and not (java and jar):
        # not a pass: a book that was never checked must not be reported as clean
        print("verify_epub: epubcheck cannot run (no Java or no epubcheck) -- "
              "run `python tools/verify_epub.py --install-tools`")
        ok = False
    if want_kp and not previewer:
        print("verify_epub: Kindle Previewer not found (see docs/BUILD.md)")

    for src in epubs:
        size = os.path.getsize(src) / 1024 / 1024
        print(f"\n=== {os.path.basename(src)} ({size:.1f} MB) ===")
        if src.lower().endswith("-kindle.epub") and not args.epubcheck_only:
            # the rules of the Kindle Publishing Guidelines that neither tool reports
            import kindle_audit
            print("  Kindle Publishing Guidelines (tools/kindle_audit.py):")
            result = kindle_audit.audit(src)
            for level, section, what, detail in result.rows:
                if level != "ok":
                    print(f"    {level} [{section}] {what}" + (f": {detail}" if detail else ""))
            print(f"    {result.count('ok')} checks passed, {result.count('WARN')} warning(s), "
                  f"{result.count('FAIL')} failure(s)")
            ok &= result.count("FAIL") == 0
        print("  Image size (Apple Books limit):")
        ok &= check_image_pixels(src)
        with tempfile.TemporaryDirectory() as tmp:
            epub = ascii_copy(src, tmp)
            if want_ec and java and jar:
                print(f"  epubcheck ({os.path.basename(os.path.dirname(jar))}):")
                ok &= run_epubcheck(java, jar, epub)
            if want_kp and previewer:
                print("  Kindle Previewer:")
                keep = (os.path.join(ROOT, "_book", "kindle-preview")
                        if os.path.dirname(os.path.abspath(src)) == os.path.join(ROOT, "_book")
                        else None)
                ok &= run_previewer(previewer, epub, os.path.join(tmp, "kp"), keep)
    print("\nverify_epub:", "all checks passed" if ok else "problems found (above)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
