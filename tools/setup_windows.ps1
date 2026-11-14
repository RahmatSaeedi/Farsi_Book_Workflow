<#
.SYNOPSIS
  Prepare a Windows computer to build the book and commit to it.

.DESCRIPTION
  Installs whatever is missing and leaves everything already present alone, so
  it is safe to run again at any time. Run it from a PowerShell window in the
  repository folder:

      powershell -ExecutionPolicy Bypass -File tools\setup_windows.ps1

  What it does (docs\BUILD.md explains each item):
    1. Git, Python 3, Quarto            via winget (if not already installed)
    2. TinyTeX (LuaLaTeX)               quarto install tinytex --update-path
    3. the TeX packages the book needs  tlmgr install <tools\tex-packages.txt>
    4. luaotfload font index that includes the repo's Vazirmatn fonts
    5. Python packages                  pip install -r requirements.txt
    6. portable Java + epubcheck        into .tools\ (no admin rights needed)
    7. optional: Kindle Previewer 4     (-WithKindlePreviewer)
    8. git settings for this repo       quotepath, longpaths, your identity
    9. final check                      python tools\check_env.py

  Options:
    -WithKindlePreviewer       also install Amazon Kindle Previewer 4
    -GitName "Name" -GitEmail "you@example.com"
                               set your global git identity (needed to commit)
    -CheckOnly                 only run the final check

  Only winget installers may ask for administrator approval (Git, Python,
  Quarto). Everything else installs into your user profile or into .tools\.
#>
param(
  [switch]$WithKindlePreviewer,
  [string]$GitName,
  [string]$GitEmail,
  [switch]$CheckOnly
)

# Native tools (tlmgr, pip, winget) write progress to stderr; with 'Stop'
# Windows PowerShell 5.1 would turn that into a terminating error. Exit codes
# are checked explicitly instead.
$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Problems = New-Object System.Collections.Generic.List[string]

function Step([string]$title) {
  Write-Host ''
  Write-Host "=== $title ===" -ForegroundColor Cyan
}

function Refresh-Path {
  # pick up what installers just added, without opening a new window
  $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
  $user = [Environment]::GetEnvironmentVariable('Path', 'User')
  $env:Path = "$machine;$user"
  $tiny = Join-Path $env:APPDATA 'TinyTeX\bin\windows'
  if (Test-Path $tiny) { $env:Path = "$tiny;$env:Path" }
}

function Have([string]$command) {
  return [bool](Get-Command $command -ErrorAction SilentlyContinue)
}

function Winget-Install([string]$id, [string]$what, [string]$manual) {
  if (-not (Have 'winget')) {
    $Problems.Add("$what is missing and winget is not available: install it from $manual")
    return
  }
  Write-Host "installing $what ($id) with winget ..."
  winget install --id $id -e --accept-package-agreements --accept-source-agreements
  if ($LASTEXITCODE -ne 0) {
    $Problems.Add("winget could not install $what (exit $LASTEXITCODE): install it from $manual")
  }
  Refresh-Path
}

function Find-Python {
  # the Microsoft Store stub (WindowsApps\python.exe) is not a real interpreter
  # Returns @{Exe=...; Args=@(...)} (the py launcher needs '-3').
  foreach ($c in @(Get-Command python, py -All -ErrorAction SilentlyContinue)) {
    if ($c.Source -match 'WindowsApps') { continue }
    $extra = @()
    if ($c.Name -notlike 'python*') { $extra = @('-3') }
    $v = & $c.Source @extra -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
    if ($LASTEXITCODE -eq 0 -and $v -and ([version]"$v" -ge [version]'3.10')) {
      return [pscustomobject]@{ Exe = $c.Source; Args = $extra }
    }
  }
  return $null
}

Refresh-Path

