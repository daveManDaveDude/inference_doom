import os
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage21_door_thinker_ticker_and_special_update_probe as stage


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


def _sector(floor: int = 16, ceiling: int = 16) -> stage.stage19.Stage19Sector:
    return stage.stage19.Stage19Sector(0, floor * stage.FRACUNIT, ceiling * stage.FRACUNIT)


def _ticker_world(*, ceiling: int = 16, paused: bool = False, menuactive: bool = False) -> stage.Stage21TickerWorld:
    world = stage.Stage21TickerWorld(
        sectors=[_sector(16, ceiling)],
        counters=stage.Stage21Counters(),
        paused=paused,
        menuactive=menuactive,
        consoleplayer_viewz=2 if menuactive else 1,
    )
    stage.p_init_thinkers_stage21_source_shape(world.thinker_list, world.counters)
    return world


def _door(
    *,
    ceiling_top: int = 108,
    door_type: int = stage.VLD_BLAZE_RAISE,
    direction: int = 1,
    topcountdown: int = 0,
) -> stage.Stage21DoorThinker:
    return stage.Stage21DoorThinker(
        sector_index=0,
        type=door_type,
        topheight=ceiling_top * stage.FRACUNIT,
        speed=8 * stage.FRACUNIT,
        direction=direction,
        topwait=150,
        topcountdown=topcountdown,
    )


