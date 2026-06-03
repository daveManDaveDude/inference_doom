from __future__ import annotations

import argparse
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage01_wad_map as stage01
from tools import emit_source_stage02_bsp_setup as stage02
from tools import emit_source_stage03_bsp_walk_debug as stage03
from tools import x86
from tools.map_loader import load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


FRAMEBUFFER_WIDTH = stage03.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage03.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage03.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage03.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage03.WINDOW_WIDTH
WINDOW_HEIGHT = stage03.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage04BboxVisibilityDebug"
WINDOW_TITLE = "Inference Doom S04 BBox Visibility"
WAD_PATH = stage03.WAD_PATH

FRACBITS = stage03.FRACBITS
FRACUNIT = stage03.FRACUNIT
NF_SUBSECTOR = stage03.NF_SUBSECTOR

VIEW_X_FIXED = stage03.VIEW_X_FIXED
VIEW_Y_FIXED = stage03.VIEW_Y_FIXED
VIEW_ANGLE = stage03.VIEW_ANGLE

COLOR_BACKGROUND = stage03.COLOR_BACKGROUND
COLOR_MAP_LINE = stage03.COLOR_MAP_LINE
COLOR_VISITED_SEG = 0x000058A8
COLOR_BBOX_VISIBLE_SEG = 0x0000FF70
COLOR_VIEWPOINT = stage03.COLOR_VIEWPOINT
COLOR_ERROR = stage03.COLOR_ERROR

MAX_VISITED_SEGS = stage03.MAX_VISITED_SEGS
VISITED_SEG_INDICES_BYTES = stage03.VISITED_SEG_INDICES_BYTES
BBOX_VISIBLE_SEG_INDICES_BYTES = VISITED_SEG_INDICES_BYTES

ANG90 = 0x40000000
ANG180 = 0x80000000
ANG270 = 0xC0000000
ANGLETOFINESHIFT = 19
FINEANGLES = 8192
FIELDOFVIEW = 2048
SLOPERANGE = 2048

VIEWWIDTH = FRAMEBUFFER_WIDTH
CENTERX = VIEWWIDTH // 2
CENTERXFRAC = CENTERX << FRACBITS
PROJECTION = CENTERXFRAC

BOXTOP = 0
BOXBOTTOM = 1
BOXLEFT = 2
BOXRIGHT = 3

CHECKCOORD = (
    (3, 0, 2, 1),
    (3, 0, 2, 0),
    (3, 1, 2, 0),
    (0, 0, 0, 0),
    (2, 0, 2, 1),
    (0, 0, 0, 0),
    (3, 1, 3, 0),
    (0, 0, 0, 0),
    (2, 0, 3, 1),
    (2, 1, 3, 1),
    (2, 1, 3, 0),
)

CLIPRANGE_FIRST = 0
CLIPRANGE_LAST = 4
CLIPRANGE_RECORD_SIZE = 8
MAX_SOLIDSEGS = VIEWWIDTH // 2 + 1
SOLIDSEGS_BYTES = MAX_SOLIDSEGS * CLIPRANGE_RECORD_SIZE

TRAVERSAL_VISITED_NODE_COUNT = stage03.TRAVERSAL_VISITED_NODE_COUNT
TRAVERSAL_VISITED_SUBSECTOR_COUNT = stage03.TRAVERSAL_VISITED_SUBSECTOR_COUNT
TRAVERSAL_VISITED_SEG_COUNT = stage03.TRAVERSAL_VISITED_SEG_COUNT
TRAVERSAL_MAX_DEPTH = stage03.TRAVERSAL_MAX_DEPTH
TRAVERSAL_FIRST_SUBSECTOR = stage03.TRAVERSAL_FIRST_SUBSECTOR
TRAVERSAL_LAST_SUBSECTOR = stage03.TRAVERSAL_LAST_SUBSECTOR
TRAVERSAL_VIEW_SUBSECTOR = stage03.TRAVERSAL_VIEW_SUBSECTOR
TRAVERSAL_DEBUG_STATE_BYTES = stage03.TRAVERSAL_DEBUG_STATE_BYTES

BBOX_TRAVERSAL_VISITED_NODE_COUNT = 0
BBOX_TRAVERSAL_VISITED_SUBSECTOR_COUNT = 4
BBOX_TRAVERSAL_VISITED_SEG_COUNT = 8
BBOX_TRAVERSAL_MAX_DEPTH = 12
BBOX_TRAVERSAL_FIRST_SUBSECTOR = 16
BBOX_TRAVERSAL_LAST_SUBSECTOR = 20
BBOX_TRAVERSAL_CULLED_NODE_COUNT = 24
BBOX_TRAVERSAL_DEBUG_STATE_BYTES = 28

TABLES_C = Path(__file__).resolve().parents[1] / "reference/chocolate-doom/src/tables.c"

SOURCE_TRACE = stage03.SOURCE_TRACE + (
    ("reference/chocolate-doom/src/tables.c", "SlopeDiv", "render_slope_div"),
    ("reference/chocolate-doom/src/tables.c", "tantoangle / finetangent", "render_angle_tables"),
    ("reference/chocolate-doom/src/doom/r_main.c", "R_PointToAngle", "render_point_to_angle"),
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_InitTextureMapping",
        "render_init_texture_mapping_tables",
    ),
    ("reference/chocolate-doom/src/doom/r_bsp.c", "R_ClearClipSegs", "render_clear_clipsegs"),
    ("reference/chocolate-doom/src/doom/r_bsp.c", "R_CheckBBox", "render_check_bbox"),
)


@dataclass(frozen=True)
class BspVisibilityReference(stage03.BspTraversalReference):
    bbox_visited_node_count: int
    bbox_visited_subsector_count: int
    bbox_visited_seg_count: int
    bbox_max_depth: int
    bbox_first_subsector: int
    bbox_last_subsector: int
    bbox_culled_node_count: int


def _uint32(value: int) -> int:
    return value & 0xFFFFFFFF


def _int32(value: int) -> int:
    return stage03._int32(value)


