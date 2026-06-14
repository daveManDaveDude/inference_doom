from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage25_first_platform_lift_cycle_probe as stage25
from tools import x86
from tools.map_loader import NO_SIDEDEF, load_map
from tools.pe32 import PE32
from tools.wad import WadFile


stage01 = stage25.stage01
stage02 = stage25.stage02
stage03 = stage25.stage03
stage04 = stage25.stage04
stage07 = stage25.stage07
stage08 = stage25.stage08
stage10 = stage25.stage10
stage11 = stage25.stage11
stage12 = stage25.stage12
stage13 = stage25.stage13
stage14 = stage25.stage14
stage15 = stage25.stage15
stage16 = stage25.stage16
stage17 = stage25.stage17
stage18 = stage25.stage18
stage19 = stage25.stage19
stage20 = stage25.stage20
stage21 = stage25.stage21
stage22 = stage25.stage22
stage23 = stage25.stage23
stage24 = stage25.stage24


FRAMEBUFFER_WIDTH = stage25.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage25.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage25.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage25.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage25.WINDOW_WIDTH
WINDOW_HEIGHT = stage25.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage26FirstCeilingOrCrusherSpecialProbe"
WINDOW_TITLE = "Inference Doom S26 Ceiling Crusher Special"
WAD_PATH = stage25.WAD_PATH

FRACBITS = stage25.FRACBITS
FRACUNIT = stage25.FRACUNIT
FNV_PRIME = stage25.FNV_PRIME
CEILSPEED = FRACUNIT
TICRATE = stage21.TICRATE
MAXCEILINGS = 30
BUTTONTIME = stage25.BUTTONTIME
LOWER_TO_FLOOR = 0
RAISE_TO_HIGHEST = 1
LOWER_AND_CRUSH = 2
CRUSH_AND_RAISE = 3
FAST_CRUSH_AND_RAISE = 4
SILENT_CRUSH_AND_RAISE = 5
DEFAULT_STAGE26_TICKER_TICS = 210

SELECTED_MAP = "MAP29"
SELECTED_LINE_INDEX = 71
SELECTED_SPECIAL = 49
SELECTED_TAG = 40
SELECTED_RIGHT_SIDEDEF = 125
SELECTED_LEFT_SIDEDEF = NO_SIDEDEF
SELECTED_FRONT_SECTOR = 75
SELECTED_TARGET_SECTOR = 117

BUTTON_MIDDLE = stage25.BUTTON_MIDDLE
RESULT_OK = stage21.RESULT_OK
RESULT_CRUSHED = stage21.RESULT_CRUSHED
RESULT_PASTDEST = stage21.RESULT_PASTDEST
THINKER_FUNCTION_CEILING = 4

SOURCE_TRACE = stage25.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_switch.c",
        "P_UseSpecialLine case 49 one-shot crushAndRaise ceiling switch path",
        "P_UseSpecialLine_switch49_crushAndRaise_stage26_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_ceilng.c",
        "EV_DoCeiling crushAndRaise selected tagged ceiling thinker setup",
        "EV_DoCeiling_crushAndRaise_stage26_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_spec.c",
        "P_FindSectorFromLineTag selected MAP29 tag 40 traversal",
        "P_FindSectorFromLineTag_stage26_ceiling_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_ceilng.c",
        "T_MoveCeiling selected crushAndRaise down/up reversals and sound boundaries",
        "T_MoveCeiling_crushAndRaise_stage26_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_floor.c",
        "T_MovePlane ceiling branch selected down/up movement and strict clamp",
        "T_MovePlane_ceiling_stage26_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_ceilng.c",
        "P_AddActiveCeiling/P_RemoveActiveCeiling selected activeceilings slot lifecycle",
        "P_ActiveCeiling_stage26_source_shape_debug",
    ),
)


@dataclass
class Stage26Counters(stage25.Stage25Counters):
    ev_do_ceiling_calls: int = 0
    ceiling_find_sector_calls: int = 0
    ceiling_tag_scan_steps: int = 0
    ceiling_tagged_sector_matches: int = 0
    ceiling_tagged_sector_spawns: int = 0
    ceiling_already_active_skips: int = 0
    ceiling_no_matching_tag_results: int = 0
    ceiling_thinker_records: int = 0
    ceiling_allocation_deferrals: int = 0
    activeceiling_add_calls: int = 0
    activeceiling_slot_allocations: int = 0
    activeceiling_full_errors: int = 0
    activeceiling_remove_calls: int = 0
    activeceiling_slot_clears: int = 0
    activeceiling_missing_errors: int = 0
    ceiling_ticks: int = 0
    ceiling_move_plane_calls: int = 0
    ceiling_mutations: int = 0
    ceiling_pastdest_events: int = 0
    ceiling_change_sector_checks: int = 0
    ceiling_change_sector_nofit: int = 0
    ceiling_crush_events: int = 0
    ceiling_bottom_reversals: int = 0
    ceiling_top_reversals: int = 0
    ceiling_removal_requests: int = 0
    ceiling_move_sound_deferrals: int = 0
    ceiling_stop_sound_deferrals: int = 0
    unsupported_ceiling_type_absent: int = 1
    generalized_ceiling_absent: int = 1
    generalized_floor_absent: int = 1
    generalized_plat_absent: int = 1
    stage27_absent: int = 1


@dataclass
class Stage26CeilingThinker:
    sector_index: int
    type: int
    speed: int
    bottomheight: int
    topheight: int
    direction: int
    olddirection: int
    crush: bool
    tag: int
    active: int = 1
    removal_requested: int = 0
    active_slot: int = -1


@dataclass(frozen=True)
class Stage26CeilingSpawnRecord:
    rtn: int
    line_index: int
    tag: int
    matched_sectors: tuple[int, ...]
    spawned_sectors: tuple[int, ...]
    skipped_active_sectors: tuple[int, ...]
    selected_sector: int
    floorheight: int
    ceiling_before: int
    special: int
    bottomheight: int
    topheight: int
    speed: int
    direction: int
    crush: int
    ceiling_type: int
    active_slot: int


@dataclass(frozen=True)
class Stage26CeilingTraceRecord:
    tic: int
    leveltime_before: int
    sector_index: int
    ceiling_before: int
    ceiling_after: int
    direction_before: int
    direction_after: int
    dest: int
    speed: int
    result: int
    removed: int
    move_sound: int
    stop_sound: int


