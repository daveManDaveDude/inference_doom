from __future__ import annotations

import argparse
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
from tools import emit_source_stage04_bbox_visibility_debug as stage04
from tools import emit_source_stage07_wall_projection_debug as stage07
from tools import emit_source_stage08_texture_data_setup_debug as stage08
from tools import emit_source_stage09_direct_wall_column_pixels_debug as stage09
from tools import x86
from tools.map_loader import LineDef, LoadedMap, load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


FRAMEBUFFER_WIDTH = stage09.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage09.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage09.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage09.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage09.WINDOW_WIDTH
WINDOW_HEIGHT = stage09.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage10CompositeTwoSidedWallEdgesDebug"
WINDOW_TITLE = "Inference Doom S10 Composite Wall Edges"
WAD_PATH = stage09.WAD_PATH

FRACBITS = stage09.FRACBITS
FRACUNIT = stage09.FRACUNIT
VIEW_ANGLE = stage09.VIEW_ANGLE
ANG180 = stage09.ANG180
HEIGHTBITS = stage09.HEIGHTBITS
HEIGHTUNIT = stage09.HEIGHTUNIT
CENTER_Y = stage09.CENTER_Y
CENTERYFRAC = stage09.CENTERYFRAC
WALL_COLUMN_SOURCE_HEIGHT = stage09.WALL_COLUMN_SOURCE_HEIGHT
FNV_OFFSET_BASIS = stage09.FNV_OFFSET_BASIS
FNV_PRIME = stage09.FNV_PRIME
ML_DONTPEGTOP = 8
ML_DONTPEGBOTTOM = stage09.ML_DONTPEGBOTTOM

DRAW_COMMAND_X = stage09.DRAW_COMMAND_X
DRAW_COMMAND_YL = stage09.DRAW_COMMAND_YL
DRAW_COMMAND_YH = stage09.DRAW_COMMAND_YH
DRAW_COMMAND_ISCALE = stage09.DRAW_COMMAND_ISCALE
DRAW_COMMAND_TEXTUREMID = stage09.DRAW_COMMAND_TEXTUREMID
DRAW_COMMAND_SOURCE = stage09.DRAW_COMMAND_SOURCE
DRAW_COMMAND_RECORD_SIZE = stage09.DRAW_COMMAND_RECORD_SIZE

DEFAULT_COMPOSITE_CACHE_MAX_ENTRIES = 4096

SOURCE_TRACE = stage09.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/r_data.c",
        "R_DrawColumnInCache",
        "render_draw_column_in_cache_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_data.c",
        "R_GenerateComposite",
        "render_generate_composite_cache_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_data.c",
        "R_GetColumn composite branch",
        "render_get_column_direct_or_composite_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_segs.c",
        "R_StoreWallRange two-sided upper/lower setup",
        "render_two_sided_wall_edges_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_segs.c",
        "R_RenderSegLoop toptexture/bottomtexture branches",
        "render_two_sided_wall_edges_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_plane.c",
        "R_ClearPlanes and R_CheckPlane record hooks",
        "render_plane_mark_records_debug",
    ),
)


@dataclass
class CompositeColumnCache:
    max_entries: int = DEFAULT_COMPOSITE_CACHE_MAX_ENTRIES
    entries: dict[tuple[int, int], bytes] | None = None
    builds: int = 0
    hits: int = 0
    overflow: int = 0
    missing: int = 0
    bad_columns: int = 0

    def __post_init__(self) -> None:
        if self.entries is None:
            self.entries = {}


@dataclass(frozen=True)
class ColumnLookupResult:
    texture_column: int
    pixels: bytes | None
    skip_reason: str | None
    source_kind: str


@dataclass(frozen=True)
class Stage10DrawCommand:
    x: int
    yl: int
    yh: int
    iscale: int
    texturemid: int
    source_index: int
    texture_id: int
    texture_name: str
    texture_column: int
    tier: str
    source_kind: str


@dataclass(frozen=True)
class PlaneMarkRecord:
    kind: str
    x: int
    top: int
    bottom: int
    seg_index: int


@dataclass(frozen=True)
class EdgeClipColumnResult:
    yl: int
    yh: int
    upper_yl: int | None
    upper_yh: int | None
    lower_yl: int | None
    lower_yh: int | None
    ceilingclip: int
    floorclip: int
    ceiling_mark: tuple[int, int] | None
    floor_mark: tuple[int, int] | None
    pixhigh_next: int
    pixlow_next: int


@dataclass(frozen=True)
class Stage10CompositeTwoSidedWallEdgesReference:
    stage09: stage09.DirectWallColumnPixelsReference
    palette32: tuple[int, ...]
    column_sources: tuple[bytes, ...]
    commands: tuple[Stage10DrawCommand, ...]
    plane_mark_records: tuple[PlaneMarkRecord, ...]
    spans_considered: int
    one_sided_spans: int
    two_sided_spans: int
    two_sided_supported_edge_spans: int
    two_sided_no_supported_edge_spans: int
    mid_direct_columns_attempted: int
    mid_composite_columns_attempted: int
    mid_composite_columns_drawn: int
    mid_composite_columns_clipped_empty: int
    upper_direct_columns_attempted: int
    upper_composite_columns_attempted: int
    upper_columns_drawn: int
    upper_composite_columns_drawn: int
    upper_columns_clipped_empty: int
    lower_direct_columns_attempted: int
    lower_composite_columns_attempted: int
    lower_columns_drawn: int
    lower_composite_columns_drawn: int
    lower_columns_clipped_empty: int
    composite_cache_builds: int
    composite_cache_hits: int
    composite_cache_overflows: int
    composite_cache_missing_columns: int
    composite_cache_bad_columns: int
    composite_cache_entries: int
    direct_cache_entries: int
    composite_skip_short_columns: int
    composite_skip_other_columns: int
    masked_midtexture_skips: int
    plane_mark_ceiling_records: int
    plane_mark_floor_records: int
    columns_drawn: int
    direct_columns_drawn: int
    composite_columns_drawn: int
    pixels_drawn: int
    framebuffer_signature: int
    first_drawn_texture_id: int
    first_drawn_texture_name: str
    first_drawn_texture_column: int
    last_drawn_texture_id: int
    last_drawn_texture_name: str
    last_drawn_texture_column: int


def r_draw_column_in_cache(
    posts: Sequence[stage09.PatchColumnPost],
    *,
    originy: int,
    cacheheight: int,
    initial: bytes | None = None,
) -> bytes:
    if cacheheight < 0:
        raise stage08.TextureFormatError("cache height must be non-negative")
    if initial is None:
        cache = bytearray(cacheheight)
    else:
        if len(initial) != cacheheight:
            raise stage08.TextureFormatError("initial cache height does not match")
        cache = bytearray(initial)

    for post in posts:
        source_offset = 0
        count = len(post.pixels)
        position = originy + post.topdelta

        if position < 0:
            source_offset = -position
            count += position
            position = 0

        if position + count > cacheheight:
            count = cacheheight - position

        if count > 0:
            cache[position : position + count] = post.pixels[
                source_offset : source_offset + count
            ]

    return bytes(cache)


