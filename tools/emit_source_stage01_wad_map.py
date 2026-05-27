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

CS_VREDRAW = 0x0001
CS_HREDRAW = 0x0002
COLOR_WINDOW = 5
CW_USEDEFAULT = 0x80000000
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

DT_WORDBREAK = 0x00000010
DT_EXPANDTABS = 0x00000040
DT_NOPREFIX = 0x00000800
DRAW_TEXT_FLAGS = DT_WORDBREAK | DT_EXPANDTABS | DT_NOPREFIX

WINDOW_WIDTH = 820
WINDOW_HEIGHT = 520
WINDOW_STYLE = WS_OVERLAPPEDWINDOW | WS_VISIBLE
WNDCLASSEXW_SIZE = 48
PAINTSTRUCT_SIZE = 64

WAD_HEADER_SIZE = 12
WAD_DIRECTORY_ENTRY_SIZE = 16
MAX_WAD_LUMPS = 8192
WAD_DIRECTORY_BUFFER_BYTES = MAX_WAD_LUMPS * WAD_DIRECTORY_ENTRY_SIZE
IWAD_MAGIC = 0x44415749
PWAD_MAGIC = 0x44415750

MAPVERTEX_RECORD_SIZE = 4
MAPSECTOR_RECORD_SIZE = 26
MAPSIDEDEF_RECORD_SIZE = 30
MAPLINEDEF_RECORD_SIZE = 14

VERTEX_T_RECORD_SIZE = 8
SECTOR_T_RECORD_SIZE = 36
SIDE_T_RECORD_SIZE = 40
LINE_T_RECORD_SIZE = 64

VERTEXES_BUFFER_BYTES = 64 * 1024
SECTORS_BUFFER_BYTES = 32 * 1024
SIDEDEFS_BUFFER_BYTES = 128 * 1024
LINEDEFS_BUFFER_BYTES = 128 * 1024
MAP_RAW_BUFFER_BYTES = 128 * 1024

MAX_VERTEXES = VERTEXES_BUFFER_BYTES // VERTEX_T_RECORD_SIZE
MAX_SECTORS = SECTORS_BUFFER_BYTES // SECTOR_T_RECORD_SIZE
MAX_SIDEDEFS = SIDEDEFS_BUFFER_BYTES // SIDE_T_RECORD_SIZE
MAX_LINEDEFS = LINEDEFS_BUFFER_BYTES // LINE_T_RECORD_SIZE

ML_LABEL = 0
ML_THINGS = 1
ML_LINEDEFS = 2
ML_SIDEDEFS = 3
ML_VERTEXES = 4
ML_SEGS = 5
ML_SSECTORS = 6
ML_NODES = 7
ML_SECTORS = 8
ML_REJECT = 9
ML_BLOCKMAP = 10

ST_HORIZONTAL = 0
ST_VERTICAL = 1
ST_POSITIVE = 2
ST_NEGATIVE = 3

LINE_V1 = 0
LINE_V2 = 4
LINE_DX = 8
LINE_DY = 12
LINE_FLAGS = 16
LINE_SPECIAL = 18
LINE_TAG = 20
LINE_SIDENUM0 = 22
LINE_SIDENUM1 = 24
LINE_BBOX_TOP = 28
LINE_BBOX_BOTTOM = 32
LINE_BBOX_LEFT = 36
LINE_BBOX_RIGHT = 40
LINE_SLOPETYPE = 44
LINE_FRONTSECTOR = 48
LINE_BACKSECTOR = 52
LINE_VALIDCOUNT = 56
LINE_SPECIALDATA = 60

WINDOW_CLASS_NAME = "InferenceDoomSourceStage01WadMap"
WINDOW_TITLE = "Inference Doom - Source Stage 01 WAD/Map"
WAD_PATH = r"third_party\freedoom\freedoom2.wad"

SOURCE_TRACE = (
    ("reference/chocolate-doom/src/w_wad.c", "W_NumLumps", "wad_num_lumps"),
    ("reference/chocolate-doom/src/w_wad.c", "W_CheckNumForName", "wad_check_num_for_name"),
    ("reference/chocolate-doom/src/w_wad.c", "W_GetNumForName", "wad_get_num_for_name"),
    ("reference/chocolate-doom/src/w_wad.c", "W_LumpLength", "wad_lump_length"),
    ("reference/chocolate-doom/src/w_wad.c", "W_ReadLump", "wad_read_lump"),
    ("reference/chocolate-doom/src/doom/p_setup.c", "P_LoadVertexes", "map_load_vertexes"),
    ("reference/chocolate-doom/src/doom/p_setup.c", "P_LoadSectors", "map_load_sectors"),
    ("reference/chocolate-doom/src/doom/p_setup.c", "P_LoadSideDefs", "map_load_sidedefs"),
    ("reference/chocolate-doom/src/doom/p_setup.c", "P_LoadLineDefs", "map_load_linedefs"),
)


def checked_record_count(byte_count: int, record_size: int) -> int:
    if byte_count < 0:
        raise ValueError("negative byte count")
    if byte_count % record_size:
        raise ValueError(f"{byte_count} is not aligned to {record_size}-byte records")
    return byte_count // record_size


def emit_set_status_ptrs(pe: PE32, status_label: str, title_label: str) -> None:
    x86.mov_mem_abs32_abs32(pe, "status_text_ptr", status_label)
    x86.mov_mem_abs32_abs32(pe, "status_title_ptr", title_label)


def emit_divide_size_to_count(
    pe: PE32,
    *,
    size_label: str,
    count_label: str,
    record_size: int,
    max_count: int,
    fail_label: str,
) -> None:
    x86.mov_reg_mem_abs32(pe, "eax", size_label)
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, fail_label)
    x86.cmp_reg_imm32(pe, "eax", MAP_RAW_BUFFER_BYTES)
    x86.ja_rel32(pe, fail_label)
    x86.xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "ecx", record_size)
    x86.div_reg(pe, "ecx")
    x86.test_reg_reg(pe, "edx")
    x86.jne_rel32(pe, fail_label)
    x86.cmp_reg_imm32(pe, "eax", max_count)
    x86.ja_rel32(pe, fail_label)
    x86.mov_mem_abs32_eax(pe, count_label)


