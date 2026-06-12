import os
import subprocess
import time
import unittest
from pathlib import Path

from tools.map_loader import LineDef, LoadedMap, Sector, SideDef, Thing, Vertex
from tools import emit_source_stage13_things_sprites_and_real_frame_setup as stage13
from tools import emit_source_stage14_game_loop_input_collision as stage14
from tools import emit_source_stage15_pickups_psprites_statusbar_shell as stage15
from tools import emit_source_stage16_active_monster_thinkers_and_targeting as stage16
from tools import emit_source_stage17_first_weapon_fire_damage_and_death_probe as stage


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


def _loaded_map(line_count: int = 0) -> LoadedMap:
    vertices = (
        Vertex(-1024, -1024),
        Vertex(1024, -1024),
        Vertex(1024, 1024),
        Vertex(-1024, 1024),
        Vertex(128, -128),
        Vertex(128, 128),
    )
    linedefs = []
    if line_count:
        linedefs.append(LineDef(4, 5, 0, 0, 0, 0, -1))
    return LoadedMap(
        name="MAP01",
        source="synthetic",
        vertices=vertices,
        linedefs=tuple(linedefs),
        sidedefs=(SideDef(0, 0, "-", "-", "-", 0),),
        sectors=(Sector(0, 128, "FLAT1", "FLAT2", 160, 0, 0),),
        things=(Thing(0, 0, 0, 1, 7),),
    )


def _movement_line(index: int = 0) -> stage14.MovementLine:
    return stage14.MovementLine(
        index=index,
        v1x=128 * stage.FRACUNIT,
        v1y=-128 * stage.FRACUNIT,
        v2x=128 * stage.FRACUNIT,
        v2y=128 * stage.FRACUNIT,
        dx=0,
        dy=256 * stage.FRACUNIT,
        bbox=(
            -128 * stage.FRACUNIT,
            128 * stage.FRACUNIT,
            128 * stage.FRACUNIT,
            128 * stage.FRACUNIT,
        ),
        slopetype=stage14.ST_VERTICAL,
        flags=0,
        special=0,
        frontsector=0,
        backsector=None,
    )


def _active_mobj(
    info: stage16.Stage16InfoTables,
    *,
    index: int,
    mapthing_index: int,
    type_name: str,
    x: int,
    y: int,
    angle: int = 0,
    health: int | None = None,
    state_name: str | None = None,
) -> stage16.ActiveMobj:
    minfo = info.by_name[type_name]
    state = minfo.spawnstate if state_name is None else info.state_info.state_index[state_name]
    st = info.state_info.states[state]
    return stage16.ActiveMobj(
        index=index,
        mapthing_index=mapthing_index,
        type_name=type_name,
        doomednum=minfo.doomednum,
        x=x,
        y=y,
        z=0,
        angle=angle,
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
        health=minfo.spawnhealth if health is None else health,
        reactiontime=minfo.reactiontime,
        state=state,
        tics=st.tics,
        sprite=st.sprite,
        frame=st.frame,
        lastlook=0,
    )


def _movement_mobj_from_active(
    mobj: stage16.ActiveMobj,
    *,
    player_index: int = -1,
    bnext: int | None = None,
) -> stage14.MovementMobj:
    return stage14.MovementMobj(
        index=mobj.index,
        mapthing_index=mobj.mapthing_index,
        type_name=mobj.type_name,
        doomednum=mobj.doomednum,
        x=mobj.x,
        y=mobj.y,
        z=mobj.z,
        angle=mobj.angle,
        momx=mobj.momx,
        momy=mobj.momy,
        momz=mobj.momz,
        radius=mobj.radius,
        height=mobj.height,
        flags=mobj.flags,
        floorz=mobj.floorz,
        ceilingz=mobj.ceilingz,
        subsector=mobj.subsector,
        sector=mobj.sector,
        player_index=player_index,
        reactiontime=mobj.reactiontime,
        state_name=mobj.type_name,
        bnext=bnext,
    )


