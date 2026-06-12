import os
import subprocess
import time
import unittest
from pathlib import Path

from tools.map_loader import LoadedMap, Sector
from tools import emit_source_stage14_game_loop_input_collision as stage14
from tools import emit_source_stage18_post_damage_monster_movement_and_chase_probe as stage18
from tools import emit_source_stage19_first_door_or_switch_sector_special_probe as stage


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


def _line(
    index: int,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    *,
    flags: int = stage.ML_TWOSIDED,
    special: int = 117,
    tag: int = 0,
    front: int = 0,
    back: int | None = 1,
    upper: str = "BIGDOOR1",
) -> stage.Stage19Line:
    v1x = x1 << stage.FRACBITS
    v1y = y1 << stage.FRACBITS
    v2x = x2 << stage.FRACBITS
    v2y = y2 << stage.FRACBITS
    dx = v2x - v1x
    dy = v2y - v1y
    return stage.Stage19Line(
        index=index,
        v1x=v1x,
        v1y=v1y,
        v2x=v2x,
        v2y=v2y,
        dx=dx,
        dy=dy,
        bbox=(max(v1y, v2y), min(v1y, v2y), min(v1x, v2x), max(v1x, v2x)),
        slopetype=stage14._slopetype(dx, dy),
        flags=flags,
        special=special,
        tag=tag,
        sidenum=(index * 2, stage.NO_SIDEDEF if back is None else index * 2 + 1),
        side_sectors=(front, back),
        side_upper=(upper, ""),
        side_lower=("-", "-"),
        side_middle=("-", "-"),
    )


def _world(
    *,
    lines: tuple[stage.Stage19Line, ...] = (),
    sectors: tuple[stage.Stage19Sector, ...] | None = None,
    force_nofit: bool = False,
) -> stage.Stage19World:
    if sectors is None:
        sectors = (
            stage.Stage19Sector(0, 0, 112 * stage.FRACUNIT),
            stage.Stage19Sector(1, 16 * stage.FRACUNIT, 16 * stage.FRACUNIT),
        )
    width = height = 4
    loaded = LoadedMap(
        name="SYN",
        source="synthetic",
        vertices=(),
        linedefs=(),
        sidedefs=(),
        sectors=tuple(
            Sector(
                sector.floorheight >> stage.FRACBITS,
                sector.ceilingheight >> stage.FRACBITS,
                "FLOOR",
                "CEIL",
                160,
                sector.special,
                sector.tag,
            )
            for sector in sectors
        ),
        things=(),
    )
    blockmap = stage14.BlockMap(
        origin_x=-128 * stage.FRACUNIT,
        origin_y=-128 * stage.FRACUNIT,
        width=width,
        height=height,
        shorts=(),
        offsets=(0,) * (width * height),
        lists=tuple(tuple(line.index for line in lines) for _ in range(width * height)),
    )
    return stage.Stage19World(
        loaded=loaded,
        blockmap=blockmap,
        sectors=[sector for sector in sectors],
        lines=[line for line in lines],
        sector_lines=stage.build_stage19_sector_lines(lines, len(sectors)),
        counters=stage.Stage19Counters(),
        force_change_sector_nofit=force_nofit,
    )


