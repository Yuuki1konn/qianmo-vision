param(
    [switch]$IncludeTrainingAssets
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot

$safeTargets = @(
    '.android-user',
    '.gradle-user',
    '.venv-export',
    'tmp',
    'android\.gradle',
    'android\build',
    'android\app\build'
)

$trainingTargets = @(
    'data',
    'docs',
    'runs'
)

function Remove-Target {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $fullPath = Join-Path $root $RelativePath
    if (-not (Test-Path -LiteralPath $fullPath)) {
        return
    }

    Write-Host "Removing $RelativePath"
    Remove-Item -LiteralPath $fullPath -Recurse -Force
}

foreach ($target in $safeTargets) {
    Remove-Target -RelativePath $target
}

if ($IncludeTrainingAssets) {
    foreach ($target in $trainingTargets) {
        Remove-Target -RelativePath $target
    }
} else {
    Write-Host 'Kept training assets: data, docs, runs'
    Write-Host 'Pass -IncludeTrainingAssets only after you have backed them up elsewhere.'
}
