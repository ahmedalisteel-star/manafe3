# Manafe3: start a work session on this PC. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
#   powershell -ExecutionPolicy Bypass -File .\start-work.ps1          (or .\start-work.ps1 if scripts are allowed)
#   -SkipTests   pull and sync only
# Steps: git pull -> uv sync -> tests (engine pytest + npm test) -> print the current task from HANDOVER.md.
param([switch]$SkipTests)
$ErrorActionPreference = 'Continue'   # native tools write progress to stderr; exit codes are checked instead
Set-Location -LiteralPath $PSScriptRoot

function Step($t) { Write-Host "`n== $t ==" -ForegroundColor Cyan }

Step 'git pull'
git pull --ff-only
if ($LASTEXITCODE -ne 0) { Write-Host 'git pull failed (local changes or a diverged branch?). Fix that first.' -ForegroundColor Red; exit 1 }

if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.env.local'))) {
  Write-Host '.env.local is missing on this PC: copy .env.local.example to .env.local and fill in the folders.' -ForegroundColor Yellow
}

Step 'uv sync'
uv sync
if ($LASTEXITCODE -ne 0) { Write-Host 'uv sync failed.' -ForegroundColor Red; exit 1 }

$failed = $false
if (-not $SkipTests) {
  Step 'engine tests (pytest, fast set: -m "not slow" - end-work.ps1 runs everything)'
  uv run pytest -q -m "not slow"
  if ($LASTEXITCODE -ne 0) { $failed = $true }
  Step 'app tests (npm test)'
  npm test --silent
  if ($LASTEXITCODE -ne 0) { $failed = $true }
}

Step 'current task (HANDOVER.md)'
$lines = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'HANDOVER.md') -Encoding UTF8
$in = $false
foreach ($l in $lines) {
  if ($l -match '^## ') { if ($in) { break }; if ($l -match '^## Next task') { $in = $true } }
  if ($in) { Write-Host $l }
}

if ($failed) { Write-Host "`nTESTS FAILED - fix them before new work." -ForegroundColor Red; exit 1 }
Write-Host "`nReady. Start the app with:  python manafe3.py" -ForegroundColor Green
