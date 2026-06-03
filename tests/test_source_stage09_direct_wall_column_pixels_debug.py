import os
import struct
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage09_direct_wall_column_pixels_debug as stage
from tools import emit_source_stage08_texture_data_setup_debug as stage08
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
    return struct.pack("<i", len(defs)) + b"".join(struct.pack("<i", o) for o in offsets) + b"".join(records)


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


class SourceStage09DirectWallColumnPixelsDebugTests(unittest.TestCase):
    def test_source_trace_covers_direct_column_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("render_get_column_direct_debug", labels)
        self.assertIn("render_draw_column_debug", labels)
        self.assertIn("render_direct_wall_column_pixels_debug", labels)
        self.assertIn("stage09_direct_patch_column_decode_debug", labels)

    def test_synthetic_patch_header_and_column_post_parsing(self) -> None:
        data = patch_lump(
            [
                [(0, bytes(range(128)))],
                [(3, b"\x10\x11"), (9, b"\x20")],
            ]
        )

        header = stage08.parse_patch_header(data, lump_name="PATCHA")
        posts0 = stage.parse_patch_column_posts(data, 0, lump_name="PATCHA")
        posts1 = stage.parse_patch_column_posts(data, 1, lump_name="PATCHA")

        self.assertEqual((header.width, header.height), (2, 128))
        self.assertEqual(len(posts0), 1)
        self.assertEqual((posts0[0].topdelta, len(posts0[0].pixels)), (0, 128))
        self.assertEqual([(post.topdelta, post.pixels) for post in posts1], [(3, b"\x10\x11"), (9, b"\x20")])
        self.assertEqual(stage.decode_opaque_direct_column(data, 0, lump_name="PATCHA"), bytes(range(128)))
        self.assertIsNone(stage.decode_opaque_direct_column(data, 1, lump_name="PATCHA"))

    def test_synthetic_direct_r_get_column_wraps_and_composite_columns_skip(self) -> None:
        full_a = bytes([7] * 128)
        full_b = bytes([9] * 128)
        wad = build_wad(
            [
                ("DUMMY", b""),
                ("PATCHA", patch_lump([[(0, full_a)], [(0, full_b)]])),
                ("PATCHB", patch_lump([[(0, bytes([11] * 128))]])),
                ("PNAMES", pnames_lump(["PATCHA", "PATCHB"])),
                (
                    "TEXTURE1",
                    texture_lump(
                        [
                            ("DIRECT", 2, 128, [(0, 0, 0)]),
                            ("COMBO", 1, 128, [(0, 0, 0), (0, 0, 1)]),
                        ]
                    ),
                ),
                ("F_START", b""),
                ("FLAT1", b"\x00" * 4096),
                ("F_END", b""),
                ("PLAYPAL", b"\x00" * 768),
                ("COLORMAP", bytes(range(256))),
            ]
        )
        setup = stage08.load_texture_setup_from_wad(wad)

        wrapped = stage.r_get_column_direct(wad, setup, 0, 3, {})
        composite = stage.r_get_column_direct(wad, setup, 1, 0, {})

        self.assertEqual(wrapped.texture_column, 1)
        self.assertEqual(wrapped.pixels, full_b)
        self.assertIsNone(wrapped.skip_reason)
        self.assertEqual(composite.skip_reason, "composite")
        self.assertIsNone(composite.pixels)

    def test_r_draw_column_stepping_against_synthetic_column(self) -> None:
        source = bytes(range(128))
        palette32 = tuple(index * 0x010101 for index in range(256))

        colors, signature = stage.r_draw_column_pixels(
            source,
            palette32,
            yl=99,
            yh=102,
            iscale=stage.FRACUNIT,
            texturemid=0,
        )

        self.assertEqual(colors, (0x7F7F7F, 0x000000, 0x010101, 0x020202))
        self.assertNotEqual(signature, stage.FNV_OFFSET_BASIS)

    def test_pinned_map_direct_wall_pixel_reference_counts(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_direct_wall_column_pixels_for_pinned_map(PINNED_WAD)

        self.assertEqual(ref.direct_wall_spans_considered, 86)
        self.assertEqual(ref.opaque_candidate_spans, 24)
        self.assertEqual(ref.direct_columns_attempted, 297)
        self.assertEqual(ref.columns_drawn, 162)
        self.assertEqual(ref.skipped_composite_columns, 135)
        self.assertEqual(ref.skipped_unsupported_wall_cases, 62)
        self.assertEqual(ref.skipped_texture0_spans, 0)
        self.assertEqual(ref.skipped_masked_midtexture_spans, 0)
        self.assertEqual(ref.skipped_nonopaque_columns, 0)
        self.assertEqual(ref.pixels_drawn, 15508)
        self.assertEqual(
            (ref.first_drawn_texture_id, ref.first_drawn_texture_name, ref.first_drawn_texture_column),
            (850, "AQRUST08", 127),
        )
        self.assertEqual(ref.framebuffer_signature, 2194105880)
        self.assertEqual((len(ref.direct_columns), len(ref.commands)), (134, 162))

    def test_executable_build_contains_direct_drawing_status_text_and_no_later_stage_strings(self) -> None:
        image = stage.build_source_stage09_direct_wall_column_pixels_debug_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage09_direct_wall_column_pixels_debug", image)
        self.assertIn(b"Direct wall column pixels debug OK", image)
        self.assertIn(b"R_GetColumn", image)
        self.assertIn(b"R_DrawColumn", image)
        self.assertIn(b" DWSP=", image)
        self.assertIn(b" SIG=", image)
        self.assertNotIn(b"R_GenerateComposite", image)
        self.assertNotIn(b"R_DrawColumnInCache", image)
        self.assertNotIn(b"visplane", image.lower())
        self.assertNotIn(b"sprite", image.lower())
        self.assertNotIn(b"masked wall drawing", image.lower())
        self.assertNotIn(b"source_stage10", image)
        self.assertNotIn(b"GCC:", image)
        self.assertNotIn(b"MinGW", image)
        self.assertNotIn(b"Microsoft Visual C", image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_direct_column_counts_pixel_signature_and_preserved_stage08_counts(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_direct_wall_column_pixels_for_pinned_map(PINNED_WAD)
        setup = ref.texture_data.texture_setup
        exe_path = REPO_ROOT / "build" / "source_stage09_direct_wall_column_pixels_debug.exe"
        stage.write_source_stage09_direct_wall_column_pixels_debug_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid)
            clip = ref.texture_data.projection.clip
            self.assertIn(f"VN={clip.visited_node_count}", title)
            self.assertIn(f"BVN={clip.bbox_visited_node_count}", title)
            self.assertIn(f"CLN={clip.clip_visited_node_count}", title)
            self.assertIn(f"CLSS={clip.clip_visited_subsector_count}", title)
            self.assertIn(f"CLSEG={clip.clip_visited_seg_count}", title)
            self.assertIn(f"SPAN={clip.stored_span_count}", title)
            self.assertIn(f"PRJ={len(ref.texture_data.projection.projected_spans)}", title)
            self.assertIn(f"TEX={setup.numtextures}", title)
            self.assertIn(f"PN={len(setup.patch_names)}", title)
            self.assertIn(f"FLAT={setup.numflats}", title)
            self.assertIn(f"DIRC={setup.direct_column_count}", title)
            self.assertIn(f"COMPC={setup.composite_column_count}", title)
            self.assertIn(f"FPTEX={ref.texture_data.first_projected_texture_id}", title)
            self.assertIn(f"LPTEX={ref.texture_data.last_projected_texture_id}", title)
            self.assertIn(f"DWSP={ref.direct_wall_spans_considered}", title)
            self.assertIn(f"OPQSP={ref.opaque_candidate_spans}", title)
            self.assertIn(f"DCOL={ref.direct_columns_attempted}", title)
            self.assertIn(f"DRAW={ref.columns_drawn}", title)
            self.assertIn(f"SKC={ref.skipped_composite_columns}", title)
            self.assertIn(f"SKU={ref.skipped_unsupported_wall_cases}", title)
            self.assertIn(f"ZTEX={ref.skipped_texture0_spans}", title)
            self.assertIn(f"MASK={ref.skipped_masked_midtexture_spans}", title)
            self.assertIn(f"FTEX={ref.first_drawn_texture_id}", title)
            self.assertIn(f"FN={ref.first_drawn_texture_name}", title)
            self.assertIn(f"FCOL={ref.first_drawn_texture_column}", title)
            self.assertIn(f"PIX={ref.pixels_drawn}", title)
            self.assertIn(f"SIG={ref.framebuffer_signature}", title)
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
