import os
import re
import subprocess
import time
import unittest
from functools import lru_cache
from pathlib import Path

from tools import emit_source_stage44_live_ticcmd_unified_player_render_loop_bridge as stage


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


@lru_cache(maxsize=1)
def built_stage44_image() -> bytes:
    return stage.build_source_stage44_live_ticcmd_unified_player_render_loop_bridge_exe()


def write_stage44_exe() -> Path:
    output = stage.OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(built_stage44_image())
    return output


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


def collect_stage44_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP44=3" in title and "S44SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage44 final title not reached; saw {titles!r}")


def close_window(hwnd: int) -> None:
    import ctypes

    if hwnd:
        ctypes.WinDLL("user32", use_last_error=True).PostMessageW(hwnd, 0x0010, 0, 0)


class SourceStage44LiveTiccmdUnifiedPlayerRenderLoopBridgeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage44LiveTiccmdUnifiedPlayerRenderLoopBridgeReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_live_ticcmd_unified_player_render_loop_bridge_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_cover_live_ticcmd_player_redraw_and_present_sources(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}
        files = {entry[0] for entry in stage.SOURCE_TRACE}

        for label in (
            "D_DoomLoop_stage44_replay_or_live_ticcmd_intake_debug",
            "I_Input_stage44_bounded_keydown_keyup_gamekeydown_debug",
            "G_BuildTiccmd_stage44_live_or_replay_gamekeydown_table_debug",
            "G_Ticker_stage44_ticcmd_player_ownership_debug",
            "P_PlayerThink_stage44_bounded_player_command_update_debug",
            "P_Thrust_stage44_selected_forward_turn_momentum_debug",
            "P_XYMovement_stage44_bounded_player_trymove_debug",
            "P_TryMove_stage44_selected_player_no_general_collision_debug",
            "P_BlockIterators_stage44_selected_player_bounds_debug",
            "R_SetupFrame_stage44_finite_route_redraw_sample_select_debug",
            "V_DrawFilledBox_stage44_runtime_player_view_marker_debug",
            "I_Video_stage44_final_present_after_live_ticcmd_debug",
        ):
            self.assertIn(label, labels)
        for source in ("d_loop.c", "i_input.c", "g_game.c", "p_user.c", "p_mobj.c", "p_map.c", "p_maputl.c", "r_main.c", "v_video.c", "i_video.c"):
            self.assertTrue(any(path.endswith(source) for path in files), source)

    def test_synthetic_live_key_transitions_feed_stage28_gamekeydown_and_ticcmd_tables(self) -> None:
        bridge = stage.Stage44CommandBridgeState()
        stage.d_post_event_stage44_live_key_state_bridge_source_shape(bridge, "forward", True)
        stage.d_post_event_stage44_live_key_state_bridge_source_shape(bridge, "right", True)
        stage.d_post_event_stage44_live_key_state_bridge_source_shape(bridge, "use", True)
        keys = stage._key_state_from_bridge(bridge)
        self.assertEqual((keys.forward, keys.turn_right, keys.use), (True, True, True))
        self.assertEqual(bridge.live_key_events, 3)

        counters = stage.Stage44Counters()
        live_cmd = stage.g_build_ticcmd_stage44_live_or_replay_bridge_source_shape(
            bridge,
            counters,
            replay=False,
            live_keys=keys,
            tic=11,
            source_index=7,
        )
        self.assertEqual((live_cmd.forwardmove, live_cmd.sidemove, live_cmd.angleturn, live_cmd.buttons), (stage.FORWARDMOVE, 0, -stage.SLOW_ANGLETURN, stage.BT_USE))
        self.assertEqual((counters.manual_commands_built, counters.manual_forward_fields, counters.manual_turn_fields, counters.manual_bt_use_commands), (1, 1, 1, 1))

        stage.d_post_event_stage44_live_key_state_bridge_source_shape(bridge, "forward", False)
        self.assertFalse(stage._key_state_from_bridge(bridge).forward)
        replay_cmd = stage.g_build_ticcmd_stage44_live_or_replay_bridge_source_shape(
            bridge,
            counters,
            replay=True,
            replay_cmd=stage.Stage44TicCmd(tic=12),
            live_keys=stage.Stage44KeyState(forward=True, turn_left=True, use=True),
            tic=12,
            source_index=8,
        )
        self.assertEqual((replay_cmd.forwardmove, replay_cmd.angleturn, replay_cmd.buttons), (0, 0, 0))
        self.assertEqual(counters.replay_ignored_live_key_state, 1)

    def test_synthetic_replay_default_uses_stage28_bridge_and_ignores_live_keys(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.deterministic_replay_default, 1)
        self.assertEqual(ref.live_mode_requires_flag, 1)
        self.assertEqual(ref.stage28_bridge_reused, 1)
        self.assertEqual(ref.gamekeydown_table_shared, 1)
        self.assertEqual(ref.replay_ignores_live_keys, 1)
        self.assertEqual([s.mode for s in ref.samples], ["REPLAY"] * 3)
        self.assertEqual([s.live_enabled for s in ref.samples], [0, 0, 0])
        self.assertEqual([s.replay_commands_built for s in ref.samples], [1, 2, 3])
        self.assertEqual([s.replay_ignored_live_key_state for s in ref.samples], [1, 2, 3])
        self.assertEqual([(s.live_keys_forward, s.live_keys_left, s.live_keys_right, s.live_keys_use) for s in ref.samples], [(1, 0, 0, 1), (1, 0, 1, 0), (1, 1, 0, 1)])

    def test_synthetic_player_view_state_mutates_from_ticcmd_input(self) -> None:
        ref = self._ref()

        self.assertEqual([s.tic for s in ref.samples], [0, 4, 7])
        self.assertEqual([(s.ticcmd.forwardmove, s.ticcmd.sidemove, s.ticcmd.angleturn, s.ticcmd.buttons) for s in ref.samples], [(0, 0, 0, 0), (25, 0, -320, 0), (25, 0, 320, 2)])
        self.assertEqual([(s.new_x >> stage.stage31.FRACBITS, s.new_y >> stage.stage31.FRACBITS, s.new_angle) for s in ref.samples], [(-192, -192, 0), (-192, -193, 4273995776), (-190, -193, 0)])
        self.assertEqual([s.move_delta.g_ticker_calls for s in ref.samples], [1, 1, 1])
        self.assertEqual([s.move_delta.player_think_calls for s in ref.samples], [1, 1, 1])
        self.assertEqual([s.move_delta.xy_movement_calls for s in ref.samples], [1, 1, 1])
        self.assertEqual([s.move_delta.try_move_calls for s in ref.samples], [0, 1, 1])
        self.assertEqual([s.move_delta.check_position_calls for s in ref.samples], [0, 1, 1])
        self.assertEqual([s.move_delta.accepted_moves for s in ref.samples], [0, 1, 1])
        self.assertEqual([s.move_delta.rejected_moves for s in ref.samples], [0, 0, 0])
        self.assertGreaterEqual(len({(s.new_x, s.new_y, s.new_angle) for s in ref.samples}), 2)
        self.assertEqual(ref.selected_player_movement_update, 1)
        self.assertEqual(ref.selected_p_thrust_update, 1)
        self.assertEqual(ref.selected_xy_movement_update, 1)
        self.assertEqual(ref.selected_trymove_boundary, 1)

    def test_synthetic_bounded_redraw_sample_selection_is_explicit(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.finite_redraw_route_table, 1)
        self.assertEqual(ref.finite_redraw_route_table_size, 3)
        self.assertEqual(ref.free_roaming_render_absent, 1)
        self.assertEqual([s.redraw_sample_id for s in ref.samples], [0, 1, 2])
        self.assertEqual([s.redraw_table_size for s in ref.samples], [3, 3, 3])
        self.assertEqual([s.finite_route_table for s in ref.samples], [1, 1, 1])
        self.assertEqual([s.free_roaming_render_absent for s in ref.samples], [1, 1, 1])
        self.assertTrue(all(s.pre_marker_framebuffer_signature != s.framebuffer_signature for s in ref.samples))
        self.assertIn("RSEL44=2/3 ROUTE44=bounded3 FREE44=0", stage._stage44_replay_titles(ref)[-1])

    def test_synthetic_ordering_runs_player_update_before_projectile_status_and_present(self) -> None:
        ref = self._ref()

        for sample in ref.samples:
            self.assertLess(sample.start_tic_sequence, sample.input_event_sequence)
            self.assertLess(sample.input_event_sequence, sample.ticcmd_sequence)
            self.assertLess(sample.ticcmd_sequence, sample.g_ticker_sequence)
            self.assertLess(sample.g_ticker_sequence, sample.p_ticker_sequence)
            self.assertLess(sample.p_ticker_sequence, sample.player_think_sequence)
            self.assertLess(sample.player_think_sequence, sample.p_move_player_sequence)
            self.assertLess(sample.p_move_player_sequence, sample.p_thrust_sequence)
            self.assertLess(sample.p_thrust_sequence, sample.xy_movement_sequence)
            self.assertLess(sample.xy_movement_sequence, sample.try_move_sequence)
            self.assertLess(sample.try_move_sequence, sample.r_setup_frame_sequence)
            self.assertLess(sample.r_setup_frame_sequence, sample.bounded_redraw_sequence)
            self.assertLess(sample.p_move_player_sequence, sample.projectile_thinker_sequence)
            self.assertLess(sample.projectile_thinker_sequence, sample.status_sequence)
            self.assertLess(sample.status_sequence, sample.signature_sequence)
            self.assertLess(sample.signature_sequence, sample.present_sequence)
        self.assertEqual(ref.selected_projectile_after_player_update, 1)

    def test_synthetic_signatures_and_state_differ_because_runtime_state_changed(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.signature, 1090523498)
        self.assertEqual(ref.state_signature, 904132091)
        self.assertEqual([s.player_view_state_signature for s in ref.samples], [357948012, 892576224, 2418604776])
        self.assertEqual([s.stage44_unified_state_signature for s in ref.samples], [2223136105, 28118546, 1194642191])
        self.assertEqual([s.framebuffer_signature for s in ref.samples], [2010236716, 1358571739, 2958912480])
        self.assertEqual(ref.distinct_player_view_state_signatures, 3)
        self.assertEqual(ref.distinct_stage44_unified_state_signatures, 3)
        self.assertEqual(ref.distinct_framebuffer_signatures, 3)

    def test_projectile_status_world_vissprite_psprite_and_present_baselines_preserved(self) -> None:
        ref = self._ref()

        self.assertEqual(ref.stage43_projectile_preserved, 1)
        self.assertEqual(ref.stage43_unified_loop_preserved, 1)
        self.assertEqual(ref.stage42_unified_loop_preserved, 1)
        self.assertEqual(ref.stage41_status_preserved, 1)
        self.assertEqual(ref.stage40_vissprite_preserved, 1)
        self.assertEqual(ref.stage39_projectile_state_preserved, 1)
        self.assertEqual(ref.compact_status_preserved, 1)
        self.assertEqual(ref.stage40_bal1_vissprite_preserved, 1)
        self.assertEqual(ref.stage43.signature, 2916740242)
        self.assertEqual(ref.stage43.state_signature, 801364352)
        self.assertEqual([s.baseline.projectile_state_signature for s in ref.samples], [2141010421, 1184488335, 467194799])
        self.assertEqual([s.baseline.stage43_unified_state_signature for s in ref.samples], [531845647, 3017464017, 3895028583])
        self.assertEqual([s.baseline.framebuffer_signature for s in ref.samples], [832571689, 3232273554, 3301289045])
        self.assertEqual(ref.stage43.stage42.stage41.stage40.stage39.projectile.type_name, "MT_TROOPSHOT")

    def test_present_after_final_player_sample_and_stage43_stability_preserved(self) -> None:
        ref = self._ref()

        self.assertEqual((ref.timer_samples, ref.invalidate_calls, ref.update_window_calls, ref.expected_paint_calls), (3, 3, 3, 3))
        self.assertEqual(ref.paint_after_final_player_sample, 1)
        self.assertEqual(ref.final_window_alive_after_samples, 1)
        self.assertEqual(ref.closes_normally, 1)
        self.assertEqual((ref.stage43.invalidate_calls, ref.stage43.update_window_calls, ref.stage43.expected_paint_calls), (3, 3, 3))
        self.assertEqual(ref.stage43.paint_after_final_projectile_sample, 1)
        self.assertIn("INV44=3 UPD44=3 PAINT44=3 PAF44=1", stage._stage44_replay_titles(ref)[-1])

    def test_runtime_primitives_tables_generate_visual_state_changes_without_full_frame_copies(self) -> None:
        ref = self._ref()
        image = built_stage44_image()

        self.assertEqual(ref.full_frame_byte_arrays_absent, 1)
        self.assertEqual(ref.runtime_renderer_primitives, 1)
        self.assertIn(b"NOFULL44=1", image)
        self.assertIn(b"finite redraw samples", image)
        self.assertIn(b"ROUTE44=bounded3", image)
        self.assertNotIn(b"stage44_frame_pixels", image)
        self.assertNotIn(b"stage44_copy_rendered_frame", image)
        self.assertEqual(image.count(b"\xF3\xA5"), 0)

    def test_absence_flags_keep_deferred_systems_out_and_no_stage45_strings(self) -> None:
        ref = self._ref()
        lower = built_stage44_image().lower()

        for value in (
            ref.generalized_thinkers_absent,
            ref.generalized_collision_absent,
            ref.generalized_projectile_manager_absent,
            ref.broad_monster_ai_absent,
            ref.generalized_combat_absent,
            ref.broad_sprite_traversal_absent,
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
            ref.source_stage45_absent,
        ):
            self.assertEqual(value, 1)
        self.assertNotIn(b"source_stage45", lower)
        for forbidden in (
            b"free roaming render implemented",
            b"generalized thinker implemented",
            b"generalized collision implemented",
            b"generalized projectile manager implemented",
            b"broad sprite traversal implemented",
            b"broad combat implemented",
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

    def test_preserves_stage43_through_stage19_signatures(self) -> None:
        ref = self._ref()
        ref43 = ref.stage43
        ref42 = ref43.stage42
        ref41 = ref42.stage41
        ref40 = ref41.stage40
        ref39 = ref40.stage39
        ref38 = ref39.stage38
        s29 = ref38.stage29
        s36 = ref38.stage36
        s31 = s36.stage34.stage33.stage32.stage31

        self.assertEqual(ref43.signature, 2916740242)
        self.assertEqual(ref43.state_signature, 801364352)
        self.assertEqual(ref42.signature, 2427416971)
        self.assertEqual(ref42.state_signature, 2148021159)
        self.assertEqual(ref41.signature, 951695045)
        self.assertEqual(ref41.state_signature, 157977072)
        self.assertEqual(ref40.signature, 2737672056)
        self.assertEqual(ref40.state_signature, 268409133)
        self.assertEqual(ref39.signature, 3469618451)
        self.assertEqual(ref39.projectile.state_signature, 1403583302)
        self.assertEqual(ref38.signature, 2314527789)
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

    def test_executable_build_contains_stage44_status_live_flag_and_no_stage45_strings(self) -> None:
        image = built_stage44_image()
        output = write_stage44_exe()
        lower = image.lower()

        self.assertTrue(output.exists())
        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage44_live_ticcmd_unified_player_render_loop_bridge", image)
        self.assertIn(b"Live Ticcmd Unified Player Render Loop Bridge proof OK", image)
        self.assertIn(b"S44 REPLAY START STEP44=0 LIVE44=0", image)
        self.assertIn(b"S44 LIVE START LIVE44=1", image)
        self.assertIn(b"STEP44=3", image)
        self.assertIn(b"S44SIG=1090523498", image)
        self.assertIn(b"STATE44=904132091", image)
        self.assertIn(b"CMD44=F25/S0/A320/B2", image)
        self.assertIn(b"RSEL44=2/3", image)
        self.assertIn(b"PATCH40=BAL1", image)
        self.assertIn(b"BTUSE44=", image)
        self.assertIn(b"S45ABS=1", image)
        self.assertNotIn(b"source_stage45", lower)
        for marker in (b" S43SIG=", b" S42SIG=", b" S41SIG=", b" S40SIG=", b" S39SIG=", b" S38SIG=", b" S37SIG=", b" S36SIG=", b" S35SIG=", b" S34SIG=", b" S33SIG=", b" S32SIG=", b" S31SIG=", b" S30SIG=", b" S29SIG=", b" S28SIG=", b" S27SIG=", b" S26SIG=", b" S25SIG=", b" S24SIG=", b" S23SIG=", b" S22SIG=", b" S21SIG=", b" S20SIG=", b" S19SIG="):
            self.assertIn(marker, image)
        for forbidden in (b"gcc:", b"mingw", b"microsoft visual c", b"nasm", b"source_stage45"):
            self.assertNotIn(forbidden, lower)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage44_final_replay_title_and_closes(self) -> None:
        ref = self._ref()
        exe_path = write_stage44_exe()
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, titles = collect_stage44_titles(process.pid)
            title = titles[-1]
            self.assertIn("STEP44=3", title)
            self.assertIn("LIVE44=0", title)
            self.assertIn("CMD44=F25/S0/A320/B2", title)
            self.assertIn("PX44=-190 PY44=-193", title)
            self.assertIn("RSEL44=2/3 ROUTE44=bounded3 FREE44=0", title)
            self.assertIn(f"PVSTATE44={ref.samples[-1].player_view_state_signature}", title)
            self.assertIn(f"ULSTATE44={ref.samples[-1].stage44_unified_state_signature}", title)
            self.assertIn(f"FB44={ref.samples[-1].framebuffer_signature}", title)
            self.assertIn(f"STATE44={ref.state_signature}", title)
            self.assertIn(f"S44SIG={ref.signature}", title)
            self.assertIn("MISS43=MT_TROOPSHOT", title)
            self.assertIn("PSTATE43=467194799", title)
            self.assertIn("PATCH40=BAL1", title)
            self.assertIn("S43SIG=2916740242", title)
            self.assertIn("S42SIG=2427416971", title)
            self.assertIn("S41SIG=951695045", title)
            self.assertIn("S40SIG=2737672056", title)
            self.assertIn("S39SIG=3469618451", title)
            self.assertIn("S19SIG=2088411722", title)
            self.assertIn("INV44=3 UPD44=3 PAINT44=3 PAF44=1", title)
            self.assertIn("NOFULL44=1", title)
            self.assertIn("BAL144=1", title)
            self.assertIn("S45ABS=1", title)
            self.assertIsNone(process.poll())
        finally:
            close_window(hwnd)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=3)


if __name__ == "__main__":
    unittest.main()
