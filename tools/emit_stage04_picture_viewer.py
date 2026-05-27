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
WINDOW_WIDTH = 656
WINDOW_HEIGHT = 439
WINDOW_STYLE = WS_OVERLAPPEDWINDOW | WS_VISIBLE
WNDCLASSEXW_SIZE = 48
PAINTSTRUCT_SIZE = 64

WAD_HEADER_SIZE = 12
WAD_DIRECTORY_ENTRY_SIZE = 16
IWAD_MAGIC = 0x44415749
PWAD_MAGIC = 0x44415750
PLAYPAL_BYTES = 256 * 3
PICTURE_BUFFER_BYTES = 128 * 1024

PLAYPAL_NAME0 = int.from_bytes(b"PLAY", "little")
PLAYPAL_NAME1 = int.from_bytes(b"PAL\x00", "little")
TITLEPIC_NAME0 = int.from_bytes(b"TITL", "little")
TITLEPIC_NAME1 = int.from_bytes(b"EPIC", "little")
TITLEPIC_WIDTH_HEIGHT = (FRAMEBUFFER_HEIGHT << 16) | FRAMEBUFFER_WIDTH

WINDOW_CLASS_NAME = "InferenceDoomStage04PictureViewer"
WINDOW_TITLE = "Inference Doom - Stage 04 Picture Viewer"
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


def mov_ptr_reg_eax(pe: PE32, base: str) -> None:
    pe.emit(bytes([0x89, x86.modrm(0, "eax", base)]))


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


def and_reg_imm32(pe: PE32, reg: str, value: int) -> None:
    if x86.reg_code(reg) == x86.reg_code("eax"):
        pe.emit(b"\x25")
    else:
        pe.emit(bytes([0x81, x86.modrm(3, 4, reg)]))
    pe.emit_u32(value)


def shl_reg_imm8(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0xC1, x86.modrm(3, 4, reg), value & 0xFF]))


def or_reg_reg(pe: PE32, dst: str, src: str) -> None:
    pe.emit(bytes([0x09, x86.modrm(3, src, dst)]))


def xor_reg_reg(pe: PE32, dst: str, src: str) -> None:
    x86.xor_reg_reg(pe, dst, src)


def inc_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x40 + x86.reg_code(reg))


def dec_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x48 + x86.reg_code(reg))


def dec_mem_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\xFF\x0D")
    pe.write_abs32(label)


def cmp_eax_imm32(pe: PE32, value: int) -> None:
    pe.emit(b"\x3D")
    pe.emit_u32(value)


def cmp_reg_imm32(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0x81, x86.modrm(3, 7, reg)]))
    pe.emit_u32(value)


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


def jbe_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x86")
    pe.write_rel32(label)


def mov_al_ptr_reg(pe: PE32, base: str) -> None:
    pe.emit(bytes([0x8A, x86.modrm(0, 0, base)]))


def mov_al_ptr_reg_disp8(pe: PE32, base: str, displacement: int) -> None:
    pe.emit(bytes([0x8A, x86.modrm(1, 0, base), displacement & 0xFF]))


def mov_dl_ptr_reg(pe: PE32, base: str) -> None:
    pe.emit(bytes([0x8A, x86.modrm(0, 2, base)]))


def mov_dl_ptr_reg_disp8(pe: PE32, base: str, displacement: int) -> None:
    pe.emit(bytes([0x8A, x86.modrm(1, 2, base), displacement & 0xFF]))


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
    x86.call_rel32(pe, "load_wad_data")
    x86.call_rel32(pe, "render_loaded_pixels")

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


