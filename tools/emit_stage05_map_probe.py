from __future__ import annotations

import argparse
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import x86
from tools.pe32 import PE32


KERNEL32 = "KERNEL32.dll"
USER32 = "USER32.dll"
GDI32 = "GDI32.dll"

CS_VREDRAW = 0x0001
CS_HREDRAW = 0x0002
COLOR_WINDOW = 5
CW_USEDEFAULT = 0x80000000
DIB_RGB_COLORS = 0
BI_RGB = 0
SRCCOPY = 0x00CC0020
SW_SHOWNORMAL = 1
WM_DESTROY = 0x0002
WM_PAINT = 0x000F
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_VISIBLE = 0x10000000

GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_BEGIN = 0
INVALID_HANDLE_VALUE = 0xFFFFFFFF

FRAMEBUFFER_WIDTH = 320
FRAMEBUFFER_HEIGHT = 200
FRAMEBUFFER_PIXELS = FRAMEBUFFER_WIDTH * FRAMEBUFFER_HEIGHT
FRAMEBUFFER_BYTES = FRAMEBUFFER_PIXELS * 4
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 640
WINDOW_STYLE = WS_OVERLAPPEDWINDOW | WS_VISIBLE
WNDCLASSEXW_SIZE = 48
PAINTSTRUCT_SIZE = 64

WAD_HEADER_SIZE = 12
WAD_DIRECTORY_ENTRY_SIZE = 16
IWAD_MAGIC = 0x44415749
PWAD_MAGIC = 0x44415750

VERTEX_RECORD_SIZE = 4
LINEDEF_RECORD_SIZE = 14
VERTEX_BUFFER_BYTES = 64 * 1024
LINEDEF_BUFFER_BYTES = 128 * 1024
MAX_SCREEN_VERTEX_BYTES = (VERTEX_BUFFER_BYTES // VERTEX_RECORD_SIZE) * 8

MAP01_NAME0 = int.from_bytes(b"MAP0", "little")
MAP01_NAME1 = int.from_bytes(b"1\0\0\0", "little")
LINEDEFS_NAME0 = int.from_bytes(b"LINE", "little")
LINEDEFS_NAME1 = int.from_bytes(b"DEFS", "little")
VERTEXES_NAME0 = int.from_bytes(b"VERT", "little")
VERTEXES_NAME1 = int.from_bytes(b"EXES", "little")

# Freedoom2 MAP01 currently spans x=-248..2176 and y=-1800..1600.
# These constants keep Phase 10 focused on runtime WAD map loading and line drawing.
MAP_MIN_X = -248
MAP_MIN_Y = -1800
MAP_SCALE_16_16 = 3469
SCREEN_X_OFFSET = 96
SCREEN_Y_BOTTOM = 190

COLOR_BACKGROUND = 0x00091016
COLOR_ERROR = 0x00200070
COLOR_ONE_SIDED_LINE = 0x00F2F5EA
COLOR_TWO_SIDED_LINE = 0x006A8590

WINDOW_CLASS_NAME = "InferenceDoomStage05MapProbe"
WINDOW_TITLE = "Inference Doom - Stage 05 Map Probe"
WAD_PATH = r"third_party\freedoom\freedoom2.wad"


def push_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\x68")
    pe.write_abs32(label)


def push_mem_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\xFF\x35")
    pe.write_abs32(label)


def mov_mem_abs32_eax(pe: PE32, label: str) -> None:
    pe.emit(b"\xA3")
    pe.write_abs32(label)


def mov_mem_abs32_reg(pe: PE32, label: str, reg: str) -> None:
    pe.emit(bytes([0x89, x86.modrm(0, reg, 5)]))
    pe.write_abs32(label)


def mov_mem_abs32_imm32(pe: PE32, label: str, value: int) -> None:
    pe.emit(b"\xC7\x05")
    pe.write_abs32(label)
    pe.emit_u32(value)


def mov_reg_abs32(pe: PE32, reg: str, label: str) -> None:
    pe.emit_u8(0xB8 + x86.reg_code(reg))
    pe.write_abs32(label)


def mov_reg_mem_abs32(pe: PE32, reg: str, label: str) -> None:
    pe.emit(bytes([0x8B, x86.modrm(0, reg, 5)]))
    pe.write_abs32(label)


def mov_reg_ptr_reg(pe: PE32, dst: str, base: str) -> None:
    pe.emit(bytes([0x8B, x86.modrm(0, dst, base)]))


def mov_reg_ptr_reg_disp8(pe: PE32, dst: str, base: str, displacement: int) -> None:
    pe.emit(bytes([0x8B, x86.modrm(1, dst, base), displacement & 0xFF]))


def mov_ptr_reg_eax(pe: PE32, base: str) -> None:
    pe.emit(bytes([0x89, x86.modrm(0, "eax", base)]))


def mov_ptr_reg_disp8_eax(pe: PE32, base: str, displacement: int) -> None:
    pe.emit(bytes([0x89, x86.modrm(1, "eax", base), displacement & 0xFF]))


def movzx_reg_word_ptr_reg(pe: PE32, dst: str, base: str) -> None:
    pe.emit(bytes([0x0F, 0xB7, x86.modrm(0, dst, base)]))


def movzx_reg_word_ptr_reg_disp8(
    pe: PE32, dst: str, base: str, displacement: int
) -> None:
    pe.emit(bytes([0x0F, 0xB7, x86.modrm(1, dst, base), displacement & 0xFF]))


def movsx_reg_word_ptr_reg(pe: PE32, dst: str, base: str) -> None:
    pe.emit(bytes([0x0F, 0xBF, x86.modrm(0, dst, base)]))


def movsx_reg_word_ptr_reg_disp8(
    pe: PE32, dst: str, base: str, displacement: int
) -> None:
    pe.emit(bytes([0x0F, 0xBF, x86.modrm(1, dst, base), displacement & 0xFF]))


def mov_eax_ebp_disp8(pe: PE32, displacement: int) -> None:
    pe.emit(bytes([0x8B, 0x45, displacement & 0xFF]))


def push_ebp_disp8(pe: PE32, displacement: int) -> None:
    pe.emit(bytes([0xFF, 0x75, displacement & 0xFF]))


def mov_reg_reg(pe: PE32, dst: str, src: str) -> None:
    pe.emit(bytes([0x8B, x86.modrm(3, dst, src)]))


def add_reg_reg(pe: PE32, dst: str, src: str) -> None:
    pe.emit(bytes([0x01, x86.modrm(3, src, dst)]))


def add_reg_imm32(pe: PE32, reg: str, value: int) -> None:
    if x86.reg_code(reg) == x86.reg_code("eax"):
        pe.emit(b"\x05")
    else:
        pe.emit(bytes([0x81, x86.modrm(3, 0, reg)]))
    pe.emit_u32(value)


def add_reg_mem_abs32(pe: PE32, reg: str, label: str) -> None:
    pe.emit(bytes([0x03, x86.modrm(0, reg, 5)]))
    pe.write_abs32(label)


def sub_reg_reg(pe: PE32, dst: str, src: str) -> None:
    pe.emit(bytes([0x29, x86.modrm(3, src, dst)]))


def sub_reg_mem_abs32(pe: PE32, reg: str, label: str) -> None:
    pe.emit(bytes([0x2B, x86.modrm(0, reg, 5)]))
    pe.write_abs32(label)


def and_reg_imm32(pe: PE32, reg: str, value: int) -> None:
    if x86.reg_code(reg) == x86.reg_code("eax"):
        pe.emit(b"\x25")
    else:
        pe.emit(bytes([0x81, x86.modrm(3, 4, reg)]))
    pe.emit_u32(value)


def shl_reg_imm8(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0xC1, x86.modrm(3, 4, reg), value & 0xFF]))


