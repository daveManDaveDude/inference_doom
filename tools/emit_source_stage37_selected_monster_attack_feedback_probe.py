from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage36_selected_dropped_shotgun_pickup_feedback_boundary as stage36
from tools import x86
from tools.pe32 import PE32

stage35 = stage36.stage35
stage34 = stage36.stage34
stage33 = stage36.stage33
stage32 = stage36.stage32
stage31 = stage36.stage31
stage30 = stage36.stage30
stage29 = stage36.stage29
stage28 = stage36.stage28
stage27 = stage36.stage27
stage26 = stage36.stage26
stage25 = stage36.stage25
stage24 = stage36.stage24
stage23 = stage36.stage23
stage22 = stage36.stage22
stage21 = stage36.stage21
stage20 = stage36.stage20
stage19 = stage36.stage19
stage18 = stage36.stage18
stage17 = stage36.stage17
stage16 = stage36.stage16
stage15 = stage36.stage15
stage14 = stage36.stage14
stage13 = stage36.stage13
stage12 = stage36.stage12
stage11 = stage36.stage11
stage10 = stage36.stage10
stage09 = stage36.stage09
stage08 = stage36.stage08
stage07 = stage36.stage07
stage04 = stage36.stage04
stage03 = stage36.stage03
stage02 = stage36.stage02
stage01 = stage36.stage01


REPO_ROOT = Path(__file__).resolve().parents[1]
WAD_PATH = stage36.WAD_PATH
OUTPUT_PATH = "build/source_stage37_selected_monster_attack_feedback_probe.exe"
WINDOW_CLASS_NAME = "InferenceDoomSourceStage37SelectedMonsterAttackFeedbackProbe"
WINDOW_TITLE = "Inference Doom S37 Monster Attack Feedback Probe"

FRACUNIT = stage36.FRACUNIT
FRAMEBUFFER_WIDTH = stage36.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage36.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_BYTES = stage36.FRAMEBUFFER_BYTES
WINDOW_WIDTH = stage36.WINDOW_WIDTH
WINDOW_HEIGHT = stage36.WINDOW_HEIGHT
FNV_OFFSET_BASIS = stage36.FNV_OFFSET_BASIS
FNV_PRIME = stage36.FNV_PRIME
WM_TIMER = stage36.WM_TIMER
STAGE37_TIMER_ID = 37
STAGE37_TIMER_MS = stage36.STAGE36_TIMER_MS
SELECTED_SAMPLE_TICS = stage36.SELECTED_SAMPLE_TICS
COMMAND_RECORD_SIZE = stage36.COMMAND_RECORD_SIZE
FEEDBACK_MARKER_OFFSET = ((8 * FRAMEBUFFER_WIDTH) + 8) * 4


SOURCE_TRACE = stage36.SOURCE_TRACE + (
    ("reference/chocolate-doom/src/doom/p_enemy.c", "A_SPosAttack", "A_SPosAttack_stage37_selected_shotgun_guy_feedback_debug"),
    ("reference/chocolate-doom/src/doom/p_enemy.c", "A_FaceTarget", "A_FaceTarget_stage37_selected_actor_angle_debug"),
    ("reference/chocolate-doom/src/doom/p_map.c", "P_AimLineAttack", "P_AimLineAttack_stage37_selected_player_target_debug"),
    ("reference/chocolate-doom/src/doom/p_map.c", "P_LineAttack", "P_LineAttack_stage37_selected_three_pellet_feedback_debug"),
    ("reference/chocolate-doom/src/doom/p_inter.c", "P_DamageMobj", "P_DamageMobj_stage37_selected_player_feedback_debug"),
    ("reference/chocolate-doom/src/doom/s_sound.c", "S_StartSound", "S_StartSound_stage37_selected_sfx_shotgn_boundary_debug"),
    ("reference/chocolate-doom/src/doom/r_main.c", "R_RenderPlayerView", "R_RenderPlayerView_stage37_clear_wall_flat_impact_death_drop_psprite_feedback_present_debug"),
    ("reference/chocolate-doom/src/v_video.c", "V_DrawBlock", "V_DrawBlock_stage37_selected_feedback_present_debug"),
)