def emit_entry(pe: PE32) -> None:
    pe.label("entry")

    x86.push_imm8(pe, 0)
    x86.call_import(pe, KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")

    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("class_registered")
    x86.call_rel32(pe, "source_stage01_load_wad_map")

    x86.push_imm8(pe, 0)  # lpParam
    x86.push_mem_abs32(pe, "wc_hInstance")
    x86.push_imm8(pe, 0)  # hMenu
    x86.push_imm8(pe, 0)  # hWndParent
    x86.push_imm32(pe, WINDOW_HEIGHT)
    x86.push_imm32(pe, WINDOW_WIDTH)
    x86.push_imm32(pe, CW_USEDEFAULT)
    x86.push_imm32(pe, CW_USEDEFAULT)
    x86.push_imm32(pe, WINDOW_STYLE)
    x86.push_abs32(pe, "window_title_w")
    x86.push_abs32(pe, "class_name")
    x86.push_imm8(pe, 0)  # dwExStyle
    x86.call_import(pe, USER32, "CreateWindowExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_mem_abs32(pe, "status_title_ptr")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, USER32, "SetWindowTextA")

    x86.push_imm8(pe, SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, USER32, "UpdateWindow")

    pe.label("message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, USER32, "GetMessageW")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "message_error")

    x86.push_abs32(pe, "message")
    x86.call_import(pe, USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "message_loop")

    pe.label("clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, KERNEL32, "ExitProcess")


def emit_wndproc(pe: PE32) -> None:
    pe.label("wndproc")
    x86.emit_function_prologue(pe)

    x86.mov_eax_ebp_disp8(pe, 12)
    x86.cmp_eax_imm32(pe, WM_DESTROY)
    x86.je_rel32(pe, "wndproc_destroy")
    x86.cmp_eax_imm32(pe, WM_PAINT)
    x86.je_rel32(pe, "wndproc_paint")

    pe.label("wndproc_default")
    x86.push_ebp_disp8(pe, 20)
    x86.push_ebp_disp8(pe, 16)
    x86.push_ebp_disp8(pe, 12)
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, USER32, "DefWindowProcW")
    x86.emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_destroy")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, USER32, "PostQuitMessage")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_paint")
    x86.push_abs32(pe, "paint_struct")
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, USER32, "BeginPaint")
    x86.mov_mem_abs32_eax(pe, "paint_hdc")

    x86.push_abs32(pe, "client_rect")
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, USER32, "GetClientRect")

    x86.push_imm32(pe, DRAW_TEXT_FLAGS)
    x86.push_abs32(pe, "client_rect")
    x86.push_imm32(pe, 0xFFFFFFFF)
    x86.push_mem_abs32(pe, "status_text_ptr")
    x86.push_mem_abs32(pe, "paint_hdc")
    x86.call_import(pe, USER32, "DrawTextA")

    x86.push_abs32(pe, "paint_struct")
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, USER32, "EndPaint")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.emit_function_epilogue_ret(pe, 16)


def emit_source_stage01_load_wad_map(pe: PE32) -> None:
    pe.label("source_stage01_load_wad_map")
    x86.mov_mem_abs32_imm32(pe, "map_loaded", 0)
    emit_set_status_ptrs(pe, "status_load_failed", "status_title_failed")

    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, FILE_ATTRIBUTE_NORMAL)
    x86.push_imm32(pe, OPEN_EXISTING)
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, FILE_SHARE_READ)
    x86.push_imm32(pe, GENERIC_READ)
    x86.push_abs32(pe, "wad_path_w")
    x86.call_import(pe, KERNEL32, "CreateFileW")
    x86.cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    x86.jne_rel32(pe, "source_stage01_file_opened")
    emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage01_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage01_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage01_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage01_magic_ok")
    x86.cmp_eax_imm32(pe, PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage01_close_and_return")

    pe.label("source_stage01_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage01_close_and_return")

    x86.call_rel32(pe, "source_stage01_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage01_close_and_return")

    x86.call_rel32(pe, "build_success_status")

    pe.label("source_stage01_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_load_wad_directory(pe: PE32) -> None:
    pe.label("load_wad_directory")
    x86.mov_reg_mem_abs32(pe, "eax", "wad_lump_count")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "load_wad_directory_fail")
    x86.cmp_reg_imm32(pe, "eax", MAX_WAD_LUMPS)
    x86.ja_rel32(pe, "load_wad_directory_fail")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_directory_offset")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "load_wad_directory_fail")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_lump_count")
    x86.shl_reg_imm8(pe, "eax", 4)
    x86.mov_mem_abs32_eax(pe, "wad_directory_bytes")

    x86.push_imm32(pe, FILE_BEGIN)
    x86.push_imm8(pe, 0)
    x86.push_mem_abs32(pe, "wad_directory_offset")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "SetFilePointer")
    x86.cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    x86.je_rel32(pe, "load_wad_directory_fail")

    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_mem_abs32(pe, "wad_directory_bytes")
    x86.push_abs32(pe, "lump_directory")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "load_wad_directory_fail")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_reg_mem_abs32(pe, "eax", "wad_directory_bytes")
    x86.jne_rel32(pe, "load_wad_directory_fail")

    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)

    pe.label("load_wad_directory_fail")
    emit_set_status_ptrs(pe, "status_directory_failed", "status_title_failed")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def emit_wad_num_lumps(pe: PE32) -> None:
    pe.label("wad_num_lumps")
    x86.mov_reg_mem_abs32(pe, "eax", "wad_lump_count")
    x86.ret(pe)