def shr_reg_imm8(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0xC1, x86.modrm(3, 5, reg), value & 0xFF]))


def sar_reg_imm8(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0xC1, x86.modrm(3, 7, reg), value & 0xFF]))


def imul_reg_reg_imm32(pe: PE32, dst: str, src: str, value: int) -> None:
    pe.emit(bytes([0x69, x86.modrm(3, dst, src)]))
    pe.emit_u32(value)


def neg_reg(pe: PE32, reg: str) -> None:
    pe.emit(bytes([0xF7, x86.modrm(3, 3, reg)]))


def cdq(pe: PE32) -> None:
    pe.emit(b"\x99")


def div_ecx(pe: PE32) -> None:
    pe.emit(b"\xF7\xF1")


def idiv_ecx(pe: PE32) -> None:
    pe.emit(b"\xF7\xF9")


def xor_reg_reg(pe: PE32, dst: str, src: str) -> None:
    x86.xor_reg_reg(pe, dst, src)


def inc_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x40 + x86.reg_code(reg))


def dec_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x48 + x86.reg_code(reg))


def dec_mem_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\xFF\x0D")
    pe.write_abs32(label)


def push_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x50 + x86.reg_code(reg))


def pop_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x58 + x86.reg_code(reg))


def cmp_eax_imm32(pe: PE32, value: int) -> None:
    pe.emit(b"\x3D")
    pe.emit_u32(value)


def cmp_reg_imm32(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0x81, x86.modrm(3, 7, reg)]))
    pe.emit_u32(value)


def cmp_reg_reg(pe: PE32, left: str, right: str) -> None:
    pe.emit(bytes([0x39, x86.modrm(3, right, left)]))


def cmp_reg_mem_abs32(pe: PE32, reg: str, label: str) -> None:
    pe.emit(bytes([0x3B, x86.modrm(0, reg, 5)]))
    pe.write_abs32(label)


def test_eax_eax(pe: PE32) -> None:
    pe.emit(b"\x85\xC0")


def test_reg_reg(pe: PE32, reg: str) -> None:
    pe.emit(bytes([0x85, x86.modrm(3, reg, reg)]))


def je_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x84")
    pe.write_rel32(label)


