# inference_doom

No-compiler Windows Doom executable experiments.

The end goal is deliberately strange and hard: build Doom from source behavior
without using a compiler, assembler, linker, CMake, MSBuild, MinGW, NASM, or
compiled code blobs. Python reads source/WAD data and emits PE32 x86 bytes
directly. Every source-guided slice must end with a runnable executable and a
scripted smoke test.

## Current Progress

The current released baseline is:

```text
source_stage41_statusbar_weapon_ammo_feedback_bridge
build/source_stage41_statusbar_weapon_ammo_feedback_bridge.exe
```

Stage41 is still a selected proof, not a playable game. It does, however,
carry a lot of real Doom-shaped behavior:

- Real WAD-backed wall/flat rendering from the stage31 runtime redraw bridge.
- Selected shotgun psprite posts from real WAD patch data.
- Selected impact, pain, death, dropped shotgun, pickup, enemy attack, and
  projectile state proofs preserved from stages 32-40.
- A bounded selected world-vissprite route:
  `R_AddSprites -> R_ProjectSprite -> R_SortVisSprites -> R_DrawMasked`.
- A compact runtime status strip showing source-owned player feedback:
  health, armor, shell ammo, shotgun ownership, pending weapon, `GOTSHOTGUN`,
  `bonuscount`, `damagecount`, flash markers, and deferred sound markers for
  `sfx_wpnup`, `sfx_shotgn`, and `sfx_firsht`.

Latest pinned stage41 signals:

```text
S41SIG=951695045
STATE41=157977072
FB41=2820600565,3443819349,1672331767
SSTATE41=1548266261,4244284538,3218471217
```

## Run The Latest Slice

From the repository root:

```powershell
py -3 -B .\tools\emit_source_stage41_statusbar_weapon_ammo_feedback_bridge.py
.\build\source_stage41_statusbar_weapon_ammo_feedback_bridge.exe
```

Run the focused stage41 tests:

```powershell
py -3 -B -m unittest tests.test_source_stage41_statusbar_weapon_ammo_feedback_bridge -q
```

Full discovery is still useful, but local Windows AV may block older emitted
smoke binaries. The stage41 work records that precisely when it happens.

## Next

The next planned slice is:

```text
source_stage42_unified_live_tick_render_loop_probe
build/source_stage42_unified_live_tick_render_loop_probe.exe
```

Stage42 should merge the currently separate selected proofs into one bounded
timer-driven source-shaped replay loop:

```text
tic -> selected state update -> render -> compact status feedback -> signature -> present
```

This is not a full game loop yet. It is the bridge that should make selected
player movement, weapon/pickup/damage/projectile state, world-vissprite
rendering, psprites, status feedback, framebuffer signatures, and Win32 present
advance under one emitted runtime controller.

## Demo Estimate

The current roadmap places a playable shareware-style vertical slice around
`source_stage51` or `source_stage52`.

That means roughly **10-11 more releasable stages** from the stage41 baseline.
A realistic range is **8-13 more stages**: fewer if the unified loop absorbs
more existing selected proofs than expected, more if projectile collision,
broad sprite traversal, live input, UI shells, or audio integration expose
another strict source-order boundary that deserves its own runnable proof.

See [docs/source-guided-emission-plan.md](docs/source-guided-emission-plan.md)
for the living plan.