@dataclass(frozen=True)
class Stage26PinnedCensusRecord:
    map_name: str
    line_index: int
    special: int
    tag: int
    side: int
    right_sidedef: int
    left_sidedef: int
    front_sector: int
    middle_texture_before: str
    middle_texture_pressed: str
    middle_texture_restored: str
    target_sector: int
    target_floor: int
    target_ceiling_before: int
    target_ceiling_after: int
    target_special: int
    bottomheight: int


@dataclass
class Stage26World(stage25.Stage25World):
    counters: Stage26Counters = field(default_factory=Stage26Counters)
    activeceilings: list[Stage26CeilingThinker | None] = field(default_factory=lambda: [None for _ in range(MAXCEILINGS)])
    selected_ceiling: Stage26CeilingThinker | None = None
    selected_ceiling_node: stage21.Stage21ThinkerNode | None = None
    ceiling_spawn: Stage26CeilingSpawnRecord | None = None
    ceiling_trace: list[Stage26CeilingTraceRecord] = field(default_factory=list)


@dataclass(frozen=True)
class Stage26FirstCeilingOrCrusherSpecialReference:
    stage25: stage25.Stage25FirstPlatformLiftCycleReference
    census: Stage26PinnedCensusRecord
    switch: stage22.Stage22SwitchTextureResult
    ceiling_spawn: Stage26CeilingSpawnRecord
    ceiling_trace: tuple[Stage26CeilingTraceRecord, ...]
    counters: Stage26Counters
    ticker_counters: stage21.Stage21Counters
    leveltime_before: int
    leveltime_after: int
    order_ok: int
    signature: int


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & 0xFFFFFFFF


def _hash_bytes(signature: int, data: bytes) -> int:
    for byte in data:
        signature = _hash_u32(signature, byte)
    return signature


def _texture_name(world: stage22.Stage22World, texture_id: int) -> str:
    return stage22._texture_name(world, texture_id)


def p_find_highest_ceiling_surrounding_stage26_source_shape(
    world: stage19.Stage19World,
    sector_index: int,
) -> int:
    height = 0
    for line_index in world.sector_lines.get(sector_index, []):
        line = world.lines[line_index]
        other = stage19.get_next_sector_stage19_source_shape(world, line, sector_index)
        if other is not None and world.sectors[other].ceilingheight > height:
            height = world.sectors[other].ceilingheight
    return height


def _build_stage26_world(wad: WadFile, map_name: str) -> Stage26World:
    loaded = load_map(wad, map_name)
    block_data = wad.read_lump(wad.map_lumps(map_name).get("BLOCKMAP"))
    blockmap = stage14.p_load_blockmap_source_shape(block_data, num_lines=len(loaded.linedefs))
    base = stage19.Stage19World(
        loaded=loaded,
        blockmap=blockmap,
        sectors=[
            stage19.Stage19Sector(
                index=index,
                floorheight=sector.floor_height << FRACBITS,
                ceilingheight=sector.ceiling_height << FRACBITS,
                special=sector.special_type,
                tag=sector.tag,
            )
            for index, sector in enumerate(loaded.sectors)
        ],
        lines=stage19.build_stage19_lines(loaded),
        sector_lines={},
        counters=stage19.Stage19Counters(special_census_runs=1),
    )
    base.sector_lines = stage19.build_stage19_sector_lines(base.lines, len(base.sectors))
    setup = stage08.load_texture_setup_from_wad(wad)
    pairs = stage22.p_init_switch_list_stage22_source_shape(setup, None, episode=3)
    switchlist, switch_names = stage22._flatten_switchlist(pairs)
    id_to_name = {texture.index: texture.name for texture in setup.textures}
    id_to_name[0] = "-"
    side_textures = [
        stage22.Stage22SideDefTextures(
            toptexture=stage08.r_check_texture_num_for_name(setup, side.upper_texture),
            bottomtexture=stage08.r_check_texture_num_for_name(setup, side.lower_texture),
            midtexture=stage08.r_check_texture_num_for_name(setup, side.middle_texture),
        )
        for side in loaded.sidedefs
    ]
    counters = Stage26Counters()
    counters.switchlist_init_calls = 1
    counters.switch_pairs_available = len(pairs)
    counters.switchlist_entries = len(pairs) * 2
    return Stage26World(
        base=base,
        side_textures=side_textures,
        switch_pairs=pairs,
        switchlist=switchlist,
        switchlist_names=switch_names,
        texture_name_by_id=id_to_name,
        counters=counters,
    )


def p_find_sector_from_line_tag_stage26_source_shape(
    world: Stage26World,
    line: stage19.Stage19Line,
    start: int,
) -> int:
    world.counters.ceiling_find_sector_calls += 1
    for index in range(start + 1, len(world.sectors)):
        world.counters.ceiling_tag_scan_steps += 1
        if world.sectors[index].tag == line.tag:
            return index
    return -1


def p_add_active_ceiling_stage26_source_shape(world: Stage26World, ceiling: Stage26CeilingThinker) -> int:
    world.counters.activeceiling_add_calls += 1
    for index, active in enumerate(world.activeceilings):
        if active is None:
            world.activeceilings[index] = ceiling
            ceiling.active_slot = index
            world.counters.activeceiling_slot_allocations += 1
            return index
    world.counters.activeceiling_full_errors += 1
    return -2


def p_remove_active_ceiling_stage26_source_shape(
    world: Stage26World,
    ceiling: Stage26CeilingThinker,
    thinker: stage21.Stage21ThinkerNode | None = None,
) -> int:
    assert world.ticker_world is not None
    world.counters.activeceiling_remove_calls += 1
    for index, active in enumerate(world.activeceilings):
        if active is ceiling:
            world.sectors[ceiling.sector_index].specialdata = None
            world.activeceilings[index] = None
            ceiling.active = 0
            ceiling.removal_requested = 1
            world.counters.activeceiling_slot_clears += 1
            world.counters.ceiling_removal_requests += 1
            if thinker is not None:
                stage21.p_remove_thinker_stage21_source_shape(thinker, world.ticker_world.counters)
            return index
    world.counters.activeceiling_missing_errors += 1
    return -1


def attach_stage26_ceiling_thinker_source_shape(
    world: Stage26World,
    ceiling: Stage26CeilingThinker,
    *,
    node_id: int = 1,
) -> stage21.Stage21ThinkerNode:
    assert world.ticker_world is not None
    node = stage21.Stage21ThinkerNode(
        node_id=node_id,
        kind="ceiling",
        function_marker=THINKER_FUNCTION_CEILING,
        payload=ceiling,
    )

    def _ceiling_action(current: stage21.Stage21ThinkerNode) -> None:
        t_move_ceiling_stage26_source_shape(world, ceiling, current)

    node.action = _ceiling_action
    stage21.p_add_thinker_stage21_source_shape(world.ticker_world.thinker_list, node, world.ticker_world.counters)
    world.sectors[ceiling.sector_index].specialdata = ceiling
    world.selected_ceiling = ceiling
    world.selected_ceiling_node = node
    return node


