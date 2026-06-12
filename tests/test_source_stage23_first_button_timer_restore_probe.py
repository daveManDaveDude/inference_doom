import os
import subprocess
import time
import unittest
from pathlib import Path

from tools.map_loader import LoadedMap, Sector
from tools import emit_source_stage14_game_loop_input_collision as stage14
from tools import emit_source_stage23_first_button_timer_restore_probe as stage


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
    special: int = 61,
    tag: int = 24,
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
        side_middle=("SW1COMP", ""),
    )


def _world(*, side: stage.stage22.Stage22SideDefTextures | None = None) -> stage.Stage23World:
    line = _line()
    sectors = (
        stage.stage19.Stage19Sector(0, 0, 56 * stage.FRACUNIT),
        stage.stage19.Stage19Sector(1, -64 * stage.FRACUNIT, 48 * stage.FRACUNIT, tag=24),
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
    blockmap = stage14.BlockMap(
        origin_x=-128 * stage.FRACUNIT,
        origin_y=-128 * stage.FRACUNIT,
        width=4,
        height=4,
        shorts=(),
        offsets=(0,) * 16,
        lists=((0,),) * 16,
    )
    base = stage.stage19.Stage19World(
        loaded=loaded,
        blockmap=blockmap,
        sectors=list(sectors),
        lines=[line],
        sector_lines=stage.stage19.build_stage19_sector_lines((line,), len(sectors)),
        counters=stage.stage19.Stage19Counters(),
    )
    pair = stage.stage22.Stage22SwitchPair(0, 0, "SW1COMP", "SW2COMP", 1, 2)
    switchlist, names = stage.stage22._flatten_switchlist((pair,))
    return stage.Stage23World(
        base=base,
        side_textures=[side or stage.stage22.Stage22SideDefTextures(0, 0, 1)],
        switch_pairs=(pair,),
        switchlist=switchlist,
        switchlist_names=names,
        texture_name_by_id={0: "-", 1: "SW1COMP", 2: "SW2COMP", 99: "OTHER"},
        counters=stage.Stage23Counters(switchlist_init_calls=1, switch_pairs_available=1, switchlist_entries=2),
    )


class SourceStage23FirstButtonTimerRestoreTests(unittest.TestCase):
    def test_source_trace_labels_name_button_restore_route(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("P_UseSpecialLine_button61_vld_open_source_shape_debug", labels)
        self.assertIn("P_StartButton_first_reusable_button_source_shape_debug", labels)
        self.assertIn("P_UpdateSpecials_button_timer_restore_source_shape_debug", labels)
        self.assertIn("EV_DoDoor_map15_button_tagged_vld_open_source_shape_debug", labels)

    def test_synthetic_p_start_button_duplicate_free_full_and_slots(self) -> None:
        for where in (stage.BUTTON_TOP, stage.BUTTON_MIDDLE, stage.BUTTON_BOTTOM):
            side = stage.stage22.Stage22SideDefTextures(0, 0, 0)
            stage.stage22._set_switch_slot_value(side, where, 2)
            world = _world(side=side)
            slot = stage.p_start_button_stage23_source_shape(world, world.lines[0], where, 1, stage.BUTTONTIME)
            duplicate = stage.p_start_button_stage23_source_shape(world, world.lines[0], where, 1, stage.BUTTONTIME)
            self.assertEqual((slot, duplicate), (0, -1))
            self.assertEqual((world.buttonlist[0].where, world.buttonlist[0].btexture, world.buttonlist[0].btimer), (where, 1, 35))

        full = _world()
        for i, button in enumerate(full.buttonlist):
            button.line_index = 100 + i
            button.where = stage.BUTTON_MIDDLE
            button.btexture = 1
            button.btimer = 1
        self.assertEqual(stage.p_start_button_stage23_source_shape(full, full.lines[0], stage.BUTTON_MIDDLE, 1), -2)
        self.assertEqual(full.counters.button_full_errors, 1)

    def test_synthetic_p_update_specials_noop_countdown_restore_sound_and_clear(self) -> None:
        inactive = _world()
        stage.p_update_specials_stage23_source_shape(inactive)
        self.assertEqual((inactive.counters.inactive_button_noops, inactive.counters.button_countdowns), (1, 0))

        for where in (stage.BUTTON_TOP, stage.BUTTON_MIDDLE, stage.BUTTON_BOTTOM):
            side = stage.stage22.Stage22SideDefTextures(0, 0, 0)
            stage.stage22._set_switch_slot_value(side, where, 2)
            slot_world = _world(side=side)
            stage.p_start_button_stage23_source_shape(slot_world, slot_world.lines[0], where, 1, 1)
            stage.p_update_specials_stage23_source_shape(slot_world)
            self.assertEqual(stage.stage22._switch_slot_value(slot_world.side_textures[0], where), 1)
            self.assertEqual((slot_world.buttonlist[0].btimer, slot_world.counters.button_slot_clears), (0, 1))

        world = _world(side=stage.stage22.Stage22SideDefTextures(0, 0, 2))
        stage.p_start_button_stage23_source_shape(world, world.lines[0], stage.BUTTON_MIDDLE, 1, 2)
        stage.p_update_specials_stage23_source_shape(world)
        self.assertEqual((world.buttonlist[0].btimer, world.side_textures[0].midtexture), (1, 2))
        stage.p_update_specials_stage23_source_shape(world)
        self.assertEqual((world.buttonlist[0].btimer, world.buttonlist[0].line_index), (0, -1))
        self.assertEqual(world.side_textures[0].midtexture, 1)
        self.assertEqual((world.counters.button_restore_steps, world.counters.button_switch_off_sound_deferrals, world.counters.button_slot_clears), (1, 1, 1))
        self.assertEqual((world.button_trace[-1].timer_before, world.button_trace[-1].timer_after, world.button_trace[-1].restored), (1, 0, 1))

    def test_synthetic_change_switch_texture_use_again_preserves_special_starts_and_restores(self) -> None:
        world = _world()
        result = stage.p_change_switch_texture_stage23_source_shape(world, world.lines[0], 1)

        self.assertEqual((result.before_name, result.after_name, result.where), ("SW1COMP", "SW2COMP", stage.BUTTON_MIDDLE))
        self.assertEqual((world.lines[0].special, result.line_special_after), (61, 61))
        self.assertEqual((result.button_started, world.buttonlist[0].btexture, world.buttonlist[0].btimer), (1, 1, 35))
        for _ in range(stage.BUTTONTIME):
            stage.p_update_specials_stage23_source_shape(world)
        self.assertEqual((world.side_textures[0].midtexture, world.buttonlist[0].btimer), (1, 0))

    def test_real_candidate_census_documents_map01_absence_and_map15_candidate(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        map01_count, all_count, door_count, records = stage.reusable_switch_button_census(PINNED_WAD)

        self.assertEqual((map01_count, all_count, door_count), (0, 72, 8))
        self.assertIn(("MAP15", 3452, 61, 24, 4798, stage.NO_SIDEDEF, 548, ("-", "SW1COMP", "-")), records)

    def test_pinned_map_stage23_reference_restores_map15_button_and_preserves_baselines(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_first_button_timer_restore_probe_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.stage22.signature, 2207028069)
        self.assertEqual(ref.stage22.stage21.signature, 1770773845)
        self.assertEqual(ref.stage22.stage21.stage20.signature, 3226031347)
        self.assertEqual(ref.stage22.stage21.stage20.stage19.signature, 2088411722)
        self.assertEqual((ref.census.map_name, ref.census.line_index, ref.census.special, ref.census.tag), ("MAP15", 3452, 61, 24))
        self.assertEqual((ref.census.right_sidedef, ref.census.left_sidedef, ref.census.front_sector), (4798, stage.NO_SIDEDEF, 548))
        self.assertEqual((ref.census.middle_texture_before, ref.census.middle_texture_pressed, ref.census.middle_texture_restored), ("SW1COMP", "SW2COMP", "SW1COMP"))
        self.assertEqual((ref.switch.pair_index, ref.switch.switchlist_index, ref.switch.where), (6, 12, stage.BUTTON_MIDDLE))
        self.assertEqual((ref.switch.line_special_before, ref.switch.line_special_after), (61, 61))
        self.assertEqual((ref.button_slot, ref.button_timer_start, ref.button_timer_end, ref.duplicate_guard_result), (0, 35, 0, -1))
        self.assertEqual((ref.counters.button_countdowns, ref.counters.button_restore_steps, ref.counters.button_slot_clears), (35, 1, 1))
        self.assertEqual((ref.counters.button_switch_off_sound_deferrals, ref.counters.real_audio_playbacks), (1, 0))
        self.assertEqual((ref.door_spawn.matched_sectors, ref.door_spawn.spawned_sectors), ((530,), (530,)))
        self.assertEqual((ref.census.target_floor >> stage.FRACBITS, ref.census.target_ceiling >> stage.FRACBITS, ref.census.target_special), (-64, 48, 0))
        self.assertEqual((ref.census.surrounding_lowest_ceiling >> stage.FRACBITS, ref.census.topheight >> stage.FRACBITS), (56, 52))
        self.assertEqual((ref.door_spawn.direction, ref.door_spawn.speed >> stage.FRACBITS, ref.door_spawn.topwait), (1, 2, 150))
        self.assertEqual((ref.ticker_counters.ticker_calls, ref.ticker_counters.update_specials_calls, ref.leveltime_after), (35, 35, 35))
        self.assertEqual((ref.ticker_counters.t_vertical_door_ticks, ref.ticker_counters.move_plane_calls, ref.ticker_counters.door_removal_requests), (3, 3, 1))
        self.assertEqual((ref.order_ok, ref.counters.fallback_used, ref.counters.stage24_absent), (1, 0, 1))
        self.assertEqual((ref.counters.generalized_specials, ref.counters.generalized_doors, ref.counters.generalized_sector_effects), (0, 0, 0))
        self.assertEqual(ref.signature, 3216085132)

    def test_executable_build_contains_stage23_status_preserves_stage22_and_omits_forbidden_strings(self) -> None:
        image = stage.build_source_stage23_first_button_timer_restore_probe_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage23_first_button_timer_restore_probe", image)
        self.assertIn(b"First reusable button timer restore proof OK", image)
        self.assertIn(b"P_StartButton", image)
        self.assertIn(b"P_UpdateSpecials", image)
        self.assertIn(b"SW1COMP", image)
        self.assertIn(b"SW2COMP", image)
        for marker in (b" S19SIG=", b" S20SIG=", b" S21SIG=", b" S22SIG=", b" S23SIG="):
            self.assertIn(marker, image)
        self.assertNotIn(b"source_stage24", lower)
        for forbidden in (
            b"generalized floor",
            b"generalized plat",
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
    def test_smoke_launch_reports_stage23_button_restore_and_preserved_stage22_stage21_stage20_stage19(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_first_button_timer_restore_probe_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage23_first_button_timer_restore_probe.exe"
        stage.write_source_stage23_first_button_timer_restore_probe_exe(exe_path)

        expected = (
            f"S19SIG={ref.stage22.stage21.stage20.stage19.signature}",
            f"S20SIG={ref.stage22.stage21.stage20.signature}",
            f"S21SIG={ref.stage22.stage21.signature}",
            f"S22SIG={ref.stage22.signature}",
            f"S23SIG={ref.signature}",
            "S23LINE=3452",
            "TEX230=SW1COMP",
            "TEX231=SW2COMP",
            "TEX232=SW1COMP",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn("S22LINE=839", title)
            self.assertIn("S21SEC=56", title)
            self.assertIn("S20ID=88", title)
            self.assertIn("S19LINE=332", title)
            self.assertIn("BT230=35", title)
            self.assertIn("BT231=0", title)
            self.assertIn("BREST23=1", title)
            self.assertIn("BCLR23=1", title)
            self.assertIn("TSEC23=530", title)
            self.assertIn("MAP01BTN23=0", title)
            self.assertIn("CENS23=72", title)
            self.assertIn("DOORBTN23=8", title)
            self.assertIn("AUD23=0", title)
            self.assertIn("GEN23=0", title)
            self.assertIn("S24ABS=1", title)
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
