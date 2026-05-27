from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_stage06_raycast_view as ray
from tools import x86
from tools.map_loader import load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


KERNEL32 = "KERNEL32.dll"
USER32 = "USER32.dll"

CS_VREDRAW = 0x0001
CS_HREDRAW = 0x0002
COLOR_WINDOW = 5
CW_USEDEFAULT = 0x80000000
SW_SHOWNORMAL = 1
WM_TIMER_MILLISECONDS = 33
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_VISIBLE = 0x10000000
WINDOW_STYLE = WS_OVERLAPPEDWINDOW | WS_VISIBLE
WNDCLASSEXW_SIZE = 48
PAINTSTRUCT_SIZE = 64

GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_BEGIN = 0
INVALID_HANDLE_VALUE = 0xFFFFFFFF

FRAMEBUFFER_WIDTH = ray.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = ray.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = ray.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = ray.FRAMEBUFFER_BYTES
WINDOW_WIDTH = ray.WINDOW_WIDTH
WINDOW_HEIGHT = ray.WINDOW_HEIGHT

ANGLE_MASK = ray.ANGLE_MASK
RAY_MAX_DISTANCE = 8192
RAY_DISTANCE_SHIFT = 8

WAD_HEADER_SIZE = 12
WAD_DIRECTORY_ENTRY_SIZE = 16
IWAD_MAGIC = 0x44415749
PWAD_MAGIC = 0x44415750

THING_RECORD_SIZE = 10
VERTEX_RECORD_SIZE = 4
LINEDEF_RECORD_SIZE = 14
SIDEDEF_RECORD_SIZE = 30
THING_BUFFER_BYTES = 16 * 1024
VERTEX_BUFFER_BYTES = 64 * 1024
LINEDEF_BUFFER_BYTES = 128 * 1024
SIDEDEF_BUFFER_BYTES = 128 * 1024

WALL_TEXTURE_SIZE = 64
WALL_TEXTURE_COUNT = 32
WALL_TEXTURE_MASK = WALL_TEXTURE_COUNT - 1
WALL_TEXTURE_BYTES = WALL_TEXTURE_SIZE * WALL_TEXTURE_SIZE * 4
WALL_TEXTURE_ATLAS_BYTES = WALL_TEXTURE_COUNT * WALL_TEXTURE_BYTES
WALL_TEXTURE_BYTES_SHIFT = 14
WALL_TEXTURE_ROW_BYTES_SHIFT = 8
WALL_TEXTURE_V_SCALE = WALL_TEXTURE_SIZE << 16

MAP01_NAME0 = int.from_bytes(b"MAP0", "little")
MAP01_NAME1 = int.from_bytes(b"1\0\0\0", "little")
THINGS_NAME0 = int.from_bytes(b"THIN", "little")
THINGS_NAME1 = int.from_bytes(b"GS\0\0", "little")
LINEDEFS_NAME0 = int.from_bytes(b"LINE", "little")
LINEDEFS_NAME1 = int.from_bytes(b"DEFS", "little")
SIDEDEFS_NAME0 = int.from_bytes(b"SIDE", "little")
SIDEDEFS_NAME1 = int.from_bytes(b"DEFS", "little")
VERTEXES_NAME0 = int.from_bytes(b"VERT", "little")
VERTEXES_NAME1 = int.from_bytes(b"EXES", "little")
NO_SIDEDEF = 0xFFFF
NO_TEXTURE_NAME0 = int.from_bytes(b"-\0\0\0", "little")
NO_TEXTURE_NAME1 = 0

# Freedoom2 MAP01 bounds, padded slightly for a crude Phase 12 movement fence.
MAP_MIN_X = -512
MAP_MAX_X = 2432
MAP_MIN_Y = -2048
MAP_MAX_Y = 1792

PLAYER_START_X = -192
PLAYER_START_Y = -192
PLAYER_START_ANGLE = 0

COLOR_ERROR = 0x00200070
COLOR_WALL = 0x00B7C3BA

WINDOW_CLASS_NAME = "InferenceDoomStage07RealMapView"
WINDOW_TITLE = "Inference Doom - Stage 07 Real Map View"
WAD_PATH = r"third_party\freedoom\freedoom2.wad"


def fixed_wad_name(raw_name: bytes) -> str:
    return raw_name.split(b"\x00", 1)[0].decode("ascii", errors="ignore").upper()


def packed_texture_name(name: str) -> tuple[int, int]:
    encoded = name.upper().encode("ascii", errors="ignore")[:8]
    raw = encoded + b"\x00" * (8 - len(encoded))
    return int.from_bytes(raw[:4], "little"), int.from_bytes(raw[4:], "little")


def texture_slot_for_name(name: str) -> int:
    name0, name1 = packed_texture_name(name)
    value = (name0 ^ name1) & 0xFFFFFFFF
    value = (value ^ (value >> 16)) & 0xFFFFFFFF
    return (value & WALL_TEXTURE_MASK) + 1


def candidate_wad_paths() -> tuple[Path, ...]:
    return (
        Path(WAD_PATH),
        Path("build") / WAD_PATH,
        Path(__file__).resolve().parents[1] / WAD_PATH,
        Path(__file__).resolve().parents[1] / "build" / WAD_PATH,
    )


def find_wall_texture_wad() -> Path | None:
    for path in candidate_wad_paths():
        if path.exists():
            return path
    return None


