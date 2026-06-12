import os
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage08_texture_data_setup_debug as stage08
from tools import emit_source_stage09_direct_wall_column_pixels_debug as stage09
from tools import emit_source_stage12_sky_and_masked_midtextures_debug as stage
from tools.map_loader import LineDef, LoadedMap, Sector, SideDef, Thing, Vertex


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


def _minimal_texture_setup() -> stage08.TextureSetup:
    empty_texture = stage08.TextureMetadata(
        index=0,
        name="-",
        width=8,
        height=8,
        patches=(),
        texturewidthmask=7,
        textureheight=8 * stage.FRACUNIT,
        texturecolumnlump=(0,) * 8,
        texturecolumnofs=(0,) * 8,
        texturecompositesize=0,
        direct_columns=0,
        composite_columns=0,
        missing_columns=0,
    )
    masked_texture = stage08.TextureMetadata(
        index=1,
        name="MASKA",
        width=8,
        height=16,
        patches=(),
        texturewidthmask=7,
        textureheight=16 * stage.FRACUNIT,
        texturecolumnlump=(1,) * 8,
        texturecolumnofs=(0,) * 8,
        texturecompositesize=0,
        direct_columns=8,
        composite_columns=0,
        missing_columns=0,
    )
    return stage08.TextureSetup(
        patch_names=(),
        patch_lumps=(),
        textures=(empty_texture, masked_texture),
        texturetranslation=(0, 1),
        textures_hashtable=(),
        firstflat=0,
        lastflat=0,
        numflats=0,
        flattranslation=(),
        texture2_present=False,
        texture1_count=2,
        texture2_count=0,
    )


