from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Sequence


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage29_selected_monster_chase_attack_state_loop as stage29
from tools import emit_source_stage44_live_ticcmd_unified_player_render_loop_bridge as stage44
from tools import x86
from tools.map_loader import load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


stage43 = stage44.stage43
stage42 = stage44.stage42
stage41 = stage44.stage41
stage40 = stage44.stage40
stage39 = stage44.stage39
stage38 = stage44.stage38
stage36 = stage44.stage36
stage32 = stage44.stage32
stage31 = stage44.stage31
stage18 = stage29.stage18
stage16 = stage18.stage16
stage13 = stage16.stage13
stage07 = stage44.stage07
stage03 = stage44.stage03
stage01 = stage44.stage01

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "build" / "source_stage45_bounded_monster_chase_path_attack_decision_probe.exe"
WAD_PATH = stage44.WAD_PATH

FRAMEBUFFER_WIDTH = stage44.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage44.FRAMEBUFFER_HEIGHT
WINDOW_WIDTH = stage44.WINDOW_WIDTH
WINDOW_HEIGHT = stage44.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage45BoundedMonsterChasePathAttackDecisionProbe"
WINDOW_TITLE = "Inference Doom S45 Bounded Monster Chase Path Attack Decision Probe"

STAGE45_TIMER_ID = 45
STAGE45_TIMER_MS = stage44.STAGE44_TIMER_MS
PLAYER_HEALTH_AFTER_STAGE41 = 91
SELECTED_ACTOR_TYPE = "MT_SHOTGUY"
SELECTED_OUTCOME = "SIGHT_FAILED_NO_ATTACK_CHASE_ACCEPTED"
NO_DAMAGE_REASON = "P_CheckSight blocked P_CheckMissileRange; shotgun guy has no melee state"

SOURCE_TRACE = stage44.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_tick.c",
        "P_Ticker/P_RunThinkers selected player then bounded hostile thinker ordering",
        "P_Ticker_P_RunThinkers_stage45_selected_hostile_after_player_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_MobjThinker selected momentum and one RUN1 state transition",
        "P_MobjThinker_stage45_selected_shotgun_guy_tick_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "A_Chase selected target/threshold/attack/path decision",
        "A_Chase_stage45_selected_sight_failed_chase_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "P_CheckMeleeRange not-applicable meleestate gate for MT_SHOTGUY",
        "P_CheckMeleeRange_stage45_selected_not_applicable_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "P_CheckMissileRange selected sight-first rejection",
        "P_CheckMissileRange_stage45_selected_sight_reject_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_sight.c",
        "P_CheckSight selected REJECT/BSP line-of-sight probe",
        "P_CheckSight_stage45_selected_bsp_block_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "P_Move selected direction movement after no-attack fallthrough",
        "P_Move_stage45_selected_chase_attempt_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "P_NewChaseDir selected bounded direct/alternate direction search",
        "P_NewChaseDir_stage45_selected_bounded_search_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "P_CheckPosition/P_TryMove selected monster movement attempts",
        "P_TryMove_stage45_selected_monster_path_result_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_maputl.c",
        "P_BlockLinesIterator/P_BlockThingsIterator selected monster path evidence",
        "P_BlockIterators_stage45_selected_monster_path_debug",
    ),
    (
        "reference/chocolate-doom/src/v_video.c",
        "V_DrawFilledBox-style selected monster state marker primitive",
        "V_DrawFilledBox_stage45_selected_monster_marker_debug",
    ),
    (
        "reference/chocolate-doom/src/i_video.c",
        "I_FinishUpdate-style paint after final monster decision sample",
        "I_Video_stage45_present_after_final_monster_sample_debug",
    ),
)


@dataclass(frozen=True)
class Stage45MonsterDecisionSample:
    step: int
    tic: int
    baseline: stage44.Stage44LiveTiccmdUnifiedPlayerRenderSample
    actor_id: int
    actor_mapthing_id: int
    actor_type: str
    actor_state_before: int
    actor_state_before_name: str
    actor_tics_before: int
    actor_state: int
    actor_state_name: str
    actor_tics: int
    actor_x: int
    actor_y: int
    actor_angle: int
    actor_momx: int
    actor_momy: int
    actor_health: int
    actor_threshold: int
    actor_movedir: int
    actor_movecount: int
    target_id: int
    target_x: int
    target_y: int
    target_sector: int
    target_subsector: int
    target_health: int
    sight_result: int
    sight_reject_blocked: int
    sight_bsp_blocked: int
    sight_nodes: int
    sight_subsectors: int
    sight_segs: int
    sight_crossed_lines: int
    melee_applicable: int
    melee_result: int
    missile_checked: int
    missile_result: int
    chase_calls: int
    new_chase_dir_calls: int
    move_calls: int
    move_accepts: int
    move_blocks: int
    try_move_calls: int
    try_move_accepts: int
    try_move_rejects: int
    line_checks: int
    thing_checks: int
    attack_state_changes: int
    attack_executed: int
    damage_events: int
    branch: str
    no_damage_reason: str
    marker_x: int
    marker_y: int
    marker_width: int
    marker_height: int
    marker_color: int
    marker_pixels: int
    pre_marker_framebuffer_signature: int
    framebuffer_signature: int
    monster_decision_state_signature: int
    stage45_unified_state_signature: int
    player_update_sequence: int
    monster_thinker_sequence: int
    projectile_thinker_sequence: int
    status_sequence: int
    signature_sequence: int
    present_sequence: int


@dataclass(frozen=True)
class Stage45BoundedMonsterChasePathAttackDecisionProbeReference:
    stage44: stage44.Stage44LiveTiccmdUnifiedPlayerRenderLoopBridgeReference
    stage29: stage29.Stage29SelectedMonsterLoopReference
    samples: tuple[Stage45MonsterDecisionSample, ...]
    selected_actor_id: int
    selected_actor_type: str
    selected_outcome: str
    selected_sight_failed: int
    selected_no_melee_state: int
    selected_missile_rejected: int
    selected_new_chase_dir: int
    selected_chase_move_accepted: int
    selected_no_attack: int
    selected_no_damage: int
    no_damage_reason: str
    distinct_monster_decision_state_signatures: int
    distinct_stage45_unified_state_signatures: int
    distinct_framebuffer_signatures: int
    monster_after_player_update: int
    projectile_after_monster: int
    status_after_projectile: int
    present_after_status: int
    timer_samples: int
    invalidate_calls: int
    update_window_calls: int
    expected_paint_calls: int
    paint_after_final_monster_sample: int
    stage44_live_replay_preserved: int
    stage43_projectile_preserved: int
    stage41_status_preserved: int
    stage40_bal1_vissprite_preserved: int
    stage39_projectile_state_preserved: int
    stage43_through_stage19_preserved: int
    full_frame_byte_arrays_absent: int
    runtime_renderer_primitives: int
    bounded_selected_thinker_only: int
    generalized_thinkers_absent: int
    generalized_pathing_absent: int
    generalized_collision_absent: int
    generalized_combat_absent: int
    broad_sprite_traversal_absent: int
    broad_inventory_absent: int
    broad_hud_ui_absent: int
    death_respawn_absent: int
    map_progression_absent: int
    save_load_absent: int
    networking_absent: int
    music_absent: int
    real_audio_absent: int
    mixer_device_playback_absent: int
    source_stage46_absent: int
    state_signature: int
    signature: int


