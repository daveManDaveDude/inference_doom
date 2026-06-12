import os
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage11_visplanes_floor_ceiling_debug as stage


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


def window_title_for_pid(
    pid: int, expected: tuple[str, ...] = (), timeout_seconds: float = 5.0
) -> tuple[int, str]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    deadline = time.monotonic() + timeout_seconds
    last_seen = ""

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
            hwnd, title = found[0]
            last_seen = title
            if not expected or all(fragment in title for fragment in expected):
                return hwnd, title
        time.sleep(0.1)

    raise TimeoutError(f"no matching visible window title found for pid {pid}: {last_seen!r}")


class SourceStage11VisplanesFloorCeilingDebugTests(unittest.TestCase):
    def test_source_trace_covers_visplane_and_span_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("render_visplane_subsector_candidates_debug", labels)
        self.assertIn("render_clear_planes_source_shape_debug", labels)
        self.assertIn("render_find_plane_source_shape_debug", labels)
        self.assertIn("render_check_plane_source_shape_debug", labels)
        self.assertIn("render_make_spans_source_shape_debug", labels)
        self.assertIn("render_map_plane_source_shape_debug", labels)
        self.assertIn("render_draw_planes_source_shape_debug", labels)
        self.assertIn("render_draw_span_debug", labels)
        self.assertIn("stage11_flat_lump_sources_debug", labels)

    def test_r_find_plane_reuses_normalizes_sky_initializes_and_counts_overflow(self) -> None:
        state = stage.VisplaneState(width=4, height=4, max_visplanes=3, skyflatnum=99)
        state.clear_planes()

        first = state.find_plane(64, 7, 160, "floor")
        reused = state.find_plane(64, 7, 160, "floor")
        sky = state.find_plane(128, 99, 192, "ceiling")
        sky_reused = state.find_plane(256, 99, 64, "ceiling")

        self.assertIsNotNone(first)
        self.assertIs(first, reused)
        self.assertIs(sky, sky_reused)
        assert first is not None
        assert sky is not None
        self.assertEqual((first.minx, first.maxx), (4, -1))
        self.assertTrue(all(value == stage.NO_TOP for value in first.top))
        self.assertEqual((sky.height, sky.lightlevel, sky.picnum), (0, 0, 99))
        self.assertEqual((state.find_new, state.find_reused, state.overflow), (2, 2, 0))

        tiny = stage.VisplaneState(width=4, height=4, max_visplanes=1, skyflatnum=99)
        self.assertIsNotNone(tiny.find_plane(0, 1, 0))
        self.assertIsNone(tiny.find_plane(0, 2, 0))
        self.assertEqual(tiny.overflow, 1)

    def test_r_check_plane_reuses_splits_unions_occupied_arrays_and_counts_overflow(self) -> None:
        state = stage.VisplaneState(width=8, height=8, max_visplanes=3)
        plane = state.find_plane(0, 1, 0)
        self.assertIsNotNone(plane)
        assert plane is not None

        reused = state.check_plane(plane, 2, 4, "floor")
        self.assertIs(reused, plane)
        self.assertEqual((plane.minx, plane.maxx), (2, 4))

        plane.set_mark(3, 1, 2, "floor")
        self.assertNotEqual(plane.top_at(3), stage.NO_TOP)
        split = state.check_plane(plane, 3, 5, "floor")
        self.assertIsNot(split, plane)
        self.assertIsNotNone(split)
        assert split is not None
        self.assertEqual((split.minx, split.maxx), (3, 5))
        self.assertEqual(state.check_splits, 1)

        union = state.check_plane(plane, 0, 1, "floor")
        self.assertIs(union, plane)
        self.assertEqual((plane.minx, plane.maxx), (0, 4))

        tiny = stage.VisplaneState(width=8, height=8, max_visplanes=1)
        only = tiny.find_plane(0, 1, 0)
        self.assertIsNotNone(only)
        assert only is not None
        only.minx = 0
        only.maxx = 2
        only.set_mark(1, 1, 1, "floor")
        self.assertIsNone(tiny.check_plane(only, 1, 3, "floor"))
        self.assertEqual(tiny.overflow, 1)

    def test_r_make_spans_opens_and_closes_horizontal_spans(self) -> None:
        state = stage.VisplaneState(width=8, height=8)
        mapped: list[tuple[int, int, int]] = []
        record = lambda y, x1, x2: mapped.append((y, x1, x2))

        stage.r_make_spans(state, 3, stage.NO_TOP, 0, 1, 2, record)
        self.assertEqual(mapped, [])
        self.assertEqual((state.spanstart[1], state.spanstart[2]), (3, 3))

        stage.r_make_spans(state, 5, 1, 2, stage.NO_TOP, 0, record)
        self.assertEqual(mapped, [(1, 3, 4), (2, 3, 4)])

    def test_r_draw_span_and_r_map_plane_use_deterministic_flat_sampling(self) -> None:
        flat = bytes(i & 0xFF for i in range(stage.FLAT_SIZE))
        palette = tuple(range(256))

        colors, signature = stage.r_draw_span_pixels(
            flat,
            palette,
            x1=0,
            x2=3,
            xfrac=0,
            yfrac=0,
            xstep=stage.FRACUNIT,
            ystep=0,
        )

        expected_signature = stage.FNV_OFFSET_BASIS
        for color in (0, 1, 2, 3):
            expected_signature = ((expected_signature * stage.FNV_PRIME) & 0xFFFFFFFF) ^ color
            expected_signature &= 0xFFFFFFFF

        self.assertEqual(colors, (0, 1, 2, 3))
        self.assertEqual(signature, expected_signature)

        tables = stage.PlaneMappingTables.fixed_view()
        command, pixels, mapped_signature = stage.r_map_plane(
            tables,
            y=120,
            x1=10,
            x2=12,
            planeheight=64 * stage.FRACUNIT,
            source_index=2,
            source=flat,
            palette32=palette,
            signature=stage.FNV_OFFSET_BASIS,
            flat_id=17,
            flat_name="TESTFLT",
            plane_kind="floor",
        )
        _, redraw_signature = stage.r_draw_span_pixels(
            flat,
            palette,
            x1=command.x1,
            x2=command.x2,
            xfrac=command.xfrac,
            yfrac=command.yfrac,
            xstep=command.xstep,
            ystep=command.ystep,
        )

        self.assertEqual(pixels, 3)
        self.assertEqual(command.source_index, 2)
        self.assertEqual((command.flat_id, command.flat_name, command.plane_kind), (17, "TESTFLT", "floor"))
        self.assertEqual(mapped_signature, redraw_signature)

    def test_pinned_map_visplanes_flat_spans_and_preserved_stage10_counts(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_visplanes_floor_ceiling_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.stage10.stage09.columns_drawn, 162)
        self.assertEqual(ref.stage10.stage09.framebuffer_signature, 2194105880)
        self.assertEqual(ref.stage10.composite_cache_builds, 89)
        self.assertEqual(ref.stage10.composite_cache_hits, 75)
        self.assertEqual(ref.stage10.plane_mark_ceiling_records, 727)
        self.assertEqual(ref.stage10.plane_mark_floor_records, 932)
        self.assertEqual(ref.stage10.columns_drawn, 780)
        self.assertEqual(ref.stage10.pixels_drawn, 37546)
        self.assertEqual(ref.stage10.framebuffer_signature, 4201955800)

        self.assertEqual(ref.visplane_count, 38)
        self.assertEqual(ref.visplane_find_calls, 118)
        self.assertEqual(ref.visplane_new_count, 30)
        self.assertEqual(ref.visplane_reuse_count, 88)
        self.assertEqual(ref.visplane_check_calls, 110)
        self.assertEqual(ref.visplane_check_reuse_count, 102)
        self.assertEqual(ref.visplane_split_count, 8)
        self.assertEqual(ref.visplane_overflow_count, 0)
        self.assertEqual(ref.ceiling_plane_mark_records, 727)
        self.assertEqual(ref.floor_plane_mark_records, 932)
        self.assertEqual(ref.regular_visplanes_drawn, 38)
        self.assertEqual(ref.flat_spans_drawn, 169)
        self.assertEqual(ref.flat_pixels_drawn, 20791)
        self.assertEqual(ref.flat_source_skips, 0)
        self.assertEqual(ref.flat_span_overflow_count, 0)
        self.assertEqual(ref.sky_visplanes_skipped, 0)
        self.assertEqual(ref.sky_columns_skipped, 0)
        self.assertEqual(ref.sky_pixels_skipped, 0)
        self.assertEqual((ref.first_floor_flat_id, ref.first_floor_flat_name), (81, "SLIME14"))
        self.assertEqual((ref.first_ceiling_flat_id, ref.first_ceiling_flat_name), (113, "FLOOR5_2"))
        self.assertEqual(ref.framebuffer_signature, 2178063413)
        self.assertEqual((len(ref.flat_sources), len(ref.commands)), (8, 169))

    def test_executable_build_contains_stage11_status_text_and_no_stage12_or_deferred_features(self) -> None:
        image = stage.build_source_stage11_visplanes_floor_ceiling_debug_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage11_visplanes_floor_ceiling_debug", image)
        self.assertIn(b"Visplane regular flat span debug OK", image)
        self.assertIn(b"R_FindPlane", image)
        self.assertIn(b"R_CheckPlane", image)
        self.assertIn(b"R_MakeSpans", image)
        self.assertIn(b"R_MapPlane", image)
        self.assertIn(b"R_DrawPlanes", image)
        self.assertIn(b"R_DrawSpan", image)
        self.assertIn(b" VP=", image)
        self.assertIn(b" FSP=", image)
        self.assertIn(b" FSIG=", image)
        self.assertNotIn(b"sky rendering", lower)
        self.assertNotIn(b"masked wall drawing", lower)
        self.assertNotIn(b"sprite rendering", lower)
        self.assertNotIn(b"actor rendering", lower)
        self.assertNotIn(b"movement", lower)
        self.assertNotIn(b"gameplay loop", lower)
        self.assertNotIn(b"source_stage12", image)
        self.assertNotIn(b"GCC:", image)
        self.assertNotIn(b"MinGW", image)
        self.assertNotIn(b"Microsoft Visual C", image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage11_counts_signature_and_preserved_stage10_counts(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_visplanes_floor_ceiling_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage11_visplanes_floor_ceiling_debug.exe"
        stage.write_source_stage11_visplanes_floor_ceiling_debug_exe(exe_path)

        expected = (
            f"DRAW={ref.stage10.stage09.columns_drawn}",
            f"TCOL={ref.stage10.columns_drawn}",
            f"FSP={ref.flat_spans_drawn}",
            f"FSIG={ref.framebuffer_signature}",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn(f"DRAW={ref.stage10.stage09.columns_drawn}", title)
            self.assertIn(f"SIG={ref.stage10.stage09.framebuffer_signature}", title)
            self.assertIn(f"CMB={ref.stage10.composite_cache_builds}", title)
            self.assertIn(f"CMH={ref.stage10.composite_cache_hits}", title)
            self.assertIn(f"PM={ref.stage10.plane_mark_ceiling_records + ref.stage10.plane_mark_floor_records}", title)
            self.assertIn(f"TCOL={ref.stage10.columns_drawn}", title)
            self.assertIn(f"TPIX={ref.stage10.pixels_drawn}", title)
            self.assertIn(f"TSIG={ref.stage10.framebuffer_signature}", title)
            self.assertIn(f"VP={ref.visplane_count}", title)
            self.assertIn(f"VPF={ref.visplane_new_count}", title)
            self.assertIn(f"VPR={ref.visplane_reuse_count}", title)
            self.assertIn(f"VPS={ref.visplane_split_count}", title)
            self.assertIn(f"VPO={ref.visplane_overflow_count}", title)
            self.assertIn(f"CPM={ref.ceiling_plane_mark_records}", title)
            self.assertIn(f"FPM={ref.floor_plane_mark_records}", title)
            self.assertIn(f"FSP={ref.flat_spans_drawn}", title)
            self.assertIn(f"FPIX={ref.flat_pixels_drawn}", title)
            self.assertIn(f"SKYV={ref.sky_visplanes_skipped}", title)
            self.assertIn(f"SKYC={ref.sky_columns_skipped}", title)
            self.assertIn(f"SKYP={ref.sky_pixels_skipped}", title)
            self.assertIn(f"FSK={ref.flat_source_skips}", title)
            self.assertIn(f"SPO={ref.flat_span_overflow_count}", title)
            self.assertIn(f"F11F={ref.first_floor_flat_id}", title)
            self.assertIn(f"F11FN={ref.first_floor_flat_name}", title)
            self.assertIn(f"C11F={ref.first_ceiling_flat_id}", title)
            self.assertIn(f"C11N={ref.first_ceiling_flat_name}", title)
            self.assertIn(f"FSIG={ref.framebuffer_signature}", title)
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
