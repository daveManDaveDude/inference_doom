import argparse
import re
import struct
import sys
from contextlib import contextmanager
from dataclasses import dataclass
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
from tools import emit_source_stage09_direct_wall_column_pixels_debug as stage09
from tools import emit_source_stage10_composite_two_sided_wall_edges_debug as stage10
from tools import emit_source_stage11_visplanes_floor_ceiling_debug as stage11
from tools import emit_source_stage12_sky_and_masked_midtextures_debug as stage12
from tools import x86
from tools.map_loader import THING_RECORD_SIZE, LoadedMap, Thing, parse_things, load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


FRAMEBUFFER_WIDTH = stage12.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage12.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage12.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage12.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage12.WINDOW_WIDTH
WINDOW_HEIGHT = stage12.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage13ThingsSpritesRealFrameSetup"
WINDOW_TITLE = "Inference Doom S13 Things Sprites"
WAD_PATH = stage12.WAD_PATH

FRACBITS = stage12.FRACBITS
FRACUNIT = stage12.FRACUNIT
VIEWHEIGHT = stage12.VIEWHEIGHT
ANG90 = stage12.ANG90
ANG45 = ANG90 // 2
ANGLETOFINESHIFT = stage12.ANGLETOFINESHIFT
FINEMASK = stage12.FINEMASK
FINECOSINE = stage12.FINECOSINE
FINESINE = stage12.FINESINE
CENTER_Y = stage12.CENTER_Y
CENTERYFRAC = stage12.CENTERYFRAC
CENTERXFRAC = (FRAMEBUFFER_WIDTH // 2) << FRACBITS
PROJECTION = CENTERXFRAC
MINZ = 4 * FRACUNIT
WALL_COLUMN_SOURCE_HEIGHT = stage12.WALL_COLUMN_SOURCE_HEIGHT
FNV_PRIME = stage12.FNV_PRIME

MAXVISSPRITES = 128
MAX_SPRITE_FRAMES = 29
DEFAULT_MAX_MAPTHINGS = 512
DEFAULT_MAX_RENDER_MOBJS = 512
DEFAULT_MAX_SPRITE_DRAW_COLUMNS = 256
FF_FRAMEMASK = 0x7FFF
FF_FULLBRIGHT = 0x8000
ONFLOORZ = -0x80000000
ONCEILINGZ = 0x7FFFFFFF

REPO_ROOT = Path(__file__).resolve().parents[1]
INFO_C = REPO_ROOT / "reference" / "chocolate-doom" / "src" / "doom" / "info.c"
P_MOBJ_H = REPO_ROOT / "reference" / "chocolate-doom" / "src" / "doom" / "p_mobj.h"

MF_SPECIAL = 1
MF_SOLID = 2
MF_SHOOTABLE = 4
MF_NOSECTOR = 8
MF_NOBLOCKMAP = 16
MF_AMBUSH = 32
MF_JUSTHIT = 64
MF_JUSTATTACKED = 128
MF_SPAWNCEILING = 256
MF_NOGRAVITY = 512
MF_DROPOFF = 0x400
MF_PICKUP = 0x800
MF_NOCLIP = 0x1000
MF_SLIDE = 0x2000
MF_FLOAT = 0x4000
MF_TELEPORT = 0x8000
MF_MISSILE = 0x10000
MF_DROPPED = 0x20000
MF_SHADOW = 0x40000
MF_NOBLOOD = 0x80000
MF_CORPSE = 0x100000
MF_INFLOAT = 0x200000
MF_COUNTKILL = 0x400000
MF_COUNTITEM = 0x800000
MF_SKULLFLY = 0x1000000
MF_NOTDMATCH = 0x2000000
MF_TRANSLATION = 0xC000000
MF_TRANSSHIFT = 26

SOURCE_TRACE = stage12.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_setup.c",
        "P_LoadThings",
        "P_LoadThings_decode_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_SpawnMapThing player start and inert render mobj subset",
        "P_SpawnMapThing_render_subset_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.h",
        "mobj_t render-facing fields",
        "mobj_t_render_record_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/d_player.h",
        "player_t mo/view fields",
        "player_t_minimal_view_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/info.c",
        "sprnames, states, mobjinfo",
        "info_tables_sprite_state_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_data.c",
        "R_InitSpriteLumps",
        "R_InitSpriteLumps_metadata_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_things.c",
        "R_InitSprites/R_ClearSprites/R_NewVisSprite",
        "R_InitSprites_vissprite_pool_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_things.c",
        "R_AddSprites/R_ProjectSprite/R_SortVisSprites",
        "R_ProjectSprite_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_things.c",
        "R_DrawSprite/R_DrawSpriteRange/R_DrawMaskedColumn",
        "R_DrawSpriteRange_columns_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_SetupFrame",
        "R_SetupFrame_real_player_start_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_bsp.c",
        "R_Subsector calls R_AddSprites(frontsector)",
        "R_Subsector_AddSprites_sector_gather_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_segs.c",
        "drawseg sprite clipping fields",
        "R_DrawSprite_drawseg_clip_debug",
    ),
)


@dataclass(frozen=True)
class StateInfo:
    name: str
    sprite: int
    frame: int
    nextstate: str


@dataclass(frozen=True)
class DoomMobjInfo:
    name: str
    doomednum: int
    spawnstate: int
    radius: int
    height: int
    flags: int


@dataclass(frozen=True)
class DoomInfoTables:
    sprnames: tuple[str, ...]
    state_names: tuple[str, ...]
    states: tuple[StateInfo, ...]
    mobjinfo: tuple[DoomMobjInfo, ...]
    by_doomednum: dict[int, DoomMobjInfo]


@dataclass(frozen=True)
class ThingLoadResult:
    things: tuple[Thing, ...]
    loaded_count: int
    player_start_count: int
    overflow_count: int
    nonpositive_skip_count: int
    commercial_filter_skip_count: int


@dataclass(frozen=True)
class SpawnOptions:
    gameskill: int = 2
    commercial: bool = True
    deathmatch: bool = False
    netgame: bool = False
    nomonsters: bool = False
    playeringame: tuple[bool, bool, bool, bool] = (True, False, False, False)


@dataclass(frozen=True)
class MapGeometry:
    subsectors: tuple[tuple[int, int], ...]
    segs: tuple[tuple[int, int, int, int, int, int], ...]
    nodes: tuple[tuple[int, ...], ...]
    subsector_sectors: tuple[int, ...]


@dataclass(frozen=True)
class RenderMobj:
    index: int
    mapthing_index: int
    type_name: str
    doomednum: int
    x: int
    y: int
    z: int
    angle: int
    sprite: int
    frame: int
    flags: int
    radius: int
    height: int
    floorz: int
    ceilingz: int
    sector: int
    subsector: int
    player_index: int = -1


@dataclass(frozen=True)
class MinimalPlayer:
    player_index: int
    mapthing_index: int
    mobj_index: int
    x: int
    y: int
    z: int
    angle: int
    viewz: int
    sector: int
    subsector: int


@dataclass(frozen=True)
class ThingSpawnResult:
    players: tuple[MinimalPlayer, ...]
    mobjs: tuple[RenderMobj, ...]
    player_start_count: int
    player_mobj_count: int
    inert_mobj_count: int
    unsupported_type_count: int
    option_skip_count: int
    skill_skip_count: int
    nomonster_skip_count: int
    deathmatch_skip_count: int
    overflow_count: int


@dataclass(frozen=True)
class SpriteLumpMetadata:
    index: int
    name: str
    width: int
    offset: int
    topoffset: int
    patch_width: int
    patch_height: int


@dataclass(frozen=True)
class SpriteFrameMetadata:
    rotate: int
    lump: tuple[int, int, int, int, int, int, int, int]
    flip: tuple[bool, bool, bool, bool, bool, bool, bool, bool]


@dataclass(frozen=True)
class SpriteDefMetadata:
    name: str
    frames: tuple[SpriteFrameMetadata, ...]


@dataclass(frozen=True)
class SpriteMetadata:
    sprnames: tuple[str, ...]
    firstspritelump: int
    lastspritelump: int
    lumps: tuple[SpriteLumpMetadata, ...]
    defs: tuple[SpriteDefMetadata, ...]
    sprite_defs_present: int
    frames_present: int
    missing_frames: int


