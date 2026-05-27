from __future__ import annotations

import argparse
import struct
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage01_wad_map as stage01
from tools import emit_source_stage02_bsp_setup as stage02
from tools import x86
from tools.map_loader import load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


GDI32 = "GDI32.dll"

DIB_RGB_COLORS = 0
BI_RGB = 0
SRCCOPY = 0x00CC0020

FRAMEBUFFER_WIDTH = 320
FRAMEBUFFER_HEIGHT = 200
FRAMEBUFFER_PIXELS = FRAMEBUFFER_WIDTH * FRAMEBUFFER_HEIGHT
FRAMEBUFFER_BYTES = FRAMEBUFFER_PIXELS * 4

WINDOW_WIDTH = 960
WINDOW_HEIGHT = 640
WINDOW_CLASS_NAME = "InferenceDoomSourceStage03BspWalkDebug"
WINDOW_TITLE = "Inference Doom - Source Stage 03 BSP Walk Debug"
WAD_PATH = stage02.WAD_PATH

FRACBITS = 16
FRACUNIT = 1 << FRACBITS
NF_SUBSECTOR = 0x8000

# Pinned Freedoom2 MAP01 player-one start. Stage02 does not load THINGS yet.
VIEW_X_MAP_UNITS = -192
VIEW_Y_MAP_UNITS = -192
VIEW_ANGLE_DEGREES = 0
VIEW_X_FIXED = VIEW_X_MAP_UNITS << FRACBITS
VIEW_Y_FIXED = VIEW_Y_MAP_UNITS << FRACBITS
VIEW_ANGLE = 0

# Same top-down framing as the earlier map probe; it fits pinned MAP01.
MAP_MIN_X = -248
MAP_MIN_Y = -1800
MAP_SCALE_16_16 = 3469
SCREEN_X_OFFSET = 96
SCREEN_Y_BOTTOM = 190

COLOR_BACKGROUND = 0x00091016
COLOR_MAP_LINE = 0x00334A55
COLOR_VISITED_SEG = 0x0000C8FF
COLOR_VIEWPOINT = 0x00FFFFFF
COLOR_ERROR = 0x00200070

MAX_VISITED_SEGS = stage02.MAX_SEGS
VISITED_SEG_INDICES_BYTES = MAX_VISITED_SEGS * 4

TRAVERSAL_VISITED_NODE_COUNT = 0
TRAVERSAL_VISITED_SUBSECTOR_COUNT = 4
TRAVERSAL_VISITED_SEG_COUNT = 8
TRAVERSAL_MAX_DEPTH = 12
TRAVERSAL_FIRST_SUBSECTOR = 16
TRAVERSAL_LAST_SUBSECTOR = 20
TRAVERSAL_VIEW_SUBSECTOR = 24
TRAVERSAL_DEBUG_STATE_BYTES = 28

SOURCE_TRACE = stage02.SOURCE_TRACE + (
    ("reference/chocolate-doom/src/doom/r_main.c", "R_PointOnSide", "render_point_on_side"),
    ("reference/chocolate-doom/src/doom/r_main.c", "R_PointInSubsector", "render_point_in_subsector"),
    ("reference/chocolate-doom/src/doom/r_bsp.c", "R_Subsector", "render_debug_subsector"),
    ("reference/chocolate-doom/src/doom/r_bsp.c", "R_RenderBSPNode", "render_bsp_node_debug"),
)


@dataclass(frozen=True)
class BspTraversalReference:
    vertex_count: int
    sector_count: int
    sidedef_count: int
    linedef_count: int
    subsector_count: int
    node_count: int
    seg_count: int
    visited_node_count: int
    visited_subsector_count: int
    visited_seg_count: int
    max_depth: int
    first_subsector: int
    last_subsector: int
    view_subsector: int


def _int32(value: int) -> int:
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def fixed_mul(a: int, b: int) -> int:
    return _int32((_int32(a) * _int32(b)) >> FRACBITS)


def point_on_side_fixed(x: int, y: int, node: Sequence[int]) -> int:
    node_x, node_y, node_dx, node_dy = (
        _int32(node[0]),
        _int32(node[1]),
        _int32(node[2]),
        _int32(node[3]),
    )

    if node_dx == 0:
        if x <= node_x:
            return int(node_dy > 0)
        return int(node_dy < 0)

    if node_dy == 0:
        if y <= node_y:
            return int(node_dx < 0)
        return int(node_dx > 0)

    dx = _int32(x - node_x)
    dy = _int32(y - node_y)

    if _int32(node_dy ^ node_dx ^ dx ^ dy) & 0x80000000:
        if _int32(node_dy ^ dx) & 0x80000000:
            return 1
        return 0

    left = fixed_mul(node_dy >> FRACBITS, dx)
    right = fixed_mul(dy, node_dx >> FRACBITS)
    return 0 if right < left else 1


def runtime_node_from_mapnode(mapnode: Sequence[int]) -> tuple[int, ...]:
    return tuple(_int32(value << FRACBITS) for value in mapnode[:12]) + tuple(mapnode[12:])


