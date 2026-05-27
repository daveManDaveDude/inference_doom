#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$MsysRoot = "C:\msys64",
    [switch]$InstallDependencies
)

$ErrorActionPreference = "Stop"

function Convert-ToMsysPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $resolved = (Resolve-Path $Path).Path -replace "\\", "/"
    if ($resolved -match "^([A-Za-z]):/(.*)$") {
        return "/" + $Matches[1].ToLowerInvariant() + "/" + $Matches[2]
    }
    return $resolved
}

function Copy-MingwDependencies {
    param(
        [Parameter(Mandatory = $true)][string]$RootExe,
        [Parameter(Mandatory = $true)][string]$StageDir,
        [Parameter(Mandatory = $true)][string]$MingwBin
    )

    $objdump = Join-Path $MingwBin "objdump.exe"
    if (-not (Test-Path $objdump)) {
        throw "objdump.exe not found: $objdump"
    }

    $systemDlls = @(
        "advapi32.dll", "bcrypt.dll", "cfgmgr32.dll", "combase.dll",
        "crypt32.dll", "dwmapi.dll", "gdi32.dll", "imm32.dll",
        "iphlpapi.dll", "kernel32.dll", "msvcrt.dll", "ole32.dll",
        "oleaut32.dll", "rpcrt4.dll", "secur32.dll", "setupapi.dll",
        "shell32.dll", "shlwapi.dll", "user32.dll", "version.dll",
        "winmm.dll", "ws2_32.dll", "ntdll.dll"
    )

    $systemLookup = @{}
    foreach ($dll in $systemDlls) {
        $systemLookup[$dll] = $true
    }

    $seen = @{}
    $queue = New-Object System.Collections.Generic.Queue[string]
    $queue.Enqueue($RootExe)

    while ($queue.Count -gt 0) {
        $file = $queue.Dequeue()
        if (-not (Test-Path $file)) {
            continue
        }

        $key = (Resolve-Path $file).Path.ToLowerInvariant()
        if ($seen.ContainsKey($key)) {
            continue
        }
        $seen[$key] = $true

        $imports = & $objdump -p $file |
            Select-String -Pattern "DLL Name:" |
            ForEach-Object { ($_.Line -replace "^\s*DLL Name:\s*", "").Trim() }

        foreach ($dll in $imports) {
            $name = $dll.ToLowerInvariant()
            if ($systemLookup.ContainsKey($name)) {
                continue
            }

            $source = Join-Path $MingwBin $dll
            $dest = Join-Path $StageDir $dll
            if (-not (Test-Path $source)) {
                Write-Warning "Could not find dependency in MSYS2 mingw32 bin: $dll"
                continue
            }

            if (-not (Test-Path $dest)) {
                Copy-Item -Path $source -Destination $dest -Force
            }
            $queue.Enqueue($dest)
        }
    }
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Bash = Join-Path $MsysRoot "usr\bin\bash.exe"
$MingwBin = Join-Path $MsysRoot "mingw32\bin"

if (-not (Test-Path $Bash)) {
    throw "MSYS2 bash not found at $Bash. Install MSYS2 first."
}

if ($InstallDependencies) {
    & $Bash -lc "pacman -Syu --noconfirm"
    & $Bash -lc "pacman -S --needed --noconfirm base-devel msys2-devel mingw-w64-i686-toolchain mingw-w64-i686-SDL2 mingw-w64-i686-SDL2_net mingw-w64-i686-SDL2_mixer mingw-w64-i686-libpng mingw-w64-i686-cmake mingw-w64-i686-ninja automake-wrapper autoconf python zip git"
}

$RepoMsys = Convert-ToMsysPath $RepoRoot
$BuildScript = @"
set -euo pipefail
export MSYSTEM=MINGW32
export CHERE_INVOKING=1
export PATH=/mingw32/bin:/usr/bin:`$PATH
cd "$RepoMsys"
mkdir -p reference
cd reference
if [ ! -d chocolate-doom/.git ]; then
    git clone https://github.com/chocolate-doom/chocolate-doom.git chocolate-doom
fi
cd chocolate-doom
git fetch --tags
git checkout chocolate-doom-3.1.1
cmake -S . -B build-mingw32 -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/mingw32/bin/gcc.exe
cmake --build build-mingw32 --config Release
mkdir -p pkg/win32/staging-doom
cp build-mingw32/src/chocolate-doom.exe pkg/win32/staging-doom/
cp build-mingw32/src/chocolate-setup.exe pkg/win32/staging-doom/chocolate-doom-setup.exe
"@

& $Bash -lc $BuildScript

$StageDir = Join-Path $RepoRoot "reference\chocolate-doom\pkg\win32\staging-doom"
$Engine = Join-Path $StageDir "chocolate-doom.exe"
Copy-MingwDependencies -RootExe $Engine -StageDir $StageDir -MingwBin $MingwBin

Write-Host "Chocolate Doom reference engine staged:"
Write-Host "  $Engine"
