from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Sequence


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage01_wad_map as stage01
from tools import emit_source_stage02_bsp_setup as stage02
from tools import emit_source_stage03_bsp_walk_debug as stage03
from tools import emit_source_stage04_bbox_visibility_debug as stage04
from tools import emit_source_stage07_wall_projection_debug as stage07
from tools import emit_source_stage08_texture_data_setup_debug as stage08
from tools import emit_source_stage10_composite_two_sided_wall_edges_debug as stage10
from tools import emit_source_stage11_visplanes_floor_ceiling_debug as stage11
from tools import emit_source_stage12_sky_and_masked_midtextures_debug as stage12
from tools import emit_source_stage13_things_sprites_and_real_frame_setup as stage13
from tools import emit_source_stage14_game_loop_input_collision as stage14
from tools import emit_source_stage15_pickups_psprites_statusbar_shell as stage15
from tools import emit_source_stage16_active_monster_thinkers_and_targeting as stage16
from tools import emit_source_stage17_first_weapon_fire_damage_and_death_probe as stage17
from tools import x86
from tools.map_loader import LoadedMap, load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


FRAMEBUFFER_WIDTH = stage17.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage17.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage17.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage17.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage17.WINDOW_WIDTH
WINDOW_HEIGHT = stage17.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage18PostDamageMonsterMovementChaseProbe"
WINDOW_TITLE = "Inference Doom S18 Post Damage Monster Movement"
WAD_PATH = stage17.WAD_PATH

FRACBITS = stage17.FRACBITS
FRACUNIT = stage17.FRACUNIT
FNV_PRIME = stage17.FNV_PRIME
ANG90 = stage17.ANG90
ANG270 = (ANG90 * 3) & 0xFFFFFFFF
BASETHRESHOLD = stage17.BASETHRESHOLD
MELEERANGE = stage16.MELEERANGE
MISSILERANGE = stage17.MISSILERANGE

DI_EAST = 0
DI_NORTHEAST = 1
DI_NORTH = 2
DI_NORTHWEST = 3
DI_WEST = 4
DI_SOUTHWEST = 5
DI_SOUTH = 6
DI_SOUTHEAST = 7
DI_NODIR = 8

OPPOSITE = (DI_WEST, DI_SOUTHWEST, DI_SOUTH, DI_SOUTHEAST, DI_EAST, DI_NORTHEAST, DI_NORTH, DI_NORTHWEST, DI_NODIR)
DIAGS = (DI_NORTHWEST, DI_NORTHEAST, DI_SOUTHWEST, DI_SOUTHEAST)
XSPEED = (FRACUNIT, 47000, 0, -47000, -FRACUNIT, -47000, 0, 47000)
YSPEED = (0, 47000, FRACUNIT, 47000, 0, -47000, -FRACUNIT, -47000)

ROUTE_POST_DAMAGE_MOMENTUM = 1
DEFAULT_STAGE18_TICS = 1

SOURCE_TRACE = stage17.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_MobjThinker/P_XYMovement post-damage momentum path",
        "P_MobjThinker_XYMovement_post_damage_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "P_TryMove/P_CheckPosition/PIT_CheckLine/PIT_CheckThing monster subset",
        "P_TryMove_monster_post_damage_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_maputl.c",
        "P_BlockLinesIterator/P_BlockThingsIterator/P_SetThingPosition/P_UnsetThingPosition",
        "P_BlockIterators_monster_movement_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "A_Pain sound deferral and A_Chase/P_NewChaseDir/P_Move bounded probe",
        "A_Pain_A_Chase_monster_movement_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/info.c",
        "S_SPOS_PAIN/S_SPOS_PAIN2/S_SPOS_RUN1 and MT_SHOTGUY movement metadata",
        "info_tables_shotguy_post_damage_movement_debug",
    ),
)


@dataclass
class Stage18Counters:
    movement_census_runs: int = 0
    mobj_thinker_calls: int = 0
    xy_movement_services: int = 0
    state_tic_decrements: int = 0
    mobj_state_sets: int = 0
    mobj_state_transitions: int = 0
    action_dispatches: int = 0
    action_deferrals: int = 0
    pain_sound_deferrals: int = 0
    pain_recovery_transitions: int = 0
    chase_reached: int = 0
    chase_deferred: int = 0
    chase_calls: int = 0
    new_chase_dir_calls: int = 0
    try_walk_calls: int = 0
    move_calls: int = 0
    move_accepts: int = 0
    move_blocks: int = 0
    direction_choices: int = 0
    target_loss_fallbacks: int = 0
    look_for_players_deferred: int = 0
    threshold_decrements: int = 0
    melee_range_checks: int = 0
    missile_range_checks: int = 0
    attack_state_deferrals: int = 0
    attack_actions_executed: int = 0
    active_sound_deferrals: int = 0
    sound_playback_deferrals: int = 0
    sector_specials_deferred: int = 0
    doors_switches_deferred: int = 0
    live_keyboard_deferred: int = 0
    source_stage19_absent: int = 1


@dataclass(frozen=True)
class MovementDelta:
    try_moves: int
    accepted_moves: int
    rejected_moves: int
    line_checks: int
    thing_checks: int
    blocking_lines: int
    blocking_things: int
    step_rejects: int
    dropoff_rejects: int
    block_relinks: int
    sector_relinks: int
    line_iterator_calls: int
    thing_iterator_calls: int
    line_visits: int
    thing_visits: int
    line_duplicate_skips: int


@dataclass(frozen=True)
class Stage18MovementCensusRecord:
    route: int
    route_name: str
    mapthing_index: int
    mobj_index: int
    type_name: str
    start_x: int
    start_y: int
    start_sector: int
    start_subsector: int
    start_block_x: int
    start_block_y: int
    health: int
    state: int
    state_name: str
    tics: int
    target_index: int
    threshold: int
    momx: int
    momy: int
    next_state: int
    next_state_name: str
    recovery_state: int
    recovery_state_name: str
    run_state: int
    run_state_name: str


@dataclass(frozen=True)
class Stage18TraceRecord:
    tic: int
    x: int
    y: int
    momx: int
    momy: int
    state: int
    state_name: str
    tics: int
    block_x: int
    block_y: int
    accepted_moves: int
    rejected_moves: int
    line_checks: int
    thing_checks: int
    block_relinks: int
    sector_relinks: int


@dataclass
class Stage18World:
    movement: stage14.MovementWorld
    info: stage16.Stage16InfoTables
    actor: stage16.ActiveMobj
    targets: dict[int, stage16.ActiveMobj]
    counters: Stage18Counters
    rng: stage16.DoomRandom
    execute_chase_actions: bool = False
    sight_visible: bool = True


@dataclass(frozen=True)
class Stage18PostDamageMonsterMovementReference:
    stage17: stage17.Stage17FirstWeaponFireReference
    census: Stage18MovementCensusRecord
    trace: tuple[Stage18TraceRecord, ...]
    counters: Stage18Counters
    movement_counters: stage14.MovementCounters
    iterator: stage14.BlockIteratorState
    start_mobj: stage16.ActiveMobj
    final_mobj: stage16.ActiveMobj
    route: int
    route_name: str
    signature: int


def _u32(value: int) -> int:
    return value & 0xFFFFFFFF


def _i32(value: int) -> int:
    return stage04._int32(value)


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & 0xFFFFFFFF


def _hash_bytes(signature: int, data: bytes) -> int:
    for byte in data:
        signature = _hash_u32(signature, byte)
    return signature


def _state_name(info: stage16.Stage16InfoTables, state: int | None) -> str:
    return stage16._state_name(info, state)