def jne_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x85")
    pe.write_rel32(label)


def jb_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x82")
    pe.write_rel32(label)


def ja_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x87")
    pe.write_rel32(label)


def jae_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x83")
    pe.write_rel32(label)


def jns_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x89")
    pe.write_rel32(label)


def emit_function_prologue(pe: PE32) -> None:
    pe.emit(b"\x55")  # push ebp
    pe.emit(b"\x89\xE5")  # mov ebp, esp


def emit_function_epilogue_ret(pe: PE32, stack_bytes: int) -> None:
    pe.emit(b"\xC9")  # leave
    pe.emit(b"\xC2")
    pe.emit_u16(stack_bytes)


def emit_utf16z(pe: PE32, value: str) -> None:
    pe.emit(value.encode("utf-16le"))
    pe.emit_u16(0)


def emit_entry(pe: PE32) -> None:
    pe.label("entry")

    x86.push_imm8(pe, 0)
    x86.call_import(pe, KERNEL32, "GetModuleHandleW")
    mov_mem_abs32_eax(pe, "wc_hInstance")

    push_abs32(pe, "window_class")
    x86.call_import(pe, USER32, "RegisterClassExW")
    test_eax_eax(pe)
    jne_rel32(pe, "class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("class_registered")
    x86.call_rel32(pe, "load_map_data")
    x86.call_rel32(pe, "render_map")

    x86.push_imm8(pe, 0)  # lpParam
    push_mem_abs32(pe, "wc_hInstance")
    x86.push_imm8(pe, 0)  # hMenu
    x86.push_imm8(pe, 0)  # hWndParent
    x86.push_imm32(pe, WINDOW_HEIGHT)
    x86.push_imm32(pe, WINDOW_WIDTH)
    x86.push_imm32(pe, CW_USEDEFAULT)
    x86.push_imm32(pe, CW_USEDEFAULT)
    x86.push_imm32(pe, WINDOW_STYLE)
    push_abs32(pe, "window_title")
    push_abs32(pe, "class_name")
    x86.push_imm8(pe, 0)  # dwExStyle
    x86.call_import(pe, USER32, "CreateWindowExW")
    test_eax_eax(pe)
    jne_rel32(pe, "window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("window_created")
    mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_imm8(pe, SW_SHOWNORMAL)
    push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, USER32, "ShowWindow")
    push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, USER32, "UpdateWindow")

    pe.label("message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    push_abs32(pe, "message")
    x86.call_import(pe, USER32, "GetMessageW")
    test_eax_eax(pe)
    je_rel32(pe, "clean_exit")
    cmp_eax_imm32(pe, 0xFFFFFFFF)
    je_rel32(pe, "message_error")

    push_abs32(pe, "message")
    x86.call_import(pe, USER32, "TranslateMessage")
    push_abs32(pe, "message")
    x86.call_import(pe, USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "message_loop")

    pe.label("clean_exit")
    push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, KERNEL32, "ExitProcess")


def emit_wndproc(pe: PE32) -> None:
    pe.label("wndproc")
    emit_function_prologue(pe)

    mov_eax_ebp_disp8(pe, 12)  # UINT message
    cmp_eax_imm32(pe, WM_DESTROY)
    je_rel32(pe, "wndproc_destroy")
    cmp_eax_imm32(pe, WM_PAINT)
    je_rel32(pe, "wndproc_paint")

    pe.label("wndproc_default")
    push_ebp_disp8(pe, 20)  # LPARAM lParam
    push_ebp_disp8(pe, 16)  # WPARAM wParam
    push_ebp_disp8(pe, 12)  # UINT message
    push_ebp_disp8(pe, 8)  # HWND hwnd
    x86.call_import(pe, USER32, "DefWindowProcW")
    emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_destroy")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, USER32, "PostQuitMessage")
    xor_reg_reg(pe, "eax", "eax")
    emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_paint")
    push_abs32(pe, "paint_struct")
    push_ebp_disp8(pe, 8)  # hwnd
    x86.call_import(pe, USER32, "BeginPaint")
    mov_mem_abs32_eax(pe, "paint_hdc")

    push_abs32(pe, "client_rect")
    push_ebp_disp8(pe, 8)  # hwnd
    x86.call_import(pe, USER32, "GetClientRect")

    x86.push_imm32(pe, SRCCOPY)  # rop
    x86.push_imm8(pe, DIB_RGB_COLORS)  # iUsage
    push_abs32(pe, "bitmap_info")
    push_abs32(pe, "framebuffer")
    x86.push_imm32(pe, FRAMEBUFFER_HEIGHT)
    x86.push_imm32(pe, FRAMEBUFFER_WIDTH)
    x86.push_imm8(pe, 0)  # ySrc
    x86.push_imm8(pe, 0)  # xSrc
    push_mem_abs32(pe, "client_bottom")  # DestHeight
    push_mem_abs32(pe, "client_right")  # DestWidth
    x86.push_imm8(pe, 0)  # yDest
    x86.push_imm8(pe, 0)  # xDest
    push_mem_abs32(pe, "paint_hdc")
    x86.call_import(pe, GDI32, "StretchDIBits")

    push_abs32(pe, "paint_struct")
    push_ebp_disp8(pe, 8)  # hwnd
    x86.call_import(pe, USER32, "EndPaint")
    xor_reg_reg(pe, "eax", "eax")
    emit_function_epilogue_ret(pe, 16)


