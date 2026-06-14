import os
import re
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage31_runtime_real_renderer_motion_bridge as stage


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
        time.sleep(0.05)

    raise TimeoutError(f"no visible window title found for pid {pid}")


def collect_stage31_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP31=3" in title and "S31SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage31 final title not reached; saw {titles!r}")


class SourceStage31RuntimeRealRendererMotionBridgeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage31RuntimeRealRendererReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_runtime_real_renderer_motion_bridge_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_name_runtime_real_renderer_sources(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("R_RenderPlayerView_stage31_runtime_command_table_redraw_debug", labels)
        self.assertIn("R_RenderSegLoop_stage31_runtime_wall_command_table_debug", labels)
        self.assertIn("R_DrawPlanes_stage31_runtime_flat_command_table_debug", labels)
        self.assertIn("V_DrawBlock_stage31_runtime_real_renderer_present_debug", labels)

    def test_synthetic_frame_step_ordering_is_start_samples_final(self) -> None:
        ref = self._ref()

        self.assertEqual([sample.step for sample in ref.samples], [1, 2, 3])
        self.assertEqual([sample.tic for sample in ref.samples], [0, 4, 7])
        titles = stage._stage31_replay_titles(ref)
        self.assertIn("STEP31=1", titles[0])
        self.assertIn("STEP31=3", titles[-1])
        self.assertIn("S31SIG=", titles[-1])

    def test_synthetic_selected_runtime_state_maps_to_renderer_inputs(self) -> None:
        ref = self._ref()

        self.assertEqual(
            [(s.viewx >> stage.FRACBITS, s.viewy >> stage.FRACBITS, s.viewangle_degrees) for s in ref.samples],
            [(-192, -192, 0), (-182, -192, 1), (-172, -194, 3)],
        )
        self.assertEqual(ref.distinct_view_inputs, 3)
        for sample in ref.samples:
            self.assertGreater(len(sample.wall_commands), 0)
            self.assertGreater(len(sample.flat_spans), 0)

    def test_synthetic_render_command_table_selection_changes_tables(self) -> None:
        ref = self._ref()

        first_columns = [
            tuple((command.x, command.yl, command.yh, command.texturemid) for command in sample.wall_commands[:16])
            for sample in ref.samples
        ]
        self.assertEqual(ref.distinct_command_tables, 3)
        self.assertEqual(len(set(first_columns)), 3)
        self.assertEqual([len(sample.wall_commands) for sample in ref.samples], [780, 776, 769])
        self.assertEqual([len(sample.flat_spans) for sample in ref.samples], [169, 169, 169])

    def test_synthetic_framebuffer_clear_draw_present_ordering(self) -> None:
        ref = self._ref()

        self.assertEqual(
            [(s.clear_sequence, s.draw_sequence, s.present_sequence) for s in ref.samples],
            [(1, 2, 3), (4, 5, 6), (7, 8, 9)],
        )
        for sample in ref.samples:
            self.assertLess(sample.clear_sequence, sample.draw_sequence)
            self.assertLess(sample.draw_sequence, sample.present_sequence)
            self.assertGreater(sample.wall_pixels_drawn, 0)
            self.assertGreater(sample.flat_pixels_drawn, 0)

    def test_synthetic_distinct_framebuffer_signature_expectations(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.signature, 3593583171)
        self.assertEqual(
            [sample.framebuffer_signature for sample in ref.samples],
            [2926869513, 622680457, 1677820087],
        )
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)

    def test_absence_flags_keep_deferred_systems_and_stage32_out(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage31_runtime_real_renderer_motion_bridge_exe()
        lower = image.lower()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertEqual(ref.runtime_renderer_primitives, 1)
        self.assertEqual(ref.wall_path_replayed, 1)
        self.assertEqual(ref.flat_path_replayed, 1)
        self.assertEqual(ref.sky_path_deferred, 1)
        self.assertEqual(ref.masked_path_deferred, 1)
        self.assertEqual(ref.sprite_path_deferred, 1)
        self.assertEqual(ref.projectiles_absent, 1)
        self.assertEqual(ref.explosions_absent, 1)
        self.assertEqual(ref.combat_visual_state_absent, 1)
        self.assertEqual(ref.generalized_combat_absent, 1)
        self.assertEqual(ref.broad_ai_absent, 1)
        self.assertEqual(ref.generalized_specials_absent, 1)
        self.assertEqual(ref.map_progression_absent, 1)
        self.assertEqual(ref.ui_systems_absent, 1)
        self.assertEqual(ref.real_audio_absent, 1)
        self.assertEqual(ref.source_stage32_absent, 1)
        self.assertNotIn(b"source_stage32", lower)
        for forbidden in (
            b"projectile spawned",
            b"explosion spawned",
            b"combat visual state implemented",
            b"map progression implemented",
            b"menu system implemented",
            b"real audio playback implemented",
        ):
            self.assertNotIn(forbidden, lower)

    def test_stage31_does_not_rely_on_full_pre_rendered_frame_arrays_for_motion(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage31_runtime_real_renderer_motion_bridge_exe()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertNotIn(b"stage31_frame_pixels", image)
        self.assertNotIn(b"stage31_copy_rendered_frame", image)
        self.assertIn(b"Runtime renderer command frame log", image)
        self.assertIn(b"WC31=", image)
        self.assertIn(b"SP31=", image)
        self.assertIn(b"NOFULL31=1", image)
        self.assertIn(b"R_DrawColumn/R_DrawSpan-shaped primitives", image)
        self.assertEqual(image.count(b"\xF3\xA5"), 0)
        command_bytes = sum(
            len(sample.wall_commands) * stage.COMMAND_RECORD_SIZE + len(sample.flat_spans) * stage.SPAN_RECORD_SIZE
            for sample in ref.samples
        )
        self.assertLess(command_bytes, stage.FRAMEBUFFER_BYTES * len(ref.samples) // 8)

    def test_pinned_real_map_replay_changes_inputs_and_real_renderer_pixels(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.stage30.signature, 3898523864)
        self.assertEqual(ref.stage30.stage29.signature, 3738922932)
        self.assertEqual(ref.distinct_view_inputs, 3)
        self.assertEqual(ref.distinct_command_tables, 3)
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)
        self.assertGreaterEqual(len({sample.framebuffer_signature for sample in ref.samples}), 2)
        self.assertGreater(ref.samples[-1].wall_pixels_drawn + ref.samples[-1].flat_pixels_drawn, 50000)

    def test_preserves_stage30_through_stage19_signatures(self) -> None:
        ref = self._ref()
        stage29_ref = ref.stage30.stage29
        stage28_ref = stage29_ref.stage28

        self.assertEqual(ref.stage30.signature, 3898523864)
        self.assertEqual(stage29_ref.signature, 3738922932)
        self.assertEqual(stage28_ref.signature, 2805406010)
        self.assertEqual(stage28_ref.stage27.signature, 1735738182)
        self.assertEqual(stage28_ref.stage27.stage26.signature, 132405987)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.signature, 1688844032)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.stage24.signature, 1919312263)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.stage24.stage23.signature, 3216085132)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.stage24.stage23.stage22.signature, 2207028069)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.stage24.stage23.stage22.stage21.signature, 1770773845)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.signature, 3226031347)
        self.assertEqual(stage28_ref.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)

    def test_executable_build_contains_stage31_markers_and_no_stage32_strings(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage31_runtime_real_renderer_motion_bridge_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage31_runtime_real_renderer_motion_bridge", image)
        self.assertIn(b"Runtime real-renderer command bridge proof OK", image)
        self.assertIn(b"S31 REALRENDER START STEP31=0", image)
        self.assertIn(b"STEP31=1", image)
        self.assertIn(b"STEP31=2", image)
        self.assertIn(b"STEP31=3", image)
        self.assertIn(f"S31SIG={ref.signature}".encode("ascii"), image)
        self.assertIn(b"S30SIG=3898523864", image)
        self.assertIn(b"S19SIG=2088411722", image)
        self.assertNotIn(b"source_stage32", image.lower())

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage31_frames_and_distinct_signatures(self) -> None:
        ref = self._ref()
        exe_path = REPO_ROOT / "build" / "source_stage31_runtime_real_renderer_motion_bridge.exe"
        stage.write_source_stage31_runtime_real_renderer_motion_bridge_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, titles = collect_stage31_titles(process.pid, timeout_seconds=8.0)
            joined = "\n".join(titles)
            fb_values = {
                int(match.group(1))
                for title in titles
                for match in [re.search(r"FB31=(\d+)", title)]
                if match
            }

            self.assertIn("S31 REALRENDER START STEP31=0", joined)
            self.assertIn("STEP31=1", joined)
            self.assertIn("STEP31=2", joined)
            self.assertIn("STEP31=3", joined)
            self.assertEqual(fb_values, {sample.framebuffer_signature for sample in ref.samples})
            self.assertGreaterEqual(len(fb_values), 2)
            self.assertIn(f"FBDIST31={ref.distinct_framebuffer_signatures}", joined)
            self.assertIn("NOFULL31=1", joined)
            self.assertIn(f"S31SIG={ref.signature}", joined)
            for stage_num, signature in (
                (30, 3898523864),
                (29, 3738922932),
                (28, 2805406010),
                (27, 1735738182),
                (26, 132405987),
                (25, 1688844032),
                (24, 1919312263),
                (23, 3216085132),
                (22, 2207028069),
                (21, 1770773845),
                (20, 3226031347),
                (19, 2088411722),
            ):
                self.assertIn(f"S{stage_num}SIG={signature}", joined)
            self.assertIn("S32ABS=1", joined)
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
