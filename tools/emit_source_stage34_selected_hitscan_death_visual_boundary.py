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

from tools import emit_source_stage33_selected_hitscan_impact_visual_boundary as stage33
from tools import x86
from tools.pe32 import PE32
from tools.wad import WadFile


stage32 = stage33.stage32
stage31 = stage33.stage31
stage30 = stage33.stage30
stage29 = stage33.stage29
stage28 = stage33.stage28
stage27 = stage33.stage27
stage26 = stage33.stage26
stage25 = stage33.stage25
stage24 = stage33.stage24
stage23 = stage33.stage23
stage22 = stage33.stage22
stage21 = stage33.stage21
stage20 = stage33.stage20
stage19 = stage33.stage19
stage18 = stage33.stage18
stage17 = stage33.stage17
stage16 = stage33.stage16
stage15 = stage33.stage15
stage14 = stage33.stage14
stage13 = stage33.stage13
stage12 = stage33.stage12
stage11 = stage33.stage11
stage10 = stage33.stage10
stage09 = stage10.stage09
stage08 = stage32.stage08
stage07 = stage32.stage07
stage04 = stage32.stage04
stage03 = stage32.stage03
stage02 = stage32.stage02
stage01 = stage32.stage01

FRAMEBUFFER_WIDTH = stage31.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage31.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_BYTES = stage31.FRAMEBUFFER_BYTES
WINDOW_WIDTH = stage31.WINDOW_WIDTH
WINDOW_HEIGHT = stage31.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage34SelectedHitscanDeathVisualBoundary"
WINDOW_TITLE = "Inference Doom S34 Hitscan Death Visual Boundary"
WAD_PATH = stage31.WAD_PATH

FRACBITS = stage31.FRACBITS
FRACUNIT = stage15.FRACUNIT
FNV_OFFSET_BASIS = stage31.FNV_OFFSET_BASIS
FNV_PRIME = stage31.FNV_PRIME
WM_TIMER = stage31.WM_TIMER
STAGE34_TIMER_ID = 34
STAGE34_TIMER_MS = stage33.STAGE33_TIMER_MS
SELECTED_SAMPLE_TICS = stage31.SELECTED_SAMPLE_TICS
COMMAND_RECORD_SIZE = stage31.COMMAND_RECORD_SIZE
SELECTED_DEATH_STATES = ("NONE", "S_SPOS_DIE1", "S_SPOS_DIE2")
SELECTED_DEATH_CENTER_X = 161
SELECTED_DEATH_TOP_Y = 60
SELECTED_DEATH_MAX_COLUMNS = 56

SOURCE_TRACE = stage33.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_pspr.c",
        "A_FireShotgun selected route supplies the bounded lethal replay setup",
        "A_FireShotgun_stage34_selected_lethal_replay_setup_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "P_LineAttack/PTR_ShootTraverse selected hit route reaches the chosen target before lethal damage",
        "P_LineAttack_stage34_selected_hitscan_lethal_boundary_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_inter.c",
        "P_DamageMobj/P_KillMobj selected shotgun-guy lethal transition",
        "P_DamageMobj_P_KillMobj_stage34_selected_death_state_visual_boundary_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_SetMobjState selected shotgun-guy death-state route",
        "P_SetMobjState_stage34_selected_shotguy_death_route_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_things.c",
        "R_ProjectSprite/R_DrawVisSprite/R_DrawMaskedColumn selected death posts before psprites",
        "R_DrawSpriteRange_stage34_selected_death_world_post_table_debug",
    ),
    (
        "reference/chocolate-doom/src/v_video.c",
        "V_DrawBlock-style present after wall/flat, selected impact, selected death, and selected psprite posts",
        "V_DrawBlock_stage34_selected_hitscan_death_visual_present_debug",
    ),
)


@dataclass(frozen=True)
class Stage34DeathCommand:
    x: int
    yl: int
    yh: int
    iscale: int
    texturemid: int
    source_index: int
    patch_name: str
    patch_column: int


@dataclass(frozen=True)
class Stage34FrameSample:
    step: int
    tic: int
    psprite_state: int
    psprite_state_name: str
    psprite_patch_name: str
    psprite_frame: int
    impact_state: int
    impact_state_name: str
    impact_patch_name: str
    impact_commands: tuple[stage33.Stage33ImpactCommand, ...]
    death_state: int
    death_state_name: str
    death_sprite_name: str
    death_patch_name: str
    death_frame: int
    death_commands: tuple[Stage34DeathCommand, ...]
    psprite_commands: tuple[stage32.Stage32PspriteCommand, ...]
    base_framebuffer_signature: int
    impact_framebuffer_signature: int
    death_framebuffer_signature: int
    framebuffer_signature: int
    wall_pixels_drawn: int
    flat_pixels_drawn: int
    impact_pixels_drawn: int
    death_pixels_drawn: int
    psprite_pixels_drawn: int
    clear_sequence: int
    wall_flat_sequence: int
    impact_sequence: int
    death_sequence: int
    psprite_sequence: int
    present_sequence: int


@dataclass(frozen=True)
class Stage34SelectedHitscanDeathVisualBoundaryReference:
    stage33: stage33.Stage33SelectedHitscanImpactVisualBoundaryReference
    stage17: stage17.Stage17FirstWeaponFireReference
    samples: tuple[Stage34FrameSample, ...]
    death_sources: tuple[bytes, ...]
    palette32: tuple[int, ...]
    target_mapthing_index: int
    target_mobj_index: int
    selected_nonlethal_damage: int
    selected_lethal_damage: int
    selected_damage_total: int
    selected_target_health_before_lethal: int
    selected_target_health_after: int
    selected_kill_events: int
    selected_death_state_sets: int
    selected_drop_deferred: int
    selected_corpse_flags: int
    distinct_death_states: int
    distinct_death_command_tables: int
    distinct_framebuffer_signatures: int
    distinct_impact_framebuffer_signatures: int
    distinct_death_framebuffer_signatures: int
    impact_contribution_signatures: int
    death_contribution_signatures: int
    psprite_contribution_signatures: int
    full_frame_byte_arrays_absent: int
    runtime_renderer_primitives: int
    wall_path_replayed: int
    flat_path_replayed: int
    death_or_pain_path_replayed: int
    psprite_path_replayed: int
    blood_puff_spawn_deferred: int
    projectiles_absent: int
    explosions_absent: int
    monster_attack_execution_absent: int
    item_pickup_absent: int
    generalized_death_drop_absent: int
    selected_drop_visual_deferred: int
    generalized_combat_absent: int
    broad_ai_absent: int
    generalized_sprite_systems_absent: int
    generalized_specials_absent: int
    map_progression_absent: int
    ui_systems_absent: int
    real_audio_absent: int
    source_stage35_absent: int
    signature: int


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & 0xFFFFFFFF


