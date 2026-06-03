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
from tools import x86
from tools.map_loader import LineDef, LoadedMap, load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


FRAMEBUFFER_WIDTH = stage08.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage08.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage08.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage08.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage08.WINDOW_WIDTH
WINDOW_HEIGHT = stage08.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage09DirectWallColumnPixelsDebug"
WINDOW_TITLE = "Inference Doom S09 Direct Wall Pixels"
WAD_PATH = stage08.WAD_PATH

FRACBITS = stage08.FRACBITS
FRACUNIT = stage08.FRACUNIT
NF_SUBSECTOR = stage08.NF_SUBSECTOR

VIEW_ANGLE = stage08.VIEW_ANGLE
ANG90 = stage07.ANG90
ANG180 = stage08.ANG180
ANGLETOFINESHIFT = stage07.ANGLETOFINESHIFT
FINEANGLES = stage07.FINEANGLES
FINEMASK = FINEANGLES - 1
FINESINE = stage07.FINESINE
FINETANGENT = stage04.FINETANGENT
XTOVIEWANGLE = stage04.XTOVIEWANGLE

HEIGHTBITS = 12
HEIGHTUNIT = 1 << HEIGHTBITS
CENTER_Y = FRAMEBUFFER_HEIGHT // 2
CENTERYFRAC = CENTER_Y << FRACBITS
WALL_COLUMN_SOURCE_HEIGHT = 128
ML_DONTPEGBOTTOM = 16

FNV_OFFSET_BASIS = 2166136261
FNV_PRIME = 16777619

DRAW_COMMAND_X = 0
DRAW_COMMAND_YL = 4
DRAW_COMMAND_YH = 8
DRAW_COMMAND_ISCALE = 12
DRAW_COMMAND_TEXTUREMID = 16
DRAW_COMMAND_SOURCE = 20
DRAW_COMMAND_RECORD_SIZE = 24

SOURCE_TRACE = stage08.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/r_data.c",
        "R_GetColumn direct patch-backed path",
        "render_get_column_direct_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_draw.c",
        "R_DrawColumn",
        "render_draw_column_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_segs.c",
        "R_StoreWallRange one-sided midtexture setup",
        "render_direct_wall_column_pixels_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_segs.c",
        "R_RenderSegLoop midtexture branch",
        "render_direct_wall_column_pixels_debug",
    ),
    (
        "reference/chocolate-doom/src/v_patch.h",
        "patch_t/post_t column data",
        "stage09_direct_patch_column_decode_debug",
    ),
)


@dataclass(frozen=True)
class PatchColumnPost:
    topdelta: int
    pixels: bytes


@dataclass(frozen=True)
class DirectColumnResult:
    texture_column: int
    lump: int
    patch_column: int | None
    pixels: bytes | None
    skip_reason: str | None


@dataclass(frozen=True)
class WallColumnDrawCommand:
    x: int
    yl: int
    yh: int
    iscale: int
    texturemid: int
    source_index: int
    texture_id: int
    texture_name: str
    texture_column: int


@dataclass(frozen=True)
class DirectWallColumnPixelsReference:
    texture_data: stage08.TextureDataSetupReference
    palette32: tuple[int, ...]
    direct_columns: tuple[bytes, ...]
    commands: tuple[WallColumnDrawCommand, ...]
    direct_wall_spans_considered: int
    opaque_candidate_spans: int
    direct_columns_attempted: int
    columns_drawn: int
    skipped_composite_columns: int
    skipped_unsupported_wall_cases: int
    skipped_texture0_spans: int
    skipped_masked_midtexture_spans: int
    skipped_nonopaque_columns: int
    pixels_drawn: int
    first_drawn_texture_id: int
    first_drawn_texture_name: str
    first_drawn_texture_column: int
    framebuffer_signature: int


def _uint32(value: int) -> int:
    return value & 0xFFFFFFFF


