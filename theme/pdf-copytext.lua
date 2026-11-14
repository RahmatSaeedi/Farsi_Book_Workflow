-- theme/pdf-copytext.lua — make the Persian text of the PDF copy/paste and search
-- correctly in PDF viewers. Loaded from theme/preamble.tex (LuaLaTeX only) with
--   \directlua{dofile("theme/pdf-copytext.lua")}
-- BEFORE the \babelfont lines, so both hooks below are in place when the fonts load.
--
-- The page RENDERS identically with or without this file: nothing here changes
-- glyphs, positions or line breaks. It only changes what a viewer *reads back*.
-- Verify with tools that rasterise both PDFs and diff them (see README).
--
-- Six defects of the plain LuaLaTeX + babel(bidi=basic) + Vazirmatn output are
-- fixed (the third one is a font-feature switch in preamble.tex):
--
-- 1. ToUnicode: presentation forms -> real letters.
--    Vazirmatn maps its contextual glyphs (initial/medial/final forms, lam-alef)
--    to the legacy "Arabic Presentation Forms" code points and names them so
--    (uniFBFE = FARSI YEH INITIAL FORM, ...). luaotfload copies that into the
--    PDF's ToUnicode map, so copied text came out as U+FBFE/U+FE8E... instead of
--    ی/ا: it looks "Arabic"/non-standard, does not match a search for the plain
--    word, and does not reshape when pasted. The `luaotfload.patch_font` hook
--    below rewrites every such entry to its compatibility decomposition (the
--    table PRESFORMS = NFKC for U+FB50-FDFF and U+FE70-FEFF, tatweel dropped),
--    so a copied word is exactly the word that was typed.
--
-- 2. Glyph order: logical -> visual.
--    LuaTeX writes an RTL line into the content stream in LOGICAL order and moves
--    the pen leftwards glyph by glyph. Text extractors (PDF spec 14.8.2.3.3)
--    assume the stream is in VISUAL (left-to-right) order and un-reverse RTL
--    runs themselves; given a logical stream they therefore return the letters
--    REVERSED. PDFium (Chrome / Edge / many apps) and Acrobat do exactly that;
--    XeTeX-made PDFs do not have the problem because XeTeX reverses at shipout.
--    The `pre_shipout_filter` hook below does the same for LuaTeX: every hlist
--    that is TRT (or contains dir nodes) is rebuilt in visual order and turned
--    into a TLT box of the same width, so the backend emits glyphs left-to-right.
--    Zero-width state nodes (colour push/pop, link start/end, save/restore,
--    literals, dests...) are kept semantically in place; a box that cannot be
--    reordered exactly (unbalanced link/colour span that continues on another
--    line, or position-dependent literals inside) is left as LuaTeX made it, so
--    rendering can never be wrong; it merely copies as before. A one-line summary
--    of how many boxes were reordered/left alone is written to the .log.
--
-- 3. ZWNJ (U+200C): two layers dropped it. Pandoc's template makes U+200C active
--    and typesets it as \discretionary{-}{}{\kern.03em} (no glyph at all), and
--    luaotfload's `invisible` feature would replace a ZWNJ glyph by a space glyph
--    + negative kern; either way every "می‌شود" copied as "میشود". preamble.tex
--    redefines \zerowidthnonjoiner to put the real (zero-width) U+200C glyph in
--    the discretionary and passes RawFeature={invisible=8204} to Vazirmatn (which
--    HAS such a glyph), so the ZWNJ reaches the PDF with ToUnicode U+200C.
--    Nothing to do here.
--
-- 4. Combining marks (the kasra of every ezafe, tanvin, shadda, hamza above).
--    A mark is drawn with an x/y offset, hence as a text chunk of its own, and
--    viewers answered with a space or a line break at every one of them: a line
--    came out in fragments, in the wrong order, and no phrase with an ezafe in
--    it could be found. The text of a mark is now carried by a blank zero-width
--    glyph inside the run and its ink is drawn separately (CARRIERS, part 1).
--
-- 5. Spaces. TeX has none (interword glue is just a gap); each viewer guessed
--    them from the geometry, differently. Every interword glue of a rebuilt
--    line is now a real space glyph plus a kern (real_spaces, part 2).
--
-- 6. Mathematical alphanumerics (U+1D400...) read back as the plain letter, so
--    that a formula's "k" or "FOV" can be found and pasted (MATH_RUNS, part 1).
--
-- What a viewer returns still depends on its own bidi handling, as for any
-- Word/Chrome-made Persian PDF, and the engines disagree with each other. The
-- output is tuned on the three that matter on the desktop, measured in the real
-- applications: PDFium (Chrome, Android), the Edge viewer and pdf.js (Firefox).
-- Known limits that cannot be fixed from the PDF side without breaking another
-- engine (visual glyph order is what Edge, pdf.js and MuPDF require):
--   * PDFium has no real bidi algorithm: inside a Persian line it reverses the
--     order of Latin words and of letter/digit groups ("T2" -> "2T", "k-space"
--     -> "space-k", "A B" -> "B A") and breaks the line at super/subscripts;
--   * pdf.js drops ZWNJ (it discards all format characters), puts a space
--     before a word-final mark, and does not mirror brackets (neither does Edge);
--   * pdfminer-style extractors apply no bidi at all and return visual order.

if not (luatexbase and node and font) then return end   -- LuaTeX only

