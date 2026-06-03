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
from tools import emit_source_stage03_bsp_walk_debug as stage03
from tools import emit_source_stage04_bbox_visibility_debug as stage04
from tools import emit_source_stage07_wall_projection_debug as stage07
from tools import x86
from tools.map_loader import LineDef, LoadedMap, load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile, normalize_name


FRAMEBUFFER_WIDTH = stage07.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage07.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage07.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage07.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage07.WINDOW_WIDTH
WINDOW_HEIGHT = stage07.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage08TextureDataSetupDebug"
WINDOW_TITLE = "Inference Doom S08 Texture Data Setup"
WAD_PATH = stage07.WAD_PATH

FRACBITS = stage07.FRACBITS
FRACUNIT = stage07.FRACUNIT
NF_SUBSECTOR = stage07.NF_SUBSECTOR

VIEW_X_FIXED = stage07.VIEW_X_FIXED
VIEW_Y_FIXED = stage07.VIEW_Y_FIXED
VIEW_ANGLE = stage07.VIEW_ANGLE

ANG180 = stage07.ANG180
CLIPANGLE = stage07.CLIPANGLE
ML_TWOSIDED = stage07.ML_TWOSIDED

SECTOR_FLOORHEIGHT = stage07.SECTOR_FLOORHEIGHT
SECTOR_CEILINGHEIGHT = stage07.SECTOR_CEILINGHEIGHT
SECTOR_LIGHTLEVEL = stage07.SECTOR_LIGHTLEVEL

SPAN_REASON_SOLID = stage07.SPAN_REASON_SOLID
SPAN_REASON_PASS = stage07.SPAN_REASON_PASS

MAX_TEXTURES = 4096
MAX_PATCH_NAMES = 8192
MAX_TEXTURE_WIDTH = 4096
MAX_TEXTURE_HEIGHT = 4096
MAX_TEXTURE_PATCHES = 2048
MAX_TOTAL_TEXTURE_COLUMNS = 512 * 1024
MAX_TOTAL_TEXPATCHES = 128 * 1024

MAPTEXTURE_HEADER_SIZE = 22
MAPPATCH_RECORD_SIZE = 10
PATCH_HEADER_SIZE = 8

SOURCE_TRACE = stage07.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/r_data.c",
        "R_InitTextures",
        "render_init_texture_data_setup_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_data.c",
        "R_GenerateLookup metadata/column directory",
        "render_generate_lookup_metadata_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_data.c",
        "R_InitFlats",
        "render_init_flats_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_data.c",
        "R_CheckTextureNumForName",
        "render_check_texture_num_for_name_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_data.c",
        "R_TextureNumForName",
        "render_texture_num_for_name_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_data.c",
        "R_FlatNumForName",
        "render_flat_num_for_name_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_setup.c",
        "P_LoadSideDefs texture ID resolution",
        "map_load_sidedefs_texture_ids_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_setup.c",
        "P_LoadSectors flat ID resolution",
        "map_load_sectors_flat_ids_debug",
    ),
)


class TextureFormatError(ValueError):
    """Raised when source texture metadata is malformed or outside bounds."""


@dataclass(frozen=True)
class PatchHeader:
    width: int
    height: int
    column_offsets: tuple[int, ...]


@dataclass(frozen=True)
class TexturePatch:
    originx: int
    originy: int
    patch_name_index: int
    patch_lump: int
    patch_name: str


@dataclass(frozen=True)
class TextureMetadata:
    index: int
    name: str
    width: int
    height: int
    patches: tuple[TexturePatch, ...]
    texturewidthmask: int
    textureheight: int
    texturecolumnlump: tuple[int, ...]
    texturecolumnofs: tuple[int, ...]
    texturecompositesize: int
    direct_columns: int
    composite_columns: int
    missing_columns: int


@dataclass(frozen=True)
class TextureSetup:
    patch_names: tuple[str, ...]
    patch_lumps: tuple[int, ...]
    textures: tuple[TextureMetadata, ...]
    texturetranslation: tuple[int, ...]
    textures_hashtable: tuple[tuple[int, ...], ...]
    firstflat: int
    lastflat: int
    numflats: int
    flattranslation: tuple[int, ...]
    texture2_present: bool
    texture1_count: int
    texture2_count: int

    @property
    def numtextures(self) -> int:
        return len(self.textures)

    @property
    def direct_column_count(self) -> int:
        return sum(texture.direct_columns for texture in self.textures)

    @property
    def composite_column_count(self) -> int:
        return sum(texture.composite_columns for texture in self.textures)

    @property
    def missing_column_count(self) -> int:
        return sum(texture.missing_columns for texture in self.textures)

    @property
    def texpatch_count(self) -> int:
        return sum(len(texture.patches) for texture in self.textures)


@dataclass(frozen=True)
class ResolvedSideDefTextures:
    toptexture: int
    bottomtexture: int
    midtexture: int


@dataclass(frozen=True)
class ResolvedSectorFlats:
    floorpic: int
    ceilingpic: int


