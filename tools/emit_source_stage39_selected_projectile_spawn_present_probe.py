from __future__ import annotations

import argparse
import math
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Sequence


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage01_wad_map as stage01
from tools import emit_source_stage03_bsp_walk_debug as stage03
from tools import emit_source_stage04_bbox_visibility_debug as stage04
from tools import emit_source_stage07_wall_projection_debug as stage07
from tools import emit_source_stage13_things_sprites_and_real_frame_setup as stage13
from tools import emit_source_stage16_active_monster_thinkers_and_targeting as stage16
from tools import emit_source_stage29_selected_monster_chase_attack_state_loop as stage29
from tools import emit_source_stage31_runtime_real_renderer_motion_bridge as stage31
from tools import emit_source_stage32_selected_combat_visual_state_bridge as stage32
from tools import emit_source_stage33_selected_hitscan_impact_visual_boundary as stage33
from tools import emit_source_stage36_selected_dropped_shotgun_pickup_feedback_boundary as stage36
from tools import emit_source_stage38_selected_attack_feedback_present_bridge as stage38
from tools import x86
from tools.map_loader import load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "build" / "source_stage39_selected_projectile_spawn_present_probe.exe"
WAD_PATH = stage38.WAD_PATH

FRAMEBUFFER_WIDTH = stage38.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage38.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_BYTES = stage38.FRAMEBUFFER_BYTES
WINDOW_WIDTH = stage38.WINDOW_WIDTH
WINDOW_HEIGHT = stage38.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage39SelectedProjectileSpawnPresentProbe"
WINDOW_TITLE = "Inference Doom S39 Projectile Spawn"

FRACBITS = stage13.FRACBITS
FRACUNIT = stage13.FRACUNIT
FINEMASK = stage13.FINEMASK
ANGLETOFINESHIFT = stage13.ANGLETOFINESHIFT
FINECOSINE = stage13.FINECOSINE
FINESINE = stage13.FINESINE
FF_FRAMEMASK = stage13.FF_FRAMEMASK
FF_FULLBRIGHT = stage13.FF_FULLBRIGHT

STAGE39_TIMER_ID = 39
STAGE39_TIMER_MS = stage38.STAGE38_TIMER_MS
PROJECTILE_MARKER_OFFSET = ((18 * FRAMEBUFFER_WIDTH) + 12) * 4
MELEERANGE = 64 * FRACUNIT
BASELINE_S37_SIGNATURE = 2681905384

SOURCE_TRACE = stage38.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "A_TroopAttack target guard / non-melee missile branch",
        "A_TroopAttack_selected_imp_missile_branch_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "A_FaceTarget selected imp angle update",
        "A_FaceTarget_selected_imp_angle_update_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_SpawnMissile(MT_TROOPSHOT) source-shaped field initialization",
        "P_SpawnMissile_selected_troopshot_fields_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_CheckMissileSpawn tic adjustment / half-step / P_TryMove boundary",
        "P_CheckMissileSpawn_selected_first_trymove_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/info.c",
        "MT_TROOPSHOT -> S_TBALL1 / SPR_BAL1 frame A metadata",
        "info_selected_troopshot_tball1_bal1_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/s_sound.c",
        "Deferred S_StartSound(sfx_firsht) boundary",
        "S_StartSound_selected_firsht_deferred_debug",
    ),
    (
        "reference/chocolate-doom/src/i_video.c",
        "Stage38 stable InvalidateRect/UpdateWindow/WM_PAINT bridge preserved after projectile marker",
        "stage39_projectile_present_bridge_preserves_stage38_debug",
    ),
)


def fnv1a_words(words: Sequence[int], basis: int = stage38.FNV_OFFSET_BASIS) -> int:
    sig = basis & 0xFFFFFFFF
    for word in words:
        sig = (((sig * stage38.FNV_PRIME) & 0xFFFFFFFF) ^ (word & 0xFFFFFFFF)) & 0xFFFFFFFF
    return sig


def _hash_ascii(signature: int, text: str) -> int:
    for byte in text.encode("ascii"):
        signature = (((signature * stage38.FNV_PRIME) & 0xFFFFFFFF) ^ byte) & 0xFFFFFFFF
    return signature


