from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage01_wad_map as stage01
from tools import emit_source_stage02_bsp_setup as stage02
from tools import emit_source_stage03_bsp_walk_debug as stage03
from tools import emit_source_stage04_bbox_visibility_debug as stage04
from tools import emit_source_stage07_wall_projection_debug as stage07
from tools import emit_source_stage08_texture_data_setup_debug as stage08
from tools import emit_source_stage09_direct_wall_column_pixels_debug as stage09
from tools import emit_source_stage10_composite_two_sided_wall_edges_debug as stage10
from tools import x86
from tools.map_loader import LoadedMap, load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


FRAMEBUFFER_WIDTH = stage10.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage10.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage10.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage10.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage10.WINDOW_WIDTH
WINDOW_HEIGHT = stage10.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage11VisplanesFloorCeilingDebug"
WINDOW_TITLE = "Inference Doom S11 Visplanes Flats"
WAD_PATH = stage10.WAD_PATH

FRACBITS = stage10.FRACBITS
FRACUNIT = stage10.FRACUNIT
VIEW_ANGLE = stage10.VIEW_ANGLE
ANG90 = stage07.ANG90
ANGLETOFINESHIFT = stage07.ANGLETOFINESHIFT
FINEANGLES = stage07.FINEANGLES
FINEMASK = FINEANGLES - 1
FINESINE = stage07.FINESINE
FINECOSINE = stage07.FINECOSINE
XTOVIEWANGLE = stage04.XTOVIEWANGLE
CENTER_X = FRAMEBUFFER_WIDTH // 2
CENTER_Y = FRAMEBUFFER_HEIGHT // 2
CENTERXFRAC = CENTER_X << FRACBITS
CENTERYFRAC = CENTER_Y << FRACBITS
VIEW_X_FIXED = stage07.VIEW_X_FIXED
VIEW_Y_FIXED = stage07.VIEW_Y_FIXED
FNV_OFFSET_BASIS = stage10.FNV_OFFSET_BASIS
FNV_PRIME = stage10.FNV_PRIME

NO_TOP = 0xFF
VISPLANE_PAD = 1
DEFAULT_MAX_VISPLANES = 128
DEFAULT_MAX_FLAT_SPAN_COMMANDS = 65536
FLAT_SIZE = 64 * 64

SPAN_COMMAND_Y = 0
SPAN_COMMAND_X1 = 4
SPAN_COMMAND_X2 = 8
SPAN_COMMAND_XFRAC = 12
SPAN_COMMAND_YFRAC = 16
SPAN_COMMAND_XSTEP = 20
SPAN_COMMAND_YSTEP = 24
SPAN_COMMAND_SOURCE = 28
SPAN_COMMAND_RECORD_SIZE = 32

SOURCE_TRACE = stage10.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/r_bsp.c",
        "R_Subsector floorplane/ceilingplane candidates",
        "render_visplane_subsector_candidates_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_plane.c",
        "R_ClearPlanes",
        "render_clear_planes_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_plane.c",
        "R_FindPlane",
        "render_find_plane_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_plane.c",
        "R_CheckPlane",
        "render_check_plane_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_plane.c",
        "R_MakeSpans",
        "render_make_spans_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_plane.c",
        "R_MapPlane",
        "render_map_plane_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_plane.c",
        "R_DrawPlanes regular flat branch",
        "render_draw_planes_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_draw.c",
        "R_DrawSpan",
        "render_draw_span_debug",
    ),
    (
        "WAD flat data",
        "64x64 flat lumps",
        "stage11_flat_lump_sources_debug",
    ),
)


@dataclass(frozen=True)
class Stage11SpanCommand:
    y: int
    x1: int
    x2: int
    xfrac: int
    yfrac: int
    xstep: int
    ystep: int
    source_index: int
    flat_id: int
    flat_name: str
    plane_kind: str


@dataclass
class Visplane:
    height: int
    picnum: int
    lightlevel: int
    width: int = FRAMEBUFFER_WIDTH
    minx: int = FRAMEBUFFER_WIDTH
    maxx: int = -1
    top: list[int] = field(default_factory=list)
    bottom: list[int] = field(default_factory=list)
    kinds: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.minx == FRAMEBUFFER_WIDTH and self.width != FRAMEBUFFER_WIDTH:
            self.minx = self.width
        if not self.top:
            self.top = [NO_TOP] * (self.width + 2 * VISPLANE_PAD)
        if not self.bottom:
            self.bottom = [0] * (self.width + 2 * VISPLANE_PAD)

    def _slot(self, x: int) -> int:
        if x < -1 or x > self.width:
            raise IndexError(f"visplane padded x out of range: {x}")
        return x + VISPLANE_PAD

    def top_at(self, x: int) -> int:
        return self.top[self._slot(x)]

    def bottom_at(self, x: int) -> int:
        return self.bottom[self._slot(x)]

    def set_mark(self, x: int, top: int, bottom: int, kind: str) -> None:
        if x < 0 or x >= self.width:
            raise IndexError(f"visplane screen x out of range: {x}")
        slot = self._slot(x)
        self.top[slot] = top & 0xFF
        self.bottom[slot] = bottom & 0xFF
        self.kinds.add(kind)

    def set_top_sentinel(self, x: int) -> None:
        self.top[self._slot(x)] = NO_TOP


@dataclass
class VisplaneState:
    width: int = FRAMEBUFFER_WIDTH
    height: int = FRAMEBUFFER_HEIGHT
    max_visplanes: int = DEFAULT_MAX_VISPLANES
    skyflatnum: int = -1
    visplanes: list[Visplane] = field(default_factory=list)
    spanstart: list[int] = field(default_factory=list)
    find_calls: int = 0
    find_new: int = 0
    find_reused: int = 0
    check_calls: int = 0
    check_reused: int = 0
    check_splits: int = 0
    overflow: int = 0

    def __post_init__(self) -> None:
        if not self.spanstart:
            self.spanstart = [0] * self.height

    def clear_planes(self) -> None:
        self.visplanes.clear()
        self.spanstart = [0] * self.height
        self.find_calls = 0
        self.find_new = 0
        self.find_reused = 0
        self.check_calls = 0
        self.check_reused = 0
        self.check_splits = 0
        self.overflow = 0

    def find_plane(
        self, height: int, picnum: int, lightlevel: int, kind: str = ""
    ) -> Visplane | None:
        self.find_calls += 1
        if picnum == self.skyflatnum:
            height = 0
            lightlevel = 0

        for plane in self.visplanes:
            if (
                plane.height == height
                and plane.picnum == picnum
                and plane.lightlevel == lightlevel
            ):
                self.find_reused += 1
                if kind:
                    plane.kinds.add(kind)
                return plane

        if len(self.visplanes) >= self.max_visplanes:
            self.overflow += 1
            return None

        plane = Visplane(
            height=height,
            picnum=picnum,
            lightlevel=lightlevel,
            width=self.width,
        )
        if kind:
            plane.kinds.add(kind)
        self.visplanes.append(plane)
        self.find_new += 1
        return plane

    def check_plane(
        self, plane: Visplane | None, start: int, stop: int, kind: str = ""
    ) -> Visplane | None:
        if plane is None:
            return None
        self.check_calls += 1

        if start < plane.minx:
            intrl = plane.minx
            unionl = start
        else:
            unionl = plane.minx
            intrl = start

        if stop > plane.maxx:
            intrh = plane.maxx
            unionh = stop
        else:
            unionh = plane.maxx
            intrh = stop

        occupied = False
        if intrl <= intrh:
            for x in range(intrl, intrh + 1):
                if plane.top_at(x) != NO_TOP:
                    occupied = True
                    break

        if not occupied:
            plane.minx = unionl
            plane.maxx = unionh
            if kind:
                plane.kinds.add(kind)
            self.check_reused += 1
            return plane

        if len(self.visplanes) >= self.max_visplanes:
            self.overflow += 1
            return None

        split = Visplane(
            height=plane.height,
            picnum=plane.picnum,
            lightlevel=plane.lightlevel,
            width=self.width,
            minx=start,
            maxx=stop,
        )
        split.kinds.update(plane.kinds)
        if kind:
            split.kinds.add(kind)
        self.visplanes.append(split)
        self.check_splits += 1
        return split


