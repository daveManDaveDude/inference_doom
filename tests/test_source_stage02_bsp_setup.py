import os
import struct
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage02_bsp_setup as stage
from tools.map_loader import load_map_from_file
from tools.wad import WadFile


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


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


class SourceStage02BspSetupTests(unittest.TestCase):
    def test_source_trace_covers_bsp_setup_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("map_load_subsectors", labels)
        self.assertIn("map_load_nodes", labels)
        self.assertIn("map_load_segs", labels)
        self.assertIn("map_group_lines", labels)

    def test_layout_constants_match_classic_bsp_map_records(self) -> None:
        self.assertEqual(stage.MAPSEG_RECORD_SIZE, struct.calcsize("<hhhhhh"))
        self.assertEqual(stage.MAPSUBSECTOR_RECORD_SIZE, struct.calcsize("<hh"))
        self.assertEqual(stage.MAPNODE_RECORD_SIZE, struct.calcsize("<hhhhhhhhhhhhHH"))

    def test_runtime_layout_offsets_for_bsp_structures(self) -> None:
        self.assertEqual(stage.SUBSECTOR_T_RECORD_SIZE, 8)
        self.assertEqual(stage.SUBSECTOR_SECTOR, 0)
        self.assertEqual(stage.SUBSECTOR_NUMLINES, 4)
        self.assertEqual(stage.SUBSECTOR_FIRSTLINE, 6)

        self.assertEqual(stage.NODE_T_RECORD_SIZE, 52)
        self.assertEqual(stage.NODE_X, 0)
        self.assertEqual(stage.NODE_Y, 4)
        self.assertEqual(stage.NODE_DX, 8)
        self.assertEqual(stage.NODE_DY, 12)
        self.assertEqual(stage.NODE_BBOX, 16)
        self.assertEqual(stage.NODE_CHILD0, 48)
        self.assertEqual(stage.NODE_CHILD1, 50)

        self.assertEqual(stage.SEG_T_RECORD_SIZE, 32)
        self.assertEqual(stage.SEG_V1, 0)
        self.assertEqual(stage.SEG_V2, 4)
        self.assertEqual(stage.SEG_OFFSET, 8)
        self.assertEqual(stage.SEG_ANGLE, 12)
        self.assertEqual(stage.SEG_SIDEDEF, 16)
        self.assertEqual(stage.SEG_LINEDEF, 20)
        self.assertEqual(stage.SEG_FRONTSECTOR, 24)
        self.assertEqual(stage.SEG_BACKSECTOR, 28)

    def test_synthetic_bsp_records_validate_counts(self) -> None:
        subsectors = struct.pack("<hhhh", 4, 0, 2, 4)
        segs = struct.pack("<hhhhhh", 1, 2, -16384, 7, 1, 64)
        node = struct.pack(
            "<hhhhhhhhhhhhHH",
            10,
            -20,
            30,
            -40,
            1,
            2,
            3,
            4,
            -5,
            -6,
            -7,
            -8,
            0x8000,
            3,
        )

        self.assertEqual(stage.checked_record_count(len(subsectors), stage.MAPSUBSECTOR_RECORD_SIZE), 2)
        self.assertEqual(stage.checked_record_count(len(segs), stage.MAPSEG_RECORD_SIZE), 1)
        self.assertEqual(stage.checked_record_count(len(node), stage.MAPNODE_RECORD_SIZE), 1)
        self.assertEqual(stage.parse_mapsubsectors(subsectors)[0], (4, 0))
        self.assertEqual(stage.parse_mapsegs(segs)[0], (1, 2, -16384, 7, 1, 64))
        self.assertEqual(stage.parse_mapnodes(node)[0][-2:], (0x8000, 3))

        with self.assertRaisesRegex(ValueError, "not aligned"):
            stage.checked_record_count(len(node) + 1, stage.MAPNODE_RECORD_SIZE)

    def test_pinned_iwad_bsp_counts_fit_buffers_and_match_reference(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        wad = WadFile.from_file(PINNED_WAD)
        loaded = load_map_from_file(PINNED_WAD, "MAP01")
        map_lumps = wad.map_lumps("MAP01")

        subsectors = stage.parse_mapsubsectors(wad.read_lump(map_lumps.get("SSECTORS")))
        nodes = stage.parse_mapnodes(wad.read_lump(map_lumps.get("NODES")))
        segs = stage.parse_mapsegs(wad.read_lump(map_lumps.get("SEGS")))
        line_counts = stage.sector_line_counts_for_loaded_map(loaded)

        self.assertEqual(len(subsectors), map_lumps.get("SSECTORS").size // stage.MAPSUBSECTOR_RECORD_SIZE)
        self.assertEqual(len(nodes), map_lumps.get("NODES").size // stage.MAPNODE_RECORD_SIZE)
        self.assertEqual(len(segs), map_lumps.get("SEGS").size // stage.MAPSEG_RECORD_SIZE)
        self.assertLessEqual(len(subsectors), stage.MAX_SUBSECTORS)
        self.assertLessEqual(len(nodes), stage.MAX_NODES)
        self.assertLessEqual(len(segs), stage.MAX_SEGS)
        self.assertLessEqual(sum(line_counts), stage.MAX_SECTOR_LINE_REFS)

        first_subsector = subsectors[0]
        first_subsector_seg = segs[first_subsector[1]]
        first_subsector_line = loaded.linedefs[first_subsector_seg[3]]
        first_subsector_sidedef = (
            first_subsector_line.right_sidedef
            if first_subsector_seg[4] == 0
            else first_subsector_line.left_sidedef
        )

        self.assertEqual(first_subsector, (4, 0))
        self.assertEqual(segs[0][:5], (726, 56, -16384, 271, 0))
        self.assertEqual(loaded.sidedefs[first_subsector_sidedef].sector, 108)
        self.assertEqual(len(nodes) - 1, 696)
        self.assertEqual((sum(line_counts), min(line_counts), max(line_counts), line_counts[0]), (2036, 3, 81, 16))

    def test_executable_build_contains_source_stage_status_text(self) -> None:
        image = stage.build_source_stage02_bsp_setup_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage02_bsp_setup", image)
        self.assertIn(b"P_LoadSubsectors count", image)
        self.assertIn(b"P_LoadSegs count", image)
        self.assertIn(b'requestedExecutionLevel level="asInvoker"', image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_expected_bsp_counts_in_window_title(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        loaded = load_map_from_file(PINNED_WAD, "MAP01")
        wad = WadFile.from_file(PINNED_WAD)
        map_lumps = wad.map_lumps("MAP01")
        subsectors = stage.parse_mapsubsectors(wad.read_lump(map_lumps.get("SSECTORS")))
        nodes = stage.parse_mapnodes(wad.read_lump(map_lumps.get("NODES")))
        segs = stage.parse_mapsegs(wad.read_lump(map_lumps.get("SEGS")))
        line_counts = stage.sector_line_counts_for_loaded_map(loaded)
        exe_path = REPO_ROOT / "build" / "source_stage02_bsp_setup.exe"
        stage.write_source_stage02_bsp_setup_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid)
            self.assertIn(f"V={len(loaded.vertices)}", title)
            self.assertIn(f"L={len(loaded.linedefs)}", title)
            self.assertIn(f"SD={len(loaded.sidedefs)}", title)
            self.assertIn(f"SEC={len(loaded.sectors)}", title)
            self.assertIn(f"SS={len(subsectors)}", title)
            self.assertIn(f"N={len(nodes)}", title)
            self.assertIn(f"SG={len(segs)}", title)
            self.assertIn(f"ROOT={len(nodes) - 1}", title)
            self.assertIn(f"G={min(line_counts)}..{max(line_counts)}", title)
            self.assertIn(f"F0={line_counts[0]}", title)
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
