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
WINDOW_CLASS_NAME = "InferenceDoomSourceStage07WallProjectionDebug"
WINDOW_TITLE = "Inference Doom S07 Wall Projection"
WAD_PATH = stage04.WAD_PATH

FRACBITS = stage04.FRACBITS
FRACUNIT = stage04.FRACUNIT
NF_SUBSECTOR = stage04.NF_SUBSECTOR

VIEW_X_FIXED = stage04.VIEW_X_FIXED
VIEW_Y_FIXED = stage04.VIEW_Y_FIXED
VIEW_ANGLE = stage04.VIEW_ANGLE

ANG90 = stage04.ANG90
ANG180 = stage04.ANG180
ANG270 = stage04.ANG270
ANGLETOFINESHIFT = stage04.ANGLETOFINESHIFT
FINEANGLES = stage04.FINEANGLES
VIEWWIDTH = stage04.VIEWWIDTH
CLIPANGLE = stage04.CLIPANGLE
PROJECTION = stage04.PROJECTION
SLOPEBITS = 11
DBITS = FRACBITS - SLOPEBITS
FINEMASK = FINEANGLES - 1
VIEWHEIGHT = 41 * FRACUNIT
MAXSCALE = 64 * FRACUNIT
MINSCALE = 256

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

PROJECTED_SPAN_X1 = 0
PROJECTED_SPAN_X2 = 4
PROJECTED_SPAN_SEG_INDEX = 8
PROJECTED_SPAN_RW_NORMALANGLE = 12
PROJECTED_SPAN_RW_DISTANCE = 16
PROJECTED_SPAN_SCALE1 = 20
PROJECTED_SPAN_SCALE2 = 24
PROJECTED_SPAN_SCALESTEP = 28
PROJECTED_SPAN_RECORD_SIZE = 32
MAX_PROJECTED_SPANS = MAX_DEBUG_SPANS
PROJECTED_SPAN_BUFFER_BYTES = MAX_PROJECTED_SPANS * PROJECTED_SPAN_RECORD_SIZE

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

FINESINE = stage04._parse_table("finesine", FINEANGLES * 5 // 4)
FINECOSINE = FINESINE[FINEANGLES // 4 :]

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
    (
        "reference/chocolate-doom/src/tables.c",
        "finesine / finecosine",
        "render_fine_trig_tables",
    ),
    (
        "reference/chocolate-doom/src/doom/p_local.h / reference/chocolate-doom/src/doom/p_user.c",
        "VIEWHEIGHT / P_CalcHeight viewz path",
        "render_setup_frame_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_SetupFrame",
        "render_setup_frame_debug",
    ),
    (
        "reference/chocolate-doom/src/m_fixed.c",
        "FixedDiv",
        "render_fixed_div",
    ),
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_PointToDist",
        "render_point_to_dist",
    ),
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_ScaleFromGlobalAngle",
        "render_scale_from_global_angle",
    ),
    (
        "reference/chocolate-doom/src/doom/r_segs.c",
        "R_StoreWallRange distance/scale prefix",
        "render_store_wall_range_projected_debug",
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


@dataclass(frozen=True)
class ProjectedSpan:
    x1: int
    x2: int
    seg_index: int
    rw_normalangle: int
    rw_distance: int
    scale1: int
    scale2: int
    scalestep: int


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
    spans: tuple[DebugSpan, ...] = ()


@dataclass(frozen=True)
class WallProjectionReference:
    clip: SegClipReference
    viewz: int
    viewcos: int
    viewsin: int
    validcount: int
    framecount: int
    projected_spans: tuple[ProjectedSpan, ...]
    min_distance: int
    max_distance: int
    min_scale: int
    max_scale: int
    first_projected_span: ProjectedSpan
    last_projected_span: ProjectedSpan


def angle_to_view_x(angle: int) -> int:
    index = stage04._uint32(angle + ANG90) >> ANGLETOFINESHIFT
    return stage04.VIEWANGLETOX[index]


def fixed_div(a: int, b: int) -> int:
    return stage04.fixed_div(a, b)


def fixed_mul(a: int, b: int) -> int:
    return stage04.fixed_mul(a, b)


def fine_index(angle: int) -> int:
    return stage04._uint32(angle) >> ANGLETOFINESHIFT


def point_to_dist(
    x: int,
    y: int,
    *,
    viewx: int = VIEW_X_FIXED,
    viewy: int = VIEW_Y_FIXED,
) -> int:
    dx = abs(stage04._int32(x - viewx))
    dy = abs(stage04._int32(y - viewy))

    if dy > dx:
        dx, dy = dy, dx

    frac = fixed_div(dy, dx) if dx != 0 else 0
    angle = fine_index(stage04._uint32(stage04.TANTOANGLE[stage04._uint32(frac) >> DBITS] + ANG90))
    return fixed_div(dx, FINESINE[angle])


def scale_from_global_angle(
    visangle: int,
    rw_normalangle: int,
    rw_distance: int,
    *,
    viewangle: int = VIEW_ANGLE,
) -> int:
    anglea = stage04._uint32(ANG90 + stage04._uint32(visangle - viewangle))
    angleb = stage04._uint32(ANG90 + stage04._uint32(visangle - rw_normalangle))
    sinea = FINESINE[fine_index(anglea)]
    sineb = FINESINE[fine_index(angleb)]
    num = fixed_mul(PROJECTION, sineb)
    den = fixed_mul(rw_distance, sinea)

    if den > (num >> FRACBITS):
        scale = fixed_div(num, den)
        if scale > MAXSCALE:
            return MAXSCALE
        if scale < MINSCALE:
            return MINSCALE
        return scale

    return MAXSCALE


def project_debug_span(
    span: DebugSpan,
    loaded: LoadedMap,
    raw_seg: Sequence[int],
) -> ProjectedSpan:
    v1 = loaded.vertices[raw_seg[0]]
    v1x = v1.x << FRACBITS
    v1y = v1.y << FRACBITS
    rw_angle1 = stage04.point_to_angle(v1x, v1y)
    rw_normalangle = stage04._uint32(raw_seg[2] << FRACBITS)
    rw_normalangle = stage04._uint32(rw_normalangle + ANG90)

    offsetangle = abs(stage04._int32(rw_normalangle) - stage04._int32(rw_angle1))
    if offsetangle > ANG90:
        offsetangle = ANG90

    distangle = ANG90 - offsetangle
    hyp = point_to_dist(v1x, v1y)
    sineval = FINESINE[fine_index(distangle)]
    rw_distance = fixed_mul(hyp, sineval)

    scale1 = scale_from_global_angle(
        stage04._uint32(VIEW_ANGLE + stage04.XTOVIEWANGLE[span.start]),
        rw_normalangle,
        rw_distance,
    )
    if span.stop > span.start:
        scale2 = scale_from_global_angle(
            stage04._uint32(VIEW_ANGLE + stage04.XTOVIEWANGLE[span.stop]),
            rw_normalangle,
            rw_distance,
        )
        scalestep = stage04._c_div(scale2 - scale1, span.stop - span.start)
    else:
        scale2 = scale1
        scalestep = 0

    return ProjectedSpan(
        x1=span.start,
        x2=span.stop,
        seg_index=span.seg_index,
        rw_normalangle=rw_normalangle,
        rw_distance=rw_distance,
        scale1=scale1,
        scale2=scale2,
        scalestep=scalestep,
    )


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
        spans=tuple(state.spans),
    )


