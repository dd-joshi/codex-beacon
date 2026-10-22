$PlatformIoArguments = $args

$platformIo = Join-Path $env:USERPROFILE '.platformio\penv\Scripts\platformio.exe'
if (-not (Test-Path -LiteralPath $platformIo -PathType Leaf)) {
    throw "PlatformIO executable not found: $platformIo"
}

# ESP-IDF's generated CMake command line is not reliable when PLATFORMIO_CORE_DIR
# contains spaces. This profile does, so expose it temporarily through a short
# drive path. Refuse to reuse an unrelated P: mapping.
if ($env:USERPROFILE -notmatch '\s') {
    & $platformIo @PlatformIoArguments
    exit $LASTEXITCODE
}

$createdMapping = $false
$mappingLine = (& subst) |
    Where-Object { $_ -match '^P:\\: =>\s*(.+)$' } |
    Select-Object -First 1
if ($null -ne $mappingLine) {
    $mappedPath = [regex]::Match(
        $mappingLine, '^P:\\: =>\s*(.+)$').Groups[1].Value.TrimEnd('\')
    if (-not $mappedPath.Equals(
            $env:USERPROFILE.TrimEnd('\'),
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "P: is mapped to '$mappedPath', not the PlatformIO profile."
    }
} elseif (Test-Path -LiteralPath 'P:\') {
    throw 'P: is already in use; free it or adjust the temporary drive in pio.ps1.'
} else {
    & subst P: $env:USERPROFILE
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not create the temporary P: mapping for PlatformIO.'
    }
    $createdMapping = $true
}

try {
    $env:PLATFORMIO_CORE_DIR = 'P:\.platformio'
    & 'P:\.platformio\penv\Scripts\platformio.exe' @PlatformIoArguments
    $result = $LASTEXITCODE
} finally {
    if ($createdMapping) {
        & subst P: /D | Out-Null
    }
}

exit $result