from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.wad import MapLumps, WadError, WadFile, normalize_name


NO_SIDEDEF = 0xFFFF

VERTEX_RECORD_SIZE = 4
THING_RECORD_SIZE = 10
LINEDEF_RECORD_SIZE = 14
SIDEDEF_RECORD_SIZE = 30
SECTOR_RECORD_SIZE = 26

_VERTEX_STRUCT = struct.Struct("<hh")
_THING_STRUCT = struct.Struct("<hhHHH")
_LINEDEF_STRUCT = struct.Struct("<HHHHHHH")
_SIDEDEF_STRUCT = struct.Struct("<hh8s8s8sH")
_SECTOR_STRUCT = struct.Struct("<hh8s8shHH")

REQUIRED_MAP_LUMPS = (
    "THINGS",
    "LINEDEFS",
    "SIDEDEFS",
    "VERTEXES",
    "SECTORS",
)

DEFAULT_MAP_CANDIDATES = ("MAP01", "E1M1")
PLAYER_START_TYPES = frozenset({1, 2, 3, 4})


class MapFormatError(ValueError):
    """Raised when a classic DOOM map lump is malformed."""


@dataclass(frozen=True)
class Vertex:
    x: int
    y: int


@dataclass(frozen=True)
class Thing:
    x: int
    y: int
    angle: int
    type: int
    flags: int

    @property
    def is_player_start(self) -> bool:
        return self.type in PLAYER_START_TYPES


@dataclass(frozen=True)
class LineDef:
    start_vertex: int
    end_vertex: int
    flags: int
    special_type: int
    sector_tag: int
    right_sidedef: int
    left_sidedef: int

    @property
    def is_two_sided(self) -> bool:
        return self.left_sidedef != NO_SIDEDEF


@dataclass(frozen=True)
class SideDef:
    x_offset: int
    y_offset: int
    upper_texture: str
    lower_texture: str
    middle_texture: str
    sector: int


@dataclass(frozen=True)
class Sector:
    floor_height: int
    ceiling_height: int
    floor_flat: str
    ceiling_flat: str
    light_level: int
    special_type: int
    tag: int


@dataclass(frozen=True)
class LoadedMap:
    name: str
    source: str
    vertices: tuple[Vertex, ...]
    linedefs: tuple[LineDef, ...]
    sidedefs: tuple[SideDef, ...]
    sectors: tuple[Sector, ...]
    things: tuple[Thing, ...]

    @property
    def bounds(self) -> tuple[int, int, int, int] | None:
        if not self.vertices:
            return None
        xs = [vertex.x for vertex in self.vertices]
        ys = [vertex.y for vertex in self.vertices]
        return min(xs), min(ys), max(xs), max(ys)

    @property
    def player_starts(self) -> tuple[Thing, ...]:
        return tuple(thing for thing in self.things if thing.is_player_start)

    @property
    def one_sided_linedef_count(self) -> int:
        return sum(1 for linedef in self.linedefs if not linedef.is_two_sided)

    @property
    def two_sided_linedef_count(self) -> int:
        return sum(1 for linedef in self.linedefs if linedef.is_two_sided)


def select_default_map_name(wad: WadFile) -> str:
    marker_names = {normalize_name(marker.name): marker.name for marker in wad.map_markers()}
    for candidate in DEFAULT_MAP_CANDIDATES:
        if candidate in marker_names:
            return marker_names[candidate]

    markers = wad.map_markers()
    if not markers:
        raise MapFormatError("WAD does not contain any classic DOOM map markers")
    return markers[0].name


def load_map_from_file(path: str | Path, map_name: str | None = None) -> LoadedMap:
    wad = WadFile.from_file(path)
    return load_map(wad, map_name=map_name)


def load_map(wad: WadFile, map_name: str | None = None) -> LoadedMap:
    selected_map = map_name or select_default_map_name(wad)
    map_lumps = wad.map_lumps(selected_map)

    missing = tuple(name for name in REQUIRED_MAP_LUMPS if map_lumps.get(name) is None)
    if missing:
        raise MapFormatError(f"map {map_lumps.name} is missing required lumps: {', '.join(missing)}")

    return LoadedMap(
        name=map_lumps.name,
        source=wad.source,
        vertices=parse_vertices(_read_map_lump(wad, map_lumps, "VERTEXES")),
        linedefs=parse_linedefs(_read_map_lump(wad, map_lumps, "LINEDEFS")),
        sidedefs=parse_sidedefs(_read_map_lump(wad, map_lumps, "SIDEDEFS")),
        sectors=parse_sectors(_read_map_lump(wad, map_lumps, "SECTORS")),
        things=parse_things(_read_map_lump(wad, map_lumps, "THINGS")),
    )


def parse_vertices(data: bytes) -> tuple[Vertex, ...]:
    _require_aligned("VERTEXES", data, VERTEX_RECORD_SIZE)
    return tuple(Vertex(x=x, y=y) for x, y in _VERTEX_STRUCT.iter_unpack(data))


def parse_things(data: bytes) -> tuple[Thing, ...]:
    _require_aligned("THINGS", data, THING_RECORD_SIZE)
    return tuple(
        Thing(x=x, y=y, angle=angle, type=thing_type, flags=flags)
        for x, y, angle, thing_type, flags in _THING_STRUCT.iter_unpack(data)
    )