def build_placeholder_wall_textures() -> bytes:
    base_palettes = (
        (0x00D8E0D5, 0x00B7C3BA, 0x006E8793),
        (0x00D7B48A, 0x009D7754, 0x00594334),
        (0x00BFC7D6, 0x00808CA8, 0x004C5571),
        (0x00C7D09A, 0x0087945C, 0x004C5936),
        (0x00D5A19A, 0x00A7635D, 0x0061333B),
        (0x00AEC7C5, 0x006E9999, 0x003A5A62),
        (0x00D2C0D6, 0x00907AA6, 0x00524770),
        (0x00C8C0A8, 0x00867F68, 0x004E493D),
    )

    def shade(color: int, delta: int) -> int:
        red = min(255, max(0, ((color >> 16) & 0xFF) + delta))
        green = min(255, max(0, ((color >> 8) & 0xFF) + delta))
        blue = min(255, max(0, (color & 0xFF) + delta))
        return (red << 16) | (green << 8) | blue

    data = bytearray()
    for texture_index in range(WALL_TEXTURE_COUNT):
        mortar, mid, dark = base_palettes[texture_index % len(base_palettes)]
        delta = ((texture_index // len(base_palettes)) - 1) * 18
        mortar = shade(mortar, delta)
        mid = shade(mid, delta)
        dark = shade(dark, delta)
        for y in range(WALL_TEXTURE_SIZE):
            row_shift = ((y // 16) & 1) * 16
            for x in range(WALL_TEXTURE_SIZE):
                brick_edge = (y & 15) == 0 or ((x + row_shift) & 31) == 0
                roughness = ((x * 3 + y * 5 + texture_index * 11) >> 3) & 3
                stripe = ((x // 8) ^ (y // 8) ^ texture_index) & 1
                if brick_edge:
                    color = mortar
                elif roughness == 0:
                    color = dark
                elif stripe:
                    color = mid
                else:
                    color = ((mid & 0x00FEFEFE) >> 1) + ((mortar & 0x00FEFEFE) >> 1)
                data.extend((color & 0xFFFFFFFF).to_bytes(4, "little"))
    return bytes(data)


def parse_pnames(wad: WadFile) -> list[str]:
    data = wad.read_lump("PNAMES")
    if len(data) < 4:
        return []
    count = struct.unpack_from("<i", data, 0)[0]
    names = []
    for index in range(max(0, count)):
        offset = 4 + index * 8
        if offset + 8 > len(data):
            break
        names.append(fixed_wad_name(data[offset : offset + 8]))
    return names


def parse_texture_lump(data: bytes) -> dict[str, tuple[int, int, tuple[tuple[int, int, int], ...]]]:
    if len(data) < 4:
        return {}
    count = struct.unpack_from("<i", data, 0)[0]
    textures = {}
    for index in range(max(0, count)):
        directory_offset = 4 + index * 4
        if directory_offset + 4 > len(data):
            break
        texture_offset = struct.unpack_from("<i", data, directory_offset)[0]
        if texture_offset < 0 or texture_offset + 22 > len(data):
            continue
        name = fixed_wad_name(data[texture_offset : texture_offset + 8])
        width, height, _column_directory, patch_count = struct.unpack_from(
            "<hhih", data, texture_offset + 12
        )
        if width <= 0 or height <= 0 or patch_count <= 0:
            continue
        patches = []
        patch_offset = texture_offset + 22
        for _patch_index in range(patch_count):
            if patch_offset + 10 > len(data):
                break
            origin_x, origin_y, patch_number, _stepdir, _colormap = struct.unpack_from(
                "<hhhhh", data, patch_offset
            )
            patches.append((origin_x, origin_y, patch_number))
            patch_offset += 10
        if patches:
            textures[name] = (width, height, tuple(patches))
    return textures


def load_texture_definitions(wad: WadFile) -> dict[str, tuple[int, int, tuple[tuple[int, int, int], ...]]]:
    textures = {}
    for lump_name in ("TEXTURE1", "TEXTURE2"):
        lump = wad.find_lump(lump_name)
        if lump is not None:
            textures.update(parse_texture_lump(wad.read_lump(lump)))
    return textures


def decode_patch_pixels(patch_data: bytes, palette: list[int]) -> tuple[int, int, list[int | None]] | None:
    if len(patch_data) < 8:
        return None
    width, height, _left, _top = struct.unpack_from("<hhhh", patch_data, 0)
    if width <= 0 or height <= 0 or width > 1024 or height > 1024:
        return None
    directory_end = 8 + width * 4
    if directory_end > len(patch_data):
        return None

    pixels: list[int | None] = [None] * (width * height)
    for x in range(width):
        column_offset = struct.unpack_from("<i", patch_data, 8 + x * 4)[0]
        if column_offset < 0 or column_offset >= len(patch_data):
            continue
        offset = column_offset
        while offset < len(patch_data):
            top_delta = patch_data[offset]
            offset += 1
            if top_delta == 0xFF:
                break
            if offset + 2 > len(patch_data):
                break
            length = patch_data[offset]
            offset += 2  # Skip length and unused byte.
            if offset + length + 1 > len(patch_data):
                break
            for y_offset in range(length):
                y = top_delta + y_offset
                if 0 <= y < height:
                    pixels[y * width + x] = palette[patch_data[offset + y_offset]]
            offset += length + 1
    return width, height, pixels


def compose_texture(
    wad: WadFile,
    pnames: list[str],
    texture: tuple[int, int, tuple[tuple[int, int, int], ...]],
    palette: list[int],
) -> list[int] | None:
    width, height, patches = texture
    composed: list[int | None] = [None] * (width * height)
    for origin_x, origin_y, patch_number in patches:
        if patch_number < 0 or patch_number >= len(pnames):
            continue
        lump = wad.find_lump(pnames[patch_number])
        if lump is None:
            continue
        decoded = decode_patch_pixels(wad.read_lump(lump), palette)
        if decoded is None:
            continue
        patch_width, patch_height, patch_pixels = decoded
        for patch_y in range(patch_height):
            target_y = origin_y + patch_y
            if target_y < 0 or target_y >= height:
                continue
            for patch_x in range(patch_width):
                target_x = origin_x + patch_x
                if target_x < 0 or target_x >= width:
                    continue
                color = patch_pixels[patch_y * patch_width + patch_x]
                if color is not None:
                    composed[target_y * width + target_x] = color

    if not any(pixel is not None for pixel in composed):
        return None

    fallback = 0x00505050
    scaled = []
    for y in range(WALL_TEXTURE_SIZE):
        source_y = min(height - 1, (y * height) // WALL_TEXTURE_SIZE)
        for x in range(WALL_TEXTURE_SIZE):
            source_x = min(width - 1, (x * width) // WALL_TEXTURE_SIZE)
            pixel = composed[source_y * width + source_x]
            scaled.append(fallback if pixel is None else pixel)
    return scaled


def used_wall_texture_names(wad_path: Path) -> tuple[str, ...]:
    loaded_map = load_map_from_file(wad_path, map_name="MAP01")
    names = []
    seen = set()
    for linedef in loaded_map.linedefs:
        if linedef.left_sidedef != NO_SIDEDEF:
            continue
        if linedef.right_sidedef >= len(loaded_map.sidedefs):
            continue
        name = loaded_map.sidedefs[linedef.right_sidedef].middle_texture.upper()
        if name and name != "-" and name not in seen:
            names.append(name)
            seen.add(name)
    return tuple(names)


def build_real_wall_texture_atlas(wad_path: Path) -> bytes | None:
    try:
        wad = WadFile.from_file(wad_path)
        playpal = wad.read_lump("PLAYPAL")
        if len(playpal) < 256 * 3:
            return None
        palette = [
            (playpal[index * 3] << 16)
            | (playpal[index * 3 + 1] << 8)
            | playpal[index * 3 + 2]
            for index in range(256)
        ]
        pnames = parse_pnames(wad)
        textures = load_texture_definitions(wad)
        names = used_wall_texture_names(wad_path)
    except (OSError, KeyError, ValueError, struct.error):
        return None

    atlas = bytearray(build_placeholder_wall_textures())
    filled_slots: set[int] = set()
    for name in names:
        slot_index = texture_slot_for_name(name) - 1
        if slot_index in filled_slots:
            continue
        texture = textures.get(name)
        if texture is None:
            continue
        composed = compose_texture(wad, pnames, texture, palette)
        if composed is None:
            continue
        offset = slot_index * WALL_TEXTURE_BYTES
        for pixel_index, color in enumerate(composed):
            atlas[offset + pixel_index * 4 : offset + pixel_index * 4 + 4] = (
                color & 0xFFFFFFFF
            ).to_bytes(4, "little")
        filled_slots.add(slot_index)

    return bytes(atlas) if filled_slots else None


def build_wall_texture_atlas() -> bytes:
    wad_path = find_wall_texture_wad()
    if wad_path is not None:
        real_atlas = build_real_wall_texture_atlas(wad_path)
        if real_atlas is not None:
            return real_atlas
    return build_placeholder_wall_textures()


PLACEHOLDER_WALL_TEXTURES = build_wall_texture_atlas()
if len(PLACEHOLDER_WALL_TEXTURES) != WALL_TEXTURE_ATLAS_BYTES:
    raise AssertionError("generated wall texture atlas has the wrong size")


def mov_reg_ptr_reg_disp8(pe: PE32, dst: str, base: str, displacement: int) -> None:
    pe.emit(bytes([0x8B, ray.x86.modrm(1, dst, base), displacement & 0xFF]))


def movzx_reg_word_ptr_reg(pe: PE32, dst: str, base: str) -> None:
    pe.emit(bytes([0x0F, 0xB7, ray.x86.modrm(0, dst, base)]))


def movzx_reg_word_ptr_reg_disp8(
    pe: PE32, dst: str, base: str, displacement: int
) -> None:
    pe.emit(bytes([0x0F, 0xB7, ray.x86.modrm(1, dst, base), displacement & 0xFF]))


def movsx_reg_word_ptr_reg(pe: PE32, dst: str, base: str) -> None:
    pe.emit(bytes([0x0F, 0xBF, ray.x86.modrm(0, dst, base)]))


def movsx_reg_word_ptr_reg_disp8(
    pe: PE32, dst: str, base: str, displacement: int
) -> None:
    pe.emit(bytes([0x0F, 0xBF, ray.x86.modrm(1, dst, base), displacement & 0xFF]))


def cmp_reg_reg(pe: PE32, left: str, right: str) -> None:
    pe.emit(bytes([0x39, ray.x86.modrm(3, right, left)]))


def add_mem_abs32_reg(pe: PE32, label: str, reg: str) -> None:
    pe.emit(bytes([0x01, ray.x86.modrm(0, reg, 5)]))
    pe.write_abs32(label)


def jl_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x8C")
    pe.write_rel32(label)


def jg_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x8F")
    pe.write_rel32(label)


def ja_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x87")
    pe.write_rel32(label)


def neg_reg(pe: PE32, reg: str) -> None:
    pe.emit(bytes([0xF7, ray.x86.modrm(3, 3, reg)]))


def dec_mem_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\xFF\x0D")
    pe.write_abs32(label)


def emit_entry(pe: PE32) -> None:
    pe.label("entry")

    x86.push_imm8(pe, 0)
    x86.call_import(pe, KERNEL32, "GetModuleHandleW")
    ray.mov_mem_abs32_eax(pe, "wc_hInstance")

    ray.push_abs32(pe, "window_class")
    x86.call_import(pe, USER32, "RegisterClassExW")
    ray.test_eax_eax(pe)
    ray.jne_rel32(pe, "class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("class_registered")
    x86.call_rel32(pe, "load_map_data")
    x86.call_rel32(pe, "render_scene")

    x86.push_imm8(pe, 0)  # lpParam
    ray.push_mem_abs32(pe, "wc_hInstance")
    x86.push_imm8(pe, 0)  # hMenu
    x86.push_imm8(pe, 0)  # hWndParent
    x86.push_imm32(pe, WINDOW_HEIGHT)
    x86.push_imm32(pe, WINDOW_WIDTH)
    x86.push_imm32(pe, CW_USEDEFAULT)
    x86.push_imm32(pe, CW_USEDEFAULT)
    x86.push_imm32(pe, WINDOW_STYLE)
    ray.push_abs32(pe, "window_title")
    ray.push_abs32(pe, "class_name")
    x86.push_imm8(pe, 0)  # dwExStyle
    x86.call_import(pe, USER32, "CreateWindowExW")
    ray.test_eax_eax(pe)
    ray.jne_rel32(pe, "window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("window_created")
    ray.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_imm8(pe, SW_SHOWNORMAL)
    ray.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, USER32, "ShowWindow")
    ray.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, USER32, "UpdateWindow")

    x86.push_imm8(pe, 0)  # lpTimerFunc
    x86.push_imm8(pe, WM_TIMER_MILLISECONDS)  # uElapse
    x86.push_imm8(pe, 1)  # nIDEvent
    ray.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, USER32, "SetTimer")
    ray.test_eax_eax(pe)
    ray.jne_rel32(pe, "timer_created")
    x86.push_imm8(pe, 4)
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("timer_created")
    pe.label("message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    ray.push_abs32(pe, "message")
    x86.call_import(pe, USER32, "GetMessageW")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "clean_exit")
    ray.cmp_eax_imm32(pe, 0xFFFFFFFF)
    ray.je_rel32(pe, "message_error")

    ray.push_abs32(pe, "message")
    x86.call_import(pe, USER32, "TranslateMessage")
    ray.push_abs32(pe, "message")
    x86.call_import(pe, USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "message_loop")

    pe.label("clean_exit")
    ray.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, KERNEL32, "ExitProcess")


def emit_load_map_data(pe: PE32) -> None:
    pe.label("load_map_data")
    ray.mov_mem_abs32_imm32(pe, "map_loaded", 0)
    ray.mov_mem_abs32_imm32(pe, "player_start_found", 0)

    x86.push_imm8(pe, 0)  # hTemplateFile
    x86.push_imm32(pe, FILE_ATTRIBUTE_NORMAL)
    x86.push_imm32(pe, OPEN_EXISTING)
    x86.push_imm8(pe, 0)  # lpSecurityAttributes
    x86.push_imm32(pe, FILE_SHARE_READ)
    x86.push_imm32(pe, GENERIC_READ)
    ray.push_abs32(pe, "wad_path_w")
    x86.call_import(pe, KERNEL32, "CreateFileW")
    ray.cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    ray.jne_rel32(pe, "map_file_opened")
    x86.ret(pe)

    pe.label("map_file_opened")
    ray.mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)  # lpOverlapped
    ray.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, WAD_HEADER_SIZE)
    ray.push_abs32(pe, "wad_header")
    ray.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "load_close_and_return")
    ray.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    ray.cmp_eax_imm32(pe, WAD_HEADER_SIZE)
    ray.jne_rel32(pe, "load_close_and_return")

    ray.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    ray.cmp_eax_imm32(pe, IWAD_MAGIC)
    ray.je_rel32(pe, "map_magic_ok")
    ray.cmp_eax_imm32(pe, PWAD_MAGIC)
    ray.jne_rel32(pe, "load_close_and_return")

    pe.label("map_magic_ok")
    ray.mov_reg_mem_abs32(pe, "eax", "wad_lump_count")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "load_close_and_return")
    ray.mov_reg_mem_abs32(pe, "eax", "wad_directory_offset")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "load_close_and_return")

    x86.push_imm32(pe, FILE_BEGIN)
    x86.push_imm8(pe, 0)  # lpDistanceToMoveHigh
    ray.push_mem_abs32(pe, "wad_directory_offset")
    ray.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "SetFilePointer")
    ray.cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    ray.je_rel32(pe, "load_close_and_return")

    ray.mov_reg_mem_abs32(pe, "eax", "wad_lump_count")
    ray.mov_mem_abs32_eax(pe, "directory_entries_remaining")

    pe.label("directory_scan_loop")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_entries_remaining")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "directory_scan_done")

    x86.push_imm8(pe, 0)  # lpOverlapped
    ray.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, WAD_DIRECTORY_ENTRY_SIZE)
    ray.push_abs32(pe, "directory_entry")
    ray.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "load_close_and_return")
    ray.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    ray.cmp_eax_imm32(pe, WAD_DIRECTORY_ENTRY_SIZE)
    ray.jne_rel32(pe, "load_close_and_return")

    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_name0")
    ray.cmp_eax_imm32(pe, MAP01_NAME0)
    ray.jne_rel32(pe, "check_map_lump_names")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_name1")
    ray.cmp_eax_imm32(pe, MAP01_NAME1)
    ray.jne_rel32(pe, "check_map_lump_names")
    ray.mov_mem_abs32_imm32(pe, "map_scan_active", 1)
    x86.jmp_rel32(pe, "directory_next_entry")

    pe.label("check_map_lump_names")
    ray.mov_reg_mem_abs32(pe, "eax", "map_scan_active")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "directory_next_entry")

    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_name0")
    ray.cmp_eax_imm32(pe, THINGS_NAME0)
    ray.jne_rel32(pe, "check_linedefs_name")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_name1")
    ray.cmp_eax_imm32(pe, THINGS_NAME1)
    ray.jne_rel32(pe, "check_linedefs_name")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_offset")
    ray.mov_mem_abs32_eax(pe, "things_offset")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_size")
    ray.mov_mem_abs32_eax(pe, "things_size")
    ray.mov_mem_abs32_imm32(pe, "things_found", 1)
    x86.jmp_rel32(pe, "check_lumps_complete")

    pe.label("check_linedefs_name")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_name0")
    ray.cmp_eax_imm32(pe, LINEDEFS_NAME0)
    ray.jne_rel32(pe, "check_sidedefs_name")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_name1")
    ray.cmp_eax_imm32(pe, LINEDEFS_NAME1)
    ray.jne_rel32(pe, "check_sidedefs_name")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_offset")
    ray.mov_mem_abs32_eax(pe, "linedefs_offset")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_size")
    ray.mov_mem_abs32_eax(pe, "linedefs_size")
    ray.mov_mem_abs32_imm32(pe, "linedefs_found", 1)
    x86.jmp_rel32(pe, "check_lumps_complete")

    pe.label("check_sidedefs_name")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_name0")
    ray.cmp_eax_imm32(pe, SIDEDEFS_NAME0)
    ray.jne_rel32(pe, "check_vertexes_name")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_name1")
    ray.cmp_eax_imm32(pe, SIDEDEFS_NAME1)
    ray.jne_rel32(pe, "check_vertexes_name")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_offset")
    ray.mov_mem_abs32_eax(pe, "sidedefs_offset")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_size")
    ray.mov_mem_abs32_eax(pe, "sidedefs_size")
    ray.mov_mem_abs32_imm32(pe, "sidedefs_found", 1)
    x86.jmp_rel32(pe, "check_lumps_complete")

    pe.label("check_vertexes_name")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_name0")
    ray.cmp_eax_imm32(pe, VERTEXES_NAME0)
    ray.jne_rel32(pe, "check_lumps_complete")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_name1")
    ray.cmp_eax_imm32(pe, VERTEXES_NAME1)
    ray.jne_rel32(pe, "check_lumps_complete")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_offset")
    ray.mov_mem_abs32_eax(pe, "vertexes_offset")
    ray.mov_reg_mem_abs32(pe, "eax", "directory_lump_size")
    ray.mov_mem_abs32_eax(pe, "vertexes_size")
    ray.mov_mem_abs32_imm32(pe, "vertexes_found", 1)

    pe.label("check_lumps_complete")
    ray.mov_reg_mem_abs32(pe, "eax", "things_found")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "directory_next_entry")
    ray.mov_reg_mem_abs32(pe, "eax", "linedefs_found")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "directory_next_entry")
    ray.mov_reg_mem_abs32(pe, "eax", "sidedefs_found")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "directory_next_entry")
    ray.mov_reg_mem_abs32(pe, "eax", "vertexes_found")
    ray.test_eax_eax(pe)
    ray.jne_rel32(pe, "directory_scan_done")

    pe.label("directory_next_entry")
    dec_mem_abs32(pe, "directory_entries_remaining")
    x86.jmp_rel32(pe, "directory_scan_loop")

    pe.label("directory_scan_done")
    ray.mov_reg_mem_abs32(pe, "eax", "things_found")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "load_close_and_return")
    ray.mov_reg_mem_abs32(pe, "eax", "linedefs_found")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "load_close_and_return")
    ray.mov_reg_mem_abs32(pe, "eax", "sidedefs_found")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "load_close_and_return")
    ray.mov_reg_mem_abs32(pe, "eax", "vertexes_found")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "load_close_and_return")

    x86.call_rel32(pe, "validate_map_lump_sizes")
    ray.mov_reg_mem_abs32(pe, "eax", "map_lumps_valid")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "load_close_and_return")

    x86.call_rel32(pe, "read_map_lumps")
    ray.mov_reg_mem_abs32(pe, "eax", "map_lumps_read")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "load_close_and_return")

    x86.call_rel32(pe, "init_player_from_things")
    ray.mov_reg_mem_abs32(pe, "eax", "player_start_found")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "load_close_and_return")
    ray.mov_mem_abs32_imm32(pe, "map_loaded", 1)

    pe.label("load_close_and_return")
    ray.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_validate_map_lump_sizes(pe: PE32) -> None:
    pe.label("validate_map_lump_sizes")
    ray.mov_mem_abs32_imm32(pe, "map_lumps_valid", 0)

    ray.mov_reg_mem_abs32(pe, "eax", "vertexes_size")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "validate_done")
    ray.cmp_reg_imm32(pe, "eax", VERTEX_BUFFER_BYTES)
    ja_rel32(pe, "validate_done")
    ray.mov_reg_reg(pe, "edx", "eax")
    ray.and_reg_imm32(pe, "edx", VERTEX_RECORD_SIZE - 1)
    ray.test_reg_reg(pe, "edx")
    ray.jne_rel32(pe, "validate_done")
    ray.shr_reg_imm8(pe, "eax", 2)
    ray.mov_mem_abs32_eax(pe, "vertex_count")

    ray.mov_reg_mem_abs32(pe, "eax", "linedefs_size")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "validate_done")
    ray.cmp_reg_imm32(pe, "eax", LINEDEF_BUFFER_BYTES)
    ja_rel32(pe, "validate_done")
    ray.xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "ecx", LINEDEF_RECORD_SIZE)
    ray.div_ecx(pe)
    ray.test_reg_reg(pe, "edx")
    ray.jne_rel32(pe, "validate_done")
    ray.mov_mem_abs32_eax(pe, "linedef_count")

    ray.mov_reg_mem_abs32(pe, "eax", "sidedefs_size")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "validate_done")
    ray.cmp_reg_imm32(pe, "eax", SIDEDEF_BUFFER_BYTES)
    ja_rel32(pe, "validate_done")
    ray.xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "ecx", SIDEDEF_RECORD_SIZE)
    ray.div_ecx(pe)
    ray.test_reg_reg(pe, "edx")
    ray.jne_rel32(pe, "validate_done")
    ray.mov_mem_abs32_eax(pe, "sidedef_count")

    ray.mov_reg_mem_abs32(pe, "eax", "things_size")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "validate_done")
    ray.cmp_reg_imm32(pe, "eax", THING_BUFFER_BYTES)
    ja_rel32(pe, "validate_done")
    ray.xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "ecx", THING_RECORD_SIZE)
    ray.div_ecx(pe)
    ray.test_reg_reg(pe, "edx")
    ray.jne_rel32(pe, "validate_done")
    ray.mov_mem_abs32_eax(pe, "thing_count")

    ray.mov_mem_abs32_imm32(pe, "map_lumps_valid", 1)

    pe.label("validate_done")
    x86.ret(pe)


