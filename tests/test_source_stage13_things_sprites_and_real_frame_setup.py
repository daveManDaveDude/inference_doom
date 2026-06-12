import os
import struct
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage09_direct_wall_column_pixels_debug as stage09
from tools import emit_source_stage13_things_sprites_and_real_frame_setup as stage
from tools.map_loader import Thing


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


def _sprite_metadata_for_projection() -> stage.SpriteMetadata:
    frame = stage.SpriteFrameMetadata(
        rotate=0,
        lump=(0, 0, 0, 0, 0, 0, 0, 0),
        flip=(False, False, False, False, False, False, False, False),
    )
    return stage.SpriteMetadata(
        sprnames=("PLAY",),
        firstspritelump=0,
        lastspritelump=0,
        lumps=(
            stage.SpriteLumpMetadata(
                index=0,
                name="PLAYA0",
                width=64 * stage.FRACUNIT,
                offset=32 * stage.FRACUNIT,
                topoffset=56 * stage.FRACUNIT,
                patch_width=64,
                patch_height=56,
            ),
        ),
        defs=(stage.SpriteDefMetadata(name="PLAY", frames=(frame,)),),
        sprite_defs_present=1,
        frames_present=1,
        missing_frames=0,
    )


def _mobj(**kwargs) -> stage.RenderMobj:
    defaults = dict(
        index=0,
        mapthing_index=0,
        type_name="MT_TEST",
        doomednum=1,
        x=64 * stage.FRACUNIT,
        y=0,
        z=0,
        angle=0,
        sprite=0,
        frame=0,
        flags=0,
        radius=16 * stage.FRACUNIT,
        height=56 * stage.FRACUNIT,
        floorz=0,
        ceilingz=128 * stage.FRACUNIT,
        sector=0,
        subsector=0,
    )
    defaults.update(kwargs)
    return stage.RenderMobj(**defaults)


def _player(**kwargs) -> stage.MinimalPlayer:
    defaults = dict(
        player_index=0,
        mapthing_index=0,
        mobj_index=0,
        x=0,
        y=0,
        z=0,
        angle=0,
        viewz=41 * stage.FRACUNIT,
        sector=0,
        subsector=0,
    )
    defaults.update(kwargs)
    return stage.MinimalPlayer(**defaults)