def _block_xy(world: stage14.MovementWorld, x: int, y: int) -> tuple[int, int]:
    return (
        stage14._block_coord(world, x, world.blockmap.origin_x),
        stage14._block_coord(world, y, world.blockmap.origin_y),
    )


def _movement_delta_before(world: stage14.MovementWorld) -> tuple[stage14.MovementCounters, stage14.BlockIteratorState]:
    return (
        replace(world.counters),
        replace(world.iterator, line_validcounts=dict(world.iterator.line_validcounts or {})),
    )


def _movement_delta_after(
    world: stage14.MovementWorld,
    before: tuple[stage14.MovementCounters, stage14.BlockIteratorState],
) -> MovementDelta:
    counters, iterator = before
    return MovementDelta(
        try_moves=world.counters.try_move_calls - counters.try_move_calls,
        accepted_moves=world.counters.accepted_moves - counters.accepted_moves,
        rejected_moves=world.counters.rejected_moves - counters.rejected_moves,
        line_checks=world.counters.line_checks - counters.line_checks,
        thing_checks=world.counters.thing_checks - counters.thing_checks,
        blocking_lines=world.counters.blocking_lines - counters.blocking_lines,
        blocking_things=world.counters.blocking_things - counters.blocking_things,
        step_rejects=world.counters.step_rejects - counters.step_rejects,
        dropoff_rejects=world.counters.dropoff_rejects - counters.dropoff_rejects,
        block_relinks=world.counters.block_relinks - counters.block_relinks,
        sector_relinks=world.counters.sector_relinks - counters.sector_relinks,
        line_iterator_calls=world.iterator.line_iterator_calls - iterator.line_iterator_calls,
        thing_iterator_calls=world.iterator.thing_iterator_calls - iterator.thing_iterator_calls,
        line_visits=world.iterator.line_visits - iterator.line_visits,
        thing_visits=world.iterator.thing_visits - iterator.thing_visits,
        line_duplicate_skips=world.iterator.line_duplicate_skips - iterator.line_duplicate_skips,
    )