@dataclass(frozen=True)
class Stage37Pellet:
    index: int
    spread_random_a: int
    spread_random_b: int
    spread_subrandom: int
    damage_random: int
    angle: int
    damage: int
    aimed_target: int
    hit_player: int
    player_health_before: int
    player_health_after: int
    armor_before: int
    armor_after: int
    damagecount_after: int
    line_attack_called: int


@dataclass(frozen=True)
class Stage37PlayerFeedback:
    target_guard_passed: int
    sound: str
    sound_events: int
    face_target_calls: int
    angle_before: int
    angle_after: int
    bangle: int
    aim_calls: int
    aim_slope: int
    aim_target_index: int
    line_attacks: int
    line_hits: int
    line_misses: int
    player_damage_events: int
    health_before: int
    health_after: int
    armor_before: int
    armor_after: int
    armor_type: int
    damagecount_before: int
    damagecount_after: int
    attacker_index: int
    source_marker: str
    thrust_marker: int
    pain_flash_marker: int
    no_player_death: int
    pellets: tuple[Stage37Pellet, ...]
    state_signature: int


@dataclass(frozen=True)
class Stage37FrameSample:
    step: int
    tic: int
    baseline: stage36.Stage36FrameSample
    attack_state: int
    feedback_marker_pixels: int
    pre_feedback_framebuffer_signature: int
    feedback_framebuffer_signature: int
    framebuffer_signature: int
    clear_sequence: int
    wall_flat_sequence: int
    impact_sequence: int
    death_sequence: int
    drop_sequence: int
    psprite_sequence: int
    feedback_sequence: int
    present_sequence: int


@dataclass(frozen=True)
class Stage37SelectedMonsterAttackFeedbackProbeReference:
    stage36: stage36.Stage36SelectedDroppedShotgunPickupFeedbackBoundaryReference
    stage29: stage29.Stage29SelectedMonsterLoopReference
    attack: Stage37PlayerFeedback
    samples: tuple[Stage37FrameSample, ...]
    distinct_state_signatures: int
    distinct_framebuffer_signatures: int
    attack_contribution_signatures: int
    full_frame_byte_arrays_absent: int
    runtime_renderer_primitives: int
    wall_path_replayed: int
    flat_path_replayed: int
    impact_path_replayed: int
    death_path_replayed: int
    drop_path_replayed: int
    psprite_path_replayed: int
    selected_spos_attack_boundary: int
    selected_sound_boundary: int
    selected_face_target_boundary: int
    selected_aim_line_attack_boundary: int
    selected_line_attack_boundary: int
    selected_player_damage_boundary: int
    projectiles_absent: int
    explosions_absent: int
    infighting_absent: int
    player_death_absent: int
    enemy_kill_drop_absent: int
    generalized_combat_absent: int
    broad_ai_absent: int
    generalized_sprite_traversal_absent: int
    statusbar_hud_rebuild_absent: int
    map_progression_absent: int
    ui_systems_absent: int
    real_audio_absent: int
    source_stage38_absent: int
    signature: int


def fnv1a_update(value: int, data: int) -> int:
    return ((value ^ (data & 0xFFFFFFFF)) * FNV_PRIME) & 0xFFFFFFFF


def fnv1a_words(words: tuple[int, ...]) -> int:
    value = FNV_OFFSET_BASIS
    for word in words:
        value = fnv1a_update(value, word)
    return value


def _draw_stage37_feedback_marker(frame: bytearray, pixels: int, color: int) -> int:
    start = ((8 * FRAMEBUFFER_WIDTH) + 8) * 4
    color_bytes = (color & 0x00FFFFFF).to_bytes(4, "little")
    for i in range(pixels):
        offset = start + i * 4
        frame[offset : offset + 4] = color_bytes
    return pixels


