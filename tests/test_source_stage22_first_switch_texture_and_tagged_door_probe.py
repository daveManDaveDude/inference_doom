import os
import subprocess
import time
import unittest
from pathlib import Path

from tools.map_loader import LoadedMap, Sector
from tools import emit_source_stage14_game_loop_input_collision as stage14
from tools import emit_source_stage22_first_switch_texture_and_tagged_door_probe as stage


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
    *,
    special: int = 103,
    tag: int = 4,
    front: int = 0,
    back: int | None = 1,
    right: int | None = None,
    left: int | None = None,
) -> stage.stage19.Stage19Line:
    right_index = index * 2 if right is None else right
    left_index = stage.NO_SIDEDEF if back is None else (index * 2 + 1 if left is None else left)
    x1, y1, x2, y2 = 32, 32, 32, -32
    v1x = x1 << stage.FRACBITS
    v1y = y1 << stage.FRACBITS
    v2x = x2 << stage.FRACBITS
    v2y = y2 << stage.FRACBITS
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
        flags=stage.ML_TWOSIDED if back is not None else 0,
        special=special,
        tag=tag,
        sidenum=(right_index, left_index),
        side_sectors=(front, back),
        side_upper=("-", "-"),
        side_lower=("-", "-"),
        side_middle=("-", "-"),
    )


def _adjacency_line(index: int, sector: int, other: int = 0) -> stage.stage19.Stage19Line:
    return _line(index, special=0, tag=0, front=sector, back=other)


def _base_world(
    *,
    lines: tuple[stage.stage19.Stage19Line, ...],
    sectors: tuple[stage.stage19.Stage19Sector, ...],
) -> stage.stage19.Stage19World:
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
    return stage.stage19.Stage19World(
        loaded=loaded,
        blockmap=blockmap,
        sectors=[sector for sector in sectors],
        lines=[line for line in lines],
        sector_lines=stage.stage19.build_stage19_sector_lines(lines, len(sectors)),
        counters=stage.stage19.Stage19Counters(),
    )


def _synthetic_world(
    *,
    line: stage.stage19.Stage19Line | None = None,
    sectors: tuple[stage.stage19.Stage19Sector, ...] | None = None,
    side_textures: tuple[stage.Stage22SideDefTextures, ...] | None = None,
    extra_lines: tuple[stage.stage19.Stage19Line, ...] = (),
) -> stage.Stage22World:
    if line is None:
        line = _line(0)
    if sectors is None:
        sectors = (
            stage.stage19.Stage19Sector(0, 0, 0),
            stage.stage19.Stage19Sector(1, -80 * stage.FRACUNIT, -80 * stage.FRACUNIT, tag=4),
        )
    if side_textures is None:
        side_textures = (
            stage.Stage22SideDefTextures(toptexture=0, bottomtexture=2, midtexture=0),
            stage.Stage22SideDefTextures(toptexture=0, bottomtexture=0, midtexture=0),
        )
    pair = stage.Stage22SwitchPair(0, 0, "SW1COMP", "SW2COMP", 1, 2)
    switchlist, names = stage._flatten_switchlist((pair,))
    return stage.Stage22World(
        base=_base_world(lines=(line,) + extra_lines, sectors=sectors),
        side_textures=[stage.Stage22SideDefTextures(s.toptexture, s.bottomtexture, s.midtexture) for s in side_textures],
        switch_pairs=(pair,),
        switchlist=switchlist,
        switchlist_names=names,
        texture_name_by_id={0: "-", 1: "SW1COMP", 2: "SW2COMP", 99: "OTHER"},
        counters=stage.Stage22Counters(switchlist_init_calls=1, switch_pairs_available=1, switchlist_entries=2),
    )


