import os
import subprocess
import time
import unittest
from pathlib import Path

from tools.map_loader import LoadedMap, Sector
from tools import emit_source_stage13_things_sprites_and_real_frame_setup as stage13
from tools import emit_source_stage14_game_loop_input_collision as stage14
from tools import emit_source_stage16_active_monster_thinkers_and_targeting as stage16
from tools import emit_source_stage29_selected_monster_chase_attack_state_loop as stage


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


def _active_mobj(
    info: stage16.Stage16InfoTables,
    *,
    index: int = 0,
    type_name: str = "MT_SHOTGUY",
    state_name: str = "S_SPOS_PAIN",
    x: int = 0,
    y: int = 0,
    momx: int = 0,
    momy: int = 0,
    tics: int | None = None,
    target_index: int | None = 1,
    threshold: int = stage.stage18.BASETHRESHOLD,
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
        movedir=stage.stage18.DI_NODIR,
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
        sector=active.sector,
        subsector=active.subsector,
        player_index=-1,
        reactiontime=active.reactiontime,
        state_name=active.type_name,
    )


def _target(
    index: int = 1,
    *,
    x: int = 256 * stage.FRACUNIT,
    y: int = 0,
    flags: int | None = None,
) -> stage16.ActiveMobj:
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


def _stage29_world(
    *,
    actor: stage16.ActiveMobj | None = None,
    targets: dict[int, stage16.ActiveMobj] | None = None,
) -> stage.Stage29World:
    info = stage16.parse_stage16_info_tables()
    if actor is None:
        actor = _active_mobj(info)
    blockmap = stage14.BlockMap(
        origin_x=-128 * stage.FRACUNIT,
        origin_y=-128 * stage.FRACUNIT,
        width=4,
        height=4,
        shorts=(),
        offsets=(0,) * 16,
        lists=((),) * 16,
    )
    sectors = [stage14.MovementSector(0, 0, 128 * stage.FRACUNIT)]
    loaded = LoadedMap(
        name="SYN",
        source="synthetic",
        vertices=(),
        linedefs=(),
        sidedefs=(),
        sectors=(Sector(0, 128, "FLOOR", "CEIL", 160, 0, 0),),
        things=(),
    )
    movement = stage14.MovementWorld(
        loaded=loaded,
        geometry=stage13.MapGeometry((), (), (), ()),
        blockmap=blockmap,
        sectors=sectors,
        lines=[],
        mobjs=[_movement_mobj_from_active(actor)],
        player=stage14.MovementPlayer(0, 0, stage14.TicCmd(), 41 * stage.FRACUNIT),
        blocklinks=[None] * blockmap.block_count,
        sectorlinks=[None],
        iterator=stage14.BlockIteratorState(),
        counters=stage14.MovementCounters(),
    )
    for mobj in movement.mobjs:
        stage14.p_set_thing_position_source_shape(movement, mobj)
    movement.counters = stage14.MovementCounters()
    counters = stage.Stage29Counters()
    monster = stage.stage18.Stage18World(
        movement=movement,
        info=info,
        actor=actor,
        targets={1: _target()} if targets is None else targets,
        counters=counters,
        rng=stage16.DoomRandom(0),
        execute_chase_actions=True,
    )
    return stage.Stage29World(monster=monster, counters=counters)


