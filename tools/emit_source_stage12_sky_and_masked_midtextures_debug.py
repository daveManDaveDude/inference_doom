from __future__ import annotations

import argparse
import math
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Sequence


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
from tools import emit_source_stage11_visplanes_floor_ceiling_debug as stage11
from tools import x86
from tools.map_loader import LineDef, LoadedMap, NO_SIDEDEF, SideDef, load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


FRAMEBUFFER_WIDTH = stage11.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage11.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage11.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage11.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage11.WINDOW_WIDTH
WINDOW_HEIGHT = stage11.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage12SkyMaskedMidtexturesDebug"
WINDOW_TITLE = "Inference Doom S12 Sky Masked"
WAD_PATH = stage11.WAD_PATH

FRACBITS = stage11.FRACBITS
FRACUNIT = stage11.FRACUNIT
VIEWHEIGHT = 41
ANG90 = stage07.ANG90
ANG180 = stage09.ANG180
CLIPANGLE = stage07.CLIPANGLE
ANGLETOFINESHIFT = stage07.ANGLETOFINESHIFT
ANGLETOSKYSHIFT = 22
FINEMASK = stage11.FINEMASK
FINESINE = stage07.FINESINE
FINECOSINE = stage07.FINECOSINE
FINETANGENT = stage04.FINETANGENT
XTOVIEWANGLE = stage04.XTOVIEWANGLE
CENTER_Y = stage10.CENTER_Y
CENTERYFRAC = stage10.CENTERYFRAC
WALL_COLUMN_SOURCE_HEIGHT = stage09.WALL_COLUMN_SOURCE_HEIGHT
FNV_OFFSET_BASIS = stage10.FNV_OFFSET_BASIS
FNV_PRIME = stage10.FNV_PRIME
SHRT_MAX = 0x7FFF

COLUMN_COMMAND_X = 0
COLUMN_COMMAND_YL = 4
COLUMN_COMMAND_YH = 8
COLUMN_COMMAND_ISCALE = 12
COLUMN_COMMAND_TEXTUREMID = 16
COLUMN_COMMAND_SOURCE = 20
COLUMN_COMMAND_RECORD_SIZE = 24

PROBE_NORMAL_OFFSET = 16
PROBE_SKY_X1 = 8
PROBE_SKY_X2 = 39
PROBE_SKY_YL = 8
PROBE_SKY_YH = 47
PROBE_MASKED_X1 = 48
PROBE_MASKED_X2 = 79
PROBE_MASKED_CEILING_CLIP = 63
PROBE_MASKED_FLOOR_CLIP = 160
DEFAULT_MAX_MASKED_OPENINGS = 256

SOURCE_TRACE = stage11.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/r_sky.c",
        "R_InitSkyMap",
        "render_init_sky_map_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/g_game.c",
        "Doom II MAP01 F_SKY1/SKY1 selection",
        "render_debug_map01_sky_selection",
    ),
    (
        "reference/chocolate-doom/src/doom/r_plane.c",
        "R_DrawPlanes sky branch",
        "render_draw_planes_sky_branch_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_segs.c",
        "R_StoreWallRange masked midtexture setup",
        "render_store_masked_midtexture_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_segs.c",
        "R_RenderSegLoop maskedtexturecol writes",
        "render_maskedtexturecol_openings_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_segs.c",
        "R_RenderMaskedSegRange",
        "render_masked_seg_range_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_things.c",
        "R_DrawMaskedColumn",
        "render_draw_masked_column_debug",
    ),
)


@dataclass(frozen=True)
class SkySectorCandidate:
    sector_index: int
    ceiling_flat_name: str
    ceiling_pic: int


@dataclass(frozen=True)
class MaskedSidedefCandidate:
    linedef_index: int
    side: int
    sidedef_index: int
    sector_index: int
    texture_id: int
    texture_name: str
    raw_seg_index: int | None
    v1x: int
    v1y: int
    v2x: int
    v2y: int

    @property
    def side_name(self) -> str:
        return "right" if self.side == 0 else "left"


@dataclass(frozen=True)
class FeatureProbeSelection:
    uses_probe: bool
    sky_sector: SkySectorCandidate | None
    masked: MaskedSidedefCandidate | None
    view_x: int
    view_y: int
    view_angle: int
    view_angle_degrees: int
    view_sector: int


@dataclass
class MaskedTextureColumnStore:
    width: int
    max_openings: int = DEFAULT_MAX_MASKED_OPENINGS
    columns: list[int] | None = None
    stored_count: int = 0
    overflow_count: int = 0
    clipped_count: int = 0

    def __post_init__(self) -> None:
        if self.columns is None:
            self.columns = [SHRT_MAX] * self.width

    def store(self, x: int, texturecolumn: int) -> bool:
        if self.columns is None:
            raise AssertionError("columns not initialized")
        if x < 0 or x >= self.width:
            self.clipped_count += 1
            return False
        if self.stored_count >= self.max_openings:
            self.overflow_count += 1
            return False
        self.columns[x] = texturecolumn
        self.stored_count += 1
        return True

    def consume(self, x: int) -> int:
        if self.columns is None:
            raise AssertionError("columns not initialized")
        value = self.columns[x]
        self.columns[x] = SHRT_MAX
        return value


@dataclass(frozen=True)
class Stage12ColumnCommand:
    x: int
    yl: int
    yh: int
    iscale: int
    texturemid: int
    source_index: int
    tier: str
    texture_id: int
    texture_name: str
    texture_column: int


@dataclass(frozen=True)
class ProbeMaskedProjection:
    x1: int
    x2: int
    scale1: int
    scale2: int
    scalestep: int
    rw_distance: int
    rw_offset: int
    rw_centerangle: int
    texturemid: int
    viewz: int


@dataclass(frozen=True)
class Stage12SkyMaskedReference:
    stage11: stage11.Stage11VisplanesFloorCeilingReference
    palette32: tuple[int, ...]
    column_sources: tuple[bytes, ...]
    sky_commands: tuple[Stage12ColumnCommand, ...]
    masked_commands: tuple[Stage12ColumnCommand, ...]
    sky_sector_candidates: tuple[SkySectorCandidate, ...]
    masked_sidedef_candidates: tuple[MaskedSidedefCandidate, ...]
    probe: FeatureProbeSelection
    skyflatnum: int
    skytexture: int
    skytexturemid: int
    primary_sky_columns: int
    primary_masked_columns: int
    sky_visplanes_drawn: int
    sky_columns_drawn: int
    sky_pixels_drawn: int
    masked_segments_considered: int
    masked_columns_stored: int
    masked_columns_drawn: int
    masked_post_commands_drawn: int
    masked_pixels_drawn: int
    masked_opening_overflow_count: int
    masked_column_source_skips: int
    skipped_sprite_count: int
    first_sky_texture_id: int
    first_sky_texture_name: str
    first_sky_texture_column: int
    first_masked_texture_id: int
    first_masked_texture_name: str
    first_masked_texture_column: int
    framebuffer_signature: int


