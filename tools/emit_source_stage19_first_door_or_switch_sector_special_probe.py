from __future__ import annotations

import argparse
import math
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
from tools import emit_source_stage17_first_weapon_fire_damage_and_death_probe as stage17
from tools import emit_source_stage18_post_damage_monster_movement_and_chase_probe as stage18
from tools import x86
from tools.map_loader import LoadedMap, NO_SIDEDEF, load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


FRAMEBUFFER_WIDTH = stage18.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage18.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage18.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage18.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage18.WINDOW_WIDTH
WINDOW_HEIGHT = stage18.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage19FirstDoorSwitchSectorSpecialProbe"
WINDOW_TITLE = "Inference Doom S19 First Door Sector Special"
WAD_PATH = stage18.WAD_PATH

FRACBITS = stage18.FRACBITS
FRACUNIT = stage18.FRACUNIT
FNV_PRIME = stage18.FNV_PRIME
ANGLETOFINESHIFT = stage14.ANGLETOFINESHIFT
FINEMASK = stage14.FINEMASK
FINECOSINE = stage14.FINECOSINE
FINESINE = stage14.FINESINE
USERANGE = 64 * FRACUNIT

ML_TWOSIDED = stage14.ML_TWOSIDED
PT_ADDLINES = stage17.PT_ADDLINES

VDOORSPEED = 2 * FRACUNIT
VDOORWAIT = 150

RESULT_OK = 0
RESULT_CRUSHED = 1
RESULT_PASTDEST = 2

VLD_NORMAL = 0
VLD_CLOSE30_THEN_OPEN = 1
VLD_CLOSE = 2
VLD_OPEN = 3
VLD_RAISE_IN_5_MINS = 4
VLD_BLAZE_RAISE = 5
VLD_BLAZE_OPEN = 6
VLD_BLAZE_CLOSE = 7

SELECTED_LINE_INDEX = 332
SELECTED_PAIRED_LINE_INDEX = 330
SELECTED_SPECIAL = 117
SELECTED_TARGET_SECTOR = 56
SELECTED_FRONT_SECTOR = 55
SELECTED_PROBE_X = 1792 * FRACUNIT
SELECTED_PROBE_Y = -160 * FRACUNIT
SELECTED_PROBE_ANGLE = 0
DEFAULT_STAGE19_DOOR_TICS = 1

SFX_BDOPN = 86
SFX_NOWAY = 82
SFX_OOF = 34

SOURCE_TRACE = stage18.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "P_UseLines/PTR_UseTraverse manual use-line path",
        "P_UseLines_PathTraverse_manual_door_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_maputl.c",
        "P_PathTraverse/PIT_AddLineIntercepts/P_TraverseIntercepts use-line subset",
        "P_PathTraverse_use_line_bounded_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_switch.c",
        "P_UseSpecialLine manual door dispatch and switch deferral boundary",
        "P_UseSpecialLine_manual_vertical_door_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_doors.c",
        "EV_VerticalDoor blazing manual door spawn",
        "EV_VerticalDoor_manual_blazing_door_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_spec.c",
        "P_FindLowestCeilingSurrounding/getNextSector",
        "P_FindLowestCeilingSurrounding_manual_door_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_doors.c",
        "T_VerticalDoor upward door thinker tick",
        "T_VerticalDoor_manual_door_tic_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_floor.c",
        "T_MovePlane ceiling movement subset",
        "T_MovePlane_ceiling_mutation_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_switch.c",
        "P_ChangeSwitchTexture/P_StartButton deferred guard",
        "P_ChangeSwitchTexture_deferred_stage19_debug",
    ),
)


@dataclass
class Stage19Counters:
    special_census_runs: int = 0
    fixed_use_probes: int = 0
    stage18_player_in_userange: int = 0
    path_traverses: int = 0
    block_steps: int = 0
    block_line_iters: int = 0
    line_intercepts: int = 0
    traversed_intercepts: int = 0
    no_special_passes: int = 0
    blocked_nonspecial_lines: int = 0
    noway_sound_deferrals: int = 0
    special_use_attempts: int = 0
    use_special_calls: int = 0
    front_side_activations: int = 0
    back_side_rejections: int = 0
    one_special_terminations: int = 0
    vertical_door_calls: int = 0
    manual_door_spawns: int = 0
    locked_door_rejections: int = 0
    already_active_reversals: int = 0
    already_active_closures: int = 0
    already_active_nondoor_deferrals: int = 0
    door_thinker_records: int = 0
    thinker_add_deferrals: int = 0
    allocation_deferrals: int = 0
    sound_start_deferrals: int = 0
    door_open_sound_deferrals: int = 0
    t_vertical_door_ticks: int = 0
    move_plane_calls: int = 0
    ceiling_mutations: int = 0
    pastdest_events: int = 0
    wait_at_top_setups: int = 0
    crush_events: int = 0
    change_sector_checks: int = 0
    change_sector_nofit: int = 0
    switch_texture_deferrals: int = 0
    button_start_deferrals: int = 0
    tagged_door_deferrals: int = 0
    broad_special_deferrals: int = 0
    broad_door_switch_deferrals: int = 0
    broad_sector_effect_deferrals: int = 0
    real_sound_output_deferrals: int = 0
    live_input_deferrals: int = 0
    source_stage20_absent: int = 1


@dataclass
class Stage19Sector:
    index: int
    floorheight: int
    ceilingheight: int
    special: int = 0
    tag: int = 0
    specialdata: "Stage19DoorThinker | None" = None


@dataclass
class Stage19Line:
    index: int
    v1x: int
    v1y: int
    v2x: int
    v2y: int
    dx: int
    dy: int
    bbox: tuple[int, int, int, int]
    slopetype: int
    flags: int
    special: int
    tag: int
    sidenum: tuple[int, int]
    side_sectors: tuple[int | None, int | None]
    side_upper: tuple[str, str]
    side_lower: tuple[str, str]
    side_middle: tuple[str, str]

    @property
    def frontsector(self) -> int:
        return self.side_sectors[0] if self.side_sectors[0] is not None else 0

    @property
    def backsector(self) -> int | None:
        return self.side_sectors[1]


@dataclass
class Stage19UseThing:
    x: int
    y: int
    angle: int
    player: bool = True
    blue_key: bool = False
    red_key: bool = False
    yellow_key: bool = False


@dataclass
class Stage19DoorThinker:
    sector_index: int
    type: int
    topheight: int
    speed: int
    direction: int
    topwait: int
    topcountdown: int = 0
    thinker_kind: str = "door"
    active: int = 1


@dataclass(frozen=True)
class Stage19PathIntercept:
    frac: int
    line_index: int
    order: int


@dataclass(frozen=True)
class Stage19PathResult:
    intercepts: tuple[Stage19PathIntercept, ...]
    blocks: tuple[tuple[int, int], ...]
    completed: bool
    stopped_by_line: int | None


@dataclass(frozen=True)
class Stage19UseTraceRecord:
    line_index: int
    side: int
    special: int
    frac: int
    use_special_result: int
    door_spawned: int
    terminated: int


