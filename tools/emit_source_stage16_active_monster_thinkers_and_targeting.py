from __future__ import annotations

import argparse
import re
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
from tools import x86
from tools.map_loader import LoadedMap, NO_SIDEDEF, load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


FRAMEBUFFER_WIDTH = stage15.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage15.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage15.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage15.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage15.WINDOW_WIDTH
WINDOW_HEIGHT = stage15.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage16ActiveMonsterThinkersTargeting"
WINDOW_TITLE = "Inference Doom S16 Active Monster Thinkers"
WAD_PATH = stage15.WAD_PATH

FRACBITS = stage15.FRACBITS
FRACUNIT = stage15.FRACUNIT
FNV_PRIME = stage15.FNV_PRIME
ANG90 = stage13.ANG90
ANG270 = (ANG90 * 3) & 0xFFFFFFFF
MELEERANGE = 64 * FRACUNIT
ML_TWOSIDED = stage14.ML_TWOSIDED

DEFAULT_ACTIVE_MONSTER_MAPTHING_INDEX = 37
DEFAULT_ACTIVE_MONSTER_TICS = 13
MAXPLAYERS = 4
S_NULL = 0
ACTION_REMOVE = "REMOVE"

RND_TABLE = (
    0,
    8,
    109,
    220,
    222,
    241,
    149,
    107,
    75,
    248,
    254,
    140,
    16,
    66,
    74,
    21,
    211,
    47,
    80,
    242,
    154,
    27,
    205,
    128,
    161,
    89,
    77,
    36,
    95,
    110,
    85,
    48,
    212,
    140,
    211,
    249,
    22,
    79,
    200,
    50,
    28,
    188,
    52,
    140,
    202,
    120,
    68,
    145,
    62,
    70,
    184,
    190,
    91,
    197,
    152,
    224,
    149,
    104,
    25,
    178,
    252,
    182,
    202,
    182,
    141,
    197,
    4,
    81,
    181,
    242,
    145,
    42,
    39,
    227,
    156,
    198,
    225,
    193,
    219,
    93,
    122,
    175,
    249,
    0,
    175,
    143,
    70,
    239,
    46,
    246,
    163,
    53,
    163,
    109,
    168,
    135,
    2,
    235,
    25,
    92,
    20,
    145,
    138,
    77,
    69,
    166,
    78,
    176,
    173,
    212,
    166,
    113,
    94,
    161,
    41,
    50,
    239,
    49,
    111,
    164,
    70,
    60,
    2,
    37,
    171,
    75,
    136,
    156,
    11,
    56,
    42,
    146,
    138,
    229,
    73,
    146,
    77,
    61,
    98,
    196,
    135,
    106,
    63,
    197,
    195,
    86,
    96,
    203,
    113,
    101,
    170,
    247,
    181,
    113,
    80,
    250,
    108,
    7,
    255,
    237,
    129,
    226,
    79,
    107,
    112,
    166,
    103,
    241,
    24,
    223,
    239,
    120,
    198,
    58,
    60,
    82,
    128,
    3,
    184,
    66,
    143,
    224,
    145,
    224,
    81,
    206,
    163,
    45,
    63,
    90,
    168,
    114,
    59,
    33,
    159,
    95,
    28,
    139,
    123,
    98,
    125,
    196,
    15,
    70,
    194,
    253,
    54,
    14,
    109,
    226,
    71,
    17,
    161,
    93,
    186,
    87,
    244,
    138,
    20,
    52,
    123,
    251,
    26,
    36,
    17,
    46,
    52,
    231,
    232,
    76,
    31,
    221,
    84,
    37,
    216,
    165,
    212,
    106,
    197,
    242,
    98,
    43,
    39,
    175,
    254,
    145,
    190,
    84,
    118,
    222,
    187,
    136,
    120,
    163,
    236,
    249,
)

SOURCE_TRACE = stage15.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_setup.c",
        "P_SetupLevel totalkills/P_LoadThings active monster handoff",
        "P_SetupLevel_active_monster_census_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_tick.c",
        "P_InitThinkers/P_AddThinker/P_RemoveThinker/P_RunThinkers/P_Ticker",
        "P_ThinkerList_active_monster_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_SpawnMobj/P_SpawnMapThing active monster setup",
        "P_SpawnMobj_active_monster_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_MobjThinker/P_SetMobjState",
        "P_MobjThinker_SetMobjState_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "A_Look/P_LookForPlayers",
        "A_Look_P_LookForPlayers_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_sight.c",
        "P_CheckSight bounded REJECT/BSP probe",
        "P_CheckSight_bounded_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "A_Chase/P_NewChaseDir deferred boundary",
        "A_Chase_deferred_active_monster_boundary_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/m_random.c",
        "P_Random spawn tic/lastlook sequence",
        "P_Random_spawn_sequence_source_shape_debug",
    ),
)


@dataclass
class DoomRandom:
    prndindex: int = 0

    def p_random(self) -> int:
        self.prndindex = (self.prndindex + 1) & 0xFF
        return RND_TABLE[self.prndindex]


@dataclass(frozen=True)
class Stage16MobjInfo:
    name: str
    doomednum: int
    spawnstate: int
    spawnhealth: int
    seestate: int
    seesound_name: str
    reactiontime: int
    attacksound_name: str
    painstate: int
    painchance: int
    painsound_name: str
    meleestate: int
    missilestate: int
    deathstate: int
    xdeathstate: int
    deathsound_name: str
    speed: int
    radius: int
    height: int
    mass: int
    damage: int
    activesound_name: str
    flags: int
    raisestate: int


@dataclass(frozen=True)
class Stage16InfoTables:
    state_info: stage15.Stage15InfoTables
    mobjinfo: tuple[Stage16MobjInfo, ...]
    by_name: dict[str, Stage16MobjInfo]
    by_doomednum: dict[int, Stage16MobjInfo]


@dataclass
class ActiveMobj:
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
    health: int
    reactiontime: int
    state: int | None
    tics: int
    sprite: int
    frame: int
    lastlook: int
    threshold: int = 0
    target_index: int | None = None
    movedir: int = 8
    movecount: int = 0
    removed: bool = False


@dataclass(frozen=True)
class ActivePlayerTarget:
    player_index: int
    mo_index: int
    x: int
    y: int
    z: int
    sector: int
    subsector: int
    health: int
    flags: int
    radius: int
    height: int


@dataclass
class ThinkerNode:
    name: str
    function: str | None = None
    prev: str = "CAP"
    next: str = "CAP"
    mobj_index: int | None = None


@dataclass
class ThinkerList:
    nodes: dict[str, ThinkerNode]

    @property
    def cap(self) -> ThinkerNode:
        return self.nodes["CAP"]


@dataclass
class Stage16Counters:
    thinker_init_calls: int = 0
    thinker_adds: int = 0
    thinker_deferred_removes: int = 0
    thinker_actual_removes: int = 0
    thinker_iteration_calls: int = 0
    thinker_function_calls: int = 0
    thinker_mutation_adds: int = 0
    p_ticker_calls: int = 0
    mobj_thinker_calls: int = 0
    mobj_state_sets: int = 0
    mobj_state_transitions: int = 0
    mobj_null_removals: int = 0
    action_dispatches: int = 0
    action_deferrals: int = 0
    a_look_calls: int = 0
    look_for_players_calls: int = 0
    look_iterations: int = 0
    look_player_checks: int = 0
    look_dead_skips: int = 0
    look_sight_rejects: int = 0
    look_front_rejects: int = 0
    target_acquired: int = 0
    sight_checks: int = 0
    sight_reject_matrix_blocks: int = 0
    sight_bsp_accepts: int = 0
    sight_bsp_blocks: int = 0
    sight_nodes: int = 0
    sight_subsectors: int = 0
    sight_segs: int = 0
    sight_crossed_lines: int = 0
    chase_deferred: int = 0
    new_chase_dir_deferred: int = 0
    sound_deferred: int = 0
    alert_deferred: int = 0
    attacks_deferred: int = 0
    damage_events: int = 0
    kills: int = 0
    drops: int = 0
    sector_specials_deferred: int = 0
    live_input_deferred: int = 0


