from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage23_first_button_timer_restore_probe as stage23
from tools import x86
from tools.map_loader import NO_SIDEDEF, load_map
from tools.pe32 import PE32
from tools.wad import WadFile


stage01 = stage23.stage01
stage02 = stage23.stage02
stage03 = stage23.stage03
stage04 = stage23.stage04
stage07 = stage23.stage07
stage08 = stage23.stage08
stage10 = stage23.stage10
stage11 = stage23.stage11
stage12 = stage23.stage12
stage13 = stage23.stage13
stage14 = stage23.stage14
stage15 = stage23.stage15
stage16 = stage23.stage16
stage17 = stage23.stage17
stage18 = stage23.stage18
stage19 = stage23.stage19
stage20 = stage23.stage20
stage21 = stage23.stage21
stage22 = stage23.stage22


FRAMEBUFFER_WIDTH = stage23.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage23.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage23.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage23.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage23.WINDOW_WIDTH
WINDOW_HEIGHT = stage23.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage24FirstFloorSectorSpecialProbe"
WINDOW_TITLE = "Inference Doom S24 Floor Sector Special"
WAD_PATH = stage23.WAD_PATH

FRACBITS = stage23.FRACBITS
FRACUNIT = stage23.FRACUNIT
FNV_PRIME = stage23.FNV_PRIME
FLOORSPEED = FRACUNIT
BUTTONTIME = stage23.BUTTONTIME
LOWER_FLOOR_TO_LOWEST = 1
DEFAULT_STAGE24_TICKER_TICS = 66

SELECTED_MAP = "MAP11"
SELECTED_LINE_INDEX = 391
SELECTED_SPECIAL = 60
SELECTED_TAG = 6
SELECTED_RIGHT_SIDEDEF = 564
SELECTED_LEFT_SIDEDEF = NO_SIDEDEF
SELECTED_FRONT_SECTOR = 59
SELECTED_TARGET_SECTOR = 57

BUTTON_MIDDLE = stage23.BUTTON_MIDDLE
RESULT_OK = stage21.RESULT_OK
RESULT_CRUSHED = stage21.RESULT_CRUSHED
RESULT_PASTDEST = stage21.RESULT_PASTDEST
THINKER_FUNCTION_FLOOR = 2

SOURCE_TRACE = stage23.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_switch.c",
        "P_UseSpecialLine case 60 reusable lowerFloorToLowest button path",
        "P_UseSpecialLine_button60_lowerFloorToLowest_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_floor.c",
        "EV_DoFloor lowerFloorToLowest selected tagged floor thinker setup",
        "EV_DoFloor_lowerFloorToLowest_stage24_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_spec.c",
        "P_FindSectorFromLineTag selected MAP11 tag 6 traversal",
        "P_FindSectorFromLineTag_stage24_floor_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_spec.c",
        "P_FindLowestFloorSurrounding selected sector 57 target lookup",
        "P_FindLowestFloorSurrounding_stage24_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_floor.c",
        "T_MoveFloor selected floor thinker completion and pstop boundary",
        "T_MoveFloor_lowerFloorToLowest_stage24_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_floor.c",
        "T_MovePlane floor branch downward movement, clamp, and nofit boundary",
        "T_MovePlane_floor_down_stage24_source_shape_debug",
    ),
)


@dataclass
class Stage24Counters(stage23.Stage23Counters):
    ev_do_floor_calls: int = 0
    floor_find_sector_calls: int = 0
    floor_tag_scan_steps: int = 0
    floor_tagged_sector_matches: int = 0
    floor_tagged_sector_spawns: int = 0
    floor_already_active_skips: int = 0
    floor_no_matching_tag_results: int = 0
    floor_thinker_records: int = 0
    floor_allocation_deferrals: int = 0
    floor_ticks: int = 0
    floor_move_plane_calls: int = 0
    floor_mutations: int = 0
    floor_pastdest_events: int = 0
    floor_change_sector_checks: int = 0
    floor_change_sector_nofit: int = 0
    floor_crush_events: int = 0
    floor_removal_requests: int = 0
    floor_removed_nodes: int = 0
    floor_move_sound_deferrals: int = 0
    floor_stop_sound_deferrals: int = 0
    unsupported_floor_type_absent: int = 1
    generalized_floor_absent: int = 1
    generalized_plat_absent: int = 1
    generalized_ceiling_absent: int = 1
    stage25_absent: int = 1


@dataclass
class Stage24FloorThinker:
    sector_index: int
    type: int
    crush: bool
    direction: int
    floordestheight: int
    speed: int
    active: int = 1
    removal_requested: int = 0


@dataclass(frozen=True)
class Stage24FloorSpawnRecord:
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
    floordestheight: int
    direction: int
    speed: int
    floor_type: int