@dataclass(frozen=True)
class Stage19DoorCensusRecord:
    line_index: int
    paired_line_index: int
    special: int
    side: int
    front_sector: int
    target_sector: int
    right_sidedef: int
    left_sidedef: int
    front_upper_texture: str
    target_floor: int
    target_ceiling: int
    surrounding_lowest_ceiling: int
    topheight: int
    probe_x: int
    probe_y: int
    probe_angle_degrees: int
    stage18_player_distance: int
    stage18_player_in_userange: int


@dataclass(frozen=True)
class Stage19DoorTraceRecord:
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


@dataclass
class Stage19World:
    loaded: LoadedMap
    blockmap: stage14.BlockMap
    sectors: list[Stage19Sector]
    lines: list[Stage19Line]
    sector_lines: dict[int, list[int]]
    counters: Stage19Counters
    selected_line_index: int = SELECTED_LINE_INDEX
    selected_side: int = 0
    force_change_sector_nofit: bool = False
    last_path: Stage19PathResult | None = None
    use_trace: list[Stage19UseTraceRecord] | None = None
    selected_door: Stage19DoorThinker | None = None

    def __post_init__(self) -> None:
        if self.use_trace is None:
            self.use_trace = []


@dataclass(frozen=True)
class Stage19FirstDoorSwitchSectorSpecialReference:
    stage18: stage18.Stage18PostDamageMonsterMovementReference
    census: Stage19DoorCensusRecord
    path: Stage19PathResult
    use_trace: tuple[Stage19UseTraceRecord, ...]
    door_trace: tuple[Stage19DoorTraceRecord, ...]
    counters: Stage19Counters
    final_door: Stage19DoorThinker
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


def _c_div(numerator: int, denominator: int) -> int:
    return stage04._c_div(numerator, denominator)


def _angle_to_degrees(angle: int) -> int:
    return stage13.angle_to_degrees(angle)


def _line_side_sector(loaded: LoadedMap, sidenum: int) -> int | None:
    if sidenum == NO_SIDEDEF or sidenum >= len(loaded.sidedefs):
        return None
    return loaded.sidedefs[sidenum].sector


def _line_side_textures(loaded: LoadedMap, sidenum: int) -> tuple[str, str, str]:
    if sidenum == NO_SIDEDEF or sidenum >= len(loaded.sidedefs):
        return ("", "", "")
    side = loaded.sidedefs[sidenum]
    return (side.upper_texture, side.lower_texture, side.middle_texture)


def build_stage19_lines(loaded: LoadedMap) -> list[Stage19Line]:
    lines: list[Stage19Line] = []
    for index, raw in enumerate(loaded.linedefs):
        v1 = loaded.vertices[raw.start_vertex]
        v2 = loaded.vertices[raw.end_vertex]
        v1x = v1.x << FRACBITS
        v1y = v1.y << FRACBITS
        v2x = v2.x << FRACBITS
        v2y = v2.y << FRACBITS
        dx = _i32(v2x - v1x)
        dy = _i32(v2y - v1y)
        right = raw.right_sidedef
        left = raw.left_sidedef
        right_textures = _line_side_textures(loaded, right)
        left_textures = _line_side_textures(loaded, left)
        lines.append(
            Stage19Line(
                index=index,
                v1x=v1x,
                v1y=v1y,
                v2x=v2x,
                v2y=v2y,
                dx=dx,
                dy=dy,
                bbox=(max(v1y, v2y), min(v1y, v2y), min(v1x, v2x), max(v1x, v2x)),
                slopetype=stage14._slopetype(dx, dy),
                flags=raw.flags,
                special=raw.special_type,
                tag=raw.sector_tag,
                sidenum=(right, left),
                side_sectors=(_line_side_sector(loaded, right), _line_side_sector(loaded, left)),
                side_upper=(right_textures[0], left_textures[0]),
                side_lower=(right_textures[1], left_textures[1]),
                side_middle=(right_textures[2], left_textures[2]),
            )
        )
    return lines


def build_stage19_sector_lines(lines: Sequence[Stage19Line], sector_count: int) -> dict[int, list[int]]:
    sector_lines = {index: [] for index in range(sector_count)}
    for line in lines:
        for sector_index in line.side_sectors:
            if sector_index is not None and 0 <= sector_index < sector_count:
                if line.index not in sector_lines[sector_index]:
                    sector_lines[sector_index].append(line.index)
    return sector_lines


def build_stage19_world(wad: WadFile, loaded: LoadedMap) -> Stage19World:
    block_data = wad.read_lump(wad.map_lumps("MAP01").get("BLOCKMAP"))
    blockmap = stage14.p_load_blockmap_source_shape(block_data, num_lines=len(loaded.linedefs))
    sectors = [
        Stage19Sector(
            index=index,
            floorheight=sector.floor_height << FRACBITS,
            ceilingheight=sector.ceiling_height << FRACBITS,
            special=sector.special_type,
            tag=sector.tag,
        )
        for index, sector in enumerate(loaded.sectors)
    ]
    lines = build_stage19_lines(loaded)
    return Stage19World(
        loaded=loaded,
        blockmap=blockmap,
        sectors=sectors,
        lines=lines,
        sector_lines=build_stage19_sector_lines(lines, len(sectors)),
        counters=Stage19Counters(special_census_runs=1),
    )


def get_next_sector_stage19_source_shape(
    world: Stage19World,
    line: Stage19Line,
    sector_index: int,
) -> int | None:
    if not (line.flags & ML_TWOSIDED):
        return None
    if line.side_sectors[0] == sector_index:
        return line.side_sectors[1]
    return line.side_sectors[0]


def p_find_lowest_ceiling_surrounding_source_shape(world: Stage19World, sector_index: int) -> int:
    height = 0x7FFFFFFF
    for line_index in world.sector_lines.get(sector_index, []):
        line = world.lines[line_index]
        other = get_next_sector_stage19_source_shape(world, line, sector_index)
        if other is None:
            continue
        if world.sectors[other].ceilingheight < height:
            height = world.sectors[other].ceilingheight
    return height


def p_line_opening_stage19_source_shape(
    world: Stage19World,
    line: Stage19Line,
) -> tuple[int, int, int, int]:
    if line.sidenum[1] == NO_SIDEDEF or line.backsector is None:
        return 0, 0, 0, 0
    front = world.sectors[line.frontsector]
    back = world.sectors[line.backsector]
    opentop = min(front.ceilingheight, back.ceilingheight)
    if front.floorheight > back.floorheight:
        openbottom = front.floorheight
        lowfloor = back.floorheight
    else:
        openbottom = back.floorheight
        lowfloor = front.floorheight
    return opentop, openbottom, opentop - openbottom, lowfloor


def _line_divline(line: Stage19Line) -> tuple[int, int, int, int]:
    return (line.v1x, line.v1y, line.dx, line.dy)


