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

## Source Stage 11 Visplanes Floor/Ceiling Debug

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage11_visplanes_floor_ceiling_debug.py
```

Expected output:

```text
build/source_stage11_visplanes_floor_ceiling_debug.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage11_visplanes_floor_ceiling_debug.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedClip = "*VN=697 VSS=698 VSEG=2233 BVN=559 BVSS=513 BVSEG=1709 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1*"
$ExpectedProjection = "*PRJ=86 MIND=2073560 MAXD=58720255 MINS=11702 MAXS=108495*"
$ExpectedTexture = "*TEX=963 PN=1054 FLAT=246 DIRC=80797 COMPC=26323 FPTEX=850 LPTEX=13 EMID=1*"
$ExpectedStage09 = "*DWSP=86 OPQSP=24 DCOL=297 DRAW=162 SKC=135 SKU=62 ZTEX=0 MASK=0 FTEX=850 FN=AQRUST08 FCOL=127 PIX=15508 SIG=2194105880*"
$ExpectedStage10 = "*CMB=89 CMH=75 CMO=0 MCOL=2 MCEMP=133 UCOL=478 UCOMP=6 LCOL=138 PM=1659 F10TEX=850 F10N=AQRUST08 L10TEX=887 L10N=AQSECT08 TCOL=780 TPIX=37546 TSIG=4201955800*"
$ExpectedStage11 = "*VP=38 VPF=30 VPR=88 VPS=8 VPO=0 CPM=727 FPM=932 FSP=169 FPIX=20791 SKYV=0 SKYC=0 SKYP=0 FSK=0 SPO=0 F11F=81 F11FN=SLIME14 C11F=113 C11N=FLOOR5_2 FSIG=2178063413*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedClip -and
          $Process.MainWindowTitle -like $ExpectedProjection -and
          $Process.MainWindowTitle -like $ExpectedTexture -and
          $Process.MainWindowTitle -like $ExpectedStage09 -and
          $Process.MainWindowTitle -like $ExpectedStage10 -and
          $Process.MainWindowTitle -like $ExpectedStage11) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage11_visplanes_floor_ceiling_debug.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedClip -or
    $Process.MainWindowTitle -notlike $ExpectedProjection -or
    $Process.MainWindowTitle -notlike $ExpectedTexture -or
    $Process.MainWindowTitle -notlike $ExpectedStage09 -or
    $Process.MainWindowTitle -notlike $ExpectedStage10 -or
    $Process.MainWindowTitle -notlike $ExpectedStage11) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage11_visplanes_floor_ceiling_debug.exe did not report the expected visplane/flat-span counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage11_visplanes_floor_ceiling_debug.exe did not close cleanly"
}
```

Stage11 preserves the stage10 wall renderer and counters, consumes the
stage10 plane-mark handoff through bounded visplanes, draws regular
floor/ceiling flat spans from real 64x64 WAD flat lumps, counts skipped sky
ceilings, and reports a deterministic wall+flat RGB signature.

## Source Stage 12 Sky And Masked Midtextures Debug

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage12_sky_and_masked_midtextures_debug.py
```

Expected output:

```text
build/source_stage12_sky_and_masked_midtextures_debug.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage12_sky_and_masked_midtextures_debug.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedClip = "*VN=697 VSS=698 VSEG=2233 BVN=559 BVSS=513 BVSEG=1709 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1*"
$ExpectedProjection = "*PRJ=86 MIND=2073560 MAXD=58720255 MINS=11702 MAXS=108495*"
$ExpectedTexture = "*TEX=963 PN=1054 FLAT=246 DIRC=80797 COMPC=26323 FPTEX=850 LPTEX=13 EMID=1*"
$ExpectedStage09 = "*DWSP=86 OPQSP=24 DCOL=297 DRAW=162 SKC=135 SKU=62 ZTEX=0 MASK=0 FTEX=850 FN=AQRUST08 FCOL=127 PIX=15508 SIG=2194105880*"
$ExpectedStage10 = "*CMB=89 CMH=75 CMO=0 MCOL=2 MCEMP=133 UCOL=478 UCOMP=6 LCOL=138 PM=1659 F10TEX=850 F10N=AQRUST08 L10TEX=887 L10N=AQSECT08 TCOL=780 TPIX=37546 TSIG=4201955800*"
$ExpectedStage11 = "*VP=38 VPF=30 VPR=88 VPS=8 VPO=0 CPM=727 FPM=932 FSP=169 FPIX=20791 SKYV=0 SKYC=0 SKYP=0 FSK=0 SPO=0 F11F=81 F11FN=SLIME14 C11F=113 C11N=FLOOR5_2 FSIG=2178063413*"
$ExpectedStage12 = "*SKCAND=40 MCAND=27 PROBE=1 PSKY=0 PMASK=0 SKYSEC=2 MSIDE=617 PVX=1771 PVY=-773 PVA=277 PSEC=196 SKYT=229 SKYN=SKY1 SCOL=32 SPIX=1280 MTEX=814 MN=AQMETL29 MCOL12=32 MPOST=32 MPIX=1888 SPR=0 SSK=0 S12SIG=2853564869*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedClip -and
          $Process.MainWindowTitle -like $ExpectedProjection -and
          $Process.MainWindowTitle -like $ExpectedTexture -and
          $Process.MainWindowTitle -like $ExpectedStage09 -and
          $Process.MainWindowTitle -like $ExpectedStage10 -and
          $Process.MainWindowTitle -like $ExpectedStage11 -and
          $Process.MainWindowTitle -like $ExpectedStage12) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage12_sky_and_masked_midtextures_debug.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedClip -or
    $Process.MainWindowTitle -notlike $ExpectedProjection -or
    $Process.MainWindowTitle -notlike $ExpectedTexture -or
    $Process.MainWindowTitle -notlike $ExpectedStage09 -or
    $Process.MainWindowTitle -notlike $ExpectedStage10 -or
    $Process.MainWindowTitle -notlike $ExpectedStage11 -or
    $Process.MainWindowTitle -notlike $ExpectedStage12) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage12_sky_and_masked_midtextures_debug.exe did not report the expected sky/masked counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage12_sky_and_masked_midtextures_debug.exe did not close cleanly"
}
```

Stage12 preserves the stage11 primary player-start renderer and counters. The
primary view has no sky or masked midtexture work, so the executable also draws
a deterministic MAP01 feature-probe proof using real pinned IWAD `SKY1` and
`AQMETL29` columns, then reports a wall+flat+sky+masked RGB signature.

## Source Stage 13 Things Sprites And Real Frame Setup

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage13_things_sprites_and_real_frame_setup.py
```

Expected output:

```text
build/source_stage13_things_sprites_and_real_frame_setup.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage13_things_sprites_and_real_frame_setup.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedClip = "*VN=697 VSS=698 VSEG=2233 BVN=559 BVSS=513 BVSEG=1709 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1*"
$ExpectedProjection = "*PRJ=86 MIND=2073560 MAXD=58720255 MINS=11702 MAXS=108495*"
$ExpectedTexture = "*TEX=963 PN=1054 FLAT=246 DIRC=80797 COMPC=26323 FPTEX=850 LPTEX=13 EMID=1*"
$ExpectedStage09 = "*DWSP=86 OPQSP=24 DCOL=297 DRAW=162 SKC=135 SKU=62 ZTEX=0 MASK=0 FTEX=850 FN=AQRUST08 FCOL=127 PIX=15508 SIG=2194105880*"
$ExpectedStage10 = "*CMB=89 CMH=75 CMO=0 MCOL=2 MCEMP=133 UCOL=478 UCOMP=6 LCOL=138 PM=1659 F10TEX=850 F10N=AQRUST08 L10TEX=887 L10N=AQSECT08 TCOL=780 TPIX=37546 TSIG=4201955800*"
$ExpectedStage11 = "*VP=38 VPF=30 VPR=88 VPS=8 VPO=0 CPM=727 FPM=932 FSP=169 FPIX=20791 SKYV=0 SKYC=0 SKYP=0 FSK=0 SPO=0 F11F=81 F11FN=SLIME14 C11F=113 C11N=FLOOR5_2 FSIG=2178063413*"
$ExpectedStage12 = "*SKCAND=40 MCAND=27 PROBE=1 PSKY=0 PMASK=0 SKYSEC=2 MSIDE=617 PVX=1771 PVY=-773 PVA=277 PSEC=196 SKYT=229 SKYN=SKY1 SCOL=32 SPIX=1280 MTEX=814 MN=AQMETL29 MCOL12=32 MPOST=32 MPIX=1888 SPR=0 SSK=0 S12SIG=2853564869*"
$ExpectedStage13 = "*TH=200 PST=4 RMO=120 UTH=2 SKSK=17 PSX=-192 PSY=-192 PSA=0 PSS=0 SPNAMES=138 SPLUMPS=1350 SPMISS=0 SPSEC=29 VIS=6 VISOV=0 SPROBE=0 FSTH=8 FSPR=60 FSN=BON1 FSF=0 FSPT=1009 FSPN=BON1A0 SPCOL=35 SPPOST=40 SPPIX=175 S13SIG=2904743961*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedClip -and
          $Process.MainWindowTitle -like $ExpectedProjection -and
          $Process.MainWindowTitle -like $ExpectedTexture -and
          $Process.MainWindowTitle -like $ExpectedStage09 -and
          $Process.MainWindowTitle -like $ExpectedStage10 -and
          $Process.MainWindowTitle -like $ExpectedStage11 -and
          $Process.MainWindowTitle -like $ExpectedStage12 -and
          $Process.MainWindowTitle -like $ExpectedStage13) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage13_things_sprites_and_real_frame_setup.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedClip -or
    $Process.MainWindowTitle -notlike $ExpectedProjection -or
    $Process.MainWindowTitle -notlike $ExpectedTexture -or
    $Process.MainWindowTitle -notlike $ExpectedStage09 -or
    $Process.MainWindowTitle -notlike $ExpectedStage10 -or
    $Process.MainWindowTitle -notlike $ExpectedStage11 -or
    $Process.MainWindowTitle -notlike $ExpectedStage12 -or
    $Process.MainWindowTitle -notlike $ExpectedStage13) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage13_things_sprites_and_real_frame_setup.exe did not report the expected THINGS/sprite counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage13_things_sprites_and_real_frame_setup.exe did not close cleanly"
}
```

Stage13 preserves the stage12 renderer and counters, decodes real `MAP01`
`THINGS`, seeds the fixed frame from the real player-one start, gathers primary
frame sprites through source-shaped sector lists, draws real sprite patch posts
through the masked-column primitive, and reports a deterministic stage13 RGB
signature.

## Source Stage 14 Game Loop Input Collision

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage14_game_loop_input_collision.py
```