def emit_wad_check_num_for_name(pe: PE32) -> None:
    pe.label("wad_check_num_for_name")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_reg_mem_abs32(pe, "ecx", "wad_lump_count")
    x86.test_reg_reg(pe, "ecx")
    x86.je_rel32(pe, "wad_check_name_not_found")
    x86.mov_reg_ebp_disp8(pe, "edi", 8)
    x86.mov_reg_reg(pe, "ebx", "ecx")
    x86.dec_reg(pe, "ebx")

    pe.label("wad_check_name_loop")
    x86.mov_reg_reg(pe, "eax", "ebx")
    x86.shl_reg_imm8(pe, "eax", 4)
    x86.mov_reg_abs32(pe, "esi", "lump_directory")
    x86.add_reg_reg(pe, "esi", "eax")

    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 8)
    x86.mov_reg_ptr_reg(pe, "edx", "edi")
    x86.cmp_reg_reg(pe, "eax", "edx")
    x86.jne_rel32(pe, "wad_check_name_next")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 12)
    x86.mov_reg_ptr_reg_disp8(pe, "edx", "edi", 4)
    x86.cmp_reg_reg(pe, "eax", "edx")
    x86.je_rel32(pe, "wad_check_name_found")

    pe.label("wad_check_name_next")
    x86.test_reg_reg(pe, "ebx")
    x86.je_rel32(pe, "wad_check_name_not_found")
    x86.dec_reg(pe, "ebx")
    x86.jmp_rel32(pe, "wad_check_name_loop")

    pe.label("wad_check_name_found")
    x86.mov_reg_reg(pe, "eax", "ebx")
    x86.jmp_rel32(pe, "wad_check_name_done")

    pe.label("wad_check_name_not_found")
    x86.mov_reg_imm32(pe, "eax", 0xFFFFFFFF)

    pe.label("wad_check_name_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_wad_get_num_for_name(pe: PE32) -> None:
    pe.label("wad_get_num_for_name")
    x86.emit_function_prologue(pe)
    x86.push_ebp_disp8(pe, 8)
    x86.call_rel32(pe, "wad_check_num_for_name")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.jne_rel32(pe, "wad_get_num_done")
    x86.mov_mem_abs32_imm32(pe, "loader_error_code", 1)
    pe.label("wad_get_num_done")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_wad_lump_length(pe: PE32) -> None:
    pe.label("wad_lump_length")
    x86.emit_function_prologue(pe)
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.cmp_reg_mem_abs32(pe, "eax", "wad_lump_count")
    x86.jae_rel32(pe, "wad_lump_length_bad_index")
    x86.shl_reg_imm8(pe, "eax", 4)
    x86.mov_reg_abs32(pe, "esi", "lump_directory")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 4)
    x86.emit_function_epilogue_ret(pe, 4)

    pe.label("wad_lump_length_bad_index")
    x86.mov_mem_abs32_imm32(pe, "loader_error_code", 2)
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_wad_read_lump(pe: PE32) -> None:
    pe.label("wad_read_lump")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "esi")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.cmp_reg_mem_abs32(pe, "eax", "wad_lump_count")
    x86.jae_rel32(pe, "wad_read_lump_fail")
    x86.shl_reg_imm8(pe, "eax", 4)
    x86.mov_reg_abs32(pe, "esi", "lump_directory")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "esi")
    x86.mov_mem_abs32_eax(pe, "active_lump_offset")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 4)
    x86.mov_mem_abs32_eax(pe, "active_lump_size")

    x86.push_imm32(pe, FILE_BEGIN)
    x86.push_imm8(pe, 0)
    x86.push_mem_abs32(pe, "active_lump_offset")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "SetFilePointer")
    x86.cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    x86.je_rel32(pe, "wad_read_lump_fail")

    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_mem_abs32(pe, "active_lump_size")
    x86.push_ebp_disp8(pe, 12)
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "wad_read_lump_fail")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_reg_mem_abs32(pe, "eax", "active_lump_size")
    x86.jne_rel32(pe, "wad_read_lump_fail")

    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, "wad_read_lump_done")

    pe.label("wad_read_lump_fail")
    x86.mov_mem_abs32_imm32(pe, "loader_error_code", 3)
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("wad_read_lump_done")
    x86.pop_reg(pe, "esi")
    x86.emit_function_epilogue_ret(pe, 8)


def emit_source_stage01_load_map(pe: PE32) -> None:
    pe.label("source_stage01_load_map")
    emit_set_status_ptrs(pe, "status_map_failed", "status_title_failed")

    x86.push_abs32(pe, "map01_name")
    x86.call_rel32(pe, "wad_get_num_for_name")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "source_stage01_load_map_fail")
    x86.mov_mem_abs32_eax(pe, "map_marker_lump")

    x86.add_reg_imm32(pe, "eax", ML_SECTORS)
    x86.cmp_reg_mem_abs32(pe, "eax", "wad_lump_count")
    x86.jae_rel32(pe, "source_stage01_load_map_fail")

    x86.mov_reg_mem_abs32(pe, "eax", "map_marker_lump")
    x86.add_reg_imm32(pe, "eax", ML_VERTEXES)
    x86.mov_mem_abs32_eax(pe, "vertexes_lump_index")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "map_load_vertexes")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage01_load_map_fail")

    x86.mov_reg_mem_abs32(pe, "eax", "map_marker_lump")
    x86.add_reg_imm32(pe, "eax", ML_SECTORS)
    x86.mov_mem_abs32_eax(pe, "sectors_lump_index")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "map_load_sectors")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage01_load_map_fail")

    x86.mov_reg_mem_abs32(pe, "eax", "map_marker_lump")
    x86.add_reg_imm32(pe, "eax", ML_SIDEDEFS)
    x86.mov_mem_abs32_eax(pe, "sidedefs_lump_index")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "map_load_sidedefs")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage01_load_map_fail")

    x86.mov_reg_mem_abs32(pe, "eax", "map_marker_lump")
    x86.add_reg_imm32(pe, "eax", ML_LINEDEFS)
    x86.mov_mem_abs32_eax(pe, "linedefs_lump_index")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "map_load_linedefs")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage01_load_map_fail")

    x86.mov_mem_abs32_imm32(pe, "map_loaded", 1)
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)

    pe.label("source_stage01_load_map_fail")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def emit_read_current_lump_to_raw(pe: PE32, fail_label: str) -> None:
    x86.push_abs32(pe, "map_raw_buffer")
    x86.push_ebp_disp8(pe, 8)
    x86.call_rel32(pe, "wad_read_lump")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, fail_label)