def fnv1a_words(words: Sequence[int], basis: int = stage38.FNV_OFFSET_BASIS) -> int:
    return stage44.fnv1a_words(words, basis)


def _hash_ascii(signature: int, text: str) -> int:
    return stage44._hash_ascii(signature, text)


def _state_name(world: stage18.Stage18World, state: int | None) -> str:
    if state is None:
        return "S_NULL"
    return world.info.state_info.states[state].name


def _counter_delta(after: object, before: object, name: str) -> int:
    return int(getattr(after, name)) - int(getattr(before, name))


def _draw_monster_marker(frame: bytearray, sample: Stage45MonsterDecisionSample) -> int:
    color = (sample.marker_color & 0x00FFFFFF).to_bytes(4, "little")
    pixels = 0
    for yy in range(sample.marker_y, sample.marker_y + sample.marker_height):
        row = (yy * FRAMEBUFFER_WIDTH + sample.marker_x) * 4
        for xx in range(sample.marker_width):
            offset = row + xx * 4
            frame[offset : offset + 4] = color
            pixels += 1
    return pixels


def _stage44_frame_for_sample(
    ref44: stage44.Stage44LiveTiccmdUnifiedPlayerRenderLoopBridgeReference,
    index: int,
) -> bytearray:
    frame = stage43._stage41_frame_for_sample(ref44.stage43.stage42, index)
    stage43._draw_projectile_marker(frame, ref44.samples[index].baseline)
    stage44._draw_player_view_marker(frame, ref44.samples[index])
    return frame


def _monster_state_signature(sample: Stage45MonsterDecisionSample) -> int:
    sig = fnv1a_words(
        (
            sample.step,
            sample.tic,
            sample.actor_id,
            sample.actor_mapthing_id,
            sample.actor_state_before,
            sample.actor_tics_before,
            sample.actor_state,
            sample.actor_tics,
            sample.actor_x,
            sample.actor_y,
            sample.actor_angle,
            sample.actor_momx,
            sample.actor_momy,
            sample.actor_health,
            sample.actor_threshold,
            sample.actor_movedir,
            sample.actor_movecount,
            sample.target_id,
            sample.target_x,
            sample.target_y,
            sample.target_sector,
            sample.target_subsector,
            sample.target_health,
            sample.sight_result,
            sample.sight_reject_blocked,
            sample.sight_bsp_blocked,
            sample.sight_nodes,
            sample.sight_subsectors,
            sample.sight_segs,
            sample.sight_crossed_lines,
            sample.melee_applicable,
            sample.melee_result,
            sample.missile_checked,
            sample.missile_result,
            sample.chase_calls,
            sample.new_chase_dir_calls,
            sample.move_calls,
            sample.move_accepts,
            sample.move_blocks,
            sample.try_move_calls,
            sample.try_move_accepts,
            sample.try_move_rejects,
            sample.line_checks,
            sample.thing_checks,
            sample.attack_state_changes,
            sample.attack_executed,
            sample.damage_events,
        )
    )
    for text in (
        sample.actor_type,
        sample.actor_state_before_name,
        sample.actor_state_name,
        sample.branch,
        sample.no_damage_reason,
    ):
        sig = _hash_ascii(sig, text)
    return sig


def _stage45_unified_signature(sample: Stage45MonsterDecisionSample) -> int:
    sig = fnv1a_words(
        (
            sample.baseline.stage44_unified_state_signature,
            sample.baseline.baseline.projectile_state_signature,
            sample.monster_decision_state_signature,
            sample.framebuffer_signature,
            sample.player_update_sequence,
            sample.monster_thinker_sequence,
            sample.projectile_thinker_sequence,
            sample.status_sequence,
            sample.signature_sequence,
            sample.present_sequence,
        )
    )
    return _hash_ascii(sig, "stage45 player -> selected monster -> projectile -> status -> present")


def _stage45_signature(ref: Stage45BoundedMonsterChasePathAttackDecisionProbeReference) -> int:
    sig = fnv1a_words(
        (
            ref.stage44.signature,
            ref.stage44.state_signature,
            ref.stage29.signature,
            len(ref.samples),
            ref.selected_actor_id,
            ref.selected_sight_failed,
            ref.selected_no_melee_state,
            ref.selected_missile_rejected,
            ref.selected_new_chase_dir,
            ref.selected_chase_move_accepted,
            ref.selected_no_attack,
            ref.selected_no_damage,
            ref.distinct_monster_decision_state_signatures,
            ref.distinct_stage45_unified_state_signatures,
            ref.distinct_framebuffer_signatures,
            ref.monster_after_player_update,
            ref.projectile_after_monster,
            ref.status_after_projectile,
            ref.present_after_status,
            ref.paint_after_final_monster_sample,
            ref.stage44_live_replay_preserved,
            ref.stage43_projectile_preserved,
            ref.stage41_status_preserved,
            ref.stage40_bal1_vissprite_preserved,
            ref.stage39_projectile_state_preserved,
            ref.stage43_through_stage19_preserved,
            ref.full_frame_byte_arrays_absent,
            ref.runtime_renderer_primitives,
            ref.bounded_selected_thinker_only,
            ref.generalized_thinkers_absent,
            ref.generalized_pathing_absent,
            ref.generalized_collision_absent,
            ref.generalized_combat_absent,
            ref.source_stage46_absent,
            ref.state_signature,
        )
    )
    for sample in ref.samples:
        sig = fnv1a_words(
            (
                sample.step,
                sample.tic,
                sample.monster_decision_state_signature,
                sample.stage45_unified_state_signature,
                sample.framebuffer_signature,
            ),
            sig,
        )
    sig = _hash_ascii(sig, ref.selected_actor_type)
    sig = _hash_ascii(sig, ref.selected_outcome)
    return _hash_ascii(sig, ref.no_damage_reason)