def reference_traversal_for_pinned_map(wad_path: str | Path) -> BspTraversalReference:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    map_lumps = wad.map_lumps("MAP01")
    subsectors = stage02.parse_mapsubsectors(wad.read_lump(map_lumps.get("SSECTORS")))
    nodes = tuple(
        runtime_node_from_mapnode(node)
        for node in stage02.parse_mapnodes(wad.read_lump(map_lumps.get("NODES")))
    )
    segs = stage02.parse_mapsegs(wad.read_lump(map_lumps.get("SEGS")))

    view_x = VIEW_X_FIXED
    view_y = VIEW_Y_FIXED

    def point_in_subsector() -> int:
        if not nodes:
            return 0

        nodenum = len(nodes) - 1
        while not (nodenum & NF_SUBSECTOR):
            node = nodes[nodenum]
            side = point_on_side_fixed(view_x, view_y, node)
            nodenum = node[12 + side]
        return nodenum & ~NF_SUBSECTOR

    order: list[int] = []
    counts = {
        "nodes": 0,
        "subsectors": 0,
        "segs": 0,
        "depth": 0,
    }

    def walk(bspnum: int, depth: int) -> None:
        counts["depth"] = max(counts["depth"], depth)
        if bspnum & NF_SUBSECTOR:
            subsector_id = 0 if bspnum == 0xFFFFFFFF else (bspnum & ~NF_SUBSECTOR)
            order.append(subsector_id)
            counts["subsectors"] += 1
            counts["segs"] += subsectors[subsector_id][0]
            return

        counts["nodes"] += 1
        node = nodes[bspnum]
        side = point_on_side_fixed(view_x, view_y, node)
        walk(node[12 + side], depth + 1)
        walk(node[12 + (side ^ 1)], depth + 1)

    root = (len(nodes) - 1) if nodes else 0xFFFFFFFF
    walk(root, 0)

    return BspTraversalReference(
        vertex_count=len(loaded.vertices),
        sector_count=len(loaded.sectors),
        sidedef_count=len(loaded.sidedefs),
        linedef_count=len(loaded.linedefs),
        subsector_count=len(subsectors),
        node_count=len(nodes),
        seg_count=len(segs),
        visited_node_count=counts["nodes"],
        visited_subsector_count=counts["subsectors"],
        visited_seg_count=counts["segs"],
        max_depth=counts["depth"],
        first_subsector=order[0],
        last_subsector=order[-1],
        view_subsector=point_in_subsector(),
    )


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
    x86.call_rel32(pe, "source_stage03_load_wad_bsp_walk")

    x86.push_imm8(pe, 0)
    x86.push_mem_abs32(pe, "wc_hInstance")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, WINDOW_HEIGHT)
    x86.push_imm32(pe, WINDOW_WIDTH)
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


def emit_wndproc_framebuffer(pe: PE32) -> None:
    pe.label("wndproc")
    x86.emit_function_prologue(pe)

    x86.mov_eax_ebp_disp8(pe, 12)
    x86.cmp_eax_imm32(pe, stage01.WM_DESTROY)
    x86.je_rel32(pe, "wndproc_destroy")
    x86.cmp_eax_imm32(pe, stage01.WM_PAINT)
    x86.je_rel32(pe, "wndproc_paint")

    pe.label("wndproc_default")
    x86.push_ebp_disp8(pe, 20)
    x86.push_ebp_disp8(pe, 16)
    x86.push_ebp_disp8(pe, 12)
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, stage01.USER32, "DefWindowProcW")
    x86.emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_destroy")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.USER32, "PostQuitMessage")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_paint")
    x86.push_abs32(pe, "paint_struct")
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, stage01.USER32, "BeginPaint")
    x86.mov_mem_abs32_eax(pe, "paint_hdc")

    x86.push_abs32(pe, "client_rect")
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, stage01.USER32, "GetClientRect")

    x86.push_imm32(pe, SRCCOPY)
    x86.push_imm8(pe, DIB_RGB_COLORS)
    x86.push_abs32(pe, "bitmap_info")
    x86.push_abs32(pe, "framebuffer")
    x86.push_imm32(pe, FRAMEBUFFER_HEIGHT)
    x86.push_imm32(pe, FRAMEBUFFER_WIDTH)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_mem_abs32(pe, "client_bottom")
    x86.push_mem_abs32(pe, "client_right")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_mem_abs32(pe, "paint_hdc")
    x86.call_import(pe, GDI32, "StretchDIBits")

    x86.push_abs32(pe, "paint_struct")
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, stage01.USER32, "EndPaint")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.emit_function_epilogue_ret(pe, 16)


def emit_source_stage03_load_wad_bsp_walk(pe: PE32) -> None:
    pe.label("source_stage03_load_wad_bsp_walk")
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
    x86.jne_rel32(pe, "source_stage03_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage03_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage03_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage03_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage03_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage03_close_and_return")

    pe.label("source_stage03_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage03_close_and_return")

    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage03_close_and_return")

    x86.call_rel32(pe, "source_stage03_run_bsp_walk_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage03_close_and_return")

    x86.call_rel32(pe, "build_success_status")

    pe.label("source_stage03_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_source_stage03_run_bsp_walk_debug(pe: PE32) -> None:
    pe.label("source_stage03_run_bsp_walk_debug")
    x86.mov_mem_abs32_imm32(pe, "visited_node_count", 0)
    x86.mov_mem_abs32_imm32(pe, "visited_subsector_count", 0)
    x86.mov_mem_abs32_imm32(pe, "visited_seg_count", 0)
    x86.mov_mem_abs32_imm32(pe, "max_traversal_depth", 0)
    x86.mov_mem_abs32_imm32(pe, "first_visited_subsector", 0xFFFFFFFF)
    x86.mov_mem_abs32_imm32(pe, "last_visited_subsector", 0)
    x86.mov_mem_abs32_imm32(pe, "view_subsector_index", 0)
    x86.mov_mem_abs32_imm32(pe, "traversal_done", 0)

    x86.push_mem_abs32(pe, "viewy")
    x86.push_mem_abs32(pe, "viewx")
    x86.call_rel32(pe, "render_point_in_subsector")

    x86.mov_reg_mem_abs32(pe, "eax", "node_count")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "source_stage03_have_nodes")
    x86.mov_reg_imm32(pe, "eax", 0xFFFFFFFF)
    x86.jmp_rel32(pe, "source_stage03_have_root")

    pe.label("source_stage03_have_nodes")
    x86.dec_reg(pe, "eax")

    pe.label("source_stage03_have_root")
    x86.push_imm8(pe, 0)
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_bsp_node_debug")

    x86.call_rel32(pe, "render_debug_framebuffer")
    x86.mov_mem_abs32_imm32(pe, "traversal_done", 1)
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)


def emit_render_fixed_mul(pe: PE32) -> None:
    pe.label("render_fixed_mul")
    x86.emit_function_prologue(pe)
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_reg_ebp_disp8(pe, "ecx", 12)
    x86.imul_reg(pe, "ecx")
    x86.shrd_reg_reg_imm8(pe, "eax", "edx", FRACBITS)
    x86.emit_function_epilogue_ret(pe, 8)