def _u32(value: int) -> int:
    return value & 0xFFFFFFFF


def _fine_index(angle: int) -> int:
    return (_u32(angle) >> ANGLETOFINESHIFT) & FINEMASK


def _angle_degrees(angle: int) -> int:
    return int(round((_u32(angle) * 360.0) / 4294967296.0)) % 360


def skytexturemid_for_view_height(height: int = FRAMEBUFFER_HEIGHT) -> int:
    return (height // 2) * FRACUNIT


def sky_texture_column(viewangle: int, x: int) -> int:
    return _u32(viewangle + XTOVIEWANGLE[x]) >> ANGLETOSKYSHIFT


def find_sky_sector_candidates(
    loaded: LoadedMap,
    resolved_sectors: Sequence[stage08.ResolvedSectorFlats],
    skyflatnum: int,
) -> tuple[SkySectorCandidate, ...]:
    candidates: list[SkySectorCandidate] = []
    for index, sector in enumerate(loaded.sectors):
        if resolved_sectors[index].ceilingpic == skyflatnum:
            candidates.append(
                SkySectorCandidate(
                    sector_index=index,
                    ceiling_flat_name=sector.ceiling_flat,
                    ceiling_pic=resolved_sectors[index].ceilingpic,
                )
            )
    return tuple(candidates)


def _raw_seg_index_by_line_side(
    raw_segs: Sequence[tuple[int, int, int, int, int, int]]
) -> dict[tuple[int, int], int]:
    result: dict[tuple[int, int], int] = {}
    for index, raw_seg in enumerate(raw_segs):
        result.setdefault((raw_seg[3], raw_seg[4]), index)
    return result


def find_two_sided_masked_sidedef_candidates(
    loaded: LoadedMap,
    resolved_sidedefs: Sequence[stage08.ResolvedSideDefTextures],
    setup: stage08.TextureSetup,
    raw_segs: Sequence[tuple[int, int, int, int, int, int]] = (),
) -> tuple[MaskedSidedefCandidate, ...]:
    seg_index_by_line_side = _raw_seg_index_by_line_side(raw_segs)
    candidates: list[MaskedSidedefCandidate] = []
    for linedef_index, line in enumerate(loaded.linedefs):
        if not (line.flags & stage08.ML_TWOSIDED):
            continue

        for side, sidedef_index in ((0, line.right_sidedef), (1, line.left_sidedef)):
            if sidedef_index == NO_SIDEDEF or sidedef_index >= len(loaded.sidedefs):
                continue
            resolved = resolved_sidedefs[sidedef_index]
            if resolved.midtexture == 0:
                continue

            texture = setup.textures[resolved.midtexture]
            v1 = loaded.vertices[line.start_vertex]
            v2 = loaded.vertices[line.end_vertex]
            candidates.append(
                MaskedSidedefCandidate(
                    linedef_index=linedef_index,
                    side=side,
                    sidedef_index=sidedef_index,
                    sector_index=loaded.sidedefs[sidedef_index].sector,
                    texture_id=resolved.midtexture,
                    texture_name=texture.name,
                    raw_seg_index=seg_index_by_line_side.get((linedef_index, side)),
                    v1x=v1.x,
                    v1y=v1.y,
                    v2x=v2.x,
                    v2y=v2.y,
                )
            )
    return tuple(candidates)


def _probe_view_for_masked_candidate(
    candidate: MaskedSidedefCandidate,
) -> tuple[int, int, int, int]:
    dx = candidate.v2x - candidate.v1x
    dy = candidate.v2y - candidate.v1y
    length = math.hypot(dx, dy)
    if length == 0:
        view_x = candidate.v1x
        view_y = candidate.v1y
    else:
        if candidate.side == 0:
            normal_x = dy / length
            normal_y = -dx / length
        else:
            normal_x = -dy / length
            normal_y = dx / length
        mid_x = (candidate.v1x + candidate.v2x) / 2.0
        mid_y = (candidate.v1y + candidate.v2y) / 2.0
        view_x = round(mid_x + normal_x * PROBE_NORMAL_OFFSET)
        view_y = round(mid_y + normal_y * PROBE_NORMAL_OFFSET)

    target_x = round((candidate.v1x + candidate.v2x) / 2.0)
    target_y = round((candidate.v1y + candidate.v2y) / 2.0)
    angle = stage04.point_to_angle(
        target_x << FRACBITS,
        target_y << FRACBITS,
        viewx=view_x << FRACBITS,
        viewy=view_y << FRACBITS,
    )
    return view_x, view_y, angle, _angle_degrees(angle)


def select_feature_probe(
    sky_candidates: Sequence[SkySectorCandidate],
    masked_candidates: Sequence[MaskedSidedefCandidate],
    *,
    primary_sky_columns: int,
    primary_masked_columns: int,
) -> FeatureProbeSelection:
    if primary_sky_columns or primary_masked_columns:
        return FeatureProbeSelection(False, None, None, 0, 0, 0, 0, -1)
    if not sky_candidates or not masked_candidates:
        return FeatureProbeSelection(False, None, None, 0, 0, 0, 0, -1)

    masked = next(
        (candidate for candidate in masked_candidates if candidate.texture_name == "AQMETL29"),
        masked_candidates[0],
    )
    view_x, view_y, view_angle, view_angle_degrees = _probe_view_for_masked_candidate(masked)
    return FeatureProbeSelection(
        uses_probe=True,
        sky_sector=sky_candidates[0],
        masked=masked,
        view_x=view_x,
        view_y=view_y,
        view_angle=view_angle,
        view_angle_degrees=view_angle_degrees,
        view_sector=masked.sector_index,
    )


def _line_sidedef_index(line: LineDef, side: int) -> int:
    return line.right_sidedef if side == 0 else line.left_sidedef


def _line_backsector_index(line: LineDef, side: int, loaded: LoadedMap) -> int | None:
    return stage10._line_backsector_index(line, side, loaded)


def _project_masked_candidate(
    loaded: LoadedMap,
    raw_seg: tuple[int, int, int, int, int, int],
    candidate: MaskedSidedefCandidate,
    setup: stage08.TextureSetup,
    *,
    view_x: int,
    view_y: int,
    view_angle: int,
) -> ProbeMaskedProjection | None:
    v1 = loaded.vertices[raw_seg[0]]
    v2 = loaded.vertices[raw_seg[1]]
    viewx_fixed = view_x << FRACBITS
    viewy_fixed = view_y << FRACBITS
    angle1 = stage04.point_to_angle(v1.x << FRACBITS, v1.y << FRACBITS, viewx=viewx_fixed, viewy=viewy_fixed)
    angle2 = stage04.point_to_angle(v2.x << FRACBITS, v2.y << FRACBITS, viewx=viewx_fixed, viewy=viewy_fixed)
    span = _u32(angle1 - angle2)
    if span >= ANG180:
        return None

    rel1 = _u32(angle1 - view_angle)
    rel2 = _u32(angle2 - view_angle)
    two_clipangle = CLIPANGLE * 2

    tspan = _u32(rel1 + CLIPANGLE)
    if tspan > two_clipangle:
        tspan = _u32(tspan - two_clipangle)
        if tspan >= span:
            return None
        rel1 = CLIPANGLE

    tspan = _u32(CLIPANGLE - rel2)
    if tspan > two_clipangle:
        tspan = _u32(tspan - two_clipangle)
        if tspan >= span:
            return None
        rel2 = _u32(-CLIPANGLE)

    screen_x1 = stage07.angle_to_view_x(rel1)
    screen_x2 = stage07.angle_to_view_x(rel2) - 1
    if screen_x1 > screen_x2:
        return None

    rw_angle1 = stage04.point_to_angle(
        v1.x << FRACBITS,
        v1.y << FRACBITS,
        viewx=viewx_fixed,
        viewy=viewy_fixed,
    )
    rw_normalangle = _u32((raw_seg[2] << FRACBITS) + ANG90)
    offsetangle = abs(stage04._int32(rw_normalangle) - stage04._int32(rw_angle1))
    if offsetangle > ANG90:
        offsetangle = ANG90

    distangle = ANG90 - offsetangle
    hyp = stage07.point_to_dist(v1.x << FRACBITS, v1.y << FRACBITS, viewx=viewx_fixed, viewy=viewy_fixed)
    rw_distance = stage07.fixed_mul(hyp, FINESINE[stage07.fine_index(distangle)])

    scale1 = stage07.scale_from_global_angle(
        _u32(view_angle + XTOVIEWANGLE[screen_x1]),
        rw_normalangle,
        rw_distance,
        viewangle=view_angle,
    )
    scale2 = stage07.scale_from_global_angle(
        _u32(view_angle + XTOVIEWANGLE[screen_x2]),
        rw_normalangle,
        rw_distance,
        viewangle=view_angle,
    )
    scalestep = stage04._c_div(scale2 - scale1, screen_x2 - screen_x1) if screen_x2 > screen_x1 else 0

    raw_offsetangle = _u32(rw_normalangle - rw_angle1)
    texture_offsetangle = raw_offsetangle
    if texture_offsetangle > ANG180:
        texture_offsetangle = _u32(-texture_offsetangle)
    if texture_offsetangle > ANG90:
        texture_offsetangle = ANG90

    sidedef = loaded.sidedefs[candidate.sidedef_index]
    rw_offset = stage07.fixed_mul(hyp, FINESINE[_fine_index(texture_offsetangle)])
    if raw_offsetangle < ANG180:
        rw_offset = -rw_offset
    rw_offset += (sidedef.x_offset << FRACBITS) + (raw_seg[5] << FRACBITS)
    rw_centerangle = _u32(ANG90 + view_angle - rw_normalangle)

    line = loaded.linedefs[candidate.linedef_index]
    backsector_index = _line_backsector_index(line, candidate.side, loaded)
    if backsector_index is None:
        return None
    frontsector = loaded.sectors[candidate.sector_index]
    backsector = loaded.sectors[backsector_index]
    texture = setup.textures[candidate.texture_id]
    viewz = (frontsector.floor_height + VIEWHEIGHT) << FRACBITS
    if line.flags & stage10.ML_DONTPEGBOTTOM:
        texturemid = (max(frontsector.floor_height, backsector.floor_height) << FRACBITS) + texture.textureheight - viewz
    else:
        texturemid = (min(frontsector.ceiling_height, backsector.ceiling_height) << FRACBITS) - viewz
    texturemid += sidedef.y_offset << FRACBITS

    return ProbeMaskedProjection(
        x1=screen_x1,
        x2=screen_x2,
        scale1=scale1,
        scale2=scale2,
        scalestep=scalestep,
        rw_distance=rw_distance,
        rw_offset=rw_offset,
        rw_centerangle=rw_centerangle,
        texturemid=texturemid,
        viewz=viewz,
    )


def texture_column_for_x(
    projection: ProbeMaskedProjection,
    x: int,
) -> int:
    angle = _fine_index(_u32(projection.rw_centerangle + XTOVIEWANGLE[x]))
    return (
        projection.rw_offset
        - stage07.fixed_mul(FINETANGENT[angle], projection.rw_distance)
    ) >> FRACBITS


def _column_lookup_source(
    wad: WadFile,
    setup: stage08.TextureSetup,
    texture_id: int,
    texture_column: int,
    composite_cache: stage10.CompositeColumnCache,
    direct_cache: dict[tuple[int, int], bytes],
) -> tuple[int, bytes] | None:
    lookup = stage10.r_get_column_direct_or_composite(
        wad,
        setup,
        texture_id,
        texture_column,
        composite_cache,
        direct_cache,
    )
    if lookup.pixels is None or lookup.skip_reason is not None:
        return None
    return lookup.texture_column, lookup.pixels


def _masked_column_posts(
    wad: WadFile,
    setup: stage08.TextureSetup,
    texture_id: int,
    texture_column: int,
) -> tuple[int, tuple[stage09.PatchColumnPost, ...]] | None:
    texture = setup.textures[texture_id]
    wrapped = texture_column & texture.texturewidthmask
    lump = texture.texturecolumnlump[wrapped]
    if lump <= 0:
        return None
    patch_lump = wad.lumps[lump]
    patch_data = wad.read_lump(patch_lump)
    wanted_column_offset = texture.texturecolumnofs[wrapped] - 3
    header = stage08.parse_patch_header(patch_data, lump_name=patch_lump.name)
    try:
        patch_column = header.column_offsets.index(wanted_column_offset)
    except ValueError:
        return None
    return wrapped, stage09.parse_patch_column_posts(patch_data, patch_column, lump_name=patch_lump.name)


def _padded_source(pixels: bytes, height: int = WALL_COLUMN_SOURCE_HEIGHT) -> bytes:
    if len(pixels) >= height:
        return pixels[:height]
    return pixels + bytes(height - len(pixels))


def masked_post_draw_commands(
    posts: Sequence[stage09.PatchColumnPost],
    *,
    x: int,
    texture_id: int,
    texture_name: str,
    texture_column: int,
    sprtopscreen: int,
    spryscale: int,
    dc_texturemid: int,
    mfloorclip: int,
    mceilingclip: int,
    source_index_for_pixels,
) -> tuple[Stage12ColumnCommand, ...]:
    commands: list[Stage12ColumnCommand] = []
    if spryscale <= 0:
        return ()
    dc_iscale = 0xFFFFFFFF // spryscale
    for post in posts:
        topscreen = sprtopscreen + spryscale * post.topdelta
        bottomscreen = topscreen + spryscale * len(post.pixels)
        yl = (topscreen + FRACUNIT - 1) >> FRACBITS
        yh = (bottomscreen - 1) >> FRACBITS
        if yh >= mfloorclip:
            yh = mfloorclip - 1
        if yl <= mceilingclip:
            yl = mceilingclip + 1
        if yl <= yh:
            source_index = source_index_for_pixels(_padded_source(post.pixels))
            commands.append(
                Stage12ColumnCommand(
                    x=x,
                    yl=yl,
                    yh=yh,
                    iscale=dc_iscale,
                    texturemid=dc_texturemid - (post.topdelta << FRACBITS),
                    source_index=source_index,
                    tier="masked",
                    texture_id=texture_id,
                    texture_name=texture_name,
                    texture_column=texture_column,
                )
            )
    return tuple(commands)


def _append_signature_for_command(
    signature: int,
    command: Stage12ColumnCommand,
    source: bytes,
    palette32: Sequence[int],
) -> tuple[int, int]:
    colors, _ = stage09.r_draw_column_pixels(
        source,
        palette32,
        yl=command.yl,
        yh=command.yh,
        iscale=command.iscale,
        texturemid=command.texturemid,
    )
    for color in colors:
        signature = ((signature * FNV_PRIME) & 0xFFFFFFFF) ^ color
        signature &= 0xFFFFFFFF
    return signature, len(colors)


def _reference_sky_masked_uncached(wad_path: str) -> Stage12SkyMaskedReference:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    stage11_ref = stage11.reference_visplanes_floor_ceiling_for_pinned_map(wad_path)
    texture_data = stage11_ref.stage10.stage09.texture_data
    setup = texture_data.texture_setup
    palette32 = tuple(stage11_ref.palette32)
    raw_segs = stage02.parse_mapsegs(wad.read_lump(wad.map_lumps("MAP01").get("SEGS")))

    skyflatnum = stage08.r_flat_num_for_name(wad, setup, "F_SKY1")
    skytexture = stage08.r_texture_num_for_name(setup, "SKY1")
    skytexturemid = skytexturemid_for_view_height()
    sky_candidates = find_sky_sector_candidates(loaded, texture_data.resolved_sectors, skyflatnum)
    masked_candidates = find_two_sided_masked_sidedef_candidates(
        loaded,
        texture_data.resolved_sidedefs,
        setup,
        raw_segs,
    )

    primary_sky_columns = stage11_ref.sky_columns_skipped
    primary_masked_columns = stage11_ref.stage10.masked_midtexture_skips
    probe = select_feature_probe(
        sky_candidates,
        masked_candidates,
        primary_sky_columns=primary_sky_columns,
        primary_masked_columns=primary_masked_columns,
    )

    column_sources: list[bytes] = []
    source_index_by_pixels: dict[bytes, int] = {}

    def source_index_for_pixels(pixels: bytes) -> int:
        index = source_index_by_pixels.get(pixels)
        if index is None:
            index = len(column_sources)
            source_index_by_pixels[pixels] = index
            column_sources.append(pixels)
        return index

    sky_commands: list[Stage12ColumnCommand] = []
    masked_commands: list[Stage12ColumnCommand] = []
    composite_cache = stage10.CompositeColumnCache()
    direct_cache: dict[tuple[int, int], bytes] = {}
    masked_store = MaskedTextureColumnStore(FRAMEBUFFER_WIDTH)
    masked_column_source_skips = 0
    masked_segments_considered = 0
    masked_columns_drawn_set: set[int] = set()
    signature = stage11_ref.framebuffer_signature
    sky_pixels_drawn = 0
    masked_pixels_drawn = 0
    first_sky_texture_column = 0
    first_masked_texture_column = 0

    if probe.uses_probe and probe.sky_sector is not None:
        for x in range(PROBE_SKY_X1, PROBE_SKY_X2 + 1):
            raw_column = sky_texture_column(probe.view_angle, x)
            lookup = _column_lookup_source(
                wad,
                setup,
                skytexture,
                raw_column,
                composite_cache,
                direct_cache,
            )
            if lookup is None:
                continue
            wrapped_column, source = lookup
            source_index = source_index_for_pixels(source)
            command = Stage12ColumnCommand(
                x=x,
                yl=PROBE_SKY_YL,
                yh=PROBE_SKY_YH,
                iscale=FRACUNIT,
                texturemid=skytexturemid,
                source_index=source_index,
                tier="sky",
                texture_id=skytexture,
                texture_name=setup.textures[skytexture].name,
                texture_column=wrapped_column,
            )
            if not sky_commands:
                first_sky_texture_column = wrapped_column
            sky_commands.append(command)
            signature, pixels = _append_signature_for_command(signature, command, source, palette32)
            sky_pixels_drawn += pixels

    if probe.uses_probe and probe.masked is not None and probe.masked.raw_seg_index is not None:
        raw_seg = raw_segs[probe.masked.raw_seg_index]
        projection = _project_masked_candidate(
            loaded,
            raw_seg,
            probe.masked,
            setup,
            view_x=probe.view_x,
            view_y=probe.view_y,
            view_angle=probe.view_angle,
        )
        if projection is not None:
            masked_segments_considered = 1
            draw_x1 = max(PROBE_MASKED_X1, projection.x1)
            draw_x2 = min(PROBE_MASKED_X2, projection.x2)
            for x in range(draw_x1, draw_x2 + 1):
                texture_column = texture_column_for_x(projection, x)
                if not masked_store.store(x, texture_column):
                    continue

            for x in range(draw_x1, draw_x2 + 1):
                texture_column = masked_store.consume(x)
                if texture_column == SHRT_MAX:
                    continue
                posts_result = _masked_column_posts(
                    wad,
                    setup,
                    probe.masked.texture_id,
                    texture_column,
                )
                if posts_result is None:
                    masked_column_source_skips += 1
                    continue
                wrapped_column, posts = posts_result
                spryscale = projection.scale1 + (x - projection.x1) * projection.scalestep
                sprtopscreen = CENTERYFRAC - stage07.fixed_mul(projection.texturemid, spryscale)
                post_commands = masked_post_draw_commands(
                    posts,
                    x=x,
                    texture_id=probe.masked.texture_id,
                    texture_name=probe.masked.texture_name,
                    texture_column=wrapped_column,
                    sprtopscreen=sprtopscreen,
                    spryscale=spryscale,
                    dc_texturemid=projection.texturemid,
                    mfloorclip=PROBE_MASKED_FLOOR_CLIP,
                    mceilingclip=PROBE_MASKED_CEILING_CLIP,
                    source_index_for_pixels=source_index_for_pixels,
                )
                if post_commands:
                    masked_columns_drawn_set.add(x)
                    if first_masked_texture_column == 0:
                        first_masked_texture_column = wrapped_column
                for command in post_commands:
                    masked_commands.append(command)
                    source = column_sources[command.source_index]
                    signature, pixels = _append_signature_for_command(signature, command, source, palette32)
                    masked_pixels_drawn += pixels

    return Stage12SkyMaskedReference(
        stage11=stage11_ref,
        palette32=palette32,
        column_sources=tuple(column_sources),
        sky_commands=tuple(sky_commands),
        masked_commands=tuple(masked_commands),
        sky_sector_candidates=sky_candidates,
        masked_sidedef_candidates=masked_candidates,
        probe=probe,
        skyflatnum=skyflatnum,
        skytexture=skytexture,
        skytexturemid=skytexturemid,
        primary_sky_columns=primary_sky_columns,
        primary_masked_columns=primary_masked_columns,
        sky_visplanes_drawn=1 if sky_commands else 0,
        sky_columns_drawn=len(sky_commands),
        sky_pixels_drawn=sky_pixels_drawn,
        masked_segments_considered=masked_segments_considered,
        masked_columns_stored=masked_store.stored_count,
        masked_columns_drawn=len(masked_columns_drawn_set),
        masked_post_commands_drawn=len(masked_commands),
        masked_pixels_drawn=masked_pixels_drawn,
        masked_opening_overflow_count=masked_store.overflow_count,
        masked_column_source_skips=masked_column_source_skips,
        skipped_sprite_count=0,
        first_sky_texture_id=skytexture if sky_commands else 0,
        first_sky_texture_name=setup.textures[skytexture].name if sky_commands else "",
        first_sky_texture_column=first_sky_texture_column,
        first_masked_texture_id=probe.masked.texture_id if probe.masked is not None and masked_commands else 0,
        first_masked_texture_name=probe.masked.texture_name if probe.masked is not None and masked_commands else "",
        first_masked_texture_column=first_masked_texture_column,
        framebuffer_signature=signature,
    )


@lru_cache(maxsize=4)
def _reference_sky_masked_cached(wad_path: str) -> Stage12SkyMaskedReference:
    return _reference_sky_masked_uncached(wad_path)


def reference_sky_and_masked_midtextures_for_pinned_map(
    wad_path: str | Path,
) -> Stage12SkyMaskedReference:
    return _reference_sky_masked_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage12SkyMaskedReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_sky_and_masked_midtextures_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage12_load_wad_sky_masked_midtextures_debug")

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


def emit_source_stage12_load_wad_sky_masked_midtextures_debug(pe: PE32) -> None:
    pe.label("source_stage12_load_wad_sky_masked_midtextures_debug")
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
    x86.jne_rel32(pe, "source_stage12_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage12_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage12_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage12_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage12_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage12_close_and_return")

    pe.label("source_stage12_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage12_close_and_return")

    x86.call_rel32(pe, "render_init_texture_data_setup_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage12_close_and_return")

    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage12_close_and_return")

    x86.call_rel32(pe, "source_stage06_run_live_seg_clip_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage12_close_and_return")

    x86.call_rel32(pe, "render_composite_two_sided_wall_edges_debug")
    x86.call_rel32(pe, "render_visplanes_floor_ceiling_debug")
    x86.call_rel32(pe, "render_sky_and_masked_midtextures_debug")
    x86.call_rel32(pe, "build_success_status")

    pe.label("source_stage12_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def _emit_column_command_loop(
    pe: PE32,
    *,
    command_label: str,
    count_label: str,
    scan_label: str,
    remaining_label: str,
    loop_label: str,
    done_label: str,
    column_counter_label: str,
    draw_func_label: str,
) -> None:
    x86.mov_reg_abs32(pe, "esi", command_label)
    x86.mov_mem_abs32_reg(pe, scan_label, "esi")
    x86.mov_reg_mem_abs32(pe, "eax", count_label)
    x86.mov_mem_abs32_eax(pe, remaining_label)

    pe.label(loop_label)
    x86.mov_reg_mem_abs32(pe, "eax", remaining_label)
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, done_label)

    x86.mov_reg_mem_abs32(pe, "esi", scan_label)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", COLUMN_COMMAND_X)
    x86.mov_mem_abs32_eax(pe, "dc_x")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", COLUMN_COMMAND_YL)
    x86.mov_mem_abs32_eax(pe, "dc_yl")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", COLUMN_COMMAND_YH)
    x86.mov_mem_abs32_eax(pe, "dc_yh")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", COLUMN_COMMAND_ISCALE)
    x86.mov_mem_abs32_eax(pe, "dc_iscale")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", COLUMN_COMMAND_TEXTUREMID)
    x86.mov_mem_abs32_eax(pe, "dc_texturemid")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", COLUMN_COMMAND_SOURCE)
    x86.mov_mem_abs32_eax(pe, "dc_source")

    stage07._emit_inc_abs32(pe, column_counter_label)
    x86.call_rel32(pe, draw_func_label)

    x86.mov_reg_mem_abs32(pe, "esi", scan_label)
    x86.add_reg_imm32(pe, "esi", COLUMN_COMMAND_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, scan_label, "esi")
    x86.dec_mem_abs32(pe, remaining_label)
    x86.jmp_rel32(pe, loop_label)
    pe.label(done_label)