def _covered_patch_columns(
    wad: WadFile,
    texture: stage08.TextureMetadata,
    texture_column: int,
) -> tuple[tuple[stage08.TexturePatch, bytes, int], ...]:
    covered: list[tuple[stage08.TexturePatch, bytes, int]] = []
    for patch in texture.patches:
        patch_lump = wad.lumps[patch.patch_lump]
        patch_data = wad.read_lump(patch_lump)
        patch_header = stage08.parse_patch_header(patch_data, lump_name=patch_lump.name)
        x1 = patch.originx
        x2 = x1 + patch_header.width
        if texture_column >= max(0, x1) and texture_column < min(x2, texture.width):
            covered.append((patch, patch_data, texture_column - x1))
    return tuple(covered)


def r_generate_composite_column(
    wad: WadFile,
    setup: stage08.TextureSetup,
    tex: int,
    col: int,
    cache: CompositeColumnCache,
) -> ColumnLookupResult:
    texture = setup.textures[tex]
    texture_column = col & texture.texturewidthmask
    key = (tex, texture_column)
    assert cache.entries is not None

    if key in cache.entries:
        cache.hits += 1
        return ColumnLookupResult(texture_column, cache.entries[key], None, "composite")

    covered = _covered_patch_columns(wad, texture, texture_column)
    if not covered:
        cache.missing += 1
        return ColumnLookupResult(texture_column, None, "missing", "composite")
    if len(covered) == 1:
        return ColumnLookupResult(texture_column, None, "direct-only", "composite")
    if len(cache.entries) >= cache.max_entries:
        cache.overflow += 1
        return ColumnLookupResult(texture_column, None, "overflow", "composite")

    column = bytes(texture.height)
    for patch, patch_data, patch_column in covered:
        posts = stage09.parse_patch_column_posts(
            patch_data, patch_column, lump_name=patch.patch_name
        )
        column = r_draw_column_in_cache(
            posts,
            originy=patch.originy,
            cacheheight=texture.height,
            initial=column,
        )

    cache.entries[key] = column
    cache.builds += 1
    return ColumnLookupResult(texture_column, column, None, "composite")


def r_get_column_direct_or_composite(
    wad: WadFile,
    setup: stage08.TextureSetup,
    tex: int,
    col: int,
    composite_cache: CompositeColumnCache,
    direct_cache: dict[tuple[int, int], bytes] | None = None,
) -> ColumnLookupResult:
    texture = setup.textures[tex]
    texture_column = col & texture.texturewidthmask
    lump = texture.texturecolumnlump[texture_column]

    if lump > 0:
        patch_lump = wad.lumps[lump]
        patch_data = wad.read_lump(patch_lump)
        wanted_column_offset = texture.texturecolumnofs[texture_column] - 3
        header = stage08.parse_patch_header(patch_data, lump_name=patch_lump.name)
        try:
            patch_column = header.column_offsets.index(wanted_column_offset)
        except ValueError:
            return ColumnLookupResult(texture_column, None, "bad-offset", "direct")

        key = (lump, patch_column)
        if direct_cache is not None and key in direct_cache:
            return ColumnLookupResult(texture_column, direct_cache[key], None, "direct")

        pixels = stage09.decode_opaque_direct_column(
            patch_data,
            patch_column,
            lump_name=patch_lump.name,
            height=WALL_COLUMN_SOURCE_HEIGHT,
        )
        if pixels is None:
            return ColumnLookupResult(texture_column, None, "non-opaque", "direct")
        if direct_cache is not None:
            direct_cache[key] = pixels
        return ColumnLookupResult(texture_column, pixels, None, "direct")

    result = r_generate_composite_column(wad, setup, tex, col, composite_cache)
    if result.pixels is None or result.skip_reason is not None:
        return result
    if len(result.pixels) < WALL_COLUMN_SOURCE_HEIGHT:
        composite_cache.bad_columns += 1
        return ColumnLookupResult(
            result.texture_column, None, "short-composite", "composite"
        )
    return ColumnLookupResult(
        result.texture_column,
        result.pixels[:WALL_COLUMN_SOURCE_HEIGHT],
        None,
        "composite",
    )


def render_seg_loop_edge_clip_column(
    *,
    ceilingclip: int,
    floorclip: int,
    topfrac: int,
    bottomfrac: int,
    pixhigh: int,
    pixlow: int,
    pixhighstep: int,
    pixlowstep: int,
    markceiling: bool,
    markfloor: bool,
    has_toptexture: bool,
    has_bottomtexture: bool,
) -> EdgeClipColumnResult:
    yl = (topfrac + HEIGHTUNIT - 1) >> HEIGHTBITS
    if yl < ceilingclip + 1:
        yl = ceilingclip + 1

    ceiling_mark: tuple[int, int] | None = None
    if markceiling:
        top = ceilingclip + 1
        bottom = yl - 1
        if bottom >= floorclip:
            bottom = floorclip - 1
        if top <= bottom:
            ceiling_mark = (top, bottom)

    yh = bottomfrac >> HEIGHTBITS
    if yh >= floorclip:
        yh = floorclip - 1

    floor_mark: tuple[int, int] | None = None
    if markfloor:
        top = yh + 1
        bottom = floorclip - 1
        if top <= ceilingclip:
            top = ceilingclip + 1
        if top <= bottom:
            floor_mark = (top, bottom)

    upper_yl: int | None = None
    upper_yh: int | None = None
    lower_yl: int | None = None
    lower_yh: int | None = None
    next_ceilingclip = ceilingclip
    next_floorclip = floorclip
    next_pixhigh = pixhigh
    next_pixlow = pixlow

    if has_toptexture:
        mid = pixhigh >> HEIGHTBITS
        next_pixhigh = pixhigh + pixhighstep
        if mid >= floorclip:
            mid = floorclip - 1
        if mid >= yl:
            upper_yl = yl
            upper_yh = mid
            next_ceilingclip = mid
        else:
            next_ceilingclip = yl - 1
    elif markceiling:
        next_ceilingclip = yl - 1

    if has_bottomtexture:
        mid = (pixlow + HEIGHTUNIT - 1) >> HEIGHTBITS
        next_pixlow = pixlow + pixlowstep
        if mid <= next_ceilingclip:
            mid = next_ceilingclip + 1
        if mid <= yh:
            lower_yl = mid
            lower_yh = yh
            next_floorclip = mid
        else:
            next_floorclip = yh + 1
    elif markfloor:
        next_floorclip = yh + 1

    return EdgeClipColumnResult(
        yl=yl,
        yh=yh,
        upper_yl=upper_yl,
        upper_yh=upper_yh,
        lower_yl=lower_yl,
        lower_yh=lower_yh,
        ceilingclip=next_ceilingclip,
        floorclip=next_floorclip,
        ceiling_mark=ceiling_mark,
        floor_mark=floor_mark,
        pixhigh_next=next_pixhigh,
        pixlow_next=next_pixlow,
    )


def _uint32(value: int) -> int:
    return value & 0xFFFFFFFF


def _line_sidedef_index(line: LineDef, side: int) -> int:
    return line.right_sidedef if side == 0 else line.left_sidedef


def _line_backsector_index(line: LineDef, side: int, loaded: LoadedMap) -> int | None:
    if not (line.flags & stage08.ML_TWOSIDED):
        return None
    sidenum = line.left_sidedef if side == 0 else line.right_sidedef
    if sidenum == 0xFFFF or sidenum >= len(loaded.sidedefs):
        return None
    return loaded.sidedefs[sidenum].sector


