import os
import subprocess
import time
import unittest
from pathlib import Path

from tools.map_loader import LoadedMap, Sector
from tools import emit_source_stage14_game_loop_input_collision as stage14
from tools import emit_source_stage26_first_ceiling_or_crusher_special_probe as stage


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace('\\', '/')


def window_title_for_pid(pid: int, expected: tuple[str, ...] = (), timeout_seconds: float = 5.0) -> tuple[int, str]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL('user32', use_last_error=True)
    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    deadline = time.monotonic() + timeout_seconds
    last_seen = ''
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
    raise TimeoutError(f'no matching visible window title found for pid {pid}: {last_seen!r}')


def _line(index: int = 0, *, special: int = 49, tag: int = 40, front: int = 0, right: int = 0) -> stage.stage19.Stage19Line:
    v1x = 32 << stage.FRACBITS
    v1y = 32 << stage.FRACBITS
    v2x = 32 << stage.FRACBITS
    v2y = -32 << stage.FRACBITS
    dx = v2x - v1x
    dy = v2y - v1y
    return stage.stage19.Stage19Line(
        index=index, v1x=v1x, v1y=v1y, v2x=v2x, v2y=v2y, dx=dx, dy=dy,
        bbox=(max(v1y, v2y), min(v1y, v2y), min(v1x, v2x), max(v1x, v2x)),
        slopetype=stage14._slopetype(dx, dy), flags=0, special=special, tag=tag,
        sidenum=(right, stage.NO_SIDEDEF), side_sectors=(front, None),
        side_upper=('-', ''), side_lower=('-', ''), side_middle=('SW1GSTON', ''),
    )


def _adjacency_line(index: int, sector: int, other: int) -> stage.stage19.Stage19Line:
    line = _line(index, special=0, tag=0, front=sector, right=index)
    return stage.stage19.Stage19Line(**{**line.__dict__, 'flags': stage.stage19.ML_TWOSIDED, 'sidenum': (index, index + 100), 'side_sectors': (sector, other)})


def _world(*, line: stage.stage19.Stage19Line | None = None, sectors: tuple[stage.stage19.Stage19Sector, ...] | None = None, extra_lines: tuple[stage.stage19.Stage19Line, ...] = ()) -> stage.Stage26World:
    if line is None:
        line = _line()
    if sectors is None:
        sectors = (
            stage.stage19.Stage19Sector(0, 0, 304 * stage.FRACUNIT),
            stage.stage19.Stage19Sector(1, 192 * stage.FRACUNIT, 304 * stage.FRACUNIT, tag=40),
            stage.stage19.Stage19Sector(2, 128 * stage.FRACUNIT, 384 * stage.FRACUNIT),
        )
    loaded = LoadedMap(
        name='SYN', source='synthetic', vertices=(), linedefs=(), sidedefs=(),
        sectors=tuple(Sector(s.floorheight >> stage.FRACBITS, s.ceilingheight >> stage.FRACBITS, 'F', 'C', 160, s.special, s.tag) for s in sectors),
        things=(),
    )
    lines = (line,) + extra_lines
    blockmap = stage14.BlockMap(-128 * stage.FRACUNIT, -128 * stage.FRACUNIT, 4, 4, (), (0,) * 16, tuple(tuple(l.index for l in lines) for _ in range(16)))
    base = stage.stage19.Stage19World(loaded=loaded, blockmap=blockmap, sectors=[s for s in sectors], lines=[l for l in lines], sector_lines=stage.stage19.build_stage19_sector_lines(lines, len(sectors)), counters=stage.stage19.Stage19Counters())
    pair = stage.stage22.Stage22SwitchPair(22, 22, 'SW1GSTON', 'SW2GSTON', 1, 2)
    switchlist, names = stage.stage22._flatten_switchlist((pair,))
    return stage.Stage26World(
        base=base,
        side_textures=[stage.stage22.Stage22SideDefTextures(0, 0, 1)],
        switch_pairs=(pair,), switchlist=switchlist, switchlist_names=names,
        texture_name_by_id={0: '-', 1: 'SW1GSTON', 2: 'SW2GSTON', 99: 'OTHER'},
        counters=stage.Stage26Counters(switchlist_init_calls=1, switch_pairs_available=1, switchlist_entries=2),
    )


