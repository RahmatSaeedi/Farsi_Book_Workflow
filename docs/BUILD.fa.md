# ساختِ کتاب: زنجیرهٔ ابزار، گردشِ کار و تله‌ها

*[English](BUILD.md)*

این راهنما یک **رایانهٔ کاملاً تازه** را به جایی می‌رساند که همهٔ نسخه‌های کتابی را که از این
قالب ساخته شده بسازد و بتواند در مخزنِ آن commit کند. زنجیرهٔ ابزار و نسخه‌های زیر همان‌هایی
است که یک کتابِ مهندسیِ فارسیِ ۲٬۹۰۰ صفحه‌ای با ۲۲۸ نمودار در ۲۳ آبان ۱۴۰۵ (2026-11-13) با
آن‌ها ساخته و راستی‌آزمایی شد (اجرای «اتاقِ تمیز» روی ویندوز: کلونِ تازه، TinyTeXِ تازه،
پایتونِ تازه، و جاوا و epubcheckِ دانلودشده از اینترنت). کتابِ نمونهٔ خودِ این قالب هم همان
روز با همین ابزارها ساخته شد.

قراردادهای نگارش (نثرِ راست‌به‌چپ، جزیره‌های چپ‌به‌راست، نمودارها) در
[README](../README.md#farsi-guide) است؛ این فایل دربارهٔ ابزارها و ساخت است.

---

## ۱. شروعِ سریع (ویندوز)

```powershell
# ۱. گیت، سپس نسخهٔ خودتان از قالب
winget install Git.Git            # سپس یک پنجرهٔ PowerShellِ تازه باز کنید
git clone <نشانیِ مخزنِ کتابِ شما>
cd <پوشهٔ آن>

# ۲. همهٔ ابزارهای لازم (اجرای دوباره بی‌خطر است و هر چه نصب باشد را رد می‌کند)
powershell -ExecutionPolicy Bypass -File tools\setup_windows.ps1 `
    -GitName "Your Name" -GitEmail "you@example.com" -WithKindlePreviewer

# ۳. در یک پنجرهٔ PowerShellِ تازه (تا تغییرِ PATH اعمال شود)
python tools\check_env.py         # همهٔ سطرها باید OK باشند
python tools\build_all.py         # همه‌چیز را در _book\ می‌سازد

# ۴. commitِ تغییراتِ منبع (خروجی‌ها در گیت نادیده گرفته می‌شوند)
git status
git add -A
git commit -m "Describe the change"
git push
```

`-WithKindlePreviewer` اختیاری است (بررسیِ تبدیلِ خودِ آمازون، بخشِ ۶)؛ جفتِ
`-GitName/-GitEmail` فقط یک بار در هر رایانه لازم است. لینوکس و مک: بخشِ ۳٫۳.

کتابِ نمونه در حدودِ یک دقیقه ساخته می‌شود. `_book/index.html` و PDF را باز کنید: فارسی باید
راست‌به‌چپ و با Vazirmatn باشد، ریاضی/کد/انگلیسی چپ‌به‌راست و بدونِ آینه‌شدن، و نمودار تیز.
سپس یک جملهٔ فارسی را در PDF انتخاب و کپی کنید و در یک ویرایشگرِ متن بچسبانید: باید همان
جمله‌ای باشد که می‌بینید (بخشِ ۵).

---

## ۲. خروجی‌های ساخت

همه‌چیز در `_book/` قرار می‌گیرد که گیت آن را نادیده می‌گیرد. نامِ فایل‌ها از `title:` در
`_quarto.yml` می‌آید؛ پس PDF و EPUBِ یک عنوانِ فارسی نامِ فارسی دارند.

| فایل در `_book/` | چیست | کجا می‌رود |
|---|---|---|
| `index.html` و `chapters/`، `site_libs/`، … | وب‌سایت | GitHub Pages (CI در هر push به `main` منتشرش می‌کند) |
| `<عنوان>.pdf` | نسخهٔ PDF/چاپی، با متنِ فارسیِ قابلِ کپی و جست‌وجو | خوانندگان، چاپ |
| `<عنوان>.epub` | EPUB 3 با معادله‌های MathML و شکل‌های برداری | **Apple Books**، Google Play Books، Kobo، … |
| `<ascii>-kindle.epub` | نسخهٔ کیندل (معادله به متن/PNG، شکل به PNG، کدِ شکسته‌شونده) | **فقط Amazon KDP** |
| `<ascii>-kindle-cover.jpg` / `.tif` | جلدِ تبلیغاتیِ کیندل، ارتفاعِ ۲۵۶۰ پیکسل، ۳۰۰ DPI، sRGB | بارگذاریِ جلد در KDP |
| `kindle-preview/*.kpf` | تبدیلِ Kindle Previewer (فقط با `--kindle-previewer`) | باز کردن در Kindle Previewer |

خروجی‌های کتابِ نمونه در [`examples/`](../examples/) در مخزن نگه داشته شده تا نخستین ساختِ
خودتان را با آن بسنجید.

`<ascii>` چیزی است که پس از حذفِ همه‌چیز جز حروفِ لاتین و رقم از عنوان می‌ماند (برای عنوانی
که «MRI» دارد: `MRI-kindle.epub`)، و اگر چیزی نماند `book`. فایلِ `-kindle.epub` را به اپل
ندهید: آن نسخهٔ ساده‌شده‌ای است که برای مبدلِ آمازون ساخته می‌شود. اپل EPUBِ اصلی را می‌گیرد.

لازم نیست همهٔ نسخه‌ها را منتشر کنید. `python tools/build_all.py --no-kindle` فایل‌های کیندل
را رد می‌کند؛ با برداشتنِ بلوکِ `epub:` از `_quarto.yml` دیگر EPUB ساخته نمی‌شود (گام‌های بعدی
کاری برای انجام ندارند، پس `--no-kindle --no-verify` بدهید).

---

## ۳. زنجیرهٔ ابزار

### ۳٫۱ نسخه‌های راستی‌آزمایی‌شده

| ابزار | نسخه | کاربرد | نصب با |
|---|---|---|---|
| Git | 2.52 | کنترلِ نسخه | `winget install Git.Git` |
| Quarto | 1.11.9 (Pandoc 3.10 درونِ خودش)؛ کمینه 1.4 | رِندرِ HTML، PDF و EPUB | `winget install Posit.Quarto` |
| TinyTeX | TeX Live 2026، LuaHBTeX 1.24.0 | PDF، شکل‌ها، جلد، معادله‌های کیندل | `quarto install tinytex --update-path` |
| بسته‌های TeX | ۳۹ بستهٔ فهرست‌شده در [`tools/tex-packages.txt`](../tools/tex-packages.txt) | توضیحِ هر گروه در همان فایل | `tlmgr install …` |
| Python | 3.14.1 (هر 3.10 به بالا) | همهٔ ابزارهای ساخت | `winget install Python.Python.3.14` |
| بسته‌های پایتون | PyMuPDF 2.1، pypdfium2 5.15، Pillow 13، numpy 2.5، PyYAML 6.0 ([`requirements.txt`](../requirements.txt)) | شکل‌ها، جلد، نسخهٔ کیندل، بررسی‌ها | `pip install -r requirements.txt` |
| Java | 25 LTS (Temurin JRE، قابل‌حمل در `.tools/`) | اجرای epubcheck | `python tools/verify_epub.py --install-tools` |
| epubcheck | 5.4.0 (در `.tools/`) | همان اعتبارسنجی که فروشگاه‌ها اجرا می‌کنند | همان فرمان |
| Kindle Previewer | 4.0.4 (اختیاری؛ ویندوز/مک) | بررسیِ تبدیلِ خودِ آمازون | `winget install Amazon.KindlePreviewer` |
| فونت‌ها | Vazirmatn (در `fonts/`)، Latin Modern (از TeX) | متن، کد، ریاضی | نیازی به نصب نیست |

**لازم نیست:** نصبِ سیستمیِ Vazirmatn، Pandocِ جداگانه (Quarto از Pandocِ خودش استفاده
می‌کند)، `make` روی ویندوز، یا دسترسیِ مدیر (فقط نصب‌کننده‌های winget برای Git/Python/Quarto
ممکن است تأیید بخواهند).

`python tools/check_env.py` همهٔ این‌ها و تنظیماتِ گیتِ بخشِ ۸ را می‌سنجد و برای هر کمبود،
فرمانِ رفعِ آن را چاپ می‌کند.

### ۳٫۲ کارهایی که `tools/setup_windows.ps1` انجام می‌دهد

این‌ها گام‌های دستی‌ای است که اسکریپت خودکار می‌کند؛ هر گامی که از پیش انجام شده باشد رد
می‌شود.

1. **Git، Python و Quarto** با winget. `python`ی که فقط stubِ فروشگاهِ مایکروسافت
   (`…\WindowsApps\python.exe`) باشد به حساب نمی‌آید.
2. **TinyTeX** با `quarto install tinytex --update-path` (در `%APPDATA%\TinyTeX`).
3. **بسته‌های TeX:** هر سطرِ `tools/tex-packages.txt` با `kpsewhich` بررسی و فقط کمبودها
   نصب می‌شوند (`tlmgr update --self` و سپس `tlmgr install …`). در آزمونِ اتاقِ تمیز،
   TinyTeXِ تازه `luatexbase ctablestack pgfplots fvextra` را نداشت.
4. **نمایهٔ فونت:** `OSFONTDIR` را به پوشهٔ `fonts\` مخزن می‌گذارد و
   `luaotfload-tool --update --force` را اجرا می‌کند تا LuaTeX فونتِ Vazirmatn را با **نام**
   پیدا کند (بخشِ ۷).
5. **بسته‌های پایتون** با `python -m pip install -r requirements.txt`. بدونِ دسترسیِ مدیر،
   pip در پروفایلِ کاربر نصب می‌کند.
6. **جاوا و epubcheck** با `python tools\verify_epub.py --install-tools` که در `.tools\`
   دانلود می‌کند.
7. **Kindle Previewer 4**، فقط با `-WithKindlePreviewer`.
8. **تنظیماتِ گیت** برای این مخزن: `core.quotepath false`، `core.longpaths true`، و اگر
   داده شده باشد نام و ایمیلِ شما.
9. **بررسیِ پایانی** با `python tools\check_env.py`.

### ۳٫۳ لینوکس و مک

همان گام‌ها به‌صورتِ دستی. گردشِ کارِ CI
([`.github/workflows/build.yml`](../.github/workflows/build.yml)) نسخهٔ لینوکسیِ همین دستور
است.

```bash
# Quarto: https://quarto.org/docs/get-started/  (macOS: brew install --cask quarto)
quarto install tinytex --update-path            # سپس یک ترمینالِ تازه باز کنید
tlmgr update --self                             # TinyTeXِ تازه ممکن است تا این اجرا نشود، نصب را رد کند
tlmgr install $(grep -v '^\s*#' tools/tex-packages.txt | awk 'NF {print $1}')
OSFONTDIR="$PWD/fonts" luaotfload-tool --update --force
python3 -m venv .venv && . .venv/bin/activate   # .venv/ در گیت نادیده گرفته می‌شود
pip install -r requirements.txt
python tools/verify_epub.py --install-tools     # جاوا و epubcheck در .tools/
git config core.quotepath false
python tools/check_env.py
python tools/build_all.py
```

Kindle Previewer فقط برای ویندوز و مک وجود دارد. روی لینوکس نسخهٔ کیندل باز هم ساخته و با
epubcheck و `kindle_audit.py` بررسی می‌شود.

### ۳٫۴ همهٔ ابزارهای پوشهٔ `tools/`

| اسکریپت | چه می‌کند |
|---|---|
| `setup_windows.ps1` | کلِ زنجیرهٔ ابزار را روی ویندوز نصب می‌کند (بخشِ ۳٫۲) |
| `check_env.py` | می‌گوید چه نصب است و هر کمبود چگونه رفع می‌شود |
| `build_all.py` | کلِ ساخت، به ترتیبِ درست، همراه با بررسی‌ها (بخشِ ۴) |
| `build_diagrams.py` (‏`.ps1` و `diagrams/Makefile` پوسته‌اند) | `diagrams/*.tex` ← PDFِ بریده و SVG |
| `new_figure.py` | یک نمودار را از `diagrams/figure-template.tex` آغاز می‌کند |
| `check_diagrams.py` | نمودارهایی را که سفید یا بریده‌نشده درآمده‌اند نشان می‌دهد |
| `build_cover.py` | `cover/cover.tex` ← `cover/cover.pdf` و `cover.png` |
| `gen_stubs.py` | اختیاری: اسکلتِ فصل‌ها و فهرستِ فصل‌ها از روی `outline/chapters.yml` |
| `fix_epub.py` | پس از هر رِندر اجرا می‌شود (قلابِ post-renderِ Quarto): EPUB را برای epubcheck/اپل/کیندل اصلاح می‌کند |
| `build_kindle_epub.py`، `kindle_math.py` | نسخهٔ کیندل را از روی EPUB می‌سازند |
| `make_kindle_cover.py` | جلدِ تبلیغاتیِ KDP از روی `cover/cover.pdf` |
| `verify_epub.py` | epubcheck، سقفِ اندازهٔ تصویرِ اپل، Kindle Previewer؛ `--install-tools` جاوا و epubcheck را می‌گیرد |
| `kindle_audit.py` | قاعده‌هایی از راهنمای انتشارِ کیندل که هیچ ابزارِ دیگری گزارش نمی‌کند |
| `pdf_text_check.py` | آنچه یک نمایشگر از PDF کپی می‌کند؛ مقایسهٔ هندسیِ دو PDF (بخشِ ۵) |
| `pdf_to_png.py` | رِستر کردنِ صفحه‌های PDF برای دیدن |
| `update_examples.py` | خروجی‌های کتابِ نمونه را از `_book/` به پوشهٔ commitشدهٔ `examples/` کپی می‌کند (فقط برای نگه‌داریِ خودِ قالب) |
| `source-fixes/*.py` | اختیاری: اصلاحِ خطاهای رایجِ نشانه‌گذاری در منبع‌های `.qmd` (بخشِ ۴٫۳) |
| `tex-packages.txt` | فهرستِ بسته‌های TeX، مشترک میانِ نصب، `check_env.py` و CI |

---

## ۴. گردشِ کارِ ساخت

### ۴٫۱ `python tools/build_all.py`

این گام‌ها را به ترتیب اجرا می‌کند و در نخستین خطا می‌ایستد. زمان‌ها برای کتابِ مرجعِ ۲٬۹۰۰
صفحه‌ای با ساختِ هر ۲۲۸ نمودار از صفر است؛ کتابِ نمونه روی‌هم حدودِ یک دقیقه می‌برد.

| گام | فرمانی که اجرا می‌کند | چه می‌کند | زمان (کتابِ بزرگ) |
|---|---|---|---|
| ۱ | `tools/check_env.py` | اگر ابزارِ لازمی نباشد، شروع نمی‌کند | چند ثانیه |
| ۲ | `tools/build_diagrams.py` | هر `diagrams/*.tex` را که PDF/SVGاش نیست، از منبع کهنه‌تر است یا هرگز بریده نشده کامپایل می‌کند (LuaLaTeX، سپس PyMuPDF آن را به PDFِ تنگ برای چاپ و SVG برای وب می‌بُرد). اگر `cover/cover.pdf` یا `.png` نباشد، جلد را هم می‌سازد | حدودِ ۲۰ دقیقه |
| ۳ | `quarto render` | وب‌سایت، PDF و EPUB **در یک رِندر**؛ سپس قلابِ post-renderِ Quarto فایلِ `tools/fix_epub.py` را اجرا می‌کند که آنچه نویسندهٔ EPUBِ Pandoc برای epubcheck/اپل به‌جا می‌گذارد را اصلاح می‌کند | حدودِ ۴۵ دقیقه |
| ۴ | `tools/build_kindle_epub.py` | فایلِ `-kindle.epub` را می‌سازد: معادله به متنِ یونیکد یا PNG، شکل به PNG (حداکثر ۵٫۵ مگاپیکسل)، شکستنِ سطرهای کد، فهرستِ دوسطحی | حدودِ ۳ دقیقه |
| ۵ | `tools/make_kindle_cover.py` | `cover/cover.pdf` را به جلدِ تبلیغاتیِ KDP (JPEG و TIFF) تبدیل می‌کند | چند ثانیه |
| ۶ | `tools/verify_epub.py --epubcheck-only` و `tools/kindle_audit.py` | epubcheck روی هر دو EPUB، سقفِ ۵٫۶ مگاپیکسلیِ تصویر در اپل، ممیزیِ راهنمای کیندل | حدودِ ۲ دقیقه (با `--kindle-previewer` حدودِ ۵۵ دقیقه بیشتر) |
| ۷ | مقایسهٔ `git status` پیش و پس از ساخت | هر چیزی که ساخت بیرون از پوشه‌های نادیده‌گرفته عوض کرده باشد را فهرست می‌کند (معمولاً هیچ) | چند ثانیه |

گزینه‌ها:

| گزینه | اثر |
|---|---|
| `--kindle-previewer` | EPUBِ کیندل را با Kindle Previewer هم تبدیل می‌کند (ویندوز/مک) و KPF را در `_book/kindle-preview/` نگه می‌دارد. EPUBِ اصلی تبدیل نمی‌شود: در کتابِ پرریاضی، Previewer ساعت‌ها روی MathMLِ آن می‌ماند |
| `--skip-render` | HTML/PDF/EPUBِ موجود در `_book/` را دوباره به کار می‌برد (فقط نسخهٔ کیندل، جلد و بررسی‌ها) |
| `--force-diagrams` | همهٔ نمودارها را دوباره می‌سازد |
| `--no-kindle`، `--no-verify` | آن گام‌ها را رد می‌کند |

### ۴٫۲ هنگامِ نوشتن

| چه چیزی را تغییر دادید | چه اجرا کنید |
|---|---|
| متنِ فصل (`chapters/*.qmd`، `appendices/*.qmd`) | `quarto preview` برای پیش‌نمایشِ زندهٔ HTML؛ پیش از انتشار `python tools/build_all.py` |
| یک نمودار (`diagrams/*.tex`) | `python tools/build_all.py` (فقط همان نمودار را می‌سازد) یا `python tools/build_diagrams.py <نامِ-نمودار>` |
| جلد (`cover/cover.tex`) | `python tools/build_cover.py`، سپس `cover.pdf` و `cover.png` را commit کنید |
| سرفصل (`outline/chapters.yml`، اگر از آن استفاده می‌کنید) | `python tools/gen_stubs.py`. فقط فهرستِ میانِ دو سطرِ نشانگر را در `_quarto.yml` بازنویسی می‌کند؛ بقیهٔ `_quarto.yml` را دستی ویرایش کنید |
| یک بستهٔ LaTeX در `theme/preamble.tex` یا در یک نمودار | آن را به `tools/tex-packages.txt` بیفزایید (نامِ بسته، سپس فایلی که فراهم می‌کند) |
| خط‌لولهٔ متنِ PDF (`theme/pdf-copytext.lua`) | `python tools/pdf_text_check.py OLD.pdf NEW.pdf --geometry`؛ سپس چند سطر را در Chrome، Edge و Firefox کپی کنید |

`smoke-test.qmd` سندی یک‌صفحه‌ای با نثرِ راست‌به‌چپ، ریاضی، کد، نمودار و جدول است. اگر چیزی در
کتاب نادرست دیده شد، آن را جداگانه رِندر کنید تا مشکلِ زنجیرهٔ ابزار از مشکلِ محتوا جدا شود:
`python tools/build_diagrams.py sample-figure` و سپس `quarto render smoke-test.qmd --to pdf`
(تک‌فایلی بیرون از کتاب است و به `_book/` دست نمی‌زند).

### ۴٫۳ اصلاحِ نشانه‌گذاری (`tools/source-fixes/`)

فصل‌هایی که شتاب‌زده یا با دستیارِ هوشِ مصنوعی نوشته می‌شوند چند خطای نشانه‌گذاری را تکرار
می‌کنند که ساختِ PDF را می‌شکند. هر اسکریپتِ زیر یکی از آن‌ها را در `chapters/*.qmd` و
`appendices/*.qmd` اصلاح می‌کند و به بلوک‌های کد دست نمی‌زند. فایل‌ها را درجا بازنویسی می‌کنند:
**نخست commit کنید، اجرا کنید، سپس `git diff` را بخوانید.**

| اسکریپت | خطا ← اصلاح |
|---|---|
| `normalize_math.py` | `\( … \)` و `\[ … \]` ← `$ … $` و `$$ … $$` |
| `fix_math_spacing.py` | `$ x $` (فاصله درونِ جداکننده‌ها؛ Pandoc آن را متن چاپ می‌کند) ← `$x$` |
| `unwrap_math_ltr.py` | `[$x$]{.ltr}` ← `$x$` (ریاضی خودش چپ‌به‌راست است؛ این پوشش برخی عبارت‌ها را در PDF می‌شکند) |
| `fix_ltr_math.py`، `fix_ltr_brackets.py` | لاتکِ خام درونِ `[…]{.ltr}` (مثلِ `[\omega_0]{.ltr}`) ← ریاضی یا کدِ درون‌خطی |
| `fix_paren_ltr.py` | `(term){.ltr}` ← `[(term)]{.ltr}` |
| `fix_math_ops.py` | `G_\max` ← `G_{\max}` |
| `fix_math_supersub.py` | `$T^*^$` ← `$T^{*}$` |
| `fix_isotopes.py` | `$^13C$` ← `${}^{13}\mathrm{C}$` |

---

## ۵. کپی، چسباندن و جست‌وجو در PDF

خروجیِ خامِ LuaLaTeX درست دیده می‌شود ولی نادرست خوانده می‌شود. در نسخهٔ پیشینِ این
گردشِ‌کار، متنِ کپی‌شده از PDF با حروفِ وارونه، با کدهای «شکلِ نمایشی» که هیچ جست‌وجویی
پیدایشان نمی‌کند، و بدونِ نیم‌فاصله می‌آمد («می‌شود» به «میشود»).
[`theme/pdf-copytext.lua`](../theme/pdf-copytext.lua) که `theme/preamble.tex` آن را بار
می‌کند، این را هنگامِ نوشتنِ PDF رفع می‌کند:

| عیبِ خروجیِ خامِ LuaLaTeX | کاری که مازول می‌کند |
|---|---|
| سطرهای راست‌به‌چپ به ترتیبِ منطقی و با قلمِ رو‌به‌چپ نوشته می‌شوند؛ نمایشگرها ترتیبِ دیداری را فرض می‌کنند و حروف را وارونه کپی می‌کنند | هنگامِ shipout هر سطرِ راست‌به‌چپ را به ترتیبِ دیداری بازمی‌سازد (پیوندها، رنگ‌ها، علائمِ ترکیبی و پهنای جعبه‌ها حفظ می‌شود) |
| Vazirmatn گلیف‌های شکل‌گرفته را به «Presentation Forms» (‏U+FBxx/U+FExx) نگاشت می‌کند و همان به ToUnicode می‌رفت | ToUnicode را به حروفی که تایپ شده برمی‌گرداند |
| نیم‌فاصله (ZWNJ) هرگز به PDF نمی‌رسید (قالبِ Pandoc آن را به kern و luaotfload به گلیفِ فاصله تبدیل می‌کند) | `preamble.tex` فرمانِ `\zerowidthnonjoiner` را بازتعریف و فونت‌ها را با `RawFeature={invisible=8204}` بار می‌کند تا گلیفِ واقعیِ بی‌پهنای U+200C نوشته شود |
| اِعراب (کسرهٔ اضافه، تنوین، تشدید) تکه‌های متنیِ جدا بودند و نمایشگرها کنارشان فاصله یا شکستِ سطر می‌گذاشتند | متنِ علامت را یک گلیفِ حاملِ بی‌پهنا کنارِ حرفِ پایه می‌برد و جوهرش همان‌جای پیشین کشیده می‌شود |
| TeX نویسهٔ فاصله ندارد و نمایشگرها فاصله را از اندازهٔ شکاف حدس می‌زدند | هر فاصلهٔ میان‌واژه‌ای یک گلیفِ واقعیِ فاصله به‌همراهِ kern با همان پهناست |
| حروفِ الفبای ریاضی (U+1D400…) در Chrome به‌صورتِ `�` کپی می‌شدند | به حرفِ ساده خوانده می‌شوند، پس نمادهای درونِ فرمول جست‌وجوپذیرند |
| سطرِ زیرنویسِ شکل و جدول به ترتیبِ منطقی می‌ماند و وارونه کپی می‌شد (رنگِ زیرنویس درونِ سطر باز و بیرون از آن بسته می‌شود) | چنین سطری هم بازسازی می‌شود؛ `preamble.tex` برچسبِ «شکل» را هم با «ک»ِ فارسی می‌نویسد تا جست‌وجوی «شکل» زیرنویس‌ها را پیدا کند |

**چیدمانِ صفحه تغییر نمی‌کند**؛ فقط ترتیب و برچسبِ گلیف‌ها در جریانِ PDF عوض می‌شود. (یک
استثنا: نقطه‌چینِ فهرستِ مطالب می‌تواند کمتر از یک فاصلهٔ نقطه جابه‌جا شود.)

برای سنجشِ یک ساخت:

```bash
python tools/pdf_text_check.py _book/BOOK.pdf --page 3       # متن، آن‌گونه که PyMuPDF و PDFium (Chrome/Edge) بیرون می‌کشند
python tools/pdf_text_check.py OLD.pdf NEW.pdf --geometry    # ثابت می‌کند دو ساخت هر گلیف را یک‌جا می‌گذارند
```

پایانِ لاگِ LaTeX شمارِ سطرهایی را که مازول ناچار به ترتیبِ منطقی رها کرده گزارش می‌دهد
(`pdf-copytext: … left as is`): سطرهایی که یک پیوند یا رنگ در آن‌ها به سطرِ بعد ادامه دارد.

**آنچه پوشش داده نمی‌شود:** متنِ درونِ نمودارها و روی جلد (این‌ها PDFهای جداگانه‌ای‌اند که
به‌صورتِ تصویر درج می‌شوند)، و کامنتِ فارسی درونِ بلوکِ کد.

**خطاهایی که از خودِ نمایشگرهاست** (از سمتِ PDF بدونِ خراب‌کردنِ نمایشگرِ دیگر رفع‌شدنی
نیست): PDFium (Chrome، Edge، اندروید) الگوریتمِ bidi کامل ندارد؛ درونِ سطرِ فارسی واژه‌های
لاتین و گروه‌های حرف/رقم را جابه‌جا می‌کند («T2» ← «2T»، «k-space» ← «space-k») و سطر را در
بالانویس/زیرنویسِ ریاضی می‌شکند. pdf.js (Firefox) نیم‌فاصله را می‌اندازد و پیش از اِعرابِ
پایانِ واژه یک فاصله می‌گذارد؛ جست‌وجو در آن کار می‌کند. هنگامِ تغییرِ مازول، متنِ کپی‌شده را
در خودِ مرورگرها بسنجید، نه فقط با PyMuPDF/pypdfium2.

وب‌سایت و EPUB هرگز این مشکل را نداشتند: متنِ آن‌ها HTMLِ یونیکدِ معمولی است.

---

## ۶. پیش از انتشار

`build_all.py` سه بررسیِ نخست را خودش اجرا می‌کند.

- **epubcheck** روی هر دو EPUB بدونِ خطا و بدونِ هشدار (۰/۰) است. اپل و KDP با خطاهای آن
  رد می‌کنند.
- **اندازهٔ تصویر:** هیچ تصویری بزرگ‌تر از ۵٫۶ مگاپیکسل نیست (سقفِ ITMS-9000ِ اپل).
  `verify_epub.py` این را برای هر دو کتاب می‌سنجد.
- **`kindle_audit.py`** همهٔ بررسی‌ها را می‌گذراند: قاعده‌های راهنمای انتشارِ کیندل 2026.3
  که هیچ ابزارِ دیگری گزارش نمی‌کند.
- **Kindle Previewer:** `python tools/build_all.py --skip-render --kindle-previewer` باید
  *Success*، *Enhanced Typesetting: Supported*، ۰ خطا و ۰ مشکلِ کیفی گزارش کند. سپس KPF را
  باز کنید و چند فصلِ دارای کد و معادله را ببینید.
- **فرمِ KDP:** زبان را **فارسی** انتخاب کنید. ناهماهنگی با `<dc:language>fa</dc:language>`
  رایج‌ترین علتِ «internal error»ِ KDP است.
- **جلد:** متن‌های جانگهدار را در `cover/cover.tex` (یا کلِ طرح را) عوض کنید و
  `python tools/build_cover.py` را اجرا کنید.

چرا نسخهٔ کیندل فایلِ جداگانه‌ای است: مبدلِ آمازون روی ۳۹٬۸۴۳ عبارتِ MathMLِ کتابِ مرجع به
پایان نرسید (بیش از دو ساعت CPU، بدونِ خروجی؛ KDP می‌گوید «We couldn't convert your HTML
file to Kindle format»)، و راهنما Enhanced Typesetting را برای کتابِ دارای بیش از ۲۵ تصویرِ
SVG پشتیبانی نمی‌کند (بندِ ۱۱٫۴٫۱۱). پس `build_kindle_epub.py` هر معادله را، هر جا وفادارانه
ممکن باشد، به متنِ یونیکد (`B₀`، `x²`، `10⁻³`) و وگرنه به PNGِ ساخته‌شده با پیش‌درآمدِ خودِ کتاب
تبدیل می‌کند، شکل‌ها را از PDFهای `diagrams/` به PNG برمی‌گرداند، سطرهای کد را می‌شکند (کیندل
هرگز `<pre>` را نمی‌شکند)، فهرست را دوسطحی می‌کند و پوششِ SVGِ جلدِ Pandoc را با یک تصویرِ ساده
جایگزین می‌کند. کتابی با ریاضی و شکلِ اندک شاید از EPUBِ اصلی هم درست تبدیل شود؛ نسخهٔ کیندل
در هر حال انتخابِ مطمئن است.

---

## ۷. تله‌ها (به بهای گزاف آموخته‌شده)

- **هرگز قالب‌ها را تک‌تک رِندر نکنید.** هر `quarto render` نخست `_book/` را خالی می‌کند؛
  پس `quarto render --to pdf` وب‌سایت، EPUBها و فایل‌های کیندل را پاک می‌کند. یک
  `quarto render` (همهٔ قالب‌ها) یا `build_all.py` را اجرا کنید.
- **بدونِ `lang:`ِ سراسری در `_quarto.yml`.** باعث می‌شود Pandoc برای PDF بسته‌های
  babel/polyglossia را بار کند که با `theme/preamble.tex` تداخل دارد. `lang`/`dir` فقط روی
  قالب‌های `html` و `epub` تنظیم می‌شوند. بلوکِ `language:` (برچسب‌های فارسی) چیزِ دیگری است
  و بی‌خطر است.
- **نه `xepersian`، نه `polyglossia`، نه بستهٔ `bidi`.** ‏`xepersian` روی `array`/`longtable`
  می‌شکند، `polyglossia` فونتِ اضافی می‌خواهد و بستهٔ `bidi` فارسیِ چندخطیِ نمودارها را
  وارونه می‌کند. مسیرِ آزموده LuaLaTeX + `babel` با `bidi=basic` است، هم برای بدنه و هم برای
  نمودارها.
- **«os error 32 … remove '…\_book'»:** برنامه‌ای `_book/` را باز نگه داشته و Quarto
  نمی‌تواند جایگزینش کند. پنجره‌های Explorer، ترمینال‌هایی که پوشهٔ جاری‌شان درونِ آن است و
  نمایشگرهای PDF/EPUBی که فایلی از آن را نشان می‌دهند ببندید. `check_env.py` این را
  می‌آزماید.
- **Quarto برای این پروژه بستهٔ TeX نصب نمی‌کند.** `_quarto.yml` گزینهٔ
  `latex-auto-install: false` را دارد، چون نصب‌کنندهٔ خودکار بستهٔ ناموجودِ
  `hyphen-persian` را می‌خواهد و رِندر را می‌شکند. پس هر بسته باید در
  `tools/tex-packages.txt` باشد. به‌روزرسانی‌های TeX Live گاهی بسته‌ها را جدا می‌کنند: در
  2026، `nameref` از `hyperref` جدا شد و PDF با `nameref.sty not found` شکست خورد. بستهٔ تازه
  را به فهرست بیفزایید.
- **Vazirmatn با نام:** قلمِ کدِ PDF برای نویسه‌های فارسی به Vazirmatn پناه می‌برد و این
  جایگزین، فونت را با نام پیدا می‌کند. روی رایانه‌ای که Vazirmatn در ویندوز نصب نیست، LuaTeX
  نسخهٔ درونِ مخزن را فقط وقتی می‌بیند که `OSFONTDIR` به `fonts/` اشاره کند؛ وگرنه پایانِ
  ساختِ PDF با `cannot find file ''` می‌شکند. `setup_windows.ps1`، `build_all.py`،
  `build_diagrams.py`، `build_cover.py` و `build_kindle_epub.py` این را مدیریت می‌کنند؛ برای
  `quarto render`ِ دستی، `OSFONTDIR` را خودتان تنظیم کنید. یک به‌روزرسانیِ TeX می‌تواند
  نمایهٔ فونت را کهنه بگذارد و همین خطا را روی رایانه‌ای که دیروز کار می‌کرد پدید آورد:
  `luaotfload-tool --update --force`.
- **`theme/pdf-copytext.lua` باید پیش از سطرهای `\babelfont` بار شود** (در
  `theme/preamble.tex`) تا قلابِ فونتش بارشدنِ فونت‌ها را ببیند. `Renderer=Node` و
  `RawFeature={invisible=8204}` را روی هر دو سطرِ `\babelfont` نگه دارید.
- **`siunitx` و `bm` را به پیش‌درآمد نیفزایید.** `\mu` را بازنگاشت می‌کنند و
  `\boldsymbol\mu` را می‌شکنند.
- **ساختِ نیمه‌کارهٔ نمودار:** نموداری که ساختش پس از LuaLaTeX و پیش از برش متوقف شود، بومِ
  کاملِ ۳۴۰۲ پوینتی را با نقاشی در یک گوشه نگه می‌دارد. تاریخش از منبع تازه‌تر است، پس
  به‌روز به نظر می‌رسد. در PDF به‌صورتِ یک قابِ بزرگِ تقریباً خالی چاپ می‌شود و در کیندل به
  تصویری ۱۱٫۶ مگاپیکسلی تبدیل می‌شود که اپل رد می‌کند. `build_all.py` هر نموداری را که PDFاش
  هرگز بریده نشده دوباره می‌سازد و `check_diagrams.py` آن را نشان می‌دهد.
- **شمارهٔ صفحهٔ آینه‌شده:** وقتی صفحه درونِ یک بلوکِ کد می‌شکست، شمارهٔ صفحه وارونه چیده
  می‌شد («321» در صفحهٔ ۱۲۳). `preamble.tex` شمارهٔ صفحه را در یک جعبهٔ صریحاً چپ‌به‌راست
  می‌گذارد.
- **Kindle Previewer:**
  - در هر لحظه **فقط یک تبدیل**؛ دو تبدیلِ هم‌زمان هر دو بی‌هیچ خطایی خروجیِ خالی می‌دهند.
  - تبدیلِ کاملِ یک کتابِ ۲٬۹۰۰ صفحه‌ای حدودِ ۵۵ دقیقه طول می‌کشد.
  - تبدیلی که کشته شود پوشهٔ `%TEMP%\kpr_cli_<name>_epub` را به‌جا می‌گذارد و پس از آن هر
    تبدیلِ فایلی با همان نام در چند ثانیه در «Pre-processing» شکست می‌خورد.
    `verify_epub.py` پیش از تبدیل آن پوشه را پاک می‌کند.
  - نسخهٔ ۳ با نخستین اجرا خودش را به نسخهٔ ۴ (یک برنامهٔ MSIX) ارتقا می‌دهد؛ فرمان‌ها از آن
    پس `kindlepreviewer4` / `kpr4` هستند.
- **نامِ فارسیِ فایل و جاوا:** روی ویندوز، JVM نامِ فارسیِ EPUB را `????` دریافت می‌کند و
  epubcheck «File not found» می‌دهد که درست مثلِ «فایل خراب است» به نظر می‌رسد.
  `verify_epub.py` یک کپی با نامِ اَسکی را می‌سنجد و نسخهٔ کیندل از ابتدا نامِ اَسکی دارد.
- **stubِ پایتون:** `python` ممکن است جانگهدارِ فروشگاهِ مایکروسافت باشد. `check_env.py`
  آن را نشان می‌دهد؛ پایتونِ واقعی نصب کنید (بخشِ ۳٫۱).
- **کد در کیندل:** کیندل فقط `white-space: normal | nowrap` را پشتیبانی می‌کند، پس `<pre>`
  هرگز نمی‌شکند و سطرهای بلند از صفحه بیرون می‌زنند. `build_kindle_epub.py` هر قطعه‌کد را
  به سطرهای شکسته‌شونده بازنویسی می‌کند و اگر سطرِ بلندِ `<pre>` برگردد، `kindle_audit.py`
  شکست می‌خورد.
- **پیوند به فایلِ `.qmd` در EPUB می‌شکند.** ‏`[فصلِ بعد](chapters/02-x.qmd)` در وب کار می‌کند
  ولی epubcheck آن را با `RSC-007` رد می‌کند. با `@sec-…` ارجاع دهید.
- **رنگِ نحوِ زبانی که Pandoc نمی‌شناسد:** یک تعریفِ نحوِ KDE در `theme/syntax/<lang>.xml`
  بگذارید، آن را زیرِ `syntax-definitions:` در `_quarto.yml` ثبت کنید و نامش را زبانِ بلوکِ
  کد بگذارید.
- **ریاضی‌ای که EPUB نمی‌تواند تبدیل کند:** مبدلِ MathMLِ Pandoc چند فرمان را ندارد
  (`\xleftrightarrow`، `\tbinom`، `\dbinom`)؛ `theme/epub-math.lua` آن‌ها را فقط برای EPUB
  بازنویسی می‌کند. اگر رِندر «Could not convert TeX math» ثبت کرد، فرمان را آن‌جا بیفزایید.
- **دانلودی که 403 می‌دهد:** برخی سرورها (APIِ جاوای Adoptium) عاملِ کاربرِ پیش‌فرضِ
  پایتون را رد می‌کنند. `verify_epub.py` یک عاملِ کاربرِ عمومی می‌فرستد.

---

## ۸. گیت: چه پیگیری می‌شود و چه ساخته می‌شود

**پیگیری‌شده (منبع):**
- `chapters/`، `appendices/`، `index.qmd`، `outline/`، `glossary/`، `templates/`،
  `references.bib`
- `diagrams/*.tex`، `theme/`، `tools/`، `fonts/`
- `cover/` (`cover.tex`، `cover.pdf`، `cover.png`)
- `_quarto.yml`، `requirements.txt`، `.gitattributes`، `.github/`، `docs/`
- `examples/`: خروجی‌های کتابِ نمونه که فقط `tools/update_examples.py` تازه‌شان می‌کند. در
  مخزنِ کتابِ خودتان پاکش کنید

**نادیده‌گرفته (ساخته‌شده؛ هر زمان پاک‌کردنش بی‌خطر است):**

| مسیر | دوباره ساخته می‌شود با |
|---|---|
| `_book/`، `_site/` | `build_all.py`. هرگز این‌ها را از نادیده‌گرفتن خارج نکنید: برای کتابِ بزرگ روی‌هم حدودِ ۴۰۰ مگابایت‌اند و یک `.kpf` به‌تنهایی می‌تواند از سقفِ ۱۰۰ مگابایتیِ هر فایل در گیت‌هاب بزرگ‌تر شود، پس push رد می‌شود |
| `.quarto/` | Quarto |
| `.kindle-build/` | `build_kindle_epub.py` |
| `.tools/` | `verify_epub.py --install-tools` |
| `diagrams/*.pdf`، `*.svg`، `*.aux`، `*.log`، `*.xdv` | `build_all.py` |
| `__pycache__/`، `.venv/` | پایتون |
| `smoke-test.pdf`، `smoke-test.html`، `smoke-test_files/` | رِندرِ `smoke-test.qmd` |
| `_*.py`، `_*.txt` | هیچ؛ بنا به قرارداد این‌ها فایل‌های چرک‌نویس‌اند |
| `.claude/`، `CLAUDE.local.md` | هیچ؛ تنظیماتِ شخصیِ Claude Code برای همین رایانه. هرگز commit نشوند |

**تنظیمات:**
- `.gitattributes` همهٔ فایل‌های متنی را با پایانِ سطرِ LF ذخیره می‌کند. روی ویندوز، با
  `core.autocrlf=true`ِ پیش‌فرضِ گیت، نسخهٔ کاری CRLF دارد؛ هشدارِ «CRLF will be replaced by
  LF» طبیعی و بی‌خطر است.
- `core.quotepath false` نام‌های فارسیِ فایل را در `git status` به‌صورتِ متن نشان می‌دهد.
- `core.longpaths true` از سقفِ ۲۶۰ نویسه‌ایِ ویندوز درونِ `_book/` جلوگیری می‌کند.

**فهرستِ بررسیِ پیش از commit:**
1. `python tools/build_all.py` را اجرا کنید. گامِ پایانیِ آن گزارش می‌دهد «the build left the
   git working tree as it found it».
2. `git status` فقط فایل‌های منبعی را نشان می‌دهد که قصدِ تغییرشان را داشتید.
3. commit و push کنید. CI نمودارها را می‌سازد، وب‌سایت و PDF و EPUB را رِندر می‌کند، EPUBِ
   کیندل را می‌سازد، epubcheck را به‌عنوانِ دروازه اجرا می‌کند و وب‌سایت را منتشر می‌کند. این را
   یک بار در *Settings → Pages → Source: GitHub Actions* فعال کنید.

---

## ۹. انتقالِ یک کتاب از نسخهٔ پیشینِ این گردشِ‌کار

قالبِ پیشین فقط HTML و PDF می‌ساخت و متنِ PDFِ آن درست کپی و جست‌وجو نمی‌شد. برای به‌روز کردنِ
یک کتابِ موجود، این‌ها را از قالبِ کنونی روی فایل‌های کتابتان کپی کنید و سپس
`python tools/check_env.py` را اجرا کنید.

| چه چیزی را کپی کنید | چرا |
|---|---|
| `theme/preamble.tex`، `theme/pdf-copytext.lua` | متنِ PDFِ قابلِ کپی و جست‌وجو، نیم‌فاصله، اصلاحِ شمارهٔ صفحه. افزوده‌های خودتان به پیش‌درآمد را دوباره اعمال کنید |
| `theme/epub.css`، `theme/epub-math.lua` | نسخهٔ EPUB |
| `tools/` (کلِ پوشه)، `requirements.txt` | ابزارهای تازهٔ ساخت، بررسی و کیندل؛ سپس `pip install -r requirements.txt` |
| `.github/workflows/build.yml`، `.gitattributes`، `.gitignore` | CI برای همهٔ نسخه‌ها، پایانِ سطرِ LF، پوشه‌های نادیده‌گرفتهٔ تازه |
| `cover/` | نسخه‌های EPUB و کیندل جلد می‌خواهند |

سپس در `_quarto.yml`ِ خودتان این‌ها را از `_quarto.yml`ِ قالب بیفزایید: قلابِ
`project: post-render:`، فیلترِ `theme/epub-math.lua`، `cover-image:`، بلوکِ `language:` و کلِ
بلوکِ قالبِ `epub:`. نمودارهایتان تغییری نمی‌خواهند. اگر فصل‌هایتان ریاضی را در
`[$…$]{.ltr}` پیچیده‌اند، `python tools/source-fixes/unwrap_math_ltr.py` را اجرا کنید (بخشِ
۴٫۳)؛ و پیوندهای میانِ فصل‌ها را از پیوندِ فایل به `@sec-…` برگردانید.