def emit_load_wad_data(pe: PE32) -> None:
    pe.label("load_wad_data")

    x86.push_imm8(pe, 0)  # hTemplateFile
    x86.push_imm32(pe, FILE_ATTRIBUTE_NORMAL)
    x86.push_imm32(pe, OPEN_EXISTING)
    x86.push_imm8(pe, 0)  # lpSecurityAttributes
    x86.push_imm32(pe, FILE_SHARE_READ)
    x86.push_imm32(pe, GENERIC_READ)
    push_abs32(pe, "wad_path_w")
    x86.call_import(pe, KERNEL32, "CreateFileW")
    cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    jne_rel32(pe, "load_file_opened")
    x86.ret(pe)

    pe.label("load_file_opened")
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
    je_rel32(pe, "load_magic_ok")
    cmp_eax_imm32(pe, PWAD_MAGIC)
    jne_rel32(pe, "load_close_and_return")

    pe.label("load_magic_ok")
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
    cmp_eax_imm32(pe, PLAYPAL_NAME0)
    jne_rel32(pe, "check_titlepic_name")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_name1")
    cmp_eax_imm32(pe, PLAYPAL_NAME1)
    jne_rel32(pe, "check_titlepic_name")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_offset")
    mov_mem_abs32_eax(pe, "playpal_offset")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_size")
    mov_mem_abs32_eax(pe, "playpal_size")

    pe.label("check_titlepic_name")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_name0")
    cmp_eax_imm32(pe, TITLEPIC_NAME0)
    jne_rel32(pe, "directory_next_entry")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_name1")
    cmp_eax_imm32(pe, TITLEPIC_NAME1)
    jne_rel32(pe, "directory_next_entry")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_offset")
    mov_mem_abs32_eax(pe, "titlepic_offset")
    mov_reg_mem_abs32(pe, "eax", "directory_lump_size")
    mov_mem_abs32_eax(pe, "titlepic_size")

    pe.label("directory_next_entry")
    dec_mem_abs32(pe, "directory_entries_remaining")
    x86.jmp_rel32(pe, "directory_scan_loop")

    pe.label("directory_scan_done")
    mov_reg_mem_abs32(pe, "eax", "playpal_offset")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")
    mov_reg_mem_abs32(pe, "eax", "playpal_size")
    cmp_reg_imm32(pe, "eax", PLAYPAL_BYTES)
    jb_rel32(pe, "load_close_and_return")

    x86.push_imm32(pe, FILE_BEGIN)
    x86.push_imm8(pe, 0)  # lpDistanceToMoveHigh
    push_mem_abs32(pe, "playpal_offset")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "SetFilePointer")
    cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    je_rel32(pe, "load_close_and_return")

    x86.push_imm8(pe, 0)  # lpOverlapped
    push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, PLAYPAL_BYTES)
    push_abs32(pe, "playpal")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")
    mov_reg_mem_abs32(pe, "eax", "bytes_read")
    cmp_eax_imm32(pe, PLAYPAL_BYTES)
    jne_rel32(pe, "load_close_and_return")
    mov_mem_abs32_imm32(pe, "palette_loaded", 1)

    mov_reg_mem_abs32(pe, "eax", "titlepic_offset")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")
    mov_reg_mem_abs32(pe, "eax", "titlepic_size")
    cmp_reg_imm32(pe, "eax", 8)
    jbe_rel32(pe, "load_close_and_return")
    cmp_reg_imm32(pe, "eax", PICTURE_BUFFER_BYTES)
    ja_rel32(pe, "load_close_and_return")

    x86.push_imm32(pe, FILE_BEGIN)
    x86.push_imm8(pe, 0)  # lpDistanceToMoveHigh
    push_mem_abs32(pe, "titlepic_offset")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "SetFilePointer")
    cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    je_rel32(pe, "load_close_and_return")

    x86.push_imm8(pe, 0)  # lpOverlapped
    push_abs32(pe, "bytes_read")
    push_mem_abs32(pe, "titlepic_size")
    push_abs32(pe, "picture_lump")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    test_eax_eax(pe)
    je_rel32(pe, "load_close_and_return")
    mov_reg_mem_abs32(pe, "eax", "bytes_read")
    cmp_reg_mem_abs32(pe, "eax", "titlepic_size")
    jne_rel32(pe, "load_close_and_return")
    mov_mem_abs32_imm32(pe, "picture_loaded", 1)

    pe.label("load_close_and_return")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_render_loaded_pixels(pe: PE32) -> None:
    pe.label("render_loaded_pixels")

    mov_reg_mem_abs32(pe, "eax", "palette_loaded")
    test_eax_eax(pe)
    jne_rel32(pe, "render_have_palette")
    x86.call_rel32(pe, "render_error_pattern")
    x86.ret(pe)

    pe.label("render_have_palette")
    mov_reg_mem_abs32(pe, "eax", "picture_loaded")
    test_eax_eax(pe)
    je_rel32(pe, "render_palette_fallback")
    x86.call_rel32(pe, "render_titlepic")
    mov_reg_mem_abs32(pe, "eax", "picture_rendered")
    test_eax_eax(pe)
    jne_rel32(pe, "render_loaded_done")

    pe.label("render_palette_fallback")
    x86.call_rel32(pe, "render_palette_bars")

    pe.label("render_loaded_done")
    x86.ret(pe)


def emit_color_from_playpal_index(pe: PE32, index_reg: str) -> None:
    mov_reg_reg(pe, "eax", index_reg)
    mov_reg_reg(pe, "edx", "eax")
    shl_reg_imm8(pe, "eax", 1)
    add_reg_reg(pe, "eax", "edx")
    mov_reg_abs32(pe, "esi", "playpal")
    add_reg_reg(pe, "esi", "eax")

    xor_reg_reg(pe, "eax", "eax")
    mov_al_ptr_reg(pe, "esi")
    shl_reg_imm8(pe, "eax", 16)
    xor_reg_reg(pe, "edx", "edx")
    mov_dl_ptr_reg_disp8(pe, "esi", 1)
    shl_reg_imm8(pe, "edx", 8)
    or_reg_reg(pe, "eax", "edx")
    xor_reg_reg(pe, "edx", "edx")
    mov_dl_ptr_reg_disp8(pe, "esi", 2)
    or_reg_reg(pe, "eax", "edx")