@dataclass(frozen=True)
class TextureDataSetupReference:
    projection: stage07.WallProjectionReference
    texture_setup: TextureSetup
    resolved_sidedefs: tuple[ResolvedSideDefTextures, ...]
    resolved_sectors: tuple[ResolvedSectorFlats, ...]
    numeric_clip: stage07.SegClipReference
    first_projected_texture_id: int
    last_projected_texture_id: int
    first_projected_sidedef_id: int
    last_projected_sidedef_id: int
    no_midtexture_sidedef_count: int
    sidedef_texture_resolution_count: int
    sector_flat_resolution_count: int


def _decode_fixed_name(raw_name: bytes) -> str:
    name_bytes = raw_name.split(b"\x00", 1)[0]
    try:
        return name_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise TextureFormatError("texture name field is not ASCII") from exc


def _fixed_name_bytes(name: str) -> bytes:
    encoded = name.encode("ascii")
    if len(encoded) > 8:
        raise ValueError("fixed WAD names are limited to 8 bytes")
    return encoded.ljust(8, b"\x00")


def lump_name_hash(name: str) -> int:
    result = 5381
    for char in name[:8]:
        if char == "\x00":
            break
        result = ((result << 5) ^ result) ^ ord(char.upper())
        result &= 0xFFFFFFFF
    return result


def wad_check_num_for_name(wad: WadFile, name: str) -> int:
    wanted = normalize_name(name)
    for lump in reversed(wad.lumps):
        if normalize_name(lump.name) == wanted:
            return lump.index
    return -1


def wad_get_num_for_name(wad: WadFile, name: str) -> int:
    result = wad_check_num_for_name(wad, name)
    if result == -1:
        raise TextureFormatError(f"required lump not found: {name}")
    return result


def parse_pnames(data: bytes, wad: WadFile) -> tuple[tuple[str, ...], tuple[int, ...]]:
    if len(data) < 4:
        raise TextureFormatError("PNAMES lump is too small")

    (count,) = struct.unpack_from("<i", data, 0)
    if count < 0 or count > MAX_PATCH_NAMES:
        raise TextureFormatError(f"PNAMES patch count is outside bounds: {count}")

    expected = 4 + count * 8
    if expected > len(data):
        raise TextureFormatError("PNAMES lump is truncated")

    names: list[str] = []
    lump_indexes: list[int] = []
    for index in range(count):
        name = _decode_fixed_name(data[4 + index * 8 : 12 + index * 8])
        names.append(name)
        lump_indexes.append(wad_check_num_for_name(wad, name))

    return tuple(names), tuple(lump_indexes)


def parse_patch_header(data: bytes, *, lump_name: str) -> PatchHeader:
    if len(data) < PATCH_HEADER_SIZE:
        raise TextureFormatError(f"patch lump {lump_name} is too small")

    width, height, _leftoffset, _topoffset = struct.unpack_from("<hhhh", data, 0)
    if width < 0 or width > MAX_TEXTURE_WIDTH:
        raise TextureFormatError(f"patch lump {lump_name} width is outside bounds: {width}")
    if height < 0 or height > MAX_TEXTURE_HEIGHT:
        raise TextureFormatError(f"patch lump {lump_name} height is outside bounds: {height}")

    directory_end = PATCH_HEADER_SIZE + width * 4
    if directory_end > len(data):
        raise TextureFormatError(f"patch lump {lump_name} column directory is truncated")

    column_offsets = struct.unpack_from(f"<{width}I", data, PATCH_HEADER_SIZE) if width else ()
    return PatchHeader(width=width, height=height, column_offsets=tuple(column_offsets))


def _texture_width_mask(width: int) -> int:
    value = 1
    while value * 2 <= width:
        value <<= 1
    return value - 1


def _read_patch_header_for_lump(wad: WadFile, lump_index: int) -> PatchHeader:
    if lump_index < 0 or lump_index >= len(wad.lumps):
        raise TextureFormatError(f"patch lump index is outside WAD bounds: {lump_index}")
    lump = wad.lumps[lump_index]
    return parse_patch_header(wad.read_lump(lump), lump_name=lump.name)