def _synthetic_world(*, with_wall: bool = False, target_y: int = 0, target_health: int = 30) -> stage.Stage17AttackWorld:
    info = stage16.parse_stage16_info_tables()
    player_mobj = _active_mobj(
        info,
        index=0,
        mapthing_index=0,
        type_name="MT_PLAYER",
        x=0,
        y=0,
        angle=0,
        health=100,
    )
    target = _active_mobj(
        info,
        index=1,
        mapthing_index=1,
        type_name="MT_SHOTGUY",
        x=256 * stage.FRACUNIT,
        y=target_y,
        angle=(stage.ANG90 * 2) & 0xFFFFFFFF,
        health=target_health,
        state_name="S_SPOS_RUN1",
    )
    loaded = _loaded_map(line_count=1 if with_wall else 0)
    blockmap = stage14.BlockMap(
        origin_x=-1024 * stage.FRACUNIT,
        origin_y=-1024 * stage.FRACUNIT,
        width=16,
        height=16,
        shorts=(),
        offsets=(),
        lists=tuple(((0,) if with_wall else ()) for _ in range(16 * 16)),
    )
    blocklinks = [None] * blockmap.block_count
    center = stage14._block_index(blockmap, 8, 8)
    target_block = stage14._block_index(blockmap, 10, 8 if target_y == 0 else 9)
    blocklinks[center] = 0
    blocklinks[target_block] = 1
    movement = stage14.MovementWorld(
        loaded=loaded,
        geometry=stage13.MapGeometry((), (), (), ()),
        blockmap=blockmap,
        sectors=[stage14.MovementSector(0, 0, 128 * stage.FRACUNIT)],
        lines=[_movement_line()] if with_wall else [],
        mobjs=[
            _movement_mobj_from_active(
                player_mobj,
                player_index=0,
                bnext=1 if target_block == center else None,
            ),
            _movement_mobj_from_active(target),
        ],
        player=stage14.MovementPlayer(0, 0, stage14.TicCmd(), stage14.VIEWHEIGHT),
        blocklinks=blocklinks,
        sectorlinks=[None],
        iterator=stage14.BlockIteratorState(),
        counters=stage14.MovementCounters(),
    )
    player = stage15.Stage15Player(mo_index=0)
    assert player.weaponowned is not None
    assert player.ammo is not None
    assert player.psprites is not None
    player.readyweapon = stage15.WP_SHOTGUN
    player.pendingweapon = stage15.WP_NOCHANGE
    player.weaponowned[stage15.WP_SHOTGUN] = True
    player.ammo[stage15.AM_SHELL] = 2
    player.attackdown = False
    player.psprites[stage15.PS_WEAPON] = stage15.PspDef(
        state=info.state_info.state_index["S_SGUN"],
        tics=1,
        sx=stage15.WEAPONBOTTOM,
        sy=stage15.WEAPONBOTTOM,
    )
    return stage.Stage17AttackWorld(
        movement=movement,
        info=info,
        player=player,
        weaponinfo=stage15.build_weaponinfo_source_shape(info.state_info),
        mobjs={0: player_mobj, 1: target},
        counters=stage.Stage17Counters(),
        rng=stage16.DoomRandom(0),
        selected_index=1,
    )


