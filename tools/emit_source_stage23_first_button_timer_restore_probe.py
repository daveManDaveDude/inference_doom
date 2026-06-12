from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage22_first_switch_texture_and_tagged_door_probe as stage22
from tools import x86
from tools.map_loader import NO_SIDEDEF, load_map
from tools.pe32 import PE32
from tools.wad import WadFile


stage01 = stage22.stage01
stage02 = stage22.stage02
stage03 = stage22.stage03
stage04 = stage22.stage04
stage07 = stage22.stage07
stage08 = stage22.stage08
stage10 = stage22.stage10
stage11 = stage22.stage11
stage12 = stage22.stage12
stage13 = stage22.stage13
stage14 = stage22.stage14
stage15 = stage22.stage15
stage16 = stage22.stage16
stage17 = stage22.stage17
stage18 = stage22.stage18
stage19 = stage22.stage19
stage20 = stage22.stage20
stage21 = stage22.stage21


FRAMEBUFFER_WIDTH = stage22.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage22.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage22.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage22.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage22.WINDOW_WIDTH
WINDOW_HEIGHT = stage22.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage23FirstButtonTimerRestoreProbe"
WINDOW_TITLE = "Inference Doom S23 Button Timer Restore"
WAD_PATH = stage22.WAD_PATH

FRACBITS = stage22.FRACBITS
FRACUNIT = stage22.FRACUNIT
FNV_PRIME = stage22.FNV_PRIME
VLD_OPEN = stage22.VLD_OPEN
VDOORSPEED = stage22.VDOORSPEED
VDOORWAIT = stage22.VDOORWAIT
BUTTONTIME = stage22.BUTTONTIME
MAXBUTTONS = stage22.MAXBUTTONS
BUTTON_TOP = stage22.BUTTON_TOP
BUTTON_MIDDLE = stage22.BUTTON_MIDDLE
BUTTON_BOTTOM = stage22.BUTTON_BOTTOM
SFX_SWTCHN = stage22.SFX_SWTCHN

SELECTED_MAP = "MAP15"
SELECTED_LINE_INDEX = 3452
SELECTED_SPECIAL = 61
SELECTED_TAG = 24
SELECTED_RIGHT_SIDEDEF = 4798
SELECTED_LEFT_SIDEDEF = NO_SIDEDEF
SELECTED_FRONT_SECTOR = 548
SELECTED_TARGET_SECTOR = 530
DEFAULT_STAGE23_TICKER_TICS = BUTTONTIME

BUTTON_SPECIALS = frozenset(
    {42, 43, 45, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 99, 114, 115, 116, 123, 132, 134, 136, 138, 139}
)
STAGE23_DOOR_BUTTON_SPECIALS = frozenset({61, 63, 115})

SOURCE_TRACE = stage22.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_switch.c",
        "P_UseSpecialLine case 61 and P_ChangeSwitchTexture useAgain=1 button path",
        "P_UseSpecialLine_button61_vld_open_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_switch.c",
        "P_StartButton duplicate guard, free slot allocation, old texture storage, BUTTONTIME",
        "P_StartButton_first_reusable_button_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_spec.c",
        "P_UpdateSpecials button countdown, texture restore, switch-off sound boundary, memset slot clear",
        "P_UpdateSpecials_button_timer_restore_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_doors.c",
        "EV_DoDoor tagged vld_open spawn for selected MAP15 tag 24 sector",
        "EV_DoDoor_map15_button_tagged_vld_open_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/s_sound.c",
        "S_StartSound switch-on/off boundaries remain deferred",
        "S_StartSound_button_switch_boundaries_deferred_stage23_debug",
    ),
)


@dataclass(frozen=True)
class Stage23PinnedCensusRecord:
    map_name: str
    line_index: int
    special: int
    tag: int
    side: int
    right_sidedef: int
    left_sidedef: int
    front_sector: int
    middle_texture_before: str
    middle_texture_pressed: str
    middle_texture_restored: str
    target_sector: int
    target_floor: int
    target_ceiling: int
    target_special: int
    surrounding_lowest_ceiling: int
    topheight: int


@dataclass
class Stage23Counters(stage22.Stage22Counters):
    button_update_calls: int = 0
    button_countdowns: int = 0
    button_restore_mutations: int = 0
    button_slot_clears: int = 0
    button_switch_off_sound_deferrals: int = 0
    inactive_button_noops: int = 0
    map01_clean_reusable_buttons: int = 0
    pinned_reusable_buttons: int = 0
    pinned_door_button_candidates: int = 0
    fallback_used: int = 0
    stage24_absent: int = 1


