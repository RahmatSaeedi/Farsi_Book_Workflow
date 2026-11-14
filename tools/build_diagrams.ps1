<#
.SYNOPSIS
  Windows wrapper to build every TikZ figure in diagrams/ to a tight cropped PDF
  (print) and an SVG (web). Thin shim over the cross-platform builder
  tools/build_diagrams.py.

  Pipeline: LuaLaTeX (babel bidi=basic, Renderer=Node) -> big-page PDF
            -> PyMuPDF crop -> tight <base>.pdf + <base>.svg

  The figures carry Persian (RTL) labels mixed with LTR math/code; LuaLaTeX +
  babel `bidi=basic` (the book body's engine) renders the bidi text correctly,
  unlike the old XeLaTeX + `bidi`-package route which mis-ordered multi-line
  RTL nodes. SVGs are outlined glyphs (no <text>), immune to viewer bidi.

.PARAMETER Filter
  Optional wildcard subset, e.g. -Filter '33-*'. Default: all.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools/build_diagrams.ps1
  powershell -ExecutionPolicy Bypass -File tools/build_diagrams.ps1 -Filter '38-*'
#>
[CmdletBinding()]
param([string]$Filter = '*')

# Pick a real CPython (the bare `python` may be the Microsoft Store stub).
$py = $null
foreach ($cmd in @(Get-Command python, python3 -All -ErrorAction SilentlyContinue)) {
  if ($cmd.Source -notmatch 'WindowsApps') { $py = $cmd.Source; break }
}
if (-not $py) { throw "No Python found. Run tools\setup_windows.ps1 (or install Python 3 and: pip install -r requirements.txt)." }

# Make sure TinyTeX's lualatex is reachable.
$tex = Join-Path $env:APPDATA 'TinyTeX\bin\windows'
if (Test-Path $tex) { $env:Path = "$tex;$env:Path" }

& $py (Join-Path $PSScriptRoot 'build_diagrams.py') $Filter
exit $LASTEXITCODE
