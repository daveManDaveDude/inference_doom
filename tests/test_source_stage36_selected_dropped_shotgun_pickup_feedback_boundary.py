import os
import re
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage36_selected_dropped_shotgun_pickup_feedback_boundary as stage


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


def collect_stage36_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP36=3" in title and "S36SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage36 final title not reached; saw {titles!r}")


class SourceStage36SelectedDroppedShotgunPickupFeedbackBoundaryTests(unittest.TestCase):
    def _ref(self) -> stage.Stage36SelectedDroppedShotgunPickupFeedbackBoundaryReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_selected_dropped_shotgun_pickup_feedback_boundary_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_name_selected_pickup_sources(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("P_TouchSpecialThing_stage36_selected_dropped_shotgun_feedback_debug", labels)
        self.assertIn("P_GiveWeapon_stage36_selected_dropped_shotgun_debug", labels)
        self.assertIn("weaponinfo_stage36_selected_shotgun_pickup_debug", labels)
        self.assertIn("P_RemoveMobj_stage36_selected_dropped_shotgun_debug", labels)
        self.assertIn("S_StartSound_stage36_selected_wpnup_boundary_debug", labels)

    def test_synthetic_frame_step_ordering_is_clear_wall_impact_death_optional_drop_psprite_present(self) -> None:
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
                    s.present_sequence,
                )
                for s in ref.samples
            ],
            [(1, 2, 3, 4, 5, 6, 7), (8, 9, 10, 11, 12, 13, 14), (15, 16, 17, 18, 19, 20, 21)],
        )

    def test_synthetic_selected_p_touch_specialthing_z_live_and_sprite_gates(self) -> None:
        flags = stage.stage13.MF_SPECIAL | stage.stage13.MF_DROPPED

        accepted = stage.p_touch_special_thing_stage36_selected(special_flags=flags)
        high = stage.p_touch_special_thing_stage36_selected(
            special_flags=flags,
            special_z=57 * stage.FRACUNIT,
            toucher_height=56 * stage.FRACUNIT,
        )
        low = stage.p_touch_special_thing_stage36_selected(special_flags=flags, special_z=-9 * stage.FRACUNIT)
        dead = stage.p_touch_special_thing_stage36_selected(special_flags=flags, toucher_health=0)
        wrong_sprite = stage.p_touch_special_thing_stage36_selected(special_flags=flags, special_sprite_name="CLIP")

        self.assertEqual((accepted.z_reach_passed, accepted.live_toucher_passed, accepted.sprite_dispatch_passed), (1, 1, 1))
        self.assertEqual((high.z_reach_passed, high.give_weapon_return), (0, 0))
        self.assertEqual((low.z_reach_passed, low.give_weapon_return), (0, 0))
        self.assertEqual((dead.live_toucher_passed, dead.give_weapon_return), (0, 0))
        self.assertEqual((wrong_sprite.sprite_dispatch_passed, wrong_sprite.give_weapon_return), (0, 0))

    def test_synthetic_dropped_shotgun_p_giveweapon_return_cases(self) -> None:
        max_shell = stage.stage15.MAXAMMO[stage.stage15.AM_SHELL]

        ammo_only = stage.p_give_weapon_stage36_selected(owned_before=True, ammo_before=0)
        weapon_only = stage.p_give_weapon_stage36_selected(owned_before=False, ammo_before=max_shell)
        both = stage.p_give_weapon_stage36_selected(owned_before=False, ammo_before=0)
        neither = stage.p_give_weapon_stage36_selected(owned_before=True, ammo_before=max_shell)

        self.assertEqual(ammo_only, (True, False, True, 4, True, stage.stage15.WP_PISTOL))
        self.assertEqual(weapon_only, (False, True, True, max_shell, True, stage.stage15.WP_SHOTGUN))
        self.assertEqual(both, (True, True, True, 4, True, stage.stage15.WP_SHOTGUN))
        self.assertEqual(neither, (False, False, False, max_shell, True, stage.stage15.WP_PISTOL))

    def test_synthetic_selected_pickup_feedback_message_sound_bonus_and_removal(self) -> None:
        ref = self._ref()
        pickup = ref.pickup

        self.assertEqual((pickup.special_sprite_name, pickup.dropped_weapon), ("SHOT", 1))
        self.assertEqual((pickup.weapon, pickup.ammo_type, pickup.ammo_clip_amount), (stage.stage15.WP_SHOTGUN, stage.stage15.AM_SHELL, 4))
        self.assertEqual((pickup.ammo_before, pickup.ammo_after), (0, 4))
        self.assertEqual((pickup.weapon_owned_before, pickup.weapon_owned_after), (0, 1))
        self.assertEqual((pickup.pending_before, pickup.pending_after), (stage.stage15.WP_PISTOL, stage.stage15.WP_SHOTGUN))
        self.assertEqual((pickup.gave_ammo, pickup.gave_weapon, pickup.give_weapon_return), (1, 1, 1))
        self.assertEqual((pickup.message, pickup.sound, pickup.sound_events), ("GOTSHOTGUN", "sfx_wpnup", 1))
        self.assertEqual((pickup.bonuscount_before, pickup.bonuscount_after), (0, stage.stage15.BONUSADD))
        self.assertEqual((pickup.removed_item, pickup.item_present_before, pickup.item_present_after), (1, 1, 0))
        self.assertEqual(pickup.respawn_queue_events, 0)

    def test_synthetic_runtime_command_table_selection_suppresses_drop_after_pickup(self) -> None:
        ref = self._ref()

        self.assertEqual([s.drop_state_name for s in ref.samples], ["NONE", "S_SHOT", "REMOVED"])
        self.assertEqual([len(s.drop_commands) for s in ref.samples], [0, 44, 0])
        self.assertEqual([s.drop_pixels_drawn for s in ref.samples], [0, 284, 0])
        self.assertEqual(ref.drop_path_replayed, 1)
        self.assertEqual(ref.samples[1].drop_framebuffer_signature, 3057214504)
        self.assertEqual(ref.samples[2].drop_framebuffer_signature, ref.samples[2].death_framebuffer_signature)

    def test_synthetic_framebuffer_signatures_prove_pickup_item_removal_contribution(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.signature, 397846180)
        self.assertEqual([s.base_framebuffer_signature for s in ref.samples], [2926869513, 622680457, 1677820087])
        self.assertEqual([s.impact_framebuffer_signature for s in ref.samples], [2926869513, 330358001, 1300993588])
        self.assertEqual([s.death_framebuffer_signature for s in ref.samples], [2926869513, 1191322670, 2513680424])
        self.assertEqual([s.drop_framebuffer_signature for s in ref.samples], [2926869513, 3057214504, 2513680424])
        self.assertEqual([s.framebuffer_signature for s in ref.samples], [2997224612, 1668066382, 1194192847])
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)
        self.assertNotEqual(ref.samples[1].framebuffer_signature, ref.samples[2].framebuffer_signature)
        self.assertEqual(ref.samples[2].framebuffer_signature, 1194192847)

    def test_absence_flags_keep_broad_deferred_systems_and_stage37_out(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage36_selected_dropped_shotgun_pickup_feedback_boundary_exe()
        lower = image.lower()

        for value in (
            ref.full_frame_byte_arrays_absent,
            ref.runtime_renderer_primitives,
            ref.wall_path_replayed,
            ref.flat_path_replayed,
            ref.death_or_pain_path_replayed,
            ref.drop_path_replayed,
            ref.psprite_path_replayed,
            ref.selected_item_pickup_boundary,
            ref.selected_touch_special_boundary,
            ref.selected_give_weapon_boundary,
            ref.selected_ammo_weapon_grant_boundary,
            ref.selected_pickup_message_boundary,
            ref.selected_item_removal_boundary,
            ref.respawn_queue_absent,
            ref.broad_inventory_statusbar_absent,
            ref.generalized_item_traversal_absent,
            ref.projectiles_absent,
            ref.explosions_absent,
            ref.broad_ai_absent,
            ref.generalized_combat_absent,
            ref.ui_systems_absent,
            ref.real_audio_absent,
            ref.source_stage37_absent,
        ):
            self.assertEqual(value, 1)
        self.assertNotIn(b"source_stage37", lower)
        for forbidden in (
            b"deathmatch weapon stay implemented",
            b"respawn queue implemented",
            b"generalized item traversal implemented",
            b"broad inventory implemented",
            b"full hud implemented",
            b"projectile spawned",
            b"explosion spawned",
            b"monster ai implemented",
            b"map progression implemented",
            b"menu system implemented",
            b"real audio playback implemented",
        ):
            self.assertNotIn(forbidden, lower)

    def test_stage36_does_not_rely_on_full_pre_rendered_frame_arrays_for_motion(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage36_selected_dropped_shotgun_pickup_feedback_boundary_exe()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertNotIn(b"stage36_frame_pixels", image)
        self.assertNotIn(b"stage36_copy_rendered_frame", image)
        self.assertIn(b"Selected impact/death/drop visual log", image)
        self.assertIn(b"NOFULL36=1", image)
        self.assertIn(b"R_DrawMaskedColumn-shaped commands", image)
        self.assertEqual(image.count(b"\xF3\xA5"), 0)
        command_bytes = sum(
            len(s.impact_commands) * stage.COMMAND_RECORD_SIZE
            + len(s.death_commands) * stage.COMMAND_RECORD_SIZE
            + len(s.drop_commands) * stage.COMMAND_RECORD_SIZE
            + len(s.psprite_commands) * stage.COMMAND_RECORD_SIZE
            + len(ref.stage34.stage33.stage32.stage31.samples[i].wall_commands) * stage.COMMAND_RECORD_SIZE
            + len(ref.stage34.stage33.stage32.stage31.samples[i].flat_spans) * stage.stage31.SPAN_RECORD_SIZE
            for i, s in enumerate(ref.samples)
        )
        self.assertLess(command_bytes, stage.FRAMEBUFFER_BYTES * len(ref.samples) // 8)

    def test_pinned_replay_preserves_visual_bridges_and_pickup_state(self) -> None:
        ref = self._ref()

        self.assertEqual(stage.ref35_signature(ref), 3270148876)
        self.assertEqual(ref.stage34.signature, 4027590938)
        self.assertEqual(ref.stage34.stage33.signature, 1614948054)
        self.assertEqual(ref.stage34.stage33.stage32.signature, 533488475)
        self.assertEqual(ref.stage34.stage33.stage32.stage31.signature, 3593583171)
        self.assertGreater(ref.samples[-1].wall_pixels_drawn + ref.samples[-1].flat_pixels_drawn, 50000)
        self.assertGreater(ref.samples[-1].impact_pixels_drawn, 0)
        self.assertGreater(ref.samples[-1].death_pixels_drawn, 0)
        self.assertEqual(ref.samples[-1].drop_pixels_drawn, 0)
        self.assertGreater(ref.samples[-1].psprite_pixels_drawn, 1000)

    def test_preserves_stage35_through_stage19_signatures(self) -> None:
        ref = self._ref()
        stage31_ref = ref.stage34.stage33.stage32.stage31
        stage29_ref = stage31_ref.stage30.stage29
        stage28_ref = stage29_ref.stage28

        self.assertEqual(stage.ref35_signature(ref), 3270148876)
        self.assertEqual(ref.stage34.signature, 4027590938)
        self.assertEqual(ref.stage34.stage33.signature, 1614948054)
        self.assertEqual(ref.stage34.stage33.stage32.signature, 533488475)
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

    def test_executable_build_contains_stage36_markers_and_no_stage37_strings(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage36_selected_dropped_shotgun_pickup_feedback_boundary_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage36_selected_dropped_shotgun_pickup_feedback_boundary", image)
        self.assertIn(b"Selected dropped shotgun pickup feedback boundary proof OK", image)
        self.assertIn(b"S36 PICKUP START STEP36=0", image)
        self.assertIn(b"DROP36=S_SHOT", image)
        self.assertIn(b"DROP36=REMOVED", image)
        self.assertIn(b"MSG36=GOTSHOTGUN", image)
        self.assertIn(b"SFX36=sfx_wpnup", image)
        self.assertIn(f"S36SIG={ref.signature}".encode("ascii"), image)
        self.assertIn(b"S35SIG=3270148876", image)
        self.assertIn(b"S34SIG=4027590938", image)
        self.assertIn(b"S19SIG=2088411722", image)
        self.assertNotIn(b"source_stage37", image.lower())

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage36_pickup_feedback_and_distinct_signatures(self) -> None:
        ref = self._ref()
        exe_path = REPO_ROOT / "build" / "source_stage36_selected_dropped_shotgun_pickup_feedback_boundary.exe"
        stage.write_source_stage36_selected_dropped_shotgun_pickup_feedback_boundary_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, titles = collect_stage36_titles(process.pid, timeout_seconds=8.0)
            joined = "\n".join(titles)
            fb_values = {
                int(match.group(1))
                for title in titles
                for match in [re.search(r"(?:^| )FB36=(\d+)", title)]
                if match
            }

            self.assertIn("S36 PICKUP START STEP36=0", joined)
            self.assertIn("STEP36=1", joined)
            self.assertIn("STEP36=2", joined)
            self.assertIn("STEP36=3", joined)
            self.assertEqual(fb_values, {sample.framebuffer_signature for sample in ref.samples})
            self.assertGreaterEqual(len(fb_values), 2)
            self.assertIn("DROP36=S_SHOT", joined)
            self.assertIn("DROP36=REMOVED", joined)
            self.assertIn("DRC36=0", joined)
            self.assertIn("PICK36=1", joined)
            self.assertIn("ITEM36=0", joined)
            self.assertIn("SHELL36=4", joined)
            self.assertIn("WOWN36=1", joined)
            self.assertIn("PEND36=2", joined)
            self.assertIn("MSG36=GOTSHOTGUN", joined)
            self.assertIn("SFX36=sfx_wpnup", joined)
            self.assertIn("SFXC36=1", joined)
            self.assertIn("BONUS36=6", joined)
            self.assertIn(f"S36SIG={ref.signature}", joined)
            self.assertIn("S35SIG=3270148876", joined)
            self.assertIn("S19SIG=2088411722", joined)
            self.assertIn("S37ABS=1", joined)
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
