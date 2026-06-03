import os
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage02_bsp_setup as stage02
from tools import emit_source_stage04_bbox_visibility_debug as stage


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


def expected_fixed_mul(a: int, b: int) -> int:
    return stage._int32((stage._int32(a) * stage._int32(b)) >> stage.FRACBITS)


def expected_fixed_div(a: int, b: int) -> int:
    a = stage._int32(a)
    b = stage._int32(b)
    if (abs(a) >> 14) >= abs(b):
        return -0x80000000 if (a ^ b) < 0 else 0x7FFFFFFF
    sign = -1 if (a < 0) ^ (b < 0) else 1
    return stage._int32(sign * ((abs(a) << stage.FRACBITS) // abs(b)))


def expected_texture_mapping_tables() -> tuple[dict[int, int], dict[int, int], int]:
    viewangletox = [0] * (stage.FINEANGLES // 2)
    focallength = expected_fixed_div(
        stage.CENTERXFRAC,
        stage.FINETANGENT[stage.FINEANGLES // 4 + stage.FIELDOFVIEW // 2],
    )

    for i in range(stage.FINEANGLES // 2):
        tangent = stage.FINETANGENT[i]
        if tangent > stage.FRACUNIT * 2:
            t = -1
        elif tangent < -stage.FRACUNIT * 2:
            t = stage.VIEWWIDTH + 1
        else:
            t = expected_fixed_mul(tangent, focallength)
            t = (stage.CENTERXFRAC - t + stage.FRACUNIT - 1) >> stage.FRACBITS
            if t < -1:
                t = -1
            elif t > stage.VIEWWIDTH + 1:
                t = stage.VIEWWIDTH + 1
        viewangletox[i] = t

    xtoviewangle = [0] * (stage.VIEWWIDTH + 1)
    for x in range(stage.VIEWWIDTH + 1):
        i = 0
        while viewangletox[i] > x:
            i += 1
        xtoviewangle[x] = stage._uint32((i << stage.ANGLETOFINESHIFT) - stage.ANG90)

    for i in range(stage.FINEANGLES // 2):
        if viewangletox[i] == -1:
            viewangletox[i] = 0
        elif viewangletox[i] == stage.VIEWWIDTH + 1:
            viewangletox[i] = stage.VIEWWIDTH

    view_samples = {i: viewangletox[i] for i in (0, 1024, 2048, 3072, 4095)}
    x_samples = {i: xtoviewangle[i] for i in (0, 1, 159, 160, 319, 320)}
    return view_samples, x_samples, xtoviewangle[0]


class SourceStage04BBoxVisibilityDebugTests(unittest.TestCase):
    def test_source_trace_covers_bbox_visibility_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("render_slope_div", labels)
        self.assertIn("render_angle_tables", labels)
        self.assertIn("render_point_to_angle", labels)
        self.assertIn("render_init_texture_mapping_tables", labels)
        self.assertIn("render_clear_clipsegs", labels)
        self.assertIn("render_check_bbox", labels)

    def test_slope_div_threshold_normal_and_clamping_behavior(self) -> None:
        self.assertEqual(stage.slope_div(0, 0), stage.SLOPERANGE)
        self.assertEqual(stage.slope_div(1, 511), stage.SLOPERANGE)
        self.assertEqual(stage.slope_div(0, 512), 0)
        self.assertEqual(stage.slope_div(stage.FRACUNIT, stage.FRACUNIT * 2), 1024)
        self.assertEqual(stage.slope_div(stage.FRACUNIT, stage.FRACUNIT), stage.SLOPERANGE)
        self.assertEqual(stage.slope_div(stage.FRACUNIT * 8, stage.FRACUNIT), stage.SLOPERANGE)

    def test_point_to_angle_octants_and_unsigned_wraparound(self) -> None:
        unit = stage.FRACUNIT

        def world(dx: int, dy: int) -> tuple[int, int]:
            return stage.VIEW_X_FIXED + dx, stage.VIEW_Y_FIXED + dy

        shallow = stage.TANTOANGLE[stage.slope_div(unit, unit * 4)]
        steep = stage.TANTOANGLE[stage.slope_div(unit, unit * 4)]

        cases = (
            (world(unit * 4, unit), shallow),
            (world(unit, unit * 4), stage._uint32(stage.ANG90 - 1 - steep)),
            (world(-unit, unit * 4), stage._uint32(stage.ANG90 + steep)),
            (world(-unit * 4, unit), stage._uint32(stage.ANG180 - 1 - shallow)),
            (world(-unit * 4, -unit), stage._uint32(stage.ANG180 + shallow)),
            (world(-unit, -unit * 4), stage._uint32(stage.ANG270 - 1 - steep)),
            (world(unit, -unit * 4), stage._uint32(stage.ANG270 + steep)),
            (world(unit * 4, -unit), stage._uint32(-shallow)),
        )

        for (x, y), expected in cases:
            with self.subTest(x=x, y=y):
                self.assertEqual(stage.point_to_angle(x, y), expected)

        wrapped = stage.point_to_angle(*world(unit * 4, -unit))
        self.assertGreater(wrapped, stage.ANG270)
        self.assertEqual(stage.point_to_angle(*world(0, 0)), 0)

    def test_generated_texture_mapping_tables_match_source_algorithm_samples(self) -> None:
        expected_viewangletox, expected_xtoviewangle, expected_clipangle = (
            expected_texture_mapping_tables()
        )

        self.assertEqual(stage.CLIPANGLE, expected_clipangle)
        for index, expected in expected_viewangletox.items():
            self.assertEqual(stage.VIEWANGLETOX[index], expected)
        for index, expected in expected_xtoviewangle.items():
            self.assertEqual(stage.XTOVIEWANGLE[index], expected)

        self.assertEqual(stage.CLIPANGLE, stage.XTOVIEWANGLE[0])
        self.assertEqual(stage.VIEWANGLETOX[2048], stage.CENTERX)

    def test_check_bbox_synthetic_fast_accept_and_offscreen_rejection(self) -> None:
        unit = stage.FRACUNIT
        inside = [
            stage.VIEW_Y_FIXED + unit,
            stage.VIEW_Y_FIXED - unit,
            stage.VIEW_X_FIXED - unit,
            stage.VIEW_X_FIXED + unit,
        ]
        east_visible = [
            stage.VIEW_Y_FIXED + unit,
            stage.VIEW_Y_FIXED - unit,
            stage.VIEW_X_FIXED + unit * 4,
            stage.VIEW_X_FIXED + unit * 6,
        ]
        west_offscreen = [
            stage.VIEW_Y_FIXED + unit,
            stage.VIEW_Y_FIXED - unit,
            stage.VIEW_X_FIXED - unit * 6,
            stage.VIEW_X_FIXED - unit * 4,
        ]
        north_offscreen = [
            stage.VIEW_Y_FIXED + unit * 6,
            stage.VIEW_Y_FIXED + unit * 4,
            stage.VIEW_X_FIXED - unit,
            stage.VIEW_X_FIXED + unit,
        ]

        fully_closed = ((-0x7FFFFFFF, 0x7FFFFFFF),)
        self.assertTrue(stage.check_bbox(inside, solidsegs=fully_closed))
        self.assertTrue(stage.check_bbox(east_visible))
        self.assertFalse(stage.check_bbox(west_offscreen))
        self.assertFalse(stage.check_bbox(north_offscreen))

    def test_pinned_iwad_reference_bbox_visibility_matches_expected_counts(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_visibility_for_pinned_map(PINNED_WAD)

        self.assertEqual(
            (
                ref.visited_node_count,
                ref.visited_subsector_count,
                ref.visited_seg_count,
                ref.max_depth,
                ref.first_subsector,
                ref.last_subsector,
            ),
            (697, 698, 2233, 33, 227, 169),
        )
        self.assertEqual(
            (
                ref.bbox_visited_node_count,
                ref.bbox_visited_subsector_count,
                ref.bbox_visited_seg_count,
                ref.bbox_max_depth,
                ref.bbox_first_subsector,
                ref.bbox_last_subsector,
                ref.bbox_culled_node_count,
            ),
            (559, 513, 1709, 33, 227, 153, 47),
        )

    def test_stage04_debug_offsets_and_clipseg_layout(self) -> None:
        self.assertEqual(stage.TRAVERSAL_VISITED_NODE_COUNT, 0)
        self.assertEqual(stage.TRAVERSAL_VISITED_SUBSECTOR_COUNT, 4)
        self.assertEqual(stage.TRAVERSAL_VISITED_SEG_COUNT, 8)
        self.assertEqual(stage.TRAVERSAL_MAX_DEPTH, 12)
        self.assertEqual(stage.TRAVERSAL_FIRST_SUBSECTOR, 16)
        self.assertEqual(stage.TRAVERSAL_LAST_SUBSECTOR, 20)
        self.assertEqual(stage.TRAVERSAL_VIEW_SUBSECTOR, 24)
        self.assertEqual(stage.TRAVERSAL_DEBUG_STATE_BYTES, 28)

        self.assertEqual(stage.BBOX_TRAVERSAL_VISITED_NODE_COUNT, 0)
        self.assertEqual(stage.BBOX_TRAVERSAL_VISITED_SUBSECTOR_COUNT, 4)
        self.assertEqual(stage.BBOX_TRAVERSAL_VISITED_SEG_COUNT, 8)
        self.assertEqual(stage.BBOX_TRAVERSAL_MAX_DEPTH, 12)
        self.assertEqual(stage.BBOX_TRAVERSAL_FIRST_SUBSECTOR, 16)
        self.assertEqual(stage.BBOX_TRAVERSAL_LAST_SUBSECTOR, 20)
        self.assertEqual(stage.BBOX_TRAVERSAL_CULLED_NODE_COUNT, 24)
        self.assertEqual(stage.BBOX_TRAVERSAL_DEBUG_STATE_BYTES, 28)

        self.assertEqual(stage.CLIPRANGE_FIRST, 0)
        self.assertEqual(stage.CLIPRANGE_LAST, 4)
        self.assertEqual(stage.CLIPRANGE_RECORD_SIZE, 8)
        self.assertEqual(stage.MAX_SOLIDSEGS, stage.VIEWWIDTH // 2 + 1)
        self.assertEqual(stage.SOLIDSEGS_BYTES, stage.MAX_SOLIDSEGS * 8)
        self.assertEqual(stage.BBOX_VISIBLE_SEG_INDICES_BYTES, stage02.MAX_SEGS * 4)
        self.assertEqual(stage.clear_clipseg_sentinels(), ((-0x7FFFFFFF, -1), (320, 0x7FFFFFFF)))

    def test_executable_build_contains_source_stage_status_text(self) -> None:
        image = stage.build_source_stage04_bbox_visibility_debug_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage04_bbox_visibility_debug", image)
        self.assertIn(b"R_CheckBBox visible nodes", image)
        self.assertIn(b"R_ClearClipSegs sentinel solidsegs only", image)
        self.assertIn(b"render_angle_tables table-emitted", image)
        self.assertIn(b" BVN=", image)
        self.assertIn(b" CULL=", image)
        self.assertNotIn(b"R_ClipSolidWallSegment", image)
        self.assertNotIn(b"GCC:", image)
        self.assertNotIn(b"MinGW", image)
        self.assertNotIn(b"Microsoft Visual C", image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_expected_bbox_counts_in_window_title(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_visibility_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage04_bbox_visibility_debug.exe"
        stage.write_source_stage04_bbox_visibility_debug_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid)
            self.assertIn(f"VN={ref.visited_node_count}", title)
            self.assertIn(f"VSS={ref.visited_subsector_count}", title)
            self.assertIn(f"VSEG={ref.visited_seg_count}", title)
            self.assertIn(f"BVN={ref.bbox_visited_node_count}", title)
            self.assertIn(f"BVSS={ref.bbox_visited_subsector_count}", title)
            self.assertIn(f"BVSEG={ref.bbox_visited_seg_count}", title)
            self.assertIn(f"BDEPTH={ref.bbox_max_depth}", title)
            self.assertIn(f"BFIRSTSS={ref.bbox_first_subsector}", title)
            self.assertIn(f"BLASTSS={ref.bbox_last_subsector}", title)
            self.assertIn(f"CULL={ref.bbox_culled_node_count}", title)
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
