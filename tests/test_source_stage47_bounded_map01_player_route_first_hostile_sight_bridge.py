import os
import re
import subprocess
import time
import unittest
from functools import lru_cache
from pathlib import Path

from tools import emit_source_stage47_bounded_map01_player_route_first_hostile_sight_bridge as stage


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


@lru_cache(maxsize=1)
def built_stage47_image() -> bytes:
    return stage.build_source_stage47_bounded_map01_player_route_first_hostile_sight_bridge_exe()


@lru_cache(maxsize=1)
def stage47_reference() -> stage.Stage47BoundedMap01PlayerRouteFirstHostileSightBridgeReference:
    ref = stage._reference_for_default_wad_or_none()
    if ref is None:
        raise FileNotFoundError(PINNED_WAD)
    return ref


def write_stage47_exe() -> Path:
    stage.OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    image = built_stage47_image()
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


def collect_title(pid: int, marker: str, timeout_seconds: float = 12.0) -> tuple[int, str]:
    deadline = time.monotonic() + timeout_seconds
    titles: list[str] = []
    while time.monotonic() < deadline:
        hwnd, title = window_title_for_pid(pid, timeout_seconds=0.25)
        if title and (not titles or title != titles[-1]):
            titles.append(title)
        if marker in title:
            return hwnd, title
        time.sleep(0.02)
    raise TimeoutError(f"stage47 title marker {marker!r} not reached; saw {titles[-6:]!r}")


def close_window(hwnd: int) -> None:
    import ctypes

    if hwnd:
        ctypes.WinDLL("user32", use_last_error=True).PostMessageW(hwnd, 0x0010, 0, 0)


