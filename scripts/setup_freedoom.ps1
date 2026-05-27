#Requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$ForceDownload,
    [string]$Archive,
    [string]$Destination,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $PSCommandPath
$PythonScript = Join-Path $ScriptDir "setup_freedoom.py"

$PythonArgs = @($PythonScript)

if ($ForceDownload) {
    $PythonArgs += "--force-download"
}

if ($Archive) {
    $PythonArgs += @("--archive", $Archive)
}

if ($Destination) {
    $PythonArgs += @("--destination", $Destination)
}

if (Get-Command $Python -ErrorAction SilentlyContinue) {
    & $Python @PythonArgs
    exit $LASTEXITCODE
}

if ($Python -eq "python" -and (Get-Command "py" -ErrorAction SilentlyContinue)) {
    & py -3 @PythonArgs
    exit $LASTEXITCODE
}

throw "Python was not found. Install Python 3, or pass -Python with the executable path."