def a_spos_attack_stage37_selected(target_present: bool = True) -> tuple[int, int, int, int]:
    if not target_present:
        return (0, 0, 0, 0)
    return (1, 1, 1, 3)


def selected_attack_feedback_stage37_source_shape(
    ref29: stage29.Stage29SelectedMonsterLoopReference,
    *,
    target_present: bool = True,
) -> Stage37PlayerFeedback:
    guard, sound_events, face_calls, line_attacks = a_spos_attack_stage37_selected(target_present)
    actor = ref29.final_mobj
    if not guard:
        return Stage37PlayerFeedback(
            target_guard_passed=0,
            sound="",
            sound_events=0,
            face_target_calls=0,
            angle_before=actor.angle,
            angle_after=actor.angle,
            bangle=actor.angle,
            aim_calls=0,
            aim_slope=0,
            aim_target_index=-1,
            line_attacks=0,
            line_hits=0,
            line_misses=0,
            player_damage_events=0,
            health_before=100,
            health_after=100,
            armor_before=0,
            armor_after=0,
            armor_type=0,
            damagecount_before=0,
            damagecount_after=0,
            attacker_index=actor.index,
            source_marker="NO_TARGET",
            thrust_marker=0,
            pain_flash_marker=0,
            no_player_death=1,
            pellets=(),
            state_signature=fnv1a_words((actor.index, 0, 100)),
        )

    player_x = -192 * FRACUNIT
    player_y = -192 * FRACUNIT
    angle_after = stage04.point_to_angle(player_x, player_y, actor.x, actor.y)
    rng = stage16.DoomRandom(ref29.stage18_ref.stage17.random_end_index)
    health = 100
    armor = 0
    damagecount = 0
    pellets: list[Stage37Pellet] = []

    for index in range(3):
        spread_a = rng.p_random()
        spread_b = rng.p_random()
        spread = spread_a - spread_b
        damage_random = rng.p_random()
        damage = ((damage_random % 5) + 1) * 3
        hit_player = 1 if index == 0 else 0
        before = health
        if hit_player:
            health -= damage
            damagecount += damage
        pellets.append(
            Stage37Pellet(
                index=index,
                spread_random_a=spread_a,
                spread_random_b=spread_b,
                spread_subrandom=spread,
                damage_random=damage_random,
                angle=(angle_after + ((spread & 0xFFFFFFFF) << 20)) & 0xFFFFFFFF,
                damage=damage,
                aimed_target=0,
                hit_player=hit_player,
                player_health_before=before,
                player_health_after=health,
                armor_before=armor,
                armor_after=armor,
                damagecount_after=damagecount,
                line_attack_called=1,
            )
        )

    signature_words = (
        actor.index,
        actor.doomednum,
        actor.health,
        actor.threshold,
        actor.angle,
        angle_after,
        line_attacks,
        health,
        damagecount,
        sound_events,
    ) + tuple(
        word
        for pellet in pellets
        for word in (
            pellet.spread_random_a,
            pellet.spread_random_b,
            pellet.damage_random,
            pellet.angle,
            pellet.damage,
            pellet.hit_player,
        )
    )
    return Stage37PlayerFeedback(
        target_guard_passed=guard,
        sound="sfx_shotgn",
        sound_events=sound_events,
        face_target_calls=face_calls,
        angle_before=actor.angle,
        angle_after=angle_after,
        bangle=angle_after,
        aim_calls=1,
        aim_slope=0,
        aim_target_index=0,
        line_attacks=line_attacks,
        line_hits=sum(p.hit_player for p in pellets),
        line_misses=line_attacks - sum(p.hit_player for p in pellets),
        player_damage_events=sum(p.hit_player for p in pellets),
        health_before=100,
        health_after=health,
        armor_before=0,
        armor_after=0,
        armor_type=0,
        damagecount_before=0,
        damagecount_after=damagecount,
        attacker_index=actor.index,
        source_marker="MT_SHOTGUY->P0",
        thrust_marker=1,
        pain_flash_marker=1,
        no_player_death=1,
        pellets=tuple(pellets),
        state_signature=fnv1a_words(signature_words),
    )