def _c_div(numerator: int, denominator: int) -> int:
    if denominator == 0:
        raise ZeroDivisionError("fixed-point division by zero")
    sign = -1 if (numerator < 0) ^ (denominator < 0) else 1
    return sign * (abs(numerator) // abs(denominator))


def fixed_mul(a: int, b: int) -> int:
    return _int32((_int32(a) * _int32(b)) >> FRACBITS)


def fixed_div(a: int, b: int) -> int:
    if (abs(_int32(a)) >> 14) >= abs(_int32(b)):
        return -0x80000000 if (_int32(a) ^ _int32(b)) < 0 else 0x7FFFFFFF
    return _int32(_c_div(_int32(a) << FRACBITS, _int32(b)))


def slope_div(num: int, den: int) -> int:
    num = _uint32(num)
    den = _uint32(den)
    if den < 512:
        return SLOPERANGE

    ans = _uint32(num << 3) // (den >> 8)
    return ans if ans <= SLOPERANGE else SLOPERANGE


def _parse_table(name: str, expected_len: int) -> tuple[int, ...]:
    text = TABLES_C.read_text(encoding="utf-8")
    match = re.search(
        rf"const\s+(?:fixed_t|angle_t)\s+{name}\[[^\]]+\]\s*=\s*\{{(.*?)\n\}};",
        text,
        re.DOTALL,
    )
    if not match:
        raise ValueError(f"could not find {name} in {TABLES_C}")
    values = tuple(int(value) for value in re.findall(r"-?\d+", match.group(1)))
    if len(values) != expected_len:
        raise ValueError(f"{name} length {len(values)} != {expected_len}")
    return values


FINETANGENT = _parse_table("finetangent", FINEANGLES // 2)
TANTOANGLE = tuple(_uint32(value) for value in _parse_table("tantoangle", SLOPERANGE + 1))


def generate_texture_mapping_tables() -> tuple[tuple[int, ...], tuple[int, ...], int]:
    viewangletox = [0] * (FINEANGLES // 2)
    xtoviewangle = [0] * (VIEWWIDTH + 1)

    focallength = fixed_div(CENTERXFRAC, FINETANGENT[FINEANGLES // 4 + FIELDOFVIEW // 2])

    for i in range(FINEANGLES // 2):
        tangent = FINETANGENT[i]
        if tangent > FRACUNIT * 2:
            t = -1
        elif tangent < -FRACUNIT * 2:
            t = VIEWWIDTH + 1
        else:
            t = fixed_mul(tangent, focallength)
            t = (CENTERXFRAC - t + FRACUNIT - 1) >> FRACBITS
            if t < -1:
                t = -1
            elif t > VIEWWIDTH + 1:
                t = VIEWWIDTH + 1
        viewangletox[i] = t

    for x in range(VIEWWIDTH + 1):
        i = 0
        while viewangletox[i] > x:
            i += 1
        xtoviewangle[x] = _uint32((i << ANGLETOFINESHIFT) - ANG90)

    for i in range(FINEANGLES // 2):
        if viewangletox[i] == -1:
            viewangletox[i] = 0
        elif viewangletox[i] == VIEWWIDTH + 1:
            viewangletox[i] = VIEWWIDTH

    return tuple(viewangletox), tuple(xtoviewangle), xtoviewangle[0]


VIEWANGLETOX, XTOVIEWANGLE, CLIPANGLE = generate_texture_mapping_tables()


def point_to_angle(x: int, y: int, viewx: int = VIEW_X_FIXED, viewy: int = VIEW_Y_FIXED) -> int:
    x = _int32(x - viewx)
    y = _int32(y - viewy)

    if x == 0 and y == 0:
        return 0

    if x >= 0:
        if y >= 0:
            if x > y:
                return TANTOANGLE[slope_div(y, x)]
            return _uint32(ANG90 - 1 - TANTOANGLE[slope_div(x, y)])

        y = _int32(-y)
        if x > y:
            return _uint32(-TANTOANGLE[slope_div(y, x)])
        return _uint32(ANG270 + TANTOANGLE[slope_div(x, y)])

    x = _int32(-x)
    if y >= 0:
        if x > y:
            return _uint32(ANG180 - 1 - TANTOANGLE[slope_div(y, x)])
        return _uint32(ANG90 + TANTOANGLE[slope_div(x, y)])

    y = _int32(-y)
    if x > y:
        return _uint32(ANG180 + TANTOANGLE[slope_div(y, x)])
    return _uint32(ANG270 - 1 - TANTOANGLE[slope_div(x, y)])


def clear_clipseg_sentinels() -> tuple[tuple[int, int], tuple[int, int]]:
    return ((-0x7FFFFFFF, -1), (VIEWWIDTH, 0x7FFFFFFF))


def check_bbox(
    bspcoord: Sequence[int],
    *,
    viewx: int = VIEW_X_FIXED,
    viewy: int = VIEW_Y_FIXED,
    viewangle: int = VIEW_ANGLE,
    solidsegs: Sequence[tuple[int, int]] | None = None,
) -> bool:
    if solidsegs is None:
        solidsegs = clear_clipseg_sentinels()

    if viewx <= bspcoord[BOXLEFT]:
        boxx = 0
    elif viewx < bspcoord[BOXRIGHT]:
        boxx = 1
    else:
        boxx = 2

    if viewy >= bspcoord[BOXTOP]:
        boxy = 0
    elif viewy > bspcoord[BOXBOTTOM]:
        boxy = 1
    else:
        boxy = 2

    boxpos = (boxy << 2) + boxx
    if boxpos == 5:
        return True

    x1 = bspcoord[CHECKCOORD[boxpos][0]]
    y1 = bspcoord[CHECKCOORD[boxpos][1]]
    x2 = bspcoord[CHECKCOORD[boxpos][2]]
    y2 = bspcoord[CHECKCOORD[boxpos][3]]

    angle1 = _uint32(point_to_angle(x1, y1, viewx, viewy) - viewangle)
    angle2 = _uint32(point_to_angle(x2, y2, viewx, viewy) - viewangle)
    span = _uint32(angle1 - angle2)

    if span >= ANG180:
        return True

    two_clipangle = CLIPANGLE * 2
    tspan = _uint32(angle1 + CLIPANGLE)
    if tspan > two_clipangle:
        tspan = _uint32(tspan - two_clipangle)
        if tspan >= span:
            return False
        angle1 = CLIPANGLE

    tspan = _uint32(CLIPANGLE - angle2)
    if tspan > two_clipangle:
        tspan = _uint32(tspan - two_clipangle)
        if tspan >= span:
            return False
        angle2 = _uint32(-CLIPANGLE)

    angle1_index = _uint32(angle1 + ANG90) >> ANGLETOFINESHIFT
    angle2_index = _uint32(angle2 + ANG90) >> ANGLETOFINESHIFT
    sx1 = VIEWANGLETOX[angle1_index]
    sx2 = VIEWANGLETOX[angle2_index]

    if sx1 == sx2:
        return False
    sx2 -= 1

    start_index = 0
    while solidsegs[start_index][1] < sx2:
        start_index += 1

    first, last = solidsegs[start_index]
    if sx1 >= first and sx2 <= last:
        return False

    return True


def reference_visibility_for_pinned_map(wad_path: str | Path) -> BspVisibilityReference:
    full = stage03.reference_traversal_for_pinned_map(wad_path)
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    map_lumps = wad.map_lumps("MAP01")
    subsectors = stage02.parse_mapsubsectors(wad.read_lump(map_lumps.get("SSECTORS")))
    nodes = tuple(
        stage03.runtime_node_from_mapnode(node)
        for node in stage02.parse_mapnodes(wad.read_lump(map_lumps.get("NODES")))
    )
    segs = stage02.parse_mapsegs(wad.read_lump(map_lumps.get("SEGS")))

    order: list[int] = []
    counts = {
        "nodes": 0,
        "subsectors": 0,
        "segs": 0,
        "depth": 0,
        "culled": 0,
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
        side = stage03.point_on_side_fixed(VIEW_X_FIXED, VIEW_Y_FIXED, node)
        walk(node[12 + side], depth + 1)

        back_side = side ^ 1
        bbox_start = 4 + back_side * 4
        if check_bbox(node[bbox_start : bbox_start + 4]):
            walk(node[12 + back_side], depth + 1)
        else:
            counts["culled"] += 1

    root = (len(nodes) - 1) if nodes else 0xFFFFFFFF
    walk(root, 0)

    return BspVisibilityReference(
        vertex_count=len(loaded.vertices),
        sector_count=len(loaded.sectors),
        sidedef_count=len(loaded.sidedefs),
        linedef_count=len(loaded.linedefs),
        subsector_count=len(subsectors),
        node_count=len(nodes),
        seg_count=len(segs),
        visited_node_count=full.visited_node_count,
        visited_subsector_count=full.visited_subsector_count,
        visited_seg_count=full.visited_seg_count,
        max_depth=full.max_depth,
        first_subsector=full.first_subsector,
        last_subsector=full.last_subsector,
        view_subsector=full.view_subsector,
        bbox_visited_node_count=counts["nodes"],
        bbox_visited_subsector_count=counts["subsectors"],
        bbox_visited_seg_count=counts["segs"],
        bbox_max_depth=counts["depth"],
        bbox_first_subsector=order[0],
        bbox_last_subsector=order[-1],
        bbox_culled_node_count=counts["culled"],
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
    x86.call_rel32(pe, "source_stage04_load_wad_bbox_visibility")

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


def emit_source_stage04_load_wad_bbox_visibility(pe: PE32) -> None:
    pe.label("source_stage04_load_wad_bbox_visibility")
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
    x86.jne_rel32(pe, "source_stage04_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage04_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage04_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage04_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage04_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage04_close_and_return")

    pe.label("source_stage04_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage04_close_and_return")

    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage04_close_and_return")

    x86.call_rel32(pe, "source_stage04_run_bbox_visibility_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage04_close_and_return")

    x86.call_rel32(pe, "build_success_status")

    pe.label("source_stage04_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_source_stage04_run_bbox_visibility_debug(pe: PE32) -> None:
    pe.label("source_stage04_run_bbox_visibility_debug")
    _emit_clear_full_traversal_counters(pe)
    _emit_clear_bbox_traversal_counters(pe)
    x86.mov_mem_abs32_imm32(pe, "traversal_done", 0)

    x86.push_mem_abs32(pe, "viewy")
    x86.push_mem_abs32(pe, "viewx")
    x86.call_rel32(pe, "render_point_in_subsector")

    _emit_load_root_node(pe, "source_stage04_have_nodes", "source_stage04_have_root")
    x86.push_imm8(pe, 0)
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_bsp_node_debug")

    x86.call_rel32(pe, "render_clear_clipsegs")
    _emit_load_root_node(pe, "source_stage04_bbox_have_nodes", "source_stage04_bbox_have_root")
    x86.push_imm8(pe, 0)
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_bsp_node_bbox_debug")

    x86.call_rel32(pe, "render_debug_framebuffer")
    x86.mov_mem_abs32_imm32(pe, "traversal_done", 1)
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)


def _emit_clear_full_traversal_counters(pe: PE32) -> None:
    x86.mov_mem_abs32_imm32(pe, "visited_node_count", 0)
    x86.mov_mem_abs32_imm32(pe, "visited_subsector_count", 0)
    x86.mov_mem_abs32_imm32(pe, "visited_seg_count", 0)
    x86.mov_mem_abs32_imm32(pe, "max_traversal_depth", 0)
    x86.mov_mem_abs32_imm32(pe, "first_visited_subsector", 0xFFFFFFFF)
    x86.mov_mem_abs32_imm32(pe, "last_visited_subsector", 0)
    x86.mov_mem_abs32_imm32(pe, "view_subsector_index", 0)


def _emit_clear_bbox_traversal_counters(pe: PE32) -> None:
    x86.mov_mem_abs32_imm32(pe, "bbox_visible_node_count", 0)
    x86.mov_mem_abs32_imm32(pe, "bbox_visible_subsector_count", 0)
    x86.mov_mem_abs32_imm32(pe, "bbox_visible_seg_count", 0)
    x86.mov_mem_abs32_imm32(pe, "bbox_max_traversal_depth", 0)
    x86.mov_mem_abs32_imm32(pe, "bbox_first_visible_subsector", 0xFFFFFFFF)
    x86.mov_mem_abs32_imm32(pe, "bbox_last_visible_subsector", 0)
    x86.mov_mem_abs32_imm32(pe, "bbox_culled_node_count", 0)


def _emit_load_root_node(pe: PE32, have_nodes_label: str, have_root_label: str) -> None:
    x86.mov_reg_mem_abs32(pe, "eax", "node_count")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, have_nodes_label)
    x86.mov_reg_imm32(pe, "eax", 0xFFFFFFFF)
    x86.jmp_rel32(pe, have_root_label)
    pe.label(have_nodes_label)
    x86.dec_reg(pe, "eax")
    pe.label(have_root_label)


def emit_render_slope_div(pe: PE32) -> None:
    pe.label("render_slope_div")
    x86.emit_function_prologue(pe)

    x86.mov_eax_ebp_disp8(pe, 12)
    x86.cmp_eax_imm32(pe, 512)
    x86.jb_rel32(pe, "slope_div_clamp")

    x86.mov_reg_reg(pe, "ecx", "eax")
    x86.shr_reg_imm8(pe, "ecx", 8)
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.shl_reg_imm8(pe, "eax", 3)
    x86.xor_reg_reg(pe, "edx", "edx")
    x86.div_reg(pe, "ecx")
    x86.cmp_eax_imm32(pe, SLOPERANGE)
    x86.jbe_rel32(pe, "slope_div_done")

    pe.label("slope_div_clamp")
    x86.mov_reg_imm32(pe, "eax", SLOPERANGE)

    pe.label("slope_div_done")
    x86.emit_function_epilogue_ret(pe, 8)


def emit_render_point_to_angle(pe: PE32) -> None:
    pe.label("render_point_to_angle")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.sub_reg_mem_abs32(pe, "eax", "viewx")
    x86.mov_mem_abs32_eax(pe, "point_angle_dx")
    x86.mov_eax_ebp_disp8(pe, 12)
    x86.sub_reg_mem_abs32(pe, "eax", "viewy")
    x86.mov_mem_abs32_eax(pe, "point_angle_dy")

    x86.mov_reg_mem_abs32(pe, "eax", "point_angle_dx")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "point_to_angle_nonzero")
    x86.mov_reg_mem_abs32(pe, "eax", "point_angle_dy")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "point_to_angle_nonzero")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.jmp_rel32(pe, "point_to_angle_return")

    pe.label("point_to_angle_nonzero")
    x86.mov_reg_mem_abs32(pe, "eax", "point_angle_dx")
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "point_to_angle_x_nonnegative")

    x86.neg_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "point_angle_absx")
    x86.mov_reg_mem_abs32(pe, "eax", "point_angle_dy")
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "point_to_angle_xneg_y_nonnegative")
    x86.neg_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "point_angle_absy")
    _emit_point_to_angle_compare_absx_absy(pe, "point_to_angle_oct4", "point_to_angle_oct5")

    pe.label("point_to_angle_oct4")
    _emit_call_slope_div_mem(pe, "point_angle_absy", "point_angle_absx")
    _emit_lookup_tantoangle_from_eax(pe)
    x86.add_reg_imm32(pe, "eax", ANG180)
    x86.jmp_rel32(pe, "point_to_angle_return")

    pe.label("point_to_angle_oct5")
    _emit_call_slope_div_mem(pe, "point_angle_absx", "point_angle_absy")
    _emit_lookup_tantoangle_from_eax(pe)
    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_imm32(pe, "eax", ANG270 - 1)
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.jmp_rel32(pe, "point_to_angle_return")

    pe.label("point_to_angle_xneg_y_nonnegative")
    x86.mov_mem_abs32_eax(pe, "point_angle_absy")
    _emit_point_to_angle_compare_absx_absy(pe, "point_to_angle_oct3", "point_to_angle_oct2")

    pe.label("point_to_angle_oct3")
    _emit_call_slope_div_mem(pe, "point_angle_absy", "point_angle_absx")
    _emit_lookup_tantoangle_from_eax(pe)
    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_imm32(pe, "eax", ANG180 - 1)
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.jmp_rel32(pe, "point_to_angle_return")

    pe.label("point_to_angle_oct2")
    _emit_call_slope_div_mem(pe, "point_angle_absx", "point_angle_absy")
    _emit_lookup_tantoangle_from_eax(pe)
    x86.add_reg_imm32(pe, "eax", ANG90)
    x86.jmp_rel32(pe, "point_to_angle_return")

    pe.label("point_to_angle_x_nonnegative")
    x86.mov_mem_abs32_eax(pe, "point_angle_absx")
    x86.mov_reg_mem_abs32(pe, "eax", "point_angle_dy")
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "point_to_angle_xpos_y_nonnegative")
    x86.neg_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "point_angle_absy")
    _emit_point_to_angle_compare_absx_absy(pe, "point_to_angle_oct8", "point_to_angle_oct7")

    pe.label("point_to_angle_oct8")
    _emit_call_slope_div_mem(pe, "point_angle_absy", "point_angle_absx")
    _emit_lookup_tantoangle_from_eax(pe)
    x86.neg_reg(pe, "eax")
    x86.jmp_rel32(pe, "point_to_angle_return")

    pe.label("point_to_angle_oct7")
    _emit_call_slope_div_mem(pe, "point_angle_absx", "point_angle_absy")
    _emit_lookup_tantoangle_from_eax(pe)
    x86.add_reg_imm32(pe, "eax", ANG270)
    x86.jmp_rel32(pe, "point_to_angle_return")

    pe.label("point_to_angle_xpos_y_nonnegative")
    x86.mov_mem_abs32_eax(pe, "point_angle_absy")
    _emit_point_to_angle_compare_absx_absy(pe, "point_to_angle_oct0", "point_to_angle_oct1")

    pe.label("point_to_angle_oct0")
    _emit_call_slope_div_mem(pe, "point_angle_absy", "point_angle_absx")
    _emit_lookup_tantoangle_from_eax(pe)
    x86.jmp_rel32(pe, "point_to_angle_return")

    pe.label("point_to_angle_oct1")
    _emit_call_slope_div_mem(pe, "point_angle_absx", "point_angle_absy")
    _emit_lookup_tantoangle_from_eax(pe)
    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_imm32(pe, "eax", ANG90 - 1)
    x86.sub_reg_reg(pe, "eax", "ebx")

    pe.label("point_to_angle_return")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 8)