if (-not $CheckOnly) {
  Step '1/8 Git, Python, Quarto'
  if (Have 'git') { Write-Host "git: $(git --version)" }
  else { Winget-Install 'Git.Git' 'Git' 'https://git-scm.com/download/win' }

  $Py = Find-Python
  if (-not $Py) {
    Winget-Install 'Python.Python.3.14' 'Python 3.14' 'https://www.python.org/downloads/windows/'
    $Py = Find-Python
  }
  if ($Py) {
    $PyExe = $Py.Exe; $PyArgs = $Py.Args
    Write-Host "python: $(& $PyExe @PyArgs --version) ($PyExe)"
  } else {
    $Problems.Add('no Python 3.10+ found (install it, open a new window, run this again)')
  }

  if (Have 'quarto') { Write-Host "quarto: $(quarto --version)" }
  else { Winget-Install 'Posit.Quarto' 'Quarto' 'https://quarto.org/docs/get-started/' }

  Step '2/8 TinyTeX (LuaLaTeX)'
  if (Have 'lualatex') {
    Write-Host "lualatex: $((lualatex --version | Select-Object -First 1))"
  } elseif (Have 'quarto') {
    quarto install tinytex --update-path --no-prompt
    if ($LASTEXITCODE -ne 0) { $Problems.Add('quarto install tinytex failed') }
    Refresh-Path
  } else {
    $Problems.Add('TinyTeX not installed because Quarto is missing')
  }

  Step '3/8 TeX packages (tools\tex-packages.txt)'
  if (Have 'kpsewhich') {
    $missing = @()
    foreach ($line in Get-Content (Join-Path $Root 'tools\tex-packages.txt')) {
      $fields = ($line -replace '#.*$', '').Trim() -split '\s+'
      if ($fields.Count -lt 2 -or $fields[0] -eq '') { continue }
      $hit = kpsewhich $fields[1] 2>$null
      if (-not $hit) { $missing += $fields[0] }
    }
    if ($missing.Count -eq 0) {
      Write-Host 'all packages present'
    } else {
      Write-Host "installing: $($missing -join ' ')"
      tlmgr update --self
      tlmgr install @missing
      if ($LASTEXITCODE -ne 0) { $Problems.Add("tlmgr install failed for: $($missing -join ' ')") }
    }
  } else {
    $Problems.Add('kpsewhich not found: TeX is not installed or not on PATH')
  }

  Step '4/8 font index (Vazirmatn by name)'
  # The PDF's code font falls back to Vazirmatn for Persian characters; the
  # fallback must resolve the font BY NAME, so the repo's fonts\ folder has to
  # be in luaotfload's index (tools\build_all.py sets OSFONTDIR for every build).
  if (Have 'luaotfload-tool') {
    $env:OSFONTDIR = Join-Path $Root 'fonts'
    $found = luaotfload-tool --find=Vazirmatn 2>&1 | Out-String
    if ($found -match 'Resolved') {
      Write-Host 'Vazirmatn already resolves by name'
    } else {
      Write-Host 'indexing fonts (a few minutes the first time) ...'
      luaotfload-tool --update --force
      if ($LASTEXITCODE -ne 0) { $Problems.Add('luaotfload-tool --update failed') }
    }
  }

  if ($Py) {
    Step '5/8 Python packages (requirements.txt)'
    & $PyExe @PyArgs -m pip install --upgrade pip
    & $PyExe @PyArgs -m pip install -r (Join-Path $Root 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { $Problems.Add('pip install -r requirements.txt failed') }

    Step '6/8 Java + epubcheck (into .tools\)'
    & $PyExe @PyArgs (Join-Path $Root 'tools\verify_epub.py') --install-tools
    if ($LASTEXITCODE -ne 0) { $Problems.Add('could not fetch Java/epubcheck (offline?)') }
  }

  Step '7/8 Kindle Previewer 4 (optional)'
  if ((Have 'kindlepreviewer4') -or (Have 'kpr4')) {
    Write-Host 'already installed'
  } elseif ($WithKindlePreviewer) {
    Winget-Install 'Amazon.KindlePreviewer' 'Kindle Previewer' 'https://kdp.amazon.com/en_US/help/topic/G202131170'
  } else {
    Write-Host 'skipped (add -WithKindlePreviewer to install it)'
  }

  Step '8/8 git settings'
  if (Have 'git') {
    git rev-parse --is-inside-work-tree *> $null
    if ($LASTEXITCODE -eq 0) {
      git config core.quotepath false     # show Persian file names as text
      git config core.longpaths true      # deep paths under _book\site_libs
      Write-Host 'repo: core.quotepath=false, core.longpaths=true'
    } else {
      Write-Host 'this folder is not a git checkout (clone the repository to commit)'
    }
    if ($GitName) { git config --global user.name $GitName }
    if ($GitEmail) { git config --global user.email $GitEmail }
    $name = git config user.name
    $mail = git config user.email
    if ($name -and $mail) { Write-Host "identity: $name <$mail>" }
    else { Write-Host 'identity not set: re-run with -GitName "Your Name" -GitEmail "you@example.com"' -ForegroundColor Yellow }
  }
}

Step 'check'
Refresh-Path
$Py = Find-Python
if (-not $Py) {
  Write-Host 'Python not found; open a new PowerShell window and run this script again.' -ForegroundColor Yellow
  exit 1
}
$PyExe = $Py.Exe; $PyArgs = $Py.Args
& $PyExe @PyArgs (Join-Path $Root 'tools\check_env.py')
$code = $LASTEXITCODE
if ($Problems.Count -gt 0) {
  Write-Host ''
  Write-Host 'Problems during setup:' -ForegroundColor Yellow
  foreach ($p in $Problems) { Write-Host "  - $p" -ForegroundColor Yellow }
  if ($code -eq 0) { $code = 1 }
}
if ($code -eq 0) {
  Write-Host ''
  Write-Host 'Ready. Open a NEW PowerShell window (so PATH changes apply), then:' -ForegroundColor Green
  Write-Host '    python tools\build_all.py' -ForegroundColor Green
}
exit $code