class SourceStage17FirstWeaponFireTests(unittest.TestCase):
    def setUp(self) -> None:
        self.info = stage16.parse_stage16_info_tables()

    def test_source_trace_labels_name_the_bounded_weapon_damage_route(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}
        self.assertIn("P_PlayerShotgunFire_first_damage_source_shape_debug", labels)
        self.assertIn("P_BulletSlope_GunShot_first_damage_source_shape_debug", labels)
        self.assertIn("P_AimLineAttack_LineAttack_bounded_source_shape_debug", labels)
        self.assertIn("P_DamageMobj_KillMobj_first_damage_source_shape_debug", labels)

    def test_synthetic_attack_census_records_bearing_current_miss_and_no_live_input(self) -> None:
        world = _synthetic_world(target_y=128 * stage.FRACUNIT)
        player = world.mobjs[0]
        target = world.mobjs[1]
        player.angle = 0
        current = stage.p_aim_line_attack_source_shape(world, player, player.angle, stage.BULLET_AIM_RANGE)
        selected_angle = stage.stage04.point_to_angle(target.x, target.y, player.x, player.y)
        selected = stage.p_aim_line_attack_source_shape(world, player, selected_angle, stage.BULLET_AIM_RANGE)

        self.assertEqual(stage.stage13.angle_to_degrees(selected_angle), 26)
        self.assertIsNone(current.target_index)
        self.assertEqual(selected.target_index, target.index)
        self.assertEqual(world.counters.no_live_input_dependency, 1)
        self.assertEqual((world.counters.aim_line_attacks, world.counters.aim_hits, world.counters.aim_misses), (2, 1, 1))

    def test_synthetic_ammo_fire_psprite_flash_and_deferrals(self) -> None:
        world = _synthetic_world()
        shooter = world.mobjs[0]

        shots = stage.a_weapon_ready_attack_stage17_source_shape(world, shooter)

        self.assertEqual(len(shots), 7)
        self.assertEqual(world.player.ammo[stage15.AM_SHELL], 1)
        self.assertEqual(world.counters.ammo_decrements, 1)
        self.assertEqual(world.counters.selected_fire_actions, 1)
        self.assertEqual(world.counters.flash_setups, 1)
        self.assertEqual(stage._state_name(self.info, world.player.psprites[stage15.PS_FLASH].state), "S_SGUNFLASH1")
        self.assertEqual(world.counters.unsupported_weapon_deferrals, 0)

        empty = _synthetic_world()
        empty.player.ammo[stage15.AM_SHELL] = 0
        self.assertFalse(stage.p_check_ammo_stage17_source_shape(empty))
        self.assertEqual(empty.counters.ammo_failures, 1)

    def test_synthetic_aim_and_line_attack_hit_miss_ordering_and_solid_line_block(self) -> None:
        hit_world = _synthetic_world()
        shooter = hit_world.mobjs[0]
        aim = stage.p_aim_line_attack_source_shape(hit_world, shooter, 0, stage.BULLET_AIM_RANGE)
        shot = stage.p_line_attack_source_shape(hit_world, shooter, 0, stage.BULLET_AIM_RANGE, aim.slope, 4, shot_index=1)

        self.assertEqual(aim.target_index, 1)
        self.assertEqual(shot.hit_mobj_index, 1)
        self.assertEqual(shot.target_health_after, 26)
        self.assertEqual((hit_world.counters.line_hits, hit_world.counters.shootable_thing_intercepts), (1, 2))
        self.assertGreaterEqual(hit_world.counters.traversed_intercepts, 2)

        miss_world = _synthetic_world(target_y=256 * stage.FRACUNIT)
        miss = stage.p_line_attack_source_shape(miss_world, miss_world.mobjs[0], 0, stage.BULLET_AIM_RANGE, 0, 4, shot_index=1)
        self.assertIsNone(miss.hit_mobj_index)
        self.assertEqual(miss_world.counters.line_misses, 1)

        blocked_world = _synthetic_world(with_wall=True)
        blocked = stage.p_line_attack_source_shape(
            blocked_world,
            blocked_world.mobjs[0],
            0,
            stage.BULLET_AIM_RANGE,
            0,
            4,
            shot_index=1,
        )
        self.assertIsNone(blocked.hit_mobj_index)
        self.assertEqual((blocked.blocked_by_line, blocked_world.counters.solid_line_blocks), (1, 1))

    def test_synthetic_damage_pain_death_and_drop_deferred_subset(self) -> None:
        world = _synthetic_world(target_health=30)
        shooter = world.mobjs[0]
        target = world.mobjs[1]
        stage.p_damage_mobj_source_shape(world, target, shooter, shooter, 5)

        self.assertEqual(target.health, 25)
        self.assertEqual(world.counters.damage_events, 1)
        self.assertEqual(world.counters.thrust_applications, 1)
        self.assertGreaterEqual(world.counters.pain_events, 0)

        lethal = _synthetic_world(target_health=10)
        stage.p_damage_mobj_source_shape(lethal, lethal.mobjs[1], lethal.mobjs[0], lethal.mobjs[0], 20)
        corpse = lethal.mobjs[1]
        self.assertLessEqual(corpse.health, 0)
        self.assertFalse(corpse.flags & stage13.MF_SHOOTABLE)
        self.assertEqual(stage._state_name(self.info, corpse.state), "S_SPOS_DIE1")
        self.assertEqual(lethal.player.killcount, 1)
        self.assertEqual((lethal.counters.kill_events, lethal.counters.death_state_sets, lethal.counters.drop_deferred), (1, 1, 1))
        self.assertEqual(lethal.counters.removal_deferred, 0)

    def test_pinned_map_first_damage_reference_preserves_stage16_and_mutates_selected_monster(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_first_weapon_fire_damage_and_death_probe_for_pinned_map(PINNED_WAD)
        counters = ref.counters

        self.assertEqual(ref.stage16.stage15.stage14.signature, 3925602456)
        self.assertEqual(ref.stage16.stage15.signature, 2810145191)
        self.assertEqual(ref.stage16.signature, 249707937)
        self.assertEqual((ref.stage16.selected.mapthing_index, ref.stage16.selected.mobj_index), (37, 28))
        self.assertEqual((ref.stage16.final_mobj.health, stage16._state_name(self.info, ref.stage16.final_mobj.state)), (30, "S_SPOS_RUN1"))

        self.assertEqual((ref.census.current_angle_degrees, ref.census.player_to_target_degrees), (0, 254))
        self.assertEqual((ref.census.target_to_player_degrees, ref.census.angle_delta_degrees), (74, 254))
        self.assertEqual((ref.census.current_angle_hits_selected, ref.census.selected_angle_blocked_by_line), (0, 1))
        self.assertEqual((ref.census.readyweapon_name, ref.census.shell_before, ref.census.target_health_before), ("SHOTGUN", 8, 30))
        self.assertEqual(ref.census.candidate_actions, ("A_FireShotgun", "A_FirePistol"))

        self.assertEqual((ref.shell_before, ref.shell_after), (8, 7))
        self.assertEqual((ref.health_before, ref.health_after), (30, 20))
        self.assertEqual((ref.final_target.index, ref.final_target.state, ref.final_target.tics), (28, 220, 3))
        self.assertEqual(stage._state_name(self.info, ref.final_target.state), "S_SPOS_PAIN")
        self.assertEqual((ref.weapon_state_name, ref.weapon_tics, ref.flash_state_name, ref.flash_tics), ("S_SGUN2", 7, "S_SGUNFLASH1", 3))
        self.assertEqual((ref.attack_angle_degrees, ref.bullet_slope, ref.random_start_index, ref.random_end_index), (254, 0, 178, 221))

        self.assertEqual((counters.gunshots, counters.line_hits, counters.line_misses), (7, 1, 6))
        self.assertEqual((counters.damage_events, counters.damage_total, counters.pain_events), (1, 10, 1))
        self.assertEqual((counters.kill_events, counters.death_state_sets, counters.drop_deferred, counters.removal_deferred), (0, 0, 0, 0))
        self.assertEqual((counters.monster_chase_moves, counters.doors_switches_deferred, counters.sector_specials_deferred), (0, 0, 0))
        self.assertEqual((counters.generalized_combat_deferred, counters.live_keyboard_deferred), (0, 0))
        self.assertEqual((ref.draw.status_pixels, ref.draw.weapon_pixels, ref.draw.signature), (12525, 2083, 3848018813))
        self.assertEqual(ref.signature, 2157381017)

    def test_executable_build_contains_stage17_status_preserves_baseline_and_omits_deferred_system_strings(self) -> None:
        image = stage.build_source_stage17_first_weapon_fire_damage_and_death_probe_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage17_first_weapon_fire_damage_and_death_probe", image)
        self.assertIn(b"First source-shaped weapon fire damage probe OK", image)
        self.assertIn(b"P_BulletSlope", image)
        self.assertIn(b"P_AimLineAttack", image)
        self.assertIn(b"P_LineAttack", image)
        self.assertIn(b"P_DamageMobj", image)
        self.assertIn(b" S14SIG=", image)
        self.assertIn(b" S15SIG=", image)
        self.assertIn(b" S16SIG=", image)
        self.assertIn(b" S17SIG=", image)
        self.assertIn(b" DMG17=", image)
        self.assertIn(b" H17=", image)
        self.assertNotIn(b"source_stage18", lower)
        for forbidden in (
            b"generalized combat",
            b"monster chase movement",
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
    def test_smoke_launch_reports_stage17_first_damage_and_preserved_stage16(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_first_weapon_fire_damage_and_death_probe_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage17_first_weapon_fire_damage_and_death_probe.exe"
        stage.write_source_stage17_first_weapon_fire_damage_and_death_probe_exe(exe_path)

        expected = (
            f"S14SIG={ref.stage16.stage15.stage14.signature}",
            f"S15SIG={ref.stage16.stage15.signature}",
            f"S16SIG={ref.stage16.signature}",
            f"S17SIG={ref.signature}",
            f"DMG17={ref.counters.damage_total}",
            f"H17={ref.health_after}",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn(f"MT16={ref.stage16.selected.mapthing_index}", title)
            self.assertIn(f"MO16={ref.stage16.selected.mobj_index}", title)
            self.assertIn(f"TGT={ref.stage16.counters.target_acquired}", title)
            self.assertIn(f"WACT={ref.census.selected_action}", title)
            self.assertIn(f"CANG={ref.census.current_angle_degrees}", title)
            self.assertIn(f"AANG={ref.attack_angle_degrees}", title)
            self.assertIn(f"CMISS={ref.counters.current_angle_misses}", title)
            self.assertIn(f"SH1={ref.shell_after}", title)
            self.assertIn(f"HIT17={ref.counters.line_hits}", title)
            self.assertIn(f"KILL17={ref.counters.kill_events}", title)
            self.assertIn(f"ST17N={stage._state_name(self.info, ref.final_target.state)}", title)
            self.assertIn("CHASEMV=0", title)
            self.assertIn("LIVEIN=0", title)
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