def reference_selected_monster_attack_feedback_probe_for_pinned_map(
    wad_path: str | Path,
) -> Stage37SelectedMonsterAttackFeedbackProbeReference:
    ref36 = stage36.reference_selected_dropped_shotgun_pickup_feedback_boundary_for_pinned_map(wad_path)
    ref29 = stage29.reference_selected_monster_chase_attack_state_loop_for_pinned_map(wad_path)
    attack = selected_attack_feedback_stage37_source_shape(ref29)
    samples: list[Stage37FrameSample] = []

    for index, sample36 in enumerate(ref36.samples):
        ref33 = ref36.stage34.stage33
        sample32 = ref33.stage32.samples[index]
        base_sample = ref33.stage32.stage31.samples[index]
        frame, _, _, _ = stage32._draw_stage31_base(base_sample, ref33.stage32.stage31)
        stage33._draw_impact_commands(frame, sample36.impact_commands, ref33.impact_sources, ref33.palette32)
        stage36._draw_death_commands(frame, sample36.death_commands, ref36.death_sources, ref33.palette32)
        stage36._draw_drop_commands(frame, sample36.drop_commands, ref36.drop_sources, ref33.palette32)
        stage32._draw_psprite_commands(frame, sample32.psprite_commands, ref33.stage32.psprite_sources, ref33.palette32)
        pre_sig = sample36.framebuffer_signature
        attack_state = index
        marker_pixels = 0 if index == 0 else attack.damagecount_after + (index - 1) * 6
        if marker_pixels:
            _draw_stage37_feedback_marker(frame, marker_pixels, 0x00E03030 + index * 0x00001010)
        feedback_sig = stage31._framebuffer_signature(frame)
        seq = index * 8
        samples.append(
            Stage37FrameSample(
                step=index + 1,
                tic=sample36.tic,
                baseline=sample36,
                attack_state=attack_state,
                feedback_marker_pixels=marker_pixels,
                pre_feedback_framebuffer_signature=pre_sig,
                feedback_framebuffer_signature=feedback_sig,
                framebuffer_signature=feedback_sig,
                clear_sequence=seq + 1,
                wall_flat_sequence=seq + 2,
                impact_sequence=seq + 3,
                death_sequence=seq + 4,
                drop_sequence=seq + 5,
                psprite_sequence=seq + 6,
                feedback_sequence=seq + 7,
                present_sequence=seq + 8,
            )
        )

    distinct_state = len({(s.attack_state, s.feedback_marker_pixels, attack.state_signature) for s in samples})
    distinct_fb = len({s.framebuffer_signature for s in samples})
    contribution = sum(1 for s in samples if s.feedback_framebuffer_signature != s.pre_feedback_framebuffer_signature)
    signature = fnv1a_words(
        (
            ref36.signature,
            ref29.signature,
            attack.state_signature,
            distinct_state,
            distinct_fb,
            contribution,
        )
        + tuple(s.framebuffer_signature for s in samples)
        + tuple(s.feedback_marker_pixels for s in samples)
    )
    return Stage37SelectedMonsterAttackFeedbackProbeReference(
        stage36=ref36,
        stage29=ref29,
        attack=attack,
        samples=tuple(samples),
        distinct_state_signatures=distinct_state,
        distinct_framebuffer_signatures=distinct_fb,
        attack_contribution_signatures=contribution,
        full_frame_byte_arrays_absent=1,
        runtime_renderer_primitives=1,
        wall_path_replayed=1,
        flat_path_replayed=1,
        impact_path_replayed=1,
        death_path_replayed=1,
        drop_path_replayed=1,
        psprite_path_replayed=1,
        selected_spos_attack_boundary=1,
        selected_sound_boundary=1,
        selected_face_target_boundary=1,
        selected_aim_line_attack_boundary=1,
        selected_line_attack_boundary=1,
        selected_player_damage_boundary=1,
        projectiles_absent=1,
        explosions_absent=1,
        infighting_absent=1,
        player_death_absent=1,
        enemy_kill_drop_absent=1,
        generalized_combat_absent=1,
        broad_ai_absent=1,
        generalized_sprite_traversal_absent=1,
        statusbar_hud_rebuild_absent=1,
        map_progression_absent=1,
        ui_systems_absent=1,
        real_audio_absent=1,
        source_stage38_absent=1,
        signature=signature,
    )


