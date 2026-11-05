# Manafe3: end a work session on this PC. Copyright (c) 2026 Ahmed Ali. All rights reserved.
#   powershell -ExecutionPolicy Bypass -File .\end-work.ps1 -Message "What I did"
#   -Next "..."   also replace the "Next task" line in the Last session block (optional)
#   -Footer "..." extra lines at the end of the commit message, e.g. a Co-Authored-By trailer (optional)
# Steps: tests -> update HANDOVER.md "Last session" -> git add -> commit -> git push. Nothing is pushed if a test fails.
param([string]$Message, [string]$Next, [string]$Footer)
$ErrorActionPreference = 'Continue'   # native tools write progress to stderr; exit codes are checked instead
Set-Location -LiteralPath $PSScriptRoot
function Step($t) { Write-Host "`n== $t ==" -ForegroundColor Cyan }

if (-not $Message) { $Message = Read-Host 'What did you do this session (one line, used as the commit message)' }
if (-not $Message.Trim()) { Write-Host 'A message is needed.' -ForegroundColor Red; exit 1 }

Step 'engine tests (pytest)'
$py = (uv run pytest -q 2>&1 | Out-String)
$pyOk = ($LASTEXITCODE -eq 0)
$pyLine = ($py -split "`r?`n" | Where-Object { $_ -match '\d+ (passed|failed)' } | Select-Object -Last 1)
Write-Host $pyLine
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
