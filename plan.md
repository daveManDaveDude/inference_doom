# Build DOOM Without a Compiler or Linker — Codex Implementation Plan

## 0. Intent

This project is an experiment in building a working Windows DOOM executable without invoking a C/C++ compiler, assembler, linker, CMake, MSBuild, Visual Studio, MinGW, NASM, or SDK build tools during the final no-compiler build path.

The inspiration is the existing `inferenceCompiler` calculator repo, where a Python script emits a native Win32 PE32 executable directly.

The first goal is not to build a general-purpose compiler.

The goal is to progressively build a domain-specific executable emitter that can produce increasingly DOOM-like Windows binaries, eventually running a legal free DOOM IWAD.

## 1. Hard constraints

1. Target platform: Windows.
2. Initial binary format: PE32 x86.
3. Final no-compiler path must be driven by Python.
4. The no-compiler path must emit an `.exe` directly.
5. The no-compiler path must not call:
   - C/C++ compiler
   - assembler
   - linker
   - CMake
   - MSBuild
   - Visual Studio build tools
   - MinGW/GCC/Clang
   - NASM/FASM/MASM
6. The no-compiler emitter may use:
   - Python standard library
   - explicit PE-writing code
   - explicit import-table writing code
   - explicit relocation/fixup logic
   - explicit x86 instruction helpers
   - generated static data tables
   - small domain-specific codegen helpers
7. The no-compiler emitter must not become a general-purpose compiler or general-purpose linker unless explicitly promoted to that role in a later phase.
8. The project must use legally distributable assets.
9. Use Freedoom IWADs for assets, not commercial DOOM WADs.
10. Do not commit commercial WAD files.

## 2. Recommended platform decision

Use **32-bit Windows PE32 x86** for the first serious path.

Reasons:

- The existing calculator emitter is already PE32/x86.
- The existing emitter already knows how to:
  - write PE headers
  - write a section table
  - write an import table
  - emit absolute addresses, RVAs and rel32 calls
  - generate a GUI subsystem executable
  - call Win32 APIs through the IAT
- Chocolate Doom’s Windows build instructions favour a 32-bit Windows build.
- 32-bit x86 instruction encoding is more familiar and easier to hand-emit than x64.
- 32-bit Windows binaries still run on normal 64-bit Windows.
- DOOM is old enough that 32-bit is more than enough.

Do not start with x64. Move to x64 only after a complete PE32 path exists.

## 3. Reference projects

### 3.1 Behavioural/game reference

Use Chocolate Doom as the first reference engine.

Why Chocolate Doom:

- It is intentionally conservative.
- It aims to behave like vanilla DOOM.
- It has a known Windows build path.
- Its architecture is closer to the original DOOM engine than many modern ports.
- It avoids the complexity of modern OpenGL/Vulkan renderers.

### 3.2 Asset reference

Use Freedoom.

Recommended IWADs:

- `freedoom1.wad`
- `freedoom2.wad`

Initial target should be `freedoom1.wad` or `freedoom2.wad`, whichever is easiest to boot with the selected reference build.

The repository should include a setup script that downloads a known Freedoom release zip and verifies a SHA256 hash.

Do not rely on users manually finding a WAD.

## 4. Lessons from the calculator repo

The calculator project teaches several important lessons that should transfer directly.

### 4.1 Keep the C/C++ source as the behavioural reference

The calculator repo kept `src/main.cpp` as the readable reference, while the actual no-compiler artifact came from `tools/emit_win32_calculator.py`.

Do the same here.

Keep a compiled DOOM reference path first.

Then build a no-compiler emitter against that reference.

### 4.2 Use a staged emitter, not a grand compiler

The calculator emitter worked because it was specific.

It emitted exactly what the calculator needed:

- PE headers
- one `.text` section
- import descriptors
- IAT entries
- UTF-16 strings
- global state
- hand-encoded x86 routines
- Win32 calls

For DOOM, preserve that style.

Do not ask Codex to “write a compiler”.

Ask Codex to add one small executable capability at a time.

### 4.3 Keep labels and fixups

The existing label/fixup model is crucial.

The DOOM emitter should keep and expand the same concepts:

- labels
- absolute address fixups
- RVA fixups
- rel32 fixups
- section-relative addresses
- data labels
- import labels

Promote these into a reusable `pe32.py` / `x86.py` mini-framework early.

### 4.4 Build validation into every phase

The calculator repo’s verification path included launching the GUI and driving it with Win32 messages.

