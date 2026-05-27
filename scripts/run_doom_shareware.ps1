#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Engine,
    [string]$Iwad,
    [switch]$NoSound,
    [switch]$Sound
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not $Engine) {
    $Engine = Join-Path $RepoRoot "reference\chocolate-doom\pkg\win32\staging-doom\chocolate-doom.exe"
}

if (-not $Iwad) {
    $Iwad = Join-Path $RepoRoot "third_party\doom_shareware\doom1.wad"
}

if (-not (Test-Path $Engine)) {
    throw "Chocolate Doom executable not found: $Engine"
}

if (-not (Test-Path $Iwad)) {
    throw "Doom shareware IWAD not found: $Iwad"
}

$EnginePath = (Resolve-Path $Engine).Path
$IwadPath = (Resolve-Path $Iwad).Path
$Arguments = @("-iwad", $IwadPath, "-window")

if ($NoSound -or -not $Sound) {
    $Arguments += "-nosound"
}

$Process = Start-Process `
    -FilePath $EnginePath `
    -ArgumentList $Arguments `
    -WorkingDirectory (Split-Path $EnginePath) `
    -PassThru

Start-Sleep -Seconds 2
$Process.Refresh()

if ($Process.HasExited) {
    throw "Doom exited immediately with code $($Process.ExitCode)."
}

Write-Host "Doom shareware started:"
Write-Host "  PID: $($Process.Id)"
Write-Host "  IWAD: $IwadPath"
Write-Host "  Engine: $EnginePath"
if ($Process.MainWindowTitle) {
    Write-Host "  Window: $($Process.MainWindowTitle)"
}