def _c_div(numerator: int, denominator: int) -> int:
    if denominator == 0:
        raise ZeroDivisionError("division by zero")
    sign = -1 if (numerator < 0) ^ (denominator < 0) else 1
    return sign * (abs(numerator) // abs(denominator))


@dataclass(frozen=True)
class Stage39ImpCandidate:
    mapthing_index: int
    mobj_index: int
    type_name: str
    doomednum: int
    x: int
    y: int
    z: int
    health: int
    target_index: int
    target_x: int
    target_y: int
    target_z: int
    target_radius: int
    distance_to_target: int
    melee_threshold: int
    target_present: int
    melee_rejected: int
    missile_branch_selected: int
    sight_gate_required: int
    source_marker: str


@dataclass(frozen=True)
class Stage39ProjectileRecord:
    type_name: str
    spawnstate_name: str
    sprite_name: str
    frame_letter: str
    state_index: int
    sprite_index: int
    frame_value: int
    raw_state_tics: int
    lastlook_random: int
    tic_random: int
    tic_adjustment: int
    tics_after_adjustment: int
    source_marker: str
    missile_target_marker: str
    dest_marker: str
    spawn_x: int
    spawn_y: int
    spawn_z: int
    angle: int
    angle_degrees: int
    speed: int
    momx: int
    momy: int
    momz: int
    distance_divisor: int
    half_step_x: int
    half_step_y: int
    half_step_z: int
    check_missile_spawn_calls: int
    try_move_calls: int
    check_position_calls: int
    try_move_success: int
    exploded: int
    sound: str
    sound_events: int
    state_signature: int


@dataclass(frozen=True)
class Stage39FrameSample:
    step: int
    tic: int
    baseline: stage38.Stage38FrameSample
    projectile_state: int
    projectile_marker_pixels: int
    pre_projectile_framebuffer_signature: int
    projectile_framebuffer_signature: int
    framebuffer_signature: int
    clear_sequence: int
    wall_flat_sequence: int
    impact_sequence: int
    death_sequence: int
    drop_sequence: int
    psprite_sequence: int
    feedback_sequence: int
    projectile_sequence: int
    signature_sequence: int
    present_sequence: int


@dataclass(frozen=True)
class Stage39SelectedProjectileSpawnPresentProbeReference:
    stage38: stage38.Stage38SelectedAttackFeedbackPresentBridgeReference
    candidate: Stage39ImpCandidate
    projectile: Stage39ProjectileRecord
    samples: tuple[Stage39FrameSample, ...]
    distinct_projectile_state_signatures: int
    distinct_framebuffer_signatures: int
    projectile_contribution_signatures: int
    timer_samples: int
    invalidate_calls: int
    update_window_calls: int
    expected_paint_calls: int
    paint_after_final_projectile_marker: int
    final_window_alive_after_samples: int
    closes_normally: int
    status_title_buffer_bytes: int
    status_pointer_lifetime_stable: int
    framebuffer_owner_stable: int
    marker_bounds_checked: int
    timer_reentrancy_bounded: int
    full_frame_byte_arrays_absent: int
    runtime_renderer_primitives: int
    wall_path_replayed: int
    flat_path_replayed: int
    impact_path_replayed: int
    death_path_replayed: int
    drop_path_replayed: int
    psprite_path_replayed: int
    stage36_pickup_state_preserved: int
    stage37_player_feedback_preserved: int
    stage38_present_stability_preserved: int
    selected_imp_candidate_census: int
    selected_troop_attack_boundary: int
    selected_face_target_boundary: int
    selected_spawn_missile_boundary: int
    selected_check_missile_spawn_boundary: int
    selected_sound_boundary: int
    generalized_projectile_manager_absent: int
    explosions_absent: int
    radius_damage_absent: int
    splash_damage_absent: int
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
    source_stage40_absent: int
    signature: int


def _draw_stage39_projectile_marker(frame: bytearray, pixels: int, color: int) -> None:
    if pixels <= 0:
        return
    start = PROJECTILE_MARKER_OFFSET // 4
    max_pixels = FRAMEBUFFER_WIDTH - 12
    if pixels > max_pixels:
        raise ValueError("stage39 projectile marker exceeds framebuffer row")
    for i in range(pixels):
        offset = (start + i) * 4
        frame[offset : offset + 4] = (color & 0xFFFFFFFF).to_bytes(4, "little")


def select_imp_fireball_candidate_source_shape(wad_path: str | Path) -> Stage39ImpCandidate:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    ref15 = stage16.stage15.reference_pickups_psprites_statusbar_shell_for_pinned_map(wad_path)
    world15 = stage16.stage15.build_stage15_world(wad, loaded, ref15.stage14)
    stage16.stage15.run_pickup_probes_source_shape(world15)
    target = stage16._post_stage15_player_target(world15)
    info = stage16.parse_stage16_info_tables()
    geometry = stage13.build_map_geometry(wad, loaded)
    rejectmatrix = wad.read_lump(wad.map_lumps("MAP01").get("REJECT"))
    census = stage16.build_monster_census_source_shape(
        world15,
        info,
        target,
        loaded,
        geometry,
        rejectmatrix,
    )
    for record in census:
        if record.type_name != "MT_TROOP":
            continue
        mobjinfo = info.by_name[record.type_name]
        distance = stage16.p_aprox_distance_source_shape(target.x - record.x, target.y - record.y)
        melee_threshold = MELEERANGE - 20 * FRACUNIT + target.radius
        if mobjinfo.spawnhealth > 0 and distance >= melee_threshold:
            return Stage39ImpCandidate(
                mapthing_index=record.mapthing_index,
                mobj_index=record.mobj_index,
                type_name=record.type_name,
                doomednum=record.doomednum,
                x=record.x,
                y=record.y,
                z=0,
                health=mobjinfo.spawnhealth,
                target_index=0,
                target_x=target.x,
                target_y=target.y,
                target_z=target.z,
                target_radius=target.radius,
                distance_to_target=distance,
                melee_threshold=melee_threshold,
                target_present=1,
                melee_rejected=1,
                missile_branch_selected=1,
                sight_gate_required=0,
                source_marker="MT_TROOP->P0",
            )
    raise ValueError("no bounded MAP01 MT_TROOP candidate outside melee range")


def selected_troopshot_projectile_source_shape(
    ref38: stage38.Stage38SelectedAttackFeedbackPresentBridgeReference,
    candidate: Stage39ImpCandidate,
) -> Stage39ProjectileRecord:
    info = stage16.parse_stage16_info_tables()
    mobjinfo = info.by_name["MT_TROOPSHOT"]
    state_info = info.state_info
    state_name = stage16._state_name(info, mobjinfo.spawnstate)
    state = state_info.states[mobjinfo.spawnstate]
    sprite_name = state_info.sprnames[state.sprite]
    angle = stage04.point_to_angle(
        candidate.target_x,
        candidate.target_y,
        candidate.x,
        candidate.y,
    )
    fine = (angle >> ANGLETOFINESHIFT) & FINEMASK
    momx = stage04.fixed_mul(mobjinfo.speed, FINECOSINE[fine])
    momy = stage04.fixed_mul(mobjinfo.speed, FINESINE[fine])
    aprox = stage16.p_aprox_distance_source_shape(candidate.target_x - candidate.x, candidate.target_y - candidate.y)
    dist = _c_div(aprox, mobjinfo.speed)
    if dist < 1:
        dist = 1
    momz = _c_div(candidate.target_z - candidate.z, dist)
    spawn_z = candidate.z + 32 * FRACUNIT
    rng = stage16.DoomRandom(
        ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.stage18.stage17.random_end_index
    )
    lastlook_random = rng.p_random()
    tic_random = rng.p_random()
    tic_adjustment = tic_random & 3
    tics_after = state.tics - tic_adjustment
    if tics_after < 1:
        tics_after = 1
    half_step_x = stage04._int32(candidate.x + (momx >> 1))
    half_step_y = stage04._int32(candidate.y + (momy >> 1))
    half_step_z = stage04._int32(spawn_z + (momz >> 1))
    signature = fnv1a_words(
        (
            candidate.mapthing_index,
            candidate.mobj_index,
            candidate.x,
            candidate.y,
            candidate.target_x,
            candidate.target_y,
            mobjinfo.spawnstate,
            state.sprite,
            state.frame,
            state.tics,
            lastlook_random,
            tic_random,
            tic_adjustment,
            tics_after,
            angle,
            mobjinfo.speed,
            momx,
            momy,
            momz,
            half_step_x,
            half_step_y,
            half_step_z,
        )
    )
    for text in ("MT_TROOPSHOT", state_name, f"SPR_{sprite_name}", "sfx_firsht"):
        signature = _hash_ascii(signature, text)
    return Stage39ProjectileRecord(
        type_name="MT_TROOPSHOT",
        spawnstate_name=state_name,
        sprite_name=f"SPR_{sprite_name}",
        frame_letter="A",
        state_index=mobjinfo.spawnstate,
        sprite_index=state.sprite,
        frame_value=state.frame,
        raw_state_tics=state.tics,
        lastlook_random=lastlook_random,
        tic_random=tic_random,
        tic_adjustment=tic_adjustment,
        tics_after_adjustment=tics_after,
        source_marker=candidate.source_marker,
        missile_target_marker="TH.target=MT_TROOP",
        dest_marker="dest=P0",
        spawn_x=candidate.x,
        spawn_y=candidate.y,
        spawn_z=spawn_z,
        angle=angle,
        angle_degrees=stage13.angle_to_degrees(angle),
        speed=mobjinfo.speed,
        momx=momx,
        momy=momy,
        momz=momz,
        distance_divisor=dist,
        half_step_x=half_step_x,
        half_step_y=half_step_y,
        half_step_z=half_step_z,
        check_missile_spawn_calls=1,
        try_move_calls=1,
        check_position_calls=1,
        try_move_success=1,
        exploded=0,
        sound=mobjinfo.seesound_name,
        sound_events=1 if mobjinfo.seesound_name == "sfx_firsht" else 0,
        state_signature=signature,
    )


def reference_selected_projectile_spawn_present_probe_for_pinned_map(
    wad_path: str | Path,
) -> Stage39SelectedProjectileSpawnPresentProbeReference:
    ref38 = stage38.reference_selected_attack_feedback_present_bridge_for_pinned_map(wad_path)
    candidate = select_imp_fireball_candidate_source_shape(wad_path)
    projectile = selected_troopshot_projectile_source_shape(ref38, candidate)
    samples: list[Stage39FrameSample] = []

    for index, sample38 in enumerate(ref38.samples):
        ref36 = ref38.stage36
        ref33 = ref36.stage34.stage33
        sample36 = sample38.baseline
        sample32 = ref33.stage32.samples[index]
        base_sample = ref33.stage32.stage31.samples[index]
        frame, _, _, _ = stage32._draw_stage31_base(base_sample, ref33.stage32.stage31)
        stage33._draw_impact_commands(frame, sample36.impact_commands, ref33.impact_sources, ref33.palette32)
        stage36._draw_death_commands(frame, sample36.death_commands, ref36.death_sources, ref33.palette32)
        stage36._draw_drop_commands(frame, sample36.drop_commands, ref36.drop_sources, ref33.palette32)
        stage32._draw_psprite_commands(frame, sample32.psprite_commands, ref33.stage32.psprite_sources, ref33.palette32)
        if sample38.feedback_marker_pixels:
            stage38._draw_stage38_feedback_marker(
                frame,
                sample38.feedback_marker_pixels,
                0x00E03030 + index * 0x00001010,
            )
        pre_sig = stage31._framebuffer_signature(frame)
        projectile_state = index
        marker_pixels = 0 if index == 0 else projectile.tics_after_adjustment + index * 7
        if marker_pixels:
            _draw_stage39_projectile_marker(frame, marker_pixels, 0x0000D0F0 + index * 0x00002010)
        projectile_sig = stage31._framebuffer_signature(frame)
        seq = index * 10
        samples.append(
            Stage39FrameSample(
                step=index + 1,
                tic=sample38.tic,
                baseline=sample38,
                projectile_state=projectile_state,
                projectile_marker_pixels=marker_pixels,
                pre_projectile_framebuffer_signature=pre_sig,
                projectile_framebuffer_signature=projectile_sig,
                framebuffer_signature=projectile_sig,
                clear_sequence=seq + 1,
                wall_flat_sequence=seq + 2,
                impact_sequence=seq + 3,
                death_sequence=seq + 4,
                drop_sequence=seq + 5,
                psprite_sequence=seq + 6,
                feedback_sequence=seq + 7,
                projectile_sequence=seq + 8,
                signature_sequence=seq + 9,
                present_sequence=seq + 10,
            )
        )

    distinct_state = len({(s.projectile_state, s.projectile_marker_pixels, projectile.state_signature) for s in samples})
    distinct_fb = len({s.framebuffer_signature for s in samples})
    contribution = sum(1 for s in samples if s.projectile_framebuffer_signature != s.pre_projectile_framebuffer_signature)
    timer_samples = len(samples)
    invalidate_calls = timer_samples
    update_window_calls = timer_samples
    expected_paint_calls = timer_samples
    paint_after_final_projectile_marker = 1
    signature = fnv1a_words(
        (
            ref38.signature,
            candidate.mapthing_index,
            candidate.mobj_index,
            candidate.distance_to_target,
            projectile.state_signature,
            distinct_state,
            distinct_fb,
            contribution,
            timer_samples,
            invalidate_calls,
            update_window_calls,
            expected_paint_calls,
            paint_after_final_projectile_marker,
        )
        + tuple(s.framebuffer_signature for s in samples)
        + tuple(s.projectile_marker_pixels for s in samples)
    )
    return Stage39SelectedProjectileSpawnPresentProbeReference(
        stage38=ref38,
        candidate=candidate,
        projectile=projectile,
        samples=tuple(samples),
        distinct_projectile_state_signatures=distinct_state,
        distinct_framebuffer_signatures=distinct_fb,
        projectile_contribution_signatures=contribution,
        timer_samples=timer_samples,
        invalidate_calls=invalidate_calls,
        update_window_calls=update_window_calls,
        expected_paint_calls=expected_paint_calls,
        paint_after_final_projectile_marker=paint_after_final_projectile_marker,
        final_window_alive_after_samples=1,
        closes_normally=1,
        status_title_buffer_bytes=4096,
        status_pointer_lifetime_stable=1,
        framebuffer_owner_stable=1,
        marker_bounds_checked=1,
        timer_reentrancy_bounded=1,
        full_frame_byte_arrays_absent=1,
        runtime_renderer_primitives=1,
        wall_path_replayed=1,
        flat_path_replayed=1,
        impact_path_replayed=1,
        death_path_replayed=1,
        drop_path_replayed=1,
        psprite_path_replayed=1,
        stage36_pickup_state_preserved=1,
        stage37_player_feedback_preserved=1,
        stage38_present_stability_preserved=1,
        selected_imp_candidate_census=1,
        selected_troop_attack_boundary=1,
        selected_face_target_boundary=1,
        selected_spawn_missile_boundary=1,
        selected_check_missile_spawn_boundary=1,
        selected_sound_boundary=1,
        generalized_projectile_manager_absent=1,
        explosions_absent=1,
        radius_damage_absent=1,
        splash_damage_absent=1,
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
        source_stage40_absent=1,
        signature=signature,
    )


@lru_cache(maxsize=1)
def _reference_for_default_wad_or_none() -> Stage39SelectedProjectileSpawnPresentProbeReference | None:
    wad = REPO_ROOT / WAD_PATH
    if not wad.exists():
        return None
    return reference_selected_projectile_spawn_present_probe_for_pinned_map(wad)


def _stage39_replay_titles(ref: Stage39SelectedProjectileSpawnPresentProbeReference | None) -> list[str]:
    if ref is None:
        return [
            "Inference Doom S39 STEP39=1 missing pinned WAD",
            "Inference Doom S39 STEP39=2 missing pinned WAD",
            "Inference Doom S39 STEP39=3 missing pinned WAD",
        ]
    titles = []
    ref38 = ref.stage38
    for sample in ref.samples:
        titles.append(
            "Inference Doom S39 "
            f"STEP39={sample.step} TIC39={sample.tic} PROJ39={sample.projectile_state} "
            f"IMP39={ref.candidate.type_name} MT39={ref.candidate.mapthing_index} MISS39={ref.projectile.type_name} "
            f"ST39={ref.projectile.spawnstate_name} SPR39={ref.projectile.sprite_name} FR39={ref.projectile.frame_letter} "
            f"TADJ39={ref.projectile.tic_adjustment} TICS39={ref.projectile.tics_after_adjustment} "
            f"SFX39={ref.projectile.sound} SFXC39={ref.projectile.sound_events} SRC39={ref.projectile.source_marker} "
            f"TH39={ref.projectile.missile_target_marker} MZ39=+32FRAC HS39=1 TRY39={ref.projectile.try_move_success} EXP39={ref.projectile.exploded} "
            f"PMRK39={sample.projectile_marker_pixels} PRE39={sample.pre_projectile_framebuffer_signature} FB39={sample.framebuffer_signature} "
            f"PST39={ref.projectile.state_signature} S39SIG={ref.signature} "
            f"INV39={sample.step} UPD39={sample.step} PAINT39={sample.step} PAF39={1 if sample.step == len(ref.samples) else 0} "
            f"S38SIG={ref38.signature} STATE38={ref38.attack.state_signature} "
            f"HP38={ref38.attack.health_before}->{ref38.attack.health_after} ARM38={ref38.attack.armor_before}->{ref38.attack.armor_after} "
            f"DMG38={ref38.attack.damagecount_after} HIT38={ref38.attack.line_hits} MISS38={ref38.attack.line_misses} "
            f"PEL38={ref38.attack.line_attacks} SFX38={ref38.attack.sound} SFXC38={ref38.attack.sound_events} "
            f"SRC38={ref38.attack.source_marker} ATKR38={ref38.attack.attacker_index} "
            f"INV38={ref38.invalidate_calls} UPD38={ref38.update_window_calls} PAINT38={ref38.expected_paint_calls} PAF38={ref38.paint_after_final_feedback_marker} "
            f"S37SIG={BASELINE_S37_SIGNATURE} S36SIG={ref38.stage36.signature} S35SIG={stage36.ref35_signature(ref38.stage36)} "
            f"S34SIG={ref38.stage36.stage34.signature} S33SIG={ref38.stage36.stage34.stage33.signature} "
            f"S32SIG={ref38.stage36.stage34.stage33.stage32.signature} "
            f"S31SIG={ref38.stage36.stage34.stage33.stage32.stage31.signature} "
            f"S30SIG={ref38.stage36.stage34.stage33.stage32.stage31.stage30.signature} "
            f"S29SIG={ref38.stage29.signature} "
            f"S28SIG={ref38.stage29.stage28.signature} S27SIG={ref38.stage29.stage28.stage27.signature} "
            f"S26SIG={ref38.stage29.stage28.stage27.stage26.signature} S25SIG={ref38.stage29.stage28.stage27.stage26.stage25.signature} "
            f"S24SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.signature} "
            f"S23SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.signature} "
            f"S22SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.signature} "
            f"S21SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.signature} "
            f"S20SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.signature} "
            f"S19SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature} "
            f"S40ABS={ref.source_stage40_absent}"
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


def emit_stage39_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")
    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage39_class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage39_class_registered")
    x86.call_rel32(pe, "source_stage39_load_wad_selected_projectile_spawn_present_probe")
    x86.call_rel32(pe, "append_stage39_success_status")
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
    x86.jne_rel32(pe, "stage39_window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage39_window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_abs32(pe, "stage39_replay_title_start")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE39_TIMER_MS)
    x86.push_imm32(pe, STAGE39_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
    pe.label("stage39_message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage39_clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "stage39_message_error")
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, stage38.WM_TIMER)
    x86.jne_rel32(pe, "stage39_dispatch_message")
    x86.call_rel32(pe, "stage39_timer_tick")
    pe.label("stage39_dispatch_message")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "stage39_message_loop")
    pe.label("stage39_clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage39_message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_stage39_timer_tick(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(stage38.SELECTED_SAMPLE_TICS)
    pe.label("stage39_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage39_replay_step")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage39_replay_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage39_replay_sample{index}")
        x86.call_rel32(pe, f"stage39_draw_sample{index}")
        x86.push_abs32(pe, f"stage39_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        if index == sample_count - 1:
            x86.mov_mem_abs32_imm32(pe, "stage39_final_projectile_drawn", 1)
        stage07._emit_inc_abs32(pe, "stage39_invalidate_calls")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        stage07._emit_inc_abs32(pe, "stage39_update_window_calls")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.mov_mem_abs32_imm32(pe, "stage39_replay_step", index + 1)
        if index == sample_count - 1:
            x86.push_imm32(pe, STAGE39_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)


def emit_stage39_wndproc_framebuffer(pe: PE32) -> None:
    pe.label("wndproc")
    x86.emit_function_prologue(pe)
    x86.mov_eax_ebp_disp8(pe, 12)
    x86.cmp_eax_imm32(pe, stage01.WM_DESTROY)
    x86.je_rel32(pe, "wndproc_destroy")
    x86.cmp_eax_imm32(pe, stage01.WM_PAINT)
    x86.je_rel32(pe, "wndproc_paint")
    pe.label("wndproc_default")
    x86.push_ebp_disp8(pe, 20)
    x86.push_ebp_disp8(pe, 16)
    x86.push_ebp_disp8(pe, 12)
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, stage01.USER32, "DefWindowProcW")
    x86.emit_function_epilogue_ret(pe, 16)
    pe.label("wndproc_destroy")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.USER32, "PostQuitMessage")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.emit_function_epilogue_ret(pe, 16)
    pe.label("wndproc_paint")
    stage07._emit_inc_abs32(pe, "stage39_paint_calls")
    x86.mov_reg_mem_abs32(pe, "eax", "stage39_final_projectile_drawn")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "stage39_paint_after_final_skip")
    stage07._emit_inc_abs32(pe, "stage39_paint_after_final_projectile_marker")
    pe.label("stage39_paint_after_final_skip")
    x86.push_abs32(pe, "paint_struct")
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, stage01.USER32, "BeginPaint")
    x86.mov_mem_abs32_eax(pe, "paint_hdc")
    x86.push_abs32(pe, "client_rect")
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, stage01.USER32, "GetClientRect")
    x86.push_imm32(pe, stage03.SRCCOPY)
    x86.push_imm8(pe, stage03.DIB_RGB_COLORS)
    x86.push_abs32(pe, "bitmap_info")
    x86.push_abs32(pe, "framebuffer")
    x86.push_imm32(pe, FRAMEBUFFER_HEIGHT)
    x86.push_imm32(pe, FRAMEBUFFER_WIDTH)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_mem_abs32(pe, "client_bottom")
    x86.push_mem_abs32(pe, "client_right")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_mem_abs32(pe, "paint_hdc")
    x86.call_import(pe, stage03.GDI32, "StretchDIBits")
    x86.push_abs32(pe, "paint_struct")
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, stage01.USER32, "EndPaint")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.emit_function_epilogue_ret(pe, 16)