class SourceStage12SkyMaskedDebugTests(unittest.TestCase):
    def test_source_trace_covers_sky_masked_and_masked_column_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("render_init_sky_map_debug", labels)
        self.assertIn("render_debug_map01_sky_selection", labels)
        self.assertIn("render_draw_planes_sky_branch_debug", labels)
        self.assertIn("render_store_masked_midtexture_debug", labels)
        self.assertIn("render_maskedtexturecol_openings_debug", labels)
        self.assertIn("render_masked_seg_range_debug", labels)
        self.assertIn("render_draw_masked_column_debug", labels)

    def test_synthetic_feature_candidates_and_probe_selection_are_deterministic(self) -> None:
        loaded = LoadedMap(
            name="MAP01",
            source="synthetic",
            vertices=(Vertex(0, 0), Vertex(64, 0)),
            linedefs=(
                LineDef(0, 1, stage08.ML_TWOSIDED, 0, 0, 0, 1),
                LineDef(1, 0, 0, 0, 0, 2, 0xFFFF),
            ),
            sidedefs=(
                SideDef(0, 0, "-", "-", "MASKA", 1),
                SideDef(0, 0, "-", "-", "-", 2),
                SideDef(0, 0, "-", "-", "MASKA", 0),
            ),
            sectors=(
                Sector(0, 128, "FLOOR", "CEIL", 160, 0, 0),
                Sector(0, 128, "FLOOR", "F_SKY1", 160, 0, 0),
                Sector(0, 128, "FLOOR", "CEIL", 160, 0, 0),
            ),
            things=(),
        )
        resolved_sectors = (
            stage08.ResolvedSectorFlats(0, 0),
            stage08.ResolvedSectorFlats(0, 99),
            stage08.ResolvedSectorFlats(0, 0),
        )
        resolved_sidedefs = (
            stage08.ResolvedSideDefTextures(0, 0, 1),
            stage08.ResolvedSideDefTextures(0, 0, 0),
            stage08.ResolvedSideDefTextures(0, 0, 1),
        )

        sky = stage.find_sky_sector_candidates(loaded, resolved_sectors, 99)
        masked = stage.find_two_sided_masked_sidedef_candidates(
            loaded,
            resolved_sidedefs,
            _minimal_texture_setup(),
            raw_segs=((0, 1, 0, 0, 0, 0),),
        )
        probe = stage.select_feature_probe(
            sky,
            masked,
            primary_sky_columns=0,
            primary_masked_columns=0,
        )

        self.assertEqual([candidate.sector_index for candidate in sky], [1])
        self.assertEqual(len(masked), 1)
        self.assertEqual((masked[0].linedef_index, masked[0].sidedef_index), (0, 0))
        self.assertTrue(probe.uses_probe)
        self.assertEqual(probe.sky_sector, sky[0])
        self.assertEqual(probe.masked, masked[0])
        self.assertEqual((probe.view_x, probe.view_y, probe.view_sector), (32, -16, 1))

    def test_synthetic_sky_column_selection_and_skytexturemid(self) -> None:
        self.assertEqual(stage.skytexturemid_for_view_height(200), 100 * stage.FRACUNIT)

        x = 12
        viewangle = 0x12345678
        expected = ((viewangle + stage.XTOVIEWANGLE[x]) & 0xFFFFFFFF) >> stage.ANGLETOSKYSHIFT
        self.assertEqual(stage.sky_texture_column(viewangle, x), expected)

    def test_maskedtexturecol_store_bounds_and_consumption(self) -> None:
        store = stage.MaskedTextureColumnStore(width=4, max_openings=2)

        self.assertTrue(store.store(1, 17))
        self.assertTrue(store.store(2, 18))
        self.assertFalse(store.store(3, 19))
        self.assertFalse(store.store(4, 20))
        self.assertEqual((store.stored_count, store.overflow_count, store.clipped_count), (2, 1, 1))
        self.assertEqual(store.consume(1), 17)
        self.assertEqual(store.consume(1), stage.SHRT_MAX)

    def test_r_draw_masked_column_post_clips_against_floor_and_ceiling(self) -> None:
        posts = (
            stage09.PatchColumnPost(topdelta=0, pixels=b"\x01\x02"),
            stage09.PatchColumnPost(topdelta=4, pixels=b"\x03\x04\x05\x06"),
        )
        sources: list[bytes] = []

        def source_index(pixels: bytes) -> int:
            sources.append(pixels)
            return len(sources) - 1

        commands = stage.masked_post_draw_commands(
            posts,
            x=7,
            texture_id=12,
            texture_name="MASKED",
            texture_column=5,
            sprtopscreen=8 * stage.FRACUNIT,
            spryscale=stage.FRACUNIT,
            dc_texturemid=20 * stage.FRACUNIT,
            mfloorclip=11,
            mceilingclip=8,
            source_index_for_pixels=source_index,
        )

        self.assertEqual(len(commands), 1)
        self.assertEqual((commands[0].x, commands[0].yl, commands[0].yh), (7, 9, 9))
        self.assertEqual(commands[0].texturemid, 20 * stage.FRACUNIT)
        self.assertEqual(len(sources[0]), stage.WALL_COLUMN_SOURCE_HEIGHT)

    def test_pinned_map_preserves_stage11_and_adds_probe_sky_masked_pixels(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_sky_and_masked_midtextures_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.stage11.stage10.stage09.columns_drawn, 162)
        self.assertEqual(ref.stage11.stage10.stage09.framebuffer_signature, 2194105880)
        self.assertEqual(ref.stage11.stage10.columns_drawn, 780)
        self.assertEqual(ref.stage11.stage10.framebuffer_signature, 4201955800)
        self.assertEqual(ref.stage11.visplane_count, 38)
        self.assertEqual(ref.stage11.flat_spans_drawn, 169)
        self.assertEqual(ref.stage11.flat_pixels_drawn, 20791)
        self.assertEqual(ref.stage11.sky_visplanes_skipped, 0)
        self.assertEqual(ref.stage11.framebuffer_signature, 2178063413)

        self.assertEqual(len(ref.sky_sector_candidates), 40)
        self.assertEqual(len(ref.masked_sidedef_candidates), 27)
        self.assertTrue(ref.probe.uses_probe)
        self.assertEqual(ref.probe.sky_sector.sector_index, 2)
        assert ref.probe.masked is not None
        self.assertEqual((ref.probe.masked.linedef_index, ref.probe.masked.sidedef_index), (418, 617))
        self.assertEqual((ref.probe.view_x, ref.probe.view_y, ref.probe.view_angle_degrees, ref.probe.view_sector), (1771, -773, 277, 196))
        self.assertEqual((ref.skyflatnum, ref.skytexture, ref.skytexturemid), (120, 229, 6553600))
        self.assertEqual((ref.sky_visplanes_drawn, ref.sky_columns_drawn, ref.sky_pixels_drawn), (1, 32, 1280))
        self.assertEqual((ref.first_sky_texture_id, ref.first_sky_texture_name, ref.first_sky_texture_column), (229, "SKY1", 144))
        self.assertEqual((ref.masked_segments_considered, ref.masked_columns_stored), (1, 32))
        self.assertEqual((ref.masked_columns_drawn, ref.masked_post_commands_drawn, ref.masked_pixels_drawn), (32, 32, 1888))
        self.assertEqual((ref.masked_opening_overflow_count, ref.masked_column_source_skips), (0, 0))
        self.assertEqual((ref.first_masked_texture_id, ref.first_masked_texture_name, ref.first_masked_texture_column), (814, "AQMETL29", 3))
        self.assertEqual(ref.skipped_sprite_count, 0)
        self.assertEqual(ref.framebuffer_signature, 2853564869)

    def test_executable_build_contains_stage12_status_and_no_stage13_or_deferred_feature_strings(self) -> None:
        image = stage.build_source_stage12_sky_and_masked_midtextures_debug_exe()
        lower = image.lower()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage12_sky_and_masked_midtextures_debug", image)
        self.assertIn(b"Sky and masked midtexture debug OK", image)
        self.assertIn(b"R_DrawPlanes", image)
        self.assertIn(b"R_RenderMaskedSegRange", image)
        self.assertIn(b"R_DrawMaskedColumn", image)
        self.assertIn(b" SKCAND=", image)
        self.assertIn(b" SCOL=", image)
        self.assertIn(b" MCOL12=", image)
        self.assertIn(b" S12SIG=", image)
        self.assertNotIn(b"source_stage13", image)
        self.assertNotIn(b"real sprites", lower)
        self.assertNotIn(b"actor rendering", lower)
        self.assertNotIn(b"movement", lower)
        self.assertNotIn(b"gameplay loop", lower)
        self.assertNotIn(b"thing loading", lower)
        self.assertNotIn(b"GCC:", image)
        self.assertNotIn(b"MinGW", image)
        self.assertNotIn(b"Microsoft Visual C", image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage12_sky_masked_counts_and_preserved_stage11(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_sky_and_masked_midtextures_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage12_sky_and_masked_midtextures_debug.exe"
        stage.write_source_stage12_sky_and_masked_midtextures_debug_exe(exe_path)

        expected = (
            f"FSIG={ref.stage11.framebuffer_signature}",
            f"SKCAND={len(ref.sky_sector_candidates)}",
            f"MCAND={len(ref.masked_sidedef_candidates)}",
            f"SCOL={ref.sky_columns_drawn}",
            f"MCOL12={ref.masked_columns_drawn}",
            f"S12SIG={ref.framebuffer_signature}",
        )
        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid, expected=expected)
            self.assertIn(f"DRAW={ref.stage11.stage10.stage09.columns_drawn}", title)
            self.assertIn(f"TCOL={ref.stage11.stage10.columns_drawn}", title)
            self.assertIn(f"FSP={ref.stage11.flat_spans_drawn}", title)
            self.assertIn(f"FPIX={ref.stage11.flat_pixels_drawn}", title)
            self.assertIn(f"SKYSEC={ref.probe.sky_sector.sector_index}", title)
            self.assertIn(f"MSIDE={ref.probe.masked.sidedef_index}", title)
            self.assertIn(f"SKYT={ref.first_sky_texture_id}", title)
            self.assertIn(f"SKYN={ref.first_sky_texture_name}", title)
            self.assertIn(f"SPIX={ref.sky_pixels_drawn}", title)
            self.assertIn(f"MTEX={ref.first_masked_texture_id}", title)
            self.assertIn(f"MN={ref.first_masked_texture_name}", title)
            self.assertIn(f"MPOST={ref.masked_post_commands_drawn}", title)
            self.assertIn(f"MPIX={ref.masked_pixels_drawn}", title)
            self.assertIn(f"SSK={ref.skipped_sprite_count}", title)
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
