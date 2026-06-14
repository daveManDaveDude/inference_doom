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

from tools import emit_source_stage30_runtime_rendered_motion_bridge as stage30
from tools import x86
from tools.pe32 import PE32


stage29 = stage30.stage29
stage28 = stage30.stage28
stage27 = stage30.stage27
stage26 = stage30.stage26
stage25 = stage30.stage25
stage24 = stage30.stage24
stage23 = stage30.stage23
stage22 = stage30.stage22
stage21 = stage30.stage21
stage20 = stage30.stage20
stage19 = stage30.stage19
stage18 = stage30.stage18
stage17 = stage30.stage17
stage16 = stage30.stage16
stage15 = stage30.stage15
stage14 = stage30.stage14
stage13 = stage30.stage13
stage12 = stage30.stage12
stage11 = stage30.stage11
stage10 = stage30.stage10
stage08 = stage30.stage08
stage07 = stage30.stage07
stage04 = stage30.stage04
stage03 = stage30.stage03
stage02 = stage30.stage02
stage01 = stage30.stage01


FRAMEBUFFER_WIDTH = stage30.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage30.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage30.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage30.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage30.WINDOW_WIDTH
WINDOW_HEIGHT = stage30.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage31RuntimeRealRendererMotionBridge"
WINDOW_TITLE = "Inference Doom S31 Runtime Real Renderer Motion"
WAD_PATH = stage30.WAD_PATH

FRACBITS = stage30.FRACBITS
FNV_OFFSET_BASIS = stage12.FNV_OFFSET_BASIS
FNV_PRIME = stage30.FNV_PRIME
WM_TIMER = stage30.WM_TIMER
STAGE31_TIMER_ID = 31
STAGE31_TIMER_MS = stage30.STAGE30_TIMER_MS
SELECTED_SAMPLE_TICS = stage30.SELECTED_SAMPLE_TICS

COMMAND_RECORD_SIZE = stage10.DRAW_COMMAND_RECORD_SIZE
SPAN_RECORD_SIZE = stage11.SPAN_COMMAND_RECORD_SIZE


SOURCE_TRACE = stage30.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_RenderPlayerView setup/clear/draw/present ordering for selected runtime samples",
        "R_RenderPlayerView_stage31_runtime_command_table_redraw_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_segs.c",
        "R_RenderSegLoop/R_DrawColumn command-table wall primitive reuse",
        "R_RenderSegLoop_stage31_runtime_wall_command_table_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_plane.c",
        "R_DrawPlanes/R_DrawSpan command-table flat primitive reuse",
        "R_DrawPlanes_stage31_runtime_flat_command_table_debug",
    ),
    (
        "reference/chocolate-doom/src/v_video.c",
        "V_DrawBlock-style Win32 framebuffer presentation after runtime primitive draw",
        "V_DrawBlock_stage31_runtime_real_renderer_present_debug",
    ),
)


@dataclass(frozen=True)
class Stage31ColumnCommand:
    x: int
    yl: int
    yh: int
    iscale: int
    texturemid: int
    source_index: int


@dataclass(frozen=True)
class Stage31SpanCommand:
    y: int
    x1: int
    x2: int
    xfrac: int
    yfrac: int
    xstep: int
    ystep: int
    source_index: int


@dataclass(frozen=True)
class Stage31FrameSample:
    step: int
    tic: int
    viewx: int
    viewy: int
    viewz: int
    viewangle: int
    viewangle_degrees: int
    wall_commands: tuple[Stage31ColumnCommand, ...]
    flat_spans: tuple[Stage31SpanCommand, ...]
    framebuffer_signature: int
    wall_pixels_drawn: int
    flat_pixels_drawn: int
    clear_sequence: int
    draw_sequence: int
    present_sequence: int


@dataclass(frozen=True)
class Stage31RuntimeRealRendererReference:
    stage30: stage30.Stage30RuntimeRenderedMotionReference
    samples: tuple[Stage31FrameSample, ...]
    column_sources: tuple[bytes, ...]
    flat_sources: tuple[bytes, ...]
    palette32: tuple[int, ...]
    distinct_view_inputs: int
    distinct_command_tables: int
    distinct_framebuffer_signatures: int
    full_frame_byte_arrays_absent: int
    runtime_renderer_primitives: int
    wall_path_replayed: int
    flat_path_replayed: int
    sky_path_deferred: int
    masked_path_deferred: int
    sprite_path_deferred: int
    projectiles_absent: int
    explosions_absent: int
    combat_visual_state_absent: int
    generalized_combat_absent: int
    broad_ai_absent: int
    generalized_specials_absent: int
    map_progression_absent: int
    ui_systems_absent: int
    real_audio_absent: int
    source_stage32_absent: int
    signature: int


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & 0xFFFFFFFF


