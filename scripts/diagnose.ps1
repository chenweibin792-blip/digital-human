[CmdletBinding()]
param()

$repoRoot = Split-Path -Parent $PSScriptRoot
$shell = (Get-Process -Id $PID).Path

Write-Host '=== LiveTalking diagnostics ===' -ForegroundColor Cyan
Write-Host ("Timestamp: {0}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'))
Write-Host ("Repository: {0}" -f $repoRoot)

Push-Location $repoRoot
try {
    $branch = (& git branch --show-current 2>&1 | Out-String).Trim()
    $commit = (& git rev-parse HEAD 2>&1 | Out-String).Trim()
    Write-Host ("Git branch: {0}" -f $branch)
    Write-Host ("Git commit: {0}" -f $commit)

    Write-Host ''
    & $shell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'check_environment.ps1')
    $environmentExit = $LASTEXITCODE

    Write-Host ''
    & $shell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'check_models.ps1')
    $modelsExit = $LASTEXITCODE
}
finally {
    Pop-Location
}

Write-Host ''
if ($environmentExit -ne 0) {
    Write-Host 'Diagnosis: environment has blocking failures.' -ForegroundColor Red
    exit 1
}
if ($modelsExit -ne 0) {
    Write-Host 'Diagnosis: environment is ready; stage 2 model/avatar files are not ready.' -ForegroundColor Yellow
    exit 2
}

Write-Host 'Diagnosis: ready to start.' -ForegroundColor Green
exit 0
