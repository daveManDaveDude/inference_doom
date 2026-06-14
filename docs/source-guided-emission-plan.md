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

This plan is intentionally agile. The end goal stays fixed: build Doom from
source behavior without a compiler. The exact next slice may be refined after
each release when the source, pinned WAD data, or emitted runtime proves that a
smaller or differently ordered step would be more honest.

## Rules

1. Do not use a compiler, assembler, linker, CMake, MSBuild, MinGW, NASM, or
   compiler-produced code blobs in the emitted path.
2. Do not translate all of Doom at once.
3. Each emitted routine should have a source trace entry: source file, source
   function, intended emitted function label, and validation notes.
4. Prefer source-faithful data layouts before source-faithful control flow.
5. Keep the released debug stages as proofs, but do not build the next phase by
   piling more special cases into them.

## Current Baseline: source_stage36_selected_dropped_shotgun_pickup_feedback_boundary

The source-guided line now covers WAD/map setup, BSP setup structures,
source-ordered BSP traversal, Doom-shaped bbox/frustum visibility, and live
emitted x86 mutable wall-span clipping for the pinned `MAP01` player start.
It turns the accepted live wall spans into source-shaped projection records
using Doom fixed-point distance and scale math, connects those projected spans
to real Doom texture and flat metadata, draws real WAD wall texture pixels
from direct columns, source-shaped composite columns, and supported two-sided
upper/lower wall edges, and now draws regular floor/ceiling flat spans from
real 64x64 WAD flat lumps.

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

Stage11 consumes those plane-mark records through bounded padded
`visplane_t`-shaped records, runs source-shaped `R_FindPlane`,
`R_CheckPlane`, `R_MakeSpans`, and `R_MapPlane` references for the fixed view,
then emits span commands and real flat lump bytes for an emitted x86
`R_DrawSpan` loop.

Stage12 preserves that primary player-start wall/flat view and adds the first
sky and masked-midtexture proof. Because the primary pinned view has no visible
sky or masked midtexture columns, Stage12 freezes a deterministic secondary
MAP01 feature probe selected from real geometry: sky sector `2` and masked
sidedef `617` at `PVX=1771 PVY=-773 PVA=277 PSEC=196`. It draws `SKY1` sky
columns through the `R_DrawPlanes` sky branch, then draws `AQMETL29` masked
midtexture posts after walls/flats through the shared masked-column primitive.

Stage13 keeps the released stage12 renderer intact, decodes real `MAP01`
`THINGS`, creates minimal render-facing `mobj_t` / `player_t` records, seeds
the fixed frame from the real player-one start at `(-192, -192)`, initializes
reachable sprite metadata from `info.c` and WAD sprite lumps, gathers bounded
vissprites through the primary `R_Subsector -> R_AddSprites(frontsector)`
sector set, sorts them, and draws real sprite patch posts after the stage12
path through the shared masked-column primitive. The primary frame naturally
contains sprite proof work, so no secondary sprite probe is needed.

Stage14 preserves the full stage13 renderer as a no-script baseline, loads the
real `MAP01` `BLOCKMAP`, links the player and inert solid things into
source-shaped sector/block lists, runs an eight-tic deterministic `ticcmd_t`
script from the real player start, advances the local player through the
narrowed `G_Ticker -> P_Ticker -> P_PlayerThink -> P_MovePlayer -> P_Thrust ->
P_XYMovement -> P_TryMove/P_CheckPosition` path, and records the final
`R_SetupFrame` fields. The main script proves accepted movement; a separate
bounded MAP01 collision probe proves a blocking line through the real blockmap.

Stage15 preserves stage14 as the movement baseline, then runs a separate fixed
MAP01 pickup proof selected from a source-shaped pickup census. The proof
touches the real shotgun at mapthing `27` and the real clip at mapthing `41`
through `PIT_CheckThing -> P_TouchSpecialThing`, mutates player inventory via
source-shaped grant helpers, raises the shotgun through `P_SetupPsprites` /
`P_MovePsprites`, and draws a compact real-patch status strip plus shotgun
psprite shell.

Stage16 keeps the stage15 pickup/status proof stable and adds the first bounded
active monster thinker. A source-shaped MAP01 monster census selects the real
shotgun guy at mapthing `37` / mobj `28`; the proof links it into a Doom-shaped
thinker list, advances `P_MobjThinker` / `P_SetMobjState` for 13 bounded tics,
dispatches `A_Look`, acquires the player through `P_LookForPlayers` and a
bounded REJECT+BSP `P_CheckSight` probe, and stops when the first `A_Chase`
action is reached as a counted deferred boundary.

Stage17 keeps the stage16 active-monster proof stable and adds the first
bounded player weapon damage proof. The attack census records that the player's
current angle `0` does not hit the selected shotgun guy, freezes the documented
player-to-target attack angle `254` degrees, advances the ready shotgun psprite
to `A_FireShotgun`, spends one shell, and runs the bounded hitscan route until
one pellet mutates the selected monster through `P_DamageMobj`.

Stage18 keeps the stage17 damage proof stable and adds the first bounded
post-damage monster movement proof. A source-shaped census starts from the
actual damaged shotgun guy left by stage17: `S_SPOS_PAIN`, `tics=3`, target
`0`, threshold `100`, and thrust momentum `(-22182,-78859)`. Source order
services `P_XYMovement` before pain recovery, so the released proof performs
one real MAP01 `P_TryMove` momentum step, accepts the move to `(1751,-938)`,
relinks the monster, applies friction, and leaves chase/attack execution
deferred.

Stage19 keeps the stage18 post-damage movement proof stable and adds the first
bounded environment-state mutation. A MAP01 special census selects real manual
door linedef `332`, special `117`, visible `BIGDOOR1`, from a fixed front-side
use probe at `(1792,-160)` facing east. The source-shaped route reaches
`P_UseLines -> P_PathTraverse -> PTR_UseTraverse -> P_UseSpecialLine ->
EV_VerticalDoor`, targets sector `56` through `line->sidenum[side^1]`, computes
`P_FindLowestCeilingSurrounding=112` and `topheight=108`, table-emits one
bounded door thinker record, then runs one `T_VerticalDoor -> T_MovePlane` tic
that mutates the sector ceiling from `16` to `24` map units.

Stage20 keeps the stage19 manual-door proof stable and converts the reached
`EV_VerticalDoor -> S_StartSound(&sec->soundorg, sfx_bdopn)` boundary into
deterministic source-shaped sound-channel state. It parses `sounds.h` /
`sounds.c` metadata for `sfx_bdopn`, computes sector `56`'s centered
`soundorg` from the `P_GroupLines` sector bounding-box rule, applies bounded
`S_AdjustSoundParams`, deterministic `M_Random` pitch variation, `S_StopSound`,
`S_GetChannel`, usefulness/lump bookkeeping, and writes one record in a bounded
8-channel table while keeping platform speaker output deferred.

Stage21 keeps both stage20 and stage19 stable, then clones the selected manual
door's just-created state into an isolated normal ticker proof. It initializes a
bounded `thinkercap`, appends one door thinker node, and runs two source-ordered
`P_Ticker` tics through `P_RunThinkers -> T_VerticalDoor -> T_MovePlane`,
mutating the cloned sector `56` ceiling from `16 -> 24 -> 32`. The ticker also
reports explicit player-think, `P_UpdateSpecials`, `P_RespawnSpecials`, and
`leveltime++` ordering guards while keeping animation, scroller, button, exit,
respawn, and new sound/device work absent or deferred.

Stage22 keeps stage21 stable, then proves the first source-shaped switch
texture mutation and tagged-door activation. A fixed front-side `P_UseLines`
probe at `(216,-584)` facing south reaches real MAP01 linedef `839`, special
`103`, tag `4`, front sidedef `1289`, and lower texture `SW2COMP`. The bounded
route follows `P_UseSpecialLine -> EV_DoDoor(vld_open) ->
P_FindSectorFromLineTag -> P_AddThinker -> P_ChangeSwitchTexture`, mutates
`SW2COMP -> SW1COMP`, clears the one-shot line special, spawns one sector `208`
door thinker with topheight `-4`, and runs one ticker tic from ceiling
`-80 -> -78` while leaving button restore and generalized specials deferred.

Stage23 keeps stage22 stable, then proves the reusable-button half of
`P_ChangeSwitchTexture` on a real secondary-map candidate. The selected proof
uses real `MAP15` linedef `3452`, special `61`, tag `24`, front sidedef `4798`,
and middle texture `SW1COMP`. The bounded route reaches
`P_UseSpecialLine -> EV_DoDoor(vld_open) -> P_ChangeSwitchTexture(line, 1) ->
P_StartButton`, mutates `SW1COMP -> SW2COMP`, preserves the line special,
allocates one button slot with old texture `SW1COMP` and timer `35`, then runs
35 source-ordered ticker/update-special tics until `P_UpdateSpecials` restores
`SW1COMP`, counts the switch-off sound boundary, and clears the slot.

Stage24 keeps stage23 stable, then proves the first source-shaped floor thinker
on real `MAP11` linedef `391`, special `60`, tag `6`, front sidedef `564`, and
middle texture `SW1BROWN`. The bounded route reaches
`P_UseSpecialLine -> EV_DoFloor(lowerFloorToLowest) ->
P_FindSectorFromLineTag -> P_FindLowestFloorSurrounding -> P_AddThinker`,
starts the reusable `SW1BROWN -> SW2BROWN -> SW1BROWN` button lifecycle, and
runs a bounded ticker window through `T_MoveFloor -> T_MovePlane` until target
sector `57` moves from floor `16` to `-48`, fires the strict
past-destination pstop boundary, and lazily unlinks the thinker.

Stage25 keeps stage24 stable, then proves the first source-shaped platform/lift
cycle on real `MAP12` linedef `2304`, special `62`, tag `26`, front sidedef
`3005`, back sidedef `3004`, and lower texture `SW1STRTN`. The bounded route
reaches `P_UseSpecialLine -> EV_DoPlat(downWaitUpStay) ->
P_FindSectorFromLineTag -> P_FindLowestFloorSurrounding -> P_AddThinker ->
P_AddActivePlat`, starts the reusable `SW1STRTN -> SW2STRTN -> SW1STRTN`
button lifecycle, and runs a 136-tic ticker window through
`T_PlatRaise -> T_MovePlane`: sector `77` moves down from `-8` to `-64`, waits
105 platform dispatches, restarts upward, returns to `-8`, clears
`activeplats[]` and sector `specialdata`, marks the thinker for lazy removal,
and proves the final lazy unlink.

The renderer is still a debug renderer. It knows which texture metadata belongs
to visible spans and can draw deterministic wall columns and regular flat
spans, and it now proves sky, masked-wall, real sprite pixel paths, and the
first source-shaped local player movement/collision, inventory/status mutation,
active monster thinker/targeting, first weapon damage, first post-damage
monster movement, manual door sector mutation, first sound-channel state,
normal door ticker, first switch/tagged-door, and first reusable-button timer
restore slices, plus the first selected lowerFloorToLowest floor thinker. It
now also proves one selected `downWaitUpStay` platform/lift cycle with
`activeplats[]`, wait-state transitions, active platform removal, a bounded
scripted room loop, a small live-input-to-`ticcmd_t` bridge, a six-tic selected
shotgun-guy pain/chase/attack-decision state loop, changed framebuffer pixels
after launch, runtime-selected real WAD wall/flat command-table redraws, and
one selected shotgun psprite visual route feeding the same live renderer. It
now carries that route through one selected hitscan impact/pain visual
boundary, one selected shotgun-guy death visual boundary, and the first selected
aftermath drop visual boundary: `P_DamageMobj` reaches `P_KillMobj`, the
selected target enters `S_SPOS_DIE1` / `S_SPOS_DIE2`, the selected
`MT_SHOTGUY -> MT_SHOTGUN` drop is materialized through a bounded
`P_SpawnMobj`-shaped record, marked `MF_DROPPED`, and drawn from real `SHOTA0`
WAD posts in the same runtime wall/flat/impact/death/drop/psprite order, then
the selected dropped shotgun is touched through the bounded
`P_TouchSpecialThing -> P_GiveWeapon(player, wp_shotgun, dropped=true)` route.
The released pickup proof grants one shell clip and shotgun ownership, sets the
pending weapon, reports `GOTSHOTGUN`, `sfx_wpnup`, and `bonuscount`, removes
only the selected dropped item, and omits its posts from the final frame. It
still stops before generalized continuous camera rendering,
generalized combat, generalized monster AI/chase, generalized sprite traversal,
generalized death/drop/item systems, generalized specials, generalized
doors/switches, generalized floor/plat/ceiling families beyond the selected
paths, real audio output, generalized UI, map progression, and a full playable
game loop.

The next milestone should keep the same discipline: port source behavior in a
small runnable slice, not a generic rewrite and not a compiled-code shortcut.
Stage12 taught that a zero-hit primary view can still hide real engine work in
the map data; Stage13 then showed the primary player-start frame does naturally
exercise real sprite projection once `THINGS` are loaded. Stage14 showed that
the player-start route can prove accepted movement without forcing a collision,
so bounded secondary probes remain useful for collision features that should
not distort the main deterministic script. Stage15 showed the same rule applies
to gameplay state: fixed probes can still be source-shaped when they are chosen
from real THINGS/BLOCKMAP data and kept separate from the released baseline.
Stage16 showed that wake/target state can become active before combat: one real
monster can prove thinker mutation, state actions, and sight-driven targeting
without starting damage, death, or generalized AI. Stage17 showed the shortest
honest next step is nonlethal player hitscan damage: one source-shaped shotgun
pellet can spend ammo, participate in bounded line/path traversal, mutate health,
and leave death/drop/chase for later. Stage18 showed that the next honest
movement after damage is not a clean chase start: source `P_MobjThinker` first
services existing momentum, and one accepted MAP01 `P_TryMove` is enough to
prove post-damage monster movement without executing attacks or generalized AI.
Stage19 showed that the first environment mutation can be a fixed real manual
door probe rather than a player-path requirement: `P_UseLines` and one door
thinker can mutate a real sector without broad special dispatch, switch
animation, sound channels, or live input. Stage20 showed that the reached sound
boundary can become real state before any speaker backend exists: one selected
`S_StartSound` call is enough to prove channel choice, metadata, attenuation,
pitch variation, and usefulness/lump bookkeeping while keeping the platform
start call deferred. Stage21 showed that the selected door thinker can be
carried by the normal `P_Ticker -> P_RunThinkers` path without disturbing the
direct stage19 proof. Stage22 showed that a real one-shot switch line can
honestly combine switchlist texture mutation, tagged-sector lookup, thinker
spawn, and one bounded ticker movement while still deferring reusable button
restoration and broad special dispatch.
Stage23 showed that the honest first reusable button proof is not in MAP01:
the pinned IWAD has no clean MAP01 reusable button with a switchlist texture,
so a real MAP15 candidate gives a tighter source-shaped proof than a synthetic
MAP01 shortcut. It also showed that door thinker completion can happen during
the bounded 35-tic button timer without requiring a generalized door system.
Stage24 showed that floor movement has one subtle ticker detail worth preserving
early: the selected lowerFloorToLowest movement reaches the destination on tic
64, but source `T_MovePlane` reports `pastdest` only on the following strict
comparison tic, and the lazy thinker unlink needs one more `P_RunThinkers` pass.
Stage25 confirmed that the same strict plane timing matters once a thinker has
state transitions: the selected lift reaches low and high on equality tics, but
`T_PlatRaise` only changes status or removes the active platform on the next
strict `pastdest` dispatch. It also showed that the active thinker arrays are
worth porting as first-class state before trying to integrate a longer room
script.

Stage26 confirmed the same strict plane timing on the ceiling side while adding
the first source-shaped `activeceilings[]` lifecycle. The selected MAP29
`crushAndRaise` proof reaches the bottom and top on equality tics, then only
reverses on the following strict `pastdest` dispatch. Unlike the selected
stage25 platform, it remains active/cycling after the top reversal, so the
runtime now proves all three representative moving-sector families
(floor/platform/ceiling) without broad generalized sector-special systems.

Stage27 integrates one of those proven ingredients into the first deliberately
scripted, multi-sample room loop. The selected MAP12 platform button route now
runs behind a deterministic `ticcmd_t` sequence through `G_Ticker`,
`P_PlayerThink`, `P_UseLines`, normal `P_Ticker` ordering, `T_PlatRaise`, and
`P_UpdateSpecials`, then reports six successive samples from the same bounded
world instead of only one final snapshot.

Stage28 preserves that non-static loop and adds the first bounded live-input
bridge. Replay mode remains the deterministic smoke path and feeds the stage27
script through a `G_BuildTiccmd`-shaped command builder while reporting
`LIVE28=0`. Manual `-manual` mode reads a tiny Win32 key subset into
Doom-shaped keydown state, builds forward/back/turn/use `ticcmd_t` fields, and
applies the same `BT_USE` usedown edge gate while reporting live command
counters in the title.

Stage29 shows that the existing selected MAP01 shotgun-guy route can continue
through a longer source-ordered thinker loop without broad AI. The bounded
replay starts from the stage17/18 damaged shotgun guy, services momentum,
recovers through pain states, retains target `0`, dispatches one `A_Chase`,
and stops at the first honest attack-decision boundary before attack action,
projectiles, second damage, death, or drops.

Stage30 proves the first real framebuffer-after-launch motion signal: selected
stage14 MAP01 player-view samples drive changed live framebuffer bytes on timer
ticks, and smoke observes distinct `FB30=` signatures. The important caveat is
that this is still a bounded runtime render bridge using emitted frame bytes,
not a continuously recomputed Doom camera view from the full wall/plane/sprite
renderer. The next renderer milestone should close that gap before layering on
combat visuals.

Stage31 closes that caveat for a narrow renderer subset: selected MAP01 view
samples clear the live framebuffer and execute runtime-selected wall-column and
flat-span command tables through emitted `R_DrawColumn`/`R_DrawSpan`-shaped
primitives over real WAD texture and flat data. The proof is still bounded and
command-table driven, but the changed pixels no longer come from full
pre-rendered framebuffer copies.

Stage32 proves the first combat-adjacent visual state in that live redraw path:
selected shotgun psprite states choose real WAD patch/post command tables and
draw after stage31 walls/flats, changing both state markers and framebuffer
signatures. That makes the next honest boundary a selected firing consequence
or impact visual, not another generic renderer proof.

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
- `r_bsp.c`: `R_Subsector` floor/ceiling plane candidates as a source-shaped
  visplane reference
- `r_plane.c`: `R_ClearPlanes` as a source-shaped visplane/frame setup
  reference
- `r_plane.c`: `R_FindPlane` as a bounded padded-visplane reference
- `r_plane.c`: `R_CheckPlane` as a bounded reuse/split reference
- `r_plane.c`: `R_MakeSpans` as a source-shaped span-opening reference
- `r_plane.c`: `R_MapPlane` as a fixed-view plane mapping reference
- `r_plane.c`: `R_DrawPlanes` regular flat branch as a source-shaped reference
- `r_draw.c`: `R_DrawSpan` as a narrow emitted scaler
- WAD flat data: reachable 64x64 regular flat lumps table-emitted for the
  fixed view
- `r_sky.c`: `R_InitSkyMap` as fixed-view sky setup
- `g_game.c`: Doom II `MAP01` `F_SKY1`/`SKY1` selection as a debug adaptation
- `r_plane.c`: `R_DrawPlanes` sky branch as a narrow emitted sky-column loop
- `r_segs.c`: `R_StoreWallRange` masked midtexture setup as a source-shaped
  drawseg/opening reference
- `r_segs.c`: `R_RenderSegLoop` `maskedtexturecol` writes as bounded
  opening-style storage
- `r_segs.c`: `R_RenderMaskedSegRange` as a narrow emitted masked-column loop
- `r_things.c`: `R_DrawMaskedColumn` as the shared masked post/clipping
  primitive
- `p_setup.c`: `P_LoadThings` as source-shaped THINGS decoding
- `p_mobj.c`: `P_SpawnMapThing` as a narrowed player-start/inert-render-mobj
  setup path
- `p_mobj.h` / `d_player.h`: minimal render-facing `mobj_t` and `player_t`
  records
- `info.c` / `info.h`: `sprnames`, `states`, `mobjinfo`, sprite numbers, and
  frame indexes as parsed source tables
- `r_data.c`: `R_InitSpriteLumps` metadata for reachable sprite patch lumps
- `r_things.c`: `R_InitSprites`, `R_ClearSprites`, `R_NewVisSprite`,
  `R_AddSprites`, `R_ProjectSprite`, `R_SortVisSprites`, `R_DrawSprite`, and
  `R_DrawSpriteRange` as source-shaped references/table emission
- `r_bsp.c`: `R_Subsector` sprite gather hook as a primary-sector census
- `r_segs.c`: drawseg `sprtopclip` / `sprbottomclip` sprite clip interaction
  as a synthetic-covered helper
- `p_setup.c`: `P_LoadBlockMap` as source-shaped blockmap decoding
- `p_maputl.c`: `P_BlockLinesIterator`, `P_BlockThingsIterator`,
  `P_PointOnLineSide`, `P_BoxOnLineSide`, and `P_LineOpening` as bounded
  movement/collision references
- `p_map.c`: `PIT_CheckLine`, `PIT_CheckThing`, `P_CheckPosition`, and
  `P_TryMove` as the narrowed local-player collision path
- `p_user.c`: `P_Thrust`, `P_MovePlayer`, `P_CalcHeight`, and the movement
  branch of `P_PlayerThink`
- `p_mobj.c`: `P_XYMovement`, `P_SetThingPosition`, and
  `P_UnsetThingPosition` for player mobj movement and relinking
- `p_tick.c`: `P_Ticker` narrowed to the local player and player mobj
  movement path
- `g_game.c`: `G_Ticker` single-player `ticcmd_t` dispatch
- `d_main.c` / `d_net.c`: frame/tic boundary references for deterministic
  scripted tics
- `r_main.c`: `R_SetupFrame` after movement as final frame setup proof
- `g_game.c`: `G_PlayerReborn` inventory defaults
- `p_mobj.c`: `P_SpawnPlayer` inventory/psprite setup path
- `p_map.c`: `PIT_CheckThing` special-touch branch for bounded pickup probes
- `p_inter.c`: `P_TouchSpecialThing`, `P_GiveAmmo`, `P_GiveWeapon`,
  `P_GiveBody`, `P_GiveArmor`, `P_GiveCard`, and selected power grants
- `d_items.c` / `d_items.h`: `weaponinfo` and ammo/weapon relationships
- `p_pspr.c`: `P_SetupPsprites`, `P_SetPsprite`, `P_BringUpWeapon`, and
  `P_MovePsprites` as no-fire ready-weapon proof