The DOOM repo needs similar smoke tests:

- validate PE headers
- validate imports
- launch executable
- confirm window appears
- confirm framebuffer changes
- confirm input can be delivered
- confirm the IWAD loads
- confirm first level can be reached
- confirm deterministic demo or scripted movement runs

### 4.5 Avoid premature abstraction

The calculator README explicitly says not to introduce a general-purpose linker abstraction yet.

Follow the same principle.

Only add abstraction when duplication becomes painful.

Good abstraction:

- PE writer
- x86 encoder helpers
- import table builder
- WAD parser
- framebuffer blitter
- fixed-point math helper emitter
- generated lookup tables

Bad early abstraction:

- C compiler
- generic IR
- full assembler syntax parser
- generic linker
- ELF/COFF object loader, unless explicitly chosen as a later experimental branch

## 5. Realistic feasibility assessment

### 5.1 Can this be managed with GPT-5.5 and xhigh reasoning?

Yes, but only if the plan is staged.

A direct prompt like:

> Build DOOM without a compiler or linker.

is too large.

A staged approach is realistic:

1. Build Chocolate Doom normally on Windows.
2. Run Freedoom legally.
3. Extract the smallest viable DOOM engine path.
4. Build a no-compiler PE emitter scaffold.
5. Emit a Win32 framebuffer window.
6. Emit input handling.
7. Emit WAD directory parsing.
8. Emit enough rendering to draw a flat/texture/sample screen.
9. Emit map loading.
10. Emit fixed-point/player movement.
11. Emit a tiny “DOOM-like” renderer.
12. Gradually replace reference C modules with emitted x86 routines.
13. Eventually produce a standalone emitted executable.

### 5.2 What is unrealistic?

A complete, hand-emitted Chocolate Doom clone in one pass is unrealistic.

The hard parts are not just PE emission. The hard parts are:

- WAD parsing
- zone memory
- map loading
- BSP traversal
- column rendering
- texture composition
- fixed-point arithmetic
- event loop
- timing
- audio
- save/config paths
- input mapping
- endianness assumptions
- large static tables
- debugging generated x86
- verifying behavioural equivalence

### 5.3 What is the most likely success path?

The most likely success path is a ladder:

- First: normal compiled Chocolate Doom + Freedoom.
- Then: emitted Win32 executable that opens a window and draws pixels.
- Then: emitted executable that reads Freedoom WAD metadata.
- Then: emitted executable that displays a WAD lump or title graphic.
- Then: emitted executable that loads a map and draws a simple top-down view.
- Then: emitted executable that renders a DOOM-like first-person view.
- Then: emitted executable that runs enough of the real data structures to feel like DOOM.
- Finally: emitted executable that can boot a Freedoom level.

That is the fun version and has a high chance of visible wins.

## 6. Repository layout

Create a new repo, for example:

```text
doom-no-compiler/
  README.md
  plan.md
  LICENSE
  .gitignore

  docs/
    architecture.md
    calculator-lessons.md
    phase-checklist.md
    wad-format-notes.md
    pe32-notes.md
    x86-notes.md

  scripts/
    setup_freedoom.ps1
    setup_freedoom.py
    verify_freedoom.py
    build_reference_chocolate_doom.md
    smoke_test_reference.ps1
    smoke_test_emitted.ps1

  third_party/
    README.md
    freedoom/
      .gitkeep

  reference/
    README.md
    chocolate-doom/
      .gitkeep

  src_reference/
    README.md
    tiny_doom_reference.c
    tiny_wad_probe.c
    tiny_framebuffer.c

  tools/
    emit_pe32.py
    x86.py
    pe32.py
    wad.py
    emit_stage01_window.py
    emit_stage02_framebuffer.py
    emit_stage03_wad_probe.py
    emit_stage04_picture_viewer.py
    emit_stage05_map_probe.py
    emit_stage06_topdown_map.py
    emit_stage07_raycast_view.py

  build/
    .gitkeep

  tests/
    test_pe32_headers.py
    test_x86_encoding.py
    test_wad_parser.py
    test_emitted_imports.py
```

## 7. Phase plan

## Phase 1 — Build normal DOOM first

### Goal

Get a legal, reproducible Windows reference build running with Freedoom.

### Deliverables

- `scripts/setup_freedoom.py`
- `scripts/setup_freedoom.ps1`
- `docs/build-reference-chocolate-doom.md`
- `docs/reference-runbook.md`
- screenshots or notes proving the reference engine starts with Freedoom
- exact command line to run the game

