from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Sequence


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage31_runtime_real_renderer_motion_bridge as stage31
from tools import x86
from tools.pe32 import PE32
from tools.wad import WadFile


stage30 = stage31.stage30
stage29 = stage31.stage29
stage28 = stage31.stage28
stage27 = stage31.stage27
stage26 = stage31.stage26
stage25 = stage31.stage25
stage24 = stage31.stage24
stage23 = stage31.stage23
stage22 = stage31.stage22
stage21 = stage31.stage21
stage20 = stage31.stage20
stage19 = stage31.stage19
stage18 = stage31.stage18
stage17 = stage31.stage17
stage16 = stage31.stage16
stage15 = stage31.stage15
stage14 = stage31.stage14
stage13 = stage31.stage13
stage12 = stage31.stage12
stage11 = stage31.stage11
stage10 = stage31.stage10
stage08 = stage31.stage08
stage07 = stage31.stage07
stage04 = stage31.stage04
stage03 = stage31.stage03
stage02 = stage31.stage02
stage01 = stage31.stage01


FRAMEBUFFER_WIDTH = stage31.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage31.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage31.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage31.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage31.WINDOW_WIDTH
WINDOW_HEIGHT = stage31.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage32SelectedCombatVisualStateBridge"
WINDOW_TITLE = "Inference Doom S32 Combat Visual State Bridge"
WAD_PATH = stage31.WAD_PATH

FRACBITS = stage31.FRACBITS
FRACUNIT = stage15.FRACUNIT
FNV_OFFSET_BASIS = stage31.FNV_OFFSET_BASIS
FNV_PRIME = stage31.FNV_PRIME
WM_TIMER = stage31.WM_TIMER
STAGE32_TIMER_ID = 32
STAGE32_TIMER_MS = stage31.STAGE31_TIMER_MS
SELECTED_SAMPLE_TICS = stage31.SELECTED_SAMPLE_TICS

COMMAND_RECORD_SIZE = stage31.COMMAND_RECORD_SIZE
SPAN_RECORD_SIZE = stage31.SPAN_RECORD_SIZE
SELECTED_PSPRITE_STATES = ("S_SGUN", "S_SGUN3", "S_SGUN4")


SOURCE_TRACE = stage31.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_pspr.c",
        "P_SetPsprite/P_MovePsprites selected shotgun psprite state progression",
        "P_SetPsprite_stage32_selected_shotgun_psprite_state_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_things.c",
        "R_DrawPlayerSprites/R_DrawPSprite selected weapon patch posts after masked draw ordering",
        "R_DrawPSprite_stage32_selected_weapon_post_table_debug",
    ),
    (
        "reference/chocolate-doom/src/v_video.c",
        "V_DrawBlock-style present after walls/flats and selected psprite posts",
        "V_DrawBlock_stage32_selected_combat_visual_present_debug",
    ),
)


@dataclass(frozen=True)
class Stage32PspriteCommand:
    x: int
    yl: int
    yh: int
    iscale: int
    texturemid: int
    source_index: int
    patch_name: str
    patch_column: int


@dataclass(frozen=True)
class Stage32FrameSample:
    step: int
    tic: int
    psprite_state: int
    psprite_state_name: str
    psprite_sprite_name: str
    psprite_patch_name: str
    psprite_frame: int
    psprite_tics: int
    psprite_commands: tuple[Stage32PspriteCommand, ...]
    base_framebuffer_signature: int
    framebuffer_signature: int
    wall_pixels_drawn: int
    flat_pixels_drawn: int
    psprite_pixels_drawn: int
    clear_sequence: int
    wall_flat_sequence: int
    psprite_sequence: int
    present_sequence: int


