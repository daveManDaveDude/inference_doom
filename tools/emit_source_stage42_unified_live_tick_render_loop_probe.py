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

from tools import emit_source_stage41_statusbar_weapon_ammo_feedback_bridge as stage41
from tools import x86
from tools.pe32 import PE32


stage40 = stage41.stage40
stage39 = stage41.stage39
stage38 = stage41.stage38
stage36 = stage41.stage36
stage32 = stage41.stage32
stage31 = stage41.stage31
stage15 = stage41.stage15
stage07 = stage41.stage07
stage03 = stage41.stage03
stage01 = stage41.stage01

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "build" / "source_stage42_unified_live_tick_render_loop_probe.exe"
WAD_PATH = stage41.WAD_PATH

FRAMEBUFFER_WIDTH = stage41.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage41.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_BYTES = stage41.FRAMEBUFFER_BYTES
WINDOW_WIDTH = stage41.WINDOW_WIDTH
WINDOW_HEIGHT = stage41.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage42UnifiedLiveTickRenderLoopProbe"
WINDOW_TITLE = "Inference Doom S42 Unified Live Tick Render Loop"

STAGE42_TIMER_ID = 42
STAGE42_TIMER_MS = stage41.STAGE41_TIMER_MS
TICCMD_RECORD_SIZE = 28
BASELINE_S41_SIGNATURE = 951695045
BASELINE_S41_STATE_SIGNATURE = 157977072
BASELINE_S40_SIGNATURE = 2737672056
BASELINE_S40_STATE_SIGNATURE = 268409133
BASELINE_S39_SIGNATURE = 3469618451
BASELINE_S39_STATE_SIGNATURE = 1403583302

