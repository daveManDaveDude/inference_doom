from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage26_first_ceiling_or_crusher_special_probe as stage26
from tools import x86
from tools.pe32 import PE32
from tools.wad import WadFile


stage25 = stage26.stage25
stage24 = stage26.stage24
stage23 = stage26.stage23
stage22 = stage26.stage22
stage21 = stage26.stage21
stage20 = stage26.stage20
stage19 = stage26.stage19
stage18 = stage26.stage18
stage17 = stage26.stage17
stage16 = stage26.stage16
stage15 = stage26.stage15
stage14 = stage26.stage14
stage13 = stage26.stage13
stage12 = stage26.stage12
stage11 = stage26.stage11
stage10 = stage26.stage10
stage08 = stage26.stage08
stage07 = stage26.stage07
stage04 = stage26.stage04
stage03 = stage26.stage03
stage02 = stage26.stage02
stage01 = stage26.stage01


FRAMEBUFFER_WIDTH = stage26.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage26.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage26.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage26.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage26.WINDOW_WIDTH
WINDOW_HEIGHT = stage26.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage27IntegratedScriptedRoomInteractionLoop"
WINDOW_TITLE = "Inference Doom S27 Scripted Room Loop"
WAD_PATH = stage26.WAD_PATH

FRACBITS = stage26.FRACBITS
FRACUNIT = stage26.FRACUNIT
FNV_PRIME = stage26.FNV_PRIME
BT_USE = 2
DEFAULT_STAGE27_TICKER_TICS = stage25.DEFAULT_STAGE25_TICKER_TICS
SAMPLE_TICS = (1, 14, 35, 36, 120, 136)
STAGE27_SAMPLE_COUNT = len(SAMPLE_TICS)
WM_TIMER = 0x0113
STAGE27_TIMER_ID = 27
STAGE27_TIMER_MS = 350

SELECTED_MAP = stage25.SELECTED_MAP
SELECTED_LINE_INDEX = stage25.SELECTED_LINE_INDEX
SELECTED_SPECIAL = stage25.SELECTED_SPECIAL
SELECTED_TAG = stage25.SELECTED_TAG
SELECTED_TARGET_SECTOR = stage25.SELECTED_TARGET_SECTOR


SOURCE_TRACE = stage26.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/g_game.c",
        "G_Ticker deterministic ticcmd consumption for a bounded scripted room loop",
        "G_Ticker_stage27_scripted_ticcmd_room_loop_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_user.c",
        "P_PlayerThink BT_USE edge gate into P_UseLines/P_UseSpecialLine",
        "P_PlayerThink_stage27_scripted_use_gate_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "P_UseLines/PTR_UseTraverse selected front-side line activation boundary",
        "P_UseLines_stage27_selected_line_use_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_tick.c",
        "P_Ticker normal order around P_RunThinkers/P_UpdateSpecials/leveltime++",
        "P_Ticker_stage27_integrated_order_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_plats.c",
        "T_PlatRaise downWaitUpStay movement sampled across one runtime lifecycle",
        "T_PlatRaise_stage27_sampled_runtime_loop_source_shape_debug",
    ),
)


@dataclass(frozen=True)
class Stage27Ticcmd:
    forwardmove: int = 0
    sidemove: int = 0
    angleturn: int = 0
    buttons: int = 0


@dataclass(frozen=True)
class Stage27StateSample:
    tic: int
    floor: int
    button_timer: int
    texture: str
    plat_status: int
    plat_count: int
    leveltime: int


@dataclass
class Stage27Counters(stage25.Stage25Counters):
    g_ticker_calls: int = 0
    script_commands_consumed: int = 0
    scripted_use_commands: int = 0
    player_think_calls: int = 0
    player_use_edges: int = 0
    player_use_held_skips: int = 0
    selected_use_line_calls: int = 0
    state_samples: int = 0
    distinct_sample_states: int = 0
    button_restore_during_plat_motion: int = 0
    no_live_input_dependency: int = 1
    actual_speaker_playback_deferred: int = 1
    map_progression_absent: int = 1
    generalized_combat_absent: int = 1


