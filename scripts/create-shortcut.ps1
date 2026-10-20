[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$launcher = Join-Path $repoRoot 'START-MULTITRACK.bat'
$icon = Join-Path $repoRoot 'resources\icons\multitrack.ico'
foreach ($requiredPath in @($launcher, $icon)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required local file not found: $requiredPath"
    }
}

$shortcutPath = Join-Path $repoRoot 'MultiTrack.lnk'
$shortcutShell = New-Object -ComObject WScript.Shell
$shortcut = $shortcutShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcher
$shortcut.WorkingDirectory = $repoRoot
$shortcut.IconLocation = "$icon,0"
$shortcut.Description = 'Abrir MultiTrack'
$shortcut.WindowStyle = 7
$shortcut.Save()

$legacyShortcutPath = Join-Path $repoRoot 'StemLab.lnk'
if (Test-Path -LiteralPath $legacyShortcutPath -PathType Leaf) {
    $legacyShortcut = $shortcutShell.CreateShortcut($legacyShortcutPath)
    if ($legacyShortcut.TargetPath -eq (Join-Path $repoRoot 'START-STEMLAB.bat')) {
        Remove-Item -LiteralPath $legacyShortcutPath
    }
}

Write-Host "MultiTrack shortcut created: $shortcutPath"
