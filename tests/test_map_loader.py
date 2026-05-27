import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.map_loader import (
    NO_SIDEDEF,
    LineDef,
    MapFormatError,
    Sector,
    SideDef,
    Thing,
    Vertex,
    load_map,
    parse_linedefs,
    parse_sectors,
    parse_sidedefs,
    parse_things,
    parse_vertices,
    summary_lines,
)
from tools.wad import HEADER_SIZE, WadFile


def lump_name(name: str) -> bytes:
    encoded = name.encode("ascii")
    if len(encoded) > 8:
        raise ValueError(f"lump name is too long: {name}")
    return encoded + b"\x00" * (8 - len(encoded))


def fixed_name(name: str) -> bytes:
    return lump_name(name)


def build_wad(lumps: list[tuple[str, bytes]], *, kind: bytes = b"IWAD") -> bytes:
    lump_data = bytearray()
    directory_entries = []

    for name, payload in lumps:
        offset = HEADER_SIZE + len(lump_data)
        lump_data.extend(payload)
        directory_entries.append((offset, len(payload), lump_name(name)))

    directory_offset = HEADER_SIZE + len(lump_data)
    directory = bytearray()
    for offset, size, name in directory_entries:
        directory.extend(struct.pack("<ii8s", offset, size, name))

    header = struct.pack("<4sii", kind, len(lumps), directory_offset)
    return header + lump_data + directory


def synthetic_map_lumps(marker: str = "MAP01") -> list[tuple[str, bytes]]:
    things = b"".join(
        [
            struct.pack("<hhHHH", 64, 96, 90, 1, 0x0007),
            struct.pack("<hhHHH", -32, 48, 0, 3004, 0x0001),
        ]
    )
    linedefs = b"".join(
        [
            struct.pack("<HHHHHHH", 0, 1, 0x0001, 0, 0, 0, NO_SIDEDEF),
            struct.pack("<HHHHHHH", 1, 2, 0x0004, 11, 3, 0, 1),
        ]
    )
    sidedefs = b"".join(
        [
            struct.pack("<hh8s8s8sH", 0, 8, fixed_name("-"), fixed_name("-"), fixed_name("STARTAN3"), 0),
            struct.pack("<hh8s8s8sH", -16, 0, fixed_name("STONE2"), fixed_name("-"), fixed_name("-"), 1),
        ]
    )
    vertices = b"".join(
        [
            struct.pack("<hh", 0, 0),
            struct.pack("<hh", 128, 0),
            struct.pack("<hh", 128, 96),
        ]
    )
    sectors = b"".join(
        [
            struct.pack("<hh8s8shHH", 0, 128, fixed_name("FLOOR0_1"), fixed_name("CEIL1_1"), 160, 0, 0),
            struct.pack("<hh8s8shHH", -24, 192, fixed_name("NUKAGE1"), fixed_name("F_SKY1"), 96, 5, 3),
        ]
    )
    return [
        (marker, b""),
        ("THINGS", things),
        ("LINEDEFS", linedefs),
        ("SIDEDEFS", sidedefs),
        ("VERTEXES", vertices),
        ("SECTORS", sectors),
        ("REJECT", b""),
        ("BLOCKMAP", b""),
    ]


def synthetic_map_wad(marker: str = "MAP01") -> bytes:
    return build_wad(synthetic_map_lumps(marker))


class MapLoaderTests(unittest.TestCase):
    def test_parses_core_binary_lump_records(self) -> None:
        self.assertEqual(parse_vertices(struct.pack("<hhhh", -128, 64, 256, -512)), (
            Vertex(-128, 64),
            Vertex(256, -512),
        ))
        self.assertEqual(parse_things(struct.pack("<hhHHH", 64, 96, 90, 1, 7)), (
            Thing(64, 96, 90, 1, 7),
        ))
        self.assertEqual(parse_linedefs(struct.pack("<HHHHHHH", 0, 1, 4, 11, 3, 2, NO_SIDEDEF)), (
            LineDef(0, 1, 4, 11, 3, 2, NO_SIDEDEF),
        ))
        self.assertEqual(
            parse_sidedefs(struct.pack("<hh8s8s8sH", -16, 8, fixed_name("UP"), fixed_name("-"), fixed_name("MID"), 2)),
            (SideDef(-16, 8, "UP", "-", "MID", 2),),
        )
        self.assertEqual(
            parse_sectors(struct.pack("<hh8s8shHH", -24, 128, fixed_name("FLOOR"), fixed_name("CEIL"), 160, 5, 9)),
            (Sector(-24, 128, "FLOOR", "CEIL", 160, 5, 9),),
        )

    def test_loads_map_from_wad_and_summarizes_it(self) -> None:
        wad = WadFile.from_bytes(synthetic_map_wad(), source="tiny-map.wad")

        loaded = load_map(wad, map_name="map01")

        self.assertEqual(loaded.name, "MAP01")
        self.assertEqual(len(loaded.vertices), 3)
        self.assertEqual(len(loaded.linedefs), 2)
        self.assertEqual(len(loaded.sidedefs), 2)
        self.assertEqual(len(loaded.sectors), 2)
        self.assertEqual(len(loaded.things), 2)
        self.assertEqual(loaded.bounds, (0, 0, 128, 96))
        self.assertEqual(loaded.one_sided_linedef_count, 1)
        self.assertEqual(loaded.two_sided_linedef_count, 1)
        self.assertEqual(loaded.player_starts, (Thing(64, 96, 90, 1, 0x0007),))

        summary = "\n".join(summary_lines(loaded))
        self.assertIn("map: MAP01", summary)
        self.assertIn("linedefs: 2 (one-sided: 1, two-sided: 1)", summary)
        self.assertIn("bounds: x=0..128 y=0..96 size=128x96", summary)
        self.assertIn("type=1 at (64, 96) angle=90 flags=0x0007", summary)
        self.assertIn("sector heights: floor=-24..0 ceiling=128..192", summary)

    def test_default_map_selection_handles_doom1_style_markers(self) -> None:
        wad = WadFile.from_bytes(synthetic_map_wad("E1M1"), source="tiny-e1m1.wad")

        loaded = load_map(wad)

        self.assertEqual(loaded.name, "E1M1")

    def test_rejects_unaligned_core_lump_data(self) -> None:
        with self.assertRaisesRegex(MapFormatError, "VERTEXES lump size"):
            parse_vertices(b"\x00")

    def test_missing_required_lump_is_reported(self) -> None:
        wad = WadFile.from_bytes(build_wad(synthetic_map_lumps()[:-3]), source="missing-sector.wad")

        with self.assertRaisesRegex(MapFormatError, "SECTORS"):
            load_map(wad, map_name="MAP01")

    def test_cli_summary_uses_synthetic_wad_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wad_path = Path(tmp) / "tiny-map.wad"
            wad_path.write_bytes(synthetic_map_wad())

            script = Path(__file__).resolve().parents[1] / "tools" / "map_loader.py"
            completed = subprocess.run(
                [sys.executable, str(script), str(wad_path), "--map", "MAP01"],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("map: MAP01", completed.stdout)
        self.assertIn("vertices: 3", completed.stdout)
        self.assertIn("things: 2", completed.stdout)
        self.assertIn("player starts:", completed.stdout)


if __name__ == "__main__":
    unittest.main()
