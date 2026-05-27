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

## Rules

1. Do not use a compiler, assembler, linker, CMake, MSBuild, MinGW, NASM, or
   compiler-produced code blobs in the emitted path.
2. Do not translate all of Doom at once.
3. Each emitted routine should have a source trace entry: source file, source
   function, intended emitted function label, and validation notes.
4. Prefer source-faithful data layouts before source-faithful control flow.
5. Keep stage07 as a visual proof, but do not build the next phase by piling
   more special cases into it.

## First Source-Guided Slice

Start with WAD and map setup because the current repo already has working
parsers and emitted WAD reads.

Target source routines:

- `w_wad.c`: `W_NumLumps`
- `w_wad.c`: `W_CheckNumForName`
- `w_wad.c`: `W_GetNumForName`
- `w_wad.c`: `W_LumpLength`
- `w_wad.c`: `W_ReadLump`
- `p_setup.c`: `P_LoadVertexes`
- `p_setup.c`: `P_LoadSectors`
- `p_setup.c`: `P_LoadSideDefs`
- `p_setup.c`: `P_LoadLineDefs`

Initial emitted executable:

```text
build/source_stage01_wad_map.exe
```

Expected behavior:

- Open the pinned IWAD path.
- Build a runtime lump directory in emitted code.
- Find `MAP01`.
- Load `VERTEXES`, `SECTORS`, `SIDEDEFS`, and `LINEDEFS`.
- Display counts and simple sanity values in the framebuffer.

This is deliberately less flashy than stage07. It is the bridge from
experiment to source-guided engine port.

## Then

After the first slice works, move to the source structures that unlock real
Doom rendering:

- `p_setup.c`: `P_LoadNodes`, `P_LoadSegs`, `P_LoadSubsectors`
- `p_setup.c`: `P_GroupLines`
- `r_main.c`: `R_InitTables`, `R_InitTextureMapping`, `R_SetupFrame`
- `r_bsp.c`: `R_RenderBSPNode`, `R_Subsector`
- `r_segs.c`: `R_RenderSegLoop`
- `r_draw.c`: `R_DrawColumn`

At that point the renderer can stop being a raycast approximation and start
following Doom's BSP/seg/column pipeline.

## Immediate Engineering Work

1. Add a source trace manifest for source routine to emitted label mapping.
2. Consolidate duplicated x86 helpers from the stage emitters into `tools/x86.py`
   only when a new source-guided routine needs them.
3. Create `tools/emit_source_stage01_wad_map.py` rather than extending stage07.
4. Add unit tests that validate emitted data layout constants against synthetic
   WAD/map records.
5. Add a smoke test that launches the emitted executable and checks that it
   reports the expected map lump counts.