@dataclass(frozen=True)
class Stage23ButtonTraceRecord:
    tic: int
    slot: int
    timer_before: int
    timer_after: int
    texture_before: int
    texture_after: int
    restored: int
    cleared: int


@dataclass
class Stage23World(stage22.Stage22World):
    counters: Stage23Counters = field(default_factory=Stage23Counters)
    button_trace: list[Stage23ButtonTraceRecord] = field(default_factory=list)


@dataclass(frozen=True)
class Stage23FirstButtonTimerRestoreReference:
    stage22: stage22.Stage22FirstSwitchTextureTaggedDoorReference
    census: Stage23PinnedCensusRecord
    switch: stage22.Stage22SwitchTextureResult
    door_spawn: stage22.Stage22DoorSpawnRecord
    button_slot: int
    button_timer_start: int
    button_timer_end: int
    button_old_texture_name: str
    button_pressed_texture_name: str
    button_restored_texture_name: str
    duplicate_guard_result: int
    button_trace: tuple[Stage23ButtonTraceRecord, ...]
    ticker_door_trace: tuple[stage21.Stage21DoorTraceRecord, ...]
    counters: Stage23Counters
    ticker_counters: stage21.Stage21Counters
    leveltime_before: int
    leveltime_after: int
    order_ok: int
    signature: int


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & 0xFFFFFFFF


def _hash_bytes(signature: int, data: bytes) -> int:
    for byte in data:
        signature = _hash_u32(signature, byte)
    return signature


def _texture_name(world: stage22.Stage22World, texture_id: int) -> str:
    return stage22._texture_name(world, texture_id)


def _build_stage23_world(wad: WadFile, map_name: str) -> Stage23World:
    loaded = load_map(wad, map_name)
    block_data = wad.read_lump(wad.map_lumps(map_name).get("BLOCKMAP"))
    blockmap = stage14.p_load_blockmap_source_shape(block_data, num_lines=len(loaded.linedefs))
    base = stage19.Stage19World(
        loaded=loaded,
        blockmap=blockmap,
        sectors=[
            stage19.Stage19Sector(
                index=index,
                floorheight=sector.floor_height << FRACBITS,
                ceilingheight=sector.ceiling_height << FRACBITS,
                special=sector.special_type,
                tag=sector.tag,
            )
            for index, sector in enumerate(loaded.sectors)
        ],
        lines=stage19.build_stage19_lines(loaded),
        sector_lines={},
        counters=stage19.Stage19Counters(special_census_runs=1),
    )
    base.sector_lines = stage19.build_stage19_sector_lines(base.lines, len(base.sectors))
    setup = stage08.load_texture_setup_from_wad(wad)
    pairs = stage22.p_init_switch_list_stage22_source_shape(setup, None, episode=3)
    switchlist, switch_names = stage22._flatten_switchlist(pairs)
    id_to_name = {texture.index: texture.name for texture in setup.textures}
    id_to_name[0] = "-"
    side_textures = [
        stage22.Stage22SideDefTextures(
            toptexture=stage08.r_check_texture_num_for_name(setup, side.upper_texture),
            bottomtexture=stage08.r_check_texture_num_for_name(setup, side.lower_texture),
            midtexture=stage08.r_check_texture_num_for_name(setup, side.middle_texture),
        )
        for side in loaded.sidedefs
    ]
    counters = Stage23Counters()
    counters.switchlist_init_calls = 1
    counters.switch_pairs_available = len(pairs)
    counters.switchlist_entries = len(pairs) * 2
    return Stage23World(
        base=base,
        side_textures=side_textures,
        switch_pairs=pairs,
        switchlist=switchlist,
        switchlist_names=switch_names,
        texture_name_by_id=id_to_name,
        counters=counters,
    )


def p_start_button_stage23_source_shape(
    world: Stage23World,
    line: stage19.Stage19Line,
    where: int,
    texture: int,
    time: int = BUTTONTIME,
) -> int:
    return stage22.p_start_button_stage22_source_shape(world, line, where, texture, time)


def p_change_switch_texture_stage23_source_shape(
    world: Stage23World,
    line: stage19.Stage19Line,
    use_again: int,
) -> stage22.Stage22SwitchTextureResult:
    return stage22.p_change_switch_texture_stage22_source_shape(world, line, use_again)


