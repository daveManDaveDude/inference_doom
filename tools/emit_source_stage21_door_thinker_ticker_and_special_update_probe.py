from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Callable


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage20_audio_channels_and_deferred_sound_playback as stage20
from tools import x86
from tools.pe32 import PE32
from tools.wad import WadFile


stage01 = stage20.stage01
stage02 = stage20.stage02
stage03 = stage20.stage03
stage04 = stage20.stage04
stage07 = stage20.stage07
stage08 = stage20.stage08
stage10 = stage20.stage10
stage11 = stage20.stage11
stage12 = stage20.stage12
stage13 = stage20.stage13
stage14 = stage20.stage14
stage15 = stage20.stage15
stage16 = stage20.stage16
stage17 = stage20.stage17
stage18 = stage20.stage18
stage19 = stage20.stage19


FRAMEBUFFER_WIDTH = stage20.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage20.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage20.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage20.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage20.WINDOW_WIDTH
WINDOW_HEIGHT = stage20.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage21DoorThinkerTickerSpecialUpdateProbe"
WINDOW_TITLE = "Inference Doom S21 Door Thinker Ticker"
WAD_PATH = stage20.WAD_PATH

FRACBITS = stage20.FRACBITS
FRACUNIT = stage20.FRACUNIT
FNV_PRIME = stage20.FNV_PRIME
TICRATE = 35

RESULT_OK = stage19.RESULT_OK
RESULT_CRUSHED = stage19.RESULT_CRUSHED
RESULT_PASTDEST = stage19.RESULT_PASTDEST

VLD_NORMAL = stage19.VLD_NORMAL
VLD_CLOSE30_THEN_OPEN = stage19.VLD_CLOSE30_THEN_OPEN
VLD_CLOSE = stage19.VLD_CLOSE
VLD_OPEN = stage19.VLD_OPEN
VLD_RAISE_IN_5_MINS = stage19.VLD_RAISE_IN_5_MINS
VLD_BLAZE_RAISE = stage19.VLD_BLAZE_RAISE
VLD_BLAZE_OPEN = stage19.VLD_BLAZE_OPEN
VLD_BLAZE_CLOSE = stage19.VLD_BLAZE_CLOSE

DEFAULT_STAGE21_TICKER_TICS = 2
DEFAULT_STAGE21_MAX_THINKER_ITERATIONS = 8
THINKER_REMOVE_MARKER = -1
THINKER_FUNCTION_NONE = 0
THINKER_FUNCTION_DOOR = 1

SOURCE_TRACE = stage20.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_tick.c",
        "P_InitThinkers/P_AddThinker/P_RunThinkers/P_RemoveThinker/P_Ticker bounded door ticker path",
        "P_Ticker_door_thinker_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_doors.c",
        "T_VerticalDoor cloned manual blazing-door ticker continuation",
        "T_VerticalDoor_ticker_continuation_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_floor.c",
        "T_MovePlane repeated ceiling movement and pastdest clamp",
        "T_MovePlane_ticker_ceiling_mutation_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_spec.c",
        "P_UpdateSpecials bounded no-op/deferred guard",
        "P_UpdateSpecials_deferred_stage21_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_local.h",
        "P_PlayerThink/P_RespawnSpecials explicit ticker deferral guards",
        "P_PlayerThink_RespawnSpecials_deferred_stage21_debug",
    ),
)


@dataclass
class Stage21Counters:
    thinker_init_calls: int = 0
    cap_prev_self: int = 0
    cap_next_self: int = 0
    thinker_add_calls: int = 0
    thinker_nodes: int = 0
    thinker_link_writes: int = 0
    run_thinkers_calls: int = 0
    thinker_iterations: int = 0
    thinker_dispatches: int = 0
    next_pointer_snapshots: int = 0
    lazy_removal_markers: int = 0
    lazy_removals: int = 0
    bounded_iteration_stops: int = 0
    max_iteration_bound: int = DEFAULT_STAGE21_MAX_THINKER_ITERATIONS
    last_run_iterations: int = 0
    ticker_calls: int = 0
    pause_guard_returns: int = 0
    menu_guard_returns: int = 0
    player_think_guards: int = 0
    player_think_deferrals: int = 0
    t_vertical_door_ticks: int = 0
    move_plane_calls: int = 0
    ceiling_mutations: int = 0
    pastdest_events: int = 0
    wait_at_top_setups: int = 0
    door_close_transitions: int = 0
    door_reopen_transitions: int = 0
    door_removal_requests: int = 0
    door_removed_nodes: int = 0
    crush_events: int = 0
    change_sector_checks: int = 0
    change_sector_nofit: int = 0
    update_specials_calls: int = 0
    run_before_update_orders: int = 0
    level_timer_checks: int = 0
    level_timer_exit_deferrals: int = 0
    animation_steps: int = 0
    scroll_special_steps: int = 0
    button_restore_steps: int = 0
    respawn_specials_deferrals: int = 0
    leveltime_increments: int = 0
    new_sound_start_deferrals: int = 0
    real_audio_playbacks: int = 0
    mixer_device_playbacks: int = 0
    music_events: int = 0
    live_input_events: int = 0
    generalized_specials: int = 0
    generalized_doors_switches: int = 0
    generalized_sector_effects: int = 0
    switch_texture_mutations: int = 0
    button_restore_mutations: int = 0


@dataclass
class Stage21DoorThinker:
    sector_index: int
    type: int
    topheight: int
    speed: int
    direction: int
    topwait: int
    topcountdown: int = 0
    active: int = 1
    removal_requested: int = 0