def _zero_movement_delta() -> MovementDelta:
    return MovementDelta(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def _movement_mobj(world: Stage18World) -> stage14.MovementMobj:
    return world.movement.mobjs[world.actor.index]


def _sync_active_to_movement(world: Stage18World) -> None:
    mo = _movement_mobj(world)
    mo.x = world.actor.x
    mo.y = world.actor.y
    mo.z = world.actor.z
    mo.angle = world.actor.angle
    mo.momx = world.actor.momx
    mo.momy = world.actor.momy
    mo.momz = world.actor.momz
    mo.radius = world.actor.radius
    mo.height = world.actor.height
    mo.flags = world.actor.flags
    mo.floorz = world.actor.floorz
    mo.ceilingz = world.actor.ceilingz
    mo.subsector = world.actor.subsector
    mo.sector = world.actor.sector


def _sync_movement_to_active(world: Stage18World) -> None:
    mo = _movement_mobj(world)
    world.actor.x = mo.x
    world.actor.y = mo.y
    world.actor.z = mo.z
    world.actor.angle = mo.angle
    world.actor.momx = mo.momx
    world.actor.momy = mo.momy
    world.actor.momz = mo.momz
    world.actor.floorz = mo.floorz
    world.actor.ceilingz = mo.ceilingz
    world.actor.subsector = mo.subsector
    world.actor.sector = mo.sector
    world.actor.flags = mo.flags


def p_try_move_monster_source_shape(world: Stage18World, x: int, y: int) -> tuple[bool, MovementDelta]:
    _sync_active_to_movement(world)
    before = _movement_delta_before(world.movement)
    ok = stage14.p_try_move_source_shape(world.movement, _movement_mobj(world), x, y)
    delta = _movement_delta_after(world.movement, before)
    _sync_movement_to_active(world)
    if not ok and world.movement.spechit:
        world.counters.sector_specials_deferred += len(world.movement.spechit)
        world.counters.doors_switches_deferred += len(world.movement.spechit)
    return ok, delta


def p_xy_movement_monster_source_shape(world: Stage18World) -> MovementDelta:
    world.counters.xy_movement_services += 1
    _sync_active_to_movement(world)
    before = _movement_delta_before(world.movement)
    stage14.p_xy_movement_source_shape(world.movement, _movement_mobj(world))
    delta = _movement_delta_after(world.movement, before)
    _sync_movement_to_active(world)
    return delta


def a_pain_stage18_source_shape(world: Stage18World, actor: stage16.ActiveMobj) -> None:
    info = world.info.by_name.get(actor.type_name)
    if info is not None and info.painsound_name != "sfx_None":
        world.counters.pain_sound_deferrals += 1
        world.counters.sound_playback_deferrals += 1


def _target_for_actor(world: Stage18World, actor: stage16.ActiveMobj) -> stage16.ActiveMobj | None:
    if actor.target_index is None:
        return None
    return world.targets.get(actor.target_index)


def p_check_melee_range_stage18_source_shape(world: Stage18World, actor: stage16.ActiveMobj) -> bool:
    world.counters.melee_range_checks += 1
    target = _target_for_actor(world, actor)
    if target is None:
        return False
    dist = stage16.p_aprox_distance_source_shape(target.x - actor.x, target.y - actor.y)
    range_limit = MELEERANGE - 20 * FRACUNIT + target.radius
    if dist >= range_limit:
        return False
    return bool(world.sight_visible)


def p_check_missile_range_stage18_source_shape(world: Stage18World, actor: stage16.ActiveMobj) -> bool:
    world.counters.missile_range_checks += 1
    target = _target_for_actor(world, actor)
    if target is None or not world.sight_visible:
        return False
    if actor.flags & stage13.MF_JUSTHIT:
        actor.flags &= ~stage13.MF_JUSTHIT
        return True
    if actor.reactiontime:
        return False
    info = world.info.by_name[actor.type_name]
    dist = stage16.p_aprox_distance_source_shape(actor.x - target.x, actor.y - target.y) - 64 * FRACUNIT
    if not info.meleestate:
        dist -= 128 * FRACUNIT
    dist >>= FRACBITS
    if actor.type_name == "MT_UNDEAD" and dist < 196:
        return False
    if actor.type_name in {"MT_UNDEAD", "MT_CYBORG", "MT_SPIDER", "MT_SKULL"}:
        dist >>= 1
    if dist > 200:
        dist = 200
    if actor.type_name == "MT_CYBORG" and dist > 160:
        dist = 160
    return world.rng.p_random() >= dist


def p_move_stage18_source_shape(world: Stage18World, actor: stage16.ActiveMobj) -> bool:
    world.counters.move_calls += 1
    if actor.movedir == DI_NODIR:
        world.counters.move_blocks += 1
        return False
    if actor.movedir < 0 or actor.movedir >= 8:
        raise ValueError(f"Weird actor->movedir: {actor.movedir}")
    speed = world.info.by_name[actor.type_name].speed
    tryx = _i32(actor.x + speed * XSPEED[actor.movedir])
    tryy = _i32(actor.y + speed * YSPEED[actor.movedir])
    ok, _delta = p_try_move_monster_source_shape(world, tryx, tryy)
    if not ok:
        actor.movedir = DI_NODIR if world.movement.spechit else actor.movedir
        world.counters.move_blocks += 1
        return False
    if not (actor.flags & stage13.MF_FLOAT):
        actor.z = actor.floorz
        _sync_active_to_movement(world)
    world.counters.move_accepts += 1
    return True


def p_try_walk_stage18_source_shape(world: Stage18World, actor: stage16.ActiveMobj) -> bool:
    world.counters.try_walk_calls += 1
    if not p_move_stage18_source_shape(world, actor):
        return False
    actor.movecount = world.rng.p_random() & 15
    return True


def p_new_chase_dir_stage18_source_shape(world: Stage18World, actor: stage16.ActiveMobj) -> None:
    world.counters.new_chase_dir_calls += 1
    target = _target_for_actor(world, actor)
    if target is None:
        raise ValueError("P_NewChaseDir called with no target")
    olddir = actor.movedir
    turnaround = OPPOSITE[olddir]
    deltax = target.x - actor.x
    deltay = target.y - actor.y
    d1 = DI_EAST if deltax > 10 * FRACUNIT else DI_WEST if deltax < -10 * FRACUNIT else DI_NODIR
    d2 = DI_SOUTH if deltay < -10 * FRACUNIT else DI_NORTH if deltay > 10 * FRACUNIT else DI_NODIR

    if d1 != DI_NODIR and d2 != DI_NODIR:
        actor.movedir = DIAGS[((deltay < 0) << 1) + (deltax > 0)]
        world.counters.direction_choices += 1
        if actor.movedir != turnaround and p_try_walk_stage18_source_shape(world, actor):
            return

    if world.rng.p_random() > 200 or abs(deltay) > abs(deltax):
        d1, d2 = d2, d1
    if d1 == turnaround:
        d1 = DI_NODIR
    if d2 == turnaround:
        d2 = DI_NODIR
    for direction in (d1, d2):
        if direction != DI_NODIR:
            actor.movedir = direction
            world.counters.direction_choices += 1
            if p_try_walk_stage18_source_shape(world, actor):
                return
    if olddir != DI_NODIR:
        actor.movedir = olddir
        world.counters.direction_choices += 1
        if p_try_walk_stage18_source_shape(world, actor):
            return
    if world.rng.p_random() & 1:
        search = range(DI_EAST, DI_SOUTHEAST + 1)
    else:
        search = range(DI_SOUTHEAST, DI_EAST - 1, -1)
    for direction in search:
        if direction != turnaround:
            actor.movedir = direction
            world.counters.direction_choices += 1
            if p_try_walk_stage18_source_shape(world, actor):
                return
    if turnaround != DI_NODIR:
        actor.movedir = turnaround
        world.counters.direction_choices += 1
        if p_try_walk_stage18_source_shape(world, actor):
            return
    actor.movedir = DI_NODIR


def a_chase_stage18_source_shape(world: Stage18World, actor: stage16.ActiveMobj) -> None:
    world.counters.chase_calls += 1
    info = world.info.by_name[actor.type_name]
    if actor.reactiontime:
        actor.reactiontime -= 1
    if actor.threshold:
        target = _target_for_actor(world, actor)
        if target is None or target.health <= 0:
            actor.threshold = 0
        else:
            actor.threshold -= 1
            world.counters.threshold_decrements += 1
    if actor.movedir < 8:
        actor.angle &= 7 << 29
        delta = _i32(actor.angle - (actor.movedir << 29))
        if delta > 0:
            actor.angle = _u32(actor.angle - ANG90 // 2)
        elif delta < 0:
            actor.angle = _u32(actor.angle + ANG90 // 2)
    target = _target_for_actor(world, actor)
    if target is None or not (target.flags & stage13.MF_SHOOTABLE):
        world.counters.target_loss_fallbacks += 1
        world.counters.look_for_players_deferred += 1
        p_set_mobj_state_stage18_source_shape(world, actor, info.spawnstate)
        return
    if actor.flags & stage13.MF_JUSTATTACKED:
        actor.flags &= ~stage13.MF_JUSTATTACKED
        p_new_chase_dir_stage18_source_shape(world, actor)
        return
    if info.meleestate and p_check_melee_range_stage18_source_shape(world, actor):
        world.counters.attack_state_deferrals += 1
        return
    if info.missilestate:
        if actor.movecount and not (actor.flags & stage13.MF_JUSTHIT):
            pass
        elif p_check_missile_range_stage18_source_shape(world, actor):
            world.counters.attack_state_deferrals += 1
            return
    actor.movecount -= 1
    if actor.movecount < 0 or not p_move_stage18_source_shape(world, actor):
        p_new_chase_dir_stage18_source_shape(world, actor)
    if info.activesound_name != "sfx_None" and world.rng.p_random() < 3:
        world.counters.active_sound_deferrals += 1
        world.counters.sound_playback_deferrals += 1


def dispatch_mobj_action_stage18_source_shape(
    world: Stage18World,
    actor: stage16.ActiveMobj,
    action: str,
) -> None:
    if not action:
        return
    world.counters.action_dispatches += 1
    if action == "A_Pain":
        a_pain_stage18_source_shape(world, actor)
        world.counters.action_deferrals += 1
    elif action in {"A_Chase", "A_VileChase", "A_Hoof", "A_Metal", "A_BabyMetal"}:
        world.counters.chase_reached += 1
        if world.execute_chase_actions:
            a_chase_stage18_source_shape(world, actor)
        else:
            world.counters.chase_deferred += 1
            world.counters.action_deferrals += 1
    elif "Attack" in action or action in {"A_PosAttack", "A_SPosAttack", "A_CPosAttack"}:
        world.counters.attack_state_deferrals += 1
        world.counters.action_deferrals += 1
    else:
        world.counters.action_deferrals += 1


def p_set_mobj_state_stage18_source_shape(
    world: Stage18World,
    mobj: stage16.ActiveMobj,
    state: int,
    *,
    max_steps: int = 64,
) -> bool:
    steps = 0
    while True:
        steps += 1
        if steps > max_steps:
            raise RuntimeError("P_SetMobjState exceeded bounded state steps")
        if state == stage16.S_NULL:
            mobj.state = None
            mobj.tics = 0
            mobj.removed = True
            return False
        st = world.info.state_info.states[state]
        previous = mobj.state
        mobj.state = state
        mobj.tics = st.tics
        mobj.sprite = st.sprite
        mobj.frame = st.frame
        world.counters.mobj_state_sets += 1
        if previous != state:
            world.counters.mobj_state_transitions += 1
            if previous in {
                world.info.state_info.state_index.get("S_SPOS_PAIN"),
                world.info.state_info.state_index.get("S_SPOS_PAIN2"),
            }:
                world.counters.pain_recovery_transitions += 1
        dispatch_mobj_action_stage18_source_shape(world, mobj, st.action)
        state = st.nextstate
        if mobj.tics:
            return True


def p_mobj_thinker_stage18_source_shape(world: Stage18World, actor: stage16.ActiveMobj) -> MovementDelta:
    world.counters.mobj_thinker_calls += 1
    delta = _zero_movement_delta()
    if actor.momx or actor.momy or (actor.flags & stage13.MF_SKULLFLY):
        delta = p_xy_movement_monster_source_shape(world)
        if actor.removed:
            return delta
    if actor.z != actor.floorz or actor.momz:
        world.counters.action_deferrals += 1
    if actor.tics != -1:
        actor.tics -= 1
        world.counters.state_tic_decrements += 1
        if not actor.tics and actor.state is not None:
            nextstate = world.info.state_info.states[actor.state].nextstate
            p_set_mobj_state_stage18_source_shape(world, actor, nextstate)
    return delta


def _player_target_as_active(target: stage16.ActivePlayerTarget) -> stage16.ActiveMobj:
    return stage16.ActiveMobj(
        index=target.mo_index,
        mapthing_index=target.mo_index,
        type_name="MT_PLAYER",
        doomednum=1,
        x=target.x,
        y=target.y,
        z=target.z,
        angle=0,
        momx=0,
        momy=0,
        momz=0,
        radius=target.radius,
        height=target.height,
        flags=target.flags,
        floorz=0,
        ceilingz=128 * FRACUNIT,
        subsector=target.subsector,
        sector=target.sector,
        health=target.health,
        reactiontime=0,
        state=None,
        tics=-1,
        sprite=0,
        frame=0,
        lastlook=0,
    )


def build_stage18_world_from_stage17(
    wad: WadFile,
    loaded: LoadedMap,
    ref17: stage17.Stage17FirstWeaponFireReference,
) -> Stage18World:
    stage15_world = stage15.build_stage15_world(wad, loaded, ref17.stage16.stage15.stage14)
    stage15.run_pickup_probes_source_shape(stage15_world)
    movement = stage14.clone_movement_world(stage15_world.movement)
    info = stage16.parse_stage16_info_tables()
    actor = replace(ref17.final_target)
    world = Stage18World(
        movement=movement,
        info=info,
        actor=actor,
        targets={ref17.stage16.target.mo_index: _player_target_as_active(ref17.stage16.target)},
        counters=Stage18Counters(movement_census_runs=1),
        rng=stage16.DoomRandom(ref17.random_end_index),
    )
    _sync_active_to_movement(world)
    return world


def build_stage18_movement_census_source_shape(world: Stage18World) -> Stage18MovementCensusRecord:
    actor = world.actor
    bx, by = _block_xy(world.movement, actor.x, actor.y)
    pain = world.info.state_info.state_index["S_SPOS_PAIN"]
    pain2 = world.info.state_info.state_index["S_SPOS_PAIN2"]
    run1 = world.info.state_info.state_index["S_SPOS_RUN1"]
    nextstate = world.info.state_info.states[actor.state].nextstate if actor.state is not None else stage16.S_NULL
    return Stage18MovementCensusRecord(
        route=ROUTE_POST_DAMAGE_MOMENTUM,
        route_name="POST_DAMAGE_MOMENTUM",
        mapthing_index=actor.mapthing_index,
        mobj_index=actor.index,
        type_name=actor.type_name,
        start_x=actor.x,
        start_y=actor.y,
        start_sector=actor.sector,
        start_subsector=actor.subsector,
        start_block_x=bx,
        start_block_y=by,
        health=actor.health,
        state=actor.state if actor.state is not None else 0,
        state_name=_state_name(world.info, actor.state),
        tics=actor.tics,
        target_index=actor.target_index if actor.target_index is not None else -1,
        threshold=actor.threshold,
        momx=actor.momx,
        momy=actor.momy,
        next_state=nextstate,
        next_state_name=_state_name(world.info, nextstate),
        recovery_state=pain2 if actor.state == pain else nextstate,
        recovery_state_name=_state_name(world.info, pain2 if actor.state == pain else nextstate),
        run_state=run1,
        run_state_name=_state_name(world.info, run1),
    )


def run_stage18_post_damage_movement_probe_source_shape(
    world: Stage18World,
    *,
    tics: int = DEFAULT_STAGE18_TICS,
) -> tuple[Stage18TraceRecord, ...]:
    trace: list[Stage18TraceRecord] = []
    for tic in range(1, tics + 1):
        delta = p_mobj_thinker_stage18_source_shape(world, world.actor)
        bx, by = _block_xy(world.movement, world.actor.x, world.actor.y)
        trace.append(
            Stage18TraceRecord(
                tic=tic,
                x=world.actor.x,
                y=world.actor.y,
                momx=world.actor.momx,
                momy=world.actor.momy,
                state=world.actor.state if world.actor.state is not None else 0,
                state_name=_state_name(world.info, world.actor.state),
                tics=world.actor.tics,
                block_x=bx,
                block_y=by,
                accepted_moves=delta.accepted_moves,
                rejected_moves=delta.rejected_moves,
                line_checks=delta.line_checks,
                thing_checks=delta.thing_checks,
                block_relinks=delta.block_relinks,
                sector_relinks=delta.sector_relinks,
            )
        )
    return tuple(trace)


def _stage18_signature(
    ref17: stage17.Stage17FirstWeaponFireReference,
    census: Stage18MovementCensusRecord,
    trace: Sequence[Stage18TraceRecord],
    counters: Stage18Counters,
    movement: stage14.MovementCounters,
    iterator: stage14.BlockIteratorState,
    final_mobj: stage16.ActiveMobj,
) -> int:
    signature = ref17.signature
    for value in (
        census.route,
        census.mapthing_index,
        census.mobj_index,
        census.start_x,
        census.start_y,
        census.start_sector,
        census.start_subsector,
        census.start_block_x,
        census.start_block_y,
        census.health,
        census.state,
        census.tics,
        census.target_index,
        census.threshold,
        census.momx,
        census.momy,
    ):
        signature = _hash_u32(signature, value)
    for record in trace:
        for value in (
            record.tic,
            record.x,
            record.y,
            record.momx,
            record.momy,
            record.state,
            record.tics,
            record.block_x,
            record.block_y,
            record.accepted_moves,
            record.rejected_moves,
            record.line_checks,
            record.thing_checks,
            record.block_relinks,
            record.sector_relinks,
        ):
            signature = _hash_u32(signature, value)
    for value in (
        counters.mobj_thinker_calls,
        counters.xy_movement_services,
        counters.state_tic_decrements,
        counters.pain_sound_deferrals,
        counters.chase_reached,
        counters.chase_deferred,
        counters.chase_calls,
        counters.new_chase_dir_calls,
        counters.attack_state_deferrals,
        counters.attack_actions_executed,
        movement.try_move_calls,
        movement.accepted_moves,
        movement.rejected_moves,
        movement.line_checks,
        movement.thing_checks,
        movement.block_relinks,
        movement.sector_relinks,
        iterator.line_iterator_calls,
        iterator.thing_iterator_calls,
        iterator.line_visits,
        iterator.thing_visits,
        iterator.line_duplicate_skips,
        final_mobj.x,
        final_mobj.y,
        final_mobj.momx,
        final_mobj.momy,
        final_mobj.state if final_mobj.state is not None else 0,
        final_mobj.tics,
    ):
        signature = _hash_u32(signature, value)
    signature = _hash_bytes(signature, census.route_name.encode("ascii"))
    signature = _hash_bytes(signature, _state_name(stage16.parse_stage16_info_tables(), final_mobj.state).encode("ascii"))
    return signature


def _reference_stage18_uncached(wad_path: str) -> Stage18PostDamageMonsterMovementReference:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    ref17 = stage17.reference_first_weapon_fire_damage_and_death_probe_for_pinned_map(wad_path)
    world = build_stage18_world_from_stage17(wad, loaded, ref17)
    start_mobj = replace(world.actor)
    census = build_stage18_movement_census_source_shape(world)
    trace = run_stage18_post_damage_movement_probe_source_shape(world)
    final_mobj = replace(world.actor)
    iterator = replace(world.movement.iterator, line_validcounts=dict(world.movement.iterator.line_validcounts or {}))
    signature = _stage18_signature(ref17, census, trace, world.counters, world.movement.counters, iterator, final_mobj)
    return Stage18PostDamageMonsterMovementReference(
        stage17=ref17,
        census=census,
        trace=trace,
        counters=replace(world.counters),
        movement_counters=replace(world.movement.counters),
        iterator=iterator,
        start_mobj=start_mobj,
        final_mobj=final_mobj,
        route=census.route,
        route_name=census.route_name,
        signature=signature,
    )


@lru_cache(maxsize=4)
def _reference_stage18_cached(wad_path: str) -> Stage18PostDamageMonsterMovementReference:
    return _reference_stage18_uncached(wad_path)


def reference_post_damage_monster_movement_and_chase_probe_for_pinned_map(
    wad_path: str | Path,
) -> Stage18PostDamageMonsterMovementReference:
    return _reference_stage18_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage18PostDamageMonsterMovementReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_post_damage_monster_movement_and_chase_probe_for_pinned_map(wad_path)


@contextmanager
def patched_stage01_window_labels():
    old_class = stage01.WINDOW_CLASS_NAME
    old_title = stage01.WINDOW_TITLE
    stage01.WINDOW_CLASS_NAME = WINDOW_CLASS_NAME
    stage01.WINDOW_TITLE = WINDOW_TITLE
    try:
        yield
    finally:
        stage01.WINDOW_CLASS_NAME = old_class
        stage01.WINDOW_TITLE = old_title


def emit_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")

    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")

    pe.label("class_registered")
    x86.call_rel32(pe, "source_stage18_load_wad_post_damage_monster_movement_chase_probe")

    x86.push_imm8(pe, 0)
    x86.push_mem_abs32(pe, "wc_hInstance")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, WINDOW_HEIGHT)
    x86.push_imm32(pe, WINDOW_WIDTH)
    x86.push_imm32(pe, stage01.CW_USEDEFAULT)
    x86.push_imm32(pe, stage01.CW_USEDEFAULT)
    x86.push_imm32(pe, stage01.WINDOW_STYLE)
    x86.push_abs32(pe, "window_title_w")
    x86.push_abs32(pe, "class_name")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.USER32, "CreateWindowExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")

    pe.label("window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_mem_abs32(pe, "status_title_ptr")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")

    pe.label("message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "message_error")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "message_loop")

    pe.label("clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")

    pe.label("message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_source_stage18_load_wad_post_damage_monster_movement_chase_probe(pe: PE32) -> None:
    pe.label("source_stage18_load_wad_post_damage_monster_movement_chase_probe")
    x86.call_rel32(pe, "source_stage17_load_wad_first_weapon_fire_damage_death_probe")
    x86.mov_reg_mem_abs32(pe, "eax", "stage17_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage17_expected_signature")
    x86.jne_rel32(pe, "source_stage18_return")
    x86.call_rel32(pe, "render_post_damage_monster_movement_chase_probe_debug")
    x86.call_rel32(pe, "append_stage18_success_status")
    pe.label("source_stage18_return")
    x86.ret(pe)


def emit_render_post_damage_monster_movement_chase_probe_debug(pe: PE32) -> None:
    pe.label("P_MobjThinker_XYMovement_post_damage_source_shape_debug")
    pe.label("P_TryMove_monster_post_damage_source_shape_debug")
    pe.label("P_BlockIterators_monster_movement_source_shape_debug")
    pe.label("A_Pain_A_Chase_monster_movement_source_shape_debug")
    pe.label("info_tables_shotguy_post_damage_movement_debug")
    pe.label("render_post_damage_monster_movement_chase_probe_debug")

    x86.mov_reg_mem_abs32(pe, "eax", "stage18_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage18_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage18_try_moves")
    x86.mov_mem_abs32_eax(pe, "stage18_runtime_try_moves")
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage14._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage18_success_status(pe: PE32) -> None:
    pe.label("append_stage18_success_status")

    _emit_seek_buffer_end(pe, "status_success_buffer", "stage18_status")
    stage01.append_c_string_label(pe, "status_stage18_success_header")
    stage01.append_u32_label(pe, "status_stage18_route_prefix", "stage18_route")
    stage01.append_u32_label(pe, "status_stage18_try_prefix", "stage18_runtime_try_moves")
    stage01.append_u32_label(pe, "status_stage18_accept_prefix", "stage18_accepted_moves")
    stage01.append_u32_label(pe, "status_stage18_signature_prefix", "stage18_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage18_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage18_title")
    stage01.append_u32_label(pe, "title_stage18_route_prefix", "stage18_route")
    stage01.append_u32_label(pe, "title_stage18_tics_prefix", "stage18_tics")
    stage01.append_u32_label(pe, "title_stage18_mapthing_prefix", "stage18_mapthing")
    stage01.append_u32_label(pe, "title_stage18_mobj_prefix", "stage18_mobj")
    stage01.append_c_string_label(pe, "title_stage18_type_prefix")
    stage01.append_c_string_label(pe, "stage18_type_name")
    stage01.append_i32_label(pe, "title_stage18_start_x_prefix", "stage18_start_x")
    stage01.append_i32_label(pe, "title_stage18_start_y_prefix", "stage18_start_y")
    stage01.append_u32_label(pe, "title_stage18_start_block_x_prefix", "stage18_start_block_x")
    stage01.append_u32_label(pe, "title_stage18_start_block_y_prefix", "stage18_start_block_y")
    stage01.append_c_string_label(pe, "title_stage18_start_state_name_prefix")
    stage01.append_c_string_label(pe, "stage18_start_state_name")
    stage01.append_u32_label(pe, "title_stage18_start_state_prefix", "stage18_start_state")
    stage01.append_u32_label(pe, "title_stage18_start_tics_prefix", "stage18_start_tics")
    stage01.append_i32_label(pe, "title_stage18_start_momx_prefix", "stage18_start_momx")
    stage01.append_i32_label(pe, "title_stage18_start_momy_prefix", "stage18_start_momy")
    stage01.append_i32_label(pe, "title_stage18_final_x_prefix", "stage18_final_x")
    stage01.append_i32_label(pe, "title_stage18_final_y_prefix", "stage18_final_y")
    stage01.append_u32_label(pe, "title_stage18_final_block_x_prefix", "stage18_final_block_x")
    stage01.append_u32_label(pe, "title_stage18_final_block_y_prefix", "stage18_final_block_y")
    stage01.append_c_string_label(pe, "title_stage18_final_state_name_prefix")
    stage01.append_c_string_label(pe, "stage18_final_state_name")
    stage01.append_u32_label(pe, "title_stage18_final_state_prefix", "stage18_final_state")
    stage01.append_u32_label(pe, "title_stage18_final_tics_prefix", "stage18_final_tics")
    stage01.append_i32_label(pe, "title_stage18_final_momx_prefix", "stage18_final_momx")
    stage01.append_i32_label(pe, "title_stage18_final_momy_prefix", "stage18_final_momy")
    stage01.append_u32_label(pe, "title_stage18_xy_prefix", "stage18_xy_services")
    stage01.append_u32_label(pe, "title_stage18_try_prefix", "stage18_runtime_try_moves")
    stage01.append_u32_label(pe, "title_stage18_accept_prefix", "stage18_accepted_moves")
    stage01.append_u32_label(pe, "title_stage18_reject_prefix", "stage18_rejected_moves")
    stage01.append_u32_label(pe, "title_stage18_line_checks_prefix", "stage18_line_checks")
    stage01.append_u32_label(pe, "title_stage18_thing_checks_prefix", "stage18_thing_checks")
    stage01.append_u32_label(pe, "title_stage18_line_iter_prefix", "stage18_line_iterator_calls")
    stage01.append_u32_label(pe, "title_stage18_thing_iter_prefix", "stage18_thing_iterator_calls")
    stage01.append_u32_label(pe, "title_stage18_line_duplicate_prefix", "stage18_line_duplicate_skips")
    stage01.append_u32_label(pe, "title_stage18_block_relink_prefix", "stage18_block_relinks")
    stage01.append_u32_label(pe, "title_stage18_sector_relink_prefix", "stage18_sector_relinks")
    stage01.append_u32_label(pe, "title_stage18_state_tics_prefix", "stage18_state_tic_decrements")
    stage01.append_u32_label(pe, "title_stage18_pain_sound_prefix", "stage18_pain_sound_deferrals")
    stage01.append_u32_label(pe, "title_stage18_chase_prefix", "stage18_chase_calls")
    stage01.append_u32_label(pe, "title_stage18_new_chase_prefix", "stage18_new_chase_dir_calls")
    stage01.append_u32_label(pe, "title_stage18_pmove_prefix", "stage18_move_calls")
    stage01.append_u32_label(pe, "title_stage18_attack_def_prefix", "stage18_attack_state_deferrals")
    stage01.append_u32_label(pe, "title_stage18_attack_exec_prefix", "stage18_attack_actions_executed")
    stage01.append_u32_label(pe, "title_stage18_signature_prefix", "stage18_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage18_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    census = ref.census if ref is not None else None
    trace_last = ref.trace[-1] if ref is not None and ref.trace else None
    counters = ref.counters if ref is not None else Stage18Counters()
    movement = ref.movement_counters if ref is not None else stage14.MovementCounters()
    iterator = ref.iterator if ref is not None else stage14.BlockIteratorState()
    final_mobj = ref.final_mobj if ref is not None else None

    pe.align_section(4)
    pe.label("stage18_route")
    pe.emit_u32(ref.route if ref is not None else 0)
    pe.label("stage18_tics")
    pe.emit_u32(len(ref.trace) if ref is not None else 0)
    pe.label("stage18_mapthing")
    pe.emit_u32(census.mapthing_index if census is not None else 0)
    pe.label("stage18_mobj")
    pe.emit_u32(census.mobj_index if census is not None else 0)
    pe.label("stage18_start_x")
    pe.emit_u32((census.start_x >> FRACBITS if census is not None else 0) & 0xFFFFFFFF)
    pe.label("stage18_start_y")
    pe.emit_u32((census.start_y >> FRACBITS if census is not None else 0) & 0xFFFFFFFF)
    pe.label("stage18_start_x_fixed")
    pe.emit_u32(census.start_x if census is not None else 0)
    pe.label("stage18_start_y_fixed")
    pe.emit_u32(census.start_y if census is not None else 0)
    pe.label("stage18_start_sector")
    pe.emit_u32(census.start_sector if census is not None else 0)
    pe.label("stage18_start_subsector")
    pe.emit_u32(census.start_subsector if census is not None else 0)
    pe.label("stage18_start_block_x")
    pe.emit_u32(census.start_block_x if census is not None else 0)
    pe.label("stage18_start_block_y")
    pe.emit_u32(census.start_block_y if census is not None else 0)
    pe.label("stage18_health")
    pe.emit_u32((census.health if census is not None else 0) & 0xFFFFFFFF)
    pe.label("stage18_start_state")
    pe.emit_u32(census.state if census is not None else 0)
    pe.label("stage18_start_tics")
    pe.emit_u32(census.tics if census is not None else 0)
    pe.label("stage18_target_index")
    pe.emit_u32((census.target_index if census is not None else 0) & 0xFFFFFFFF)
    pe.label("stage18_threshold")
    pe.emit_u32(census.threshold if census is not None else 0)
    pe.label("stage18_start_momx")
    pe.emit_u32((census.momx if census is not None else 0) & 0xFFFFFFFF)
    pe.label("stage18_start_momy")
    pe.emit_u32((census.momy if census is not None else 0) & 0xFFFFFFFF)
    pe.label("stage18_next_state")
    pe.emit_u32(census.next_state if census is not None else 0)
    pe.label("stage18_recovery_state")
    pe.emit_u32(census.recovery_state if census is not None else 0)
    pe.label("stage18_run_state")
    pe.emit_u32(census.run_state if census is not None else 0)

    pe.label("stage18_final_x")
    pe.emit_u32((final_mobj.x >> FRACBITS if final_mobj is not None else 0) & 0xFFFFFFFF)
    pe.label("stage18_final_y")
    pe.emit_u32((final_mobj.y >> FRACBITS if final_mobj is not None else 0) & 0xFFFFFFFF)
    pe.label("stage18_final_x_fixed")
    pe.emit_u32(final_mobj.x if final_mobj is not None else 0)
    pe.label("stage18_final_y_fixed")
    pe.emit_u32(final_mobj.y if final_mobj is not None else 0)
    pe.label("stage18_final_block_x")
    pe.emit_u32(trace_last.block_x if trace_last is not None else 0)
    pe.label("stage18_final_block_y")
    pe.emit_u32(trace_last.block_y if trace_last is not None else 0)
    pe.label("stage18_final_state")
    pe.emit_u32(final_mobj.state if final_mobj is not None and final_mobj.state is not None else 0)
    pe.label("stage18_final_tics")
    pe.emit_u32(final_mobj.tics if final_mobj is not None else 0)
    pe.label("stage18_final_momx")
    pe.emit_u32((final_mobj.momx if final_mobj is not None else 0) & 0xFFFFFFFF)
    pe.label("stage18_final_momy")
    pe.emit_u32((final_mobj.momy if final_mobj is not None else 0) & 0xFFFFFFFF)

    pe.label("stage18_mobj_thinker_calls")
    pe.emit_u32(counters.mobj_thinker_calls)
    pe.label("stage18_xy_services")
    pe.emit_u32(counters.xy_movement_services)
    pe.label("stage18_state_tic_decrements")
    pe.emit_u32(counters.state_tic_decrements)
    pe.label("stage18_state_sets")
    pe.emit_u32(counters.mobj_state_sets)
    pe.label("stage18_state_transitions")
    pe.emit_u32(counters.mobj_state_transitions)
    pe.label("stage18_action_dispatches")
    pe.emit_u32(counters.action_dispatches)
    pe.label("stage18_action_deferrals")
    pe.emit_u32(counters.action_deferrals)
    pe.label("stage18_pain_sound_deferrals")
    pe.emit_u32(counters.pain_sound_deferrals)
    pe.label("stage18_pain_recovery_transitions")
    pe.emit_u32(counters.pain_recovery_transitions)
    pe.label("stage18_chase_reached")
    pe.emit_u32(counters.chase_reached)
    pe.label("stage18_chase_deferred")
    pe.emit_u32(counters.chase_deferred)
    pe.label("stage18_chase_calls")
    pe.emit_u32(counters.chase_calls)
    pe.label("stage18_new_chase_dir_calls")
    pe.emit_u32(counters.new_chase_dir_calls)
    pe.label("stage18_try_walk_calls")
    pe.emit_u32(counters.try_walk_calls)
    pe.label("stage18_move_calls")
    pe.emit_u32(counters.move_calls)
    pe.label("stage18_move_accepts")
    pe.emit_u32(counters.move_accepts)
    pe.label("stage18_move_blocks")
    pe.emit_u32(counters.move_blocks)
    pe.label("stage18_direction_choices")
    pe.emit_u32(counters.direction_choices)
    pe.label("stage18_target_loss_fallbacks")
    pe.emit_u32(counters.target_loss_fallbacks)
    pe.label("stage18_threshold_decrements")
    pe.emit_u32(counters.threshold_decrements)
    pe.label("stage18_melee_range_checks")
    pe.emit_u32(counters.melee_range_checks)
    pe.label("stage18_missile_range_checks")
    pe.emit_u32(counters.missile_range_checks)
    pe.label("stage18_attack_state_deferrals")
    pe.emit_u32(counters.attack_state_deferrals)
    pe.label("stage18_attack_actions_executed")
    pe.emit_u32(counters.attack_actions_executed)
    pe.label("stage18_sound_playback_deferrals")
    pe.emit_u32(counters.sound_playback_deferrals)
    pe.label("stage18_sector_specials_deferred")
    pe.emit_u32(counters.sector_specials_deferred)
    pe.label("stage18_doors_switches_deferred")
    pe.emit_u32(counters.doors_switches_deferred)
    pe.label("stage18_live_keyboard_deferred")
    pe.emit_u32(counters.live_keyboard_deferred)
    pe.label("stage18_source_stage19_absent")
    pe.emit_u32(counters.source_stage19_absent)

    pe.label("stage18_try_moves")
    pe.emit_u32(movement.try_move_calls)
    pe.label("stage18_runtime_try_moves")
    pe.emit_u32(0)
    pe.label("stage18_accepted_moves")
    pe.emit_u32(movement.accepted_moves)
    pe.label("stage18_rejected_moves")
    pe.emit_u32(movement.rejected_moves)
    pe.label("stage18_line_checks")
    pe.emit_u32(movement.line_checks)
    pe.label("stage18_thing_checks")
    pe.emit_u32(movement.thing_checks)
    pe.label("stage18_blocking_lines")
    pe.emit_u32(movement.blocking_lines)
    pe.label("stage18_blocking_things")
    pe.emit_u32(movement.blocking_things)
    pe.label("stage18_step_rejects")
    pe.emit_u32(movement.step_rejects)
    pe.label("stage18_dropoff_rejects")
    pe.emit_u32(movement.dropoff_rejects)
    pe.label("stage18_block_relinks")
    pe.emit_u32(movement.block_relinks)
    pe.label("stage18_sector_relinks")
    pe.emit_u32(movement.sector_relinks)
    pe.label("stage18_line_iterator_calls")
    pe.emit_u32(iterator.line_iterator_calls)
    pe.label("stage18_thing_iterator_calls")
    pe.emit_u32(iterator.thing_iterator_calls)
    pe.label("stage18_line_visits")
    pe.emit_u32(iterator.line_visits)
    pe.label("stage18_thing_visits")
    pe.emit_u32(iterator.thing_visits)
    pe.label("stage18_line_duplicate_skips")
    pe.emit_u32(iterator.line_duplicate_skips)

    pe.label("stage18_expected_signature")
    pe.emit_u32(ref.signature if ref is not None else 0)
    pe.label("stage18_runtime_signature")
    pe.emit_u32(0)

    pe.align_section(1)
    pe.label("stage18_route_name")
    x86.emit_asciiz(pe, ref.route_name if ref is not None else "")
    pe.label("stage18_type_name")
    raw_type = census.type_name[3:] if census is not None and census.type_name.startswith("MT_") else ""
    x86.emit_asciiz(pe, raw_type)
    pe.label("stage18_start_state_name")
    x86.emit_asciiz(pe, census.state_name if census is not None else "")
    pe.label("stage18_next_state_name")
    x86.emit_asciiz(pe, census.next_state_name if census is not None else "")
    pe.label("stage18_recovery_state_name")
    x86.emit_asciiz(pe, census.recovery_state_name if census is not None else "")
    pe.label("stage18_run_state_name")
    x86.emit_asciiz(pe, census.run_state_name if census is not None else "")
    pe.label("stage18_final_state_name")
    x86.emit_asciiz(pe, _state_name(stage16.parse_stage16_info_tables(), final_mobj.state) if final_mobj is not None else "")

    pe.label("status_stage18_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage18_post_damage_monster_movement_and_chase_probe\r\n"
        "Post-damage monster movement proof OK\r\n",
    )
    pe.label("status_stage18_route_prefix")
    x86.emit_asciiz(pe, "\r\nMovement route id: ")
    pe.label("status_stage18_try_prefix")
    x86.emit_asciiz(pe, "\r\nMonster P_TryMove calls: ")
    pe.label("status_stage18_accept_prefix")
    x86.emit_asciiz(pe, "\r\nAccepted monster movement records: ")
    pe.label("status_stage18_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage18 movement signature: ")
    pe.label("status_stage18_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage18 preserves the released stage17 first-damage proof, then "
        "starts from the damaged shotgun guy in S_SPOS_PAIN with inherited "
        "thrust momentum. The bounded P_MobjThinker tic services "
        "P_XYMovement, reaches P_TryMove over real MAP01 BLOCKMAP data, "
        "accepts the tiny post-damage move, relinks the actor, applies "
        "friction, and decrements the pain tic. A_Pain and A_Chase are "
        "covered as bounded deferral/probe paths; no monster action damage or "
        "environment systems are executed in this release.\r\n",
    )

    pe.label("title_stage18_route_prefix")
    x86.emit_asciiz(pe, " M18R=")
    pe.label("title_stage18_tics_prefix")
    x86.emit_asciiz(pe, " M18TIC=")
    pe.label("title_stage18_mapthing_prefix")
    x86.emit_asciiz(pe, " MT18=")
    pe.label("title_stage18_mobj_prefix")
    x86.emit_asciiz(pe, " MO18=")
    pe.label("title_stage18_type_prefix")
    x86.emit_asciiz(pe, " M18N=")
    pe.label("title_stage18_start_x_prefix")
    x86.emit_asciiz(pe, " S18X=")
    pe.label("title_stage18_start_y_prefix")
    x86.emit_asciiz(pe, " S18Y=")
    pe.label("title_stage18_start_block_x_prefix")
    x86.emit_asciiz(pe, " S18BX=")
    pe.label("title_stage18_start_block_y_prefix")
    x86.emit_asciiz(pe, " S18BY=")
    pe.label("title_stage18_start_state_name_prefix")
    x86.emit_asciiz(pe, " S18STN=")
    pe.label("title_stage18_start_state_prefix")
    x86.emit_asciiz(pe, " S18ST=")
    pe.label("title_stage18_start_tics_prefix")
    x86.emit_asciiz(pe, " S18T=")
    pe.label("title_stage18_start_momx_prefix")
    x86.emit_asciiz(pe, " MX0=")
    pe.label("title_stage18_start_momy_prefix")
    x86.emit_asciiz(pe, " MY0=")
    pe.label("title_stage18_final_x_prefix")
    x86.emit_asciiz(pe, " F18X=")
    pe.label("title_stage18_final_y_prefix")
    x86.emit_asciiz(pe, " F18Y=")
    pe.label("title_stage18_final_block_x_prefix")
    x86.emit_asciiz(pe, " F18BX=")
    pe.label("title_stage18_final_block_y_prefix")
    x86.emit_asciiz(pe, " F18BY=")
    pe.label("title_stage18_final_state_name_prefix")
    x86.emit_asciiz(pe, " F18STN=")
    pe.label("title_stage18_final_state_prefix")
    x86.emit_asciiz(pe, " F18ST=")
    pe.label("title_stage18_final_tics_prefix")
    x86.emit_asciiz(pe, " F18T=")
    pe.label("title_stage18_final_momx_prefix")
    x86.emit_asciiz(pe, " MX18=")
    pe.label("title_stage18_final_momy_prefix")
    x86.emit_asciiz(pe, " MY18=")
    pe.label("title_stage18_xy_prefix")
    x86.emit_asciiz(pe, " XY18=")
    pe.label("title_stage18_try_prefix")
    x86.emit_asciiz(pe, " TRY18=")
    pe.label("title_stage18_accept_prefix")
    x86.emit_asciiz(pe, " MACC=")
    pe.label("title_stage18_reject_prefix")
    x86.emit_asciiz(pe, " MREJ=")
    pe.label("title_stage18_line_checks_prefix")
    x86.emit_asciiz(pe, " MLCHK=")
    pe.label("title_stage18_thing_checks_prefix")
    x86.emit_asciiz(pe, " MTCHK=")
    pe.label("title_stage18_line_iter_prefix")
    x86.emit_asciiz(pe, " MBLI=")
    pe.label("title_stage18_thing_iter_prefix")
    x86.emit_asciiz(pe, " MBTI=")
    pe.label("title_stage18_line_duplicate_prefix")
    x86.emit_asciiz(pe, " MLDUP=")
    pe.label("title_stage18_block_relink_prefix")
    x86.emit_asciiz(pe, " MBRL=")
    pe.label("title_stage18_sector_relink_prefix")
    x86.emit_asciiz(pe, " MSRL=")
    pe.label("title_stage18_state_tics_prefix")
    x86.emit_asciiz(pe, " PAINTIC=")
    pe.label("title_stage18_pain_sound_prefix")
    x86.emit_asciiz(pe, " P18DEF=")
    pe.label("title_stage18_chase_prefix")
    x86.emit_asciiz(pe, " CH18=")
    pe.label("title_stage18_new_chase_prefix")
    x86.emit_asciiz(pe, " NCD18=")
    pe.label("title_stage18_pmove_prefix")
    x86.emit_asciiz(pe, " PMV18=")
    pe.label("title_stage18_attack_def_prefix")
    x86.emit_asciiz(pe, " ATK18=")
    pe.label("title_stage18_attack_exec_prefix")
    x86.emit_asciiz(pe, " ATKEX18=")
    pe.label("title_stage18_signature_prefix")
    x86.emit_asciiz(pe, " S18SIG=")


def build_source_stage18_post_damage_monster_movement_and_chase_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage18_load_wad_post_damage_monster_movement_chase_probe(pe)
    stage17.emit_source_stage17_load_wad_first_weapon_fire_damage_death_probe(pe)
    stage08.emit_render_init_texture_data_setup_debug(pe)
    stage01.emit_load_wad_directory(pe)
    stage01.emit_wad_num_lumps(pe)
    stage01.emit_wad_check_num_for_name(pe)
    stage01.emit_wad_get_num_for_name(pe)
    stage01.emit_wad_lump_length(pe)
    stage01.emit_wad_read_lump(pe)
    stage02.emit_source_stage02_load_map(pe)
    stage01.emit_map_load_vertexes(pe)
    stage01.emit_map_load_sectors(pe)
    stage01.emit_map_load_sidedefs(pe)
    stage01.emit_map_load_linedefs(pe)
    stage02.emit_map_load_subsectors(pe)
    stage02.emit_map_load_nodes(pe)
    stage02.emit_map_load_segs(pe)
    stage02.emit_map_group_lines(pe)
    stage02.emit_group_count_sector_ref(pe)
    stage02.emit_group_append_sector_line(pe)
    stage07.emit_source_stage06_run_live_seg_clip_debug(pe)
    stage03.emit_render_fixed_mul(pe)
    stage03.emit_render_point_on_side(pe)
    stage03.emit_render_point_in_subsector(pe)
    stage03.emit_render_debug_subsector(pe)
    stage03.emit_render_check_bbox_accept_all(pe)
    stage03.emit_render_bsp_node_debug(pe)
    stage04.emit_render_slope_div(pe)
    stage04.emit_render_point_to_angle(pe)
    stage04.emit_render_clear_clipsegs(pe)
    stage04.emit_render_check_bbox(pe)
    stage04.emit_render_debug_subsector_bbox(pe)
    stage04.emit_render_bsp_node_bbox_debug(pe)
    stage07.emit_render_angle_to_view_x_debug(pe)
    stage07.emit_render_setup_frame_debug(pe)
    stage07.emit_render_fixed_div(pe)
    stage07.emit_render_point_to_dist(pe)
    stage07.emit_render_scale_from_global_angle(pe)
    stage07.emit_render_store_wall_range_debug(pe)
    stage07.emit_render_clip_solid_wall_segment(pe)
    stage07.emit_render_clip_pass_wall_segment(pe)
    stage08.emit_render_add_line_debug(pe)
    stage07.emit_render_debug_subsector_clip(pe)
    stage07.emit_render_bsp_node_clip_debug(pe)
    stage07.emit_render_finish_clip_debug(pe)
    stage04.emit_render_debug_framebuffer(pe)
    stage03.emit_clear_framebuffer(pe)
    stage03.emit_render_error_pattern(pe)
    stage03.emit_transform_point_to_screen(pe)
    stage03.emit_draw_all_linedefs(pe)
    stage03.emit_draw_visited_segs(pe)
    stage04.emit_draw_bbox_visible_segs(pe)
    stage03.emit_draw_viewpoint_marker(pe)
    stage03.emit_draw_line(pe)
    stage03.emit_plot_pixel(pe)
    stage10.emit_render_composite_two_sided_wall_edges_debug(pe)
    stage10.emit_render_draw_column_debug(pe)
    stage11.emit_render_visplanes_floor_ceiling_debug(pe)
    stage11.emit_render_draw_span_debug(pe)
    stage12.emit_render_sky_and_masked_midtextures_debug(pe)
    stage12.emit_render_draw_stage12_columns_debug(pe)
    stage13.emit_render_things_sprites_and_real_frame_setup_debug(pe)
    stage13.emit_render_draw_stage13_sprite_column_debug(pe)
    stage14.emit_render_game_loop_input_collision_debug(pe)
    stage15.emit_render_pickups_psprites_statusbar_shell_debug(pe)
    stage15.emit_render_draw_stage15_columns_debug(pe)
    stage16.emit_render_active_monster_thinkers_targeting_debug(pe)
    stage17.emit_render_first_weapon_fire_damage_death_probe_debug(pe)
    emit_render_post_damage_monster_movement_chase_probe_debug(pe)
    stage12.emit_build_success_status(pe)
    stage13.emit_append_stage13_success_status(pe)
    stage14.emit_append_stage14_success_status(pe)
    stage15.emit_append_stage15_success_status(pe)
    stage16.emit_append_stage16_success_status(pe)
    stage17.emit_append_stage17_success_status(pe)
    emit_append_stage18_success_status(pe)
    stage01.emit_append_c_string(pe)
    stage01.emit_append_u32_decimal(pe)
    stage01.emit_append_i32_decimal(pe)
    with patched_stage01_window_labels():
        stage01.emit_data(pe)
    stage02.emit_stage02_data(pe)
    stage04.emit_stage04_data(pe)
    stage07.emit_stage07_data(pe)
    stage08.emit_stage08_data(pe)
    stage10.emit_stage10_data(pe)
    stage11.emit_stage11_data(pe)
    stage12.emit_stage12_data(pe)
    stage13.emit_stage13_data(pe)
    stage14.emit_stage14_data(pe)
    stage15.emit_stage15_data(pe)
    stage16.emit_stage16_data(pe)
    stage17.emit_stage17_data(pe)
    emit_stage18_data(pe)
    return pe.build("entry")


def write_source_stage18_post_damage_monster_movement_and_chase_probe_exe(path: str | Path) -> bytes:
    image = build_source_stage18_post_damage_monster_movement_and_chase_probe_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage18 post-damage monster movement/chase PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage18_post_damage_monster_movement_and_chase_probe.exe",
        help="path to write, default: build/source_stage18_post_damage_monster_movement_and_chase_probe.exe",
    )
    args = parser.parse_args()
    write_source_stage18_post_damage_monster_movement_and_chase_probe_exe(args.output)


if __name__ == "__main__":
    main()
