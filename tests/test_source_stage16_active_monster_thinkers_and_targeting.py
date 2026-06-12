import os
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage13_things_sprites_and_real_frame_setup as stage13
from tools import emit_source_stage16_active_monster_thinkers_and_targeting as stage


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


def _target() -> stage.ActivePlayerTarget:
    return stage.ActivePlayerTarget(
        player_index=0,
        mo_index=0,
        x=64 * stage.FRACUNIT,
        y=0,
        z=0,
        sector=0,
        subsector=0,
        health=100,
        flags=stage13.MF_SOLID | stage13.MF_SHOOTABLE,
        radius=16 * stage.FRACUNIT,
        height=56 * stage.FRACUNIT,
    )


def _active_mobj(
    info: stage.Stage16InfoTables,
    *,
    index: int = 1,
    type_name: str = "MT_SHOTGUY",
    state_name: str = "S_SPOS_STND",
    tics: int = 1,
    lastlook: int = 0,
) -> stage.ActiveMobj:
    minfo = info.by_name[type_name]
    state = info.state_info.state_index[state_name]
    st = info.state_info.states[state]
    return stage.ActiveMobj(
        index=index,
        mapthing_index=index,
        type_name=type_name,
        doomednum=minfo.doomednum,
        x=0,
        y=0,
        z=0,
        angle=0,
        momx=0,
        momy=0,
        momz=0,
        radius=minfo.radius,
        height=minfo.height,
        flags=minfo.flags,
        floorz=0,
        ceilingz=128 * stage.FRACUNIT,
        subsector=0,
        sector=0,
        health=minfo.spawnhealth,
        reactiontime=minfo.reactiontime,
        state=state,
        tics=tics,
        sprite=st.sprite,
        frame=st.frame,
        lastlook=lastlook,
    )


def _world(
    info: stage.Stage16InfoTables,
    *,
    thinkers: stage.ThinkerList | None = None,
    mobjs: list[stage.ActiveMobj] | None = None,
    players: list[stage.ActivePlayerTarget] | None = None,
    playeringame: list[bool] | None = None,
    counters: stage.Stage16Counters | None = None,
    sight_overrides: dict[tuple[int, int], stage.SightProbeResult] | None = None,
) -> stage.Stage16World:
    if counters is None:
        counters = stage.Stage16Counters()
    if thinkers is None:
        thinkers = stage.p_init_thinkers_source_shape(counters)
    if mobjs is None:
        mobjs = []
    if players is None:
        players = [_target()]
    if playeringame is None:
        playeringame = [True, False, False, False]
    return stage.Stage16World(
        loaded=None,
        geometry=None,
        rejectmatrix=b"",
        info=info,
        thinkers=thinkers,
        mobjs=mobjs,
        players=players,
        playeringame=playeringame,
        counters=counters,
        sight_overrides=sight_overrides,
    )


class SourceStage16ActiveMonsterThinkersTargetingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.info = stage.parse_stage16_info_tables()

    def test_source_trace_covers_stage16_active_monster_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("P_SetupLevel_active_monster_census_source_shape_debug", labels)
        self.assertIn("P_ThinkerList_active_monster_source_shape_debug", labels)
        self.assertIn("P_SpawnMobj_active_monster_source_shape_debug", labels)
        self.assertIn("P_MobjThinker_SetMobjState_source_shape_debug", labels)
        self.assertIn("A_Look_P_LookForPlayers_source_shape_debug", labels)
        self.assertIn("P_CheckSight_bounded_source_shape_debug", labels)
        self.assertIn("A_Chase_deferred_active_monster_boundary_debug", labels)

    def test_synthetic_thinker_list_add_deferred_remove_and_mutation_while_iterating(self) -> None:
        counters = stage.Stage16Counters()
        thinkers = stage.p_init_thinkers_source_shape(counters)
        stage.p_add_thinker_source_shape(thinkers, stage.ThinkerNode("A", "tick"), counters)
        stage.p_add_thinker_source_shape(thinkers, stage.ThinkerNode("B", "tick"), counters)
        world = _world(self.info, thinkers=thinkers, counters=counters)
        visited: list[str] = []

        def callback(run_world: stage.Stage16World, node: stage.ThinkerNode) -> None:
            visited.append(node.name)
            if node.name == "A":
                stage.p_add_thinker_source_shape(
                    run_world.thinkers,
                    stage.ThinkerNode("C", "tick"),
                    run_world.counters,
                )
                run_world.counters.thinker_mutation_adds += 1
                stage.p_remove_thinker_source_shape(run_world.thinkers, "B", run_world.counters)

        stage.p_run_thinkers_source_shape(world, callback)

        self.assertEqual(visited, ["A", "C"])
        self.assertEqual(stage.thinker_names_source_shape(thinkers), ("A", "C"))
        self.assertEqual(
            (
                counters.thinker_init_calls,
                counters.thinker_adds,
                counters.thinker_deferred_removes,
                counters.thinker_actual_removes,
                counters.thinker_mutation_adds,
            ),
            (1, 3, 1, 1, 1),
        )

    def test_synthetic_p_set_mobj_state_mobj_thinker_null_removal_and_action_deferral(self) -> None:
        counters = stage.Stage16Counters()
        thinkers = stage.p_init_thinkers_source_shape(counters)
        actor = _active_mobj(self.info, index=1, state_name="S_SPOS_RUN1", tics=1)
        stage.p_add_thinker_source_shape(
            thinkers,
            stage.ThinkerNode("mobj_1", "P_MobjThinker", mobj_index=0),
            counters,
        )
        world = _world(self.info, thinkers=thinkers, mobjs=[actor], counters=counters)

        stage.p_mobj_thinker_source_shape(world, actor)

        self.assertEqual(stage._state_name(self.info, actor.state), "S_SPOS_RUN2")
        self.assertEqual(actor.tics, 3)
        self.assertEqual((counters.mobj_thinker_calls, counters.chase_deferred), (1, 1))
        self.assertEqual((counters.action_dispatches, counters.action_deferrals), (1, 1))

        self.assertFalse(stage.p_set_mobj_state_source_shape(world, actor, stage.S_NULL))
        self.assertTrue(actor.removed)
        self.assertEqual(counters.mobj_null_removals, 1)
        self.assertEqual(world.thinkers.nodes["mobj_1"].function, stage.ACTION_REMOVE)

    def test_synthetic_a_look_and_p_look_for_players_target_acquisition(self) -> None:
        actor = _active_mobj(self.info, state_name="S_SPOS_STND", tics=10, lastlook=1)
        world = _world(
            self.info,
            mobjs=[actor],
            sight_overrides={(actor.index, 0): stage.SightProbeResult(visible=True, bsp_accept=1)},
        )

        stage.a_look_source_shape(world, actor)
        self.assertIsNone(actor.target_index)
        self.assertEqual((actor.lastlook, world.counters.a_look_calls), (0, 1))

        stage.a_look_source_shape(world, actor)
        self.assertEqual(actor.target_index, 0)
        self.assertEqual(stage._state_name(self.info, actor.state), "S_SPOS_RUN1")
        self.assertEqual(
            (
                world.counters.a_look_calls,
                world.counters.look_for_players_calls,
                world.counters.look_iterations,
                world.counters.sight_checks,
                world.counters.target_acquired,
                world.counters.chase_deferred,
            ),
            (2, 2, 5, 1, 1, 1),
        )

    def test_synthetic_p_check_sight_override_and_bounded_no_bsp_accept(self) -> None:
        actor = _active_mobj(self.info)
        blocked = _world(
            self.info,
            mobjs=[actor],
            sight_overrides={(actor.index, 0): stage.SightProbeResult(visible=False, reject_blocked=1)},
        )
        self.assertFalse(stage.p_check_sight_source_shape(blocked, actor, blocked.players[0]).visible)
        self.assertEqual(blocked.counters.sight_reject_matrix_blocks, 1)

        open_world = _world(self.info, mobjs=[actor])
        self.assertTrue(stage.p_check_sight_source_shape(open_world, actor, open_world.players[0]).visible)
        self.assertEqual(open_world.counters.sight_bsp_accepts, 1)

    def test_pinned_map_active_monster_reference_identity_targeting_and_signature(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_active_monster_thinkers_and_targeting_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.stage15.stage14.stage13.draw.framebuffer_signature, 2904743961)
        self.assertEqual(ref.stage15.stage14.signature, 3925602456)
        self.assertEqual(ref.stage15.signature, 2810145191)
        self.assertEqual(ref.monster_count, 18)

        selected = ref.selected
        self.assertEqual(stage.DEFAULT_ACTIVE_MONSTER_MAPTHING_INDEX, 37)
        self.assertEqual((selected.mapthing_index, selected.mobj_index, selected.type_name), (37, 28, "MT_SHOTGUY"))
        self.assertEqual((selected.doomednum, selected.x >> stage.FRACBITS, selected.y >> stage.FRACBITS), (9, 1752, -936))
        self.assertEqual((selected.sector, selected.subsector, selected.block_x, selected.block_y), (58, 620, 15, 6))
        self.assertEqual((selected.spawn_state_name, selected.spawn_state, selected.spawn_tics), ("S_SPOS_STND", 207, 3))
        self.assertEqual((selected.raw_spawn_tics, selected.spawn_lastlook, selected.distance_to_player), (10, 1, 292))
        self.assertEqual((selected.front_arc, selected.sight.visible), (1, True))
        self.assertEqual((selected.sight.nodes, selected.sight.subsectors, selected.sight.segs, selected.sight.crossed_lines), (77, 28, 69, 5))

        self.assertEqual((ref.target.x >> stage.FRACBITS, ref.target.y >> stage.FRACBITS), (1824, -680))
        self.assertEqual((ref.target.sector, ref.target.subsector), (196, 633))
        self.assertEqual(len(ref.trace), 13)
        self.assertEqual((ref.trace[2].tic, ref.trace[2].state_name, ref.trace[2].target_index), (3, "S_SPOS_STND2", -1))
        self.assertEqual((ref.trace[-1].tic, ref.trace[-1].state_name, ref.trace[-1].target_index), (13, "S_SPOS_RUN1", 0))

        self.assertEqual(stage._state_name(self.info, ref.final_mobj.state), "S_SPOS_RUN1")
        self.assertEqual((ref.final_mobj.tics, ref.final_mobj.target_index), (3, 0))
        self.assertEqual(
            (
                ref.counters.thinker_adds,
                ref.counters.p_ticker_calls,
                ref.counters.mobj_thinker_calls,
                ref.counters.mobj_state_sets,
                ref.counters.action_dispatches,
                ref.counters.a_look_calls,
                ref.counters.look_for_players_calls,
                ref.counters.look_iterations,
                ref.counters.sight_checks,
                ref.counters.target_acquired,
                ref.counters.chase_deferred,
                ref.counters.sound_deferred,
                ref.counters.attacks_deferred,
                ref.counters.damage_events,
                ref.counters.kills,
            ),
            (1, 13, 13, 3, 3, 2, 2, 5, 1, 1, 1, 1, 0, 0, 0),
        )
        self.assertEqual(ref.signature, 249707937)

    def test_executable_build_contains_stage16_status_preserves_stage15_and_omits_deferred_system_strings(self) -> None:
        image = stage.build_source_stage16_active_monster_thinkers_and_targeting_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage16_active_monster_thinkers_and_targeting", image)
        self.assertIn(b"Active monster thinker and targeting OK", image)
        self.assertIn(b"P_InitThinkers", image)
        self.assertIn(b"P_AddThinker", image)
        self.assertIn(b"P_MobjThinker", image)
        self.assertIn(b"P_SetMobjState", image)
        self.assertIn(b"A_Look", image)
        self.assertIn(b"P_LookForPlayers", image)
        self.assertIn(b"P_CheckSight", image)
        self.assertIn(b" S15SIG=", image)
        self.assertIn(b" MCENS=", image)
        self.assertIn(b" MT16=", image)
        self.assertIn(b" S16SIG=", image)
        self.assertNotIn(b"source_stage17", lower)
        for forbidden in (
            b"p_damagemobj",
            b"p_killmobj",
            b"item drops",
            b"doors",
            b"switches",
            b"sound playback",
            b"automap",
            b"menus",
            b"save/load",
            b"networking",
            b"live keyboard",
            b"gcc:",
            b"mingw",
            b"microsoft visual c",
        ):
            self.assertNotIn(forbidden, lower)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage16_active_monster_and_preserved_stage15(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_active_monster_thinkers_and_targeting_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage16_active_monster_thinkers_and_targeting.exe"
        stage.write_source_stage16_active_monster_thinkers_and_targeting_exe(exe_path)

        expected = (
            f"S14SIG={ref.stage15.stage14.signature}",
            f"S15SIG={ref.stage15.signature}",
            f"MCENS={ref.monster_count}",
            f"MT16={ref.selected.mapthing_index}",
            f"MO16={ref.selected.mobj_index}",
            f"TGT={ref.counters.target_acquired}",
            f"S16SIG={ref.signature}",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn(f"P1={ref.stage15.pickups[0].mapthing_index}", title)
            self.assertIn(f"P2={ref.stage15.pickups[1].mapthing_index}", title)
            self.assertIn(f"CLIP={ref.stage15.player.ammo[stage.stage15.AM_CLIP]}", title)
            self.assertIn(f"SHELL={ref.stage15.player.ammo[stage.stage15.AM_SHELL]}", title)
            self.assertIn(f"M16N={ref.selected.type_name[3:]}", title)
            self.assertIn(f"LOOK={ref.counters.a_look_calls}", title)
            self.assertIn(f"SIGHT={ref.counters.sight_checks}", title)
            self.assertIn(f"STFN={stage._state_name(self.info, ref.final_mobj.state)}", title)
            self.assertIn(f"CHDEF={ref.counters.chase_deferred}", title)
            self.assertIn("ATK=0", title)
            self.assertIn("DMG=0", title)
            self.assertIn("KILL=0", title)
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
