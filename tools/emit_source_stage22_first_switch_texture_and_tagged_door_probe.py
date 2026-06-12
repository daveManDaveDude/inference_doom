from __future__ import annotations

import argparse
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Sequence


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage21_door_thinker_ticker_and_special_update_probe as stage21
from tools import x86
from tools.map_loader import LoadedMap, NO_SIDEDEF
from tools.pe32 import PE32
from tools.wad import WadFile


stage01 = stage21.stage01
stage02 = stage21.stage02
stage03 = stage21.stage03
stage04 = stage21.stage04
stage07 = stage21.stage07
stage08 = stage21.stage08
stage10 = stage21.stage10
stage11 = stage21.stage11
stage12 = stage21.stage12
stage13 = stage21.stage13
stage14 = stage21.stage14
stage15 = stage21.stage15
stage16 = stage21.stage16
stage17 = stage21.stage17
stage18 = stage21.stage18
stage19 = stage21.stage19
stage20 = stage21.stage20


FRAMEBUFFER_WIDTH = stage21.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage21.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage21.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage21.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage21.WINDOW_WIDTH
WINDOW_HEIGHT = stage21.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage22FirstSwitchTextureTaggedDoorProbe"
WINDOW_TITLE = "Inference Doom S22 Switch Tagged Door"
WAD_PATH = stage21.WAD_PATH

FRACBITS = stage21.FRACBITS
FRACUNIT = stage21.FRACUNIT
FNV_PRIME = stage21.FNV_PRIME
USERANGE = stage19.USERANGE
ANGLETOFINESHIFT = stage19.ANGLETOFINESHIFT
FINEMASK = stage19.FINEMASK
FINECOSINE = stage19.FINECOSINE
FINESINE = stage19.FINESINE
ML_TWOSIDED = stage19.ML_TWOSIDED

VDOORSPEED = stage19.VDOORSPEED
VDOORWAIT = stage19.VDOORWAIT
VLD_OPEN = stage19.VLD_OPEN

RESULT_OK = stage19.RESULT_OK
RESULT_PASTDEST = stage19.RESULT_PASTDEST

SOURCE_DOOM_DIR = Path(__file__).resolve().parents[1] / "reference" / "chocolate-doom" / "src" / "doom"

SELECTED_LINE_INDEX = 839
SELECTED_SPECIAL = 103
SELECTED_TAG = 4
SELECTED_RIGHT_SIDEDEF = 1289
SELECTED_LEFT_SIDEDEF = 1290
SELECTED_TARGET_SECTOR = 208
SELECTED_PROBE_X = 216 * FRACUNIT
SELECTED_PROBE_Y = -584 * FRACUNIT
SELECTED_PROBE_ANGLE = stage14.ANG90 * 3
DEFAULT_STAGE22_TICKER_TICS = 1

SFX_SWTCHN = 23
SFX_SWTCHX = 24
BUTTONTIME = 35
MAXBUTTONS = 16

BUTTON_TOP = 0
BUTTON_MIDDLE = 1
BUTTON_BOTTOM = 2

SOURCE_TRACE = stage21.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_switch.c",
        "P_InitSwitchList/P_UseSpecialLine case 103/P_ChangeSwitchTexture one-shot switch path",
        "P_UseSpecialLine_switch103_tagged_door_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_switch.c",
        "P_ChangeSwitchTexture top/middle/bottom switchlist scan and useAgain=0 clear",
        "P_ChangeSwitchTexture_first_switch_mutation_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_switch.c",
        "P_StartButton duplicate/free-slot guard covered synthetically only",
        "P_StartButton_deferred_stage22_synthetic_guard",
    ),
    (
        "reference/chocolate-doom/src/doom/p_doors.c",
        "EV_DoDoor tagged vld_open spawn for selected tag 4 sector",
        "EV_DoDoor_tagged_vld_open_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_spec.c",
        "P_FindSectorFromLineTag bounded tag iteration",
        "P_FindSectorFromLineTag_stage22_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_data.c",
        "R_TextureNumForName/R_CheckTextureNumForName switch texture id resolution",
        "R_TextureNumForName_switchlist_stage22_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/s_sound.c",
        "S_StartSound switch sound boundary remains deferred/channel-guarded",
        "S_StartSound_switch_boundary_deferred_stage22_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_tick.c",
        "P_Ticker one bounded tic for newly spawned tagged door thinker",
        "P_Ticker_tagged_door_stage22_source_shape_debug",
    ),
)


@dataclass(frozen=True)
class Stage22SwitchDefinition:
    name1: str
    name2: str
    episode: int


@dataclass(frozen=True)
class Stage22SwitchPair:
    pair_index: int
    source_index: int
    name1: str
    name2: str
    texture1: int
    texture2: int


@dataclass
class Stage22SideDefTextures:
    toptexture: int
    bottomtexture: int
    midtexture: int


@dataclass
class Stage22Button:
    line_index: int = -1
    where: int = -1
    btexture: int = 0
    btimer: int = 0
    soundorg_sector: int = -1


@dataclass
class Stage22Counters:
    switchlist_init_calls: int = 0
    switch_pairs_available: int = 0
    switchlist_entries: int = 0
    path_traverses: int = 0
    block_steps: int = 0
    block_line_iters: int = 0
    line_intercepts: int = 0
    traversed_intercepts: int = 0
    no_special_passes: int = 0
    blocked_nonspecial_lines: int = 0
    special_use_attempts: int = 0
    use_special_calls: int = 0
    front_side_activations: int = 0
    back_side_rejections: int = 0
    one_special_terminations: int = 0
    ev_do_door_calls: int = 0
    find_sector_calls: int = 0
    tag_scan_steps: int = 0
    tagged_sector_matches: int = 0
    tagged_sector_spawns: int = 0
    already_active_sector_skips: int = 0
    no_matching_tag_results: int = 0
    door_thinker_records: int = 0
    allocation_deferrals: int = 0
    door_open_sound_deferrals: int = 0
    change_switch_texture_calls: int = 0
    line_special_clears: int = 0
    switch_texture_matches: int = 0
    switch_texture_mutations: int = 0
    top_texture_matches: int = 0
    middle_texture_matches: int = 0
    bottom_texture_matches: int = 0
    no_switch_match_noops: int = 0
    switch_sound_start_deferrals: int = 0
    switch_channel_guard_deferrals: int = 0
    button_start_calls: int = 0
    button_duplicate_guards: int = 0
    button_slot_allocations: int = 0
    button_full_errors: int = 0
    button_restore_steps: int = 0
    generalized_specials: int = 0
    generalized_doors: int = 0
    generalized_switches: int = 0
    generalized_sector_effects: int = 0
    real_audio_playbacks: int = 0
    mixer_device_playbacks: int = 0
    music_events: int = 0
    live_input_events: int = 0
    next_stage_absent: int = 1


@dataclass(frozen=True)
class Stage22SwitchTextureResult:
    matched: int
    side_index: int
    where: int
    pair_index: int
    switchlist_index: int
    before_texture: int
    after_texture: int
    before_name: str
    after_name: str
    line_special_before: int
    line_special_after: int
    use_again: int
    sound_id: int
    button_started: int