def emit_render_palette_bars(pe: PE32) -> None:
    pe.label("render_palette_bars")
    pe.emit(b"\x53")  # push ebx
    pe.emit(b"\x56")  # push esi
    pe.emit(b"\x57")  # push edi
    pe.emit(b"\xFC")  # cld

    mov_reg_abs32(pe, "edi", "framebuffer")
    xor_reg_reg(pe, "ebx", "ebx")  # y = 0

    pe.label("palette_y_loop")
    xor_reg_reg(pe, "ecx", "ecx")  # x = 0

    pe.label("palette_x_loop")
    mov_reg_reg(pe, "eax", "ecx")
    and_reg_imm32(pe, "eax", 0xFF)
    emit_color_from_playpal_index(pe, "eax")
    pe.emit(b"\xAB")  # stosd

    inc_reg(pe, "ecx")
    cmp_reg_imm32(pe, "ecx", FRAMEBUFFER_WIDTH)
    jne_rel32(pe, "palette_x_loop")

    inc_reg(pe, "ebx")
    cmp_reg_imm32(pe, "ebx", FRAMEBUFFER_HEIGHT)
    jne_rel32(pe, "palette_y_loop")

    pe.emit(b"\x5F")  # pop edi
    pe.emit(b"\x5E")  # pop esi
    pe.emit(b"\x5B")  # pop ebx
    x86.ret(pe)


def emit_clear_framebuffer(pe: PE32) -> None:
    pe.label("clear_framebuffer")
    pe.emit(b"\x57")  # push edi
    pe.emit(b"\xFC")  # cld
    mov_reg_abs32(pe, "edi", "framebuffer")
    xor_reg_reg(pe, "eax", "eax")
    x86.mov_reg_imm32(pe, "ecx", FRAMEBUFFER_PIXELS)
    pe.emit(b"\xF3\xAB")  # rep stosd
    pe.emit(b"\x5F")  # pop edi
    x86.ret(pe)


def emit_render_error_pattern(pe: PE32) -> None:
    pe.label("render_error_pattern")
    pe.emit(b"\x57")  # push edi
    pe.emit(b"\xFC")  # cld
    mov_reg_abs32(pe, "edi", "framebuffer")
    x86.mov_reg_imm32(pe, "eax", 0x00B00020)
    x86.mov_reg_imm32(pe, "ecx", FRAMEBUFFER_PIXELS)
    pe.emit(b"\xF3\xAB")  # rep stosd
    pe.emit(b"\x5F")  # pop edi
    x86.ret(pe)


