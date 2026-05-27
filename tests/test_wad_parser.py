import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.wad import HEADER_SIZE, WadError, WadFile, is_map_marker_name, parse_wad


def lump_name(name: str) -> bytes:
    encoded = name.encode("ascii")
    if len(encoded) > 8:
        raise ValueError(f"lump name is too long: {name}")
    return encoded + b"\x00" * (8 - len(encoded))


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


def synthetic_wad() -> bytes:
    return build_wad(
        [
            ("PLAYPAL", bytes(range(256)) * 3),
            ("COLORMAP", b"\x00" * (34 * 256)),
            ("TITLEPIC", b"title"),
            ("MAP01", b""),
            ("THINGS", b"\x01" * 10),
            ("LINEDEFS", b"\x02" * 14),
            ("SIDEDEFS", b"\x03" * 30),
            ("VERTEXES", struct.pack("<hhhh", 0, 0, 64, 64)),
            ("SEGS", b"\x04" * 12),
            ("SSECTORS", b"\x05" * 4),
            ("NODES", b"\x06" * 28),
            ("SECTORS", b"\x07" * 26),
            ("REJECT", b""),
            ("BLOCKMAP", b"\x08" * 8),
        ]
    )


class WadParserTests(unittest.TestCase):
    def test_parse_header_directory_and_read_lumps(self) -> None:
        wad = WadFile.from_bytes(synthetic_wad(), source="tiny.wad")

        self.assertEqual(wad.header.kind, "IWAD")
        self.assertEqual(wad.header.lump_count, 14)
        self.assertEqual(wad.lump_names()[:4], ("PLAYPAL", "COLORMAP", "TITLEPIC", "MAP01"))

        playpal = wad.find_lump("playpal")
        self.assertIsNotNone(playpal)
        self.assertEqual(playpal.offset, HEADER_SIZE)
        self.assertEqual(playpal.size, 768)
        self.assertEqual(wad.read_lump("TITLEPIC"), b"title")

        important = wad.important_lumps()
        self.assertEqual(important["PLAYPAL"], playpal)
        self.assertEqual(important["TITLE"].name, "TITLEPIC")

    def test_locates_important_map_lumps(self) -> None:
        wad = parse_wad(synthetic_wad())

        maps = wad.maps()
        self.assertEqual([map_lumps.name for map_lumps in maps], ["MAP01"])

        map_lumps = wad.map_lumps("map01")
        self.assertTrue(map_lumps.has_core_lumps())
        self.assertEqual(map_lumps.missing_core_lump_names(), ())
        self.assertEqual(map_lumps.get("THINGS").size, 10)
        self.assertEqual(map_lumps.get("SECTORS").size, 26)
        self.assertEqual(
            [lump.name for lump in map_lumps.ordered_lumps()],
            [
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
            ],
        )

    def test_episode_and_doom2_map_marker_names_are_detected(self) -> None:
        self.assertTrue(is_map_marker_name("E1M1"))
        self.assertTrue(is_map_marker_name("e4m8"))
        self.assertTrue(is_map_marker_name("MAP01"))
        self.assertFalse(is_map_marker_name("MAP1"))
        self.assertFalse(is_map_marker_name("PLAYPAL"))

    def test_rejects_truncated_directory(self) -> None:
        broken = struct.pack("<4sii", b"IWAD", 1, HEADER_SIZE) + b"\x00" * 15

        with self.assertRaises(WadError):
            parse_wad(broken)

    def test_cli_summary_uses_synthetic_wad_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wad_path = Path(tmp) / "tiny.wad"
            wad_path.write_bytes(synthetic_wad())

            script = Path(__file__).resolve().parents[1] / "tools" / "wad.py"
            completed = subprocess.run(
                [sys.executable, str(script), str(wad_path), "--summary"],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("type: IWAD", completed.stdout)
        self.assertIn("PLAYPAL", completed.stdout)
        self.assertIn("MAP01", completed.stdout)
        self.assertIn("THINGS", completed.stdout)


if __name__ == "__main__":
    unittest.main()