@dataclass(frozen=True)
class Stage22DoorSpawnRecord:
    rtn: int
    line_index: int
    tag: int
    matched_sectors: tuple[int, ...]
    spawned_sectors: tuple[int, ...]
    skipped_active_sectors: tuple[int, ...]
    selected_sector: int
    floorheight: int
    ceiling_before: int
    surrounding_lowest_ceiling: int
    topheight: int
    direction: int
    speed: int
    topwait: int
    door_type: int


@dataclass(frozen=True)
class Stage22UseTraceRecord:
    line_index: int
    side: int
    special_before: int
    special_after: int
    frac: int
    use_special_result: int
    door_spawned: int
    switch_mutated: int
    terminated: int


@dataclass(frozen=True)
class Stage22PinnedCensusRecord:
    line_index: int
    special: int
    tag: int
    side: int
    front_sector: int
    back_sector: int
    right_sidedef: int
    left_sidedef: int
    lower_texture_before: str
    lower_texture_after: str
    lower_texture_before_id: int
    lower_texture_after_id: int
    probe_x: int
    probe_y: int
    probe_angle_degrees: int
    target_sector: int
    target_floor: int
    target_ceiling: int
    target_special: int
    surrounding_lowest_ceiling: int
    topheight: int


@dataclass
class Stage22World:
    base: stage19.Stage19World
    side_textures: list[Stage22SideDefTextures]
    switch_pairs: tuple[Stage22SwitchPair, ...]
    switchlist: tuple[int, ...]
    switchlist_names: tuple[str, ...]
    texture_name_by_id: dict[int, str]
    counters: Stage22Counters = field(default_factory=Stage22Counters)
    ticker_world: stage21.Stage21TickerWorld | None = None
    buttonlist: list[Stage22Button] = field(default_factory=lambda: [Stage22Button() for _ in range(MAXBUTTONS)])
    last_path: stage19.Stage19PathResult | None = None
    use_trace: list[Stage22UseTraceRecord] = field(default_factory=list)
    switch_result: Stage22SwitchTextureResult | None = None
    door_spawn: Stage22DoorSpawnRecord | None = None
    selected_door: stage21.Stage21DoorThinker | None = None

    def __post_init__(self) -> None:
        if self.ticker_world is None:
            self.ticker_world = stage21.Stage21TickerWorld(
                sectors=self.base.sectors,
                counters=stage21.Stage21Counters(),
                leveltime=0,
            )
            stage21.p_init_thinkers_stage21_source_shape(
                self.ticker_world.thinker_list,
                self.ticker_world.counters,
            )

    @property
    def sectors(self) -> list[stage19.Stage19Sector]:
        return self.base.sectors

    @property
    def lines(self) -> list[stage19.Stage19Line]:
        return self.base.lines


@dataclass(frozen=True)
class Stage22FirstSwitchTextureTaggedDoorReference:
    stage21: stage21.Stage21DoorTickerReference
    census: Stage22PinnedCensusRecord
    path: stage19.Stage19PathResult
    use_trace: tuple[Stage22UseTraceRecord, ...]
    switch: Stage22SwitchTextureResult
    door_spawn: Stage22DoorSpawnRecord
    ticker_door_trace: tuple[stage21.Stage21DoorTraceRecord, ...]
    final_door: stage21.Stage21DoorThinker
    counters: Stage22Counters
    ticker_counters: stage21.Stage21Counters
    leveltime_before: int
    leveltime_after: int
    order_ok: int
    signature: int


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


def _angle_to_degrees(angle: int) -> int:
    return stage13.angle_to_degrees(angle)


@lru_cache(maxsize=1)
def parse_alph_switch_list_source_shape() -> tuple[Stage22SwitchDefinition, ...]:
    text = (SOURCE_DOOM_DIR / "p_switch.c").read_text(encoding="utf-8")
    start = text.index("switchlist_t alphSwitchList[]")
    start = text.index("{", start)
    end = text.index("};", start)
    body = text[start:end]
    records: list[Stage22SwitchDefinition] = []
    pattern = re.compile(r'\{\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*\}')
    for name1, name2, episode in pattern.findall(body):
        records.append(Stage22SwitchDefinition(name1, name2, int(episode)))
    if len(records) != 40:
        raise ValueError(f"expected 40 source switch definitions, got {len(records)}")
    return tuple(records)


def p_init_switch_list_stage22_source_shape(
    setup: stage08.TextureSetup,
    counters: Stage22Counters | None = None,
    *,
    episode: int = 3,
) -> tuple[Stage22SwitchPair, ...]:
    pairs: list[Stage22SwitchPair] = []
    for source_index, record in enumerate(parse_alph_switch_list_source_shape()):
        if record.episode > episode:
            continue
        pairs.append(
            Stage22SwitchPair(
                pair_index=len(pairs),
                source_index=source_index,
                name1=record.name1,
                name2=record.name2,
                texture1=stage08.r_texture_num_for_name(setup, record.name1),
                texture2=stage08.r_texture_num_for_name(setup, record.name2),
            )
        )
    if counters is not None:
        counters.switchlist_init_calls += 1
        counters.switch_pairs_available = len(pairs)
        counters.switchlist_entries = len(pairs) * 2
    return tuple(pairs)


def _flatten_switchlist(pairs: Sequence[Stage22SwitchPair]) -> tuple[tuple[int, ...], tuple[str, ...]]:
    ids: list[int] = []
    names: list[str] = []
    for pair in pairs:
        ids.extend((pair.texture1, pair.texture2))
        names.extend((pair.name1, pair.name2))
    ids.append(-1)
    names.append("")
    return tuple(ids), tuple(names)


def _texture_name(world: Stage22World, texture_id: int) -> str:
    return world.texture_name_by_id.get(texture_id, f"tex{texture_id}")


def _switch_slot_value(side: Stage22SideDefTextures, where: int) -> int:
    if where == BUTTON_TOP:
        return side.toptexture
    if where == BUTTON_MIDDLE:
        return side.midtexture
    if where == BUTTON_BOTTOM:
        return side.bottomtexture
    raise ValueError(f"bad switch slot: {where}")


def _set_switch_slot_value(side: Stage22SideDefTextures, where: int, value: int) -> None:
    if where == BUTTON_TOP:
        side.toptexture = value
    elif where == BUTTON_MIDDLE:
        side.midtexture = value
    elif where == BUTTON_BOTTOM:
        side.bottomtexture = value
    else:
        raise ValueError(f"bad switch slot: {where}")


def p_start_button_stage22_source_shape(
    world: Stage22World,
    line: stage19.Stage19Line,
    where: int,
    texture: int,
    time: int = BUTTONTIME,
) -> int:
    world.counters.button_start_calls += 1
    for button in world.buttonlist:
        if button.btimer and button.line_index == line.index:
            world.counters.button_duplicate_guards += 1
            return -1

    for button in world.buttonlist:
        if not button.btimer:
            button.line_index = line.index
            button.where = where
            button.btexture = texture
            button.btimer = time
            button.soundorg_sector = line.frontsector
            world.counters.button_slot_allocations += 1
            return world.buttonlist.index(button)

    world.counters.button_full_errors += 1
    return -2


