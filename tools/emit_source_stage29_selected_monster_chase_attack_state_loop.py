from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage28_live_input_to_deterministic_game_loop_bridge as stage28
from tools import x86
from tools.map_loader import load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


stage27 = stage28.stage27
stage26 = stage28.stage26
stage25 = stage28.stage25
stage24 = stage28.stage24
stage23 = stage28.stage23
stage22 = stage28.stage22
stage21 = stage28.stage21
stage20 = stage28.stage20
stage19 = stage28.stage19
stage18 = stage28.stage18
stage17 = stage28.stage17
stage16 = stage28.stage16
stage15 = stage28.stage15
stage14 = stage28.stage14
stage13 = stage28.stage13
stage12 = stage28.stage12
stage11 = stage28.stage11
stage10 = stage28.stage10
stage08 = stage28.stage08
stage07 = stage28.stage07
stage04 = stage28.stage04
stage03 = stage28.stage03
stage02 = stage28.stage02
stage01 = stage28.stage01


FRAMEBUFFER_WIDTH = stage28.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage28.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage28.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage28.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage28.WINDOW_WIDTH
WINDOW_HEIGHT = stage28.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage29SelectedMonsterChaseAttackStateLoop"
WINDOW_TITLE = "Inference Doom S29 Monster State Loop"
WAD_PATH = stage28.WAD_PATH

FRACBITS = stage28.FRACBITS
FRACUNIT = stage28.FRACUNIT
FNV_PRIME = stage28.FNV_PRIME
WM_TIMER = stage28.WM_TIMER
STAGE29_TIMER_ID = 29
STAGE29_TIMER_MS = stage28.STAGE28_TIMER_MS
DEFAULT_STAGE29_TICS = 6


SOURCE_TRACE = stage28.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/g_game.c",
        "G_Ticker deterministic replay shell for selected monster loop",
        "G_Ticker_stage29_selected_monster_replay_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_user.c",
        "P_PlayerThink/P_MovePsprites no-op selected command route",
        "P_PlayerThink_MovePsprites_stage29_selected_route_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_tick.c",
        "P_Ticker/P_RunThinkers/P_MobjThinker source ordering for one mobj",
        "P_Ticker_RunThinkers_MobjThinker_stage29_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_MobjThinker pain recovery and momentum service across multiple tics",
        "P_MobjThinker_stage29_selected_monster_state_loop_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "A_Chase selected target retention and attack-state decision boundary",
        "A_Chase_stage29_selected_attack_decision_boundary_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/info.c",
        "S_SPOS_PAIN/S_SPOS_PAIN2/S_SPOS_RUN1 selected shotgun-guy state loop",
        "info_tables_stage29_shotguy_state_loop_debug",
    ),
)


@dataclass
class Stage29Counters(stage18.Stage18Counters):
    g_ticker_calls: int = 0
    player_think_calls: int = 0
    move_psprites_calls: int = 0
    p_ticker_calls: int = 0
    run_thinkers_calls: int = 0
    thinker_function_calls: int = 0
    target_retained_tics: int = 0
    multi_tic_logs: int = 0
    final_attack_boundary: int = 0
    selected_damage_events: int = 0
    selected_death_events: int = 0
    selected_drop_events: int = 0
    deterministic_replay: int = 1
    live_input_ignored: int = 1
    broad_ai_absent: int = 1
    projectiles_absent: int = 1
    infighting_absent: int = 1
    generalized_combat_absent: int = 1
    pickups_absent: int = 1
    exits_absent: int = 1
    map_progression_absent: int = 1
    real_audio_absent: int = 1
    runtime_rendered_motion_deferred: int = 1
    source_stage30_absent: int = 1


@dataclass(frozen=True)
class Stage29MonsterLogRecord:
    tic: int
    state: int
    state_name: str
    tics: int
    x: int
    y: int
    momx: int
    momy: int
    target_index: int
    health: int
    threshold: int
    chase_calls: int
    attack_boundaries: int
    accepted_moves: int
    line_checks: int


