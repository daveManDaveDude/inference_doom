# Emitted Executable Smoke Tests

These checks cover the no-compiler PE32 executables emitted directly by Python.

## Stage 01 Window

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_stage01_window.py
```

Expected output:

```text
build/stage01_window.exe
```

Manual smoke test:

```powershell
.\build\stage01_window.exe
```

Expected result:

- A visible window opens.
- The title is `Inference Doom - Stage 01 Window`.
- Closing the window exits the process cleanly.

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\stage01_window.exe).Path
$Process = Start-Process -FilePath $Exe -PassThru
$Deadline = (Get-Date).AddSeconds(5)

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until ($Process.MainWindowTitle -eq "Inference Doom - Stage 01 Window" -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "stage01_window.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -ne "Inference Doom - Stage 01 Window") {
    Stop-Process -Id $Process.Id -Force
    throw "stage01_window.exe did not expose the expected window title"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "stage01_window.exe did not close cleanly"
}

if ($Process.ExitCode -ne 0) {
    throw "stage01_window.exe exited with code $($Process.ExitCode)"
}
```

This path must not invoke a compiler, assembler, linker, CMake, MSBuild, Visual Studio, MinGW, NASM, or external binary tools.

## Source Stage 01 WAD/Map

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage01_wad_map.py
```

Expected output:

```text
build/source_stage01_wad_map.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage01_wad_map.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until ($Process.MainWindowTitle -like "*V=1189 L=1274 SD=2041 SEC=211*" -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage01_wad_map.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike "*V=1189 L=1274 SD=2041 SEC=211*") {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage01_wad_map.exe did not report the expected MAP01 counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage01_wad_map.exe did not close cleanly"
}
```

Those counts are for the pinned `third_party\freedoom\freedoom2.wad` `MAP01`
used by the first source-guided slice.

## Source Stage 02 BSP Setup

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage02_bsp_setup.py
```

Expected output:

```text
build/source_stage02_bsp_setup.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage02_bsp_setup.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until ($Process.MainWindowTitle -like "*V=1189 L=1274 SD=2041 SEC=211 SS=698 N=697 SG=2233 ROOT=696 G=3..81 F0=16*" -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage02_bsp_setup.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike "*V=1189 L=1274 SD=2041 SEC=211 SS=698 N=697 SG=2233 ROOT=696 G=3..81 F0=16*") {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage02_bsp_setup.exe did not report the expected MAP01 BSP setup counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage02_bsp_setup.exe did not close cleanly"
}
```

The executable embeds an `asInvoker` manifest resource because the required
filename contains `setup`; this keeps direct process launch from tripping
Windows installer-elevation heuristics.

## Source Stage 03 BSP Walk Debug

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage03_bsp_walk_debug.py
```

Expected output:

```text
build/source_stage03_bsp_walk_debug.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage03_bsp_walk_debug.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until ($Process.MainWindowTitle -like "*V=1189 SEC=211 SD=2041 L=1274 SS=698 N=697 SG=2233 VN=697 VSS=698 VSEG=2233 DEPTH=33 FIRSTSS=227 LASTSS=169*" -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage03_bsp_walk_debug.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike "*V=1189 SEC=211 SD=2041 L=1274 SS=698 N=697 SG=2233 VN=697 VSS=698 VSEG=2233 DEPTH=33 FIRSTSS=227 LASTSS=169*") {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage03_bsp_walk_debug.exe did not report the expected BSP traversal counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage03_bsp_walk_debug.exe did not close cleanly"
}
```

The window framebuffer shows a simple top-down map view: muted map lines,
highlighted visited segs from the accept-all BSP traversal, and the pinned
player-start viewpoint marker. Stage03 intentionally keeps `R_CheckBBox` as an
accept-all debug boundary; real bbox/frustum visibility belongs to stage04.