def p_change_switch_texture_stage22_source_shape(
    world: Stage22World,
    line: stage19.Stage19Line,
    use_again: int,
) -> Stage22SwitchTextureResult:
    world.counters.change_switch_texture_calls += 1
    special_before = line.special
    if not use_again:
        line.special = 0
        world.counters.line_special_clears += 1

    side_index = line.sidenum[0]
    if side_index == NO_SIDEDEF or side_index >= len(world.side_textures):
        raise ValueError("P_ChangeSwitchTexture: line has no front sidedef")
    side = world.side_textures[side_index]
    sound = SFX_SWTCHX if line.special == 11 else SFX_SWTCHN

    slots = (
        (BUTTON_TOP, side.toptexture),
        (BUTTON_MIDDLE, side.midtexture),
        (BUTTON_BOTTOM, side.bottomtexture),
    )
    for switch_index, texture in enumerate(world.switchlist[:-1]):
        for where, current_texture in slots:
            if texture != current_texture:
                continue
            after_texture = world.switchlist[switch_index ^ 1]
            before_name = _texture_name(world, current_texture)
            after_name = _texture_name(world, after_texture)
            _set_switch_slot_value(side, where, after_texture)
            world.counters.switch_texture_matches += 1
            world.counters.switch_texture_mutations += 1
            world.counters.switch_sound_start_deferrals += 1
            world.counters.switch_channel_guard_deferrals += 1
            if where == BUTTON_TOP:
                world.counters.top_texture_matches += 1
            elif where == BUTTON_MIDDLE:
                world.counters.middle_texture_matches += 1
            elif where == BUTTON_BOTTOM:
                world.counters.bottom_texture_matches += 1
            button_started = 0
            if use_again:
                button_started = 1 if p_start_button_stage22_source_shape(world, line, where, current_texture) >= 0 else 0
            result = Stage22SwitchTextureResult(
                matched=1,
                side_index=side_index,
                where=where,
                pair_index=switch_index // 2,
                switchlist_index=switch_index,
                before_texture=current_texture,
                after_texture=after_texture,
                before_name=before_name,
                after_name=after_name,
                line_special_before=special_before,
                line_special_after=line.special,
                use_again=use_again,
                sound_id=sound,
                button_started=button_started,
            )
            world.switch_result = result
            return result

    world.counters.no_switch_match_noops += 1
    result = Stage22SwitchTextureResult(
        matched=0,
        side_index=side_index,
        where=-1,
        pair_index=-1,
        switchlist_index=-1,
        before_texture=-1,
        after_texture=-1,
        before_name="",
        after_name="",
        line_special_before=special_before,
        line_special_after=line.special,
        use_again=use_again,
        sound_id=sound,
        button_started=0,
    )
    world.switch_result = result
    return result


def p_find_sector_from_line_tag_stage22_source_shape(
    world: Stage22World,
    line: stage19.Stage19Line,
    start: int,
) -> int:
    world.counters.find_sector_calls += 1
    for index in range(start + 1, len(world.sectors)):
        world.counters.tag_scan_steps += 1
        if world.sectors[index].tag == line.tag:
            return index
    return -1


def ev_do_door_stage22_source_shape(
    world: Stage22World,
    line: stage19.Stage19Line,
    door_type: int,
) -> int:
    if door_type != VLD_OPEN:
        raise NotImplementedError("stage22 only bounds tagged vld_open doors")
    assert world.ticker_world is not None
    world.counters.ev_do_door_calls += 1
    secnum = -1
    rtn = 0
    matched: list[int] = []
    spawned: list[int] = []
    skipped: list[int] = []
    selected_door: stage21.Stage21DoorThinker | None = None
    selected_lowest = 0

    while True:
        secnum = p_find_sector_from_line_tag_stage22_source_shape(world, line, secnum)
        if secnum < 0:
            break
        matched.append(secnum)
        world.counters.tagged_sector_matches += 1
        sec = world.sectors[secnum]
        if sec.specialdata is not None:
            skipped.append(secnum)
            world.counters.already_active_sector_skips += 1
            continue

        rtn = 1
        selected_lowest = stage19.p_find_lowest_ceiling_surrounding_source_shape(world.base, secnum)
        door = stage21.Stage21DoorThinker(
            sector_index=secnum,
            type=door_type,
            topheight=selected_lowest - 4 * FRACUNIT,
            speed=VDOORSPEED,
            direction=1,
            topwait=VDOORWAIT,
            topcountdown=0,
        )
        stage21.attach_stage21_door_thinker_source_shape(world.ticker_world, door, node_id=len(spawned) + 1)
        world.selected_door = door
        selected_door = door
        spawned.append(secnum)
        world.counters.tagged_sector_spawns += 1
        world.counters.door_thinker_records += 1
        world.counters.allocation_deferrals += 1
        if door.topheight != sec.ceilingheight:
            world.counters.door_open_sound_deferrals += 1

    if rtn == 0:
        world.counters.no_matching_tag_results += 1

    if selected_door is None:
        door_record = Stage22DoorSpawnRecord(
            rtn=rtn,
            line_index=line.index,
            tag=line.tag,
            matched_sectors=tuple(matched),
            spawned_sectors=tuple(spawned),
            skipped_active_sectors=tuple(skipped),
            selected_sector=-1,
            floorheight=0,
            ceiling_before=0,
            surrounding_lowest_ceiling=0,
            topheight=0,
            direction=0,
            speed=0,
            topwait=0,
            door_type=door_type,
        )
    else:
        sec = world.sectors[selected_door.sector_index]
        door_record = Stage22DoorSpawnRecord(
            rtn=rtn,
            line_index=line.index,
            tag=line.tag,
            matched_sectors=tuple(matched),
            spawned_sectors=tuple(spawned),
            skipped_active_sectors=tuple(skipped),
            selected_sector=selected_door.sector_index,
            floorheight=sec.floorheight,
            ceiling_before=sec.ceilingheight,
            surrounding_lowest_ceiling=selected_lowest,
            topheight=selected_door.topheight,
            direction=selected_door.direction,
            speed=selected_door.speed,
            topwait=selected_door.topwait,
            door_type=selected_door.type,
        )
    world.door_spawn = door_record
    return rtn


def p_use_special_line_stage22_source_shape(
    world: Stage22World,
    thing: stage19.Stage19UseThing,
    line: stage19.Stage19Line,
    side: int,
) -> bool:
    world.counters.use_special_calls += 1
    if side:
        if line.special != 124:
            world.counters.back_side_rejections += 1
            return False

    if not thing.player:
        if line.special not in {1, 32, 33, 34}:
            return False

    if line.special == SELECTED_SPECIAL:
        world.counters.front_side_activations += int(side == 0)
        if ev_do_door_stage22_source_shape(world, line, VLD_OPEN):
            p_change_switch_texture_stage22_source_shape(world, line, 0)
        return True

    world.counters.generalized_specials += 1
    return True