def parse_texture_lump(
    data: bytes,
    *,
    lump_name: str,
    wad: WadFile,
    patch_names: Sequence[str],
    patch_lumps: Sequence[int],
    first_texture_index: int = 0,
    max_total_columns: int = MAX_TOTAL_TEXTURE_COLUMNS,
) -> tuple[TextureMetadata, ...]:
    if len(data) < 4:
        raise TextureFormatError(f"{lump_name} lump is too small")

    (count,) = struct.unpack_from("<i", data, 0)
    if count < 0 or count > MAX_TEXTURES:
        raise TextureFormatError(f"{lump_name} texture count is outside bounds: {count}")

    directory_end = 4 + count * 4
    if directory_end > len(data):
        raise TextureFormatError(f"{lump_name} directory is truncated")

    offsets = struct.unpack_from(f"<{count}i", data, 4) if count else ()
    textures: list[TextureMetadata] = []
    total_columns = 0
    total_patches = 0

    for local_index, offset in enumerate(offsets):
        if offset < directory_end or offset + MAPTEXTURE_HEADER_SIZE > len(data):
            raise TextureFormatError(f"{lump_name} has a bad texture directory entry")

        name = _decode_fixed_name(data[offset : offset + 8])
        width, height, _obsolete, patchcount = struct.unpack_from("<hhih", data, offset + 12)
        if width <= 0 or width > MAX_TEXTURE_WIDTH:
            raise TextureFormatError(f"texture {name} width is outside bounds: {width}")
        if height <= 0 or height > MAX_TEXTURE_HEIGHT:
            raise TextureFormatError(f"texture {name} height is outside bounds: {height}")
        if patchcount < 0 or patchcount > MAX_TEXTURE_PATCHES:
            raise TextureFormatError(f"texture {name} patch count is outside bounds: {patchcount}")

        total_columns += width
        total_patches += patchcount
        if total_columns > max_total_columns:
            raise TextureFormatError("bounded texture-column arena overflow")
        if total_patches > MAX_TOTAL_TEXPATCHES:
            raise TextureFormatError("bounded texture-patch arena overflow")

        patch_data_start = offset + MAPTEXTURE_HEADER_SIZE
        patch_data_end = patch_data_start + patchcount * MAPPATCH_RECORD_SIZE
        if patch_data_end > len(data):
            raise TextureFormatError(f"texture {name} patch directory is truncated")

        patches: list[TexturePatch] = []
        patch_column_headers: list[PatchHeader] = []
        for patch_index in range(patchcount):
            entry = patch_data_start + patch_index * MAPPATCH_RECORD_SIZE
            originx, originy, patch_name_index, _stepdir, _colormap = struct.unpack_from(
                "<hhhhh", data, entry
            )
            if patch_name_index < 0 or patch_name_index >= len(patch_names):
                raise TextureFormatError(f"texture {name} references a bad PNAMES index")
            patch_lump = patch_lumps[patch_name_index]
            if patch_lump == -1:
                raise TextureFormatError(
                    f"R_InitTextures: Missing patch in texture {name}"
                )
            patches.append(
                TexturePatch(
                    originx=originx,
                    originy=originy,
                    patch_name_index=patch_name_index,
                    patch_lump=patch_lump,
                    patch_name=patch_names[patch_name_index],
                )
            )
            patch_column_headers.append(_read_patch_header_for_lump(wad, patch_lump))

        column_counts = [0] * width
        column_lumps = [0] * width
        column_offsets = [0] * width
        for patch, patch_header in zip(patches, patch_column_headers):
            x1 = patch.originx
            x2 = x1 + patch_header.width
            x = 0 if x1 < 0 else x1
            x2 = min(x2, width)
            while x < x2:
                patch_column_index = x - x1
                column_counts[x] += 1
                column_lumps[x] = patch.patch_lump
                column_offsets[x] = patch_header.column_offsets[patch_column_index] + 3
                x += 1

        composite_size = 0
        direct_columns = 0
        composite_columns = 0
        missing_columns = 0
        for column, count_for_column in enumerate(column_counts):
            if count_for_column == 0:
                missing_columns += 1
                continue
            if count_for_column == 1:
                direct_columns += 1
                continue

            column_lumps[column] = -1
            column_offsets[column] = composite_size
            if composite_size > 0x10000 - height:
                raise TextureFormatError(f"R_GenerateLookup: texture {first_texture_index + local_index} is >64k")
            composite_size += height
            composite_columns += 1

        textures.append(
            TextureMetadata(
                index=first_texture_index + local_index,
                name=name,
                width=width,
                height=height,
                patches=tuple(patches),
                texturewidthmask=_texture_width_mask(width),
                textureheight=height << FRACBITS,
                texturecolumnlump=tuple(column_lumps),
                texturecolumnofs=tuple(column_offsets),
                texturecompositesize=composite_size,
                direct_columns=direct_columns,
                composite_columns=composite_columns,
                missing_columns=missing_columns,
            )
        )

    return tuple(textures)


def generate_texture_hash_table(textures: Sequence[TextureMetadata]) -> tuple[tuple[int, ...], ...]:
    if not textures:
        return ()

    buckets: list[list[int]] = [[] for _ in textures]
    for index, texture in enumerate(textures):
        key = lump_name_hash(texture.name) % len(textures)
        buckets[key].append(index)
    return tuple(tuple(bucket) for bucket in buckets)


def load_texture_setup_from_wad(wad: WadFile) -> TextureSetup:
    pnames_lump = wad.lumps[wad_get_num_for_name(wad, "PNAMES")]
    patch_names, patch_lumps = parse_pnames(wad.read_lump(pnames_lump), wad)

    texture1_lump = wad.lumps[wad_get_num_for_name(wad, "TEXTURE1")]
    textures1 = parse_texture_lump(
        wad.read_lump(texture1_lump),
        lump_name="TEXTURE1",
        wad=wad,
        patch_names=patch_names,
        patch_lumps=patch_lumps,
    )

    texture2_index = wad_check_num_for_name(wad, "TEXTURE2")
    if texture2_index != -1:
        texture2_lump = wad.lumps[texture2_index]
        textures2 = parse_texture_lump(
            wad.read_lump(texture2_lump),
            lump_name="TEXTURE2",
            wad=wad,
            patch_names=patch_names,
            patch_lumps=patch_lumps,
            first_texture_index=len(textures1),
        )
    else:
        textures2 = ()

    textures = textures1 + textures2
    firstflat = wad_get_num_for_name(wad, "F_START") + 1
    lastflat = wad_get_num_for_name(wad, "F_END") - 1
    numflats = lastflat - firstflat + 1
    if numflats < 0:
        raise TextureFormatError("flat lump range is inverted")

    return TextureSetup(
        patch_names=tuple(patch_names),
        patch_lumps=tuple(patch_lumps),
        textures=textures,
        texturetranslation=tuple(range(len(textures))),
        textures_hashtable=generate_texture_hash_table(textures),
        firstflat=firstflat,
        lastflat=lastflat,
        numflats=numflats,
        flattranslation=tuple(range(numflats)),
        texture2_present=bool(textures2),
        texture1_count=len(textures1),
        texture2_count=len(textures2),
    )