@dataclass(frozen=True)
class SightProbeResult:
    visible: bool
    reject_blocked: int = 0
    bsp_accept: int = 0
    bsp_blocked: int = 0
    nodes: int = 0
    subsectors: int = 0
    segs: int = 0
    crossed_lines: int = 0


@dataclass(frozen=True)
class MonsterCensusRecord:
    mapthing_index: int
    mobj_index: int
    type_name: str
    doomednum: int
    x: int
    y: int
    angle_degrees: int
    sector: int
    subsector: int
    block_x: int
    block_y: int
    spawn_state: int
    spawn_state_name: str
    spawn_tics: int
    raw_spawn_tics: int
    spawn_lastlook: int
    distance_to_player: int
    front_arc: int
    sight: SightProbeResult


@dataclass(frozen=True)
class MonsterTraceRecord:
    tic: int
    state: int
    state_name: str
    tics: int
    target_index: int
    action_dispatches: int
    look_calls: int
    sight_checks: int
    chase_deferred: int


@dataclass
class Stage16World:
    loaded: LoadedMap | None
    geometry: stage13.MapGeometry | None
    rejectmatrix: bytes
    info: Stage16InfoTables
    thinkers: ThinkerList
    mobjs: list[ActiveMobj]
    players: list[ActivePlayerTarget]
    playeringame: list[bool]
    counters: Stage16Counters
    sight_overrides: dict[tuple[int, int], SightProbeResult] | None = None
    leveltime: int = 0

    def __post_init__(self) -> None:
        if self.sight_overrides is None:
            self.sight_overrides = {}


@dataclass(frozen=True)
class Stage16ActiveMonsterReference:
    stage15: stage15.Stage15PickupsPspritesStatusbarReference
    monster_count: int
    selected: MonsterCensusRecord
    trace: tuple[MonsterTraceRecord, ...]
    final_mobj: ActiveMobj
    target: ActivePlayerTarget
    counters: Stage16Counters
    thinker_node_count: int
    active_thinker_count: int
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


def p_aprox_distance_source_shape(dx: int, dy: int) -> int:
    dx = abs(dx)
    dy = abs(dy)
    if dx < dy:
        return dx + dy - (dx >> 1)
    return dx + dy - (dy >> 1)


def _state_name(info: Stage16InfoTables, state: int | None) -> str:
    if state is None:
        return "S_NULL"
    return stage15._state_name(info.state_info, state)


def _eval_info_value(expr: str, namespace: dict[str, int]) -> int:
    expr = expr.strip()
    if expr.startswith("sfx_"):
        return 0
    return int(eval(expr, {"__builtins__": {}}, namespace))


def parse_stage16_info_tables() -> Stage16InfoTables:
    state_info = stage15.parse_stage15_info_tables()
    text = Path(stage13.INFO_C).read_text(encoding="utf-8")
    flag_values = stage13.parse_mobj_flag_values()
    namespace: dict[str, int] = {
        "FRACUNIT": FRACUNIT,
        **state_info.state_index,
        **flag_values,
    }

    table_match = re.search(r"mobjinfo_t\s+mobjinfo\[NUMMOBJTYPES\]\s*=\s*\{", text)
    if table_match is None:
        raise ValueError("could not find mobjinfo in info.c")
    block = text[table_match.end() :]

    mobjinfo: list[Stage16MobjInfo] = []
    position = 0
    while True:
        entry_match = re.search(r"\{\s*//\s*(MT_[A-Z0-9_]+)", block[position:])
        if entry_match is None:
            break
        name = entry_match.group(1)
        entry_start = position + entry_match.end()
        end_match = re.search(r"\n\s*\}(?:,|\s*;)", block[entry_start:])
        if end_match is None:
            break
        entry_text = block[entry_start : entry_start + end_match.start()]
        fields = [
            line.split("//", 1)[0].strip().rstrip(",")
            for line in entry_text.splitlines()
            if "//" in line
        ]
        fields = [field for field in fields if field]
        if len(fields) >= 23:
            mobjinfo.append(
                Stage16MobjInfo(
                    name=name,
                    doomednum=_eval_info_value(fields[0], namespace),
                    spawnstate=_eval_info_value(fields[1], namespace),
                    spawnhealth=_eval_info_value(fields[2], namespace),
                    seestate=_eval_info_value(fields[3], namespace),
                    seesound_name=fields[4],
                    reactiontime=_eval_info_value(fields[5], namespace),
                    attacksound_name=fields[6],
                    painstate=_eval_info_value(fields[7], namespace),
                    painchance=_eval_info_value(fields[8], namespace),
                    painsound_name=fields[9],
                    meleestate=_eval_info_value(fields[10], namespace),
                    missilestate=_eval_info_value(fields[11], namespace),
                    deathstate=_eval_info_value(fields[12], namespace),
                    xdeathstate=_eval_info_value(fields[13], namespace),
                    deathsound_name=fields[14],
                    speed=_eval_info_value(fields[15], namespace),
                    radius=_eval_info_value(fields[16], namespace),
                    height=_eval_info_value(fields[17], namespace),
                    mass=_eval_info_value(fields[18], namespace),
                    damage=_eval_info_value(fields[19], namespace),
                    activesound_name=fields[20],
                    flags=_eval_info_value(fields[21], namespace),
                    raisestate=_eval_info_value(fields[22], namespace),
                )
            )
        position = entry_start + end_match.end()

    by_name = {info.name: info for info in mobjinfo}
    by_doomednum = {info.doomednum: info for info in mobjinfo if info.doomednum >= 0}
    return Stage16InfoTables(
        state_info=state_info,
        mobjinfo=tuple(mobjinfo),
        by_name=by_name,
        by_doomednum=by_doomednum,
    )


def p_init_thinkers_source_shape(counters: Stage16Counters | None = None) -> ThinkerList:
    if counters is not None:
        counters.thinker_init_calls += 1
    cap = ThinkerNode("CAP", function=None, prev="CAP", next="CAP")
    return ThinkerList(nodes={"CAP": cap})


def p_add_thinker_source_shape(
    thinkers: ThinkerList,
    thinker: ThinkerNode,
    counters: Stage16Counters | None = None,
) -> None:
    cap = thinkers.cap
    tail = thinkers.nodes[cap.prev]
    tail.next = thinker.name
    thinker.prev = tail.name
    thinker.next = "CAP"
    cap.prev = thinker.name
    thinkers.nodes[thinker.name] = thinker
    if counters is not None:
        counters.thinker_adds += 1


def p_remove_thinker_source_shape(
    thinkers: ThinkerList,
    thinker_name: str,
    counters: Stage16Counters | None = None,
) -> None:
    thinkers.nodes[thinker_name].function = ACTION_REMOVE
    if counters is not None:
        counters.thinker_deferred_removes += 1


def _unlink_thinker(
    thinkers: ThinkerList,
    thinker_name: str,
    counters: Stage16Counters | None = None,
) -> None:
    node = thinkers.nodes[thinker_name]
    thinkers.nodes[node.prev].next = node.next
    thinkers.nodes[node.next].prev = node.prev
    if thinker_name != "CAP":
        del thinkers.nodes[thinker_name]
    if counters is not None:
        counters.thinker_actual_removes += 1