def _emit_point_to_angle_compare_absx_absy(pe: PE32, x_gt_y_label: str, else_label: str) -> None:
    x86.mov_reg_mem_abs32(pe, "eax", "point_angle_absy")
    x86.mov_reg_mem_abs32(pe, "ebx", "point_angle_absx")
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jl_rel32(pe, x_gt_y_label)
    x86.jmp_rel32(pe, else_label)


def _emit_call_slope_div_mem(pe: PE32, num_label: str, den_label: str) -> None:
    x86.push_mem_abs32(pe, den_label)
    x86.push_mem_abs32(pe, num_label)
    x86.call_rel32(pe, "render_slope_div")


def _emit_lookup_tantoangle_from_eax(pe: PE32) -> None:
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "ebx", "render_tantoangle_table")
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "ebx")


def emit_render_clear_clipsegs(pe: PE32) -> None:
    pe.label("render_clear_clipsegs")
    x86.mov_mem_abs32_imm32(pe, "solidsegs_first0", -0x7FFFFFFF)
    x86.mov_mem_abs32_imm32(pe, "solidsegs_last0", -1)
    x86.mov_mem_abs32_imm32(pe, "solidsegs_first1", VIEWWIDTH)
    x86.mov_mem_abs32_imm32(pe, "solidsegs_last1", 0x7FFFFFFF)
    x86.mov_reg_abs32(pe, "eax", "solidsegs")
    x86.add_reg_imm32(pe, "eax", CLIPRANGE_RECORD_SIZE * 2)
    x86.mov_mem_abs32_reg(pe, "solidseg_newend", "eax")
    x86.ret(pe)