-- ---------------------------------------------------------------------------
-- 1. ToUnicode normalisation
-- ---------------------------------------------------------------------------
-- NFKC of every assigned Arabic Presentation Forms-A/B code point (compatibility
-- decomposition with the tatweel U+0640 dropped from the medial/initial mark
-- forms); each value is a run of 4-hex-digit UTF-16 units, i.e. LuaTeX's
-- `tounicode` format. Generated with Python's unicodedata (see README).
local PRESFORMS = {
  [0xFB50]="0671", [0xFB51]="0671", [0xFB52]="067B", [0xFB53]="067B", [0xFB54]="067B", [0xFB55]="067B",
  [0xFB56]="067E", [0xFB57]="067E", [0xFB58]="067E", [0xFB59]="067E", [0xFB5A]="0680", [0xFB5B]="0680",
  [0xFB5C]="0680", [0xFB5D]="0680", [0xFB5E]="067A", [0xFB5F]="067A", [0xFB60]="067A", [0xFB61]="067A",
  [0xFB62]="067F", [0xFB63]="067F", [0xFB64]="067F", [0xFB65]="067F", [0xFB66]="0679", [0xFB67]="0679",
  [0xFB68]="0679", [0xFB69]="0679", [0xFB6A]="06A4", [0xFB6B]="06A4", [0xFB6C]="06A4", [0xFB6D]="06A4",
  [0xFB6E]="06A6", [0xFB6F]="06A6", [0xFB70]="06A6", [0xFB71]="06A6", [0xFB72]="0684", [0xFB73]="0684",
  [0xFB74]="0684", [0xFB75]="0684", [0xFB76]="0683", [0xFB77]="0683", [0xFB78]="0683", [0xFB79]="0683",
  [0xFB7A]="0686", [0xFB7B]="0686", [0xFB7C]="0686", [0xFB7D]="0686", [0xFB7E]="0687", [0xFB7F]="0687",
  [0xFB80]="0687", [0xFB81]="0687", [0xFB82]="068D", [0xFB83]="068D", [0xFB84]="068C", [0xFB85]="068C",
  [0xFB86]="068E", [0xFB87]="068E", [0xFB88]="0688", [0xFB89]="0688", [0xFB8A]="0698", [0xFB8B]="0698",
  [0xFB8C]="0691", [0xFB8D]="0691", [0xFB8E]="06A9", [0xFB8F]="06A9", [0xFB90]="06A9", [0xFB91]="06A9",
  [0xFB92]="06AF", [0xFB93]="06AF", [0xFB94]="06AF", [0xFB95]="06AF", [0xFB96]="06B3", [0xFB97]="06B3",
  [0xFB98]="06B3", [0xFB99]="06B3", [0xFB9A]="06B1", [0xFB9B]="06B1", [0xFB9C]="06B1", [0xFB9D]="06B1",
  [0xFB9E]="06BA", [0xFB9F]="06BA", [0xFBA0]="06BB", [0xFBA1]="06BB", [0xFBA2]="06BB", [0xFBA3]="06BB",
  [0xFBA4]="06C0", [0xFBA5]="06C0", [0xFBA6]="06C1", [0xFBA7]="06C1", [0xFBA8]="06C1", [0xFBA9]="06C1",
  [0xFBAA]="06BE", [0xFBAB]="06BE", [0xFBAC]="06BE", [0xFBAD]="06BE", [0xFBAE]="06D2", [0xFBAF]="06D2",
  [0xFBB0]="06D3", [0xFBB1]="06D3", [0xFBD3]="06AD", [0xFBD4]="06AD", [0xFBD5]="06AD", [0xFBD6]="06AD",
  [0xFBD7]="06C7", [0xFBD8]="06C7", [0xFBD9]="06C6", [0xFBDA]="06C6", [0xFBDB]="06C8", [0xFBDC]="06C8",
  [0xFBDD]="06C70674", [0xFBDE]="06CB", [0xFBDF]="06CB", [0xFBE0]="06C5", [0xFBE1]="06C5", [0xFBE2]="06C9",
  [0xFBE3]="06C9", [0xFBE4]="06D0", [0xFBE5]="06D0", [0xFBE6]="06D0", [0xFBE7]="06D0", [0xFBE8]="0649",
  [0xFBE9]="0649", [0xFBEA]="06260627", [0xFBEB]="06260627", [0xFBEC]="062606D5", [0xFBED]="062606D5", [0xFBEE]="06260648",
  [0xFBEF]="06260648", [0xFBF0]="062606C7", [0xFBF1]="062606C7", [0xFBF2]="062606C6", [0xFBF3]="062606C6", [0xFBF4]="062606C8",
  [0xFBF5]="062606C8", [0xFBF6]="062606D0", [0xFBF7]="062606D0", [0xFBF8]="062606D0", [0xFBF9]="06260649", [0xFBFA]="06260649",
  [0xFBFB]="06260649", [0xFBFC]="06CC", [0xFBFD]="06CC", [0xFBFE]="06CC", [0xFBFF]="06CC", [0xFC00]="0626062C",
  [0xFC01]="0626062D", [0xFC02]="06260645", [0xFC03]="06260649", [0xFC04]="0626064A", [0xFC05]="0628062C", [0xFC06]="0628062D",
  [0xFC07]="0628062E", [0xFC08]="06280645", [0xFC09]="06280649", [0xFC0A]="0628064A", [0xFC0B]="062A062C", [0xFC0C]="062A062D",
  [0xFC0D]="062A062E", [0xFC0E]="062A0645", [0xFC0F]="062A0649", [0xFC10]="062A064A", [0xFC11]="062B062C", [0xFC12]="062B0645",
  [0xFC13]="062B0649", [0xFC14]="062B064A", [0xFC15]="062C062D", [0xFC16]="062C0645", [0xFC17]="062D062C", [0xFC18]="062D0645",
  [0xFC19]="062E062C", [0xFC1A]="062E062D", [0xFC1B]="062E0645", [0xFC1C]="0633062C", [0xFC1D]="0633062D", [0xFC1E]="0633062E",
  [0xFC1F]="06330645", [0xFC20]="0635062D", [0xFC21]="06350645", [0xFC22]="0636062C", [0xFC23]="0636062D", [0xFC24]="0636062E",
  [0xFC25]="06360645", [0xFC26]="0637062D", [0xFC27]="06370645", [0xFC28]="06380645", [0xFC29]="0639062C", [0xFC2A]="06390645",
  [0xFC2B]="063A062C", [0xFC2C]="063A0645", [0xFC2D]="0641062C", [0xFC2E]="0641062D", [0xFC2F]="0641062E", [0xFC30]="06410645",
  [0xFC31]="06410649", [0xFC32]="0641064A", [0xFC33]="0642062D", [0xFC34]="06420645", [0xFC35]="06420649", [0xFC36]="0642064A",
  [0xFC37]="06430627", [0xFC38]="0643062C", [0xFC39]="0643062D", [0xFC3A]="0643062E", [0xFC3B]="06430644", [0xFC3C]="06430645",
  [0xFC3D]="06430649", [0xFC3E]="0643064A", [0xFC3F]="0644062C", [0xFC40]="0644062D", [0xFC41]="0644062E", [0xFC42]="06440645",
  [0xFC43]="06440649", [0xFC44]="0644064A", [0xFC45]="0645062C", [0xFC46]="0645062D", [0xFC47]="0645062E", [0xFC48]="06450645",
  [0xFC49]="06450649", [0xFC4A]="0645064A", [0xFC4B]="0646062C", [0xFC4C]="0646062D", [0xFC4D]="0646062E", [0xFC4E]="06460645",
  [0xFC4F]="06460649", [0xFC50]="0646064A", [0xFC51]="0647062C", [0xFC52]="06470645", [0xFC53]="06470649", [0xFC54]="0647064A",
  [0xFC55]="064A062C", [0xFC56]="064A062D", [0xFC57]="064A062E", [0xFC58]="064A0645", [0xFC59]="064A0649", [0xFC5A]="064A064A",
  [0xFC5B]="06300670", [0xFC5C]="06310670", [0xFC5D]="06490670", [0xFC5E]="0020064C0651", [0xFC5F]="0020064D0651", [0xFC60]="0020064E0651",
  [0xFC61]="0020064F0651", [0xFC62]="002006500651", [0xFC63]="002006510670", [0xFC64]="06260631", [0xFC65]="06260632", [0xFC66]="06260645",
  [0xFC67]="06260646", [0xFC68]="06260649", [0xFC69]="0626064A", [0xFC6A]="06280631", [0xFC6B]="06280632", [0xFC6C]="06280645",
  [0xFC6D]="06280646", [0xFC6E]="06280649", [0xFC6F]="0628064A", [0xFC70]="062A0631", [0xFC71]="062A0632", [0xFC72]="062A0645",
  [0xFC73]="062A0646", [0xFC74]="062A0649", [0xFC75]="062A064A", [0xFC76]="062B0631", [0xFC77]="062B0632", [0xFC78]="062B0645",
  [0xFC79]="062B0646", [0xFC7A]="062B0649", [0xFC7B]="062B064A", [0xFC7C]="06410649", [0xFC7D]="0641064A", [0xFC7E]="06420649",
  [0xFC7F]="0642064A", [0xFC80]="06430627", [0xFC81]="06430644", [0xFC82]="06430645", [0xFC83]="06430649", [0xFC84]="0643064A",
  [0xFC85]="06440645", [0xFC86]="06440649", [0xFC87]="0644064A", [0xFC88]="06450627", [0xFC89]="06450645", [0xFC8A]="06460631",
  [0xFC8B]="06460632", [0xFC8C]="06460645", [0xFC8D]="06460646", [0xFC8E]="06460649", [0xFC8F]="0646064A", [0xFC90]="06490670",
  [0xFC91]="064A0631", [0xFC92]="064A0632", [0xFC93]="064A0645", [0xFC94]="064A0646", [0xFC95]="064A0649", [0xFC96]="064A064A",
  [0xFC97]="0626062C", [0xFC98]="0626062D", [0xFC99]="0626062E", [0xFC9A]="06260645", [0xFC9B]="06260647", [0xFC9C]="0628062C",
  [0xFC9D]="0628062D", [0xFC9E]="0628062E", [0xFC9F]="06280645", [0xFCA0]="06280647", [0xFCA1]="062A062C", [0xFCA2]="062A062D",
  [0xFCA3]="062A062E", [0xFCA4]="062A0645", [0xFCA5]="062A0647", [0xFCA6]="062B0645", [0xFCA7]="062C062D", [0xFCA8]="062C0645",
  [0xFCA9]="062D062C", [0xFCAA]="062D0645", [0xFCAB]="062E062C", [0xFCAC]="062E0645", [0xFCAD]="0633062C", [0xFCAE]="0633062D",
  [0xFCAF]="0633062E", [0xFCB0]="06330645", [0xFCB1]="0635062D", [0xFCB2]="0635062E", [0xFCB3]="06350645", [0xFCB4]="0636062C",
  [0xFCB5]="0636062D", [0xFCB6]="0636062E", [0xFCB7]="06360645", [0xFCB8]="0637062D", [0xFCB9]="06380645", [0xFCBA]="0639062C",
  [0xFCBB]="06390645", [0xFCBC]="063A062C", [0xFCBD]="063A0645", [0xFCBE]="0641062C", [0xFCBF]="0641062D", [0xFCC0]="0641062E",
  [0xFCC1]="06410645", [0xFCC2]="0642062D", [0xFCC3]="06420645", [0xFCC4]="0643062C", [0xFCC5]="0643062D", [0xFCC6]="0643062E",
  [0xFCC7]="06430644", [0xFCC8]="06430645", [0xFCC9]="0644062C", [0xFCCA]="0644062D", [0xFCCB]="0644062E", [0xFCCC]="06440645",
  [0xFCCD]="06440647", [0xFCCE]="0645062C", [0xFCCF]="0645062D", [0xFCD0]="0645062E", [0xFCD1]="06450645", [0xFCD2]="0646062C",
  [0xFCD3]="0646062D", [0xFCD4]="0646062E", [0xFCD5]="06460645", [0xFCD6]="06460647", [0xFCD7]="0647062C", [0xFCD8]="06470645",
  [0xFCD9]="06470670", [0xFCDA]="064A062C", [0xFCDB]="064A062D", [0xFCDC]="064A062E", [0xFCDD]="064A0645", [0xFCDE]="064A0647",
  [0xFCDF]="06260645", [0xFCE0]="06260647", [0xFCE1]="06280645", [0xFCE2]="06280647", [0xFCE3]="062A0645", [0xFCE4]="062A0647",
  [0xFCE5]="062B0645", [0xFCE6]="062B0647", [0xFCE7]="06330645", [0xFCE8]="06330647", [0xFCE9]="06340645", [0xFCEA]="06340647",
  [0xFCEB]="06430644", [0xFCEC]="06430645", [0xFCED]="06440645", [0xFCEE]="06460645", [0xFCEF]="06460647", [0xFCF0]="064A0645",
  [0xFCF1]="064A0647", [0xFCF2]="064E0651", [0xFCF3]="064F0651", [0xFCF4]="06500651", [0xFCF5]="06370649", [0xFCF6]="0637064A",
  [0xFCF7]="06390649", [0xFCF8]="0639064A", [0xFCF9]="063A0649", [0xFCFA]="063A064A", [0xFCFB]="06330649", [0xFCFC]="0633064A",
  [0xFCFD]="06340649", [0xFCFE]="0634064A", [0xFCFF]="062D0649", [0xFD00]="062D064A", [0xFD01]="062C0649", [0xFD02]="062C064A",
  [0xFD03]="062E0649", [0xFD04]="062E064A", [0xFD05]="06350649", [0xFD06]="0635064A", [0xFD07]="06360649", [0xFD08]="0636064A",
  [0xFD09]="0634062C", [0xFD0A]="0634062D", [0xFD0B]="0634062E", [0xFD0C]="06340645", [0xFD0D]="06340631", [0xFD0E]="06330631",
  [0xFD0F]="06350631", [0xFD10]="06360631", [0xFD11]="06370649", [0xFD12]="0637064A", [0xFD13]="06390649", [0xFD14]="0639064A",
  [0xFD15]="063A0649", [0xFD16]="063A064A", [0xFD17]="06330649", [0xFD18]="0633064A", [0xFD19]="06340649", [0xFD1A]="0634064A",
  [0xFD1B]="062D0649", [0xFD1C]="062D064A", [0xFD1D]="062C0649", [0xFD1E]="062C064A", [0xFD1F]="062E0649", [0xFD20]="062E064A",
  [0xFD21]="06350649", [0xFD22]="0635064A", [0xFD23]="06360649", [0xFD24]="0636064A", [0xFD25]="0634062C", [0xFD26]="0634062D",
  [0xFD27]="0634062E", [0xFD28]="06340645", [0xFD29]="06340631", [0xFD2A]="06330631", [0xFD2B]="06350631", [0xFD2C]="06360631",
  [0xFD2D]="0634062C", [0xFD2E]="0634062D", [0xFD2F]="0634062E", [0xFD30]="06340645", [0xFD31]="06330647", [0xFD32]="06340647",
  [0xFD33]="06370645", [0xFD34]="0633062C", [0xFD35]="0633062D", [0xFD36]="0633062E", [0xFD37]="0634062C", [0xFD38]="0634062D",
  [0xFD39]="0634062E", [0xFD3A]="06370645", [0xFD3B]="06380645", [0xFD3C]="0627064B", [0xFD3D]="0627064B", [0xFD50]="062A062C0645",
  [0xFD51]="062A062D062C", [0xFD52]="062A062D062C", [0xFD53]="062A062D0645", [0xFD54]="062A062E0645", [0xFD55]="062A0645062C", [0xFD56]="062A0645062D",
  [0xFD57]="062A0645062E", [0xFD58]="062C0645062D", [0xFD59]="062C0645062D", [0xFD5A]="062D0645064A", [0xFD5B]="062D06450649", [0xFD5C]="0633062D062C",
  [0xFD5D]="0633062C062D", [0xFD5E]="0633062C0649", [0xFD5F]="06330645062D", [0xFD60]="06330645062D", [0xFD61]="06330645062C", [0xFD62]="063306450645",
  [0xFD63]="063306450645", [0xFD64]="0635062D062D", [0xFD65]="0635062D062D", [0xFD66]="063506450645", [0xFD67]="0634062D0645", [0xFD68]="0634062D0645",
  [0xFD69]="0634062C064A", [0xFD6A]="06340645062E", [0xFD6B]="06340645062E", [0xFD6C]="063406450645", [0xFD6D]="063406450645", [0xFD6E]="0636062D0649",
  [0xFD6F]="0636062E0645", [0xFD70]="0636062E0645", [0xFD71]="06370645062D", [0xFD72]="06370645062D", [0xFD73]="063706450645", [0xFD74]="06370645064A",
  [0xFD75]="0639062C0645", [0xFD76]="063906450645", [0xFD77]="063906450645", [0xFD78]="063906450649", [0xFD79]="063A06450645", [0xFD7A]="063A0645064A",
  [0xFD7B]="063A06450649", [0xFD7C]="0641062E0645", [0xFD7D]="0641062E0645", [0xFD7E]="06420645062D", [0xFD7F]="064206450645", [0xFD80]="0644062D0645",
  [0xFD81]="0644062D064A", [0xFD82]="0644062D0649", [0xFD83]="0644062C062C", [0xFD84]="0644062C062C", [0xFD85]="0644062E0645", [0xFD86]="0644062E0645",
  [0xFD87]="06440645062D", [0xFD88]="06440645062D", [0xFD89]="0645062D062C", [0xFD8A]="0645062D0645", [0xFD8B]="0645062D064A", [0xFD8C]="0645062C062D",
  [0xFD8D]="0645062C0645", [0xFD8E]="0645062E062C", [0xFD8F]="0645062E0645", [0xFD92]="0645062C062E", [0xFD93]="06470645062C", [0xFD94]="064706450645",
  [0xFD95]="0646062D0645", [0xFD96]="0646062D0649", [0xFD97]="0646062C0645", [0xFD98]="0646062C0645", [0xFD99]="0646062C0649", [0xFD9A]="06460645064A",
  [0xFD9B]="064606450649", [0xFD9C]="064A06450645", [0xFD9D]="064A06450645", [0xFD9E]="0628062E064A", [0xFD9F]="062A062C064A", [0xFDA0]="062A062C0649",
  [0xFDA1]="062A062E064A", [0xFDA2]="062A062E0649", [0xFDA3]="062A0645064A", [0xFDA4]="062A06450649", [0xFDA5]="062C0645064A", [0xFDA6]="062C062D0649",
  [0xFDA7]="062C06450649", [0xFDA8]="0633062E0649", [0xFDA9]="0635062D064A", [0xFDAA]="0634062D064A", [0xFDAB]="0636062D064A", [0xFDAC]="0644062C064A",
  [0xFDAD]="06440645064A", [0xFDAE]="064A062D064A", [0xFDAF]="064A062C064A", [0xFDB0]="064A0645064A", [0xFDB1]="06450645064A", [0xFDB2]="06420645064A",
  [0xFDB3]="0646062D064A", [0xFDB4]="06420645062D", [0xFDB5]="0644062D0645", [0xFDB6]="06390645064A", [0xFDB7]="06430645064A", [0xFDB8]="0646062C062D",
  [0xFDB9]="0645062E064A", [0xFDBA]="0644062C0645", [0xFDBB]="064306450645", [0xFDBC]="0644062C0645", [0xFDBD]="0646062C062D", [0xFDBE]="062C062D064A",
  [0xFDBF]="062D062C064A", [0xFDC0]="0645062C064A", [0xFDC1]="06410645064A", [0xFDC2]="0628062D064A", [0xFDC3]="064306450645", [0xFDC4]="0639062C0645",
  [0xFDC5]="063506450645", [0xFDC6]="0633062E064A", [0xFDC7]="0646062C064A", [0xFDF0]="0635064406D2", [0xFDF1]="0642064406D2", [0xFDF2]="0627064406440647",
  [0xFDF3]="0627064306280631", [0xFDF4]="0645062D0645062F", [0xFDF5]="0635064406390645", [0xFDF6]="0631063306480644", [0xFDF7]="06390644064A0647", [0xFDF8]="0648063306440645",
  [0xFDF9]="063506440649", [0xFDFA]="06350644064900200627064406440647002006390644064A064700200648063306440645", [0xFDFB]="062C06440020062C0644062706440647", [0xFDFC]="063106CC06270644", [0xFE70]="0020064B", [0xFE71]="064B",
  [0xFE72]="0020064C", [0xFE74]="0020064D", [0xFE76]="0020064E", [0xFE77]="064E", [0xFE78]="0020064F", [0xFE79]="064F",
  [0xFE7A]="00200650", [0xFE7B]="0650", [0xFE7C]="00200651", [0xFE7D]="0651", [0xFE7E]="00200652", [0xFE7F]="0652",
  [0xFE80]="0621", [0xFE81]="0622", [0xFE82]="0622", [0xFE83]="0623", [0xFE84]="0623", [0xFE85]="0624",
  [0xFE86]="0624", [0xFE87]="0625", [0xFE88]="0625", [0xFE89]="0626", [0xFE8A]="0626", [0xFE8B]="0626",
  [0xFE8C]="0626", [0xFE8D]="0627", [0xFE8E]="0627", [0xFE8F]="0628", [0xFE90]="0628", [0xFE91]="0628",
  [0xFE92]="0628", [0xFE93]="0629", [0xFE94]="0629", [0xFE95]="062A", [0xFE96]="062A", [0xFE97]="062A",
  [0xFE98]="062A", [0xFE99]="062B", [0xFE9A]="062B", [0xFE9B]="062B", [0xFE9C]="062B", [0xFE9D]="062C",
  [0xFE9E]="062C", [0xFE9F]="062C", [0xFEA0]="062C", [0xFEA1]="062D", [0xFEA2]="062D", [0xFEA3]="062D",
  [0xFEA4]="062D", [0xFEA5]="062E", [0xFEA6]="062E", [0xFEA7]="062E", [0xFEA8]="062E", [0xFEA9]="062F",
  [0xFEAA]="062F", [0xFEAB]="0630", [0xFEAC]="0630", [0xFEAD]="0631", [0xFEAE]="0631", [0xFEAF]="0632",
  [0xFEB0]="0632", [0xFEB1]="0633", [0xFEB2]="0633", [0xFEB3]="0633", [0xFEB4]="0633", [0xFEB5]="0634",
  [0xFEB6]="0634", [0xFEB7]="0634", [0xFEB8]="0634", [0xFEB9]="0635", [0xFEBA]="0635", [0xFEBB]="0635",
  [0xFEBC]="0635", [0xFEBD]="0636", [0xFEBE]="0636", [0xFEBF]="0636", [0xFEC0]="0636", [0xFEC1]="0637",
  [0xFEC2]="0637", [0xFEC3]="0637", [0xFEC4]="0637", [0xFEC5]="0638", [0xFEC6]="0638", [0xFEC7]="0638",
  [0xFEC8]="0638", [0xFEC9]="0639", [0xFECA]="0639", [0xFECB]="0639", [0xFECC]="0639", [0xFECD]="063A",
  [0xFECE]="063A", [0xFECF]="063A", [0xFED0]="063A", [0xFED1]="0641", [0xFED2]="0641", [0xFED3]="0641",
  [0xFED4]="0641", [0xFED5]="0642", [0xFED6]="0642", [0xFED7]="0642", [0xFED8]="0642", [0xFED9]="0643",
  [0xFEDA]="0643", [0xFEDB]="0643", [0xFEDC]="0643", [0xFEDD]="0644", [0xFEDE]="0644", [0xFEDF]="0644",
  [0xFEE0]="0644", [0xFEE1]="0645", [0xFEE2]="0645", [0xFEE3]="0645", [0xFEE4]="0645", [0xFEE5]="0646",
  [0xFEE6]="0646", [0xFEE7]="0646", [0xFEE8]="0646", [0xFEE9]="0647", [0xFEEA]="0647", [0xFEEB]="0647",
  [0xFEEC]="0647", [0xFEED]="0648", [0xFEEE]="0648", [0xFEEF]="0649", [0xFEF0]="0649", [0xFEF1]="064A",
  [0xFEF2]="064A", [0xFEF3]="064A", [0xFEF4]="064A", [0xFEF5]="06440622", [0xFEF6]="06440622", [0xFEF7]="06440623",
  [0xFEF8]="06440623", [0xFEF9]="06440625", [0xFEFA]="06440625", [0xFEFB]="06440627", [0xFEFC]="06440627",
}