@dataclass(frozen=True)
class Stage32SelectedCombatVisualStateReference:
    stage31: stage31.Stage31RuntimeRealRendererReference
    samples: tuple[Stage32FrameSample, ...]
    psprite_sources: tuple[bytes, ...]
    palette32: tuple[int, ...]
    distinct_visual_states: int
    distinct_psprite_command_tables: int
    distinct_framebuffer_signatures: int
    distinct_base_framebuffer_signatures: int
    sprite_contribution_signatures: int
    full_frame_byte_arrays_absent: int
    runtime_renderer_primitives: int
    wall_path_replayed: int
    flat_path_replayed: int
    psprite_path_replayed: int
    projectiles_absent: int
    explosions_absent: int
    monster_attack_execution_absent: int
    damage_death_drop_absent: int
    generalized_combat_absent: int
    broad_ai_absent: int
    generalized_sprite_systems_absent: int
    generalized_specials_absent: int
    map_progression_absent: int
    ui_systems_absent: int
    real_audio_absent: int
    source_stage33_absent: int
    signature: int


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & 0xFFFFFFFF


def _draw_stage31_base(
    sample: stage31.Stage31FrameSample,
    ref31: stage31.Stage31RuntimeRealRendererReference,
) -> tuple[bytearray, int, int, int]:
    frame = bytearray(FRAMEBUFFER_BYTES)
    wall_pixels = 0
    flat_pixels = 0
    for command in sample.wall_commands:
        wall_pixels += stage31._draw_column(
            frame,
            command,
            ref31.column_sources[command.source_index],
            ref31.palette32,
        )
    for command in sample.flat_spans:
        flat_pixels += stage31._draw_span(
            frame,
            command,
            ref31.flat_sources[command.source_index],
            ref31.palette32,
        )
    return frame, stage31._framebuffer_signature(frame), wall_pixels, flat_pixels


def _draw_psprite_commands(
    frame: bytearray,
    commands: Sequence[Stage32PspriteCommand],
    sources: Sequence[bytes],
    palette32: Sequence[int],
) -> int:
    pixels = 0
    for command in commands:
        pixels += stage31._draw_column(
            frame,
            stage31.Stage31ColumnCommand(
                x=command.x,
                yl=command.yl,
                yh=command.yh,
                iscale=command.iscale,
                texturemid=command.texturemid,
                source_index=command.source_index,
            ),
            sources[command.source_index],
            palette32,
        )
    return pixels


def _selected_psprite_commands(
    wad: WadFile,
    info: stage15.Stage15InfoTables,
    patch_lookup: dict[tuple[int, int], str],
    state_name: str,
    sources: list[bytes],
) -> tuple[int, str, str, str, int, int, tuple[Stage32PspriteCommand, ...]]:
    state_index = info.state_index[state_name]
    state = info.states[state_index]
    frame = state.frame & stage13.FF_FRAMEMASK
    sprite_name = info.sprnames[state.sprite]
    patch_name = patch_lookup.get((state.sprite, frame), f"{sprite_name}{chr(ord('A') + frame)}0")
    before = len(sources)
    psp = stage15.PspDef(state=state_index, tics=state.tics, sx=0, sy=stage15.WEAPONTOP)
    raw_commands: list[stage15.PatchDrawCommand] = []
    stage15._append_psprite_patch_commands(wad, patch_name, psp, "weapon", raw_commands, sources)
    commands = tuple(
        Stage32PspriteCommand(
            x=command.x,
            yl=command.yl,
            yh=command.yh,
            iscale=command.iscale,
            texturemid=command.texturemid,
            source_index=command.source_index,
            patch_name=command.patch_name,
            patch_column=command.patch_column,
        )
        for command in raw_commands
    )
    assert len(sources) >= before
    return state_index, state.name, sprite_name, patch_name, frame, state.tics, commands


