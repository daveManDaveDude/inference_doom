import os
import re
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage41_statusbar_weapon_ammo_feedback_bridge as stage


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


def collect_stage41_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP41=3" in title and "S41SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage41 final title not reached; saw {titles!r}")


class SourceStage41StatusbarWeaponAmmoFeedbackBridgeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage41StatusbarWeaponAmmoFeedbackBridgeReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_statusbar_weapon_ammo_feedback_bridge_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_cover_status_feedback_sources(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}
        files = {entry[0] for entry in stage.SOURCE_TRACE}

        self.assertIn("ST_updateWidgets_stage41_compact_status_player_fields_debug", labels)
        self.assertIn("HU_Ticker_stage41_selected_pickup_message_debug", labels)
        self.assertIn("P_TouchSpecialThing_stage41_selected_shotgun_status_feedback_debug", labels)
        self.assertIn("P_DamageMobj_stage41_selected_player_status_feedback_debug", labels)
        self.assertIn("P_SetupPsprites_stage41_selected_weapon_pending_status_debug", labels)
        self.assertIn("V_DrawFilledBox_stage41_compact_status_strip_debug", labels)
        self.assertIn("stage41_status_present_bridge_preserves_stage40_debug", labels)
        for source in ("st_stuff.c", "hu_stuff.c", "p_inter.c", "p_pspr.c", "v_video.c", "i_video.c"):
            self.assertTrue(any(path.endswith(source) for path in files), source)

    def test_synthetic_selected_status_player_state_census(self) -> None:
        ref = self._ref()
        states = [sample.status for sample in ref.samples]

        self.assertEqual([s.health for s in states], [100, 91, 91])
        self.assertEqual([s.armor for s in states], [0, 0, 0])
        self.assertEqual([s.shell_ammo for s in states], [0, 4, 4])
        self.assertEqual([s.shotgun_owned for s in states], [0, 1, 1])
        self.assertEqual([s.pending_weapon for s in states], [stage.stage15.WP_PISTOL, stage.stage15.WP_SHOTGUN, stage.stage15.WP_SHOTGUN])
        self.assertEqual([s.message for s in states], ["", "GOTSHOTGUN", "GOTSHOTGUN"])
        self.assertEqual(ref.source_status_player_fields, 1)

    def test_synthetic_health_armor_damagecount_preserves_stage37_stage38_damage(self) -> None:
        ref = self._ref()
        attack = ref.stage40.stage39.stage38.attack

        self.assertEqual((attack.health_before, attack.health_after), (100, 91))
        self.assertEqual((attack.armor_before, attack.armor_after), (0, 0))
        self.assertEqual(attack.damagecount_after, 9)
        self.assertEqual([s.status.damagecount for s in ref.samples], [0, 9, 5])
        self.assertEqual(ref.source_damage_feedback_bridge, 1)
        self.assertEqual(ref.stage37_feedback_preserved, 1)

    def test_synthetic_shell_ammo_shotgun_owned_pending_weapon_preserves_stage36_pickup(self) -> None:
        ref = self._ref()
        pickup = ref.stage40.stage39.stage38.stage36.pickup

        self.assertEqual((pickup.ammo_before, pickup.ammo_after), (0, 4))
        self.assertEqual((pickup.weapon_owned_before, pickup.weapon_owned_after), (0, 1))
        self.assertEqual((pickup.pending_before, pickup.pending_after), (stage.stage15.WP_PISTOL, stage.stage15.WP_SHOTGUN))
        self.assertEqual((pickup.gave_ammo, pickup.gave_weapon, pickup.give_weapon_return), (1, 1, 1))
        self.assertEqual(ref.source_weapon_pending_bridge, 1)
        self.assertEqual(ref.stage36_pickup_preserved, 1)

    def test_synthetic_gotshotgun_message_bonuscount_and_pickup_flash(self) -> None:
        ref = self._ref()

        self.assertEqual([s.status.message or "NONE" for s in ref.samples], ["NONE", "GOTSHOTGUN", "GOTSHOTGUN"])
        self.assertEqual([s.status.bonuscount for s in ref.samples], [0, 6, 4])
        self.assertEqual([s.status.pickup_flash for s in ref.samples], [0, 6, 6])
        self.assertEqual(ref.source_hu_message_bridge, 1)
        self.assertEqual(ref.source_pickup_feedback_bridge, 1)

    def test_synthetic_deferred_sound_markers(self) -> None:
        ref = self._ref()

        self.assertEqual([(s.status.sfx_wpnup, s.status.sfx_shotgn, s.status.sfx_firsht) for s in ref.samples], [(0, 0, 0), (1, 1, 0), (1, 1, 1)])
        self.assertEqual(ref.stage40.stage39.stage38.stage36.pickup.sound, "sfx_wpnup")
        self.assertEqual(ref.stage40.stage39.stage38.attack.sound, "sfx_shotgn")
        self.assertEqual(ref.stage40.stage39.projectile.sound, "sfx_firsht")

    def test_synthetic_compact_status_strip_draw_bounds_and_framebuffer_ownership(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.compact_status_strip_drawn, 1)
        self.assertEqual(ref.status_draw_bounds_checked, 1)
        for sample in ref.samples:
            self.assertGreaterEqual(sample.command_count, 10)
            self.assertGreater(sample.status_pixels_drawn, 0)
            self.assertNotEqual(sample.pre_status_framebuffer_signature, sample.framebuffer_signature)
            for command in sample.commands:
                self.assertGreaterEqual(command.x, 0)
                self.assertGreaterEqual(command.y, stage.STATUS_STRIP_Y)
                self.assertLessEqual(command.x + command.width, stage.FRAMEBUFFER_WIDTH)
                self.assertLessEqual(command.y + command.height, stage.FRAMEBUFFER_HEIGHT)
                self.assertEqual(command.row_advance, (stage.FRAMEBUFFER_WIDTH - command.width) * 4)

    def test_synthetic_status_draw_ordering_after_world_vissprite_psprite_feedback_and_projectile_state(self) -> None:
        ref = self._ref()

        for sample in ref.samples:
            self.assertLess(sample.world_vissprite_sequence, sample.psprite_sequence)
            self.assertLess(sample.psprite_sequence, sample.feedback_sequence)
            self.assertLess(sample.feedback_sequence, sample.projectile_state_sequence)
            self.assertLess(sample.projectile_state_sequence, sample.status_sequence)
            self.assertLess(sample.status_sequence, sample.signature_sequence)
            self.assertLess(sample.signature_sequence, sample.present_sequence)
        self.assertEqual(ref.status_draw_after_world_vissprite_and_psprite, 1)
        self.assertEqual(ref.status_draw_after_feedback_and_projectile_state, 1)

    def test_synthetic_invalidate_update_paint_ordering_preserves_stage40_behavior(self) -> None:
        ref = self._ref()

        self.assertEqual((ref.timer_samples, ref.invalidate_calls, ref.update_window_calls, ref.expected_paint_calls), (3, 3, 3, 3))
        self.assertEqual(ref.paint_after_final_status, 1)
        self.assertEqual((ref.stage40.invalidate_calls, ref.stage40.update_window_calls, ref.stage40.expected_paint_calls), (3, 3, 3))
        self.assertEqual(ref.stage40.paint_after_final_vissprite, 1)
        self.assertEqual(ref.stage38_present_preserved, 1)

    def test_synthetic_selected_status_state_signature_contribution(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.signature, 951695045)
        self.assertEqual(ref.state_signature, 157977072)
        self.assertEqual([s.framebuffer_signature for s in ref.samples], [2820600565, 3443819349, 1672331767])
        self.assertEqual([s.selected_status_state_signature for s in ref.samples], [1548266261, 4244284538, 3218471217])
        self.assertEqual(ref.distinct_selected_status_signatures, 3)
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)
        self.assertEqual(ref.status_contribution_signatures, 3)

    def test_stage41_does_not_rely_on_full_pre_rendered_frame_arrays_for_status_motion(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage41_statusbar_weapon_ammo_feedback_bridge_exe()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertEqual(ref.runtime_renderer_primitives, 1)
        self.assertIn(b"NOFULL41=1", image)
        self.assertIn(b"compact status strip", image)
        self.assertNotIn(b"stage41_frame_pixels", image)
        self.assertNotIn(b"stage41_copy_rendered_frame", image)
        self.assertEqual(image.count(b"\xF3\xA5"), 0)

    def test_absence_flags_keep_broad_ui_audio_inventory_and_combat_systems_out(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage41_statusbar_weapon_ammo_feedback_bridge_exe()
        lower = image.lower()

        for value in (
            ref.broad_hud_statusbar_rebuild_absent,
            ref.classic_full_statusbar_layout_absent,
            ref.face_animation_absent,
            ref.automap_absent,
            ref.menu_absent,
            ref.intermission_absent,
            ref.save_load_absent,
            ref.networking_absent,
            ref.music_absent,
            ref.real_audio_absent,
            ref.generalized_inventory_absent,
            ref.generalized_item_traversal_absent,
            ref.generalized_combat_absent,
            ref.broad_monster_ai_absent,
            ref.player_death_absent,
            ref.enemy_kill_drop_absent,
            ref.broad_all_map_sprite_traversal_absent,
            ref.generalized_projectile_manager_absent,
            ref.explosions_absent,
            ref.radius_damage_absent,
            ref.splash_damage_absent,
            ref.infighting_absent,
            ref.map_progression_absent,
            ref.source_stage42_absent,
        ):
            self.assertEqual(value, 1)
        self.assertNotIn(b"source_stage42", lower)
        for forbidden in (
            b"classic full statusbar implemented",
            b"face animation implemented",
            b"automap implemented",
            b"menu system implemented",
            b"intermission implemented",
            b"save load implemented",
            b"networking implemented",
            b"real audio playback implemented",
            b"generalized inventory implemented",
            b"generalized item traversal implemented",
            b"generalized monster ai implemented",
            b"player death implemented",
            b"enemy kill drop implemented",
            b"generalized projectile manager implemented",
            b"explosion spawned",
            b"radius damage implemented",
            b"splash damage implemented",
            b"infighting implemented",
            b"map progression implemented",
        ):
            self.assertNotIn(forbidden, lower)

    def test_runtime_command_state_table_selection(self) -> None:
        ref = self._ref()
        image = stage.build_source_stage41_statusbar_weapon_ammo_feedback_bridge_exe()

        self.assertIn(b"ST_updateWidgets/HU_Ticker/P_TouchSpecialThing", image)
        self.assertIn(b"STRIP41=", image)
        self.assertEqual(
            [[command.field for command in sample.commands] for sample in ref.samples],
            [
                ["status_background", "health", "damagecount", "armor", "shell_ammo", "shotgun_owned", "pending_weapon", "message_empty", "bonuscount", "damage_flash", "sfx_wpnup", "sfx_shotgn", "sfx_firsht"],
                ["status_background", "health", "damagecount", "armor", "shell_ammo", "shotgun_owned", "pending_weapon", "message_GOTSHOTGUN", "bonuscount", "damage_flash", "sfx_wpnup", "sfx_shotgn", "sfx_firsht"],
                ["status_background", "health", "damagecount", "armor", "shell_ammo", "shotgun_owned", "pending_weapon", "message_GOTSHOTGUN", "bonuscount", "damage_flash", "sfx_wpnup", "sfx_shotgn", "sfx_firsht"],
            ],
        )
        self.assertEqual([s.command_count for s in ref.samples], [13, 13, 13])
        self.assertGreater(len({tuple((c.field, c.width, c.color) for c in s.commands) for s in ref.samples}), 1)

    def test_preserves_stage40_through_stage19_signatures_and_paths(self) -> None:
        ref = self._ref()
        ref40 = ref.stage40
        ref39 = ref40.stage39
        ref38 = ref39.stage38
        s29 = ref38.stage29
        s36 = ref38.stage36
        s31 = s36.stage34.stage33.stage32.stage31

        self.assertEqual(ref.stage40_vissprite_preserved, 1)
        self.assertEqual(ref.stage39_projectile_state_preserved, 1)
        self.assertEqual(ref.stage31_wall_flat_preserved, 1)
        self.assertEqual(ref.stage32_psprite_preserved, 1)
        self.assertEqual(ref.stage33_impact_preserved, 1)
        self.assertEqual(ref.stage34_death_preserved, 1)
        self.assertEqual(ref.stage35_drop_preserved, 1)
        self.assertEqual(ref.stage36_pickup_preserved, 1)
        self.assertEqual(ref.stage37_feedback_preserved, 1)
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

    def test_build_output_contains_stage41_markers_and_no_stage42_strings(self) -> None:
        output = REPO_ROOT / "build" / "source_stage41_statusbar_weapon_ammo_feedback_bridge.exe"
        output.parent.mkdir(parents=True, exist_ok=True)
        image = stage.build_source_stage41_statusbar_weapon_ammo_feedback_bridge_exe()
        output.write_bytes(image)

        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 100_000)
        self.assertIn(b"source_stage41_statusbar_weapon_ammo_feedback_bridge", image)
        self.assertIn(b"S41SIG=951695045", image)
        self.assertIn(b"STATE41=157977072", image)
        self.assertIn(b"MSG41=GOTSHOTGUN", image)
        self.assertIn(b"SFX41=sfx_wpnup:1,sfx_shotgn:1,sfx_firsht:1", image)
        self.assertIn(b"INV41=3 UPD41=3 PAINT41=3 PAF41=1", image)
        self.assertIn(b"INV40=3 UPD40=3 PAINT40=3 PAF40=1", image)
        self.assertNotIn(b"source_stage42", image.lower())

    @unittest.skipUnless(os.name == "nt", "Win32 GUI smoke test requires Windows")
    def test_smoke_executable_launches_reports_status_samples_and_closes(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        output = REPO_ROOT / "build" / "source_stage41_statusbar_weapon_ammo_feedback_bridge.exe"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(stage.build_source_stage41_statusbar_weapon_ammo_feedback_bridge_exe())

        proc = subprocess.Popen([str(output)], cwd=REPO_ROOT)
        try:
            hwnd, titles = collect_stage41_titles(proc.pid)
            final = titles[-1]
            self.assertNotEqual(hwnd, 0)
            self.assertIn("STEP41=3", final)
            self.assertIn("S41SIG=951695045", final)
            self.assertIn("STATE41=157977072", final)
            self.assertIn("HP41=91", final)
            self.assertIn("SHELL41=4", final)
            self.assertIn("WOWN41=1", final)
            self.assertIn("PEND41=2", final)
            self.assertIn("MSG41=GOTSHOTGUN", final)
            self.assertIn("SFX41=sfx_wpnup:1,sfx_shotgn:1,sfx_firsht:1", final)
            self.assertIn("PATCH40=BAL1", final)
            self.assertIn("MISS39=MT_TROOPSHOT", final)
            self.assertIn("INV41=3 UPD41=3 PAINT41=3 PAF41=1", final)
            self.assertIn("INV40=3 UPD40=3 PAINT40=3 PAF40=1", final)
            self.assertIn("S42ABS=1", final)
            fb_values = {
                int(match.group(1))
                for title in titles
                for match in re.finditer(r"FB41=(\d+)", title)
            }
            state_values = {
                int(match.group(1))
                for title in titles
                for match in re.finditer(r"SSTATE41=(\d+)", title)
            }
            self.assertGreaterEqual(len(fb_values), 2)
            self.assertGreaterEqual(len(state_values), 2)
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
