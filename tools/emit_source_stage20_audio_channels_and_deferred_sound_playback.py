from __future__ import annotations

import argparse
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Sequence


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage19_first_door_or_switch_sector_special_probe as stage19
from tools import x86
from tools.pe32 import PE32
from tools.wad import WadFile


stage01 = stage19.stage01
stage02 = stage19.stage02
stage03 = stage19.stage03
stage04 = stage19.stage04
stage07 = stage19.stage07
stage08 = stage19.stage08
stage10 = stage19.stage10
stage11 = stage19.stage11
stage12 = stage19.stage12
stage13 = stage19.stage13
stage14 = stage19.stage14
stage15 = stage19.stage15
stage16 = stage19.stage16
stage17 = stage19.stage17
stage18 = stage19.stage18


FRAMEBUFFER_WIDTH = stage19.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage19.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage19.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage19.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage19.WINDOW_WIDTH
WINDOW_HEIGHT = stage19.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage20AudioChannelsDeferredSoundPlayback"
WINDOW_TITLE = "Inference Doom S20 Audio Channel State"
WAD_PATH = stage19.WAD_PATH

FRACBITS = stage19.FRACBITS
FRACUNIT = stage19.FRACUNIT
FNV_PRIME = stage19.FNV_PRIME
ANGLETOFINESHIFT = stage19.ANGLETOFINESHIFT
FINEMASK = stage19.FINEMASK
FINESINE = stage19.FINESINE

SOURCE_DOOM_DIR = Path(__file__).resolve().parents[1] / "reference" / "chocolate-doom" / "src" / "doom"

S_CLIPPING_DIST = 1200 * FRACUNIT
S_CLOSE_DIST = 200 * FRACUNIT
S_ATTENUATOR = (S_CLIPPING_DIST - S_CLOSE_DIST) >> FRACBITS
S_STEREO_SWING = 96 * FRACUNIT

NORM_PRIORITY = 64
NORM_SEP = 128
NORM_PITCH = 127
SFX_VOLUME_DEFAULT = 8
SND_SFX_VOLUME = SFX_VOLUME_DEFAULT * 8
SND_CHANNELS = 8

SFX_NONE = 0
SFX_PISTOL = 1
SFX_SAWUP = 10
SFX_SAWHIT = 13
SFX_ITEMUP = 32
SFX_HOOF = 84
SFX_METAL = 85
SFX_CHGUN = 86
SFX_TINK = 87
SFX_BDOPN = 88

SOUND_ORIGIN_NONE = -1
SOUND_ORIGIN_PLAYER_PROBE = -2
SOUND_ORIGIN_SECTOR_BASE = 1000

SOURCE_TRACE = stage19.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/s_sound.c",
        "S_StartSound selected sfx channel-state path",
        "S_StartSound_bdopn_channel_state_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/s_sound.c",
        "S_GetChannel bounded free/replacement/no-channel path",
        "S_GetChannel_bounded_channel_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/s_sound.c",
        "S_StopSound/S_StopChannel same-origin replacement subset",
        "S_StopSound_channel_replacement_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/s_sound.c",
        "S_AdjustSoundParams sector sound-origin attenuation subset",
        "S_AdjustSoundParams_sector_origin_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/sounds.c",
        'S_sfx metadata entry SOUND("bdopn", 100)',
        "sounds_bdopn_metadata_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_doors.c",
        "EV_VerticalDoor manual blazing door S_StartSound call site",
        "EV_VerticalDoor_bdopn_sound_boundary_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/m_random.c",
        "M_Random sound pitch variation",
        "M_Random_sound_pitch_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/i_sound.c",
        "I_GetSfxLumpNum/I_StartSound platform boundary",
        "I_StartSound_deferred_stage20_debug",
    ),
)


@dataclass
class Stage20Counters:
    sound_init_static_channels: int = 1
    sound_start_calls: int = 0
    bogus_id_rejections: int = 0
    selected_bdopn_calls: int = 0
    linked_sfx_adjustments: int = 0
    linked_volume_rejections: int = 0
    adjust_param_calls: int = 0
    same_xy_sep_overrides: int = 0
    audible_adjustments: int = 0
    clipped_adjustments: int = 0
    normal_pitch_randomizations: int = 0
    saw_pitch_randomizations: int = 0
    random_reads: int = 0
    stop_sound_calls: int = 0
    same_origin_stops: int = 0
    stop_channel_calls: int = 0
    sound_is_playing_checks: int = 0
    stop_sound_device_deferrals: int = 0
    get_channel_calls: int = 0
    free_channel_selections: int = 0
    priority_replacements: int = 0
    no_channel_rejections: int = 0
    channel_mutations: int = 0
    usefulness_increments: int = 0
    usefulness_decrements: int = 0
    lump_lookup_deferrals: int = 0
    sound_data_cache_deferrals: int = 0
    i_start_sound_deferrals: int = 0
    device_playback_deferrals: int = 0
    actual_device_playbacks: int = 0
    mixer_absent: int = 0
    music_absent: int = 0
    all_sfx_runtime_absent: int = 0
    broad_sound_cache_absent: int = 0
    source_stage21_absent: int = 1


@dataclass
class Stage20SfxInfo:
    sfx_id: int
    enum_name: str
    name: str
    priority: int
    link_id: int | None = None
    pitch: int = 0
    volume: int = 0
    usefulness: int = -1
    lumpnum: int = -1


@dataclass
class Stage20Channel:
    sfx_id: int = 0
    origin_id: int | None = None
    handle: int = 0
    pitch: int = 0
    playing: bool = False


@dataclass(frozen=True)
class Stage20SoundOrigin:
    origin_id: int
    kind: str
    x: int
    y: int
    z: int = 0
    angle: int = 0


@dataclass(frozen=True)
class Stage20AdjustResult:
    audible: bool
    volume: int
    separation: int
    approx_distance: int
    angle: int