def reference_wall_projection_for_pinned_map(wad_path: str | Path) -> WallProjectionReference:
    clip = reference_seg_clip_for_pinned_map(wad_path)
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    map_lumps = wad.map_lumps("MAP01")
    subsectors = stage02.parse_mapsubsectors(wad.read_lump(map_lumps.get("SSECTORS")))
    raw_segs = stage02.parse_mapsegs(wad.read_lump(map_lumps.get("SEGS")))

    view_subsector = clip.view_subsector
    view_sector_index = 0
    if 0 <= view_subsector < len(subsectors):
        numlines, firstline = subsectors[view_subsector]
        if numlines:
            first_seg = raw_segs[firstline]
            linedef = loaded.linedefs[first_seg[3]]
            sidenum = linedef.right_sidedef if first_seg[4] == 0 else linedef.left_sidedef
            view_sector_index = loaded.sidedefs[sidenum].sector

    viewz = (loaded.sectors[view_sector_index].floor_height << FRACBITS) + VIEWHEIGHT
    view_index = fine_index(VIEW_ANGLE)
    projected = tuple(
        project_debug_span(span, loaded, raw_segs[span.seg_index]) for span in clip.spans
    )

    distances = [span.rw_distance for span in projected] or [0]
    scales = [value for span in projected for value in (span.scale1, span.scale2)] or [0]
    empty = ProjectedSpan(0, 0, -1, 0, 0, 0, 0, 0)

    return WallProjectionReference(
        clip=clip,
        viewz=viewz,
        viewcos=FINECOSINE[view_index],
        viewsin=FINESINE[view_index],
        validcount=1,
        framecount=1,
        projected_spans=projected,
        min_distance=min(distances),
        max_distance=max(distances),
        min_scale=min(scales),
        max_scale=max(scales),
        first_projected_span=projected[0] if projected else empty,
        last_projected_span=projected[-1] if projected else empty,
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
    emit_clear_projection_counters(pe)
    x86.mov_mem_abs32_imm32(pe, "traversal_done", 0)

    x86.call_rel32(pe, "render_setup_frame_debug")

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


def emit_clear_projection_counters(pe: PE32) -> None:
    for label in (
        "projection_span_count",
        "projection_span_overflow_count",
        "projection_max_distance",
        "projection_max_scale",
        "projection_first_x1",
        "projection_first_x2",
        "projection_first_seg_index",
        "projection_first_rw_normalangle",
        "projection_first_rw_distance",
        "projection_first_scale1",
        "projection_first_scale2",
        "projection_first_scalestep",
        "projection_last_x1",
        "projection_last_x2",
        "projection_last_seg_index",
        "projection_last_rw_normalangle",
        "projection_last_rw_distance",
        "projection_last_scale1",
        "projection_last_scale2",
        "projection_last_scalestep",
        "projection_store_index",
        "projection_record_ptr",
        "projection_tmp_anglea",
        "projection_tmp_angleb",
        "projection_tmp_sinea",
        "projection_tmp_sineb",
        "projection_tmp_num",
        "projection_tmp_den",
        "projection_tmp_scale1",
        "projection_tmp_scale2",
        "projection_tmp_scalestep",
        "projection_tmp_hyp",
        "projection_tmp_offsetangle",
        "projection_tmp_distangle",
    ):
        x86.mov_mem_abs32_imm32(pe, label, 0)
    x86.mov_mem_abs32_imm32(pe, "projection_min_distance", 0x7FFFFFFF)
    x86.mov_mem_abs32_imm32(pe, "projection_min_scale", 0x7FFFFFFF)


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


def _emit_lookup_finesine_from_eax(pe: PE32) -> None:
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "ebx", "render_finesine_table")
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "ebx")