- `st_stuff.c` / `st_lib.c`: compact status widget selection and real patch
  draw commands
- `v_video.c`: `V_DrawPatch` as a narrow emitted status patch-column path
- `r_things.c`: `R_DrawPSprite` as a source-shaped ready weapon placement path
- `r_segs.c` / `r_plane.c`: runtime-selected `R_DrawColumn` and
  `R_DrawSpan` command-table replay for changed live wall/flat frames
- `r_things.c`: selected `R_DrawPlayerSprites` / `R_DrawPSprite` shotgun
  psprite post-table replay after the live wall/flat base
- `p_tick.c`: `P_InitThinkers`, `P_AddThinker`, `P_RemoveThinker`, and a
  bounded `P_Ticker` thinker iteration path
- `p_mobj.c`: `P_SpawnMapThing`, `P_SpawnMobj`, `P_SetMobjState`, and
  `P_MobjThinker` for one active MAP01 monster
- `p_enemy.c`: `A_Look` and `P_LookForPlayers` for bounded target acquisition
- `p_sight.c`: `P_CheckSight`, `P_CrossBSPNode`, and `P_CrossSubsector` as a
  bounded REJECT+BSP sight probe
- `p_enemy.c`: `A_Chase` and `P_NewChaseDir` as counted deferred boundaries
- `p_pspr.c`: `P_CheckAmmo`, `A_WeaponReady`, `A_FireShotgun`,
  `P_BulletSlope`, and `P_GunShot` as a bounded ready-shotgun fire proof
- `p_maputl.c` / `p_map.c`: `P_PathTraverse`, `P_AimLineAttack`, and
  `P_LineAttack` as a bounded hitscan path over real blockmap data
- `p_inter.c`: `P_DamageMobj` and the reached nonlethal pain-state subset;
  `P_KillMobj` remains synthetic/deferred for the pinned proof
- `p_mobj.c`: `P_XYMovement` and post-damage `P_MobjThinker` source order for
  one selected monster
- `p_map.c` / `p_maputl.c`: monster `P_TryMove`, `P_CheckPosition`,
  `PIT_CheckLine`, `PIT_CheckThing`, block iterators, and thing relinking for
  one post-damage movement proof
- `p_map.c` / `p_maputl.c`: `P_UseLines`, `PTR_UseTraverse`, and
  `P_PathTraverse` as a bounded manual-use line probe
- `p_switch.c`: `P_UseSpecialLine` selected manual-door dispatch, with
  switch/button texture behavior covered as a deferred guard
- `p_doors.c`: `EV_VerticalDoor` and `T_VerticalDoor` for one manual blazing
  door thinker record
- `p_spec.c`: `P_FindLowestCeilingSurrounding` / `getNextSector` for the
  selected target sector
- `p_floor.c`: `T_MovePlane` as a bounded ceiling mutation path
- `s_sound.c`: `S_StartSound`, `S_AdjustSoundParams`, `S_StopSound`,
  `S_StopChannel`, and `S_GetChannel` as a bounded first sound-channel state
  proof
- `sounds.h` / `sounds.c`: `sfx_bdopn` enum and `S_sfx` metadata parsing for
  `SOUND("bdopn", 100)`
- `m_random.c`: `M_Random` deterministic pitch variation for the selected
  sound-start call
- `i_sound.c`: `I_GetSfxLumpNum` and `I_StartSound` as counted platform
  boundaries with no speaker output
- `p_switch.c`: `P_InitSwitchList` and switchlist texture pair resolution
- `p_switch.c`: `P_UseSpecialLine` case `103` selected switch-open-door
  dispatch
- `p_switch.c`: `P_ChangeSwitchTexture` one-shot top/middle/bottom switch scan
  and `useAgain=0` line clear
- `p_switch.c`: `P_StartButton` duplicate/free-slot behavior as
  synthetic/deferred stage22 coverage
- `p_doors.c`: `EV_DoDoor` tagged `vld_open` selected path
- `p_spec.c`: `P_FindSectorFromLineTag` bounded tag iteration
- `p_tick.c`: `P_Ticker` one-tic tagged-door continuation using the stage21
  thinker path

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
build/source_stage11_visplanes_floor_ceiling_debug.exe
build/source_stage12_sky_and_masked_midtextures_debug.exe
build/source_stage13_things_sprites_and_real_frame_setup.exe
build/source_stage14_game_loop_input_collision.exe
build/source_stage15_pickups_psprites_statusbar_shell.exe
build/source_stage16_active_monster_thinkers_and_targeting.exe
build/source_stage17_first_weapon_fire_damage_and_death_probe.exe
build/source_stage18_post_damage_monster_movement_and_chase_probe.exe
build/source_stage19_first_door_or_switch_sector_special_probe.exe
build/source_stage20_audio_channels_and_deferred_sound_playback.exe
build/source_stage21_door_thinker_ticker_and_special_update_probe.exe
build/source_stage22_first_switch_texture_and_tagged_door_probe.exe
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
- Consume the stage10 `727` ceiling and `932` floor plane marks through
  bounded padded visplanes, split occupied planes visibly, map regular spans,
  and draw `20791` floor/ceiling flat pixels through emitted x86
  `R_DrawSpan`.
- Run a source-shaped MAP01 feature census that finds `40` sky-ceiling sectors
  and `27` two-sided masked sidedef candidates.
- Preserve the primary player-start view's zero sky/masked hits as
  `PSKY=0 PMASK=0`, then use a documented fixed feature probe at
  `PVX=1771 PVY=-773 PVA=277 PSEC=196`.
- Draw `32` `SKY1` sky columns and `1280` sky pixels through the sky branch of
  `R_DrawPlanes`.
- Draw `32` `AQMETL29` masked midtexture columns, `32` masked post commands,
  and `1888` masked pixels after walls and flats.
- Decode real `MAP01` `THINGS`, seed the fixed frame from player-one start,
  gather `6` primary-frame vissprites, and draw `175` real sprite pixels.
- Load the real `MAP01` `BLOCKMAP`, run the eight-tic stage14 movement script,
  and preserve `S14SIG=3925602456`.
- Run a separate fixed pickup proof through real THINGS/BLOCKMAP data:
  shotgun mapthing `27`, then clip mapthing `41`.
- Mutate source-shaped player inventory to `CLIP=60 SHELL=8 WOWN=3`, raise the
  shotgun psprite to `S_SGUN`, draw real status and weapon patches, and report
  `S15SIG=2810145191`.
- Select real MAP01 shotgun-guy mapthing `37` / mobj `28`, advance it through
  a 13-tic bounded thinker/state loop, acquire the stage15 player mobj through
  `A_Look`, `P_LookForPlayers`, and bounded `P_CheckSight`, and report
  `S16SIG=249707937` while keeping chase movement and combat deferred.
- Fire the ready shotgun through a bounded source-shaped weapon path, spend one
  shell, run real blockmap hitscan participation, mutate the selected shotgun
  guy from `30` to `20` health through `P_DamageMobj`, and report
  `S17SIG=2157381017` while keeping death/drop/chase absent.
- Load the real `MAP01` `BLOCKMAP` with origin `(-256, -1808)` and size
  `20x27`, run an eight-tic deterministic local command script from the real
  player start, accept `8` source-shaped `P_TryMove` moves through blockmap
  line/thing checks, relink the player mobj each move, and record a final
  post-script frame setup at `F14X=-172 F14Y=-194 F14A=3 F14SS=227 F14SEC=0`.
- Keep a separate MAP01 collision probe for the first blocking line proof:
  `CPROBE=1 CLINE=0 CBLK=1 CBLN=1`.
- Draw a simple top-down debug framebuffer with map lines, visited segs, and
  the fixed viewpoint marker; stage04 through stage06 overlay bbox-visible
  segs from the second pass, stages09/10 overlay wall pixels, stage11 overlays
  regular flat pixels in marked floor/ceiling regions, and stage12 overlays the
  fixed sky/masked feature-probe proof.
- Display deterministic accept-all, sentinel-only bbox-visible, mutable
  clipping, wall-projection, texture setup, flat setup, first/last
  projected-span texture IDs, direct-column counters, first drawn texture,
  visplane/flat-span counters, first floor/ceiling flat names, sky/masked
  probe metadata, first sky/masked texture names, sprite counters, movement
  counters, blockmap counters, collision-probe counters, pickup/status
  counters, active-monster thinker/target counters, and runtime pixel,
  movement, or gameplay-state signatures in the framebuffer and window title.

The verified stage09 smoke signal for pinned Freedoom2 `MAP01` is:

```text
V=1189 SEC=211 SD=2041 L=1274 SS=698 N=697 SG=2233 VN=697 VSS=698 VSEG=2233 DEPTH=33 FIRSTSS=227 LASTSS=169 BVN=559 BVSS=513 BVSEG=1709 BDEPTH=33 BFIRSTSS=227 BLASTSS=153 CULL=47 CLN=72 CLSS=56 CLSEG=205 CLCULL=17 BF=82 OFF=17 ZPX=5 SOL=30 PASS=70 SPAN=86 NSEGS=1 FSPAN=224-255 FSEG=605 LSPAN=143-165 LSEG=855 VZ=2686976 VCOS=65535 VSIN=25 VALID=1 FRAME=1 PRJ=86 MIND=2073560 MAXD=58720255 MINS=11702 MAXS=108495 FPRJ=224-255 FPSEG=605 LPRJ=143-165 LPSEG=855 TEX=963 PN=1054 FLAT=246 DIRC=80797 COMPC=26323 FPTEX=850 LPTEX=13 EMID=1 DWSP=86 OPQSP=24 DCOL=297 DRAW=162 SKC=135 SKU=62 ZTEX=0 MASK=0 FTEX=850 FN=AQRUST08 FCOL=127 PIX=15508 SIG=2194105880
```

The verified stage10 smoke signal keeps the stage09 string above and adds:

```text
CMB=89 CMH=75 CMO=0 MCOL=2 MCEMP=133 UCOL=478 UCOMP=6 LCOL=138 PM=1659 F10TEX=850 F10N=AQRUST08 L10TEX=887 L10N=AQSECT08 TCOL=780 TPIX=37546 TSIG=4201955800
```

The verified stage11 smoke signal keeps the stage10 string above and adds:

```text
VP=38 VPF=30 VPR=88 VPS=8 VPO=0 CPM=727 FPM=932 FSP=169 FPIX=20791 SKYV=0 SKYC=0 SKYP=0 FSK=0 SPO=0 F11F=81 F11FN=SLIME14 C11F=113 C11N=FLOOR5_2 FSIG=2178063413
```

The verified stage12 smoke signal keeps the stage11 string above and adds:

```text
SKCAND=40 MCAND=27 PROBE=1 PSKY=0 PMASK=0 SKYSEC=2 MSIDE=617 PVX=1771 PVY=-773 PVA=277 PSEC=196 SKYT=229 SKYN=SKY1 SCOL=32 SPIX=1280 MTEX=814 MN=AQMETL29 MCOL12=32 MPOST=32 MPIX=1888 SPR=0 SSK=0 S12SIG=2853564869
```

The verified stage13 smoke signal keeps the stage12 string above and adds:

```text
TH=200 PST=4 RMO=120 UTH=2 SKSK=17 PSX=-192 PSY=-192 PSA=0 PSS=0 SPNAMES=138 SPLUMPS=1350 SPMISS=0 SPSEC=29 VIS=6 VISOV=0 SPROBE=0 FSTH=8 FSPR=60 FSN=BON1 FSF=0 FSPT=1009 FSPN=BON1A0 SPCOL=35 SPPOST=40 SPPIX=175 S13SIG=2904743961
```

The verified stage14 smoke signal keeps the stage13 string above and adds:

```text
BMW=20 BMH=27 TIC=8 I14X=-192 I14Y=-192 F14X=-172 F14Y=-194 F14A=3 F14SS=227 F14SEC=0 F14VZ=2753061 F14MX=183699 F14MY=-36831 ACPT=8 REJ14=0 LCHK=48 TCHK=0 BLI=8 BTI=16 LDUP=8 SDEF=0 CPROBE=1 CLINE=0 CBLK=1 CBLN=1 RLINK=8 S14SIG=3925602456
```

The verified stage15 smoke signal keeps the stage14 string above and adds:

```text
PPROBE=2 PACC=2 PREM=2 P1=27 P1N=SHOT P2=41 P2N=CLIP HP=100 ARM=0 AT=0 CLIP=60 SHELL=8 WOWN=3 RDY=2 PEND=9 PSPST=18 PSPN=S_SGUN PSPT=1 STP=11 STCOL=469 STPIX=12533 WPN=SHTGA0 WPCOL=66 WPPIX=2083 MDEF=2 SNDDEF=2 S15SIG=2810145191
```

The verified stage16 smoke signal keeps the stage15 string above and adds:

```text
MCENS=18 ACTM=1 TADD=1 TRUN=13 MT16=37 MO16=28 M16N=SHOTGUY M16X=1752 M16Y=-936 M16SEC=58 M16BX=15 M16BY=6 MTIC0=3 LLOOK=1 LOOK=2 LFP=2 SIGHT=1 SOK=1 SNODE=77 SSUB=28 SLINE=5 TGT=1 ST0=207 STFN=S_SPOS_RUN1 STF=209 FTIC=3 CHDEF=1 SND16=1 ATK=0 DMG=0 KILL=0 S16SIG=249707937
```

This is deliberately still a debug renderer. It is a bridge from experiment to
source-guided engine port: the project is walking real Doom BSP structures in
source order, pruning bbox-invisible back subtrees, and computing mutable wall
span clipping and wall projection live, with source-shaped texture/flat setup
and a broader wall-plus-regular-flat-plus-sky/masked/sprite rendering path plus
the first local-player movement/collision, inventory/status, and active-monster
targeting proofs now proven. The end goal remains the same: build Doom from the
source behavior, without a compiler, one runnable emitted PE32 slice at a time.

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
  Stage11 turned those marks into real bounded `visplane_t` records before
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

## Lessons From source_stage11_visplanes_floor_ceiling_debug

- Padded `visplane_t` layout matters even in the Python reference. The source
  writes sentinel `top[minx-1]` and `top[maxx+1]`, so modeling the pad bytes
  made `R_MakeSpans` behave like the C routine instead of a simplified
  rectangle filler.
- The stage10 handoff is enough for a narrow regular-flat proof. Replaying
  those marks through `R_FindPlane` and `R_CheckPlane` yields `38` visplanes,
  `30` new planes, `88` reuses, and `8` splits for the pinned view.
- `R_DrawSpan` is a good emitted-runtime boundary. Python can source-shape the
  fixed `R_MapPlane` math and table-emit span globals, while the executable
  still performs the packed-position flat sampling, framebuffer writes, pixel
  counts, and signature updates live.
- The pinned MAP01 player-start view has no visible sky plane in the stage10
  handoff (`SKYV=0 SKYC=0 SKYP=0`) and no masked midtexture hit, even though
  MAP01 contains both sky sectors and two-sided masked sidedefs. Stage12 should
  preserve the player-start view and add a documented fixed feature probe if
  needed, rather than treating zero sky/masked counters as a release.
- The next slice should preserve the wall-first, regular-flat-second order and
  add only the deferred sky/masked wall drawing. Real sprites remain a later
  boundary because they need thing loading and actor state.

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

Source routines traced/reused:

- Reuse from stage04: `r_main.c`: `R_PointToAngle`, `viewangletox`,
  `xtoviewangle`, and `clipangle`
- Reuse from stage04: `r_bsp.c`: `R_ClearClipSegs` and `R_CheckBBox`
- `r_bsp.c`: `R_Subsector` as a debug adaptation that now calls
  `R_AddLine`
- `r_bsp.c`: `R_AddLine`
- `r_bsp.c`: `R_ClipSolidWallSegment`
- `r_bsp.c`: `R_ClipPassWallSegment`
- `r_segs.c`: `R_StoreWallRange` as a debug span-recording adaptation

Released goal:

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

## Released Slice: source_stage11_visplanes_floor_ceiling_debug

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

- Source order mattered: `R_ClearPlanes` runs at frame start; subsector handling
  calls `R_FindPlane` for current floor/ceiling candidates; wall range storage
  calls `R_CheckPlane`; wall columns write top/bottom marks; `R_DrawPlanes`
  later turns those visplane marks into spans. Stage11 mirrors that order with
  some structures still table-fed for the fixed pinned view.
- Stage10 provided the pinned handoff records for this: `727` ceiling marks,
  `932` floor marks, and `PM=1659` total records. Stage11 consumes those
  records through source-shaped visplane find/check logic before mapping flat
  pixels.
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

Released because:

- `build/source_stage11_visplanes_floor_ceiling_debug.exe` exists and
  launches.
- It preserves the stage10 wall-pixel signal:
  `CMB=89 CMH=75 CMO=0 MCOL=2 MCEMP=133 UCOL=478 UCOMP=6 LCOL=138 PM=1659 F10TEX=850 F10N=AQRUST08 L10TEX=887 L10N=AQSECT08 TCOL=780 TPIX=37546 TSIG=4201955800`.
- It reports deterministic stage11 visplane and regular flat-span counters:
  `VP=38 VPF=30 VPR=88 VPS=8 VPO=0 CPM=727 FPM=932 FSP=169 FPIX=20791 SKYV=0 SKYC=0 SKYP=0 FSK=0 SPO=0 F11F=81 F11FN=SLIME14 C11F=113 C11N=FLOOR5_2 FSIG=2178063413`.
- Synthetic tests cover `R_FindPlane`, `R_CheckPlane`, `R_MakeSpans`,
  `R_MapPlane`, and `R_DrawSpan`.
- Pinned MAP01 tests cover preserved stage10 counters, visplane counts,
  plane-mark consumption, regular flat span/pixel totals, skipped sky
  counters, first floor/ceiling flat IDs/names, and framebuffer signature.
- `python -B -m unittest discover -s tests` passes and the scripted smoke test
  launches/closes the binary.
- Source trace and smoke docs are updated.

## Released Slice: source_stage12_sky_and_masked_midtextures_debug

Output:

```text
build/source_stage12_sky_and_masked_midtextures_debug.exe
```

Source routines to read and trace/reuse:

- Reuse from stage11: wall columns, regular flat spans, visplanes,
  `ceilingclip` / `floorclip`, flat IDs, palette/colormap adaptation, and
  framebuffer signature.
- Reuse the stage07/stage11 fixed-view setup path for a secondary MAP01
  feature-probe view only if the primary player-start view still has no visible
  sky or masked midtexture work.
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

Stage11 taught one important correction: the primary pinned player-start view
reports no sky visplanes and no masked midtexture hits, even though the pinned
Freedoom2 `MAP01` data contains `40` sky-ceiling sectors and `27` two-sided
masked sidedef references, currently all resolving to `AQMETL29`. Stage12
therefore must not be a zero-work title-only release. It should preserve the
primary stage11 view and counters, then add a bounded secondary fixed
feature-probe view selected from real `MAP01` geometry if needed to visibly
exercise sky and masked-wall drawing. The probe view must be deterministic,
documented in the trace/tests, and still use the pinned IWAD; it is not
movement, gameplay, or a generalized camera.

User-visible feature:

- Draws the primary stage11 player-start view unchanged.
- Draws supported sky ceiling columns and deterministic masked midtexture
  columns in the primary view if reachable; otherwise draws them in a
  secondary fixed MAP01 feature-probe pane/view.
- Draws masked midtexture columns from real WAD patch/composite data after
  solid wall and flat drawing.
- Reports primary-view preserved stage11 counters, feature-probe selection
  metadata, sky visplanes/columns/pixels, masked wall spans/columns/pixels,
  masked ordering records, skipped sprite records, first sky texture name,
  first masked texture name, and a framebuffer signature.
- Preserves upstream stage10/stage11 counters.

Runtime data to add:

- `skyflatnum`, `skytexture`, `skytexturemid`, and the fixed Doom II `MAP01`
  sky texture selection needed by the debug view.
- A small source-guided MAP01 feature-candidate scan emitted as deterministic
  metadata: sky sector candidates, two-sided masked sidedef candidates, selected
  probe view coordinates/angle/sector, and visible unsupported/zero counters.
- `maskedtexturecol` / opening-style storage for two-sided midtexture columns,
  with bounded overflow counters.
- Minimal drawseg fields needed by `R_RenderMaskedSegRange`: `x1`, `x2`,
  `scale1`, `scalestep`, `sprtopclip`, `sprbottomclip`, `maskedtexturecol`,
  and the sidedef/sector texture fields already proven by earlier slices.
- Masked column globals used by `R_DrawMaskedColumn`, including `sprtopscreen`,
  `spryscale`, `mfloorclip`, and `mceilingclip`.
- Separate primary/probe counters for sky and masked work if a probe view is
  needed, so the title never hides the fact that the original player-start
  view had zero feature hits.

Implementation notes:

- Keep Stage12 ordered like the source frame: solid walls first, regular flats
  next, then late masked drawing. Sky comes through the sky branch in
  `R_DrawPlanes`; masked midtextures come through drawseg/opening records.
- A fixed `SKY1` selection is acceptable for the pinned Doom II `MAP01` proof,
  but document it as a debug adaptation and keep later generalized episode/map
  sky selection small.
- Start with a Python source-shaped candidate census over the pinned WAD and
  map. If the primary view remains `SKYV=0` and `MASK=0`, choose one bounded
  secondary MAP01 proof view from that census and freeze it in tests before
  emitting bytes.
- Keep the secondary view small: it may have its own draw commands and
  signature path, but it must reuse existing source-shaped setup/math rather
  than inventing a second renderer architecture.
- The shared masked-column primitive may be source-shaped in Python first, but
  the executable must still draw deterministic sky/masked pixels and update a
  runtime signature.
- Do not load things or project sprites in Stage12. It may include zero-sprite
  ordering counters so Stage13 has a clean hook, but real sprite data belongs
  with `P_LoadThings` and `mobj_t` setup.
- Do not continue to stage13 unless the executable proves at least one real
  sky or masked-wall pixel path from the pinned IWAD, either in the primary
  view or the documented feature probe.

Tests:

- Synthetic MAP01-feature candidate tests for sky sector detection, two-sided
  masked sidedef detection, and deterministic probe selection when the primary
  pinned view has no feature hits.
- Synthetic sky-column tests for angle-to-sky texture column selection and
  fixed `skytexturemid` stepping.
- Synthetic `maskedtexturecol` / opening tests for bounded storage, clipping,
  and draw order after walls/flats.
- Synthetic `R_DrawMaskedColumn` tests for post clipping against
  `mfloorclip`/`mceilingclip`.
- Pinned MAP01 reference tests for preserved primary stage11 counters, feature
  probe metadata if used, sky counts, masked wall counts, first names, skipped
  sprite count, and framebuffer signature.
