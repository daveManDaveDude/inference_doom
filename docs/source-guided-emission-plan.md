# Source-Guided Emission Plan

## Intent

The next phase is not a generic DOOM clone and not compiled-code extraction.
The goal is to read the Doom engine source, understand one bounded subsystem at
a time, and write Python emitter code that emits the equivalent PE32 x86 machine
code directly.

The existing stage emitters prove the substrate:

- PE32 x86 executable emission works.
- Win32 window/framebuffer/input code works.
- WAD directory and map lump parsing are understood in Python.
- Emitted binaries can read real WAD files.
- A real-map first-person view exists as an experiment.

Those stages should now be treated as prototypes and test fixtures, not as the
final architecture.

## Source Baseline

Use `reference/chocolate-doom` as the immediate local source tree because it is
already present, pinned to `chocolate-doom-3.1.1`, and runnable on this Windows
setup. For engine behavior, prefer the classic Doom modules under:

```text
reference/chocolate-doom/src/doom/
```

The original id Software Doom source release can also be added as a second
reference if exact original provenance becomes more important than the current
Windows reference build. Either way, generated code should cite the source
routine it was based on.

## Working Agreement

Use `docs/source-guided-ways-of-working.md` as the clean-context quick
reference. In particular, every slice must end with a runnable executable and a
scripted smoke test that launches it and verifies the intended behavior.

## Rules

1. Do not use a compiler, assembler, linker, CMake, MSBuild, MinGW, NASM, or
   compiler-produced code blobs in the emitted path.
2. Do not translate all of Doom at once.
3. Each emitted routine should have a source trace entry: source file, source
   function, intended emitted function label, and validation notes.
4. Prefer source-faithful data layouts before source-faithful control flow.
5. Keep stage07 as a visual proof, but do not build the next phase by piling
   more special cases into it.

## Current Baseline: source_stage03_bsp_walk_debug

The source-guided line now covers WAD/map setup, BSP setup structures, and a
source-ordered BSP traversal proof from the pinned `MAP01` player start.

Implemented source routines:

- `w_wad.c`: `W_NumLumps`
- `w_wad.c`: `W_CheckNumForName`
- `w_wad.c`: `W_GetNumForName`
- `w_wad.c`: `W_LumpLength`
- `w_wad.c`: `W_ReadLump`
- `p_setup.c`: `P_LoadVertexes`
- `p_setup.c`: `P_LoadSectors`
- `p_setup.c`: `P_LoadSideDefs`
- `p_setup.c`: `P_LoadLineDefs`
- `p_setup.c`: `P_LoadSubsectors`
- `p_setup.c`: `P_LoadNodes`
- `p_setup.c`: `P_LoadSegs`
- `p_setup.c`: `P_GroupLines`
- `r_main.c`: `R_PointOnSide`
- `r_main.c`: `R_PointInSubsector`
- `r_bsp.c`: `R_Subsector` as a debug/counting adaptation
- `r_bsp.c`: `R_RenderBSPNode` as a debug/counting adaptation

Emitted executables:

```text
build/source_stage01_wad_map.exe
build/source_stage02_bsp_setup.exe
build/source_stage03_bsp_walk_debug.exe
```

Expected and verified behavior:

- Open the pinned IWAD path.
- Build a runtime lump directory in emitted code.
- Find `MAP01`.
- Load `VERTEXES`, `SECTORS`, `SIDEDEFS`, and `LINEDEFS`.
- Load `SSECTORS`, `NODES`, and `SEGS`.
- Assign subsector sectors and prove sector line grouping with deterministic
  min/max/first line counts.
- Seed `viewx`, `viewy`, and `viewangle` from the pinned `MAP01` player-one
  start `(-192, -192, 0)`.
- Traverse the BSP front-to-back using source-shaped `R_PointOnSide` and
  `R_RenderBSPNode` ordering.
- Keep `R_CheckBBox` as an explicit accept-all debug boundary.
- Draw a simple top-down debug framebuffer with map lines, visited segs, and
  the fixed viewpoint marker.
- Display deterministic traversal counts in the framebuffer and window title.

The verified stage03 smoke signal for pinned Freedoom2 `MAP01` is:

```text
V=1189 SEC=211 SD=2041 L=1274 SS=698 N=697 SG=2233 VN=697 VSS=698 VSEG=2233 DEPTH=33 FIRSTSS=227 LASTSS=169
```

This is deliberately less flashy than stage07. It is the bridge from
experiment to source-guided engine port: the renderer is now walking real Doom
BSP structures in source order, but it is not yet doing view-frustum rejection,
wall span clipping, texture projection, planes, or sprites.

## Lessons From source_stage03_bsp_walk_debug

- The source-shaped runtime layouts are paying off: `subsector_t`, `node_t`,
  and `seg_t` now have the pointer fields needed by `R_RenderBSPNode` and
  `R_Subsector`, and stage03 reused them without reshaping the stage02 loader.
- `P_GroupLines` is partially complete by design. Subsector sector assignment
  and sector line grouping are proven, but blockmap-derived sector block boxes
  remain deferred because `P_LoadBlockMap` is outside the current rendering
  path.
- Direct recursive BSP emission was workable for stage03 and preserved the
  source front/back visit order. If later slices need more instrumentation,
  an iterative stack remains acceptable only if tests prove identical order.
- The accept-all `R_CheckBBox` boundary is now the exact next handoff: stage04
  should replace only that decision with source-guided bbox/frustum logic.
- Full wall rendering is still too large for one jump. The clean split is now:
  bbox visibility, then seg span clipping, then wall projection/texture columns.

## Released Slice: source_stage03_bsp_walk_debug

Output:

```text
build/source_stage03_bsp_walk_debug.exe
```

Source routines to read and trace:

- `r_main.c`: `R_PointOnSide`
- `r_main.c`: `R_PointInSubsector`
- `r_bsp.c`: `R_RenderBSPNode`
- `r_bsp.c`: `R_Subsector`

Goal:

Prove that the emitted executable can traverse the loaded Doom BSP in source
front-to-back order from the pinned player/viewpoint, using the stage02 runtime
nodes/subsectors/segs without starting the texture or wall column renderer.

User-visible feature:

- Launches a framebuffer window.
- Loads the stage02 runtime map/BSP structures.
- Uses emitted `R_PointOnSide` and `R_RenderBSPNode`-style traversal to count
  visited nodes, visited subsectors, visited segs, max recursion depth, and the
  first/last visited subsector IDs from the pinned `MAP01` player start.
- Draws a simple top-down debug view: all map lines in a muted color, visited
  segs in a highlight color, and the fixed viewpoint marker.
- Reports deterministic traversal values in the title and framebuffer.

Runtime data to add:

- Viewpoint fields (`viewx`, `viewy`, `viewangle`) in Doom fixed-point style,
  seeded from the pinned map's player start.
- Traversal counters: visited nodes, visited subsectors, visited segs, max
  depth, first visited subsector, last visited subsector, and containing
  subsector.
- Visited seg debug buffer for top-down highlighting.
- Minimal framebuffer drawing helpers for a top-down view.

Implementation notes:

- This is a traversal proof, not visibility clipping and not final wall
  rendering.
- `render_point_on_side` includes the source vertical/horizontal fast paths,
  sign-bit shortcut, and fixed multiply comparison.
- `render_debug_subsector` is a debug/counting adaptation: it increments
  counters and records seg indexes, while leaving planes, sprites, `R_AddLine`,
  and `solidsegs` untouched.
- `render_check_bbox_accept_all` is deliberately named and documented so the
  next slice can replace it cleanly.

Tests:

- Unit tests for point-side classification against synthetic nodes, including
  vertical and horizontal partition fast paths.
- Python reference traversal test for pinned `MAP01` from the player start.
- Unit tests for fixed-point viewpoint constants and traversal/debug offsets.
- Build test that verifies the stage03 PE contains expected source-stage status
  strings and no compiler-produced blob markers.
- Smoke test launches `source_stage03_bsp_walk_debug.exe`, checks the title for
  deterministic traversal counts, and closes it cleanly.

Done when:

- `build/source_stage03_bsp_walk_debug.exe` launches, traverses the real
  `MAP01` BSP in front-to-back order, shows the debug view, and reports
  deterministic traversal counts.
