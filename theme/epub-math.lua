-- theme/epub-math.lua — make the book's TeX math convertible to MathML for EPUB.
--
-- Pandoc's TeX->MathML converter (texmath) covers virtually all of the book, but a
-- handful of amsmath/mathtools commands have no texmath equivalent and would fall
-- back to raw, broken TeX in the e-book. This filter rewrites ONLY those commands,
-- ONLY for EPUB, into texmath-supported forms that render identically. The PDF
-- (LaTeX) and HTML (MathJax) paths are untouched — both handle the originals
-- natively, so the high-fidelity print/web math is never disturbed.
--
-- Cases (found by a full-book EPUB render — re-run it if you add exotic math and
-- watch the log for "Could not convert TeX math" warnings):
--   \xleftrightarrow{A}  ->  \overset{A}{\longleftrightarrow}  (Fourier-transform-pair arrow)
--   \tbinom / \dbinom    ->  \binom                           (texmath lacks the t/d variants)

function Math(el)
  if not FORMAT:match('epub') then return nil end
  local tex = el.text
  -- extensible left-right arrow carrying a label: \xleftrightarrow{LABEL}
  tex = tex:gsub('\\xleftrightarrow%s*(%b{})', '\\overset%1{\\longleftrightarrow}')
  -- text-/display-style binomials texmath does not implement
  tex = tex:gsub('\\tbinom', '\\binom')
  tex = tex:gsub('\\dbinom', '\\binom')
  el.text = tex
  return el
end