- Build/smoke tests verifying preserved stage11 counters plus sky/masked
  counters, and confirming real sprites, actors, movement, gameplay, and
  `source_stage13` strings are absent.

Done when:

- The stage12 executable draws deterministic wall, flat, sky, and masked
  midtexture pixels from the pinned WAD.
- Real sprite/thing/gameplay work remains absent and visibly counted/deferred.
- Full unit tests and GUI smoke pass.
- Source trace and smoke docs are updated.

Released because:

- `build/source_stage12_sky_and_masked_midtextures_debug.exe` exists and
  launches.
- It preserves the stage11 primary player-start wall/flat signal:
  `VP=38 VPF=30 VPR=88 VPS=8 VPO=0 CPM=727 FPM=932 FSP=169 FPIX=20791 SKYV=0 SKYC=0 SKYP=0 FSK=0 SPO=0 F11F=81 F11FN=SLIME14 C11F=113 C11N=FLOOR5_2 FSIG=2178063413`.
- It reports deterministic stage12 feature-probe, sky, masked-wall, and
  signature counters:
  `SKCAND=40 MCAND=27 PROBE=1 PSKY=0 PMASK=0 SKYSEC=2 MSIDE=617 PVX=1771 PVY=-773 PVA=277 PSEC=196 SKYT=229 SKYN=SKY1 SCOL=32 SPIX=1280 MTEX=814 MN=AQMETL29 MCOL12=32 MPOST=32 MPIX=1888 SPR=0 SSK=0 S12SIG=2853564869`.
- Synthetic tests cover sky sector detection, masked sidedef detection,
  deterministic probe selection, sky texture column selection,
  `maskedtexturecol` storage/consumption, and masked post clipping.
- Pinned MAP01 tests cover preserved stage11 counters, feature-probe metadata,
  sky/masked names and counts, skipped sprite count, and framebuffer
  signature.
- `python -B -m unittest discover -s tests` passes and the scripted smoke test
  launches/closes the binary.
- Source trace and smoke docs are updated.

## Released Slice: source_stage13_things_sprites_and_real_frame_setup

Output:

```text
build/source_stage13_things_sprites_and_real_frame_setup.exe
```

Released proof:

- Stage13 preserves all stage08-stage12 counters, including
  `S12SIG=2853564869`.
- It decodes `TH=200` real `MAP01` THINGS records, records `PST=4` player
  starts, creates `RMO=120` render mobjs, and seeds the fixed frame from
  `PSX=-192 PSY=-192 PSA=0 PSS=0`.
- It initializes `SPNAMES=138 SPLUMPS=1350 SPMISS=0` sprite metadata records,
  gathers `VIS=6` primary-frame vissprites from `SPSEC=29` source-shaped
  sectors, and uses no sprite proof probe (`SPROBE=0`).
- It draws first sprite `FSTH=8 FSPR=60 FSN=BON1 FSF=0 FSPT=1009 FSPN=BON1A0`
  and reports `SPCOL=35 SPPOST=40 SPPIX=175 S13SIG=2904743961`.

Source routines to read and trace/reuse:

- Reuse from stage12: wall columns, regular flats, sky columns, masked wall
  columns, drawseg/opening records, palette/colormap adaptation, and framebuffer
  signature.
- `p_setup.c`: `P_LoadThings`.
- `p_mobj.c`: `P_SpawnMapThing` only as far as the fixed proof needs mapthing
  type, position, angle, flags, and sprite/frame identity.
- `info.c` / `info.h`: `mobjinfo`, states, sprite numbers, and frame indexes
  needed for visible map things.
- `p_mobj.h` / `d_player.h`: enough `mobj_t` and `player_t` layout to seed
  render-facing fields without starting thinkers.
- `r_data.c`: `R_InitSpriteLumps`, narrowed to table-emitted metadata for
  reachable sprite lumps.
- `r_things.c`: `R_InitSprites`, `R_ClearSprites`, `R_NewVisSprite`,
  `R_AddSprites`, `R_ProjectSprite`, `R_SortVisSprites`, `R_DrawSprite`,
  `R_DrawSpriteRange`, and the shared masked-column primitive already proven in
  stage12.
- `r_main.c`: `R_SetupFrame` using real loaded player start / minimal
  `player_t` and `mobj_t` state instead of only hard-coded debug globals.

Goal:

Load real map things and prove Doom's sprite projection/drawing path for the
fixed renderer without starting gameplay. This is the first slice where the
renderer should use real `THINGS` data and a minimal source-shaped player/mobj
frame setup, while still ending in a deterministic debug executable rather than
a moving game.

Stage13 remains renderer-first. It creates inert render-facing `mobj_t`
records from `P_LoadThings` / `P_SpawnMapThing`, but it does not tick world
state, process weapon psprites, perform collision movement, or advance the
world.

User-visible feature:

- Preserves stage12 wall, flat, sky, and masked-wall output.
- Seeds the fixed view from a minimal real player start object created from
  `THINGS`, matching the previous pinned `(-192, -192, 0)` view.
- Draws deterministic visible sprites from real WAD sprite lumps in the primary
  player-start view, so no secondary MAP01 sprite-probe view is needed.
- Reports thing counts, spawned player/mobj counts, sprite definitions/lumps
  touched, vissprite counts, clipped/drawn sprite columns/pixels, skipped
  unsupported sprite frames, first sprite name/frame, primary/probe selection
  metadata if used, and framebuffer signature.

Runtime data to add:

- Bounded mapthing records loaded from `THINGS`.
- Minimal inert `mobj_t` / `player_t` / view setup fields needed by
  `R_SetupFrame`, `R_AddSprites`, and `R_ProjectSprite`: position, angle,
  subsector/sector link, sprite, frame, render flags, radius/height, floorz,
  ceilingz, and player start ownership.
- Bounded sprite metadata tables: sprite names, sprite frame rotations, lump
  numbers, offsets, widths, top offsets, and patch-column sources.
- `vissprite_t`-shaped records, `vissprite_p`, overflow/sentinel handling, and
  sorting storage.
- Sprite clip access to stage12 drawseg `sprtopclip` / `sprbottomclip` data,
  with visible overflow/skipped counters.
- A deterministic sprite feature census over pinned `MAP01`, including primary
  visible candidates and any secondary sprite-probe view required to prove at
  least one real sprite pixel path.

Implementation notes:

- Keep this as a renderer-data slice, not gameplay. Do not add thinker ticks,
  movement, collision, attacks, pickups, sound, status bar, automap, menu, or
  save/game state.
- Preserve the stage12 sky/masked proof and the primary stage12 counters before
  adding sprite output. If a sprite probe is needed, keep it as explicit and
  deterministic as the stage12 feature probe.
- Prefer a Python source-shaped reference for sprite lump/frame selection and
  projection before emitting bytes. The executable should still perform the
  final sprite/masked-column draw loop and signature updates.
- Keep primary player-start compatibility visible. Any secondary sprite probe
  must be documented as a deterministic proof view selected from real MAP01
  data, not a movable camera.
- Reuse stage12's masked-column primitive wherever possible; sprite drawing and
  masked-wall drawing share ordering and clipping ideas in the source.
- Draw order should match the source: clear sprites at frame start, gather
  sprites during subsector handling, draw walls/flats/sky, then draw masked
  walls and sprites through the late masked path. If the debug slice keeps
  masked walls and sprites in separate command buffers, the title/status should
  make that adaptation visible.
- Bound `vissprite` and sprite-column buffers with visible title counters.

Tests:

- Synthetic `P_LoadThings` tests for mapthing decoding, player start
  recognition, and unsupported thing counts.
- Synthetic `P_SpawnMapThing` tests for player starts, inert render mobjs,
  skill/option filtering, and unsupported type counters.
- Synthetic sprite metadata tests for lump naming, rotation/frame resolution,
  offsets, and missing frame handling.
- Synthetic `R_ClearSprites` / `R_NewVisSprite` tests for reset and overflow.
- Synthetic `R_ProjectSprite` tests for view-space transform, screen x ranges,
  scale, clipping, and rejection cases.
- Synthetic `R_SortVisSprites` / `R_DrawSprite` / `R_DrawSpriteRange` tests for
  draw order, horizontal clipping, and clip interaction with drawsegs.
- Pinned MAP01 reference tests for thing counts, player start setup, visible
  sprite counts, selected primary/probe view if needed, first sprite/frame,
  drawn sprite pixels, and signature.
- Build/smoke tests verifying preserved stage12 counters plus sprite counters,
  and confirming gameplay loop, movement, collision, sound, UI, and
  `source_stage14` strings are absent.

Released status:

- The stage13 executable draws deterministic sprites from real WAD sprite
  lumps after stage12 walls/flats/sky/masked walls.
- The fixed view is seeded from real loaded player-start data.
- Runtime actor updates remain absent and visibly deferred.
- Full unit tests and GUI smoke pass.
- Source trace and smoke docs are updated.

## Released Slice: source_stage14_game_loop_input_collision

Output:

```text
build/source_stage14_game_loop_input_collision.exe
```

Source routines to read and trace/reuse:

- Reuse from stage13: real loaded `THINGS`, minimal player/mobj setup, sprite
  metadata, primary fixed renderer proof, and the emitted stage13 no-script
  baseline.
- `p_setup.c`: `P_LoadBlockMap`, because an honest movement/collision proof
  needs real MAP01 block coordinates and block line lists.
- `p_maputl.c`: `P_BlockLinesIterator`, `P_BlockThingsIterator`, and the
  bounding-box/line-side helpers needed by the narrowed collision path.
- `p_map.c`: `PIT_CheckLine`, `PIT_CheckThing`, `P_CheckPosition`,
  `P_TryMove`, and only the `P_SlideMove` subset needed if the chosen script
  hits a wall at an angle.
- `p_user.c`: `P_Thrust`, `P_MovePlayer`, `P_CalcHeight`, and the movement
  portion of `P_PlayerThink`.
- `p_mobj.c`: `P_XYMovement`, `P_SetThingPosition`, and
  `P_UnsetThingPosition` as far as they update the player mobj's position,
  sector/subsector link, block link, and floor/ceiling values.
- `p_tick.c`: `P_Ticker`, narrowed to one local player and the player mobj
  movement path, not a generalized thinker list.
- `g_game.c`: `G_Ticker` command dispatch for a single local player.
- `d_main.c` / `d_net.c`: `D_DoomLoop` / `TryRunTics` only as timing and
  frame-boundary references for a deterministic scripted run.
- `r_main.c`: `R_SetupFrame` rerun after the player mobj moves, so the final
  frame uses updated source-shaped view fields.

Goal:

Turn the fixed renderer harness into the first source-shaped local-player world
slice: load real blockmap state, run a short deterministic `ticcmd_t` script
from the real player start, move through the source player/mobj/collision path,
and re-render the final frame. This is still not full gameplay. It should prove
command interpretation, momentum, map collision, sector relinking, and
post-move frame setup while preserving a deterministic stage13 baseline mode.

User-visible feature:

- The executable runs a bounded scripted command sequence, for example
  forward/turn/strafe tics chosen from a Python source-shaped MAP01 census.
- It renders the original stage13 fixed frame and a final post-script frame,
  or clearly reports both the baseline and scripted signatures.
- It reports initial/final player x/y/z, angle, subsector, sector, viewz,
  momentum, accepted/rejected move counts, slide counts if used, blocking
  line/thing counts, blockmap dimensions, tic count, and a deterministic
  movement/frame signature.
- It keeps a no-script comparison path so `S13SIG=2904743961` remains visible
  and testable.
- It does not add attacks, pickups, doors/switch activation, monster AI,
  damage, sound, status bar, automap, menu, save/load, or networking.

Runtime data to add:

- A minimal `ticcmd_t` buffer and local player command runner for deterministic
  scripted input.
- Movement-facing `player_t` fields: command, viewheight, deltaviewheight,
  bob, viewz, playerstate, cheats/no-clip flag, and enough weapon/psprite
  fields to keep the movement branch inert.
- Movement-facing `mobj_t` fields: x/y/z, momx/momy/momz, radius/height,
  flags, angle, floorz, ceilingz, subsector/sector links, block links,
  reactiontime, state, and player ownership.
- Real blockmap data: origin, width, height, block offsets/lists, and bounded
  iterators for line and thing checks.
- Collision globals mirrored from `p_map.c`: `tmthing`, `tmx/tmy`, `tmbbox`,
  `tmfloorz`, `tmceilingz`, `tmdropoffz`, touched line counters, and visible
  overflow/skip counters.
- Sector/block thing lists for the player and inert solid things that can block
  movement; special pickup mutation remains deferred and should be counted if a
  script touches one accidentally.
- Deterministic per-tic trace records and per-frame signature records for
  smoke tests.

Implementation notes:

- Keep this stage source-guided and narrow. It is the first moving-player proof,
  not the first combat or interaction proof.
- Start with a Python reference over the pinned WAD that loads blockmap data,
  runs the scripted tics, and freezes expected positions/counters before
  emitting bytes.
- Choose a script that proves at least one accepted move. If a natural script
  from the player start does not hit a blocking line or thing, choose one
  deterministic MAP01 collision probe and report it separately, the same way
  stage12 separated its feature probe.
- Do not fake movement with direct position assignment. The path should be
  `ticcmd_t -> P_PlayerThink/P_MovePlayer -> P_Thrust -> P_XYMovement ->
  P_TryMove/P_CheckPosition` for accepted/rejected movement.
- Avoid pickup routes in the stage14 script. If `PIT_CheckThing` sees
  `MF_SPECIAL`, count it as deferred rather than mutating inventory.
- Keep live keyboard input out of the releasable proof. It can be a later
  convenience, but the smoke path must be deterministic.
- Preserve the stage13 fixed render path and add the scripted movement render
  as a clearly separated pass so renderer regressions are easy to spot.
- Bound every tic, block, line, thing, touch-line, and movement buffer with
  title/status counters.

Tests:

- Synthetic `P_LoadBlockMap` tests for header decoding, offsets, terminators,
  bounds, and malformed block lists.
- Synthetic block iterator tests for line and thing visitation order, duplicate
  suppression, and overflow counters.
- Synthetic `ticcmd_t`, `P_Thrust`, `P_MovePlayer`, and `P_XYMovement` tests
  for forward/side/angle command interpretation and momentum/friction.
- Synthetic `P_CheckPosition` / `P_TryMove` tests for open space, wall block,
  step/drop limits, thing blocking, and deferred special-touch accounting.
- Pinned MAP01 scripted movement reference tests for initial/final position,
  angle, subsector, sector, viewz, accepted/rejected movement counts, blocking
  line/thing counters, and final signature.
- Build/smoke tests verifying preserved stage13 render counters plus stage14
  movement/collision counters, and confirming attacks, pickups, monster AI,
  sound, UI, save/load, networking, and `source_stage15` strings are absent.

Released status:

- The stage14 executable preserves the full stage13 baseline, including
  `S13SIG=2904743961`.
- It loads real `MAP01` blockmap data (`BMW=20 BMH=27`) and runs an eight-tic
  deterministic command script from `I14X=-192 I14Y=-192`.
- The script proves accepted source-shaped movement:
  `F14X=-172 F14Y=-194 F14A=3 F14SS=227 F14SEC=0 F14VZ=2753061
  F14MX=183699 F14MY=-36831 ACPT=8 REJ14=0 LCHK=48 TCHK=0`.
- The separate MAP01 collision probe reports
  `CPROBE=1 CLINE=0 CBLK=1 CBLN=1`.
- Stage14 reports `S14SIG=3925602456` and keeps deferred systems absent from
  the PE status strings. Stage14-focused unit tests and GUI smoke pass; the
  most recent full `unittest discover` run was blocked locally by Windows
  Defender/AV while launching older stage09/stage11 smoke executables, not by a
  stage14 assertion.
- Source trace and smoke docs are updated.

## Released Slice: source_stage15_pickups_psprites_statusbar_shell

Output:

```text
build/source_stage15_pickups_psprites_statusbar_shell.exe
```

Released proof:

- Stage15 preserves the full stage14 movement/collision baseline and runs a
  separate fixed MAP01 pickup proof selected by a source-shaped pickup census.
- The released route touches shotgun mapthing `27` / mobj `21` / sprite
  `SHOT`, then clip mapthing `41` / mobj `30` / sprite `CLIP`; both touches
  go through real `THINGS`/`BLOCKMAP` participation and `PIT_CheckThing ->
  P_TouchSpecialThing`.
- Final stage15 title/status proof:
  `PPROBE=2 PACC=2 PREM=2 P1=27 P1N=SHOT P2=41 P2N=CLIP HP=100 ARM=0 AT=0 CLIP=60 SHELL=8 WOWN=3 RDY=2 PEND=9 PSPST=18 PSPN=S_SGUN PSPT=1 STP=11 STCOL=469 STPIX=12533 WPN=SHTGA0 WPCOL=66 WPPIX=2083 MDEF=2 SNDDEF=2 S15SIG=2810145191`.
  The preserved stage14 baseline remains `S14SIG=3925602456`.
  Dedicated stage15 unit/build/GUI smoke tests pass.

Source routines to read and trace/reuse:

- Reuse from stage14: scripted local-player movement, real blockmap collision,
  player/mobj sector/block links, and the post-move renderer proof.
- `g_game.c`: `G_PlayerReborn` and player inventory defaults as the source
  shape for health, starting weapons, ammo, cards, powers, frags, and weapon
  slots.
- `p_mobj.c`: `P_SpawnPlayer` setup that connects the player mobj, viewheight,
  health, ready weapon, and psprite initialization; keep the stage14 movement
  fields stable.
- `p_map.c`: `PIT_CheckThing` special-touch branch now enabled for a bounded
  set of pickups.
- `p_inter.c`: `P_TouchSpecialThing`, `P_GiveAmmo`, `P_GiveWeapon`,
  `P_GiveBody`, `P_GiveArmor`, `P_GiveCard`, selected powerup grant helpers,
  and the bonus/message side effects only as far as deterministic pickups
  require.
- `d_items.c` / `d_items.h`: `weaponinfo` and ammo/weapon relationships.
- `p_pspr.c`: `P_SetupPsprites`, `P_SetPsprite`, `P_BringUpWeapon`,
  `P_MovePsprites`, and `P_CheckAmmo`; firing states remain deferred unless a
  no-damage dry proof is explicitly needed.
- `st_stuff.c` / `st_lib.c`: `ST_Start`, `ST_Ticker`, and the widget drawing
  path narrowed to a deterministic status-bar shell.
- `v_video.c`: `V_DrawPatch` / patch blit behavior reused in a narrow emitted
  form for status and psprite patches.
- WAD status/weapon patches: only the reachable status digits/icons and ready
  weapon psprite patches needed by the pinned proof.

Goal:

Make the first visible game-state slice after movement: walk into one or more
real MAP01 pickups, update source-shaped player inventory/state, show the
ready weapon psprite/status-bar shell, and re-render deterministically. This is
still not combat and not a full HUD/menu system. The important transition is
from "the player can move through the map" to "the player can mutate game state
through the same collision/touch path the source uses."

User-visible feature delivered:

- The release uses a documented fixed MAP01 pickup probe for two selected real
  `MF_SPECIAL` things, while keeping the released stage14 movement script as
  the no-pickup baseline.
- The executable reports pickup type, removed/kept thing counts, health, armor,
  ammo, owned weapons, ready/pending weapon, psprite state, status-bar pixels,
  weapon-sprite pixels, and final signature.
- The status output visually proves at least one source-shaped inventory or
  weapon-state change.
- It renders a compact bottom status strip and a ready weapon overlay using
  real WAD patch data, with counters for the first status patch and first
  psprite patch drawn.
- Attacks, damage, monster AI, doors/switches, sound playback, automap, menu,
  save/load, networking, and live keyboard gameplay remain absent.

Runtime data added:

- Player inventory/state fields: health, armorpoints, armortype, ammo,
  maxammo, weaponowned, cards, powers, readyweapon, pendingweapon, bonuscount,
  itemcount, secretcount passthrough if needed, damagecount/message fields as
  inert or counted-deferred values, and enough message/item counters for
  deterministic reporting.
- Pickup mutation for bounded map things: picked/removed flags, item counters,
  and no respawn.
- Two `pspdef_t` records and state/lump metadata for ready weapon proof.
- Status-bar patch metadata, palette/colormap reuse, and table-emitted
  patch-column draw commands for a compact, deterministic widget shell.
- Visible counters for unsupported pickup types, skipped powerups, skipped
  weapon actions, deferred messages/sounds, and status/psprite draw overflows.

Implementation notes from release:

- Stage15 started with a Python source-shaped pickup census over the pinned
  WAD, then froze candidate thing indexes, map coordinates, block coordinates,
  and expected before/after player inventory before emitting bytes.
- The released pickups are deterministic and narrow: shotgun plus clip, proving
  weapon grant and separate ammo grant without requiring combat.
- Do not repurpose the stage14 blocking-line probe as an item route. Keep the
  released movement script stable, then select a separate deterministic
  pickup route or MAP01 item probe from the real thing/blockmap data.
- Stage15 enabled `P_TouchSpecialThing` only after stage14 collision was
  stable; pickup debugging stayed separate from first blockmap movement
  debugging.
- Source-shaped psprites prove weapon state/lump setup and movement of psprite
  timers. They do not fire or spawn attacks in this slice.
- The compact status-bar shell uses real status patches and source-shaped
  player values. Full menus, automap, intermission, and finale remain later
  work.
- Sound starts, pickup messages, weapon flashes, and attack states remain
  deferred counters.
- The emitted proof stays small: Python parses WAD patch data and source
  tables, while the executable owns the deterministic state proof, final patch
  draw, and signature path.

Tests added:

- Synthetic `G_PlayerReborn` / `P_SpawnPlayer` tests for initial health, ammo,
  weapon ownership, ready/pending weapon, psprite setup, and stable carry-over
  of stage14 movement fields.
- Synthetic `P_GiveAmmo`, `P_GiveWeapon`, `P_GiveBody`, `P_GiveArmor`, and
  selected key/powerup grant tests.
- Synthetic `P_TouchSpecialThing` tests for pickup acceptance, already-full
  rejection, unsupported type counters, item removal, and deferred
  message/sound accounting.
- Synthetic psprite tests for setup, ready weapon state, pending weapon change,
  timer stepping, and no-fire deferral.
- Synthetic status widget tests for number/icon patch selection and clipped
  patch-column drawing.
- Synthetic patch blit tests for status/weapon patches using the existing
  palette and post/column parsing assumptions.
- Pinned MAP01 pickup reference tests for selected pickup path/probe, thing
  indexes, before/after inventory state, thing removal, status/psprite pixel
  counts, and signature.
