from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage29_selected_monster_chase_attack_state_loop as stage29
from tools import x86
from tools.pe32 import PE32


stage28 = stage29.stage28
stage27 = stage29.stage27
stage26 = stage29.stage26
stage25 = stage29.stage25
stage24 = stage29.stage24
stage23 = stage29.stage23
stage22 = stage29.stage22
stage21 = stage29.stage21
stage20 = stage29.stage20
stage19 = stage29.stage19
stage18 = stage29.stage18
stage17 = stage29.stage17
stage16 = stage29.stage16
stage15 = stage29.stage15
stage14 = stage29.stage14
stage13 = stage29.stage13
stage12 = stage29.stage12
stage11 = stage29.stage11
stage10 = stage29.stage10
stage08 = stage29.stage08
stage07 = stage29.stage07
stage04 = stage29.stage04
stage03 = stage29.stage03
stage02 = stage29.stage02
stage01 = stage29.stage01


FRAMEBUFFER_WIDTH = stage29.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage29.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage29.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage29.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage29.WINDOW_WIDTH
WINDOW_HEIGHT = stage29.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage30RuntimeRenderedMotionBridge"
WINDOW_TITLE = "Inference Doom S30 Runtime Rendered Motion"
WAD_PATH = stage29.WAD_PATH

FRACBITS = stage29.FRACBITS
FRACUNIT = stage29.FRACUNIT
FNV_OFFSET_BASIS = stage12.FNV_OFFSET_BASIS
FNV_PRIME = stage29.FNV_PRIME
WM_TIMER = stage29.WM_TIMER
STAGE30_TIMER_ID = 30
STAGE30_TIMER_MS = stage29.STAGE29_TIMER_MS
SELECTED_SAMPLE_TICS = (0, 4, 7)


SOURCE_TRACE = stage29.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/g_game.c",
        "G_Ticker selected deterministic MAP01 movement replay samples",
        "G_Ticker_stage30_selected_motion_replay_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_user.c",
        "P_PlayerThink/P_MovePlayer/P_Thrust selected stage14 route",
        "P_PlayerThink_stage30_motion_view_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_SetupFrame viewx/viewy/viewangle/viewz copy into render inputs",
        "R_SetupFrame_stage30_runtime_view_copy_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_RenderPlayerView clear, BSP/walls/flats/masked/sprites ordering boundary",
        "R_RenderPlayerView_stage30_runtime_redraw_bridge_debug",
    ),
    (
        "reference/chocolate-doom/src/v_video.c",
        "V_DrawBlock/V_UseBuffer-style framebuffer bytes presented by Win32 paint",
        "V_DrawBlock_stage30_framebuffer_present_debug",
    ),
)


@dataclass(frozen=True)
class Stage30FrameSample:
    step: int
    tic: int
    viewx: int
    viewy: int
    viewz: int
    viewangle: int
    viewangle_degrees: int
    viewcos: int
    viewsin: int
    subsector: int
    sector: int
    framebuffer_signature: int
    pixels_drawn: int
    clear_sequence: int
    redraw_sequence: int
    framebuffer: bytes


@dataclass(frozen=True)
class Stage30RuntimeRenderedMotionReference:
    stage29: stage29.Stage29SelectedMonsterLoopReference
    stage14: stage14.Stage14GameLoopInputCollisionReference
    samples: tuple[Stage30FrameSample, ...]
    distinct_view_inputs: int
    distinct_framebuffer_signatures: int
    replay_frame_count: int
    projectiles_absent: int
    explosions_absent: int
    generalized_combat_absent: int
    broad_ai_absent: int
    generalized_specials_absent: int
    map_progression_absent: int
    ui_systems_absent: int
    real_audio_absent: int
    source_stage31_absent: int
    signature: int


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & 0xFFFFFFFF


def _hash_bytes(signature: int, data: bytes) -> int:
    for byte in data:
        signature = _hash_u32(signature, byte)
    return signature


def _framebuffer_signature(framebuffer: bytes) -> int:
    sig = FNV_OFFSET_BASIS
    for offset in range(0, len(framebuffer), 4):
        color = int.from_bytes(framebuffer[offset : offset + 4], "little")
        sig = _hash_u32(sig, color)
    return sig


def _put_pixel(frame: bytearray, x: int, y: int, color: int) -> None:
    if 0 <= x < FRAMEBUFFER_WIDTH and 0 <= y < FRAMEBUFFER_HEIGHT:
        offset = (y * FRAMEBUFFER_WIDTH + x) * 4
        frame[offset : offset + 4] = (color & 0x00FFFFFF).to_bytes(4, "little")


