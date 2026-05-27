from __future__ import annotations

import argparse
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


HEADER_SIZE = 12
DIRECTORY_ENTRY_SIZE = 16

CLASSIC_MAP_LUMP_ORDER = (
    "THINGS",
    "LINEDEFS",
    "SIDEDEFS",
    "VERTEXES",
    "SEGS",
    "SSECTORS",
    "NODES",
    "SECTORS",
    "REJECT",
    "BLOCKMAP",
)
CORE_MAP_LUMPS = (
    "THINGS",
    "LINEDEFS",
    "SIDEDEFS",
    "VERTEXES",
    "SEGS",
    "SSECTORS",
    "NODES",
    "SECTORS",
)
EXTENDED_MAP_LUMPS = (
    "BEHAVIOR",
    "SCRIPTS",
)
KNOWN_MAP_LUMPS = CLASSIC_MAP_LUMP_ORDER + EXTENDED_MAP_LUMPS
COMMON_LUMPS = (
    "PLAYPAL",
    "COLORMAP",
)
TITLE_LUMP_CANDIDATES = (
    "TITLEPIC",
    "INTERPIC",
    "CREDIT",
    "HELP1",
    "HELP2",
)

_EPISODE_MAP_RE = re.compile(r"^E\dM\d$")
_DOOM2_MAP_RE = re.compile(r"^MAP\d\d$")


class WadError(ValueError):
    """Raised when a WAD file is malformed or unsupported."""


@dataclass(frozen=True)
class WadHeader:
    kind: str
    lump_count: int
    directory_offset: int


@dataclass(frozen=True)
class Lump:
    index: int
    name: str
    offset: int
    size: int
    raw_name: bytes

    @property
    def end_offset(self) -> int:
        return self.offset + self.size


@dataclass(frozen=True)
class MapLumps:
    marker: Lump
    lumps: dict[str, Lump]

    @property
    def name(self) -> str:
        return self.marker.name

    def get(self, name: str) -> Lump | None:
        return self.lumps.get(normalize_name(name))

    def has_core_lumps(self) -> bool:
        return not self.missing_core_lump_names()

    def missing_core_lump_names(self) -> tuple[str, ...]:
        return tuple(name for name in CORE_MAP_LUMPS if name not in self.lumps)

    def ordered_lumps(self) -> tuple[Lump, ...]:
        return tuple(
            self.lumps[name]
            for name in KNOWN_MAP_LUMPS
            if name in self.lumps
        )


class WadFile:
    def __init__(self, header: WadHeader, lumps: list[Lump], data: bytes, source: str) -> None:
        self.header = header
        self.lumps = tuple(lumps)
        self._data = data
        self.source = source

    @classmethod
    def from_bytes(cls, data: bytes | bytearray | memoryview, *, source: str = "<memory>") -> "WadFile":
        return parse_wad(bytes(data), source=source)

    @classmethod
    def from_file(cls, path: str | Path) -> "WadFile":
        wad_path = Path(path)
        return parse_wad(wad_path.read_bytes(), source=str(wad_path))

    def lump_names(self) -> tuple[str, ...]:
        return tuple(lump.name for lump in self.lumps)

    def find_lump(self, name: str, *, start: int = 0) -> Lump | None:
        wanted = normalize_name(name)
        for lump in self.lumps[start:]:
            if normalize_name(lump.name) == wanted:
                return lump
        return None

    def find_lumps(self, name: str) -> tuple[Lump, ...]:
        wanted = normalize_name(name)
        return tuple(
            lump
            for lump in self.lumps
            if normalize_name(lump.name) == wanted
        )

    def read_lump(self, lump: str | Lump) -> bytes:
        if isinstance(lump, str):
            found = self.find_lump(lump)
            if found is None:
                raise KeyError(f"lump not found: {lump}")
            lump = found
        return self._data[lump.offset:lump.end_offset]

    def important_lumps(self) -> dict[str, Lump | None]:
        found: dict[str, Lump | None] = {
            name: self.find_lump(name)
            for name in COMMON_LUMPS
        }
        found["TITLE"] = self.find_title_lump()
        return found

    def find_title_lump(self) -> Lump | None:
        for name in TITLE_LUMP_CANDIDATES:
            lump = self.find_lump(name)
            if lump is not None:
                return lump
        return None

    def map_markers(self) -> tuple[Lump, ...]:
        return tuple(lump for lump in self.lumps if is_map_marker_name(lump.name))

    def maps(self) -> tuple[MapLumps, ...]:
        return tuple(self.map_lumps(marker.name) for marker in self.map_markers())

    def map_lumps(self, map_name: str) -> MapLumps:
        wanted = normalize_name(map_name)
        marker = None
        for lump in self.lumps:
            if normalize_name(lump.name) == wanted:
                marker = lump
                break

        if marker is None:
            raise KeyError(f"map marker not found: {map_name}")
        if not is_map_marker_name(marker.name):
            raise ValueError(f"lump is not a DOOM map marker: {map_name}")

        next_marker_index = len(self.lumps)
        for lump in self.lumps[marker.index + 1:]:
            if is_map_marker_name(lump.name):
                next_marker_index = lump.index
                break

        found: dict[str, Lump] = {}
        for lump in self.lumps[marker.index + 1:next_marker_index]:
            name = normalize_name(lump.name)
            if name in KNOWN_MAP_LUMPS and name not in found:
                found[name] = lump

        return MapLumps(marker=marker, lumps=found)


