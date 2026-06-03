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

## Source Stage 04 BBox Visibility Debug

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage04_bbox_visibility_debug.py
```

Expected output:

```text
build/source_stage04_bbox_visibility_debug.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage04_bbox_visibility_debug.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until ($Process.MainWindowTitle -like "*V=1189 SEC=211 SD=2041 L=1274 SS=698 N=697 SG=2233 VN=697 VSS=698 VSEG=2233 DEPTH=33 FIRSTSS=227 LASTSS=169 BVN=559 BVSS=513 BVSEG=1709 BDEPTH=33 BFIRSTSS=227 BLASTSS=153 CULL=47*" -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage04_bbox_visibility_debug.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike "*V=1189 SEC=211 SD=2041 L=1274 SS=698 N=697 SG=2233 VN=697 VSS=698 VSEG=2233 DEPTH=33 FIRSTSS=227 LASTSS=169 BVN=559 BVSS=513 BVSEG=1709 BDEPTH=33 BFIRSTSS=227 BLASTSS=153 CULL=47*") {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage04_bbox_visibility_debug.exe did not report the expected bbox visibility counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage04_bbox_visibility_debug.exe did not close cleanly"
}
```

The window framebuffer keeps the stage03 top-down debug view and overlays
bbox-visible segs from the `R_CheckBBox` pass. Stage04 initializes only the
`R_ClearClipSegs` sentinel ranges and does not start wall-span clipping.

## Source Stage 05 Seg Clip Debug

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage05_seg_clip_debug.py
```

Expected output:

```text
build/source_stage05_seg_clip_debug.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage05_seg_clip_debug.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until ($Process.MainWindowTitle -like "*VN=697 VSS=698 VSEG=2233 BVN=559 BVSS=513 BVSEG=1709 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1*" -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage05_seg_clip_debug.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike "*VN=697 VSS=698 VSEG=2233 BVN=559 BVSS=513 BVSEG=1709 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1*") {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage05_seg_clip_debug.exe did not report the expected seg clipping counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage05_seg_clip_debug.exe did not close cleanly"
}
```

Stage05 preserves the stage04 accept-all and sentinel-only bbox-visible
baselines, then adds mutable wall-span clipping counters from the pinned
source-shaped `MAP01` reference. It stops at debug span recording and does not
start projection, texture drawing, planes, sprites, or source_stage06.

## Source Stage 06 Live Seg Clip Debug

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage06_live_seg_clip_debug.py
```

Expected output:

```text
build/source_stage06_live_seg_clip_debug.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage06_live_seg_clip_debug.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until ($Process.MainWindowTitle -like "*VN=697 VSS=698 VSEG=2233 BVN=559 BVSS=513 BVSEG=1709 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1 FSPAN=224-255 FSEG=605 LSPAN=143-165 LSEG=855*" -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage06_live_seg_clip_debug.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike "*VN=697 VSS=698 VSEG=2233 BVN=559 BVSS=513 BVSEG=1709 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1 FSPAN=224-255 FSEG=605 LSPAN=143-165 LSEG=855*") {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage06_live_seg_clip_debug.exe did not report the expected live seg clipping counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage06_live_seg_clip_debug.exe did not close cleanly"
}
```

Stage06 keeps the stage04 comparison baselines, then runs the mutable
wall-span clipping traversal live in emitted x86. The smoke signal includes
the first and last debug span records to prove the runtime span buffer is being
filled. It still stops before projection, texture drawing, planes, sprites,
masked textures, and source_stage07.

## Source Stage 07 Wall Projection Debug

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage07_wall_projection_debug.py
```

Expected output:

```text
build/source_stage07_wall_projection_debug.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage07_wall_projection_debug.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until ($Process.MainWindowTitle -like "*VN=697 VSS=698 VSEG=2233 BVN=559 BVSS=513 BVSEG=1709 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1 FSPAN=224-255 FSEG=605 LSPAN=143-165 LSEG=855 VZ=2686976 VCOS=65535 VSIN=25 VALID=1 FRAME=1 PRJ=86 MIND=2073560 MAXD=58720255 MINS=11702 MAXS=108495 FPRJ=224-255 FPSEG=605 LPRJ=143-165 LPSEG=855*" -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage07_wall_projection_debug.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike "*VN=697 VSS=698 VSEG=2233 BVN=559 BVSS=513 BVSEG=1709 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1 FSPAN=224-255 FSEG=605 LSPAN=143-165 LSEG=855 VZ=2686976 VCOS=65535 VSIN=25 VALID=1 FRAME=1 PRJ=86 MIND=2073560 MAXD=58720255 MINS=11702 MAXS=108495 FPRJ=224-255 FPSEG=605 LPRJ=143-165 LPSEG=855*") {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage07_wall_projection_debug.exe did not report the expected wall projection counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage07_wall_projection_debug.exe did not close cleanly"
}
```

Stage07 preserves the stage04/stage06 traversal and clipping counters, then
adds fixed-player frame fields plus source-shaped `FixedDiv`,
`R_PointToDist`, and `R_ScaleFromGlobalAngle` projection records for the same
86 accepted spans. It stops before texture lookup, `R_RenderSegLoop`,
`R_DrawColumn`, planes, sprites, masked textures, light tables, and
source_stage08.