class SourceStage21DoorThinkerTickerTests(unittest.TestCase):
    def test_source_trace_labels_name_ticker_door_update_route(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("P_Ticker_door_thinker_source_shape_debug", labels)
        self.assertIn("T_VerticalDoor_ticker_continuation_source_shape_debug", labels)
        self.assertIn("T_MovePlane_ticker_ceiling_mutation_source_shape_debug", labels)
        self.assertIn("P_UpdateSpecials_deferred_stage21_debug", labels)

    def test_synthetic_thinker_list_init_add_order_dispatch_lazy_remove_and_bound(self) -> None:
        counters = stage.Stage21Counters()
        thinkers = stage.Stage21ThinkerList()
        stage.p_init_thinkers_stage21_source_shape(thinkers, counters)
        self.assertIs(thinkers.cap.prev, thinkers.cap)
        self.assertIs(thinkers.cap.next, thinkers.cap)
        self.assertEqual((counters.cap_prev_self, counters.cap_next_self), (1, 1))

        calls: list[int] = []
        first = stage.Stage21ThinkerNode(1, "first", stage.THINKER_FUNCTION_DOOR, lambda node: calls.append(node.node_id))
        second = stage.Stage21ThinkerNode(2, "second", stage.THINKER_FUNCTION_DOOR, lambda node: calls.append(node.node_id))
        stage.p_add_thinker_stage21_source_shape(thinkers, first, counters)
        stage.p_add_thinker_stage21_source_shape(thinkers, second, counters)
        self.assertIs(thinkers.cap.next, first)
        self.assertIs(first.next, second)
        self.assertIs(second.next, thinkers.cap)

        world = stage.Stage21TickerWorld([_sector()], counters, thinkers)
        stage.p_run_thinkers_stage21_source_shape(world)
        self.assertEqual(calls, [1, 2])
        self.assertEqual((counters.thinker_add_calls, counters.thinker_dispatches), (2, 2))

        stage.p_remove_thinker_stage21_source_shape(first, counters)
        calls.clear()
        stage.p_run_thinkers_stage21_source_shape(world)
        self.assertEqual(calls, [2])
        self.assertIs(thinkers.cap.next, second)
        self.assertEqual((counters.lazy_removal_markers, counters.lazy_removals), (1, 1))

        mutate = _ticker_world()
        events: list[str] = []
        node_a = stage.Stage21ThinkerNode(10, "self_remove", stage.THINKER_FUNCTION_DOOR)
        node_b = stage.Stage21ThinkerNode(11, "after", stage.THINKER_FUNCTION_DOOR, lambda node: events.append("after"))

        def remove_self(node: stage.Stage21ThinkerNode) -> None:
            events.append("self")
            stage.p_remove_thinker_stage21_source_shape(node, mutate.counters)

        node_a.action = remove_self
        stage.p_add_thinker_stage21_source_shape(mutate.thinker_list, node_a, mutate.counters)
        stage.p_add_thinker_stage21_source_shape(mutate.thinker_list, node_b, mutate.counters)
        stage.p_run_thinkers_stage21_source_shape(mutate)
        self.assertEqual(events, ["self", "after"])
        self.assertEqual(mutate.counters.next_pointer_snapshots, 2)

        bounded = _ticker_world()
        looping = stage.Stage21ThinkerNode(20, "loop", stage.THINKER_FUNCTION_DOOR, lambda node: None)
        stage.p_add_thinker_stage21_source_shape(bounded.thinker_list, looping, bounded.counters)
        looping.next = looping
        stage.p_run_thinkers_stage21_source_shape(bounded, max_iterations=3)
        self.assertEqual((bounded.counters.last_run_iterations, bounded.counters.bounded_iteration_stops), (3, 1))

    def test_synthetic_door_ticker_repeated_upward_top_clamp_wait_and_removal_cases(self) -> None:
        world = _ticker_world()
        door = _door()
        stage.attach_stage21_door_thinker_source_shape(world, door)
        stage.p_ticker_stage21_source_shape(world)
        stage.p_ticker_stage21_source_shape(world)
        self.assertEqual([(t.ceiling_before >> stage.FRACBITS, t.ceiling_after >> stage.FRACBITS) for t in world.door_trace], [(16, 24), (24, 32)])
        self.assertEqual((door.direction, door.topcountdown), (1, 0))
        self.assertEqual((world.counters.door_close_transitions, world.counters.door_removal_requests), (0, 0))

        clamp = _ticker_world(ceiling=104)
        clamp_door = _door()
        stage.attach_stage21_door_thinker_source_shape(clamp, clamp_door)
        stage.p_ticker_stage21_source_shape(clamp)
        self.assertEqual((clamp.sectors[0].ceilingheight >> stage.FRACBITS, clamp_door.direction), (108, 0))
        self.assertEqual((clamp_door.topcountdown, clamp.counters.wait_at_top_setups), (150, 1))

        open_world = _ticker_world(ceiling=104)
        open_door = _door(door_type=stage.VLD_OPEN)
        stage.attach_stage21_door_thinker_source_shape(open_world, open_door)
        stage.p_ticker_stage21_source_shape(open_world)
        self.assertEqual((open_door.active, open_door.removal_requested), (0, 1))
        self.assertEqual((open_world.counters.door_removal_requests, open_world.counters.lazy_removals), (1, 0))
        stage.p_ticker_stage21_source_shape(open_world)
        self.assertEqual(open_world.counters.lazy_removals, 1)

    def test_synthetic_p_ticker_update_special_guards_and_source_order(self) -> None:
        paused = _ticker_world(paused=True)
        self.assertFalse(stage.p_ticker_stage21_source_shape(paused))
        self.assertEqual((paused.counters.pause_guard_returns, paused.counters.run_thinkers_calls), (1, 0))
        self.assertEqual(paused.leveltime, 0)

        menu = _ticker_world(menuactive=True)
        self.assertFalse(stage.p_ticker_stage21_source_shape(menu))
        self.assertEqual((menu.counters.menu_guard_returns, menu.counters.update_specials_calls), (1, 0))

        world = _ticker_world()
        self.assertTrue(stage.p_ticker_stage21_source_shape(world))
        self.assertEqual((world.counters.player_think_guards, world.counters.player_think_deferrals), (1, 1))
        self.assertEqual((world.counters.run_thinkers_calls, world.counters.update_specials_calls), (1, 1))
        self.assertEqual((world.counters.run_before_update_orders, world.leveltime), (1, 1))
        self.assertEqual((world.counters.animation_steps, world.counters.scroll_special_steps), (0, 0))
        self.assertEqual((world.counters.button_restore_steps, world.counters.respawn_specials_deferrals), (0, 1))

    def test_pinned_map_stage21_reference_clones_sector56_and_ticks_via_normal_ticker(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_door_thinker_ticker_and_special_update_probe_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.stage20.signature, 3226031347)
        self.assertEqual(ref.stage20.stage19.signature, 2088411722)
        self.assertEqual(ref.stage20.stage19.stage18.signature, 1615679087)
        self.assertEqual(ref.stage20.stage19.stage18.stage17.signature, 2157381017)
        self.assertEqual((ref.selected_sector, ref.cloned_door.sector_index), (56, 56))
        self.assertEqual((ref.cloned_door.type, ref.cloned_door.direction), (stage.VLD_BLAZE_RAISE, 1))
        self.assertEqual((ref.cloned_door.topheight >> stage.FRACBITS, ref.cloned_door.speed >> stage.FRACBITS), (108, 8))
        self.assertEqual(ref.cloned_door.topwait, 150)

        self.assertEqual([(t.ceiling_before >> stage.FRACBITS, t.ceiling_after >> stage.FRACBITS) for t in ref.door_trace], [(16, 24), (24, 32)])
        self.assertTrue(all(t.via_ticker for t in ref.door_trace))
        self.assertEqual((ref.counters.thinker_init_calls, ref.counters.thinker_add_calls, ref.counters.thinker_nodes), (1, 1, 1))
        self.assertEqual((ref.counters.ticker_calls, ref.counters.run_thinkers_calls, ref.counters.thinker_iterations), (2, 2, 2))
        self.assertEqual((ref.counters.t_vertical_door_ticks, ref.counters.move_plane_calls, ref.counters.ceiling_mutations), (2, 2, 2))
        self.assertEqual((ref.counters.update_specials_calls, ref.counters.run_before_update_orders), (2, 2))
        self.assertEqual((ref.counters.animation_steps, ref.counters.scroll_special_steps, ref.counters.button_restore_steps), (0, 0, 0))
        self.assertEqual((ref.counters.level_timer_exit_deferrals, ref.counters.respawn_specials_deferrals), (0, 2))
        self.assertEqual((ref.counters.door_close_transitions, ref.counters.door_removal_requests, ref.counters.new_sound_start_deferrals), (0, 0, 0))
        self.assertEqual((ref.leveltime_before, ref.leveltime_after, ref.order_ok), (0, 2, 1))
        self.assertEqual(ref.signature, 1770773845)

    def test_executable_build_contains_stage21_status_preserves_stage20_and_omits_later_system_strings(self) -> None:
        image = stage.build_source_stage21_door_thinker_ticker_and_special_update_probe_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage21_door_thinker_ticker_and_special_update_probe", image)
        self.assertIn(b"Door thinker ticker and special-update guard proof OK", image)
        self.assertIn(b"P_Ticker", image)
        self.assertIn(b"P_RunThinkers", image)
        self.assertIn(b"T_VerticalDoor", image)
        self.assertIn(b"T_MovePlane", image)
        self.assertIn(b"P_UpdateSpecials", image)
        self.assertIn(b" S19SIG=", image)
        self.assertIn(b" S20SIG=", image)
        self.assertIn(b" S21SIG=", image)
        self.assertIn(b" C210=", image)
        self.assertIn(b" C212=", image)
        self.assertNotIn(b"source_stage22", lower)
        for forbidden in (
            b"generalized specials",
            b"generalized doors",
            b"generalized switches",
            b"switch texture mutation",
            b"button restore",
            b"generalized sector effects",
            b"live keyboard input",
            b"menus",
            b"automap",
            b"save/load",
            b"networking",
            b"music",
            b"real audio playback",
            b"mixer/device playback",
            b"gcc:",
            b"mingw",
            b"microsoft visual c",
        ):
            self.assertNotIn(forbidden, lower)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage21_ticker_and_preserved_stage20_stage19(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_door_thinker_ticker_and_special_update_probe_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage21_door_thinker_ticker_and_special_update_probe.exe"
        stage.write_source_stage21_door_thinker_ticker_and_special_update_probe_exe(exe_path)

        expected = (
            f"S19SIG={ref.stage20.stage19.signature}",
            f"S20SIG={ref.stage20.signature}",
            f"S21SIG={ref.signature}",
            "S21SEC=56",
            "C210=16",
            "C212=32",
            "ORDER21=1",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn("S19LINE=332", title)
            self.assertIn("C191=24", title)
            self.assertIn("S20ID=88", title)
            self.assertIn("PTIC21=2", title)
            self.assertIn("RUN21=2", title)
            self.assertIn("TVD21=2", title)
            self.assertIn("MP21=2", title)
            self.assertIn("UPD21=2", title)
            self.assertIn("RESP21=2", title)
            self.assertIn("AUD21=0", title)
            self.assertIn("LIVE21=0", title)
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