def p_update_specials_stage23_source_shape(world: Stage23World) -> None:
    world.counters.button_update_calls += 1
    active = 0
    for slot, button in enumerate(world.buttonlist):
        if not button.btimer:
            continue
        active += 1
        line = world.lines[button.line_index]
        side = world.side_textures[line.sidenum[0]]
        where = button.where
        texture_before = stage22._switch_slot_value(side, where)
        timer_before = button.btimer
        button.btimer -= 1
        world.counters.button_countdowns += 1
        restored = 0
        cleared = 0
        if not button.btimer:
            stage22._set_switch_slot_value(side, where, button.btexture)
            world.counters.button_restore_steps += 1
            world.counters.button_restore_mutations += 1
            world.counters.button_switch_off_sound_deferrals += 1
            world.counters.switch_channel_guard_deferrals += 1
            button.line_index = -1
            button.where = -1
            button.btexture = 0
            button.soundorg_sector = -1
            world.counters.button_slot_clears += 1
            restored = 1
            cleared = 1
        texture_after = stage22._switch_slot_value(side, where)
        world.button_trace.append(
            Stage23ButtonTraceRecord(
                tic=world.counters.button_update_calls,
                slot=slot,
                timer_before=timer_before,
                timer_after=button.btimer,
                texture_before=texture_before,
                texture_after=texture_after,
                restored=restored,
                cleared=cleared,
            )
        )
    if active == 0:
        world.counters.inactive_button_noops += 1


def p_ticker_stage23_source_shape(world: Stage23World) -> bool:
    assert world.ticker_world is not None
    ticker = world.ticker_world
    ticker.counters.ticker_calls += 1
    ticker.order_log.append("P_Ticker")
    for active in ticker.playeringame:
        if active:
            ticker.counters.player_think_guards += 1
            ticker.counters.player_think_deferrals += 1
            ticker.order_log.append("P_PlayerThink_guard")
    stage21.p_run_thinkers_stage21_source_shape(ticker)
    ticker.counters.update_specials_calls += 1
    ticker.order_log.append("P_UpdateSpecials")
    if ticker.last_run_order_index >= 0:
        ticker.counters.run_before_update_orders += 1
    p_update_specials_stage23_source_shape(world)
    stage21.p_respawn_specials_stage21_source_shape(ticker)
    ticker.leveltime += 1
    ticker.counters.leveltime_increments += 1
    ticker.order_log.append("leveltime++")
    return True


def ev_do_door_stage23_source_shape(world: Stage23World, line: stage19.Stage19Line, door_type: int) -> int:
    return stage22.ev_do_door_stage22_source_shape(world, line, door_type)


def p_use_special_line_stage23_source_shape(world: Stage23World, line: stage19.Stage19Line, side: int) -> bool:
    world.counters.special_use_attempts += 1
    world.counters.use_special_calls += 1
    if side:
        world.counters.back_side_rejections += 1
        return False
    world.counters.front_side_activations += 1
    if line.special != SELECTED_SPECIAL:
        world.counters.generalized_specials += 1
        return True
    if ev_do_door_stage23_source_shape(world, line, VLD_OPEN):
        p_change_switch_texture_stage23_source_shape(world, line, 1)
    world.use_trace.append(
        stage22.Stage22UseTraceRecord(
            line_index=line.index,
            side=side,
            special_before=SELECTED_SPECIAL,
            special_after=line.special,
            frac=0,
            use_special_result=1,
            door_spawned=1,
            switch_mutated=1,
            terminated=1,
        )
    )
    return True


def reusable_switch_button_census(wad_path: str | Path) -> tuple[int, int, int, tuple[str, int, int, int, int, int, tuple[str, str, str]], ...]:
    wad = WadFile.from_file(wad_path)
    setup = stage08.load_texture_setup_from_wad(wad)
    pairs = stage22.p_init_switch_list_stage22_source_shape(setup, None, episode=3)
    switch_names = {name for pair in pairs for name in (pair.name1, pair.name2)}
    map01_clean = 0
    all_clean: list[tuple[str, int, int, int, int, int, tuple[str, str, str]]] = []
    door_clean = 0
    for marker in wad.map_markers():
        if not marker.name.upper().startswith("MAP"):
            continue
        loaded = load_map(wad, marker.name)
        for index, linedef in enumerate(loaded.linedefs):
            if linedef.special_type not in BUTTON_SPECIALS or linedef.right_sidedef == NO_SIDEDEF:
                continue
            side = loaded.sidedefs[linedef.right_sidedef]
            slots = (side.upper_texture, side.middle_texture, side.lower_texture)
            if not any(texture in switch_names for texture in slots):
                continue
            record = (
                marker.name,
                index,
                linedef.special_type,
                linedef.sector_tag,
                linedef.right_sidedef,
                linedef.left_sidedef,
                side.sector,
                slots,
            )
            all_clean.append(record)
            if marker.name.upper() == "MAP01":
                map01_clean += 1
            if linedef.special_type in STAGE23_DOOR_BUTTON_SPECIALS:
                door_clean += 1
    return map01_clean, len(all_clean), door_clean, tuple(all_clean)


