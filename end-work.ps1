# Manafe3: end a work session on this PC. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
#   powershell -ExecutionPolicy Bypass -File .\end-work.ps1 -Message "What I did"
#   -Next "..."   also replace the "Next task" line in the Last session block (optional)
#   -Footer "..." extra lines at the end of the commit message, e.g. a Co-Authored-By trailer (optional)
#   -DryRun       run the tests and stop: nothing is written, committed or pushed (exit 1 when a test fails)
#   -OnlyTests "test_x*.py"  only these engine test files (negative controls); implies -DryRun
#   -NoCache     solve every building analysis (no test analysis cache). A fully uncached run is REQUIRED before any
#                upstream merge into main and once a week (user decision 2026-11-25).
# Steps: tests (engine: one file at a time, tools/run-tests-by-file.py) -> update HANDOVER.md "Last session" -> git add -> commit -> git push. Nothing is pushed if a test fails.
param([string]$Message, [string]$Next, [string]$Footer, [switch]$DryRun, [string]$OnlyTests, [switch]$NoCache)
if ($OnlyTests) { $DryRun = $true }
$ErrorActionPreference = 'Continue'   # native tools write progress to stderr; exit codes are checked instead
Set-Location -LiteralPath $PSScriptRoot
function Step($t) { Write-Host "`n== $t ==" -ForegroundColor Cyan }

if (-not $Message -and $DryRun) { $Message = 'dry run' }
if (-not $Message) { $Message = Read-Host 'What did you do this session (one line, used as the commit message)' }
if (-not $Message.Trim()) { Write-Host 'A message is needed.' -ForegroundColor Red; exit 1 }

Step 'engine tests (every file on its own, slow included; tools/run-tests-by-file.py)'
# one fresh Python process per test file, analyses serial (MANAFE3_WORKERS=1); it warns first when memory is short
$env:PYTHONIOENCODING = 'utf-8'
# the analysis cache is ON unless -NoCache (the cached = fresh control in test_analysis_cache.py always solves)
$cacheArg = @(); if ($NoCache) { $cacheArg = @('--no-cache') }
if ($OnlyTests) { uv run python tools/run-tests-by-file.py --only $OnlyTests @cacheArg | Tee-Object -Variable pyOut | Out-Host }
else { uv run python tools/run-tests-by-file.py @cacheArg | Tee-Object -Variable pyOut | Out-Host }
$pyRc = $LASTEXITCODE
$pyOk = ($pyRc -eq 0)
$py = ($pyOut | Out-String)
$pyLine = ($py -split "`r?`n" | Where-Object { $_ -match '^engine: ' } | Select-Object -Last 1)
if (-not $pyLine) { $pyLine = 'engine: no summary (the runner did not finish)'; $pyOk = $false }
if ($pyLine -match 'FAILED FILES') { $pyOk = $false }
Write-Host "engine runner exit code: $pyRc"
Step 'app tests (npm test)'
$js = (npm test --silent 2>&1 | Out-String)
$jsOk = ($LASTEXITCODE -eq 0)
$jsLine = ($js -split "`r?`n" | Where-Object { $_ -match 'test files passed' } | Select-Object -Last 1)
Write-Host $jsLine
if (-not ($pyOk -and $jsOk)) {
  Write-Host "`nTESTS FAILED - nothing committed or pushed. Fix the tests first." -ForegroundColor Red
  if (-not $pyOk) { Write-Host $py }
  if (-not $jsOk) { Write-Host (($js -split "`r?`n" | Where-Object { $_ -match 'FAIL' }) -join "`n") }
  exit 1
}
if ($DryRun) { Write-Host "`nDRY RUN: tests passed - nothing written, committed or pushed." -ForegroundColor Green; exit 0 }

Step 'HANDOVER.md last session'
$hand = Join-Path $PSScriptRoot 'HANDOVER.md'
$text = [IO.File]::ReadAllText($hand)
$date = Get-Date -Format 'yyyy-MM-dd HH:mm'
$block = @"
<!-- LAST-SESSION:START (written by end-work.ps1) -->
- When: $date on $env:COMPUTERNAME
- Did: $Message
- Tests: engine $($pyLine.Trim()) | app $($jsLine.Trim())
"@
if ($Next) { $block += "`r`n- Next: $Next" }
$block += "`r`n<!-- LAST-SESSION:END -->"
$re = '(?s)<!-- LAST-SESSION:START.*?<!-- LAST-SESSION:END -->'
if ($text -match $re) { $text = [regex]::Replace($text, $re, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $block }) }
else { $text += "`r`n## Last session`r`n`r`n$block`r`n" }
[IO.File]::WriteAllText($hand, $text, (New-Object Text.UTF8Encoding $false))

Step 'commit and push'
git add -A
# a guard: nothing over 20 MB goes in (client files belong in MANAFE3_PROJECTS_DIR, see .env.local)
$big = git diff --cached --name-only | Where-Object { (Test-Path -LiteralPath $_) -and (Get-Item -LiteralPath $_).Length -gt 20MB }
if ($big) { Write-Host "Refusing: files over 20 MB staged:`n$($big -join "`n")" -ForegroundColor Red; git reset -q; exit 1 }
$msgFile = Join-Path ([IO.Path]::GetTempPath()) ('manafe3-commit-' + [guid]::NewGuid() + '.txt')
[IO.File]::WriteAllText($msgFile, "$Message`n`nend-work.ps1 on $env:COMPUTERNAME. Tests: engine $($pyLine.Trim()); app $($jsLine.Trim())`n" + $(if ($Footer) { "`n$Footer`n" } else { "" }), (New-Object Text.UTF8Encoding $false))
git commit -q -F $msgFile
$c = $LASTEXITCODE
Remove-Item -LiteralPath $msgFile -Force
if ($c -ne 0) { Write-Host 'Nothing to commit.' -ForegroundColor Yellow }
git push
if ($LASTEXITCODE -ne 0) { Write-Host 'git push failed (pull first with start-work.ps1?).' -ForegroundColor Red; exit 1 }
Write-Host "`nPushed. On the other PC run:  .\start-work.ps1" -ForegroundColor Green