### Requirements

1. Download a pinned Freedoom release.
2. Verify the SHA256.
3. Place the IWAD under `third_party/freedoom/`.
4. Document that Freedoom is the legal asset path.
5. Build Chocolate Doom using MSYS2 on Windows.
6. Run Chocolate Doom with the downloaded Freedoom IWAD.
7. Record the exact run command.

### Codex prompt

```text
Read plan.md and implement Phase 1 only.

Create a reproducible Windows setup path for the legal IWAD assets and the compiled reference engine.

Use Freedoom as the asset source. Do not use or mention commercial DOOM WADs except to say they are not required and must not be committed.

Add:
- scripts/setup_freedoom.py
- scripts/setup_freedoom.ps1
- docs/build-reference-chocolate-doom.md
- docs/reference-runbook.md

The setup script should download a pinned Freedoom release, verify SHA256, extract the IWADs into third_party/freedoom, and print the exact paths.

The docs should explain how to build Chocolate Doom on Windows with MSYS2 and how to run it against the downloaded Freedoom IWAD.

Do not implement any no-compiler emitter work in this phase.
```

## Phase 2 — Extract calculator lessons into reusable emitter modules

### Goal

Port the useful architecture from `inferenceCompiler` into this repo.

### Deliverables

- `tools/pe32.py`
- `tools/x86.py`
- `tools/emit_pe32.py`
- unit tests for PE headers and basic x86 encoding

### Requirements

1. Create a reusable PE32 writer.
2. Create an x86 helper module.
3. Support:
   - labels
   - abs32 fixups
   - rva32 fixups
   - rel32 fixups
   - import tables
   - one executable/readable/writable section initially
4. Add tests for:
   - MZ header
   - PE signature
   - machine type `0x014c`
   - GUI subsystem
   - import directory RVA
   - simple rel32 fixup
   - simple IAT call pattern

### Codex prompt

```text
Read plan.md and implement Phase 2 only.

Use the existing calculator emitter design as the reference style:
- explicit PE32 writing
- explicit x86 instruction helpers
- labels and fixups
- explicit import table
- no compiler
- no assembler
- no linker
- no general-purpose linker abstraction

Create reusable modules:
- tools/pe32.py
- tools/x86.py
- tools/emit_pe32.py

Add tests:
- tests/test_pe32_headers.py
- tests/test_x86_encoding.py
- tests/test_emitted_imports.py

Keep the implementation small and specific. It only needs enough functionality for later phases.
```

## Phase 3 — Emit a minimal Win32 window executable

### Goal

Produce a directly emitted Windows GUI executable that opens a window.

### Deliverables

- `tools/emit_stage01_window.py`
- `build/stage01_window.exe`

### Requirements

1. Emit PE32 x86 directly.
2. Import only required Win32 APIs.
3. Create a standard overlapped window.
4. Register a window class.
5. Run a message loop.
6. Exit cleanly on close.
7. Smoke test:
   - launch executable
   - confirm process starts
   - confirm window title exists
   - close process cleanly

### Codex prompt

```text
Read plan.md and implement Phase 3 only.

Create tools/emit_stage01_window.py.

It must use the PE32 and x86 emitter modules from Phase 2 to write build/stage01_window.exe directly.

The executable should:
- be PE32 x86
- be a Windows GUI subsystem executable
- register a Win32 window class
- create a visible window
- run a GetMessageW / TranslateMessage / DispatchMessageW loop
- handle WM_DESTROY with PostQuitMessage
- exit cleanly

Do not use a compiler, assembler, linker, CMake, MSBuild, Visual Studio, MinGW, NASM, or external binary tools.

Add or update smoke test documentation.
```

## Phase 4 — Emit a framebuffer window

### Goal

Create the rendering substrate needed for DOOM.

### Deliverables

- `tools/emit_stage02_framebuffer.py`
- `build/stage02_framebuffer.exe`

### Requirements

1. Open a Win32 window.
2. Allocate or define a 320x200 8-bit or 32-bit framebuffer.
3. Draw a changing test pattern.
4. Blit it to the window using a simple Win32 path.
5. Handle paint messages.
6. Handle timer or loop-based redraw.
7. Smoke test should detect that the process remains alive and the window exists.

### Preferred rendering API

Use the simplest GDI path first:

- `CreateDIBSection`, or
- `StretchDIBits`

Avoid DirectDraw, Direct3D, OpenGL, SDL, or Vulkan at this stage.