- `python -B -m unittest discover -s tests` passes.
- Source trace and smoke docs are updated.

## Next Releasable Slice: source_stage04_bbox_visibility_debug

Output:

```text
build/source_stage04_bbox_visibility_debug.exe
```

Source routines to read and trace:

- `tables.c`: `SlopeDiv`
- `tables.c`: `tantoangle` and `finetangent` table data
- `r_main.c`: `R_PointToAngle`
- `r_main.c`: `R_InitTextureMapping`
- `r_bsp.c`: `R_ClearClipSegs`
- `r_bsp.c`: `R_CheckBBox`

Goal:

Replace stage03's accept-all BSP bounding-box shortcut with source-guided
view-frustum/bounding-box visibility. This should prune BSP back-sides that are
outside the fixed view cone while still avoiding wall span clipping and full
wall rendering.

User-visible feature:

- Launches the same top-down debug view as stage03.
- Reports both full accept-all traversal counts and bbox-visible traversal
  counts, so the user can see that `R_CheckBBox` changed the walk.
- Highlights full/visible/culled traversal state with distinct colors or
  counters.
- The current Python reference for the pinned start, using `R_CheckBBox` with
  only `R_ClearClipSegs` sentinel ranges, is:
  `BVN=559 BVSS=513 BVSEG=1709 BDEPTH=33 BFIRSTSS=227 BLASTSS=153 CULL=47`.

Runtime data to add:

- Angle constants and table storage needed by the renderer path:
  `ANG90`, `ANG180`, `ANG270`, `ANGLETOFINESHIFT`, `FINEANGLES`,
  `FIELDOFVIEW`, `SLOPERANGE`, `tantoangle`, and `finetangent`.
- View projection state for a fixed full-width view: `viewwidth`, `centerx`,
  `centerxfrac`, `projection`, `clipangle`, `viewangletox`, and
  `xtoviewangle`.
- `solidsegs` and `newend` initialized exactly like `R_ClearClipSegs`, but not
  updated by wall spans in this slice.
- Bbox-visible traversal counters, culled-node counters, and optional visited
  seg/subsector buffers for the visible pass.

Implementation notes:

- Reuse stage03 traversal and run two debug passes if that is simpler and more
  testable: one accept-all pass for baseline counts, then one bbox-visible pass
  using source-shaped `R_CheckBBox`.
- Keep `R_AddLine`, `R_ClipSolidWallSegment`, and `R_ClipPassWallSegment` out
  of stage04. `solidsegs` should contain only the left/right sentinel ranges
  from `R_ClearClipSegs`.
- Port `R_PointToAngle` with Doom unsigned `angle_t` wraparound and exact
  octant behavior. Port or table-emit `SlopeDiv`, `tantoangle`, and
  `finetangent` rather than using floating-point approximations at runtime.
- Generate `viewangletox` and `xtoviewangle` from the source
  `R_InitTextureMapping` algorithm for `viewwidth=320`, `detailshift=0`, and
  `centerx=160`.
- Use the source `checkcoord` table and pass `bsp->bbox[side^1]` to
  `R_CheckBBox`, matching the original back-child decision point.
- Keep planes, sprites, drawsegs, texture columns, and wall span clipping out
  of this slice.

Tests:

- Unit tests for `SlopeDiv`, `R_PointToAngle` octants, and unsigned angle
  wraparound.
- Unit tests for generated `viewangletox`, `xtoviewangle`, and `clipangle`
  selected entries against source-equivalent calculations.
- Unit tests for `R_CheckBBox` synthetic box positions, including the
  view-inside-box `boxpos == 5` fast accept and off-screen rejection.
- Python reference test for pinned `MAP01` bbox-visible counts from the fixed
  viewpoint, including culled back-child count and first/last visible
  subsector IDs.
- Build test that verifies the stage04 PE contains expected source-stage status
  strings and table/debug labels.
- Smoke test launches `source_stage04_bbox_visibility_debug.exe`, checks the
  title for full vs bbox-visible traversal counts, and closes it cleanly.

Done when:

- The executable launches and shows a deterministic difference between
  accept-all traversal and bbox-visible traversal.
- Full unit test suite passes.
- Source trace and smoke docs are updated.

## Releasable Slice After That: source_stage05_seg_clip_debug

