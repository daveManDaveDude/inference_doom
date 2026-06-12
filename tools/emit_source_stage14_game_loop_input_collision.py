from __future__ import annotations

import argparse
import struct
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
from tools import x86
from tools.map_loader import LineDef, LoadedMap, NO_SIDEDEF, load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


FRAMEBUFFER_WIDTH = stage13.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage13.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage13.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage13.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage13.WINDOW_WIDTH
WINDOW_HEIGHT = stage13.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage14GameLoopInputCollision"
WINDOW_TITLE = "Inference Doom S14 Game Loop Input Collision"
WAD_PATH = stage13.WAD_PATH

FRACBITS = stage13.FRACBITS
FRACUNIT = stage13.FRACUNIT
VIEWHEIGHT_UNITS = stage13.VIEWHEIGHT
VIEWHEIGHT = VIEWHEIGHT_UNITS * FRACUNIT
ANG90 = stage13.ANG90
ANG45 = stage13.ANG45
ANGLETOFINESHIFT = stage13.ANGLETOFINESHIFT
FINEMASK = stage13.FINEMASK
FINECOSINE = stage13.FINECOSINE
FINESINE = stage13.FINESINE
FNV_OFFSET_BASIS = stage12.FNV_OFFSET_BASIS
FNV_PRIME = stage13.FNV_PRIME

BOXTOP = 0
BOXBOTTOM = 1
BOXLEFT = 2
BOXRIGHT = 3

ST_HORIZONTAL = 0
ST_VERTICAL = 1
ST_POSITIVE = 2
ST_NEGATIVE = 3

ML_BLOCKING = 1
ML_BLOCKMONSTERS = 2
ML_TWOSIDED = 4

MAPBLOCKUNITS = 128
MAPBLOCKSIZE = MAPBLOCKUNITS * FRACUNIT
MAPBLOCKSHIFT = FRACBITS + 7
MAXRADIUS = 32 * FRACUNIT
MAXMOVE = 30 * FRACUNIT
PLAYERRADIUS = 16 * FRACUNIT
STOPSPEED = 0x1000
FRICTION = 0xE800
MAXBOB = 0x100000

PST_LIVE = 0
CF_NOCLIP = 1
CF_NOMOMENTUM = 4

DEFAULT_SCRIPT = (
    # A short source-shaped local tic stream: begin with a few walking tics,
    # then add one low-resolution turn and one sidestep so angle and side
    # command handling both participate before friction settles the final mom.
    (25, 0, 0, 0),
    (25, 0, 0, 0),
    (25, 0, 0, 0),
    (25, 0, 0, 0),
    (25, 0, 320, 0),
    (25, 0, 320, 0),
    (0, 24, 0, 0),
    (0, 0, 0, 0),
)

SOURCE_TRACE = stage13.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_setup.c",
        "P_LoadBlockMap",
        "P_LoadBlockMap_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_maputl.c",
        "P_BlockLinesIterator/P_BlockThingsIterator",
        "P_BlockIterators_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_maputl.c",
        "P_PointOnLineSide/P_BoxOnLineSide/P_LineOpening",
        "P_LineBBoxHelpers_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "PIT_CheckLine/PIT_CheckThing",
        "PIT_CheckLineThing_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "P_CheckPosition/P_TryMove",
        "P_CheckPosition_TryMove_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_user.c",
        "P_Thrust/P_MovePlayer/P_CalcHeight/P_PlayerThink movement branch",
        "P_PlayerThinkMovement_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_XYMovement/P_SetThingPosition/P_UnsetThingPosition",
        "P_XYMovementRelink_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_tick.c",
        "P_Ticker narrowed single local player dispatch",
        "P_Ticker_single_player_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/g_game.c",
        "G_Ticker single-player ticcmd_t dispatch",
        "G_Ticker_ticcmd_dispatch_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/d_main.c",
        "D_DoomLoop/D_RunFrame timing boundary reference",
        "D_DoomLoop_frame_boundary_reference_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/d_net.c",
        "TryRunTics/RunTic command boundary reference",
        "TryRunTics_command_boundary_reference_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_SetupFrame after moved player mobj",
        "R_SetupFrame_after_movement_source_shape_debug",
    ),
)


@dataclass(frozen=True)
class TicCmd:
    forwardmove: int = 0
    sidemove: int = 0
    angleturn: int = 0
    buttons: int = 0


@dataclass(frozen=True)
class BlockMap:
    origin_x: int
    origin_y: int
    width: int
    height: int
    shorts: tuple[int, ...]
    offsets: tuple[int, ...]
    lists: tuple[tuple[int, ...], ...]

    @property
    def block_count(self) -> int:
        return self.width * self.height


@dataclass
class BlockIteratorState:
    validcount: int = 1
    line_validcounts: dict[int, int] | None = None
    line_iterator_calls: int = 0
    thing_iterator_calls: int = 0
    line_out_of_bounds: int = 0
    thing_out_of_bounds: int = 0
    line_visits: int = 0
    thing_visits: int = 0
    line_duplicate_skips: int = 0
    line_overflows: int = 0
    thing_overflows: int = 0

    def __post_init__(self) -> None:
        if self.line_validcounts is None:
            self.line_validcounts = {}


@dataclass(frozen=True)
class MovementSector:
    index: int
    floorheight: int
    ceilingheight: int
    special: int = 0


@dataclass(frozen=True)
class MovementLine:
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
    frontsector: int
    backsector: int | None


@dataclass
class MovementMobj:
    index: int
    mapthing_index: int
    type_name: str
    doomednum: int
    x: int
    y: int
    z: int
    angle: int
    momx: int
    momy: int
    momz: int
    radius: int
    height: int
    flags: int
    floorz: int
    ceilingz: int
    subsector: int
    sector: int
    player_index: int = -1
    reactiontime: int = 0
    state_name: str = "S_PLAY"
    bnext: int | None = None
    bprev: int | None = None
    snext: int | None = None
    sprev: int | None = None

    @property
    def has_player(self) -> bool:
        return self.player_index >= 0


@dataclass
class MovementPlayer:
    player_index: int
    mo_index: int
    cmd: TicCmd
    viewz: int
    viewheight: int = VIEWHEIGHT
    deltaviewheight: int = 0
    bob: int = 0
    playerstate: int = PST_LIVE
    cheats: int = 0
    extralight: int = 0
    fixedcolormap: int = 0


@dataclass
class MovementCounters:
    check_position_calls: int = 0
    try_move_calls: int = 0
    accepted_moves: int = 0
    rejected_moves: int = 0
    line_checks: int = 0
    thing_checks: int = 0
    blocking_lines: int = 0
    blocking_things: int = 0
    special_lines_deferred: int = 0
    special_things_deferred: int = 0
    nofit_rejects: int = 0
    ceiling_rejects: int = 0
    step_rejects: int = 0
    dropoff_rejects: int = 0
    unset_links: int = 0
    set_links: int = 0
    block_relinks: int = 0
    sector_relinks: int = 0
    slide_attempts: int = 0
    slide_deferred: int = 0
    tic_count: int = 0
    p_ticker_calls: int = 0
    g_ticker_calls: int = 0
    xy_movement_calls: int = 0


@dataclass
class MovementWorld:
    loaded: LoadedMap
    geometry: stage13.MapGeometry
    blockmap: BlockMap
    sectors: list[MovementSector]
    lines: list[MovementLine]
    mobjs: list[MovementMobj]
    player: MovementPlayer
    blocklinks: list[int | None]
    sectorlinks: list[int | None]
    iterator: BlockIteratorState
    counters: MovementCounters
    leveltime: int = 0
    validcount: int = 1
    tmfloorz: int = 0
    tmceilingz: int = 0
    tmdropoffz: int = 0
    tmbbox: tuple[int, int, int, int] = (0, 0, 0, 0)
    spechit: list[int] | None = None

    def __post_init__(self) -> None:
        if self.spechit is None:
            self.spechit = []


