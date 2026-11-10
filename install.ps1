<#
.SYNOPSIS
  Install the oral-video-packager skill for WorkBuddy on Windows.
.EXAMPLE
  .\install.ps1
  .\install.ps1 -Project
  .\install.ps1 -Force
#>
param(
    [switch]$Project,
    [string]$Dir,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$Repo = 'https://github.com/ZeyZhang/oral-video-packager.git'
$Name = 'oral-video-packager'

if ($Dir) {
    $Root = $Dir
} elseif ($Project) {
    $Root = Join-Path (Get-Location).Path '.workbuddy\skills'
} else {
    $Root = Join-Path $env:USERPROFILE '.workbuddy\skills'
}
$Target = Join-Path $Root $Name

function Test-Cmd($n) {
    return $null -ne (Get-Command $n -ErrorAction SilentlyContinue)
}

Write-Host '== Checking dependencies =='
$missing = @()
foreach ($c in @('git', 'ffmpeg', 'ffprobe', 'python')) {
    if (Test-Cmd $c) {
        Write-Host "  [OK]   $c"
    } else {
        Write-Host "  [MISS] $c"
        $missing += $c
    }
}
if ($missing.Count -gt 0) {
    Write-Host "Missing required tools: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "Remotion backend also needs Node 18+ and 'npm install' inside remotion/."
    exit 1
}
& python -c "import PIL" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Missing Python package Pillow. Run: pip install Pillow' -ForegroundColor Red
    exit 1
} else {
    Write-Host '  [OK]   Pillow'
}

if ((Test-Path $Target) -and (Get-ChildItem $Target -Force | Select-Object -First 1)) {
    if (-not $Force) {
        Write-Host "Target already exists: $Target" -ForegroundColor Yellow
        Write-Host 'Re-run with -Force to replace (a backup will be created).'
        exit 1
    }
    $bak = "$Target.bak-$(Get-Date -Format yyyyMMddHHmmss)"
    Move-Item -Path $Target -Destination $bak
    Write-Host "Backup created: $bak"
}

$tmp = Join-Path $env:TEMP "ovp-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
try {
    Write-Host '== Cloning public repository =='
    & git clone --depth 1 $Repo (Join-Path $tmp 'src')
    if ($LASTEXITCODE -ne 0) { throw 'git clone failed' }

    Write-Host "== Installing to $Target =="
    New-Item -ItemType Directory -Path $Target -Force | Out-Null
    Copy-Item -Path (Join-Path $tmp 'src\*') -Destination $Target -Recurse -Force

    foreach ($p in @('.git', 'remotion\node_modules', 'remotion\out', '__pycache__', 'scripts\__pycache__')) {
        $full = Join-Path $Target $p
        if (Test-Path $full) { Remove-Item $full -Recurse -Force }
    }
    Get-ChildItem $Target -Recurse -Filter '*.pyc' -ErrorAction SilentlyContinue | Remove-Item -Force

    if (-not (Test-Path (Join-Path $Target 'SKILL.md'))) {
        throw 'SKILL.md not found after install'
    }

    Write-Host "Installed to: $Target" -ForegroundColor Green
    Write-Host 'Next steps:'
    Write-Host '  1. Open a NEW WorkBuddy conversation (new skills load on new sessions)'
    Write-Host "  2. Copy $Target\assets\config.example.json to myconfig.json"
    Write-Host '  3. Replace source / reference / output / workdir paths and person fields'
    Write-Host "  4. python $Target\scripts\package_video.py --config myconfig.json"
}
finally {
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue }
}