def emit_render_point_on_side(pe: PE32) -> None:
    pe.label("render_point_on_side")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_reg_ebp_disp8(pe, "esi", 16)

    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_DX)
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "point_on_side_has_dx")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", stage02.NODE_X)
    x86.cmp_reg_reg(pe, "ebx", "eax")
    x86.jl_rel32(pe, "point_on_side_vertical_x_greater")
    _emit_return_node_dy_positive(pe, "point_on_side_return")

    pe.label("point_on_side_vertical_x_greater")
    _emit_return_node_dy_negative(pe, "point_on_side_return")

    pe.label("point_on_side_has_dx")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_DY)
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "point_on_side_general")
    x86.mov_eax_ebp_disp8(pe, 12)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", stage02.NODE_Y)
    x86.cmp_reg_reg(pe, "ebx", "eax")
    x86.jl_rel32(pe, "point_on_side_horizontal_y_greater")
    _emit_return_node_dx_negative(pe, "point_on_side_return")

    pe.label("point_on_side_horizontal_y_greater")
    _emit_return_node_dx_positive(pe, "point_on_side_return")

    pe.label("point_on_side_general")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", stage02.NODE_X)
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.mov_mem_abs32_eax(pe, "point_side_dx")

    x86.mov_eax_ebp_disp8(pe, 12)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", stage02.NODE_Y)
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.mov_mem_abs32_eax(pe, "point_side_dy")

    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_DY)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", stage02.NODE_DX)
    x86.xor_reg_reg(pe, "eax", "ebx")
    x86.mov_reg_mem_abs32(pe, "ebx", "point_side_dx")
    x86.xor_reg_reg(pe, "eax", "ebx")
    x86.mov_reg_mem_abs32(pe, "ebx", "point_side_dy")
    x86.xor_reg_reg(pe, "eax", "ebx")
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "point_on_side_no_sign_shortcut")

    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_DY)
    x86.mov_reg_mem_abs32(pe, "ebx", "point_side_dx")
    x86.xor_reg_reg(pe, "eax", "ebx")
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "point_on_side_sign_return_front")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, "point_on_side_return")

    pe.label("point_on_side_sign_return_front")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.jmp_rel32(pe, "point_on_side_return")

    pe.label("point_on_side_no_sign_shortcut")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_DY)
    x86.sar_reg_imm8(pe, "eax", FRACBITS)
    x86.push_mem_abs32(pe, "point_side_dx")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_fixed_mul")
    x86.mov_mem_abs32_eax(pe, "point_side_left")

    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_DX)
    x86.sar_reg_imm8(pe, "eax", FRACBITS)
    x86.push_reg(pe, "eax")
    x86.push_mem_abs32(pe, "point_side_dy")
    x86.call_rel32(pe, "render_fixed_mul")
    x86.cmp_reg_mem_abs32(pe, "eax", "point_side_left")
    x86.jl_rel32(pe, "point_on_side_compare_front")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, "point_on_side_return")

    pe.label("point_on_side_compare_front")
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("point_on_side_return")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 12)


def _emit_return_node_dy_positive(pe: PE32, done_label: str) -> None:
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_DY)
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "point_on_side_dy_nonnegative")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.jmp_rel32(pe, done_label)
    pe.label("point_on_side_dy_nonnegative")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "point_on_side_dy_positive_false")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, done_label)
    pe.label("point_on_side_dy_positive_false")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.jmp_rel32(pe, done_label)


def _emit_return_node_dy_negative(pe: PE32, done_label: str) -> None:
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_DY)
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "point_on_side_dy_negative_false")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, done_label)
    pe.label("point_on_side_dy_negative_false")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.jmp_rel32(pe, done_label)


def _emit_return_node_dx_positive(pe: PE32, done_label: str) -> None:
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_DX)
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "point_on_side_dx_nonnegative")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.jmp_rel32(pe, done_label)
    pe.label("point_on_side_dx_nonnegative")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "point_on_side_dx_positive_false")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, done_label)
    pe.label("point_on_side_dx_positive_false")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.jmp_rel32(pe, done_label)


def _emit_return_node_dx_negative(pe: PE32, done_label: str) -> None:
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_DX)
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "point_on_side_dx_negative_false")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, done_label)
    pe.label("point_on_side_dx_negative_false")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.jmp_rel32(pe, done_label)


