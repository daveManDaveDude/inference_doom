import os
import re
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage30_runtime_rendered_motion_bridge as stage


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


def window_title_for_pid(pid: int, timeout_seconds: float = 5.0) -> tuple[int, str]:
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
            return found[0]
        time.sleep(0.05)

    raise TimeoutError(f"no visible window title found for pid {pid}: {last_seen!r}")


def collect_stage30_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP30=3" in title and "S30SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage30 final title not reached; saw {titles!r}")


class SourceStage30RuntimeRenderedMotionBridgeTests(unittest.TestCase):
    def test_source_trace_labels_name_runtime_rendered_motion_sources(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("G_Ticker_stage30_selected_motion_replay_source_shape_debug", labels)
        self.assertIn("P_PlayerThink_stage30_motion_view_source_shape_debug", labels)
        self.assertIn("R_SetupFrame_stage30_runtime_view_copy_source_shape_debug", labels)
        self.assertIn("R_RenderPlayerView_stage30_runtime_redraw_bridge_debug", labels)
        self.assertIn("V_DrawBlock_stage30_framebuffer_present_debug", labels)

    def test_synthetic_frame_step_ordering_is_start_then_samples_then_final(self) -> None:
        ref = stage.reference_runtime_rendered_motion_bridge_for_pinned_map(PINNED_WAD)

        self.assertEqual([sample.step for sample in ref.samples], [1, 2, 3])
        self.assertEqual([sample.tic for sample in ref.samples], [0, 4, 7])
        self.assertEqual(stage._stage30_replay_titles(ref)[0].split()[4], "STEP30=1")
        self.assertIn("STEP30=3", stage._stage30_replay_titles(ref)[-1])

    def test_synthetic_runtime_state_maps_to_renderer_inputs(self) -> None:
        ref = stage.reference_runtime_rendered_motion_bridge_for_pinned_map(PINNED_WAD)
        samples = ref.samples

        self.assertEqual([(s.viewx >> stage.FRACBITS, s.viewy >> stage.FRACBITS) for s in samples], [
            (-192, -192),
            (-182, -192),
            (-172, -194),
        ])
        self.assertEqual([s.viewangle_degrees for s in samples], [0, 1, 3])
        self.assertEqual(ref.distinct_view_inputs, 3)

    def test_synthetic_framebuffer_clear_then_redraw_ordering(self) -> None:
        ref = stage.reference_runtime_rendered_motion_bridge_for_pinned_map(PINNED_WAD)

        self.assertEqual([(s.clear_sequence, s.redraw_sequence) for s in ref.samples], [(1, 2), (3, 4), (5, 6)])
        for sample in ref.samples:
            self.assertLess(sample.clear_sequence, sample.redraw_sequence)
            self.assertEqual(sample.pixels_drawn, stage.FRAMEBUFFER_PIXELS)
            self.assertEqual(len(sample.framebuffer), stage.FRAMEBUFFER_BYTES)

    def test_synthetic_distinct_framebuffer_signature_expectations(self) -> None:
        ref = stage.reference_runtime_rendered_motion_bridge_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.signature, 3898523864)
        self.assertEqual([s.framebuffer_signature for s in ref.samples], [2289904038, 2221072019, 169445058])
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)

    def test_absence_flags_keep_deferred_systems_and_stage31_out(self) -> None:
        ref = stage.reference_runtime_rendered_motion_bridge_for_pinned_map(PINNED_WAD)
        image = stage.build_source_stage30_runtime_rendered_motion_bridge_exe()

        self.assertEqual(ref.projectiles_absent, 1)
        self.assertEqual(ref.explosions_absent, 1)
        self.assertEqual(ref.generalized_combat_absent, 1)
        self.assertEqual(ref.broad_ai_absent, 1)
        self.assertEqual(ref.generalized_specials_absent, 1)
        self.assertEqual(ref.map_progression_absent, 1)
        self.assertEqual(ref.ui_systems_absent, 1)
        self.assertEqual(ref.real_audio_absent, 1)
        self.assertEqual(ref.source_stage31_absent, 1)
        self.assertNotIn(b"source_stage31", image.lower())
        for forbidden in (
            b"projectile spawned",
            b"explosion spawned",
            b"map progression implemented",
            b"menu system",
            b"mixer playback",
            b"stage31",
        ):
            if forbidden == b"stage31":
                self.assertNotIn(b"source_stage31", image.lower())
            else:
                self.assertNotIn(forbidden, image.lower())

    def test_pinned_real_map_replay_changes_view_inputs_and_framebuffer_pixels(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_runtime_rendered_motion_bridge_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.stage29.signature, 3738922932)
        self.assertEqual(ref.stage14.signature, 3925602456)
        self.assertEqual(ref.replay_frame_count, 3)
        self.assertEqual(ref.distinct_view_inputs, 3)
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)
        self.assertGreaterEqual(len({sample.framebuffer for sample in ref.samples}), 2)

    def test_preserves_stage29_through_stage19_signatures(self) -> None:
        ref = stage.reference_runtime_rendered_motion_bridge_for_pinned_map(PINNED_WAD)
        stage28_ref = ref.stage29.stage28

        self.assertEqual(ref.stage29.signature, 3738922932)
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

    def test_executable_build_contains_stage30_markers_and_no_stage31_strings(self) -> None:
        ref = stage.reference_runtime_rendered_motion_bridge_for_pinned_map(PINNED_WAD)
        image = stage.build_source_stage30_runtime_rendered_motion_bridge_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage30_runtime_rendered_motion_bridge", image)
        self.assertIn(b"Runtime rendered motion bridge proof OK", image)
        self.assertIn(b"S30 RENDER START STEP30=0", image)
        self.assertIn(b"STEP30=1", image)
        self.assertIn(b"STEP30=2", image)
        self.assertIn(b"STEP30=3", image)
        self.assertIn(f"S30SIG={ref.signature}".encode("ascii"), image)
        self.assertIn(b"S29SIG=3738922932", image)
        self.assertIn(b"S19SIG=2088411722", image)
        self.assertNotIn(b"source_stage31", image.lower())

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage30_frames_and_distinct_framebuffer_signatures(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_runtime_rendered_motion_bridge_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage30_runtime_rendered_motion_bridge.exe"
        stage.write_source_stage30_runtime_rendered_motion_bridge_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, titles = collect_stage30_titles(process.pid, timeout_seconds=8.0)
            joined = "\n".join(titles)
            fb_values = {
                int(match.group(1))
                for title in titles
                for match in [re.search(r"FB30=(\d+)", title)]
                if match
            }

            self.assertIn("S30 RENDER START STEP30=0", joined)
            self.assertIn("STEP30=1", joined)
            self.assertIn("STEP30=2", joined)
            self.assertIn("STEP30=3", joined)
            self.assertGreaterEqual(len(fb_values), 2)
            self.assertEqual(fb_values, {s.framebuffer_signature for s in ref.samples})
            self.assertIn(f"FBDIST30={ref.distinct_framebuffer_signatures}", joined)
            self.assertIn(f"S30SIG={ref.signature}", joined)
            for stage_num, signature in (
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
            self.assertIn("S31ABS=1", joined)
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
