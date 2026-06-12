import os
import subprocess
import time
import unittest
from pathlib import Path

from tools.map_loader import LoadedMap, Sector
from tools import emit_source_stage13_things_sprites_and_real_frame_setup as stage13
from tools import emit_source_stage14_game_loop_input_collision as stage14
from tools import emit_source_stage16_active_monster_thinkers_and_targeting as stage16
from tools import emit_source_stage18_post_damage_monster_movement_and_chase_probe as stage


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
    flags: int = 0,
    special: int = 0,
    front: int = 0,
    back: int | None = None,
) -> stage14.MovementLine:
    v1x = x1 << stage.FRACBITS
    v1y = y1 << stage.FRACBITS
    v2x = x2 << stage.FRACBITS
    v2y = y2 << stage.FRACBITS
    dx = v2x - v1x
    dy = v2y - v1y
    return stage14.MovementLine(
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
        frontsector=front,
        backsector=back,
    )


def _active_mobj(
    info: stage16.Stage16InfoTables,
    *,
    index: int = 0,
    type_name: str = "MT_SHOTGUY",
    state_name: str = "S_SPOS_RUN1",
    x: int = 0,
    y: int = 0,
    momx: int = 0,
    momy: int = 0,
    tics: int | None = None,
    target_index: int | None = 1,
    threshold: int = 0,
) -> stage16.ActiveMobj:
    minfo = info.by_name[type_name]
    state = info.state_info.state_index[state_name]
    st = info.state_info.states[state]
    return stage16.ActiveMobj(
        index=index,
        mapthing_index=index,
        type_name=type_name,
        doomednum=minfo.doomednum,
        x=x,
        y=y,
        z=0,
        angle=0,
        momx=momx,
        momy=momy,
        momz=0,
        radius=minfo.radius,
        height=minfo.height,
        flags=minfo.flags,
        floorz=0,
        ceilingz=128 * stage.FRACUNIT,
        subsector=0,
        sector=0,
        health=minfo.spawnhealth,
        reactiontime=0,
        state=state,
        tics=st.tics if tics is None else tics,
        sprite=st.sprite,
        frame=st.frame,
        lastlook=0,
        threshold=threshold,
        target_index=target_index,
        movedir=stage.DI_NODIR,
        movecount=0,
    )


def _movement_mobj_from_active(active: stage16.ActiveMobj) -> stage14.MovementMobj:
    return stage14.MovementMobj(
        index=active.index,
        mapthing_index=active.mapthing_index,
        type_name=active.type_name,
        doomednum=active.doomednum,
        x=active.x,
        y=active.y,
        z=active.z,
        angle=active.angle,
        momx=active.momx,
        momy=active.momy,
        momz=active.momz,
        radius=active.radius,
        height=active.height,
        flags=active.flags,
        floorz=active.floorz,
        ceilingz=active.ceilingz,
        subsector=active.subsector,
        sector=active.sector,
        player_index=-1,
        reactiontime=active.reactiontime,
        state_name=active.type_name,
    )


def _target(index: int = 1, *, x: int = 256 * stage.FRACUNIT, y: int = 0, flags: int | None = None) -> stage16.ActiveMobj:
    if flags is None:
        flags = stage13.MF_SOLID | stage13.MF_SHOOTABLE
    return stage16.ActiveMobj(
        index=index,
        mapthing_index=index,
        type_name="MT_PLAYER",
        doomednum=1,
        x=x,
        y=y,
        z=0,
        angle=0,
        momx=0,
        momy=0,
        momz=0,
        radius=16 * stage.FRACUNIT,
        height=56 * stage.FRACUNIT,
        flags=flags,
        floorz=0,
        ceilingz=128 * stage.FRACUNIT,
        subsector=0,
        sector=0,
        health=100,
        reactiontime=0,
        state=None,
        tics=-1,
        sprite=0,
        frame=0,
        lastlook=0,
    )