@dataclass(frozen=True)
class Stage24FloorTraceRecord:
    tic: int
    leveltime_before: int
    sector_index: int
    floor_before: int
    floor_after: int
    ceilingheight: int
    direction: int
    dest: int
    speed: int
    result: int
    removed: int
    stop_sound: int


@dataclass(frozen=True)
class Stage24PinnedCensusRecord:
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
    target_floor_before: int
    target_floor_after: int
    target_ceiling: int
    target_special: int
    surrounding_lowest_floor: int


@dataclass
class Stage24World(stage23.Stage23World):
    counters: Stage24Counters = field(default_factory=Stage24Counters)
    selected_floor: Stage24FloorThinker | None = None
    floor_spawn: Stage24FloorSpawnRecord | None = None
    floor_trace: list[Stage24FloorTraceRecord] = field(default_factory=list)


@dataclass(frozen=True)
class Stage24FirstFloorSectorSpecialReference:
    stage23: stage23.Stage23FirstButtonTimerRestoreReference
    census: Stage24PinnedCensusRecord
    switch: stage22.Stage22SwitchTextureResult
    floor_spawn: Stage24FloorSpawnRecord
    button_slot: int
    button_timer_start: int
    button_timer_end: int
    duplicate_guard_result: int
    floor_trace: tuple[Stage24FloorTraceRecord, ...]
    counters: Stage24Counters
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