def _render_motion_debug_frame(
    *,
    step: int,
    viewx: int,
    viewy: int,
    viewz: int,
    viewangle_degrees: int,
) -> tuple[bytes, int]:
    frame = bytearray(FRAMEBUFFER_BYTES)
    x_units = viewx >> FRACBITS
    y_units = viewy >> FRACBITS
    horizon = 92 + ((viewz >> 13) & 7)

    for y in range(FRAMEBUFFER_HEIGHT):
        if y < horizon:
            shade = 38 + ((horizon - y) // 5)
            color = (shade << 16) | ((shade + 8) << 8) | (shade + 24)
        else:
            shade = 28 + ((y - horizon) // 4)
            color = ((shade + 12) << 16) | (shade << 8) | (shade // 2)
        row = color.to_bytes(4, "little") * FRAMEBUFFER_WIDTH
        start = y * FRAMEBUFFER_WIDTH * 4
        frame[start : start + FRAMEBUFFER_WIDTH * 4] = row

    phase = (x_units * 7 + y_units * 3 + viewangle_degrees * 11) & 0x7F
    for x in range(FRAMEBUFFER_WIDTH):
        column = (x + phase) & 0x7F
        perspective = abs(x - FRAMEBUFFER_WIDTH // 2)
        top = 26 + ((column * 5 + step * 13) & 31) + perspective // 16
        bottom = 174 - ((column * 3 + step * 7) & 23) - perspective // 22
        if top >= bottom:
            continue
        for y in range(max(0, top), min(FRAMEBUFFER_HEIGHT, bottom)):
            stripe = ((column >> 3) ^ (y >> 4) ^ step) & 3
            red = 86 + stripe * 28
            green = 60 + ((column + y + step * 17) & 31)
            blue = 42 + ((viewangle_degrees + y) & 15)
            _put_pixel(frame, x, y, (red << 16) | (green << 8) | blue)

    marker_x = 14 + step * 18
    marker_y = 12
    marker_color = 0xF4D35E
    for y in range(marker_y, marker_y + 10):
        for x in range(marker_x, marker_x + 28):
            if x in (marker_x, marker_x + 27) or y in (marker_y, marker_y + 9):
                _put_pixel(frame, x, y, marker_color)

    return bytes(frame), FRAMEBUFFER_PIXELS


def _frame_sample_from_trace(
    ref14: stage14.Stage14GameLoopInputCollisionReference,
    *,
    step: int,
    tic: int,
) -> Stage30FrameSample:
    trace = next(record for record in ref14.trace if record.tic == tic)
    subsector, sector = ref14.frame.subsector, ref14.frame.sector
    angle = (trace.angle_degrees * 0x100000000 // 360) & 0xFFFFFFFF
    fine = stage14.fine_index(angle)
    framebuffer, pixels = _render_motion_debug_frame(
        step=step,
        viewx=trace.x,
        viewy=trace.y,
        viewz=trace.viewz,
        viewangle_degrees=trace.angle_degrees,
    )
    return Stage30FrameSample(
        step=step,
        tic=tic,
        viewx=trace.x,
        viewy=trace.y,
        viewz=trace.viewz,
        viewangle=angle,
        viewangle_degrees=trace.angle_degrees,
        viewcos=stage14.FINECOSINE[fine],
        viewsin=stage14.FINESINE[fine],
        subsector=subsector,
        sector=sector,
        framebuffer_signature=_framebuffer_signature(framebuffer),
        pixels_drawn=pixels,
        clear_sequence=step * 2 - 1,
        redraw_sequence=step * 2,
        framebuffer=framebuffer,
    )


def _stage30_signature(ref: Stage30RuntimeRenderedMotionReference) -> int:
    sig = 2166136261
    for value in (
        ref.stage29.signature,
        ref.stage14.signature,
        ref.replay_frame_count,
        ref.distinct_view_inputs,
        ref.distinct_framebuffer_signatures,
        ref.projectiles_absent,
        ref.explosions_absent,
        ref.generalized_combat_absent,
        ref.broad_ai_absent,
        ref.generalized_specials_absent,
        ref.map_progression_absent,
        ref.ui_systems_absent,
        ref.real_audio_absent,
        ref.source_stage31_absent,
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
            sample.viewcos,
            sample.viewsin,
            sample.subsector,
            sample.sector,
            sample.framebuffer_signature,
            sample.pixels_drawn,
            sample.clear_sequence,
            sample.redraw_sequence,
        ):
            sig = _hash_u32(sig, value)
    return sig


def _reference_stage30_uncached(wad_path: str | Path) -> Stage30RuntimeRenderedMotionReference:
    wad_path = Path(wad_path)
    ref29 = stage29.reference_selected_monster_chase_attack_state_loop_for_pinned_map(wad_path)
    ref14 = stage14.reference_game_loop_input_collision_for_pinned_map(wad_path)
    samples = tuple(
        _frame_sample_from_trace(ref14, step=index + 1, tic=tic)
        for index, tic in enumerate(SELECTED_SAMPLE_TICS)
    )
    ref = Stage30RuntimeRenderedMotionReference(
        stage29=ref29,
        stage14=ref14,
        samples=samples,
        distinct_view_inputs=len({(s.viewx, s.viewy, s.viewangle, s.viewz) for s in samples}),
        distinct_framebuffer_signatures=len({s.framebuffer_signature for s in samples}),
        replay_frame_count=len(samples),
        projectiles_absent=1,
        explosions_absent=1,
        generalized_combat_absent=1,
        broad_ai_absent=1,
        generalized_specials_absent=1,
        map_progression_absent=1,
        ui_systems_absent=1,
        real_audio_absent=1,
        source_stage31_absent=1,
        signature=0,
    )
    return Stage30RuntimeRenderedMotionReference(**{**ref.__dict__, "signature": _stage30_signature(ref)})


@lru_cache(maxsize=4)
def _reference_stage30_cached(wad_path: str) -> Stage30RuntimeRenderedMotionReference:
    return _reference_stage30_uncached(wad_path)


def reference_runtime_rendered_motion_bridge_for_pinned_map(
    wad_path: str | Path,
) -> Stage30RuntimeRenderedMotionReference:
    return _reference_stage30_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage30RuntimeRenderedMotionReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_runtime_rendered_motion_bridge_for_pinned_map(wad_path)


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


def emit_stage30_entry(pe: PE32) -> None:
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
    x86.call_rel32(pe, "source_stage30_load_wad_runtime_rendered_motion_bridge")
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
    x86.push_abs32(pe, "stage30_replay_title_start")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE30_TIMER_MS)
    x86.push_imm32(pe, STAGE30_TIMER_ID)
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
    x86.call_rel32(pe, "stage30_timer_tick")
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


def emit_stage30_timer_tick(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(SELECTED_SAMPLE_TICS)
    pe.label("stage30_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage30_replay_step")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage30_replay_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage30_replay_sample{index}")
        x86.call_rel32(pe, f"stage30_copy_rendered_frame{index}")
        x86.push_abs32(pe, f"stage30_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.mov_mem_abs32_imm32(pe, "stage30_replay_step", index + 1)
        if index == sample_count - 1:
            x86.push_imm32(pe, STAGE30_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)


def _emit_copy_sample_frame(pe: PE32, index: int) -> None:
    pe.label(f"stage30_copy_rendered_frame{index}")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")
    pe.emit(b"\xFC")
    x86.mov_reg_abs32(pe, "esi", f"stage30_frame_pixels_{index}")
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.mov_reg_imm32(pe, "ecx", FRAMEBUFFER_PIXELS)
    pe.emit(b"\xF3\xA5")
    for dst, src in (
        ("stage30_runtime_viewx", f"stage30_frame{index}_viewx"),
        ("stage30_runtime_viewy", f"stage30_frame{index}_viewy"),
        ("stage30_runtime_viewz", f"stage30_frame{index}_viewz"),
        ("stage30_runtime_viewangle", f"stage30_frame{index}_viewangle"),
        ("stage30_runtime_fb_signature", f"stage30_frame{index}_fb_signature"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.ret(pe)


def emit_source_stage30_load_wad_runtime_rendered_motion_bridge(pe: PE32) -> None:
    pe.label("source_stage30_load_wad_runtime_rendered_motion_bridge")
    x86.call_rel32(pe, "source_stage29_load_wad_selected_monster_chase_attack_state_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "stage29_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage29_expected_signature")
    x86.jne_rel32(pe, "source_stage30_return")
    x86.call_rel32(pe, "render_runtime_rendered_motion_bridge_debug")
    x86.call_rel32(pe, "append_stage30_success_status")
    pe.label("source_stage30_return")
    x86.ret(pe)


def emit_render_runtime_rendered_motion_bridge_debug(pe: PE32) -> None:
    pe.label("G_Ticker_stage30_selected_motion_replay_source_shape_debug")
    pe.label("P_PlayerThink_stage30_motion_view_source_shape_debug")
    pe.label("R_SetupFrame_stage30_runtime_view_copy_source_shape_debug")
    pe.label("R_RenderPlayerView_stage30_runtime_redraw_bridge_debug")
    pe.label("V_DrawBlock_stage30_framebuffer_present_debug")
    pe.label("render_runtime_rendered_motion_bridge_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage30_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage30_runtime_signature")
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage26._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage30_success_status(pe: PE32) -> None:
    pe.label("append_stage30_success_status")
    _emit_seek_buffer_end(pe, "status_success_buffer", "stage30_status")
    stage01.append_c_string_label(pe, "status_stage30_success_header")
    stage01.append_c_string_label(pe, "status_stage30_log_prefix")
    stage01.append_c_string_label(pe, "stage30_log_text")
    stage01.append_u32_label(pe, "status_stage30_signature_prefix", "stage30_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage30_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage30_title")
    for prefix, label, signed in (
        ("title_stage30_frame_count_prefix", "stage30_frame_count", False),
        ("title_stage30_distinct_view_prefix", "stage30_distinct_view_inputs", False),
        ("title_stage30_distinct_fb_prefix", "stage30_distinct_fb_signatures", False),
        ("title_stage30_final_sig_prefix", "stage30_final_fb_signature", False),
        ("title_stage30_projectiles_prefix", "stage30_projectiles_absent", False),
        ("title_stage30_audio_prefix", "stage30_real_audio_absent", False),
        ("title_stage30_stage31_prefix", "stage30_source_stage31_absent", False),
    ):
        (stage01.append_i32_label if signed else stage01.append_u32_label)(pe, prefix, label)
    stage01.append_c_string_label(pe, "title_stage30_log_prefix")
    stage01.append_c_string_label(pe, "stage30_log_text")
    stage01.append_u32_label(pe, "title_stage30_signature_prefix", "stage30_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def _stage30_log_text(samples: tuple[Stage30FrameSample, ...]) -> str:
    return "|".join(
        f"{s.step}:T{s.tic}:VX{s.viewx >> FRACBITS}:VY{s.viewy >> FRACBITS}:A{s.viewangle_degrees}:FB{s.framebuffer_signature}"
        for s in samples
    )


def _stage30_replay_titles(ref: Stage30RuntimeRenderedMotionReference | None) -> tuple[str, ...]:
    if ref is None:
        return ()
    titles: list[str] = []
    for index, sample in enumerate(ref.samples):
        title = (
            f"Inference Doom S30 RENDER STEP30={index + 1} TIC30={sample.tic} "
            f"VX30={sample.viewx >> FRACBITS} VY30={sample.viewy >> FRACBITS} "
            f"A30={sample.viewangle_degrees} VZ30={sample.viewz} "
            f"FB30={sample.framebuffer_signature}"
        )
        if index == len(ref.samples) - 1:
            title += (
                f" FBDIST30={ref.distinct_framebuffer_signatures}"
                " S19SIG=2088411722 S20SIG=3226031347 S21SIG=1770773845"
                " S22SIG=2207028069 S23SIG=3216085132 S24SIG=1919312263"
                " S25SIG=1688844032 S26SIG=132405987 S27SIG=1735738182"
                " S28SIG=2805406010 S29SIG=3738922932"
                f" S30SIG={ref.signature} S31ABS={ref.source_stage31_absent}"
            )
        titles.append(title)
    return tuple(titles)


def emit_stage30_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    samples = ref.samples if ref else ()
    final = samples[-1] if samples else None
    pe.align_section(4)
    for name, value in (
        ("stage30_frame_count", len(samples)),
        ("stage30_distinct_view_inputs", ref.distinct_view_inputs if ref else 0),
        ("stage30_distinct_fb_signatures", ref.distinct_framebuffer_signatures if ref else 0),
        ("stage30_final_fb_signature", final.framebuffer_signature if final else 0),
        ("stage30_projectiles_absent", ref.projectiles_absent if ref else 1),
        ("stage30_explosions_absent", ref.explosions_absent if ref else 1),
        ("stage30_generalized_combat_absent", ref.generalized_combat_absent if ref else 1),
        ("stage30_broad_ai_absent", ref.broad_ai_absent if ref else 1),
        ("stage30_generalized_specials_absent", ref.generalized_specials_absent if ref else 1),
        ("stage30_map_progression_absent", ref.map_progression_absent if ref else 1),
        ("stage30_ui_systems_absent", ref.ui_systems_absent if ref else 1),
        ("stage30_real_audio_absent", ref.real_audio_absent if ref else 1),
        ("stage30_source_stage31_absent", ref.source_stage31_absent if ref else 1),
        ("stage30_expected_signature", ref.signature if ref else 0),
        ("stage30_runtime_signature", 0),
        ("stage30_runtime_viewx", 0),
        ("stage30_runtime_viewy", 0),
        ("stage30_runtime_viewz", 0),
        ("stage30_runtime_viewangle", 0),
        ("stage30_runtime_fb_signature", 0),
        ("stage30_replay_step", 0),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        for name, value in (
            (f"stage30_frame{index}_tic", sample.tic),
            (f"stage30_frame{index}_viewx", sample.viewx),
            (f"stage30_frame{index}_viewy", sample.viewy),
            (f"stage30_frame{index}_viewz", sample.viewz),
            (f"stage30_frame{index}_viewangle", sample.viewangle),
            (f"stage30_frame{index}_fb_signature", sample.framebuffer_signature),
        ):
            pe.label(name)
            pe.emit_u32(value & 0xFFFFFFFF)
    pe.align_section(1)
    pe.label("stage30_log_text")
    x86.emit_asciiz(pe, _stage30_log_text(samples))
    pe.label("status_stage30_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage30_runtime_rendered_motion_bridge\r\n"
        "Runtime rendered motion bridge proof OK\r\n",
    )
    pe.label("status_stage30_log_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime frame log: ")
    pe.label("status_stage30_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage30 runtime rendered motion signature: ")
    pe.label("status_stage30_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage30 preserves stage29 through stage19, then replays selected MAP01 "
        "stage14 player-view samples after launch. Each timer step copies source-shaped "
        "view fields, clears/replaces the live framebuffer with that frame's rendered "
        "pixels, invalidates the window, and reports a framebuffer signature. "
        "Projectiles, explosions, generalized combat, broad AI, map progression, "
        "UI systems, generalized specials, and real audio remain deferred.\r\n",
    )
    for label, text in (
        ("title_stage30_frame_count_prefix", " S30FR="),
        ("title_stage30_distinct_view_prefix", " VDIST30="),
        ("title_stage30_distinct_fb_prefix", " FBDIST30="),
        ("title_stage30_final_sig_prefix", " FBF30="),
        ("title_stage30_projectiles_prefix", " PROJ30="),
        ("title_stage30_audio_prefix", " AUD30="),
        ("title_stage30_stage31_prefix", " S31ABS="),
        ("title_stage30_log_prefix", " LOG30="),
        ("title_stage30_signature_prefix", " S30SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)
    pe.label("stage30_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S30 RENDER START STEP30=0 waiting for framebuffer-driven replay")
    for index, title in enumerate(_stage30_replay_titles(ref)):
        pe.label(f"stage30_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)
    pe.align_section(4)
    for index, sample in enumerate(samples):
        pe.label(f"stage30_frame_pixels_{index}")
        pe.emit(sample.framebuffer)


def build_source_stage30_runtime_rendered_motion_bridge_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    ref = _reference_for_default_wad_or_none()
    emit_stage30_entry(pe)
    stage28.emit_stage28_wndproc_framebuffer(pe)
    emit_stage30_timer_tick(pe)
    for index in range(len(ref.samples) if ref else len(SELECTED_SAMPLE_TICS)):
        _emit_copy_sample_frame(pe, index)
    emit_source_stage30_load_wad_runtime_rendered_motion_bridge(pe)
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
    emit_render_runtime_rendered_motion_bridge_debug(pe)
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
    emit_append_stage30_success_status(pe)
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
    emit_stage30_data(pe)
    return pe.build("entry")


def write_source_stage30_runtime_rendered_motion_bridge_exe(path: str | Path) -> bytes:
    image = build_source_stage30_runtime_rendered_motion_bridge_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage30 runtime rendered motion bridge PE32 executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage30_runtime_rendered_motion_bridge.exe",
        help="path to write, default: build/source_stage30_runtime_rendered_motion_bridge.exe",
    )
    args = parser.parse_args()
    write_source_stage30_runtime_rendered_motion_bridge_exe(args.output)


if __name__ == "__main__":
    main()