def emit_load_map_data(pe: PE32) -> None:
    pe.label("load_map_data")

    x86.push_imm8(pe, 0)  # hTemplateFile
    x86.push_imm32(pe, FILE_ATTRIBUTE_NORMAL)
    x86.push_imm32(pe, OPEN_EXISTING)
    x86.push_imm8(pe, 0)  # lpSecurityAttributes
    x86.push_imm32(pe, FILE_SHARE_READ)
    x86.push_imm32(pe, GENERIC_READ)
    push_abs32(pe, "wad_path_w")
    x86.call_import(pe, KERNEL32, "CreateFileW")
    cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    jne_rel32(pe, "map_file_opened")
    x86.ret(pe)

    pe.label("map_file_opened")
    mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)  # lpOverlapped
    push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, WAD_HEADER_SIZE)
    push_abs32(pe, "wad_header")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")
    mov_reg_mem_abs32(pe, "eax", "bytes_read")
    cmp_eax_imm32(pe, WAD_HEADER_SIZE)
    jne_rel32(pe, "load_close_and_return")

    mov_reg_mem_abs32(pe, "eax", "wad_kind")
    cmp_eax_imm32(pe, IWAD_MAGIC)
    je_rel32(pe, "map_magic_ok")
    cmp_eax_imm32(pe, PWAD_MAGIC)
    jne_rel32(pe, "load_close_and_return")

    pe.label("map_magic_ok")
    mov_reg_mem_abs32(pe, "eax", "wad_lump_count")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")
    mov_reg_mem_abs32(pe, "eax", "wad_directory_offset")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")

    x86.push_imm32(pe, FILE_BEGIN)
    x86.push_imm8(pe, 0)  # lpDistanceToMoveHigh
    push_mem_abs32(pe, "wad_directory_offset")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "SetFilePointer")
    cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    je_rel32(pe, "load_close_and_return")

    mov_reg_mem_abs32(pe, "eax", "wad_lump_count")
    mov_mem_abs32_eax(pe, "directory_entries_remaining")

    pe.label("directory_scan_loop")
    mov_reg_mem_abs32(pe, "eax", "directory_entries_remaining")
    test_eax_eax(pe)
    je_rel32(pe, "directory_scan_done")

    x86.push_imm8(pe, 0)  # lpOverlapped
    push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, WAD_DIRECTORY_ENTRY_SIZE)
    push_abs32(pe, "directory_entry")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")
    mov_reg_mem_abs32(pe, "eax", "bytes_read")
    cmp_eax_imm32(pe, WAD_DIRECTORY_ENTRY_SIZE)
    jne_rel32(pe, "load_close_and_return")

    mov_reg_mem_abs32(pe, "eax", "directory_lump_name0")
    cmp_eax_imm32(pe, MAP01_NAME0)
    jne_rel32(pe, "check_map_lump_names")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_name1")
    cmp_eax_imm32(pe, MAP01_NAME1)
    jne_rel32(pe, "check_map_lump_names")
    mov_mem_abs32_imm32(pe, "map_scan_active", 1)
    x86.jmp_rel32(pe, "directory_next_entry")

    pe.label("check_map_lump_names")
    mov_reg_mem_abs32(pe, "eax", "map_scan_active")
    test_eax_eax(pe)
    je_rel32(pe, "directory_next_entry")

    mov_reg_mem_abs32(pe, "eax", "directory_lump_name0")
    cmp_eax_imm32(pe, LINEDEFS_NAME0)
    jne_rel32(pe, "check_vertexes_name")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_name1")
    cmp_eax_imm32(pe, LINEDEFS_NAME1)
    jne_rel32(pe, "check_vertexes_name")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_offset")
    mov_mem_abs32_eax(pe, "linedefs_offset")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_size")
    mov_mem_abs32_eax(pe, "linedefs_size")
    mov_mem_abs32_imm32(pe, "linedefs_found", 1)
    x86.jmp_rel32(pe, "check_lumps_complete")

    pe.label("check_vertexes_name")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_name0")
    cmp_eax_imm32(pe, VERTEXES_NAME0)
    jne_rel32(pe, "check_lumps_complete")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_name1")
    cmp_eax_imm32(pe, VERTEXES_NAME1)
    jne_rel32(pe, "check_lumps_complete")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_offset")
    mov_mem_abs32_eax(pe, "vertexes_offset")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_size")
    mov_mem_abs32_eax(pe, "vertexes_size")
    mov_mem_abs32_imm32(pe, "vertexes_found", 1)

    pe.label("check_lumps_complete")
    mov_reg_mem_abs32(pe, "eax", "linedefs_found")
    test_eax_eax(pe)
    je_rel32(pe, "directory_next_entry")
    mov_reg_mem_abs32(pe, "eax", "vertexes_found")
    test_eax_eax(pe)
    jne_rel32(pe, "directory_scan_done")

    pe.label("directory_next_entry")
    dec_mem_abs32(pe, "directory_entries_remaining")
    x86.jmp_rel32(pe, "directory_scan_loop")

    pe.label("directory_scan_done")
    mov_reg_mem_abs32(pe, "eax", "linedefs_found")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")
    mov_reg_mem_abs32(pe, "eax", "vertexes_found")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")

    mov_reg_mem_abs32(pe, "eax", "vertexes_size")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")
    cmp_reg_imm32(pe, "eax", VERTEX_BUFFER_BYTES)
    ja_rel32(pe, "load_close_and_return")
    mov_reg_reg(pe, "edx", "eax")
    and_reg_imm32(pe, "edx", VERTEX_RECORD_SIZE - 1)
    test_reg_reg(pe, "edx")
    jne_rel32(pe, "load_close_and_return")
    shr_reg_imm8(pe, "eax", 2)
    mov_mem_abs32_eax(pe, "vertex_count")

    mov_reg_mem_abs32(pe, "eax", "linedefs_size")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")
    cmp_reg_imm32(pe, "eax", LINEDEF_BUFFER_BYTES)
    ja_rel32(pe, "load_close_and_return")
    xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "ecx", LINEDEF_RECORD_SIZE)
    div_ecx(pe)
    test_reg_reg(pe, "edx")
    jne_rel32(pe, "load_close_and_return")
    mov_mem_abs32_eax(pe, "linedef_count")

    x86.push_imm32(pe, FILE_BEGIN)
    x86.push_imm8(pe, 0)  # lpDistanceToMoveHigh
    push_mem_abs32(pe, "vertexes_offset")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "SetFilePointer")
    cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    je_rel32(pe, "load_close_and_return")

    x86.push_imm8(pe, 0)  # lpOverlapped
    push_abs32(pe, "bytes_read")
    push_mem_abs32(pe, "vertexes_size")
    push_abs32(pe, "vertexes_buffer")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")
    mov_reg_mem_abs32(pe, "eax", "bytes_read")
    cmp_reg_mem_abs32(pe, "eax", "vertexes_size")
    jne_rel32(pe, "load_close_and_return")

    x86.push_imm32(pe, FILE_BEGIN)
    x86.push_imm8(pe, 0)  # lpDistanceToMoveHigh
    push_mem_abs32(pe, "linedefs_offset")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "SetFilePointer")
    cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    je_rel32(pe, "load_close_and_return")

    x86.push_imm8(pe, 0)  # lpOverlapped
    push_abs32(pe, "bytes_read")
    push_mem_abs32(pe, "linedefs_size")
    push_abs32(pe, "linedefs_buffer")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")
    mov_reg_mem_abs32(pe, "eax", "bytes_read")
    cmp_reg_mem_abs32(pe, "eax", "linedefs_size")
    jne_rel32(pe, "load_close_and_return")

    mov_mem_abs32_imm32(pe, "map_loaded", 1)

    pe.label("load_close_and_return")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_render_map(pe: PE32) -> None:
    pe.label("render_map")
    mov_reg_mem_abs32(pe, "eax", "map_loaded")
    test_eax_eax(pe)
    jne_rel32(pe, "render_have_map")
    x86.call_rel32(pe, "render_error_pattern")
    x86.ret(pe)

    pe.label("render_have_map")
    x86.call_rel32(pe, "clear_framebuffer")
    x86.call_rel32(pe, "transform_vertices")
    x86.call_rel32(pe, "draw_linedefs")
    x86.ret(pe)


