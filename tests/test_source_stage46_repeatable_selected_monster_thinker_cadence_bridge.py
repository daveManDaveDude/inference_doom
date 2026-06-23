import os
import re
import subprocess
import time
import unittest
from functools import lru_cache
from pathlib import Path

from tools import emit_source_stage46_repeatable_selected_monster_thinker_cadence_bridge as stage


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


@lru_cache(maxsize=1)
def built_stage46_image() -> bytes:
    return stage.build_source_stage46_repeatable_selected_monster_thinker_cadence_bridge_exe()


@lru_cache(maxsize=1)
def stage46_reference() -> stage.Stage46RepeatableSelectedMonsterThinkerCadenceBridgeReference:
    return stage.reference_repeatable_selected_monster_thinker_cadence_bridge_for_pinned_map(PINNED_WAD)


def write_stage46_exe() -> Path:
    stage.OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    stage.OUTPUT_PATH.write_bytes(built_stage46_image())
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
            if length:
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


def collect_final_title(pid: int, timeout_seconds: float = 10.0) -> tuple[int, str]:
    deadline = time.monotonic() + timeout_seconds
    titles: list[str] = []
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title and (not titles or title != titles[-1]):
            titles.append(title)
        if "STEP46=7" in title and "PAF46=1" in title:
            return hwnd, title
        time.sleep(0.05)
    raise TimeoutError(f"stage46 final title not reached; saw {titles!r}")


def collect_live_title(pid: int, minimum_tic: int = 7, timeout_seconds: float = 10.0) -> tuple[int, str]:
    deadline = time.monotonic() + timeout_seconds
    titles: list[str] = []
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.5)
        if title and (not titles or title != titles[-1]):
            titles.append(title)
        match = re.search(r"TIC46=(\d+)", title)
        if match and int(match.group(1)) >= minimum_tic:
            return hwnd, title
        time.sleep(0.05)
    raise TimeoutError(f"stage46 live tic {minimum_tic} not reached; saw {titles!r}")


def close_window(hwnd: int) -> None:
    import ctypes

    if hwnd:
        ctypes.WinDLL("user32", use_last_error=True).PostMessageW(hwnd, 0x0010, 0, 0)