def emit_map_load_vertexes(pe: PE32) -> None:
    pe.label("map_load_vertexes")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.push_ebp_disp8(pe, 8)
    x86.call_rel32(pe, "wad_lump_length")
    x86.mov_mem_abs32_eax(pe, "vertexes_size")
    emit_divide_size_to_count(
        pe,
        size_label="vertexes_size",
        count_label="vertex_count",
        record_size=MAPVERTEX_RECORD_SIZE,
        max_count=MAX_VERTEXES,
        fail_label="map_load_vertexes_fail",
    )
    emit_read_current_lump_to_raw(pe, "map_load_vertexes_fail")

    x86.mov_reg_abs32(pe, "esi", "map_raw_buffer")
    x86.mov_reg_abs32(pe, "edi", "vertexes_buffer")
    x86.mov_reg_mem_abs32(pe, "ecx", "vertex_count")

    pe.label("map_load_vertexes_loop")
    x86.movsx_reg_word_ptr_reg(pe, "eax", "esi")
    x86.shl_reg_imm8(pe, "eax", 16)
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.movsx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 2)
    x86.shl_reg_imm8(pe, "eax", 16)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 4)
    x86.add_reg_imm32(pe, "esi", MAPVERTEX_RECORD_SIZE)
    x86.add_reg_imm32(pe, "edi", VERTEX_T_RECORD_SIZE)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "map_load_vertexes_loop")

    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, "map_load_vertexes_done")

    pe.label("map_load_vertexes_fail")
    x86.mov_mem_abs32_imm32(pe, "loader_error_code", 10)
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("map_load_vertexes_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "ecx")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_map_load_sectors(pe: PE32) -> None:
    pe.label("map_load_sectors")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.push_ebp_disp8(pe, 8)
    x86.call_rel32(pe, "wad_lump_length")
    x86.mov_mem_abs32_eax(pe, "sectors_size")
    emit_divide_size_to_count(
        pe,
        size_label="sectors_size",
        count_label="sector_count",
        record_size=MAPSECTOR_RECORD_SIZE,
        max_count=MAX_SECTORS,
        fail_label="map_load_sectors_fail",
    )
    emit_read_current_lump_to_raw(pe, "map_load_sectors_fail")

    x86.mov_reg_abs32(pe, "esi", "map_raw_buffer")
    x86.mov_reg_abs32(pe, "edi", "sectors_buffer")
    x86.mov_reg_mem_abs32(pe, "ecx", "sector_count")

    pe.label("map_load_sectors_loop")
    x86.movsx_reg_word_ptr_reg(pe, "eax", "esi")
    x86.shl_reg_imm8(pe, "eax", 16)
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.movsx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 2)
    x86.shl_reg_imm8(pe, "eax", 16)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 4)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 4)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 8)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 8)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 12)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 12)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 16)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 16)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 20)
    x86.movsx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 20)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 24)
    x86.movsx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 22)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 28)
    x86.movsx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 24)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 32)
    x86.add_reg_imm32(pe, "esi", MAPSECTOR_RECORD_SIZE)
    x86.add_reg_imm32(pe, "edi", SECTOR_T_RECORD_SIZE)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "map_load_sectors_loop")

    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, "map_load_sectors_done")

    pe.label("map_load_sectors_fail")
    x86.mov_mem_abs32_imm32(pe, "loader_error_code", 11)
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("map_load_sectors_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "ecx")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_map_load_sidedefs(pe: PE32) -> None:
    pe.label("map_load_sidedefs")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.push_ebp_disp8(pe, 8)
    x86.call_rel32(pe, "wad_lump_length")
    x86.mov_mem_abs32_eax(pe, "sidedefs_size")
    emit_divide_size_to_count(
        pe,
        size_label="sidedefs_size",
        count_label="sidedef_count",
        record_size=MAPSIDEDEF_RECORD_SIZE,
        max_count=MAX_SIDEDEFS,
        fail_label="map_load_sidedefs_fail",
    )
    emit_read_current_lump_to_raw(pe, "map_load_sidedefs_fail")

    x86.mov_reg_abs32(pe, "esi", "map_raw_buffer")
    x86.mov_reg_abs32(pe, "edi", "sidedefs_buffer")
    x86.mov_reg_mem_abs32(pe, "ecx", "sidedef_count")

    pe.label("map_load_sidedefs_loop")
    x86.movsx_reg_word_ptr_reg(pe, "eax", "esi")
    x86.shl_reg_imm8(pe, "eax", 16)
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.movsx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 2)
    x86.shl_reg_imm8(pe, "eax", 16)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 4)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 4)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 8)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 8)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 12)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 12)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 16)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 16)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 20)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 20)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 24)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 24)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 28)

    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 28)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 32)
    x86.cmp_reg_mem_abs32(pe, "eax", "sector_count")
    x86.jae_rel32(pe, "map_load_sidedefs_null_sector")
    x86.imul_reg_reg_imm32(pe, "ebx", "eax", SECTOR_T_RECORD_SIZE)
    x86.mov_reg_abs32(pe, "eax", "sectors_buffer")
    x86.add_reg_reg(pe, "eax", "ebx")
    x86.jmp_rel32(pe, "map_load_sidedefs_store_sector")

    pe.label("map_load_sidedefs_null_sector")
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("map_load_sidedefs_store_sector")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", 36)
    x86.add_reg_imm32(pe, "esi", MAPSIDEDEF_RECORD_SIZE)
    x86.add_reg_imm32(pe, "edi", SIDE_T_RECORD_SIZE)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "map_load_sidedefs_loop")

    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, "map_load_sidedefs_done")

    pe.label("map_load_sidedefs_fail")
    x86.mov_mem_abs32_imm32(pe, "loader_error_code", 12)
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("map_load_sidedefs_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_map_load_linedefs(pe: PE32) -> None:
    pe.label("map_load_linedefs")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.push_ebp_disp8(pe, 8)
    x86.call_rel32(pe, "wad_lump_length")
    x86.mov_mem_abs32_eax(pe, "linedefs_size")
    emit_divide_size_to_count(
        pe,
        size_label="linedefs_size",
        count_label="linedef_count",
        record_size=MAPLINEDEF_RECORD_SIZE,
        max_count=MAX_LINEDEFS,
        fail_label="map_load_linedefs_fail",
    )
    emit_read_current_lump_to_raw(pe, "map_load_linedefs_fail")

    x86.mov_reg_abs32(pe, "esi", "map_raw_buffer")
    x86.mov_reg_abs32(pe, "edi", "lines_buffer")
    x86.mov_reg_mem_abs32(pe, "ecx", "linedef_count")

    pe.label("map_load_linedefs_loop")
    x86.movzx_reg_word_ptr_reg(pe, "eax", "esi")
    x86.cmp_reg_mem_abs32(pe, "eax", "vertex_count")
    x86.jae_rel32(pe, "map_load_linedefs_fail")
    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.shl_reg_imm8(pe, "ebx", 3)
    x86.mov_reg_abs32(pe, "eax", "vertexes_buffer")
    x86.add_reg_reg(pe, "eax", "ebx")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", LINE_V1)
    x86.mov_mem_abs32_eax(pe, "line_tmp_v1_ptr")

    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 2)
    x86.cmp_reg_mem_abs32(pe, "eax", "vertex_count")
    x86.jae_rel32(pe, "map_load_linedefs_fail")
    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.shl_reg_imm8(pe, "ebx", 3)
    x86.mov_reg_abs32(pe, "eax", "vertexes_buffer")
    x86.add_reg_reg(pe, "eax", "ebx")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", LINE_V2)
    x86.mov_mem_abs32_eax(pe, "line_tmp_v2_ptr")

    x86.mov_reg_mem_abs32(pe, "ebx", "line_tmp_v2_ptr")
    x86.mov_reg_ptr_reg(pe, "eax", "ebx")
    x86.mov_reg_mem_abs32(pe, "edx", "line_tmp_v1_ptr")
    x86.mov_reg_ptr_reg(pe, "edx", "edx")
    x86.sub_reg_reg(pe, "eax", "edx")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", LINE_DX)
    x86.mov_mem_abs32_eax(pe, "line_tmp_dx")

    x86.mov_reg_mem_abs32(pe, "ebx", "line_tmp_v2_ptr")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "ebx", 4)
    x86.mov_reg_mem_abs32(pe, "edx", "line_tmp_v1_ptr")
    x86.mov_reg_ptr_reg_disp8(pe, "edx", "edx", 4)
    x86.sub_reg_reg(pe, "eax", "edx")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", LINE_DY)
    x86.mov_mem_abs32_eax(pe, "line_tmp_dy")

    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 4)
    x86.mov_word_ptr_reg_disp8_ax(pe, "edi", LINE_FLAGS)
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 6)
    x86.mov_word_ptr_reg_disp8_ax(pe, "edi", LINE_SPECIAL)
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 8)
    x86.mov_word_ptr_reg_disp8_ax(pe, "edi", LINE_TAG)
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 10)
    x86.mov_word_ptr_reg_disp8_ax(pe, "edi", LINE_SIDENUM0)
    x86.mov_mem_abs32_eax(pe, "line_tmp_sidenum0")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 12)
    x86.mov_word_ptr_reg_disp8_ax(pe, "edi", LINE_SIDENUM1)
    x86.mov_mem_abs32_eax(pe, "line_tmp_sidenum1")

    x86.mov_reg_mem_abs32(pe, "eax", "line_tmp_dx")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "map_load_linedefs_slope_vertical")
    x86.mov_reg_mem_abs32(pe, "eax", "line_tmp_dy")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "map_load_linedefs_slope_horizontal")
    x86.mov_reg_mem_abs32(pe, "eax", "line_tmp_dx")
    x86.mov_reg_mem_abs32(pe, "edx", "line_tmp_dy")
    x86.xor_reg_reg(pe, "eax", "edx")
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "map_load_linedefs_slope_positive")
    x86.mov_reg_imm32(pe, "eax", ST_NEGATIVE)
    x86.jmp_rel32(pe, "map_load_linedefs_store_slope")

    pe.label("map_load_linedefs_slope_vertical")
    x86.mov_reg_imm32(pe, "eax", ST_VERTICAL)
    x86.jmp_rel32(pe, "map_load_linedefs_store_slope")

    pe.label("map_load_linedefs_slope_horizontal")
    x86.mov_reg_imm32(pe, "eax", ST_HORIZONTAL)
    x86.jmp_rel32(pe, "map_load_linedefs_store_slope")

    pe.label("map_load_linedefs_slope_positive")
    x86.mov_reg_imm32(pe, "eax", ST_POSITIVE)

    pe.label("map_load_linedefs_store_slope")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", LINE_SLOPETYPE)

    x86.mov_reg_mem_abs32(pe, "ebx", "line_tmp_v1_ptr")
    x86.mov_reg_ptr_reg(pe, "eax", "ebx")
    x86.mov_reg_mem_abs32(pe, "ebx", "line_tmp_v2_ptr")
    x86.mov_reg_ptr_reg(pe, "edx", "ebx")
    x86.cmp_reg_reg(pe, "eax", "edx")
    x86.jl_rel32(pe, "map_load_linedefs_x_v1_left")
    x86.mov_ptr_reg_disp8_reg(pe, "edi", LINE_BBOX_LEFT, "edx")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", LINE_BBOX_RIGHT)
    x86.jmp_rel32(pe, "map_load_linedefs_bbox_x_done")

    pe.label("map_load_linedefs_x_v1_left")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", LINE_BBOX_LEFT)
    x86.mov_ptr_reg_disp8_reg(pe, "edi", LINE_BBOX_RIGHT, "edx")

    pe.label("map_load_linedefs_bbox_x_done")
    x86.mov_reg_mem_abs32(pe, "ebx", "line_tmp_v1_ptr")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "ebx", 4)
    x86.mov_reg_mem_abs32(pe, "ebx", "line_tmp_v2_ptr")
    x86.mov_reg_ptr_reg_disp8(pe, "edx", "ebx", 4)
    x86.cmp_reg_reg(pe, "eax", "edx")
    x86.jl_rel32(pe, "map_load_linedefs_y_v1_bottom")
    x86.mov_ptr_reg_disp8_reg(pe, "edi", LINE_BBOX_BOTTOM, "edx")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", LINE_BBOX_TOP)
    x86.jmp_rel32(pe, "map_load_linedefs_bbox_y_done")

    pe.label("map_load_linedefs_y_v1_bottom")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", LINE_BBOX_BOTTOM)
    x86.mov_ptr_reg_disp8_reg(pe, "edi", LINE_BBOX_TOP, "edx")

    pe.label("map_load_linedefs_bbox_y_done")
    x86.mov_reg_mem_abs32(pe, "eax", "line_tmp_sidenum0")
    x86.cmp_eax_imm32(pe, 0xFFFF)
    x86.je_rel32(pe, "map_load_linedefs_null_frontsector")
    x86.cmp_reg_mem_abs32(pe, "eax", "sidedef_count")
    x86.jae_rel32(pe, "map_load_linedefs_null_frontsector")
    x86.imul_reg_reg_imm32(pe, "ebx", "eax", SIDE_T_RECORD_SIZE)
    x86.mov_reg_abs32(pe, "eax", "sidedefs_buffer")
    x86.add_reg_reg(pe, "eax", "ebx")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "eax", 36)
    x86.jmp_rel32(pe, "map_load_linedefs_store_frontsector")

    pe.label("map_load_linedefs_null_frontsector")
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("map_load_linedefs_store_frontsector")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", LINE_FRONTSECTOR)

    x86.mov_reg_mem_abs32(pe, "eax", "line_tmp_sidenum1")
    x86.cmp_eax_imm32(pe, 0xFFFF)
    x86.je_rel32(pe, "map_load_linedefs_null_backsector")
    x86.cmp_reg_mem_abs32(pe, "eax", "sidedef_count")
    x86.jae_rel32(pe, "map_load_linedefs_null_backsector")
    x86.imul_reg_reg_imm32(pe, "ebx", "eax", SIDE_T_RECORD_SIZE)
    x86.mov_reg_abs32(pe, "eax", "sidedefs_buffer")
    x86.add_reg_reg(pe, "eax", "ebx")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "eax", 36)
    x86.jmp_rel32(pe, "map_load_linedefs_store_backsector")

    pe.label("map_load_linedefs_null_backsector")
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("map_load_linedefs_store_backsector")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", LINE_BACKSECTOR)
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", LINE_VALIDCOUNT)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", LINE_SPECIALDATA)

    x86.add_reg_imm32(pe, "esi", MAPLINEDEF_RECORD_SIZE)
    x86.add_reg_imm32(pe, "edi", LINE_T_RECORD_SIZE)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "map_load_linedefs_loop")

    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, "map_load_linedefs_done")

    pe.label("map_load_linedefs_fail")
    x86.mov_mem_abs32_imm32(pe, "loader_error_code", 13)
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("map_load_linedefs_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_build_success_status(pe: PE32) -> None:
    pe.label("build_success_status")
    x86.mov_reg_abs32(pe, "edi", "status_success_buffer")

    append_c_string_label(pe, "status_success_header")
    append_c_string_label(pe, "status_path_prefix")
    append_c_string_label(pe, "wad_path_a")
    append_c_string_label(pe, "status_lumps_prefix")
    x86.call_rel32(pe, "wad_num_lumps")
    x86.call_rel32(pe, "append_u32_decimal")
    append_u32_label(pe, "status_map_lump_prefix", "map_marker_lump")
    append_u32_label(pe, "status_vertexes_prefix", "vertex_count")
    append_u32_label(pe, "status_sectors_prefix", "sector_count")
    append_u32_label(pe, "status_sidedefs_prefix", "sidedef_count")
    append_u32_label(pe, "status_linedefs_prefix", "linedef_count")
    append_i32_label(pe, "status_first_vertex_prefix", "first_vertex_x")
    append_i32_label(pe, "status_comma_prefix", "first_vertex_y")
    append_i32_label(pe, "status_first_sector_prefix", "first_sector_floor")
    append_i32_label(pe, "status_comma_prefix", "first_sector_ceiling")
    append_i32_label(pe, "status_first_linedef_prefix", "first_linedef_dx")
    append_i32_label(pe, "status_comma_prefix", "first_linedef_dy")
    append_u32_label(pe, "status_first_light_prefix", "first_sector_light")
    append_u32_label(pe, "status_first_side_sector_prefix", "first_sidedef_sector_index")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    x86.mov_reg_abs32(pe, "edi", "title_status_buffer")
    append_c_string_label(pe, "title_success_prefix")
    append_u32_label(pe, "title_v_prefix", "vertex_count")
    append_u32_label(pe, "title_l_prefix", "linedef_count")
    append_u32_label(pe, "title_sd_prefix", "sidedef_count")
    append_u32_label(pe, "title_sec_prefix", "sector_count")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def append_c_string_label(pe: PE32, label: str) -> None:
    x86.mov_reg_abs32(pe, "esi", label)
    x86.call_rel32(pe, "append_c_string")


def append_u32_label(pe: PE32, prefix_label: str, value_label: str) -> None:
    append_c_string_label(pe, prefix_label)
    x86.mov_reg_mem_abs32(pe, "eax", value_label)
    x86.call_rel32(pe, "append_u32_decimal")


def append_i32_label(pe: PE32, prefix_label: str, value_label: str) -> None:
    append_c_string_label(pe, prefix_label)
    x86.mov_reg_mem_abs32(pe, "eax", value_label)
    x86.call_rel32(pe, "append_i32_decimal")


def emit_append_c_string(pe: PE32) -> None:
    pe.label("append_c_string")
    x86.push_reg(pe, "eax")

    pe.label("append_c_string_loop")
    x86.mov_al_ptr_esi(pe)
    x86.cmp_al_imm8(pe, 0)
    x86.je_rel32(pe, "append_c_string_done")
    x86.mov_ptr_edi_al(pe)
    x86.inc_reg(pe, "esi")
    x86.inc_reg(pe, "edi")
    x86.jmp_rel32(pe, "append_c_string_loop")

    pe.label("append_c_string_done")
    x86.pop_reg(pe, "eax")
    x86.ret(pe)


def emit_append_u32_decimal(pe: PE32) -> None:
    pe.label("append_u32_decimal")
    x86.push_reg(pe, "eax")
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")

    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "append_decimal_nonzero")
    x86.mov_byte_ptr_edi_imm8(pe, ord("0"))
    x86.inc_reg(pe, "edi")
    x86.jmp_rel32(pe, "append_decimal_done")

    pe.label("append_decimal_nonzero")
    x86.mov_reg_abs32(pe, "esi", "number_scratch_end")
    x86.mov_reg_imm32(pe, "ecx", 10)

    pe.label("append_decimal_divide_loop")
    x86.xor_reg_reg(pe, "edx", "edx")
    x86.div_reg(pe, "ecx")
    x86.dec_reg(pe, "esi")
    x86.add_dl_imm8(pe, ord("0"))
    x86.mov_ptr_esi_dl(pe)
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "append_decimal_divide_loop")

    x86.mov_reg_abs32(pe, "ebx", "number_scratch_end")

    pe.label("append_decimal_copy_loop")
    x86.cmp_reg_reg(pe, "esi", "ebx")
    x86.je_rel32(pe, "append_decimal_done")
    x86.mov_dl_ptr_esi(pe)
    x86.mov_ptr_edi_dl(pe)
    x86.inc_reg(pe, "esi")
    x86.inc_reg(pe, "edi")
    x86.jmp_rel32(pe, "append_decimal_copy_loop")

    pe.label("append_decimal_done")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.pop_reg(pe, "eax")
    x86.ret(pe)


