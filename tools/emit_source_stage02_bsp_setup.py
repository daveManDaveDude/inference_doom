from __future__ import annotations

import argparse
import struct
import sys
from contextlib import contextmanager
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage01_wad_map as stage01
from tools import x86
from tools.pe32 import PE32


WINDOW_CLASS_NAME = "InferenceDoomSourceStage02BspSetup"
WINDOW_TITLE = "Inference Doom - Source Stage 02 BSP Setup"
WAD_PATH = stage01.WAD_PATH

ML_TWOSIDED = 4

MAPSUBSECTOR_RECORD_SIZE = 4
MAPSEG_RECORD_SIZE = 12
MAPNODE_RECORD_SIZE = 28

SUBSECTOR_T_RECORD_SIZE = 8
NODE_T_RECORD_SIZE = 52
SEG_T_RECORD_SIZE = 32

SUBSECTOR_SECTOR = 0
SUBSECTOR_NUMLINES = 4
SUBSECTOR_FIRSTLINE = 6

NODE_X = 0
NODE_Y = 4
NODE_DX = 8
NODE_DY = 12
NODE_BBOX = 16
NODE_CHILDREN = 48
NODE_CHILD0 = 48
NODE_CHILD1 = 50

SEG_V1 = 0
SEG_V2 = 4
SEG_OFFSET = 8
SEG_ANGLE = 12
SEG_SIDEDEF = 16
SEG_LINEDEF = 20
SEG_FRONTSECTOR = 24
SEG_BACKSECTOR = 28

SUBSECTORS_BUFFER_BYTES = 32 * 1024
NODES_BUFFER_BYTES = 128 * 1024
SEGS_BUFFER_BYTES = 128 * 1024

MAX_SUBSECTORS = SUBSECTORS_BUFFER_BYTES // SUBSECTOR_T_RECORD_SIZE
MAX_NODES = NODES_BUFFER_BYTES // NODE_T_RECORD_SIZE
MAX_SEGS = SEGS_BUFFER_BYTES // SEG_T_RECORD_SIZE
MAX_SECTOR_LINE_REFS = stage01.MAX_LINEDEFS * 2

_MAPSUBSECTOR_STRUCT = struct.Struct("<hh")
_MAPSEG_STRUCT = struct.Struct("<hhhhhh")
_MAPNODE_STRUCT = struct.Struct("<hhhhhhhhhhhhHH")

SOURCE_TRACE = stage01.SOURCE_TRACE + (
    ("reference/chocolate-doom/src/doom/p_setup.c", "P_LoadSubsectors", "map_load_subsectors"),
    ("reference/chocolate-doom/src/doom/p_setup.c", "P_LoadNodes", "map_load_nodes"),
    ("reference/chocolate-doom/src/doom/p_setup.c", "P_LoadSegs", "map_load_segs"),
    ("reference/chocolate-doom/src/doom/p_setup.c", "P_GroupLines", "map_group_lines"),
)

checked_record_count = stage01.checked_record_count


def parse_mapsubsectors(data: bytes) -> tuple[tuple[int, int], ...]:
    checked_record_count(len(data), MAPSUBSECTOR_RECORD_SIZE)
    return tuple(_MAPSUBSECTOR_STRUCT.iter_unpack(data))


def parse_mapsegs(data: bytes) -> tuple[tuple[int, int, int, int, int, int], ...]:
    checked_record_count(len(data), MAPSEG_RECORD_SIZE)
    return tuple(_MAPSEG_STRUCT.iter_unpack(data))


def parse_mapnodes(data: bytes) -> tuple[tuple[int, ...], ...]:
    checked_record_count(len(data), MAPNODE_RECORD_SIZE)
    return tuple(_MAPNODE_STRUCT.iter_unpack(data))


def sector_line_counts_for_loaded_map(loaded_map) -> tuple[int, ...]:
    counts = [0] * len(loaded_map.sectors)

    for line in loaded_map.linedefs:
        front_sector = None
        if line.right_sidedef != 0xFFFF:
            if line.right_sidedef < len(loaded_map.sidedefs):
                front_sector = loaded_map.sidedefs[line.right_sidedef].sector
                if front_sector < len(counts):
                    counts[front_sector] += 1

        if line.left_sidedef != 0xFFFF and line.left_sidedef < len(loaded_map.sidedefs):
            back_sector = loaded_map.sidedefs[line.left_sidedef].sector
            if back_sector < len(counts) and back_sector != front_sector:
                counts[back_sector] += 1

    return tuple(counts)


@contextmanager
def patched_stage01_window_labels():
    old_class = stage01.WINDOW_CLASS_NAME
    old_title = stage01.WINDOW_TITLE
    stage01.WINDOW_CLASS_NAME = WINDOW_CLASS_NAME
    stage01.WINDOW_TITLE = WINDOW_TITLE
    try:
        yield
    finally:
        stage01.WINDOW_CLASS_NAME = old_class
        stage01.WINDOW_TITLE = old_title