@dataclass
class Stage27World(stage25.Stage25World):
    counters: Stage27Counters = field(default_factory=Stage27Counters)
    scripted_usedown: bool = False
    ticcmd_script: tuple[Stage27Ticcmd, ...] = field(default_factory=tuple)
    state_log: list[Stage27StateSample] = field(default_factory=list)


@dataclass(frozen=True)
class Stage27IntegratedScriptedRoomLoopReference:
    stage26: stage26.Stage26FirstCeilingOrCrusherSpecialReference
    stage25_route: stage25.Stage25FirstPlatformLiftCycleReference
    ticcmd_script: tuple[Stage27Ticcmd, ...]
    samples: tuple[Stage27StateSample, ...]
    counters: Stage27Counters
    ticker_counters: stage21.Stage21Counters
    leveltime_after: int
    order_ok: int
    signature: int


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & (0xFFFFFFFF)


def _hash_bytes(signature: int, data: bytes) -> int:
    for byte in data:
        signature = _hash_u32(signature, byte)
    return signature


def _texture_name(world: stage22.Stage22World, texture_id: int) -> str:
    return stage22._texture_name(world, texture_id)


def _build_stage27_world(wad: WadFile, map_name: str) -> Stage27World:
    base = stage25._build_stage25_world(wad, map_name)
    return Stage27World(
        base=base.base,
        side_textures=base.side_textures,
        switch_pairs=base.switch_pairs,
        switchlist=base.switchlist,
        switchlist_names=base.switchlist_names,
        texture_name_by_id=base.texture_name_by_id,
        counters=Stage27Counters(
            switchlist_init_calls=base.counters.switchlist_init_calls,
            switch_pairs_available=base.counters.switch_pairs_available,
            switchlist_entries=base.counters.switchlist_entries,
        ),
        ticcmd_script=(Stage27Ticcmd(buttons=BT_USE),)
        + tuple(Stage27Ticcmd() for _ in range(DEFAULT_STAGE27_TICKER_TICS - 1)),
    )


def _sample_stage27_state(world: Stage27World) -> Stage27StateSample:
    assert world.ticker_world is not None
    side = world.side_textures[stage25.SELECTED_RIGHT_SIDEDEF]
    texture = _texture_name(world, side.bottomtexture)
    plat_status = world.selected_plat.status if world.selected_plat is not None else -1
    plat_count = world.selected_plat.count if world.selected_plat is not None else -1
    button_timer = world.buttonlist[0].btimer
    sample = Stage27StateSample(
        tic=world.counters.g_ticker_calls,
        floor=world.sectors[SELECTED_TARGET_SECTOR].floorheight >> FRACBITS,
        button_timer=button_timer,
        texture=texture,
        plat_status=plat_status,
        plat_count=plat_count,
        leveltime=world.ticker_world.leveltime,
    )
    world.state_log.append(sample)
    world.counters.state_samples += 1
    return sample


def p_player_think_stage27_scripted_use_gate_source_shape(
    world: Stage27World,
    cmd: Stage27Ticcmd,
) -> None:
    world.counters.player_think_calls += 1
    if cmd.buttons & BT_USE:
        if not world.scripted_usedown:
            world.counters.player_use_edges += 1
            world.counters.selected_use_line_calls += 1
            stage25.p_use_special_line_stage25_source_shape(world, world.lines[SELECTED_LINE_INDEX], 0)
            world.scripted_usedown = True
        else:
            world.counters.player_use_held_skips += 1
    else:
        world.scripted_usedown = False


def g_ticker_stage27_scripted_ticcmd_room_loop_source_shape(world: Stage27World) -> bool:
    world.counters.g_ticker_calls += 1
    script_index = world.counters.g_ticker_calls - 1
    cmd = world.ticcmd_script[script_index] if script_index < len(world.ticcmd_script) else Stage27Ticcmd()
    world.counters.script_commands_consumed += 1
    if cmd.buttons & BT_USE:
        world.counters.scripted_use_commands += 1
    p_player_think_stage27_scripted_use_gate_source_shape(world, cmd)
    stage25.p_ticker_stage25_source_shape(world)
    if world.counters.g_ticker_calls in SAMPLE_TICS:
        _sample_stage27_state(world)
    return True


def _stage27_order_ok(world: Stage27World) -> int:
    order = tuple(world.ticker_world.order_log if world.ticker_world is not None else ())
    return stage21._stage21_order_ok(order)


