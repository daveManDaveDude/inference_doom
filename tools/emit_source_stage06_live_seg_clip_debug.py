from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage01_wad_map as stage01
from tools import emit_source_stage02_bsp_setup as stage02
from tools import emit_source_stage03_bsp_walk_debug as stage03
from tools import emit_source_stage04_bbox_visibility_debug as stage04
from tools import x86
from tools.map_loader import LineDef, LoadedMap, Sector, SideDef, Vertex, load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


FRAMEBUFFER_WIDTH = stage04.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage04.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage04.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage04.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage04.WINDOW_WIDTH
WINDOW_HEIGHT = stage04.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage06LiveSegClipDebug"
WINDOW_TITLE = "Inference Doom S06 Live Seg Clip"
WAD_PATH = stage04.WAD_PATH

FRACBITS = stage04.FRACBITS
FRACUNIT = stage04.FRACUNIT
NF_SUBSECTOR = stage04.NF_SUBSECTOR

VIEW_X_FIXED = stage04.VIEW_X_FIXED
VIEW_Y_FIXED = stage04.VIEW_Y_FIXED
VIEW_ANGLE = stage04.VIEW_ANGLE

ANG90 = stage04.ANG90
ANG180 = stage04.ANG180
ANGLETOFINESHIFT = stage04.ANGLETOFINESHIFT
VIEWWIDTH = stage04.VIEWWIDTH
CLIPANGLE = stage04.CLIPANGLE

CLIPRANGE_FIRST = stage04.CLIPRANGE_FIRST
CLIPRANGE_LAST = stage04.CLIPRANGE_LAST
CLIPRANGE_RECORD_SIZE = stage04.CLIPRANGE_RECORD_SIZE
MAX_SOLIDSEGS = stage04.MAX_SOLIDSEGS
SOLIDSEGS_BYTES = stage04.SOLIDSEGS_BYTES

ML_TWOSIDED = stage02.ML_TWOSIDED

SECTOR_FLOORHEIGHT = 0
SECTOR_CEILINGHEIGHT = 4
SECTOR_FLOORPIC0 = 8
SECTOR_FLOORPIC1 = 12
SECTOR_CEILINGPIC0 = 16
SECTOR_CEILINGPIC1 = 20
SECTOR_LIGHTLEVEL = 24

SIDE_MIDTEXTURE0 = 24
SIDE_MIDTEXTURE1 = 28

SPAN_REASON_SOLID = 1
SPAN_REASON_PASS = 2
DEBUG_SPAN_START = 0
DEBUG_SPAN_STOP = 4
DEBUG_SPAN_REASON = 8
DEBUG_SPAN_SEG_INDEX = 12
DEBUG_SPAN_RECORD_SIZE = 16
MAX_DEBUG_SPANS = 512
DEBUG_SPAN_BUFFER_BYTES = MAX_DEBUG_SPANS * DEBUG_SPAN_RECORD_SIZE

CLIP_TRAVERSAL_VISITED_NODE_COUNT = 0
CLIP_TRAVERSAL_VISITED_SUBSECTOR_COUNT = 4
CLIP_TRAVERSAL_VISITED_SEG_COUNT = 8
CLIP_TRAVERSAL_MAX_DEPTH = 12
CLIP_TRAVERSAL_FIRST_SUBSECTOR = 16
CLIP_TRAVERSAL_LAST_SUBSECTOR = 20
CLIP_TRAVERSAL_CULLED_NODE_COUNT = 24
CLIP_TRAVERSAL_BACKFACE_REJECT_COUNT = 28
CLIP_TRAVERSAL_OFF_FRUSTUM_REJECT_COUNT = 32
CLIP_TRAVERSAL_ZERO_PIXEL_REJECT_COUNT = 36
CLIP_TRAVERSAL_SOLID_SEG_COUNT = 40
CLIP_TRAVERSAL_PASS_SEG_COUNT = 44
CLIP_TRAVERSAL_EMPTY_LINE_REJECT_COUNT = 48
CLIP_TRAVERSAL_STORED_SPAN_COUNT = 52
CLIP_TRAVERSAL_FINAL_SOLIDSEG_COUNT = 56
CLIP_TRAVERSAL_SPAN_OVERFLOW_COUNT = 60
CLIP_TRAVERSAL_INSERT_COUNT = 64
CLIP_TRAVERSAL_EXTEND_FRONT_COUNT = 68
CLIP_TRAVERSAL_EXTEND_TAIL_COUNT = 72
CLIP_TRAVERSAL_MERGE_COUNT = 76
CLIP_TRAVERSAL_DEBUG_STATE_BYTES = 80

SOURCE_TRACE = stage04.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/r_bsp.c",
        "R_RenderBSPNode",
        "render_bsp_node_clip_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_bsp.c",
        "R_Subsector",
        "render_debug_subsector_clip",
    ),
    (
        "reference/chocolate-doom/src/doom/r_bsp.c",
        "R_AddLine",
        "render_add_line_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_bsp.c",
        "R_ClipSolidWallSegment",
        "render_clip_solid_wall_segment",
    ),
    (
        "reference/chocolate-doom/src/doom/r_bsp.c",
        "R_ClipPassWallSegment",
        "render_clip_pass_wall_segment",
    ),
    (
        "reference/chocolate-doom/src/doom/r_segs.c",
        "R_StoreWallRange",
        "render_store_wall_range_debug",
    ),
)


@dataclass(frozen=True)
class DebugSector:
    floor_height: int
    ceiling_height: int
    floor_flat: str = "FLOOR"
    ceiling_flat: str = "CEIL"
    light_level: int = 160


@dataclass(frozen=True)
class DebugSideDef:
    middle_texture: str
    sector: int


@dataclass(frozen=True)
class DebugLineDef:
    flags: int
    right_sidedef: int
    left_sidedef: int = 0xFFFF


@dataclass(frozen=True)
class DebugSeg:
    v1: int
    v2: int
    linedef: int
    side: int = 0


@dataclass(frozen=True)
class DebugSpan:
    start: int
    stop: int
    reason: int
    seg_index: int


@dataclass
class SegClipDebugState:
    solidsegs: list[tuple[int, int]] = field(
        default_factory=lambda: list(stage04.clear_clipseg_sentinels())
    )
    spans: list[DebugSpan] = field(default_factory=list)
    max_spans: int = MAX_DEBUG_SPANS
    current_reason: int = 0
    current_seg_index: int = -1
    visited_node_count: int = 0
    visited_subsector_count: int = 0
    visited_seg_count: int = 0
    max_depth: int = 0
    first_subsector: int = -1
    last_subsector: int = 0
    bbox_cull_count: int = 0
    backface_reject_count: int = 0
    off_frustum_reject_count: int = 0
    zero_pixel_reject_count: int = 0
    solid_classification_count: int = 0
    pass_classification_count: int = 0
    empty_line_reject_count: int = 0
    stored_span_count: int = 0
    span_overflow_count: int = 0
    clip_insert_count: int = 0
    clip_extend_front_count: int = 0
    clip_extend_tail_count: int = 0
    clip_merge_count: int = 0

    @property
    def final_solidseg_count(self) -> int:
        return len(self.solidsegs)

    @property
    def first_span(self) -> DebugSpan | None:
        return self.spans[0] if self.spans else None

    @property
    def last_span(self) -> DebugSpan | None:
        return self.spans[-1] if self.spans else None


@dataclass(frozen=True)
class SegClipReference(stage04.BspVisibilityReference):
    clip_visited_node_count: int
    clip_visited_subsector_count: int
    clip_visited_seg_count: int
    clip_max_depth: int
    clip_first_subsector: int
    clip_last_subsector: int
    clip_bbox_cull_count: int
    backface_reject_count: int
    off_frustum_reject_count: int
    zero_pixel_reject_count: int
    solid_classification_count: int
    pass_classification_count: int
    empty_line_reject_count: int
    stored_span_count: int
    final_solidseg_count: int
    span_overflow_count: int
    clip_insert_count: int
    clip_extend_front_count: int
    clip_extend_tail_count: int
    clip_merge_count: int
    first_span: DebugSpan
    last_span: DebugSpan


def angle_to_view_x(angle: int) -> int:
    index = stage04._uint32(angle + ANG90) >> ANGLETOFINESHIFT
    return stage04.VIEWANGLETOX[index]


def debug_store_wall_range(
    state: SegClipDebugState, start: int, stop: int, *, reason: int | None = None, seg_index: int | None = None
) -> None:
    if start > stop:
        return

    if len(state.spans) >= state.max_spans:
        state.span_overflow_count += 1
        return

    state.spans.append(
        DebugSpan(
            start=start,
            stop=stop,
            reason=state.current_reason if reason is None else reason,
            seg_index=state.current_seg_index if seg_index is None else seg_index,
        )
    )
    state.stored_span_count += 1


