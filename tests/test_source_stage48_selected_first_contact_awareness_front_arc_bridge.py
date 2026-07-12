import os
import subprocess
import time
import unittest
from functools import lru_cache
from pathlib import Path

from tools import emit_source_stage48_selected_first_contact_awareness_front_arc_bridge as stage


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


@lru_cache(maxsize=1)
def built_stage48_image() -> bytes:
    return stage.build_source_stage48_selected_first_contact_awareness_front_arc_bridge_exe()


@lru_cache(maxsize=1)
def stage48_reference() -> stage.Stage48SelectedFirstContactAwarenessFrontArcBridgeReference:
    ref = stage._reference_for_default_wad_or_none()
    if ref is None:
        raise FileNotFoundError(PINNED_WAD)
    return ref


def write_stage48_exe() -> Path:
    stage.OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    image = built_stage48_image()
    if not stage.OUTPUT_PATH.exists() or stage.OUTPUT_PATH.read_bytes() != image:
        stage.OUTPUT_PATH.write_bytes(image)
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
        time.sleep(0.02)
    return 0, ""


def collect_title(pid: int, marker: str, timeout_seconds: float = 14.0) -> tuple[int, str]:
    deadline = time.monotonic() + timeout_seconds
    titles: list[str] = []
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.25)
        if title and (not titles or title != titles[-1]):
            titles.append(title)
        if marker in title:
            return hwnd, title
        time.sleep(0.02)
    raise TimeoutError(f"stage48 title marker {marker!r} not reached; saw {titles[-6:]!r}")


def close_window(hwnd: int) -> None:
    import ctypes

    if hwnd:
        ctypes.WinDLL("user32", use_last_error=True).PostMessageW(hwnd, 0x0010, 0, 0)