def r_check_texture_num_for_name(setup: TextureSetup, name: str) -> int:
    if name.startswith("-"):
        return 0
    if setup.numtextures == 0:
        return -1

    key = lump_name_hash(name) % setup.numtextures
    for texture_index in setup.textures_hashtable[key]:
        if setup.textures[texture_index].name[:8].upper() == name[:8].upper():
            return texture_index
    return -1


def r_texture_num_for_name(setup: TextureSetup, name: str) -> int:
    result = r_check_texture_num_for_name(setup, name)
    if result == -1:
        raise TextureFormatError(f"R_TextureNumForName: {name} not found")
    return result


def r_flat_num_for_name(wad: WadFile, setup: TextureSetup, name: str) -> int:
    lump_index = wad_check_num_for_name(wad, name)
    if lump_index == -1:
        raise TextureFormatError(f"R_FlatNumForName: {name} not found")
    return lump_index - setup.firstflat


def resolve_sidedef_texture_ids(
    loaded: LoadedMap, setup: TextureSetup
) -> tuple[ResolvedSideDefTextures, ...]:
    return tuple(
        ResolvedSideDefTextures(
            toptexture=r_texture_num_for_name(setup, sidedef.upper_texture),
            bottomtexture=r_texture_num_for_name(setup, sidedef.lower_texture),
            midtexture=r_texture_num_for_name(setup, sidedef.middle_texture),
        )
        for sidedef in loaded.sidedefs
    )


def resolve_sector_flat_ids(
    wad: WadFile, loaded: LoadedMap, setup: TextureSetup
) -> tuple[ResolvedSectorFlats, ...]:
    return tuple(
        ResolvedSectorFlats(
            floorpic=r_flat_num_for_name(wad, setup, sector.floor_flat),
            ceilingpic=r_flat_num_for_name(wad, setup, sector.ceiling_flat),
        )
        for sector in loaded.sectors
    )


def _line_backsector_index(line: LineDef, side: int, loaded: LoadedMap) -> int | None:
    if not (line.flags & ML_TWOSIDED):
        return None
    sidenum = line.left_sidedef if side == 0 else line.right_sidedef
    if sidenum == 0xFFFF or sidenum >= len(loaded.sidedefs):
        return None
    return loaded.sidedefs[sidenum].sector


def _line_sidedef_index(line: LineDef, side: int) -> int:
    return line.right_sidedef if side == 0 else line.left_sidedef


def debug_add_line_texture_ids(
    state: stage07.SegClipDebugState,
    seg: stage07.DebugSeg,
    loaded: LoadedMap,
    resolved_sidedefs: Sequence[ResolvedSideDefTextures],
    resolved_sectors: Sequence[ResolvedSectorFlats],
    *,
    frontsector_index: int,
    seg_index: int,
) -> tuple[int, int] | None:
    state.current_seg_index = seg_index

    v1 = loaded.vertices[seg.v1]
    v2 = loaded.vertices[seg.v2]
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

    x1 = stage07.angle_to_view_x(angle1)
    x2 = stage07.angle_to_view_x(angle2)
    if x1 == x2:
        state.zero_pixel_reject_count += 1
        return None

    line = loaded.linedefs[seg.linedef]
    frontsector = loaded.sectors[frontsector_index]
    backsector_index = _line_backsector_index(line, seg.side, loaded)

    if backsector_index is None:
        state.solid_classification_count += 1
        state.current_reason = SPAN_REASON_SOLID
        stage07.debug_clip_solid_wall_segment(state, x1, x2 - 1)
        return x1, x2 - 1

    backsector = loaded.sectors[backsector_index]
    if (
        backsector.ceiling_height <= frontsector.floor_height
        or backsector.floor_height >= frontsector.ceiling_height
    ):
        state.solid_classification_count += 1
        state.current_reason = SPAN_REASON_SOLID
        stage07.debug_clip_solid_wall_segment(state, x1, x2 - 1)
        return x1, x2 - 1

    if (
        backsector.ceiling_height != frontsector.ceiling_height
        or backsector.floor_height != frontsector.floor_height
    ):
        state.pass_classification_count += 1
        state.current_reason = SPAN_REASON_PASS
        stage07.debug_clip_pass_wall_segment(state, x1, x2 - 1)
        return x1, x2 - 1

    sidedef_index = _line_sidedef_index(line, seg.side)
    if (
        resolved_sectors[backsector_index].ceilingpic == resolved_sectors[frontsector_index].ceilingpic
        and resolved_sectors[backsector_index].floorpic == resolved_sectors[frontsector_index].floorpic
        and backsector.light_level == frontsector.light_level
        and resolved_sidedefs[sidedef_index].midtexture == 0
    ):
        state.empty_line_reject_count += 1
        return None

    state.pass_classification_count += 1
    state.current_reason = SPAN_REASON_PASS
    stage07.debug_clip_pass_wall_segment(state, x1, x2 - 1)
    return x1, x2 - 1


