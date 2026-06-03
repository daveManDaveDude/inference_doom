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
5. Keep the released debug stages as proofs, but do not build the next phase by
   piling more special cases into them.

## Current Baseline: source_stage10_composite_two_sided_wall_edges_debug

The source-guided line now covers WAD/map setup, BSP setup structures,
source-ordered BSP traversal, Doom-shaped bbox/frustum visibility, and live
emitted x86 mutable wall-span clipping for the pinned `MAP01` player start.
It turns the accepted live wall spans into source-shaped projection records
using Doom fixed-point distance and scale math, connects those projected spans
to real Doom texture and flat metadata, and now draws real WAD wall texture
pixels from direct columns, source-shaped composite columns, and supported
two-sided upper/lower wall edges.

Stage08 parses and validates `PNAMES`, `TEXTURE1`, optional `TEXTURE2`, and the
flat lump range in Python, then emits bounded source-shaped metadata tables into
the PE. Stage09 extends that bridge by parsing patch column posts, `PLAYPAL`,
and `COLORMAP` row 0 in Python, table-emitting only the reachable direct opaque
column bytes, and using emitted x86 to run a narrow `R_DrawColumn`-shaped scaler
into the existing 32-bit framebuffer.

Stage10 extends the same bridge with source-shaped composite cache generation,
direct/composite column dispatch, two-sided upper/lower wall-edge clipping, and
floor/ceiling plane-mark records. The emitted executable still draws through a
small runtime x86 column loop and reports a deterministic framebuffer
signature, while Python continues to perform bounded source-guided WAD parsing
and table emission for the fixed proof.

The renderer is still a debug renderer. It knows which texture metadata belongs
to visible spans and can draw deterministic wall columns, but it still stops
before flat-span drawing, sky drawing, masked/translucent wall drawing,
sprites, actors, game/player movement, and the full game loop.

Implemented or source-proven routines:

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
- `tables.c`: `SlopeDiv`
- `tables.c`: `tantoangle` and `finetangent` table data
- `r_main.c`: `R_PointToAngle`
- `r_main.c`: `R_InitTextureMapping` table generation for the fixed debug view
- `r_bsp.c`: `R_ClearClipSegs`
- `r_bsp.c`: `R_CheckBBox`
- `r_bsp.c`: `R_Subsector` as a debug/counting adaptation
- `r_bsp.c`: `R_RenderBSPNode` as a debug/counting adaptation
- `r_bsp.c`: `R_Subsector` as a Python mutable-clipping reference adaptation
- `r_bsp.c`: `R_AddLine` as a Python mutable-clipping reference adaptation
- `r_bsp.c`: `R_ClipSolidWallSegment` as a Python mutable-clipping reference
- `r_bsp.c`: `R_ClipPassWallSegment` as a Python mutable-clipping reference
- `r_segs.c`: `R_StoreWallRange` as a debug span-recording reference
- `r_bsp.c`: `R_RenderBSPNode` as a live emitted clipping-pass debug adaptation
- `r_bsp.c`: `R_Subsector` as a live emitted clipping-pass debug adaptation
- `r_bsp.c`: `R_AddLine` as live emitted x86
- `r_bsp.c`: `R_ClipSolidWallSegment` as live emitted x86
- `r_bsp.c`: `R_ClipPassWallSegment` as live emitted x86
- `r_segs.c`: `R_StoreWallRange` as a live emitted debug span recorder
- `tables.c`: `finesine` and `finecosine` table data
- `p_local.h` / `p_user.c`: `VIEWHEIGHT` and the stable start `viewz` path
- `r_main.c`: `R_SetupFrame` as a fixed-player debug adaptation
- `m_fixed.c`: `FixedDiv`
- `r_main.c`: `R_PointToDist`
- `r_main.c`: `R_ScaleFromGlobalAngle`
- `r_segs.c`: `R_StoreWallRange` distance/scale prefix as a projected debug
  span recorder
- `r_data.c`: `R_InitTextures` as bounded texture metadata parsing/emission
- `r_data.c`: `R_GenerateLookup` metadata/column-directory portion
- `r_data.c`: `R_InitFlats`
- `r_data.c`: `R_CheckTextureNumForName`
- `r_data.c`: `R_TextureNumForName`
- `r_data.c`: `R_FlatNumForName`
- `p_setup.c`: `P_LoadSideDefs` texture ID resolution
- `p_setup.c`: `P_LoadSectors` flat ID resolution
- `r_data.c`: `R_GetColumn` direct patch-backed path
- `r_draw.c`: `R_DrawColumn` as a narrow emitted scaler
- `r_segs.c`: `R_StoreWallRange` one-sided midtexture setup as a direct-pixel
  debug adaptation
- `r_segs.c`: `R_RenderSegLoop` midtexture branch as a narrow debug loop
- `v_patch.h`: `patch_t` / `post_t` direct column parsing
- WAD graphics data: `PLAYPAL` and first `COLORMAP` row palette adaptation
- `r_data.c`: `R_DrawColumnInCache` as a source-shaped composite cache
  reference/table-emission path
- `r_data.c`: `R_GenerateComposite` as a bounded composite column cache
  reference/table-emission path
- `r_data.c`: `R_GetColumn` direct/composite dispatch as a debug adaptation
- `r_segs.c`: `R_StoreWallRange` two-sided upper/lower setup as a wall-edge
  debug adaptation
- `r_segs.c`: `R_RenderSegLoop` toptexture/bottomtexture branches as a narrow
  wall-edge debug loop
- `r_plane.c`: `R_ClearPlanes` and `R_CheckPlane` as plane-mark record/count
  hooks for the stage11 handoff

Emitted executables:

```text
build/source_stage01_wad_map.exe
build/source_stage02_bsp_setup.exe
build/source_stage03_bsp_walk_debug.exe
build/source_stage04_bbox_visibility_debug.exe
build/source_stage05_seg_clip_debug.exe
build/source_stage06_live_seg_clip_debug.exe
build/source_stage07_wall_projection_debug.exe
build/source_stage08_texture_data_setup_debug.exe
build/source_stage09_direct_wall_column_pixels_debug.exe
build/source_stage10_composite_two_sided_wall_edges_debug.exe
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
- Run an accept-all stage03-compatible traversal baseline.
- Generate and emit Doom angle/projection tables for `viewwidth=320`.
- Initialize `solidsegs` with only the two `R_ClearClipSegs` sentinel ranges.
- Run a second traversal using source-shaped `R_CheckBBox` for back-child
  bbox/frustum visibility.
- Run a Python source-shaped mutable wall-span clipping reference that starts
  from `R_ClearClipSegs`, calls debug `R_AddLine` from real subsectors,
  classifies solid/pass/empty segs, updates `solidsegs`, and records debug
  visible spans.
- Run the same mutable wall-span clipping traversal live in emitted x86,
  updating runtime `solidsegs`, recording runtime debug spans, and feeding
  those solid ranges back into later `R_CheckBBox` calls.
- Seed fixed debug frame fields (`viewz`, `viewcos`, `viewsin`, `validcount`,
  and `framecount`) from source-shaped setup paths.
- Project the same 86 accepted spans into debug records containing `x1`, `x2`,
  source seg index, `rw_normalangle`, `rw_distance`, `scale1`, `scale2`, and
  `scalestep`.
- Parse real Doom texture metadata from `PNAMES`, `TEXTURE1`, and optional
  `TEXTURE2`; validate patch references and source-shaped texture dimensions.
- Emit numeric sidedef texture IDs and sector flat IDs while preserving the
  stage07 raw names for trace/debug checks.
- Emit source-shaped `texturetranslation`, `texturewidthmask`,
  `textureheight`, `texturecolumnlump`, `texturecolumnofs`,
  `texturecomposite`, `texturecompositesize`, `textures_hashtable`, and
  `flattranslation` metadata.
- Count direct patch-backed texture columns and columns that will require
  composite generation later, without decoding or drawing patch pixels.
- Decode direct full-height patch-backed columns reached by one-sided opaque
  midtexture spans; skip composite-needed columns, texture id `0`, unsupported
  two-sided/non-opaque spans, and masked midtextures with visible counters.
- Draw 162 direct wall columns and 15508 real WAD-derived pixels through emitted
  x86 column stepping, using `COLORMAP` row 0 and the first `PLAYPAL` palette
  to convert Doom palette indexes to 32-bit RGB.
- Build/reuse a bounded source-shaped composite column cache for the pinned
  wall proof, draw visible composite-backed columns, and report visible
  clipped/skipped composite outcomes.
- Initialize source-shaped `ceilingclip[320]` / `floorclip[320]` for the
  two-sided edge proof, draw supported upper/lower wall-edge columns, and
  record floor/ceiling plane marks without drawing flat spans.
- Draw a simple top-down debug framebuffer with map lines, visited segs, and
  the fixed viewpoint marker; stage04 through stage06 overlay bbox-visible
  segs from the second pass, and stages09/10 overlay wall pixels.
- Display deterministic accept-all, sentinel-only bbox-visible, mutable
  clipping, wall-projection, texture setup, flat setup, first/last
  projected-span texture IDs, direct-column counters, first drawn texture, and
  runtime pixel signature in the framebuffer and window title.

The verified stage09 smoke signal for pinned Freedoom2 `MAP01` is:

```text
V=1189 SEC=211 SD=2041 L=1274 SS=698 N=697 SG=2233 VN=697 VSS=698 VSEG=2233 DEPTH=33 FIRSTSS=227 LASTSS=169 BVN=559 BVSS=513 BVSEG=1709 BDEPTH=33 BFIRSTSS=227 BLASTSS=153 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1 FSPAN=224-255 FSEG=605 LSPAN=143-165 LSEG=855 VZ=2686976 VCOS=65535 VSIN=25 VALID=1 FRAME=1 PRJ=86 MIND=2073560 MAXD=58720255 MINS=11702 MAXS=108495 FPRJ=224-255 FPSEG=605 LPRJ=143-165 LPSEG=855 TEX=963 PN=1054 FLAT=246 DIRC=80797 COMPC=26323 FPTEX=850 LPTEX=13 EMID=1 DWSP=86 OPQSP=24 DCOL=297 DRAW=162 SKC=135 SKU=62 ZTEX=0 MASK=0 FTEX=850 FN=AQRUST08 FCOL=127 PIX=15508 SIG=2194105880
```

The verified stage10 smoke signal keeps the stage09 string above and adds:

```text
CMB=89 CMH=75 CMO=0 MCOL=2 MCEMP=133 UCOL=478 UCOMP=6 LCOL=138 PM=1659 F10TEX=850 F10N=AQRUST08 L10TEX=887 L10N=AQSECT08 TCOL=780 TPIX=37546 TSIG=4201955800
```

This is deliberately still a debug renderer. It is a bridge from experiment to
source-guided engine port: the project is walking real Doom BSP structures in
source order, pruning bbox-invisible back subtrees, and computing mutable wall
span clipping and wall projection live, with source-shaped texture/flat setup
and a broader composite/two-sided wall-column path now proven. The end goal remains the
same: build Doom from the source behavior, without a compiler, one runnable
emitted PE32 slice at a time.

## Lessons From source_stage07_wall_projection_debug

- The source-shaped runtime layouts are still the right foundation:
  `subsector_t`, `node_t`, `seg_t`, sidedef, linedef, and sector pointers
  contain enough information to classify one-sided, closed-door, window, and
  empty trigger lines without reshaping the loader.
- Mutable `solidsegs` changes the traversal dramatically. The stage04
  sentinel-only bbox pass visits `559` nodes, `513` subsectors, and `1709`
  segs. The pinned mutable pass visits only `72` nodes, `56` subsectors, and
  `205` segs, with `17` bbox culls after solid wall spans feed back into
  `R_CheckBBox`.
- The stage05 Python reference is valuable because it froze the exact behavior
  before x86 emission: `82` backface rejects, `17` off-frustum rejects,
  `5` zero-pixel rejects, `30` solid classifications, `70` pass
  classifications, `1` empty trigger reject, `86` stored spans, and one final
  covering solidseg range.
- Stage06 proves that the emitted executable can compute those mutable
  clipping counters itself rather than copying pinned constants from the Python
  reference.
- Stage07 proves the distance/scale prefix without changing clipping
  semantics: 86 accepted spans remain 86 projected records with the same
  first/last anchors.
- The first and last pinned debug spans, `224..255` from seg `605` and
  `143..165` from seg `855`, are useful smoke anchors for the live span buffer.
- Keep the end goal visible: every slice should move one source routine or
  source data layout closer to Doom's real renderer while still ending in a
  runnable emitted PE. Python may parse, plan, and emit bytes, but the runtime
  proof must remain compilerless.

## Lessons From source_stage08_texture_data_setup_debug

- Texture and flat setup is now source-shaped enough for the renderer to stop
  talking in raw map names. `R_AddLine` can classify empty two-sided lines
  using numeric `midtexture == 0` and numeric flat IDs while preserving the
  exact stage07 clipping and projection counters.
- Python-side WAD parsing plus table-emitted PE data is a useful bridge for
  large source layouts. It keeps the executable compilerless and runnable while
  avoiding a premature live x86 port of every cache/allocation detail in
  `R_InitTextures`.
- The first projected span resolves to texture `850` (`AQRUST08`), a direct
  single-patch texture. The last projected span resolves to texture `13`
  (`BIGDOOR1`), which needs composite columns. This gives stage09 a natural
  small proof: draw direct patch-backed opaque midtexture columns first, then
  broaden to composites and two-sided edges in stage10.
- The pinned view has plenty of direct texture work available before composite
  generation: 78 of the accepted projected spans resolve to direct-only
  texture metadata, while 7 resolve to composite-only textures and 1 is mixed.
- Stage09 should produce real WAD pixels but stay narrow. It should not start
  composite generation, two-sided wall edges, plane spans, actors, movement, or
  generalized wall rendering until the first direct wall-column path is visible
  and smoke-tested.

## Lessons From source_stage09_direct_wall_column_pixels_debug

- The first direct-pixel proof is small but genuine: the emitted executable
  now draws 162 columns and 15508 pixels from real patch column bytes selected
  through stage08 `texturecolumnlump` / `texturecolumnofs` metadata.
- The fixed pinned view has fewer one-sided opaque spans than the direct-only
  texture metadata count suggested: 24 projected spans are in the narrow stage09
  wall class, while 62 accepted projected spans are still unsupported two-sided
  cases for this slice.
- Direct patch-backed does not automatically mean safe to draw opaquely. The
  stage09 parser deliberately requires single full-height posts for the emitted
  direct path and keeps non-opaque direct columns counted/skipped.
- Composite generation is the next important unlock. Stage09 attempts 297
  one-sided candidate columns, draws 162 directly, and skips 135 because their
  texture columns need composite cache construction.
- The runtime pixel signature (`2194105880`) is useful because it is updated by
  emitted x86 as pixels are written, not just copied from a Python reference.

## Lessons From source_stage10_composite_two_sided_wall_edges_debug

- Stage10 broadened the wall-column proof without changing the upstream
  traversal, clipping, projection, texture setup, or stage09 direct counters.
  This is the right release shape: each renderer slice should prove one more
  source subsystem while leaving earlier oracles intact.
- Source-shaped composite generation is useful even when only a few columns are
  visible. The pinned view builds 89 composite cache columns and hits 75 cache
  entries, but only 8 composite-backed draw columns survive clipping. The cache
  counters matter because they prove the real texture path, not just the final
  visible pixels.
- The two-sided edge pass produced a concrete handoff for visplanes:
  `727` ceiling mark records, `932` floor mark records, and `PM=1659` total.
  Stage11 should turn those marks into real bounded `visplane_t` records before
  drawing flats.
- Stage10 still uses a table-fed debug bridge for selected column bytes. That
  is acceptable for this phase because Python is following source data and the
  emitted executable still performs the runtime draw loop/signature, but later
  slices should keep pushing stable layouts toward live source-shaped runtime
  state when the behavior becomes shared.
- Real sprites should not be folded into the next sky/masked-wall slice. Doom's
  masked drawing order eventually joins masked wall columns and sprites in
  `R_DrawMasked`, but sprites need `P_LoadThings`, sprite lump setup, and
  `mobj_t`/`player_t` state. Keep that as a separate release boundary.

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

## Released Slice: source_stage04_bbox_visibility_debug

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

Runtime data added:

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

Released because:

- The executable launches and shows a deterministic difference between
  accept-all traversal and bbox-visible traversal.
- Full unit test suite passes.
- Source trace and smoke docs are updated.

## Released Slice: source_stage05_seg_clip_debug

Output:

```text
build/source_stage05_seg_clip_debug.exe
```

Source routines to read and trace/reuse:

- Reuse from stage04: `r_main.c`: `R_PointToAngle`, `viewangletox`,
  `xtoviewangle`, and `clipangle`
- Reuse from stage04: `r_bsp.c`: `R_ClearClipSegs` and `R_CheckBBox`
- `r_bsp.c`: `R_Subsector` as a debug adaptation that now calls
  `R_AddLine`
- `r_bsp.c`: `R_AddLine`
- `r_bsp.c`: `R_ClipSolidWallSegment`
- `r_bsp.c`: `R_ClipPassWallSegment`
- `r_segs.c`: `R_StoreWallRange` as a debug span-recording adaptation

Goal:

Freeze the source-shaped mutable wall-span clipping behavior for pinned MAP01
and make the executable visibly report those counters alongside the stage04
baselines. This proved the desired `R_AddLine` angle clipping,
one-sided/two-sided wall classification, solid/pass clipping, and
`solidsegs`/`R_CheckBBox` feedback loop in Python before committing to the
larger live x86 emission.

User-visible feature:

- Launches the stage04 top-down debug view.
- Keeps the stage04 accept-all and sentinel-only bbox-visible counters as
  comparison baselines.
- Reports the Python reference wall-span traversal pass that starts from
  `R_ClearClipSegs`, visits BSP nodes with `R_CheckBBox`, calls debug
  `R_AddLine` for each visited seg, mutates `solidsegs` through
  `R_ClipSolidWallSegment`, and records visible wall column ranges through a
  debug `R_StoreWallRange`.
- Reports traversal counts for the mutable-clipping pass, rejected backfaces,
  off-frustum segs, zero-pixel spans, solid/pass classification counts, stored
  visible spans, final `solidsegs` count, and overflow/limit guards.
- Leaves the live emitted x86 clipping pass as the explicit next correction.

Runtime data to add:

- Full mutable `solidsegs` array sized for the pinned view, plus `newend`.
- Debug wall-span buffer with start/stop columns and source reason
  (`solid`, `pass`, or clipped fragment), plus the source seg index where
  practical.
- `curline`, `frontsector`, and `backsector` state needed by `R_AddLine`.
- `rw_angle1` because `R_AddLine` stores the global first endpoint angle before
  converting to view-relative angles.
- Counters for mutable-clipping traversal nodes/subsectors/segs, bbox culls,
  backface rejects, left/right frustum rejects, zero-pixel spans, solid/pass
  classification, stored spans, and clip-list insert/extend/merge cases.

Implementation notes:

- Reuse stage04 angle tables and `clipangle` rather than regenerating a second
  projection path.
- The stage04 sentinel-only bbox counts are no longer expected to match the
  mutable-clipping pass. Once solid walls update `solidsegs`, later
  `R_CheckBBox` calls can be rejected by already-occluded screen columns.
- Before emitting x86, build a Python source reference for the pinned `MAP01`
  mutable-clipping pass and freeze its deterministic counters in tests.
- The released stage05 executable applies those frozen counters to the visible
  status/title. This is an intentional agile stopping point, not the final
  compilerless engine behavior.
- `R_StoreWallRange` should be a debug adaptation in stage05: record accepted
  `start..stop` ranges and counters, but do not build full `drawseg_t` wall
  projection yet.
- Source `R_AddLine` treats identical two-sided sectors with no midtexture as
  empty trigger lines. Until texture lookup lands, use the loaded sidedef middle
  texture name (`"-"` means no midtexture) as the stable debug equivalent.
- `R_Subsector` should set `frontsector = sub->sector` before iterating segs,
  matching the source dependency used by `R_AddLine` for one-sided/two-sided
  wall classification.
- It is acceptable to record `linedef->flags |= ML_MAPPED` only as a debug
  counter or deferred note if mutating linedef flags would broaden the slice.
- Keep `R_PointToDist`, `R_ScaleFromGlobalAngle`, `R_RenderSegLoop`,
  `R_DrawColumn`, planes, sprites, and texture-backed drawing out unless the
  wall-span debug slice is already complete and green.

Tests:

- Unit tests for `R_AddLine` angle clipping and x span mapping with synthetic
  segs.
- Unit tests for `R_ClipSolidWallSegment` insert/extend/merge behavior and
  `R_ClipPassWallSegment` non-mutating behavior.
- Unit tests that prove mutable `solidsegs` changes can make `R_CheckBBox`
  reject a later synthetic bbox that the stage04 sentinel-only pass accepts.
- Unit tests for debug `R_StoreWallRange` span buffer bounds and counters.
- Python reference test for pinned `MAP01` seg clipping totals from the fixed
  viewpoint, including mutable-clipping traversal counts, bbox culls, final
  `solidsegs` count, and first/last stored span.
- Smoke test checks the stage05 title for deterministic clipping counters and
  final `solidsegs` count.

Done when:

- The executable launches and reports deterministic wall-span clipping counters
  from the pinned real `MAP01` Python reference.
- Full unit test suite passes.
- Source trace and smoke docs are updated.

Released because:

- The Python source-shaped mutable clipping reference is pinned and covered by
  unit tests.
- The executable launches and reports stage04 baselines plus deterministic
  mutable clipping counters:
  `CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1`.
- The release exposed a useful correction: the next slice should make those
  counters live in emitted x86 before projection starts.

## Released Slice: source_stage06_live_seg_clip_debug

Output:

```text
build/source_stage06_live_seg_clip_debug.exe
```

Source routines to read and trace/reuse:

- Reuse from stage04: `R_PointToAngle`, `viewangletox`, `xtoviewangle`,
  `clipangle`, `R_ClearClipSegs`, and `R_CheckBBox`.
- Reuse from stage05: the Python source-shaped mutable clipping reference and
  pinned MAP01 counters.
- `r_bsp.c`: `R_RenderBSPNode` as a clipping-pass debug adaptation.
- `r_bsp.c`: `R_Subsector` as a live emitted debug adaptation that calls
  `R_AddLine`.
- `r_bsp.c`: `R_AddLine`.
- `r_bsp.c`: `R_ClipSolidWallSegment`.
- `r_bsp.c`: `R_ClipPassWallSegment`.
- `r_segs.c`: `R_StoreWallRange` as a debug span-recording adaptation.

Goal:

Replace stage05's frozen-counter handoff with a real emitted x86 mutable
wall-span clipping traversal. The executable should compute the same pinned
MAP01 counters that the Python reference currently computes, using runtime map
structures, runtime `solidsegs`, and a runtime debug span buffer.

User-visible feature:

- Launches the stage05 top-down debug view.
- Keeps the accept-all and sentinel-only bbox-visible baseline counts.
- Runs a third live emitted clipping pass from `R_ClearClipSegs`.
- Reports the same deterministic mutable clipping counters as the stage05
  reference, but calculated by the emitted executable rather than copied from
  constants.
- Reports first and last stored debug spans, including columns and source seg
  indexes, so the span buffer itself is visible in the smoke signal.

Runtime data to add or make live:

- `curline`, `frontsector`, `backsector`, `rw_angle1`, current source seg
  index, and current debug span reason.
- Mutable `solidsegs` and `newend` used by both `R_CheckBBox` and the live wall
  clippers during the same pass.
- A bounded debug span buffer shaped as `{start, stop, reason, seg_index}`.
- Clipping counters for traversal, bbox culls, backface/off-frustum/zero-pixel
  rejects, solid/pass/empty classifications, stored spans, overflow guards,
  and solidseg insert/extend/merge cases.

Implementation notes:

- `render_bsp_node_clip_debug` mirrors the stage04 bbox traversal, but calls
  `render_debug_subsector_clip` for leaves and uses the mutable
  `solidsegs` when checking back-child bboxes.
- `render_debug_subsector_clip` sets `frontsector = sub->sector`, iterates
  `sub->numlines` from `sub->firstline`, updates traversal/seg counters, sets
  the source seg index, and calls `render_add_line_debug`.
- `render_add_line_debug` is source-shaped: it computes endpoint angles,
  rejects backfaces, clips to `clipangle`, maps through `viewangletox`,
  rejects zero-pixel spans, classifies solid/pass/empty lines from loaded
  sector/sidedef data, then calls the matching clip routine.
- Until texture setup lands, keep the stage05 source equivalent for empty
  trigger lines: identical floor/ceiling flat names, identical light level, and
  sidedef middle texture name `"-"`.
- `render_store_wall_range_debug` records spans only. It does not calculate
  distance, scale, textures, visplanes, masked textures, sprites, or columns.
- No new `tools/x86.py` helpers were needed for this slice; the live clip-list
  shifting and bounded span writes use the existing byte helpers.
- The emitted binary no longer needs a
  `source_stage05_apply_pinned_clip_reference`-style constant copy for clipping
  totals.

Tests:

- Keep the stage05 Python reference tests as the oracle for pinned MAP01.
- Unit tests for any new x86 helpers added for clip-list mutation or span
  storage.
- Unit tests for live debug buffer offsets and first/last span fields.
- Build test verifying the stage06 PE contains live clipping status strings and
  does not contain projection/texture-stage strings such as `R_PointToDist`,
  `R_ScaleFromGlobalAngle`, `R_RenderSegLoop`, or `R_DrawColumn`.
- Smoke test that builds, launches
  `build/source_stage06_live_seg_clip_debug.exe`, checks the stage05 reference
  counters plus first/last span anchors in the title/status, and closes it
  cleanly.

Done when:

- The executable computes the mutable clipping pass live and matches the pinned
  stage05 Python reference counters.
- `python -B -m unittest discover -s tests` passes.
- Source trace and smoke docs are updated.
- No wall projection, texture drawing, planes, sprites, or source_stage07 work
  has started.

Released because:

- The executable launches and reports stage04 baselines plus live-computed
  mutable clipping counters:
  `CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1`.
- The title includes live span-buffer anchors:
  `FSPAN=224-255 FSEG=605 LSPAN=143-165 LSEG=855`.
- The build test confirms the PE contains live clipping status strings and
  does not contain projection/texture-stage strings such as `R_PointToDist`,
  `R_ScaleFromGlobalAngle`, `R_RenderSegLoop`, `R_DrawColumn`, or
  `source_stage07`.

## Released Slice: source_stage07_wall_projection_debug

Output:

```text
build/source_stage07_wall_projection_debug.exe
```

Source routines to read and trace/reuse:

- Reuse from stage06: live bbox-visible BSP traversal, live `R_AddLine`,
  mutable `solidsegs`, debug span records, `rw_angle1`, and current `curline`
  state.
- `m_fixed.c`: `FixedDiv`; reuse the existing emitted `FixedMul`.
- `tables.c`: `finesine` and `finecosine` table data needed by distance and
  scale math.
- `p_local.h`: `VIEWHEIGHT`, and `p_user.c`: the stable `P_CalcHeight` path
  used to justify the fixed debug `viewz` seed.
- `r_main.c`: `R_SetupFrame` as a fixed-player debug adaptation.
- `r_main.c`: `R_PointToDist`
- `r_main.c`: `R_ScaleFromGlobalAngle`
- `r_segs.c`: the distance/scale prefix of `R_StoreWallRange`

Goal:

Turn stage06's accepted wall spans into source-shaped wall projection records.
This should prove Doom's fixed-point distance and scale math for visible wall
ranges while still stopping before texture lookup, plane marking, sprites, and
pixel column drawing.

User-visible feature:

- Launches the stage06 debug view and preserves all stage04/stage06 comparison
  counters.
- Records projected wall-span records for the same 86 live clipping fragments:
  `x1`, `x2`, seg index, `rw_distance`, `rw_normalangle`, `scale1`, `scale2`,
  and `scalestep`.
- Reports deterministic projection stats such as projected span count,
  first/last projected span, min/max distance, min/max scale, and overflow
  guards.
- Draws a compact untextured projection strip where span height or brightness
  reflects calculated scale. This is a debug visualization, not
  `R_RenderSegLoop` or textured column drawing.

Runtime data to add:

- Stable frame fields from `R_SetupFrame`: `viewz`, `viewcos`, `viewsin`,
  `validcount`, `framecount`, and any fixed debug equivalents needed before
  real `player_t`/`mobj_t` exists. Seed `viewz` from the pinned start sector
  floor plus Doom `VIEWHEIGHT` (`41*FRACUNIT`) unless the source read uncovers a
  more faithful fixed-start path.
- `finesine` and `finecosine` table storage, table-emitted from Chocolate Doom;
  preserve the existing `tantoangle`, `viewangletox`, and `xtoviewangle`
  tables.
- A source-shaped `FixedDiv` helper with Doom overflow saturation, used by
  `R_PointToDist` and `R_ScaleFromGlobalAngle`.
- Wall projection scratch fields used by the first half of `R_StoreWallRange`:
  `rw_angle1`, `rw_normalangle`, `rw_distance`, `rw_scale`, `rw_scalestep`,
  `rw_x`, `rw_stopx`, `sidedef`, and `linedef` if needed for traceability.
- A bounded projected-span/debug-drawseg buffer with `x1`, `x2`, source seg
  index, `rw_normalangle`, `rw_distance`, `scale1`, `scale2`, and `scalestep`.
  It should be shaped so a later slice can grow it toward real `drawseg_t`, but
  it should contain only fields proven by this slice.

Implementation notes:

- Keep stage07 focused on projection math. Do not start texture lookup,
  `R_RenderSegLoop`, `R_DrawColumn`, visplanes, masked textures, sprites, or
  light-table selection.
- `R_SetupFrame` should be a fixed-player debug adaptation until
  `P_LoadThings` and real player/mobj state are introduced. The adaptation must
  explicitly document fixed values such as `viewz`.
- Port `R_PointToDist` and `R_ScaleFromGlobalAngle` with Doom fixed-point
  overflow/clamp behavior, using table-emitted trigonometry rather than
  runtime floating point.
- Replace the stage06 debug-only span store with a projected debug
  `R_StoreWallRange` adaptation that still records the same span fields first,
  then calculates `rw_normalangle`, `rw_distance`, `scale1`, `scale2`, and
  `scalestep`. Stop immediately before texture-boundary, plane, and masked
  texture decisions.
- Preserve stage06's span records as an input/debug comparison. Stage07 should
  add projection fields, not change clipping semantics or the 86-span oracle.
- Before emitting x86, build and freeze a Python source-shaped projection
  reference for pinned MAP01, including first/last projected spans and min/max
  distance/scale values.

Tests:

- Unit tests for selected `finesine`/`finecosine` entries and table offsets.
- Unit tests for `R_PointToDist` synthetic points in each quadrant and near the
  view origin.
- Unit tests for `R_ScaleFromGlobalAngle` clamp/min/max behavior and selected
  synthetic angles.
- Unit tests for `FixedDiv` overflow saturation and signed division behavior.
- Python reference test for pinned `MAP01` projected-span stats from the
  stage06 accepted spans and fixed viewpoint.
- Build and smoke tests that verify the stage07 title/status reports
  deterministic projection counters and still reports the unchanged stage06
  clipping counters.

Done when:

- The executable launches and reports deterministic wall projection counters
  from real `MAP01` accepted spans.
- Full unit test suite passes.
- Source trace and smoke docs are updated.
- The PE contains projection status strings but still does not contain
  texture/column-stage strings such as `R_RenderSegLoop`, `R_DrawColumn`,
  `R_InitTextures`, or `source_stage08`.

Released because:

- The executable launches and preserves the stage04 baselines plus the stage06
  live clipping totals:
  `CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1`.
- The title includes the unchanged live span-buffer anchors:
  `FSPAN=224-255 FSEG=605 LSPAN=143-165 LSEG=855`.
- The title reports deterministic fixed-frame and projection stats:
  `VZ=2686976 VCOS=65535 VSIN=25 VALID=1 FRAME=1 PRJ=86 MIND=2073560 MAXD=58720255 MINS=11702 MAXS=108495 FPRJ=224-255 FPSEG=605 LPRJ=143-165 LPSEG=855`.
- The build test confirms the PE contains projection status strings and does
  not contain `R_RenderSegLoop`, `R_DrawColumn`, `R_InitTextures`, or
  `source_stage08`.

## Released Slice: source_stage08_texture_data_setup_debug

Output:

```text
build/source_stage08_texture_data_setup_debug.exe
```

Goal:

Load and validate Doom texture, flat, and patch metadata in source-shaped
layouts, then resolve MAP01 sidedef texture names and sector flat names to
numeric IDs. Preserve the stage07 clipping/projection pipeline and retire the
raw-name empty-line shortcut by using `midtexture == 0`.

Released because:

- The executable launches and reports the unchanged stage07 clipping and
  projection counters.
- The title reports deterministic texture/flat setup counts:
  `TEX=963 PN=1054 FLAT=246 DIRC=80797 COMPC=26323 FPTEX=850 LPTEX=13 EMID=1`.
- Unit tests cover synthetic `PNAMES`, `TEXTURE1`, optional `TEXTURE2`, bad
  offsets, missing patch names, bounded overflow, texture-name lookup,
  pinned MAP01 ID resolution, and the unchanged clipping/projection oracle.
- The smoke test builds, launches, checks the title, and closes
  `build/source_stage08_texture_data_setup_debug.exe`.
- The PE contains texture setup status strings and still excludes
  `R_RenderSegLoop`, `R_DrawColumn`, `R_GetColumn`, `R_GenerateComposite`,
  `R_DrawColumnInCache`, `R_InitColormaps`, `R_InitLightTables`, and
  `source_stage09`.

Implementation note:

Stage08 is intentionally a setup/data release. It uses Python to parse and
validate the pinned WAD/source-shaped metadata and emits deterministic PE data
tables directly. That is still inside the project rules: no compiler, no
assembler, no linked code blobs, and a runnable emitted PE at the end. Later
slices can decide, case by case, whether a setup step should become live x86 or
remain table-emitted data.

## Released Slice: source_stage09_direct_wall_column_pixels_debug

Output:

```text
build/source_stage09_direct_wall_column_pixels_debug.exe
```

Source routines to read and trace/reuse:

- Reuse from stage08: live clipping/projection, texture IDs, flat IDs, direct
  vs composite column metadata, and first/last projected-span texture IDs.
- `r_data.c`: `R_GetColumn`, direct patch-backed column path only. Defer
  `R_GenerateComposite` and `R_DrawColumnInCache`.
- `r_draw.c`: `R_DrawColumn`, enough of the source column stepping path to draw
  opaque columns into the existing 32-bit framebuffer.
- `r_segs.c`: `R_StoreWallRange` one-sided opaque midtexture setup and the
  midtexture branch of `R_RenderSegLoop`, adapted as a narrow debug loop rather
  than the full wall renderer.
- WAD graphics data: patch column post parsing, `PLAYPAL`, and the first
  usable `COLORMAP` row or an explicitly documented fixed-colormap adaptation
  for converting Doom palette indices to visible framebuffer RGB values.

Goal:

Draw the first real Doom wall texture pixels from the pinned WAD, using only
direct patch-backed, one-sided opaque midtexture columns. This should be the
smallest visible proof that stage08's texture metadata can drive actual WAD
pixel drawing without starting the full `R_RenderSegLoop` feature set.

Why this scope changed:

The previous plan included composites, `R_GenerateComposite`,
`R_DrawColumnInCache`, full colormap/light-table setup, and first pixels in one
slice. Stage08 showed the first projected texture (`AQRUST08`, id `850`) is a
direct single-patch texture, while the last projected texture (`BIGDOOR1`, id
`13`) needs composites. The agile next step is therefore direct columns first:
real pixels, fewer moving parts, and a clear smoke signal.

User-visible feature:

- Launches a fixed-view render/debug window and preserves the stage08 title
  counters.
- Draws a deterministic subset of single-sided opaque wall columns using real
  patch column bytes from the WAD.
- Reports direct wall spans considered, direct columns attempted, columns
  drawn, skipped composite columns, skipped non-opaque/two-sided cases, first
  drawn texture ID/name/column, and a small framebuffer checksum or sampled RGB
  signature.

Runtime data to add:

- `dc_x`, `dc_yl`, `dc_yh`, `dc_iscale`, `dc_texturemid`, `dc_source`,
  `dc_colormap`, and a palette-index-to-32-bit framebuffer adaptation.
- `ylookup`/`columnofs`-equivalent addressing for the existing 320x200
  framebuffer.
- Direct patch column lookup from stage08 `texturecolumnlump` and
  `texturecolumnofs`; columns whose lookup needs a composite are counted and
  skipped visibly.
- Minimal one-sided wall globals: `midtexture`, `rw_offset`,
  `rw_centerangle`, `rw_midtexturemid`, and enough scale stepping to feed
  `R_DrawColumn`.

Implementation notes:

- Keep the renderer bounded to direct patch-backed opaque midtextures. Do not
  draw upper/lower two-sided walls, masked midtextures, sprites, floors,
  ceilings, sky, or composite texture columns in stage09.
- Prefer a dedicated wall-pixel pane or overlay that can coexist with the
  current debug view. The smoke test should check a deterministic pixel
  signature rather than relying only on window text.
- If an accepted span has `texture id 0`, needs composite columns, or is a
  two-sided/non-opaque case, count it in the title/status and move on.
- Keep `R_InitLightTables` out unless the implementation truly needs it for
  the narrow fixed-colormap proof. If a fixed colormap is used, document it in
  the trace manifest as a deliberate stage09 adaptation.

Tests:

- Synthetic tests for patch header/column-directory parsing and simple post
  decoding.
- Unit tests for direct `R_GetColumn` wrapping/masking behavior and for
  composite-needed columns being skipped rather than drawn.
- Unit tests for `R_DrawColumn` stepping against small synthetic columns,
  including clipping to the framebuffer.
- Pinned MAP01 reference test for direct one-sided spans/columns touched by the
  fixed viewpoint.
- Build test confirming stage09 contains direct texture drawing status strings
  and does not contain `R_GenerateComposite`, `R_DrawColumnInCache`,
  visplane/sprite/masked-wall strings, or `source_stage10`.
- Smoke test that launches the executable, verifies preserved stage08 counters,
  deterministic direct-column counters, and a framebuffer pixel signature.

Released because:

- `build/source_stage09_direct_wall_column_pixels_debug.exe` exists and
  launches.
- It draws deterministic real wall texture pixels from direct WAD patch
  columns:
  `DWSP=86 OPQSP=24 DCOL=297 DRAW=162 SKC=135 SKU=62 ZTEX=0 MASK=0 FTEX=850 FN=AQRUST08 FCOL=127 PIX=15508 SIG=2194105880`.
- Stage08 setup, clipping, and projection counters remain unchanged.
- Unit tests cover synthetic patch header/post parsing, direct `R_GetColumn`
  wrapping, composite-needed skips, `R_DrawColumn` stepping, pinned MAP01
  direct-column counters, PE string exclusions, and the GUI smoke path.
- `python -B -m unittest discover -s tests` passes and the scripted smoke test
  launches/closes the binary.
- Source trace and smoke docs are updated.

## Released Slice: source_stage10_composite_two_sided_wall_edges_debug

Output:

```text
build/source_stage10_composite_two_sided_wall_edges_debug.exe
```

Source routines to read and trace/reuse:

- Reuse from stage09: direct pixel drawing, palette/colormap adaptation,
  `R_DrawColumn`, direct `R_GetColumn`, and the runtime pixel signature path.
- `r_data.c`: `R_GenerateComposite`, `R_DrawColumnInCache`, and the composite
  branch of `R_GetColumn`.
- `r_segs.c`: upper/lower two-sided wall setup in `R_StoreWallRange` and the
  toptexture/bottomtexture paths in `R_RenderSegLoop`.
- `r_segs.c`: wall clipping arrays such as `ceilingclip`, `floorclip`,
  `sprtopclip`, `sprbottomclip`, and `maskedtexturecol`, shaped only as far as
  this slice needs.
- `r_plane.c`: `R_ClearPlanes` and `R_CheckPlane` only as record/count hooks if
  the wall-edge branch needs source-shaped floor/ceiling marking. Do not draw
  plane spans in this slice.

Goal:

Broaden the first-pixel proof from direct one-sided opaque walls to composite
texture columns and supported two-sided upper/lower wall edges. Stage09 skipped
135 one-sided candidate columns because they need composites; stage10 should
turn that deferred work into visible pixels, then use the same column path for
the first supported two-sided top/bottom wall edges. This remains a wall-column
renderer slice, not floor/ceiling rendering, masked midtextures, actors, sky,
movement, or gameplay.

User-visible feature:

- Draws the stage09 direct wall pixels unchanged.
- Adds composite-backed columns for one-sided opaque midtextures that stage09
  counted as `SKC=135`.
- Adds visible upper and/or lower texture columns for supported two-sided wall
  edge spans from the `SKU=62` stage09 unsupported-span set.
- Reports preserved stage09 direct counters, composite columns built/drawn,
  composite cache hits, composite skips/overflows, upper columns, lower
  columns, unsupported masked columns, plane-mark records, and a framebuffer
  signature.
- Preserves upstream stage08/stage09 counters.

Runtime data to add:

- Bounded composite cache storage keyed by `(texture, column)`, with cache
  entry state, source pointer, texture height, build/hit/overflow counters, and
  deterministic eviction-free behavior for the pinned view.
- Source-shaped composite column building that draws patch posts into a
  temporary cache using `R_DrawColumnInCache` semantics. Use real patch post
  data; do not substitute placeholder pixels.
- Composite branch of `R_GetColumn`: direct columns still return direct patch
  bytes, composite columns build or reuse cache bytes, bad/missing columns are
  counted and skipped.
- `ceilingclip[320]` and `floorclip[320]`, initialized like the source view
  clip arrays for the fixed 320x200 debug view.
- Minimal wall-edge globals and stepping fields:
  `toptexture`, `bottomtexture`, `rw_toptexturemid`, `rw_bottomtexturemid`,
  `worldtop`, `worldbottom`, `worldhigh`, `worldlow`, `topfrac`,
  `bottomfrac`, `topstep`, `bottomstep`, `pixhigh`, `pixlow`,
  `pixhighstep`, and `pixlowstep`.
- Plane-mark debug records/counters only if `markfloor` or `markceiling` is
  reached. These records are for stage11; stage10 must not draw flat spans.

Implementation notes:

- Freeze a Python source-shaped pinned reference before emitting x86. It should
  classify the stage09 skipped work into composite one-sided columns,
  supported upper columns, supported lower columns, masked-midtexture skips,
  sky/plane-only skips, and unsupported wall cases.
- It is fine to implement the stage10 executable in two internal passes if that
  keeps the proof small: one-sided composite columns first, then supported
  two-sided top/bottom wall edges. The release is done only when both are
  visible or the reference proves one class has no reachable pinned pixels.
- Keep the fixed colormap adaptation from stage09. Full light tables remain
  deferred unless the source read proves they are unavoidable for deterministic
  composite/two-sided pixels.
- Initialize and update `ceilingclip` / `floorclip` enough for upper/lower wall
  edge clipping, but leave `R_DrawPlanes`, flat spans, and sky drawing out.
- Composite cache limits must be deterministic and visible. Overflow should be
  counted, not silently fall back to placeholder pixels.
- Do not start stage11 while building stage10.

Tests:

- Synthetic `R_DrawColumnInCache` tests for clipping posts by `originy` and
  cache height, including overlapping patch order.
- Synthetic `R_GenerateComposite` tests with direct-only, composite, missing,
  and overflow columns.
- Tests for direct vs composite `R_GetColumn` dispatch, cache build/hit paths,
  and composite-needed columns no longer being skipped.
- Synthetic `R_RenderSegLoop` upper/lower edge tests for `ceilingclip`,
  `floorclip`, `pixhigh`, and `pixlow` clipping.
- Pinned MAP01 reference tests for composite columns built/drawn, supported
  upper/lower columns, masked skips, plane-mark counters, first/last drawn
  texture names, and framebuffer signature.
- Build/smoke tests verifying preserved stage08/stage09 counters plus new
  composite/two-sided counters, and confirming flat-span drawing, sky drawing,
  masked texture drawing, actors, gameplay, and `source_stage11` strings are
  absent.

Done when:

- The stage10 executable draws deterministic direct, composite, and supported
  upper/lower wall edge pixels from the pinned WAD.
- Stage08/stage09 counters remain unchanged, and stage09's direct pixel
  signature changes only as documented by the broader stage10 framebuffer
  signature.
- Full unit tests and GUI smoke pass.
- Source trace and smoke docs are updated.

Released because:

- `build/source_stage10_composite_two_sided_wall_edges_debug.exe` exists and
  launches.
- It preserves the stage09 direct wall-pixel signal:
  `DWSP=86 OPQSP=24 DCOL=297 DRAW=162 SKC=135 SKU=62 ZTEX=0 MASK=0 FTEX=850 FN=AQRUST08 FCOL=127 PIX=15508 SIG=2194105880`.
- It reports deterministic stage10 composite and wall-edge counters:
  `CMB=89 CMH=75 CMO=0 MCOL=2 MCEMP=133 UCOL=478 UCOMP=6 LCOL=138 PM=1659 F10TEX=850 F10N=AQRUST08 L10TEX=887 L10N=AQSECT08 TCOL=780 TPIX=37546 TSIG=4201955800`.
- Synthetic tests cover `R_DrawColumnInCache`, `R_GenerateComposite`,
  direct/composite `R_GetColumn` dispatch, and upper/lower wall-edge clipping.
- Pinned MAP01 tests cover composite builds/hits, drawn/skipped composite
  columns, supported upper/lower columns, plane-mark counters, first/last drawn
  texture names, and the framebuffer signature.
- `python -B -m unittest discover -s tests` passes and the scripted smoke test
  launches/closes the binary.
- Source trace and smoke docs are updated.

## Next Releasable Slice: source_stage11_visplanes_floor_ceiling_debug

Output:

```text
build/source_stage11_visplanes_floor_ceiling_debug.exe
```

Source routines to read and trace/reuse:

- Reuse from stage10: wall drawing, `ceilingclip` / `floorclip`, plane-mark
  records, sector flat IDs/heights/light levels, palette/colormap adaptation,
  and framebuffer signature.
- `r_bsp.c`: the `R_Subsector` calls to `R_FindPlane` for `floorplane` and
  `ceilingplane`.
- `r_segs.c`: the `R_StoreWallRange` calls to `R_CheckPlane` and the
  `R_RenderSegLoop` writes to `plane->top[x]` / `plane->bottom[x]`.
- `r_plane.c`: `R_ClearPlanes`, `R_FindPlane`, `R_CheckPlane`,
  `R_MakeSpans`, `R_MapPlane`, and `R_DrawPlanes`.
- `r_draw.c`: `R_DrawSpan` for regular flat spans.
- WAD flat data: 64x64 flat lumps addressed through stage08 flat metadata.

Goal:

Turn the stage10 floor/ceiling mark records into the first source-shaped
flat-span rendering proof. Draw deterministic floor and ceiling flat pixels for
the fixed pinned view while preserving the wall-column renderer. This should be
the first release where the screen starts to read as a Doom room rather than a
wall-only debug pane.

User-visible feature:

- Draws stage10 wall columns plus supported floor and ceiling flat spans.
- Reports visplanes found, visplanes split/merged, flat spans mapped, flat
  pixels drawn, skipped sky ceilings, first floor/ceiling flat IDs/names, and a
  framebuffer signature.
- Preserves upstream traversal, clipping, projection, texture, direct-column,
  composite, and wall-edge counters.

Runtime data to add:

- Bounded `visplane_t`-shaped records with `height`, `picnum`, `lightlevel`,
  `minx`, `maxx`, and per-column `top` / `bottom` arrays.
- `floorplane`, `ceilingplane`, `lastvisplane`, `spanstart`, and the fixed-view
  plane stepping data needed by `R_MapPlane`.
- Plane mapping tables and caches for the fixed 320x200 view:
  `yslope[200]`, `distscale[320]`, `basexscale`, `baseyscale`,
  `cachedheight[200]`, `cacheddistance[200]`, `cachedxstep[200]`, and
  `cachedystep[200]`.
- Span globals mirroring `R_DrawSpan`: `ds_y`, `ds_x1`, `ds_x2`,
  `ds_xfrac`, `ds_yfrac`, `ds_xstep`, `ds_ystep`, and `ds_source`.
- Flat lookup/source pointers for 64x64 WAD flat data, using the same fixed
  palette/colormap adaptation as stage09/stage10.
- Visible overflow/skip counters for visplane, opening/span, unsupported sky,
  and flat-source failures.

Implementation notes:

- Source order matters: `R_ClearPlanes` runs at frame start; subsector handling
  calls `R_FindPlane` for current floor/ceiling candidates; wall range storage
  calls `R_CheckPlane`; wall columns write top/bottom marks; `R_DrawPlanes`
  later turns those visplane marks into spans. Stage11 should mirror that order
  even if some structures are still table-fed for the fixed pinned view.
- Stage10 provides the pinned handoff records for this: `727` ceiling marks,
  `932` floor marks, and `PM=1659` total records. Stage11 should first consume
  those records through source-shaped visplane find/check logic before mapping
  any flat pixels.
- The preferred implementation path is two internal checks: first reproduce the
  Stage10 plane-mark totals through bounded `visplane_t` records without
  drawing flats, then enable `R_MakeSpans` / `R_MapPlane` / `R_DrawSpan` over
  real 64x64 flat lumps.
- Keep sky ceilings counted but undrawn in Stage11. A sky flat is a source
  branch inside `R_DrawPlanes`, but the sky wall texture path is large enough
  to deserve Stage12.
- Keep the fixed view and fixed colormap. Do not add sky rendering, dynamic
  lights, movement, actors, masked midtextures, or gameplay in stage11.
- Bound all arrays and make overflow visible in the title/status rather than
  silently dropping spans.

Tests:

- Synthetic `R_FindPlane` and `R_CheckPlane` tests for reuse, split, min/max,
  and overflow behavior.
- Synthetic `R_MakeSpans`, `R_MapPlane`, and `R_DrawSpan` tests against a tiny
  deterministic flat and fixed camera values.
- Pinned MAP01 reference tests for visplane counts, first flat IDs/names, flat
  span/pixel totals, skipped sky counters, and framebuffer signature.
- Build/smoke tests verifying preserved stage10 counters plus flat-span
  counters, and confirming sky rendering, actors, masked textures, movement,
  gameplay, and `source_stage12` strings are absent.

Done when:

- The stage11 executable draws deterministic wall, floor, and ceiling pixels
  from the pinned WAD for the fixed view.
- Full unit tests and GUI smoke pass.
- Source trace and smoke docs are updated.

## Releasable Slice After That: source_stage12_sky_and_masked_midtextures_debug

Output:

```text
build/source_stage12_sky_and_masked_midtextures_debug.exe
```

Source routines to read and trace/reuse:

- Reuse from stage11: wall columns, regular flat spans, visplanes,
  `ceilingclip` / `floorclip`, flat IDs, palette/colormap adaptation, and
  framebuffer signature.
- `r_sky.c`: `R_InitSkyMap`.
- `g_game.c`: sky flat/texture selection for Doom II `MAP01` only as a fixed
  debug adaptation (`F_SKY1` and `SKY1`).
- `r_plane.c`: sky branch inside `R_DrawPlanes`.
- `r_segs.c`: masked midtexture setup in `R_StoreWallRange`,
  `maskedtexturecol` writes in `R_RenderSegLoop`, and
  `R_RenderMaskedSegRange`.
- `r_things.c`: `R_DrawMaskedColumn` only as the shared masked-column drawing
  primitive. Real sprite projection remains stage13.

Goal:

Add the two most important deferred render-order features that do not require
real actor state yet: sky ceiling columns and masked two-sided midtexture
columns. Preserve the fixed-view wall and flat renderer while proving Doom's
late masked drawing order for wall openings. Do not add real sprites, movement,
actors, gameplay, or a full game loop in this slice.

User-visible feature:

- Draws stage11 walls/floors/ceilings plus supported sky ceiling columns.
- Draws deterministic masked midtexture columns from real WAD patch/composite
  data after solid wall and flat drawing.
- Reports sky visplanes/columns/pixels, masked wall spans/columns/pixels,
  masked ordering records, skipped sprite records, first sky texture name,
  first masked texture name, and a framebuffer signature.
- Preserves upstream stage10/stage11 counters.

Runtime data to add:

- `skyflatnum`, `skytexture`, `skytexturemid`, and the fixed Doom II `MAP01`
  sky texture selection needed by the debug view.
- `maskedtexturecol` / opening-style storage for two-sided midtexture columns,
  with bounded overflow counters.
- Minimal drawseg fields needed by `R_RenderMaskedSegRange`: `x1`, `x2`,
  `scale1`, `scalestep`, `sprtopclip`, `sprbottomclip`, `maskedtexturecol`,
  and the sidedef/sector texture fields already proven by earlier slices.
- Masked column globals used by `R_DrawMaskedColumn`, including `sprtopscreen`,
  `spryscale`, `mfloorclip`, and `mceilingclip`.

Implementation notes:

- Keep Stage12 ordered like the source frame: solid walls first, regular flats
  next, then late masked drawing. Sky comes through the sky branch in
  `R_DrawPlanes`; masked midtextures come through drawseg/opening records.
- A fixed `SKY1` selection is acceptable for the pinned Doom II `MAP01` proof,
  but document it as a debug adaptation and keep later generalized episode/map
  sky selection small.
- The shared masked-column primitive may be source-shaped in Python first, but
  the executable must still draw deterministic sky/masked pixels and update a
  runtime signature.
- Do not load things or project sprites in Stage12. It may include zero-sprite
  ordering counters so Stage13 has a clean hook, but real sprite data belongs
  with `P_LoadThings` and `mobj_t` setup.

Tests:

- Synthetic sky-column tests for angle-to-sky texture column selection and
  fixed `skytexturemid` stepping.
- Synthetic `maskedtexturecol` / opening tests for bounded storage, clipping,
  and draw order after walls/flats.
- Synthetic `R_DrawMaskedColumn` tests for post clipping against
  `mfloorclip`/`mceilingclip`.
- Pinned MAP01 reference tests for sky counts, masked wall counts, first names,
  skipped sprite count, and framebuffer signature.
- Build/smoke tests verifying preserved stage11 counters plus sky/masked
  counters, and confirming real sprites, actors, movement, gameplay, and
  `source_stage13` strings are absent.

Done when:

- The stage12 executable draws deterministic wall, flat, sky, and masked
  midtexture pixels from the pinned WAD.
- Real sprite/thing/gameplay work remains absent and visibly counted/deferred.
- Full unit tests and GUI smoke pass.
- Source trace and smoke docs are updated.

## Future Backlog

Likely next slices after stage12, intentionally kept as headlines:

- `source_stage13_things_sprites_and_real_frame_setup`: `P_LoadThings`,
  sprite lump metadata, first visible sprites, and real `player_t`/`mobj_t`
  frame setup.
- `source_stage14_game_loop_input_collision`: tic/update loop, input, movement,
  and map collision.
- `source_stage15_gameplay_state_and_ui`: weapons, status bar, automap/menu
  shell, sound hooks, and enough game state to feel like Doom.

At that point the fixed render harness can start becoming the game, not just a
source-shaped renderer proof.
