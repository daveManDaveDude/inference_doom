import os
import re
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage39_selected_projectile_spawn_present_probe as stage


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
            return True

        user32.EnumWindows(enum_proc_type(enum_proc), 0)
        if found:
            return found[0]
        time.sleep(0.05)
    return 0, ""


def collect_stage39_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP39=3" in title and "S39SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage39 final title not reached; saw {titles!r}")


class SourceStage39SelectedProjectileSpawnPresentProbeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage39SelectedProjectileSpawnPresentProbeReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_selected_projectile_spawn_present_probe_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_name_selected_projectile_sources(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("A_TroopAttack_selected_imp_missile_branch_debug", labels)
        self.assertIn("A_FaceTarget_selected_imp_angle_update_debug", labels)
        self.assertIn("P_SpawnMissile_selected_troopshot_fields_debug", labels)
        self.assertIn("P_CheckMissileSpawn_selected_first_trymove_debug", labels)
        self.assertIn("info_selected_troopshot_tball1_bal1_debug", labels)
        self.assertIn("S_StartSound_selected_firsht_deferred_debug", labels)

    def test_synthetic_selected_imp_candidate_census_and_non_melee_branch(self) -> None:
        ref = self._ref()
        c = ref.candidate

        self.assertEqual((c.type_name, c.doomednum), ("MT_TROOP", 3001))
        self.assertEqual((c.mapthing_index, c.mobj_index), (55, 42))
        self.assertEqual(c.health, 60)
        self.assertEqual(c.target_index, 0)
        self.assertEqual(c.target_present, 1)
        self.assertGreaterEqual(c.distance_to_target, c.melee_threshold)
        self.assertEqual((c.melee_rejected, c.missile_branch_selected, c.sight_gate_required), (1, 1, 0))
        self.assertEqual(c.source_marker, "MT_TROOP->P0")

    def test_synthetic_a_face_target_angle_update_and_spawn_missile_fields(self) -> None:
        ref = self._ref()
        c = ref.candidate
        p = ref.projectile

        self.assertEqual(p.angle, stage.stage04.point_to_angle(c.target_x, c.target_y, c.x, c.y))
        self.assertEqual(p.angle_degrees, stage.stage13.angle_to_degrees(p.angle))
        self.assertEqual((p.spawn_x, p.spawn_y, p.spawn_z), (c.x, c.y, c.z + 32 * stage.FRACUNIT))
        self.assertNotEqual(p.momx, 0)
        self.assertNotEqual(p.momy, 0)
        self.assertEqual(p.momz, 0)
        self.assertEqual((p.source_marker, p.missile_target_marker, p.dest_marker), ("MT_TROOP->P0", "TH.target=MT_TROOP", "dest=P0"))

    def test_synthetic_troopshot_tball1_bal1_metadata(self) -> None:
        ref = self._ref()
        p = ref.projectile

        self.assertEqual((p.type_name, p.spawnstate_name, p.sprite_name, p.frame_letter), ("MT_TROOPSHOT", "S_TBALL1", "SPR_BAL1", "A"))
        self.assertEqual(p.raw_state_tics, 4)
        self.assertEqual(p.frame_value & stage.FF_FRAMEMASK, 0)
        self.assertTrue(p.frame_value & stage.FF_FULLBRIGHT)
        self.assertEqual((p.sound, p.sound_events), ("sfx_firsht", 1))
        self.assertGreater(p.speed, 0)

    def test_synthetic_deterministic_p_random_tic_adjustment(self) -> None:
        ref = self._ref()
        p = ref.projectile

        self.assertEqual((p.lastlook_random, p.tic_random), (26, 36))
        self.assertEqual(p.tic_adjustment, p.tic_random & 3)
        self.assertEqual(p.tics_after_adjustment, max(1, p.raw_state_tics - p.tic_adjustment))
        self.assertEqual(p.tics_after_adjustment, 4)
        self.assertEqual(ref.projectile.state_signature, 1403583302)

    def test_synthetic_p_check_missile_spawn_movement_trymove_ordering(self) -> None:
        ref = self._ref()
        p = ref.projectile

        self.assertEqual((p.check_missile_spawn_calls, p.try_move_calls, p.check_position_calls), (1, 1, 1))
        self.assertEqual((p.try_move_success, p.exploded), (1, 0))
        self.assertEqual(p.half_step_x, stage.stage04._int32(p.spawn_x + (p.momx >> 1)))
        self.assertEqual(p.half_step_y, stage.stage04._int32(p.spawn_y + (p.momy >> 1)))
        self.assertEqual(p.half_step_z, stage.stage04._int32(p.spawn_z + (p.momz >> 1)))

    def test_synthetic_projectile_marker_bounds_and_state_signature_contribution(self) -> None:
        ref = self._ref()
        max_marker_pixels = max(sample.projectile_marker_pixels for sample in ref.samples)
        marker_end = stage.PROJECTILE_MARKER_OFFSET + max_marker_pixels * 4

        self.assertEqual([sample.projectile_marker_pixels for sample in ref.samples], [0, 11, 18])
        self.assertEqual([sample.pre_projectile_framebuffer_signature for sample in ref.samples], [2997224612, 1850654463, 4146202648])
        self.assertEqual([sample.framebuffer_signature for sample in ref.samples], [2997224612, 3296846536, 2778992910])
        self.assertLessEqual(marker_end, stage.FRAMEBUFFER_BYTES)
        self.assertEqual(ref.distinct_projectile_state_signatures, 3)
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)
        self.assertEqual(ref.projectile_contribution_signatures, 2)

    def test_synthetic_frame_step_ordering_preserves_all_prior_draws_then_projectile_present(self) -> None:
        ref = self._ref()

        self.assertEqual([sample.step for sample in ref.samples], [1, 2, 3])
        self.assertEqual([sample.tic for sample in ref.samples], [0, 4, 7])
        self.assertEqual(
            [
                (
                    s.clear_sequence,
                    s.wall_flat_sequence,
                    s.impact_sequence,
                    s.death_sequence,
                    s.drop_sequence,
                    s.psprite_sequence,
                    s.feedback_sequence,
                    s.projectile_sequence,
                    s.signature_sequence,
                    s.present_sequence,
                )
                for s in ref.samples
            ],
            [(1, 2, 3, 4, 5, 6, 7, 8, 9, 10), (11, 12, 13, 14, 15, 16, 17, 18, 19, 20), (21, 22, 23, 24, 25, 26, 27, 28, 29, 30)],
        )

    def test_synthetic_invalidate_update_paint_ordering_preserves_stage38_behavior(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.timer_samples, len(ref.samples))
        self.assertEqual((ref.invalidate_calls, ref.update_window_calls, ref.expected_paint_calls), (3, 3, 3))
        self.assertEqual(ref.paint_after_final_projectile_marker, 1)
        self.assertEqual(ref.stage38_present_stability_preserved, 1)
        self.assertEqual((ref.stage38.invalidate_calls, ref.stage38.update_window_calls, ref.stage38.expected_paint_calls), (3, 3, 3))
        self.assertEqual(ref.stage38.paint_after_final_feedback_marker, 1)

    def test_absence_flags_keep_deferred_systems_out(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage39_selected_projectile_spawn_present_probe_exe()
        lower = image.lower()

        for value in (
            ref.full_frame_byte_arrays_absent,
            ref.runtime_renderer_primitives,
            ref.generalized_projectile_manager_absent,
            ref.explosions_absent,
            ref.radius_damage_absent,
            ref.splash_damage_absent,
            ref.infighting_absent,
            ref.player_death_absent,
            ref.enemy_kill_drop_absent,
            ref.generalized_combat_absent,
            ref.broad_ai_absent,
            ref.generalized_sprite_traversal_absent,
            ref.statusbar_hud_rebuild_absent,
            ref.map_progression_absent,
            ref.ui_systems_absent,
            ref.real_audio_absent,
            ref.source_stage40_absent,
        ):
            self.assertEqual(value, 1)
        self.assertNotIn(b"source_stage40", lower)
        for forbidden in (
            b"generalized projectile manager implemented",
            b"explosion spawned",
            b"radius damage implemented",
            b"splash damage implemented",
            b"infighting implemented",
            b"player death implemented",
            b"enemy kill drop implemented",
            b"generalized monster ai implemented",
            b"broad combat implemented",
            b"generalized sprite traversal implemented",
            b"statusbar hud rebuild implemented",
            b"map progression implemented",
            b"menu system implemented",
            b"real audio playback implemented",
        ):
            self.assertNotIn(forbidden, lower)

    def test_stage39_does_not_rely_on_full_pre_rendered_frame_arrays_for_motion(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage39_selected_projectile_spawn_present_probe_exe()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertNotIn(b"stage39_frame_pixels", image)
        self.assertNotIn(b"stage39_copy_rendered_frame", image)
        self.assertIn(b"NOFULL39=1", image)
        self.assertIn(b"A_TroopAttack->A_FaceTarget->P_SpawnMissile", image)
        self.assertEqual(image.count(b"\xF3\xA5"), 0)

    def test_pinned_replay_preserves_stage38_through_stage31_visual_bridges(self) -> None:
        ref = self._ref()
        s36 = ref.stage38.stage36

        self.assertEqual(ref.stage38.signature, 2314527789)
        self.assertEqual(ref.stage38.attack.state_signature, 1816157848)
        self.assertEqual(s36.signature, 397846180)
        self.assertEqual(stage.stage36.ref35_signature(s36), 3270148876)
        self.assertEqual(s36.stage34.signature, 4027590938)
        self.assertEqual(s36.stage34.stage33.signature, 1614948054)
        self.assertEqual(s36.stage34.stage33.stage32.signature, 533488475)
        self.assertEqual(s36.stage34.stage33.stage32.stage31.signature, 3593583171)
        self.assertEqual((s36.pickup.removed_item, s36.pickup.item_present_after), (1, 0))
        self.assertGreater(s36.samples[-1].wall_pixels_drawn + s36.samples[-1].flat_pixels_drawn, 50000)
        self.assertGreater(s36.samples[-1].impact_pixels_drawn, 0)
        self.assertGreater(s36.samples[-1].death_pixels_drawn, 0)
        self.assertEqual(s36.samples[-1].drop_pixels_drawn, 0)
        self.assertGreater(s36.samples[-1].psprite_pixels_drawn, 1000)

    def test_preserves_stage38_through_stage19_signatures(self) -> None:
        ref = self._ref()
        s29 = ref.stage38.stage29
        s31 = ref.stage38.stage36.stage34.stage33.stage32.stage31

        self.assertEqual(ref.signature, 3469618451)
        self.assertEqual(ref.stage38.signature, 2314527789)
        self.assertEqual(stage.BASELINE_S37_SIGNATURE, 2681905384)
        self.assertEqual(ref.stage38.stage36.signature, 397846180)
        self.assertEqual(stage.stage36.ref35_signature(ref.stage38.stage36), 3270148876)
        self.assertEqual(ref.stage38.stage36.stage34.signature, 4027590938)
        self.assertEqual(ref.stage38.stage36.stage34.stage33.signature, 1614948054)
        self.assertEqual(ref.stage38.stage36.stage34.stage33.stage32.signature, 533488475)
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

    def test_build_output_contains_stage39_markers_and_no_stage40_strings(self) -> None:
        output = REPO_ROOT / "build" / "source_stage39_selected_projectile_spawn_present_probe.exe"
        output.parent.mkdir(parents=True, exist_ok=True)
        image = stage.build_source_stage39_selected_projectile_spawn_present_probe_exe()
        output.write_bytes(image)

        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 100_000)
        self.assertIn(b"source_stage39_selected_projectile_spawn_present_probe", image)
        self.assertIn(b"S39SIG=3469618451", image)
        self.assertIn(b"MISS39=MT_TROOPSHOT", image)
        self.assertIn(b"SFX39=sfx_firsht", image)
        self.assertIn(b"INV38=3 UPD38=3 PAINT38=3 PAF38=1", image)
        self.assertNotIn(b"source_stage40", image.lower())

    @unittest.skipUnless(os.name == "nt", "Win32 GUI smoke test requires Windows")
    def test_smoke_executable_launches_reports_projectile_samples_and_closes(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        output = REPO_ROOT / "build" / "source_stage39_selected_projectile_spawn_present_probe.exe"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(stage.build_source_stage39_selected_projectile_spawn_present_probe_exe())

        proc = subprocess.Popen([str(output)], cwd=REPO_ROOT)
        try:
            hwnd, titles = collect_stage39_titles(proc.pid)
            final = titles[-1]
            self.assertNotEqual(hwnd, 0)
            self.assertIn("STEP39=3", final)
            self.assertIn("S39SIG=3469618451", final)
            self.assertIn("PST39=1403583302", final)
            self.assertIn("MISS39=MT_TROOPSHOT", final)
            self.assertIn("ST39=S_TBALL1", final)
            self.assertIn("SPR39=SPR_BAL1", final)
            self.assertIn("SFX39=sfx_firsht", final)
            self.assertIn("INV39=3 UPD39=3 PAINT39=3 PAF39=1", final)
            self.assertIn("INV38=3 UPD38=3 PAINT38=3 PAF38=1", final)
            self.assertIn("S40ABS=1", final)
            fb_values = {
                int(match.group(1))
                for title in titles
                for match in re.finditer(r"FB39=(\d+)", title)
            }
            marker_values = {
                int(match.group(1))
                for title in titles
                for match in re.finditer(r"PMRK39=(\d+)", title)
            }
            self.assertGreaterEqual(len(fb_values), 2)
            self.assertGreaterEqual(len(marker_values), 2)
            time.sleep(0.25)
            self.assertIsNone(proc.poll())
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3.0)
        self.assertIn(proc.returncode, (0, 1))


if __name__ == "__main__":
    unittest.main()