def emit_entry(pe: PE32) -> None:
    pe.label("entry")

    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")

    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")

    pe.label("class_registered")
    x86.call_rel32(pe, "source_stage02_load_wad_bsp")

    x86.push_imm8(pe, 0)
    x86.push_mem_abs32(pe, "wc_hInstance")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, stage01.WINDOW_HEIGHT)
    x86.push_imm32(pe, stage01.WINDOW_WIDTH)
    x86.push_imm32(pe, stage01.CW_USEDEFAULT)
    x86.push_imm32(pe, stage01.CW_USEDEFAULT)
    x86.push_imm32(pe, stage01.WINDOW_STYLE)
    x86.push_abs32(pe, "window_title_w")
    x86.push_abs32(pe, "class_name")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.USER32, "CreateWindowExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")

    pe.label("window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_mem_abs32(pe, "status_title_ptr")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")

    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")

    pe.label("message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "message_error")

    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "message_loop")

    pe.label("clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")

    pe.label("message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_source_stage02_load_wad_bsp(pe: PE32) -> None:
    pe.label("source_stage02_load_wad_bsp")
    x86.mov_mem_abs32_imm32(pe, "map_loaded", 0)
    stage01.emit_set_status_ptrs(pe, "status_load_failed", "status_title_failed")

    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, stage01.FILE_ATTRIBUTE_NORMAL)
    x86.push_imm32(pe, stage01.OPEN_EXISTING)
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, stage01.FILE_SHARE_READ)
    x86.push_imm32(pe, stage01.GENERIC_READ)
    x86.push_abs32(pe, "wad_path_w")
    x86.call_import(pe, stage01.KERNEL32, "CreateFileW")
    x86.cmp_eax_imm32(pe, stage01.INVALID_HANDLE_VALUE)
    x86.jne_rel32(pe, "source_stage02_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage02_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage02_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage02_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage02_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage02_close_and_return")

    pe.label("source_stage02_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage02_close_and_return")

    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage02_close_and_return")

    x86.call_rel32(pe, "build_success_status")

    pe.label("source_stage02_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_source_stage02_load_map(pe: PE32) -> None:
    pe.label("source_stage02_load_map")
    stage01.emit_set_status_ptrs(pe, "status_map_failed", "status_title_failed")

    x86.push_abs32(pe, "map01_name")
    x86.call_rel32(pe, "wad_get_num_for_name")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "source_stage02_load_map_fail")
    x86.mov_mem_abs32_eax(pe, "map_marker_lump")

    x86.add_reg_imm32(pe, "eax", stage01.ML_SECTORS)
    x86.cmp_reg_mem_abs32(pe, "eax", "wad_lump_count")
    x86.jae_rel32(pe, "source_stage02_load_map_fail")

    _load_map_lump(pe, stage01.ML_VERTEXES, "vertexes_lump_index", "map_load_vertexes")
    _load_map_lump(pe, stage01.ML_SECTORS, "sectors_lump_index", "map_load_sectors")
    _load_map_lump(pe, stage01.ML_SIDEDEFS, "sidedefs_lump_index", "map_load_sidedefs")
    _load_map_lump(pe, stage01.ML_LINEDEFS, "linedefs_lump_index", "map_load_linedefs")
    _load_map_lump(pe, stage01.ML_SSECTORS, "subsectors_lump_index", "map_load_subsectors")
    _load_map_lump(pe, stage01.ML_NODES, "nodes_lump_index", "map_load_nodes")
    _load_map_lump(pe, stage01.ML_SEGS, "segs_lump_index", "map_load_segs")

    x86.call_rel32(pe, "map_group_lines")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage02_load_map_fail")

    x86.mov_mem_abs32_imm32(pe, "map_loaded", 1)
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)

    pe.label("source_stage02_load_map_fail")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def _load_map_lump(pe: PE32, lump_offset: int, index_label: str, loader_label: str) -> None:
    x86.mov_reg_mem_abs32(pe, "eax", "map_marker_lump")
    x86.add_reg_imm32(pe, "eax", lump_offset)
    x86.mov_mem_abs32_eax(pe, index_label)
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, loader_label)
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage02_load_map_fail")