def emit_clear_framebuffer(pe: PE32) -> None:
    pe.label("clear_framebuffer")
    push_reg(pe, "edi")
    pe.emit(b"\xFC")  # cld
    mov_reg_abs32(pe, "edi", "framebuffer")
    x86.mov_reg_imm32(pe, "eax", COLOR_BACKGROUND)
    x86.mov_reg_imm32(pe, "ecx", FRAMEBUFFER_PIXELS)
    pe.emit(b"\xF3\xAB")  # rep stosd
    pop_reg(pe, "edi")
    x86.ret(pe)


def emit_render_error_pattern(pe: PE32) -> None:
    pe.label("render_error_pattern")
    push_reg(pe, "edi")
    pe.emit(b"\xFC")  # cld
    mov_reg_abs32(pe, "edi", "framebuffer")
    x86.mov_reg_imm32(pe, "eax", COLOR_ERROR)
    x86.mov_reg_imm32(pe, "ecx", FRAMEBUFFER_PIXELS)
    pe.emit(b"\xF3\xAB")  # rep stosd
    pop_reg(pe, "edi")
    x86.ret(pe)


def emit_transform_vertices(pe: PE32) -> None:
    pe.label("transform_vertices")
    push_reg(pe, "ecx")
    push_reg(pe, "edx")
    push_reg(pe, "esi")
    push_reg(pe, "edi")

    mov_reg_abs32(pe, "esi", "vertexes_buffer")
    mov_reg_abs32(pe, "edi", "screen_vertices")
    mov_reg_mem_abs32(pe, "ecx", "vertex_count")
    test_reg_reg(pe, "ecx")
    je_rel32(pe, "transform_vertices_done")

    pe.label("transform_vertices_loop")
    movsx_reg_word_ptr_reg(pe, "eax", "esi")
    add_reg_imm32(pe, "eax", -MAP_MIN_X)
    imul_reg_reg_imm32(pe, "eax", "eax", MAP_SCALE_16_16)
    sar_reg_imm8(pe, "eax", 16)
    add_reg_imm32(pe, "eax", SCREEN_X_OFFSET)
    mov_ptr_reg_eax(pe, "edi")

    movsx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 2)
    add_reg_imm32(pe, "eax", -MAP_MIN_Y)
    imul_reg_reg_imm32(pe, "eax", "eax", MAP_SCALE_16_16)
    sar_reg_imm8(pe, "eax", 16)
    x86.mov_reg_imm32(pe, "edx", SCREEN_Y_BOTTOM)
    sub_reg_reg(pe, "edx", "eax")
    mov_reg_reg(pe, "eax", "edx")
    mov_ptr_reg_disp8_eax(pe, "edi", 4)

    add_reg_imm32(pe, "esi", VERTEX_RECORD_SIZE)
    add_reg_imm32(pe, "edi", 8)
    dec_reg(pe, "ecx")
    jne_rel32(pe, "transform_vertices_loop")

    pe.label("transform_vertices_done")
    pop_reg(pe, "edi")
    pop_reg(pe, "esi")
    pop_reg(pe, "edx")
    pop_reg(pe, "ecx")
    x86.ret(pe)