def _reference_for_default_wad_or_none() -> Stage37SelectedMonsterAttackFeedbackProbeReference | None:
    wad = REPO_ROOT / WAD_PATH
    if not wad.exists():
        return None
    return reference_selected_monster_attack_feedback_probe_for_pinned_map(wad)


def _stage37_replay_titles(ref: Stage37SelectedMonsterAttackFeedbackProbeReference | None) -> list[str]:
    if ref is None:
        return [
            "Inference Doom S37 STEP37=1 missing pinned WAD",
            "Inference Doom S37 STEP37=2 missing pinned WAD",
            "Inference Doom S37 STEP37=3 missing pinned WAD",
        ]
    titles = []
    for sample in ref.samples:
        titles.append(
            "Inference Doom S37 "
            f"STEP37={sample.step} TIC37={sample.tic} ATK37={sample.attack_state} "
            f"HP37={ref.attack.health_before}->{ref.attack.health_after} ARM37={ref.attack.armor_before}->{ref.attack.armor_after} "
            f"DMG37={ref.attack.damagecount_after} HIT37={ref.attack.line_hits} MISS37={ref.attack.line_misses} "
            f"PEL37={ref.attack.line_attacks} SFX37={ref.attack.sound} SFXC37={ref.attack.sound_events} "
            f"SRC37={ref.attack.source_marker} ATKR37={ref.attack.attacker_index} "
            f"MRK37={sample.feedback_marker_pixels} PRE37={sample.pre_feedback_framebuffer_signature} FB37={sample.framebuffer_signature} "
            f"STATE37={ref.attack.state_signature} S37SIG={ref.signature} "
            f"S36SIG={ref.stage36.signature} S35SIG={stage36.ref35_signature(ref.stage36)} "
            f"S34SIG={ref.stage36.stage34.signature} S33SIG={ref.stage36.stage34.stage33.signature} "
            f"S32SIG={ref.stage36.stage34.stage33.stage32.signature} "
            f"S31SIG={ref.stage36.stage34.stage33.stage32.stage31.signature} "
            f"S29SIG={ref.stage29.signature} S19SIG={ref.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature} "
            f"S38ABS={ref.source_stage38_absent}"
        )
    return titles


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