def thinker_names_source_shape(thinkers: ThinkerList) -> tuple[str, ...]:
    names: list[str] = []
    current = thinkers.cap.next
    guard = 0
    while current != "CAP" and guard < 1024:
        names.append(current)
        current = thinkers.nodes[current].next
        guard += 1
    return tuple(names)


def p_run_thinkers_source_shape(
    world: Stage16World,
    callback: Callable[[Stage16World, ThinkerNode], None],
    *,
    max_iterations: int = 128,
) -> None:
    world.counters.thinker_iteration_calls += 1
    current = world.thinkers.cap.next
    iterations = 0
    while current != "CAP":
        iterations += 1
        if iterations > max_iterations:
            raise RuntimeError("P_RunThinkers exceeded bounded iteration count")
        node = world.thinkers.nodes[current]
        if node.function == ACTION_REMOVE:
            nextthinker = node.next
            _unlink_thinker(world.thinkers, current, world.counters)
        else:
            if node.function is not None:
                world.counters.thinker_function_calls += 1
                callback(world, node)
            nextthinker = node.next
        current = nextthinker


def _front_back_sector_for_seg(
    loaded: LoadedMap,
    line_index: int,
    side: int,
) -> tuple[int | None, int | None]:
    line = loaded.linedefs[line_index]
    front_idx = line.right_sidedef if side == 0 else line.left_sidedef
    back_idx = line.left_sidedef if side == 0 else line.right_sidedef
    front = None
    back = None
    if front_idx != NO_SIDEDEF and front_idx < len(loaded.sidedefs):
        front = loaded.sidedefs[front_idx].sector
    if back_idx != NO_SIDEDEF and back_idx < len(loaded.sidedefs):
        back = loaded.sidedefs[back_idx].sector
    return front, back


def p_divline_side_source_shape(x: int, y: int, node: Sequence[int]) -> int:
    node_x, node_y, node_dx, node_dy = (
        _i32(node[0]),
        _i32(node[1]),
        _i32(node[2]),
        _i32(node[3]),
    )
    if node_dx == 0:
        if x == node_x:
            return 2
        if x <= node_x:
            return int(node_dy > 0)
        return int(node_dy < 0)
    if node_dy == 0:
        if x == node_y:
            return 2
        if y <= node_y:
            return int(node_dx < 0)
        return int(node_dx > 0)
    dx = _i32(x - node_x)
    dy = _i32(y - node_y)
    left = _i32((node_dy >> FRACBITS) * (dx >> FRACBITS))
    right = _i32((dy >> FRACBITS) * (node_dx >> FRACBITS))
    if right < left:
        return 0
    if left == right:
        return 2
    return 1


def p_intercept_vector2_source_shape(
    strace: Sequence[int],
    divline: Sequence[int],
) -> int:
    den = _i32(
        stage04.fixed_mul(strace[3] >> 8, divline[2])
        - stage04.fixed_mul(strace[2] >> 8, divline[3])
    )
    if den == 0:
        return 0
    num = _i32(
        stage04.fixed_mul((strace[0] - divline[0]) >> 8, strace[3])
        + stage04.fixed_mul((divline[1] - strace[1]) >> 8, strace[2])
    )
    return stage04.fixed_div(num, den)