@dataclass(frozen=True)
class Stage20SoundTraceRecord:
    call_site_line: int
    call_site_sector: int
    call_site_special: int
    sfx_id: int
    sfx_name: str
    sfx_priority: int
    origin_kind: str
    origin_id: int
    origin_x: int
    origin_y: int
    listener_x: int
    listener_y: int
    listener_angle: int
    approx_distance: int
    volume_before: int
    volume_after: int
    separation: int
    pitch_before: int
    random_value: int
    pitch_after: int
    channel_index: int
    usefulness_before: int
    usefulness_after: int
    lump_before: int
    lump_after: int
    handle: int
    audible: int


@dataclass
class Stage20SoundWorld:
    sfx: dict[int, Stage20SfxInfo]
    channels: list[Stage20Channel]
    listener: Stage20SoundOrigin
    counters: Stage20Counters
    snd_sfx_volume: int = SND_SFX_VOLUME
    snd_channels: int = SND_CHANNELS
    gamemap: int = 1
    rng: "DoomMRandom | None" = None
    last_trace: Stage20SoundTraceRecord | None = None

    def __post_init__(self) -> None:
        if self.rng is None:
            self.rng = DoomMRandom()

    @property
    def num_sfx(self) -> int:
        return max(self.sfx) + 1


@dataclass(frozen=True)
class Stage20AudioChannelsReference:
    stage19: stage19.Stage19FirstDoorSwitchSectorSpecialReference
    sound: Stage20SoundTraceRecord
    channels: tuple[Stage20Channel, ...]
    counters: Stage20Counters
    signature: int


class DoomMRandom:
    def __init__(self, index: int = 0, table: Sequence[int] | None = None) -> None:
        self.index = index
        self.table = tuple(parse_m_random_table_source_shape() if table is None else table)

    def m_random(self) -> int:
        self.index = (self.index + 1) & 0xFF
        return self.table[self.index]


def _u32(value: int) -> int:
    return value & 0xFFFFFFFF


def _i32(value: int) -> int:
    return stage04._int32(value)


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & 0xFFFFFFFF


def _hash_bytes(signature: int, data: bytes) -> int:
    for byte in data:
        signature = _hash_u32(signature, byte)
    return signature


def clamp_source_shape(value: int) -> int:
    if value < 0:
        return 0
    if value > 255:
        return 255
    return value


def _read_source_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def parse_sfx_enum_source_shape() -> tuple[str, ...]:
    text = _read_source_text(SOURCE_DOOM_DIR / "sounds.h")
    start = text.index("typedef enum", text.index("Identifiers for all sfx"))
    end = text.index("} sfxenum_t", start)
    body = text[start:end]
    names: list[str] = []
    for raw in body.splitlines():
        line = raw.split("//", 1)[0].strip().rstrip(",")
        if not line or line in {"typedef enum", "{"}:
            continue
        if line == "NUMSFX":
            break
        if line.startswith("sfx_"):
            names.append(line)
    return tuple(names)


@lru_cache(maxsize=1)
def parse_sfx_table_source_shape() -> dict[int, Stage20SfxInfo]:
    enum_names = parse_sfx_enum_source_shape()
    enum_index = {name: index for index, name in enumerate(enum_names)}
    text = _read_source_text(SOURCE_DOOM_DIR / "sounds.c")
    start = text.index("sfxinfo_t S_sfx[]")
    start = text.index("{", start)
    end = text.index("};", start)
    body = text[start:end]
    records: list[Stage20SfxInfo] = []
    for raw in body.splitlines():
        line = raw.split("//", 1)[0].strip().rstrip(",")
        if not line or line == "{":
            continue
        link = re.match(r'SOUND_LINK\("([^"]+)",\s*(\d+),\s*(sfx_[A-Za-z0-9_]+),\s*(-?\d+),\s*(-?\d+)\)', line)
        normal = re.match(r'SOUND\("([^"]+)",\s*(\d+)\)', line)
        sfx_id = len(records)
        enum_name = enum_names[sfx_id]
        if link:
            name, priority, link_name, pitch, volume = link.groups()
            records.append(
                Stage20SfxInfo(
                    sfx_id=sfx_id,
                    enum_name=enum_name,
                    name=name,
                    priority=int(priority),
                    link_id=enum_index[link_name],
                    pitch=int(pitch),
                    volume=int(volume),
                )
            )
        elif normal:
            name, priority = normal.groups()
            records.append(
                Stage20SfxInfo(
                    sfx_id=sfx_id,
                    enum_name=enum_name,
                    name=name,
                    priority=int(priority),
                )
            )
        else:
            raise ValueError(f"unparsed S_sfx line: {raw!r}")

    if len(records) != len(enum_names):
        raise ValueError(f"S_sfx table length {len(records)} does not match enum length {len(enum_names)}")
    return {record.sfx_id: record for record in records}


@lru_cache(maxsize=1)
def parse_m_random_table_source_shape() -> tuple[int, ...]:
    text = _read_source_text(SOURCE_DOOM_DIR / "m_random.c")
    start = text.index("rndtable[256]")
    start = text.index("{", start)
    end = text.index("};", start)
    values = tuple(int(value) for value in re.findall(r"\b\d+\b", text[start:end]))
    if len(values) != 256:
        raise ValueError(f"expected 256 M_Random table values, got {len(values)}")
    return values


def clone_sfx_table_source_shape() -> dict[int, Stage20SfxInfo]:
    return {sfx_id: replace(info) for sfx_id, info in parse_sfx_table_source_shape().items()}


def build_empty_stage20_sound_world(listener: Stage20SoundOrigin | None = None) -> Stage20SoundWorld:
    if listener is None:
        listener = Stage20SoundOrigin(SOUND_ORIGIN_PLAYER_PROBE, "player_probe", 0, 0, 0, 0)
    return Stage20SoundWorld(
        sfx=clone_sfx_table_source_shape(),
        channels=[Stage20Channel() for _ in range(SND_CHANNELS)],
        listener=listener,
        counters=Stage20Counters(),
    )