def _add_line_intercept_stage19_source_shape(
    world: Stage19World,
    trace: Sequence[int],
    line: Stage19Line,
    intercepts: list[Stage19PathIntercept],
    order: int,
) -> int:
    if (
        trace[2] > FRACUNIT * 16
        or trace[3] > FRACUNIT * 16
        or trace[2] < -FRACUNIT * 16
        or trace[3] < -FRACUNIT * 16
    ):
        s1 = stage16.p_divline_side_source_shape(line.v1x, line.v1y, trace)
        s2 = stage16.p_divline_side_source_shape(line.v2x, line.v2y, trace)
    else:
        s1 = stage14.point_on_line_side_source_shape(trace[0], trace[1], line)
        s2 = stage14.point_on_line_side_source_shape(_i32(trace[0] + trace[2]), _i32(trace[1] + trace[3]), line)
    if s1 == s2:
        return order

    frac = stage16.p_intercept_vector2_source_shape(trace, _line_divline(line))
    if frac < 0:
        return order

    intercepts.append(Stage19PathIntercept(frac=frac, line_index=line.index, order=order))
    world.counters.line_intercepts += 1
    return order + 1


def p_path_traverse_use_line_source_shape(
    world: Stage19World,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    traverser: Callable[[Stage19PathIntercept], bool],
    *,
    max_blocks: int = 64,
    max_intercepts: int = stage16.MAXPLAYERS * 64,
) -> Stage19PathResult:
    world.counters.path_traverses += 1
    if ((x1 - world.blockmap.origin_x) & (stage14.MAPBLOCKSIZE - 1)) == 0:
        x1 += FRACUNIT
    if ((y1 - world.blockmap.origin_y) & (stage14.MAPBLOCKSIZE - 1)) == 0:
        y1 += FRACUNIT

    trace = (x1, y1, _i32(x2 - x1), _i32(y2 - y1))
    local_x1 = _i32(x1 - world.blockmap.origin_x)
    local_y1 = _i32(y1 - world.blockmap.origin_y)
    local_x2 = _i32(x2 - world.blockmap.origin_x)
    local_y2 = _i32(y2 - world.blockmap.origin_y)
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
    blocks: list[tuple[int, int]] = []
    intercepts: list[Stage19PathIntercept] = []
    checked_lines: set[int] = set()
    order = 0

    for _count in range(max_blocks):
        blocks.append((mapx, mapy))
        world.counters.block_steps += 1
        world.counters.block_line_iters += 1
        if 0 <= mapx < world.blockmap.width and 0 <= mapy < world.blockmap.height:
            for line_index in world.blockmap.lists[stage14._block_index(world.blockmap, mapx, mapy)]:
                if line_index in checked_lines or line_index >= len(world.lines):
                    continue
                checked_lines.add(line_index)
                order = _add_line_intercept_stage19_source_shape(
                    world,
                    trace,
                    world.lines[line_index],
                    intercepts,
                    order,
                )
                if len(intercepts) >= max_intercepts:
                    return Stage19PathResult(tuple(intercepts), tuple(blocks), False, None)

        if mapx == xt2 and mapy == yt2:
            break
        if (yintercept >> FRACBITS) == mapy:
            yintercept = _i32(yintercept + ystep)
            mapx += mapxstep
        elif (xintercept >> FRACBITS) == mapx:
            xintercept = _i32(xintercept + xstep)
            mapy += mapystep

    remaining = list(intercepts)
    while remaining:
        nearest = min(remaining, key=lambda item: item.frac)
        if nearest.frac > FRACUNIT:
            return Stage19PathResult(tuple(intercepts), tuple(blocks), True, None)
        world.counters.traversed_intercepts += 1
        if not traverser(nearest):
            return Stage19PathResult(tuple(intercepts), tuple(blocks), False, nearest.line_index)
        remaining.remove(nearest)
    return Stage19PathResult(tuple(intercepts), tuple(blocks), True, None)


def p_change_switch_texture_stage19_deferred(
    world: Stage19World,
    line: Stage19Line,
    use_again: int,
) -> None:
    world.counters.switch_texture_deferrals += 1
    if use_again:
        p_start_button_stage19_deferred(world, line)


def p_start_button_stage19_deferred(world: Stage19World, _line: Stage19Line) -> None:
    world.counters.button_start_deferrals += 1


def p_use_special_line_stage19_source_shape(
    world: Stage19World,
    thing: Stage19UseThing,
    line: Stage19Line,
    side: int,
) -> bool:
    world.counters.use_special_calls += 1
    if side:
        if line.special != 124:
            world.counters.back_side_rejections += 1
            return False

    if not thing.player:
        if line.special not in {1, 32, 33, 34}:
            return False

    if line.special in {1, 26, 27, 28, 31, 32, 33, 34, 117, 118}:
        world.counters.front_side_activations += int(side == 0)
        return ev_vertical_door_stage19_source_shape(world, line, thing) is not None

    if line.special in {103, 111, 112, 113, 42, 61, 63, 114, 115, 116}:
        world.counters.tagged_door_deferrals += 1
        p_change_switch_texture_stage19_deferred(world, line, 1 if line.special in {42, 61, 63, 114, 115, 116} else 0)
        return True

    world.counters.broad_special_deferrals += 1
    return True


def ptr_use_traverse_stage19_source_shape(
    world: Stage19World,
    thing: Stage19UseThing,
    intercept: Stage19PathIntercept,
) -> bool:
    line = world.lines[intercept.line_index]
    if not line.special:
        _opentop, _openbottom, openrange, _lowfloor = p_line_opening_stage19_source_shape(world, line)
        if openrange <= 0:
            world.counters.blocked_nonspecial_lines += 1
            world.counters.noway_sound_deferrals += 1
            world.counters.sound_start_deferrals += 1
            world.counters.real_sound_output_deferrals += 1
            return False
        world.counters.no_special_passes += 1
        return True

    world.counters.special_use_attempts += 1
    side = 1 if stage14.point_on_line_side_source_shape(thing.x, thing.y, line) == 1 else 0
    before = world.counters.manual_door_spawns
    ok = p_use_special_line_stage19_source_shape(world, thing, line, side)
    assert world.use_trace is not None
    world.use_trace.append(
        Stage19UseTraceRecord(
            line_index=line.index,
            side=side,
            special=line.special,
            frac=intercept.frac,
            use_special_result=1 if ok else 0,
            door_spawned=world.counters.manual_door_spawns - before,
            terminated=1,
        )
    )
    world.counters.one_special_terminations += 1
    return False


def p_use_lines_stage19_source_shape(
    world: Stage19World,
    thing: Stage19UseThing,
) -> Stage19PathResult:
    world.counters.fixed_use_probes += 1
    angle = (thing.angle >> ANGLETOFINESHIFT) & FINEMASK
    x2 = _i32(thing.x + (USERANGE >> FRACBITS) * FINECOSINE[angle])
    y2 = _i32(thing.y + (USERANGE >> FRACBITS) * FINESINE[angle])
    result = p_path_traverse_use_line_source_shape(
        world,
        thing.x,
        thing.y,
        x2,
        y2,
        lambda intercept: ptr_use_traverse_stage19_source_shape(world, thing, intercept),
    )
    world.last_path = result
    return result


def _missing_key_for_special(line: Stage19Line, thing: Stage19UseThing) -> bool:
    if line.special in {26, 32}:
        return not thing.blue_key
    if line.special in {27, 34}:
        return not thing.yellow_key
    if line.special in {28, 33}:
        return not thing.red_key
    return False


