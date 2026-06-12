from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage24_first_floor_sector_special_probe as stage24
from tools import x86
from tools.map_loader import NO_SIDEDEF, load_map
from tools.pe32 import PE32
from tools.wad import WadFile


stage01 = stage24.stage01
stage02 = stage24.stage02
stage03 = stage24.stage03
stage04 = stage24.stage04
stage07 = stage24.stage07
stage08 = stage24.stage08
stage10 = stage24.stage10
stage11 = stage24.stage11
stage12 = stage24.stage12
stage13 = stage24.stage13
stage14 = stage24.stage14
stage15 = stage24.stage15
stage16 = stage24.stage16
stage17 = stage24.stage17
stage18 = stage24.stage18
stage19 = stage24.stage19
stage20 = stage24.stage20
stage21 = stage24.stage21
stage22 = stage24.stage22
stage23 = stage24.stage23


FRAMEBUFFER_WIDTH = stage24.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage24.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage24.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage24.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage24.WINDOW_WIDTH
WINDOW_HEIGHT = stage24.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage25FirstPlatformLiftCycleProbe"
WINDOW_TITLE = "Inference Doom S25 Platform Lift Cycle"
WAD_PATH = stage24.WAD_PATH

FRACBITS = stage24.FRACBITS
FRACUNIT = stage24.FRACUNIT
FNV_PRIME = stage24.FNV_PRIME
PLATSPEED = FRACUNIT
TICRATE = stage21.TICRATE
PLATWAIT = 3
MAXPLATS = 30
BUTTONTIME = stage24.BUTTONTIME
DOWN_WAIT_UP_STAY = 1
DEFAULT_STAGE25_TICKER_TICS = 136

SELECTED_MAP = "MAP12"
SELECTED_LINE_INDEX = 2304
SELECTED_SPECIAL = 62
SELECTED_TAG = 26
SELECTED_RIGHT_SIDEDEF = 3005
SELECTED_LEFT_SIDEDEF = 3004
SELECTED_FRONT_SECTOR = 228
SELECTED_TARGET_SECTOR = 77

BUTTON_BOTTOM = stage22.BUTTON_BOTTOM
BUTTON_MIDDLE = stage24.BUTTON_MIDDLE
RESULT_OK = stage21.RESULT_OK
RESULT_CRUSHED = stage21.RESULT_CRUSHED
RESULT_PASTDEST = stage21.RESULT_PASTDEST
THINKER_FUNCTION_PLAT = 3
PLAT_UP = 0
PLAT_DOWN = 1
PLAT_WAITING = 2
PLAT_IN_STASIS = 3

SOURCE_TRACE = stage24.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_switch.c",
        "P_UseSpecialLine case 62 reusable downWaitUpStay platform button path",
        "P_UseSpecialLine_button62_downWaitUpStay_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_plats.c",
        "EV_DoPlat downWaitUpStay selected tagged platform thinker setup",
        "EV_DoPlat_downWaitUpStay_stage25_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_spec.c",
        "P_FindSectorFromLineTag selected MAP12 tag 26 traversal",
        "P_FindSectorFromLineTag_stage25_plat_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_spec.c",
        "P_FindLowestFloorSurrounding selected sector 77 target lookup",
        "P_FindLowestFloorSurrounding_stage25_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_plats.c",
        "T_PlatRaise selected down/wait/up/stay transitions and pstart/pstop boundaries",
        "T_PlatRaise_downWaitUpStay_stage25_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_floor.c",
        "T_MovePlane floor branch platform down/up movement and strict clamp",
        "T_MovePlane_plat_floor_stage25_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_plats.c",
        "P_AddActivePlat/P_RemoveActivePlat selected activeplats slot lifecycle",
        "P_ActivePlat_stage25_source_shape_debug",
    ),
)


@dataclass
class Stage25Counters(stage24.Stage24Counters):
    ev_do_plat_calls: int = 0
    plat_find_sector_calls: int = 0
    plat_tag_scan_steps: int = 0
    plat_tagged_sector_matches: int = 0
    plat_tagged_sector_spawns: int = 0
    plat_already_active_skips: int = 0
    plat_no_matching_tag_results: int = 0
    plat_thinker_records: int = 0
    plat_allocation_deferrals: int = 0
    activeplat_add_calls: int = 0
    activeplat_slot_allocations: int = 0
    activeplat_full_errors: int = 0
    activeplat_remove_calls: int = 0
    activeplat_slot_clears: int = 0
    activeplat_missing_errors: int = 0
    plat_ticks: int = 0
    plat_move_plane_calls: int = 0
    plat_mutations: int = 0
    plat_pastdest_events: int = 0
    plat_change_sector_checks: int = 0
    plat_change_sector_nofit: int = 0
    plat_crush_events: int = 0
    plat_wait_transitions: int = 0
    plat_wait_countdowns: int = 0
    plat_up_restarts: int = 0
    plat_down_restarts: int = 0
    plat_removal_requests: int = 0
    plat_start_sound_deferrals: int = 0
    plat_stop_sound_deferrals: int = 0
    unsupported_plat_type_absent: int = 1
    generalized_plat_absent: int = 1
    generalized_floor_absent: int = 1
    generalized_ceiling_absent: int = 1
    stage26_absent: int = 1


@dataclass
class Stage25PlatThinker:
    sector_index: int
    type: int
    speed: int
    low: int
    high: int
    wait: int
    count: int
    status: int
    oldstatus: int
    crush: bool
    tag: int
    active: int = 1
    removal_requested: int = 0
    active_slot: int = -1


