[CmdletBinding()]
param(
    [string]$OutputPath,
    [switch]$ManifestOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$toolsDirectory = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$repository = (Resolve-Path -LiteralPath (Join-Path $toolsDirectory '..')).Path.TrimEnd(
    [System.IO.Path]::DirectorySeparatorChar,
    [System.IO.Path]::AltDirectorySeparatorChar
)
$repositoryPrefix = $repository + [System.IO.Path]::DirectorySeparatorChar
$archiveRoot = 'Peri6-Agent'

function Resolve-RepositoryFile {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath
    )

    if ([System.IO.Path]::IsPathRooted($RelativePath)) {
        throw "Package allowlist entries must be relative paths: $RelativePath"
    }

    $candidate = [System.IO.Path]::GetFullPath((Join-Path $repository $RelativePath))
    if (-not $candidate.StartsWith($repositoryPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Package allowlist entry escaped the repository: $RelativePath"
    }
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        throw "Required package file is missing: $RelativePath"
    }

    $resolved = (Resolve-Path -LiteralPath $candidate).Path
    if (-not $resolved.StartsWith($repositoryPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Package source resolves outside the repository: $RelativePath"
    }

    $item = Get-Item -LiteralPath $resolved -Force
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Package source cannot be a link or reparse point: $RelativePath"
    }
    return $resolved
}

function Convert-ToArchivePath {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath
    )

    return "$archiveRoot/$($RelativePath.Replace('\', '/'))"
}

$fixedFiles = @(
    '.codex\hooks\peri6_agent_hook.py',
    'desktop\pyproject.toml',
    'setup-peri6-agent.cmd',
    'start-peri6-agent.cmd',
    'start-peri6.cmd',
    'tools\setup-peri6-agent.ps1'
)

$entries = [System.Collections.Generic.List[object]]::new()
foreach ($relativePath in $fixedFiles) {
    $entries.Add([pscustomobject]@{
        Entry = Convert-ToArchivePath -RelativePath $relativePath
        Source = Resolve-RepositoryFile -RelativePath $relativePath
        Content = $null
    })
}

$allowedSourceExtensions = @('.py', '.json')
$sourceRootFiles = @(
    'desktop\src\peri6\__init__.py',
    'desktop\src\peri6\agent_setup.py',
    'desktop\src\peri6\config.py'
)
$sourceDirectoryAllowlist = @(
    'desktop\src\peri6\companion',
    'desktop\src\peri6\contracts',
    'desktop\src\peri6\host',
    'desktop\src\peri6\packs',
    'desktop\src\peri6\protocol',
    'desktop\src\peri6\tester',
    'desktop\src\peri6\transport'
)