class SourceStage48SelectedFirstContactAwarenessFrontArcBridgeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage48SelectedFirstContactAwarenessFrontArcBridgeReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage48_reference()

    def test_source_trace_covers_player_landing_awareness_sight_state_render_and_present(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}
        for label in (
            "P_Ticker_stage48_player_selected_awareness_projectile_status_debug",
            "P_PlayerThink_P_MovePlayer_P_Thrust_stage48_runtime_owned_continuation_debug",
            "P_XYMovement_P_ZMovement_stage48_bounded_player_continuation_debug",
            "P_TryMove_stage48_collision_valid_acquisition_route_debug",
            "A_Look_P_LookForPlayers_stage48_front_arc_reject_then_acquire_debug",
            "P_CheckSight_stage48_selected_awareness_samples_debug",
            "info_stage48_bounded_S_POSS_STND_STND2_RUN1_table_debug",
            "V_DrawFilledBox_stage48_runtime_awareness_primitives_debug",
            "I_Video_stage48_present_after_final_acquisition_debug",
        ):
            self.assertIn(label, labels)

    def test_runtime_continuation_commands_are_minimal_bounded_family_and_player_owned(self) -> None:
        ref = self._ref()
        self.assertEqual(len(ref.commands), 63)
        self.assertTrue(all((c.forwardmove, c.sidemove, c.angleturn, c.buttons) == (25, 0, 640, 0) for c in ref.commands[:21]))
        self.assertTrue(all((c.forwardmove, c.sidemove, c.angleturn, c.buttons) == (25, 0, 0, 0) for c in ref.commands[21:]))
        self.assertEqual(stage.search_shortest_bounded_awareness_continuation_family(PINNED_WAD), (21, 63))
        final = ref.samples[-1]
        self.assertEqual((final.player_x, final.player_y, final.player_z, final.player_floorz), (27185001, 7807736, -4194304, -4194304))
        self.assertEqual((final.player_sector, final.player_subsector), (15, 242))
        self.assertEqual((ref.runtime_owned_player_continuation, ref.replay_live_command_ownership), (1, 1))

    def test_collision_valid_continuation_records_are_inputs_outcomes_not_snapshots(self) -> None:
        ref = self._ref()
        self.assertEqual(len(ref.collision_records), 63)
        self.assertEqual(sum(record.accepted for record in ref.collision_records), 63)
        self.assertEqual(ref.collision_valid_continuation, 1)
        self.assertGreater(sum(record.line_checks for record in ref.collision_records), 0)
        self.assertGreater(sum(record.line_visits for record in ref.collision_records), 0)
        fields = set(stage.Stage48CollisionRecord.__dataclass_fields__)
        self.assertEqual(fields, {"tic", "try_x", "try_y", "accepted", "subsector", "sector", "floorz", "ceilingz", "line_checks", "thing_checks", "line_visits", "thing_visits"})
        self.assertFalse(fields & {"angle", "momx", "momy", "state", "tics", "target", "health"})

    def test_initial_contact_visible_but_front_arc_rejects_before_awareness(self) -> None:
        ref47, world, actor = stage._contact_world_and_actor(PINNED_WAD)
        sight, relative, distance, strict_front, close = stage._sight_front_evidence(
            actor,
            stage._player_as_target(world),
            stage.load_map_from_file(PINNED_WAD, "MAP01"),
            stage.stage13.build_map_geometry(stage.WadFile.from_file(PINNED_WAD), stage.load_map_from_file(PINNED_WAD, "MAP01")),
            stage.WadFile.from_file(PINNED_WAD).read_lump(stage.WadFile.from_file(PINNED_WAD).map_lumps("MAP01").get("REJECT")),
        )
        self.assertEqual((ref47.signature, ref47.state_signature), (654580656, 1986136589))
        self.assertTrue(sight.visible)
        self.assertEqual((sight.nodes, sight.subsectors, sight.segs, sight.crossed_lines), (85, 32, 113, 6))
        self.assertAlmostEqual(relative * 360 / 2**32, 183.03, places=1)
        self.assertGreater(distance, stage.stage16.MELEERANGE)
        self.assertFalse(strict_front)
        self.assertFalse(close)

    def test_stand_cadence_a_look_slot_iteration_front_rejection_and_acquisition(self) -> None:
        ref = self._ref()
        self.assertEqual([record.tic for record in ref.look_records], [3, 13, 23, 33, 43, 53, 63])
        first = ref.look_records[0]
        self.assertEqual((first.player_checks, first.slots, first.lastlook_before, first.lastlook_after), (0, (1, 2, 3, 0), 1, 0))
        reject = ref.initial_contact_rejection
        self.assertEqual((reject.tic, reject.sight_visible, reject.front_rejects, reject.acquired), (13, 1, 2, 0))
        self.assertEqual((reject.sight_nodes, reject.sight_subsectors, reject.sight_segs, reject.sight_crossed_lines), (74, 27, 95, 8))
        self.assertEqual((reject.strict_front_arc, reject.close_range_override, reject.front_accept), (0, 0, 0))
        acquired = ref.acquisition_record
        self.assertEqual((acquired.tic, acquired.acquired, acquired.target_after), (63, 1, 0))
        self.assertEqual((acquired.state_after_name, acquired.tics_after), ("S_POSS_RUN1", 4))
        self.assertEqual((acquired.sight_nodes, acquired.sight_subsectors, acquired.sight_segs, acquired.sight_crossed_lines), (14, 1, 4, 0))
        self.assertEqual((acquired.strict_front_arc, acquired.close_range_override, acquired.front_accept), (0, 1, 1))
        self.assertEqual((ref.target_null_to_player0, ref.run1_transition, ref.see_sound_deferred, ref.chase_deferred_without_decision), (1, 1, 1, 1))

    def test_no_attack_damage_status_mutation_and_ordering(self) -> None:
        ref = self._ref()
        self.assertEqual(ref.no_attack_damage_status_mutation, 1)
        self.assertEqual(ref.ordering_preserved, 1)
        image = built_stage48_image().lower()
        for marker in (
            b"CHASE48=deferred_no_decision",
            b"ATTACK48=0",
            b"DMG48=0",
            b"STATUSMUT48=0",
        ):
            self.assertIn(marker.lower(), image)
        for forbidden in (
            b"a_posattack implemented",
            b"hitscan implemented",
            b"damage implemented",
            b"pain state reached",
            b"death state reached",
        ):
            self.assertNotIn(forbidden, image)

    def test_signatures_are_distinct_pinned_and_stage47_stage19_preserved(self) -> None:
        ref = self._ref()
        self.assertEqual((ref.signature, ref.state_signature), (1847800974, 944776482))
        self.assertEqual((ref.distinct_awareness_signatures, ref.distinct_unified_signatures, ref.distinct_framebuffer_signatures), (63, 63, 63))
        final = ref.samples[-1]
        self.assertEqual((final.awareness_state_signature, final.unified_state_signature, final.framebuffer_signature), (2179569613, 2022082875, 4057594050))
        self.assertEqual((ref.stage47.signature, ref.stage47.state_signature), (654580656, 1986136589))
        self.assertEqual((ref.stage47.samples[-1].route_state_signature, ref.stage47.samples[-1].unified_state_signature, ref.stage47.samples[-1].framebuffer_signature), (394107838, 4253428114, 48847643))
        self.assertEqual((ref.stage47_preserved, ref.stage46_through_stage19_preserved), (1, 1))
        self.assertEqual(ref.stage47.stage46.stage45.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)

    def test_no_snapshots_full_frame_copies_broad_systems_or_future_marker(self) -> None:
        ref = self._ref()
        source = Path(stage.__file__).read_text(encoding="utf-8").lower()
        image = built_stage48_image().lower()
        self.assertNotIn("source_stage49", source)
        self.assertNotIn(b"source_stage49", image)
        self.assertNotIn("stage48_sample0_player_x", source)
        self.assertNotIn("stage48_sample0_actor", source)
        self.assertEqual(image.count(b"\xf3\xa5"), 0)
        self.assertIn(b"no attack, damage, status mutation", image)
        self.assertEqual((ref.snapshots_absent, ref.full_frame_copies_absent, ref.broad_deferred_systems_absent, ref.future_stage_marker_absent), (1, 1, 1, 1))
        for forbidden in (
            b"generalized pathfinding implemented",
            b"generalized collision implemented",
            b"generalized rendering implemented",
            b"ui implemented",
            b"progression implemented",
            b"save/load implemented",
            b"networking implemented",
            b"real audio playback implemented",
        ):
            self.assertNotIn(forbidden, image)

    def test_executable_has_exact_stage48_evidence_and_pe32_x86_header(self) -> None:
        image = built_stage48_image()
        output = write_stage48_exe()
        self.assertTrue(output.exists())
        self.assertEqual(image[:2], b"MZ")
        pe_offset = int.from_bytes(image[0x3C:0x40], "little")
        self.assertEqual(image[pe_offset:pe_offset + 4], b"PE\0\0")
        self.assertEqual(int.from_bytes(image[pe_offset + 4:pe_offset + 6], "little"), 0x14C)
        for marker in (
            b"source_stage48_selected_first_contact_awareness_front_arc_bridge",
            b"Selected First Contact Awareness Front Arc Bridge proof OK",
            b"STEP48=63 TIC48=107 OWN48=x86",
            b"ROUTE48=21xF25A640+42xF25A0 MIN48=63 SEARCH48=bounded",
            b"ACT48=48/66:MT_POSSESSED AST48=S_POSS_STND/T3->S_POSS_RUN1/T4",
            b"LOOK48=7 SLOT48=1,2,3,0 FIRSTLOOK48=slotstop",
            b"TARGET48=NULL->P0 SFX48=see_deferred CHASE48=deferred_no_decision ATTACK48=0 DMG48=0 STATUSMUT48=0",
            b"ASTATE48=2179569613 ULSTATE48=2022082875 FB48=4057594050",
            b"STATE48=944776482 S48SIG=1847800974",
            b"S47SIG=654580656 STATE47=1986136589 RSTATE47=394107838 ULSTATE47=4253428114 FB47=48847643",
            b"ORDER48=P-A-PRJ-ST-SIG-PRESENT ONCE48=1 KEY48=finite2 NOFULL48=1 NOSNAP48=1",
            b"MISMATCH48=0 PAF48=1",
        ):
            self.assertIn(marker, image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_00_smoke_launch_reaches_final_acquisition_paint_and_closes_cleanly(self) -> None:
        process = subprocess.Popen([str(write_stage48_exe())], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = collect_title(process.pid, "STEP48=63")
            for marker in (
                "PXY48=414,119",
                "AST48=S_POSS_STND/T3->S_POSS_RUN1/T4",
                "TARGET48=NULL->P0",
                "CHASE48=deferred_no_decision ATTACK48=0 DMG48=0 STATUSMUT48=0",
                "ASTATE48=2179569613 ULSTATE48=2022082875 FB48=4057594050",
                "STATE48=944776482 S48SIG=1847800974",
                "S47SIG=654580656 STATE47=1986136589",
                "MISMATCH48=0 PAF48=1",
            ):
                self.assertIn(marker, title)
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