def emit_read_map_lumps(pe: PE32) -> None:
    pe.label("read_map_lumps")
    ray.mov_mem_abs32_imm32(pe, "map_lumps_read", 0)

    x86.push_imm32(pe, FILE_BEGIN)
    x86.push_imm8(pe, 0)
    ray.push_mem_abs32(pe, "vertexes_offset")
    ray.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "SetFilePointer")
    ray.cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    ray.je_rel32(pe, "read_lumps_done")

    x86.push_imm8(pe, 0)
    ray.push_abs32(pe, "bytes_read")
    ray.push_mem_abs32(pe, "vertexes_size")
    ray.push_abs32(pe, "vertexes_buffer")
    ray.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "read_lumps_done")
    ray.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    ray.cmp_reg_mem_abs32(pe, "eax", "vertexes_size")
    ray.jne_rel32(pe, "read_lumps_done")

    x86.push_imm32(pe, FILE_BEGIN)
    x86.push_imm8(pe, 0)
    ray.push_mem_abs32(pe, "linedefs_offset")
    ray.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "SetFilePointer")
    ray.cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    ray.je_rel32(pe, "read_lumps_done")

    x86.push_imm8(pe, 0)
    ray.push_abs32(pe, "bytes_read")
    ray.push_mem_abs32(pe, "linedefs_size")
    ray.push_abs32(pe, "linedefs_buffer")
    ray.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "read_lumps_done")
    ray.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    ray.cmp_reg_mem_abs32(pe, "eax", "linedefs_size")
    ray.jne_rel32(pe, "read_lumps_done")

    x86.push_imm32(pe, FILE_BEGIN)
    x86.push_imm8(pe, 0)
    ray.push_mem_abs32(pe, "sidedefs_offset")
    ray.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "SetFilePointer")
    ray.cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    ray.je_rel32(pe, "read_lumps_done")

    x86.push_imm8(pe, 0)
    ray.push_abs32(pe, "bytes_read")
    ray.push_mem_abs32(pe, "sidedefs_size")
    ray.push_abs32(pe, "sidedefs_buffer")
    ray.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "read_lumps_done")
    ray.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    ray.cmp_reg_mem_abs32(pe, "eax", "sidedefs_size")
    ray.jne_rel32(pe, "read_lumps_done")

    x86.push_imm32(pe, FILE_BEGIN)
    x86.push_imm8(pe, 0)
    ray.push_mem_abs32(pe, "things_offset")
    ray.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "SetFilePointer")
    ray.cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    ray.je_rel32(pe, "read_lumps_done")

    x86.push_imm8(pe, 0)
    ray.push_abs32(pe, "bytes_read")
    ray.push_mem_abs32(pe, "things_size")
    ray.push_abs32(pe, "things_buffer")
    ray.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "read_lumps_done")
    ray.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    ray.cmp_reg_mem_abs32(pe, "eax", "things_size")
    ray.jne_rel32(pe, "read_lumps_done")

    ray.mov_mem_abs32_imm32(pe, "map_lumps_read", 1)

    pe.label("read_lumps_done")
    x86.ret(pe)


