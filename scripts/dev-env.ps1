[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$localPaths = [ordered]@{
    TEMP                      = Join-Path $repoRoot '.tmp'
    TMP                       = Join-Path $repoRoot '.tmp'
    PIP_CACHE_DIR             = Join-Path $repoRoot '.cache\pip'
    TORCH_HOME                = Join-Path $repoRoot '.cache\torch'
    HF_HOME                   = Join-Path $repoRoot '.cache\huggingface'
    XDG_CACHE_HOME            = Join-Path $repoRoot '.cache'
    MPLCONFIGDIR              = Join-Path $repoRoot '.cache\matplotlib'
    AUDIO_SEPARATOR_MODEL_DIR = Join-Path $repoRoot 'models'
}

foreach ($path in ($localPaths.Values | Select-Object -Unique)) {
    New-Item -ItemType Directory -Force -Path $path | Out-Null
}

foreach ($entry in $localPaths.GetEnumerator()) {
    [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
}
$env:PYTHONUTF8 = '1'

$activateScript = Join-Path $repoRoot '.venv\Scripts\Activate.ps1'
if (Test-Path -LiteralPath $activateScript) {
    $bundledPython = Join-Path $repoRoot 'tools\python312\python.exe'
    & $bundledPython -X utf8 (Join-Path $repoRoot 'scripts\repair-local-runtime.py')
    if ($LASTEXITCODE -ne 0) {
        throw 'MultiTrack local runtime repair failed.'
    }
    . $activateScript
    Write-Host "MultiTrack environment active: $env:VIRTUAL_ENV"
} else {
    Write-Warning "MultiTrack .venv not found at $(Join-Path $repoRoot '.venv')."
}

# Apply tool paths after virtualenv activation because Activate.ps1 may restore
# a previously saved PATH when this script is dot-sourced more than once.
$ffmpegBin = Join-Path $repoRoot 'tools\ffmpeg\bin'
if (Test-Path -LiteralPath $ffmpegBin) {
    $pathSeparator = [string][IO.Path]::PathSeparator
    $normalizedFfmpegBin = $ffmpegBin.TrimEnd('\', '/')
    $existingPathEntries = @(
        $env:PATH -split [regex]::Escape($pathSeparator) |
            Where-Object {
                $_ -and $_.TrimEnd('\', '/') -ine $normalizedFfmpegBin
            }
    )
    $env:PATH = (@($ffmpegBin) + $existingPathEntries) -join $pathSeparator
}

Write-Host "MultiTrack repository: $repoRoot"
