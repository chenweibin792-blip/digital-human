[CmdletBinding()]
param(
    [string]$AvatarId = 'wav2lip256_avatar1'
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$modelFile = Join-Path $repoRoot 'models\wav2lip.pth'
$avatarRoot = Join-Path $repoRoot ("data\avatars\{0}" -f $AvatarId)
$required = @(
    @{ Name = 'Wav2Lip checkpoint'; Path = $modelFile; Type = 'Leaf' },
    @{ Name = 'Avatar directory'; Path = $avatarRoot; Type = 'Container' },
    @{ Name = 'Avatar coordinates'; Path = (Join-Path $avatarRoot 'coords.pkl'); Type = 'Leaf' },
    @{ Name = 'Avatar full frames'; Path = (Join-Path $avatarRoot 'full_imgs'); Type = 'Container' },
    @{ Name = 'Avatar face frames'; Path = (Join-Path $avatarRoot 'face_imgs'); Type = 'Container' }
)
$missing = 0

Write-Host 'LiveTalking model check' -ForegroundColor Cyan
foreach ($item in $required) {
    $exists = Test-Path -LiteralPath $item.Path -PathType $item.Type
    $label = if ($exists) { 'PASS' } else { 'MISSING' }
    $color = if ($exists) { 'Green' } else { 'Yellow' }
    Write-Host ("[{0}] {1}: {2}" -f $label, $item.Name, $item.Path) -ForegroundColor $color
    if (-not $exists) {
        $missing++
    }
}

if ($missing -eq 0) {
    Write-Host 'Model and avatar checks passed.' -ForegroundColor Green
    exit 0
}

Write-Host ("Model check incomplete: {0} required item(s) missing. These are installed in stage 2." -f $missing) -ForegroundColor Yellow
exit 2
