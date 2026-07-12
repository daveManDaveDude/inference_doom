# Inference Doom: Project Review and Recovery Plan

## Verdict

Yes, the core idea is technically possible. Python can emit every byte of a
native PE32 executable, and this repository proves that.

But the current process is not converging reliably toward playable Doom. Stop
before stage 49 and pivot the architecture and measurement system.

The honest constraint should be:

> No external compiler, assembler, linker, or compiler-produced code blobs in
> the emitted path.

The Python emitter is functionally a specialized compiler or code generator,
even if it does not translate C mechanically.

## What Has Genuinely Been Achieved

This is not a failed project. It contains substantial real engineering:

- A working PE32 writer with labels, imports, fixups, resources, and executable
  generation.
- Direct native x86 instruction emission.
- Real Win32 window, input, timer, framebuffer, and GDI presentation.
- Runtime WAD and map access.
- Real emitted drawing loops and some genuine emitted movement and state
  mutation.
- Strong source tracing and a large regression suite.

A clean, single-process test run produced:

```text
Ran 501 tests in 331.906s
OK
```

Stage 48 alone passed all 10 tests. The artifacts are real and runnable.

## Why Progress Keeps Receding

The historical estimates expose a moving horizon:

| Baseline completed | Forecast at the time | Claimed distance |
| --- | ---: | ---: |
| Stage 25 | Stage 35 | 10 stages |
| Stage 36 | Stage 45 | 9 stages |
| Stage 41 | Stage 51/52 | 10-11 stages |
| Stage 47 | Stage 57/58 | 10-11 stages |

Twenty-two additional stages were completed, but playability stayed
approximately ten stages away. Stage count is therefore not measuring
remaining work.

The living plan itself estimates only 24-29% of the eventual loop as reusable
runtime-owned x86 and still lists continuous rendering, multiple actors,
progression, UI, persistence, and audio as missing.

### The Central Technical Problem

The latest executable is a hybrid of real emitted computation and precomputed
transcripts:

| Capability | What stage 48 does | What playability requires |
| --- | --- | --- |
| Collision | Matches requested coordinates against the next Python-generated record, then copies its result | Compute collision from current geometry for arbitrary coordinates |
| Awareness | Loads precomputed sight, distance, front-arc, and acquisition results | Runtime sight and awareness for arbitrary actors and positions |
| Rendering | Always selects one earlier finite render sample and overlays markers | Generate walls, planes, and sprites from the current camera |
| Validation | Copies expected signatures into runtime signature fields | Independently observe values computed by the executable |
| Architecture | Reassembles a long chain of prior stage loaders, data, renderers, and status markers | One modular runtime whose old experiments are tests, not dependencies |

That means the tests strongly prove:

> The executable reproduces the planned bounded transcript.

They do not yet prove:

> The executable behaves correctly for unseen game states and inputs.

That distinction explains nearly all the apparent lack of progress.

This is not dishonesty. The documentation is unusually candid about the
bounded shortcuts. But the definition of "stage complete" rewards another
visible proof, even when it does not generalize.

## Is It Salvageable?

Absolutely, as three related projects:

1. A valuable legacy corpus of inference-emitted PE/x86 experiments.
2. An engineering effort toward a narrow playable Freedoom vertical slice.
3. A future-model benchmark.

It is not currently:

- A Doom-source translator.
- A cold one-shot benchmark.
- Close enough to justify another 9-14 stage estimate.

The current builder does not accept the Doom source tree as input. The model
reads the source during development and writes bespoke emitter code. That is a
good warm engineering benchmark, but different from "source in, binary out."

There are also three competing baselines:

- The README says stage 41 is current.
- GitHub `main` contains stage 47.
- The working tree contains uncommitted stage 48 work.

Preserve stage 48 before restructuring anything.

## Replacement Process

Use fixed capability gates instead of incrementing stages.

Every capability should have exactly one status:

```text
NOT_STARTED
PYTHON_REFERENCE
EMITTED_SELECTED
EMITTED_GENERAL
INTEGRATED
DIFFERENTIAL_PASS
```

Only `INTEGRATED` and `DIFFERENTIAL_PASS` count toward playability.

Use this preamble for every Codex task:

