import os
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage27_integrated_scripted_room_interaction_loop as stage


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


class SourceStage27IntegratedScriptedRoomInteractionLoopTests(unittest.TestCase):
    def _ref(self) -> stage.Stage27IntegratedScriptedRoomLoopReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_integrated_scripted_room_interaction_loop_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_name_integrated_loop_route(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}
        self.assertIn("G_Ticker_stage27_scripted_ticcmd_room_loop_source_shape_debug", labels)
        self.assertIn("P_PlayerThink_stage27_scripted_use_gate_source_shape_debug", labels)
        self.assertIn("P_UseLines_stage27_selected_line_use_source_shape_debug", labels)
        self.assertIn("P_Ticker_stage27_integrated_order_source_shape_debug", labels)
        self.assertIn("T_PlatRaise_stage27_sampled_runtime_loop_source_shape_debug", labels)

    def test_synthetic_ticker_order_and_deterministic_ticcmd_consumption(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        world = stage._build_stage27_world(stage.WadFile.from_file(PINNED_WAD), stage.SELECTED_MAP)
        for _ in range(3):
            stage.g_ticker_stage27_scripted_ticcmd_room_loop_source_shape(world)

        self.assertEqual((world.counters.g_ticker_calls, world.counters.script_commands_consumed), (3, 3))
        self.assertEqual((world.counters.scripted_use_commands, world.counters.player_use_edges), (1, 1))
        self.assertEqual(world.counters.selected_use_line_calls, 1)
        self.assertEqual(world.ticker_world.order_log[:5], ["P_Ticker", "P_PlayerThink_guard", "P_RunThinkers", "P_UpdateSpecials", "P_RespawnSpecials"])
        self.assertEqual(stage._stage27_order_ok(world), 1)

    def test_synthetic_multi_tic_state_log_has_distinct_successive_states(self) -> None:
        ref = self._ref()
        self.assertEqual([sample.tic for sample in ref.samples], [1, 14, 35, 36, 120, 136])
        states = {(sample.floor, sample.button_timer, sample.texture, sample.plat_status, sample.plat_count) for sample in ref.samples}
        self.assertGreaterEqual(len(states), 3)
        self.assertEqual(ref.counters.distinct_sample_states, 6)
        self.assertIn("1:F-12:B34:SW2STRTN:S1:C0", stage._stage27_log_text(ref.samples))
        self.assertIn("35:F-64:B0:SW1STRTN:S2:C85", stage._stage27_log_text(ref.samples))
        self.assertIn("136:F-8:B0:SW1STRTN:S2:C105", stage._stage27_log_text(ref.samples))

    def test_synthetic_button_restores_while_platform_thinker_lifecycle_continues(self) -> None:
        ref = self._ref()
        restore = next(sample for sample in ref.samples if sample.tic == 35)
        later = next(sample for sample in ref.samples if sample.tic == 120)
        final = ref.samples[-1]
        self.assertEqual((restore.texture, restore.button_timer, restore.floor), ("SW1STRTN", 0, -64))
        self.assertEqual((later.plat_status, later.floor), (stage.stage25.PLAT_UP, -64))
        self.assertEqual((final.floor, ref.counters.plat_removal_requests, ref.counters.activeplat_slot_clears), (-8, 1, 1))
        self.assertEqual(ref.counters.button_restore_during_plat_motion, 1)

    def test_synthetic_no_live_input_dependency_and_deferred_boundaries(self) -> None:
        ref = self._ref()
        self.assertEqual(ref.counters.no_live_input_dependency, 1)
        self.assertEqual(ref.counters.live_input_events, 0)
        self.assertEqual(ref.counters.actual_speaker_playback_deferred, 1)
        self.assertEqual(ref.counters.real_audio_playbacks, 0)
        self.assertEqual((ref.counters.map_progression_absent, ref.counters.generalized_combat_absent), (1, 1))

    def test_pinned_real_map_script_preserves_stage26_to_stage19_and_reports_signature(self) -> None:
        ref = self._ref()
        self.assertEqual(ref.stage26.signature, 132405987)
        self.assertEqual(ref.stage26.stage25.signature, 1688844032)
        self.assertEqual(ref.stage26.stage25.stage24.signature, 1919312263)
        self.assertEqual(ref.stage26.stage25.stage24.stage23.signature, 3216085132)
        self.assertEqual(ref.stage26.stage25.stage24.stage23.stage22.signature, 2207028069)
        self.assertEqual(ref.stage26.stage25.stage24.stage23.stage22.stage21.signature, 1770773845)
        self.assertEqual(ref.stage26.stage25.stage24.stage23.stage22.stage21.stage20.signature, 3226031347)
        self.assertEqual(ref.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)
        self.assertEqual((ref.stage25_route.census.map_name, ref.stage25_route.census.line_index, ref.stage25_route.census.special), ("MAP12", 2304, 62))
        self.assertEqual((ref.counters.g_ticker_calls, ref.ticker_counters.ticker_calls, ref.leveltime_after, ref.order_ok), (136, 136, 136, 1))
        self.assertEqual(ref.signature, 1735738182)

    def test_executable_build_contains_stage27_status_preserves_signatures_and_omits_forbidden_strings(self) -> None:
        image = stage.build_source_stage27_integrated_scripted_room_interaction_loop_exe()
        lower = image.lower()
        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage27_integrated_scripted_room_interaction_loop", image)
        self.assertIn(b"Integrated scripted room loop proof OK", image)
        self.assertIn(b"LOG27=", image)
        self.assertIn(b"S27 LIVE START STEP27=0", image)
        self.assertIn(b"S27 LIVE STEP27=1 TIC27=1", image)
        self.assertIn(b"S27 LIVE STEP27=6 TIC27=136", image)
        self.assertIn(b"1:F-12:B34:SW2STRTN:S1:C0", image)
        self.assertIn(b"35:F-64:B0:SW1STRTN:S2:C85", image)
        for marker in (b" S19SIG=", b" S20SIG=", b" S21SIG=", b" S22SIG=", b" S23SIG=", b" S24SIG=", b" S25SIG=", b" S26SIG=", b" S27SIG="):
            self.assertIn(marker, image)
        self.assertNotIn(b"source_stage28", lower)
        for forbidden in (b"gcc:", b"mingw", b"microsoft visual c", b"real audio playback", b"mixer/device playback"):
            self.assertNotIn(forbidden, lower)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage27_log_and_preserved_stage26_to_stage19(self) -> None:
        ref = self._ref()
        exe_path = REPO_ROOT / "build" / "source_stage27_integrated_scripted_room_interaction_loop.exe"
        stage.write_source_stage27_integrated_scripted_room_interaction_loop_exe(exe_path)
        expected = (
            f"S19SIG={ref.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature}",
            f"S20SIG={ref.stage26.stage25.stage24.stage23.stage22.stage21.stage20.signature}",
            f"S21SIG={ref.stage26.stage25.stage24.stage23.stage22.stage21.signature}",
            f"S22SIG={ref.stage26.stage25.stage24.stage23.stage22.signature}",
            f"S23SIG={ref.stage26.stage25.stage24.stage23.signature}",
            f"S24SIG={ref.stage26.stage25.stage24.signature}",
            f"S25SIG={ref.stage26.stage25.signature}",
            f"S26SIG={ref.stage26.signature}",
            f"S27SIG={ref.signature}",
            "STEP27=6",
            "TIC27=136",
            "F27=-8",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, start_title = window_title_for_pid(process.pid, expected=("S27 LIVE START",), timeout_seconds=1.5)
            self.assertIn("STEP27=0", start_title)
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn("S27 LIVE STEP27=6", title)
            self.assertIn("TEX27=SW1STRTN", title)
            self.assertIn("STAT27=2", title)
            self.assertIn("COUNT27=105", title)
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