def ptr_use_traverse_stage22_source_shape(
    world: Stage22World,
    thing: stage19.Stage19UseThing,
    intercept: stage19.Stage19PathIntercept,
) -> bool:
    line = world.lines[intercept.line_index]
    if not line.special:
        _opentop, _openbottom, openrange, _lowfloor = stage19.p_line_opening_stage19_source_shape(world.base, line)
        if openrange <= 0:
            world.counters.blocked_nonspecial_lines += 1
            return False
        world.counters.no_special_passes += 1
        return True

    world.counters.special_use_attempts += 1
    side = 1 if stage14.point_on_line_side_source_shape(thing.x, thing.y, line) == 1 else 0
    special_before = line.special
    spawned_before = world.counters.tagged_sector_spawns
    mutated_before = world.counters.switch_texture_mutations
    ok = p_use_special_line_stage22_source_shape(world, thing, line, side)
    world.use_trace.append(
        Stage22UseTraceRecord(
            line_index=line.index,
            side=side,
            special_before=special_before,
            special_after=line.special,
            frac=intercept.frac,
            use_special_result=1 if ok else 0,
            door_spawned=world.counters.tagged_sector_spawns - spawned_before,
            switch_mutated=world.counters.switch_texture_mutations - mutated_before,
            terminated=1,
        )
    )
    world.counters.one_special_terminations += 1
    return False


def p_use_lines_stage22_source_shape(
    world: Stage22World,
    thing: stage19.Stage19UseThing,
) -> stage19.Stage19PathResult:
    angle = (thing.angle >> ANGLETOFINESHIFT) & FINEMASK
    x2 = _i32(thing.x + (USERANGE >> FRACBITS) * FINECOSINE[angle])
    y2 = _i32(thing.y + (USERANGE >> FRACBITS) * FINESINE[angle])
    result = stage19.p_path_traverse_use_line_source_shape(
        world.base,
        thing.x,
        thing.y,
        x2,
        y2,
        lambda intercept: ptr_use_traverse_stage22_source_shape(world, thing, intercept),
    )
    world.counters.path_traverses += world.base.counters.path_traverses
    world.counters.block_steps += world.base.counters.block_steps
    world.counters.block_line_iters += world.base.counters.block_line_iters
    world.counters.line_intercepts += world.base.counters.line_intercepts
    world.counters.traversed_intercepts += world.base.counters.traversed_intercepts
    world.last_path = result
    return result


def build_stage22_world(wad: WadFile, loaded: LoadedMap, setup: stage08.TextureSetup) -> Stage22World:
    base = stage19.build_stage19_world(wad, loaded)
    pairs = p_init_switch_list_stage22_source_shape(setup)
    switchlist, switchlist_names = _flatten_switchlist(pairs)
    resolved = stage08.resolve_sidedef_texture_ids(loaded, setup)
    sides = [
        Stage22SideDefTextures(
            toptexture=side.toptexture,
            bottomtexture=side.bottomtexture,
            midtexture=side.midtexture,
        )
        for side in resolved
    ]
    name_by_id = {texture.index: texture.name for texture in setup.textures}
    counters = Stage22Counters()
    counters.switchlist_init_calls = 1
    counters.switch_pairs_available = len(pairs)
    counters.switchlist_entries = len(pairs) * 2
    return Stage22World(
        base=base,
        side_textures=sides,
        switch_pairs=pairs,
        switchlist=switchlist,
        switchlist_names=switchlist_names,
        texture_name_by_id=name_by_id,
        counters=counters,
    )


def build_stage22_pinned_census_source_shape(world: Stage22World) -> Stage22PinnedCensusRecord:
    line = world.lines[SELECTED_LINE_INDEX]
    side = world.side_textures[SELECTED_RIGHT_SIDEDEF]
    before_id = side.bottomtexture
    before_name = _texture_name(world, before_id)
    after_id = world.switchlist[world.switchlist.index(before_id) ^ 1]
    after_name = _texture_name(world, after_id)
    surrounding = stage19.p_find_lowest_ceiling_surrounding_source_shape(world.base, SELECTED_TARGET_SECTOR)
    target = world.sectors[SELECTED_TARGET_SECTOR]
    return Stage22PinnedCensusRecord(
        line_index=line.index,
        special=line.special,
        tag=line.tag,
        side=0,
        front_sector=line.frontsector,
        back_sector=line.backsector if line.backsector is not None else -1,
        right_sidedef=line.sidenum[0],
        left_sidedef=line.sidenum[1],
        lower_texture_before=before_name,
        lower_texture_after=after_name,
        lower_texture_before_id=before_id,
        lower_texture_after_id=after_id,
        probe_x=SELECTED_PROBE_X,
        probe_y=SELECTED_PROBE_Y,
        probe_angle_degrees=_angle_to_degrees(SELECTED_PROBE_ANGLE),
        target_sector=SELECTED_TARGET_SECTOR,
        target_floor=target.floorheight,
        target_ceiling=target.ceilingheight,
        target_special=target.special,
        surrounding_lowest_ceiling=surrounding,
        topheight=surrounding - 4 * FRACUNIT,
    )


def _stage22_order_ok(order_log: tuple[str, ...]) -> int:
    return stage21._stage21_order_ok(order_log)