def _append_draw_command(
    *,
    commands: list[Stage10DrawCommand],
    column_sources: list[bytes],
    source_index_by_key: dict[tuple[str, int, int], int],
    palette32: Sequence[int],
    setup: stage08.TextureSetup,
    lookup: ColumnLookupResult,
    framebuffer_signature: int,
    pixels_drawn: int,
    x: int,
    yl: int,
    yh: int,
    iscale: int,
    texturemid: int,
    texture_id: int,
    tier: str,
) -> tuple[int, int, bool]:
    if lookup.pixels is None or yl > yh:
        return framebuffer_signature, pixels_drawn, False

    key = (lookup.source_kind, texture_id, lookup.texture_column)
    source_index = source_index_by_key.get(key)
    if source_index is None:
        source_index = len(column_sources)
        source_index_by_key[key] = source_index
        column_sources.append(lookup.pixels)

    texture = setup.textures[texture_id]
    commands.append(
        Stage10DrawCommand(
            x=x,
            yl=yl,
            yh=yh,
            iscale=iscale,
            texturemid=texturemid,
            source_index=source_index,
            texture_id=texture_id,
            texture_name=texture.name,
            texture_column=lookup.texture_column,
            tier=tier,
            source_kind=lookup.source_kind,
        )
    )

    colors, _column_signature = stage09.r_draw_column_pixels(
        lookup.pixels,
        palette32,
        yl=yl,
        yh=yh,
        iscale=iscale,
        texturemid=texturemid,
    )
    for color in colors:
        framebuffer_signature = ((framebuffer_signature * FNV_PRIME) & 0xFFFFFFFF) ^ color
        framebuffer_signature &= 0xFFFFFFFF
    return framebuffer_signature, pixels_drawn + len(colors), True


def _texture_column_for_x(
    span: stage07.ProjectedSpan,
    rw_offset: int,
    rw_centerangle: int,
    x: int,
) -> int:
    angle = stage09._fine_index(_uint32(rw_centerangle + stage04.XTOVIEWANGLE[x]))
    return (
        rw_offset - stage07.fixed_mul(stage04.FINETANGENT[angle], span.rw_distance)
    ) >> FRACBITS