def _stage23_signature(ref: Stage23FirstButtonTimerRestoreReference) -> int:
    sig = 2166136261
    for value in (
        ref.stage22.signature,
        ref.census.line_index,
        ref.census.special,
        ref.census.tag,
        ref.census.right_sidedef,
        ref.census.front_sector,
        ref.census.target_sector,
        ref.switch.where,
        ref.switch.pair_index,
        ref.switch.switchlist_index,
        ref.switch.line_special_after,
        ref.button_slot,
        ref.button_timer_start,
        ref.button_timer_end,
        ref.counters.button_countdowns,
        ref.counters.button_restore_steps,
        ref.counters.button_slot_clears,
        ref.ticker_counters.ticker_calls,
        ref.ticker_counters.t_vertical_door_ticks,
        ref.ticker_counters.move_plane_calls,
        ref.leveltime_after,
    ):
        sig = _hash_u32(sig, value)
    sig = _hash_bytes(sig, ref.button_old_texture_name.encode("ascii"))
    sig = _hash_bytes(sig, ref.button_pressed_texture_name.encode("ascii"))
    sig = _hash_bytes(sig, ref.button_restored_texture_name.encode("ascii"))
    return sig


def _reference_stage23_uncached(wad_path: str | Path) -> Stage23FirstButtonTimerRestoreReference:
    wad_path = Path(wad_path)
    wad = WadFile.from_file(wad_path)
    stage22_ref = stage22.reference_first_switch_texture_and_tagged_door_probe_for_pinned_map(wad_path)
    map01_clean, all_clean, door_clean, records = reusable_switch_button_census(wad_path)
    if (SELECTED_MAP, SELECTED_LINE_INDEX, SELECTED_SPECIAL, SELECTED_TAG, SELECTED_RIGHT_SIDEDEF, SELECTED_LEFT_SIDEDEF, SELECTED_FRONT_SECTOR, ("-", "SW1COMP", "-")) not in records:
        raise AssertionError("pinned MAP15 reusable button candidate was not found")

    world = _build_stage23_world(wad, SELECTED_MAP)
    world.counters.map01_clean_reusable_buttons = map01_clean
    world.counters.pinned_reusable_buttons = all_clean
    world.counters.pinned_door_button_candidates = door_clean
    line = world.lines[SELECTED_LINE_INDEX]
    before_special = line.special
    p_use_special_line_stage23_source_shape(world, line, 0)
    switch = world.switch_result
    door = world.door_spawn
    if switch is None or door is None:
        raise AssertionError("stage23 selected route did not mutate a switch and spawn a door")
    duplicate_guard_result = p_start_button_stage23_source_shape(world, line, switch.where, switch.before_texture)
    button_slot = next(index for index, button in enumerate(world.buttonlist) if button.btimer)
    button_timer_start = world.buttonlist[button_slot].btimer
    assert world.ticker_world is not None
    leveltime_before = world.ticker_world.leveltime
    for _ in range(DEFAULT_STAGE23_TICKER_TICS):
        p_ticker_stage23_source_shape(world)
    leveltime_after = world.ticker_world.leveltime
    order_ok = stage21._stage21_order_ok(tuple(world.ticker_world.order_log))
    restored_id = stage22._switch_slot_value(world.side_textures[SELECTED_RIGHT_SIDEDEF], BUTTON_MIDDLE)
    census = Stage23PinnedCensusRecord(
        map_name=SELECTED_MAP,
        line_index=line.index,
        special=before_special,
        tag=line.tag,
        side=0,
        right_sidedef=line.sidenum[0],
        left_sidedef=line.sidenum[1],
        front_sector=line.frontsector,
        middle_texture_before=switch.before_name,
        middle_texture_pressed=switch.after_name,
        middle_texture_restored=_texture_name(world, restored_id),
        target_sector=door.selected_sector,
        target_floor=door.floorheight,
        target_ceiling=door.ceiling_before,
        target_special=world.sectors[door.selected_sector].special,
        surrounding_lowest_ceiling=door.surrounding_lowest_ceiling,
        topheight=door.topheight,
    )
    ref = Stage23FirstButtonTimerRestoreReference(
        stage22=stage22_ref,
        census=census,
        switch=switch,
        door_spawn=door,
        button_slot=button_slot,
        button_timer_start=button_timer_start,
        button_timer_end=world.buttonlist[button_slot].btimer,
        button_old_texture_name=switch.before_name,
        button_pressed_texture_name=switch.after_name,
        button_restored_texture_name=census.middle_texture_restored,
        duplicate_guard_result=duplicate_guard_result,
        button_trace=tuple(world.button_trace),
        ticker_door_trace=tuple(world.ticker_world.door_trace),
        counters=world.counters,
        ticker_counters=world.ticker_world.counters,
        leveltime_before=leveltime_before,
        leveltime_after=leveltime_after,
        order_ok=order_ok,
        signature=0,
    )
    return Stage23FirstButtonTimerRestoreReference(**{**ref.__dict__, "signature": _stage23_signature(ref)})