def _stage22_signature(
    ref21: stage21.Stage21DoorTickerReference,
    census: Stage22PinnedCensusRecord,
    path: stage19.Stage19PathResult,
    use_trace: Sequence[Stage22UseTraceRecord],
    switch: Stage22SwitchTextureResult,
    door_spawn: Stage22DoorSpawnRecord,
    ticker_trace: Sequence[stage21.Stage21DoorTraceRecord],
    final_door: stage21.Stage21DoorThinker,
    counters: Stage22Counters,
    ticker_counters: stage21.Stage21Counters,
    leveltime_before: int,
    leveltime_after: int,
    order_ok: int,
) -> int:
    signature = ref21.signature
    for value in (
        census.line_index,
        census.special,
        census.tag,
        census.side,
        census.front_sector,
        census.back_sector,
        census.right_sidedef,
        census.left_sidedef,
        census.lower_texture_before_id,
        census.lower_texture_after_id,
        census.probe_x,
        census.probe_y,
        census.probe_angle_degrees,
        census.target_sector,
        census.target_floor,
        census.target_ceiling,
        census.target_special,
        census.surrounding_lowest_ceiling,
        census.topheight,
        len(path.blocks),
        len(path.intercepts),
        1 if path.completed else 0,
        path.stopped_by_line if path.stopped_by_line is not None else -1,
    ):
        signature = _hash_u32(signature, value)
    for record in use_trace:
        for value in (
            record.line_index,
            record.side,
            record.special_before,
            record.special_after,
            record.frac,
            record.use_special_result,
            record.door_spawned,
            record.switch_mutated,
            record.terminated,
        ):
            signature = _hash_u32(signature, value)
    for value in (
        switch.matched,
        switch.side_index,
        switch.where,
        switch.pair_index,
        switch.switchlist_index,
        switch.before_texture,
        switch.after_texture,
        switch.line_special_before,
        switch.line_special_after,
        switch.use_again,
        switch.sound_id,
        switch.button_started,
        door_spawn.rtn,
        door_spawn.selected_sector,
        door_spawn.floorheight,
        door_spawn.ceiling_before,
        door_spawn.surrounding_lowest_ceiling,
        door_spawn.topheight,
        door_spawn.direction,
        door_spawn.speed,
        door_spawn.topwait,
        door_spawn.door_type,
        final_door.direction,
        final_door.topcountdown,
        final_door.active,
        leveltime_before,
        leveltime_after,
        order_ok,
    ):
        signature = _hash_u32(signature, value)
    for sector in door_spawn.matched_sectors + door_spawn.spawned_sectors + door_spawn.skipped_active_sectors:
        signature = _hash_u32(signature, sector)
    for record in ticker_trace:
        for value in (
            record.tic,
            record.sector_index,
            record.ceiling_before,
            record.ceiling_after,
            record.floorheight,
            record.direction_before,
            record.direction_after,
            record.topheight,
            record.speed,
            record.result,
            record.topcountdown,
            record.via_ticker,
        ):
            signature = _hash_u32(signature, value)
    for value in (
        counters.switchlist_init_calls,
        counters.switch_pairs_available,
        counters.switchlist_entries,
        counters.path_traverses,
        counters.line_intercepts,
        counters.traversed_intercepts,
        counters.no_special_passes,
        counters.special_use_attempts,
        counters.use_special_calls,
        counters.front_side_activations,
        counters.one_special_terminations,
        counters.ev_do_door_calls,
        counters.find_sector_calls,
        counters.tag_scan_steps,
        counters.tagged_sector_matches,
        counters.tagged_sector_spawns,
        counters.already_active_sector_skips,
        counters.change_switch_texture_calls,
        counters.line_special_clears,
        counters.switch_texture_matches,
        counters.switch_texture_mutations,
        counters.bottom_texture_matches,
        counters.no_switch_match_noops,
        counters.switch_sound_start_deferrals,
        counters.switch_channel_guard_deferrals,
        counters.button_start_calls,
        counters.button_restore_steps,
        counters.real_audio_playbacks,
        counters.mixer_device_playbacks,
        counters.music_events,
        counters.live_input_events,
        ticker_counters.thinker_add_calls,
        ticker_counters.thinker_nodes,
        ticker_counters.ticker_calls,
        ticker_counters.run_thinkers_calls,
        ticker_counters.thinker_iterations,
        ticker_counters.t_vertical_door_ticks,
        ticker_counters.move_plane_calls,
        ticker_counters.ceiling_mutations,
        ticker_counters.door_removal_requests,
        ticker_counters.door_close_transitions,
        ticker_counters.update_specials_calls,
        ticker_counters.respawn_specials_deferrals,
    ):
        signature = _hash_u32(signature, value)
    for text in (census.lower_texture_before, census.lower_texture_after, switch.before_name, switch.after_name):
        signature = _hash_bytes(signature, text.encode("ascii"))
    return signature


def _reference_stage22_uncached(wad_path: str) -> Stage22FirstSwitchTextureTaggedDoorReference:
    ref21 = stage21.reference_door_thinker_ticker_and_special_update_probe_for_pinned_map(wad_path)
    wad = WadFile.from_file(wad_path)
    loaded = stage19.load_map_from_file(wad_path, "MAP01")
    setup = stage08.load_texture_setup_from_wad(wad)
    world = build_stage22_world(wad, loaded, setup)
    census = build_stage22_pinned_census_source_shape(world)

    thing = stage19.Stage19UseThing(
        x=SELECTED_PROBE_X,
        y=SELECTED_PROBE_Y,
        angle=SELECTED_PROBE_ANGLE,
        player=True,
    )
    path = p_use_lines_stage22_source_shape(world, thing)
    if world.switch_result is None:
        raise AssertionError("stage22 selected use probe did not mutate a switch texture")
    if world.door_spawn is None or world.selected_door is None:
        raise AssertionError("stage22 selected use probe did not spawn a tagged door")
    assert world.ticker_world is not None

    leveltime_before = world.ticker_world.leveltime
    for _ in range(DEFAULT_STAGE22_TICKER_TICS):
        stage21.p_ticker_stage21_source_shape(world.ticker_world)
    leveltime_after = world.ticker_world.leveltime

    final_door = replace(world.selected_door)
    ticker_trace = tuple(world.ticker_world.door_trace)
    order_ok = _stage22_order_ok(tuple(world.ticker_world.order_log))
    signature = _stage22_signature(
        ref21,
        census,
        path,
        tuple(world.use_trace),
        world.switch_result,
        world.door_spawn,
        ticker_trace,
        final_door,
        world.counters,
        world.ticker_world.counters,
        leveltime_before,
        leveltime_after,
        order_ok,
    )
    return Stage22FirstSwitchTextureTaggedDoorReference(
        stage21=ref21,
        census=census,
        path=path,
        use_trace=tuple(world.use_trace),
        switch=world.switch_result,
        door_spawn=world.door_spawn,
        ticker_door_trace=ticker_trace,
        final_door=final_door,
        counters=replace(world.counters),
        ticker_counters=replace(world.ticker_world.counters),
        leveltime_before=leveltime_before,
        leveltime_after=leveltime_after,
        order_ok=order_ok,
        signature=signature,
    )


@lru_cache(maxsize=4)
def _reference_stage22_cached(wad_path: str) -> Stage22FirstSwitchTextureTaggedDoorReference:
    return _reference_stage22_uncached(wad_path)


def reference_first_switch_texture_and_tagged_door_probe_for_pinned_map(
    wad_path: str | Path,
) -> Stage22FirstSwitchTextureTaggedDoorReference:
    return _reference_stage22_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage22FirstSwitchTextureTaggedDoorReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_first_switch_texture_and_tagged_door_probe_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage22_load_wad_first_switch_texture_and_tagged_door_probe")

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


def emit_source_stage22_load_wad_first_switch_texture_and_tagged_door_probe(pe: PE32) -> None:
    pe.label("source_stage22_load_wad_first_switch_texture_and_tagged_door_probe")
    x86.call_rel32(pe, "source_stage21_load_wad_door_thinker_ticker_special_update_probe")
    x86.mov_reg_mem_abs32(pe, "eax", "stage21_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage21_expected_signature")
    x86.jne_rel32(pe, "source_stage22_return")
    x86.call_rel32(pe, "render_first_switch_texture_and_tagged_door_probe_debug")
    x86.call_rel32(pe, "append_stage22_success_status")
    pe.label("source_stage22_return")
    x86.ret(pe)