def debug_clip_solid_wall_segment(state: SegClipDebugState, first: int, last: int) -> None:
    start = 0
    while state.solidsegs[start][1] < first - 1:
        start += 1

    if first < state.solidsegs[start][0]:
        if last < state.solidsegs[start][0] - 1:
            debug_store_wall_range(state, first, last)
            state.solidsegs.insert(start, (first, last))
            state.clip_insert_count += 1
            return

        debug_store_wall_range(state, first, state.solidsegs[start][0] - 1)
        state.solidsegs[start] = (first, state.solidsegs[start][1])
        state.clip_extend_front_count += 1

    if last <= state.solidsegs[start][1]:
        return

    next_index = start
    while last >= state.solidsegs[next_index + 1][0] - 1:
        debug_store_wall_range(
            state,
            state.solidsegs[next_index][1] + 1,
            state.solidsegs[next_index + 1][0] - 1,
        )
        next_index += 1

        if last <= state.solidsegs[next_index][1]:
            state.solidsegs[start] = (
                state.solidsegs[start][0],
                state.solidsegs[next_index][1],
            )
            if next_index != start:
                del state.solidsegs[start + 1 : next_index + 1]
                state.clip_merge_count += 1
            else:
                state.clip_extend_tail_count += 1
            return

    debug_store_wall_range(state, state.solidsegs[next_index][1] + 1, last)
    state.solidsegs[start] = (state.solidsegs[start][0], last)

    if next_index == start:
        state.clip_extend_tail_count += 1
        return

    del state.solidsegs[start + 1 : next_index + 1]
    state.clip_merge_count += 1


def debug_clip_pass_wall_segment(state: SegClipDebugState, first: int, last: int) -> None:
    start = 0
    while state.solidsegs[start][1] < first - 1:
        start += 1

    if first < state.solidsegs[start][0]:
        if last < state.solidsegs[start][0] - 1:
            debug_store_wall_range(state, first, last)
            return

        debug_store_wall_range(state, first, state.solidsegs[start][0] - 1)

    if last <= state.solidsegs[start][1]:
        return

    while last >= state.solidsegs[start + 1][0] - 1:
        debug_store_wall_range(
            state,
            state.solidsegs[start][1] + 1,
            state.solidsegs[start + 1][0] - 1,
        )
        start += 1

        if last <= state.solidsegs[start][1]:
            return

    debug_store_wall_range(state, state.solidsegs[start][1] + 1, last)


def _sector_from_any(sector: Sector | DebugSector) -> DebugSector:
    return DebugSector(
        floor_height=sector.floor_height,
        ceiling_height=sector.ceiling_height,
        floor_flat=getattr(sector, "floor_flat", "FLOOR"),
        ceiling_flat=getattr(sector, "ceiling_flat", "CEIL"),
        light_level=sector.light_level,
    )


def _line_backsector(
    line: LineDef | DebugLineDef,
    side: int,
    sidedefs: Sequence[SideDef | DebugSideDef],
    sectors: Sequence[Sector | DebugSector],
) -> DebugSector | None:
    if not (line.flags & ML_TWOSIDED):
        return None

    sidenum = line.left_sidedef if side == 0 else line.right_sidedef
    if sidenum == 0xFFFF or sidenum >= len(sidedefs):
        return None

    return _sector_from_any(sectors[sidedefs[sidenum].sector])


def _line_sidedef(
    line: LineDef | DebugLineDef, side: int, sidedefs: Sequence[SideDef | DebugSideDef]
) -> SideDef | DebugSideDef:
    sidenum = line.right_sidedef if side == 0 else line.left_sidedef
    return sidedefs[sidenum]


def debug_add_line(
    state: SegClipDebugState,
    seg: DebugSeg,
    vertices: Sequence[Vertex],
    linedefs: Sequence[LineDef | DebugLineDef],
    sidedefs: Sequence[SideDef | DebugSideDef],
    sectors: Sequence[Sector | DebugSector],
    *,
    frontsector_index: int,
    seg_index: int,
) -> tuple[int, int] | None:
    state.current_seg_index = seg_index

    v1 = vertices[seg.v1]
    v2 = vertices[seg.v2]
    angle1 = stage04.point_to_angle(v1.x << FRACBITS, v1.y << FRACBITS)
    angle2 = stage04.point_to_angle(v2.x << FRACBITS, v2.y << FRACBITS)
    span = stage04._uint32(angle1 - angle2)

    if span >= ANG180:
        state.backface_reject_count += 1
        return None

    angle1 = stage04._uint32(angle1 - VIEW_ANGLE)
    angle2 = stage04._uint32(angle2 - VIEW_ANGLE)

    two_clipangle = CLIPANGLE * 2
    tspan = stage04._uint32(angle1 + CLIPANGLE)
    if tspan > two_clipangle:
        tspan = stage04._uint32(tspan - two_clipangle)
        if tspan >= span:
            state.off_frustum_reject_count += 1
            return None
        angle1 = CLIPANGLE

    tspan = stage04._uint32(CLIPANGLE - angle2)
    if tspan > two_clipangle:
        tspan = stage04._uint32(tspan - two_clipangle)
        if tspan >= span:
            state.off_frustum_reject_count += 1
            return None
        angle2 = stage04._uint32(-CLIPANGLE)

    x1 = angle_to_view_x(angle1)
    x2 = angle_to_view_x(angle2)
    if x1 == x2:
        state.zero_pixel_reject_count += 1
        return None

    line = linedefs[seg.linedef]
    frontsector = _sector_from_any(sectors[frontsector_index])
    backsector = _line_backsector(line, seg.side, sidedefs, sectors)

    if backsector is None:
        state.solid_classification_count += 1
        state.current_reason = SPAN_REASON_SOLID
        debug_clip_solid_wall_segment(state, x1, x2 - 1)
        return x1, x2 - 1

    if (
        backsector.ceiling_height <= frontsector.floor_height
        or backsector.floor_height >= frontsector.ceiling_height
    ):
        state.solid_classification_count += 1
        state.current_reason = SPAN_REASON_SOLID
        debug_clip_solid_wall_segment(state, x1, x2 - 1)
        return x1, x2 - 1

    if (
        backsector.ceiling_height != frontsector.ceiling_height
        or backsector.floor_height != frontsector.floor_height
    ):
        state.pass_classification_count += 1
        state.current_reason = SPAN_REASON_PASS
        debug_clip_pass_wall_segment(state, x1, x2 - 1)
        return x1, x2 - 1

    sidedef = _line_sidedef(line, seg.side, sidedefs)
    no_midtexture = sidedef.middle_texture in ("", "-")
    if (
        backsector.ceiling_flat == frontsector.ceiling_flat
        and backsector.floor_flat == frontsector.floor_flat
        and backsector.light_level == frontsector.light_level
        and no_midtexture
    ):
        state.empty_line_reject_count += 1
        return None

    state.pass_classification_count += 1
    state.current_reason = SPAN_REASON_PASS
    debug_clip_pass_wall_segment(state, x1, x2 - 1)
    return x1, x2 - 1


def _runtime_segs_for_loaded_map(wad_path: str | Path) -> tuple[
    LoadedMap,
    tuple[tuple[int, int], ...],
    tuple[int, ...],
    tuple[int, ...],
    tuple[DebugSeg, ...],
]:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    map_lumps = wad.map_lumps("MAP01")
    subsectors = stage02.parse_mapsubsectors(wad.read_lump(map_lumps.get("SSECTORS")))
    raw_segs = stage02.parse_mapsegs(wad.read_lump(map_lumps.get("SEGS")))

    subsector_sectors: list[int] = []
    for numlines, firstline in subsectors:
        sector_index = 0
        if numlines:
            seg = raw_segs[firstline]
            linedef = loaded.linedefs[seg[3]]
            sidenum = linedef.right_sidedef if seg[4] == 0 else linedef.left_sidedef
            sector_index = loaded.sidedefs[sidenum].sector
        subsector_sectors.append(sector_index)

    debug_segs = tuple(
        DebugSeg(v1=seg[0], v2=seg[1], linedef=seg[3], side=seg[4]) for seg in raw_segs
    )
    nodes = tuple(
        stage03.runtime_node_from_mapnode(node)
        for node in stage02.parse_mapnodes(wad.read_lump(map_lumps.get("NODES")))
    )

    return loaded, subsectors, tuple(subsector_sectors), nodes, debug_segs