def reference_composite_two_sided_wall_edges_for_pinned_map(
    wad_path: str | Path,
    *,
    composite_cache_max_entries: int = DEFAULT_COMPOSITE_CACHE_MAX_ENTRIES,
) -> Stage10CompositeTwoSidedWallEdgesReference:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    stage09_ref = stage09.reference_direct_wall_column_pixels_for_pinned_map(wad_path)
    texture_data = stage09_ref.texture_data
    setup = texture_data.texture_setup
    palette32 = stage09_ref.palette32
    raw_segs = stage02.parse_mapsegs(wad.read_lump(wad.map_lumps("MAP01").get("SEGS")))
    skyflatnum = stage08.r_flat_num_for_name(wad, setup, "F_SKY1")

    composite_cache = CompositeColumnCache(max_entries=composite_cache_max_entries)
    direct_cache: dict[tuple[int, int], bytes] = {}
    column_sources: list[bytes] = []
    source_index_by_key: dict[tuple[str, int, int], int] = {}
    commands: list[Stage10DrawCommand] = []
    plane_marks: list[PlaneMarkRecord] = []

    spans_considered = len(texture_data.projection.projected_spans)
    one_sided_spans = 0
    two_sided_spans = 0
    two_sided_supported_edge_spans = 0
    two_sided_no_supported_edge_spans = 0
    mid_direct_columns_attempted = 0
    mid_composite_columns_attempted = 0
    mid_composite_columns_drawn = 0
    mid_composite_columns_clipped_empty = 0
    upper_direct_columns_attempted = 0
    upper_composite_columns_attempted = 0
    upper_columns_drawn = 0
    upper_composite_columns_drawn = 0
    upper_columns_clipped_empty = 0
    lower_direct_columns_attempted = 0
    lower_composite_columns_attempted = 0
    lower_columns_drawn = 0
    lower_composite_columns_drawn = 0
    lower_columns_clipped_empty = 0
    composite_skip_short_columns = 0
    composite_skip_other_columns = 0
    masked_midtexture_skips = 0
    plane_mark_ceiling_records = 0
    plane_mark_floor_records = 0
    direct_columns_drawn = 0
    composite_columns_drawn = 0
    pixels_drawn = 0
    framebuffer_signature = FNV_OFFSET_BASIS

    # Stage09-shaped one-sided pass: preserve its direct proof and turn its
    # composite-needed column lookups into explicit draw or clipped counters.
    for span in texture_data.projection.projected_spans:
        raw_seg = raw_segs[span.seg_index]
        line = loaded.linedefs[raw_seg[3]]
        sidedef_index = _line_sidedef_index(line, raw_seg[4])
        resolved = texture_data.resolved_sidedefs[sidedef_index]
        backsector_index = _line_backsector_index(line, raw_seg[4], loaded)

        if backsector_index is not None:
            if resolved.midtexture != 0:
                masked_midtexture_skips += 1
            continue

        one_sided_spans += 1
        texid = resolved.midtexture
        if texid == 0:
            continue

        texture = setup.textures[texid]
        sidedef = loaded.sidedefs[sidedef_index]
        frontsector = loaded.sectors[sidedef.sector]
        worldtop = (frontsector.ceiling_height << FRACBITS) - texture_data.projection.viewz
        worldbottom = (frontsector.floor_height << FRACBITS) - texture_data.projection.viewz
        if line.flags & ML_DONTPEGBOTTOM:
            rw_midtexturemid = (
                (frontsector.floor_height << FRACBITS)
                + texture.textureheight
                - texture_data.projection.viewz
            )
        else:
            rw_midtexturemid = worldtop
        rw_midtexturemid += sidedef.y_offset << FRACBITS

        rw_offset, rw_centerangle = stage09._rw_offset_for_seg(
            span, raw_seg, loaded, sidedef_index
        )
        topfrac = (CENTERYFRAC >> 4) - stage07.fixed_mul(worldtop >> 4, span.scale1)
        bottomfrac = (CENTERYFRAC >> 4) - stage07.fixed_mul(worldbottom >> 4, span.scale1)
        topstep = -stage07.fixed_mul(span.scalestep, worldtop >> 4)
        bottomstep = -stage07.fixed_mul(span.scalestep, worldbottom >> 4)
        scale = span.scale1

        for x in range(span.x1, span.x2 + 1):
            yl = (topfrac + HEIGHTUNIT - 1) >> HEIGHTBITS
            if yl < 0:
                yl = 0
            yh = bottomfrac >> HEIGHTBITS
            if yh >= FRAMEBUFFER_HEIGHT:
                yh = FRAMEBUFFER_HEIGHT - 1

            texturecolumn = _texture_column_for_x(span, rw_offset, rw_centerangle, x)
            iscale = 0xFFFFFFFF // scale
            lookup = r_get_column_direct_or_composite(
                wad, setup, texid, texturecolumn, composite_cache, direct_cache
            )
            if lookup.source_kind == "direct":
                mid_direct_columns_attempted += 1
            else:
                mid_composite_columns_attempted += 1

            if lookup.skip_reason == "short-composite":
                composite_skip_short_columns += 1
            elif lookup.skip_reason is not None:
                composite_skip_other_columns += 1
            elif yl > yh and lookup.source_kind == "composite":
                mid_composite_columns_clipped_empty += 1
            else:
                before_count = len(commands)
                framebuffer_signature, pixels_drawn, drew = _append_draw_command(
                    commands=commands,
                    column_sources=column_sources,
                    source_index_by_key=source_index_by_key,
                    palette32=palette32,
                    setup=setup,
                    lookup=lookup,
                    framebuffer_signature=framebuffer_signature,
                    pixels_drawn=pixels_drawn,
                    x=x,
                    yl=yl,
                    yh=yh,
                    iscale=iscale,
                    texturemid=rw_midtexturemid,
                    texture_id=texid,
                    tier="mid",
                )
                if drew and lookup.source_kind == "direct":
                    direct_columns_drawn += 1
                elif drew:
                    composite_columns_drawn += 1
                    mid_composite_columns_drawn += 1
                if len(commands) == before_count and lookup.source_kind == "composite":
                    mid_composite_columns_clipped_empty += 1

            topfrac += topstep
            bottomfrac += bottomstep
            scale += span.scalestep

    ceilingclip = [-1] * FRAMEBUFFER_WIDTH
    floorclip = [FRAMEBUFFER_HEIGHT] * FRAMEBUFFER_WIDTH

    # Two-sided edge pass: this is the new source-shaped clip-array proof.
    for span in texture_data.projection.projected_spans:
        raw_seg = raw_segs[span.seg_index]
        line = loaded.linedefs[raw_seg[3]]
        sidedef_index = _line_sidedef_index(line, raw_seg[4])
        sidedef = loaded.sidedefs[sidedef_index]
        resolved = texture_data.resolved_sidedefs[sidedef_index]
        backsector_index = _line_backsector_index(line, raw_seg[4], loaded)
        if backsector_index is None:
            continue

        two_sided_spans += 1
        frontsector_index = sidedef.sector
        frontsector = loaded.sectors[frontsector_index]
        backsector = loaded.sectors[backsector_index]
        worldtop = (frontsector.ceiling_height << FRACBITS) - texture_data.projection.viewz
        worldbottom = (frontsector.floor_height << FRACBITS) - texture_data.projection.viewz
        worldhigh = (backsector.ceiling_height << FRACBITS) - texture_data.projection.viewz
        worldlow = (backsector.floor_height << FRACBITS) - texture_data.projection.viewz

        if (
            texture_data.resolved_sectors[frontsector_index].ceilingpic == skyflatnum
            and texture_data.resolved_sectors[backsector_index].ceilingpic == skyflatnum
        ):
            worldtop = worldhigh

        markfloor = (
            worldlow != worldbottom
            or texture_data.resolved_sectors[backsector_index].floorpic
            != texture_data.resolved_sectors[frontsector_index].floorpic
            or backsector.light_level != frontsector.light_level
        )
        markceiling = (
            worldhigh != worldtop
            or texture_data.resolved_sectors[backsector_index].ceilingpic
            != texture_data.resolved_sectors[frontsector_index].ceilingpic
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
        rw_toptexturemid = 0
        rw_bottomtexturemid = 0

        if worldhigh < worldtop:
            toptexture = resolved.toptexture
            if toptexture:
                texture = setup.textures[toptexture]
                if line.flags & ML_DONTPEGTOP:
                    rw_toptexturemid = worldtop
                else:
                    rw_toptexturemid = (
                        (backsector.ceiling_height << FRACBITS)
                        + texture.textureheight
                        - texture_data.projection.viewz
                    )

        if worldlow > worldbottom:
            bottomtexture = resolved.bottomtexture
            if bottomtexture:
                if line.flags & ML_DONTPEGBOTTOM:
                    rw_bottomtexturemid = worldtop
                else:
                    rw_bottomtexturemid = worldlow

        rw_toptexturemid += sidedef.y_offset << FRACBITS
        rw_bottomtexturemid += sidedef.y_offset << FRACBITS

        if resolved.midtexture:
            masked_midtexture_skips += 1

        if not toptexture and not bottomtexture:
            two_sided_no_supported_edge_spans += 1
        else:
            two_sided_supported_edge_spans += 1

        if (frontsector.floor_height << FRACBITS) >= texture_data.projection.viewz:
            markfloor = False

        if (
            (frontsector.ceiling_height << FRACBITS) <= texture_data.projection.viewz
            and texture_data.resolved_sectors[frontsector_index].ceilingpic != skyflatnum
        ):
            markceiling = False

        segtextured = bool(toptexture or bottomtexture or resolved.midtexture)
        if segtextured:
            rw_offset, rw_centerangle = stage09._rw_offset_for_seg(
                span, raw_seg, loaded, sidedef_index
            )
        else:
            rw_offset = rw_centerangle = 0

        topfrac = (CENTERYFRAC >> 4) - stage07.fixed_mul(worldtop >> 4, span.scale1)
        bottomfrac = (CENTERYFRAC >> 4) - stage07.fixed_mul(
            worldbottom >> 4, span.scale1
        )
        topstep = -stage07.fixed_mul(span.scalestep, worldtop >> 4)
        bottomstep = -stage07.fixed_mul(span.scalestep, worldbottom >> 4)
        pixhigh = pixlow = pixhighstep = pixlowstep = 0

        if worldhigh < worldtop:
            pixhigh = (CENTERYFRAC >> 4) - stage07.fixed_mul(
                worldhigh >> 4, span.scale1
            )
            pixhighstep = -stage07.fixed_mul(span.scalestep, worldhigh >> 4)

        if worldlow > worldbottom:
            pixlow = (CENTERYFRAC >> 4) - stage07.fixed_mul(worldlow >> 4, span.scale1)
            pixlowstep = -stage07.fixed_mul(span.scalestep, worldlow >> 4)

        scale = span.scale1
        for x in range(span.x1, span.x2 + 1):
            clip = render_seg_loop_edge_clip_column(
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

            if clip.ceiling_mark is not None:
                plane_mark_ceiling_records += 1
                plane_marks.append(
                    PlaneMarkRecord(
                        "ceiling",
                        x,
                        clip.ceiling_mark[0],
                        clip.ceiling_mark[1],
                        span.seg_index,
                    )
                )
            if clip.floor_mark is not None:
                plane_mark_floor_records += 1
                plane_marks.append(
                    PlaneMarkRecord(
                        "floor", x, clip.floor_mark[0], clip.floor_mark[1], span.seg_index
                    )
                )

            texturecolumn = 0
            iscale = 0
            if toptexture or bottomtexture:
                texturecolumn = _texture_column_for_x(span, rw_offset, rw_centerangle, x)
                iscale = 0xFFFFFFFF // scale

            if toptexture:
                if clip.upper_yl is None or clip.upper_yh is None:
                    upper_columns_clipped_empty += 1
                else:
                    lookup = r_get_column_direct_or_composite(
                        wad, setup, toptexture, texturecolumn, composite_cache, direct_cache
                    )
                    if lookup.source_kind == "direct":
                        upper_direct_columns_attempted += 1
                    else:
                        upper_composite_columns_attempted += 1
                    if lookup.skip_reason == "short-composite":
                        composite_skip_short_columns += 1
                    elif lookup.skip_reason is not None:
                        composite_skip_other_columns += 1
                    else:
                        framebuffer_signature, pixels_drawn, drew = _append_draw_command(
                            commands=commands,
                            column_sources=column_sources,
                            source_index_by_key=source_index_by_key,
                            palette32=palette32,
                            setup=setup,
                            lookup=lookup,
                            framebuffer_signature=framebuffer_signature,
                            pixels_drawn=pixels_drawn,
                            x=x,
                            yl=clip.upper_yl,
                            yh=clip.upper_yh,
                            iscale=iscale,
                            texturemid=rw_toptexturemid,
                            texture_id=toptexture,
                            tier="upper",
                        )
                        if drew:
                            upper_columns_drawn += 1
                            if lookup.source_kind == "direct":
                                direct_columns_drawn += 1
                            else:
                                composite_columns_drawn += 1
                                upper_composite_columns_drawn += 1

            if bottomtexture:
                if clip.lower_yl is None or clip.lower_yh is None:
                    lower_columns_clipped_empty += 1
                else:
                    lookup = r_get_column_direct_or_composite(
                        wad,
                        setup,
                        bottomtexture,
                        texturecolumn,
                        composite_cache,
                        direct_cache,
                    )
                    if lookup.source_kind == "direct":
                        lower_direct_columns_attempted += 1
                    else:
                        lower_composite_columns_attempted += 1
                    if lookup.skip_reason == "short-composite":
                        composite_skip_short_columns += 1
                    elif lookup.skip_reason is not None:
                        composite_skip_other_columns += 1
                    else:
                        framebuffer_signature, pixels_drawn, drew = _append_draw_command(
                            commands=commands,
                            column_sources=column_sources,
                            source_index_by_key=source_index_by_key,
                            palette32=palette32,
                            setup=setup,
                            lookup=lookup,
                            framebuffer_signature=framebuffer_signature,
                            pixels_drawn=pixels_drawn,
                            x=x,
                            yl=clip.lower_yl,
                            yh=clip.lower_yh,
                            iscale=iscale,
                            texturemid=rw_bottomtexturemid,
                            texture_id=bottomtexture,
                            tier="lower",
                        )
                        if drew:
                            lower_columns_drawn += 1
                            if lookup.source_kind == "direct":
                                direct_columns_drawn += 1
                            else:
                                composite_columns_drawn += 1
                                lower_composite_columns_drawn += 1

            ceilingclip[x] = clip.ceilingclip
            floorclip[x] = clip.floorclip
            pixhigh = clip.pixhigh_next
            pixlow = clip.pixlow_next
            topfrac += topstep
            bottomfrac += bottomstep
            scale += span.scalestep

    first = commands[0] if commands else None
    last = commands[-1] if commands else None
    assert composite_cache.entries is not None

    return Stage10CompositeTwoSidedWallEdgesReference(
        stage09=stage09_ref,
        palette32=tuple(palette32),
        column_sources=tuple(column_sources),
        commands=tuple(commands),
        plane_mark_records=tuple(plane_marks),
        spans_considered=spans_considered,
        one_sided_spans=one_sided_spans,
        two_sided_spans=two_sided_spans,
        two_sided_supported_edge_spans=two_sided_supported_edge_spans,
        two_sided_no_supported_edge_spans=two_sided_no_supported_edge_spans,
        mid_direct_columns_attempted=mid_direct_columns_attempted,
        mid_composite_columns_attempted=mid_composite_columns_attempted,
        mid_composite_columns_drawn=mid_composite_columns_drawn,
        mid_composite_columns_clipped_empty=mid_composite_columns_clipped_empty,
        upper_direct_columns_attempted=upper_direct_columns_attempted,
        upper_composite_columns_attempted=upper_composite_columns_attempted,
        upper_columns_drawn=upper_columns_drawn,
        upper_composite_columns_drawn=upper_composite_columns_drawn,
        upper_columns_clipped_empty=upper_columns_clipped_empty,
        lower_direct_columns_attempted=lower_direct_columns_attempted,
        lower_composite_columns_attempted=lower_composite_columns_attempted,
        lower_columns_drawn=lower_columns_drawn,
        lower_composite_columns_drawn=lower_composite_columns_drawn,
        lower_columns_clipped_empty=lower_columns_clipped_empty,
        composite_cache_builds=composite_cache.builds,
        composite_cache_hits=composite_cache.hits,
        composite_cache_overflows=composite_cache.overflow,
        composite_cache_missing_columns=composite_cache.missing,
        composite_cache_bad_columns=composite_cache.bad_columns,
        composite_cache_entries=len(composite_cache.entries),
        direct_cache_entries=len(direct_cache),
        composite_skip_short_columns=composite_skip_short_columns,
        composite_skip_other_columns=composite_skip_other_columns,
        masked_midtexture_skips=masked_midtexture_skips,
        plane_mark_ceiling_records=plane_mark_ceiling_records,
        plane_mark_floor_records=plane_mark_floor_records,
        columns_drawn=len(commands),
        direct_columns_drawn=direct_columns_drawn,
        composite_columns_drawn=composite_columns_drawn,
        pixels_drawn=pixels_drawn,
        framebuffer_signature=framebuffer_signature,
        first_drawn_texture_id=first.texture_id if first else 0,
        first_drawn_texture_name=first.texture_name if first else "",
        first_drawn_texture_column=first.texture_column if first else 0,
        last_drawn_texture_id=last.texture_id if last else 0,
        last_drawn_texture_name=last.texture_name if last else "",
        last_drawn_texture_column=last.texture_column if last else 0,
    )


def _reference_for_default_wad_or_none() -> Stage10CompositeTwoSidedWallEdgesReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_composite_two_sided_wall_edges_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage10_load_wad_composite_two_sided_wall_edges_debug")

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


def emit_source_stage10_load_wad_composite_two_sided_wall_edges_debug(pe: PE32) -> None:
    pe.label("source_stage10_load_wad_composite_two_sided_wall_edges_debug")
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
    x86.jne_rel32(pe, "source_stage10_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage10_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage10_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage10_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage10_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage10_close_and_return")

    pe.label("source_stage10_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage10_close_and_return")

    x86.call_rel32(pe, "render_init_texture_data_setup_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage10_close_and_return")

    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage10_close_and_return")

    x86.call_rel32(pe, "source_stage06_run_live_seg_clip_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage10_close_and_return")

    x86.call_rel32(pe, "render_composite_two_sided_wall_edges_debug")
    x86.call_rel32(pe, "build_success_status")

    pe.label("source_stage10_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_render_composite_two_sided_wall_edges_debug(pe: PE32) -> None:
    pe.label("render_draw_column_in_cache_source_shape_debug")
    pe.label("render_generate_composite_cache_debug")
    pe.label("render_get_column_direct_or_composite_debug")
    pe.label("render_two_sided_wall_edges_debug")
    pe.label("render_plane_mark_records_debug")
    pe.label("render_composite_two_sided_wall_edges_debug")
    x86.mov_mem_abs32_imm32(pe, "stage10_columns_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage10_pixels_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage10_pixel_signature", FNV_OFFSET_BASIS)
    x86.mov_mem_abs32_abs32(pe, "dc_colormap", "stage10_palette32")

    x86.mov_reg_abs32(pe, "esi", "stage10_draw_commands")
    x86.mov_mem_abs32_reg(pe, "stage10_draw_scan_ptr", "esi")
    x86.mov_reg_mem_abs32(pe, "eax", "stage10_draw_command_count")
    x86.mov_mem_abs32_eax(pe, "stage10_draw_remaining")

    pe.label("stage10_draw_command_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "stage10_draw_remaining")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage10_draw_commands_done")

    x86.mov_reg_mem_abs32(pe, "esi", "stage10_draw_scan_ptr")
    x86.mov_mem_abs32_reg(pe, "stage10_current_command", "esi")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", DRAW_COMMAND_X)
    x86.mov_mem_abs32_eax(pe, "dc_x")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", DRAW_COMMAND_YL)
    x86.mov_mem_abs32_eax(pe, "dc_yl")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", DRAW_COMMAND_YH)
    x86.mov_mem_abs32_eax(pe, "dc_yh")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", DRAW_COMMAND_ISCALE)
    x86.mov_mem_abs32_eax(pe, "dc_iscale")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", DRAW_COMMAND_TEXTUREMID)
    x86.mov_mem_abs32_eax(pe, "dc_texturemid")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", DRAW_COMMAND_SOURCE)
    x86.mov_mem_abs32_eax(pe, "dc_source")

    stage07._emit_inc_abs32(pe, "stage10_columns_drawn")
    x86.call_rel32(pe, "render_draw_column_debug")

    x86.mov_reg_mem_abs32(pe, "esi", "stage10_draw_scan_ptr")
    x86.add_reg_imm32(pe, "esi", DRAW_COMMAND_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, "stage10_draw_scan_ptr", "esi")
    x86.dec_mem_abs32(pe, "stage10_draw_remaining")
    x86.jmp_rel32(pe, "stage10_draw_command_loop")

    pe.label("stage10_draw_commands_done")
    x86.ret(pe)


def emit_render_draw_column_debug(pe: PE32) -> None:
    pe.label("render_draw_column_debug")
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_reg_mem_abs32(pe, "eax", "dc_yh")
    x86.sub_reg_mem_abs32(pe, "eax", "dc_yl")
    x86.jl_rel32(pe, "stage10_draw_column_done")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "stage10_column_remaining")

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

    pe.label("stage10_draw_column_loop")
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

    x86.mov_reg_mem_abs32(pe, "ecx", "stage10_pixel_signature")
    x86.imul_reg_reg_imm32(pe, "ecx", "ecx", FNV_PRIME)
    x86.xor_reg_reg(pe, "ecx", "eax")
    x86.mov_mem_abs32_reg(pe, "stage10_pixel_signature", "ecx")
    stage07._emit_inc_abs32(pe, "stage10_pixels_drawn")

    x86.add_reg_imm32(pe, "edi", FRAMEBUFFER_WIDTH * 4)
    x86.mov_reg_mem_abs32(pe, "eax", "dc_frac")
    x86.add_reg_mem_abs32(pe, "eax", "dc_iscale")
    x86.mov_mem_abs32_eax(pe, "dc_frac")
    x86.dec_mem_abs32(pe, "stage10_column_remaining")
    x86.jne_rel32(pe, "stage10_draw_column_loop")

    pe.label("stage10_draw_column_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_build_success_status(pe: PE32) -> None:
    pe.label("build_success_status")
    x86.mov_reg_abs32(pe, "edi", "status_success_buffer")
    stage01.append_c_string_label(pe, "status_stage10_success_header")
    stage01.append_u32_label(pe, "status_clip_nodes_prefix", "clip_visited_node_count")
    stage01.append_u32_label(pe, "status_clip_subsectors_prefix", "clip_visited_subsector_count")
    stage01.append_u32_label(pe, "status_clip_segs_prefix", "clip_visited_seg_count")
    stage01.append_u32_label(pe, "status_clip_cull_prefix", "clip_culled_node_count")
    stage01.append_u32_label(pe, "status_projection_count_prefix", "projection_span_count")
    stage01.append_u32_label(pe, "status_texture_count_prefix", "stage08_numtextures")
    stage01.append_u32_label(pe, "status_stage09_columns_drawn_prefix", "stage09_columns_drawn")
    stage01.append_u32_label(pe, "status_stage09_signature_prefix", "stage09_pixel_signature")
    stage01.append_u32_label(pe, "status_stage10_cache_builds_prefix", "stage10_composite_cache_builds")
    stage01.append_u32_label(pe, "status_stage10_cache_hits_prefix", "stage10_composite_cache_hits")
    stage01.append_u32_label(pe, "status_stage10_mid_composite_drawn_prefix", "stage10_mid_composite_columns_drawn")
    stage01.append_u32_label(pe, "status_stage10_upper_columns_prefix", "stage10_upper_columns_drawn")
    stage01.append_u32_label(pe, "status_stage10_lower_columns_prefix", "stage10_lower_columns_drawn")
    stage01.append_u32_label(pe, "status_stage10_plane_mark_prefix", "stage10_plane_mark_records")
    stage01.append_u32_label(pe, "status_stage10_columns_drawn_prefix", "stage10_columns_drawn")
    stage01.append_u32_label(pe, "status_stage10_pixels_drawn_prefix", "stage10_pixels_drawn")
    stage01.append_u32_label(pe, "status_stage10_signature_prefix", "stage10_pixel_signature")
    stage01.append_c_string_label(pe, "status_stage10_note")
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
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def _emit_u32_table(pe: PE32, label: str, values: Sequence[int]) -> None:
    pe.label(label)
    for value in values:
        pe.emit_u32(value & 0xFFFFFFFF)


def _emit_stage09_preserved_data(
    pe: PE32, ref: Stage10CompositeTwoSidedWallEdgesReference | None
) -> None:
    s9 = ref.stage09 if ref is not None else None
    pe.label("stage09_direct_wall_spans_considered")
    pe.emit_u32(s9.direct_wall_spans_considered if s9 is not None else 0)
    pe.label("stage09_opaque_candidate_spans")
    pe.emit_u32(s9.opaque_candidate_spans if s9 is not None else 0)
    pe.label("stage09_direct_columns_attempted")
    pe.emit_u32(s9.direct_columns_attempted if s9 is not None else 0)
    pe.label("stage09_skipped_composite_columns")
    pe.emit_u32(s9.skipped_composite_columns if s9 is not None else 0)
    pe.label("stage09_skipped_unsupported_wall_cases")
    pe.emit_u32(s9.skipped_unsupported_wall_cases if s9 is not None else 0)
    pe.label("stage09_skipped_texture0_spans")
    pe.emit_u32(s9.skipped_texture0_spans if s9 is not None else 0)
    pe.label("stage09_skipped_masked_midtexture_spans")
    pe.emit_u32(s9.skipped_masked_midtexture_spans if s9 is not None else 0)
    pe.label("stage09_skipped_nonopaque_columns")
    pe.emit_u32(s9.skipped_nonopaque_columns if s9 is not None else 0)
    pe.label("stage09_columns_drawn")
    pe.emit_u32(s9.columns_drawn if s9 is not None else 0)
    pe.label("stage09_pixels_drawn")
    pe.emit_u32(s9.pixels_drawn if s9 is not None else 0)
    pe.label("stage09_pixel_signature")
    pe.emit_u32(s9.framebuffer_signature if s9 is not None else 0)
    pe.label("stage09_first_drawn_texture_id")
    pe.emit_u32(s9.first_drawn_texture_id if s9 is not None else 0)
    pe.label("stage09_first_drawn_texture_column")
    pe.emit_u32(s9.first_drawn_texture_column if s9 is not None else 0)
    pe.label("stage09_first_drawn_texture_name")
    x86.emit_asciiz(pe, s9.first_drawn_texture_name if s9 is not None else "")


def emit_stage10_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()

    pe.align_section(4)
    _emit_stage09_preserved_data(pe, ref)

    pe.label("stage10_spans_considered")
    pe.emit_u32(ref.spans_considered if ref is not None else 0)
    pe.label("stage10_one_sided_spans")
    pe.emit_u32(ref.one_sided_spans if ref is not None else 0)
    pe.label("stage10_two_sided_spans")
    pe.emit_u32(ref.two_sided_spans if ref is not None else 0)
    pe.label("stage10_two_sided_supported_edge_spans")
    pe.emit_u32(ref.two_sided_supported_edge_spans if ref is not None else 0)
    pe.label("stage10_two_sided_no_supported_edge_spans")
    pe.emit_u32(ref.two_sided_no_supported_edge_spans if ref is not None else 0)
    pe.label("stage10_mid_direct_columns_attempted")
    pe.emit_u32(ref.mid_direct_columns_attempted if ref is not None else 0)
    pe.label("stage10_mid_composite_columns_attempted")
    pe.emit_u32(ref.mid_composite_columns_attempted if ref is not None else 0)
    pe.label("stage10_mid_composite_columns_drawn")
    pe.emit_u32(ref.mid_composite_columns_drawn if ref is not None else 0)
    pe.label("stage10_mid_composite_columns_clipped_empty")
    pe.emit_u32(ref.mid_composite_columns_clipped_empty if ref is not None else 0)
    pe.label("stage10_upper_direct_columns_attempted")
    pe.emit_u32(ref.upper_direct_columns_attempted if ref is not None else 0)
    pe.label("stage10_upper_composite_columns_attempted")
    pe.emit_u32(ref.upper_composite_columns_attempted if ref is not None else 0)
    pe.label("stage10_upper_columns_drawn")
    pe.emit_u32(ref.upper_columns_drawn if ref is not None else 0)
    pe.label("stage10_upper_composite_columns_drawn")
    pe.emit_u32(ref.upper_composite_columns_drawn if ref is not None else 0)
    pe.label("stage10_upper_columns_clipped_empty")
    pe.emit_u32(ref.upper_columns_clipped_empty if ref is not None else 0)
    pe.label("stage10_lower_direct_columns_attempted")
    pe.emit_u32(ref.lower_direct_columns_attempted if ref is not None else 0)
    pe.label("stage10_lower_composite_columns_attempted")
    pe.emit_u32(ref.lower_composite_columns_attempted if ref is not None else 0)
    pe.label("stage10_lower_columns_drawn")
    pe.emit_u32(ref.lower_columns_drawn if ref is not None else 0)
    pe.label("stage10_lower_composite_columns_drawn")
    pe.emit_u32(ref.lower_composite_columns_drawn if ref is not None else 0)
    pe.label("stage10_lower_columns_clipped_empty")
    pe.emit_u32(ref.lower_columns_clipped_empty if ref is not None else 0)
    pe.label("stage10_composite_cache_builds")
    pe.emit_u32(ref.composite_cache_builds if ref is not None else 0)
    pe.label("stage10_composite_cache_hits")
    pe.emit_u32(ref.composite_cache_hits if ref is not None else 0)
    pe.label("stage10_composite_cache_overflows")
    pe.emit_u32(ref.composite_cache_overflows if ref is not None else 0)
    pe.label("stage10_composite_cache_missing_columns")
    pe.emit_u32(ref.composite_cache_missing_columns if ref is not None else 0)
    pe.label("stage10_composite_cache_bad_columns")
    pe.emit_u32(ref.composite_cache_bad_columns if ref is not None else 0)
    pe.label("stage10_composite_cache_entries")
    pe.emit_u32(ref.composite_cache_entries if ref is not None else 0)
    pe.label("stage10_direct_cache_entries")
    pe.emit_u32(ref.direct_cache_entries if ref is not None else 0)
    pe.label("stage10_composite_skip_short_columns")
    pe.emit_u32(ref.composite_skip_short_columns if ref is not None else 0)
    pe.label("stage10_composite_skip_other_columns")
    pe.emit_u32(ref.composite_skip_other_columns if ref is not None else 0)
    pe.label("stage10_masked_midtexture_skips")
    pe.emit_u32(ref.masked_midtexture_skips if ref is not None else 0)
    pe.label("stage10_plane_mark_ceiling_records")
    pe.emit_u32(ref.plane_mark_ceiling_records if ref is not None else 0)
    pe.label("stage10_plane_mark_floor_records")
    pe.emit_u32(ref.plane_mark_floor_records if ref is not None else 0)
    pe.label("stage10_plane_mark_records")
    pe.emit_u32(
        (ref.plane_mark_ceiling_records + ref.plane_mark_floor_records)
        if ref is not None
        else 0
    )
    pe.label("stage10_direct_columns_drawn")
    pe.emit_u32(ref.direct_columns_drawn if ref is not None else 0)
    pe.label("stage10_composite_columns_drawn")
    pe.emit_u32(ref.composite_columns_drawn if ref is not None else 0)
    pe.label("stage10_expected_columns_drawn")
    pe.emit_u32(ref.columns_drawn if ref is not None else 0)
    pe.label("stage10_expected_pixels_drawn")
    pe.emit_u32(ref.pixels_drawn if ref is not None else 0)
    pe.label("stage10_expected_pixel_signature")
    pe.emit_u32(ref.framebuffer_signature if ref is not None else 0)
    pe.label("stage10_first_drawn_texture_id")
    pe.emit_u32(ref.first_drawn_texture_id if ref is not None else 0)
    pe.label("stage10_first_drawn_texture_column")
    pe.emit_u32(ref.first_drawn_texture_column if ref is not None else 0)
    pe.label("stage10_last_drawn_texture_id")
    pe.emit_u32(ref.last_drawn_texture_id if ref is not None else 0)
    pe.label("stage10_last_drawn_texture_column")
    pe.emit_u32(ref.last_drawn_texture_column if ref is not None else 0)
    pe.label("stage10_draw_command_count")
    pe.emit_u32(len(ref.commands) if ref is not None else 0)

    pe.label("stage10_columns_drawn")
    pe.emit_u32(0)
    pe.label("stage10_pixels_drawn")
    pe.emit_u32(0)
    pe.label("stage10_pixel_signature")
    pe.emit_u32(0)
    pe.label("stage10_draw_scan_ptr")
    pe.emit_u32(0)
    pe.label("stage10_current_command")
    pe.emit_u32(0)
    pe.label("stage10_draw_remaining")
    pe.emit_u32(0)
    pe.label("stage10_column_remaining")
    pe.emit_u32(0)
    pe.label("dc_x")
    pe.emit_u32(0)
    pe.label("dc_yl")
    pe.emit_u32(0)
    pe.label("dc_yh")
    pe.emit_u32(0)
    pe.label("dc_iscale")
    pe.emit_u32(0)
    pe.label("dc_texturemid")
    pe.emit_u32(0)
    pe.label("dc_source")
    pe.emit_u32(0)
    pe.label("dc_colormap")
    pe.emit_u32(0)
    pe.label("dc_frac")
    pe.emit_u32(0)

    _emit_u32_table(pe, "stage10_palette32", list(ref.palette32) if ref is not None else [0] * 256)

    pe.align_section(4)
    pe.label("stage10_draw_commands")
    if ref is not None:
        for command in ref.commands:
            pe.emit_u32(command.x)
            pe.emit_u32(command.yl)
            pe.emit_u32(command.yh)
            pe.emit_u32(command.iscale)
            pe.emit_u32(command.texturemid)
            pe.write_abs32(f"stage10_column_source_{command.source_index}")

    pe.align_section(1)
    if ref is not None:
        for index, pixels in enumerate(ref.column_sources):
            pe.label(f"stage10_column_source_{index}")
            pe.emit(pixels)

    pe.align_section(1)
    pe.label("stage10_first_drawn_texture_name")
    x86.emit_asciiz(pe, ref.first_drawn_texture_name if ref is not None else "")
    pe.label("stage10_last_drawn_texture_name")
    x86.emit_asciiz(pe, ref.last_drawn_texture_name if ref is not None else "")

    pe.label("status_stage10_success_header")
    x86.emit_asciiz(
        pe,
        "source_stage10_composite_two_sided_wall_edges_debug\r\n"
        "Composite and two-sided wall edge debug OK\r\n",
    )
    pe.label("status_stage09_columns_drawn_prefix")
    x86.emit_asciiz(pe, "\r\nPreserved stage09 R_DrawColumn direct columns: ")
    pe.label("status_stage09_signature_prefix")
    x86.emit_asciiz(pe, "\r\nPreserved stage09 pixel signature: ")
    pe.label("status_stage10_cache_builds_prefix")
    x86.emit_asciiz(pe, "\r\nR_GenerateComposite cache builds: ")
    pe.label("status_stage10_cache_hits_prefix")
    x86.emit_asciiz(pe, "\r\nComposite cache hits: ")
    pe.label("status_stage10_mid_composite_drawn_prefix")
    x86.emit_asciiz(pe, "\r\nOne-sided composite midtexture columns drawn: ")
    pe.label("status_stage10_upper_columns_prefix")
    x86.emit_asciiz(pe, "\r\nTwo-sided upper wall columns drawn: ")
    pe.label("status_stage10_lower_columns_prefix")
    x86.emit_asciiz(pe, "\r\nTwo-sided lower wall columns drawn: ")
    pe.label("status_stage10_plane_mark_prefix")
    x86.emit_asciiz(pe, "\r\nR_CheckPlane mark records: ")
    pe.label("status_stage10_columns_drawn_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime stage10 R_DrawColumn columns drawn: ")
    pe.label("status_stage10_pixels_drawn_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime stage10 wall pixels drawn: ")
    pe.label("status_stage10_signature_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime stage10 pixel RGB signature: ")
    pe.label("status_stage10_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage10 uses source-shaped R_DrawColumnInCache, R_GenerateComposite, "
        "R_GetColumn, and R_RenderSegLoop wall-edge selection over table-emitted "
        "column bytes for the pinned view.\r\n",
    )

    pe.label("title_stage09_span_considered_prefix")
    x86.emit_asciiz(pe, " DWSP=")
    pe.label("title_stage09_candidate_spans_prefix")
    x86.emit_asciiz(pe, " OPQSP=")
    pe.label("title_stage09_columns_attempted_prefix")
    x86.emit_asciiz(pe, " DCOL=")
    pe.label("title_stage09_columns_drawn_prefix")
    x86.emit_asciiz(pe, " DRAW=")
    pe.label("title_stage09_composite_skip_prefix")
    x86.emit_asciiz(pe, " SKC=")
    pe.label("title_stage09_unsupported_skip_prefix")
    x86.emit_asciiz(pe, " SKU=")
    pe.label("title_stage09_texture0_skip_prefix")
    x86.emit_asciiz(pe, " ZTEX=")
    pe.label("title_stage09_masked_skip_prefix")
    x86.emit_asciiz(pe, " MASK=")
    pe.label("title_stage09_first_texture_id_prefix")
    x86.emit_asciiz(pe, " FTEX=")
    pe.label("title_stage09_first_texture_name_prefix")
    x86.emit_asciiz(pe, " FN=")
    pe.label("title_stage09_first_texture_column_prefix")
    x86.emit_asciiz(pe, " FCOL=")
    pe.label("title_stage09_pixels_drawn_prefix")
    x86.emit_asciiz(pe, " PIX=")
    pe.label("title_stage09_signature_prefix")
    x86.emit_asciiz(pe, " SIG=")

    pe.label("title_stage10_cache_builds_prefix")
    x86.emit_asciiz(pe, " CMB=")
    pe.label("title_stage10_cache_hits_prefix")
    x86.emit_asciiz(pe, " CMH=")
    pe.label("title_stage10_cache_overflow_prefix")
    x86.emit_asciiz(pe, " CMO=")
    pe.label("title_stage10_mid_composite_drawn_prefix")
    x86.emit_asciiz(pe, " MCOL=")
    pe.label("title_stage10_mid_composite_empty_prefix")
    x86.emit_asciiz(pe, " MCEMP=")
    pe.label("title_stage10_upper_columns_prefix")
    x86.emit_asciiz(pe, " UCOL=")
    pe.label("title_stage10_upper_composite_prefix")
    x86.emit_asciiz(pe, " UCOMP=")
    pe.label("title_stage10_lower_columns_prefix")
    x86.emit_asciiz(pe, " LCOL=")
    pe.label("title_stage10_plane_mark_prefix")
    x86.emit_asciiz(pe, " PM=")
    pe.label("title_stage10_first_texture_id_prefix")
    x86.emit_asciiz(pe, " F10TEX=")
    pe.label("title_stage10_first_texture_name_prefix")
    x86.emit_asciiz(pe, " F10N=")
    pe.label("title_stage10_last_texture_id_prefix")
    x86.emit_asciiz(pe, " L10TEX=")
    pe.label("title_stage10_last_texture_name_prefix")
    x86.emit_asciiz(pe, " L10N=")
    pe.label("title_stage10_columns_drawn_prefix")
    x86.emit_asciiz(pe, " TCOL=")
    pe.label("title_stage10_pixels_drawn_prefix")
    x86.emit_asciiz(pe, " TPIX=")
    pe.label("title_stage10_signature_prefix")
    x86.emit_asciiz(pe, " TSIG=")


def build_source_stage10_composite_two_sided_wall_edges_debug_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage10_load_wad_composite_two_sided_wall_edges_debug(pe)
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
    emit_render_composite_two_sided_wall_edges_debug(pe)
    emit_render_draw_column_debug(pe)
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
    emit_stage10_data(pe)
    return pe.build("entry")


def write_source_stage10_composite_two_sided_wall_edges_debug_exe(
    path: str | Path,
) -> bytes:
    image = build_source_stage10_composite_two_sided_wall_edges_debug_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the source-guided PE32 x86 composite/two-sided wall edge debug executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/source_stage10_composite_two_sided_wall_edges_debug.exe",
        help="path to write, default: build/source_stage10_composite_two_sided_wall_edges_debug.exe",
    )
    args = parser.parse_args()
    write_source_stage10_composite_two_sided_wall_edges_debug_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