@dataclass(frozen=True)
class Stage25PlatSpawnRecord:
    rtn: int
    line_index: int
    tag: int
    matched_sectors: tuple[int, ...]
    spawned_sectors: tuple[int, ...]
    skipped_active_sectors: tuple[int, ...]
    selected_sector: int
    floor_before: int
    ceilingheight: int
    special: int
    surrounding_lowest_floor: int
    low: int
    high: int
    speed: int
    wait: int
    status: int
    plat_type: int
    active_slot: int


@dataclass(frozen=True)
class Stage25PlatTraceRecord:
    tic: int
    leveltime_before: int
    sector_index: int
    floor_before: int
    floor_after: int
    status_before: int
    status_after: int
    count_before: int
    count_after: int
    dest: int
    speed: int
    result: int
    removed: int
    start_sound: int
    stop_sound: int


@dataclass(frozen=True)
class Stage25PinnedCensusRecord:
    map_name: str
    line_index: int
    special: int
    tag: int
    side: int
    right_sidedef: int
    left_sidedef: int
    front_sector: int
    lower_texture_before: str
    lower_texture_pressed: str
    lower_texture_restored: str
    target_sector: int
    target_floor_before: int
    target_floor_after: int
    target_ceiling: int
    target_special: int
    surrounding_lowest_floor: int


@dataclass
class Stage25World(stage24.Stage24World):
    counters: Stage25Counters = field(default_factory=Stage25Counters)
    activeplats: list[Stage25PlatThinker | None] = field(default_factory=lambda: [None for _ in range(MAXPLATS)])
    selected_plat: Stage25PlatThinker | None = None
    selected_plat_node: stage21.Stage21ThinkerNode | None = None
    plat_spawn: Stage25PlatSpawnRecord | None = None
    plat_trace: list[Stage25PlatTraceRecord] = field(default_factory=list)


@dataclass(frozen=True)
class Stage25FirstPlatformLiftCycleReference:
    stage24: stage24.Stage24FirstFloorSectorSpecialReference
    census: Stage25PinnedCensusRecord
    switch: stage22.Stage22SwitchTextureResult
    plat_spawn: Stage25PlatSpawnRecord
    button_slot: int
    button_timer_start: int
    button_timer_end: int
    duplicate_guard_result: int
    plat_trace: tuple[Stage25PlatTraceRecord, ...]
    counters: Stage25Counters
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


def p_find_lowest_floor_surrounding_stage25_source_shape(
    world: stage19.Stage19World,
    sector_index: int,
) -> int:
    floor = world.sectors[sector_index].floorheight
    for line_index in world.sector_lines.get(sector_index, []):
        line = world.lines[line_index]
        other = stage19.get_next_sector_stage19_source_shape(world, line, sector_index)
        if other is None:
            continue
        if world.sectors[other].floorheight < floor:
            floor = world.sectors[other].floorheight
    return floor


def _build_stage25_world(wad: WadFile, map_name: str) -> Stage25World:
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
    counters = Stage25Counters()
    counters.switchlist_init_calls = 1
    counters.switch_pairs_available = len(pairs)
    counters.switchlist_entries = len(pairs) * 2
    return Stage25World(
        base=base,
        side_textures=side_textures,
        switch_pairs=pairs,
        switchlist=switchlist,
        switchlist_names=switch_names,
        texture_name_by_id=id_to_name,
        counters=counters,
    )


def p_find_sector_from_line_tag_stage25_source_shape(
    world: Stage25World,
    line: stage19.Stage19Line,
    start: int,
) -> int:
    world.counters.plat_find_sector_calls += 1
    for index in range(start + 1, len(world.sectors)):
        world.counters.plat_tag_scan_steps += 1
        if world.sectors[index].tag == line.tag:
            return index
    return -1


def p_add_active_plat_stage25_source_shape(world: Stage25World, plat: Stage25PlatThinker) -> int:
    world.counters.activeplat_add_calls += 1
    for index, active in enumerate(world.activeplats):
        if active is None:
            world.activeplats[index] = plat
            plat.active_slot = index
            world.counters.activeplat_slot_allocations += 1
            return index
    world.counters.activeplat_full_errors += 1
    return -2


def p_remove_active_plat_stage25_source_shape(
    world: Stage25World,
    plat: Stage25PlatThinker,
    thinker: stage21.Stage21ThinkerNode | None = None,
) -> int:
    assert world.ticker_world is not None
    world.counters.activeplat_remove_calls += 1
    for index, active in enumerate(world.activeplats):
        if active is plat:
            world.sectors[plat.sector_index].specialdata = None
            world.activeplats[index] = None
            plat.active = 0
            plat.removal_requested = 1
            world.counters.activeplat_slot_clears += 1
            world.counters.plat_removal_requests += 1
            if thinker is not None:
                stage21.p_remove_thinker_stage21_source_shape(thinker, world.ticker_world.counters)
            return index
    world.counters.activeplat_missing_errors += 1
    return -1


def attach_stage25_plat_thinker_source_shape(
    world: Stage25World,
    plat: Stage25PlatThinker,
    *,
    node_id: int = 1,
) -> stage21.Stage21ThinkerNode:
    assert world.ticker_world is not None
    node = stage21.Stage21ThinkerNode(
        node_id=node_id,
        kind="plat",
        function_marker=THINKER_FUNCTION_PLAT,
        payload=plat,
    )

    def _plat_action(current: stage21.Stage21ThinkerNode) -> None:
        t_plat_raise_stage25_source_shape(world, plat, current)

    node.action = _plat_action
    stage21.p_add_thinker_stage21_source_shape(world.ticker_world.thinker_list, node, world.ticker_world.counters)
    world.sectors[plat.sector_index].specialdata = plat
    world.selected_plat = plat
    world.selected_plat_node = node
    return node