def emit_render_titlepic(pe: PE32) -> None:
    pe.label("render_titlepic")
    pe.emit(b"\x53")  # push ebx
    pe.emit(b"\x56")  # push esi
    pe.emit(b"\x57")  # push edi

    mov_mem_abs32_imm32(pe, "picture_rendered", 0)
    mov_reg_mem_abs32(pe, "eax", "picture_width_height")
    cmp_eax_imm32(pe, TITLEPIC_WIDTH_HEIGHT)
    jne_rel32(pe, "render_titlepic_done")

    x86.call_rel32(pe, "clear_framebuffer")
    mov_mem_abs32_imm32(pe, "render_column_x", 0)

    pe.label("titlepic_column_loop")
    mov_reg_mem_abs32(pe, "eax", "render_column_x")
    cmp_reg_imm32(pe, "eax", FRAMEBUFFER_WIDTH)
    jae_rel32(pe, "render_titlepic_success")

    mov_reg_reg(pe, "ebx", "eax")
    shl_reg_imm8(pe, "ebx", 2)
    mov_reg_abs32(pe, "esi", "picture_column_offsets")
    add_reg_reg(pe, "esi", "ebx")
    mov_reg_ptr_reg(pe, "esi", "esi")
    mov_reg_abs32(pe, "edx", "picture_lump")
    add_reg_reg(pe, "esi", "edx")
    mov_mem_abs32_reg(pe, "render_post_ptr", "esi")

    pe.label("titlepic_post_loop")
    mov_reg_mem_abs32(pe, "esi", "render_post_ptr")
    xor_reg_reg(pe, "eax", "eax")
    mov_al_ptr_reg(pe, "esi")
    cmp_reg_imm32(pe, "eax", 255)
    je_rel32(pe, "titlepic_next_column")
    mov_mem_abs32_eax(pe, "post_top")

    xor_reg_reg(pe, "eax", "eax")
    mov_al_ptr_reg_disp8(pe, "esi", 1)
    mov_mem_abs32_eax(pe, "post_length")
    test_eax_eax(pe)
    je_rel32(pe, "titlepic_finish_post")

    add_reg_imm32(pe, "esi", 3)
    mov_reg_reg(pe, "ebx", "esi")  # source pixels

    mov_reg_mem_abs32(pe, "eax", "post_top")
    mov_reg_reg(pe, "edx", "eax")
    shl_reg_imm8(pe, "eax", 8)
    shl_reg_imm8(pe, "edx", 6)
    add_reg_reg(pe, "eax", "edx")
    add_reg_mem_abs32(pe, "eax", "render_column_x")
    shl_reg_imm8(pe, "eax", 2)
    mov_reg_abs32(pe, "edi", "framebuffer")
    add_reg_reg(pe, "edi", "eax")

    mov_reg_mem_abs32(pe, "ecx", "post_length")

    pe.label("titlepic_pixel_loop")
    xor_reg_reg(pe, "eax", "eax")
    mov_al_ptr_reg(pe, "ebx")
    emit_color_from_playpal_index(pe, "eax")
    mov_ptr_reg_eax(pe, "edi")
    add_reg_imm32(pe, "edi", FRAMEBUFFER_WIDTH * 4)
    inc_reg(pe, "ebx")
    dec_reg(pe, "ecx")
    jne_rel32(pe, "titlepic_pixel_loop")

    pe.label("titlepic_finish_post")
    mov_reg_mem_abs32(pe, "eax", "render_post_ptr")
    add_reg_mem_abs32(pe, "eax", "post_length")
    add_reg_imm32(pe, "eax", 4)
    mov_mem_abs32_eax(pe, "render_post_ptr")
    x86.jmp_rel32(pe, "titlepic_post_loop")

    pe.label("titlepic_next_column")
    mov_reg_mem_abs32(pe, "eax", "render_column_x")
    add_reg_imm32(pe, "eax", 1)
    mov_mem_abs32_eax(pe, "render_column_x")
    x86.jmp_rel32(pe, "titlepic_column_loop")

    pe.label("render_titlepic_success")
    mov_mem_abs32_imm32(pe, "picture_rendered", 1)

    pe.label("render_titlepic_done")
    pe.emit(b"\x5F")  # pop edi
    pe.emit(b"\x5E")  # pop esi
    pe.emit(b"\x5B")  # pop ebx
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
    pe.label("palette_loaded")
    pe.emit_u32(0)
    pe.label("picture_loaded")
    pe.emit_u32(0)
    pe.label("picture_rendered")
    pe.emit_u32(0)
    pe.label("directory_entries_remaining")
    pe.emit_u32(0)
    pe.label("playpal_offset")
    pe.emit_u32(0)
    pe.label("playpal_size")
    pe.emit_u32(0)
    pe.label("titlepic_offset")
    pe.emit_u32(0)
    pe.label("titlepic_size")
    pe.emit_u32(0)
    pe.label("render_column_x")
    pe.emit_u32(0)
    pe.label("render_post_ptr")
    pe.emit_u32(0)
    pe.label("post_top")
    pe.emit_u32(0)
    pe.label("post_length")
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
    pe.label("playpal")
    pe.emit_zeros(PLAYPAL_BYTES)

    pe.align_section(4)
    pe.label("picture_lump")
    pe.label("picture_width_height")
    pe.emit_u32(0)
    pe.label("picture_left_top")
    pe.emit_u32(0)
    pe.label("picture_column_offsets")
    pe.emit_zeros(PICTURE_BUFFER_BYTES - 8)

    pe.align_section(4)
    pe.label("framebuffer")
    pe.emit_zeros(FRAMEBUFFER_BYTES)


def build_stage04_picture_viewer_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    emit_wndproc(pe)
    emit_load_wad_data(pe)
    emit_render_loaded_pixels(pe)
    emit_render_palette_bars(pe)
    emit_clear_framebuffer(pe)
    emit_render_error_pattern(pe)
    emit_render_titlepic(pe)
    emit_data(pe)
    return pe.build("entry")


def write_stage04_picture_viewer_exe(path: str | Path) -> bytes:
    image = build_stage04_picture_viewer_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the Phase 8 PE32 x86 Win32 WAD picture viewer executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/stage04_picture_viewer.exe",
        help="path to write, default: build/stage04_picture_viewer.exe",
    )
    args = parser.parse_args()
    write_stage04_picture_viewer_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