class SourceStage19FirstDoorSwitchSectorSpecialTests(unittest.TestCase):
    def test_source_trace_labels_name_stage19_use_door_and_moveplane_route(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("P_UseLines_PathTraverse_manual_door_source_shape_debug", labels)
        self.assertIn("P_UseSpecialLine_manual_vertical_door_source_shape_debug", labels)
        self.assertIn("EV_VerticalDoor_manual_blazing_door_source_shape_debug", labels)
        self.assertIn("T_MovePlane_ceiling_mutation_source_shape_debug", labels)

    def test_synthetic_use_line_path_front_back_block_pass_and_one_special_stop(self) -> None:
        front_world = _world(lines=(_line(0, 32, 32, 32, -32),))
        front_thing = stage.Stage19UseThing(0, 0, 0)
        front_path = stage.p_use_lines_stage19_source_shape(front_world, front_thing)
        self.assertEqual(front_path.stopped_by_line, 0)
        self.assertEqual((front_world.counters.use_special_calls, front_world.counters.manual_door_spawns), (1, 1))
        self.assertEqual(front_world.use_trace[0].side, 0)

        back_world = _world(lines=(_line(0, 32, 32, 32, -32),))
        west = stage.stage14.ANG90 * 2
        back_thing = stage.Stage19UseThing(64 * stage.FRACUNIT, 0, west)
        stage.p_use_lines_stage19_source_shape(back_world, back_thing)
        self.assertEqual((back_world.counters.back_side_rejections, back_world.counters.manual_door_spawns), (1, 0))
        self.assertEqual(back_world.use_trace[0].side, 1)

        blocked_world = _world(lines=(_line(0, 32, 32, 32, -32, flags=0, special=0, back=None),))
        stage.p_use_lines_stage19_source_shape(blocked_world, front_thing)
        self.assertEqual((blocked_world.counters.blocked_nonspecial_lines, blocked_world.counters.noway_sound_deferrals), (1, 1))
        self.assertEqual(blocked_world.counters.use_special_calls, 0)

        pass_world = _world(
            lines=(
                _line(0, 16, 32, 16, -32, special=0, back=2),
                _line(1, 32, 32, 32, -32),
            ),
            sectors=(
                stage.Stage19Sector(0, 0, 112 * stage.FRACUNIT),
                stage.Stage19Sector(1, 16 * stage.FRACUNIT, 16 * stage.FRACUNIT),
                stage.Stage19Sector(2, 0, 112 * stage.FRACUNIT),
            ),
        )
        stage.p_use_lines_stage19_source_shape(pass_world, front_thing)
        self.assertEqual((pass_world.counters.no_special_passes, pass_world.counters.manual_door_spawns), (1, 1))
        self.assertEqual(pass_world.use_trace[0].line_index, 1)

        stop_world = _world(
            lines=(
                _line(0, 32, 32, 32, -32),
                _line(1, 48, 32, 48, -32),
            )
        )
        stage.p_use_lines_stage19_source_shape(stop_world, front_thing)
        self.assertEqual((stop_world.counters.one_special_terminations, len(stop_world.use_trace)), (1, 1))
        self.assertEqual(stop_world.use_trace[0].line_index, 0)

    def test_synthetic_ev_vertical_door_spawn_locks_active_directions_topheight_and_sound(self) -> None:
        line = _line(0, 32, 32, 32, -32)
        world = _world(lines=(line,))
        thing = stage.Stage19UseThing(0, 0, 0)

        door = stage.ev_vertical_door_stage19_source_shape(world, line, thing)
        self.assertIsNotNone(door)
        assert door is not None
        self.assertEqual((door.sector_index, door.type, door.direction), (1, stage.VLD_BLAZE_RAISE, 1))
        self.assertEqual((door.topheight >> stage.FRACBITS, door.speed >> stage.FRACBITS, door.topwait), (108, 8, 150))
        self.assertEqual((world.counters.manual_door_spawns, world.counters.door_open_sound_deferrals), (1, 1))

        locked_line = _line(0, 32, 32, 32, -32, special=26)
        locked = _world(lines=(locked_line,))
        self.assertIsNone(stage.ev_vertical_door_stage19_source_shape(locked, locked_line, thing))
        self.assertEqual((locked.counters.locked_door_rejections, locked.counters.sound_start_deferrals), (1, 1))

        active_line = _line(0, 32, 32, 32, -32)
        active = _world(lines=(active_line,))
        active.sectors[1].specialdata = stage.Stage19DoorThinker(1, stage.VLD_BLAZE_RAISE, 108 * stage.FRACUNIT, 8 * stage.FRACUNIT, -1, 150)
        stage.ev_vertical_door_stage19_source_shape(active, active_line, thing)
        self.assertEqual((active.sectors[1].specialdata.direction, active.counters.already_active_reversals), (1, 1))

        closing = _world(lines=(active_line,))
        closing.sectors[1].specialdata = stage.Stage19DoorThinker(1, stage.VLD_BLAZE_RAISE, 108 * stage.FRACUNIT, 8 * stage.FRACUNIT, 1, 150)
        stage.ev_vertical_door_stage19_source_shape(closing, active_line, thing)
        self.assertEqual((closing.sectors[1].specialdata.direction, closing.counters.already_active_closures), (-1, 1))

    def test_synthetic_t_vertical_door_and_moveplane_mutation_pastdest_wait_and_crush_accounting(self) -> None:
        world = _world()
        door = stage.Stage19DoorThinker(1, stage.VLD_BLAZE_RAISE, 108 * stage.FRACUNIT, 8 * stage.FRACUNIT, 1, 150)
        trace = stage.t_vertical_door_stage19_source_shape(world, door)
        self.assertEqual((trace.ceiling_before >> stage.FRACBITS, trace.ceiling_after >> stage.FRACBITS), (16, 24))
        self.assertEqual((trace.result, world.counters.ceiling_mutations, world.counters.change_sector_checks), (stage.RESULT_OK, 1, 1))

        past_world = _world(
            sectors=(
                stage.Stage19Sector(0, 0, 112 * stage.FRACUNIT),
                stage.Stage19Sector(1, 16 * stage.FRACUNIT, 104 * stage.FRACUNIT),
            )
        )
        past_door = stage.Stage19DoorThinker(1, stage.VLD_BLAZE_RAISE, 108 * stage.FRACUNIT, 8 * stage.FRACUNIT, 1, 150)
        past = stage.t_vertical_door_stage19_source_shape(past_world, past_door)
        self.assertEqual((past.result, past.ceiling_after >> stage.FRACBITS), (stage.RESULT_PASTDEST, 108))
        self.assertEqual((past_door.direction, past_door.topcountdown, past_world.counters.wait_at_top_setups), (0, 150, 1))

        crush_world = _world(
            sectors=(
                stage.Stage19Sector(0, 0, 112 * stage.FRACUNIT),
                stage.Stage19Sector(1, 0, 64 * stage.FRACUNIT),
            ),
            force_nofit=True,
        )
        result = stage.t_move_plane_stage19_source_shape(crush_world, 1, 8 * stage.FRACUNIT, 0, False, 1, -1)
        self.assertEqual(result, stage.RESULT_CRUSHED)
        self.assertEqual(crush_world.sectors[1].ceilingheight >> stage.FRACBITS, 64)
        self.assertEqual((crush_world.counters.crush_events, crush_world.counters.change_sector_nofit), (1, 2))

    def test_synthetic_switch_and_button_paths_are_deferred_not_generalized(self) -> None:
        switch_line = _line(0, 32, 32, 32, -32, special=103, tag=4)
        world = _world(lines=(switch_line,))
        ok = stage.p_use_special_line_stage19_source_shape(world, stage.Stage19UseThing(0, 0, 0), switch_line, 0)
        self.assertTrue(ok)
        self.assertEqual((world.counters.tagged_door_deferrals, world.counters.switch_texture_deferrals), (1, 1))
        self.assertEqual(world.counters.manual_door_spawns, 0)

        button_line = _line(0, 32, 32, 32, -32, special=61, tag=4)
        button_world = _world(lines=(button_line,))
        stage.p_use_special_line_stage19_source_shape(button_world, stage.Stage19UseThing(0, 0, 0), button_line, 0)
        self.assertEqual((button_world.counters.switch_texture_deferrals, button_world.counters.button_start_deferrals), (1, 1))

    def test_pinned_map_stage19_reference_uses_line332_and_mutates_sector56_preserving_stage18(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_first_door_or_switch_sector_special_probe_for_pinned_map(PINNED_WAD)
        census = ref.census
        trace = ref.door_trace[-1]

        self.assertEqual(ref.stage18.signature, 1615679087)
        self.assertEqual(ref.stage18.stage17.signature, 2157381017)
        self.assertEqual((census.line_index, census.paired_line_index, census.special), (332, 330, 117))
        self.assertEqual((census.front_sector, census.target_sector, census.right_sidedef, census.left_sidedef), (55, 56, 490, 491))
        self.assertEqual(census.front_upper_texture, "BIGDOOR1")
        self.assertEqual((census.target_floor >> stage.FRACBITS, census.target_ceiling >> stage.FRACBITS), (16, 16))
        self.assertEqual((census.surrounding_lowest_ceiling >> stage.FRACBITS, census.topheight >> stage.FRACBITS), (112, 108))
        self.assertEqual((census.probe_x >> stage.FRACBITS, census.probe_y >> stage.FRACBITS, census.probe_angle_degrees), (1792, -160, 0))
        self.assertEqual((census.stage18_player_distance, census.stage18_player_in_userange), (456, 0))

        self.assertEqual((ref.path.stopped_by_line, len(ref.path.blocks), ref.counters.line_intercepts), (332, 1, 5))
        self.assertEqual((ref.use_trace[0].line_index, ref.use_trace[0].side, ref.use_trace[0].door_spawned), (332, 0, 1))
        self.assertEqual((ref.final_door.type, ref.final_door.speed >> stage.FRACBITS, ref.final_door.topwait), (stage.VLD_BLAZE_RAISE, 8, 150))
        self.assertEqual((trace.ceiling_before >> stage.FRACBITS, trace.ceiling_after >> stage.FRACBITS), (16, 24))
        self.assertEqual((trace.result, ref.counters.t_vertical_door_ticks, ref.counters.move_plane_calls), (stage.RESULT_OK, 1, 1))
        self.assertEqual((ref.counters.switch_texture_deferrals, ref.counters.button_start_deferrals), (0, 0))
        self.assertEqual((ref.counters.broad_special_deferrals, ref.counters.broad_door_switch_deferrals, ref.counters.broad_sector_effect_deferrals), (0, 0, 0))
        self.assertEqual(ref.signature, 2088411722)

    def test_executable_build_contains_stage19_status_preserves_stage18_and_omits_later_system_strings(self) -> None:
        image = stage.build_source_stage19_first_door_or_switch_sector_special_probe_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage19_first_door_or_switch_sector_special_probe", image)
        self.assertIn(b"First source-shaped manual door sector mutation OK", image)
        self.assertIn(b"P_UseLines", image)
        self.assertIn(b"EV_VerticalDoor", image)
        self.assertIn(b"T_MovePlane", image)
        self.assertIn(b" S18SIG=", image)
        self.assertIn(b" S19SIG=", image)
        self.assertIn(b" S19LINE=", image)
        self.assertIn(b" C191=", image)
        self.assertNotIn(b"source_stage20", lower)
        for forbidden in (
            b"generalized specials",
            b"generalized doors",
            b"generalized switches",
            b"generalized sector effects",
            b"audio playback",
            b"automap",
            b"menus",
            b"save/load",
            b"networking",
            b"live keyboard input",
            b"gcc:",
            b"mingw",
            b"microsoft visual c",
        ):
            self.assertNotIn(forbidden, lower)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage19_door_mutation_and_preserved_stage18(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_first_door_or_switch_sector_special_probe_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage19_first_door_or_switch_sector_special_probe.exe"
        stage.write_source_stage19_first_door_or_switch_sector_special_probe_exe(exe_path)

        expected = (
            f"S17SIG={ref.stage18.stage17.signature}",
            f"S18SIG={ref.stage18.signature}",
            f"S19SIG={ref.signature}",
            f"S19LINE={ref.census.line_index}",
            f"S19SEC={ref.census.target_sector}",
            "C191=24",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn(f"TRY18={ref.stage18.movement_counters.try_move_calls}", title)
            self.assertIn(f"MACC={ref.stage18.movement_counters.accepted_moves}", title)
            self.assertIn(f"PATH19={ref.counters.path_traverses}", title)
            self.assertIn(f"USE19={ref.counters.use_special_calls}", title)
            self.assertIn(f"VD19={ref.counters.vertical_door_calls}", title)
            self.assertIn(f"TOP19={ref.census.topheight >> stage.FRACBITS}", title)
            self.assertIn("SWDEF19=0", title)
            self.assertIn("GSECT19=0", title)
            self.assertIn("LIVE19=0", title)
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