def ev_do_plat_stage25_source_shape(
    world: Stage25World,
    line: stage19.Stage19Line,
    plat_type: int,
    amount: int = 1,
) -> int:
    del amount
    world.counters.ev_do_plat_calls += 1
    if plat_type != DOWN_WAIT_UP_STAY:
        raise NotImplementedError("stage25 only bounds downWaitUpStay")

    secnum = -1
    rtn = 0
    matched: list[int] = []
    spawned: list[int] = []
    skipped: list[int] = []
    selected_plat: Stage25PlatThinker | None = None
    selected_lowest = 0
    selected_slot = -1

    while True:
        secnum = p_find_sector_from_line_tag_stage25_source_shape(world, line, secnum)
        if secnum < 0:
            break
        matched.append(secnum)
        world.counters.plat_tagged_sector_matches += 1
        sec = world.sectors[secnum]
        if sec.specialdata is not None:
            skipped.append(secnum)
            world.counters.plat_already_active_skips += 1
            continue

        rtn = 1
        selected_lowest = p_find_lowest_floor_surrounding_stage25_source_shape(world.base, secnum)
        if selected_lowest > sec.floorheight:
            selected_lowest = sec.floorheight
        plat = Stage25PlatThinker(
            sector_index=secnum,
            type=plat_type,
            speed=PLATSPEED * 4,
            low=selected_lowest,
            high=sec.floorheight,
            wait=TICRATE * PLATWAIT,
            count=0,
            status=PLAT_DOWN,
            oldstatus=PLAT_DOWN,
            crush=False,
            tag=line.tag,
        )
        attach_stage25_plat_thinker_source_shape(world, plat, node_id=len(spawned) + 1)
        selected_slot = p_add_active_plat_stage25_source_shape(world, plat)
        selected_plat = plat
        spawned.append(secnum)
        world.counters.plat_tagged_sector_spawns += 1
        world.counters.plat_thinker_records += 1
        world.counters.plat_allocation_deferrals += 1
        world.counters.plat_start_sound_deferrals += 1

    if rtn == 0:
        world.counters.plat_no_matching_tag_results += 1

    if selected_plat is None:
        record = Stage25PlatSpawnRecord(rtn, line.index, line.tag, tuple(matched), tuple(spawned), tuple(skipped), -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, plat_type, -1)
    else:
        sec = world.sectors[selected_plat.sector_index]
        record = Stage25PlatSpawnRecord(
            rtn=rtn,
            line_index=line.index,
            tag=line.tag,
            matched_sectors=tuple(matched),
            spawned_sectors=tuple(spawned),
            skipped_active_sectors=tuple(skipped),
            selected_sector=selected_plat.sector_index,
            floor_before=sec.floorheight,
            ceilingheight=sec.ceilingheight,
            special=sec.special,
            surrounding_lowest_floor=selected_lowest,
            low=selected_plat.low,
            high=selected_plat.high,
            speed=selected_plat.speed,
            wait=selected_plat.wait,
            status=selected_plat.status,
            plat_type=plat_type,
            active_slot=selected_slot,
        )
    world.plat_spawn = record
    return rtn


def p_change_sector_stage25_source_shape(world: Stage25World, _sector_index: int, _crunch: bool) -> bool:
    world.counters.plat_change_sector_checks += 1
    if world.ticker_world is not None and world.ticker_world.force_change_sector_nofit:
        world.counters.plat_change_sector_nofit += 1
        return True
    return False


def t_move_plane_plat_floor_stage25_source_shape(
    world: Stage25World,
    sector_index: int,
    speed: int,
    dest: int,
    crush: bool,
    direction: int,
) -> int:
    world.counters.plat_move_plane_calls += 1
    sector = world.sectors[sector_index]
    if direction == -1:
        if sector.floorheight - speed < dest:
            lastpos = sector.floorheight
            sector.floorheight = dest
            if p_change_sector_stage25_source_shape(world, sector_index, crush):
                sector.floorheight = lastpos
                p_change_sector_stage25_source_shape(world, sector_index, crush)
            if sector.floorheight != lastpos:
                world.counters.plat_mutations += 1
            world.counters.plat_pastdest_events += 1
            return RESULT_PASTDEST

        lastpos = sector.floorheight
        sector.floorheight -= speed
        if p_change_sector_stage25_source_shape(world, sector_index, crush):
            sector.floorheight = lastpos
            p_change_sector_stage25_source_shape(world, sector_index, crush)
            world.counters.plat_crush_events += 1
            return RESULT_CRUSHED
        if sector.floorheight != lastpos:
            world.counters.plat_mutations += 1
        return RESULT_OK

    if direction == 1:
        if sector.floorheight + speed > dest:
            lastpos = sector.floorheight
            sector.floorheight = dest
            if p_change_sector_stage25_source_shape(world, sector_index, crush):
                sector.floorheight = lastpos
                p_change_sector_stage25_source_shape(world, sector_index, crush)
            if sector.floorheight != lastpos:
                world.counters.plat_mutations += 1
            world.counters.plat_pastdest_events += 1
            return RESULT_PASTDEST
        lastpos = sector.floorheight
        sector.floorheight += speed
        if p_change_sector_stage25_source_shape(world, sector_index, crush):
            if crush:
                world.counters.plat_crush_events += 1
                return RESULT_CRUSHED
            sector.floorheight = lastpos
            p_change_sector_stage25_source_shape(world, sector_index, crush)
            world.counters.plat_crush_events += 1
            return RESULT_CRUSHED
        if sector.floorheight != lastpos:
            world.counters.plat_mutations += 1
    return RESULT_OK


