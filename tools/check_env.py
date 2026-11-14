#!/usr/bin/env python3
"""Check that this computer has everything needed to build and commit the book.

    python tools/check_env.py            # full report; exit 1 if something required is missing
    python tools/check_env.py --quick    # skip the (slower) font look-ups

Every row says what was found and, when something is missing, the command that
fixes it. tools/setup_windows.ps1 runs this at the end; tools/build_all.py runs
it before building. The versions under TESTED are the toolchain the current
outputs were built and validated with (see docs/BUILD.md).
"""
from __future__ import annotations

import argparse
import importlib
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The toolchain this workflow was last built and validated with (2026-11-13).
TESTED = {
    "quarto": "1.11.9",
    "texlive": "TeX Live 2026 (TinyTeX), LuaHBTeX 1.24.0",
    "python": "3.14.1",
    "pymupdf": "2.1",
    "java": "25 (Temurin JRE, portable in .tools/)",
    "epubcheck": "5.4.0",
    "kindle previewer": "4.0.4",
    "git": "2.52",
}
MIN_QUARTO = (1, 4)
MIN_PYTHON = (3, 10)
PY_MODULES = [  # (import name, pip name)
    ("yaml", "PyYAML"), ("pymupdf", "pymupdf"), ("pypdfium2", "pypdfium2"),
    ("numpy", "numpy"), ("PIL", "Pillow"),
]


def tex_env() -> dict[str, str]:
    """Environment with TinyTeX on PATH (a fresh install may not be on it yet)
    and the repo fonts visible to luaotfload (see docs/BUILD.md, OSFONTDIR)."""
    env = dict(os.environ)
    tiny = os.path.join(env.get("APPDATA", ""), "TinyTeX", "bin", "windows")
    if os.path.isdir(tiny) and not shutil.which("lualatex", path=env.get("PATH")):
        env["PATH"] = tiny + os.pathsep + env.get("PATH", "")
    fonts = os.path.join(ROOT, "fonts")
    env["OSFONTDIR"] = fonts + (os.pathsep + env["OSFONTDIR"] if env.get("OSFONTDIR") else "")
    return env


def run(cmd: list[str], env: dict | None = None, timeout: int = 120) -> tuple[int, str]:
    exe = shutil.which(cmd[0], path=(env or os.environ).get("PATH"))
    if not exe:
        return 127, ""
    try:
        p = subprocess.run([exe] + cmd[1:], capture_output=True, text=True,
                           errors="replace", env=env, timeout=timeout, cwd=ROOT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def version_tuple(text: str) -> tuple[int, ...]:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    return tuple(int(g) for g in m.groups() if g is not None) if m else ()


def tex_packages() -> list[tuple[str, str]]:
    rows = []
    with open(os.path.join(ROOT, "tools", "tex-packages.txt"), encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].split()
            if len(line) >= 2:
                rows.append((line[0], line[1]))
    return rows


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str, str]] = []

    def add(self, status: str, what: str, detail: str = "", fix: str = "") -> None:
        self.rows.append((status, what, detail, fix))
        mark = {"ok": " OK ", "warn": "WARN", "miss": "MISS", "info": "INFO"}[status]
        print(f"[{mark}] {what}" + (f" -- {detail}" if detail else ""))
        if fix and status in ("warn", "miss"):
            print(f"       fix: {fix}")

    def missing(self) -> int:
        return sum(1 for r in self.rows if r[0] == "miss")

    def warnings(self) -> int:
        return sum(1 for r in self.rows if r[0] == "warn")