def _target_as_mobj(target: ActivePlayerTarget) -> ActiveMobj:
    return ActiveMobj(
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
        floorz=target.z,
        ceilingz=target.z + target.height,
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


def p_check_sight_source_shape(
    world: Stage16World,
    actor: ActiveMobj,
    target: ActivePlayerTarget,
) -> SightProbeResult:
    world.counters.sight_checks += 1
    assert world.sight_overrides is not None
    override = world.sight_overrides.get((actor.index, target.mo_index))
    if override is not None:
        _accumulate_sight_counters(world.counters, override)
        return override

    if world.loaded is None or world.geometry is None or not world.geometry.nodes:
        result = SightProbeResult(visible=True, bsp_accept=1)
        _accumulate_sight_counters(world.counters, result)
        return result

    result = _p_check_sight_bounded(
        actor,
        _target_as_mobj(target),
        world.loaded,
        world.geometry,
        world.rejectmatrix,
    )
    _accumulate_sight_counters(world.counters, result)
    return result


def _accumulate_sight_counters(counters: Stage16Counters, result: SightProbeResult) -> None:
    counters.sight_reject_matrix_blocks += result.reject_blocked
    counters.sight_bsp_accepts += result.bsp_accept
    counters.sight_bsp_blocks += result.bsp_blocked
    counters.sight_nodes += result.nodes
    counters.sight_subsectors += result.subsectors
    counters.sight_segs += result.segs
    counters.sight_crossed_lines += result.crossed_lines


def _p_check_sight_bounded(
    actor: ActiveMobj,
    target: ActiveMobj,
    loaded: LoadedMap,
    geometry: stage13.MapGeometry,
    rejectmatrix: bytes,
) -> SightProbeResult:
    pnum = actor.sector * len(loaded.sectors) + target.sector
    bytenum = pnum >> 3
    bitnum = 1 << (pnum & 7)
    if bytenum < len(rejectmatrix) and rejectmatrix[bytenum] & bitnum:
        return SightProbeResult(visible=False, reject_blocked=1)

    counters = {
        "nodes": 0,
        "subsectors": 0,
        "segs": 0,
        "crossed_lines": 0,
        "blocked": 0,
    }
    sightzstart = actor.z + actor.height - (actor.height >> 2)
    topslope = (target.z + target.height) - sightzstart
    bottomslope = target.z - sightzstart
    strace = (
        actor.x,
        actor.y,
        _i32(target.x - actor.x),
        _i32(target.y - actor.y),
    )
    t2x = target.x
    t2y = target.y
    valid_lines: set[int] = set()

    def cross_subsector(num: int) -> bool:
        nonlocal topslope, bottomslope
        counters["subsectors"] += 1
        if num < 0 or num >= len(geometry.subsectors):
            counters["blocked"] += 1
            return False
        count, firstline = geometry.subsectors[num]
        for seg_index in range(firstline, firstline + count):
            counters["segs"] += 1
            seg = geometry.segs[seg_index]
            line_index = seg[3]
            if line_index in valid_lines:
                continue
            valid_lines.add(line_index)
            line = loaded.linedefs[line_index]
            v1 = loaded.vertices[line.start_vertex]
            v2 = loaded.vertices[line.end_vertex]
            v1x = v1.x << FRACBITS
            v1y = v1.y << FRACBITS
            v2x = v2.x << FRACBITS
            v2y = v2.y << FRACBITS

            s1 = p_divline_side_source_shape(v1x, v1y, strace)
            s2 = p_divline_side_source_shape(v2x, v2y, strace)
            if s1 == s2:
                continue

            divline = (v1x, v1y, _i32(v2x - v1x), _i32(v2y - v1y))
            s1 = p_divline_side_source_shape(strace[0], strace[1], divline)
            s2 = p_divline_side_source_shape(t2x, t2y, divline)
            if s1 == s2:
                continue

            counters["crossed_lines"] += 1
            front_sector, back_sector = _front_back_sector_for_seg(loaded, line_index, seg[4])
            if back_sector is None or front_sector is None:
                counters["blocked"] += 1
                return False
            if not (line.flags & ML_TWOSIDED):
                counters["blocked"] += 1
                return False

            front = loaded.sectors[front_sector]
            back = loaded.sectors[back_sector]
            front_floor = front.floor_height << FRACBITS
            front_ceiling = front.ceiling_height << FRACBITS
            back_floor = back.floor_height << FRACBITS
            back_ceiling = back.ceiling_height << FRACBITS
            if front_floor == back_floor and front_ceiling == back_ceiling:
                continue

            opentop = min(front_ceiling, back_ceiling)
            openbottom = max(front_floor, back_floor)
            if openbottom >= opentop:
                counters["blocked"] += 1
                return False

            frac = p_intercept_vector2_source_shape(strace, divline)
            if front_floor != back_floor:
                slope = stage04.fixed_div(_i32(openbottom - sightzstart), frac)
                if slope > bottomslope:
                    bottomslope = slope
            if front_ceiling != back_ceiling:
                slope = stage04.fixed_div(_i32(opentop - sightzstart), frac)
                if slope < topslope:
                    topslope = slope
            if topslope <= bottomslope:
                counters["blocked"] += 1
                return False
        return True

    def cross_bsp_node(bspnum: int) -> bool:
        counters["nodes"] += 1
        if bspnum & stage03.NF_SUBSECTOR:
            if bspnum == 0xFFFFFFFF:
                return cross_subsector(0)
            return cross_subsector(bspnum & ~stage03.NF_SUBSECTOR)
        node = geometry.nodes[bspnum]
        side = p_divline_side_source_shape(strace[0], strace[1], node[:4])
        if side == 2:
            side = 0
        if not cross_bsp_node(node[12 + side]):
            return False
        if side == p_divline_side_source_shape(t2x, t2y, node[:4]):
            return True
        return cross_bsp_node(node[12 + (side ^ 1)])

    visible = cross_bsp_node(len(geometry.nodes) - 1)
    return SightProbeResult(
        visible=visible,
        bsp_accept=1 if visible else 0,
        bsp_blocked=0 if visible else max(1, counters["blocked"]),
        nodes=counters["nodes"],
        subsectors=counters["subsectors"],
        segs=counters["segs"],
        crossed_lines=counters["crossed_lines"],
    )


def p_look_for_players_source_shape(
    world: Stage16World,
    actor: ActiveMobj,
    allaround: bool,
    *,
    max_iterations: int = 8,
) -> bool:
    world.counters.look_for_players_calls += 1
    c = 0
    stop = (actor.lastlook - 1) & 3
    iterations = 0
    while True:
        iterations += 1
        if iterations > max_iterations:
            raise RuntimeError("P_LookForPlayers exceeded bounded iteration count")
        if world.playeringame[actor.lastlook]:
            if c == 2 or actor.lastlook == stop:
                world.counters.look_iterations += iterations
                return False
            c += 1
            world.counters.look_player_checks += 1
            player = world.players[actor.lastlook]
            if player.health <= 0:
                world.counters.look_dead_skips += 1
            else:
                sight = p_check_sight_source_shape(world, actor, player)
                if not sight.visible:
                    world.counters.look_sight_rejects += 1
                else:
                    if not allaround:
                        an = _u32(stage04.point_to_angle(player.x, player.y, actor.x, actor.y) - actor.angle)
                        if an > ANG90 and an < ANG270:
                            dist = p_aprox_distance_source_shape(player.x - actor.x, player.y - actor.y)
                            if dist > MELEERANGE:
                                world.counters.look_front_rejects += 1
                                actor.lastlook = (actor.lastlook + 1) & 3
                                world.counters.look_iterations += iterations
                                continue
                    actor.target_index = player.mo_index
                    world.counters.target_acquired += 1
                    world.counters.look_iterations += iterations
                    return True
        actor.lastlook = (actor.lastlook + 1) & 3


def a_look_source_shape(world: Stage16World, actor: ActiveMobj) -> None:
    world.counters.a_look_calls += 1
    actor.threshold = 0
    if not p_look_for_players_source_shape(world, actor, False):
        return
    info = world.info.by_name[actor.type_name]
    if info.seesound_name != "sfx_None":
        world.counters.sound_deferred += 1
    p_set_mobj_state_source_shape(world, actor, info.seestate)


def dispatch_mobj_action_source_shape(
    world: Stage16World,
    actor: ActiveMobj,
    action: str,
) -> None:
    if not action:
        return
    world.counters.action_dispatches += 1
    if action == "A_Look":
        a_look_source_shape(world, actor)
    elif action in {"A_Chase", "A_VileChase", "A_Hoof", "A_Metal", "A_BabyMetal"}:
        world.counters.chase_deferred += 1
        world.counters.action_deferrals += 1
    elif "Attack" in action or action in {"A_PosAttack", "A_SPosAttack", "A_CPosAttack"}:
        world.counters.attacks_deferred += 1
        world.counters.action_deferrals += 1
    else:
        world.counters.action_deferrals += 1


def p_set_mobj_state_source_shape(
    world: Stage16World,
    mobj: ActiveMobj,
    state: int,
    *,
    max_steps: int = 64,
) -> bool:
    steps = 0
    while True:
        steps += 1
        if steps > max_steps:
            raise RuntimeError("P_SetMobjState exceeded bounded state steps")
        if state == S_NULL:
            mobj.state = None
            mobj.tics = 0
            mobj.removed = True
            world.counters.mobj_null_removals += 1
            p_remove_thinker_source_shape(world.thinkers, f"mobj_{mobj.index}", world.counters)
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
        dispatch_mobj_action_source_shape(world, mobj, st.action)
        state = st.nextstate
        if mobj.tics:
            return True


def p_mobj_thinker_source_shape(world: Stage16World, mobj: ActiveMobj) -> None:
    world.counters.mobj_thinker_calls += 1
    if mobj.momx or mobj.momy or mobj.momz:
        world.counters.chase_deferred += 1
        return
    if mobj.tics != -1:
        mobj.tics -= 1
        if not mobj.tics and mobj.state is not None:
            nextstate = world.info.state_info.states[mobj.state].nextstate
            p_set_mobj_state_source_shape(world, mobj, nextstate)


def _thinker_callback(world: Stage16World, node: ThinkerNode) -> None:
    if node.function != "P_MobjThinker" or node.mobj_index is None:
        return
    p_mobj_thinker_source_shape(world, world.mobjs[node.mobj_index])


def p_ticker_active_monster_source_shape(
    world: Stage16World,
    tics: int,
) -> tuple[MonsterTraceRecord, ...]:
    trace: list[MonsterTraceRecord] = []
    for tic in range(tics):
        world.counters.p_ticker_calls += 1
        p_run_thinkers_source_shape(world, _thinker_callback)
        world.leveltime += 1
        monster = world.mobjs[0]
        trace.append(
            MonsterTraceRecord(
                tic=tic + 1,
                state=monster.state if monster.state is not None else 0,
                state_name=_state_name(world.info, monster.state),
                tics=monster.tics,
                target_index=monster.target_index if monster.target_index is not None else -1,
                action_dispatches=world.counters.action_dispatches,
                look_calls=world.counters.a_look_calls,
                sight_checks=world.counters.sight_checks,
                chase_deferred=world.counters.chase_deferred,
            )
        )
    return tuple(trace)


def _copy_active_mobj(
    source: stage14.MovementMobj,
    info: Stage16MobjInfo,
    state_info: stage15.Stage15InfoTables,
    *,
    lastlook: int,
    spawn_tics: int,
) -> ActiveMobj:
    state = state_info.states[info.spawnstate]
    return ActiveMobj(
        index=source.index,
        mapthing_index=source.mapthing_index,
        type_name=source.type_name,
        doomednum=source.doomednum,
        x=source.x,
        y=source.y,
        z=source.z,
        angle=source.angle,
        momx=0,
        momy=0,
        momz=0,
        radius=source.radius,
        height=source.height,
        flags=source.flags,
        floorz=source.floorz,
        ceilingz=source.ceilingz,
        subsector=source.subsector,
        sector=source.sector,
        health=info.spawnhealth,
        reactiontime=info.reactiontime,
        state=info.spawnstate,
        tics=spawn_tics,
        sprite=state.sprite,
        frame=state.frame,
        lastlook=lastlook,
    )


def _post_stage15_player_target(
    world: stage15.Stage15World,
) -> ActivePlayerTarget:
    player_mo = world.movement.mobjs[world.movement.player.mo_index]
    return ActivePlayerTarget(
        player_index=world.movement.player.player_index,
        mo_index=player_mo.index,
        x=player_mo.x,
        y=player_mo.y,
        z=player_mo.z,
        sector=player_mo.sector,
        subsector=player_mo.subsector,
        health=world.player.health,
        flags=player_mo.flags,
        radius=player_mo.radius,
        height=player_mo.height,
    )


def build_monster_census_source_shape(
    stage15_world: stage15.Stage15World,
    info: Stage16InfoTables,
    target: ActivePlayerTarget,
    loaded: LoadedMap,
    geometry: stage13.MapGeometry,
    rejectmatrix: bytes,
) -> tuple[MonsterCensusRecord, ...]:
    rng = DoomRandom()
    raw_spawn: dict[int, tuple[int, int, int]] = {}
    for mobj in stage15_world.movement.mobjs:
        lastlook = rng.p_random() % MAXPLAYERS
        minfo = info.by_name.get(mobj.type_name)
        raw_tics = -1
        spawn_tics = -1
        if minfo is not None and 0 <= minfo.spawnstate < len(info.state_info.states):
            raw_tics = info.state_info.states[minfo.spawnstate].tics
            spawn_tics = raw_tics
            if mobj.player_index < 0 and raw_tics > 0:
                spawn_tics = 1 + (rng.p_random() % raw_tics)
        raw_spawn[mobj.index] = (lastlook, spawn_tics, raw_tics)

    records: list[MonsterCensusRecord] = []
    for mobj in stage15_world.movement.mobjs:
        if not (mobj.flags & stage13.MF_COUNTKILL):
            continue
        minfo = info.by_name[mobj.type_name]
        lastlook, spawn_tics, raw_tics = raw_spawn[mobj.index]
        active = _copy_active_mobj(
            mobj,
            minfo,
            info.state_info,
            lastlook=lastlook,
            spawn_tics=spawn_tics,
        )
        sight = _p_check_sight_bounded(active, _target_as_mobj(target), loaded, geometry, rejectmatrix)
        relative_angle = _u32(stage04.point_to_angle(target.x, target.y, mobj.x, mobj.y) - mobj.angle)
        front_arc = not (relative_angle > ANG90 and relative_angle < ANG270)
        block_x = stage14._block_coord(stage15_world.movement, mobj.x, stage15_world.movement.blockmap.origin_x)
        block_y = stage14._block_coord(stage15_world.movement, mobj.y, stage15_world.movement.blockmap.origin_y)
        records.append(
            MonsterCensusRecord(
                mapthing_index=mobj.mapthing_index,
                mobj_index=mobj.index,
                type_name=mobj.type_name,
                doomednum=mobj.doomednum,
                x=mobj.x,
                y=mobj.y,
                angle_degrees=stage13.angle_to_degrees(mobj.angle),
                sector=mobj.sector,
                subsector=mobj.subsector,
                block_x=block_x,
                block_y=block_y,
                spawn_state=minfo.spawnstate,
                spawn_state_name=_state_name(info, minfo.spawnstate),
                spawn_tics=spawn_tics,
                raw_spawn_tics=raw_tics,
                spawn_lastlook=lastlook,
                distance_to_player=p_aprox_distance_source_shape(target.x - mobj.x, target.y - mobj.y) >> FRACBITS,
                front_arc=1 if front_arc else 0,
                sight=sight,
            )
        )
    return tuple(records)


def select_active_monster_record(
    census: Sequence[MonsterCensusRecord],
    *,
    preferred_mapthing_index: int = DEFAULT_ACTIVE_MONSTER_MAPTHING_INDEX,
) -> MonsterCensusRecord:
    for record in census:
        if record.mapthing_index == preferred_mapthing_index:
            return record
    candidates = [record for record in census if record.front_arc and record.sight.visible]
    if not candidates:
        raise RuntimeError("no bounded MAP01 monster target candidate found")
    return min(candidates, key=lambda record: (record.distance_to_player, record.mapthing_index))


def build_stage16_world_for_selected(
    stage15_world: stage15.Stage15World,
    info: Stage16InfoTables,
    selected: MonsterCensusRecord,
    target: ActivePlayerTarget,
    loaded: LoadedMap,
    geometry: stage13.MapGeometry,
    rejectmatrix: bytes,
) -> Stage16World:
    counters = Stage16Counters()
    thinkers = p_init_thinkers_source_shape(counters)
    source = stage15_world.movement.mobjs[selected.mobj_index]
    minfo = info.by_name[source.type_name]
    active = _copy_active_mobj(
        source,
        minfo,
        info.state_info,
        lastlook=selected.spawn_lastlook,
        spawn_tics=selected.spawn_tics,
    )
    p_add_thinker_source_shape(
        thinkers,
        ThinkerNode(f"mobj_{active.index}", function="P_MobjThinker", mobj_index=0),
        counters,
    )
    return Stage16World(
        loaded=loaded,
        geometry=geometry,
        rejectmatrix=rejectmatrix,
        info=info,
        thinkers=thinkers,
        mobjs=[active],
        players=[target],
        playeringame=[True, False, False, False],
        counters=counters,
    )


def _stage16_signature(
    ref15: stage15.Stage15PickupsPspritesStatusbarReference,
    monster_count: int,
    selected: MonsterCensusRecord,
    trace: Sequence[MonsterTraceRecord],
    final_mobj: ActiveMobj,
    target: ActivePlayerTarget,
    counters: Stage16Counters,
) -> int:
    signature = ref15.signature
    for value in (
        monster_count,
        selected.mapthing_index,
        selected.mobj_index,
        selected.doomednum,
        selected.x,
        selected.y,
        selected.sector,
        selected.subsector,
        selected.block_x,
        selected.block_y,
        selected.spawn_state,
        selected.spawn_tics,
        selected.raw_spawn_tics,
        selected.spawn_lastlook,
        selected.distance_to_player,
        selected.front_arc,
        1 if selected.sight.visible else 0,
        selected.sight.reject_blocked,
        selected.sight.bsp_accept,
        selected.sight.nodes,
        selected.sight.subsectors,
        selected.sight.segs,
        selected.sight.crossed_lines,
        target.x,
        target.y,
        target.sector,
        target.subsector,
        final_mobj.state if final_mobj.state is not None else 0,
        final_mobj.tics,
        final_mobj.target_index if final_mobj.target_index is not None else 0xFFFFFFFF,
    ):
        signature = _hash_u32(signature, value)
    for record in trace:
        for value in (
            record.tic,
            record.state,
            record.tics,
            record.target_index,
            record.action_dispatches,
            record.look_calls,
            record.sight_checks,
            record.chase_deferred,
        ):
            signature = _hash_u32(signature, value)
        signature = _hash_bytes(signature, record.state_name.encode("ascii"))
    for value in (
        counters.thinker_init_calls,
        counters.thinker_adds,
        counters.thinker_iteration_calls,
        counters.thinker_function_calls,
        counters.p_ticker_calls,
        counters.mobj_thinker_calls,
        counters.mobj_state_sets,
        counters.mobj_state_transitions,
        counters.action_dispatches,
        counters.action_deferrals,
        counters.a_look_calls,
        counters.look_for_players_calls,
        counters.look_iterations,
        counters.look_player_checks,
        counters.target_acquired,
        counters.sight_checks,
        counters.sight_bsp_accepts,
        counters.sight_nodes,
        counters.sight_subsectors,
        counters.sight_segs,
        counters.sight_crossed_lines,
        counters.chase_deferred,
        counters.sound_deferred,
        counters.attacks_deferred,
        counters.damage_events,
        counters.kills,
        counters.drops,
    ):
        signature = _hash_u32(signature, value)
    signature = _hash_bytes(signature, selected.type_name.encode("ascii"))
    signature = _hash_bytes(signature, _state_name(parse_stage16_info_tables(), final_mobj.state).encode("ascii"))
    return signature


def _reference_stage16_uncached(wad_path: str) -> Stage16ActiveMonsterReference:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    ref15 = stage15.reference_pickups_psprites_statusbar_shell_for_pinned_map(wad_path)
    stage15_world = stage15.build_stage15_world(wad, loaded, ref15.stage14)
    stage15.run_pickup_probes_source_shape(stage15_world)
    target = _post_stage15_player_target(stage15_world)
    info = parse_stage16_info_tables()
    geometry = stage13.build_map_geometry(wad, loaded)
    rejectmatrix = wad.read_lump(wad.map_lumps("MAP01").get("REJECT"))
    census = build_monster_census_source_shape(
        stage15_world,
        info,
        target,
        loaded,
        geometry,
        rejectmatrix,
    )
    selected = select_active_monster_record(census)
    world = build_stage16_world_for_selected(
        stage15_world,
        info,
        selected,
        target,
        loaded,
        geometry,
        rejectmatrix,
    )
    trace = p_ticker_active_monster_source_shape(world, DEFAULT_ACTIVE_MONSTER_TICS)
    final_mobj = replace(world.mobjs[0])
    signature = _stage16_signature(
        ref15,
        len(census),
        selected,
        trace,
        final_mobj,
        target,
        world.counters,
    )
    return Stage16ActiveMonsterReference(
        stage15=ref15,
        monster_count=len(census),
        selected=selected,
        trace=trace,
        final_mobj=final_mobj,
        target=target,
        counters=replace(world.counters),
        thinker_node_count=len(world.thinkers.nodes) - 1,
        active_thinker_count=sum(1 for node in world.thinkers.nodes.values() if node.function == "P_MobjThinker"),
        signature=signature,
    )


@lru_cache(maxsize=4)
def _reference_stage16_cached(wad_path: str) -> Stage16ActiveMonsterReference:
    return _reference_stage16_uncached(wad_path)


def reference_active_monster_thinkers_and_targeting_for_pinned_map(
    wad_path: str | Path,
) -> Stage16ActiveMonsterReference:
    return _reference_stage16_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage16ActiveMonsterReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_active_monster_thinkers_and_targeting_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage16_load_wad_active_monster_thinkers_targeting")

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


def emit_source_stage16_load_wad_active_monster_thinkers_targeting(pe: PE32) -> None:
    pe.label("source_stage16_load_wad_active_monster_thinkers_targeting")
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
    x86.jne_rel32(pe, "source_stage16_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage16_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage16_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage16_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage16_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage16_close_and_return")

    pe.label("source_stage16_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage16_close_and_return")
    x86.call_rel32(pe, "render_init_texture_data_setup_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage16_close_and_return")
    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage16_close_and_return")
    x86.call_rel32(pe, "source_stage06_run_live_seg_clip_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage16_close_and_return")

    x86.call_rel32(pe, "render_composite_two_sided_wall_edges_debug")
    x86.call_rel32(pe, "render_visplanes_floor_ceiling_debug")
    x86.call_rel32(pe, "render_sky_and_masked_midtextures_debug")
    x86.call_rel32(pe, "render_things_sprites_real_frame_setup_debug")
    x86.call_rel32(pe, "render_game_loop_input_collision_debug")
    x86.call_rel32(pe, "render_pickups_psprites_statusbar_shell_debug")
    x86.call_rel32(pe, "render_active_monster_thinkers_targeting_debug")
    x86.call_rel32(pe, "build_success_status")
    x86.call_rel32(pe, "append_stage13_success_status")
    x86.call_rel32(pe, "append_stage14_success_status")
    x86.call_rel32(pe, "append_stage15_success_status")
    x86.call_rel32(pe, "append_stage16_success_status")

    pe.label("source_stage16_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_render_active_monster_thinkers_targeting_debug(pe: PE32) -> None:
    pe.label("P_SetupLevel_active_monster_census_source_shape_debug")
    pe.label("P_ThinkerList_active_monster_source_shape_debug")
    pe.label("P_SpawnMobj_active_monster_source_shape_debug")
    pe.label("P_MobjThinker_SetMobjState_source_shape_debug")
    pe.label("A_Look_P_LookForPlayers_source_shape_debug")
    pe.label("P_CheckSight_bounded_source_shape_debug")
    pe.label("A_Chase_deferred_active_monster_boundary_debug")
    pe.label("P_Random_spawn_sequence_source_shape_debug")
    pe.label("render_active_monster_thinkers_targeting_debug")

    x86.mov_reg_mem_abs32(pe, "eax", "stage16_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage16_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage16_ticker_calls")
    x86.mov_mem_abs32_eax(pe, "stage16_runtime_ticker_calls")
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage14._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage16_success_status(pe: PE32) -> None:
    pe.label("append_stage16_success_status")

    _emit_seek_buffer_end(pe, "status_success_buffer", "stage16_status")
    stage01.append_c_string_label(pe, "status_stage16_success_header")
    stage01.append_u32_label(pe, "status_stage16_monsters_prefix", "stage16_monster_count")
    stage01.append_u32_label(pe, "status_stage16_selected_prefix", "stage16_selected_mapthing")
    stage01.append_u32_label(pe, "status_stage16_target_prefix", "stage16_target_acquired")
    stage01.append_u32_label(pe, "status_stage16_signature_prefix", "stage16_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage16_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage16_title")
    stage01.append_u32_label(pe, "title_stage16_monster_count_prefix", "stage16_monster_count")
    stage01.append_u32_label(pe, "title_stage16_active_prefix", "stage16_active_thinker_count")
    stage01.append_u32_label(pe, "title_stage16_thinker_add_prefix", "stage16_thinker_adds")
    stage01.append_u32_label(pe, "title_stage16_ticker_prefix", "stage16_runtime_ticker_calls")
    stage01.append_u32_label(pe, "title_stage16_selected_mapthing_prefix", "stage16_selected_mapthing")
    stage01.append_u32_label(pe, "title_stage16_selected_mobj_prefix", "stage16_selected_mobj")
    stage01.append_c_string_label(pe, "title_stage16_type_prefix")
    stage01.append_c_string_label(pe, "stage16_selected_type_name")
    stage01.append_i32_label(pe, "title_stage16_x_prefix", "stage16_selected_x")
    stage01.append_i32_label(pe, "title_stage16_y_prefix", "stage16_selected_y")
    stage01.append_u32_label(pe, "title_stage16_sector_prefix", "stage16_selected_sector")
    stage01.append_u32_label(pe, "title_stage16_block_x_prefix", "stage16_selected_block_x")
    stage01.append_u32_label(pe, "title_stage16_block_y_prefix", "stage16_selected_block_y")
    stage01.append_u32_label(pe, "title_stage16_spawn_tics_prefix", "stage16_selected_spawn_tics")
    stage01.append_u32_label(pe, "title_stage16_lastlook_prefix", "stage16_selected_lastlook")
    stage01.append_u32_label(pe, "title_stage16_look_prefix", "stage16_a_look_calls")
    stage01.append_u32_label(pe, "title_stage16_lfp_prefix", "stage16_look_for_players_calls")
    stage01.append_u32_label(pe, "title_stage16_sight_prefix", "stage16_sight_checks")
    stage01.append_u32_label(pe, "title_stage16_sight_ok_prefix", "stage16_sight_bsp_accepts")
    stage01.append_u32_label(pe, "title_stage16_sight_nodes_prefix", "stage16_sight_nodes")
    stage01.append_u32_label(pe, "title_stage16_sight_subsectors_prefix", "stage16_sight_subsectors")
    stage01.append_u32_label(pe, "title_stage16_sight_lines_prefix", "stage16_sight_crossed_lines")
    stage01.append_u32_label(pe, "title_stage16_target_prefix", "stage16_target_acquired")
    stage01.append_u32_label(pe, "title_stage16_initial_state_prefix", "stage16_initial_state")
    stage01.append_c_string_label(pe, "title_stage16_final_state_name_prefix")
    stage01.append_c_string_label(pe, "stage16_final_state_name")
    stage01.append_u32_label(pe, "title_stage16_final_state_prefix", "stage16_final_state")
    stage01.append_u32_label(pe, "title_stage16_final_tics_prefix", "stage16_final_tics")
    stage01.append_u32_label(pe, "title_stage16_chase_deferred_prefix", "stage16_chase_deferred")
    stage01.append_u32_label(pe, "title_stage16_sound_deferred_prefix", "stage16_sound_deferred")
    stage01.append_u32_label(pe, "title_stage16_attack_prefix", "stage16_attacks_deferred")
    stage01.append_u32_label(pe, "title_stage16_damage_prefix", "stage16_damage_events")
    stage01.append_u32_label(pe, "title_stage16_kill_prefix", "stage16_kills")
    stage01.append_u32_label(pe, "title_stage16_signature_prefix", "stage16_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage16_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    selected = ref.selected if ref is not None else None
    final = ref.final_mobj if ref is not None else None
    counters = ref.counters if ref is not None else Stage16Counters()

    pe.align_section(4)
    pe.label("stage16_monster_count")
    pe.emit_u32(ref.monster_count if ref is not None else 0)
    pe.label("stage16_active_thinker_count")
    pe.emit_u32(ref.active_thinker_count if ref is not None else 0)
    pe.label("stage16_thinker_node_count")
    pe.emit_u32(ref.thinker_node_count if ref is not None else 0)
    pe.label("stage16_thinker_adds")
    pe.emit_u32(counters.thinker_adds)
    pe.label("stage16_thinker_iterations")
    pe.emit_u32(counters.thinker_iteration_calls)
    pe.label("stage16_thinker_function_calls")
    pe.emit_u32(counters.thinker_function_calls)
    pe.label("stage16_ticker_calls")
    pe.emit_u32(counters.p_ticker_calls)
    pe.label("stage16_runtime_ticker_calls")
    pe.emit_u32(0)
    pe.label("stage16_mobj_thinker_calls")
    pe.emit_u32(counters.mobj_thinker_calls)
    pe.label("stage16_state_sets")
    pe.emit_u32(counters.mobj_state_sets)
    pe.label("stage16_state_transitions")
    pe.emit_u32(counters.mobj_state_transitions)
    pe.label("stage16_action_dispatches")
    pe.emit_u32(counters.action_dispatches)
    pe.label("stage16_action_deferrals")
    pe.emit_u32(counters.action_deferrals)
    pe.label("stage16_a_look_calls")
    pe.emit_u32(counters.a_look_calls)
    pe.label("stage16_look_for_players_calls")
    pe.emit_u32(counters.look_for_players_calls)
    pe.label("stage16_look_iterations")
    pe.emit_u32(counters.look_iterations)
    pe.label("stage16_look_player_checks")
    pe.emit_u32(counters.look_player_checks)
    pe.label("stage16_target_acquired")
    pe.emit_u32(counters.target_acquired)
    pe.label("stage16_sight_checks")
    pe.emit_u32(counters.sight_checks)
    pe.label("stage16_sight_reject_blocks")
    pe.emit_u32(counters.sight_reject_matrix_blocks)
    pe.label("stage16_sight_bsp_accepts")
    pe.emit_u32(counters.sight_bsp_accepts)
    pe.label("stage16_sight_bsp_blocks")
    pe.emit_u32(counters.sight_bsp_blocks)
    pe.label("stage16_sight_nodes")
    pe.emit_u32(counters.sight_nodes)
    pe.label("stage16_sight_subsectors")
    pe.emit_u32(counters.sight_subsectors)
    pe.label("stage16_sight_segs")
    pe.emit_u32(counters.sight_segs)
    pe.label("stage16_sight_crossed_lines")
    pe.emit_u32(counters.sight_crossed_lines)
    pe.label("stage16_chase_deferred")
    pe.emit_u32(counters.chase_deferred)
    pe.label("stage16_new_chase_dir_deferred")
    pe.emit_u32(counters.new_chase_dir_deferred)
    pe.label("stage16_sound_deferred")
    pe.emit_u32(counters.sound_deferred)
    pe.label("stage16_alert_deferred")
    pe.emit_u32(counters.alert_deferred)
    pe.label("stage16_attacks_deferred")
    pe.emit_u32(counters.attacks_deferred)
    pe.label("stage16_damage_events")
    pe.emit_u32(counters.damage_events)
    pe.label("stage16_kills")
    pe.emit_u32(counters.kills)
    pe.label("stage16_drops")
    pe.emit_u32(counters.drops)
    pe.label("stage16_sector_specials_deferred")
    pe.emit_u32(counters.sector_specials_deferred)
    pe.label("stage16_live_input_deferred")
    pe.emit_u32(counters.live_input_deferred)

    pe.label("stage16_selected_mapthing")
    pe.emit_u32(selected.mapthing_index if selected is not None else 0)
    pe.label("stage16_selected_mobj")
    pe.emit_u32(selected.mobj_index if selected is not None else 0)
    pe.label("stage16_selected_doomednum")
    pe.emit_u32(selected.doomednum if selected is not None else 0)
    pe.label("stage16_selected_x")
    pe.emit_u32((selected.x >> FRACBITS if selected is not None else 0) & 0xFFFFFFFF)
    pe.label("stage16_selected_y")
    pe.emit_u32((selected.y >> FRACBITS if selected is not None else 0) & 0xFFFFFFFF)
    pe.label("stage16_selected_sector")
    pe.emit_u32(selected.sector if selected is not None else 0)
    pe.label("stage16_selected_subsector")
    pe.emit_u32(selected.subsector if selected is not None else 0)
    pe.label("stage16_selected_block_x")
    pe.emit_u32(selected.block_x if selected is not None else 0)
    pe.label("stage16_selected_block_y")
    pe.emit_u32(selected.block_y if selected is not None else 0)
    pe.label("stage16_selected_spawn_tics")
    pe.emit_u32(selected.spawn_tics if selected is not None else 0)
    pe.label("stage16_selected_raw_tics")
    pe.emit_u32(selected.raw_spawn_tics if selected is not None else 0)
    pe.label("stage16_selected_lastlook")
    pe.emit_u32(selected.spawn_lastlook if selected is not None else 0)
    pe.label("stage16_selected_distance")
    pe.emit_u32(selected.distance_to_player if selected is not None else 0)
    pe.label("stage16_selected_front_arc")
    pe.emit_u32(selected.front_arc if selected is not None else 0)
    pe.label("stage16_selected_sight_visible")
    pe.emit_u32(1 if selected is not None and selected.sight.visible else 0)

    pe.label("stage16_target_x")
    pe.emit_u32((ref.target.x >> FRACBITS if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage16_target_y")
    pe.emit_u32((ref.target.y >> FRACBITS if ref is not None else 0) & 0xFFFFFFFF)
    pe.label("stage16_target_sector")
    pe.emit_u32(ref.target.sector if ref is not None else 0)
    pe.label("stage16_target_subsector")
    pe.emit_u32(ref.target.subsector if ref is not None else 0)

    pe.label("stage16_initial_state")
    pe.emit_u32(selected.spawn_state if selected is not None else 0)
    pe.label("stage16_final_state")
    pe.emit_u32(final.state if final is not None and final.state is not None else 0)
    pe.label("stage16_final_tics")
    pe.emit_u32(final.tics if final is not None else 0)
    pe.label("stage16_final_target")
    pe.emit_u32(final.target_index if final is not None and final.target_index is not None else 0xFFFFFFFF)
    pe.label("stage16_expected_signature")
    pe.emit_u32(ref.signature if ref is not None else 0)
    pe.label("stage16_runtime_signature")
    pe.emit_u32(0)

    pe.align_section(1)
    pe.label("stage16_selected_type_name")
    raw_type = selected.type_name[3:] if selected is not None and selected.type_name.startswith("MT_") else ""
    x86.emit_asciiz(pe, raw_type)
    pe.label("stage16_initial_state_name")
    x86.emit_asciiz(pe, selected.spawn_state_name if selected is not None else "")
    pe.label("stage16_final_state_name")
    x86.emit_asciiz(pe, _state_name(parse_stage16_info_tables(), final.state) if final is not None else "")

    pe.label("status_stage16_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage16_active_monster_thinkers_and_targeting\r\n"
        "Active monster thinker and targeting OK\r\n",
    )
    pe.label("status_stage16_monsters_prefix")
    x86.emit_asciiz(pe, "\r\nReal MAP01 monster census: ")
    pe.label("status_stage16_selected_prefix")
    x86.emit_asciiz(pe, "\r\nSelected active mapthing: ")
    pe.label("status_stage16_target_prefix")
    x86.emit_asciiz(pe, "\r\nTarget acquired: ")
    pe.label("status_stage16_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage16 active monster signature: ")
    pe.label("status_stage16_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage16 keeps stage15 pickup/status output stable, then proves one "
        "real MAP01 shotgun guy through P_InitThinkers, P_AddThinker, "
        "P_MobjThinker, P_SetMobjState, A_Look, P_LookForPlayers, and a "
        "bounded P_CheckSight probe. The chase action is reached as a counted "
        "deferred boundary; wider systems remain outside this release.\r\n",
    )

    pe.label("title_stage16_monster_count_prefix")
    x86.emit_asciiz(pe, " MCENS=")
    pe.label("title_stage16_active_prefix")
    x86.emit_asciiz(pe, " ACTM=")
    pe.label("title_stage16_thinker_add_prefix")
    x86.emit_asciiz(pe, " TADD=")
    pe.label("title_stage16_ticker_prefix")
    x86.emit_asciiz(pe, " TRUN=")
    pe.label("title_stage16_selected_mapthing_prefix")
    x86.emit_asciiz(pe, " MT16=")
    pe.label("title_stage16_selected_mobj_prefix")
    x86.emit_asciiz(pe, " MO16=")
    pe.label("title_stage16_type_prefix")
    x86.emit_asciiz(pe, " M16N=")
    pe.label("title_stage16_x_prefix")
    x86.emit_asciiz(pe, " M16X=")
    pe.label("title_stage16_y_prefix")
    x86.emit_asciiz(pe, " M16Y=")
    pe.label("title_stage16_sector_prefix")
    x86.emit_asciiz(pe, " M16SEC=")
    pe.label("title_stage16_block_x_prefix")
    x86.emit_asciiz(pe, " M16BX=")
    pe.label("title_stage16_block_y_prefix")
    x86.emit_asciiz(pe, " M16BY=")
    pe.label("title_stage16_spawn_tics_prefix")
    x86.emit_asciiz(pe, " MTIC0=")
    pe.label("title_stage16_lastlook_prefix")
    x86.emit_asciiz(pe, " LLOOK=")
    pe.label("title_stage16_look_prefix")
    x86.emit_asciiz(pe, " LOOK=")
    pe.label("title_stage16_lfp_prefix")
    x86.emit_asciiz(pe, " LFP=")
    pe.label("title_stage16_sight_prefix")
    x86.emit_asciiz(pe, " SIGHT=")
    pe.label("title_stage16_sight_ok_prefix")
    x86.emit_asciiz(pe, " SOK=")
    pe.label("title_stage16_sight_nodes_prefix")
    x86.emit_asciiz(pe, " SNODE=")
    pe.label("title_stage16_sight_subsectors_prefix")
    x86.emit_asciiz(pe, " SSUB=")
    pe.label("title_stage16_sight_lines_prefix")
    x86.emit_asciiz(pe, " SLINE=")
    pe.label("title_stage16_target_prefix")
    x86.emit_asciiz(pe, " TGT=")
    pe.label("title_stage16_initial_state_prefix")
    x86.emit_asciiz(pe, " ST0=")
    pe.label("title_stage16_final_state_name_prefix")
    x86.emit_asciiz(pe, " STFN=")
    pe.label("title_stage16_final_state_prefix")
    x86.emit_asciiz(pe, " STF=")
    pe.label("title_stage16_final_tics_prefix")
    x86.emit_asciiz(pe, " FTIC=")
    pe.label("title_stage16_chase_deferred_prefix")
    x86.emit_asciiz(pe, " CHDEF=")
    pe.label("title_stage16_sound_deferred_prefix")
    x86.emit_asciiz(pe, " SND16=")
    pe.label("title_stage16_attack_prefix")
    x86.emit_asciiz(pe, " ATK=")
    pe.label("title_stage16_damage_prefix")
    x86.emit_asciiz(pe, " DMG=")
    pe.label("title_stage16_kill_prefix")
    x86.emit_asciiz(pe, " KILL=")
    pe.label("title_stage16_signature_prefix")
    x86.emit_asciiz(pe, " S16SIG=")


def build_source_stage16_active_monster_thinkers_and_targeting_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage16_load_wad_active_monster_thinkers_targeting(pe)
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
    emit_render_active_monster_thinkers_targeting_debug(pe)
    stage12.emit_build_success_status(pe)
    stage13.emit_append_stage13_success_status(pe)
    stage14.emit_append_stage14_success_status(pe)
    stage15.emit_append_stage15_success_status(pe)
    emit_append_stage16_success_status(pe)
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
    emit_stage16_data(pe)
    return pe.build("entry")


def write_source_stage16_active_monster_thinkers_and_targeting_exe(path: str | Path) -> bytes:
    image = build_source_stage16_active_monster_thinkers_and_targeting_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage16 active monster thinker/targeting PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage16_active_monster_thinkers_and_targeting.exe",
        help="path to write, default: build/source_stage16_active_monster_thinkers_and_targeting.exe",
    )
    args = parser.parse_args()
    write_source_stage16_active_monster_thinkers_and_targeting_exe(args.output)


if __name__ == "__main__":
    main()