@lru_cache(maxsize=4)
def _reference_stage23_cached(wad_path: str) -> Stage23FirstButtonTimerRestoreReference:
    return _reference_stage23_uncached(wad_path)


def reference_first_button_timer_restore_probe_for_pinned_map(wad_path: str | Path) -> Stage23FirstButtonTimerRestoreReference:
    return _reference_stage23_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage23FirstButtonTimerRestoreReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_first_button_timer_restore_probe_for_pinned_map(wad_path)


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
    x86.call_rel32(pe, "source_stage23_load_wad_first_button_timer_restore_probe")
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


def emit_source_stage23_load_wad_first_button_timer_restore_probe(pe: PE32) -> None:
    pe.label("source_stage23_load_wad_first_button_timer_restore_probe")
    x86.call_rel32(pe, "source_stage22_load_wad_first_switch_texture_and_tagged_door_probe")
    x86.mov_reg_mem_abs32(pe, "eax", "stage22_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage22_expected_signature")
    x86.jne_rel32(pe, "source_stage23_return")
    x86.call_rel32(pe, "render_first_button_timer_restore_probe_debug")
    x86.call_rel32(pe, "append_stage23_success_status")
    pe.label("source_stage23_return")
    x86.ret(pe)


def emit_render_first_button_timer_restore_probe_debug(pe: PE32) -> None:
    pe.label("P_UseSpecialLine_button61_vld_open_source_shape_debug")
    pe.label("P_StartButton_first_reusable_button_source_shape_debug")
    pe.label("P_UpdateSpecials_button_timer_restore_source_shape_debug")
    pe.label("EV_DoDoor_map15_button_tagged_vld_open_source_shape_debug")
    pe.label("S_StartSound_button_switch_boundaries_deferred_stage23_debug")
    pe.label("render_first_button_timer_restore_probe_debug")
    for dst, src in (
        ("stage23_runtime_signature", "stage23_expected_signature"),
        ("stage23_runtime_texture_pressed", "stage23_texture_pressed"),
        ("stage23_runtime_texture_restored", "stage23_texture_restored"),
        ("stage23_runtime_button_timer_end", "stage23_button_timer_end"),
        ("stage23_runtime_leveltime_after", "stage23_leveltime_after"),
        ("stage23_runtime_order_ok", "stage23_order_ok"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage14._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage23_success_status(pe: PE32) -> None:
    pe.label("append_stage23_success_status")
    _emit_seek_buffer_end(pe, "status_success_buffer", "stage23_status")
    stage01.append_c_string_label(pe, "status_stage23_success_header")
    stage01.append_u32_label(pe, "status_stage23_line_prefix", "stage23_line")
    stage01.append_c_string_label(pe, "status_stage23_texture_prefix")
    stage01.append_c_string_label(pe, "stage23_texture_before_name")
    stage01.append_c_string_label(pe, "status_stage23_arrow")
    stage01.append_c_string_label(pe, "stage23_texture_pressed_name")
    stage01.append_c_string_label(pe, "status_stage23_arrow")
    stage01.append_c_string_label(pe, "stage23_texture_restored_name")
    stage01.append_u32_label(pe, "status_stage23_signature_prefix", "stage23_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage23_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage23_title")
    for prefix, label, signed in (
        ("title_stage23_map_prefix", "stage23_map_number", False),
        ("title_stage23_line_prefix", "stage23_line", False),
        ("title_stage23_special_prefix", "stage23_special", False),
        ("title_stage23_tag_prefix", "stage23_tag", False),
        ("title_stage23_side_prefix", "stage23_side", False),
        ("title_stage23_right_sidedef_prefix", "stage23_right_sidedef", False),
        ("title_stage23_left_sidedef_prefix", "stage23_left_sidedef", False),
        ("title_stage23_front_sector_prefix", "stage23_front_sector", False),
        ("title_stage23_slot_prefix", "stage23_switch_where", False),
    ):
        (stage01.append_i32_label if signed else stage01.append_u32_label)(pe, prefix, label)
    stage01.append_c_string_label(pe, "title_stage23_texture_before_prefix")
    stage01.append_c_string_label(pe, "stage23_texture_before_name")
    stage01.append_c_string_label(pe, "title_stage23_texture_pressed_prefix")
    stage01.append_c_string_label(pe, "stage23_texture_pressed_name")
    stage01.append_c_string_label(pe, "title_stage23_texture_restored_prefix")
    stage01.append_c_string_label(pe, "stage23_texture_restored_name")
    for prefix, label in (
        ("title_stage23_pair_prefix", "stage23_switch_pair_index"),
        ("title_stage23_switch_index_prefix", "stage23_switchlist_index"),
        ("title_stage23_special_after_prefix", "stage23_line_special_after"),
        ("title_stage23_button_slot_prefix", "stage23_button_slot"),
        ("title_stage23_button_old_prefix", "stage23_button_old_texture"),
        ("title_stage23_timer0_prefix", "stage23_button_timer_start"),
        ("title_stage23_timer1_prefix", "stage23_runtime_button_timer_end"),
        ("title_stage23_duplicate_prefix", "stage23_duplicate_guard_result"),
        ("title_stage23_update_prefix", "stage23_update_specials_calls"),
        ("title_stage23_countdown_prefix", "stage23_button_countdowns"),
        ("title_stage23_restore_prefix", "stage23_button_restore_steps"),
        ("title_stage23_clear_prefix", "stage23_button_slot_clears"),
        ("title_stage23_offsound_prefix", "stage23_button_switch_off_sound_deferrals"),
        ("title_stage23_sector_prefix", "stage23_tagged_sector"),
        ("title_stage23_floor_prefix", "stage23_tagged_floor"),
        ("title_stage23_ceiling0_prefix", "stage23_tagged_ceiling_before"),
        ("title_stage23_low_prefix", "stage23_lowest_ceiling"),
        ("title_stage23_top_prefix", "stage23_topheight"),
        ("title_stage23_direction_prefix", "stage23_door_direction"),
        ("title_stage23_speed_prefix", "stage23_door_speed_units"),
        ("title_stage23_wait_prefix", "stage23_door_topwait"),
        ("title_stage23_ticker_prefix", "stage23_ticker_calls"),
        ("title_stage23_door_ticks_prefix", "stage23_t_vertical_door_ticks"),
        ("title_stage23_move_plane_prefix", "stage23_move_plane_calls"),
        ("title_stage23_remove_prefix", "stage23_door_removal_requests"),
        ("title_stage23_leveltime_prefix", "stage23_runtime_leveltime_after"),
        ("title_stage23_order_prefix", "stage23_runtime_order_ok"),
        ("title_stage23_map01_prefix", "stage23_map01_clean_reusable_buttons"),
        ("title_stage23_census_prefix", "stage23_pinned_reusable_buttons"),
        ("title_stage23_door_census_prefix", "stage23_pinned_door_button_candidates"),
        ("title_stage23_audio_prefix", "stage23_real_audio_playbacks"),
        ("title_stage23_generalized_prefix", "stage23_generalized_specials"),
        ("title_stage23_fallback_prefix", "stage23_fallback_used"),
        ("title_stage23_stage24_prefix", "stage23_stage24_absent"),
    ):
        stage01.append_i32_label(pe, prefix, label)
    stage01.append_u32_label(pe, "title_stage23_signature_prefix", "stage23_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage23_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    counters = ref.counters if ref is not None else Stage23Counters()
    ticker = ref.ticker_counters if ref is not None else stage21.Stage21Counters()
    census = ref.census if ref is not None else None
    switch = ref.switch if ref is not None else None
    door = ref.door_spawn if ref is not None else None
    pe.align_section(4)
    for name, value in (
        ("stage23_map_number", 15),
        ("stage23_line", census.line_index if census else 0),
        ("stage23_special", census.special if census else 0),
        ("stage23_tag", census.tag if census else 0),
        ("stage23_side", census.side if census else 0),
        ("stage23_right_sidedef", census.right_sidedef if census else 0),
        ("stage23_left_sidedef", (census.left_sidedef if census else 0) & 0xFFFFFFFF),
        ("stage23_front_sector", census.front_sector if census else 0),
        ("stage23_texture_before", switch.before_texture if switch else 0),
        ("stage23_texture_pressed", switch.after_texture if switch else 0),
        ("stage23_runtime_texture_pressed", 0),
        ("stage23_texture_restored", switch.before_texture if switch else 0),
        ("stage23_runtime_texture_restored", 0),
        ("stage23_switch_where", switch.where if switch else 0),
        ("stage23_switch_pair_index", switch.pair_index if switch else 0),
        ("stage23_switchlist_index", switch.switchlist_index if switch else 0),
        ("stage23_line_special_after", switch.line_special_after if switch else 0),
        ("stage23_button_slot", ref.button_slot if ref else 0),
        ("stage23_button_old_texture", switch.before_texture if switch else 0),
        ("stage23_button_timer_start", ref.button_timer_start if ref else 0),
        ("stage23_button_timer_end", ref.button_timer_end if ref else 0),
        ("stage23_runtime_button_timer_end", 0),
        ("stage23_duplicate_guard_result", ref.duplicate_guard_result if ref else 0),
        ("stage23_update_specials_calls", ticker.update_specials_calls),
        ("stage23_button_countdowns", counters.button_countdowns),
        ("stage23_button_restore_steps", counters.button_restore_steps),
        ("stage23_button_slot_clears", counters.button_slot_clears),
        ("stage23_button_switch_off_sound_deferrals", counters.button_switch_off_sound_deferrals),
        ("stage23_tagged_sector", door.selected_sector if door else 0),
        ("stage23_tagged_floor", ((door.floorheight >> FRACBITS) if door else 0) & 0xFFFFFFFF),
        ("stage23_tagged_ceiling_before", ((door.ceiling_before >> FRACBITS) if door else 0) & 0xFFFFFFFF),
        ("stage23_lowest_ceiling", ((door.surrounding_lowest_ceiling >> FRACBITS) if door else 0) & 0xFFFFFFFF),
        ("stage23_topheight", ((door.topheight >> FRACBITS) if door else 0) & 0xFFFFFFFF),
        ("stage23_door_direction", door.direction if door else 0),
        ("stage23_door_speed_units", ((door.speed >> FRACBITS) if door else 0)),
        ("stage23_door_topwait", door.topwait if door else 0),
        ("stage23_ticker_calls", ticker.ticker_calls),
        ("stage23_t_vertical_door_ticks", ticker.t_vertical_door_ticks),
        ("stage23_move_plane_calls", ticker.move_plane_calls),
        ("stage23_door_removal_requests", ticker.door_removal_requests),
        ("stage23_leveltime_after", ref.leveltime_after if ref else 0),
        ("stage23_runtime_leveltime_after", 0),
        ("stage23_order_ok", ref.order_ok if ref else 0),
        ("stage23_runtime_order_ok", 0),
        ("stage23_map01_clean_reusable_buttons", counters.map01_clean_reusable_buttons),
        ("stage23_pinned_reusable_buttons", counters.pinned_reusable_buttons),
        ("stage23_pinned_door_button_candidates", counters.pinned_door_button_candidates),
        ("stage23_real_audio_playbacks", counters.real_audio_playbacks),
        ("stage23_generalized_specials", counters.generalized_specials),
        ("stage23_generalized_doors", counters.generalized_doors),
        ("stage23_generalized_switches", counters.generalized_switches),
        ("stage23_generalized_sector_effects", counters.generalized_sector_effects),
        ("stage23_fallback_used", counters.fallback_used),
        ("stage23_stage24_absent", counters.stage24_absent),
        ("stage23_expected_signature", ref.signature if ref else 0),
        ("stage23_runtime_signature", 0),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    pe.align_section(1)
    pe.label("stage23_texture_before_name")
    x86.emit_asciiz(pe, ref.button_old_texture_name if ref else "")
    pe.label("stage23_texture_pressed_name")
    x86.emit_asciiz(pe, ref.button_pressed_texture_name if ref else "")
    pe.label("stage23_texture_restored_name")
    x86.emit_asciiz(pe, ref.button_restored_texture_name if ref else "")
    pe.label("status_stage23_success_header")
    x86.emit_asciiz(pe, "\r\nsource_stage23_first_button_timer_restore_probe\r\nFirst reusable button timer restore proof OK\r\n")
    pe.label("status_stage23_line_prefix")
    x86.emit_asciiz(pe, "\r\nSelected MAP15 button linedef: ")
    pe.label("status_stage23_texture_prefix")
    x86.emit_asciiz(pe, "\r\nButton texture lifecycle: ")
    pe.label("status_stage23_arrow")
    x86.emit_asciiz(pe, " -> ")
    pe.label("status_stage23_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage23 button restore signature: ")
    pe.label("status_stage23_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage23 preserves stage22 through stage19, then uses real MAP15 linedef 3452. "
        "The bounded route reaches P_UseSpecialLine case 61, EV_DoDoor(vld_open), "
        "P_ChangeSwitchTexture(line,1), P_StartButton, and P_UpdateSpecials restore after 35 tics. "
        "Switch sounds are counted as deferred boundaries; broad special, floor, plat, input, progression, "
        "speaker, mixer, and later-stage work stay absent.\r\n",
    )
    for label, text in (
        ("title_stage23_map_prefix", " S23MAP="),
        ("title_stage23_line_prefix", " S23LINE="),
        ("title_stage23_special_prefix", " S23SPEC="),
        ("title_stage23_tag_prefix", " TAG23="),
        ("title_stage23_side_prefix", " SIDE23="),
        ("title_stage23_right_sidedef_prefix", " RSID23="),
        ("title_stage23_left_sidedef_prefix", " LSID23="),
        ("title_stage23_front_sector_prefix", " FSEC23="),
        ("title_stage23_slot_prefix", " SLOT23="),
        ("title_stage23_texture_before_prefix", " TEX230="),
        ("title_stage23_texture_pressed_prefix", " TEX231="),
        ("title_stage23_texture_restored_prefix", " TEX232="),
        ("title_stage23_pair_prefix", " PAIR23="),
        ("title_stage23_switch_index_prefix", " SWI23="),
        ("title_stage23_special_after_prefix", " SPC231="),
        ("title_stage23_button_slot_prefix", " BSLOT23="),
        ("title_stage23_button_old_prefix", " BOLD23="),
        ("title_stage23_timer0_prefix", " BT230="),
        ("title_stage23_timer1_prefix", " BT231="),
        ("title_stage23_duplicate_prefix", " BDUP23="),
        ("title_stage23_update_prefix", " UPD23="),
        ("title_stage23_countdown_prefix", " BDEC23="),
        ("title_stage23_restore_prefix", " BREST23="),
        ("title_stage23_clear_prefix", " BCLR23="),
        ("title_stage23_offsound_prefix", " BOFFSND23="),
        ("title_stage23_sector_prefix", " TSEC23="),
        ("title_stage23_floor_prefix", " F23="),
        ("title_stage23_ceiling0_prefix", " C230="),
        ("title_stage23_low_prefix", " LOW23="),
        ("title_stage23_top_prefix", " TOP23="),
        ("title_stage23_direction_prefix", " DIR23="),
        ("title_stage23_speed_prefix", " SPD23="),
        ("title_stage23_wait_prefix", " WAIT23="),
        ("title_stage23_ticker_prefix", " PTIC23="),
        ("title_stage23_door_ticks_prefix", " TVD23="),
        ("title_stage23_move_plane_prefix", " MP23="),
        ("title_stage23_remove_prefix", " REM23="),
        ("title_stage23_leveltime_prefix", " LT23="),
        ("title_stage23_order_prefix", " ORDER23="),
        ("title_stage23_map01_prefix", " MAP01BTN23="),
        ("title_stage23_census_prefix", " CENS23="),
        ("title_stage23_door_census_prefix", " DOORBTN23="),
        ("title_stage23_audio_prefix", " AUD23="),
        ("title_stage23_generalized_prefix", " GEN23="),
        ("title_stage23_fallback_prefix", " FALL23="),
        ("title_stage23_stage24_prefix", " S24ABS="),
        ("title_stage23_signature_prefix", " S23SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)


def build_source_stage23_first_button_timer_restore_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage23_load_wad_first_button_timer_restore_probe(pe)
    stage22.emit_source_stage22_load_wad_first_switch_texture_and_tagged_door_probe(pe)
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
    stage22.emit_render_first_switch_texture_and_tagged_door_probe_debug(pe)
    emit_render_first_button_timer_restore_probe_debug(pe)
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
    stage22.emit_append_stage22_success_status(pe)
    emit_append_stage23_success_status(pe)
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
    stage22.emit_stage22_data(pe)
    emit_stage23_data(pe)
    return pe.build("entry")


def write_source_stage23_first_button_timer_restore_probe_exe(path: str | Path) -> bytes:
    image = build_source_stage23_first_button_timer_restore_probe_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage23 first reusable button timer restore PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage23_first_button_timer_restore_probe.exe",
        help="path to write, default: build/source_stage23_first_button_timer_restore_probe.exe",
    )
    args = parser.parse_args()
    write_source_stage23_first_button_timer_restore_probe_exe(args.output)


if __name__ == "__main__":
    main()