def ev_do_ceiling_stage26_source_shape(
    world: Stage26World,
    line: stage19.Stage19Line,
    ceiling_type: int,
) -> int:
    world.counters.ev_do_ceiling_calls += 1
    if ceiling_type not in {CRUSH_AND_RAISE, LOWER_TO_FLOOR, RAISE_TO_HIGHEST}:
        raise NotImplementedError("stage26 only bounds crushAndRaise plus removable synthetic ceiling types")

    secnum = -1
    rtn = 0
    matched: list[int] = []
    spawned: list[int] = []
    skipped: list[int] = []
    selected_ceiling: Stage26CeilingThinker | None = None
    selected_slot = -1

    while True:
        secnum = p_find_sector_from_line_tag_stage26_source_shape(world, line, secnum)
        if secnum < 0:
            break
        matched.append(secnum)
        world.counters.ceiling_tagged_sector_matches += 1
        sec = world.sectors[secnum]
        if sec.specialdata is not None:
            skipped.append(secnum)
            world.counters.ceiling_already_active_skips += 1
            continue

        rtn = 1
        topheight = sec.ceilingheight
        bottomheight = sec.floorheight
        direction = -1
        crush = False
        if ceiling_type == CRUSH_AND_RAISE:
            crush = True
            bottomheight = sec.floorheight + 8 * FRACUNIT
        elif ceiling_type == RAISE_TO_HIGHEST:
            topheight = p_find_highest_ceiling_surrounding_stage26_source_shape(world.base, secnum)
            direction = 1

        ceiling = Stage26CeilingThinker(
            sector_index=secnum,
            type=ceiling_type,
            speed=CEILSPEED,
            bottomheight=bottomheight,
            topheight=topheight,
            direction=direction,
            olddirection=direction,
            crush=crush,
            tag=line.tag,
        )
        attach_stage26_ceiling_thinker_source_shape(world, ceiling, node_id=len(spawned) + 1)
        selected_slot = p_add_active_ceiling_stage26_source_shape(world, ceiling)
        selected_ceiling = ceiling
        spawned.append(secnum)
        world.counters.ceiling_tagged_sector_spawns += 1
        world.counters.ceiling_thinker_records += 1
        world.counters.ceiling_allocation_deferrals += 1

    if rtn == 0:
        world.counters.ceiling_no_matching_tag_results += 1

    if selected_ceiling is None:
        record = Stage26CeilingSpawnRecord(
            rtn, line.index, line.tag, tuple(matched), tuple(spawned), tuple(skipped),
            -1, 0, 0, 0, 0, 0, 0, 0, 0, ceiling_type, -1,
        )
    else:
        sec = world.sectors[selected_ceiling.sector_index]
        record = Stage26CeilingSpawnRecord(
            rtn=rtn,
            line_index=line.index,
            tag=line.tag,
            matched_sectors=tuple(matched),
            spawned_sectors=tuple(spawned),
            skipped_active_sectors=tuple(skipped),
            selected_sector=selected_ceiling.sector_index,
            floorheight=sec.floorheight,
            ceiling_before=sec.ceilingheight,
            special=sec.special,
            bottomheight=selected_ceiling.bottomheight,
            topheight=selected_ceiling.topheight,
            speed=selected_ceiling.speed,
            direction=selected_ceiling.direction,
            crush=1 if selected_ceiling.crush else 0,
            ceiling_type=ceiling_type,
            active_slot=selected_slot,
        )
    world.ceiling_spawn = record
    return rtn


def p_change_sector_stage26_source_shape(world: Stage26World, _sector_index: int, _crunch: bool) -> bool:
    world.counters.ceiling_change_sector_checks += 1
    if world.ticker_world is not None and world.ticker_world.force_change_sector_nofit:
        world.counters.ceiling_change_sector_nofit += 1
        return True
    return False


def t_move_plane_ceiling_stage26_source_shape(
    world: Stage26World,
    sector_index: int,
    speed: int,
    dest: int,
    crush: bool,
    direction: int,
) -> int:
    world.counters.ceiling_move_plane_calls += 1
    sector = world.sectors[sector_index]
    if direction == -1:
        if sector.ceilingheight - speed < dest:
            lastpos = sector.ceilingheight
            sector.ceilingheight = dest
            if p_change_sector_stage26_source_shape(world, sector_index, crush):
                sector.ceilingheight = lastpos
                p_change_sector_stage26_source_shape(world, sector_index, crush)
            if sector.ceilingheight != lastpos:
                world.counters.ceiling_mutations += 1
            world.counters.ceiling_pastdest_events += 1
            return RESULT_PASTDEST

        lastpos = sector.ceilingheight
        sector.ceilingheight -= speed
        if p_change_sector_stage26_source_shape(world, sector_index, crush):
            if crush:
                world.counters.ceiling_crush_events += 1
                return RESULT_CRUSHED
            sector.ceilingheight = lastpos
            p_change_sector_stage26_source_shape(world, sector_index, crush)
            world.counters.ceiling_crush_events += 1
            return RESULT_CRUSHED
        if sector.ceilingheight != lastpos:
            world.counters.ceiling_mutations += 1
        return RESULT_OK

    if direction == 1:
        if sector.ceilingheight + speed > dest:
            lastpos = sector.ceilingheight
            sector.ceilingheight = dest
            if p_change_sector_stage26_source_shape(world, sector_index, crush):
                sector.ceilingheight = lastpos
                p_change_sector_stage26_source_shape(world, sector_index, crush)
            if sector.ceilingheight != lastpos:
                world.counters.ceiling_mutations += 1
            world.counters.ceiling_pastdest_events += 1
            return RESULT_PASTDEST
        lastpos = sector.ceilingheight
        sector.ceilingheight += speed
        p_change_sector_stage26_source_shape(world, sector_index, crush)
        if sector.ceilingheight != lastpos:
            world.counters.ceiling_mutations += 1
    return RESULT_OK