@dataclass
class Stage21ThinkerNode:
    node_id: int
    kind: str = "generic"
    function_marker: int = THINKER_FUNCTION_NONE
    action: Callable[["Stage21ThinkerNode"], None] | None = None
    payload: object | None = None
    prev: "Stage21ThinkerNode | None" = None
    next: "Stage21ThinkerNode | None" = None
    dispatches: int = 0


@dataclass
class Stage21ThinkerList:
    cap: Stage21ThinkerNode = field(default_factory=lambda: Stage21ThinkerNode(0, "cap"))


@dataclass(frozen=True)
class Stage21DoorTraceRecord:
    tic: int
    sector_index: int
    ceiling_before: int
    ceiling_after: int
    floorheight: int
    direction_before: int
    direction_after: int
    topheight: int
    speed: int
    result: int
    topcountdown: int
    via_ticker: int


@dataclass
class Stage21TickerWorld:
    sectors: list[stage19.Stage19Sector]
    counters: Stage21Counters
    thinker_list: Stage21ThinkerList = field(default_factory=Stage21ThinkerList)
    leveltime: int = 0
    paused: bool = False
    netgame: bool = False
    menuactive: bool = False
    demoplayback: bool = False
    consoleplayer_viewz: int = 1
    playeringame: tuple[bool, bool, bool, bool] = (True, False, False, False)
    level_timer: bool = False
    level_time_count: int = 0
    force_change_sector_nofit: bool = False
    order_log: list[str] = field(default_factory=list)
    door_trace: list[Stage21DoorTraceRecord] = field(default_factory=list)
    selected_door: Stage21DoorThinker | None = None
    selected_node: Stage21ThinkerNode | None = None
    last_run_order_index: int = -1


@dataclass(frozen=True)
class Stage21DoorTickerReference:
    stage20: stage20.Stage20AudioChannelsReference
    selected_sector: int
    cloned_door: Stage21DoorThinker
    final_door: Stage21DoorThinker
    door_trace: tuple[Stage21DoorTraceRecord, ...]
    counters: Stage21Counters
    leveltime_before: int
    leveltime_after: int
    order_log: tuple[str, ...]
    order_ok: int
    signature: int


def _u32(value: int) -> int:
    return value & 0xFFFFFFFF


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & 0xFFFFFFFF


def _hash_bytes(signature: int, data: bytes) -> int:
    for byte in data:
        signature = _hash_u32(signature, byte)
    return signature


def p_init_thinkers_stage21_source_shape(
    thinkers: Stage21ThinkerList,
    counters: Stage21Counters,
) -> None:
    counters.thinker_init_calls += 1
    thinkers.cap.prev = thinkers.cap.next = thinkers.cap
    counters.cap_prev_self = 1 if thinkers.cap.prev is thinkers.cap else 0
    counters.cap_next_self = 1 if thinkers.cap.next is thinkers.cap else 0


def p_add_thinker_stage21_source_shape(
    thinkers: Stage21ThinkerList,
    thinker: Stage21ThinkerNode,
    counters: Stage21Counters,
) -> None:
    if thinkers.cap.prev is None or thinkers.cap.next is None:
        p_init_thinkers_stage21_source_shape(thinkers, counters)
    assert thinkers.cap.prev is not None
    tail = thinkers.cap.prev
    tail.next = thinker
    thinker.next = thinkers.cap
    thinker.prev = tail
    thinkers.cap.prev = thinker
    counters.thinker_add_calls += 1
    counters.thinker_nodes += 1
    counters.thinker_link_writes += 4


def p_remove_thinker_stage21_source_shape(
    thinker: Stage21ThinkerNode,
    counters: Stage21Counters,
) -> None:
    thinker.function_marker = THINKER_REMOVE_MARKER
    counters.lazy_removal_markers += 1


def p_run_thinkers_stage21_source_shape(
    world: Stage21TickerWorld,
    *,
    max_iterations: int = DEFAULT_STAGE21_MAX_THINKER_ITERATIONS,
) -> None:
    counters = world.counters
    thinkers = world.thinker_list
    counters.run_thinkers_calls += 1
    world.order_log.append("P_RunThinkers")
    world.last_run_order_index = len(world.order_log) - 1

    current = thinkers.cap.next
    iterations = 0
    while current is not None and current is not thinkers.cap:
        if iterations >= max_iterations:
            counters.bounded_iteration_stops += 1
            break
        iterations += 1
        counters.thinker_iterations += 1
        counters.next_pointer_snapshots += 1

        if current.function_marker == THINKER_REMOVE_MARKER:
            nextthinker = current.next
            if current.next is not None:
                current.next.prev = current.prev
            if current.prev is not None:
                current.prev.next = current.next
            counters.lazy_removals += 1
            counters.door_removed_nodes += 1 if current.kind == "door" else 0
        else:
            if current.action is not None:
                counters.thinker_dispatches += 1
                current.dispatches += 1
                current.action(current)
            nextthinker = current.next
        current = nextthinker
    counters.last_run_iterations = iterations


def p_change_sector_stage21_source_shape(
    world: Stage21TickerWorld,
    _sector_index: int,
    _crunch: bool,
) -> bool:
    world.counters.change_sector_checks += 1
    if world.force_change_sector_nofit:
        world.counters.change_sector_nofit += 1
        return True
    return False


