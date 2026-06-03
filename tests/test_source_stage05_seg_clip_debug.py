import os
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage04_bbox_visibility_debug as stage04
from tools import emit_source_stage05_seg_clip_debug as stage
from tools.map_loader import Vertex


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


def world_vertex(dx: int, dy: int) -> Vertex:
    return Vertex(stage.stage03.VIEW_X_MAP_UNITS + dx, stage.stage03.VIEW_Y_MAP_UNITS + dy)


class SourceStage05SegClipDebugTests(unittest.TestCase):
    def test_source_trace_covers_seg_clip_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("render_debug_subsector_clip", labels)
        self.assertIn("render_add_line_debug", labels)
        self.assertIn("render_clip_solid_wall_segment", labels)
        self.assertIn("render_clip_pass_wall_segment", labels)
        self.assertIn("render_store_wall_range_debug", labels)

    def test_add_line_angle_clipping_and_x_span_mapping_with_synthetic_segs(self) -> None:
        front = stage.DebugSector(0, 128, "FLOOR", "CEIL", 160)
        back = stage.DebugSector(0, 64, "LOWER", "CEIL", 160)
        sectors = [front, back]
        sidedefs = [stage.DebugSideDef("MID", 0), stage.DebugSideDef("MID", 1)]
        solid_line = stage.DebugLineDef(0, 0)
        pass_line = stage.DebugLineDef(stage.ML_TWOSIDED, 0, 1)
        vertices = [
            world_vertex(4, 1),
            world_vertex(4, -1),
            world_vertex(4, -1),
            world_vertex(4, 1),
            world_vertex(-1, 8),
            world_vertex(1, 8),
            world_vertex(1000, 2),
            world_vertex(1000, 1),
        ]

        visible = stage.SegClipDebugState()
        span = stage.debug_add_line(
            visible,
            stage.DebugSeg(0, 1, 0),
            vertices,
            [solid_line, pass_line],
            sidedefs,
            sectors,
            frontsector_index=0,
            seg_index=7,
        )
        self.assertEqual(span, (121, 199))
        self.assertEqual(visible.solid_classification_count, 1)
        self.assertEqual(visible.spans[0], stage.DebugSpan(121, 199, stage.SPAN_REASON_SOLID, 7))

        backface = stage.SegClipDebugState()
        self.assertIsNone(
            stage.debug_add_line(
                backface,
                stage.DebugSeg(2, 3, 0),
                vertices,
                [solid_line],
                sidedefs,
                sectors,
                frontsector_index=0,
                seg_index=8,
            )
        )
        self.assertEqual(backface.backface_reject_count, 1)

        offscreen = stage.SegClipDebugState()
        self.assertIsNone(
            stage.debug_add_line(
                offscreen,
                stage.DebugSeg(4, 5, 0),
                vertices,
                [solid_line],
                sidedefs,
                sectors,
                frontsector_index=0,
                seg_index=9,
            )
        )
        self.assertEqual(offscreen.off_frustum_reject_count, 1)

        zero = stage.SegClipDebugState()
        self.assertIsNone(
            stage.debug_add_line(
                zero,
                stage.DebugSeg(6, 7, 0),
                vertices,
                [solid_line],
                sidedefs,
                sectors,
                frontsector_index=0,
                seg_index=10,
            )
        )
        self.assertEqual(zero.zero_pixel_reject_count, 1)

        pass_state = stage.SegClipDebugState()
        stage.debug_add_line(
            pass_state,
            stage.DebugSeg(0, 1, 1),
            vertices,
            [solid_line, pass_line],
            sidedefs,
            sectors,
            frontsector_index=0,
            seg_index=11,
        )
        self.assertEqual(pass_state.pass_classification_count, 1)
        self.assertEqual(pass_state.solidsegs, list(stage04.clear_clipseg_sentinels()))

    def test_clip_solid_wall_segment_insert_extend_and_merge_behavior(self) -> None:
        state = stage.SegClipDebugState()
        state.current_reason = stage.SPAN_REASON_SOLID
        state.current_seg_index = 1

        stage.debug_clip_solid_wall_segment(state, 10, 20)
        self.assertEqual(state.solidsegs, [(-0x7FFFFFFF, -1), (10, 20), (320, 0x7FFFFFFF)])
        self.assertEqual(state.clip_insert_count, 1)
        self.assertEqual(state.spans[-1], stage.DebugSpan(10, 20, stage.SPAN_REASON_SOLID, 1))

        stage.debug_clip_solid_wall_segment(state, 5, 12)
        self.assertEqual(state.solidsegs[1], (5, 20))
        self.assertEqual(state.clip_extend_front_count, 1)
        self.assertEqual(state.spans[-1].start, 5)
        self.assertEqual(state.spans[-1].stop, 9)

        state.solidsegs.insert(2, (30, 40))
        stage.debug_clip_solid_wall_segment(state, 15, 35)
        self.assertEqual(state.solidsegs, [(-0x7FFFFFFF, -1), (5, 40), (320, 0x7FFFFFFF)])
        self.assertEqual(state.clip_merge_count, 1)
        self.assertEqual(state.spans[-1], stage.DebugSpan(21, 29, stage.SPAN_REASON_SOLID, 1))

    def test_clip_pass_wall_segment_records_without_mutating_solidsegs(self) -> None:
        state = stage.SegClipDebugState(
            solidsegs=[(-0x7FFFFFFF, -1), (10, 20), (320, 0x7FFFFFFF)]
        )
        state.current_reason = stage.SPAN_REASON_PASS
        state.current_seg_index = 2
        before = list(state.solidsegs)

        stage.debug_clip_pass_wall_segment(state, 5, 25)

        self.assertEqual(state.solidsegs, before)
        self.assertEqual(
            state.spans,
            [
                stage.DebugSpan(5, 9, stage.SPAN_REASON_PASS, 2),
                stage.DebugSpan(21, 25, stage.SPAN_REASON_PASS, 2),
            ],
        )

    def test_mutable_solidsegs_can_make_check_bbox_reject_stage04_accepts(self) -> None:
        unit = stage.FRACUNIT
        east_visible = [
            stage.VIEW_Y_FIXED + unit,
            stage.VIEW_Y_FIXED - unit,
            stage.VIEW_X_FIXED + unit * 4,
            stage.VIEW_X_FIXED + unit * 6,
        ]

        self.assertTrue(stage04.check_bbox(east_visible, solidsegs=stage04.clear_clipseg_sentinels()))
        self.assertFalse(stage04.check_bbox(east_visible, solidsegs=[(-0x7FFFFFFF, 0x7FFFFFFF)]))

    def test_store_wall_range_span_buffer_bounds_and_counters(self) -> None:
        state = stage.SegClipDebugState(max_spans=2)
        state.current_reason = stage.SPAN_REASON_PASS
        state.current_seg_index = 44

        stage.debug_store_wall_range(state, 1, 2)
        stage.debug_store_wall_range(state, 3, 4)
        stage.debug_store_wall_range(state, 5, 6)
        stage.debug_store_wall_range(state, 7, 6)

        self.assertEqual(state.stored_span_count, 2)
        self.assertEqual(state.span_overflow_count, 1)
        self.assertEqual(state.last_span, stage.DebugSpan(3, 4, stage.SPAN_REASON_PASS, 44))

    def test_pinned_iwad_reference_seg_clipping_matches_expected_counts(self) -> None:
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
                ref.clip_max_depth,
                ref.clip_first_subsector,
                ref.clip_last_subsector,
                ref.clip_bbox_cull_count,
                ref.backface_reject_count,
                ref.off_frustum_reject_count,
                ref.zero_pixel_reject_count,
                ref.solid_classification_count,
                ref.pass_classification_count,
                ref.empty_line_reject_count,
                ref.stored_span_count,
                ref.final_solidseg_count,
                ref.span_overflow_count,
                ref.clip_insert_count,
                ref.clip_extend_front_count,
                ref.clip_extend_tail_count,
                ref.clip_merge_count,
            ),
            (72, 56, 205, 15, 227, 294, 17, 82, 17, 5, 30, 70, 1, 86, 1, 0, 6, 9, 3, 7),
        )
        self.assertEqual(ref.first_span, stage.DebugSpan(224, 255, stage.SPAN_REASON_SOLID, 605))
        self.assertEqual(ref.last_span, stage.DebugSpan(143, 165, stage.SPAN_REASON_SOLID, 855))

    def test_stage05_debug_buffer_offsets(self) -> None:
        self.assertEqual(stage.DEBUG_SPAN_START, 0)
        self.assertEqual(stage.DEBUG_SPAN_STOP, 4)
        self.assertEqual(stage.DEBUG_SPAN_REASON, 8)
        self.assertEqual(stage.DEBUG_SPAN_SEG_INDEX, 12)
        self.assertEqual(stage.DEBUG_SPAN_RECORD_SIZE, 16)
        self.assertEqual(stage.DEBUG_SPAN_BUFFER_BYTES, stage.MAX_DEBUG_SPANS * 16)

        self.assertEqual(stage.CLIP_TRAVERSAL_VISITED_NODE_COUNT, 0)
        self.assertEqual(stage.CLIP_TRAVERSAL_VISITED_SUBSECTOR_COUNT, 4)
        self.assertEqual(stage.CLIP_TRAVERSAL_VISITED_SEG_COUNT, 8)
        self.assertEqual(stage.CLIP_TRAVERSAL_MAX_DEPTH, 12)
        self.assertEqual(stage.CLIP_TRAVERSAL_FIRST_SUBSECTOR, 16)
        self.assertEqual(stage.CLIP_TRAVERSAL_LAST_SUBSECTOR, 20)
        self.assertEqual(stage.CLIP_TRAVERSAL_CULLED_NODE_COUNT, 24)
        self.assertEqual(stage.CLIP_TRAVERSAL_STORED_SPAN_COUNT, 52)
        self.assertEqual(stage.CLIP_TRAVERSAL_DEBUG_STATE_BYTES, 80)

    def test_executable_build_contains_source_stage_status_text(self) -> None:
        image = stage.build_source_stage05_seg_clip_debug_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage05_seg_clip_debug", image)
        self.assertIn(b"Seg clipping debug OK", image)
        self.assertIn(b"R_ClipSolidWallSegment calls", image)
        self.assertIn(b"R_ClipPassWallSegment calls", image)
        self.assertIn(b"Debug R_StoreWallRange spans", image)
        self.assertIn(b" CLN=", image)
        self.assertIn(b" SPAN=", image)
        self.assertNotIn(b"source_stage06", image)
        self.assertNotIn(b"R_PointToDist", image)
        self.assertNotIn(b"R_RenderSegLoop", image)
        self.assertNotIn(b"GCC:", image)
        self.assertNotIn(b"MinGW", image)
        self.assertNotIn(b"Microsoft Visual C", image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_expected_seg_clip_counts_in_window_title(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_seg_clip_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage05_seg_clip_debug.exe"
        stage.write_source_stage05_seg_clip_debug_exe(exe_path)

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
