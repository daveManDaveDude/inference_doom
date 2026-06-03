import os
import struct
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage08_texture_data_setup_debug as stage08
from tools import emit_source_stage09_direct_wall_column_pixels_debug as stage09
from tools import emit_source_stage10_composite_two_sided_wall_edges_debug as stage
from tools.wad import WadFile


REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_WAD = REPO_ROOT / stage.WAD_PATH.replace("\\", "/")


def window_title_for_pid(pid: int, timeout_seconds: float = 5.0) -> tuple[int, str]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    deadline = time.monotonic() + timeout_seconds

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
            return found[0]
        time.sleep(0.1)

    raise TimeoutError(f"no visible window title found for pid {pid}")


def fixed_name(name: str) -> bytes:
    return name.encode("ascii").ljust(8, b"\x00")


def patch_lump(columns: list[list[tuple[int, bytes]]], *, height: int = 128) -> bytes:
    width = len(columns)
    header_size = 8 + width * 4
    offsets: list[int] = []
    column_blobs: list[bytes] = []
    cursor = header_size
    for posts in columns:
        offsets.append(cursor)
        blob = bytearray()
        for topdelta, pixels in posts:
            blob.extend(bytes([topdelta, len(pixels), 0]))
            blob.extend(pixels)
            blob.append(0)
        blob.append(0xFF)
        column_blobs.append(bytes(blob))
        cursor += len(blob)

    return (
        struct.pack("<hhhh", width, height, 0, 0)
        + b"".join(struct.pack("<I", offset) for offset in offsets)
        + b"".join(column_blobs)
    )


def pnames_lump(names: list[str]) -> bytes:
    return struct.pack("<i", len(names)) + b"".join(fixed_name(name) for name in names)


def texture_lump(defs: list[tuple[str, int, int, list[tuple[int, int, int]]]]) -> bytes:
    directory_size = 4 + len(defs) * 4
    records: list[bytes] = []
    offsets: list[int] = []
    cursor = directory_size
    for name, width, height, patches in defs:
        offsets.append(cursor)
        record = (
            fixed_name(name)
            + struct.pack("<i", 0)
            + struct.pack("<hh", width, height)
            + struct.pack("<i", 0)
            + struct.pack("<h", len(patches))
        )
        for originx, originy, patch_index in patches:
            record += struct.pack("<hhhhh", originx, originy, patch_index, 0, 0)
        records.append(record)
        cursor += len(record)
    return (
        struct.pack("<i", len(defs))
        + b"".join(struct.pack("<i", offset) for offset in offsets)
        + b"".join(records)
    )


def build_wad(lumps: list[tuple[str, bytes]]) -> WadFile:
    offset = 12
    lump_blobs: list[bytes] = []
    directory: list[bytes] = []
    for name, data in lumps:
        lump_blobs.append(data)
        directory.append(struct.pack("<ii8s", offset, len(data), fixed_name(name)))
        offset += len(data)
    directory_offset = offset
    wad_data = (
        struct.pack("<4sii", b"IWAD", len(lumps), directory_offset)
        + b"".join(lump_blobs)
        + b"".join(directory)
    )
    return WadFile.from_bytes(wad_data, source="<test>")


def synthetic_texture_wad(height: int = 128) -> WadFile:
    patch_a = bytes([7] * height)
    patch_b = bytes([9] * height)
    patch_c = bytes([11] * height)
    return build_wad(
        [
            ("DUMMY", b""),
            ("PATCHA", patch_lump([[(0, patch_a)], [(0, patch_b)]], height=height)),
            ("PATCHB", patch_lump([[(0, patch_c)]], height=height)),
            ("PNAMES", pnames_lump(["PATCHA", "PATCHB"])),
            (
                "TEXTURE1",
                texture_lump(
                    [
                        ("DIRECT", 2, height, [(0, 0, 0)]),
                        ("COMBO", 1, height, [(0, 0, 0), (0, 0, 1)]),
                        ("MISS", 2, height, [(0, 0, 1)]),
                    ]
                ),
            ),
            ("F_START", b""),
            ("F_SKY1", b"\x00" * 4096),
            ("FLAT1", b"\x00" * 4096),
            ("F_END", b""),
            ("PLAYPAL", b"\x00" * 768),
            ("COLORMAP", bytes(range(256))),
        ]
    )