class SourceStage46RepeatableSelectedMonsterThinkerCadenceBridgeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage46RepeatableSelectedMonsterThinkerCadenceBridgeReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage46_reference()

    def test_source_trace_covers_runtime_cadence_state_chase_move_render_and_present(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}
        files = {entry[0] for entry in stage.SOURCE_TRACE}
        for label in (
            "P_Ticker_P_RunThinkers_stage46_selected_actor_once_per_accepted_tic_debug",
            "P_MobjThinker_stage46_runtime_owned_selected_actor_cadence_debug",
            "info_stage46_bounded_S_SPOS_RUN1_RUN8_state_table_debug",
            "A_Chase_stage46_repeatable_selected_runtime_dispatch_debug",
            "P_Move_P_TryWalk_P_NewChaseDir_stage46_bounded_runtime_debug",
            "P_CheckSight_stage46_selected_blocked_evidence_debug",
            "P_TryMove_stage46_bounded_input_outcome_table_debug",
            "P_BlockIterators_stage46_bounded_attempt_evidence_debug",
            "V_DrawFilledBox_stage46_runtime_actor_marker_debug",
            "I_Video_stage46_present_after_final_cadence_sample_debug",
        ):
            self.assertIn(label, labels)
        for filename in ("p_tick.c", "p_mobj.c", "info.c", "p_enemy.c", "p_sight.c", "p_map.c", "p_maputl.c", "v_video.c", "i_video.c"):
            self.assertTrue(any(path.endswith(filename) for path in files), filename)

    def test_runtime_owned_state_table_advances_three_honest_a_chase_dispatches(self) -> None:
        ref = self._ref()
        self.assertEqual((ref.selected_actor_id, ref.selected_mapthing_id, ref.selected_actor_type), (28, 37, "MT_SHOTGUY"))
        self.assertEqual(len(ref.state_table), 8)
        self.assertEqual([record[1] for record in ref.state_table], [3] * 8)
        self.assertEqual([record[2] for record in ref.state_table[:-1]], [record[0] for record in ref.state_table[1:]])
        self.assertEqual(ref.state_table[-1][2], ref.state_table[0][0])
        self.assertEqual([record[3] for record in ref.state_table], [1] * 8)
        transitions = [(s.step, s.state_before_name, s.tics_before, s.state_name, s.tics) for s in ref.samples if s.state_transitions]
        self.assertEqual(transitions, [
            (1, "S_SPOS_RUN1", 1, "S_SPOS_RUN2", 3),
            (4, "S_SPOS_RUN2", 1, "S_SPOS_RUN3", 3),
            (7, "S_SPOS_RUN3", 1, "S_SPOS_RUN4", 3),
        ])
        self.assertEqual((ref.runtime_owned_actor_fields, ref.runtime_state_table_transitions), (1, 1))
        self.assertEqual((ref.action_dispatches, ref.chase_dispatches), (3, 3))

    def test_tic4_nomissile_gate_has_five_blocks_then_one_accept_and_tic7_accepts_current(self) -> None:
        ref = self._ref()
        tic4 = ref.samples[3]
        self.assertEqual((tic4.nomissile_movecount_gates, tic4.missile_checks, tic4.sight_checks), (1, 0, 0))
        self.assertEqual((tic4.move_calls, tic4.move_accepts, tic4.move_blocks), (6, 1, 5))
        chase_attempts = [a for a in tic4.attempts if a.kind != stage.ATTEMPT_MOMENTUM]
        self.assertEqual([a.accepted for a in chase_attempts], [0, 0, 0, 0, 0, 1])
        self.assertEqual([a.movedir for a in chase_attempts], [2, 3, 4, 2, 2, 7])
        tic7 = ref.samples[6]
        self.assertEqual((tic7.nomissile_movecount_gates, tic7.move_calls, tic7.move_accepts, tic7.move_blocks), (1, 1, 1, 0))
        self.assertEqual((tic7.new_chase_dir_calls, tic7.actor_movedir, tic7.actor_movecount), (0, 7, 6))
        self.assertEqual((ref.tic4_nomissile_gate, ref.tic4_five_blocked_one_accepted, ref.later_current_direction_accepted), (1, 1, 1))

    def test_first_sight_failure_and_later_nomissile_gates_explain_zero_attack_damage(self) -> None:
        ref = self._ref()
        first = ref.samples[0]
        self.assertEqual((first.sight_checks, first.sight_result, first.missile_checks, first.missile_result), (1, 0, 1, 0))
        self.assertEqual((first.attack_state_changes, first.attack_actions, first.damage_events), (0, 0, 0))
        self.assertTrue(all((s.attack_actions, s.damage_events) == (0, 0) for s in ref.samples))
        self.assertIn("P_CheckSight failure", ref.no_damage_reason)
        self.assertIn("nonzero movecount nomissile", ref.no_damage_reason)
        self.assertIn("P_DamageMobj is unreachable", ref.no_damage_reason)
        self.assertEqual(ref.blocked_sight_no_attack, 1)

    def test_attempt_table_contains_inputs_and_outcomes_not_complete_actor_frames(self) -> None:
        ref = self._ref()
        source = Path(stage.__file__).read_text(encoding="utf-8")
        self.assertGreaterEqual(len(ref.attempt_table), sum(len(s.attempts) for s in ref.samples))
        self.assertTrue(all(a.kind in (0, 1, 2) and a.accepted in (0, 1) for a in ref.attempt_table))
        self.assertIn("attempt.try_x", source)
        self.assertIn("attempt.accepted", source)
        self.assertNotIn("stage46_sample{index}_actor_state", source)
        image = built_stage46_image().lower()
        self.assertNotIn(b"stage46_sample0_actor", image)
        self.assertNotIn(b"stage45_sample0_actor", image)
        self.assertIn(b"contains no final actor frames", image)
        self.assertEqual((ref.complete_actor_snapshot_tables_absent, ref.full_frame_byte_arrays_absent), (1, 1))
        self.assertEqual(image.count(b"\xf3\xa5"), 0)

    def test_replay_live_ownership_and_update_order_are_preserved(self) -> None:
        ref = self._ref()
        for sample in ref.samples:
            self.assertLess(sample.player_update_sequence, sample.monster_thinker_sequence)
            self.assertLess(sample.monster_thinker_sequence, sample.projectile_thinker_sequence)
            self.assertLess(sample.projectile_thinker_sequence, sample.status_sequence)
            self.assertLess(sample.status_sequence, sample.signature_sequence)
            self.assertLess(sample.signature_sequence, sample.present_sequence)
        self.assertEqual((ref.replay_thinker_once_per_tic, ref.live_thinker_once_per_tic), (1, 1))
        self.assertEqual((ref.player_before_monster, ref.monster_before_projectile, ref.projectile_before_status, ref.status_before_signature, ref.signature_before_present), (1, 1, 1, 1, 1))
        image = built_stage46_image()
        self.assertIn(b"LIVE44=1 OWN46=x86 ONCE46=1", image)
        self.assertIn(b"ORDER46=P-M-PRJ-ST-SIG-PRESENT ONCE46=1", image)

    def test_runtime_state_and_framebuffer_signatures_are_distinct_and_pinned(self) -> None:
        ref = self._ref()
        self.assertEqual(ref.signature, 2719909431)
        self.assertEqual(ref.state_signature, 4094043488)
        self.assertEqual([s.monster_state_signature for s in ref.samples], [2557949986, 3037306965, 2247320167, 29004293, 3810739213, 1892788599, 533767476])
        self.assertEqual([s.unified_state_signature for s in ref.samples], [1560044802, 2153923995, 1942825685, 2641348968, 2957418852, 1405647190, 3637274982])
        self.assertEqual([s.framebuffer_signature for s in ref.samples], [1154819706, 2382271357, 1757537078, 190720345, 3141461029, 3141461029, 3905320152])
        self.assertEqual(ref.distinct_monster_state_signatures, 7)
        self.assertEqual(ref.distinct_unified_state_signatures, 7)
        self.assertGreaterEqual(ref.distinct_framebuffer_signatures, 6)
        self.assertTrue(all(s.pre_marker_framebuffer_signature != s.framebuffer_signature for s in ref.samples))

    def test_stage45_through_stage19_baselines_are_preserved(self) -> None:
        ref = self._ref()
        self.assertEqual((ref.stage45.signature, ref.stage45.state_signature), (799763036, 1707493859))
        self.assertEqual([s.monster_decision_state_signature for s in ref.stage45.samples], list(stage.BASELINE_MSTATE45))
        self.assertEqual([s.stage45_unified_state_signature for s in ref.stage45.samples], list(stage.BASELINE_ULSTATE45))
        self.assertEqual([s.framebuffer_signature for s in ref.stage45.samples], list(stage.BASELINE_FB45))
        self.assertEqual((ref.stage44.signature, ref.stage44.state_signature), (1090523498, 904132091))
        r43 = ref.stage44.stage43
        r42 = r43.stage42
        r41 = r42.stage41
        r40 = r41.stage40
        r39 = r40.stage39
        self.assertEqual((r43.signature, r43.state_signature), (2916740242, 801364352))
        self.assertEqual((r42.signature, r42.state_signature), (2427416971, 2148021159))
        self.assertEqual((r41.signature, r41.state_signature), (951695045, 157977072))
        self.assertEqual((r40.signature, r40.state_signature), (2737672056, 268409133))
        self.assertEqual((r39.signature, r39.projectile.state_signature), (3469618451, 1403583302))
        self.assertEqual(ref.stage45.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)
        self.assertEqual((ref.stage45_preserved, ref.stage44_live_replay_preserved, ref.stage43_through_stage19_preserved), (1, 1, 1))

    def test_final_paint_deferred_scope_and_no_future_stage_string(self) -> None:
        ref = self._ref()
        self.assertEqual((ref.timer_samples, ref.paint_after_final_sample), (7, 1))
        self.assertIn("STEP46=7", stage._replay_titles(ref)[-1])
        self.assertIn("PAF46=1", stage._replay_titles(ref)[-1])
        self.assertEqual((ref.bounded_selected_thinker_only, ref.broad_deferred_systems_absent, ref.source_stage47_absent), (1, 1, 1))
        lower = built_stage46_image().lower()
        self.assertNotIn(b"source_stage47", lower)
        for forbidden in (
            b"generalized thinker implemented", b"generalized pathfinding implemented",
            b"generalized collision implemented", b"broad combat implemented",
            b"save/load implemented", b"networking implemented", b"real audio playback implemented",
        ):
            self.assertNotIn(forbidden, lower)

    def test_executable_contains_exact_stage46_evidence_and_pe32_header(self) -> None:
        image = built_stage46_image()
        output = write_stage46_exe()
        self.assertTrue(output.exists())
        self.assertEqual(image[:2], b"MZ")
        pe_offset = int.from_bytes(image[0x3C:0x40], "little")
        self.assertEqual(image[pe_offset:pe_offset + 4], b"PE\0\0")
        self.assertEqual(int.from_bytes(image[pe_offset + 4:pe_offset + 6], "little"), 0x14C)
        for marker in (
            b"source_stage46_repeatable_selected_monster_thinker_cadence_bridge",
            b"Repeatable Selected Monster Thinker Cadence Bridge proof OK",
            b"STEP46=4", b"AST46=S_SPOS_RUN2/T1->S_SPOS_RUN3/T3",
            b"NOMISSILE46=1", b"MOVE46=6:1:5",
            b"ATTEMPTS46=MOMD8", b"CURD2", b"NEWD7",
            b"STEP46=7", b"AST46=S_SPOS_RUN3/T1->S_SPOS_RUN4/T3",
            b"ATTACK46=0 DMG46=0 WHY46=SIGHT_BLOCKED_OR_NONZERO_MOVECOUNT",
            b"S46SIG=2719909431", b"STATE46=4094043488",
            b"S45SIG=799763036", b"STATE45=1707493859",
            b"MISS43=MT_TROOPSHOT", b"PATCH40=BAL1", b"S19SIG=2088411722",
            b"NOFULL46=1 NOSNAP46=1 S47ABS=1",
        ):
            self.assertIn(marker, image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reaches_final_paint_and_closes_cleanly(self) -> None:
        ref = self._ref()
        process = subprocess.Popen([str(write_stage46_exe())], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = collect_final_title(process.pid)
            self.assertIn("STEP46=7", title)
            self.assertIn("AST46=S_SPOS_RUN3/T1->S_SPOS_RUN4/T3", title)
            self.assertIn("NOMISSILE46=1", title)
            self.assertIn("MOVE46=1:1:0", title)
            self.assertIn("ATTACK46=0 DMG46=0 WHY46=SIGHT_BLOCKED_OR_NONZERO_MOVECOUNT", title)
            self.assertIn(f"MSTATE46={ref.samples[-1].monster_state_signature}", title)
            self.assertIn(f"ULSTATE46={ref.samples[-1].unified_state_signature}", title)
            self.assertIn(f"FB46={ref.samples[-1].framebuffer_signature}", title)
            self.assertIn(f"STATE46={ref.state_signature} S46SIG={ref.signature}", title)
            self.assertIn("ORDER46=P-M-PRJ-ST-SIG-PRESENT ONCE46=1 PAF46=1", title)
            self.assertIsNone(process.poll())
        finally:
            close_window(hwnd)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=3)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_live_launch_mutates_runtime_actor_once_per_accepted_tic_and_closes(self) -> None:
        process = subprocess.Popen([str(write_stage46_exe()), "-live"], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = collect_live_title(process.pid)
            match = re.search(r"TIC46=(\d+)", title)
            self.assertIsNotNone(match)
            self.assertGreaterEqual(int(match.group(1)), 7)
            self.assertIn("LIVE44=1 OWN46=x86 ONCE46=1", title)
            self.assertRegex(title, r"AST46=21[2-6]")
            self.assertRegex(title, r"MSTATE46=[1-9][0-9]*")
            self.assertRegex(title, r"FB46=[1-9][0-9]*")
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