def normalize_name(name: str) -> str:
    return name.strip().upper()


def is_map_marker_name(name: str) -> bool:
    normalized = normalize_name(name)
    return bool(_EPISODE_MAP_RE.match(normalized) or _DOOM2_MAP_RE.match(normalized))


def parse_wad(data: bytes, *, source: str = "<memory>") -> WadFile:
    if len(data) < HEADER_SIZE:
        raise WadError("WAD is too small to contain a header")

    kind_bytes, lump_count, directory_offset = struct.unpack_from("<4sii", data, 0)
    try:
        kind = kind_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise WadError("WAD identifier is not ASCII") from exc

    if kind not in {"IWAD", "PWAD"}:
        raise WadError(f"unsupported WAD identifier: {kind!r}")
    if lump_count < 0:
        raise WadError(f"negative lump count: {lump_count}")
    if directory_offset < 0:
        raise WadError(f"negative directory offset: {directory_offset}")

    directory_size = lump_count * DIRECTORY_ENTRY_SIZE
    directory_end = directory_offset + directory_size
    if directory_end > len(data):
        raise WadError(
            f"directory extends past end of file: offset={directory_offset} "
            f"size={directory_size} file_size={len(data)}"
        )

    lumps = []
    for index in range(lump_count):
        entry_offset = directory_offset + index * DIRECTORY_ENTRY_SIZE
        file_offset, size, raw_name = struct.unpack_from("<ii8s", data, entry_offset)
        if file_offset < 0:
            raise WadError(f"lump {index} has a negative file offset")
        if size < 0:
            raise WadError(f"lump {index} has a negative size")
        if file_offset > len(data):
            raise WadError(f"lump {index} starts past end of file")
        if size and file_offset + size > len(data):
            raise WadError(f"lump {index} extends past end of file")

        lumps.append(
            Lump(
                index=index,
                name=decode_lump_name(raw_name, index),
                offset=file_offset,
                size=size,
                raw_name=raw_name,
            )
        )

    return WadFile(
        header=WadHeader(kind=kind, lump_count=lump_count, directory_offset=directory_offset),
        lumps=lumps,
        data=data,
        source=source,
    )


def decode_lump_name(raw_name: bytes, index: int) -> str:
    name_bytes = raw_name.split(b"\x00", 1)[0]
    try:
        return name_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise WadError(f"lump {index} name is not ASCII") from exc


def format_lump(lump: Lump) -> str:
    return f"#{lump.index:04d} {lump.name:<8} offset={lump.offset} size={lump.size}"


def summary_lines(wad: WadFile) -> Iterable[str]:
    yield f"WAD: {wad.source}"
    yield f"type: {wad.header.kind}"
    yield f"lumps: {wad.header.lump_count}"
    yield f"directory offset: {wad.header.directory_offset}"
    yield ""
    yield "important lumps:"
    for label, lump in wad.important_lumps().items():
        display = label
        if label == "TITLE" and lump is not None:
            display = f"TITLE ({lump.name})"
        if lump is None:
            yield f"  {display:<16} missing"
        else:
            yield f"  {display:<16} {format_lump(lump)}"

    maps = wad.maps()
    yield ""
    yield f"maps: {len(maps)}"
    if not maps:
        return

    for map_lumps in maps:
        yield f"  {format_lump(map_lumps.marker)}"
        for lump in map_lumps.ordered_lumps():
            yield f"    {format_lump(lump)}"
        missing = map_lumps.missing_core_lump_names()
        if missing:
            yield f"    missing core map lumps: {', '.join(missing)}"


def list_lines(wad: WadFile) -> Iterable[str]:
    for lump in wad.lumps:
        yield format_lump(lump)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect a DOOM WAD header and directory.")
    parser.add_argument("wad", type=Path, help="Path to an IWAD or PWAD file.")
    parser.add_argument("--summary", action="store_true", help="Print header, important lumps, and maps.")
    parser.add_argument("--list", action="store_true", help="List every lump in directory order.")
    parser.add_argument("--map", dest="map_name", help="Print important lumps for one map marker.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        wad = WadFile.from_file(args.wad)
        if args.map_name:
            map_lumps = wad.map_lumps(args.map_name)
            print(format_lump(map_lumps.marker))
            for lump in map_lumps.ordered_lumps():
                print(f"  {format_lump(lump)}")
            missing = map_lumps.missing_core_lump_names()
            if missing:
                print(f"  missing core map lumps: {', '.join(missing)}")
        elif args.list:
            for line in list_lines(wad):
                print(line)
        else:
            for line in summary_lines(wad):
                print(line)
    except (OSError, WadError, KeyError, ValueError) as exc:
        print(f"wad.py: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