def _emit_lookup_finecosine_from_eax(pe: PE32) -> None:
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "ebx", "render_finecosine_table")
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "ebx")


def _emit_lookup_xtoviewangle_from_eax(pe: PE32) -> None:
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "ebx", "render_xtoviewangle_table")
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "ebx")


def emit_render_setup_frame_debug(pe: PE32) -> None:
    pe.label("render_setup_frame_debug")
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")

    x86.push_mem_abs32(pe, "viewy")
    x86.push_mem_abs32(pe, "viewx")
    x86.call_rel32(pe, "render_point_in_subsector")
    x86.mov_reg_ptr_reg(pe, "eax", "eax")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "eax", SECTOR_FLOORHEIGHT)
    x86.add_reg_imm32(pe, "eax", VIEWHEIGHT)
    x86.mov_mem_abs32_eax(pe, "viewz")

    x86.mov_reg_mem_abs32(pe, "eax", "viewangle")
    x86.shr_reg_imm8(pe, "eax", ANGLETOFINESHIFT)
    x86.mov_reg_reg(pe, "ecx", "eax")
    _emit_lookup_finesine_from_eax(pe)
    x86.mov_mem_abs32_eax(pe, "viewsin")
    x86.mov_reg_reg(pe, "eax", "ecx")
    _emit_lookup_finecosine_from_eax(pe)
    x86.mov_mem_abs32_eax(pe, "viewcos")

    _emit_inc_abs32(pe, "validcount")
    _emit_inc_abs32(pe, "framecount")

    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_render_fixed_div(pe: PE32) -> None:
    pe.label("render_fixed_div")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "edi")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_reg_ebp_disp8(pe, "ecx", 12)

    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.test_reg_reg(pe, "ebx")
    x86.jns_rel32(pe, "fixed_div_abs_a_done")
    x86.neg_reg(pe, "ebx")
    pe.label("fixed_div_abs_a_done")
    x86.shr_reg_imm8(pe, "ebx", 14)

    x86.mov_reg_reg(pe, "edi", "ecx")
    x86.test_reg_reg(pe, "edi")
    x86.jns_rel32(pe, "fixed_div_abs_b_done")
    x86.neg_reg(pe, "edi")
    pe.label("fixed_div_abs_b_done")

    x86.cmp_reg_reg(pe, "ebx", "edi")
    x86.jb_rel32(pe, "fixed_div_do_divide")

    x86.mov_reg_reg(pe, "edx", "eax")
    x86.xor_reg_reg(pe, "edx", "ecx")
    x86.test_reg_reg(pe, "edx")
    x86.jns_rel32(pe, "fixed_div_positive_saturation")
    x86.mov_reg_imm32(pe, "eax", 0x80000000)
    x86.jmp_rel32(pe, "fixed_div_done")

    pe.label("fixed_div_positive_saturation")
    x86.mov_reg_imm32(pe, "eax", 0x7FFFFFFF)
    x86.jmp_rel32(pe, "fixed_div_done")

    pe.label("fixed_div_do_divide")
    x86.cdq(pe)
    x86.shld_reg_reg_imm8(pe, "edx", "eax", FRACBITS)
    x86.shl_reg_imm8(pe, "eax", FRACBITS)
    x86.idiv_reg(pe, "ecx")

    pe.label("fixed_div_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 8)


def emit_render_point_to_dist(pe: PE32) -> None:
    pe.label("render_point_to_dist")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.sub_reg_mem_abs32(pe, "eax", "viewx")
    x86.test_reg_reg(pe, "eax")
    x86.jns_rel32(pe, "point_to_dist_dx_abs_done")
    x86.neg_reg(pe, "eax")
    pe.label("point_to_dist_dx_abs_done")
    x86.mov_reg_reg(pe, "ebx", "eax")

    x86.mov_eax_ebp_disp8(pe, 12)
    x86.sub_reg_mem_abs32(pe, "eax", "viewy")
    x86.test_reg_reg(pe, "eax")
    x86.jns_rel32(pe, "point_to_dist_dy_abs_done")
    x86.neg_reg(pe, "eax")
    pe.label("point_to_dist_dy_abs_done")
    x86.mov_reg_reg(pe, "ecx", "eax")

    x86.cmp_reg_reg(pe, "ecx", "ebx")
    x86.jbe_rel32(pe, "point_to_dist_have_major")
    x86.mov_reg_reg(pe, "eax", "ebx")
    x86.mov_reg_reg(pe, "ebx", "ecx")
    x86.mov_reg_reg(pe, "ecx", "eax")

    pe.label("point_to_dist_have_major")
    x86.mov_mem_abs32_reg(pe, "projection_tmp_point_dx", "ebx")
    x86.test_reg_reg(pe, "ebx")
    x86.je_rel32(pe, "point_to_dist_zero_dx")
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.call_rel32(pe, "render_fixed_div")
    x86.jmp_rel32(pe, "point_to_dist_have_frac")

    pe.label("point_to_dist_zero_dx")
    x86.xor_reg_reg(pe, "eax", "eax")

    pe.label("point_to_dist_have_frac")
    x86.shr_reg_imm8(pe, "eax", DBITS)
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "esi", "render_tantoangle_table")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "esi")
    x86.add_reg_imm32(pe, "eax", ANG90)
    x86.shr_reg_imm8(pe, "eax", ANGLETOFINESHIFT)
    _emit_lookup_finesine_from_eax(pe)
    x86.push_reg(pe, "eax")
    x86.push_mem_abs32(pe, "projection_tmp_point_dx")
    x86.call_rel32(pe, "render_fixed_div")

    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 8)