def parse_linedefs(data: bytes) -> tuple[LineDef, ...]:
    _require_aligned("LINEDEFS", data, LINEDEF_RECORD_SIZE)
    return tuple(
        LineDef(
            start_vertex=start_vertex,
            end_vertex=end_vertex,
            flags=flags,
            special_type=special_type,
            sector_tag=sector_tag,
            right_sidedef=right_sidedef,
            left_sidedef=left_sidedef,
        )
        for (
            start_vertex,
            end_vertex,
            flags,
            special_type,
            sector_tag,
            right_sidedef,
            left_sidedef,
        ) in _LINEDEF_STRUCT.iter_unpack(data)
    )


def parse_sidedefs(data: bytes) -> tuple[SideDef, ...]:
    _require_aligned("SIDEDEFS", data, SIDEDEF_RECORD_SIZE)
    return tuple(
        SideDef(
            x_offset=x_offset,
            y_offset=y_offset,
            upper_texture=_decode_fixed_name(upper_texture),
            lower_texture=_decode_fixed_name(lower_texture),
            middle_texture=_decode_fixed_name(middle_texture),
            sector=sector,
        )
        for x_offset, y_offset, upper_texture, lower_texture, middle_texture, sector
        in _SIDEDEF_STRUCT.iter_unpack(data)
    )


def parse_sectors(data: bytes) -> tuple[Sector, ...]:
    _require_aligned("SECTORS", data, SECTOR_RECORD_SIZE)
    return tuple(
        Sector(
            floor_height=floor_height,
            ceiling_height=ceiling_height,
            floor_flat=_decode_fixed_name(floor_flat),
            ceiling_flat=_decode_fixed_name(ceiling_flat),
            light_level=light_level,
            special_type=special_type,
            tag=tag,
        )
        for (
            floor_height,
            ceiling_height,
            floor_flat,
            ceiling_flat,
            light_level,
            special_type,
            tag,
        ) in _SECTOR_STRUCT.iter_unpack(data)
    )


def summary_lines(loaded_map: LoadedMap) -> Iterable[str]:
    yield f"WAD: {loaded_map.source}"
    yield f"map: {loaded_map.name}"
    yield f"vertices: {len(loaded_map.vertices)}"
    yield (
        f"linedefs: {len(loaded_map.linedefs)} "
        f"(one-sided: {loaded_map.one_sided_linedef_count}, "
        f"two-sided: {loaded_map.two_sided_linedef_count})"
    )
    yield f"sidedefs: {len(loaded_map.sidedefs)}"
    yield f"sectors: {len(loaded_map.sectors)}"
    yield f"things: {len(loaded_map.things)}"

    bounds = loaded_map.bounds
    if bounds is None:
        yield "bounds: no vertices"
    else:
        min_x, min_y, max_x, max_y = bounds
        yield f"bounds: x={min_x}..{max_x} y={min_y}..{max_y} size={max_x - min_x}x{max_y - min_y}"

    starts = loaded_map.player_starts
    if starts:
        yield "player starts:"
        for thing in starts:
            yield (
                f"  type={thing.type} at ({thing.x}, {thing.y}) "
                f"angle={thing.angle} flags=0x{thing.flags:04x}"
            )
    else:
        yield "player starts: none"

    if loaded_map.sectors:
        floor_heights = [sector.floor_height for sector in loaded_map.sectors]
        ceiling_heights = [sector.ceiling_height for sector in loaded_map.sectors]
        light_levels = [sector.light_level for sector in loaded_map.sectors]
        yield (
            f"sector heights: floor={min(floor_heights)}..{max(floor_heights)} "
            f"ceiling={min(ceiling_heights)}..{max(ceiling_heights)}"
        )
        yield f"light levels: {min(light_levels)}..{max(light_levels)}"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load and summarize a classic DOOM map from a WAD.")
    parser.add_argument("wad", type=Path, help="Path to an IWAD or PWAD file.")
    parser.add_argument("--map", dest="map_name", help="Map marker to load, such as MAP01 or E1M1.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        loaded_map = load_map_from_file(args.wad, map_name=args.map_name)
        for line in summary_lines(loaded_map):
            print(line)
    except (OSError, WadError, KeyError, ValueError) as exc:
        print(f"map_loader.py: {exc}", file=sys.stderr)
        return 1

    return 0


def _read_map_lump(wad: WadFile, map_lumps: MapLumps, name: str) -> bytes:
    lump = map_lumps.get(name)
    if lump is None:
        raise MapFormatError(f"map {map_lumps.name} is missing required lump: {name}")
    return wad.read_lump(lump)


def _require_aligned(lump_name: str, data: bytes, record_size: int) -> None:
    if len(data) % record_size:
        raise MapFormatError(
            f"{lump_name} lump size {len(data)} is not a multiple of {record_size} bytes"
        )


def _decode_fixed_name(raw_name: bytes) -> str:
    name_bytes = raw_name.split(b"\x00", 1)[0]
    try:
        return name_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise MapFormatError("map name field is not ASCII") from exc


if __name__ == "__main__":
    raise SystemExit(main())