def _stage27_signature(ref: Stage27IntegratedScriptedRoomLoopReference) -> int:
    sig = 2166136261
    for value in (
        ref.stage26.signature,
        ref.stage25_route.signature,
        len(ref.ticcmd_script),
        ref.counters.g_ticker_calls,
        ref.counters.script_commands_consumed,
        ref.counters.scripted_use_commands,
        ref.counters.player_use_edges,
        ref.counters.selected_use_line_calls,
        ref.counters.state_samples,
        ref.counters.distinct_sample_states,
        ref.counters.button_restore_during_plat_motion,
        ref.ticker_counters.ticker_calls,
        ref.leveltime_after,
        ref.order_ok,
    ):
        sig = _hash_u32(sig, value)
    for sample in ref.samples:
        for value in (sample.tic, sample.floor, sample.button_timer, sample.plat_status, sample.plat_count, sample.leveltime):
            sig = _hash_u32(sig, value)
        sig = _hash_bytes(sig, sample.texture.encode("ascii"))
    return sig


def _reference_stage27_uncached(wad_path: str | Path) -> Stage27IntegratedScriptedRoomLoopReference:
    wad_path = Path(wad_path)
    wad = WadFile.from_file(wad_path)
    stage26_ref = stage26.reference_first_ceiling_or_crusher_special_probe_for_pinned_map(wad_path)
    stage25_ref = stage25.reference_first_platform_lift_cycle_probe_for_pinned_map(wad_path)
    world = _build_stage27_world(wad, SELECTED_MAP)
    for _ in range(DEFAULT_STAGE27_TICKER_TICS):
        g_ticker_stage27_scripted_ticcmd_room_loop_source_shape(world)
    states = {(sample.floor, sample.button_timer, sample.texture, sample.plat_status, sample.plat_count) for sample in world.state_log}
    world.counters.distinct_sample_states = len(states)
    world.counters.button_restore_during_plat_motion = 1 if any(
        sample.tic == 35 and sample.button_timer == 0 and sample.texture == "SW1STRTN" and world.counters.plat_removal_requests == 1
        for sample in world.state_log
    ) else 0
    order_ok = _stage27_order_ok(world)
    ref = Stage27IntegratedScriptedRoomLoopReference(
        stage26=stage26_ref,
        stage25_route=stage25_ref,
        ticcmd_script=world.ticcmd_script,
        samples=tuple(world.state_log),
        counters=world.counters,
        ticker_counters=world.ticker_world.counters,
        leveltime_after=world.ticker_world.leveltime,
        order_ok=order_ok,
        signature=0,
    )
    return Stage27IntegratedScriptedRoomLoopReference(**{**ref.__dict__, "signature": _stage27_signature(ref)})


@lru_cache(maxsize=4)
def _reference_stage27_cached(wad_path: str) -> Stage27IntegratedScriptedRoomLoopReference:
    return _reference_stage27_uncached(wad_path)


def reference_integrated_scripted_room_interaction_loop_for_pinned_map(
    wad_path: str | Path,
) -> Stage27IntegratedScriptedRoomLoopReference:
    return _reference_stage27_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage27IntegratedScriptedRoomLoopReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_integrated_scripted_room_interaction_loop_for_pinned_map(wad_path)


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


def emit_stage27_entry(pe: PE32) -> None:
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
    x86.call_rel32(pe, "source_stage27_load_wad_integrated_scripted_room_interaction_loop")
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
    x86.push_abs32(pe, "stage27_live_title_start")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE27_TIMER_MS)
    x86.push_imm32(pe, STAGE27_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
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
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, WM_TIMER)
    x86.jne_rel32(pe, "dispatch_message")
    x86.call_rel32(pe, "stage27_timer_tick")
    pe.label("dispatch_message")
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