## Source Stage 08 Texture Data Setup Debug

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage08_texture_data_setup_debug.py
```

Expected output:

```text
build/source_stage08_texture_data_setup_debug.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage08_texture_data_setup_debug.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedClip = "*VN=697 VSS=698 VSEG=2233 BVN=559 BVSS=513 BVSEG=1709 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1*"
$ExpectedProjection = "*PRJ=86 MIND=2073560 MAXD=58720255 MINS=11702 MAXS=108495*"
$ExpectedTexture = "*TEX=963 PN=1054 FLAT=246 DIRC=80797 COMPC=26323 FPTEX=850 LPTEX=13 EMID=1*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedClip -and
          $Process.MainWindowTitle -like $ExpectedProjection -and
          $Process.MainWindowTitle -like $ExpectedTexture) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage08_texture_data_setup_debug.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedClip -or
    $Process.MainWindowTitle -notlike $ExpectedProjection -or
    $Process.MainWindowTitle -notlike $ExpectedTexture) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage08_texture_data_setup_debug.exe did not report the expected texture setup counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage08_texture_data_setup_debug.exe did not close cleanly"
}
```

Stage08 preserves the stage07 clipping/projection pipeline and adds bounded
source-shaped texture/flat metadata. The smoke signal proves `PNAMES`,
`TEXTURE1`, optional `TEXTURE2`, flat ranges, sidedef texture IDs, and sector
flat IDs are connected to the projected spans. It stops before texture pixel
lookup, `R_RenderSegLoop`, `R_DrawColumn`, colormaps, light tables, visplanes,
sprites, masked textures, and source_stage09.

## Source Stage 09 Direct Wall Column Pixels Debug

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage09_direct_wall_column_pixels_debug.py
```

Expected output:

```text
build/source_stage09_direct_wall_column_pixels_debug.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage09_direct_wall_column_pixels_debug.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedClip = "*VN=697 VSS=698 VSEG=2233 BVN=559 BVSS=513 BVSEG=1709 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1*"
$ExpectedProjection = "*PRJ=86 MIND=2073560 MAXD=58720255 MINS=11702 MAXS=108495*"
$ExpectedTexture = "*TEX=963 PN=1054 FLAT=246 DIRC=80797 COMPC=26323 FPTEX=850 LPTEX=13 EMID=1*"
$ExpectedPixels = "*DWSP=86 OPQSP=24 DCOL=297 DRAW=162 SKC=135 SKU=62 ZTEX=0 MASK=0 FTEX=850 FN=AQRUST08 FCOL=127 PIX=15508 SIG=2194105880*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedClip -and
          $Process.MainWindowTitle -like $ExpectedProjection -and
          $Process.MainWindowTitle -like $ExpectedTexture -and
          $Process.MainWindowTitle -like $ExpectedPixels) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage09_direct_wall_column_pixels_debug.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedClip -or
    $Process.MainWindowTitle -notlike $ExpectedProjection -or
    $Process.MainWindowTitle -notlike $ExpectedTexture -or
    $Process.MainWindowTitle -notlike $ExpectedPixels) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage09_direct_wall_column_pixels_debug.exe did not report the expected direct wall pixel counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage09_direct_wall_column_pixels_debug.exe did not close cleanly"
}
```

Stage09 preserves the stage08 setup, clipping, and projection counters, then
draws deterministic real wall pixels from direct patch-backed, one-sided opaque
midtexture columns. It counts texture-zero spans, composite-needed columns,
unsupported two-sided cases, and masked midtextures, and reports a runtime RGB
pixel signature. It still defers composite generation, two-sided wall edges,
plane spans, actors, sky, movement, and gameplay.

## Source Stage 10 Composite Two-Sided Wall Edges Debug

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage10_composite_two_sided_wall_edges_debug.py
```

Expected output:

```text
build/source_stage10_composite_two_sided_wall_edges_debug.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage10_composite_two_sided_wall_edges_debug.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedClip = "*VN=697 VSS=698 VSEG=2233 BVN=559 BVSS=513 BVSEG=1709 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1*"
$ExpectedProjection = "*PRJ=86 MIND=2073560 MAXD=58720255 MINS=11702 MAXS=108495*"
$ExpectedTexture = "*TEX=963 PN=1054 FLAT=246 DIRC=80797 COMPC=26323 FPTEX=850 LPTEX=13 EMID=1*"
$ExpectedStage09 = "*DWSP=86 OPQSP=24 DCOL=297 DRAW=162 SKC=135 SKU=62 ZTEX=0 MASK=0 FTEX=850 FN=AQRUST08 FCOL=127 PIX=15508 SIG=2194105880*"
$ExpectedStage10 = "*CMB=89 CMH=75 CMO=0 MCOL=2 MCEMP=133 UCOL=478 UCOMP=6 LCOL=138 PM=1659 F10TEX=850 F10N=AQRUST08 L10TEX=887 L10N=AQSECT08 TCOL=780 TPIX=37546 TSIG=4201955800*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedClip -and
          $Process.MainWindowTitle -like $ExpectedProjection -and
          $Process.MainWindowTitle -like $ExpectedTexture -and
          $Process.MainWindowTitle -like $ExpectedStage09 -and
          $Process.MainWindowTitle -like $ExpectedStage10) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage10_composite_two_sided_wall_edges_debug.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedClip -or
    $Process.MainWindowTitle -notlike $ExpectedProjection -or
    $Process.MainWindowTitle -notlike $ExpectedTexture -or
    $Process.MainWindowTitle -notlike $ExpectedStage09 -or
    $Process.MainWindowTitle -notlike $ExpectedStage10) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage10_composite_two_sided_wall_edges_debug.exe did not report the expected composite/two-sided wall edge counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage10_composite_two_sided_wall_edges_debug.exe did not close cleanly"
}
```

Stage10 preserves the stage09 direct wall-pixel counters, adds source-shaped
composite column construction for the pinned one-sided midtexture candidates,
draws supported two-sided upper/lower wall edge columns, records plane-mark
handoff counts, and reports a deterministic runtime RGB pixel signature.