def reference_seg_clip_texture_ids_for_pinned_map(
    wad_path: str | Path,
    setup: TextureSetup,
    loaded: LoadedMap,
    resolved_sidedefs: Sequence[ResolvedSideDefTextures],
    resolved_sectors: Sequence[ResolvedSectorFlats],
) -> stage07.SegClipReference:
    baseline = stage04.reference_visibility_for_pinned_map(wad_path)
    wad = WadFile.from_file(wad_path)
    map_lumps = wad.map_lumps("MAP01")
    subsectors = stage02.parse_mapsubsectors(wad.read_lump(map_lumps.get("SSECTORS")))
    raw_segs = stage02.parse_mapsegs(wad.read_lump(map_lumps.get("SEGS")))
    nodes = tuple(
        stage03.runtime_node_from_mapnode(node)
        for node in stage02.parse_mapnodes(wad.read_lump(map_lumps.get("NODES")))
    )

    subsector_sectors: list[int] = []
    for numlines, firstline in subsectors:
        sector_index = 0
        if numlines:
            seg = raw_segs[firstline]
            line = loaded.linedefs[seg[3]]
            sidedef_index = _line_sidedef_index(line, seg[4])
            sector_index = loaded.sidedefs[sidedef_index].sector
        subsector_sectors.append(sector_index)

    segs = tuple(
        stage07.DebugSeg(v1=seg[0], v2=seg[1], linedef=seg[3], side=seg[4])
        for seg in raw_segs
    )
    state = stage07.SegClipDebugState()

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
                debug_add_line_texture_ids(
                    state,
                    segs[seg_index],
                    loaded,
                    resolved_sidedefs,
                    resolved_sectors,
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

    first_span = state.first_span or stage07.DebugSpan(0, 0, 0, -1)
    last_span = state.last_span or stage07.DebugSpan(0, 0, 0, -1)
    return stage07.SegClipReference(
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


def _sidedef_and_texture_for_projected_span(
    span: stage07.ProjectedSpan,
    raw_segs: Sequence[tuple[int, int, int, int, int, int]],
    loaded: LoadedMap,
    resolved_sidedefs: Sequence[ResolvedSideDefTextures],
) -> tuple[int, int]:
    if span.seg_index < 0 or span.seg_index >= len(raw_segs):
        return -1, -1

    raw_seg = raw_segs[span.seg_index]
    line = loaded.linedefs[raw_seg[3]]
    sidedef_index = _line_sidedef_index(line, raw_seg[4])
    if sidedef_index == 0xFFFF or sidedef_index >= len(resolved_sidedefs):
        return -1, -1

    resolved = resolved_sidedefs[sidedef_index]
    frontsector = loaded.sectors[loaded.sidedefs[sidedef_index].sector]
    backsector_index = _line_backsector_index(line, raw_seg[4], loaded)
    if backsector_index is None:
        return sidedef_index, resolved.midtexture

    backsector = loaded.sectors[backsector_index]
    if backsector.ceiling_height != frontsector.ceiling_height and resolved.toptexture != 0:
        return sidedef_index, resolved.toptexture
    if backsector.floor_height != frontsector.floor_height and resolved.bottomtexture != 0:
        return sidedef_index, resolved.bottomtexture
    return sidedef_index, resolved.midtexture


def reference_texture_data_setup_for_pinned_map(wad_path: str | Path) -> TextureDataSetupReference:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    setup = load_texture_setup_from_wad(wad)
    resolved_sidedefs = resolve_sidedef_texture_ids(loaded, setup)
    resolved_sectors = resolve_sector_flat_ids(wad, loaded, setup)
    projection = stage07.reference_wall_projection_for_pinned_map(wad_path)
    numeric_clip = reference_seg_clip_texture_ids_for_pinned_map(
        wad_path,
        setup,
        loaded,
        resolved_sidedefs,
        resolved_sectors,
    )
    map_lumps = wad.map_lumps("MAP01")
    raw_segs = stage02.parse_mapsegs(wad.read_lump(map_lumps.get("SEGS")))
    first_sidedef, first_texture = _sidedef_and_texture_for_projected_span(
        projection.first_projected_span, raw_segs, loaded, resolved_sidedefs
    )
    last_sidedef, last_texture = _sidedef_and_texture_for_projected_span(
        projection.last_projected_span, raw_segs, loaded, resolved_sidedefs
    )

    return TextureDataSetupReference(
        projection=projection,
        texture_setup=setup,
        resolved_sidedefs=tuple(resolved_sidedefs),
        resolved_sectors=tuple(resolved_sectors),
        numeric_clip=numeric_clip,
        first_projected_texture_id=first_texture,
        last_projected_texture_id=last_texture,
        first_projected_sidedef_id=first_sidedef,
        last_projected_sidedef_id=last_sidedef,
        no_midtexture_sidedef_count=sum(1 for side in resolved_sidedefs if side.midtexture == 0),
        sidedef_texture_resolution_count=len(resolved_sidedefs) * 3,
        sector_flat_resolution_count=len(resolved_sectors) * 2,
    )


def _reference_for_default_wad_or_none() -> TextureDataSetupReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_texture_data_setup_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage08_load_wad_texture_data_setup_debug")

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


def emit_source_stage08_load_wad_texture_data_setup_debug(pe: PE32) -> None:
    pe.label("source_stage08_load_wad_texture_data_setup_debug")
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
    x86.jne_rel32(pe, "source_stage08_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage08_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage08_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage08_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage08_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage08_close_and_return")

    pe.label("source_stage08_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage08_close_and_return")

    x86.call_rel32(pe, "render_init_texture_data_setup_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage08_close_and_return")

    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage08_close_and_return")

    x86.call_rel32(pe, "source_stage06_run_live_seg_clip_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage08_close_and_return")

    x86.call_rel32(pe, "build_success_status")

    pe.label("source_stage08_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_render_init_texture_data_setup_debug(pe: PE32) -> None:
    pe.label("render_init_texture_data_setup_debug")
    pe.label("render_generate_lookup_metadata_debug")
    pe.label("render_init_flats_debug")
    pe.label("render_check_texture_num_for_name_debug")
    pe.label("render_texture_num_for_name_debug")
    pe.label("render_flat_num_for_name_debug")
    pe.label("map_load_sidedefs_texture_ids_debug")
    pe.label("map_load_sectors_flat_ids_debug")
    x86.mov_mem_abs32_imm32(pe, "texture_setup_loaded", 1)
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)


def _emit_load_sector_table_value(pe: PE32, pointer_reg: str, table_label: str, out_label: str) -> None:
    x86.mov_reg_reg(pe, "eax", pointer_reg)
    x86.mov_reg_abs32(pe, "ebx", "sectors_buffer")
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "ebx", stage01.SECTOR_T_RECORD_SIZE)
    x86.div_reg(pe, "ebx")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "ebx", table_label)
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "ebx")
    x86.mov_mem_abs32_eax(pe, out_label)