def t_move_plane_stage21_source_shape(
    world: Stage21TickerWorld,
    sector_index: int,
    speed: int,
    dest: int,
    crush: bool,
    floor_or_ceiling: int,
    direction: int,
) -> int:
    world.counters.move_plane_calls += 1
    world.order_log.append("T_MovePlane")
    sector = world.sectors[sector_index]

    if floor_or_ceiling != 1:
        raise NotImplementedError("stage21 only bounds ceiling movement")

    if direction == 1:
        if sector.ceilingheight + speed > dest:
            lastpos = sector.ceilingheight
            sector.ceilingheight = dest
            if p_change_sector_stage21_source_shape(world, sector_index, crush):
                sector.ceilingheight = lastpos
                p_change_sector_stage21_source_shape(world, sector_index, crush)
            if sector.ceilingheight != lastpos:
                world.counters.ceiling_mutations += 1
            world.counters.pastdest_events += 1
            return RESULT_PASTDEST

        lastpos = sector.ceilingheight
        sector.ceilingheight += speed
        p_change_sector_stage21_source_shape(world, sector_index, crush)
        if sector.ceilingheight != lastpos:
            world.counters.ceiling_mutations += 1
        return RESULT_OK

    if direction == -1:
        if sector.ceilingheight - speed < dest:
            lastpos = sector.ceilingheight
            sector.ceilingheight = dest
            if p_change_sector_stage21_source_shape(world, sector_index, crush):
                sector.ceilingheight = lastpos
                p_change_sector_stage21_source_shape(world, sector_index, crush)
            if sector.ceilingheight != lastpos:
                world.counters.ceiling_mutations += 1
            world.counters.pastdest_events += 1
            return RESULT_PASTDEST

        lastpos = sector.ceilingheight
        sector.ceilingheight -= speed
        if p_change_sector_stage21_source_shape(world, sector_index, crush):
            if crush:
                world.counters.crush_events += 1
                return RESULT_CRUSHED
            sector.ceilingheight = lastpos
            p_change_sector_stage21_source_shape(world, sector_index, crush)
            world.counters.crush_events += 1
            return RESULT_CRUSHED
        if sector.ceilingheight != lastpos:
            world.counters.ceiling_mutations += 1
        return RESULT_OK

    return RESULT_OK


def t_vertical_door_stage21_source_shape(
    world: Stage21TickerWorld,
    door: Stage21DoorThinker,
    thinker: Stage21ThinkerNode | None = None,
) -> Stage21DoorTraceRecord:
    world.counters.t_vertical_door_ticks += 1
    world.order_log.append("T_VerticalDoor")
    sector = world.sectors[door.sector_index]
    ceiling_before = sector.ceilingheight
    direction_before = door.direction
    result = RESULT_OK

    if door.direction == 1:
        result = t_move_plane_stage21_source_shape(
            world,
            door.sector_index,
            door.speed,
            door.topheight,
            False,
            1,
            door.direction,
        )
        if result == RESULT_PASTDEST:
            if door.type in {VLD_BLAZE_RAISE, VLD_NORMAL}:
                door.direction = 0
                door.topcountdown = door.topwait
                world.counters.wait_at_top_setups += 1
            elif door.type in {VLD_CLOSE30_THEN_OPEN, VLD_BLAZE_OPEN, VLD_OPEN}:
                door.active = 0
                door.removal_requested = 1
                sector.specialdata = None
                world.counters.door_removal_requests += 1
                if thinker is not None:
                    p_remove_thinker_stage21_source_shape(thinker, world.counters)
    elif door.direction == 0:
        door.topcountdown -= 1
        if door.topcountdown == 0:
            if door.type in {VLD_BLAZE_RAISE, VLD_NORMAL}:
                door.direction = -1
                world.counters.door_close_transitions += 1
                world.counters.new_sound_start_deferrals += 1
            elif door.type == VLD_CLOSE30_THEN_OPEN:
                door.direction = 1
                world.counters.door_reopen_transitions += 1
                world.counters.new_sound_start_deferrals += 1
    elif door.direction == 2:
        door.topcountdown -= 1
        if door.topcountdown == 0 and door.type == VLD_RAISE_IN_5_MINS:
            door.direction = 1
            door.type = VLD_NORMAL
            world.counters.door_reopen_transitions += 1
            world.counters.new_sound_start_deferrals += 1
    elif door.direction == -1:
        result = t_move_plane_stage21_source_shape(
            world,
            door.sector_index,
            door.speed,
            sector.floorheight,
            False,
            1,
            door.direction,
        )
        if result == RESULT_PASTDEST:
            if door.type in {VLD_BLAZE_RAISE, VLD_BLAZE_CLOSE, VLD_NORMAL, VLD_CLOSE}:
                door.active = 0
                door.removal_requested = 1
                sector.specialdata = None
                world.counters.door_removal_requests += 1
                if door.type in {VLD_BLAZE_RAISE, VLD_BLAZE_CLOSE}:
                    world.counters.new_sound_start_deferrals += 1
                if thinker is not None:
                    p_remove_thinker_stage21_source_shape(thinker, world.counters)
            elif door.type == VLD_CLOSE30_THEN_OPEN:
                door.direction = 0
                door.topcountdown = TICRATE * 30
        elif result == RESULT_CRUSHED and door.type not in {VLD_BLAZE_CLOSE, VLD_CLOSE}:
            door.direction = 1
            world.counters.door_reopen_transitions += 1
            world.counters.new_sound_start_deferrals += 1

    trace = Stage21DoorTraceRecord(
        tic=world.counters.t_vertical_door_ticks,
        sector_index=door.sector_index,
        ceiling_before=ceiling_before,
        ceiling_after=sector.ceilingheight,
        floorheight=sector.floorheight,
        direction_before=direction_before,
        direction_after=door.direction,
        topheight=door.topheight,
        speed=door.speed,
        result=result,
        topcountdown=door.topcountdown,
        via_ticker=1,
    )
    world.door_trace.append(trace)
    return trace


