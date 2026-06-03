import os
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage07_wall_projection_debug as stage


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


class SourceStage07WallProjectionDebugTests(unittest.TestCase):
    def test_source_trace_covers_projection_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("render_fine_trig_tables", labels)
        self.assertIn("render_setup_frame_debug", labels)
        self.assertIn("render_fixed_div", labels)
        self.assertIn("render_point_to_dist", labels)
        self.assertIn("render_scale_from_global_angle", labels)
        self.assertIn("render_store_wall_range_projected_debug", labels)

    def test_finesine_and_finecosine_entries_match_chocolate_tables(self) -> None:
        self.assertEqual(len(stage.FINESINE), stage.FINEANGLES * 5 // 4)
        self.assertEqual(stage.FINESINE[0], 25)
        self.assertEqual(stage.FINESINE[1024], 46358)
        self.assertEqual(stage.FINESINE[2048], 65535)
        self.assertEqual(stage.FINESINE[4096], -25)
        self.assertEqual(stage.FINESINE[6144], -65535)
        self.assertEqual(stage.FINECOSINE[0], stage.FINESINE[stage.FINEANGLES // 4])
        self.assertEqual(stage.FINECOSINE[2048], stage.FINESINE[4096])

    def test_fixed_div_overflow_saturation_and_signed_division(self) -> None:
        self.assertEqual(stage.fixed_div(stage.FRACUNIT, 2 * stage.FRACUNIT), stage.FRACUNIT // 2)
        self.assertEqual(stage.fixed_div(-3 * stage.FRACUNIT, 2 * stage.FRACUNIT), -98304)
        self.assertEqual(stage.fixed_div(0x40000000, 1), 0x7FFFFFFF)
        self.assertEqual(stage.fixed_div(-0x40000000, 1), -0x80000000)
        self.assertEqual(stage.fixed_div(stage.FRACUNIT, 0), 0x7FFFFFFF)
        self.assertEqual(stage.fixed_div(-stage.FRACUNIT, 0), -0x80000000)

    def test_point_to_dist_synthetic_quadrants_and_near_origin(self) -> None:
        f = stage.FRACUNIT
        origin_x = stage.VIEW_X_FIXED
        origin_y = stage.VIEW_Y_FIXED

        east = stage.point_to_dist(origin_x + f, origin_y)
        west = stage.point_to_dist(origin_x - f, origin_y)
        north = stage.point_to_dist(origin_x, origin_y + f)
        south = stage.point_to_dist(origin_x, origin_y - f)
        diagonal = stage.point_to_dist(origin_x + f, origin_y + f)

        self.assertEqual((east, west, north, south), (65537, 65537, 65537, 65537))
        self.assertEqual(stage.point_to_dist(origin_x, origin_y), 0)
        self.assertEqual(stage.point_to_dist(origin_x + 1, origin_y + 1), 1)
        self.assertGreater(diagonal, east)

    def test_scale_from_global_angle_clamps_and_selected_angles(self) -> None:
        self.assertEqual(
            stage.scale_from_global_angle(0, 0, stage.FRACUNIT // 4),
            stage.MAXSCALE,
        )
        self.assertEqual(
            stage.scale_from_global_angle(0, stage.ANG90, 0x7FFFFFFF),
            stage.MINSCALE,
        )
        self.assertEqual(stage.scale_from_global_angle(0, stage.ANG90, stage.FRACUNIT), 4000)
        self.assertEqual(
            stage.scale_from_global_angle(stage.ANG90, 0, stage.FRACUNIT),
            stage.MAXSCALE,
        )

    def test_projection_record_layout_and_pinned_reference_stats(self) -> None:
        self.assertEqual(stage.PROJECTED_SPAN_X1, 0)
        self.assertEqual(stage.PROJECTED_SPAN_X2, 4)
        self.assertEqual(stage.PROJECTED_SPAN_SEG_INDEX, 8)
        self.assertEqual(stage.PROJECTED_SPAN_RW_NORMALANGLE, 12)
        self.assertEqual(stage.PROJECTED_SPAN_RW_DISTANCE, 16)
        self.assertEqual(stage.PROJECTED_SPAN_SCALE1, 20)
        self.assertEqual(stage.PROJECTED_SPAN_SCALE2, 24)
        self.assertEqual(stage.PROJECTED_SPAN_SCALESTEP, 28)
        self.assertEqual(stage.PROJECTED_SPAN_RECORD_SIZE, 32)
        self.assertEqual(stage.PROJECTED_SPAN_BUFFER_BYTES, stage.MAX_PROJECTED_SPANS * 32)

        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_wall_projection_for_pinned_map(PINNED_WAD)
        self.assertEqual(ref.viewz, 2686976)
        self.assertEqual((ref.viewcos, ref.viewsin, ref.validcount, ref.framecount), (65535, 25, 1, 1))
        self.assertEqual(
            (
                ref.clip.clip_visited_node_count,
                ref.clip.clip_visited_subsector_count,
                ref.clip.clip_visited_seg_count,
                ref.clip.clip_bbox_cull_count,
                ref.clip.backface_reject_count,
                ref.clip.off_frustum_reject_count,
                ref.clip.zero_pixel_reject_count,
                ref.clip.solid_classification_count,
                ref.clip.pass_classification_count,
                ref.clip.stored_span_count,
                ref.clip.final_solidseg_count,
            ),
            (72, 56, 205, 17, 82, 17, 5, 30, 70, 86, 1),
        )
        self.assertEqual(len(ref.projected_spans), 86)
        self.assertEqual(
            ref.first_projected_span,
            stage.ProjectedSpan(224, 255, 605, 0, 10485759, 65536, 65536, 0),
        )
        self.assertEqual(
            ref.last_projected_span,
            stage.ProjectedSpan(143, 165, 855, 0, 58720255, 11702, 11702, 0),
        )
        self.assertEqual((ref.min_distance, ref.max_distance), (2073560, 58720255))
        self.assertEqual((ref.min_scale, ref.max_scale), (11702, 108495))

    def test_executable_build_contains_projection_status_text_and_no_later_stage_strings(self) -> None:
        image = stage.build_source_stage07_wall_projection_debug_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage07_wall_projection_debug", image)
        self.assertIn(b"Wall projection debug OK", image)
        self.assertIn(b"R_PointToDist", image)
        self.assertIn(b"R_ScaleFromGlobalAngle", image)
        self.assertIn(b" PRJ=", image)
        self.assertIn(b" FPRJ=", image)
        self.assertNotIn(b"R_RenderSegLoop", image)
        self.assertNotIn(b"R_DrawColumn", image)
        self.assertNotIn(b"R_InitTextures", image)
        self.assertNotIn(b"source_stage08", image)
        self.assertNotIn(b"GCC:", image)
        self.assertNotIn(b"MinGW", image)
        self.assertNotIn(b"Microsoft Visual C", image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_expected_projection_counts_and_preserved_clip_counts(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_wall_projection_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage07_wall_projection_debug.exe"
        stage.write_source_stage07_wall_projection_debug_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid)
            self.assertIn(f"VN={ref.clip.visited_node_count}", title)
            self.assertIn(f"BVN={ref.clip.bbox_visited_node_count}", title)
            self.assertIn(f"CLN={ref.clip.clip_visited_node_count}", title)
            self.assertIn(f"CLSS={ref.clip.clip_visited_subsector_count}", title)
            self.assertIn(f"CLSEG={ref.clip.clip_visited_seg_count}", title)
            self.assertIn(f"SPAN={ref.clip.stored_span_count}", title)
            self.assertIn(f"FSPAN={ref.clip.first_span.start}-{ref.clip.first_span.stop}", title)
            self.assertIn(f"LSPAN={ref.clip.last_span.start}-{ref.clip.last_span.stop}", title)
            self.assertIn(f"VZ={ref.viewz}", title)
            self.assertIn(f"VCOS={ref.viewcos}", title)
            self.assertIn(f"VSIN={ref.viewsin}", title)
            self.assertIn(f"PRJ={len(ref.projected_spans)}", title)
            self.assertIn(f"MIND={ref.min_distance}", title)
            self.assertIn(f"MAXD={ref.max_distance}", title)
            self.assertIn(f"MINS={ref.min_scale}", title)
            self.assertIn(f"MAXS={ref.max_scale}", title)
            self.assertIn(
                f"FPRJ={ref.first_projected_span.x1}-{ref.first_projected_span.x2}",
                title,
            )
            self.assertIn(f"FPSEG={ref.first_projected_span.seg_index}", title)
            self.assertIn(
                f"LPRJ={ref.last_projected_span.x1}-{ref.last_projected_span.x2}",
                title,
            )
            self.assertIn(f"LPSEG={ref.last_projected_span.seg_index}", title)
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