def _int32(value: int) -> int:
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def _fine_index(angle: int) -> int:
    return (angle >> ANGLETOFINESHIFT) & FINEMASK


def parse_patch_column_posts(
    data: bytes, column_index: int, *, lump_name: str = "<patch>"
) -> tuple[PatchColumnPost, ...]:
    header = stage08.parse_patch_header(data, lump_name=lump_name)
    if column_index < 0 or column_index >= header.width:
        raise stage08.TextureFormatError(
            f"patch lump {lump_name} column index is outside bounds: {column_index}"
        )

    posts: list[PatchColumnPost] = []
    position = header.column_offsets[column_index]
    guard = 0
    while True:
        if position >= len(data):
            raise stage08.TextureFormatError(f"patch lump {lump_name} column is truncated")

        topdelta = data[position]
        if topdelta == 0xFF:
            break

        if position + 3 > len(data):
            raise stage08.TextureFormatError(f"patch lump {lump_name} post header is truncated")

        length = data[position + 1]
        pixel_start = position + 3
        pixel_end = pixel_start + length
        if pixel_end >= len(data):
            raise stage08.TextureFormatError(f"patch lump {lump_name} post pixels are truncated")

        posts.append(PatchColumnPost(topdelta=topdelta, pixels=data[pixel_start:pixel_end]))
        position = pixel_end + 1
        guard += 1
        if guard > 256:
            raise stage08.TextureFormatError(f"patch lump {lump_name} has too many posts")

    return tuple(posts)


def decode_opaque_direct_column(
    data: bytes,
    column_index: int,
    *,
    lump_name: str = "<patch>",
    height: int = WALL_COLUMN_SOURCE_HEIGHT,
) -> bytes | None:
    posts = parse_patch_column_posts(data, column_index, lump_name=lump_name)
    if len(posts) != 1:
        return None
    post = posts[0]
    if post.topdelta != 0 or len(post.pixels) < height:
        return None
    return post.pixels[:height]


def palette32_from_wad(wad: WadFile) -> tuple[int, ...]:
    playpal = wad.read_lump(wad.lumps[stage08.wad_get_num_for_name(wad, "PLAYPAL")])
    colormap = wad.read_lump(wad.lumps[stage08.wad_get_num_for_name(wad, "COLORMAP")])
    if len(playpal) < 256 * 3:
        raise stage08.TextureFormatError("PLAYPAL first palette is truncated")
    if len(colormap) < 256:
        raise stage08.TextureFormatError("COLORMAP first row is truncated")

    colors: list[int] = []
    for index in range(256):
        mapped = colormap[index]
        r, g, b = playpal[mapped * 3 : mapped * 3 + 3]
        colors.append((r << 16) | (g << 8) | b)
    return tuple(colors)


def r_get_column_direct(
    wad: WadFile,
    setup: stage08.TextureSetup,
    tex: int,
    col: int,
    column_cache: dict[tuple[int, int], bytes] | None = None,
) -> DirectColumnResult:
    texture = setup.textures[tex]
    texture_column = col & texture.texturewidthmask
    lump = texture.texturecolumnlump[texture_column]
    if lump <= 0:
        return DirectColumnResult(texture_column, lump, None, None, "composite")

    patch_lump = wad.lumps[lump]
    patch_data = wad.read_lump(patch_lump)
    wanted_column_offset = texture.texturecolumnofs[texture_column] - 3
    header = stage08.parse_patch_header(patch_data, lump_name=patch_lump.name)
    try:
        patch_column = header.column_offsets.index(wanted_column_offset)
    except ValueError:
        return DirectColumnResult(texture_column, lump, None, None, "bad-offset")

    key = (lump, patch_column)
    cached = column_cache.get(key) if column_cache is not None else None
    if cached is not None:
        return DirectColumnResult(texture_column, lump, patch_column, cached, None)

    pixels = decode_opaque_direct_column(patch_data, patch_column, lump_name=patch_lump.name)
    if pixels is None:
        return DirectColumnResult(texture_column, lump, patch_column, None, "non-opaque")

    if column_cache is not None:
        column_cache[key] = pixels
    return DirectColumnResult(texture_column, lump, patch_column, pixels, None)


