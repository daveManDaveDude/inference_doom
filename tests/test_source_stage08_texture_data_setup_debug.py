import os
import struct
import subprocess
import time
import unittest
from pathlib import Path

from tools import emit_source_stage08_texture_data_setup_debug as stage
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


def patch_lump(width: int, height: int = 16) -> bytes:
    return (
        struct.pack("<hhhh", width, height, 0, 0)
        + b"".join(struct.pack("<I", 8 + width * 4) for _ in range(width))
        + b"\xff"
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


class SourceStage08TextureDataSetupDebugTests(unittest.TestCase):
    def test_source_trace_covers_texture_setup_labels(self) -> None:
        labels = {entry[2] for entry in stage.SOURCE_TRACE}

        self.assertIn("render_init_texture_data_setup_debug", labels)
        self.assertIn("render_generate_lookup_metadata_debug", labels)
        self.assertIn("render_init_flats_debug", labels)
        self.assertIn("render_check_texture_num_for_name_debug", labels)
        self.assertIn("map_load_sidedefs_texture_ids_debug", labels)
        self.assertIn("map_load_sectors_flat_ids_debug", labels)

    def test_synthetic_pnames_texture1_and_optional_texture2_parse(self) -> None:
        wad = build_wad(
            [
                ("PATCHA", patch_lump(8)),
                ("PATCHB", patch_lump(4)),
                ("PNAMES", pnames_lump(["PATCHA", "PATCHB"])),
                ("TEXTURE1", texture_lump([("STARTAN1", 8, 32, [(0, 0, 0)])])),
                ("TEXTURE2", texture_lump([("EXITDOOR", 4, 64, [(0, 0, 1)])])),
                ("F_START", b""),
                ("FLAT1", b"\x00" * 4096),
                ("F_END", b""),
            ]
        )

        setup = stage.load_texture_setup_from_wad(wad)

        self.assertEqual(setup.numtextures, 2)
        self.assertEqual(setup.texture1_count, 1)
        self.assertEqual(setup.texture2_count, 1)
        self.assertTrue(setup.texture2_present)
        self.assertEqual(setup.patch_names, ("PATCHA", "PATCHB"))
        self.assertEqual(setup.textures[0].name, "STARTAN1")
        self.assertEqual((setup.textures[0].width, setup.textures[0].height), (8, 32))
        self.assertEqual(setup.textures[0].direct_columns, 8)
        self.assertEqual(setup.numflats, 1)

    def test_synthetic_texture_parser_rejects_bad_inputs_and_overflow(self) -> None:
        wad = build_wad(
            [
                ("PATCHA", patch_lump(8)),
                ("PNAMES", pnames_lump(["PATCHA"])),
                ("TEXTURE1", texture_lump([("WALL", 8, 32, [(0, 0, 0)])])),
                ("F_START", b""),
                ("FLAT1", b"\x00" * 4096),
                ("F_END", b""),
            ]
        )
        patch_names, patch_lumps = stage.parse_pnames(wad.read_lump("PNAMES"), wad)

        bad_directory = struct.pack("<ii", 1, 0)
        with self.assertRaises(stage.TextureFormatError):
            stage.parse_texture_lump(
                bad_directory,
                lump_name="TEXTURE1",
                wad=wad,
                patch_names=patch_names,
                patch_lumps=patch_lumps,
            )

        missing_patch_wad = build_wad(
            [
                ("PNAMES", pnames_lump(["MISSING"])),
                ("TEXTURE1", texture_lump([("WALL", 8, 32, [(0, 0, 0)])])),
                ("F_START", b""),
                ("FLAT1", b"\x00" * 4096),
                ("F_END", b""),
            ]
        )
        with self.assertRaises(stage.TextureFormatError):
            stage.load_texture_setup_from_wad(missing_patch_wad)

        with self.assertRaises(stage.TextureFormatError):
            stage.parse_texture_lump(
                texture_lump([("WALL", 8, 32, [(0, 0, 0)])]),
                lump_name="TEXTURE1",
                wad=wad,
                patch_names=patch_names,
                patch_lumps=patch_lumps,
                max_total_columns=4,
            )

    def test_check_texture_num_for_name_marker_missing_case_and_hash_scan(self) -> None:
        wad = build_wad(
            [
                ("PATCHA", patch_lump(8)),
                ("PNAMES", pnames_lump(["PATCHA"])),
                (
                    "TEXTURE1",
                    texture_lump(
                        [
                            ("FIRST", 8, 32, [(0, 0, 0)]),
                            ("DUPNAME", 8, 32, [(0, 0, 0)]),
                            ("DUPNAME", 8, 32, [(0, 0, 0)]),
                        ]
                    ),
                ),
                ("F_START", b""),
                ("FLAT1", b"\x00" * 4096),
                ("F_END", b""),
            ]
        )
        setup = stage.load_texture_setup_from_wad(wad)

        self.assertEqual(stage.r_check_texture_num_for_name(setup, "-"), 0)
        self.assertEqual(stage.r_check_texture_num_for_name(setup, "missing"), -1)
        self.assertEqual(stage.r_check_texture_num_for_name(setup, "first"), 0)
        self.assertEqual(stage.r_check_texture_num_for_name(setup, "dupname"), 1)
        key = stage.lump_name_hash("DUPNAME") % setup.numtextures
        self.assertEqual(setup.textures_hashtable[key], (1, 2))

    def test_pinned_map_texture_flat_resolution_and_preserved_projection_counters(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_texture_data_setup_for_pinned_map(PINNED_WAD)
        setup = ref.texture_setup

        self.assertEqual(setup.numtextures, 963)
        self.assertEqual(len(setup.patch_names), 1054)
        self.assertEqual(setup.texture1_count, 963)
        self.assertEqual(setup.texture2_count, 0)
        self.assertEqual(setup.numflats, 246)
        self.assertEqual((setup.direct_column_count, setup.composite_column_count), (80797, 26323))
        self.assertEqual((setup.textures[0].name, setup.textures[0].width, setup.textures[0].height), ("AASHITTY", 64, 64))
        self.assertEqual((setup.textures[-1].name, setup.textures[-1].width, setup.textures[-1].height), ("SAW2", 72, 128))

        self.assertEqual(ref.resolved_sidedefs[0], stage.ResolvedSideDefTextures(0, 0, 850))
        self.assertEqual(ref.resolved_sectors[0], stage.ResolvedSectorFlats(81, 113))
        self.assertEqual((ref.sidedef_texture_resolution_count, ref.sector_flat_resolution_count), (6123, 422))
        self.assertEqual((ref.first_projected_texture_id, ref.last_projected_texture_id), (850, 13))
        self.assertEqual((ref.first_projected_sidedef_id, ref.last_projected_sidedef_id), (3, 255))

        numeric_clip = ref.numeric_clip
        projection = ref.projection
        self.assertEqual(
            (
                numeric_clip.clip_visited_node_count,
                numeric_clip.clip_visited_subsector_count,
                numeric_clip.clip_visited_seg_count,
                numeric_clip.clip_bbox_cull_count,
                numeric_clip.backface_reject_count,
                numeric_clip.off_frustum_reject_count,
                numeric_clip.zero_pixel_reject_count,
                numeric_clip.solid_classification_count,
                numeric_clip.pass_classification_count,
                numeric_clip.empty_line_reject_count,
                numeric_clip.stored_span_count,
                numeric_clip.final_solidseg_count,
            ),
            (72, 56, 205, 17, 82, 17, 5, 30, 70, 1, 86, 1),
        )
        self.assertEqual(len(projection.projected_spans), 86)
        self.assertEqual((projection.min_distance, projection.max_distance), (2073560, 58720255))
        self.assertEqual((projection.min_scale, projection.max_scale), (11702, 108495))
        self.assertEqual(projection.first_projected_span, stage.stage07.ProjectedSpan(224, 255, 605, 0, 10485759, 65536, 65536, 0))
        self.assertEqual(projection.last_projected_span, stage.stage07.ProjectedSpan(143, 165, 855, 0, 58720255, 11702, 11702, 0))

    def test_executable_build_contains_texture_setup_status_text_and_no_later_stage_strings(self) -> None:
        image = stage.build_source_stage08_texture_data_setup_debug_exe()

        self.assertEqual(image[:2], b"MZ")
        self.assertIn(b"source_stage08_texture_data_setup_debug", image)
        self.assertIn(b"Texture data setup debug OK", image)
        self.assertIn(b"R_InitTextures", image)
        self.assertIn(b"R_GenerateLookup", image)
        self.assertIn(b" TEX=", image)
        self.assertNotIn(b"R_RenderSegLoop", image)
        self.assertNotIn(b"R_DrawColumn", image)
        self.assertNotIn(b"R_GetColumn", image)
        self.assertNotIn(b"R_GenerateComposite", image)
        self.assertNotIn(b"R_DrawColumnInCache", image)
        self.assertNotIn(b"R_InitColormaps", image)
        self.assertNotIn(b"R_InitLightTables", image)
        self.assertNotIn(b"source_stage09", image)
        self.assertNotIn(b"GCC:", image)
        self.assertNotIn(b"MinGW", image)
        self.assertNotIn(b"Microsoft Visual C", image)

    @unittest.skipUnless(os.name == "nt", "GUI smoke test requires Windows")
    def test_smoke_launch_reports_texture_setup_counts_and_preserved_stage07_counts(self) -> None:
        if not PINNED_WAD.exists():
            self.skipTest(f"pinned WAD missing: {PINNED_WAD}")

        ref = stage.reference_texture_data_setup_for_pinned_map(PINNED_WAD)
        setup = ref.texture_setup
        exe_path = REPO_ROOT / "build" / "source_stage08_texture_data_setup_debug.exe"
        stage.write_source_stage08_texture_data_setup_debug_exe(exe_path)

        process = subprocess.Popen([str(exe_path)], cwd=REPO_ROOT)
        hwnd = 0
        try:
            hwnd, title = window_title_for_pid(process.pid)
            clip = ref.projection.clip
            self.assertIn(f"VN={clip.visited_node_count}", title)
            self.assertIn(f"BVN={clip.bbox_visited_node_count}", title)
            self.assertIn(f"CLN={clip.clip_visited_node_count}", title)
            self.assertIn(f"CLSS={clip.clip_visited_subsector_count}", title)
            self.assertIn(f"CLSEG={clip.clip_visited_seg_count}", title)
            self.assertIn(f"SPAN={clip.stored_span_count}", title)
            self.assertIn(f"PRJ={len(ref.projection.projected_spans)}", title)
            self.assertIn(f"MIND={ref.projection.min_distance}", title)
            self.assertIn(f"MAXS={ref.projection.max_scale}", title)
            self.assertIn(f"TEX={setup.numtextures}", title)
            self.assertIn(f"PN={len(setup.patch_names)}", title)
            self.assertIn(f"FLAT={setup.numflats}", title)
            self.assertIn(f"DIRC={setup.direct_column_count}", title)
            self.assertIn(f"COMPC={setup.composite_column_count}", title)
            self.assertIn(f"FPTEX={ref.first_projected_texture_id}", title)
            self.assertIn(f"LPTEX={ref.last_projected_texture_id}", title)
            self.assertIn(f"EMID={ref.numeric_clip.empty_line_reject_count}", title)
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