class SourceStage13ThingsSpritesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doom = stage.parse_source_info_tables()

    def test_source_trace_covers_things_sprites_and_frame_setup_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("P_LoadThings_decode_debug", labels)
        self.assertIn("P_SpawnMapThing_render_subset_debug", labels)
        self.assertIn("R_InitSpriteLumps_metadata_debug", labels)
        self.assertIn("R_ProjectSprite_source_shape_debug", labels)
        self.assertIn("R_DrawSpriteRange_columns_debug", labels)
        self.assertIn("R_SetupFrame_real_player_start_debug", labels)

    def test_synthetic_p_loadthings_decodes_filters_and_bounds_records(self) -> None:
        records = b"".join(
            struct.pack("<hhHHH", *record)
            for record in (
                (10, 20, 90, 1, 7),
                (30, 40, 0, 3004, 2),
                (0, 0, 0, 0, 0),
                (0, 0, 0, 65, 2),
                (50, 60, 0, 2001, 2),
            )
        )

        result = stage.p_loadthings_source_shape(records, max_things=2, commercial=False)

        self.assertEqual(result.loaded_count, 2)
        self.assertEqual(result.player_start_count, 1)
        self.assertEqual(result.nonpositive_skip_count, 1)
        self.assertEqual(result.commercial_filter_skip_count, 1)
        self.assertEqual(result.overflow_count, 1)
        self.assertEqual((result.things[0].x, result.things[0].y, result.things[0].type), (10, 20, 1))

    def test_synthetic_spawn_mapthing_handles_player_mobjs_filters_and_unknowns(self) -> None:
        things = (
            Thing(-16, 32, 90, 1, 7),
            Thing(0, 0, 0, 3004, 2),
            Thing(0, 0, 0, 3004, 0),
            Thing(0, 0, 0, 9999, 2),
            Thing(0, 0, 0, 2001, 18),
        )

        result = stage.p_spawn_mapthings_source_shape(things, self.doom)

        self.assertEqual(result.player_start_count, 1)
        self.assertEqual(result.player_mobj_count, 1)
        self.assertEqual(result.inert_mobj_count, 1)
        self.assertEqual(result.skill_skip_count, 1)
        self.assertEqual(result.unsupported_type_count, 1)
        self.assertEqual(result.option_skip_count, 1)
        self.assertEqual((result.players[0].x >> stage.FRACBITS, result.players[0].y >> stage.FRACBITS), (-16, 32))
        self.assertEqual(stage.angle_to_degrees(result.players[0].angle), 90)

    def test_synthetic_spawn_respects_playeringame_and_nomonitor_options(self) -> None:
        starts = (Thing(0, 0, 0, 1, 7), Thing(64, 0, 0, 2, 7))
        result = stage.p_spawn_mapthings_source_shape(starts, self.doom)

        self.assertEqual(result.player_start_count, 2)
        self.assertEqual(result.player_mobj_count, 1)
        self.assertEqual(len(result.players), 1)

        monsters_off = stage.p_spawn_mapthings_source_shape(
            (Thing(0, 0, 0, 3004, 2),),
            self.doom,
            options=stage.SpawnOptions(nomonsters=True),
        )
        self.assertEqual(monsters_off.nomonster_skip_count, 1)

    def test_synthetic_sprite_metadata_resolves_rotations_offsets_and_missing_frames(self) -> None:
        defs, present, frames, missing = stage.build_sprite_defs_from_lump_names(
            ("TEST",),
            ("TESTA0", "TESTB1B5", "TESTB2B6", "TESTB3B7", "TESTB4B8"),
        )

        self.assertEqual((present, frames, missing), (1, 2, 0))
        self.assertEqual(defs[0].frames[0].rotate, 0)
        self.assertEqual(defs[0].frames[0].lump, (0, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(defs[0].frames[1].rotate, 1)
        self.assertEqual(defs[0].frames[1].lump, (1, 2, 3, 4, 1, 2, 3, 4))
        self.assertTrue(defs[0].frames[1].flip[4])

        _defs, _present, _frames, missing = stage.build_sprite_defs_from_lump_names(
            ("MISS",),
            ("MISSA1",),
        )
        self.assertEqual(missing, 1)

    def test_synthetic_clear_and_new_vissprite_reset_and_overflow(self) -> None:
        metadata = _sprite_metadata_for_projection()
        vis, reason = stage.r_project_sprite_source_shape(_mobj(), _player(), metadata)
        self.assertIsNone(reason)
        assert vis is not None

        state = stage.VisSpriteState(max_vissprites=1)
        self.assertIsNotNone(stage.r_new_vissprite_source_shape(state, vis))
        self.assertIsNone(stage.r_new_vissprite_source_shape(state, vis))
        self.assertEqual(state.overflow_count, 1)

        stage.r_clear_sprites_source_shape(state)
        self.assertEqual((len(state.vissprites or ()), state.overflow_count), (0, 0))

    def test_synthetic_project_sprite_transform_clipping_and_rejection(self) -> None:
        metadata = _sprite_metadata_for_projection()
        player = _player()

        vis, reason = stage.r_project_sprite_source_shape(_mobj(), player, metadata)
        self.assertIsNone(reason)
        assert vis is not None
        self.assertLessEqual(vis.x1, vis.x2)
        self.assertGreater(vis.scale, 0)
        self.assertGreaterEqual(vis.x1, 0)

        behind, reason = stage.r_project_sprite_source_shape(
            _mobj(x=-64 * stage.FRACUNIT),
            player,
            metadata,
        )
        self.assertIsNone(behind)
        self.assertEqual(reason, "minz")

        side, reason = stage.r_project_sprite_source_shape(
            _mobj(x=64 * stage.FRACUNIT, y=400 * stage.FRACUNIT),
            player,
            metadata,
        )
        self.assertIsNone(side)
        self.assertEqual(reason, "side")

    def test_synthetic_sort_draw_range_and_drawseg_clip_interaction(self) -> None:
        far = _sprite_metadata_for_projection()
        vis_a = stage.VisSprite(
            0, 0, "A", "TEST", 0, 0, 0, "TESTA0",
            10, 10, 10, 10, stage.FRACUNIT, stage.FRACUNIT, 0, 0, False, 1,
        )
        vis_b = stage.VisSprite(
            1, 1, "B", "TEST", 0, 0, 0, "TESTA0",
            10, 10, 10, 10, stage.FRACUNIT * 2, stage.FRACUNIT, 0, 0, False, 1,
        )
        self.assertEqual([vis.thing_index for vis in stage.r_sort_vissprites_source_shape((vis_b, vis_a))], [0, 1])
        self.assertEqual(far.lumps[0].patch_width, 64)

        sources: list[bytes] = []

        def source_index(pixels: bytes) -> int:
            sources.append(pixels)
            return len(sources) - 1

        drawseg = stage.DrawSegClip(
            x1=10,
            x2=10,
            sprtopclip=(100,),
            sprbottomclip=(102,),
        )
        floorclip, ceilingclip, clipped = stage.apply_drawseg_sprite_clips(vis_a, (drawseg,))
        commands, columns, posts, skips = stage.r_draw_sprite_range_source_shape(
            vis_a,
            lambda _column: (stage09.PatchColumnPost(topdelta=0, pixels=b"\x01\x02\x03\x04"),),
            source_index,
            floorclip=floorclip,
            ceilingclip=ceilingclip,
        )

        self.assertEqual(clipped, 1)
        self.assertEqual((columns, posts, skips), (1, 1, 0))
        self.assertEqual((commands[0].x, commands[0].yl, commands[0].yh), (10, 101, 101))
        self.assertEqual(len(sources[0]), stage.WALL_COLUMN_SOURCE_HEIGHT)

    def test_pinned_map_preserves_stage12_and_adds_real_things_sprite_pixels(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_things_sprites_real_frame_setup_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.stage12.stage11.stage10.stage09.columns_drawn, 162)
        self.assertEqual(ref.stage12.stage11.stage10.stage09.framebuffer_signature, 2194105880)
        self.assertEqual(ref.stage12.stage11.stage10.columns_drawn, 780)
        self.assertEqual(ref.stage12.stage11.stage10.framebuffer_signature, 4201955800)
        self.assertEqual(ref.stage12.stage11.visplane_count, 38)
        self.assertEqual(ref.stage12.stage11.flat_spans_drawn, 169)
        self.assertEqual(ref.stage12.stage11.flat_pixels_drawn, 20791)
        self.assertEqual(ref.stage12.stage11.framebuffer_signature, 2178063413)
        self.assertEqual(ref.stage12.framebuffer_signature, 2853564869)

        self.assertEqual((ref.thing_load.loaded_count, ref.spawn.player_start_count), (200, 4))
        self.assertEqual((len(ref.spawn.mobjs), ref.spawn.player_mobj_count, ref.spawn.inert_mobj_count), (120, 1, 119))
        self.assertEqual((ref.spawn.unsupported_type_count, ref.spawn.option_skip_count, ref.spawn.skill_skip_count), (2, 48, 17))
        self.assertEqual((ref.player.x >> stage.FRACBITS, ref.player.y >> stage.FRACBITS), (-192, -192))
        self.assertEqual((stage.angle_to_degrees(ref.player.angle), ref.player.sector, ref.player.subsector, ref.player.viewz), (0, 0, 227, 2686976))

        self.assertEqual((len(ref.sprite_metadata.sprnames), len(ref.sprite_metadata.lumps)), (138, 1350))
        self.assertEqual((ref.sprite_metadata.sprite_defs_present, ref.sprite_metadata.frames_present, ref.sprite_metadata.missing_frames), (138, 625, 0))
        self.assertEqual((ref.primary_sector_count, len(ref.vissprites), ref.probe_active), (29, 6, 0))
        self.assertEqual(ref.projection_rejects, {"minz": 1, "side": 1, "left": 1})

        first = ref.draw.first_drawn
        assert first is not None
        self.assertEqual((first.mapthing_index, first.type_name, first.sprite_name), (8, "MT_MISC2", "BON1"))
        self.assertEqual((first.sprite, first.frame, first.patch, first.patch_name), (60, 0, 1009, "BON1A0"))
        self.assertEqual((first.x1, first.x2, first.scale, ref.draw.first_drawn_patch_column), (67, 69, 16178, 0))
        self.assertEqual((ref.draw.columns_drawn, ref.draw.post_commands_drawn, ref.draw.pixels_drawn), (35, 40, 175))
        self.assertEqual((ref.draw.source_skip_count, ref.draw.drawseg_clip_columns, len(ref.draw.column_sources)), (0, 0, 31))
        self.assertEqual(ref.draw.framebuffer_signature, 2904743961)

    def test_executable_build_contains_stage13_status_and_no_stage14_or_deferred_feature_strings(self) -> None:
        image = stage.build_source_stage13_things_sprites_and_real_frame_setup_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage13_things_sprites_and_real_frame_setup", image)
        self.assertIn(b"THINGS and sprite frame setup OK", image)
        self.assertIn(b"P_LoadThings", image)
        self.assertIn(b"R_ProjectSprite", image)
        self.assertIn(b"R_DrawSpriteRange", image)
        self.assertIn(b"R_DrawMaskedColumn", image)
        self.assertIn(b'requestedExecutionLevel level="asInvoker"', image)
        self.assertIn(b" TH=", image)
        self.assertIn(b" VIS=", image)
        self.assertIn(b" SPCOL=", image)
        self.assertIn(b" S13SIG=", image)
        self.assertNotIn(b"source_stage14", lower)
        for forbidden in (
            b"movement",
            b"collision movement",
            b"thinker ticks",
            b"enemy ai",
            b"attacks",
            b"pickups",
            b"sound",
            b"user interface",
            b"save/load",
            b"networking",
            b"gcc:",
            b"mingw",
            b"microsoft visual c",
        ):
            self.assertNotIn(forbidden, lower)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage13_sprite_counts_and_preserved_stage12(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_things_sprites_real_frame_setup_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage13_things_sprites_and_real_frame_setup.exe"
        stage.write_source_stage13_things_sprites_and_real_frame_setup_exe(exe_path)

        expected = (
            f"FSIG={ref.stage12.stage11.framebuffer_signature}",
            f"S12SIG={ref.stage12.framebuffer_signature}",
            f"TH={ref.thing_load.loaded_count}",
            f"PST={ref.spawn.player_start_count}",
            f"RMO={len(ref.spawn.mobjs)}",
            f"VIS={len(ref.vissprites)}",
            f"SPCOL={ref.draw.columns_drawn}",
            f"SPPIX={ref.draw.pixels_drawn}",
            f"S13SIG={ref.draw.framebuffer_signature}",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn(f"DRAW={ref.stage12.stage11.stage10.stage09.columns_drawn}", title)
            self.assertIn(f"TCOL={ref.stage12.stage11.stage10.columns_drawn}", title)
            self.assertIn(f"FSP={ref.stage12.stage11.flat_spans_drawn}", title)
            self.assertIn(f"SCOL={ref.stage12.sky_columns_drawn}", title)
            self.assertIn(f"MCOL12={ref.stage12.masked_columns_drawn}", title)
            self.assertIn(f"PSX={ref.player.x >> stage.FRACBITS}", title)
            self.assertIn(f"PSY={ref.player.y >> stage.FRACBITS}", title)
            self.assertIn(f"FSN={ref.draw.first_drawn.sprite_name}", title)
            self.assertIn(f"FSPN={ref.draw.first_drawn.patch_name}", title)
            self.assertIn(f"SPPOST={ref.draw.post_commands_drawn}", title)
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