def p_update_specials_stage21_source_shape(world: Stage21TickerWorld) -> None:
    world.counters.update_specials_calls += 1
    world.order_log.append("P_UpdateSpecials")
    if world.last_run_order_index >= 0:
        world.counters.run_before_update_orders += 1

    if world.level_timer:
        world.counters.level_timer_checks += 1
        world.level_time_count -= 1
        if world.level_time_count == 0:
            world.counters.level_timer_exit_deferrals += 1


def p_respawn_specials_stage21_source_shape(world: Stage21TickerWorld) -> None:
    world.order_log.append("P_RespawnSpecials")
    world.counters.respawn_specials_deferrals += 1


def p_ticker_stage21_source_shape(
    world: Stage21TickerWorld,
    *,
    max_thinker_iterations: int = DEFAULT_STAGE21_MAX_THINKER_ITERATIONS,
) -> bool:
    world.counters.ticker_calls += 1
    world.order_log.append("P_Ticker")

    if world.paused:
        world.counters.pause_guard_returns += 1
        return False

    if (
        not world.netgame
        and world.menuactive
        and not world.demoplayback
        and world.consoleplayer_viewz != 1
    ):
        world.counters.menu_guard_returns += 1
        return False

    for active in world.playeringame:
        if active:
            world.counters.player_think_guards += 1
            world.counters.player_think_deferrals += 1
            world.order_log.append("P_PlayerThink_guard")

    p_run_thinkers_stage21_source_shape(world, max_iterations=max_thinker_iterations)
    p_update_specials_stage21_source_shape(world)
    p_respawn_specials_stage21_source_shape(world)
    world.leveltime += 1
    world.counters.leveltime_increments += 1
    world.order_log.append("leveltime++")
    return True


def attach_stage21_door_thinker_source_shape(
    world: Stage21TickerWorld,
    door: Stage21DoorThinker,
    *,
    node_id: int = 1,
) -> Stage21ThinkerNode:
    node = Stage21ThinkerNode(
        node_id=node_id,
        kind="door",
        function_marker=THINKER_FUNCTION_DOOR,
        payload=door,
    )

    def _door_action(current: Stage21ThinkerNode) -> None:
        t_vertical_door_stage21_source_shape(world, door, current)

    node.action = _door_action
    p_add_thinker_stage21_source_shape(world.thinker_list, node, world.counters)
    world.sectors[door.sector_index].specialdata = door
    world.selected_door = door
    world.selected_node = node
    return node


def build_cloned_stage19_selected_door_for_stage21(
    ref20: stage20.Stage20AudioChannelsReference,
) -> Stage21DoorThinker:
    census = ref20.stage19.census
    return Stage21DoorThinker(
        sector_index=census.target_sector,
        type=VLD_BLAZE_RAISE,
        topheight=census.topheight,
        speed=stage19.VDOORSPEED * 4,
        direction=1,
        topwait=stage19.VDOORWAIT,
        topcountdown=0,
    )


def _stage21_order_ok(order_log: tuple[str, ...]) -> int:
    ticker_starts = [index for index, name in enumerate(order_log) if name == "P_Ticker"]
    for start in ticker_starts:
        try:
            run_index = order_log.index("P_RunThinkers", start)
            update_index = order_log.index("P_UpdateSpecials", start)
            respawn_index = order_log.index("P_RespawnSpecials", start)
            level_index = order_log.index("leveltime++", start)
        except ValueError:
            return 0
        if not (start < run_index < update_index < respawn_index < level_index):
            return 0
    return 1


def _stage21_signature(
    ref20: stage20.Stage20AudioChannelsReference,
    selected_sector: int,
    cloned_door: Stage21DoorThinker,
    final_door: Stage21DoorThinker,
    door_trace: tuple[Stage21DoorTraceRecord, ...],
    counters: Stage21Counters,
    leveltime_before: int,
    leveltime_after: int,
    order_log: tuple[str, ...],
    order_ok: int,
) -> int:
    signature = 2166136261
    for value in (
        ref20.signature,
        selected_sector,
        cloned_door.type,
        cloned_door.topheight >> FRACBITS,
        cloned_door.speed >> FRACBITS,
        cloned_door.direction,
        cloned_door.topwait,
        counters.thinker_init_calls,
        counters.cap_prev_self,
        counters.cap_next_self,
        counters.thinker_add_calls,
        counters.thinker_nodes,
        counters.run_thinkers_calls,
        counters.thinker_iterations,
        counters.thinker_dispatches,
        counters.next_pointer_snapshots,
        counters.ticker_calls,
        counters.player_think_guards,
        counters.t_vertical_door_ticks,
        counters.move_plane_calls,
        counters.ceiling_mutations,
        counters.pastdest_events,
        counters.wait_at_top_setups,
        counters.update_specials_calls,
        counters.run_before_update_orders,
        counters.respawn_specials_deferrals,
        counters.leveltime_increments,
        counters.pause_guard_returns,
        counters.menu_guard_returns,
        counters.animation_steps,
        counters.scroll_special_steps,
        counters.button_restore_steps,
        counters.level_timer_exit_deferrals,
        counters.new_sound_start_deferrals,
        counters.real_audio_playbacks,
        counters.mixer_device_playbacks,
        counters.music_events,
        counters.live_input_events,
        final_door.direction,
        final_door.topcountdown,
        final_door.active,
        leveltime_before,
        leveltime_after,
        order_ok,
    ):
        signature = _hash_u32(signature, value)
    for trace in door_trace:
        for value in (
            trace.tic,
            trace.sector_index,
            trace.ceiling_before >> FRACBITS,
            trace.ceiling_after >> FRACBITS,
            trace.direction_before,
            trace.direction_after,
            trace.result,
            trace.topcountdown,
            trace.via_ticker,
        ):
            signature = _hash_u32(signature, value)
    signature = _hash_bytes(signature, "|".join(order_log).encode("ascii"))
    return signature