### Codex prompt

```text
Read plan.md and implement Phase 4 only.

Create tools/emit_stage02_framebuffer.py.

The emitted executable should open a Win32 window and display a 320x200 framebuffer scaled to a larger client area.

Use a simple GDI path such as StretchDIBits or CreateDIBSection.

Render a visible generated test pattern so we know pixels are under our control.

Do not use SDL, Direct3D, OpenGL, Vulkan, a compiler, assembler, linker, or external libraries.
```

## Phase 5 — Add keyboard input

### Goal

Prove the emitted executable can respond to player-style input.

### Deliverables

- `tools/emit_stage02_framebuffer.py` updated, or
- `tools/emit_stage03_input.py`

### Requirements

1. Handle keyboard messages.
2. Track key state for:
   - forward
   - backward
   - turn left
   - turn right
   - strafe left
   - strafe right
   - escape
3. Update the framebuffer based on key state.
4. Add a simple on-screen visual proof, such as a moving square or changing gradient.

### Codex prompt

```text
Read plan.md and implement Phase 5 only.

Add keyboard input to the emitted framebuffer executable.

The binary should respond to arrow keys or WASD and visibly change the framebuffer.

Keep the implementation explicit and small.

Do not start WAD parsing or DOOM rendering yet.
```

## Phase 6 — Build a Python WAD parser

### Goal

Understand Freedoom IWAD files from Python before emitting any WAD logic into x86.

### Deliverables

- `tools/wad.py`
- `tests/test_wad_parser.py`
- `docs/wad-format-notes.md`

### Requirements

1. Parse WAD header.
2. Parse directory.
3. List lump names, offsets and sizes.
4. Find common lumps:
   - `PLAYPAL`
   - `COLORMAP`
   - `TITLEPIC` or equivalent
   - `E1M1` or `MAP01`
   - `THINGS`
   - `LINEDEFS`
   - `SIDEDEFS`
   - `VERTEXES`
   - `SECTORS`
   - `SEGS`
   - `SSECTORS`
   - `NODES`
5. Add CLI command:

```powershell
python tools/wad.py third_party/freedoom/freedoom2.wad --summary
```

### Codex prompt

```text
Read plan.md and implement Phase 6 only.

Create a pure Python WAD parser in tools/wad.py.

It should parse the WAD header and directory, list lumps, and locate important DOOM map lumps.

Add tests using a tiny synthetic WAD generated inside the test, so tests do not depend on downloading Freedoom.

Add docs/wad-format-notes.md explaining the WAD structures we need.

Do not emit any x86 WAD parser yet.
```

## Phase 7 — Emit a WAD probe executable

### Goal

The emitted executable should open a WAD file and prove it can parse the header/directory.

### Deliverables

- `tools/emit_stage03_wad_probe.py`
- `build/stage03_wad_probe.exe`

### Requirements

1. Import file APIs:
   - `CreateFileW`
   - `ReadFile`
   - `SetFilePointer` or equivalent
   - `CloseHandle`
2. Read WAD header.
3. Validate `IWAD` or `PWAD`.
4. Read number of lumps and directory offset.
5. Display a simple status in the window:
   - `WAD OK`
   - lump count
   - failure reason
6. Accept a fixed relative path first:
   - `third_party\freedoom\freedoom2.wad`

### Codex prompt

```text
Read plan.md and implement Phase 7 only.

Create tools/emit_stage03_wad_probe.py.

The emitted PE32 executable should open a pinned Freedoom IWAD from third_party/freedoom, read the WAD header, validate it, read the lump count and directory offset, and display the result in a Win32 window.

Keep the parser tiny. Only parse enough to prove the emitted executable can read the WAD.

Do not implement map loading or rendering yet.
```

## Phase 8 — Display a WAD graphic or palette-derived output

### Goal

Render something from the real WAD.

### Deliverables

- `tools/emit_stage04_picture_viewer.py`
- `build/stage04_picture_viewer.exe`

### Requirements

1. Load `PLAYPAL`.
2. Load a simple picture lump if feasible.
3. Convert palette-indexed pixels to 32-bit framebuffer.
4. Display the graphic in the emitted framebuffer window.
5. If picture format proves too much for one phase, display the palette as coloured bars first.

### Codex prompt