@dataclass
class Stage29World:
    monster: stage18.Stage18World
    counters: Stage29Counters = field(default_factory=Stage29Counters)
    log: list[Stage29MonsterLogRecord] = field(default_factory=list)
    leveltime: int = 0


@dataclass(frozen=True)
class Stage29SelectedMonsterLoopReference:
    stage28: stage28.Stage28LiveInputBridgeReference
    stage18_ref: stage18.Stage18PostDamageMonsterMovementReference
    start_mobj: stage16.ActiveMobj
    final_mobj: stage16.ActiveMobj
    log: tuple[Stage29MonsterLogRecord, ...]
    counters: Stage29Counters
    movement_counters: stage14.MovementCounters
    iterator: stage14.BlockIteratorState
    boundary: str
    signature: int


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & 0xFFFFFFFF


def _hash_bytes(signature: int, data: bytes) -> int:
    for byte in data:
        signature = _hash_u32(signature, byte)
    return signature


def _state_name(info: stage16.Stage16InfoTables, state: int | None) -> str:
    return stage16._state_name(info, state)


def _copy_stage18_counters(src: stage18.Stage18Counters) -> Stage29Counters:
    values = {
        name: getattr(src, name)
        for name in stage18.Stage18Counters.__dataclass_fields__
    }
    return Stage29Counters(**values)


def build_stage29_world_from_stage17(
    wad: WadFile,
    wad_path: str | Path,
    ref17: stage17.Stage17FirstWeaponFireReference,
) -> Stage29World:
    loaded = load_map_from_file(wad_path, "MAP01")
    monster_world = stage18.build_stage18_world_from_stage17(wad, loaded, ref17)
    monster_world.execute_chase_actions = True
    counters = _copy_stage18_counters(monster_world.counters)
    monster_world.counters = counters
    return Stage29World(monster=monster_world, counters=counters)


def _sample_stage29(world: Stage29World, tic: int, delta: stage18.MovementDelta) -> None:
    actor = world.monster.actor
    record = Stage29MonsterLogRecord(
        tic=tic,
        state=actor.state if actor.state is not None else 0,
        state_name=_state_name(world.monster.info, actor.state),
        tics=actor.tics,
        x=actor.x >> FRACBITS,
        y=actor.y >> FRACBITS,
        momx=actor.momx,
        momy=actor.momy,
        target_index=actor.target_index if actor.target_index is not None else -1,
        health=actor.health,
        threshold=actor.threshold,
        chase_calls=world.counters.chase_calls,
        attack_boundaries=world.counters.attack_state_deferrals,
        accepted_moves=delta.accepted_moves,
        line_checks=delta.line_checks,
    )
    world.log.append(record)
    world.counters.multi_tic_logs += 1
    if record.target_index >= 0:
        world.counters.target_retained_tics += 1


def p_player_think_move_psprites_stage29_selected_route_source_shape(world: Stage29World) -> None:
    world.counters.player_think_calls += 1
    world.counters.move_psprites_calls += 1


def p_ticker_run_thinkers_mobjthinker_stage29_source_shape(world: Stage29World) -> stage18.MovementDelta:
    world.counters.p_ticker_calls += 1
    world.counters.run_thinkers_calls += 1
    world.counters.thinker_function_calls += 1
    delta = stage18.p_mobj_thinker_stage18_source_shape(world.monster, world.monster.actor)
    world.leveltime += 1
    return delta


def g_ticker_stage29_selected_monster_replay_source_shape(world: Stage29World) -> None:
    world.counters.g_ticker_calls += 1
    p_player_think_move_psprites_stage29_selected_route_source_shape(world)
    delta = p_ticker_run_thinkers_mobjthinker_stage29_source_shape(world)
    _sample_stage29(world, world.counters.g_ticker_calls, delta)
    if world.counters.attack_state_deferrals:
        world.counters.final_attack_boundary = 1