- Build/smoke tests verifying preserved stage14 movement/render counters plus
  stage15 pickup/status counters, and confirming monster AI, attacks, doors,
  sound, menus, save/load, networking, and `source_stage16` strings are absent.

Released status:

- The stage15 executable performs a deterministic real pickup proof through
  source-shaped player inventory code.
- Weapon psprite readiness and a compact real-patch status shell are visible
  and counted.
- Stage14 movement/collision remains testable as a baseline.
- Combat, doors/switches, sound, menus, save/load, and networking remain absent
  from the released PE behavior.
- Source trace and smoke docs are updated.

## Released Slice: source_stage16_active_monster_thinkers_and_targeting

Output:

```text
build/source_stage16_active_monster_thinkers_and_targeting.exe
```

Why this slice was needed:

Stage15 proved source-shaped player state mutation and a ready weapon shell,
but it deliberately kept every monster inert. Jumping straight to full combat
would require thinker lists, monster state transitions, target acquisition,
movement, sight checks, weapon firing, damage, deaths, and drops all at once.
That is too much for one honest release. Stage16 first made one real MAP01
monster active and visibly source-shaped, while keeping attacks and damage out
of scope.

Source routines to read and trace/reuse:

- Reuse from stage15: real player inventory, psprite/status shell, movement,
  collision, sector/block thing links, shotgun+clip pickup baseline, and
  deterministic signatures through `S15SIG=2810145191`.
- `p_setup.c`: `P_SetupLevel` counters around `totalkills`, `totalitems`, and
  `P_LoadThings`, only as needed to stop treating all non-player mobjs as inert
  render records.
- `p_tick.c`: `P_InitThinkers`, `P_AddThinker`, `P_RemoveThinker`, and bounded
  `P_Ticker` thinker iteration with mutation while iterating.
- `p_mobj.c`: `P_SpawnMobj`, `P_SpawnMapThing`, `P_SetMobjState`,
  `P_RemoveMobj`, `P_MobjThinker`, and `P_ZMovement` for a small active mobj
  subset.
- `p_enemy.c`: `A_Look`, `P_LookForPlayers`, `A_Chase`, and `P_NewChaseDir`
  only if the selected proof needs a chase step.
- `p_sight.c`: `P_CheckSight` if the selected monster proof needs real
  line-of-sight before target acquisition.
- `p_map.c` / `p_maputl.c`: monster `P_TryMove` / blockmap helpers only for
  bounded chase movement if the selected proof uses it.
- `info.c` / `info.h`: monster spawn, see, chase, and no-attack state metadata
  for the selected monster type.

Released goal:

Introduce the first bounded active monster loop. One real MAP01 monster is
spawned as a real thinker, advances through source-shaped state/tic logic, and
acquires the player as a target. The selected proof reaches the first chase
action and records it as a deferred boundary instead of moving. The executable
reports the changed monster state and `S16SIG=249707937`. It does not fire,
damage anything, kill anything, open doors, play audio, or generalize monster
AI.

User-visible feature:

- A Python source-shaped census selects one real MAP01 monster and records its
  mapthing index, mobj index, type, sprite/state, sector/block position,
  distance to the player, and line-of-sight result.
- The executable reports active thinker count, thinker tics run, selected
  monster identity, state transitions, target acquisition result, sight checks,
  chase deferral, final monster state, preserved stage15 counters, and
  `S16SIG`.
- The renderer/status shell should still show the stage15 player state, while
  the selected monster's source-shaped state change is reflected in sprite
  selection or proof counters.

Implementation notes from release:

- Stage16 started with a source-shaped monster census over the pinned WAD and
  selected shotgun-guy mapthing `37` / mobj `28`, at `(1752,-936)`, sector
  `58`, block `(15,6)`.
- The monster's spawn tics use the source randomization shape and become
  `MTIC0=3`; the source `lastlook=1` behavior means the first `A_Look` call
  does not check player zero, while the second call does.
- The proof uses a bounded REJECT+BSP `P_CheckSight` path that reports
  `SIGHT=1 SOK=1 SNODE=77 SSUB=28 SLINE=5`.
- The clean proof targets the player without requiring movement. Chase movement
  is left for a later slice; the reached `A_Chase` action is recorded as
  `CHDEF=1`.
- Count sound starts, alert propagation, attacks, damage, deaths, drops, sector
  specials, and respawn behavior as deferred. Do not implement them in stage16.
- Keep live keyboard input out; use scripted or fixed proof data as before.

Tests added:

- Synthetic thinker-list initialization, add, deferred remove, and iteration
  tests, including mutation while iterating.
- Synthetic `P_SetMobjState` / `P_MobjThinker` tests for tics, action dispatch,
  state changes, null/removal handling, and bounded action deferral.
- Synthetic `A_Look`, `P_LookForPlayers`, and bounded `P_CheckSight` tests for
  the selected monster proof.
- Pinned MAP01 active-monster reference tests for selected monster identity,
  thinker counts, state/tic sequence, target acquisition, sight counters,
  preserved stage15 counters, and signature.
- Build/smoke tests verifying preserved stage15 counters plus stage16 active
  monster counters, and confirming attacks, damage, doors/switches, audio
  playback, menus, save/load, networking, and `source_stage17` strings are
  absent.

Released status:

- The stage16 executable advances at least one real MAP01 monster through a
  bounded source-shaped thinker/targeting path.
- The selected monster's state or target state changes visibly in counters and
  rendering while stage15 pickup/status behavior remains intact.
- Attacks, damage, deaths, drops, doors/switches, sector specials, audio
  playback, menus, save/load, and networking remain absent.
- Source trace and smoke docs are updated.

## Released Slice: source_stage17_first_weapon_fire_damage_and_death_probe

Output:

```text
build/source_stage17_first_weapon_fire_damage_and_death_probe.exe
```

Goal:

Build on stage16's active monster by proving one deterministic attack/damage
path. The preferred route is a player weapon proof against the selected active
monster after the stage15 shotgun pickup and stage16 target acquisition. The
released stage16 pair is promising but not already aimed: the player probe ends
at `(1824,-680)` with the shotgun owned/ready and `SHELL=8`, the selected
shotgun guy is at `(1752,-936)` with `health=30`, and line of sight is proven,
but the player mobj angle is still `0`. The attack census clarified the paired
bearings: player-to-target is `254` degrees, while target-to-player is `74`
degrees. Stage17 therefore freezes the source-shaped player-to-target attack
angle and proves one bounded damage event rather than a combat system.

Source routines to read and trace/reuse:

- Reuse from stage16: active thinker list, selected monster, target state,
  bounded sight result, blockmap links, stage15 player inventory/status/
  psprites, and deterministic rendering through `S16SIG=249707937`.
- Reuse the concrete stage16 target pair first: player mobj `0` at
  `(1824,-680)`, sector `196` / subsector `633`; shotgun-guy mobj `28` at
  `(1752,-936)`, sector `58` / subsector `620`; `P_CheckSight` already reports
  `SIGHT=1 SOK=1 SNODE=77 SSUB=28 SLINE=5`.
- `p_pspr.c`: `P_CheckAmmo`, `A_WeaponReady`, the selected fire action
  (`A_FirePistol`, `A_FireShotgun`, or another chosen minimal path), flash
  state setup, ammo decrement, and the `P_SetPsprite` transitions needed to
  enter/leave the selected firing state.
- `p_pspr.c`: `P_BulletSlope` and `P_GunShot` if the selected route is pistol
  or shotgun hitscan.
- `p_map.c`: `P_AimLineAttack`, `P_LineAttack`, `PIT_AimLineAttack`, and
  `PIT_LineAttack` for a hitscan proof if selected.
- `p_inter.c`: `P_DamageMobj`, `P_KillMobj`, player/monster damage accounting,
  pain/death state changes, kill count mutation, and item-drop behavior only if
  the selected proof reaches a kill.
- `p_mobj.c`: `P_SetMobjState`, `P_RemoveMobj`, corpse/drop setup, and missile
  spawning only if a hitscan proof is not viable.
- `m_random.c`: deterministic random table use for spread/damage only where
  the selected source path requires it.

User-visible feature:

- The executable reports selected attacker/target, weapon/state, ammo before
  and after, chosen attack angle, target bearing, aim/line traversal counts,
  hit/miss result, damage rolled/applied, target health before/after,
  pain/death/removal/drop counters if reached, psprite state/flash counters,
  updated status pixels, and `S17SIG`.
- Stage17 should still avoid generalized monster AI, monster chase movement,
  doors/switches, sector specials, audio playback, menus, save/load,
  networking, and live input.

Implementation notes:

1. Start with a Python source-shaped attack census over the released stage16
   pair. Record current player angle, target bearing, angle delta, sight result,
   weapon ownership/readiness, ammo, target health, and candidate fire actions.
2. Prefer hitscan before missiles because it avoids projectile thinker lifetime
   and collision breadth. The first candidates should be:
   - current ready shotgun with a deterministic source-shaped aim angle if the
     full `A_FireShotgun` path is still bounded;
   - pistol only if switching/readying it is smaller than shotgun death/drop
     breadth;
   - a documented monster attack probe only if the player weapon path turns out
     less source-faithful for this pinned pair.
3. Do not assume the current player angle hits the selected monster. Either
   advance a tiny scripted aim/fire tic through source-shaped command handling,
   or freeze a documented attack probe angle from the source-shaped census and
   count that as a probe boundary.
4. Keep death/drop optional. A nonlethal damage event is releasable if it
   proves ammo use, line/path participation, deterministic damage mutation, and
   render/status update. If the shortest honest shotgun proof kills the target,
   include only the reached `P_KillMobj` subset and count clip-drop spawning as
   deferred unless it is needed for the signature.
5. Count audio starts, broad alert propagation, recoil/light side effects, and
   unselected weapon families as deferred unless the chosen source path cannot
   be represented without them.

Tests:

- Synthetic attack-census tests for target bearing, aim choice, current-angle
  miss/hit distinction, and no live-input dependency.
- Synthetic ammo/fire/psprite tests for the selected weapon action, flash state
  setup, ammo decrement, no-ammo rejection, and no accidental unsupported
  weapon families.
- Synthetic aim/line attack tests over a bounded blockmap with hit, miss, and
  intercept ordering, including one solid-line block and one shootable-mobj
  intercept.
- Synthetic damage, pain, death, state transition, removal, and optional drop
  tests, scaled to exactly what the pinned proof reaches.
- Pinned MAP01 first-damage reference tests for selected route, attack angle,
  before/after ammo/health/state, hit/damage counters, render/status pixels,
  and signature.
- Build/smoke tests verifying preserved stage16 counters plus stage17 damage
  counters, and confirming doors/switches, sector specials, audio playback,
  menus, save/load, networking, and `source_stage18` strings are absent.

Released status:

- The stage17 executable launches and preserves the full stage16 active-monster
  proof.
- The released route uses the stage15 ready shotgun and selected stage16
  shotgun guy. It reports `CANG=0 AANG=254 TBRG=254 ADEL=254 CMISS=1`,
  `SH0=8 SH1=7`, `HIT17=1 DMG17=10 HP0=30 H17=20`, final state
  `ST17N=S_SPOS_PAIN`, and `S17SIG=2157381017`.
- The bounded path reaches `P_CheckAmmo`, `A_WeaponReady`, `P_SetPsprite`,
  `A_FireShotgun`, `P_BulletSlope`, `P_AimLineAttack`, `P_LineAttack`, and
  `P_DamageMobj`; death/removal/drop stay absent because the selected proof is
  nonlethal.
- Generalized combat, monster chase movement, doors/switches, sector specials,
  audio playback, menus, save/load, networking, live input, and stage18 strings
  remain absent from the stage17 executable.

## Released Slice: source_stage18_post_damage_monster_movement_and_chase_probe

Output:

```text
build/source_stage18_post_damage_monster_movement_and_chase_probe.exe
```

Released goal:

Prove the next honest source-shaped monster movement after stage17. The
released stage17 target is still the selected MAP01 shotgun guy, but it is not
standing cleanly in `S_SPOS_RUN1`: it is alive at health `20`, state
`S_SPOS_PAIN` (`220`), `tics=3`, `target_index=0`, `threshold=100`, and has
post-damage thrust momentum `momx=-22182 momy=-78859`. Source `P_MobjThinker`
services XY momentum before state tic transitions, and the pain path runs
`S_SPOS_PAIN -> S_SPOS_PAIN2 -> S_SPOS_RUN1` before `A_Chase` can move.

Stage18 therefore did not assume a pure chase start. It began with a
post-stage17 monster-movement census and chose the shortest source-faithful
movement proof:

- The reached post-damage `P_XYMovement -> P_TryMove` momentum movement
  produces a real deterministic position/collision mutation, so it is the
  pinned proof.
- Bounded pain recovery to `S_SPOS_PAIN2`/`S_SPOS_RUN1`, `A_Pain`, `A_Chase`,
  `P_NewChaseDir`, `P_Move`, blocked movement, target-loss fallback, and
  attack gates are covered synthetically.
- No fresh pre-damage chase candidate is needed; the post-stage17 path is small
  and source-ordered.

Source routines to read and trace/reuse:

- Reuse from stage17: selected shotgun guy identity, post-damage health/state,
  target, threshold, momentum, sector/block links, and `S17SIG=2157381017`.
- `p_mobj.c`: `P_MobjThinker`, `P_XYMovement`, `P_SetMobjState`, and
  `P_ZMovement` only if the selected route reaches vertical movement.
- `p_enemy.c`: `A_Pain` as a reached sound-only deferral, then `A_Chase`,
  `P_NewChaseDir`, `P_Move`, and melee/missile range checks only as gates.
- `p_map.c` / `p_maputl.c`: monster `P_TryMove`, `P_CheckPosition`,
  `PIT_CheckLine`, `PIT_CheckThing`, `P_BlockLinesIterator`,
  `P_BlockThingsIterator`, `P_SetThingPosition`, and `P_UnsetThingPosition`.
- `info.c` / `info.h`: shotgun-guy pain and run state sequence, speed, radius,
  height, flags, and chase metadata.

User-visible feature:

- The executable reports selected mover/target, start and final position,
  start/final state and tics, post-damage momentum before/after, pain recovery
  steps if reached, move direction/count, tried directions, accepted/rejected
  movement, blocking line/thing counters, sector/block relinks, attack
  deferrals, preserved stage17 counters, and `S18SIG`.
- It does not execute attacks, doors/switches, sector specials, audio playback,
  menus, save/load, networking, or live input. Sound starts and attack choices
  are counted as deferred boundaries.

Implementation notes:

- The released emitter is
  `tools/emit_source_stage18_post_damage_monster_movement_and_chase_probe.py`.
- The stage17 reference world is reused first, then the stage18 movement census
  records state `220`, `tics=3`, target `0`, threshold `100`, momentum
  `(-22182,-78859)`, and block `(15,6)` for the selected monster.
- The proof stays to one selected monster and one `P_MobjThinker` tic. Source
  order services XY momentum before pain-state recovery, calls real MAP01
  `P_TryMove`, accepts the move, relinks block/sector state, applies friction,
  and decrements pain tics.
- The pinned proof does not reach `A_Chase`; melee/missile range checks and
  selected attack states remain deferred in synthetic coverage only.
- Stage17 render/status/damage counters are preserved exactly.

Tests:

- Synthetic post-damage `P_MobjThinker` tests for XY momentum service, pain
  tics, `S_SPOS_PAIN2`, `A_Pain` deferral, and transition back to
  `S_SPOS_RUN1`.
- Synthetic `A_Chase` / `P_NewChaseDir` tests for direction choice, target loss
  fallback, attack gating, and deferred attack actions.
- Synthetic monster `P_TryMove` tests for accepted move, blocked line, blocked
  thing, drop/step limits, and relink accounting.
- Pinned MAP01 movement reference tests for selected monster identity,
  post-stage17 starting state, start/final block position, momentum/chase
  counters, attack deferrals, preserved stage17 counters, and `S18SIG`.
- Build/smoke tests verifying preserved stage17 counters plus stage18 movement
  counters, and confirming doors/switches, sector specials, audio playback,
  menus, save/load, networking, and `source_stage19` strings are absent.

Released status:

- The stage18 executable launches and preserves the full stage17 first-damage
  proof.
- The released route starts with selected shotgun guy mapthing `37`, mobj `28`,
  type `SHOTGUY`, at `(1752,-936)`, state `S_SPOS_PAIN`, `tics=3`, momentum
  `(-22182,-78859)`, target `0`, and threshold `100`.
- One source-shaped `P_MobjThinker` tick reaches
  `P_XYMovement -> P_TryMove -> P_CheckPosition` over real MAP01 blockmap,
  line, thing, sector, and subsector data. The move is accepted with
  `TRY18=1 MACC=1 MREJ=0 MLCHK=8 MTCHK=0`, relinks once, and finishes at
  `(1751,-938)`, block `(15,6)`, state `S_SPOS_PAIN`, `tics=2`, momentum
  `(-20103,-71466)`.
- The proof reports
  `M18R=1 M18TIC=1 XY18=1 PAINTIC=1 P18DEF=0 CH18=0 NCD18=0 PMV18=0 ATK18=0 ATKEX18=0 S18SIG=1615679087`.
- Generalized monster AI, generalized combat, attacks, doors/switches, sector
  specials, sound playback, automap, menus, save/load, networking, live input,
  and stage19 strings remain absent from the stage18 executable.

## Released Slice: source_stage19_first_door_or_switch_sector_special_probe

Output:

```text
build/source_stage19_first_door_or_switch_sector_special_probe.exe
```

Released goal:

Introduce the first bounded environment state change from Doom source behavior,
not a generalized special system. Stage19 starts with a source-shaped MAP01
line/sector special census and picks one honest, small proof. The released
route is a fixed feature probe around a real manual door, not the current
player path: the stage17/stage18 player position is `456` map units from the
selected line, outside `USERANGE=64`, but MAP01 has real manual door lines that
are narrow enough to prove source behavior without broadening movement or live
input.

Released proof:

- MAP01 linedef `332`, special `117` (`EV_VerticalDoor` blazing door raise),
  is activated from the front side by a fixed probe at `(1792,-160)` facing
  east.
- The line is two-sided, has no tag dependency, uses visible `BIGDOOR1`, and
  directly targets sector `56` through `line->sidenum[side^1]`.
- Target sector `56` starts with floor/ceiling `16/16`.
  `P_FindLowestCeilingSurrounding` finds surrounding ceiling `112`, giving
  `topheight=108`.
- One bounded thinker tic mutates the sector ceiling via
  `T_VerticalDoor -> T_MovePlane` from `16` to `24` map units for blazing speed
  (`VDOORSPEED*4 = 8` map units).

Fallbacks if the preferred candidate turns out misleading:

- Use another real manual door, such as paired special `117` lines `165/167`
  or `721/876`, with the same direct-sector door path.
- Use the switch/button door path only if the manual door path is less honest
  than expected. The current MAP01 census has a tag-based switch/button door
  candidate at linedef `839`, special `103`, tag `4`, targeting sector `208`,
  but that also pulls in `P_ChangeSwitchTexture` and switch-list behavior.
- Keep crossing specials, scrolling lines, floor/plat specials, exit lines, and
  sector damage/light specials deferred unless the chosen door proof cannot be
  represented honestly without them.

The proof mutates one line/sector/thinker state and reports deterministic
counters while preserving stage18 movement and stage17 damage.

Source routines to read and trace/reuse:

- `p_map.c`: `P_UseLines` and its `P_PathTraverse` use-line path, with a
  scripted fixed probe rather than live input.
- `p_switch.c`: `P_UseSpecialLine` dispatch, but only the selected manual-door
  case should be active in the pinned proof.
- `p_doors.c`: `EV_VerticalDoor`, `T_VerticalDoor`, door type/speed/topwait
  setup, and direct back-sector selection for manual doors.
- `p_floor.c`: `T_MovePlane` for ceiling mutation and bounded crush/block
  accounting.
- `p_spec.c`: `P_SpawnSpecials` only as a census/deferred baseline unless the
  selected proof needs line animations or button restoration. `P_UpdateSpecials`
  should stay mostly deferred for stage19.
- `p_maputl.c`: `P_PathTraverse`/intercept ordering for use-line reach, reusing
  the stage17 hitscan traversal shape where practical.
- `p_switch.c`: `P_ChangeSwitchTexture`, `P_StartButton`, and button timer
  restoration only in synthetic tests or if a switch fallback becomes the
  pinned proof.

User-visible feature:

- The executable reports selected special line, probe position/angle,
  front/back side result, target sector, sector floor/ceiling before and after,
  computed top height, door type/speed/direction/topwait, spawned thinker count,
  bounded `T_VerticalDoor`/`T_MovePlane` tic count, line/path/intercept counts,
  sound/button/switch deferrals, preserved stage18/stage17 counters, and
  `S19SIG`.
- It does not implement generalized map progression, all special types,
  keyed-door inventory policy beyond synthetic guards, switch animation lists
  beyond the chosen proof, audio playback, menus, save/load, networking, or live
  input.

Implementation notes:

- The released emitter is
  `tools/emit_source_stage19_first_door_or_switch_sector_special_probe.py`.
- The census covers real MAP01 linedefs, sectors, sidedefs, tags, and special
  types, and records why a fixed feature probe is used: the existing stage18
  player position is not within `USERANGE` of the chosen line.
- Reuse the stage18 executable structure and preserved title/status counters.
  Do not disturb the stage18 monster movement proof.
- Build only the selected door data needed for line `332`/`330` or the selected
  fallback: line flags/special/sides, target sector, surrounding-sector ceiling
  search, and one door thinker record.
- Treat `S_StartSound`, allocation tags, and broad thinker memory management as
  counted deferrals. The emitted PE can table-emit one door thinker record
  rather than generalizing `Z_Malloc`.
- Keep the first proof to one activation and a tiny number of thinker tics.
  One post-activation `T_VerticalDoor` tic is releasable if it mutates the
  sector ceiling through `T_MovePlane` and reports the computed top height.
- Synthetic coverage may include locked-door rejection, use through a blocking
  nonspecial line, already-active `specialdata`, switch/button texture
  deferral, and a tag-based `EV_DoDoor` fallback. Keep the pinned proof to one
  manual door unless the census proves otherwise.

Tests:

- Synthetic use-line/path tests for front-side activation, back-side rejection,
  blocked nonspecial line, no-special pass-through, and one-special-only
  traversal termination.
- Synthetic `EV_VerticalDoor` tests for manual door spawn, locked-door
  rejection, already-active door direction handling, computed top height, and
  sound deferral.
- Synthetic `T_VerticalDoor` / `T_MovePlane` tests for first upward ceiling
  mutation, past-destination behavior, wait-at-top setup, and crush/block
  accounting.
