import os
import subprocess
import time
import unittest
from pathlib import Path

from tools.map_loader import LoadedMap, Sector
from tools import emit_source_stage14_game_loop_input_collision as stage14
from tools import emit_source_stage24_first_floor_sector_special_probe as stage


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
    index: int = 0,
    *,
    special: int = 60,
    tag: int = 6,
    front: int = 0,
    right: int = 0,
) -> stage.stage19.Stage19Line:
    v1x = 32 << stage.FRACBITS
    v1y = 32 << stage.FRACBITS
    v2x = 32 << stage.FRACBITS
    v2y = -32 << stage.FRACBITS
    dx = v2x - v1x
    dy = v2y - v1y
    return stage.stage19.Stage19Line(
        index=index,
        v1x=v1x,
        v1y=v1y,
        v2x=v2x,
        v2y=v2y,
        dx=dx,
        dy=dy,
        bbox=(max(v1y, v2y), min(v1y, v2y), min(v1x, v2x), max(v1x, v2x)),
        slopetype=stage14._slopetype(dx, dy),
        flags=0,
        special=special,
        tag=tag,
        sidenum=(right, stage.NO_SIDEDEF),
        side_sectors=(front, None),
        side_upper=("-", ""),
        side_lower=("-", ""),
        side_middle=("SW1BROWN", ""),
    )


def _adjacency_line(index: int, sector: int, other: int) -> stage.stage19.Stage19Line:
    line = _line(index, special=0, tag=0, front=sector, right=index)
    return stage.stage19.Stage19Line(
        **{
            **line.__dict__,
            "flags": stage.stage19.ML_TWOSIDED,
            "sidenum": (index, index + 100),
            "side_sectors": (sector, other),
        }
    )


def _world(
    *,
    line: stage.stage19.Stage19Line | None = None,
    sectors: tuple[stage.stage19.Stage19Sector, ...] | None = None,
    side: stage.stage22.Stage22SideDefTextures | None = None,
    extra_lines: tuple[stage.stage19.Stage19Line, ...] = (),
) -> stage.Stage24World:
    if line is None:
        line = _line()
    if sectors is None:
        sectors = (
            stage.stage19.Stage19Sector(0, 0, 144 * stage.FRACUNIT),
            stage.stage19.Stage19Sector(1, 16 * stage.FRACUNIT, 144 * stage.FRACUNIT, tag=6),
            stage.stage19.Stage19Sector(2, -48 * stage.FRACUNIT, 144 * stage.FRACUNIT),
        )
    loaded = LoadedMap(
        name="SYN",
        source="synthetic",
        vertices=(),
        linedefs=(),
        sidedefs=(),
        sectors=tuple(
            Sector(s.floorheight >> stage.FRACBITS, s.ceilingheight >> stage.FRACBITS, "F", "C", 160, s.special, s.tag)
            for s in sectors
        ),
        things=(),
    )
    lines = (line,) + extra_lines
    blockmap = stage14.BlockMap(
        origin_x=-128 * stage.FRACUNIT,
        origin_y=-128 * stage.FRACUNIT,
        width=4,
        height=4,
        shorts=(),
        offsets=(0,) * 16,
        lists=tuple(tuple(l.index for l in lines) for _ in range(16)),
    )
    base = stage.stage19.Stage19World(
        loaded=loaded,
        blockmap=blockmap,
        sectors=[s for s in sectors],
        lines=[l for l in lines],
        sector_lines=stage.stage19.build_stage19_sector_lines(lines, len(sectors)),
        counters=stage.stage19.Stage19Counters(),
    )
    pair = stage.stage22.Stage22SwitchPair(4, 4, "SW1BROWN", "SW2BROWN", 1, 2)
    switchlist, names = stage.stage22._flatten_switchlist((pair,))
    world = stage.Stage24World(
        base=base,
        side_textures=[side or stage.stage22.Stage22SideDefTextures(0, 0, 1)],
        switch_pairs=(pair,),
        switchlist=switchlist,
        switchlist_names=names,
        texture_name_by_id={0: "-", 1: "SW1BROWN", 2: "SW2BROWN", 99: "OTHER"},
        counters=stage.Stage24Counters(switchlist_init_calls=1, switch_pairs_available=1, switchlist_entries=2),
    )
    return world