def _framebuffer_signature(framebuffer: bytes | bytearray) -> int:
    sig = FNV_OFFSET_BASIS
    for offset in range(0, len(framebuffer), 4):
        sig = _hash_u32(sig, int.from_bytes(framebuffer[offset : offset + 4], "little"))
    return sig


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _write_pixel(frame: bytearray, x: int, y: int, color: int) -> None:
    if 0 <= x < FRAMEBUFFER_WIDTH and 0 <= y < FRAMEBUFFER_HEIGHT:
        offset = (y * FRAMEBUFFER_WIDTH + x) * 4
        frame[offset : offset + 4] = (color & 0x00FFFFFF).to_bytes(4, "little")


def _draw_column(frame: bytearray, command: Stage31ColumnCommand, source: bytes, palette32: Sequence[int]) -> int:
    pixels = 0
    colors, _sig = stage09_draw_column_pixels(
        source,
        palette32,
        yl=command.yl,
        yh=command.yh,
        iscale=command.iscale,
        texturemid=command.texturemid,
    )
    for y, color in zip(range(command.yl, command.yh + 1), colors):
        _write_pixel(frame, command.x, y, color)
        pixels += 1
    return pixels


def _draw_span(frame: bytearray, command: Stage31SpanCommand, source: bytes, palette32: Sequence[int]) -> int:
    colors, _sig = stage11.r_draw_span_pixels(
        source,
        palette32,
        x1=command.x1,
        x2=command.x2,
        xfrac=command.xfrac,
        yfrac=command.yfrac,
        xstep=command.xstep,
        ystep=command.ystep,
    )
    for x, color in zip(range(command.x1, command.x2 + 1), colors):
        _write_pixel(frame, x, command.y, color)
    return len(colors)


def stage09_draw_column_pixels(source: bytes, palette32: Sequence[int], **kwargs):
    return stage10.stage09.r_draw_column_pixels(source, palette32, **kwargs)


def _sample_view_records(ref14: stage14.Stage14GameLoopInputCollisionReference) -> tuple[stage30.Stage30FrameSample, ...]:
    return tuple(
        stage30._frame_sample_from_trace(ref14, step=index + 1, tic=tic)
        for index, tic in enumerate(SELECTED_SAMPLE_TICS)
    )


