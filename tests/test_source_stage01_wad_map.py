import os
import struct
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage01_wad_map as stage
from tools.map_loader import load_map_from_file
from tools.wad import WadFile


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


def fixed_name(name: str) -> bytes:
    encoded = name.encode("ascii")
    return encoded + b"\x00" * (8 - len(encoded))


def window_title_for_pid(pid: int, timeout_seconds: float = 5.0) -> tuple[int, str]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        found: list[tuple[int, str]] = []

        @enum_proc_type
        def enum_proc(hwnd, _lparam):
            process_id = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            if process_id.value != pid or not user32.IsWindowVisible(hwnd):
                return True

            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, len(buffer))
            if buffer.value:
                found.append((int(hwnd), buffer.value))
                return False
            return True

        user32.EnumWindows(enum_proc, 0)
        if found:
            return found[0]
        time.sleep(0.1)

    raise TimeoutError(f"no visible window title found for pid {pid}")


class SourceStage01WadMapTests(unittest.TestCase):
    def test_source_trace_covers_first_slice_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertEqual(
            labels,
            {
                "wad_num_lumps",
                "wad_check_num_for_name",
                "wad_get_num_for_name",
                "wad_lump_length",
                "wad_read_lump",
                "map_load_vertexes",
                "map_load_sectors",
                "map_load_sidedefs",
                "map_load_linedefs",
            },
        )

    def test_layout_constants_match_classic_map_records(self) -> None:
        self.assertEqual(stage.MAPVERTEX_RECORD_SIZE, struct.calcsize("<hh"))
        self.assertEqual(stage.MAPSECTOR_RECORD_SIZE, struct.calcsize("<hh8s8shHH"))
        self.assertEqual(stage.MAPSIDEDEF_RECORD_SIZE, struct.calcsize("<hh8s8s8sH"))
        self.assertEqual(stage.MAPLINEDEF_RECORD_SIZE, struct.calcsize("<HHHHHHH"))

        self.assertEqual(stage.VERTEX_T_RECORD_SIZE, 8)
        self.assertEqual(stage.SECTOR_T_RECORD_SIZE, 36)
        self.assertEqual(stage.SIDE_T_RECORD_SIZE, 40)
        self.assertEqual(stage.LINE_T_RECORD_SIZE, 64)
        self.assertEqual(stage.LINE_DX, 8)
        self.assertEqual(stage.LINE_DY, 12)
        self.assertEqual(stage.LINE_BBOX_TOP, 28)
        self.assertEqual(stage.LINE_BBOX_BOTTOM, 32)
        self.assertEqual(stage.LINE_BBOX_LEFT, 36)
        self.assertEqual(stage.LINE_BBOX_RIGHT, 40)

    def test_synthetic_records_validate_counts_and_source_conversions(self) -> None:
        vertices = struct.pack("<hhhh", -128, 64, 256, -512)
        sectors = struct.pack(
            "<hh8s8shHH",
            -24,
            128,
            fixed_name("FLOOR"),
            fixed_name("CEIL"),
            160,
            5,
            9,
        )
        sidedefs = struct.pack(
            "<hh8s8s8sH",
            -16,
            8,
            fixed_name("UP"),
            fixed_name("-"),
            fixed_name("MID"),
            2,
        )
        linedefs = struct.pack("<HHHHHHH", 0, 1, 4, 11, 3, 2, 0xFFFF)

        self.assertEqual(stage.checked_record_count(len(vertices), stage.MAPVERTEX_RECORD_SIZE), 2)
        self.assertEqual(stage.checked_record_count(len(sectors), stage.MAPSECTOR_RECORD_SIZE), 1)
        self.assertEqual(stage.checked_record_count(len(sidedefs), stage.MAPSIDEDEF_RECORD_SIZE), 1)
        self.assertEqual(stage.checked_record_count(len(linedefs), stage.MAPLINEDEF_RECORD_SIZE), 1)
        self.assertEqual(-128 << 16, -8388608)
        self.assertEqual(128 << 16, 8388608)

        with self.assertRaisesRegex(ValueError, "not aligned"):
            stage.checked_record_count(len(linedefs) + 1, stage.MAPLINEDEF_RECORD_SIZE)

    def test_pinned_iwad_map_counts_fit_emitted_buffers(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        wad = WadFile.from_file(PINNED_WAD)
        loaded = load_map_from_file(PINNED_WAD, "MAP01")
        map_lumps = wad.map_lumps("MAP01")

        self.assertEqual(
            stage.checked_record_count(map_lumps.get("VERTEXES").size, stage.MAPVERTEX_RECORD_SIZE),
            len(loaded.vertices),
        )
        self.assertEqual(
            stage.checked_record_count(map_lumps.get("SECTORS").size, stage.MAPSECTOR_RECORD_SIZE),
            len(loaded.sectors),
        )
        self.assertEqual(
            stage.checked_record_count(map_lumps.get("SIDEDEFS").size, stage.MAPSIDEDEF_RECORD_SIZE),
            len(loaded.sidedefs),
        )
        self.assertEqual(
            stage.checked_record_count(map_lumps.get("LINEDEFS").size, stage.MAPLINEDEF_RECORD_SIZE),
            len(loaded.linedefs),
        )

        self.assertLessEqual(len(loaded.vertices), stage.MAX_VERTEXES)
        self.assertLessEqual(len(loaded.sectors), stage.MAX_SECTORS)
        self.assertLessEqual(len(loaded.sidedefs), stage.MAX_SIDEDEFS)
        self.assertLessEqual(len(loaded.linedefs), stage.MAX_LINEDEFS)

    def test_executable_build_contains_source_stage_status_text(self) -> None:
        image = stage.build_source_stage01_wad_map_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage01_wad_map", image)
        self.assertIn(b"P_LoadLineDefs count", image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_expected_map_counts_in_window_title(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        loaded = load_map_from_file(PINNED_WAD, "MAP01")
        exe_path = REPO_ROOT / "build" / "source_stage01_wad_map.exe"
        stage.write_source_stage01_wad_map_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid)
            self.assertIn(f"V={len(loaded.vertices)}", title)
            self.assertIn(f"L={len(loaded.linedefs)}", title)
            self.assertIn(f"SD={len(loaded.sidedefs)}", title)
            self.assertIn(f"SEC={len(loaded.sectors)}", title)
        finally:
            if hwnd:
                import ctypes

                ctypes.WinDLL("user32", use_last_error=True).PostMessageW(hwnd, 0x0010, 0, 0)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=3)


if __name__ == "__main__":
    unittest.main()
