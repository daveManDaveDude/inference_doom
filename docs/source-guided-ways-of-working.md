# Source-Guided Ways Of Working

This is the quick-reference working agreement for each clean context. The goal
is a real Doom executable emitted by inference-guided Python byte writers:
Python may plan, parse source/reference data, and write PE32 x86 bytes, but the
emitted path must not use compiled code.

## North Star

Build Doom one source-bounded slice at a time. Each slice must end with a
runnable `.exe` that proves the intended behavior on the pinned IWAD.

## Non-Negotiable Rules

1. Do not use a compiler, assembler, linker, CMake, MSBuild, MinGW, NASM, or
   compiler-produced code blobs in the emitted executable path.
2. Python may emit bytes, build PE32 structures, parse WAD/source data for
   tests, and generate deterministic lookup tables or assets.
3. Read the relevant Chocolate Doom source before emitting a routine.
4. Every emitted routine must have a source trace entry with source file,
   source function, emitted label, status, and validation target.
5. Prefer source-faithful runtime data layouts before source-faithful control
   flow. A stable layout gives later slices somewhere real to land.
6. Each step must finish with a releasable executable feature, not just a
   library refactor.
7. Always build, run, and smoke-test the emitted binary before calling a step
   done.
8. Keep old prototype stages as references and tests. Do not grow the new
   source-guided line by adding more stage07 special cases.
9. Consolidate x86 helpers into `tools/x86.py` only when the current slice
   actually needs them.
10. If a shortcut is taken, make it explicit in the trace manifest and keep the
    next correction small.

## Definition Of Done

A slice is done only when all of these are true:

- The output executable exists under `build/` with the planned name.
- The executable launches on Windows and visibly reports or demonstrates the
  intended feature.
- A scripted smoke test runs the executable and checks the visible success
  signal, usually the window title or deterministic on-screen text.
- Unit tests cover new data layout constants, generated tables, and parser
  assumptions using synthetic records where possible.
- `python -B -m unittest discover -s tests` passes.
- The source trace manifest is updated.
- The docs say how to manually or script-smoke the executable.

## Clean Context Kickoff

At the start of each fresh context:

1. Read this file.
2. Read `docs/source-guided-emission-plan.md`.
3. Read `docs/source-trace-manifest.md`.
4. Run `git status --short` and preserve unrelated user changes.
5. Identify the next releasable slice and its output `.exe`.
6. Read only the relevant Chocolate Doom source routines for that slice.
7. Build the executable, run it, and test it before final response.

## Slice Shape

Each slice should fit this template:

```text
Name:
Output exe:
Source routines:
User-visible feature:
Runtime data added:
Tests:
Smoke success signal:
Done when:
```

## Planning Style

Plan the next one or two slices in detail. Keep later work as a thin backlog.
After each release, re-plan from what the binary actually proves. This keeps
the project agile: the next step is specific, the long-term direction is clear,
and distant implementation details stay flexible.

## Testing Standard

Every release should have three layers:

- Unit tests for constants, byte encoders, source-layout assumptions, and
  synthetic WAD/map records.
- Build tests that call the Python emitter and inspect the PE for expected
  strings/data when useful.
- A Windows smoke test that launches the emitted `.exe`, waits for the expected
  title/text/visual signal, and closes the process cleanly.

Manual visual checks are allowed as extra confidence, but they do not replace
the scripted smoke test.