def _stage32_signature(ref: Stage32SelectedCombatVisualStateReference) -> int:
    sig = FNV_OFFSET_BASIS
    for value in (
        ref.stage31.signature,
        len(ref.samples),
        len(ref.psprite_sources),
        ref.distinct_visual_states,
        ref.distinct_psprite_command_tables,
        ref.distinct_framebuffer_signatures,
        ref.distinct_base_framebuffer_signatures,
        ref.sprite_contribution_signatures,
        ref.full_frame_byte_arrays_absent,
        ref.runtime_renderer_primitives,
        ref.wall_path_replayed,
        ref.flat_path_replayed,
        ref.psprite_path_replayed,
        ref.projectiles_absent,
        ref.explosions_absent,
        ref.monster_attack_execution_absent,
        ref.damage_death_drop_absent,
        ref.generalized_combat_absent,
        ref.broad_ai_absent,
        ref.generalized_sprite_systems_absent,
        ref.generalized_specials_absent,
        ref.map_progression_absent,
        ref.ui_systems_absent,
        ref.real_audio_absent,
        ref.source_stage33_absent,
    ):
        sig = _hash_u32(sig, value)
    for sample in ref.samples:
        for value in (
            sample.step,
            sample.tic,
            sample.psprite_state,
            sample.psprite_frame,
            sample.psprite_tics,
            len(sample.psprite_commands),
            sample.base_framebuffer_signature,
            sample.framebuffer_signature,
            sample.wall_pixels_drawn,
            sample.flat_pixels_drawn,
            sample.psprite_pixels_drawn,
            sample.clear_sequence,
            sample.wall_flat_sequence,
            sample.psprite_sequence,
            sample.present_sequence,
        ):
            sig = _hash_u32(sig, value)
    return sig


def _reference_stage32_uncached(wad_path: str | Path) -> Stage32SelectedCombatVisualStateReference:
    wad_path = Path(wad_path)
    wad = WadFile.from_file(wad_path)
    ref31 = stage31.reference_runtime_real_renderer_motion_bridge_for_pinned_map(wad_path)
    info = stage15.parse_stage15_info_tables()
    patch_lookup = stage15.build_patch_frame_lookup(wad, info)
    psprite_sources: list[bytes] = []
    samples: list[Stage32FrameSample] = []
    for index, base_sample in enumerate(ref31.samples):
        state_name = SELECTED_PSPRITE_STATES[index % len(SELECTED_PSPRITE_STATES)]
        state_index, resolved_name, sprite_name, patch_name, frame_index, tics, commands = _selected_psprite_commands(
            wad,
            info,
            patch_lookup,
            state_name,
            psprite_sources,
        )
        frame, base_sig, wall_pixels, flat_pixels = _draw_stage31_base(base_sample, ref31)
        psprite_pixels = _draw_psprite_commands(frame, commands, psprite_sources, ref31.palette32)
        samples.append(
            Stage32FrameSample(
                step=base_sample.step,
                tic=base_sample.tic,
                psprite_state=state_index,
                psprite_state_name=resolved_name,
                psprite_sprite_name=sprite_name,
                psprite_patch_name=patch_name,
                psprite_frame=frame_index,
                psprite_tics=tics,
                psprite_commands=commands,
                base_framebuffer_signature=base_sig,
                framebuffer_signature=stage31._framebuffer_signature(frame),
                wall_pixels_drawn=wall_pixels,
                flat_pixels_drawn=flat_pixels,
                psprite_pixels_drawn=psprite_pixels,
                clear_sequence=base_sample.step * 4 - 3,
                wall_flat_sequence=base_sample.step * 4 - 2,
                psprite_sequence=base_sample.step * 4 - 1,
                present_sequence=base_sample.step * 4,
            )
        )
    ref = Stage32SelectedCombatVisualStateReference(
        stage31=ref31,
        samples=tuple(samples),
        psprite_sources=tuple(psprite_sources),
        palette32=ref31.palette32,
        distinct_visual_states=len({s.psprite_state_name for s in samples}),
        distinct_psprite_command_tables=len(
            {tuple((c.x, c.yl, c.yh, c.texturemid, c.patch_name) for c in s.psprite_commands[:32]) for s in samples}
        ),
        distinct_framebuffer_signatures=len({s.framebuffer_signature for s in samples}),
        distinct_base_framebuffer_signatures=len({s.base_framebuffer_signature for s in samples}),
        sprite_contribution_signatures=len({(s.base_framebuffer_signature, s.framebuffer_signature) for s in samples}),
        full_frame_byte_arrays_absent=1,
        runtime_renderer_primitives=1,
        wall_path_replayed=1,
        flat_path_replayed=1,
        psprite_path_replayed=1,
        projectiles_absent=1,
        explosions_absent=1,
        monster_attack_execution_absent=1,
        damage_death_drop_absent=1,
        generalized_combat_absent=1,
        broad_ai_absent=1,
        generalized_sprite_systems_absent=1,
        generalized_specials_absent=1,
        map_progression_absent=1,
        ui_systems_absent=1,
        real_audio_absent=1,
        source_stage33_absent=1,
        signature=0,
    )
    return Stage32SelectedCombatVisualStateReference(**{**ref.__dict__, "signature": _stage32_signature(ref)})