def sector_sound_origin_stage20_source_shape(
    world: stage19.Stage19World,
    sector_index: int,
) -> Stage20SoundOrigin:
    left = bottom = 0x7FFFFFFF
    right = top = -0x80000000
    for line_index in world.sector_lines.get(sector_index, []):
        line = world.lines[line_index]
        for x, y in ((line.v1x, line.v1y), (line.v2x, line.v2y)):
            left = min(left, x)
            right = max(right, x)
            bottom = min(bottom, y)
            top = max(top, y)
    if left == 0x7FFFFFFF:
        raise ValueError(f"sector {sector_index} has no lines for sound origin")
    return Stage20SoundOrigin(
        origin_id=SOUND_ORIGIN_SECTOR_BASE + sector_index,
        kind="sector_soundorg",
        x=_i32((right + left) // 2),
        y=_i32((top + bottom) // 2),
        z=0,
        angle=0,
    )


def s_adjust_sound_params_stage20_source_shape(
    listener: Stage20SoundOrigin,
    source: Stage20SoundOrigin,
    volume: int,
    separation: int,
    counters: Stage20Counters | None = None,
    *,
    gamemap: int = 1,
) -> Stage20AdjustResult:
    if counters is not None:
        counters.adjust_param_calls += 1
    adx = abs(_i32(listener.x - source.x))
    ady = abs(_i32(listener.y - source.y))
    approx_dist = _i32(adx + ady - (min(adx, ady) >> 1))

    if gamemap != 8 and approx_dist > S_CLIPPING_DIST:
        if counters is not None:
            counters.clipped_adjustments += 1
        return Stage20AdjustResult(False, volume, separation, approx_dist, 0)

    angle = stage04.point_to_angle(source.x, source.y, listener.x, listener.y)
    if angle > listener.angle:
        angle = _u32(angle - listener.angle)
    else:
        angle = _u32(angle + (0xFFFFFFFF - listener.angle))
    fine = (angle >> ANGLETOFINESHIFT) & FINEMASK
    separation = 128 - (stage04.fixed_mul(S_STEREO_SWING, FINESINE[fine]) >> FRACBITS)

    if approx_dist < S_CLOSE_DIST:
        volume = SND_SFX_VOLUME
    elif gamemap == 8:
        clipped = min(approx_dist, S_CLIPPING_DIST)
        volume = 15 + ((SND_SFX_VOLUME - 15) * ((S_CLIPPING_DIST - clipped) >> FRACBITS)) // S_ATTENUATOR
    else:
        volume = (SND_SFX_VOLUME * ((S_CLIPPING_DIST - approx_dist) >> FRACBITS)) // S_ATTENUATOR

    audible = volume > 0
    if counters is not None:
        if audible:
            counters.audible_adjustments += 1
        else:
            counters.clipped_adjustments += 1
    return Stage20AdjustResult(audible, volume, separation, approx_dist, angle)


def s_stop_channel_stage20_source_shape(world: Stage20SoundWorld, channel_index: int) -> None:
    channel = world.channels[channel_index]
    if not channel.sfx_id:
        return
    world.counters.stop_channel_calls += 1
    world.counters.sound_is_playing_checks += 1
    if channel.playing:
        world.counters.stop_sound_device_deferrals += 1
    sfx = world.sfx[channel.sfx_id]
    sfx.usefulness -= 1
    world.counters.usefulness_decrements += 1
    channel.sfx_id = 0
    channel.origin_id = None
    channel.handle = 0
    channel.pitch = 0
    channel.playing = False


def s_stop_sound_stage20_source_shape(world: Stage20SoundWorld, origin: Stage20SoundOrigin | None) -> None:
    world.counters.stop_sound_calls += 1
    origin_id = None if origin is None else origin.origin_id
    for cnum, channel in enumerate(world.channels):
        if channel.sfx_id and channel.origin_id == origin_id:
            world.counters.same_origin_stops += 1
            s_stop_channel_stage20_source_shape(world, cnum)
            break


def s_get_channel_stage20_source_shape(
    world: Stage20SoundWorld,
    origin: Stage20SoundOrigin | None,
    sfx: Stage20SfxInfo,
) -> int:
    world.counters.get_channel_calls += 1
    origin_id = None if origin is None else origin.origin_id
    cnum = 0
    while cnum < world.snd_channels:
        channel = world.channels[cnum]
        if not channel.sfx_id:
            world.counters.free_channel_selections += 1
            break
        if origin is not None and channel.origin_id == origin_id:
            world.counters.same_origin_stops += 1
            s_stop_channel_stage20_source_shape(world, cnum)
            break
        cnum += 1

    if cnum == world.snd_channels:
        cnum = 0
        while cnum < world.snd_channels:
            channel_sfx = world.sfx[world.channels[cnum].sfx_id]
            if channel_sfx.priority >= sfx.priority:
                break
            cnum += 1
        if cnum == world.snd_channels:
            world.counters.no_channel_rejections += 1
            return -1
        world.counters.priority_replacements += 1
        s_stop_channel_stage20_source_shape(world, cnum)

    channel = world.channels[cnum]
    channel.sfx_id = sfx.sfx_id
    channel.origin_id = origin_id
    world.counters.channel_mutations += 1
    return cnum


def s_start_sound_stage20_source_shape(
    world: Stage20SoundWorld,
    origin: Stage20SoundOrigin | None,
    sfx_id: int,
    *,
    call_site_line: int = 0,
    call_site_sector: int = 0,
    call_site_special: int = 0,
) -> Stage20SoundTraceRecord | None:
    world.counters.sound_start_calls += 1
    volume = world.snd_sfx_volume

    if sfx_id < 1 or sfx_id >= world.num_sfx or sfx_id not in world.sfx:
        world.counters.bogus_id_rejections += 1
        return None

    sfx = world.sfx[sfx_id]
    if sfx_id == SFX_BDOPN:
        world.counters.selected_bdopn_calls += 1

    pitch_before = NORM_PITCH
    pitch = NORM_PITCH
    if sfx.link_id is not None:
        world.counters.linked_sfx_adjustments += 1
        volume += sfx.volume
        pitch = sfx.pitch
        pitch_before = pitch
        if volume < 1:
            world.counters.linked_volume_rejections += 1
            return None
        if volume > world.snd_sfx_volume:
            volume = world.snd_sfx_volume

    separation = NORM_SEP
    approx_dist = 0
    audible = 1
    if origin is not None and origin.origin_id != world.listener.origin_id:
        adjusted = s_adjust_sound_params_stage20_source_shape(
            world.listener,
            origin,
            volume,
            separation,
            world.counters,
            gamemap=world.gamemap,
        )
        volume = adjusted.volume
        separation = adjusted.separation
        approx_dist = adjusted.approx_distance
        audible = 1 if adjusted.audible else 0
        if origin.x == world.listener.x and origin.y == world.listener.y:
            separation = NORM_SEP
            world.counters.same_xy_sep_overrides += 1
        if not adjusted.audible:
            return None
    else:
        separation = NORM_SEP

    random_value = -1
    assert world.rng is not None
    if SFX_SAWUP <= sfx_id <= SFX_SAWHIT:
        random_value = world.rng.m_random()
        world.counters.random_reads += 1
        world.counters.saw_pitch_randomizations += 1
        pitch += 8 - (random_value & 15)
    elif sfx_id not in {SFX_ITEMUP, SFX_TINK}:
        random_value = world.rng.m_random()
        world.counters.random_reads += 1
        world.counters.normal_pitch_randomizations += 1
        pitch += 16 - (random_value & 31)
    pitch = clamp_source_shape(pitch)

    s_stop_sound_stage20_source_shape(world, origin)
    cnum = s_get_channel_stage20_source_shape(world, origin, sfx)
    if cnum < 0:
        return None

    usefulness_before = sfx.usefulness
    old_usefulness = sfx.usefulness
    sfx.usefulness += 1
    if old_usefulness < 0:
        sfx.usefulness = 1
    world.counters.usefulness_increments += 1
    usefulness_after = sfx.usefulness

    lump_before = sfx.lumpnum
    if sfx.lumpnum < 0:
        world.counters.lump_lookup_deferrals += 1
        sfx.lumpnum = 0
    lump_after = sfx.lumpnum

    channel = world.channels[cnum]
    channel.pitch = pitch
    channel.handle = 0
    channel.playing = False
    world.counters.sound_data_cache_deferrals += 1
    world.counters.i_start_sound_deferrals += 1
    world.counters.device_playback_deferrals += 1

    listener = world.listener
    if origin is None:
        origin_record = Stage20SoundOrigin(SOUND_ORIGIN_NONE, "null", listener.x, listener.y)
    else:
        origin_record = origin

    trace = Stage20SoundTraceRecord(
        call_site_line=call_site_line,
        call_site_sector=call_site_sector,
        call_site_special=call_site_special,
        sfx_id=sfx.sfx_id,
        sfx_name=sfx.name,
        sfx_priority=sfx.priority,
        origin_kind=origin_record.kind,
        origin_id=origin_record.origin_id,
        origin_x=origin_record.x,
        origin_y=origin_record.y,
        listener_x=listener.x,
        listener_y=listener.y,
        listener_angle=listener.angle,
        approx_distance=approx_dist,
        volume_before=world.snd_sfx_volume,
        volume_after=volume,
        separation=separation,
        pitch_before=pitch_before,
        random_value=random_value,
        pitch_after=pitch,
        channel_index=cnum,
        usefulness_before=usefulness_before,
        usefulness_after=usefulness_after,
        lump_before=lump_before,
        lump_after=lump_after,
        handle=channel.handle,
        audible=audible,
    )
    world.last_trace = trace
    return trace


def _stage20_signature(
    ref19: stage19.Stage19FirstDoorSwitchSectorSpecialReference,
    sound: Stage20SoundTraceRecord,
    counters: Stage20Counters,
    channels: Sequence[Stage20Channel],
) -> int:
    signature = ref19.signature
    for value in (
        sound.call_site_line,
        sound.call_site_sector,
        sound.call_site_special,
        sound.sfx_id,
        sound.sfx_priority,
        sound.origin_id,
        sound.origin_x,
        sound.origin_y,
        sound.listener_x,
        sound.listener_y,
        sound.listener_angle,
        sound.approx_distance,
        sound.volume_before,
        sound.volume_after,
        sound.separation,
        sound.pitch_before,
        sound.random_value,
        sound.pitch_after,
        sound.channel_index,
        sound.usefulness_before,
        sound.usefulness_after,
        sound.lump_before,
        sound.lump_after,
        sound.handle,
        sound.audible,
    ):
        signature = _hash_u32(signature, value)
    for value in (
        counters.sound_init_static_channels,
        counters.sound_start_calls,
        counters.selected_bdopn_calls,
        counters.adjust_param_calls,
        counters.audible_adjustments,
        counters.normal_pitch_randomizations,
        counters.random_reads,
        counters.stop_sound_calls,
        counters.same_origin_stops,
        counters.get_channel_calls,
        counters.free_channel_selections,
        counters.priority_replacements,
        counters.no_channel_rejections,
        counters.channel_mutations,
        counters.usefulness_increments,
        counters.lump_lookup_deferrals,
        counters.sound_data_cache_deferrals,
        counters.i_start_sound_deferrals,
        counters.device_playback_deferrals,
        counters.actual_device_playbacks,
        counters.mixer_absent,
        counters.music_absent,
        counters.all_sfx_runtime_absent,
        counters.broad_sound_cache_absent,
    ):
        signature = _hash_u32(signature, value)
    for channel in channels:
        for value in (
            channel.sfx_id,
            channel.origin_id if channel.origin_id is not None else -1,
            channel.handle,
            channel.pitch,
            1 if channel.playing else 0,
        ):
            signature = _hash_u32(signature, value)
    signature = _hash_bytes(signature, sound.sfx_name.encode("ascii"))
    signature = _hash_bytes(signature, sound.origin_kind.encode("ascii"))
    return signature


def _reference_stage20_uncached(wad_path: str) -> Stage20AudioChannelsReference:
    wad = WadFile.from_file(wad_path)
    loaded = stage19.load_map_from_file(wad_path, "MAP01")
    ref19 = stage19.reference_first_door_or_switch_sector_special_probe_for_pinned_map(wad_path)
    stage19_world = stage19.build_stage19_world(wad, loaded)
    listener = Stage20SoundOrigin(
        origin_id=SOUND_ORIGIN_PLAYER_PROBE,
        kind="player_probe",
        x=ref19.census.probe_x,
        y=ref19.census.probe_y,
        z=0,
        angle=stage19.SELECTED_PROBE_ANGLE,
    )
    origin = sector_sound_origin_stage20_source_shape(stage19_world, ref19.census.target_sector)
    sound_world = build_empty_stage20_sound_world(listener)
    sound = s_start_sound_stage20_source_shape(
        sound_world,
        origin,
        SFX_BDOPN,
        call_site_line=ref19.census.line_index,
        call_site_sector=ref19.census.target_sector,
        call_site_special=ref19.census.special,
    )
    if sound is None:
        raise AssertionError("stage20 selected S_StartSound did not allocate a channel")
    signature = _stage20_signature(ref19, sound, sound_world.counters, sound_world.channels)
    return Stage20AudioChannelsReference(
        stage19=ref19,
        sound=sound,
        channels=tuple(replace(channel) for channel in sound_world.channels),
        counters=replace(sound_world.counters),
        signature=signature,
    )


@lru_cache(maxsize=4)
def _reference_stage20_cached(wad_path: str) -> Stage20AudioChannelsReference:
    return _reference_stage20_uncached(wad_path)


def reference_audio_channels_and_deferred_sound_playback_for_pinned_map(
    wad_path: str | Path,
) -> Stage20AudioChannelsReference:
    return _reference_stage20_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage20AudioChannelsReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_audio_channels_and_deferred_sound_playback_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage20_load_wad_audio_channels_deferred_sound_playback")

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
    x86.cmp_eax_imm32(pe, 0)
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


def emit_source_stage20_load_wad_audio_channels_deferred_sound_playback(pe: PE32) -> None:
    pe.label("source_stage20_load_wad_audio_channels_deferred_sound_playback")
    x86.call_rel32(pe, "source_stage19_load_wad_first_door_switch_sector_special_probe")
    x86.mov_reg_mem_abs32(pe, "eax", "stage19_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage19_expected_signature")
    x86.jne_rel32(pe, "source_stage20_return")
    x86.call_rel32(pe, "render_audio_channels_deferred_sound_playback_debug")
    x86.call_rel32(pe, "append_stage20_success_status")
    pe.label("source_stage20_return")
    x86.ret(pe)


def emit_render_audio_channels_deferred_sound_playback_debug(pe: PE32) -> None:
    pe.label("S_StartSound_bdopn_channel_state_source_shape_debug")
    pe.label("S_GetChannel_bounded_channel_source_shape_debug")
    pe.label("S_StopSound_channel_replacement_source_shape_debug")
    pe.label("S_AdjustSoundParams_sector_origin_source_shape_debug")
    pe.label("sounds_bdopn_metadata_source_shape_debug")
    pe.label("EV_VerticalDoor_bdopn_sound_boundary_source_shape_debug")
    pe.label("M_Random_sound_pitch_source_shape_debug")
    pe.label("I_StartSound_deferred_stage20_debug")
    pe.label("render_audio_channels_deferred_sound_playback_debug")

    for dst, src in (
        ("stage20_runtime_signature", "stage20_expected_signature"),
        ("stage20_runtime_channel_index", "stage20_channel_index"),
        ("stage20_runtime_channel0_sfx", "stage20_channel0_sfx"),
        ("stage20_runtime_channel0_origin", "stage20_channel0_origin"),
        ("stage20_runtime_channel0_handle", "stage20_channel0_handle"),
        ("stage20_runtime_channel0_pitch", "stage20_channel0_pitch"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage14._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage20_success_status(pe: PE32) -> None:
    pe.label("append_stage20_success_status")

    _emit_seek_buffer_end(pe, "status_success_buffer", "stage20_status")
    stage01.append_c_string_label(pe, "status_stage20_success_header")
    stage01.append_u32_label(pe, "status_stage20_sound_prefix", "stage20_sfx_id")
    stage01.append_c_string_label(pe, "status_stage20_name_prefix")
    stage01.append_c_string_label(pe, "stage20_sfx_name")
    stage01.append_u32_label(pe, "status_stage20_channel_prefix", "stage20_runtime_channel_index")
    stage01.append_u32_label(pe, "status_stage20_signature_prefix", "stage20_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage20_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage20_title")
    stage01.append_u32_label(pe, "title_stage20_call_prefix", "stage20_sound_start_calls")
    stage01.append_u32_label(pe, "title_stage20_line_prefix", "stage20_call_site_line")
    stage01.append_u32_label(pe, "title_stage20_sector_prefix", "stage20_call_site_sector")
    stage01.append_u32_label(pe, "title_stage20_sound_id_prefix", "stage20_sfx_id")
    stage01.append_c_string_label(pe, "title_stage20_sound_name_prefix")
    stage01.append_c_string_label(pe, "stage20_sfx_name")
    stage01.append_u32_label(pe, "title_stage20_priority_prefix", "stage20_sfx_priority")
    stage01.append_u32_label(pe, "title_stage20_channels_prefix", "stage20_snd_channels")
    stage01.append_u32_label(pe, "title_stage20_channel_prefix", "stage20_runtime_channel_index")
    stage01.append_u32_label(pe, "title_stage20_origin_sector_prefix", "stage20_origin_sector")
    stage01.append_i32_label(pe, "title_stage20_origin_x_prefix", "stage20_origin_x")
    stage01.append_i32_label(pe, "title_stage20_origin_y_prefix", "stage20_origin_y")
    stage01.append_i32_label(pe, "title_stage20_listener_x_prefix", "stage20_listener_x")
    stage01.append_i32_label(pe, "title_stage20_listener_y_prefix", "stage20_listener_y")
    stage01.append_u32_label(pe, "title_stage20_distance_prefix", "stage20_approx_distance_units")
    stage01.append_u32_label(pe, "title_stage20_volume_prefix", "stage20_volume_after")
    stage01.append_u32_label(pe, "title_stage20_sep_prefix", "stage20_separation")
    stage01.append_u32_label(pe, "title_stage20_pitch_before_prefix", "stage20_pitch_before")
    stage01.append_i32_label(pe, "title_stage20_random_prefix", "stage20_random_value")
    stage01.append_u32_label(pe, "title_stage20_pitch_after_prefix", "stage20_pitch_after")
    stage01.append_u32_label(pe, "title_stage20_stop_prefix", "stage20_stop_sound_calls")
    stage01.append_u32_label(pe, "title_stage20_same_prefix", "stage20_same_origin_stops")
    stage01.append_u32_label(pe, "title_stage20_get_prefix", "stage20_get_channel_calls")
    stage01.append_u32_label(pe, "title_stage20_free_prefix", "stage20_free_channel_selections")
    stage01.append_u32_label(pe, "title_stage20_replace_prefix", "stage20_priority_replacements")
    stage01.append_u32_label(pe, "title_stage20_nochan_prefix", "stage20_no_channel_rejections")
    stage01.append_i32_label(pe, "title_stage20_use_before_prefix", "stage20_usefulness_before")
    stage01.append_i32_label(pe, "title_stage20_use_after_prefix", "stage20_usefulness_after")
    stage01.append_u32_label(pe, "title_stage20_lump_def_prefix", "stage20_lump_lookup_deferrals")
    stage01.append_u32_label(pe, "title_stage20_lump_prefix", "stage20_lump_after")
    stage01.append_u32_label(pe, "title_stage20_istart_prefix", "stage20_i_start_sound_deferrals")
    stage01.append_u32_label(pe, "title_stage20_handle_prefix", "stage20_channel0_handle")
    stage01.append_u32_label(pe, "title_stage20_play_prefix", "stage20_actual_device_playbacks")
    stage01.append_u32_label(pe, "title_stage20_aud_prefix", "stage20_device_playback_deferrals")
    stage01.append_u32_label(pe, "title_stage20_mix_prefix", "stage20_mixer_absent")
    stage01.append_u32_label(pe, "title_stage20_mus_prefix", "stage20_music_absent")
    stage01.append_u32_label(pe, "title_stage20_all_prefix", "stage20_all_sfx_runtime_absent")
    stage01.append_u32_label(pe, "title_stage20_cache_prefix", "stage20_broad_sound_cache_absent")
    stage01.append_u32_label(pe, "title_stage20_signature_prefix", "stage20_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage20_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sound = ref.sound if ref is not None else None
    counters = ref.counters if ref is not None else Stage20Counters()
    channels = ref.channels if ref is not None else tuple(Stage20Channel() for _ in range(SND_CHANNELS))
    channel0 = channels[0] if channels else Stage20Channel()

    pe.align_section(4)
    pe.label("stage20_call_site_line")
    pe.emit_u32(sound.call_site_line if sound is not None else 0)
    pe.label("stage20_call_site_sector")
    pe.emit_u32(sound.call_site_sector if sound is not None else 0)
    pe.label("stage20_call_site_special")
    pe.emit_u32(sound.call_site_special if sound is not None else 0)
    pe.label("stage20_sfx_id")
    pe.emit_u32(sound.sfx_id if sound is not None else 0)
    pe.label("stage20_sfx_priority")
    pe.emit_u32(sound.sfx_priority if sound is not None else 0)
    pe.label("stage20_snd_channels")
    pe.emit_u32(SND_CHANNELS)
    pe.label("stage20_channel_index")
    pe.emit_u32(sound.channel_index if sound is not None else 0)
    pe.label("stage20_runtime_channel_index")
    pe.emit_u32(0)
    pe.label("stage20_origin_sector")
    pe.emit_u32(sound.call_site_sector if sound is not None else 0)
    pe.label("stage20_origin_id")
    pe.emit_u32(sound.origin_id if sound is not None else 0)
    pe.label("stage20_origin_x")
    pe.emit_u32(((sound.origin_x >> FRACBITS) if sound is not None else 0) & 0xFFFFFFFF)
    pe.label("stage20_origin_y")
    pe.emit_u32(((sound.origin_y >> FRACBITS) if sound is not None else 0) & 0xFFFFFFFF)
    pe.label("stage20_origin_x_fixed")
    pe.emit_u32(sound.origin_x if sound is not None else 0)
    pe.label("stage20_origin_y_fixed")
    pe.emit_u32(sound.origin_y if sound is not None else 0)
    pe.label("stage20_listener_x")
    pe.emit_u32(((sound.listener_x >> FRACBITS) if sound is not None else 0) & 0xFFFFFFFF)
    pe.label("stage20_listener_y")
    pe.emit_u32(((sound.listener_y >> FRACBITS) if sound is not None else 0) & 0xFFFFFFFF)
    pe.label("stage20_listener_angle")
    pe.emit_u32(sound.listener_angle if sound is not None else 0)
    pe.label("stage20_approx_distance")
    pe.emit_u32(sound.approx_distance if sound is not None else 0)
    pe.label("stage20_approx_distance_units")
    pe.emit_u32((sound.approx_distance >> FRACBITS) if sound is not None else 0)
    pe.label("stage20_volume_before")
    pe.emit_u32(sound.volume_before if sound is not None else 0)
    pe.label("stage20_volume_after")
    pe.emit_u32(sound.volume_after if sound is not None else 0)
    pe.label("stage20_separation")
    pe.emit_u32(sound.separation if sound is not None else 0)
    pe.label("stage20_pitch_before")
    pe.emit_u32(sound.pitch_before if sound is not None else 0)
    pe.label("stage20_random_value")
    pe.emit_u32((sound.random_value if sound is not None else 0) & 0xFFFFFFFF)
    pe.label("stage20_pitch_after")
    pe.emit_u32(sound.pitch_after if sound is not None else 0)
    pe.label("stage20_usefulness_before")
    pe.emit_u32((sound.usefulness_before if sound is not None else 0) & 0xFFFFFFFF)
    pe.label("stage20_usefulness_after")
    pe.emit_u32((sound.usefulness_after if sound is not None else 0) & 0xFFFFFFFF)
    pe.label("stage20_lump_before")
    pe.emit_u32((sound.lump_before if sound is not None else 0) & 0xFFFFFFFF)
    pe.label("stage20_lump_after")
    pe.emit_u32(sound.lump_after if sound is not None else 0)
    pe.label("stage20_handle")
    pe.emit_u32(sound.handle if sound is not None else 0)
    pe.label("stage20_audible")
    pe.emit_u32(sound.audible if sound is not None else 0)

    for name, value in (
        ("stage20_sound_init_static_channels", counters.sound_init_static_channels),
        ("stage20_sound_start_calls", counters.sound_start_calls),
        ("stage20_bogus_id_rejections", counters.bogus_id_rejections),
        ("stage20_selected_bdopn_calls", counters.selected_bdopn_calls),
        ("stage20_linked_sfx_adjustments", counters.linked_sfx_adjustments),
        ("stage20_linked_volume_rejections", counters.linked_volume_rejections),
        ("stage20_adjust_param_calls", counters.adjust_param_calls),
        ("stage20_same_xy_sep_overrides", counters.same_xy_sep_overrides),
        ("stage20_audible_adjustments", counters.audible_adjustments),
        ("stage20_clipped_adjustments", counters.clipped_adjustments),
        ("stage20_normal_pitch_randomizations", counters.normal_pitch_randomizations),
        ("stage20_saw_pitch_randomizations", counters.saw_pitch_randomizations),
        ("stage20_random_reads", counters.random_reads),
        ("stage20_stop_sound_calls", counters.stop_sound_calls),
        ("stage20_same_origin_stops", counters.same_origin_stops),
        ("stage20_stop_channel_calls", counters.stop_channel_calls),
        ("stage20_sound_is_playing_checks", counters.sound_is_playing_checks),
        ("stage20_stop_sound_device_deferrals", counters.stop_sound_device_deferrals),
        ("stage20_get_channel_calls", counters.get_channel_calls),
        ("stage20_free_channel_selections", counters.free_channel_selections),
        ("stage20_priority_replacements", counters.priority_replacements),
        ("stage20_no_channel_rejections", counters.no_channel_rejections),
        ("stage20_channel_mutations", counters.channel_mutations),
        ("stage20_usefulness_increments", counters.usefulness_increments),
        ("stage20_usefulness_decrements", counters.usefulness_decrements),
        ("stage20_lump_lookup_deferrals", counters.lump_lookup_deferrals),
        ("stage20_sound_data_cache_deferrals", counters.sound_data_cache_deferrals),
        ("stage20_i_start_sound_deferrals", counters.i_start_sound_deferrals),
        ("stage20_device_playback_deferrals", counters.device_playback_deferrals),
        ("stage20_actual_device_playbacks", counters.actual_device_playbacks),
        ("stage20_mixer_absent", counters.mixer_absent),
        ("stage20_music_absent", counters.music_absent),
        ("stage20_all_sfx_runtime_absent", counters.all_sfx_runtime_absent),
        ("stage20_broad_sound_cache_absent", counters.broad_sound_cache_absent),
        ("stage20_source_stage21_absent", counters.source_stage21_absent),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)

    pe.label("stage20_channel0_sfx")
    pe.emit_u32(channel0.sfx_id)
    pe.label("stage20_channel0_origin")
    pe.emit_u32((channel0.origin_id if channel0.origin_id is not None else 0) & 0xFFFFFFFF)
    pe.label("stage20_channel0_handle")
    pe.emit_u32(channel0.handle)
    pe.label("stage20_channel0_pitch")
    pe.emit_u32(channel0.pitch)
    pe.label("stage20_runtime_channel0_sfx")
    pe.emit_u32(0)
    pe.label("stage20_runtime_channel0_origin")
    pe.emit_u32(0)
    pe.label("stage20_runtime_channel0_handle")
    pe.emit_u32(0)
    pe.label("stage20_runtime_channel0_pitch")
    pe.emit_u32(0)

    pe.label("stage20_channel_table")
    for channel in channels:
        pe.emit_u32(channel.sfx_id)
        pe.emit_u32((channel.origin_id if channel.origin_id is not None else 0) & 0xFFFFFFFF)
        pe.emit_u32(channel.handle)
        pe.emit_u32(channel.pitch)

    pe.label("stage20_expected_signature")
    pe.emit_u32(ref.signature if ref is not None else 0)
    pe.label("stage20_runtime_signature")
    pe.emit_u32(0)

    pe.align_section(1)
    pe.label("stage20_sfx_name")
    x86.emit_asciiz(pe, sound.sfx_name if sound is not None else "")
    pe.label("stage20_origin_kind")
    x86.emit_asciiz(pe, sound.origin_kind if sound is not None else "")

    pe.label("status_stage20_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage20_audio_channels_and_deferred_sound_playback\r\n"
        "Sound channel state proof OK\r\n",
    )
    pe.label("status_stage20_sound_prefix")
    x86.emit_asciiz(pe, "\r\nSelected sound id: ")
    pe.label("status_stage20_name_prefix")
    x86.emit_asciiz(pe, "\r\nSelected sound name: ")
    pe.label("status_stage20_channel_prefix")
    x86.emit_asciiz(pe, "\r\nSelected channel index: ")
    pe.label("status_stage20_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage20 sound-channel signature: ")
    pe.label("status_stage20_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage20 preserves the released stage19 manual door mutation, then "
        "turns the reached EV_VerticalDoor S_StartSound boundary for sfx_bdopn "
        "into one bounded channel record. The source-shaped path resolves "
        "S_sfx metadata, applies S_AdjustSoundParams volume/separation, "
        "pitch variation, S_StopSound, S_GetChannel, usefulness, and lump bookkeeping. "
        "The platform start call is counted as a boundary; no speaker output "
        "is produced.\r\n",
    )

    pe.label("title_stage20_call_prefix")
    x86.emit_asciiz(pe, " S20CALL=")
    pe.label("title_stage20_line_prefix")
    x86.emit_asciiz(pe, " S20LINE=")
    pe.label("title_stage20_sector_prefix")
    x86.emit_asciiz(pe, " S20SEC=")
    pe.label("title_stage20_sound_id_prefix")
    x86.emit_asciiz(pe, " S20ID=")
    pe.label("title_stage20_sound_name_prefix")
    x86.emit_asciiz(pe, " S20N=")
    pe.label("title_stage20_priority_prefix")
    x86.emit_asciiz(pe, " S20PRI=")
    pe.label("title_stage20_channels_prefix")
    x86.emit_asciiz(pe, " CHS20=")
    pe.label("title_stage20_channel_prefix")
    x86.emit_asciiz(pe, " CH20=")
    pe.label("title_stage20_origin_sector_prefix")
    x86.emit_asciiz(pe, " ORG20=")
    pe.label("title_stage20_origin_x_prefix")
    x86.emit_asciiz(pe, " O20X=")
    pe.label("title_stage20_origin_y_prefix")
    x86.emit_asciiz(pe, " O20Y=")
    pe.label("title_stage20_listener_x_prefix")
    x86.emit_asciiz(pe, " L20X=")
    pe.label("title_stage20_listener_y_prefix")
    x86.emit_asciiz(pe, " L20Y=")
    pe.label("title_stage20_distance_prefix")
    x86.emit_asciiz(pe, " DIST20=")
    pe.label("title_stage20_volume_prefix")
    x86.emit_asciiz(pe, " VOL20=")
    pe.label("title_stage20_sep_prefix")
    x86.emit_asciiz(pe, " SEP20=")
    pe.label("title_stage20_pitch_before_prefix")
    x86.emit_asciiz(pe, " P200=")
    pe.label("title_stage20_random_prefix")
    x86.emit_asciiz(pe, " RND20=")
    pe.label("title_stage20_pitch_after_prefix")
    x86.emit_asciiz(pe, " P201=")
    pe.label("title_stage20_stop_prefix")
    x86.emit_asciiz(pe, " STOP20=")
    pe.label("title_stage20_same_prefix")
    x86.emit_asciiz(pe, " SAME20=")
    pe.label("title_stage20_get_prefix")
    x86.emit_asciiz(pe, " GET20=")
    pe.label("title_stage20_free_prefix")
    x86.emit_asciiz(pe, " FREE20=")
    pe.label("title_stage20_replace_prefix")
    x86.emit_asciiz(pe, " REP20=")
    pe.label("title_stage20_nochan_prefix")
    x86.emit_asciiz(pe, " NOCH20=")
    pe.label("title_stage20_use_before_prefix")
    x86.emit_asciiz(pe, " USE200=")
    pe.label("title_stage20_use_after_prefix")
    x86.emit_asciiz(pe, " USE201=")
    pe.label("title_stage20_lump_def_prefix")
    x86.emit_asciiz(pe, " LDEF20=")
    pe.label("title_stage20_lump_prefix")
    x86.emit_asciiz(pe, " LUMP20=")
    pe.label("title_stage20_istart_prefix")
    x86.emit_asciiz(pe, " IST20=")
    pe.label("title_stage20_handle_prefix")
    x86.emit_asciiz(pe, " H20=")
    pe.label("title_stage20_play_prefix")
    x86.emit_asciiz(pe, " PLAY20=")
    pe.label("title_stage20_aud_prefix")
    x86.emit_asciiz(pe, " AUD20=")
    pe.label("title_stage20_mix_prefix")
    x86.emit_asciiz(pe, " MIX20=")
    pe.label("title_stage20_mus_prefix")
    x86.emit_asciiz(pe, " MUS20=")
    pe.label("title_stage20_all_prefix")
    x86.emit_asciiz(pe, " ALLS20=")
    pe.label("title_stage20_cache_prefix")
    x86.emit_asciiz(pe, " CACH20=")
    pe.label("title_stage20_signature_prefix")
    x86.emit_asciiz(pe, " S20SIG=")


def build_source_stage20_audio_channels_and_deferred_sound_playback_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage20_load_wad_audio_channels_deferred_sound_playback(pe)
    stage19.emit_source_stage19_load_wad_first_door_switch_sector_special_probe(pe)
    stage18.emit_source_stage18_load_wad_post_damage_monster_movement_chase_probe(pe)
    stage17.emit_source_stage17_load_wad_first_weapon_fire_damage_death_probe(pe)
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
    stage12.emit_render_sky_and_masked_midtextures_debug(pe)
    stage12.emit_render_draw_stage12_columns_debug(pe)
    stage13.emit_render_things_sprites_and_real_frame_setup_debug(pe)
    stage13.emit_render_draw_stage13_sprite_column_debug(pe)
    stage14.emit_render_game_loop_input_collision_debug(pe)
    stage15.emit_render_pickups_psprites_statusbar_shell_debug(pe)
    stage15.emit_render_draw_stage15_columns_debug(pe)
    stage16.emit_render_active_monster_thinkers_targeting_debug(pe)
    stage17.emit_render_first_weapon_fire_damage_death_probe_debug(pe)
    stage18.emit_render_post_damage_monster_movement_chase_probe_debug(pe)
    stage19.emit_render_first_door_switch_sector_special_probe_debug(pe)
    emit_render_audio_channels_deferred_sound_playback_debug(pe)
    stage12.emit_build_success_status(pe)
    stage13.emit_append_stage13_success_status(pe)
    stage14.emit_append_stage14_success_status(pe)
    stage15.emit_append_stage15_success_status(pe)
    stage16.emit_append_stage16_success_status(pe)
    stage17.emit_append_stage17_success_status(pe)
    stage18.emit_append_stage18_success_status(pe)
    stage19.emit_append_stage19_success_status(pe)
    emit_append_stage20_success_status(pe)
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
    stage12.emit_stage12_data(pe)
    stage13.emit_stage13_data(pe)
    stage14.emit_stage14_data(pe)
    stage15.emit_stage15_data(pe)
    stage16.emit_stage16_data(pe)
    stage17.emit_stage17_data(pe)
    stage18.emit_stage18_data(pe)
    stage19.emit_stage19_data(pe)
    emit_stage20_data(pe)
    return pe.build("entry")


def write_source_stage20_audio_channels_and_deferred_sound_playback_exe(path: str | Path) -> bytes:
    image = build_source_stage20_audio_channels_and_deferred_sound_playback_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage20 audio channel-state PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage20_audio_channels_and_deferred_sound_playback.exe",
        help="path to write, default: build/source_stage20_audio_channels_and_deferred_sound_playback.exe",
    )
    args = parser.parse_args()
    write_source_stage20_audio_channels_and_deferred_sound_playback_exe(args.output)


if __name__ == "__main__":
    main()
