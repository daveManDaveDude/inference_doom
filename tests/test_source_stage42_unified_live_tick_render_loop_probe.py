import os
import re
import subprocess
import time
import unittest
from functools import lru_cache
from pathlib import Path

from tools import emit_source_stage42_unified_live_tick_render_loop_probe as stage


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


@lru_cache(maxsize=1)
def built_stage42_image() -> bytes:
    return stage.build_source_stage42_unified_live_tick_render_loop_probe_exe()


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


def collect_stage42_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP42=3" in title and "S42SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage42 final title not reached; saw {titles!r}")


def close_window(hwnd: int) -> None:
    import ctypes

    if hwnd:
        ctypes.WinDLL("user32", use_last_error=True).PostMessageW(hwnd, 0x0010, 0, 0)


class SourceStage42UnifiedLiveTickRenderLoopProbeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage42UnifiedLiveTickRenderLoopProbeReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_unified_live_tick_render_loop_probe_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_cover_unified_loop_sources(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}
        files = {entry[0] for entry in stage.SOURCE_TRACE}

        for label in (
            "D_DoomLoop_stage42_selected_timer_replay_boundary_debug",
            "G_Ticker_stage42_selected_ticcmd_ownership_debug",
            "P_Ticker_stage42_selected_update_order_debug",
            "P_PlayerThink_stage42_selected_player_command_update_debug",
            "P_MovePsprites_stage42_selected_weapon_state_update_debug",
            "P_MobjThinker_stage42_selected_mobj_projectile_update_debug",
            "P_Enemy_stage42_selected_attack_projectile_boundaries_debug",
            "R_RenderPlayerView_stage42_unified_order_debug",
            "ST_Ticker_stage42_compact_status_after_gameplay_debug",
            "HU_Ticker_stage42_selected_message_after_gameplay_debug",
            "P_Inter_stage42_selected_pickup_damage_feedback_debug",
            "V_DrawBlock_stage42_runtime_status_present_debug",
            "I_Video_stage42_invalidate_update_paint_debug",
        ):
            self.assertIn(label, labels)
        for source in (
            "d_loop.c",
            "g_game.c",
            "p_tick.c",
            "p_user.c",
            "p_pspr.c",
            "p_mobj.c",
            "p_enemy.c",
            "r_main.c",
            "st_stuff.c",
            "hu_stuff.c",
            "p_inter.c",
            "v_video.c",
            "i_video.c",
        ):
            self.assertTrue(any(path.endswith(source) for path in files), source)

    def test_synthetic_selected_unified_loop_state_census(self) -> None:
        ref = self._ref()

        self.assertEqual([sample.step for sample in ref.samples], [1, 2, 3])
        self.assertEqual([sample.tic for sample in ref.samples], [0, 4, 7])
        self.assertEqual(ref.deterministic_ticcmd_intake, 1)
        self.assertEqual(ref.selected_g_ticker_ownership, 1)
        self.assertEqual(ref.selected_p_ticker_ordering, 1)
        self.assertEqual(ref.selected_player_movement_update, 1)
        self.assertEqual(ref.selected_pickup_damage_projectile_update, 1)
        self.assertEqual([sample.command_record_count for sample in ref.samples], [1, 1, 1])
        self.assertEqual([sample.status_command_count for sample in ref.samples], [13, 13, 13])

    def test_synthetic_deterministic_ticcmd_intake(self) -> None:
        ref = self._ref()
        commands = [sample.ticcmd for sample in ref.samples]

        self.assertEqual([(c.forwardmove, c.sidemove, c.angleturn, c.buttons) for c in commands], [(0, 0, 0, 0), (14, 0, 96, 0), (8, -5, -32, 0)])
        self.assertEqual([c.source_index for c in commands], [0, 1, 2])
        self.assertEqual(len({c.consistency for c in commands}), 3)
        self.assertTrue(all("deterministic ticcmd table" in c.source_marker for c in commands))

    def test_synthetic_g_ticker_p_ticker_update_ordering(self) -> None:
        ref = self._ref()

        for sample in ref.samples:
            self.assertLess(sample.start_tic_sequence, sample.ticcmd_sequence)
            self.assertLess(sample.ticcmd_sequence, sample.g_ticker_sequence)
            self.assertLess(sample.g_ticker_sequence, sample.p_ticker_sequence)
            self.assertLess(sample.p_ticker_sequence, sample.player_update_sequence)
            self.assertLess(sample.player_update_sequence, sample.psprite_weapon_update_sequence)
            self.assertLess(sample.psprite_weapon_update_sequence, sample.pickup_damage_projectile_sequence)

    def test_synthetic_selected_player_weapon_status_progression_preserves_stage41(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.stage41.signature, 951695045)
        self.assertEqual(ref.stage41.state_signature, 157977072)
        self.assertEqual([s.player.health for s in ref.samples], [100, 91, 91])
        self.assertEqual([s.player.shell_ammo for s in ref.samples], [0, 4, 4])
        self.assertEqual([s.player.shotgun_owned for s in ref.samples], [0, 1, 1])
        self.assertEqual([s.player.pending_weapon for s in ref.samples], [stage.stage15.WP_PISTOL, stage.stage15.WP_SHOTGUN, stage.stage15.WP_SHOTGUN])
        self.assertEqual([s.player.ready_weapon for s in ref.samples], [stage.stage15.WP_PISTOL, stage.stage15.WP_PISTOL, stage.stage15.WP_SHOTGUN])
        self.assertEqual([s.player.message or "NONE" for s in ref.samples], ["NONE", "GOTSHOTGUN", "GOTSHOTGUN"])
        self.assertEqual([s.player.psprite_state_name for s in ref.samples], ["S_SGUN", "S_SGUN3", "S_SGUN4"])

    def test_synthetic_selected_mobj_projectile_progression_preserves_stage39_stage40(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.stage40_vissprite_preserved, 1)
        self.assertEqual(ref.stage39_projectile_state_preserved, 1)
        self.assertEqual(ref.stage41.stage40.signature, 2737672056)
        self.assertEqual(ref.stage41.stage40.state_signature, 268409133)
        self.assertEqual(ref.stage41.stage40.stage39.signature, 3469618451)
        self.assertEqual(ref.stage41.stage40.stage39.projectile.state_signature, 1403583302)
        self.assertEqual([s.mobj.enemy_type_name for s in ref.samples], ["MT_TROOP", "MT_TROOP", "MT_TROOP"])
        self.assertEqual([s.mobj.projectile_type_name for s in ref.samples], ["MT_TROOPSHOT", "MT_TROOPSHOT", "MT_TROOPSHOT"])
        self.assertEqual([s.mobj.projectile_present for s in ref.samples], [0, 1, 1])
        self.assertEqual([s.mobj.projectile_tics for s in ref.samples], [0, 4, 3])
        self.assertEqual([s.mobj.dropped_shotgun_present for s in ref.samples], [1, 0, 0])
        self.assertEqual([s.mobj.dropped_shotgun_removed for s in ref.samples], [0, 1, 1])
        self.assertEqual([s.world_vissprite_state_signature for s in ref.samples], [1957020629, 3758004534, 1436017657])

    def test_synthetic_status_feedback_after_gameplay_and_after_world_psprite_draws(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.status_after_gameplay_mutation, 1)
        self.assertEqual(ref.status_draw_after_world_vissprite_and_psprite, 1)
        self.assertEqual(ref.status_draw_after_feedback_and_projectile_state, 1)
        for sample in ref.samples:
            self.assertLess(sample.pickup_damage_projectile_sequence, sample.clear_sequence)
            self.assertLess(sample.world_vissprite_sequence, sample.psprite_sequence)
            self.assertLess(sample.psprite_sequence, sample.feedback_sequence)
            self.assertLess(sample.feedback_sequence, sample.projectile_state_sequence)
            self.assertLess(sample.projectile_state_sequence, sample.status_sequence)
            self.assertLess(sample.status_sequence, sample.signature_sequence)
            self.assertLess(sample.signature_sequence, sample.present_sequence)

    def test_synthetic_clear_wallflat_vissprite_psprite_status_signature_present_ordering(self) -> None:
        ref = self._ref()

        for sample in ref.samples:
            self.assertLess(sample.clear_sequence, sample.wall_flat_sequence)
            self.assertLess(sample.wall_flat_sequence, sample.impact_sequence)
            self.assertLess(sample.impact_sequence, sample.death_sequence)
            self.assertLess(sample.death_sequence, sample.drop_sequence)
            self.assertLess(sample.drop_sequence, sample.world_vissprite_sequence)
            self.assertLess(sample.world_vissprite_sequence, sample.psprite_sequence)
            self.assertLess(sample.status_sequence, sample.present_sequence)

    def test_synthetic_invalidate_update_present_and_paint_after_final_sample(self) -> None:
        ref = self._ref()

        self.assertEqual((ref.timer_samples, ref.invalidate_calls, ref.update_window_calls, ref.expected_paint_calls), (3, 3, 3, 3))
        self.assertEqual(ref.paint_after_final_unified_sample, 1)
        self.assertEqual(ref.final_window_alive_after_samples, 1)
        self.assertEqual(ref.closes_normally, 1)
        self.assertEqual((ref.stage41.invalidate_calls, ref.stage41.update_window_calls, ref.stage41.expected_paint_calls), (3, 3, 3))
        self.assertEqual(ref.stage38_present_preserved, 1)

    def test_synthetic_selected_unified_loop_state_signature_contribution(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.signature, 2427416971)
        self.assertEqual(ref.state_signature, 2148021159)
        self.assertEqual([s.unified_loop_state_signature for s in ref.samples], [1903094291, 1130420740, 3331619657])
        self.assertEqual([s.framebuffer_signature for s in ref.samples], [2820600565, 3443819349, 1672331767])
        self.assertEqual([s.status_state_signature for s in ref.samples], [1548266261, 4244284538, 3218471217])
        self.assertEqual(ref.distinct_unified_loop_state_signatures, 3)
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)

    def test_synthetic_compact_runtime_command_state_table_selection(self) -> None:
        ref = self._ref()
        image = built_stage42_image()

        self.assertIn(b"source_stage42_unified_live_tick_render_loop_probe", image)
        self.assertIn(b"CMD42=F14/S0/A96/B0", image)
        self.assertIn(b"ULSTATE42=3331619657", image)
        self.assertIn(b"NOFULL42=1", image)
        self.assertEqual([s.command_record_count for s in ref.samples], [1, 1, 1])
        self.assertEqual(len({(s.player.x, s.player.y, s.player.angle) for s in ref.samples}), 3)

    def test_no_full_prerendered_framebuffer_byte_arrays(self) -> None:
        ref = self._ref()
        image = built_stage42_image()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertEqual(ref.runtime_renderer_primitives, 1)
        self.assertNotIn(b"stage42_frame_pixels", image)
        self.assertNotIn(b"stage42_copy_rendered_frame", image)
        self.assertEqual(image.count(b"\xF3\xA5"), 0)

    def test_deferred_system_absence_flags_remain_set(self) -> None:
        ref = self._ref()
        lower = built_stage42_image().lower()

        for value in (
            ref.live_input_absent,
            ref.generalized_thinkers_absent,
            ref.generalized_collision_absent,
            ref.generalized_projectile_manager_absent,
            ref.explosions_absent,
            ref.radius_damage_absent,
            ref.splash_damage_absent,
            ref.broad_monster_ai_absent,
            ref.generalized_combat_absent,
            ref.broad_inventory_absent,
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
            ref.mixer_device_playback_absent,
            ref.map_progression_absent,
            ref.infighting_absent,
            ref.player_death_absent,
            ref.enemy_kill_drop_absent,
            ref.broad_all_map_sprite_traversal_absent,
            ref.source_stage43_absent,
        ):
            self.assertEqual(value, 1)
        self.assertNotIn(b"source_stage43", lower)
        for forbidden in (
            b"live keyboard input implemented",
            b"live mouse input implemented",
            b"generalized thinker implemented",
            b"generalized collision implemented",
            b"generalized projectile manager implemented",
            b"explosion spawned",
            b"radius damage implemented",
            b"splash damage implemented",
            b"broad monster ai implemented",
            b"classic full statusbar implemented",
            b"face animation implemented",
            b"automap implemented",
            b"menu system implemented",
            b"intermission implemented",
            b"save load implemented",
            b"networking implemented",
            b"real audio playback implemented",
            b"mixer device playback implemented",
            b"map progression implemented",
            b"infighting implemented",
            b"player death implemented",
            b"enemy kill drop implemented",
            b"all-map sprite traversal implemented",
        ):
            self.assertNotIn(forbidden, lower)

    def test_preserves_stage41_through_stage19_signatures(self) -> None:
        ref = self._ref()
        ref41 = ref.stage41
        ref40 = ref41.stage40
        ref39 = ref40.stage39
        ref38 = ref39.stage38
        s29 = ref38.stage29
        s36 = ref38.stage36
        s31 = s36.stage34.stage33.stage32.stage31

        self.assertEqual(ref.stage41_status_preserved, 1)
        self.assertEqual(ref.compact_status_strip_preserved, 1)
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

    def test_build_output_contains_stage42_markers_and_no_stage43_strings(self) -> None:
        output = REPO_ROOT / "build" / "source_stage42_unified_live_tick_render_loop_probe.exe"
        output.parent.mkdir(parents=True, exist_ok=True)
        image = built_stage42_image()
        output.write_bytes(image)

        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 100_000)
        self.assertIn(b"source_stage42_unified_live_tick_render_loop_probe", image)
        self.assertIn(b"S42SIG=2427416971", image)
        self.assertIn(b"STATE42=2148021159", image)
        self.assertIn(b"ULSTATE42=3331619657", image)
        self.assertIn(b"INV42=3 UPD42=3 PAINT42=3 PAF42=1", image)
        self.assertIn(b"S41SIG=951695045", image)
        self.assertIn(b"S40SIG=2737672056", image)
        self.assertIn(b"MISS39=MT_TROOPSHOT", image)
        self.assertNotIn(b"source_stage43", image.lower())

    @unittest.skipUnless(os.name == "nt", "Win32 GUI smoke test requires Windows")
    def test_smoke_executable_launches_reports_unified_samples_paints_and_closes(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        output = REPO_ROOT / "build" / "source_stage42_unified_live_tick_render_loop_probe.exe"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(built_stage42_image())

        proc = subprocess.Popen([str(output)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, titles = collect_stage42_titles(proc.pid)
            final = titles[-1]
            self.assertNotEqual(hwnd, 0)
            self.assertIn("STEP42=3", final)
            self.assertIn("S42SIG=2427416971", final)
            self.assertIn("STATE42=2148021159", final)
            self.assertIn("CMD42=F8/S-5/A-32/B0", final)
            self.assertIn("HP42=91", final)
            self.assertIn("SHELL42=4", final)
            self.assertIn("WOWN42=1", final)
            self.assertIn("READY42=2", final)
            self.assertIn("PROJ42=1:S_TBALL1", final)
            self.assertIn("DROP42=0->1", final)
            self.assertIn("FB41=1672331767", final)
            self.assertIn("SSTATE41=3218471217", final)
            self.assertIn("MISS39=MT_TROOPSHOT", final)
            self.assertIn("INV42=3 UPD42=3 PAINT42=3 PAF42=1", final)
            self.assertIn("INV41=3 UPD41=3 PAINT41=3 PAF41=1", final)
            self.assertIn("S43ABS=1", final)
            fb_values = {
                int(match.group(1))
                for title in titles
                for match in re.finditer(r"FB42=(\d+)", title)
            }
            state_values = {
                int(match.group(1))
                for title in titles
                for match in re.finditer(r"ULSTATE42=(\d+)", title)
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