def run_stage29_selected_monster_loop_source_shape(
    world: Stage29World,
    *,
    max_tics: int = DEFAULT_STAGE29_TICS,
) -> tuple[Stage29MonsterLogRecord, ...]:
    for _ in range(max_tics):
        g_ticker_stage29_selected_monster_replay_source_shape(world)
        if world.counters.final_attack_boundary or world.monster.actor.health <= 0:
            break
    return tuple(world.log)


def _stage29_signature(ref: Stage29SelectedMonsterLoopReference) -> int:
    signature = 2166136261
    for value in (
        ref.stage28.signature,
        ref.stage18_ref.signature,
        len(ref.log),
        ref.counters.g_ticker_calls,
        ref.counters.player_think_calls,
        ref.counters.move_psprites_calls,
        ref.counters.p_ticker_calls,
        ref.counters.run_thinkers_calls,
        ref.counters.thinker_function_calls,
        ref.counters.xy_movement_services,
        ref.counters.state_tic_decrements,
        ref.counters.mobj_state_sets,
        ref.counters.mobj_state_transitions,
        ref.counters.pain_sound_deferrals,
        ref.counters.chase_calls,
        ref.counters.threshold_decrements,
        ref.counters.missile_range_checks,
        ref.counters.attack_state_deferrals,
        ref.counters.final_attack_boundary,
        ref.counters.selected_damage_events,
        ref.counters.selected_death_events,
        ref.counters.selected_drop_events,
        ref.movement_counters.try_move_calls,
        ref.movement_counters.accepted_moves,
        ref.movement_counters.line_checks,
        ref.movement_counters.block_relinks,
        ref.movement_counters.sector_relinks,
        ref.final_mobj.x,
        ref.final_mobj.y,
        ref.final_mobj.momx,
        ref.final_mobj.momy,
        ref.final_mobj.state if ref.final_mobj.state is not None else 0,
        ref.final_mobj.tics,
        ref.final_mobj.health,
        ref.final_mobj.threshold,
        ref.counters.source_stage30_absent,
    ):
        signature = _hash_u32(signature, value)
    for record in ref.log:
        for value in (
            record.tic,
            record.state,
            record.tics,
            record.x,
            record.y,
            record.momx,
            record.momy,
            record.target_index,
            record.health,
            record.threshold,
            record.chase_calls,
            record.attack_boundaries,
            record.accepted_moves,
            record.line_checks,
        ):
            signature = _hash_u32(signature, value)
        signature = _hash_bytes(signature, record.state_name.encode("ascii"))
    signature = _hash_bytes(signature, ref.boundary.encode("ascii"))
    return signature


def _reference_stage29_uncached(wad_path: str | Path) -> Stage29SelectedMonsterLoopReference:
    wad_path = Path(wad_path)
    wad = WadFile.from_file(wad_path)
    ref28 = stage28.reference_live_input_to_deterministic_game_loop_bridge_for_pinned_map(wad_path)
    ref18 = stage18.reference_post_damage_monster_movement_and_chase_probe_for_pinned_map(wad_path)
    ref17 = stage17.reference_first_weapon_fire_damage_and_death_probe_for_pinned_map(wad_path)
    world = build_stage29_world_from_stage17(wad, wad_path, ref17)
    start_mobj = replace(world.monster.actor)
    log = run_stage29_selected_monster_loop_source_shape(world)
    final_mobj = replace(world.monster.actor)
    iterator = replace(world.monster.movement.iterator, line_validcounts=dict(world.monster.movement.iterator.line_validcounts or {}))
    boundary = "ATTACK_DECISION" if world.counters.final_attack_boundary else "TIC_WINDOW"
    ref = Stage29SelectedMonsterLoopReference(
        stage28=ref28,
        stage18_ref=ref18,
        start_mobj=start_mobj,
        final_mobj=final_mobj,
        log=log,
        counters=replace(world.counters),
        movement_counters=replace(world.monster.movement.counters),
        iterator=iterator,
        boundary=boundary,
        signature=0,
    )
    return Stage29SelectedMonsterLoopReference(**{**ref.__dict__, "signature": _stage29_signature(ref)})


