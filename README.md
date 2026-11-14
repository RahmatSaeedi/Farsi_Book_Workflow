# Farsi Technical-Book Workflow

> 🌐 **English** (below) · **[راهنمای فارسی ↓](#farsi-guide)** — همین راهنما به فارسی، در پایینِ فایل.

A ready-to-use **template and build environment** for **Persian/Farsi (right-to-left)
technical and science books** that mix RTL prose with **left-to-right islands** (mathematics,
code, English terms) and carry **vector figures** with Persian labels. One source produces:

| Edition | File | Notes |
|---|---|---|
| Website | `_book/index.html` | deployed to GitHub Pages by CI |
| Print PDF | `_book/<title>.pdf` | Persian text **copies, pastes and searches correctly** |
| EPUB 3 | `_book/<title>.epub` | Apple Books, Google Play Books, Kobo; passes epubcheck |
| Kindle | `_book/<ascii>-kindle.epub` + marketing cover | for Amazon KDP; audited against the Kindle guidelines |

Everything here was distilled from, and validated on, a 2,900-page, 228-figure Farsi
engineering book. Copy this folder, drop in your content, and you have a working book in
*any* technical subject.

**See the result first:** [`examples/`](examples/) holds the built sample book (PDF, EPUB,
Kindle edition, cover, page previews).

**Full toolchain and build guide: [`docs/BUILD.md`](docs/BUILD.md)**
(فارسی: [`docs/BUILD.fa.md`](docs/BUILD.fa.md)). This README is the overview and the
authoring guide.

---

## Quick start

On a new Windows computer, after installing Git and getting your copy of this folder, one
command installs every tool (it skips what is already there, and is safe to re-run):

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup_windows.ps1 -GitName "Your Name" -GitEmail "you@example.com"
# then, in a NEW PowerShell window:
python tools\check_env.py      # every row should be OK
python tools\build_all.py      # every edition + all checks -> _book\   (about 1 minute for the sample)
```

Linux and macOS: the same steps by hand, in [`docs/BUILD.md` §3.3](docs/BUILD.md#33-linux-and-macos).

Then open `_book/index.html` and the PDF. Persian must flow right-to-left in Vazirmatn;
math, code and English must be left-to-right and not mirrored; the figure must be sharp.
Select a Persian sentence in the PDF, copy it and paste it into a text editor: it must come
out as the sentence you see.

While writing, use `quarto preview` for a live HTML preview. **Do not render one format at a
time** (`quarto render --to pdf`): every render empties `_book/` first. Use
`python tools/build_all.py`.

---

## The validated stack

| Concern | Choice | Why (and what failed) |
|---|---|---|
| Publishing engine | **Quarto** 1.11 (`.qmd` → HTML + PDF + EPUB) | one source, citations, cross-references |
| PDF / bidi | **LuaLaTeX + `babel` `bidi=basic`** | robust with `array`/`longtable`. **`xepersian`** breaks on tables; **`polyglossia`** wants extra fonts; the standalone **`bidi`** package mis-orders multi-line nodes |
| Copy/search in the PDF | **`theme/pdf-copytext.lua`** | plain LuaLaTeX output copies Persian reversed, as presentation-form code points, without ZWNJ |
| Body font | **Vazirmatn**, loaded by file from `fonts/` | free, good Persian + Latin; no system install |
| Figures | **LuaLaTeX + babel → PyMuPDF crop → PDF + SVG** | **XeLaTeX + `bidi` + `dvisvgm`** reversed multi-line RTL, and its SVGs were re-mirrored by browsers |
| Persian in HTML math | **MathJax `mtextInheritFont`** | otherwise `\text{...}` shows disconnected Persian |
| EPUB | Pandoc EPUB 3, MathML, embedded Vazirmatn, **`tools/fix_epub.py`** | Pandoc's EPUB writer leaves errors that Apple and KDP reject |
| Kindle | **`tools/build_kindle_epub.py`** | Amazon's converter does not cope with a math-heavy book's MathML or more than 25 SVGs |
| Validation | **epubcheck**, `kindle_audit.py`, Kindle Previewer | the same checks the stores run, before you upload |

Tested versions (Quarto 1.11.9, TeX Live 2026, Python 3.14, Java 25, epubcheck 5.4.0, …)
and how each is installed: [`docs/BUILD.md` §3](docs/BUILD.md#3-the-toolchain).

---

## Project structure

```text
.
├── _quarto.yml                 # book config: title, chapter list, formats   — EDIT THIS
├── index.qmd                   # preface / first page
├── chapters/                   # one .qmd per chapter
│   └── 01-sample-chapter.qmd   # demonstrates every authoring convention
├── references.bib              # BibTeX bibliography
├── cover/                      # cover.tex -> cover.pdf (print) + cover.png (web, EPUB)
├── diagrams/                   # TikZ figures: figure-template.tex, sample-figure.tex, Makefile
├── outline/chapters.yml        # optional: book structure for tools/gen_stubs.py
├── templates/, glossary/       # chapter template; writing conventions + fa–en term list
├── theme/
│   ├── preamble.tex            # LuaLaTeX + babel bidi=basic + Vazirmatn (PDF)
│   ├── pdf-copytext.lua        # ★ makes the PDF's Persian text copy/search correctly
│   ├── ltr.lua                 # Pandoc filter: [..]{.ltr} islands -> correct per format
│   ├── epub.css, epub-math.lua # EPUB: RTL + embedded font; math commands MathML lacks
│   └── custom.scss, mathjax-config.html   # website
├── tools/
│   ├── setup_windows.ps1       # ★ installs the whole toolchain on a new Windows computer
│   ├── check_env.py            # ★ what is installed, and the fix for what is not
│   ├── build_all.py            # ★ every edition, in the right order, with all checks
│   ├── build_diagrams.py       # figures: LuaLaTeX -> PyMuPDF crop -> PDF + SVG
│   ├── new_figure.py, check_diagrams.py, build_cover.py, gen_stubs.py
│   ├── fix_epub.py, build_kindle_epub.py, kindle_math.py, make_kindle_cover.py
│   ├── verify_epub.py, kindle_audit.py, pdf_text_check.py, pdf_to_png.py
│   ├── source-fixes/           # optional repairs for common markup mistakes
│   └── tex-packages.txt        # the TeX package list (setup, check and CI share it)
├── fonts/                      # Vazirmatn .ttf + OFL license
├── docs/BUILD.md, BUILD.fa.md  # ★ toolchain, build workflow, pitfalls, git
├── examples/                   # ★ the built sample book: what the workflow produces
├── smoke-test.qmd              # one-page toolchain test
└── .github/workflows/build.yml # CI: build, validate, deploy to GitHub Pages
```

What each tool does: [`docs/BUILD.md` §3.4](docs/BUILD.md#34-every-tool-in-tools).

---

## Starting your own book

1. Edit `_quarto.yml`: `title`, `subtitle`, `author`.
2. Edit the three text lines in `cover/cover.tex` (or replace the artwork), run
   `python tools/build_cover.py`, and commit `cover.pdf` and `cover.png`.
3. Replace `index.qmd` and `chapters/01-sample-chapter.qmd` with your content. Keep the
   sample around as a cheat-sheet until the conventions are familiar. New chapters can
   start from `templates/chapter-template.qmd`.
4. List your chapters. Either:
   - **by hand** in `_quarto.yml` under `book: chapters:` (then delete `outline/` and the two
     marker comments), or
   - **from an outline**: describe the book in `outline/chapters.yml` and run
     `python tools/gen_stubs.py`. It creates a stub for every chapter that has no file yet
     and rewrites only the chapter list between the marker comments in `_quarto.yml`.
     Recommended for a book with parts and dozens of chapters.
5. Add figures under `diagrams/` and references to `references.bib`.
6. Delete `examples/` (the sample book's committed outputs).
7. Nothing in `theme/`, `tools/` or `fonts/` is subject-specific. If a chapter needs another
   LaTeX package, add it to `theme/preamble.tex` **and** to `tools/tex-packages.txt`.

---

## Mixing RTL prose with LTR islands

In `.qmd` prose, Persian is the base direction. Wrap an English term, an acronym or a Latin
number with its unit in an **LTR island** so it is not mirrored:

```markdown
گذرگاهِ [DC]{.ltr} باید دستِ‌کم [2000 V]{.ltr} فراهم کند، یعنی $V_\text{dc} \ge 2000$.

::: {.ltr}
A whole left-to-right paragraph or an ASCII diagram goes in a div.
:::
```

- `theme/ltr.lua` maps `[..]{.ltr}` / `::: {.ltr}` to `dir="ltr"` (HTML, EPUB) and
  `\babelsublr{..}` / `\begin{otherlanguage}{english}` (PDF).
- **Math** (`$...$`, `$$...$$`) and **code** are left-to-right by themselves. Do **not** wrap
  math in a span: `[$x$]{.ltr}` is redundant and breaks the PDF build for some expressions.
  Do not put raw LaTeX in a span either (`[\omega_0]{.ltr}`): make it math.
- No space just inside the dollar signs: `$x+y$`, not `$ x+y $`.
- Refer to chapters, sections, figures, tables and equations with `@sec-…`, `@fig-…`,
  `@tbl-…`, `@eq-…`. A link to a `.qmd` file breaks in the EPUB.
- Labels that Quarto generates ("شکل 1.1", "جدول", "فهرست", callout titles) are Persian in
  every format through the `language:` block in `_quarto.yml`.
- **Do not set a global `lang:`** in `_quarto.yml`: it makes Pandoc load babel/polyglossia
  for the PDF and clash with `preamble.tex`. `lang`/`dir` belong on the `html` and `epub`
  formats only.

The complete conventions (terminology, digits, units, citations) are in
[`glossary/conventions.md`](glossary/conventions.md).

---

## The figure pipeline (read this before drawing)

Figures carry Persian labels mixed with LTR math and English. The naive route (XeLaTeX +
`standalone` + the `bidi` package, then `dvisvgm`) **silently reverses multi-line Persian**:
the first line of a `text width` box, and the whole of an `align` box, come out
left-to-right. The error is in the PDF layout, so it is not a viewer bug.

What `diagrams/figure-template.tex` and `tools/build_diagrams.py` do instead:

1. Compile each figure with **LuaLaTeX + babel `bidi=basic`**, the same engine as the book
   body.
2. Load the font with `\babelfont{rm}[Renderer=Node, Path=../fonts/, …]{Vazirmatn}` (and
   `{sf}`). **`Renderer=Node` is mandatory**: LuaHBTeX's default HarfBuzz renderer has a
   Persian-shaping assertion bug.
3. Use `\documentclass{article}` on a huge `geometry` page, and wrap the **whole**
   `tikzpicture` in **`\babelsublr{...}`**. Without it the RTL page mirrors the geometry (a
   node at x=6 lands on the left); with it the geometry is LTR while node text is still RTL.
4. **PyMuPDF** crops the page to its content, measured on rendered pixels, and writes a
   tight `<name>.pdf` and a `<name>.svg` with outlined glyphs (no `<text>`, so browsers
   cannot re-order it).

### Add a figure

```bash
python tools/new_figure.py 02-my-diagram        # copies figure-template.tex -> diagrams/02-my-diagram.tex
# ...draw inside diagrams/02-my-diagram.tex...
python tools/build_diagrams.py 02-my-diagram    # -> 02-my-diagram.pdf + .svg
```

Reference it from a chapter with one include per format. The SVG branch also serves the
EPUB, and the Kindle edition takes its PNG from the PDF:

```markdown
::: {.content-visible when-format="html"}
![عنوانِ شکل](../diagrams/02-my-diagram.svg){#fig-mine width=70%}
:::
::: {.content-visible when-format="pdf"}
![عنوانِ شکل](../diagrams/02-my-diagram.pdf){#fig-mine width=70%}
:::
```

`python tools/build_all.py` rebuilds only the figures whose `.tex` changed. The built
PDF/SVG files are git-ignored.

### Figure authoring tips (inside a `.tex`)

- Persian node text just works: no `\setRTL`, no `\RL`, no `Script=Arabic`.
- English and math are LTR automatically; write them plainly. Do **not** use `[..]{.ltr}`
  inside a `.tex` (that is Pandoc markdown, not LaTeX).
- Inline math with a binary relation (`$Y=HX$`) inside an RTL node can render with loose
  gaps. Wrap it: `\mbox{$Y=HX$}` (see `sample-figure.tex`).
- `python tools/check_diagrams.py` flags figures that came out blank or uncropped.

---

## Copy, paste and search in the PDF

This was the main defect of the earlier version of this workflow, and it is fixed in the
PDF itself by `theme/pdf-copytext.lua`: lines are written in visual order, the fonts map to
real letters instead of presentation forms, the ZWNJ («می‌شود») survives, diacritics stay
attached to their letters, spaces are real spaces, and figure and table captions are
included. The page layout does not change.

```bash
python tools/pdf_text_check.py _book/BOOK.pdf --page 3     # what PyMuPDF and PDFium (Chrome/Edge) copy out
```

Known limits, all on the viewer side: Chrome/Edge swap Latin words and digit groups inside a
Persian line ("T2" → "2T"), and Firefox drops the ZWNJ when copying (search still works).
Text inside figures and on the cover, and Persian comments in code blocks, are not covered. Details and the
full list: [`docs/BUILD.md` §5](docs/BUILD.md#5-copy-paste-and-search-in-the-pdf).

---

## Verification (do not trust your eyes on RTL)

- `python tools/build_all.py` ends with epubcheck on both EPUBs, Apple's image-size limit,
  the Kindle guideline audit, and a report of anything the build changed in git.
- `python tools/build_all.py --skip-render --kindle-previewer` adds Amazon's own conversion
  (needs Kindle Previewer; optional).
- `smoke-test.qmd` exercises RTL + math + code + figure + table on one page; render it
  alone to tell a toolchain problem from a content problem.
- Is a figure's Persian in the right order? Extract word coordinates instead of squinting:
  ```python
  import pymupdf
  ws = pymupdf.open("diagrams/NN.pdf")[0].get_text("words")  # (x0, y0, x1, y1, word, ...)
  # in an RTL line the FIRST logical word must have the LARGEST x (rightmost)
  ```
  The Windows console cannot print Persian; write results to a UTF-8 file and read that.
- `python tools/pdf_to_png.py file.pdf out` rasterises any PDF page for a quick look.

---

## Deploy

`.github/workflows/build.yml` builds the figures, renders HTML + PDF + EPUB, builds the
Kindle EPUB, runs epubcheck as a gate and deploys the site to **GitHub Pages** on every push
to `main`. To enable it, push the repository and set *Settings → Pages → Source* to
**GitHub Actions**.

---

## What changed from the first version of this template

| Before | Now |
|---|---|
| HTML + PDF | HTML + PDF + EPUB 3 + Kindle edition + Kindle cover |
| Persian copied from the PDF came out reversed, in presentation forms, without ZWNJ | `theme/pdf-copytext.lua`; checked with `tools/pdf_text_check.py` |
| "Figure 1.1", "Table of contents" in English | Persian labels in every format |
| manual install from a prerequisites list | `tools/setup_windows.ps1`, `tools/check_env.py`, one package list for setup and CI |
| `quarto render` per format (each one deleting the others' output) | `tools/build_all.py` |
| no validation | epubcheck, Apple image limit, Kindle audit, Kindle Previewer |
| mirrored page numbers on pages that break inside a code block | fixed in `theme/preamble.tex` |

Moving an existing book to this version: [`docs/BUILD.md` §9](docs/BUILD.md#9-moving-a-book-from-the-old-version-of-this-workflow).

---
---

<a id="farsi-guide"></a>

# گردش‌کارِ کتابِ علمی-فنیِ فارسی

> 🌐 **[English ↑](#farsi-technical-book-workflow)** · این بخش همان راهنمای بالاست، به فارسی.

یک **قالب و محیطِ ساختِ آماده** برای **کتاب‌های علمی-فنیِ فارسی (راست‌به‌چپ)** که نثرِ
راست‌به‌چپ را با **جزیره‌های چپ‌به‌راست** (ریاضی، کد، اصطلاحِ انگلیسی) می‌آمیزند و **نمودارهای
برداری** با برچسبِ فارسی دارند. از یک منبع، این نسخه‌ها ساخته می‌شود:

| نسخه | فایل | توضیح |
|---|---|---|
| وب‌سایت | `_book/index.html` | CI آن را روی GitHub Pages منتشر می‌کند |
| PDFِ چاپی | `_book/<عنوان>.pdf` | متنِ فارسی **درست کپی، چسبانده و جست‌وجو می‌شود** |
| EPUB 3 | `_book/<عنوان>.epub` | Apple Books، Google Play Books، Kobo؛ epubcheck را می‌گذراند |
| کیندل | `_book/<ascii>-kindle.epub` و جلدِ تبلیغاتی | برای Amazon KDP؛ با راهنمای کیندل ممیزی می‌شود |

همه‌چیزِ این قالب از یک کتابِ مهندسیِ فارسیِ ۲٬۹۰۰ صفحه‌ای با ۲۲۸ نمودار گرفته و روی همان
آزموده شده است. این پوشه را کپی کنید، محتوای خود را بگذارید و در **هر** موضوعِ فنی یک کتابِ
کارکن دارید.

**نخست نتیجه را ببینید:** پوشهٔ [`examples/`](examples/) کتابِ نمونهٔ ساخته‌شده را دارد (PDF،
EPUB، نسخهٔ کیندل، جلد و پیش‌نمایشِ صفحه‌ها).

**راهنمای کاملِ زنجیرهٔ ابزار و ساخت: [`docs/BUILD.fa.md`](docs/BUILD.fa.md)**
(انگلیسی: [`docs/BUILD.md`](docs/BUILD.md)). این فایل، مرور و راهنمای نگارش است.

## شروعِ سریع

روی یک رایانهٔ ویندوزیِ تازه، پس از نصبِ گیت و گرفتنِ نسخهٔ خودتان از این پوشه، یک فرمان همهٔ
ابزارها را نصب می‌کند (هر چه نصب باشد رد می‌شود و اجرای دوباره بی‌خطر است):

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup_windows.ps1 -GitName "Your Name" -GitEmail "you@example.com"
# سپس در یک پنجرهٔ PowerShellِ تازه:
python tools\check_env.py      # همهٔ سطرها باید OK باشند
python tools\build_all.py      # همهٔ نسخه‌ها و همهٔ بررسی‌ها -> _book\   (برای کتابِ نمونه حدودِ یک دقیقه)
```

لینوکس و مک: همان گام‌ها به‌صورتِ دستی، در [بخشِ ۳٫۳ِ `docs/BUILD.fa.md`](docs/BUILD.fa.md).

سپس `_book/index.html` و PDF را باز کنید. فارسی باید راست‌به‌چپ و با Vazirmatn باشد؛ ریاضی،
کد و انگلیسی چپ‌به‌راست و بدونِ آینه‌شدن؛ و نمودار تیز. یک جملهٔ فارسی را در PDF انتخاب و کپی
کنید و در یک ویرایشگرِ متن بچسبانید: باید همان جمله‌ای باشد که می‌بینید.

هنگامِ نوشتن، `quarto preview` پیش‌نمایشِ زندهٔ HTML می‌دهد. **قالب‌ها را تک‌تک رِندر نکنید**
(`quarto render --to pdf`): هر رِندر نخست `_book/` را خالی می‌کند. از
`python tools/build_all.py` استفاده کنید.

## پشتهٔ آزموده‌شده

| دغدغه | انتخاب | چرا (و چه چیزی شکست خورد) |
|---|---|---|
| موتورِ انتشار | **Quarto** 1.11 (‏`.qmd` ← HTML + PDF + EPUB) | یک منبع، استناد و ارجاعِ متقابل |
| PDF / دوسویه | **LuaLaTeX + `babel` با `bidi=basic`** | با `array`/`longtable` پایدار است. **`xepersian`** روی جدول‌ها می‌شکند؛ **`polyglossia`** فونتِ اضافی می‌خواهد؛ بستهٔ مستقلِ **`bidi`** گره‌های چندخطی را بد می‌چیند |
| کپی/جست‌وجو در PDF | **`theme/pdf-copytext.lua`** | خروجیِ خامِ LuaLaTeX فارسی را وارونه، با کدهای «شکلِ نمایشی» و بدونِ نیم‌فاصله کپی می‌کند |
| فونتِ بدنه | **Vazirmatn**، از پوشهٔ `fonts/` | آزاد، پوششِ خوبِ فارسی و لاتین؛ بدونِ نصبِ سیستمی |
| نمودارها | **LuaLaTeX + babel ← برشِ PyMuPDF ← PDF و SVG** | **XeLaTeX + `bidi` + `dvisvgm`** متنِ چندخطی را وارونه می‌کرد و SVGهایش در مرورگر آینه می‌شد |
| فارسی درونِ ریاضیِ HTML | **‏`mtextInheritFont` در MathJax** | وگرنه `\text{...}` فارسیِ گسسته نشان می‌دهد |
| EPUB | ‏EPUB 3ِ Pandoc، MathML، Vazirmatnِ نهفته، **`tools/fix_epub.py`** | نویسندهٔ EPUBِ Pandoc خطاهایی به‌جا می‌گذارد که اپل و KDP رد می‌کنند |
| کیندل | **`tools/build_kindle_epub.py`** | مبدلِ آمازون از پسِ MathMLِ یک کتابِ پرریاضی یا بیش از ۲۵ SVG برنمی‌آید |
| اعتبارسنجی | **epubcheck**، `kindle_audit.py`، Kindle Previewer | همان بررسی‌های فروشگاه‌ها، پیش از بارگذاری |

نسخه‌های آزموده (Quarto 1.11.9، TeX Live 2026، Python 3.14، Java 25، epubcheck 5.4.0 و …) و
شیوهٔ نصبِ هر کدام: [بخشِ ۳ِ `docs/BUILD.fa.md`](docs/BUILD.fa.md).

## ساختارِ پروژه

همان درختی است که در بخشِ انگلیسی (*Project structure*) آمده. مهم‌ترین‌ها:

- `_quarto.yml` — پیکربندیِ کتاب (عنوان، فهرستِ فصل‌ها، قالب‌ها)؛ **این را ویرایش کنید**.
- `index.qmd`، `chapters/`، `references.bib` — محتوا.
- `cover/` — جلد: `cover.tex` ← `cover.pdf` (چاپ) و `cover.png` (وب و EPUB).
- `diagrams/` — نمودارهای TikZ (`figure-template.tex`، `sample-figure.tex`).
- `outline/chapters.yml` — اختیاری: ساختارِ کتاب برای `tools/gen_stubs.py`.
- `templates/`، `glossary/` — الگوی فصل؛ قراردادهای نگارش و واژه‌نامهٔ فا–en.
- `theme/` — `preamble.tex` (PDF)، **`pdf-copytext.lua`** (کپی/جست‌وجوی PDF)، `ltr.lua`
  (جزیره‌های چپ‌به‌راست)، `epub.css` و `epub-math.lua` (EPUB)، `custom.scss` و
  `mathjax-config.html` (وب).
- `tools/` — **`setup_windows.ps1`** (نصبِ همهٔ ابزارها)، **`check_env.py`** (بررسیِ محیط)،
  **`build_all.py`** (ساختِ همهٔ نسخه‌ها با بررسی‌ها) و ابزارهای نمودار، جلد، EPUB، کیندل و
  اعتبارسنجی. کارِ هر کدام: بخشِ ۳٫۴ِ [`docs/BUILD.fa.md`](docs/BUILD.fa.md).
- `docs/BUILD.fa.md`، `docs/BUILD.md` — زنجیرهٔ ابزار، گردشِ کارِ ساخت، تله‌ها و گیت.
- `examples/` — کتابِ نمونهٔ ساخته‌شده: آنچه این گردشِ‌کار تولید می‌کند.
- `smoke-test.qmd` — آزمونِ یک‌صفحه‌ایِ زنجیرهٔ ابزار.
- `.github/workflows/build.yml` — CI: ساخت، اعتبارسنجی و انتشار روی GitHub Pages.

## آغازِ کتابِ خودتان

۱. در `_quarto.yml` مقدارهای `title`، `subtitle` و `author` را بنویسید.
۲. سه سطرِ متن را در `cover/cover.tex` عوض کنید (یا طرحِ خودتان را بگذارید)،
   `python tools/build_cover.py` را اجرا کنید و `cover.pdf` و `cover.png` را commit کنید.
۳. `index.qmd` و `chapters/01-sample-chapter.qmd` را با محتوای خود جایگزین کنید. فصلِ نمونه
   را تا آشنا شدن با قراردادها به‌عنوانِ برگهٔ راهنما نگه دارید. فصلِ تازه می‌تواند از
   `templates/chapter-template.qmd` آغاز شود.
۴. فصل‌ها را فهرست کنید. یا **دستی** در `_quarto.yml` زیرِ `book: chapters:` (در این صورت
   `outline/` و دو سطرِ نشانگر را پاک کنید)، یا **از روی سرفصل**: کتاب را در
   `outline/chapters.yml` توصیف و `python tools/gen_stubs.py` را اجرا کنید. این ابزار برای هر
   فصلی که فایل ندارد اسکلت می‌سازد و فقط فهرستِ میانِ دو نشانگر را در `_quarto.yml` بازنویسی
   می‌کند. برای کتابِ چندبخشی با ده‌ها فصل، راهِ دوم بهتر است.
۵. نمودارها را زیرِ `diagrams/` و منابع را در `references.bib` بیفزایید.
۶. پوشهٔ `examples/` را پاک کنید (خروجی‌های commitشدهٔ کتابِ نمونه).
۷. هیچ‌چیز در `theme/`، `tools/` و `fonts/` وابسته به موضوع نیست. اگر فصلی بستهٔ LaTeXِ
   دیگری می‌خواهد، آن را هم به `theme/preamble.tex` و هم به `tools/tex-packages.txt`
   بیفزایید.

## آمیختنِ نثرِ راست‌به‌چپ با جزیره‌های چپ‌به‌راست

در نثرِ `.qmd` جهتِ پایه فارسی است. اصطلاحِ انگلیسی، سرواژه یا عددِ لاتین با یکایش را در یک
«جزیرهٔ چپ‌به‌راست» بپیچید تا آینه نشود:

```markdown
گذرگاهِ [DC]{.ltr} باید دستِ‌کم [2000 V]{.ltr} فراهم کند، یعنی $V_\text{dc} \ge 2000$.

::: {.ltr}
A whole left-to-right paragraph or an ASCII diagram goes in a div.
:::
```

- `theme/ltr.lua` نشانِ `[..]{.ltr}` و `::: {.ltr}` را به `dir="ltr"` (در HTML و EPUB) و
  `\babelsublr{..}` / `\begin{otherlanguage}{english}` (در PDF) نگاشت می‌کند.
- **ریاضی** (`$...$`، `$$...$$`) و **کد** خودشان چپ‌به‌راست‌اند. ریاضی را در اسپن **نپیچید**:
  `[$x$]{.ltr}` زائد است و برای برخی عبارت‌ها ساختِ PDF را می‌شکند. لاتکِ خام هم درونِ اسپن
  ننویسید (`[\omega_0]{.ltr}`): آن را ریاضی کنید.
- درست پس از `$`ِ آغاز و پیش از `$`ِ پایان فاصله نگذارید: `$x+y$`، نه `$ x+y $`.
- برای ارجاع به فصل، بخش، شکل، جدول و معادله از `@sec-…`، `@fig-…`، `@tbl-…` و `@eq-…`
  استفاده کنید. پیوند به فایلِ `.qmd` در EPUB می‌شکند.
- برچسب‌هایی که Quarto می‌سازد («شکل 1.1»، «جدول»، «فهرست»، عنوانِ کادرها) با بلوکِ
  `language:` در `_quarto.yml` در همهٔ قالب‌ها فارسی‌اند.
- **`lang:`ِ سراسری نگذارید:** Pandoc را وادار می‌کند برای PDF بسته‌های babel/polyglossia را
  بار کند و با `preamble.tex` تداخل کند. `lang`/`dir` فقط روی قالب‌های `html` و `epub`.

قراردادهای کامل (اصطلاح‌شناسی، ارقام، یکاها، استناد) در
[`glossary/conventions.md`](glossary/conventions.md) است.

## خط‌لولهٔ نمودار (پیش از کشیدن بخوانید)

نمودارها برچسبِ فارسی را با ریاضی و انگلیسیِ چپ‌به‌راست می‌آمیزند. مسیرِ ساده (XeLaTeX +
`standalone` + بستهٔ `bidi` و سپس `dvisvgm`) **متنِ چندخطیِ فارسی را بی‌سروصدا وارونه
می‌کند**: سطرِ اولِ گره‌های `text width` و کلِ گره‌های `align` چپ‌به‌راست درمی‌آیند. خطا در
چیدمانِ PDF است، نه در نمایشگر.

کاری که `diagrams/figure-template.tex` و `tools/build_diagrams.py` به‌جای آن می‌کنند:

۱. هر نمودار با **LuaLaTeX + babel با `bidi=basic`** کامپایل می‌شود؛ همان موتورِ بدنهٔ کتاب.
۲. فونت با `\babelfont{rm}[Renderer=Node, Path=../fonts/, …]{Vazirmatn}` (و `{sf}`) بار
   می‌شود. **`Renderer=Node` الزامی است:** رِندررِ پیش‌فرضِ HarfBuzz در LuaHBTeX یک باگِ
   شکل‌دهیِ فارسی دارد.
۳. `\documentclass{article}` روی یک صفحهٔ بزرگِ `geometry`، و **کلِ** `tikzpicture` درونِ
   **`\babelsublr{...}`**. بدونِ آن، صفحهٔ راست‌به‌چپ هندسه را آینه می‌کند (گرهی در x=۶ به چپ
   می‌افتد)؛ با آن، هندسه چپ‌به‌راست می‌ماند و متنِ گره‌ها راست‌به‌چپ.
۴. **PyMuPDF** صفحه را بر پایهٔ پیکسل‌های رِندرشده به اندازهٔ محتوا می‌بُرد و یک `<name>.pdf`ِ
   تنگ و یک `<name>.svg` با گلیف‌های مسیرشده می‌نویسد (بدونِ `<text>`، پس مرورگر نمی‌تواند
   ترتیبش را به‌هم بزند).

### افزودنِ یک نمودار

```bash
python tools/new_figure.py 02-my-diagram        # figure-template.tex را به diagrams/02-my-diagram.tex کپی می‌کند
# ...درونِ diagrams/02-my-diagram.tex بکشید...
python tools/build_diagrams.py 02-my-diagram    # -> 02-my-diagram.pdf + .svg
```

در فصل، برای هر قالب یک درج بگذارید. شاخهٔ SVG به EPUB هم می‌رسد و نسخهٔ کیندل PNGِ خود را از
PDF می‌گیرد:

```markdown
::: {.content-visible when-format="html"}
![عنوانِ شکل](../diagrams/02-my-diagram.svg){#fig-mine width=70%}
:::
::: {.content-visible when-format="pdf"}
![عنوانِ شکل](../diagrams/02-my-diagram.pdf){#fig-mine width=70%}
:::
```

`python tools/build_all.py` فقط نمودارهایی را می‌سازد که `.tex`شان عوض شده است. PDF/SVGِ
ساخته‌شده در گیت نادیده گرفته می‌شود.

### نکته‌های نگارشِ نمودار (درونِ `.tex`)

- متنِ فارسیِ گره همین‌طور کار می‌کند: بدونِ `\setRTL`، `\RL` یا `Script=Arabic`.
- انگلیسی و ریاضی خودکار چپ‌به‌راست‌اند؛ ساده بنویسیدشان. درونِ `.tex` از `[..]{.ltr}`
  استفاده **نکنید** (آن نشانه‌گذاریِ Pandoc است، نه LaTeX).
- ریاضیِ درون‌خطیِ دارای رابطهٔ دوتایی (`$Y=HX$`) درونِ گرهِ راست‌به‌چپ ممکن است با فاصلهٔ باز
  رِندر شود. بپیچیدش: `\mbox{$Y=HX$}` (نمونه در `sample-figure.tex`).
- `python tools/check_diagrams.py` نمودارهایی را که سفید یا بریده‌نشده درآمده‌اند نشان می‌دهد.

## کپی، چسباندن و جست‌وجو در PDF

این عیبِ اصلیِ نسخهٔ پیشینِ این گردشِ‌کار بود و اکنون در خودِ PDF با `theme/pdf-copytext.lua`
رفع شده است: سطرها به ترتیبِ دیداری نوشته می‌شوند، فونت‌ها به حروفِ واقعی (نه «شکل‌های
نمایشی») نگاشت می‌شوند، نیم‌فاصله («می‌شود») می‌ماند، اِعراب به حرفِ خود چسبیده می‌ماند،
فاصله‌ها نویسهٔ واقعی‌اند، و زیرنویسِ شکل‌ها و جدول‌ها هم پوشش داده می‌شود. چیدمانِ صفحه
تغییر نمی‌کند.

```bash
python tools/pdf_text_check.py _book/BOOK.pdf --page 3     # آنچه PyMuPDF و PDFium (Chrome/Edge) کپی می‌کنند
```

محدودیت‌های شناخته‌شده، همه از سمتِ نمایشگر: Chrome و Edge درونِ سطرِ فارسی ترتیبِ واژه‌های
لاتین و گروه‌های رقم را جابه‌جا می‌کنند («T2» ← «2T») و Firefox هنگامِ کپی نیم‌فاصله را
می‌اندازد (جست‌وجو کار می‌کند). متنِ درونِ نمودارها و روی جلد و کامنتِ فارسیِ درونِ
بلوکِ کد پوشش داده نمی‌شود. جزئیات: بخشِ ۵ِ [`docs/BUILD.fa.md`](docs/BUILD.fa.md).

## راستی‌آزمایی (روی راست‌به‌چپ به چشم اعتماد نکنید)

- `python tools/build_all.py` با epubcheck روی هر دو EPUB، سقفِ اندازهٔ تصویرِ اپل، ممیزیِ
  راهنمای کیندل و گزارشِ هر تغییری که ساخت در گیت داده پایان می‌یابد.
- `python tools/build_all.py --skip-render --kindle-previewer` تبدیلِ خودِ آمازون را هم
  می‌افزاید (Kindle Previewer می‌خواهد؛ اختیاری).
- `smoke-test.qmd` راست‌به‌چپ + ریاضی + کد + نمودار + جدول را در یک صفحه می‌سنجد؛ برای
  جداکردنِ مشکلِ زنجیرهٔ ابزار از مشکلِ محتوا، آن را جداگانه رِندر کنید.
- آیا ترتیبِ فارسیِ یک نمودار درست است؟ به‌جای خیره‌شدن، مختصاتِ واژه‌ها را بگیرید:
  ```python
  import pymupdf
  ws = pymupdf.open("diagrams/NN.pdf")[0].get_text("words")  # (x0, y0, x1, y1, word, ...)
  # در سطرِ راست‌به‌چپ، نخستین واژهٔ منطقی باید بزرگ‌ترین x را داشته باشد (راست‌ترین)
  ```
  کنسولِ ویندوز فارسی چاپ نمی‌کند؛ نتیجه را در یک فایلِ UTF-8 بنویسید و آن را بخوانید.
- `python tools/pdf_to_png.py file.pdf out` هر صفحهٔ PDF را برای نگاهِ سریع رِستر می‌کند.

## استقرار

`.github/workflows/build.yml` در هر push به `main` نمودارها را می‌سازد، HTML و PDF و EPUB را
رِندر می‌کند، EPUBِ کیندل را می‌سازد، epubcheck را به‌عنوانِ دروازه اجرا می‌کند و سایت را روی
**GitHub Pages** منتشر می‌کند. برای فعال‌سازی، مخزن را push کنید و در
*Settings → Pages → Source* گزینهٔ **GitHub Actions** را بگذارید.

## چه چیزی نسبت به نسخهٔ نخستِ این قالب عوض شده

| پیش‌تر | اکنون |
|---|---|
| HTML و PDF | HTML، PDF، EPUB 3، نسخهٔ کیندل و جلدِ کیندل |
| فارسیِ کپی‌شده از PDF وارونه، با «شکل‌های نمایشی» و بدونِ نیم‌فاصله بود | `theme/pdf-copytext.lua`؛ سنجش با `tools/pdf_text_check.py` |
| «Figure 1.1» و «Table of contents» به انگلیسی | برچسبِ فارسی در همهٔ قالب‌ها |
| نصبِ دستی از روی فهرستِ پیش‌نیازها | `tools/setup_windows.ps1`، `tools/check_env.py` و یک فهرستِ بستهٔ مشترک برای نصب و CI |
| `quarto render` جدا برای هر قالب (که خروجیِ بقیه را پاک می‌کرد) | `tools/build_all.py` |
| بدونِ اعتبارسنجی | epubcheck، سقفِ تصویرِ اپل، ممیزیِ کیندل، Kindle Previewer |
| شمارهٔ صفحهٔ آینه‌شده در صفحه‌هایی که درونِ بلوکِ کد می‌شکنند | در `theme/preamble.tex` رفع شده |

انتقالِ یک کتابِ موجود به این نسخه: بخشِ ۹ِ [`docs/BUILD.fa.md`](docs/BUILD.fa.md).