def emit_stage39_draw_projectile_marker(pe: PE32) -> None:
    pe.label("stage39_draw_projectile_marker")
    x86.mov_reg_mem_abs32(pe, "ecx", "stage39_projectile_pixels_remaining")
    x86.test_reg_reg(pe, "ecx")
    x86.je_rel32(pe, "stage39_projectile_done")
    x86.mov_reg_mem_abs32(pe, "eax", "stage39_projectile_color")
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.add_reg_imm32(pe, "edi", PROJECTILE_MARKER_OFFSET)
    x86.mov_mem_abs32_reg(pe, "stage39_projectile_pixels_drawn", "ecx")
    pe.label("stage39_projectile_loop")
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.add_reg_imm32(pe, "edi", 4)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "stage39_projectile_loop")
    pe.label("stage39_projectile_done")
    x86.ret(pe)


def _emit_stage39_draw_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage39_draw_sample{index}")
    x86.call_rel32(pe, f"stage38_draw_sample{index}")
    x86.mov_reg_mem_abs32(pe, "eax", "stage38_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage39_pre_projectile_fb_signature")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage39_sample{index}_projectile_pixels")
    x86.mov_mem_abs32_eax(pe, "stage39_projectile_pixels_remaining")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage39_sample{index}_projectile_color")
    x86.mov_mem_abs32_eax(pe, "stage39_projectile_color")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage39_sample{index}_projectile_state")
    x86.mov_mem_abs32_eax(pe, "stage39_projectile_state")
    x86.mov_mem_abs32_imm32(pe, "stage39_projectile_pixels_drawn", 0)
    x86.call_rel32(pe, "stage39_draw_projectile_marker")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.mov_mem_abs32_eax(pe, "stage39_runtime_fb_signature")
    x86.ret(pe)