$sourceFiles = [System.Collections.Generic.List[System.IO.FileInfo]]::new()
foreach ($sourceRootFile in $sourceRootFiles) {
    $sourceFiles.Add((Get-Item -LiteralPath (Resolve-RepositoryFile -RelativePath $sourceRootFile) -Force))
}
foreach ($sourceDirectoryRelative in $sourceDirectoryAllowlist) {
    $sourceDirectory = [System.IO.Path]::GetFullPath((Join-Path $repository $sourceDirectoryRelative))
    if (-not (Test-Path -LiteralPath $sourceDirectory -PathType Container)) {
        throw "Required package source directory is missing: $sourceDirectoryRelative"
    }
    $resolvedSourceDirectory = (Resolve-Path -LiteralPath $sourceDirectory).Path
    if (-not $resolvedSourceDirectory.StartsWith($repositoryPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Package source directory resolves outside the repository: $sourceDirectoryRelative"
    }
    if (((Get-Item -LiteralPath $resolvedSourceDirectory -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Package source directory cannot be a link or reparse point: $sourceDirectoryRelative"
    }

    Get-ChildItem -LiteralPath $resolvedSourceDirectory -File -Recurse -Force |
        Where-Object {
            $allowedSourceExtensions -contains $_.Extension.ToLowerInvariant() -and
            $_.FullName -notmatch '(^|[\\/])__pycache__([\\/]|$)'
        } |
        ForEach-Object { $sourceFiles.Add($_) }
}

foreach ($sourceFile in $sourceFiles) {
    $resolvedFile = (Resolve-Path -LiteralPath $sourceFile.FullName).Path
    if (-not $resolvedFile.StartsWith($repositoryPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Package source resolves outside the repository: $($sourceFile.FullName)"
    }
    if (($sourceFile.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Package source cannot be a link or reparse point: $($sourceFile.FullName)"
    }

    $relativePath = $resolvedFile.Substring($repositoryPrefix.Length)
    $entries.Add([pscustomobject]@{
        Entry = Convert-ToArchivePath -RelativePath $relativePath
        Source = $resolvedFile
        Content = $null
    })
}

$startHere = @'
PERI6 AGENT - START HERE

1. Extract the entire Peri6-Agent folder from this ZIP to a permanent location.
   Do not run setup from inside the ZIP. If you move the folder later, run setup again.
2. Double-click setup-peri6-agent.cmd and let it finish.
3. Reload your VS Code window.
4. Open a terminal, run codex, then run /hooks inside Codex.
5. Verify the five User Config Peri6 hooks show Trusted.

For everyday use, double-click start-peri6-agent.cmd.

The desktop preview works without Peri6 hardware. A physical device needs its
own separately provisioned desktop/local-config.json; the sender's private
device credential is intentionally not included in this package.

Requirements: Windows, Python 3.10 or newer, VS Code, and the official Codex
extension. Node.js LTS is recommended so setup can install a compatible Codex
CLI automatically when the extension's bundled copy is too old.
'@
$entries.Add([pscustomobject]@{
    Entry = "$archiveRoot/START-HERE.txt"
    Source = $null
    Content = $startHere
})

$entries = @($entries | Sort-Object Entry)
$duplicateEntries = $entries | Group-Object { $_.Entry.ToLowerInvariant() } | Where-Object Count -gt 1
if ($duplicateEntries) {
    throw "Duplicate package entries were generated: $($duplicateEntries.Name -join ', ')"
}

$forbiddenFragments = @(
    '/.venv/',
    '/.vscode/',
    '/__pycache__/',
    '/desktop/local-config.json',
    '/desktop/agent-hook.json',
    '/desktop/agent-hook.log',
    '/firmware/include/peri6/local_config.h',
    '/firmware/include/peri6_local_config.h'
)
foreach ($entry in $entries) {
    $lowerEntry = "/$($entry.Entry.ToLowerInvariant())"
    foreach ($forbiddenFragment in $forbiddenFragments) {
        if ($lowerEntry.Contains($forbiddenFragment)) {
            throw "Forbidden local artifact reached the package manifest: $($entry.Entry)"
        }
    }
    if ($lowerEntry.EndsWith('.pyc')) {
        throw "Compiled Python artifacts are forbidden in the package: $($entry.Entry)"
    }
}

if ($ManifestOnly) {
    $entries | ForEach-Object { $_.Entry }
    return
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repository 'dist\Peri6-Agent-friend.zip'
}
elseif (-not [System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath = Join-Path $repository $OutputPath
}

$outputFullPath = [System.IO.Path]::GetFullPath($OutputPath)
if ([System.IO.Path]::GetExtension($outputFullPath) -ine '.zip') {
    throw "Friend package output must be a .zip file: $outputFullPath"
}
$outputDirectory = [System.IO.Path]::GetDirectoryName($outputFullPath)
if ([string]::IsNullOrWhiteSpace($outputDirectory)) {
    throw "Friend package output directory could not be resolved: $outputFullPath"
}

[System.IO.Directory]::CreateDirectory($outputDirectory) | Out-Null
$resolvedOutputDirectory = (Resolve-Path -LiteralPath $outputDirectory).Path.TrimEnd(
    [System.IO.Path]::DirectorySeparatorChar,
    [System.IO.Path]::AltDirectorySeparatorChar
)
$outputFullPath = Join-Path $resolvedOutputDirectory ([System.IO.Path]::GetFileName($outputFullPath))
if (Test-Path -LiteralPath $outputFullPath -PathType Container) {
    throw "Friend package output points to a directory: $outputFullPath"
}

$temporaryName = ".$([System.IO.Path]::GetFileName($outputFullPath)).$([guid]::NewGuid().ToString('N')).tmp"
$temporaryZip = [System.IO.Path]::GetFullPath((Join-Path $resolvedOutputDirectory $temporaryName))
if (-not [System.IO.Path]::GetDirectoryName($temporaryZip).Equals(
    $resolvedOutputDirectory,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "Temporary package path escaped the requested output directory: $temporaryZip"
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$archiveStream = $null
$archive = $null
try {
    $archiveStream = [System.IO.File]::Open(
        $temporaryZip,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
    $archive = [System.IO.Compression.ZipArchive]::new(
        $archiveStream,
        [System.IO.Compression.ZipArchiveMode]::Create,
        $false
    )

    foreach ($entry in $entries) {
        if ($null -ne $entry.Source) {
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive,
                $entry.Source,
                $entry.Entry,
                [System.IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
            continue
        }

        $zipEntry = $archive.CreateEntry($entry.Entry, [System.IO.Compression.CompressionLevel]::Optimal)
        $writer = [System.IO.StreamWriter]::new(
            $zipEntry.Open(),
            [System.Text.UTF8Encoding]::new($false)
        )
        try {
            $writer.Write($entry.Content)
        }
        finally {
            $writer.Dispose()
        }
    }

    $archive.Dispose()
    $archive = $null
    $archiveStream.Dispose()
    $archiveStream = $null

    if (Test-Path -LiteralPath $outputFullPath) {
        Remove-Item -LiteralPath $outputFullPath -Force
    }
    Move-Item -LiteralPath $temporaryZip -Destination $outputFullPath
}
finally {
    if ($null -ne $archive) {
        $archive.Dispose()
    }
    if ($null -ne $archiveStream) {
        $archiveStream.Dispose()
    }
    if (Test-Path -LiteralPath $temporaryZip -PathType Leaf) {
        $temporaryParent = [System.IO.Path]::GetDirectoryName(
            [System.IO.Path]::GetFullPath($temporaryZip)
        )
        if (-not $temporaryParent.Equals(
            $resolvedOutputDirectory,
            [System.StringComparison]::OrdinalIgnoreCase
        )) {
            throw "Refusing to clean up an unverified temporary path: $temporaryZip"
        }
        Remove-Item -LiteralPath $temporaryZip -Force
    }
}

Write-Host "Created friend package with $($entries.Count) allowlisted files:" -ForegroundColor Green
Write-Output $outputFullPath