Expected output:

```text
build/source_stage14_game_loop_input_collision.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage14_game_loop_input_collision.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage13 = "*TH=200 PST=4 RMO=120 UTH=2 SKSK=17 PSX=-192 PSY=-192 PSA=0 PSS=0 SPNAMES=138 SPLUMPS=1350 SPMISS=0 SPSEC=29 VIS=6 VISOV=0 SPROBE=0 FSTH=8 FSPR=60 FSN=BON1 FSF=0 FSPT=1009 FSPN=BON1A0 SPCOL=35 SPPOST=40 SPPIX=175 S13SIG=2904743961*"
$ExpectedStage14 = "*BMW=20 BMH=27 TIC=8 I14X=-192 I14Y=-192 F14X=-172 F14Y=-194 F14A=3 F14SS=227 F14SEC=0 F14VZ=2753061 F14MX=183699 F14MY=-36831 ACPT=8 REJ14=0 LCHK=48 TCHK=0 BLI=8 BTI=16 LDUP=8 SDEF=0 CPROBE=1 CLINE=0 CBLK=1 CBLN=1 RLINK=8 S14SIG=3925602456*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage13 -and
          $Process.MainWindowTitle -like $ExpectedStage14) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage14_game_loop_input_collision.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStage13 -or
    $Process.MainWindowTitle -notlike $ExpectedStage14) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage14_game_loop_input_collision.exe did not report the expected movement/collision counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage14_game_loop_input_collision.exe did not close cleanly"
}
```

Stage14 preserves the stage13 fixed renderer and counters, loads the real
`MAP01` `BLOCKMAP`, advances an eight-tic deterministic local command script
through source-shaped player/mobj/collision movement, relinks the moved player
through sector/block state, records final `R_SetupFrame` fields, and reports a
separate bounded MAP01 blocking-line probe.

## Source Stage 15 Pickups Psprites Statusbar Shell

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage15_pickups_psprites_statusbar_shell.py
```

Expected output:

```text
build/source_stage15_pickups_psprites_statusbar_shell.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage15_pickups_psprites_statusbar_shell.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage13 = "*TH=200 PST=4 RMO=120 UTH=2 SKSK=17 PSX=-192 PSY=-192 PSA=0 PSS=0 SPNAMES=138 SPLUMPS=1350 SPMISS=0 SPSEC=29 VIS=6 VISOV=0 SPROBE=0 FSTH=8 FSPR=60 FSN=BON1 FSF=0 FSPT=1009 FSPN=BON1A0 SPCOL=35 SPPOST=40 SPPIX=175 S13SIG=2904743961*"
$ExpectedStage14 = "*BMW=20 BMH=27 TIC=8 I14X=-192 I14Y=-192 F14X=-172 F14Y=-194 F14A=3 F14SS=227 F14SEC=0 F14VZ=2753061 F14MX=183699 F14MY=-36831 ACPT=8 REJ14=0 LCHK=48 TCHK=0 BLI=8 BTI=16 LDUP=8 SDEF=0 CPROBE=1 CLINE=0 CBLK=1 CBLN=1 RLINK=8 S14SIG=3925602456*"
$ExpectedStage15 = "*PPROBE=2 PACC=2 PREM=2 P1=27 P1N=SHOT P2=41 P2N=CLIP HP=100 ARM=0 AT=0 CLIP=60 SHELL=8 WOWN=3 RDY=2 PEND=9 PSPST=18 PSPN=S_SGUN PSPT=1 STP=11 STCOL=469 STPIX=12533 WPN=SHTGA0 WPCOL=66 WPPIX=2083 MDEF=2 SNDDEF=2 S15SIG=2810145191*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage13 -and
          $Process.MainWindowTitle -like $ExpectedStage14 -and
          $Process.MainWindowTitle -like $ExpectedStage15) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage15_pickups_psprites_statusbar_shell.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStage13 -or
    $Process.MainWindowTitle -notlike $ExpectedStage14 -or
    $Process.MainWindowTitle -notlike $ExpectedStage15) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage15_pickups_psprites_statusbar_shell.exe did not report the expected pickup/status counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage15_pickups_psprites_statusbar_shell.exe did not close cleanly"
}
```

Stage15 preserves the stage14 movement/collision baseline, then runs a separate
fixed MAP01 pickup proof through the special-touch path for shotgun mapthing
`27` and clip mapthing `41`. Inventory mutates through source-shaped grant
helpers, psprites raise the shotgun to `S_SGUN`, and real status/weapon patch
columns report deterministic pixel counts and signature.

## Source Stage 16 Active Monster Thinkers And Targeting

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage16_active_monster_thinkers_and_targeting.py
```

Expected output:

```text
build/source_stage16_active_monster_thinkers_and_targeting.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage16_active_monster_thinkers_and_targeting.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage13 = "*TH=200 PST=4 RMO=120 UTH=2 SKSK=17 PSX=-192 PSY=-192 PSA=0 PSS=0 SPNAMES=138 SPLUMPS=1350 SPMISS=0 SPSEC=29 VIS=6 VISOV=0 SPROBE=0 FSTH=8 FSPR=60 FSN=BON1 FSF=0 FSPT=1009 FSPN=BON1A0 SPCOL=35 SPPOST=40 SPPIX=175 S13SIG=2904743961*"
$ExpectedStage14 = "*BMW=20 BMH=27 TIC=8 I14X=-192 I14Y=-192 F14X=-172 F14Y=-194 F14A=3 F14SS=227 F14SEC=0 F14VZ=2753061 F14MX=183699 F14MY=-36831 ACPT=8 REJ14=0 LCHK=48 TCHK=0 BLI=8 BTI=16 LDUP=8 SDEF=0 CPROBE=1 CLINE=0 CBLK=1 CBLN=1 RLINK=8 S14SIG=3925602456*"
$ExpectedStage15 = "*PPROBE=2 PACC=2 PREM=2 P1=27 P1N=SHOT P2=41 P2N=CLIP HP=100 ARM=0 AT=0 CLIP=60 SHELL=8 WOWN=3 RDY=2 PEND=9 PSPST=18 PSPN=S_SGUN PSPT=1 STP=11 STCOL=469 STPIX=12533 WPN=SHTGA0 WPCOL=66 WPPIX=2083 MDEF=2 SNDDEF=2 S15SIG=2810145191*"
$ExpectedStage16 = "*MCENS=18 ACTM=1 TADD=1 TRUN=13 MT16=37 MO16=28 M16N=SHOTGUY M16X=1752 M16Y=-936 M16SEC=58 M16BX=15 M16BY=6 MTIC0=3 LLOOK=1 LOOK=2 LFP=2 SIGHT=1 SOK=1 SNODE=77 SSUB=28 SLINE=5 TGT=1 ST0=207 STFN=S_SPOS_RUN1 STF=209 FTIC=3 CHDEF=1 SND16=1 ATK=0 DMG=0 KILL=0 S16SIG=249707937*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage13 -and
          $Process.MainWindowTitle -like $ExpectedStage14 -and
          $Process.MainWindowTitle -like $ExpectedStage15 -and
          $Process.MainWindowTitle -like $ExpectedStage16) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage16_active_monster_thinkers_and_targeting.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStage13 -or
    $Process.MainWindowTitle -notlike $ExpectedStage14 -or
    $Process.MainWindowTitle -notlike $ExpectedStage15 -or
    $Process.MainWindowTitle -notlike $ExpectedStage16) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage16_active_monster_thinkers_and_targeting.exe did not report the expected active-monster counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage16_active_monster_thinkers_and_targeting.exe did not close cleanly"
}
```

Stage16 preserves the stage15 pickup/status/psprite baseline, then selects real
MAP01 shotgun-guy mapthing `37` / mobj `28`, runs it as one active thinker for
`13` bounded tics, advances `S_SPOS_STND -> S_SPOS_STND2 -> S_SPOS_RUN1`,
acquires the player through `A_Look`, `P_LookForPlayers`, and a bounded
REJECT+BSP `P_CheckSight` probe, and stops at a counted chase deferral with no
attacks, damage, kills, or drops.