def emit_map_load_subsectors(pe: PE32) -> None:
    pe.label("map_load_subsectors")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.push_ebp_disp8(pe, 8)
    x86.call_rel32(pe, "wad_lump_length")
    x86.mov_mem_abs32_eax(pe, "subsectors_size")
    stage01.emit_divide_size_to_count(
        pe,
        size_label="subsectors_size",
        count_label="subsector_count",
        record_size=MAPSUBSECTOR_RECORD_SIZE,
        max_count=MAX_SUBSECTORS,
        fail_label="map_load_subsectors_fail",
    )
    stage01.emit_read_current_lump_to_raw(pe, "map_load_subsectors_fail")

    x86.mov_reg_abs32(pe, "esi", "map_raw_buffer")
    x86.mov_reg_abs32(pe, "edi", "subsectors_buffer")
    x86.mov_reg_mem_abs32(pe, "ecx", "subsector_count")

    pe.label("map_load_subsectors_loop")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.mov_ptr_reg_eax(pe, "edi")

    x86.movzx_reg_word_ptr_reg(pe, "eax", "esi")
    x86.mov_word_ptr_reg_disp8_ax(pe, "edi", SUBSECTOR_NUMLINES)
    x86.mov_reg_abs32(pe, "ebx", "subsectors_buffer")
    x86.cmp_reg_reg(pe, "edi", "ebx")
    x86.jne_rel32(pe, "map_load_subsectors_not_first_count")
    x86.mov_mem_abs32_eax(pe, "first_subsector_numlines_value")

    pe.label("map_load_subsectors_not_first_count")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 2)
    x86.mov_word_ptr_reg_disp8_ax(pe, "edi", SUBSECTOR_FIRSTLINE)
    x86.mov_reg_abs32(pe, "ebx", "subsectors_buffer")
    x86.cmp_reg_reg(pe, "edi", "ebx")
    x86.jne_rel32(pe, "map_load_subsectors_not_first_line")
    x86.mov_mem_abs32_eax(pe, "first_subsector_firstline_value")

    pe.label("map_load_subsectors_not_first_line")
    x86.add_reg_imm32(pe, "esi", MAPSUBSECTOR_RECORD_SIZE)
    x86.add_reg_imm32(pe, "edi", SUBSECTOR_T_RECORD_SIZE)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "map_load_subsectors_loop")

    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, "map_load_subsectors_done")

    pe.label("map_load_subsectors_fail")
    x86.mov_mem_abs32_imm32(pe, "loader_error_code", 20)
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("map_load_subsectors_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_map_load_nodes(pe: PE32) -> None:
    pe.label("map_load_nodes")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.push_ebp_disp8(pe, 8)
    x86.call_rel32(pe, "wad_lump_length")
    x86.mov_mem_abs32_eax(pe, "nodes_size")
    stage01.emit_divide_size_to_count(
        pe,
        size_label="nodes_size",
        count_label="node_count",
        record_size=MAPNODE_RECORD_SIZE,
        max_count=MAX_NODES,
        fail_label="map_load_nodes_fail",
    )
    x86.mov_reg_mem_abs32(pe, "eax", "node_count")
    x86.dec_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "root_node_index")
    stage01.emit_read_current_lump_to_raw(pe, "map_load_nodes_fail")

    x86.mov_reg_abs32(pe, "esi", "map_raw_buffer")
    x86.mov_reg_abs32(pe, "edi", "nodes_buffer")
    x86.mov_reg_mem_abs32(pe, "ecx", "node_count")

    pe.label("map_load_nodes_loop")
    _emit_signed_word_to_fixed_field(pe, 0, NODE_X)
    _emit_signed_word_to_fixed_field(pe, 2, NODE_Y)
    _emit_signed_word_to_fixed_field(pe, 4, NODE_DX)
    _emit_signed_word_to_fixed_field(pe, 6, NODE_DY)
    _emit_signed_word_to_fixed_field(pe, 8, NODE_BBOX + 0)
    _emit_signed_word_to_fixed_field(pe, 10, NODE_BBOX + 4)
    _emit_signed_word_to_fixed_field(pe, 12, NODE_BBOX + 8)
    _emit_signed_word_to_fixed_field(pe, 14, NODE_BBOX + 12)
    _emit_signed_word_to_fixed_field(pe, 16, NODE_BBOX + 16)
    _emit_signed_word_to_fixed_field(pe, 18, NODE_BBOX + 20)
    _emit_signed_word_to_fixed_field(pe, 20, NODE_BBOX + 24)
    _emit_signed_word_to_fixed_field(pe, 22, NODE_BBOX + 28)

    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 24)
    x86.mov_word_ptr_reg_disp8_ax(pe, "edi", NODE_CHILD0)
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 26)
    x86.mov_word_ptr_reg_disp8_ax(pe, "edi", NODE_CHILD1)

    x86.add_reg_imm32(pe, "esi", MAPNODE_RECORD_SIZE)
    x86.add_reg_imm32(pe, "edi", NODE_T_RECORD_SIZE)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "map_load_nodes_loop")

    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, "map_load_nodes_done")

    pe.label("map_load_nodes_fail")
    x86.mov_mem_abs32_imm32(pe, "loader_error_code", 21)
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("map_load_nodes_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "ecx")
    x86.emit_function_epilogue_ret(pe, 4)


def _emit_signed_word_to_fixed_field(pe: PE32, source_offset: int, target_offset: int) -> None:
    if source_offset == 0:
        x86.movsx_reg_word_ptr_reg(pe, "eax", "esi")
    else:
        x86.movsx_reg_word_ptr_reg_disp8(pe, "eax", "esi", source_offset)
    x86.shl_reg_imm8(pe, "eax", 16)
    if target_offset == 0:
        x86.mov_ptr_reg_eax(pe, "edi")
    else:
        x86.mov_ptr_reg_disp8_eax(pe, "edi", target_offset)


def emit_map_load_segs(pe: PE32) -> None:
    pe.label("map_load_segs")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.push_ebp_disp8(pe, 8)
    x86.call_rel32(pe, "wad_lump_length")
    x86.mov_mem_abs32_eax(pe, "segs_size")
    stage01.emit_divide_size_to_count(
        pe,
        size_label="segs_size",
        count_label="seg_count",
        record_size=MAPSEG_RECORD_SIZE,
        max_count=MAX_SEGS,
        fail_label="map_load_segs_fail",
    )
    stage01.emit_read_current_lump_to_raw(pe, "map_load_segs_fail")

    x86.mov_reg_abs32(pe, "esi", "map_raw_buffer")
    x86.mov_reg_abs32(pe, "edi", "segs_buffer")
    x86.mov_reg_mem_abs32(pe, "ecx", "seg_count")

    pe.label("map_load_segs_loop")
    x86.movzx_reg_word_ptr_reg(pe, "eax", "esi")
    x86.cmp_reg_mem_abs32(pe, "eax", "vertex_count")
    x86.jae_rel32(pe, "map_load_segs_fail")
    x86.mov_mem_abs32_eax(pe, "seg_tmp_v1_index")
    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.shl_reg_imm8(pe, "ebx", 3)
    x86.mov_reg_abs32(pe, "eax", "vertexes_buffer")
    x86.add_reg_reg(pe, "eax", "ebx")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", SEG_V1)

    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 2)
    x86.cmp_reg_mem_abs32(pe, "eax", "vertex_count")
    x86.jae_rel32(pe, "map_load_segs_fail")
    x86.mov_mem_abs32_eax(pe, "seg_tmp_v2_index")
    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.shl_reg_imm8(pe, "ebx", 3)
    x86.mov_reg_abs32(pe, "eax", "vertexes_buffer")
    x86.add_reg_reg(pe, "eax", "ebx")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", SEG_V2)

    x86.movsx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 10)
    x86.shl_reg_imm8(pe, "eax", 16)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", SEG_OFFSET)

    x86.movsx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 4)
    x86.shl_reg_imm8(pe, "eax", 16)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", SEG_ANGLE)

    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 6)
    x86.cmp_reg_mem_abs32(pe, "eax", "linedef_count")
    x86.jae_rel32(pe, "map_load_segs_fail")
    x86.mov_mem_abs32_eax(pe, "seg_tmp_linedef_index")
    x86.imul_reg_reg_imm32(pe, "ebx", "eax", stage01.LINE_T_RECORD_SIZE)
    x86.mov_reg_abs32(pe, "eax", "lines_buffer")
    x86.add_reg_reg(pe, "eax", "ebx")
    x86.mov_mem_abs32_eax(pe, "seg_tmp_linedef_ptr")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", SEG_LINEDEF)

    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", 8)
    x86.cmp_eax_imm32(pe, 1)
    x86.ja_rel32(pe, "map_load_segs_fail")
    x86.mov_mem_abs32_eax(pe, "seg_tmp_side")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "map_load_segs_get_side1")
    x86.mov_reg_mem_abs32(pe, "ebx", "seg_tmp_linedef_ptr")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "ebx", stage01.LINE_SIDENUM0)
    x86.jmp_rel32(pe, "map_load_segs_have_sidenum")

    pe.label("map_load_segs_get_side1")
    x86.mov_reg_mem_abs32(pe, "ebx", "seg_tmp_linedef_ptr")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "ebx", stage01.LINE_SIDENUM1)

    pe.label("map_load_segs_have_sidenum")
    x86.cmp_reg_mem_abs32(pe, "eax", "sidedef_count")
    x86.jae_rel32(pe, "map_load_segs_fail")
    x86.mov_mem_abs32_eax(pe, "seg_tmp_sidenum")
    _emit_store_seg_side_and_frontsector(pe)

    x86.mov_reg_mem_abs32(pe, "ebx", "seg_tmp_linedef_ptr")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "ebx", stage01.LINE_FLAGS)
    x86.and_reg_imm32(pe, "eax", ML_TWOSIDED)
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "map_load_segs_no_backsector")

    x86.mov_reg_mem_abs32(pe, "eax", "seg_tmp_side")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "map_load_segs_back_from_side0")
    x86.mov_reg_mem_abs32(pe, "ebx", "seg_tmp_linedef_ptr")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "ebx", stage01.LINE_SIDENUM1)
    x86.jmp_rel32(pe, "map_load_segs_have_back_sidenum")

    pe.label("map_load_segs_back_from_side0")
    x86.mov_reg_mem_abs32(pe, "ebx", "seg_tmp_linedef_ptr")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "ebx", stage01.LINE_SIDENUM0)

    pe.label("map_load_segs_have_back_sidenum")
    x86.cmp_reg_mem_abs32(pe, "eax", "sidedef_count")
    x86.jae_rel32(pe, "map_load_segs_no_backsector")
    x86.imul_reg_reg_imm32(pe, "ebx", "eax", stage01.SIDE_T_RECORD_SIZE)
    x86.mov_reg_abs32(pe, "eax", "sidedefs_buffer")
    x86.add_reg_reg(pe, "eax", "ebx")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "eax", 36)
    x86.jmp_rel32(pe, "map_load_segs_store_backsector")

    pe.label("map_load_segs_no_backsector")
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("map_load_segs_store_backsector")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", SEG_BACKSECTOR)

    x86.mov_reg_abs32(pe, "eax", "segs_buffer")
    x86.cmp_reg_reg(pe, "edi", "eax")
    x86.jne_rel32(pe, "map_load_segs_not_first")
    x86.mov_reg_mem_abs32(pe, "eax", "seg_tmp_v1_index")
    x86.mov_mem_abs32_eax(pe, "first_seg_v1_index")
    x86.mov_reg_mem_abs32(pe, "eax", "seg_tmp_v2_index")
    x86.mov_mem_abs32_eax(pe, "first_seg_v2_index")
    x86.mov_reg_mem_abs32(pe, "eax", "seg_tmp_linedef_index")
    x86.mov_mem_abs32_eax(pe, "first_seg_linedef_index")
    x86.mov_reg_mem_abs32(pe, "eax", "seg_tmp_side")
    x86.mov_mem_abs32_eax(pe, "first_seg_side")

    pe.label("map_load_segs_not_first")
    x86.add_reg_imm32(pe, "esi", MAPSEG_RECORD_SIZE)
    x86.add_reg_imm32(pe, "edi", SEG_T_RECORD_SIZE)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "map_load_segs_loop")

    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, "map_load_segs_done")

    pe.label("map_load_segs_fail")
    x86.mov_mem_abs32_imm32(pe, "loader_error_code", 22)
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("map_load_segs_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 4)


def _emit_store_seg_side_and_frontsector(pe: PE32) -> None:
    x86.imul_reg_reg_imm32(pe, "ebx", "eax", stage01.SIDE_T_RECORD_SIZE)
    x86.mov_reg_abs32(pe, "eax", "sidedefs_buffer")
    x86.add_reg_reg(pe, "eax", "ebx")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", SEG_SIDEDEF)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "eax", 36)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", SEG_FRONTSECTOR)