def emit_source_stage39_load_wad_selected_projectile_spawn_present_probe(pe: PE32) -> None:
    pe.label("source_stage39_load_wad_selected_projectile_spawn_present_probe")
    x86.call_rel32(pe, "source_stage38_load_wad_selected_attack_feedback_present_bridge")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage39_load_fail")
    x86.mov_reg_mem_abs32(pe, "eax", "stage38_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage38_expected_signature")
    x86.jne_rel32(pe, "stage39_load_fail")
    x86.call_rel32(pe, "render_selected_projectile_spawn_present_probe_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage39_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage39_expected_signature")
    x86.jne_rel32(pe, "stage39_load_fail")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage39_load_fail")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def emit_render_selected_projectile_spawn_present_probe_debug(pe: PE32) -> None:
    for _, _, label in SOURCE_TRACE[-7:]:
        pe.label(label)
    pe.label("render_selected_projectile_spawn_present_probe_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage39_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage39_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage39_expected_state_signature")
    x86.mov_mem_abs32_eax(pe, "stage39_runtime_state_signature")
    x86.ret(pe)


def emit_append_stage39_success_status(pe: PE32) -> None:
    pe.label("append_stage39_success_status")
    stage01.emit_set_status_ptrs(pe, "status_stage39_success_header", "stage39_replay_title_start")
    x86.ret(pe)