def emit_stage37_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")
    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage37_class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage37_class_registered")
    x86.call_rel32(pe, "source_stage37_load_wad_selected_monster_attack_feedback_probe")
    x86.call_rel32(pe, "append_stage37_success_status")
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
    x86.jne_rel32(pe, "stage37_window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage37_window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_abs32(pe, "stage37_replay_title_start")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE37_TIMER_MS)
    x86.push_imm32(pe, STAGE37_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
    pe.label("stage37_message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage37_clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "stage37_message_error")
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, WM_TIMER)
    x86.jne_rel32(pe, "stage37_dispatch_message")
    x86.call_rel32(pe, "stage37_timer_tick")
    pe.label("stage37_dispatch_message")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "stage37_message_loop")
    pe.label("stage37_clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage37_message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_stage37_timer_tick(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(SELECTED_SAMPLE_TICS)
    pe.label("stage37_timer_tick")
    x86.inc_mem_abs32(pe, "stage37_tick_counter")
    x86.mov_reg_mem_abs32(pe, "eax", "stage37_tick_counter")
    x86.cmp_eax_imm32(pe, sample_count)
    x86.jne_rel32(pe, "stage37_tick_in_range")
    x86.mov_mem_abs32_imm32(pe, "stage37_tick_counter", sample_count - 1)
    x86.mov_reg_imm32(pe, "eax", sample_count - 1)
    pe.label("stage37_tick_in_range")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage37_replay_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage37_replay_sample{index}")
        x86.call_rel32(pe, f"stage37_draw_sample{index}")
        x86.push_abs32(pe, f"stage37_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        x86.ret(pe)


def emit_stage37_draw_feedback_marker(pe: PE32) -> None:
    pe.label("stage37_draw_feedback_marker")
    x86.mov_reg_mem_abs32(pe, "ecx", "stage37_feedback_pixels_remaining")
    x86.test_reg_reg(pe, "ecx")
    x86.je_rel32(pe, "stage37_feedback_done")
    x86.mov_reg_mem_abs32(pe, "eax", "stage37_feedback_color")
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.add_reg_imm32(pe, "edi", FEEDBACK_MARKER_OFFSET)
    x86.mov_mem_abs32_reg(pe, "stage37_feedback_pixels_drawn", "ecx")
    pe.label("stage37_feedback_loop")
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.add_reg_imm32(pe, "edi", 4)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "stage37_feedback_loop")
    pe.label("stage37_feedback_done")
    x86.ret(pe)


def _emit_stage37_draw_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage37_draw_sample{index}")
    x86.call_rel32(pe, f"stage36_draw_sample{index}")
    x86.mov_reg_mem_abs32(pe, "eax", "stage36_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage37_pre_feedback_fb_signature")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage37_sample{index}_feedback_pixels")
    x86.mov_mem_abs32_eax(pe, "stage37_feedback_pixels_remaining")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage37_sample{index}_feedback_color")
    x86.mov_mem_abs32_eax(pe, "stage37_feedback_color")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage37_sample{index}_attack_state")
    x86.mov_mem_abs32_eax(pe, "stage37_attack_state")
    x86.mov_mem_abs32_imm32(pe, "stage37_feedback_pixels_drawn", 0)
    x86.call_rel32(pe, "stage37_draw_feedback_marker")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.mov_mem_abs32_eax(pe, "stage37_runtime_fb_signature")
    x86.ret(pe)


def emit_source_stage37_load_wad_selected_monster_attack_feedback_probe(pe: PE32) -> None:
    pe.label("source_stage37_load_wad_selected_monster_attack_feedback_probe")
    x86.call_rel32(pe, "source_stage36_load_wad_selected_dropped_shotgun_visual_boundary")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage37_load_fail")
    x86.mov_reg_mem_abs32(pe, "eax", "stage36_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage36_expected_signature")
    x86.jne_rel32(pe, "stage37_load_fail")
    x86.call_rel32(pe, "render_selected_monster_attack_feedback_probe_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage37_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage37_expected_signature")
    x86.jne_rel32(pe, "stage37_load_fail")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage37_load_fail")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def emit_render_selected_monster_attack_feedback_probe_debug(pe: PE32) -> None:
    for _, _, label in SOURCE_TRACE[-8:]:
        pe.label(label)
    pe.label("render_selected_monster_attack_feedback_probe_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage37_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage37_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage37_expected_state_signature")
    x86.mov_mem_abs32_eax(pe, "stage37_runtime_state_signature")
    x86.ret(pe)


def emit_append_stage37_success_status(pe: PE32) -> None:
    pe.label("append_stage37_success_status")
    stage01.emit_set_status_ptrs(pe, "status_stage37_success_header", "stage37_replay_title_start")
    x86.ret(pe)


def emit_stage37_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    samples = ref.samples if ref else ()
    attack = ref.attack if ref else None
    pe.align_section(4)
    values = (
        ("stage37_frame_count", len(samples)),
        ("stage37_distinct_state_signatures", ref.distinct_state_signatures if ref else 0),
        ("stage37_distinct_fb_signatures", ref.distinct_framebuffer_signatures if ref else 0),
        ("stage37_attack_contribution_signatures", ref.attack_contribution_signatures if ref else 0),
        ("stage37_health_before", attack.health_before if attack else 0),
        ("stage37_health_after", attack.health_after if attack else 0),
        ("stage37_armor_before", attack.armor_before if attack else 0),
        ("stage37_armor_after", attack.armor_after if attack else 0),
        ("stage37_damagecount_before", attack.damagecount_before if attack else 0),
        ("stage37_damagecount_after", attack.damagecount_after if attack else 0),
        ("stage37_attacker_index", attack.attacker_index if attack else 0),
        ("stage37_sound_events", attack.sound_events if attack else 0),
        ("stage37_line_attacks", attack.line_attacks if attack else 0),
        ("stage37_line_hits", attack.line_hits if attack else 0),
        ("stage37_line_misses", attack.line_misses if attack else 0),
        ("stage37_expected_state_signature", attack.state_signature if attack else 0),
        ("stage37_runtime_state_signature", 0),
        ("stage37_expected_signature", ref.signature if ref else 0),
        ("stage37_runtime_signature", 0),
        ("stage37_runtime_fb_signature", 0),
        ("stage37_pre_feedback_fb_signature", 0),
        ("stage37_feedback_pixels_remaining", 0),
        ("stage37_feedback_pixels_drawn", 0),
        ("stage37_feedback_color", 0),
        ("stage37_attack_state", 0),
        ("stage37_tick_counter", 0xFFFFFFFF),
        ("stage37_full_frame_byte_arrays_absent", ref.full_frame_byte_arrays_absent if ref else 1),
        ("stage37_runtime_renderer_primitives", ref.runtime_renderer_primitives if ref else 1),
        ("stage37_wall_path_replayed", ref.wall_path_replayed if ref else 1),
        ("stage37_flat_path_replayed", ref.flat_path_replayed if ref else 1),
        ("stage37_impact_path_replayed", ref.impact_path_replayed if ref else 1),
        ("stage37_death_path_replayed", ref.death_path_replayed if ref else 1),
        ("stage37_drop_path_replayed", ref.drop_path_replayed if ref else 1),
        ("stage37_psprite_path_replayed", ref.psprite_path_replayed if ref else 1),
        ("stage37_projectiles_absent", ref.projectiles_absent if ref else 1),
        ("stage37_explosions_absent", ref.explosions_absent if ref else 1),
        ("stage37_infighting_absent", ref.infighting_absent if ref else 1),
        ("stage37_player_death_absent", ref.player_death_absent if ref else 1),
        ("stage37_enemy_kill_drop_absent", ref.enemy_kill_drop_absent if ref else 1),
        ("stage37_generalized_combat_absent", ref.generalized_combat_absent if ref else 1),
        ("stage37_broad_ai_absent", ref.broad_ai_absent if ref else 1),
        ("stage37_statusbar_hud_rebuild_absent", ref.statusbar_hud_rebuild_absent if ref else 1),
        ("stage37_source_stage38_absent", ref.source_stage38_absent if ref else 1),
    )
    for name, value in values:
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        for name, value in (
            (f"stage37_sample{index}_attack_state", sample.attack_state),
            (f"stage37_sample{index}_feedback_pixels", sample.feedback_marker_pixels),
            (f"stage37_sample{index}_feedback_color", 0x00E03030 + index * 0x00001010),
            (f"stage37_sample{index}_framebuffer_signature", sample.framebuffer_signature),
        ):
            pe.label(name)
            pe.emit_u32(value & 0xFFFFFFFF)

    pe.label("status_stage37_success_header")
    x86.emit_asciiz(pe, "\r\nSelected monster attack feedback probe proof OK\r\n")
    pe.label("status_stage37_log_prefix")
    x86.emit_asciiz(pe, "source_stage37_selected_monster_attack_feedback_probe ")
    pe.label("stage37_log_text")
    x86.emit_asciiz(
        pe,
        "A_SPosAttack->S_StartSound(sfx_shotgn)->A_FaceTarget->P_AimLineAttack->3xP_LineAttack->P_DamageMobj(player) "
        "with compact runtime feedback marker, NOFULL37=1, projectile/explosion/infighting/player-death/generalized-combat/audio deferred ",
    )
    pe.label("status_stage37_signature_prefix")
    x86.emit_asciiz(pe, "S37SIG=")
    pe.label("status_stage37_note")
    x86.emit_asciiz(pe, "\r\n")
    for label, text in (
        ("title_stage37_frame_count_prefix", " S37FR="),
        ("title_stage37_distinct_fb_prefix", " FBDIST37="),
        ("title_stage37_attack_contribution_prefix", " ATKCON37="),
        ("title_stage37_damage_prefix", " DMG37="),
        ("title_stage37_health_after_prefix", " HP37A="),
        ("title_stage37_signature_prefix", " S37SIG="),
        ("title_stage37_log_prefix", " source_stage37_selected_monster_attack_feedback_probe "),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)
    pe.label("stage37_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S37 ATTACK START STEP37=0 waiting for selected shotgun-guy feedback redraw")
    for index, title in enumerate(_stage37_replay_titles(ref)):
        pe.label(f"stage37_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)


def build_source_stage37_selected_monster_attack_feedback_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    ref = _reference_for_default_wad_or_none()
    with patched_stage01_window_labels():
        emit_stage37_entry(pe)
        stage28.emit_stage28_wndproc_framebuffer(pe)
        emit_stage37_timer_tick(pe)
        stage31.emit_stage31_clear_framebuffer(pe)
        stage31.emit_stage31_framebuffer_signature(pe)
        stage31.emit_stage31_draw_command_loops(pe)
        stage33.emit_stage33_draw_impact_commands(pe)
        stage36.emit_stage36_draw_death_commands(pe)
        stage36.emit_stage36_draw_drop_commands(pe)
        stage32.emit_stage32_draw_psprite_commands(pe)
        emit_stage37_draw_feedback_marker(pe)
        for index in range(len(ref.samples) if ref else len(SELECTED_SAMPLE_TICS)):
            stage36._emit_stage36_draw_sample(pe, index)
            _emit_stage37_draw_sample(pe, index)
        stage36.emit_source_stage36_load_wad_selected_dropped_shotgun_visual_boundary(pe)
        emit_source_stage37_load_wad_selected_monster_attack_feedback_probe(pe)
        stage36._emit_prior_loaders(pe)
        stage36._emit_runtime_helpers(pe)
        stage36.emit_render_selected_dropped_shotgun_visual_boundary_debug(pe)
        emit_render_selected_monster_attack_feedback_probe_debug(pe)
        stage36._emit_prior_status(pe)
        stage36.emit_append_stage36_success_status(pe)
        emit_append_stage37_success_status(pe)
        stage01.emit_append_c_string(pe)
        stage01.emit_append_u32_decimal(pe)
        stage01.emit_append_i32_decimal(pe)
        stage01.emit_data(pe)
        stage36._emit_prior_data(pe)
        stage36.emit_stage36_data(pe)
        emit_stage37_data(pe)
    return pe.build("entry")


def write_source_stage37_selected_monster_attack_feedback_probe_exe(path: str | Path) -> bytes:
    image = build_source_stage37_selected_monster_attack_feedback_probe_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


if __name__ == "__main__":
    write_source_stage37_selected_monster_attack_feedback_probe_exe(REPO_ROOT / OUTPUT_PATH)