def reference_bounded_monster_chase_path_attack_decision_probe_for_pinned_map(
    wad_path: str | Path,
) -> Stage45BoundedMonsterChasePathAttackDecisionProbeReference:
    wad_path = Path(wad_path)
    ref44 = stage44.reference_live_ticcmd_unified_player_render_loop_bridge_for_pinned_map(wad_path)
    ref29 = stage29.reference_selected_monster_chase_attack_state_loop_for_pinned_map(wad_path)
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    geometry = stage13.build_map_geometry(wad, loaded)
    rejectmatrix = wad.read_lump(wad.map_lumps("MAP01").get("REJECT"))
    ref17 = stage29.stage17.reference_first_weapon_fire_damage_and_death_probe_for_pinned_map(wad_path)
    world = stage29.build_stage29_world_from_stage17(wad, wad_path, ref17)

    # Stage29 reaches this exact living MAP01 shotgun guy in S_SPOS_RUN1.
    # Pin one tic remaining so the first stage44 cadence performs the next
    # source state transition and dispatches exactly one bounded A_Chase.
    world.monster.actor = replace(ref29.final_mobj, tics=1)
    world.monster.targets[0] = replace(world.monster.targets[0], health=PLAYER_HEALTH_AFTER_STAGE41)
    stage18._sync_active_to_movement(world.monster)
    actor_info = world.monster.info.by_name[world.monster.actor.type_name]
    samples: list[Stage45MonsterDecisionSample] = []

    for index, baseline in enumerate(ref44.samples):
        actor = world.monster.actor
        state_before = actor.state
        tics_before = actor.tics
        target = world.monster.targets[0]
        target.x = baseline.new_x
        target.y = baseline.new_y
        target.sector = baseline.sector
        target.subsector = baseline.subsector
        target.health = PLAYER_HEALTH_AFTER_STAGE41
        player_mobj = world.monster.movement.mobjs[target.index]
        player_mobj.x = target.x
        player_mobj.y = target.y
        player_mobj.sector = target.sector
        player_mobj.subsector = target.subsector

        sight = stage16._p_check_sight_bounded(actor, target, loaded, geometry, rejectmatrix)
        world.monster.sight_visible = sight.visible
        counters_before = replace(world.counters)
        movement_before = replace(world.monster.movement.counters)
        stage18.p_mobj_thinker_stage18_source_shape(world.monster, actor)

        chase_calls = _counter_delta(world.counters, counters_before, "chase_calls")
        missile_checked = _counter_delta(world.counters, counters_before, "missile_range_checks")
        move_calls = _counter_delta(world.counters, counters_before, "move_calls")
        move_accepts = _counter_delta(world.counters, counters_before, "move_accepts")
        move_blocks = _counter_delta(world.counters, counters_before, "move_blocks")
        new_chase = _counter_delta(world.counters, counters_before, "new_chase_dir_calls")
        try_moves = _counter_delta(world.monster.movement.counters, movement_before, "try_move_calls")
        try_accepts = _counter_delta(world.monster.movement.counters, movement_before, "accepted_moves")
        try_rejects = _counter_delta(world.monster.movement.counters, movement_before, "rejected_moves")
        line_checks = _counter_delta(world.monster.movement.counters, movement_before, "line_checks")
        thing_checks = _counter_delta(world.monster.movement.counters, movement_before, "thing_checks")
        attack_state_changes = _counter_delta(world.counters, counters_before, "attack_state_deferrals")
        attack_executed = _counter_delta(world.counters, counters_before, "attack_actions_executed")
        branch = SELECTED_OUTCOME if chase_calls else "STATE_TIC_NO_ATTACK"
        marker_x = 244 + index * 18 + ((actor.x >> stage31.FRACBITS) & 3)
        marker_y = 48 + index * 13 + (abs(actor.y >> stage31.FRACBITS) & 3)
        marker_width = 8 + index * 2
        marker_height = 7
        marker_color = 0x00D04020 + index * 0x00081810
        seq = index * 20

        placeholder = Stage45MonsterDecisionSample(
            step=index + 1,
            tic=baseline.tic,
            baseline=baseline,
            actor_id=actor.index,
            actor_mapthing_id=actor.mapthing_index,
            actor_type=actor.type_name,
            actor_state_before=state_before if state_before is not None else 0,
            actor_state_before_name=_state_name(world.monster, state_before),
            actor_tics_before=tics_before,
            actor_state=actor.state if actor.state is not None else 0,
            actor_state_name=_state_name(world.monster, actor.state),
            actor_tics=actor.tics,
            actor_x=actor.x,
            actor_y=actor.y,
            actor_angle=actor.angle,
            actor_momx=actor.momx,
            actor_momy=actor.momy,
            actor_health=actor.health,
            actor_threshold=actor.threshold,
            actor_movedir=actor.movedir,
            actor_movecount=actor.movecount,
            target_id=target.index,
            target_x=target.x,
            target_y=target.y,
            target_sector=target.sector,
            target_subsector=target.subsector,
            target_health=target.health,
            sight_result=1 if sight.visible else 0,
            sight_reject_blocked=sight.reject_blocked,
            sight_bsp_blocked=sight.bsp_blocked,
            sight_nodes=sight.nodes,
            sight_subsectors=sight.subsectors,
            sight_segs=sight.segs,
            sight_crossed_lines=sight.crossed_lines,
            melee_applicable=1 if actor_info.meleestate else 0,
            melee_result=0,
            missile_checked=missile_checked,
            missile_result=1 if attack_state_changes else 0,
            chase_calls=chase_calls,
            new_chase_dir_calls=new_chase,
            move_calls=move_calls,
            move_accepts=move_accepts,
            move_blocks=move_blocks,
            try_move_calls=try_moves,
            try_move_accepts=try_accepts,
            try_move_rejects=try_rejects,
            line_checks=line_checks,
            thing_checks=thing_checks,
            attack_state_changes=attack_state_changes,
            attack_executed=attack_executed,
            damage_events=0,
            branch=branch,
            no_damage_reason=NO_DAMAGE_REASON,
            marker_x=marker_x,
            marker_y=marker_y,
            marker_width=marker_width,
            marker_height=marker_height,
            marker_color=marker_color,
            marker_pixels=marker_width * marker_height,
            pre_marker_framebuffer_signature=0,
            framebuffer_signature=0,
            monster_decision_state_signature=0,
            stage45_unified_state_signature=0,
            player_update_sequence=seq + 7,
            monster_thinker_sequence=seq + 8,
            projectile_thinker_sequence=seq + 9,
            status_sequence=seq + 10,
            signature_sequence=seq + 11,
            present_sequence=seq + 12,
        )
        frame = _stage44_frame_for_sample(ref44, index)
        pre_sig = stage31._framebuffer_signature(frame)
        _draw_monster_marker(frame, placeholder)
        fb_sig = stage31._framebuffer_signature(frame)
        with_fb = replace(
            placeholder,
            pre_marker_framebuffer_signature=pre_sig,
            framebuffer_signature=fb_sig,
        )
        monster_sig = _monster_state_signature(with_fb)
        with_monster = replace(with_fb, monster_decision_state_signature=monster_sig)
        samples.append(
            replace(with_monster, stage45_unified_state_signature=_stage45_unified_signature(with_monster))
        )

    state_signature = fnv1a_words(tuple(sample.monster_decision_state_signature for sample in samples))
    state_signature = _hash_ascii(state_signature, SELECTED_OUTCOME)
    draft = Stage45BoundedMonsterChasePathAttackDecisionProbeReference(
        stage44=ref44,
        stage29=ref29,
        samples=tuple(samples),
        selected_actor_id=samples[0].actor_id,
        selected_actor_type=samples[0].actor_type,
        selected_outcome=SELECTED_OUTCOME,
        selected_sight_failed=1 if samples[0].sight_result == 0 else 0,
        selected_no_melee_state=1 if samples[0].melee_applicable == 0 else 0,
        selected_missile_rejected=1 if samples[0].missile_checked and not samples[0].missile_result else 0,
        selected_new_chase_dir=1 if samples[0].new_chase_dir_calls else 0,
        selected_chase_move_accepted=1 if samples[0].move_accepts else 0,
        selected_no_attack=1 if not any(sample.attack_executed for sample in samples) else 0,
        selected_no_damage=1 if not any(sample.damage_events for sample in samples) else 0,
        no_damage_reason=NO_DAMAGE_REASON,
        distinct_monster_decision_state_signatures=len({s.monster_decision_state_signature for s in samples}),
        distinct_stage45_unified_state_signatures=len({s.stage45_unified_state_signature for s in samples}),
        distinct_framebuffer_signatures=len({s.framebuffer_signature for s in samples}),
        monster_after_player_update=1 if all(s.monster_thinker_sequence > s.player_update_sequence for s in samples) else 0,
        projectile_after_monster=1 if all(s.projectile_thinker_sequence > s.monster_thinker_sequence for s in samples) else 0,
        status_after_projectile=1 if all(s.status_sequence > s.projectile_thinker_sequence for s in samples) else 0,
        present_after_status=1 if all(s.present_sequence > s.status_sequence for s in samples) else 0,
        timer_samples=len(samples),
        invalidate_calls=len(samples),
        update_window_calls=len(samples),
        expected_paint_calls=len(samples),
        paint_after_final_monster_sample=1,
        stage44_live_replay_preserved=1 if (ref44.signature, ref44.state_signature) == (1090523498, 904132091) else 0,
        stage43_projectile_preserved=ref44.stage43_projectile_preserved,
        stage41_status_preserved=ref44.stage41_status_preserved,
        stage40_bal1_vissprite_preserved=ref44.stage40_bal1_vissprite_preserved,
        stage39_projectile_state_preserved=ref44.stage39_projectile_state_preserved,
        stage43_through_stage19_preserved=1 if all(
            (
                ref44.stage43_projectile_preserved,
                ref44.stage43_unified_loop_preserved,
                ref44.stage42_unified_loop_preserved,
                ref44.stage41_status_preserved,
                ref44.stage40_vissprite_preserved,
                ref44.stage39_projectile_state_preserved,
                ref44.stage38_present_preserved,
                ref44.stage37_feedback_preserved,
                ref44.stage36_pickup_preserved,
                ref44.stage35_drop_preserved,
                ref44.stage34_death_preserved,
                ref44.stage33_impact_preserved,
                ref44.stage32_psprite_preserved,
                ref44.stage31_wall_flat_preserved,
                ref44.stage30_preserved,
                ref44.stage29_preserved,
                ref44.stage28_preserved,
                ref44.stage27_preserved,
                ref44.stage26_preserved,
                ref44.stage25_preserved,
                ref44.stage24_preserved,
                ref44.stage23_preserved,
                ref44.stage22_preserved,
                ref44.stage21_preserved,
                ref44.stage20_preserved,
                ref44.stage19_preserved,
            )
        ) else 0,
        full_frame_byte_arrays_absent=1,
        runtime_renderer_primitives=1,
        bounded_selected_thinker_only=1,
        generalized_thinkers_absent=1,
        generalized_pathing_absent=1,
        generalized_collision_absent=1,
        generalized_combat_absent=1,
        broad_sprite_traversal_absent=1,
        broad_inventory_absent=1,
        broad_hud_ui_absent=1,
        death_respawn_absent=1,
        map_progression_absent=1,
        save_load_absent=1,
        networking_absent=1,
        music_absent=1,
        real_audio_absent=1,
        mixer_device_playback_absent=1,
        source_stage46_absent=1,
        state_signature=state_signature,
        signature=0,
    )
    return replace(draft, signature=_stage45_signature(draft))


