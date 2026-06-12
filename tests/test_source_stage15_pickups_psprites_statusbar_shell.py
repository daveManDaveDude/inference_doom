import os
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage14_game_loop_input_collision as stage14
from tools import emit_source_stage15_pickups_psprites_statusbar_shell as stage
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


def _mobj(index: int, **kwargs) -> stage14.MovementMobj:
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
    return stage14.MovementMobj(index=index, **defaults)


def _movement_world(mobjs: tuple[stage14.MovementMobj, ...]) -> stage14.MovementWorld:
    loaded = LoadedMap(
        name="SYN",
        source="synthetic",
        vertices=(),
        linedefs=(),
        sidedefs=(),
        sectors=(Sector(0, 128, "FLOOR", "CEIL", 160, 0, 0),),
        things=(),
    )
    return stage14.MovementWorld(
        loaded=loaded,
        geometry=stage.stage13.MapGeometry((), (), (), ()),
        blockmap=stage14.BlockMap(
            origin_x=-128 * stage.FRACUNIT,
            origin_y=-128 * stage.FRACUNIT,
            width=1,
            height=1,
            shorts=(),
            offsets=(0,),
            lists=((),),
        ),
        sectors=[stage14.MovementSector(0, 0, 128 * stage.FRACUNIT)],
        lines=[],
        mobjs=list(mobjs),
        player=stage14.MovementPlayer(0, 0, stage14.TicCmd(), 41 * stage.FRACUNIT),
        blocklinks=[None],
        sectorlinks=[None],
        iterator=stage14.BlockIteratorState(),
        counters=stage14.MovementCounters(),
    )


class SourceStage15PickupsPspritesStatusbarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.info = stage.parse_stage15_info_tables()
        cls.weaponinfo = stage.build_weaponinfo_source_shape(cls.info)
        cls.doom = stage.stage13.parse_source_info_tables()

    def _world_for_special(
        self,
        sprite_name: str,
        *,
        player: stage.Stage15Player | None = None,
        special_flags: int | None = None,
        special_z: int = 0,
    ) -> stage.Stage15World:
        if special_flags is None:
            special_flags = stage.stage13.MF_SPECIAL
        toucher = _mobj(0, flags=stage.stage13.MF_SOLID | stage.stage13.MF_PICKUP)
        special = _mobj(
            1,
            type_name=f"MT_{sprite_name}",
            flags=special_flags,
            z=special_z,
            player_index=-1,
        )
        movement = _movement_world((toucher, special))
        if player is None:
            player = stage.g_player_reborn_source_shape(mo_index=0)
        sprite = self.info.sprnames.index(sprite_name) if sprite_name in self.info.sprnames else -1
        return stage.Stage15World(
            movement=movement,
            player=player,
            info=self.info,
            doom=self.doom,
            weaponinfo=self.weaponinfo,
            sprite_by_mobj_index={1: sprite},
            patch_by_sprite_frame={},
            counters=stage.Stage15Counters(),
        )

    def test_source_trace_covers_stage15_pickup_psprite_status_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("PIT_CheckThing_special_touch_source_shape_debug", labels)
        self.assertIn("P_TouchSpecialThing_inventory_source_shape_debug", labels)
        self.assertIn("P_GiveInventory_source_shape_debug", labels)
        self.assertIn("P_Psprites_source_shape_debug", labels)
        self.assertIn("ST_StatusWidget_source_shape_debug", labels)
        self.assertIn("V_DrawPatch_status_psprite_source_shape_debug", labels)
        self.assertIn("R_DrawPSprite_ready_weapon_shell_debug", labels)

    def test_synthetic_reborn_spawn_initial_inventory_psprites_and_stage14_fields(self) -> None:
        movement = _movement_world((_mobj(0, x=12 * stage.FRACUNIT, y=-3 * stage.FRACUNIT),))
        counters = stage.Stage15Counters()

        player = stage.p_spawn_player_inventory_psprite_source_shape(
            movement,
            self.info,
            self.weaponinfo,
            counters,
        )

        self.assertEqual((player.health, player.mo_health), (100, 100))
        self.assertEqual(player.ammo, [50, 0, 0, 0])
        self.assertEqual(player.maxammo, [200, 50, 300, 50])
        self.assertTrue(player.weaponowned[stage.WP_FIST])
        self.assertTrue(player.weaponowned[stage.WP_PISTOL])
        self.assertFalse(player.weaponowned[stage.WP_SHOTGUN])
        self.assertEqual((player.readyweapon, player.pendingweapon), (stage.WP_PISTOL, stage.WP_NOCHANGE))
        self.assertEqual((counters.psprite_setup_calls, counters.psprite_bringup_calls), (1, 1))
        self.assertIsNotNone(player.psprites[stage.PS_WEAPON].state)
        self.assertEqual((movement.mobjs[0].x >> stage.FRACBITS, movement.mobjs[0].y >> stage.FRACBITS), (12, -3))
        self.assertEqual(movement.player.viewheight, stage.VIEWHEIGHT)

    def test_synthetic_give_inventory_helpers_mutate_source_shaped_player(self) -> None:
        counters = stage.Stage15Counters()

        ammo_player = stage.g_player_reborn_source_shape()
        self.assertTrue(stage.p_give_ammo_source_shape(ammo_player, stage.AM_SHELL, 1, self.weaponinfo, counters))
        self.assertEqual(ammo_player.ammo[stage.AM_SHELL], 4)
        self.assertEqual(counters.ammo_grants, 1)

        weapon_player = stage.g_player_reborn_source_shape()
        self.assertTrue(
            stage.p_give_weapon_source_shape(
                weapon_player,
                stage.WP_SHOTGUN,
                False,
                self.weaponinfo,
                counters,
            )
        )
        self.assertTrue(weapon_player.weaponowned[stage.WP_SHOTGUN])
        self.assertEqual((weapon_player.ammo[stage.AM_SHELL], weapon_player.pendingweapon), (8, stage.WP_SHOTGUN))

        body_player = stage.g_player_reborn_source_shape()
        body_player.health = body_player.mo_health = 77
        self.assertTrue(stage.p_give_body_source_shape(body_player, 25, counters))
        self.assertEqual((body_player.health, body_player.mo_health), (100, 100))

        armor_player = stage.g_player_reborn_source_shape()
        self.assertTrue(stage.p_give_armor_source_shape(armor_player, 1, counters))
        self.assertEqual((armor_player.armorpoints, armor_player.armortype), (100, 1))

        card_player = stage.g_player_reborn_source_shape()
        self.assertTrue(stage.p_give_card_source_shape(card_player, stage.IT_BLUECARD, counters))
        self.assertTrue(card_player.cards[stage.IT_BLUECARD])
        self.assertEqual(card_player.bonuscount, stage.BONUSADD)

        power_player = stage.g_player_reborn_source_shape()
        self.assertTrue(stage.p_give_power_source_shape(power_player, stage.PW_INVISIBILITY, counters))
        self.assertEqual(power_player.powers[stage.PW_INVISIBILITY], stage.INVISTICS)

    def test_synthetic_touch_special_acceptance_rejection_unsupported_removal_and_deferred_accounting(self) -> None:
        accepted = self._world_for_special("CLIP")
        special = accepted.movement.mobjs[1]
        toucher = accepted.movement.mobjs[0]

        self.assertTrue(stage.p_touch_special_thing_source_shape(accepted, special, toucher))
        self.assertEqual(accepted.player.ammo[stage.AM_CLIP], 60)
        self.assertIn(1, accepted.removed_mobj_indexes)
        self.assertEqual(
            (
                accepted.counters.pickup_accepts,
                accepted.counters.removed_specials,
                accepted.counters.message_deferred,
                accepted.counters.sound_deferred,
                accepted.counters.item_respawn_deferred,
            ),
            (1, 1, 1, 1, 1),
        )

        full_player = stage.g_player_reborn_source_shape()
        full_player.ammo[stage.AM_CLIP] = full_player.maxammo[stage.AM_CLIP]
        rejected = self._world_for_special("CLIP", player=full_player)
        self.assertFalse(stage.p_touch_special_thing_source_shape(rejected, rejected.movement.mobjs[1], rejected.movement.mobjs[0]))
        self.assertEqual((rejected.counters.pickup_rejections, rejected.counters.removed_specials), (1, 0))

        unsupported = self._world_for_special("PLAY")
        self.assertFalse(stage.p_touch_special_thing_source_shape(unsupported, unsupported.movement.mobjs[1], unsupported.movement.mobjs[0]))
        self.assertEqual(unsupported.counters.unsupported_specials, 1)

        high = self._world_for_special("CLIP", special_z=96 * stage.FRACUNIT)
        self.assertFalse(stage.p_touch_special_thing_source_shape(high, high.movement.mobjs[1], high.movement.mobjs[0]))
        self.assertEqual(high.counters.pickup_out_of_reach, 1)

    def test_synthetic_pit_check_thing_special_branch_and_countitem(self) -> None:
        world = self._world_for_special("BON2", special_flags=stage.stage13.MF_SPECIAL | stage.stage13.MF_COUNTITEM)

        self.assertTrue(
            stage.pit_check_thing_special_touch_source_shape(
                world,
                world.movement.mobjs[0],
                world.movement.mobjs[1],
                world.movement.mobjs[1].x,
                world.movement.mobjs[1].y,
            )
        )
        self.assertEqual((world.counters.pickup_attempts, world.counters.pickup_accepts), (1, 1))
        self.assertEqual((world.player.armorpoints, world.player.armortype, world.player.itemcount), (1, 1, 1))

    def test_synthetic_psprites_setup_ready_pending_timer_and_no_fire_deferral(self) -> None:
        player = stage.g_player_reborn_source_shape()
        counters = stage.Stage15Counters()
        stage.p_setup_psprites_source_shape(player, self.info, self.weaponinfo, counters)

        self.assertEqual((counters.psprite_setup_calls, counters.psprite_bringup_calls), (1, 1))
        self.assertEqual(player.pendingweapon, stage.WP_NOCHANGE)
        for _ in range(20):
            stage.p_move_psprites_source_shape(player, self.info, self.weaponinfo, counters)
        weapon_psp = player.psprites[stage.PS_WEAPON]
        self.assertEqual(self.info.states[weapon_psp.state].name, "S_PISTOL")
        self.assertEqual((weapon_psp.sx, weapon_psp.sy), (stage.FRACUNIT, stage.WEAPONTOP))

        player.weaponowned[stage.WP_SHOTGUN] = True
        player.pendingweapon = stage.WP_SHOTGUN
        stage.a_weapon_ready_source_shape(player, self.info, self.weaponinfo, counters, weapon_psp)
        for _ in range(40):
            stage.p_move_psprites_source_shape(player, self.info, self.weaponinfo, counters)
        weapon_psp = player.psprites[stage.PS_WEAPON]
        self.assertEqual((player.readyweapon, player.pendingweapon), (stage.WP_SHOTGUN, stage.WP_NOCHANGE))
        self.assertEqual(self.info.states[weapon_psp.state].name, "S_SGUN")

        before = counters.psprite_no_fire_deferrals
        stage.p_set_psprite_source_shape(
            player,
            self.info,
            self.weaponinfo,
            counters,
            stage.PS_WEAPON,
            self.info.state_index["S_PISTOL2"],
        )
        self.assertGreater(counters.psprite_no_fire_deferrals, before)

    def test_pinned_status_widget_and_patch_blit_use_real_patch_columns(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_pickups_psprites_statusbar_shell_for_pinned_map(PINNED_WAD)
        status = next(command for command in ref.draw.commands if command.tier == "status")
        weapon = next(command for command in ref.draw.commands if command.tier == "weapon")

        self.assertEqual(ref.draw.first_status_patch, "STBAR")
        self.assertEqual((ref.draw.status_patch_draws, ref.draw.status_columns, ref.draw.status_pixels), (11, 469, 12533))
        self.assertEqual((ref.draw.weapon_patch_draws, ref.draw.weapon_columns, ref.draw.weapon_pixels), (1, 66, 2083))
        self.assertEqual((ref.draw.first_weapon_patch, ref.draw.weapon_state_name, ref.draw.weapon_sprite_name), ("SHTGA0", "S_SGUN", "SHTG"))
        self.assertEqual(len(ref.draw.column_sources[status.source_index]), stage.WALL_COLUMN_SOURCE_HEIGHT)
        self.assertEqual(len(ref.draw.column_sources[weapon.source_index]), stage.WALL_COLUMN_SOURCE_HEIGHT)

        colors, _ = stage.stage09.r_draw_column_pixels(
            ref.draw.column_sources[weapon.source_index],
            ref.stage14.stage13.stage12.palette32,
            yl=weapon.yl,
            yh=weapon.yh,
            iscale=weapon.iscale,
            texturemid=weapon.texturemid,
        )
        self.assertEqual(len(colors), weapon.yh - weapon.yl + 1)

    def test_pinned_map_pickup_probe_inventory_psprites_status_and_signatures(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_pickups_psprites_statusbar_shell_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.stage14.stage13.stage12.framebuffer_signature, 2853564869)
        self.assertEqual(ref.stage14.stage13.draw.framebuffer_signature, 2904743961)
        self.assertEqual(ref.stage14.signature, 3925602456)
        self.assertEqual((ref.stage14.blockmap.width, ref.stage14.blockmap.height, len(ref.stage14.script)), (20, 27, 8))
        self.assertEqual((ref.stage14.final_mobj.x >> stage.FRACBITS, ref.stage14.final_mobj.y >> stage.FRACBITS), (-172, -194))
        self.assertEqual((ref.stage14.counters.accepted_moves, ref.stage14.counters.rejected_moves), (8, 0))

        self.assertEqual(stage.DEFAULT_PICKUP_MAPTHING_INDEXES, (27, 41))
        self.assertEqual(tuple(p.mapthing_index for p in ref.pickups), (27, 41))
        self.assertEqual(tuple(p.mobj_index for p in ref.pickups), (21, 30))
        self.assertEqual(tuple(p.sprite_name for p in ref.pickups), ("SHOT", "CLIP"))
        self.assertEqual(tuple(p.accepted_move for p in ref.pickups), (1, 1))
        self.assertEqual(tuple(p.removed for p in ref.pickups), (1, 1))
        self.assertEqual((ref.pickups[0].before_shell, ref.pickups[0].after_shell), (0, 8))
        self.assertEqual((ref.pickups[1].before_clip, ref.pickups[1].after_clip), (50, 60))
        self.assertEqual((ref.player.health, ref.player.armorpoints, ref.player.ammo[stage.AM_CLIP], ref.player.ammo[stage.AM_SHELL]), (100, 0, 60, 8))
        self.assertTrue(ref.player.weaponowned[stage.WP_SHOTGUN])
        self.assertEqual((ref.player.readyweapon, ref.player.pendingweapon), (stage.WP_SHOTGUN, stage.WP_NOCHANGE))
        self.assertEqual((ref.player.psprites[stage.PS_WEAPON].state, ref.player.psprites[stage.PS_WEAPON].tics), (18, 1))
        self.assertEqual(
            (
                ref.counters.pickup_probe_count,
                ref.counters.pickup_accepts,
                ref.counters.removed_specials,
                ref.counters.ammo_grants,
                ref.counters.weapon_grants,
            ),
            (2, 2, 2, 2, 1),
        )
        self.assertEqual((ref.draw.status_pixels, ref.draw.weapon_pixels, ref.signature), (12533, 2083, 2810145191))

    def test_executable_build_contains_stage15_status_and_absent_deferred_feature_strings(self) -> None:
        image = stage.build_source_stage15_pickups_psprites_statusbar_shell_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage15_pickups_psprites_statusbar_shell", image)
        self.assertIn(b"Pickups, psprites, and real-patch status shell OK", image)
        self.assertIn(b"PIT_CheckThing", image)
        self.assertIn(b"P_TouchSpecialThing", image)
        self.assertIn(b"P_GiveWeapon", image)
        self.assertIn(b"P_GiveAmmo", image)
        self.assertIn(b"P_SetupPsprites", image)
        self.assertIn(b"P_MovePsprites", image)
        self.assertIn(b"V_DrawPatch", image)
        self.assertIn(b"R_DrawPSprite", image)
        self.assertIn(b" S14SIG=", image)
        self.assertIn(b" PPROBE=", image)
        self.assertIn(b" PACC=", image)
        self.assertIn(b" WPN=", image)
        self.assertIn(b" S15SIG=", image)
        self.assertNotIn(b"source_stage16", lower)
        for forbidden in (
            b"attacks",
            b"damage",
            b"monster ai",
            b"doors",
            b"switches",
            b"sound playback",
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
    def test_smoke_launch_reports_stage15_pickup_status_and_preserved_stage14(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_pickups_psprites_statusbar_shell_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage15_pickups_psprites_statusbar_shell.exe"
        stage.write_source_stage15_pickups_psprites_statusbar_shell_exe(exe_path)

        expected = (
            f"S13SIG={ref.stage14.stage13.draw.framebuffer_signature}",
            f"S14SIG={ref.stage14.signature}",
            f"PPROBE={ref.counters.pickup_probe_count}",
            f"PACC={ref.counters.pickup_accepts}",
            f"P1={ref.pickups[0].mapthing_index}",
            f"P2={ref.pickups[1].mapthing_index}",
            f"CLIP={ref.player.ammo[stage.AM_CLIP]}",
            f"SHELL={ref.player.ammo[stage.AM_SHELL]}",
            f"RDY={ref.player.readyweapon}",
            f"S15SIG={ref.signature}",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn(f"S12SIG={ref.stage14.stage13.stage12.framebuffer_signature}", title)
            self.assertIn(f"BMW={ref.stage14.blockmap.width}", title)
            self.assertIn(f"TIC={len(ref.stage14.script)}", title)
            self.assertIn(f"F14X={ref.stage14.final_mobj.x >> stage.FRACBITS}", title)
            self.assertIn(f"P1N={ref.pickups[0].sprite_name}", title)
            self.assertIn(f"P2N={ref.pickups[1].sprite_name}", title)
            self.assertIn(f"PSPN={ref.draw.weapon_state_name}", title)
            self.assertIn(f"STPIX={ref.draw.status_pixels}", title)
            self.assertIn(f"WPPIX={ref.draw.weapon_pixels}", title)
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