## Source Stage 17 First Weapon Fire Damage And Death Probe

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage17_first_weapon_fire_damage_and_death_probe.py
```

Expected output:

```text
build/source_stage17_first_weapon_fire_damage_and_death_probe.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage17_first_weapon_fire_damage_and_death_probe.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage13 = "*TH=200 PST=4 RMO=120 UTH=2 SKSK=17 PSX=-192 PSY=-192 PSA=0 PSS=0 SPNAMES=138 SPLUMPS=1350 SPMISS=0 SPSEC=29 VIS=6 VISOV=0 SPROBE=0 FSTH=8 FSPR=60 FSN=BON1 FSF=0 FSPT=1009 FSPN=BON1A0 SPCOL=35 SPPOST=40 SPPIX=175 S13SIG=2904743961*"
$ExpectedStage14 = "*BMW=20 BMH=27 TIC=8 I14X=-192 I14Y=-192 F14X=-172 F14Y=-194 F14A=3 F14SS=227 F14SEC=0 F14VZ=2753061 F14MX=183699 F14MY=-36831 ACPT=8 REJ14=0 LCHK=48 TCHK=0 BLI=8 BTI=16 LDUP=8 SDEF=0 CPROBE=1 CLINE=0 CBLK=1 CBLN=1 RLINK=8 S14SIG=3925602456*"
$ExpectedStage15 = "*PPROBE=2 PACC=2 PREM=2 P1=27 P1N=SHOT P2=41 P2N=CLIP HP=100 ARM=0 AT=0 CLIP=60 SHELL=8 WOWN=3 RDY=2 PEND=9 PSPST=18 PSPN=S_SGUN PSPT=1 STP=11 STCOL=469 STPIX=12533 WPN=SHTGA0 WPCOL=66 WPPIX=2083 MDEF=2 SNDDEF=2 S15SIG=2810145191*"
$ExpectedStage16 = "*MCENS=18 ACTM=1 TADD=1 TRUN=13 MT16=37 MO16=28 M16N=SHOTGUY M16X=1752 M16Y=-936 M16SEC=58 M16BX=15 M16BY=6 MTIC0=3 LLOOK=1 LOOK=2 LFP=2 SIGHT=1 SOK=1 SNODE=77 SSUB=28 SLINE=5 TGT=1 ST0=207 STFN=S_SPOS_RUN1 STF=209 FTIC=3 CHDEF=1 SND16=1 ATK=0 DMG=0 KILL=0 S16SIG=249707937*"
$ExpectedStage17 = "*ACENS=1 ATMO=0 TGMO=28 W17=2 WACT=A_FireShotgun CANG=0 AANG=254 TBRG=254 ADEL=254 CMISS=1 AIMFIX=1 S17LOS=1 SH0=8 SH1=7 PSP17=22 PSP17N=S_SGUN2 PSP17T=7 FLS=30 FLSN=S_SGUNFLASH1 FLT=3 AIM=5 LNA=7 PATH=12 LI=71 TI=33 HIT17=1 DEVT=1 DMG17=10 HP0=30 H17=20 ST17N=S_SPOS_PAIN ST17=220 PAIN=1 KILL17=0 DROPDEF=0 ST17PIX=12525 WP17PIX=2083 CHASEMV=0 LIVEIN=0 S17SIG=2157381017*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage13 -and
          $Process.MainWindowTitle -like $ExpectedStage14 -and
          $Process.MainWindowTitle -like $ExpectedStage15 -and
          $Process.MainWindowTitle -like $ExpectedStage16 -and
          $Process.MainWindowTitle -like $ExpectedStage17) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage17_first_weapon_fire_damage_and_death_probe.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStage13 -or
    $Process.MainWindowTitle -notlike $ExpectedStage14 -or
    $Process.MainWindowTitle -notlike $ExpectedStage15 -or
    $Process.MainWindowTitle -notlike $ExpectedStage16 -or
    $Process.MainWindowTitle -notlike $ExpectedStage17) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage17_first_weapon_fire_damage_and_death_probe.exe did not report the expected first-damage counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage17_first_weapon_fire_damage_and_death_probe.exe did not close cleanly"
}
```

Stage17 preserves the stage16 active-monster baseline, then freezes the
source-shaped player-to-target attack angle, advances the ready shotgun through
the bounded fire psprite path, spends one shell, runs the hitscan line path, and
mutates the selected shotgun guy from `30` health to `20` health through
`P_DamageMobj`. The selected proof is nonlethal, so death, removal, and drop
counters remain zero.

## Source Stage 18 Post Damage Monster Movement And Chase Probe

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage18_post_damage_monster_movement_and_chase_probe.py
```

Expected output:

```text
build/source_stage18_post_damage_monster_movement_and_chase_probe.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage18_post_damage_monster_movement_and_chase_probe.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage17 = "*ACENS=1 ATMO=0 TGMO=28 W17=2 WACT=A_FireShotgun CANG=0 AANG=254 TBRG=254 ADEL=254 CMISS=1 AIMFIX=1 S17LOS=1 SH0=8 SH1=7 PSP17=22 PSP17N=S_SGUN2 PSP17T=7 FLS=30 FLSN=S_SGUNFLASH1 FLT=3 AIM=5 LNA=7 PATH=12 LI=71 TI=33 HIT17=1 DEVT=1 DMG17=10 HP0=30 H17=20 ST17N=S_SPOS_PAIN ST17=220 PAIN=1 KILL17=0 DROPDEF=0 ST17PIX=12525 WP17PIX=2083 CHASEMV=0 LIVEIN=0 S17SIG=2157381017*"
$ExpectedStage18 = "*M18R=1 M18TIC=1 MT18=37 MO18=28 M18N=SHOTGUY S18X=1752 S18Y=-936 S18BX=15 S18BY=6 S18STN=S_SPOS_PAIN S18ST=220 S18T=3 MX0=-22182 MY0=-78859 F18X=1751 F18Y=-938 F18BX=15 F18BY=6 F18STN=S_SPOS_PAIN F18ST=220 F18T=2 MX18=-20103 MY18=-71466 XY18=1 TRY18=1 MACC=1 MREJ=0 MLCHK=8 MTCHK=0 MBLI=1 MBTI=4 MLDUP=0 MBRL=1 MSRL=1 PAINTIC=1 P18DEF=0 CH18=0 NCD18=0 PMV18=0 ATK18=0 ATKEX18=0 S18SIG=1615679087*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage17 -and
          $Process.MainWindowTitle -like $ExpectedStage18) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage18_post_damage_monster_movement_and_chase_probe.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStage17 -or
    $Process.MainWindowTitle -notlike $ExpectedStage18) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage18_post_damage_monster_movement_and_chase_probe.exe did not report the expected post-damage movement counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage18_post_damage_monster_movement_and_chase_probe.exe did not close cleanly"
}
```

Stage18 preserves the stage17 first-damage baseline, then advances the damaged
shotgun guy for one source-ordered `P_MobjThinker` tic. `P_XYMovement` services
the stage17 thrust momentum before pain recovery, calls real MAP01
`P_TryMove`/block iterators, accepts the move from `(1752,-936)` to
`(1751,-938)`, applies friction to momentum, and leaves chase/attack execution
deferred.

## Source Stage 19 First Door Or Switch Sector Special Probe

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage19_first_door_or_switch_sector_special_probe.py
```

Expected output:

```text
build/source_stage19_first_door_or_switch_sector_special_probe.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage19_first_door_or_switch_sector_special_probe.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage17 = "*ACENS=1 ATMO=0 TGMO=28 W17=2 WACT=A_FireShotgun CANG=0 AANG=254 TBRG=254 ADEL=254 CMISS=1 AIMFIX=1 S17LOS=1 SH0=8 SH1=7 PSP17=22 PSP17N=S_SGUN2 PSP17T=7 FLS=30 FLSN=S_SGUNFLASH1 FLT=3 AIM=5 LNA=7 PATH=12 LI=71 TI=33 HIT17=1 DEVT=1 DMG17=10 HP0=30 H17=20 ST17N=S_SPOS_PAIN ST17=220 PAIN=1 KILL17=0 DROPDEF=0 ST17PIX=12525 WP17PIX=2083 CHASEMV=0 LIVEIN=0 S17SIG=2157381017*"
$ExpectedStage18 = "*M18R=1 M18TIC=1 MT18=37 MO18=28 M18N=SHOTGUY S18X=1752 S18Y=-936 S18BX=15 S18BY=6 S18STN=S_SPOS_PAIN S18ST=220 S18T=3 MX0=-22182 MY0=-78859 F18X=1751 F18Y=-938 F18BX=15 F18BY=6 F18STN=S_SPOS_PAIN F18ST=220 F18T=2 MX18=-20103 MY18=-71466 XY18=1 TRY18=1 MACC=1 MREJ=0 MLCHK=8 MTCHK=0 MBLI=1 MBTI=4 MLDUP=0 MBRL=1 MSRL=1 PAINTIC=1 P18DEF=0 CH18=0 NCD18=0 PMV18=0 ATK18=0 ATKEX18=0 S18SIG=1615679087*"
$ExpectedStage19 = "*S19LINE=332 SIDE=0 S19SEC=56 S19SPEC=117 S19TEX=BIGDOOR1 PROBE19=1 U19X=1792 U19Y=-160 U19A=0 P18USE=0 P18DIST=456 PATH19=1 BLK19=1 LI19=5 TRV19=1 USE19=1 BACK19=0 TERM19=1 VD19=1 DTH19=1 TOP19=108 F19=16 C190=16 C191=24 DIR19=1 SPD19=8 TWAIT19=150 TD19=1 MP19=1 MPR19=0 PAST19=0 CRUSH19=0 SND19=1 SWDEF19=0 BTNDEF19=0 GSPEC19=0 GDOOR19=0 GSECT19=0 AUD19=1 LIVE19=0 S19SIG=2088411722*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage17 -and
          $Process.MainWindowTitle -like $ExpectedStage18 -and
          $Process.MainWindowTitle -like $ExpectedStage19) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage19_first_door_or_switch_sector_special_probe.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStage17 -or
    $Process.MainWindowTitle -notlike $ExpectedStage18 -or
    $Process.MainWindowTitle -notlike $ExpectedStage19) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage19_first_door_or_switch_sector_special_probe.exe did not report the expected manual door mutation counts"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage19_first_door_or_switch_sector_special_probe.exe did not close cleanly"
}
```

Stage19 preserves the stage18 post-damage movement baseline, then activates real
MAP01 linedef `332` from a fixed front-side use probe. The bounded route reaches
`P_UseSpecialLine`, `EV_VerticalDoor`, `P_FindLowestCeilingSurrounding`,
`T_VerticalDoor`, and `T_MovePlane`, spawns one table-emitted blazing-door
thinker record, and mutates sector `56` ceiling from `16` to `24` map units.
Switch/button behavior, broad special systems, real sound output, and live input
remain counted boundaries.

## Source Stage 20 Audio Channels And Deferred Sound Playback

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage20_audio_channels_and_deferred_sound_playback.py
```

Expected output:

```text
build/source_stage20_audio_channels_and_deferred_sound_playback.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage20_audio_channels_and_deferred_sound_playback.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage19 = "*S19LINE=332 SIDE=0 S19SEC=56 S19SPEC=117 S19TEX=BIGDOOR1 PROBE19=1 U19X=1792 U19Y=-160 U19A=0 P18USE=0 P18DIST=456 PATH19=1 BLK19=1 LI19=5 TRV19=1 USE19=1 BACK19=0 TERM19=1 VD19=1 DTH19=1 TOP19=108 F19=16 C190=16 C191=24 DIR19=1 SPD19=8 TWAIT19=150 TD19=1 MP19=1 MPR19=0 PAST19=0 CRUSH19=0 SND19=1 SWDEF19=0 BTNDEF19=0 GSPEC19=0 GDOOR19=0 GSECT19=0 AUD19=1 LIVE19=0 S19SIG=2088411722*"
$ExpectedStage20 = "*S20CALL=1 S20LINE=332 S20SEC=56 S20ID=88 S20N=bdopn S20PRI=100 CHS20=8 CH20=0 ORG20=56 O20X=1832 O20Y=-160 L20X=1792 L20Y=-160 DIST20=40 VOL20=64 SEP20=129 P200=127 RND20=8 P201=135 STOP20=1 SAME20=0 GET20=1 FREE20=1 REP20=0 NOCH20=0 USE200=-1 USE201=1 LDEF20=1 LUMP20=0 IST20=1 H20=0 PLAY20=0 AUD20=1 MIX20=0 MUS20=0 ALLS20=0 CACH20=0 S20SIG=3226031347*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage19 -and
          $Process.MainWindowTitle -like $ExpectedStage20) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage20_audio_channels_and_deferred_sound_playback.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStage19 -or
    $Process.MainWindowTitle -notlike $ExpectedStage20) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage20_audio_channels_and_deferred_sound_playback.exe did not report the expected sound-channel state"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage20_audio_channels_and_deferred_sound_playback.exe did not close cleanly"
}
```

Stage20 preserves the stage19 manual door mutation, then turns the reached
`EV_VerticalDoor -> S_StartSound(&sec->soundorg, sfx_bdopn)` boundary into one
source-shaped sound channel record. It resolves `S_sfx[sfx_bdopn]` from source
metadata, computes sector-origin volume/separation and deterministic pitch,
selects channel `0`, increments usefulness, records the deferred lump/platform
sound calls, and still produces no speaker output.

## Source Stage 21 Door Thinker Ticker And Special Update Probe

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage21_door_thinker_ticker_and_special_update_probe.py
```

Expected output:

```text
build/source_stage21_door_thinker_ticker_and_special_update_probe.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage21_door_thinker_ticker_and_special_update_probe.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage19 = "*S19LINE=332 SIDE=0 S19SEC=56 S19SPEC=117*S19SIG=2088411722*"
$ExpectedStage20 = "*S20CALL=1 S20LINE=332 S20SEC=56 S20ID=88 S20N=bdopn*S20SIG=3226031347*"
$ExpectedStage21 = "*S21SEC=56 CAP21=1 ADD21=1 NODE21=1 LNK21=4 PTIC21=2 RUN21=2 ITER21=2 DISP21=2 NEXT21=2 TVD21=2 MP21=2 C210=16 C211=24 C212=32 TOP21=108 SPD21=8 DIR21=1 WAIT21=150 TCNT21=0 PLY21=2 UPD21=2 RESP21=2 LT210=0 LT211=2 ORDER21=1 PAUSE21=0 MENU21=0 ANIM21=0 SCRL21=0 BTN21=0 EXIT21=0 REM21=0 CLOSE21=0 SND21=0 AUD21=0 MIX21=0 MUS21=0 LIVE21=0 S21SIG=1770773845*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage19 -and
          $Process.MainWindowTitle -like $ExpectedStage20 -and
          $Process.MainWindowTitle -like $ExpectedStage21) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage21_door_thinker_ticker_and_special_update_probe.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStage19 -or
    $Process.MainWindowTitle -notlike $ExpectedStage20 -or
    $Process.MainWindowTitle -notlike $ExpectedStage21) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage21_door_thinker_ticker_and_special_update_probe.exe did not report the expected thinker ticker proof"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage21_door_thinker_ticker_and_special_update_probe.exe did not close cleanly"
}
```

Stage21 preserves the stage20 sound-channel proof and stage19's direct manual
door tic, then clones the selected sector `56` door state into a bounded normal
ticker proof. Two source-ordered `P_Ticker` calls dispatch one door thinker via
`P_RunThinkers`, advance `T_VerticalDoor -> T_MovePlane`, and mutate the cloned
ceiling sequence `16 -> 24 -> 32`. `P_UpdateSpecials` and
`P_RespawnSpecials` are present as counted guards only.

## Source Stage 22 First Switch Texture And Tagged Door Probe

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage22_first_switch_texture_and_tagged_door_probe.py
```

Expected output:

```text
build/source_stage22_first_switch_texture_and_tagged_door_probe.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage22_first_switch_texture_and_tagged_door_probe.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage19 = "*S19LINE=332*S19SIG=2088411722*"
$ExpectedStage20 = "*S20CALL=1*S20SIG=3226031347*"
$ExpectedStage21 = "*S21SEC=56*S21SIG=1770773845*"
$ExpectedStage22 = "*S22LINE=839 S22SPEC=103 TAG22=4 SIDE22=0 RSID22=1289 LSID22=1290 SLOT22=2 TEX220=SW2COMP TEX221=SW1COMP PAIR22=6 SWI22=13 SPC221=0 PATH22=1 LI22=7 TRV22=2 EV22=1 TFIND22=1 TITER22=211 TSEC22=208 F22=-80 C220=-80 LOW22=0 TOP22=-4 DIR22=1 SPD22=2 WAIT22=150 ADD22=1 PTIC22=1 TVD22=1 MP22=1 C221=-78 UPD22=1 BTN22=0 REM22=0 CLOSE22=0 SWSND22=1 AUD22=0 GEN22=0 S22SIG=2207028069*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage19 -and
          $Process.MainWindowTitle -like $ExpectedStage20 -and
          $Process.MainWindowTitle -like $ExpectedStage21 -and
          $Process.MainWindowTitle -like $ExpectedStage22) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage22_first_switch_texture_and_tagged_door_probe.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStage19 -or
    $Process.MainWindowTitle -notlike $ExpectedStage20 -or
    $Process.MainWindowTitle -notlike $ExpectedStage21 -or
    $Process.MainWindowTitle -notlike $ExpectedStage22) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage22_first_switch_texture_and_tagged_door_probe.exe did not report the expected switch/tagged-door proof"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage22_first_switch_texture_and_tagged_door_probe.exe did not close cleanly"
}
```

Stage22 preserves the stage21 ticker proof, then activates real MAP01 linedef
`839` through the bounded source-shaped use-line route. It mutates front lower
texture `SW2COMP -> SW1COMP`, clears the one-shot line special, resolves tag
`4` to sector `208`, spawns one `vld_open` door thinker, and advances the new
tagged door ceiling from `-80` to `-78` in one normal ticker tic. Reusable
button restoration, broad specials, broad doors/switches, and real speaker
playback remain deferred.

## Source Stage 23 First Button Timer Restore Probe

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage23_first_button_timer_restore_probe.py
```

Expected output:

```text
build/source_stage23_first_button_timer_restore_probe.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage23_first_button_timer_restore_probe.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage19 = "*S19LINE=332*S19SIG=2088411722*"
$ExpectedStage20 = "*S20CALL=1*S20SIG=3226031347*"
$ExpectedStage21 = "*S21SEC=56*S21SIG=1770773845*"
$ExpectedStage22 = "*S22LINE=839*S22SIG=2207028069*"
$ExpectedStage23 = "*S23MAP=15 S23LINE=3452 S23SPEC=61 TAG23=24 SIDE23=0 RSID23=4798 LSID23=65535 FSEC23=548 SLOT23=1 TEX230=SW1COMP TEX231=SW2COMP TEX232=SW1COMP PAIR23=6 SWI23=12 SPC231=61 BSLOT23=0 BOLD23=292 BT230=35 BT231=0 BDUP23=-1 UPD23=35 BDEC23=35 BREST23=1 BCLR23=1 BOFFSND23=1 TSEC23=530 F23=-64 C230=48 LOW23=56 TOP23=52 DIR23=1 SPD23=2 WAIT23=150 PTIC23=35 TVD23=3 MP23=3 REM23=1 LT23=35 ORDER23=1 MAP01BTN23=0 CENS23=72 DOORBTN23=8 AUD23=0 GEN23=0 FALL23=0 S24ABS=1 S23SIG=3216085132*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage19 -and
          $Process.MainWindowTitle -like $ExpectedStage20 -and
          $Process.MainWindowTitle -like $ExpectedStage21 -and
          $Process.MainWindowTitle -like $ExpectedStage22 -and
          $Process.MainWindowTitle -like $ExpectedStage23) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage23_first_button_timer_restore_probe.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStage19 -or
    $Process.MainWindowTitle -notlike $ExpectedStage20 -or
    $Process.MainWindowTitle -notlike $ExpectedStage21 -or
    $Process.MainWindowTitle -notlike $ExpectedStage22 -or
    $Process.MainWindowTitle -notlike $ExpectedStage23) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage23_first_button_timer_restore_probe.exe did not report the expected button restore proof"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage23_first_button_timer_restore_probe.exe did not close cleanly"
}
```

Stage23 preserves the stage22 switch/tagged-door proof, then activates real
MAP15 linedef `3452` through the selected source-shaped reusable button route.
It mutates front middle texture `SW1COMP -> SW2COMP`, preserves line special
`61`, allocates one button slot with timer `35`, resolves tag `24` to sector
`530`, and runs bounded ticker/update-special tics until the button restores
`SW1COMP` and clears its slot. Real speaker playback, generalized specials,
generalized floors/plats, and map progression remain deferred.

## Source Stage 24 First Floor Sector Special Probe

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage24_first_floor_sector_special_probe.py
```

Expected output:

```text
build/source_stage24_first_floor_sector_special_probe.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage24_first_floor_sector_special_probe.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage19 = "*S19LINE=332*S19SIG=2088411722*"
$ExpectedStage20 = "*S20CALL=1*S20SIG=3226031347*"
$ExpectedStage21 = "*S21SEC=56*S21SIG=1770773845*"
$ExpectedStage22 = "*S22LINE=839*S22SIG=2207028069*"
$ExpectedStage23 = "*S23LINE=3452*S23SIG=3216085132*"
$ExpectedStage24 = "*S24LINE=391 S24SPEC=60 TAG24=6 SIDE24=0 RSID24=564 LSID24=-1 FSEC24=59 SLOT24=1 TEX240=SW1BROWN TEX241=SW2BROWN TEX242=SW1BROWN PAIR24=4 SWI24=8 SPC241=60 BSLOT24=0 BT240=35 BT241=0 BREST24=1 BCLR24=1 EVF24=1 TFIND24=2 TITER24=648 TSEC24=57 F240=16 F241=-48 C24=144 SSPEC24=0 LOWF24=-48 DEST24=-48 DIR24=-1 SPD24=1 ADD24=1 PTIC24=66 TMF24=65 MP24=65 FMUT24=64 PAST24=1 REM24=1 LREM24=1 MSND24=9 STOP24=1 LT24=66 ORDER24=1 AUD24=0 GENF24=1 GPLAT24=1 GCEIL24=1 S25ABS=1 S24SIG=1919312263*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage19 -and
          $Process.MainWindowTitle -like $ExpectedStage20 -and
          $Process.MainWindowTitle -like $ExpectedStage21 -and
          $Process.MainWindowTitle -like $ExpectedStage22 -and
          $Process.MainWindowTitle -like $ExpectedStage23 -and
          $Process.MainWindowTitle -like $ExpectedStage24) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage24_first_floor_sector_special_probe.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStage19 -or
    $Process.MainWindowTitle -notlike $ExpectedStage20 -or
    $Process.MainWindowTitle -notlike $ExpectedStage21 -or
    $Process.MainWindowTitle -notlike $ExpectedStage22 -or
    $Process.MainWindowTitle -notlike $ExpectedStage23 -or
    $Process.MainWindowTitle -notlike $ExpectedStage24) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage24_first_floor_sector_special_probe.exe did not report the expected floor special proof"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage24_first_floor_sector_special_probe.exe did not close cleanly"
}
```

Stage24 preserves the stage23 reusable-button proof, then activates real MAP11
linedef `391` through the selected source-shaped reusable floor-button route.
It mutates front middle texture `SW1BROWN -> SW2BROWN`, preserves line special
`60`, allocates one button slot with timer `35`, resolves tag `6` to sector
`57`, and runs bounded ticker/update-special tics until the button restores and
the floor thinker moves sector `57` from `16` to `-48`, fires the pstop
boundary, and lazily unlinks. Real speaker playback, generalized floors/plats,
ceilings/crushers, stairs, donuts, and map progression remain deferred.

## Source Stage 25 First Platform Lift Cycle Probe

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage25_first_platform_lift_cycle_probe.py
```

Expected output:

```text
build/source_stage25_first_platform_lift_cycle_probe.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage25_first_platform_lift_cycle_probe.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage19 = "*S19LINE=332*S19SIG=2088411722*"
$ExpectedStage20 = "*S20CALL=1*S20SIG=3226031347*"
$ExpectedStage21 = "*S21SEC=56*S21SIG=1770773845*"
$ExpectedStage22 = "*S22LINE=839*S22SIG=2207028069*"
$ExpectedStage23 = "*S23LINE=3452*S23SIG=3216085132*"
$ExpectedStage24 = "*S24LINE=391*S24SIG=1919312263*"
$ExpectedStage25 = "*S25LINE=2304 S25SPEC=62 TAG25=26 SIDE25=0 RSID25=3005 LSID25=3004 FSEC25=228 SLOT25=2 TEX250=SW1STRTN TEX251=SW2STRTN TEX252=SW1STRTN PAIR25=18 SWI25=36 SPC251=62 BSLOT25=0 BT250=35 BT251=0 BREST25=1 BCLR25=1 EVP25=1 TFIND25=2 TITER25=863 TSEC25=77 F250=-8 F251=-8 C25=256 SSPEC25=0 LOW25=-64 HIGH25=-8 STAT25=1 SPD25=4 WAIT25=105 ASLOT25=0 ADD25=1 PTIC25=136 TPL25=135 MP25=30 PMUT25=28 PAST25=2 WT25=2 WDEC25=105 UP25=1 AREM25=1 ACLR25=1 LREM25=1 PSTART25=2 PSTOP25=2 LT25=136 ORDER25=1 AUD25=0 GENF25=1 GPLAT25=1 GCEIL25=1 S26ABS=1 S25SIG=1688844032*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage19 -and
          $Process.MainWindowTitle -like $ExpectedStage20 -and
          $Process.MainWindowTitle -like $ExpectedStage21 -and
          $Process.MainWindowTitle -like $ExpectedStage22 -and
          $Process.MainWindowTitle -like $ExpectedStage23 -and
          $Process.MainWindowTitle -like $ExpectedStage24 -and
          $Process.MainWindowTitle -like $ExpectedStage25) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage25_first_platform_lift_cycle_probe.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStage19 -or
    $Process.MainWindowTitle -notlike $ExpectedStage20 -or
    $Process.MainWindowTitle -notlike $ExpectedStage21 -or
    $Process.MainWindowTitle -notlike $ExpectedStage22 -or
    $Process.MainWindowTitle -notlike $ExpectedStage23 -or
    $Process.MainWindowTitle -notlike $ExpectedStage24 -or
    $Process.MainWindowTitle -notlike $ExpectedStage25) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage25_first_platform_lift_cycle_probe.exe did not report the expected platform lift cycle proof"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage25_first_platform_lift_cycle_probe.exe did not close cleanly"
}
```

Stage25 preserves the stage24 floor proof, then activates real MAP12 linedef
`2304` through the selected source-shaped reusable platform-button route. It
mutates front lower texture `SW1STRTN -> SW2STRTN`, preserves line special
`62`, allocates one button slot with timer `35`, resolves tag `26` to sector
`77`, allocates activeplats slot `0`, and runs bounded ticker/update-special
tics until the button restores and the platform moves `-8 -> -64`, waits,
restarts upward, returns `-64 -> -8`, clears activeplats and sector
`specialdata`, fires the deferred pstart/pstop boundaries, and lazily unlinks.
Real speaker playback, generalized platforms/lifts, generalized floors,
ceilings/crushers, stairs, donuts, and map progression remain deferred.

## Source Stage 26 First Ceiling Or Crusher Special Probe

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage26_first_ceiling_or_crusher_special_probe.py
```

Expected output:

```text
build/source_stage26_first_ceiling_or_crusher_special_probe.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage26_first_ceiling_or_crusher_special_probe.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage19 = "*S19LINE=332*S19SIG=2088411722*"
$ExpectedStage20 = "*S20CALL=1*S20SIG=3226031347*"
$ExpectedStage21 = "*S21SEC=56*S21SIG=1770773845*"
$ExpectedStage22 = "*S22LINE=839*S22SIG=2207028069*"
$ExpectedStage23 = "*S23LINE=3452*S23SIG=3216085132*"
$ExpectedStage24 = "*S24LINE=391*S24SIG=1919312263*"
$ExpectedStage25 = "*S25LINE=2304*S25SIG=1688844032*"
$ExpectedStage26 = "*S26LINE=71 S26SPEC=49 TAG26=40 SIDE26=0 RSID26=125 LSID26=-1 FSEC26=75 SLOT26=1 TEX260=SW1GSTON TEX261=SW2GSTON TEX262=SW2GSTON PAIR26=22 SWI26=44 SPC261=0 EVC26=1 TFIND26=2 TITER26=131 TSEC26=117 F26=192 C260=304 C261=304 SSPEC26=0 BOT26=200 TOP26=304 DIR260=-1 DIR261=-1 CRUSH26=1 SPD26=1 ASLOT26=0 ADD26=1 PTIC26=210 TMC26=210 MP26=210 CMUT26=208 PAST26=2 BREV26=1 TREV26=1 AREM26=0 ACLR26=0 LREM26=0 MSND26=27 PSTOP26=0 LT26=210 ORDER26=1 AUD26=0 GENF26=1 GPLAT26=1 GCEIL26=1 S27ABS=1 S26SIG=132405987*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage19 -and
          $Process.MainWindowTitle -like $ExpectedStage20 -and
          $Process.MainWindowTitle -like $ExpectedStage21 -and
          $Process.MainWindowTitle -like $ExpectedStage22 -and
          $Process.MainWindowTitle -like $ExpectedStage23 -and
          $Process.MainWindowTitle -like $ExpectedStage24 -and
          $Process.MainWindowTitle -like $ExpectedStage25 -and
          $Process.MainWindowTitle -like $ExpectedStage26) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage26_first_ceiling_or_crusher_special_probe.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStage19 -or
    $Process.MainWindowTitle -notlike $ExpectedStage20 -or
    $Process.MainWindowTitle -notlike $ExpectedStage21 -or
    $Process.MainWindowTitle -notlike $ExpectedStage22 -or
    $Process.MainWindowTitle -notlike $ExpectedStage23 -or
    $Process.MainWindowTitle -notlike $ExpectedStage24 -or
    $Process.MainWindowTitle -notlike $ExpectedStage25 -or
    $Process.MainWindowTitle -notlike $ExpectedStage26) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage26_first_ceiling_or_crusher_special_probe.exe did not report the expected ceiling/crusher proof"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage26_first_ceiling_or_crusher_special_probe.exe did not close cleanly"
}
```

Stage26 preserves the stage25 platform/lift proof, then activates real MAP29
linedef `71` through the selected source-shaped one-shot ceiling switch route.
It mutates front middle texture `SW1GSTON -> SW2GSTON`, clears line special
`49`, resolves tag `40` to sector `117`, allocates activeceilings slot `0`, and
runs 210 bounded ticker/update-special tics until the ceiling moves
`304 -> 200 -> 304`, reverses at both strict past-destination boundaries, and
remains active/cycling. Real speaker playback, generalized ceilings/crushers,
generalized floors/platforms, stairs, donuts, and map progression remain
deferred.