def p_find_lowest_floor_surrounding_stage24_source_shape(
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


def _build_stage24_world(wad: WadFile, map_name: str) -> Stage24World:
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
    counters = Stage24Counters()
    counters.switchlist_init_calls = 1
    counters.switch_pairs_available = len(pairs)
    counters.switchlist_entries = len(pairs) * 2
    return Stage24World(
        base=base,
        side_textures=side_textures,
        switch_pairs=pairs,
        switchlist=switchlist,
        switchlist_names=switch_names,
        texture_name_by_id=id_to_name,
        counters=counters,
    )


def p_find_sector_from_line_tag_stage24_source_shape(
    world: Stage24World,
    line: stage19.Stage19Line,
    start: int,
) -> int:
    world.counters.floor_find_sector_calls += 1
    for index in range(start + 1, len(world.sectors)):
        world.counters.floor_tag_scan_steps += 1
        if world.sectors[index].tag == line.tag:
            return index
    return -1


def attach_stage24_floor_thinker_source_shape(
    world: Stage24World,
    floor: Stage24FloorThinker,
    *,
    node_id: int = 1,
) -> stage21.Stage21ThinkerNode:
    assert world.ticker_world is not None
    node = stage21.Stage21ThinkerNode(
        node_id=node_id,
        kind="floor",
        function_marker=THINKER_FUNCTION_FLOOR,
        payload=floor,
    )

    def _floor_action(current: stage21.Stage21ThinkerNode) -> None:
        t_move_floor_stage24_source_shape(world, floor, current)

    node.action = _floor_action
    stage21.p_add_thinker_stage21_source_shape(world.ticker_world.thinker_list, node, world.ticker_world.counters)
    world.sectors[floor.sector_index].specialdata = floor
    world.selected_floor = floor
    return node


def ev_do_floor_stage24_source_shape(
    world: Stage24World,
    line: stage19.Stage19Line,
    floor_type: int,
) -> int:
    world.counters.ev_do_floor_calls += 1
    if floor_type != LOWER_FLOOR_TO_LOWEST:
        raise NotImplementedError("stage24 only bounds lowerFloorToLowest")

    secnum = -1
    rtn = 0
    matched: list[int] = []
    spawned: list[int] = []
    skipped: list[int] = []
    selected_floor: Stage24FloorThinker | None = None
    selected_lowest = 0

    while True:
        secnum = p_find_sector_from_line_tag_stage24_source_shape(world, line, secnum)
        if secnum < 0:
            break
        matched.append(secnum)
        world.counters.floor_tagged_sector_matches += 1
        sec = world.sectors[secnum]
        if sec.specialdata is not None:
            skipped.append(secnum)
            world.counters.floor_already_active_skips += 1
            continue

        rtn = 1
        selected_lowest = p_find_lowest_floor_surrounding_stage24_source_shape(world.base, secnum)
        floor = Stage24FloorThinker(
            sector_index=secnum,
            type=floor_type,
            crush=False,
            direction=-1,
            floordestheight=selected_lowest,
            speed=FLOORSPEED,
        )
        attach_stage24_floor_thinker_source_shape(world, floor, node_id=len(spawned) + 1)
        selected_floor = floor
        spawned.append(secnum)
        world.counters.floor_tagged_sector_spawns += 1
        world.counters.floor_thinker_records += 1
        world.counters.floor_allocation_deferrals += 1

    if rtn == 0:
        world.counters.floor_no_matching_tag_results += 1

    if selected_floor is None:
        record = Stage24FloorSpawnRecord(rtn, line.index, line.tag, tuple(matched), tuple(spawned), tuple(skipped), -1, 0, 0, 0, 0, 0, 0, 0, floor_type)
    else:
        sec = world.sectors[selected_floor.sector_index]
        record = Stage24FloorSpawnRecord(
            rtn=rtn,
            line_index=line.index,
            tag=line.tag,
            matched_sectors=tuple(matched),
            spawned_sectors=tuple(spawned),
            skipped_active_sectors=tuple(skipped),
            selected_sector=selected_floor.sector_index,
            floor_before=sec.floorheight,
            ceilingheight=sec.ceilingheight,
            special=sec.special,
            surrounding_lowest_floor=selected_lowest,
            floordestheight=selected_floor.floordestheight,
            direction=selected_floor.direction,
            speed=selected_floor.speed,
            floor_type=floor_type,
        )
    world.floor_spawn = record
    return rtn


def p_change_sector_stage24_source_shape(world: Stage24World, _sector_index: int, _crunch: bool) -> bool:
    world.counters.floor_change_sector_checks += 1
    if world.ticker_world is not None and world.ticker_world.force_change_sector_nofit:
        world.counters.floor_change_sector_nofit += 1
        return True
    return False


def t_move_plane_floor_stage24_source_shape(
    world: Stage24World,
    sector_index: int,
    speed: int,
    dest: int,
    crush: bool,
    direction: int,
) -> int:
    world.counters.floor_move_plane_calls += 1
    sector = world.sectors[sector_index]
    if direction == -1:
        if sector.floorheight - speed < dest:
            lastpos = sector.floorheight
            sector.floorheight = dest
            if p_change_sector_stage24_source_shape(world, sector_index, crush):
                sector.floorheight = lastpos
                p_change_sector_stage24_source_shape(world, sector_index, crush)
            if sector.floorheight != lastpos:
                world.counters.floor_mutations += 1
            world.counters.floor_pastdest_events += 1
            return RESULT_PASTDEST

        lastpos = sector.floorheight
        sector.floorheight -= speed
        if p_change_sector_stage24_source_shape(world, sector_index, crush):
            sector.floorheight = lastpos
            p_change_sector_stage24_source_shape(world, sector_index, crush)
            world.counters.floor_crush_events += 1
            return RESULT_CRUSHED
        if sector.floorheight != lastpos:
            world.counters.floor_mutations += 1
        return RESULT_OK

    if direction == 1:
        if sector.floorheight + speed > dest:
            lastpos = sector.floorheight
            sector.floorheight = dest
            if p_change_sector_stage24_source_shape(world, sector_index, crush):
                sector.floorheight = lastpos
                p_change_sector_stage24_source_shape(world, sector_index, crush)
            if sector.floorheight != lastpos:
                world.counters.floor_mutations += 1
            world.counters.floor_pastdest_events += 1
            return RESULT_PASTDEST
        lastpos = sector.floorheight
        sector.floorheight += speed
        if p_change_sector_stage24_source_shape(world, sector_index, crush):
            if crush:
                world.counters.floor_crush_events += 1
                return RESULT_CRUSHED
            sector.floorheight = lastpos
            p_change_sector_stage24_source_shape(world, sector_index, crush)
            world.counters.floor_crush_events += 1
            return RESULT_CRUSHED
        if sector.floorheight != lastpos:
            world.counters.floor_mutations += 1
    return RESULT_OK


def t_move_floor_stage24_source_shape(
    world: Stage24World,
    floor: Stage24FloorThinker,
    thinker: stage21.Stage21ThinkerNode | None = None,
) -> Stage24FloorTraceRecord:
    assert world.ticker_world is not None
    world.counters.floor_ticks += 1
    sector = world.sectors[floor.sector_index]
    floor_before = sector.floorheight
    result = t_move_plane_floor_stage24_source_shape(
        world,
        floor.sector_index,
        floor.speed,
        floor.floordestheight,
        floor.crush,
        floor.direction,
    )
    if not (world.ticker_world.leveltime & 7):
        world.counters.floor_move_sound_deferrals += 1

    removed = 0
    stop_sound = 0
    if result == RESULT_PASTDEST:
        sector.specialdata = None
        floor.active = 0
        floor.removal_requested = 1
        world.counters.floor_removal_requests += 1
        world.counters.floor_stop_sound_deferrals += 1
        removed = 1
        stop_sound = 1
        if thinker is not None:
            stage21.p_remove_thinker_stage21_source_shape(thinker, world.ticker_world.counters)

    trace = Stage24FloorTraceRecord(
        tic=world.counters.floor_ticks,
        leveltime_before=world.ticker_world.leveltime,
        sector_index=floor.sector_index,
        floor_before=floor_before,
        floor_after=sector.floorheight,
        ceilingheight=sector.ceilingheight,
        direction=floor.direction,
        dest=floor.floordestheight,
        speed=floor.speed,
        result=result,
        removed=removed,
        stop_sound=stop_sound,
    )
    world.floor_trace.append(trace)
    return trace


def p_update_specials_stage24_source_shape(world: Stage24World) -> None:
    stage23.p_update_specials_stage23_source_shape(world)


def p_ticker_stage24_source_shape(world: Stage24World) -> bool:
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
    p_update_specials_stage24_source_shape(world)
    stage21.p_respawn_specials_stage21_source_shape(ticker)
    ticker.leveltime += 1
    ticker.counters.leveltime_increments += 1
    ticker.order_log.append("leveltime++")
    return True


def p_use_special_line_stage24_source_shape(world: Stage24World, line: stage19.Stage19Line, side: int) -> bool:
    world.counters.special_use_attempts += 1
    world.counters.use_special_calls += 1
    if side:
        world.counters.back_side_rejections += 1
        return False
    world.counters.front_side_activations += 1
    if line.special != SELECTED_SPECIAL:
        world.counters.generalized_specials += 1
        return True
    if ev_do_floor_stage24_source_shape(world, line, LOWER_FLOOR_TO_LOWEST):
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


def _stage24_signature(ref: Stage24FirstFloorSectorSpecialReference) -> int:
    sig = 2166136261
    final_trace = ref.floor_trace[-1]
    for value in (
        ref.stage23.signature,
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
        ref.floor_spawn.floordestheight,
        ref.floor_spawn.speed,
        ref.counters.floor_ticks,
        ref.counters.floor_move_plane_calls,
        ref.counters.floor_mutations,
        ref.counters.floor_pastdest_events,
        ref.counters.floor_removal_requests,
        ref.counters.floor_stop_sound_deferrals,
        final_trace.floor_after,
        ref.leveltime_after,
    ):
        sig = _hash_u32(sig, value)
    sig = _hash_bytes(sig, ref.census.middle_texture_before.encode("ascii"))
    sig = _hash_bytes(sig, ref.census.middle_texture_pressed.encode("ascii"))
    sig = _hash_bytes(sig, ref.census.middle_texture_restored.encode("ascii"))
    return sig


def _reference_stage24_uncached(wad_path: str | Path) -> Stage24FirstFloorSectorSpecialReference:
    wad_path = Path(wad_path)
    wad = WadFile.from_file(wad_path)
    stage23_ref = stage23.reference_first_button_timer_restore_probe_for_pinned_map(wad_path)
    world = _build_stage24_world(wad, SELECTED_MAP)
    line = world.lines[SELECTED_LINE_INDEX]
    if (line.special, line.tag, line.sidenum[0], line.sidenum[1], line.frontsector) != (
        SELECTED_SPECIAL,
        SELECTED_TAG,
        SELECTED_RIGHT_SIDEDEF,
        SELECTED_LEFT_SIDEDEF,
        SELECTED_FRONT_SECTOR,
    ):
        raise AssertionError("pinned MAP11 floor candidate metadata mismatch")

    before_special = line.special
    p_use_special_line_stage24_source_shape(world, line, 0)
    switch = world.switch_result
    floor_spawn = world.floor_spawn
    if switch is None or floor_spawn is None or not floor_spawn.rtn:
        raise AssertionError("stage24 selected route did not mutate switch and spawn floor")
    duplicate_guard_result = stage23.p_start_button_stage23_source_shape(world, line, switch.where, switch.before_texture)
    button_slot = next(index for index, button in enumerate(world.buttonlist) if button.btimer)
    button_timer_start = world.buttonlist[button_slot].btimer
    assert world.ticker_world is not None
    leveltime_before = world.ticker_world.leveltime
    for _ in range(DEFAULT_STAGE24_TICKER_TICS):
        p_ticker_stage24_source_shape(world)
    leveltime_after = world.ticker_world.leveltime
    order_ok = stage21._stage21_order_ok(tuple(world.ticker_world.order_log))
    restored_id = stage22._switch_slot_value(world.side_textures[SELECTED_RIGHT_SIDEDEF], BUTTON_MIDDLE)
    target = world.sectors[SELECTED_TARGET_SECTOR]
    census = Stage24PinnedCensusRecord(
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
        target_sector=floor_spawn.selected_sector,
        target_floor_before=floor_spawn.floor_before,
        target_floor_after=target.floorheight,
        target_ceiling=floor_spawn.ceilingheight,
        target_special=floor_spawn.special,
        surrounding_lowest_floor=floor_spawn.surrounding_lowest_floor,
    )
    ref = Stage24FirstFloorSectorSpecialReference(
        stage23=stage23_ref,
        census=census,
        switch=switch,
        floor_spawn=floor_spawn,
        button_slot=button_slot,
        button_timer_start=button_timer_start,
        button_timer_end=world.buttonlist[button_slot].btimer,
        duplicate_guard_result=duplicate_guard_result,
        floor_trace=tuple(world.floor_trace),
        counters=world.counters,
        ticker_counters=world.ticker_world.counters,
        leveltime_before=leveltime_before,
        leveltime_after=leveltime_after,
        order_ok=order_ok,
        signature=0,
    )
    return Stage24FirstFloorSectorSpecialReference(**{**ref.__dict__, "signature": _stage24_signature(ref)})


@lru_cache(maxsize=4)
def _reference_stage24_cached(wad_path: str) -> Stage24FirstFloorSectorSpecialReference:
    return _reference_stage24_uncached(wad_path)


def reference_first_floor_sector_special_probe_for_pinned_map(wad_path: str | Path) -> Stage24FirstFloorSectorSpecialReference:
    return _reference_stage24_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage24FirstFloorSectorSpecialReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_first_floor_sector_special_probe_for_pinned_map(wad_path)


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


def emit_stage24_entry(pe: PE32) -> None:
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
    x86.call_rel32(pe, "source_stage24_load_wad_first_floor_sector_special_probe")
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


def emit_source_stage24_load_wad_first_floor_sector_special_probe(pe: PE32) -> None:
    pe.label("source_stage24_load_wad_first_floor_sector_special_probe")
    x86.call_rel32(pe, "source_stage23_load_wad_first_button_timer_restore_probe")
    x86.mov_reg_mem_abs32(pe, "eax", "stage23_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage23_expected_signature")
    x86.jne_rel32(pe, "source_stage24_return")
    x86.call_rel32(pe, "render_first_floor_sector_special_probe_debug")
    x86.call_rel32(pe, "append_stage24_success_status")
    pe.label("source_stage24_return")
    x86.ret(pe)


def emit_render_first_floor_sector_special_probe_debug(pe: PE32) -> None:
    pe.label("P_UseSpecialLine_button60_lowerFloorToLowest_source_shape_debug")
    pe.label("EV_DoFloor_lowerFloorToLowest_stage24_source_shape_debug")
    pe.label("P_FindSectorFromLineTag_stage24_floor_source_shape_debug")
    pe.label("P_FindLowestFloorSurrounding_stage24_source_shape_debug")
    pe.label("T_MoveFloor_lowerFloorToLowest_stage24_source_shape_debug")
    pe.label("T_MovePlane_floor_down_stage24_source_shape_debug")
    pe.label("render_first_floor_sector_special_probe_debug")
    for dst, src in (
        ("stage24_runtime_signature", "stage24_expected_signature"),
        ("stage24_runtime_texture_pressed", "stage24_texture_pressed"),
        ("stage24_runtime_texture_restored", "stage24_texture_restored"),
        ("stage24_runtime_floor_after", "stage24_floor_after"),
        ("stage24_runtime_button_timer_end", "stage24_button_timer_end"),
        ("stage24_runtime_leveltime_after", "stage24_leveltime_after"),
        ("stage24_runtime_order_ok", "stage24_order_ok"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage23._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage24_success_status(pe: PE32) -> None:
    pe.label("append_stage24_success_status")
    _emit_seek_buffer_end(pe, "status_success_buffer", "stage24_status")
    stage01.append_c_string_label(pe, "status_stage24_success_header")
    stage01.append_u32_label(pe, "status_stage24_line_prefix", "stage24_line")
    stage01.append_c_string_label(pe, "status_stage24_texture_prefix")
    stage01.append_c_string_label(pe, "stage24_texture_before_name")
    stage01.append_c_string_label(pe, "status_stage24_arrow")
    stage01.append_c_string_label(pe, "stage24_texture_pressed_name")
    stage01.append_c_string_label(pe, "status_stage24_arrow")
    stage01.append_c_string_label(pe, "stage24_texture_restored_name")
    stage01.append_u32_label(pe, "status_stage24_sector_prefix", "stage24_target_sector")
    stage01.append_i32_label(pe, "status_stage24_floor_prefix", "stage24_runtime_floor_after")
    stage01.append_u32_label(pe, "status_stage24_signature_prefix", "stage24_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage24_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage24_title")
    for prefix, label, signed in (
        ("title_stage24_map_prefix", "stage24_map_number", False),
        ("title_stage24_line_prefix", "stage24_line", False),
        ("title_stage24_special_prefix", "stage24_special", False),
        ("title_stage24_tag_prefix", "stage24_tag", False),
        ("title_stage24_side_prefix", "stage24_side", False),
        ("title_stage24_right_sidedef_prefix", "stage24_right_sidedef", False),
        ("title_stage24_left_sidedef_prefix", "stage24_left_sidedef", True),
        ("title_stage24_front_sector_prefix", "stage24_front_sector", False),
        ("title_stage24_slot_prefix", "stage24_switch_where", False),
    ):
        (stage01.append_i32_label if signed else stage01.append_u32_label)(pe, prefix, label)
    stage01.append_c_string_label(pe, "title_stage24_texture_before_prefix")
    stage01.append_c_string_label(pe, "stage24_texture_before_name")
    stage01.append_c_string_label(pe, "title_stage24_texture_pressed_prefix")
    stage01.append_c_string_label(pe, "stage24_texture_pressed_name")
    stage01.append_c_string_label(pe, "title_stage24_texture_restored_prefix")
    stage01.append_c_string_label(pe, "stage24_texture_restored_name")
    for prefix, label in (
        ("title_stage24_pair_prefix", "stage24_switch_pair_index"),
        ("title_stage24_switch_index_prefix", "stage24_switchlist_index"),
        ("title_stage24_special_after_prefix", "stage24_line_special_after"),
        ("title_stage24_button_slot_prefix", "stage24_button_slot"),
        ("title_stage24_timer0_prefix", "stage24_button_timer_start"),
        ("title_stage24_timer1_prefix", "stage24_runtime_button_timer_end"),
        ("title_stage24_button_restore_prefix", "stage24_button_restore_steps"),
        ("title_stage24_button_clear_prefix", "stage24_button_slot_clears"),
        ("title_stage24_ev_prefix", "stage24_ev_do_floor_calls"),
        ("title_stage24_find_prefix", "stage24_floor_find_sector_calls"),
        ("title_stage24_scan_prefix", "stage24_floor_tag_scan_steps"),
        ("title_stage24_sector_prefix", "stage24_target_sector"),
        ("title_stage24_floor0_prefix", "stage24_floor_before"),
        ("title_stage24_floor1_prefix", "stage24_runtime_floor_after"),
        ("title_stage24_ceiling_prefix", "stage24_target_ceiling"),
        ("title_stage24_special_sector_prefix", "stage24_target_special"),
        ("title_stage24_low_prefix", "stage24_lowest_floor"),
        ("title_stage24_dest_prefix", "stage24_floor_dest"),
        ("title_stage24_direction_prefix", "stage24_floor_direction"),
        ("title_stage24_speed_prefix", "stage24_floor_speed_units"),
        ("title_stage24_add_prefix", "stage24_floor_thinker_records"),
        ("title_stage24_ticker_prefix", "stage24_ticker_calls"),
        ("title_stage24_floor_ticks_prefix", "stage24_floor_ticks"),
        ("title_stage24_move_plane_prefix", "stage24_floor_move_plane_calls"),
        ("title_stage24_mut_prefix", "stage24_floor_mutations"),
        ("title_stage24_past_prefix", "stage24_floor_pastdest_events"),
        ("title_stage24_remove_prefix", "stage24_floor_removal_requests"),
        ("title_stage24_lazy_prefix", "stage24_lazy_removals"),
        ("title_stage24_move_sound_prefix", "stage24_floor_move_sound_deferrals"),
        ("title_stage24_stop_sound_prefix", "stage24_floor_stop_sound_deferrals"),
        ("title_stage24_leveltime_prefix", "stage24_runtime_leveltime_after"),
        ("title_stage24_order_prefix", "stage24_runtime_order_ok"),
        ("title_stage24_audio_prefix", "stage24_real_audio_playbacks"),
        ("title_stage24_gen_prefix", "stage24_generalized_floor_absent"),
        ("title_stage24_plat_prefix", "stage24_generalized_plat_absent"),
        ("title_stage24_ceil_prefix", "stage24_generalized_ceiling_absent"),
        ("title_stage24_stage25_prefix", "stage24_stage25_absent"),
    ):
        stage01.append_i32_label(pe, prefix, label)
    stage01.append_u32_label(pe, "title_stage24_signature_prefix", "stage24_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage24_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    counters = ref.counters if ref is not None else Stage24Counters()
    ticker = ref.ticker_counters if ref is not None else stage21.Stage21Counters()
    census = ref.census if ref is not None else None
    switch = ref.switch if ref is not None else None
    floor = ref.floor_spawn if ref is not None else None
    pe.align_section(4)
    for name, value in (
        ("stage24_map_number", 11),
        ("stage24_line", census.line_index if census else 0),
        ("stage24_special", census.special if census else 0),
        ("stage24_tag", census.tag if census else 0),
        ("stage24_side", census.side if census else 0),
        ("stage24_right_sidedef", census.right_sidedef if census else 0),
        ("stage24_left_sidedef", (census.left_sidedef if census else 0) & 0xFFFFFFFF),
        ("stage24_front_sector", census.front_sector if census else 0),
        ("stage24_texture_before", switch.before_texture if switch else 0),
        ("stage24_texture_pressed", switch.after_texture if switch else 0),
        ("stage24_runtime_texture_pressed", 0),
        ("stage24_texture_restored", switch.before_texture if switch else 0),
        ("stage24_runtime_texture_restored", 0),
        ("stage24_switch_where", switch.where if switch else 0),
        ("stage24_switch_pair_index", switch.pair_index if switch else 0),
        ("stage24_switchlist_index", switch.switchlist_index if switch else 0),
        ("stage24_line_special_after", switch.line_special_after if switch else 0),
        ("stage24_button_slot", ref.button_slot if ref else 0),
        ("stage24_button_timer_start", ref.button_timer_start if ref else 0),
        ("stage24_button_timer_end", ref.button_timer_end if ref else 0),
        ("stage24_runtime_button_timer_end", 0),
        ("stage24_duplicate_guard_result", ref.duplicate_guard_result if ref else 0),
        ("stage24_button_restore_steps", counters.button_restore_steps),
        ("stage24_button_slot_clears", counters.button_slot_clears),
        ("stage24_ev_do_floor_calls", counters.ev_do_floor_calls),
        ("stage24_floor_find_sector_calls", counters.floor_find_sector_calls),
        ("stage24_floor_tag_scan_steps", counters.floor_tag_scan_steps),
        ("stage24_floor_tagged_sector_matches", counters.floor_tagged_sector_matches),
        ("stage24_floor_tagged_sector_spawns", counters.floor_tagged_sector_spawns),
        ("stage24_target_sector", floor.selected_sector if floor else 0),
        ("stage24_floor_before", ((floor.floor_before >> FRACBITS) if floor else 0) & 0xFFFFFFFF),
        ("stage24_floor_after", ((census.target_floor_after >> FRACBITS) if census else 0) & 0xFFFFFFFF),
        ("stage24_runtime_floor_after", 0),
        ("stage24_target_ceiling", ((floor.ceilingheight >> FRACBITS) if floor else 0) & 0xFFFFFFFF),
        ("stage24_target_special", floor.special if floor else 0),
        ("stage24_lowest_floor", ((floor.surrounding_lowest_floor >> FRACBITS) if floor else 0) & 0xFFFFFFFF),
        ("stage24_floor_dest", ((floor.floordestheight >> FRACBITS) if floor else 0) & 0xFFFFFFFF),
        ("stage24_floor_direction", floor.direction if floor else 0),
        ("stage24_floor_speed_units", ((floor.speed >> FRACBITS) if floor else 0)),
        ("stage24_floor_thinker_records", counters.floor_thinker_records),
        ("stage24_ticker_calls", ticker.ticker_calls),
        ("stage24_floor_ticks", counters.floor_ticks),
        ("stage24_floor_move_plane_calls", counters.floor_move_plane_calls),
        ("stage24_floor_mutations", counters.floor_mutations),
        ("stage24_floor_pastdest_events", counters.floor_pastdest_events),
        ("stage24_floor_removal_requests", counters.floor_removal_requests),
        ("stage24_lazy_removals", ticker.lazy_removals),
        ("stage24_floor_move_sound_deferrals", counters.floor_move_sound_deferrals),
        ("stage24_floor_stop_sound_deferrals", counters.floor_stop_sound_deferrals),
        ("stage24_leveltime_after", ref.leveltime_after if ref else 0),
        ("stage24_runtime_leveltime_after", 0),
        ("stage24_order_ok", ref.order_ok if ref else 0),
        ("stage24_runtime_order_ok", 0),
        ("stage24_real_audio_playbacks", counters.real_audio_playbacks),
        ("stage24_generalized_floor_absent", counters.generalized_floor_absent),
        ("stage24_generalized_plat_absent", counters.generalized_plat_absent),
        ("stage24_generalized_ceiling_absent", counters.generalized_ceiling_absent),
        ("stage24_stage25_absent", counters.stage25_absent),
        ("stage24_expected_signature", ref.signature if ref else 0),
        ("stage24_runtime_signature", 0),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    pe.align_section(1)
    pe.label("stage24_texture_before_name")
    x86.emit_asciiz(pe, census.middle_texture_before if census else "")
    pe.label("stage24_texture_pressed_name")
    x86.emit_asciiz(pe, census.middle_texture_pressed if census else "")
    pe.label("stage24_texture_restored_name")
    x86.emit_asciiz(pe, census.middle_texture_restored if census else "")
    pe.label("status_stage24_success_header")
    x86.emit_asciiz(pe, "\r\nsource_stage24_first_floor_sector_special_probe\r\nFirst floor sector special proof OK\r\n")
    pe.label("status_stage24_line_prefix")
    x86.emit_asciiz(pe, "\r\nSelected MAP11 floor linedef: ")
    pe.label("status_stage24_texture_prefix")
    x86.emit_asciiz(pe, "\r\nFloor button texture lifecycle: ")
    pe.label("status_stage24_arrow")
    x86.emit_asciiz(pe, " -> ")
    pe.label("status_stage24_sector_prefix")
    x86.emit_asciiz(pe, "\r\nFloor target sector: ")
    pe.label("status_stage24_floor_prefix")
    x86.emit_asciiz(pe, "\r\nFloor after bounded ticker: ")
    pe.label("status_stage24_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage24 floor signature: ")
    pe.label("status_stage24_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage24 preserves stage23 through stage19, then uses real MAP11 linedef 391. "
        "The bounded route reaches P_UseSpecialLine case 60, EV_DoFloor(lowerFloorToLowest), "
        "P_FindSectorFromLineTag, P_FindLowestFloorSurrounding, P_AddThinker, T_MoveFloor, "
        "and the floor branch of T_MovePlane. The floor reaches -48 and the following strict "
        "past-destination tic removes the thinker and counts the pstop sound boundary. "
        "Speaker output, broad floor families, platforms, ceilings, crushers, stairs, donuts, "
        "live input, progression, and later-stage work stay absent.\r\n",
    )
    for label, text in (
        ("title_stage24_map_prefix", " S24MAP="),
        ("title_stage24_line_prefix", " S24LINE="),
        ("title_stage24_special_prefix", " S24SPEC="),
        ("title_stage24_tag_prefix", " TAG24="),
        ("title_stage24_side_prefix", " SIDE24="),
        ("title_stage24_right_sidedef_prefix", " RSID24="),
        ("title_stage24_left_sidedef_prefix", " LSID24="),
        ("title_stage24_front_sector_prefix", " FSEC24="),
        ("title_stage24_slot_prefix", " SLOT24="),
        ("title_stage24_texture_before_prefix", " TEX240="),
        ("title_stage24_texture_pressed_prefix", " TEX241="),
        ("title_stage24_texture_restored_prefix", " TEX242="),
        ("title_stage24_pair_prefix", " PAIR24="),
        ("title_stage24_switch_index_prefix", " SWI24="),
        ("title_stage24_special_after_prefix", " SPC241="),
        ("title_stage24_button_slot_prefix", " BSLOT24="),
        ("title_stage24_timer0_prefix", " BT240="),
        ("title_stage24_timer1_prefix", " BT241="),
        ("title_stage24_button_restore_prefix", " BREST24="),
        ("title_stage24_button_clear_prefix", " BCLR24="),
        ("title_stage24_ev_prefix", " EVF24="),
        ("title_stage24_find_prefix", " TFIND24="),
        ("title_stage24_scan_prefix", " TITER24="),
        ("title_stage24_sector_prefix", " TSEC24="),
        ("title_stage24_floor0_prefix", " F240="),
        ("title_stage24_floor1_prefix", " F241="),
        ("title_stage24_ceiling_prefix", " C24="),
        ("title_stage24_special_sector_prefix", " SSPEC24="),
        ("title_stage24_low_prefix", " LOWF24="),
        ("title_stage24_dest_prefix", " DEST24="),
        ("title_stage24_direction_prefix", " DIR24="),
        ("title_stage24_speed_prefix", " SPD24="),
        ("title_stage24_add_prefix", " ADD24="),
        ("title_stage24_ticker_prefix", " PTIC24="),
        ("title_stage24_floor_ticks_prefix", " TMF24="),
        ("title_stage24_move_plane_prefix", " MP24="),
        ("title_stage24_mut_prefix", " FMUT24="),
        ("title_stage24_past_prefix", " PAST24="),
        ("title_stage24_remove_prefix", " REM24="),
        ("title_stage24_lazy_prefix", " LREM24="),
        ("title_stage24_move_sound_prefix", " MSND24="),
        ("title_stage24_stop_sound_prefix", " STOP24="),
        ("title_stage24_leveltime_prefix", " LT24="),
        ("title_stage24_order_prefix", " ORDER24="),
        ("title_stage24_audio_prefix", " AUD24="),
        ("title_stage24_gen_prefix", " GENF24="),
        ("title_stage24_plat_prefix", " GPLAT24="),
        ("title_stage24_ceil_prefix", " GCEIL24="),
        ("title_stage24_stage25_prefix", " S25ABS="),
        ("title_stage24_signature_prefix", " S24SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)


def build_source_stage24_first_floor_sector_special_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_stage24_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage24_load_wad_first_floor_sector_special_probe(pe)
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
    emit_render_first_floor_sector_special_probe_debug(pe)
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
    emit_append_stage24_success_status(pe)
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
    emit_stage24_data(pe)
    return pe.build("entry")


def write_source_stage24_first_floor_sector_special_probe_exe(path: str | Path) -> bytes:
    image = build_source_stage24_first_floor_sector_special_probe_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage24 first floor sector special PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage24_first_floor_sector_special_probe.exe",
        help="path to write, default: build/source_stage24_first_floor_sector_special_probe.exe",
    )
    args = parser.parse_args()
    write_source_stage24_first_floor_sector_special_probe_exe(args.output)


if __name__ == "__main__":
    main()