-- Persian convention used throughout the book (and ISIRI 6219): "ۀ" is HEH +
-- HAMZA ABOVE (U+0647 U+0654). Vazirmatn's ccmp composes that pair into its
-- uni06C0 glyph, whose ToUnicode would be U+06C0; map it back so the copied
-- text equals the source.
local CANONICAL = { ["06C0"] = "06470654" }

-- Mathematical alphanumerics -> the plain letter (NFKC). A math font names the
-- italic k of a formula U+1D458 "MATHEMATICAL ITALIC SMALL K", a character
-- outside the BMP: copied text is then unsearchable ("FOV" typed on a keyboard
-- never matches the styled letters), many programs cannot display it, and
-- PDFium (Chrome) tears its two UTF-16 halves apart when the formula sits in a
-- right-to-left line, pasting U+FFFD boxes. { first, count, first target }.
local MATH_RUNS = {
  {0x1D400,26,0x41}, {0x1D41A,26,0x61}, {0x1D434,26,0x41}, {0x1D44E,7,0x61}, {0x1D456,18,0x69},
  {0x1D468,26,0x41}, {0x1D482,26,0x61}, {0x1D49C,1,0x41}, {0x1D49E,2,0x43}, {0x1D4A2,1,0x47},
  {0x1D4A5,2,0x4A}, {0x1D4A9,4,0x4E}, {0x1D4AE,8,0x53}, {0x1D4B6,4,0x61}, {0x1D4BB,1,0x66},
  {0x1D4BD,7,0x68}, {0x1D4C5,11,0x70}, {0x1D4D0,26,0x41}, {0x1D4EA,26,0x61}, {0x1D504,2,0x41},
  {0x1D507,4,0x44}, {0x1D50D,8,0x4A}, {0x1D516,7,0x53}, {0x1D51E,26,0x61}, {0x1D538,2,0x41},
  {0x1D53B,4,0x44}, {0x1D540,5,0x49}, {0x1D546,1,0x4F}, {0x1D54A,7,0x53}, {0x1D552,26,0x61},
  {0x1D56C,26,0x41}, {0x1D586,26,0x61}, {0x1D5A0,26,0x41}, {0x1D5BA,26,0x61}, {0x1D5D4,26,0x41},
  {0x1D5EE,26,0x61}, {0x1D608,26,0x41}, {0x1D622,26,0x61}, {0x1D63C,26,0x41}, {0x1D656,26,0x61},
  {0x1D670,26,0x41}, {0x1D68A,26,0x61}, {0x1D6A4,1,0x131}, {0x1D6A5,1,0x237}, {0x1D6A8,17,0x391},
  {0x1D6B9,1,0x398}, {0x1D6BA,7,0x3A3}, {0x1D6C1,1,0x2207}, {0x1D6C2,25,0x3B1}, {0x1D6DB,1,0x2202},
  {0x1D6DC,1,0x3B5}, {0x1D6DD,1,0x3B8}, {0x1D6DE,1,0x3BA}, {0x1D6DF,1,0x3C6}, {0x1D6E0,1,0x3C1},
  {0x1D6E1,1,0x3C0}, {0x1D6E2,17,0x391}, {0x1D6F3,1,0x398}, {0x1D6F4,7,0x3A3}, {0x1D6FB,1,0x2207},
  {0x1D6FC,25,0x3B1}, {0x1D715,1,0x2202}, {0x1D716,1,0x3B5}, {0x1D717,1,0x3B8}, {0x1D718,1,0x3BA},
  {0x1D719,1,0x3C6}, {0x1D71A,1,0x3C1}, {0x1D71B,1,0x3C0}, {0x1D71C,17,0x391}, {0x1D72D,1,0x398},
  {0x1D72E,7,0x3A3}, {0x1D735,1,0x2207}, {0x1D736,25,0x3B1}, {0x1D74F,1,0x2202}, {0x1D750,1,0x3B5},
  {0x1D751,1,0x3B8}, {0x1D752,1,0x3BA}, {0x1D753,1,0x3C6}, {0x1D754,1,0x3C1}, {0x1D755,1,0x3C0},
  {0x1D756,17,0x391}, {0x1D767,1,0x398}, {0x1D768,7,0x3A3}, {0x1D76F,1,0x2207}, {0x1D770,25,0x3B1},
  {0x1D789,1,0x2202}, {0x1D78A,1,0x3B5}, {0x1D78B,1,0x3B8}, {0x1D78C,1,0x3BA}, {0x1D78D,1,0x3C6},
  {0x1D78E,1,0x3C1}, {0x1D78F,1,0x3C0}, {0x1D790,17,0x391}, {0x1D7A1,1,0x398}, {0x1D7A2,7,0x3A3},
  {0x1D7A9,1,0x2207}, {0x1D7AA,25,0x3B1}, {0x1D7C3,1,0x2202}, {0x1D7C4,1,0x3B5}, {0x1D7C5,1,0x3B8},
  {0x1D7C6,1,0x3BA}, {0x1D7C7,1,0x3C6}, {0x1D7C8,1,0x3C1}, {0x1D7C9,1,0x3C0}, {0x1D7CA,2,0x3DC},
  {0x1D7CE,10,0x30}, {0x1D7D8,10,0x30}, {0x1D7E2,10,0x30}, {0x1D7EC,10,0x30}, {0x1D7F6,10,0x30},
}
local function math_plain(cp)
  if cp == 0x210E then return 0x68 end            -- PLANCK CONSTANT = the italic h
  if cp < 0x1D400 or cp > 0x1D7FF then return nil end
  for _, r in ipairs(MATH_RUNS) do
    if cp >= r[1] and cp < r[1] + r[2] then return r[3] + (cp - r[1]) end
  end
  return nil
