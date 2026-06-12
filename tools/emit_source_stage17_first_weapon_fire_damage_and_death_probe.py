from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Callable, Sequence


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
from tools import x86
from tools.map_loader import LoadedMap, load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


FRAMEBUFFER_WIDTH = stage16.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage16.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage16.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage16.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage16.WINDOW_WIDTH
WINDOW_HEIGHT = stage16.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage17FirstWeaponFireDamageDeathProbe"
WINDOW_TITLE = "Inference Doom S17 First Weapon Fire Damage"
WAD_PATH = stage16.WAD_PATH

FRACBITS = stage16.FRACBITS
FRACUNIT = stage16.FRACUNIT
FNV_PRIME = stage16.FNV_PRIME
ANG90 = stage16.ANG90
ANGLETOFINESHIFT = stage14.ANGLETOFINESHIFT
FINEMASK = stage14.FINEMASK
FINECOSINE = stage14.FINECOSINE
FINESINE = stage14.FINESINE
MISSILERANGE = 32 * 64 * FRACUNIT
BULLET_AIM_RANGE = 16 * 64 * FRACUNIT
SCREENWIDTH = 320
SCREENHEIGHT = 200
BASETHRESHOLD = 100

PT_ADDLINES = 1
PT_ADDTHINGS = 2
PT_EARLYOUT = 4
BT_ATTACK = 1

DEFAULT_ATTACK_TARGET_MAPTHING_INDEX = stage16.DEFAULT_ACTIVE_MONSTER_MAPTHING_INDEX
SELECTED_WEAPON_NAME = "A_FireShotgun"

SOURCE_TRACE = stage16.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_pspr.c",
        "P_CheckAmmo/A_WeaponReady/P_FireWeapon/A_FireShotgun",
        "P_PlayerShotgunFire_first_damage_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_pspr.c",
        "P_BulletSlope/P_GunShot",
        "P_BulletSlope_GunShot_first_damage_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "P_AimLineAttack/P_LineAttack/PTR_AimTraverse/PTR_ShootTraverse",
        "P_AimLineAttack_LineAttack_bounded_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_maputl.c",
        "P_PathTraverse/PIT_AddLineIntercepts/PIT_AddThingIntercepts/P_TraverseIntercepts",
        "P_PathTraverse_hitscan_bounded_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_inter.c",
        "P_DamageMobj/P_KillMobj reached subset",
        "P_DamageMobj_KillMobj_first_damage_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_SetMobjState/P_SpawnBlood bounded reached subset",
        "P_SetMobjState_SpawnBlood_first_damage_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/m_random.c",
        "P_Random/P_SubRandom for shotgun damage and spread",
        "P_Random_weapon_damage_source_shape_debug",
    ),
)


@dataclass
class Stage17Counters:
    attack_census_runs: int = 0
    attack_angle_freezes: int = 0
    current_angle_aims: int = 0
    current_angle_misses: int = 0
    no_live_input_dependency: int = 1
    ammo_checks: int = 0
    ammo_failures: int = 0
    weapon_ready_calls: int = 0
    fire_weapon_calls: int = 0
    selected_fire_actions: int = 0
    unsupported_weapon_deferrals: int = 0
    psprite_set_calls: int = 0
    psprite_move_calls: int = 0
    psprite_state_changes: int = 0
    flash_setups: int = 0
    light_deferred: int = 0
    ammo_decrements: int = 0
    shell_spent: int = 0
    player_attack_state_sets: int = 0
    sound_deferred: int = 0
    noise_alert_deferred: int = 0
    bullet_slope_calls: int = 0
    gunshots: int = 0
    aim_line_attacks: int = 0
    aim_hits: int = 0
    aim_misses: int = 0
    aim_fallbacks: int = 0
    line_attacks: int = 0
    path_traverses: int = 0
    block_steps: int = 0
    block_line_iters: int = 0
    block_thing_iters: int = 0
    line_intercepts: int = 0
    thing_intercepts: int = 0
    traversed_intercepts: int = 0
    solid_line_blocks: int = 0
    shootable_thing_intercepts: int = 0
    line_hits: int = 0
    line_misses: int = 0
    blood_spawns_deferred: int = 0
    puff_spawns_deferred: int = 0
    damage_events: int = 0
    damage_total: int = 0
    thrust_applications: int = 0
    pain_events: int = 0
    kill_events: int = 0
    death_state_sets: int = 0
    removal_deferred: int = 0
    drop_deferred: int = 0
    mobj_state_sets: int = 0
    mobj_state_transitions: int = 0
    generalized_combat_deferred: int = 0
    monster_chase_moves: int = 0
    doors_switches_deferred: int = 0
    sector_specials_deferred: int = 0
    live_keyboard_deferred: int = 0


@dataclass(frozen=True)
class AttackCensusRecord:
    attacker_mobj_index: int
    target_mapthing_index: int
    target_mobj_index: int
    current_angle: int
    current_angle_degrees: int
    player_to_target_angle: int
    player_to_target_degrees: int
    target_to_player_angle: int
    target_to_player_degrees: int
    angle_delta_degrees: int
    current_angle_hits_selected: int
    selected_angle_hits_selected: int
    selected_angle_slope: int
    selected_angle_blocked_by_line: int
    sight_visible: int
    readyweapon: int
    readyweapon_name: str
    shell_before: int
    target_health_before: int
    selected_action: str
    candidate_actions: tuple[str, ...]


@dataclass(frozen=True)
class PathIntercept:
    frac: int
    isaline: bool
    index: int
    order: int


@dataclass(frozen=True)
class PathTraverseResult:
    intercepts: tuple[PathIntercept, ...]
    blocks: tuple[tuple[int, int], ...]
    completed: bool


@dataclass(frozen=True)
class AimLineAttackResult:
    slope: int
    target_index: int | None
    hit_selected: int
    blocked_by_line: int
    path: PathTraverseResult


@dataclass(frozen=True)
class LineAttackShotResult:
    shot_index: int
    angle: int
    damage: int
    hit_mobj_index: int | None
    selected_hit: int
    target_health_after: int
    target_state_after: int | None
    killed: int
    blocked_by_line: int


@dataclass(frozen=True)
class Stage17FirstWeaponFireReference:
    stage16: stage16.Stage16ActiveMonsterReference
    census: AttackCensusRecord
    shots: tuple[LineAttackShotResult, ...]
    counters: Stage17Counters
    final_target: stage16.ActiveMobj
    player: stage15.Stage15Player
    draw: stage15.PatchDrawResult
    attack_angle: int
    attack_angle_degrees: int
    bullet_slope: int
    random_start_index: int
    random_end_index: int
    shell_before: int
    shell_after: int
    health_before: int
    health_after: int
    weapon_state: int
    weapon_state_name: str
    weapon_tics: int
    flash_state: int
    flash_state_name: str
    flash_tics: int
    signature: int


@dataclass
class Stage17AttackWorld:
    movement: stage14.MovementWorld
    info: stage16.Stage16InfoTables
    player: stage15.Stage15Player
    weaponinfo: tuple[stage15.WeaponInfo, ...]
    mobjs: dict[int, stage16.ActiveMobj]
    counters: Stage17Counters
    rng: stage16.DoomRandom
    selected_index: int
    linetarget_index: int | None = None
    last_bullet_slope: int = 0


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


def _fine_index(angle: int) -> int:
    return (_u32(angle) >> ANGLETOFINESHIFT) & FINEMASK


def _state_name(info: stage16.Stage16InfoTables, state: int | None) -> str:
    return stage16._state_name(info, state)


def _psprite_state_name(info: stage15.Stage15InfoTables, state: int | None) -> str:
    return stage15._state_name(info, state)


def _weapon_name(weapon: int) -> str:
    names = {
        stage15.WP_FIST: "FIST",
        stage15.WP_PISTOL: "PISTOL",
        stage15.WP_SHOTGUN: "SHOTGUN",
        stage15.WP_CHAINGUN: "CHAINGUN",
        stage15.WP_MISSILE: "MISSILE",
        stage15.WP_PLASMA: "PLASMA",
        stage15.WP_BFG: "BFG",
        stage15.WP_CHAINSAW: "CHAINSAW",
        stage15.WP_SUPERSHOTGUN: "SSG",
    }
    return names.get(weapon, f"W{weapon}")


def _copy_attack_mobj(
    mobj: stage14.MovementMobj,
    info: stage16.Stage16InfoTables,
    player: stage15.Stage15Player,
) -> stage16.ActiveMobj:
    if mobj.player_index >= 0:
        state = info.state_info.state_index["S_PLAY"]
        health = player.health
        type_name = "MT_PLAYER"
        doomednum = 1
        reactiontime = 0
    else:
        minfo = info.by_name.get(mobj.type_name)
        if minfo is not None:
            state = minfo.spawnstate
            health = minfo.spawnhealth
            doomednum = minfo.doomednum
            reactiontime = minfo.reactiontime
            type_name = mobj.type_name
        else:
            state = None
            health = 1000
            doomednum = mobj.doomednum
            reactiontime = 0
            type_name = mobj.type_name
    st = info.state_info.states[state] if state is not None else None
    return stage16.ActiveMobj(
        index=mobj.index,
        mapthing_index=mobj.mapthing_index,
        type_name=type_name,
        doomednum=doomednum,
        x=mobj.x,
        y=mobj.y,
        z=mobj.z,
        angle=mobj.angle,
        momx=mobj.momx,
        momy=mobj.momy,
        momz=mobj.momz,
        radius=mobj.radius,
        height=mobj.height,
        flags=mobj.flags,
        floorz=mobj.floorz,
        ceilingz=mobj.ceilingz,
        subsector=mobj.subsector,
        sector=mobj.sector,
        health=health,
        reactiontime=reactiontime,
        state=state,
        tics=st.tics if st is not None else -1,
        sprite=st.sprite if st is not None else 0,
        frame=st.frame if st is not None else 0,
        lastlook=0,
    )


