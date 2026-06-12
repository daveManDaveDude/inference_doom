import os
import struct
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage14_game_loop_input_collision as stage
from tools.map_loader import LoadedMap, Sector


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


def _blockmap_data(header: tuple[int, int, int, int], offsets: tuple[int, ...], tail: tuple[int, ...]) -> bytes:
    return struct.pack("<" + "h" * (4 + len(offsets) + len(tail)), *(header + offsets + tail))


def _line(
    index: int,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    *,
    flags: int = 0,
    special: int = 0,
    front: int = 0,
    back: int | None = None,
) -> stage.MovementLine:
    v1x = x1 << stage.FRACBITS
    v1y = y1 << stage.FRACBITS
    v2x = x2 << stage.FRACBITS
    v2y = y2 << stage.FRACBITS
    dx = v2x - v1x
    dy = v2y - v1y
    return stage.MovementLine(
        index=index,
        v1x=v1x,
        v1y=v1y,
        v2x=v2x,
        v2y=v2y,
        dx=dx,
        dy=dy,
        bbox=(max(v1y, v2y), min(v1y, v2y), min(v1x, v2x), max(v1x, v2x)),
        slopetype=stage._slopetype(dx, dy),
        flags=flags,
        special=special,
        frontsector=front,
        backsector=back,
    )


def _mobj(index: int = 0, **kwargs) -> stage.MovementMobj:
    defaults = dict(
        mapthing_index=index,
        type_name="MT_TEST",
        doomednum=1,
        x=0,
        y=0,
        z=0,
        angle=0,
        momx=0,
        momy=0,
        momz=0,
        radius=16 * stage.FRACUNIT,
        height=56 * stage.FRACUNIT,
        flags=stage.stage13.MF_SOLID,
        floorz=0,
        ceilingz=128 * stage.FRACUNIT,
        subsector=0,
        sector=0,
        player_index=0 if index == 0 else -1,
        state_name="S_PLAY" if index == 0 else "S_INERT",
    )
    defaults.update(kwargs)
    return stage.MovementMobj(index=index, **defaults)


def _world(
    *,
    lines: tuple[stage.MovementLine, ...] = (),
    sectors: tuple[stage.MovementSector, ...] = (
        stage.MovementSector(0, 0, 128 * stage.FRACUNIT),
    ),
    mobjs: tuple[stage.MovementMobj, ...] = (_mobj(),),
    block_lists: tuple[tuple[int, ...], ...] | None = None,
) -> stage.MovementWorld:
    width = height = 4
    if block_lists is None:
        block_lists = tuple(tuple(line.index for line in lines) for _ in range(width * height))
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
                0,
            )
            for sector in sectors
        ),
        things=(),
    )
    geometry = stage.stage13.MapGeometry((), (), (), ())
    blockmap = stage.BlockMap(
        origin_x=-128 * stage.FRACUNIT,
        origin_y=-128 * stage.FRACUNIT,
        width=width,
        height=height,
        shorts=(),
        offsets=(0,) * (width * height),
        lists=block_lists,
    )
    world = stage.MovementWorld(
        loaded=loaded,
        geometry=geometry,
        blockmap=blockmap,
        sectors=list(sectors),
        lines=list(lines),
        mobjs=[m for m in mobjs],
        player=stage.MovementPlayer(0, 0, stage.TicCmd(), 41 * stage.FRACUNIT),
        blocklinks=[None] * (width * height),
        sectorlinks=[None] * len(sectors),
        iterator=stage.BlockIteratorState(),
        counters=stage.MovementCounters(),
    )
    for mobj in world.mobjs:
        stage.p_set_thing_position_source_shape(world, mobj)
    world.counters = stage.MovementCounters()
    return world