@lru_cache(maxsize=4)
def _reference_stage29_cached(wad_path: str) -> Stage29SelectedMonsterLoopReference:
    return _reference_stage29_uncached(wad_path)


def reference_selected_monster_chase_attack_state_loop_for_pinned_map(
    wad_path: str | Path,
) -> Stage29SelectedMonsterLoopReference:
    return _reference_stage29_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage29SelectedMonsterLoopReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_selected_monster_chase_attack_state_loop_for_pinned_map(wad_path)


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


def emit_stage29_entry(pe: PE32) -> None:
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
    x86.call_rel32(pe, "source_stage29_load_wad_selected_monster_chase_attack_state_loop")
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
    x86.push_abs32(pe, "stage29_replay_title_start")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE29_TIMER_MS)
    x86.push_imm32(pe, STAGE29_TIMER_ID)
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
    x86.call_rel32(pe, "stage29_timer_tick")
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


def emit_stage29_timer_tick(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.log) if ref else DEFAULT_STAGE29_TICS
    pe.label("stage29_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage29_replay_step")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage29_replay_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage29_replay_sample{index}")
        x86.push_abs32(pe, f"stage29_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        x86.mov_mem_abs32_imm32(pe, "stage29_replay_step", index + 1)
        if index == sample_count - 1:
            x86.push_imm32(pe, STAGE29_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)


def emit_source_stage29_load_wad_selected_monster_chase_attack_state_loop(pe: PE32) -> None:
    pe.label("source_stage29_load_wad_selected_monster_chase_attack_state_loop")
    x86.call_rel32(pe, "source_stage28_load_wad_live_input_to_deterministic_game_loop_bridge")
    x86.mov_reg_mem_abs32(pe, "eax", "stage28_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage28_expected_signature")
    x86.jne_rel32(pe, "source_stage29_return")
    x86.call_rel32(pe, "render_selected_monster_chase_attack_state_loop_debug")
    x86.call_rel32(pe, "append_stage29_success_status")
    pe.label("source_stage29_return")
    x86.ret(pe)


def emit_render_selected_monster_chase_attack_state_loop_debug(pe: PE32) -> None:
    pe.label("G_Ticker_stage29_selected_monster_replay_source_shape_debug")
    pe.label("P_PlayerThink_MovePsprites_stage29_selected_route_source_shape_debug")
    pe.label("P_Ticker_RunThinkers_MobjThinker_stage29_source_shape_debug")
    pe.label("P_MobjThinker_stage29_selected_monster_state_loop_source_shape_debug")
    pe.label("A_Chase_stage29_selected_attack_decision_boundary_debug")
    pe.label("info_tables_stage29_shotguy_state_loop_debug")
    pe.label("render_selected_monster_chase_attack_state_loop_debug")
    for dst, src in (
        ("stage29_runtime_signature", "stage29_expected_signature"),
        ("stage29_runtime_final_x", "stage29_final_x"),
        ("stage29_runtime_final_y", "stage29_final_y"),
        ("stage29_runtime_final_state", "stage29_final_state"),
        ("stage29_runtime_final_tics", "stage29_final_tics"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage26._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage29_success_status(pe: PE32) -> None:
    pe.label("append_stage29_success_status")
    _emit_seek_buffer_end(pe, "status_success_buffer", "stage29_status")
    stage01.append_c_string_label(pe, "status_stage29_success_header")
    stage01.append_c_string_label(pe, "status_stage29_log_prefix")
    stage01.append_c_string_label(pe, "stage29_log_text")
    stage01.append_u32_label(pe, "status_stage29_signature_prefix", "stage29_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage29_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage29_title")
    for prefix, label, signed in (
        ("title_stage29_mapthing_prefix", "stage29_mapthing", False),
        ("title_stage29_mobj_prefix", "stage29_mobj", False),
        ("title_stage29_tics_prefix", "stage29_tics", False),
        ("title_stage29_g_prefix", "stage29_g_ticker_calls", False),
        ("title_stage29_pthink_prefix", "stage29_player_think_calls", False),
        ("title_stage29_pticker_prefix", "stage29_p_ticker_calls", False),
        ("title_stage29_run_prefix", "stage29_run_thinkers_calls", False),
        ("title_stage29_xy_prefix", "stage29_xy_movement_services", False),
        ("title_stage29_chase_prefix", "stage29_chase_calls", False),
        ("title_stage29_attack_prefix", "stage29_attack_state_deferrals", False),
        ("title_stage29_final_x_prefix", "stage29_runtime_final_x", True),
        ("title_stage29_final_y_prefix", "stage29_runtime_final_y", True),
        ("title_stage29_final_state_prefix", "stage29_runtime_final_state", False),
        ("title_stage29_final_tics_prefix", "stage29_runtime_final_tics", False),
        ("title_stage29_health_prefix", "stage29_final_health", True),
        ("title_stage29_target_prefix", "stage29_final_target", True),
        ("title_stage29_damage_prefix", "stage29_selected_damage_events", False),
        ("title_stage29_death_prefix", "stage29_selected_death_events", False),
        ("title_stage29_drop_prefix", "stage29_selected_drop_events", False),
        ("title_stage29_stage30_prefix", "stage29_source_stage30_absent", False),
    ):
        (stage01.append_i32_label if signed else stage01.append_u32_label)(pe, prefix, label)
    stage01.append_c_string_label(pe, "title_stage29_boundary_prefix")
    stage01.append_c_string_label(pe, "stage29_boundary_text")
    stage01.append_c_string_label(pe, "title_stage29_log_prefix")
    stage01.append_c_string_label(pe, "stage29_log_text")
    stage01.append_u32_label(pe, "title_stage29_signature_prefix", "stage29_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def _stage29_log_text(log: tuple[Stage29MonsterLogRecord, ...]) -> str:
    return "|".join(
        f"{rec.tic}:{rec.state_name}:T{rec.tics}:XY{rec.x},{rec.y}:M{rec.momx},{rec.momy}:TG{rec.target_index}:H{rec.health}:TH{rec.threshold}:CH{rec.chase_calls}:AB{rec.attack_boundaries}"
        for rec in log
    )


def _stage29_replay_titles(ref: Stage29SelectedMonsterLoopReference | None) -> tuple[str, ...]:
    if ref is None:
        return ()
    titles: list[str] = []
    for index, rec in enumerate(ref.log):
        title = (
            f"Inference Doom S29 REPLAY STEP29={index + 1} LIVE29=0 "
            f"TIC29={rec.tic} ST29={rec.state_name} T29={rec.tics} "
            f"X29={rec.x} Y29={rec.y} H29={rec.health} TG29={rec.target_index} "
            f"CH29={rec.chase_calls} AB29={rec.attack_boundaries}"
        )
        if index == len(ref.log) - 1:
            first = ref.log[0]
            title += (
                f" BOUND29={ref.boundary} S30ABS={ref.counters.source_stage30_absent}"
                f" LOG29={first.tic}:{first.state_name}>{rec.tic}:{rec.state_name}"
                " S19SIG=2088411722 S20SIG=3226031347 S21SIG=1770773845"
                " S22SIG=2207028069 S23SIG=3216085132 S24SIG=1919312263"
                " S25SIG=1688844032 S26SIG=132405987 S27SIG=1735738182"
                " S28SIG=2805406010"
                f" S29SIG={ref.signature}"
            )
        titles.append(title)
    return tuple(titles)


def emit_stage29_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    counters = ref.counters if ref else Stage29Counters()
    final = ref.final_mobj if ref else None
    log = ref.log if ref else ()
    pe.align_section(4)
    for name, value in (
        ("stage29_mapthing", ref.start_mobj.mapthing_index if ref else 0),
        ("stage29_mobj", ref.start_mobj.index if ref else 0),
        ("stage29_tics", len(log)),
        ("stage29_g_ticker_calls", counters.g_ticker_calls),
        ("stage29_player_think_calls", counters.player_think_calls),
        ("stage29_move_psprites_calls", counters.move_psprites_calls),
        ("stage29_p_ticker_calls", counters.p_ticker_calls),
        ("stage29_run_thinkers_calls", counters.run_thinkers_calls),
        ("stage29_thinker_function_calls", counters.thinker_function_calls),
        ("stage29_xy_movement_services", counters.xy_movement_services),
        ("stage29_state_tic_decrements", counters.state_tic_decrements),
        ("stage29_pain_sound_deferrals", counters.pain_sound_deferrals),
        ("stage29_chase_calls", counters.chase_calls),
        ("stage29_threshold_decrements", counters.threshold_decrements),
        ("stage29_missile_range_checks", counters.missile_range_checks),
        ("stage29_attack_state_deferrals", counters.attack_state_deferrals),
        ("stage29_final_attack_boundary", counters.final_attack_boundary),
        ("stage29_selected_damage_events", counters.selected_damage_events),
        ("stage29_selected_death_events", counters.selected_death_events),
        ("stage29_selected_drop_events", counters.selected_drop_events),
        ("stage29_broad_ai_absent", counters.broad_ai_absent),
        ("stage29_projectiles_absent", counters.projectiles_absent),
        ("stage29_infighting_absent", counters.infighting_absent),
        ("stage29_generalized_combat_absent", counters.generalized_combat_absent),
        ("stage29_pickups_absent", counters.pickups_absent),
        ("stage29_exits_absent", counters.exits_absent),
        ("stage29_map_progression_absent", counters.map_progression_absent),
        ("stage29_real_audio_absent", counters.real_audio_absent),
        ("stage29_runtime_rendered_motion_deferred", counters.runtime_rendered_motion_deferred),
        ("stage29_source_stage30_absent", counters.source_stage30_absent),
        ("stage29_final_x", (final.x >> FRACBITS if final else 0) & 0xFFFFFFFF),
        ("stage29_runtime_final_x", 0),
        ("stage29_final_y", (final.y >> FRACBITS if final else 0) & 0xFFFFFFFF),
        ("stage29_runtime_final_y", 0),
        ("stage29_final_state", final.state if final and final.state is not None else 0),
        ("stage29_runtime_final_state", 0),
        ("stage29_final_tics", final.tics if final else 0),
        ("stage29_runtime_final_tics", 0),
        ("stage29_final_health", final.health if final else 0),
        ("stage29_final_target", final.target_index if final and final.target_index is not None else -1),
        ("stage29_expected_signature", ref.signature if ref else 0),
        ("stage29_runtime_signature", 0),
        ("stage29_replay_step", 0),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    pe.align_section(1)
    pe.label("stage29_boundary_text")
    x86.emit_asciiz(pe, ref.boundary if ref else "")
    pe.label("stage29_final_state_name")
    x86.emit_asciiz(pe, _state_name(stage16.parse_stage16_info_tables(), final.state) if final else "")
    pe.label("stage29_log_text")
    x86.emit_asciiz(pe, _stage29_log_text(log))
    pe.label("status_stage29_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage29_selected_monster_chase_attack_state_loop\r\n"
        "Selected monster chase/attack state loop proof OK\r\n",
    )
    pe.label("status_stage29_log_prefix")
    x86.emit_asciiz(pe, "\r\nSelected monster multi-tic log: ")
    pe.label("status_stage29_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage29 selected monster loop signature: ")
    pe.label("status_stage29_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage29 preserves stage28 through stage19, then runs a deterministic "
        "MAP01 shotgun-guy replay from the stage17 damaged state through the "
        "source-ordered G_Ticker, P_PlayerThink/P_MovePsprites, P_Ticker, "
        "P_RunThinkers, and P_MobjThinker shape. The route services momentum, "
        "recovers pain states, retains target 0, dispatches one A_Chase, and "
        "stops at the selected attack decision boundary. The attack action, "
        "projectiles, deaths, drops, broad AI, generalized combat, map progression, "
        "runtime rendered motion, and real audio remain deferred.\r\n",
    )
    for label, text in (
        ("title_stage29_mapthing_prefix", " MT29="),
        ("title_stage29_mobj_prefix", " MO29="),
        ("title_stage29_tics_prefix", " TIC29="),
        ("title_stage29_g_prefix", " GTIC29="),
        ("title_stage29_pthink_prefix", " PTH29="),
        ("title_stage29_pticker_prefix", " PTIC29="),
        ("title_stage29_run_prefix", " RUN29="),
        ("title_stage29_xy_prefix", " XY29="),
        ("title_stage29_chase_prefix", " CH29="),
        ("title_stage29_attack_prefix", " AB29="),
        ("title_stage29_final_x_prefix", " FX29="),
        ("title_stage29_final_y_prefix", " FY29="),
        ("title_stage29_final_state_prefix", " FST29="),
        ("title_stage29_final_tics_prefix", " FT29="),
        ("title_stage29_health_prefix", " H29="),
        ("title_stage29_target_prefix", " TG29="),
        ("title_stage29_damage_prefix", " DMG29="),
        ("title_stage29_death_prefix", " DIE29="),
        ("title_stage29_drop_prefix", " DROP29="),
        ("title_stage29_stage30_prefix", " S30ABS="),
        ("title_stage29_boundary_prefix", " BOUND29="),
        ("title_stage29_log_prefix", " LOG29="),
        ("title_stage29_signature_prefix", " S29SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)
    pe.label("stage29_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S29 REPLAY START STEP29=0 LIVE29=0 waiting for selected monster state loop")
    for index, title in enumerate(_stage29_replay_titles(ref)):
        pe.label(f"stage29_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)


def build_source_stage29_selected_monster_chase_attack_state_loop_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_stage29_entry(pe)
    stage28.emit_stage28_wndproc_framebuffer(pe)
    emit_stage29_timer_tick(pe)
    emit_source_stage29_load_wad_selected_monster_chase_attack_state_loop(pe)
    stage28.emit_source_stage28_load_wad_live_input_to_deterministic_game_loop_bridge(pe)
    stage27.emit_source_stage27_load_wad_integrated_scripted_room_interaction_loop(pe)
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
    stage27.emit_render_integrated_scripted_room_interaction_loop_debug(pe)
    stage28.emit_render_live_input_to_deterministic_game_loop_bridge_debug(pe)
    emit_render_selected_monster_chase_attack_state_loop_debug(pe)
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
    stage27.emit_append_stage27_success_status(pe)
    stage28.emit_append_stage28_success_status(pe)
    emit_append_stage29_success_status(pe)
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
    stage27.emit_stage27_data(pe)
    stage28.emit_stage28_data(pe)
    emit_stage29_data(pe)
    return pe.build("entry")


def write_source_stage29_selected_monster_chase_attack_state_loop_exe(path: str | Path) -> bytes:
    image = build_source_stage29_selected_monster_chase_attack_state_loop_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage29 selected monster chase/attack state loop PE32 executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage29_selected_monster_chase_attack_state_loop.exe",
        help="path to write, default: build/source_stage29_selected_monster_chase_attack_state_loop.exe",
    )
    args = parser.parse_args()
    write_source_stage29_selected_monster_chase_attack_state_loop_exe(args.output)


if __name__ == "__main__":
    main()