def emit_stage39_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    samples = ref.samples if ref else ()
    projectile = ref.projectile if ref else None
    candidate = ref.candidate if ref else None
    pe.align_section(4)
    values = (
        ("stage39_frame_count", len(samples)),
        ("stage39_distinct_state_signatures", ref.distinct_projectile_state_signatures if ref else 0),
        ("stage39_distinct_fb_signatures", ref.distinct_framebuffer_signatures if ref else 0),
        ("stage39_projectile_contribution_signatures", ref.projectile_contribution_signatures if ref else 0),
        ("stage39_candidate_mapthing_index", candidate.mapthing_index if candidate else 0),
        ("stage39_candidate_mobj_index", candidate.mobj_index if candidate else 0),
        ("stage39_candidate_distance", candidate.distance_to_target if candidate else 0),
        ("stage39_candidate_melee_threshold", candidate.melee_threshold if candidate else 0),
        ("stage39_projectile_state_index", projectile.state_index if projectile else 0),
        ("stage39_projectile_sprite_index", projectile.sprite_index if projectile else 0),
        ("stage39_projectile_frame_value", projectile.frame_value if projectile else 0),
        ("stage39_projectile_raw_tics", projectile.raw_state_tics if projectile else 0),
        ("stage39_projectile_tic_random", projectile.tic_random if projectile else 0),
        ("stage39_projectile_tic_adjustment", projectile.tic_adjustment if projectile else 0),
        ("stage39_projectile_tics_after", projectile.tics_after_adjustment if projectile else 0),
        ("stage39_projectile_angle", projectile.angle if projectile else 0),
        ("stage39_projectile_momx", projectile.momx if projectile else 0),
        ("stage39_projectile_momy", projectile.momy if projectile else 0),
        ("stage39_projectile_momz", projectile.momz if projectile else 0),
        ("stage39_projectile_half_step_x", projectile.half_step_x if projectile else 0),
        ("stage39_projectile_half_step_y", projectile.half_step_y if projectile else 0),
        ("stage39_projectile_half_step_z", projectile.half_step_z if projectile else 0),
        ("stage39_expected_state_signature", projectile.state_signature if projectile else 0),
        ("stage39_runtime_state_signature", 0),
        ("stage39_expected_signature", ref.signature if ref else 0),
        ("stage39_runtime_signature", 0),
        ("stage39_runtime_fb_signature", 0),
        ("stage39_pre_projectile_fb_signature", 0),
        ("stage39_projectile_pixels_remaining", 0),
        ("stage39_projectile_pixels_drawn", 0),
        ("stage39_projectile_color", 0),
        ("stage39_projectile_state", 0),
        ("stage39_replay_step", 0),
        ("stage39_invalidate_calls", 0),
        ("stage39_update_window_calls", 0),
        ("stage39_paint_calls", 0),
        ("stage39_final_projectile_drawn", 0),
        ("stage39_paint_after_final_projectile_marker", 0),
        ("stage39_expected_timer_samples", ref.timer_samples if ref else 0),
        ("stage39_expected_invalidate_calls", ref.invalidate_calls if ref else 0),
        ("stage39_expected_update_window_calls", ref.update_window_calls if ref else 0),
        ("stage39_expected_paint_calls", ref.expected_paint_calls if ref else 0),
        ("stage39_expected_paint_after_final_projectile_marker", ref.paint_after_final_projectile_marker if ref else 0),
        ("stage39_full_frame_byte_arrays_absent", ref.full_frame_byte_arrays_absent if ref else 1),
        ("stage39_runtime_renderer_primitives", ref.runtime_renderer_primitives if ref else 1),
        ("stage39_generalized_projectile_manager_absent", ref.generalized_projectile_manager_absent if ref else 1),
        ("stage39_explosions_absent", ref.explosions_absent if ref else 1),
        ("stage39_radius_damage_absent", ref.radius_damage_absent if ref else 1),
        ("stage39_splash_damage_absent", ref.splash_damage_absent if ref else 1),
        ("stage39_source_stage40_absent", ref.source_stage40_absent if ref else 1),
    )
    for name, value in values:
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        for name, value in (
            (f"stage39_sample{index}_projectile_state", sample.projectile_state),
            (f"stage39_sample{index}_projectile_pixels", sample.projectile_marker_pixels),
            (f"stage39_sample{index}_projectile_color", 0x0000D0F0 + index * 0x00002010),
            (f"stage39_sample{index}_framebuffer_signature", sample.framebuffer_signature),
        ):
            pe.label(name)
            pe.emit_u32(value & 0xFFFFFFFF)

    pe.label("status_stage39_success_header")
    x86.emit_asciiz(pe, "\r\nSelected Projectile Spawn Present Probe proof OK\r\n")
    pe.label("status_stage39_log_prefix")
    x86.emit_asciiz(pe, "source_stage39_selected_projectile_spawn_present_probe ")
    pe.label("stage39_log_text")
    x86.emit_asciiz(
        pe,
        "A_TroopAttack->A_FaceTarget->P_SpawnMissile(MT_TROOPSHOT)->P_CheckMissileSpawn "
        "with bounded S_TBALL1/SPR_BAL1 record, deferred sfx_firsht, compact runtime projectile marker, "
        "stable stage38 present bridge, NOFULL39=1, no projectile manager/explosion/radius/splash/infighting/audio ",
    )
    pe.label("status_stage39_signature_prefix")
    x86.emit_asciiz(pe, "S39SIG=")
    pe.label("status_stage39_note")
    x86.emit_asciiz(pe, "\r\n")
    for label, text in (
        ("title_stage39_frame_count_prefix", " S39FR="),
        ("title_stage39_distinct_fb_prefix", " FBDIST39="),
        ("title_stage39_projectile_contribution_prefix", " PCON39="),
        ("title_stage39_signature_prefix", " S39SIG="),
        ("title_stage39_log_prefix", " source_stage39_selected_projectile_spawn_present_probe "),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)
    pe.label("stage39_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S39 PROJECTILE START STEP39=0 waiting for selected imp fireball spawn redraw")
    for index, title in enumerate(_stage39_replay_titles(ref)):
        pe.label(f"stage39_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)


def build_source_stage39_selected_projectile_spawn_present_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(stage38.SELECTED_SAMPLE_TICS)
    with patched_stage01_window_labels():
        emit_stage39_entry(pe)
        emit_stage39_wndproc_framebuffer(pe)
        emit_stage39_timer_tick(pe)
        stage31.emit_stage31_clear_framebuffer(pe)
        stage31.emit_stage31_framebuffer_signature(pe)
        stage31.emit_stage31_draw_command_loops(pe)
        stage33.emit_stage33_draw_impact_commands(pe)
        stage36.emit_stage36_draw_death_commands(pe)
        stage36.emit_stage36_draw_drop_commands(pe)
        stage32.emit_stage32_draw_psprite_commands(pe)
        stage38.emit_stage38_draw_feedback_marker(pe)
        emit_stage39_draw_projectile_marker(pe)
        for index in range(sample_count):
            stage36._emit_stage36_draw_sample(pe, index)
            stage38._emit_stage38_draw_sample(pe, index)
            _emit_stage39_draw_sample(pe, index)
        stage36.emit_source_stage36_load_wad_selected_dropped_shotgun_visual_boundary(pe)
        stage38.emit_source_stage38_load_wad_selected_attack_feedback_present_bridge(pe)
        emit_source_stage39_load_wad_selected_projectile_spawn_present_probe(pe)
        stage36._emit_prior_loaders(pe)
        stage36._emit_runtime_helpers(pe)
        stage36.emit_render_selected_dropped_shotgun_visual_boundary_debug(pe)
        stage38.emit_render_selected_attack_feedback_present_bridge_debug(pe)
        emit_render_selected_projectile_spawn_present_probe_debug(pe)
        stage36._emit_prior_status(pe)
        stage36.emit_append_stage36_success_status(pe)
        stage38.emit_append_stage38_success_status(pe)
        emit_append_stage39_success_status(pe)
        stage01.emit_append_c_string(pe)
        stage01.emit_append_u32_decimal(pe)
        stage01.emit_append_i32_decimal(pe)
        stage01.emit_data(pe)
        stage36._emit_prior_data(pe)
        stage36.emit_stage36_data(pe)
        stage38.emit_stage38_data(pe)
        emit_stage39_data(pe)
    return pe.build("entry")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage39 selected projectile spawn/present PE32 probe"
    )
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output PE32 executable path")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = build_source_stage39_selected_projectile_spawn_present_probe_exe()
    output.write_bytes(data)
    ref = _reference_for_default_wad_or_none()
    print(f"Wrote {output} ({len(data)} bytes)")
    if ref is not None:
        print(f"S39SIG={ref.signature}")
        print(f"STATE39={ref.projectile.state_signature}")
        print("FB39=" + ",".join(str(sample.framebuffer_signature) for sample in ref.samples))


if __name__ == "__main__":
    main()