@dataclass(frozen=True)
class MovementTraceRecord:
    tic: int
    forwardmove: int
    sidemove: int
    angleturn: int
    x: int
    y: int
    angle_degrees: int
    momx: int
    momy: int
    viewz: int
    accepted_moves: int
    rejected_moves: int
    line_checks: int
    thing_checks: int


@dataclass(frozen=True)
class FrameSetupRecord:
    viewx: int
    viewy: int
    viewz: int
    viewangle: int
    viewangle_degrees: int
    viewcos: int
    viewsin: int
    subsector: int
    sector: int
    framecount: int
    validcount: int


@dataclass(frozen=True)
class CollisionProbeResult:
    active: int
    line_index: int
    target_x: int
    target_y: int
    blocked: int
    line_checks: int
    thing_checks: int
    blocking_lines: int
    blocking_things: int


@dataclass(frozen=True)
class Stage14GameLoopInputCollisionReference:
    stage13: stage13.Stage13ThingsSpritesReference
    blockmap: BlockMap
    initial_player: stage13.MinimalPlayer
    final_mobj: MovementMobj
    final_player: MovementPlayer
    frame: FrameSetupRecord
    script: tuple[TicCmd, ...]
    trace: tuple[MovementTraceRecord, ...]
    counters: MovementCounters
    iterator: BlockIteratorState
    probe: CollisionProbeResult
    signature: int


def _u32(value: int) -> int:
    return value & 0xFFFFFFFF


def _i32(value: int) -> int:
    return stage04._int32(value)


def _c_div(numerator: int, denominator: int) -> int:
    return stage04._c_div(numerator, denominator)


def _fixed_mul(a: int, b: int) -> int:
    return stage07.fixed_mul(a, b)


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & 0xFFFFFFFF


def angle_to_degrees(angle: int) -> int:
    return stage13.angle_to_degrees(angle)


def fine_index(angle: int) -> int:
    return (_u32(angle) >> ANGLETOFINESHIFT) & FINEMASK


def _block_index(blockmap: BlockMap, x: int, y: int) -> int:
    return y * blockmap.width + x


def p_load_blockmap_source_shape(
    data: bytes,
    *,
    num_lines: int | None = None,
    max_list_entries: int = 4096,
) -> BlockMap:
    if len(data) % 2:
        raise ValueError("BLOCKMAP lump length is not word-aligned")
    count = len(data) // 2
    if count < 4:
        raise ValueError("BLOCKMAP lump is too short for the header")
    shorts = struct.unpack("<" + "h" * count, data)
    origin_x = shorts[0] << FRACBITS
    origin_y = shorts[1] << FRACBITS
    width = shorts[2]
    height = shorts[3]
    if width <= 0 or height <= 0:
        raise ValueError("BLOCKMAP dimensions must be positive")
    block_count = width * height
    offset_table_end = 4 + block_count
    if offset_table_end > count:
        raise ValueError("BLOCKMAP offset table extends past lump")

    offsets = tuple(shorts[4:offset_table_end])
    lists: list[tuple[int, ...]] = []
    for block_number, offset in enumerate(offsets):
        if offset < 0 or offset >= count:
            raise ValueError(f"BLOCKMAP block {block_number} has out-of-range offset {offset}")
        entries: list[int] = []
        cursor = offset
        while True:
            if cursor >= count:
                raise ValueError(f"BLOCKMAP block {block_number} list is unterminated")
            value = shorts[cursor]
            cursor += 1
            if value == -1:
                break
            if value < 0:
                raise ValueError(f"BLOCKMAP block {block_number} has malformed line index {value}")
            if num_lines is not None and value >= num_lines:
                raise ValueError(f"BLOCKMAP block {block_number} references line {value}")
            entries.append(value)
            if len(entries) > max_list_entries:
                raise ValueError(f"BLOCKMAP block {block_number} exceeds bounded list length")
        lists.append(tuple(entries))

    return BlockMap(
        origin_x=origin_x,
        origin_y=origin_y,
        width=width,
        height=height,
        shorts=tuple(shorts),
        offsets=offsets,
        lists=tuple(lists),
    )


def p_block_lines_iterator_source_shape(
    blockmap: BlockMap,
    x: int,
    y: int,
    lines: Sequence[MovementLine],
    state: BlockIteratorState,
    func: Callable[[MovementLine], bool],
    *,
    max_line_entries: int = 256,
) -> bool:
    state.line_iterator_calls += 1
    if x < 0 or y < 0 or x >= blockmap.width or y >= blockmap.height:
        state.line_out_of_bounds += 1
        return True
    assert state.line_validcounts is not None
    entries = blockmap.lists[_block_index(blockmap, x, y)]
    for entry_number, line_index in enumerate(entries):
        if entry_number >= max_line_entries:
            state.line_overflows += 1
            break
        if line_index >= len(lines):
            state.line_overflows += 1
            continue
        if state.line_validcounts.get(line_index) == state.validcount:
            state.line_duplicate_skips += 1
            continue
        state.line_validcounts[line_index] = state.validcount
        state.line_visits += 1
        if not func(lines[line_index]):
            return False
    return True


def p_block_things_iterator_source_shape(
    world: MovementWorld,
    x: int,
    y: int,
    func: Callable[[MovementMobj], bool],
    *,
    max_thing_entries: int = 128,
) -> bool:
    world.iterator.thing_iterator_calls += 1
    if x < 0 or y < 0 or x >= world.blockmap.width or y >= world.blockmap.height:
        world.iterator.thing_out_of_bounds += 1
        return True
    mobj_index = world.blocklinks[_block_index(world.blockmap, x, y)]
    visits = 0
    while mobj_index is not None:
        if visits >= max_thing_entries:
            world.iterator.thing_overflows += 1
            return True
        mobj = world.mobjs[mobj_index]
        world.iterator.thing_visits += 1
        if not func(mobj):
            return False
        mobj_index = mobj.bnext
        visits += 1
    return True


def _line_sidedef_index(line: LineDef, side: int) -> int:
    return line.right_sidedef if side == 0 else line.left_sidedef


def _line_backsector_index(line: LineDef, side: int, loaded: LoadedMap) -> int | None:
    other = _line_sidedef_index(line, side ^ 1)
    if other == NO_SIDEDEF or other >= len(loaded.sidedefs):
        return None
    return loaded.sidedefs[other].sector


def _line_frontsector_index(line: LineDef, side: int, loaded: LoadedMap) -> int:
    sidedef = _line_sidedef_index(line, side)
    if sidedef == NO_SIDEDEF or sidedef >= len(loaded.sidedefs):
        return 0
    return loaded.sidedefs[sidedef].sector


def _slopetype(dx: int, dy: int) -> int:
    if dx == 0:
        return ST_VERTICAL
    if dy == 0:
        return ST_HORIZONTAL
    return ST_POSITIVE if stage04.fixed_div(dy, dx) > 0 else ST_NEGATIVE


def build_movement_sectors(loaded: LoadedMap) -> list[MovementSector]:
    return [
        MovementSector(
            index=index,
            floorheight=sector.floor_height << FRACBITS,
            ceilingheight=sector.ceiling_height << FRACBITS,
            special=sector.special_type,
        )
        for index, sector in enumerate(loaded.sectors)
    ]