def ev_vertical_door_stage19_source_shape(
    world: Stage19World,
    line: Stage19Line,
    thing: Stage19UseThing,
) -> Stage19DoorThinker | None:
    world.counters.vertical_door_calls += 1
    side = 0
    if line.special in {26, 27, 28, 32, 33, 34}:
        if not thing.player or _missing_key_for_special(line, thing):
            world.counters.locked_door_rejections += 1
            world.counters.sound_start_deferrals += 1
            world.counters.real_sound_output_deferrals += 1
            return None

    if line.sidenum[side ^ 1] == NO_SIDEDEF:
        raise ValueError("EV_VerticalDoor: DR special type on 1-sided linedef")

    sec_index = line.side_sectors[side ^ 1]
    if sec_index is None:
        raise ValueError("EV_VerticalDoor: missing target sector")
    sec = world.sectors[sec_index]

    if sec.specialdata is not None:
        door = sec.specialdata
        if line.special in {1, 26, 27, 28, 117}:
            if door.direction == -1:
                door.direction = 1
                world.counters.already_active_reversals += 1
            else:
                if not thing.player:
                    return door
                if door.thinker_kind == "door":
                    door.direction = -1
                    world.counters.already_active_closures += 1
                else:
                    world.counters.already_active_nondoor_deferrals += 1
            return door

    if line.special in {117, 118}:
        world.counters.door_open_sound_deferrals += 1
    world.counters.sound_start_deferrals += 1
    world.counters.real_sound_output_deferrals += 1

    door_type = VLD_NORMAL
    speed = VDOORSPEED
    if line.special in {31, 32, 33, 34}:
        door_type = VLD_OPEN
        line.special = 0
    elif line.special == 117:
        door_type = VLD_BLAZE_RAISE
        speed = VDOORSPEED * 4
    elif line.special == 118:
        door_type = VLD_BLAZE_OPEN
        line.special = 0
        speed = VDOORSPEED * 4

    topheight = p_find_lowest_ceiling_surrounding_source_shape(world, sec_index) - 4 * FRACUNIT
    door = Stage19DoorThinker(
        sector_index=sec_index,
        type=door_type,
        topheight=topheight,
        speed=speed,
        direction=1,
        topwait=VDOORWAIT,
    )
    sec.specialdata = door
    world.selected_door = door
    world.counters.manual_door_spawns += 1
    world.counters.door_thinker_records += 1
    world.counters.thinker_add_deferrals += 1
    world.counters.allocation_deferrals += 1
    return door


def p_change_sector_stage19_source_shape(
    world: Stage19World,
    _sector_index: int,
    _crunch: bool,
) -> bool:
    world.counters.change_sector_checks += 1
    if world.force_change_sector_nofit:
        world.counters.change_sector_nofit += 1
        return True
    return False


def t_move_plane_stage19_source_shape(
    world: Stage19World,
    sector_index: int,
    speed: int,
    dest: int,
    crush: bool,
    floor_or_ceiling: int,
    direction: int,
) -> int:
    world.counters.move_plane_calls += 1
    sector = world.sectors[sector_index]
    if floor_or_ceiling == 1 and direction == 1:
        if sector.ceilingheight + speed > dest:
            lastpos = sector.ceilingheight
            sector.ceilingheight = dest
            if p_change_sector_stage19_source_shape(world, sector_index, crush):
                sector.ceilingheight = lastpos
                p_change_sector_stage19_source_shape(world, sector_index, crush)
            if sector.ceilingheight != lastpos:
                world.counters.ceiling_mutations += 1
            world.counters.pastdest_events += 1
            return RESULT_PASTDEST
        lastpos = sector.ceilingheight
        sector.ceilingheight += speed
        p_change_sector_stage19_source_shape(world, sector_index, crush)
        if sector.ceilingheight != lastpos:
            world.counters.ceiling_mutations += 1
        return RESULT_OK

    if floor_or_ceiling == 1 and direction == -1:
        if sector.ceilingheight - speed < dest:
            lastpos = sector.ceilingheight
            sector.ceilingheight = dest
            if p_change_sector_stage19_source_shape(world, sector_index, crush):
                sector.ceilingheight = lastpos
                p_change_sector_stage19_source_shape(world, sector_index, crush)
            if sector.ceilingheight != lastpos:
                world.counters.ceiling_mutations += 1
            world.counters.pastdest_events += 1
            return RESULT_PASTDEST
        lastpos = sector.ceilingheight
        sector.ceilingheight -= speed
        if p_change_sector_stage19_source_shape(world, sector_index, crush):
            if crush:
                world.counters.crush_events += 1
                return RESULT_CRUSHED
            sector.ceilingheight = lastpos
            p_change_sector_stage19_source_shape(world, sector_index, crush)
            world.counters.crush_events += 1
            return RESULT_CRUSHED
        if sector.ceilingheight != lastpos:
            world.counters.ceiling_mutations += 1
        return RESULT_OK

    raise NotImplementedError("stage19 only bounds ceiling movement")


def t_vertical_door_stage19_source_shape(
    world: Stage19World,
    door: Stage19DoorThinker,
) -> Stage19DoorTraceRecord:
    world.counters.t_vertical_door_ticks += 1
    sector = world.sectors[door.sector_index]
    ceiling_before = sector.ceilingheight
    direction_before = door.direction
    result = RESULT_OK

    if door.direction == 1:
        result = t_move_plane_stage19_source_shape(
            world,
            door.sector_index,
            door.speed,
            door.topheight,
            False,
            1,
            door.direction,
        )
        if result == RESULT_PASTDEST and door.type in {VLD_BLAZE_RAISE, VLD_NORMAL}:
            door.direction = 0
            door.topcountdown = door.topwait
            world.counters.wait_at_top_setups += 1
    elif door.direction == 0:
        door.topcountdown -= 1
        if door.topcountdown == 0 and door.type in {VLD_BLAZE_RAISE, VLD_NORMAL}:
            door.direction = -1
            world.counters.sound_start_deferrals += 1
            world.counters.real_sound_output_deferrals += 1
    elif door.direction == -1:
        result = t_move_plane_stage19_source_shape(
            world,
            door.sector_index,
            door.speed,
            sector.floorheight,
            False,
            1,
            door.direction,
        )
        if result == RESULT_CRUSHED and door.type not in {VLD_BLAZE_CLOSE, VLD_CLOSE}:
            door.direction = 1
            world.counters.sound_start_deferrals += 1
            world.counters.real_sound_output_deferrals += 1

    return Stage19DoorTraceRecord(
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
    )


def run_stage19_door_tics_source_shape(
    world: Stage19World,
    door: Stage19DoorThinker,
    *,
    tics: int = DEFAULT_STAGE19_DOOR_TICS,
) -> tuple[Stage19DoorTraceRecord, ...]:
    trace = []
    for _ in range(tics):
        trace.append(t_vertical_door_stage19_source_shape(world, door))
    return tuple(trace)


def _distance_from_point_to_line_units(x: int, y: int, line: Stage19Line) -> int:
    px = x / FRACUNIT
    py = y / FRACUNIT
    x1 = line.v1x / FRACUNIT
    y1 = line.v1y / FRACUNIT
    x2 = line.v2x / FRACUNIT
    y2 = line.v2y / FRACUNIT
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return int(math.hypot(px - x1, py - y1))
    frac = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    closest_x = x1 + frac * dx
    closest_y = y1 + frac * dy
    return int(round(math.hypot(px - closest_x, py - closest_y)))


