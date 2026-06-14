import os
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage28_live_input_to_deterministic_game_loop_bridge as stage


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


def window_title_for_pid(
    pid: int, expected: tuple[str, ...] = (), timeout_seconds: float = 5.0
) -> tuple[int, str]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    deadline = time.monotonic() + timeout_seconds
    last_seen = ""

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
                return False
            return True

        user32.EnumWindows(enum_proc, 0)
        if found:
            hwnd, title = found[0]
            last_seen = title
            if not expected or all(fragment in title for fragment in expected):
                return hwnd, title
        time.sleep(0.1)

    raise TimeoutError(f"no matching visible window title found for pid {pid}: {last_seen!r}")


class SourceStage28LiveInputBridgeTests(unittest.TestCase):
    def _ref(self) -> stage.Stage28LiveInputBridgeReference:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        return stage.reference_live_input_to_deterministic_game_loop_bridge_for_pinned_map(PINNED_WAD)

    def test_source_trace_labels_name_input_bridge_route(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}
        self.assertIn("D_PostEvent_stage28_live_key_state_bridge_source_shape_debug", labels)
        self.assertIn("G_BuildTiccmd_stage28_live_or_replay_bridge_source_shape_debug", labels)
        self.assertIn("P_PlayerThink_stage28_bridge_usedown_source_shape_debug", labels)
        self.assertIn("G_Ticker_stage28_bridge_room_loop_source_shape_debug", labels)

    def test_synthetic_key_down_up_state(self) -> None:
        bridge = stage.Stage28CommandBridgeState()
        stage.d_post_event_stage28_live_key_state_bridge_source_shape(bridge, "forward", True)
        self.assertTrue(stage._key_state_from_bridge(bridge).forward)
        stage.d_post_event_stage28_live_key_state_bridge_source_shape(bridge, "forward", False)
        self.assertFalse(stage._key_state_from_bridge(bridge).forward)
        self.assertEqual(bridge.live_key_events, 2)

    def test_synthetic_forward_back_turn_use_ticcmd_fields(self) -> None:
        counters = stage.Stage28Counters()
        bridge = stage.Stage28CommandBridgeState()
        cmd = stage.g_build_ticcmd_stage28_live_or_replay_bridge_source_shape(
            bridge,
            counters,
            replay=False,
            live_keys=stage.Stage28KeyState(forward=True, turn_right=True, use=True),
        )
        self.assertEqual((cmd.forwardmove, cmd.angleturn, cmd.buttons), (stage.FORWARDMOVE, -stage.SLOW_ANGLETURN, stage.BT_USE))
        self.assertEqual((counters.manual_forward_fields, counters.manual_turn_fields, counters.manual_bt_use_commands), (1, 1, 1))

        cmd = stage.g_build_ticcmd_stage28_live_or_replay_bridge_source_shape(
            bridge,
            counters,
            replay=False,
            live_keys=stage.Stage28KeyState(back=True, turn_left=True),
        )
        self.assertEqual((cmd.forwardmove, cmd.angleturn, cmd.buttons), (-stage.FORWARDMOVE, stage.SLOW_ANGLETURN, 0))
        self.assertEqual((counters.manual_back_fields, counters.manual_turn_fields), (1, 2))

    def test_synthetic_bt_use_edge_usedown_gating(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")
        world = stage._build_stage28_world(stage.WadFile.from_file(PINNED_WAD), stage.SELECTED_MAP)
        use = stage.stage27.Stage27Ticcmd(buttons=stage.BT_USE)
        stage.p_player_think_stage28_bridge_usedown_source_shape(world, use, manual=False)
        stage.p_player_think_stage28_bridge_usedown_source_shape(world, use, manual=False)
        stage.p_player_think_stage28_bridge_usedown_source_shape(world, stage.stage27.Stage27Ticcmd(), manual=False)
        stage.p_player_think_stage28_bridge_usedown_source_shape(world, use, manual=False)
        self.assertEqual((world.counters.player_use_edges, world.counters.player_use_held_skips), (2, 1))

    def test_synthetic_replay_ignores_live_key_state_and_reaches_stage27_route(self) -> None:
        ref = self._ref()
        self.assertEqual(ref.replay_signature, 1735738182)
        self.assertEqual(ref.counters.replay_commands_built, 136)
        self.assertEqual(ref.counters.replay_ignored_live_key_state, 136)
        self.assertEqual(stage._stage28_log_text(ref.samples), stage._stage28_log_text(ref.stage27.samples))
        self.assertIn("1:F-12:B34:SW2STRTN:S1:C0", stage._stage28_log_text(ref.samples))
        self.assertIn("136:F-8:B0:SW1STRTN:S2:C105", stage._stage28_log_text(ref.samples))

    def test_synthetic_manual_mode_can_emit_bt_use_and_movement(self) -> None:
        counters = stage.Stage28Counters()
        bridge = stage.Stage28CommandBridgeState()
        stage.d_post_event_stage28_live_key_state_bridge_source_shape(bridge, "forward", True)
        stage.d_post_event_stage28_live_key_state_bridge_source_shape(bridge, "use", True)
        cmd = stage.g_build_ticcmd_stage28_live_or_replay_bridge_source_shape(bridge, counters, replay=False)
        self.assertEqual((cmd.forwardmove, cmd.buttons), (stage.FORWARDMOVE, stage.BT_USE))
        self.assertEqual(counters.manual_live_input_enabled, 1)
        if cmd.buttons & stage.BT_USE and not bridge.usedown:
            counters.manual_use_edges += 1
            bridge.usedown = True
        self.assertEqual(counters.manual_use_edges, 1)

    def test_stage28_preserves_stage27_post_launch_stepping_titles(self) -> None:
        ref = self._ref()
        titles = stage._stage28_replay_titles(ref)
        self.assertEqual(len(titles), 6)
        self.assertIn("S28 REPLAY STEP28=1", titles[0])
        self.assertIn("TIC28=1", titles[0])
        self.assertIn("S28 REPLAY STEP28=6", titles[-1])
        self.assertIn("TIC28=136", titles[-1])
        self.assertIn("LIVE28=0", titles[-1])

    def test_pinned_replay_preserves_stage27_through_stage19_signatures(self) -> None:
        ref = self._ref()
        self.assertEqual(ref.stage27.signature, 1735738182)
        self.assertEqual(ref.stage27.stage26.signature, 132405987)
        self.assertEqual(ref.stage27.stage26.stage25.signature, 1688844032)
        self.assertEqual(ref.stage27.stage26.stage25.stage24.signature, 1919312263)
        self.assertEqual(ref.stage27.stage26.stage25.stage24.stage23.signature, 3216085132)
        self.assertEqual(ref.stage27.stage26.stage25.stage24.stage23.stage22.signature, 2207028069)
        self.assertEqual(ref.stage27.stage26.stage25.stage24.stage23.stage22.stage21.signature, 1770773845)
        self.assertEqual(ref.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.signature, 3226031347)
        self.assertEqual(ref.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)
        self.assertEqual(ref.signature, 2805406010)

    def test_executable_build_contains_stage28_status_and_no_stage29_strings(self) -> None:
        image = stage.build_source_stage28_live_input_to_deterministic_game_loop_bridge_exe()
        lower = image.lower()
        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage28_live_input_to_deterministic_game_loop_bridge", image)
        self.assertIn(b"Live input to deterministic game loop bridge proof OK", image)
        self.assertIn(b"S28 REPLAY START STEP28=0", image)
        self.assertIn(b"S28 REPLAY STEP28=1", image)
        self.assertIn(b"S28 REPLAY STEP28=6", image)
        self.assertIn(b"LIVE28=0", image)
        self.assertIn(b"MANUAL LIVE28=1", image)
        self.assertIn(b"BTUSE28=", image)
        self.assertIn(b"S28SIG=", image)
        for marker in (b" S19SIG=", b" S20SIG=", b" S21SIG=", b" S22SIG=", b" S23SIG=", b" S24SIG=", b" S25SIG=", b" S26SIG=", b" S27SIG="):
            self.assertIn(marker, image)
        self.assertNotIn(b"source_stage29", lower)
        for forbidden in (b"gcc:", b"mingw", b"microsoft visual c", b"real audio playback", b"mixer/device playback"):
            self.assertNotIn(forbidden, lower)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage28_replay_start_final_and_preserved_signatures(self) -> None:
        ref = self._ref()
        exe_path = REPO_ROOT / "build" / "source_stage28_live_input_to_deterministic_game_loop_bridge.exe"
        stage.write_source_stage28_live_input_to_deterministic_game_loop_bridge_exe(exe_path)
        expected = (
            "STEP28=6",
            "LIVE28=0",
            "TIC28=136",
            "F28=-8",
            "TEX28=SW1STRTN",
            f"S27SIG={ref.stage27.signature}",
            f"S28SIG={ref.signature}",
            "S19SIG=2088411722",
            "S20SIG=3226031347",
            "S21SIG=1770773845",
            "S22SIG=2207028069",
            "S23SIG=3216085132",
            "S24SIG=1919312263",
            "S25SIG=1688844032",
            "S26SIG=132405987",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, start_title = window_title_for_pid(process.pid, expected=("S28 REPLAY START", "STEP28=0", "LIVE28=0"), timeout_seconds=1.5)
            self.assertIn("bridge-driven deterministic loop", start_title)
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn("S28 REPLAY STEP28=6", title)
            self.assertIn("COUNT28=105", title)
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