## Source Stage 27 Integrated Scripted Room Interaction Loop

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage27_integrated_scripted_room_interaction_loop.py
```

Expected output:

```text
build/source_stage27_integrated_scripted_room_interaction_loop.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage27_integrated_scripted_room_interaction_loop.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStage19 = "*S19SIG=2088411722*"
$ExpectedStage20 = "*S20SIG=3226031347*"
$ExpectedStage21 = "*S21SIG=1770773845*"
$ExpectedStage22 = "*S22SIG=2207028069*"
$ExpectedStage23 = "*S23SIG=3216085132*"
$ExpectedStage24 = "*S24SIG=1919312263*"
$ExpectedStage25 = "*S25SIG=1688844032*"
$ExpectedStage26 = "*S26SIG=132405987*"
$ExpectedStart = "*S27 LIVE START*STEP27=0*"
$ExpectedFinal = "*S27 LIVE STEP27=6*TIC27=136*F27=-8*TEX27=SW1STRTN*S27SIG=1735738182*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStart) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage27_integrated_scripted_room_interaction_loop.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStart) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage27_integrated_scripted_room_interaction_loop.exe did not report the start of the post-launch loop"
}

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStage19 -and
          $Process.MainWindowTitle -like $ExpectedStage20 -and
          $Process.MainWindowTitle -like $ExpectedStage21 -and
          $Process.MainWindowTitle -like $ExpectedStage22 -and
          $Process.MainWindowTitle -like $ExpectedStage23 -and
          $Process.MainWindowTitle -like $ExpectedStage24 -and
          $Process.MainWindowTitle -like $ExpectedStage25 -and
          $Process.MainWindowTitle -like $ExpectedStage26 -and
          $Process.MainWindowTitle -like $ExpectedFinal) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.MainWindowTitle -notlike $ExpectedStage19 -or
    $Process.MainWindowTitle -notlike $ExpectedStage20 -or
    $Process.MainWindowTitle -notlike $ExpectedStage21 -or
    $Process.MainWindowTitle -notlike $ExpectedStage22 -or
    $Process.MainWindowTitle -notlike $ExpectedStage23 -or
    $Process.MainWindowTitle -notlike $ExpectedStage24 -or
    $Process.MainWindowTitle -notlike $ExpectedStage25 -or
    $Process.MainWindowTitle -notlike $ExpectedStage26 -or
    $Process.MainWindowTitle -notlike $ExpectedFinal) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage27_integrated_scripted_room_interaction_loop.exe did not advance to the expected final scripted room loop title"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage27_integrated_scripted_room_interaction_loop.exe did not close cleanly"
}
```

Stage27 preserves the stage26 ceiling/crusher proof, then owns one bounded
MAP12 runtime world using the stage25 reusable platform-button route. A
deterministic `ticcmd_t` script issues one use command, then the normal ticker
loop samples the same world at six tics while the switch changes, the button
restores, the platform waits, restarts, and clears active state. After the
window is created, a timer updates the title through the six samples so the
proof visibly advances after launch. Manual input, speaker playback, map
progression, generalized combat, and broader special systems remain deferred.

## Source Stage 28 Live Input To Deterministic Game Loop Bridge

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage28_live_input_to_deterministic_game_loop_bridge.py
```

Expected output:

```text
build/source_stage28_live_input_to_deterministic_game_loop_bridge.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage28_live_input_to_deterministic_game_loop_bridge.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(5)
$ExpectedStart = "*S28 REPLAY START*STEP28=0*LIVE28=0*"
$ExpectedFinal = "*S28 REPLAY STEP28=6*LIVE28=0*TIC28=136*F28=-8*TEX28=SW1STRTN*S27SIG=1735738182*R28SIG=1735738182*S28SIG=2805406010*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStart) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage28_live_input_to_deterministic_game_loop_bridge.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStart) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage28_live_input_to_deterministic_game_loop_bridge.exe did not report the replay start marker"
}

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedFinal) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.MainWindowTitle -notlike $ExpectedFinal) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage28_live_input_to_deterministic_game_loop_bridge.exe did not advance to the expected final replay bridge title"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage28_live_input_to_deterministic_game_loop_bridge.exe did not close cleanly"
}
```

Manual smoke note:

```powershell
.\build\source_stage28_live_input_to_deterministic_game_loop_bridge.exe -manual
```

Manual mode reports `LIVE28=1` in the title and updates bounded live command
fields for W/S/up/down forward/back, A/D/left/right turn, and E/Space use.
Replay mode remains deterministic and does not depend on live input.

## Source Stage 29 Selected Monster Chase Attack State Loop

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage29_selected_monster_chase_attack_state_loop.py
```

Expected output:

```text
build/source_stage29_selected_monster_chase_attack_state_loop.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage29_selected_monster_chase_attack_state_loop.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(8)
$ExpectedStart = "*S29 REPLAY START*STEP29=0*LIVE29=0*"
$ExpectedFinal = "*S29 REPLAY STEP29=6*LIVE29=0*TIC29=6*ST29=S_SPOS_RUN1*AB29=1*BOUND29=ATTACK_DECISION*LOG29=1:S_SPOS_PAIN>6:S_SPOS_RUN1*S30ABS=1*S19SIG=2088411722*S28SIG=2805406010*S29SIG=3738922932*"

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedStart) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage29_selected_monster_chase_attack_state_loop.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStart) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage29_selected_monster_chase_attack_state_loop.exe did not report the replay start marker"
}

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until (($Process.MainWindowTitle -like $ExpectedFinal) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.MainWindowTitle -notlike $ExpectedFinal) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage29_selected_monster_chase_attack_state_loop.exe did not advance to the expected final monster-loop title"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage29_selected_monster_chase_attack_state_loop.exe did not close cleanly"
}
```

Stage29 starts from the selected MAP01 shotgun-guy state proven by stages16-18,
then replays six source-ordered tics through `G_Ticker`,
`P_PlayerThink`/`P_MovePsprites`, `P_Ticker`, `P_RunThinkers`, and
`P_MobjThinker`. The final boundary is the selected `A_Chase` attack decision;
attack execution, projectiles, second damage, death/drop, broad AI, runtime
rendered motion, map progression, UI systems, and real audio remain deferred.

## Source Stage 30 Runtime Rendered Motion Bridge

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage30_runtime_rendered_motion_bridge.py
```

Expected output:

```text
build/source_stage30_runtime_rendered_motion_bridge.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage30_runtime_rendered_motion_bridge.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(8)
$ExpectedStart = "*S30 RENDER START*STEP30=0*"
$ExpectedFinal = "*STEP30=3*TIC30=7*VX30=-172*VY30=-194*A30=3*FB30=169445058*FBDIST30=3*S19SIG=2088411722*S29SIG=3738922932*S30SIG=3898523864*S31ABS=1*"
$SeenTitles = New-Object System.Collections.Generic.List[string]

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
    if ($Process.MainWindowTitle -and -not $SeenTitles.Contains($Process.MainWindowTitle)) {
        $SeenTitles.Add($Process.MainWindowTitle)
    }
} until (($Process.MainWindowTitle -like $ExpectedStart) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage30_runtime_rendered_motion_bridge.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStart) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage30_runtime_rendered_motion_bridge.exe did not report the render start marker"
}

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
    if ($Process.MainWindowTitle -and -not $SeenTitles.Contains($Process.MainWindowTitle)) {
        $SeenTitles.Add($Process.MainWindowTitle)
    }
} until (($Process.MainWindowTitle -like $ExpectedFinal) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.MainWindowTitle -notlike $ExpectedFinal) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage30_runtime_rendered_motion_bridge.exe did not advance to the expected final render title"
}

$FbValues = @{}
foreach ($Title in $SeenTitles) {
    foreach ($Match in [regex]::Matches($Title, "FB30=(\d+)")) {
        $FbValues[$Match.Groups[1].Value] = $true
    }
}

if ($FbValues.Count -lt 2) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage30_runtime_rendered_motion_bridge.exe did not report distinct post-launch framebuffer signatures"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage30_runtime_rendered_motion_bridge.exe did not close cleanly"
}
```

Stage30 reuses the selected stage14 MAP01 player movement route, samples tics
`0`, `4`, and `7`, and copies rendered frame bytes into the live framebuffer on
timer ticks. The smoke must see distinct `FB30=` values after launch; changing
title/status text alone is not sufficient. Projectiles, explosions, generalized
combat, broad AI, generalized specials, map progression, UI systems, real audio
playback, and stage31 remain deferred.

## Source Stage 31 Runtime Real Renderer Motion Bridge

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage31_runtime_real_renderer_motion_bridge.py
```

Expected output:

```text
build/source_stage31_runtime_real_renderer_motion_bridge.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage31_runtime_real_renderer_motion_bridge.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(8)
$ExpectedStart = "*S31 REALRENDER START*STEP31=0*"
$ExpectedFinal = "*STEP31=3*TIC31=7*VX31=-172*VY31=-194*A31=3*FB31=1677820087*FBDIST31=3*NOFULL31=1*S19SIG=2088411722*S30SIG=3898523864*S31SIG=3593583171*S32ABS=1*"
$SeenTitles = New-Object System.Collections.Generic.List[string]

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
    if ($Process.MainWindowTitle -and -not $SeenTitles.Contains($Process.MainWindowTitle)) {
        $SeenTitles.Add($Process.MainWindowTitle)
    }
} until (($Process.MainWindowTitle -like $ExpectedStart) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage31_runtime_real_renderer_motion_bridge.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStart) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage31_runtime_real_renderer_motion_bridge.exe did not report the real-renderer start marker"
}

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
    if ($Process.MainWindowTitle -and -not $SeenTitles.Contains($Process.MainWindowTitle)) {
        $SeenTitles.Add($Process.MainWindowTitle)
    }
} until (($Process.MainWindowTitle -like $ExpectedFinal) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.MainWindowTitle -notlike $ExpectedFinal) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage31_runtime_real_renderer_motion_bridge.exe did not advance to the expected final real-renderer title"
}

$FbValues = @{}
foreach ($Title in $SeenTitles) {
    foreach ($Match in [regex]::Matches($Title, "FB31=(\d+)")) {
        $FbValues[$Match.Groups[1].Value] = $true
    }
}

if ($FbValues.Count -lt 2) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage31_runtime_real_renderer_motion_bridge.exe did not report distinct post-launch real-renderer framebuffer signatures"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage31_runtime_real_renderer_motion_bridge.exe did not close cleanly"
}
```

Stage31 reuses the selected stage14 MAP01 player movement route, samples tics
`0`, `4`, and `7`, and redraws the live framebuffer from runtime-selected wall
column and flat span command tables. The smoke must see distinct `FB31=` values
after launch; stage31 motion is produced by executing the emitted
`R_DrawColumn`/`R_DrawSpan`-shaped primitives, not by copying full pre-rendered
stage31 framebuffer byte arrays. Sky, masked midtextures, sprite posts, combat
visual state, projectiles, explosions, generalized combat, broad AI,
generalized specials, map progression, UI systems, and real audio playback
remain deferred.

## Source Stage 32 Selected Combat Visual State Bridge

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage32_selected_combat_visual_state_bridge.py
```

