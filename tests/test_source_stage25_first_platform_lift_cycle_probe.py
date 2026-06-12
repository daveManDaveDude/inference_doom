import os
import subprocess
import time
import unittest
from pathlib import Path

from tools.map_loader import LoadedMap, Sector
from tools import emit_source_stage14_game_loop_input_collision as stage14
from tools import emit_source_stage25_first_platform_lift_cycle_probe as stage


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
    special: int = 62,
    tag: int = 26,
    front: int = 0,
    back: int | None = None,
    right: int = 0,
    left: int = stage.NO_SIDEDEF,
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
        flags=stage.stage19.ML_TWOSIDED if back is not None else 0,
        special=special,
        tag=tag,
        sidenum=(right, left),
        side_sectors=(front, back),
        side_upper=("-", ""),
        side_lower=("SW1STRTN", ""),
        side_middle=("-", ""),
    )


def _adjacency_line(index: int, sector: int, other: int) -> stage.stage19.Stage19Line:
    return _line(index, special=0, tag=0, front=sector, back=other, right=index, left=index + 100)


def _world(
    *,
    line: stage.stage19.Stage19Line | None = None,
    sectors: tuple[stage.stage19.Stage19Sector, ...] | None = None,
    side: stage.stage22.Stage22SideDefTextures | None = None,
    extra_lines: tuple[stage.stage19.Stage19Line, ...] = (),
) -> stage.Stage25World:
    if line is None:
        line = _line()
    if sectors is None:
        sectors = (
            stage.stage19.Stage19Sector(0, 0, 256 * stage.FRACUNIT),
            stage.stage19.Stage19Sector(1, -8 * stage.FRACUNIT, 256 * stage.FRACUNIT, tag=26),
            stage.stage19.Stage19Sector(2, -64 * stage.FRACUNIT, 256 * stage.FRACUNIT),
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
    pair = stage.stage22.Stage22SwitchPair(18, 18, "SW1STRTN", "SW2STRTN", 1, 2)
    switchlist, names = stage.stage22._flatten_switchlist((pair,))
    return stage.Stage25World(
        base=base,
        side_textures=[side or stage.stage22.Stage22SideDefTextures(0, 1, 0)],
        switch_pairs=(pair,),
        switchlist=switchlist,
        switchlist_names=names,
        texture_name_by_id={0: "-", 1: "SW1STRTN", 2: "SW2STRTN", 99: "OTHER"},
        counters=stage.Stage25Counters(switchlist_init_calls=1, switch_pairs_available=1, switchlist_entries=2),
    )


class SourceStage25FirstPlatformLiftCycleTests(unittest.TestCase):
    def test_source_trace_labels_name_platform_route(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("P_UseSpecialLine_button62_downWaitUpStay_source_shape_debug", labels)
        self.assertIn("EV_DoPlat_downWaitUpStay_stage25_source_shape_debug", labels)
        self.assertIn("T_PlatRaise_downWaitUpStay_stage25_source_shape_debug", labels)
        self.assertIn("T_MovePlane_plat_floor_stage25_source_shape_debug", labels)
        self.assertIn("P_ActivePlat_stage25_source_shape_debug", labels)

    def test_synthetic_ev_do_plat_setup_tag_active_no_match_and_slot_allocation(self) -> None:
        world = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        self.assertEqual(stage.ev_do_plat_stage25_source_shape(world, world.lines[0], stage.DOWN_WAIT_UP_STAY, 1), 1)

        plat = world.selected_plat
        self.assertIsNotNone(plat)
        assert plat is not None
        self.assertEqual((world.plat_spawn.matched_sectors, world.plat_spawn.spawned_sectors), ((1,), (1,)))
        self.assertEqual((plat.sector_index, plat.low >> stage.FRACBITS, plat.high >> stage.FRACBITS), (1, -64, -8))
        self.assertEqual((plat.speed >> stage.FRACBITS, plat.wait, plat.status, plat.tag), (4, 105, stage.PLAT_DOWN, 26))
        self.assertEqual((world.activeplats[0], plat.active_slot), (plat, 0))
        self.assertEqual((world.counters.plat_thinker_records, world.ticker_world.counters.thinker_nodes), (1, 1))

        active = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        active.sectors[1].specialdata = object()
        self.assertEqual(stage.ev_do_plat_stage25_source_shape(active, active.lines[0], stage.DOWN_WAIT_UP_STAY, 1), 0)
        self.assertEqual((active.counters.plat_already_active_skips, active.counters.plat_tagged_sector_spawns), (1, 0))

        missing = _world(line=_line(tag=99), extra_lines=(_adjacency_line(1, 1, 2),))
        self.assertEqual(stage.ev_do_plat_stage25_source_shape(missing, missing.lines[0], stage.DOWN_WAIT_UP_STAY, 1), 0)
        self.assertEqual((missing.counters.plat_no_matching_tag_results, missing.counters.plat_tagged_sector_spawns), (1, 0))

    def test_synthetic_activeplats_boundaries_and_lazy_removal(self) -> None:
        world = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        stage.ev_do_plat_stage25_source_shape(world, world.lines[0], stage.DOWN_WAIT_UP_STAY, 1)
        assert world.selected_plat is not None
        assert world.selected_plat_node is not None

        removed_slot = stage.p_remove_active_plat_stage25_source_shape(world, world.selected_plat, world.selected_plat_node)
        self.assertEqual(removed_slot, 0)
        self.assertIsNone(world.activeplats[0])
        self.assertIsNone(world.sectors[1].specialdata)
        self.assertEqual((world.counters.activeplat_slot_clears, world.ticker_world.counters.lazy_removal_markers), (1, 1))
        stage.stage21.p_run_thinkers_stage21_source_shape(world.ticker_world)
        self.assertEqual(world.ticker_world.counters.lazy_removals, 1)

        full = _world()
        for i in range(stage.MAXPLATS):
            full.activeplats[i] = stage.Stage25PlatThinker(1, stage.DOWN_WAIT_UP_STAY, 4, -64, -8, 105, 0, stage.PLAT_DOWN, stage.PLAT_DOWN, False, 26)
        extra = stage.Stage25PlatThinker(1, stage.DOWN_WAIT_UP_STAY, 4, -64, -8, 105, 0, stage.PLAT_DOWN, stage.PLAT_DOWN, False, 26)
        self.assertEqual(stage.p_add_active_plat_stage25_source_shape(full, extra), -2)
        self.assertEqual(full.counters.activeplat_full_errors, 1)
        self.assertEqual(stage.p_remove_active_plat_stage25_source_shape(full, extra), -1)
        self.assertEqual(full.counters.activeplat_missing_errors, 1)

    def test_synthetic_t_plat_raise_full_down_wait_up_stay_cycle(self) -> None:
        world = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        stage.ev_do_plat_stage25_source_shape(world, world.lines[0], stage.DOWN_WAIT_UP_STAY, 1)
        assert world.selected_plat is not None

        for _ in range(14):
            stage.p_ticker_stage25_source_shape(world)
        self.assertEqual((world.sectors[1].floorheight >> stage.FRACBITS, world.counters.plat_pastdest_events), (-64, 0))

        stage.p_ticker_stage25_source_shape(world)
        self.assertEqual((world.plat_trace[-1].result, world.selected_plat.status, world.selected_plat.count), (stage.RESULT_PASTDEST, stage.PLAT_WAITING, 105))
        self.assertEqual(world.counters.plat_stop_sound_deferrals, 1)

        for _ in range(105):
            stage.p_ticker_stage25_source_shape(world)
        self.assertEqual((world.selected_plat.status, world.counters.plat_wait_countdowns, world.counters.plat_up_restarts), (stage.PLAT_UP, 105, 1))
        self.assertEqual(world.counters.plat_start_sound_deferrals, 2)

        for _ in range(14):
            stage.p_ticker_stage25_source_shape(world)
        self.assertEqual(world.sectors[1].floorheight >> stage.FRACBITS, -8)
        self.assertEqual(world.counters.plat_removal_requests, 0)

        stage.p_ticker_stage25_source_shape(world)
        self.assertEqual((world.plat_trace[-1].result, world.plat_trace[-1].removed), (stage.RESULT_PASTDEST, 1))
        self.assertIsNone(world.activeplats[0])
        self.assertIsNone(world.sectors[1].specialdata)
        self.assertEqual((world.counters.plat_pastdest_events, world.counters.activeplat_slot_clears), (2, 1))

        stage.p_ticker_stage25_source_shape(world)
        self.assertEqual(world.ticker_world.counters.lazy_removals, 1)

    def test_synthetic_boundaries_for_unsupported_plats_and_button_lifecycle(self) -> None:
        with self.assertRaises(NotImplementedError):
            stage.ev_do_plat_stage25_source_shape(_world(), _line(), 99)

        absent = stage.Stage25Counters()
        self.assertEqual((absent.unsupported_plat_type_absent, absent.generalized_plat_absent, absent.generalized_floor_absent, absent.generalized_ceiling_absent), (1, 1, 1, 1))

        world = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        self.assertTrue(stage.p_use_special_line_stage25_source_shape(world, world.lines[0], 0))
        self.assertEqual((world.switch_result.before_name, world.switch_result.after_name, world.switch_result.where), ("SW1STRTN", "SW2STRTN", stage.BUTTON_BOTTOM))
        self.assertEqual((world.switch_result.line_special_after, world.buttonlist[0].btimer), (62, 35))
        for _ in range(stage.BUTTONTIME):
            stage.p_update_specials_stage25_source_shape(world)
        self.assertEqual((world.side_textures[0].bottomtexture, world.buttonlist[0].btimer), (1, 0))
        self.assertEqual((world.counters.button_restore_steps, world.counters.button_slot_clears), (1, 1))

    def test_pinned_map_stage25_reference_cycles_map12_lift_and_preserves_baselines(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_first_platform_lift_cycle_probe_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.stage24.signature, 1919312263)
        self.assertEqual(ref.stage24.stage23.signature, 3216085132)
        self.assertEqual(ref.stage24.stage23.stage22.signature, 2207028069)
        self.assertEqual(ref.stage24.stage23.stage22.stage21.signature, 1770773845)
        self.assertEqual(ref.stage24.stage23.stage22.stage21.stage20.signature, 3226031347)
        self.assertEqual(ref.stage24.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)
        self.assertEqual((ref.census.map_name, ref.census.line_index, ref.census.special, ref.census.tag), ("MAP12", 2304, 62, 26))
        self.assertEqual((ref.census.right_sidedef, ref.census.left_sidedef, ref.census.front_sector), (3005, 3004, 228))
        self.assertEqual((ref.census.lower_texture_before, ref.census.lower_texture_pressed, ref.census.lower_texture_restored), ("SW1STRTN", "SW2STRTN", "SW1STRTN"))
        self.assertEqual((ref.switch.pair_index, ref.switch.switchlist_index, ref.switch.where), (18, 36, stage.BUTTON_BOTTOM))
        self.assertEqual((ref.switch.line_special_before, ref.switch.line_special_after), (62, 62))
        self.assertEqual((ref.plat_spawn.matched_sectors, ref.plat_spawn.spawned_sectors), ((77,), (77,)))
        self.assertEqual((ref.census.target_floor_before >> stage.FRACBITS, ref.census.target_floor_after >> stage.FRACBITS), (-8, -8))
        self.assertEqual((ref.census.target_ceiling >> stage.FRACBITS, ref.census.target_special), (256, 0))
        self.assertEqual((ref.plat_spawn.low >> stage.FRACBITS, ref.plat_spawn.high >> stage.FRACBITS, ref.plat_spawn.speed >> stage.FRACBITS, ref.plat_spawn.wait, ref.plat_spawn.status), (-64, -8, 4, 105, stage.PLAT_DOWN))
        self.assertEqual((ref.button_slot, ref.button_timer_start, ref.button_timer_end, ref.duplicate_guard_result), (0, 35, 0, -1))
        self.assertEqual((ref.counters.button_countdowns, ref.counters.button_restore_steps, ref.counters.button_slot_clears), (35, 1, 1))
        self.assertEqual((ref.ticker_counters.ticker_calls, ref.leveltime_after, ref.order_ok), (136, 136, 1))
        self.assertEqual((ref.counters.plat_ticks, ref.counters.plat_move_plane_calls, ref.counters.plat_mutations), (135, 30, 28))
        self.assertEqual((ref.counters.plat_pastdest_events, ref.counters.plat_wait_transitions, ref.counters.plat_wait_countdowns, ref.counters.plat_up_restarts), (2, 2, 105, 1))
        self.assertEqual((ref.counters.plat_removal_requests, ref.counters.activeplat_slot_clears, ref.ticker_counters.lazy_removals), (1, 1, 1))
        self.assertEqual((ref.counters.plat_start_sound_deferrals, ref.counters.plat_stop_sound_deferrals, ref.counters.real_audio_playbacks), (2, 2, 0))
        self.assertEqual(ref.signature, 1688844032)

    def test_executable_build_contains_stage25_status_preserves_stage24_and_omits_forbidden_strings(self) -> None:
        image = stage.build_source_stage25_first_platform_lift_cycle_probe_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage25_first_platform_lift_cycle_probe", image)
        self.assertIn(b"First platform lift cycle proof OK", image)
        self.assertIn(b"EV_DoPlat", image)
        self.assertIn(b"T_PlatRaise", image)
        self.assertIn(b"P_AddActivePlat", image)
        self.assertIn(b"SW1STRTN", image)
        self.assertIn(b"SW2STRTN", image)
        for marker in (b" S19SIG=", b" S20SIG=", b" S21SIG=", b" S22SIG=", b" S23SIG=", b" S24SIG=", b" S25SIG="):
            self.assertIn(marker, image)
        self.assertNotIn(b"source_stage26", lower)
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
    def test_smoke_launch_reports_stage25_platform_and_preserved_stage24_stage23_stage22_stage21_stage20_stage19(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_first_platform_lift_cycle_probe_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage25_first_platform_lift_cycle_probe.exe"
        stage.write_source_stage25_first_platform_lift_cycle_probe_exe(exe_path)

        expected = (
            f"S19SIG={ref.stage24.stage23.stage22.stage21.stage20.stage19.signature}",
            f"S20SIG={ref.stage24.stage23.stage22.stage21.stage20.signature}",
            f"S21SIG={ref.stage24.stage23.stage22.stage21.signature}",
            f"S22SIG={ref.stage24.stage23.stage22.signature}",
            f"S23SIG={ref.stage24.stage23.signature}",
            f"S24SIG={ref.stage24.signature}",
            f"S25SIG={ref.signature}",
            "S25LINE=2304",
            "TEX250=SW1STRTN",
            "TEX251=SW2STRTN",
            "TEX252=SW1STRTN",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn("S24LINE=391", title)
            self.assertIn("S23LINE=3452", title)
            self.assertIn("S22LINE=839", title)
            self.assertIn("S21SEC=56", title)
            self.assertIn("S20ID=88", title)
            self.assertIn("S19LINE=332", title)
            self.assertIn("TSEC25=77", title)
            self.assertIn("F250=-8", title)
            self.assertIn("F251=-8", title)
            self.assertIn("LOW25=-64", title)
            self.assertIn("HIGH25=-8", title)
            self.assertIn("SPD25=4", title)
            self.assertIn("WAIT25=105", title)
            self.assertIn("ASLOT25=0", title)
            self.assertIn("TPL25=135", title)
            self.assertIn("MP25=30", title)
            self.assertIn("WDEC25=105", title)
            self.assertIn("AREM25=1", title)
            self.assertIn("ACLR25=1", title)
            self.assertIn("LREM25=1", title)
            self.assertIn("PSTART25=2", title)
            self.assertIn("PSTOP25=2", title)
            self.assertIn("AUD25=0", title)
            self.assertIn("S26ABS=1", title)
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