def emit_map_group_lines(pe: PE32) -> None:
    pe.label("map_group_lines")
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_reg_mem_abs32(pe, "eax", "sector_count")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "map_group_lines_fail")
    x86.mov_reg_mem_abs32(pe, "eax", "subsector_count")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "map_group_lines_fail")
    x86.mov_reg_mem_abs32(pe, "eax", "seg_count")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "map_group_lines_fail")

    x86.mov_reg_abs32(pe, "esi", "subsectors_buffer")
    x86.mov_reg_mem_abs32(pe, "ecx", "subsector_count")

    pe.label("map_group_subsector_loop")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", SUBSECTOR_FIRSTLINE)
    x86.cmp_reg_mem_abs32(pe, "eax", "seg_count")
    x86.jae_rel32(pe, "map_group_lines_fail")
    x86.shl_reg_imm8(pe, "eax", 5)
    x86.mov_reg_abs32(pe, "ebx", "segs_buffer")
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "ebx", SEG_SIDEDEF)
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "map_group_lines_fail")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "eax", 36)
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "map_group_lines_fail")
    x86.mov_ptr_reg_eax(pe, "esi")

    x86.mov_reg_abs32(pe, "ebx", "subsectors_buffer")
    x86.cmp_reg_reg(pe, "esi", "ebx")
    x86.jne_rel32(pe, "map_group_subsector_not_first")
    _emit_store_sector_index_from_eax(pe, "first_subsector_sector_index")

    pe.label("map_group_subsector_not_first")
    x86.add_reg_imm32(pe, "esi", SUBSECTOR_T_RECORD_SIZE)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "map_group_subsector_loop")

    _emit_clear_sector_group_arrays(pe)
    x86.mov_mem_abs32_imm32(pe, "total_grouped_line_refs", 0)

    x86.mov_reg_abs32(pe, "esi", "lines_buffer")
    x86.mov_reg_mem_abs32(pe, "ecx", "linedef_count")

    pe.label("map_group_count_loop")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage01.LINE_FRONTSECTOR)
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "map_group_count_skip_front")
    x86.call_rel32(pe, "group_count_sector_ref")

    pe.label("map_group_count_skip_front")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage01.LINE_BACKSECTOR)
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "map_group_count_next")
    x86.mov_reg_ptr_reg_disp8(pe, "edx", "esi", stage01.LINE_FRONTSECTOR)
    x86.cmp_reg_reg(pe, "eax", "edx")
    x86.je_rel32(pe, "map_group_count_next")
    x86.call_rel32(pe, "group_count_sector_ref")

    pe.label("map_group_count_next")
    x86.add_reg_imm32(pe, "esi", stage01.LINE_T_RECORD_SIZE)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "map_group_count_loop")

    x86.mov_reg_mem_abs32(pe, "eax", "total_grouped_line_refs")
    x86.cmp_reg_imm32(pe, "eax", MAX_SECTOR_LINE_REFS)
    x86.ja_rel32(pe, "map_group_lines_fail")

    _emit_build_sector_line_starts(pe)
    _emit_clear_sector_group_work_counts(pe)
    _emit_build_sector_line_table(pe)

    x86.mov_mem_abs32_imm32(pe, "map_grouped", 1)
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, "map_group_lines_done")

    pe.label("map_group_lines_fail")
    x86.mov_mem_abs32_imm32(pe, "loader_error_code", 23)
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("map_group_lines_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.ret(pe)


def _emit_store_sector_index_from_eax(pe: PE32, dst_label: str) -> None:
    x86.mov_reg_abs32(pe, "ebx", "sectors_buffer")
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "ebx", stage01.SECTOR_T_RECORD_SIZE)
    x86.div_reg(pe, "ebx")
    x86.mov_mem_abs32_eax(pe, dst_label)