```text
Read plan.md and implement Phase 8 only.

Create tools/emit_stage04_picture_viewer.py.

The emitted executable should read real data from the Freedoom IWAD and display it.

Preferred target:
- read PLAYPAL
- read a simple picture lump
- convert indexed pixels to the framebuffer

Fallback target:
- read PLAYPAL and display the palette as coloured bars

Keep this phase focused on WAD data to pixels. Do not implement map loading yet.
```

## Phase 9 — Python map loader first

### Goal

Load a DOOM map in Python and understand the data before emitting it.

### Deliverables

- `tools/map_loader.py`
- `tests/test_map_loader.py`
- `docs/map-format-notes.md`

### Requirements

1. Use `tools/wad.py`.
2. Load a map marker:
   - `E1M1`, or
   - `MAP01`
3. Parse:
   - vertices
   - linedefs
   - sidedefs
   - sectors
   - things
4. Print a useful summary.
5. Optionally output a simple SVG or text dump of the map.

### Codex prompt

```text
Read plan.md and implement Phase 9 only.

Create a Python-side map loader before emitting any map logic into x86.

It should load a Freedoom map, parse the core map lumps, and print a useful summary.

Add tests using synthetic binary lump data.

Do not change any PE emitter code in this phase.
```

## Phase 10 — Emitted top-down map viewer

### Goal

The emitted executable draws a simple top-down view of a real map.

### Deliverables

- `tools/emit_stage05_map_probe.py`
- `build/stage05_map_probe.exe`

### Requirements

1. Read map vertices and linedefs from the IWAD.
2. Transform map coordinates into screen coordinates.
3. Draw lines into the framebuffer.
4. Show player start if available.
5. No BSP, no wall textures, no monsters.

### Codex prompt

```text
Read plan.md and implement Phase 10 only.

Create tools/emit_stage05_map_probe.py.

The emitted executable should load a Freedoom map from the IWAD and draw a top-down wireframe view into the framebuffer.

Only parse enough WAD/map data to draw vertices and linedefs.

Do not implement first-person rendering yet.
```

## Phase 11 — Tiny first-person renderer

### Goal

Create a DOOM-like visual milestone without full DOOM correctness.

### Deliverables

- `tools/emit_stage06_raycast_view.py`
- `build/stage06_raycast_view.exe`

### Requirements

1. Use simple wall data.
2. Render vertical columns.
3. Support player movement and turning.
4. Use solid colours first.
5. Use fixed-point arithmetic if practical.
6. Avoid full BSP initially.

### Codex prompt

```text
Read plan.md and implement Phase 11 only.

Create a tiny emitted first-person renderer.

It does not need to load a real DOOM map yet.

Use a small hardcoded map or wall list, render vertical wall columns, and allow the player to move and turn.

This is a rendering milestone, not a WAD milestone.
```

## Phase 12 — Real map first-person rendering

### Goal

Use real map data with the first-person renderer.

### Deliverables

- `tools/emit_stage07_real_map_view.py`
- `build/stage07_real_map_view.exe`

### Requirements

1. Load vertices and linedefs.
2. Use the player start from things.
3. Render a simplified first-person view.
4. Collision can be crude.
5. Use solid-colour walls first.
6. No sprites.
7. No monsters.
8. No sound.

### Codex prompt

```text
Read plan.md and implement Phase 12 only.

Connect the emitted first-person renderer to real map data loaded from the Freedoom IWAD.

Use simplified geometry. Solid-colour walls are acceptable.

The milestone is: launch emitted EXE, load a real map, walk around a recognizable first-person level shape.

Do not implement sprites, enemies, weapons, sound, menus, or save games.
```

## Phase 13 — Texture columns

### Goal

Start looking like DOOM.

### Deliverables

- textured wall columns
- palette lookup
- simple texture cache or generated texture buffers

### Requirements

1. Load relevant texture metadata.
2. Load patches as needed.
3. Compose or approximate wall textures.
4. Render texture columns.
5. Keep fallback solid-colour mode for debugging.

### Codex prompt

```text
Read plan.md and implement Phase 13 only.

Add simple wall texture support to the emitted real-map renderer.

Start with the smallest viable subset:
- identify wall texture names from sidedefs
- locate texture data or use a generated placeholder mapping
- render textured columns where possible
- retain solid-colour fallback

Do not implement sprites, enemies, sound, menus, or full DOOM gameplay yet.
```

## Phase 14 — Toward a playable minimal DOOM loop

### Goal

Add the minimum game-loop features needed to feel like DOOM.

### Candidate features

- player spawn
- keyboard movement
- collision
- doors or sector height blocking
- weapon sprite placeholder
- simple status bar placeholder
- simple enemy placeholder
- basic hitscan or projectile
- map exit detection

