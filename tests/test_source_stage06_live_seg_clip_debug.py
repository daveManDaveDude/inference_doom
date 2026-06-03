import os
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage06_live_seg_clip_debug as stage


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


class SourceStage06LiveSegClipDebugTests(unittest.TestCase):
    def test_source_trace_covers_live_seg_clip_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("render_bsp_node_clip_debug", labels)
        self.assertIn("render_debug_subsector_clip", labels)
        self.assertIn("render_add_line_debug", labels)
        self.assertIn("render_clip_solid_wall_segment", labels)
        self.assertIn("render_clip_pass_wall_segment", labels)
        self.assertIn("render_store_wall_range_debug", labels)

    def test_live_debug_buffer_offsets_and_reference_span_anchors(self) -> None:
        self.assertEqual(stage.DEBUG_SPAN_START, 0)
        self.assertEqual(stage.DEBUG_SPAN_STOP, 4)
        self.assertEqual(stage.DEBUG_SPAN_REASON, 8)
        self.assertEqual(stage.DEBUG_SPAN_SEG_INDEX, 12)
        self.assertEqual(stage.DEBUG_SPAN_RECORD_SIZE, 16)
        self.assertEqual(stage.DEBUG_SPAN_BUFFER_BYTES, stage.MAX_DEBUG_SPANS * 16)

        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_seg_clip_for_pinned_map(PINNED_WAD)
        self.assertEqual(ref.first_span, stage.DebugSpan(224, 255, stage.SPAN_REASON_SOLID, 605))
        self.assertEqual(ref.last_span, stage.DebugSpan(143, 165, stage.SPAN_REASON_SOLID, 855))

    def test_pinned_iwad_reference_clip_oracle_still_matches_stage05_counts(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_seg_clip_for_pinned_map(PINNED_WAD)

        self.assertEqual(
            (
                ref.visited_node_count,
                ref.visited_subsector_count,
                ref.visited_seg_count,
                ref.bbox_visited_node_count,
                ref.bbox_visited_subsector_count,
                ref.bbox_visited_seg_count,
                ref.bbox_culled_node_count,
            ),
            (697, 698, 2233, 559, 513, 1709, 47),
        )
        self.assertEqual(
            (
                ref.clip_visited_node_count,
                ref.clip_visited_subsector_count,
                ref.clip_visited_seg_count,
                ref.clip_bbox_cull_count,
                ref.backface_reject_count,
                ref.off_frustum_reject_count,
                ref.zero_pixel_reject_count,
                ref.solid_classification_count,
                ref.pass_classification_count,
                ref.empty_line_reject_count,
                ref.stored_span_count,
                ref.final_solidseg_count,
            ),
            (72, 56, 205, 17, 82, 17, 5, 30, 70, 1, 86, 1),
        )

    def test_executable_build_contains_live_status_text_and_no_projection_stage_strings(self) -> None:
        image = stage.build_source_stage06_live_seg_clip_debug_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage06_live_seg_clip_debug", image)
        self.assertIn(b"Live mutable seg clipping debug OK", image)
        self.assertIn(b"Mutable R_AddLine", image)
        self.assertIn(b"R_ClipSolidWallSegment", image)
        self.assertIn(b"R_ClipPassWallSegment", image)
        self.assertIn(b" FSPAN=", image)
        self.assertIn(b" LSEG=", image)
        self.assertNotIn(b"source_stage05_apply_pinned_clip_reference", image)
        self.assertNotIn(b"R_PointToDist", image)
        self.assertNotIn(b"R_ScaleFromGlobalAngle", image)
        self.assertNotIn(b"R_RenderSegLoop", image)
        self.assertNotIn(b"R_DrawColumn", image)
        self.assertNotIn(b"source_stage07", image)
        self.assertNotIn(b"GCC:", image)
        self.assertNotIn(b"MinGW", image)
        self.assertNotIn(b"Microsoft Visual C", image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_expected_live_clip_counts_and_span_anchors(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_seg_clip_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage06_live_seg_clip_debug.exe"
        stage.write_source_stage06_live_seg_clip_debug_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid)
            self.assertIn(f"VN={ref.visited_node_count}", title)
            self.assertIn(f"BVN={ref.bbox_visited_node_count}", title)
            self.assertIn(f"BVSEG={ref.bbox_visited_seg_count}", title)
            self.assertIn(f"CLN={ref.clip_visited_node_count}", title)
            self.assertIn(f"CLSS={ref.clip_visited_subsector_count}", title)
            self.assertIn(f"CLSEG={ref.clip_visited_seg_count}", title)
            self.assertIn(f"CLCULL={ref.clip_bbox_cull_count}", title)
            self.assertIn(f"BF={ref.backface_reject_count}", title)
            self.assertIn(f"OFF={ref.off_frustum_reject_count}", title)
            self.assertIn(f"ZPX={ref.zero_pixel_reject_count}", title)
            self.assertIn(f"SOL={ref.solid_classification_count}", title)
            self.assertIn(f"PASS={ref.pass_classification_count}", title)
            self.assertIn(f"SPAN={ref.stored_span_count}", title)
            self.assertIn(f"NSEGS={ref.final_solidseg_count}", title)
            self.assertIn(f"FSPAN={ref.first_span.start}-{ref.first_span.stop}", title)
            self.assertIn(f"FSEG={ref.first_span.seg_index}", title)
            self.assertIn(f"LSPAN={ref.last_span.start}-{ref.last_span.stop}", title)
            self.assertIn(f"LSEG={ref.last_span.seg_index}", title)
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