class SourceStage29SelectedMonsterChaseAttackStateLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.info = stage16.parse_stage16_info_tables()

    def test_source_trace_labels_name_stage29_source_ordered_loop(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("G_Ticker_stage29_selected_monster_replay_source_shape_debug", labels)
        self.assertIn("P_PlayerThink_MovePsprites_stage29_selected_route_source_shape_debug", labels)
        self.assertIn("P_Ticker_RunThinkers_MobjThinker_stage29_source_shape_debug", labels)
        self.assertIn("A_Chase_stage29_selected_attack_decision_boundary_debug", labels)

    def test_synthetic_selected_mobj_state_transition_is_logged(self) -> None:
        actor = _active_mobj(self.info, state_name="S_SPOS_PAIN", tics=1, momx=0, momy=0)
        world = _stage29_world(actor=actor)

        stage.g_ticker_stage29_selected_monster_replay_source_shape(world)

        self.assertEqual(stage._state_name(self.info, actor.state), "S_SPOS_PAIN2")
        self.assertEqual(actor.tics, 3)
        self.assertEqual(len(world.log), 1)
        self.assertEqual(world.log[0].state_name, "S_SPOS_PAIN2")
        self.assertEqual((world.counters.mobj_state_sets, world.counters.mobj_state_transitions), (1, 1))

    def test_synthetic_thinker_ordering_counts_one_selected_mobj(self) -> None:
        world = _stage29_world()

        stage.g_ticker_stage29_selected_monster_replay_source_shape(world)

        self.assertEqual(world.counters.g_ticker_calls, 1)
        self.assertEqual(world.counters.player_think_calls, 1)
        self.assertEqual(world.counters.move_psprites_calls, 1)
        self.assertEqual(world.counters.p_ticker_calls, 1)
        self.assertEqual(world.counters.run_thinkers_calls, 1)
        self.assertEqual(world.counters.thinker_function_calls, 1)
        self.assertEqual(world.counters.mobj_thinker_calls, 1)

    def test_synthetic_target_retention_and_chase_action_dispatch_boundary(self) -> None:
        actor = _active_mobj(self.info, state_name="S_SPOS_RUN1", tics=1, target_index=1)
        actor.flags |= stage13.MF_JUSTHIT
        world = _stage29_world(actor=actor)

        stage.g_ticker_stage29_selected_monster_replay_source_shape(world)

        self.assertEqual(world.counters.target_retained_tics, 1)
        self.assertEqual(world.counters.chase_reached, 1)
        self.assertEqual(world.counters.chase_calls, 1)
        self.assertEqual(world.counters.missile_range_checks, 1)
        self.assertEqual(world.counters.attack_state_deferrals, 1)
        self.assertEqual(world.counters.final_attack_boundary, 1)
        self.assertEqual(world.counters.attack_actions_executed, 0)

    def test_synthetic_selected_boundary_excludes_damage_death_and_drop(self) -> None:
        actor = _active_mobj(self.info, state_name="S_SPOS_RUN1", tics=1, target_index=1)
        actor.flags |= stage13.MF_JUSTHIT
        world = _stage29_world(actor=actor)

        stage.run_stage29_selected_monster_loop_source_shape(world)

        self.assertEqual(world.counters.selected_damage_events, 0)
        self.assertEqual(world.counters.selected_death_events, 0)
        self.assertEqual(world.counters.selected_drop_events, 0)
        self.assertEqual(actor.health, self.info.by_name["MT_SHOTGUY"].spawnhealth)

    def test_absence_flags_keep_broad_systems_deferred_and_stage30_out(self) -> None:
        ref = stage.reference_selected_monster_chase_attack_state_loop_for_pinned_map(PINNED_WAD)
        counters = ref.counters
        image = stage.build_source_stage29_selected_monster_chase_attack_state_loop_exe()

        self.assertEqual(counters.broad_ai_absent, 1)
        self.assertEqual(counters.projectiles_absent, 1)
        self.assertEqual(counters.infighting_absent, 1)
        self.assertEqual(counters.generalized_combat_absent, 1)
        self.assertEqual(counters.pickups_absent, 1)
        self.assertEqual(counters.exits_absent, 1)
        self.assertEqual(counters.map_progression_absent, 1)
        self.assertEqual(counters.real_audio_absent, 1)
        self.assertEqual(counters.runtime_rendered_motion_deferred, 1)
        self.assertNotIn(b"source_stage30", image.lower())

    def test_pinned_real_map_replay_changes_selected_monster_over_multiple_tics(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_selected_monster_chase_attack_state_loop_for_pinned_map(PINNED_WAD)
        final = ref.final_mobj
        log_text = stage._stage29_log_text(ref.log)

        self.assertEqual(ref.stage28.signature, 2805406010)
        self.assertEqual(ref.stage18_ref.signature, 1615679087)
        self.assertEqual(ref.signature, 3738922932)
        self.assertEqual(ref.boundary, "ATTACK_DECISION")
        self.assertEqual(len(ref.log), 6)
        self.assertEqual([record.state_name for record in ref.log], [
            "S_SPOS_PAIN",
            "S_SPOS_PAIN",
            "S_SPOS_PAIN2",
            "S_SPOS_PAIN2",
            "S_SPOS_PAIN2",
            "S_SPOS_RUN1",
        ])
        self.assertEqual((final.x >> stage.FRACBITS, final.y >> stage.FRACBITS), (1750, -942))
        self.assertEqual((final.momx, final.momy), (-12291, -43689))
        self.assertEqual((final.target_index, final.health, final.threshold), (0, 20, 99))
        self.assertEqual((stage._state_name(self.info, final.state), final.state, final.tics), ("S_SPOS_RUN1", 209, 3))
        self.assertEqual((ref.counters.g_ticker_calls, ref.counters.p_ticker_calls, ref.counters.mobj_thinker_calls), (6, 6, 6))
        self.assertEqual((ref.counters.chase_reached, ref.counters.chase_calls, ref.counters.attack_state_deferrals), (1, 1, 1))
        self.assertEqual((ref.movement_counters.try_move_calls, ref.movement_counters.accepted_moves, ref.movement_counters.line_checks), (6, 6, 48))
        self.assertIn("1:S_SPOS_PAIN:T2:XY1751,-938", log_text)
        self.assertIn("6:S_SPOS_RUN1:T3:XY1750,-942", log_text)

    def test_preserves_stage28_through_stage19_signatures(self) -> None:
        ref = stage.reference_selected_monster_chase_attack_state_loop_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.stage28.signature, 2805406010)
        self.assertEqual(ref.stage28.stage27.signature, 1735738182)
        self.assertEqual(ref.stage28.stage27.stage26.signature, 132405987)
        self.assertEqual(ref.stage28.stage27.stage26.stage25.signature, 1688844032)
        self.assertEqual(ref.stage28.stage27.stage26.stage25.stage24.signature, 1919312263)
        self.assertEqual(ref.stage28.stage27.stage26.stage25.stage24.stage23.signature, 3216085132)
        self.assertEqual(ref.stage28.stage27.stage26.stage25.stage24.stage23.stage22.signature, 2207028069)
        self.assertEqual(ref.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.signature, 1770773845)
        self.assertEqual(ref.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.signature, 3226031347)
        self.assertEqual(ref.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature, 2088411722)

    def test_executable_build_contains_stage29_log_signature_and_absences(self) -> None:
        ref = stage.reference_selected_monster_chase_attack_state_loop_for_pinned_map(PINNED_WAD)
        image = stage.build_source_stage29_selected_monster_chase_attack_state_loop_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage29_selected_monster_chase_attack_state_loop", image)
        self.assertIn(b"Selected monster chase/attack state loop proof OK", image)
        self.assertIn(b"P_PlayerThink/P_MovePsprites, P_Ticker, P_RunThinkers, and P_MobjThinker", image)
        self.assertIn(b" S28SIG=", image)
        self.assertIn(b" S29SIG=", image)
        self.assertIn(str(ref.signature).encode("ascii"), image)
        self.assertIn(stage._stage29_log_text(ref.log).encode("ascii"), image)
        self.assertIn(b" S30ABS=1", image)
        self.assertNotIn(b"source_stage30", image.lower())
        for forbidden in (
            b"projectile spawned",
            b"explosion",
            b"gcc:",
            b"mingw",
            b"microsoft visual c",
        ):
            self.assertNotIn(forbidden, image.lower())

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage29_markers_log_and_preserved_baselines(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_selected_monster_chase_attack_state_loop_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage29_selected_monster_chase_attack_state_loop.exe"
        stage.write_source_stage29_selected_monster_chase_attack_state_loop_exe(exe_path)

        expected = (
            "STEP29=6",
            "TIC29=6",
            "ST29=S_SPOS_RUN1",
            "AB29=1",
            f"S29SIG={ref.signature}",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected, timeout_seconds=8.0)
            self.assertIn(f"S28SIG={ref.stage28.signature}", title)
            self.assertIn(f"S27SIG={ref.stage28.stage27.signature}", title)
            self.assertIn(f"S26SIG={ref.stage28.stage27.stage26.signature}", title)
            self.assertIn(f"S25SIG={ref.stage28.stage27.stage26.stage25.signature}", title)
            self.assertIn(f"S24SIG={ref.stage28.stage27.stage26.stage25.stage24.signature}", title)
            self.assertIn(f"S23SIG={ref.stage28.stage27.stage26.stage25.stage24.stage23.signature}", title)
            self.assertIn(f"S22SIG={ref.stage28.stage27.stage26.stage25.stage24.stage23.stage22.signature}", title)
            self.assertIn(f"S21SIG={ref.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.signature}", title)
            self.assertIn(f"S20SIG={ref.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.signature}", title)
            self.assertIn(f"S19SIG={ref.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature}", title)
            self.assertIn("BOUND29=ATTACK_DECISION", title)
            self.assertIn("LOG29=1:S_SPOS_PAIN>6:S_SPOS_RUN1", title)
            self.assertIn("S30ABS=1", title)
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