Output:

```text
build/source_stage05_seg_clip_debug.exe
```

Source routines to read and trace/reuse:

- Reuse from stage04: `r_main.c`: `R_PointToAngle`, `viewangletox`,
  `xtoviewangle`, and `clipangle`
- `r_bsp.c`: `R_AddLine`
- `r_bsp.c`: `R_ClipSolidWallSegment`
- `r_bsp.c`: `R_ClipPassWallSegment`
- `r_segs.c`: `R_StoreWallRange` as a debug span-recording adaptation

Goal:

Start updating `solidsegs` from real BSP segs and report source-shaped wall
span clipping decisions. This should prove `R_AddLine` angle clipping,
one-sided/two-sided wall classification, and solid/pass clipping without yet
drawing textured wall columns.

User-visible feature:

- Launches the stage04 top-down debug view.
- Traverses bbox-visible BSP nodes, calls a debug `R_AddLine` for each visited
  seg, updates `solidsegs`, and records visible wall column ranges.
- Reports visited segs, rejected backfaces, off-frustum segs, solid clipped
  spans, pass clipped spans, stored visible spans, final `solidsegs` count, and
  overflow/limit guards.
- Optionally draws a small horizontal span strip or heat bar that shows which
  screen columns were accepted by clipping.

Runtime data to add:

- Full mutable `solidsegs` array sized for the pinned view, plus `newend`.
- Debug wall-span buffer with start/stop columns and source reason
  (`solid`, `pass`, or clipped fragment).
- `curline`, `frontsector`, and `backsector` state needed by `R_AddLine`.
- Counters for backface rejects, left/right frustum rejects, zero-pixel spans,
  solid/pass classification, stored spans, and clip-list insert/merge cases.

Implementation notes:

- Reuse stage04 angle tables and `clipangle` rather than regenerating a second
  projection path.
- `R_StoreWallRange` should be a debug adaptation in stage05: record accepted
  `start..stop` ranges and counters, but do not build full `drawseg_t` wall
  projection yet.
- Source `R_AddLine` treats identical two-sided sectors with no midtexture as
  empty trigger lines. Until texture lookup lands, use the loaded sidedef middle
  texture name (`"-"` means no midtexture) as the stable debug equivalent.
- Keep `R_PointToDist`, `R_ScaleFromGlobalAngle`, `R_RenderSegLoop`,
  `R_DrawColumn`, planes, sprites, and texture-backed drawing out unless the
  wall-span debug slice is already complete and green.

Tests:

- Unit tests for `R_AddLine` angle clipping and x span mapping with synthetic
  segs.
- Unit tests for `R_ClipSolidWallSegment` insert/extend/merge behavior and
  `R_ClipPassWallSegment` non-mutating behavior.
- Unit tests for debug `R_StoreWallRange` span buffer bounds and counters.
- Python reference test for pinned `MAP01` seg clipping totals from the fixed
  viewpoint.
- Smoke test checks the stage05 title for deterministic clipping counters and
  final `solidsegs` count.

Done when:

- The executable launches and reports deterministic wall-span clipping counters
  from real `MAP01` segs.
- Full unit test suite passes.
- Source trace and smoke docs are updated.

## Future Backlog

Likely next slices after stage05, still intentionally less detailed:

- `source_stage06_frame_setup_tables`: port the stable view setup path around
  `R_SetupFrame`, `R_PointToDist`, `R_ScaleFromGlobalAngle`, and the
  projection/light table data needed by real wall columns.
- `source_stage07_texture_data_setup`: load enough texture and flat metadata to
  replace the current stable name/id placeholders. Source targets include
  `r_data.c` texture lookup and `W_CacheLumpNum`-style cached patch access.
- `source_stage08_wall_column_first_pixels`: port the first narrow vertical
  wall-column path through `R_RenderSegLoop` and `R_DrawColumn`, initially for
  opaque one-sided walls and a fixed view.
- Complete remaining map setup when the engine needs it:
  `P_LoadBlockMap`, full `P_GroupLines` block boxes, `P_LoadReject`, and
  `P_LoadThings`.

At that point the renderer can stop being a raycast approximation and start
following Doom's BSP/seg/column pipeline.
