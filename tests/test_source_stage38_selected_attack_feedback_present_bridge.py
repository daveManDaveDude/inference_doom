import os
import re
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage38_selected_attack_feedback_present_bridge as stage


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


def collect_stage38_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP38=3" in title and "S38SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage38 final title not reached; saw {titles!r}")


class SourceStage38SelectedAttackFeedbackPresentBridgeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage38SelectedAttackFeedbackPresentBridgeReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_selected_attack_feedback_present_bridge_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_name_selected_attack_sources(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("A_SPosAttack_stage38_selected_shotgun_guy_feedback_debug", labels)
        self.assertIn("A_FaceTarget_stage38_selected_actor_angle_debug", labels)
        self.assertIn("P_AimLineAttack_stage38_selected_player_target_debug", labels)
        self.assertIn("P_LineAttack_stage38_selected_three_pellet_feedback_debug", labels)
        self.assertIn("P_DamageMobj_stage38_selected_player_feedback_debug", labels)
        self.assertIn("S_StartSound_stage38_selected_sfx_shotgn_boundary_debug", labels)

    def test_synthetic_frame_step_ordering_preserves_prior_renderer_then_feedback_present(self) -> None:
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
                    s.present_sequence,
                )
                for s in ref.samples
            ],
            [(1, 2, 3, 4, 5, 6, 7, 8), (9, 10, 11, 12, 13, 14, 15, 16), (17, 18, 19, 20, 21, 22, 23, 24)],
        )

    def test_synthetic_selected_stage29_living_monster_context_is_preserved(self) -> None:
        ref = self._ref()
        actor = ref.stage29.final_mobj

        self.assertEqual(ref.stage29.boundary, "ATTACK_DECISION")
        self.assertEqual(actor.type_name, "MT_SHOTGUY")
        self.assertEqual(actor.target_index, 0)
        self.assertEqual(actor.health, 20)
        self.assertEqual(actor.threshold, 99)
        self.assertFalse(actor.removed)

    def test_synthetic_a_spos_attack_target_guard_and_face_target_angle_update(self) -> None:
        ref = self._ref()
        no_target = stage.selected_attack_feedback_stage38_source_shape(ref.stage29, target_present=False)

        self.assertEqual(stage.a_spos_attack_stage38_selected(target_present=False), (0, 0, 0, 0))
        self.assertEqual(no_target.target_guard_passed, 0)
        self.assertEqual(no_target.line_attacks, 0)
        self.assertEqual(ref.attack.target_guard_passed, 1)
        self.assertEqual(ref.attack.face_target_calls, 1)
        self.assertNotEqual(ref.attack.angle_before, ref.attack.angle_after)
        self.assertEqual(ref.attack.bangle, ref.attack.angle_after)

    def test_synthetic_deterministic_spread_damage_aim_and_line_attack_accounting(self) -> None:
        ref = self._ref()
        attack = ref.attack

        self.assertEqual(attack.aim_calls, 1)
        self.assertEqual(attack.aim_target_index, 0)
        self.assertEqual(attack.aim_slope, 0)
        self.assertEqual(attack.line_attacks, 3)
        self.assertEqual((attack.line_hits, attack.line_misses), (1, 2))
        self.assertEqual(
            [(p.spread_random_a, p.spread_random_b, p.damage_random, p.damage, p.hit_player) for p in attack.pellets],
            [(26, 36, 17, 9, 1), (46, 52, 231, 6, 0), (232, 76, 31, 6, 0)],
        )
        self.assertTrue(all(p.line_attack_called for p in attack.pellets))

    def test_synthetic_selected_player_p_damagemobj_mutation_and_sound_boundary(self) -> None:
        ref = self._ref()
        attack = ref.attack

        self.assertEqual((attack.health_before, attack.health_after), (100, 91))
        self.assertEqual((attack.armor_before, attack.armor_after, attack.armor_type), (0, 0, 0))
        self.assertEqual((attack.damagecount_before, attack.damagecount_after), (0, 9))
        self.assertEqual((attack.player_damage_events, attack.no_player_death), (1, 1))
        self.assertEqual((attack.attacker_index, attack.source_marker), (28, "MT_SHOTGUY->P0"))
        self.assertEqual((attack.thrust_marker, attack.pain_flash_marker), (1, 1))
        self.assertEqual((attack.sound, attack.sound_events), ("sfx_shotgn", 1))

    def test_synthetic_feedback_marker_and_state_signatures_include_attack_contribution(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.signature, 2314527789)
        self.assertEqual(ref.attack.state_signature, 1816157848)
        self.assertEqual([s.pre_feedback_framebuffer_signature for s in ref.samples], [2997224612, 1668066382, 1194192847])
        self.assertEqual([s.framebuffer_signature for s in ref.samples], [2997224612, 1850654463, 4146202648])
        self.assertEqual([s.feedback_marker_pixels for s in ref.samples], [0, 9, 15])
        self.assertEqual(ref.distinct_state_signatures, 3)
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)
        self.assertEqual(ref.attack_contribution_signatures, 2)

    def test_synthetic_status_pointer_framebuffer_and_marker_bounds_are_stable(self) -> None:
        ref = self._ref()
        max_marker_pixels = max(sample.feedback_marker_pixels for sample in ref.samples)
        marker_end = stage.FEEDBACK_MARKER_OFFSET + max_marker_pixels * 4

        self.assertGreaterEqual(ref.status_title_buffer_bytes, 4096)
        self.assertEqual(ref.status_pointer_lifetime_stable, 1)
        self.assertEqual(ref.framebuffer_owner_stable, 1)
        self.assertEqual(ref.marker_bounds_checked, 1)
        self.assertLessEqual(marker_end, stage.FRAMEBUFFER_BYTES)

    def test_synthetic_invalidate_update_paint_ordering_is_bounded_after_final_marker(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.timer_samples, len(ref.samples))
        self.assertEqual((ref.invalidate_calls, ref.update_window_calls, ref.expected_paint_calls), (3, 3, 3))
        self.assertEqual(ref.paint_after_final_feedback_marker, 1)
        self.assertEqual(ref.timer_reentrancy_bounded, 1)
        self.assertEqual(ref.final_window_alive_after_samples, 1)
        self.assertEqual(ref.closes_normally, 1)

    def test_absence_flags_keep_deferred_systems_out(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage38_selected_attack_feedback_present_bridge_exe()
        lower = image.lower()

        for value in (
            ref.full_frame_byte_arrays_absent,
            ref.runtime_renderer_primitives,
            ref.wall_path_replayed,
            ref.flat_path_replayed,
            ref.impact_path_replayed,
            ref.death_path_replayed,
            ref.drop_path_replayed,
            ref.psprite_path_replayed,
            ref.projectiles_absent,
            ref.explosions_absent,
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
            ref.source_stage39_absent,
        ):
            self.assertEqual(value, 1)
        self.assertNotIn(b"source_stage39", lower)
        for forbidden in (
            b"projectile spawned",
            b"explosion spawned",
            b"infighting implemented",
            b"player death implemented",
            b"enemy kill drop implemented",
            b"generalized monster ai implemented",
            b"broad combat implemented",
            b"statusbar hud rebuild implemented",
            b"map progression implemented",
            b"menu system implemented",
            b"real audio playback implemented",
        ):
            self.assertNotIn(forbidden, lower)

    def test_stage38_does_not_rely_on_full_pre_rendered_frame_arrays_for_motion(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage38_selected_attack_feedback_present_bridge_exe()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertNotIn(b"stage38_frame_pixels", image)
        self.assertNotIn(b"stage38_copy_rendered_frame", image)
        self.assertIn(b"NOFULL38=1", image)
        self.assertIn(b"A_SPosAttack->S_StartSound", image)
        self.assertEqual(image.count(b"\xF3\xA5"), 0)

    def test_pinned_replay_preserves_stage36_visual_and_pickup_bridges(self) -> None:
        ref = self._ref()
        s36 = ref.stage36

        self.assertEqual(s36.signature, 397846180)
        self.assertEqual(stage.stage36.ref35_signature(s36), 3270148876)
        self.assertEqual(s36.stage34.signature, 4027590938)
        self.assertEqual(s36.stage34.stage33.signature, 1614948054)
        self.assertEqual(s36.stage34.stage33.stage32.signature, 533488475)
        self.assertEqual(s36.stage34.stage33.stage32.stage31.signature, 3593583171)
        self.assertGreater(s36.samples[-1].wall_pixels_drawn + s36.samples[-1].flat_pixels_drawn, 50000)
        self.assertGreater(s36.samples[-1].impact_pixels_drawn, 0)
        self.assertGreater(s36.samples[-1].death_pixels_drawn, 0)
        self.assertEqual(s36.samples[-1].drop_pixels_drawn, 0)
        self.assertGreater(s36.samples[-1].psprite_pixels_drawn, 1000)
        self.assertEqual((s36.pickup.removed_item, s36.pickup.item_present_after), (1, 0))

    def test_preserves_stage36_through_stage19_signatures(self) -> None:
        ref = self._ref()
        stage31_ref = ref.stage36.stage34.stage33.stage32.stage31
        stage29_ref = stage31_ref.stage30.stage29
        stage28_ref = stage29_ref.stage28

        self.assertEqual(ref.stage36.signature, 397846180)
        self.assertEqual(stage.stage36.ref35_signature(ref.stage36), 3270148876)
        self.assertEqual(ref.stage36.stage34.signature, 4027590938)
        self.assertEqual(ref.stage36.stage34.stage33.signature, 1614948054)
        self.assertEqual(ref.stage36.stage34.stage33.stage32.signature, 533488475)
        self.assertEqual(stage31_ref.signature, 3593583171)
        self.assertEqual(stage31_ref.stage30.signature, 3898523864)
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

    def test_executable_build_contains_stage38_markers_and_no_stage39_strings(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage38_selected_attack_feedback_present_bridge_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage38_selected_attack_feedback_present_bridge", image)
        self.assertIn(b"Selected Attack Feedback Present Bridge proof OK", image)
        self.assertIn(b"S38 ATTACK START STEP38=0", image)
        self.assertIn(b"SFX38=sfx_shotgn", image)
        self.assertIn(b"HP38=100->91", image)
        self.assertIn(b"DMG38=9", image)
        self.assertIn(f"S38SIG={ref.signature}".encode("ascii"), image)
        self.assertIn(b"S36SIG=397846180", image)
        self.assertIn(b"S19SIG=2088411722", image)
        self.assertNotIn(b"source_stage39", image.lower())

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage38_attack_feedback_and_distinct_signatures(self) -> None:
        ref = self._ref()
        exe_path = REPO_ROOT / "build" / "source_stage38_selected_attack_feedback_present_bridge.exe"
        stage.write_source_stage38_selected_attack_feedback_present_bridge_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, titles = collect_stage38_titles(process.pid, timeout_seconds=8.0)
            joined = "\n".join(titles)
            fb_values = {
                int(match.group(1))
                for title in titles
                for match in [re.search(r"(?:^| )FB38=(\d+)", title)]
                if match
            }

            self.assertIn("S38 ATTACK START STEP38=0", joined)
            self.assertIn("STEP38=1", joined)
            self.assertIn("STEP38=2", joined)
            self.assertIn("STEP38=3", joined)
            self.assertEqual(fb_values, {sample.framebuffer_signature for sample in ref.samples})
            self.assertGreaterEqual(len(fb_values), 2)
            self.assertIn("HP38=100->91", joined)
            self.assertIn("DMG38=9", joined)
            self.assertIn("HIT38=1", joined)
            self.assertIn("MISS38=2", joined)
            self.assertIn("SFX38=sfx_shotgn", joined)
            self.assertIn("SFXC38=1", joined)
            self.assertIn("SRC38=MT_SHOTGUY->P0", joined)
            self.assertIn("INV38=3", joined)
            self.assertIn("UPD38=3", joined)
            self.assertIn("PAINT38=3", joined)
            self.assertIn("PAF38=1", joined)
            self.assertIn(f"S38SIG={ref.signature}", joined)
            self.assertIn("S36SIG=397846180", joined)
            self.assertIn("S19SIG=2088411722", joined)
            self.assertIn("S39ABS=1", joined)
            time.sleep(0.35)
            self.assertIsNone(process.poll(), "stage38 exited before the stability observation window")
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