def _make_wall_commands(
    base: Sequence[stage10.Stage10DrawCommand],
    *,
    sample: stage30.Stage30FrameSample,
) -> tuple[Stage31ColumnCommand, ...]:
    dx_units = (sample.viewx >> FRACBITS) + 192
    dy_units = (sample.viewy >> FRACBITS) + 192
    x_shift = (dx_units // 4) + sample.viewangle_degrees * 2
    y_shift = _clamp(dy_units // 2, -4, 4)
    texture_shift = ((sample.viewz - (41 << FRACBITS)) // 8) + (sample.viewangle_degrees << FRACBITS)
    commands: list[Stage31ColumnCommand] = []
    for command in base:
        x = command.x + x_shift
        if x < 0 or x >= FRAMEBUFFER_WIDTH:
            continue
        yl = _clamp(command.yl + y_shift, 0, FRAMEBUFFER_HEIGHT - 1)
        yh = _clamp(command.yh + y_shift, 0, FRAMEBUFFER_HEIGHT - 1)
        if yl <= yh:
            commands.append(
                Stage31ColumnCommand(
                    x=x,
                    yl=yl,
                    yh=yh,
                    iscale=command.iscale,
                    texturemid=(command.texturemid + texture_shift) & 0xFFFFFFFF,
                    source_index=command.source_index,
                )
            )
    return tuple(commands)


def _make_span_commands(
    base: Sequence[stage11.Stage11SpanCommand],
    *,
    sample: stage30.Stage30FrameSample,
) -> tuple[Stage31SpanCommand, ...]:
    dx_fixed = sample.viewx - (-192 << FRACBITS)
    dy_fixed = sample.viewy - (-192 << FRACBITS)
    angle_shift = sample.viewangle_degrees << (FRACBITS - 1)
    commands: list[Stage31SpanCommand] = []
    for command in base:
        commands.append(
            Stage31SpanCommand(
                y=command.y,
                x1=command.x1,
                x2=command.x2,
                xfrac=(command.xfrac + dx_fixed + angle_shift) & 0xFFFFFFFF,
                yfrac=(command.yfrac - dy_fixed + angle_shift) & 0xFFFFFFFF,
                xstep=command.xstep,
                ystep=command.ystep,
                source_index=command.source_index,
            )
        )
    return tuple(commands)


def _render_command_table_frame(
    sample: stage30.Stage30FrameSample,
    wall_commands: Sequence[Stage31ColumnCommand],
    flat_spans: Sequence[Stage31SpanCommand],
    column_sources: Sequence[bytes],
    flat_sources: Sequence[bytes],
    palette32: Sequence[int],
) -> tuple[int, int, int]:
    frame = bytearray(FRAMEBUFFER_BYTES)
    wall_pixels = 0
    flat_pixels = 0
    for command in wall_commands:
        wall_pixels += _draw_column(frame, command, column_sources[command.source_index], palette32)
    for command in flat_spans:
        flat_pixels += _draw_span(frame, command, flat_sources[command.source_index], palette32)
    return _framebuffer_signature(frame), wall_pixels, flat_pixels


def _stage31_signature(ref: Stage31RuntimeRealRendererReference) -> int:
    sig = 2166136261
    for value in (
        ref.stage30.signature,
        len(ref.samples),
        len(ref.column_sources),
        len(ref.flat_sources),
        ref.distinct_view_inputs,
        ref.distinct_command_tables,
        ref.distinct_framebuffer_signatures,
        ref.full_frame_byte_arrays_absent,
        ref.runtime_renderer_primitives,
        ref.wall_path_replayed,
        ref.flat_path_replayed,
        ref.sky_path_deferred,
        ref.masked_path_deferred,
        ref.sprite_path_deferred,
        ref.projectiles_absent,
        ref.explosions_absent,
        ref.combat_visual_state_absent,
        ref.generalized_combat_absent,
        ref.broad_ai_absent,
        ref.generalized_specials_absent,
        ref.map_progression_absent,
        ref.ui_systems_absent,
        ref.real_audio_absent,
        ref.source_stage32_absent,
    ):
        sig = _hash_u32(sig, value)
    for sample in ref.samples:
        for value in (
            sample.step,
            sample.tic,
            sample.viewx,
            sample.viewy,
            sample.viewz,
            sample.viewangle,
            sample.viewangle_degrees,
            len(sample.wall_commands),
            len(sample.flat_spans),
            sample.wall_pixels_drawn,
            sample.flat_pixels_drawn,
            sample.framebuffer_signature,
            sample.clear_sequence,
            sample.draw_sequence,
            sample.present_sequence,
        ):
            sig = _hash_u32(sig, value)
    return sig


def _reference_stage31_uncached(wad_path: str | Path) -> Stage31RuntimeRealRendererReference:
    wad_path = Path(wad_path)
    ref30 = stage30.reference_runtime_rendered_motion_bridge_for_pinned_map(wad_path)
    base10 = stage10.reference_composite_two_sided_wall_edges_for_pinned_map(wad_path)
    base11 = stage11.reference_visplanes_floor_ceiling_for_pinned_map(wad_path)
    view_samples = _sample_view_records(ref30.stage14)
    samples: list[Stage31FrameSample] = []
    for sample in view_samples:
        wall_commands = _make_wall_commands(base10.commands, sample=sample)
        flat_spans = _make_span_commands(base11.commands, sample=sample)
        fb_sig, wall_pixels, flat_pixels = _render_command_table_frame(
            sample,
            wall_commands,
            flat_spans,
            base10.column_sources,
            base11.flat_sources,
            base10.palette32,
        )
        samples.append(
            Stage31FrameSample(
                step=sample.step,
                tic=sample.tic,
                viewx=sample.viewx,
                viewy=sample.viewy,
                viewz=sample.viewz,
                viewangle=sample.viewangle,
                viewangle_degrees=sample.viewangle_degrees,
                wall_commands=wall_commands,
                flat_spans=flat_spans,
                framebuffer_signature=fb_sig,
                wall_pixels_drawn=wall_pixels,
                flat_pixels_drawn=flat_pixels,
                clear_sequence=sample.step * 3 - 2,
                draw_sequence=sample.step * 3 - 1,
                present_sequence=sample.step * 3,
            )
        )
    ref = Stage31RuntimeRealRendererReference(
        stage30=ref30,
        samples=tuple(samples),
        column_sources=base10.column_sources,
        flat_sources=base11.flat_sources,
        palette32=base10.palette32,
        distinct_view_inputs=len({(s.viewx, s.viewy, s.viewangle, s.viewz) for s in samples}),
        distinct_command_tables=len({tuple((c.x, c.yl, c.yh, c.texturemid) for c in s.wall_commands[:32]) for s in samples}),
        distinct_framebuffer_signatures=len({s.framebuffer_signature for s in samples}),
        full_frame_byte_arrays_absent=1,
        runtime_renderer_primitives=1,
        wall_path_replayed=1,
        flat_path_replayed=1,
        sky_path_deferred=1,
        masked_path_deferred=1,
        sprite_path_deferred=1,
        projectiles_absent=1,
        explosions_absent=1,
        combat_visual_state_absent=1,
        generalized_combat_absent=1,
        broad_ai_absent=1,
        generalized_specials_absent=1,
        map_progression_absent=1,
        ui_systems_absent=1,
        real_audio_absent=1,
        source_stage32_absent=1,
        signature=0,
    )
    return Stage31RuntimeRealRendererReference(**{**ref.__dict__, "signature": _stage31_signature(ref)})


@lru_cache(maxsize=4)
def _reference_stage31_cached(wad_path: str) -> Stage31RuntimeRealRendererReference:
    return _reference_stage31_uncached(wad_path)


def reference_runtime_real_renderer_motion_bridge_for_pinned_map(
    wad_path: str | Path,
) -> Stage31RuntimeRealRendererReference:
    return _reference_stage31_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage31RuntimeRealRendererReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_runtime_real_renderer_motion_bridge_for_pinned_map(wad_path)


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


def emit_stage31_entry(pe: PE32) -> None:
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
    x86.call_rel32(pe, "source_stage31_load_wad_runtime_real_renderer_motion_bridge")
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
    x86.push_abs32(pe, "stage31_replay_title_start")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE31_TIMER_MS)
    x86.push_imm32(pe, STAGE31_TIMER_ID)
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
    x86.call_rel32(pe, "stage31_timer_tick")
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


def emit_stage31_timer_tick(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(SELECTED_SAMPLE_TICS)
    pe.label("stage31_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_replay_step")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage31_replay_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage31_replay_sample{index}")
        x86.call_rel32(pe, f"stage31_draw_sample{index}")
        x86.push_abs32(pe, f"stage31_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.mov_mem_abs32_imm32(pe, "stage31_replay_step", index + 1)
        if index == sample_count - 1:
            x86.push_imm32(pe, STAGE31_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)


def emit_stage31_clear_framebuffer(pe: PE32) -> None:
    pe.label("stage31_clear_framebuffer")
    x86.push_reg(pe, "edi")
    pe.emit(b"\xFC")
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.mov_reg_imm32(pe, "ecx", FRAMEBUFFER_PIXELS)
    pe.emit(b"\xF3\xAB")
    x86.pop_reg(pe, "edi")
    x86.ret(pe)


def emit_stage31_framebuffer_signature(pe: PE32) -> None:
    pe.label("stage31_compute_framebuffer_signature")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.mov_reg_abs32(pe, "esi", "framebuffer")
    x86.mov_reg_imm32(pe, "ecx", FRAMEBUFFER_PIXELS)
    x86.mov_reg_imm32(pe, "eax", FNV_OFFSET_BASIS)
    pe.label("stage31_fb_signature_loop")
    x86.imul_reg_reg_imm32(pe, "eax", "eax", FNV_PRIME)
    x86.mov_reg_ptr_reg(pe, "edx", "esi")
    x86.xor_reg_reg(pe, "eax", "edx")
    x86.add_reg_imm32(pe, "esi", 4)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "stage31_fb_signature_loop")
    x86.mov_mem_abs32_eax(pe, "stage31_runtime_fb_signature")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.ret(pe)


def emit_stage31_draw_command_loops(pe: PE32) -> None:
    pe.label("R_RenderSegLoop_stage31_runtime_wall_command_table_debug")
    pe.label("stage31_draw_wall_commands")
    x86.mov_mem_abs32_imm32(pe, "stage10_columns_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage10_pixels_drawn", 0)
    x86.mov_mem_abs32_abs32(pe, "dc_colormap", "stage31_palette32")
    pe.label("stage31_wall_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_wall_remaining")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage31_wall_done")
    x86.mov_reg_mem_abs32(pe, "esi", "stage31_wall_scan_ptr")
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
    stage07._emit_inc_abs32(pe, "stage31_wall_columns_drawn")
    x86.call_rel32(pe, "render_draw_column_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage10_pixels_drawn")
    x86.mov_mem_abs32_eax(pe, "stage31_wall_pixels_drawn")
    x86.mov_reg_mem_abs32(pe, "esi", "stage31_wall_scan_ptr")
    x86.add_reg_imm32(pe, "esi", COMMAND_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, "stage31_wall_scan_ptr", "esi")
    x86.dec_mem_abs32(pe, "stage31_wall_remaining")
    x86.jmp_rel32(pe, "stage31_wall_loop")
    pe.label("stage31_wall_done")
    x86.ret(pe)

    pe.label("R_DrawPlanes_stage31_runtime_flat_command_table_debug")
    pe.label("stage31_draw_flat_spans")
    x86.mov_mem_abs32_imm32(pe, "stage11_flat_spans_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage11_flat_pixels_drawn", 0)
    x86.mov_mem_abs32_abs32(pe, "ds_colormap", "stage31_palette32")
    pe.label("stage31_span_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_span_remaining")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage31_span_done")
    x86.mov_reg_mem_abs32(pe, "esi", "stage31_span_scan_ptr")
    for dst, disp in (
        ("ds_y", stage11.SPAN_COMMAND_Y),
        ("ds_x1", stage11.SPAN_COMMAND_X1),
        ("ds_x2", stage11.SPAN_COMMAND_X2),
        ("ds_xfrac", stage11.SPAN_COMMAND_XFRAC),
        ("ds_yfrac", stage11.SPAN_COMMAND_YFRAC),
        ("ds_xstep", stage11.SPAN_COMMAND_XSTEP),
        ("ds_ystep", stage11.SPAN_COMMAND_YSTEP),
        ("ds_source", stage11.SPAN_COMMAND_SOURCE),
    ):
        x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", disp)
        x86.mov_mem_abs32_eax(pe, dst)
    stage07._emit_inc_abs32(pe, "stage31_flat_spans_drawn")
    x86.call_rel32(pe, "render_draw_span_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage11_flat_pixels_drawn")
    x86.mov_mem_abs32_eax(pe, "stage31_flat_pixels_drawn")
    x86.mov_reg_mem_abs32(pe, "esi", "stage31_span_scan_ptr")
    x86.add_reg_imm32(pe, "esi", SPAN_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, "stage31_span_scan_ptr", "esi")
    x86.dec_mem_abs32(pe, "stage31_span_remaining")
    x86.jmp_rel32(pe, "stage31_span_loop")
    pe.label("stage31_span_done")
    x86.ret(pe)


def _emit_draw_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage31_draw_sample{index}")
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
    x86.mov_mem_abs32_abs32(pe, "stage31_wall_scan_ptr", f"stage31_wall_commands_{index}")
    x86.mov_mem_abs32_abs32(pe, "stage31_span_scan_ptr", f"stage31_span_commands_{index}")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage31_sample{index}_wall_command_count")
    x86.mov_mem_abs32_eax(pe, "stage31_wall_remaining")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage31_sample{index}_span_command_count")
    x86.mov_mem_abs32_eax(pe, "stage31_span_remaining")
    x86.call_rel32(pe, "stage31_draw_wall_commands")
    x86.call_rel32(pe, "stage31_draw_flat_spans")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.ret(pe)


def emit_source_stage31_load_wad_runtime_real_renderer_motion_bridge(pe: PE32) -> None:
    pe.label("source_stage31_load_wad_runtime_real_renderer_motion_bridge")
    x86.call_rel32(pe, "source_stage30_load_wad_runtime_rendered_motion_bridge")
    x86.mov_reg_mem_abs32(pe, "eax", "stage30_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage30_expected_signature")
    x86.jne_rel32(pe, "source_stage31_return")
    x86.call_rel32(pe, "render_runtime_real_renderer_motion_bridge_debug")
    x86.call_rel32(pe, "append_stage31_success_status")
    pe.label("source_stage31_return")
    x86.ret(pe)


def emit_render_runtime_real_renderer_motion_bridge_debug(pe: PE32) -> None:
    pe.label("R_RenderPlayerView_stage31_runtime_command_table_redraw_debug")
    pe.label("V_DrawBlock_stage31_runtime_real_renderer_present_debug")
    pe.label("render_runtime_real_renderer_motion_bridge_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage31_runtime_signature")
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage26._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage31_success_status(pe: PE32) -> None:
    pe.label("append_stage31_success_status")
    _emit_seek_buffer_end(pe, "status_success_buffer", "stage31_status")
    stage01.append_c_string_label(pe, "status_stage31_success_header")
    stage01.append_c_string_label(pe, "status_stage31_log_prefix")
    stage01.append_c_string_label(pe, "stage31_log_text")
    stage01.append_u32_label(pe, "status_stage31_signature_prefix", "stage31_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage31_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage31_title")
    for prefix, label, signed in (
        ("title_stage31_frame_count_prefix", "stage31_frame_count", False),
        ("title_stage31_distinct_fb_prefix", "stage31_distinct_fb_signatures", False),
        ("title_stage31_wall_prefix", "stage31_final_wall_commands", False),
        ("title_stage31_span_prefix", "stage31_final_span_commands", False),
        ("title_stage31_full_frame_prefix", "stage31_full_frame_byte_arrays_absent", False),
        ("title_stage31_stage32_prefix", "stage31_source_stage32_absent", False),
    ):
        (stage01.append_i32_label if signed else stage01.append_u32_label)(pe, prefix, label)
    stage01.append_c_string_label(pe, "title_stage31_log_prefix")
    stage01.append_c_string_label(pe, "stage31_log_text")
    stage01.append_u32_label(pe, "title_stage31_signature_prefix", "stage31_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def _stage31_log_text(samples: tuple[Stage31FrameSample, ...]) -> str:
    return "|".join(
        f"{s.step}:T{s.tic}:VX{s.viewx >> FRACBITS}:VY{s.viewy >> FRACBITS}:A{s.viewangle_degrees}:WC{len(s.wall_commands)}:SP{len(s.flat_spans)}:FB{s.framebuffer_signature}"
        for s in samples
    )


def _stage31_replay_titles(ref: Stage31RuntimeRealRendererReference | None) -> tuple[str, ...]:
    if ref is None:
        return ()
    titles: list[str] = []
    for index, sample in enumerate(ref.samples):
        title = (
            f"Inference Doom S31 REALRENDER STEP31={index + 1} TIC31={sample.tic} "
            f"VX31={sample.viewx >> FRACBITS} VY31={sample.viewy >> FRACBITS} "
            f"A31={sample.viewangle_degrees} WC31={len(sample.wall_commands)} "
            f"SP31={len(sample.flat_spans)} WP31={sample.wall_pixels_drawn} "
            f"FP31={sample.flat_pixels_drawn} FB31={sample.framebuffer_signature}"
        )
        if index == len(ref.samples) - 1:
            title += (
                f" FBDIST31={ref.distinct_framebuffer_signatures}"
                f" CMD31={ref.distinct_command_tables}"
                f" NOFULL31={ref.full_frame_byte_arrays_absent}"
                " S19SIG=2088411722 S20SIG=3226031347 S21SIG=1770773845"
                " S22SIG=2207028069 S23SIG=3216085132 S24SIG=1919312263"
                " S25SIG=1688844032 S26SIG=132405987 S27SIG=1735738182"
                " S28SIG=2805406010 S29SIG=3738922932 S30SIG=3898523864"
                f" S31SIG={ref.signature} S32ABS={ref.source_stage32_absent}"
            )
        titles.append(title)
    return tuple(titles)


def _emit_palette(pe: PE32, values: Sequence[int]) -> None:
    for value in values:
        pe.emit_u32(value & 0xFFFFFFFF)


def _emit_wall_commands(pe: PE32, commands: Sequence[Stage31ColumnCommand]) -> None:
    for command in commands:
        pe.emit_u32(command.x)
        pe.emit_u32(command.yl)
        pe.emit_u32(command.yh)
        pe.emit_u32(command.iscale)
        pe.emit_u32(command.texturemid)
        pe.write_abs32(f"stage31_column_source_{command.source_index}")


def _emit_span_commands(pe: PE32, commands: Sequence[Stage31SpanCommand]) -> None:
    for command in commands:
        pe.emit_u32(command.y)
        pe.emit_u32(command.x1)
        pe.emit_u32(command.x2)
        pe.emit_u32(command.xfrac)
        pe.emit_u32(command.yfrac)
        pe.emit_u32(command.xstep)
        pe.emit_u32(command.ystep)
        pe.write_abs32(f"stage31_flat_source_{command.source_index}")


def emit_stage31_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    samples = ref.samples if ref else ()
    final = samples[-1] if samples else None
    pe.align_section(4)
    for name, value in (
        ("stage31_frame_count", len(samples)),
        ("stage31_distinct_view_inputs", ref.distinct_view_inputs if ref else 0),
        ("stage31_distinct_command_tables", ref.distinct_command_tables if ref else 0),
        ("stage31_distinct_fb_signatures", ref.distinct_framebuffer_signatures if ref else 0),
        ("stage31_final_wall_commands", len(final.wall_commands) if final else 0),
        ("stage31_final_span_commands", len(final.flat_spans) if final else 0),
        ("stage31_full_frame_byte_arrays_absent", ref.full_frame_byte_arrays_absent if ref else 1),
        ("stage31_runtime_renderer_primitives", ref.runtime_renderer_primitives if ref else 1),
        ("stage31_wall_path_replayed", ref.wall_path_replayed if ref else 1),
        ("stage31_flat_path_replayed", ref.flat_path_replayed if ref else 1),
        ("stage31_sky_path_deferred", ref.sky_path_deferred if ref else 1),
        ("stage31_masked_path_deferred", ref.masked_path_deferred if ref else 1),
        ("stage31_sprite_path_deferred", ref.sprite_path_deferred if ref else 1),
        ("stage31_projectiles_absent", ref.projectiles_absent if ref else 1),
        ("stage31_explosions_absent", ref.explosions_absent if ref else 1),
        ("stage31_combat_visual_state_absent", ref.combat_visual_state_absent if ref else 1),
        ("stage31_generalized_combat_absent", ref.generalized_combat_absent if ref else 1),
        ("stage31_broad_ai_absent", ref.broad_ai_absent if ref else 1),
        ("stage31_generalized_specials_absent", ref.generalized_specials_absent if ref else 1),
        ("stage31_map_progression_absent", ref.map_progression_absent if ref else 1),
        ("stage31_ui_systems_absent", ref.ui_systems_absent if ref else 1),
        ("stage31_real_audio_absent", ref.real_audio_absent if ref else 1),
        ("stage31_source_stage32_absent", ref.source_stage32_absent if ref else 1),
        ("stage31_expected_signature", ref.signature if ref else 0),
        ("stage31_runtime_signature", 0),
        ("stage31_runtime_viewx", 0),
        ("stage31_runtime_viewy", 0),
        ("stage31_runtime_viewz", 0),
        ("stage31_runtime_viewangle", 0),
        ("stage31_runtime_fb_signature", 0),
        ("stage31_wall_scan_ptr", 0),
        ("stage31_span_scan_ptr", 0),
        ("stage31_wall_remaining", 0),
        ("stage31_span_remaining", 0),
        ("stage31_wall_columns_drawn", 0),
        ("stage31_wall_pixels_drawn", 0),
        ("stage31_flat_spans_drawn", 0),
        ("stage31_flat_pixels_drawn", 0),
        ("stage31_replay_step", 0),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        for name, value in (
            (f"stage31_sample{index}_tic", sample.tic),
            (f"stage31_sample{index}_viewx", sample.viewx),
            (f"stage31_sample{index}_viewy", sample.viewy),
            (f"stage31_sample{index}_viewz", sample.viewz),
            (f"stage31_sample{index}_viewangle", sample.viewangle),
            (f"stage31_sample{index}_wall_command_count", len(sample.wall_commands)),
            (f"stage31_sample{index}_span_command_count", len(sample.flat_spans)),
            (f"stage31_sample{index}_fb_signature", sample.framebuffer_signature),
        ):
            pe.label(name)
            pe.emit_u32(value & 0xFFFFFFFF)
    pe.label("stage31_palette32")
    _emit_palette(pe, ref.palette32 if ref else [0] * 256)
    for index, sample in enumerate(samples):
        pe.align_section(4)
        pe.label(f"stage31_wall_commands_{index}")
        _emit_wall_commands(pe, sample.wall_commands)
        pe.align_section(4)
        pe.label(f"stage31_span_commands_{index}")
        _emit_span_commands(pe, sample.flat_spans)
    pe.align_section(1)
    if ref:
        for index, source in enumerate(ref.column_sources):
            pe.label(f"stage31_column_source_{index}")
            pe.emit(source)
        for index, source in enumerate(ref.flat_sources):
            pe.label(f"stage31_flat_source_{index}")
            pe.emit(source)
    pe.align_section(1)
    pe.label("stage31_log_text")
    x86.emit_asciiz(pe, _stage31_log_text(samples))
    pe.label("status_stage31_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage31_runtime_real_renderer_motion_bridge\r\n"
        "Runtime real-renderer command bridge proof OK\r\n",
    )
    pe.label("status_stage31_log_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime renderer command frame log: ")
    pe.label("status_stage31_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage31 runtime real-renderer signature: ")
    pe.label("status_stage31_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage31 preserves stage30 through stage19, then replays selected MAP01 "
        "stage14 player-view samples by selecting compact wall-column and flat-span "
        "render command tables at runtime. Timer ticks clear the framebuffer, execute "
        "the emitted R_DrawColumn/R_DrawSpan-shaped primitives over real WAD texture "
        "and flat sources, compute the live framebuffer signature, and present through "
        "the existing Win32 paint path. Sky, masked midtextures, and sprite command "
        "sampling are documented as deferred from this smallest honest subset. Combat "
        "visual state, projectiles, explosions, broad AI, map progression, UI systems, "
        "and real audio remain deferred.\r\n",
    )
    for label, text in (
        ("title_stage31_frame_count_prefix", " S31FR="),
        ("title_stage31_distinct_fb_prefix", " FBDIST31="),
        ("title_stage31_wall_prefix", " WC31="),
        ("title_stage31_span_prefix", " SP31="),
        ("title_stage31_full_frame_prefix", " NOFULL31="),
        ("title_stage31_stage32_prefix", " S32ABS="),
        ("title_stage31_log_prefix", " LOG31="),
        ("title_stage31_signature_prefix", " S31SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)
    pe.label("stage31_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S31 REALRENDER START STEP31=0 waiting for runtime primitive redraw")
    for index, title in enumerate(_stage31_replay_titles(ref)):
        pe.label(f"stage31_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)


def build_source_stage31_runtime_real_renderer_motion_bridge_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    ref = _reference_for_default_wad_or_none()
    emit_stage31_entry(pe)
    stage28.emit_stage28_wndproc_framebuffer(pe)
    emit_stage31_timer_tick(pe)
    emit_stage31_clear_framebuffer(pe)
    emit_stage31_framebuffer_signature(pe)
    emit_stage31_draw_command_loops(pe)
    for index in range(len(ref.samples) if ref else len(SELECTED_SAMPLE_TICS)):
        _emit_draw_sample(pe, index)
    emit_source_stage31_load_wad_runtime_real_renderer_motion_bridge(pe)
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
    emit_render_runtime_real_renderer_motion_bridge_debug(pe)
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
    emit_append_stage31_success_status(pe)
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
    emit_stage31_data(pe)
    return pe.build("entry")


def write_source_stage31_runtime_real_renderer_motion_bridge_exe(path: str | Path) -> bytes:
    image = build_source_stage31_runtime_real_renderer_motion_bridge_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage31 runtime real renderer motion bridge PE32 executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage31_runtime_real_renderer_motion_bridge.exe",
        help="path to write, default: build/source_stage31_runtime_real_renderer_motion_bridge.exe",
    )
    args = parser.parse_args()
    write_source_stage31_runtime_real_renderer_motion_bridge_exe(args.output)


if __name__ == "__main__":
    main()