@dataclass(frozen=True)
class VisSprite:
    thing_index: int
    mapthing_index: int
    type_name: str
    sprite_name: str
    sprite: int
    frame: int
    patch: int
    patch_name: str
    x1: int
    x2: int
    raw_x1: int
    raw_x2: int
    scale: int
    xiscale: int
    startfrac: int
    texturemid: int
    flip: bool
    tz: int


@dataclass
class VisSpriteState:
    max_vissprites: int = MAXVISSPRITES
    vissprites: list[VisSprite] | None = None
    overflow_count: int = 0

    def __post_init__(self) -> None:
        if self.vissprites is None:
            self.vissprites = []


@dataclass(frozen=True)
class DrawSegClip:
    x1: int
    x2: int
    sprtopclip: tuple[int, ...] | None = None
    sprbottomclip: tuple[int, ...] | None = None


@dataclass(frozen=True)
class SpriteDrawResult:
    commands: tuple[stage12.Stage12ColumnCommand, ...]
    column_sources: tuple[bytes, ...]
    columns_drawn: int
    post_commands_drawn: int
    pixels_drawn: int
    source_skip_count: int
    drawseg_clip_columns: int
    framebuffer_signature: int
    first_drawn: VisSprite | None
    first_drawn_patch_column: int


@dataclass(frozen=True)
class Stage13ThingsSpritesReference:
    stage12: stage12.Stage12SkyMaskedReference
    thing_load: ThingLoadResult
    spawn: ThingSpawnResult
    sprite_metadata: SpriteMetadata
    player: MinimalPlayer
    primary_sector_count: int
    vissprites: tuple[VisSprite, ...]
    projection_rejects: dict[str, int]
    draw: SpriteDrawResult
    probe_active: int


def _u32(value: int) -> int:
    return value & 0xFFFFFFFF


def _i32(value: int) -> int:
    return stage04._int32(value)


def _fine_index(angle: int) -> int:
    return (_u32(angle) >> ANGLETOFINESHIFT) & FINEMASK


def angle_to_degrees(angle: int) -> int:
    return (_u32(angle) * 360) // 0x100000000


def parse_mobj_flag_values(path: str | Path = P_MOBJ_H) -> dict[str, int]:
    text = Path(path).read_text(encoding="utf-8")
    block = re.search(r"typedef\s+enum\s*\{(.*?)\}\s*mobjflag_t;", text, re.DOTALL)
    if block is None:
        return {
            name: value
            for name, value in globals().items()
            if name.startswith("MF_") and isinstance(value, int)
        }

    values: dict[str, int] = {}
    next_value = 0
    for line in block.group(1).splitlines():
        line = line.split("//", 1)[0].strip().rstrip(",")
        if not line or not line.startswith("MF_"):
            continue
        if "=" in line:
            name, expr = (part.strip() for part in line.split("=", 1))
            next_value = int(eval(expr, {"__builtins__": {}}, values))
        else:
            name = line
        values[name] = next_value
        next_value += 1
    return values


def parse_source_info_tables(
    info_path: str | Path = INFO_C,
    p_mobj_path: str | Path = P_MOBJ_H,
) -> DoomInfoTables:
    text = Path(info_path).read_text(encoding="utf-8")
    spr_match = re.search(r"const char \*sprnames\[\] = \{(.*?)NULL\s*\n\};", text, re.DOTALL)
    if spr_match is None:
        raise ValueError("could not find sprnames in info.c")
    sprnames = tuple(re.findall(r'"([A-Z0-9]{4})"', spr_match.group(1)))
    sprite_index = {f"SPR_{name}": index for index, name in enumerate(sprnames)}

    state_rows: list[tuple[str, str, str, str]] = []
    for match in re.finditer(
        r"\{\s*(SPR_[A-Z0-9]+)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*\{[^}]*\}\s*,"
        r"\s*(S_[A-Z0-9_]+)\s*,\s*[^,]+\s*,\s*[^}]+\}\s*,?\s*//\s*(S_[A-Z0-9_]+)",
        text,
    ):
        sprite_name, frame_expr, _tics_expr, nextstate, state_name = match.groups()
        state_rows.append((state_name, sprite_name, frame_expr, nextstate))

    state_names = tuple(row[0] for row in state_rows)
    state_index = {name: index for index, name in enumerate(state_names)}
    states = tuple(
        StateInfo(
            name=state_name,
            sprite=sprite_index[sprite_name],
            frame=int(frame_expr, 0),
            nextstate=nextstate,
        )
        for state_name, sprite_name, frame_expr, nextstate in state_rows
    )

    flag_values = parse_mobj_flag_values(p_mobj_path)

    def eval_info_expr(expr: str) -> int:
        namespace: dict[str, int] = {"FRACUNIT": FRACUNIT, **state_index, **flag_values}
        namespace.update({name: 0 for name in re.findall(r"sfx_[A-Za-z0-9_]+", expr)})
        return int(eval(expr.strip(), {"__builtins__": {}}, namespace))

    table_match = re.search(r"mobjinfo_t\s+mobjinfo\[NUMMOBJTYPES\]\s*=\s*\{", text)
    if table_match is None:
        raise ValueError("could not find mobjinfo in info.c")
    block = text[table_match.end() :]
    mobjinfo: list[DoomMobjInfo] = []
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
        if len(fields) >= 22:
            mobjinfo.append(
                DoomMobjInfo(
                    name=name,
                    doomednum=eval_info_expr(fields[0]),
                    spawnstate=eval_info_expr(fields[1]),
                    radius=eval_info_expr(fields[16]),
                    height=eval_info_expr(fields[17]),
                    flags=eval_info_expr(fields[21]),
                )
            )
        position = entry_start + end_match.end()

    by_doomednum = {info.doomednum: info for info in mobjinfo if info.doomednum >= 0}
    return DoomInfoTables(
        sprnames=sprnames,
        state_names=state_names,
        states=states,
        mobjinfo=tuple(mobjinfo),
        by_doomednum=by_doomednum,
    )


def p_loadthings_source_shape(
    data: bytes,
    *,
    max_things: int = DEFAULT_MAX_MAPTHINGS,
    commercial: bool = True,
) -> ThingLoadResult:
    raw_things = parse_things(data)
    things: list[Thing] = []
    overflow_count = 0
    nonpositive_skip_count = 0
    commercial_filter_skip_count = 0
    doom2_only = {68, 64, 88, 89, 69, 67, 71, 65, 66, 84}

    for thing in raw_things:
        if thing.type <= 0:
            nonpositive_skip_count += 1
            continue
        if not commercial and thing.type in doom2_only:
            commercial_filter_skip_count += 1
            continue
        if len(things) >= max_things:
            overflow_count += 1
            continue
        things.append(thing)

    return ThingLoadResult(
        things=tuple(things),
        loaded_count=len(things),
        player_start_count=sum(1 for thing in things if thing.is_player_start),
        overflow_count=overflow_count,
        nonpositive_skip_count=nonpositive_skip_count,
        commercial_filter_skip_count=commercial_filter_skip_count,
    )


def build_map_geometry(wad: WadFile, loaded: LoadedMap, map_name: str = "MAP01") -> MapGeometry:
    map_lumps = wad.map_lumps(map_name)
    subsectors = stage02.parse_mapsubsectors(wad.read_lump(map_lumps.get("SSECTORS")))
    segs = stage02.parse_mapsegs(wad.read_lump(map_lumps.get("SEGS")))
    nodes = tuple(
        stage03.runtime_node_from_mapnode(node)
        for node in stage02.parse_mapnodes(wad.read_lump(map_lumps.get("NODES")))
    )

    subsector_sectors: list[int] = []
    for numlines, firstline in subsectors:
        sector_index = 0
        if numlines:
            seg = segs[firstline]
            linedef = loaded.linedefs[seg[3]]
            sidenum = linedef.right_sidedef if seg[4] == 0 else linedef.left_sidedef
            if sidenum == 0xFFFF or sidenum >= len(loaded.sidedefs):
                sidenum = linedef.left_sidedef if seg[4] == 0 else linedef.right_sidedef
            if sidenum != 0xFFFF and sidenum < len(loaded.sidedefs):
                sector_index = loaded.sidedefs[sidenum].sector
        subsector_sectors.append(sector_index)

    return MapGeometry(
        subsectors=subsectors,
        segs=segs,
        nodes=nodes,
        subsector_sectors=tuple(subsector_sectors),
    )