def emit_init_player_from_things(pe: PE32) -> None:
    pe.label("init_player_from_things")
    ray.push_reg(pe, "ecx")
    ray.push_reg(pe, "esi")

    ray.mov_reg_abs32(pe, "esi", "things_buffer")
    ray.mov_reg_mem_abs32(pe, "ecx", "thing_count")
    ray.test_reg_reg(pe, "ecx")
    ray.je_rel32(pe, "init_player_done")

    pe.label("thing_scan_loop")
    movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 6)
    ray.cmp_eax_imm32(pe, 1)
    ray.je_rel32(pe, "thing_player_found")
    ray.cmp_eax_imm32(pe, 2)
    ray.je_rel32(pe, "thing_player_found")
    ray.cmp_eax_imm32(pe, 3)
    ray.je_rel32(pe, "thing_player_found")
    ray.cmp_eax_imm32(pe, 4)
    ray.je_rel32(pe, "thing_player_found")

    ray.add_reg_imm32(pe, "esi", THING_RECORD_SIZE)
    ray.dec_reg(pe, "ecx")
    ray.jne_rel32(pe, "thing_scan_loop")
    x86.jmp_rel32(pe, "init_player_done")

    pe.label("thing_player_found")
    movsx_reg_word_ptr_reg(pe, "eax", "esi")
    ray.mov_mem_abs32_eax(pe, "player_x")
    ray.mov_mem_abs32_eax(pe, "candidate_x")
    movsx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 2)
    ray.mov_mem_abs32_eax(pe, "player_y")
    ray.mov_mem_abs32_eax(pe, "candidate_y")

    movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 4)
    ray.shl_reg_imm8(pe, "eax", 8)
    ray.xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "ecx", 360)
    ray.div_ecx(pe)
    ray.and_reg_imm32(pe, "eax", ANGLE_MASK)
    ray.mov_mem_abs32_eax(pe, "player_angle")
    ray.mov_mem_abs32_imm32(pe, "player_start_found", 1)

    pe.label("init_player_done")
    ray.pop_reg(pe, "esi")
    ray.pop_reg(pe, "ecx")
    x86.ret(pe)