class SourceStage26FirstCeilingOrCrusherSpecialTests(unittest.TestCase):
    def test_source_trace_labels_name_ceiling_route(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}
        self.assertIn('P_UseSpecialLine_switch49_crushAndRaise_stage26_source_shape_debug', labels)
        self.assertIn('EV_DoCeiling_crushAndRaise_stage26_source_shape_debug', labels)
        self.assertIn('T_MoveCeiling_crushAndRaise_stage26_source_shape_debug', labels)
        self.assertIn('T_MovePlane_ceiling_stage26_source_shape_debug', labels)
        self.assertIn('P_ActiveCeiling_stage26_source_shape_debug', labels)

    def test_synthetic_ev_do_ceiling_setup_tag_active_no_match_and_slot_allocation(self) -> None:
        world = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        self.assertEqual(stage.ev_do_ceiling_stage26_source_shape(world, world.lines[0], stage.CRUSH_AND_RAISE), 1)
        ceiling = world.selected_ceiling
        self.assertIsNotNone(ceiling)
        assert ceiling is not None
        self.assertEqual((world.ceiling_spawn.matched_sectors, world.ceiling_spawn.spawned_sectors), ((1,), (1,)))
        self.assertEqual((ceiling.sector_index, ceiling.bottomheight >> stage.FRACBITS, ceiling.topheight >> stage.FRACBITS), (1, 200, 304))
        self.assertEqual((ceiling.speed >> stage.FRACBITS, ceiling.crush, ceiling.direction, ceiling.tag), (1, True, -1, 40))
        self.assertEqual((world.activeceilings[0], ceiling.active_slot, world.ticker_world.counters.thinker_nodes), (ceiling, 0, 1))

        active = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        active.sectors[1].specialdata = object()
        self.assertEqual(stage.ev_do_ceiling_stage26_source_shape(active, active.lines[0], stage.CRUSH_AND_RAISE), 0)
        self.assertEqual((active.counters.ceiling_already_active_skips, active.counters.ceiling_tagged_sector_spawns), (1, 0))

        missing = _world(line=_line(tag=99), extra_lines=(_adjacency_line(1, 1, 2),))
        self.assertEqual(stage.ev_do_ceiling_stage26_source_shape(missing, missing.lines[0], stage.CRUSH_AND_RAISE), 0)
        self.assertEqual((missing.counters.ceiling_no_matching_tag_results, missing.counters.ceiling_tagged_sector_spawns), (1, 0))

    def test_synthetic_activeceilings_boundaries_and_lazy_removal(self) -> None:
        world = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        stage.ev_do_ceiling_stage26_source_shape(world, world.lines[0], stage.LOWER_TO_FLOOR)
        assert world.selected_ceiling is not None and world.selected_ceiling_node is not None
        removed_slot = stage.p_remove_active_ceiling_stage26_source_shape(world, world.selected_ceiling, world.selected_ceiling_node)
        self.assertEqual(removed_slot, 0)
        self.assertIsNone(world.activeceilings[0])
        self.assertIsNone(world.sectors[1].specialdata)
        self.assertEqual((world.counters.activeceiling_slot_clears, world.ticker_world.counters.lazy_removal_markers), (1, 1))
        stage.stage21.p_run_thinkers_stage21_source_shape(world.ticker_world)
        self.assertEqual(world.ticker_world.counters.lazy_removals, 1)

        full = _world()
        for i in range(stage.MAXCEILINGS):
            full.activeceilings[i] = stage.Stage26CeilingThinker(1, stage.CRUSH_AND_RAISE, stage.CEILSPEED, 200, 304, -1, -1, True, 40)
        extra = stage.Stage26CeilingThinker(1, stage.CRUSH_AND_RAISE, stage.CEILSPEED, 200, 304, -1, -1, True, 40)
        self.assertEqual(stage.p_add_active_ceiling_stage26_source_shape(full, extra), -2)
        self.assertEqual(full.counters.activeceiling_full_errors, 1)
        self.assertEqual(stage.p_remove_active_ceiling_stage26_source_shape(full, extra), -1)
        self.assertEqual(full.counters.activeceiling_missing_errors, 1)

    def test_synthetic_t_move_ceiling_full_crush_and_raise_cycle(self) -> None:
        world = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        stage.ev_do_ceiling_stage26_source_shape(world, world.lines[0], stage.CRUSH_AND_RAISE)
        assert world.selected_ceiling is not None
        for _ in range(104):
            stage.p_ticker_stage26_source_shape(world)
        self.assertEqual((world.sectors[1].ceilingheight >> stage.FRACBITS, world.counters.ceiling_pastdest_events), (200, 0))
        stage.p_ticker_stage26_source_shape(world)
        self.assertEqual((world.ceiling_trace[-1].result, world.selected_ceiling.direction), (stage.RESULT_PASTDEST, 1))
        for _ in range(104):
            stage.p_ticker_stage26_source_shape(world)
        self.assertEqual(world.sectors[1].ceilingheight >> stage.FRACBITS, 304)
        stage.p_ticker_stage26_source_shape(world)
        self.assertEqual((world.ceiling_trace[-1].result, world.selected_ceiling.direction), (stage.RESULT_PASTDEST, -1))
        self.assertIs(world.activeceilings[0], world.selected_ceiling)
        self.assertIs(world.sectors[1].specialdata, world.selected_ceiling)
        self.assertEqual((world.counters.ceiling_ticks, world.counters.ceiling_move_plane_calls, world.counters.ceiling_mutations), (210, 210, 208))
        self.assertEqual((world.counters.ceiling_bottom_reversals, world.counters.ceiling_top_reversals, world.counters.ceiling_move_sound_deferrals), (1, 1, 27))

    def test_synthetic_boundaries_for_unsupported_types_nofit_and_button_lifecycle_preservation(self) -> None:
        with self.assertRaises(NotImplementedError):
            stage.ev_do_ceiling_stage26_source_shape(_world(), _line(), 99)
        absent = stage.Stage26Counters()
        self.assertEqual((absent.unsupported_ceiling_type_absent, absent.generalized_floor_absent, absent.generalized_plat_absent, absent.generalized_ceiling_absent), (1, 1, 1, 1))

        nofit = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        stage.ev_do_ceiling_stage26_source_shape(nofit, nofit.lines[0], stage.CRUSH_AND_RAISE)
        nofit.ticker_world.force_change_sector_nofit = True
        stage.p_ticker_stage26_source_shape(nofit)
        self.assertEqual(nofit.sectors[1].ceilingheight >> stage.FRACBITS, 303)
        self.assertEqual((nofit.counters.ceiling_change_sector_nofit, nofit.counters.ceiling_crush_events), (1, 1))

        world = _world(extra_lines=(_adjacency_line(1, 1, 2),))
        self.assertTrue(stage.p_use_special_line_stage26_source_shape(world, world.lines[0], 0))
        self.assertEqual((world.switch_result.before_name, world.switch_result.after_name, world.switch_result.where), ('SW1GSTON', 'SW2GSTON', stage.BUTTON_MIDDLE))
        self.assertEqual((world.switch_result.line_special_after, world.counters.button_start_calls, world.buttonlist[0].btimer), (0, 0, 0))

    def test_pinned_map_stage26_reference_cycles_map29_crusher_and_preserves_baselines(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f'pinned WAD missing: {PINNED_WAD}')
        ref = stage.reference_first_ceiling_or_crusher_special_probe_for_pinned_map(PINNED_WAD)
        self.assertEqual(ref.stage25.signature, 1688844032)
        self.assertEqual(ref.stage25.stage24.signature, 1919312263)
        self.assertEqual(ref.stage25.stage24.stage23.signature, 3216085132)
        self.assertEqual(ref.stage25.stage24.stage23.stage22.signature, 2207028069)
        self.assertEqual(ref.stage25.stage24.stage23.stage22.stage21.signature, 1770773845)
        self.assertEqual(ref.stage25.stage24.stage23.stage22.stage21.stage20.signature, 3226031347)
        self.assertEqual(ref.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)
        self.assertEqual((ref.census.map_name, ref.census.line_index, ref.census.special, ref.census.tag), ('MAP29', 71, 49, 40))
        self.assertEqual((ref.census.right_sidedef, ref.census.left_sidedef, ref.census.front_sector), (125, stage.NO_SIDEDEF, 75))
        self.assertEqual((ref.census.middle_texture_before, ref.census.middle_texture_pressed, ref.census.middle_texture_restored), ('SW1GSTON', 'SW2GSTON', 'SW2GSTON'))
        self.assertEqual((ref.switch.pair_index, ref.switch.switchlist_index, ref.switch.where, ref.switch.line_special_after), (22, 44, stage.BUTTON_MIDDLE, 0))
        self.assertEqual((ref.ceiling_spawn.matched_sectors, ref.ceiling_spawn.spawned_sectors), ((117,), (117,)))
        self.assertEqual((ref.census.target_floor >> stage.FRACBITS, ref.census.target_ceiling_before >> stage.FRACBITS, ref.census.target_ceiling_after >> stage.FRACBITS), (192, 304, 304))
        self.assertEqual((ref.ceiling_spawn.bottomheight >> stage.FRACBITS, ref.ceiling_spawn.topheight >> stage.FRACBITS, ref.ceiling_spawn.speed >> stage.FRACBITS), (200, 304, 1))
        self.assertEqual((ref.ceiling_spawn.crush, ref.ceiling_spawn.direction, ref.ceiling_spawn.active_slot), (1, -1, 0))
        self.assertEqual((ref.ticker_counters.ticker_calls, ref.leveltime_after, ref.order_ok), (210, 210, 1))
        self.assertEqual((ref.counters.ceiling_ticks, ref.counters.ceiling_move_plane_calls, ref.counters.ceiling_mutations, ref.counters.ceiling_pastdest_events), (210, 210, 208, 2))
        self.assertEqual((ref.counters.ceiling_bottom_reversals, ref.counters.ceiling_top_reversals, ref.counters.ceiling_removal_requests, ref.counters.activeceiling_slot_clears), (1, 1, 0, 0))
        self.assertEqual((ref.counters.ceiling_move_sound_deferrals, ref.counters.ceiling_stop_sound_deferrals, ref.counters.real_audio_playbacks), (27, 0, 0))
        self.assertEqual(ref.signature, 132405987)

    def test_executable_build_contains_stage26_status_preserves_stage25_and_omits_forbidden_strings(self) -> None:
        image = stage.build_source_stage26_first_ceiling_or_crusher_special_probe_exe()
        lower = image.lower()
        self.assertEqual(image[:2], b'MZ')
        self.assertIn(b'source_stage26_first_ceiling_or_crusher_special_probe', image)
        self.assertIn(b'First ceiling crusher special proof OK', image)
        self.assertIn(b'EV_DoCeiling', image)
        self.assertIn(b'T_MoveCeiling', image)
        self.assertIn(b'P_AddActiveCeiling', image)
        self.assertIn(b'SW1GSTON', image)
        self.assertIn(b'SW2GSTON', image)
        for marker in (b' S19SIG=', b' S20SIG=', b' S21SIG=', b' S22SIG=', b' S23SIG=', b' S24SIG=', b' S25SIG=', b' S26SIG='):
            self.assertIn(marker, image)
        self.assertNotIn(b'source_stage27', lower)
        for forbidden in (b'live keyboard input', b'save/load', b'networking', b'real audio playback', b'mixer/device playback', b'gcc:', b'mingw', b'microsoft visual c'):
            self.assertNotIn(forbidden, lower)

    @unittest.skipUnless(os.name == 'nt', 'GUI smoke test requires Windows')
    def test_smoke_launch_reports_stage26_ceiling_and_preserved_stage25_to_stage19(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f'pinned WAD missing: {PINNED_WAD}')
        ref = stage.reference_first_ceiling_or_crusher_special_probe_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / 'build' / 'source_stage26_first_ceiling_or_crusher_special_probe.exe'
        stage.write_source_stage26_first_ceiling_or_crusher_special_probe_exe(exe_path)
        expected = (f'S19SIG={ref.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature}', f'S20SIG={ref.stage25.stage24.stage23.stage22.stage21.stage20.signature}', f'S21SIG={ref.stage25.stage24.stage23.stage22.stage21.signature}', f'S22SIG={ref.stage25.stage24.stage23.stage22.signature}', f'S23SIG={ref.stage25.stage24.stage23.signature}', f'S24SIG={ref.stage25.stage24.signature}', f'S25SIG={ref.stage25.signature}', f'S26SIG={ref.signature}', 'S26LINE=71', 'TEX260=SW1GSTON', 'TEX261=SW2GSTON')
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn('S25LINE=2304', title)
            self.assertIn('S24LINE=391', title)
            self.assertIn('S23LINE=3452', title)
            self.assertIn('S22LINE=839', title)
            self.assertIn('S21SEC=56', title)
            self.assertIn('S20ID=88', title)
            self.assertIn('S19LINE=332', title)
            self.assertIn('TSEC26=117', title)
            self.assertIn('F26=192', title)
            self.assertIn('C260=304', title)
            self.assertIn('BOT26=200', title)
            self.assertIn('TOP26=304', title)
            self.assertIn('DIR261=-1', title)
            self.assertIn('BREV26=1', title)
            self.assertIn('TREV26=1', title)
            self.assertIn('MSND26=27', title)
            self.assertIn('AUD26=0', title)
            self.assertIn('S27ABS=1', title)
        finally:
            if hwnd:
                import ctypes
                ctypes.WinDLL('user32', use_last_error=True).PostMessageW(hwnd, 0x0010, 0, 0)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=3)


if __name__ == '__main__':
    unittest.main()