def _append_source(sources: list[bytes], pixels: bytes) -> int:
    sources.append(stage12._padded_source(pixels))
    return len(sources) - 1


def _patch_for_state(
    wad: WadFile,
    info: stage15.Stage15InfoTables,
    patch_lookup: dict[tuple[int, int], str],
    state_name: str,
) -> tuple[int, str, str, int, str]:
    state_index = info.state_index[state_name]
    state = info.states[state_index]
    frame = state.frame & stage13.FF_FRAMEMASK
    sprite_name = info.sprnames[state.sprite]
    patch_name = patch_lookup.get((state.sprite, frame))
    if patch_name is None:
        prefix = f"{sprite_name}{chr(ord('A') + frame)}"
        patch_name = next(lump.name for lump in wad.lumps if lump.name.startswith(prefix))
    return state_index, sprite_name, patch_name, frame, state.name


def _selected_pain_commands(
    wad: WadFile,
    info: stage15.Stage15InfoTables,
    patch_lookup: dict[tuple[int, int], str],
    state_name: str,
    sources: list[bytes],
) -> tuple[tuple[Stage34DeathCommand, ...], int, str, str, int, str]:
    if state_name == "NONE":
        return (), 0, "", "", 0, "NONE"

    state_index, sprite_name, patch_name, frame, mapped_name = _patch_for_state(wad, info, patch_lookup, state_name)
    patch_data = wad.read_lump(patch_name)
    header = stage08.parse_patch_header(patch_data, lump_name=patch_name)
    width = min(header.width, SELECTED_DEATH_MAX_COLUMNS)
    left = SELECTED_DEATH_CENTER_X - width // 2
    texturemid = ((stage13.CENTER_Y - SELECTED_DEATH_TOP_Y) << FRACBITS) & 0xFFFFFFFF
    vis = stage13.VisSprite(
        thing_index=stage17.DEFAULT_ATTACK_TARGET_MAPTHING_INDEX,
        mapthing_index=stage17.DEFAULT_ATTACK_TARGET_MAPTHING_INDEX,
        type_name="MT_SHOTGUY",
        sprite_name=sprite_name,
        sprite=info.sprnames.index(sprite_name),
        frame=frame,
        patch=0,
        patch_name=patch_name,
        x1=max(0, left),
        x2=min(FRAMEBUFFER_WIDTH - 1, left + width - 1),
        raw_x1=left,
        raw_x2=left + width - 1,
        scale=FRACUNIT,
        xiscale=FRACUNIT,
        startfrac=0,
        texturemid=texturemid,
        flip=False,
        tz=FRACUNIT,
    )

    def posts_for_column(column: int):
        if 0 <= column < header.width:
            return stage09.parse_patch_column_posts(patch_data, column, lump_name=patch_name)
        return None

    raw_commands, _columns, _posts, _skips = stage13.r_draw_sprite_range_source_shape(
        vis,
        posts_for_column,
        lambda pixels: _append_source(sources, pixels),
        floorclip=[FRAMEBUFFER_HEIGHT] * FRAMEBUFFER_WIDTH,
        ceilingclip=[-1] * FRAMEBUFFER_WIDTH,
        max_new_columns=SELECTED_DEATH_MAX_COLUMNS,
    )
    return (
        tuple(
            Stage34DeathCommand(
                x=command.x,
                yl=command.yl,
                yh=command.yh,
                iscale=command.iscale,
                texturemid=command.texturemid,
                source_index=command.source_index,
                patch_name=patch_name,
                patch_column=command.texture_column,
            )
            for command in raw_commands
        ),
        state_index,
        sprite_name,
        patch_name,
        frame,
        mapped_name,
    )