def emit_render_scale_from_global_angle(pe: PE32) -> None:
    pe.label("render_scale_from_global_angle")
    x86.emit_function_prologue(pe)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.sub_reg_mem_abs32(pe, "eax", "viewangle")
    x86.add_reg_imm32(pe, "eax", ANG90)
    x86.mov_mem_abs32_eax(pe, "projection_tmp_anglea")
    x86.shr_reg_imm8(pe, "eax", ANGLETOFINESHIFT)
    _emit_lookup_finesine_from_eax(pe)
    x86.mov_mem_abs32_eax(pe, "projection_tmp_sinea")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.sub_reg_mem_abs32(pe, "eax", "projection_rw_normalangle")
    x86.add_reg_imm32(pe, "eax", ANG90)
    x86.mov_mem_abs32_eax(pe, "projection_tmp_angleb")
    x86.shr_reg_imm8(pe, "eax", ANGLETOFINESHIFT)
    _emit_lookup_finesine_from_eax(pe)
    x86.mov_mem_abs32_eax(pe, "projection_tmp_sineb")

    x86.push_mem_abs32(pe, "projection_tmp_sineb")
    x86.push_mem_abs32(pe, "projection")
    x86.call_rel32(pe, "render_fixed_mul")
    x86.mov_mem_abs32_eax(pe, "projection_tmp_num")

    x86.push_mem_abs32(pe, "projection_tmp_sinea")
    x86.push_mem_abs32(pe, "projection_rw_distance")
    x86.call_rel32(pe, "render_fixed_mul")
    x86.mov_mem_abs32_eax(pe, "projection_tmp_den")

    x86.mov_reg_mem_abs32(pe, "ebx", "projection_tmp_num")
    x86.shr_reg_imm8(pe, "ebx", FRACBITS)
    x86.mov_reg_mem_abs32(pe, "eax", "projection_tmp_den")
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jbe_rel32(pe, "scale_from_global_angle_max")

    x86.push_reg(pe, "eax")
    x86.push_mem_abs32(pe, "projection_tmp_num")
    x86.call_rel32(pe, "render_fixed_div")
    x86.cmp_eax_imm32(pe, MAXSCALE)
    x86.jbe_rel32(pe, "scale_from_global_angle_check_min")
    x86.mov_reg_imm32(pe, "eax", MAXSCALE)
    x86.jmp_rel32(pe, "scale_from_global_angle_done")

    pe.label("scale_from_global_angle_check_min")
    x86.cmp_eax_imm32(pe, MINSCALE)
    x86.jae_rel32(pe, "scale_from_global_angle_done")
    x86.mov_reg_imm32(pe, "eax", MINSCALE)
    x86.jmp_rel32(pe, "scale_from_global_angle_done")

    pe.label("scale_from_global_angle_max")
    x86.mov_reg_imm32(pe, "eax", MAXSCALE)

    pe.label("scale_from_global_angle_done")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 4)