def _emit_load_sidedef_midtexture(pe: PE32) -> None:
    x86.mov_reg_mem_abs32(pe, "esi", "clip_curline")
    x86.mov_reg_ptr_reg_disp8(pe, "esi", "esi", stage02.SEG_SIDEDEF)
    x86.mov_reg_reg(pe, "eax", "esi")
    x86.mov_reg_abs32(pe, "ebx", "sidedefs_buffer")
    x86.sub_reg_reg(pe, "eax", "ebx")
    x86.xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "ebx", stage01.SIDE_T_RECORD_SIZE)
    x86.div_reg(pe, "ebx")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "ebx", "stage08_side_midtexture_ids")
    x86.add_reg_reg(pe, "ebx", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "ebx")
    x86.mov_mem_abs32_eax(pe, "stage08_current_midtexture_id")


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
    stage07._emit_inc_abs32(pe, "clip_backface_reject_count")
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
    stage07._emit_inc_abs32(pe, "clip_off_frustum_reject_count")
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
    stage07._emit_inc_abs32(pe, "clip_off_frustum_reject_count")
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
    stage07._emit_inc_abs32(pe, "clip_zero_pixel_reject_count")
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

    _emit_load_sector_table_value(pe, "edi", "stage08_sector_ceilingpic_ids", "stage08_back_ceilingpic_id")
    _emit_load_sector_table_value(pe, "esi", "stage08_sector_ceilingpic_ids", "stage08_front_ceilingpic_id")
    x86.mov_reg_mem_abs32(pe, "eax", "stage08_back_ceilingpic_id")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage08_front_ceilingpic_id")
    x86.jne_rel32(pe, "add_line_clip_pass")

    _emit_load_sector_table_value(pe, "edi", "stage08_sector_floorpic_ids", "stage08_back_floorpic_id")
    _emit_load_sector_table_value(pe, "esi", "stage08_sector_floorpic_ids", "stage08_front_floorpic_id")
    x86.mov_reg_mem_abs32(pe, "eax", "stage08_back_floorpic_id")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage08_front_floorpic_id")
    x86.jne_rel32(pe, "add_line_clip_pass")

    x86.mov_reg_ptr_reg_disp8(pe, "eax", "edi", SECTOR_LIGHTLEVEL)
    x86.mov_reg_ptr_reg_disp8(pe, "ebx", "esi", SECTOR_LIGHTLEVEL)
    x86.cmp_reg_reg(pe, "eax", "ebx")
    x86.jne_rel32(pe, "add_line_clip_pass")

    _emit_load_sidedef_midtexture(pe)
    x86.mov_reg_mem_abs32(pe, "eax", "stage08_current_midtexture_id")
    x86.test_reg_reg(pe, "eax")
    x86.jne_rel32(pe, "add_line_clip_pass")
    stage07._emit_inc_abs32(pe, "clip_empty_line_reject_count")
    x86.jmp_rel32(pe, "add_line_done")

    pe.label("add_line_clip_pass")
    stage07._emit_inc_abs32(pe, "clip_pass_classification_count")
    x86.mov_mem_abs32_imm32(pe, "clip_current_span_reason", SPAN_REASON_PASS)
    x86.mov_reg_mem_abs32(pe, "eax", "clip_x2")
    x86.dec_reg(pe, "eax")
    x86.push_reg(pe, "eax")
    x86.push_mem_abs32(pe, "clip_x1")
    x86.call_rel32(pe, "render_clip_pass_wall_segment")
    x86.jmp_rel32(pe, "add_line_done")

    pe.label("add_line_clip_solid")
    stage07._emit_inc_abs32(pe, "clip_solid_classification_count")
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


