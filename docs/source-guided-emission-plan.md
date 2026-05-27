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

## Current Baseline: source_stage02_bsp_setup

The source-guided line now covers WAD/map setup plus the first BSP setup
structures needed before real Doom rendering.

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

Emitted executables:

```text
build/source_stage01_wad_map.exe
build/source_stage02_bsp_setup.exe
```

Expected and verified behavior:

- Open the pinned IWAD path.
- Build a runtime lump directory in emitted code.
- Find `MAP01`.
- Load `VERTEXES`, `SECTORS`, `SIDEDEFS`, and `LINEDEFS`.
- Load `SSECTORS`, `NODES`, and `SEGS`.
- Assign subsector sectors and prove sector line grouping with deterministic
  min/max/first line counts.
- Display counts and simple sanity values in the framebuffer and window title.

This is deliberately less flashy than stage07. It is the bridge from
experiment to source-guided engine port.

## Lessons From source_stage02_bsp_setup

- The source-shaped runtime layouts are paying off: `subsector_t`, `node_t`,
  and `seg_t` now have the pointer fields needed by `R_RenderBSPNode` and
  `R_Subsector`.
- `P_GroupLines` is partially complete by design. Subsector sector assignment
  and sector line grouping are proven, but blockmap-derived sector block boxes
  remain deferred because `P_LoadBlockMap` is outside the current rendering
  path.
- The required `source_stage02_bsp_setup.exe` name triggered Windows
  installer-elevation heuristics until the PE writer embedded an `asInvoker`
  manifest. Future emitted executables can reuse that manifest support when a
  name or behavior looks installer-like.
- Full Doom BSP rendering should not be attempted in one jump. The source
  split is clearer now: first prove BSP front-to-back ordering, then add
  frustum/bounding-box visibility, then add seg clipping/wall projection, then
  texture-backed column drawing.

## Released Slice: source_stage02_bsp_setup

Output:

```text
build/source_stage02_bsp_setup.exe
```

Source routines to read and trace:

- `p_setup.c`: `P_LoadSubsectors`
- `p_setup.c`: `P_LoadNodes`
- `p_setup.c`: `P_LoadSegs`
- `p_setup.c`: `P_GroupLines`

Goal:

Extend the source-guided map setup from flat line/sector data to the BSP-era
runtime structures needed by real Doom rendering.

User-visible feature:

- Launches a Win32 window.
- Opens the pinned IWAD and loads `MAP01`.
- Reports `VERTEXES`, `SECTORS`, `SIDEDEFS`, `LINEDEFS`, `SSECTORS`, `NODES`,
  and `SEGS` counts.
- Reports simple BSP sanity values, such as root node index, first subsector
  first-seg/count, first seg vertex links, and min/max sector line counts after
  grouping.

Runtime data to add:

- `subsectors_buffer`, matching the source fields needed now:
  `sector`, `numlines`, `firstline`.
- `nodes_buffer`, with fixed-point partition origin/delta, child indexes, and
  fixed-point bounding boxes.
- `segs_buffer`, with vertex links, angle/offset, linedef link, side link,
  front sector, and back sector.
- Sector line grouping storage sufficient for `P_GroupLines` validation:
  per-sector line counts and line-list pointers or offsets.

Implementation notes:

- Keep texture and flat number lookups stubbed as stable name/id placeholders
  until the renderer texture slice. Do not pull in the whole texture manager.
- Use `W_LumpLength` and `W_ReadLump` from source_stage01 rather than adding
  another ad hoc WAD read path.
- Validate record sizes before reading into fixed-size buffers.
- Favor source field ordering even if not every field is consumed by the
  immediate display.

Tests:

- Unit tests for map record sizes: `mapseg_t`, `mapsubsector_t`, and
  `mapnode_t`.
- Unit tests for emitted runtime layout offsets for subsectors, nodes, and
  segs.
- Pinned IWAD tests that expected `MAP01` `SSECTORS`, `NODES`, and `SEGS`
  counts fit the buffers and match Python parser/reference calculations.
- Smoke test launches `source_stage02_bsp_setup.exe` and checks the title for
  expected counts.

Done when:

- `build/source_stage02_bsp_setup.exe` launches and reports the BSP setup
  counts/sanity values.
- `python -B -m unittest discover -s tests` passes.
- The smoke test launches and closes the executable cleanly.
- `docs/source-trace-manifest.md` marks the stage02 routines as emitted.

## Next Releasable Slice: source_stage03_bsp_walk_debug

Output:

```text
build/source_stage03_bsp_walk_debug.exe
```

Source routines to read and trace:

- `r_main.c`: `R_PointOnSide`
- `r_bsp.c`: `R_RenderBSPNode`
- `r_bsp.c`: `R_Subsector`
- `r_main.c`: `R_PointInSubsector` as a reference check for the fixed
  viewpoint's containing subsector.

Goal:

Prove that the emitted executable can traverse the loaded Doom BSP in source
front-to-back order from a fixed player/viewpoint, using the stage02 runtime
nodes/subsectors/segs without starting the texture or wall column renderer.

User-visible feature:

- Launches a framebuffer window.
- Loads the stage02 runtime map/BSP structures.
- Uses emitted `R_PointOnSide` and `R_RenderBSPNode`-style traversal to count
  visited nodes, visited subsectors, visited segs, max recursion depth, and the
  first/last visited subsector IDs from the pinned `MAP01` player start.