def _stage18_world(
    *,
    actor: stage16.ActiveMobj | None = None,
    targets: dict[int, stage16.ActiveMobj] | None = None,
    lines: tuple[stage14.MovementLine, ...] = (),
    sectors: tuple[stage14.MovementSector, ...] = (
        stage14.MovementSector(0, 0, 128 * stage.FRACUNIT),
    ),
    blockers: tuple[stage14.MovementMobj, ...] = (),
    execute_chase_actions: bool = False,
) -> stage.Stage18World:
    info = stage16.parse_stage16_info_tables()
    if actor is None:
        actor = _active_mobj(info)
    mobjs = [_movement_mobj_from_active(actor), *blockers]
    width = height = 4
    blockmap = stage14.BlockMap(
        origin_x=-128 * stage.FRACUNIT,
        origin_y=-128 * stage.FRACUNIT,
        width=width,
        height=height,
        shorts=(),
        offsets=(0,) * (width * height),
        lists=tuple(tuple(line.index for line in lines) for _ in range(width * height)),
    )
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
    movement = stage14.MovementWorld(
        loaded=loaded,
        geometry=stage13.MapGeometry((), (), (), ()),
        blockmap=blockmap,
        sectors=list(sectors),
        lines=list(lines),
        mobjs=mobjs,
        player=stage14.MovementPlayer(0, 0, stage14.TicCmd(), 41 * stage.FRACUNIT),
        blocklinks=[None] * blockmap.block_count,
        sectorlinks=[None] * len(sectors),
        iterator=stage14.BlockIteratorState(),
        counters=stage14.MovementCounters(),
    )
    for mobj in movement.mobjs:
        stage14.p_set_thing_position_source_shape(movement, mobj)
    movement.counters = stage14.MovementCounters()
    return stage.Stage18World(
        movement=movement,
        info=info,
        actor=actor,
        targets={1: _target()} if targets is None else targets,
        counters=stage.Stage18Counters(),
        rng=stage16.DoomRandom(0),
        execute_chase_actions=execute_chase_actions,
    )


