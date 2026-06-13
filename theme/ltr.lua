-- theme/ltr.lua — left-to-right "islands" inside RTL Persian text.
--
-- Usage in .qmd:
--   inline:  the field is [B_0]{.ltr} tesla
--   block:   ::: {.ltr}
--            (English paragraph / ASCII diagram)
--            :::
--
-- Output:
--   * HTML  -> adds dir="ltr" (CSS in theme/custom.scss isolates direction)
--   * LaTeX -> wraps inline runs in babel's \babelsublr{...} (bidi=basic) and
--              blocks in \begin{otherlanguage}{english}. Math ($...$) and code
--              already stay LTR automatically.

local function has_ltr(el)
  return el.classes and el.classes:includes('ltr')
end

-- LaTeX side uses babel's \babelsublr{...} (bidi=basic) to force an LTR run.
function Span(el)
  if not has_ltr(el) then return nil end
  if FORMAT:match('latex') then
    local out = pandoc.List({ pandoc.RawInline('latex', '\\babelsublr{') })
    out:extend(el.content)
    out:insert(pandoc.RawInline('latex', '}'))
    return out
  else
    el.attributes['dir'] = 'ltr'
    return el
  end
end

function Div(el)
  if not has_ltr(el) then return nil end
  if FORMAT:match('latex') then
    local out = pandoc.List({ pandoc.RawBlock('latex', '\\begin{otherlanguage}{english}') })
    out:extend(el.content)
    out:insert(pandoc.RawBlock('latex', '\\end{otherlanguage}'))
    return out
  else
    el.attributes['dir'] = 'ltr'
    return el
  end
end

-- Inline `code` is (almost always) English/ASCII: force it LTR in PDF so
-- punctuation isn't reordered. (HTML handles this via CSS in custom.scss.)
function Code(el)
  if FORMAT:match('latex') then
    return { pandoc.RawInline('latex', '\\babelsublr{'), el, pandoc.RawInline('latex', '}') }
  end
  return nil
end

-- Code BLOCKS: wrap the whole block in the LTR `english` language from the
-- OUTSIDE of Pandoc's `Shaded` box, so the block reads left-to-right and
-- left-aligns. Wrapping from outside keeps framed/verbatim balanced.
-- (HTML handles direction via CSS in custom.scss.)
function CodeBlock(el)
  if FORMAT:match('latex') then
    return {
      pandoc.RawBlock('latex', '\\begin{otherlanguage}{english}'),
      el,
      pandoc.RawBlock('latex', '\\end{otherlanguage}'),
    }
  end
  return nil
end