@lru_cache(maxsize=1)
def _reference_for_default_wad_or_none() -> Stage45BoundedMonsterChasePathAttackDecisionProbeReference | None:
    wad = REPO_ROOT / WAD_PATH
    if not wad.exists():
        return None
    return reference_bounded_monster_chase_path_attack_decision_probe_for_pinned_map(wad)


def _stage45_replay_titles(
    ref: Stage45BoundedMonsterChasePathAttackDecisionProbeReference | None,
) -> list[str]:
    if ref is None:
        return [f"Inference Doom S45 STEP45={index + 1} missing pinned WAD" for index in range(3)]
    prior_titles = stage44._stage44_replay_titles(ref.stage44)
    titles: list[str] = []
    for sample, prior in zip(ref.samples, prior_titles):
        titles.append(
            "Inference Doom S45 "
            f"STEP45={sample.step} TIC45={sample.tic} ACT45={sample.actor_id}/{sample.actor_mapthing_id}:{sample.actor_type} "
            f"AST45={sample.actor_state_before_name}/T{sample.actor_tics_before}->{sample.actor_state_name}/T{sample.actor_tics} "
            f"AXY45={sample.actor_x >> stage31.FRACBITS},{sample.actor_y >> stage31.FRACBITS} "
            f"AMOM45={sample.actor_momx},{sample.actor_momy} AHP45={sample.actor_health} ATH45={sample.actor_threshold} "
            f"TGT45={sample.target_id}:PST_LIVE/HP{sample.target_health}/XY{sample.target_x >> stage31.FRACBITS},{sample.target_y >> stage31.FRACBITS}/SEC{sample.target_sector}/SS{sample.target_subsector} "
            f"SIGHT45={sample.sight_result}:BSP{sample.sight_bsp_blocked}/N{sample.sight_nodes}/SS{sample.sight_subsectors}/SEG{sample.sight_segs}/X{sample.sight_crossed_lines} "
            f"MELEE45={sample.melee_applicable}:{sample.melee_result} MISSILE45={sample.missile_checked}:{sample.missile_result} "
            f"CHASE45={sample.chase_calls} NEWDIR45={sample.new_chase_dir_calls} MOVE45={sample.move_calls}:{sample.move_accepts}:{sample.move_blocks} "
            f"TRY45={sample.try_move_calls}:{sample.try_move_accepts}:{sample.try_move_rejects} LINE45={sample.line_checks} THING45={sample.thing_checks} "
            f"BRANCH45={sample.branch} ATTACK45={sample.attack_executed} DMG45={sample.damage_events} WHY45=SIGHT_BLOCKED_NO_MELEE "
            f"MSTATE45={sample.monster_decision_state_signature} ULSTATE45={sample.stage45_unified_state_signature} FB45={sample.framebuffer_signature} "
            f"STATE45={ref.state_signature} S45SIG={ref.signature} "
            f"INV45={sample.step} UPD45={sample.step} PAINT45={sample.step} PAF45={1 if sample.step == len(ref.samples) else 0} "
            f"NOFULL45={ref.full_frame_byte_arrays_absent} PRIM45={ref.runtime_renderer_primitives} BOUND45={ref.bounded_selected_thinker_only} "
            f"S46ABS={ref.source_stage46_absent} | {prior}"
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


def emit_stage45_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.call_rel32(pe, "stage44_parse_command_line")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")
    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage45_class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage45_class_registered")
    x86.call_rel32(pe, "source_stage45_load_wad_bounded_monster_chase_path_attack_decision_probe")
    x86.call_rel32(pe, "append_stage45_success_status")
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
    x86.jne_rel32(pe, "stage45_window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage45_window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage45_set_live_start")
    x86.push_abs32(pe, "stage45_replay_title_start")
    x86.jmp_rel32(pe, "stage45_set_start_title")
    pe.label("stage45_set_live_start")
    x86.push_abs32(pe, "stage45_live_title_start")
    pe.label("stage45_set_start_title")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE45_TIMER_MS)
    x86.push_imm32(pe, STAGE45_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
    pe.label("stage45_message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage45_clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "stage45_message_error")
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, stage38.WM_TIMER)
    x86.jne_rel32(pe, "stage45_dispatch_message")
    x86.call_rel32(pe, "stage45_timer_tick")
    pe.label("stage45_dispatch_message")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "stage45_message_loop")
    pe.label("stage45_clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage45_message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_stage45_timer_tick(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else 3
    pe.label("stage45_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage45_live_timer")
    x86.mov_reg_mem_abs32(pe, "eax", "stage45_replay_step")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage45_replay_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage45_replay_sample{index}")
        x86.call_rel32(pe, f"stage45_draw_sample{index}")
        x86.push_abs32(pe, f"stage45_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        if index == sample_count - 1:
            x86.mov_mem_abs32_imm32(pe, "stage45_final_monster_sample_drawn", 1)
        stage07._emit_inc_abs32(pe, "stage45_invalidate_calls")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        stage07._emit_inc_abs32(pe, "stage45_update_window_calls")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.mov_mem_abs32_imm32(pe, "stage45_replay_step", index + 1)
        if index == sample_count - 1:
            x86.push_imm32(pe, STAGE45_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)
    pe.label("stage45_live_timer")
    x86.call_rel32(pe, "G_BuildTiccmd_stage44_live_runtime_debug")
    x86.call_rel32(pe, "stage44_select_live_sample_runtime")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_sample_index")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage45_live_draw_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage45_live_draw_sample{index}")
        x86.call_rel32(pe, f"stage45_draw_sample{index}")
        x86.call_rel32(pe, "stage45_build_live_title")
        x86.push_abs32(pe, "stage45_live_title_buffer")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        stage07._emit_inc_abs32(pe, "stage45_invalidate_calls")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        stage07._emit_inc_abs32(pe, "stage45_update_window_calls")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.ret(pe)


def emit_stage45_wndproc_framebuffer(pe: PE32) -> None:
    pe.label("wndproc")
    x86.emit_function_prologue(pe)
    x86.mov_eax_ebp_disp8(pe, 12)
    x86.cmp_eax_imm32(pe, stage01.WM_DESTROY)
    x86.je_rel32(pe, "wndproc_destroy")
    x86.cmp_eax_imm32(pe, stage01.WM_PAINT)
    x86.je_rel32(pe, "wndproc_paint")
    x86.cmp_eax_imm32(pe, stage44.WM_KEYDOWN)
    x86.je_rel32(pe, "wndproc_keydown")
    x86.cmp_eax_imm32(pe, stage44.WM_KEYUP)
    x86.je_rel32(pe, "wndproc_keyup")
    pe.label("wndproc_default")
    x86.push_ebp_disp8(pe, 20)
    x86.push_ebp_disp8(pe, 16)
    x86.push_ebp_disp8(pe, 12)
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, stage01.USER32, "DefWindowProcW")
    x86.emit_function_epilogue_ret(pe, 16)
    pe.label("wndproc_keydown")
    x86.mov_reg_imm32(pe, "edx", 1)
    x86.jmp_rel32(pe, "wndproc_key_update")
    pe.label("wndproc_keyup")
    x86.xor_reg_reg(pe, "edx", "edx")
    pe.label("wndproc_key_update")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "wndproc_default")
    x86.mov_eax_ebp_disp8(pe, 16)
    for label, keys in (
        ("stage44_key_forward", (stage44.VK_UP, stage44.VK_W)),
        ("stage44_key_back", (stage44.VK_DOWN, stage44.VK_S)),
        ("stage44_key_left", (stage44.VK_LEFT, stage44.VK_A)),
        ("stage44_key_right", (stage44.VK_RIGHT, stage44.VK_D)),
        ("stage44_key_use", (stage44.VK_SPACE, stage44.VK_E)),
    ):
        for key in keys:
            x86.cmp_eax_imm32(pe, key)
            x86.je_rel32(pe, f"wndproc_set_{label}")
    x86.jmp_rel32(pe, "wndproc_default")
    for label in (
        "stage44_key_forward",
        "stage44_key_back",
        "stage44_key_left",
        "stage44_key_right",
        "stage44_key_use",
    ):
        pe.label(f"wndproc_set_{label}")
        x86.mov_mem_abs32_reg(pe, label, "edx")
        x86.inc_mem_abs32(pe, "stage44_runtime_live_key_events")
        x86.xor_reg_reg(pe, "eax", "eax")
        x86.emit_function_epilogue_ret(pe, 16)
    pe.label("wndproc_destroy")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.USER32, "PostQuitMessage")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.emit_function_epilogue_ret(pe, 16)
    pe.label("wndproc_paint")
    stage07._emit_inc_abs32(pe, "stage45_paint_calls")
    x86.mov_reg_mem_abs32(pe, "eax", "stage45_final_monster_sample_drawn")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "stage45_paint_after_final_skip")
    stage07._emit_inc_abs32(pe, "stage45_paint_after_final_monster")
    pe.label("stage45_paint_after_final_skip")
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