class SourceStage24FirstFloorSectorSpecialTests(unittest.TestCase):
    def test_source_trace_labels_name_floor_route(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("P_UseSpecialLine_button60_lowerFloorToLowest_source_shape_debug", labels)
        self.assertIn("EV_DoFloor_lowerFloorToLowest_stage24_source_shape_debug", labels)
        self.assertIn("P_FindLowestFloorSurrounding_stage24_source_shape_debug", labels)
        self.assertIn("T_MoveFloor_lowerFloorToLowest_stage24_source_shape_debug", labels)
        self.assertIn("T_MovePlane_floor_down_stage24_source_shape_debug", labels)

    def test_synthetic_ev_do_floor_setup_tag_duplicate_and_no_match_boundaries(self) -> None:
        line = _line()
        world = _world(line=line, extra_lines=(_adjacency_line(1, 1, 2),))
        self.assertEqual(stage.ev_do_floor_stage24_source_shape(world, line, stage.LOWER_FLOOR_TO_LOWEST), 1)

        floor = world.selected_floor
        self.assertIsNotNone(floor)
        assert floor is not None
        self.assertEqual((world.floor_spawn.matched_sectors, world.floor_spawn.spawned_sectors), ((1,), (1,)))
        self.assertEqual((floor.sector_index, floor.direction, floor.speed >> stage.FRACBITS), (1, -1, 1))
        self.assertEqual(floor.floordestheight >> stage.FRACBITS, -48)
        self.assertEqual((world.counters.floor_thinker_records, world.ticker_world.counters.thinker_nodes), (1, 1))

        active = _world(line=_line(), extra_lines=(_adjacency_line(1, 1, 2),))
        active.sectors[1].specialdata = object()
        self.assertEqual(stage.ev_do_floor_stage24_source_shape(active, active.lines[0], stage.LOWER_FLOOR_TO_LOWEST), 0)
        self.assertEqual((active.counters.floor_already_active_skips, active.counters.floor_tagged_sector_spawns), (1, 0))

        missing = _world(line=_line(tag=99), extra_lines=(_adjacency_line(1, 1, 2),))
        self.assertEqual(stage.ev_do_floor_stage24_source_shape(missing, missing.lines[0], stage.LOWER_FLOOR_TO_LOWEST), 0)
        self.assertEqual((missing.counters.floor_no_matching_tag_results, missing.counters.floor_tagged_sector_spawns), (1, 0))

    def test_synthetic_t_move_plane_floor_down_clamps_removes_and_stops_sound(self) -> None:
        world = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        stage.ev_do_floor_stage24_source_shape(world, world.lines[0], stage.LOWER_FLOOR_TO_LOWEST)
        assert world.selected_floor is not None

        for _ in range(64):
            stage.p_ticker_stage24_source_shape(world)
        self.assertEqual(world.sectors[1].floorheight >> stage.FRACBITS, -48)
        self.assertEqual((world.counters.floor_pastdest_events, world.counters.floor_removal_requests), (0, 0))

        stage.p_ticker_stage24_source_shape(world)
        self.assertEqual(world.floor_trace[-1].result, stage.RESULT_PASTDEST)
        self.assertEqual((world.floor_trace[-1].floor_before >> stage.FRACBITS, world.floor_trace[-1].floor_after >> stage.FRACBITS), (-48, -48))
        self.assertEqual((world.selected_floor.removal_requested, world.counters.floor_stop_sound_deferrals), (1, 1))
        self.assertEqual((world.counters.floor_ticks, world.counters.floor_mutations), (65, 64))

        stage.p_ticker_stage24_source_shape(world)
        self.assertEqual(world.ticker_world.counters.lazy_removals, 1)

    def test_synthetic_boundaries_for_nofit_unsupported_and_generalized_absence(self) -> None:
        nofit = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        nofit.ev = stage.ev_do_floor_stage24_source_shape(nofit, nofit.lines[0], stage.LOWER_FLOOR_TO_LOWEST)
        nofit.ticker_world.force_change_sector_nofit = True
        stage.p_ticker_stage24_source_shape(nofit)
        self.assertEqual(nofit.sectors[1].floorheight >> stage.FRACBITS, 16)
        self.assertEqual((nofit.counters.floor_change_sector_nofit, nofit.counters.floor_crush_events), (2, 1))

        with self.assertRaises(NotImplementedError):
            stage.ev_do_floor_stage24_source_shape(_world(), _line(), 99)

        absent = stage.Stage24Counters()
        self.assertEqual((absent.unsupported_floor_type_absent, absent.generalized_floor_absent, absent.generalized_plat_absent, absent.generalized_ceiling_absent), (1, 1, 1, 1))

    def test_synthetic_use_special_line_case60_preserves_button_lifecycle(self) -> None:
        world = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        self.assertTrue(stage.p_use_special_line_stage24_source_shape(world, world.lines[0], 0))
        self.assertEqual((world.switch_result.before_name, world.switch_result.after_name), ("SW1BROWN", "SW2BROWN"))
        self.assertEqual((world.switch_result.line_special_after, world.buttonlist[0].btimer), (60, 35))
        for _ in range(stage.BUTTONTIME):
            stage.p_update_specials_stage24_source_shape(world)
        self.assertEqual((world.side_textures[0].midtexture, world.buttonlist[0].btimer), (1, 0))
        self.assertEqual((world.counters.button_restore_steps, world.counters.button_slot_clears), (1, 1))

    def test_pinned_map_stage24_reference_moves_map11_floor_and_preserves_baselines(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_first_floor_sector_special_probe_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.stage23.signature, 3216085132)
        self.assertEqual(ref.stage23.stage22.signature, 2207028069)
        self.assertEqual(ref.stage23.stage22.stage21.signature, 1770773845)
        self.assertEqual(ref.stage23.stage22.stage21.stage20.signature, 3226031347)
        self.assertEqual(ref.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)
        self.assertEqual((ref.census.map_name, ref.census.line_index, ref.census.special, ref.census.tag), ("MAP11", 391, 60, 6))
        self.assertEqual((ref.census.right_sidedef, ref.census.left_sidedef, ref.census.front_sector), (564, stage.NO_SIDEDEF, 59))
        self.assertEqual((ref.census.middle_texture_before, ref.census.middle_texture_pressed, ref.census.middle_texture_restored), ("SW1BROWN", "SW2BROWN", "SW1BROWN"))
        self.assertEqual((ref.switch.pair_index, ref.switch.switchlist_index, ref.switch.where), (4, 8, stage.BUTTON_MIDDLE))
        self.assertEqual((ref.switch.line_special_before, ref.switch.line_special_after), (60, 60))
        self.assertEqual((ref.floor_spawn.matched_sectors, ref.floor_spawn.spawned_sectors), ((57,), (57,)))
        self.assertEqual((ref.census.target_floor_before >> stage.FRACBITS, ref.census.target_floor_after >> stage.FRACBITS), (16, -48))
        self.assertEqual((ref.census.target_ceiling >> stage.FRACBITS, ref.census.target_special), (144, 0))
        self.assertEqual((ref.census.surrounding_lowest_floor >> stage.FRACBITS, ref.floor_spawn.floordestheight >> stage.FRACBITS), (-48, -48))
        self.assertEqual((ref.floor_spawn.direction, ref.floor_spawn.speed >> stage.FRACBITS), (-1, 1))
        self.assertEqual((ref.button_slot, ref.button_timer_start, ref.button_timer_end, ref.duplicate_guard_result), (0, 35, 0, -1))
        self.assertEqual((ref.counters.button_countdowns, ref.counters.button_restore_steps, ref.counters.button_slot_clears), (35, 1, 1))
        self.assertEqual((ref.ticker_counters.ticker_calls, ref.leveltime_after, ref.order_ok), (66, 66, 1))
        self.assertEqual((ref.counters.floor_ticks, ref.counters.floor_move_plane_calls, ref.counters.floor_mutations), (65, 65, 64))
        self.assertEqual((ref.counters.floor_pastdest_events, ref.counters.floor_removal_requests, ref.ticker_counters.lazy_removals), (1, 1, 1))
        self.assertEqual((ref.counters.floor_move_sound_deferrals, ref.counters.floor_stop_sound_deferrals), (9, 1))
        self.assertEqual((ref.counters.real_audio_playbacks, ref.counters.generalized_floor_absent, ref.counters.generalized_plat_absent, ref.counters.generalized_ceiling_absent), (0, 1, 1, 1))
        self.assertEqual(ref.signature, 1919312263)

    def test_executable_build_contains_stage24_status_preserves_stage23_and_omits_forbidden_strings(self) -> None:
        image = stage.build_source_stage24_first_floor_sector_special_probe_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage24_first_floor_sector_special_probe", image)
        self.assertIn(b"First floor sector special proof OK", image)
        self.assertIn(b"EV_DoFloor", image)
        self.assertIn(b"T_MoveFloor", image)
        self.assertIn(b"T_MovePlane", image)
        self.assertIn(b"SW1BROWN", image)
        self.assertIn(b"SW2BROWN", image)
        for marker in (b" S19SIG=", b" S20SIG=", b" S21SIG=", b" S22SIG=", b" S23SIG=", b" S24SIG="):
            self.assertIn(marker, image)
        self.assertNotIn(b"source_stage25", lower)
        for forbidden in (
            b"generalized platforms",
            b"generalized ceilings",
            b"live keyboard input",
            b"save/load",
            b"networking",
            b"real audio playback",
            b"mixer/device playback",
            b"gcc:",
            b"mingw",
            b"microsoft visual c",
        ):
            self.assertNotIn(forbidden, lower)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage24_floor_and_preserved_stage23_stage22_stage21_stage20_stage19(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_first_floor_sector_special_probe_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage24_first_floor_sector_special_probe.exe"
        stage.write_source_stage24_first_floor_sector_special_probe_exe(exe_path)

        expected = (
            f"S19SIG={ref.stage23.stage22.stage21.stage20.stage19.signature}",
            f"S20SIG={ref.stage23.stage22.stage21.stage20.signature}",
            f"S21SIG={ref.stage23.stage22.stage21.signature}",
            f"S22SIG={ref.stage23.stage22.signature}",
            f"S23SIG={ref.stage23.signature}",
            f"S24SIG={ref.signature}",
            "S24LINE=391",
            "TEX240=SW1BROWN",
            "TEX241=SW2BROWN",
            "TEX242=SW1BROWN",
            "F241=-48",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn("S23LINE=3452", title)
            self.assertIn("S22LINE=839", title)
            self.assertIn("S21SEC=56", title)
            self.assertIn("S20ID=88", title)
            self.assertIn("S19LINE=332", title)
            self.assertIn("TSEC24=57", title)
            self.assertIn("F240=16", title)
            self.assertIn("LOWF24=-48", title)
            self.assertIn("SPD24=1", title)
            self.assertIn("TMF24=65", title)
            self.assertIn("REM24=1", title)
            self.assertIn("LREM24=1", title)
            self.assertIn("STOP24=1", title)
            self.assertIn("AUD24=0", title)
            self.assertIn("S25ABS=1", title)
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