def _random_after_stage16_spawn_sequence(
    stage15_world: stage15.Stage15World,
    info: stage16.Stage16InfoTables,
) -> tuple[stage16.DoomRandom, int]:
    rng = stage16.DoomRandom()
    calls = 0
    for mobj in stage15_world.movement.mobjs:
        rng.p_random()
        calls += 1
        minfo = info.by_name.get(mobj.type_name)
        if minfo is None or minfo.spawnstate >= len(info.state_info.states):
            continue
        raw_tics = info.state_info.states[minfo.spawnstate].tics
        if mobj.player_index < 0 and raw_tics > 0:
            rng.p_random()
            calls += 1
    return rng, calls


def build_stage17_attack_world(
    stage15_world: stage15.Stage15World,
    ref16: stage16.Stage16ActiveMonsterReference,
    info: stage16.Stage16InfoTables,
) -> Stage17AttackWorld:
    rng, _calls = _random_after_stage16_spawn_sequence(stage15_world, info)
    mobjs = {
        mobj.index: _copy_attack_mobj(mobj, info, stage15_world.player)
        for mobj in stage15_world.movement.mobjs
    }
    mobjs[ref16.final_mobj.index] = replace(ref16.final_mobj)
    return Stage17AttackWorld(
        movement=stage15_world.movement,
        info=info,
        player=stage15_world.player,
        weaponinfo=stage15_world.weaponinfo,
        mobjs=mobjs,
        counters=Stage17Counters(),
        rng=rng,
        selected_index=ref16.final_mobj.index,
    )


def p_intercept_vector_source_shape(
    trace: Sequence[int],
    divline: Sequence[int],
) -> int:
    return stage16.p_intercept_vector2_source_shape(trace, divline)


def _line_divline(line: stage14.MovementLine) -> tuple[int, int, int, int]:
    return (line.v1x, line.v1y, line.dx, line.dy)


def _add_line_intercept_source_shape(
    attack_world: Stage17AttackWorld,
    trace: Sequence[int],
    line: stage14.MovementLine,
    intercepts: list[PathIntercept],
    order: int,
    *,
    earlyout: bool = False,
) -> tuple[bool, int]:
    if (
        trace[2] > FRACUNIT * 16
        or trace[3] > FRACUNIT * 16
        or trace[2] < -FRACUNIT * 16
        or trace[3] < -FRACUNIT * 16
    ):
        s1 = stage16.p_divline_side_source_shape(line.v1x, line.v1y, trace)
        s2 = stage16.p_divline_side_source_shape(line.v1x + line.dx, line.v1y + line.dy, trace)
    else:
        s1 = stage14.point_on_line_side_source_shape(trace[0], trace[1], line)
        s2 = stage14.point_on_line_side_source_shape(_i32(trace[0] + trace[2]), _i32(trace[1] + trace[3]), line)
    if s1 == s2:
        return True, order

    frac = p_intercept_vector_source_shape(trace, _line_divline(line))
    if frac < 0:
        return True, order
    if earlyout and frac < FRACUNIT and line.backsector is None:
        return False, order

    intercepts.append(PathIntercept(frac=frac, isaline=True, index=line.index, order=order))
    attack_world.counters.line_intercepts += 1
    return True, order + 1


def _add_thing_intercept_source_shape(
    attack_world: Stage17AttackWorld,
    trace: Sequence[int],
    thing_index: int,
    intercepts: list[PathIntercept],
    order: int,
) -> int:
    thing = attack_world.mobjs.get(thing_index)
    if thing is None:
        return order
    tracepositive = _i32(trace[2] ^ trace[3]) > 0
    if tracepositive:
        x1 = thing.x - thing.radius
        y1 = thing.y + thing.radius
        x2 = thing.x + thing.radius
        y2 = thing.y - thing.radius
    else:
        x1 = thing.x - thing.radius
        y1 = thing.y - thing.radius
        x2 = thing.x + thing.radius
        y2 = thing.y + thing.radius

    s1 = stage16.p_divline_side_source_shape(x1, y1, trace)
    s2 = stage16.p_divline_side_source_shape(x2, y2, trace)
    if s1 == s2:
        return order

    divline = (x1, y1, _i32(x2 - x1), _i32(y2 - y1))
    frac = p_intercept_vector_source_shape(trace, divline)
    if frac < 0:
        return order

    intercepts.append(PathIntercept(frac=frac, isaline=False, index=thing.index, order=order))
    attack_world.counters.thing_intercepts += 1
    return order + 1


def p_path_traverse_source_shape(
    attack_world: Stage17AttackWorld,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    flags: int,
    *,
    max_blocks: int = 64,
    max_intercepts: int = stage16.MAXPLAYERS * 64,
) -> PathTraverseResult:
    attack_world.counters.path_traverses += 1
    earlyout = bool(flags & PT_EARLYOUT)
    if ((x1 - attack_world.movement.blockmap.origin_x) & (stage14.MAPBLOCKSIZE - 1)) == 0:
        x1 += FRACUNIT
    if ((y1 - attack_world.movement.blockmap.origin_y) & (stage14.MAPBLOCKSIZE - 1)) == 0:
        y1 += FRACUNIT

    trace = (x1, y1, _i32(x2 - x1), _i32(y2 - y1))
    local_x1 = _i32(x1 - attack_world.movement.blockmap.origin_x)
    local_y1 = _i32(y1 - attack_world.movement.blockmap.origin_y)
    local_x2 = _i32(x2 - attack_world.movement.blockmap.origin_x)
    local_y2 = _i32(y2 - attack_world.movement.blockmap.origin_y)
    xt1 = local_x1 >> stage14.MAPBLOCKSHIFT
    yt1 = local_y1 >> stage14.MAPBLOCKSHIFT
    xt2 = local_x2 >> stage14.MAPBLOCKSHIFT
    yt2 = local_y2 >> stage14.MAPBLOCKSHIFT

    if xt2 > xt1:
        mapxstep = 1
        partial = FRACUNIT - ((local_x1 >> (stage14.MAPBLOCKSHIFT - FRACBITS)) & (FRACUNIT - 1))
        ystep = stage04.fixed_div(_i32(local_y2 - local_y1), abs(_i32(local_x2 - local_x1)))
    elif xt2 < xt1:
        mapxstep = -1
        partial = (local_x1 >> (stage14.MAPBLOCKSHIFT - FRACBITS)) & (FRACUNIT - 1)
        ystep = stage04.fixed_div(_i32(local_y2 - local_y1), abs(_i32(local_x2 - local_x1)))
    else:
        mapxstep = 0
        partial = FRACUNIT
        ystep = 256 * FRACUNIT
    yintercept = (local_y1 >> (stage14.MAPBLOCKSHIFT - FRACBITS)) + stage04.fixed_mul(partial, ystep)

    if yt2 > yt1:
        mapystep = 1
        partial = FRACUNIT - ((local_y1 >> (stage14.MAPBLOCKSHIFT - FRACBITS)) & (FRACUNIT - 1))
        xstep = stage04.fixed_div(_i32(local_x2 - local_x1), abs(_i32(local_y2 - local_y1)))
    elif yt2 < yt1:
        mapystep = -1
        partial = (local_y1 >> (stage14.MAPBLOCKSHIFT - FRACBITS)) & (FRACUNIT - 1)
        xstep = stage04.fixed_div(_i32(local_x2 - local_x1), abs(_i32(local_y2 - local_y1)))
    else:
        mapystep = 0
        partial = FRACUNIT
        xstep = 256 * FRACUNIT
    xintercept = (local_x1 >> (stage14.MAPBLOCKSHIFT - FRACBITS)) + stage04.fixed_mul(partial, xstep)

    mapx = xt1
    mapy = yt1
    intercepts: list[PathIntercept] = []
    blocks: list[tuple[int, int]] = []
    checked_lines: set[int] = set()
    order = 0
    completed = True

    for _count in range(max_blocks):
        blocks.append((mapx, mapy))
        attack_world.counters.block_steps += 1
        if flags & PT_ADDLINES:
            attack_world.counters.block_line_iters += 1
            if 0 <= mapx < attack_world.movement.blockmap.width and 0 <= mapy < attack_world.movement.blockmap.height:
                for line_index in attack_world.movement.blockmap.lists[stage14._block_index(attack_world.movement.blockmap, mapx, mapy)]:
                    if line_index in checked_lines or line_index >= len(attack_world.movement.lines):
                        continue
                    checked_lines.add(line_index)
                    keep_going, order = _add_line_intercept_source_shape(
                        attack_world,
                        trace,
                        attack_world.movement.lines[line_index],
                        intercepts,
                        order,
                        earlyout=earlyout,
                    )
                    if not keep_going:
                        completed = False
                        return PathTraverseResult(tuple(intercepts), tuple(blocks), completed)
                    if len(intercepts) >= max_intercepts:
                        completed = False
                        return PathTraverseResult(tuple(intercepts), tuple(blocks), completed)
        if flags & PT_ADDTHINGS:
            attack_world.counters.block_thing_iters += 1
            if 0 <= mapx < attack_world.movement.blockmap.width and 0 <= mapy < attack_world.movement.blockmap.height:
                thing_index = attack_world.movement.blocklinks[stage14._block_index(attack_world.movement.blockmap, mapx, mapy)]
                visits = 0
                while thing_index is not None and visits < 128:
                    order = _add_thing_intercept_source_shape(
                        attack_world,
                        trace,
                        thing_index,
                        intercepts,
                        order,
                    )
                    if len(intercepts) >= max_intercepts:
                        completed = False
                        return PathTraverseResult(tuple(intercepts), tuple(blocks), completed)
                    next_index = attack_world.movement.mobjs[thing_index].bnext
                    thing_index = next_index
                    visits += 1

        if mapx == xt2 and mapy == yt2:
            break
        if (yintercept >> FRACBITS) == mapy:
            yintercept = _i32(yintercept + ystep)
            mapx += mapxstep
        elif (xintercept >> FRACBITS) == mapx:
            xintercept = _i32(xintercept + xstep)
            mapy += mapystep
        else:
            completed = False
            break

    return PathTraverseResult(tuple(intercepts), tuple(blocks), completed)