def emit_render_sky_and_masked_midtextures_debug(pe: PE32) -> None:
    pe.label("render_init_sky_map_debug")
    pe.label("render_debug_map01_sky_selection")
    pe.label("render_draw_planes_sky_branch_debug")
    pe.label("render_store_masked_midtexture_debug")
    pe.label("render_maskedtexturecol_openings_debug")
    pe.label("render_masked_seg_range_debug")
    pe.label("render_sky_and_masked_midtextures_debug")
    x86.mov_mem_abs32_imm32(pe, "stage12_sky_columns_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage12_sky_pixels_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage12_masked_columns_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage12_masked_post_commands_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage12_masked_pixels_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage12_pixels_drawn", 0)
    x86.mov_reg_mem_abs32(pe, "eax", "stage11_pixel_signature")
    x86.mov_mem_abs32_eax(pe, "stage12_pixel_signature")
    x86.mov_mem_abs32_abs32(pe, "dc_colormap", "stage12_palette32")

    _emit_column_command_loop(
        pe,
        command_label="stage12_sky_commands",
        count_label="stage12_sky_command_count",
        scan_label="stage12_sky_scan_ptr",
        remaining_label="stage12_sky_remaining_commands",
        loop_label="stage12_sky_command_loop",
        done_label="stage12_sky_commands_done",
        column_counter_label="stage12_sky_columns_drawn",
        draw_func_label="render_draw_stage12_sky_column_debug",
    )

    _emit_column_command_loop(
        pe,
        command_label="stage12_masked_commands",
        count_label="stage12_masked_command_count",
        scan_label="stage12_masked_scan_ptr",
        remaining_label="stage12_masked_remaining_commands",
        loop_label="stage12_masked_command_loop",
        done_label="stage12_masked_commands_done",
        column_counter_label="stage12_masked_columns_drawn",
        draw_func_label="render_draw_stage12_masked_column_debug",
    )

    x86.ret(pe)