```text
Work only on the named capability gate.

Treat all existing emit_source_stageNN files as legacy experiments and read-only
fixtures. New production runtime code must not import them.

The emitted path may use Python byte writers but may not invoke an external
compiler, assembler, linker, or compiler-produced code blob. A normally compiled
Chocolate Doom reference is allowed only as an independent test oracle.

Build-time data may contain immutable source-derived tables such as trig tables,
states[], mobjinfo[], and sprite metadata. It must not contain input-specific
collision outcomes, sight decisions, per-tic state snapshots, render keyframes,
precomputed draw commands, expected framebuffer hashes, or success signatures.

Tests must include cases selected after the executable is built and must compare
against an independent oracle. Update the capability ledger after the task.
Do not claim completion unless the stated exit gate passes. Record a failed
attempt under the same gate rather than creating a new stage.
```

## Codex Tasks, in Order

### Task 0: Freeze the Contract

> Preserve the current committed stage47 and uncommitted stage48 work. Do not
> stage, commit, delete, or rewrite those files. Create
> `docs/recovery/playable-contract.md`,
> `docs/recovery/capability-ledger.md`, and
> `docs/recovery/benchmark-contract.md`. Define playability as: one Python
> command emits a PE32 executable; runtime `-iwad` path; direct MAP01 start;
> live move/turn/strafe/use/fire; arbitrary runtime collision; continuous
> first-person rendering; multiple enemies; damage/death/drop/pickup; required
> door/switch/exit; deterministic replay to completion. Explicitly exclude
> audio, menus, automap, save/load, networking, and broad compatibility.
> Classify every current capability using the six controlled statuses, with
> evidence links. Do not add gameplay.

After reviewing this result, checkpoint stage 48 separately and tag the old
trajectory as a legacy proof baseline.

### Task 1: Make Validation Reproducible

> Isolate the test harness. Give tests unique temporary executable paths or
> explicitly serialize GUI tests. Split a fast pure-unit gate from Windows GUI
> integration tests. Add a clean-checkout verification command, pinned
> source/WAD hashes, and an emitted artifact hash. Required tests must not
> silently skip when the WAD or reference source is absent. Demonstrate a clean
> full-suite pass and prove concurrent runs cannot corrupt one another. Do not
> change gameplay behavior.

Prospectively stop tracking generated `.pyc`, WAD, and executable duplicates,
but do not rewrite Git history without a separate decision.

### Task 2: Build an Independent Oracle

> Define a fixed binary replay format and per-tic trace format. Create a
> reproducible patch against pinned Chocolate Doom that consumes a deterministic
> command stream and emits player position, angle, momentum, subsector,
> health/ammo, actor states/targets, sector state, events, and internal 320x200
> framebuffer hashes. Build a comparator independent of the emitter modules.
> Prove identical reference runs are deterministic, then deliberately mutate one
> expected value and prove comparison fails. The compiled reference may use its
> normal toolchain; the emitted path may not.

### Task 3: Start a Stage-Neutral Runtime

> Create one new production runtime that imports `pe32.py`, `x86.py`, and newly
> extracted stage-neutral modules only. It must not import any
> `emit_source_stageNN` module or embed prior success titles. Add a documented
> calling convention and symbol-map output. Emit one executable accepting
> `-iwad`, `-map`, `-replay`, and `-trace`. Load the IWAD and allocate map
> storage at runtime, using bounded runtime allocation such as `VirtualAlloc` if
> helpful. The same executable must load MAP01 and MAP02 without regeneration
> and report independently verified lump/map counts.

Do not spend months redesigning PE sections or relocations yet; those are
secondary until the walk kernel works.

### Task 4: General Runtime Collision

> Implement runtime blockmap loading, block line/thing iteration,
> `P_CheckPosition`, `P_TryMove`, relinking, floor/ceiling updates, slide
> movement, and player XY/Z movement in the stage-neutral runtime. Remove all
> collision outcome tables. Build the executable first, then generate at least
> 1,000 held-out replay tics across MAP01 and MAP02 containing both accepted and
> rejected moves. Compare position, momentum, sector, subsector, floor, and
> ceiling against the independent reference every tic. Corrupt one collision
> branch and prove the gate fails.

This is the first decisive feasibility gate.

### Task 5: Arbitrary-Camera Wall and Plane Rendering