- Synthetic switch/button tests should prove `P_ChangeSwitchTexture` and
  `P_StartButton` are either deferred or bounded fallback behavior, not a
  generalized switch system.
- Pinned MAP01 reference tests for selected line/sector identity, activation
  route, topheight, before/after ceiling mutation, preserved stage18/stage17
  counters, and `S19SIG`.
- Build/smoke tests verifying preserved counters plus stage19 special counters,
  and confirming audio playback, menus, save/load, networking, live input, and
  `source_stage20` strings are absent.

Released status:

- The stage19 executable launches and preserves the full stage18 post-damage
  monster movement proof and stage17 first-damage proof.
- The released use route reports
  `S19LINE=332 SIDE=0 S19SEC=56 S19SPEC=117 S19TEX=BIGDOOR1 PROBE19=1 U19X=1792 U19Y=-160 U19A=0 P18USE=0 P18DIST=456`.
- The bounded line traversal reports
  `PATH19=1 BLK19=1 LI19=5 TRV19=1 USE19=1 BACK19=0 TERM19=1`.
- The manual door proof spawns one table-emitted door thinker with
  `VD19=1 DTH19=1 TOP19=108 F19=16 C190=16 C191=24 DIR19=1 SPD19=8 TWAIT19=150 TD19=1 MP19=1 MPR19=0`.
- Switch/button behavior, broad special dispatch, broad door/switch systems,
  broad sector effects, real sound output, and live input remain counted as
  absent or deferred:
  `SWDEF19=0 BTNDEF19=0 GSPEC19=0 GDOOR19=0 GSECT19=0 AUD19=1 LIVE19=0`.
- The released signature is `S19SIG=2088411722`.

## Released Slice: source_stage20_audio_channels_and_deferred_sound_playback

Output:

```text
build/source_stage20_audio_channels_and_deferred_sound_playback.exe
```

Released goal:

Realize the first bounded sound-start behavior after many stages counted
sound as a deferral. This is still not generalized audio playback and not an
OS/device mixer slice. Stage20 preserves stage19 and converts the reached
manual-door sound boundary from `EV_VerticalDoor` into
source-shaped `S_StartSound` channel state:

- Selected source call site: stage19 manual blazing door line `332`, special
  `117`, sector `56`, `S_StartSound(&sec->soundorg, sfx_bdopn)`.
- Selected sound metadata: `sounds.h` enum `sfx_bdopn`, `sounds.c` entry
  `SOUND("bdopn", 100)`.
- Selected runtime state: a bounded channel array equivalent to
  `snd_channels=8`, one channel mutation, deterministic pitch/volume/separation
  accounting, and a counted `I_StartSound` playback deferral.
- Preserve stage19's `AUD19=1` as the old boundary and add explicit stage20
  sound-state counters that prove the boundary has become real source-shaped
  state.

Source routines to read and trace/reuse:

- `s_sound.c`: `S_Init` channel setup shape, but table-emit or statically emit
  the bounded channel records rather than generalizing `Z_Malloc`.
- `s_sound.c`: `S_StartSound`, including bogus-sfx guard, linked-sfx volume and
  pitch handling, audibility branch, pitch variation branch, `S_StopSound`,
  `S_GetChannel`, usefulness/lump bookkeeping, and the final `I_StartSound`
  boundary.
- `s_sound.c`: `S_GetChannel`, `S_StopSound`, and `S_StopChannel` for free
  channel choice, same-origin replacement, priority replacement, and duplicate
  usefulness accounting.
- `s_sound.c`: `S_AdjustSoundParams` only as far as the selected sector origin
  requires. If the stage19 door `soundorg` has no full mobj position yet, first
  run a Python census of sector `soundorg` setup and either emit the minimal
  origin fields or document a centered-origin fallback with a deferral counter.
- `sounds.c` / `sounds.h`: `S_sfx` metadata and enum id for `sfx_bdopn`.
- `p_doors.c`: stage19 `EV_VerticalDoor` manual-door sound call site,
  preserving selected origin and sound id.
- `m_random.c`: deterministic `M_Random` pitch variation if the selected sound
  reaches the normal pitch-randomization branch.
- `i_sound.c` / Chocolate Doom platform glue only as a boundary reference.
  Stage20 does not open a sound device or play speaker audio.

User-visible feature:

- The executable reports selected sound id/name/lump name, source call site,
  origin class, channel count, chosen channel index, same-origin stop count,
  priority replacement result, usefulness before/after, lump lookup deferral,
  pitch before/after, volume, separation, final `I_StartSound` deferral,
  preserved stage19/stage18/stage17 counters, and `S20SIG`.
- Actual speaker playback remains deferred. A releasable stage20 is
  deterministic sound-channel state mutation and source-shaped channel
  selection, not a finished sound mixer.

Implementation notes:

1. Start by reading `s_sound.c`, `sounds.h`, `sounds.c`, `p_doors.c`, and the
   sector `soundorg` setup path used by loaded sectors.
2. Preserve the exact stage19 manual-door proof before changing the audio
   boundary. The selected door still mutates sector `56` from `16` to `24` in
   the same first thinker tic.
3. Keep the emitted runtime bounded to the selected `sfx_bdopn` door-open
   call. Do not generalize music, all sound effects, all active origins, sound
   caching, lump decoding, resampling, or a platform audio backend.
4. Count `I_GetSfxLumpNum`, sound data caching, `I_StartSound`, `I_StopSound`,
   and device playback as explicit deferrals unless the selected channel-state
   proof cannot be represented without a tiny stub value.
5. Synthetic coverage should exercise replacement and rejection branches, but
   the pinned MAP01 proof should start from an empty channel table and fill one
   deterministic channel.

Tests:

- Synthetic `S_StartSound` tests for bogus id rejection, linked-sfx volume/pitch
  handling, same-origin stop, free-channel selection, priority replacement,
  no-channel rejection, normal pitch randomization, and no-device playback
  deferral.
- Synthetic `S_AdjustSoundParams` tests for same-origin normal separation,
  audible near source, clipped far source, and volume/separation math if the
  selected proof reaches positional attenuation.
- Pinned MAP01 stage20 reference test for the stage19 door sound boundary
  becoming deterministic channel state for `sfx_bdopn`.
- Build/smoke test verifying preserved stage19 counters plus sound-channel
  counters, and confirming menus, save/load, networking, live input, and
  `source_stage21` strings are absent.

Definition of done:

- `build/source_stage20_audio_channels_and_deferred_sound_playback.exe` exists.
- It launches, preserves stage19 exactly, and reports deterministic `S20SIG`.
- The selected `sfx_bdopn` sound-start call mutates one source-shaped channel
  record without real audio playback.
- Generalized audio playback, music, menus, automap, save/load, networking,
  live input, broader special systems, and stage21 remain absent.

Released status:

- The stage20 executable launches and preserves the full stage19 manual-door
  sector mutation proof, stage18 post-damage movement proof, and stage17
  first-damage proof.
- The selected sound metadata is source-parsed as `sfx_bdopn`, source enum id
  `88`, name `bdopn`, priority `100`.
- Sector `56`'s sound origin is computed from the source `P_GroupLines`
  centered bounding-box rule as `(1832,-160)`, with the fixed stage19 use probe
  `(1792,-160)` acting as the listener for this bounded proof.
- The released sound-channel signal is:
  `S20CALL=1 S20LINE=332 S20SEC=56 S20ID=88 S20N=bdopn S20PRI=100 CHS20=8 CH20=0 ORG20=56 O20X=1832 O20Y=-160 L20X=1792 L20Y=-160 DIST20=40 VOL20=64 SEP20=129 P200=127 RND20=8 P201=135 STOP20=1 SAME20=0 GET20=1 FREE20=1 REP20=0 NOCH20=0 USE200=-1 USE201=1 LDEF20=1 LUMP20=0 IST20=1 H20=0 PLAY20=0 AUD20=1 MIX20=0 MUS20=0 ALLS20=0 CACH20=0 S20SIG=3226031347`.
- The emitted runtime starts from an empty bounded 8-channel table, fills
  channel `0` with `sfx_bdopn`, origin id `1056`, pitch `135`, handle `0`, and
  leaves actual platform playback absent.

## Released Slice: source_stage21_door_thinker_ticker_and_special_update_probe

Output:

```text
build/source_stage21_door_thinker_ticker_and_special_update_probe.exe
```

Released goal:

After stage20 makes the reached sound boundary real as channel state, reconnect
the selected manual door thinker to a bounded source-shaped game tic. Stage19
remains preserved exactly, including its direct one-tic
`T_VerticalDoor -> T_MovePlane` proof. Stage21 adds an isolated normal-ticker
proof using a cloned copy of the same post-activation door state, without
rewriting the stage19/stage20 path underneath it.

The pinned proof starts from the stage19 selected door immediately after
`EV_VerticalDoor` has created it: sector `56`, ceiling `16`, topheight `108`,
direction `1`, speed `8`, topwait `150`. Two bounded ticker tics prove
`P_Ticker -> P_RunThinkers -> T_VerticalDoor -> T_MovePlane` with source-order
leveltime accounting and produce the continuation `16 -> 24 -> 32` without
reaching wait-at-top, closing, removal, switch animation, or button restoration.

Source routines to read and trace/reuse:

- `p_tick.c`: `P_InitThinkers`, `P_AddThinker`, `P_RunThinkers`, lazy
  `P_RemoveThinker`, and the relevant `P_Ticker` order.
- `p_doors.c`: `T_VerticalDoor` continuing the same blazing door from stage19,
  including wait-at-top setup if the bounded tic count reaches the top.
- `p_floor.c`: `T_MovePlane` for repeated ceiling mutation and past-destination
  handling.
- `p_spec.c`: `P_UpdateSpecials` as a deliberately bounded pass: level timer,
  global flat/texture animation, scrolling line specials, and button restore
  behavior should remain counted absent unless the selected proof reaches them.
- `p_mobj.c` / `p_user.c`: the player-think portion of `P_Ticker` should be an
  explicit no-op/deferred guard for this isolated door proof. Do not broaden
  live input, local movement, monster AI, or combat in this slice.
- `s_sound.c`: preserve the stage20 channel-state proof; do not start new sound
  playback or expand sound effects during the ticker proof.

User-visible feature:

- The executable reports preserved stage20/stage19 counters, thinker-list
  setup, one selected door thinker node, bounded `P_Ticker` count,
  `P_RunThinkers` iteration count, door-function dispatch count, repeated
  ceiling heights, leveltime before/after, `P_UpdateSpecials` no-op/deferred
  counters, player-think guard counters, and `S21SIG`.
- It still avoids generalized specials, all door/switch types, animated
  texture systems, button restoration, music, real audio playback, menus,
  automap, save/load, networking, and live input.

Implementation notes:

1. Preserve stage20 and stage19 exact counters/signatures. Stage21 adds a new
   cloned ticker proof instead of moving stage19's direct door tic.
2. Table-emit a bounded `thinkercap` plus one selected door thinker node. This
   is the first normal thinker-list ownership proof for a map special, not a
   general allocator or arbitrary thinker system.
3. Keep `P_Ticker` source order visible: pause/menu guards, player-think guard,
   `P_RunThinkers`, `P_UpdateSpecials`, `P_RespawnSpecials` deferral, and
   `leveltime++`.
4. Keep `P_UpdateSpecials` present but empty for the pinned door run. Texture
   animation, scrolling lines, level timer exits, and button restore should be
   counted as absent/deferred, setting up the following switch/button work.
5. Include synthetic coverage for lazy removal and top/wait transitions, but
   keep the pinned proof to the safe upward movement window unless the census
   shows a smaller honest path.

Tests:

- Synthetic thinker-list tests for add order, removal marker handling,
  next-pointer safety while a thinker mutates/removes itself, and bounded
  iteration counts.
- Synthetic door ticker tests for repeated upward movement, exact top clamp,
  wait-at-top setup, and no accidental close/reopen unless the bounded tic count
  intentionally reaches it.
- Synthetic `P_UpdateSpecials` guard tests proving animations, scroll specials,
  buttons, and level exits are absent or counted deferred in the pinned proof.
- Pinned MAP01 stage21 reference test preserving the selected sector `56` door
  state and proving it advances through `P_Ticker` rather than a direct door
  call.

Released status:

- The stage21 executable launches and preserves the full released stage20
  sound-channel proof, stage19 manual-door mutation proof, stage18
  post-damage movement proof, and stage17 first-damage proof.
- The selected cloned ticker state is sector `56`, type `vld_blazeRaise`,
  ceiling `16`, topheight `108`, direction `1`, speed `8`, and topwait `150`.
- The bounded ticker proof reports:
  `S21SEC=56 CAP21=1 ADD21=1 NODE21=1 LNK21=4 PTIC21=2 RUN21=2 ITER21=2 DISP21=2 NEXT21=2 TVD21=2 MP21=2 C210=16 C211=24 C212=32 TOP21=108 SPD21=8 DIR21=1 WAIT21=150 TCNT21=0 PLY21=2 UPD21=2 RESP21=2 LT210=0 LT211=2 ORDER21=1 PAUSE21=0 MENU21=0 ANIM21=0 SCRL21=0 BTN21=0 EXIT21=0 REM21=0 CLOSE21=0 SND21=0 AUD21=0 MIX21=0 MUS21=0 LIVE21=0 S21SIG=1770773845`.
- Synthetic tests cover thinker cap initialization, append order, dispatch,
  lazy removal, next-pointer safety, bounded iteration limits, repeated upward
  door movement, exact top clamp/wait setup, open-door removal, pause/menu
  ticker guards, and `P_RunThinkers` before `P_UpdateSpecials`.
- Generalized specials, generalized doors/switches, switch texture mutation,
  button restoration, generalized sector effects, live input, menus, automap,
  save/load, networking, music, real audio playback, mixer/device playback, and
  reusable button behavior remain outside the stage21 emitted runtime.

## Released Slice: source_stage22_first_switch_texture_and_tagged_door_probe

Output:

```text
build/source_stage22_first_switch_texture_and_tagged_door_probe.exe
```

Released goal:

After stage21 makes the normal ticker path real enough to carry map-special
thinkers, add the first source-shaped switch texture mutation and tagged-door
activation. Re-checking the pinned `MAP01` candidate after stage21 confirms the
next slice is still accurate: real linedef `839` has special `103`, tag `4`,
front/right sidedef `1289`, and lower texture `SW2COMP`; the only tagged sector
is sector `208`. The source route is
`P_UseLines -> P_UseSpecialLine -> EV_DoDoor(line, vld_open) ->
P_ChangeSwitchTexture(line, 0)`, followed by one bounded ticker tic for the
new tagged door thinker.

This should be a bounded real-map switch proof, not a generalized switch,
button, or tagged-special system. The pinned route should prove one tag lookup,
one selected sector door thinker spawn for tag `4`, one switch texture pair
change `SW2COMP -> SW1COMP` through the source `switchlist`, and one normal
door-open ticker movement for sector `208` from ceiling `-80` to `-78`.
Button timers/restoration stay out of the pinned stage22 proof because
`P_ChangeSwitchTexture(line, 0)` clears the one-shot switch and never calls
`P_StartButton`.

Pinned data checked for stage22:

- Linedef `839`: special `103`, tag `4`, side `0`, right sidedef `1289`, left
  sidedef `1290`.
- Right/front sidedef `1289`: sector `152`, top `-`, middle `-`, lower
  `SW2COMP`; source slot to mutate is bottom/lower.
- Tag `4` resolves only to sector `208`, with floor `-80`, ceiling `-80`,
  special `0`.
- `P_FindLowestCeilingSurrounding(sector 208)` reaches neighboring ceiling `0`,
  so `EV_DoDoor(vld_open)` sets topheight to `-4`, direction `1`, speed `2`,
  and topwait `150`.
- A one-tic ticker after spawn should move the tagged door ceiling
  `-80 -> -78`; it should not reach wait-at-top, removal, or button restore.

Source routines to read and trace/reuse:

- `p_switch.c`: `P_InitSwitchList`, `P_UseSpecialLine` case `103`,
  `P_ChangeSwitchTexture`, switch texture pair lookup, and the one-shot
  `useAgain=0` behavior that clears the line special.
- `p_doors.c`: `EV_DoDoor` tagged-door open path, but only for the selected
  tag `4` candidate and `vld_open` door type.
- `p_spec.c`: `P_FindSectorFromLineTag` for bounded tag iteration.
- `r_data.c`: texture name/id resolution already exists; reuse it for
  switchlist entries rather than inventing a separate texture table.
- `s_sound.c`: switch sound should remain a counted boundary or a tiny reuse of
  the stage20 sound-start proof if that stays bounded. Do not turn this into
  broad audio.
- `p_tick.c`: reuse the stage21 bounded thinker/ticker path for one post-spawn
  `vld_open` door tic, preserving the existing cloned stage21 door proof.

User-visible feature:

- The executable reports preserved stage21/stage20 counters, selected switch
  line/special/tag/sidedef, switch texture before/after, switchlist pair index,
  line special before/after, selected tagged sector/door fields, tag iteration
  counts, one ticker movement for the tagged sector door, switch sound
  deferral/channel guard counters, and `S22SIG`.
- It still avoids reusable button timers/restoration in the pinned proof unless
  a real clean MAP01 button candidate contradicts the current census.
  `P_StartButton` and buttonlist restoration should be synthetic coverage only
  in stage22, then become the focus of stage23.

Tests:

- Synthetic switchlist tests for Doom II pair availability, top/middle/bottom
  texture matching, no-match no-op, one-shot `line->special=0`, and reusable
  button `P_StartButton` guard behavior.
- Synthetic tag-door tests for one matching sector, no matching sector,
  already-active sector skip, and multiple tagged sectors without generalizing
  all door types.
- Synthetic `P_ChangeSwitchTexture` tests proving `SW2COMP -> SW1COMP` and
  switch sound boundary/deferred channel behavior.
- Synthetic ticker tests proving the newly spawned `vld_open` door advances one
  tic and does not remove, close, or reopen.
- Pinned MAP01 reference tests for linedef `839`, special `103`, tag `4`,
  sidedef `1289`, lower texture `SW2COMP`, switch pair mutation to `SW1COMP`,
  line special clear, selected sector `208` door spawn, first ticker movement
  `-80 -> -78`, preserved stage21 counters, and deterministic `S22SIG`.

Released status:

- The stage22 executable launches and preserves the released stage21, stage20,
  and stage19 signals.
- The selected real line is `839`, special `103`, tag `4`, side `0`, right
  sidedef `1289`, left sidedef `1290`, with front lower texture `SW2COMP`.
- Source switchlist lookup resolves pair `6`, switchlist index `13`, and
  mutates `SW2COMP -> SW1COMP`; one-shot activation clears the line special
  from `103` to `0`.
- Tag `4` resolves only to sector `208`; the selected sector starts with floor
  `-80`, ceiling `-80`, special `0`, reaches neighboring ceiling `0`, and
  spawns a `vld_open` door with topheight `-4`, direction `1`, speed `2`, and
  topwait `150`.
- One bounded ticker tic advances the tagged door ceiling from `-80` to `-78`
  through the stage21 thinker/ticker path.
- The released stage22 signal is:
  `S22LINE=839 S22SPEC=103 TAG22=4 SIDE22=0 RSID22=1289 LSID22=1290 SLOT22=2 TEX220=SW2COMP TEX221=SW1COMP PAIR22=6 SWI22=13 SPC221=0 PATH22=1 LI22=7 TRV22=2 EV22=1 TFIND22=1 TITER22=211 TSEC22=208 F22=-80 C220=-80 LOW22=0 TOP22=-4 DIR22=1 SPD22=2 WAIT22=150 ADD22=1 PTIC22=1 TVD22=1 MP22=1 C221=-78 UPD22=1 BTN22=0 REM22=0 CLOSE22=0 SWSND22=1 AUD22=0 GEN22=0 S22SIG=2207028069`.
- Synthetic tests cover switchlist top/middle/bottom matching, no-match
  one-shot clear, duplicate/free button guards, one/no/active/multiple tagged
  sectors, switch sound boundary behavior, and ticker no removal/close/reopen.
- Generalized specials, generalized switches, generalized doors, floors,
  plats, reusable button restoration, live input, menus, automap, save/load,
  networking, music, real audio playback, mixer/device playback, and stage23
  remain outside the emitted runtime.

## Released Slice: source_stage23_first_button_timer_restore_probe

Output:

```text
build/source_stage23_first_button_timer_restore_probe.exe
```

Goal:

After stage22 proves one-shot switch texture mutation and tagged-door spawn,
prove the reusable-button half of `P_ChangeSwitchTexture`: `useAgain=1`,
`P_StartButton`, countdown in `P_UpdateSpecials`, texture restoration, and the
button sound boundary. The stage22 follow-up census still found no clean MAP01
reusable button line whose front-side texture is a source `switchlist` pair, so
forcing MAP01 would be less honest than using a real secondary-map candidate.
The broader pinned IWAD census found `72` reusable button-special lines with
switchlist textures; `8` of those are door-only button specials. Stage23 should
therefore use a real secondary-map candidate and table-emit only the bounded
candidate metadata needed for the proof.

Pinned candidate to validate first:

- Map `MAP15`, linedef `3452`, special `61` (`EV_DoDoor(line, vld_open)` plus
  `P_ChangeSwitchTexture(line, 1)`), tag `24`.
- Front/right sidedef `4798`, one-sided line, front sector `548`, middle
  texture `SW1COMP`.
- Source switch pair `SW1COMP -> SW2COMP` is pair `6`; press mutates the middle
  texture to `SW2COMP`, stores old texture `SW1COMP` in the button slot, and
  does not clear the line special because `useAgain=1`.
- Tag `24` resolves to sector `530`, floor `-64`, ceiling `48`, special `0`;
  surrounding ceiling `56` gives `vld_open` topheight `52`, direction `1`,
  speed `2`, and topwait `150`.
- The button timer should start at `BUTTONTIME=35`. A bounded ticker run should
  decrement it through `P_UpdateSpecials`, restore the middle texture to
  `SW1COMP` on zero, emit/count the `sfx_swtchn` boundary, and clear the button
  slot. Door movement may complete during the run, but generalized door systems
  and later map progression remain outside the slice.

Fallback if the pinned MAP15 candidate exposes an unexpected mismatch during
implementation: use the stage22 `SW2COMP/SW1COMP` pair as an explicitly
synthetic `buttonlist`/timer proof, but only after documenting the real-candidate
failure. The preferred release remains a real secondary-map button candidate.

This slice should not implement generalized plats/floors, all reusable button
specials, all switch texture pairs at runtime, exits, live input, or broad
audio. Its job is to make the source button timer lifecycle real enough for
later map interaction.

Source routines to read and trace/reuse:

