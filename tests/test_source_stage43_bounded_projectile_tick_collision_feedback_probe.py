import os
import re
import subprocess
import time
import unittest
from functools import lru_cache
from pathlib import Path

from tools import emit_source_stage43_bounded_projectile_tick_collision_feedback_probe as stage


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


@lru_cache(maxsize=1)
def built_stage43_image() -> bytes:
    return stage.build_source_stage43_bounded_projectile_tick_collision_feedback_probe_exe()


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
            return True

        user32.EnumWindows(enum_proc_type(enum_proc), 0)
        if found:
            return found[0]
        time.sleep(0.05)
    return 0, ""


def collect_stage43_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP43=3" in title and "S43SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage43 final title not reached; saw {titles!r}")


def close_window(hwnd: int) -> None:
    import ctypes

    if hwnd:
        ctypes.WinDLL("user32", use_last_error=True).PostMessageW(hwnd, 0x0010, 0, 0)


class SourceStage43BoundedProjectileTickCollisionFeedbackProbeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage43BoundedProjectileTickCollisionFeedbackProbeReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_bounded_projectile_tick_collision_feedback_probe_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_cover_projectile_thinker_collision_and_feedback_sources(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}
        files = {entry[0] for entry in stage.SOURCE_TRACE}

        for label in (
            "P_MobjThinker_stage43_selected_troopshot_tick_debug",
            "P_TryMove_stage43_selected_missile_no_collision_debug",
            "PIT_CheckThing_stage43_selected_source_skip_no_damage_debug",
            "P_BlockIterators_stage43_selected_projectile_bounds_debug",
            "info_stage43_selected_troopshot_tic_metadata_debug",
            "R_RenderPlayerView_stage43_projectile_feedback_order_debug",
            "ST_updateWidgets_stage43_no_damage_status_preserved_debug",
            "I_Video_stage43_projectile_tick_present_debug",
        ):
            self.assertIn(label, labels)
        for source in ("p_mobj.c", "p_map.c", "p_maputl.c", "info.c", "r_main.c", "st_stuff.c", "i_video.c"):
            self.assertTrue(any(path.endswith(source) for path in files), source)

    def test_synthetic_projectile_thinker_samples_advance_after_launch(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.deterministic_projectile_thinker_samples, 1)
        self.assertEqual(ref.projectile_advanced_after_launch, 1)
        self.assertEqual([s.step for s in ref.samples], [1, 2, 3])
        self.assertEqual([s.thinker_tic for s in ref.samples], [0, 1, 2])
        self.assertEqual([s.tic for s in ref.samples], [0, 4, 7])
        self.assertEqual([s.type_name for s in ref.samples], ["MT_TROOPSHOT"] * 3)
        self.assertEqual([s.state_name for s in ref.samples], ["S_TBALL1"] * 3)
        self.assertEqual([s.next_state_name for s in ref.samples], ["S_TBALL2"] * 3)
        self.assertEqual([s.sprite_name for s in ref.samples], ["SPR_BAL1"] * 3)
        self.assertEqual([s.tics_after for s in ref.samples], [4, 3, 2])
        self.assertEqual([(s.new_x >> stage.stage31.FRACBITS, s.new_y >> stage.stage31.FRACBITS) for s in ref.samples], [(1332, -435), (1341, -439), (1350, -444)])
        self.assertEqual(len({(s.new_x, s.new_y, s.tics_after) for s in ref.samples}), 3)

    def test_synthetic_trymove_checkposition_no_collision_no_damage_evidence(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.selected_trymove_boundary, 1)
        self.assertEqual(ref.selected_checkposition_boundary, 1)
        self.assertEqual(ref.selected_block_iterator_boundary, 1)
        self.assertEqual(ref.selected_source_skip_boundary, 1)
        self.assertEqual(ref.selected_no_collision_result, 1)
        self.assertEqual(ref.selected_no_damage_feedback, 1)
        self.assertEqual([s.try_move_success for s in ref.samples], [1, 1, 1])
        self.assertEqual([s.no_collision for s in ref.samples], [1, 1, 1])
        self.assertEqual([s.no_damage for s in ref.samples], [1, 1, 1])
        self.assertEqual([s.move_delta.try_move_calls for s in ref.samples], [0, 1, 1])
        self.assertEqual([s.move_delta.check_position_calls for s in ref.samples], [0, 1, 1])
        self.assertEqual([s.move_delta.accepted_moves for s in ref.samples], [0, 1, 1])
        self.assertEqual([s.move_delta.rejected_moves for s in ref.samples], [0, 0, 0])
        self.assertEqual([s.move_delta.blocking_lines for s in ref.samples], [0, 0, 0])
        self.assertEqual([s.move_delta.blocking_things for s in ref.samples], [0, 0, 0])
        self.assertEqual([s.move_delta.source_thing_skips for s in ref.samples], [0, 1, 1])
        self.assertTrue(all(s.target_distance_x > s.target_radius_sum for s in ref.samples))
        self.assertTrue(all(s.target_distance_y > s.target_radius_sum for s in ref.samples))
        self.assertEqual([(s.player_health_before, s.player_health_after) for s in ref.samples], [(100, 100), (91, 91), (91, 91)])

    def test_synthetic_projectile_thinker_ordering_inside_unified_loop(self) -> None:
        ref = self._ref()

        for sample in ref.samples:
            self.assertLess(sample.p_ticker_sequence, sample.p_runthinkers_sequence)
            self.assertLess(sample.p_runthinkers_sequence, sample.mobj_thinker_sequence)
            self.assertLess(sample.mobj_thinker_sequence, sample.xy_movement_sequence)
            self.assertLess(sample.xy_movement_sequence, sample.check_position_sequence)
            self.assertLess(sample.check_position_sequence, sample.try_move_sequence)
            self.assertLess(sample.try_move_sequence, sample.state_tic_sequence)
            self.assertLess(sample.state_tic_sequence, sample.no_collision_feedback_sequence)
            self.assertLess(sample.no_collision_feedback_sequence, sample.render_sequence)
            self.assertLess(sample.render_sequence, sample.status_sequence)
            self.assertLess(sample.status_sequence, sample.signature_sequence)
            self.assertLess(sample.signature_sequence, sample.present_sequence)

    def test_synthetic_no_damage_status_feedback_and_bal1_vissprite_preserved(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.compact_status_preserved_because_no_damage, 1)
        self.assertEqual(ref.stage40_bal1_vissprite_preserved, 1)
        self.assertEqual(ref.stage42.stage41.signature, 951695045)
        self.assertEqual(ref.stage42.stage41.state_signature, 157977072)
        self.assertEqual(ref.stage42.stage41.stage40.signature, 2737672056)
        self.assertEqual(ref.stage42.stage41.stage40.state_signature, 268409133)
        self.assertEqual([s.baseline.baseline.selected_status_state_signature for s in ref.samples], [1548266261, 4244284538, 3218471217])
        self.assertEqual([s.baseline.world_vissprite_state_signature for s in ref.samples], [1957020629, 3758004534, 1436017657])

    def test_synthetic_state_and_framebuffer_signatures(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.signature, 2916740242)
        self.assertEqual(ref.state_signature, 801364352)
        self.assertEqual([s.projectile_state_signature for s in ref.samples], [2141010421, 1184488335, 467194799])
        self.assertEqual([s.stage43_unified_state_signature for s in ref.samples], [531845647, 3017464017, 3895028583])
        self.assertEqual([s.framebuffer_signature for s in ref.samples], [832571689, 3232273554, 3301289045])
        self.assertEqual(ref.distinct_projectile_state_signatures, 3)
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)
        self.assertEqual(ref.distinct_stage43_unified_state_signatures, 3)
        self.assertTrue(all(s.pre_marker_framebuffer_signature != s.framebuffer_signature for s in ref.samples))

    def test_synthetic_present_after_final_projectile_sample_preserves_stage42(self) -> None:
        ref = self._ref()

        self.assertEqual((ref.timer_samples, ref.invalidate_calls, ref.update_window_calls, ref.expected_paint_calls), (3, 3, 3, 3))
        self.assertEqual(ref.paint_after_final_projectile_sample, 1)
        self.assertEqual(ref.final_window_alive_after_samples, 1)
        self.assertEqual(ref.closes_normally, 1)
        self.assertEqual(ref.stage42_unified_loop_preserved, 1)
        self.assertEqual((ref.stage42.invalidate_calls, ref.stage42.update_window_calls, ref.stage42.expected_paint_calls), (3, 3, 3))
        self.assertEqual(ref.stage42.paint_after_final_unified_sample, 1)

    def test_runtime_primitives_tables_generate_state_changes_without_full_frame_copies(self) -> None:
        ref = self._ref()
        image = built_stage43_image()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertEqual(ref.runtime_renderer_primitives, 1)
        self.assertIn(b"NOFULL43=1", image)
        self.assertIn(b"P_MobjThinker->P_XYMovement->P_TryMove", image)
        self.assertNotIn(b"stage43_frame_pixels", image)
        self.assertNotIn(b"stage43_copy_rendered_frame", image)
        self.assertEqual(image.count(b"\xF3\xA5"), 0)

    def test_absence_flags_keep_deferred_systems_out_and_no_stage44_strings(self) -> None:
        ref = self._ref()
        lower = built_stage43_image().lower()

        for value in (
            ref.live_input_absent,
            ref.generalized_thinkers_absent,
            ref.generalized_collision_absent,
            ref.generalized_projectile_manager_absent,
            ref.broad_monster_ai_absent,
            ref.broad_inventory_absent,
            ref.broad_hud_ui_absent,
            ref.player_death_absent,
            ref.enemy_kill_drop_absent,
            ref.explosions_absent,
            ref.radius_damage_absent,
            ref.splash_damage_absent,
            ref.infighting_absent,
            ref.map_progression_absent,
            ref.save_load_absent,
            ref.networking_absent,
            ref.music_absent,
            ref.real_audio_absent,
            ref.mixer_device_playback_absent,
            ref.source_stage44_absent,
        ):
            self.assertEqual(value, 1)
        self.assertNotIn(b"source_stage44", lower)
        for forbidden in (
            b"generalized thinker implemented",
            b"generalized collision implemented",
            b"generalized projectile manager implemented",
            b"explosion spawned",
            b"radius damage implemented",
            b"splash damage implemented",
            b"infighting implemented",
            b"player death implemented",
            b"enemy kill drop implemented",
            b"real audio playback implemented",
            b"mixer device playback implemented",
        ):
            self.assertNotIn(forbidden, lower)

    def test_preserves_stage42_through_stage19_signatures(self) -> None:
        ref = self._ref()
        ref42 = ref.stage42
        ref41 = ref42.stage41
        ref40 = ref41.stage40
        ref39 = ref40.stage39
        ref38 = ref39.stage38
        s29 = ref38.stage29
        s36 = ref38.stage36
        s31 = s36.stage34.stage33.stage32.stage31

        self.assertEqual(ref.stage42_unified_loop_preserved, 1)
        self.assertEqual(ref.stage41_status_preserved, 1)
        self.assertEqual(ref.stage40_vissprite_preserved, 1)
        self.assertEqual(ref.stage39_projectile_state_preserved, 1)
        self.assertEqual(ref.stage38_present_preserved, 1)
        self.assertEqual(ref42.signature, 2427416971)
        self.assertEqual(ref42.state_signature, 2148021159)
        self.assertEqual(ref41.signature, 951695045)
        self.assertEqual(ref41.state_signature, 157977072)
        self.assertEqual(ref40.signature, 2737672056)
        self.assertEqual(ref40.state_signature, 268409133)
        self.assertEqual(ref39.signature, 3469618451)
        self.assertEqual(ref39.projectile.state_signature, 1403583302)
        self.assertEqual(ref38.signature, 2314527789)
        self.assertEqual(ref38.attack.state_signature, 1816157848)
        self.assertEqual(stage.stage39.BASELINE_S37_SIGNATURE, 2681905384)
        self.assertEqual(s36.signature, 397846180)
        self.assertEqual(stage.stage36.ref35_signature(s36), 3270148876)
        self.assertEqual(s36.stage34.signature, 4027590938)
        self.assertEqual(s36.stage34.stage33.signature, 1614948054)
        self.assertEqual(s36.stage34.stage33.stage32.signature, 533488475)
        self.assertEqual(s31.signature, 3593583171)
        self.assertEqual(s31.stage30.signature, 3898523864)
        self.assertEqual(s29.signature, 3738922932)
        self.assertEqual(s29.stage28.signature, 2805406010)
        self.assertEqual(s29.stage28.stage27.signature, 1735738182)
        self.assertEqual(s29.stage28.stage27.stage26.signature, 132405987)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.signature, 1688844032)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.stage24.signature, 1919312263)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.stage24.stage23.signature, 3216085132)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.signature, 2207028069)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.signature, 1770773845)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.signature, 3226031347)
        self.assertEqual(s29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)

    def test_build_output_contains_stage43_markers_and_no_stage44_strings(self) -> None:
        output = REPO_ROOT / "build" / "source_stage43_bounded_projectile_tick_collision_feedback_probe.exe"
        output.parent.mkdir(parents=True, exist_ok=True)
        image = built_stage43_image()
        output.write_bytes(image)

        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 100_000)
        self.assertIn(b"source_stage43_bounded_projectile_tick_collision_feedback_probe", image)
        self.assertIn(b"S43SIG=2916740242", image)
        self.assertIn(b"STATE43=801364352", image)
        self.assertIn(b"PSTATE43=467194799", image)
        self.assertIn(b"NOCOLL43=1", image)
        self.assertIn(b"NODMG43=1", image)
        self.assertIn(b"PATCH40=BAL1", image)
        self.assertIn(b"INV43=3 UPD43=3 PAINT43=3 PAF43=1", image)
        self.assertIn(b"S42SIG=2427416971", image)
        self.assertIn(b"S19SIG=2088411722", image)
        self.assertNotIn(b"source_stage44", image.lower())

    @unittest.skipUnless(os.name == "nt", "Win32 GUI smoke test requires Windows")
    def test_smoke_executable_launches_reports_projectile_ticks_paints_and_closes(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        output = REPO_ROOT / "build" / "source_stage43_bounded_projectile_tick_collision_feedback_probe.exe"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(built_stage43_image())

        proc = subprocess.Popen([str(output)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, titles = collect_stage43_titles(proc.pid)
            final = titles[-1]
            self.assertNotEqual(hwnd, 0)
            self.assertIn("STEP43=3", final)
            self.assertIn("S43SIG=2916740242", final)
            self.assertIn("STATE43=801364352", final)
            self.assertIn("MISS43=MT_TROOPSHOT:S_TBALL1->S_TBALL2", final)
            self.assertIn("PX43=1350", final)
            self.assertIn("PY43=-444", final)
            self.assertIn("TICS43=3->2", final)
            self.assertIn("TRY43=1:1", final)
            self.assertIn("CHK43=1:1", final)
            self.assertIn("SRC_SKIP43=1", final)
            self.assertIn("NOCOLL43=1", final)
            self.assertIn("NODMG43=1", final)
            self.assertIn("PATCH40=BAL1", final)
            self.assertIn("INV43=3 UPD43=3 PAINT43=3 PAF43=1", final)
            self.assertIn("INV42=3 UPD42=3 PAINT42=3 PAF42=1", final)
            self.assertIn("S44ABS=1", final)
            fb_values = {
                int(match.group(1))
                for title in titles
                for match in re.finditer(r"FB43=(\d+)", title)
            }
            state_values = {
                int(match.group(1))
                for title in titles
                for match in re.finditer(r"PSTATE43=(\d+)", title)
            }
            self.assertGreaterEqual(len(fb_values), 2)
            self.assertGreaterEqual(len(state_values), 2)
            time.sleep(0.25)
            self.assertIsNone(proc.poll())
            close_window(hwnd)
            proc.wait(timeout=3.0)
        finally:
            if proc.poll() is None:
                if hwnd:
                    close_window(hwnd)
                    try:
                        proc.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        proc.terminate()
                else:
                    proc.terminate()
                try:
                    proc.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3.0)
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