def _traverse_intercepts_source_shape(
    attack_world: Stage17AttackWorld,
    path: PathTraverseResult,
    func: Callable[[PathIntercept], bool],
    maxfrac: int = FRACUNIT,
) -> bool:
    remaining = list(path.intercepts)
    while remaining:
        intercept = min(remaining, key=lambda item: (item.frac, item.order))
        remaining.remove(intercept)
        if intercept.frac > maxfrac:
            return True
        attack_world.counters.traversed_intercepts += 1
        if not func(intercept):
            return False
    return True


def p_aim_line_attack_source_shape(
    attack_world: Stage17AttackWorld,
    shooter: stage16.ActiveMobj,
    angle: int,
    distance: int,
) -> AimLineAttackResult:
    attack_world.counters.aim_line_attacks += 1
    fine = _fine_index(angle)
    x2 = _i32(shooter.x + (distance >> FRACBITS) * FINECOSINE[fine])
    y2 = _i32(shooter.y + (distance >> FRACBITS) * FINESINE[fine])
    shootz = shooter.z + (shooter.height >> 1) + 8 * FRACUNIT
    topslope = (SCREENHEIGHT // 2) * FRACUNIT // (SCREENWIDTH // 2)
    bottomslope = -topslope
    attackrange = distance
    linetarget: int | None = None
    aimslope = 0
    blocked_by_line = 0
    path = p_path_traverse_source_shape(attack_world, shooter.x, shooter.y, x2, y2, PT_ADDLINES | PT_ADDTHINGS)

    def ptr_aim(intercept: PathIntercept) -> bool:
        nonlocal topslope, bottomslope, linetarget, aimslope, blocked_by_line
        if intercept.isaline:
            line = attack_world.movement.lines[intercept.index]
            if line.backsector is None or not (line.flags & stage14.ML_TWOSIDED):
                blocked_by_line = 1
                attack_world.counters.solid_line_blocks += 1
                return False
            opentop, openbottom, _openrange, _lowfloor = stage14.p_line_opening_source_shape(attack_world.movement, line)
            if openbottom >= opentop:
                blocked_by_line = 1
                attack_world.counters.solid_line_blocks += 1
                return False
            dist = stage04.fixed_mul(attackrange, intercept.frac)
            front = attack_world.movement.sectors[line.frontsector]
            back = attack_world.movement.sectors[line.backsector]
            if front.floorheight != back.floorheight:
                slope = stage04.fixed_div(_i32(openbottom - shootz), dist)
                if slope > bottomslope:
                    bottomslope = slope
            if front.ceilingheight != back.ceilingheight:
                slope = stage04.fixed_div(_i32(opentop - shootz), dist)
                if slope < topslope:
                    topslope = slope
            if topslope <= bottomslope:
                blocked_by_line = 1
                attack_world.counters.solid_line_blocks += 1
                return False
            return True

        thing = attack_world.mobjs.get(intercept.index)
        if thing is None or thing.index == shooter.index:
            return True
        if not (thing.flags & stage13.MF_SHOOTABLE):
            return True
        dist = stage04.fixed_mul(attackrange, intercept.frac)
        if dist == 0:
            return True
        thingtopslope = stage04.fixed_div(_i32(thing.z + thing.height - shootz), dist)
        if thingtopslope < bottomslope:
            return True
        thingbottomslope = stage04.fixed_div(_i32(thing.z - shootz), dist)
        if thingbottomslope > topslope:
            return True
        if thingtopslope > topslope:
            thingtopslope = topslope
        if thingbottomslope < bottomslope:
            thingbottomslope = bottomslope
        aimslope = _i32((thingtopslope + thingbottomslope) // 2)
        linetarget = thing.index
        attack_world.counters.shootable_thing_intercepts += 1
        return False

    _traverse_intercepts_source_shape(attack_world, path, ptr_aim)
    attack_world.linetarget_index = linetarget
    if linetarget is None:
        attack_world.counters.aim_misses += 1
    else:
        attack_world.counters.aim_hits += 1
    return AimLineAttackResult(
        slope=aimslope if linetarget is not None else 0,
        target_index=linetarget,
        hit_selected=1 if linetarget == attack_world.selected_index else 0,
        blocked_by_line=blocked_by_line,
        path=path,
    )


def _set_mobj_state_stage17(
    attack_world: Stage17AttackWorld,
    mobj: stage16.ActiveMobj,
    state: int,
) -> bool:
    if state == stage16.S_NULL:
        mobj.state = None
        mobj.tics = 0
        mobj.removed = True
        attack_world.counters.removal_deferred += 1
        return False
    st = attack_world.info.state_info.states[state]
    previous = mobj.state
    mobj.state = state
    mobj.tics = st.tics
    mobj.sprite = st.sprite
    mobj.frame = st.frame
    attack_world.counters.mobj_state_sets += 1
    if previous != state:
        attack_world.counters.mobj_state_transitions += 1
    return True


def _spawn_blood_deferred_source_shape(
    attack_world: Stage17AttackWorld,
    damage: int,
) -> None:
    attack_world.rng.p_random()
    attack_world.rng.p_random()
    attack_world.rng.p_random()
    attack_world.counters.blood_spawns_deferred += 1
    if damage <= 12 and damage >= 9:
        attack_world.counters.mobj_state_sets += 1
    elif damage < 9:
        attack_world.counters.mobj_state_sets += 1


def _spawn_puff_deferred_source_shape(attack_world: Stage17AttackWorld) -> None:
    attack_world.rng.p_random()
    attack_world.rng.p_random()
    attack_world.rng.p_random()
    attack_world.counters.puff_spawns_deferred += 1


def p_kill_mobj_source_shape(
    attack_world: Stage17AttackWorld,
    source: stage16.ActiveMobj | None,
    target: stage16.ActiveMobj,
) -> None:
    target.flags &= ~(stage13.MF_SHOOTABLE | stage13.MF_FLOAT | stage13.MF_SKULLFLY)
    if target.type_name != "MT_SKULL":
        target.flags &= ~stage13.MF_NOGRAVITY
    target.flags |= stage13.MF_CORPSE | stage13.MF_DROPOFF
    target.height >>= 2
    minfo = attack_world.info.by_name[target.type_name]
    if source is not None and source.type_name == "MT_PLAYER" and (target.flags & stage13.MF_COUNTKILL):
        attack_world.player.killcount += 1
    deathstate = minfo.xdeathstate if target.health < -minfo.spawnhealth and minfo.xdeathstate else minfo.deathstate
    _set_mobj_state_stage17(attack_world, target, deathstate)
    attack_world.counters.death_state_sets += 1
    target.tics -= attack_world.rng.p_random() & 3
    if target.tics < 1:
        target.tics = 1
    attack_world.counters.kill_events += 1
    if target.type_name in {"MT_WOLFSS", "MT_POSSESSED", "MT_SHOTGUY", "MT_CHAINGUY"}:
        attack_world.counters.drop_deferred += 1


def p_damage_mobj_source_shape(
    attack_world: Stage17AttackWorld,
    target: stage16.ActiveMobj,
    inflictor: stage16.ActiveMobj | None,
    source: stage16.ActiveMobj | None,
    damage: int,
) -> None:
    if not (target.flags & stage13.MF_SHOOTABLE):
        return
    if target.health <= 0:
        return
    if target.flags & stage13.MF_SKULLFLY:
        target.momx = target.momy = target.momz = 0

    minfo = attack_world.info.by_name[target.type_name]
    if inflictor is not None and not (target.flags & stage13.MF_NOCLIP):
        if source is None or source.type_name != "MT_PLAYER" or attack_world.player.readyweapon != stage15.WP_CHAINSAW:
            ang = stage04.point_to_angle(target.x, target.y, inflictor.x, inflictor.y)
            thrust = damage * (FRACUNIT >> 3) * 100 // max(1, minfo.mass)
            fine = _fine_index(ang)
            target.momx = _i32(target.momx + stage04.fixed_mul(thrust, FINECOSINE[fine]))
            target.momy = _i32(target.momy + stage04.fixed_mul(thrust, FINESINE[fine]))
            attack_world.counters.thrust_applications += 1

    target.health -= damage
    attack_world.counters.damage_events += 1
    attack_world.counters.damage_total += damage
    if target.health <= 0:
        p_kill_mobj_source_shape(attack_world, source, target)
        return

    if (attack_world.rng.p_random() < minfo.painchance) and not (target.flags & stage13.MF_SKULLFLY):
        target.flags |= stage13.MF_JUSTHIT
        _set_mobj_state_stage17(attack_world, target, minfo.painstate)
        attack_world.counters.pain_events += 1
    target.reactiontime = 0
    if source is not None and (not target.threshold or target.type_name == "MT_VILE") and source != target and source.type_name != "MT_VILE":
        target.target_index = source.index
        target.threshold = BASETHRESHOLD
        if target.state == minfo.spawnstate and minfo.seestate != stage16.S_NULL:
            _set_mobj_state_stage17(attack_world, target, minfo.seestate)


def p_line_attack_source_shape(
    attack_world: Stage17AttackWorld,
    shooter: stage16.ActiveMobj,
    angle: int,
    distance: int,
    slope: int,
    damage: int,
    *,
    shot_index: int,
) -> LineAttackShotResult:
    attack_world.counters.line_attacks += 1
    fine = _fine_index(angle)
    x2 = _i32(shooter.x + (distance >> FRACBITS) * FINECOSINE[fine])
    y2 = _i32(shooter.y + (distance >> FRACBITS) * FINESINE[fine])
    shootz = shooter.z + (shooter.height >> 1) + 8 * FRACUNIT
    attackrange = distance
    aimslope = slope
    hit_mobj_index: int | None = None
    blocked_by_line = 0
    killed = 0
    path = p_path_traverse_source_shape(attack_world, shooter.x, shooter.y, x2, y2, PT_ADDLINES | PT_ADDTHINGS)

    def ptr_shoot(intercept: PathIntercept) -> bool:
        nonlocal hit_mobj_index, blocked_by_line, killed
        if intercept.isaline:
            line = attack_world.movement.lines[intercept.index]
            hitline = False
            if line.special:
                attack_world.counters.sector_specials_deferred += 1
            if line.backsector is None or not (line.flags & stage14.ML_TWOSIDED):
                hitline = True
            else:
                opentop, openbottom, _openrange, _lowfloor = stage14.p_line_opening_source_shape(attack_world.movement, line)
                dist = stage04.fixed_mul(attackrange, intercept.frac)
                front = attack_world.movement.sectors[line.frontsector]
                back = attack_world.movement.sectors[line.backsector]
                if front.floorheight != back.floorheight:
                    line_slope = stage04.fixed_div(_i32(openbottom - shootz), dist)
                    if line_slope > aimslope:
                        hitline = True
                if front.ceilingheight != back.ceilingheight:
                    line_slope = stage04.fixed_div(_i32(opentop - shootz), dist)
                    if line_slope < aimslope:
                        hitline = True
            if hitline:
                blocked_by_line = 1
                attack_world.counters.solid_line_blocks += 1
                _spawn_puff_deferred_source_shape(attack_world)
                return False
            return True

        thing = attack_world.mobjs.get(intercept.index)
        if thing is None or thing.index == shooter.index:
            return True
        if not (thing.flags & stage13.MF_SHOOTABLE):
            return True
        dist = stage04.fixed_mul(attackrange, intercept.frac)
        if dist == 0:
            return True
        thingtopslope = stage04.fixed_div(_i32(thing.z + thing.height - shootz), dist)
        if thingtopslope < aimslope:
            return True
        thingbottomslope = stage04.fixed_div(_i32(thing.z - shootz), dist)
        if thingbottomslope > aimslope:
            return True

        hit_mobj_index = thing.index
        attack_world.counters.shootable_thing_intercepts += 1
        if thing.flags & stage13.MF_NOBLOOD:
            _spawn_puff_deferred_source_shape(attack_world)
        else:
            _spawn_blood_deferred_source_shape(attack_world, damage)
        before = thing.health
        if damage:
            p_damage_mobj_source_shape(attack_world, thing, shooter, shooter, damage)
        killed = 1 if before > 0 and thing.health <= 0 else 0
        return False

    _traverse_intercepts_source_shape(attack_world, path, ptr_shoot)
    target = attack_world.mobjs[attack_world.selected_index]
    if hit_mobj_index is None:
        attack_world.counters.line_misses += 1
    else:
        attack_world.counters.line_hits += 1
    return LineAttackShotResult(
        shot_index=shot_index,
        angle=angle,
        damage=damage,
        hit_mobj_index=hit_mobj_index,
        selected_hit=1 if hit_mobj_index == attack_world.selected_index else 0,
        target_health_after=target.health,
        target_state_after=target.state,
        killed=killed,
        blocked_by_line=blocked_by_line,
    )


def p_bullet_slope_source_shape(
    attack_world: Stage17AttackWorld,
    shooter: stage16.ActiveMobj,
) -> int:
    attack_world.counters.bullet_slope_calls += 1
    angle = shooter.angle
    aim = p_aim_line_attack_source_shape(attack_world, shooter, angle, BULLET_AIM_RANGE)
    if aim.target_index is None:
        attack_world.counters.aim_fallbacks += 1
        aim = p_aim_line_attack_source_shape(attack_world, shooter, _u32(angle + (1 << 26)), BULLET_AIM_RANGE)
        if aim.target_index is None:
            attack_world.counters.aim_fallbacks += 1
            aim = p_aim_line_attack_source_shape(attack_world, shooter, _u32(angle - (1 << 26)), BULLET_AIM_RANGE)
    return aim.slope


def p_gunshot_source_shape(
    attack_world: Stage17AttackWorld,
    shooter: stage16.ActiveMobj,
    accurate: bool,
    bulletslope: int,
    shot_index: int,
) -> LineAttackShotResult:
    attack_world.counters.gunshots += 1
    damage = 5 * (attack_world.rng.p_random() % 3 + 1)
    angle = shooter.angle
    if not accurate:
        angle = _u32(angle + ((attack_world.rng.p_random() - attack_world.rng.p_random()) << 18))
    return p_line_attack_source_shape(
        attack_world,
        shooter,
        angle,
        MISSILERANGE,
        bulletslope,
        damage,
        shot_index=shot_index,
    )


def _decrease_ammo_source_shape(
    player: stage15.Stage15Player,
    ammo: int,
    amount: int,
    counters: Stage17Counters,
) -> None:
    assert player.ammo is not None
    assert player.maxammo is not None
    if ammo < stage15.NUMAMMO:
        before = player.ammo[ammo]
        player.ammo[ammo] -= amount
        counters.ammo_decrements += 1
        if ammo == stage15.AM_SHELL:
            counters.shell_spent += before - player.ammo[ammo]
    else:
        player.maxammo[ammo - stage15.NUMAMMO] -= amount
        counters.ammo_decrements += 1


def p_set_psprite_stage17_source_shape(
    attack_world: Stage17AttackWorld,
    position: int,
    stnum: int,
    shooter: stage16.ActiveMobj,
    *,
    max_steps: int = 64,
) -> tuple[LineAttackShotResult, ...]:
    attack_world.counters.psprite_set_calls += 1
    psp = attack_world.player.psprites[position]
    shots: list[LineAttackShotResult] = []
    steps = 0
    while True:
        steps += 1
        if steps > max_steps:
            raise RuntimeError("stage17 P_SetPsprite exceeded bounded state steps")
        if stnum == attack_world.info.state_info.state_index["S_NULL"]:
            psp.state = None
            psp.tics = 0
            attack_world.counters.psprite_state_changes += 1
            return tuple(shots)
        state = attack_world.info.state_info.states[stnum]
        psp.state = stnum
        psp.tics = state.tics
        if state.misc1:
            psp.sx = state.misc1 << FRACBITS
            psp.sy = state.misc2 << FRACBITS
        attack_world.counters.psprite_state_changes += 1

        if state.action == "A_FireShotgun":
            shots.extend(a_fire_shotgun_source_shape(attack_world, shooter, psp))
        elif state.action == "A_Light1":
            attack_world.counters.light_deferred += 1
        elif state.action == "A_Light2":
            attack_world.counters.light_deferred += 1
        elif state.action in {"A_FirePistol", "A_FireCGun", "A_FireShotgun2", "A_FireMissile", "A_FirePlasma", "A_FireBFG"}:
            attack_world.counters.unsupported_weapon_deferrals += 1
        elif state.action:
            attack_world.counters.unsupported_weapon_deferrals += 1

        if psp.state is None or psp.tics:
            return tuple(shots)
        stnum = attack_world.info.state_info.states[psp.state].nextstate


def p_move_psprites_stage17_source_shape(
    attack_world: Stage17AttackWorld,
    shooter: stage16.ActiveMobj,
) -> tuple[LineAttackShotResult, ...]:
    attack_world.counters.psprite_move_calls += 1
    shots: list[LineAttackShotResult] = []
    assert attack_world.player.psprites is not None
    for position, psp in enumerate(attack_world.player.psprites):
        if psp.state is None:
            continue
        if psp.tics != -1:
            psp.tics -= 1
            if not psp.tics and psp.state is not None:
                shots.extend(
                    p_set_psprite_stage17_source_shape(
                        attack_world,
                        position,
                        attack_world.info.state_info.states[psp.state].nextstate,
                        shooter,
                    )
                )
    attack_world.player.psprites[stage15.PS_FLASH].sx = attack_world.player.psprites[stage15.PS_WEAPON].sx
    attack_world.player.psprites[stage15.PS_FLASH].sy = attack_world.player.psprites[stage15.PS_WEAPON].sy
    return tuple(shots)


def p_check_ammo_stage17_source_shape(attack_world: Stage17AttackWorld) -> bool:
    attack_world.counters.ammo_checks += 1
    player = attack_world.player
    assert player.ammo is not None
    assert player.weaponowned is not None
    ammo = attack_world.weaponinfo[player.readyweapon].ammo
    if player.readyweapon == stage15.WP_BFG:
        count = 40
    elif player.readyweapon == stage15.WP_SUPERSHOTGUN:
        count = 2
    else:
        count = 1
    if ammo == stage15.AM_NOAMMO or player.ammo[ammo] >= count:
        return True
    attack_world.counters.ammo_failures += 1
    if player.weaponowned[stage15.WP_PLASMA] and player.ammo[stage15.AM_CELL]:
        player.pendingweapon = stage15.WP_PLASMA
    elif player.weaponowned[stage15.WP_SUPERSHOTGUN] and player.ammo[stage15.AM_SHELL] > 2:
        player.pendingweapon = stage15.WP_SUPERSHOTGUN
    elif player.weaponowned[stage15.WP_CHAINGUN] and player.ammo[stage15.AM_CLIP]:
        player.pendingweapon = stage15.WP_CHAINGUN
    elif player.weaponowned[stage15.WP_SHOTGUN] and player.ammo[stage15.AM_SHELL]:
        player.pendingweapon = stage15.WP_SHOTGUN
    elif player.ammo[stage15.AM_CLIP]:
        player.pendingweapon = stage15.WP_PISTOL
    elif player.weaponowned[stage15.WP_CHAINSAW]:
        player.pendingweapon = stage15.WP_CHAINSAW
    elif player.weaponowned[stage15.WP_MISSILE] and player.ammo[stage15.AM_MISL]:
        player.pendingweapon = stage15.WP_MISSILE
    elif player.weaponowned[stage15.WP_BFG] and player.ammo[stage15.AM_CELL] > 40:
        player.pendingweapon = stage15.WP_BFG
    else:
        player.pendingweapon = stage15.WP_FIST
    p_set_psprite_stage17_source_shape(
        attack_world,
        stage15.PS_WEAPON,
        attack_world.weaponinfo[player.readyweapon].downstate,
        attack_world.mobjs[player.mo_index],
    )
    return False


def p_fire_weapon_stage17_source_shape(
    attack_world: Stage17AttackWorld,
    shooter: stage16.ActiveMobj,
) -> tuple[LineAttackShotResult, ...]:
    attack_world.counters.fire_weapon_calls += 1
    if not p_check_ammo_stage17_source_shape(attack_world):
        return ()
    attack_world.counters.player_attack_state_sets += 1
    p_set_psprite_stage17_source_shape(
        attack_world,
        stage15.PS_WEAPON,
        attack_world.weaponinfo[attack_world.player.readyweapon].atkstate,
        shooter,
    )
    attack_world.counters.noise_alert_deferred += 1
    shots: list[LineAttackShotResult] = []
    for _ in range(8):
        moved = p_move_psprites_stage17_source_shape(attack_world, shooter)
        shots.extend(moved)
        if moved:
            break
    return tuple(shots)


def a_weapon_ready_attack_stage17_source_shape(
    attack_world: Stage17AttackWorld,
    shooter: stage16.ActiveMobj,
) -> tuple[LineAttackShotResult, ...]:
    attack_world.counters.weapon_ready_calls += 1
    if attack_world.player.pendingweapon != stage15.WP_NOCHANGE or attack_world.player.health <= 0:
        p_set_psprite_stage17_source_shape(
            attack_world,
            stage15.PS_WEAPON,
            attack_world.weaponinfo[attack_world.player.readyweapon].downstate,
            shooter,
        )
        return ()
    attack_world.player.attackdown = True
    return p_fire_weapon_stage17_source_shape(attack_world, shooter)


def a_fire_shotgun_source_shape(
    attack_world: Stage17AttackWorld,
    shooter: stage16.ActiveMobj,
    _psp: stage15.PspDef,
) -> tuple[LineAttackShotResult, ...]:
    attack_world.counters.selected_fire_actions += 1
    attack_world.counters.sound_deferred += 1
    attack_world.counters.player_attack_state_sets += 1
    _decrease_ammo_source_shape(
        attack_world.player,
        attack_world.weaponinfo[attack_world.player.readyweapon].ammo,
        1,
        attack_world.counters,
    )
    attack_world.counters.flash_setups += 1
    p_set_psprite_stage17_source_shape(
        attack_world,
        stage15.PS_FLASH,
        attack_world.weaponinfo[attack_world.player.readyweapon].flashstate,
        shooter,
    )
    bulletslope = p_bullet_slope_source_shape(attack_world, shooter)
    attack_world.last_bullet_slope = bulletslope
    shots = [
        p_gunshot_source_shape(attack_world, shooter, False, bulletslope, shot_index=i + 1)
        for i in range(7)
    ]
    return tuple(shots)


def build_attack_census_source_shape(
    attack_world: Stage17AttackWorld,
    ref16: stage16.Stage16ActiveMonsterReference,
) -> AttackCensusRecord:
    attack_world.counters.attack_census_runs += 1
    source = attack_world.mobjs[ref16.target.mo_index]
    target = attack_world.mobjs[ref16.final_mobj.index]
    current_angle = source.angle
    player_to_target = stage04.point_to_angle(target.x, target.y, source.x, source.y)
    target_to_player = stage04.point_to_angle(source.x, source.y, target.x, target.y)
    attack_world.counters.current_angle_aims += 1
    before = replace(target)
    aim_current = p_aim_line_attack_source_shape(attack_world, source, current_angle, BULLET_AIM_RANGE)
    if aim_current.target_index != target.index:
        attack_world.counters.current_angle_misses += 1
    attack_world.mobjs[target.index] = before
    before = replace(target)
    aim_selected = p_aim_line_attack_source_shape(attack_world, source, player_to_target, BULLET_AIM_RANGE)
    attack_world.mobjs[target.index] = before
    assert attack_world.player.ammo is not None
    return AttackCensusRecord(
        attacker_mobj_index=source.index,
        target_mapthing_index=target.mapthing_index,
        target_mobj_index=target.index,
        current_angle=current_angle,
        current_angle_degrees=stage13.angle_to_degrees(current_angle),
        player_to_target_angle=player_to_target,
        player_to_target_degrees=stage13.angle_to_degrees(player_to_target),
        target_to_player_angle=target_to_player,
        target_to_player_degrees=stage13.angle_to_degrees(target_to_player),
        angle_delta_degrees=stage13.angle_to_degrees(_u32(player_to_target - current_angle)),
        current_angle_hits_selected=1 if aim_current.target_index == target.index else 0,
        selected_angle_hits_selected=1 if aim_selected.target_index == target.index else 0,
        selected_angle_slope=aim_selected.slope,
        selected_angle_blocked_by_line=aim_selected.blocked_by_line,
        sight_visible=1 if ref16.selected.sight.visible else 0,
        readyweapon=attack_world.player.readyweapon,
        readyweapon_name=_weapon_name(attack_world.player.readyweapon),
        shell_before=attack_world.player.ammo[stage15.AM_SHELL],
        target_health_before=target.health,
        selected_action=SELECTED_WEAPON_NAME,
        candidate_actions=("A_FireShotgun", "A_FirePistol"),
    )


def run_stage17_first_weapon_fire_probe_source_shape(
    attack_world: Stage17AttackWorld,
    ref16: stage16.Stage16ActiveMonsterReference,
    census: AttackCensusRecord,
) -> tuple[LineAttackShotResult, int, int]:
    source = attack_world.mobjs[ref16.target.mo_index]
    source.angle = census.player_to_target_angle
    attack_world.counters.attack_angle_freezes += 1
    shots = a_weapon_ready_attack_stage17_source_shape(attack_world, source)
    return shots, source.angle, attack_world.last_bullet_slope


def _stage17_signature(
    ref16: stage16.Stage16ActiveMonsterReference,
    census: AttackCensusRecord,
    shots: Sequence[LineAttackShotResult],
    counters: Stage17Counters,
    final_target: stage16.ActiveMobj,
    player: stage15.Stage15Player,
    draw: stage15.PatchDrawResult,
    attack_angle: int,
    bullet_slope: int,
    random_start_index: int,
    random_end_index: int,
) -> int:
    signature = ref16.signature
    for value in (
        census.attacker_mobj_index,
        census.target_mapthing_index,
        census.target_mobj_index,
        census.current_angle,
        census.player_to_target_angle,
        census.target_to_player_angle,
        census.current_angle_hits_selected,
        census.selected_angle_hits_selected,
        census.selected_angle_slope,
        census.selected_angle_blocked_by_line,
        census.sight_visible,
        census.readyweapon,
        census.shell_before,
        census.target_health_before,
        attack_angle,
        bullet_slope,
        random_start_index,
        random_end_index,
        player.ammo[stage15.AM_SHELL] if player.ammo is not None else 0,
        player.readyweapon,
        player.pendingweapon,
        player.killcount,
        final_target.health,
        final_target.state if final_target.state is not None else 0,
        final_target.tics,
        final_target.flags,
        final_target.momx,
        final_target.momy,
        draw.status_pixels,
        draw.weapon_pixels,
        draw.signature,
    ):
        signature = _hash_u32(signature, value)
    for shot in shots:
        for value in (
            shot.shot_index,
            shot.angle,
            shot.damage,
            shot.hit_mobj_index if shot.hit_mobj_index is not None else 0xFFFFFFFF,
            shot.selected_hit,
            shot.target_health_after,
            shot.target_state_after if shot.target_state_after is not None else 0,
            shot.killed,
            shot.blocked_by_line,
        ):
            signature = _hash_u32(signature, value)
    for value in (
        counters.attack_census_runs,
        counters.attack_angle_freezes,
        counters.current_angle_misses,
        counters.ammo_checks,
        counters.ammo_failures,
        counters.weapon_ready_calls,
        counters.fire_weapon_calls,
        counters.selected_fire_actions,
        counters.psprite_set_calls,
        counters.psprite_move_calls,
        counters.flash_setups,
        counters.ammo_decrements,
        counters.shell_spent,
        counters.bullet_slope_calls,
        counters.gunshots,
        counters.aim_line_attacks,
        counters.aim_hits,
        counters.aim_misses,
        counters.line_attacks,
        counters.path_traverses,
        counters.line_intercepts,
        counters.thing_intercepts,
        counters.traversed_intercepts,
        counters.solid_line_blocks,
        counters.shootable_thing_intercepts,
        counters.line_hits,
        counters.line_misses,
        counters.damage_events,
        counters.damage_total,
        counters.pain_events,
        counters.kill_events,
        counters.drop_deferred,
        counters.sound_deferred,
        counters.noise_alert_deferred,
        counters.light_deferred,
        counters.unsupported_weapon_deferrals,
        counters.monster_chase_moves,
        counters.live_keyboard_deferred,
    ):
        signature = _hash_u32(signature, value)
    signature = _hash_bytes(signature, census.selected_action.encode("ascii"))
    signature = _hash_bytes(signature, _state_name(stage16.parse_stage16_info_tables(), final_target.state).encode("ascii"))
    return signature


def _reference_stage17_uncached(wad_path: str) -> Stage17FirstWeaponFireReference:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    ref16 = stage16.reference_active_monster_thinkers_and_targeting_for_pinned_map(wad_path)
    stage15_world = stage15.build_stage15_world(wad, loaded, ref16.stage15.stage14)
    stage15.run_pickup_probes_source_shape(stage15_world)
    info = stage16.parse_stage16_info_tables()
    attack_world = build_stage17_attack_world(stage15_world, ref16, info)
    _rng_for_start, random_start_index = _random_after_stage16_spawn_sequence(stage15_world, info)
    census = build_attack_census_source_shape(attack_world, ref16)
    shell_before = attack_world.player.ammo[stage15.AM_SHELL]
    health_before = attack_world.mobjs[ref16.final_mobj.index].health
    shots, attack_angle, bullet_slope = run_stage17_first_weapon_fire_probe_source_shape(attack_world, ref16, census)
    final_target = replace(attack_world.mobjs[ref16.final_mobj.index])
    shell_after = attack_world.player.ammo[stage15.AM_SHELL]
    health_after = final_target.health
    weapon_psp = attack_world.player.psprites[stage15.PS_WEAPON]
    flash_psp = attack_world.player.psprites[stage15.PS_FLASH]
    stage15.st_ticker_compact_source_shape(stage15_world)
    draw = stage15.build_status_psprite_patch_draw_source_shape(wad, stage15_world)
    signature = _stage17_signature(
        ref16,
        census,
        shots,
        attack_world.counters,
        final_target,
        attack_world.player,
        draw,
        attack_angle,
        bullet_slope,
        random_start_index,
        attack_world.rng.prndindex,
    )
    return Stage17FirstWeaponFireReference(
        stage16=ref16,
        census=census,
        shots=tuple(shots),
        counters=replace(attack_world.counters),
        final_target=final_target,
        player=attack_world.player,
        draw=draw,
        attack_angle=attack_angle,
        attack_angle_degrees=stage13.angle_to_degrees(attack_angle),
        bullet_slope=bullet_slope,
        random_start_index=random_start_index,
        random_end_index=attack_world.rng.prndindex,
        shell_before=shell_before,
        shell_after=shell_after,
        health_before=health_before,
        health_after=health_after,
        weapon_state=weapon_psp.state if weapon_psp.state is not None else 0,
        weapon_state_name=_psprite_state_name(info.state_info, weapon_psp.state),
        weapon_tics=weapon_psp.tics,
        flash_state=flash_psp.state if flash_psp.state is not None else 0,
        flash_state_name=_psprite_state_name(info.state_info, flash_psp.state),
        flash_tics=flash_psp.tics,
        signature=signature,
    )


@lru_cache(maxsize=4)
def _reference_stage17_cached(wad_path: str) -> Stage17FirstWeaponFireReference:
    return _reference_stage17_uncached(wad_path)


def reference_first_weapon_fire_damage_and_death_probe_for_pinned_map(
    wad_path: str | Path,
) -> Stage17FirstWeaponFireReference:
    return _reference_stage17_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage17FirstWeaponFireReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_first_weapon_fire_damage_and_death_probe_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage17_load_wad_first_weapon_fire_damage_death_probe")

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


def emit_source_stage17_load_wad_first_weapon_fire_damage_death_probe(pe: PE32) -> None:
    pe.label("source_stage17_load_wad_first_weapon_fire_damage_death_probe")
    x86.mov_mem_abs32_imm32(pe, "map_loaded", 0)
    stage01.emit_set_status_ptrs(pe, "status_load_failed", "status_title_failed")

    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, stage01.FILE_ATTRIBUTE_NORMAL)
    x86.push_imm32(pe, stage01.OPEN_EXISTING)
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, stage01.FILE_SHARE_READ)
    x86.push_imm32(pe, stage01.GENERIC_READ)
    x86.push_abs32(pe, "wad_path_w")
    x86.call_import(pe, stage01.KERNEL32, "CreateFileW")
    x86.cmp_eax_imm32(pe, stage01.INVALID_HANDLE_VALUE)
    x86.jne_rel32(pe, "source_stage17_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage17_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage17_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage17_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage17_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage17_close_and_return")

    pe.label("source_stage17_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage17_close_and_return")
    x86.call_rel32(pe, "render_init_texture_data_setup_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage17_close_and_return")
    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage17_close_and_return")
    x86.call_rel32(pe, "source_stage06_run_live_seg_clip_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage17_close_and_return")

    x86.call_rel32(pe, "render_composite_two_sided_wall_edges_debug")
    x86.call_rel32(pe, "render_visplanes_floor_ceiling_debug")
    x86.call_rel32(pe, "render_sky_and_masked_midtextures_debug")
    x86.call_rel32(pe, "render_things_sprites_real_frame_setup_debug")
    x86.call_rel32(pe, "render_game_loop_input_collision_debug")
    x86.call_rel32(pe, "render_pickups_psprites_statusbar_shell_debug")
    x86.call_rel32(pe, "render_active_monster_thinkers_targeting_debug")
    x86.call_rel32(pe, "render_first_weapon_fire_damage_death_probe_debug")
    x86.call_rel32(pe, "build_success_status")
    x86.call_rel32(pe, "append_stage13_success_status")
    x86.call_rel32(pe, "append_stage14_success_status")
    x86.call_rel32(pe, "append_stage15_success_status")
    x86.call_rel32(pe, "append_stage16_success_status")
    x86.call_rel32(pe, "append_stage17_success_status")

    pe.label("source_stage17_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_render_first_weapon_fire_damage_death_probe_debug(pe: PE32) -> None:
    pe.label("P_PlayerShotgunFire_first_damage_source_shape_debug")
    pe.label("P_BulletSlope_GunShot_first_damage_source_shape_debug")
    pe.label("P_AimLineAttack_LineAttack_bounded_source_shape_debug")
    pe.label("P_PathTraverse_hitscan_bounded_source_shape_debug")
    pe.label("P_DamageMobj_KillMobj_first_damage_source_shape_debug")
    pe.label("P_SetMobjState_SpawnBlood_first_damage_source_shape_debug")
    pe.label("P_Random_weapon_damage_source_shape_debug")
    pe.label("render_first_weapon_fire_damage_death_probe_debug")

    x86.mov_reg_mem_abs32(pe, "eax", "stage17_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage17_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage17_line_attacks")
    x86.mov_mem_abs32_eax(pe, "stage17_runtime_line_attacks")
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage14._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage17_success_status(pe: PE32) -> None:
    pe.label("append_stage17_success_status")

    _emit_seek_buffer_end(pe, "status_success_buffer", "stage17_status")
    stage01.append_c_string_label(pe, "status_stage17_success_header")
    stage01.append_u32_label(pe, "status_stage17_angle_prefix", "stage17_attack_angle_degrees")
    stage01.append_u32_label(pe, "status_stage17_damage_prefix", "stage17_damage_total")
    stage01.append_i32_label(pe, "status_stage17_health_prefix", "stage17_health_after")
    stage01.append_u32_label(pe, "status_stage17_signature_prefix", "stage17_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage17_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage17_title")
    stage01.append_u32_label(pe, "title_stage17_census_prefix", "stage17_attack_census_runs")
    stage01.append_u32_label(pe, "title_stage17_attacker_prefix", "stage17_attacker_mobj")
    stage01.append_u32_label(pe, "title_stage17_target_prefix", "stage17_target_mobj")
    stage01.append_u32_label(pe, "title_stage17_weapon_prefix", "stage17_readyweapon")
    stage01.append_c_string_label(pe, "title_stage17_action_prefix")
    stage01.append_c_string_label(pe, "stage17_selected_action_name")
    stage01.append_u32_label(pe, "title_stage17_current_angle_prefix", "stage17_current_angle_degrees")
    stage01.append_u32_label(pe, "title_stage17_attack_angle_prefix", "stage17_attack_angle_degrees")
    stage01.append_u32_label(pe, "title_stage17_target_bearing_prefix", "stage17_target_bearing_degrees")
    stage01.append_u32_label(pe, "title_stage17_angle_delta_prefix", "stage17_angle_delta_degrees")
    stage01.append_u32_label(pe, "title_stage17_current_miss_prefix", "stage17_current_angle_misses")
    stage01.append_u32_label(pe, "title_stage17_angle_freeze_prefix", "stage17_attack_angle_freezes")
    stage01.append_u32_label(pe, "title_stage17_sight_prefix", "stage17_sight_visible")
    stage01.append_u32_label(pe, "title_stage17_ammo_before_prefix", "stage17_shell_before")
    stage01.append_u32_label(pe, "title_stage17_ammo_after_prefix", "stage17_shell_after")
    stage01.append_u32_label(pe, "title_stage17_weapon_state_prefix", "stage17_weapon_state")
    stage01.append_c_string_label(pe, "title_stage17_weapon_state_name_prefix")
    stage01.append_c_string_label(pe, "stage17_weapon_state_name")
    stage01.append_u32_label(pe, "title_stage17_weapon_tics_prefix", "stage17_weapon_tics")
    stage01.append_u32_label(pe, "title_stage17_flash_state_prefix", "stage17_flash_state")
    stage01.append_c_string_label(pe, "title_stage17_flash_state_name_prefix")
    stage01.append_c_string_label(pe, "stage17_flash_state_name")
    stage01.append_u32_label(pe, "title_stage17_flash_tics_prefix", "stage17_flash_tics")
    stage01.append_u32_label(pe, "title_stage17_aim_prefix", "stage17_aim_line_attacks")
    stage01.append_u32_label(pe, "title_stage17_line_attack_prefix", "stage17_runtime_line_attacks")
    stage01.append_u32_label(pe, "title_stage17_path_prefix", "stage17_path_traverses")
    stage01.append_u32_label(pe, "title_stage17_line_intercepts_prefix", "stage17_line_intercepts")
    stage01.append_u32_label(pe, "title_stage17_thing_intercepts_prefix", "stage17_thing_intercepts")
    stage01.append_u32_label(pe, "title_stage17_hits_prefix", "stage17_line_hits")
    stage01.append_u32_label(pe, "title_stage17_damage_events_prefix", "stage17_damage_events")
    stage01.append_u32_label(pe, "title_stage17_damage_total_prefix", "stage17_damage_total")
    stage01.append_i32_label(pe, "title_stage17_health_before_prefix", "stage17_health_before")
    stage01.append_i32_label(pe, "title_stage17_health_after_prefix", "stage17_health_after")
    stage01.append_c_string_label(pe, "title_stage17_final_state_name_prefix")
    stage01.append_c_string_label(pe, "stage17_final_state_name")
    stage01.append_u32_label(pe, "title_stage17_final_state_prefix", "stage17_final_state")
    stage01.append_u32_label(pe, "title_stage17_pain_prefix", "stage17_pain_events")
    stage01.append_u32_label(pe, "title_stage17_kill_prefix", "stage17_kill_events")
    stage01.append_u32_label(pe, "title_stage17_drop_prefix", "stage17_drop_deferred")
    stage01.append_u32_label(pe, "title_stage17_status_pixels_prefix", "stage17_status_pixels")
    stage01.append_u32_label(pe, "title_stage17_weapon_pixels_prefix", "stage17_weapon_pixels")
    stage01.append_u32_label(pe, "title_stage17_monster_chase_moves_prefix", "stage17_monster_chase_moves")
    stage01.append_u32_label(pe, "title_stage17_live_input_prefix", "stage17_live_keyboard_deferred")
    stage01.append_u32_label(pe, "title_stage17_signature_prefix", "stage17_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage17_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    counters = ref.counters if ref is not None else Stage17Counters()
    census = ref.census if ref is not None else None
    final_target = ref.final_target if ref is not None else None

    pe.align_section(4)
    pe.label("stage17_attack_census_runs")
    pe.emit_u32(counters.attack_census_runs)
    pe.label("stage17_attacker_mobj")
    pe.emit_u32(census.attacker_mobj_index if census is not None else 0)
    pe.label("stage17_target_mapthing")
    pe.emit_u32(census.target_mapthing_index if census is not None else 0)
    pe.label("stage17_target_mobj")
    pe.emit_u32(census.target_mobj_index if census is not None else 0)
    pe.label("stage17_readyweapon")
    pe.emit_u32(census.readyweapon if census is not None else 0)
    pe.label("stage17_current_angle_degrees")
    pe.emit_u32(census.current_angle_degrees if census is not None else 0)
    pe.label("stage17_attack_angle_degrees")
    pe.emit_u32(ref.attack_angle_degrees if ref is not None else 0)
    pe.label("stage17_target_bearing_degrees")
    pe.emit_u32(census.player_to_target_degrees if census is not None else 0)
    pe.label("stage17_monster_bearing_degrees")
    pe.emit_u32(census.target_to_player_degrees if census is not None else 0)
    pe.label("stage17_angle_delta_degrees")
    pe.emit_u32(census.angle_delta_degrees if census is not None else 0)
    pe.label("stage17_current_angle_hits_selected")
    pe.emit_u32(census.current_angle_hits_selected if census is not None else 0)
    pe.label("stage17_current_angle_misses")
    pe.emit_u32(counters.current_angle_misses)
    pe.label("stage17_attack_angle_freezes")
    pe.emit_u32(counters.attack_angle_freezes)
    pe.label("stage17_sight_visible")
    pe.emit_u32(census.sight_visible if census is not None else 0)
    pe.label("stage17_shell_before")
    pe.emit_u32(ref.shell_before if ref is not None else 0)
    pe.label("stage17_shell_after")
    pe.emit_u32(ref.shell_after if ref is not None else 0)
    pe.label("stage17_health_before")
    pe.emit_u32((ref.health_before if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage17_health_after")
    pe.emit_u32((ref.health_after if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage17_weapon_state")
    pe.emit_u32(ref.weapon_state if ref is not None else 0)
    pe.label("stage17_weapon_tics")
    pe.emit_u32(ref.weapon_tics if ref is not None else 0)
    pe.label("stage17_flash_state")
    pe.emit_u32(ref.flash_state if ref is not None else 0)
    pe.label("stage17_flash_tics")
    pe.emit_u32(ref.flash_tics if ref is not None else 0)
    pe.label("stage17_random_start_index")
    pe.emit_u32(ref.random_start_index if ref is not None else 0)
    pe.label("stage17_random_end_index")
    pe.emit_u32(ref.random_end_index if ref is not None else 0)
    pe.label("stage17_bullet_slope")
    pe.emit_u32((ref.bullet_slope if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage17_ammo_checks")
    pe.emit_u32(counters.ammo_checks)
    pe.label("stage17_ammo_failures")
    pe.emit_u32(counters.ammo_failures)
    pe.label("stage17_weapon_ready_calls")
    pe.emit_u32(counters.weapon_ready_calls)
    pe.label("stage17_fire_weapon_calls")
    pe.emit_u32(counters.fire_weapon_calls)
    pe.label("stage17_selected_fire_actions")
    pe.emit_u32(counters.selected_fire_actions)
    pe.label("stage17_psprite_set_calls")
    pe.emit_u32(counters.psprite_set_calls)
    pe.label("stage17_psprite_move_calls")
    pe.emit_u32(counters.psprite_move_calls)
    pe.label("stage17_flash_setups")
    pe.emit_u32(counters.flash_setups)
    pe.label("stage17_ammo_decrements")
    pe.emit_u32(counters.ammo_decrements)
    pe.label("stage17_shell_spent")
    pe.emit_u32(counters.shell_spent)
    pe.label("stage17_bullet_slope_calls")
    pe.emit_u32(counters.bullet_slope_calls)
    pe.label("stage17_gunshots")
    pe.emit_u32(counters.gunshots)
    pe.label("stage17_aim_line_attacks")
    pe.emit_u32(counters.aim_line_attacks)
    pe.label("stage17_line_attacks")
    pe.emit_u32(counters.line_attacks)
    pe.label("stage17_runtime_line_attacks")
    pe.emit_u32(0)
    pe.label("stage17_path_traverses")
    pe.emit_u32(counters.path_traverses)
    pe.label("stage17_line_intercepts")
    pe.emit_u32(counters.line_intercepts)
    pe.label("stage17_thing_intercepts")
    pe.emit_u32(counters.thing_intercepts)
    pe.label("stage17_traversed_intercepts")
    pe.emit_u32(counters.traversed_intercepts)
    pe.label("stage17_solid_line_blocks")
    pe.emit_u32(counters.solid_line_blocks)
    pe.label("stage17_shootable_intercepts")
    pe.emit_u32(counters.shootable_thing_intercepts)
    pe.label("stage17_line_hits")
    pe.emit_u32(counters.line_hits)
    pe.label("stage17_line_misses")
    pe.emit_u32(counters.line_misses)
    pe.label("stage17_damage_events")
    pe.emit_u32(counters.damage_events)
    pe.label("stage17_damage_total")
    pe.emit_u32(counters.damage_total)
    pe.label("stage17_pain_events")
    pe.emit_u32(counters.pain_events)
    pe.label("stage17_kill_events")
    pe.emit_u32(counters.kill_events)
    pe.label("stage17_drop_deferred")
    pe.emit_u32(counters.drop_deferred)
    pe.label("stage17_removal_deferred")
    pe.emit_u32(counters.removal_deferred)
    pe.label("stage17_final_state")
    pe.emit_u32(final_target.state if final_target is not None and final_target.state is not None else 0)
    pe.label("stage17_status_pixels")
    pe.emit_u32(ref.draw.status_pixels if ref is not None else 0)
    pe.label("stage17_weapon_pixels")
    pe.emit_u32(ref.draw.weapon_pixels if ref is not None else 0)
    pe.label("stage17_sound_deferred")
    pe.emit_u32(counters.sound_deferred)
    pe.label("stage17_noise_alert_deferred")
    pe.emit_u32(counters.noise_alert_deferred)
    pe.label("stage17_light_deferred")
    pe.emit_u32(counters.light_deferred)
    pe.label("stage17_unsupported_weapon_deferrals")
    pe.emit_u32(counters.unsupported_weapon_deferrals)
    pe.label("stage17_generalized_combat_deferred")
    pe.emit_u32(counters.generalized_combat_deferred)
    pe.label("stage17_monster_chase_moves")
    pe.emit_u32(counters.monster_chase_moves)
    pe.label("stage17_doors_switches_deferred")
    pe.emit_u32(counters.doors_switches_deferred)
    pe.label("stage17_sector_specials_deferred")
    pe.emit_u32(counters.sector_specials_deferred)
    pe.label("stage17_live_keyboard_deferred")
    pe.emit_u32(counters.live_keyboard_deferred)
    pe.label("stage17_expected_signature")
    pe.emit_u32(ref.signature if ref is not None else 0)
    pe.label("stage17_runtime_signature")
    pe.emit_u32(0)

    pe.align_section(1)
    pe.label("stage17_selected_action_name")
    x86.emit_asciiz(pe, census.selected_action if census is not None else "")
    pe.label("stage17_readyweapon_name")
    x86.emit_asciiz(pe, census.readyweapon_name if census is not None else "")
    pe.label("stage17_weapon_state_name")
    x86.emit_asciiz(pe, ref.weapon_state_name if ref is not None else "")
    pe.label("stage17_flash_state_name")
    x86.emit_asciiz(pe, ref.flash_state_name if ref is not None else "")
    pe.label("stage17_final_state_name")
    x86.emit_asciiz(pe, _state_name(stage16.parse_stage16_info_tables(), final_target.state) if final_target is not None else "")
    pe.label("stage17_first_damage_probe_padding")
    x86.emit_asciiz(pe, "stage17 deterministic first damage proof data")

    pe.label("status_stage17_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage17_first_weapon_fire_damage_and_death_probe\r\n"
        "First source-shaped weapon fire damage probe OK\r\n",
    )
    pe.label("status_stage17_angle_prefix")
    x86.emit_asciiz(pe, "\r\nFrozen attack angle degrees: ")
    pe.label("status_stage17_damage_prefix")
    x86.emit_asciiz(pe, "\r\nApplied weapon damage: ")
    pe.label("status_stage17_health_prefix")
    x86.emit_asciiz(pe, "\r\nTarget health after damage: ")
    pe.label("status_stage17_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage17 first damage signature: ")
    pe.label("status_stage17_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage17 preserves the released stage16 active-monster proof, then "
        "runs a bounded player shotgun fire probe. A source-shaped attack census "
        "shows the current player angle misses the selected shotgun guy, freezes "
        "the documented aim angle, advances the ready shotgun psprite to "
        "A_FireShotgun, runs P_BulletSlope, P_AimLineAttack, P_LineAttack, "
        "and mutates the selected monster through P_DamageMobj. Wider combat "
        "and unrelated engine systems remain outside this release.\r\n",
    )

    pe.label("title_stage17_census_prefix")
    x86.emit_asciiz(pe, " ACENS=")
    pe.label("title_stage17_attacker_prefix")
    x86.emit_asciiz(pe, " ATMO=")
    pe.label("title_stage17_target_prefix")
    x86.emit_asciiz(pe, " TGMO=")
    pe.label("title_stage17_weapon_prefix")
    x86.emit_asciiz(pe, " W17=")
    pe.label("title_stage17_action_prefix")
    x86.emit_asciiz(pe, " WACT=")
    pe.label("title_stage17_current_angle_prefix")
    x86.emit_asciiz(pe, " CANG=")
    pe.label("title_stage17_attack_angle_prefix")
    x86.emit_asciiz(pe, " AANG=")
    pe.label("title_stage17_target_bearing_prefix")
    x86.emit_asciiz(pe, " TBRG=")
    pe.label("title_stage17_angle_delta_prefix")
    x86.emit_asciiz(pe, " ADEL=")
    pe.label("title_stage17_current_miss_prefix")
    x86.emit_asciiz(pe, " CMISS=")
    pe.label("title_stage17_angle_freeze_prefix")
    x86.emit_asciiz(pe, " AIMFIX=")
    pe.label("title_stage17_sight_prefix")
    x86.emit_asciiz(pe, " S17LOS=")
    pe.label("title_stage17_ammo_before_prefix")
    x86.emit_asciiz(pe, " SH0=")
    pe.label("title_stage17_ammo_after_prefix")
    x86.emit_asciiz(pe, " SH1=")
    pe.label("title_stage17_weapon_state_prefix")
    x86.emit_asciiz(pe, " PSP17=")
    pe.label("title_stage17_weapon_state_name_prefix")
    x86.emit_asciiz(pe, " PSP17N=")
    pe.label("title_stage17_weapon_tics_prefix")
    x86.emit_asciiz(pe, " PSP17T=")
    pe.label("title_stage17_flash_state_prefix")
    x86.emit_asciiz(pe, " FLS=")
    pe.label("title_stage17_flash_state_name_prefix")
    x86.emit_asciiz(pe, " FLSN=")
    pe.label("title_stage17_flash_tics_prefix")
    x86.emit_asciiz(pe, " FLT=")
    pe.label("title_stage17_aim_prefix")
    x86.emit_asciiz(pe, " AIM=")
    pe.label("title_stage17_line_attack_prefix")
    x86.emit_asciiz(pe, " LNA=")
    pe.label("title_stage17_path_prefix")
    x86.emit_asciiz(pe, " PATH=")
    pe.label("title_stage17_line_intercepts_prefix")
    x86.emit_asciiz(pe, " LI=")
    pe.label("title_stage17_thing_intercepts_prefix")
    x86.emit_asciiz(pe, " TI=")
    pe.label("title_stage17_hits_prefix")
    x86.emit_asciiz(pe, " HIT17=")
    pe.label("title_stage17_damage_events_prefix")
    x86.emit_asciiz(pe, " DEVT=")
    pe.label("title_stage17_damage_total_prefix")
    x86.emit_asciiz(pe, " DMG17=")
    pe.label("title_stage17_health_before_prefix")
    x86.emit_asciiz(pe, " HP0=")
    pe.label("title_stage17_health_after_prefix")
    x86.emit_asciiz(pe, " H17=")
    pe.label("title_stage17_final_state_name_prefix")
    x86.emit_asciiz(pe, " ST17N=")
    pe.label("title_stage17_final_state_prefix")
    x86.emit_asciiz(pe, " ST17=")
    pe.label("title_stage17_pain_prefix")
    x86.emit_asciiz(pe, " PAIN=")
    pe.label("title_stage17_kill_prefix")
    x86.emit_asciiz(pe, " KILL17=")
    pe.label("title_stage17_drop_prefix")
    x86.emit_asciiz(pe, " DROPDEF=")
    pe.label("title_stage17_status_pixels_prefix")
    x86.emit_asciiz(pe, " ST17PIX=")
    pe.label("title_stage17_weapon_pixels_prefix")
    x86.emit_asciiz(pe, " WP17PIX=")
    pe.label("title_stage17_monster_chase_moves_prefix")
    x86.emit_asciiz(pe, " CHASEMV=")
    pe.label("title_stage17_live_input_prefix")
    x86.emit_asciiz(pe, " LIVEIN=")
    pe.label("title_stage17_signature_prefix")
    x86.emit_asciiz(pe, " S17SIG=")


def build_source_stage17_first_weapon_fire_damage_and_death_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage17_load_wad_first_weapon_fire_damage_death_probe(pe)
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
    emit_render_first_weapon_fire_damage_death_probe_debug(pe)
    stage12.emit_build_success_status(pe)
    stage13.emit_append_stage13_success_status(pe)
    stage14.emit_append_stage14_success_status(pe)
    stage15.emit_append_stage15_success_status(pe)
    stage16.emit_append_stage16_success_status(pe)
    emit_append_stage17_success_status(pe)
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
    emit_stage17_data(pe)
    return pe.build("entry")


def write_source_stage17_first_weapon_fire_damage_and_death_probe_exe(path: str | Path) -> bytes:
    image = build_source_stage17_first_weapon_fire_damage_and_death_probe_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage17 first weapon fire/damage PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage17_first_weapon_fire_damage_and_death_probe.exe",
        help="path to write, default: build/source_stage17_first_weapon_fire_damage_and_death_probe.exe",
    )
    args = parser.parse_args()
    write_source_stage17_first_weapon_fire_damage_and_death_probe_exe(args.output)


if __name__ == "__main__":
    main()