def emit_draw_linedefs(pe: PE32) -> None:
    pe.label("draw_linedefs")
    push_reg(pe, "ebx")
    push_reg(pe, "esi")
    push_reg(pe, "edi")

    mov_reg_abs32(pe, "esi", "linedefs_buffer")
    mov_mem_abs32_reg(pe, "linedef_scan_ptr", "esi")
    mov_reg_mem_abs32(pe, "eax", "linedef_count")
    mov_mem_abs32_eax(pe, "linedefs_remaining")

    pe.label("linedef_loop")
    mov_reg_mem_abs32(pe, "eax", "linedefs_remaining")
    test_eax_eax(pe)
    je_rel32(pe, "linedef_done")

    mov_reg_mem_abs32(pe, "esi", "linedef_scan_ptr")
    movzx_reg_word_ptr_reg(pe, "eax", "esi")
    cmp_reg_mem_abs32(pe, "eax", "vertex_count")
    jae_rel32(pe, "linedef_skip")
    mov_reg_reg(pe, "ebx", "eax")
    shl_reg_imm8(pe, "ebx", 3)
    mov_reg_abs32(pe, "edi", "screen_vertices")
    add_reg_reg(pe, "edi", "ebx")
    mov_reg_ptr_reg(pe, "eax", "edi")
    mov_mem_abs32_eax(pe, "line_x0")
    mov_reg_ptr_reg_disp8(pe, "eax", "edi", 4)
    mov_mem_abs32_eax(pe, "line_y0")

    movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 2)
    cmp_reg_mem_abs32(pe, "eax", "vertex_count")
    jae_rel32(pe, "linedef_skip")
    mov_reg_reg(pe, "ebx", "eax")
    shl_reg_imm8(pe, "ebx", 3)
    mov_reg_abs32(pe, "edi", "screen_vertices")
    add_reg_reg(pe, "edi", "ebx")
    mov_reg_ptr_reg(pe, "eax", "edi")
    mov_mem_abs32_eax(pe, "line_x1")
    mov_reg_ptr_reg_disp8(pe, "eax", "edi", 4)
    mov_mem_abs32_eax(pe, "line_y1")

    movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 12)
    cmp_reg_imm32(pe, "eax", 0xFFFF)
    jne_rel32(pe, "linedef_two_sided")
    mov_mem_abs32_imm32(pe, "draw_color", COLOR_ONE_SIDED_LINE)
    x86.jmp_rel32(pe, "linedef_draw")

    pe.label("linedef_two_sided")
    mov_mem_abs32_imm32(pe, "draw_color", COLOR_TWO_SIDED_LINE)

    pe.label("linedef_draw")
    x86.call_rel32(pe, "draw_line")

    pe.label("linedef_skip")
    mov_reg_mem_abs32(pe, "esi", "linedef_scan_ptr")
    add_reg_imm32(pe, "esi", LINEDEF_RECORD_SIZE)
    mov_mem_abs32_reg(pe, "linedef_scan_ptr", "esi")
    dec_mem_abs32(pe, "linedefs_remaining")
    x86.jmp_rel32(pe, "linedef_loop")

    pe.label("linedef_done")
    pop_reg(pe, "edi")
    pop_reg(pe, "esi")
    pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_draw_line(pe: PE32) -> None:
    pe.label("draw_line")
    push_reg(pe, "ebx")
    push_reg(pe, "ecx")
    push_reg(pe, "edx")
    push_reg(pe, "esi")
    push_reg(pe, "edi")

    mov_reg_mem_abs32(pe, "eax", "line_x1")
    sub_reg_mem_abs32(pe, "eax", "line_x0")
    mov_mem_abs32_eax(pe, "line_dx")

    mov_reg_mem_abs32(pe, "eax", "line_y1")
    sub_reg_mem_abs32(pe, "eax", "line_y0")
    mov_mem_abs32_eax(pe, "line_dy")

    mov_reg_mem_abs32(pe, "eax", "line_dx")
    test_eax_eax(pe)
    jns_rel32(pe, "line_abs_dx_done")
    neg_reg(pe, "eax")
    pe.label("line_abs_dx_done")
    mov_mem_abs32_eax(pe, "line_abs_dx")

    mov_reg_mem_abs32(pe, "eax", "line_dy")
    test_eax_eax(pe)
    jns_rel32(pe, "line_abs_dy_done")
    neg_reg(pe, "eax")
    pe.label("line_abs_dy_done")
    mov_mem_abs32_eax(pe, "line_abs_dy")

    mov_reg_mem_abs32(pe, "eax", "line_abs_dx")
    cmp_reg_mem_abs32(pe, "eax", "line_abs_dy")
    jae_rel32(pe, "line_steps_selected")
    mov_reg_mem_abs32(pe, "eax", "line_abs_dy")
    pe.label("line_steps_selected")
    mov_mem_abs32_eax(pe, "line_steps")

    test_eax_eax(pe)
    jne_rel32(pe, "line_has_steps")
    mov_reg_mem_abs32(pe, "eax", "line_x0")
    mov_mem_abs32_eax(pe, "plot_x")
    mov_reg_mem_abs32(pe, "eax", "line_y0")
    mov_mem_abs32_eax(pe, "plot_y")
    x86.call_rel32(pe, "plot_pixel")
    x86.jmp_rel32(pe, "line_done")

    pe.label("line_has_steps")
    mov_reg_mem_abs32(pe, "eax", "line_x0")
    shl_reg_imm8(pe, "eax", 16)
    mov_mem_abs32_eax(pe, "line_x_fixed")

    mov_reg_mem_abs32(pe, "eax", "line_y0")
    shl_reg_imm8(pe, "eax", 16)
    mov_mem_abs32_eax(pe, "line_y_fixed")

    mov_reg_mem_abs32(pe, "eax", "line_dx")
    shl_reg_imm8(pe, "eax", 16)
    cdq(pe)
    mov_reg_mem_abs32(pe, "ecx", "line_steps")
    idiv_ecx(pe)
    mov_mem_abs32_eax(pe, "line_x_inc")

    mov_reg_mem_abs32(pe, "eax", "line_dy")
    shl_reg_imm8(pe, "eax", 16)
    cdq(pe)
    mov_reg_mem_abs32(pe, "ecx", "line_steps")
    idiv_ecx(pe)
    mov_mem_abs32_eax(pe, "line_y_inc")

    mov_reg_mem_abs32(pe, "eax", "line_steps")
    add_reg_imm32(pe, "eax", 1)
    mov_mem_abs32_eax(pe, "line_steps_remaining")

    pe.label("line_draw_loop")
    mov_reg_mem_abs32(pe, "eax", "line_x_fixed")
    sar_reg_imm8(pe, "eax", 16)
    mov_mem_abs32_eax(pe, "plot_x")
    mov_reg_mem_abs32(pe, "eax", "line_y_fixed")
    sar_reg_imm8(pe, "eax", 16)
    mov_mem_abs32_eax(pe, "plot_y")
    x86.call_rel32(pe, "plot_pixel")

    mov_reg_mem_abs32(pe, "eax", "line_x_fixed")
    add_reg_mem_abs32(pe, "eax", "line_x_inc")
    mov_mem_abs32_eax(pe, "line_x_fixed")

    mov_reg_mem_abs32(pe, "eax", "line_y_fixed")
    add_reg_mem_abs32(pe, "eax", "line_y_inc")
    mov_mem_abs32_eax(pe, "line_y_fixed")

    dec_mem_abs32(pe, "line_steps_remaining")
    jne_rel32(pe, "line_draw_loop")

    pe.label("line_done")
    pop_reg(pe, "edi")
    pop_reg(pe, "esi")
    pop_reg(pe, "edx")
    pop_reg(pe, "ecx")
    pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_plot_pixel(pe: PE32) -> None:
    pe.label("plot_pixel")
    mov_reg_mem_abs32(pe, "eax", "plot_x")
    cmp_reg_imm32(pe, "eax", FRAMEBUFFER_WIDTH)
    jae_rel32(pe, "plot_pixel_done")

    mov_reg_mem_abs32(pe, "ebx", "plot_y")
    cmp_reg_imm32(pe, "ebx", FRAMEBUFFER_HEIGHT)
    jae_rel32(pe, "plot_pixel_done")

    mov_reg_reg(pe, "edx", "ebx")
    shl_reg_imm8(pe, "ebx", 8)
    shl_reg_imm8(pe, "edx", 6)
    add_reg_reg(pe, "ebx", "edx")
    add_reg_reg(pe, "ebx", "eax")
    shl_reg_imm8(pe, "ebx", 2)

    mov_reg_abs32(pe, "edi", "framebuffer")
    add_reg_reg(pe, "edi", "ebx")
    mov_reg_mem_abs32(pe, "eax", "draw_color")
    mov_ptr_reg_eax(pe, "edi")

    pe.label("plot_pixel_done")
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
    pe.label("wad_file_handle")
    pe.emit_u32(0)
    pe.label("bytes_read")
    pe.emit_u32(0)
    pe.label("directory_entries_remaining")
    pe.emit_u32(0)
    pe.label("map_scan_active")
    pe.emit_u32(0)
    pe.label("linedefs_found")
    pe.emit_u32(0)
    pe.label("vertexes_found")
    pe.emit_u32(0)
    pe.label("map_loaded")
    pe.emit_u32(0)
    pe.label("linedefs_offset")
    pe.emit_u32(0)
    pe.label("linedefs_size")
    pe.emit_u32(0)
    pe.label("vertexes_offset")
    pe.emit_u32(0)
    pe.label("vertexes_size")
    pe.emit_u32(0)
    pe.label("vertex_count")
    pe.emit_u32(0)
    pe.label("linedef_count")
    pe.emit_u32(0)
    pe.label("linedef_scan_ptr")
    pe.emit_u32(0)
    pe.label("linedefs_remaining")
    pe.emit_u32(0)

    pe.label("line_x0")
    pe.emit_u32(0)
    pe.label("line_y0")
    pe.emit_u32(0)
    pe.label("line_x1")
    pe.emit_u32(0)
    pe.label("line_y1")
    pe.emit_u32(0)
    pe.label("line_dx")
    pe.emit_u32(0)
    pe.label("line_dy")
    pe.emit_u32(0)
    pe.label("line_abs_dx")
    pe.emit_u32(0)
    pe.label("line_abs_dy")
    pe.emit_u32(0)
    pe.label("line_steps")
    pe.emit_u32(0)
    pe.label("line_steps_remaining")
    pe.emit_u32(0)
    pe.label("line_x_fixed")
    pe.emit_u32(0)
    pe.label("line_y_fixed")
    pe.emit_u32(0)
    pe.label("line_x_inc")
    pe.emit_u32(0)
    pe.label("line_y_inc")
    pe.emit_u32(0)
    pe.label("plot_x")
    pe.emit_u32(0)
    pe.label("plot_y")
    pe.emit_u32(0)
    pe.label("draw_color")
    pe.emit_u32(COLOR_ONE_SIDED_LINE)

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
    pe.emit_u32(BI_RGB)
    pe.emit_u32(FRAMEBUFFER_BYTES)
    pe.emit_u32(0)
    pe.emit_u32(0)
    pe.emit_u32(0)
    pe.emit_u32(0)

    pe.align_section(2)
    pe.label("class_name")
    emit_utf16z(pe, WINDOW_CLASS_NAME)
    pe.label("window_title")
    emit_utf16z(pe, WINDOW_TITLE)
    pe.label("wad_path_w")
    emit_utf16z(pe, WAD_PATH)

    pe.align_section(4)
    pe.label("vertexes_buffer")
    pe.emit_zeros(VERTEX_BUFFER_BYTES)

    pe.align_section(4)
    pe.label("linedefs_buffer")
    pe.emit_zeros(LINEDEF_BUFFER_BYTES)

    pe.align_section(4)
    pe.label("screen_vertices")
    pe.emit_zeros(MAX_SCREEN_VERTEX_BYTES)

    pe.align_section(4)
    pe.label("framebuffer")
    pe.emit_zeros(FRAMEBUFFER_BYTES)


def build_stage05_map_probe_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    emit_wndproc(pe)
    emit_load_map_data(pe)
    emit_render_map(pe)
    emit_clear_framebuffer(pe)
    emit_render_error_pattern(pe)
    emit_transform_vertices(pe)
    emit_draw_linedefs(pe)
    emit_draw_line(pe)
    emit_plot_pixel(pe)
    emit_data(pe)
    return pe.build("entry")


def write_stage05_map_probe_exe(path: str | Path) -> bytes:
    image = build_stage05_map_probe_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the Phase 10 PE32 x86 Win32 top-down map probe executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/stage05_map_probe.exe",
        help="path to write, default: build/stage05_map_probe.exe",
    )
    args = parser.parse_args()
    write_stage05_map_probe_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