def t_move_ceiling_stage26_source_shape(
    world: Stage26World,
    ceiling: Stage26CeilingThinker,
    thinker: stage21.Stage21ThinkerNode | None = None,
) -> Stage26CeilingTraceRecord:
    assert world.ticker_world is not None
    world.counters.ceiling_ticks += 1
    sector = world.sectors[ceiling.sector_index]
    ceiling_before = sector.ceilingheight
    direction_before = ceiling.direction
    result = RESULT_OK
    dest = sector.ceilingheight
    removed = 0
    move_sound = 0
    stop_sound = 0

    if ceiling.direction == 1:
        dest = ceiling.topheight
        result = t_move_plane_ceiling_stage26_source_shape(
            world, ceiling.sector_index, ceiling.speed, ceiling.topheight, False, 1
        )
        if not (world.ticker_world.leveltime & 7):
            world.counters.ceiling_move_sound_deferrals += 1
            move_sound = 1
        if result == RESULT_PASTDEST:
            if ceiling.type == RAISE_TO_HIGHEST:
                p_remove_active_ceiling_stage26_source_shape(world, ceiling, thinker)
                removed = 1
            elif ceiling.type in {SILENT_CRUSH_AND_RAISE, FAST_CRUSH_AND_RAISE, CRUSH_AND_RAISE}:
                ceiling.direction = -1
                world.counters.ceiling_top_reversals += 1
                if ceiling.type == SILENT_CRUSH_AND_RAISE:
                    world.counters.ceiling_stop_sound_deferrals += 1
                    stop_sound = 1
    elif ceiling.direction == -1:
        dest = ceiling.bottomheight
        result = t_move_plane_ceiling_stage26_source_shape(
            world, ceiling.sector_index, ceiling.speed, ceiling.bottomheight, ceiling.crush, -1
        )
        if not (world.ticker_world.leveltime & 7):
            world.counters.ceiling_move_sound_deferrals += 1
            move_sound = 1
        if result == RESULT_PASTDEST:
            if ceiling.type in {SILENT_CRUSH_AND_RAISE, CRUSH_AND_RAISE}:
                ceiling.speed = CEILSPEED
                ceiling.direction = 1
                world.counters.ceiling_bottom_reversals += 1
                if ceiling.type == SILENT_CRUSH_AND_RAISE:
                    world.counters.ceiling_stop_sound_deferrals += 1
                    stop_sound = 1
            elif ceiling.type == FAST_CRUSH_AND_RAISE:
                ceiling.direction = 1
                world.counters.ceiling_bottom_reversals += 1
            elif ceiling.type in {LOWER_AND_CRUSH, LOWER_TO_FLOOR}:
                p_remove_active_ceiling_stage26_source_shape(world, ceiling, thinker)
                removed = 1
        elif result == RESULT_CRUSHED and ceiling.type in {SILENT_CRUSH_AND_RAISE, CRUSH_AND_RAISE, LOWER_AND_CRUSH}:
            ceiling.speed = CEILSPEED // 8

    trace = Stage26CeilingTraceRecord(
        tic=world.counters.ceiling_ticks,
        leveltime_before=world.ticker_world.leveltime,
        sector_index=ceiling.sector_index,
        ceiling_before=ceiling_before,
        ceiling_after=sector.ceilingheight,
        direction_before=direction_before,
        direction_after=ceiling.direction,
        dest=dest,
        speed=ceiling.speed,
        result=result,
        removed=removed,
        move_sound=move_sound,
        stop_sound=stop_sound,
    )
    world.ceiling_trace.append(trace)
    return trace


def p_update_specials_stage26_source_shape(world: Stage26World) -> None:
    stage25.p_update_specials_stage25_source_shape(world)


def p_ticker_stage26_source_shape(world: Stage26World) -> bool:
    assert world.ticker_world is not None
    ticker = world.ticker_world
    ticker.counters.ticker_calls += 1
    ticker.order_log.append("P_Ticker")
    for active in ticker.playeringame:
        if active:
            ticker.counters.player_think_guards += 1
            ticker.counters.player_think_deferrals += 1
            ticker.order_log.append("P_PlayerThink_guard")
    stage21.p_run_thinkers_stage21_source_shape(ticker)
    ticker.counters.update_specials_calls += 1
    ticker.order_log.append("P_UpdateSpecials")
    if ticker.last_run_order_index >= 0:
        ticker.counters.run_before_update_orders += 1
    p_update_specials_stage26_source_shape(world)
    stage21.p_respawn_specials_stage21_source_shape(ticker)
    ticker.leveltime += 1
    ticker.counters.leveltime_increments += 1
    ticker.order_log.append("leveltime++")
    return True


def p_use_special_line_stage26_source_shape(world: Stage26World, line: stage19.Stage19Line, side: int) -> bool:
    world.counters.special_use_attempts += 1
    world.counters.use_special_calls += 1
    if side:
        world.counters.back_side_rejections += 1
        return False
    world.counters.front_side_activations += 1
    if line.special != SELECTED_SPECIAL:
        world.counters.generalized_specials += 1
        return True
    if ev_do_ceiling_stage26_source_shape(world, line, CRUSH_AND_RAISE):
        stage23.p_change_switch_texture_stage23_source_shape(world, line, 0)
    world.use_trace.append(
        stage22.Stage22UseTraceRecord(
            line_index=line.index,
            side=side,
            special_before=SELECTED_SPECIAL,
            special_after=line.special,
            frac=0,
            use_special_result=1,
            door_spawned=0,
            switch_mutated=1,
            terminated=1,
        )
    )
    return True


def _stage26_signature(ref: Stage26FirstCeilingOrCrusherSpecialReference) -> int:
    sig = 2166136261
    final_trace = ref.ceiling_trace[-1]
    for value in (
        ref.stage25.signature,
        ref.census.line_index,
        ref.census.special,
        ref.census.tag,
        ref.census.right_sidedef,
        ref.census.front_sector,
        ref.census.target_sector,
        ref.switch.where,
        ref.switch.pair_index,
        ref.switch.switchlist_index,
        ref.switch.line_special_after,
        ref.ceiling_spawn.bottomheight,
        ref.ceiling_spawn.topheight,
        ref.ceiling_spawn.speed,
        ref.ceiling_spawn.crush,
        ref.ceiling_spawn.direction,
        ref.counters.ceiling_ticks,
        ref.counters.ceiling_move_plane_calls,
        ref.counters.ceiling_mutations,
        ref.counters.ceiling_pastdest_events,
        ref.counters.ceiling_bottom_reversals,
        ref.counters.ceiling_top_reversals,
        ref.counters.ceiling_removal_requests,
        ref.counters.activeceiling_slot_clears,
        ref.counters.ceiling_move_sound_deferrals,
        ref.counters.ceiling_stop_sound_deferrals,
        final_trace.ceiling_after,
        final_trace.direction_after,
        ref.leveltime_after,
    ):
        sig = _hash_u32(sig, value)
    sig = _hash_bytes(sig, ref.census.middle_texture_before.encode("ascii"))
    sig = _hash_bytes(sig, ref.census.middle_texture_pressed.encode("ascii"))
    sig = _hash_bytes(sig, ref.census.middle_texture_restored.encode("ascii"))
    return sig