def reference_seg_clip_for_pinned_map(wad_path: str | Path) -> SegClipReference:
    baseline = stage04.reference_visibility_for_pinned_map(wad_path)
    loaded, subsectors, subsector_sectors, nodes, segs = _runtime_segs_for_loaded_map(wad_path)
    state = SegClipDebugState()

    def walk(bspnum: int, depth: int) -> None:
        state.max_depth = max(state.max_depth, depth)
        if bspnum & NF_SUBSECTOR:
            subsector_id = 0 if bspnum == 0xFFFFFFFF else (bspnum & ~NF_SUBSECTOR)
            if state.visited_subsector_count == 0:
                state.first_subsector = subsector_id
            state.last_subsector = subsector_id
            state.visited_subsector_count += 1

            count, firstline = subsectors[subsector_id]
            for offset in range(count):
                seg_index = firstline + offset
                state.visited_seg_count += 1
                debug_add_line(
                    state,
                    segs[seg_index],
                    loaded.vertices,
                    loaded.linedefs,
                    loaded.sidedefs,
                    loaded.sectors,
                    frontsector_index=subsector_sectors[subsector_id],
                    seg_index=seg_index,
                )
            return

        state.visited_node_count += 1
        node = nodes[bspnum]
        side = stage03.point_on_side_fixed(VIEW_X_FIXED, VIEW_Y_FIXED, node)
        walk(node[12 + side], depth + 1)

        back_side = side ^ 1
        bbox_start = 4 + back_side * 4
        if stage04.check_bbox(node[bbox_start : bbox_start + 4], solidsegs=state.solidsegs):
            walk(node[12 + back_side], depth + 1)
        else:
            state.bbox_cull_count += 1

    root = (len(nodes) - 1) if nodes else 0xFFFFFFFF
    walk(root, 0)

    first_span = state.first_span or DebugSpan(0, 0, 0, -1)
    last_span = state.last_span or DebugSpan(0, 0, 0, -1)
    return SegClipReference(
        vertex_count=baseline.vertex_count,
        sector_count=baseline.sector_count,
        sidedef_count=baseline.sidedef_count,
        linedef_count=baseline.linedef_count,
        subsector_count=baseline.subsector_count,
        node_count=baseline.node_count,
        seg_count=baseline.seg_count,
        visited_node_count=baseline.visited_node_count,
        visited_subsector_count=baseline.visited_subsector_count,
        visited_seg_count=baseline.visited_seg_count,
        max_depth=baseline.max_depth,
        first_subsector=baseline.first_subsector,
        last_subsector=baseline.last_subsector,
        view_subsector=baseline.view_subsector,
        bbox_visited_node_count=baseline.bbox_visited_node_count,
        bbox_visited_subsector_count=baseline.bbox_visited_subsector_count,
        bbox_visited_seg_count=baseline.bbox_visited_seg_count,
        bbox_max_depth=baseline.bbox_max_depth,
        bbox_first_subsector=baseline.bbox_first_subsector,
        bbox_last_subsector=baseline.bbox_last_subsector,
        bbox_culled_node_count=baseline.bbox_culled_node_count,
        clip_visited_node_count=state.visited_node_count,
        clip_visited_subsector_count=state.visited_subsector_count,
        clip_visited_seg_count=state.visited_seg_count,
        clip_max_depth=state.max_depth,
        clip_first_subsector=state.first_subsector,
        clip_last_subsector=state.last_subsector,
        clip_bbox_cull_count=state.bbox_cull_count,
        backface_reject_count=state.backface_reject_count,
        off_frustum_reject_count=state.off_frustum_reject_count,
        zero_pixel_reject_count=state.zero_pixel_reject_count,
        solid_classification_count=state.solid_classification_count,
        pass_classification_count=state.pass_classification_count,
        empty_line_reject_count=state.empty_line_reject_count,
        stored_span_count=state.stored_span_count,
        final_solidseg_count=state.final_solidseg_count,
        span_overflow_count=state.span_overflow_count,
        clip_insert_count=state.clip_insert_count,
        clip_extend_front_count=state.clip_extend_front_count,
        clip_extend_tail_count=state.clip_extend_tail_count,
        clip_merge_count=state.clip_merge_count,
        first_span=first_span,
        last_span=last_span,
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
    x86.call_rel32(pe, "source_stage06_load_wad_live_seg_clip_debug")

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


def emit_source_stage06_load_wad_live_seg_clip_debug(pe: PE32) -> None:
    pe.label("source_stage06_load_wad_live_seg_clip_debug")
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
    x86.jne_rel32(pe, "source_stage06_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage06_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage06_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage06_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage06_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage06_close_and_return")

    pe.label("source_stage06_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage06_close_and_return")

    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage06_close_and_return")

    x86.call_rel32(pe, "source_stage06_run_live_seg_clip_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage06_close_and_return")

    x86.call_rel32(pe, "build_success_status")

    pe.label("source_stage06_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_source_stage06_run_live_seg_clip_debug(pe: PE32) -> None:
    pe.label("source_stage06_run_live_seg_clip_debug")
    stage04._emit_clear_full_traversal_counters(pe)
    stage04._emit_clear_bbox_traversal_counters(pe)
    emit_clear_clip_traversal_counters(pe)
    x86.mov_mem_abs32_imm32(pe, "traversal_done", 0)

    x86.push_mem_abs32(pe, "viewy")
    x86.push_mem_abs32(pe, "viewx")
    x86.call_rel32(pe, "render_point_in_subsector")

    stage04._emit_load_root_node(pe, "source_stage06_have_nodes", "source_stage06_have_root")
    x86.push_imm8(pe, 0)
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_bsp_node_debug")

    x86.call_rel32(pe, "render_clear_clipsegs")
    stage04._emit_load_root_node(pe, "source_stage06_bbox_have_nodes", "source_stage06_bbox_have_root")
    x86.push_imm8(pe, 0)
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_bsp_node_bbox_debug")

    x86.call_rel32(pe, "render_clear_clipsegs")
    stage04._emit_load_root_node(pe, "source_stage06_clip_have_nodes", "source_stage06_clip_have_root")
    x86.push_imm8(pe, 0)
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_bsp_node_clip_debug")
    x86.call_rel32(pe, "render_finish_clip_debug")

    x86.call_rel32(pe, "render_debug_framebuffer")
    x86.mov_mem_abs32_imm32(pe, "traversal_done", 1)
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)


def emit_clear_clip_traversal_counters(pe: PE32) -> None:
    for label in (
        "clip_visited_node_count",
        "clip_visited_subsector_count",
        "clip_visited_seg_count",
        "clip_max_traversal_depth",
        "clip_last_visible_subsector",
        "clip_culled_node_count",
        "clip_backface_reject_count",
        "clip_off_frustum_reject_count",
        "clip_zero_pixel_reject_count",
        "clip_solid_classification_count",
        "clip_pass_classification_count",
        "clip_empty_line_reject_count",
        "clip_stored_span_count",
        "clip_final_solidseg_count",
        "clip_span_overflow_count",
        "clip_insert_count",
        "clip_extend_front_count",
        "clip_extend_tail_count",
        "clip_merge_count",
        "clip_first_span_start",
        "clip_first_span_stop",
        "clip_first_span_reason",
        "clip_first_span_seg_index",
        "clip_last_span_start",
        "clip_last_span_stop",
        "clip_last_span_reason",
        "clip_last_span_seg_index",
        "clip_current_span_reason",
        "clip_curline",
        "clip_frontsector",
        "clip_backsector",
        "clip_rw_angle1",
        "clip_angle1",
        "clip_angle2",
        "clip_span",
        "clip_two_clipangle",
        "clip_x1",
        "clip_x2",
    ):
        x86.mov_mem_abs32_imm32(pe, label, 0)
    x86.mov_mem_abs32_imm32(pe, "clip_first_visible_subsector", 0xFFFFFFFF)
    x86.mov_mem_abs32_imm32(pe, "clip_current_seg_index", 0xFFFFFFFF)


def _emit_inc_abs32(pe: PE32, label: str) -> None:
    x86.mov_reg_mem_abs32(pe, "eax", label)
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, label)


def _emit_call_store_range_from_regs(pe: PE32, start_reg: str, stop_reg: str) -> None:
    x86.push_reg(pe, stop_reg)
    x86.push_reg(pe, start_reg)
    x86.call_rel32(pe, "render_store_wall_range_debug")


def _emit_call_store_range_from_eax_ecx(pe: PE32) -> None:
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_store_wall_range_debug")