def emit_build_success_status(pe: PE32) -> None:
    pe.label("build_success_status")
    x86.mov_reg_abs32(pe, "edi", "status_success_buffer")
    stage01.append_c_string_label(pe, "status_stage08_success_header")
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
    stage01.append_u32_label(pe, "status_sidedef_resolution_prefix", "stage08_sidedef_texture_resolution_count")
    stage01.append_u32_label(pe, "status_sector_resolution_prefix", "stage08_sector_flat_resolution_count")
    stage01.append_u32_label(pe, "status_empty_midzero_prefix", "clip_empty_line_reject_count")
    stage01.append_u32_label(pe, "status_first_projected_texture_prefix", "stage08_first_projected_texture_id")
    stage01.append_u32_label(pe, "status_last_projected_texture_prefix", "stage08_last_projected_texture_id")
    stage01.append_c_string_label(pe, "status_stage08_note")
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
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def _emit_u32_table(pe: PE32, label: str, values: Sequence[int]) -> None:
    pe.label(label)
    for value in values:
        pe.emit_u32(value & 0xFFFFFFFF)


def emit_stage08_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    setup = ref.texture_setup if ref is not None else None
    resolved_sidedefs = ref.resolved_sidedefs if ref is not None else ()
    resolved_sectors = ref.resolved_sectors if ref is not None else ()

    pe.align_section(4)
    pe.label("texture_setup_loaded")
    pe.emit_u32(0)
    pe.label("stage08_numtextures")
    pe.emit_u32(setup.numtextures if setup is not None else 0)
    pe.label("stage08_patch_name_count")
    pe.emit_u32(len(setup.patch_names) if setup is not None else 0)
    pe.label("stage08_texture1_count")
    pe.emit_u32(setup.texture1_count if setup is not None else 0)
    pe.label("stage08_texture2_count")
    pe.emit_u32(setup.texture2_count if setup is not None else 0)
    pe.label("stage08_texture2_present")
    pe.emit_u32(1 if setup is not None and setup.texture2_present else 0)
    pe.label("stage08_first_texture_width")
    pe.emit_u32(setup.textures[0].width if setup is not None and setup.textures else 0)
    pe.label("stage08_first_texture_height")
    pe.emit_u32(setup.textures[0].height if setup is not None and setup.textures else 0)
    pe.label("stage08_last_texture_width")
    pe.emit_u32(setup.textures[-1].width if setup is not None and setup.textures else 0)
    pe.label("stage08_last_texture_height")
    pe.emit_u32(setup.textures[-1].height if setup is not None and setup.textures else 0)
    pe.label("stage08_texpatch_count")
    pe.emit_u32(setup.texpatch_count if setup is not None else 0)
    pe.label("stage08_direct_column_count")
    pe.emit_u32(setup.direct_column_count if setup is not None else 0)
    pe.label("stage08_composite_column_count")
    pe.emit_u32(setup.composite_column_count if setup is not None else 0)
    pe.label("stage08_missing_column_count")
    pe.emit_u32(setup.missing_column_count if setup is not None else 0)
    pe.label("stage08_firstflat")
    pe.emit_u32(setup.firstflat if setup is not None else 0)
    pe.label("stage08_lastflat")
    pe.emit_u32(setup.lastflat if setup is not None else 0)
    pe.label("stage08_numflats")
    pe.emit_u32(setup.numflats if setup is not None else 0)
    pe.label("stage08_sidedef_texture_resolution_count")
    pe.emit_u32(ref.sidedef_texture_resolution_count if ref is not None else 0)
    pe.label("stage08_sector_flat_resolution_count")
    pe.emit_u32(ref.sector_flat_resolution_count if ref is not None else 0)
    pe.label("stage08_no_midtexture_sidedef_count")
    pe.emit_u32(ref.no_midtexture_sidedef_count if ref is not None else 0)
    pe.label("stage08_first_projected_texture_id")
    pe.emit_u32(ref.first_projected_texture_id if ref is not None else 0)
    pe.label("stage08_last_projected_texture_id")
    pe.emit_u32(ref.last_projected_texture_id if ref is not None else 0)
    pe.label("stage08_first_projected_sidedef_id")
    pe.emit_u32(ref.first_projected_sidedef_id if ref is not None else 0)
    pe.label("stage08_last_projected_sidedef_id")
    pe.emit_u32(ref.last_projected_sidedef_id if ref is not None else 0)

    pe.label("stage08_back_ceilingpic_id")
    pe.emit_u32(0)
    pe.label("stage08_front_ceilingpic_id")
    pe.emit_u32(0)
    pe.label("stage08_back_floorpic_id")
    pe.emit_u32(0)
    pe.label("stage08_front_floorpic_id")
    pe.emit_u32(0)
    pe.label("stage08_current_midtexture_id")
    pe.emit_u32(0)

    _emit_u32_table(
        pe,
        "stage08_side_toptexture_ids",
        [side.toptexture for side in resolved_sidedefs],
    )
    _emit_u32_table(
        pe,
        "stage08_side_bottomtexture_ids",
        [side.bottomtexture for side in resolved_sidedefs],
    )
    _emit_u32_table(
        pe,
        "stage08_side_midtexture_ids",
        [side.midtexture for side in resolved_sidedefs],
    )
    _emit_u32_table(
        pe,
        "stage08_sector_floorpic_ids",
        [sector.floorpic for sector in resolved_sectors],
    )
    _emit_u32_table(
        pe,
        "stage08_sector_ceilingpic_ids",
        [sector.ceilingpic for sector in resolved_sectors],
    )
    _emit_u32_table(
        pe,
        "stage08_texturetranslation",
        list(setup.texturetranslation) if setup is not None else [],
    )
    _emit_u32_table(
        pe,
        "stage08_flattranslation",
        list(setup.flattranslation) if setup is not None else [],
    )
    _emit_u32_table(
        pe,
        "stage08_texturewidthmask",
        [texture.texturewidthmask for texture in setup.textures] if setup is not None else [],
    )
    _emit_u32_table(
        pe,
        "stage08_textureheight",
        [texture.textureheight for texture in setup.textures] if setup is not None else [],
    )
    _emit_u32_table(
        pe,
        "stage08_texturecompositesize",
        [texture.texturecompositesize for texture in setup.textures] if setup is not None else [],
    )

    pe.align_section(1)
    pe.label("status_stage08_success_header")
    x86.emit_asciiz(pe, "source_stage08_texture_data_setup_debug\r\nTexture data setup debug OK\r\n")
    pe.label("status_texture_count_prefix")
    x86.emit_asciiz(pe, "\r\nR_InitTextures numtextures: ")
    pe.label("status_patch_name_count_prefix")
    x86.emit_asciiz(pe, "\r\nPNAMES patch names: ")
    pe.label("status_flat_count_prefix")
    x86.emit_asciiz(pe, "\r\nR_InitFlats numflats: ")
    pe.label("status_direct_column_prefix")
    x86.emit_asciiz(pe, "\r\nR_GenerateLookup direct patch columns: ")
    pe.label("status_composite_column_prefix")
    x86.emit_asciiz(pe, "\r\nR_GenerateLookup later composite columns: ")
    pe.label("status_sidedef_resolution_prefix")
    x86.emit_asciiz(pe, "\r\nP_LoadSideDefs texture IDs resolved: ")
    pe.label("status_sector_resolution_prefix")
    x86.emit_asciiz(pe, "\r\nP_LoadSectors flat IDs resolved: ")
    pe.label("status_empty_midzero_prefix")
    x86.emit_asciiz(pe, "\r\nR_AddLine empty midtexture==0 rejects: ")
    pe.label("status_first_projected_texture_prefix")
    x86.emit_asciiz(pe, "\r\nFirst projected span texture ID: ")
    pe.label("status_last_projected_texture_prefix")
    x86.emit_asciiz(pe, "\r\nLast projected span texture ID: ")
    pe.label("status_stage08_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage08 table-emits bounded source-shaped PNAMES/TEXTURE1/TEXTURE2 "
        "metadata, R_GenerateLookup column directories, flat translations, and "
        "sidedef/sector numeric IDs; no texture pixels or columns are drawn.\r\n",
    )
    pe.label("title_texture_count_prefix")
    x86.emit_asciiz(pe, " TEX=")
    pe.label("title_patch_name_count_prefix")
    x86.emit_asciiz(pe, " PN=")
    pe.label("title_flat_count_prefix")
    x86.emit_asciiz(pe, " FLAT=")
    pe.label("title_direct_column_prefix")
    x86.emit_asciiz(pe, " DIRC=")
    pe.label("title_composite_column_prefix")
    x86.emit_asciiz(pe, " COMPC=")
    pe.label("title_first_projected_texture_prefix")
    x86.emit_asciiz(pe, " FPTEX=")
    pe.label("title_last_projected_texture_prefix")
    x86.emit_asciiz(pe, " LPTEX=")
    pe.label("title_empty_midzero_prefix")
    x86.emit_asciiz(pe, " EMID=")


def build_source_stage08_texture_data_setup_debug_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage08_load_wad_texture_data_setup_debug(pe)
    emit_render_init_texture_data_setup_debug(pe)
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
    emit_render_add_line_debug(pe)
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
    emit_build_success_status(pe)
    stage01.emit_append_c_string(pe)
    stage01.emit_append_u32_decimal(pe)
    stage01.emit_append_i32_decimal(pe)
    with patched_stage01_window_labels():
        stage01.emit_data(pe)
    stage02.emit_stage02_data(pe)
    stage04.emit_stage04_data(pe)
    stage07.emit_stage07_data(pe)
    emit_stage08_data(pe)
    return pe.build("entry")


def write_source_stage08_texture_data_setup_debug_exe(path: str | Path) -> bytes:
    image = build_source_stage08_texture_data_setup_debug_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the source-guided PE32 x86 texture data setup debug executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/source_stage08_texture_data_setup_debug.exe",
        help="path to write, default: build/source_stage08_texture_data_setup_debug.exe",
    )
    args = parser.parse_args()
    write_source_stage08_texture_data_setup_debug_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