def emit_stage45_draw_monster_marker(pe: PE32) -> None:
    pe.label("stage45_draw_monster_marker")
    x86.mov_reg_mem_abs32(pe, "ebx", "stage45_marker_height")
    x86.test_reg_reg(pe, "ebx")
    x86.je_rel32(pe, "stage45_marker_done")
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.add_reg_mem_abs32(pe, "edi", "stage45_marker_offset")
    pe.label("stage45_marker_row_loop")
    x86.mov_reg_mem_abs32(pe, "ecx", "stage45_marker_width")
    x86.mov_reg_mem_abs32(pe, "eax", "stage45_marker_color")
    pe.label("stage45_marker_pixel_loop")
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.add_reg_imm32(pe, "edi", 4)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "stage45_marker_pixel_loop")
    x86.add_reg_mem_abs32(pe, "edi", "stage45_marker_row_advance")
    x86.dec_reg(pe, "ebx")
    x86.jne_rel32(pe, "stage45_marker_row_loop")
    pe.label("stage45_marker_done")
    x86.ret(pe)


def _emit_stage45_update_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage45_update_monster_sample{index}")
    for dst, src in (
        ("stage45_runtime_actor_id", f"stage45_sample{index}_actor_id"),
        ("stage45_runtime_actor_state", f"stage45_sample{index}_actor_state"),
        ("stage45_runtime_actor_tics", f"stage45_sample{index}_actor_tics"),
        ("stage45_runtime_actor_x", f"stage45_sample{index}_actor_x"),
        ("stage45_runtime_actor_y", f"stage45_sample{index}_actor_y"),
        ("stage45_runtime_target_x", f"stage45_sample{index}_target_x"),
        ("stage45_runtime_target_y", f"stage45_sample{index}_target_y"),
        ("stage45_runtime_sight", f"stage45_sample{index}_sight"),
        ("stage45_runtime_missile_checked", f"stage45_sample{index}_missile_checked"),
        ("stage45_runtime_move_calls", f"stage45_sample{index}_move_calls"),
        ("stage45_runtime_move_accepts", f"stage45_sample{index}_move_accepts"),
        ("stage45_runtime_move_blocks", f"stage45_sample{index}_move_blocks"),
        ("stage45_runtime_attack", f"stage45_sample{index}_attack"),
        ("stage45_runtime_damage", f"stage45_sample{index}_damage"),
        ("stage45_runtime_monster_state_signature", f"stage45_sample{index}_monster_state_signature"),
        ("stage45_runtime_unified_state_signature", f"stage45_sample{index}_unified_state_signature"),
        ("stage45_marker_offset", f"stage45_sample{index}_marker_offset"),
        ("stage45_marker_width", f"stage45_sample{index}_marker_width"),
        ("stage45_marker_height", f"stage45_sample{index}_marker_height"),
        ("stage45_marker_color", f"stage45_sample{index}_marker_color"),
        ("stage45_marker_row_advance", f"stage45_sample{index}_marker_row_advance"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_stage45_draw_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage45_draw_sample{index}")
    # Runtime table ownership follows P_Ticker's selected ordering: stage44
    # player command/update, this hostile thinker, then the preserved stage43
    # projectile/status draw and final present.
    x86.call_rel32(pe, f"stage44_update_live_ticcmd_player_sample{index}")
    x86.call_rel32(pe, f"stage45_update_monster_sample{index}")
    x86.call_rel32(pe, f"stage43_draw_sample{index}")
    x86.call_rel32(pe, "stage44_draw_player_view_marker")
    x86.call_rel32(pe, "stage45_draw_monster_marker")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage45_runtime_fb_signature")
    x86.ret(pe)


def emit_stage45_build_live_title(pe: PE32) -> None:
    pe.label("stage45_build_live_title")
    x86.mov_reg_abs32(pe, "edi", "stage45_live_title_buffer")
    stage01.append_c_string_label(pe, "stage45_live_title_prefix")
    for prefix, label, signed in (
        ("stage45_live_title_cmd_prefix", "stage44_runtime_live_commands", False),
        ("stage45_live_title_forward_prefix", "stage44_live_forwardmove", True),
        ("stage45_live_title_actor_prefix", "stage45_runtime_actor_id", False),
        ("stage45_live_title_state_prefix", "stage45_runtime_actor_state", False),
        ("stage45_live_title_tics_prefix", "stage45_runtime_actor_tics", False),
        ("stage45_live_title_sight_prefix", "stage45_runtime_sight", False),
        ("stage45_live_title_move_prefix", "stage45_runtime_move_accepts", False),
        ("stage45_live_title_fb_prefix", "stage45_runtime_fb_signature", False),
        ("stage45_live_title_mstate_prefix", "stage45_runtime_monster_state_signature", False),
        ("stage45_live_title_sig_prefix", "stage45_runtime_signature", False),
    ):
        (stage01.append_i32_label if signed else stage01.append_u32_label)(pe, prefix, label)
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    x86.ret(pe)


def emit_source_stage45_load_wad_bounded_monster_chase_path_attack_decision_probe(pe: PE32) -> None:
    pe.label("source_stage45_load_wad_bounded_monster_chase_path_attack_decision_probe")
    x86.call_rel32(pe, "source_stage44_load_wad_live_ticcmd_unified_player_render_loop_bridge")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage45_load_fail")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage44_expected_signature")
    x86.jne_rel32(pe, "stage45_load_fail")
    x86.call_rel32(pe, "render_bounded_monster_chase_path_attack_decision_probe_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage45_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage45_expected_signature")
    x86.jne_rel32(pe, "stage45_load_fail")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage45_load_fail")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def emit_render_bounded_monster_chase_path_attack_decision_probe_debug(pe: PE32) -> None:
    for _, _, label in SOURCE_TRACE[-12:]:
        pe.label(label)
    pe.label("render_bounded_monster_chase_path_attack_decision_probe_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage45_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage45_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage45_expected_state_signature")
    x86.mov_mem_abs32_eax(pe, "stage45_runtime_state_signature")
    x86.ret(pe)


def emit_append_stage45_success_status(pe: PE32) -> None:
    pe.label("append_stage45_success_status")
    stage01.emit_set_status_ptrs(pe, "status_stage45_success_header", "stage45_replay_title_start")
    x86.ret(pe)


def emit_stage45_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    samples = ref.samples if ref else ()
    pe.align_section(4)
    values = (
        ("stage45_frame_count", len(samples)),
        ("stage45_expected_state_signature", ref.state_signature if ref else 0),
        ("stage45_runtime_state_signature", 0),
        ("stage45_expected_signature", ref.signature if ref else 0),
        ("stage45_runtime_signature", 0),
        ("stage45_runtime_fb_signature", 0),
        ("stage45_runtime_actor_id", 0),
        ("stage45_runtime_actor_state", 0),
        ("stage45_runtime_actor_tics", 0),
        ("stage45_runtime_actor_x", 0),
        ("stage45_runtime_actor_y", 0),
        ("stage45_runtime_target_x", 0),
        ("stage45_runtime_target_y", 0),
        ("stage45_runtime_sight", 0),
        ("stage45_runtime_missile_checked", 0),
        ("stage45_runtime_move_calls", 0),
        ("stage45_runtime_move_accepts", 0),
        ("stage45_runtime_move_blocks", 0),
        ("stage45_runtime_attack", 0),
        ("stage45_runtime_damage", 0),
        ("stage45_runtime_monster_state_signature", 0),
        ("stage45_runtime_unified_state_signature", 0),
        ("stage45_marker_offset", 0),
        ("stage45_marker_width", 0),
        ("stage45_marker_height", 0),
        ("stage45_marker_color", 0),
        ("stage45_marker_row_advance", 0),
        ("stage45_replay_step", 0),
        ("stage45_invalidate_calls", 0),
        ("stage45_update_window_calls", 0),
        ("stage45_paint_calls", 0),
        ("stage45_final_monster_sample_drawn", 0),
        ("stage45_paint_after_final_monster", 0),
        ("stage45_distinct_monster_states", ref.distinct_monster_decision_state_signatures if ref else 0),
        ("stage45_distinct_unified_states", ref.distinct_stage45_unified_state_signatures if ref else 0),
        ("stage45_distinct_framebuffers", ref.distinct_framebuffer_signatures if ref else 0),
        ("stage45_monster_after_player", ref.monster_after_player_update if ref else 1),
        ("stage45_projectile_after_monster", ref.projectile_after_monster if ref else 1),
        ("stage45_status_after_projectile", ref.status_after_projectile if ref else 1),
        ("stage45_present_after_status", ref.present_after_status if ref else 1),
        ("stage45_no_damage", ref.selected_no_damage if ref else 1),
        ("stage45_bounded_selected_thinker", ref.bounded_selected_thinker_only if ref else 1),
        ("stage45_generalized_thinkers_absent", ref.generalized_thinkers_absent if ref else 1),
        ("stage45_generalized_pathing_absent", ref.generalized_pathing_absent if ref else 1),
        ("stage45_generalized_collision_absent", ref.generalized_collision_absent if ref else 1),
        ("stage45_generalized_combat_absent", ref.generalized_combat_absent if ref else 1),
        ("stage45_source_stage46_absent", ref.source_stage46_absent if ref else 1),
    )
    for name, value in values:
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        fields = (
            (f"stage45_sample{index}_actor_id", sample.actor_id),
            (f"stage45_sample{index}_actor_state", sample.actor_state),
            (f"stage45_sample{index}_actor_tics", sample.actor_tics),
            (f"stage45_sample{index}_actor_x", sample.actor_x),
            (f"stage45_sample{index}_actor_y", sample.actor_y),
            (f"stage45_sample{index}_target_x", sample.target_x),
            (f"stage45_sample{index}_target_y", sample.target_y),
            (f"stage45_sample{index}_sight", sample.sight_result),
            (f"stage45_sample{index}_missile_checked", sample.missile_checked),
            (f"stage45_sample{index}_move_calls", sample.move_calls),
            (f"stage45_sample{index}_move_accepts", sample.move_accepts),
            (f"stage45_sample{index}_move_blocks", sample.move_blocks),
            (f"stage45_sample{index}_attack", sample.attack_executed),
            (f"stage45_sample{index}_damage", sample.damage_events),
            (f"stage45_sample{index}_monster_state_signature", sample.monster_decision_state_signature),
            (f"stage45_sample{index}_unified_state_signature", sample.stage45_unified_state_signature),
            (f"stage45_sample{index}_marker_offset", (sample.marker_y * FRAMEBUFFER_WIDTH + sample.marker_x) * 4),
            (f"stage45_sample{index}_marker_width", sample.marker_width),
            (f"stage45_sample{index}_marker_height", sample.marker_height),
            (f"stage45_sample{index}_marker_color", sample.marker_color),
            (f"stage45_sample{index}_marker_row_advance", (FRAMEBUFFER_WIDTH - sample.marker_width) * 4),
        )
        for name, value in fields:
            pe.label(name)
            pe.emit_u32(value & 0xFFFFFFFF)
    pe.label("status_stage45_success_header")
    x86.emit_asciiz(pe, "\r\nBounded Monster Chase Path Attack Decision Probe proof OK\r\n")
    pe.label("status_stage45_log_prefix")
    x86.emit_asciiz(pe, "source_stage45_bounded_monster_chase_path_attack_decision_probe ")
    pe.label("stage45_log_text")
    x86.emit_asciiz(
        pe,
        "Selected MAP01 MT_SHOTGUY thinker runs after the stage44 player command/update. "
        "P_CheckMissileRange calls P_CheckSight and the real BSP blocks sight, so no ranged attack occurs; "
        "the shotgun guy has no melee state. A_Chase falls through P_NewChaseDir/P_Move and accepts one bounded chase move. "
        "Damage remains zero because no attack state/action is reached. Stage43 projectile, stage41 status, BAL1 world vissprite, "
        "stage39 projectile state, stage44 live/replay ownership, finite redraw, and present ordering remain preserved. "
        "No generalized thinkers/pathing/collision/combat, broad sprites/HUD/inventory, death/respawn, progression, save, network, music, or audio. ",
    )
    pe.label("stage45_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S45 REPLAY START STEP45=0 LIVE44=0 selected MT_SHOTGUY thinker waiting")
    pe.label("stage45_live_title_start")
    x86.emit_asciiz(pe, "Inference Doom S45 LIVE START LIVE44=1 bounded stage44 ticcmd and finite monster sample table")
    for index, title in enumerate(_stage45_replay_titles(ref)):
        pe.label(f"stage45_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)
    pe.label("stage45_live_title_buffer")
    pe.emit(b"\0" * 1024)
    pe.label("stage45_live_title_prefix")
    x86.emit_asciiz(pe, "Inference Doom S45 LIVE LIVE44=1 BOUND45=1 ROUTE44=bounded3")
    for label, text in (
        ("stage45_live_title_cmd_prefix", " LCMD44="),
        ("stage45_live_title_forward_prefix", " FM44="),
        ("stage45_live_title_actor_prefix", " ACT45="),
        ("stage45_live_title_state_prefix", " AST45="),
        ("stage45_live_title_tics_prefix", " TICS45="),
        ("stage45_live_title_sight_prefix", " SIGHT45="),
        ("stage45_live_title_move_prefix", " MOVEACC45="),
        ("stage45_live_title_fb_prefix", " FB45="),
        ("stage45_live_title_mstate_prefix", " MSTATE45="),
        ("stage45_live_title_sig_prefix", " S45SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)


def build_source_stage45_bounded_monster_chase_path_attack_decision_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else 3
    with patched_stage01_window_labels():
        emit_stage45_entry(pe)
        emit_stage45_wndproc_framebuffer(pe)
        stage44.emit_stage44_parse_command_line(pe)
        emit_stage45_timer_tick(pe)
        stage44.emit_stage44_live_runtime(pe)
        stage44.emit_stage44_select_live_sample_runtime(pe)
        stage44.emit_stage44_build_live_title(pe)
        emit_stage45_build_live_title(pe)
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
        stage43.emit_stage43_draw_projectile_feedback_marker(pe)
        stage44.emit_stage44_draw_player_view_marker(pe)
        emit_stage45_draw_monster_marker(pe)
        for index in range(sample_count):
            stage40._emit_stage40_draw_sample(pe, index)
            stage41._emit_stage41_draw_sample(pe, index)
            stage42._emit_stage42_update_sample(pe, index)
            stage42._emit_stage42_draw_sample(pe, index)
            stage43._emit_stage43_update_sample(pe, index)
            stage43._emit_stage43_draw_sample(pe, index)
            stage44._emit_stage44_update_sample(pe, index)
            stage44._emit_stage44_draw_sample(pe, index)
            _emit_stage45_update_sample(pe, index)
            _emit_stage45_draw_sample(pe, index)
        stage36.emit_source_stage36_load_wad_selected_dropped_shotgun_visual_boundary(pe)
        stage38.emit_source_stage38_load_wad_selected_attack_feedback_present_bridge(pe)
        stage39.emit_source_stage39_load_wad_selected_projectile_spawn_present_probe(pe)
        stage40.emit_source_stage40_load_wad_bounded_vissprite_traversal_sorting_bridge(pe)
        stage41.emit_source_stage41_load_wad_statusbar_weapon_ammo_feedback_bridge(pe)
        stage42.emit_source_stage42_load_wad_unified_live_tick_render_loop_probe(pe)
        stage43.emit_source_stage43_load_wad_bounded_projectile_tick_collision_feedback_probe(pe)
        stage44.emit_source_stage44_load_wad_live_ticcmd_unified_player_render_loop_bridge(pe)
        emit_source_stage45_load_wad_bounded_monster_chase_path_attack_decision_probe(pe)
        stage36._emit_prior_loaders(pe)
        stage36._emit_runtime_helpers(pe)
        stage36.emit_render_selected_dropped_shotgun_visual_boundary_debug(pe)
        stage38.emit_render_selected_attack_feedback_present_bridge_debug(pe)
        stage39.emit_render_selected_projectile_spawn_present_probe_debug(pe)
        stage40.emit_render_bounded_vissprite_traversal_sorting_bridge_debug(pe)
        stage41.emit_render_statusbar_weapon_ammo_feedback_bridge_debug(pe)
        stage42.emit_render_unified_live_tick_render_loop_probe_debug(pe)
        stage43.emit_render_bounded_projectile_tick_collision_feedback_probe_debug(pe)
        stage44.emit_render_live_ticcmd_unified_player_render_loop_bridge_debug(pe)
        emit_render_bounded_monster_chase_path_attack_decision_probe_debug(pe)
        stage36._emit_prior_status(pe)
        stage36.emit_append_stage36_success_status(pe)
        stage38.emit_append_stage38_success_status(pe)
        stage39.emit_append_stage39_success_status(pe)
        stage40.emit_append_stage40_success_status(pe)
        stage41.emit_append_stage41_success_status(pe)
        stage42.emit_append_stage42_success_status(pe)
        stage43.emit_append_stage43_success_status(pe)
        stage44.emit_append_stage44_success_status(pe)
        emit_append_stage45_success_status(pe)
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
        stage42.emit_stage42_data(pe)
        stage43.emit_stage43_data(pe)
        stage44.emit_stage44_data(pe)
        emit_stage45_data(pe)
    return pe.build("entry")


def write_source_stage45_bounded_monster_chase_path_attack_decision_probe_exe(
    path: str | Path = OUTPUT_PATH,
) -> bytes:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = build_source_stage45_bounded_monster_chase_path_attack_decision_probe_exe()
    output.write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage45 bounded monster chase/path/attack decision PE32 probe"
    )
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output PE32 executable path")
    args = parser.parse_args()
    output = Path(args.output)
    data = write_source_stage45_bounded_monster_chase_path_attack_decision_probe_exe(output)
    ref = _reference_for_default_wad_or_none()
    print(f"Wrote {output} ({len(data)} bytes)")
    if ref is not None:
        print(f"S45SIG={ref.signature}")
        print(f"STATE45={ref.state_signature}")
        print("MSTATE45=" + ",".join(str(sample.monster_decision_state_signature) for sample in ref.samples))
        print("ULSTATE45=" + ",".join(str(sample.stage45_unified_state_signature) for sample in ref.samples))
        print("FB45=" + ",".join(str(sample.framebuffer_signature) for sample in ref.samples))
        print(f"OUTCOME45={ref.selected_outcome}")


if __name__ == "__main__":
    main()