- `p_switch.c`: `P_ChangeSwitchTexture(line, 1)`, texture-slot detection,
  `P_StartButton`, duplicate-button guard, button slot allocation, and
  `BUTTONTIME`.
- `p_spec.c`: the `P_UpdateSpecials` button loop, `btimer--`, texture
  restoration by `where`, `S_StartSound(&buttonlist[i].soundorg, sfx_swtchn)`,
  and `memset(&buttonlist[i], 0, sizeof(button_t))`.
- `p_tick.c`: preserve stage21/source-order `P_Ticker` so button restoration
  happens after thinkers and before `leveltime++`.
- `s_sound.c`: keep switch-on/switch-off sound starts as bounded channel-state
  reuse or counted deferrals; do not implement speaker playback.

User-visible feature:

- The executable reports preserved stage22/stage21 counters, selected button
  source, secondary-map marker, linedef/special/tag/sidedef, texture slot,
  texture before/pressed/restored, button slot index, timer start/end,
  duplicate-button guard result, `P_UpdateSpecials` restoration count, selected
  tagged door fields if the MAP15 route stays valid, switch sound
  deferral/channel counters, and `S23SIG`.
- It should prove exactly one button lifecycle and leave broad buttons,
  generalized line specials, exits, floors/plats, and audio output deferred.

Tests:

- Synthetic `P_StartButton` tests for duplicate line rejection, free-slot
  allocation, full-list error boundary, and top/middle/bottom restore slots.
- Synthetic `P_UpdateSpecials` tests for no-op inactive buttons, countdown,
  exact restore-on-zero behavior, sound boundary, and slot clearing.
- Real-candidate census test proving MAP01 has no clean natural reusable
  switch-texture button while the pinned IWAD contains the selected MAP15
  candidate.
- Pinned MAP15 reference test proving `SW1COMP -> SW2COMP -> SW1COMP`,
  `P_StartButton` slot state, `P_UpdateSpecials` timer countdown/restoration,
  preserved stage22/stage21 signals, and deterministic `S23SIG`.

Definition of done:

- `build/source_stage23_first_button_timer_restore_probe.exe` exists.
- It launches, preserves stage22/stage21/stage20/stage19 signals, and reports
  deterministic `S23SIG`.
- A real reusable button candidate mutates a switch texture, starts a button
  timer, restores the texture through the source `P_UpdateSpecials` loop, and
  clears the button slot.
- Speaker playback, generalized specials, all floors/plats, live input, map
  progression, menus, automap, save/load, networking, and stage24 remain
  deferred.

Released status:

- The stage23 executable launches and preserves the released stage22, stage21,
  stage20, and stage19 signals.
- The selected real button line is `MAP15` linedef `3452`, special `61`, tag
  `24`, side `0`, right sidedef `4798`, left sidedef `65535`, front sector
  `548`, with front middle texture `SW1COMP`.
- Source switchlist lookup resolves pair `6`, switchlist index `12`, and
  mutates `SW1COMP -> SW2COMP`; reusable activation preserves the line special
  as `61`.
- `P_StartButton` allocates slot `0`, stores old texture id `292` /
  `SW1COMP`, starts timer `35`, and duplicate-line start returns the counted
  guard result `-1`.
- Tag `24` resolves only to sector `530`; the selected sector starts with floor
  `-64`, ceiling `48`, special `0`, reaches neighboring ceiling `56`, and
  spawns a `vld_open` door with topheight `52`, direction `1`, speed `2`, and
  topwait `150`.
- Thirty-five bounded ticker/update-special tics decrement the button timer to
  zero, restore the middle texture to `SW1COMP`, count one switch-off sound
  boundary, and clear the button slot. The open door reaches its top and is
  lazily removed during the same bounded run.
- The released stage23 signal is:
  `S23MAP=15 S23LINE=3452 S23SPEC=61 TAG23=24 SIDE23=0 RSID23=4798 LSID23=65535 FSEC23=548 SLOT23=1 TEX230=SW1COMP TEX231=SW2COMP TEX232=SW1COMP PAIR23=6 SWI23=12 SPC231=61 BSLOT23=0 BOLD23=292 BT230=35 BT231=0 BDUP23=-1 UPD23=35 BDEC23=35 BREST23=1 BCLR23=1 BOFFSND23=1 TSEC23=530 F23=-64 C230=48 LOW23=56 TOP23=52 DIR23=1 SPD23=2 WAIT23=150 PTIC23=35 TVD23=3 MP23=3 REM23=1 LT23=35 ORDER23=1 MAP01BTN23=0 CENS23=72 DOORBTN23=8 AUD23=0 GEN23=0 FALL23=0 S24ABS=1 S23SIG=3216085132`.
- Synthetic tests cover duplicate button rejection, free-slot allocation,
  full-list error boundary, top/middle/bottom restore slots, inactive button
  update no-op, countdown, exact restore-on-zero, switch-off sound boundary,
  slot clearing, and `P_ChangeSwitchTexture(line, 1)` preservation of line
  special.
- Generalized specials, generalized switch systems, generalized doors,
  generalized floors/plats, live keyboard input, menus, automap, save/load,
  networking, music, mixer/device playback, real speaker playback, map
  progression, and stage24 remain outside the emitted runtime.

## Released Slice: source_stage24_first_floor_sector_special_probe

Output:

```text
build/source_stage24_first_floor_sector_special_probe.exe
```

Goal:

After stage23 makes reusable button timers real, broaden sector movement beyond
doors by selecting exactly one floor special from a real map candidate. Re-check
of the stage23 reusable switch-texture census shows that floor movement should
come before platforms: `EV_DoFloor -> T_MoveFloor -> T_MovePlane` adds a
`floormove_t` record and the floor half of the already familiar plane mover,
without yet needing `plat_t`, `activeplats[]`, wait states, or in-stasis
management.

Pinned candidate to validate first:

- Map `MAP11`, linedef `391`, special `60` (`EV_DoFloor(line,
  lowerFloorToLowest)` plus `P_ChangeSwitchTexture(line, 1)`), tag `6`.
- Front/right sidedef `564`, one-sided line, front sector `59`, middle texture
  `SW1BROWN`.
- Source switch pair should mutate `SW1BROWN -> SW2BROWN` on press, preserve
  line special `60`, allocate one button slot, and later restore `SW1BROWN`
  through the stage23 button timer path.
- Tag `6` resolves to one sector, sector `57`, with floor `16`, ceiling `144`,
  special `0`.
- `P_FindLowestFloorSurrounding(sector 57)` reaches `-48`, so
  `EV_DoFloor(lowerFloorToLowest)` sets direction `-1`, speed `FLOORSPEED=1`,
  and `floordestheight=-48`.
- Run a bounded ticker window long enough to prove repeated `T_MoveFloor ->
  T_MovePlane` floor mutation and past-destination removal. Because the source
  uses a strict `< dest` check, the floor reaches `-48` on tic `64`, then the
  following tic fires the `pastdest` completion, `P_RemoveThinker`, and pstop
  boundary; one more ticker pass proves the lazy thinker unlink. The button
  timer still restores at tic `35`.

Fallback if this candidate exposes an implementation mismatch: choose the next
single-tag, reusable, switch-texture floor-lower candidate from the same census
(`MAP11` line `533` or `716`) and document the rejected candidate explicitly.
Do not silently fall back to a synthetic floor proof.

Scope:

- Reuse the stage23 button/switch/ticker scaffolding where practical.
- Port only the selected `EV_DoFloor(lowerFloorToLowest)` path and one selected
  `floormove_t` thinker/state record.
- Add the floor branch of `T_MovePlane`, preserving source past-destination
  clamp and `P_ChangeSector` boundary accounting.
- Run a bounded ticker window that proves one real sector floor height mutation,
  button restoration, `T_MoveFloor` completion, `P_RemoveThinker`, and `sfx_pstop`
  as a deferred sound boundary.
- Preserve stage23/stage22 signals and keep live input, map progression, real
  speaker output, menus, automap, save/load, networking, platforms, ceilings,
  stairs, crushers, floor texture-change families, and generalized WAD
  compatibility deferred.

Validation shape:

- Synthetic tests for floor thinker setup, down movement, exact
  past-destination clamp, inactive-sector skip, nofit/crush boundary behavior,
  deferred move/pstop sounds, and preservation of the stage23 button lifecycle.
- Pinned real-map test for the chosen line, switch texture/button state if
  reused, selected sector floor sequence, bounded ticker count, floor thinker
  removal, and deterministic `S24SIG`.
- Build/smoke test that launches the emitted PE and proves preserved
  stage23/stage22 signals plus the new floor movement signal.

Released status:

- The stage24 executable launches and preserves the released stage23, stage22,
  stage21, stage20, and stage19 signals.
- The selected real floor line is `MAP11` linedef `391`, special `60`, tag `6`,
  side `0`, right sidedef `564`, left sidedef `65535`, front sector `59`, with
  front middle texture `SW1BROWN`.
- Source switchlist lookup resolves pair `4`, switchlist index `8`, and mutates
  `SW1BROWN -> SW2BROWN`; reusable activation preserves line special `60`.
- `P_StartButton` allocates slot `0`, starts timer `35`, and the stage23
  `P_UpdateSpecials` path restores `SW1BROWN` and clears the slot.
- Tag `6` resolves only to sector `57`; the selected sector starts with floor
  `16`, ceiling `144`, special `0`, and `P_FindLowestFloorSurrounding` reaches
  destination `-48`.
- Sixty-six bounded ticker calls prove `T_MoveFloor` dispatches `65` times,
  mutates the floor on `64` downward steps, clamps at `-48`, marks/removes the
  floor thinker at the strict past-destination boundary, and lazily unlinks the
  thinker on the final ticker pass.
- The released stage24 signal is:
  `S24MAP=11 S24LINE=391 S24SPEC=60 TAG24=6 SIDE24=0 RSID24=564 LSID24=-1 FSEC24=59 SLOT24=1 TEX240=SW1BROWN TEX241=SW2BROWN TEX242=SW1BROWN PAIR24=4 SWI24=8 SPC241=60 BSLOT24=0 BT240=35 BT241=0 BREST24=1 BCLR24=1 EVF24=1 TFIND24=2 TITER24=648 TSEC24=57 F240=16 F241=-48 C24=144 SSPEC24=0 LOWF24=-48 DEST24=-48 DIR24=-1 SPD24=1 ADD24=1 PTIC24=66 TMF24=65 MP24=65 FMUT24=64 PAST24=1 REM24=1 LREM24=1 MSND24=9 STOP24=1 LT24=66 ORDER24=1 AUD24=0 GENF24=1 GPLAT24=1 GCEIL24=1 S25ABS=1 S24SIG=1919312263`.
- Generalized floors, platforms/lifts, ceilings/crushers, stairs, donuts,
  floor texture-change families, live keyboard input, menus, automap,
  save/load, networking, music, mixer/device playback, real speaker playback,
  map progression, and stage25 remain outside the emitted runtime.

## Released Slice: source_stage25_first_platform_lift_cycle_probe

Output:

```text
build/source_stage25_first_platform_lift_cycle_probe.exe
```

Goal:

After stage24 proves the floor half of `T_MovePlane`, add the first platform
or lift cycle. This should be a real switch-texture reusable button candidate
routing through `EV_DoPlat(downWaitUpStay)`, because that is the first point
where the source needs `plat_t`, `activeplats[MAXPLATS]`, platform status
transitions, wait counts, and active-plat removal.

Re-check after stage24:

- The pinned candidate still matches the WAD data and source route. The stage24
  floor-side `T_MovePlane` subset is directly reusable for platform floor
  movement; stage25 should add only the `plat_t` wrapper/status behavior around
  it.
- Source `T_MovePlane` uses strict past-destination comparisons, so the stage25
  ticker window should account for equality-at-destination tics before
  `pastdest` is reported, just as stage24 did.

Pinned candidate to validate first:

- Map `MAP12`, linedef `2304`, special `62`
  (`EV_DoPlat(line, downWaitUpStay, 1)` plus
  `P_ChangeSwitchTexture(line, 1)`), tag `26`.
- Front/right sidedef `3005`, back sidedef `3004`, front sector `228`, lower
  texture `SW1STRTN`.
- Tag `26` resolves to one sector, sector `77`, with floor `-8`, ceiling
  `256`, special `0`.
- `P_FindLowestFloorSurrounding(sector 77)` reaches `-64`, so the plat starts
  with `low=-64`, `high=-8`, `speed=PLATSPEED*4`, `wait=TICRATE*PLATWAIT=105`,
  status `down`, and tag `26`.
- Source switch pair resolves `SW1STRTN -> SW2STRTN` through switch pair `18`;
  reusable activation should preserve line special `62`, allocate a button
  slot, and restore `SW1STRTN` at tic `35`.
- Downward movement reaches `-64` after 14 movement tics, then reports
  `pastdest` on the following strict-comparison tic. The platform enters
  `waiting`, sets `count=105`, and counts `sfx_pstop`.
- Waiting decrements for 105 ticker dispatches. When the count reaches zero,
  status changes to `up` and `sfx_pstart` is counted.
- Upward movement reaches `-8` after 14 movement tics, then reports
  `pastdest` on the following strict-comparison tic. Because the type is
  `downWaitUpStay`, `P_RemoveActivePlat` should clear the active plat slot,
  clear sector `specialdata`, mark the thinker for lazy removal, and count the
  final `sfx_pstop` boundary.
- A bounded window of about 136 ticker calls should be enough to prove the full
  down-wait-up-stay lifecycle plus lazy unlink, while still avoiding perpetual
  plats, broad lift families, and live map progression.

Fallback if the pinned MAP12 candidate exposes a mismatch during
implementation: choose the next real reusable switch-texture platform/lift
candidate from the same census and document why line `2304` was rejected. Do
not silently fall back to a synthetic lift.

Scope:

- Reuse stage24 floor-side `T_MovePlane` and stage23 button/switch timer
  scaffolding.
- Add only the selected `plat_t` fields and `activeplats[]` slot behavior
  required by `downWaitUpStay`.
- Cover `P_AddActivePlat`, selected `T_PlatRaise` statuses (`down`, `waiting`,
  `up`), `P_RemoveActivePlat`, active-plat slot clearing, sector
  `specialdata` clearing, lazy thinker unlink, pstart/pstop deferred sound
  boundaries, and the stage23 button restore path.
- Keep perpetual plats, blaze variants beyond synthetic comparison,
  in-stasis/reactivation, floor texture-change plats, generalized lifts,
  generalized specials, live input, map progression, and real audio output
  deferred.

Validation shape:

- Synthetic tests for `EV_DoPlat(downWaitUpStay)` setup, no matching tag,
  already-active sector skip, full `activeplats[]` boundary, slot allocation,
  and unsupported plat types remaining absent.
- Synthetic `T_PlatRaise` tests for strict low/high clamps, no overshoot,
  down-to-waiting transition, wait countdown, up restart, active-plat removal,
  lazy thinker removal, and pstart/pstop sound boundaries.
- Pinned MAP12 tests for line `2304`, sidedefs `3005/3004`, front sector
  `228`, target sector `77`, floor `-8 -> -64 -> -8`, speed `4`, wait `105`,
  preserved stage24/stage23/stage22/stage21/stage20/stage19 counters, and
  deterministic `S25SIG`.

Released status:

- The stage25 executable launches and preserves the released stage24, stage23,
  stage22, stage21, stage20, and stage19 signals.
- The selected real platform line is `MAP12` linedef `2304`, special `62`, tag
  `26`, side `0`, right sidedef `3005`, left sidedef `3004`, front sector
  `228`, with front lower texture `SW1STRTN`.
- Source switchlist lookup resolves pair `18`, switchlist index `36`, and
  mutates `SW1STRTN -> SW2STRTN`; reusable activation preserves line special
  `62`, starts button timer `35`, and restores `SW1STRTN`.
- Tag `26` resolves only to sector `77`; the selected sector starts with floor
  `-8`, ceiling `256`, special `0`, and `P_FindLowestFloorSurrounding` reaches
  low `-64`.
- One active platform thinker is spawned with low `-64`, high `-8`, speed `4`,
  wait `105`, status `down`, tag `26`, and activeplats slot `0`.
- The 136 bounded ticker calls prove `135` `T_PlatRaise` dispatches, `30`
  `T_MovePlane` calls, `28` floor mutations, strict past-destination events at
  low and high, `105` waiting countdowns, one upward restart, active slot and
  sector `specialdata` clearing, and one lazy unlink.
- The released stage25 signal includes:
  `S25MAP=12 S25LINE=2304 S25SPEC=62 TAG25=26 RSID25=3005 LSID25=3004 FSEC25=228 TEX250=SW1STRTN TEX251=SW2STRTN TEX252=SW1STRTN PAIR25=18 SWI25=36 TSEC25=77 F250=-8 F251=-8 LOW25=-64 HIGH25=-8 SPD25=4 WAIT25=105 ASLOT25=0 PTIC25=136 TPL25=135 MP25=30 PMUT25=28 PAST25=2 WT25=2 WDEC25=105 UP25=1 AREM25=1 ACLR25=1 LREM25=1 PSTART25=2 PSTOP25=2 AUD25=0 S26ABS=1 S25SIG=1688844032`.
- Generalized platforms/lifts, generalized floors, generalized
  ceilings/crushers, stairs, donuts, live keyboard input, menus, automap,
  save/load, networking, music, mixer/device playback, real speaker playback,
  map progression, and stage26 remain outside the emitted runtime.

## Released Slice: source_stage26_first_ceiling_or_crusher_special_probe

Output:

```text
build/source_stage26_first_ceiling_or_crusher_special_probe.exe
```

Goal:

After stage25 proves platform-specific state around floor movement, add the
first ceiling/crusher thinker. This should reuse the existing `T_MovePlane`
ceiling branch from the door proof but route through `EV_DoCeiling ->
T_MoveCeiling`, proving `ceiling_t`, `activeceilings[MAXCEILINGS]`, selected
crush/lower behavior, and active-ceiling removal or reversal without a broad
crusher system.

Re-check after stage25:

- Stage25 added the missing active-array lifecycle pattern for platforms. Stage26
  should mirror that shape for `activeceilings[]` rather than broadening the
  special dispatcher.
- A fresh switch-texture ceiling census found two clean `EV_DoCeiling` switch
  candidates in the pinned IWAD. `MAP11` linedef `3407`, special `49`, tag
  `15`, lower texture `SW2STON1`, resolves two tagged sectors (`567` and
  `583`). `MAP29` linedef `71`, special `49`, tag `40`, middle texture
  `SW1GSTON`, resolves one tagged sector (`117`). The single-sector MAP29
  candidate is the cleaner first release target.

Pinned candidate to validate first:

- Map `MAP29`, linedef `71`, special `49`
  (`EV_DoCeiling(line, crushAndRaise)` plus
  `P_ChangeSwitchTexture(line, 0)`), tag `40`.
- Front/right sidedef `125`, one-sided line, front sector `75`, middle texture
  `SW1GSTON`.
- Source switch pair should mutate `SW1GSTON -> SW2GSTON` on press and clear
  line special `49`, because this is a one-shot switch (`useAgain=0`).
- Tag `40` resolves to sector `117`, with floor `192`, ceiling `304`, special
  `0`. For `crushAndRaise`, `EV_DoCeiling` should set `crush=true`,
  `topheight=304`, `bottomheight=floor+8=200`, `direction=-1`,
  `speed=CEILSPEED=1`, `tag=40`, and type `crushAndRaise`.
- The bounded ticker should prove downward ceiling movement from `304` to
  `200` through `T_MoveCeiling -> T_MovePlane`, strict source-shaped
  past-destination behavior after equality at bottom, reversal to direction
  `1`, upward movement back to `304`, strict past-destination behavior after
  equality at top, and reversal back to direction `-1`. Because
  `crushAndRaise` is a cycling ceiling, it should not remove itself in the
  first full cycle.
- One additional synthetic path should cover `P_RemoveActiveCeiling` using a
  selected removable type such as `lowerToFloor` or `raiseToHighest`, so
  active slot clearing and sector `specialdata` clearing are proven without
  turning the MAP29 crusher proof into a broader ceiling system.

Scope:

- Reuse stage21/stage24 ceiling-side `T_MovePlane` semantics and stage25
  active-array discipline.
- Add only the selected `ceiling_t` fields and `activeceilings[]` slot behavior
  required for `crushAndRaise`, plus synthetic removable-ceiling coverage.
- Count moving-ceiling sound and pstop boundaries as deferred; actual speaker
  playback remains deferred.
- Keep generalized ceilings/crushers, crusher damage expansion, ceiling stop
  line families, in-stasis reactivation beyond small synthetic guards, live
  input, map progression, menus, automap, save/load, networking, music, mixer
  output, and stage27 absent.

Fallback:

If MAP29 line `71` exposes a mismatch during implementation, validate the
documented MAP11 line `3407` candidate next and explicitly record the reason
MAP29 failed. Do not silently fall back to a synthetic ceiling proof.

Validation shape:

- Synthetic `EV_DoCeiling` tests for `crushAndRaise` setup, tag traversal, no
  matching tag, already-active sector skip, selected sector assignment,
  activeceilings slot allocation, full-list boundary, and unsupported ceiling
  types remaining absent from the selected runtime.
- Synthetic `T_MoveCeiling/T_MovePlane` tests for downward movement, exact
  bottom clamp/no overshoot, strict past-destination reversal, upward movement,
  exact top clamp/no overshoot, repeated cycling, crush/nofit speed adjustment
  boundary, deferred sound boundaries, synthetic active ceiling removal, and
  preservation of the stage25 platform/button lifecycle.
- Pinned MAP29 tests for linedef `71`, special `49`, tag `40`, sidedef `125`,
  front sector `75`, `SW1GSTON -> SW2GSTON`, target sector `117`, ceiling
  `304 -> 200 -> 304`, floor `192`, speed `1`, bottom `200`, active ceiling
  allocation, reversal counts, preserved stage25 through stage19 counters, and
  deterministic `S26SIG`.

Released status:

- `build/source_stage26_first_ceiling_or_crusher_special_probe.exe` exists.
- It launches and reports preserved stage25/stage24/stage23/stage22/stage21/
  stage20/stage19 baselines plus deterministic stage26 ceiling/crusher proof.
- The selected MAP29 ceiling moves down and back up through source-shaped
  `T_MoveCeiling/T_MovePlane` logic, with strict past-destination reversals and
  active ceiling state visible in the smoke signal.
