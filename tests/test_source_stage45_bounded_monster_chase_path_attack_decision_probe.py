import os
import subprocess
import time
import unittest
from functools import lru_cache
from pathlib import Path

from tools import emit_source_stage45_bounded_monster_chase_path_attack_decision_probe as stage


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


@lru_cache(maxsize=1)
def built_stage45_image() -> bytes:
    return stage.build_source_stage45_bounded_monster_chase_path_attack_decision_probe_exe()


def write_stage45_exe() -> Path:
    stage.OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    stage.OUTPUT_PATH.write_bytes(built_stage45_image())
    return stage.OUTPUT_PATH


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
            if length > 0:
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


def collect_stage45_titles(pid: int, timeout_seconds: float = 8.0) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout_seconds
    hwnd = 0
    titles: list[str] = []
    seen: set[str] = set()
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
        if "STEP45=3" in title and "S45SIG=" in title:
            return hwnd, titles
        time.sleep(0.05)
    raise TimeoutError(f"stage45 final title not reached; saw {titles!r}")


def close_window(hwnd: int) -> None:
    import ctypes

    if hwnd:
        ctypes.WinDLL("user32", use_last_error=True).PostMessageW(hwnd, 0x0010, 0, 0)


class SourceStage45BoundedMonsterChasePathAttackDecisionProbeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage45BoundedMonsterChasePathAttackDecisionProbeReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_bounded_monster_chase_path_attack_decision_probe_for_pinned_map(PINNED_WAD)

    def test_source_trace_covers_selected_thinker_chase_sight_path_and_present(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}
        files = {entry[0] for entry in stage.SOURCE_TRACE}
        for label in (
            "P_Ticker_P_RunThinkers_stage45_selected_hostile_after_player_debug",
            "P_MobjThinker_stage45_selected_shotgun_guy_tick_debug",
            "A_Chase_stage45_selected_sight_failed_chase_debug",
            "P_CheckMeleeRange_stage45_selected_not_applicable_debug",
            "P_CheckMissileRange_stage45_selected_sight_reject_debug",
            "P_CheckSight_stage45_selected_bsp_block_debug",
            "P_Move_stage45_selected_chase_attempt_debug",
            "P_NewChaseDir_stage45_selected_bounded_search_debug",
            "P_TryMove_stage45_selected_monster_path_result_debug",
            "P_BlockIterators_stage45_selected_monster_path_debug",
            "V_DrawFilledBox_stage45_selected_monster_marker_debug",
            "I_Video_stage45_present_after_final_monster_sample_debug",
        ):
            self.assertIn(label, labels)
        for source in ("p_tick.c", "p_mobj.c", "p_enemy.c", "p_sight.c", "p_map.c", "p_maputl.c", "v_video.c", "i_video.c"):
            self.assertTrue(any(path.endswith(source) for path in files), source)

    def test_selected_map01_shotgun_guy_exact_sight_failed_no_attack_chase_result(self) -> None:
        ref = self._ref()
        first = ref.samples[0]
        self.assertEqual((first.actor_id, first.actor_mapthing_id, first.actor_type), (28, 37, "MT_SHOTGUY"))
        self.assertEqual((first.actor_state_before_name, first.actor_tics_before), ("S_SPOS_RUN1", 1))
        self.assertEqual((first.actor_state_name, first.actor_tics), ("S_SPOS_RUN2", 3))
        self.assertEqual((first.target_id, first.target_health), (0, 91))
        self.assertEqual((first.target_x >> stage.stage31.FRACBITS, first.target_y >> stage.stage31.FRACBITS), (-192, -192))
        self.assertEqual((first.sight_result, first.sight_reject_blocked, first.sight_bsp_blocked), (0, 0, 1))
        self.assertEqual((first.sight_nodes, first.sight_subsectors, first.sight_segs, first.sight_crossed_lines), (8, 1, 1, 1))
        self.assertEqual((first.melee_applicable, first.melee_result), (0, 0))
        self.assertEqual((first.missile_checked, first.missile_result), (1, 0))
        self.assertEqual((first.chase_calls, first.new_chase_dir_calls), (1, 1))
        self.assertEqual((first.move_calls, first.move_accepts, first.move_blocks), (3, 1, 2))
        self.assertEqual((first.try_move_calls, first.try_move_accepts, first.try_move_rejects), (4, 2, 2))
        self.assertEqual((first.attack_state_changes, first.attack_executed, first.damage_events), (0, 0, 0))
        self.assertEqual(first.branch, "SIGHT_FAILED_NO_ATTACK_CHASE_ACCEPTED")
        self.assertIn("P_CheckSight blocked", first.no_damage_reason)
        self.assertEqual((ref.selected_sight_failed, ref.selected_no_melee_state, ref.selected_missile_rejected), (1, 1, 1))
        self.assertEqual((ref.selected_new_chase_dir, ref.selected_chase_move_accepted, ref.selected_no_attack, ref.selected_no_damage), (1, 1, 1, 1))

    def test_thinker_runs_after_stage44_player_and_before_projectile_status_present(self) -> None:
        ref = self._ref()
        for sample in ref.samples:
            self.assertLess(sample.player_update_sequence, sample.monster_thinker_sequence)
            self.assertLess(sample.monster_thinker_sequence, sample.projectile_thinker_sequence)
            self.assertLess(sample.projectile_thinker_sequence, sample.status_sequence)
            self.assertLess(sample.status_sequence, sample.signature_sequence)
            self.assertLess(sample.signature_sequence, sample.present_sequence)
        self.assertEqual((ref.monster_after_player_update, ref.projectile_after_monster, ref.status_after_projectile, ref.present_after_status), (1, 1, 1, 1))

    def test_monster_and_unified_state_signatures_differ(self) -> None:
        ref = self._ref()
        self.assertEqual(ref.signature, 799763036)
        self.assertEqual(ref.state_signature, 1707493859)
        self.assertEqual([s.monster_decision_state_signature for s in ref.samples], [2099866182, 4104622831, 802996254])
        self.assertEqual([s.stage45_unified_state_signature for s in ref.samples], [3743123641, 634485342, 4107409497])
        self.assertEqual([s.framebuffer_signature for s in ref.samples], [135776868, 2645699933, 4149793188])
        self.assertEqual((ref.distinct_monster_decision_state_signatures, ref.distinct_stage45_unified_state_signatures, ref.distinct_framebuffer_signatures), (3, 3, 3))

    def test_runtime_marker_primitive_changes_each_frame_without_full_frame_copies(self) -> None:
        ref = self._ref()
        image = built_stage45_image()
        self.assertTrue(all(s.pre_marker_framebuffer_signature != s.framebuffer_signature for s in ref.samples))
        self.assertTrue(all(s.marker_pixels == s.marker_width * s.marker_height for s in ref.samples))
        self.assertEqual((ref.full_frame_byte_arrays_absent, ref.runtime_renderer_primitives), (1, 1))
        self.assertIn(b"NOFULL45=1", image)
        self.assertIn(b"PRIM45=1", image)
        self.assertNotIn(b"stage45_frame_pixels", image)
        self.assertNotIn(b"stage45_copy_rendered_frame", image)
        self.assertEqual(image.count(b"\xF3\xA5"), 0)

    def test_stage44_and_projectile_status_vissprite_projectile_state_are_preserved(self) -> None:
        ref = self._ref()
        self.assertEqual((ref.stage44.signature, ref.stage44.state_signature), (1090523498, 904132091))
        self.assertEqual([s.baseline.player_view_state_signature for s in ref.samples], [357948012, 892576224, 2418604776])
        self.assertEqual([s.baseline.stage44_unified_state_signature for s in ref.samples], [2223136105, 28118546, 1194642191])
        self.assertEqual([s.baseline.framebuffer_signature for s in ref.samples], [2010236716, 1358571739, 2958912480])
        self.assertEqual((ref.stage44_live_replay_preserved, ref.stage43_projectile_preserved, ref.stage41_status_preserved, ref.stage40_bal1_vissprite_preserved, ref.stage39_projectile_state_preserved), (1, 1, 1, 1, 1))
        self.assertEqual(ref.stage44.stage43.signature, 2916740242)
        self.assertEqual(ref.stage44.stage43.stage42.stage41.stage40.stage39.projectile.type_name, "MT_TROOPSHOT")

    def test_stage43_through_stage19_signatures_are_preserved(self) -> None:
        ref = self._ref()
        r44 = ref.stage44
        r43 = r44.stage43
        r42 = r43.stage42
        r41 = r42.stage41
        r40 = r41.stage40
        r39 = r40.stage39
        r38 = r39.stage38
        s29 = r38.stage29
        s36 = r38.stage36
        s31 = s36.stage34.stage33.stage32.stage31
        self.assertEqual(ref.stage43_through_stage19_preserved, 1)
        self.assertEqual((r43.signature, r43.state_signature), (2916740242, 801364352))
        self.assertEqual((r42.signature, r42.state_signature), (2427416971, 2148021159))
        self.assertEqual((r41.signature, r41.state_signature), (951695045, 157977072))
        self.assertEqual((r40.signature, r40.state_signature), (2737672056, 268409133))
        self.assertEqual((r39.signature, r39.projectile.state_signature), (3469618451, 1403583302))
        self.assertEqual(r38.signature, 2314527789)
        self.assertEqual(stage.stage39.BASELINE_S37_SIGNATURE, 2681905384)
        self.assertEqual(s36.signature, 397846180)
        self.assertEqual(stage.stage36.ref35_signature(s36), 3270148876)
        self.assertEqual((s36.stage34.signature, s36.stage34.stage33.signature, s36.stage34.stage33.stage32.signature), (4027590938, 1614948054, 533488475))
        self.assertEqual((s31.signature, s31.stage30.signature, s29.signature), (3593583171, 3898523864, 3738922932))
        self.assertEqual((s29.stage28.signature, s29.stage28.stage27.signature), (2805406010, 1735738182))
        self.assertEqual(s29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)

    def test_present_occurs_after_final_sample_and_gui_counters_are_pinned(self) -> None:
        ref = self._ref()
        self.assertEqual((ref.timer_samples, ref.invalidate_calls, ref.update_window_calls, ref.expected_paint_calls), (3, 3, 3, 3))
        self.assertEqual(ref.paint_after_final_monster_sample, 1)
        self.assertIn("INV45=3 UPD45=3 PAINT45=3 PAF45=1", stage._stage45_replay_titles(ref)[-1])

    def test_deferred_broad_systems_and_stage46_string_are_absent(self) -> None:
        ref = self._ref()
        lower = built_stage45_image().lower()
        for value in (
            ref.bounded_selected_thinker_only,
            ref.generalized_thinkers_absent,
            ref.generalized_pathing_absent,
            ref.generalized_collision_absent,
            ref.generalized_combat_absent,
            ref.broad_sprite_traversal_absent,
            ref.broad_inventory_absent,
            ref.broad_hud_ui_absent,
            ref.death_respawn_absent,
            ref.map_progression_absent,
            ref.save_load_absent,
            ref.networking_absent,
            ref.music_absent,
            ref.real_audio_absent,
            ref.mixer_device_playback_absent,
            ref.source_stage46_absent,
        ):
            self.assertEqual(value, 1)
        self.assertNotIn(b"source_stage46", lower)
        for forbidden in (b"generalized thinker implemented", b"generalized pathing implemented", b"generalized collision implemented", b"broad combat implemented", b"real audio playback implemented", b"mixer device playback implemented"):
            self.assertNotIn(forbidden, lower)

    def test_executable_build_contains_exact_decision_and_preservation_evidence(self) -> None:
        image = built_stage45_image()
        output = write_stage45_exe()
        lower = image.lower()
        self.assertTrue(output.exists())
        self.assertEqual(image[:2], b"MZ")
        for marker in (
            b"source_stage45_bounded_monster_chase_path_attack_decision_probe",
            b"Bounded Monster Chase Path Attack Decision Probe proof OK",
            b"S45 REPLAY START STEP45=0",
            b"STEP45=3",
            b"ACT45=28/37:MT_SHOTGUY",
            b"BRANCH45=SIGHT_FAILED_NO_ATTACK_CHASE_ACCEPTED",
            b"SIGHT45=0:BSP1",
            b"MISSILE45=1:0",
            b"MOVE45=3:1:2",
            b"ATTACK45=0 DMG45=0 WHY45=SIGHT_BLOCKED_NO_MELEE",
            b"S45SIG=799763036",
            b"STATE45=1707493859",
            b"S44SIG=1090523498",
            b"MISS43=MT_TROOPSHOT",
            b"PATCH40=BAL1",
            b"S19SIG=2088411722",
            b"S46ABS=1",
        ):
            self.assertIn(marker, image)
        for forbidden in (b"gcc:", b"mingw", b"microsoft visual c", b"nasm", b"source_stage46"):
            self.assertNotIn(forbidden, lower)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage45_decision_paints_and_closes(self) -> None:
        ref = self._ref()
        exe_path = write_stage45_exe()
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, titles = collect_stage45_titles(process.pid)
            title = titles[-1]
            self.assertIn("STEP45=3", title)
            self.assertIn("ACT45=28/37:MT_SHOTGUY", title)
            self.assertIn("AST45=S_SPOS_RUN2/T2->S_SPOS_RUN2/T1", title)
            self.assertIn("TGT45=0:PST_LIVE/HP91/XY-190,-193", title)
            self.assertIn("SIGHT45=0:BSP1/N8/SS1/SEG1/X1", title)
            self.assertIn("ATTACK45=0 DMG45=0 WHY45=SIGHT_BLOCKED_NO_MELEE", title)
            self.assertIn(f"MSTATE45={ref.samples[-1].monster_decision_state_signature}", title)
            self.assertIn(f"ULSTATE45={ref.samples[-1].stage45_unified_state_signature}", title)
            self.assertIn(f"FB45={ref.samples[-1].framebuffer_signature}", title)
            self.assertIn(f"STATE45={ref.state_signature} S45SIG={ref.signature}", title)
            self.assertIn("S44SIG=1090523498", title)
            self.assertIn("MISS43=MT_TROOPSHOT", title)
            self.assertIn("PATCH40=BAL1", title)
            self.assertIn("INV45=3 UPD45=3 PAINT45=3 PAF45=1", title)
            self.assertIn("S46ABS=1", title)
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