end

-- Arabic-script code points (the blocks Vazirmatn's Persian glyphs live in).
local function is_arabic(cp)
  return (cp >= 0x0600 and cp <= 0x06FF) or (cp >= 0x0750 and cp <= 0x077F)
      or (cp >= 0x08A0 and cp <= 0x08FF) or (cp >= 0xFB50 and cp <= 0xFDFF)
      or (cp >= 0xFE70 and cp <= 0xFEFF)
end

-- Split a tounicode string into code points (surrogate pairs kept together).
local function units(hex)
  local cps = {}
  local i, n = 1, #hex
  while i + 3 <= n do
    local u = tonumber(hex:sub(i, i + 3), 16)
    if u >= 0xD800 and u <= 0xDBFF and i + 7 <= n then
      cps[#cps + 1] = hex:sub(i, i + 7); i = i + 8
    else
      cps[#cps + 1] = hex:sub(i, i + 3); i = i + 4
    end
  end
  return cps
end

local function normalize_tounicode(hex)
  if type(hex) ~= "string" or #hex % 4 ~= 0 then return hex end
  local out = {}
  for _, unit in ipairs(units(hex)) do
    unit = unit:upper()
    local cp = tonumber(unit:sub(1, 4), 16)
    if #unit == 8 then
      cp = 0x10000 + (cp - 0xD800) * 0x400 + (tonumber(unit:sub(5, 8), 16) - 0xDC00)
    end
    local plain = math_plain(cp)
    if plain then
      out[#out + 1] = string.format("%04X", plain)
    else
      local rep = PRESFORMS[cp] or unit
      for _, u in ipairs(units(rep)) do
        for _, v in ipairs(units(CANONICAL[u] or u)) do out[#out + 1] = v end
      end
    end
  end
  -- A glyph standing for SEVERAL characters (lam-alef, heh+hamza, fatha+shadda)
  -- must list them in VISUAL order: the content stream is emitted in visual
  -- order (part 2 below) and extractors un-reverse the whole RTL run, the
  -- expansion included. Latin ligatures (ff, fi) keep their logical order.
  if #out > 1 and is_arabic(tonumber(out[1]:sub(1, 4), 16)) then
    local rev = {}
    for i = #out, 1, -1 do rev[#rev + 1] = out[i] end
    out = rev
  end
  return table.concat(out)
end

local function patch_font(tfmdata)
  local chars = tfmdata and tfmdata.characters
  if not chars then return end
  for slot, chr in pairs(chars) do
    local tu = chr.tounicode
    if tu == nil then
      -- no explicit map: the backend would use the slot number itself
      if type(slot) == "number" and slot < 0x10000 then
        local hex = string.format("%04X", slot)
        if PRESFORMS[slot] or CANONICAL[hex] or math_plain(slot) then
          chr.tounicode = normalize_tounicode(hex)
        end
      elseif type(slot) == "number" then
        local plain = math_plain(slot)
        if plain then chr.tounicode = string.format("%04X", plain) end
      end
    else
      -- also covers ligature glyphs whose expansion luaotfload derived itself
      local fixed = normalize_tounicode(tu)
      if fixed ~= tu then chr.tounicode = fixed end
    end
  end
end

-- Combining marks (kasra of the ezafe, tanvin, shadda, hamza above...) are the
-- one thing a viewer cannot read back reliably: the shaper places each of them
-- with an x/y offset, the backend therefore writes it as a text chunk of its own
-- at a shifted origin, and every extractor then applies its geometry heuristics
-- to that chunk ("far from the previous glyph: insert a space", "other
-- baseline: start a new line"). Copied text came out with a space before every
-- kasra or with a line break in the middle of the line, and no phrase
-- containing an ezafe could be found.
-- So the *text* of a mark and its *ink* are separated (part 2 below):
--   * the text is carried by a blank zero-width glyph of the same font, put in
--     the run right next to the base with no offset at all. CARRIERS pairs each
--     mark with such a glyph (format controls the book never typesets) and the
--     glyph's ToUnicode is set to the mark;
--   * the ink is the real mark glyph, drawn exactly where it always was, but
--     moved to the START of its line in stream order, where no word can be
--     disturbed by it. Its ToUnicode becomes INK, a ZERO WIDTH SPACE: pdf.js
--     (Firefox) drops such format characters, and Edge, which would attach a
--     real space to the neighbouring line and push the last letter of that
--     line onto a line of its own, leaves the text alone. For PDFium the marks
--     are wrapped in a marked-content span it skips (MARK_OPEN below).
-- LRM/RLM (U+200E/F) are left alone. A mark without a carrier (the font's
-- stacked forms, the rarer marks) is written before its base, as in part 2.
local CARRIERS = {
  { 0x0650, 0x200B },   -- kasra (every ezafe)
  { 0x064E, 0x200D },   -- fatha
  { 0x064F, 0x202A },   -- damma
  { 0x064B, 0x202B },   -- fathatan (tanvin)
  { 0x0651, 0x202C },   -- shadda
  { 0x0654, 0x202D },   -- hamza above
  { 0x0652, 0x202E },   -- sukun
  { 0x064D, 0xFEFF },   -- kasratan
}
local INK = "200B"

local function add_carriers(tfmdata)
  local chars = tfmdata and tfmdata.characters
  if not chars then return end
  local map
  for _, pair in ipairs(CARRIERS) do
    local mark, blank = chars[pair[1]], chars[pair[2]]
    if mark and blank and (mark.width or 0) == 0 and (blank.width or 0) == 0
       and (blank.height or 0) == 0 and (blank.depth or 0) == 0 then
      blank.tounicode = string.format("%04X", pair[1])
      mark.tounicode = INK
      map = map or {}
      map[pair[1]] = pair[2]
    end
  end
  tfmdata.pdfcopytext_carriers = map
end

luatexbase.add_to_callback("luaotfload.patch_font", function(tfmdata)
  patch_font(tfmdata)
  add_carriers(tfmdata)
end, "pdf-copytext.tounicode")

-- ---------------------------------------------------------------------------
-- 2. Visual-order glyph streams
-- ---------------------------------------------------------------------------
local node_id, traverse = node.id, node.traverse
local HLIST, VLIST, RULE, GLUE, KERN, MATH, GLYPH, DISC, DIR, WHATSIT, MARGIN_KERN =
  node_id("hlist"), node_id("vlist"), node_id("rule"), node_id("glue"), node_id("kern"),
  node_id("math"), node_id("glyph"), node_id("disc"), node_id("dir"), node_id("whatsit"),
  node_id("margin_kern")

local W = {}
for num, name in pairs(node.whatsits()) do W[name] = num end
local START_LINK, END_LINK, COLORSTACK, SAVE, RESTORE, ANNOT =
  W.pdf_start_link, W.pdf_end_link, W.pdf_colorstack, W.pdf_save, W.pdf_restore, W.pdf_annot
-- whatsits whose *position* matters (they draw or record where the pen is):
-- a box containing one at top level is left alone.
local POSITIONAL = {}
for _, name in ipairs { "pdf_literal", "pdf_late_literal", "special", "late_special", "late_lua", "save_pos" } do
  if W[name] then POSITIONAL[W[name]] = true end
end

local stats = { boxes = 0, reordered = 0, literal = 0, unbalanced = 0, carried = 0, spaces = 0 }
-- The deferred mark glyphs (see CARRIERS) are wrapped in a marked-content
-- span whose replacement text is a lone TAB: PDFium (Chrome, Android) then
-- skips them altogether instead of reading each as a stray character on a
-- line of its own (it honours /ActualText, and drops a span whose text has
-- nothing printable).
local MARK_OPEN, MARK_CLOSE
if W.pdf_literal then
  local function literal(data)
    local n = node.new(WHATSIT, W.pdf_literal)
    n.mode, n.data = 1, data      -- 1 = "page": outside any text object
    return n
  end
  MARK_OPEN = literal("/Span<</ActualText<FEFF0009>>>BDC")
  MARK_CLOSE = literal("EMC")
end
local DEBUG = os.getenv("PDFCOPYTEXT_DEBUG") ~= nil   -- log every skipped box

-- item:       occupies width (glyph, rule, box, glue, kern, math, annot): reordered
-- open/close: bracket pair whose interior is reordered but whose markers stay
--             around it in stream order (dir nodes, links, colour push/pop,
--             save/restore)
-- marker:     zero-width state (dest, colour set, setmatrix, penalties, ...):
--             attached to the item that follows it (or to the group's end)
local function classify(n)
  local id = n.id
  if id == GLYPH or id == RULE or id == HLIST or id == VLIST or id == GLUE
     or id == KERN or id == MARGIN_KERN or id == MATH or id == DISC then
    return "item"
  elseif id == DIR then
    return n.dir:sub(1, 1) == "+" and "open" or "close"
  elseif id == WHATSIT then
    local st = n.subtype
    if st == START_LINK or st == SAVE then return "open" end
    if st == END_LINK or st == RESTORE then return "close" end
    if st == COLORSTACK then
      local c = n.command   -- 0 set, 1 push, 2 pop, 3 current
      if c == 1 then return "open" elseif c == 2 then return "close" end
      return "marker"
    end
    if st == ANNOT then return "item" end
    if POSITIONAL[st] then return "positional" end
    return "marker"
  end
  return "marker"
end

local function matches(open, close)
  if open.id == DIR then return close.id == DIR and open.dir:sub(2) == close.dir:sub(2) end
  if open.id ~= WHATSIT or close.id ~= WHATSIT then return false end
  local o, c = open.subtype, close.subtype
  if o == START_LINK then return c == END_LINK end
  if o == SAVE then return c == RESTORE end
  if o == COLORSTACK then return c == COLORSTACK and open.stack == close.stack end
  return false
end

-- A combining mark (kasra, shadda, hamza above...) is a zero-width glyph that
-- luaotfload attached to the glyph before it with xoffset/yoffset. Detected via
-- the font's GDEF class, falling back to "zero width with an offset".
local mark_cache = {}
local function is_mark(n)
  if n.width ~= 0 then return false end
  local key = n.font .. ":" .. n.char
  local r = mark_cache[key]
  if r == nil then
    local tf = font.getfont(n.font)
    local descs = tf and tf.shared and tf.shared.rawdata and tf.shared.rawdata.descriptions
    local d = descs and descs[n.char]
    r = (d ~= nil and d.class == "mark") or false
    mark_cache[key] = r
  end
  return r or (n.xoffset ~= 0 or n.yoffset ~= 0)
end

-- Synthetic bracket nodes, needed when a link/colour span and a direction run
-- overlap without nesting (Quarto's "Equation 2.4": the link opens inside the
-- LTR run and closes just after it). The span is then split at the run
-- boundary into two properly nested spans: same colours, two link rectangles
-- covering the same glyphs.
local function synthetic_close(open)
  if open.id == WHATSIT then
    local st = open.subtype
    if st == START_LINK then return node.new(WHATSIT, END_LINK) end
    if st == SAVE then return node.new(WHATSIT, RESTORE) end
    if st == COLORSTACK then
      local c = node.new(WHATSIT, COLORSTACK)
      c.stack, c.command, c.data = open.stack, 2, ""
      return c
    end
  end
  return nil
end

local function copy_open(open)
  local c = node.copy(open)
  if open.id == WHATSIT and open.subtype == START_LINK then
    -- each link node owns one annotation object; the copy needs its own
    c.objnum = pdf.reserveobj("annot")
  end
  return c
end

-- Parse a node list into a tree of items and bracket groups. Returns
-- root, has_dir; or nil, reason when the list cannot be reordered exactly
-- (a span that continues on another line, a position-dependent literal).
local function parse(head)
  local root = { items = {}, dirgroup = true }
  local stack, pending, has_dir = { root }, {}, false
  local created, discard = {}, {}

  local function fail(reason)
    for _, c in ipairs(created) do node.free(c) end
    return nil, reason
  end

  -- glue and kerns carry no ink: a colour marker may move across them exactly.
  -- So may it across an EMPTY box (the paragraph-indent box that starts a
  -- caption line: KOMA pushes the caption colour right after it and pops it
  -- after the paragraph, so without this every figure/table caption was left
  -- in logical order and copied reversed).
  local function is_ink(e)
    if e.n then
      local id = e.n.id
      if (id == HLIST or id == VLIST) and not e.n.head then return false end
      return id ~= GLUE and id ~= KERN and id ~= MARGIN_KERN
    end
    return true   -- a group (dir/link/colour): treat as content
  end

  local function open_group(n, reopened)
    local g = { open = n, items = {}, pre = pending, reopened = reopened }
    pending = {}
    if n.id == DIR then g.dirgroup, g.rtl, has_dir = true, (n.dir == "+TRT"), true end
    local top = stack[#stack]
    top.items[#top.items + 1] = g
    stack[#stack + 1] = g
    return g
  end

  local function close_top(n)
    local g = stack[#stack]
    if g.reopened and #g.items == 0 then
      -- a continued span that ends at once: nothing inside, drop both markers
      local parent = stack[#stack - 1]
      parent.items[#parent.items] = nil
      local merged = {}
      for _, m in ipairs(g.pre) do merged[#merged + 1] = m end
      for _, m in ipairs(pending) do merged[#merged + 1] = m end
      pending = merged
      if g.open then discard[#discard + 1] = g.open end
      discard[#discard + 1] = n
    else
      g.post, g.close = pending, n
      pending = {}
    end
    stack[#stack] = nil
  end

  for n in traverse(head) do
    local kind = classify(n)
    local top = stack[#stack]
    if kind == "positional" then
      return fail("literal")
    elseif kind == "item" then
      if root.sealed == "strict" or (root.sealed and n.id ~= GLUE and n.id ~= KERN and n.id ~= MARGIN_KERN) then
        return fail("unbalanced")
      end
      local last = top.items[#top.items]
      if n.id == GLYPH and #pending == 0 and last and last.n and last.n.id == GLYPH and is_mark(n) then
        -- keep the mark glued to its base: emitted right after it, whatever the direction
        last.marks = last.marks or {}
        last.marks[#last.marks + 1] = n
      else
        top.items[#top.items + 1] = { n = n, pre = pending }
        pending = {}
      end
    elseif kind == "marker" then
      pending[#pending + 1] = n
    elseif kind == "open" then
      if root.sealed then return fail("unbalanced") end
      open_group(n, false)
    else -- close
      if root.sealed and n.id ~= DIR then return fail("unbalanced") end
      if n.id ~= DIR then
        local open_brackets = false
        for k = 2, #stack do if not stack[k].dirgroup then open_brackets = true end end
        if not open_brackets then
          -- A pop/end whose open lives in an earlier box (KOMA's ToC entries push a
          -- colour in the page-number box and pop it in the title box). Exact as
          -- long as no content follows it in this box: it is then emitted last,
          -- after everything it covered, just like in the original stream.
          root.trailing = root.trailing or {}
          root.trailing[#root.trailing + 1] = n
          -- a link/restore end must be the very last thing (its rectangle would
          -- otherwise grow); a colour pop may be followed by ink-less glue/kerns
          if root.sealed ~= "strict" then
            root.sealed = (n.subtype == COLORSTACK) and "colour" or "strict"
          end
          goto continue
        end
      end
      if #stack == 1 then return fail("unbalanced") end
      if matches(top.open or top.open_src, n) then
        close_top(n)
      else
        local j
        for k = #stack, 2, -1 do
          if matches(stack[k].open or stack[k].open_src, n) then j = k; break end
        end
        if not j then return fail("unbalanced") end
        if n.id == DIR then
          -- The run ends while spans opened inside it are still open: end them
          -- here and continue them after the run.
          local reopen = {}
          while #stack > j do
            local g = stack[#stack]
            if g.dirgroup then return fail("unbalanced") end
            if #g.items == 0 then
              -- nothing inside the run: the span really starts after it
              local parent = stack[#stack - 1]
              parent.items[#parent.items] = nil
              local merged = {}
              for _, m in ipairs(g.pre) do merged[#merged + 1] = m end
              for _, m in ipairs(pending) do merged[#merged + 1] = m end
              pending = merged
              stack[#stack] = nil
              reopen[#reopen + 1] = { src = g.open, move = true }
            else
              local sc = synthetic_close(g.open)
              if not sc then return fail("unbalanced") end
              created[#created + 1] = sc
              reopen[#reopen + 1] = { src = g.open }
              close_top(sc)
            end
          end
          close_top(n)
          for k = #reopen, 1, -1 do
            local r = reopen[k]
            if r.move then
              open_group(r.src, false)          -- the original marker, just later
            else
              local g = open_group(r.src, true) -- a copy, made only if it gets content
              g.open, g.open_src = nil, r.src
            end
          end
        else
          -- A span ends inside run(s) that opened after it: end the span before
          -- the run and continue it inside, around what the run holds so far.
          local idx = j
          while idx < #stack do
            local M, I, parent = stack[idx], stack[idx + 1], stack[idx - 1]
            local src = M.open or M.open_src
            M.items[#M.items] = nil            -- I was M's last item
            local Mc
            if #M.items == 0 then
              -- the span holds nothing before the run: it simply starts inside it
              parent.items[#parent.items] = nil  -- M was the parent's last item
              for _, m in ipairs(M.pre) do I.pre[#I.pre + 1] = m end
              Mc = { open = M.open, open_src = M.open_src, items = I.items, pre = {}, reopened = M.reopened }
            else
              local sc = synthetic_close(src)
              if not sc then return fail("unbalanced") end
              created[#created + 1] = sc
              M.close, M.post = sc, {}
              Mc = { open_src = src, items = I.items, pre = {}, reopened = true }
            end
            parent.items[#parent.items + 1] = I -- I now follows (or replaces) M in the parent
            I.items = { Mc }
            stack[idx], stack[idx + 1] = I, Mc
            idx = idx + 1
          end
          close_top(n)
        end
      end
    end
    ::continue::
  end
  -- Spans still open at the end are exact only when they started at the very
  -- beginning of the box (their close lives in a later box): emitted first,
  -- they cover everything, as in the original stream. Anything else is a span
  -- that genuinely continues on another line: leave the box alone.
  for k = 2, #stack do
    local g, parent = stack[k], stack[k - 1]
    if g.dirgroup then return fail("unbalanced") end
    local colour = (g.open or g.open_src).subtype == COLORSTACK
    for _, e in ipairs(parent.items) do
      if e == g then break end
      if not colour or is_ink(e) then return fail("unbalanced") end
    end
  end
  root.post = pending
  root.discard = discard
  return root, has_dir
end

-- font id -> { [mark slot] = carrier slot } (false: none)
local carrier_cache = {}
local function carriers_of(fid)
  local c = carrier_cache[fid]
  if c == nil then
    local tf = font.getfont(fid)
    c = (tf and tf.pdfcopytext_carriers) or false
    carrier_cache[fid] = c
  end
  return c
end

-- Visible marks waiting to be drawn: { anchor = node at whose position the
-- pen is at the base's left edge, mark = the glyph }. A "stretch" is a part of
-- the line with one graphics state: it ends at anything that changes the state
-- (colour, link, any whatsit). The marks of a stretch are drawn at its START
-- (a { flush = list } entry put into `out` there), so a mark keeps its colour,
-- stays inside its link and never sits between two words of the text.
local deferred = {}
local stretch_start = 1          -- index in `out` where the current stretch began
local function flush_deferred(out)
  if #deferred > 0 then
    table.insert(out, stretch_start, { flush = deferred })
    deferred = {}
  end
end
-- call right after a state-changing node has been appended to `out`
local function new_stretch(out) stretch_start = #out + 1 end

local emit_group

local function has_whatsit(list)
  for _, m in ipairs(list) do
    if m.id == WHATSIT then return true end
  end
  return false
end

local function emit_entry(e, rtl, out, drop)
  if has_whatsit(e.pre) then
    flush_deferred(out)
    for _, m in ipairs(e.pre) do out[#out + 1] = m end
    new_stretch(out)
  else
    for _, m in ipairs(e.pre) do out[#out + 1] = m end
  end
  if e.n then
    local n = e.n
    -- LuaTeX's backend MIRRORS a glyph's xoffset in a right-to-left run
    -- (pos.h -= xoffset), and luaotfload positions marks (kasra, hamza...)
    -- with that in mind. The run is emitted left-to-right from now on, so
    -- flip the offset to keep every mark where it was.
    if rtl and n.id == GLYPH and n.xoffset ~= 0 then n.xoffset = -n.xoffset end
    if e.marks and rtl then
      -- Visual order means the WHOLE run is mirrored, marks included: a mark
      -- comes BEFORE its base in the stream (what HarfBuzz/Skia/Word emit), so
      -- that an extractor reversing the run gets "base, mark" again. In the RTL
      -- box the mark sat at (base's left edge - xoffset); the pen of the TLT box
      -- is at the base's left edge when the mark is emitted, so just flip it.
      -- With a carrier (see CARRIERS) the text goes here and the ink is deferred.
      local cmap = carriers_of(n.font)
      for i = #e.marks, 1, -1 do
        local m = e.marks[i]
        m.xoffset = -m.xoffset
        local slot = cmap and m.font == n.font and cmap[m.char]
        if slot then
          local c = node.copy(m)            -- the text: blank, zero width, no offset
          c.char, c.xoffset, c.yoffset = slot, 0, 0
          out[#out + 1] = c
          deferred[#deferred + 1] = { anchor = c, mark = m }   -- the ink: later
          stats.carried = stats.carried + 1
        else
          out[#out + 1] = m
        end
      end
      out[#out + 1] = n
    else
      out[#out + 1] = n
      if e.marks then
        for _, m in ipairs(e.marks) do out[#out + 1] = m end
      end
    end
  elseif e.dirgroup then
    -- the whole box becomes TLT: the dir nodes go away, only the order they
    -- implied survives
    drop[#drop + 1] = e.open
    drop[#drop + 1] = e.close
    emit_group(e, e.rtl, out, drop)
  else
    if not e.open then e.open = copy_open(e.open_src) end   -- continuation of a split span
    flush_deferred(out)
    out[#out + 1] = e.open
    new_stretch(out)
    emit_group(e, rtl, out, drop)
    flush_deferred(out)
    if e.close then out[#out + 1] = e.close end            -- nil: closed in a later box
    new_stretch(out)
  end
end

function emit_group(g, rtl, out, drop)
  local items = g.items
  if rtl then
    for i = #items, 1, -1 do emit_entry(items[i], rtl, out, drop) end
  else
    for i = 1, #items do emit_entry(items[i], rtl, out, drop) end
  end
  if g.post and #g.post > 0 then
    local state = has_whatsit(g.post)
    if state then flush_deferred(out) end
    for _, m in ipairs(g.post) do out[#out + 1] = m end
    if state then new_stretch(out) end
  end
end

-- TeX has no space characters: the gap between two words is glue, and a viewer
-- has to guess from the size of the gap whether a space was meant (too tight a
-- line: words run together; a zero-width glyph next to the gap: the space lands
-- on the wrong side of it). So every interword glue of a rebuilt line is
-- replaced by a real space glyph of the neighbouring font plus a kern for the
-- rest of the gap: same width to the scaled point, but the space is now text.
local SPACESKIP, XSPACESKIP = 13, 14
local space_cache = {}
local function space_width(fid)
  local w = space_cache[fid]
  if w == nil then
    local tf = font.getfont(fid)
    local c = tf and tf.characters and tf.characters[32]
    -- only a real glyph of an OpenType font (TeX's 8-bit fonts have no space)
    w = (c and c.index and c.width and c.width > 0 and tf.format ~= "type1" and c.width) or false
    space_cache[fid] = w
  end
  return w
end

local function round(x) return math.floor(x + 0.5) end

local function real_spaces(out, box)
  local gs, sign, order = box.glue_set, box.glue_sign, box.glue_order
  -- font of the nearest glyph: the one before in the stream, else the one after
  local nextfont, f = {}, nil
  for i = #out, 1, -1 do
    local n = out[i]
    if type(n) ~= "table" and n.id == GLYPH then f = n.font end
    nextfont[i] = f
  end
  local res, prevfont = {}, nil
  for i = 1, #out do
    local n = out[i]
    if type(n) == "table" then
      res[#res + 1] = n
    elseif n.id == GLYPH then
      prevfont = n.font
      res[#res + 1] = n
    elseif n.id == GLUE and (n.subtype == SPACESKIP or n.subtype == XSPACESKIP) and not n.leader then
      local fid = prevfont or nextfont[i]
      local sw = fid and space_width(fid)
      if sw then
        local w = n.width
        if sign == 1 and n.stretch_order == order then
          w = w + round(n.stretch * gs)
        elseif sign == 2 and n.shrink_order == order then
          w = w - round(n.shrink * gs)
        end
        if w ~= sw then
          local k = node.new(KERN)
          k.kern = w - sw
          res[#res + 1] = k
        end
        local g = node.new(GLYPH)
        g.subtype, g.font, g.char = 256, fid, 32
        g.attr = n.attr
        res[#res + 1] = g
        node.free(n)
        stats.spaces = stats.spaces + 1
      else
        res[#res + 1] = n
      end
    else
      res[#res + 1] = n
    end
  end
  return res
end

-- Replace the { flush = ... } entries of `out` by the marks they hold. Each
-- mark is reached with a kern from wherever the pen is, drawn at the place it
-- had next to its base, and the pen is put back: nothing moves on the page.
local function place_deferred(out, box)
  local nodes, flushes = {}, {}
  for i = 1, #out do
    local o = out[i]
    if type(o) == "table" then
      flushes[#flushes + 1] = { at = #nodes + 1, list = o.flush }   -- before nodes[at]
    else
      nodes[#nodes + 1] = o
    end
  end
  if #flushes == 0 then return out end
  for i = 1, #nodes do
    nodes[i].prev = nodes[i - 1]
    nodes[i].next = nodes[i + 1]
  end
  -- x position (from the start of the list) of every node we need
  local want = {}
  for _, f in ipairs(flushes) do
    for _, d in ipairs(f.list) do want[d.anchor] = true end
    if nodes[f.at] then want[nodes[f.at]] = true end
  end
  local gs, sign, order = box.glue_set, box.glue_sign, box.glue_order
  local xpos, x, from = {}, 0, nodes[1]
  for i = 1, #nodes do
    local n = nodes[i]
    if want[n] then
      if n ~= from then x = x + node.dimensions(gs, sign, order, from, n) end
      xpos[n], from = x, n
    end
  end
  local xend = x + node.dimensions(gs, sign, order, from)
  local final, fi = {}, 1
  for i = 1, #nodes + 1 do
    while flushes[fi] and flushes[fi].at == i do
      local pen = nodes[i] and xpos[nodes[i]] or xend
      local cur = pen
      local function move(to)
        if to ~= cur then
          local k = node.new(KERN)
          k.kern = to - cur
          final[#final + 1] = k
          cur = to
        end
      end
      if MARK_OPEN then final[#final + 1] = node.copy(MARK_OPEN) end
      for _, d in ipairs(flushes[fi].list) do
        move(xpos[d.anchor])
        final[#final + 1] = d.mark
      end
      move(pen)
      if MARK_CLOSE then final[#final + 1] = node.copy(MARK_CLOSE) end
      fi = fi + 1
    end
    if nodes[i] then final[#final + 1] = nodes[i] end
  end
  return final
end

local flatten = node.flatten_discretionaries

local process_list

local function process_hlist(box)
  local head = box.head
  if not head then return end
  if flatten then
    -- unbroken discretionaries still sit in the line as nodes; the backend
    -- would draw their `replace` list in box direction, so inline it first
    head = flatten(head)
    box.head = head
  end
  process_list(head)              -- nested boxes first (independent of ours)
  stats.boxes = stats.boxes + 1
  local rtl = (box.dir == "TRT")
  local root, info = parse(head)
  if not root then
    if rtl or info == "literal" then stats[info] = stats[info] + 1 end
    if DEBUG then
      local parts = {}
      for n in traverse(head) do
        if n.id == WHATSIT then
          local nm = node.whatsits()[n.subtype] or n.subtype
          local data = (n.data and type(n.data) == "string") and n.data:sub(1, 60):gsub("%s+", " ") or ""
          parts[#parts + 1] = nm .. (data ~= "" and ("[" .. data .. "]") or "")
        elseif n.id == GLYPH then parts[#parts + 1] = utf8.char(n.char < 0xF0000 and n.char or 0xFFFD)
        elseif n.id == DIR then parts[#parts + 1] = n.dir
        elseif n.id == HLIST or n.id == VLIST then parts[#parts + 1] = "{box}"
        elseif n.id == GLUE then parts[#parts + 1] = "_"
        elseif n.id == KERN or n.id == MARGIN_KERN then parts[#parts + 1] = "k"
        end
      end
      texio.write_nl("log", "pdf-copytext DEBUG skipped(" .. tostring(info) .. ", dir=" .. tostring(box.dir) .. "): " .. table.concat(parts, " "):sub(1, 400))
    end
    return
  end
  if not rtl and not info then return end   -- plain LTR box: nothing to do
  root.rtl = rtl
  local out, drop = {}, {}
  deferred, stretch_start = {}, 1
  emit_group(root, rtl, out, drop)
  flush_deferred(out)
  if root.trailing then for _, t in ipairs(root.trailing) do out[#out + 1] = t end end
  if #out == 0 then return end
  if rtl then
    -- The backend lays a TRT box's content out leftwards from its RIGHT edge,
    -- a TLT box's rightwards from its LEFT edge. Those coincide only when the
    -- set content width equals the box width. When they differ (a table cell
    -- spanning columns: TeX gives it the first column's width but sets its glue
    -- for the whole span; an overfull line; \hbox to X{} without glue) the
    -- overhang would flip sides, so start the content where it used to be.
    local content = node.dimensions(box.glue_set, box.glue_sign, box.glue_order, head)
    local delta = box.width - content
    if delta ~= 0 then
      local k = node.new(KERN)
      k.kern = delta
      table.insert(out, 1, k)
      if DEBUG and math.abs(delta) > 655 then   -- > 0.01pt
        local sig = {}
        for n in traverse(head) do
          if n.id == GLYPH then sig[#sig + 1] = utf8.char(n.char < 0xF0000 and n.char or 0xFFFD)
          elseif n.id == GLUE then sig[#sig + 1] = "_"
          elseif n.id == HLIST or n.id == VLIST then sig[#sig + 1] = "{" .. node.type(n.id) .. ":" .. tostring(n.dir) .. "}"
          elseif n.id == KERN or n.id == MARGIN_KERN then sig[#sig + 1] = "k"
          elseif n.id == WHATSIT then sig[#sig + 1] = "<" .. tostring(node.whatsits()[n.subtype]) .. ">"
          else sig[#sig + 1] = "<" .. node.type(n.id) .. ">" end
        end
        texio.write_nl("log", string.format("pdf-copytext DEBUG compensation %.3fpt (box %.2fpt sub=%d gs=%.3f sign=%d): %s",
          delta / 65536, box.width / 65536, box.subtype, box.glue_set, box.glue_sign, table.concat(sig, " "):sub(1, 300)))
      end
    end
  end
  out = real_spaces(out, box)
  out = place_deferred(out, box)
  for i = 1, #out do
    local n = out[i]
    n.prev = out[i - 1]
    n.next = out[i + 1]
  end
  box.head = out[1]
  box.dir = "TLT"
  for _, d in ipairs(drop) do if d then node.free(d) end end
  for _, d in ipairs(root.discard) do node.free(d) end
  stats.reordered = stats.reordered + 1
end

function process_list(head)
  for n in traverse(head) do
    local id = n.id
    if id == HLIST then
      process_hlist(n)
    elseif id == VLIST then
      process_list(n.head)
    elseif id == GLUE and n.leader then
      local l = n.leader
      if l.id == HLIST then process_hlist(l) elseif l.id == VLIST then process_list(l.head) end
    end
  end
end

luatexbase.add_to_callback("pre_shipout_filter", function(box)
  if box then
    if box.id == HLIST then process_hlist(box)
    elseif box.id == VLIST then process_list(box.head) end
  end
  return box
end, "pdf-copytext.visual-order")

luatexbase.add_to_callback("finish_pdffile", function()
  texio.write_nl("log", string.format(
    "pdf-copytext: %d hlists seen, %d rebuilt in visual order, %d left as is "
    .. "(%d with position-dependent literals, %d with a link/colour span continuing "
    .. "on another line); %d combining marks carried inline, %d interword spaces "
    .. "written as space glyphs.",
    stats.boxes, stats.reordered, stats.literal + stats.unbalanced, stats.literal, stats.unbalanced,
    stats.carried, stats.spaces))
end, "pdf-copytext.report")