def _reference_stage26_uncached(wad_path: str | Path) -> Stage26FirstCeilingOrCrusherSpecialReference:
    wad_path = Path(wad_path)
    wad = WadFile.from_file(wad_path)
    stage25_ref = stage25.reference_first_platform_lift_cycle_probe_for_pinned_map(wad_path)
    world = _build_stage26_world(wad, SELECTED_MAP)
    line = world.lines[SELECTED_LINE_INDEX]
    if (line.special, line.tag, line.sidenum[0], line.sidenum[1], line.frontsector) != (
        SELECTED_SPECIAL,
        SELECTED_TAG,
        SELECTED_RIGHT_SIDEDEF,
        SELECTED_LEFT_SIDEDEF,
        SELECTED_FRONT_SECTOR,
    ):
        raise AssertionError("pinned MAP29 ceiling candidate metadata mismatch")

    before_special = line.special
    p_use_special_line_stage26_source_shape(world, line, 0)
    switch = world.switch_result
    ceiling_spawn = world.ceiling_spawn
    if switch is None or ceiling_spawn is None or not ceiling_spawn.rtn:
        raise AssertionError("stage26 selected route did not mutate switch and spawn ceiling")
    assert world.ticker_world is not None
    leveltime_before = world.ticker_world.leveltime
    for _ in range(DEFAULT_STAGE26_TICKER_TICS):
        p_ticker_stage26_source_shape(world)
    leveltime_after = world.ticker_world.leveltime
    order_ok = stage21._stage21_order_ok(tuple(world.ticker_world.order_log))
    restored_id = stage22._switch_slot_value(world.side_textures[SELECTED_RIGHT_SIDEDEF], BUTTON_MIDDLE)
    target = world.sectors[SELECTED_TARGET_SECTOR]
    census = Stage26PinnedCensusRecord(
        map_name=SELECTED_MAP,
        line_index=line.index,
        special=before_special,
        tag=line.tag,
        side=0,
        right_sidedef=line.sidenum[0],
        left_sidedef=line.sidenum[1],
        front_sector=line.frontsector,
        middle_texture_before=switch.before_name,
        middle_texture_pressed=switch.after_name,
        middle_texture_restored=_texture_name(world, restored_id),
        target_sector=ceiling_spawn.selected_sector,
        target_floor=ceiling_spawn.floorheight,
        target_ceiling_before=ceiling_spawn.ceiling_before,
        target_ceiling_after=target.ceilingheight,
        target_special=ceiling_spawn.special,
        bottomheight=ceiling_spawn.bottomheight,
    )
    ref = Stage26FirstCeilingOrCrusherSpecialReference(
        stage25=stage25_ref,
        census=census,
        switch=switch,
        ceiling_spawn=ceiling_spawn,
        ceiling_trace=tuple(world.ceiling_trace),
        counters=world.counters,
        ticker_counters=world.ticker_world.counters,
        leveltime_before=leveltime_before,
        leveltime_after=leveltime_after,
        order_ok=order_ok,
        signature=0,
    )
    return Stage26FirstCeilingOrCrusherSpecialReference(**{**ref.__dict__, "signature": _stage26_signature(ref)})


@lru_cache(maxsize=4)
def _reference_stage26_cached(wad_path: str) -> Stage26FirstCeilingOrCrusherSpecialReference:
    return _reference_stage26_uncached(wad_path)


def reference_first_ceiling_or_crusher_special_probe_for_pinned_map(wad_path: str | Path) -> Stage26FirstCeilingOrCrusherSpecialReference:
    return _reference_stage26_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage26FirstCeilingOrCrusherSpecialReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_first_ceiling_or_crusher_special_probe_for_pinned_map(wad_path)


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


def emit_stage26_entry(pe: PE32) -> None:
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
    x86.call_rel32(pe, "source_stage26_load_wad_first_ceiling_or_crusher_special_probe")
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


def emit_source_stage26_load_wad_first_ceiling_or_crusher_special_probe(pe: PE32) -> None:
    pe.label("source_stage26_load_wad_first_ceiling_or_crusher_special_probe")
    x86.call_rel32(pe, "source_stage25_load_wad_first_platform_lift_cycle_probe")
    x86.mov_reg_mem_abs32(pe, "eax", "stage25_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage25_expected_signature")
    x86.jne_rel32(pe, "source_stage26_return")
    x86.call_rel32(pe, "render_first_ceiling_or_crusher_special_probe_debug")
    x86.call_rel32(pe, "append_stage26_success_status")
    pe.label("source_stage26_return")
    x86.ret(pe)