class SourceStage14GameLoopInputCollisionTests(unittest.TestCase):
    def test_source_trace_covers_stage14_game_loop_input_collision_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("P_LoadBlockMap_source_shape_debug", labels)
        self.assertIn("P_BlockIterators_source_shape_debug", labels)
        self.assertIn("P_CheckPosition_TryMove_source_shape_debug", labels)
        self.assertIn("P_PlayerThinkMovement_source_shape_debug", labels)
        self.assertIn("P_XYMovementRelink_source_shape_debug", labels)
        self.assertIn("G_Ticker_ticcmd_dispatch_source_shape_debug", labels)
        self.assertIn("R_SetupFrame_after_movement_source_shape_debug", labels)

    def test_synthetic_p_load_blockmap_decodes_header_offsets_and_lists(self) -> None:
        data = _blockmap_data(
            (-1, 2, 2, 1),
            (6, 9),
            (0, 2, -1, 1, -1),
        )

        blockmap = stage.p_load_blockmap_source_shape(data, num_lines=3)

        self.assertEqual((blockmap.origin_x, blockmap.origin_y), (-stage.FRACUNIT, 2 * stage.FRACUNIT))
        self.assertEqual((blockmap.width, blockmap.height, blockmap.block_count), (2, 1, 2))
        self.assertEqual(blockmap.offsets, (6, 9))
        self.assertEqual(blockmap.lists, ((0, 2), (1,)))

    def test_synthetic_p_load_blockmap_rejects_malformed_records(self) -> None:
        with self.assertRaises(ValueError):
            stage.p_load_blockmap_source_shape(b"\x00")
        with self.assertRaises(ValueError):
            stage.p_load_blockmap_source_shape(struct.pack("<hhhhH", 0, 0, 4, 1, 0))
        with self.assertRaises(ValueError):
            stage.p_load_blockmap_source_shape(_blockmap_data((0, 0, 1, 1), (99,), (-1,)))
        with self.assertRaises(ValueError):
            stage.p_load_blockmap_source_shape(_blockmap_data((0, 0, 1, 1), (5,), (0,)), num_lines=1)
        with self.assertRaises(ValueError):
            stage.p_load_blockmap_source_shape(_blockmap_data((0, 0, 1, 1), (5,), (7, -1)), num_lines=2)

    def test_synthetic_block_iterators_visit_in_order_suppress_duplicates_and_bound_overflow(self) -> None:
        blockmap = stage.BlockMap(
            origin_x=0,
            origin_y=0,
            width=2,
            height=1,
            shorts=(),
            offsets=(0, 0),
            lists=((0, 1, 0, 2), (1, 2)),
        )
        lines = (_line(0, 0, 0, 0, 64), _line(1, 0, 0, 64, 0), _line(2, 64, 0, 64, 64))
        state = stage.BlockIteratorState(validcount=42)
        visited: list[int] = []

        self.assertTrue(
            stage.p_block_lines_iterator_source_shape(
                blockmap,
                0,
                0,
                lines,
                state,
                lambda line: visited.append(line.index) is None or True,
            )
        )
        self.assertTrue(
            stage.p_block_lines_iterator_source_shape(
                blockmap,
                1,
                0,
                lines,
                state,
                lambda line: visited.append(line.index) is None or True,
            )
        )
        self.assertEqual(visited, [0, 1, 2])
        self.assertEqual(state.line_duplicate_skips, 3)

        overflow = stage.BlockIteratorState(validcount=7)
        stage.p_block_lines_iterator_source_shape(
            blockmap,
            0,
            0,
            lines,
            overflow,
            lambda _line: True,
            max_line_entries=1,
        )
        self.assertEqual((overflow.line_visits, overflow.line_overflows), (1, 1))

        world = _world(mobjs=(_mobj(0), _mobj(1, x=1), _mobj(2, x=2)))
        world.blocklinks[0] = 0
        world.mobjs[0].bnext = 1
        world.mobjs[1].bnext = 2
        things: list[int] = []
        stage.p_block_things_iterator_source_shape(
            world,
            0,
            0,
            lambda thing: things.append(thing.index) is None or True,
            max_thing_entries=2,
        )
        self.assertEqual(things, [0, 1])
        self.assertEqual(world.iterator.thing_overflows, 1)

    def test_synthetic_ticcmd_thrust_moveplayer_and_xy_movement_apply_momentum_and_friction(self) -> None:
        world = _world()
        player = world.player
        mo = world.mobjs[player.mo_index]

        stage.p_thrust_source_shape(player, mo, 0, 25 * 2048)
        self.assertGreater(mo.momx, 0)
        self.assertGreaterEqual(mo.momy, 0)

        mo.momx = mo.momy = 0
        player.cmd = stage.TicCmd(forwardmove=25, sidemove=24, angleturn=320)
        stage.p_move_player_source_shape(world, player)
        self.assertEqual(stage.angle_to_degrees(mo.angle), 1)
        self.assertNotEqual((mo.momx, mo.momy), (0, 0))

        before = (mo.x, mo.y, mo.momx, mo.momy)
        stage.p_xy_movement_source_shape(world, mo)
        self.assertNotEqual((mo.x, mo.y), before[:2])
        self.assertEqual(world.counters.accepted_moves, 1)
        self.assertLess(abs(mo.momx), abs(before[2]) + 1)
        self.assertLess(abs(mo.momy), abs(before[3]) + 1)

    def test_synthetic_trymove_open_space_wall_step_drop_thing_and_deferred_special(self) -> None:
        open_world = _world()
        self.assertTrue(stage.p_try_move_source_shape(open_world, open_world.mobjs[0], 32 * stage.FRACUNIT, 0))
        self.assertEqual(open_world.counters.accepted_moves, 1)

        wall = _line(0, 64, -64, 64, 64)
        wall_world = _world(lines=(wall,))
        self.assertFalse(stage.p_try_move_source_shape(wall_world, wall_world.mobjs[0], 64 * stage.FRACUNIT, 0))
        self.assertEqual((wall_world.counters.rejected_moves, wall_world.counters.blocking_lines), (1, 1))

        high_sector = stage.MovementSector(1, 32 * stage.FRACUNIT, 128 * stage.FRACUNIT)
        step_line = _line(0, 64, -64, 64, 64, back=1)
        step_world = _world(sectors=(stage.MovementSector(0, 0, 128 * stage.FRACUNIT), high_sector), lines=(step_line,))
        self.assertFalse(stage.p_try_move_source_shape(step_world, step_world.mobjs[0], 64 * stage.FRACUNIT, 0))
        self.assertEqual(step_world.counters.step_rejects, 1)

        low_sector = stage.MovementSector(1, -32 * stage.FRACUNIT, 128 * stage.FRACUNIT)
        drop_line = _line(0, 64, -64, 64, 64, back=1)
        dropper = _mobj(flags=stage.stage13.MF_SOLID, player_index=-1)
        drop_world = _world(
            sectors=(stage.MovementSector(0, 0, 128 * stage.FRACUNIT), low_sector),
            lines=(drop_line,),
            mobjs=(dropper,),
        )
        self.assertFalse(stage.p_try_move_source_shape(drop_world, drop_world.mobjs[0], 64 * stage.FRACUNIT, 0))
        self.assertEqual(drop_world.counters.dropoff_rejects, 1)

        blocker = _mobj(1, x=32 * stage.FRACUNIT, flags=stage.stage13.MF_SOLID)
        thing_world = _world(mobjs=(_mobj(0), blocker), block_lists=tuple(() for _ in range(16)))
        self.assertFalse(stage.p_try_move_source_shape(thing_world, thing_world.mobjs[0], 32 * stage.FRACUNIT, 0))
        self.assertEqual(thing_world.counters.blocking_things, 1)

        special = _mobj(1, x=32 * stage.FRACUNIT, flags=stage.stage13.MF_SPECIAL)
        special_world = _world(mobjs=(_mobj(0, flags=stage.stage13.MF_SOLID | stage.stage13.MF_PICKUP), special), block_lists=tuple(() for _ in range(16)))
        self.assertTrue(stage.p_try_move_source_shape(special_world, special_world.mobjs[0], 32 * stage.FRACUNIT, 0))
        self.assertEqual(special_world.counters.special_things_deferred, 1)

    def test_pinned_map_runs_scripted_movement_and_collision_probe(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_game_loop_input_collision_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.stage13.stage12.framebuffer_signature, 2853564869)
        self.assertEqual(ref.stage13.draw.framebuffer_signature, 2904743961)
        self.assertEqual((ref.blockmap.origin_x >> stage.FRACBITS, ref.blockmap.origin_y >> stage.FRACBITS), (-256, -1808))
        self.assertEqual((ref.blockmap.width, ref.blockmap.height, ref.blockmap.offsets[0]), (20, 27, 544))
        self.assertEqual((ref.initial_player.x >> stage.FRACBITS, ref.initial_player.y >> stage.FRACBITS), (-192, -192))

        self.assertEqual(len(ref.script), 8)
        self.assertEqual((ref.counters.accepted_moves, ref.counters.rejected_moves), (8, 0))
        self.assertEqual((ref.counters.line_checks, ref.counters.thing_checks), (48, 0))
        self.assertEqual((ref.iterator.line_iterator_calls, ref.iterator.thing_iterator_calls), (8, 16))
        self.assertEqual((ref.iterator.line_visits, ref.iterator.line_duplicate_skips), (48, 8))
        self.assertEqual((ref.counters.block_relinks, ref.counters.sector_relinks), (8, 8))
        self.assertEqual((ref.counters.slide_attempts, ref.counters.slide_deferred), (0, 0))

        self.assertEqual((ref.final_mobj.x, ref.final_mobj.y), (-11234608, -12661930))
        self.assertEqual((ref.final_mobj.x >> stage.FRACBITS, ref.final_mobj.y >> stage.FRACBITS), (-172, -194))
        self.assertEqual((ref.frame.viewangle_degrees, ref.frame.subsector, ref.frame.sector), (3, 227, 0))
        self.assertEqual((ref.frame.viewz, ref.final_mobj.momx, ref.final_mobj.momy), (2753061, 183699, -36831))
        self.assertEqual((ref.probe.active, ref.probe.line_index, ref.probe.blocked, ref.probe.blocking_lines), (1, 0, 1, 1))
        self.assertEqual(ref.signature, 3925602456)

    def test_executable_build_contains_stage14_status_and_no_deferred_feature_strings(self) -> None:
        image = stage.build_source_stage14_game_loop_input_collision_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage14_game_loop_input_collision", image)
        self.assertIn(b"Scripted local movement and collision OK", image)
        self.assertIn(b"P_LoadBlockMap", image)
        self.assertIn(b"P_BlockLinesIterator", image)
        self.assertIn(b"P_BlockThingsIterator", image)
        self.assertIn(b"P_CheckPosition", image)
        self.assertIn(b"P_TryMove", image)
        self.assertIn(b"G_Ticker", image)
        self.assertIn(b"R_SetupFrame", image)
        self.assertIn(b" BMW=", image)
        self.assertIn(b" ACPT=", image)
        self.assertIn(b" CPROBE=", image)
        self.assertIn(b" S14SIG=", image)
        self.assertNotIn(b"source_stage15", lower)
        for forbidden in (
            b"pickups",
            b"attacks",
            b"monster ai",
            b"doors",
            b"switches",
            b"damage",
            b"sound",
            b"status bar",
            b"automap",
            b"menus",
            b"save/load",
            b"networking",
            b"gcc:",
            b"mingw",
            b"microsoft visual c",
        ):
            self.assertNotIn(forbidden, lower)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage14_movement_and_preserved_stage13(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_game_loop_input_collision_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage14_game_loop_input_collision.exe"
        stage.write_source_stage14_game_loop_input_collision_exe(exe_path)

        expected = (
            f"S13SIG={ref.stage13.draw.framebuffer_signature}",
            f"BMW={ref.blockmap.width}",
            f"BMH={ref.blockmap.height}",
            f"TIC={len(ref.script)}",
            f"ACPT={ref.counters.accepted_moves}",
            f"F14X={ref.final_mobj.x >> stage.FRACBITS}",
            f"F14Y={ref.final_mobj.y >> stage.FRACBITS}",
            f"S14SIG={ref.signature}",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn(f"S12SIG={ref.stage13.stage12.framebuffer_signature}", title)
            self.assertIn(f"TH={ref.stage13.thing_load.loaded_count}", title)
            self.assertIn(f"VIS={len(ref.stage13.vissprites)}", title)
            self.assertIn(f"F14A={ref.frame.viewangle_degrees}", title)
            self.assertIn(f"F14SS={ref.frame.subsector}", title)
            self.assertIn(f"LCHK={ref.counters.line_checks}", title)
            self.assertIn(f"BTI={ref.iterator.thing_iterator_calls}", title)
            self.assertIn(f"CPROBE={ref.probe.active}", title)
            self.assertIn(f"CBLN={ref.probe.blocking_lines}", title)
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