def emit_try_commit_move(pe: PE32) -> None:
    pe.label("try_commit_move")

    ray.mov_reg_mem_abs32(pe, "eax", "candidate_x")
    ray.cmp_reg_imm32(pe, "eax", MAP_MIN_X)
    jl_rel32(pe, "try_commit_done")
    ray.cmp_reg_imm32(pe, "eax", MAP_MAX_X)
    jg_rel32(pe, "try_commit_done")

    ray.mov_reg_mem_abs32(pe, "eax", "candidate_y")
    ray.cmp_reg_imm32(pe, "eax", MAP_MIN_Y)
    jl_rel32(pe, "try_commit_done")
    ray.cmp_reg_imm32(pe, "eax", MAP_MAX_Y)
    jg_rel32(pe, "try_commit_done")

    ray.mov_reg_mem_abs32(pe, "eax", "candidate_x")
    ray.mov_mem_abs32_eax(pe, "player_x")
    ray.mov_reg_mem_abs32(pe, "eax", "candidate_y")
    ray.mov_mem_abs32_eax(pe, "player_y")

    pe.label("try_commit_done")
    x86.ret(pe)


def emit_render_scene(pe: PE32) -> None:
    pe.label("render_scene")
    ray.mov_reg_mem_abs32(pe, "eax", "map_loaded")
    ray.test_eax_eax(pe)
    ray.jne_rel32(pe, "render_have_map")
    x86.call_rel32(pe, "render_error_pattern")
    x86.ret(pe)

    pe.label("render_have_map")
    ray.push_reg(pe, "ebx")
    ray.push_reg(pe, "ecx")
    ray.push_reg(pe, "edx")
    ray.push_reg(pe, "esi")
    ray.push_reg(pe, "edi")

    x86.call_rel32(pe, "clear_view")

    ray.xor_reg_reg(pe, "ebx", "ebx")
    pe.label("render_column_loop")
    ray.mov_mem_abs32_reg(pe, "ray_column", "ebx")

    ray.mov_reg_abs32(pe, "esi", "angle_offsets")
    ray.add_reg_reg(pe, "esi", "ebx")
    ray.movzx_reg_byte_ptr_reg(pe, "eax", "esi")
    ray.add_reg_mem_abs32(pe, "eax", "player_angle")
    ray.and_reg_imm32(pe, "eax", ANGLE_MASK)
    ray.mov_mem_abs32_eax(pe, "ray_angle")

    x86.call_rel32(pe, "cast_ray")
    x86.call_rel32(pe, "draw_wall_column")

    ray.inc_reg(pe, "ebx")
    ray.cmp_reg_imm32(pe, "ebx", FRAMEBUFFER_WIDTH)
    ray.jne_rel32(pe, "render_column_loop")

    ray.pop_reg(pe, "edi")
    ray.pop_reg(pe, "esi")
    ray.pop_reg(pe, "edx")
    ray.pop_reg(pe, "ecx")
    ray.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_render_error_pattern(pe: PE32) -> None:
    pe.label("render_error_pattern")
    ray.push_reg(pe, "edi")
    pe.emit(b"\xFC")  # cld
    ray.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.mov_reg_imm32(pe, "eax", COLOR_ERROR)
    x86.mov_reg_imm32(pe, "ecx", FRAMEBUFFER_PIXELS)
    pe.emit(b"\xF3\xAB")  # rep stosd
    ray.pop_reg(pe, "edi")
    x86.ret(pe)