def emit_render_store_wall_range_debug(pe: PE32) -> None:
    pe.label("render_store_wall_range_projected_debug")
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
    x86.cmp_reg_imm32(pe, "ecx", MAX_PROJECTED_SPANS)
    x86.jb_rel32(pe, "store_wall_range_have_space")
    _emit_inc_abs32(pe, "clip_span_overflow_count")
    _emit_inc_abs32(pe, "projection_span_overflow_count")
    x86.jmp_rel32(pe, "store_wall_range_done")

    pe.label("store_wall_range_have_space")
    x86.mov_mem_abs32_reg(pe, "projection_store_index", "ecx")

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

    x86.mov_reg_mem_abs32(pe, "ecx", "projection_store_index")
    x86.test_reg_reg(pe, "ecx")
    x86.jne_rel32(pe, "store_wall_range_not_first_clip")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_mem_abs32_eax(pe, "clip_first_span_start")
    x86.mov_reg_ebp_disp8(pe, "eax", 12)
    x86.mov_mem_abs32_eax(pe, "clip_first_span_stop")
    x86.mov_reg_mem_abs32(pe, "eax", "clip_current_span_reason")
    x86.mov_mem_abs32_eax(pe, "clip_first_span_reason")
    x86.mov_reg_mem_abs32(pe, "eax", "clip_current_seg_index")
    x86.mov_mem_abs32_eax(pe, "clip_first_span_seg_index")

    pe.label("store_wall_range_not_first_clip")
    x86.mov_reg_mem_abs32(pe, "edx", "projection_store_index")
    x86.shl_reg_imm8(pe, "edx", 5)
    x86.mov_reg_abs32(pe, "edi", "wall_projection_debug_buffer")
    x86.add_reg_reg(pe, "edi", "edx")
    x86.mov_mem_abs32_reg(pe, "projection_record_ptr", "edi")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.mov_reg_ebp_disp8(pe, "eax", 12)
    x86.mov_ptr_reg_disp8_eax(pe, "edi", PROJECTED_SPAN_X2)
    x86.mov_reg_mem_abs32(pe, "eax", "clip_current_seg_index")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", PROJECTED_SPAN_SEG_INDEX)

    x86.mov_reg_mem_abs32(pe, "esi", "clip_curline")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage02.SEG_ANGLE)
    x86.add_reg_imm32(pe, "eax", ANG90)
    x86.mov_mem_abs32_eax(pe, "projection_rw_normalangle")

    x86.mov_reg_mem_abs32(pe, "eax", "projection_rw_normalangle")
    x86.sub_reg_mem_abs32(pe, "eax", "clip_rw_angle1")
    x86.test_reg_reg(pe, "eax")
    x86.jns_rel32(pe, "store_wall_range_offset_abs_done")
    x86.neg_reg(pe, "eax")
    pe.label("store_wall_range_offset_abs_done")
    x86.cmp_eax_imm32(pe, ANG90)
    x86.jbe_rel32(pe, "store_wall_range_offset_clamped")
    x86.mov_reg_imm32(pe, "eax", ANG90)
    pe.label("store_wall_range_offset_clamped")
    x86.mov_mem_abs32_eax(pe, "projection_tmp_offsetangle")
    x86.mov_reg_imm32(pe, "eax", ANG90)
    x86.sub_reg_mem_abs32(pe, "eax", "projection_tmp_offsetangle")
    x86.mov_mem_abs32_eax(pe, "projection_tmp_distangle")

    x86.mov_reg_mem_abs32(pe, "esi", "clip_curline")
    x86.mov_reg_ptr_reg_disp8(pe, "esi", "esi", stage02.SEG_V1)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 4)
    x86.push_reg(pe, "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "esi")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_point_to_dist")
    x86.mov_mem_abs32_eax(pe, "projection_tmp_hyp")

    x86.mov_reg_mem_abs32(pe, "eax", "projection_tmp_distangle")
    x86.shr_reg_imm8(pe, "eax", ANGLETOFINESHIFT)
    _emit_lookup_finesine_from_eax(pe)
    x86.push_reg(pe, "eax")
    x86.push_mem_abs32(pe, "projection_tmp_hyp")
    x86.call_rel32(pe, "render_fixed_mul")
    x86.mov_mem_abs32_eax(pe, "projection_rw_distance")

    x86.mov_eax_ebp_disp8(pe, 8)
    _emit_lookup_xtoviewangle_from_eax(pe)
    x86.add_reg_mem_abs32(pe, "eax", "viewangle")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_scale_from_global_angle")
    x86.mov_mem_abs32_eax(pe, "projection_tmp_scale1")

    x86.mov_reg_ebp_disp8(pe, "eax", 12)
    x86.mov_reg_ebp_disp8(pe, "ecx", 8)
    x86.cmp_reg_reg(pe, "eax", "ecx")
    x86.jbe_rel32(pe, "store_wall_range_single_column_scale")

    x86.mov_reg_ebp_disp8(pe, "eax", 12)
    _emit_lookup_xtoviewangle_from_eax(pe)
    x86.add_reg_mem_abs32(pe, "eax", "viewangle")
    x86.push_reg(pe, "eax")
    x86.call_rel32(pe, "render_scale_from_global_angle")
    x86.mov_mem_abs32_eax(pe, "projection_tmp_scale2")
    x86.sub_reg_mem_abs32(pe, "eax", "projection_tmp_scale1")
    x86.mov_reg_reg(pe, "ecx", "eax")
    x86.mov_reg_ebp_disp8(pe, "eax", 12)
    x86.mov_reg_ebp_disp8(pe, "ebx", 8)
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.mov_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_reg(pe, "eax", "ecx")
    x86.cdq(pe)
    x86.idiv_reg(pe, "ebx")
    x86.mov_mem_abs32_eax(pe, "projection_tmp_scalestep")
    x86.jmp_rel32(pe, "store_wall_range_have_projection_scales")

    pe.label("store_wall_range_single_column_scale")
    x86.mov_reg_mem_abs32(pe, "eax", "projection_tmp_scale1")
    x86.mov_mem_abs32_eax(pe, "projection_tmp_scale2")
    x86.mov_mem_abs32_imm32(pe, "projection_tmp_scalestep", 0)

    pe.label("store_wall_range_have_projection_scales")
    x86.mov_reg_mem_abs32(pe, "edi", "projection_record_ptr")
    x86.mov_reg_mem_abs32(pe, "eax", "projection_rw_normalangle")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", PROJECTED_SPAN_RW_NORMALANGLE)
    x86.mov_mem_abs32_eax(pe, "projection_last_rw_normalangle")
    x86.mov_reg_mem_abs32(pe, "eax", "projection_rw_distance")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", PROJECTED_SPAN_RW_DISTANCE)
    x86.mov_mem_abs32_eax(pe, "projection_last_rw_distance")
    x86.mov_reg_mem_abs32(pe, "eax", "projection_tmp_scale1")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", PROJECTED_SPAN_SCALE1)
    x86.mov_mem_abs32_eax(pe, "projection_last_scale1")
    x86.mov_reg_mem_abs32(pe, "eax", "projection_tmp_scale2")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", PROJECTED_SPAN_SCALE2)
    x86.mov_mem_abs32_eax(pe, "projection_last_scale2")
    x86.mov_reg_mem_abs32(pe, "eax", "projection_tmp_scalestep")
    x86.mov_ptr_reg_disp8_eax(pe, "edi", PROJECTED_SPAN_SCALESTEP)
    x86.mov_mem_abs32_eax(pe, "projection_last_scalestep")

    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_mem_abs32_eax(pe, "projection_last_x1")
    x86.mov_reg_ebp_disp8(pe, "eax", 12)
    x86.mov_mem_abs32_eax(pe, "projection_last_x2")
    x86.mov_reg_mem_abs32(pe, "eax", "clip_current_seg_index")
    x86.mov_mem_abs32_eax(pe, "projection_last_seg_index")

    x86.mov_reg_mem_abs32(pe, "eax", "projection_rw_distance")
    x86.cmp_reg_mem_abs32(pe, "eax", "projection_min_distance")
    x86.jae_rel32(pe, "store_wall_range_min_distance_done")
    x86.mov_mem_abs32_eax(pe, "projection_min_distance")
    pe.label("store_wall_range_min_distance_done")
    x86.cmp_reg_mem_abs32(pe, "eax", "projection_max_distance")
    x86.jbe_rel32(pe, "store_wall_range_max_distance_done")
    x86.mov_mem_abs32_eax(pe, "projection_max_distance")
    pe.label("store_wall_range_max_distance_done")

    _emit_update_projection_scale_minmax(pe, "projection_tmp_scale1", "scale1")
    _emit_update_projection_scale_minmax(pe, "projection_tmp_scale2", "scale2")

    x86.mov_reg_mem_abs32(pe, "ecx", "projection_store_index")
    x86.test_reg_reg(pe, "ecx")
    x86.jne_rel32(pe, "store_wall_range_not_first_projection")
    x86.mov_eax_ebp_disp8(pe, 8)
    x86.mov_mem_abs32_eax(pe, "projection_first_x1")
    x86.mov_reg_ebp_disp8(pe, "eax", 12)
    x86.mov_mem_abs32_eax(pe, "projection_first_x2")
    x86.mov_reg_mem_abs32(pe, "eax", "clip_current_seg_index")
    x86.mov_mem_abs32_eax(pe, "projection_first_seg_index")
    x86.mov_reg_mem_abs32(pe, "eax", "projection_rw_normalangle")
    x86.mov_mem_abs32_eax(pe, "projection_first_rw_normalangle")
    x86.mov_reg_mem_abs32(pe, "eax", "projection_rw_distance")
    x86.mov_mem_abs32_eax(pe, "projection_first_rw_distance")
    x86.mov_reg_mem_abs32(pe, "eax", "projection_tmp_scale1")
    x86.mov_mem_abs32_eax(pe, "projection_first_scale1")
    x86.mov_reg_mem_abs32(pe, "eax", "projection_tmp_scale2")
    x86.mov_mem_abs32_eax(pe, "projection_first_scale2")
    x86.mov_reg_mem_abs32(pe, "eax", "projection_tmp_scalestep")
    x86.mov_mem_abs32_eax(pe, "projection_first_scalestep")

    pe.label("store_wall_range_not_first_projection")
    x86.mov_reg_mem_abs32(pe, "ecx", "projection_store_index")
    x86.inc_reg(pe, "ecx")
    x86.mov_mem_abs32_reg(pe, "clip_stored_span_count", "ecx")
    x86.mov_mem_abs32_reg(pe, "projection_span_count", "ecx")

    pe.label("store_wall_range_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.emit_function_epilogue_ret(pe, 8)


def _emit_update_projection_scale_minmax(pe: PE32, label: str, suffix: str) -> None:
    x86.mov_reg_mem_abs32(pe, "eax", label)
    x86.cmp_reg_mem_abs32(pe, "eax", "projection_min_scale")
    x86.jae_rel32(pe, f"store_wall_range_min_{suffix}_done")
    x86.mov_mem_abs32_eax(pe, "projection_min_scale")
    pe.label(f"store_wall_range_min_{suffix}_done")
    x86.cmp_reg_mem_abs32(pe, "eax", "projection_max_scale")
    x86.jbe_rel32(pe, f"store_wall_range_max_{suffix}_done")
    x86.mov_mem_abs32_eax(pe, "projection_max_scale")
    pe.label(f"store_wall_range_max_{suffix}_done")


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

    stage01.append_c_string_label(pe, "status_stage07_success_header")
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
    stage01.append_u32_label(pe, "status_viewz_prefix", "viewz")
    stage01.append_u32_label(pe, "status_viewcos_prefix", "viewcos")
    stage01.append_u32_label(pe, "status_viewsin_prefix", "viewsin")
    stage01.append_u32_label(pe, "status_validcount_prefix", "validcount")
    stage01.append_u32_label(pe, "status_framecount_prefix", "framecount")
    stage01.append_u32_label(pe, "status_projection_count_prefix", "projection_span_count")
    stage01.append_u32_label(pe, "status_projection_min_distance_prefix", "projection_min_distance")
    stage01.append_u32_label(pe, "status_projection_max_distance_prefix", "projection_max_distance")
    stage01.append_u32_label(pe, "status_projection_min_scale_prefix", "projection_min_scale")
    stage01.append_u32_label(pe, "status_projection_max_scale_prefix", "projection_max_scale")
    stage01.append_u32_label(pe, "status_projection_first_prefix", "projection_first_x1")
    stage01.append_c_string_label(pe, "status_span_dash")
    stage01.append_u32_label(pe, "status_empty_prefix", "projection_first_x2")
    stage01.append_u32_label(pe, "status_projection_seg_prefix", "projection_first_seg_index")
    stage01.append_u32_label(pe, "status_projection_dist_prefix", "projection_first_rw_distance")
    stage01.append_u32_label(pe, "status_projection_scale_prefix", "projection_first_scale1")
    stage01.append_u32_label(pe, "status_projection_last_prefix", "projection_last_x1")
    stage01.append_c_string_label(pe, "status_span_dash")
    stage01.append_u32_label(pe, "status_empty_prefix", "projection_last_x2")
    stage01.append_u32_label(pe, "status_projection_seg_prefix", "projection_last_seg_index")
    stage01.append_u32_label(pe, "status_projection_dist_prefix", "projection_last_rw_distance")
    stage01.append_u32_label(pe, "status_projection_scale_prefix", "projection_last_scale1")
    stage01.append_c_string_label(pe, "status_stage07_note")
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
    stage01.append_u32_label(pe, "title_viewz_prefix", "viewz")
    stage01.append_u32_label(pe, "title_viewcos_prefix", "viewcos")
    stage01.append_u32_label(pe, "title_viewsin_prefix", "viewsin")
    stage01.append_u32_label(pe, "title_validcount_prefix", "validcount")
    stage01.append_u32_label(pe, "title_framecount_prefix", "framecount")
    stage01.append_u32_label(pe, "title_projection_count_prefix", "projection_span_count")
    stage01.append_u32_label(pe, "title_projection_min_distance_prefix", "projection_min_distance")
    stage01.append_u32_label(pe, "title_projection_max_distance_prefix", "projection_max_distance")
    stage01.append_u32_label(pe, "title_projection_min_scale_prefix", "projection_min_scale")
    stage01.append_u32_label(pe, "title_projection_max_scale_prefix", "projection_max_scale")
    stage01.append_u32_label(pe, "title_projection_first_prefix", "projection_first_x1")
    stage01.append_c_string_label(pe, "status_span_dash")
    stage01.append_u32_label(pe, "status_empty_prefix", "projection_first_x2")
    stage01.append_u32_label(pe, "title_projection_first_seg_prefix", "projection_first_seg_index")
    stage01.append_u32_label(pe, "title_projection_last_prefix", "projection_last_x1")
    stage01.append_c_string_label(pe, "status_span_dash")
    stage01.append_u32_label(pe, "status_empty_prefix", "projection_last_x2")
    stage01.append_u32_label(pe, "title_projection_last_seg_prefix", "projection_last_seg_index")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage07_data(pe: PE32) -> None:
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

    pe.label("viewz")
    pe.emit_u32(0)
    pe.label("viewcos")
    pe.emit_u32(0)
    pe.label("viewsin")
    pe.emit_u32(0)
    pe.label("validcount")
    pe.emit_u32(0)
    pe.label("framecount")
    pe.emit_u32(0)

    pe.label("projection_span_count")
    pe.emit_u32(0)
    pe.label("projection_span_overflow_count")
    pe.emit_u32(0)
    pe.label("projection_min_distance")
    pe.emit_u32(0x7FFFFFFF)
    pe.label("projection_max_distance")
    pe.emit_u32(0)
    pe.label("projection_min_scale")
    pe.emit_u32(0x7FFFFFFF)
    pe.label("projection_max_scale")
    pe.emit_u32(0)
    pe.label("projection_first_x1")
    pe.emit_u32(0)
    pe.label("projection_first_x2")
    pe.emit_u32(0)
    pe.label("projection_first_seg_index")
    pe.emit_u32(0)
    pe.label("projection_first_rw_normalangle")
    pe.emit_u32(0)
    pe.label("projection_first_rw_distance")
    pe.emit_u32(0)
    pe.label("projection_first_scale1")
    pe.emit_u32(0)
    pe.label("projection_first_scale2")
    pe.emit_u32(0)
    pe.label("projection_first_scalestep")
    pe.emit_u32(0)
    pe.label("projection_last_x1")
    pe.emit_u32(0)
    pe.label("projection_last_x2")
    pe.emit_u32(0)
    pe.label("projection_last_seg_index")
    pe.emit_u32(0)
    pe.label("projection_last_rw_normalangle")
    pe.emit_u32(0)
    pe.label("projection_last_rw_distance")
    pe.emit_u32(0)
    pe.label("projection_last_scale1")
    pe.emit_u32(0)
    pe.label("projection_last_scale2")
    pe.emit_u32(0)
    pe.label("projection_last_scalestep")
    pe.emit_u32(0)
    pe.label("projection_store_index")
    pe.emit_u32(0)
    pe.label("projection_record_ptr")
    pe.emit_u32(0)
    pe.label("projection_rw_normalangle")
    pe.emit_u32(0)
    pe.label("projection_rw_distance")
    pe.emit_u32(0)
    pe.label("projection_tmp_anglea")
    pe.emit_u32(0)
    pe.label("projection_tmp_angleb")
    pe.emit_u32(0)
    pe.label("projection_tmp_sinea")
    pe.emit_u32(0)
    pe.label("projection_tmp_sineb")
    pe.emit_u32(0)
    pe.label("projection_tmp_num")
    pe.emit_u32(0)
    pe.label("projection_tmp_den")
    pe.emit_u32(0)
    pe.label("projection_tmp_scale1")
    pe.emit_u32(0)
    pe.label("projection_tmp_scale2")
    pe.emit_u32(0)
    pe.label("projection_tmp_scalestep")
    pe.emit_u32(0)
    pe.label("projection_tmp_hyp")
    pe.emit_u32(0)
    pe.label("projection_tmp_offsetangle")
    pe.emit_u32(0)
    pe.label("projection_tmp_distangle")
    pe.emit_u32(0)
    pe.label("projection_tmp_point_dx")
    pe.emit_u32(0)

    pe.align_section(1)
    pe.label("status_stage07_success_header")
    x86.emit_asciiz(pe, "source_stage07_wall_projection_debug\r\nWall projection debug OK\r\n")
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
    pe.label("status_viewz_prefix")
    x86.emit_asciiz(pe, "\r\nFixed debug viewz: ")
    pe.label("status_viewcos_prefix")
    x86.emit_asciiz(pe, "\r\nR_SetupFrame viewcos: ")
    pe.label("status_viewsin_prefix")
    x86.emit_asciiz(pe, "\r\nR_SetupFrame viewsin: ")
    pe.label("status_validcount_prefix")
    x86.emit_asciiz(pe, "\r\nvalidcount: ")
    pe.label("status_framecount_prefix")
    x86.emit_asciiz(pe, "\r\nframecount: ")
    pe.label("status_projection_count_prefix")
    x86.emit_asciiz(pe, "\r\nProjected R_StoreWallRange records: ")
    pe.label("status_projection_min_distance_prefix")
    x86.emit_asciiz(pe, "\r\nR_PointToDist/rw_distance min: ")
    pe.label("status_projection_max_distance_prefix")
    x86.emit_asciiz(pe, "\r\nR_PointToDist/rw_distance max: ")
    pe.label("status_projection_min_scale_prefix")
    x86.emit_asciiz(pe, "\r\nR_ScaleFromGlobalAngle scale min: ")
    pe.label("status_projection_max_scale_prefix")
    x86.emit_asciiz(pe, "\r\nR_ScaleFromGlobalAngle scale max: ")
    pe.label("status_projection_first_prefix")
    x86.emit_asciiz(pe, "\r\nFirst projected span: ")
    pe.label("status_projection_last_prefix")
    x86.emit_asciiz(pe, "\r\nLast projected span: ")
    pe.label("status_projection_seg_prefix")
    x86.emit_asciiz(pe, " seg=")
    pe.label("status_projection_dist_prefix")
    x86.emit_asciiz(pe, " dist=")
    pe.label("status_projection_scale_prefix")
    x86.emit_asciiz(pe, " scale=")
    pe.label("status_stage07_note")
    x86.emit_asciiz(
        pe,
        "\r\nMutable R_AddLine/R_ClipSolidWallSegment/R_ClipPassWallSegment "
        "still run live; stage07 adds FixedDiv/R_PointToDist/R_ScaleFromGlobalAngle "
        "projection records and stops before texture pixels, plane spans, actors, or columns.\r\n",
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
    pe.label("title_viewz_prefix")
    x86.emit_asciiz(pe, " VZ=")
    pe.label("title_viewcos_prefix")
    x86.emit_asciiz(pe, " VCOS=")
    pe.label("title_viewsin_prefix")
    x86.emit_asciiz(pe, " VSIN=")
    pe.label("title_validcount_prefix")
    x86.emit_asciiz(pe, " VALID=")
    pe.label("title_framecount_prefix")
    x86.emit_asciiz(pe, " FRAME=")
    pe.label("title_projection_count_prefix")
    x86.emit_asciiz(pe, " PRJ=")
    pe.label("title_projection_min_distance_prefix")
    x86.emit_asciiz(pe, " MIND=")
    pe.label("title_projection_max_distance_prefix")
    x86.emit_asciiz(pe, " MAXD=")
    pe.label("title_projection_min_scale_prefix")
    x86.emit_asciiz(pe, " MINS=")
    pe.label("title_projection_max_scale_prefix")
    x86.emit_asciiz(pe, " MAXS=")
    pe.label("title_projection_first_prefix")
    x86.emit_asciiz(pe, " FPRJ=")
    pe.label("title_projection_first_seg_prefix")
    x86.emit_asciiz(pe, " FPSEG=")
    pe.label("title_projection_last_prefix")
    x86.emit_asciiz(pe, " LPRJ=")
    pe.label("title_projection_last_seg_prefix")
    x86.emit_asciiz(pe, " LPSEG=")

    pe.align_section(4)
    pe.label("wall_span_debug_buffer")
    pe.emit_zeros(DEBUG_SPAN_BUFFER_BYTES)
    pe.label("wall_projection_debug_buffer")
    pe.emit_zeros(PROJECTED_SPAN_BUFFER_BYTES)
    pe.label("render_fine_trig_tables")
    pe.label("render_finesine_table")
    for index, value in enumerate(FINESINE):
        if index == FINEANGLES // 4:
            pe.label("render_finecosine_table")
        pe.emit_u32(value)


def build_source_stage07_wall_projection_debug_exe() -> bytes:
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
    emit_render_setup_frame_debug(pe)
    emit_render_fixed_div(pe)
    emit_render_point_to_dist(pe)
    emit_render_scale_from_global_angle(pe)
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
    emit_stage07_data(pe)
    return pe.build("entry")


def write_source_stage07_wall_projection_debug_exe(path: str | Path) -> bytes:
    image = build_source_stage07_wall_projection_debug_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the source-guided PE32 x86 wall projection debug executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/source_stage07_wall_projection_debug.exe",
        help="path to write, default: build/source_stage07_wall_projection_debug.exe",
    )
    args = parser.parse_args()
    write_source_stage07_wall_projection_debug_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