class SourceStage47BoundedMap01PlayerRouteFirstHostileSightBridgeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage47BoundedMap01PlayerRouteFirstHostileSightBridgeReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage47_reference()

    def test_source_trace_covers_player_collision_sight_order_render_and_present(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}
        files = {entry[0] for entry in stage.SOURCE_TRACE}
        for label in (
            "P_Ticker_stage47_player_visibility_selected_thinker_projectile_status_debug",
            "P_PlayerThink_P_MovePlayer_P_Thrust_stage47_runtime_owned_route_debug",
            "P_XYMovement_stage47_runtime_owned_player_momentum_debug",
            "P_TryMove_stage47_bounded_map01_route_collision_debug",
            "P_BlockIterators_stage47_real_map01_route_evidence_debug",
            "P_CheckSight_stage47_first_hostile_geometric_contact_debug",
            "P_RunThinkers_stage47_selected_stand_target_null_boundary_debug",
            "R_SetupFrame_stage47_finite_route_keyframes_debug",
            "V_DrawFilledBox_stage47_runtime_player_contact_primitives_debug",
            "I_Video_stage47_present_after_final_contact_debug",
        ):
            self.assertIn(label, labels)
        for filename in ("p_tick.c", "p_user.c", "p_mobj.c", "p_map.c", "p_maputl.c", "p_sight.c", "r_main.c", "v_video.c", "i_video.c"):
            self.assertTrue(any(path.endswith(filename) for path in files), filename)

    def test_runtime_owned_44_tic_route_uses_stage44_prefix_plus_41_forward_commands(self) -> None:
        ref = self._ref()
        self.assertEqual(len(ref.commands), 44)
        self.assertEqual(
            [(c.forwardmove, c.sidemove, c.angleturn, c.buttons) for c in ref.commands[:3]],
            [(0, 0, 0, 0), (25, 0, -320, 0), (25, 0, 320, 2)],
        )
        self.assertTrue(all((c.forwardmove, c.sidemove, c.angleturn, c.buttons) == (25, 0, 0, 0) for c in ref.commands[3:]))
        final = ref.samples[-1]
        self.assertEqual((final.x, final.y, final.angle, final.momx, final.momy), (5560497, -12593285, 0, 520295, 106))
        self.assertEqual((final.x >> 16, final.y >> 16, final.sector, final.subsector), (84, -193, 9, 236))
        self.assertEqual((ref.runtime_owned_player_fields, ref.replay_live_command_ownership), (1, 1))
        self.assertEqual(len({(sample.x, sample.y, sample.momx, sample.momy) for sample in ref.samples}), 44)

    def test_real_map01_collision_records_are_inputs_outcomes_and_all_route_moves_accept(self) -> None:
        ref = self._ref()
        self.assertEqual(len(ref.collision_records), 43)
        self.assertEqual(sum(sample.try_move_calls for sample in ref.samples), 43)
        self.assertEqual(sum(sample.accepted_moves for sample in ref.samples), 43)
        self.assertEqual(sum(sample.rejected_moves for sample in ref.samples), 0)
        self.assertTrue(all(record.accepted == 1 for record in ref.collision_records))
        self.assertEqual((ref.collision_inputs_outcomes_only, ref.complete_player_actor_snapshots_absent), (1, 1))
        self.assertGreater(sum(record.line_checks for record in ref.collision_records), 0)
        self.assertGreater(sum(record.line_visits for record in ref.collision_records), 0)
        fields = set(stage.Stage47CollisionRecord.__dataclass_fields__)
        self.assertEqual(fields, {"tic", "try_x", "try_y", "accepted", "subsector", "sector", "line_checks", "thing_checks", "line_visits", "thing_visits"})
        self.assertFalse(fields & {"angle", "momx", "momy", "state", "tics", "target"})

    def test_first_sight_is_minimal_across_all_18_monsters(self) -> None:
        ref = self._ref()
        self.assertEqual(ref.monster_count, 18)
        self.assertEqual(ref.first_sight_tic, 44)
        self.assertEqual(ref.precontact_sight_checks, 43 * 18)
        self.assertEqual(ref.precontact_visible_results, 0)
        self.assertEqual(ref.contact_visible_count, 1)
        self.assertEqual(ref.total_sight_checks, 44 * 18)
        self.assertTrue(all(sample.visibility_mask == 0 and sample.visible_count == 0 for sample in ref.samples[:-1]))
        self.assertEqual((ref.samples[-1].visibility_mask, ref.samples[-1].visible_count), (1 << 11, 1))

    def test_exact_contact_actor_bsp_and_stand_target_null_evidence(self) -> None:
        ref = self._ref()
        actor = ref.contact_record
        self.assertEqual((actor.mobj_index, actor.mapthing_index, actor.type_name), (48, 66, "MT_POSSESSED"))
        self.assertEqual((actor.x >> 16, actor.y >> 16, actor.angle_degrees), (416, 176, 45))
        self.assertEqual((actor.spawn_state_name, actor.spawn_tics, actor.spawn_lastlook), ("S_POSS_STND", 3, 1))
        self.assertEqual((actor.sight.visible, actor.sight.bsp_accept), (True, 1))
        self.assertEqual((actor.sight.nodes, actor.sight.subsectors, actor.sight.segs, actor.sight.crossed_lines), (85, 32, 113, 6))
        self.assertEqual((ref.target_is_null, ref.stand_state_preserved, ref.awareness_transition_absent), (1, 1, 1))
        self.assertEqual(ref.attack_damage_status_mutation_absent, 1)

    def test_player_visibility_thinker_projectile_status_signature_present_order(self) -> None:
        ref = self._ref()
        for sample in ref.samples:
            self.assertLess(sample.player_sequence, sample.visibility_sequence)
            self.assertLess(sample.visibility_sequence, sample.selected_thinker_sequence)
            self.assertLess(sample.selected_thinker_sequence, sample.projectile_sequence)
            self.assertLess(sample.projectile_sequence, sample.status_sequence)
            self.assertLess(sample.status_sequence, sample.signature_sequence)
            self.assertLess(sample.signature_sequence, sample.present_sequence)
        self.assertEqual(ref.ordering_preserved, 1)
        source = Path(stage.__file__).read_text(encoding="utf-8")
        ticker = source[source.index('pe.label("P_Ticker_stage47_'):source.index("def _emit_fnv_words")]
        calls = [
            ticker.index("P_PlayerThink_P_MovePlayer_P_Thrust_stage47"),
            ticker.index("P_CheckSight_stage47"),
            ticker.index("P_RunThinkers_stage47"),
        ]
        self.assertEqual(calls, sorted(calls))

    def test_route_unified_and_framebuffer_signatures_are_distinct_and_pinned(self) -> None:
        ref = self._ref()
        self.assertEqual((ref.signature, ref.state_signature), (654580656, 1986136589))
        self.assertEqual((ref.distinct_route_state_signatures, ref.distinct_unified_state_signatures, ref.distinct_framebuffer_signatures), (44, 44, 44))
        final = ref.samples[-1]
        self.assertEqual((final.route_state_signature, final.unified_state_signature, final.framebuffer_signature), (394107838, 4253428114, 48847643))
        self.assertEqual(ref.finite_render_keyframes, (1, 2, 32, 44))
        self.assertEqual([ref.samples[index - 1].render_keyframe for index in ref.finite_render_keyframes], [0, 1, 2, 2])

    def test_stage46_through_stage19_baselines_are_preserved(self) -> None:
        ref = self._ref()
        r46 = ref.stage46
        self.assertEqual((r46.signature, r46.state_signature), (2719909431, 4094043488))
        self.assertEqual(tuple(sample.monster_state_signature for sample in r46.samples), stage.BASELINE_MSTATE46)
        self.assertEqual(tuple(sample.unified_state_signature for sample in r46.samples), stage.BASELINE_ULSTATE46)
        self.assertEqual(tuple(sample.framebuffer_signature for sample in r46.samples), stage.BASELINE_FB46)
        self.assertEqual((r46.stage45.signature, r46.stage45.state_signature), (799763036, 1707493859))
        self.assertEqual((r46.stage44.signature, r46.stage44.state_signature), (1090523498, 904132091))
        self.assertEqual(r46.stage45.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)
        self.assertEqual((ref.stage46_preserved, ref.stage45_through_stage19_preserved), (1, 1))

    def test_no_snapshots_full_frames_deferred_broad_systems_or_future_marker(self) -> None:
        ref = self._ref()
        source = Path(stage.__file__).read_text(encoding="utf-8").lower()
        image = built_stage47_image().lower()
        self.assertNotIn("source_stage48", source)
        self.assertNotIn(b"source_stage48", image)
        self.assertNotIn("stage47_sample0_player_x", source)
        self.assertNotIn("stage47_sample0_actor", source)
        self.assertNotIn(b"stage47_sample0_player", image)
        self.assertNotIn(b"stage47_sample0_actor", image)
        self.assertEqual(image.count(b"\xf3\xa5"), 0)
        self.assertIn(b"no complete player or actor frames", image)
        self.assertEqual((ref.full_frame_byte_arrays_absent, ref.broad_deferred_systems_absent, ref.future_stage_marker_absent), (1, 1, 1))
        for forbidden in (
            b"generalized pathfinding implemented",
            b"generalized collision implemented",
            b"target acquisition implemented",
            b"attack implemented",
            b"damage implemented",
            b"save/load implemented",
            b"networking implemented",
            b"real audio playback implemented",
        ):
            self.assertNotIn(forbidden, image)

    def test_executable_has_exact_stage47_evidence_and_pe32_x86_header(self) -> None:
        image = built_stage47_image()
        output = write_stage47_exe()
        self.assertTrue(output.exists())
        self.assertEqual(image[:2], b"MZ")
        pe_offset = int.from_bytes(image[0x3C:0x40], "little")
        self.assertEqual(image[pe_offset:pe_offset + 4], b"PE\0\0")
        self.assertEqual(int.from_bytes(image[pe_offset + 4:pe_offset + 6], "little"), 0x14C)
        for marker in (
            b"source_stage47_bounded_map01_player_route_first_hostile_sight_bridge",
            b"Bounded MAP01 Player Route First Hostile Sight Bridge proof OK",
            b"STEP47=44 TIC47=44 OWN47=x86",
            b"PXY47=84,-193 PA47=0 PMOM47=520295,106 PSEC47=9/236",
            b"COLL47=43:43:0 REALMAP47=1 FIRST47=44/44 MIN47=774:0 ALLMON47=18",
            b"ACT47=48/66:MT_POSSESSED@416,176/A45",
            b"SIGHT47=1:BSP1/N85/SS32/SEG113/X6",
            b"AST47=S_POSS_STND/T3 TARGET47=NULL AWARE47=0 ATTACK47=0 DMG47=0 STATUSMUT47=0",
            b"RSTATE47=394107838 ULSTATE47=4253428114 FB47=48847643",
            b"STATE47=1986136589 S47SIG=654580656",
            b"S46SIG=2719909431 STATE46=4094043488",
            b"ORDER47=P-V-M-PRJ-ST-SIG-PRESENT ONCE47=1 KEY47=finite4 NOFULL47=1 NOSNAP47=1",
            b"MISMATCH47=0 PAF47=1",
        ):
            self.assertIn(marker, image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_00_smoke_launch_reaches_final_contact_paint_and_closes_cleanly(self) -> None:
        process = subprocess.Popen([str(write_stage47_exe())], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = collect_title(process.pid, "STEP47=44")
            for marker in (
                "PXY47=84,-193",
                "FIRST47=44/44 MIN47=774:0 ALLMON47=18",
                "ACT47=48/66:MT_POSSESSED@416,176/A45",
                "SIGHT47=1:BSP1/N85/SS32/SEG113/X6",
                "AST47=S_POSS_STND/T3 TARGET47=NULL AWARE47=0 ATTACK47=0 DMG47=0 STATUSMUT47=0",
                "RSTATE47=394107838 ULSTATE47=4253428114 FB47=48847643",
                "STATE47=1986136589 S47SIG=654580656",
                "ORDER47=P-V-M-PRJ-ST-SIG-PRESENT ONCE47=1",
                "MISMATCH47=0 PAF47=1",
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

    def test_live_gamekeydown_ticcmd_ownership_feeds_the_runtime_player_path(self) -> None:
        bridge = stage.stage44.Stage44CommandBridgeState()
        counters = stage.stage44.Stage44Counters()
        keys = stage.stage44.Stage44KeyState(forward=True, turn_left=True, use=True)
        command = stage.stage44.g_build_ticcmd_stage44_live_or_replay_bridge_source_shape(
            bridge,
            counters,
            replay=False,
            live_keys=keys,
            tic=1,
            source_index=0,
        )
        self.assertEqual((command.forwardmove, command.sidemove, command.angleturn, command.buttons), (25, 0, 320, 2))
        self.assertEqual(counters.manual_commands_built, 1)
        source = Path(stage.__file__).read_text(encoding="utf-8")
        live_branch = source[source.index('pe.label("stage47_command_live")'):source.index("def emit_stage47_thrust")]
        for marker in (
            "G_BuildTiccmd_stage44_live_runtime_debug",
            "stage44_live_forwardmove",
            "stage44_live_sidemove",
            "stage44_live_angleturn",
            "stage44_live_buttons",
            "stage47_cmd_forwardmove",
        ):
            self.assertIn(marker, live_branch)
        self.assertIn(b"LIVE44=1 OWN47=x86", built_stage47_image())


if __name__ == "__main__":
    unittest.main()