- Draws a simple top-down debug view: all map lines in a muted color, visited
  segs or subsectors in a highlight color, and the fixed viewpoint marker.
- Reports deterministic traversal values in the title or overlay. The current
  Python reference for an accept-all bounding-box traversal from the pinned
  `MAP01` start is `VN=697 VSS=698 VSEG=2233 DEPTH=33 FIRSTSS=227 LASTSS=169`.

Runtime data to add:

- Viewpoint fields (`viewx`, `viewy`, `viewangle`) in Doom fixed-point style,
  seeded from the pinned map's player start for now.
- Traversal counters: visited nodes, visited subsectors, visited segs, current
  depth, max depth, first visited subsector, and last visited subsector.
- Small visited-subsector and/or visited-seg debug buffers.
- Minimal framebuffer drawing helpers for a top-down view, reusing patterns
  from the prototype framebuffer/map probe emitters where practical.

Implementation notes:

- This is a traversal proof, not visibility clipping and not final wall
  rendering.
- Use a source-faithful `R_PointOnSide`; it is small, deterministic, and the
  key correctness hinge for BSP ordering.
- Keep `R_CheckBBox` out of stage03 except as an explicit accept-all debug
  boundary. The real routine depends on `R_PointToAngle`, `viewangletox`,
  `clipangle`, and the `solidsegs` clip list, so it is the next slice rather
  than a hidden half-port here.
- `R_Subsector` should be a debug/counting adaptation: increment counters,
  mark subsectors/segs, and avoid planes, sprites, and `R_AddLine` until the
  renderer support routines exist.
- Use an iterative stack if direct recursive emission gets awkward, but keep
  the visited order equivalent to the source recursion and document the control
  flow choice in the trace manifest.

Tests:

- Unit tests for point-side classification against synthetic nodes.
- Python reference traversal test for pinned `MAP01` from the player start,
  including visited node/subsector/seg totals and first/last visited
  subsector IDs.
- Unit tests for fixed-point viewpoint constants and emitted traversal/debug
  buffer offsets.
- Build test that verifies the stage03 PE contains the expected source-stage
  status strings and no compiler-produced blob markers.
- Smoke test launches `source_stage03_bsp_walk_debug.exe`, checks the title for
  deterministic traversal counts, and closes it cleanly.

Done when:

- The executable launches, traverses the real `MAP01` BSP in front-to-back
  order, shows the debug view, and reports deterministic traversal counts.
- Full unit test suite passes.
- Source trace and smoke docs are updated.

## Releasable Slice After That: source_stage04_bbox_visibility_debug

Output:

```text
build/source_stage04_bbox_visibility_debug.exe
```

Source routines to read and trace:

- `r_main.c`: `R_PointToAngle`
- `r_main.c`: `R_InitTextureMapping`
- `r_bsp.c`: `R_CheckBBox`
- `r_bsp.c`: clip-list sentinel setup around `solidsegs`/`newend`

Goal:

Replace stage03's accept-all BSP bounding-box shortcut with source-guided
view-frustum/bounding-box visibility. This should prune BSP back-sides that are
outside the fixed view cone while still avoiding full wall rendering.

User-visible feature:

- Launches the same top-down debug view as stage03.
- Reports both full traversal counts and bbox-visible traversal counts, so the
  user can see that the real `R_CheckBBox`-style decision changed the walk.
- Highlights visited/culled BSP regions or segs with distinct colors.

Runtime data to add:

- `viewangle`, `clipangle`, `viewwidth`, `centerx`, `centerxfrac`, and
  projection fields needed by `R_CheckBBox`.
- `viewangletox` and `xtoviewangle` tables generated from the source tables
  and pinned view size.
- A minimal `solidsegs` clip list initialized with the source sentinel ranges.
- Bbox-visible traversal counters and culled-node counters.

Implementation notes:

- It is acceptable for stage04 to use only sentinel `solidsegs`, meaning it
  proves frustum/bbox rejection but not wall-occlusion updates. If wall span
  clipping fits cleanly, it can be added; otherwise it becomes stage05.
- Generate or embed deterministic lookup tables from Python, with tests
  checking selected entries against source-equivalent calculations.
- Keep planes, sprites, drawsegs, and texture columns out of this slice.

Tests:

- Unit tests for `R_PointToAngle` octants and `SlopeDiv` behavior.
- Unit tests for generated `viewangletox`/`xtoviewangle` selected entries and
  `clipangle`.
- Python reference test for pinned `MAP01` bbox-visible counts from the fixed
  viewpoint.
- Smoke test checks the stage04 window title for full vs bbox-visible traversal
  values.

Done when:

- The executable launches and shows a deterministic difference between
  accept-all traversal and bbox-visible traversal.
- Full unit test suite passes.
- Source trace and smoke docs are updated.

## Future Backlog

Likely next slices after stage04, still intentionally less detailed:

- `source_stage05_seg_clip_debug`: port the source-shaped parts of
  `R_AddLine`, `R_ClipSolidWallSegment`, and `R_ClipPassWallSegment` enough to
  update `solidsegs` from real seg spans and report clipped/accepted wall
  ranges without textures.
- `source_stage06_frame_setup_tables`: port the stable view setup path around
  `R_SetupFrame`, `R_InitTextureMapping`, and the projection/light table data
  needed by real wall columns. This may absorb parts of stage04 if the table
  work grows.
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