def emit_render_check_bbox(pe: PE32) -> None:
    pe.label("render_check_bbox")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_reg_ebp_disp8(pe, "esi", 8)

    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", BOXLEFT * 4)
    x86.mov_reg_mem_abs32(pe, "ebx", "viewx")
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jl_rel32(pe, "check_bbox_viewx_gt_left")
    x86.mov_mem_abs32_imm32(pe, "bbox_boxx", 0)
    x86.jmp_rel32(pe, "check_bbox_boxx_done")

    pe.label("check_bbox_viewx_gt_left")
    x86.mov_reg_mem_abs32(pe, "eax", "viewx")
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", BOXRIGHT * 4)
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jl_rel32(pe, "check_bbox_boxx_middle")
    x86.mov_mem_abs32_imm32(pe, "bbox_boxx", 2)
    x86.jmp_rel32(pe, "check_bbox_boxx_done")
    pe.label("check_bbox_boxx_middle")
    x86.mov_mem_abs32_imm32(pe, "bbox_boxx", 1)

    pe.label("check_bbox_boxx_done")
    x86.mov_reg_mem_abs32(pe, "eax", "viewy")
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", BOXTOP * 4)
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jl_rel32(pe, "check_bbox_viewy_lt_top")
    x86.mov_mem_abs32_imm32(pe, "bbox_boxy", 0)
    x86.jmp_rel32(pe, "check_bbox_boxy_done")

    pe.label("check_bbox_viewy_lt_top")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", BOXBOTTOM * 4)
    x86.mov_reg_mem_abs32(pe, "ebx", "viewy")
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jl_rel32(pe, "check_bbox_boxy_middle")
    x86.mov_mem_abs32_imm32(pe, "bbox_boxy", 2)
    x86.jmp_rel32(pe, "check_bbox_boxy_done")
    pe.label("check_bbox_boxy_middle")
    x86.mov_mem_abs32_imm32(pe, "bbox_boxy", 1)

    pe.label("check_bbox_boxy_done")
    x86.mov_reg_mem_abs32(pe, "eax", "bbox_boxy")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.add_reg_mem_abs32(pe, "eax", "bbox_boxx")
    x86.mov_mem_abs32_eax(pe, "bbox_boxpos")
    x86.cmp_eax_imm32(pe, 5)
    x86.je_rel32(pe, "check_bbox_accept")

    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.shl_reg_imm8(pe, "ebx", 4)
    x86.mov_reg_abs32(pe, "edi", "checkcoord_table")
    x86.add_reg_reg(pe, "edi", "ebx")
    _emit_check_bbox_load_corner(pe, 0, "bbox_x1")
    _emit_check_bbox_load_corner(pe, 4, "bbox_y1")
    _emit_check_bbox_load_corner(pe, 8, "bbox_x2")
    _emit_check_bbox_load_corner(pe, 12, "bbox_y2")

    x86.push_mem_abs32(pe, "bbox_y1")
    x86.push_mem_abs32(pe, "bbox_x1")
    x86.call_rel32(pe, "render_point_to_angle")
    x86.sub_reg_mem_abs32(pe, "eax", "viewangle")
    x86.mov_mem_abs32_eax(pe, "bbox_angle1")

    x86.push_mem_abs32(pe, "bbox_y2")
    x86.push_mem_abs32(pe, "bbox_x2")
    x86.call_rel32(pe, "render_point_to_angle")
    x86.sub_reg_mem_abs32(pe, "eax", "viewangle")
    x86.mov_mem_abs32_eax(pe, "bbox_angle2")

    x86.mov_reg_mem_abs32(pe, "eax", "bbox_angle1")
    x86.sub_reg_mem_abs32(pe, "eax", "bbox_angle2")
    x86.mov_mem_abs32_eax(pe, "bbox_span")
    x86.cmp_eax_imm32(pe, ANG180)
    x86.jae_rel32(pe, "check_bbox_accept")

    x86.mov_reg_mem_abs32(pe, "ebx", "clipangle")
    x86.add_reg_reg(pe, "ebx", "ebx")
    x86.mov_mem_abs32_reg(pe, "bbox_two_clipangle", "ebx")

    x86.mov_reg_mem_abs32(pe, "eax", "bbox_angle1")
    x86.add_reg_mem_abs32(pe, "eax", "clipangle")
    x86.mov_mem_abs32_eax(pe, "bbox_tspan")
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jbe_rel32(pe, "check_bbox_left_clip_done")
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.mov_mem_abs32_eax(pe, "bbox_tspan")
    x86.cmp_reg_mem_abs32(pe, "eax", "bbox_span")
    x86.jae_rel32(pe, "check_bbox_reject")
    x86.mov_reg_mem_abs32(pe, "eax", "clipangle")
    x86.mov_mem_abs32_eax(pe, "bbox_angle1")

    pe.label("check_bbox_left_clip_done")
    x86.mov_reg_mem_abs32(pe, "eax", "clipangle")
    x86.sub_reg_mem_abs32(pe, "eax", "bbox_angle2")
    x86.mov_mem_abs32_eax(pe, "bbox_tspan")
    x86.mov_reg_mem_abs32(pe, "ebx", "bbox_two_clipangle")
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jbe_rel32(pe, "check_bbox_right_clip_done")
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.mov_mem_abs32_eax(pe, "bbox_tspan")
    x86.cmp_reg_mem_abs32(pe, "eax", "bbox_span")
    x86.jae_rel32(pe, "check_bbox_reject")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.sub_reg_mem_abs32(pe, "eax", "clipangle")
    x86.mov_mem_abs32_eax(pe, "bbox_angle2")

    pe.label("check_bbox_right_clip_done")
    _emit_check_bbox_angle_to_x(pe, "bbox_angle1", "bbox_sx1")
    _emit_check_bbox_angle_to_x(pe, "bbox_angle2", "bbox_sx2")
    x86.mov_reg_mem_abs32(pe, "eax", "bbox_sx1")
    x86.cmp_reg_mem_abs32(pe, "eax", "bbox_sx2")
    x86.je_rel32(pe, "check_bbox_reject")
    x86.dec_mem_abs32(pe, "bbox_sx2")

    x86.mov_reg_abs32(pe, "edx", "solidsegs")
    pe.label("check_bbox_clipseg_loop")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edx", CLIPRANGE_LAST)
    x86.cmp_reg_mem_abs32(pe, "eax", "bbox_sx2")
    x86.jl_rel32(pe, "check_bbox_next_clipseg")
    x86.jmp_rel32(pe, "check_bbox_clipseg_found")

    pe.label("check_bbox_next_clipseg")
    x86.add_reg_imm32(pe, "edx", CLIPRANGE_RECORD_SIZE)
    x86.jmp_rel32(pe, "check_bbox_clipseg_loop")

    pe.label("check_bbox_clipseg_found")
    x86.mov_mem_abs32_reg(pe, "bbox_clip_start_ptr", "edx")
    x86.mov_reg_mem_abs32(pe, "eax", "bbox_sx1")
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "edx", CLIPRANGE_FIRST)
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jl_rel32(pe, "check_bbox_accept")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edx", CLIPRANGE_LAST)
    x86.cmp_reg_mem_abs32(pe, "eax", "bbox_sx2")
    x86.jl_rel32(pe, "check_bbox_accept")

    pe.label("check_bbox_reject")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.jmp_rel32(pe, "check_bbox_done")

    pe.label("check_bbox_accept")
    x86.mov_reg_imm32(pe, "eax", 1)

    pe.label("check_bbox_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 4)


def _emit_check_bbox_load_corner(pe: PE32, table_disp: int, dst_label: str) -> None:
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", table_disp)
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_reg(pe, "ebx", "esi")
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "ebx")
    x86.mov_mem_abs32_eax(pe, dst_label)