class SourceStage22FirstSwitchTextureTaggedDoorTests(unittest.TestCase):
    def test_source_trace_labels_name_switch_tagged_door_and_ticker_route(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("P_UseSpecialLine_switch103_tagged_door_source_shape_debug", labels)
        self.assertIn("P_ChangeSwitchTexture_first_switch_mutation_source_shape_debug", labels)
        self.assertIn("EV_DoDoor_tagged_vld_open_source_shape_debug", labels)
        self.assertIn("P_FindSectorFromLineTag_stage22_source_shape_debug", labels)
        self.assertIn("P_Ticker_tagged_door_stage22_source_shape_debug", labels)

    def test_synthetic_switchlist_doom2_pair_availability_and_slot_matching(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        wad = stage.WadFile.from_file(PINNED_WAD)
        setup = stage.stage08.load_texture_setup_from_wad(wad)
        counters = stage.Stage22Counters()
        pairs = stage.p_init_switch_list_stage22_source_shape(setup, counters, episode=3)
        pair_names = {(pair.name1, pair.name2) for pair in pairs}

        self.assertIn(("SW1COMP", "SW2COMP"), pair_names)
        self.assertIn(("SW1PANEL", "SW2PANEL"), pair_names)
        self.assertEqual((counters.switch_pairs_available, counters.switchlist_entries), (40, 80))

        for where in (stage.BUTTON_TOP, stage.BUTTON_MIDDLE, stage.BUTTON_BOTTOM):
            side = stage.Stage22SideDefTextures(0, 0, 0)
            stage._set_switch_slot_value(side, where, 2)
            world = _synthetic_world(side_textures=(side, stage.Stage22SideDefTextures(0, 0, 0)))
            result = stage.p_change_switch_texture_stage22_source_shape(world, world.lines[0], 0)
            self.assertEqual((result.matched, result.where, result.before_name, result.after_name), (1, where, "SW2COMP", "SW1COMP"))
            self.assertEqual(stage._switch_slot_value(world.side_textures[0], where), 1)

    def test_synthetic_switch_no_match_one_shot_clear_and_button_guard(self) -> None:
        no_match_side = stage.Stage22SideDefTextures(toptexture=99, bottomtexture=99, midtexture=99)
        world = _synthetic_world(side_textures=(no_match_side, stage.Stage22SideDefTextures(0, 0, 0)))
        result = stage.p_change_switch_texture_stage22_source_shape(world, world.lines[0], 0)
        self.assertEqual((result.matched, world.lines[0].special), (0, 0))
        self.assertEqual((world.counters.no_switch_match_noops, world.counters.line_special_clears), (1, 1))
        self.assertEqual(world.side_textures[0].bottomtexture, 99)

        button_world = _synthetic_world()
        first = stage.p_start_button_stage22_source_shape(button_world, button_world.lines[0], stage.BUTTON_BOTTOM, 2)
        second = stage.p_start_button_stage22_source_shape(button_world, button_world.lines[0], stage.BUTTON_BOTTOM, 2)
        self.assertEqual((first, second), (0, -1))
        self.assertEqual((button_world.counters.button_slot_allocations, button_world.counters.button_duplicate_guards), (1, 1))

    def test_synthetic_change_switch_texture_mutates_and_counts_deferred_sound_boundary(self) -> None:
        world = _synthetic_world()
        result = stage.p_change_switch_texture_stage22_source_shape(world, world.lines[0], 0)

        self.assertEqual((result.before_name, result.after_name), ("SW2COMP", "SW1COMP"))
        self.assertEqual((result.sound_id, world.counters.switch_sound_start_deferrals), (stage.SFX_SWTCHN, 1))
        self.assertEqual((world.counters.switch_channel_guard_deferrals, world.counters.real_audio_playbacks), (1, 0))
        self.assertEqual((world.counters.button_start_calls, world.counters.button_restore_steps), (0, 0))

    def test_synthetic_tagged_door_one_none_active_and_multiple_sector_bounds(self) -> None:
        line = _line(0, tag=4)
        one = _synthetic_world(line=line, extra_lines=(_adjacency_line(1, 1),))
        self.assertEqual(stage.ev_do_door_stage22_source_shape(one, line, stage.VLD_OPEN), 1)
        self.assertEqual((one.door_spawn.selected_sector, one.counters.tagged_sector_spawns), (1, 1))
        self.assertEqual((one.selected_door.topheight >> stage.FRACBITS, one.selected_door.speed >> stage.FRACBITS), (-4, 2))

        missing_line = _line(0, tag=99)
        missing = _synthetic_world(line=missing_line, extra_lines=(_adjacency_line(1, 1),))
        self.assertEqual(stage.ev_do_door_stage22_source_shape(missing, missing_line, stage.VLD_OPEN), 0)
        self.assertEqual((missing.counters.no_matching_tag_results, missing.counters.tagged_sector_spawns), (1, 0))

        active_line = _line(0, tag=4)
        active = _synthetic_world(line=active_line, extra_lines=(_adjacency_line(1, 1),))
        active.sectors[1].specialdata = stage.stage21.Stage21DoorThinker(1, stage.VLD_OPEN, -4 * stage.FRACUNIT, 2 * stage.FRACUNIT, 1, 150)
        self.assertEqual(stage.ev_do_door_stage22_source_shape(active, active_line, stage.VLD_OPEN), 0)
        self.assertEqual((active.counters.already_active_sector_skips, active.counters.tagged_sector_spawns), (1, 0))

        multi_line = _line(0, tag=4)
        sectors = (
            stage.stage19.Stage19Sector(0, 0, 0),
            stage.stage19.Stage19Sector(1, -80 * stage.FRACUNIT, -80 * stage.FRACUNIT, tag=4),
            stage.stage19.Stage19Sector(2, -64 * stage.FRACUNIT, -64 * stage.FRACUNIT, tag=4),
        )
        multi = _synthetic_world(
            line=multi_line,
            sectors=sectors,
            extra_lines=(_adjacency_line(1, 1), _adjacency_line(2, 2)),
        )
        self.assertEqual(stage.ev_do_door_stage22_source_shape(multi, multi_line, stage.VLD_OPEN), 1)
        self.assertEqual((multi.counters.tagged_sector_matches, multi.counters.tagged_sector_spawns), (2, 2))
        self.assertEqual(multi.ticker_world.counters.thinker_nodes, 2)

    def test_synthetic_newly_spawned_vld_open_ticker_advances_once_without_later_transitions(self) -> None:
        line = _line(0, tag=4)
        world = _synthetic_world(line=line, extra_lines=(_adjacency_line(1, 1),))
        stage.ev_do_door_stage22_source_shape(world, line, stage.VLD_OPEN)
        assert world.ticker_world is not None

        stage.stage21.p_ticker_stage21_source_shape(world.ticker_world)
        trace = world.ticker_world.door_trace[0]

        self.assertEqual((trace.ceiling_before >> stage.FRACBITS, trace.ceiling_after >> stage.FRACBITS), (-80, -78))
        self.assertEqual((world.selected_door.direction, world.selected_door.topcountdown), (1, 0))
        self.assertEqual((world.ticker_world.counters.door_removal_requests, world.ticker_world.counters.door_close_transitions), (0, 0))
        self.assertEqual(world.ticker_world.counters.wait_at_top_setups, 0)

    def test_pinned_map_stage22_reference_switches_line839_and_ticks_sector208_preserving_baselines(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_first_switch_texture_and_tagged_door_probe_for_pinned_map(PINNED_WAD)
        census = ref.census
        trace = ref.ticker_door_trace[0]

        self.assertEqual(ref.stage21.signature, 1770773845)
        self.assertEqual(ref.stage21.stage20.signature, 3226031347)
        self.assertEqual(ref.stage21.stage20.stage19.signature, 2088411722)
        self.assertEqual((census.line_index, census.special, census.tag, census.side), (839, 103, 4, 0))
        self.assertEqual((census.right_sidedef, census.left_sidedef), (1289, 1290))
        self.assertEqual((census.lower_texture_before, census.lower_texture_after), ("SW2COMP", "SW1COMP"))
        self.assertEqual((ref.switch.before_name, ref.switch.after_name, ref.switch.where), ("SW2COMP", "SW1COMP", stage.BUTTON_BOTTOM))
        self.assertEqual((ref.switch.pair_index, ref.switch.switchlist_index), (6, 13))
        self.assertEqual((ref.switch.line_special_before, ref.switch.line_special_after), (103, 0))
        self.assertEqual((ref.door_spawn.matched_sectors, ref.door_spawn.spawned_sectors), ((208,), (208,)))
        self.assertEqual((census.target_floor >> stage.FRACBITS, census.target_ceiling >> stage.FRACBITS, census.target_special), (-80, -80, 0))
        self.assertEqual((census.surrounding_lowest_ceiling >> stage.FRACBITS, census.topheight >> stage.FRACBITS), (0, -4))
        self.assertEqual((ref.door_spawn.direction, ref.door_spawn.speed >> stage.FRACBITS, ref.door_spawn.topwait), (1, 2, 150))
        self.assertEqual((trace.ceiling_before >> stage.FRACBITS, trace.ceiling_after >> stage.FRACBITS), (-80, -78))
        self.assertEqual((ref.counters.path_traverses, ref.counters.line_intercepts, ref.counters.traversed_intercepts), (1, 7, 2))
        self.assertEqual((ref.counters.find_sector_calls, ref.counters.tag_scan_steps, ref.counters.tagged_sector_matches), (2, 211, 1))
        self.assertEqual((ref.ticker_counters.ticker_calls, ref.ticker_counters.t_vertical_door_ticks, ref.ticker_counters.move_plane_calls), (1, 1, 1))
        self.assertEqual((ref.ticker_counters.door_removal_requests, ref.ticker_counters.door_close_transitions), (0, 0))
        self.assertEqual((ref.counters.button_start_calls, ref.counters.button_restore_steps), (0, 0))
        self.assertEqual((ref.counters.generalized_specials, ref.counters.real_audio_playbacks, ref.counters.live_input_events), (0, 0, 0))
        self.assertEqual(ref.signature, 2207028069)

    def test_executable_build_contains_stage22_status_preserves_stage21_and_omits_later_system_strings(self) -> None:
        image = stage.build_source_stage22_first_switch_texture_and_tagged_door_probe_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage22_first_switch_texture_and_tagged_door_probe", image)
        self.assertIn(b"First switch texture and tagged-door proof OK", image)
        self.assertIn(b"P_ChangeSwitchTexture", image)
        self.assertIn(b"EV_DoDoor", image)
        self.assertIn(b"P_FindSectorFromLineTag", image)
        self.assertIn(b"SW2COMP", image)
        self.assertIn(b"SW1COMP", image)
        self.assertIn(b" S19SIG=", image)
        self.assertIn(b" S20SIG=", image)
        self.assertIn(b" S21SIG=", image)
        self.assertIn(b" S22SIG=", image)
        self.assertNotIn(b"source_stage23", lower)
        for forbidden in (
            b"generalized specials",
            b"generalized doors",
            b"generalized switches",
            b"button restoration",
            b"live keyboard input",
            b"menus",
            b"automap",
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
    def test_smoke_launch_reports_stage22_switch_tagged_door_and_preserved_stage21_stage20_stage19(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_first_switch_texture_and_tagged_door_probe_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage22_first_switch_texture_and_tagged_door_probe.exe"
        stage.write_source_stage22_first_switch_texture_and_tagged_door_probe_exe(exe_path)

        expected = (
            f"S19SIG={ref.stage21.stage20.stage19.signature}",
            f"S20SIG={ref.stage21.stage20.signature}",
            f"S21SIG={ref.stage21.signature}",
            f"S22SIG={ref.signature}",
            "S22LINE=839",
            "TEX220=SW2COMP",
            "TEX221=SW1COMP",
            "TSEC22=208",
            "C221=-78",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn("S21SEC=56", title)
            self.assertIn("S20ID=88", title)
            self.assertIn("S19LINE=332", title)
            self.assertIn("SPC221=0", title)
            self.assertIn("TFIND22=1", title)
            self.assertIn("TITER22=211", title)
            self.assertIn("PTIC22=1", title)
            self.assertIn("TVD22=1", title)
            self.assertIn("MP22=1", title)
            self.assertIn("BTN22=0", title)
            self.assertIn("AUD22=0", title)
            self.assertIn("GEN22=0", title)
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