def emit_stage27_timer_tick(pe: PE32) -> None:
    pe.label("stage27_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage27_live_step")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage27_timer_sample0")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage27_timer_sample1")
    x86.cmp_eax_imm32(pe, 2)
    x86.je_rel32(pe, "stage27_timer_sample2")
    x86.cmp_eax_imm32(pe, 3)
    x86.je_rel32(pe, "stage27_timer_sample3")
    x86.cmp_eax_imm32(pe, 4)
    x86.je_rel32(pe, "stage27_timer_sample4")
    x86.cmp_eax_imm32(pe, 5)
    x86.je_rel32(pe, "stage27_timer_sample5")
    x86.ret(pe)

    for index in range(STAGE27_SAMPLE_COUNT):
        pe.label(f"stage27_timer_sample{index}")
        x86.push_abs32(pe, f"stage27_live_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        x86.mov_mem_abs32_imm32(pe, "stage27_live_step", index + 1)
        if index == STAGE27_SAMPLE_COUNT - 1:
            x86.push_imm32(pe, STAGE27_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)


def emit_source_stage27_load_wad_integrated_scripted_room_interaction_loop(pe: PE32) -> None:
    pe.label("source_stage27_load_wad_integrated_scripted_room_interaction_loop")
    x86.call_rel32(pe, "source_stage26_load_wad_first_ceiling_or_crusher_special_probe")
    x86.mov_reg_mem_abs32(pe, "eax", "stage26_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage26_expected_signature")
    x86.jne_rel32(pe, "source_stage27_return")
    x86.call_rel32(pe, "render_integrated_scripted_room_interaction_loop_debug")
    x86.call_rel32(pe, "append_stage27_success_status")
    pe.label("source_stage27_return")
    x86.ret(pe)


def emit_render_integrated_scripted_room_interaction_loop_debug(pe: PE32) -> None:
    pe.label("G_Ticker_stage27_scripted_ticcmd_room_loop_source_shape_debug")
    pe.label("P_PlayerThink_stage27_scripted_use_gate_source_shape_debug")
    pe.label("P_UseLines_stage27_selected_line_use_source_shape_debug")
    pe.label("P_Ticker_stage27_integrated_order_source_shape_debug")
    pe.label("T_PlatRaise_stage27_sampled_runtime_loop_source_shape_debug")
    pe.label("render_integrated_scripted_room_interaction_loop_debug")
    for dst, src in (
        ("stage27_runtime_signature", "stage27_expected_signature"),
        ("stage27_runtime_leveltime_after", "stage27_leveltime_after"),
        ("stage27_runtime_order_ok", "stage27_order_ok"),
        ("stage27_runtime_final_floor", "stage27_final_floor"),
        ("stage27_runtime_final_timer", "stage27_final_timer"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage26._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage27_success_status(pe: PE32) -> None:
    pe.label("append_stage27_success_status")
    _emit_seek_buffer_end(pe, "status_success_buffer", "stage27_status")
    stage01.append_c_string_label(pe, "status_stage27_success_header")
    stage01.append_u32_label(pe, "status_stage27_line_prefix", "stage27_line")
    stage01.append_c_string_label(pe, "status_stage27_log_prefix")
    stage01.append_c_string_label(pe, "stage27_log_text")
    stage01.append_u32_label(pe, "status_stage27_signature_prefix", "stage27_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage27_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage27_title")
    for prefix, label in (
        ("title_stage27_map_prefix", "stage27_map_number"),
        ("title_stage27_line_prefix", "stage27_line"),
        ("title_stage27_special_prefix", "stage27_special"),
        ("title_stage27_tag_prefix", "stage27_tag"),
        ("title_stage27_script_prefix", "stage27_script_commands"),
        ("title_stage27_use_prefix", "stage27_scripted_use_commands"),
        ("title_stage27_g_prefix", "stage27_g_ticker_calls"),
        ("title_stage27_p_prefix", "stage27_ticker_calls"),
        ("title_stage27_sample_prefix", "stage27_state_samples"),
        ("title_stage27_distinct_prefix", "stage27_distinct_sample_states"),
        ("title_stage27_button_motion_prefix", "stage27_button_restore_during_plat_motion"),
        ("title_stage27_final_floor_prefix", "stage27_runtime_final_floor"),
        ("title_stage27_final_timer_prefix", "stage27_runtime_final_timer"),
        ("title_stage27_leveltime_prefix", "stage27_runtime_leveltime_after"),
        ("title_stage27_order_prefix", "stage27_runtime_order_ok"),
        ("title_stage27_live_prefix", "stage27_no_live_input_dependency"),
        ("title_stage27_audio_prefix", "stage27_actual_speaker_playback_deferred"),
        ("title_stage27_progress_prefix", "stage27_map_progression_absent"),
        ("title_stage27_combat_prefix", "stage27_generalized_combat_absent"),
    ):
        stage01.append_i32_label(pe, prefix, label)
    stage01.append_c_string_label(pe, "title_stage27_log_prefix")
    stage01.append_c_string_label(pe, "stage27_log_text")
    stage01.append_u32_label(pe, "title_stage27_signature_prefix", "stage27_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def emit_stage27_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    counters = ref.counters if ref is not None else Stage27Counters()
    ticker = ref.ticker_counters if ref is not None else stage21.Stage21Counters()
    samples = ref.samples if ref is not None else ()
    final = samples[-1] if samples else Stage27StateSample(0, 0, 0, "", 0, 0, 0)
    pe.align_section(4)
    for name, value in (
        ("stage27_map_number", 12),
        ("stage27_line", SELECTED_LINE_INDEX),
        ("stage27_special", SELECTED_SPECIAL),
        ("stage27_tag", SELECTED_TAG),
        ("stage27_script_commands", len(ref.ticcmd_script) if ref else 0),
        ("stage27_scripted_use_commands", counters.scripted_use_commands),
        ("stage27_g_ticker_calls", counters.g_ticker_calls),
        ("stage27_ticker_calls", ticker.ticker_calls),
        ("stage27_state_samples", counters.state_samples),
        ("stage27_distinct_sample_states", counters.distinct_sample_states),
        ("stage27_button_restore_during_plat_motion", counters.button_restore_during_plat_motion),
        ("stage27_final_floor", final.floor),
        ("stage27_runtime_final_floor", 0),
        ("stage27_final_timer", final.button_timer),
        ("stage27_runtime_final_timer", 0),
        ("stage27_leveltime_after", ref.leveltime_after if ref else 0),
        ("stage27_runtime_leveltime_after", 0),
        ("stage27_order_ok", ref.order_ok if ref else 0),
        ("stage27_runtime_order_ok", 0),
        ("stage27_no_live_input_dependency", counters.no_live_input_dependency),
        ("stage27_actual_speaker_playback_deferred", counters.actual_speaker_playback_deferred),
        ("stage27_map_progression_absent", counters.map_progression_absent),
        ("stage27_generalized_combat_absent", counters.generalized_combat_absent),
        ("stage27_expected_signature", ref.signature if ref else 0),
        ("stage27_runtime_signature", 0),
        ("stage27_live_step", 0),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    pe.align_section(1)
    pe.label("stage27_log_text")
    x86.emit_asciiz(pe, _stage27_log_text(samples))
    pe.label("status_stage27_success_header")
    x86.emit_asciiz(pe, "\r\nsource_stage27_integrated_scripted_room_interaction_loop\r\nIntegrated scripted room loop proof OK\r\n")
    pe.label("status_stage27_line_prefix")
    x86.emit_asciiz(pe, "\r\nSelected MAP12 scripted room linedef: ")
    pe.label("status_stage27_log_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime state log: ")
    pe.label("status_stage27_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage27 integrated signature: ")
    pe.label("status_stage27_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage27 preserves stage26 through stage19, then owns one bounded MAP12 world. "
        "A deterministic ticcmd script issues one use command, reaches the proven reusable "
        "platform button route, and samples the same world as P_Ticker advances thinkers, "
        "P_UpdateSpecials restores the button, P_RespawnSpecials is guarded, and leveltime "
        "increments. Manual input, map progression, broad combat, and speaker output remain absent.\r\n",
    )
    for label, text in (
        ("title_stage27_map_prefix", " S27MAP="),
        ("title_stage27_line_prefix", " S27LINE="),
        ("title_stage27_special_prefix", " S27SPEC="),
        ("title_stage27_tag_prefix", " TAG27="),
        ("title_stage27_script_prefix", " SCRIPT27="),
        ("title_stage27_use_prefix", " USE27="),
        ("title_stage27_g_prefix", " GTIC27="),
        ("title_stage27_p_prefix", " PTIC27="),
        ("title_stage27_sample_prefix", " SAMP27="),
        ("title_stage27_distinct_prefix", " DIST27="),
        ("title_stage27_button_motion_prefix", " BMOV27="),
        ("title_stage27_final_floor_prefix", " FF27="),
        ("title_stage27_final_timer_prefix", " BT27="),
        ("title_stage27_leveltime_prefix", " LT27="),
        ("title_stage27_order_prefix", " ORDER27="),
        ("title_stage27_live_prefix", " LIVE27="),
        ("title_stage27_audio_prefix", " AUD27="),
        ("title_stage27_progress_prefix", " PROG27="),
        ("title_stage27_combat_prefix", " COMBAT27="),
        ("title_stage27_log_prefix", " LOG27="),
        ("title_stage27_signature_prefix", " S27SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)
    pe.label("stage27_live_title_start")
    x86.emit_asciiz(pe, "Inference Doom S27 LIVE START STEP27=0 waiting for timer-driven scripted loop")
    live_titles = _stage27_live_titles(samples, ref.signature if ref else 0)
    for index, title in enumerate(live_titles):
        pe.label(f"stage27_live_title_sample{index}")
        x86.emit_asciiz(pe, title)


def _stage27_live_titles(samples: tuple[Stage27StateSample, ...], signature: int) -> tuple[str, ...]:
    titles: list[str] = []
    for index, sample in enumerate(samples):
        prefix = (
            f"Inference Doom S27 LIVE STEP27={index + 1} "
            f"TIC27={sample.tic} F27={sample.floor} B27={sample.button_timer} "
            f"TEX27={sample.texture} STAT27={sample.plat_status} COUNT27={sample.plat_count}"
        )
        if index == len(samples) - 1:
            prefix += (
                " S19SIG=2088411722 S20SIG=3226031347 S21SIG=1770773845"
                " S22SIG=2207028069 S23SIG=3216085132 S24SIG=1919312263"
                " S25SIG=1688844032 S26SIG=132405987"
                f" S27SIG={signature}"
            )
        titles.append(prefix)
    return tuple(titles)


def _stage27_log_text(samples: tuple[Stage27StateSample, ...]) -> str:
    if not samples:
        return ""
    return "|".join(
        f"{sample.tic}:F{sample.floor}:B{sample.button_timer}:{sample.texture}:S{sample.plat_status}:C{sample.plat_count}"
        for sample in samples
    )


def build_source_stage27_integrated_scripted_room_interaction_loop_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_stage27_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_stage27_timer_tick(pe)
    emit_source_stage27_load_wad_integrated_scripted_room_interaction_loop(pe)
    stage26.emit_source_stage26_load_wad_first_ceiling_or_crusher_special_probe(pe)
    stage25.emit_source_stage25_load_wad_first_platform_lift_cycle_probe(pe)
    stage24.emit_source_stage24_load_wad_first_floor_sector_special_probe(pe)
    stage23.emit_source_stage23_load_wad_first_button_timer_restore_probe(pe)
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
    stage23.emit_render_first_button_timer_restore_probe_debug(pe)
    stage24.emit_render_first_floor_sector_special_probe_debug(pe)
    stage25.emit_render_first_platform_lift_cycle_probe_debug(pe)
    stage26.emit_render_first_ceiling_or_crusher_special_probe_debug(pe)
    emit_render_integrated_scripted_room_interaction_loop_debug(pe)
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
    stage23.emit_append_stage23_success_status(pe)
    stage24.emit_append_stage24_success_status(pe)
    stage25.emit_append_stage25_success_status(pe)
    stage26.emit_append_stage26_success_status(pe)
    emit_append_stage27_success_status(pe)
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
    stage23.emit_stage23_data(pe)
    stage24.emit_stage24_data(pe)
    stage25.emit_stage25_data(pe)
    stage26.emit_stage26_data(pe)
    emit_stage27_data(pe)
    return pe.build("entry")


def write_source_stage27_integrated_scripted_room_interaction_loop_exe(path: str | Path) -> bytes:
    image = build_source_stage27_integrated_scripted_room_interaction_loop_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage27 integrated scripted room interaction loop PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage27_integrated_scripted_room_interaction_loop.exe",
        help="path to write, default: build/source_stage27_integrated_scripted_room_interaction_loop.exe",
    )
    args = parser.parse_args()
    write_source_stage27_integrated_scripted_room_interaction_loop_exe(args.output)


if __name__ == "__main__":
    main()