def emit_render_angle_to_view_x_debug(pe: PE32) -> None:
    pe.label("render_angle_to_view_x_debug")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.add_reg_imm32(pe, "eax", ANG90)
    x86.shr_reg_imm8(pe, "eax", ANGLETOFINESHIFT)
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "ebx", "render_viewangletox_table")
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "ebx")

    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_render_finish_clip_debug(pe: PE32) -> None:
    pe.label("render_finish_clip_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "solidseg_newend")
    x86.mov_reg_abs32(pe, "ebx", "solidsegs")
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.shr_reg_imm8(pe, "eax", 3)
    x86.mov_mem_abs32_eax(pe, "clip_final_solidseg_count")
    x86.ret(pe)


def emit_render_store_wall_range_debug(pe: PE32) -> None:
    pe.label("render_store_wall_range_debug")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_reg_ebp_disp8(pe, "ebx", 12)
    x86.cmp_reg_reg(pe, "ebx", "eax")
    x86.jl_rel32(pe, "store_wall_range_done")

    x86.mov_reg_mem_abs32(pe, "ecx", "clip_stored_span_count")
    x86.cmp_reg_imm32(pe, "ecx", MAX_DEBUG_SPANS)
    x86.jb_rel32(pe, "store_wall_range_have_space")
    _emit_inc_abs32(pe, "clip_span_overflow_count")
    x86.jmp_rel32(pe, "store_wall_range_done")

    pe.label("store_wall_range_have_space")
    x86.mov_reg_reg(pe, "edx", "ecx")
    x86.shl_reg_imm8(pe, "edx", 4)
    x86.mov_reg_abs32(pe, "edi", "wall_span_debug_buffer")
    x86.add_reg_reg(pe, "edi", "edx")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.mov_mem_abs32_eax(pe, "clip_last_span_start")
    x86.mov_reg_ebp_disp8(pe, "eax", 12)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", DEBUG_SPAN_STOP)
    x86.mov_mem_abs32_eax(pe, "clip_last_span_stop")
    x86.mov_reg_mem_abs32(pe, "eax", "clip_current_span_reason")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", DEBUG_SPAN_REASON)
    x86.mov_mem_abs32_eax(pe, "clip_last_span_reason")
    x86.mov_reg_mem_abs32(pe, "eax", "clip_current_seg_index")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", DEBUG_SPAN_SEG_INDEX)
    x86.mov_mem_abs32_eax(pe, "clip_last_span_seg_index")

    x86.test_reg_reg(pe, "ecx")
    x86.jne_rel32(pe, "store_wall_range_not_first")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_mem_abs32_eax(pe, "clip_first_span_start")
    x86.mov_reg_ebp_disp8(pe, "eax", 12)
    x86.mov_mem_abs32_eax(pe, "clip_first_span_stop")
    x86.mov_reg_mem_abs32(pe, "eax", "clip_current_span_reason")
    x86.mov_mem_abs32_eax(pe, "clip_first_span_reason")
    x86.mov_reg_mem_abs32(pe, "eax", "clip_current_seg_index")
    x86.mov_mem_abs32_eax(pe, "clip_first_span_seg_index")

    pe.label("store_wall_range_not_first")
    x86.inc_reg(pe, "ecx")
    x86.mov_mem_abs32_reg(pe, "clip_stored_span_count", "ecx")

    pe.label("store_wall_range_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 8)


def emit_render_clip_pass_wall_segment(pe: PE32) -> None:
    pe.label("render_clip_pass_wall_segment")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_reg_ebp_disp8(pe, "ebx", 8)
    x86.mov_reg_ebp_disp8(pe, "edx", 12)
    x86.mov_reg_abs32(pe, "esi", "solidsegs")

    pe.label("clip_pass_find_start")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", CLIPRANGE_LAST)
    x86.mov_reg_reg(pe, "ecx", "ebx")
    x86.dec_reg(pe, "ecx")
    x86.cmp_reg_reg(pe, "eax", "ecx")
    x86.jl_rel32(pe, "clip_pass_next_start")
    x86.jmp_rel32(pe, "clip_pass_have_start")

    pe.label("clip_pass_next_start")
    x86.add_reg_imm32(pe, "esi", CLIPRANGE_RECORD_SIZE)
    x86.jmp_rel32(pe, "clip_pass_find_start")

    pe.label("clip_pass_have_start")
    x86.mov_reg_ptr_reg_disp8(pe, "ecx", "esi", CLIPRANGE_FIRST)
    x86.cmp_reg_reg(pe, "ebx", "ecx")
    x86.jl_rel32(pe, "clip_pass_first_before_start")
    x86.jmp_rel32(pe, "clip_pass_check_bottom")

    pe.label("clip_pass_first_before_start")
    x86.dec_reg(pe, "ecx")
    x86.cmp_reg_reg(pe, "edx", "ecx")
    x86.jl_rel32(pe, "clip_pass_entirely_visible")
    _emit_call_store_range_from_regs(pe, "ebx", "ecx")
    x86.jmp_rel32(pe, "clip_pass_check_bottom")

    pe.label("clip_pass_entirely_visible")
    _emit_call_store_range_from_regs(pe, "ebx", "edx")
    x86.jmp_rel32(pe, "clip_pass_done")

    pe.label("clip_pass_check_bottom")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", CLIPRANGE_LAST)
    x86.cmp_reg_reg(pe, "eax", "edx")
    x86.jl_rel32(pe, "clip_pass_scan_between")
    x86.jmp_rel32(pe, "clip_pass_done")

    pe.label("clip_pass_scan_between")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", CLIPRANGE_RECORD_SIZE + CLIPRANGE_FIRST)
    x86.dec_reg(pe, "eax")
    x86.cmp_reg_reg(pe, "edx", "eax")
    x86.jl_rel32(pe, "clip_pass_after_between")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", CLIPRANGE_LAST)
    x86.inc_reg(pe, "eax")
    x86.mov_reg_ptr_reg_disp8(pe, "ecx", "esi", CLIPRANGE_RECORD_SIZE + CLIPRANGE_FIRST)
    x86.dec_reg(pe, "ecx")
    _emit_call_store_range_from_eax_ecx(pe)
    x86.add_reg_imm32(pe, "esi", CLIPRANGE_RECORD_SIZE)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", CLIPRANGE_LAST)
    x86.cmp_reg_reg(pe, "eax", "edx")
    x86.jl_rel32(pe, "clip_pass_scan_between")
    x86.jmp_rel32(pe, "clip_pass_done")

    pe.label("clip_pass_after_between")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", CLIPRANGE_LAST)
    x86.inc_reg(pe, "eax")
    _emit_call_store_range_from_regs(pe, "eax", "edx")

    pe.label("clip_pass_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 8)


def emit_render_clip_solid_wall_segment(pe: PE32) -> None:
    pe.label("render_clip_solid_wall_segment")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_reg_ebp_disp8(pe, "ebx", 8)
    x86.mov_reg_ebp_disp8(pe, "edx", 12)
    x86.mov_reg_abs32(pe, "esi", "solidsegs")

    pe.label("clip_solid_find_start")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", CLIPRANGE_LAST)
    x86.mov_reg_reg(pe, "ecx", "ebx")
    x86.dec_reg(pe, "ecx")
    x86.cmp_reg_reg(pe, "eax", "ecx")
    x86.jl_rel32(pe, "clip_solid_next_start")
    x86.jmp_rel32(pe, "clip_solid_have_start")

    pe.label("clip_solid_next_start")
    x86.add_reg_imm32(pe, "esi", CLIPRANGE_RECORD_SIZE)
    x86.jmp_rel32(pe, "clip_solid_find_start")

    pe.label("clip_solid_have_start")
    x86.mov_reg_ptr_reg_disp8(pe, "ecx", "esi", CLIPRANGE_FIRST)
    x86.cmp_reg_reg(pe, "ebx", "ecx")
    x86.jl_rel32(pe, "clip_solid_first_before_start")
    x86.jmp_rel32(pe, "clip_solid_check_bottom")

    pe.label("clip_solid_first_before_start")
    x86.dec_reg(pe, "ecx")
    x86.cmp_reg_reg(pe, "edx", "ecx")
    x86.jl_rel32(pe, "clip_solid_insert_new")
    _emit_call_store_range_from_regs(pe, "ebx", "ecx")
    x86.mov_reg_reg(pe, "eax", "ebx")
    x86.mov_ptr_reg_eax(pe, "esi")
    _emit_inc_abs32(pe, "clip_extend_front_count")
    x86.jmp_rel32(pe, "clip_solid_check_bottom")

    pe.label("clip_solid_insert_new")
    _emit_call_store_range_from_regs(pe, "ebx", "edx")
    x86.mov_reg_mem_abs32(pe, "edi", "solidseg_newend")
    x86.mov_reg_reg(pe, "eax", "edi")
    x86.add_reg_imm32(pe, "eax", CLIPRANGE_RECORD_SIZE)
    x86.mov_mem_abs32_eax(pe, "solidseg_newend")

    pe.label("clip_solid_shift_for_insert")
    x86.cmp_reg_reg(pe, "edi", "esi")
    x86.je_rel32(pe, "clip_solid_store_insert")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", -CLIPRANGE_RECORD_SIZE)
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", -CLIPRANGE_RECORD_SIZE + CLIPRANGE_LAST)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", CLIPRANGE_LAST)
    x86.add_reg_imm32(pe, "edi", -CLIPRANGE_RECORD_SIZE)
    x86.jmp_rel32(pe, "clip_solid_shift_for_insert")

    pe.label("clip_solid_store_insert")
    x86.mov_reg_reg(pe, "eax", "ebx")
    x86.mov_ptr_reg_eax(pe, "esi")
    x86.mov_reg_reg(pe, "eax", "edx")
    x86.mov_ptr_reg_disp8_eax(pe, "esi", CLIPRANGE_LAST)
    _emit_inc_abs32(pe, "clip_insert_count")
    x86.jmp_rel32(pe, "clip_solid_done")

    pe.label("clip_solid_check_bottom")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", CLIPRANGE_LAST)
    x86.cmp_reg_reg(pe, "eax", "edx")
    x86.jl_rel32(pe, "clip_solid_scan_between")
    x86.jmp_rel32(pe, "clip_solid_done")

    pe.label("clip_solid_scan_between")
    x86.mov_reg_reg(pe, "edi", "esi")

    pe.label("clip_solid_between_loop")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", CLIPRANGE_RECORD_SIZE + CLIPRANGE_FIRST)
    x86.dec_reg(pe, "eax")
    x86.cmp_reg_reg(pe, "edx", "eax")
    x86.jl_rel32(pe, "clip_solid_after_between")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", CLIPRANGE_LAST)
    x86.inc_reg(pe, "eax")
    x86.mov_reg_ptr_reg_disp8(pe, "ecx", "edi", CLIPRANGE_RECORD_SIZE + CLIPRANGE_FIRST)
    x86.dec_reg(pe, "ecx")
    _emit_call_store_range_from_eax_ecx(pe)
    x86.add_reg_imm32(pe, "edi", CLIPRANGE_RECORD_SIZE)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", CLIPRANGE_LAST)
    x86.cmp_reg_reg(pe, "eax", "edx")
    x86.jl_rel32(pe, "clip_solid_between_loop")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", CLIPRANGE_LAST)
    x86.mov_ptr_reg_disp8_eax(pe, "esi", CLIPRANGE_LAST)
    x86.jmp_rel32(pe, "clip_solid_crunch")

    pe.label("clip_solid_after_between")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", CLIPRANGE_LAST)
    x86.inc_reg(pe, "eax")
    _emit_call_store_range_from_regs(pe, "eax", "edx")
    x86.mov_reg_reg(pe, "eax", "edx")
    x86.mov_ptr_reg_disp8_eax(pe, "esi", CLIPRANGE_LAST)

    pe.label("clip_solid_crunch")
    x86.cmp_reg_reg(pe, "edi", "esi")
    x86.jne_rel32(pe, "clip_solid_merge_ranges")
    _emit_inc_abs32(pe, "clip_extend_tail_count")
    x86.jmp_rel32(pe, "clip_solid_done")

    pe.label("clip_solid_merge_ranges")
    _emit_inc_abs32(pe, "clip_merge_count")
    x86.mov_reg_reg(pe, "ecx", "esi")
    x86.add_reg_imm32(pe, "ecx", CLIPRANGE_RECORD_SIZE)
    x86.add_reg_imm32(pe, "edi", CLIPRANGE_RECORD_SIZE)

    pe.label("clip_solid_compact_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "solidseg_newend")
    x86.cmp_reg_reg(pe, "edi", "eax")
    x86.jae_rel32(pe, "clip_solid_compact_done")
    x86.mov_reg_ptr_reg(pe, "eax", "edi")
    x86.mov_ptr_reg_eax(pe, "ecx")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", CLIPRANGE_LAST)
    x86.mov_ptr_reg_disp8_eax(pe, "ecx", CLIPRANGE_LAST)
    x86.add_reg_imm32(pe, "edi", CLIPRANGE_RECORD_SIZE)
    x86.add_reg_imm32(pe, "ecx", CLIPRANGE_RECORD_SIZE)
    x86.jmp_rel32(pe, "clip_solid_compact_loop")

    pe.label("clip_solid_compact_done")
    x86.mov_mem_abs32_reg(pe, "solidseg_newend", "ecx")

    pe.label("clip_solid_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 8)


def emit_render_add_line_debug(pe: PE32) -> None:
    pe.label("render_add_line_debug")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_reg_ebp_disp8(pe, "esi", 8)
    x86.mov_mem_abs32_reg(pe, "clip_curline", "esi")

    x86.mov_reg_ptr_reg_disp8(pe, "edi", "esi", stage02.SEG_V1)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", 4)
    x86.push_reg(pe, "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "edi")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_point_to_angle")
    x86.mov_mem_abs32_eax(pe, "clip_angle1")
    x86.mov_mem_abs32_eax(pe, "clip_rw_angle1")

    x86.mov_reg_mem_abs32(pe, "esi", "clip_curline")
    x86.mov_reg_ptr_reg_disp8(pe, "edi", "esi", stage02.SEG_V2)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", 4)
    x86.push_reg(pe, "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "edi")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_point_to_angle")
    x86.mov_mem_abs32_eax(pe, "clip_angle2")

    x86.mov_reg_mem_abs32(pe, "eax", "clip_angle1")
    x86.sub_reg_mem_abs32(pe, "eax", "clip_angle2")
    x86.mov_mem_abs32_eax(pe, "clip_span")
    x86.cmp_eax_imm32(pe, ANG180)
    x86.jb_rel32(pe, "add_line_front_facing")
    _emit_inc_abs32(pe, "clip_backface_reject_count")
    x86.jmp_rel32(pe, "add_line_done")

    pe.label("add_line_front_facing")
    x86.mov_reg_mem_abs32(pe, "eax", "clip_angle1")
    x86.sub_reg_mem_abs32(pe, "eax", "viewangle")
    x86.mov_mem_abs32_eax(pe, "clip_angle1")
    x86.mov_reg_mem_abs32(pe, "eax", "clip_angle2")
    x86.sub_reg_mem_abs32(pe, "eax", "viewangle")
    x86.mov_mem_abs32_eax(pe, "clip_angle2")

    x86.mov_reg_mem_abs32(pe, "ebx", "clipangle")
    x86.add_reg_reg(pe, "ebx", "ebx")
    x86.mov_mem_abs32_reg(pe, "clip_two_clipangle", "ebx")

    x86.mov_reg_mem_abs32(pe, "eax", "clip_angle1")
    x86.add_reg_mem_abs32(pe, "eax", "clipangle")
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jbe_rel32(pe, "add_line_left_clip_done")
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.cmp_reg_mem_abs32(pe, "eax", "clip_span")
    x86.jb_rel32(pe, "add_line_left_part_visible")
    _emit_inc_abs32(pe, "clip_off_frustum_reject_count")
    x86.jmp_rel32(pe, "add_line_done")

    pe.label("add_line_left_part_visible")
    x86.mov_reg_mem_abs32(pe, "eax", "clipangle")
    x86.mov_mem_abs32_eax(pe, "clip_angle1")

    pe.label("add_line_left_clip_done")
    x86.mov_reg_mem_abs32(pe, "eax", "clipangle")
    x86.sub_reg_mem_abs32(pe, "eax", "clip_angle2")
    x86.mov_reg_mem_abs32(pe, "ebx", "clip_two_clipangle")
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jbe_rel32(pe, "add_line_right_clip_done")
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.cmp_reg_mem_abs32(pe, "eax", "clip_span")
    x86.jb_rel32(pe, "add_line_right_part_visible")
    _emit_inc_abs32(pe, "clip_off_frustum_reject_count")
    x86.jmp_rel32(pe, "add_line_done")

    pe.label("add_line_right_part_visible")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.sub_reg_mem_abs32(pe, "eax", "clipangle")
    x86.mov_mem_abs32_eax(pe, "clip_angle2")

    pe.label("add_line_right_clip_done")
    x86.push_mem_abs32(pe, "clip_angle1")
    x86.call_rel32(pe, "render_angle_to_view_x_debug")
    x86.mov_mem_abs32_eax(pe, "clip_x1")
    x86.push_mem_abs32(pe, "clip_angle2")
    x86.call_rel32(pe, "render_angle_to_view_x_debug")
    x86.mov_mem_abs32_eax(pe, "clip_x2")
    x86.cmp_reg_mem_abs32(pe, "eax", "clip_x1")
    x86.jne_rel32(pe, "add_line_has_pixel_span")
    _emit_inc_abs32(pe, "clip_zero_pixel_reject_count")
    x86.jmp_rel32(pe, "add_line_done")

    pe.label("add_line_has_pixel_span")
    x86.mov_reg_mem_abs32(pe, "esi", "clip_curline")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage02.SEG_BACKSECTOR)
    x86.mov_mem_abs32_eax(pe, "clip_backsector")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "add_line_clip_solid")

    x86.mov_reg_reg(pe, "edi", "eax")
    x86.mov_reg_mem_abs32(pe, "esi", "clip_frontsector")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", SECTOR_CEILINGHEIGHT)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", SECTOR_FLOORHEIGHT)
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jl_rel32(pe, "add_line_clip_solid")
    x86.je_rel32(pe, "add_line_clip_solid")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", SECTOR_FLOORHEIGHT)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", SECTOR_CEILINGHEIGHT)
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jl_rel32(pe, "add_line_not_closed_door")
    x86.jmp_rel32(pe, "add_line_clip_solid")

    pe.label("add_line_not_closed_door")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", SECTOR_CEILINGHEIGHT)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", SECTOR_CEILINGHEIGHT)
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jne_rel32(pe, "add_line_clip_pass")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", SECTOR_FLOORHEIGHT)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", SECTOR_FLOORHEIGHT)
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jne_rel32(pe, "add_line_clip_pass")

    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", SECTOR_CEILINGPIC0)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", SECTOR_CEILINGPIC0)
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jne_rel32(pe, "add_line_clip_pass")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", SECTOR_CEILINGPIC1)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", SECTOR_CEILINGPIC1)
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jne_rel32(pe, "add_line_clip_pass")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", SECTOR_FLOORPIC0)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", SECTOR_FLOORPIC0)
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jne_rel32(pe, "add_line_clip_pass")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", SECTOR_FLOORPIC1)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", SECTOR_FLOORPIC1)
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jne_rel32(pe, "add_line_clip_pass")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", SECTOR_LIGHTLEVEL)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", SECTOR_LIGHTLEVEL)
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jne_rel32(pe, "add_line_clip_pass")

    x86.mov_reg_mem_abs32(pe, "esi", "clip_curline")
    x86.mov_reg_ptr_reg_disp8(pe, "esi", "esi", stage02.SEG_SIDEDEF)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", SIDE_MIDTEXTURE0)
    x86.cmp_eax_imm32(pe, 0x2D)
    x86.jne_rel32(pe, "add_line_clip_pass")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", SIDE_MIDTEXTURE1)
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "add_line_clip_pass")
    _emit_inc_abs32(pe, "clip_empty_line_reject_count")
    x86.jmp_rel32(pe, "add_line_done")

    pe.label("add_line_clip_pass")
    _emit_inc_abs32(pe, "clip_pass_classification_count")
    x86.mov_mem_abs32_imm32(pe, "clip_current_span_reason", SPAN_REASON_PASS)
    x86.mov_reg_mem_abs32(pe, "eax", "clip_x2")
    x86.dec_reg(pe, "eax")
    x86.push_reg(pe, "eax")
    x86.push_mem_abs32(pe, "clip_x1")
    x86.call_rel32(pe, "render_clip_pass_wall_segment")
    x86.jmp_rel32(pe, "add_line_done")

    pe.label("add_line_clip_solid")
    _emit_inc_abs32(pe, "clip_solid_classification_count")
    x86.mov_mem_abs32_imm32(pe, "clip_current_span_reason", SPAN_REASON_SOLID)
    x86.mov_reg_mem_abs32(pe, "eax", "clip_x2")
    x86.dec_reg(pe, "eax")
    x86.push_reg(pe, "eax")
    x86.push_mem_abs32(pe, "clip_x1")
    x86.call_rel32(pe, "render_clip_solid_wall_segment")

    pe.label("add_line_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_render_debug_subsector_clip(pe: PE32) -> None:
    pe.label("render_debug_subsector_clip")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.cmp_reg_mem_abs32(pe, "eax", "subsector_count")
    x86.jae_rel32(pe, "debug_subsector_clip_done")

    x86.mov_reg_mem_abs32(pe, "ebx", "clip_visited_subsector_count")
    x86.test_reg_reg(pe, "ebx")
    x86.jne_rel32(pe, "debug_subsector_clip_not_first")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_mem_abs32_eax(pe, "clip_first_visible_subsector")

    pe.label("debug_subsector_clip_not_first")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_mem_abs32_eax(pe, "clip_last_visible_subsector")
    _emit_inc_abs32(pe, "clip_visited_subsector_count")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.shl_reg_imm8(pe, "eax", 3)
    x86.mov_reg_abs32(pe, "esi", "subsectors_buffer")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "esi")
    x86.mov_mem_abs32_eax(pe, "clip_frontsector")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "ecx", "esi", stage02.SUBSECTOR_NUMLINES)
    x86.movzx_reg_word_ptr_reg_disp8(pe, "edx", "esi", stage02.SUBSECTOR_FIRSTLINE)

    pe.label("debug_subsector_clip_seg_loop")
    x86.test_reg_reg(pe, "ecx")
    x86.je_rel32(pe, "debug_subsector_clip_done")
    x86.mov_mem_abs32_reg(pe, "clip_current_seg_index", "edx")
    _emit_inc_abs32(pe, "clip_visited_seg_count")
    x86.mov_reg_reg(pe, "eax", "edx")
    x86.shl_reg_imm8(pe, "eax", 5)
    x86.mov_reg_abs32(pe, "edi", "segs_buffer")
    x86.add_reg_reg(pe, "edi", "eax")
    x86.push_reg(pe, "edi")
    x86.call_rel32(pe, "render_add_line_debug")
    x86.inc_reg(pe, "edx")
    x86.dec_reg(pe, "ecx")
    x86.jmp_rel32(pe, "debug_subsector_clip_seg_loop")

    pe.label("debug_subsector_clip_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_render_bsp_node_clip_debug(pe: PE32) -> None:
    pe.label("render_bsp_node_clip_debug")
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
    x86.jne_rel32(pe, "bsp_node_clip_is_subsector")

    _emit_update_clip_max_depth_from_arg(pe, "node")
    _emit_inc_abs32(pe, "clip_visited_node_count")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.cmp_reg_mem_abs32(pe, "eax", "node_count")
    x86.jae_rel32(pe, "bsp_node_clip_done")
    x86.imul_reg_reg_imm32(pe, "ebx", "eax", stage02.NODE_T_RECORD_SIZE)
    x86.mov_reg_abs32(pe, "esi", "nodes_buffer")
    x86.add_reg_reg(pe, "esi", "ebx")

    x86.push_reg(pe, "esi")
    x86.push_mem_abs32(pe, "viewy")
    x86.push_mem_abs32(pe, "viewx")
    x86.call_rel32(pe, "render_point_on_side")
    x86.mov_reg_reg(pe, "ebx", "eax")

    x86.test_reg_reg(pe, "ebx")
    x86.jne_rel32(pe, "bsp_node_clip_front_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD0)
    x86.jmp_rel32(pe, "bsp_node_clip_have_front_child")

    pe.label("bsp_node_clip_front_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD1)

    pe.label("bsp_node_clip_have_front_child")
    _emit_recurse_bsp_child_clip(pe)

    x86.test_reg_reg(pe, "ebx")
    x86.jne_rel32(pe, "bsp_node_clip_back_bbox_side_one")
    x86.mov_reg_reg(pe, "edi", "esi")
    x86.add_reg_imm32(pe, "edi", stage02.NODE_BBOX + 16)
    x86.jmp_rel32(pe, "bsp_node_clip_have_back_bbox")

    pe.label("bsp_node_clip_back_bbox_side_one")
    x86.mov_reg_reg(pe, "edi", "esi")
    x86.add_reg_imm32(pe, "edi", stage02.NODE_BBOX)

    pe.label("bsp_node_clip_have_back_bbox")
    x86.push_reg(pe, "edi")
    x86.call_rel32(pe, "render_check_bbox")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "bsp_node_clip_back_visible")
    _emit_inc_abs32(pe, "clip_culled_node_count")
    x86.jmp_rel32(pe, "bsp_node_clip_done")

    pe.label("bsp_node_clip_back_visible")
    x86.test_reg_reg(pe, "ebx")
    x86.jne_rel32(pe, "bsp_node_clip_back_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD1)
    x86.jmp_rel32(pe, "bsp_node_clip_have_back_child")

    pe.label("bsp_node_clip_back_side_one")
    x86.movzx_reg_word_ptr_reg_disp8(pe, "eax", "esi", stage02.NODE_CHILD0)

    pe.label("bsp_node_clip_have_back_child")
    _emit_recurse_bsp_child_clip(pe)
    x86.jmp_rel32(pe, "bsp_node_clip_done")

    pe.label("bsp_node_clip_is_subsector")
    _emit_update_clip_max_depth_from_arg(pe, "subsector")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.jne_rel32(pe, "bsp_node_clip_normal_subsector")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.jmp_rel32(pe, "bsp_node_clip_call_subsector")

    pe.label("bsp_node_clip_normal_subsector")
    x86.and_reg_imm32(pe, "eax", ~NF_SUBSECTOR)

    pe.label("bsp_node_clip_call_subsector")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_debug_subsector_clip")

    pe.label("bsp_node_clip_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 8)


def _emit_update_clip_max_depth_from_arg(pe: PE32, suffix: str) -> None:
    done_label = f"bsp_node_clip_depth_not_larger_{suffix}"
    x86.mov_eax_ebp_disp8(pe, 12)
    x86.cmp_reg_mem_abs32(pe, "eax", "clip_max_traversal_depth")
    x86.jbe_rel32(pe, done_label)
    x86.mov_mem_abs32_eax(pe, "clip_max_traversal_depth")
    pe.label(done_label)


def _emit_recurse_bsp_child_clip(pe: PE32) -> None:
    x86.mov_reg_ebp_disp8(pe, "ecx", 12)
    x86.inc_reg(pe, "ecx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_bsp_node_clip_debug")


def emit_build_success_status(pe: PE32) -> None:
    pe.label("build_success_status")
    x86.mov_reg_abs32(pe, "edi", "status_success_buffer")

    stage01.append_c_string_label(pe, "status_stage06_success_header")
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
    stage01.append_u32_label(pe, "status_visited_nodes_prefix", "visited_node_count")
    stage01.append_u32_label(pe, "status_visited_subsectors_prefix", "visited_subsector_count")
    stage01.append_u32_label(pe, "status_visited_segs_prefix", "visited_seg_count")
    stage01.append_u32_label(pe, "status_bbox_nodes_prefix", "bbox_visible_node_count")
    stage01.append_u32_label(pe, "status_bbox_subsectors_prefix", "bbox_visible_subsector_count")
    stage01.append_u32_label(pe, "status_bbox_segs_prefix", "bbox_visible_seg_count")
    stage01.append_u32_label(pe, "status_bbox_cull_prefix", "bbox_culled_node_count")
    stage01.append_u32_label(pe, "status_clip_nodes_prefix", "clip_visited_node_count")
    stage01.append_u32_label(pe, "status_clip_subsectors_prefix", "clip_visited_subsector_count")
    stage01.append_u32_label(pe, "status_clip_segs_prefix", "clip_visited_seg_count")
    stage01.append_u32_label(pe, "status_clip_cull_prefix", "clip_culled_node_count")
    stage01.append_u32_label(pe, "status_clip_backface_prefix", "clip_backface_reject_count")
    stage01.append_u32_label(pe, "status_clip_off_prefix", "clip_off_frustum_reject_count")
    stage01.append_u32_label(pe, "status_clip_zero_prefix", "clip_zero_pixel_reject_count")
    stage01.append_u32_label(pe, "status_clip_solid_prefix", "clip_solid_classification_count")
    stage01.append_u32_label(pe, "status_clip_pass_prefix", "clip_pass_classification_count")
    stage01.append_u32_label(pe, "status_clip_span_prefix", "clip_stored_span_count")
    stage01.append_u32_label(pe, "status_clip_final_solidsegs_prefix", "clip_final_solidseg_count")
    stage01.append_u32_label(pe, "status_clip_first_span_prefix", "clip_first_span_start")
    stage01.append_c_string_label(pe, "status_span_dash")
    stage01.append_u32_label(pe, "status_empty_prefix", "clip_first_span_stop")
    stage01.append_u32_label(pe, "status_clip_first_span_seg_prefix", "clip_first_span_seg_index")
    stage01.append_u32_label(pe, "status_clip_last_span_prefix", "clip_last_span_start")
    stage01.append_c_string_label(pe, "status_span_dash")
    stage01.append_u32_label(pe, "status_empty_prefix", "clip_last_span_stop")
    stage01.append_u32_label(pe, "status_clip_last_span_seg_prefix", "clip_last_span_seg_index")
    stage01.append_c_string_label(pe, "status_stage06_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    x86.mov_reg_abs32(pe, "edi", "title_status_buffer")
    stage01.append_c_string_label(pe, "title_success_prefix")
    stage01.append_u32_label(pe, "title_vn_prefix", "visited_node_count")
    stage01.append_u32_label(pe, "title_vss_prefix", "visited_subsector_count")
    stage01.append_u32_label(pe, "title_vseg_prefix", "visited_seg_count")
    stage01.append_u32_label(pe, "title_bvn_prefix", "bbox_visible_node_count")
    stage01.append_u32_label(pe, "title_bvss_prefix", "bbox_visible_subsector_count")
    stage01.append_u32_label(pe, "title_bvseg_prefix", "bbox_visible_seg_count")
    stage01.append_u32_label(pe, "title_cull_prefix", "bbox_culled_node_count")
    stage01.append_u32_label(pe, "title_clip_nodes_prefix", "clip_visited_node_count")
    stage01.append_u32_label(pe, "title_clip_subsectors_prefix", "clip_visited_subsector_count")
    stage01.append_u32_label(pe, "title_clip_segs_prefix", "clip_visited_seg_count")
    stage01.append_u32_label(pe, "title_clip_cull_prefix", "clip_culled_node_count")
    stage01.append_u32_label(pe, "title_clip_backface_prefix", "clip_backface_reject_count")
    stage01.append_u32_label(pe, "title_clip_off_prefix", "clip_off_frustum_reject_count")
    stage01.append_u32_label(pe, "title_clip_zero_prefix", "clip_zero_pixel_reject_count")
    stage01.append_u32_label(pe, "title_clip_solid_prefix", "clip_solid_classification_count")
    stage01.append_u32_label(pe, "title_clip_pass_prefix", "clip_pass_classification_count")
    stage01.append_u32_label(pe, "title_clip_span_prefix", "clip_stored_span_count")
    stage01.append_u32_label(pe, "title_clip_final_solidsegs_prefix", "clip_final_solidseg_count")
    stage01.append_u32_label(pe, "title_clip_first_span_prefix", "clip_first_span_start")
    stage01.append_c_string_label(pe, "status_span_dash")
    stage01.append_u32_label(pe, "status_empty_prefix", "clip_first_span_stop")
    stage01.append_u32_label(pe, "title_clip_first_span_seg_prefix", "clip_first_span_seg_index")
    stage01.append_u32_label(pe, "title_clip_last_span_prefix", "clip_last_span_start")
    stage01.append_c_string_label(pe, "status_span_dash")
    stage01.append_u32_label(pe, "status_empty_prefix", "clip_last_span_stop")
    stage01.append_u32_label(pe, "title_clip_last_span_seg_prefix", "clip_last_span_seg_index")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage06_data(pe: PE32) -> None:
    pe.align_section(4)
    pe.label("clip_traversal_debug_state")
    pe.label("clip_visited_node_count")
    pe.emit_u32(0)
    pe.label("clip_visited_subsector_count")
    pe.emit_u32(0)
    pe.label("clip_visited_seg_count")
    pe.emit_u32(0)
    pe.label("clip_max_traversal_depth")
    pe.emit_u32(0)
    pe.label("clip_first_visible_subsector")
    pe.emit_u32(0xFFFFFFFF)
    pe.label("clip_last_visible_subsector")
    pe.emit_u32(0)
    pe.label("clip_culled_node_count")
    pe.emit_u32(0)
    pe.label("clip_backface_reject_count")
    pe.emit_u32(0)
    pe.label("clip_off_frustum_reject_count")
    pe.emit_u32(0)
    pe.label("clip_zero_pixel_reject_count")
    pe.emit_u32(0)
    pe.label("clip_solid_classification_count")
    pe.emit_u32(0)
    pe.label("clip_pass_classification_count")
    pe.emit_u32(0)
    pe.label("clip_empty_line_reject_count")
    pe.emit_u32(0)
    pe.label("clip_stored_span_count")
    pe.emit_u32(0)
    pe.label("clip_final_solidseg_count")
    pe.emit_u32(0)
    pe.label("clip_span_overflow_count")
    pe.emit_u32(0)
    pe.label("clip_insert_count")
    pe.emit_u32(0)
    pe.label("clip_extend_front_count")
    pe.emit_u32(0)
    pe.label("clip_extend_tail_count")
    pe.emit_u32(0)
    pe.label("clip_merge_count")
    pe.emit_u32(0)

    pe.label("clip_first_span_start")
    pe.emit_u32(0)
    pe.label("clip_first_span_stop")
    pe.emit_u32(0)
    pe.label("clip_first_span_reason")
    pe.emit_u32(0)
    pe.label("clip_first_span_seg_index")
    pe.emit_u32(0)
    pe.label("clip_last_span_start")
    pe.emit_u32(0)
    pe.label("clip_last_span_stop")
    pe.emit_u32(0)
    pe.label("clip_last_span_reason")
    pe.emit_u32(0)
    pe.label("clip_last_span_seg_index")
    pe.emit_u32(0)

    pe.label("clip_current_seg_index")
    pe.emit_u32(0xFFFFFFFF)
    pe.label("clip_current_span_reason")
    pe.emit_u32(0)
    pe.label("clip_curline")
    pe.emit_u32(0)
    pe.label("clip_frontsector")
    pe.emit_u32(0)
    pe.label("clip_backsector")
    pe.emit_u32(0)
    pe.label("clip_rw_angle1")
    pe.emit_u32(0)
    pe.label("clip_angle1")
    pe.emit_u32(0)
    pe.label("clip_angle2")
    pe.emit_u32(0)
    pe.label("clip_span")
    pe.emit_u32(0)
    pe.label("clip_two_clipangle")
    pe.emit_u32(0)
    pe.label("clip_x1")
    pe.emit_u32(0)
    pe.label("clip_x2")
    pe.emit_u32(0)

    pe.align_section(1)
    pe.label("status_stage06_success_header")
    x86.emit_asciiz(pe, "source_stage06_live_seg_clip_debug\r\nLive mutable seg clipping debug OK\r\n")
    pe.label("status_clip_nodes_prefix")
    x86.emit_asciiz(pe, "\r\nMutable R_RenderBSPNode visited nodes: ")
    pe.label("status_clip_subsectors_prefix")
    x86.emit_asciiz(pe, "\r\nMutable R_Subsector visited subsectors: ")
    pe.label("status_clip_segs_prefix")
    x86.emit_asciiz(pe, "\r\nMutable R_AddLine visited segs: ")
    pe.label("status_clip_cull_prefix")
    x86.emit_asciiz(pe, "\r\nMutable R_CheckBBox culled back children: ")
    pe.label("status_clip_backface_prefix")
    x86.emit_asciiz(pe, "\r\nR_AddLine backface rejects: ")
    pe.label("status_clip_off_prefix")
    x86.emit_asciiz(pe, "\r\nR_AddLine off-frustum rejects: ")
    pe.label("status_clip_zero_prefix")
    x86.emit_asciiz(pe, "\r\nR_AddLine zero-pixel rejects: ")
    pe.label("status_clip_solid_prefix")
    x86.emit_asciiz(pe, "\r\nR_ClipSolidWallSegment calls: ")
    pe.label("status_clip_pass_prefix")
    x86.emit_asciiz(pe, "\r\nR_ClipPassWallSegment calls: ")
    pe.label("status_clip_span_prefix")
    x86.emit_asciiz(pe, "\r\nDebug R_StoreWallRange spans: ")
    pe.label("status_clip_final_solidsegs_prefix")
    x86.emit_asciiz(pe, "\r\nFinal mutable solidsegs count: ")
    pe.label("status_clip_first_span_prefix")
    x86.emit_asciiz(pe, "\r\nFirst stored span columns: ")
    pe.label("status_clip_first_span_seg_prefix")
    x86.emit_asciiz(pe, " seg=")
    pe.label("status_clip_last_span_prefix")
    x86.emit_asciiz(pe, "\r\nLast stored span columns: ")
    pe.label("status_clip_last_span_seg_prefix")
    x86.emit_asciiz(pe, " seg=")
    pe.label("status_span_dash")
    x86.emit_asciiz(pe, "-")
    pe.label("status_empty_prefix")
    x86.emit_asciiz(pe, "")
    pe.label("status_stage06_note")
    x86.emit_asciiz(
        pe,
        "\r\nMutable R_AddLine/R_ClipSolidWallSegment/R_ClipPassWallSegment "
        "run live in emitted x86; stage06 stops before projection/textures/planes/sprites.\r\n",
    )

    pe.label("title_clip_nodes_prefix")
    x86.emit_asciiz(pe, " CLN=")
    pe.label("title_clip_subsectors_prefix")
    x86.emit_asciiz(pe, " CLSS=")
    pe.label("title_clip_segs_prefix")
    x86.emit_asciiz(pe, " CLSEG=")
    pe.label("title_clip_cull_prefix")
    x86.emit_asciiz(pe, " CLCULL=")
    pe.label("title_clip_backface_prefix")
    x86.emit_asciiz(pe, " BF=")
    pe.label("title_clip_off_prefix")
    x86.emit_asciiz(pe, " OFF=")
    pe.label("title_clip_zero_prefix")
    x86.emit_asciiz(pe, " ZPX=")
    pe.label("title_clip_solid_prefix")
    x86.emit_asciiz(pe, " SOL=")
    pe.label("title_clip_pass_prefix")
    x86.emit_asciiz(pe, " PASS=")
    pe.label("title_clip_span_prefix")
    x86.emit_asciiz(pe, " SPAN=")
    pe.label("title_clip_final_solidsegs_prefix")
    x86.emit_asciiz(pe, " NSEGS=")
    pe.label("title_clip_first_span_prefix")
    x86.emit_asciiz(pe, " FSPAN=")
    pe.label("title_clip_first_span_seg_prefix")
    x86.emit_asciiz(pe, " FSEG=")
    pe.label("title_clip_last_span_prefix")
    x86.emit_asciiz(pe, " LSPAN=")
    pe.label("title_clip_last_span_seg_prefix")
    x86.emit_asciiz(pe, " LSEG=")

    pe.align_section(4)
    pe.label("wall_span_debug_buffer")
    pe.emit_zeros(DEBUG_SPAN_BUFFER_BYTES)


def build_source_stage06_live_seg_clip_debug_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage06_load_wad_live_seg_clip_debug(pe)
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
    emit_source_stage06_run_live_seg_clip_debug(pe)
    stage03.emit_render_fixed_mul(pe)
    stage03.emit_render_point_on_side(pe)
    stage03.emit_render_point_in_subsector(pe)
    stage03.emit_render_debug_subsector(pe)
    stage03.emit_render_check_bbox_accept_all(pe)
    stage03.emit_render_bsp_node_debug(pe)
    stage04.emit_render_slope_div(pe)
    stage04.emit_render_point_to_angle(pe)
    stage04.emit_render_clear_clipsegs(pe)
    stage04.emit_render_check_bbox(pe)
    stage04.emit_render_debug_subsector_bbox(pe)
    stage04.emit_render_bsp_node_bbox_debug(pe)
    emit_render_angle_to_view_x_debug(pe)
    emit_render_store_wall_range_debug(pe)
    emit_render_clip_solid_wall_segment(pe)
    emit_render_clip_pass_wall_segment(pe)
    emit_render_add_line_debug(pe)
    emit_render_debug_subsector_clip(pe)
    emit_render_bsp_node_clip_debug(pe)
    emit_render_finish_clip_debug(pe)
    stage04.emit_render_debug_framebuffer(pe)
    stage03.emit_clear_framebuffer(pe)
    stage03.emit_render_error_pattern(pe)
    stage03.emit_transform_point_to_screen(pe)
    stage03.emit_draw_all_linedefs(pe)
    stage03.emit_draw_visited_segs(pe)
    stage04.emit_draw_bbox_visible_segs(pe)
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
    stage04.emit_stage04_data(pe)
    emit_stage06_data(pe)
    return pe.build("entry")


def write_source_stage06_live_seg_clip_debug_exe(path: str | Path) -> bytes:
    image = build_source_stage06_live_seg_clip_debug_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the source-guided PE32 x86 live wall-span clipping debug executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/source_stage06_live_seg_clip_debug.exe",
        help="path to write, default: build/source_stage06_live_seg_clip_debug.exe",
    )
    args = parser.parse_args()
    write_source_stage06_live_seg_clip_debug_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