def _emit_clear_sector_group_arrays(pe: PE32) -> None:
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.mov_reg_abs32(pe, "edi", "sector_line_counts")
    x86.mov_reg_abs32(pe, "esi", "sector_line_starts")
    x86.mov_reg_abs32(pe, "ebx", "sector_line_work_counts")
    x86.mov_reg_mem_abs32(pe, "ecx", "sector_count")

    pe.label("map_group_clear_arrays_loop")
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.mov_ptr_reg_eax(pe, "esi")
    x86.mov_ptr_reg_eax(pe, "ebx")
    x86.add_reg_imm32(pe, "edi", 4)
    x86.add_reg_imm32(pe, "esi", 4)
    x86.add_reg_imm32(pe, "ebx", 4)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "map_group_clear_arrays_loop")


def _emit_build_sector_line_starts(pe: PE32) -> None:
    x86.mov_reg_mem_abs32(pe, "eax", "sector_line_counts")
    x86.mov_mem_abs32_eax(pe, "first_sector_line_count")
    x86.mov_mem_abs32_imm32(pe, "sector_line_min_count", 0xFFFFFFFF)
    x86.mov_mem_abs32_imm32(pe, "sector_line_max_count", 0)
    x86.mov_mem_abs32_imm32(pe, "group_running_line_refs", 0)

    x86.mov_reg_abs32(pe, "edi", "sector_line_counts")
    x86.mov_reg_abs32(pe, "esi", "sector_line_starts")
    x86.mov_reg_mem_abs32(pe, "ecx", "sector_count")

    pe.label("map_group_starts_loop")
    x86.mov_reg_ptr_reg(pe, "eax", "edi")
    x86.mov_reg_mem_abs32(pe, "edx", "group_running_line_refs")
    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_reg(pe, "eax", "edx")
    x86.mov_ptr_reg_eax(pe, "esi")
    x86.mov_reg_reg(pe, "eax", "ebx")
    x86.add_reg_reg(pe, "edx", "eax")
    x86.mov_mem_abs32_reg(pe, "group_running_line_refs", "edx")

    x86.cmp_reg_mem_abs32(pe, "eax", "sector_line_min_count")
    x86.jae_rel32(pe, "map_group_starts_skip_min")
    x86.mov_mem_abs32_eax(pe, "sector_line_min_count")

    pe.label("map_group_starts_skip_min")
    x86.cmp_reg_mem_abs32(pe, "eax", "sector_line_max_count")
    x86.jbe_rel32(pe, "map_group_starts_skip_max")
    x86.mov_mem_abs32_eax(pe, "sector_line_max_count")

    pe.label("map_group_starts_skip_max")
    x86.add_reg_imm32(pe, "edi", 4)
    x86.add_reg_imm32(pe, "esi", 4)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "map_group_starts_loop")