### Codex prompt

```text
Read plan.md and implement Phase 14 only.

Add one minimal gameplay feature to the emitted DOOM-like executable.

Pick the smallest useful feature from the phase checklist and implement it fully with a smoke test.

Do not attempt to implement all gameplay features in one pass.
```

## 8. Experimental branch: compiled-code extraction

This is a separate optional branch.

It may be useful, but it is philosophically weaker than true hand/codegen emission.

### Idea

1. Build Chocolate Doom normally once.
2. Inspect the generated binary or object files.
3. Extract code/data sections.
4. Teach Python to emit a new PE around known machine-code blobs.
5. Gradually replace compiler-produced blobs with emitter-generated routines.

### Pros

- Faster route to a “Python emitted DOOM binary”.
- Good for learning PE loading, imports, relocations and section layout.
- Good intermediate victory.

### Cons

- Less pure.
- Risks becoming a crude linker.
- Does not really prove the engine was built by inference/codegen.
- Requires careful licensing and provenance notes.
- May depend on compiler output captured earlier.

### Rule

Do not mix this into the mainline unless explicitly requested.

If used, keep it under:

```text
experiments/compiled_blob_reemitter/
```

## 9. Definition of done by milestone

### Milestone A — Reference DOOM works

- Freedoom downloaded legally.
- Chocolate Doom compiled on Windows.
- Reference engine runs with Freedoom.
- Run command documented.

### Milestone B — Emitted Win32 substrate works

- Python emits PE32 x86.
- EXE opens a window.
- EXE draws pixels.
- EXE reads keyboard input.

### Milestone C — Emitted WAD access works

- EXE opens Freedoom IWAD.
- EXE parses WAD header.
- EXE finds lumps.
- EXE displays WAD-derived data.

### Milestone D — Emitted map access works

- EXE loads real map lumps.
- EXE draws top-down map.
- EXE identifies player start.

### Milestone E — Emitted first-person renderer works

- EXE shows a first-person view.
- Player can move.
- Real map geometry is recognizable.

### Milestone F — DOOM-like executable

- Textured walls.
- Basic collision.
- Basic player loop.
- A real Freedoom level can be explored.

### Milestone G — “Actually DOOM enough”

- Menu or autostart.
- Weapons or weapon placeholder.
- Things/sprites.
- Basic enemies or pickups.
- Level exit.
- Repeatable demo/smoke test.

## 10. Debugging rules for Codex

When something fails:

1. Do not rewrite the whole emitter.
2. Add a tiny validation script.
3. Dump key RVAs and file offsets.
4. Validate PE header fields.
5. Validate import descriptors.
6. Validate IAT addresses.
7. Validate section sizes and alignments.
8. Add a minimal failing test.
9. Fix one bug.
10. Re-run the smallest possible smoke test.

Generated binaries are hard to debug.

Prefer many tiny executables over one giant executable.

## 11. Coding style rules

1. Keep emitted instruction helpers readable.
2. Comment raw opcodes.
3. Use named labels.
4. Use named constants for Win32 values.
5. Keep WAD parsing logic separate from PE emission where possible.
6. Keep generated data tables deterministic.
7. Keep each stage executable buildable independently.
8. Never silently ignore failed Win32 API calls.
9. Add visible failure output where possible.
10. Keep a “known-good” previous stage.

## 12. Suggested first Codex command

Use this after creating the repo and saving this file as `plan.md`:

```text
Read plan.md carefully. Implement Phase 1 only.

Do not implement later phases.

At the end, update README.md with:
- what Phase 1 does
- how to download Freedoom
- how to build the reference Chocolate Doom binary on Windows
- how to run the reference engine with the downloaded Freedoom IWAD
- what the next phase is

Keep all assets legal and do not commit any commercial WADs.
```

## 13. Big-picture recommendation

Do this as a visible ladder of wins.

Do not chase “full DOOM” first.

The best sequence is:

1. Reference DOOM runs.
2. Emitted window.
3. Emitted framebuffer.
4. Emitted input.
5. Python WAD parser.
6. Emitted WAD probe.
7. Emitted palette/picture viewer.
8. Python map loader.
9. Emitted top-down map.
10. Emitted first-person renderer.
11. Real map first-person renderer.
12. Textures.
13. Gameplay loop.

That gives you many impressive checkpoints and avoids the project dying under the weight of “compile all of DOOM without a compiler”.
