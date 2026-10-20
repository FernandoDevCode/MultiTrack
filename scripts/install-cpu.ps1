# Windows PowerShell 5.1 is included in supported Windows 10/11 systems.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
function Get-Sha256([string]$Path) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $algorithm.Dispose() }
}
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$setupTemp = Join-Path $root '.tmp\cpu-setup'
New-Item -ItemType Directory -Force -Path $setupTemp | Out-Null
$setupLock = $null
$transcript = $false
try {
    $setupLock = [IO.File]::Open((Join-Path $setupTemp 'install.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    Start-Transcript -LiteralPath (Join-Path $root '.tmp\install-cpu-bootstrap.log') -Append | Out-Null
    $transcript = $true
    $architecture = $env:PROCESSOR_ARCHITECTURE
    if ($env:PROCESSOR_ARCHITEW6432) { $architecture = $env:PROCESSOR_ARCHITEW6432 }
    if ($architecture -ne 'AMD64' -or [Environment]::OSVersion.Version.Major -lt 10) {
        throw 'Este pacote precisa de Windows 10/11 x64 (Intel/AMD). ARM e Windows 32 bits nao sao suportados.'
    }
    $venv = Join-Path $root '.venv'
    $marker = Join-Path $setupTemp 'in-progress.json'
    $receipt = Join-Path $root '.tmp\cpu-install-receipt.json'
    if ((Test-Path -LiteralPath $venv) -and -not (Test-Path -LiteralPath $marker) -and -not (Test-Path -LiteralPath $receipt)) {
        throw 'Ja existe um ambiente nesta pasta. Extraia o pacote CPU em outra pasta; o ambiente existente nao sera convertido.'
    }
    $manifest = Get-Content -LiteralPath (Join-Path $root 'resources\cpu-setup.json') -Raw | ConvertFrom-Json
    $python = Join-Path $root 'tools\python312\python.exe'
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        Write-Host '[1/6] Baixando Python local 3.12.10...'
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $archive = Join-Path $setupTemp 'python.3.12.10.nupkg'
        $pythonPin = $manifest.python
        if (Test-Path -LiteralPath $archive) {
            if ((Get-Sha256 $archive) -ne $pythonPin.sha256) {
                throw 'O cache do Python esta corrompido. Remova apenas .tmp\cpu-setup\python.3.12.10.nupkg e tente novamente.'
            }
        } else {
            $partial = $archive + '.partial'
            Invoke-WebRequest -UseBasicParsing -Uri $pythonPin.url -OutFile $partial -TimeoutSec 180
            if ((Get-Item -LiteralPath $partial).Length -ne $pythonPin.bytes -or
                (Get-Sha256 $partial) -ne $pythonPin.sha256) {
                throw 'O download do Python falhou na verificacao de tamanho/SHA-256. Nada foi executado.'
            }
            Move-Item -LiteralPath $partial -Destination $archive
        }
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $unpack = Join-Path $setupTemp ('python-' + [Guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $unpack | Out-Null
        $zip = [IO.Compression.ZipFile]::OpenRead($archive)
        try {
            $prefix = [IO.Path]::GetFullPath($unpack) + [IO.Path]::DirectorySeparatorChar
            foreach ($entry in $zip.Entries) {
                $target = [IO.Path]::GetFullPath((Join-Path $unpack $entry.FullName))
                if (-not $target.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
                    throw 'Caminho inseguro no arquivo Python.'
                }
            }
        } finally { $zip.Dispose() }
        [IO.Compression.ZipFile]::ExtractToDirectory($archive, $unpack)
        $pythonTarget = Join-Path $root 'tools\python312'
        if (Test-Path -LiteralPath $pythonTarget) { throw 'Pasta tools\python312 incompleta. Use uma pasta nova para a instalacao.' }
        New-Item -ItemType Directory -Force -Path (Join-Path $root 'tools') | Out-Null
        Move-Item -LiteralPath (Join-Path $unpack 'tools') -Destination $pythonTarget
    }
    $env:TEMP = Join-Path $root '.tmp'
    $env:TMP = $env:TEMP
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    & $python -I -X utf8 (Join-Path $PSScriptRoot 'install_cpu.py')
    if ($LASTEXITCODE -ne 0) { throw 'Falha na instalacao CPU. Veja .tmp\install-cpu.log.' }
    try { & (Join-Path $PSScriptRoot 'create-shortcut.ps1') }
    catch { Write-Host 'AVISO: nao foi possivel criar o atalho. Use START-MULTITRACK.bat.' }
    Write-Host 'PRONTO. Abra MultiTrack.lnk ou START-MULTITRACK.bat.'
    exit 0
} catch {
    Write-Host ('ERRO: ' + $_.Exception.Message)
    exit 1
} finally {
    if ($transcript) { Stop-Transcript | Out-Null }
    if ($setupLock) { $setupLock.Dispose() }
}