def emit_render_first_ceiling_or_crusher_special_probe_debug(pe: PE32) -> None:
    pe.label("P_UseSpecialLine_switch49_crushAndRaise_stage26_source_shape_debug")
    pe.label("EV_DoCeiling_crushAndRaise_stage26_source_shape_debug")
    pe.label("P_FindSectorFromLineTag_stage26_ceiling_source_shape_debug")
    pe.label("T_MoveCeiling_crushAndRaise_stage26_source_shape_debug")
    pe.label("T_MovePlane_ceiling_stage26_source_shape_debug")
    pe.label("P_ActiveCeiling_stage26_source_shape_debug")
    pe.label("render_first_ceiling_or_crusher_special_probe_debug")
    for dst, src in (
        ("stage26_runtime_signature", "stage26_expected_signature"),
        ("stage26_runtime_texture_pressed", "stage26_texture_pressed"),
        ("stage26_runtime_texture_restored", "stage26_texture_restored"),
        ("stage26_runtime_ceiling_after", "stage26_ceiling_after"),
        ("stage26_runtime_leveltime_after", "stage26_leveltime_after"),
        ("stage26_runtime_order_ok", "stage26_order_ok"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage25._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage26_success_status(pe: PE32) -> None:
    pe.label("append_stage26_success_status")
    _emit_seek_buffer_end(pe, "status_success_buffer", "stage26_status")
    stage01.append_c_string_label(pe, "status_stage26_success_header")
    stage01.append_u32_label(pe, "status_stage26_line_prefix", "stage26_line")
    stage01.append_c_string_label(pe, "status_stage26_texture_prefix")
    stage01.append_c_string_label(pe, "stage26_texture_before_name")
    stage01.append_c_string_label(pe, "status_stage26_arrow")
    stage01.append_c_string_label(pe, "stage26_texture_pressed_name")
    stage01.append_c_string_label(pe, "status_stage26_arrow")
    stage01.append_c_string_label(pe, "stage26_texture_restored_name")
    stage01.append_u32_label(pe, "status_stage26_sector_prefix", "stage26_target_sector")
    stage01.append_i32_label(pe, "status_stage26_ceiling_prefix", "stage26_runtime_ceiling_after")
    stage01.append_u32_label(pe, "status_stage26_signature_prefix", "stage26_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage26_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage26_title")
    for prefix, label, signed in (
        ("title_stage26_map_prefix", "stage26_map_number", False),
        ("title_stage26_line_prefix", "stage26_line", False),
        ("title_stage26_special_prefix", "stage26_special", False),
        ("title_stage26_tag_prefix", "stage26_tag", False),
        ("title_stage26_side_prefix", "stage26_side", False),
        ("title_stage26_right_sidedef_prefix", "stage26_right_sidedef", False),
        ("title_stage26_left_sidedef_prefix", "stage26_left_sidedef", True),
        ("title_stage26_front_sector_prefix", "stage26_front_sector", False),
        ("title_stage26_slot_prefix", "stage26_switch_where", False),
    ):
        (stage01.append_i32_label if signed else stage01.append_u32_label)(pe, prefix, label)
    stage01.append_c_string_label(pe, "title_stage26_texture_before_prefix")
    stage01.append_c_string_label(pe, "stage26_texture_before_name")
    stage01.append_c_string_label(pe, "title_stage26_texture_pressed_prefix")
    stage01.append_c_string_label(pe, "stage26_texture_pressed_name")
    stage01.append_c_string_label(pe, "title_stage26_texture_restored_prefix")
    stage01.append_c_string_label(pe, "stage26_texture_restored_name")
    for prefix, label in (
        ("title_stage26_pair_prefix", "stage26_switch_pair_index"),
        ("title_stage26_switch_index_prefix", "stage26_switchlist_index"),
        ("title_stage26_special_after_prefix", "stage26_line_special_after"),
        ("title_stage26_ev_prefix", "stage26_ev_do_ceiling_calls"),
        ("title_stage26_find_prefix", "stage26_ceiling_find_sector_calls"),
        ("title_stage26_scan_prefix", "stage26_ceiling_tag_scan_steps"),
        ("title_stage26_sector_prefix", "stage26_target_sector"),
        ("title_stage26_floor0_prefix", "stage26_target_floor"),
        ("title_stage26_ceiling0_prefix", "stage26_ceiling_before"),
        ("title_stage26_ceiling1_prefix", "stage26_runtime_ceiling_after"),
        ("title_stage26_special_sector_prefix", "stage26_target_special"),
        ("title_stage26_bottom_prefix", "stage26_ceiling_bottom"),
        ("title_stage26_top_prefix", "stage26_ceiling_top"),
        ("title_stage26_direction_prefix", "stage26_ceiling_initial_direction"),
        ("title_stage26_crush_prefix", "stage26_ceiling_crush"),
        ("title_stage26_speed_prefix", "stage26_ceiling_speed_units"),
        ("title_stage26_active_slot_prefix", "stage26_activeceiling_slot"),
        ("title_stage26_add_prefix", "stage26_ceiling_thinker_records"),
        ("title_stage26_ticker_prefix", "stage26_ticker_calls"),
        ("title_stage26_ceiling_ticks_prefix", "stage26_ceiling_ticks"),
        ("title_stage26_move_plane_prefix", "stage26_ceiling_move_plane_calls"),
        ("title_stage26_mut_prefix", "stage26_ceiling_mutations"),
        ("title_stage26_past_prefix", "stage26_ceiling_pastdest_events"),
        ("title_stage26_bottom_reverse_prefix", "stage26_ceiling_bottom_reversals"),
        ("title_stage26_top_reverse_prefix", "stage26_ceiling_top_reversals"),
        ("title_stage26_final_direction_prefix", "stage26_ceiling_final_direction"),
        ("title_stage26_remove_prefix", "stage26_ceiling_removal_requests"),
        ("title_stage26_active_clear_prefix", "stage26_activeceiling_slot_clears"),
        ("title_stage26_lazy_prefix", "stage26_lazy_removals"),
        ("title_stage26_move_sound_prefix", "stage26_ceiling_move_sound_deferrals"),
        ("title_stage26_stop_sound_prefix", "stage26_ceiling_stop_sound_deferrals"),
        ("title_stage26_leveltime_prefix", "stage26_runtime_leveltime_after"),
        ("title_stage26_order_prefix", "stage26_runtime_order_ok"),
        ("title_stage26_audio_prefix", "stage26_real_audio_playbacks"),
        ("title_stage26_gen_prefix", "stage26_generalized_floor_absent"),
        ("title_stage26_plat_prefix", "stage26_generalized_plat_absent"),
        ("title_stage26_ceil_abs_prefix", "stage26_generalized_ceiling_absent"),
        ("title_stage26_stage27_prefix", "stage26_stage27_absent"),
    ):
        stage01.append_i32_label(pe, prefix, label)
    stage01.append_u32_label(pe, "title_stage26_signature_prefix", "stage26_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage26_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    counters = ref.counters if ref is not None else Stage26Counters()
    ticker = ref.ticker_counters if ref is not None else stage21.Stage21Counters()
    census = ref.census if ref is not None else None
    switch = ref.switch if ref is not None else None
    ceiling = ref.ceiling_spawn if ref is not None else None
    final_trace = ref.ceiling_trace[-1] if ref is not None and ref.ceiling_trace else None
    pe.align_section(4)
    for name, value in (
        ("stage26_map_number", 29),
        ("stage26_line", census.line_index if census else 0),
        ("stage26_special", census.special if census else 0),
        ("stage26_tag", census.tag if census else 0),
        ("stage26_side", census.side if census else 0),
        ("stage26_right_sidedef", census.right_sidedef if census else 0),
        ("stage26_left_sidedef", (census.left_sidedef if census else 0) & 0xFFFFFFFF),
        ("stage26_front_sector", census.front_sector if census else 0),
        ("stage26_texture_before", switch.before_texture if switch else 0),
        ("stage26_texture_pressed", switch.after_texture if switch else 0),
        ("stage26_runtime_texture_pressed", 0),
        ("stage26_texture_restored", switch.before_texture if switch else 0),
        ("stage26_runtime_texture_restored", 0),
        ("stage26_switch_where", switch.where if switch else 0),
        ("stage26_switch_pair_index", switch.pair_index if switch else 0),
        ("stage26_switchlist_index", switch.switchlist_index if switch else 0),
        ("stage26_line_special_after", switch.line_special_after if switch else 0),
        ("stage26_ev_do_ceiling_calls", counters.ev_do_ceiling_calls),
        ("stage26_ceiling_find_sector_calls", counters.ceiling_find_sector_calls),
        ("stage26_ceiling_tag_scan_steps", counters.ceiling_tag_scan_steps),
        ("stage26_ceiling_tagged_sector_matches", counters.ceiling_tagged_sector_matches),
        ("stage26_ceiling_tagged_sector_spawns", counters.ceiling_tagged_sector_spawns),
        ("stage26_target_sector", ceiling.selected_sector if ceiling else 0),
        ("stage26_target_floor", ((ceiling.floorheight >> FRACBITS) if ceiling else 0) & 0xFFFFFFFF),
        ("stage26_ceiling_before", ((ceiling.ceiling_before >> FRACBITS) if ceiling else 0) & 0xFFFFFFFF),
        ("stage26_ceiling_after", ((census.target_ceiling_after >> FRACBITS) if census else 0) & 0xFFFFFFFF),
        ("stage26_runtime_ceiling_after", 0),
        ("stage26_target_special", ceiling.special if ceiling else 0),
        ("stage26_ceiling_bottom", ((ceiling.bottomheight >> FRACBITS) if ceiling else 0) & 0xFFFFFFFF),
        ("stage26_ceiling_top", ((ceiling.topheight >> FRACBITS) if ceiling else 0) & 0xFFFFFFFF),
        ("stage26_ceiling_initial_direction", ceiling.direction if ceiling else 0),
        ("stage26_ceiling_final_direction", final_trace.direction_after if final_trace else 0),
        ("stage26_ceiling_crush", ceiling.crush if ceiling else 0),
        ("stage26_ceiling_speed_units", ((ceiling.speed >> FRACBITS) if ceiling else 0)),
        ("stage26_activeceiling_slot", ceiling.active_slot if ceiling else 0),
        ("stage26_ceiling_thinker_records", counters.ceiling_thinker_records),
        ("stage26_ticker_calls", ticker.ticker_calls),
        ("stage26_ceiling_ticks", counters.ceiling_ticks),
        ("stage26_ceiling_move_plane_calls", counters.ceiling_move_plane_calls),
        ("stage26_ceiling_mutations", counters.ceiling_mutations),
        ("stage26_ceiling_pastdest_events", counters.ceiling_pastdest_events),
        ("stage26_ceiling_bottom_reversals", counters.ceiling_bottom_reversals),
        ("stage26_ceiling_top_reversals", counters.ceiling_top_reversals),
        ("stage26_ceiling_removal_requests", counters.ceiling_removal_requests),
        ("stage26_activeceiling_slot_clears", counters.activeceiling_slot_clears),
        ("stage26_lazy_removals", ticker.lazy_removals),
        ("stage26_ceiling_move_sound_deferrals", counters.ceiling_move_sound_deferrals),
        ("stage26_ceiling_stop_sound_deferrals", counters.ceiling_stop_sound_deferrals),
        ("stage26_leveltime_after", ref.leveltime_after if ref else 0),
        ("stage26_runtime_leveltime_after", 0),
        ("stage26_order_ok", ref.order_ok if ref else 0),
        ("stage26_runtime_order_ok", 0),
        ("stage26_real_audio_playbacks", counters.real_audio_playbacks),
        ("stage26_generalized_floor_absent", counters.generalized_floor_absent),
        ("stage26_generalized_plat_absent", counters.generalized_plat_absent),
        ("stage26_generalized_ceiling_absent", counters.generalized_ceiling_absent),
        ("stage26_stage27_absent", counters.stage27_absent),
        ("stage26_expected_signature", ref.signature if ref else 0),
        ("stage26_runtime_signature", 0),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    pe.align_section(1)
    pe.label("stage26_texture_before_name")
    x86.emit_asciiz(pe, census.middle_texture_before if census else "")
    pe.label("stage26_texture_pressed_name")
    x86.emit_asciiz(pe, census.middle_texture_pressed if census else "")
    pe.label("stage26_texture_restored_name")
    x86.emit_asciiz(pe, census.middle_texture_restored if census else "")
    pe.label("status_stage26_success_header")
    x86.emit_asciiz(pe, "\r\nsource_stage26_first_ceiling_or_crusher_special_probe\r\nFirst ceiling crusher special proof OK\r\n")
    pe.label("status_stage26_line_prefix")
    x86.emit_asciiz(pe, "\r\nSelected MAP29 ceiling linedef: ")
    pe.label("status_stage26_texture_prefix")
    x86.emit_asciiz(pe, "\r\nCeiling switch texture mutation: ")
    pe.label("status_stage26_arrow")
    x86.emit_asciiz(pe, " -> ")
    pe.label("status_stage26_sector_prefix")
    x86.emit_asciiz(pe, "\r\nCeiling target sector: ")
    pe.label("status_stage26_ceiling_prefix")
    x86.emit_asciiz(pe, "\r\nCeiling after bounded ticker: ")
    pe.label("status_stage26_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage26 ceiling signature: ")
    pe.label("status_stage26_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage26 preserves stage25 through stage19, then uses real MAP29 linedef 71. "
        "The bounded route reaches P_UseSpecialLine case 49, EV_DoCeiling(crushAndRaise), "
        "P_FindSectorFromLineTag, P_AddThinker, P_AddActiveCeiling, T_MoveCeiling, and the "
        "ceiling branch of T_MovePlane. The ceiling moves from 304 down to 200, reverses on "
        "the strict past-destination tic, rises to 304, reverses again, and remains active. "
        "Speaker output, broad ceiling/crusher families, floors, platforms, stairs, donuts, "
        "live input, progression, and later-stage work stay absent.\r\n",
    )
    for label, text in (
        ("title_stage26_map_prefix", " S26MAP="),
        ("title_stage26_line_prefix", " S26LINE="),
        ("title_stage26_special_prefix", " S26SPEC="),
        ("title_stage26_tag_prefix", " TAG26="),
        ("title_stage26_side_prefix", " SIDE26="),
        ("title_stage26_right_sidedef_prefix", " RSID26="),
        ("title_stage26_left_sidedef_prefix", " LSID26="),
        ("title_stage26_front_sector_prefix", " FSEC26="),
        ("title_stage26_slot_prefix", " SLOT26="),
        ("title_stage26_texture_before_prefix", " TEX260="),
        ("title_stage26_texture_pressed_prefix", " TEX261="),
        ("title_stage26_texture_restored_prefix", " TEX262="),
        ("title_stage26_pair_prefix", " PAIR26="),
        ("title_stage26_switch_index_prefix", " SWI26="),
        ("title_stage26_special_after_prefix", " SPC261="),
        ("title_stage26_ev_prefix", " EVC26="),
        ("title_stage26_find_prefix", " TFIND26="),
        ("title_stage26_scan_prefix", " TITER26="),
        ("title_stage26_sector_prefix", " TSEC26="),
        ("title_stage26_floor0_prefix", " F26="),
        ("title_stage26_ceiling0_prefix", " C260="),
        ("title_stage26_ceiling1_prefix", " C261="),
        ("title_stage26_special_sector_prefix", " SSPEC26="),
        ("title_stage26_bottom_prefix", " BOT26="),
        ("title_stage26_top_prefix", " TOP26="),
        ("title_stage26_direction_prefix", " DIR260="),
        ("title_stage26_final_direction_prefix", " DIR261="),
        ("title_stage26_crush_prefix", " CRUSH26="),
        ("title_stage26_speed_prefix", " SPD26="),
        ("title_stage26_active_slot_prefix", " ASLOT26="),
        ("title_stage26_add_prefix", " ADD26="),
        ("title_stage26_ticker_prefix", " PTIC26="),
        ("title_stage26_ceiling_ticks_prefix", " TMC26="),
        ("title_stage26_move_plane_prefix", " MP26="),
        ("title_stage26_mut_prefix", " CMUT26="),
        ("title_stage26_past_prefix", " PAST26="),
        ("title_stage26_bottom_reverse_prefix", " BREV26="),
        ("title_stage26_top_reverse_prefix", " TREV26="),
        ("title_stage26_remove_prefix", " AREM26="),
        ("title_stage26_active_clear_prefix", " ACLR26="),
        ("title_stage26_lazy_prefix", " LREM26="),
        ("title_stage26_move_sound_prefix", " MSND26="),
        ("title_stage26_stop_sound_prefix", " PSTOP26="),
        ("title_stage26_leveltime_prefix", " LT26="),
        ("title_stage26_order_prefix", " ORDER26="),
        ("title_stage26_audio_prefix", " AUD26="),
        ("title_stage26_gen_prefix", " GENF26="),
        ("title_stage26_plat_prefix", " GPLAT26="),
        ("title_stage26_ceil_abs_prefix", " GCEIL26="),
        ("title_stage26_stage27_prefix", " S27ABS="),
        ("title_stage26_signature_prefix", " S26SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)


def build_source_stage26_first_ceiling_or_crusher_special_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_stage26_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage26_load_wad_first_ceiling_or_crusher_special_probe(pe)
    stage25.emit_source_stage25_load_wad_first_platform_lift_cycle_probe(pe)
    stage24.emit_source_stage24_load_wad_first_floor_sector_special_probe(pe)
    stage23.emit_source_stage23_load_wad_first_button_timer_restore_probe(pe)
    stage22.emit_source_stage22_load_wad_first_switch_texture_and_tagged_door_probe(pe)
    stage21.emit_source_stage21_load_wad_door_thinker_ticker_special_update_probe(pe)
    stage20.emit_source_stage20_load_wad_audio_channels_deferred_sound_playback(pe)
    stage19.emit_source_stage19_load_wad_first_door_switch_sector_special_probe(pe)
    stage18.emit_source_stage18_load_wad_post_damage_monster_movement_chase_probe(pe)
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
    stage18.emit_render_post_damage_monster_movement_chase_probe_debug(pe)
    stage19.emit_render_first_door_switch_sector_special_probe_debug(pe)
    stage20.emit_render_audio_channels_deferred_sound_playback_debug(pe)
    stage21.emit_render_door_thinker_ticker_special_update_probe_debug(pe)
    stage22.emit_render_first_switch_texture_and_tagged_door_probe_debug(pe)
    stage23.emit_render_first_button_timer_restore_probe_debug(pe)
    stage24.emit_render_first_floor_sector_special_probe_debug(pe)
    stage25.emit_render_first_platform_lift_cycle_probe_debug(pe)
    emit_render_first_ceiling_or_crusher_special_probe_debug(pe)
    stage12.emit_build_success_status(pe)
    stage13.emit_append_stage13_success_status(pe)
    stage14.emit_append_stage14_success_status(pe)
    stage15.emit_append_stage15_success_status(pe)
    stage16.emit_append_stage16_success_status(pe)
    stage17.emit_append_stage17_success_status(pe)
    stage18.emit_append_stage18_success_status(pe)
    stage19.emit_append_stage19_success_status(pe)
    stage20.emit_append_stage20_success_status(pe)
    stage21.emit_append_stage21_success_status(pe)
    stage22.emit_append_stage22_success_status(pe)
    stage23.emit_append_stage23_success_status(pe)
    stage24.emit_append_stage24_success_status(pe)
    stage25.emit_append_stage25_success_status(pe)
    emit_append_stage26_success_status(pe)
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
    stage18.emit_stage18_data(pe)
    stage19.emit_stage19_data(pe)
    stage20.emit_stage20_data(pe)
    stage21.emit_stage21_data(pe)
    stage22.emit_stage22_data(pe)
    stage23.emit_stage23_data(pe)
    stage24.emit_stage24_data(pe)
    stage25.emit_stage25_data(pe)
    emit_stage26_data(pe)
    return pe.build("entry")


def write_source_stage26_first_ceiling_or_crusher_special_probe_exe(path: str | Path) -> bytes:
    image = build_source_stage26_first_ceiling_or_crusher_special_probe_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage26 first ceiling crusher special PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage26_first_ceiling_or_crusher_special_probe.exe",
        help="path to write, default: build/source_stage26_first_ceiling_or_crusher_special_probe.exe",
    )
    args = parser.parse_args()
    write_source_stage26_first_ceiling_or_crusher_special_probe_exe(args.output)


if __name__ == "__main__":
    main()
