# Building a book: toolchain, workflow and pitfalls

*[فارسی](BUILD.fa.md)*

This guide takes a **brand-new computer** to the point where it builds every
edition of a book made from this template and can commit to its repository.
The toolchain and the versions below are the ones a 2,900-page, 228-figure
Persian engineering book was built and validated with on 2026-11-13 (a
clean-room run on Windows: fresh clone, fresh TinyTeX, fresh Python, Java and
epubcheck downloaded from the internet). The template's own sample book was
built with the same tools on the same day.

Authoring conventions (RTL prose, LTR islands, figures) are in the
[README](../README.md); this file is about tools and builds.

---

## 1. Quick start (Windows)

```powershell
# 1. Git, then your copy of the template
winget install Git.Git            # then open a NEW PowerShell window
git clone <the URL of your book's repository>
cd <its folder>

# 2. Every tool the build needs (safe to re-run; skips what is installed)
powershell -ExecutionPolicy Bypass -File tools\setup_windows.ps1 `
    -GitName "Your Name" -GitEmail "you@example.com" -WithKindlePreviewer

# 3. In a NEW PowerShell window (so the PATH changes apply)
python tools\check_env.py         # every row should be OK
python tools\build_all.py         # builds everything into _book\

# 4. Commit your source changes (the outputs are git-ignored)
git status
git add -A
git commit -m "Describe the change"
git push
```

`-WithKindlePreviewer` is optional (Amazon's own conversion check, see §6);
the `-GitName/-GitEmail` pair is only needed once per computer.
Linux and macOS: §3.3.

The sample book builds in about a minute. Open `_book/index.html` and the
PDF: Persian must flow right-to-left in Vazirmatn, math/code/English must be
left-to-right and not mirrored, and the figure must be sharp. Then select a
Persian sentence in the PDF, copy it and paste it into a text editor: it must
come out as the sentence you see (§5).

---

## 2. What the build produces

Everything lands in `_book/`, which git ignores. File names come from the
`title:` in `_quarto.yml`, so the PDF and the EPUB of a Persian title have
Persian names.

| File in `_book/` | What it is | Where it goes |
|---|---|---|
| `index.html` + `chapters/`, `site_libs/`, … | the website | GitHub Pages (deployed by CI on every push to `main`) |
| `<title>.pdf` | print / PDF edition, with copyable and searchable Persian text | readers, print |
| `<title>.epub` | the EPUB 3: MathML equations, vector figures | **Apple Books**, Google Play Books, Kobo, … |
| `<ascii>-kindle.epub` | Kindle edition (equations as text/PNG, figures as PNG, wrapping code) | **Amazon KDP only** |
| `<ascii>-kindle-cover.jpg` / `.tif` | Kindle marketing cover, 2560 px high, 300 DPI, sRGB | KDP cover upload |
| `kindle-preview/*.kpf` | Kindle Previewer's conversion (only with `--kindle-previewer`) | open in Kindle Previewer |

The outputs of the sample book are committed in [`examples/`](../examples/), so
you can compare your first build with them.

`<ascii>` is what is left of the title after dropping everything but Latin
letters and digits (`MRI-kindle.epub` for a title containing "MRI"), or `book`
when nothing is left. Do not upload the `-kindle.epub` to Apple: it is the
degraded copy made for Amazon's converter. Apple gets the main EPUB.

You do not have to publish every edition. `python tools/build_all.py --no-kindle`
skips the Kindle files; removing the `epub:` block from `_quarto.yml` drops the
EPUB (the later steps then have nothing to do, so pass `--no-kindle --no-verify`).

---

## 3. The toolchain

### 3.1 Validated versions

| Tool | Version | Used for | Installed by |
|---|---|---|---|
| Git | 2.52 | version control | `winget install Git.Git` |
| Quarto | 1.11.9 (bundles Pandoc 3.10); 1.4 is the minimum | renders HTML, PDF, EPUB | `winget install Posit.Quarto` |
| TinyTeX | TeX Live 2026, LuaHBTeX 1.24.0 | PDF, figures, cover, Kindle equations | `quarto install tinytex --update-path` |
| TeX packages | 39 listed in [`tools/tex-packages.txt`](../tools/tex-packages.txt) | see the comments in that file | `tlmgr install …` |
| Python | 3.14.1 (3.10+ works) | all build tools | `winget install Python.Python.3.14` |
| Python packages | PyMuPDF 2.1, pypdfium2 5.15, Pillow 13, numpy 2.5, PyYAML 6.0 ([`requirements.txt`](../requirements.txt)) | figures, cover, Kindle edition, checks | `pip install -r requirements.txt` |
| Java | 25 LTS (Temurin JRE, portable in `.tools/`) | runs epubcheck | `python tools/verify_epub.py --install-tools` |
| epubcheck | 5.4.0 (in `.tools/`) | the validator the stores run | same command |
| Kindle Previewer | 4.0.4 (optional; Windows/macOS) | Amazon's own conversion check | `winget install Amazon.KindlePreviewer` |
| Fonts | Vazirmatn (in `fonts/`), Latin Modern (TeX) | body, code, math | nothing to install |

**Not needed:** a system-wide Vazirmatn install, a separate Pandoc (Quarto
uses its own), `make` on Windows, or administrator rights (only the winget
installers of Git/Python/Quarto may ask for approval).

`python tools/check_env.py` checks all of the above, plus the git settings
of §8, and prints the command that fixes anything missing.

### 3.2 What `tools/setup_windows.ps1` does

These are the manual steps the script automates. Each one is skipped when
already done.

1. **Git, Python, Quarto** via winget. A `python` that is only the Microsoft
   Store stub (`…\WindowsApps\python.exe`) does not count.
2. **TinyTeX** via `quarto install tinytex --update-path` (into
   `%APPDATA%\TinyTeX`).
3. **TeX packages.** Each line of `tools/tex-packages.txt` is checked with
   `kpsewhich`, and only the missing ones are installed
   (`tlmgr update --self`, then `tlmgr install …`). A fresh TinyTeX lacked
   `luatexbase ctablestack pgfplots fvextra` in the clean-room test.
4. **Font index.** It sets `OSFONTDIR` to the repo's `fonts\` folder and runs
   `luaotfload-tool --update --force`, so LuaTeX can find Vazirmatn by name
   (see §7).
5. **Python packages** with `python -m pip install -r requirements.txt`.
   Without admin rights pip installs into your user profile.
6. **Java + epubcheck** with `python tools\verify_epub.py --install-tools`,
   which downloads into `.tools\`.
7. **Kindle Previewer 4**, only with `-WithKindlePreviewer`.
8. **Git settings** for this repository: `core.quotepath false`,
   `core.longpaths true`, and your name and email if given.
9. **Final check** with `python tools\check_env.py`.

### 3.3 Linux and macOS

The same steps by hand. The CI workflow
([`.github/workflows/build.yml`](../.github/workflows/build.yml)) is the
Linux version of this recipe.

```bash
# Quarto: https://quarto.org/docs/get-started/  (macOS: brew install --cask quarto)
quarto install tinytex --update-path            # then open a new terminal
tlmgr update --self                             # a fresh TinyTeX may refuse installs until this
tlmgr install $(grep -v '^\s*#' tools/tex-packages.txt | awk 'NF {print $1}')
OSFONTDIR="$PWD/fonts" luaotfload-tool --update --force
python3 -m venv .venv && . .venv/bin/activate   # .venv/ is git-ignored
pip install -r requirements.txt
python tools/verify_epub.py --install-tools     # Java + epubcheck into .tools/
git config core.quotepath false
python tools/check_env.py
python tools/build_all.py
```

Kindle Previewer exists for Windows and macOS only. On Linux the Kindle
edition is still built and checked with epubcheck and `kindle_audit.py`.

### 3.4 Every tool in `tools/`

| Script | What it does |
|---|---|
| `setup_windows.ps1` | installs the whole toolchain on Windows (§3.2) |
| `check_env.py` | reports what is installed and how to fix what is not |
| `build_all.py` | the whole build, in the right order, with the checks (§4) |
| `build_diagrams.py` (`.ps1` and `diagrams/Makefile` are wrappers) | `diagrams/*.tex` → cropped PDF + SVG |
| `new_figure.py` | starts a figure from `diagrams/figure-template.tex` |
| `check_diagrams.py` | flags figures that came out blank or uncropped |
| `build_cover.py` | `cover/cover.tex` → `cover/cover.pdf` + `cover.png` |
| `gen_stubs.py` | optional: chapter stubs and the chapter list from `outline/chapters.yml` |
| `fix_epub.py` | runs after every render (Quarto post-render hook): repairs the EPUB for epubcheck/Apple/Kindle |
| `build_kindle_epub.py`, `kindle_math.py` | derive the Kindle edition from the EPUB |
| `make_kindle_cover.py` | the KDP marketing cover from `cover/cover.pdf` |
| `verify_epub.py` | epubcheck, Apple's image-size limit, Kindle Previewer; `--install-tools` fetches Java + epubcheck |
| `kindle_audit.py` | Kindle Publishing Guidelines rules that no other tool reports |
| `pdf_text_check.py` | what a viewer copies out of the PDF; geometry comparison of two PDFs (§5) |
| `pdf_to_png.py` | rasterise PDF pages to look at them |
| `update_examples.py` | copies the sample book's outputs from `_book/` into the committed `examples/` folder (template maintenance only) |
| `source-fixes/*.py` | optional repairs for common markup mistakes in `.qmd` sources (§4.3) |
| `tex-packages.txt` | the TeX package list shared by setup, `check_env.py` and CI |

---

## 4. The build workflow

### 4.1 `python tools/build_all.py`

It runs these steps in order and stops at the first failure. The times are
for the 2,900-page reference book with all 228 figures built from scratch;
the sample book takes about a minute in total.

| Step | Command it runs | What it does | Time (large book) |
|---|---|---|---|
| 1 | `tools/check_env.py` | refuses to start if a required tool is missing | seconds |
| 2 | `tools/build_diagrams.py` | compiles each `diagrams/*.tex` whose PDF/SVG is missing, older than the source, or was never cropped (LuaLaTeX, then PyMuPDF crops it to a tight PDF for print and an SVG for the web). Also builds the cover if `cover/cover.pdf` or `.png` is missing | ~20 min |
| 3 | `quarto render` | HTML site, PDF and EPUB **in one render**; Quarto's post-render hook then runs `tools/fix_epub.py`, which repairs what Pandoc's EPUB writer leaves for epubcheck/Apple | ~45 min |
| 4 | `tools/build_kindle_epub.py` | derives the `-kindle.epub`: equations become Unicode text or PNG, figures PNG (at most 5.5 MP), code listings wrap, navigation becomes 2 levels | ~3 min |
| 5 | `tools/make_kindle_cover.py` | renders `cover/cover.pdf` to the KDP marketing cover (JPEG + TIFF) | seconds |
| 6 | `tools/verify_epub.py --epubcheck-only` and `tools/kindle_audit.py` | epubcheck on both EPUBs, Apple's 5.6-megapixel image limit, the Kindle guideline audit | ~2 min (+~55 min with `--kindle-previewer`) |
| 7 | `git status` before vs after | lists anything the build changed outside the ignored folders (normally nothing) | seconds |

Options:

| Option | Effect |
|---|---|
| `--kindle-previewer` | also converts the Kindle EPUB with Kindle Previewer (Windows/macOS) and keeps the KPF in `_book/kindle-preview/`. Not the main EPUB: on a math-heavy book Previewer chews on its MathML for hours |
| `--skip-render` | reuses the HTML/PDF/EPUB already in `_book/` (rebuild only the Kindle edition, cover and checks) |
| `--force-diagrams` | rebuilds every figure |
| `--no-kindle`, `--no-verify` | skip those steps |

### 4.2 While writing

| You changed | Run |
|---|---|
| chapter text (`chapters/*.qmd`, `appendices/*.qmd`) | `quarto preview` for a live HTML preview; `python tools/build_all.py` before publishing |
| a figure (`diagrams/*.tex`) | `python tools/build_all.py` (rebuilds only that figure), or `python tools/build_diagrams.py <figure-name>` |
| the cover (`cover/cover.tex`) | `python tools/build_cover.py`, then commit `cover.pdf` and `cover.png` |
| the outline (`outline/chapters.yml`, if you use it) | `python tools/gen_stubs.py`. It rewrites only the chapter list between the two marker comments in `_quarto.yml`; edit everything else in `_quarto.yml` by hand |
| a LaTeX package in `theme/preamble.tex` or a figure | add it to `tools/tex-packages.txt` (package name, then a file it provides) |
| the PDF's text pipeline (`theme/pdf-copytext.lua`) | `python tools/pdf_text_check.py OLD.pdf NEW.pdf --geometry`; then copy a few lines in Chrome, Edge and Firefox |

`smoke-test.qmd` is a one-page document with RTL prose, math, code, a figure
and a table. When something looks wrong in the book, render it alone to tell
a toolchain problem from a content problem:
`python tools/build_diagrams.py sample-figure`, then
`quarto render smoke-test.qmd --to pdf` (a single file outside the book, so it
does not touch `_book/`).

### 4.3 Repairing markup (`tools/source-fixes/`)

Chapters drafted quickly, or by an AI assistant, repeat a small set of markup
mistakes that break the PDF build. Each script below fixes one of them in
`chapters/*.qmd` and `appendices/*.qmd`, skipping code blocks. They rewrite
files in place: **commit first, run, then read `git diff`.**

| Script | Mistake → fix |
|---|---|
| `normalize_math.py` | `\( … \)`, `\[ … \]` → `$ … $`, `$$ … $$` |
| `fix_math_spacing.py` | `$ x $` (spaces inside the delimiters; Pandoc prints it as text) → `$x$` |
| `unwrap_math_ltr.py` | `[$x$]{.ltr}` → `$x$` (math is already LTR; the wrapper breaks some expressions in the PDF) |
| `fix_ltr_math.py`, `fix_ltr_brackets.py` | raw LaTeX inside `[…]{.ltr}` (`[\omega_0]{.ltr}`) → math or inline code |
| `fix_paren_ltr.py` | `(term){.ltr}` → `[(term)]{.ltr}` |
| `fix_math_ops.py` | `G_\max` → `G_{\max}` |
| `fix_math_supersub.py` | `$T^*^$` → `$T^{*}$` |
| `fix_isotopes.py` | `$^13C$` → `${}^{13}\mathrm{C}$` |

---

## 5. Copy, paste and search in the PDF

Plain LuaLaTeX output looks right but reads back wrong. In the old version of
this workflow, text copied from the PDF came out with reversed letters, in
"presentation form" code points that no search finds, and without the ZWNJ
(«می‌شود» became «میشود»). [`theme/pdf-copytext.lua`](../theme/pdf-copytext.lua),
loaded by `theme/preamble.tex`, fixes this while the PDF is written:

| Problem in plain LuaLaTeX output | What the module does |
|---|---|
| RTL lines are written in logical order with leftward advances; viewers assume visual order and copy the letters reversed | rebuilds every RTL line in visual order at shipout (links, colours, combining marks and box widths kept) |
| Vazirmatn maps shaped glyphs to Arabic Presentation Forms (U+FBxx/U+FExx), and those went into ToUnicode | rewrites ToUnicode to the letters that were typed |
| ZWNJ never reached the PDF (Pandoc's template turns it into a kern, luaotfload into a space glyph) | `preamble.tex` redefines `\zerowidthnonjoiner` and loads the fonts with `RawFeature={invisible=8204}`, so a real zero-width U+200C glyph is written |
| Diacritics (kasra of ezafe, tanvin, tashdid) were separate text pieces; viewers put a space or a line break beside them | the mark's text rides on a zero-width carrier glyph next to its base letter; its ink is drawn where it was |
| TeX has no space character; viewers guessed spaces from gaps | every inter-word space is a real space glyph plus a kern of the same width |
| Math alphabet letters (U+1D400…) copied as `�` in Chrome | they read back as plain letters, so symbols in formulas are searchable |
| Figure and table caption lines stayed in logical order and copied reversed (the caption colour opens inside the line and closes outside it) | such a line is rebuilt too; `preamble.tex` also spells the label «شکل» with the Persian kaf, so a search for «شکل» finds the captions |

**The page layout does not change**, only the order and labelling of glyphs in
the PDF stream. (One exception: the dot leaders of the table of contents can
shift by less than one dot spacing.)

To check a build:

```bash
python tools/pdf_text_check.py _book/BOOK.pdf --page 3       # text as PyMuPDF and PDFium (Chrome/Edge) extract it
python tools/pdf_text_check.py OLD.pdf NEW.pdf --geometry    # proves two builds place every glyph identically
```

The end of the LaTeX log reports lines the module had to leave in logical
order (`pdf-copytext: … left as is`): lines where a link or colour continues
onto the next line.

**What is not covered:** text inside figures and on the cover (those are
separate PDFs placed as images), and Persian comments inside code blocks.

**What the viewers themselves still get wrong** (not fixable from the PDF side
without breaking another viewer): PDFium (Chrome, Edge, Android) has no full
bidi algorithm, so inside a Persian line it swaps Latin words and
letter/digit groups ("T2" → "2T", "k-space" → "space-k") and breaks the line
at math super/subscripts. pdf.js (Firefox) drops the ZWNJ and puts a space
before a word-final diacritic; search still works there. When you change the
module, test the copied text in the browsers themselves, not only with
PyMuPDF/pypdfium2.

The website and the EPUB never had this problem: their text is ordinary
Unicode HTML.

---

## 6. Before publishing

`build_all.py` already runs the first three checks.

- **epubcheck** passes on both EPUBs with 0 errors and 0 warnings. Apple and
  KDP reject on its errors.
- **Image size.** No image is over 5.6 megapixels (Apple's ITMS-9000 limit).
  `verify_epub.py` checks this for both books.
- **`kindle_audit.py`** passes all checks: the Kindle Publishing Guidelines
  2026.3 rules that no other tool reports.
- **Kindle Previewer:**
  `python tools/build_all.py --skip-render --kindle-previewer` should report
  *Success*, *Enhanced Typesetting: Supported*, 0 errors and 0 quality issues.
  Then open the KPF and look at a few chapters with code and equations.
- **KDP form:** choose **Persian** as the language. A mismatch with
  `<dc:language>fa</dc:language>` is the most common cause of KDP's
  "internal error".
- **Cover:** replace the placeholder texts in `cover/cover.tex` (or the
  artwork altogether) and run `python tools/build_cover.py`.

Why the Kindle edition is a separate file: Amazon's converter did not finish
on the reference book's 39,843 MathML expressions (over two hours of CPU, no
output; KDP answers "We couldn't convert your HTML file to Kindle format"),
and the guidelines do not support Enhanced Typesetting for books with more
than 25 SVG images (11.4.11). `build_kindle_epub.py` therefore turns each
equation into Unicode text where that is faithful (`B₀`, `x²`, `10⁻³`) and
into a PNG rendered with the book's own preamble otherwise, turns figures into
PNG from the PDFs in `diagrams/`, wraps code listings (Kindle never wraps a
`<pre>`), flattens the table of contents to two levels and replaces Pandoc's
SVG cover wrapper with a plain image. A book with little math and few figures
may convert fine from the main EPUB; the Kindle edition is the safe choice
either way.

---

## 7. Pitfalls, learned the hard way

- **Never render one format at a time.** Every `quarto render` first empties
  `_book/`, so `quarto render --to pdf` deletes the website, the EPUBs and the
  Kindle files. Use one `quarto render` (all formats), or `build_all.py`.
- **No global `lang:` in `_quarto.yml`.** It makes Pandoc load
  babel/polyglossia for the PDF, which clashes with `theme/preamble.tex`.
  `lang`/`dir` are set on the `html` and `epub` formats only. The `language:`
  block (Persian labels) is a different thing and is safe.
- **Not `xepersian`, `polyglossia` or the `bidi` package.** `xepersian` breaks
  on `array`/`longtable`, `polyglossia` wants extra fonts, and the `bidi`
  package reverses multi-line Persian in figures. The validated route is
  LuaLaTeX + `babel` with `bidi=basic`, for the body and for the figures.
- **"os error 32 … remove '…\_book'".** Some program has `_book/` open, so
  Quarto cannot replace it. Close Explorer windows showing it, terminals whose
  current folder is inside it, and PDF/EPUB viewers showing a file from it.
  `check_env.py` tests for this.
- **Quarto does not install TeX packages for this project.**
  `_quarto.yml` sets `latex-auto-install: false`, because the auto-installer
  asks for a non-existent `hyphen-persian` and aborts the render. Every
  package must therefore be in `tools/tex-packages.txt`. TeX Live updates
  sometimes split packages: in 2026 `nameref` left `hyperref` and the PDF
  failed with `nameref.sty not found`. Add the new package to the list.
- **Vazirmatn by name.** The PDF's code font falls back to Vazirmatn for
  Persian characters, and that fallback finds the font by name. On a computer
  without Vazirmatn installed in Windows, LuaTeX only sees the repo's copy if
  `OSFONTDIR` points to `fonts/`; otherwise PDF finalisation crashes with
  `cannot find file ''`. `setup_windows.ps1`, `build_all.py`,
  `build_diagrams.py`, `build_cover.py` and `build_kindle_epub.py` handle
  this; for a manual `quarto render`, set `OSFONTDIR` yourself. A TeX update
  can leave the font index stale and cause the same crash on a computer that
  worked the day before: `luaotfload-tool --update --force`.
- **`theme/pdf-copytext.lua` must load before the `\babelfont` lines** in
  `theme/preamble.tex`, so its font hook sees the fonts being loaded. Keep
  `Renderer=Node` and `RawFeature={invisible=8204}` on both `\babelfont`
  lines.
- **Do not add `siunitx` or `bm` to the preamble.** They remap `\mu` and
  break `\boldsymbol\mu`.
- **Interrupted figure builds.** A figure whose build died after LuaLaTeX but
  before the crop keeps a full 3402 pt canvas with the drawing in one corner.
  Its date is newer than the source, so it looks up to date. In the PDF it
  prints as a large near-empty block, and on Kindle it becomes an
  11.6-megapixel image that Apple rejects. `build_all.py` also rebuilds any
  figure whose PDF was never cropped, and `check_diagrams.py` flags it.
- **Mirrored page numbers.** When a page breaks inside a code block, the
  footer was typeset left-to-right-mirrored ("321" on page 123).
  `preamble.tex` sets the page number in an explicit LTR box.
- **Kindle Previewer:**
  - Only **one conversion at a time**; two at once both produce empty output
    with no error.
  - A full conversion of a 2,900-page book takes about 55 minutes.
  - A killed conversion leaves `%TEMP%\kpr_cli_<name>_epub` behind, and every
    later conversion of a file with that name then fails in "Pre-processing"
    within seconds. `verify_epub.py` deletes that folder before converting.
  - Version 3 upgrades itself to 4 (an MSIX app) the first time it starts;
    the commands are then `kindlepreviewer4` / `kpr4`.
- **Persian file names and Java.** On Windows the JVM receives the Persian
  EPUB name as `????`, and epubcheck reports "File not found", which reads
  like a corrupt book. `verify_epub.py` validates an ASCII-named copy, and the
  Kindle edition gets an ASCII name from the start.
- **The Python stub.** `python` can be the Microsoft Store placeholder.
  `check_env.py` flags it; install real Python (§3.1).
- **Code on Kindle.** Kindle supports only `white-space: normal | nowrap`, so
  a `<pre>` never wraps and long lines run off the screen.
  `build_kindle_epub.py` rewrites every listing into wrapping lines, and
  `kindle_audit.py` fails if a long `<pre>` line comes back.
- **A link to a `.qmd` file breaks in the EPUB.**
  `[next chapter](chapters/02-x.qmd)` works on the website, but epubcheck
  rejects it with `RSC-007`. Cross-reference with `@sec-…` instead.
- **Syntax colours for a language Pandoc does not know.** Put a KDE syntax
  definition in `theme/syntax/<lang>.xml`, list it under `syntax-definitions:`
  in `_quarto.yml`, and use its name as the code block's language.
- **Math that the EPUB cannot convert.** Pandoc's MathML converter lacks a few
  commands (`\xleftrightarrow`, `\tbinom`, `\dbinom`);
  `theme/epub-math.lua` rewrites those for EPUB only. If a render logs
  "Could not convert TeX math", add the command there.
- **Downloads answering 403.** Some servers (the Adoptium Java API) reject
  Python's default user agent. `verify_epub.py` sends a generic one.

---

## 8. Git: what is tracked, what is generated

**Tracked (sources):**
- `chapters/`, `appendices/`, `index.qmd`, `outline/`, `glossary/`,
  `templates/`, `references.bib`
- `diagrams/*.tex`, `theme/`, `tools/`, `fonts/`
- `cover/` (`cover.tex`, `cover.pdf`, `cover.png`)
- `_quarto.yml`, `requirements.txt`, `.gitattributes`, `.github/`, `docs/`
- `examples/`: the sample book's outputs, refreshed only by
  `tools/update_examples.py`. Delete it in your own book's repository

**Ignored (generated; safe to delete at any time):**

| Path | Recreated by |
|---|---|
| `_book/`, `_site/` | `build_all.py`. Never un-ignore these: for a large book they total ~400 MB, and a `.kpf` alone can exceed GitHub's 100 MB per-file limit, so the push would be rejected |
| `.quarto/` | Quarto |
| `.kindle-build/` | `build_kindle_epub.py` |
| `.tools/` | `verify_epub.py --install-tools` |
| `diagrams/*.pdf`, `*.svg`, `*.aux`, `*.log`, `*.xdv` | `build_all.py` |
| `__pycache__/`, `.venv/` | Python |
| `smoke-test.pdf`, `smoke-test.html`, `smoke-test_files/` | rendering `smoke-test.qmd` |
| `_*.py`, `_*.txt` | nothing: these are scratch files by convention |
| `.claude/`, `CLAUDE.local.md` | nothing: Claude Code's personal settings for this computer. Never commit them |

**Settings.**
- `.gitattributes` stores every text file with LF line endings. On Windows,
  with Git's default `core.autocrlf=true`, the working copy has CRLF; the
  warning "CRLF will be replaced by LF" is expected and harmless.
- `core.quotepath false` makes `git status` show Persian file names as text.
- `core.longpaths true` avoids Windows' 260-character limit inside `_book/`.

**Commit checklist:**
1. `python tools/build_all.py`. Its last step reports "the build left the git
   working tree as it found it".
2. `git status` shows only the source files you meant to change.
3. Commit and push. CI builds the figures, renders HTML + PDF + EPUB, builds
   the Kindle EPUB, runs epubcheck as a gate and deploys the website. Turn
   this on once under *Settings → Pages → Source: GitHub Actions*.

---

## 9. Moving a book from the old version of this workflow

The old template produced HTML and PDF only, and its PDF text did not copy or
search correctly. To bring an existing book up to date, copy these from the
current template over your book's files, then run `python tools/check_env.py`.

| Copy | Why |
|---|---|
| `theme/preamble.tex`, `theme/pdf-copytext.lua` | copyable/searchable PDF text, ZWNJ, page-number fix. Re-apply your own additions to the preamble |
| `theme/epub.css`, `theme/epub-math.lua` | the EPUB edition |
| `tools/` (the whole folder), `requirements.txt` | the new build, check and Kindle tools; then `pip install -r requirements.txt` |
| `.github/workflows/build.yml`, `.gitattributes`, `.gitignore` | CI for all editions, LF line endings, the new ignored folders |
| `cover/` | the EPUB and Kindle editions need a cover |

Then, in your `_quarto.yml`, add the `project: post-render:` hook, the
`theme/epub-math.lua` filter, `cover-image:`, the `language:` block and the
whole `epub:` format block from the template's `_quarto.yml`. Your figures
need no change. If your chapters wrap math in `[$…$]{.ltr}`, run
`python tools/source-fixes/unwrap_math_ltr.py` (§4.3), and turn file links
between chapters into `@sec-…` references.