class SourceStage10CompositeTwoSidedWallEdgesDebugTests(unittest.TestCase):
    def test_source_trace_covers_composite_and_two_sided_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("render_draw_column_in_cache_source_shape_debug", labels)
        self.assertIn("render_generate_composite_cache_debug", labels)
        self.assertIn("render_get_column_direct_or_composite_debug", labels)
        self.assertIn("render_two_sided_wall_edges_debug", labels)
        self.assertIn("render_plane_mark_records_debug", labels)

    def test_r_draw_column_in_cache_clips_originy_height_and_overlaps(self) -> None:
        posts = (
            stage09.PatchColumnPost(topdelta=0, pixels=b"\x01\x02\x03\x04"),
            stage09.PatchColumnPost(topdelta=1, pixels=b"\x09\x09"),
        )

        clipped_top = stage.r_draw_column_in_cache(posts[:1], originy=-2, cacheheight=4)
        clipped_bottom = stage.r_draw_column_in_cache(posts[:1], originy=2, cacheheight=4)
        overlapped = stage.r_draw_column_in_cache(posts, originy=0, cacheheight=4)

        self.assertEqual(clipped_top, b"\x03\x04\x00\x00")
        self.assertEqual(clipped_bottom, b"\x00\x00\x01\x02")
        self.assertEqual(overlapped, b"\x01\x09\x09\x04")

    def test_r_generate_composite_direct_missing_composite_and_overflow(self) -> None:
        wad = synthetic_texture_wad()
        setup = stage08.load_texture_setup_from_wad(wad)
        cache = stage.CompositeColumnCache(max_entries=4)

        direct = stage.r_generate_composite_column(wad, setup, 0, 0, cache)
        composite = stage.r_generate_composite_column(wad, setup, 1, 0, cache)
        hit = stage.r_generate_composite_column(wad, setup, 1, 0, cache)
        missing = stage.r_generate_composite_column(wad, setup, 2, 1, cache)
        overflow = stage.r_generate_composite_column(
            wad, setup, 1, 0, stage.CompositeColumnCache(max_entries=0)
        )

        self.assertEqual(direct.skip_reason, "direct-only")
        self.assertIsNone(direct.pixels)
        self.assertEqual(composite.pixels, bytes([11] * 128))
        self.assertIsNone(composite.skip_reason)
        self.assertEqual(hit.pixels, composite.pixels)
        self.assertEqual((cache.builds, cache.hits), (1, 1))
        self.assertEqual(missing.skip_reason, "missing")
        self.assertEqual(overflow.skip_reason, "overflow")

    def test_r_get_column_dispatches_direct_and_composite_cache_paths(self) -> None:
        wad = synthetic_texture_wad()
        setup = stage08.load_texture_setup_from_wad(wad)
        composite_cache = stage.CompositeColumnCache()
        direct_cache: dict[tuple[int, int], bytes] = {}

        direct = stage.r_get_column_direct_or_composite(
            wad, setup, 0, 1, composite_cache, direct_cache
        )
        composite_build = stage.r_get_column_direct_or_composite(
            wad, setup, 1, 0, composite_cache, direct_cache
        )
        composite_hit = stage.r_get_column_direct_or_composite(
            wad, setup, 1, 0, composite_cache, direct_cache
        )

        self.assertEqual(direct.source_kind, "direct")
        self.assertEqual(direct.pixels, bytes([9] * 128))
        self.assertEqual(composite_build.source_kind, "composite")
        self.assertEqual(composite_build.pixels, bytes([11] * 128))
        self.assertEqual(composite_hit.pixels, composite_build.pixels)
        self.assertEqual((composite_cache.builds, composite_cache.hits), (1, 1))

    def test_r_render_seg_loop_upper_lower_clipping_synthetic_column(self) -> None:
        result = stage.render_seg_loop_edge_clip_column(
            ceilingclip=4,
            floorclip=80,
            topfrac=(10 << stage.HEIGHTBITS),
            bottomfrac=(70 << stage.HEIGHTBITS),
            pixhigh=(20 << stage.HEIGHTBITS),
            pixlow=(50 << stage.HEIGHTBITS),
            pixhighstep=3,
            pixlowstep=5,
            markceiling=True,
            markfloor=True,
            has_toptexture=True,
            has_bottomtexture=True,
        )

        self.assertEqual((result.yl, result.yh), (10, 70))
        self.assertEqual((result.upper_yl, result.upper_yh), (10, 20))
        self.assertEqual((result.lower_yl, result.lower_yh), (50, 70))
        self.assertEqual(result.ceilingclip, 20)
        self.assertEqual(result.floorclip, 50)
        self.assertEqual(result.ceiling_mark, (5, 9))
        self.assertEqual(result.floor_mark, (71, 79))
        self.assertEqual((result.pixhigh_next, result.pixlow_next), ((20 << stage.HEIGHTBITS) + 3, (50 << stage.HEIGHTBITS) + 5))

    def test_pinned_map_composite_and_two_sided_reference_counts(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_composite_two_sided_wall_edges_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.stage09.columns_drawn, 162)
        self.assertEqual(ref.stage09.skipped_composite_columns, 135)
        self.assertEqual(ref.stage09.framebuffer_signature, 2194105880)
        self.assertEqual(ref.spans_considered, 86)
        self.assertEqual(ref.one_sided_spans, 24)
        self.assertEqual(ref.two_sided_spans, 62)
        self.assertEqual(ref.two_sided_supported_edge_spans, 30)
        self.assertEqual(ref.two_sided_no_supported_edge_spans, 32)
        self.assertEqual(ref.mid_composite_columns_attempted, 135)
        self.assertEqual(ref.mid_composite_columns_drawn, 2)
        self.assertEqual(ref.mid_composite_columns_clipped_empty, 133)
        self.assertEqual(ref.upper_columns_drawn, 478)
        self.assertEqual(ref.upper_composite_columns_drawn, 6)
        self.assertEqual(ref.lower_columns_drawn, 138)
        self.assertEqual(ref.lower_composite_columns_drawn, 0)
        self.assertEqual(ref.composite_cache_builds, 89)
        self.assertEqual(ref.composite_cache_hits, 75)
        self.assertEqual(ref.composite_cache_overflows, 0)
        self.assertEqual(ref.composite_skip_short_columns, 23)
        self.assertEqual(ref.composite_skip_other_columns, 0)
        self.assertEqual(ref.plane_mark_ceiling_records, 727)
        self.assertEqual(ref.plane_mark_floor_records, 932)
        self.assertEqual(ref.masked_midtexture_skips, 0)
        self.assertEqual(ref.columns_drawn, 780)
        self.assertEqual(ref.direct_columns_drawn, 772)
        self.assertEqual(ref.composite_columns_drawn, 8)
        self.assertEqual(ref.pixels_drawn, 37546)
        self.assertEqual(ref.framebuffer_signature, 4201955800)
        self.assertEqual(
            (ref.first_drawn_texture_id, ref.first_drawn_texture_name, ref.first_drawn_texture_column),
            (850, "AQRUST08", 127),
        )
        self.assertEqual(
            (ref.last_drawn_texture_id, ref.last_drawn_texture_name, ref.last_drawn_texture_column),
            (887, "AQSECT08", 127),
        )
        self.assertEqual((len(ref.column_sources), len(ref.commands), len(ref.plane_mark_records)), (414, 780, 1659))

    def test_executable_build_contains_stage10_status_text_and_no_stage11_or_deferred_features(self) -> None:
        image = stage.build_source_stage10_composite_two_sided_wall_edges_debug_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage10_composite_two_sided_wall_edges_debug", image)
        self.assertIn(b"Composite and two-sided wall edge debug OK", image)
        self.assertIn(b"R_DrawColumnInCache", image)
        self.assertIn(b"R_GenerateComposite", image)
        self.assertIn(b"R_GetColumn", image)
        self.assertIn(b"R_RenderSegLoop", image)
        self.assertIn(b" CMB=", image)
        self.assertIn(b" UCOL=", image)
        self.assertIn(b" TSIG=", image)
        self.assertNotIn(b"flat-span drawing", image.lower())
        self.assertNotIn(b"sky drawing", image.lower())
        self.assertNotIn(b"masked texture drawing", image.lower())
        self.assertNotIn(b"actor rendering", image.lower())
        self.assertNotIn(b"gameplay loop", image.lower())
        self.assertNotIn(b"source_stage11", image)
        self.assertNotIn(b"GCC:", image)
        self.assertNotIn(b"MinGW", image)
        self.assertNotIn(b"Microsoft Visual C", image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_stage10_counts_signature_and_preserved_stage09_counts(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_composite_two_sided_wall_edges_for_pinned_map(PINNED_WAD)
        exe_path = REPO_ROOT / "build" / "source_stage10_composite_two_sided_wall_edges_debug.exe"
        stage.write_source_stage10_composite_two_sided_wall_edges_debug_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid)
            self.assertIn(f"DRAW={ref.stage09.columns_drawn}", title)
            self.assertIn(f"SKC={ref.stage09.skipped_composite_columns}", title)
            self.assertIn(f"SKU={ref.stage09.skipped_unsupported_wall_cases}", title)
            self.assertIn(f"SIG={ref.stage09.framebuffer_signature}", title)
            self.assertIn(f"CMB={ref.composite_cache_builds}", title)
            self.assertIn(f"CMH={ref.composite_cache_hits}", title)
            self.assertIn(f"CMO={ref.composite_cache_overflows}", title)
            self.assertIn(f"MCOL={ref.mid_composite_columns_drawn}", title)
            self.assertIn(f"MCEMP={ref.mid_composite_columns_clipped_empty}", title)
            self.assertIn(f"UCOL={ref.upper_columns_drawn}", title)
            self.assertIn(f"UCOMP={ref.upper_composite_columns_drawn}", title)
            self.assertIn(f"LCOL={ref.lower_columns_drawn}", title)
            self.assertIn(
                f"PM={ref.plane_mark_ceiling_records + ref.plane_mark_floor_records}",
                title,
            )
            self.assertIn(f"F10TEX={ref.first_drawn_texture_id}", title)
            self.assertIn(f"F10N={ref.first_drawn_texture_name}", title)
            self.assertIn(f"L10TEX={ref.last_drawn_texture_id}", title)
            self.assertIn(f"L10N={ref.last_drawn_texture_name}", title)
            self.assertIn(f"TCOL={ref.columns_drawn}", title)
            self.assertIn(f"TPIX={ref.pixels_drawn}", title)
            self.assertIn(f"TSIG={ref.framebuffer_signature}", title)
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