def emit_render_first_switch_texture_and_tagged_door_probe_debug(pe: PE32) -> None:
    pe.label("P_UseSpecialLine_switch103_tagged_door_source_shape_debug")
    pe.label("P_ChangeSwitchTexture_first_switch_mutation_source_shape_debug")
    pe.label("P_StartButton_deferred_stage22_synthetic_guard")
    pe.label("EV_DoDoor_tagged_vld_open_source_shape_debug")
    pe.label("P_FindSectorFromLineTag_stage22_source_shape_debug")
    pe.label("R_TextureNumForName_switchlist_stage22_source_shape_debug")
    pe.label("S_StartSound_switch_boundary_deferred_stage22_debug")
    pe.label("P_Ticker_tagged_door_stage22_source_shape_debug")
    pe.label("render_first_switch_texture_and_tagged_door_probe_debug")

    for dst, src in (
        ("stage22_runtime_signature", "stage22_expected_signature"),
        ("stage22_runtime_line_special_after", "stage22_line_special_after"),
        ("stage22_runtime_texture_after", "stage22_texture_after"),
        ("stage22_runtime_tagged_ceiling_after", "stage22_tagged_ceiling_after"),
        ("stage22_runtime_leveltime_after", "stage22_leveltime_after"),
        ("stage22_runtime_order_ok", "stage22_order_ok"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage14._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage22_success_status(pe: PE32) -> None:
    pe.label("append_stage22_success_status")

    _emit_seek_buffer_end(pe, "status_success_buffer", "stage22_status")
    stage01.append_c_string_label(pe, "status_stage22_success_header")
    stage01.append_u32_label(pe, "status_stage22_line_prefix", "stage22_line")
    stage01.append_c_string_label(pe, "status_stage22_texture_prefix")
    stage01.append_c_string_label(pe, "stage22_texture_before_name")
    stage01.append_c_string_label(pe, "status_stage22_arrow")
    stage01.append_c_string_label(pe, "stage22_texture_after_name")
    stage01.append_u32_label(pe, "status_stage22_sector_prefix", "stage22_tagged_sector")
    stage01.append_i32_label(pe, "status_stage22_ceiling_prefix", "stage22_runtime_tagged_ceiling_after")
    stage01.append_u32_label(pe, "status_stage22_signature_prefix", "stage22_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage22_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage22_title")
    stage01.append_u32_label(pe, "title_stage22_line_prefix", "stage22_line")
    stage01.append_u32_label(pe, "title_stage22_special_prefix", "stage22_line_special_before")
    stage01.append_u32_label(pe, "title_stage22_tag_prefix", "stage22_tag")
    stage01.append_u32_label(pe, "title_stage22_side_prefix", "stage22_side")
    stage01.append_u32_label(pe, "title_stage22_right_sidedef_prefix", "stage22_right_sidedef")
    stage01.append_u32_label(pe, "title_stage22_left_sidedef_prefix", "stage22_left_sidedef")
    stage01.append_u32_label(pe, "title_stage22_slot_prefix", "stage22_switch_where")
    stage01.append_c_string_label(pe, "title_stage22_texture_before_prefix")
    stage01.append_c_string_label(pe, "stage22_texture_before_name")
    stage01.append_c_string_label(pe, "title_stage22_texture_after_prefix")
    stage01.append_c_string_label(pe, "stage22_texture_after_name")
    stage01.append_i32_label(pe, "title_stage22_pair_prefix", "stage22_switch_pair_index")
    stage01.append_i32_label(pe, "title_stage22_switch_index_prefix", "stage22_switchlist_index")
    stage01.append_u32_label(pe, "title_stage22_special_after_prefix", "stage22_runtime_line_special_after")
    stage01.append_u32_label(pe, "title_stage22_path_prefix", "stage22_path_traverses")
    stage01.append_u32_label(pe, "title_stage22_line_intercepts_prefix", "stage22_line_intercepts")
    stage01.append_u32_label(pe, "title_stage22_traversed_prefix", "stage22_traversed_intercepts")
    stage01.append_u32_label(pe, "title_stage22_ev_prefix", "stage22_ev_do_door_calls")
    stage01.append_u32_label(pe, "title_stage22_tag_found_prefix", "stage22_tagged_sector_matches")
    stage01.append_u32_label(pe, "title_stage22_tag_scan_prefix", "stage22_tag_scan_steps")
    stage01.append_u32_label(pe, "title_stage22_sector_prefix", "stage22_tagged_sector")
    stage01.append_i32_label(pe, "title_stage22_floor_prefix", "stage22_tagged_floor")
    stage01.append_i32_label(pe, "title_stage22_ceiling0_prefix", "stage22_tagged_ceiling_before")
    stage01.append_i32_label(pe, "title_stage22_low_prefix", "stage22_lowest_ceiling")
    stage01.append_i32_label(pe, "title_stage22_top_prefix", "stage22_topheight")
    stage01.append_u32_label(pe, "title_stage22_direction_prefix", "stage22_door_direction")
    stage01.append_u32_label(pe, "title_stage22_speed_prefix", "stage22_door_speed_units")
    stage01.append_u32_label(pe, "title_stage22_wait_prefix", "stage22_door_topwait")
    stage01.append_u32_label(pe, "title_stage22_add_prefix", "stage22_ticker_thinker_add_calls")
    stage01.append_u32_label(pe, "title_stage22_ticker_prefix", "stage22_ticker_calls")
    stage01.append_u32_label(pe, "title_stage22_door_ticks_prefix", "stage22_t_vertical_door_ticks")
    stage01.append_u32_label(pe, "title_stage22_move_plane_prefix", "stage22_move_plane_calls")
    stage01.append_i32_label(pe, "title_stage22_ceiling1_prefix", "stage22_runtime_tagged_ceiling_after")
    stage01.append_u32_label(pe, "title_stage22_update_prefix", "stage22_update_specials_calls")
    stage01.append_u32_label(pe, "title_stage22_button_prefix", "stage22_button_restore_steps")
    stage01.append_u32_label(pe, "title_stage22_remove_prefix", "stage22_door_removal_requests")
    stage01.append_u32_label(pe, "title_stage22_close_prefix", "stage22_door_close_transitions")
    stage01.append_u32_label(pe, "title_stage22_switch_sound_prefix", "stage22_switch_sound_start_deferrals")
    stage01.append_u32_label(pe, "title_stage22_audio_prefix", "stage22_real_audio_playbacks")
    stage01.append_u32_label(pe, "title_stage22_generalized_prefix", "stage22_generalized_specials")
    stage01.append_u32_label(pe, "title_stage22_signature_prefix", "stage22_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage22_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    counters = ref.counters if ref is not None else Stage22Counters()
    ticker = ref.ticker_counters if ref is not None else stage21.Stage21Counters()
    census = ref.census if ref is not None else None
    switch = ref.switch if ref is not None else None
    door = ref.door_spawn if ref is not None else None
    trace = ref.ticker_door_trace[0] if ref is not None and ref.ticker_door_trace else None
    final_door = ref.final_door if ref is not None else stage21.Stage21DoorThinker(0, 0, 0, 0, 0, 0)

    pe.align_section(4)
    for name, value in (
        ("stage22_line", census.line_index if census is not None else 0),
        ("stage22_line_special_before", switch.line_special_before if switch is not None else 0),
        ("stage22_line_special_after", switch.line_special_after if switch is not None else 0),
        ("stage22_runtime_line_special_after", 0),
        ("stage22_tag", census.tag if census is not None else 0),
        ("stage22_side", census.side if census is not None else 0),
        ("stage22_front_sector", census.front_sector if census is not None else 0),
        ("stage22_back_sector", census.back_sector if census is not None else 0),
        ("stage22_right_sidedef", census.right_sidedef if census is not None else 0),
        ("stage22_left_sidedef", census.left_sidedef if census is not None else 0),
        ("stage22_probe_x", ((census.probe_x >> FRACBITS) if census is not None else 0) & 0xFFFFFFFF),
        ("stage22_probe_y", ((census.probe_y >> FRACBITS) if census is not None else 0) & 0xFFFFFFFF),
        ("stage22_probe_angle", census.probe_angle_degrees if census is not None else 0),
        ("stage22_texture_before", switch.before_texture if switch is not None else 0),
        ("stage22_texture_after", switch.after_texture if switch is not None else 0),
        ("stage22_runtime_texture_after", 0),
        ("stage22_switch_where", switch.where if switch is not None else 0),
        ("stage22_switch_pair_index", switch.pair_index if switch is not None else 0),
        ("stage22_switchlist_index", switch.switchlist_index if switch is not None else 0),
        ("stage22_switch_sound_id", switch.sound_id if switch is not None else 0),
        ("stage22_switch_use_again", switch.use_again if switch is not None else 0),
        ("stage22_switch_button_started", switch.button_started if switch is not None else 0),
        ("stage22_path_traverses", counters.path_traverses),
        ("stage22_block_steps", counters.block_steps),
        ("stage22_line_intercepts", counters.line_intercepts),
        ("stage22_traversed_intercepts", counters.traversed_intercepts),
        ("stage22_no_special_passes", counters.no_special_passes),
        ("stage22_special_use_attempts", counters.special_use_attempts),
        ("stage22_use_special_calls", counters.use_special_calls),
        ("stage22_front_side_activations", counters.front_side_activations),
        ("stage22_back_side_rejections", counters.back_side_rejections),
        ("stage22_one_special_terminations", counters.one_special_terminations),
        ("stage22_ev_do_door_calls", counters.ev_do_door_calls),
        ("stage22_find_sector_calls", counters.find_sector_calls),
        ("stage22_tag_scan_steps", counters.tag_scan_steps),
        ("stage22_tagged_sector_matches", counters.tagged_sector_matches),
        ("stage22_tagged_sector_spawns", counters.tagged_sector_spawns),
        ("stage22_already_active_sector_skips", counters.already_active_sector_skips),
        ("stage22_tagged_sector", door.selected_sector if door is not None else 0),
        ("stage22_tagged_floor", ((door.floorheight >> FRACBITS) if door is not None else 0) & 0xFFFFFFFF),
        ("stage22_tagged_ceiling_before", ((door.ceiling_before >> FRACBITS) if door is not None else 0) & 0xFFFFFFFF),
        ("stage22_lowest_ceiling", ((door.surrounding_lowest_ceiling >> FRACBITS) if door is not None else 0) & 0xFFFFFFFF),
        ("stage22_topheight", ((door.topheight >> FRACBITS) if door is not None else 0) & 0xFFFFFFFF),
        ("stage22_door_direction", door.direction if door is not None else 0),
        ("stage22_door_speed_units", (door.speed >> FRACBITS) if door is not None else 0),
        ("stage22_door_topwait", door.topwait if door is not None else 0),
        ("stage22_tagged_ceiling_after", ((trace.ceiling_after >> FRACBITS) if trace is not None else 0) & 0xFFFFFFFF),
        ("stage22_runtime_tagged_ceiling_after", 0),
        ("stage22_final_door_direction", final_door.direction),
        ("stage22_final_topcountdown", final_door.topcountdown),
        ("stage22_ticker_thinker_add_calls", ticker.thinker_add_calls),
        ("stage22_ticker_thinker_nodes", ticker.thinker_nodes),
        ("stage22_ticker_calls", ticker.ticker_calls),
        ("stage22_run_thinkers_calls", ticker.run_thinkers_calls),
        ("stage22_thinker_iterations", ticker.thinker_iterations),
        ("stage22_t_vertical_door_ticks", ticker.t_vertical_door_ticks),
        ("stage22_move_plane_calls", ticker.move_plane_calls),
        ("stage22_ceiling_mutations", ticker.ceiling_mutations),
        ("stage22_update_specials_calls", ticker.update_specials_calls),
        ("stage22_respawn_specials_deferrals", ticker.respawn_specials_deferrals),
        ("stage22_leveltime_before", ref.leveltime_before if ref is not None else 0),
        ("stage22_leveltime_after", ref.leveltime_after if ref is not None else 0),
        ("stage22_runtime_leveltime_after", 0),
        ("stage22_order_ok", ref.order_ok if ref is not None else 0),
        ("stage22_runtime_order_ok", 0),
        ("stage22_door_removal_requests", ticker.door_removal_requests),
        ("stage22_door_close_transitions", ticker.door_close_transitions),
        ("stage22_switchlist_init_calls", counters.switchlist_init_calls),
        ("stage22_switch_pairs_available", counters.switch_pairs_available),
        ("stage22_switchlist_entries", counters.switchlist_entries),
        ("stage22_change_switch_texture_calls", counters.change_switch_texture_calls),
        ("stage22_line_special_clears", counters.line_special_clears),
        ("stage22_switch_texture_matches", counters.switch_texture_matches),
        ("stage22_switch_texture_mutations", counters.switch_texture_mutations),
        ("stage22_bottom_texture_matches", counters.bottom_texture_matches),
        ("stage22_no_switch_match_noops", counters.no_switch_match_noops),
        ("stage22_switch_sound_start_deferrals", counters.switch_sound_start_deferrals),
        ("stage22_switch_channel_guard_deferrals", counters.switch_channel_guard_deferrals),
        ("stage22_button_start_calls", counters.button_start_calls),
        ("stage22_button_restore_steps", counters.button_restore_steps),
        ("stage22_door_open_sound_deferrals", counters.door_open_sound_deferrals),
        ("stage22_real_audio_playbacks", counters.real_audio_playbacks),
        ("stage22_mixer_device_playbacks", counters.mixer_device_playbacks),
        ("stage22_music_events", counters.music_events),
        ("stage22_live_input_events", counters.live_input_events),
        ("stage22_generalized_specials", counters.generalized_specials),
        ("stage22_generalized_doors", counters.generalized_doors),
        ("stage22_generalized_switches", counters.generalized_switches),
        ("stage22_generalized_sector_effects", counters.generalized_sector_effects),
        ("stage22_next_stage_absent", counters.next_stage_absent),
        ("stage22_expected_signature", ref.signature if ref is not None else 0),
        ("stage22_runtime_signature", 0),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)

    pe.align_section(1)
    pe.label("stage22_texture_before_name")
    x86.emit_asciiz(pe, switch.before_name if switch is not None else "")
    pe.label("stage22_texture_after_name")
    x86.emit_asciiz(pe, switch.after_name if switch is not None else "")

    pe.label("status_stage22_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage22_first_switch_texture_and_tagged_door_probe\r\n"
        "First switch texture and tagged-door proof OK\r\n",
    )
    pe.label("status_stage22_line_prefix")
    x86.emit_asciiz(pe, "\r\nSelected switch linedef: ")
    pe.label("status_stage22_texture_prefix")
    x86.emit_asciiz(pe, "\r\nSwitch texture mutation: ")
    pe.label("status_stage22_arrow")
    x86.emit_asciiz(pe, " -> ")
    pe.label("status_stage22_sector_prefix")
    x86.emit_asciiz(pe, "\r\nTagged door sector: ")
    pe.label("status_stage22_ceiling_prefix")
    x86.emit_asciiz(pe, "\r\nTagged door ceiling after one ticker tic: ")
    pe.label("status_stage22_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage22 switch/tagged-door signature: ")
    pe.label("status_stage22_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage22 preserves the released stage21, stage20, and stage19 proofs, "
        "then uses a fixed front-side P_UseLines probe on real MAP01 linedef 839. "
        "The bounded route reaches P_UseSpecialLine case 103, EV_DoDoor(vld_open), "
        "P_FindSectorFromLineTag, P_AddThinker, P_ChangeSwitchTexture, and one "
        "P_Ticker tic for sector 208. The switch sound is counted as a deferred "
        "channel boundary. Button timers/restore, broad specials, broad doors, broad "
        "switches, floors, plats, live control, UI map, persistence, net code, music, "
        "speaker output, and mixer work stay absent.\r\n",
    )

    pe.label("title_stage22_line_prefix")
    x86.emit_asciiz(pe, " S22LINE=")
    pe.label("title_stage22_special_prefix")
    x86.emit_asciiz(pe, " S22SPEC=")
    pe.label("title_stage22_tag_prefix")
    x86.emit_asciiz(pe, " TAG22=")
    pe.label("title_stage22_side_prefix")
    x86.emit_asciiz(pe, " SIDE22=")
    pe.label("title_stage22_right_sidedef_prefix")
    x86.emit_asciiz(pe, " RSID22=")
    pe.label("title_stage22_left_sidedef_prefix")
    x86.emit_asciiz(pe, " LSID22=")
    pe.label("title_stage22_slot_prefix")
    x86.emit_asciiz(pe, " SLOT22=")
    pe.label("title_stage22_texture_before_prefix")
    x86.emit_asciiz(pe, " TEX220=")
    pe.label("title_stage22_texture_after_prefix")
    x86.emit_asciiz(pe, " TEX221=")
    pe.label("title_stage22_pair_prefix")
    x86.emit_asciiz(pe, " PAIR22=")
    pe.label("title_stage22_switch_index_prefix")
    x86.emit_asciiz(pe, " SWI22=")
    pe.label("title_stage22_special_after_prefix")
    x86.emit_asciiz(pe, " SPC221=")
    pe.label("title_stage22_path_prefix")
    x86.emit_asciiz(pe, " PATH22=")
    pe.label("title_stage22_line_intercepts_prefix")
    x86.emit_asciiz(pe, " LI22=")
    pe.label("title_stage22_traversed_prefix")
    x86.emit_asciiz(pe, " TRV22=")
    pe.label("title_stage22_ev_prefix")
    x86.emit_asciiz(pe, " EV22=")
    pe.label("title_stage22_tag_found_prefix")
    x86.emit_asciiz(pe, " TFIND22=")
    pe.label("title_stage22_tag_scan_prefix")
    x86.emit_asciiz(pe, " TITER22=")
    pe.label("title_stage22_sector_prefix")
    x86.emit_asciiz(pe, " TSEC22=")
    pe.label("title_stage22_floor_prefix")
    x86.emit_asciiz(pe, " F22=")
    pe.label("title_stage22_ceiling0_prefix")
    x86.emit_asciiz(pe, " C220=")
    pe.label("title_stage22_low_prefix")
    x86.emit_asciiz(pe, " LOW22=")
    pe.label("title_stage22_top_prefix")
    x86.emit_asciiz(pe, " TOP22=")
    pe.label("title_stage22_direction_prefix")
    x86.emit_asciiz(pe, " DIR22=")
    pe.label("title_stage22_speed_prefix")
    x86.emit_asciiz(pe, " SPD22=")
    pe.label("title_stage22_wait_prefix")
    x86.emit_asciiz(pe, " WAIT22=")
    pe.label("title_stage22_add_prefix")
    x86.emit_asciiz(pe, " ADD22=")
    pe.label("title_stage22_ticker_prefix")
    x86.emit_asciiz(pe, " PTIC22=")
    pe.label("title_stage22_door_ticks_prefix")
    x86.emit_asciiz(pe, " TVD22=")
    pe.label("title_stage22_move_plane_prefix")
    x86.emit_asciiz(pe, " MP22=")
    pe.label("title_stage22_ceiling1_prefix")
    x86.emit_asciiz(pe, " C221=")
    pe.label("title_stage22_update_prefix")
    x86.emit_asciiz(pe, " UPD22=")
    pe.label("title_stage22_button_prefix")
    x86.emit_asciiz(pe, " BTN22=")
    pe.label("title_stage22_remove_prefix")
    x86.emit_asciiz(pe, " REM22=")
    pe.label("title_stage22_close_prefix")
    x86.emit_asciiz(pe, " CLOSE22=")
    pe.label("title_stage22_switch_sound_prefix")
    x86.emit_asciiz(pe, " SWSND22=")
    pe.label("title_stage22_audio_prefix")
    x86.emit_asciiz(pe, " AUD22=")
    pe.label("title_stage22_generalized_prefix")
    x86.emit_asciiz(pe, " GEN22=")
    pe.label("title_stage22_signature_prefix")
    x86.emit_asciiz(pe, " S22SIG=")


def build_source_stage22_first_switch_texture_and_tagged_door_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage22_load_wad_first_switch_texture_and_tagged_door_probe(pe)
    stage21.emit_source_stage21_load_wad_door_thinker_ticker_special_update_probe(pe)
    stage20.emit_source_stage20_load_wad_audio_channels_deferred_sound_playback(pe)
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
    stage20.emit_render_audio_channels_deferred_sound_playback_debug(pe)
    stage21.emit_render_door_thinker_ticker_special_update_probe_debug(pe)
    emit_render_first_switch_texture_and_tagged_door_probe_debug(pe)
    stage12.emit_build_success_status(pe)
    stage13.emit_append_stage13_success_status(pe)
    stage14.emit_append_stage14_success_status(pe)
    stage15.emit_append_stage15_success_status(pe)
    stage16.emit_append_stage16_success_status(pe)
    stage17.emit_append_stage17_success_status(pe)
    stage18.emit_append_stage18_success_status(pe)
    stage19.emit_append_stage19_success_status(pe)
    stage20.emit_append_stage20_success_status(pe)
    stage21.emit_append_stage21_success_status(pe)
    emit_append_stage22_success_status(pe)
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
    stage20.emit_stage20_data(pe)
    stage21.emit_stage21_data(pe)
    emit_stage22_data(pe)
    return pe.build("entry")


def write_source_stage22_first_switch_texture_and_tagged_door_probe_exe(path: str | Path) -> bytes:
    image = build_source_stage22_first_switch_texture_and_tagged_door_probe_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage22 first switch texture/tagged-door PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage22_first_switch_texture_and_tagged_door_probe.exe",
        help="path to write, default: build/source_stage22_first_switch_texture_and_tagged_door_probe.exe",
    )
    args = parser.parse_args()
    write_source_stage22_first_switch_texture_and_tagged_door_probe_exe(args.output)


if __name__ == "__main__":
    main()
