import os
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage02_bsp_setup as stage02
from tools import emit_source_stage03_bsp_walk_debug as stage
from tools.map_loader import load_map_from_file


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


class SourceStage03BspWalkDebugTests(unittest.TestCase):
    def test_source_trace_covers_bsp_walk_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("render_point_on_side", labels)
        self.assertIn("render_point_in_subsector", labels)
        self.assertIn("render_debug_subsector", labels)
        self.assertIn("render_bsp_node_debug", labels)

    def test_point_on_side_synthetic_fast_paths_and_general_case(self) -> None:
        unit = stage.FRACUNIT
        vertical_pos = (10 * unit, 0, 0, 64 * unit)
        vertical_neg = (10 * unit, 0, 0, -64 * unit)
        horizontal_pos = (0, 20 * unit, 64 * unit, 0)
        horizontal_neg = (0, 20 * unit, -64 * unit, 0)
        diagonal = (0, 0, 64 * unit, 64 * unit)

        self.assertEqual(stage.point_on_side_fixed(9 * unit, 0, vertical_pos), 1)
        self.assertEqual(stage.point_on_side_fixed(11 * unit, 0, vertical_pos), 0)
        self.assertEqual(stage.point_on_side_fixed(9 * unit, 0, vertical_neg), 0)
        self.assertEqual(stage.point_on_side_fixed(11 * unit, 0, vertical_neg), 1)

        self.assertEqual(stage.point_on_side_fixed(0, 19 * unit, horizontal_pos), 0)
        self.assertEqual(stage.point_on_side_fixed(0, 21 * unit, horizontal_pos), 1)
        self.assertEqual(stage.point_on_side_fixed(0, 19 * unit, horizontal_neg), 1)
        self.assertEqual(stage.point_on_side_fixed(0, 21 * unit, horizontal_neg), 0)

        self.assertEqual(stage.point_on_side_fixed(64 * unit, 0, diagonal), 0)
        self.assertEqual(stage.point_on_side_fixed(0, 64 * unit, diagonal), 1)

    def test_pinned_iwad_reference_traversal_matches_expected_counts(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_traversal_for_pinned_map(PINNED_WAD)

        self.assertEqual(
            (
                ref.vertex_count,
                ref.sector_count,
                ref.sidedef_count,
                ref.linedef_count,
                ref.subsector_count,
                ref.node_count,
                ref.seg_count,
            ),
            (1189, 211, 2041, 1274, 698, 697, 2233),
        )
        self.assertEqual(
            (
                ref.visited_node_count,
                ref.visited_subsector_count,
                ref.visited_seg_count,
                ref.max_depth,
                ref.first_subsector,
                ref.last_subsector,
                ref.view_subsector,
            ),
            (697, 698, 2233, 33, 227, 169, 227),
        )

    def test_fixed_viewpoint_constants_and_debug_state_offsets(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        loaded = load_map_from_file(PINNED_WAD, "MAP01")
        player_one = loaded.player_starts[0]

        self.assertEqual((player_one.x, player_one.y, player_one.angle), (-192, -192, 0))
        self.assertEqual(stage.VIEW_X_FIXED, player_one.x << stage.FRACBITS)
        self.assertEqual(stage.VIEW_Y_FIXED, player_one.y << stage.FRACBITS)
        self.assertEqual(stage.VIEW_ANGLE, 0)

        self.assertEqual(stage.TRAVERSAL_VISITED_NODE_COUNT, 0)
        self.assertEqual(stage.TRAVERSAL_VISITED_SUBSECTOR_COUNT, 4)
        self.assertEqual(stage.TRAVERSAL_VISITED_SEG_COUNT, 8)
        self.assertEqual(stage.TRAVERSAL_MAX_DEPTH, 12)
        self.assertEqual(stage.TRAVERSAL_FIRST_SUBSECTOR, 16)
        self.assertEqual(stage.TRAVERSAL_LAST_SUBSECTOR, 20)
        self.assertEqual(stage.TRAVERSAL_VIEW_SUBSECTOR, 24)
        self.assertEqual(stage.TRAVERSAL_DEBUG_STATE_BYTES, 28)
        self.assertEqual(stage.VISITED_SEG_INDICES_BYTES, stage02.MAX_SEGS * 4)

    def test_executable_build_contains_source_stage_status_text(self) -> None:
        image = stage.build_source_stage03_bsp_walk_debug_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage03_bsp_walk_debug", image)
        self.assertIn(b"R_RenderBSPNode visited nodes", image)
        self.assertIn(b"R_CheckBBox: accept-all debug boundary", image)
        self.assertIn(b" VN=", image)
        self.assertIn(b" FIRSTSS=", image)
        self.assertNotIn(b"GCC:", image)
        self.assertNotIn(b"MinGW", image)
        self.assertNotIn(b"Microsoft Visual C", image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_expected_traversal_counts_in_window_title(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_traversal_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage03_bsp_walk_debug.exe"
        stage.write_source_stage03_bsp_walk_debug_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid)
            self.assertIn(f"V={ref.vertex_count}", title)
            self.assertIn(f"SEC={ref.sector_count}", title)
            self.assertIn(f"SD={ref.sidedef_count}", title)
            self.assertIn(f"L={ref.linedef_count}", title)
            self.assertIn(f"SS={ref.subsector_count}", title)
            self.assertIn(f"N={ref.node_count}", title)
            self.assertIn(f"SG={ref.seg_count}", title)
            self.assertIn(f"VN={ref.visited_node_count}", title)
            self.assertIn(f"VSS={ref.visited_subsector_count}", title)
            self.assertIn(f"VSEG={ref.visited_seg_count}", title)
            self.assertIn(f"DEPTH={ref.max_depth}", title)
            self.assertIn(f"FIRSTSS={ref.first_subsector}", title)
            self.assertIn(f"LASTSS={ref.last_subsector}", title)
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