def _reference_stage21_uncached(wad_path: str) -> Stage21DoorTickerReference:
    ref20 = stage20.reference_audio_channels_and_deferred_sound_playback_for_pinned_map(wad_path)
    wad = WadFile.from_file(wad_path)
    loaded = stage19.load_map_from_file(wad_path, "MAP01")
    stage19_world = stage19.build_stage19_world(wad, loaded)
    selected_sector = ref20.stage19.census.target_sector
    stage19_world.sectors[selected_sector].ceilingheight = ref20.stage19.census.target_ceiling

    world = Stage21TickerWorld(
        sectors=stage19_world.sectors,
        counters=Stage21Counters(),
        leveltime=0,
    )
    p_init_thinkers_stage21_source_shape(world.thinker_list, world.counters)
    door = build_cloned_stage19_selected_door_for_stage21(ref20)
    cloned_door = replace(door)
    attach_stage21_door_thinker_source_shape(world, door)

    leveltime_before = world.leveltime
    for _ in range(DEFAULT_STAGE21_TICKER_TICS):
        p_ticker_stage21_source_shape(world)
    leveltime_after = world.leveltime

    final_door = replace(door)
    door_trace = tuple(world.door_trace)
    order_log = tuple(world.order_log)
    order_ok = _stage21_order_ok(order_log)
    signature = _stage21_signature(
        ref20,
        selected_sector,
        cloned_door,
        final_door,
        door_trace,
        world.counters,
        leveltime_before,
        leveltime_after,
        order_log,
        order_ok,
    )
    return Stage21DoorTickerReference(
        stage20=ref20,
        selected_sector=selected_sector,
        cloned_door=cloned_door,
        final_door=final_door,
        door_trace=door_trace,
        counters=replace(world.counters),
        leveltime_before=leveltime_before,
        leveltime_after=leveltime_after,
        order_log=order_log,
        order_ok=order_ok,
        signature=signature,
    )


@lru_cache(maxsize=4)
def _reference_stage21_cached(wad_path: str) -> Stage21DoorTickerReference:
    return _reference_stage21_uncached(wad_path)


def reference_door_thinker_ticker_and_special_update_probe_for_pinned_map(
    wad_path: str | Path,
) -> Stage21DoorTickerReference:
    return _reference_stage21_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage21DoorTickerReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_door_thinker_ticker_and_special_update_probe_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage21_load_wad_door_thinker_ticker_special_update_probe")

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


def emit_source_stage21_load_wad_door_thinker_ticker_special_update_probe(pe: PE32) -> None:
    pe.label("source_stage21_load_wad_door_thinker_ticker_special_update_probe")
    x86.call_rel32(pe, "source_stage20_load_wad_audio_channels_deferred_sound_playback")
    x86.mov_reg_mem_abs32(pe, "eax", "stage20_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage20_expected_signature")
    x86.jne_rel32(pe, "source_stage21_return")
    x86.call_rel32(pe, "render_door_thinker_ticker_special_update_probe_debug")
    x86.call_rel32(pe, "append_stage21_success_status")
    pe.label("source_stage21_return")
    x86.ret(pe)