def _emit_check_bbox_angle_to_x(pe: PE32, angle_label: str, dst_label: str) -> None:
    x86.mov_reg_mem_abs32(pe, "eax", angle_label)
    x86.add_reg_imm32(pe, "eax", ANG90)
    x86.shr_reg_imm8(pe, "eax", ANGLETOFINESHIFT)
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "ebx", "render_viewangletox_table")
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "ebx")
    x86.mov_mem_abs32_eax(pe, dst_label)


def emit_render_debug_subsector_bbox(pe: PE32) -> None:
    pe.label("render_debug_subsector_bbox")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.cmp_reg_mem_abs32(pe, "eax", "subsector_count")
    x86.jae_rel32(pe, "debug_subsector_bbox_done")

    x86.mov_reg_mem_abs32(pe, "ebx", "bbox_visible_subsector_count")
    x86.test_reg_reg(pe, "ebx")
    x86.jne_rel32(pe, "debug_subsector_bbox_not_first")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_mem_abs32_eax(pe, "bbox_first_visible_subsector")

    pe.label("debug_subsector_bbox_not_first")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_mem_abs32_eax(pe, "bbox_last_visible_subsector")
    x86.mov_reg_mem_abs32(pe, "eax", "bbox_visible_subsector_count")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "bbox_visible_subsector_count")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.shl_reg_imm8(pe, "eax", 3)
    x86.mov_reg_abs32(pe, "esi", "subsectors_buffer")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "ecx", "esi", stage02.SUBSECTOR_NUMLINES)
    x86.movzx_reg_word_ptr_reg_disp8(pe, "edx", "esi", stage02.SUBSECTOR_FIRSTLINE)

    pe.label("debug_subsector_bbox_seg_loop")
    x86.test_reg_reg(pe, "ecx")
    x86.je_rel32(pe, "debug_subsector_bbox_done")
    x86.mov_reg_mem_abs32(pe, "ebx", "bbox_visible_seg_count")
    x86.cmp_reg_imm32(pe, "ebx", MAX_VISITED_SEGS)
    x86.jae_rel32(pe, "debug_subsector_bbox_skip_seg_store")
    x86.mov_reg_reg(pe, "eax", "ebx")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "edi", "bbox_visible_seg_indices")
    x86.add_reg_reg(pe, "edi", "eax")
    x86.mov_reg_reg(pe, "eax", "edx")
    x86.mov_ptr_reg_eax(pe, "edi")

    pe.label("debug_subsector_bbox_skip_seg_store")
    x86.mov_reg_mem_abs32(pe, "eax", "bbox_visible_seg_count")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "bbox_visible_seg_count")
    x86.inc_reg(pe, "edx")
    x86.dec_reg(pe, "ecx")
    x86.jmp_rel32(pe, "debug_subsector_bbox_seg_loop")

    pe.label("debug_subsector_bbox_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_render_bsp_node_bbox_debug(pe: PE32) -> None:
    pe.label("render_bsp_node_bbox_debug")
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
    x86.jne_rel32(pe, "bsp_node_bbox_is_subsector")

    _emit_update_bbox_max_depth_from_arg(pe, "node")
    x86.mov_reg_mem_abs32(pe, "eax", "bbox_visible_node_count")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "bbox_visible_node_count")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.cmp_reg_mem_abs32(pe, "eax", "node_count")
    x86.jae_rel32(pe, "bsp_node_bbox_done")
    x86.imul_reg_reg_imm32(pe, "ebx", "eax", stage02.NODE_T_RECORD_SIZE)
    x86.mov_reg_abs32(pe, "esi", "nodes_buffer")
    x86.add_reg_reg(pe, "esi", "ebx")

    x86.push_reg(pe, "esi")
    x86.push_mem_abs32(pe, "viewy")
    x86.push_mem_abs32(pe, "viewx")
    x86.call_rel32(pe, "render_point_on_side")
    x86.mov_reg_reg(pe, "ebx", "eax")

    x86.test_reg_reg(pe, "ebx")
    x86.jne_rel32(pe, "bsp_node_bbox_front_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD0)
    x86.jmp_rel32(pe, "bsp_node_bbox_have_front_child")

    pe.label("bsp_node_bbox_front_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD1)

    pe.label("bsp_node_bbox_have_front_child")
    _emit_recurse_bsp_child_bbox(pe)

    x86.test_reg_reg(pe, "ebx")
    x86.jne_rel32(pe, "bsp_node_bbox_back_bbox_side_one")
    x86.mov_reg_reg(pe, "edi", "esi")
    x86.add_reg_imm32(pe, "edi", stage02.NODE_BBOX + 16)
    x86.jmp_rel32(pe, "bsp_node_bbox_have_back_bbox")

    pe.label("bsp_node_bbox_back_bbox_side_one")
    x86.mov_reg_reg(pe, "edi", "esi")
    x86.add_reg_imm32(pe, "edi", stage02.NODE_BBOX)

    pe.label("bsp_node_bbox_have_back_bbox")
    x86.push_reg(pe, "edi")
    x86.call_rel32(pe, "render_check_bbox")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "bsp_node_bbox_back_visible")
    x86.mov_reg_mem_abs32(pe, "eax", "bbox_culled_node_count")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "bbox_culled_node_count")
    x86.jmp_rel32(pe, "bsp_node_bbox_done")

    pe.label("bsp_node_bbox_back_visible")
    x86.test_reg_reg(pe, "ebx")
    x86.jne_rel32(pe, "bsp_node_bbox_back_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD1)
    x86.jmp_rel32(pe, "bsp_node_bbox_have_back_child")

    pe.label("bsp_node_bbox_back_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD0)

    pe.label("bsp_node_bbox_have_back_child")
    _emit_recurse_bsp_child_bbox(pe)
    x86.jmp_rel32(pe, "bsp_node_bbox_done")

    pe.label("bsp_node_bbox_is_subsector")
    _emit_update_bbox_max_depth_from_arg(pe, "subsector")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.jne_rel32(pe, "bsp_node_bbox_normal_subsector")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.jmp_rel32(pe, "bsp_node_bbox_call_subsector")

    pe.label("bsp_node_bbox_normal_subsector")
    x86.and_reg_imm32(pe, "eax", ~NF_SUBSECTOR)

    pe.label("bsp_node_bbox_call_subsector")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_debug_subsector_bbox")

    pe.label("bsp_node_bbox_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 8)


def _emit_update_bbox_max_depth_from_arg(pe: PE32, suffix: str) -> None:
    done_label = f"bsp_node_bbox_depth_not_larger_{suffix}"
    x86.mov_eax_ebp_disp8(pe, 12)
    x86.cmp_reg_mem_abs32(pe, "eax", "bbox_max_traversal_depth")
    x86.jbe_rel32(pe, done_label)
    x86.mov_mem_abs32_eax(pe, "bbox_max_traversal_depth")
    pe.label(done_label)


def _emit_recurse_bsp_child_bbox(pe: PE32) -> None:
    x86.mov_reg_ebp_disp8(pe, "ecx", 12)
    x86.inc_reg(pe, "ecx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_bsp_node_bbox_debug")


def emit_render_debug_framebuffer(pe: PE32) -> None:
    pe.label("render_debug_framebuffer")
    x86.call_rel32(pe, "clear_framebuffer")
    x86.call_rel32(pe, "draw_all_linedefs")
    x86.call_rel32(pe, "draw_visited_segs")
    x86.call_rel32(pe, "draw_bbox_visible_segs")
    x86.call_rel32(pe, "draw_viewpoint_marker")
    x86.ret(pe)


def emit_draw_bbox_visible_segs(pe: PE32) -> None:
    pe.label("draw_bbox_visible_segs")
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_mem_abs32_imm32(pe, "draw_color", COLOR_BBOX_VISIBLE_SEG)
    x86.mov_reg_abs32(pe, "esi", "bbox_visible_seg_indices")
    x86.mov_mem_abs32_reg(pe, "draw_scan_ptr", "esi")
    x86.mov_reg_mem_abs32(pe, "eax", "bbox_visible_seg_count")
    x86.mov_mem_abs32_eax(pe, "draw_remaining")

    pe.label("draw_bbox_visible_segs_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "draw_remaining")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "draw_bbox_visible_segs_done")

    x86.mov_reg_mem_abs32(pe, "esi", "draw_scan_ptr")
    x86.mov_reg_ptr_reg(pe, "eax", "esi")
    x86.cmp_reg_mem_abs32(pe, "eax", "seg_count")
    x86.jae_rel32(pe, "draw_bbox_visible_segs_next")
    x86.imul_reg_reg_imm32(pe, "ebx", "eax", stage02.SEG_T_RECORD_SIZE)
    x86.mov_reg_abs32(pe, "edi", "segs_buffer")
    x86.add_reg_reg(pe, "edi", "ebx")
    x86.mov_reg_reg(pe, "ebx", "edi")

    x86.mov_reg_ptr_reg_disp8(pe, "edi", "ebx", stage02.SEG_V1)
    stage03._emit_line_endpoint_from_vertex_ptr(pe, "line_x0", "line_y0")
    x86.mov_reg_ptr_reg_disp8(pe, "edi", "ebx", stage02.SEG_V2)
    stage03._emit_line_endpoint_from_vertex_ptr(pe, "line_x1", "line_y1")
    x86.call_rel32(pe, "draw_line")

    pe.label("draw_bbox_visible_segs_next")
    x86.mov_reg_mem_abs32(pe, "esi", "draw_scan_ptr")
    x86.add_reg_imm32(pe, "esi", 4)
    x86.mov_mem_abs32_reg(pe, "draw_scan_ptr", "esi")
    x86.dec_mem_abs32(pe, "draw_remaining")
    x86.jmp_rel32(pe, "draw_bbox_visible_segs_loop")

    pe.label("draw_bbox_visible_segs_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_build_success_status(pe: PE32) -> None:
    pe.label("build_success_status")
    x86.mov_reg_abs32(pe, "edi", "status_success_buffer")

    stage01.append_c_string_label(pe, "status_stage04_success_header")
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
    stage01.append_u32_label(pe, "status_bbox_nodes_prefix", "bbox_visible_node_count")
    stage01.append_u32_label(pe, "status_bbox_subsectors_prefix", "bbox_visible_subsector_count")
    stage01.append_u32_label(pe, "status_bbox_segs_prefix", "bbox_visible_seg_count")
    stage01.append_u32_label(pe, "status_bbox_depth_prefix", "bbox_max_traversal_depth")
    stage01.append_u32_label(pe, "status_bbox_firstss_prefix", "bbox_first_visible_subsector")
    stage01.append_u32_label(pe, "status_bbox_lastss_prefix", "bbox_last_visible_subsector")
    stage01.append_u32_label(pe, "status_bbox_cull_prefix", "bbox_culled_node_count")
    stage01.append_c_string_label(pe, "status_bbox_visibility_note")
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
    stage01.append_u32_label(pe, "title_bvn_prefix", "bbox_visible_node_count")
    stage01.append_u32_label(pe, "title_bvss_prefix", "bbox_visible_subsector_count")
    stage01.append_u32_label(pe, "title_bvseg_prefix", "bbox_visible_seg_count")
    stage01.append_u32_label(pe, "title_bdepth_prefix", "bbox_max_traversal_depth")
    stage01.append_u32_label(pe, "title_bfirstss_prefix", "bbox_first_visible_subsector")
    stage01.append_u32_label(pe, "title_blastss_prefix", "bbox_last_visible_subsector")
    stage01.append_u32_label(pe, "title_cull_prefix", "bbox_culled_node_count")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage04_data(pe: PE32) -> None:
    pe.align_section(4)
    pe.label("viewx")
    pe.emit_u32(VIEW_X_FIXED)
    pe.label("viewy")
    pe.emit_u32(VIEW_Y_FIXED)
    pe.label("viewangle")
    pe.emit_u32(VIEW_ANGLE)
    pe.label("viewwidth")
    pe.emit_u32(VIEWWIDTH)
    pe.label("centerx")
    pe.emit_u32(CENTERX)
    pe.label("centerxfrac")
    pe.emit_u32(CENTERXFRAC)
    pe.label("projection")
    pe.emit_u32(PROJECTION)
    pe.label("clipangle")
    pe.emit_u32(CLIPANGLE)
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

    pe.label("bbox_traversal_debug_state")
    pe.label("bbox_visible_node_count")
    pe.emit_u32(0)
    pe.label("bbox_visible_subsector_count")
    pe.emit_u32(0)
    pe.label("bbox_visible_seg_count")
    pe.emit_u32(0)
    pe.label("bbox_max_traversal_depth")
    pe.emit_u32(0)
    pe.label("bbox_first_visible_subsector")
    pe.emit_u32(0xFFFFFFFF)
    pe.label("bbox_last_visible_subsector")
    pe.emit_u32(0)
    pe.label("bbox_culled_node_count")
    pe.emit_u32(0)

    pe.label("point_side_dx")
    pe.emit_u32(0)
    pe.label("point_side_dy")
    pe.emit_u32(0)
    pe.label("point_side_left")
    pe.emit_u32(0)
    pe.label("point_in_subsector_nodenum")
    pe.emit_u32(0)

    pe.label("point_angle_dx")
    pe.emit_u32(0)
    pe.label("point_angle_dy")
    pe.emit_u32(0)
    pe.label("point_angle_absx")
    pe.emit_u32(0)
    pe.label("point_angle_absy")
    pe.emit_u32(0)

    pe.label("bbox_boxx")
    pe.emit_u32(0)
    pe.label("bbox_boxy")
    pe.emit_u32(0)
    pe.label("bbox_boxpos")
    pe.emit_u32(0)
    pe.label("bbox_x1")
    pe.emit_u32(0)
    pe.label("bbox_y1")
    pe.emit_u32(0)
    pe.label("bbox_x2")
    pe.emit_u32(0)
    pe.label("bbox_y2")
    pe.emit_u32(0)
    pe.label("bbox_angle1")
    pe.emit_u32(0)
    pe.label("bbox_angle2")
    pe.emit_u32(0)
    pe.label("bbox_span")
    pe.emit_u32(0)
    pe.label("bbox_tspan")
    pe.emit_u32(0)
    pe.label("bbox_two_clipangle")
    pe.emit_u32(0)
    pe.label("bbox_sx1")
    pe.emit_u32(0)
    pe.label("bbox_sx2")
    pe.emit_u32(0)
    pe.label("bbox_clip_start_ptr")
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
    pe.emit_u32(stage03.BI_RGB)
    pe.emit_u32(FRAMEBUFFER_BYTES)
    pe.emit_u32(0)
    pe.emit_u32(0)
    pe.emit_u32(0)
    pe.emit_u32(0)

    pe.align_section(1)
    pe.label("status_stage04_success_header")
    x86.emit_asciiz(pe, "source_stage04_bbox_visibility_debug\r\nBBox visibility debug OK\r\n")
    pe.label("status_view_subsector_prefix")
    x86.emit_asciiz(pe, "\r\nR_PointInSubsector view ss: ")
    pe.label("status_visited_nodes_prefix")
    x86.emit_asciiz(pe, "\r\nAccept-all R_RenderBSPNode visited nodes: ")
    pe.label("status_visited_subsectors_prefix")
    x86.emit_asciiz(pe, "\r\nAccept-all R_Subsector visited subsectors: ")
    pe.label("status_visited_segs_prefix")
    x86.emit_asciiz(pe, "\r\nAccept-all R_Subsector visited segs: ")
    pe.label("status_depth_prefix")
    x86.emit_asciiz(pe, "\r\nAccept-all max traversal depth: ")
    pe.label("status_firstss_prefix")
    x86.emit_asciiz(pe, "\r\nAccept-all first visited subsector: ")
    pe.label("status_lastss_prefix")
    x86.emit_asciiz(pe, "\r\nAccept-all last visited subsector: ")
    pe.label("status_bbox_nodes_prefix")
    x86.emit_asciiz(pe, "\r\nR_CheckBBox visible nodes: ")
    pe.label("status_bbox_subsectors_prefix")
    x86.emit_asciiz(pe, "\r\nR_CheckBBox visible subsectors: ")
    pe.label("status_bbox_segs_prefix")
    x86.emit_asciiz(pe, "\r\nR_CheckBBox visible segs: ")
    pe.label("status_bbox_depth_prefix")
    x86.emit_asciiz(pe, "\r\nR_CheckBBox max traversal depth: ")
    pe.label("status_bbox_firstss_prefix")
    x86.emit_asciiz(pe, "\r\nR_CheckBBox first visible subsector: ")
    pe.label("status_bbox_lastss_prefix")
    x86.emit_asciiz(pe, "\r\nR_CheckBBox last visible subsector: ")
    pe.label("status_bbox_cull_prefix")
    x86.emit_asciiz(pe, "\r\nR_CheckBBox culled back children: ")
    pe.label("status_bbox_visibility_note")
    x86.emit_asciiz(
        pe,
        "\r\nR_ClearClipSegs sentinel solidsegs only; no R_AddLine or wall span clipping\r\n"
        "render_angle_tables table-emitted; render_init_texture_mapping_tables table-emitted\r\n",
    )

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
    pe.label("title_bvn_prefix")
    x86.emit_asciiz(pe, " BVN=")
    pe.label("title_bvss_prefix")
    x86.emit_asciiz(pe, " BVSS=")
    pe.label("title_bvseg_prefix")
    x86.emit_asciiz(pe, " BVSEG=")
    pe.label("title_bdepth_prefix")
    x86.emit_asciiz(pe, " BDEPTH=")
    pe.label("title_bfirstss_prefix")
    x86.emit_asciiz(pe, " BFIRSTSS=")
    pe.label("title_blastss_prefix")
    x86.emit_asciiz(pe, " BLASTSS=")
    pe.label("title_cull_prefix")
    x86.emit_asciiz(pe, " CULL=")

    pe.align_section(4)
    pe.label("checkcoord_table")
    for row in CHECKCOORD:
        for value in row:
            pe.emit_u32(value)

    pe.align_section(4)
    pe.label("render_angle_tables")
    pe.label("render_finetangent_table")
    for value in FINETANGENT:
        pe.emit_u32(value)

    pe.align_section(4)
    pe.label("render_tantoangle_table")
    for value in TANTOANGLE:
        pe.emit_u32(value)

    pe.align_section(4)
    pe.label("render_init_texture_mapping_tables")
    pe.label("render_viewangletox_table")
    for value in VIEWANGLETOX:
        pe.emit_u32(value)

    pe.align_section(4)
    pe.label("render_xtoviewangle_table")
    for value in XTOVIEWANGLE:
        pe.emit_u32(value)

    pe.align_section(4)
    pe.label("solidseg_newend")
    pe.emit_u32(0)
    pe.label("solidsegs")
    pe.label("solidsegs_first0")
    pe.emit_u32(-0x7FFFFFFF)
    pe.label("solidsegs_last0")
    pe.emit_u32(-1)
    pe.label("solidsegs_first1")
    pe.emit_u32(VIEWWIDTH)
    pe.label("solidsegs_last1")
    pe.emit_u32(0x7FFFFFFF)
    pe.emit_zeros(SOLIDSEGS_BYTES - CLIPRANGE_RECORD_SIZE * 2)

    pe.align_section(4)
    pe.label("visited_seg_indices")
    pe.emit_zeros(VISITED_SEG_INDICES_BYTES)

    pe.align_section(4)
    pe.label("bbox_visible_seg_indices")
    pe.emit_zeros(BBOX_VISIBLE_SEG_INDICES_BYTES)

    pe.align_section(4)
    pe.label("framebuffer")
    pe.emit_zeros(FRAMEBUFFER_BYTES)


def build_source_stage04_bbox_visibility_debug_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage04_load_wad_bbox_visibility(pe)
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
    emit_source_stage04_run_bbox_visibility_debug(pe)
    stage03.emit_render_fixed_mul(pe)
    stage03.emit_render_point_on_side(pe)
    stage03.emit_render_point_in_subsector(pe)
    stage03.emit_render_debug_subsector(pe)
    stage03.emit_render_check_bbox_accept_all(pe)
    stage03.emit_render_bsp_node_debug(pe)
    emit_render_slope_div(pe)
    emit_render_point_to_angle(pe)
    emit_render_clear_clipsegs(pe)
    emit_render_check_bbox(pe)
    emit_render_debug_subsector_bbox(pe)
    emit_render_bsp_node_bbox_debug(pe)
    emit_render_debug_framebuffer(pe)
    stage03.emit_clear_framebuffer(pe)
    stage03.emit_render_error_pattern(pe)
    stage03.emit_transform_point_to_screen(pe)
    stage03.emit_draw_all_linedefs(pe)
    stage03.emit_draw_visited_segs(pe)
    emit_draw_bbox_visible_segs(pe)
    stage03.emit_draw_viewpoint_marker(pe)
    stage03.emit_draw_line(pe)
    stage03.emit_plot_pixel(pe)
    emit_build_success_status(pe)
    stage01.emit_append_c_string(pe)
    stage01.emit_append_u32_decimal(pe)
    stage01.emit_append_i32_decimal(pe)
    with patched_stage01_window_labels():
        stage01.emit_data(pe)
    stage02.emit_stage02_data(pe)
    emit_stage04_data(pe)
    return pe.build("entry")


def write_source_stage04_bbox_visibility_debug_exe(path: str | Path) -> bytes:
    image = build_source_stage04_bbox_visibility_debug_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the source-guided PE32 x86 bbox visibility debug executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/source_stage04_bbox_visibility_debug.exe",
        help="path to write, default: build/source_stage04_bbox_visibility_debug.exe",
    )
    args = parser.parse_args()
    write_source_stage04_bbox_visibility_debug_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