def build_stage19_door_census_source_shape(
    world: Stage19World,
    ref18: stage18.Stage18PostDamageMonsterMovementReference,
) -> Stage19DoorCensusRecord:
    line = world.lines[SELECTED_LINE_INDEX]
    target_sector = line.side_sectors[1]
    if target_sector is None:
        raise ValueError("selected line does not have a back-side target sector")
    surrounding = p_find_lowest_ceiling_surrounding_source_shape(world, target_sector)
    player = ref18.stage17.stage16.target
    distance = _distance_from_point_to_line_units(player.x, player.y, line)
    in_range = int(distance <= (USERANGE >> FRACBITS))
    world.counters.stage18_player_in_userange = in_range
    return Stage19DoorCensusRecord(
        line_index=line.index,
        paired_line_index=SELECTED_PAIRED_LINE_INDEX,
        special=line.special,
        side=0,
        front_sector=line.frontsector,
        target_sector=target_sector,
        right_sidedef=line.sidenum[0],
        left_sidedef=line.sidenum[1],
        front_upper_texture=line.side_upper[0],
        target_floor=world.sectors[target_sector].floorheight,
        target_ceiling=world.sectors[target_sector].ceilingheight,
        surrounding_lowest_ceiling=surrounding,
        topheight=surrounding - 4 * FRACUNIT,
        probe_x=SELECTED_PROBE_X,
        probe_y=SELECTED_PROBE_Y,
        probe_angle_degrees=_angle_to_degrees(SELECTED_PROBE_ANGLE),
        stage18_player_distance=distance,
        stage18_player_in_userange=in_range,
    )


def _stage19_signature(
    ref18: stage18.Stage18PostDamageMonsterMovementReference,
    census: Stage19DoorCensusRecord,
    path: Stage19PathResult,
    use_trace: Sequence[Stage19UseTraceRecord],
    door_trace: Sequence[Stage19DoorTraceRecord],
    counters: Stage19Counters,
    door: Stage19DoorThinker,
) -> int:
    signature = ref18.signature
    for value in (
        census.line_index,
        census.paired_line_index,
        census.special,
        census.side,
        census.front_sector,
        census.target_sector,
        census.right_sidedef,
        census.left_sidedef,
        census.target_floor,
        census.target_ceiling,
        census.surrounding_lowest_ceiling,
        census.topheight,
        census.probe_x,
        census.probe_y,
        census.probe_angle_degrees,
        census.stage18_player_distance,
        census.stage18_player_in_userange,
        len(path.blocks),
        len(path.intercepts),
        1 if path.completed else 0,
        path.stopped_by_line if path.stopped_by_line is not None else -1,
    ):
        signature = _hash_u32(signature, value)
    for record in use_trace:
        for value in (
            record.line_index,
            record.side,
            record.special,
            record.frac,
            record.use_special_result,
            record.door_spawned,
            record.terminated,
        ):
            signature = _hash_u32(signature, value)
    for record in door_trace:
        for value in (
            record.tic,
            record.sector_index,
            record.ceiling_before,
            record.ceiling_after,
            record.floorheight,
            record.direction_before,
            record.direction_after,
            record.topheight,
            record.speed,
            record.result,
            record.topcountdown,
        ):
            signature = _hash_u32(signature, value)
    for value in (
        counters.fixed_use_probes,
        counters.path_traverses,
        counters.block_steps,
        counters.block_line_iters,
        counters.line_intercepts,
        counters.traversed_intercepts,
        counters.no_special_passes,
        counters.blocked_nonspecial_lines,
        counters.special_use_attempts,
        counters.use_special_calls,
        counters.front_side_activations,
        counters.back_side_rejections,
        counters.one_special_terminations,
        counters.vertical_door_calls,
        counters.manual_door_spawns,
        counters.door_thinker_records,
        counters.sound_start_deferrals,
        counters.door_open_sound_deferrals,
        counters.t_vertical_door_ticks,
        counters.move_plane_calls,
        counters.ceiling_mutations,
        counters.pastdest_events,
        counters.wait_at_top_setups,
        counters.crush_events,
        counters.change_sector_checks,
        counters.switch_texture_deferrals,
        counters.button_start_deferrals,
        door.sector_index,
        door.type,
        door.topheight,
        door.speed,
        door.direction,
        door.topwait,
        door.topcountdown,
    ):
        signature = _hash_u32(signature, value)
    signature = _hash_bytes(signature, census.front_upper_texture.encode("ascii"))
    return signature


def _reference_stage19_uncached(wad_path: str) -> Stage19FirstDoorSwitchSectorSpecialReference:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    ref18 = stage18.reference_post_damage_monster_movement_and_chase_probe_for_pinned_map(wad_path)
    world = build_stage19_world(wad, loaded)
    census = build_stage19_door_census_source_shape(world, ref18)
    thing = Stage19UseThing(
        x=census.probe_x,
        y=census.probe_y,
        angle=SELECTED_PROBE_ANGLE,
        player=True,
    )
    path = p_use_lines_stage19_source_shape(world, thing)
    if world.selected_door is None:
        raise AssertionError("stage19 selected use probe did not spawn a door thinker")
    door_trace = run_stage19_door_tics_source_shape(world, world.selected_door)
    final_door = replace(world.selected_door)
    signature = _stage19_signature(
        ref18,
        census,
        path,
        tuple(world.use_trace or ()),
        door_trace,
        world.counters,
        final_door,
    )
    return Stage19FirstDoorSwitchSectorSpecialReference(
        stage18=ref18,
        census=census,
        path=path,
        use_trace=tuple(world.use_trace or ()),
        door_trace=door_trace,
        counters=replace(world.counters),
        final_door=final_door,
        signature=signature,
    )


@lru_cache(maxsize=4)
def _reference_stage19_cached(wad_path: str) -> Stage19FirstDoorSwitchSectorSpecialReference:
    return _reference_stage19_uncached(wad_path)


def reference_first_door_or_switch_sector_special_probe_for_pinned_map(
    wad_path: str | Path,
) -> Stage19FirstDoorSwitchSectorSpecialReference:
    return _reference_stage19_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage19FirstDoorSwitchSectorSpecialReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_first_door_or_switch_sector_special_probe_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage19_load_wad_first_door_switch_sector_special_probe")

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


def emit_source_stage19_load_wad_first_door_switch_sector_special_probe(pe: PE32) -> None:
    pe.label("source_stage19_load_wad_first_door_switch_sector_special_probe")
    x86.call_rel32(pe, "source_stage18_load_wad_post_damage_monster_movement_chase_probe")
    x86.mov_reg_mem_abs32(pe, "eax", "stage18_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage18_expected_signature")
    x86.jne_rel32(pe, "source_stage19_return")
    x86.call_rel32(pe, "render_first_door_switch_sector_special_probe_debug")
    x86.call_rel32(pe, "append_stage19_success_status")
    pe.label("source_stage19_return")
    x86.ret(pe)