> Implement runtime `R_SetupFrame`, BSP traversal, bbox rejection, seg clipping,
> projection, wall-column generation, texture lookup/composition, visplanes, and
> spans. Work must be generated from current runtime camera state. Remove finite
> view selection and precomputed wall/span command tables. After building the
> executable, select at least 50 held-out camera poses across two maps and
> compare the internal framebuffer with the independent reference using the
> tolerance defined in the contract. No AI or combat work in this task.

### Task 6: Masked Textures and Sprites

> Extend the arbitrary-camera renderer with masked midtextures, generic
> world-sprite traversal/sorting/drawing, and player psprites. Use runtime actor
> and camera state, not selected actor IDs or pose tables. Validate held-out
> poses containing occlusion, overlapping sprites, and masked geometry against
> the independent framebuffer oracle. The same binary must pass cases chosen
> after emission.

### Task 7: Integrated Walk Kernel

> Connect live keyboard input and replay input to the same player, collision,
> camera, renderer, and presentation path. Demonstrate a 60-second arbitrary
> manual exploration and a deterministic multi-minute replay on MAP01 without
> route-specific tables. Repeat a shorter differential replay on MAP02. Record
> performance and all mismatches. Only after this gate passes, replace the old
> remaining-work forecast with a new estimate based on measured subsystem work.

If Tasks 4-7 cannot pass after three fixed-budget attempts each, stop and choose
explicitly between:

- A direct native emitter.
- A native kernel plus custom bytecode VM.
- A restricted C-to-x86 translator.

Do not respond by adding another bounded proof stage.

### Task 8: Generic Actors and AI

> Add a runtime thinker list, multiple mobjs, generic `P_SetMobjState`, full
> immutable state/mobj metadata, action dispatch, runtime sight, `A_Look`,
> `A_Chase`, chase direction, and actor collision. Validate several monsters
> under held-out player routes. No actor index, route result, or preselected
> target may be required. Compare actor state, position, target, and attack
> decisions to the independent reference per tic.

### Task 9: Combat and Inventory

> Add player weapon/psprite progression, hitscan, missiles, enemy attack,
> damage, pain, death, drops, pickups, health, ammo, and minimal HUD feedback.
> The exit test is a non-precomputed replay that kills at least two independently
> selected enemies, receives damage, collects a drop, and matches the reference
> trace. The same path must be available to live input.

### Task 10: Specials and Level Completion

> Add runtime use-line traversal and only the door, switch, floor/lift, exit,
> death, and restart behavior required by the chosen MAP01 vertical slice. Pass
> an independently authored replay from level start to exit, then complete the
> same path with human input. Do not add audio, menus, saves, or networking.

### Task 11: Stabilize and Package the Benchmark

> Require a clean checkout, pinned setup, one build command, zero required
> skips, recorded artifact hash, ten-minute stability run, unseen input stream,
> and two maps. Create separate benchmark seeds for: cold source-to-binary,
> source plus frozen PE/x86 substrate, and warm continuation from this
> repository. Record the exact seed commit, prompt, model/version/settings,
> token/time budget, tool and network policy, human interventions, artifact
> hash, and gate scores. Keep hidden command streams and camera poses outside
> the solution repository.

## Realistic Estimate

Under the present route-specific method, the work is effectively unbounded. It
could reach hundreds or thousands of stages because each transcript reveals
another special case.

After the pivot, a narrow playable MAP01 slice is more plausibly tens to low
hundreds of focused Codex tasks: roughly 50-150 as an order-of-magnitude
estimate. Full Chocolate Doom-like compatibility is probably hundreds of
tasks.

The first credible time to estimate it is after general collision and
arbitrary-camera rendering pass differential tests. Until then, "ten stages
remaining" has no useful meaning.

A current model one-shotting all of Doom into a correct Windows binary is not
realistic. But this can become an excellent benchmark for future models,
provided hidden inputs and independent observation prevent a deterministic
transcript from scoring as a general implementation.



ME: could we frame this as a translation problem. current models can translate in real time between languages, is this not partly that. Is there a way I can use this approach to move forward even if with a simple hello world example.



Yes—this is a translation problem
Your analogy is sound. Compiling is translation:
C source
   ↓ semantic understanding
typed operations and data
   ↓ target-language translation
x86 instructions
   ↓ packaging
