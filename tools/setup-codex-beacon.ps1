[CmdletBinding()]
param(
    [switch]$SkipCodexUpdate,
    [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'
$repository = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venv = Join-Path $repository '.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'
$venvPythonw = Join-Path $venv 'Scripts\pythonw.exe'
$minimumCodexVersion = [version]'0.149.0'

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath exited with code $LASTEXITCODE"
    }
}

function Get-CompatibleCodex {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    $output = @(& $Path --version 2>&1)
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    $rendered = ($output -join "`n").Trim()
    $match = [regex]::Match($rendered, '(\d+\.\d+\.\d+)')
    if (-not $match.Success) {
        return $null
    }
    $version = [version]$match.Groups[1].Value
    if ($version -lt $minimumCodexVersion) {
        return $null
    }
    return [pscustomobject]@{
        Path = (Resolve-Path -LiteralPath $Path).Path
        Version = $version
        Display = $rendered
    }
}

function Get-WindowsArchitecture {
    $architecture = [string][System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
    switch ($architecture) {
        'X64' { return 'x64' }
        'Arm64' { return 'arm64' }
        default { throw "Codex requires Windows x64 or ARM64; detected $architecture." }
    }
}

function Find-NpmCodex {
    param(
        [Parameter(Mandatory = $true)]$NpmCommand,
        [Parameter(Mandatory = $true)][string]$Architecture
    )

    $rootOutput = @(& $NpmCommand.Source root --global 2>&1)
    if ($LASTEXITCODE -ne 0 -or $rootOutput.Count -eq 0) {
        return $null
    }
    $npmRoot = $rootOutput[-1].ToString().Trim()
    if (-not $npmRoot) {
        return $null
    }
    $searchRoots = @(
        (Join-Path $npmRoot '@openai\codex'),
        (Join-Path $npmRoot "@openai\codex-win32-$Architecture")
    ) | Where-Object { Test-Path -LiteralPath $_ -PathType Container }

    $candidates = foreach ($searchRoot in $searchRoots) {
        Get-ChildItem -LiteralPath $searchRoot -Recurse -File -Filter codex.exe -ErrorAction SilentlyContinue
    }
    $candidates = @($candidates) |
        Where-Object {
            $_.FullName -like "*\@openai\codex-win32-$Architecture\vendor\*\bin\codex.exe"
        } |
        Sort-Object LastWriteTime -Descending
    foreach ($candidate in $candidates) {
        $compatible = Get-CompatibleCodex -Path $candidate.FullName
        if ($null -ne $compatible) {
            return $compatible
        }
    }
    return $null
}

function Find-BundledCodex {
    param([Parameter(Mandatory = $true)][string]$Architecture)

    $extensionRoot = Join-Path $env:USERPROFILE '.vscode\extensions'
    if (-not (Test-Path -LiteralPath $extensionRoot -PathType Container)) {
        return $null
    }
    $extensions = Get-ChildItem -LiteralPath $extensionRoot -Directory -Filter 'openai.chatgpt-*' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending
    foreach ($extension in $extensions) {
        $candidate = Join-Path $extension.FullName "bin\windows-$Architecture\codex.exe"
        $compatible = Get-CompatibleCodex -Path $candidate
        if ($null -ne $compatible) {
            return $compatible
        }
    }
    return $null
}

Write-Host 'Codex Beacon setup' -ForegroundColor Cyan
Write-Host "Workspace: $repository"

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    Write-Host '[1/5] Creating the private Python environment...'
    $py = Get-Command py.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $py) {
        Invoke-Checked -FilePath $py.Source -Arguments @('-3', '-m', 'venv', $venv)
    }
    else {
        $python = Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -eq $python) {
            throw 'Python 3.10 or newer is required. Install Python, then run setup again.'
        }
        Invoke-Checked -FilePath $python.Source -Arguments @('-m', 'venv', $venv)
    }
}
else {
    Write-Host '[1/5] Python environment already exists.'
}

$pythonVersionOutput = @(& $venvPython -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>&1)
if ($LASTEXITCODE -ne 0 -or $pythonVersionOutput.Count -eq 0) {
    throw 'The Codex Beacon Python environment could not report its version. Delete only the .venv folder and run setup again.'
}
$pythonVersionText = $pythonVersionOutput[-1].ToString().Trim()
if ([version]$pythonVersionText -lt [version]'3.10') {
    throw "Codex Beacon requires Python 3.10 or newer; this environment uses $pythonVersionText. Delete only the .venv folder and run setup again after updating Python."
}

Write-Host '[2/5] Installing the Codex Beacon desktop app...'
Invoke-Checked -FilePath $venvPython -Arguments @(
    '-m', 'pip', 'install', '--disable-pip-version-check', '-e', (Join-Path $repository 'desktop')
)

Write-Host '[3/5] Finding a compatible Codex CLI...'
$architecture = Get-WindowsArchitecture
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue | Select-Object -First 1
$codex = $null
if ($null -ne $npm) {
    $codex = Find-NpmCodex -NpmCommand $npm -Architecture $architecture
}
if ($null -eq $codex) {
    $codex = Find-BundledCodex -Architecture $architecture
}
if ($null -eq $codex -and $null -ne $npm -and -not $SkipCodexUpdate) {
    Write-Host '      Installing the current Codex CLI because no compatible copy was found...'
    Invoke-Checked -FilePath $npm.Source -Arguments @(
        'install', '--global', '@openai/codex@latest', '--include=optional', '--no-audit', '--no-fund'
    )
    $codex = Find-NpmCodex -NpmCommand $npm -Architecture $architecture
}
if ($null -eq $codex) {
    if ($null -eq $npm) {
        throw 'Codex 0.149.0 or newer was not found. Install Node.js LTS, reopen this folder, and run setup again.'
    }
    if ($SkipCodexUpdate) {
        throw 'Codex 0.149.0 or newer was not found. Run setup again without -SkipCodexUpdate.'
    }
    throw 'npm completed, but a compatible native Codex executable was not found. Ensure npm optional dependencies are enabled, then run setup again.'
}
Write-Host "      $($codex.Display)"

Write-Host '[4/5] Registering privacy-safe Codex hooks for every Codex project...'
Invoke-Checked -FilePath $venvPython -Arguments @(
    '-m', 'codex_beacon.agent_setup',
    '--repository', $repository
)

Write-Host '[5/5] Finalizing...'
if (-not $NoLaunch) {
    Start-Process -FilePath $venvPythonw -ArgumentList @(
        '-m', 'codex_beacon.companion.app'
    ) -WorkingDirectory $repository
    Write-Host 'Codex Beacon is starting in Codex status mode.' -ForegroundColor Green
}
else {
    Write-Host 'Launch skipped by request.'
}

Write-Host ''
Write-Host 'One security confirmation remains:' -ForegroundColor Yellow
Write-Host '  1. Open a terminal in any project and run: codex'
Write-Host '  2. Inside Codex, run: /hooks'
Write-Host '  3. Review the five User Config Codex Beacon hooks and verify they show Trusted.'
Write-Host ''
Write-Host 'After that, double-click start-codex-beacon.cmd whenever you want Codex status mode.'