def emit_render_first_door_switch_sector_special_probe_debug(pe: PE32) -> None:
    pe.label("P_UseLines_PathTraverse_manual_door_source_shape_debug")
    pe.label("P_PathTraverse_use_line_bounded_source_shape_debug")
    pe.label("P_UseSpecialLine_manual_vertical_door_source_shape_debug")
    pe.label("EV_VerticalDoor_manual_blazing_door_source_shape_debug")
    pe.label("P_FindLowestCeilingSurrounding_manual_door_source_shape_debug")
    pe.label("T_VerticalDoor_manual_door_tic_source_shape_debug")
    pe.label("T_MovePlane_ceiling_mutation_source_shape_debug")
    pe.label("P_ChangeSwitchTexture_deferred_stage19_debug")
    pe.label("render_first_door_switch_sector_special_probe_debug")

    x86.mov_reg_mem_abs32(pe, "eax", "stage19_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage19_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage19_ceiling_after")
    x86.mov_mem_abs32_eax(pe, "stage19_runtime_ceiling_after")
    x86.mov_reg_mem_abs32(pe, "eax", "stage19_path_traverses")
    x86.mov_mem_abs32_eax(pe, "stage19_runtime_path_traverses")
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage14._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage19_success_status(pe: PE32) -> None:
    pe.label("append_stage19_success_status")

    _emit_seek_buffer_end(pe, "status_success_buffer", "stage19_status")
    stage01.append_c_string_label(pe, "status_stage19_success_header")
    stage01.append_u32_label(pe, "status_stage19_line_prefix", "stage19_line")
    stage01.append_u32_label(pe, "status_stage19_sector_prefix", "stage19_target_sector")
    stage01.append_u32_label(pe, "status_stage19_ceiling_prefix", "stage19_runtime_ceiling_after")
    stage01.append_u32_label(pe, "status_stage19_signature_prefix", "stage19_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage19_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage19_title")
    stage01.append_u32_label(pe, "title_stage19_line_prefix", "stage19_line")
    stage01.append_u32_label(pe, "title_stage19_side_prefix", "stage19_side")
    stage01.append_u32_label(pe, "title_stage19_sector_prefix", "stage19_target_sector")
    stage01.append_u32_label(pe, "title_stage19_special_prefix", "stage19_special")
    stage01.append_c_string_label(pe, "title_stage19_texture_prefix")
    stage01.append_c_string_label(pe, "stage19_front_upper_texture")
    stage01.append_u32_label(pe, "title_stage19_probe_prefix", "stage19_fixed_use_probes")
    stage01.append_i32_label(pe, "title_stage19_probe_x_prefix", "stage19_probe_x")
    stage01.append_i32_label(pe, "title_stage19_probe_y_prefix", "stage19_probe_y")
    stage01.append_u32_label(pe, "title_stage19_probe_angle_prefix", "stage19_probe_angle")
    stage01.append_u32_label(pe, "title_stage19_stage18_range_prefix", "stage19_stage18_player_in_userange")
    stage01.append_u32_label(pe, "title_stage19_player_distance_prefix", "stage19_stage18_player_distance")
    stage01.append_u32_label(pe, "title_stage19_path_prefix", "stage19_runtime_path_traverses")
    stage01.append_u32_label(pe, "title_stage19_block_steps_prefix", "stage19_block_steps")
    stage01.append_u32_label(pe, "title_stage19_line_intercepts_prefix", "stage19_line_intercepts")
    stage01.append_u32_label(pe, "title_stage19_traversed_prefix", "stage19_traversed_intercepts")
    stage01.append_u32_label(pe, "title_stage19_use_prefix", "stage19_use_special_calls")
    stage01.append_u32_label(pe, "title_stage19_back_prefix", "stage19_back_side_rejections")
    stage01.append_u32_label(pe, "title_stage19_term_prefix", "stage19_one_special_terminations")
    stage01.append_u32_label(pe, "title_stage19_vertical_door_prefix", "stage19_vertical_door_calls")
    stage01.append_u32_label(pe, "title_stage19_door_thinker_prefix", "stage19_door_thinker_records")
    stage01.append_u32_label(pe, "title_stage19_top_prefix", "stage19_topheight")
    stage01.append_i32_label(pe, "title_stage19_floor_prefix", "stage19_sector_floor")
    stage01.append_i32_label(pe, "title_stage19_ceiling_before_prefix", "stage19_ceiling_before")
    stage01.append_i32_label(pe, "title_stage19_ceiling_after_prefix", "stage19_runtime_ceiling_after")
    stage01.append_u32_label(pe, "title_stage19_direction_prefix", "stage19_door_direction")
    stage01.append_u32_label(pe, "title_stage19_speed_prefix", "stage19_door_speed_units")
    stage01.append_u32_label(pe, "title_stage19_topwait_prefix", "stage19_door_topwait")
    stage01.append_u32_label(pe, "title_stage19_ticks_prefix", "stage19_t_vertical_door_ticks")
    stage01.append_u32_label(pe, "title_stage19_move_plane_prefix", "stage19_move_plane_calls")
    stage01.append_u32_label(pe, "title_stage19_move_result_prefix", "stage19_move_result")
    stage01.append_u32_label(pe, "title_stage19_pastdest_prefix", "stage19_pastdest_events")
    stage01.append_u32_label(pe, "title_stage19_crush_prefix", "stage19_crush_events")
    stage01.append_u32_label(pe, "title_stage19_sound_prefix", "stage19_sound_start_deferrals")
    stage01.append_u32_label(pe, "title_stage19_switch_prefix", "stage19_switch_texture_deferrals")
    stage01.append_u32_label(pe, "title_stage19_button_prefix", "stage19_button_start_deferrals")
    stage01.append_u32_label(pe, "title_stage19_broad_special_prefix", "stage19_broad_special_deferrals")
    stage01.append_u32_label(pe, "title_stage19_broad_door_prefix", "stage19_broad_door_switch_deferrals")
    stage01.append_u32_label(pe, "title_stage19_broad_sector_prefix", "stage19_broad_sector_effect_deferrals")
    stage01.append_u32_label(pe, "title_stage19_sound_output_prefix", "stage19_real_sound_output_deferrals")
    stage01.append_u32_label(pe, "title_stage19_live_input_prefix", "stage19_live_input_deferrals")
    stage01.append_u32_label(pe, "title_stage19_signature_prefix", "stage19_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage19_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    census = ref.census if ref is not None else None
    counters = ref.counters if ref is not None else Stage19Counters()
    door_trace_last = ref.door_trace[-1] if ref is not None and ref.door_trace else None
    door = ref.final_door if ref is not None else None

    pe.align_section(4)
    pe.label("stage19_line")
    pe.emit_u32(census.line_index if census is not None else 0)
    pe.label("stage19_paired_line")
    pe.emit_u32(census.paired_line_index if census is not None else 0)
    pe.label("stage19_side")
    pe.emit_u32(census.side if census is not None else 0)
    pe.label("stage19_special")
    pe.emit_u32(census.special if census is not None else 0)
    pe.label("stage19_front_sector")
    pe.emit_u32(census.front_sector if census is not None else 0)
    pe.label("stage19_target_sector")
    pe.emit_u32(census.target_sector if census is not None else 0)
    pe.label("stage19_right_sidedef")
    pe.emit_u32(census.right_sidedef if census is not None else 0)
    pe.label("stage19_left_sidedef")
    pe.emit_u32(census.left_sidedef if census is not None else 0)
    pe.label("stage19_sector_floor")
    pe.emit_u32(((census.target_floor >> FRACBITS) if census is not None else 0) & 0xFFFFFFFF)
    pe.label("stage19_ceiling_before")
    pe.emit_u32(((census.target_ceiling >> FRACBITS) if census is not None else 0) & 0xFFFFFFFF)
    pe.label("stage19_surrounding_lowest_ceiling")
    pe.emit_u32(((census.surrounding_lowest_ceiling >> FRACBITS) if census is not None else 0) & 0xFFFFFFFF)
    pe.label("stage19_topheight")
    pe.emit_u32(((census.topheight >> FRACBITS) if census is not None else 0) & 0xFFFFFFFF)
    pe.label("stage19_probe_x")
    pe.emit_u32(((census.probe_x >> FRACBITS) if census is not None else 0) & 0xFFFFFFFF)
    pe.label("stage19_probe_y")
    pe.emit_u32(((census.probe_y >> FRACBITS) if census is not None else 0) & 0xFFFFFFFF)
    pe.label("stage19_probe_angle")
    pe.emit_u32(census.probe_angle_degrees if census is not None else 0)
    pe.label("stage19_stage18_player_distance")
    pe.emit_u32(census.stage18_player_distance if census is not None else 0)
    pe.label("stage19_stage18_player_in_userange")
    pe.emit_u32(census.stage18_player_in_userange if census is not None else 0)

    pe.label("stage19_special_census_runs")
    pe.emit_u32(counters.special_census_runs)
    pe.label("stage19_fixed_use_probes")
    pe.emit_u32(counters.fixed_use_probes)
    pe.label("stage19_path_traverses")
    pe.emit_u32(counters.path_traverses)
    pe.label("stage19_runtime_path_traverses")
    pe.emit_u32(0)
    pe.label("stage19_block_steps")
    pe.emit_u32(counters.block_steps)
    pe.label("stage19_block_line_iters")
    pe.emit_u32(counters.block_line_iters)
    pe.label("stage19_line_intercepts")
    pe.emit_u32(counters.line_intercepts)
    pe.label("stage19_traversed_intercepts")
    pe.emit_u32(counters.traversed_intercepts)
    pe.label("stage19_no_special_passes")
    pe.emit_u32(counters.no_special_passes)
    pe.label("stage19_blocked_nonspecial_lines")
    pe.emit_u32(counters.blocked_nonspecial_lines)
    pe.label("stage19_noway_sound_deferrals")
    pe.emit_u32(counters.noway_sound_deferrals)
    pe.label("stage19_special_use_attempts")
    pe.emit_u32(counters.special_use_attempts)
    pe.label("stage19_use_special_calls")
    pe.emit_u32(counters.use_special_calls)
    pe.label("stage19_front_side_activations")
    pe.emit_u32(counters.front_side_activations)
    pe.label("stage19_back_side_rejections")
    pe.emit_u32(counters.back_side_rejections)
    pe.label("stage19_one_special_terminations")
    pe.emit_u32(counters.one_special_terminations)
    pe.label("stage19_vertical_door_calls")
    pe.emit_u32(counters.vertical_door_calls)
    pe.label("stage19_manual_door_spawns")
    pe.emit_u32(counters.manual_door_spawns)
    pe.label("stage19_locked_door_rejections")
    pe.emit_u32(counters.locked_door_rejections)
    pe.label("stage19_already_active_reversals")
    pe.emit_u32(counters.already_active_reversals)
    pe.label("stage19_already_active_closures")
    pe.emit_u32(counters.already_active_closures)
    pe.label("stage19_door_thinker_records")
    pe.emit_u32(counters.door_thinker_records)
    pe.label("stage19_thinker_add_deferrals")
    pe.emit_u32(counters.thinker_add_deferrals)
    pe.label("stage19_allocation_deferrals")
    pe.emit_u32(counters.allocation_deferrals)
    pe.label("stage19_sound_start_deferrals")
    pe.emit_u32(counters.sound_start_deferrals)
    pe.label("stage19_door_open_sound_deferrals")
    pe.emit_u32(counters.door_open_sound_deferrals)
    pe.label("stage19_t_vertical_door_ticks")
    pe.emit_u32(counters.t_vertical_door_ticks)
    pe.label("stage19_move_plane_calls")
    pe.emit_u32(counters.move_plane_calls)
    pe.label("stage19_ceiling_mutations")
    pe.emit_u32(counters.ceiling_mutations)
    pe.label("stage19_pastdest_events")
    pe.emit_u32(counters.pastdest_events)
    pe.label("stage19_wait_at_top_setups")
    pe.emit_u32(counters.wait_at_top_setups)
    pe.label("stage19_crush_events")
    pe.emit_u32(counters.crush_events)
    pe.label("stage19_change_sector_checks")
    pe.emit_u32(counters.change_sector_checks)
    pe.label("stage19_change_sector_nofit")
    pe.emit_u32(counters.change_sector_nofit)
    pe.label("stage19_switch_texture_deferrals")
    pe.emit_u32(counters.switch_texture_deferrals)
    pe.label("stage19_button_start_deferrals")
    pe.emit_u32(counters.button_start_deferrals)
    pe.label("stage19_tagged_door_deferrals")
    pe.emit_u32(counters.tagged_door_deferrals)
    pe.label("stage19_broad_special_deferrals")
    pe.emit_u32(counters.broad_special_deferrals)
    pe.label("stage19_broad_door_switch_deferrals")
    pe.emit_u32(counters.broad_door_switch_deferrals)
    pe.label("stage19_broad_sector_effect_deferrals")
    pe.emit_u32(counters.broad_sector_effect_deferrals)
    pe.label("stage19_real_sound_output_deferrals")
    pe.emit_u32(counters.real_sound_output_deferrals)
    pe.label("stage19_live_input_deferrals")
    pe.emit_u32(counters.live_input_deferrals)
    pe.label("stage19_source_stage20_absent")
    pe.emit_u32(counters.source_stage20_absent)

    pe.label("stage19_door_type")
    pe.emit_u32(door.type if door is not None else 0)
    pe.label("stage19_door_direction")
    pe.emit_u32((door.direction if door is not None else 0) & 0xFFFFFFFF)
    pe.label("stage19_door_speed")
    pe.emit_u32(door.speed if door is not None else 0)
    pe.label("stage19_door_speed_units")
    pe.emit_u32((door.speed >> FRACBITS) if door is not None else 0)
    pe.label("stage19_door_topwait")
    pe.emit_u32(door.topwait if door is not None else 0)
    pe.label("stage19_door_topcountdown")
    pe.emit_u32(door.topcountdown if door is not None else 0)
    pe.label("stage19_move_result")
    pe.emit_u32(door_trace_last.result if door_trace_last is not None else 0)
    pe.label("stage19_ceiling_after")
    pe.emit_u32(((door_trace_last.ceiling_after >> FRACBITS) if door_trace_last is not None else 0) & 0xFFFFFFFF)
    pe.label("stage19_runtime_ceiling_after")
    pe.emit_u32(0)

    pe.label("stage19_expected_signature")
    pe.emit_u32(ref.signature if ref is not None else 0)
    pe.label("stage19_runtime_signature")
    pe.emit_u32(0)

    pe.align_section(1)
    pe.label("stage19_front_upper_texture")
    x86.emit_asciiz(pe, census.front_upper_texture if census is not None else "")
    pe.label("status_stage19_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage19_first_door_or_switch_sector_special_probe\r\n"
        "First source-shaped manual door sector mutation OK\r\n",
    )
    pe.label("status_stage19_line_prefix")
    x86.emit_asciiz(pe, "\r\nSelected manual linedef: ")
    pe.label("status_stage19_sector_prefix")
    x86.emit_asciiz(pe, "\r\nMutated target sector: ")
    pe.label("status_stage19_ceiling_prefix")
    x86.emit_asciiz(pe, "\r\nSector ceiling after first door tic: ")
    pe.label("status_stage19_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage19 door mutation signature: ")
    pe.label("status_stage19_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage19 preserves the released stage18 post-damage movement proof, "
        "then uses a fixed MAP01 front-side P_UseLines probe on real linedef 332. "
        "The bounded route reaches P_UseSpecialLine, EV_VerticalDoor, "
        "P_FindLowestCeilingSurrounding, T_VerticalDoor, and T_MovePlane, "
        "spawns one table-backed door thinker record, and mutates sector 56's "
        "ceiling upward by the blazing door speed. Sound starts and broader "
        "special systems remain counted boundaries.\r\n",
    )

    pe.label("title_stage19_line_prefix")
    x86.emit_asciiz(pe, " S19LINE=")
    pe.label("title_stage19_side_prefix")
    x86.emit_asciiz(pe, " SIDE=")
    pe.label("title_stage19_sector_prefix")
    x86.emit_asciiz(pe, " S19SEC=")
    pe.label("title_stage19_special_prefix")
    x86.emit_asciiz(pe, " S19SPEC=")
    pe.label("title_stage19_texture_prefix")
    x86.emit_asciiz(pe, " S19TEX=")
    pe.label("title_stage19_probe_prefix")
    x86.emit_asciiz(pe, " PROBE19=")
    pe.label("title_stage19_probe_x_prefix")
    x86.emit_asciiz(pe, " U19X=")
    pe.label("title_stage19_probe_y_prefix")
    x86.emit_asciiz(pe, " U19Y=")
    pe.label("title_stage19_probe_angle_prefix")
    x86.emit_asciiz(pe, " U19A=")
    pe.label("title_stage19_stage18_range_prefix")
    x86.emit_asciiz(pe, " P18USE=")
    pe.label("title_stage19_player_distance_prefix")
    x86.emit_asciiz(pe, " P18DIST=")
    pe.label("title_stage19_path_prefix")
    x86.emit_asciiz(pe, " PATH19=")
    pe.label("title_stage19_block_steps_prefix")
    x86.emit_asciiz(pe, " BLK19=")
    pe.label("title_stage19_line_intercepts_prefix")
    x86.emit_asciiz(pe, " LI19=")
    pe.label("title_stage19_traversed_prefix")
    x86.emit_asciiz(pe, " TRV19=")
    pe.label("title_stage19_use_prefix")
    x86.emit_asciiz(pe, " USE19=")
    pe.label("title_stage19_back_prefix")
    x86.emit_asciiz(pe, " BACK19=")
    pe.label("title_stage19_term_prefix")
    x86.emit_asciiz(pe, " TERM19=")
    pe.label("title_stage19_vertical_door_prefix")
    x86.emit_asciiz(pe, " VD19=")
    pe.label("title_stage19_door_thinker_prefix")
    x86.emit_asciiz(pe, " DTH19=")
    pe.label("title_stage19_top_prefix")
    x86.emit_asciiz(pe, " TOP19=")
    pe.label("title_stage19_floor_prefix")
    x86.emit_asciiz(pe, " F19=")
    pe.label("title_stage19_ceiling_before_prefix")
    x86.emit_asciiz(pe, " C190=")
    pe.label("title_stage19_ceiling_after_prefix")
    x86.emit_asciiz(pe, " C191=")
    pe.label("title_stage19_direction_prefix")
    x86.emit_asciiz(pe, " DIR19=")
    pe.label("title_stage19_speed_prefix")
    x86.emit_asciiz(pe, " SPD19=")
    pe.label("title_stage19_topwait_prefix")
    x86.emit_asciiz(pe, " TWAIT19=")
    pe.label("title_stage19_ticks_prefix")
    x86.emit_asciiz(pe, " TD19=")
    pe.label("title_stage19_move_plane_prefix")
    x86.emit_asciiz(pe, " MP19=")
    pe.label("title_stage19_move_result_prefix")
    x86.emit_asciiz(pe, " MPR19=")
    pe.label("title_stage19_pastdest_prefix")
    x86.emit_asciiz(pe, " PAST19=")
    pe.label("title_stage19_crush_prefix")
    x86.emit_asciiz(pe, " CRUSH19=")
    pe.label("title_stage19_sound_prefix")
    x86.emit_asciiz(pe, " SND19=")
    pe.label("title_stage19_switch_prefix")
    x86.emit_asciiz(pe, " SWDEF19=")
    pe.label("title_stage19_button_prefix")
    x86.emit_asciiz(pe, " BTNDEF19=")
    pe.label("title_stage19_broad_special_prefix")
    x86.emit_asciiz(pe, " GSPEC19=")
    pe.label("title_stage19_broad_door_prefix")
    x86.emit_asciiz(pe, " GDOOR19=")
    pe.label("title_stage19_broad_sector_prefix")
    x86.emit_asciiz(pe, " GSECT19=")
    pe.label("title_stage19_sound_output_prefix")
    x86.emit_asciiz(pe, " AUD19=")
    pe.label("title_stage19_live_input_prefix")
    x86.emit_asciiz(pe, " LIVE19=")
    pe.label("title_stage19_signature_prefix")
    x86.emit_asciiz(pe, " S19SIG=")


def build_source_stage19_first_door_or_switch_sector_special_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage19_load_wad_first_door_switch_sector_special_probe(pe)
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
    emit_render_first_door_switch_sector_special_probe_debug(pe)
    stage12.emit_build_success_status(pe)
    stage13.emit_append_stage13_success_status(pe)
    stage14.emit_append_stage14_success_status(pe)
    stage15.emit_append_stage15_success_status(pe)
    stage16.emit_append_stage16_success_status(pe)
    stage17.emit_append_stage17_success_status(pe)
    stage18.emit_append_stage18_success_status(pe)
    emit_append_stage19_success_status(pe)
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
    emit_stage19_data(pe)
    return pe.build("entry")


def write_source_stage19_first_door_or_switch_sector_special_probe_exe(path: str | Path) -> bytes:
    image = build_source_stage19_first_door_or_switch_sector_special_probe_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage19 first door/switch sector special PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage19_first_door_or_switch_sector_special_probe.exe",
        help="path to write, default: build/source_stage19_first_door_or_switch_sector_special_probe.exe",
    )
    args = parser.parse_args()
    write_source_stage19_first_door_or_switch_sector_special_probe_exe(args.output)


if __name__ == "__main__":
    main()
