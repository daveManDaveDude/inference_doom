# inference_doom

No-compiler Windows DOOM executable experiments.

## Current status

This repository now has a working PE32/x86 emitter substrate plus several
experimental emitted executables. The latest experiment is
`tools/emit_stage07_real_map_view.py`, which writes a Win32 PE32 executable
directly from Python and renders a first-person view from real WAD map data.

```powershell
py -3 .\tools\emit_stage07_real_map_view.py
.\build\stage07_real_map_view.exe
```

The project is now pivoting from "DOOM-like experiments" toward
source-guided emission: read the Doom/Chocolate Doom source as the behavioral
specification, then write Python emitters that generate the machine code
directly, without a compiler, assembler, linker, or compiled code blobs.

See `docs/source-guided-emission-plan.md` for the next phase.