def _emit_clear_sector_group_work_counts(pe: PE32) -> None:
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.mov_reg_abs32(pe, "ebx", "sector_line_work_counts")
    x86.mov_reg_mem_abs32(pe, "ecx", "sector_count")

    pe.label("map_group_clear_work_loop")
    x86.mov_ptr_reg_eax(pe, "ebx")
    x86.add_reg_imm32(pe, "ebx", 4)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "map_group_clear_work_loop")


def _emit_build_sector_line_table(pe: PE32) -> None:
    x86.mov_reg_abs32(pe, "esi", "lines_buffer")
    x86.mov_reg_mem_abs32(pe, "ecx", "linedef_count")

    pe.label("map_group_append_loop")
    x86.mov_reg_reg(pe, "edx", "esi")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage01.LINE_FRONTSECTOR)
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "map_group_append_skip_front")
    x86.call_rel32(pe, "group_append_sector_line")

    pe.label("map_group_append_skip_front")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage01.LINE_BACKSECTOR)
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "map_group_append_next")
    x86.mov_reg_ptr_reg_disp8(pe, "edx", "esi", stage01.LINE_FRONTSECTOR)
    x86.cmp_reg_reg(pe, "eax", "edx")
    x86.je_rel32(pe, "map_group_append_next")
    x86.mov_reg_reg(pe, "edx", "esi")
    x86.call_rel32(pe, "group_append_sector_line")

    pe.label("map_group_append_next")
    x86.add_reg_imm32(pe, "esi", stage01.LINE_T_RECORD_SIZE)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "map_group_append_loop")