def r_draw_column_pixels(
    source: bytes,
    palette32: Sequence[int],
    *,
    yl: int,
    yh: int,
    iscale: int,
    texturemid: int,
    center_y: int = CENTER_Y,
) -> tuple[tuple[int, ...], int]:
    count = yh - yl
    if count < 0:
        return (), FNV_OFFSET_BASIS

    frac = _int32(texturemid + (yl - center_y) * iscale)
    colors: list[int] = []
    signature = FNV_OFFSET_BASIS
    for _ in range(count + 1):
        palette_index = source[(frac >> FRACBITS) & 127]
        color = palette32[palette_index]
        colors.append(color)
        signature = ((signature * FNV_PRIME) & 0xFFFFFFFF) ^ color
        signature &= 0xFFFFFFFF
        frac = _int32(frac + iscale)
    return tuple(colors), signature


def _line_sidedef_index(line: LineDef, side: int) -> int:
    return line.right_sidedef if side == 0 else line.left_sidedef


def _line_backsector_index(line: LineDef, side: int, loaded: LoadedMap) -> int | None:
    if not (line.flags & stage08.ML_TWOSIDED):
        return None
    sidenum = line.left_sidedef if side == 0 else line.right_sidedef
    if sidenum == 0xFFFF or sidenum >= len(loaded.sidedefs):
        return None
    return loaded.sidedefs[sidenum].sector


def _rw_offset_for_seg(
    span: stage07.ProjectedSpan,
    raw_seg: Sequence[int],
    loaded: LoadedMap,
    sidedef_index: int,
) -> tuple[int, int]:
    sidedef = loaded.sidedefs[sidedef_index]
    v1 = loaded.vertices[raw_seg[0]]
    rw_angle1 = stage04.point_to_angle(v1.x << FRACBITS, v1.y << FRACBITS)
    rw_normalangle = _uint32((raw_seg[2] << FRACBITS) + ANG90)
    offsetangle = _uint32(rw_normalangle - rw_angle1)
    raw_offsetangle = offsetangle
    if offsetangle > ANG180:
        offsetangle = _uint32(-offsetangle)
    if offsetangle > ANG90:
        offsetangle = ANG90

    hyp = stage07.point_to_dist(v1.x << FRACBITS, v1.y << FRACBITS)
    rw_offset = stage07.fixed_mul(hyp, FINESINE[_fine_index(offsetangle)])
    if raw_offsetangle < ANG180:
        rw_offset = -rw_offset
    rw_offset += (sidedef.x_offset << FRACBITS) + (raw_seg[5] << FRACBITS)
    rw_centerangle = _uint32(ANG90 + VIEW_ANGLE - span.rw_normalangle)
    return rw_offset, rw_centerangle