- Generalized ceiling/crusher systems and real audio output remain deferred.
- The released stage26 signal includes:
  `S26MAP=29 S26LINE=71 S26SPEC=49 TAG26=40 SIDE26=0 RSID26=125 LSID26=-1 FSEC26=75 SLOT26=1 TEX260=SW1GSTON TEX261=SW2GSTON TEX262=SW2GSTON PAIR26=22 SWI26=44 SPC261=0 EVC26=1 TFIND26=2 TITER26=131 TSEC26=117 F26=192 C260=304 C261=304 SSPEC26=0 BOT26=200 TOP26=304 DIR260=-1 DIR261=-1 CRUSH26=1 SPD26=1 ASLOT26=0 ADD26=1 PTIC26=210 TMC26=210 MP26=210 CMUT26=208 PAST26=2 BREV26=1 TREV26=1 AREM26=0 ACLR26=0 LREM26=0 MSND26=27 PSTOP26=0 LT26=210 ORDER26=1 AUD26=0 GENF26=1 GPLAT26=1 GCEIL26=1 S27ABS=1 S26SIG=132405987`.

## Released Slice: source_stage27_integrated_scripted_room_interaction_loop

Output:

```text
build/source_stage27_integrated_scripted_room_interaction_loop.exe
```

Goal:

After stage26 completes the first representative floor/platform/ceiling sector
movement trio, stop adding isolated environment probes for one slice and
integrate a small scripted room interaction loop. The point is not live input
yet; it is to make one emitted executable own one runtime world, advance a
short deterministic sequence of normal `G_Ticker` / `P_Ticker` calls, mutate
state over time, and report multiple successive states from that same world
instead of only reporting a final precomputed proof snapshot. This should be
the first deliberately non-static source-guided test executable: still bounded
and scripted, but visibly or title/log-observably changing across tics after
launch.

Re-check after stage26:

- Stage24, stage25, and stage26 prove the selected floor, platform, and ceiling
  thinkers independently, but each proof still snapshots a bounded outcome into
  title/status data.
- Stage21 already proved normal `P_Ticker` ordering, and stages23-26 proved
  button/update-special interaction while other thinkers exist. Stage27 should
  reuse that ordering in one cohesive runtime harness rather than adding a new
  environment special.
- A single-map script is preferable if a clean candidate exists, but a
  documented two-probe harness is still honest if it preserves one world/ticker
  lifecycle and exposes a multi-tic state log from emitted runtime state.

Proposed shape:

- Use a compact real-map script chosen from already-proven ingredients. First
  choice: a one-map route that starts from a real player/map state, consumes a
  short `ticcmd_t` sequence, reaches a usable line, activates one already-proven
  sector thinker, and continues ticking until at least two distinct post-use
  state changes are visible. If that census is not clean, use a documented
  harness with a real movement probe and a real switch/sector probe under one
  normal ticker loop.
- Keep the runtime bounded and deterministic. A good first window is roughly
  40-220 tics depending on the selected special: long enough to show switch
  mutation, button restore if applicable, and several movement samples, but not
  long enough to require map progression or generalized gameplay.
- Add a small emitted tic/state strip in the framebuffer and title/status:
  examples include `LOG27=0:closed,1:pressed,35:restored,66:floor_done` or a
  fixed ring of sampled sector heights. The smoke test should verify multiple
  sequential markers, not just final counters.
- Preserve stage26 through stage19 signals and still keep live keyboard input,
  menus, automap, map exits, save/load, networking, music, and real audio
  device output deferred.
- Preserve determinism: no live keyboard input, no random unscripted monster
  behavior, no map progression, and no real audio device output.

Likely source routines to re-read:

- `g_game.c`: `G_Ticker` ordering and `ticcmd_t` consumption.
- `p_user.c`: `P_PlayerThink`, `P_MovePlayer`, and script-driven use/movement
  where the selected route needs a moving player.
- `p_tick.c`: `P_Ticker`, `P_RunThinkers`, `P_UpdateSpecials`, and
  `leveltime++` ordering as an integrated loop rather than isolated probes.
- `p_map.c` / `p_maputl.c`: `P_UseLines` and path traversal from a moving
  player position.
- The selected environment thinker source from stages24-26, depending on the
  chosen room script.
- `p_switch.c`: `P_UseSpecialLine` and `P_ChangeSwitchTexture` for the selected
  activation path.

Candidate selection notes:

- Prefer a real map candidate whose line special and texture pair are already
  represented by stages22-26, because the release goal is integration rather
  than broad special coverage.
- Prefer a candidate where the player can reach/use the line with a very short
  deterministic script from a source-shaped start state. Avoid routes that need
  live turning finesse, monster interference, keys, exits, or map progression.
- If no clean single-map route is found quickly, document the census miss and
  use the smallest honest two-probe harness that still advances one normal
  ticker loop and exposes changing runtime state.

Validation shape:

- Synthetic loop tests for order, deterministic tic count, multi-tic state log,
  button restoration during other thinker movement, and no accidental live
  input dependency.
- Pinned real-map tests proving the selected script advances visible or
  reported state across several tics, samples at least three distinct runtime
  states, and preserves stage26 through stage19 signatures.
- Smoke test that launches the executable and verifies multiple sequential
  state markers, not just final-state counters.

Released status:

- `build/source_stage27_integrated_scripted_room_interaction_loop.exe` exists.
- The released route uses the already-proven real `MAP12` linedef `2304`,
  special `62`, tag `26`, front lower texture `SW1STRTN`, and target sector
  `77`.
- A deterministic `ticcmd_t` script issues one `BT_USE` command, then runs a
  136-tic `G_Ticker -> P_PlayerThink -> P_UseLines/P_UseSpecialLine ->
  P_Ticker -> P_RunThinkers -> T_PlatRaise/T_MovePlane -> P_UpdateSpecials ->
  P_RespawnSpecials -> leveltime++` lifecycle in one bounded world.
- The emitted title/status reports six sequential samples from that same world:
  `LOG27=1:F-12:B34:SW2STRTN:S1:C0|14:F-64:B21:SW2STRTN:S1:C0|35:F-64:B0:SW1STRTN:S2:C85|36:F-64:B0:SW1STRTN:S2:C84|120:F-64:B0:SW1STRTN:S0:C0|136:F-8:B0:SW1STRTN:S2:C105`.
- The executable no longer publishes only a frozen final title: after the
  window is created it sets a `WM_TIMER` and visibly advances the title through
  `S27 LIVE START STEP27=0`, then `STEP27=1` through `STEP27=6`, ending at
  `TIC27=136 F27=-8 TEX27=SW1STRTN`.
- Stage27 preserves stage26 through stage19 signatures and reports
  `S27SIG=1735738182`.
- Manual input, menus, automap, save/load, networking, music, speaker output,
  map progression, generalized combat, and broader special systems remain
  deferred.

## Released Slice: source_stage28_live_input_to_deterministic_game_loop_bridge

Output:

```text
build/source_stage28_live_input_to_deterministic_game_loop_bridge.exe
```

Goal:

After stage27 proves a non-static scripted runtime loop, bridge real keyboard
events into the same source-shaped `ticcmd_t` path without sacrificing
determinism in tests. The executable should accept live movement/use controls
for manual play in the bounded harness, while the smoke path still feeds a
fixed command script and proves the same state markers without depending on a
human.

Re-check after stage27:

- Stage27 already owns one bounded world and proves that a deterministic
  `ticcmd_t` stream can activate a reusable platform button and expose changing
  runtime state across tics. Its title now advances after the window is created
  through a bounded `WM_TIMER` sequence, so it is no longer only a frozen final
  proof snapshot.
- The emitted executable still has no input path into the game command stream:
  command data is deterministic and scripted, and no Win32 key state is
  translated into `ticcmd_t` fields.
- Stage28 should not make a full playable Doom loop yet. The honest next step
  is a small live-control bridge that can be disabled for smoke and that feeds
  the same command fields the stage27 script used.

Likely shape:

- Re-read `d_event.c`, `g_game.c`, `p_user.c`, and the existing Win32 input
  code from the early stages.
- Translate a small subset of keyboard events into Doom-shaped command fields:
  forward/back, turn left/right, and use. Add strafe only if it fits without
  disturbing the small command builder.
- Keep two modes in one executable:
  deterministic replay mode for smoke, which replays the stage27 script and
  must produce the same `LOG27` markers; and manual mode, enabled by an
  explicit command-line flag or visible toggle, which reads Win32 key state and
  builds live `ticcmd_t` records.
- Reuse the MAP12 room route from stage27. The manual path should let a user
  press use to activate the same platform button, then observe the same ticker
  lifecycle. Movement may be represented in title/status/player fields even if
  the renderer remains debug-oriented.
- Preserve the stage27 post-launch stepping behavior. Replay mode should still
  show a start state, advance through visible runtime markers after window
  creation, and only then report its final deterministic signature.
- Keep the emitted status/title explicit about mode, command counts, use-edge
  counts, and whether live input was enabled. Scripted smoke should report
  `LIVE28=0`; manual runs can report `LIVE28=1`.
- Do not add menus, automap, save/load, map progression, networking, broad
  combat, generalized specials, or real audio device output. The release is the
  input bridge into the existing loop, not a playable vertical slice yet.

Source routines to re-read:

- `d_event.c`: event input path and key up/down semantics.
- `g_game.c`: `G_BuildTiccmd`, `G_Ticker`, `gamekeydown[]`, and command
  replay/demo consistency details.
- `p_user.c`: `P_PlayerThink`, `P_MovePlayer`, `P_Thrust`, and `BT_USE`
  `usedown` gating.
- Existing Win32 message/input code in the early emitted window stages.
- Stage27 emitter/test code for the deterministic replay contract.

Validation shape:

- Synthetic command-building tests for key down/up state, forward/back/turn/use
  command fields, use-edge gating, and deterministic replay override.
- Synthetic tests proving replay mode ignores live key state and manual mode
  can emit `BT_USE`.
- Pinned smoke test that replays the stage27 script through the same input
  bridge, observes both the post-launch start marker and final replay marker,
  reaches the same state log/signature, preserves stage27 through stage19
  signatures, and reports no speaker output or map progression.
- Build inspection proving the stage28 executable contains stage28 status
  strings but does not contain stage29 strings.
- Manual run note documenting the small live-control harness and deferred
  systems.

Released status:

- `build/source_stage28_live_input_to_deterministic_game_loop_bridge.exe`
  exists and launches.
- Replay mode is the deterministic smoke path and reports `LIVE28=0`. It
  replays the stage27 MAP12 script through
  `G_BuildTiccmd_stage28_live_or_replay_bridge_source_shape_debug`, ignores a
  synthetic live key state during the reference proof, and reproduces the
  stage27 route/signature:
  `LOG27=1:F-12:B34:SW2STRTN:S1:C0|14:F-64:B21:SW2STRTN:S1:C0|35:F-64:B0:SW1STRTN:S2:C85|36:F-64:B0:SW1STRTN:S2:C84|120:F-64:B0:SW1STRTN:S0:C0|136:F-8:B0:SW1STRTN:S2:C105`
  and `R28SIG=1735738182`.
- The post-launch title sequence is preserved under stage28 markers: it starts
  at `S28 REPLAY START STEP28=0 LIVE28=0`, advances through `STEP28=1..6`,
  and ends at `TIC28=136 F28=-8 TEX28=SW1STRTN`.
- Manual mode is enabled with `-manual`. It reads bounded Win32 key
  down/up state for W/S/up/down forward/back, A/D/left/right turn, and
  E/Space use. The manual timer builds live `ticcmd_t` fields and reports
  `LIVE28=1`, `FM28`, `AT28`, `BTN28`, `BTUSE28`, `USEEDGE28`, and key-event
  counters in the title.
- Stage28 preserves stage27 through stage19 signatures and reports
  `S28SIG=2805406010`.
- Menus, automap, save/load, networking, music, real speaker output,
  mixer/device playback, map progression, generalized combat, broad AI, and
  broader special systems remain deferred.

## Released Slice: source_stage29_selected_monster_chase_attack_state_loop

Output:

```text
build/source_stage29_selected_monster_chase_attack_state_loop.exe
```

Goal:

After stage28 lets commands enter the bounded loop through either replay or
manual input, return to gameplay state and integrate the first longer selected
monster loop. Stage29 continues the stage16-18 MAP01 shotgun-guy route after
the selected nonlethal shotgun hit: the monster services momentum, recovers
through pain states, retains its target, dispatches one `A_Chase`, and stops at
the first source-honest attack-decision boundary.

Re-check after stage28:

- Stage28 proved command ingress, not full play. Manual input can produce
  Doom-shaped movement/use fields, but replay remains the correct validation
  path for any gameplay state that needs deterministic smoke.
- Stages16-18 already provide the ingredients for one selected MAP01 shotgun
  guy: `A_Look`/target acquisition, one nonlethal shotgun damage mutation, and
  one post-damage momentum move before chase logic resumes.
- Stage17's shotgun route is a strong candidate because it is already
  source-shaped and deterministic, but a full kill/drop may require multiple
  repeated weapon cycles, psprite timing, pain/chase interleaving, and possibly
  more monster action code than one narrow release should absorb.
- The next slice should therefore be named and scoped around the selected
  monster state loop, not promise a death/drop unless the first source pass
  shows it falls out naturally.

Released shape:

- The emitted tool is
  `tools/emit_source_stage29_selected_monster_chase_attack_state_loop.py`.
- The deterministic replay path builds one bounded reference world from the
  selected stage17/18 MAP01 shotgun-guy state and advances six tics through:
  `G_Ticker`, `P_PlayerThink`/`P_MovePsprites`, `P_Ticker`,
  `P_RunThinkers`, and `P_MobjThinker`.
- The selected monster log is:
  `1:S_SPOS_PAIN:T2:XY1751,-938:M-20103,-71466:TG0:H20:TH100:CH0:AB0|2:S_SPOS_PAIN:T1:XY1751,-939:M-18219,-64767:TG0:H20:TH100:CH0:AB0|3:S_SPOS_PAIN2:T3:XY1751,-940:M-16511,-58696:TG0:H20:TH100:CH0:AB0|4:S_SPOS_PAIN2:T2:XY1750,-941:M-14964,-53194:TG0:H20:TH100:CH0:AB0|5:S_SPOS_PAIN2:T1:XY1750,-941:M-13562,-48208:TG0:H20:TH100:CH0:AB0|6:S_SPOS_RUN1:T3:XY1750,-942:M-12291,-43689:TG0:H20:TH99:CH1:AB1`.
- The first honest boundary is `ATTACK_DECISION`: `A_Chase` reaches the
  selected missile-range/attack-state dispatch point, then the release stops
  before attack action execution, projectiles, additional damage, death, or
  drop handling.
- The post-launch title still advances under a timer. It starts at
  `S29 REPLAY START STEP29=0 LIVE29=0`, steps through six replay samples, and
  ends at `STEP29=6`, `TIC29=6`, `ST29=S_SPOS_RUN1`, `AB29=1`,
  `BOUND29=ATTACK_DECISION`, `S30ABS=1`, and `S29SIG=3738922932`.

Validation shape:

- Synthetic tests cover selected mobj state transitions, source-shaped ticker
  ordering, target retention, chase/action dispatch, and the fact that this
  route includes no new damage/death/drop boundary.
- Absence tests keep broad AI, projectiles, infighting, generalized combat,
  pickups, exits, map progression, real audio, runtime rendered motion, and
  stage30 outside this slice.
- The pinned real-map replay proves six changing monster samples and preserves
  stage28 through stage19 signatures.
- The executable build/smoke test verifies the PE launches, reports stage29
  markers/log/signature, preserves baselines, and contains no `source_stage30`
  strings.

Released status:

- `build/source_stage29_selected_monster_chase_attack_state_loop.exe` exists
  and launches.
- The selected monster follows the six-tic source-shaped route through
  `ATTACK_DECISION`.
- The replay path is deterministic and stage28 live input remains optional and
  isolated from smoke.
- Stage29 reports `S29SIG=3738922932`.
- Stage28 through stage19 baselines are preserved:
  `S28SIG=2805406010`, `S27SIG=1735738182`, `S26SIG=132405987`,
  `S25SIG=1688844032`, `S24SIG=1919312263`, `S23SIG=3216085132`,
  `S22SIG=2207028069`, `S21SIG=1770773845`, `S20SIG=3226031347`, and
  `S19SIG=2088411722`.
- Runtime rendered motion, projectiles, explosions, generalized combat, broad
  AI, map progression, UI systems, and real audio remain deferred.

## Released Slice: source_stage30_runtime_rendered_motion_bridge

Output:

```text
build/source_stage30_runtime_rendered_motion_bridge.exe
```

Goal:

After stage29 adds another moving gameplay state loop, connect one bounded
runtime state change back into the existing renderer so the executable has
actual changing framebuffer pixels, not only changing title/status text. This
is the first non-static visual proof in the source-guided line: a timer-driven
replay advances selected MAP01 player-view samples, replaces the live
framebuffer from updated source-shaped fields, invalidates the Win32 window,
and the smoke test observes changing pixel signatures across frames.

Re-check after stage29:

- Stage27 and stage28 already visibly advance title text after launch, and
  stages24-26 prove real moving sector state. Stage29 proves real selected
  monster state mutation. The framebuffer itself is still effectively a fixed
  proof image.
- Earlier renderer stages already know how to draw source-shaped walls, flats,
  sky, masked midtextures, sprites, and the selected debug frame from emitted
  x86 plus table-emitted WAD data. The missing bridge is not a broader renderer;
  it is using updated runtime fields as the frame input and repainting more than
  once.
- A moving player-view proof is likely the cleanest first candidate because
  earlier MAP01 renderer/player-movement stages already agree on map, player
  start, view fields, BSP traversal, and framebuffer signatures. It avoids
  proving dynamic sector visibility at the same time as proving redraw.
- A moving-sector proof remains a strong fallback if a fixed MAP12 viewpoint
  can see sector `77` move with a small renderer input change, but it may need
  more sector-plane/wall-height plumbing than a player-view redraw.
- A moving-monster visual proof is probably one stage too early: stage29 changes
  monster state and position, but the renderer would need dynamic sprite
  placement, state frame selection, and possibly occlusion interactions at the
  same time as the first redraw bridge.

Implemented shape:

- The emitted tool is
  `tools/emit_source_stage30_runtime_rendered_motion_bridge.py`.
- Stage30 reuses the stage14 MAP01 deterministic player movement route and
  selects three source-shaped samples from tics `0`, `4`, and `7`.
- Each sample maps `viewx`, `viewy`, `viewz`, and `viewangle` into a bounded
  runtime render bridge, clears/replaces the live framebuffer bytes, records
  clear/redraw ordering, invalidates the Win32 window, and reports a per-frame
  framebuffer signature.
- The timer-driven replay after launch is:
  `S30 RENDER START STEP30=0` -> `STEP30=1` -> `STEP30=2` -> `STEP30=3`.
- The selected frame log is:
  `1:T0:VX-192:VY-192:A0:FB2289904038|2:T4:VX-182:VY-192:A1:FB2221072019|3:T7:VX-172:VY-194:A3:FB169445058`.
- The stage30 bridge keeps stage28's Win32 framebuffer paint path and uses
  direct x86 `rep movsd` copies from emitted frame bytes into the live
  framebuffer on timer ticks. No new x86 helper was needed.
- Projectiles, explosions, generalized combat, broad AI, generalized specials,
  map progression, UI systems, real audio playback, and stage31 remain
  deferred.

Validation shape:

- Synthetic tests cover frame-step ordering, selected runtime state to render
  input mapping, framebuffer clear/redraw ordering, and distinct
  frame-signature expectations.
- The pinned real-map replay proves three changed view/render inputs and three
  distinct framebuffer signatures.
- Build inspection proves the emitted executable contains stage30 strings and
  no `source_stage31` strings.
- Scripted smoke launches the executable, observes the start marker, waits for
  the three rendered-frame markers/signatures, proves at least two distinct
  `FB30=` values after launch, and closes cleanly.
- Preservation tests cover stage29/stage28 through stage19 signatures.

Released status:

- `build/source_stage30_runtime_rendered_motion_bridge.exe` exists and
  launches.
- Stage30 reports `S30SIG=3898523864`.
- The runtime framebuffer signatures are distinct:
  `FB30=2289904038`, `FB30=2221072019`, and `FB30=169445058`.
- Stage29 through stage19 baselines are preserved:
  `S29SIG=3738922932`, `S28SIG=2805406010`, `S27SIG=1735738182`,
  `S26SIG=132405987`, `S25SIG=1688844032`, `S24SIG=1919312263`,
  `S23SIG=3216085132`, `S22SIG=2207028069`, `S21SIG=1770773845`,
  `S20SIG=3226031347`, and `S19SIG=2088411722`.

## Released Slice: source_stage31_runtime_real_renderer_motion_bridge

Output:

```text
build/source_stage31_runtime_real_renderer_motion_bridge.exe
```

Goal:

After stage30 proves that runtime state can drive changing framebuffer pixels,
replace the bounded debug-frame bridge with the smallest honest runtime bridge
back into the existing real renderer path. The goal is a non-static executable
whose changing pixels are produced by re-running source-shaped renderer
primitives from changed `viewx`, `viewy`, and `viewangle`, not by copying
pre-emitted full-frame byte arrays.

Re-check after stage30:

- Stage30 accomplished the first post-launch pixel proof, but it did so by
  table-emitting complete framebuffer samples and copying them with `rep movsd`.
  That was a useful bridge, not the destination.
- Earlier renderer stages already have source-shaped wall column, composite
  texture, flat span, sky, masked midtexture, and sprite paths. Most of that
  work is still fixed-view or pre-derived in Python, so stage31 should select
  the narrowest piece that can be recomputed for several runtime view samples.
- The cleanest first target is still the stage14 MAP01 player movement route:
  three to five samples from the same deterministic path, but the framebuffer
  signatures must come from regenerated render commands or runtime render loops
  keyed by the changed view fields.
- Combat visuals should wait one slice. Stage29 gives useful monster state, but
  adding dynamic sprite state while the camera redraw path is still a full-frame
  copy would blur what the release proves.

Implemented shape:

- The emitted tool is
  `tools/emit_source_stage31_runtime_real_renderer_motion_bridge.py`.
- Stage31 reuses the stage14 MAP01 deterministic player movement route and
  selects the same three view samples from tics `0`, `4`, and `7`.
- Python derives compact per-sample wall-column and flat-span command tables
  from the existing source-shaped renderer data. It does not emit finished
  stage31 framebuffer byte arrays.
- On each timer tick, the executable copies the selected source-shaped view
  fields, clears the live framebuffer, selects that sample's command table,
  executes the existing `R_DrawColumn`-shaped and `R_DrawSpan`-shaped x86 draw
  primitives, computes a runtime framebuffer signature, invalidates/updates the
  Win32 window, and reports draw counters.
- The timer-driven replay after launch is:
  `S31 REALRENDER START STEP31=0` -> `STEP31=1` -> `STEP31=2` -> `STEP31=3`.