def check(quick: bool) -> Report:
    r = Report()
    env = tex_env()
    win = sys.platform == "win32"

    print("== Python ==")
    pv = sys.version_info[:3]
    if "WindowsApps" in sys.executable:
        r.add("miss", "Python interpreter", f"{sys.executable} is the Microsoft Store stub",
              "winget install Python.Python.3.14  (then open a new terminal)")
    elif pv[:2] < MIN_PYTHON:
        r.add("miss", "Python", f"{'.'.join(map(str, pv))} < 3.10", "install Python 3.10 or newer")
    else:
        r.add("ok", "Python", f"{'.'.join(map(str, pv))} at {sys.executable} (tested {TESTED['python']})")
    for mod, pip in PY_MODULES:
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", None) or getattr(m, "VersionBind", "")
            r.add("ok", f"python module {pip}", str(ver))
        except Exception as exc:  # ImportError, or a broken binary wheel
            r.add("miss", f"python module {pip}", type(exc).__name__,
                  f"{os.path.basename(sys.executable)} -m pip install -r requirements.txt")

    print("== Publishing tools ==")
    code, out = run(["git", "--version"])
    r.add("ok" if code == 0 else "miss", "Git", out.strip(), "winget install Git.Git")
    code, out = run(["quarto", "--version"])
    qv = version_tuple(out)
    if code != 0 or not qv:
        r.add("miss", "Quarto", "not found", "winget install Posit.Quarto  (or https://quarto.org/docs/get-started/)")
    elif qv[:2] < MIN_QUARTO:
        r.add("miss", "Quarto", f"{out.strip()} is older than 1.4", "winget upgrade Posit.Quarto")
    else:
        r.add("ok", "Quarto", f"{out.strip()} (tested {TESTED['quarto']}; it bundles its own Pandoc)")

    print("== TeX (LuaLaTeX) ==")
    code, out = run(["lualatex", "--version"], env)
    if code != 0:
        r.add("miss", "LuaLaTeX", "not found",
              "quarto install tinytex --update-path  (then open a new terminal)")
    else:
        r.add("ok", "LuaLaTeX", out.splitlines()[0].strip() + f" (tested {TESTED['texlive']})")
        pk = tex_packages()
        code, out = run(["kpsewhich"] + [f for _, f in pk], env)
        found = {os.path.basename(line.strip()).lower() for line in out.splitlines() if line.strip()}
        absent = [p for p, f in pk if f.lower() not in found]
        if absent:
            r.add("miss", f"TeX packages ({len(pk) - len(absent)}/{len(pk)} present)",
                  "missing: " + " ".join(absent),
                  "tlmgr install " + " ".join(absent))
        else:
            r.add("ok", f"TeX packages ({len(pk)}/{len(pk)} from tools/tex-packages.txt)")
        for ttf in ("Vazirmatn-Regular.ttf", "Vazirmatn-Bold.ttf"):
            if not os.path.exists(os.path.join(ROOT, "fonts", ttf)):
                r.add("miss", f"fonts/{ttf}", "not in the checkout", "git checkout -- fonts/")
        if not quick:
            for name in ("Latin Modern Mono", "Vazirmatn"):
                code, out = run(["luaotfload-tool", f"--find={name}"], env, timeout=600)
                if code == 0 and "Resolved" in out:
                    path = re.search(r'"([^"]+)"', out.split("Resolved", 1)[1])
                    r.add("ok", f"font by name: {name}", os.path.basename(path.group(1)) if path else "")
                else:
                    fix = ('set OSFONTDIR to the repo fonts folder, then: luaotfload-tool --update --force'
                           if name == "Vazirmatn" else "tlmgr install lm")
                    r.add("miss", f"font by name: {name}", "luaotfload cannot resolve it", fix)

    print("== Validation (needed for the verify step) ==")
    import verify_epub
    java, jar = verify_epub.find_java(), verify_epub.find_epubcheck()
    fix = "python tools/verify_epub.py --install-tools"
    if java:
        code, out = run([java, "-version"])
        r.add("ok", "Java", (out.splitlines() or [""])[0].strip() + f" ({java})")
    else:
        r.add("warn", "Java", "not found (epubcheck cannot run)", fix)
    r.add("ok" if jar else "warn", "epubcheck",
          os.path.basename(os.path.dirname(jar)) if jar else "not in .tools/", fix)
    kp = verify_epub.find_previewer()
    if kp:
        r.add("ok", "Kindle Previewer", kp)
    elif win or sys.platform == "darwin":
        r.add("warn", "Kindle Previewer", "not found (optional: Amazon's own Kindle conversion check)",
              "winget install Amazon.KindlePreviewer  (or https://kdp.amazon.com/en_US/help/topic/G202131170)")
    else:
        r.add("info", "Kindle Previewer", "not available on Linux; epubcheck + kindle_audit still run")

    print("== Git (to commit) ==")
    code, out = run(["git", "rev-parse", "--is-inside-work-tree"])
    if code != 0 or "true" not in out:
        r.add("warn", "git repository", "this folder is not a git checkout",
              "git init   (or clone your book's repository)")
    else:
        for key in ("user.name", "user.email"):
            code, out = run(["git", "config", key])
            r.add("ok" if code == 0 and out.strip() else "warn", f"git {key}",
                  out.strip() or "not set (git refuses to commit)",
                  f'git config --global {key} "..."')
        code, out = run(["git", "config", "core.quotepath"])
        r.add("ok" if out.strip() == "false" else "warn", "git core.quotepath",
              "false (Persian file names readable)" if out.strip() == "false"
              else "Persian file names show as \\331\\276... in git status",
              "git config core.quotepath false")
        if win:
            code, out = run(["git", "config", "core.longpaths"])
            r.add("ok" if out.strip() == "true" else "warn", "git core.longpaths",
                  out.strip() or "not set", "git config core.longpaths true")

    print("== Output folder ==")
    book = os.path.join(ROOT, "_book")
    if os.path.isdir(book):
        probe = book + ".locktest"
        try:
            os.rename(book, probe)
            os.rename(probe, book)
            r.add("ok", "_book/ can be replaced by quarto render")
        except OSError as exc:
            r.add("warn", "_book/ is in use", str(exc),
                  "close Explorer windows, terminals (cd) and viewers that are inside _book/")
    else:
        r.add("info", "_book/", "not built yet")
    return r


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true", help="skip the font look-ups")
    args = ap.parse_args()
    r = check(args.quick)
    print()
    if r.missing():
        print(f"check_env: {r.missing()} required item(s) missing, {r.warnings()} warning(s) -- see 'fix:' lines above")
        return 1
    print(f"check_env: ready to build ({r.warnings()} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