PE executable
It differs from natural-language translation in three important ways:
The output must be exact; one incorrect byte can invalidate everything.
Programming languages have strict operational semantics, not merely equivalent meaning.
The translator must manage calling conventions, memory layout, control flow, imports, and binary addresses.
But these are differences in precision and scale, not a fundamentally different kind of problem.
The important change is to make translation itself the repeated process. Currently each stage translates one selected Doom behaviour into a bespoke emitter. You want one stable translation pipeline that can accept different small programs without modifying the pipeline.
Separate semantic translation from mechanical encoding
I recommend this architecture:
Restricted source
   ↓ inference/model
semantic IR
   ↓ deterministic Python backend
x86 + PE32
   ↓ Windows
executable
The model handles the genuinely intelligent part:
Understanding what the source means.
Selecting operations and data.
Preserving control flow.
Producing a typed intermediate representation.
The existing Python backend handles mechanical exactness:
Instruction encoding.
Calling conventions.
Registers and stack layout.
Labels and fixups.
Imports.
PE construction.
That is still inference-driven binary generation. Using a deterministic backend is no more a betrayal of translation than using a tokenizer and renderer in a language-translation system.
It also lets you measure two separate capabilities:
Did the model understand and translate the program?
Did the backend encode that translation correctly?
The Hello World experiment
Start with a tiny restricted source language—initially a microscopic subset of C:
int main(void)
{
    message_box("Hello, world!", "Inference");
    return 0;
}
The model should translate that into semantic IR such as:
{
  "entry": "main",
  "functions": [
    {
      "name": "main",
      "body": [
        {
          "op": "call",
          "function": "MessageBoxA",
          "args": [
            {"type": "u32", "value": 0},
            {"type": "string", "value": "Hello, world!"},
            {"type": "string", "value": "Inference"},
            {"type": "u32", "value": 0}
          ]
        },
        {"op": "return", "value": 0}
      ]
    }
  ]
}
A fixed Python backend then translates that IR into:
USER32.dll!MessageBoxA
KERNEL32.dll!ExitProcess
PE32 imports
strings
x86 calls
an entry point
The critical test is not whether one Hello World works. It is whether the unchanged translator and backend handle hidden variations:
message_box("Different text", "Different title");
return 17;
int x = 7 + 5;
return x;
if (x > 10)
    message_box("large", "result");
else
    message_box("small", "result");
If every variation requires editing the emitter, it remains bespoke generation. If new source passes through the same pipeline, you have begun building a translator.
A sensible translation ladder
Advance only when hidden programs pass without modifying the translator:
String literals, function calls, and integer returns.
Integer arithmetic and local variables.
Comparisons and if/else.
Loops.
Arrays, pointers, and memory loads/stores.
Struct layouts.
Multiple functions and calls.
Multiple source modules and globals.
File access and a small WAD-header reader.
A translated map parser.
Fixed-point movement or rendering functions.
Larger Doom modules.
This creates an honest benchmark at every level. A model might score:
Level 1: calls and literals
Level 2: expressions
Level 3: control flow
Level 6: structures
Level 9: real file parsing
Level 12: substantial Doom translation
That is much more informative than “stage 48 but still ten stages from playable.”
Recommended first Codex prompt
Create a new isolated experiment under:

experiments/translation_hello/

Do not modify or import any emit_source_stageNN module.

The experiment is a restricted-source-to-PE32 translation pipeline.

Create:

- experiments/translation_hello/README.md
- experiments/translation_hello/source/hello.tc
- experiments/translation_hello/schema/program-ir.schema.json
- experiments/translation_hello/translate_source.py
- experiments/translation_hello/emit_ir_pe32.py
- experiments/translation_hello/tests/

The restricted source language initially supports only:

- int main(void)
- message_box(string message, string title)
- return <integer literal>

translate_source.py must parse source text and produce semantic JSON IR.
It must not emit x86 or contain program-specific strings.

emit_ir_pe32.py must consume only the JSON IR and use the existing pe32.py and
x86.py helpers to emit a runnable PE32 executable. It must not read the source
file.

Add tests using several source programs with different message text, titles,
and return values. At least one test program must be generated after the backend
is initialized so that hard-coded Hello World output cannot pass.

The same translator and backend must process every test without source-specific
changes.

Document clearly:

source -> semantic IR -> x86/PE32 -> executable

Do not add arithmetic, variables, branches, loops, Doom code, or a general C
parser in this task.
This is the direction I would pursue alongside the frozen Doom work. It turns the project into a measurable translation ladder while preserving the wonderfully strange original goal.