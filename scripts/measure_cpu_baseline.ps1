[CmdletBinding()]
param(
    [int]$Port = 8011,
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$envRoot = 'E:\Anaconda\envs\DIGITAL-HUMAN'
$python = Join-Path $envRoot 'python.exe'
$logRoot = 'E:\SZR\.tmp\digital-human-baseline'
$stdoutLog = Join-Path $logRoot 'stdout.log'
$stderrLog = Join-Path $logRoot 'stderr.log'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "DIGITAL-HUMAN Python not found: $python"
}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $Port is already in use."
}

New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$env:PATH = @(
    $envRoot
    (Join-Path $envRoot 'Scripts')
    (Join-Path $envRoot 'Library\bin')
    $env:PATH
) -join [IO.Path]::PathSeparator
$env:TEMP = 'E:\SZR\.tmp'
$env:TMP = 'E:\SZR\.tmp'

$arguments = @(
    'app.py'
    '--transport', 'webrtc'
    '--model', 'wav2lip'
    '--avatar_id', 'wav2lip256_avatar1'
    '--tts', 'edgetts'
    '--listenport', $Port
    '--host', '127.0.0.1'
)

$stopwatch = [Diagnostics.Stopwatch]::StartNew()
$process = Start-Process `
    -FilePath $python `
    -ArgumentList $arguments `
    -WorkingDirectory $repoRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WindowStyle Hidden `
    -PassThru

try {
    $ready = $false
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline -and -not $process.HasExited) {
        Start-Sleep -Milliseconds 500
        try {
            $response = Invoke-WebRequest `
                -Uri "http://127.0.0.1:$Port/index.html" `
                -UseBasicParsing `
                -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        }
        catch {
            # Startup polling is expected to fail until model warm-up completes.
        }
    }
    $stopwatch.Stop()
    $process.Refresh()
    [pscustomobject]@{
        Ready = $ready
        StartupSeconds = [math]::Round($stopwatch.Elapsed.TotalSeconds, 3)
        WorkingSetMB = if (-not $process.HasExited) {
            [math]::Round($process.WorkingSet64 / 1MB, 1)
        } else {
            $null
        }
        Python = (& $python --version 2>&1 | Out-String).Trim()
        Port = $Port
        StderrLog = $stderrLog
    } | ConvertTo-Json

    if (-not $ready) {
        Get-Content -LiteralPath $stderrLog -Tail 40 -ErrorAction SilentlyContinue
        exit 2
    }
}
finally {
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id
        $process.WaitForExit(10000) | Out-Null
    }
}