def emit_append_i32_decimal(pe: PE32) -> None:
    pe.label("append_i32_decimal")
    x86.push_reg(pe, "eax")
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "append_i32_nonnegative")
    x86.mov_byte_ptr_edi_imm8(pe, ord("-"))
    x86.inc_reg(pe, "edi")
    x86.neg_reg(pe, "eax")

    pe.label("append_i32_nonnegative")
    x86.call_rel32(pe, "append_u32_decimal")
    x86.pop_reg(pe, "eax")
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
    pe.label("paint_hdc")
    pe.emit_u32(0)
    pe.label("wad_file_handle")
    pe.emit_u32(0)
    pe.label("bytes_read")
    pe.emit_u32(0)
    pe.label("status_text_ptr")
    pe.write_abs32("status_not_run")
    pe.label("status_title_ptr")
    pe.write_abs32("status_title_not_run")
    pe.label("loader_error_code")
    pe.emit_u32(0)
    pe.label("map_loaded")
    pe.emit_u32(0)

    pe.label("wad_directory_bytes")
    pe.emit_u32(0)
    pe.label("active_lump_offset")
    pe.emit_u32(0)
    pe.label("active_lump_size")
    pe.emit_u32(0)

    pe.label("map_marker_lump")
    pe.emit_u32(0)
    pe.label("vertexes_lump_index")
    pe.emit_u32(0)
    pe.label("sectors_lump_index")
    pe.emit_u32(0)
    pe.label("sidedefs_lump_index")
    pe.emit_u32(0)
    pe.label("linedefs_lump_index")
    pe.emit_u32(0)

    pe.label("vertexes_size")
    pe.emit_u32(0)
    pe.label("sectors_size")
    pe.emit_u32(0)
    pe.label("sidedefs_size")
    pe.emit_u32(0)
    pe.label("linedefs_size")
    pe.emit_u32(0)
    pe.label("vertex_count")
    pe.emit_u32(0)
    pe.label("sector_count")
    pe.emit_u32(0)
    pe.label("sidedef_count")
    pe.emit_u32(0)
    pe.label("linedef_count")
    pe.emit_u32(0)
    pe.label("line_tmp_v1_ptr")
    pe.emit_u32(0)
    pe.label("line_tmp_v2_ptr")
    pe.emit_u32(0)
    pe.label("line_tmp_dx")
    pe.emit_u32(0)
    pe.label("line_tmp_dy")
    pe.emit_u32(0)
    pe.label("line_tmp_sidenum0")
    pe.emit_u32(0)
    pe.label("line_tmp_sidenum1")
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
    pe.emit_zeros(PAINTSTRUCT_SIZE)

    pe.align_section(4)
    pe.label("client_rect")
    pe.label("client_left")
    pe.emit_u32(12)
    pe.label("client_top")
    pe.emit_u32(12)
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

    pe.align_section(2)
    pe.label("class_name")
    x86.emit_utf16z(pe, WINDOW_CLASS_NAME)
    pe.label("window_title_w")
    x86.emit_utf16z(pe, WINDOW_TITLE)
    pe.label("wad_path_w")
    x86.emit_utf16z(pe, WAD_PATH)

    pe.align_section(1)
    pe.label("map01_name")
    pe.emit(b"MAP01\x00\x00\x00")
    pe.label("wad_path_a")
    x86.emit_asciiz(pe, WAD_PATH)

    pe.label("status_not_run")
    x86.emit_asciiz(pe, "source_stage01_wad_map has not run yet.")
    pe.label("status_open_failed")
    x86.emit_asciiz(pe, f"FAIL: could not open {WAD_PATH}")
    pe.label("status_directory_failed")
    x86.emit_asciiz(pe, "FAIL: could not build the runtime WAD lump directory.")
    pe.label("status_map_failed")
    x86.emit_asciiz(pe, "FAIL: could not find MAP01 or load its source-guided map lumps.")
    pe.label("status_load_failed")
    x86.emit_asciiz(pe, "FAIL: WAD/map source stage did not complete.")

    pe.label("status_title_not_run")
    x86.emit_asciiz(pe, f"{WINDOW_TITLE} | not run")
    pe.label("status_title_failed")
    x86.emit_asciiz(pe, f"{WINDOW_TITLE} | FAIL")

    pe.label("status_success_header")
    x86.emit_asciiz(pe, "source_stage01_wad_map\r\nWAD/map load OK\r\n")
    pe.label("status_path_prefix")
    x86.emit_asciiz(pe, "path: ")
    pe.label("status_lumps_prefix")
    x86.emit_asciiz(pe, "\r\nW_NumLumps: ")
    pe.label("status_map_lump_prefix")
    x86.emit_asciiz(pe, "\r\nMAP01 lump: ")
    pe.label("status_vertexes_prefix")
    x86.emit_asciiz(pe, "\r\nP_LoadVertexes count: ")
    pe.label("status_sectors_prefix")
    x86.emit_asciiz(pe, "\r\nP_LoadSectors count: ")
    pe.label("status_sidedefs_prefix")
    x86.emit_asciiz(pe, "\r\nP_LoadSideDefs count: ")
    pe.label("status_linedefs_prefix")
    x86.emit_asciiz(pe, "\r\nP_LoadLineDefs count: ")
    pe.label("status_first_vertex_prefix")
    x86.emit_asciiz(pe, "\r\nfirst vertex fixed: ")
    pe.label("status_first_sector_prefix")
    x86.emit_asciiz(pe, "\r\nfirst sector floor/ceiling fixed: ")
    pe.label("status_first_linedef_prefix")
    x86.emit_asciiz(pe, "\r\nfirst line dx/dy fixed: ")
    pe.label("status_first_light_prefix")
    x86.emit_asciiz(pe, "\r\nfirst sector light: ")
    pe.label("status_first_side_sector_prefix")
    x86.emit_asciiz(pe, "\r\nfirst sidedef sector index: ")
    pe.label("status_comma_prefix")
    x86.emit_asciiz(pe, ", ")

    pe.label("title_success_prefix")
    x86.emit_asciiz(pe, f"{WINDOW_TITLE} |")
    pe.label("title_v_prefix")
    x86.emit_asciiz(pe, " V=")
    pe.label("title_l_prefix")
    x86.emit_asciiz(pe, " L=")
    pe.label("title_sd_prefix")
    x86.emit_asciiz(pe, " SD=")
    pe.label("title_sec_prefix")
    x86.emit_asciiz(pe, " SEC=")

    pe.align_section(4)
    pe.label("number_scratch")
    pe.emit_zeros(16)
    pe.label("number_scratch_end")

    pe.align_section(4)
    pe.label("status_success_buffer")
    pe.emit_zeros(1024)
    pe.label("title_status_buffer")
    pe.emit_zeros(256)

    pe.align_section(4)
    pe.label("lump_directory")
    pe.emit_zeros(WAD_DIRECTORY_BUFFER_BYTES)

    pe.align_section(4)
    pe.label("map_raw_buffer")
    pe.emit_zeros(MAP_RAW_BUFFER_BYTES)

    pe.align_section(4)
    pe.label("vertexes_buffer")
    pe.label("first_vertex_x")
    pe.emit_zeros(4)
    pe.label("first_vertex_y")
    pe.emit_zeros(VERTEXES_BUFFER_BYTES - 4)

    pe.align_section(4)
    pe.label("sectors_buffer")
    pe.label("first_sector_floor")
    pe.emit_zeros(4)
    pe.label("first_sector_ceiling")
    pe.emit_zeros(20)
    pe.label("first_sector_light")
    pe.emit_zeros(SECTORS_BUFFER_BYTES - 24)

    pe.align_section(4)
    pe.label("sidedefs_buffer")
    pe.emit_zeros(32)
    pe.label("first_sidedef_sector_index")
    pe.emit_zeros(SIDEDEFS_BUFFER_BYTES - 32)

    pe.align_section(4)
    pe.label("lines_buffer")
    pe.emit_zeros(8)
    pe.label("first_linedef_dx")
    pe.emit_zeros(4)
    pe.label("first_linedef_dy")
    pe.emit_zeros(LINEDEFS_BUFFER_BYTES - 12)


def build_source_stage01_wad_map_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    emit_wndproc(pe)
    emit_source_stage01_load_wad_map(pe)
    emit_load_wad_directory(pe)
    emit_wad_num_lumps(pe)
    emit_wad_check_num_for_name(pe)
    emit_wad_get_num_for_name(pe)
    emit_wad_lump_length(pe)
    emit_wad_read_lump(pe)
    emit_source_stage01_load_map(pe)
    emit_map_load_vertexes(pe)
    emit_map_load_sectors(pe)
    emit_map_load_sidedefs(pe)
    emit_map_load_linedefs(pe)
    emit_build_success_status(pe)
    emit_append_c_string(pe)
    emit_append_u32_decimal(pe)
    emit_append_i32_decimal(pe)
    emit_data(pe)
    return pe.build("entry")


def write_source_stage01_wad_map_exe(path: str | Path) -> bytes:
    image = build_source_stage01_wad_map_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the source-guided PE32 x86 WAD/MAP setup executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/source_stage01_wad_map.exe",
        help="path to write, default: build/source_stage01_wad_map.exe",
    )
    args = parser.parse_args()
    write_source_stage01_wad_map_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