Expected output:

```text
build/source_stage32_selected_combat_visual_state_bridge.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage32_selected_combat_visual_state_bridge.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(8)
$ExpectedStart = "*S32 PSVIS START*STEP32=0*"
$ExpectedFinal = "*STEP32=3*TIC32=7*PS32=S_SGUN4*PATCH32=SHTGC0*PC32=135*PP32=7493*FB32=2243530028*FBDIST32=3*PSDIST32=3*NOFULL32=1*S19SIG=2088411722*S31SIG=3593583171*S32SIG=533488475*S33ABS=1*"
$SeenTitles = New-Object System.Collections.Generic.List[string]

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
    if ($Process.MainWindowTitle -and -not $SeenTitles.Contains($Process.MainWindowTitle)) {
        $SeenTitles.Add($Process.MainWindowTitle)
    }
} until (($Process.MainWindowTitle -like $ExpectedStart) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage32_selected_combat_visual_state_bridge.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStart) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage32_selected_combat_visual_state_bridge.exe did not report the psprite visual start marker"
}

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
    if ($Process.MainWindowTitle -and -not $SeenTitles.Contains($Process.MainWindowTitle)) {
        $SeenTitles.Add($Process.MainWindowTitle)
    }
} until (($Process.MainWindowTitle -like $ExpectedFinal) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.MainWindowTitle -notlike $ExpectedFinal) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage32_selected_combat_visual_state_bridge.exe did not advance to the expected final psprite visual title"
}

$FbValues = @{}
foreach ($Title in $SeenTitles) {
    foreach ($Match in [regex]::Matches($Title, "(^| )FB32=(\d+)")) {
        $FbValues[$Match.Groups[2].Value] = $true
    }
}

if ($FbValues.Count -lt 2) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage32_selected_combat_visual_state_bridge.exe did not report distinct post-launch psprite framebuffer signatures"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage32_selected_combat_visual_state_bridge.exe did not close cleanly"
}
```

Stage32 preserves the stage31 selected MAP01 wall/flat runtime redraw path and
then draws one selected shotgun psprite route after walls/flats. The smoke must
see distinct `FB32=` values after launch; the changed pixels come from
runtime-executed `R_DrawColumn`-shaped psprite post commands for real WAD patch
data, not from full pre-rendered framebuffer byte arrays. Projectiles,
explosions, monster attack execution, damage/death/drop, generalized combat,
broad AI, generalized sprite systems, map progression, UI systems, and real
audio playback remain deferred.

## Source Stage 33 Selected Hitscan Impact Visual Boundary

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage33_selected_hitscan_impact_visual_boundary.py
```

Expected output:

```text
build/source_stage33_selected_hitscan_impact_visual_boundary.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage33_selected_hitscan_impact_visual_boundary.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(8)
$ExpectedStart = "*S33 IMPACT START*STEP33=0*"
$ExpectedFinal = "*STEP33=3*TIC33=7*PS33=S_SGUN4*PATCH33=SHTGC0*IMP33=S_SPOS_PAIN2*IPATCH33=SPOSG1*IC33=61*IP33=981*FB33=1535635467*FBDIST33=3*IMPDIST33=3*NOFULL33=1*S19SIG=2088411722*S32SIG=533488475*S33SIG=1614948054*S34ABS=1*"
$SeenTitles = New-Object System.Collections.Generic.List[string]

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
    if ($Process.MainWindowTitle -and -not $SeenTitles.Contains($Process.MainWindowTitle)) {
        $SeenTitles.Add($Process.MainWindowTitle)
    }
} until (($Process.MainWindowTitle -like $ExpectedStart) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage33_selected_hitscan_impact_visual_boundary.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStart) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage33_selected_hitscan_impact_visual_boundary.exe did not report the impact visual start marker"
}

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
    if ($Process.MainWindowTitle -and -not $SeenTitles.Contains($Process.MainWindowTitle)) {
        $SeenTitles.Add($Process.MainWindowTitle)
    }
} until (($Process.MainWindowTitle -like $ExpectedFinal) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.MainWindowTitle -notlike $ExpectedFinal) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage33_selected_hitscan_impact_visual_boundary.exe did not advance to the expected final impact visual title"
}

$FbValues = @{}
foreach ($Title in $SeenTitles) {
    foreach ($Match in [regex]::Matches($Title, "(^| )FB33=(\d+)")) {
        $FbValues[$Match.Groups[2].Value] = $true
    }
}

if ($FbValues.Count -lt 2) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage33_selected_hitscan_impact_visual_boundary.exe did not report distinct post-launch impact framebuffer signatures"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage33_selected_hitscan_impact_visual_boundary.exe did not close cleanly"
}
```

Stage33 preserves the stage31 selected MAP01 wall/flat runtime redraw path and
the stage32 selected shotgun psprite route, then draws one bounded selected
shotgun-guy pain-state world sprite route between them. The smoke must see
distinct `FB33=` values after launch; the changed pixels come from
runtime-executed `R_DrawColumn`-shaped world pain and psprite post commands for
real WAD patch data, not from full pre-rendered framebuffer byte arrays. Blood
or puff spawning, projectiles, explosions, monster attack execution, monster
death/drop, generalized combat, broad AI, generalized sprite systems, map
progression, UI systems, stage34, and real audio playback remain deferred.

## Source Stage34 Selected Hitscan Death Visual Boundary

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage34_selected_hitscan_death_visual_boundary.py
```

Expected output:

```text
build/source_stage34_selected_hitscan_death_visual_boundary.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage34_selected_hitscan_death_visual_boundary.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(8)
$ExpectedStart = "*S34 DEATH START*STEP34=0*"
$ExpectedFinal = "*STEP34=3*TIC34=7*PS34=S_SGUN4*PATCH34=SHTGC0*IMP34=S_SPOS_PAIN2*IPATCH34=SPOSG1*DIE34=S_SPOS_DIE2*DPATCH34=SPOSI0*DC34=91*DP34=1013*FB34=1194192847*FBDIST34=3*DEATHDIST34=3*NOFULL34=1*S19SIG=2088411722*S32SIG=533488475*S33SIG=1614948054*S34SIG=4027590938*S35ABS=1*"
$SeenTitles = New-Object System.Collections.Generic.List[string]

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
    if ($Process.MainWindowTitle -and -not $SeenTitles.Contains($Process.MainWindowTitle)) {
        $SeenTitles.Add($Process.MainWindowTitle)
    }
} until (($Process.MainWindowTitle -like $ExpectedStart) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage34_selected_hitscan_death_visual_boundary.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStart) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage34_selected_hitscan_death_visual_boundary.exe did not report the death visual start marker"
}

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
    if ($Process.MainWindowTitle -and -not $SeenTitles.Contains($Process.MainWindowTitle)) {
        $SeenTitles.Add($Process.MainWindowTitle)
    }
} until (($Process.MainWindowTitle -like $ExpectedFinal) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.MainWindowTitle -notlike $ExpectedFinal) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage34_selected_hitscan_death_visual_boundary.exe did not advance to the expected final death visual title"
}

$FbValues = @{}
foreach ($Title in $SeenTitles) {
    foreach ($Match in [regex]::Matches($Title, "(^| )FB34=(\d+)")) {
        $FbValues[$Match.Groups[2].Value] = $true
    }
}

if ($FbValues.Count -lt 2) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage34_selected_hitscan_death_visual_boundary.exe did not report distinct post-launch death framebuffer signatures"
}

$Bytes = [System.IO.File]::ReadAllBytes($Exe)
$Ascii = [System.Text.Encoding]::ASCII.GetString($Bytes).ToLowerInvariant()
if ($Ascii.Contains("source_stage35")) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage34_selected_hitscan_death_visual_boundary.exe contains a source_stage35 marker"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage34_selected_hitscan_death_visual_boundary.exe did not close cleanly"
}
```

Stage34 preserves the stage31 selected MAP01 wall/flat runtime redraw path, the
stage33 selected impact/pain world-post route, and the stage32 selected shotgun
psprite route, then draws one bounded selected shotgun-guy death-state route
between impact/pain and psprite posts. The smoke must see distinct `FB34=`
values after launch; the changed pixels come from runtime-executed
`R_DrawColumn`-shaped death and psprite post commands for real WAD patch data,
not from full pre-rendered framebuffer byte arrays. Item pickup, generalized
death/drop, projectiles, explosions, broad monster AI, generalized combat,
generalized sprite systems, map progression, UI systems, stage35 executable
work, and real audio playback remain deferred.

## Source Stage35 Selected Dropped Shotgun Visual Boundary

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage35_selected_dropped_shotgun_visual_boundary.py
```

Expected output:

```text
build/source_stage35_selected_dropped_shotgun_visual_boundary.exe
```

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\source_stage35_selected_dropped_shotgun_visual_boundary.exe).Path
$Process = Start-Process -FilePath $Exe -WorkingDirectory (Get-Location).Path -PassThru
$Deadline = (Get-Date).AddSeconds(8)
$ExpectedStart = "*S35 DROP START*STEP35=0*"
$ExpectedFinal = "*STEP35=3*TIC35=7*DROP35=S_SHOT*DRPATCH35=SHOTA0*DRC35=44*DRP35=284*DROPFB35=3299982258*FB35=4078405109*FBDIST35=3*DROPDIST35=2*DROPSPAWN35=1*DROPMF35=1*NOFULL35=1*S19SIG=2088411722*S34SIG=4027590938*S35SIG=3270148876*S36ABS=1*"
$SeenTitles = New-Object System.Collections.Generic.List[string]

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
    if ($Process.MainWindowTitle -and -not $SeenTitles.Contains($Process.MainWindowTitle)) {
        $SeenTitles.Add($Process.MainWindowTitle)
    }
} until (($Process.MainWindowTitle -like $ExpectedStart) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "source_stage35_selected_dropped_shotgun_visual_boundary.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -notlike $ExpectedStart) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage35_selected_dropped_shotgun_visual_boundary.exe did not report the drop visual start marker"
}

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
    if ($Process.MainWindowTitle -and -not $SeenTitles.Contains($Process.MainWindowTitle)) {
        $SeenTitles.Add($Process.MainWindowTitle)
    }
} until (($Process.MainWindowTitle -like $ExpectedFinal) -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.MainWindowTitle -notlike $ExpectedFinal) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage35_selected_dropped_shotgun_visual_boundary.exe did not advance to the expected final drop visual title"
}

$FbValues = @{}
foreach ($Title in $SeenTitles) {
    foreach ($Match in [regex]::Matches($Title, "(^| )FB35=(\d+)")) {
        $FbValues[$Match.Groups[2].Value] = $true
    }
}

if ($FbValues.Count -lt 2) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage35_selected_dropped_shotgun_visual_boundary.exe did not report distinct post-launch drop framebuffer signatures"
}

$Bytes = [System.IO.File]::ReadAllBytes($Exe)
$Ascii = [System.Text.Encoding]::ASCII.GetString($Bytes).ToLowerInvariant()
if ($Ascii.Contains("source_stage36")) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage35_selected_dropped_shotgun_visual_boundary.exe contains a source_stage36 marker"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "source_stage35_selected_dropped_shotgun_visual_boundary.exe did not close cleanly"
}
```