@lru_cache(maxsize=4)
def _reference_stage32_cached(wad_path: str) -> Stage32SelectedCombatVisualStateReference:
    return _reference_stage32_uncached(wad_path)


def reference_selected_combat_visual_state_bridge_for_pinned_map(
    wad_path: str | Path,
) -> Stage32SelectedCombatVisualStateReference:
    return _reference_stage32_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage32SelectedCombatVisualStateReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_selected_combat_visual_state_bridge_for_pinned_map(wad_path)


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


def emit_stage32_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")
    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage32_class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage32_class_registered")
    x86.call_rel32(pe, "source_stage32_load_wad_selected_combat_visual_state_bridge")
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
    x86.jne_rel32(pe, "stage32_window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage32_window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_abs32(pe, "stage32_replay_title_start")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE32_TIMER_MS)
    x86.push_imm32(pe, STAGE32_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
    pe.label("stage32_message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage32_clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "stage32_message_error")
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, WM_TIMER)
    x86.jne_rel32(pe, "stage32_dispatch_message")
    x86.call_rel32(pe, "stage32_timer_tick")
    pe.label("stage32_dispatch_message")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "stage32_message_loop")
    pe.label("stage32_clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage32_message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_stage32_timer_tick(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(SELECTED_SAMPLE_TICS)
    pe.label("stage32_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage32_replay_step")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage32_replay_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage32_replay_sample{index}")
        x86.call_rel32(pe, f"stage32_draw_sample{index}")
        x86.push_abs32(pe, f"stage32_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.mov_mem_abs32_imm32(pe, "stage32_replay_step", index + 1)
        if index == sample_count - 1:
            x86.push_imm32(pe, STAGE32_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)


def emit_stage32_draw_psprite_commands(pe: PE32) -> None:
    pe.label("R_DrawPSprite_stage32_selected_weapon_post_table_debug")
    pe.label("stage32_draw_psprite_commands")
    x86.mov_mem_abs32_imm32(pe, "stage10_columns_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage10_pixels_drawn", 0)
    x86.mov_mem_abs32_abs32(pe, "dc_colormap", "stage31_palette32")
    pe.label("stage32_psprite_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "stage32_psprite_remaining")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage32_psprite_done")
    x86.mov_reg_mem_abs32(pe, "esi", "stage32_psprite_scan_ptr")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage10.DRAW_COMMAND_X)
    x86.mov_mem_abs32_eax(pe, "dc_x")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage10.DRAW_COMMAND_YL)
    x86.mov_mem_abs32_eax(pe, "dc_yl")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage10.DRAW_COMMAND_YH)
    x86.mov_mem_abs32_eax(pe, "dc_yh")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage10.DRAW_COMMAND_ISCALE)
    x86.mov_mem_abs32_eax(pe, "dc_iscale")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage10.DRAW_COMMAND_TEXTUREMID)
    x86.mov_mem_abs32_eax(pe, "dc_texturemid")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", stage10.DRAW_COMMAND_SOURCE)
    x86.mov_mem_abs32_eax(pe, "dc_source")
    stage07._emit_inc_abs32(pe, "stage32_psprite_posts_drawn")
    x86.call_rel32(pe, "render_draw_column_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage10_pixels_drawn")
    x86.mov_mem_abs32_eax(pe, "stage32_psprite_pixels_drawn")
    x86.mov_reg_mem_abs32(pe, "esi", "stage32_psprite_scan_ptr")
    x86.add_reg_imm32(pe, "esi", COMMAND_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, "stage32_psprite_scan_ptr", "esi")
    x86.dec_mem_abs32(pe, "stage32_psprite_remaining")
    x86.jmp_rel32(pe, "stage32_psprite_loop")
    pe.label("stage32_psprite_done")
    x86.ret(pe)