def emit_render_point_in_subsector(pe: PE32) -> None:
    pe.label("render_point_in_subsector")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")

    x86.mov_reg_mem_abs32(pe, "eax", "node_count")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "point_in_subsector_have_nodes")
    x86.mov_mem_abs32_imm32(pe, "view_subsector_index", 0)
    x86.mov_reg_abs32(pe, "eax", "subsectors_buffer")
    x86.jmp_rel32(pe, "point_in_subsector_done")

    pe.label("point_in_subsector_have_nodes")
    x86.dec_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "point_in_subsector_nodenum")

    pe.label("point_in_subsector_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "point_in_subsector_nodenum")
    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.and_reg_imm32(pe, "ebx", NF_SUBSECTOR)
    x86.test_reg_reg(pe, "ebx")
    x86.jne_rel32(pe, "point_in_subsector_leaf")

    x86.imul_reg_reg_imm32(pe, "ebx", "eax", stage02.NODE_T_RECORD_SIZE)
    x86.mov_reg_abs32(pe, "esi", "nodes_buffer")
    x86.add_reg_reg(pe, "esi", "ebx")

    x86.push_reg(pe, "esi")
    x86.push_ebp_disp8(pe, 12)
    x86.push_ebp_disp8(pe, 8)
    x86.call_rel32(pe, "render_point_on_side")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "point_in_subsector_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD0)
    x86.jmp_rel32(pe, "point_in_subsector_store_child")

    pe.label("point_in_subsector_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD1)

    pe.label("point_in_subsector_store_child")
    x86.mov_mem_abs32_eax(pe, "point_in_subsector_nodenum")
    x86.jmp_rel32(pe, "point_in_subsector_loop")

    pe.label("point_in_subsector_leaf")
    x86.mov_reg_mem_abs32(pe, "eax", "point_in_subsector_nodenum")
    x86.and_reg_imm32(pe, "eax", ~NF_SUBSECTOR)
    x86.mov_mem_abs32_eax(pe, "view_subsector_index")
    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.shl_reg_imm8(pe, "ebx", 3)
    x86.mov_reg_abs32(pe, "eax", "subsectors_buffer")
    x86.add_reg_reg(pe, "eax", "ebx")

    pe.label("point_in_subsector_done")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 8)


def emit_render_debug_subsector(pe: PE32) -> None:
    pe.label("render_debug_subsector")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.cmp_reg_mem_abs32(pe, "eax", "subsector_count")
    x86.jae_rel32(pe, "debug_subsector_done")

    x86.mov_reg_mem_abs32(pe, "ebx", "visited_subsector_count")
    x86.test_reg_reg(pe, "ebx")
    x86.jne_rel32(pe, "debug_subsector_not_first")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_mem_abs32_eax(pe, "first_visited_subsector")

    pe.label("debug_subsector_not_first")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_mem_abs32_eax(pe, "last_visited_subsector")
    x86.mov_reg_mem_abs32(pe, "eax", "visited_subsector_count")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "visited_subsector_count")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.shl_reg_imm8(pe, "eax", 3)
    x86.mov_reg_abs32(pe, "esi", "subsectors_buffer")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "ecx", "esi", stage02.SUBSECTOR_NUMLINES)
    x86.movzx_reg_word_ptr_reg_disp8(pe, "edx", "esi", stage02.SUBSECTOR_FIRSTLINE)

    pe.label("debug_subsector_seg_loop")
    x86.test_reg_reg(pe, "ecx")
    x86.je_rel32(pe, "debug_subsector_done")
    x86.mov_reg_mem_abs32(pe, "ebx", "visited_seg_count")
    x86.cmp_reg_imm32(pe, "ebx", MAX_VISITED_SEGS)
    x86.jae_rel32(pe, "debug_subsector_skip_seg_store")
    x86.mov_reg_reg(pe, "eax", "ebx")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "edi", "visited_seg_indices")
    x86.add_reg_reg(pe, "edi", "eax")
    x86.mov_reg_reg(pe, "eax", "edx")
    x86.mov_ptr_reg_eax(pe, "edi")

    pe.label("debug_subsector_skip_seg_store")
    x86.mov_reg_mem_abs32(pe, "eax", "visited_seg_count")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "visited_seg_count")
    x86.inc_reg(pe, "edx")
    x86.dec_reg(pe, "ecx")
    x86.jmp_rel32(pe, "debug_subsector_seg_loop")

    pe.label("debug_subsector_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_render_check_bbox_accept_all(pe: PE32) -> None:
    pe.label("render_check_bbox_accept_all")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)