def build_movement_lines(loaded: LoadedMap) -> list[MovementLine]:
    lines: list[MovementLine] = []
    for index, raw in enumerate(loaded.linedefs):
        v1 = loaded.vertices[raw.start_vertex]
        v2 = loaded.vertices[raw.end_vertex]
        v1x = v1.x << FRACBITS
        v1y = v1.y << FRACBITS
        v2x = v2.x << FRACBITS
        v2y = v2.y << FRACBITS
        dx = _i32(v2x - v1x)
        dy = _i32(v2y - v1y)
        bbox = (
            max(v1y, v2y),
            min(v1y, v2y),
            min(v1x, v2x),
            max(v1x, v2x),
        )
        lines.append(
            MovementLine(
                index=index,
                v1x=v1x,
                v1y=v1y,
                v2x=v2x,
                v2y=v2y,
                dx=dx,
                dy=dy,
                bbox=bbox,
                slopetype=_slopetype(dx, dy),
                flags=raw.flags,
                special=raw.special_type,
                frontsector=_line_frontsector_index(raw, 0, loaded),
                backsector=_line_backsector_index(raw, 0, loaded),
            )
        )
    return lines


def point_on_line_side_source_shape(x: int, y: int, line: MovementLine) -> int:
    if line.dx == 0:
        if x <= line.v1x:
            return 1 if line.dy > 0 else 0
        return 1 if line.dy < 0 else 0
    if line.dy == 0:
        if y <= line.v1y:
            return 1 if line.dx < 0 else 0
        return 1 if line.dx > 0 else 0

    dx = _i32(x - line.v1x)
    dy = _i32(y - line.v1y)
    left = _fixed_mul(line.dy >> FRACBITS, dx)
    right = _fixed_mul(dy, line.dx >> FRACBITS)
    return 0 if right < left else 1


def box_on_line_side_source_shape(tmbox: Sequence[int], line: MovementLine) -> int:
    p1 = p2 = 0
    if line.slopetype == ST_HORIZONTAL:
        p1 = 1 if tmbox[BOXTOP] > line.v1y else 0
        p2 = 1 if tmbox[BOXBOTTOM] > line.v1y else 0
        if line.dx < 0:
            p1 ^= 1
            p2 ^= 1
    elif line.slopetype == ST_VERTICAL:
        p1 = 1 if tmbox[BOXRIGHT] < line.v1x else 0
        p2 = 1 if tmbox[BOXLEFT] < line.v1x else 0
        if line.dy < 0:
            p1 ^= 1
            p2 ^= 1
    elif line.slopetype == ST_POSITIVE:
        p1 = point_on_line_side_source_shape(tmbox[BOXLEFT], tmbox[BOXTOP], line)
        p2 = point_on_line_side_source_shape(tmbox[BOXRIGHT], tmbox[BOXBOTTOM], line)
    else:
        p1 = point_on_line_side_source_shape(tmbox[BOXRIGHT], tmbox[BOXTOP], line)
        p2 = point_on_line_side_source_shape(tmbox[BOXLEFT], tmbox[BOXBOTTOM], line)
    return p1 if p1 == p2 else -1


def p_line_opening_source_shape(
    world: MovementWorld,
    line: MovementLine,
) -> tuple[int, int, int, int]:
    if line.backsector is None:
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


def _block_coord(world: MovementWorld, fixed_value: int, origin: int) -> int:
    return _i32(fixed_value - origin) >> MAPBLOCKSHIFT


def _subsector_sector_for_point(world: MovementWorld, x: int, y: int) -> tuple[int, int]:
    return stage13.sector_for_point_source_shape(x, y, world.loaded, world.geometry)


def p_unset_thing_position_source_shape(world: MovementWorld, thing: MovementMobj) -> None:
    world.counters.unset_links += 1
    if not (thing.flags & stage13.MF_NOSECTOR):
        if thing.snext is not None:
            world.mobjs[thing.snext].sprev = thing.sprev
        if thing.sprev is not None:
            world.mobjs[thing.sprev].snext = thing.snext
        elif 0 <= thing.sector < len(world.sectorlinks):
            world.sectorlinks[thing.sector] = thing.snext
        thing.snext = None
        thing.sprev = None
    if not (thing.flags & stage13.MF_NOBLOCKMAP):
        if thing.bnext is not None:
            world.mobjs[thing.bnext].bprev = thing.bprev
        if thing.bprev is not None:
            world.mobjs[thing.bprev].bnext = thing.bnext
        else:
            blockx = _block_coord(world, thing.x, world.blockmap.origin_x)
            blocky = _block_coord(world, thing.y, world.blockmap.origin_y)
            if 0 <= blockx < world.blockmap.width and 0 <= blocky < world.blockmap.height:
                world.blocklinks[_block_index(world.blockmap, blockx, blocky)] = thing.bnext
        thing.bnext = None
        thing.bprev = None


def p_set_thing_position_source_shape(world: MovementWorld, thing: MovementMobj) -> None:
    world.counters.set_links += 1
    subsector, sector = _subsector_sector_for_point(world, thing.x, thing.y)
    thing.subsector = subsector
    thing.sector = sector
    if not (thing.flags & stage13.MF_NOSECTOR):
        head = world.sectorlinks[sector]
        thing.sprev = None
        thing.snext = head
        if head is not None:
            world.mobjs[head].sprev = thing.index
        world.sectorlinks[sector] = thing.index
        world.counters.sector_relinks += 1
    if not (thing.flags & stage13.MF_NOBLOCKMAP):
        blockx = _block_coord(world, thing.x, world.blockmap.origin_x)
        blocky = _block_coord(world, thing.y, world.blockmap.origin_y)
        if 0 <= blockx < world.blockmap.width and 0 <= blocky < world.blockmap.height:
            link_index = _block_index(world.blockmap, blockx, blocky)
            head = world.blocklinks[link_index]
            thing.bprev = None
            thing.bnext = head
            if head is not None:
                world.mobjs[head].bprev = thing.index
            world.blocklinks[link_index] = thing.index
            world.counters.block_relinks += 1
        else:
            thing.bnext = None
            thing.bprev = None


def pit_check_thing_source_shape(world: MovementWorld, tmthing: MovementMobj, thing: MovementMobj, tmx: int, tmy: int) -> bool:
    if not (thing.flags & (stage13.MF_SOLID | stage13.MF_SPECIAL | stage13.MF_SHOOTABLE)):
        return True
    blockdist = thing.radius + tmthing.radius
    if abs(thing.x - tmx) >= blockdist or abs(thing.y - tmy) >= blockdist:
        return True
    if thing.index == tmthing.index:
        return True
    world.counters.thing_checks += 1
    if thing.flags & stage13.MF_SPECIAL:
        world.counters.special_things_deferred += 1
        return not bool(thing.flags & stage13.MF_SOLID)
    if thing.flags & stage13.MF_SOLID:
        world.counters.blocking_things += 1
        return False
    return True


def pit_check_line_source_shape(world: MovementWorld, tmthing: MovementMobj, line: MovementLine) -> bool:
    world.counters.line_checks += 1
    tmbbox = world.tmbbox
    if (
        tmbbox[BOXRIGHT] <= line.bbox[BOXLEFT]
        or tmbbox[BOXLEFT] >= line.bbox[BOXRIGHT]
        or tmbbox[BOXTOP] <= line.bbox[BOXBOTTOM]
        or tmbbox[BOXBOTTOM] >= line.bbox[BOXTOP]
    ):
        return True
    if box_on_line_side_source_shape(tmbbox, line) != -1:
        return True
    if line.backsector is None:
        world.counters.blocking_lines += 1
        return False
    if not (tmthing.flags & stage13.MF_MISSILE):
        if line.flags & ML_BLOCKING:
            world.counters.blocking_lines += 1
            return False
        if not tmthing.has_player and line.flags & ML_BLOCKMONSTERS:
            world.counters.blocking_lines += 1
            return False
    opentop, openbottom, _openrange, lowfloor = p_line_opening_source_shape(world, line)
    if opentop < world.tmceilingz:
        world.tmceilingz = opentop
    if openbottom > world.tmfloorz:
        world.tmfloorz = openbottom
    if lowfloor < world.tmdropoffz:
        world.tmdropoffz = lowfloor
    if line.special:
        world.counters.special_lines_deferred += 1
        assert world.spechit is not None
        world.spechit.append(line.index)
    return True