def t_plat_raise_stage25_source_shape(
    world: Stage25World,
    plat: Stage25PlatThinker,
    thinker: stage21.Stage21ThinkerNode | None = None,
) -> Stage25PlatTraceRecord:
    assert world.ticker_world is not None
    world.counters.plat_ticks += 1
    sector = world.sectors[plat.sector_index]
    floor_before = sector.floorheight
    status_before = plat.status
    count_before = plat.count
    result = RESULT_OK
    dest = sector.floorheight
    removed = 0
    start_sound = 0
    stop_sound = 0

    if plat.status == PLAT_UP:
        dest = plat.high
        result = t_move_plane_plat_floor_stage25_source_shape(world, plat.sector_index, plat.speed, plat.high, plat.crush, 1)
        if result == RESULT_CRUSHED and not plat.crush:
            plat.count = plat.wait
            plat.status = PLAT_DOWN
            world.counters.plat_down_restarts += 1
            world.counters.plat_start_sound_deferrals += 1
            start_sound = 1
        elif result == RESULT_PASTDEST:
            plat.count = plat.wait
            plat.status = PLAT_WAITING
            world.counters.plat_wait_transitions += 1
            world.counters.plat_stop_sound_deferrals += 1
            stop_sound = 1
            if plat.type == DOWN_WAIT_UP_STAY:
                p_remove_active_plat_stage25_source_shape(world, plat, thinker)
                removed = 1
    elif plat.status == PLAT_DOWN:
        dest = plat.low
        result = t_move_plane_plat_floor_stage25_source_shape(world, plat.sector_index, plat.speed, plat.low, False, -1)
        if result == RESULT_PASTDEST:
            plat.count = plat.wait
            plat.status = PLAT_WAITING
            world.counters.plat_wait_transitions += 1
            world.counters.plat_stop_sound_deferrals += 1
            stop_sound = 1
    elif plat.status == PLAT_WAITING:
        plat.count -= 1
        world.counters.plat_wait_countdowns += 1
        if plat.count == 0:
            if sector.floorheight == plat.low:
                plat.status = PLAT_UP
                world.counters.plat_up_restarts += 1
            else:
                plat.status = PLAT_DOWN
                world.counters.plat_down_restarts += 1
            world.counters.plat_start_sound_deferrals += 1
            start_sound = 1

    trace = Stage25PlatTraceRecord(
        tic=world.counters.plat_ticks,
        leveltime_before=world.ticker_world.leveltime,
        sector_index=plat.sector_index,
        floor_before=floor_before,
        floor_after=sector.floorheight,
        status_before=status_before,
        status_after=plat.status,
        count_before=count_before,
        count_after=plat.count,
        dest=dest,
        speed=plat.speed,
        result=result,
        removed=removed,
        start_sound=start_sound,
        stop_sound=stop_sound,
    )
    world.plat_trace.append(trace)
    return trace


def p_update_specials_stage25_source_shape(world: Stage25World) -> None:
    stage24.p_update_specials_stage24_source_shape(world)


def p_ticker_stage25_source_shape(world: Stage25World) -> bool:
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
    p_update_specials_stage25_source_shape(world)
    stage21.p_respawn_specials_stage21_source_shape(ticker)
    ticker.leveltime += 1
    ticker.counters.leveltime_increments += 1
    ticker.order_log.append("leveltime++")
    return True


def p_use_special_line_stage25_source_shape(world: Stage25World, line: stage19.Stage19Line, side: int) -> bool:
    world.counters.special_use_attempts += 1
    world.counters.use_special_calls += 1
    if side:
        world.counters.back_side_rejections += 1
        return False
    world.counters.front_side_activations += 1
    if line.special != SELECTED_SPECIAL:
        world.counters.generalized_specials += 1
        return True
    if ev_do_plat_stage25_source_shape(world, line, DOWN_WAIT_UP_STAY, 1):
        stage23.p_change_switch_texture_stage23_source_shape(world, line, 1)
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


def _stage25_signature(ref: Stage25FirstPlatformLiftCycleReference) -> int:
    sig = 2166136261
    final_trace = ref.plat_trace[-1]
    for value in (
        ref.stage24.signature,
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
        ref.button_slot,
        ref.button_timer_start,
        ref.button_timer_end,
        ref.plat_spawn.low,
        ref.plat_spawn.high,
        ref.plat_spawn.speed,
        ref.plat_spawn.wait,
        ref.counters.plat_ticks,
        ref.counters.plat_move_plane_calls,
        ref.counters.plat_mutations,
        ref.counters.plat_pastdest_events,
        ref.counters.plat_wait_transitions,
        ref.counters.plat_wait_countdowns,
        ref.counters.plat_up_restarts,
        ref.counters.plat_removal_requests,
        ref.counters.activeplat_slot_clears,
        ref.counters.plat_start_sound_deferrals,
        ref.counters.plat_stop_sound_deferrals,
        final_trace.floor_after,
        ref.leveltime_after,
    ):
        sig = _hash_u32(sig, value)
    sig = _hash_bytes(sig, ref.census.lower_texture_before.encode("ascii"))
    sig = _hash_bytes(sig, ref.census.lower_texture_pressed.encode("ascii"))
    sig = _hash_bytes(sig, ref.census.lower_texture_restored.encode("ascii"))
    return sig