def reference_direct_wall_column_pixels_for_pinned_map(
    wad_path: str | Path,
) -> DirectWallColumnPixelsReference:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    texture_data = stage08.reference_texture_data_setup_for_pinned_map(wad_path)
    setup = texture_data.texture_setup
    palette32 = palette32_from_wad(wad)
    map_lumps = wad.map_lumps("MAP01")
    raw_segs = stage02.parse_mapsegs(wad.read_lump(map_lumps.get("SEGS")))

    direct_wall_spans_considered = 0
    opaque_candidate_spans = 0
    direct_columns_attempted = 0
    columns_drawn = 0
    skipped_composite_columns = 0
    skipped_unsupported_wall_cases = 0
    skipped_texture0_spans = 0
    skipped_masked_midtexture_spans = 0
    skipped_nonopaque_columns = 0
    pixels_drawn = 0
    framebuffer_signature = FNV_OFFSET_BASIS
    first_drawn_texture_id = 0
    first_drawn_texture_name = ""
    first_drawn_texture_column = 0

    column_cache: dict[tuple[int, int], bytes] = {}
    source_index_by_key: dict[tuple[int, int], int] = {}
    direct_columns: list[bytes] = []
    commands: list[WallColumnDrawCommand] = []

    for span in texture_data.projection.projected_spans:
        direct_wall_spans_considered += 1
        raw_seg = raw_segs[span.seg_index]
        line = loaded.linedefs[raw_seg[3]]
        sidedef_index = _line_sidedef_index(line, raw_seg[4])
        resolved = texture_data.resolved_sidedefs[sidedef_index]
        backsector_index = _line_backsector_index(line, raw_seg[4], loaded)

        if backsector_index is not None:
            if resolved.midtexture != 0:
                skipped_masked_midtexture_spans += 1
            else:
                skipped_unsupported_wall_cases += 1
            continue

        texid = resolved.midtexture
        if texid == 0:
            skipped_texture0_spans += 1
            continue

        opaque_candidate_spans += 1
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

        rw_offset, rw_centerangle = _rw_offset_for_seg(span, raw_seg, loaded, sidedef_index)
        worldtop_step = worldtop >> 4
        worldbottom_step = worldbottom >> 4
        topfrac = (CENTERYFRAC >> 4) - stage07.fixed_mul(worldtop_step, span.scale1)
        bottomfrac = (CENTERYFRAC >> 4) - stage07.fixed_mul(worldbottom_step, span.scale1)
        topstep = -stage07.fixed_mul(span.scalestep, worldtop_step)
        bottomstep = -stage07.fixed_mul(span.scalestep, worldbottom_step)
        scale = span.scale1

        for x in range(span.x1, span.x2 + 1):
            yl = (topfrac + HEIGHTUNIT - 1) >> HEIGHTBITS
            if yl < 0:
                yl = 0
            yh = bottomfrac >> HEIGHTBITS
            if yh >= FRAMEBUFFER_HEIGHT:
                yh = FRAMEBUFFER_HEIGHT - 1

            angle = _fine_index(_uint32(rw_centerangle + XTOVIEWANGLE[x]))
            texturecolumn = (
                rw_offset - stage07.fixed_mul(FINETANGENT[angle], span.rw_distance)
            ) >> FRACBITS
            direct_columns_attempted += 1
            result = r_get_column_direct(wad, setup, texid, texturecolumn, column_cache)
            if result.skip_reason == "composite":
                skipped_composite_columns += 1
            elif result.skip_reason is not None or result.pixels is None or result.patch_column is None:
                skipped_nonopaque_columns += 1
            elif yl <= yh:
                key = (result.lump, result.patch_column)
                source_index = source_index_by_key.get(key)
                if source_index is None:
                    source_index = len(direct_columns)
                    source_index_by_key[key] = source_index
                    direct_columns.append(result.pixels)

                iscale = 0xFFFFFFFF // scale
                if columns_drawn == 0:
                    first_drawn_texture_id = texid
                    first_drawn_texture_name = texture.name
                    first_drawn_texture_column = result.texture_column
                commands.append(
                    WallColumnDrawCommand(
                        x=x,
                        yl=yl,
                        yh=yh,
                        iscale=iscale,
                        texturemid=rw_midtexturemid,
                        source_index=source_index,
                        texture_id=texid,
                        texture_name=texture.name,
                        texture_column=result.texture_column,
                    )
                )
                colors, _column_signature = r_draw_column_pixels(
                    result.pixels,
                    palette32,
                    yl=yl,
                    yh=yh,
                    iscale=iscale,
                    texturemid=rw_midtexturemid,
                )
                for color in colors:
                    framebuffer_signature = ((framebuffer_signature * FNV_PRIME) & 0xFFFFFFFF) ^ color
                    framebuffer_signature &= 0xFFFFFFFF
                pixels_drawn += len(colors)
                columns_drawn += 1
            else:
                skipped_nonopaque_columns += 1

            topfrac += topstep
            bottomfrac += bottomstep
            scale += span.scalestep

    return DirectWallColumnPixelsReference(
        texture_data=texture_data,
        palette32=tuple(palette32),
        direct_columns=tuple(direct_columns),
        commands=tuple(commands),
        direct_wall_spans_considered=direct_wall_spans_considered,
        opaque_candidate_spans=opaque_candidate_spans,
        direct_columns_attempted=direct_columns_attempted,
        columns_drawn=columns_drawn,
        skipped_composite_columns=skipped_composite_columns,
        skipped_unsupported_wall_cases=skipped_unsupported_wall_cases,
        skipped_texture0_spans=skipped_texture0_spans,
        skipped_masked_midtexture_spans=skipped_masked_midtexture_spans,
        skipped_nonopaque_columns=skipped_nonopaque_columns,
        pixels_drawn=pixels_drawn,
        first_drawn_texture_id=first_drawn_texture_id,
        first_drawn_texture_name=first_drawn_texture_name,
        first_drawn_texture_column=first_drawn_texture_column,
        framebuffer_signature=framebuffer_signature,
    )