def _emit_render_draw_stage12_column_debug(
    pe: PE32,
    *,
    label: str,
    per_tier_pixel_counter: str,
    per_tier_post_counter: str | None = None,
) -> None:
    pe.label(label)
    if per_tier_post_counter is not None:
        stage07._emit_inc_abs32(pe, per_tier_post_counter)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_reg_mem_abs32(pe, "eax", "dc_yh")
    x86.sub_reg_mem_abs32(pe, "eax", "dc_yl")
    x86.jl_rel32(pe, f"{label}_done")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "stage12_column_remaining")

    x86.mov_reg_mem_abs32(pe, "ebx", "dc_yl")
    x86.mov_reg_reg(pe, "edx", "ebx")
    x86.shl_reg_imm8(pe, "ebx", 8)
    x86.shl_reg_imm8(pe, "edx", 6)
    x86.add_reg_reg(pe, "ebx", "edx")
    x86.add_reg_mem_abs32(pe, "ebx", "dc_x")
    x86.shl_reg_imm8(pe, "ebx", 2)
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.add_reg_reg(pe, "edi", "ebx")

    x86.mov_reg_mem_abs32(pe, "eax", "dc_yl")
    x86.add_reg_imm32(pe, "eax", -CENTER_Y)
    x86.mov_reg_mem_abs32(pe, "ecx", "dc_iscale")
    x86.imul_reg(pe, "ecx")
    x86.add_reg_mem_abs32(pe, "eax", "dc_texturemid")
    x86.mov_mem_abs32_eax(pe, "dc_frac")

    pe.label(f"{label}_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "dc_frac")
    x86.sar_reg_imm8(pe, "eax", FRACBITS)
    x86.and_reg_imm32(pe, "eax", WALL_COLUMN_SOURCE_HEIGHT - 1)
    x86.mov_reg_mem_abs32(pe, "esi", "dc_source")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.movzx_reg_byte_ptr_reg(pe, "eax", "esi")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_mem_abs32(pe, "esi", "dc_colormap")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "esi")
    x86.mov_ptr_reg_eax(pe, "edi")

    x86.mov_reg_mem_abs32(pe, "ecx", "stage12_pixel_signature")
    x86.imul_reg_reg_imm32(pe, "ecx", "ecx", FNV_PRIME)
    x86.xor_reg_reg(pe, "ecx", "eax")
    x86.mov_mem_abs32_reg(pe, "stage12_pixel_signature", "ecx")
    stage07._emit_inc_abs32(pe, "stage12_pixels_drawn")
    stage07._emit_inc_abs32(pe, per_tier_pixel_counter)

    x86.add_reg_imm32(pe, "edi", FRAMEBUFFER_WIDTH * 4)
    x86.mov_reg_mem_abs32(pe, "eax", "dc_frac")
    x86.add_reg_mem_abs32(pe, "eax", "dc_iscale")
    x86.mov_mem_abs32_eax(pe, "dc_frac")
    x86.dec_mem_abs32(pe, "stage12_column_remaining")
    x86.jne_rel32(pe, f"{label}_loop")

    pe.label(f"{label}_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_render_draw_stage12_columns_debug(pe: PE32) -> None:
    _emit_render_draw_stage12_column_debug(
        pe,
        label="render_draw_stage12_sky_column_debug",
        per_tier_pixel_counter="stage12_sky_pixels_drawn",
    )
    pe.label("render_draw_masked_column_debug")
    _emit_render_draw_stage12_column_debug(
        pe,
        label="render_draw_stage12_masked_column_debug",
        per_tier_pixel_counter="stage12_masked_pixels_drawn",
        per_tier_post_counter="stage12_masked_post_commands_drawn",
    )


def emit_build_success_status(pe: PE32) -> None:
    pe.label("build_success_status")
    x86.mov_reg_abs32(pe, "edi", "status_success_buffer")
    stage01.append_c_string_label(pe, "status_stage12_success_header")
    stage01.append_u32_label(pe, "status_clip_nodes_prefix", "clip_visited_node_count")
    stage01.append_u32_label(pe, "status_clip_subsectors_prefix", "clip_visited_subsector_count")
    stage01.append_u32_label(pe, "status_clip_segs_prefix", "clip_visited_seg_count")
    stage01.append_u32_label(pe, "status_stage10_columns_drawn_prefix", "stage10_columns_drawn")
    stage01.append_u32_label(pe, "status_stage10_signature_prefix", "stage10_pixel_signature")
    stage01.append_u32_label(pe, "status_stage11_visplanes_prefix", "stage11_visplane_count")
    stage01.append_u32_label(pe, "status_stage11_spans_prefix", "stage11_flat_spans_drawn")
    stage01.append_u32_label(pe, "status_stage11_pixels_prefix", "stage11_flat_pixels_drawn")
    stage01.append_u32_label(pe, "status_stage11_signature_prefix", "stage11_pixel_signature")
    stage01.append_u32_label(pe, "status_stage12_sky_columns_prefix", "stage12_sky_columns_drawn")
    stage01.append_u32_label(pe, "status_stage12_masked_columns_prefix", "stage12_masked_columns_drawn")
    stage01.append_u32_label(pe, "status_stage12_pixels_prefix", "stage12_pixels_drawn")
    stage01.append_u32_label(pe, "status_stage12_signature_prefix", "stage12_pixel_signature")
    stage01.append_c_string_label(pe, "status_stage12_note")
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
    stage01.append_u32_label(pe, "title_stage12_sky_candidate_prefix", "stage12_sky_sector_candidate_count")
    stage01.append_u32_label(pe, "title_stage12_masked_candidate_prefix", "stage12_masked_sidedef_candidate_count")
    stage01.append_u32_label(pe, "title_stage12_probe_prefix", "stage12_probe_active")
    stage01.append_u32_label(pe, "title_stage12_primary_sky_prefix", "stage12_primary_sky_columns")
    stage01.append_u32_label(pe, "title_stage12_primary_mask_prefix", "stage12_primary_masked_columns")
    stage01.append_u32_label(pe, "title_stage12_probe_sky_sector_prefix", "stage12_probe_sky_sector")
    stage01.append_u32_label(pe, "title_stage12_probe_mask_sidedef_prefix", "stage12_probe_mask_sidedef")
    stage01.append_i32_label(pe, "title_stage12_probe_x_prefix", "stage12_probe_view_x")
    stage01.append_i32_label(pe, "title_stage12_probe_y_prefix", "stage12_probe_view_y")
    stage01.append_u32_label(pe, "title_stage12_probe_angle_prefix", "stage12_probe_view_angle_degrees")
    stage01.append_u32_label(pe, "title_stage12_probe_sector_prefix", "stage12_probe_view_sector")
    stage01.append_u32_label(pe, "title_stage12_sky_texture_id_prefix", "stage12_first_sky_texture_id")
    stage01.append_c_string_label(pe, "title_stage12_sky_texture_name_prefix")
    stage01.append_c_string_label(pe, "stage12_first_sky_texture_name")
    stage01.append_u32_label(pe, "title_stage12_sky_columns_prefix", "stage12_sky_columns_drawn")
    stage01.append_u32_label(pe, "title_stage12_sky_pixels_prefix", "stage12_sky_pixels_drawn")
    stage01.append_u32_label(pe, "title_stage12_masked_texture_id_prefix", "stage12_first_masked_texture_id")
    stage01.append_c_string_label(pe, "title_stage12_masked_texture_name_prefix")
    stage01.append_c_string_label(pe, "stage12_first_masked_texture_name")
    stage01.append_u32_label(pe, "title_stage12_masked_columns_prefix", "stage12_masked_columns_drawn")
    stage01.append_u32_label(pe, "title_stage12_masked_posts_prefix", "stage12_masked_post_commands_drawn")
    stage01.append_u32_label(pe, "title_stage12_masked_pixels_prefix", "stage12_masked_pixels_drawn")
    stage01.append_u32_label(pe, "title_stage12_sprite_skip_prefix", "stage12_skipped_sprite_count")
    stage01.append_u32_label(pe, "title_stage12_signature_prefix", "stage12_pixel_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def _emit_u32_table(pe: PE32, label: str, values: Sequence[int]) -> None:
    pe.label(label)
    for value in values:
        pe.emit_u32(value & 0xFFFFFFFF)


def _emit_column_commands(pe: PE32, commands: Sequence[Stage12ColumnCommand]) -> None:
    for command in commands:
        pe.emit_u32(command.x)
        pe.emit_u32(command.yl)
        pe.emit_u32(command.yh)
        pe.emit_u32(command.iscale)
        pe.emit_u32(command.texturemid)
        pe.write_abs32(f"stage12_column_source_{command.source_index}")


def emit_stage12_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()

    pe.align_section(4)
    pe.label("stage12_skyflatnum")
    pe.emit_u32(ref.skyflatnum if ref is not None else 0)
    pe.label("stage12_skytexture")
    pe.emit_u32(ref.skytexture if ref is not None else 0)
    pe.label("stage12_skytexturemid")
    pe.emit_u32(ref.skytexturemid if ref is not None else 0)
    pe.label("stage12_sky_sector_candidate_count")
    pe.emit_u32(len(ref.sky_sector_candidates) if ref is not None else 0)
    pe.label("stage12_masked_sidedef_candidate_count")
    pe.emit_u32(len(ref.masked_sidedef_candidates) if ref is not None else 0)
    pe.label("stage12_probe_active")
    pe.emit_u32(1 if ref is not None and ref.probe.uses_probe else 0)
    pe.label("stage12_primary_sky_columns")
    pe.emit_u32(ref.primary_sky_columns if ref is not None else 0)
    pe.label("stage12_primary_masked_columns")
    pe.emit_u32(ref.primary_masked_columns if ref is not None else 0)
    pe.label("stage12_probe_sky_sector")
    pe.emit_u32(ref.probe.sky_sector.sector_index if ref is not None and ref.probe.sky_sector is not None else 0)
    pe.label("stage12_probe_mask_linedef")
    pe.emit_u32(ref.probe.masked.linedef_index if ref is not None and ref.probe.masked is not None else 0)
    pe.label("stage12_probe_mask_sidedef")
    pe.emit_u32(ref.probe.masked.sidedef_index if ref is not None and ref.probe.masked is not None else 0)
    pe.label("stage12_probe_view_x")
    pe.emit_u32(ref.probe.view_x if ref is not None else 0)
    pe.label("stage12_probe_view_y")
    pe.emit_u32(ref.probe.view_y if ref is not None else 0)
    pe.label("stage12_probe_view_angle")
    pe.emit_u32(ref.probe.view_angle if ref is not None else 0)
    pe.label("stage12_probe_view_angle_degrees")
    pe.emit_u32(ref.probe.view_angle_degrees if ref is not None else 0)
    pe.label("stage12_probe_view_sector")
    pe.emit_u32(ref.probe.view_sector if ref is not None and ref.probe.view_sector >= 0 else 0)
    pe.label("stage12_sky_visplanes_drawn")
    pe.emit_u32(ref.sky_visplanes_drawn if ref is not None else 0)
    pe.label("stage12_expected_sky_columns_drawn")
    pe.emit_u32(ref.sky_columns_drawn if ref is not None else 0)
    pe.label("stage12_expected_sky_pixels_drawn")
    pe.emit_u32(ref.sky_pixels_drawn if ref is not None else 0)
    pe.label("stage12_masked_segments_considered")
    pe.emit_u32(ref.masked_segments_considered if ref is not None else 0)
    pe.label("stage12_masked_columns_stored")
    pe.emit_u32(ref.masked_columns_stored if ref is not None else 0)
    pe.label("stage12_expected_masked_columns_drawn")
    pe.emit_u32(ref.masked_columns_drawn if ref is not None else 0)
    pe.label("stage12_expected_masked_post_commands_drawn")
    pe.emit_u32(ref.masked_post_commands_drawn if ref is not None else 0)
    pe.label("stage12_expected_masked_pixels_drawn")
    pe.emit_u32(ref.masked_pixels_drawn if ref is not None else 0)
    pe.label("stage12_masked_opening_overflow_count")
    pe.emit_u32(ref.masked_opening_overflow_count if ref is not None else 0)
    pe.label("stage12_masked_column_source_skips")
    pe.emit_u32(ref.masked_column_source_skips if ref is not None else 0)
    pe.label("stage12_skipped_sprite_count")
    pe.emit_u32(ref.skipped_sprite_count if ref is not None else 0)
    pe.label("stage12_first_sky_texture_id")
    pe.emit_u32(ref.first_sky_texture_id if ref is not None else 0)
    pe.label("stage12_first_sky_texture_column")
    pe.emit_u32(ref.first_sky_texture_column if ref is not None else 0)
    pe.label("stage12_first_masked_texture_id")
    pe.emit_u32(ref.first_masked_texture_id if ref is not None else 0)
    pe.label("stage12_first_masked_texture_column")
    pe.emit_u32(ref.first_masked_texture_column if ref is not None else 0)
    pe.label("stage12_expected_pixel_signature")
    pe.emit_u32(ref.framebuffer_signature if ref is not None else 0)
    pe.label("stage12_sky_command_count")
    pe.emit_u32(len(ref.sky_commands) if ref is not None else 0)
    pe.label("stage12_masked_command_count")
    pe.emit_u32(len(ref.masked_commands) if ref is not None else 0)

    pe.label("stage12_sky_columns_drawn")
    pe.emit_u32(0)
    pe.label("stage12_sky_pixels_drawn")
    pe.emit_u32(0)
    pe.label("stage12_masked_columns_drawn")
    pe.emit_u32(0)
    pe.label("stage12_masked_post_commands_drawn")
    pe.emit_u32(0)
    pe.label("stage12_masked_pixels_drawn")
    pe.emit_u32(0)
    pe.label("stage12_pixels_drawn")
    pe.emit_u32(0)
    pe.label("stage12_pixel_signature")
    pe.emit_u32(0)
    pe.label("stage12_sky_scan_ptr")
    pe.emit_u32(0)
    pe.label("stage12_sky_remaining_commands")
    pe.emit_u32(0)
    pe.label("stage12_masked_scan_ptr")
    pe.emit_u32(0)
    pe.label("stage12_masked_remaining_commands")
    pe.emit_u32(0)
    pe.label("stage12_column_remaining")
    pe.emit_u32(0)

    _emit_u32_table(pe, "stage12_palette32", list(ref.palette32) if ref is not None else [0] * 256)

    pe.align_section(4)
    pe.label("stage12_sky_commands")
    if ref is not None:
        _emit_column_commands(pe, ref.sky_commands)

    pe.align_section(4)
    pe.label("stage12_masked_commands")
    if ref is not None:
        _emit_column_commands(pe, ref.masked_commands)

    pe.align_section(1)
    if ref is not None:
        for index, pixels in enumerate(ref.column_sources):
            pe.label(f"stage12_column_source_{index}")
            pe.emit(pixels)

    pe.align_section(1)
    pe.label("stage12_first_sky_texture_name")
    x86.emit_asciiz(pe, ref.first_sky_texture_name if ref is not None else "")
    pe.label("stage12_first_masked_texture_name")
    x86.emit_asciiz(pe, ref.first_masked_texture_name if ref is not None else "")

    pe.label("status_stage12_success_header")
    x86.emit_asciiz(
        pe,
        "source_stage12_sky_and_masked_midtextures_debug\r\n"
        "Sky and masked midtexture debug OK\r\n",
    )
    pe.label("status_stage12_sky_columns_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime R_DrawPlanes sky columns: ")
    pe.label("status_stage12_masked_columns_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime R_RenderMaskedSegRange columns: ")
    pe.label("status_stage12_pixels_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime stage12 sky/masked pixels: ")
    pe.label("status_stage12_signature_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime wall+flat+sky+masked RGB signature: ")
    pe.label("status_stage12_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage12 preserves the primary stage11 player-start view and uses a "
        "deterministic MAP01 feature probe when the primary view has no sky or "
        "masked midtexture columns. It uses fixed Doom II MAP01 F_SKY1/SKY1 "
        "selection as a debug adaptation, draws sky through the R_DrawPlanes "
        "sky branch, and draws two-sided masked midtexture posts after walls "
        "and flats with R_RenderMaskedSegRange and R_DrawMaskedColumn. Later "
        "renderer and game-system slices remain deferred.\r\n",
    )

    pe.label("title_stage12_sky_candidate_prefix")
    x86.emit_asciiz(pe, " SKCAND=")
    pe.label("title_stage12_masked_candidate_prefix")
    x86.emit_asciiz(pe, " MCAND=")
    pe.label("title_stage12_probe_prefix")
    x86.emit_asciiz(pe, " PROBE=")
    pe.label("title_stage12_primary_sky_prefix")
    x86.emit_asciiz(pe, " PSKY=")
    pe.label("title_stage12_primary_mask_prefix")
    x86.emit_asciiz(pe, " PMASK=")
    pe.label("title_stage12_probe_sky_sector_prefix")
    x86.emit_asciiz(pe, " SKYSEC=")
    pe.label("title_stage12_probe_mask_sidedef_prefix")
    x86.emit_asciiz(pe, " MSIDE=")
    pe.label("title_stage12_probe_x_prefix")
    x86.emit_asciiz(pe, " PVX=")
    pe.label("title_stage12_probe_y_prefix")
    x86.emit_asciiz(pe, " PVY=")
    pe.label("title_stage12_probe_angle_prefix")
    x86.emit_asciiz(pe, " PVA=")
    pe.label("title_stage12_probe_sector_prefix")
    x86.emit_asciiz(pe, " PSEC=")
    pe.label("title_stage12_sky_texture_id_prefix")
    x86.emit_asciiz(pe, " SKYT=")
    pe.label("title_stage12_sky_texture_name_prefix")
    x86.emit_asciiz(pe, " SKYN=")
    pe.label("title_stage12_sky_columns_prefix")
    x86.emit_asciiz(pe, " SCOL=")
    pe.label("title_stage12_sky_pixels_prefix")
    x86.emit_asciiz(pe, " SPIX=")
    pe.label("title_stage12_masked_texture_id_prefix")
    x86.emit_asciiz(pe, " MTEX=")
    pe.label("title_stage12_masked_texture_name_prefix")
    x86.emit_asciiz(pe, " MN=")
    pe.label("title_stage12_masked_columns_prefix")
    x86.emit_asciiz(pe, " MCOL12=")
    pe.label("title_stage12_masked_posts_prefix")
    x86.emit_asciiz(pe, " MPOST=")
    pe.label("title_stage12_masked_pixels_prefix")
    x86.emit_asciiz(pe, " MPIX=")
    pe.label("title_stage12_sprite_skip_prefix")
    x86.emit_asciiz(pe, " SPR=0 SSK=")
    pe.label("title_stage12_signature_prefix")
    x86.emit_asciiz(pe, " S12SIG=")


def build_source_stage12_sky_and_masked_midtextures_debug_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage12_load_wad_sky_masked_midtextures_debug(pe)
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
    stage11.emit_render_visplanes_floor_ceiling_debug(pe)
    stage11.emit_render_draw_span_debug(pe)
    emit_render_sky_and_masked_midtextures_debug(pe)
    emit_render_draw_stage12_columns_debug(pe)
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
    stage11.emit_stage11_data(pe)
    emit_stage12_data(pe)
    return pe.build("entry")


def write_source_stage12_sky_and_masked_midtextures_debug_exe(path: str | Path) -> bytes:
    image = build_source_stage12_sky_and_masked_midtextures_debug_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the source-guided PE32 x86 sky/masked midtexture debug executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/source_stage12_sky_and_masked_midtextures_debug.exe",
        help="path to write, default: build/source_stage12_sky_and_masked_midtextures_debug.exe",
    )
    args = parser.parse_args()
    write_source_stage12_sky_and_masked_midtextures_debug_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
