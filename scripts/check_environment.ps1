[CmdletBinding()]
param(
    [string]$FfmpegPathOverride = '',
    [switch]$SimulateCudaUnavailable,
    [switch]$SkipPortCheck
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectRoot = Split-Path -Parent $repoRoot
$envRoot = Join-Path $projectRoot '.conda\envs\livetalking-local'
$python = Join-Path $envRoot 'python.exe'
$ffmpeg = if ($FfmpegPathOverride) {
    $FfmpegPathOverride
}
else {
    Join-Path $envRoot 'Library\bin\ffmpeg.exe'
}
$failures = 0

function Write-Check {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail
    )
    $label = if ($Passed) { 'PASS' } else { 'FAIL' }
    $color = if ($Passed) { 'Green' } else { 'Red' }
    Write-Host ("[{0}] {1}: {2}" -f $label, $Name, $Detail) -ForegroundColor $color
    if (-not $Passed) {
        $script:failures++
    }
}

Write-Host 'LiveTalking environment check' -ForegroundColor Cyan
Write-Host ("Repository: {0}" -f $repoRoot)
Write-Host ("Environment: {0}" -f $envRoot)

$rootOnE = ([IO.Path]::GetPathRoot($projectRoot) -eq 'E:\')
Write-Check 'Project placement' $rootOnE $projectRoot
Write-Check 'Python executable' (Test-Path -LiteralPath $python -PathType Leaf) $python

if (Test-Path -LiteralPath $python -PathType Leaf) {
    $pythonVersion = (& $python --version 2>&1 | Out-String).Trim()
    Write-Check 'Python runtime' ($LASTEXITCODE -eq 0) $pythonVersion

    if ($SimulateCudaUnavailable) {
        Write-Check 'PyTorch CUDA' $false '{"cuda_available": false, "simulated_test": true}'
    }
    else {
        $cudaProbe = @'
import json
import torch
result = {
    "torch": torch.__version__,
    "compiled_cuda": torch.version.cuda,
    "cuda_available": torch.cuda.is_available(),
}
if torch.cuda.is_available():
    result["device"] = torch.cuda.get_device_name(0)
    result["vram_gib"] = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
    result["probe"] = (torch.ones(1, device="cuda") + 1).cpu().item()
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(0 if result["cuda_available"] else 2)
'@
        $cudaResult = ($cudaProbe | & $python - 2>&1 | Out-String).Trim()
        Write-Check 'PyTorch CUDA' ($LASTEXITCODE -eq 0) $cudaResult
    }
}

Write-Check 'FFmpeg executable' (Test-Path -LiteralPath $ffmpeg -PathType Leaf) $ffmpeg
if (Test-Path -LiteralPath $ffmpeg -PathType Leaf) {
    $ffmpegVersion = (& $ffmpeg -version 2>&1 | Select-Object -First 1 | Out-String).Trim()
    Write-Check 'FFmpeg runtime' ($LASTEXITCODE -eq 0) $ffmpegVersion
}

$nvidiaSmi = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
Write-Check 'NVIDIA driver utility' ($null -ne $nvidiaSmi) $(if ($nvidiaSmi) { $nvidiaSmi.Source } else { 'nvidia-smi.exe not found' })
if ($nvidiaSmi) {
    $gpuInfo = (& $nvidiaSmi.Source --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>&1 | Out-String).Trim()
    Write-Check 'NVIDIA GPU' ($LASTEXITCODE -eq 0) $gpuInfo
}

$portInUse = Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue
if ($SkipPortCheck) {
    Write-Check 'Port 8010 check' $true 'skipped by explicit test flag'
}
else {
    Write-Check 'Port 8010 available' ($null -eq $portInUse) $(if ($portInUse) { 'already listening' } else { 'available' })
}

$drive = Get-PSDrive -Name ([IO.Path]::GetPathRoot($projectRoot).Substring(0, 1))
$freeGiB = [math]::Round($drive.Free / 1GB, 2)
Write-Check 'Free disk space' ($freeGiB -ge 5) ("{0} GiB free on {1}:" -f $freeGiB, $drive.Name)

if ($failures -eq 0) {
    Write-Host 'Environment check passed.' -ForegroundColor Green
    exit 0
}

Write-Host ("Environment check failed: {0} item(s)." -f $failures) -ForegroundColor Red
exit 1