def emit_group_count_sector_ref(pe: PE32) -> None:
    pe.label("group_count_sector_ref")
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "edx")

    x86.mov_reg_abs32(pe, "ebx", "sectors_buffer")
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "ebx", stage01.SECTOR_T_RECORD_SIZE)
    x86.div_reg(pe, "ebx")
    x86.cmp_reg_mem_abs32(pe, "eax", "sector_count")
    x86.jae_rel32(pe, "group_count_sector_done")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "ebx", "sector_line_counts")
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "ebx")
    x86.inc_reg(pe, "eax")
    x86.mov_ptr_reg_eax(pe, "ebx")
    x86.mov_reg_mem_abs32(pe, "eax", "total_grouped_line_refs")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "total_grouped_line_refs")

    pe.label("group_count_sector_done")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_group_append_sector_line(pe: PE32) -> None:
    pe.label("group_append_sector_line")
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.mov_mem_abs32_reg(pe, "group_tmp_line_ptr", "edx")

    x86.mov_reg_abs32(pe, "ebx", "sectors_buffer")
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "ebx", stage01.SECTOR_T_RECORD_SIZE)
    x86.div_reg(pe, "ebx")
    x86.cmp_reg_mem_abs32(pe, "eax", "sector_count")
    x86.jae_rel32(pe, "group_append_sector_done")
    x86.shl_reg_imm8(pe, "eax", 2)

    x86.mov_reg_abs32(pe, "ebx", "sector_line_starts")
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_ptr_reg(pe, "ecx", "ebx")

    x86.mov_reg_abs32(pe, "ebx", "sector_line_work_counts")
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_ptr_reg(pe, "esi", "ebx")
    x86.mov_reg_reg(pe, "edx", "esi")
    x86.inc_reg(pe, "edx")
    x86.mov_reg_reg(pe, "eax", "edx")
    x86.mov_ptr_reg_eax(pe, "ebx")

    x86.add_reg_reg(pe, "ecx", "esi")
    x86.cmp_reg_imm32(pe, "ecx", MAX_SECTOR_LINE_REFS)
    x86.jae_rel32(pe, "group_append_sector_done")
    x86.shl_reg_imm8(pe, "ecx", 2)
    x86.mov_reg_abs32(pe, "ebx", "sector_line_table")
    x86.add_reg_reg(pe, "ebx", "ecx")
    x86.mov_reg_mem_abs32(pe, "eax", "group_tmp_line_ptr")
    x86.mov_ptr_reg_eax(pe, "ebx")

    pe.label("group_append_sector_done")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_build_success_status(pe: PE32) -> None:
    pe.label("build_success_status")
    x86.mov_reg_abs32(pe, "edi", "status_success_buffer")

    stage01.append_c_string_label(pe, "status_stage02_success_header")
    stage01.append_c_string_label(pe, "status_path_prefix")
    stage01.append_c_string_label(pe, "wad_path_a")
    stage01.append_c_string_label(pe, "status_lumps_prefix")
    x86.call_rel32(pe, "wad_num_lumps")
    x86.call_rel32(pe, "append_u32_decimal")
    stage01.append_u32_label(pe, "status_map_lump_prefix", "map_marker_lump")
    stage01.append_u32_label(pe, "status_vertexes_prefix", "vertex_count")
    stage01.append_u32_label(pe, "status_sectors_prefix", "sector_count")
    stage01.append_u32_label(pe, "status_sidedefs_prefix", "sidedef_count")
    stage01.append_u32_label(pe, "status_linedefs_prefix", "linedef_count")
    stage01.append_u32_label(pe, "status_subsectors_prefix", "subsector_count")
    stage01.append_u32_label(pe, "status_nodes_prefix", "node_count")
    stage01.append_u32_label(pe, "status_segs_prefix", "seg_count")
    stage01.append_u32_label(pe, "status_root_node_prefix", "root_node_index")
    stage01.append_u32_label(pe, "status_first_subsector_prefix", "first_subsector_firstline_value")
    stage01.append_u32_label(pe, "status_slash_prefix", "first_subsector_numlines_value")
    stage01.append_u32_label(pe, "status_first_subsector_sector_prefix", "first_subsector_sector_index")
    stage01.append_u32_label(pe, "status_first_seg_prefix", "first_seg_v1_index")
    stage01.append_u32_label(pe, "status_slash_prefix", "first_seg_v2_index")
    stage01.append_u32_label(pe, "status_slash_prefix", "first_seg_linedef_index")
    stage01.append_u32_label(pe, "status_slash_prefix", "first_seg_side")
    stage01.append_u32_label(pe, "status_group_prefix", "total_grouped_line_refs")
    stage01.append_u32_label(pe, "status_slash_prefix", "sector_line_min_count")
    stage01.append_u32_label(pe, "status_slash_prefix", "sector_line_max_count")
    stage01.append_u32_label(pe, "status_slash_prefix", "first_sector_line_count")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    x86.mov_reg_abs32(pe, "edi", "title_status_buffer")
    stage01.append_c_string_label(pe, "title_success_prefix")
    stage01.append_u32_label(pe, "title_v_prefix", "vertex_count")
    stage01.append_u32_label(pe, "title_l_prefix", "linedef_count")
    stage01.append_u32_label(pe, "title_sd_prefix", "sidedef_count")
    stage01.append_u32_label(pe, "title_sec_prefix", "sector_count")
    stage01.append_u32_label(pe, "title_ss_prefix", "subsector_count")
    stage01.append_u32_label(pe, "title_n_prefix", "node_count")
    stage01.append_u32_label(pe, "title_sg_prefix", "seg_count")
    stage01.append_u32_label(pe, "title_root_prefix", "root_node_index")
    stage01.append_u32_label(pe, "title_group_prefix", "sector_line_min_count")
    stage01.append_u32_label(pe, "title_range_prefix", "sector_line_max_count")
    stage01.append_u32_label(pe, "title_f0_prefix", "first_sector_line_count")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage02_data(pe: PE32) -> None:
    pe.align_section(4)
    pe.label("subsectors_lump_index")
    pe.emit_u32(0)
    pe.label("nodes_lump_index")
    pe.emit_u32(0)
    pe.label("segs_lump_index")
    pe.emit_u32(0)

    pe.label("subsectors_size")
    pe.emit_u32(0)
    pe.label("nodes_size")
    pe.emit_u32(0)
    pe.label("segs_size")
    pe.emit_u32(0)
    pe.label("subsector_count")
    pe.emit_u32(0)
    pe.label("node_count")
    pe.emit_u32(0)
    pe.label("seg_count")
    pe.emit_u32(0)
    pe.label("root_node_index")
    pe.emit_u32(0)
    pe.label("map_grouped")
    pe.emit_u32(0)

    pe.label("first_subsector_numlines_value")
    pe.emit_u32(0)
    pe.label("first_subsector_firstline_value")
    pe.emit_u32(0)
    pe.label("first_subsector_sector_index")
    pe.emit_u32(0)
    pe.label("first_seg_v1_index")
    pe.emit_u32(0)
    pe.label("first_seg_v2_index")
    pe.emit_u32(0)
    pe.label("first_seg_linedef_index")
    pe.emit_u32(0)
    pe.label("first_seg_side")
    pe.emit_u32(0)

    pe.label("seg_tmp_v1_index")
    pe.emit_u32(0)
    pe.label("seg_tmp_v2_index")
    pe.emit_u32(0)
    pe.label("seg_tmp_linedef_index")
    pe.emit_u32(0)
    pe.label("seg_tmp_linedef_ptr")
    pe.emit_u32(0)
    pe.label("seg_tmp_side")
    pe.emit_u32(0)
    pe.label("seg_tmp_sidenum")
    pe.emit_u32(0)

    pe.label("total_grouped_line_refs")
    pe.emit_u32(0)
    pe.label("group_running_line_refs")
    pe.emit_u32(0)
    pe.label("group_tmp_line_ptr")
    pe.emit_u32(0)
    pe.label("first_sector_line_count")
    pe.emit_u32(0)
    pe.label("sector_line_min_count")
    pe.emit_u32(0)
    pe.label("sector_line_max_count")
    pe.emit_u32(0)

    pe.align_section(1)
    pe.label("status_stage02_success_header")
    x86.emit_asciiz(pe, "source_stage02_bsp_setup\r\nWAD/map+BSP setup OK\r\n")
    pe.label("status_subsectors_prefix")
    x86.emit_asciiz(pe, "\r\nP_LoadSubsectors count: ")
    pe.label("status_nodes_prefix")
    x86.emit_asciiz(pe, "\r\nP_LoadNodes count: ")
    pe.label("status_segs_prefix")
    x86.emit_asciiz(pe, "\r\nP_LoadSegs count: ")
    pe.label("status_root_node_prefix")
    x86.emit_asciiz(pe, "\r\nroot node index: ")
    pe.label("status_first_subsector_prefix")
    x86.emit_asciiz(pe, "\r\nfirst subsector first/count: ")
    pe.label("status_first_subsector_sector_prefix")
    x86.emit_asciiz(pe, "\r\nfirst subsector sector index: ")
    pe.label("status_first_seg_prefix")
    x86.emit_asciiz(pe, "\r\nfirst seg v1/v2/linedef/side: ")
    pe.label("status_group_prefix")
    x86.emit_asciiz(pe, "\r\nP_GroupLines total/min/max/first: ")
    pe.label("status_slash_prefix")
    x86.emit_asciiz(pe, "/")

    pe.label("title_ss_prefix")
    x86.emit_asciiz(pe, " SS=")
    pe.label("title_n_prefix")
    x86.emit_asciiz(pe, " N=")
    pe.label("title_sg_prefix")
    x86.emit_asciiz(pe, " SG=")
    pe.label("title_root_prefix")
    x86.emit_asciiz(pe, " ROOT=")
    pe.label("title_group_prefix")
    x86.emit_asciiz(pe, " G=")
    pe.label("title_range_prefix")
    x86.emit_asciiz(pe, "..")
    pe.label("title_f0_prefix")
    x86.emit_asciiz(pe, " F0=")

    pe.align_section(4)
    pe.label("subsectors_buffer")
    pe.emit_zeros(SUBSECTORS_BUFFER_BYTES)

    pe.align_section(4)
    pe.label("nodes_buffer")
    pe.emit_zeros(NODES_BUFFER_BYTES)

    pe.align_section(4)
    pe.label("segs_buffer")
    pe.emit_zeros(SEGS_BUFFER_BYTES)

    pe.align_section(4)
    pe.label("sector_line_counts")
    pe.emit_zeros(stage01.MAX_SECTORS * 4)

    pe.align_section(4)
    pe.label("sector_line_starts")
    pe.emit_zeros(stage01.MAX_SECTORS * 4)

    pe.align_section(4)
    pe.label("sector_line_work_counts")
    pe.emit_zeros(stage01.MAX_SECTORS * 4)

    pe.align_section(4)
    pe.label("sector_line_table")
    pe.emit_zeros(MAX_SECTOR_LINE_REFS * 4)


