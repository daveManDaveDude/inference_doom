#Requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$InstallDependencies,
    [switch]$Launch,
    [switch]$NoSound,
    [switch]$Sound
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $PSCommandPath

& (Join-Path $ScriptDir "setup_doom_shareware.ps1")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& (Join-Path $ScriptDir "build_reference_chocolate_doom.ps1") -InstallDependencies:$InstallDependencies

if ($Launch) {
    & (Join-Path $ScriptDir "run_doom_shareware.ps1") -NoSound:$NoSound -Sound:$Sound
}