def _reference_stage25_uncached(wad_path: str | Path) -> Stage25FirstPlatformLiftCycleReference:
    wad_path = Path(wad_path)
    wad = WadFile.from_file(wad_path)
    stage24_ref = stage24.reference_first_floor_sector_special_probe_for_pinned_map(wad_path)
    world = _build_stage25_world(wad, SELECTED_MAP)
    line = world.lines[SELECTED_LINE_INDEX]
    if (line.special, line.tag, line.sidenum[0], line.sidenum[1], line.frontsector) != (
        SELECTED_SPECIAL,
        SELECTED_TAG,
        SELECTED_RIGHT_SIDEDEF,
        SELECTED_LEFT_SIDEDEF,
        SELECTED_FRONT_SECTOR,
    ):
        raise AssertionError("pinned MAP12 platform candidate metadata mismatch")

    before_special = line.special
    p_use_special_line_stage25_source_shape(world, line, 0)
    switch = world.switch_result
    plat_spawn = world.plat_spawn
    if switch is None or plat_spawn is None or not plat_spawn.rtn:
        raise AssertionError("stage25 selected route did not mutate switch and spawn platform")
    duplicate_guard_result = stage23.p_start_button_stage23_source_shape(world, line, switch.where, switch.before_texture)
    button_slot = next(index for index, button in enumerate(world.buttonlist) if button.btimer)
    button_timer_start = world.buttonlist[button_slot].btimer
    assert world.ticker_world is not None
    leveltime_before = world.ticker_world.leveltime
    for _ in range(DEFAULT_STAGE25_TICKER_TICS):
        p_ticker_stage25_source_shape(world)
    leveltime_after = world.ticker_world.leveltime
    order_ok = stage21._stage21_order_ok(tuple(world.ticker_world.order_log))
    restored_id = stage22._switch_slot_value(world.side_textures[SELECTED_RIGHT_SIDEDEF], BUTTON_BOTTOM)
    target = world.sectors[SELECTED_TARGET_SECTOR]
    census = Stage25PinnedCensusRecord(
        map_name=SELECTED_MAP,
        line_index=line.index,
        special=before_special,
        tag=line.tag,
        side=0,
        right_sidedef=line.sidenum[0],
        left_sidedef=line.sidenum[1],
        front_sector=line.frontsector,
        lower_texture_before=switch.before_name,
        lower_texture_pressed=switch.after_name,
        lower_texture_restored=_texture_name(world, restored_id),
        target_sector=plat_spawn.selected_sector,
        target_floor_before=plat_spawn.floor_before,
        target_floor_after=target.floorheight,
        target_ceiling=plat_spawn.ceilingheight,
        target_special=plat_spawn.special,
        surrounding_lowest_floor=plat_spawn.surrounding_lowest_floor,
    )
    ref = Stage25FirstPlatformLiftCycleReference(
        stage24=stage24_ref,
        census=census,
        switch=switch,
        plat_spawn=plat_spawn,
        button_slot=button_slot,
        button_timer_start=button_timer_start,
        button_timer_end=world.buttonlist[button_slot].btimer,
        duplicate_guard_result=duplicate_guard_result,
        plat_trace=tuple(world.plat_trace),
        counters=world.counters,
        ticker_counters=world.ticker_world.counters,
        leveltime_before=leveltime_before,
        leveltime_after=leveltime_after,
        order_ok=order_ok,
        signature=0,
    )
    return Stage25FirstPlatformLiftCycleReference(**{**ref.__dict__, "signature": _stage25_signature(ref)})


@lru_cache(maxsize=4)
def _reference_stage25_cached(wad_path: str) -> Stage25FirstPlatformLiftCycleReference:
    return _reference_stage25_uncached(wad_path)


def reference_first_platform_lift_cycle_probe_for_pinned_map(wad_path: str | Path) -> Stage25FirstPlatformLiftCycleReference:
    return _reference_stage25_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage25FirstPlatformLiftCycleReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_first_platform_lift_cycle_probe_for_pinned_map(wad_path)


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


def emit_stage25_entry(pe: PE32) -> None:
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
    x86.call_rel32(pe, "source_stage25_load_wad_first_platform_lift_cycle_probe")
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


def emit_source_stage25_load_wad_first_platform_lift_cycle_probe(pe: PE32) -> None:
    pe.label("source_stage25_load_wad_first_platform_lift_cycle_probe")
    x86.call_rel32(pe, "source_stage24_load_wad_first_floor_sector_special_probe")
    x86.mov_reg_mem_abs32(pe, "eax", "stage24_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage24_expected_signature")
    x86.jne_rel32(pe, "source_stage25_return")
    x86.call_rel32(pe, "render_first_platform_lift_cycle_probe_debug")
    x86.call_rel32(pe, "append_stage25_success_status")
    pe.label("source_stage25_return")
    x86.ret(pe)