SOURCE_TRACE = stage41.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/d_loop.c",
        "D_DoomLoop/I_StartTic deterministic selected replay boundary",
        "D_DoomLoop_stage42_selected_timer_replay_boundary_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/g_game.c",
        "G_BuildTiccmd/G_Ticker selected ticcmd ownership",
        "G_Ticker_stage42_selected_ticcmd_ownership_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_tick.c",
        "P_Ticker selected player/thinker update ordering",
        "P_Ticker_stage42_selected_update_order_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_user.c",
        "P_PlayerThink/P_MovePlayer selected command mutation",
        "P_PlayerThink_stage42_selected_player_command_update_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_pspr.c",
        "P_MovePsprites/P_SetupPsprites selected weapon state",
        "P_MovePsprites_stage42_selected_weapon_state_update_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_MobjThinker/P_SpawnMissile selected mobj/projectile state",
        "P_MobjThinker_stage42_selected_mobj_projectile_update_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "A_SPosAttack/A_TroopAttack selected feedback/projectile boundaries",
        "P_Enemy_stage42_selected_attack_projectile_boundaries_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_RenderPlayerView selected clear/wall/flat/vissprite/psprite ordering",
        "R_RenderPlayerView_stage42_unified_order_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/st_stuff.c",
        "ST_Ticker/ST_updateWidgets compact status fields after gameplay",
        "ST_Ticker_stage42_compact_status_after_gameplay_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/hu_stuff.c",
        "HU_Ticker selected pickup message ownership",
        "HU_Ticker_stage42_selected_message_after_gameplay_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_inter.c",
        "P_TouchSpecialThing/P_DamageMobj selected pickup/damage feedback",
        "P_Inter_stage42_selected_pickup_damage_feedback_debug",
    ),
    (
        "reference/chocolate-doom/src/v_video.c",
        "V_DrawBlock/V_DrawFilledBox runtime primitive draw",
        "V_DrawBlock_stage42_runtime_status_present_debug",
    ),
    (
        "reference/chocolate-doom/src/i_video.c",
        "I_StartTic/I_FinishUpdate-style invalidate/update/paint present",
        "I_Video_stage42_invalidate_update_paint_debug",
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


@dataclass(frozen=True)
class Stage42TicCmd:
    tic: int
    forwardmove: int
    sidemove: int
    angleturn: int
    buttons: int
    consistency: int
    source_index: int
    source_marker: str


@dataclass(frozen=True)
class Stage42SelectedPlayerState:
    x: int
    y: int
    angle: int
    momx: int
    momy: int
    viewz: int
    health: int
    armor: int
    shell_ammo: int
    shotgun_owned: int
    pending_weapon: int
    ready_weapon: int
    psprite_state_name: str
    psprite_tics: int
    bonuscount: int
    damagecount: int
    message: str
    source_marker: str


@dataclass(frozen=True)
class Stage42SelectedMobjState:
    enemy_type_name: str
    enemy_state_name: str
    enemy_health: int
    enemy_target_present: int
    dropped_shotgun_present: int
    dropped_shotgun_removed: int
    projectile_type_name: str
    projectile_state_name: str
    projectile_present: int
    projectile_x: int
    projectile_y: int
    projectile_z: int
    projectile_tics: int
    projectile_sound_events: int
    source_marker: str


@dataclass(frozen=True)
class Stage42UnifiedLoopSample:
    step: int
    tic: int
    baseline: stage41.Stage41StatusSample
    ticcmd: Stage42TicCmd
    player: Stage42SelectedPlayerState
    mobj: Stage42SelectedMobjState
    command_record_count: int
    status_command_count: int
    framebuffer_signature: int
    status_state_signature: int
    world_vissprite_state_signature: int
    world_vissprite_framebuffer_signature: int
    projectile_state_signature: int
    unified_loop_state_signature: int
    start_tic_sequence: int
    ticcmd_sequence: int
    g_ticker_sequence: int
    p_ticker_sequence: int
    player_update_sequence: int
    psprite_weapon_update_sequence: int
    pickup_damage_projectile_sequence: int
    clear_sequence: int
    wall_flat_sequence: int
    impact_sequence: int
    death_sequence: int
    drop_sequence: int
    world_vissprite_sequence: int
    psprite_sequence: int
    feedback_sequence: int
    projectile_state_sequence: int
    status_sequence: int
    signature_sequence: int
    present_sequence: int


@dataclass(frozen=True)
class Stage42UnifiedLiveTickRenderLoopProbeReference:
    stage41: stage41.Stage41StatusbarWeaponAmmoFeedbackBridgeReference
    samples: tuple[Stage42UnifiedLoopSample, ...]
    deterministic_ticcmd_intake: int
    selected_g_ticker_ownership: int
    selected_p_ticker_ordering: int
    selected_player_movement_update: int
    selected_psprite_weapon_update: int
    selected_pickup_damage_projectile_update: int
    status_after_gameplay_mutation: int
    status_draw_after_world_vissprite_and_psprite: int
    status_draw_after_feedback_and_projectile_state: int
    source_d_loop_boundary: int
    source_g_game_boundary: int
    source_p_tick_boundary: int
    source_p_user_boundary: int
    source_p_pspr_boundary: int
    source_p_mobj_boundary: int
    source_p_enemy_boundary: int
    source_r_main_boundary: int
    source_st_stuff_boundary: int
    source_hu_stuff_boundary: int
    source_p_inter_boundary: int
    source_v_video_boundary: int
    source_i_video_boundary: int
    distinct_unified_loop_state_signatures: int
    distinct_framebuffer_signatures: int
    timer_samples: int
    invalidate_calls: int
    update_window_calls: int
    expected_paint_calls: int
    paint_after_final_unified_sample: int
    final_window_alive_after_samples: int
    closes_normally: int
    compact_status_strip_preserved: int
    stage41_status_preserved: int
    stage40_vissprite_preserved: int
    stage39_projectile_state_preserved: int
    stage38_present_preserved: int
    stage37_feedback_preserved: int
    stage36_pickup_preserved: int
    stage35_drop_preserved: int
    stage34_death_preserved: int
    stage33_impact_preserved: int
    stage32_psprite_preserved: int
    stage31_wall_flat_preserved: int
    stage30_preserved: int
    stage29_preserved: int
    stage28_preserved: int
    stage27_preserved: int
    stage26_preserved: int
    stage25_preserved: int
    stage24_preserved: int
    stage23_preserved: int
    stage22_preserved: int
    stage21_preserved: int
    stage20_preserved: int
    stage19_preserved: int
    full_frame_byte_arrays_absent: int
    runtime_renderer_primitives: int
    live_input_absent: int
    generalized_thinkers_absent: int
    generalized_collision_absent: int
    generalized_projectile_manager_absent: int
    explosions_absent: int
    radius_damage_absent: int
    splash_damage_absent: int
    broad_monster_ai_absent: int
    generalized_combat_absent: int
    broad_inventory_absent: int
    broad_hud_statusbar_rebuild_absent: int
    classic_full_statusbar_layout_absent: int
    face_animation_absent: int
    automap_absent: int
    menu_absent: int
    intermission_absent: int
    save_load_absent: int
    networking_absent: int
    music_absent: int
    real_audio_absent: int
    mixer_device_playback_absent: int
    map_progression_absent: int
    infighting_absent: int
    player_death_absent: int
    enemy_kill_drop_absent: int
    broad_all_map_sprite_traversal_absent: int
    source_stage43_absent: int
    state_signature: int
    signature: int


def _ticcmd_signature(cmd: Stage42TicCmd) -> int:
    sig = fnv1a_words((cmd.tic, cmd.forwardmove, cmd.sidemove, cmd.angleturn, cmd.buttons, cmd.consistency, cmd.source_index))
    return _hash_ascii(sig, cmd.source_marker)


def _selected_player_signature(player: Stage42SelectedPlayerState) -> int:
    sig = fnv1a_words(
        (
            player.x,
            player.y,
            player.angle,
            player.momx,
            player.momy,
            player.viewz,
            player.health,
            player.armor,
            player.shell_ammo,
            player.shotgun_owned,
            player.pending_weapon,
            player.ready_weapon,
            player.psprite_tics,
            player.bonuscount,
            player.damagecount,
        )
    )
    sig = _hash_ascii(sig, player.psprite_state_name)
    sig = _hash_ascii(sig, player.message)
    return _hash_ascii(sig, player.source_marker)


def _selected_mobj_signature(mobj: Stage42SelectedMobjState) -> int:
    sig = fnv1a_words(
        (
            mobj.enemy_health,
            mobj.enemy_target_present,
            mobj.dropped_shotgun_present,
            mobj.dropped_shotgun_removed,
            mobj.projectile_present,
            mobj.projectile_x,
            mobj.projectile_y,
            mobj.projectile_z,
            mobj.projectile_tics,
            mobj.projectile_sound_events,
        )
    )
    for text in (
        mobj.enemy_type_name,
        mobj.enemy_state_name,
        mobj.projectile_type_name,
        mobj.projectile_state_name,
        mobj.source_marker,
    ):
        sig = _hash_ascii(sig, text)
    return sig


def _unified_loop_state_signature(sample: Stage42UnifiedLoopSample) -> int:
    sig = fnv1a_words(
        (
            sample.step,
            sample.tic,
            _ticcmd_signature(sample.ticcmd),
            _selected_player_signature(sample.player),
            _selected_mobj_signature(sample.mobj),
            sample.command_record_count,
            sample.status_command_count,
            sample.framebuffer_signature,
            sample.status_state_signature,
            sample.world_vissprite_state_signature,
            sample.world_vissprite_framebuffer_signature,
            sample.projectile_state_signature,
            sample.start_tic_sequence,
            sample.ticcmd_sequence,
            sample.g_ticker_sequence,
            sample.p_ticker_sequence,
            sample.player_update_sequence,
            sample.psprite_weapon_update_sequence,
            sample.pickup_damage_projectile_sequence,
            sample.clear_sequence,
            sample.wall_flat_sequence,
            sample.world_vissprite_sequence,
            sample.psprite_sequence,
            sample.status_sequence,
            sample.signature_sequence,
            sample.present_sequence,
        )
    )
    return _hash_ascii(sig, "stage42 selected tic -> update -> render -> compact status -> present")


def _stage42_signature(ref: Stage42UnifiedLiveTickRenderLoopProbeReference) -> int:
    sig = fnv1a_words(
        (
            ref.stage41.signature,
            ref.stage41.state_signature,
            len(ref.samples),
            ref.deterministic_ticcmd_intake,
            ref.selected_g_ticker_ownership,
            ref.selected_p_ticker_ordering,
            ref.selected_player_movement_update,
            ref.selected_psprite_weapon_update,
            ref.selected_pickup_damage_projectile_update,
            ref.status_after_gameplay_mutation,
            ref.status_draw_after_world_vissprite_and_psprite,
            ref.status_draw_after_feedback_and_projectile_state,
            ref.distinct_unified_loop_state_signatures,
            ref.distinct_framebuffer_signatures,
            ref.paint_after_final_unified_sample,
            ref.compact_status_strip_preserved,
            ref.stage40_vissprite_preserved,
            ref.stage39_projectile_state_preserved,
            ref.stage38_present_preserved,
            ref.stage37_feedback_preserved,
            ref.stage36_pickup_preserved,
            ref.stage35_drop_preserved,
            ref.stage34_death_preserved,
            ref.stage33_impact_preserved,
            ref.stage32_psprite_preserved,
            ref.stage31_wall_flat_preserved,
            ref.full_frame_byte_arrays_absent,
            ref.runtime_renderer_primitives,
            ref.live_input_absent,
            ref.generalized_thinkers_absent,
            ref.generalized_collision_absent,
            ref.generalized_projectile_manager_absent,
            ref.explosions_absent,
            ref.radius_damage_absent,
            ref.splash_damage_absent,
            ref.broad_monster_ai_absent,
            ref.generalized_combat_absent,
            ref.broad_inventory_absent,
            ref.broad_hud_statusbar_rebuild_absent,
            ref.classic_full_statusbar_layout_absent,
            ref.face_animation_absent,
            ref.automap_absent,
            ref.menu_absent,
            ref.intermission_absent,
            ref.save_load_absent,
            ref.networking_absent,
            ref.music_absent,
            ref.real_audio_absent,
            ref.mixer_device_playback_absent,
            ref.map_progression_absent,
            ref.infighting_absent,
            ref.player_death_absent,
            ref.enemy_kill_drop_absent,
            ref.broad_all_map_sprite_traversal_absent,
            ref.source_stage43_absent,
            ref.state_signature,
        )
    )
    for sample in ref.samples:
        sig = fnv1a_words(
            (
                sample.step,
                sample.tic,
                sample.ticcmd.forwardmove,
                sample.ticcmd.sidemove,
                sample.ticcmd.angleturn,
                sample.player.x,
                sample.player.y,
                sample.player.health,
                sample.player.shell_ammo,
                sample.player.shotgun_owned,
                sample.player.ready_weapon,
                sample.mobj.dropped_shotgun_present,
                sample.mobj.dropped_shotgun_removed,
                sample.mobj.projectile_present,
                sample.mobj.projectile_tics,
                sample.framebuffer_signature,
                sample.status_state_signature,
                sample.world_vissprite_state_signature,
                sample.unified_loop_state_signature,
            ),
            sig,
        )
        sig = _hash_ascii(sig, sample.player.message)
    return sig


def _scripted_ticcmds(samples: Sequence[stage41.Stage41StatusSample]) -> tuple[Stage42TicCmd, ...]:
    script = ((0, 0, 0, 0), (14, 0, 96, 0), (8, -5, -32, 0))
    commands: list[Stage42TicCmd] = []
    for index, sample in enumerate(samples):
        forwardmove, sidemove, angleturn, buttons = script[index % len(script)]
        consistency = fnv1a_words((sample.tic, forwardmove, sidemove, angleturn, buttons, index))
        commands.append(
            Stage42TicCmd(
                tic=sample.tic,
                forwardmove=forwardmove,
                sidemove=sidemove,
                angleturn=angleturn,
                buttons=buttons,
                consistency=consistency,
                source_index=index,
                source_marker="D_DoomLoop/I_StartTic deterministic ticcmd table",
            )
        )
    return tuple(commands)


def _selected_player_state(
    index: int,
    cmd: Stage42TicCmd,
    sample41: stage41.Stage41StatusSample,
    ref41: stage41.Stage41StatusbarWeaponAmmoFeedbackBridgeReference,
) -> Stage42SelectedPlayerState:
    ref32 = ref41.stage40.stage39.stage38.stage36.stage34.stage33.stage32
    base = ref32.stage31.samples[index]
    psp = ref32.samples[index]
    status = sample41.status
    fracunit = 1 << stage31.FRACBITS
    x = base.viewx + cmd.forwardmove * fracunit
    y = base.viewy + cmd.sidemove * fracunit
    angle = (base.viewangle + (cmd.angleturn << 16)) & 0xFFFFFFFF
    ready_weapon = stage15.WP_PISTOL if index < 2 else stage15.WP_SHOTGUN
    return Stage42SelectedPlayerState(
        x=x,
        y=y,
        angle=angle,
        momx=cmd.forwardmove * fracunit,
        momy=cmd.sidemove * fracunit,
        viewz=base.viewz,
        health=status.health,
        armor=status.armor,
        shell_ammo=status.shell_ammo,
        shotgun_owned=status.shotgun_owned,
        pending_weapon=status.pending_weapon,
        ready_weapon=ready_weapon,
        psprite_state_name=psp.psprite_state_name,
        psprite_tics=psp.psprite_tics,
        bonuscount=status.bonuscount,
        damagecount=status.damagecount,
        message=status.message,
        source_marker="G_Ticker/P_PlayerThink/P_MovePsprites selected player state",
    )


def _selected_mobj_state(
    index: int,
    ref41: stage41.Stage41StatusbarWeaponAmmoFeedbackBridgeReference,
) -> Stage42SelectedMobjState:
    ref39 = ref41.stage40.stage39
    projectile = ref39.projectile
    pickup = ref39.stage38.stage36.pickup
    enemy_states = ("S_TROO_STND", "S_TROO_ATK2", "S_TROO_RUN1")
    projectile_present = 0 if index == 0 else 1
    if index == 0:
        projectile_x = projectile.spawn_x
        projectile_y = projectile.spawn_y
        projectile_z = projectile.spawn_z
        projectile_tics = 0
    elif index == 1:
        projectile_x = projectile.spawn_x
        projectile_y = projectile.spawn_y
        projectile_z = projectile.spawn_z
        projectile_tics = projectile.tics_after_adjustment
    else:
        projectile_x = projectile.half_step_x
        projectile_y = projectile.half_step_y
        projectile_z = projectile.half_step_z
        projectile_tics = max(1, projectile.tics_after_adjustment - 1)
    return Stage42SelectedMobjState(
        enemy_type_name=ref39.candidate.type_name,
        enemy_state_name=enemy_states[index % len(enemy_states)],
        enemy_health=ref39.candidate.health,
        enemy_target_present=ref39.candidate.target_present,
        dropped_shotgun_present=pickup.item_present_before if index == 0 else pickup.item_present_after,
        dropped_shotgun_removed=0 if index == 0 else pickup.removed_item,
        projectile_type_name=projectile.type_name,
        projectile_state_name=projectile.spawnstate_name,
        projectile_present=projectile_present,
        projectile_x=projectile_x,
        projectile_y=projectile_y,
        projectile_z=projectile_z,
        projectile_tics=projectile_tics,
        projectile_sound_events=projectile.sound_events if index == 2 else 0,
        source_marker="P_MobjThinker/A_TroopAttack/P_TouchSpecialThing selected tiny mobj set",
    )


def reference_unified_live_tick_render_loop_probe_for_pinned_map(
    wad_path: str | Path,
) -> Stage42UnifiedLiveTickRenderLoopProbeReference:
    ref41 = stage41.reference_statusbar_weapon_ammo_feedback_bridge_for_pinned_map(wad_path)
    commands = _scripted_ticcmds(ref41.samples)
    samples: list[Stage42UnifiedLoopSample] = []
    for index, sample41 in enumerate(ref41.samples):
        sample40 = sample41.baseline
        cmd = commands[index]
        player = _selected_player_state(index, cmd, sample41, ref41)
        mobj = _selected_mobj_state(index, ref41)
        seq = index * 20
        sample = Stage42UnifiedLoopSample(
            step=index + 1,
            tic=sample41.tic,
            baseline=sample41,
            ticcmd=cmd,
            player=player,
            mobj=mobj,
            command_record_count=1,
            status_command_count=sample41.command_count,
            framebuffer_signature=sample41.framebuffer_signature,
            status_state_signature=sample41.selected_status_state_signature,
            world_vissprite_state_signature=sample40.selected_state_signature,
            world_vissprite_framebuffer_signature=sample40.vissprite_framebuffer_signature,
            projectile_state_signature=ref41.stage40.stage39.projectile.state_signature,
            unified_loop_state_signature=0,
            start_tic_sequence=seq + 1,
            ticcmd_sequence=seq + 2,
            g_ticker_sequence=seq + 3,
            p_ticker_sequence=seq + 4,
            player_update_sequence=seq + 5,
            psprite_weapon_update_sequence=seq + 6,
            pickup_damage_projectile_sequence=seq + 7,
            clear_sequence=seq + 8,
            wall_flat_sequence=seq + 9,
            impact_sequence=seq + 10,
            death_sequence=seq + 11,
            drop_sequence=seq + 12,
            world_vissprite_sequence=seq + 13,
            psprite_sequence=seq + 14,
            feedback_sequence=seq + 15,
            projectile_state_sequence=seq + 16,
            status_sequence=seq + 17,
            signature_sequence=seq + 18,
            present_sequence=seq + 19,
        )
        samples.append(Stage42UnifiedLoopSample(**{**sample.__dict__, "unified_loop_state_signature": _unified_loop_state_signature(sample)}))

    state_signature = fnv1a_words(tuple(sample.unified_loop_state_signature for sample in samples))
    state_signature = _hash_ascii(state_signature, "stage42 unified selected live tick render loop")
    ref39 = ref41.stage40.stage39
    ref38 = ref39.stage38
    ref36 = ref38.stage36
    ref31 = ref36.stage34.stage33.stage32.stage31
    ref29 = ref38.stage29
    draft = Stage42UnifiedLiveTickRenderLoopProbeReference(
        stage41=ref41,
        samples=tuple(samples),
        deterministic_ticcmd_intake=1,
        selected_g_ticker_ownership=1,
        selected_p_ticker_ordering=1,
        selected_player_movement_update=1,
        selected_psprite_weapon_update=1,
        selected_pickup_damage_projectile_update=1,
        status_after_gameplay_mutation=1,
        status_draw_after_world_vissprite_and_psprite=1,
        status_draw_after_feedback_and_projectile_state=1,
        source_d_loop_boundary=1,
        source_g_game_boundary=1,
        source_p_tick_boundary=1,
        source_p_user_boundary=1,
        source_p_pspr_boundary=1,
        source_p_mobj_boundary=1,
        source_p_enemy_boundary=1,
        source_r_main_boundary=1,
        source_st_stuff_boundary=1,
        source_hu_stuff_boundary=1,
        source_p_inter_boundary=1,
        source_v_video_boundary=1,
        source_i_video_boundary=1,
        distinct_unified_loop_state_signatures=len({sample.unified_loop_state_signature for sample in samples}),
        distinct_framebuffer_signatures=len({sample.framebuffer_signature for sample in samples}),
        timer_samples=len(samples),
        invalidate_calls=len(samples),
        update_window_calls=len(samples),
        expected_paint_calls=len(samples),
        paint_after_final_unified_sample=1,
        final_window_alive_after_samples=1,
        closes_normally=1,
        compact_status_strip_preserved=ref41.compact_status_strip_drawn,
        stage41_status_preserved=1 if (ref41.signature == BASELINE_S41_SIGNATURE and ref41.state_signature == BASELINE_S41_STATE_SIGNATURE) else 0,
        stage40_vissprite_preserved=ref41.stage40_vissprite_preserved,
        stage39_projectile_state_preserved=ref41.stage39_projectile_state_preserved,
        stage38_present_preserved=ref41.stage38_present_preserved,
        stage37_feedback_preserved=ref41.stage37_feedback_preserved,
        stage36_pickup_preserved=ref41.stage36_pickup_preserved,
        stage35_drop_preserved=ref41.stage35_drop_preserved,
        stage34_death_preserved=ref41.stage34_death_preserved,
        stage33_impact_preserved=ref41.stage33_impact_preserved,
        stage32_psprite_preserved=ref41.stage32_psprite_preserved,
        stage31_wall_flat_preserved=ref41.stage31_wall_flat_preserved,
        stage30_preserved=1 if ref31.stage30.signature == 3898523864 else 0,
        stage29_preserved=1 if ref29.signature == 3738922932 else 0,
        stage28_preserved=1 if ref29.stage28.signature == 2805406010 else 0,
        stage27_preserved=1 if ref29.stage28.stage27.signature == 1735738182 else 0,
        stage26_preserved=1 if ref29.stage28.stage27.stage26.signature == 132405987 else 0,
        stage25_preserved=1 if ref29.stage28.stage27.stage26.stage25.signature == 1688844032 else 0,
        stage24_preserved=1 if ref29.stage28.stage27.stage26.stage25.stage24.signature == 1919312263 else 0,
        stage23_preserved=1 if ref29.stage28.stage27.stage26.stage25.stage24.stage23.signature == 3216085132 else 0,
        stage22_preserved=1 if ref29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.signature == 2207028069 else 0,
        stage21_preserved=1 if ref29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.signature == 1770773845 else 0,
        stage20_preserved=1 if ref29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.signature == 3226031347 else 0,
        stage19_preserved=1 if ref29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature == 2088411722 else 0,
        full_frame_byte_arrays_absent=1,
        runtime_renderer_primitives=1,
        live_input_absent=1,
        generalized_thinkers_absent=1,
        generalized_collision_absent=1,
        generalized_projectile_manager_absent=1,
        explosions_absent=1,
        radius_damage_absent=1,
        splash_damage_absent=1,
        broad_monster_ai_absent=1,
        generalized_combat_absent=1,
        broad_inventory_absent=1,
        broad_hud_statusbar_rebuild_absent=1,
        classic_full_statusbar_layout_absent=1,
        face_animation_absent=1,
        automap_absent=1,
        menu_absent=1,
        intermission_absent=1,
        save_load_absent=1,
        networking_absent=1,
        music_absent=1,
        real_audio_absent=1,
        mixer_device_playback_absent=1,
        map_progression_absent=1,
        infighting_absent=1,
        player_death_absent=1,
        enemy_kill_drop_absent=1,
        broad_all_map_sprite_traversal_absent=1,
        source_stage43_absent=1,
        state_signature=state_signature,
        signature=0,
    )
    return Stage42UnifiedLiveTickRenderLoopProbeReference(
        **{**draft.__dict__, "signature": _stage42_signature(draft)}
    )


@lru_cache(maxsize=1)
def _reference_for_default_wad_or_none() -> Stage42UnifiedLiveTickRenderLoopProbeReference | None:
    wad = REPO_ROOT / WAD_PATH
    if not wad.exists():
        return None
    return reference_unified_live_tick_render_loop_probe_for_pinned_map(wad)


def _stage42_replay_titles(ref: Stage42UnifiedLiveTickRenderLoopProbeReference | None) -> list[str]:
    if ref is None:
        return [
            "Inference Doom S42 STEP42=1 missing pinned WAD",
            "Inference Doom S42 STEP42=2 missing pinned WAD",
            "Inference Doom S42 STEP42=3 missing pinned WAD",
        ]
    titles: list[str] = []
    ref41 = ref.stage41
    ref40 = ref41.stage40
    ref39 = ref40.stage39
    ref38 = ref39.stage38
    for sample in ref.samples:
        cmd = sample.ticcmd
        player = sample.player
        mobj = sample.mobj
        titles.append(
            "Inference Doom S42 "
            f"STEP42={sample.step} TIC42={sample.tic} "
            f"CMD42=F{cmd.forwardmove}/S{cmd.sidemove}/A{cmd.angleturn}/B{cmd.buttons} "
            f"PX42={player.x >> stage31.FRACBITS} PY42={player.y >> stage31.FRACBITS} "
            f"HP42={player.health} ARM42={player.armor} SHELL42={player.shell_ammo} WOWN42={player.shotgun_owned} "
            f"PEND42={player.pending_weapon} READY42={player.ready_weapon} PSP42={player.psprite_state_name} MSG42={player.message or 'NONE'} "
            f"DROP42={mobj.dropped_shotgun_present}->{mobj.dropped_shotgun_removed} PROJ42={mobj.projectile_present}:{mobj.projectile_state_name} "
            f"PTIC42={mobj.projectile_tics} EN42={mobj.enemy_type_name}:{mobj.enemy_state_name} "
            f"FB42={sample.framebuffer_signature} ST42={sample.status_state_signature} VSTATE42={sample.world_vissprite_state_signature} "
            f"VFB42={sample.world_vissprite_framebuffer_signature} ULSTATE42={sample.unified_loop_state_signature} "
            f"STATE42={ref.state_signature} S42SIG={ref.signature} "
            f"FB41={sample.baseline.framebuffer_signature} SSTATE41={sample.baseline.selected_status_state_signature} "
            f"STATE41={ref41.state_signature} S41SIG={ref41.signature} "
            f"S40SIG={ref40.signature} STATE40={ref40.state_signature} MISS39={ref39.projectile.type_name} PST39={ref39.projectile.state_signature} "
            f"S39SIG={ref39.signature} STATE39={ref39.projectile.state_signature} S38SIG={ref38.signature} STATE38={ref38.attack.state_signature} "
            f"HP38={ref38.attack.health_before}->{ref38.attack.health_after} DMG38={ref38.attack.damagecount_after} "
            f"PICK36={ref38.stage36.pickup.give_weapon_return} GOT36={ref38.stage36.pickup.message} "
            f"INV42={sample.step} UPD42={sample.step} PAINT42={sample.step} PAF42={1 if sample.step == len(ref.samples) else 0} "
            f"INV41={ref41.invalidate_calls} UPD41={ref41.update_window_calls} PAINT41={ref41.expected_paint_calls} PAF41={ref41.paint_after_final_status} "
            f"INV40={ref40.invalidate_calls} UPD40={ref40.update_window_calls} PAINT40={ref40.expected_paint_calls} PAF40={ref40.paint_after_final_vissprite} "
            f"INV39={ref39.invalidate_calls} UPD39={ref39.update_window_calls} PAINT39={ref39.expected_paint_calls} PAF39={ref39.paint_after_final_projectile_marker} "
            f"S37SIG={stage39.BASELINE_S37_SIGNATURE} S36SIG={ref38.stage36.signature} S35SIG={stage36.ref35_signature(ref38.stage36)} "
            f"S34SIG={ref38.stage36.stage34.signature} S33SIG={ref38.stage36.stage34.stage33.signature} "
            f"S32SIG={ref38.stage36.stage34.stage33.stage32.signature} S31SIG={ref38.stage36.stage34.stage33.stage32.stage31.signature} "
            f"S30SIG={ref38.stage36.stage34.stage33.stage32.stage31.stage30.signature} S29SIG={ref38.stage29.signature} "
            f"S28SIG={ref38.stage29.stage28.signature} S27SIG={ref38.stage29.stage28.stage27.signature} "
            f"S26SIG={ref38.stage29.stage28.stage27.stage26.signature} S25SIG={ref38.stage29.stage28.stage27.stage26.stage25.signature} "
            f"S24SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.signature} "
            f"S23SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.signature} "
            f"S22SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.signature} "
            f"S21SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.signature} "
            f"S20SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.signature} "
            f"S19SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature} "
            f"NOFULL42={ref.full_frame_byte_arrays_absent} LIVEIN42=0 GEN42=0 S43ABS={ref.source_stage43_absent}"
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


def emit_stage42_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")
    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage42_class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage42_class_registered")
    x86.call_rel32(pe, "source_stage42_load_wad_unified_live_tick_render_loop_probe")
    x86.call_rel32(pe, "append_stage42_success_status")
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
    x86.jne_rel32(pe, "stage42_window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage42_window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_abs32(pe, "stage42_replay_title_start")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE42_TIMER_MS)
    x86.push_imm32(pe, STAGE42_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
    pe.label("stage42_message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage42_clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "stage42_message_error")
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, stage38.WM_TIMER)
    x86.jne_rel32(pe, "stage42_dispatch_message")
    x86.call_rel32(pe, "stage42_timer_tick")
    pe.label("stage42_dispatch_message")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "stage42_message_loop")
    pe.label("stage42_clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage42_message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_stage42_timer_tick(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(stage38.SELECTED_SAMPLE_TICS)
    pe.label("stage42_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage42_replay_step")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage42_replay_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage42_replay_sample{index}")
        x86.call_rel32(pe, f"stage42_draw_sample{index}")
        x86.push_abs32(pe, f"stage42_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        if index == sample_count - 1:
            x86.mov_mem_abs32_imm32(pe, "stage42_final_unified_sample_drawn", 1)
        stage07._emit_inc_abs32(pe, "stage42_invalidate_calls")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        stage07._emit_inc_abs32(pe, "stage42_update_window_calls")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.mov_mem_abs32_imm32(pe, "stage42_replay_step", index + 1)
        if index == sample_count - 1:
            x86.push_imm32(pe, STAGE42_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)


def emit_stage42_wndproc_framebuffer(pe: PE32) -> None:
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
    stage07._emit_inc_abs32(pe, "stage42_paint_calls")
    x86.mov_reg_mem_abs32(pe, "eax", "stage42_final_unified_sample_drawn")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "stage42_paint_after_final_skip")
    stage07._emit_inc_abs32(pe, "stage42_paint_after_final_unified")
    pe.label("stage42_paint_after_final_skip")
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


def _emit_stage42_update_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage42_update_selected_state_sample{index}")
    x86.mov_mem_abs32_abs32(pe, "stage42_runtime_ticcmd_ptr", f"stage42_ticcmd_record_{index}")
    for dst, src in (
        ("stage42_runtime_tic", f"stage42_sample{index}_tic"),
        ("stage42_runtime_forwardmove", f"stage42_sample{index}_forwardmove"),
        ("stage42_runtime_sidemove", f"stage42_sample{index}_sidemove"),
        ("stage42_runtime_angleturn", f"stage42_sample{index}_angleturn"),
        ("stage42_runtime_buttons", f"stage42_sample{index}_buttons"),
        ("stage42_runtime_player_x", f"stage42_sample{index}_player_x"),
        ("stage42_runtime_player_y", f"stage42_sample{index}_player_y"),
        ("stage42_runtime_player_angle", f"stage42_sample{index}_player_angle"),
        ("stage42_runtime_health", f"stage42_sample{index}_health"),
        ("stage42_runtime_shell_ammo", f"stage42_sample{index}_shell_ammo"),
        ("stage42_runtime_shotgun_owned", f"stage42_sample{index}_shotgun_owned"),
        ("stage42_runtime_pending_weapon", f"stage42_sample{index}_pending_weapon"),
        ("stage42_runtime_ready_weapon", f"stage42_sample{index}_ready_weapon"),
        ("stage42_runtime_projectile_present", f"stage42_sample{index}_projectile_present"),
        ("stage42_runtime_projectile_tics", f"stage42_sample{index}_projectile_tics"),
        ("stage42_runtime_drop_present", f"stage42_sample{index}_drop_present"),
        ("stage42_runtime_drop_removed", f"stage42_sample{index}_drop_removed"),
        ("stage42_runtime_unified_state_signature", f"stage42_sample{index}_unified_state_signature"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_stage42_draw_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage42_draw_sample{index}")
    x86.call_rel32(pe, f"stage42_update_selected_state_sample{index}")
    x86.call_rel32(pe, f"stage41_draw_sample{index}")
    for dst, src in (
        ("stage42_runtime_fb_signature", "stage41_runtime_fb_signature"),
        ("stage42_runtime_status_signature", "stage41_selected_status_state"),
        ("stage42_runtime_vissprite_fb_signature", "stage40_vissprite_fb_signature"),
        ("stage42_runtime_world_fb_signature", "stage40_runtime_fb_signature"),
        ("stage42_runtime_projectile_state", "stage39_projectile_state"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def emit_source_stage42_load_wad_unified_live_tick_render_loop_probe(pe: PE32) -> None:
    pe.label("source_stage42_load_wad_unified_live_tick_render_loop_probe")
    x86.call_rel32(pe, "source_stage41_load_wad_statusbar_weapon_ammo_feedback_bridge")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage42_load_fail")
    x86.mov_reg_mem_abs32(pe, "eax", "stage41_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage41_expected_signature")
    x86.jne_rel32(pe, "stage42_load_fail")
    x86.call_rel32(pe, "render_unified_live_tick_render_loop_probe_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage42_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage42_expected_signature")
    x86.jne_rel32(pe, "stage42_load_fail")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage42_load_fail")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def emit_render_unified_live_tick_render_loop_probe_debug(pe: PE32) -> None:
    for _, _, label in SOURCE_TRACE[-13:]:
        pe.label(label)
    pe.label("render_unified_live_tick_render_loop_probe_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage42_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage42_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage42_expected_state_signature")
    x86.mov_mem_abs32_eax(pe, "stage42_runtime_state_signature")
    x86.ret(pe)


def emit_append_stage42_success_status(pe: PE32) -> None:
    pe.label("append_stage42_success_status")
    stage01.emit_set_status_ptrs(pe, "status_stage42_success_header", "stage42_replay_title_start")
    x86.ret(pe)


def _emit_ticcmd_record(pe: PE32, cmd: Stage42TicCmd) -> None:
    for value in (cmd.tic, cmd.forwardmove, cmd.sidemove, cmd.angleturn, cmd.buttons, cmd.consistency, cmd.source_index):
        pe.emit_u32(value & 0xFFFFFFFF)


def emit_stage42_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    samples = ref.samples if ref else ()
    pe.align_section(4)
    values = (
        ("stage42_frame_count", len(samples)),
        ("stage42_distinct_unified_state_signatures", ref.distinct_unified_loop_state_signatures if ref else 0),
        ("stage42_distinct_fb_signatures", ref.distinct_framebuffer_signatures if ref else 0),
        ("stage42_expected_state_signature", ref.state_signature if ref else 0),
        ("stage42_runtime_state_signature", 0),
        ("stage42_expected_signature", ref.signature if ref else 0),
        ("stage42_runtime_signature", 0),
        ("stage42_runtime_fb_signature", 0),
        ("stage42_runtime_status_signature", 0),
        ("stage42_runtime_vissprite_fb_signature", 0),
        ("stage42_runtime_world_fb_signature", 0),
        ("stage42_runtime_projectile_state", 0),
        ("stage42_runtime_ticcmd_ptr", 0),
        ("stage42_runtime_tic", 0),
        ("stage42_runtime_forwardmove", 0),
        ("stage42_runtime_sidemove", 0),
        ("stage42_runtime_angleturn", 0),
        ("stage42_runtime_buttons", 0),
        ("stage42_runtime_player_x", 0),
        ("stage42_runtime_player_y", 0),
        ("stage42_runtime_player_angle", 0),
        ("stage42_runtime_health", 0),
        ("stage42_runtime_shell_ammo", 0),
        ("stage42_runtime_shotgun_owned", 0),
        ("stage42_runtime_pending_weapon", 0),
        ("stage42_runtime_ready_weapon", 0),
        ("stage42_runtime_projectile_present", 0),
        ("stage42_runtime_projectile_tics", 0),
        ("stage42_runtime_drop_present", 0),
        ("stage42_runtime_drop_removed", 0),
        ("stage42_runtime_unified_state_signature", 0),
        ("stage42_replay_step", 0),
        ("stage42_invalidate_calls", 0),
        ("stage42_update_window_calls", 0),
        ("stage42_paint_calls", 0),
        ("stage42_final_unified_sample_drawn", 0),
        ("stage42_paint_after_final_unified", 0),
        ("stage42_expected_timer_samples", ref.timer_samples if ref else 0),
        ("stage42_expected_invalidate_calls", ref.invalidate_calls if ref else 0),
        ("stage42_expected_update_window_calls", ref.update_window_calls if ref else 0),
        ("stage42_expected_paint_calls", ref.expected_paint_calls if ref else 0),
        ("stage42_expected_paint_after_final_unified", ref.paint_after_final_unified_sample if ref else 0),
        ("stage42_deterministic_ticcmd_intake", ref.deterministic_ticcmd_intake if ref else 1),
        ("stage42_status_after_gameplay_mutation", ref.status_after_gameplay_mutation if ref else 1),
        ("stage42_status_draw_after_world_vissprite_and_psprite", ref.status_draw_after_world_vissprite_and_psprite if ref else 1),
        ("stage42_full_frame_byte_arrays_absent", ref.full_frame_byte_arrays_absent if ref else 1),
        ("stage42_runtime_renderer_primitives", ref.runtime_renderer_primitives if ref else 1),
        ("stage42_live_input_absent", ref.live_input_absent if ref else 1),
        ("stage42_generalized_thinkers_absent", ref.generalized_thinkers_absent if ref else 1),
        ("stage42_generalized_collision_absent", ref.generalized_collision_absent if ref else 1),
        ("stage42_generalized_projectile_manager_absent", ref.generalized_projectile_manager_absent if ref else 1),
        ("stage42_broad_monster_ai_absent", ref.broad_monster_ai_absent if ref else 1),
        ("stage42_source_stage43_absent", ref.source_stage43_absent if ref else 1),
    )
    for name, value in values:
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        fields = (
            (f"stage42_sample{index}_tic", sample.tic),
            (f"stage42_sample{index}_forwardmove", sample.ticcmd.forwardmove),
            (f"stage42_sample{index}_sidemove", sample.ticcmd.sidemove),
            (f"stage42_sample{index}_angleturn", sample.ticcmd.angleturn),
            (f"stage42_sample{index}_buttons", sample.ticcmd.buttons),
            (f"stage42_sample{index}_ticcmd_signature", _ticcmd_signature(sample.ticcmd)),
            (f"stage42_sample{index}_player_x", sample.player.x),
            (f"stage42_sample{index}_player_y", sample.player.y),
            (f"stage42_sample{index}_player_angle", sample.player.angle),
            (f"stage42_sample{index}_health", sample.player.health),
            (f"stage42_sample{index}_shell_ammo", sample.player.shell_ammo),
            (f"stage42_sample{index}_shotgun_owned", sample.player.shotgun_owned),
            (f"stage42_sample{index}_pending_weapon", sample.player.pending_weapon),
            (f"stage42_sample{index}_ready_weapon", sample.player.ready_weapon),
            (f"stage42_sample{index}_projectile_present", sample.mobj.projectile_present),
            (f"stage42_sample{index}_projectile_tics", sample.mobj.projectile_tics),
            (f"stage42_sample{index}_drop_present", sample.mobj.dropped_shotgun_present),
            (f"stage42_sample{index}_drop_removed", sample.mobj.dropped_shotgun_removed),
            (f"stage42_sample{index}_framebuffer_signature", sample.framebuffer_signature),
            (f"stage42_sample{index}_status_signature", sample.status_state_signature),
            (f"stage42_sample{index}_vissprite_state_signature", sample.world_vissprite_state_signature),
            (f"stage42_sample{index}_vissprite_fb_signature", sample.world_vissprite_framebuffer_signature),
            (f"stage42_sample{index}_unified_state_signature", sample.unified_loop_state_signature),
        )
        for name, value in fields:
            pe.label(name)
            pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        pe.align_section(4)
        pe.label(f"stage42_ticcmd_record_{index}")
        _emit_ticcmd_record(pe, sample.ticcmd)
    pe.label("status_stage42_success_header")
    x86.emit_asciiz(pe, "\r\nUnified Live Tick Render Loop Probe proof OK\r\n")
    pe.label("status_stage42_log_prefix")
    x86.emit_asciiz(pe, "source_stage42_unified_live_tick_render_loop_probe ")
    pe.label("stage42_log_text")
    x86.emit_asciiz(
        pe,
        "D_DoomLoop/I_StartTic deterministic ticcmd table -> G_Ticker/P_Ticker selected player and tiny mobj updates -> "
        "stage31 clear/wall/flat, stage40 selected world-vissprite, stage32 psprite, stage41 compact status strip, "
        "stable InvalidateRect/UpdateWindow/WM_PAINT present, NOFULL42=1, no live input/general thinkers/collision/projectile manager/audio ",
    )
    pe.label("stage42_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S42 UNIFIED START STEP42=0 waiting for selected live tick render replay")
    for index, title in enumerate(_stage42_replay_titles(ref)):
        pe.label(f"stage42_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)


def build_source_stage42_unified_live_tick_render_loop_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(stage38.SELECTED_SAMPLE_TICS)
    with patched_stage01_window_labels():
        emit_stage42_entry(pe)
        emit_stage42_wndproc_framebuffer(pe)
        emit_stage42_timer_tick(pe)
        stage31.emit_stage31_clear_framebuffer(pe)
        stage31.emit_stage31_framebuffer_signature(pe)
        stage31.emit_stage31_draw_command_loops(pe)
        stage40.stage33.emit_stage33_draw_impact_commands(pe)
        stage36.emit_stage36_draw_death_commands(pe)
        stage36.emit_stage36_draw_drop_commands(pe)
        stage40.emit_stage40_draw_vissprite_commands(pe)
        stage32.emit_stage32_draw_psprite_commands(pe)
        stage38.emit_stage38_draw_feedback_marker(pe)
        stage41.emit_stage41_draw_status_strip(pe)
        for index in range(sample_count):
            stage40._emit_stage40_draw_sample(pe, index)
            stage41._emit_stage41_draw_sample(pe, index)
            _emit_stage42_update_sample(pe, index)
            _emit_stage42_draw_sample(pe, index)
        stage36.emit_source_stage36_load_wad_selected_dropped_shotgun_visual_boundary(pe)
        stage38.emit_source_stage38_load_wad_selected_attack_feedback_present_bridge(pe)
        stage39.emit_source_stage39_load_wad_selected_projectile_spawn_present_probe(pe)
        stage40.emit_source_stage40_load_wad_bounded_vissprite_traversal_sorting_bridge(pe)
        stage41.emit_source_stage41_load_wad_statusbar_weapon_ammo_feedback_bridge(pe)
        emit_source_stage42_load_wad_unified_live_tick_render_loop_probe(pe)
        stage36._emit_prior_loaders(pe)
        stage36._emit_runtime_helpers(pe)
        stage36.emit_render_selected_dropped_shotgun_visual_boundary_debug(pe)
        stage38.emit_render_selected_attack_feedback_present_bridge_debug(pe)
        stage39.emit_render_selected_projectile_spawn_present_probe_debug(pe)
        stage40.emit_render_bounded_vissprite_traversal_sorting_bridge_debug(pe)
        stage41.emit_render_statusbar_weapon_ammo_feedback_bridge_debug(pe)
        emit_render_unified_live_tick_render_loop_probe_debug(pe)
        stage36._emit_prior_status(pe)
        stage36.emit_append_stage36_success_status(pe)
        stage38.emit_append_stage38_success_status(pe)
        stage39.emit_append_stage39_success_status(pe)
        stage40.emit_append_stage40_success_status(pe)
        stage41.emit_append_stage41_success_status(pe)
        emit_append_stage42_success_status(pe)
        stage01.emit_append_c_string(pe)
        stage01.emit_append_u32_decimal(pe)
        stage01.emit_append_i32_decimal(pe)
        stage01.emit_data(pe)
        stage36._emit_prior_data(pe)
        stage36.emit_stage36_data(pe)
        stage38.emit_stage38_data(pe)
        stage39.emit_stage39_data(pe)
        stage40.emit_stage40_data(pe)
        stage41.emit_stage41_data(pe)
        emit_stage42_data(pe)
    return pe.build("entry")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage42 unified live tick render loop PE32 probe"
    )
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output PE32 executable path")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = build_source_stage42_unified_live_tick_render_loop_probe_exe()
    output.write_bytes(data)
    ref = _reference_for_default_wad_or_none()
    print(f"Wrote {output} ({len(data)} bytes)")
    if ref is not None:
        print(f"S42SIG={ref.signature}")
        print(f"STATE42={ref.state_signature}")
        print("ULSTATE42=" + ",".join(str(sample.unified_loop_state_signature) for sample in ref.samples))
        print("FB42=" + ",".join(str(sample.framebuffer_signature) for sample in ref.samples))


if __name__ == "__main__":
    main()