def build_source_stage02_bsp_setup_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_entry(pe)
    stage01.emit_wndproc(pe)
    emit_source_stage02_load_wad_bsp(pe)
    stage01.emit_load_wad_directory(pe)
    stage01.emit_wad_num_lumps(pe)
    stage01.emit_wad_check_num_for_name(pe)
    stage01.emit_wad_get_num_for_name(pe)
    stage01.emit_wad_lump_length(pe)
    stage01.emit_wad_read_lump(pe)
    emit_source_stage02_load_map(pe)
    stage01.emit_map_load_vertexes(pe)
    stage01.emit_map_load_sectors(pe)
    stage01.emit_map_load_sidedefs(pe)
    stage01.emit_map_load_linedefs(pe)
    emit_map_load_subsectors(pe)
    emit_map_load_nodes(pe)
    emit_map_load_segs(pe)
    emit_map_group_lines(pe)
    emit_group_count_sector_ref(pe)
    emit_group_append_sector_line(pe)
    emit_build_success_status(pe)
    stage01.emit_append_c_string(pe)
    stage01.emit_append_u32_decimal(pe)
    stage01.emit_append_i32_decimal(pe)
    with patched_stage01_window_labels():
        stage01.emit_data(pe)
    emit_stage02_data(pe)
    return pe.build("entry")


def write_source_stage02_bsp_setup_exe(path: str | Path) -> bytes:
    image = build_source_stage02_bsp_setup_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the source-guided PE32 x86 BSP setup executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/source_stage02_bsp_setup.exe",
        help="path to write, default: build/source_stage02_bsp_setup.exe",
    )
    args = parser.parse_args()
    write_source_stage02_bsp_setup_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