def p_check_position_source_shape(world: MovementWorld, thing: MovementMobj, x: int, y: int) -> bool:
    world.counters.check_position_calls += 1
    world.tmbbox = (
        y + thing.radius,
        y - thing.radius,
        x - thing.radius,
        x + thing.radius,
    )
    new_subsector, new_sector = _subsector_sector_for_point(world, x, y)
    sector = world.sectors[new_sector]
    world.tmfloorz = sector.floorheight
    world.tmdropoffz = sector.floorheight
    world.tmceilingz = sector.ceilingheight
    world.validcount += 1
    world.iterator.validcount = world.validcount
    if world.spechit is not None:
        world.spechit.clear()

    if thing.flags & stage13.MF_NOCLIP:
        return True

    xl = _block_coord(world, world.tmbbox[BOXLEFT] - MAXRADIUS, world.blockmap.origin_x)
    xh = _block_coord(world, world.tmbbox[BOXRIGHT] + MAXRADIUS, world.blockmap.origin_x)
    yl = _block_coord(world, world.tmbbox[BOXBOTTOM] - MAXRADIUS, world.blockmap.origin_y)
    yh = _block_coord(world, world.tmbbox[BOXTOP] + MAXRADIUS, world.blockmap.origin_y)
    for bx in range(xl, xh + 1):
        for by in range(yl, yh + 1):
            if not p_block_things_iterator_source_shape(
                world,
                bx,
                by,
                lambda other: pit_check_thing_source_shape(world, thing, other, x, y),
            ):
                return False

    xl = _block_coord(world, world.tmbbox[BOXLEFT], world.blockmap.origin_x)
    xh = _block_coord(world, world.tmbbox[BOXRIGHT], world.blockmap.origin_x)
    yl = _block_coord(world, world.tmbbox[BOXBOTTOM], world.blockmap.origin_y)
    yh = _block_coord(world, world.tmbbox[BOXTOP], world.blockmap.origin_y)
    for bx in range(xl, xh + 1):
        for by in range(yl, yh + 1):
            if not p_block_lines_iterator_source_shape(
                world.blockmap,
                bx,
                by,
                world.lines,
                world.iterator,
                lambda line: pit_check_line_source_shape(world, thing, line),
            ):
                return False
    return True


def p_try_move_source_shape(world: MovementWorld, thing: MovementMobj, x: int, y: int) -> bool:
    world.counters.try_move_calls += 1
    oldx = thing.x
    oldy = thing.y
    if not p_check_position_source_shape(world, thing, x, y):
        world.counters.rejected_moves += 1
        return False
    if not (thing.flags & stage13.MF_NOCLIP):
        if world.tmceilingz - world.tmfloorz < thing.height:
            world.counters.nofit_rejects += 1
            world.counters.rejected_moves += 1
            return False
        if not (thing.flags & stage13.MF_TELEPORT) and world.tmceilingz - thing.z < thing.height:
            world.counters.ceiling_rejects += 1
            world.counters.rejected_moves += 1
            return False
        if not (thing.flags & stage13.MF_TELEPORT) and world.tmfloorz - thing.z > 24 * FRACUNIT:
            world.counters.step_rejects += 1
            world.counters.rejected_moves += 1
            return False
        if not (thing.flags & (stage13.MF_DROPOFF | stage13.MF_FLOAT)) and world.tmfloorz - world.tmdropoffz > 24 * FRACUNIT:
            world.counters.dropoff_rejects += 1
            world.counters.rejected_moves += 1
            return False

    p_unset_thing_position_source_shape(world, thing)
    thing.floorz = world.tmfloorz
    thing.ceilingz = world.tmceilingz
    thing.x = x
    thing.y = y
    p_set_thing_position_source_shape(world, thing)
    world.counters.accepted_moves += 1

    if not (thing.flags & (stage13.MF_TELEPORT | stage13.MF_NOCLIP)) and world.spechit:
        for line_index in reversed(world.spechit):
            line = world.lines[line_index]
            side = point_on_line_side_source_shape(thing.x, thing.y, line)
            oldside = point_on_line_side_source_shape(oldx, oldy, line)
            if side != oldside and line.special:
                world.counters.special_lines_deferred += 1
    return True


def p_thrust_source_shape(player: MovementPlayer, mo: MovementMobj, angle: int, move: int) -> None:
    fine = fine_index(angle)
    mo.momx = _i32(mo.momx + _fixed_mul(move, FINECOSINE[fine]))
    mo.momy = _i32(mo.momy + _fixed_mul(move, FINESINE[fine]))


def p_move_player_source_shape(world: MovementWorld, player: MovementPlayer) -> None:
    mo = world.mobjs[player.mo_index]
    cmd = player.cmd
    mo.angle = _u32(mo.angle + ((cmd.angleturn << FRACBITS) & 0xFFFFFFFF))
    onground = mo.z <= mo.floorz
    if cmd.forwardmove and onground:
        p_thrust_source_shape(player, mo, mo.angle, cmd.forwardmove * 2048)
    if cmd.sidemove and onground:
        p_thrust_source_shape(player, mo, _u32(mo.angle - ANG90), cmd.sidemove * 2048)
    if (cmd.forwardmove or cmd.sidemove) and mo.state_name == "S_PLAY":
        mo.state_name = "S_PLAY_RUN1"