Stage35 preserves the stage31 selected MAP01 wall/flat runtime redraw path, the
stage33 selected impact/pain world-post route, the stage34 selected death route,
and the stage32 selected shotgun psprite route. It materializes the selected
`P_KillMobj` `MT_SHOTGUY -> MT_SHOTGUN` drop through a bounded
`P_SpawnMobj`-shaped record, marks `MF_DROPPED`, and draws real WAD `SHOTA0`
posts after death and before psprites. The smoke must see distinct `FB35=`
values after launch; the new drop contribution changes `DIEFB35=2513680424` to
`DROPFB35=3299982258` before the final psprite pass. Pickup,
`P_TouchSpecialThing`, `P_GiveWeapon`, ammo/weapon grant, pickup message, item
removal, respawn queue, broad inventory/statusbar systems, generalized item
traversal, generalized death/drop, projectiles, explosions, broad monster AI,
generalized combat, map progression, UI systems, stage36 executable work, and
real audio playback remain deferred.

## Source Stage36 Selected Dropped Shotgun Pickup Feedback Boundary

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage36_selected_dropped_shotgun_pickup_feedback_boundary.py
```

Expected output:

```text
build/source_stage36_selected_dropped_shotgun_pickup_feedback_boundary.exe
```

Scripted smoke test:

```powershell
py -3 -B -m unittest tests.test_source_stage36_selected_dropped_shotgun_pickup_feedback_boundary.SourceStage36SelectedDroppedShotgunPickupFeedbackBoundaryTests.test_smoke_launch_reports_stage36_pickup_feedback_and_distinct_signatures
```

Stage36 preserves the stage31 wall/flat runtime redraw path, stage33
impact/pain posts, stage34 death posts, stage35 dropped-shotgun posts before
pickup, and stage32 psprite posts. The selected `SPR_SHOT` dropped item is
touched through the bounded `P_TouchSpecialThing` gate, gives one shell clip
and the shotgun through `P_GiveWeapon(... dropped=true)`, reports `GOTSHOTGUN`,
`sfx_wpnup`, `bonuscount`, shell ammo, owned/pending weapon state, removes only
the selected item, and shows `DROP36=REMOVED` / `DRC36=0` in the final frame.
The smoke must see distinct `FB36=` values, `S36SIG=397846180`,
`S35SIG=3270148876`, and no `source_stage37` strings in the executable.

## Source Stage37 Selected Monster Attack Feedback Probe

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage37_selected_monster_attack_feedback_probe.py
```

Expected output:

```text
build/source_stage37_selected_monster_attack_feedback_probe.exe
```

Scripted smoke test:

```powershell
py -3 -B -m unittest tests.test_source_stage37_selected_monster_attack_feedback_probe.SourceStage37SelectedMonsterAttackFeedbackProbeTests.test_smoke_launch_reports_stage37_attack_feedback_and_distinct_signatures
```

Stage37 preserves the stage36 pickup/removal state and the stage31-stage35
visual bridges, then returns to the selected living stage29 shotgun-guy route.
The selected `A_SPosAttack` proof reports one deferred `sfx_shotgn`, a selected
`A_FaceTarget` angle update, three deterministic pellet records, one player
damage event, health `100->91`, armor `0->0`, `damagecount=9`, source marker
`MT_SHOTGUY->P0`, and no player death. The smoke must see distinct `FB37=`
values, `STATE37=1816157848`, `S37SIG=2681905384`, preserved
`S36SIG=397846180` and `S19SIG=2088411722`, and no `source_stage38` strings in
the executable.

## Source Stage38 Selected Attack Feedback Present Bridge

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage38_selected_attack_feedback_present_bridge.py
```

Expected output:

```text
build/source_stage38_selected_attack_feedback_present_bridge.exe
```

Scripted smoke test:

```powershell
py -3 -B -m unittest tests.test_source_stage38_selected_attack_feedback_present_bridge.SourceStage38SelectedAttackFeedbackPresentBridgeTests.test_smoke_launch_reports_stage38_attack_feedback_and_distinct_signatures
```

Stage38 preserves the stage37 selected `A_SPosAttack` gameplay feedback and
restores the bounded Win32 present path. The smoke must see distinct `FB38=`
values, `STATE38=1816157848`, `S38SIG=2314527789`, `HP38=100->91`,
`DMG38=9`, `SFX38=sfx_shotgn`, and present evidence `INV38=3`, `UPD38=3`,
`PAINT38=3`, `PAF38=1`. It also verifies the process remains alive after the
final feedback marker long enough for a stability observation, closes normally,
preserves `S36SIG=397846180` and `S19SIG=2088411722`, and contains no
`source_stage39` strings in the executable.

## Source Stage39 Selected Projectile Spawn Present Probe

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage39_selected_projectile_spawn_present_probe.py
```

Expected output:

```text
build/source_stage39_selected_projectile_spawn_present_probe.exe
```

Scripted smoke test:

```powershell
py -3 -B -m unittest tests.test_source_stage39_selected_projectile_spawn_present_probe.SourceStage39SelectedProjectileSpawnPresentProbeTests.test_smoke_executable_launches_reports_projectile_samples_and_closes
```

Stage39 preserves stage38 present stability, then crosses one selected imp
fireball creation/presentation boundary:
`A_TroopAttack -> A_FaceTarget -> P_SpawnMissile(MT_TROOPSHOT) ->
P_CheckMissileSpawn`. The smoke must see distinct `FB39=` values,
`STATE39=1403583302`, `S39SIG=3469618451`, `MISS39=MT_TROOPSHOT`,
`ST39=S_TBALL1`, `SPR39=SPR_BAL1`, `SFX39=sfx_firsht`, and present evidence
`INV39=3`, `UPD39=3`, `PAINT39=3`, `PAF39=1`. It also verifies preserved
stage38 evidence `INV38=3`, `UPD38=3`, `PAINT38=3`, `PAF38=1`, preserved
baselines through `S19SIG=2088411722`, no copied full-frame projectile motion,
and no `source_stage40` strings in the executable.

## Source Stage40 Bounded Vissprite Traversal Sorting Bridge

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage40_bounded_vissprite_traversal_sorting_bridge.py
```

Expected output:

```text
build/source_stage40_bounded_vissprite_traversal_sorting_bridge.exe
```

Scripted smoke test:

```powershell
py -3 -B -m unittest tests.test_source_stage40_bounded_vissprite_traversal_sorting_bridge.SourceStage40BoundedVisspriteTraversalSortingBridgeTests.test_smoke_executable_launches_reports_vissprite_samples_and_closes
```

Stage40 preserves the stage39 selected projectile state and present bridge,
then replaces the compact stage39 projectile marker in the stage40 visual path
with bounded selected `MT_TROOPSHOT` / BAL1 world-vissprite posts:
`R_AddSprites -> R_ProjectSprite -> R_SortVisSprites -> R_DrawMasked`. The
smoke must see distinct `FB40=` and `VSTATE40=` values, `STATE40=268409133`,
`S40SIG=2737672056`, `PATCH40=BAL1`, `MISS39=MT_TROOPSHOT`,
`PST39=1403583302`, present evidence `INV40=3`, `UPD40=3`, `PAINT40=3`,
`PAF40=1`, preserved stage39 evidence `INV39=3`, `UPD39=3`, `PAINT39=3`,
`PAF39=1`, preserved baselines through `S19SIG=2088411722`, no copied
full-frame selected-vissprite motion, and no `source_stage41` strings in the
executable.

## Source Stage41 Statusbar Weapon Ammo Feedback Bridge

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_source_stage41_statusbar_weapon_ammo_feedback_bridge.py
```

Expected output:

```text
build/source_stage41_statusbar_weapon_ammo_feedback_bridge.exe
```

Scripted smoke test:

```powershell
py -3 -B -m unittest tests.test_source_stage41_statusbar_weapon_ammo_feedback_bridge.SourceStage41StatusbarWeaponAmmoFeedbackBridgeTests.test_smoke_executable_launches_reports_status_samples_and_closes
```

Stage41 preserves the stage40 bounded selected-vissprite path and adds a
compact runtime status strip after the world-vissprite, psprite, feedback, and
projectile evidence draws. The smoke must see distinct `FB41=` and
`SSTATE41=` values, `STATE41=157977072`, `S41SIG=951695045`, selected
health/armor/ammo/weapon/message evidence including `HP41=100->91`,
`ARM41=0`, `AMMO41=0->4`, `OWN41=0->1`, `PEND41=WP_SHOTGUN`,
`MSG41=GOTSHOTGUN`, `BONUS41=6`, `DMG41=9`, deferred sound markers
`SFX41=sfx_wpnup+sfx_shotgn+sfx_firsht`, present evidence `INV41=3`,
`UPD41=3`, `PAINT41=3`, `PAF41=1`, preserved stage40/stage39 present evidence
and baselines through `S19SIG=2088411722`, no copied full-frame status motion,
and no `source_stage42` strings in the executable.