def _reference_for_default_wad_or_none() -> DirectWallColumnPixelsReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_direct_wall_column_pixels_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage09_load_wad_direct_wall_column_pixels_debug")

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


def emit_source_stage09_load_wad_direct_wall_column_pixels_debug(pe: PE32) -> None:
    pe.label("source_stage09_load_wad_direct_wall_column_pixels_debug")
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
    x86.jne_rel32(pe, "source_stage09_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage09_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage09_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage09_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage09_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage09_close_and_return")

    pe.label("source_stage09_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage09_close_and_return")

    x86.call_rel32(pe, "render_init_texture_data_setup_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage09_close_and_return")

    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage09_close_and_return")

    x86.call_rel32(pe, "source_stage06_run_live_seg_clip_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage09_close_and_return")

    x86.call_rel32(pe, "render_direct_wall_column_pixels_debug")
    x86.call_rel32(pe, "build_success_status")

    pe.label("source_stage09_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_render_direct_wall_column_pixels_debug(pe: PE32) -> None:
    pe.label("stage09_direct_patch_column_decode_debug")
    pe.label("render_direct_wall_column_pixels_debug")
    x86.mov_mem_abs32_imm32(pe, "stage09_columns_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage09_pixels_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage09_pixel_signature", FNV_OFFSET_BASIS)
    x86.mov_mem_abs32_abs32(pe, "dc_colormap", "stage09_palette32")

    x86.mov_reg_abs32(pe, "esi", "stage09_draw_commands")
    x86.mov_mem_abs32_reg(pe, "stage09_draw_scan_ptr", "esi")
    x86.mov_reg_mem_abs32(pe, "eax", "stage09_draw_command_count")
    x86.mov_mem_abs32_eax(pe, "stage09_draw_remaining")

    pe.label("stage09_draw_command_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "stage09_draw_remaining")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage09_draw_commands_done")

    x86.mov_reg_mem_abs32(pe, "esi", "stage09_draw_scan_ptr")
    x86.mov_mem_abs32_reg(pe, "stage09_current_command", "esi")
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
    x86.call_rel32(pe, "render_get_column_direct_debug")
    x86.mov_mem_abs32_eax(pe, "dc_source")

    stage07._emit_inc_abs32(pe, "stage09_columns_drawn")
    x86.call_rel32(pe, "render_draw_column_debug")

    x86.mov_reg_mem_abs32(pe, "esi", "stage09_draw_scan_ptr")
    x86.add_reg_imm32(pe, "esi", DRAW_COMMAND_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, "stage09_draw_scan_ptr", "esi")
    x86.dec_mem_abs32(pe, "stage09_draw_remaining")
    x86.jmp_rel32(pe, "stage09_draw_command_loop")

    pe.label("stage09_draw_commands_done")
    x86.ret(pe)


def emit_render_get_column_direct_debug(pe: PE32) -> None:
    pe.label("render_get_column_direct_debug")
    x86.mov_reg_mem_abs32(pe, "esi", "stage09_current_command")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", DRAW_COMMAND_SOURCE)
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
    x86.jl_rel32(pe, "stage09_draw_column_done")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "stage09_column_remaining")

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

    pe.label("stage09_draw_column_loop")
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

    x86.mov_reg_mem_abs32(pe, "ecx", "stage09_pixel_signature")
    x86.imul_reg_reg_imm32(pe, "ecx", "ecx", FNV_PRIME)
    x86.xor_reg_reg(pe, "ecx", "eax")
    x86.mov_mem_abs32_reg(pe, "stage09_pixel_signature", "ecx")
    stage07._emit_inc_abs32(pe, "stage09_pixels_drawn")

    x86.add_reg_imm32(pe, "edi", FRAMEBUFFER_WIDTH * 4)
    x86.mov_reg_mem_abs32(pe, "eax", "dc_frac")
    x86.add_reg_mem_abs32(pe, "eax", "dc_iscale")
    x86.mov_mem_abs32_eax(pe, "dc_frac")
    x86.dec_mem_abs32(pe, "stage09_column_remaining")
    x86.jne_rel32(pe, "stage09_draw_column_loop")

    pe.label("stage09_draw_column_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_build_success_status(pe: PE32) -> None:
    pe.label("build_success_status")
    x86.mov_reg_abs32(pe, "edi", "status_success_buffer")
    stage01.append_c_string_label(pe, "status_stage09_success_header")
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
    stage01.append_u32_label(pe, "status_projection_count_prefix", "projection_span_count")
    stage01.append_u32_label(pe, "status_projection_min_distance_prefix", "projection_min_distance")
    stage01.append_u32_label(pe, "status_projection_max_distance_prefix", "projection_max_distance")
    stage01.append_u32_label(pe, "status_projection_min_scale_prefix", "projection_min_scale")
    stage01.append_u32_label(pe, "status_projection_max_scale_prefix", "projection_max_scale")
    stage01.append_u32_label(pe, "status_texture_count_prefix", "stage08_numtextures")
    stage01.append_u32_label(pe, "status_patch_name_count_prefix", "stage08_patch_name_count")
    stage01.append_u32_label(pe, "status_flat_count_prefix", "stage08_numflats")
    stage01.append_u32_label(pe, "status_direct_column_prefix", "stage08_direct_column_count")
    stage01.append_u32_label(pe, "status_composite_column_prefix", "stage08_composite_column_count")
    stage01.append_u32_label(pe, "status_stage09_span_considered_prefix", "stage09_direct_wall_spans_considered")
    stage01.append_u32_label(pe, "status_stage09_candidate_spans_prefix", "stage09_opaque_candidate_spans")
    stage01.append_u32_label(pe, "status_stage09_columns_attempted_prefix", "stage09_direct_columns_attempted")
    stage01.append_u32_label(pe, "status_stage09_columns_drawn_prefix", "stage09_columns_drawn")
    stage01.append_u32_label(pe, "status_stage09_composite_skip_prefix", "stage09_skipped_composite_columns")
    stage01.append_u32_label(pe, "status_stage09_unsupported_skip_prefix", "stage09_skipped_unsupported_wall_cases")
    stage01.append_u32_label(pe, "status_stage09_texture0_skip_prefix", "stage09_skipped_texture0_spans")
    stage01.append_u32_label(pe, "status_stage09_masked_skip_prefix", "stage09_skipped_masked_midtexture_spans")
    stage01.append_u32_label(pe, "status_stage09_nonopaque_skip_prefix", "stage09_skipped_nonopaque_columns")
    stage01.append_u32_label(pe, "status_stage09_pixels_drawn_prefix", "stage09_pixels_drawn")
    stage01.append_u32_label(pe, "status_stage09_first_texture_id_prefix", "stage09_first_drawn_texture_id")
    stage01.append_c_string_label(pe, "status_stage09_first_texture_name_prefix")
    stage01.append_c_string_label(pe, "stage09_first_drawn_texture_name")
    stage01.append_u32_label(pe, "status_stage09_first_texture_column_prefix", "stage09_first_drawn_texture_column")
    stage01.append_u32_label(pe, "status_stage09_signature_prefix", "stage09_pixel_signature")
    stage01.append_c_string_label(pe, "status_stage09_note")
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
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def _emit_u32_table(pe: PE32, label: str, values: Sequence[int]) -> None:
    pe.label(label)
    for value in values:
        pe.emit_u32(value & 0xFFFFFFFF)


def emit_stage09_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()

    pe.align_section(4)
    pe.label("stage09_direct_wall_spans_considered")
    pe.emit_u32(ref.direct_wall_spans_considered if ref is not None else 0)
    pe.label("stage09_opaque_candidate_spans")
    pe.emit_u32(ref.opaque_candidate_spans if ref is not None else 0)
    pe.label("stage09_direct_columns_attempted")
    pe.emit_u32(ref.direct_columns_attempted if ref is not None else 0)
    pe.label("stage09_skipped_composite_columns")
    pe.emit_u32(ref.skipped_composite_columns if ref is not None else 0)
    pe.label("stage09_skipped_unsupported_wall_cases")
    pe.emit_u32(ref.skipped_unsupported_wall_cases if ref is not None else 0)
    pe.label("stage09_skipped_texture0_spans")
    pe.emit_u32(ref.skipped_texture0_spans if ref is not None else 0)
    pe.label("stage09_skipped_masked_midtexture_spans")
    pe.emit_u32(ref.skipped_masked_midtexture_spans if ref is not None else 0)
    pe.label("stage09_skipped_nonopaque_columns")
    pe.emit_u32(ref.skipped_nonopaque_columns if ref is not None else 0)
    pe.label("stage09_expected_columns_drawn")
    pe.emit_u32(ref.columns_drawn if ref is not None else 0)
    pe.label("stage09_expected_pixels_drawn")
    pe.emit_u32(ref.pixels_drawn if ref is not None else 0)
    pe.label("stage09_expected_pixel_signature")
    pe.emit_u32(ref.framebuffer_signature if ref is not None else 0)
    pe.label("stage09_first_drawn_texture_id")
    pe.emit_u32(ref.first_drawn_texture_id if ref is not None else 0)
    pe.label("stage09_first_drawn_texture_column")
    pe.emit_u32(ref.first_drawn_texture_column if ref is not None else 0)
    pe.label("stage09_draw_command_count")
    pe.emit_u32(len(ref.commands) if ref is not None else 0)

    pe.label("stage09_columns_drawn")
    pe.emit_u32(0)
    pe.label("stage09_pixels_drawn")
    pe.emit_u32(0)
    pe.label("stage09_pixel_signature")
    pe.emit_u32(0)
    pe.label("stage09_draw_scan_ptr")
    pe.emit_u32(0)
    pe.label("stage09_current_command")
    pe.emit_u32(0)
    pe.label("stage09_draw_remaining")
    pe.emit_u32(0)
    pe.label("stage09_column_remaining")
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

    _emit_u32_table(pe, "stage09_palette32", list(ref.palette32) if ref is not None else [0] * 256)

    pe.align_section(4)
    pe.label("stage09_draw_commands")
    if ref is not None:
        for command in ref.commands:
            pe.emit_u32(command.x)
            pe.emit_u32(command.yl)
            pe.emit_u32(command.yh)
            pe.emit_u32(command.iscale)
            pe.emit_u32(command.texturemid)
            pe.write_abs32(f"stage09_direct_column_{command.source_index}")

    pe.align_section(1)
    if ref is not None:
        for index, pixels in enumerate(ref.direct_columns):
            pe.label(f"stage09_direct_column_{index}")
            pe.emit(pixels)

    pe.align_section(1)
    pe.label("stage09_first_drawn_texture_name")
    x86.emit_asciiz(pe, ref.first_drawn_texture_name if ref is not None else "")

    pe.label("status_stage09_success_header")
    x86.emit_asciiz(pe, "source_stage09_direct_wall_column_pixels_debug\r\nDirect wall column pixels debug OK\r\n")
    pe.label("status_stage09_span_considered_prefix")
    x86.emit_asciiz(pe, "\r\nProjected spans considered for direct wall pixels: ")
    pe.label("status_stage09_candidate_spans_prefix")
    x86.emit_asciiz(pe, "\r\nOne-sided opaque midtexture spans: ")
    pe.label("status_stage09_columns_attempted_prefix")
    x86.emit_asciiz(pe, "\r\nDirect R_GetColumn columns attempted: ")
    pe.label("status_stage09_columns_drawn_prefix")
    x86.emit_asciiz(pe, "\r\nR_DrawColumn direct columns drawn: ")
    pe.label("status_stage09_composite_skip_prefix")
    x86.emit_asciiz(pe, "\r\nSkipped composite-needed columns: ")
    pe.label("status_stage09_unsupported_skip_prefix")
    x86.emit_asciiz(pe, "\r\nSkipped unsupported two-sided/non-opaque spans: ")
    pe.label("status_stage09_texture0_skip_prefix")
    x86.emit_asciiz(pe, "\r\nSkipped texture id 0 spans: ")
    pe.label("status_stage09_masked_skip_prefix")
    x86.emit_asciiz(pe, "\r\nSkipped masked midtexture spans: ")
    pe.label("status_stage09_nonopaque_skip_prefix")
    x86.emit_asciiz(pe, "\r\nSkipped direct non-opaque columns: ")
    pe.label("status_stage09_pixels_drawn_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime wall pixels drawn: ")
    pe.label("status_stage09_first_texture_id_prefix")
    x86.emit_asciiz(pe, "\r\nFirst drawn texture ID: ")
    pe.label("status_stage09_first_texture_name_prefix")
    x86.emit_asciiz(pe, "\r\nFirst drawn texture name: ")
    pe.label("status_stage09_first_texture_column_prefix")
    x86.emit_asciiz(pe, "\r\nFirst drawn texture column: ")
    pe.label("status_stage09_signature_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime pixel RGB signature: ")
    pe.label("status_stage09_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage09 table-emits PLAYPAL/COLORMAP row 0 RGB values and direct patch-backed "
        "opaque column bytes selected via texturecolumnlump/texturecolumnofs. "
        "Composite caching, plane spans, actors, sky, and translucent walls stay deferred.\r\n",
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


def build_source_stage09_direct_wall_column_pixels_debug_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage09_load_wad_direct_wall_column_pixels_debug(pe)
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
    emit_render_direct_wall_column_pixels_debug(pe)
    emit_render_get_column_direct_debug(pe)
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
    emit_stage09_data(pe)
    return pe.build("entry")


def write_source_stage09_direct_wall_column_pixels_debug_exe(path: str | Path) -> bytes:
    image = build_source_stage09_direct_wall_column_pixels_debug_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the source-guided PE32 x86 direct wall column pixels debug executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/source_stage09_direct_wall_column_pixels_debug.exe",
        help="path to write, default: build/source_stage09_direct_wall_column_pixels_debug.exe",
    )
    args = parser.parse_args()
    write_source_stage09_direct_wall_column_pixels_debug_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