@dataclass
class PlaneMappingTables:
    yslope: list[int]
    distscale: list[int]
    basexscale: int
    baseyscale: int
    cachedheight: list[int]
    cacheddistance: list[int]
    cachedxstep: list[int]
    cachedystep: list[int]

    @classmethod
    def fixed_view(cls) -> "PlaneMappingTables":
        yslope: list[int] = []
        for y in range(FRAMEBUFFER_HEIGHT):
            dy = ((y - FRAMEBUFFER_HEIGHT // 2) << FRACBITS) + FRACUNIT // 2
            dy = abs(dy)
            yslope.append(stage04.fixed_div((FRAMEBUFFER_WIDTH // 2) * FRACUNIT, dy))

        distscale: list[int] = []
        for x in range(FRAMEBUFFER_WIDTH):
            angle = (stage04._uint32(XTOVIEWANGLE[x]) >> ANGLETOFINESHIFT) & FINEMASK
            cosadj = abs(FINECOSINE[angle])
            distscale.append(stage04.fixed_div(FRACUNIT, cosadj))

        base_angle = (
            stage04._uint32(VIEW_ANGLE - ANG90) >> ANGLETOFINESHIFT
        ) & FINEMASK
        basexscale = stage04.fixed_div(FINECOSINE[base_angle], CENTERXFRAC)
        baseyscale = stage04._int32(-stage04.fixed_div(FINESINE[base_angle], CENTERXFRAC))

        return cls(
            yslope=yslope,
            distscale=distscale,
            basexscale=basexscale,
            baseyscale=baseyscale,
            cachedheight=[0] * FRAMEBUFFER_HEIGHT,
            cacheddistance=[0] * FRAMEBUFFER_HEIGHT,
            cachedxstep=[0] * FRAMEBUFFER_HEIGHT,
            cachedystep=[0] * FRAMEBUFFER_HEIGHT,
        )


@dataclass(frozen=True)
class Stage11VisplanesFloorCeilingReference:
    stage10: stage10.Stage10CompositeTwoSidedWallEdgesReference
    palette32: tuple[int, ...]
    flat_sources: tuple[bytes, ...]
    commands: tuple[Stage11SpanCommand, ...]
    visplane_count: int
    visplane_find_calls: int
    visplane_new_count: int
    visplane_reuse_count: int
    visplane_check_calls: int
    visplane_check_reuse_count: int
    visplane_split_count: int
    visplane_overflow_count: int
    ceiling_plane_mark_records: int
    floor_plane_mark_records: int
    regular_visplanes_drawn: int
    flat_spans_drawn: int
    flat_pixels_drawn: int
    flat_source_skips: int
    flat_span_overflow_count: int
    sky_visplanes_skipped: int
    sky_columns_skipped: int
    sky_pixels_skipped: int
    first_floor_flat_id: int
    first_floor_flat_name: str
    first_ceiling_flat_id: int
    first_ceiling_flat_name: str
    framebuffer_signature: int


def _u32(value: int) -> int:
    return value & 0xFFFFFFFF


def _fine_index(angle: int) -> int:
    return (stage04._uint32(angle) >> ANGLETOFINESHIFT) & FINEMASK


def _flat_lump_index(setup: stage08.TextureSetup, picnum: int) -> int | None:
    if picnum < 0 or picnum >= len(setup.flattranslation):
        return None
    return setup.firstflat + setup.flattranslation[picnum]


def flat_name_for_picnum(wad: WadFile, setup: stage08.TextureSetup, picnum: int) -> str:
    lump_index = _flat_lump_index(setup, picnum)
    if lump_index is None or lump_index < 0 or lump_index >= len(wad.lumps):
        return ""
    return wad.lumps[lump_index].name


def flat_data_for_picnum(
    wad: WadFile, setup: stage08.TextureSetup, picnum: int
) -> bytes | None:
    lump_index = _flat_lump_index(setup, picnum)
    if lump_index is None or lump_index < 0 or lump_index >= len(wad.lumps):
        return None
    data = wad.read_lump(wad.lumps[lump_index])
    if len(data) != FLAT_SIZE:
        return None
    return data


def r_draw_span_pixels(
    source: bytes,
    palette32: Sequence[int],
    *,
    x1: int,
    x2: int,
    xfrac: int,
    yfrac: int,
    xstep: int,
    ystep: int,
    signature: int = FNV_OFFSET_BASIS,
) -> tuple[tuple[int, ...], int]:
    if x2 < x1:
        return (), signature
    position = (((xfrac << 10) & 0xFFFF0000) | ((yfrac >> 6) & 0x0000FFFF)) & 0xFFFFFFFF
    step = (((xstep << 10) & 0xFFFF0000) | ((ystep >> 6) & 0x0000FFFF)) & 0xFFFFFFFF
    colors: list[int] = []
    for _ in range(x2 - x1 + 1):
        ytemp = (position >> 4) & 0x0FC0
        xtemp = position >> 26
        spot = xtemp | ytemp
        color = palette32[source[spot]]
        colors.append(color)
        signature = ((signature * FNV_PRIME) & 0xFFFFFFFF) ^ color
        signature &= 0xFFFFFFFF
        position = (position + step) & 0xFFFFFFFF
    return tuple(colors), signature


def r_map_plane(
    tables: PlaneMappingTables,
    *,
    y: int,
    x1: int,
    x2: int,
    planeheight: int,
    source_index: int,
    source: bytes,
    palette32: Sequence[int],
    signature: int,
    flat_id: int = 0,
    flat_name: str = "",
    plane_kind: str = "",
) -> tuple[Stage11SpanCommand, int, int]:
    if planeheight != tables.cachedheight[y]:
        tables.cachedheight[y] = planeheight
        distance = tables.cacheddistance[y] = stage04.fixed_mul(planeheight, tables.yslope[y])
        tables.cachedxstep[y] = stage04.fixed_mul(distance, tables.basexscale)
        tables.cachedystep[y] = stage04.fixed_mul(distance, tables.baseyscale)
    else:
        distance = tables.cacheddistance[y]

    xstep = tables.cachedxstep[y]
    ystep = tables.cachedystep[y]
    length = stage04.fixed_mul(distance, tables.distscale[x1])
    angle = _fine_index(_u32(VIEW_ANGLE + XTOVIEWANGLE[x1]))
    xfrac = stage04._int32(VIEW_X_FIXED + stage04.fixed_mul(FINECOSINE[angle], length))
    yfrac = stage04._int32(-VIEW_Y_FIXED - stage04.fixed_mul(FINESINE[angle], length))

    command = Stage11SpanCommand(
        y=y,
        x1=x1,
        x2=x2,
        xfrac=xfrac,
        yfrac=yfrac,
        xstep=xstep,
        ystep=ystep,
        source_index=source_index,
        flat_id=flat_id,
        flat_name=flat_name,
        plane_kind=plane_kind,
    )
    colors, signature = r_draw_span_pixels(
        source,
        palette32,
        x1=x1,
        x2=x2,
        xfrac=xfrac,
        yfrac=yfrac,
        xstep=xstep,
        ystep=ystep,
        signature=signature,
    )
    return command, len(colors), signature


def r_make_spans(
    state: VisplaneState,
    x: int,
    t1: int,
    b1: int,
    t2: int,
    b2: int,
    map_plane: Callable[[int, int, int], None],
) -> None:
    while t1 < t2 and t1 <= b1:
        map_plane(t1, state.spanstart[t1], x - 1)
        t1 += 1
    while b1 > b2 and b1 >= t1:
        map_plane(b1, state.spanstart[b1], x - 1)
        b1 -= 1

    while t2 < t1 and t2 <= b2:
        state.spanstart[t2] = x
        t2 += 1
    while b2 > b1 and b2 >= t2:
        state.spanstart[b2] = x
        b2 -= 1


def _line_frontsector_index(
    raw_seg: tuple[int, int, int, int, int, int], loaded: LoadedMap
) -> int:
    line = loaded.linedefs[raw_seg[3]]
    sidedef_index = stage10._line_sidedef_index(line, raw_seg[4])
    return loaded.sidedefs[sidedef_index].sector


def build_visplanes_for_stage10_handoff(
    wad_path: str | Path,
    stage10_ref: stage10.Stage10CompositeTwoSidedWallEdgesReference | None = None,
    *,
    max_visplanes: int = DEFAULT_MAX_VISPLANES,
) -> tuple[VisplaneState, int, int, int, str, int, str]:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    ref = stage10_ref or stage10.reference_composite_two_sided_wall_edges_for_pinned_map(wad_path)
    texture_data = ref.stage09.texture_data
    setup = texture_data.texture_setup
    raw_segs = stage02.parse_mapsegs(wad.read_lump(wad.map_lumps("MAP01").get("SEGS")))
    skyflatnum = stage08.r_flat_num_for_name(wad, setup, "F_SKY1")

    state = VisplaneState(max_visplanes=max_visplanes, skyflatnum=skyflatnum)
    state.clear_planes()

    ceilingclip = [-1] * FRAMEBUFFER_WIDTH
    floorclip = [FRAMEBUFFER_HEIGHT] * FRAMEBUFFER_WIDTH
    ceiling_marks = 0
    floor_marks = 0
    first_floor_flat_id = -1
    first_floor_flat_name = ""
    first_ceiling_flat_id = -1
    first_ceiling_flat_name = ""

    for span in texture_data.projection.projected_spans:
        raw_seg = raw_segs[span.seg_index]
        line = loaded.linedefs[raw_seg[3]]
        sidedef_index = stage10._line_sidedef_index(line, raw_seg[4])
        sidedef = loaded.sidedefs[sidedef_index]
        backsector_index = stage10._line_backsector_index(line, raw_seg[4], loaded)
        if backsector_index is None:
            continue

        frontsector_index = sidedef.sector
        frontsector = loaded.sectors[frontsector_index]
        backsector = loaded.sectors[backsector_index]
        resolved = texture_data.resolved_sidedefs[sidedef_index]
        front_resolved = texture_data.resolved_sectors[frontsector_index]
        back_resolved = texture_data.resolved_sectors[backsector_index]

        floorplane = None
        ceilingplane = None
        front_floor_height = frontsector.floor_height << FRACBITS
        front_ceiling_height = frontsector.ceiling_height << FRACBITS
        if front_floor_height < texture_data.projection.viewz:
            floorplane = state.find_plane(
                front_floor_height,
                front_resolved.floorpic,
                frontsector.light_level,
                "floor",
            )
        if (
            front_ceiling_height > texture_data.projection.viewz
            or front_resolved.ceilingpic == skyflatnum
        ):
            ceilingplane = state.find_plane(
                front_ceiling_height,
                front_resolved.ceilingpic,
                frontsector.light_level,
                "ceiling",
            )

        worldtop = front_ceiling_height - texture_data.projection.viewz
        worldbottom = front_floor_height - texture_data.projection.viewz
        worldhigh = (backsector.ceiling_height << FRACBITS) - texture_data.projection.viewz
        worldlow = (backsector.floor_height << FRACBITS) - texture_data.projection.viewz

        if front_resolved.ceilingpic == skyflatnum and back_resolved.ceilingpic == skyflatnum:
            worldtop = worldhigh

        markfloor = (
            worldlow != worldbottom
            or back_resolved.floorpic != front_resolved.floorpic
            or backsector.light_level != frontsector.light_level
        )
        markceiling = (
            worldhigh != worldtop
            or back_resolved.ceilingpic != front_resolved.ceilingpic
            or backsector.light_level != frontsector.light_level
        )

        if (
            backsector.ceiling_height <= frontsector.floor_height
            or backsector.floor_height >= frontsector.ceiling_height
        ):
            markfloor = True
            markceiling = True

        toptexture = 0
        bottomtexture = 0
        if worldhigh < worldtop:
            toptexture = resolved.toptexture
        if worldlow > worldbottom:
            bottomtexture = resolved.bottomtexture

        if front_floor_height >= texture_data.projection.viewz:
            markfloor = False
        if front_ceiling_height <= texture_data.projection.viewz and front_resolved.ceilingpic != skyflatnum:
            markceiling = False

        if markceiling:
            ceilingplane = state.check_plane(ceilingplane, span.x1, span.x2, "ceiling")
        if markfloor:
            floorplane = state.check_plane(floorplane, span.x1, span.x2, "floor")

        topfrac = (CENTERYFRAC >> 4) - stage07.fixed_mul(worldtop >> 4, span.scale1)
        bottomfrac = (CENTERYFRAC >> 4) - stage07.fixed_mul(worldbottom >> 4, span.scale1)
        topstep = -stage07.fixed_mul(span.scalestep, worldtop >> 4)
        bottomstep = -stage07.fixed_mul(span.scalestep, worldbottom >> 4)
        pixhigh = pixlow = pixhighstep = pixlowstep = 0

        if worldhigh < worldtop:
            pixhigh = (CENTERYFRAC >> 4) - stage07.fixed_mul(worldhigh >> 4, span.scale1)
            pixhighstep = -stage07.fixed_mul(span.scalestep, worldhigh >> 4)
        if worldlow > worldbottom:
            pixlow = (CENTERYFRAC >> 4) - stage07.fixed_mul(worldlow >> 4, span.scale1)
            pixlowstep = -stage07.fixed_mul(span.scalestep, worldlow >> 4)

        for x in range(span.x1, span.x2 + 1):
            clip = stage10.render_seg_loop_edge_clip_column(
                ceilingclip=ceilingclip[x],
                floorclip=floorclip[x],
                topfrac=topfrac,
                bottomfrac=bottomfrac,
                pixhigh=pixhigh,
                pixlow=pixlow,
                pixhighstep=pixhighstep,
                pixlowstep=pixlowstep,
                markceiling=markceiling,
                markfloor=markfloor,
                has_toptexture=bool(toptexture),
                has_bottomtexture=bool(bottomtexture),
            )

            if clip.ceiling_mark is not None and ceilingplane is not None:
                ceilingplane.set_mark(x, clip.ceiling_mark[0], clip.ceiling_mark[1], "ceiling")
                ceiling_marks += 1
                if (
                    first_ceiling_flat_id < 0
                    and ceilingplane.picnum != skyflatnum
                ):
                    first_ceiling_flat_id = ceilingplane.picnum
                    first_ceiling_flat_name = flat_name_for_picnum(wad, setup, ceilingplane.picnum)

            if clip.floor_mark is not None and floorplane is not None:
                floorplane.set_mark(x, clip.floor_mark[0], clip.floor_mark[1], "floor")
                floor_marks += 1
                if first_floor_flat_id < 0 and floorplane.picnum != skyflatnum:
                    first_floor_flat_id = floorplane.picnum
                    first_floor_flat_name = flat_name_for_picnum(wad, setup, floorplane.picnum)

            ceilingclip[x] = clip.ceilingclip
            floorclip[x] = clip.floorclip
            pixhigh = clip.pixhigh_next
            pixlow = clip.pixlow_next
            topfrac += topstep
            bottomfrac += bottomstep

    return (
        state,
        ceiling_marks,
        floor_marks,
        first_floor_flat_id,
        first_floor_flat_name,
        first_ceiling_flat_id,
        first_ceiling_flat_name,
    )


def reference_visplanes_floor_ceiling_for_pinned_map(
    wad_path: str | Path,
    *,
    max_visplanes: int = DEFAULT_MAX_VISPLANES,
    max_span_commands: int = DEFAULT_MAX_FLAT_SPAN_COMMANDS,
) -> Stage11VisplanesFloorCeilingReference:
    wad = WadFile.from_file(wad_path)
    stage10_ref = stage10.reference_composite_two_sided_wall_edges_for_pinned_map(wad_path)
    texture_data = stage10_ref.stage09.texture_data
    setup = texture_data.texture_setup
    palette32 = stage10_ref.palette32
    skyflatnum = stage08.r_flat_num_for_name(wad, setup, "F_SKY1")

    (
        state,
        ceiling_marks,
        floor_marks,
        first_floor_flat_id,
        first_floor_flat_name,
        first_ceiling_flat_id,
        first_ceiling_flat_name,
    ) = build_visplanes_for_stage10_handoff(
        wad_path, stage10_ref, max_visplanes=max_visplanes
    )

    tables = PlaneMappingTables.fixed_view()
    flat_sources: list[bytes] = []
    flat_source_index: dict[int, int] = {}
    commands: list[Stage11SpanCommand] = []
    signature = stage10_ref.framebuffer_signature
    flat_pixels_drawn = 0
    flat_source_skips = 0
    flat_span_overflow_count = 0
    regular_visplanes_drawn = 0
    sky_visplanes_skipped = 0
    sky_columns_skipped = 0
    sky_pixels_skipped = 0

    for plane in state.visplanes:
        if plane.minx > plane.maxx:
            continue

        if plane.picnum == skyflatnum:
            sky_visplanes_skipped += 1
            for x in range(plane.minx, plane.maxx + 1):
                top = plane.top_at(x)
                bottom = plane.bottom_at(x)
                if top <= bottom:
                    sky_columns_skipped += 1
                    sky_pixels_skipped += bottom - top + 1
            continue

        flat_source = flat_data_for_picnum(wad, setup, plane.picnum)
        if flat_source is None:
            flat_source_skips += 1
            continue

        source_index = flat_source_index.get(plane.picnum)
        if source_index is None:
            source_index = len(flat_sources)
            flat_source_index[plane.picnum] = source_index
            flat_sources.append(flat_source)

        regular_visplanes_drawn += 1
        planeheight = abs(plane.height - texture_data.projection.viewz)
        flat_name = flat_name_for_picnum(wad, setup, plane.picnum)
        plane.set_top_sentinel(plane.maxx + 1)
        plane.set_top_sentinel(plane.minx - 1)
        stop = plane.maxx + 1

        def map_plane(y: int, x1: int, x2: int) -> None:
            nonlocal signature, flat_pixels_drawn, flat_span_overflow_count
            if len(commands) >= max_span_commands:
                flat_span_overflow_count += 1
                return
            command, pixels, signature = r_map_plane(
                tables,
                y=y,
                x1=x1,
                x2=x2,
                planeheight=planeheight,
                source_index=source_index,
                source=flat_source,
                palette32=palette32,
                signature=signature,
                flat_id=plane.picnum,
                flat_name=flat_name,
                plane_kind="/".join(sorted(plane.kinds)),
            )
            commands.append(command)
            flat_pixels_drawn += pixels

        for x in range(plane.minx, stop + 1):
            r_make_spans(
                state,
                x,
                plane.top_at(x - 1),
                plane.bottom_at(x - 1),
                plane.top_at(x),
                plane.bottom_at(x),
                map_plane,
            )

    return Stage11VisplanesFloorCeilingReference(
        stage10=stage10_ref,
        palette32=tuple(palette32),
        flat_sources=tuple(flat_sources),
        commands=tuple(commands),
        visplane_count=len(state.visplanes),
        visplane_find_calls=state.find_calls,
        visplane_new_count=state.find_new,
        visplane_reuse_count=state.find_reused,
        visplane_check_calls=state.check_calls,
        visplane_check_reuse_count=state.check_reused,
        visplane_split_count=state.check_splits,
        visplane_overflow_count=state.overflow,
        ceiling_plane_mark_records=ceiling_marks,
        floor_plane_mark_records=floor_marks,
        regular_visplanes_drawn=regular_visplanes_drawn,
        flat_spans_drawn=len(commands),
        flat_pixels_drawn=flat_pixels_drawn,
        flat_source_skips=flat_source_skips,
        flat_span_overflow_count=flat_span_overflow_count,
        sky_visplanes_skipped=sky_visplanes_skipped,
        sky_columns_skipped=sky_columns_skipped,
        sky_pixels_skipped=sky_pixels_skipped,
        first_floor_flat_id=first_floor_flat_id,
        first_floor_flat_name=first_floor_flat_name,
        first_ceiling_flat_id=first_ceiling_flat_id,
        first_ceiling_flat_name=first_ceiling_flat_name,
        framebuffer_signature=signature,
    )


def _reference_for_default_wad_or_none() -> Stage11VisplanesFloorCeilingReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_visplanes_floor_ceiling_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage11_load_wad_visplanes_floor_ceiling_debug")

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


def emit_source_stage11_load_wad_visplanes_floor_ceiling_debug(pe: PE32) -> None:
    pe.label("source_stage11_load_wad_visplanes_floor_ceiling_debug")
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
    x86.jne_rel32(pe, "source_stage11_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage11_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage11_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage11_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage11_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage11_close_and_return")

    pe.label("source_stage11_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage11_close_and_return")

    x86.call_rel32(pe, "render_init_texture_data_setup_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage11_close_and_return")

    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage11_close_and_return")

    x86.call_rel32(pe, "source_stage06_run_live_seg_clip_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage11_close_and_return")

    x86.call_rel32(pe, "render_composite_two_sided_wall_edges_debug")
    x86.call_rel32(pe, "render_visplanes_floor_ceiling_debug")
    x86.call_rel32(pe, "build_success_status")

    pe.label("source_stage11_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_render_visplanes_floor_ceiling_debug(pe: PE32) -> None:
    pe.label("render_visplane_subsector_candidates_debug")
    pe.label("render_clear_planes_source_shape_debug")
    pe.label("render_find_plane_source_shape_debug")
    pe.label("render_check_plane_source_shape_debug")
    pe.label("render_make_spans_source_shape_debug")
    pe.label("render_map_plane_source_shape_debug")
    pe.label("render_draw_planes_source_shape_debug")
    pe.label("stage11_flat_lump_sources_debug")
    pe.label("render_visplanes_floor_ceiling_debug")
    x86.mov_mem_abs32_imm32(pe, "stage11_flat_spans_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage11_flat_pixels_drawn", 0)
    x86.mov_reg_mem_abs32(pe, "eax", "stage10_pixel_signature")
    x86.mov_mem_abs32_eax(pe, "stage11_pixel_signature")
    x86.mov_mem_abs32_abs32(pe, "ds_colormap", "stage11_palette32")

    x86.mov_reg_abs32(pe, "esi", "stage11_span_commands")
    x86.mov_mem_abs32_reg(pe, "stage11_span_scan_ptr", "esi")
    x86.mov_reg_mem_abs32(pe, "eax", "stage11_span_command_count")
    x86.mov_mem_abs32_eax(pe, "stage11_span_remaining_commands")

    pe.label("stage11_span_command_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "stage11_span_remaining_commands")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage11_span_commands_done")

    x86.mov_reg_mem_abs32(pe, "esi", "stage11_span_scan_ptr")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", SPAN_COMMAND_Y)
    x86.mov_mem_abs32_eax(pe, "ds_y")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", SPAN_COMMAND_X1)
    x86.mov_mem_abs32_eax(pe, "ds_x1")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", SPAN_COMMAND_X2)
    x86.mov_mem_abs32_eax(pe, "ds_x2")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", SPAN_COMMAND_XFRAC)
    x86.mov_mem_abs32_eax(pe, "ds_xfrac")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", SPAN_COMMAND_YFRAC)
    x86.mov_mem_abs32_eax(pe, "ds_yfrac")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", SPAN_COMMAND_XSTEP)
    x86.mov_mem_abs32_eax(pe, "ds_xstep")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", SPAN_COMMAND_YSTEP)
    x86.mov_mem_abs32_eax(pe, "ds_ystep")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", SPAN_COMMAND_SOURCE)
    x86.mov_mem_abs32_eax(pe, "ds_source")

    stage07._emit_inc_abs32(pe, "stage11_flat_spans_drawn")
    x86.call_rel32(pe, "render_draw_span_debug")

    x86.mov_reg_mem_abs32(pe, "esi", "stage11_span_scan_ptr")
    x86.add_reg_imm32(pe, "esi", SPAN_COMMAND_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, "stage11_span_scan_ptr", "esi")
    x86.dec_mem_abs32(pe, "stage11_span_remaining_commands")
    x86.jmp_rel32(pe, "stage11_span_command_loop")

    pe.label("stage11_span_commands_done")
    x86.ret(pe)


def emit_render_draw_span_debug(pe: PE32) -> None:
    pe.label("render_draw_span_debug")
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_reg_mem_abs32(pe, "eax", "ds_x2")
    x86.sub_reg_mem_abs32(pe, "eax", "ds_x1")
    x86.jl_rel32(pe, "stage11_draw_span_done")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "stage11_span_remaining_pixels")

    x86.mov_reg_mem_abs32(pe, "ebx", "ds_y")
    x86.mov_reg_reg(pe, "edx", "ebx")
    x86.shl_reg_imm8(pe, "ebx", 8)
    x86.shl_reg_imm8(pe, "edx", 6)
    x86.add_reg_reg(pe, "ebx", "edx")
    x86.add_reg_mem_abs32(pe, "ebx", "ds_x1")
    x86.shl_reg_imm8(pe, "ebx", 2)
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.add_reg_reg(pe, "edi", "ebx")

    x86.mov_reg_mem_abs32(pe, "eax", "ds_xfrac")
    x86.shl_reg_imm8(pe, "eax", 10)
    x86.and_reg_imm32(pe, "eax", 0xFFFF0000)
    x86.mov_reg_mem_abs32(pe, "ebx", "ds_yfrac")
    x86.shr_reg_imm8(pe, "ebx", 6)
    x86.and_reg_imm32(pe, "ebx", 0x0000FFFF)
    x86.add_reg_reg(pe, "eax", "ebx")
    x86.mov_mem_abs32_eax(pe, "ds_position")

    x86.mov_reg_mem_abs32(pe, "eax", "ds_xstep")
    x86.shl_reg_imm8(pe, "eax", 10)
    x86.and_reg_imm32(pe, "eax", 0xFFFF0000)
    x86.mov_reg_mem_abs32(pe, "ebx", "ds_ystep")
    x86.shr_reg_imm8(pe, "ebx", 6)
    x86.and_reg_imm32(pe, "ebx", 0x0000FFFF)
    x86.add_reg_reg(pe, "eax", "ebx")
    x86.mov_mem_abs32_eax(pe, "ds_step")

    pe.label("stage11_draw_span_loop")
    x86.mov_reg_mem_abs32(pe, "ebx", "ds_position")
    x86.mov_reg_reg(pe, "eax", "ebx")
    x86.shr_reg_imm8(pe, "eax", 4)
    x86.and_reg_imm32(pe, "eax", 0x0FC0)
    x86.mov_reg_reg(pe, "edx", "ebx")
    x86.shr_reg_imm8(pe, "edx", 26)
    x86.add_reg_reg(pe, "eax", "edx")
    x86.mov_reg_mem_abs32(pe, "esi", "ds_source")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.movzx_reg_byte_ptr_reg(pe, "eax", "esi")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_mem_abs32(pe, "esi", "ds_colormap")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "esi")
    x86.mov_ptr_reg_eax(pe, "edi")

    x86.mov_reg_mem_abs32(pe, "ecx", "stage11_pixel_signature")
    x86.imul_reg_reg_imm32(pe, "ecx", "ecx", FNV_PRIME)
    x86.xor_reg_reg(pe, "ecx", "eax")
    x86.mov_mem_abs32_reg(pe, "stage11_pixel_signature", "ecx")
    stage07._emit_inc_abs32(pe, "stage11_flat_pixels_drawn")

    x86.add_reg_imm32(pe, "edi", 4)
    x86.mov_reg_mem_abs32(pe, "eax", "ds_position")
    x86.add_reg_mem_abs32(pe, "eax", "ds_step")
    x86.mov_mem_abs32_eax(pe, "ds_position")
    x86.dec_mem_abs32(pe, "stage11_span_remaining_pixels")
    x86.jne_rel32(pe, "stage11_draw_span_loop")

    pe.label("stage11_draw_span_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_build_success_status(pe: PE32) -> None:
    pe.label("build_success_status")
    x86.mov_reg_abs32(pe, "edi", "status_success_buffer")
    stage01.append_c_string_label(pe, "status_stage11_success_header")
    stage01.append_u32_label(pe, "status_clip_nodes_prefix", "clip_visited_node_count")
    stage01.append_u32_label(pe, "status_clip_subsectors_prefix", "clip_visited_subsector_count")
    stage01.append_u32_label(pe, "status_clip_segs_prefix", "clip_visited_seg_count")
    stage01.append_u32_label(pe, "status_stage10_columns_drawn_prefix", "stage10_columns_drawn")
    stage01.append_u32_label(pe, "status_stage10_signature_prefix", "stage10_pixel_signature")
    stage01.append_u32_label(pe, "status_stage11_visplanes_prefix", "stage11_visplane_count")
    stage01.append_u32_label(pe, "status_stage11_spans_prefix", "stage11_flat_spans_drawn")
    stage01.append_u32_label(pe, "status_stage11_pixels_prefix", "stage11_flat_pixels_drawn")
    stage01.append_u32_label(pe, "status_stage11_signature_prefix", "stage11_pixel_signature")
    stage01.append_c_string_label(pe, "status_stage11_note")
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
    stage01.append_u32_label(pe, "title_texture_count_prefix", "stage08_numtextures")
    stage01.append_u32_label(pe, "title_patch_name_count_prefix", "stage08_patch_name_count")
    stage01.append_u32_label(pe, "title_flat_count_prefix", "stage08_numflats")
    stage01.append_u32_label(pe, "title_direct_column_prefix", "stage08_direct_column_count")
    stage01.append_u32_label(pe, "title_composite_column_prefix", "stage08_composite_column_count")
    stage01.append_u32_label(pe, "title_first_projected_texture_prefix", "stage08_first_projected_texture_id")
    stage01.append_u32_label(pe, "title_last_projected_texture_prefix", "stage08_last_projected_texture_id")
    stage01.append_u32_label(pe, "title_empty_midzero_prefix", "clip_empty_line_reject_count")
    stage01.append_u32_label(pe, "title_stage09_span_considered_prefix", "stage09_direct_wall_spans_considered")
    stage01.append_u32_label(pe, "title_stage09_candidate_spans_prefix", "stage09_opaque_candidate_spans")
    stage01.append_u32_label(pe, "title_stage09_columns_attempted_prefix", "stage09_direct_columns_attempted")
    stage01.append_u32_label(pe, "title_stage09_columns_drawn_prefix", "stage09_columns_drawn")
    stage01.append_u32_label(pe, "title_stage09_composite_skip_prefix", "stage09_skipped_composite_columns")
    stage01.append_u32_label(pe, "title_stage09_unsupported_skip_prefix", "stage09_skipped_unsupported_wall_cases")
    stage01.append_u32_label(pe, "title_stage09_texture0_skip_prefix", "stage09_skipped_texture0_spans")
    stage01.append_u32_label(pe, "title_stage09_masked_skip_prefix", "stage09_skipped_masked_midtexture_spans")
    stage01.append_u32_label(pe, "title_stage09_first_texture_id_prefix", "stage09_first_drawn_texture_id")
    stage01.append_c_string_label(pe, "title_stage09_first_texture_name_prefix")
    stage01.append_c_string_label(pe, "stage09_first_drawn_texture_name")
    stage01.append_u32_label(pe, "title_stage09_first_texture_column_prefix", "stage09_first_drawn_texture_column")
    stage01.append_u32_label(pe, "title_stage09_pixels_drawn_prefix", "stage09_pixels_drawn")
    stage01.append_u32_label(pe, "title_stage09_signature_prefix", "stage09_pixel_signature")
    stage01.append_u32_label(pe, "title_stage10_cache_builds_prefix", "stage10_composite_cache_builds")
    stage01.append_u32_label(pe, "title_stage10_cache_hits_prefix", "stage10_composite_cache_hits")
    stage01.append_u32_label(pe, "title_stage10_cache_overflow_prefix", "stage10_composite_cache_overflows")
    stage01.append_u32_label(pe, "title_stage10_mid_composite_drawn_prefix", "stage10_mid_composite_columns_drawn")
    stage01.append_u32_label(pe, "title_stage10_mid_composite_empty_prefix", "stage10_mid_composite_columns_clipped_empty")
    stage01.append_u32_label(pe, "title_stage10_upper_columns_prefix", "stage10_upper_columns_drawn")
    stage01.append_u32_label(pe, "title_stage10_upper_composite_prefix", "stage10_upper_composite_columns_drawn")
    stage01.append_u32_label(pe, "title_stage10_lower_columns_prefix", "stage10_lower_columns_drawn")
    stage01.append_u32_label(pe, "title_stage10_plane_mark_prefix", "stage10_plane_mark_records")
    stage01.append_u32_label(pe, "title_stage10_first_texture_id_prefix", "stage10_first_drawn_texture_id")
    stage01.append_c_string_label(pe, "title_stage10_first_texture_name_prefix")
    stage01.append_c_string_label(pe, "stage10_first_drawn_texture_name")
    stage01.append_u32_label(pe, "title_stage10_last_texture_id_prefix", "stage10_last_drawn_texture_id")
    stage01.append_c_string_label(pe, "title_stage10_last_texture_name_prefix")
    stage01.append_c_string_label(pe, "stage10_last_drawn_texture_name")
    stage01.append_u32_label(pe, "title_stage10_columns_drawn_prefix", "stage10_columns_drawn")
    stage01.append_u32_label(pe, "title_stage10_pixels_drawn_prefix", "stage10_pixels_drawn")
    stage01.append_u32_label(pe, "title_stage10_signature_prefix", "stage10_pixel_signature")
    stage01.append_u32_label(pe, "title_stage11_visplane_prefix", "stage11_visplane_count")
    stage01.append_u32_label(pe, "title_stage11_visplane_new_prefix", "stage11_visplane_new_count")
    stage01.append_u32_label(pe, "title_stage11_visplane_reuse_prefix", "stage11_visplane_reuse_count")
    stage01.append_u32_label(pe, "title_stage11_visplane_split_prefix", "stage11_visplane_split_count")
    stage01.append_u32_label(pe, "title_stage11_visplane_overflow_prefix", "stage11_visplane_overflow_count")
    stage01.append_u32_label(pe, "title_stage11_ceiling_marks_prefix", "stage11_ceiling_plane_mark_records")
    stage01.append_u32_label(pe, "title_stage11_floor_marks_prefix", "stage11_floor_plane_mark_records")
    stage01.append_u32_label(pe, "title_stage11_flat_spans_prefix", "stage11_flat_spans_drawn")
    stage01.append_u32_label(pe, "title_stage11_flat_pixels_prefix", "stage11_flat_pixels_drawn")
    stage01.append_u32_label(pe, "title_stage11_sky_visplanes_prefix", "stage11_sky_visplanes_skipped")
    stage01.append_u32_label(pe, "title_stage11_sky_columns_prefix", "stage11_sky_columns_skipped")
    stage01.append_u32_label(pe, "title_stage11_sky_pixels_prefix", "stage11_sky_pixels_skipped")
    stage01.append_u32_label(pe, "title_stage11_flat_source_skips_prefix", "stage11_flat_source_skips")
    stage01.append_u32_label(pe, "title_stage11_span_overflow_prefix", "stage11_flat_span_overflow_count")
    stage01.append_u32_label(pe, "title_stage11_first_floor_flat_id_prefix", "stage11_first_floor_flat_id")
    stage01.append_c_string_label(pe, "title_stage11_first_floor_flat_name_prefix")
    stage01.append_c_string_label(pe, "stage11_first_floor_flat_name")
    stage01.append_u32_label(pe, "title_stage11_first_ceiling_flat_id_prefix", "stage11_first_ceiling_flat_id")
    stage01.append_c_string_label(pe, "title_stage11_first_ceiling_flat_name_prefix")
    stage01.append_c_string_label(pe, "stage11_first_ceiling_flat_name")
    stage01.append_u32_label(pe, "title_stage11_signature_prefix", "stage11_pixel_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def _emit_u32_table(pe: PE32, label: str, values: Sequence[int]) -> None:
    pe.label(label)
    for value in values:
        pe.emit_u32(value & 0xFFFFFFFF)


def emit_stage11_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()

    pe.align_section(4)
    pe.label("stage11_visplane_count")
    pe.emit_u32(ref.visplane_count if ref is not None else 0)
    pe.label("stage11_visplane_find_calls")
    pe.emit_u32(ref.visplane_find_calls if ref is not None else 0)
    pe.label("stage11_visplane_new_count")
    pe.emit_u32(ref.visplane_new_count if ref is not None else 0)
    pe.label("stage11_visplane_reuse_count")
    pe.emit_u32(ref.visplane_reuse_count if ref is not None else 0)
    pe.label("stage11_visplane_check_calls")
    pe.emit_u32(ref.visplane_check_calls if ref is not None else 0)
    pe.label("stage11_visplane_check_reuse_count")
    pe.emit_u32(ref.visplane_check_reuse_count if ref is not None else 0)
    pe.label("stage11_visplane_split_count")
    pe.emit_u32(ref.visplane_split_count if ref is not None else 0)
    pe.label("stage11_visplane_overflow_count")
    pe.emit_u32(ref.visplane_overflow_count if ref is not None else 0)
    pe.label("stage11_ceiling_plane_mark_records")
    pe.emit_u32(ref.ceiling_plane_mark_records if ref is not None else 0)
    pe.label("stage11_floor_plane_mark_records")
    pe.emit_u32(ref.floor_plane_mark_records if ref is not None else 0)
    pe.label("stage11_regular_visplanes_drawn")
    pe.emit_u32(ref.regular_visplanes_drawn if ref is not None else 0)
    pe.label("stage11_expected_flat_spans_drawn")
    pe.emit_u32(ref.flat_spans_drawn if ref is not None else 0)
    pe.label("stage11_expected_flat_pixels_drawn")
    pe.emit_u32(ref.flat_pixels_drawn if ref is not None else 0)
    pe.label("stage11_flat_source_skips")
    pe.emit_u32(ref.flat_source_skips if ref is not None else 0)
    pe.label("stage11_flat_span_overflow_count")
    pe.emit_u32(ref.flat_span_overflow_count if ref is not None else 0)
    pe.label("stage11_sky_visplanes_skipped")
    pe.emit_u32(ref.sky_visplanes_skipped if ref is not None else 0)
    pe.label("stage11_sky_columns_skipped")
    pe.emit_u32(ref.sky_columns_skipped if ref is not None else 0)
    pe.label("stage11_sky_pixels_skipped")
    pe.emit_u32(ref.sky_pixels_skipped if ref is not None else 0)
    pe.label("stage11_first_floor_flat_id")
    pe.emit_u32(ref.first_floor_flat_id if ref is not None and ref.first_floor_flat_id >= 0 else 0)
    pe.label("stage11_first_ceiling_flat_id")
    pe.emit_u32(ref.first_ceiling_flat_id if ref is not None and ref.first_ceiling_flat_id >= 0 else 0)
    pe.label("stage11_expected_pixel_signature")
    pe.emit_u32(ref.framebuffer_signature if ref is not None else 0)
    pe.label("stage11_span_command_count")
    pe.emit_u32(len(ref.commands) if ref is not None else 0)

    pe.label("stage11_flat_spans_drawn")
    pe.emit_u32(0)
    pe.label("stage11_flat_pixels_drawn")
    pe.emit_u32(0)
    pe.label("stage11_pixel_signature")
    pe.emit_u32(0)
    pe.label("stage11_span_scan_ptr")
    pe.emit_u32(0)
    pe.label("stage11_span_remaining_commands")
    pe.emit_u32(0)
    pe.label("stage11_span_remaining_pixels")
    pe.emit_u32(0)
    pe.label("ds_y")
    pe.emit_u32(0)
    pe.label("ds_x1")
    pe.emit_u32(0)
    pe.label("ds_x2")
    pe.emit_u32(0)
    pe.label("ds_xfrac")
    pe.emit_u32(0)
    pe.label("ds_yfrac")
    pe.emit_u32(0)
    pe.label("ds_xstep")
    pe.emit_u32(0)
    pe.label("ds_ystep")
    pe.emit_u32(0)
    pe.label("ds_source")
    pe.emit_u32(0)
    pe.label("ds_colormap")
    pe.emit_u32(0)
    pe.label("ds_position")
    pe.emit_u32(0)
    pe.label("ds_step")
    pe.emit_u32(0)

    _emit_u32_table(pe, "stage11_palette32", list(ref.palette32) if ref is not None else [0] * 256)

    pe.align_section(4)
    pe.label("stage11_span_commands")
    if ref is not None:
        for command in ref.commands:
            pe.emit_u32(command.y)
            pe.emit_u32(command.x1)
            pe.emit_u32(command.x2)
            pe.emit_u32(command.xfrac)
            pe.emit_u32(command.yfrac)
            pe.emit_u32(command.xstep)
            pe.emit_u32(command.ystep)
            pe.write_abs32(f"stage11_flat_source_{command.source_index}")

    pe.align_section(1)
    if ref is not None:
        for index, pixels in enumerate(ref.flat_sources):
            pe.label(f"stage11_flat_source_{index}")
            pe.emit(pixels)

    pe.align_section(1)
    pe.label("stage11_first_floor_flat_name")
    x86.emit_asciiz(pe, ref.first_floor_flat_name if ref is not None else "")
    pe.label("stage11_first_ceiling_flat_name")
    x86.emit_asciiz(pe, ref.first_ceiling_flat_name if ref is not None else "")

    pe.label("status_stage11_success_header")
    x86.emit_asciiz(
        pe,
        "source_stage11_visplanes_floor_ceiling_debug\r\n"
        "Visplane regular flat span debug OK\r\n",
    )
    pe.label("status_stage11_visplanes_prefix")
    x86.emit_asciiz(pe, "\r\nR_FindPlane/R_CheckPlane visplanes: ")
    pe.label("status_stage11_spans_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime R_DrawSpan flat spans: ")
    pe.label("status_stage11_pixels_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime regular flat pixels: ")
    pe.label("status_stage11_signature_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime wall+flat RGB signature: ")
    pe.label("status_stage11_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage11 follows R_ClearPlanes, R_FindPlane, R_CheckPlane, "
        "R_MakeSpans, R_MapPlane, R_DrawPlanes, and R_DrawSpan over bounded "
        "visplanes, draws regular 64x64 WAD flat spans, and counts sky ceilings "
        "as skipped.\r\n",
    )

    pe.label("title_stage11_visplane_prefix")
    x86.emit_asciiz(pe, " VP=")
    pe.label("title_stage11_visplane_new_prefix")
    x86.emit_asciiz(pe, " VPF=")
    pe.label("title_stage11_visplane_reuse_prefix")
    x86.emit_asciiz(pe, " VPR=")
    pe.label("title_stage11_visplane_split_prefix")
    x86.emit_asciiz(pe, " VPS=")
    pe.label("title_stage11_visplane_overflow_prefix")
    x86.emit_asciiz(pe, " VPO=")
    pe.label("title_stage11_ceiling_marks_prefix")
    x86.emit_asciiz(pe, " CPM=")
    pe.label("title_stage11_floor_marks_prefix")
    x86.emit_asciiz(pe, " FPM=")
    pe.label("title_stage11_flat_spans_prefix")
    x86.emit_asciiz(pe, " FSP=")
    pe.label("title_stage11_flat_pixels_prefix")
    x86.emit_asciiz(pe, " FPIX=")
    pe.label("title_stage11_sky_visplanes_prefix")
    x86.emit_asciiz(pe, " SKYV=")
    pe.label("title_stage11_sky_columns_prefix")
    x86.emit_asciiz(pe, " SKYC=")
    pe.label("title_stage11_sky_pixels_prefix")
    x86.emit_asciiz(pe, " SKYP=")
    pe.label("title_stage11_flat_source_skips_prefix")
    x86.emit_asciiz(pe, " FSK=")
    pe.label("title_stage11_span_overflow_prefix")
    x86.emit_asciiz(pe, " SPO=")
    pe.label("title_stage11_first_floor_flat_id_prefix")
    x86.emit_asciiz(pe, " F11F=")
    pe.label("title_stage11_first_floor_flat_name_prefix")
    x86.emit_asciiz(pe, " F11FN=")
    pe.label("title_stage11_first_ceiling_flat_id_prefix")
    x86.emit_asciiz(pe, " C11F=")
    pe.label("title_stage11_first_ceiling_flat_name_prefix")
    x86.emit_asciiz(pe, " C11N=")
    pe.label("title_stage11_signature_prefix")
    x86.emit_asciiz(pe, " FSIG=")


def build_source_stage11_visplanes_floor_ceiling_debug_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage11_load_wad_visplanes_floor_ceiling_debug(pe)
    stage08.emit_render_init_texture_data_setup_debug(pe)
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
    stage07.emit_source_stage06_run_live_seg_clip_debug(pe)
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
    stage07.emit_render_angle_to_view_x_debug(pe)
    stage07.emit_render_setup_frame_debug(pe)
    stage07.emit_render_fixed_div(pe)
    stage07.emit_render_point_to_dist(pe)
    stage07.emit_render_scale_from_global_angle(pe)
    stage07.emit_render_store_wall_range_debug(pe)
    stage07.emit_render_clip_solid_wall_segment(pe)
    stage07.emit_render_clip_pass_wall_segment(pe)
    stage08.emit_render_add_line_debug(pe)
    stage07.emit_render_debug_subsector_clip(pe)
    stage07.emit_render_bsp_node_clip_debug(pe)
    stage07.emit_render_finish_clip_debug(pe)
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
    stage10.emit_render_composite_two_sided_wall_edges_debug(pe)
    stage10.emit_render_draw_column_debug(pe)
    emit_render_visplanes_floor_ceiling_debug(pe)
    emit_render_draw_span_debug(pe)
    emit_build_success_status(pe)
    stage01.emit_append_c_string(pe)
    stage01.emit_append_u32_decimal(pe)
    stage01.emit_append_i32_decimal(pe)
    with patched_stage01_window_labels():
        stage01.emit_data(pe)
    stage02.emit_stage02_data(pe)
    stage04.emit_stage04_data(pe)
    stage07.emit_stage07_data(pe)
    stage08.emit_stage08_data(pe)
    stage10.emit_stage10_data(pe)
    emit_stage11_data(pe)
    return pe.build("entry")


def write_source_stage11_visplanes_floor_ceiling_debug_exe(path: str | Path) -> bytes:
    image = build_source_stage11_visplanes_floor_ceiling_debug_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the source-guided PE32 x86 visplane floor/ceiling debug executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/source_stage11_visplanes_floor_ceiling_debug.exe",
        help="path to write, default: build/source_stage11_visplanes_floor_ceiling_debug.exe",
    )
    args = parser.parse_args()
    write_source_stage11_visplanes_floor_ceiling_debug_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