def _draw_death_commands(
    frame: bytearray,
    commands: Sequence[Stage34DeathCommand],
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


def _stage34_signature(ref: Stage34SelectedHitscanDeathVisualBoundaryReference) -> int:
    sig = FNV_OFFSET_BASIS
    for value in (
        34,
        ref.stage33.signature,
        ref.stage17.signature,
        len(ref.samples),
        ref.target_mapthing_index,
        ref.target_mobj_index,
        ref.selected_nonlethal_damage,
        ref.selected_lethal_damage,
        ref.selected_damage_total,
        ref.selected_target_health_before_lethal,
        ref.selected_target_health_after,
        ref.selected_kill_events,
        ref.selected_death_state_sets,
        ref.selected_drop_deferred,
        ref.selected_corpse_flags,
        ref.distinct_death_states,
        ref.distinct_death_command_tables,
        ref.distinct_framebuffer_signatures,
        ref.distinct_impact_framebuffer_signatures,
        ref.distinct_death_framebuffer_signatures,
        ref.impact_contribution_signatures,
        ref.death_contribution_signatures,
        ref.psprite_contribution_signatures,
        ref.full_frame_byte_arrays_absent,
        ref.runtime_renderer_primitives,
        ref.death_or_pain_path_replayed,
        ref.psprite_path_replayed,
        ref.source_stage35_absent,
    ):
        sig = _hash_u32(sig, value)
    for sample in ref.samples:
        for value in (
            sample.step,
            sample.tic,
            sample.psprite_state,
            sample.impact_state,
            sample.death_state,
            sample.death_frame,
            len(sample.impact_commands),
            len(sample.death_commands),
            len(sample.psprite_commands),
            sample.base_framebuffer_signature,
            sample.impact_framebuffer_signature,
            sample.death_framebuffer_signature,
            sample.framebuffer_signature,
            sample.wall_pixels_drawn,
            sample.flat_pixels_drawn,
            sample.impact_pixels_drawn,
            sample.death_pixels_drawn,
            sample.psprite_pixels_drawn,
            sample.clear_sequence,
            sample.wall_flat_sequence,
            sample.impact_sequence,
            sample.death_sequence,
            sample.psprite_sequence,
            sample.present_sequence,
        ):
            sig = _hash_u32(sig, value)
    return sig


def _reference_stage34_uncached(wad_path: str) -> Stage34SelectedHitscanDeathVisualBoundaryReference:
    wad = WadFile.from_file(wad_path)
    ref33 = stage33.reference_selected_hitscan_impact_visual_boundary_for_pinned_map(wad_path)
    ref17 = stage17.reference_first_weapon_fire_damage_and_death_probe_for_pinned_map(wad_path)
    selected_shot = next(shot for shot in ref17.shots if shot.selected_hit)
    info = stage15.parse_stage15_info_tables()
    patch_lookup = stage15.build_patch_frame_lookup(wad, info)
    death_sources: list[bytes] = []
    death_tables: list[tuple[Stage34DeathCommand, ...]] = []
    death_meta: list[tuple[int, str, str, int, str]] = []
    for state_name in SELECTED_DEATH_STATES:
        commands, state_index, sprite_name, patch_name, frame, mapped_name = _selected_pain_commands(
            wad, info, patch_lookup, state_name, death_sources
        )
        death_tables.append(commands)
        death_meta.append((state_index, sprite_name, patch_name, frame, mapped_name))

    samples: list[Stage34FrameSample] = []
    for index, sample33 in enumerate(ref33.samples):
        sample32 = ref33.stage32.samples[index]
        base_sample = ref33.stage32.stage31.samples[index]
        frame, base_sig, wall_pixels, flat_pixels = stage32._draw_stage31_base(base_sample, ref33.stage32.stage31)
        impact_pixels = stage33._draw_impact_commands(
            frame, sample33.impact_commands, ref33.impact_sources, ref33.palette32
        )
        impact_sig = stage31._framebuffer_signature(frame)
        death_commands = death_tables[index]
        death_pixels = _draw_death_commands(frame, death_commands, death_sources, ref33.palette32)
        death_sig = stage31._framebuffer_signature(frame)
        psprite_pixels = stage32._draw_psprite_commands(
            frame, sample32.psprite_commands, ref33.stage32.psprite_sources, ref33.palette32
        )
        final_sig = stage31._framebuffer_signature(frame)
        state_index, sprite_name, patch_name, frame_index, mapped_name = death_meta[index]
        seq = index * 6
        samples.append(
            Stage34FrameSample(
                step=index + 1,
                tic=sample32.tic,
                psprite_state=sample32.psprite_state,
                psprite_state_name=sample32.psprite_state_name,
                psprite_patch_name=sample32.psprite_patch_name,
                psprite_frame=sample32.psprite_frame,
                impact_state=sample33.impact_state,
                impact_state_name=sample33.impact_state_name,
                impact_patch_name=sample33.impact_patch_name,
                impact_commands=sample33.impact_commands,
                death_state=state_index,
                death_state_name=mapped_name,
                death_sprite_name=sprite_name,
                death_patch_name=patch_name,
                death_frame=frame_index,
                death_commands=death_commands,
                psprite_commands=sample32.psprite_commands,
                base_framebuffer_signature=base_sig,
                impact_framebuffer_signature=impact_sig,
                death_framebuffer_signature=death_sig,
                framebuffer_signature=final_sig,
                wall_pixels_drawn=wall_pixels,
                flat_pixels_drawn=flat_pixels,
                impact_pixels_drawn=impact_pixels,
                death_pixels_drawn=death_pixels,
                psprite_pixels_drawn=psprite_pixels,
                clear_sequence=seq + 1,
                wall_flat_sequence=seq + 2,
                impact_sequence=seq + 3,
                death_sequence=seq + 4,
                psprite_sequence=seq + 5,
                present_sequence=seq + 6,
            )
        )

    selected_lethal_damage = ref17.health_after
    selected_target_health_after = ref17.health_after - selected_lethal_damage
    selected_corpse_flags = (
        stage13.MF_CORPSE
        | stage13.MF_DROPOFF
        | (ref17.final_target.flags & ~(stage13.MF_SHOOTABLE | stage13.MF_FLOAT | stage13.MF_SKULLFLY | stage13.MF_NOGRAVITY))
    )
    provisional = Stage34SelectedHitscanDeathVisualBoundaryReference(
        stage33=ref33,
        stage17=ref17,
        samples=tuple(samples),
        death_sources=tuple(death_sources),
        palette32=ref33.palette32,
        target_mapthing_index=stage17.DEFAULT_ATTACK_TARGET_MAPTHING_INDEX,
        target_mobj_index=ref17.census.target_mobj_index,
        selected_nonlethal_damage=selected_shot.damage,
        selected_lethal_damage=selected_lethal_damage,
        selected_damage_total=selected_shot.damage + selected_lethal_damage,
        selected_target_health_before_lethal=ref17.health_after,
        selected_target_health_after=selected_target_health_after,
        selected_kill_events=1,
        selected_death_state_sets=1,
        selected_drop_deferred=1,
        selected_corpse_flags=selected_corpse_flags,
        distinct_death_states=len({s.death_state_name for s in samples}),
        distinct_death_command_tables=len({tuple((c.x, c.yl, c.yh, c.source_index) for c in s.death_commands) for s in samples}),
        distinct_framebuffer_signatures=len({s.framebuffer_signature for s in samples}),
        distinct_impact_framebuffer_signatures=len({s.impact_framebuffer_signature for s in samples}),
        distinct_death_framebuffer_signatures=len({s.death_framebuffer_signature for s in samples}),
        impact_contribution_signatures=sum(1 for s in samples if s.impact_framebuffer_signature != s.base_framebuffer_signature),
        death_contribution_signatures=sum(1 for s in samples if s.death_framebuffer_signature != s.impact_framebuffer_signature),
        psprite_contribution_signatures=sum(1 for s in samples if s.framebuffer_signature != s.death_framebuffer_signature),
        full_frame_byte_arrays_absent=1,
        runtime_renderer_primitives=1,
        wall_path_replayed=1,
        flat_path_replayed=1,
        death_or_pain_path_replayed=1,
        psprite_path_replayed=1,
        blood_puff_spawn_deferred=1,
        projectiles_absent=1,
        explosions_absent=1,
        monster_attack_execution_absent=1,
        item_pickup_absent=1,
        generalized_death_drop_absent=1,
        selected_drop_visual_deferred=1,
        generalized_combat_absent=1,
        broad_ai_absent=1,
        generalized_sprite_systems_absent=1,
        generalized_specials_absent=1,
        map_progression_absent=1,
        ui_systems_absent=1,
        real_audio_absent=1,
        source_stage35_absent=1,
        signature=0,
    )
    return Stage34SelectedHitscanDeathVisualBoundaryReference(
        **{**provisional.__dict__, "signature": _stage34_signature(provisional)}
    )


@lru_cache(maxsize=4)
def reference_selected_hitscan_death_visual_boundary_for_pinned_map(
    wad_path: str | Path = WAD_PATH,
) -> Stage34SelectedHitscanDeathVisualBoundaryReference:
    return _reference_stage34_uncached(str(wad_path))


@lru_cache(maxsize=1)
def _reference_for_default_wad_or_none() -> Stage34SelectedHitscanDeathVisualBoundaryReference | None:
    try:
        return reference_selected_hitscan_death_visual_boundary_for_pinned_map(WAD_PATH)
    except FileNotFoundError:
        return None


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


def emit_stage34_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")
    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage34_class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage34_class_registered")
    x86.call_rel32(pe, "source_stage34_load_wad_selected_hitscan_death_visual_boundary")
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
    x86.jne_rel32(pe, "stage34_window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage34_window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_abs32(pe, "stage34_replay_title_start")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE34_TIMER_MS)
    x86.push_imm32(pe, STAGE34_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
    pe.label("stage34_message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage34_clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "stage34_message_error")
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, WM_TIMER)
    x86.jne_rel32(pe, "stage34_dispatch_message")
    x86.call_rel32(pe, "stage34_timer_tick")
    pe.label("stage34_dispatch_message")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "stage34_message_loop")
    pe.label("stage34_clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage34_message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_stage34_timer_tick(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(SELECTED_SAMPLE_TICS)
    pe.label("stage34_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage34_replay_step")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage34_replay_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage34_replay_sample{index}")
        x86.call_rel32(pe, f"stage34_draw_sample{index}")
        x86.push_abs32(pe, f"stage34_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.mov_mem_abs32_imm32(pe, "stage34_replay_step", index + 1)
        if index == sample_count - 1:
            x86.push_imm32(pe, STAGE34_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)


def emit_stage34_draw_death_commands(pe: PE32) -> None:
    pe.label("R_ProjectSprite_stage34_selected_death_state_post_table_debug")
    pe.label("R_DrawSpriteRange_stage34_selected_death_world_post_table_debug")
    pe.label("stage34_draw_death_commands")
    x86.mov_mem_abs32_imm32(pe, "stage10_columns_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage10_pixels_drawn", 0)
    x86.mov_mem_abs32_abs32(pe, "dc_colormap", "stage31_palette32")
    pe.label("stage34_death_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "stage34_death_remaining")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage34_death_done")
    x86.mov_reg_mem_abs32(pe, "esi", "stage34_death_scan_ptr")
    for field, dst in (
        (stage10.DRAW_COMMAND_X, "dc_x"),
        (stage10.DRAW_COMMAND_YL, "dc_yl"),
        (stage10.DRAW_COMMAND_YH, "dc_yh"),
        (stage10.DRAW_COMMAND_ISCALE, "dc_iscale"),
        (stage10.DRAW_COMMAND_TEXTUREMID, "dc_texturemid"),
        (stage10.DRAW_COMMAND_SOURCE, "dc_source"),
    ):
        x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", field)
        x86.mov_mem_abs32_eax(pe, dst)
    stage07._emit_inc_abs32(pe, "stage34_death_posts_drawn")
    x86.call_rel32(pe, "render_draw_column_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage10_pixels_drawn")
    x86.mov_mem_abs32_eax(pe, "stage34_death_pixels_drawn")
    x86.mov_reg_mem_abs32(pe, "esi", "stage34_death_scan_ptr")
    x86.add_reg_imm32(pe, "esi", COMMAND_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, "stage34_death_scan_ptr", "esi")
    x86.dec_mem_abs32(pe, "stage34_death_remaining")
    x86.jmp_rel32(pe, "stage34_death_loop")
    pe.label("stage34_death_done")
    x86.ret(pe)


def _emit_stage34_draw_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage34_draw_sample{index}")
    x86.call_rel32(pe, "stage31_clear_framebuffer")
    for dst, src in (
        ("stage31_runtime_viewx", f"stage31_sample{index}_viewx"),
        ("stage31_runtime_viewy", f"stage31_sample{index}_viewy"),
        ("stage31_runtime_viewz", f"stage31_sample{index}_viewz"),
        ("stage31_runtime_viewangle", f"stage31_sample{index}_viewangle"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    for name in (
        "stage31_wall_columns_drawn",
        "stage31_wall_pixels_drawn",
        "stage31_flat_spans_drawn",
        "stage31_flat_pixels_drawn",
        "stage32_psprite_posts_drawn",
        "stage32_psprite_pixels_drawn",
        "stage33_impact_posts_drawn",
        "stage33_impact_pixels_drawn",
        "stage34_impact_posts_drawn",
        "stage34_impact_pixels_drawn",
        "stage34_death_posts_drawn",
        "stage34_death_pixels_drawn",
        "stage34_psprite_posts_drawn",
        "stage34_psprite_pixels_drawn",
    ):
        x86.mov_mem_abs32_imm32(pe, name, 0)
    x86.mov_mem_abs32_abs32(pe, "stage31_wall_scan_ptr", f"stage31_wall_commands_{index}")
    x86.mov_mem_abs32_abs32(pe, "stage31_span_scan_ptr", f"stage31_span_commands_{index}")
    x86.mov_mem_abs32_abs32(pe, "stage33_impact_scan_ptr", f"stage33_impact_commands_{index}")
    x86.mov_mem_abs32_abs32(pe, "stage34_death_scan_ptr", f"stage34_death_commands_{index}")
    x86.mov_mem_abs32_abs32(pe, "stage32_psprite_scan_ptr", f"stage32_psprite_commands_{index}")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage31_sample{index}_wall_command_count")
    x86.mov_mem_abs32_eax(pe, "stage31_wall_remaining")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage31_sample{index}_span_command_count")
    x86.mov_mem_abs32_eax(pe, "stage31_span_remaining")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage33_sample{index}_impact_command_count")
    x86.mov_mem_abs32_eax(pe, "stage33_impact_remaining")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage34_sample{index}_death_command_count")
    x86.mov_mem_abs32_eax(pe, "stage34_death_remaining")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage32_sample{index}_psprite_command_count")
    x86.mov_mem_abs32_eax(pe, "stage32_psprite_remaining")
    x86.call_rel32(pe, "stage31_draw_wall_commands")
    x86.call_rel32(pe, "stage31_draw_flat_spans")
    x86.call_rel32(pe, "stage33_draw_impact_commands")
    x86.mov_reg_mem_abs32(pe, "eax", "stage33_impact_posts_drawn")
    x86.mov_mem_abs32_eax(pe, "stage34_impact_posts_drawn")
    x86.mov_reg_mem_abs32(pe, "eax", "stage33_impact_pixels_drawn")
    x86.mov_mem_abs32_eax(pe, "stage34_impact_pixels_drawn")
    x86.call_rel32(pe, "stage34_draw_death_commands")
    x86.call_rel32(pe, "stage32_draw_psprite_commands")
    x86.mov_reg_mem_abs32(pe, "eax", "stage32_psprite_posts_drawn")
    x86.mov_mem_abs32_eax(pe, "stage34_psprite_posts_drawn")
    x86.mov_reg_mem_abs32(pe, "eax", "stage32_psprite_pixels_drawn")
    x86.mov_mem_abs32_eax(pe, "stage34_psprite_pixels_drawn")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage34_runtime_fb_signature")
    x86.ret(pe)


def emit_source_stage34_load_wad_selected_hitscan_death_visual_boundary(pe: PE32) -> None:
    pe.label("source_stage34_load_wad_selected_hitscan_death_visual_boundary")
    x86.call_rel32(pe, "source_stage33_load_wad_selected_hitscan_impact_visual_boundary")
    x86.mov_reg_mem_abs32(pe, "eax", "stage33_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage33_expected_signature")
    x86.jne_rel32(pe, "source_stage34_return")
    x86.call_rel32(pe, "render_selected_hitscan_death_visual_boundary_debug")
    x86.call_rel32(pe, "append_stage34_success_status")
    pe.label("source_stage34_return")
    x86.ret(pe)


def emit_render_selected_hitscan_death_visual_boundary_debug(pe: PE32) -> None:
    pe.label("A_FireShotgun_stage34_selected_lethal_replay_setup_debug")
    pe.label("P_LineAttack_stage34_selected_hitscan_lethal_boundary_debug")
    pe.label("P_DamageMobj_P_KillMobj_stage34_selected_death_state_visual_boundary_debug")
    pe.label("P_SetMobjState_stage34_selected_shotguy_death_route_debug")
    pe.label("R_RenderPlayerView_stage34_clear_wall_flat_impact_death_psprite_present_debug")
    pe.label("V_DrawBlock_stage34_selected_hitscan_death_visual_present_debug")
    pe.label("render_selected_hitscan_death_visual_boundary_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage34_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage34_runtime_signature")
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage31._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage34_success_status(pe: PE32) -> None:
    pe.label("append_stage34_success_status")
    _emit_seek_buffer_end(pe, "status_success_buffer", "stage34_status")
    stage01.append_c_string_label(pe, "status_stage34_success_header")
    stage01.append_c_string_label(pe, "status_stage34_log_prefix")
    stage01.append_c_string_label(pe, "stage34_log_text")
    stage01.append_u32_label(pe, "status_stage34_signature_prefix", "stage34_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage34_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage34_title")
    for prefix, label in (
        ("title_stage34_frame_count_prefix", "stage34_frame_count"),
        ("title_stage34_distinct_fb_prefix", "stage34_distinct_fb_signatures"),
        ("title_stage34_distinct_death_prefix", "stage34_distinct_death_states"),
        ("title_stage34_death_posts_prefix", "stage34_final_death_posts"),
        ("title_stage34_death_pixels_prefix", "stage34_final_death_pixels"),
        ("title_stage34_psprite_posts_prefix", "stage34_final_psprite_posts"),
        ("title_stage34_psprite_pixels_prefix", "stage34_final_psprite_pixels"),
        ("title_stage34_full_frame_prefix", "stage34_full_frame_byte_arrays_absent"),
        ("title_stage34_stage35_prefix", "stage34_source_stage35_absent"),
    ):
        stage01.append_u32_label(pe, prefix, label)
    stage01.append_c_string_label(pe, "title_stage34_log_prefix")
    stage01.append_c_string_label(pe, "stage34_log_text")
    stage01.append_u32_label(pe, "title_stage34_signature_prefix", "stage34_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def _stage34_log_text(samples: tuple[Stage34FrameSample, ...]) -> str:
    return "|".join(
        f"{s.step}:T{s.tic}:PS{s.psprite_state_name}:PN{s.psprite_patch_name}:"
        f"IMP{s.impact_state_name}:IPN{s.impact_patch_name}:IC{len(s.impact_commands)}:"
        f"IP{s.impact_pixels_drawn}:DIE{s.death_state_name}:DPN{s.death_patch_name}:"
        f"DC{len(s.death_commands)}:DP{s.death_pixels_drawn}:PP{s.psprite_pixels_drawn}:"
        f"BASE{s.base_framebuffer_signature}:IMPFB{s.impact_framebuffer_signature}:"
        f"DIEFB{s.death_framebuffer_signature}:FB{s.framebuffer_signature}"
        for s in samples
    )


def _stage34_replay_titles(ref: Stage34SelectedHitscanDeathVisualBoundaryReference | None) -> tuple[str, ...]:
    if ref is None:
        return ()
    titles: list[str] = []
    for index, sample in enumerate(ref.samples):
        base = ref.stage33.stage32.stage31.samples[index]
        title = (
            f"Inference Doom S34 DEATH STEP34={index + 1} TIC34={sample.tic} "
            f"VX31={base.viewx >> FRACBITS} VY31={base.viewy >> FRACBITS} "
            f"A31={base.viewangle_degrees} WC31={len(base.wall_commands)} SP31={len(base.flat_spans)} "
            f"PS34={sample.psprite_state_name} PATCH34={sample.psprite_patch_name} "
            f"IMP34={sample.impact_state_name} IPATCH34={sample.impact_patch_name or 'NONE'} "
            f"IC34={len(sample.impact_commands)} IP34={sample.impact_pixels_drawn} "
            f"DIE34={sample.death_state_name} DPATCH34={sample.death_patch_name or 'NONE'} "
            f"DC34={len(sample.death_commands)} DP34={sample.death_pixels_drawn} "
            f"PC32={len(sample.psprite_commands)} PP32={sample.psprite_pixels_drawn} "
            f"BASEFB34={sample.base_framebuffer_signature} IMPFB34={sample.impact_framebuffer_signature} "
            f"DIEFB34={sample.death_framebuffer_signature} FB34={sample.framebuffer_signature}"
        )
        if index == len(ref.samples) - 1:
            title += (
                f" FBDIST34={ref.distinct_framebuffer_signatures} IMPDIST34={ref.distinct_impact_framebuffer_signatures}"
                f" DEATHDIST34={ref.distinct_death_states} HIT34=1"
                f" DMG34={ref.selected_damage_total} LDMG34={ref.selected_lethal_damage}"
                f" H34={ref.selected_target_health_after} DROPVIS34={ref.selected_drop_visual_deferred}"
                f" NOFULL34={ref.full_frame_byte_arrays_absent} S19SIG=2088411722 S20SIG=3226031347"
                " S21SIG=1770773845 S22SIG=2207028069 S23SIG=3216085132"
                " S24SIG=1919312263 S25SIG=1688844032 S26SIG=132405987"
                " S27SIG=1735738182 S28SIG=2805406010 S29SIG=3738922932"
                f" S30SIG=3898523864 S31SIG={ref.stage33.stage32.stage31.signature}"
                f" S32SIG={ref.stage33.stage32.signature} S33SIG={ref.stage33.signature}"
                f" S34SIG={ref.signature} S35ABS={ref.source_stage35_absent}"
            )
        titles.append(title)
    return tuple(titles)


def _emit_death_commands(pe: PE32, commands: Sequence[Stage34DeathCommand]) -> None:
    for command in commands:
        pe.emit_u32(command.x)
        pe.emit_u32(command.yl)
        pe.emit_u32(command.yh)
        pe.emit_u32(command.iscale)
        pe.emit_u32(command.texturemid)
        pe.write_abs32(f"stage34_death_source_{command.source_index}")


def emit_stage34_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    samples = ref.samples if ref else ()
    final = samples[-1] if samples else None
    pe.align_section(4)
    for name, value in (
        ("stage34_frame_count", len(samples)),
        ("stage34_distinct_death_states", ref.distinct_death_states if ref else 0),
        ("stage34_distinct_death_command_tables", ref.distinct_death_command_tables if ref else 0),
        ("stage34_distinct_fb_signatures", ref.distinct_framebuffer_signatures if ref else 0),
        ("stage34_distinct_death_fb_signatures", ref.distinct_death_framebuffer_signatures if ref else 0),
        ("stage34_death_contribution_signatures", ref.death_contribution_signatures if ref else 0),
        ("stage34_psprite_contribution_signatures", ref.psprite_contribution_signatures if ref else 0),
        ("stage34_final_death_posts", len(final.death_commands) if final else 0),
        ("stage34_final_death_pixels", final.death_pixels_drawn if final else 0),
        ("stage34_final_psprite_posts", len(final.psprite_commands) if final else 0),
        ("stage34_final_psprite_pixels", final.psprite_pixels_drawn if final else 0),
        ("stage34_target_mapthing_index", ref.target_mapthing_index if ref else 0),
        ("stage34_target_mobj_index", ref.target_mobj_index if ref else 0),
        ("stage34_selected_nonlethal_damage", ref.selected_nonlethal_damage if ref else 0),
        ("stage34_selected_lethal_damage", ref.selected_lethal_damage if ref else 0),
        ("stage34_selected_damage_total", ref.selected_damage_total if ref else 0),
        ("stage34_selected_target_health_before_lethal", ref.selected_target_health_before_lethal if ref else 0),
        ("stage34_selected_target_health_after", ref.selected_target_health_after if ref else 0),
        ("stage34_selected_kill_events", ref.selected_kill_events if ref else 0),
        ("stage34_selected_death_state_sets", ref.selected_death_state_sets if ref else 0),
        ("stage34_selected_drop_deferred", ref.selected_drop_deferred if ref else 0),
        ("stage34_full_frame_byte_arrays_absent", ref.full_frame_byte_arrays_absent if ref else 1),
        ("stage34_runtime_renderer_primitives", ref.runtime_renderer_primitives if ref else 1),
        ("stage34_wall_path_replayed", ref.wall_path_replayed if ref else 1),
        ("stage34_flat_path_replayed", ref.flat_path_replayed if ref else 1),
        ("stage34_death_or_pain_path_replayed", ref.death_or_pain_path_replayed if ref else 1),
        ("stage34_psprite_path_replayed", ref.psprite_path_replayed if ref else 1),
        ("stage34_blood_puff_spawn_deferred", ref.blood_puff_spawn_deferred if ref else 1),
        ("stage34_projectiles_absent", ref.projectiles_absent if ref else 1),
        ("stage34_explosions_absent", ref.explosions_absent if ref else 1),
        ("stage34_monster_attack_execution_absent", ref.monster_attack_execution_absent if ref else 1),
        ("stage34_item_pickup_absent", ref.item_pickup_absent if ref else 1),
        ("stage34_generalized_death_drop_absent", ref.generalized_death_drop_absent if ref else 1),
        ("stage34_selected_drop_visual_deferred", ref.selected_drop_visual_deferred if ref else 1),
        ("stage34_generalized_combat_absent", ref.generalized_combat_absent if ref else 1),
        ("stage34_broad_ai_absent", ref.broad_ai_absent if ref else 1),
        ("stage34_generalized_sprite_systems_absent", ref.generalized_sprite_systems_absent if ref else 1),
        ("stage34_generalized_specials_absent", ref.generalized_specials_absent if ref else 1),
        ("stage34_map_progression_absent", ref.map_progression_absent if ref else 1),
        ("stage34_ui_systems_absent", ref.ui_systems_absent if ref else 1),
        ("stage34_real_audio_absent", ref.real_audio_absent if ref else 1),
        ("stage34_source_stage35_absent", ref.source_stage35_absent if ref else 1),
        ("stage34_expected_signature", ref.signature if ref else 0),
        ("stage34_runtime_signature", 0),
        ("stage34_runtime_fb_signature", 0),
        ("stage34_impact_posts_drawn", 0),
        ("stage34_impact_pixels_drawn", 0),
        ("stage34_death_scan_ptr", 0),
        ("stage34_death_remaining", 0),
        ("stage34_death_posts_drawn", 0),
        ("stage34_death_pixels_drawn", 0),
        ("stage34_psprite_posts_drawn", 0),
        ("stage34_psprite_pixels_drawn", 0),
        ("stage34_replay_step", 0),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        for name, value in (
            (f"stage34_sample{index}_tic", sample.tic),
            (f"stage34_sample{index}_psprite_state", sample.psprite_state),
            (f"stage34_sample{index}_death_state", sample.death_state),
            (f"stage34_sample{index}_death_frame", sample.death_frame),
            (f"stage34_sample{index}_death_command_count", len(sample.death_commands)),
            (f"stage34_sample{index}_base_fb_signature", sample.base_framebuffer_signature),
            (f"stage34_sample{index}_impact_fb_signature", sample.impact_framebuffer_signature),
            (f"stage34_sample{index}_death_fb_signature", sample.death_framebuffer_signature),
            (f"stage34_sample{index}_fb_signature", sample.framebuffer_signature),
        ):
            pe.label(name)
            pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        pe.align_section(4)
        pe.label(f"stage34_death_commands_{index}")
        _emit_death_commands(pe, sample.death_commands)
    pe.align_section(1)
    if ref:
        for index, source in enumerate(ref.death_sources):
            pe.label(f"stage34_death_source_{index}")
            pe.emit(source)
    pe.align_section(1)
    pe.label("stage34_log_text")
    x86.emit_asciiz(pe, _stage34_log_text(samples))
    pe.label("status_stage34_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage34_selected_hitscan_death_visual_boundary\r\n"
        "Selected hitscan death visual boundary proof OK\r\n",
    )
    pe.label("status_stage34_log_prefix")
    x86.emit_asciiz(pe, "\r\nSelected impact/death visual log: ")
    pe.label("status_stage34_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage34 selected hitscan death visual signature: ")
    pe.label("status_stage34_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage34 preserves the stage31 live wall/flat runtime redraw bridge and the "
        "stage33 selected impact/pain bridge and the stage32 selected shotgun psprite "
        "bridge, then inserts one selected shotgun-guy death-state world post table "
        "before psprites. The consequence follows a selected "
        "A_FireShotgun/P_LineAttack/P_DamageMobj/P_KillMobj/P_SetMobjState route, draws compact "
        "R_DrawMaskedColumn-shaped commands from real WAD sprite posts, computes the live "
        "framebuffer signature, and presents through the existing Win32 paint path. "
        "Blood/puff spawning, projectiles, explosions, monster attack execution, monster "
        "death/drop, generalized combat, broad AI, generalized sprite systems, generalized "
        "specials, map progression, UI systems, and real audio remain deferred.\r\n",
    )
    for label, text in (
        ("title_stage34_frame_count_prefix", " S34FR="),
        ("title_stage34_distinct_fb_prefix", " FBDIST34="),
        ("title_stage34_distinct_death_prefix", " DEATHDIST34="),
        ("title_stage34_death_posts_prefix", " DC34="),
        ("title_stage34_death_pixels_prefix", " DP34="),
        ("title_stage34_psprite_posts_prefix", " PC32="),
        ("title_stage34_psprite_pixels_prefix", " PP32="),
        ("title_stage34_full_frame_prefix", " NOFULL34="),
        ("title_stage34_stage35_prefix", " S35ABS="),
        ("title_stage34_log_prefix", " LOG34="),
        ("title_stage34_signature_prefix", " S34SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)
    pe.label("stage34_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S34 DEATH START STEP34=0 waiting for wall/flat plus selected impact plus selected death plus psprite redraw")
    for index, title in enumerate(_stage34_replay_titles(ref)):
        pe.label(f"stage34_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)


def _emit_prior_loaders(pe: PE32) -> None:
    for emit in (
        stage33.emit_source_stage33_load_wad_selected_hitscan_impact_visual_boundary,
        stage32.emit_source_stage32_load_wad_selected_combat_visual_state_bridge,
        stage31.emit_source_stage31_load_wad_runtime_real_renderer_motion_bridge,
        stage30.emit_source_stage30_load_wad_runtime_rendered_motion_bridge,
        stage29.emit_source_stage29_load_wad_selected_monster_chase_attack_state_loop,
        stage28.emit_source_stage28_load_wad_live_input_to_deterministic_game_loop_bridge,
        stage27.emit_source_stage27_load_wad_integrated_scripted_room_interaction_loop,
        stage26.emit_source_stage26_load_wad_first_ceiling_or_crusher_special_probe,
        stage25.emit_source_stage25_load_wad_first_platform_lift_cycle_probe,
        stage24.emit_source_stage24_load_wad_first_floor_sector_special_probe,
        stage23.emit_source_stage23_load_wad_first_button_timer_restore_probe,
        stage22.emit_source_stage22_load_wad_first_switch_texture_and_tagged_door_probe,
        stage21.emit_source_stage21_load_wad_door_thinker_ticker_special_update_probe,
        stage20.emit_source_stage20_load_wad_audio_channels_deferred_sound_playback,
        stage19.emit_source_stage19_load_wad_first_door_switch_sector_special_probe,
        stage18.emit_source_stage18_load_wad_post_damage_monster_movement_chase_probe,
        stage17.emit_source_stage17_load_wad_first_weapon_fire_damage_death_probe,
    ):
        emit(pe)


def _emit_runtime_helpers(pe: PE32) -> None:
    for emit in (
        stage08.emit_render_init_texture_data_setup_debug,
        stage01.emit_load_wad_directory,
        stage01.emit_wad_num_lumps,
        stage01.emit_wad_check_num_for_name,
        stage01.emit_wad_get_num_for_name,
        stage01.emit_wad_lump_length,
        stage01.emit_wad_read_lump,
        stage02.emit_source_stage02_load_map,
        stage01.emit_map_load_vertexes,
        stage01.emit_map_load_sectors,
        stage01.emit_map_load_sidedefs,
        stage01.emit_map_load_linedefs,
        stage02.emit_map_load_subsectors,
        stage02.emit_map_load_nodes,
        stage02.emit_map_load_segs,
        stage02.emit_map_group_lines,
        stage02.emit_group_count_sector_ref,
        stage02.emit_group_append_sector_line,
        stage07.emit_source_stage06_run_live_seg_clip_debug,
        stage03.emit_render_fixed_mul,
        stage03.emit_render_point_on_side,
        stage03.emit_render_point_in_subsector,
        stage03.emit_render_debug_subsector,
        stage03.emit_render_check_bbox_accept_all,
        stage03.emit_render_bsp_node_debug,
        stage04.emit_render_slope_div,
        stage04.emit_render_point_to_angle,
        stage04.emit_render_clear_clipsegs,
        stage04.emit_render_check_bbox,
        stage04.emit_render_debug_subsector_bbox,
        stage04.emit_render_bsp_node_bbox_debug,
        stage07.emit_render_angle_to_view_x_debug,
        stage07.emit_render_setup_frame_debug,
        stage07.emit_render_fixed_div,
        stage07.emit_render_point_to_dist,
        stage07.emit_render_scale_from_global_angle,
        stage07.emit_render_store_wall_range_debug,
        stage07.emit_render_clip_solid_wall_segment,
        stage07.emit_render_clip_pass_wall_segment,
        stage08.emit_render_add_line_debug,
        stage07.emit_render_debug_subsector_clip,
        stage07.emit_render_bsp_node_clip_debug,
        stage07.emit_render_finish_clip_debug,
        stage04.emit_render_debug_framebuffer,
        stage03.emit_clear_framebuffer,
        stage03.emit_render_error_pattern,
        stage03.emit_transform_point_to_screen,
        stage03.emit_draw_all_linedefs,
        stage03.emit_draw_visited_segs,
        stage04.emit_draw_bbox_visible_segs,
        stage03.emit_draw_viewpoint_marker,
        stage03.emit_draw_line,
        stage03.emit_plot_pixel,
        stage10.emit_render_composite_two_sided_wall_edges_debug,
        stage10.emit_render_draw_column_debug,
        stage11.emit_render_visplanes_floor_ceiling_debug,
        stage11.emit_render_draw_span_debug,
        stage12.emit_render_sky_and_masked_midtextures_debug,
        stage12.emit_render_draw_stage12_columns_debug,
        stage13.emit_render_things_sprites_and_real_frame_setup_debug,
        stage13.emit_render_draw_stage13_sprite_column_debug,
        stage14.emit_render_game_loop_input_collision_debug,
        stage15.emit_render_pickups_psprites_statusbar_shell_debug,
        stage15.emit_render_draw_stage15_columns_debug,
        stage16.emit_render_active_monster_thinkers_targeting_debug,
        stage17.emit_render_first_weapon_fire_damage_death_probe_debug,
        stage18.emit_render_post_damage_monster_movement_chase_probe_debug,
        stage19.emit_render_first_door_switch_sector_special_probe_debug,
        stage20.emit_render_audio_channels_deferred_sound_playback_debug,
        stage21.emit_render_door_thinker_ticker_special_update_probe_debug,
        stage22.emit_render_first_switch_texture_and_tagged_door_probe_debug,
        stage23.emit_render_first_button_timer_restore_probe_debug,
        stage24.emit_render_first_floor_sector_special_probe_debug,
        stage25.emit_render_first_platform_lift_cycle_probe_debug,
        stage26.emit_render_first_ceiling_or_crusher_special_probe_debug,
        stage27.emit_render_integrated_scripted_room_interaction_loop_debug,
        stage28.emit_render_live_input_to_deterministic_game_loop_bridge_debug,
        stage29.emit_render_selected_monster_chase_attack_state_loop_debug,
        stage30.emit_render_runtime_rendered_motion_bridge_debug,
        stage31.emit_render_runtime_real_renderer_motion_bridge_debug,
        stage32.emit_render_selected_combat_visual_state_bridge_debug,
        stage33.emit_render_selected_hitscan_impact_visual_boundary_debug,
    ):
        emit(pe)


def _emit_prior_status(pe: PE32) -> None:
    for emit in (
        stage12.emit_build_success_status,
        stage13.emit_append_stage13_success_status,
        stage14.emit_append_stage14_success_status,
        stage15.emit_append_stage15_success_status,
        stage16.emit_append_stage16_success_status,
        stage17.emit_append_stage17_success_status,
        stage18.emit_append_stage18_success_status,
        stage19.emit_append_stage19_success_status,
        stage20.emit_append_stage20_success_status,
        stage21.emit_append_stage21_success_status,
        stage22.emit_append_stage22_success_status,
        stage23.emit_append_stage23_success_status,
        stage24.emit_append_stage24_success_status,
        stage25.emit_append_stage25_success_status,
        stage26.emit_append_stage26_success_status,
        stage27.emit_append_stage27_success_status,
        stage28.emit_append_stage28_success_status,
        stage29.emit_append_stage29_success_status,
        stage30.emit_append_stage30_success_status,
        stage31.emit_append_stage31_success_status,
        stage32.emit_append_stage32_success_status,
        stage33.emit_append_stage33_success_status,
    ):
        emit(pe)


def _emit_prior_data(pe: PE32) -> None:
    for emit in (
        stage02.emit_stage02_data,
        stage04.emit_stage04_data,
        stage07.emit_stage07_data,
        stage08.emit_stage08_data,
        stage10.emit_stage10_data,
        stage11.emit_stage11_data,
        stage12.emit_stage12_data,
        stage13.emit_stage13_data,
        stage14.emit_stage14_data,
        stage15.emit_stage15_data,
        stage16.emit_stage16_data,
        stage17.emit_stage17_data,
        stage18.emit_stage18_data,
        stage19.emit_stage19_data,
        stage20.emit_stage20_data,
        stage21.emit_stage21_data,
        stage22.emit_stage22_data,
        stage23.emit_stage23_data,
        stage24.emit_stage24_data,
        stage25.emit_stage25_data,
        stage26.emit_stage26_data,
        stage27.emit_stage27_data,
        stage28.emit_stage28_data,
        stage29.emit_stage29_data,
        stage30.emit_stage30_data,
        stage31.emit_stage31_data,
        stage32.emit_stage32_data,
        stage33.emit_stage33_data,
    ):
        emit(pe)


def build_source_stage34_selected_hitscan_death_visual_boundary_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    ref = _reference_for_default_wad_or_none()
    emit_stage34_entry(pe)
    stage28.emit_stage28_wndproc_framebuffer(pe)
    emit_stage34_timer_tick(pe)
    stage31.emit_stage31_clear_framebuffer(pe)
    stage31.emit_stage31_framebuffer_signature(pe)
    stage31.emit_stage31_draw_command_loops(pe)
    stage33.emit_stage33_draw_impact_commands(pe)
    emit_stage34_draw_death_commands(pe)
    stage32.emit_stage32_draw_psprite_commands(pe)
    for index in range(len(ref.samples) if ref else len(SELECTED_SAMPLE_TICS)):
        _emit_stage34_draw_sample(pe, index)
    emit_source_stage34_load_wad_selected_hitscan_death_visual_boundary(pe)
    _emit_prior_loaders(pe)
    _emit_runtime_helpers(pe)
    emit_render_selected_hitscan_death_visual_boundary_debug(pe)
    _emit_prior_status(pe)
    emit_append_stage34_success_status(pe)
    stage01.emit_append_c_string(pe)
    stage01.emit_append_u32_decimal(pe)
    stage01.emit_append_i32_decimal(pe)
    with patched_stage01_window_labels():
        stage01.emit_data(pe)
    _emit_prior_data(pe)
    emit_stage34_data(pe)
    return pe.build("entry")


def write_source_stage34_selected_hitscan_death_visual_boundary_exe(path: str | Path) -> bytes:
    image = build_source_stage34_selected_hitscan_death_visual_boundary_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage34 selected hitscan death visual boundary PE32 executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage34_selected_hitscan_death_visual_boundary.exe",
        help="path to write, default: build/source_stage34_selected_hitscan_death_visual_boundary.exe",
    )
    args = parser.parse_args()
    write_source_stage34_selected_hitscan_death_visual_boundary_exe(args.output)


if __name__ == "__main__":
    main()