def emit_cast_ray(pe: PE32) -> None:
    pe.label("cast_ray")
    ray.push_reg(pe, "ebx")
    ray.push_reg(pe, "ecx")
    ray.push_reg(pe, "edx")
    ray.push_reg(pe, "esi")
    ray.push_reg(pe, "edi")

    ray.mov_mem_abs32_imm32(pe, "ray_distance", RAY_MAX_DISTANCE)
    ray.mov_mem_abs32_imm32(pe, "ray_hit_tile", 0)
    ray.mov_mem_abs32_imm32(pe, "ray_hit_color", COLOR_WALL)
    ray.mov_mem_abs32_imm32(pe, "ray_hit_texture", 0)
    ray.mov_mem_abs32_imm32(pe, "ray_texture_x", 0)
    ray.mov_mem_abs32_imm32(pe, "ray_texture_name0", 0)
    ray.mov_mem_abs32_imm32(pe, "ray_texture_name1", 0)

    ray.emit_load_trig_value(pe, "cos_table", "ray_angle", "eax")
    ray.mov_mem_abs32_eax(pe, "ray_dx")
    ray.emit_load_trig_value(pe, "sin_table", "ray_angle", "eax")
    ray.mov_mem_abs32_eax(pe, "ray_dy")

    ray.mov_reg_abs32(pe, "esi", "linedefs_buffer")
    ray.mov_mem_abs32_reg(pe, "linedef_scan_ptr", "esi")
    ray.mov_reg_mem_abs32(pe, "eax", "linedef_count")
    ray.mov_mem_abs32_eax(pe, "linedefs_remaining")

    pe.label("cast_linedef_loop")
    ray.mov_reg_mem_abs32(pe, "eax", "linedefs_remaining")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "cast_ray_done")

    ray.mov_reg_mem_abs32(pe, "esi", "linedef_scan_ptr")

    movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 12)
    ray.cmp_eax_imm32(pe, NO_SIDEDEF)
    ray.jne_rel32(pe, "cast_linedef_skip")

    movzx_reg_word_ptr_reg(pe, "eax", "esi")
    ray.cmp_reg_mem_abs32(pe, "eax", "vertex_count")
    ray.jae_rel32(pe, "cast_linedef_skip")
    ray.mov_reg_reg(pe, "ebx", "eax")
    ray.shl_reg_imm8(pe, "ebx", 2)
    ray.mov_reg_abs32(pe, "edi", "vertexes_buffer")
    ray.add_reg_reg(pe, "edi", "ebx")
    movsx_reg_word_ptr_reg(pe, "eax", "edi")
    ray.mov_mem_abs32_eax(pe, "seg_x0")
    movsx_reg_word_ptr_reg_disp8(pe, "eax", "edi", 2)
    ray.mov_mem_abs32_eax(pe, "seg_y0")

    movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 2)
    ray.cmp_reg_mem_abs32(pe, "eax", "vertex_count")
    ray.jae_rel32(pe, "cast_linedef_skip")
    ray.mov_reg_reg(pe, "ebx", "eax")
    ray.shl_reg_imm8(pe, "ebx", 2)
    ray.mov_reg_abs32(pe, "edi", "vertexes_buffer")
    ray.add_reg_reg(pe, "edi", "ebx")
    movsx_reg_word_ptr_reg(pe, "eax", "edi")
    ray.mov_mem_abs32_eax(pe, "seg_x1")
    movsx_reg_word_ptr_reg_disp8(pe, "eax", "edi", 2)
    ray.mov_mem_abs32_eax(pe, "seg_y1")

    ray.mov_reg_mem_abs32(pe, "eax", "seg_x1")
    ray.mov_reg_mem_abs32(pe, "ebx", "seg_x0")
    ray.sub_reg_reg(pe, "eax", "ebx")
    ray.mov_mem_abs32_eax(pe, "seg_dx")

    ray.mov_reg_mem_abs32(pe, "eax", "seg_y1")
    ray.mov_reg_mem_abs32(pe, "ebx", "seg_y0")
    ray.sub_reg_reg(pe, "eax", "ebx")
    ray.mov_mem_abs32_eax(pe, "seg_dy")

    ray.mov_reg_mem_abs32(pe, "eax", "seg_x0")
    ray.mov_reg_mem_abs32(pe, "ebx", "player_x")
    ray.sub_reg_reg(pe, "eax", "ebx")
    ray.mov_mem_abs32_eax(pe, "rel_x")

    ray.mov_reg_mem_abs32(pe, "eax", "seg_y0")
    ray.mov_reg_mem_abs32(pe, "ebx", "player_y")
    ray.sub_reg_reg(pe, "eax", "ebx")
    ray.mov_mem_abs32_eax(pe, "rel_y")

    ray.mov_reg_mem_abs32(pe, "eax", "ray_dx")
    ray.mov_reg_mem_abs32(pe, "ecx", "seg_dy")
    ray.imul_reg_reg(pe, "eax", "ecx")
    ray.mov_mem_abs32_eax(pe, "intersection_tmp")
    ray.mov_reg_mem_abs32(pe, "eax", "ray_dy")
    ray.mov_reg_mem_abs32(pe, "ecx", "seg_dx")
    ray.imul_reg_reg(pe, "eax", "ecx")
    ray.mov_reg_mem_abs32(pe, "edx", "intersection_tmp")
    ray.sub_reg_reg(pe, "edx", "eax")
    ray.mov_mem_abs32_reg(pe, "intersection_denom", "edx")
    ray.test_reg_reg(pe, "edx")
    ray.je_rel32(pe, "cast_linedef_skip")

    ray.mov_reg_mem_abs32(pe, "eax", "rel_x")
    ray.mov_reg_mem_abs32(pe, "ecx", "seg_dy")
    ray.imul_reg_reg(pe, "eax", "ecx")
    ray.mov_mem_abs32_eax(pe, "intersection_tmp")
    ray.mov_reg_mem_abs32(pe, "eax", "rel_y")
    ray.mov_reg_mem_abs32(pe, "ecx", "seg_dx")
    ray.imul_reg_reg(pe, "eax", "ecx")
    ray.mov_reg_mem_abs32(pe, "edx", "intersection_tmp")
    ray.sub_reg_reg(pe, "edx", "eax")
    ray.mov_mem_abs32_reg(pe, "intersection_tnum", "edx")

    ray.mov_reg_mem_abs32(pe, "eax", "rel_x")
    ray.mov_reg_mem_abs32(pe, "ecx", "ray_dy")
    ray.imul_reg_reg(pe, "eax", "ecx")
    ray.mov_mem_abs32_eax(pe, "intersection_tmp")
    ray.mov_reg_mem_abs32(pe, "eax", "rel_y")
    ray.mov_reg_mem_abs32(pe, "ecx", "ray_dx")
    ray.imul_reg_reg(pe, "eax", "ecx")
    ray.mov_reg_mem_abs32(pe, "edx", "intersection_tmp")
    ray.sub_reg_reg(pe, "edx", "eax")
    ray.mov_mem_abs32_reg(pe, "intersection_unum", "edx")

    ray.mov_reg_mem_abs32(pe, "eax", "intersection_denom")
    ray.test_eax_eax(pe)
    jl_rel32(pe, "cast_denom_negative")

    ray.mov_reg_mem_abs32(pe, "eax", "intersection_tnum")
    ray.test_eax_eax(pe)
    jl_rel32(pe, "cast_linedef_skip")
    ray.mov_reg_mem_abs32(pe, "eax", "intersection_unum")
    ray.test_eax_eax(pe)
    jl_rel32(pe, "cast_linedef_skip")
    ray.cmp_reg_mem_abs32(pe, "eax", "intersection_denom")
    jg_rel32(pe, "cast_linedef_skip")
    ray.mov_mem_abs32_eax(pe, "texture_numerator")
    ray.mov_reg_mem_abs32(pe, "eax", "intersection_tnum")
    ray.mov_mem_abs32_eax(pe, "distance_numerator")
    ray.mov_reg_mem_abs32(pe, "eax", "intersection_denom")
    ray.mov_mem_abs32_eax(pe, "distance_denominator")
    x86.jmp_rel32(pe, "cast_compute_distance")

    pe.label("cast_denom_negative")
    ray.mov_reg_mem_abs32(pe, "eax", "intersection_tnum")
    ray.test_eax_eax(pe)
    jg_rel32(pe, "cast_linedef_skip")
    ray.mov_reg_mem_abs32(pe, "eax", "intersection_unum")
    ray.test_eax_eax(pe)
    jg_rel32(pe, "cast_linedef_skip")
    ray.cmp_reg_mem_abs32(pe, "eax", "intersection_denom")
    jl_rel32(pe, "cast_linedef_skip")
    neg_reg(pe, "eax")
    ray.mov_mem_abs32_eax(pe, "texture_numerator")
    ray.mov_reg_mem_abs32(pe, "eax", "intersection_tnum")
    neg_reg(pe, "eax")
    ray.mov_mem_abs32_eax(pe, "distance_numerator")
    ray.mov_reg_mem_abs32(pe, "eax", "intersection_denom")
    neg_reg(pe, "eax")
    ray.mov_mem_abs32_eax(pe, "distance_denominator")

    pe.label("cast_compute_distance")
    ray.mov_reg_mem_abs32(pe, "eax", "distance_numerator")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "cast_linedef_skip")
    ray.shl_reg_imm8(pe, "eax", RAY_DISTANCE_SHIFT)
    ray.xor_reg_reg(pe, "edx", "edx")
    ray.mov_reg_mem_abs32(pe, "ecx", "distance_denominator")
    ray.div_ecx(pe)
    ray.test_eax_eax(pe)
    ray.jne_rel32(pe, "cast_distance_nonzero")
    x86.mov_reg_imm32(pe, "eax", 1)

    pe.label("cast_distance_nonzero")
    ray.cmp_reg_mem_abs32(pe, "eax", "ray_distance")
    ray.jae_rel32(pe, "cast_linedef_skip")
    ray.mov_mem_abs32_eax(pe, "ray_distance")
    ray.mov_mem_abs32_imm32(pe, "ray_hit_tile", 1)
    ray.mov_mem_abs32_imm32(pe, "ray_hit_color", COLOR_WALL)
    x86.call_rel32(pe, "select_wall_texture")

    pe.label("cast_linedef_skip")
    ray.mov_reg_mem_abs32(pe, "esi", "linedef_scan_ptr")
    ray.add_reg_imm32(pe, "esi", LINEDEF_RECORD_SIZE)
    ray.mov_mem_abs32_reg(pe, "linedef_scan_ptr", "esi")
    dec_mem_abs32(pe, "linedefs_remaining")
    x86.jmp_rel32(pe, "cast_linedef_loop")

    pe.label("cast_ray_done")
    ray.pop_reg(pe, "edi")
    ray.pop_reg(pe, "esi")
    ray.pop_reg(pe, "edx")
    ray.pop_reg(pe, "ecx")
    ray.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_select_wall_texture(pe: PE32) -> None:
    pe.label("select_wall_texture")
    ray.push_reg(pe, "ebx")
    ray.push_reg(pe, "ecx")
    ray.push_reg(pe, "edx")
    ray.push_reg(pe, "esi")
    ray.push_reg(pe, "edi")

    ray.mov_mem_abs32_imm32(pe, "ray_hit_texture", 0)
    ray.mov_mem_abs32_imm32(pe, "ray_texture_x", 0)
    ray.mov_mem_abs32_imm32(pe, "ray_texture_name0", 0)
    ray.mov_mem_abs32_imm32(pe, "ray_texture_name1", 0)

    ray.mov_reg_mem_abs32(pe, "esi", "linedef_scan_ptr")
    movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 10)
    ray.cmp_reg_mem_abs32(pe, "eax", "sidedef_count")
    ray.jae_rel32(pe, "select_texture_done")

    ray.mov_reg_reg(pe, "ebx", "eax")
    ray.shl_reg_imm8(pe, "ebx", 5)
    ray.mov_reg_reg(pe, "edx", "eax")
    ray.shl_reg_imm8(pe, "edx", 1)
    ray.sub_reg_reg(pe, "ebx", "edx")

    ray.mov_reg_abs32(pe, "edi", "sidedefs_buffer")
    ray.add_reg_reg(pe, "edi", "ebx")

    mov_reg_ptr_reg_disp8(pe, "eax", "edi", 20)
    mov_reg_ptr_reg_disp8(pe, "edx", "edi", 24)
    ray.mov_mem_abs32_eax(pe, "ray_texture_name0")
    ray.mov_mem_abs32_reg(pe, "ray_texture_name1", "edx")

    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "select_texture_done")
    ray.cmp_eax_imm32(pe, NO_TEXTURE_NAME0)
    ray.jne_rel32(pe, "select_texture_name_ok")
    ray.cmp_reg_imm32(pe, "edx", NO_TEXTURE_NAME1)
    ray.je_rel32(pe, "select_texture_done")

    pe.label("select_texture_name_ok")
    ray.xor_reg_reg(pe, "eax", "edx")
    ray.mov_reg_reg(pe, "ebx", "eax")
    ray.shr_reg_imm8(pe, "ebx", 16)
    ray.xor_reg_reg(pe, "eax", "ebx")
    ray.and_reg_imm32(pe, "eax", WALL_TEXTURE_MASK)
    ray.inc_reg(pe, "eax")
    ray.mov_mem_abs32_eax(pe, "ray_hit_texture")

    ray.mov_reg_mem_abs32(pe, "eax", "texture_numerator")
    ray.shl_reg_imm8(pe, "eax", 6)
    ray.xor_reg_reg(pe, "edx", "edx")
    ray.mov_reg_mem_abs32(pe, "ecx", "distance_denominator")
    ray.div_ecx(pe)
    ray.and_reg_imm32(pe, "eax", WALL_TEXTURE_SIZE - 1)
    ray.mov_mem_abs32_eax(pe, "ray_texture_x")

    pe.label("select_texture_done")
    ray.pop_reg(pe, "edi")
    ray.pop_reg(pe, "esi")
    ray.pop_reg(pe, "edx")
    ray.pop_reg(pe, "ecx")
    ray.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_draw_wall_column(pe: PE32) -> None:
    pe.label("draw_wall_column")
    ray.push_reg(pe, "ebx")
    ray.push_reg(pe, "ecx")
    ray.push_reg(pe, "edx")
    ray.push_reg(pe, "esi")
    ray.push_reg(pe, "edi")

    ray.mov_reg_mem_abs32(pe, "eax", "ray_hit_tile")
    ray.test_eax_eax(pe)
    ray.je_rel32(pe, "draw_wall_done")

    ray.mov_reg_mem_abs32(pe, "ecx", "ray_distance")
    ray.test_reg_reg(pe, "ecx")
    ray.je_rel32(pe, "draw_wall_done")
    ray.xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "eax", ray.WALL_HEIGHT_NUMERATOR)
    ray.div_ecx(pe)
    ray.cmp_reg_imm32(pe, "eax", FRAMEBUFFER_HEIGHT)
    ray.jbe_rel32(pe, "draw_wall_height_ok")
    x86.mov_reg_imm32(pe, "eax", FRAMEBUFFER_HEIGHT)

    pe.label("draw_wall_height_ok")
    ray.mov_mem_abs32_eax(pe, "column_height")

    x86.mov_reg_imm32(pe, "ebx", FRAMEBUFFER_HEIGHT)
    ray.sub_reg_reg(pe, "ebx", "eax")
    ray.shr_reg_imm8(pe, "ebx", 1)
    ray.mov_mem_abs32_reg(pe, "wall_top", "ebx")

    ray.add_reg_reg(pe, "ebx", "eax")
    ray.cmp_reg_imm32(pe, "ebx", FRAMEBUFFER_HEIGHT)
    ray.jbe_rel32(pe, "draw_wall_bottom_ok")
    x86.mov_reg_imm32(pe, "ebx", FRAMEBUFFER_HEIGHT)

    pe.label("draw_wall_bottom_ok")
    ray.mov_mem_abs32_reg(pe, "wall_bottom", "ebx")

    ray.mov_reg_mem_abs32(pe, "ecx", "wall_bottom")
    ray.mov_reg_mem_abs32(pe, "eax", "wall_top")
    ray.sub_reg_reg(pe, "ecx", "eax")
    ray.test_reg_reg(pe, "ecx")
    ray.je_rel32(pe, "draw_wall_done")

    ray.mov_reg_reg(pe, "ebx", "eax")
    ray.shl_reg_imm8(pe, "ebx", 8)
    ray.mov_reg_reg(pe, "edx", "eax")
    ray.shl_reg_imm8(pe, "edx", 6)
    ray.add_reg_reg(pe, "ebx", "edx")
    ray.add_reg_mem_abs32(pe, "ebx", "ray_column")
    ray.shl_reg_imm8(pe, "ebx", 2)

    ray.mov_reg_abs32(pe, "edi", "framebuffer")
    ray.add_reg_reg(pe, "edi", "ebx")

    ray.mov_reg_mem_abs32(pe, "eax", "ray_hit_texture")
    ray.test_eax_eax(pe)
    ray.jne_rel32(pe, "draw_wall_textured")

    ray.mov_reg_mem_abs32(pe, "eax", "ray_hit_color")

    pe.label("draw_wall_solid_loop")
    ray.mov_ptr_reg_eax(pe, "edi")
    ray.add_reg_imm32(pe, "edi", ray.ROW_STRIDE_BYTES)
    ray.dec_reg(pe, "ecx")
    ray.jne_rel32(pe, "draw_wall_solid_loop")
    x86.jmp_rel32(pe, "draw_wall_done")

    pe.label("draw_wall_textured")
    ray.dec_reg(pe, "eax")
    ray.shl_reg_imm8(pe, "eax", WALL_TEXTURE_BYTES_SHIFT)
    ray.mov_reg_abs32(pe, "esi", "placeholder_wall_textures")
    ray.add_reg_reg(pe, "esi", "eax")
    ray.mov_reg_mem_abs32(pe, "eax", "ray_texture_x")
    ray.and_reg_imm32(pe, "eax", WALL_TEXTURE_SIZE - 1)
    ray.shl_reg_imm8(pe, "eax", 2)
    ray.add_reg_reg(pe, "esi", "eax")

    ray.xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "eax", WALL_TEXTURE_V_SCALE)
    ray.div_ecx(pe)
    ray.mov_mem_abs32_eax(pe, "texture_step")
    ray.mov_mem_abs32_imm32(pe, "texture_v", 0)

    pe.label("draw_wall_textured_loop")
    ray.mov_reg_mem_abs32(pe, "eax", "texture_v")
    ray.shr_reg_imm8(pe, "eax", 16)
    ray.shl_reg_imm8(pe, "eax", WALL_TEXTURE_ROW_BYTES_SHIFT)
    ray.mov_reg_reg(pe, "edx", "esi")
    ray.add_reg_reg(pe, "edx", "eax")
    ray.mov_reg_ptr_reg(pe, "eax", "edx")
    ray.mov_ptr_reg_eax(pe, "edi")
    ray.add_reg_imm32(pe, "edi", ray.ROW_STRIDE_BYTES)
    ray.mov_reg_mem_abs32(pe, "eax", "texture_step")
    add_mem_abs32_reg(pe, "texture_v", "eax")
    ray.dec_reg(pe, "ecx")
    ray.jne_rel32(pe, "draw_wall_textured_loop")

    pe.label("draw_wall_done")
    ray.pop_reg(pe, "edi")
    ray.pop_reg(pe, "esi")
    ray.pop_reg(pe, "edx")
    ray.pop_reg(pe, "ecx")
    ray.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_data(pe: PE32) -> None:
    pe.align_section(4)
    pe.label("window_class")
    pe.label("wc_cbSize")
    pe.emit_u32(WNDCLASSEXW_SIZE)
    pe.label("wc_style")
    pe.emit_u32(CS_HREDRAW | CS_VREDRAW)
    pe.label("wc_lpfnWndProc")
    pe.write_abs32("wndproc")
    pe.label("wc_cbClsExtra")
    pe.emit_u32(0)
    pe.label("wc_cbWndExtra")
    pe.emit_u32(0)
    pe.label("wc_hInstance")
    pe.emit_u32(0)
    pe.label("wc_hIcon")
    pe.emit_u32(0)
    pe.label("wc_hCursor")
    pe.emit_u32(0)
    pe.label("wc_hbrBackground")
    pe.emit_u32(COLOR_WINDOW + 1)
    pe.label("wc_lpszMenuName")
    pe.emit_u32(0)
    pe.label("wc_lpszClassName")
    pe.write_abs32("class_name")
    pe.label("wc_hIconSm")
    pe.emit_u32(0)

    pe.label("main_hwnd")
    pe.emit_u32(0)
    pe.label("frame_index")
    pe.emit_u32(0)
    pe.label("key_forward")
    pe.emit_u32(0)
    pe.label("key_backward")
    pe.emit_u32(0)
    pe.label("key_turn_left")
    pe.emit_u32(0)
    pe.label("key_turn_right")
    pe.emit_u32(0)
    pe.label("key_strafe_left")
    pe.emit_u32(0)
    pe.label("key_strafe_right")
    pe.emit_u32(0)
    pe.label("key_escape")
    pe.emit_u32(0)

    pe.label("map_loaded")
    pe.emit_u32(0)
    pe.label("map_lumps_valid")
    pe.emit_u32(0)
    pe.label("map_lumps_read")
    pe.emit_u32(0)
    pe.label("player_start_found")
    pe.emit_u32(0)

    pe.label("player_x")
    pe.emit_u32(PLAYER_START_X)
    pe.label("player_y")
    pe.emit_u32(PLAYER_START_Y)
    pe.label("player_angle")
    pe.emit_u32(PLAYER_START_ANGLE)
    pe.label("candidate_x")
    pe.emit_u32(PLAYER_START_X)
    pe.label("candidate_y")
    pe.emit_u32(PLAYER_START_Y)
    pe.label("move_angle")
    pe.emit_u32(0)
    pe.label("move_speed")
    pe.emit_u32(0)

    pe.label("wad_file_handle")
    pe.emit_u32(0)
    pe.label("bytes_read")
    pe.emit_u32(0)
    pe.label("directory_entries_remaining")
    pe.emit_u32(0)
    pe.label("map_scan_active")
    pe.emit_u32(0)
    pe.label("things_found")
    pe.emit_u32(0)
    pe.label("linedefs_found")
    pe.emit_u32(0)
    pe.label("sidedefs_found")
    pe.emit_u32(0)
    pe.label("vertexes_found")
    pe.emit_u32(0)
    pe.label("things_offset")
    pe.emit_u32(0)
    pe.label("things_size")
    pe.emit_u32(0)
    pe.label("linedefs_offset")
    pe.emit_u32(0)
    pe.label("linedefs_size")
    pe.emit_u32(0)
    pe.label("sidedefs_offset")
    pe.emit_u32(0)
    pe.label("sidedefs_size")
    pe.emit_u32(0)
    pe.label("vertexes_offset")
    pe.emit_u32(0)
    pe.label("vertexes_size")
    pe.emit_u32(0)
    pe.label("thing_count")
    pe.emit_u32(0)
    pe.label("vertex_count")
    pe.emit_u32(0)
    pe.label("linedef_count")
    pe.emit_u32(0)
    pe.label("sidedef_count")
    pe.emit_u32(0)
    pe.label("linedef_scan_ptr")
    pe.emit_u32(0)
    pe.label("linedefs_remaining")
    pe.emit_u32(0)

    pe.label("ray_column")
    pe.emit_u32(0)
    pe.label("ray_angle")
    pe.emit_u32(0)
    pe.label("ray_distance")
    pe.emit_u32(RAY_MAX_DISTANCE)
    pe.label("ray_hit_tile")
    pe.emit_u32(0)
    pe.label("ray_hit_color")
    pe.emit_u32(COLOR_WALL)
    pe.label("ray_hit_texture")
    pe.emit_u32(0)
    pe.label("ray_texture_x")
    pe.emit_u32(0)
    pe.label("ray_texture_name0")
    pe.emit_u32(0)
    pe.label("ray_texture_name1")
    pe.emit_u32(0)
    pe.label("ray_dx")
    pe.emit_u32(0)
    pe.label("ray_dy")
    pe.emit_u32(0)
    pe.label("seg_x0")
    pe.emit_u32(0)
    pe.label("seg_y0")
    pe.emit_u32(0)
    pe.label("seg_x1")
    pe.emit_u32(0)
    pe.label("seg_y1")
    pe.emit_u32(0)
    pe.label("seg_dx")
    pe.emit_u32(0)
    pe.label("seg_dy")
    pe.emit_u32(0)
    pe.label("rel_x")
    pe.emit_u32(0)
    pe.label("rel_y")
    pe.emit_u32(0)
    pe.label("intersection_tmp")
    pe.emit_u32(0)
    pe.label("intersection_denom")
    pe.emit_u32(0)
    pe.label("intersection_tnum")
    pe.emit_u32(0)
    pe.label("intersection_unum")
    pe.emit_u32(0)
    pe.label("distance_numerator")
    pe.emit_u32(0)
    pe.label("distance_denominator")
    pe.emit_u32(1)
    pe.label("texture_numerator")
    pe.emit_u32(0)
    pe.label("texture_step")
    pe.emit_u32(0)
    pe.label("texture_v")
    pe.emit_u32(0)
    pe.label("column_height")
    pe.emit_u32(0)
    pe.label("wall_top")
    pe.emit_u32(0)
    pe.label("wall_bottom")
    pe.emit_u32(0)

    pe.align_section(4)
    pe.label("message")
    pe.label("msg_hwnd")
    pe.emit_u32(0)
    pe.label("msg_message")
    pe.emit_u32(0)
    pe.label("msg_wParam")
    pe.emit_u32(0)
    pe.label("msg_lParam")
    pe.emit_u32(0)
    pe.label("msg_time")
    pe.emit_u32(0)
    pe.label("msg_pt_x")
    pe.emit_u32(0)
    pe.label("msg_pt_y")
    pe.emit_u32(0)

    pe.align_section(4)
    pe.label("paint_struct")
    pe.label("paint_hdc")
    pe.emit_u32(0)
    pe.emit_zeros(PAINTSTRUCT_SIZE - 4)

    pe.align_section(4)
    pe.label("client_rect")
    pe.label("client_left")
    pe.emit_u32(0)
    pe.label("client_top")
    pe.emit_u32(0)
    pe.label("client_right")
    pe.emit_u32(0)
    pe.label("client_bottom")
    pe.emit_u32(0)

    pe.align_section(4)
    pe.label("wad_header")
    pe.label("wad_kind")
    pe.emit_u32(0)
    pe.label("wad_lump_count")
    pe.emit_u32(0)
    pe.label("wad_directory_offset")
    pe.emit_u32(0)

    pe.align_section(4)
    pe.label("directory_entry")
    pe.label("directory_lump_offset")
    pe.emit_u32(0)
    pe.label("directory_lump_size")
    pe.emit_u32(0)
    pe.label("directory_lump_name0")
    pe.emit_u32(0)
    pe.label("directory_lump_name1")
    pe.emit_u32(0)

    pe.align_section(4)
    pe.label("bitmap_info")
    pe.label("bmi_header")
    pe.emit_u32(40)
    pe.emit_u32(FRAMEBUFFER_WIDTH)
    pe.emit_u32((-FRAMEBUFFER_HEIGHT) & 0xFFFFFFFF)
    pe.emit_u16(1)
    pe.emit_u16(32)
    pe.emit_u32(ray.BI_RGB)
    pe.emit_u32(FRAMEBUFFER_BYTES)
    pe.emit_u32(0)
    pe.emit_u32(0)
    pe.emit_u32(0)
    pe.emit_u32(0)

    pe.align_section(2)
    pe.label("class_name")
    ray.emit_utf16z(pe, WINDOW_CLASS_NAME)
    pe.label("window_title")
    ray.emit_utf16z(pe, WINDOW_TITLE)
    pe.label("wad_path_w")
    ray.emit_utf16z(pe, WAD_PATH)

    pe.align_section(4)
    pe.label("angle_offsets")
    pe.emit(ray.ANGLE_OFFSETS)

    pe.align_section(2)
    pe.label("cos_table")
    ray.emit_i16_table(pe, ray.COS_TABLE)
    pe.label("sin_table")
    ray.emit_i16_table(pe, ray.SIN_TABLE)

    pe.align_section(4)
    pe.label("things_buffer")
    pe.emit_zeros(THING_BUFFER_BYTES)

    pe.align_section(4)
    pe.label("vertexes_buffer")
    pe.emit_zeros(VERTEX_BUFFER_BYTES)

    pe.align_section(4)
    pe.label("linedefs_buffer")
    pe.emit_zeros(LINEDEF_BUFFER_BYTES)

    pe.align_section(4)
    pe.label("sidedefs_buffer")
    pe.emit_zeros(SIDEDEF_BUFFER_BYTES)

    pe.align_section(4)
    pe.label("placeholder_wall_textures")
    pe.emit(PLACEHOLDER_WALL_TEXTURES)

    pe.align_section(4)
    pe.label("framebuffer")
    pe.emit_zeros(FRAMEBUFFER_BYTES)


def build_stage07_real_map_view_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    ray.emit_wndproc(pe)
    ray.emit_update_player(pe)
    ray.emit_add_move_vector(pe)
    emit_try_commit_move(pe)
    emit_render_scene(pe)
    ray.emit_clear_view(pe)
    emit_render_error_pattern(pe)
    emit_cast_ray(pe)
    emit_select_wall_texture(pe)
    emit_draw_wall_column(pe)
    emit_load_map_data(pe)
    emit_validate_map_lump_sizes(pe)
    emit_read_map_lumps(pe)
    emit_init_player_from_things(pe)
    emit_data(pe)
    return pe.build("entry")


def write_stage07_real_map_view_exe(path: str | Path) -> bytes:
    image = build_stage07_real_map_view_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the Phase 13 PE32 x86 Win32 real-map textured-column renderer."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/stage07_real_map_view.exe",
        help="path to write, default: build/stage07_real_map_view.exe",
    )
    args = parser.parse_args()
    write_stage07_real_map_view_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