- The selected runtime renderer command log is:
  `1:T0:VX-192:VY-192:A0:WC780:SP169:FB2926869513|2:T4:VX-182:VY-192:A1:WC776:SP169:FB622680457|3:T7:VX-172:VY-194:A3:WC769:SP169:FB1677820087`.
- Stage12 sky/masked paths and stage13 sprite posts are deferred from this
  smallest honest release; stage31 proves changed real WAD-rendered wall/flat
  pixels from runtime-selected render commands.
- Projectiles, explosions, combat expansion, dynamic monster animation, menus,
  automap, save/load, map progression, broad special systems, and real audio
  playback remain deferred.

Validation shape:

- Synthetic tests cover frame-step ordering, selected runtime-state to
  renderer-input mapping, render-command table selection,
  framebuffer clear/draw/present ordering, distinct frame-signature
  expectations, and absence flags.
- The pinned MAP01 replay proves three changed view/render inputs, three
  distinct command tables, and three distinct framebuffer signatures after
  launch.
- Build inspection proves the stage31 executable contains stage31 strings, no
  `source_stage32` strings, no stage31 full-frame copy routine, and no `rep
  movsd` full-frame motion opcode in the stage31 image.
- Preservation tests cover stage30/stage29 through stage19 signatures.

Released status:

- `build/source_stage31_runtime_real_renderer_motion_bridge.exe` exists and
  launches.
- Stage31 reports `S31SIG=3593583171`.
- The runtime real-renderer framebuffer signatures are distinct:
  `FB31=2926869513`, `FB31=622680457`, and `FB31=1677820087`.
- Stage30 through stage19 baselines are preserved:
  `S30SIG=3898523864`, `S29SIG=3738922932`, `S28SIG=2805406010`,
  `S27SIG=1735738182`, `S26SIG=132405987`, `S25SIG=1688844032`,
  `S24SIG=1919312263`, `S23SIG=3216085132`, `S22SIG=2207028069`,
  `S21SIG=1770773845`, `S20SIG=3226031347`, and `S19SIG=2088411722`.

## Planning Checkpoint After Stage32

Where we are:

- Stage31 proved changed real WAD wall/flat pixels after launch by selecting
  compact renderer command tables at runtime.
- Stage32 preserves that live wall/flat bridge and adds one selected
  combat-adjacent visual route: shotgun weapon psprite states select compact
  patch/post command tables and draw them after the stage31 walls/flats.
- The proof is still intentionally narrow. It does not run generalized sprite
  sorting/traversal, broad monster AI, projectiles, explosions, attack
  execution, damage/death/drop, map progression, UI systems, or real audio.
- The next bottleneck is no longer "can a gameplay/weapon state change live
  pixels?" Stage32 answered that for one selected psprite route. The next
  bottleneck is a single selected action/effect boundary without expanding into
  broad combat.

## Released Slice: source_stage32_selected_combat_visual_state_bridge

Output:

```text
build/source_stage32_selected_combat_visual_state_bridge.exe
```

Goal:

Connect one selected combat-adjacent visual state to the stage31 live renderer
path without adding broad combat. The released route uses selected player
shotgun psprite states (`S_SGUN`, `S_SGUN3`, `S_SGUN4`) and real WAD patch
posts (`SHTGA0`, `SHTGB0`, `SHTGC0`) drawn after the stage31 wall/flat base.

Released shape:

- Preserves the stage31 wall/flat runtime redraw bridge as the base frame.
- Adds selected `R_DrawPlayerSprites` / `R_DrawPSprite`-shaped post command
  tables for one shotgun psprite route.
- Runtime replay selects three deterministic samples from tics `0`, `4`, and
  `7`, updates selected psprite state/frame/patch markers, clears the
  framebuffer, draws stage31 walls/flats, draws selected psprite posts, signs
  the framebuffer, and presents.
- The selected psprite post counts are `66`, `96`, and `135`; selected psprite
  pixel counts are `2083`, `5906`, and `7493`.
- Generalized sprite sorting/traversal, thing sprite systems, projectile
  actors, explosion states, monster attack execution, damage/death/drop logic,
  HUD weapon systems, menus, automap, save/load, map progression, broad
  specials, and real audio remain deferred.

Validation shape:

- Synthetic tests cover frame-step ordering, selected state-to-render-frame
  mapping, selected patch/post command generation, runtime command-table
  selection, clear/wall-flat/psprite/present ordering, distinct framebuffer
  signatures, absence flags, no full-frame byte-array motion, and preservation
  of stage31 through stage19 signatures.
- The pinned replay proves the stage31 base signatures remain
  `2926869513`, `622680457`, and `1677820087`, then the selected psprite pass
  changes them to `2997224612`, `3655441960`, and `2243530028`.
- Build/smoke proves the executable launches, reports stage32 markers and
  selected psprite counters, contains no `source_stage33` strings, and still
  has no full-frame byte-copy motion mechanism.

Released status:

- `build/source_stage32_selected_combat_visual_state_bridge.exe` exists and
  launches.
- Stage32 reports `S32SIG=533488475`.
- The runtime framebuffer signatures with selected psprite contribution are
  distinct: `FB32=2997224612`, `FB32=3655441960`, and `FB32=2243530028`.
- Stage31 through stage19 baselines are preserved:
  `S31SIG=3593583171`, `S30SIG=3898523864`, `S29SIG=3738922932`,
  `S28SIG=2805406010`, `S27SIG=1735738182`, `S26SIG=132405987`,
  `S25SIG=1688844032`, `S24SIG=1919312263`, `S23SIG=3216085132`,
  `S22SIG=2207028069`, `S21SIG=1770773845`, `S20SIG=3226031347`, and
  `S19SIG=2088411722`.

## Released Slice: source_stage33_selected_hitscan_impact_visual_boundary

Output:

```text
build/source_stage33_selected_hitscan_impact_visual_boundary.exe
```

Released shape:

- Preserve the stage31 wall/flat runtime renderer and the stage32 selected
  shotgun psprite post draw.
- Reuse the stage17 selected `A_FireShotgun` / `P_LineAttack` /
  `P_DamageMobj` route for the selected MAP01 shotgun-guy target:
  mapthing `37`, mobj `28`, selected damage `10`, target health after hit
  `20`.
- Draw the bounded selected shotgun-guy pain-state world sprite route after
  walls/flats and before the selected shotgun psprite posts. The selected WAD
  sprite lump is `SPOSG1`, mapped through `S_SPOS_PAIN` and `S_SPOS_PAIN2`.
- Keep generalized sprite traversal/sorting deferred; the stage33 proof emits
  one selected world post table and stops.
- Runtime order is explicit:
  setup view/frame -> clear -> walls/flats -> selected world pain posts ->
  selected psprite posts -> signature -> present.
- Stage33 reports `S33SIG=1614948054`.
- Stage33 framebuffer signatures are `2997224612`, `3695204165`, and
  `1535635467`; the impact-stage intermediate signatures are `2926869513`,
  `330358001`, and `1300993588`.
- Stage32 through stage19 baselines are preserved:
  `S32SIG=533488475`, `S31SIG=3593583171`, `S30SIG=3898523864`,
  `S29SIG=3738922932`, `S28SIG=2805406010`, `S27SIG=1735738182`,
  `S26SIG=132405987`, `S25SIG=1688844032`, `S24SIG=1919312263`,
  `S23SIG=3216085132`, `S22SIG=2207028069`, `S21SIG=1770773845`,
  `S20SIG=3226031347`, and `S19SIG=2088411722`.
- Projectiles, explosions, monster attack execution, monster death/drop,
  generalized combat, broad AI, generalized sprite systems, generalized
  specials, map progression, UI systems, real audio, and stage34 remain
  deferred.

## Planning Checkpoint After Stage34

Where we are:

- Stage31 proved runtime-selected wall/flat renderer command tables can redraw
  real WAD pixels after launch without copying full framebuffer byte arrays.
- Stage32 proved one selected shotgun psprite route can draw live patch posts
  after that wall/flat base.
- Stage33 crossed one gameplay/visual boundary: the selected stage17 shotgun
  hit route now produces a visible selected world consequence, using bounded
  shotgun-guy pain-state posts between the wall/flat base and psprite overlay.
- Stage34 crosses the next single selected combat/visual boundary: the selected
  MAP01 shotgun-guy route reaches a bounded lethal `P_DamageMobj` /
  `P_KillMobj` / `P_SetMobjState` transition, then draws selected
  `S_SPOS_DIE1` and `S_SPOS_DIE2` world posts from real WAD sprite data after
  the preserved stage33 impact/pain posts and before the stage32 psprite
  overlay.
- We still do not have generalized sprite traversal/sorting, a generalized
  combat loop, generalized death/drop behavior, real thing removal, item
  pickup feedback, statusbar integration, map progression, menus, automap,
  save/load, networking, music, mixer/device audio, or a broad live game loop.

Next bottleneck:

- The narrowest honest next proof is the selected drop spawn/visual boundary,
  not pickup yet. Source `P_KillMobj` maps `MT_SHOTGUY -> MT_SHOTGUN`, calls
  `P_SpawnMobj(target->x, target->y, ONFLOORZ, MT_SHOTGUN)`, then marks the
  spawned item with `MF_DROPPED`. Stage34 observed that as a deferred counter
  but deliberately did not materialize or draw the dropped thing.
- Pickup feedback is the next boundary after that. `P_TouchSpecialThing` and
  `P_GiveWeapon` treat `MF_DROPPED` weapons specially, and touching the item
  introduces player inventory/ammo/message/sound effects. That is enough new
  source behavior to keep it out of the drop-spawn visual slice unless the
  drop implementation proves pickup is truly trivial.

## Released Slice: source_stage34_selected_hitscan_death_visual_boundary

Output:

```text
build/source_stage34_selected_hitscan_death_visual_boundary.exe
```

Released shape:

- Reuses the stage17 selected shotgun target and the stage33 bounded impact/pain
  world-post draw route.
- Drives a tightly bounded selected lethal probe from target health `20` with
  lethal damage `20`, total selected damage `30`, one selected kill event, one
  selected death-state set, and one observed/deferred shotgun-guy drop counter.
- Draws three deterministic post-launch samples at tics `0`, `4`, and `7`:
  no death frame, `S_SPOS_DIE1` / `SPOSH0`, then `S_SPOS_DIE2` / `SPOSI0`.
- Runtime order is explicit:
  setup view/frame -> clear -> walls/flats -> selected stage33 impact/pain
  posts -> selected stage34 death posts -> selected stage32 psprite posts ->
  signature -> present.
- The selected death post counts are `0`, `79`, and `91`; selected death pixel
  counts are `0`, `1075`, and `1013`.
- Stage31 wall/flat base signatures remain `2926869513`, `622680457`, and
  `1677820087`; preserved stage33 impact intermediate signatures remain
  `2926869513`, `330358001`, and `1300993588`; the new death intermediate
  signatures are `2926869513`, `1191322670`, and `2513680424`; final
  framebuffer signatures are `2997224612`, `2851578387`, and `1194192847`.
- Stage34 reports `S34SIG=4027590938`.
- Stage33 through stage19 baselines are preserved:
  `S33SIG=1614948054`, `S32SIG=533488475`, `S31SIG=3593583171`,
  `S30SIG=3898523864`, `S29SIG=3738922932`, `S28SIG=2805406010`,
  `S27SIG=1735738182`, `S26SIG=132405987`, `S25SIG=1688844032`,
  `S24SIG=1919312263`, `S23SIG=3216085132`, `S22SIG=2207028069`,
  `S21SIG=1770773845`, `S20SIG=3226031347`, and `S19SIG=2088411722`.
- Build/smoke proves the executable launches, advances selected death visual
  samples after launch, contains no `source_stage35` strings, and still uses
  compact runtime renderer command tables rather than full pre-rendered
  framebuffer arrays.
- Item pickup, generalized death/drop, projectiles, explosions, broad monster
  AI, generalized combat, generalized sprite systems, map progression, UI
  systems, and real audio remain deferred.

## Released Slice: source_stage35_selected_dropped_shotgun_visual_boundary

Output:

```text
build/source_stage35_selected_dropped_shotgun_visual_boundary.exe
```

Released goal:

After stage34 proves one selected target can visibly die, cross the next
single aftermath boundary: the selected `P_KillMobj` shotgun-guy route
materializes its dropped shotgun through a bounded `P_SpawnMobj`-shaped record,
marks it `MF_DROPPED`, and draws one selected dropped-item world post from real
WAD data. This should still be a single selected route, not a generalized item
or death/drop system.

Released shape:

- Preserve the stage31 wall/flat redraw path, the stage33 impact/pain route,
  the stage34 death route, and the stage32 shotgun psprite path.
- Reuse the exact selected stage34 kill context: selected target mapthing `37`,
  mobj `28`, corpse position, death state, and deferred drop counter.
- Adds only the selected source-shaped drop creation needed by
  `P_KillMobj`: `MT_SHOTGUY -> MT_SHOTGUN`, `P_SpawnMobj` at the killed
  target's `x/y`, `ONFLOORZ`, `spawnstate=S_SHOT`, sprite `SPR_SHOT`, and
  `MF_DROPPED`.
- Draws the selected dropped shotgun after selected death posts and before the
  selected psprite overlay, using compact real WAD `SHOTA0` sprite-post command
  tables. The released visual sequence is: no drop, first visible death+drop
  frame, and next death+drop frame.
- Keep pickup deferred. Do not execute `P_TouchSpecialThing`, `P_GiveWeapon`,
  ammo/weapon grant, pickup message, item removal, respawn queue, or broad
  inventory/statusbar systems in stage35.
- Keeps runtime order explicit and measurable:
  setup -> clear -> walls/flats -> selected impact/pain posts -> selected
  death posts -> selected dropped-shotgun posts -> selected psprite posts ->
  signature -> present.
- The selected dropped shotgun is visible from the selected camera, so no
  alternate sample position was needed.

Validation status:

- Stage35 reports `S35SIG=3270148876`.
- The selected drop command counts are `0`, `44`, and `44`; selected drop pixel
  counts are `0`, `284`, and `284`.
- Preserved stage34 death intermediate signatures remain `2926869513`,
  `1191322670`, and `2513680424`; the new drop intermediate signatures are
  `2926869513`, `3057214504`, and `3299982258`; final framebuffer signatures
  are `2997224612`, `1668066382`, and `4078405109`.
- Stage34 through stage19 baselines are preserved, including
  `S34SIG=4027590938`, `S33SIG=1614948054`, `S32SIG=533488475`,
  `S31SIG=3593583171`, `S30SIG=3898523864`, `S29SIG=3738922932`,
  `S28SIG=2805406010`, `S27SIG=1735738182`, `S26SIG=132405987`,
  `S25SIG=1688844032`, `S24SIG=1919312263`, `S23SIG=3216085132`,
  `S22SIG=2207028069`, `S21SIG=1770773845`, `S20SIG=3226031347`, and
  `S19SIG=2088411722`.
- Synthetic tests cover selected `P_KillMobj` drop ordering,
  `P_SpawnMobj` field initialization, `MF_DROPPED`, state-to-render-frame
  mapping, dropped-shotgun patch/post command generation, runtime command-table
  selection, clear/wall-flat/impact/death/drop/psprite/present ordering,
  distinct framebuffer signatures with drop contribution, no full-frame byte
  arrays, deferred pickup/item/inventory systems, and preservation signatures.
- The smoke test launches the executable, observes the stage35 replay markers,
  proves distinct `FB35=` signatures, sees `DROP35=S_SHOT`,
  `DRPATCH35=SHOTA0`, `DRC35=44`, and `DRP35=284`, and verifies no
  `source_stage36` strings are present.

## Released Slice: source_stage36_selected_dropped_shotgun_pickup_feedback_boundary

Output:

```text
build/source_stage36_selected_dropped_shotgun_pickup_feedback_boundary.exe
```

Released goal:

After stage35 materializes and draws the selected dropped shotgun, connect
exactly one selected touch/pickup feedback boundary. The target route is the
same dropped `MT_SHOTGUN` item from the killed shotgun guy through
`P_TouchSpecialThing -> P_GiveWeapon(player, wp_shotgun, dropped=true)`, with a
bounded player-feedback result and a clear before/after render or state
signature. This is still not a broad inventory, HUD, item traversal, or respawn
system.

Released shape:

- Preserve the stage31 wall/flat, stage33 impact/pain, stage34 death, stage35
  dropped-shotgun, and stage32 psprite paths.
- Reuse the exact stage35 selected drop record: `SPR_SHOT`, `S_SHOT`,
  `MT_SHOTGUN`, `MF_SPECIAL | MF_DROPPED`, floor-z placement at the selected
  corpse position, and real `SHOTA0` visual posts.
- Triggers only the selected touch gate with a tightly reported one-item
  contact probe: `delta = special->z - toucher->z`, reject if outside
  `toucher->height` or below `-8*FRACUNIT`, require a live toucher, then switch
  on `special->sprite == SPR_SHOT`.
- Applies only the dropped-shotgun branch of `P_GiveWeapon`: call-equivalent
  `P_GiveWeapon(player, wp_shotgun, dropped=true)`, give one ammo clip via
  `weaponinfo[wp_shotgun].ammo`, set `weaponowned[wp_shotgun]` and
  `pendingweapon` only if not already owned, and report whether ammo, weapon,
  or both were granted.
- Removes the selected item if and only if `P_GiveWeapon` returns true. The
  released proof succeeds and `P_RemoveMobj` clears the selected dropped item
  from the final frame.
- Adds one compact feedback marker, not a broad HUD: `GOTSHOTGUN`,
  `sfx_wpnup` as a deferred sound-channel/event counter, bonus count, selected
  shell ammo/weapon-owned/pending-weapon fields, and final item-present state.
- Keeps the smoke path deterministic.
- Do not generalize pickup traversal, statusbar inventory, all item classes,
  dropped clip/chaingun branches, respawn queues, deathmatch weapon staying,
  broad thing removal, or audio playback.

Validation status:

- Synthetic tests cover selected touch z/reach ordering, live-toucher guard,
  `SPR_SHOT` dispatch, `MF_DROPPED` weapon pickup semantics, one-clip dropped
  shotgun ammo behavior, selected `P_GiveWeapon` return cases, selected
  `GOTSHOTGUN`/`sfx_wpnup` boundary, selected item removal, no respawn queue,
  no full-frame byte arrays, and absence of broad item classes.
- Synthetic renderer ordering tests prove the frame after pickup no longer
  draws the selected drop posts while preserving wall/flat,
  impact/pain, death, and psprite paths.
- Pinned replay/smoke proves the selected dropped shotgun can be touched,
  produces at least one measurable player-feedback signal, changes a runtime
  framebuffer or selected drop-present signature because the drop draw path is
  removed after pickup, preserves stage35 through stage19 signatures, and
  contains no `source_stage37` strings.
- Stage36 reports `S36SIG=397846180`.
- Stage36 final framebuffer signatures are `2997224612`, `1668066382`, and
  `1194192847`; the selected drop intermediate signatures are `2926869513`,
  `3057214504`, and `2513680424`.
- The final pickup frame reports `DROP36=REMOVED`, `DRC36=0`, `DRP36=0`,
  `PICK36=1`, `ITEM36=0`, `SHELL36=4`, `WOWN36=1`, `PEND36=2`,
  `MSG36=GOTSHOTGUN`, `SFX36=sfx_wpnup`, `SFXC36=1`, `BONUS36=6`, and
  `RQ36=0`.
- Stage35 through stage19 baselines are preserved, including
  `S35SIG=3270148876`, `S34SIG=4027590938`, `S33SIG=1614948054`,
  `S32SIG=533488475`, `S31SIG=3593583171`, `S30SIG=3898523864`,
  `S29SIG=3738922932`, `S28SIG=2805406010`, `S27SIG=1735738182`,
  `S26SIG=132405987`, `S25SIG=1688844032`, `S24SIG=1919312263`,
  `S23SIG=3216085132`, `S22SIG=2207028069`, `S21SIG=1770773845`,
  `S20SIG=3226031347`, and `S19SIG=2088411722`.

## Releasable Slice After That: source_stage37_selected_monster_attack_feedback_probe

Output:

```text
build/source_stage37_selected_monster_attack_feedback_probe.exe
```

Goal:

After stage36 closes the selected dropped-weapon feedback loop, return to the
selected living-monster route and cross one enemy attack feedback boundary. The
preferred target is the already-studied stage29 shotgun-guy attack-decision
route, advanced only far enough for one source-shaped enemy hitscan/pain result
against the player, with a bounded health/pain/message/sound or visual report.
This is not a generalized monster AI, chase, projectile, infighting, or player
death system.

Likely shape:

- Preserve the released renderer and selected combat visual bridges as
  baselines, but choose a clean selected enemy-attack replay rather than
  entangling it with the killed-and-dropped stage35/36 corpse route.
- Reuse stage29's selected shotgun-guy context up to the first honest
  attack-decision boundary, then source-read the narrow `A_SPosAttack` /
  `P_LineAttack` / `P_DamageMobj(player)` path needed for one deterministic
  enemy shotgun attack.
- Report or draw only the selected player feedback: health/armor delta,
  damage count, pain-state or palette/flash marker if cheap, selected sound
  boundary if reached, and deterministic framebuffer/state signatures.
- Keep player death, enemy kill/drop, generalized combat loops, projectiles,
  explosions, broad monster AI, infighting, generalized sprite traversal,
  statusbar rebuilds, and real audio playback deferred.

Validation shape:

- Synthetic tests for selected enemy attack state/action ordering, line attack
  target selection, player damage mutation, feedback marker/reporting, absence
  of generalized AI/projectiles/death/drop, preservation signatures, and no
  `source_stage38` strings.
- Pinned smoke proving one selected enemy attack produces a measurable player
  feedback signal while the existing stage36 and stage35 baselines remain
  inspectable.

## Future Backlog

Likely later slices after stage37, intentionally kept mostly as headlines:

- `source_stage38_selected_projectile_or_barrel_visual_probe`: one selected
  projectile/barrel route, not a full projectile system.
- `source_stage39_generalized_sprite_traversal_and_sorting_bridge`: replace
  selected world-post tables with a bounded source-shaped sprite traversal
  bridge.
- `source_stage40_statusbar_weapon_ammo_feedback_bridge`
- `source_stage41_unified_live_tick_render_loop_probe`
- `source_stage42_map_progression_and_demo_determinism_probe`
- `source_stage43_menu_automap_save_load_shells`
- `source_stage44_real_audio_device_output_and_mixer_integration`
- `source_stage45_playable_shareware_style_vertical_slice`

At that point the fixed render harness can start becoming a small playable
demo, not just a chain of source-shaped renderer/gameplay proofs.