def point_in_subsector_source_shape(x: int, y: int, geometry: MapGeometry | None) -> int:
    if geometry is None or not geometry.nodes:
        return 0
    nodenum = len(geometry.nodes) - 1
    while not (nodenum & stage03.NF_SUBSECTOR):
        side = stage03.point_on_side_fixed(x, y, geometry.nodes[nodenum])
        nodenum = geometry.nodes[nodenum][12 + side]
    return nodenum & ~stage03.NF_SUBSECTOR


def sector_for_point_source_shape(
    x: int,
    y: int,
    loaded: LoadedMap | None,
    geometry: MapGeometry | None,
) -> tuple[int, int]:
    subsector = point_in_subsector_source_shape(x, y, geometry)
    if loaded is None or geometry is None:
        return subsector, 0
    if 0 <= subsector < len(geometry.subsector_sectors):
        return subsector, geometry.subsector_sectors[subsector]
    return subsector, 0


def _skill_bit(options: SpawnOptions) -> int:
    if options.gameskill <= 0:
        return 1
    if options.gameskill >= 4:
        return 4
    return 1 << ((options.gameskill - 1) & 0x1F)


def p_spawn_mapthings_source_shape(
    things: Sequence[Thing],
    doom: DoomInfoTables,
    *,
    loaded: LoadedMap | None = None,
    geometry: MapGeometry | None = None,
    options: SpawnOptions = SpawnOptions(),
    max_render_mobjs: int = DEFAULT_MAX_RENDER_MOBJS,
) -> ThingSpawnResult:
    players: list[MinimalPlayer] = []
    mobjs: list[RenderMobj] = []
    player_start_count = 0
    unsupported_type_count = 0
    option_skip_count = 0
    skill_skip_count = 0
    nomonster_skip_count = 0
    deathmatch_skip_count = 0
    overflow_count = 0
    player_start_records: dict[int, tuple[int, Thing]] = {}

    def append_mobj(mobj: RenderMobj) -> bool:
        nonlocal overflow_count
        if len(mobjs) >= max_render_mobjs:
            overflow_count += 1
            return False
        mobjs.append(mobj)
        return True

    for mapthing_index, thing in enumerate(things):
        if thing.type == 11:
            continue
        if thing.type <= 0:
            continue
        if thing.type <= 4:
            player_index = thing.type - 1
            player_start_count += 1
            player_start_records[player_index] = (mapthing_index, thing)
            if options.deathmatch or not options.playeringame[player_index]:
                continue
            x = thing.x << FRACBITS
            y = thing.y << FRACBITS
            subsector, sector = sector_for_point_source_shape(x, y, loaded, geometry)
            floorz = (loaded.sectors[sector].floor_height << FRACBITS) if loaded is not None else 0
            ceilingz = (
                loaded.sectors[sector].ceiling_height << FRACBITS
                if loaded is not None
                else 128 * FRACUNIT
            )
            sprite = doom.sprnames.index("PLAY") if "PLAY" in doom.sprnames else 0
            mobj = RenderMobj(
                index=len(mobjs),
                mapthing_index=mapthing_index,
                type_name="MT_PLAYER",
                doomednum=thing.type,
                x=x,
                y=y,
                z=floorz,
                angle=ANG45 * (thing.angle // 45),
                sprite=sprite,
                frame=0,
                flags=MF_SOLID | MF_SHOOTABLE | MF_DROPOFF | MF_PICKUP | MF_NOTDMATCH,
                radius=16 * FRACUNIT,
                height=56 * FRACUNIT,
                floorz=floorz,
                ceilingz=ceilingz,
                sector=sector,
                subsector=subsector,
                player_index=player_index,
            )
            if append_mobj(mobj):
                players.append(
                    MinimalPlayer(
                        player_index=player_index,
                        mapthing_index=mapthing_index,
                        mobj_index=mobj.index,
                        x=x,
                        y=y,
                        z=floorz,
                        angle=mobj.angle,
                        viewz=floorz + VIEWHEIGHT * FRACUNIT,
                        sector=sector,
                        subsector=subsector,
                    )
                )
            continue

        if not options.netgame and thing.flags & 16:
            option_skip_count += 1
            continue

        if not (thing.flags & _skill_bit(options)):
            skill_skip_count += 1
            continue

        info = doom.by_doomednum.get(thing.type)
        if info is None:
            unsupported_type_count += 1
            continue
        if options.deathmatch and info.flags & MF_NOTDMATCH:
            deathmatch_skip_count += 1
            continue
        if options.nomonsters and (info.flags & MF_COUNTKILL or info.name == "MT_SKULL"):
            nomonster_skip_count += 1
            continue
        if info.spawnstate < 0 or info.spawnstate >= len(doom.states):
            unsupported_type_count += 1
            continue
        state = doom.states[info.spawnstate]
        if state.name == "S_NULL":
            unsupported_type_count += 1
            continue

        x = thing.x << FRACBITS
        y = thing.y << FRACBITS
        subsector, sector = sector_for_point_source_shape(x, y, loaded, geometry)
        floorz = (loaded.sectors[sector].floor_height << FRACBITS) if loaded is not None else 0
        ceilingz = (
            loaded.sectors[sector].ceiling_height << FRACBITS
            if loaded is not None
            else 128 * FRACUNIT
        )
        z = ceilingz - info.height if info.flags & MF_SPAWNCEILING else floorz
        append_mobj(
            RenderMobj(
                index=len(mobjs),
                mapthing_index=mapthing_index,
                type_name=info.name,
                doomednum=thing.type,
                x=x,
                y=y,
                z=z,
                angle=ANG45 * (thing.angle // 45),
                sprite=state.sprite,
                frame=state.frame,
                flags=info.flags,
                radius=info.radius,
                height=info.height,
                floorz=floorz,
                ceilingz=ceilingz,
                sector=sector,
                subsector=subsector,
            )
        )

    return ThingSpawnResult(
        players=tuple(players),
        mobjs=tuple(mobjs),
        player_start_count=player_start_count,
        player_mobj_count=sum(1 for mobj in mobjs if mobj.player_index >= 0),
        inert_mobj_count=sum(1 for mobj in mobjs if mobj.player_index < 0),
        unsupported_type_count=unsupported_type_count,
        option_skip_count=option_skip_count,
        skill_skip_count=skill_skip_count,
        nomonster_skip_count=nomonster_skip_count,
        deathmatch_skip_count=deathmatch_skip_count,
        overflow_count=overflow_count,
    )


def _patch_header_origin(data: bytes, lump_name: str) -> tuple[int, int, int, int]:
    if len(data) < 8:
        raise stage08.TextureFormatError(f"patch lump {lump_name} header is truncated")
    return struct.unpack_from("<hhhh", data, 0)


def install_sprite_lump_source_shape(
    frames: list[list[SpriteFrameMetadata | None]],
    maxframe: list[int],
    sprite_index: int,
    lump: int,
    frame: int,
    rotation: int,
    flipped: bool,
) -> None:
    if frame < 0 or frame >= MAX_SPRITE_FRAMES:
        return
    current = frames[sprite_index][frame]
    if current is None:
        current = SpriteFrameMetadata(
            rotate=-1,
            lump=(-1, -1, -1, -1, -1, -1, -1, -1),
            flip=(False, False, False, False, False, False, False, False),
        )
    lumps = list(current.lump)
    flips = list(current.flip)
    rotate = current.rotate
    if rotation == 0:
        rotate = 0
        for rot in range(8):
            lumps[rot] = lump
            flips[rot] = flipped
    elif 1 <= rotation <= 8:
        rotate = 1
        lumps[rotation - 1] = lump
        flips[rotation - 1] = flipped
    else:
        return
    frames[sprite_index][frame] = SpriteFrameMetadata(
        rotate=rotate,
        lump=tuple(lumps),  # type: ignore[arg-type]
        flip=tuple(flips),  # type: ignore[arg-type]
    )
    maxframe[sprite_index] = max(maxframe[sprite_index], frame)


def build_sprite_defs_from_lump_names(
    sprnames: Sequence[str],
    lump_names: Sequence[str],
) -> tuple[tuple[SpriteDefMetadata, ...], int, int, int]:
    sprite_number = {name: index for index, name in enumerate(sprnames)}
    frames: list[list[SpriteFrameMetadata | None]] = [
        [None for _ in range(MAX_SPRITE_FRAMES)] for _ in sprnames
    ]
    maxframe = [-1 for _ in sprnames]

    for lump_index, raw_name in enumerate(lump_names):
        name = raw_name.upper()
        base = name[:4]
        if base not in sprite_number or len(name) < 6:
            continue
        if not ("A" <= name[4] <= "Z" and "0" <= name[5] <= "9"):
            continue
        sprite_index = sprite_number[base]
        install_sprite_lump_source_shape(
            frames,
            maxframe,
            sprite_index,
            lump_index,
            ord(name[4]) - ord("A"),
            ord(name[5]) - ord("0"),
            False,
        )
        if len(name) >= 8 and "A" <= name[6] <= "Z" and "0" <= name[7] <= "9":
            install_sprite_lump_source_shape(
                frames,
                maxframe,
                sprite_index,
                lump_index,
                ord(name[6]) - ord("A"),
                ord(name[7]) - ord("0"),
                True,
            )

    sprite_defs: list[SpriteDefMetadata] = []
    sprite_defs_present = 0
    frames_present = 0
    missing_frames = 0
    empty = SpriteFrameMetadata(
        rotate=-1,
        lump=(-1, -1, -1, -1, -1, -1, -1, -1),
        flip=(False, False, False, False, False, False, False, False),
    )
    for sprite_index, sprite_name in enumerate(sprnames):
        max_frame = maxframe[sprite_index]
        if max_frame >= 0:
            sprite_defs_present += 1
        def_frames: list[SpriteFrameMetadata] = []
        for frame_index in range(max_frame + 1):
            frames_present += 1
            frame = frames[sprite_index][frame_index] or empty
            if frame.rotate == -1 or (frame.rotate == 1 and any(lump < 0 for lump in frame.lump)):
                missing_frames += 1
            def_frames.append(frame)
        sprite_defs.append(SpriteDefMetadata(name=sprite_name, frames=tuple(def_frames)))

    return tuple(sprite_defs), sprite_defs_present, frames_present, missing_frames


def init_sprite_metadata_source_shape(wad: WadFile, doom: DoomInfoTables) -> SpriteMetadata:
    firstspritelump = stage08.wad_get_num_for_name(wad, "S_START") + 1
    lastspritelump = stage08.wad_get_num_for_name(wad, "S_END") - 1
    lump_names = tuple(wad.lumps[index].name for index in range(firstspritelump, lastspritelump + 1))
    defs, sprite_defs_present, frames_present, missing_frames = build_sprite_defs_from_lump_names(
        doom.sprnames,
        lump_names,
    )

    lumps: list[SpriteLumpMetadata] = []
    for index, lump_index in enumerate(range(firstspritelump, lastspritelump + 1)):
        lump = wad.lumps[lump_index]
        data = wad.read_lump(lump)
        patch_width, patch_height, leftoffset, topoffset = _patch_header_origin(data, lump.name)
        lumps.append(
            SpriteLumpMetadata(
                index=index,
                name=lump.name,
                width=patch_width << FRACBITS,
                offset=leftoffset << FRACBITS,
                topoffset=topoffset << FRACBITS,
                patch_width=patch_width,
                patch_height=patch_height,
            )
        )

    return SpriteMetadata(
        sprnames=doom.sprnames,
        firstspritelump=firstspritelump,
        lastspritelump=lastspritelump,
        lumps=tuple(lumps),
        defs=defs,
        sprite_defs_present=sprite_defs_present,
        frames_present=frames_present,
        missing_frames=missing_frames,
    )


def r_clear_sprites_source_shape(state: VisSpriteState) -> None:
    if state.vissprites is None:
        state.vissprites = []
    state.vissprites.clear()
    state.overflow_count = 0


def r_new_vissprite_source_shape(state: VisSpriteState, vissprite: VisSprite) -> VisSprite | None:
    if state.vissprites is None:
        state.vissprites = []
    if len(state.vissprites) >= state.max_vissprites:
        state.overflow_count += 1
        return None
    state.vissprites.append(vissprite)
    return vissprite


def r_project_sprite_source_shape(
    thing: RenderMobj,
    player: MinimalPlayer,
    sprite_metadata: SpriteMetadata,
) -> tuple[VisSprite | None, str | None]:
    tr_x = _i32(thing.x - player.x)
    tr_y = _i32(thing.y - player.y)
    view_index = _fine_index(player.angle)
    viewcos = FINECOSINE[view_index]
    viewsin = FINESINE[view_index]

    gxt = stage04.fixed_mul(tr_x, viewcos)
    gyt = -stage04.fixed_mul(tr_y, viewsin)
    tz = _i32(gxt - gyt)
    if tz < MINZ:
        return None, "minz"

    xscale = stage04.fixed_div(PROJECTION, tz)
    gxt = -stage04.fixed_mul(tr_x, viewsin)
    gyt = stage04.fixed_mul(tr_y, viewcos)
    tx = _i32(-(gyt + gxt))
    if abs(tx) > (tz << 2):
        return None, "side"

    if thing.sprite < 0 or thing.sprite >= len(sprite_metadata.defs):
        return None, "sprite"
    sprite_def = sprite_metadata.defs[thing.sprite]
    frame_index = thing.frame & FF_FRAMEMASK
    if frame_index < 0 or frame_index >= len(sprite_def.frames):
        return None, "frame"
    sprite_frame = sprite_def.frames[frame_index]
    if sprite_frame.rotate:
        angle = stage04.point_to_angle(thing.x, thing.y, player.x, player.y)
        rotation = (_u32(angle - thing.angle + (ANG45 // 2) * 9) >> 29) & 7
        lump_index = sprite_frame.lump[rotation]
        flip = sprite_frame.flip[rotation]
    else:
        lump_index = sprite_frame.lump[0]
        flip = sprite_frame.flip[0]
    if lump_index < 0 or lump_index >= len(sprite_metadata.lumps):
        return None, "lump"
    lump = sprite_metadata.lumps[lump_index]

    tx_left = _i32(tx - lump.offset)
    raw_x1 = (CENTERXFRAC + stage04.fixed_mul(tx_left, xscale)) >> FRACBITS
    tx_right = _i32(tx_left + lump.width)
    raw_x2 = ((CENTERXFRAC + stage04.fixed_mul(tx_right, xscale)) >> FRACBITS) - 1
    if raw_x1 >= FRAMEBUFFER_WIDTH:
        return None, "right"
    if raw_x2 < 0:
        return None, "left"

    x1 = max(0, raw_x1)
    x2 = min(FRAMEBUFFER_WIDTH - 1, raw_x2)
    iscale = stage04.fixed_div(FRACUNIT, xscale)
    if flip:
        startfrac = lump.width - 1
        xiscale = -iscale
    else:
        startfrac = 0
        xiscale = iscale
    if x1 > raw_x1:
        startfrac = _i32(startfrac + xiscale * (x1 - raw_x1))

    return (
        VisSprite(
            thing_index=thing.index,
            mapthing_index=thing.mapthing_index,
            type_name=thing.type_name,
            sprite_name=sprite_metadata.sprnames[thing.sprite],
            sprite=thing.sprite,
            frame=thing.frame,
            patch=lump_index,
            patch_name=lump.name,
            x1=x1,
            x2=x2,
            raw_x1=raw_x1,
            raw_x2=raw_x2,
            scale=xscale,
            xiscale=xiscale,
            startfrac=startfrac,
            texturemid=_i32(thing.z + lump.topoffset - player.viewz),
            flip=flip,
            tz=tz,
        ),
        None,
    )


def r_sort_vissprites_source_shape(vissprites: Sequence[VisSprite]) -> tuple[VisSprite, ...]:
    return tuple(sorted(vissprites, key=lambda sprite: sprite.scale))


def apply_drawseg_sprite_clips(
    vis: VisSprite,
    drawsegs: Sequence[DrawSegClip],
    *,
    width: int = FRAMEBUFFER_WIDTH,
    height: int = FRAMEBUFFER_HEIGHT,
) -> tuple[list[int], list[int], int]:
    floorclip = [height] * width
    ceilingclip = [-1] * width
    changed_columns: set[int] = set()
    for drawseg in drawsegs:
        left = max(vis.x1, drawseg.x1, 0)
        right = min(vis.x2, drawseg.x2, width - 1)
        if left > right:
            continue
        for x in range(left, right + 1):
            offset = x - drawseg.x1
            if drawseg.sprbottomclip is not None and 0 <= offset < len(drawseg.sprbottomclip):
                if drawseg.sprbottomclip[offset] < floorclip[x]:
                    floorclip[x] = drawseg.sprbottomclip[offset]
                    changed_columns.add(x)
            if drawseg.sprtopclip is not None and 0 <= offset < len(drawseg.sprtopclip):
                if drawseg.sprtopclip[offset] > ceilingclip[x]:
                    ceilingclip[x] = drawseg.sprtopclip[offset]
                    changed_columns.add(x)
    return floorclip, ceilingclip, len(changed_columns)


def r_draw_sprite_range_source_shape(
    vis: VisSprite,
    posts_for_column: Callable[[int], Sequence[stage09.PatchColumnPost] | None],
    source_index_for_pixels: Callable[[bytes], int],
    *,
    floorclip: Sequence[int] | None = None,
    ceilingclip: Sequence[int] | None = None,
    max_new_columns: int | None = None,
) -> tuple[tuple[stage12.Stage12ColumnCommand, ...], int, int, int]:
    commands: list[stage12.Stage12ColumnCommand] = []
    source_skips = 0
    columns_drawn = 0
    frac = vis.startfrac
    sprtopscreen = CENTERYFRAC - stage04.fixed_mul(vis.texturemid, vis.scale)
    floorclip = floorclip or [FRAMEBUFFER_HEIGHT] * FRAMEBUFFER_WIDTH
    ceilingclip = ceilingclip or [-1] * FRAMEBUFFER_WIDTH

    for x in range(vis.x1, vis.x2 + 1):
        if max_new_columns is not None and columns_drawn >= max_new_columns:
            break
        patch_column = frac >> FRACBITS
        posts = posts_for_column(patch_column)
        if posts is None:
            source_skips += 1
            frac = _i32(frac + vis.xiscale)
            continue
        column_commands = stage12.masked_post_draw_commands(
            posts,
            x=x,
            texture_id=vis.sprite,
            texture_name=vis.sprite_name,
            texture_column=patch_column,
            sprtopscreen=sprtopscreen,
            spryscale=vis.scale,
            dc_texturemid=vis.texturemid,
            mfloorclip=floorclip[x],
            mceilingclip=ceilingclip[x],
            source_index_for_pixels=source_index_for_pixels,
        )
        if column_commands:
            columns_drawn += 1
            commands.extend(column_commands)
        frac = _i32(frac + vis.xiscale)

    return tuple(commands), columns_drawn, len(commands), source_skips


def visible_sector_indices_for_primary_frame(wad_path: str | Path) -> tuple[int, ...]:
    loaded, subsectors, subsector_sectors, nodes, segs = stage07._runtime_segs_for_loaded_map(wad_path)
    state = stage07.SegClipDebugState()
    sectors: list[int] = []

    def walk(bspnum: int) -> None:
        if bspnum & stage03.NF_SUBSECTOR:
            subsector_id = 0 if bspnum == 0xFFFFFFFF else (bspnum & ~stage03.NF_SUBSECTOR)
            if 0 <= subsector_id < len(subsector_sectors):
                sectors.append(subsector_sectors[subsector_id])
            count, firstline = subsectors[subsector_id]
            for offset in range(count):
                seg_index = firstline + offset
                stage07.debug_add_line(
                    state,
                    segs[seg_index],
                    loaded.vertices,
                    loaded.linedefs,
                    loaded.sidedefs,
                    loaded.sectors,
                    frontsector_index=subsector_sectors[subsector_id],
                    seg_index=seg_index,
                )
            return

        node = nodes[bspnum]
        side = stage03.point_on_side_fixed(stage07.VIEW_X_FIXED, stage07.VIEW_Y_FIXED, node)
        walk(node[12 + side])
        back_side = side ^ 1
        bbox_start = 4 + back_side * 4
        if stage04.check_bbox(node[bbox_start : bbox_start + 4], solidsegs=state.solidsegs):
            walk(node[12 + back_side])

    walk(len(nodes) - 1 if nodes else 0xFFFFFFFF)
    return tuple(dict.fromkeys(sectors))


def r_add_sprites_source_shape(
    mobjs: Sequence[RenderMobj],
    player: MinimalPlayer,
    sprite_metadata: SpriteMetadata,
    sector_indices: Sequence[int] | None = None,
    *,
    max_vissprites: int = MAXVISSPRITES,
) -> tuple[tuple[VisSprite, ...], int, dict[str, int]]:
    sector_set = set(sector_indices) if sector_indices is not None else None
    state = VisSpriteState(max_vissprites=max_vissprites)
    r_clear_sprites_source_shape(state)
    rejects: dict[str, int] = {}

    for mobj in mobjs:
        if sector_set is not None and mobj.sector not in sector_set:
            continue
        vis, reason = r_project_sprite_source_shape(mobj, player, sprite_metadata)
        if vis is None:
            rejects[reason or "unknown"] = rejects.get(reason or "unknown", 0) + 1
            continue
        r_new_vissprite_source_shape(state, vis)

    return tuple(state.vissprites or ()), state.overflow_count, rejects


def draw_sorted_sprites_source_shape(
    wad: WadFile,
    sprite_metadata: SpriteMetadata,
    sorted_vissprites: Sequence[VisSprite],
    palette32: Sequence[int],
    initial_signature: int,
    *,
    max_draw_columns: int = DEFAULT_MAX_SPRITE_DRAW_COLUMNS,
    drawsegs: Sequence[DrawSegClip] = (),
) -> SpriteDrawResult:
    column_sources: list[bytes] = []
    source_index_by_pixels: dict[bytes, int] = {}

    def source_index_for_pixels(pixels: bytes) -> int:
        index = source_index_by_pixels.get(pixels)
        if index is None:
            index = len(column_sources)
            source_index_by_pixels[pixels] = index
            column_sources.append(pixels)
        return index

    commands: list[stage12.Stage12ColumnCommand] = []
    columns_drawn = 0
    source_skips = 0
    drawseg_clip_columns = 0
    first_drawn: VisSprite | None = None
    first_drawn_patch_column = 0

    for vis in sorted_vissprites:
        if columns_drawn >= max_draw_columns:
            break
        if vis.patch < 0 or vis.patch >= len(sprite_metadata.lumps):
            source_skips += 1
            continue
        lump = sprite_metadata.lumps[vis.patch]
        lump_record = wad.lumps[sprite_metadata.firstspritelump + vis.patch]
        data = wad.read_lump(lump_record)
        header = stage08.parse_patch_header(data, lump_name=lump_record.name)

        def posts_for_column(column: int) -> Sequence[stage09.PatchColumnPost] | None:
            if column < 0 or column >= header.width:
                return None
            return stage09.parse_patch_column_posts(data, column, lump_name=lump.name)

        floorclip, ceilingclip, clipped = apply_drawseg_sprite_clips(vis, drawsegs)
        drawseg_clip_columns += clipped
        sprite_commands, sprite_columns, _post_count, sprite_source_skips = (
            r_draw_sprite_range_source_shape(
                vis,
                posts_for_column,
                source_index_for_pixels,
                floorclip=floorclip,
                ceilingclip=ceilingclip,
                max_new_columns=max_draw_columns - columns_drawn,
            )
        )
        if sprite_columns and first_drawn is None:
            first_drawn = vis
            first_drawn_patch_column = sprite_commands[0].texture_column
        commands.extend(sprite_commands)
        columns_drawn += sprite_columns
        source_skips += sprite_source_skips

    signature = initial_signature
    pixels_drawn = 0
    for command in commands:
        signature, pixels = stage12._append_signature_for_command(
            signature,
            command,
            column_sources[command.source_index],
            palette32,
        )
        pixels_drawn += pixels

    return SpriteDrawResult(
        commands=tuple(commands),
        column_sources=tuple(column_sources),
        columns_drawn=columns_drawn,
        post_commands_drawn=len(commands),
        pixels_drawn=pixels_drawn,
        source_skip_count=source_skips,
        drawseg_clip_columns=drawseg_clip_columns,
        framebuffer_signature=signature,
        first_drawn=first_drawn,
        first_drawn_patch_column=first_drawn_patch_column,
    )


def _reference_stage13_uncached(wad_path: str) -> Stage13ThingsSpritesReference:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    map_lumps = wad.map_lumps("MAP01")
    thing_lump = wad.read_lump(map_lumps.get("THINGS"))
    thing_load = p_loadthings_source_shape(thing_lump)
    doom = parse_source_info_tables()
    geometry = build_map_geometry(wad, loaded)
    spawn = p_spawn_mapthings_source_shape(
        thing_load.things,
        doom,
        loaded=loaded,
        geometry=geometry,
        options=SpawnOptions(),
    )
    if not spawn.players:
        raise ValueError("MAP01 has no active player start for stage13")

    sprite_metadata = init_sprite_metadata_source_shape(wad, doom)
    stage12_ref = stage12.reference_sky_and_masked_midtextures_for_pinned_map(wad_path)
    primary_sectors = visible_sector_indices_for_primary_frame(wad_path)
    vissprites, overflow_count, rejects = r_add_sprites_source_shape(
        spawn.mobjs,
        spawn.players[0],
        sprite_metadata,
        primary_sectors,
    )
    rejects = dict(rejects)
    if overflow_count:
        rejects["overflow"] = overflow_count
    sorted_vissprites = r_sort_vissprites_source_shape(vissprites)
    draw = draw_sorted_sprites_source_shape(
        wad,
        sprite_metadata,
        sorted_vissprites,
        stage12_ref.palette32,
        stage12_ref.framebuffer_signature,
    )

    return Stage13ThingsSpritesReference(
        stage12=stage12_ref,
        thing_load=thing_load,
        spawn=spawn,
        sprite_metadata=sprite_metadata,
        player=spawn.players[0],
        primary_sector_count=len(primary_sectors),
        vissprites=sorted_vissprites,
        projection_rejects=rejects,
        draw=draw,
        probe_active=0 if draw.columns_drawn else 1,
    )


@lru_cache(maxsize=4)
def _reference_stage13_cached(wad_path: str) -> Stage13ThingsSpritesReference:
    return _reference_stage13_uncached(wad_path)


def reference_things_sprites_real_frame_setup_for_pinned_map(
    wad_path: str | Path,
) -> Stage13ThingsSpritesReference:
    return _reference_stage13_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage13ThingsSpritesReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_things_sprites_real_frame_setup_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage13_load_wad_things_sprites_and_real_frame_setup")

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


def emit_source_stage13_load_wad_things_sprites_and_real_frame_setup(pe: PE32) -> None:
    pe.label("source_stage13_load_wad_things_sprites_and_real_frame_setup")
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
    x86.jne_rel32(pe, "source_stage13_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage13_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage13_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage13_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage13_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage13_close_and_return")

    pe.label("source_stage13_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage13_close_and_return")

    x86.call_rel32(pe, "render_init_texture_data_setup_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage13_close_and_return")

    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage13_close_and_return")

    x86.call_rel32(pe, "source_stage06_run_live_seg_clip_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage13_close_and_return")

    x86.call_rel32(pe, "render_composite_two_sided_wall_edges_debug")
    x86.call_rel32(pe, "render_visplanes_floor_ceiling_debug")
    x86.call_rel32(pe, "render_sky_and_masked_midtextures_debug")
    x86.call_rel32(pe, "render_things_sprites_real_frame_setup_debug")
    x86.call_rel32(pe, "build_success_status")
    x86.call_rel32(pe, "append_stage13_success_status")

    pe.label("source_stage13_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_render_things_sprites_and_real_frame_setup_debug(pe: PE32) -> None:
    pe.label("P_LoadThings_decode_debug")
    pe.label("P_SpawnMapThing_render_subset_debug")
    pe.label("mobj_t_render_record_debug")
    pe.label("player_t_minimal_view_debug")
    pe.label("info_tables_sprite_state_debug")
    pe.label("R_InitSpriteLumps_metadata_debug")
    pe.label("R_InitSprites_vissprite_pool_debug")
    pe.label("R_ProjectSprite_source_shape_debug")
    pe.label("R_Subsector_AddSprites_sector_gather_debug")
    pe.label("R_DrawSprite_drawseg_clip_debug")
    pe.label("R_DrawSpriteRange_columns_debug")
    pe.label("R_SetupFrame_real_player_start_debug")
    pe.label("render_things_sprites_real_frame_setup_debug")

    x86.mov_mem_abs32_imm32(pe, "stage13_sprite_columns_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage13_sprite_post_commands_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage13_sprite_pixels_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage13_pixels_drawn", 0)
    x86.mov_reg_mem_abs32(pe, "eax", "stage12_pixel_signature")
    x86.mov_mem_abs32_eax(pe, "stage13_pixel_signature")
    x86.mov_mem_abs32_abs32(pe, "dc_colormap", "stage13_palette32")

    stage12._emit_column_command_loop(
        pe,
        command_label="stage13_sprite_commands",
        count_label="stage13_sprite_command_count",
        scan_label="stage13_sprite_scan_ptr",
        remaining_label="stage13_sprite_remaining_commands",
        loop_label="stage13_sprite_command_loop",
        done_label="stage13_sprite_commands_done",
        column_counter_label="stage13_sprite_post_commands_drawn",
        draw_func_label="render_draw_stage13_sprite_column_debug",
    )

    x86.mov_reg_mem_abs32(pe, "eax", "stage13_expected_sprite_columns_drawn")
    x86.mov_mem_abs32_eax(pe, "stage13_sprite_columns_drawn")
    x86.ret(pe)


def emit_render_draw_stage13_sprite_column_debug(pe: PE32) -> None:
    label = "render_draw_stage13_sprite_column_debug"
    pe.label(label)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_reg_mem_abs32(pe, "eax", "dc_yh")
    x86.sub_reg_mem_abs32(pe, "eax", "dc_yl")
    x86.jl_rel32(pe, f"{label}_done")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "stage13_column_remaining")

    x86.mov_reg_mem_abs32(pe, "ebx", "dc_yl")
    x86.mov_reg_reg(pe, "edx", "ebx")
    x86.shl_reg_imm8(pe, "ebx", 8)
    x86.shl_reg_imm8(pe, "edx", 6)
    x86.add_reg_reg(pe, "ebx", "edx")
    x86.add_reg_mem_abs32(pe, "ebx", "dc_x")
    x86.shl_reg_imm8(pe, "ebx", 2)
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.add_reg_reg(pe, "edi", "ebx")

    x86.mov_reg_mem_abs32(pe, "eax", "dc_yl")
    x86.add_reg_imm32(pe, "eax", -CENTER_Y)
    x86.mov_reg_mem_abs32(pe, "ecx", "dc_iscale")
    x86.imul_reg(pe, "ecx")
    x86.add_reg_mem_abs32(pe, "eax", "dc_texturemid")
    x86.mov_mem_abs32_eax(pe, "dc_frac")

    pe.label(f"{label}_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "dc_frac")
    x86.sar_reg_imm8(pe, "eax", FRACBITS)
    x86.and_reg_imm32(pe, "eax", WALL_COLUMN_SOURCE_HEIGHT - 1)
    x86.mov_reg_mem_abs32(pe, "esi", "dc_source")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.movzx_reg_byte_ptr_reg(pe, "eax", "esi")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_mem_abs32(pe, "esi", "dc_colormap")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "esi")
    x86.mov_ptr_reg_eax(pe, "edi")

    x86.mov_reg_mem_abs32(pe, "ecx", "stage13_pixel_signature")
    x86.imul_reg_reg_imm32(pe, "ecx", "ecx", FNV_PRIME)
    x86.xor_reg_reg(pe, "ecx", "eax")
    x86.mov_mem_abs32_reg(pe, "stage13_pixel_signature", "ecx")
    stage07._emit_inc_abs32(pe, "stage13_pixels_drawn")
    stage07._emit_inc_abs32(pe, "stage13_sprite_pixels_drawn")

    x86.add_reg_imm32(pe, "edi", FRAMEBUFFER_WIDTH * 4)
    x86.mov_reg_mem_abs32(pe, "eax", "dc_frac")
    x86.add_reg_mem_abs32(pe, "eax", "dc_iscale")
    x86.mov_mem_abs32_eax(pe, "dc_frac")
    x86.dec_mem_abs32(pe, "stage13_column_remaining")
    x86.jne_rel32(pe, f"{label}_loop")

    pe.label(f"{label}_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
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


def emit_append_stage13_success_status(pe: PE32) -> None:
    pe.label("append_stage13_success_status")

    _emit_seek_buffer_end(pe, "status_success_buffer", "stage13_status")
    stage01.append_c_string_label(pe, "status_stage13_success_header")
    stage01.append_u32_label(pe, "status_stage13_things_prefix", "stage13_thing_count")
    stage01.append_u32_label(pe, "status_stage13_vissprites_prefix", "stage13_vissprite_count")
    stage01.append_u32_label(pe, "status_stage13_columns_prefix", "stage13_sprite_columns_drawn")
    stage01.append_u32_label(pe, "status_stage13_pixels_prefix", "stage13_sprite_pixels_drawn")
    stage01.append_u32_label(pe, "status_stage13_signature_prefix", "stage13_pixel_signature")
    stage01.append_c_string_label(pe, "status_stage13_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage13_title")
    stage01.append_u32_label(pe, "title_stage13_thing_count_prefix", "stage13_thing_count")
    stage01.append_u32_label(pe, "title_stage13_player_start_prefix", "stage13_player_start_count")
    stage01.append_u32_label(pe, "title_stage13_render_mobj_prefix", "stage13_render_mobj_count")
    stage01.append_u32_label(pe, "title_stage13_unsupported_prefix", "stage13_unsupported_type_count")
    stage01.append_u32_label(pe, "title_stage13_skill_skip_prefix", "stage13_skill_skip_count")
    stage01.append_i32_label(pe, "title_stage13_player_x_prefix", "stage13_player_x")
    stage01.append_i32_label(pe, "title_stage13_player_y_prefix", "stage13_player_y")
    stage01.append_u32_label(pe, "title_stage13_player_angle_prefix", "stage13_player_angle_degrees")
    stage01.append_u32_label(pe, "title_stage13_player_sector_prefix", "stage13_player_sector")
    stage01.append_u32_label(pe, "title_stage13_sprite_name_count_prefix", "stage13_sprite_name_count")
    stage01.append_u32_label(pe, "title_stage13_sprite_lump_count_prefix", "stage13_sprite_lump_count")
    stage01.append_u32_label(pe, "title_stage13_missing_frame_prefix", "stage13_sprite_missing_frames")
    stage01.append_u32_label(pe, "title_stage13_sector_count_prefix", "stage13_primary_sector_count")
    stage01.append_u32_label(pe, "title_stage13_vissprite_prefix", "stage13_vissprite_count")
    stage01.append_u32_label(pe, "title_stage13_vissprite_overflow_prefix", "stage13_vissprite_overflow_count")
    stage01.append_u32_label(pe, "title_stage13_probe_prefix", "stage13_probe_active")
    stage01.append_u32_label(pe, "title_stage13_first_thing_prefix", "stage13_first_sprite_mapthing_index")
    stage01.append_u32_label(pe, "title_stage13_first_sprite_prefix", "stage13_first_sprite_id")
    stage01.append_c_string_label(pe, "title_stage13_first_sprite_name_prefix")
    stage01.append_c_string_label(pe, "stage13_first_sprite_name")
    stage01.append_u32_label(pe, "title_stage13_first_frame_prefix", "stage13_first_sprite_frame")
    stage01.append_u32_label(pe, "title_stage13_first_patch_prefix", "stage13_first_sprite_patch")
    stage01.append_c_string_label(pe, "title_stage13_first_patch_name_prefix")
    stage01.append_c_string_label(pe, "stage13_first_sprite_patch_name")
    stage01.append_u32_label(pe, "title_stage13_sprite_columns_prefix", "stage13_sprite_columns_drawn")
    stage01.append_u32_label(pe, "title_stage13_sprite_posts_prefix", "stage13_sprite_post_commands_drawn")
    stage01.append_u32_label(pe, "title_stage13_sprite_pixels_prefix", "stage13_sprite_pixels_drawn")
    stage01.append_u32_label(pe, "title_stage13_sprite_signature_prefix", "stage13_pixel_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def _emit_u32_table(pe: PE32, label: str, values: Sequence[int]) -> None:
    pe.label(label)
    for value in values:
        pe.emit_u32(value & 0xFFFFFFFF)


def _emit_stage13_column_commands(pe: PE32, commands: Sequence[stage12.Stage12ColumnCommand]) -> None:
    for command in commands:
        pe.emit_u32(command.x)
        pe.emit_u32(command.yl)
        pe.emit_u32(command.yh)
        pe.emit_u32(command.iscale)
        pe.emit_u32(command.texturemid)
        pe.write_abs32(f"stage13_column_source_{command.source_index}")


def emit_stage13_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    first = ref.draw.first_drawn if ref is not None else None

    pe.align_section(4)
    pe.label("stage13_thing_count")
    pe.emit_u32(ref.thing_load.loaded_count if ref is not None else 0)
    pe.label("stage13_player_start_count")
    pe.emit_u32(ref.spawn.player_start_count if ref is not None else 0)
    pe.label("stage13_player_mobj_count")
    pe.emit_u32(ref.spawn.player_mobj_count if ref is not None else 0)
    pe.label("stage13_inert_mobj_count")
    pe.emit_u32(ref.spawn.inert_mobj_count if ref is not None else 0)
    pe.label("stage13_render_mobj_count")
    pe.emit_u32(len(ref.spawn.mobjs) if ref is not None else 0)
    pe.label("stage13_unsupported_type_count")
    pe.emit_u32(ref.spawn.unsupported_type_count if ref is not None else 0)
    pe.label("stage13_option_skip_count")
    pe.emit_u32(ref.spawn.option_skip_count if ref is not None else 0)
    pe.label("stage13_skill_skip_count")
    pe.emit_u32(ref.spawn.skill_skip_count if ref is not None else 0)
    pe.label("stage13_nomonitor_skip_count")
    pe.emit_u32(ref.spawn.nomonster_skip_count if ref is not None else 0)
    pe.label("stage13_spawn_overflow_count")
    pe.emit_u32(ref.spawn.overflow_count if ref is not None else 0)

    pe.label("stage13_player_x")
    pe.emit_u32(ref.player.x >> FRACBITS if ref is not None else 0)
    pe.label("stage13_player_y")
    pe.emit_u32(ref.player.y >> FRACBITS if ref is not None else 0)
    pe.label("stage13_player_angle")
    pe.emit_u32(ref.player.angle if ref is not None else 0)
    pe.label("stage13_player_angle_degrees")
    pe.emit_u32(angle_to_degrees(ref.player.angle) if ref is not None else 0)
    pe.label("stage13_player_sector")
    pe.emit_u32(ref.player.sector if ref is not None else 0)
    pe.label("stage13_player_subsector")
    pe.emit_u32(ref.player.subsector if ref is not None else 0)
    pe.label("stage13_player_viewz")
    pe.emit_u32(ref.player.viewz if ref is not None else 0)

    pe.label("stage13_sprite_name_count")
    pe.emit_u32(len(ref.sprite_metadata.sprnames) if ref is not None else 0)
    pe.label("stage13_sprite_lump_count")
    pe.emit_u32(len(ref.sprite_metadata.lumps) if ref is not None else 0)
    pe.label("stage13_sprite_defs_present")
    pe.emit_u32(ref.sprite_metadata.sprite_defs_present if ref is not None else 0)
    pe.label("stage13_sprite_frames_present")
    pe.emit_u32(ref.sprite_metadata.frames_present if ref is not None else 0)
    pe.label("stage13_sprite_missing_frames")
    pe.emit_u32(ref.sprite_metadata.missing_frames if ref is not None else 0)

    pe.label("stage13_primary_sector_count")
    pe.emit_u32(ref.primary_sector_count if ref is not None else 0)
    pe.label("stage13_vissprite_count")
    pe.emit_u32(len(ref.vissprites) if ref is not None else 0)
    pe.label("stage13_vissprite_overflow_count")
    pe.emit_u32(ref.projection_rejects.get("overflow", 0) if ref is not None else 0)
    pe.label("stage13_project_minz_reject_count")
    pe.emit_u32(ref.projection_rejects.get("minz", 0) if ref is not None else 0)
    pe.label("stage13_project_side_reject_count")
    pe.emit_u32(ref.projection_rejects.get("side", 0) if ref is not None else 0)
    pe.label("stage13_project_left_reject_count")
    pe.emit_u32(ref.projection_rejects.get("left", 0) if ref is not None else 0)
    pe.label("stage13_project_right_reject_count")
    pe.emit_u32(ref.projection_rejects.get("right", 0) if ref is not None else 0)
    pe.label("stage13_probe_active")
    pe.emit_u32(ref.probe_active if ref is not None else 0)

    pe.label("stage13_first_sprite_mapthing_index")
    pe.emit_u32(first.mapthing_index if first is not None else 0)
    pe.label("stage13_first_sprite_id")
    pe.emit_u32(first.sprite if first is not None else 0)
    pe.label("stage13_first_sprite_frame")
    pe.emit_u32((first.frame & FF_FRAMEMASK) if first is not None else 0)
    pe.label("stage13_first_sprite_patch")
    pe.emit_u32(first.patch if first is not None else 0)
    pe.label("stage13_first_sprite_patch_column")
    pe.emit_u32(ref.draw.first_drawn_patch_column if ref is not None else 0)
    pe.label("stage13_first_sprite_x1")
    pe.emit_u32(first.x1 if first is not None else 0)
    pe.label("stage13_first_sprite_x2")
    pe.emit_u32(first.x2 if first is not None else 0)
    pe.label("stage13_first_sprite_scale")
    pe.emit_u32(first.scale if first is not None else 0)

    pe.label("stage13_expected_sprite_columns_drawn")
    pe.emit_u32(ref.draw.columns_drawn if ref is not None else 0)
    pe.label("stage13_expected_sprite_post_commands_drawn")
    pe.emit_u32(ref.draw.post_commands_drawn if ref is not None else 0)
    pe.label("stage13_expected_sprite_pixels_drawn")
    pe.emit_u32(ref.draw.pixels_drawn if ref is not None else 0)
    pe.label("stage13_sprite_column_source_skips")
    pe.emit_u32(ref.draw.source_skip_count if ref is not None else 0)
    pe.label("stage13_sprite_drawseg_clip_columns")
    pe.emit_u32(ref.draw.drawseg_clip_columns if ref is not None else 0)
    pe.label("stage13_expected_pixel_signature")
    pe.emit_u32(ref.draw.framebuffer_signature if ref is not None else 0)
    pe.label("stage13_sprite_command_count")
    pe.emit_u32(len(ref.draw.commands) if ref is not None else 0)
    pe.label("stage13_sprite_source_count")
    pe.emit_u32(len(ref.draw.column_sources) if ref is not None else 0)

    pe.label("stage13_sprite_columns_drawn")
    pe.emit_u32(0)
    pe.label("stage13_sprite_post_commands_drawn")
    pe.emit_u32(0)
    pe.label("stage13_sprite_pixels_drawn")
    pe.emit_u32(0)
    pe.label("stage13_pixels_drawn")
    pe.emit_u32(0)
    pe.label("stage13_pixel_signature")
    pe.emit_u32(0)
    pe.label("stage13_sprite_scan_ptr")
    pe.emit_u32(0)
    pe.label("stage13_sprite_remaining_commands")
    pe.emit_u32(0)
    pe.label("stage13_column_remaining")
    pe.emit_u32(0)

    _emit_u32_table(pe, "stage13_palette32", list(ref.stage12.palette32) if ref is not None else [0] * 256)

    pe.align_section(4)
    pe.label("stage13_sprite_commands")
    if ref is not None:
        _emit_stage13_column_commands(pe, ref.draw.commands)

    pe.align_section(1)
    if ref is not None:
        for index, pixels in enumerate(ref.draw.column_sources):
            pe.label(f"stage13_column_source_{index}")
            pe.emit(pixels)

    pe.align_section(1)
    pe.label("stage13_first_sprite_name")
    x86.emit_asciiz(pe, first.sprite_name if first is not None else "")
    pe.label("stage13_first_sprite_patch_name")
    x86.emit_asciiz(pe, first.patch_name if first is not None else "")

    pe.label("status_stage13_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage13_things_sprites_and_real_frame_setup\r\n"
        "THINGS and sprite frame setup OK\r\n",
    )
    pe.label("status_stage13_things_prefix")
    x86.emit_asciiz(pe, "\r\nP_LoadThings records: ")
    pe.label("status_stage13_vissprites_prefix")
    x86.emit_asciiz(pe, "\r\nR_ProjectSprite visibles: ")
    pe.label("status_stage13_columns_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime sprite columns: ")
    pe.label("status_stage13_pixels_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime sprite pixels: ")
    pe.label("status_stage13_signature_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime stage13 RGB signature: ")
    pe.label("status_stage13_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage13 decodes real MAP01 THINGS, seeds R_SetupFrame from the "
        "player-one start, table-emits reachable sprite metadata, gathers "
        "bounded vissprites, sorts them, and draws real sprite patch posts "
        "through R_DrawSpriteRange and R_DrawMaskedColumn after the released "
        "stage12 path.\r\n",
    )

    pe.label("title_stage13_thing_count_prefix")
    x86.emit_asciiz(pe, " TH=")
    pe.label("title_stage13_player_start_prefix")
    x86.emit_asciiz(pe, " PST=")
    pe.label("title_stage13_render_mobj_prefix")
    x86.emit_asciiz(pe, " RMO=")
    pe.label("title_stage13_unsupported_prefix")
    x86.emit_asciiz(pe, " UTH=")
    pe.label("title_stage13_skill_skip_prefix")
    x86.emit_asciiz(pe, " SKSK=")
    pe.label("title_stage13_player_x_prefix")
    x86.emit_asciiz(pe, " PSX=")
    pe.label("title_stage13_player_y_prefix")
    x86.emit_asciiz(pe, " PSY=")
    pe.label("title_stage13_player_angle_prefix")
    x86.emit_asciiz(pe, " PSA=")
    pe.label("title_stage13_player_sector_prefix")
    x86.emit_asciiz(pe, " PSS=")
    pe.label("title_stage13_sprite_name_count_prefix")
    x86.emit_asciiz(pe, " SPNAMES=")
    pe.label("title_stage13_sprite_lump_count_prefix")
    x86.emit_asciiz(pe, " SPLUMPS=")
    pe.label("title_stage13_missing_frame_prefix")
    x86.emit_asciiz(pe, " SPMISS=")
    pe.label("title_stage13_sector_count_prefix")
    x86.emit_asciiz(pe, " SPSEC=")
    pe.label("title_stage13_vissprite_prefix")
    x86.emit_asciiz(pe, " VIS=")
    pe.label("title_stage13_vissprite_overflow_prefix")
    x86.emit_asciiz(pe, " VISOV=")
    pe.label("title_stage13_probe_prefix")
    x86.emit_asciiz(pe, " SPROBE=")
    pe.label("title_stage13_first_thing_prefix")
    x86.emit_asciiz(pe, " FSTH=")
    pe.label("title_stage13_first_sprite_prefix")
    x86.emit_asciiz(pe, " FSPR=")
    pe.label("title_stage13_first_sprite_name_prefix")
    x86.emit_asciiz(pe, " FSN=")
    pe.label("title_stage13_first_frame_prefix")
    x86.emit_asciiz(pe, " FSF=")
    pe.label("title_stage13_first_patch_prefix")
    x86.emit_asciiz(pe, " FSPT=")
    pe.label("title_stage13_first_patch_name_prefix")
    x86.emit_asciiz(pe, " FSPN=")
    pe.label("title_stage13_sprite_columns_prefix")
    x86.emit_asciiz(pe, " SPCOL=")
    pe.label("title_stage13_sprite_posts_prefix")
    x86.emit_asciiz(pe, " SPPOST=")
    pe.label("title_stage13_sprite_pixels_prefix")
    x86.emit_asciiz(pe, " SPPIX=")
    pe.label("title_stage13_sprite_signature_prefix")
    x86.emit_asciiz(pe, " S13SIG=")


def build_source_stage13_things_sprites_and_real_frame_setup_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage13_load_wad_things_sprites_and_real_frame_setup(pe)
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
    emit_render_things_sprites_and_real_frame_setup_debug(pe)
    emit_render_draw_stage13_sprite_column_debug(pe)
    stage12.emit_build_success_status(pe)
    emit_append_stage13_success_status(pe)
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
    emit_stage13_data(pe)
    return pe.build("entry")


def write_source_stage13_things_sprites_and_real_frame_setup_exe(path: str | Path) -> bytes:
    image = build_source_stage13_things_sprites_and_real_frame_setup_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage13 THINGS/sprite PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage13_things_sprites_and_real_frame_setup.exe",
        help="path to write, default: build/source_stage13_things_sprites_and_real_frame_setup.exe",
    )
    args = parser.parse_args()
    write_source_stage13_things_sprites_and_real_frame_setup_exe(args.output)


if __name__ == "__main__":
    main()