def p_calc_height_source_shape(world: MovementWorld, player: MovementPlayer) -> None:
    mo = world.mobjs[player.mo_index]
    onground = mo.z <= mo.floorz
    bob = _i32(_fixed_mul(mo.momx, mo.momx) + _fixed_mul(mo.momy, mo.momy)) >> 2
    if bob > MAXBOB:
        bob = MAXBOB
    player.bob = bob
    if (player.cheats & CF_NOMOMENTUM) or not onground:
        player.viewz = mo.z + player.viewheight
        return

    angle = ((8192 // 20) * world.leveltime) & FINEMASK
    view_bob = _fixed_mul(_c_div(player.bob, 2), FINESINE[angle])
    if player.playerstate == PST_LIVE:
        player.viewheight += player.deltaviewheight
        if player.viewheight > VIEWHEIGHT:
            player.viewheight = VIEWHEIGHT
            player.deltaviewheight = 0
        if player.viewheight < VIEWHEIGHT // 2:
            player.viewheight = VIEWHEIGHT // 2
            if player.deltaviewheight <= 0:
                player.deltaviewheight = 1
        if player.deltaviewheight:
            player.deltaviewheight += FRACUNIT // 4
            if not player.deltaviewheight:
                player.deltaviewheight = 1
    player.viewz = mo.z + player.viewheight + view_bob
    if player.viewz > mo.ceilingz - 4 * FRACUNIT:
        player.viewz = mo.ceilingz - 4 * FRACUNIT


def p_player_think_movement_source_shape(world: MovementWorld, player: MovementPlayer) -> None:
    mo = world.mobjs[player.mo_index]
    if player.cheats & CF_NOCLIP:
        mo.flags |= stage13.MF_NOCLIP
    else:
        mo.flags &= ~stage13.MF_NOCLIP
    if player.playerstate != PST_LIVE:
        return
    if mo.reactiontime:
        mo.reactiontime -= 1
    else:
        p_move_player_source_shape(world, player)
    p_calc_height_source_shape(world, player)


def p_xy_movement_source_shape(world: MovementWorld, mo: MovementMobj) -> None:
    world.counters.xy_movement_calls += 1
    if not mo.momx and not mo.momy:
        return
    if mo.momx > MAXMOVE:
        mo.momx = MAXMOVE
    elif mo.momx < -MAXMOVE:
        mo.momx = -MAXMOVE
    if mo.momy > MAXMOVE:
        mo.momy = MAXMOVE
    elif mo.momy < -MAXMOVE:
        mo.momy = -MAXMOVE

    xmove = mo.momx
    ymove = mo.momy
    while xmove or ymove:
        if xmove > MAXMOVE // 2 or ymove > MAXMOVE // 2:
            ptryx = mo.x + _c_div(xmove, 2)
            ptryy = mo.y + _c_div(ymove, 2)
            xmove >>= 1
            ymove >>= 1
        else:
            ptryx = mo.x + xmove
            ptryy = mo.y + ymove
            xmove = 0
            ymove = 0
        if not p_try_move_source_shape(world, mo, ptryx, ptryy):
            if mo.has_player:
                world.counters.slide_attempts += 1
                world.counters.slide_deferred += 1
                mo.momx = 0
                mo.momy = 0
                break
            mo.momx = 0
            mo.momy = 0
            break

    if mo.has_player and world.player.cheats & CF_NOMOMENTUM:
        mo.momx = 0
        mo.momy = 0
        return
    if mo.flags & (stage13.MF_MISSILE | stage13.MF_SKULLFLY):
        return
    if mo.z > mo.floorz:
        return
    if (
        -STOPSPEED < mo.momx < STOPSPEED
        and -STOPSPEED < mo.momy < STOPSPEED
        and (not mo.has_player or (world.player.cmd.forwardmove == 0 and world.player.cmd.sidemove == 0))
    ):
        if mo.has_player and mo.state_name.startswith("S_PLAY_RUN"):
            mo.state_name = "S_PLAY"
        mo.momx = 0
        mo.momy = 0
    else:
        mo.momx = _fixed_mul(mo.momx, FRICTION)
        mo.momy = _fixed_mul(mo.momy, FRICTION)


def p_ticker_single_player_source_shape(world: MovementWorld) -> None:
    world.counters.p_ticker_calls += 1
    p_player_think_movement_source_shape(world, world.player)
    p_xy_movement_source_shape(world, world.mobjs[world.player.mo_index])
    world.leveltime += 1


def g_ticker_ticcmd_dispatch_source_shape(world: MovementWorld, cmd: TicCmd) -> None:
    world.counters.g_ticker_calls += 1
    world.player.cmd = cmd
    p_ticker_single_player_source_shape(world)


def r_setup_frame_after_movement_source_shape(world: MovementWorld, *, framecount: int = 1) -> FrameSetupRecord:
    mo = world.mobjs[world.player.mo_index]
    angle = _u32(mo.angle)
    fine = fine_index(angle)
    world.validcount += 1
    return FrameSetupRecord(
        viewx=mo.x,
        viewy=mo.y,
        viewz=world.player.viewz,
        viewangle=angle,
        viewangle_degrees=angle_to_degrees(angle),
        viewcos=FINECOSINE[fine],
        viewsin=FINESINE[fine],
        subsector=mo.subsector,
        sector=mo.sector,
        framecount=framecount,
        validcount=world.validcount,
    )


def _copy_stage13_mobj(mobj: stage13.RenderMobj) -> MovementMobj:
    return MovementMobj(
        index=mobj.index,
        mapthing_index=mobj.mapthing_index,
        type_name=mobj.type_name,
        doomednum=mobj.doomednum,
        x=mobj.x,
        y=mobj.y,
        z=mobj.z,
        angle=mobj.angle,
        momx=0,
        momy=0,
        momz=0,
        radius=mobj.radius,
        height=mobj.height,
        flags=mobj.flags,
        floorz=mobj.floorz,
        ceilingz=mobj.ceilingz,
        subsector=mobj.subsector,
        sector=mobj.sector,
        player_index=mobj.player_index,
        reactiontime=0,
        state_name="S_PLAY" if mobj.player_index >= 0 else "S_INERT",
    )


def build_movement_world_for_stage13(
    wad: WadFile,
    loaded: LoadedMap,
    ref13: stage13.Stage13ThingsSpritesReference,
) -> MovementWorld:
    block_data = wad.read_lump(wad.map_lumps("MAP01").get("BLOCKMAP"))
    blockmap = p_load_blockmap_source_shape(block_data, num_lines=len(loaded.linedefs))
    geometry = stage13.build_map_geometry(wad, loaded)
    sectors = build_movement_sectors(loaded)
    lines = build_movement_lines(loaded)
    mobjs = [_copy_stage13_mobj(mobj) for mobj in ref13.spawn.mobjs]
    player = MovementPlayer(
        player_index=ref13.player.player_index,
        mo_index=ref13.player.mobj_index,
        cmd=TicCmd(),
        viewz=ref13.player.viewz,
    )
    world = MovementWorld(
        loaded=loaded,
        geometry=geometry,
        blockmap=blockmap,
        sectors=sectors,
        lines=lines,
        mobjs=mobjs,
        player=player,
        blocklinks=[None] * blockmap.block_count,
        sectorlinks=[None] * len(sectors),
        iterator=BlockIteratorState(),
        counters=MovementCounters(),
    )
    for mobj in world.mobjs:
        p_set_thing_position_source_shape(world, mobj)
    world.counters.set_links = 0
    world.counters.block_relinks = 0
    world.counters.sector_relinks = 0
    return world


def run_scripted_movement_source_shape(
    world: MovementWorld,
    script: Sequence[TicCmd],
) -> tuple[MovementTraceRecord, ...]:
    trace: list[MovementTraceRecord] = []
    for tic, cmd in enumerate(script):
        before_accept = world.counters.accepted_moves
        before_reject = world.counters.rejected_moves
        before_lines = world.counters.line_checks
        before_things = world.counters.thing_checks
        g_ticker_ticcmd_dispatch_source_shape(world, cmd)
        world.counters.tic_count += 1
        mo = world.mobjs[world.player.mo_index]
        trace.append(
            MovementTraceRecord(
                tic=tic,
                forwardmove=cmd.forwardmove,
                sidemove=cmd.sidemove,
                angleturn=cmd.angleturn,
                x=mo.x,
                y=mo.y,
                angle_degrees=angle_to_degrees(mo.angle),
                momx=mo.momx,
                momy=mo.momy,
                viewz=world.player.viewz,
                accepted_moves=world.counters.accepted_moves - before_accept,
                rejected_moves=world.counters.rejected_moves - before_reject,
                line_checks=world.counters.line_checks - before_lines,
                thing_checks=world.counters.thing_checks - before_things,
            )
        )
    return tuple(trace)


def select_blocking_line_probe(world: MovementWorld) -> CollisionProbeResult:
    probe_world = clone_movement_world(world)
    player_mo = probe_world.mobjs[probe_world.player.mo_index]
    for line in probe_world.lines:
        if line.backsector is not None and not (line.flags & ML_BLOCKING):
            continue
        target_x = _c_div(line.v1x + line.v2x, 2)
        target_y = _c_div(line.v1y + line.v2y, 2)
        before_lines = probe_world.counters.line_checks
        before_things = probe_world.counters.thing_checks
        before_blocking_lines = probe_world.counters.blocking_lines
        before_blocking_things = probe_world.counters.blocking_things
        blocked = 0 if p_try_move_source_shape(probe_world, player_mo, target_x, target_y) else 1
        if blocked and probe_world.counters.blocking_lines > before_blocking_lines:
            return CollisionProbeResult(
                active=1,
                line_index=line.index,
                target_x=target_x,
                target_y=target_y,
                blocked=1,
                line_checks=probe_world.counters.line_checks - before_lines,
                thing_checks=probe_world.counters.thing_checks - before_things,
                blocking_lines=probe_world.counters.blocking_lines - before_blocking_lines,
                blocking_things=probe_world.counters.blocking_things - before_blocking_things,
            )
    return CollisionProbeResult(0, 0, 0, 0, 0, 0, 0, 0, 0)


def clone_movement_world(world: MovementWorld) -> MovementWorld:
    cloned = MovementWorld(
        loaded=world.loaded,
        geometry=world.geometry,
        blockmap=world.blockmap,
        sectors=list(world.sectors),
        lines=list(world.lines),
        mobjs=[replace(mobj) for mobj in world.mobjs],
        player=replace(world.player),
        blocklinks=[None] * world.blockmap.block_count,
        sectorlinks=[None] * len(world.sectors),
        iterator=BlockIteratorState(),
        counters=MovementCounters(),
        leveltime=world.leveltime,
        validcount=world.validcount,
    )
    for mobj in cloned.mobjs:
        mobj.bnext = mobj.bprev = mobj.snext = mobj.sprev = None
        p_set_thing_position_source_shape(cloned, mobj)
    cloned.counters = MovementCounters()
    return cloned


def _stage14_signature(
    ref13: stage13.Stage13ThingsSpritesReference,
    trace: Sequence[MovementTraceRecord],
    counters: MovementCounters,
    iterator: BlockIteratorState,
    frame: FrameSetupRecord,
    probe: CollisionProbeResult,
) -> int:
    signature = ref13.draw.framebuffer_signature
    for record in trace:
        for value in (
            record.tic,
            record.forwardmove,
            record.sidemove,
            record.angleturn,
            record.x,
            record.y,
            record.angle_degrees,
            record.momx,
            record.momy,
            record.viewz,
            record.accepted_moves,
            record.rejected_moves,
            record.line_checks,
            record.thing_checks,
        ):
            signature = _hash_u32(signature, value)
    for value in (
        counters.accepted_moves,
        counters.rejected_moves,
        counters.blocking_lines,
        counters.blocking_things,
        counters.special_things_deferred,
        iterator.line_iterator_calls,
        iterator.thing_iterator_calls,
        iterator.line_duplicate_skips,
        frame.viewx,
        frame.viewy,
        frame.viewz,
        frame.viewangle_degrees,
        frame.subsector,
        frame.sector,
        probe.active,
        probe.line_index,
        probe.blocking_lines,
    ):
        signature = _hash_u32(signature, value)
    return signature


def _reference_stage14_uncached(wad_path: str) -> Stage14GameLoopInputCollisionReference:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    ref13 = stage13.reference_things_sprites_real_frame_setup_for_pinned_map(wad_path)
    world = build_movement_world_for_stage13(wad, loaded, ref13)
    script = tuple(TicCmd(*values) for values in DEFAULT_SCRIPT)
    trace = run_scripted_movement_source_shape(world, script)
    frame = r_setup_frame_after_movement_source_shape(world)
    probe = select_blocking_line_probe(world)
    signature = _stage14_signature(ref13, trace, world.counters, world.iterator, frame, probe)

    return Stage14GameLoopInputCollisionReference(
        stage13=ref13,
        blockmap=world.blockmap,
        initial_player=ref13.player,
        final_mobj=replace(world.mobjs[world.player.mo_index]),
        final_player=replace(world.player),
        frame=frame,
        script=script,
        trace=trace,
        counters=replace(world.counters),
        iterator=replace(world.iterator, line_validcounts=dict(world.iterator.line_validcounts or {})),
        probe=probe,
        signature=signature,
    )


@lru_cache(maxsize=4)
def _reference_stage14_cached(wad_path: str) -> Stage14GameLoopInputCollisionReference:
    return _reference_stage14_uncached(wad_path)


def reference_game_loop_input_collision_for_pinned_map(
    wad_path: str | Path,
) -> Stage14GameLoopInputCollisionReference:
    return _reference_stage14_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage14GameLoopInputCollisionReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_game_loop_input_collision_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage14_load_wad_game_loop_input_collision")

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
    x86.test_eax_eax(pe)
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


def emit_source_stage14_load_wad_game_loop_input_collision(pe: PE32) -> None:
    pe.label("source_stage14_load_wad_game_loop_input_collision")
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
    x86.jne_rel32(pe, "source_stage14_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage14_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage14_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage14_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage14_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage14_close_and_return")

    pe.label("source_stage14_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage14_close_and_return")
    x86.call_rel32(pe, "render_init_texture_data_setup_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage14_close_and_return")
    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage14_close_and_return")
    x86.call_rel32(pe, "source_stage06_run_live_seg_clip_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage14_close_and_return")

    x86.call_rel32(pe, "render_composite_two_sided_wall_edges_debug")
    x86.call_rel32(pe, "render_visplanes_floor_ceiling_debug")
    x86.call_rel32(pe, "render_sky_and_masked_midtextures_debug")
    x86.call_rel32(pe, "render_things_sprites_real_frame_setup_debug")
    x86.call_rel32(pe, "render_game_loop_input_collision_debug")
    x86.call_rel32(pe, "build_success_status")
    x86.call_rel32(pe, "append_stage13_success_status")
    x86.call_rel32(pe, "append_stage14_success_status")

    pe.label("source_stage14_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_render_game_loop_input_collision_debug(pe: PE32) -> None:
    pe.label("P_LoadBlockMap_source_shape_debug")
    pe.label("P_BlockIterators_source_shape_debug")
    pe.label("P_LineBBoxHelpers_source_shape_debug")
    pe.label("PIT_CheckLineThing_source_shape_debug")
    pe.label("P_CheckPosition_TryMove_source_shape_debug")
    pe.label("P_PlayerThinkMovement_source_shape_debug")
    pe.label("P_XYMovementRelink_source_shape_debug")
    pe.label("P_Ticker_single_player_source_shape_debug")
    pe.label("G_Ticker_ticcmd_dispatch_source_shape_debug")
    pe.label("D_DoomLoop_frame_boundary_reference_debug")
    pe.label("TryRunTics_command_boundary_reference_debug")
    pe.label("R_SetupFrame_after_movement_source_shape_debug")
    pe.label("render_game_loop_input_collision_debug")

    x86.mov_reg_mem_abs32(pe, "eax", "stage14_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage14_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage14_script_tics")
    x86.mov_mem_abs32_eax(pe, "stage14_runtime_tics")
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    x86.mov_reg_abs32(pe, "esi", buffer_label)
    pe.label(f"{prefix}_seek_loop")
    x86.mov_al_ptr_esi(pe)
    x86.cmp_al_imm8(pe, 0)
    x86.je_rel32(pe, f"{prefix}_seek_done")
    x86.inc_reg(pe, "esi")
    x86.jmp_rel32(pe, f"{prefix}_seek_loop")
    pe.label(f"{prefix}_seek_done")
    x86.mov_reg_reg(pe, "edi", "esi")


def emit_append_stage14_success_status(pe: PE32) -> None:
    pe.label("append_stage14_success_status")

    _emit_seek_buffer_end(pe, "status_success_buffer", "stage14_status")
    stage01.append_c_string_label(pe, "status_stage14_success_header")
    stage01.append_u32_label(pe, "status_stage14_tic_prefix", "stage14_script_tics")
    stage01.append_u32_label(pe, "status_stage14_moves_prefix", "stage14_accepted_moves")
    stage01.append_u32_label(pe, "status_stage14_lines_prefix", "stage14_line_checks")
    stage01.append_u32_label(pe, "status_stage14_signature_prefix", "stage14_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage14_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage14_title")
    stage01.append_u32_label(pe, "title_stage14_bmap_width_prefix", "stage14_bmap_width")
    stage01.append_u32_label(pe, "title_stage14_bmap_height_prefix", "stage14_bmap_height")
    stage01.append_u32_label(pe, "title_stage14_tic_prefix", "stage14_script_tics")
    stage01.append_i32_label(pe, "title_stage14_initial_x_prefix", "stage14_initial_x")
    stage01.append_i32_label(pe, "title_stage14_initial_y_prefix", "stage14_initial_y")
    stage01.append_i32_label(pe, "title_stage14_final_x_prefix", "stage14_final_x")
    stage01.append_i32_label(pe, "title_stage14_final_y_prefix", "stage14_final_y")
    stage01.append_u32_label(pe, "title_stage14_final_angle_prefix", "stage14_final_angle_degrees")
    stage01.append_u32_label(pe, "title_stage14_final_subsector_prefix", "stage14_final_subsector")
    stage01.append_u32_label(pe, "title_stage14_final_sector_prefix", "stage14_final_sector")
    stage01.append_u32_label(pe, "title_stage14_final_viewz_prefix", "stage14_final_viewz")
    stage01.append_i32_label(pe, "title_stage14_final_momx_prefix", "stage14_final_momx")
    stage01.append_i32_label(pe, "title_stage14_final_momy_prefix", "stage14_final_momy")
    stage01.append_u32_label(pe, "title_stage14_accept_prefix", "stage14_accepted_moves")
    stage01.append_u32_label(pe, "title_stage14_reject_prefix", "stage14_rejected_moves")
    stage01.append_u32_label(pe, "title_stage14_line_checks_prefix", "stage14_line_checks")
    stage01.append_u32_label(pe, "title_stage14_thing_checks_prefix", "stage14_thing_checks")
    stage01.append_u32_label(pe, "title_stage14_line_iter_prefix", "stage14_line_iterator_calls")
    stage01.append_u32_label(pe, "title_stage14_thing_iter_prefix", "stage14_thing_iterator_calls")
    stage01.append_u32_label(pe, "title_stage14_dupe_prefix", "stage14_line_duplicate_skips")
    stage01.append_u32_label(pe, "title_stage14_special_deferred_prefix", "stage14_special_things_deferred")
    stage01.append_u32_label(pe, "title_stage14_probe_prefix", "stage14_probe_active")
    stage01.append_u32_label(pe, "title_stage14_probe_line_prefix", "stage14_probe_line")
    stage01.append_u32_label(pe, "title_stage14_probe_block_prefix", "stage14_probe_blocked")
    stage01.append_u32_label(pe, "title_stage14_probe_block_line_prefix", "stage14_probe_blocking_lines")
    stage01.append_u32_label(pe, "title_stage14_relink_prefix", "stage14_block_relinks")
    stage01.append_u32_label(pe, "title_stage14_signature_prefix", "stage14_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage14_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    trace0 = ref.trace[0] if ref is not None and ref.trace else None
    trace_last = ref.trace[-1] if ref is not None and ref.trace else None

    pe.align_section(4)
    pe.label("stage14_bmap_origin_x")
    pe.emit_u32((ref.blockmap.origin_x if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage14_bmap_origin_y")
    pe.emit_u32((ref.blockmap.origin_y if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage14_bmap_width")
    pe.emit_u32(ref.blockmap.width if ref is not None else 0)
    pe.label("stage14_bmap_height")
    pe.emit_u32(ref.blockmap.height if ref is not None else 0)
    pe.label("stage14_bmap_block_count")
    pe.emit_u32(ref.blockmap.block_count if ref is not None else 0)
    pe.label("stage14_bmap_first_offset")
    pe.emit_u32(ref.blockmap.offsets[0] if ref is not None and ref.blockmap.offsets else 0)

    pe.label("stage14_script_tics")
    pe.emit_u32(len(ref.script) if ref is not None else 0)
    pe.label("stage14_initial_x")
    pe.emit_u32((ref.initial_player.x >> FRACBITS if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage14_initial_y")
    pe.emit_u32((ref.initial_player.y >> FRACBITS if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage14_final_x")
    pe.emit_u32((ref.final_mobj.x >> FRACBITS if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage14_final_y")
    pe.emit_u32((ref.final_mobj.y >> FRACBITS if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage14_final_x_fixed")
    pe.emit_u32(ref.final_mobj.x if ref is not None else 0)
    pe.label("stage14_final_y_fixed")
    pe.emit_u32(ref.final_mobj.y if ref is not None else 0)
    pe.label("stage14_final_angle")
    pe.emit_u32(ref.final_mobj.angle if ref is not None else 0)
    pe.label("stage14_final_angle_degrees")
    pe.emit_u32(ref.frame.viewangle_degrees if ref is not None else 0)
    pe.label("stage14_final_subsector")
    pe.emit_u32(ref.frame.subsector if ref is not None else 0)
    pe.label("stage14_final_sector")
    pe.emit_u32(ref.frame.sector if ref is not None else 0)
    pe.label("stage14_final_viewz")
    pe.emit_u32(ref.frame.viewz if ref is not None else 0)
    pe.label("stage14_final_momx")
    pe.emit_u32((ref.final_mobj.momx if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage14_final_momy")
    pe.emit_u32((ref.final_mobj.momy if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage14_frame_viewcos")
    pe.emit_u32(ref.frame.viewcos if ref is not None else 0)
    pe.label("stage14_frame_viewsin")
    pe.emit_u32(ref.frame.viewsin if ref is not None else 0)
    pe.label("stage14_frame_count")
    pe.emit_u32(ref.frame.framecount if ref is not None else 0)
    pe.label("stage14_frame_validcount")
    pe.emit_u32(ref.frame.validcount if ref is not None else 0)

    pe.label("stage14_accepted_moves")
    pe.emit_u32(ref.counters.accepted_moves if ref is not None else 0)
    pe.label("stage14_rejected_moves")
    pe.emit_u32(ref.counters.rejected_moves if ref is not None else 0)
    pe.label("stage14_line_checks")
    pe.emit_u32(ref.counters.line_checks if ref is not None else 0)
    pe.label("stage14_thing_checks")
    pe.emit_u32(ref.counters.thing_checks if ref is not None else 0)
    pe.label("stage14_blocking_lines")
    pe.emit_u32(ref.counters.blocking_lines if ref is not None else 0)
    pe.label("stage14_blocking_things")
    pe.emit_u32(ref.counters.blocking_things if ref is not None else 0)
    pe.label("stage14_special_lines_deferred")
    pe.emit_u32(ref.counters.special_lines_deferred if ref is not None else 0)
    pe.label("stage14_special_things_deferred")
    pe.emit_u32(ref.counters.special_things_deferred if ref is not None else 0)
    pe.label("stage14_line_iterator_calls")
    pe.emit_u32(ref.iterator.line_iterator_calls if ref is not None else 0)
    pe.label("stage14_thing_iterator_calls")
    pe.emit_u32(ref.iterator.thing_iterator_calls if ref is not None else 0)
    pe.label("stage14_line_duplicate_skips")
    pe.emit_u32(ref.iterator.line_duplicate_skips if ref is not None else 0)
    pe.label("stage14_line_overflows")
    pe.emit_u32(ref.iterator.line_overflows if ref is not None else 0)
    pe.label("stage14_thing_overflows")
    pe.emit_u32(ref.iterator.thing_overflows if ref is not None else 0)
    pe.label("stage14_block_relinks")
    pe.emit_u32(ref.counters.block_relinks if ref is not None else 0)
    pe.label("stage14_sector_relinks")
    pe.emit_u32(ref.counters.sector_relinks if ref is not None else 0)
    pe.label("stage14_slide_attempts")
    pe.emit_u32(ref.counters.slide_attempts if ref is not None else 0)
    pe.label("stage14_slide_deferred")
    pe.emit_u32(ref.counters.slide_deferred if ref is not None else 0)

    pe.label("stage14_first_tic_x")
    pe.emit_u32(trace0.x if trace0 is not None else 0)
    pe.label("stage14_first_tic_y")
    pe.emit_u32(trace0.y if trace0 is not None else 0)
    pe.label("stage14_last_tic_x")
    pe.emit_u32(trace_last.x if trace_last is not None else 0)
    pe.label("stage14_last_tic_y")
    pe.emit_u32(trace_last.y if trace_last is not None else 0)

    pe.label("stage14_probe_active")
    pe.emit_u32(ref.probe.active if ref is not None else 0)
    pe.label("stage14_probe_line")
    pe.emit_u32(ref.probe.line_index if ref is not None else 0)
    pe.label("stage14_probe_x")
    pe.emit_u32((ref.probe.target_x >> FRACBITS if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage14_probe_y")
    pe.emit_u32((ref.probe.target_y >> FRACBITS if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage14_probe_blocked")
    pe.emit_u32(ref.probe.blocked if ref is not None else 0)
    pe.label("stage14_probe_line_checks")
    pe.emit_u32(ref.probe.line_checks if ref is not None else 0)
    pe.label("stage14_probe_thing_checks")
    pe.emit_u32(ref.probe.thing_checks if ref is not None else 0)
    pe.label("stage14_probe_blocking_lines")
    pe.emit_u32(ref.probe.blocking_lines if ref is not None else 0)
    pe.label("stage14_probe_blocking_things")
    pe.emit_u32(ref.probe.blocking_things if ref is not None else 0)

    pe.label("stage14_expected_signature")
    pe.emit_u32(ref.signature if ref is not None else 0)
    pe.label("stage14_runtime_signature")
    pe.emit_u32(0)
    pe.label("stage14_runtime_tics")
    pe.emit_u32(0)

    pe.align_section(1)
    pe.label("status_stage14_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage14_game_loop_input_collision\r\n"
        "Scripted local movement and collision OK\r\n",
    )
    pe.label("status_stage14_tic_prefix")
    x86.emit_asciiz(pe, "\r\nScripted ticcmd_t records: ")
    pe.label("status_stage14_moves_prefix")
    x86.emit_asciiz(pe, "\r\nAccepted P_TryMove records: ")
    pe.label("status_stage14_lines_prefix")
    x86.emit_asciiz(pe, "\r\nBLOCKMAP line checks: ")
    pe.label("status_stage14_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage14 movement/frame signature: ")
    pe.label("status_stage14_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage14 follows P_LoadBlockMap for real MAP01 BLOCKMAP data, "
        "uses P_BlockLinesIterator and P_BlockThingsIterator in source order, "
        "runs a bounded ticcmd_t script through the local G_Ticker/P_Ticker "
        "player branch, updates player mobj momentum and links through "
        "P_XYMovement, P_CheckPosition, and P_TryMove, then records the "
        "post-script R_SetupFrame fields. Special touches are counted only.\r\n",
    )

    pe.label("title_stage14_bmap_width_prefix")
    x86.emit_asciiz(pe, " BMW=")
    pe.label("title_stage14_bmap_height_prefix")
    x86.emit_asciiz(pe, " BMH=")
    pe.label("title_stage14_tic_prefix")
    x86.emit_asciiz(pe, " TIC=")
    pe.label("title_stage14_initial_x_prefix")
    x86.emit_asciiz(pe, " I14X=")
    pe.label("title_stage14_initial_y_prefix")
    x86.emit_asciiz(pe, " I14Y=")
    pe.label("title_stage14_final_x_prefix")
    x86.emit_asciiz(pe, " F14X=")
    pe.label("title_stage14_final_y_prefix")
    x86.emit_asciiz(pe, " F14Y=")
    pe.label("title_stage14_final_angle_prefix")
    x86.emit_asciiz(pe, " F14A=")
    pe.label("title_stage14_final_subsector_prefix")
    x86.emit_asciiz(pe, " F14SS=")
    pe.label("title_stage14_final_sector_prefix")
    x86.emit_asciiz(pe, " F14SEC=")
    pe.label("title_stage14_final_viewz_prefix")
    x86.emit_asciiz(pe, " F14VZ=")
    pe.label("title_stage14_final_momx_prefix")
    x86.emit_asciiz(pe, " F14MX=")
    pe.label("title_stage14_final_momy_prefix")
    x86.emit_asciiz(pe, " F14MY=")
    pe.label("title_stage14_accept_prefix")
    x86.emit_asciiz(pe, " ACPT=")
    pe.label("title_stage14_reject_prefix")
    x86.emit_asciiz(pe, " REJ14=")
    pe.label("title_stage14_line_checks_prefix")
    x86.emit_asciiz(pe, " LCHK=")
    pe.label("title_stage14_thing_checks_prefix")
    x86.emit_asciiz(pe, " TCHK=")
    pe.label("title_stage14_line_iter_prefix")
    x86.emit_asciiz(pe, " BLI=")
    pe.label("title_stage14_thing_iter_prefix")
    x86.emit_asciiz(pe, " BTI=")
    pe.label("title_stage14_dupe_prefix")
    x86.emit_asciiz(pe, " LDUP=")
    pe.label("title_stage14_special_deferred_prefix")
    x86.emit_asciiz(pe, " SDEF=")
    pe.label("title_stage14_probe_prefix")
    x86.emit_asciiz(pe, " CPROBE=")
    pe.label("title_stage14_probe_line_prefix")
    x86.emit_asciiz(pe, " CLINE=")
    pe.label("title_stage14_probe_block_prefix")
    x86.emit_asciiz(pe, " CBLK=")
    pe.label("title_stage14_probe_block_line_prefix")
    x86.emit_asciiz(pe, " CBLN=")
    pe.label("title_stage14_relink_prefix")
    x86.emit_asciiz(pe, " RLINK=")
    pe.label("title_stage14_signature_prefix")
    x86.emit_asciiz(pe, " S14SIG=")


def build_source_stage14_game_loop_input_collision_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage14_load_wad_game_loop_input_collision(pe)
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
    emit_render_game_loop_input_collision_debug(pe)
    stage12.emit_build_success_status(pe)
    stage13.emit_append_stage13_success_status(pe)
    emit_append_stage14_success_status(pe)
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
    emit_stage14_data(pe)
    return pe.build("entry")


def write_source_stage14_game_loop_input_collision_exe(path: str | Path) -> bytes:
    image = build_source_stage14_game_loop_input_collision_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage14 game-loop/input/collision PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage14_game_loop_input_collision.exe",
        help="path to write, default: build/source_stage14_game_loop_input_collision.exe",
    )
    args = parser.parse_args()
    write_source_stage14_game_loop_input_collision_exe(args.output)


if __name__ == "__main__":
    main()
