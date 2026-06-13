# Farsi Technical-Book Workflow

> 🌐 **English** (below) · **[راهنمای فارسی ↓](#farsi-guide)** — همین راهنما به فارسی، در پایینِ فایل.

A ready-to-use **template and environment** for authoring **Persian/Farsi (right-to-left)
technical & science books** that freely mix RTL prose with **left-to-right islands** —
mathematics, code, and English terms — and that produce **vector figures** with Persian
labels. It renders to a **website (HTML)** and a **print-ready PDF** from a single source.

This template distills a toolchain that was validated the hard way on a large (2900-page,
228-figure) Farsi engineering book. **Everything here is tested and works together.** Copy this
folder, drop in your content, and you have a working book — in *any* technical subject, not just
the one the sample uses.

> The single biggest lesson, if you read nothing else: **build figures with LuaLaTeX + babel
> `bidi=basic` (the same engine as the book body), wrap each picture in `\babelsublr`, and crop
> with PyMuPDF.** The "obvious" route (XeLaTeX + the `bidi` package → `dvisvgm`) silently
> reverses multi-line Persian in figures. See *The figure pipeline* below.

---

## The validated stack

| Concern | Choice | Why (and what failed) |
|---|---|---|
| Publishing engine | **Quarto** (`.qmd` → HTML + PDF) | One source, two outputs, citations, cross-refs |
| PDF / bidi | **LuaLaTeX + `babel` `bidi=basic`** | Robust with `array`/`longtable`. **`xepersian`** breaks on tables; **`polyglossia`** wants extra fonts; the standalone **`bidi`** package mis-orders multi-line nodes |
| Body font | **Vazirmatn** (loaded by file) | Free, 9 weights, good Persian + Latin; no system install |
| Figures | **LuaLaTeX + babel → PyMuPDF crop** | Renders Persian correctly; **XeLaTeX + `bidi` + `dvisvgm`** reversed multi-line RTL and the woff SVGs got re-mirrored by browsers |
| Persian in HTML math | **MathJax `mtextInheritFont`** | Otherwise `\text{...}` shows broken, disconnected Persian |

---

## Quick start

```bash
# 0. one-time: install Quarto, a LuaLaTeX TeX distro, and Python deps (see Prerequisites)
pip install -r requirements.txt

# 1. SMOKE TEST FIRST — prove the toolchain renders RTL + math + code + a figure
python tools/build_diagrams.py 'sample-figure'   # build the figure it needs
quarto render smoke-test.qmd --to html
quarto render smoke-test.qmd --to pdf
#    open the two outputs; Persian must flow RTL, math/code LTR un-mirrored, figure crisp

# 2. build all figures, then the book
make -C diagrams            # or: python tools/build_diagrams.py
quarto render               # -> _book/  (HTML site + PDF)
```

If the smoke test looks right in **both** formats, the riskiest part is done and you can write
with confidence.

---

## Prerequisites

1. **Quarto** ≥ 1.4 — <https://quarto.org/docs/get-started/>.
2. **A TeX distribution with LuaLaTeX** — TeX Live, or `quarto install tinytex`. Packages
   (most are in a full install; on TinyTeX run `tlmgr install ...`):
   `babel`, `babel-persian`, `fontspec`, `tikz`/`pgf`, `pgfplots`, `geometry`, `koma-script`,
   `fancyvrb`, `framed`, `mathtools`.
3. **Python** ≥ 3.10 with `pip install -r requirements.txt` (PyMuPDF + numpy power the figure
   cropper/QA).
4. **Vazirmatn font** — `fonts/Vazirmatn-Regular.ttf` and `-Bold.ttf` are bundled here, loaded
   by file (no system install). Refresh from <https://github.com/rastikerdar/vazirmatn>.

> **Windows note:** the bare `python` may be the Microsoft Store stub; call a real interpreter
> (e.g. `C:\Program Files\Python\python.exe`). TinyTeX lives in `%APPDATA%\TinyTeX`; add
> `%APPDATA%\TinyTeX\bin\windows` to `PATH`. `tools/build_diagrams.ps1` handles both for you.

---

## Project structure

```text
.
├── _quarto.yml                 # book config (formats, chapter list)  — EDIT THIS
├── index.qmd                   # preface / first page
├── chapters/                   # one .qmd per chapter
│   └── 01-sample-chapter.qmd   # demonstrates every authoring convention
├── smoke-test.qmd              # toolchain validation page (render this first)
├── references.bib              # BibTeX bibliography
├── theme/
│   ├── preamble.tex            # LuaLaTeX + babel bidi=basic + Vazirmatn (PDF)
│   ├── ltr.lua                 # Pandoc filter: [..]{.ltr} islands -> correct per format
│   ├── custom.scss             # RTL web styling + LTR islands (HTML)
│   └── mathjax-config.html     # Persian-inside-math fix (HTML)
├── diagrams/
│   ├── figure-template.tex     # copy this to start a new figure
│   ├── sample-figure.tex       # a working example (RTL labels + math + English)
│   └── Makefile                # `make` -> tools/build_diagrams.py
├── tools/
│   ├── build_diagrams.py       # ★ figure builder: LuaLaTeX -> PyMuPDF crop -> PDF + SVG
│   ├── build_diagrams.ps1      # Windows wrapper for the above
│   ├── check_diagrams.py       # QA: flag figures that render blank / mis-cropped
│   ├── new_figure.py           # scaffold a new figure from the template
│   └── pdf_to_png.py           # rasterize a PDF for visual inspection (PDFium)
├── fonts/                      # Vazirmatn .ttf (bundled) + OFL license
└── .github/workflows/build.yml # CI: render + deploy to GitHub Pages
```

---

## Mixing RTL prose with LTR islands (the easy half)

In `.qmd` prose, Persian is the base direction. Wrap any English term, symbol, or Latin number
in an **LTR island** so it isn't mirrored:

```markdown
گذرگاهِ [DC]{.ltr} باید دستِ‌کم [$2000\ \text{V}$]{.ltr} فراهم کند.   ← inline span

::: {.ltr}
A whole left-to-right paragraph / ASCII diagram goes in a div.
:::
```

- `theme/ltr.lua` maps `[..]{.ltr}` / `::: {.ltr}` to `dir="ltr"` (HTML) and `\babelsublr{..}` /
  `\begin{otherlanguage}{english}` (PDF).
- **Math** (`$...$`) and **code** stay LTR automatically (ltr.lua also left-aligns code blocks).
- **`mtextInheritFont`** in `mathjax-config.html` makes `\text{...}` inside equations render
  connected Persian on the web.
- **Do NOT set a global `lang:`** in `_quarto.yml` — it makes Pandoc load babel/polyglossia for
  the PDF and clash with `preamble.tex`. Set `lang`/`dir` **only** on the `html` format.

---

## The figure pipeline (the hard half — read this before drawing)

Figures carry Persian labels mixed with LTR math/English. The naive route — XeLaTeX +
`standalone` + the `bidi` package, then `dvisvgm` — **silently reverses multi-line Persian**
(the first line of a `text width` box, and the whole of an `align` box, come out left-to-right),
and the woff SVGs get re-mirrored by browsers. The error is in the PDF *layout*, so it's not a
viewer bug you can paper over.

**The fix, baked into `figure-template.tex` and `tools/build_diagrams.py`:**

1. Compile each figure with **LuaLaTeX + babel `bidi=basic`** — the *same* engine as the book
   body, which orders Persian correctly.
2. Set the font with **`\babelfont{rm}[Renderer=Node, Path=../fonts/, …]{Vazirmatn}`** (and
   `{sf}`). **`Renderer=Node` is mandatory** — LuaHBTeX's default HarfBuzz has a Persian-shaping
   assertion bug.
3. Use `\documentclass{article}` on a **huge `geometry` page**, and wrap the **whole**
   `tikzpicture` in **`\babelsublr{...}`**. Without `\babelsublr`, the RTL page *mirrors the
   geometry* (a node at x=6 lands on the left); with it, geometry is LTR while node *text* still
   gets RTL from bidi.
4. **PyMuPDF** crops the big page to its content (by *rendered pixels*, robust against invisible
   full-page elements) and writes a tight `<base>.pdf` + a `<base>.svg` with **outlined glyphs**
   (`text_as_path`, no `<text>` → immune to browser bidi).

### Add a figure

```bash
python tools/new_figure.py 02-my-diagram     # copies figure-template.tex -> diagrams/02-my-diagram.tex
# ...draw inside diagrams/02-my-diagram.tex...
python tools/build_diagrams.py '02-my-diagram'   # -> 02-my-diagram.pdf + .svg
```

Reference it from a chapter, one include per format (so each gets the right file):

```markdown
::: {.content-visible when-format="html"}
![عنوانِ شکل](../diagrams/02-my-diagram.svg){#fig-mine width=70%}
:::
::: {.content-visible when-format="pdf"}
![عنوانِ شکل](../diagrams/02-my-diagram.pdf){#fig-mine width=70%}
:::
```

### Figure authoring tips (inside a `.tex`)

- Persian node text **just works** — no `\setRTL`, no `\RL`, no `Script=Arabic`.
- English/math are LTR automatically; write them plainly. **Do not** use `[..]{.ltr}` inside a
  `.tex` (that's Pandoc markdown, not LaTeX).
- **Inline math with a binary relation** (`$Y=HX$`) inside an RTL node can render with loose
  gaps. Wrap it: **`\mbox{$Y=HX$}`** keeps it one tight LTR unit. (See `sample-figure.tex`.)
- Multi-line nodes (`\\` in an `align` / `text width` node) order correctly under this pipeline.

---

## Build & deploy

```bash
python tools/build_diagrams.py        # all figures -> PDF + SVG
quarto render --to html               # website  -> _book/
quarto render --to pdf                # print PDF (LuaLaTeX + babel)
quarto render                         # both
```

CI in `.github/workflows/build.yml` renders on every push and deploys the HTML to **GitHub
Pages**. To enable: push the repo and set Pages source to **"GitHub Actions"**.

> **Render gotcha:** `quarto render` fails (`safeRemoveDirSync`) if the previous book PDF in
> `_book/` is open in a viewer. Close it first.

---

## Verification & QA (don't trust your eyes on RTL)

Persian visual order is easy to misread. Verify **objectively**:

- **Smoke test** — render `smoke-test.qmd` to both formats; it exercises RTL + math + code +
  figure + table on one page.
- **Figure QA** — `python tools/check_diagrams.py` flags any figure that renders blank or with a
  suspicious size (catches a content-clipping crop bug). Good as a CI gate.
- **Is a figure's Persian actually in the right order?** Extract word coordinates instead of
  squinting:
  ```python
  import fitz
  ws = fitz.open("diagrams/NN.pdf")[0].get_text("words")  # (x0,y0,x1,y1, word, ...)
  # for an RTL line, the FIRST logical word must have the LARGEST x (rightmost).
  ```
  The console can't print Persian on Windows (cp1252) — write results to a UTF-8 file and read
  that.
- **See an SVG as a browser does** — `msedge --headless=new --screenshot=out.png file:///…svg`.
- **Rasterize any PDF** for a quick look — `python tools/pdf_to_png.py file.pdf out`.

---

## Gotchas reference (hard-won)

- **No global `lang:`** in `_quarto.yml` (clashes with the PDF preamble). `lang`/`dir` on `html` only.
- **Figures: LuaLaTeX + babel + `\babelsublr`, not XeLaTeX + `bidi` + `dvisvgm`.** Multi-line RTL
  reverses otherwise; woff SVGs get re-mirrored by browsers.
- **`Renderer=Node`** in `\babelfont` is mandatory (HarfBuzz Persian-shaping bug).
- **`\babelsublr` around the whole `tikzpicture`** or the RTL page mirrors the geometry.
- **`\mbox{$...$}`** for inline math with binary relations inside RTL figure nodes (spacing).
- **PyMuPDF crop: CropBox only** (don't also `set_mediabox` — it re-frames coords and blanks the
  page); compute the bbox from **rendered pixels** (vector bbox is fooled by invisible elements).
- **Code blocks** go LTR via wrapping the whole block in `\begin{otherlanguage}{english}` from
  *outside* the verbatim box (done in `ltr.lua`) — never wrap the verbatim env itself.
- **Set both `\babelfont{rm}` and `{sf}`** to the Persian font (titles/headings use sans → tofu otherwise).

---

## Adapting to a new book / subject

1. Edit `_quarto.yml`: title, author, and the `chapters:` list.
2. Replace `index.qmd` and `chapters/01-sample-chapter.qmd` with your content (keep the sample as
   a conventions cheat-sheet until you're comfortable).
3. Add figures under `diagrams/` (start from `figure-template.tex`).
4. Put references in `references.bib`.
5. Nothing in `theme/`, `tools/`, or `fonts/` is subject-specific — leave it as is.

For a large book you may want to generate the chapter list and stubs from an outline file; that's
a thin script on top of this template (parse YAML → write `_quarto.yml` + empty `chapters/*.qmd`)
and is left out here to keep the template minimal.

---
---

<a id="farsi-guide"></a>

# گردش‌کارِ کتابِ علمی-فنیِ فارسی

> 🌐 **[English ↑](#farsi-technical-book-workflow)** · این بخش همان راهنمای بالاست، به فارسی.

یک **قالب و محیطِ آمادهٔ کار** برای نوشتنِ **کتاب‌های علمی-فنیِ فارسی (راست‌به‌چپ)** که در آن‌ها
نثرِ راست‌به‌چپ با **جزیره‌های چپ‌به‌راستِ** ریاضی، کد و اصطلاحاتِ انگلیسی در می‌آمیزد، و
**نمودارهای برداری** با برچسب‌های فارسی تولید می‌شوند. خروجی از یک منبعِ واحد، هم **وب‌سایت (HTML)**
و هم **PDFِ آمادهٔ چاپ** است.

این قالب، زنجیرهٔ ابزاری را که روی یک کتابِ بزرگِ مهندسی (۲۹۰۰ صفحه، ۲۲۸ نمودار) **با هزینهٔ گزاف
آزموده شده** فشرده می‌کند. **همه‌چیز این‌جا آزموده شده و با هم کار می‌کند.** این پوشه را کپی کنید،
محتوای خود را جای‌گذاری کنید، و یک کتابِ کارکن دارید — در **هر** موضوعِ فنی، نه فقط موضوعِ نمونه.

> اگر هیچ‌چیزِ دیگری نخواندید، بزرگ‌ترین درس این است: **نمودارها را با LuaLaTeX + babel با گزینهٔ
> `bidi=basic` بسازید (همان موتورِ بدنهٔ کتاب)، هر تصویر را در `\babelsublr` بپیچید، و با PyMuPDF
> برش بزنید.** مسیرِ «بدیهی» (XeLaTeX + بستهٔ `bidi` ← `dvisvgm`) متنِ چندخطیِ فارسیِ نمودارها را
> بی‌سروصدا وارونه می‌کند. به بخشِ «خط‌لولهٔ تصویرسازی» نگاه کنید.

## پشتهٔ آزموده‌شده

| دغدغه | انتخاب | چرا (و چه چیزی شکست خورد) |
|---|---|---|
| موتورِ انتشار | **Quarto** (‏`.qmd` ← HTML + PDF) | یک منبع، دو خروجی، ارجاع و ارجاع‌دهیِ متقابل |
| PDF / دوسویه | **LuaLaTeX + بستهٔ `babel` با `bidi=basic`** | با `array`/`longtable` پایدار است. **`xepersian`** روی جدول‌ها می‌شکند؛ **`polyglossia`** فونتِ اضافی می‌خواهد؛ بستهٔ مستقلِ **`bidi`** گره‌های چندخطی را بد می‌چیند |
| فونتِ بدنه | **Vazirmatn** (با مسیر بار می‌شود) | آزاد، ۹ وزن، پوششِ خوبِ فارسی و لاتین؛ بدونِ نصبِ سیستمی |
| نمودارها | **LuaLaTeX + babel ← برشِ PyMuPDF** | فارسی را درست می‌چیند؛ **XeLaTeX + `bidi` + `dvisvgm`** متنِ چندخطی را وارونه و SVGهای woff را در مرورگر آینه می‌کرد |
| فارسی درونِ ریاضیِ HTML | **‏`mtextInheritFont` در MathJax** | وگرنه `\text{...}` فارسیِ شکسته و گسسته نشان می‌دهد |

## شروعِ سریع

```bash
# ۰) یک‌بار: Quarto، یک توزیعِ TeX با LuaLaTeX، و وابستگی‌های پایتون را نصب کنید (بخشِ پیش‌نیازها)
pip install -r requirements.txt

# ۱) نخست آزمونِ دود — اثبات کنید زنجیرهٔ ابزار، RTL + ریاضی + کد + نمودار را درست رِندر می‌کند
python tools/build_diagrams.py 'sample-figure'   # نمودارِ موردِ نیازش را بساز
quarto render smoke-test.qmd --to html
quarto render smoke-test.qmd --to pdf
#    دو خروجی را باز کنید؛ فارسی باید راست‌به‌چپ باشد، ریاضی/کد چپ‌به‌راست و بدونِ آینه، نمودار تیز

# ۲) همهٔ نمودارها، سپس کتاب را بساز
make -C diagrams            # یا: python tools/build_diagrams.py
quarto render               # ← _book/  (سایتِ HTML + PDF)
```

اگر آزمونِ دود در **هر دو** قالب درست دیده شود، پرخطرترین بخش انجام شده و می‌توانید با اطمینان
بنویسید.

## پیش‌نیازها

۱. **Quarto** نسخهٔ ≥ 1.4 — <https://quarto.org/docs/get-started/>.
۲. **یک توزیعِ TeX با LuaLaTeX** — TeX Live، یا `quarto install tinytex`. بسته‌ها (بیشترشان در
   نصبِ کامل هستند؛ روی TinyTeX با `tlmgr install ...`):
   ‏`babel`, `babel-persian`, `fontspec`, `tikz`/`pgf`, `pgfplots`, `geometry`, `koma-script`,
   `fancyvrb`, `framed`, `mathtools`.
۳. **Python** نسخهٔ ≥ 3.10 با `pip install -r requirements.txt` (‏PyMuPDF + numpy موتورِ
   برش/کنترلِ کیفیتِ نمودارها هستند).
۴. **فونتِ Vazirmatn** — فایل‌های `fonts/Vazirmatn-Regular.ttf` و `-Bold.ttf` این‌جا همراه‌اند و با
   مسیر بار می‌شوند (بدونِ نصبِ سیستمی). برای به‌روزرسانی از
   <https://github.com/rastikerdar/vazirmatn>.

> **نکتهٔ ویندوز:** `python`ِ خام ممکن است stubِ فروشگاهِ مایکروسافت باشد؛ مفسرِ واقعی را صدا بزنید
> (مثلاً `C:\Program Files\Python\python.exe`). TinyTeX در `%APPDATA%\TinyTeX` است؛
> `%APPDATA%\TinyTeX\bin\windows` را به `PATH` بیفزایید. اسکریپتِ `tools/build_diagrams.ps1` هر دو
> را برایتان مدیریت می‌کند.

## ساختار پروژه

ساختار پوشه همان است که در بخشِ انگلیسی (*Project structure*) آمده: `_quarto.yml` (پیکربندیِ کتاب
— **این را ویرایش کنید**)، `index.qmd`، `chapters/`، `smoke-test.qmd`، `references.bib`،
`theme/` (شاملِ `preamble.tex`، `ltr.lua`، `custom.scss`، `mathjax-config.html`)،
`diagrams/` (‏`figure-template.tex`، `sample-figure.tex`، `Makefile`)،
`tools/` (‏`build_diagrams.py` ★، `build_diagrams.ps1`، `check_diagrams.py`، `new_figure.py`،
`pdf_to_png.py`)، `fonts/`، و `.github/workflows/build.yml`.

## آمیختنِ نثرِ راست‌به‌چپ با جزیره‌های چپ‌به‌راست (نیمهٔ آسان)

در نثرِ `.qmd`، جهتِ پایه فارسی است. هر اصطلاح یا نمادِ انگلیسی یا عددِ لاتین را در یک «جزیرهٔ
چپ‌به‌راست» بپیچید تا آینه نشود:

```markdown
گذرگاهِ [DC]{.ltr} باید دستِ‌کم [$2000\ \text{V}$]{.ltr} فراهم کند.   ← اسپَنِ درون‌خطی

::: {.ltr}
یک پاراگرافِ کاملِ چپ‌به‌راست / نمودارِ اَسکی در یک div می‌رود.
:::
```

- ‏`theme/ltr.lua` نشانِ `[..]{.ltr}` / `::: {.ltr}` را به `dir="ltr"` (در HTML) و
  `\babelsublr{..}` / `\begin{otherlanguage}{english}` (در PDF) نگاشت می‌کند.
- **ریاضی** (‏`$...$`) و **کد** خودکار چپ‌به‌راست می‌مانند (‏`ltr.lua` بلوک‌های کد را هم چپ‌چین می‌کند).
- ‏**`mtextInheritFont`** در `mathjax-config.html` باعث می‌شود `\text{...}` درونِ معادله، فارسیِ
  پیوسته را در وب درست نشان دهد.
- **هرگز `lang:`ِ سراسری** در `_quarto.yml` نگذارید — Pandoc را وادار می‌کند برای PDF
  بسته‌های babel/polyglossia را بار کند و با `preamble.tex` تداخل کند. `lang`/`dir` را **فقط** روی
  قالبِ `html` بگذارید.

## خط‌لولهٔ تصویرسازی (نیمهٔ سخت — پیش از کشیدنِ نمودار بخوانید)

نمودارها برچسب‌های فارسی را با ریاضی/انگلیسیِ چپ‌به‌راست می‌آمیزند. مسیرِ ساده‌لوحانه — XeLaTeX +
`standalone` + بستهٔ `bidi`، سپس `dvisvgm` — **متنِ چندخطیِ فارسی را بی‌سروصدا وارونه می‌کند**
(سطرِ اولِ گره‌های `text width` و **کلِ** گره‌های `align` چپ‌به‌راست درمی‌آیند)، و SVGهای woff در
مرورگر دوباره آینه می‌شوند. خطا در **چیدمانِ** PDF است، پس یک باگِ نمایشی نیست که بتوان پنهانش کرد.

**راه‌حل، که در `figure-template.tex` و `tools/build_diagrams.py` تعبیه شده:**

۱. هر نمودار را با **LuaLaTeX + babel با `bidi=basic`** کامپایل کنید — همان موتورِ بدنهٔ کتاب که
   فارسی را درست می‌چیند.
۲. فونت را با **`\babelfont{rm}[Renderer=Node, Path=../fonts/, …]{Vazirmatn}`** (و `{sf}`) بگذارید.
   **`Renderer=Node` الزامی است** — موتورِ پیش‌فرضِ HarfBuzz در LuaHBTeX یک باگِ شکل‌دهیِ فارسی دارد.
۳. از `\documentclass{article}` روی یک صفحهٔ **بزرگِ `geometry`** استفاده کنید و **کلِ**
   `tikzpicture` را در **`\babelsublr{...}`** بپیچید. بدونِ `\babelsublr`، صفحهٔ راست‌به‌چپ
   **هندسهٔ** شکل را آینه می‌کند (گرهی در x=۶ به چپ می‌افتد)؛ با آن، هندسه چپ‌به‌راست می‌ماند ولی
   متنِ گره‌ها از طریقِ bidi راست‌به‌چپ می‌شود.
۴. **PyMuPDF** صفحهٔ بزرگ را بر اساسِ *پیکسل‌های رِندرشده* به اندازهٔ محتوا می‌برد (مصون از عناصرِ
   نامرئیِ تمام‌صفحه) و یک `<base>.pdf`ِ فشرده + یک `<base>.svg` با گلیف‌های **مسیر-شده**
   (‏`text_as_path`، بدونِ `<text>` ← مصون از bidiِ مرورگر) می‌نویسد.

### افزودنِ یک نمودار

```bash
python tools/new_figure.py 02-my-diagram     # figure-template.tex را به diagrams/02-my-diagram.tex کپی می‌کند
# ...داخلِ diagrams/02-my-diagram.tex بکشید...
python tools/build_diagrams.py '02-my-diagram'   # ← 02-my-diagram.pdf + .svg
```

از یک فصل، با یک درج به‌ازای هر قالب ارجاع دهید (تا هر کدام فایلِ درستش را بگیرد):

```markdown
::: {.content-visible when-format="html"}
![عنوانِ شکل](../diagrams/02-my-diagram.svg){#fig-mine width=70%}
:::
::: {.content-visible when-format="pdf"}
![عنوانِ شکل](../diagrams/02-my-diagram.pdf){#fig-mine width=70%}
:::
```

### نکاتِ نگارشِ نمودار (درونِ یک `.tex`)

- متنِ فارسیِ گره **همین‌جوری کار می‌کند** — بدونِ `\setRTL`، بدونِ `\RL`، بدونِ `Script=Arabic`.
- انگلیسی/ریاضی خودکار چپ‌به‌راست‌اند؛ ساده بنویسیدشان. درونِ `.tex` **از `[..]{.ltr}` استفاده
  نکنید** (آن نشانه‌گذاریِ Pandoc است، نه LaTeX).
- **ریاضیِ درون‌خطی با یک رابطهٔ دوتایی** (‏`$Y=HX$`) درونِ گرهِ راست‌به‌چپ ممکن است با فاصله‌های
  باز رِندر شود. بپیچیدش: **`\mbox{$Y=HX$}`** آن را یک واحدِ چپ‌به‌راستِ فشرده نگه می‌دارد
  (نمونه در `sample-figure.tex`).
- گره‌های چندخطی (‏`\\` درونِ گرهِ `align` / `text width`) زیرِ این خط‌لوله درست چیده می‌شوند.

## ساخت و استقرار

```bash
python tools/build_diagrams.py        # همهٔ نمودارها ← PDF + SVG
quarto render --to html               # وب‌سایت ← _book/
quarto render --to pdf                # PDFِ چاپ (LuaLaTeX + babel)
quarto render                         # هر دو
```

گردش‌کارِ `.github/workflows/build.yml` در هر push رِندر و سایتِ HTML را روی **GitHub Pages** مستقر
می‌کند. برای فعال‌سازی: مخزن را push کنید و منبعِ Pages را روی **«GitHub Actions»** بگذارید.

> **تلهٔ رِندر:** اگر PDFِ پیشینِ کتاب در `_book/` در یک نمایشگر **باز** باشد، `quarto render`
> شکست می‌خورد (‏`safeRemoveDirSync`). نخست نمایشگر را ببندید.

## راستی‌آزمایی و کنترلِ کیفیت (روی RTL به چشمِ خود اعتماد نکنید)

ترتیبِ دیداریِ فارسی به‌سادگی اشتباه خوانده می‌شود. **عینی** راستی‌آزمایی کنید:

- **آزمونِ دود** — `smoke-test.qmd` را به هر دو قالب رِندر کنید؛ RTL + ریاضی + کد + نمودار + جدول
  را در یک صفحه می‌سنجد.
- **کنترلِ کیفیتِ نمودار** — `python tools/check_diagrams.py` هر نموداری را که سفید یا با اندازهٔ
  مشکوک رِندر شده علامت می‌زند (باگِ بریده‌شدنِ محتوا را می‌گیرد). برای دروازهٔ CI خوب است.
- **آیا ترتیبِ فارسیِ نمودار واقعاً درست است؟** به‌جای خیره‌شدن، مختصاتِ واژه‌ها را استخراج کنید:
  ```python
  import fitz
  ws = fitz.open("diagrams/NN.pdf")[0].get_text("words")  # (x0,y0,x1,y1, word, ...)
  # در یک سطرِ راست‌به‌چپ، نخستین واژهٔ منطقی باید بزرگ‌ترین x را داشته باشد (راست‌ترین).
  ```
  کنسولِ ویندوز نمی‌تواند فارسی چاپ کند (cp1252) — خروجی را در یک فایلِ UTF-8 بنویسید و آن را بخوانید.
- **دیدنِ SVG آن‌گونه که مرورگر می‌بیند** — `msedge --headless=new --screenshot=out.png file:///…svg`.
- **رِستر کردنِ هر PDF** برای نگاهِ سریع — `python tools/pdf_to_png.py file.pdf out`.

## مرجعِ تله‌ها (با هزینهٔ گزاف آموخته)

- **بدونِ `lang:`ِ سراسری** در `_quarto.yml` (با preambleِ PDF تداخل می‌کند). `lang`/`dir` فقط روی `html`.
- **نمودارها: LuaLaTeX + babel + `\babelsublr`، نه XeLaTeX + `bidi` + `dvisvgm`.** وگرنه RTLِ
  چندخطی وارونه می‌شود؛ SVGهای woff در مرورگر دوباره آینه می‌شوند.
- **`Renderer=Node`** در `\babelfont` الزامی است (باگِ شکل‌دهیِ فارسیِ HarfBuzz).
- **`\babelsublr` دورِ کلِ `tikzpicture`** وگرنه صفحهٔ راست‌به‌چپ هندسه را آینه می‌کند.
- **`\mbox{$...$}`** برای ریاضیِ درون‌خطیِ دارای رابطهٔ دوتایی درونِ گره‌های نمودار (مسئلهٔ فاصله).
- **برشِ PyMuPDF: فقط CropBox** (‏`set_mediabox` را هم نگذارید — مختصات را جابه‌جا و صفحه را سفید
  می‌کند)؛ کادرِ محتوا را از **پیکسل‌های رِندرشده** بگیرید (کادرِ برداری را عناصرِ نامرئی فریب می‌دهند).
- **بلوک‌های کد** با پیچیدنِ کلِ بلوک در `\begin{otherlanguage}{english}` از **بیرونِ** جعبهٔ
  verbatim چپ‌به‌راست می‌شوند (در `ltr.lua`) — هرگز خودِ محیطِ verbatim را نپیچید.
- **هم `\babelfont{rm}` و هم `{sf}`** را به فونتِ فارسی بگذارید (عنوان/سرفصل‌ها از sans استفاده
  می‌کنند، وگرنه tofu).

## سازگارسازی برای کتاب/موضوعِ تازه

۱. ‏`_quarto.yml` را ویرایش کنید: عنوان، نویسنده و فهرستِ `chapters:`.
۲. ‏`index.qmd` و `chapters/01-sample-chapter.qmd` را با محتوای خود جایگزین کنید (فصلِ نمونه را تا
   وقتی راحت نشده‌اید به‌عنوانِ برگهٔ تقلبِ قراردادها نگه دارید).
۳. نمودارها را زیرِ `diagrams/` بیفزایید (از `figure-template.tex` آغاز کنید).
۴. ارجاع‌ها را در `references.bib` بگذارید.
۵. هیچ‌چیز در `theme/`، `tools/` یا `fonts/` وابسته به موضوع نیست — دست‌نخورده بگذاریدش.

برای کتابِ بزرگ شاید بخواهید فهرستِ فصل‌ها و اسکلت‌ها را از یک فایلِ سرفصل تولید کنید؛ آن یک
اسکریپتِ نازک روی این قالب است (‏YAML را بخواند ← `_quarto.yml` + فایل‌های خالیِ `chapters/*.qmd`
بنویسد) و برای کمینه‌ماندنِ قالب این‌جا کنار گذاشته شده است.
