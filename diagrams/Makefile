# Build vector diagrams for the book.
#
#   TikZ figure (.tex)  --LuaLaTeX (babel bidi=basic)-->  big-page PDF
#                       --PyMuPDF crop-->  tight PDF (print) + SVG (web)
#
# The real work lives in tools/build_diagrams.py (cross-platform; needs
# `lualatex` on PATH and Python's PyMuPDF). The figures carry Persian (RTL)
# labels; compiling them with LuaLaTeX + babel `bidi=basic` — the same engine
# as the book body — is what renders the bidi text correctly. See that script
# for the full rationale. (The previous XeLaTeX + dvisvgm route mis-ordered
# multi-line RTL nodes.)
#
# Usage:  make            # build all figures (PDF + SVG)
#         make clean      # remove generated artifacts

PYTHON ?= python3

all:
	$(PYTHON) ../tools/build_diagrams.py

clean:
	rm -f *.aux *.log *.out *.pdf *.svg *.xdv

.PHONY: all clean