def emit_render_first_platform_lift_cycle_probe_debug(pe: PE32) -> None:
    pe.label("P_UseSpecialLine_button62_downWaitUpStay_source_shape_debug")
    pe.label("EV_DoPlat_downWaitUpStay_stage25_source_shape_debug")
    pe.label("P_FindSectorFromLineTag_stage25_plat_source_shape_debug")
    pe.label("P_FindLowestFloorSurrounding_stage25_source_shape_debug")
    pe.label("T_PlatRaise_downWaitUpStay_stage25_source_shape_debug")
    pe.label("T_MovePlane_plat_floor_stage25_source_shape_debug")
    pe.label("P_ActivePlat_stage25_source_shape_debug")
    pe.label("render_first_platform_lift_cycle_probe_debug")
    for dst, src in (
        ("stage25_runtime_signature", "stage25_expected_signature"),
        ("stage25_runtime_texture_pressed", "stage25_texture_pressed"),
        ("stage25_runtime_texture_restored", "stage25_texture_restored"),
        ("stage25_runtime_floor_after", "stage25_floor_after"),
        ("stage25_runtime_button_timer_end", "stage25_button_timer_end"),
        ("stage25_runtime_leveltime_after", "stage25_leveltime_after"),
        ("stage25_runtime_order_ok", "stage25_order_ok"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage24._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage25_success_status(pe: PE32) -> None:
    pe.label("append_stage25_success_status")
    _emit_seek_buffer_end(pe, "status_success_buffer", "stage25_status")
    stage01.append_c_string_label(pe, "status_stage25_success_header")
    stage01.append_u32_label(pe, "status_stage25_line_prefix", "stage25_line")
    stage01.append_c_string_label(pe, "status_stage25_texture_prefix")
    stage01.append_c_string_label(pe, "stage25_texture_before_name")
    stage01.append_c_string_label(pe, "status_stage25_arrow")
    stage01.append_c_string_label(pe, "stage25_texture_pressed_name")
    stage01.append_c_string_label(pe, "status_stage25_arrow")
    stage01.append_c_string_label(pe, "stage25_texture_restored_name")
    stage01.append_u32_label(pe, "status_stage25_sector_prefix", "stage25_target_sector")
    stage01.append_i32_label(pe, "status_stage25_floor_prefix", "stage25_runtime_floor_after")
    stage01.append_u32_label(pe, "status_stage25_signature_prefix", "stage25_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage25_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage25_title")
    for prefix, label, signed in (
        ("title_stage25_map_prefix", "stage25_map_number", False),
        ("title_stage25_line_prefix", "stage25_line", False),
        ("title_stage25_special_prefix", "stage25_special", False),
        ("title_stage25_tag_prefix", "stage25_tag", False),
        ("title_stage25_side_prefix", "stage25_side", False),
        ("title_stage25_right_sidedef_prefix", "stage25_right_sidedef", False),
        ("title_stage25_left_sidedef_prefix", "stage25_left_sidedef", True),
        ("title_stage25_front_sector_prefix", "stage25_front_sector", False),
        ("title_stage25_slot_prefix", "stage25_switch_where", False),
    ):
        (stage01.append_i32_label if signed else stage01.append_u32_label)(pe, prefix, label)
    stage01.append_c_string_label(pe, "title_stage25_texture_before_prefix")
    stage01.append_c_string_label(pe, "stage25_texture_before_name")
    stage01.append_c_string_label(pe, "title_stage25_texture_pressed_prefix")
    stage01.append_c_string_label(pe, "stage25_texture_pressed_name")
    stage01.append_c_string_label(pe, "title_stage25_texture_restored_prefix")
    stage01.append_c_string_label(pe, "stage25_texture_restored_name")
    for prefix, label in (
        ("title_stage25_pair_prefix", "stage25_switch_pair_index"),
        ("title_stage25_switch_index_prefix", "stage25_switchlist_index"),
        ("title_stage25_special_after_prefix", "stage25_line_special_after"),
        ("title_stage25_button_slot_prefix", "stage25_button_slot"),
        ("title_stage25_timer0_prefix", "stage25_button_timer_start"),
        ("title_stage25_timer1_prefix", "stage25_runtime_button_timer_end"),
        ("title_stage25_button_restore_prefix", "stage25_button_restore_steps"),
        ("title_stage25_button_clear_prefix", "stage25_button_slot_clears"),
        ("title_stage25_ev_prefix", "stage25_ev_do_plat_calls"),
        ("title_stage25_find_prefix", "stage25_plat_find_sector_calls"),
        ("title_stage25_scan_prefix", "stage25_plat_tag_scan_steps"),
        ("title_stage25_sector_prefix", "stage25_target_sector"),
        ("title_stage25_floor0_prefix", "stage25_floor_before"),
        ("title_stage25_floor1_prefix", "stage25_runtime_floor_after"),
        ("title_stage25_ceiling_prefix", "stage25_target_ceiling"),
        ("title_stage25_special_sector_prefix", "stage25_target_special"),
        ("title_stage25_low_prefix", "stage25_plat_low"),
        ("title_stage25_dest_prefix", "stage25_plat_high"),
        ("title_stage25_direction_prefix", "stage25_plat_initial_status"),
        ("title_stage25_speed_prefix", "stage25_plat_speed_units"),
        ("title_stage25_wait_prefix", "stage25_plat_wait"),
        ("title_stage25_active_slot_prefix", "stage25_activeplat_slot"),
        ("title_stage25_add_prefix", "stage25_plat_thinker_records"),
        ("title_stage25_ticker_prefix", "stage25_ticker_calls"),
        ("title_stage25_floor_ticks_prefix", "stage25_plat_ticks"),
        ("title_stage25_move_plane_prefix", "stage25_plat_move_plane_calls"),
        ("title_stage25_mut_prefix", "stage25_plat_mutations"),
        ("title_stage25_past_prefix", "stage25_plat_pastdest_events"),
        ("title_stage25_wait_transition_prefix", "stage25_plat_wait_transitions"),
        ("title_stage25_wait_countdown_prefix", "stage25_plat_wait_countdowns"),
        ("title_stage25_up_restart_prefix", "stage25_plat_up_restarts"),
        ("title_stage25_remove_prefix", "stage25_plat_removal_requests"),
        ("title_stage25_active_clear_prefix", "stage25_activeplat_slot_clears"),
        ("title_stage25_lazy_prefix", "stage25_lazy_removals"),
        ("title_stage25_move_sound_prefix", "stage25_plat_start_sound_deferrals"),
        ("title_stage25_stop_sound_prefix", "stage25_plat_stop_sound_deferrals"),
        ("title_stage25_leveltime_prefix", "stage25_runtime_leveltime_after"),
        ("title_stage25_order_prefix", "stage25_runtime_order_ok"),
        ("title_stage25_audio_prefix", "stage25_real_audio_playbacks"),
        ("title_stage25_gen_prefix", "stage25_generalized_floor_absent"),
        ("title_stage25_plat_prefix", "stage25_generalized_plat_absent"),
        ("title_stage25_ceil_prefix", "stage25_generalized_ceiling_absent"),
        ("title_stage25_stage25_prefix", "stage25_stage26_absent"),
    ):
        stage01.append_i32_label(pe, prefix, label)
    stage01.append_u32_label(pe, "title_stage25_signature_prefix", "stage25_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage25_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    counters = ref.counters if ref is not None else Stage25Counters()
    ticker = ref.ticker_counters if ref is not None else stage21.Stage21Counters()
    census = ref.census if ref is not None else None
    switch = ref.switch if ref is not None else None
    plat = ref.plat_spawn if ref is not None else None
    pe.align_section(4)
    for name, value in (
        ("stage25_map_number", 12),
        ("stage25_line", census.line_index if census else 0),
        ("stage25_special", census.special if census else 0),
        ("stage25_tag", census.tag if census else 0),
        ("stage25_side", census.side if census else 0),
        ("stage25_right_sidedef", census.right_sidedef if census else 0),
        ("stage25_left_sidedef", (census.left_sidedef if census else 0) & 0xFFFFFFFF),
        ("stage25_front_sector", census.front_sector if census else 0),
        ("stage25_texture_before", switch.before_texture if switch else 0),
        ("stage25_texture_pressed", switch.after_texture if switch else 0),
        ("stage25_runtime_texture_pressed", 0),
        ("stage25_texture_restored", switch.before_texture if switch else 0),
        ("stage25_runtime_texture_restored", 0),
        ("stage25_switch_where", switch.where if switch else 0),
        ("stage25_switch_pair_index", switch.pair_index if switch else 0),
        ("stage25_switchlist_index", switch.switchlist_index if switch else 0),
        ("stage25_line_special_after", switch.line_special_after if switch else 0),
        ("stage25_button_slot", ref.button_slot if ref else 0),
        ("stage25_button_timer_start", ref.button_timer_start if ref else 0),
        ("stage25_button_timer_end", ref.button_timer_end if ref else 0),
        ("stage25_runtime_button_timer_end", 0),
        ("stage25_duplicate_guard_result", ref.duplicate_guard_result if ref else 0),
        ("stage25_button_restore_steps", counters.button_restore_steps),
        ("stage25_button_slot_clears", counters.button_slot_clears),
        ("stage25_ev_do_plat_calls", counters.ev_do_plat_calls),
        ("stage25_plat_find_sector_calls", counters.plat_find_sector_calls),
        ("stage25_plat_tag_scan_steps", counters.plat_tag_scan_steps),
        ("stage25_plat_tagged_sector_matches", counters.plat_tagged_sector_matches),
        ("stage25_plat_tagged_sector_spawns", counters.plat_tagged_sector_spawns),
        ("stage25_target_sector", plat.selected_sector if plat else 0),
        ("stage25_floor_before", ((plat.floor_before >> FRACBITS) if plat else 0) & 0xFFFFFFFF),
        ("stage25_floor_after", ((census.target_floor_after >> FRACBITS) if census else 0) & 0xFFFFFFFF),
        ("stage25_runtime_floor_after", 0),
        ("stage25_target_ceiling", ((plat.ceilingheight >> FRACBITS) if plat else 0) & 0xFFFFFFFF),
        ("stage25_target_special", plat.special if plat else 0),
        ("stage25_plat_low", ((plat.low >> FRACBITS) if plat else 0) & 0xFFFFFFFF),
        ("stage25_plat_high", ((plat.high >> FRACBITS) if plat else 0) & 0xFFFFFFFF),
        ("stage25_plat_initial_status", plat.status if plat else 0),
        ("stage25_plat_speed_units", ((plat.speed >> FRACBITS) if plat else 0)),
        ("stage25_plat_wait", plat.wait if plat else 0),
        ("stage25_activeplat_slot", plat.active_slot if plat else 0),
        ("stage25_plat_thinker_records", counters.plat_thinker_records),
        ("stage25_ticker_calls", ticker.ticker_calls),
        ("stage25_plat_ticks", counters.plat_ticks),
        ("stage25_plat_move_plane_calls", counters.plat_move_plane_calls),
        ("stage25_plat_mutations", counters.plat_mutations),
        ("stage25_plat_pastdest_events", counters.plat_pastdest_events),
        ("stage25_plat_wait_transitions", counters.plat_wait_transitions),
        ("stage25_plat_wait_countdowns", counters.plat_wait_countdowns),
        ("stage25_plat_up_restarts", counters.plat_up_restarts),
        ("stage25_plat_removal_requests", counters.plat_removal_requests),
        ("stage25_activeplat_slot_clears", counters.activeplat_slot_clears),
        ("stage25_lazy_removals", ticker.lazy_removals),
        ("stage25_plat_start_sound_deferrals", counters.plat_start_sound_deferrals),
        ("stage25_plat_stop_sound_deferrals", counters.plat_stop_sound_deferrals),
        ("stage25_leveltime_after", ref.leveltime_after if ref else 0),
        ("stage25_runtime_leveltime_after", 0),
        ("stage25_order_ok", ref.order_ok if ref else 0),
        ("stage25_runtime_order_ok", 0),
        ("stage25_real_audio_playbacks", counters.real_audio_playbacks),
        ("stage25_generalized_floor_absent", counters.generalized_floor_absent),
        ("stage25_generalized_plat_absent", counters.generalized_plat_absent),
        ("stage25_generalized_ceiling_absent", counters.generalized_ceiling_absent),
        ("stage25_stage26_absent", counters.stage26_absent),
        ("stage25_expected_signature", ref.signature if ref else 0),
        ("stage25_runtime_signature", 0),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    pe.align_section(1)
    pe.label("stage25_texture_before_name")
    x86.emit_asciiz(pe, census.lower_texture_before if census else "")
    pe.label("stage25_texture_pressed_name")
    x86.emit_asciiz(pe, census.lower_texture_pressed if census else "")
    pe.label("stage25_texture_restored_name")
    x86.emit_asciiz(pe, census.lower_texture_restored if census else "")
    pe.label("status_stage25_success_header")
    x86.emit_asciiz(pe, "\r\nsource_stage25_first_platform_lift_cycle_probe\r\nFirst platform lift cycle proof OK\r\n")
    pe.label("status_stage25_line_prefix")
    x86.emit_asciiz(pe, "\r\nSelected MAP12 platform linedef: ")
    pe.label("status_stage25_texture_prefix")
    x86.emit_asciiz(pe, "\r\nPlatform button texture lifecycle: ")
    pe.label("status_stage25_arrow")
    x86.emit_asciiz(pe, " -> ")
    pe.label("status_stage25_sector_prefix")
    x86.emit_asciiz(pe, "\r\nPlatform target sector: ")
    pe.label("status_stage25_floor_prefix")
    x86.emit_asciiz(pe, "\r\nPlatform floor after bounded ticker: ")
    pe.label("status_stage25_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage25 platform signature: ")
    pe.label("status_stage25_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage25 preserves stage24 through stage19, then uses real MAP12 linedef 2304. "
        "The bounded route reaches P_UseSpecialLine case 62, EV_DoPlat(downWaitUpStay), "
        "P_FindSectorFromLineTag, P_FindLowestFloorSurrounding, P_AddThinker, P_AddActivePlat, "
        "T_PlatRaise, and the floor branch of T_MovePlane. The platform moves down to -64, "
        "waits, restarts upward, returns to -8, clears activeplats and sector specialdata, "
        "marks the thinker for lazy removal, and counts deferred pstart/pstop sound boundaries. "
        "Speaker output, broad platform families, floors, ceilings, crushers, stairs, donuts, "
        "live input, progression, and later-stage work stay absent.\r\n",
    )
    for label, text in (
        ("title_stage25_map_prefix", " S25MAP="),
        ("title_stage25_line_prefix", " S25LINE="),
        ("title_stage25_special_prefix", " S25SPEC="),
        ("title_stage25_tag_prefix", " TAG25="),
        ("title_stage25_side_prefix", " SIDE25="),
        ("title_stage25_right_sidedef_prefix", " RSID25="),
        ("title_stage25_left_sidedef_prefix", " LSID25="),
        ("title_stage25_front_sector_prefix", " FSEC25="),
        ("title_stage25_slot_prefix", " SLOT25="),
        ("title_stage25_texture_before_prefix", " TEX250="),
        ("title_stage25_texture_pressed_prefix", " TEX251="),
        ("title_stage25_texture_restored_prefix", " TEX252="),
        ("title_stage25_pair_prefix", " PAIR25="),
        ("title_stage25_switch_index_prefix", " SWI25="),
        ("title_stage25_special_after_prefix", " SPC251="),
        ("title_stage25_button_slot_prefix", " BSLOT25="),
        ("title_stage25_timer0_prefix", " BT250="),
        ("title_stage25_timer1_prefix", " BT251="),
        ("title_stage25_button_restore_prefix", " BREST25="),
        ("title_stage25_button_clear_prefix", " BCLR25="),
        ("title_stage25_ev_prefix", " EVP25="),
        ("title_stage25_find_prefix", " TFIND25="),
        ("title_stage25_scan_prefix", " TITER25="),
        ("title_stage25_sector_prefix", " TSEC25="),
        ("title_stage25_floor0_prefix", " F250="),
        ("title_stage25_floor1_prefix", " F251="),
        ("title_stage25_ceiling_prefix", " C25="),
        ("title_stage25_special_sector_prefix", " SSPEC25="),
        ("title_stage25_low_prefix", " LOW25="),
        ("title_stage25_dest_prefix", " HIGH25="),
        ("title_stage25_direction_prefix", " STAT25="),
        ("title_stage25_speed_prefix", " SPD25="),
        ("title_stage25_wait_prefix", " WAIT25="),
        ("title_stage25_active_slot_prefix", " ASLOT25="),
        ("title_stage25_add_prefix", " ADD25="),
        ("title_stage25_ticker_prefix", " PTIC25="),
        ("title_stage25_floor_ticks_prefix", " TPL25="),
        ("title_stage25_move_plane_prefix", " MP25="),
        ("title_stage25_mut_prefix", " PMUT25="),
        ("title_stage25_past_prefix", " PAST25="),
        ("title_stage25_wait_transition_prefix", " WT25="),
        ("title_stage25_wait_countdown_prefix", " WDEC25="),
        ("title_stage25_up_restart_prefix", " UP25="),
        ("title_stage25_remove_prefix", " AREM25="),
        ("title_stage25_active_clear_prefix", " ACLR25="),
        ("title_stage25_lazy_prefix", " LREM25="),
        ("title_stage25_move_sound_prefix", " PSTART25="),
        ("title_stage25_stop_sound_prefix", " PSTOP25="),
        ("title_stage25_leveltime_prefix", " LT25="),
        ("title_stage25_order_prefix", " ORDER25="),
        ("title_stage25_audio_prefix", " AUD25="),
        ("title_stage25_gen_prefix", " GENF25="),
        ("title_stage25_plat_prefix", " GPLAT25="),
        ("title_stage25_ceil_prefix", " GCEIL25="),
        ("title_stage25_stage25_prefix", " S26ABS="),
        ("title_stage25_signature_prefix", " S25SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)


def build_source_stage25_first_platform_lift_cycle_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_stage25_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage25_load_wad_first_platform_lift_cycle_probe(pe)
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
    emit_render_first_platform_lift_cycle_probe_debug(pe)
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
    emit_append_stage25_success_status(pe)
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
    emit_stage25_data(pe)
    return pe.build("entry")


def write_source_stage25_first_platform_lift_cycle_probe_exe(path: str | Path) -> bytes:
    image = build_source_stage25_first_platform_lift_cycle_probe_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage25 first platform lift cycle PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage25_first_platform_lift_cycle_probe.exe",
        help="path to write, default: build/source_stage25_first_platform_lift_cycle_probe.exe",
    )
    args = parser.parse_args()
    write_source_stage25_first_platform_lift_cycle_probe_exe(args.output)


if __name__ == "__main__":
    main()