def emit_render_bsp_node_debug(pe: PE32) -> None:
    pe.label("render_bsp_node_debug")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.and_reg_imm32(pe, "ebx", NF_SUBSECTOR)
    x86.test_reg_reg(pe, "ebx")
    x86.jne_rel32(pe, "bsp_node_is_subsector")

    _emit_update_max_depth_from_arg(pe, "node")
    x86.mov_reg_mem_abs32(pe, "eax", "visited_node_count")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "visited_node_count")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.cmp_reg_mem_abs32(pe, "eax", "node_count")
    x86.jae_rel32(pe, "bsp_node_done")
    x86.imul_reg_reg_imm32(pe, "ebx", "eax", stage02.NODE_T_RECORD_SIZE)
    x86.mov_reg_abs32(pe, "esi", "nodes_buffer")
    x86.add_reg_reg(pe, "esi", "ebx")

    x86.push_reg(pe, "esi")
    x86.push_mem_abs32(pe, "viewy")
    x86.push_mem_abs32(pe, "viewx")
    x86.call_rel32(pe, "render_point_on_side")
    x86.mov_reg_reg(pe, "ebx", "eax")

    x86.test_reg_reg(pe, "ebx")
    x86.jne_rel32(pe, "bsp_node_front_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD0)
    x86.jmp_rel32(pe, "bsp_node_have_front_child")

    pe.label("bsp_node_front_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD1)

    pe.label("bsp_node_have_front_child")
    _emit_recurse_bsp_child(pe)

    x86.call_rel32(pe, "render_check_bbox_accept_all")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "bsp_node_done")

    x86.test_reg_reg(pe, "ebx")
    x86.jne_rel32(pe, "bsp_node_back_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD1)
    x86.jmp_rel32(pe, "bsp_node_have_back_child")

    pe.label("bsp_node_back_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD0)

    pe.label("bsp_node_have_back_child")
    _emit_recurse_bsp_child(pe)
    x86.jmp_rel32(pe, "bsp_node_done")

    pe.label("bsp_node_is_subsector")
    _emit_update_max_depth_from_arg(pe, "subsector")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.jne_rel32(pe, "bsp_node_normal_subsector")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.jmp_rel32(pe, "bsp_node_call_subsector")

    pe.label("bsp_node_normal_subsector")
    x86.and_reg_imm32(pe, "eax", ~NF_SUBSECTOR)

    pe.label("bsp_node_call_subsector")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_debug_subsector")

    pe.label("bsp_node_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 8)


def _emit_update_max_depth_from_arg(pe: PE32, suffix: str) -> None:
    done_label = f"bsp_node_depth_not_larger_{suffix}"
    x86.mov_eax_ebp_disp8(pe, 12)
    x86.cmp_reg_mem_abs32(pe, "eax", "max_traversal_depth")
    x86.jbe_rel32(pe, done_label)
    x86.mov_mem_abs32_eax(pe, "max_traversal_depth")
    pe.label(done_label)


def _emit_recurse_bsp_child(pe: PE32) -> None:
    x86.mov_reg_ebp_disp8(pe, "ecx", 12)
    x86.inc_reg(pe, "ecx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_bsp_node_debug")


def emit_render_debug_framebuffer(pe: PE32) -> None:
    pe.label("render_debug_framebuffer")
    x86.call_rel32(pe, "clear_framebuffer")
    x86.call_rel32(pe, "draw_all_linedefs")
    x86.call_rel32(pe, "draw_visited_segs")
    x86.call_rel32(pe, "draw_viewpoint_marker")
    x86.ret(pe)


def emit_clear_framebuffer(pe: PE32) -> None:
    pe.label("clear_framebuffer")
    x86.push_reg(pe, "edi")
    pe.emit(b"\xFC")
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.mov_reg_imm32(pe, "eax", COLOR_BACKGROUND)
    x86.mov_reg_imm32(pe, "ecx", FRAMEBUFFER_PIXELS)
    pe.emit(b"\xF3\xAB")
    x86.pop_reg(pe, "edi")
    x86.ret(pe)


def emit_render_error_pattern(pe: PE32) -> None:
    pe.label("render_error_pattern")
    x86.push_reg(pe, "edi")
    pe.emit(b"\xFC")
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.mov_reg_imm32(pe, "eax", COLOR_ERROR)
    x86.mov_reg_imm32(pe, "ecx", FRAMEBUFFER_PIXELS)
    pe.emit(b"\xF3\xAB")
    x86.pop_reg(pe, "edi")
    x86.ret(pe)


def emit_transform_point_to_screen(pe: PE32) -> None:
    pe.label("transform_point_to_screen")
    x86.emit_function_prologue(pe)

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.sar_reg_imm8(pe, "eax", FRACBITS)
    x86.add_reg_imm32(pe, "eax", -MAP_MIN_X)
    x86.imul_reg_reg_imm32(pe, "eax", "eax", MAP_SCALE_16_16)
    x86.sar_reg_imm8(pe, "eax", FRACBITS)
    x86.add_reg_imm32(pe, "eax", SCREEN_X_OFFSET)
    x86.mov_mem_abs32_eax(pe, "transform_screen_x")

    x86.mov_eax_ebp_disp8(pe, 12)
    x86.sar_reg_imm8(pe, "eax", FRACBITS)
    x86.add_reg_imm32(pe, "eax", -MAP_MIN_Y)
    x86.imul_reg_reg_imm32(pe, "eax", "eax", MAP_SCALE_16_16)
    x86.sar_reg_imm8(pe, "eax", FRACBITS)
    x86.mov_reg_imm32(pe, "edx", SCREEN_Y_BOTTOM)
    x86.sub_reg_reg(pe, "edx", "eax")
    x86.mov_mem_abs32_reg(pe, "transform_screen_y", "edx")

    x86.emit_function_epilogue_ret(pe, 8)


def emit_draw_all_linedefs(pe: PE32) -> None:
    pe.label("draw_all_linedefs")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_mem_abs32_imm32(pe, "draw_color", COLOR_MAP_LINE)
    x86.mov_reg_abs32(pe, "esi", "lines_buffer")
    x86.mov_mem_abs32_reg(pe, "draw_scan_ptr", "esi")
    x86.mov_reg_mem_abs32(pe, "eax", "linedef_count")
    x86.mov_mem_abs32_eax(pe, "draw_remaining")

    pe.label("draw_linedefs_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "draw_remaining")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "draw_linedefs_done")

    x86.mov_reg_mem_abs32(pe, "esi", "draw_scan_ptr")
    x86.mov_reg_ptr_reg_disp8(pe, "edi", "esi", stage01.LINE_V1)
    _emit_line_endpoint_from_vertex_ptr(pe, "line_x0", "line_y0")
    x86.mov_reg_mem_abs32(pe, "esi", "draw_scan_ptr")
    x86.mov_reg_ptr_reg_disp8(pe, "edi", "esi", stage01.LINE_V2)
    _emit_line_endpoint_from_vertex_ptr(pe, "line_x1", "line_y1")
    x86.call_rel32(pe, "draw_line")

    x86.mov_reg_mem_abs32(pe, "esi", "draw_scan_ptr")
    x86.add_reg_imm32(pe, "esi", stage01.LINE_T_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, "draw_scan_ptr", "esi")
    x86.dec_mem_abs32(pe, "draw_remaining")
    x86.jmp_rel32(pe, "draw_linedefs_loop")

    pe.label("draw_linedefs_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.ret(pe)


def emit_draw_visited_segs(pe: PE32) -> None:
    pe.label("draw_visited_segs")
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_mem_abs32_imm32(pe, "draw_color", COLOR_VISITED_SEG)
    x86.mov_reg_abs32(pe, "esi", "visited_seg_indices")
    x86.mov_mem_abs32_reg(pe, "draw_scan_ptr", "esi")
    x86.mov_reg_mem_abs32(pe, "eax", "visited_seg_count")
    x86.mov_mem_abs32_eax(pe, "draw_remaining")

    pe.label("draw_visited_segs_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "draw_remaining")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "draw_visited_segs_done")

    x86.mov_reg_mem_abs32(pe, "esi", "draw_scan_ptr")
    x86.mov_reg_ptr_reg(pe, "eax", "esi")
    x86.cmp_reg_mem_abs32(pe, "eax", "seg_count")
    x86.jae_rel32(pe, "draw_visited_segs_next")
    x86.imul_reg_reg_imm32(pe, "ebx", "eax", stage02.SEG_T_RECORD_SIZE)
    x86.mov_reg_abs32(pe, "edi", "segs_buffer")
    x86.add_reg_reg(pe, "edi", "ebx")
    x86.mov_reg_reg(pe, "ebx", "edi")

    x86.mov_reg_ptr_reg_disp8(pe, "edi", "ebx", stage02.SEG_V1)
    _emit_line_endpoint_from_vertex_ptr(pe, "line_x0", "line_y0")
    x86.mov_reg_ptr_reg_disp8(pe, "edi", "ebx", stage02.SEG_V2)
    _emit_line_endpoint_from_vertex_ptr(pe, "line_x1", "line_y1")
    x86.call_rel32(pe, "draw_line")

    pe.label("draw_visited_segs_next")
    x86.mov_reg_mem_abs32(pe, "esi", "draw_scan_ptr")
    x86.add_reg_imm32(pe, "esi", 4)
    x86.mov_mem_abs32_reg(pe, "draw_scan_ptr", "esi")
    x86.dec_mem_abs32(pe, "draw_remaining")
    x86.jmp_rel32(pe, "draw_visited_segs_loop")

    pe.label("draw_visited_segs_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "ebx")
    x86.ret(pe)


def _emit_line_endpoint_from_vertex_ptr(pe: PE32, x_label: str, y_label: str) -> None:
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", 4)
    x86.push_reg(pe, "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "edi")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "transform_point_to_screen")
    x86.mov_reg_mem_abs32(pe, "eax", "transform_screen_x")
    x86.mov_mem_abs32_eax(pe, x_label)
    x86.mov_reg_mem_abs32(pe, "eax", "transform_screen_y")
    x86.mov_mem_abs32_eax(pe, y_label)


def emit_draw_viewpoint_marker(pe: PE32) -> None:
    pe.label("draw_viewpoint_marker")
    x86.mov_mem_abs32_imm32(pe, "draw_color", COLOR_VIEWPOINT)
    x86.push_mem_abs32(pe, "viewy")
    x86.push_mem_abs32(pe, "viewx")
    x86.call_rel32(pe, "transform_point_to_screen")
    x86.mov_reg_mem_abs32(pe, "eax", "transform_screen_x")
    x86.mov_mem_abs32_eax(pe, "view_screen_x")
    x86.mov_reg_mem_abs32(pe, "eax", "transform_screen_y")
    x86.mov_mem_abs32_eax(pe, "view_screen_y")

    x86.mov_reg_mem_abs32(pe, "eax", "view_screen_x")
    x86.add_reg_imm32(pe, "eax", -3)
    x86.mov_mem_abs32_eax(pe, "line_x0")
    x86.mov_reg_mem_abs32(pe, "eax", "view_screen_y")
    x86.mov_mem_abs32_eax(pe, "line_y0")
    x86.mov_reg_mem_abs32(pe, "eax", "view_screen_x")
    x86.add_reg_imm32(pe, "eax", 3)
    x86.mov_mem_abs32_eax(pe, "line_x1")
    x86.mov_reg_mem_abs32(pe, "eax", "view_screen_y")
    x86.mov_mem_abs32_eax(pe, "line_y1")
    x86.call_rel32(pe, "draw_line")

    x86.mov_reg_mem_abs32(pe, "eax", "view_screen_x")
    x86.mov_mem_abs32_eax(pe, "line_x0")
    x86.mov_mem_abs32_eax(pe, "line_x1")
    x86.mov_reg_mem_abs32(pe, "eax", "view_screen_y")
    x86.add_reg_imm32(pe, "eax", -3)
    x86.mov_mem_abs32_eax(pe, "line_y0")
    x86.mov_reg_mem_abs32(pe, "eax", "view_screen_y")
    x86.add_reg_imm32(pe, "eax", 3)
    x86.mov_mem_abs32_eax(pe, "line_y1")
    x86.call_rel32(pe, "draw_line")
    x86.ret(pe)


def emit_draw_line(pe: PE32) -> None:
    pe.label("draw_line")
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_reg_mem_abs32(pe, "eax", "line_x1")
    x86.sub_reg_mem_abs32(pe, "eax", "line_x0")
    x86.mov_mem_abs32_eax(pe, "line_dx")

    x86.mov_reg_mem_abs32(pe, "eax", "line_y1")
    x86.sub_reg_mem_abs32(pe, "eax", "line_y0")
    x86.mov_mem_abs32_eax(pe, "line_dy")

    x86.mov_reg_mem_abs32(pe, "eax", "line_dx")
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "line_abs_dx_done")
    x86.neg_reg(pe, "eax")
    pe.label("line_abs_dx_done")
    x86.mov_mem_abs32_eax(pe, "line_abs_dx")

    x86.mov_reg_mem_abs32(pe, "eax", "line_dy")
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "line_abs_dy_done")
    x86.neg_reg(pe, "eax")
    pe.label("line_abs_dy_done")
    x86.mov_mem_abs32_eax(pe, "line_abs_dy")

    x86.mov_reg_mem_abs32(pe, "eax", "line_abs_dx")
    x86.cmp_reg_mem_abs32(pe, "eax", "line_abs_dy")
    x86.jae_rel32(pe, "line_steps_selected")
    x86.mov_reg_mem_abs32(pe, "eax", "line_abs_dy")
    pe.label("line_steps_selected")
    x86.mov_mem_abs32_eax(pe, "line_steps")

    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "line_has_steps")
    x86.mov_reg_mem_abs32(pe, "eax", "line_x0")
    x86.mov_mem_abs32_eax(pe, "plot_x")
    x86.mov_reg_mem_abs32(pe, "eax", "line_y0")
    x86.mov_mem_abs32_eax(pe, "plot_y")
    x86.call_rel32(pe, "plot_pixel")
    x86.jmp_rel32(pe, "line_done")

    pe.label("line_has_steps")
    x86.mov_reg_mem_abs32(pe, "eax", "line_x0")
    x86.shl_reg_imm8(pe, "eax", FRACBITS)
    x86.mov_mem_abs32_eax(pe, "line_x_fixed")

    x86.mov_reg_mem_abs32(pe, "eax", "line_y0")
    x86.shl_reg_imm8(pe, "eax", FRACBITS)
    x86.mov_mem_abs32_eax(pe, "line_y_fixed")

    x86.mov_reg_mem_abs32(pe, "eax", "line_dx")
    x86.shl_reg_imm8(pe, "eax", FRACBITS)
    x86.cdq(pe)
    x86.mov_reg_mem_abs32(pe, "ecx", "line_steps")
    x86.idiv_reg(pe, "ecx")
    x86.mov_mem_abs32_eax(pe, "line_x_inc")

    x86.mov_reg_mem_abs32(pe, "eax", "line_dy")
    x86.shl_reg_imm8(pe, "eax", FRACBITS)
    x86.cdq(pe)
    x86.mov_reg_mem_abs32(pe, "ecx", "line_steps")
    x86.idiv_reg(pe, "ecx")
    x86.mov_mem_abs32_eax(pe, "line_y_inc")

    x86.mov_reg_mem_abs32(pe, "eax", "line_steps")
    x86.add_reg_imm32(pe, "eax", 1)
    x86.mov_mem_abs32_eax(pe, "line_steps_remaining")

    pe.label("line_draw_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "line_x_fixed")
    x86.sar_reg_imm8(pe, "eax", FRACBITS)
    x86.mov_mem_abs32_eax(pe, "plot_x")
    x86.mov_reg_mem_abs32(pe, "eax", "line_y_fixed")
    x86.sar_reg_imm8(pe, "eax", FRACBITS)
    x86.mov_mem_abs32_eax(pe, "plot_y")
    x86.call_rel32(pe, "plot_pixel")

    x86.mov_reg_mem_abs32(pe, "eax", "line_x_fixed")
    x86.add_reg_mem_abs32(pe, "eax", "line_x_inc")
    x86.mov_mem_abs32_eax(pe, "line_x_fixed")

    x86.mov_reg_mem_abs32(pe, "eax", "line_y_fixed")
    x86.add_reg_mem_abs32(pe, "eax", "line_y_inc")
    x86.mov_mem_abs32_eax(pe, "line_y_fixed")

    x86.dec_mem_abs32(pe, "line_steps_remaining")
    x86.jne_rel32(pe, "line_draw_loop")

    pe.label("line_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_plot_pixel(pe: PE32) -> None:
    pe.label("plot_pixel")
    x86.mov_reg_mem_abs32(pe, "eax", "plot_x")
    x86.cmp_reg_imm32(pe, "eax", FRAMEBUFFER_WIDTH)
    x86.jae_rel32(pe, "plot_pixel_done")

    x86.mov_reg_mem_abs32(pe, "ebx", "plot_y")
    x86.cmp_reg_imm32(pe, "ebx", FRAMEBUFFER_HEIGHT)
    x86.jae_rel32(pe, "plot_pixel_done")

    x86.mov_reg_reg(pe, "edx", "ebx")
    x86.shl_reg_imm8(pe, "ebx", 8)
    x86.shl_reg_imm8(pe, "edx", 6)
    x86.add_reg_reg(pe, "ebx", "edx")
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.shl_reg_imm8(pe, "ebx", 2)

    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.add_reg_reg(pe, "edi", "ebx")
    x86.mov_reg_mem_abs32(pe, "eax", "draw_color")
    x86.mov_ptr_reg_eax(pe, "edi")

    pe.label("plot_pixel_done")
    x86.ret(pe)


def emit_build_success_status(pe: PE32) -> None:
    pe.label("build_success_status")
    x86.mov_reg_abs32(pe, "edi", "status_success_buffer")

    stage01.append_c_string_label(pe, "status_stage03_success_header")
    stage01.append_c_string_label(pe, "status_path_prefix")
    stage01.append_c_string_label(pe, "wad_path_a")
    stage01.append_c_string_label(pe, "status_lumps_prefix")
    x86.call_rel32(pe, "wad_num_lumps")
    x86.call_rel32(pe, "append_u32_decimal")
    stage01.append_u32_label(pe, "status_vertexes_prefix", "vertex_count")
    stage01.append_u32_label(pe, "status_sectors_prefix", "sector_count")
    stage01.append_u32_label(pe, "status_sidedefs_prefix", "sidedef_count")
    stage01.append_u32_label(pe, "status_linedefs_prefix", "linedef_count")
    stage01.append_u32_label(pe, "status_subsectors_prefix", "subsector_count")
    stage01.append_u32_label(pe, "status_nodes_prefix", "node_count")
    stage01.append_u32_label(pe, "status_segs_prefix", "seg_count")
    stage01.append_u32_label(pe, "status_view_subsector_prefix", "view_subsector_index")
    stage01.append_u32_label(pe, "status_visited_nodes_prefix", "visited_node_count")
    stage01.append_u32_label(pe, "status_visited_subsectors_prefix", "visited_subsector_count")
    stage01.append_u32_label(pe, "status_visited_segs_prefix", "visited_seg_count")
    stage01.append_u32_label(pe, "status_depth_prefix", "max_traversal_depth")
    stage01.append_u32_label(pe, "status_firstss_prefix", "first_visited_subsector")
    stage01.append_u32_label(pe, "status_lastss_prefix", "last_visited_subsector")
    stage01.append_c_string_label(pe, "status_bbox_accept_all_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    x86.mov_reg_abs32(pe, "edi", "title_status_buffer")
    stage01.append_c_string_label(pe, "title_success_prefix")
    stage01.append_u32_label(pe, "title_v_prefix", "vertex_count")
    stage01.append_u32_label(pe, "title_sec_prefix", "sector_count")
    stage01.append_u32_label(pe, "title_sd_prefix", "sidedef_count")
    stage01.append_u32_label(pe, "title_l_prefix", "linedef_count")
    stage01.append_u32_label(pe, "title_ss_prefix", "subsector_count")
    stage01.append_u32_label(pe, "title_n_prefix", "node_count")
    stage01.append_u32_label(pe, "title_sg_prefix", "seg_count")
    stage01.append_u32_label(pe, "title_vn_prefix", "visited_node_count")
    stage01.append_u32_label(pe, "title_vss_prefix", "visited_subsector_count")
    stage01.append_u32_label(pe, "title_vseg_prefix", "visited_seg_count")
    stage01.append_u32_label(pe, "title_depth_prefix", "max_traversal_depth")
    stage01.append_u32_label(pe, "title_firstss_prefix", "first_visited_subsector")
    stage01.append_u32_label(pe, "title_lastss_prefix", "last_visited_subsector")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage03_data(pe: PE32) -> None:
    pe.align_section(4)
    pe.label("viewx")
    pe.emit_u32(VIEW_X_FIXED)
    pe.label("viewy")
    pe.emit_u32(VIEW_Y_FIXED)
    pe.label("viewangle")
    pe.emit_u32(VIEW_ANGLE)
    pe.label("traversal_done")
    pe.emit_u32(0)

    pe.label("traversal_debug_state")
    pe.label("visited_node_count")
    pe.emit_u32(0)
    pe.label("visited_subsector_count")
    pe.emit_u32(0)
    pe.label("visited_seg_count")
    pe.emit_u32(0)
    pe.label("max_traversal_depth")
    pe.emit_u32(0)
    pe.label("first_visited_subsector")
    pe.emit_u32(0xFFFFFFFF)
    pe.label("last_visited_subsector")
    pe.emit_u32(0)
    pe.label("view_subsector_index")
    pe.emit_u32(0)

    pe.label("point_side_dx")
    pe.emit_u32(0)
    pe.label("point_side_dy")
    pe.emit_u32(0)
    pe.label("point_side_left")
    pe.emit_u32(0)
    pe.label("point_in_subsector_nodenum")
    pe.emit_u32(0)

    pe.label("transform_screen_x")
    pe.emit_u32(0)
    pe.label("transform_screen_y")
    pe.emit_u32(0)
    pe.label("view_screen_x")
    pe.emit_u32(0)
    pe.label("view_screen_y")
    pe.emit_u32(0)
    pe.label("draw_scan_ptr")
    pe.emit_u32(0)
    pe.label("draw_remaining")
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
    pe.emit_u32(COLOR_MAP_LINE)

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

    pe.align_section(1)
    pe.label("status_stage03_success_header")
    x86.emit_asciiz(pe, "source_stage03_bsp_walk_debug\r\nBSP traversal debug OK\r\n")
    pe.label("status_view_subsector_prefix")
    x86.emit_asciiz(pe, "\r\nR_PointInSubsector view ss: ")
    pe.label("status_visited_nodes_prefix")
    x86.emit_asciiz(pe, "\r\nR_RenderBSPNode visited nodes: ")
    pe.label("status_visited_subsectors_prefix")
    x86.emit_asciiz(pe, "\r\nR_Subsector visited subsectors: ")
    pe.label("status_visited_segs_prefix")
    x86.emit_asciiz(pe, "\r\nR_Subsector visited segs: ")
    pe.label("status_depth_prefix")
    x86.emit_asciiz(pe, "\r\nmax traversal depth: ")
    pe.label("status_firstss_prefix")
    x86.emit_asciiz(pe, "\r\nfirst visited subsector: ")
    pe.label("status_lastss_prefix")
    x86.emit_asciiz(pe, "\r\nlast visited subsector: ")
    pe.label("status_bbox_accept_all_note")
    x86.emit_asciiz(pe, "\r\nR_CheckBBox: accept-all debug boundary for stage03\r\n")

    pe.label("title_vn_prefix")
    x86.emit_asciiz(pe, " VN=")
    pe.label("title_vss_prefix")
    x86.emit_asciiz(pe, " VSS=")
    pe.label("title_vseg_prefix")
    x86.emit_asciiz(pe, " VSEG=")
    pe.label("title_depth_prefix")
    x86.emit_asciiz(pe, " DEPTH=")
    pe.label("title_firstss_prefix")
    x86.emit_asciiz(pe, " FIRSTSS=")
    pe.label("title_lastss_prefix")
    x86.emit_asciiz(pe, " LASTSS=")

    pe.align_section(4)
    pe.label("visited_seg_indices")
    pe.emit_zeros(VISITED_SEG_INDICES_BYTES)

    pe.align_section(4)
    pe.label("framebuffer")
    pe.emit_zeros(FRAMEBUFFER_BYTES)


def build_source_stage03_bsp_walk_debug_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    emit_wndproc_framebuffer(pe)
    emit_source_stage03_load_wad_bsp_walk(pe)
    stage01.emit_load_wad_directory(pe)
    stage01.emit_wad_num_lumps(pe)
    stage01.emit_wad_check_num_for_name(pe)
    stage01.emit_wad_get_num_for_name(pe)
    stage01.emit_wad_lump_length(pe)
    stage01.emit_wad_read_lump(pe)
    stage02.emit_source_stage02_load_map(pe)
    stage01.emit_map_load_vertexes(pe)
    stage01.emit_map_load_sectors(pe)
    stage01.emit_map_load_sidedefs(pe)
    stage01.emit_map_load_linedefs(pe)
    stage02.emit_map_load_subsectors(pe)
    stage02.emit_map_load_nodes(pe)
    stage02.emit_map_load_segs(pe)
    stage02.emit_map_group_lines(pe)
    stage02.emit_group_count_sector_ref(pe)
    stage02.emit_group_append_sector_line(pe)
    emit_source_stage03_run_bsp_walk_debug(pe)
    emit_render_fixed_mul(pe)
    emit_render_point_on_side(pe)
    emit_render_point_in_subsector(pe)
    emit_render_debug_subsector(pe)
    emit_render_check_bbox_accept_all(pe)
    emit_render_bsp_node_debug(pe)
    emit_render_debug_framebuffer(pe)
    emit_clear_framebuffer(pe)
    emit_render_error_pattern(pe)
    emit_transform_point_to_screen(pe)
    emit_draw_all_linedefs(pe)
    emit_draw_visited_segs(pe)
    emit_draw_viewpoint_marker(pe)
    emit_draw_line(pe)
    emit_plot_pixel(pe)
    emit_build_success_status(pe)
    stage01.emit_append_c_string(pe)
    stage01.emit_append_u32_decimal(pe)
    stage01.emit_append_i32_decimal(pe)
    with patched_stage01_window_labels():
        stage01.emit_data(pe)
    stage02.emit_stage02_data(pe)
    emit_stage03_data(pe)
    return pe.build("entry")


def write_source_stage03_bsp_walk_debug_exe(path: str | Path) -> bytes:
    image = build_source_stage03_bsp_walk_debug_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the source-guided PE32 x86 BSP traversal debug executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/source_stage03_bsp_walk_debug.exe",
        help="path to write, default: build/source_stage03_bsp_walk_debug.exe",
    )
    args = parser.parse_args()
    write_source_stage03_bsp_walk_debug_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