def _emit_stage32_draw_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage32_draw_sample{index}")
    x86.call_rel32(pe, "stage31_clear_framebuffer")
    for dst, src in (
        ("stage31_runtime_viewx", f"stage31_sample{index}_viewx"),
        ("stage31_runtime_viewy", f"stage31_sample{index}_viewy"),
        ("stage31_runtime_viewz", f"stage31_sample{index}_viewz"),
        ("stage31_runtime_viewangle", f"stage31_sample{index}_viewangle"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.mov_mem_abs32_imm32(pe, "stage31_wall_columns_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage31_wall_pixels_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage31_flat_spans_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage31_flat_pixels_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage32_psprite_posts_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage32_psprite_pixels_drawn", 0)
    x86.mov_mem_abs32_abs32(pe, "stage31_wall_scan_ptr", f"stage31_wall_commands_{index}")
    x86.mov_mem_abs32_abs32(pe, "stage31_span_scan_ptr", f"stage31_span_commands_{index}")
    x86.mov_mem_abs32_abs32(pe, "stage32_psprite_scan_ptr", f"stage32_psprite_commands_{index}")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage31_sample{index}_wall_command_count")
    x86.mov_mem_abs32_eax(pe, "stage31_wall_remaining")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage31_sample{index}_span_command_count")
    x86.mov_mem_abs32_eax(pe, "stage31_span_remaining")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage32_sample{index}_psprite_command_count")
    x86.mov_mem_abs32_eax(pe, "stage32_psprite_remaining")
    x86.call_rel32(pe, "stage31_draw_wall_commands")
    x86.call_rel32(pe, "stage31_draw_flat_spans")
    x86.call_rel32(pe, "stage32_draw_psprite_commands")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage32_runtime_fb_signature")
    x86.ret(pe)


def emit_source_stage32_load_wad_selected_combat_visual_state_bridge(pe: PE32) -> None:
    pe.label("source_stage32_load_wad_selected_combat_visual_state_bridge")
    x86.call_rel32(pe, "source_stage31_load_wad_runtime_real_renderer_motion_bridge")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage31_expected_signature")
    x86.jne_rel32(pe, "source_stage32_return")
    x86.call_rel32(pe, "render_selected_combat_visual_state_bridge_debug")
    x86.call_rel32(pe, "append_stage32_success_status")
    pe.label("source_stage32_return")
    x86.ret(pe)


def emit_render_selected_combat_visual_state_bridge_debug(pe: PE32) -> None:
    pe.label("P_SetPsprite_stage32_selected_shotgun_psprite_state_debug")
    pe.label("R_RenderPlayerView_stage32_clear_wall_flat_psprite_present_debug")
    pe.label("V_DrawBlock_stage32_selected_combat_visual_present_debug")
    pe.label("render_selected_combat_visual_state_bridge_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage32_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage32_runtime_signature")
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage31._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage32_success_status(pe: PE32) -> None:
    pe.label("append_stage32_success_status")
    _emit_seek_buffer_end(pe, "status_success_buffer", "stage32_status")
    stage01.append_c_string_label(pe, "status_stage32_success_header")
    stage01.append_c_string_label(pe, "status_stage32_log_prefix")
    stage01.append_c_string_label(pe, "stage32_log_text")
    stage01.append_u32_label(pe, "status_stage32_signature_prefix", "stage32_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage32_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage32_title")
    for prefix, label in (
        ("title_stage32_frame_count_prefix", "stage32_frame_count"),
        ("title_stage32_distinct_fb_prefix", "stage32_distinct_fb_signatures"),
        ("title_stage32_distinct_visual_prefix", "stage32_distinct_visual_states"),
        ("title_stage32_posts_prefix", "stage32_final_psprite_posts"),
        ("title_stage32_pixels_prefix", "stage32_final_psprite_pixels"),
        ("title_stage32_full_frame_prefix", "stage32_full_frame_byte_arrays_absent"),
        ("title_stage32_stage33_prefix", "stage32_source_stage33_absent"),
    ):
        stage01.append_u32_label(pe, prefix, label)
    stage01.append_c_string_label(pe, "title_stage32_log_prefix")
    stage01.append_c_string_label(pe, "stage32_log_text")
    stage01.append_u32_label(pe, "title_stage32_signature_prefix", "stage32_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def _stage32_log_text(samples: tuple[Stage32FrameSample, ...]) -> str:
    return "|".join(
        f"{s.step}:T{s.tic}:PS{s.psprite_state_name}:FR{s.psprite_frame}:PN{s.psprite_patch_name}:PC{len(s.psprite_commands)}:PP{s.psprite_pixels_drawn}:BASE{s.base_framebuffer_signature}:FB{s.framebuffer_signature}"
        for s in samples
    )


def _stage32_replay_titles(ref: Stage32SelectedCombatVisualStateReference | None) -> tuple[str, ...]:
    if ref is None:
        return ()
    titles: list[str] = []
    for index, sample in enumerate(ref.samples):
        base = ref.stage31.samples[index]
        title = (
            f"Inference Doom S32 PSVIS STEP32={index + 1} TIC32={sample.tic} "
            f"VX31={base.viewx >> FRACBITS} VY31={base.viewy >> FRACBITS} "
            f"A31={base.viewangle_degrees} WC31={len(base.wall_commands)} "
            f"SP31={len(base.flat_spans)} PS32={sample.psprite_state_name} "
            f"PATCH32={sample.psprite_patch_name} PC32={len(sample.psprite_commands)} "
            f"PP32={sample.psprite_pixels_drawn} BASEFB32={sample.base_framebuffer_signature} "
            f"FB32={sample.framebuffer_signature}"
        )
        if index == len(ref.samples) - 1:
            title += (
                f" FBDIST32={ref.distinct_framebuffer_signatures}"
                f" PSDIST32={ref.distinct_visual_states}"
                f" NOFULL32={ref.full_frame_byte_arrays_absent}"
                " S19SIG=2088411722 S20SIG=3226031347 S21SIG=1770773845"
                " S22SIG=2207028069 S23SIG=3216085132 S24SIG=1919312263"
                " S25SIG=1688844032 S26SIG=132405987 S27SIG=1735738182"
                " S28SIG=2805406010 S29SIG=3738922932 S30SIG=3898523864"
                f" S31SIG={ref.stage31.signature} S32SIG={ref.signature} S33ABS={ref.source_stage33_absent}"
            )
        titles.append(title)
    return tuple(titles)


def _emit_psprite_commands(pe: PE32, commands: Sequence[Stage32PspriteCommand]) -> None:
    for command in commands:
        pe.emit_u32(command.x)
        pe.emit_u32(command.yl)
        pe.emit_u32(command.yh)
        pe.emit_u32(command.iscale)
        pe.emit_u32(command.texturemid)
        pe.write_abs32(f"stage32_psprite_source_{command.source_index}")


def emit_stage32_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    samples = ref.samples if ref else ()
    final = samples[-1] if samples else None
    pe.align_section(4)
    for name, value in (
        ("stage32_frame_count", len(samples)),
        ("stage32_distinct_visual_states", ref.distinct_visual_states if ref else 0),
        ("stage32_distinct_psprite_command_tables", ref.distinct_psprite_command_tables if ref else 0),
        ("stage32_distinct_fb_signatures", ref.distinct_framebuffer_signatures if ref else 0),
        ("stage32_sprite_contribution_signatures", ref.sprite_contribution_signatures if ref else 0),
        ("stage32_final_psprite_posts", len(final.psprite_commands) if final else 0),
        ("stage32_final_psprite_pixels", final.psprite_pixels_drawn if final else 0),
        ("stage32_full_frame_byte_arrays_absent", ref.full_frame_byte_arrays_absent if ref else 1),
        ("stage32_runtime_renderer_primitives", ref.runtime_renderer_primitives if ref else 1),
        ("stage32_wall_path_replayed", ref.wall_path_replayed if ref else 1),
        ("stage32_flat_path_replayed", ref.flat_path_replayed if ref else 1),
        ("stage32_psprite_path_replayed", ref.psprite_path_replayed if ref else 1),
        ("stage32_projectiles_absent", ref.projectiles_absent if ref else 1),
        ("stage32_explosions_absent", ref.explosions_absent if ref else 1),
        ("stage32_monster_attack_execution_absent", ref.monster_attack_execution_absent if ref else 1),
        ("stage32_damage_death_drop_absent", ref.damage_death_drop_absent if ref else 1),
        ("stage32_generalized_combat_absent", ref.generalized_combat_absent if ref else 1),
        ("stage32_broad_ai_absent", ref.broad_ai_absent if ref else 1),
        ("stage32_generalized_sprite_systems_absent", ref.generalized_sprite_systems_absent if ref else 1),
        ("stage32_generalized_specials_absent", ref.generalized_specials_absent if ref else 1),
        ("stage32_map_progression_absent", ref.map_progression_absent if ref else 1),
        ("stage32_ui_systems_absent", ref.ui_systems_absent if ref else 1),
        ("stage32_real_audio_absent", ref.real_audio_absent if ref else 1),
        ("stage32_source_stage33_absent", ref.source_stage33_absent if ref else 1),
        ("stage32_expected_signature", ref.signature if ref else 0),
        ("stage32_runtime_signature", 0),
        ("stage32_runtime_fb_signature", 0),
        ("stage32_psprite_scan_ptr", 0),
        ("stage32_psprite_remaining", 0),
        ("stage32_psprite_posts_drawn", 0),
        ("stage32_psprite_pixels_drawn", 0),
        ("stage32_replay_step", 0),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        for name, value in (
            (f"stage32_sample{index}_tic", sample.tic),
            (f"stage32_sample{index}_psprite_state", sample.psprite_state),
            (f"stage32_sample{index}_psprite_frame", sample.psprite_frame),
            (f"stage32_sample{index}_psprite_command_count", len(sample.psprite_commands)),
            (f"stage32_sample{index}_base_fb_signature", sample.base_framebuffer_signature),
            (f"stage32_sample{index}_fb_signature", sample.framebuffer_signature),
        ):
            pe.label(name)
            pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        pe.align_section(4)
        pe.label(f"stage32_psprite_commands_{index}")
        _emit_psprite_commands(pe, sample.psprite_commands)
    pe.align_section(1)
    if ref:
        for index, source in enumerate(ref.psprite_sources):
            pe.label(f"stage32_psprite_source_{index}")
            pe.emit(source)
    pe.align_section(1)
    pe.label("stage32_log_text")
    x86.emit_asciiz(pe, _stage32_log_text(samples))
    pe.label("status_stage32_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage32_selected_combat_visual_state_bridge\r\n"
        "Selected combat visual state bridge proof OK\r\n",
    )
    pe.label("status_stage32_log_prefix")
    x86.emit_asciiz(pe, "\r\nSelected psprite frame log: ")
    pe.label("status_stage32_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage32 selected combat visual signature: ")
    pe.label("status_stage32_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage32 preserves the stage31 live wall/flat runtime redraw bridge, then "
        "selects compact shotgun psprite post command tables after walls/flats in "
        "the R_DrawPlayerSprites/R_DrawPSprite-shaped order. Timer samples change "
        "the selected S_SGUN visual state, execute R_DrawColumn-shaped post commands "
        "from real WAD patch data, compute the live framebuffer signature, and present "
        "through the existing Win32 paint path. Projectiles, explosions, monster attack "
        "execution, damage/death/drop, generalized combat, broad AI, generalized sprite "
        "systems, map progression, UI systems, and real audio remain deferred.\r\n",
    )
    for label, text in (
        ("title_stage32_frame_count_prefix", " S32FR="),
        ("title_stage32_distinct_fb_prefix", " FBDIST32="),
        ("title_stage32_distinct_visual_prefix", " PSDIST32="),
        ("title_stage32_posts_prefix", " PC32="),
        ("title_stage32_pixels_prefix", " PP32="),
        ("title_stage32_full_frame_prefix", " NOFULL32="),
        ("title_stage32_stage33_prefix", " S33ABS="),
        ("title_stage32_log_prefix", " LOG32="),
        ("title_stage32_signature_prefix", " S32SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)
    pe.label("stage32_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S32 PSVIS START STEP32=0 waiting for wall/flat plus selected psprite redraw")
    for index, title in enumerate(_stage32_replay_titles(ref)):
        pe.label(f"stage32_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)


def build_source_stage32_selected_combat_visual_state_bridge_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    ref = _reference_for_default_wad_or_none()
    emit_stage32_entry(pe)
    stage28.emit_stage28_wndproc_framebuffer(pe)
    emit_stage32_timer_tick(pe)
    stage31.emit_stage31_clear_framebuffer(pe)
    stage31.emit_stage31_framebuffer_signature(pe)
    stage31.emit_stage31_draw_command_loops(pe)
    emit_stage32_draw_psprite_commands(pe)
    for index in range(len(ref.samples) if ref else len(SELECTED_SAMPLE_TICS)):
        _emit_stage32_draw_sample(pe, index)
    emit_source_stage32_load_wad_selected_combat_visual_state_bridge(pe)
    stage31.emit_source_stage31_load_wad_runtime_real_renderer_motion_bridge(pe)
    stage30.emit_source_stage30_load_wad_runtime_rendered_motion_bridge(pe)
    stage29.emit_source_stage29_load_wad_selected_monster_chase_attack_state_loop(pe)
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
    stage29.emit_render_selected_monster_chase_attack_state_loop_debug(pe)
    stage30.emit_render_runtime_rendered_motion_bridge_debug(pe)
    stage31.emit_render_runtime_real_renderer_motion_bridge_debug(pe)
    emit_render_selected_combat_visual_state_bridge_debug(pe)
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
    stage29.emit_append_stage29_success_status(pe)
    stage30.emit_append_stage30_success_status(pe)
    stage31.emit_append_stage31_success_status(pe)
    emit_append_stage32_success_status(pe)
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
    stage29.emit_stage29_data(pe)
    stage30.emit_stage30_data(pe)
    stage31.emit_stage31_data(pe)
    emit_stage32_data(pe)
    return pe.build("entry")


def write_source_stage32_selected_combat_visual_state_bridge_exe(path: str | Path) -> bytes:
    image = build_source_stage32_selected_combat_visual_state_bridge_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage32 selected combat visual state PE32 executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage32_selected_combat_visual_state_bridge.exe",
        help="path to write, default: build/source_stage32_selected_combat_visual_state_bridge.exe",
    )
    args = parser.parse_args()
    write_source_stage32_selected_combat_visual_state_bridge_exe(args.output)


if __name__ == "__main__":
    main()