class SourceStage18PostDamageMonsterMovementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.info = stage16.parse_stage16_info_tables()

    def test_source_trace_labels_name_stage18_movement_route(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("P_MobjThinker_XYMovement_post_damage_source_shape_debug", labels)
        self.assertIn("P_TryMove_monster_post_damage_source_shape_debug", labels)
        self.assertIn("P_BlockIterators_monster_movement_source_shape_debug", labels)
        self.assertIn("A_Pain_A_Chase_monster_movement_source_shape_debug", labels)

    def test_synthetic_post_damage_mobj_thinker_services_momentum_and_pain_recovery(self) -> None:
        actor = _active_mobj(
            self.info,
            state_name="S_SPOS_PAIN",
            tics=3,
            momx=8 * stage.FRACUNIT,
            momy=0,
            threshold=stage.BASETHRESHOLD,
        )
        world = _stage18_world(actor=actor)

        first = stage.p_mobj_thinker_stage18_source_shape(world, actor)
        self.assertEqual((first.accepted_moves, first.rejected_moves), (1, 0))
        self.assertGreater(actor.x, 0)
        self.assertEqual((stage._state_name(self.info, actor.state), actor.tics), ("S_SPOS_PAIN", 2))
        self.assertEqual((world.counters.xy_movement_services, world.counters.state_tic_decrements), (1, 1))

        actor.momx = actor.momy = 0
        stage._sync_active_to_movement(world)
        stage.p_mobj_thinker_stage18_source_shape(world, actor)
        stage.p_mobj_thinker_stage18_source_shape(world, actor)
        self.assertEqual((stage._state_name(self.info, actor.state), actor.tics), ("S_SPOS_PAIN2", 3))
        self.assertEqual(world.counters.pain_sound_deferrals, 1)

        for _ in range(3):
            stage.p_mobj_thinker_stage18_source_shape(world, actor)
        self.assertEqual((stage._state_name(self.info, actor.state), actor.tics), ("S_SPOS_RUN1", 3))
        self.assertEqual((world.counters.chase_reached, world.counters.chase_deferred), (1, 1))

    def test_synthetic_monster_trymove_accepts_blocks_and_accounts_relinks(self) -> None:
        open_world = _stage18_world()
        ok, delta = stage.p_try_move_monster_source_shape(open_world, 32 * stage.FRACUNIT, 0)
        self.assertTrue(ok)
        self.assertEqual((delta.accepted_moves, delta.block_relinks, delta.sector_relinks), (1, 1, 1))

        wall = _line(0, 64, -64, 64, 64)
        wall_world = _stage18_world(lines=(wall,))
        ok, delta = stage.p_try_move_monster_source_shape(wall_world, 64 * stage.FRACUNIT, 0)
        self.assertFalse(ok)
        self.assertEqual((delta.rejected_moves, delta.blocking_lines), (1, 1))

        blocker_active = _active_mobj(self.info, index=1, x=32 * stage.FRACUNIT, y=0)
        blocker = _movement_mobj_from_active(blocker_active)
        thing_world = _stage18_world(blockers=(blocker,))
        ok, delta = stage.p_try_move_monster_source_shape(thing_world, 31 * stage.FRACUNIT, 0)
        self.assertFalse(ok)
        self.assertEqual((delta.rejected_moves, delta.blocking_things), (1, 1))

        high = stage14.MovementSector(1, 32 * stage.FRACUNIT, 128 * stage.FRACUNIT)
        step_line = _line(0, 64, -64, 64, 64, back=1)
        step_world = _stage18_world(
            sectors=(stage14.MovementSector(0, 0, 128 * stage.FRACUNIT), high),
            lines=(step_line,),
        )
        ok, delta = stage.p_try_move_monster_source_shape(step_world, 64 * stage.FRACUNIT, 0)
        self.assertFalse(ok)
        self.assertEqual(delta.step_rejects, 1)

        low = stage14.MovementSector(1, -32 * stage.FRACUNIT, 128 * stage.FRACUNIT)
        drop_line = _line(0, 64, -64, 64, 64, back=1)
        drop_world = _stage18_world(
            sectors=(stage14.MovementSector(0, 0, 128 * stage.FRACUNIT), low),
            lines=(drop_line,),
        )
        ok, delta = stage.p_try_move_monster_source_shape(drop_world, 64 * stage.FRACUNIT, 0)
        self.assertFalse(ok)
        self.assertEqual(delta.dropoff_rejects, 1)

    def test_synthetic_chase_newdir_target_loss_and_attack_gate_deferral(self) -> None:
        actor = _active_mobj(self.info, state_name="S_SPOS_RUN1", tics=3, target_index=1)
        world = _stage18_world(actor=actor, execute_chase_actions=True)
        stage.a_chase_stage18_source_shape(world, actor)
        self.assertEqual(actor.movedir, stage.DI_EAST)
        self.assertGreater(actor.x, 0)
        self.assertEqual((world.counters.new_chase_dir_calls, world.counters.move_accepts), (1, 1))

        lost = _active_mobj(self.info, state_name="S_SPOS_RUN1", tics=3, target_index=1)
        lost_world = _stage18_world(actor=lost, targets={1: _target(flags=0)}, execute_chase_actions=True)
        stage.a_chase_stage18_source_shape(lost_world, lost)
        self.assertEqual(stage._state_name(self.info, lost.state), "S_SPOS_STND")
        self.assertEqual(lost_world.counters.target_loss_fallbacks, 1)

        gated = _active_mobj(self.info, state_name="S_SPOS_RUN1", tics=3, target_index=1)
        gated.flags |= stage13.MF_JUSTHIT
        gate_world = _stage18_world(actor=gated, execute_chase_actions=True)
        stage.a_chase_stage18_source_shape(gate_world, gated)
        self.assertEqual(gate_world.counters.attack_state_deferrals, 1)
        self.assertEqual(gate_world.counters.attack_actions_executed, 0)
        self.assertEqual(gate_world.counters.move_calls, 0)

    def test_pinned_map_stage18_reference_preserves_stage17_and_moves_damaged_monster(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_post_damage_monster_movement_and_chase_probe_for_pinned_map(PINNED_WAD)
        census = ref.census
        final = ref.final_mobj

        self.assertEqual(ref.stage17.signature, 2157381017)
        self.assertEqual((ref.stage17.shell_before, ref.stage17.shell_after), (8, 7))
        self.assertEqual((ref.stage17.health_before, ref.stage17.health_after), (30, 20))
        self.assertEqual((census.mapthing_index, census.mobj_index, census.type_name), (37, 28, "MT_SHOTGUY"))
        self.assertEqual((census.start_x >> stage.FRACBITS, census.start_y >> stage.FRACBITS), (1752, -936))
        self.assertEqual((census.start_sector, census.start_subsector, census.start_block_x, census.start_block_y), (58, 620, 15, 6))
        self.assertEqual((census.health, census.state_name, census.state, census.tics), (20, "S_SPOS_PAIN", 220, 3))
        self.assertEqual((census.target_index, census.threshold, census.momx, census.momy), (0, 100, -22182, -78859))
        self.assertEqual((census.next_state_name, census.recovery_state_name, census.run_state_name), ("S_SPOS_PAIN2", "S_SPOS_PAIN2", "S_SPOS_RUN1"))

        self.assertEqual((final.x, final.y), (114796890, -61420555))
        self.assertEqual((final.x >> stage.FRACBITS, final.y >> stage.FRACBITS), (1751, -938))
        self.assertEqual((ref.trace[-1].block_x, ref.trace[-1].block_y), (15, 6))
        self.assertEqual((stage._state_name(self.info, final.state), final.state, final.tics), ("S_SPOS_PAIN", 220, 2))
        self.assertEqual((final.momx, final.momy), (-20103, -71466))

        self.assertEqual((ref.movement_counters.try_move_calls, ref.movement_counters.accepted_moves, ref.movement_counters.rejected_moves), (1, 1, 0))
        self.assertEqual((ref.movement_counters.line_checks, ref.movement_counters.thing_checks), (8, 0))
        self.assertEqual((ref.iterator.line_iterator_calls, ref.iterator.thing_iterator_calls, ref.iterator.line_visits, ref.iterator.thing_visits), (1, 4, 8, 3))
        self.assertEqual((ref.movement_counters.block_relinks, ref.movement_counters.sector_relinks), (1, 1))
        self.assertEqual((ref.counters.mobj_thinker_calls, ref.counters.xy_movement_services, ref.counters.state_tic_decrements), (1, 1, 1))
        self.assertEqual((ref.counters.chase_calls, ref.counters.new_chase_dir_calls, ref.counters.attack_state_deferrals, ref.counters.attack_actions_executed), (0, 0, 0, 0))
        self.assertEqual(ref.signature, 1615679087)

    def test_executable_build_contains_stage18_status_preserves_stage17_and_omits_later_system_strings(self) -> None:
        image = stage.build_source_stage18_post_damage_monster_movement_and_chase_probe_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage18_post_damage_monster_movement_and_chase_probe", image)
        self.assertIn(b"Post-damage monster movement proof OK", image)
        self.assertIn(b"P_MobjThinker", image)
        self.assertIn(b"P_XYMovement", image)
        self.assertIn(b"P_TryMove", image)
        self.assertIn(b" S17SIG=", image)
        self.assertIn(b" S18SIG=", image)
        self.assertIn(b" TRY18=", image)
        self.assertIn(b" MACC=", image)
        self.assertNotIn(b"source_stage19", lower)
        for forbidden in (
            b"generalized combat",
            b"door/switch",
            b"sound playback",
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
    def test_smoke_launch_reports_stage18_movement_and_preserved_stage17(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_post_damage_monster_movement_and_chase_probe_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage18_post_damage_monster_movement_and_chase_probe.exe"
        stage.write_source_stage18_post_damage_monster_movement_and_chase_probe_exe(exe_path)

        expected = (
            f"S17SIG={ref.stage17.signature}",
            f"S18SIG={ref.signature}",
            f"MT18={ref.census.mapthing_index}",
            f"MO18={ref.census.mobj_index}",
            f"TRY18={ref.movement_counters.try_move_calls}",
            f"MACC={ref.movement_counters.accepted_moves}",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn(f"S14SIG={ref.stage17.stage16.stage15.stage14.signature}", title)
            self.assertIn(f"S15SIG={ref.stage17.stage16.stage15.signature}", title)
            self.assertIn(f"S16SIG={ref.stage17.stage16.signature}", title)
            self.assertIn(f"DMG17={ref.stage17.counters.damage_total}", title)
            self.assertIn(f"H17={ref.stage17.health_after}", title)
            self.assertIn(f"S18STN={ref.census.state_name}", title)
            self.assertIn(f"F18STN={stage._state_name(self.info, ref.final_mobj.state)}", title)
            self.assertIn(f"F18X={ref.final_mobj.x >> stage.FRACBITS}", title)
            self.assertIn(f"F18Y={ref.final_mobj.y >> stage.FRACBITS}", title)
            self.assertIn("CH18=0", title)
            self.assertIn("ATKEX18=0", title)
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