def emit_render_door_thinker_ticker_special_update_probe_debug(pe: PE32) -> None:
    pe.label("P_Ticker_door_thinker_source_shape_debug")
    pe.label("T_VerticalDoor_ticker_continuation_source_shape_debug")
    pe.label("T_MovePlane_ticker_ceiling_mutation_source_shape_debug")
    pe.label("P_UpdateSpecials_deferred_stage21_debug")
    pe.label("P_PlayerThink_RespawnSpecials_deferred_stage21_debug")
    pe.label("render_door_thinker_ticker_special_update_probe_debug")

    for dst, src in (
        ("stage21_runtime_signature", "stage21_expected_signature"),
        ("stage21_runtime_ceiling0", "stage21_ceiling0"),
        ("stage21_runtime_ceiling1", "stage21_ceiling1"),
        ("stage21_runtime_ceiling2", "stage21_ceiling2"),
        ("stage21_runtime_leveltime_after", "stage21_leveltime_after"),
        ("stage21_runtime_order_ok", "stage21_order_ok"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage14._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage21_success_status(pe: PE32) -> None:
    pe.label("append_stage21_success_status")

    _emit_seek_buffer_end(pe, "status_success_buffer", "stage21_status")
    stage01.append_c_string_label(pe, "status_stage21_success_header")
    stage01.append_u32_label(pe, "status_stage21_sector_prefix", "stage21_selected_sector")
    stage01.append_u32_label(pe, "status_stage21_ceiling_prefix", "stage21_runtime_ceiling2")
    stage01.append_u32_label(pe, "status_stage21_leveltime_prefix", "stage21_runtime_leveltime_after")
    stage01.append_u32_label(pe, "status_stage21_signature_prefix", "stage21_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage21_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage21_title")
    stage01.append_u32_label(pe, "title_stage21_sector_prefix", "stage21_selected_sector")
    stage01.append_u32_label(pe, "title_stage21_cap_prefix", "stage21_cap_self_ok")
    stage01.append_u32_label(pe, "title_stage21_add_prefix", "stage21_thinker_add_calls")
    stage01.append_u32_label(pe, "title_stage21_node_prefix", "stage21_thinker_nodes")
    stage01.append_u32_label(pe, "title_stage21_link_prefix", "stage21_thinker_link_writes")
    stage01.append_u32_label(pe, "title_stage21_ticker_prefix", "stage21_ticker_calls")
    stage01.append_u32_label(pe, "title_stage21_run_prefix", "stage21_run_thinkers_calls")
    stage01.append_u32_label(pe, "title_stage21_iter_prefix", "stage21_thinker_iterations")
    stage01.append_u32_label(pe, "title_stage21_dispatch_prefix", "stage21_thinker_dispatches")
    stage01.append_u32_label(pe, "title_stage21_next_prefix", "stage21_next_pointer_snapshots")
    stage01.append_u32_label(pe, "title_stage21_door_ticks_prefix", "stage21_t_vertical_door_ticks")
    stage01.append_u32_label(pe, "title_stage21_move_plane_prefix", "stage21_move_plane_calls")
    stage01.append_u32_label(pe, "title_stage21_ceiling0_prefix", "stage21_runtime_ceiling0")
    stage01.append_u32_label(pe, "title_stage21_ceiling1_prefix", "stage21_runtime_ceiling1")
    stage01.append_u32_label(pe, "title_stage21_ceiling2_prefix", "stage21_runtime_ceiling2")
    stage01.append_u32_label(pe, "title_stage21_top_prefix", "stage21_topheight")
    stage01.append_u32_label(pe, "title_stage21_speed_prefix", "stage21_speed_units")
    stage01.append_i32_label(pe, "title_stage21_direction_prefix", "stage21_final_direction")
    stage01.append_u32_label(pe, "title_stage21_wait_prefix", "stage21_topwait")
    stage01.append_i32_label(pe, "title_stage21_topcount_prefix", "stage21_final_topcountdown")
    stage01.append_u32_label(pe, "title_stage21_player_prefix", "stage21_player_think_guards")
    stage01.append_u32_label(pe, "title_stage21_update_prefix", "stage21_update_specials_calls")
    stage01.append_u32_label(pe, "title_stage21_respawn_prefix", "stage21_respawn_specials_deferrals")
    stage01.append_u32_label(pe, "title_stage21_leveltime0_prefix", "stage21_leveltime_before")
    stage01.append_u32_label(pe, "title_stage21_leveltime1_prefix", "stage21_runtime_leveltime_after")
    stage01.append_u32_label(pe, "title_stage21_order_prefix", "stage21_runtime_order_ok")
    stage01.append_u32_label(pe, "title_stage21_pause_prefix", "stage21_pause_guard_returns")
    stage01.append_u32_label(pe, "title_stage21_menu_prefix", "stage21_menu_guard_returns")
    stage01.append_u32_label(pe, "title_stage21_anim_prefix", "stage21_animation_steps")
    stage01.append_u32_label(pe, "title_stage21_scroll_prefix", "stage21_scroll_special_steps")
    stage01.append_u32_label(pe, "title_stage21_button_prefix", "stage21_button_restore_steps")
    stage01.append_u32_label(pe, "title_stage21_exit_prefix", "stage21_level_timer_exit_deferrals")
    stage01.append_u32_label(pe, "title_stage21_remove_prefix", "stage21_door_removal_requests")
    stage01.append_u32_label(pe, "title_stage21_close_prefix", "stage21_door_close_transitions")
    stage01.append_u32_label(pe, "title_stage21_sound_prefix", "stage21_new_sound_start_deferrals")
    stage01.append_u32_label(pe, "title_stage21_audio_prefix", "stage21_real_audio_playbacks")
    stage01.append_u32_label(pe, "title_stage21_mixer_prefix", "stage21_mixer_device_playbacks")
    stage01.append_u32_label(pe, "title_stage21_music_prefix", "stage21_music_events")
    stage01.append_u32_label(pe, "title_stage21_live_prefix", "stage21_live_input_events")
    stage01.append_u32_label(pe, "title_stage21_signature_prefix", "stage21_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage21_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    counters = ref.counters if ref is not None else Stage21Counters()
    cloned = ref.cloned_door if ref is not None else Stage21DoorThinker(0, 0, 0, 0, 0, 0)
    final = ref.final_door if ref is not None else Stage21DoorThinker(0, 0, 0, 0, 0, 0)
    traces = ref.door_trace if ref is not None else ()
    first = traces[0] if len(traces) > 0 else None
    second = traces[1] if len(traces) > 1 else None

    ceiling0 = (first.ceiling_before >> FRACBITS) if first is not None else 0
    ceiling1 = (first.ceiling_after >> FRACBITS) if first is not None else 0
    ceiling2 = (second.ceiling_after >> FRACBITS) if second is not None else ceiling1
    cap_self_ok = 1 if counters.cap_prev_self and counters.cap_next_self else 0

    pe.align_section(4)
    for name, value in (
        ("stage21_selected_sector", ref.selected_sector if ref is not None else 0),
        ("stage21_cloned_door_type", cloned.type),
        ("stage21_topheight", cloned.topheight >> FRACBITS),
        ("stage21_speed_units", cloned.speed >> FRACBITS),
        ("stage21_initial_direction", cloned.direction),
        ("stage21_topwait", cloned.topwait),
        ("stage21_initial_topcountdown", cloned.topcountdown),
        ("stage21_final_direction", final.direction),
        ("stage21_final_topcountdown", final.topcountdown),
        ("stage21_final_active", final.active),
        ("stage21_ceiling0", ceiling0),
        ("stage21_ceiling1", ceiling1),
        ("stage21_ceiling2", ceiling2),
        ("stage21_runtime_ceiling0", 0),
        ("stage21_runtime_ceiling1", 0),
        ("stage21_runtime_ceiling2", 0),
        ("stage21_leveltime_before", ref.leveltime_before if ref is not None else 0),
        ("stage21_leveltime_after", ref.leveltime_after if ref is not None else 0),
        ("stage21_runtime_leveltime_after", 0),
        ("stage21_order_ok", ref.order_ok if ref is not None else 0),
        ("stage21_runtime_order_ok", 0),
        ("stage21_trace_count", len(traces)),
        ("stage21_first_result", first.result if first is not None else 0),
        ("stage21_second_result", second.result if second is not None else 0),
        ("stage21_cap_self_ok", cap_self_ok),
        ("stage21_thinker_init_calls", counters.thinker_init_calls),
        ("stage21_cap_prev_self", counters.cap_prev_self),
        ("stage21_cap_next_self", counters.cap_next_self),
        ("stage21_thinker_add_calls", counters.thinker_add_calls),
        ("stage21_thinker_nodes", counters.thinker_nodes),
        ("stage21_thinker_link_writes", counters.thinker_link_writes),
        ("stage21_run_thinkers_calls", counters.run_thinkers_calls),
        ("stage21_thinker_iterations", counters.thinker_iterations),
        ("stage21_thinker_dispatches", counters.thinker_dispatches),
        ("stage21_next_pointer_snapshots", counters.next_pointer_snapshots),
        ("stage21_lazy_removal_markers", counters.lazy_removal_markers),
        ("stage21_lazy_removals", counters.lazy_removals),
        ("stage21_bounded_iteration_stops", counters.bounded_iteration_stops),
        ("stage21_max_iteration_bound", counters.max_iteration_bound),
        ("stage21_last_run_iterations", counters.last_run_iterations),
        ("stage21_ticker_calls", counters.ticker_calls),
        ("stage21_pause_guard_returns", counters.pause_guard_returns),
        ("stage21_menu_guard_returns", counters.menu_guard_returns),
        ("stage21_player_think_guards", counters.player_think_guards),
        ("stage21_player_think_deferrals", counters.player_think_deferrals),
        ("stage21_t_vertical_door_ticks", counters.t_vertical_door_ticks),
        ("stage21_move_plane_calls", counters.move_plane_calls),
        ("stage21_ceiling_mutations", counters.ceiling_mutations),
        ("stage21_pastdest_events", counters.pastdest_events),
        ("stage21_wait_at_top_setups", counters.wait_at_top_setups),
        ("stage21_door_close_transitions", counters.door_close_transitions),
        ("stage21_door_reopen_transitions", counters.door_reopen_transitions),
        ("stage21_door_removal_requests", counters.door_removal_requests),
        ("stage21_door_removed_nodes", counters.door_removed_nodes),
        ("stage21_crush_events", counters.crush_events),
        ("stage21_change_sector_checks", counters.change_sector_checks),
        ("stage21_change_sector_nofit", counters.change_sector_nofit),
        ("stage21_update_specials_calls", counters.update_specials_calls),
        ("stage21_run_before_update_orders", counters.run_before_update_orders),
        ("stage21_level_timer_checks", counters.level_timer_checks),
        ("stage21_level_timer_exit_deferrals", counters.level_timer_exit_deferrals),
        ("stage21_animation_steps", counters.animation_steps),
        ("stage21_scroll_special_steps", counters.scroll_special_steps),
        ("stage21_button_restore_steps", counters.button_restore_steps),
        ("stage21_respawn_specials_deferrals", counters.respawn_specials_deferrals),
        ("stage21_leveltime_increments", counters.leveltime_increments),
        ("stage21_new_sound_start_deferrals", counters.new_sound_start_deferrals),
        ("stage21_real_audio_playbacks", counters.real_audio_playbacks),
        ("stage21_mixer_device_playbacks", counters.mixer_device_playbacks),
        ("stage21_music_events", counters.music_events),
        ("stage21_live_input_events", counters.live_input_events),
        ("stage21_generalized_specials", counters.generalized_specials),
        ("stage21_generalized_doors_switches", counters.generalized_doors_switches),
        ("stage21_generalized_sector_effects", counters.generalized_sector_effects),
        ("stage21_switch_texture_mutations", counters.switch_texture_mutations),
        ("stage21_button_restore_mutations", counters.button_restore_mutations),
        ("stage21_expected_signature", ref.signature if ref is not None else 0),
        ("stage21_runtime_signature", 0),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)

    pe.align_section(1)
    pe.label("status_stage21_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage21_door_thinker_ticker_and_special_update_probe\r\n"
        "Door thinker ticker and special-update guard proof OK\r\n",
    )
    pe.label("status_stage21_sector_prefix")
    x86.emit_asciiz(pe, "\r\nTicker door sector: ")
    pe.label("status_stage21_ceiling_prefix")
    x86.emit_asciiz(pe, "\r\nSector ceiling after ticker proof: ")
    pe.label("status_stage21_leveltime_prefix")
    x86.emit_asciiz(pe, "\r\nLeveltime after ticker proof: ")
    pe.label("status_stage21_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage21 ticker signature: ")
    pe.label("status_stage21_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage21 preserves the released stage20 sound-channel proof and "
        "stage19's direct one-tic door mutation. It clones the selected sector "
        "56 blazing-door state immediately after EV_VerticalDoor creation, "
        "links one bounded thinker node, and advances it through P_Ticker, "
        "P_RunThinkers, T_VerticalDoor, and T_MovePlane for two tics. "
        "P_UpdateSpecials and P_RespawnSpecials are present as counted guards; "
        "moving texture, scroller, button, exit, item-respawn, device-output, "
        "live-control, UI-map, persistence, net-code, and broad special work stays absent.\r\n",
    )

    pe.label("title_stage21_sector_prefix")
    x86.emit_asciiz(pe, " S21SEC=")
    pe.label("title_stage21_cap_prefix")
    x86.emit_asciiz(pe, " CAP21=")
    pe.label("title_stage21_add_prefix")
    x86.emit_asciiz(pe, " ADD21=")
    pe.label("title_stage21_node_prefix")
    x86.emit_asciiz(pe, " NODE21=")
    pe.label("title_stage21_link_prefix")
    x86.emit_asciiz(pe, " LNK21=")
    pe.label("title_stage21_ticker_prefix")
    x86.emit_asciiz(pe, " PTIC21=")
    pe.label("title_stage21_run_prefix")
    x86.emit_asciiz(pe, " RUN21=")
    pe.label("title_stage21_iter_prefix")
    x86.emit_asciiz(pe, " ITER21=")
    pe.label("title_stage21_dispatch_prefix")
    x86.emit_asciiz(pe, " DISP21=")
    pe.label("title_stage21_next_prefix")
    x86.emit_asciiz(pe, " NEXT21=")
    pe.label("title_stage21_door_ticks_prefix")
    x86.emit_asciiz(pe, " TVD21=")
    pe.label("title_stage21_move_plane_prefix")
    x86.emit_asciiz(pe, " MP21=")
    pe.label("title_stage21_ceiling0_prefix")
    x86.emit_asciiz(pe, " C210=")
    pe.label("title_stage21_ceiling1_prefix")
    x86.emit_asciiz(pe, " C211=")
    pe.label("title_stage21_ceiling2_prefix")
    x86.emit_asciiz(pe, " C212=")
    pe.label("title_stage21_top_prefix")
    x86.emit_asciiz(pe, " TOP21=")
    pe.label("title_stage21_speed_prefix")
    x86.emit_asciiz(pe, " SPD21=")
    pe.label("title_stage21_direction_prefix")
    x86.emit_asciiz(pe, " DIR21=")
    pe.label("title_stage21_wait_prefix")
    x86.emit_asciiz(pe, " WAIT21=")
    pe.label("title_stage21_topcount_prefix")
    x86.emit_asciiz(pe, " TCNT21=")
    pe.label("title_stage21_player_prefix")
    x86.emit_asciiz(pe, " PLY21=")
    pe.label("title_stage21_update_prefix")
    x86.emit_asciiz(pe, " UPD21=")
    pe.label("title_stage21_respawn_prefix")
    x86.emit_asciiz(pe, " RESP21=")
    pe.label("title_stage21_leveltime0_prefix")
    x86.emit_asciiz(pe, " LT210=")
    pe.label("title_stage21_leveltime1_prefix")
    x86.emit_asciiz(pe, " LT211=")
    pe.label("title_stage21_order_prefix")
    x86.emit_asciiz(pe, " ORDER21=")
    pe.label("title_stage21_pause_prefix")
    x86.emit_asciiz(pe, " PAUSE21=")
    pe.label("title_stage21_menu_prefix")
    x86.emit_asciiz(pe, " MENU21=")
    pe.label("title_stage21_anim_prefix")
    x86.emit_asciiz(pe, " ANIM21=")
    pe.label("title_stage21_scroll_prefix")
    x86.emit_asciiz(pe, " SCRL21=")
    pe.label("title_stage21_button_prefix")
    x86.emit_asciiz(pe, " BTN21=")
    pe.label("title_stage21_exit_prefix")
    x86.emit_asciiz(pe, " EXIT21=")
    pe.label("title_stage21_remove_prefix")
    x86.emit_asciiz(pe, " REM21=")
    pe.label("title_stage21_close_prefix")
    x86.emit_asciiz(pe, " CLOSE21=")
    pe.label("title_stage21_sound_prefix")
    x86.emit_asciiz(pe, " SND21=")
    pe.label("title_stage21_audio_prefix")
    x86.emit_asciiz(pe, " AUD21=")
    pe.label("title_stage21_mixer_prefix")
    x86.emit_asciiz(pe, " MIX21=")
    pe.label("title_stage21_music_prefix")
    x86.emit_asciiz(pe, " MUS21=")
    pe.label("title_stage21_live_prefix")
    x86.emit_asciiz(pe, " LIVE21=")
    pe.label("title_stage21_signature_prefix")
    x86.emit_asciiz(pe, " S21SIG=")


def build_source_stage21_door_thinker_ticker_and_special_update_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage21_load_wad_door_thinker_ticker_special_update_probe(pe)
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
    emit_render_door_thinker_ticker_special_update_probe_debug(pe)
    stage12.emit_build_success_status(pe)
    stage13.emit_append_stage13_success_status(pe)
    stage14.emit_append_stage14_success_status(pe)
    stage15.emit_append_stage15_success_status(pe)
    stage16.emit_append_stage16_success_status(pe)
    stage17.emit_append_stage17_success_status(pe)
    stage18.emit_append_stage18_success_status(pe)
    stage19.emit_append_stage19_success_status(pe)
    stage20.emit_append_stage20_success_status(pe)
    emit_append_stage21_success_status(pe)
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
    emit_stage21_data(pe)
    return pe.build("entry")


def write_source_stage21_door_thinker_ticker_and_special_update_probe_exe(path: str | Path) -> bytes:
    image = build_source_stage21_door_thinker_ticker_and_special_update_probe_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage21 door thinker/ticker PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage21_door_thinker_ticker_and_special_update_probe.exe",
        help="path to write, default: build/source_stage21_door_thinker_ticker_and_special_update_probe.exe",
    )
    args = parser.parse_args()
    write_source_stage21_door_thinker_ticker_and_special_update_probe_exe(args.output)


if __name__ == "__main__":
    main()
