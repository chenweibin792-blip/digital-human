[CmdletBinding()]
param(
    [int]$Port = 8010,
    [string]$AvatarId = 'wav2lip256_avatar1',
    [switch]$Lan,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArguments
)

$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $repoRoot
$envRoot = Join-Path $projectRoot '.conda\envs\livetalking-local'
$python = Join-Path $envRoot 'python.exe'
$shell = (Get-Process -Id $PID).Path

& $shell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot 'scripts\check_environment.ps1')
if ($LASTEXITCODE -ne 0) {
    throw 'Environment check failed. Run scripts\diagnose.ps1 for details.'
}

& $shell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot 'scripts\check_models.ps1') -AvatarId $AvatarId
if ($LASTEXITCODE -ne 0) {
    throw 'Model/avatar check failed. Complete stage 2 before starting LiveTalking.'
}

$env:PIP_CACHE_DIR = Join-Path $projectRoot '.cache\pip'
$env:HF_HOME = Join-Path $projectRoot '.cache\huggingface'
$env:TEMP = Join-Path $projectRoot '.tmp'
$env:TMP = Join-Path $projectRoot '.tmp'
$env:PATH = @(
    $envRoot
    (Join-Path $envRoot 'Scripts')
    (Join-Path $envRoot 'Library\bin')
    $env:PATH
) -join [IO.Path]::PathSeparator

$dotenv = Join-Path $repoRoot '.env'
if (Test-Path -LiteralPath $dotenv -PathType Leaf) {
    foreach ($line in Get-Content -LiteralPath $dotenv -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#') -or -not $trimmed.Contains('=')) {
            continue
        }
        $name, $value = $trimmed.Split('=', 2)
        $name = $name.Trim()
        $value = $value.Trim().Trim('"').Trim("'")
        if ($name -match '^[A-Za-z_][A-Za-z0-9_]*$') {
            [Environment]::SetEnvironmentVariable($name, $value, 'Process')
        }
    }
    Write-Host 'Loaded project .env (values hidden).' -ForegroundColor DarkGray
}

if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw ("Port {0} is already in use." -f $Port)
}

$bindHost = '127.0.0.1'
if ($Lan) {
    $bindHost = '0.0.0.0'
}
$url = "http://127.0.0.1:$Port/index.html"
$arguments = @(
    'app.py'
    '--model', 'wav2lip'
    '--avatar_id', $AvatarId
    '--tts', 'edgetts'
    '--transport', 'webrtc'
    '--listenport', $Port
    '--host', $bindHost
) + $AppArguments

Write-Host ("Starting LiveTalking from {0}" -f $repoRoot) -ForegroundColor Cyan
Write-Host ("Browser address: {0}" -f $url) -ForegroundColor Green
if ($Lan) {
    $localIp = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias '*Wi-Fi*','*Ethernet*' -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike '169.254.*' } |
        Select-Object -First 1 -ExpandProperty IPAddress
    if ($localIp) {
        Write-Host ("LAN address: http://{0}:{1}/index.html" -f $localIp, $Port) -ForegroundColor Yellow
    }
    Write-Host 'LAN mode is enabled explicitly. Allow the port in Windows Firewall if required.' -ForegroundColor Yellow
}
Write-Host 'Press Ctrl+C to stop.'

Push-Location $repoRoot
try {
    & $python @arguments
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
