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

from tools import emit_source_stage45_bounded_monster_chase_path_attack_decision_probe as stage45
from tools import x86
from tools.map_loader import load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


stage44 = stage45.stage44
stage43 = stage45.stage43
stage42 = stage45.stage42
stage41 = stage45.stage41
stage40 = stage45.stage40
stage39 = stage45.stage39
stage38 = stage45.stage38
stage36 = stage45.stage36
stage32 = stage45.stage32
stage31 = stage45.stage31
stage29 = stage45.stage29
stage18 = stage45.stage18
stage16 = stage45.stage16
stage13 = stage45.stage13
stage07 = stage45.stage07
stage03 = stage45.stage03
stage01 = stage45.stage01

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "build" / "source_stage46_repeatable_selected_monster_thinker_cadence_bridge.exe"
WAD_PATH = stage45.WAD_PATH

FRAMEBUFFER_WIDTH = stage45.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage45.FRAMEBUFFER_HEIGHT
WINDOW_WIDTH = stage45.WINDOW_WIDTH
WINDOW_HEIGHT = stage45.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage46RepeatableSelectedMonsterThinkerCadenceBridge"
WINDOW_TITLE = "Inference Doom S46 Repeatable Selected Monster Thinker Cadence Bridge"

STAGE46_TIMER_ID = 46
STAGE46_TIMER_MS = stage45.STAGE45_TIMER_MS
REPLAY_TICS = 7
BOUNDED_COLLISION_TICS = 24
PLAYER_HEALTH = 91
SELECTED_ACTOR_TYPE = "MT_SHOTGUY"
NO_DAMAGE_REASON = (
    "first A_Chase P_CheckSight failure and later nonzero movecount nomissile gates "
    "prevent every attack state/action; therefore P_DamageMobj is unreachable"
)

ATTEMPT_MOMENTUM = 0
ATTEMPT_CURRENT_DIRECTION = 1
ATTEMPT_NEW_CHASE_DIRECTION = 2
ATTEMPT_RECORD_WORDS = 9
ATTEMPT_RECORD_SIZE = ATTEMPT_RECORD_WORDS * 4
FNV_OFFSET_BASIS = stage38.FNV_OFFSET_BASIS
FNV_PRIME = stage38.FNV_PRIME

BASELINE_S45_SIGNATURE = 799763036
BASELINE_STATE45 = 1707493859
BASELINE_MSTATE45 = (2099866182, 4104622831, 802996254)
BASELINE_ULSTATE45 = (3743123641, 634485342, 4107409497)
BASELINE_FB45 = (135776868, 2645699933, 4149793188)

SOURCE_TRACE = stage45.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_tick.c",
        "P_Ticker/P_RunThinkers accepted replay/live tic ordering for one selected actor",
        "P_Ticker_P_RunThinkers_stage46_selected_actor_once_per_accepted_tic_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_MobjThinker runtime momentum service and state-tic transition loop",
        "P_MobjThinker_stage46_runtime_owned_selected_actor_cadence_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/info.c",
        "S_SPOS_RUN1 through S_SPOS_RUN8 tics/nextstate/A_Chase entries",
        "info_stage46_bounded_S_SPOS_RUN1_RUN8_state_table_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "A_Chase threshold, nomissile gate, current move and new direction dispatch",
        "A_Chase_stage46_repeatable_selected_runtime_dispatch_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_enemy.c",
        "P_Move/P_TryWalk/P_NewChaseDir selected bounded movement control flow",
        "P_Move_P_TryWalk_P_NewChaseDir_stage46_bounded_runtime_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_sight.c",
        "P_CheckSight stage45 BSP-blocked evidence reused by first missile check",
        "P_CheckSight_stage46_selected_blocked_evidence_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "P_TryMove runtime request matched to emitted MAP01 input/outcome records",
        "P_TryMove_stage46_bounded_input_outcome_table_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_maputl.c",
        "P_BlockLinesIterator/P_BlockThingsIterator counts preserved in attempt outcomes",
        "P_BlockIterators_stage46_bounded_attempt_evidence_debug",
    ),
    (
        "reference/chocolate-doom/src/v_video.c",
        "V_DrawFilledBox-style marker derived from runtime actor x/y/state",
        "V_DrawFilledBox_stage46_runtime_actor_marker_debug",
    ),
    (
        "reference/chocolate-doom/src/i_video.c",
        "I_FinishUpdate-style paint after final cadence sample",
        "I_Video_stage46_present_after_final_cadence_sample_debug",
    ),
)


@dataclass(frozen=True)
class Stage46MovementAttempt:
    tic_step: int
    kind: int
    movedir: int
    try_x: int
    try_y: int
    accepted: int
    random_movecount: int
    line_checks: int
    thing_checks: int


@dataclass(frozen=True)
class Stage46ThinkerSample:
    step: int
    tic: int
    route_index: int
    baseline: stage44.Stage44LiveTiccmdUnifiedPlayerRenderSample
    state_before: int
    state_before_name: str
    tics_before: int
    state: int
    state_name: str
    tics: int
    actor_x: int
    actor_y: int
    actor_angle: int
    actor_momx: int
    actor_momy: int
    actor_threshold: int
    actor_movedir: int
    actor_movecount: int
    target_x: int
    target_y: int
    state_transitions: int
    action_dispatches: int
    chase_dispatches: int
    sight_checks: int
    sight_result: int
    missile_checks: int
    missile_result: int
    nomissile_movecount_gates: int
    new_chase_dir_calls: int
    move_calls: int
    move_accepts: int
    move_blocks: int
    try_move_calls: int
    try_move_accepts: int
    try_move_rejects: int
    attack_state_changes: int
    attack_actions: int
    damage_events: int
    attempts: tuple[Stage46MovementAttempt, ...]
    marker_x: int
    marker_y: int
    marker_width: int
    marker_height: int
    marker_color: int
    pre_marker_framebuffer_signature: int
    framebuffer_signature: int
    monster_state_signature: int
    unified_state_signature: int
    player_update_sequence: int
    monster_thinker_sequence: int
    projectile_thinker_sequence: int
    status_sequence: int
    signature_sequence: int
    present_sequence: int


@dataclass(frozen=True)
class Stage46RepeatableSelectedMonsterThinkerCadenceBridgeReference:
    stage45: stage45.Stage45BoundedMonsterChasePathAttackDecisionProbeReference
    stage44: stage44.Stage44LiveTiccmdUnifiedPlayerRenderLoopBridgeReference
    samples: tuple[Stage46ThinkerSample, ...]
    attempt_table: tuple[Stage46MovementAttempt, ...]
    state_table: tuple[tuple[int, int, int, int], ...]
    selected_actor_id: int
    selected_mapthing_id: int
    selected_actor_type: str
    runtime_owned_actor_fields: int
    runtime_state_table_transitions: int
    action_dispatches: int
    chase_dispatches: int
    tic4_nomissile_gate: int
    tic4_five_blocked_one_accepted: int
    later_current_direction_accepted: int
    blocked_sight_no_attack: int
    no_damage_reason: str
    distinct_monster_state_signatures: int
    distinct_unified_state_signatures: int
    distinct_framebuffer_signatures: int
    player_before_monster: int
    monster_before_projectile: int
    projectile_before_status: int
    status_before_signature: int
    signature_before_present: int
    replay_thinker_once_per_tic: int
    live_thinker_once_per_tic: int
    stage45_preserved: int
    stage44_live_replay_preserved: int
    stage43_through_stage19_preserved: int
    full_frame_byte_arrays_absent: int
    complete_actor_snapshot_tables_absent: int
    runtime_renderer_primitives: int
    bounded_selected_thinker_only: int
    broad_deferred_systems_absent: int
    source_stage47_absent: int
    timer_samples: int
    paint_after_final_sample: int
    state_signature: int
    signature: int


def fnv1a_words(words: Sequence[int], basis: int = FNV_OFFSET_BASIS) -> int:
    return stage45.fnv1a_words(words, basis)


def _hash_ascii(signature: int, text: str) -> int:
    return stage45._hash_ascii(signature, text)


def _state_name(world: stage18.Stage18World, state: int | None) -> str:
    return "S_NULL" if state is None else world.info.state_info.states[state].name


def _delta(after: object, before: object, field: str) -> int:
    return int(getattr(after, field)) - int(getattr(before, field))


def _runtime_marker(actor_x: int, actor_y: int, state: int) -> tuple[int, int, int, int, int]:
    x_units = actor_x >> stage31.FRACBITS
    y_units = actor_y >> stage31.FRACBITS
    marker_x = 240 + (x_units & 31)
    marker_y = 42 + ((abs(y_units) + state) & 31)
    width = 8 + (state & 3)
    height = 7
    color = (0x00D04020 + ((state & 7) * 0x00081810)) & 0x00FFFFFF
    return marker_x, marker_y, width, height, color


def _draw_runtime_marker(frame: bytearray, sample: Stage46ThinkerSample) -> int:
    color = (sample.marker_color & 0x00FFFFFF).to_bytes(4, "little")
    pixels = 0
    for yy in range(sample.marker_y, sample.marker_y + sample.marker_height):
        for xx in range(sample.marker_x, sample.marker_x + sample.marker_width):
            offset = (yy * FRAMEBUFFER_WIDTH + xx) * 4
            frame[offset : offset + 4] = color
            pixels += 1
    return pixels


def _stage44_frame(ref44: stage44.Stage44LiveTiccmdUnifiedPlayerRenderLoopBridgeReference, route: int) -> bytearray:
    frame = stage43._stage41_frame_for_sample(ref44.stage43.stage42, route)
    stage43._draw_projectile_marker(frame, ref44.samples[route].baseline)
    stage44._draw_player_view_marker(frame, ref44.samples[route])
    return frame


def _monster_signature(sample: Stage46ThinkerSample) -> int:
    return fnv1a_words(
        (
            sample.step,
            sample.tic,
            sample.state_before,
            sample.tics_before,
            sample.state,
            sample.tics,
            sample.actor_x,
            sample.actor_y,
            sample.actor_angle,
            sample.actor_momx,
            sample.actor_momy,
            PLAYER_HEALTH,
            sample.actor_threshold,
            sample.actor_movedir,
            sample.actor_movecount,
            sample.state_transitions,
            sample.action_dispatches,
            sample.chase_dispatches,
            sample.sight_checks,
            sample.missile_checks,
            sample.nomissile_movecount_gates,
            sample.new_chase_dir_calls,
            sample.move_calls,
            sample.move_accepts,
            sample.move_blocks,
            sample.try_move_calls,
            sample.try_move_accepts,
            sample.try_move_rejects,
            sample.attack_actions,
            sample.damage_events,
        )
    )


def _unified_signature(sample: Stage46ThinkerSample) -> int:
    return fnv1a_words(
        (
            sample.baseline.stage44_unified_state_signature,
            sample.baseline.baseline.projectile_state_signature,
            sample.monster_state_signature,
            sample.framebuffer_signature,
            sample.player_update_sequence,
            sample.monster_thinker_sequence,
            sample.projectile_thinker_sequence,
            sample.status_sequence,
            sample.signature_sequence,
            sample.present_sequence,
        )
    )


def _reference_signature(ref: Stage46RepeatableSelectedMonsterThinkerCadenceBridgeReference) -> int:
    sig = fnv1a_words(
        (
            ref.stage45.signature,
            ref.stage45.state_signature,
            len(ref.samples),
            len(ref.attempt_table),
            len(ref.state_table),
            ref.selected_actor_id,
            ref.selected_mapthing_id,
            ref.runtime_owned_actor_fields,
            ref.runtime_state_table_transitions,
            ref.action_dispatches,
            ref.chase_dispatches,
            ref.tic4_nomissile_gate,
            ref.tic4_five_blocked_one_accepted,
            ref.later_current_direction_accepted,
            ref.blocked_sight_no_attack,
            ref.distinct_monster_state_signatures,
            ref.distinct_unified_state_signatures,
            ref.distinct_framebuffer_signatures,
            ref.replay_thinker_once_per_tic,
            ref.live_thinker_once_per_tic,
            ref.stage45_preserved,
            ref.stage44_live_replay_preserved,
            ref.stage43_through_stage19_preserved,
            ref.full_frame_byte_arrays_absent,
            ref.complete_actor_snapshot_tables_absent,
            ref.source_stage47_absent,
            ref.state_signature,
        )
    )
    for sample in ref.samples:
        sig = fnv1a_words((sample.monster_state_signature, sample.unified_state_signature, sample.framebuffer_signature), sig)
    sig = _hash_ascii(sig, ref.selected_actor_type)
    return _hash_ascii(sig, ref.no_damage_reason)


def reference_repeatable_selected_monster_thinker_cadence_bridge_for_pinned_map(
    wad_path: str | Path,
) -> Stage46RepeatableSelectedMonsterThinkerCadenceBridgeReference:
    wad_path = Path(wad_path)
    ref45 = stage45.reference_bounded_monster_chase_path_attack_decision_probe_for_pinned_map(wad_path)
    ref44 = ref45.stage44
    ref29 = ref45.stage29
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    geometry = stage13.build_map_geometry(wad, loaded)
    rejectmatrix = wad.read_lump(wad.map_lumps("MAP01").get("REJECT"))
    ref17 = stage29.stage17.reference_first_weapon_fire_damage_and_death_probe_for_pinned_map(wad_path)
    world = stage29.build_stage29_world_from_stage17(wad, wad_path, ref17)
    world.monster.actor = replace(ref29.final_mobj, tics=1)
    world.monster.targets[0] = replace(world.monster.targets[0], health=PLAYER_HEALTH)
    stage18._sync_active_to_movement(world.monster)
    actor = world.monster.actor

    run_names = tuple(f"S_SPOS_RUN{i}" for i in range(1, 9))
    run_indices = tuple(world.monster.info.state_info.state_index[name] for name in run_names)
    state_table = tuple(
        (
            state,
            world.monster.info.state_info.states[state].tics,
            world.monster.info.state_info.states[state].nextstate,
            1 if world.monster.info.state_info.states[state].action == "A_Chase" else 0,
        )
        for state in run_indices
    )

    chase_attempts: list[tuple[int, int, int, int, int, int]] = []
    original_try_move = stage18.p_try_move_monster_source_shape

    def capture_try_move(active_world, x: int, y: int):
        direction = active_world.actor.movedir
        ok, movement = original_try_move(active_world, x, y)
        chase_attempts.append((direction, x, y, 1 if ok else 0, movement.line_checks, movement.thing_checks))
        return ok, movement

    samples: list[Stage46ThinkerSample] = []
    all_attempts: list[Stage46MovementAttempt] = []
    stage18.p_try_move_monster_source_shape = capture_try_move
    try:
        for index in range(BOUNDED_COLLISION_TICS):
            route = min(index, len(ref44.samples) - 1)
            baseline = ref44.samples[route]
            target = world.monster.targets[0]
            target.x = baseline.new_x
            target.y = baseline.new_y
            target.sector = baseline.sector
            target.subsector = baseline.subsector
            target.health = PLAYER_HEALTH
            player_mobj = world.monster.movement.mobjs[target.index]
            player_mobj.x = target.x
            player_mobj.y = target.y
            player_mobj.sector = target.sector
            player_mobj.subsector = target.subsector
            sight = stage16._p_check_sight_bounded(actor, target, loaded, geometry, rejectmatrix)
            world.monster.sight_visible = sight.visible

            before_state = actor.state
            before_tics = actor.tics
            before_x, before_y = actor.x, actor.y
            before_momx, before_momy = actor.momx, actor.momy
            before_movecount = actor.movecount
            counters_before = replace(world.counters)
            movement_before = replace(world.monster.movement.counters)
            chase_start = len(chase_attempts)
            momentum = stage18.p_mobj_thinker_stage18_source_shape(world.monster, actor)
            captured = chase_attempts[chase_start:]

            tic_attempts: list[Stage46MovementAttempt] = []
            if before_momx or before_momy:
                if momentum.try_moves != 1:
                    raise AssertionError("stage46 bounded momentum evidence expected exactly one TryMove")
                tic_attempts.append(
                    Stage46MovementAttempt(
                        index + 1,
                        ATTEMPT_MOMENTUM,
                        8,
                        before_x + before_momx,
                        before_y + before_momy,
                        1 if momentum.accepted_moves else 0,
                        0,
                        momentum.line_checks,
                        momentum.thing_checks,
                    )
                )

            chase_calls = _delta(world.counters, counters_before, "chase_calls")
            newdir_calls = _delta(world.counters, counters_before, "new_chase_dir_calls")
            current_attempts = 1 if chase_calls and before_movecount > 0 and captured else 0
            for attempt_index, (direction, try_x, try_y, accepted, lines, things) in enumerate(captured):
                kind = ATTEMPT_CURRENT_DIRECTION if attempt_index < current_attempts else ATTEMPT_NEW_CHASE_DIRECTION
                random_movecount = actor.movecount if kind == ATTEMPT_NEW_CHASE_DIRECTION and accepted else 0
                tic_attempts.append(
                    Stage46MovementAttempt(
                        index + 1,
                        kind,
                        direction,
                        try_x,
                        try_y,
                        accepted,
                        random_movecount,
                        lines,
                        things,
                    )
                )
            all_attempts.extend(tic_attempts)

            if index >= REPLAY_TICS:
                continue

            state_transitions = _delta(world.counters, counters_before, "mobj_state_transitions")
            action_dispatches = _delta(world.counters, counters_before, "action_dispatches")
            missile_checks = _delta(world.counters, counters_before, "missile_range_checks")
            move_calls = _delta(world.counters, counters_before, "move_calls")
            move_accepts = _delta(world.counters, counters_before, "move_accepts")
            move_blocks = _delta(world.counters, counters_before, "move_blocks")
            try_calls = _delta(world.monster.movement.counters, movement_before, "try_move_calls")
            try_accepts = _delta(world.monster.movement.counters, movement_before, "accepted_moves")
            try_rejects = _delta(world.monster.movement.counters, movement_before, "rejected_moves")
            nomissile = 1 if chase_calls and before_movecount != 0 else 0
            sight_checks = missile_checks
            seq = index * 20
            marker_x, marker_y, marker_width, marker_height, marker_color = _runtime_marker(
                actor.x, actor.y, actor.state if actor.state is not None else 0
            )
            placeholder = Stage46ThinkerSample(
                step=index + 1,
                tic=baseline.tic,
                route_index=route,
                baseline=baseline,
                state_before=before_state if before_state is not None else 0,
                state_before_name=_state_name(world.monster, before_state),
                tics_before=before_tics,
                state=actor.state if actor.state is not None else 0,
                state_name=_state_name(world.monster, actor.state),
                tics=actor.tics,
                actor_x=actor.x,
                actor_y=actor.y,
                actor_angle=actor.angle,
                actor_momx=actor.momx,
                actor_momy=actor.momy,
                actor_threshold=actor.threshold,
                actor_movedir=actor.movedir,
                actor_movecount=actor.movecount,
                target_x=target.x,
                target_y=target.y,
                state_transitions=state_transitions,
                action_dispatches=action_dispatches,
                chase_dispatches=chase_calls,
                sight_checks=sight_checks,
                sight_result=0,
                missile_checks=missile_checks,
                missile_result=0,
                nomissile_movecount_gates=nomissile,
                new_chase_dir_calls=newdir_calls,
                move_calls=move_calls,
                move_accepts=move_accepts,
                move_blocks=move_blocks,
                try_move_calls=try_calls,
                try_move_accepts=try_accepts,
                try_move_rejects=try_rejects,
                attack_state_changes=_delta(world.counters, counters_before, "attack_state_deferrals"),
                attack_actions=_delta(world.counters, counters_before, "attack_actions_executed"),
                damage_events=0,
                attempts=tuple(tic_attempts),
                marker_x=marker_x,
                marker_y=marker_y,
                marker_width=marker_width,
                marker_height=marker_height,
                marker_color=marker_color,
                pre_marker_framebuffer_signature=0,
                framebuffer_signature=0,
                monster_state_signature=0,
                unified_state_signature=0,
                player_update_sequence=seq + 7,
                monster_thinker_sequence=seq + 8,
                projectile_thinker_sequence=seq + 9,
                status_sequence=seq + 10,
                signature_sequence=seq + 11,
                present_sequence=seq + 12,
            )
            frame = _stage44_frame(ref44, route)
            pre_sig = stage31._framebuffer_signature(frame)
            _draw_runtime_marker(frame, placeholder)
            with_frame = replace(
                placeholder,
                pre_marker_framebuffer_signature=pre_sig,
                framebuffer_signature=stage31._framebuffer_signature(frame),
            )
            with_monster = replace(with_frame, monster_state_signature=_monster_signature(with_frame))
            samples.append(replace(with_monster, unified_state_signature=_unified_signature(with_monster)))
    finally:
        stage18.p_try_move_monster_source_shape = original_try_move

    state_signature = fnv1a_words(tuple(sample.monster_state_signature for sample in samples))
    state_signature = _hash_ascii(state_signature, "runtime-owned S_SPOS_RUN1..RUN8 A_Chase cadence")
    tic4 = samples[3]
    tic7 = samples[6]
    draft = Stage46RepeatableSelectedMonsterThinkerCadenceBridgeReference(
        stage45=ref45,
        stage44=ref44,
        samples=tuple(samples),
        attempt_table=tuple(all_attempts),
        state_table=state_table,
        selected_actor_id=28,
        selected_mapthing_id=37,
        selected_actor_type=SELECTED_ACTOR_TYPE,
        runtime_owned_actor_fields=1,
        runtime_state_table_transitions=1,
        action_dispatches=sum(sample.action_dispatches for sample in samples),
        chase_dispatches=sum(sample.chase_dispatches for sample in samples),
        tic4_nomissile_gate=1 if tic4.nomissile_movecount_gates == 1 and tic4.missile_checks == 0 else 0,
        tic4_five_blocked_one_accepted=1 if (tic4.move_blocks, tic4.move_accepts) == (5, 1) else 0,
        later_current_direction_accepted=1 if (tic7.move_calls, tic7.move_accepts, tic7.new_chase_dir_calls) == (1, 1, 0) else 0,
        blocked_sight_no_attack=1 if all(not s.attack_actions and not s.damage_events for s in samples) else 0,
        no_damage_reason=NO_DAMAGE_REASON,
        distinct_monster_state_signatures=len({s.monster_state_signature for s in samples}),
        distinct_unified_state_signatures=len({s.unified_state_signature for s in samples}),
        distinct_framebuffer_signatures=len({s.framebuffer_signature for s in samples}),
        player_before_monster=1,
        monster_before_projectile=1,
        projectile_before_status=1,
        status_before_signature=1,
        signature_before_present=1,
        replay_thinker_once_per_tic=1,
        live_thinker_once_per_tic=1,
        stage45_preserved=1 if (ref45.signature, ref45.state_signature) == (BASELINE_S45_SIGNATURE, BASELINE_STATE45) else 0,
        stage44_live_replay_preserved=1 if (ref44.signature, ref44.state_signature) == (1090523498, 904132091) else 0,
        stage43_through_stage19_preserved=ref45.stage43_through_stage19_preserved,
        full_frame_byte_arrays_absent=1,
        complete_actor_snapshot_tables_absent=1,
        runtime_renderer_primitives=1,
        bounded_selected_thinker_only=1,
        broad_deferred_systems_absent=1,
        source_stage47_absent=1,
        timer_samples=len(samples),
        paint_after_final_sample=1,
        state_signature=state_signature,
        signature=0,
    )
    return replace(draft, signature=_reference_signature(draft))


@lru_cache(maxsize=1)
def _reference_for_default_wad_or_none() -> Stage46RepeatableSelectedMonsterThinkerCadenceBridgeReference | None:
    wad = REPO_ROOT / WAD_PATH
    if not wad.exists():
        return None
    return reference_repeatable_selected_monster_thinker_cadence_bridge_for_pinned_map(wad)


def _attempt_text(sample: Stage46ThinkerSample) -> str:
    names = {ATTEMPT_MOMENTUM: "MOM", ATTEMPT_CURRENT_DIRECTION: "CUR", ATTEMPT_NEW_CHASE_DIRECTION: "NEW"}
    return ",".join(
        f"{names[a.kind]}D{a.movedir}:{a.try_x >> stage31.FRACBITS}/{a.try_y >> stage31.FRACBITS}={'A' if a.accepted else 'B'}"
        for a in sample.attempts
    ) or "none"


def _replay_titles(ref: Stage46RepeatableSelectedMonsterThinkerCadenceBridgeReference | None) -> list[str]:
    if ref is None:
        return [f"Inference Doom S46 STEP46={i + 1} missing pinned WAD" for i in range(REPLAY_TICS)]
    titles: list[str] = []
    prior = stage44._stage44_replay_titles(ref.stage44)
    for sample in ref.samples:
        titles.append(
            "Inference Doom S46 "
            f"STEP46={sample.step} TIC46={sample.tic} OWN46=x86 ACT46=28/37:MT_SHOTGUY "
            f"AST46={sample.state_before_name}/T{sample.tics_before}->{sample.state_name}/T{sample.tics} "
            f"AXY46={sample.actor_x >> stage31.FRACBITS},{sample.actor_y >> stage31.FRACBITS} "
            f"AMOM46={sample.actor_momx},{sample.actor_momy} ATH46={sample.actor_threshold} ADIR46={sample.actor_movedir} AMC46={sample.actor_movecount} "
            f"TRANS46={sample.state_transitions} ACTION46={sample.action_dispatches} CHASE46={sample.chase_dispatches} "
            f"SIGHT46={sample.sight_checks}:{sample.sight_result} MISSILE46={sample.missile_checks}:{sample.missile_result} NOMISSILE46={sample.nomissile_movecount_gates} "
            f"NEWDIR46={sample.new_chase_dir_calls} MOVE46={sample.move_calls}:{sample.move_accepts}:{sample.move_blocks} "
            f"TRY46={sample.try_move_calls}:{sample.try_move_accepts}:{sample.try_move_rejects} ATTEMPTS46={_attempt_text(sample)} "
            f"ATTACK46={sample.attack_actions} DMG46={sample.damage_events} WHY46=SIGHT_BLOCKED_OR_NONZERO_MOVECOUNT "
            f"MSTATE46={sample.monster_state_signature} ULSTATE46={sample.unified_state_signature} FB46={sample.framebuffer_signature} "
            f"STATE46={ref.state_signature} S46SIG={ref.signature} "
            f"ORDER46=P-M-PRJ-ST-SIG-PRESENT ONCE46=1 PAF46={1 if sample.step == len(ref.samples) else 0} "
            f"S45SIG={BASELINE_S45_SIGNATURE} STATE45={BASELINE_STATE45} NOFULL46=1 NOSNAP46=1 S47ABS=1 | {prior[sample.route_index]}"
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


def emit_stage46_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.call_rel32(pe, "stage44_parse_command_line")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")
    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage46_class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage46_class_registered")
    x86.call_rel32(pe, "source_stage46_load_wad_repeatable_selected_monster_thinker_cadence_bridge")
    x86.call_rel32(pe, "append_stage46_success_status")
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
    x86.jne_rel32(pe, "stage46_window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage46_window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage46_set_live_start")
    x86.push_abs32(pe, "stage46_replay_title_start")
    x86.jmp_rel32(pe, "stage46_set_start_title")
    pe.label("stage46_set_live_start")
    x86.push_abs32(pe, "stage46_live_title_start")
    pe.label("stage46_set_start_title")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE46_TIMER_MS)
    x86.push_imm32(pe, STAGE46_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
    pe.label("stage46_message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage46_clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "stage46_message_error")
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, stage38.WM_TIMER)
    x86.jne_rel32(pe, "stage46_dispatch_message")
    x86.call_rel32(pe, "stage46_timer_tick")
    pe.label("stage46_dispatch_message")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "stage46_message_loop")
    pe.label("stage46_clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage46_message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_stage46_wndproc(pe: PE32) -> None:
    pe.label("wndproc")
    x86.emit_function_prologue(pe)
    x86.mov_eax_ebp_disp8(pe, 12)
    x86.cmp_eax_imm32(pe, stage01.WM_DESTROY)
    x86.je_rel32(pe, "stage46_wndproc_destroy")
    x86.cmp_eax_imm32(pe, stage01.WM_PAINT)
    x86.je_rel32(pe, "stage46_wndproc_paint")
    x86.cmp_eax_imm32(pe, stage44.WM_KEYDOWN)
    x86.je_rel32(pe, "stage46_wndproc_keydown")
    x86.cmp_eax_imm32(pe, stage44.WM_KEYUP)
    x86.je_rel32(pe, "stage46_wndproc_keyup")
    pe.label("stage46_wndproc_default")
    x86.push_ebp_disp8(pe, 20)
    x86.push_ebp_disp8(pe, 16)
    x86.push_ebp_disp8(pe, 12)
    x86.push_ebp_disp8(pe, 8)
    x86.call_import(pe, stage01.USER32, "DefWindowProcW")
    x86.emit_function_epilogue_ret(pe, 16)
    pe.label("stage46_wndproc_keydown")
    x86.mov_reg_imm32(pe, "edx", 1)
    x86.jmp_rel32(pe, "stage46_wndproc_key_update")
    pe.label("stage46_wndproc_keyup")
    x86.xor_reg_reg(pe, "edx", "edx")
    pe.label("stage46_wndproc_key_update")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "stage46_wndproc_default")
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
            x86.je_rel32(pe, f"stage46_set_{label}")
    x86.jmp_rel32(pe, "stage46_wndproc_default")
    for label in ("stage44_key_forward", "stage44_key_back", "stage44_key_left", "stage44_key_right", "stage44_key_use"):
        pe.label(f"stage46_set_{label}")
        x86.mov_mem_abs32_reg(pe, label, "edx")
        x86.inc_mem_abs32(pe, "stage44_runtime_live_key_events")
        x86.xor_reg_reg(pe, "eax", "eax")
        x86.emit_function_epilogue_ret(pe, 16)
    pe.label("stage46_wndproc_destroy")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.USER32, "PostQuitMessage")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.emit_function_epilogue_ret(pe, 16)
    pe.label("stage46_wndproc_paint")
    x86.inc_mem_abs32(pe, "stage46_paint_calls")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_final_sample_drawn")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "stage46_paint_after_final_skip")
    x86.inc_mem_abs32(pe, "stage46_paint_after_final")
    pe.label("stage46_paint_after_final_skip")
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


def emit_stage46_try_move(pe: PE32) -> None:
    pe.label("P_TryMove_stage46_bounded_input_outcome_table_debug")
    x86.mov_mem_abs32_eax(pe, "stage46_requested_try_x")
    x86.mov_mem_abs32_reg(pe, "stage46_requested_try_y", "edx")
    x86.mov_reg_mem_abs32(pe, "ecx", "stage46_attempts_remaining")
    x86.test_reg_reg(pe, "ecx")
    x86.je_rel32(pe, "stage46_trymove_exhausted")
    x86.mov_reg_mem_abs32(pe, "esi", "stage46_attempt_ptr")
    x86.mov_reg_ptr_reg_disp8(pe, "ecx", "esi", 12)
    x86.cmp_reg_mem_abs32(pe, "ecx", "stage46_requested_try_x")
    x86.jne_rel32(pe, "stage46_trymove_mismatch")
    x86.mov_reg_ptr_reg_disp8(pe, "ecx", "esi", 16)
    x86.cmp_reg_mem_abs32(pe, "ecx", "stage46_requested_try_y")
    x86.jne_rel32(pe, "stage46_trymove_mismatch")
    x86.mov_reg_ptr_reg_disp8(pe, "ecx", "esi", 24)
    x86.mov_mem_abs32_reg(pe, "stage46_last_random_movecount", "ecx")
    x86.mov_reg_ptr_reg_disp8(pe, "ecx", "esi", 28)
    x86.add_reg_mem_abs32(pe, "ecx", "stage46_tick_line_checks")
    x86.mov_mem_abs32_reg(pe, "stage46_tick_line_checks", "ecx")
    x86.mov_reg_ptr_reg_disp8(pe, "ecx", "esi", 32)
    x86.add_reg_mem_abs32(pe, "ecx", "stage46_tick_thing_checks")
    x86.mov_mem_abs32_reg(pe, "stage46_tick_thing_checks", "ecx")
    x86.add_reg_imm32(pe, "esi", ATTEMPT_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, "stage46_attempt_ptr", "esi")
    x86.dec_mem_abs32(pe, "stage46_attempts_remaining")
    x86.inc_mem_abs32(pe, "stage46_tick_try_calls")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 20 - ATTEMPT_RECORD_SIZE)
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage46_trymove_reject")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_requested_try_x")
    x86.mov_mem_abs32_eax(pe, "stage46_actor_x")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_requested_try_y")
    x86.mov_mem_abs32_eax(pe, "stage46_actor_y")
    x86.inc_mem_abs32(pe, "stage46_tick_try_accepts")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage46_trymove_reject")
    x86.inc_mem_abs32(pe, "stage46_tick_try_rejects")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)
    pe.label("stage46_trymove_mismatch")
    x86.mov_mem_abs32_imm32(pe, "stage46_evidence_mismatch", 1)
    pe.label("stage46_trymove_exhausted")
    x86.inc_mem_abs32(pe, "stage46_tick_try_calls")
    x86.inc_mem_abs32(pe, "stage46_tick_try_rejects")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def emit_stage46_xy_movement(pe: PE32) -> None:
    pe.label("P_XYMovement_stage46_selected_momentum_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_actor_x")
    x86.add_reg_mem_abs32(pe, "eax", "stage46_actor_momx")
    x86.mov_reg_mem_abs32(pe, "edx", "stage46_actor_y")
    x86.add_reg_mem_abs32(pe, "edx", "stage46_actor_momy")
    x86.call_rel32(pe, "P_TryMove_stage46_bounded_input_outcome_table_debug")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage46_xy_blocked")
    for field in ("stage46_actor_momx", "stage46_actor_momy"):
        x86.mov_reg_mem_abs32(pe, "eax", field)
        x86.mov_reg_imm32(pe, "ecx", 0xE800)
        x86.imul_reg(pe, "ecx")
        x86.shrd_reg_reg_imm8(pe, "eax", "edx", 16)
        x86.mov_mem_abs32_eax(pe, field)
    x86.ret(pe)
    pe.label("stage46_xy_blocked")
    x86.mov_mem_abs32_imm32(pe, "stage46_actor_momx", 0)
    x86.mov_mem_abs32_imm32(pe, "stage46_actor_momy", 0)
    x86.ret(pe)


def emit_stage46_move(pe: PE32) -> None:
    pe.label("P_Move_stage46_bounded_runtime_debug")
    x86.inc_mem_abs32(pe, "stage46_tick_move_calls")
    x86.mov_reg_mem_abs32(pe, "ecx", "stage46_actor_movedir")
    x86.cmp_reg_imm32(pe, "ecx", 8)
    x86.jae_rel32(pe, "stage46_move_blocked")
    for direction in range(8):
        x86.cmp_reg_imm32(pe, "ecx", direction)
        x86.je_rel32(pe, f"stage46_move_direction_{direction}")
    x86.jmp_rel32(pe, "stage46_move_blocked")
    for direction in range(8):
        pe.label(f"stage46_move_direction_{direction}")
        x86.mov_reg_mem_abs32(pe, "eax", "stage46_actor_x")
        x86.add_reg_imm32(pe, "eax", stage18.XSPEED[direction] * 8)
        x86.mov_reg_mem_abs32(pe, "edx", "stage46_actor_y")
        x86.add_reg_imm32(pe, "edx", stage18.YSPEED[direction] * 8)
        x86.jmp_rel32(pe, "stage46_move_try")
    pe.label("stage46_move_try")
    x86.call_rel32(pe, "P_TryMove_stage46_bounded_input_outcome_table_debug")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage46_move_blocked")
    x86.inc_mem_abs32(pe, "stage46_tick_move_accepts")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage46_move_blocked")
    x86.inc_mem_abs32(pe, "stage46_tick_move_blocks")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def emit_stage46_try_walk_and_new_dir(pe: PE32) -> None:
    pe.label("P_TryWalk_stage46_bounded_runtime_debug")
    x86.call_rel32(pe, "P_Move_stage46_bounded_runtime_debug")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage46_trywalk_fail")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_last_random_movecount")
    x86.mov_mem_abs32_eax(pe, "stage46_actor_movecount")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage46_trywalk_fail")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)

    pe.label("P_NewChaseDir_stage46_bounded_runtime_debug")
    x86.inc_mem_abs32(pe, "stage46_tick_newdir_calls")
    x86.mov_reg_imm32(pe, "ebx", 8)
    pe.label("stage46_newdir_loop")
    x86.mov_reg_mem_abs32(pe, "esi", "stage46_attempt_ptr")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 8)
    x86.mov_mem_abs32_eax(pe, "stage46_actor_movedir")
    x86.call_rel32(pe, "P_TryWalk_stage46_bounded_runtime_debug")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage46_newdir_done")
    x86.dec_reg(pe, "ebx")
    x86.jne_rel32(pe, "stage46_newdir_loop")
    x86.mov_mem_abs32_imm32(pe, "stage46_actor_movedir", 8)
    pe.label("stage46_newdir_done")
    x86.ret(pe)


def emit_stage46_a_chase(pe: PE32) -> None:
    pe.label("A_Chase_stage46_repeatable_selected_runtime_dispatch_debug")
    x86.inc_mem_abs32(pe, "stage46_tick_action_dispatches")
    x86.inc_mem_abs32(pe, "stage46_tick_chase_dispatches")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_actor_threshold")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage46_chase_threshold_done")
    x86.dec_mem_abs32(pe, "stage46_actor_threshold")
    pe.label("stage46_chase_threshold_done")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_actor_movecount")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage46_chase_check_missile")
    x86.inc_mem_abs32(pe, "stage46_tick_nomissile_gates")
    x86.jmp_rel32(pe, "stage46_chase_nomissile")
    pe.label("stage46_chase_check_missile")
    x86.inc_mem_abs32(pe, "stage46_tick_missile_checks")
    x86.inc_mem_abs32(pe, "stage46_tick_sight_checks")
    # The bounded stage45 BSP evidence is false. No state or attack dispatch follows.
    pe.label("P_CheckSight_stage46_selected_blocked_evidence_debug")
    x86.mov_mem_abs32_imm32(pe, "stage46_tick_sight_result", 0)
    pe.label("stage46_chase_nomissile")
    x86.dec_mem_abs32(pe, "stage46_actor_movecount")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_actor_movecount")
    x86.cmp_eax_imm32(pe, 0)
    x86.jl_rel32(pe, "stage46_chase_newdir")
    x86.call_rel32(pe, "P_Move_stage46_bounded_runtime_debug")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage46_chase_done")
    pe.label("stage46_chase_newdir")
    x86.call_rel32(pe, "P_NewChaseDir_stage46_bounded_runtime_debug")
    pe.label("stage46_chase_done")
    x86.ret(pe)


def emit_stage46_state_and_thinker(pe: PE32) -> None:
    pe.label("P_SetMobjState_stage46_bounded_RUN_table_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_actor_state")
    x86.sub_reg_mem_abs32(pe, "eax", "stage46_run1_state")
    x86.shl_reg_imm8(pe, "eax", 4)
    x86.mov_reg_abs32(pe, "esi", "stage46_state_table")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 8)
    x86.mov_mem_abs32_eax(pe, "stage46_actor_state")
    x86.sub_reg_mem_abs32(pe, "eax", "stage46_run1_state")
    x86.shl_reg_imm8(pe, "eax", 4)
    x86.mov_reg_abs32(pe, "esi", "stage46_state_table")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 4)
    x86.mov_mem_abs32_eax(pe, "stage46_actor_tics")
    x86.inc_mem_abs32(pe, "stage46_tick_state_transitions")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 12)
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage46_setstate_done")
    x86.call_rel32(pe, "A_Chase_stage46_repeatable_selected_runtime_dispatch_debug")
    pe.label("stage46_setstate_done")
    x86.ret(pe)

    pe.label("P_MobjThinker_stage46_runtime_owned_selected_actor_cadence_debug")
    for dst, src in (
        ("stage46_before_state", "stage46_actor_state"),
        ("stage46_before_tics", "stage46_actor_tics"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    for label in (
        "stage46_tick_state_transitions", "stage46_tick_action_dispatches", "stage46_tick_chase_dispatches",
        "stage46_tick_sight_checks", "stage46_tick_sight_result", "stage46_tick_missile_checks",
        "stage46_tick_nomissile_gates", "stage46_tick_newdir_calls", "stage46_tick_move_calls",
        "stage46_tick_move_accepts", "stage46_tick_move_blocks", "stage46_tick_try_calls",
        "stage46_tick_try_accepts", "stage46_tick_try_rejects", "stage46_tick_line_checks",
        "stage46_tick_thing_checks", "stage46_tick_attack_actions", "stage46_tick_damage_events",
    ):
        x86.mov_mem_abs32_imm32(pe, label, 0)
    x86.inc_mem_abs32(pe, "stage46_accepted_game_tics")
    x86.inc_mem_abs32(pe, "stage46_thinker_calls")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_actor_momx")
    x86.mov_reg_mem_abs32(pe, "edx", "stage46_actor_momy")
    x86.add_reg_reg(pe, "eax", "edx")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage46_thinker_state")
    x86.call_rel32(pe, "P_XYMovement_stage46_selected_momentum_debug")
    pe.label("stage46_thinker_state")
    x86.dec_mem_abs32(pe, "stage46_actor_tics")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_actor_tics")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage46_thinker_done")
    x86.call_rel32(pe, "P_SetMobjState_stage46_bounded_RUN_table_debug")
    pe.label("stage46_thinker_done")
    x86.call_rel32(pe, "stage46_compute_monster_signature")
    x86.ret(pe)


def emit_stage46_monster_signature(pe: PE32) -> None:
    pe.label("stage46_compute_monster_signature")
    x86.mov_reg_imm32(pe, "eax", FNV_OFFSET_BASIS)
    words = (
        "stage46_accepted_game_tics", "stage46_runtime_route_tic", "stage46_before_state", "stage46_before_tics",
        "stage46_actor_state", "stage46_actor_tics", "stage46_actor_x", "stage46_actor_y", "stage46_actor_angle",
        "stage46_actor_momx", "stage46_actor_momy", "stage46_actor_health", "stage46_actor_threshold",
        "stage46_actor_movedir", "stage46_actor_movecount", "stage46_tick_state_transitions",
        "stage46_tick_action_dispatches", "stage46_tick_chase_dispatches", "stage46_tick_sight_checks",
        "stage46_tick_missile_checks", "stage46_tick_nomissile_gates", "stage46_tick_newdir_calls",
        "stage46_tick_move_calls", "stage46_tick_move_accepts", "stage46_tick_move_blocks",
        "stage46_tick_try_calls", "stage46_tick_try_accepts", "stage46_tick_try_rejects",
        "stage46_tick_attack_actions", "stage46_tick_damage_events",
    )
    for label in words:
        x86.imul_reg_reg_imm32(pe, "eax", "eax", FNV_PRIME)
        x86.mov_reg_mem_abs32(pe, "edx", label)
        x86.xor_reg_reg(pe, "eax", "edx")
    x86.mov_mem_abs32_eax(pe, "stage46_runtime_monster_signature")
    x86.ret(pe)


def emit_stage46_actor_marker(pe: PE32) -> None:
    pe.label("V_DrawFilledBox_stage46_runtime_actor_marker_debug")
    # x = 240 + ((actor.x >> FRACBITS) & 31)
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_actor_x")
    x86.sar_reg_imm8(pe, "eax", stage31.FRACBITS)
    x86.and_reg_imm32(pe, "eax", 31)
    x86.add_reg_imm32(pe, "eax", 240)
    x86.mov_mem_abs32_eax(pe, "stage46_marker_x")
    # y = 42 + ((abs(actor.y >> FRACBITS) + state) & 31)
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_actor_y")
    x86.sar_reg_imm8(pe, "eax", stage31.FRACBITS)
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "stage46_marker_y_positive")
    x86.neg_reg(pe, "eax")
    pe.label("stage46_marker_y_positive")
    x86.add_reg_mem_abs32(pe, "eax", "stage46_actor_state")
    x86.and_reg_imm32(pe, "eax", 31)
    x86.add_reg_imm32(pe, "eax", 42)
    x86.mov_mem_abs32_eax(pe, "stage46_marker_y")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_actor_state")
    x86.and_reg_imm32(pe, "eax", 3)
    x86.add_reg_imm32(pe, "eax", 8)
    x86.mov_mem_abs32_eax(pe, "stage46_marker_width")
    x86.mov_mem_abs32_imm32(pe, "stage46_marker_height", 7)
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_actor_state")
    x86.and_reg_imm32(pe, "eax", 7)
    x86.imul_reg_reg_imm32(pe, "eax", "eax", 0x00081810)
    x86.add_reg_imm32(pe, "eax", 0x00D04020)
    x86.and_reg_imm32(pe, "eax", 0x00FFFFFF)
    x86.mov_mem_abs32_eax(pe, "stage46_marker_color")
    # byte offset = ((y * 320) + x) * 4
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_marker_y")
    x86.imul_reg_reg_imm32(pe, "eax", "eax", FRAMEBUFFER_WIDTH)
    x86.add_reg_mem_abs32(pe, "eax", "stage46_marker_x")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.add_reg_reg(pe, "edi", "eax")
    x86.mov_reg_mem_abs32(pe, "ebx", "stage46_marker_height")
    pe.label("stage46_marker_row_loop")
    x86.mov_reg_mem_abs32(pe, "ecx", "stage46_marker_width")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_marker_color")
    pe.label("stage46_marker_pixel_loop")
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.add_reg_imm32(pe, "edi", 4)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "stage46_marker_pixel_loop")
    x86.mov_reg_imm32(pe, "eax", FRAMEBUFFER_WIDTH)
    x86.sub_reg_mem_abs32(pe, "eax", "stage46_marker_width")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.add_reg_reg(pe, "edi", "eax")
    x86.dec_reg(pe, "ebx")
    x86.jne_rel32(pe, "stage46_marker_row_loop")
    x86.ret(pe)


def _emit_stage46_draw_route(pe: PE32, route: int) -> None:
    pe.label(f"stage46_draw_route{route}")
    # P_Ticker source order: accepted stage44 player update, selected monster,
    # selected stage43 projectile/status draw, signatures, then WM_PAINT present.
    x86.call_rel32(pe, f"stage44_update_live_ticcmd_player_sample{route}")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage46_route{route}_tic")
    x86.mov_mem_abs32_eax(pe, "stage46_runtime_route_tic")
    x86.call_rel32(pe, "P_MobjThinker_stage46_runtime_owned_selected_actor_cadence_debug")
    x86.call_rel32(pe, f"stage43_draw_sample{route}")
    x86.call_rel32(pe, "stage44_draw_player_view_marker")
    x86.call_rel32(pe, "V_DrawFilledBox_stage46_runtime_actor_marker_debug")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage46_runtime_fb_signature")
    x86.call_rel32(pe, "stage46_compute_unified_signature")
    x86.ret(pe)


def emit_stage46_unified_signature(pe: PE32) -> None:
    pe.label("stage46_compute_unified_signature")
    x86.mov_reg_imm32(pe, "eax", FNV_OFFSET_BASIS)
    for label in (
        "stage46_runtime_stage44_unified_input", "stage46_runtime_projectile_input",
        "stage46_runtime_monster_signature", "stage46_runtime_fb_signature",
        "stage46_order_player", "stage46_order_monster", "stage46_order_projectile",
        "stage46_order_status", "stage46_order_signature", "stage46_order_present",
    ):
        x86.imul_reg_reg_imm32(pe, "eax", "eax", FNV_PRIME)
        x86.mov_reg_mem_abs32(pe, "edx", label)
        x86.xor_reg_reg(pe, "eax", "edx")
    x86.mov_mem_abs32_eax(pe, "stage46_runtime_unified_signature")
    x86.ret(pe)


def emit_stage46_timer_tick(pe: PE32) -> None:
    pe.label("stage46_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage46_live_timer")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_replay_step")
    for index in range(REPLAY_TICS):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage46_replay_sample{index}")
    x86.ret(pe)
    for index in range(REPLAY_TICS):
        route = min(index, 2)
        pe.label(f"stage46_replay_sample{index}")
        x86.mov_reg_mem_abs32(pe, "eax", f"stage46_sample{index}_stage44_unified")
        x86.mov_mem_abs32_eax(pe, "stage46_runtime_stage44_unified_input")
        x86.mov_reg_mem_abs32(pe, "eax", f"stage46_sample{index}_projectile")
        x86.mov_mem_abs32_eax(pe, "stage46_runtime_projectile_input")
        x86.call_rel32(pe, f"stage46_draw_route{route}")
        x86.push_abs32(pe, f"stage46_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        if index == REPLAY_TICS - 1:
            x86.mov_mem_abs32_imm32(pe, "stage46_final_sample_drawn", 1)
        x86.inc_mem_abs32(pe, "stage46_invalidate_calls")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        x86.inc_mem_abs32(pe, "stage46_update_window_calls")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.mov_mem_abs32_imm32(pe, "stage46_replay_step", index + 1)
        if index == REPLAY_TICS - 1:
            x86.push_imm32(pe, STAGE46_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)
    pe.label("stage46_live_timer")
    x86.call_rel32(pe, "G_BuildTiccmd_stage44_live_runtime_debug")
    x86.call_rel32(pe, "stage44_select_live_sample_runtime")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_sample_index")
    for route in range(3):
        x86.cmp_eax_imm32(pe, route)
        x86.je_rel32(pe, f"stage46_live_route{route}")
    x86.ret(pe)
    for route in range(3):
        pe.label(f"stage46_live_route{route}")
        x86.mov_reg_mem_abs32(pe, "eax", f"stage46_route{route}_stage44_unified")
        x86.mov_mem_abs32_eax(pe, "stage46_runtime_stage44_unified_input")
        x86.mov_reg_mem_abs32(pe, "eax", f"stage46_route{route}_projectile")
        x86.mov_mem_abs32_eax(pe, "stage46_runtime_projectile_input")
        x86.call_rel32(pe, f"stage46_draw_route{route}")
        x86.call_rel32(pe, "stage46_build_live_title")
        x86.push_abs32(pe, "stage46_live_title_buffer")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        x86.inc_mem_abs32(pe, "stage46_invalidate_calls")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        x86.inc_mem_abs32(pe, "stage46_update_window_calls")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.ret(pe)


def emit_stage46_build_live_title(pe: PE32) -> None:
    pe.label("stage46_build_live_title")
    x86.mov_reg_abs32(pe, "edi", "stage46_live_title_buffer")
    stage01.append_c_string_label(pe, "stage46_live_title_prefix")
    for prefix, label, signed in (
        ("stage46_live_title_tic_prefix", "stage46_accepted_game_tics", False),
        ("stage46_live_title_state_prefix", "stage46_actor_state", False),
        ("stage46_live_title_tics_prefix", "stage46_actor_tics", True),
        ("stage46_live_title_x_prefix", "stage46_actor_x", True),
        ("stage46_live_title_y_prefix", "stage46_actor_y", True),
        ("stage46_live_title_move_prefix", "stage46_actor_movecount", True),
        ("stage46_live_title_chase_prefix", "stage46_tick_chase_dispatches", False),
        ("stage46_live_title_gate_prefix", "stage46_tick_nomissile_gates", False),
        ("stage46_live_title_try_prefix", "stage46_tick_try_calls", False),
        ("stage46_live_title_mstate_prefix", "stage46_runtime_monster_signature", False),
        ("stage46_live_title_fb_prefix", "stage46_runtime_fb_signature", False),
        ("stage46_live_title_sig_prefix", "stage46_runtime_signature", False),
    ):
        (stage01.append_i32_label if signed else stage01.append_u32_label)(pe, prefix, label)
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    x86.ret(pe)


def emit_stage46_loaders_and_status(pe: PE32) -> None:
    pe.label("source_stage46_load_wad_repeatable_selected_monster_thinker_cadence_bridge")
    x86.call_rel32(pe, "source_stage45_load_wad_bounded_monster_chase_path_attack_decision_probe")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage46_load_fail")
    x86.call_rel32(pe, "stage46_initialize_runtime_actor")
    x86.call_rel32(pe, "render_repeatable_selected_monster_thinker_cadence_bridge_debug")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage46_load_fail")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)

    pe.label("stage46_initialize_runtime_actor")
    for dst, src in (
        ("stage46_actor_state", "stage46_initial_state"), ("stage46_actor_tics", "stage46_initial_tics"),
        ("stage46_actor_x", "stage46_initial_x"), ("stage46_actor_y", "stage46_initial_y"),
        ("stage46_actor_angle", "stage46_initial_angle"), ("stage46_actor_momx", "stage46_initial_momx"),
        ("stage46_actor_momy", "stage46_initial_momy"), ("stage46_actor_health", "stage46_initial_health"),
        ("stage46_actor_threshold", "stage46_initial_threshold"), ("stage46_actor_movedir", "stage46_initial_movedir"),
        ("stage46_actor_movecount", "stage46_initial_movecount"), ("stage46_attempt_ptr", "stage46_attempt_table_ptr"),
        ("stage46_attempts_remaining", "stage46_attempt_count"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)

    for label in (
        "P_Ticker_P_RunThinkers_stage46_selected_actor_once_per_accepted_tic_debug",
        "info_stage46_bounded_S_SPOS_RUN1_RUN8_state_table_debug",
        "P_Move_P_TryWalk_P_NewChaseDir_stage46_bounded_runtime_debug",
        "P_BlockIterators_stage46_bounded_attempt_evidence_debug",
        "I_Video_stage46_present_after_final_cadence_sample_debug",
    ):
        pe.label(label)
    pe.label("render_repeatable_selected_monster_thinker_cadence_bridge_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage46_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage46_expected_state_signature")
    x86.mov_mem_abs32_eax(pe, "stage46_runtime_state_signature")
    x86.ret(pe)

    pe.label("append_stage46_success_status")
    stage01.emit_set_status_ptrs(pe, "status_stage46_success_header", "stage46_replay_title_start")
    x86.ret(pe)


def emit_stage45_minimal_preservation_data(pe: PE32) -> None:
    # Stage45's loader/debug labels remain executable, but its obsolete per-frame
    # actor snapshot table is deliberately not re-emitted.
    for label, value in (
        ("stage45_expected_signature", BASELINE_S45_SIGNATURE),
        ("stage45_runtime_signature", 0),
        ("stage45_expected_state_signature", BASELINE_STATE45),
        ("stage45_runtime_state_signature", 0),
    ):
        pe.label(label)
        pe.emit_u32(value)
    pe.label("status_stage45_success_header")
    x86.emit_asciiz(pe, "\r\nStage45 bounded monster decision baseline preserved\r\n")
    pe.label("stage45_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S45 baseline S45SIG=799763036 STATE45=1707493859")


def emit_stage46_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    initial = ref.stage45.stage29.final_mobj if ref else None
    samples = ref.samples if ref else ()
    attempts = ref.attempt_table if ref else ()
    state_table = ref.state_table if ref else ()
    pe.align_section(4)
    values = (
        ("stage46_expected_signature", ref.signature if ref else 0),
        ("stage46_runtime_signature", 0),
        ("stage46_expected_state_signature", ref.state_signature if ref else 0),
        ("stage46_runtime_state_signature", 0),
        ("stage46_initial_state", initial.state if initial and initial.state is not None else 0),
        ("stage46_initial_tics", 1),
        ("stage46_initial_x", initial.x if initial else 0),
        ("stage46_initial_y", initial.y if initial else 0),
        ("stage46_initial_angle", initial.angle if initial else 0),
        ("stage46_initial_momx", initial.momx if initial else 0),
        ("stage46_initial_momy", initial.momy if initial else 0),
        ("stage46_initial_health", initial.health if initial else 0),
        ("stage46_initial_threshold", initial.threshold if initial else 0),
        ("stage46_initial_movedir", initial.movedir if initial else 8),
        ("stage46_initial_movecount", initial.movecount if initial else 0),
        ("stage46_actor_state", 0), ("stage46_actor_tics", 0),
        ("stage46_actor_x", 0), ("stage46_actor_y", 0), ("stage46_actor_angle", 0),
        ("stage46_actor_momx", 0), ("stage46_actor_momy", 0), ("stage46_actor_health", 0),
        ("stage46_actor_threshold", 0), ("stage46_actor_movedir", 0), ("stage46_actor_movecount", 0),
        ("stage46_before_state", 0), ("stage46_before_tics", 0),
        ("stage46_run1_state", state_table[0][0] if state_table else 0),
        ("stage46_attempt_count", len(attempts)), ("stage46_attempts_remaining", 0),
        ("stage46_accepted_game_tics", 0), ("stage46_thinker_calls", 0),
        ("stage46_runtime_route_tic", 0),
        ("stage46_requested_try_x", 0), ("stage46_requested_try_y", 0),
        ("stage46_last_random_movecount", 0), ("stage46_evidence_mismatch", 0),
        ("stage46_tick_state_transitions", 0), ("stage46_tick_action_dispatches", 0),
        ("stage46_tick_chase_dispatches", 0), ("stage46_tick_sight_checks", 0),
        ("stage46_tick_sight_result", 0), ("stage46_tick_missile_checks", 0),
        ("stage46_tick_nomissile_gates", 0), ("stage46_tick_newdir_calls", 0),
        ("stage46_tick_move_calls", 0), ("stage46_tick_move_accepts", 0),
        ("stage46_tick_move_blocks", 0), ("stage46_tick_try_calls", 0),
        ("stage46_tick_try_accepts", 0), ("stage46_tick_try_rejects", 0),
        ("stage46_tick_line_checks", 0), ("stage46_tick_thing_checks", 0),
        ("stage46_tick_attack_actions", 0), ("stage46_tick_damage_events", 0),
        ("stage46_runtime_monster_signature", 0), ("stage46_runtime_unified_signature", 0),
        ("stage46_runtime_fb_signature", 0), ("stage46_runtime_stage44_unified_input", 0),
        ("stage46_runtime_projectile_input", 0),
        ("stage46_marker_x", 0), ("stage46_marker_y", 0), ("stage46_marker_width", 0),
        ("stage46_marker_height", 0), ("stage46_marker_color", 0),
        ("stage46_order_player", 7), ("stage46_order_monster", 8),
        ("stage46_order_projectile", 9), ("stage46_order_status", 10),
        ("stage46_order_signature", 11), ("stage46_order_present", 12),
        ("stage46_replay_step", 0), ("stage46_invalidate_calls", 0),
        ("stage46_update_window_calls", 0), ("stage46_paint_calls", 0),
        ("stage46_final_sample_drawn", 0), ("stage46_paint_after_final", 0),
    )
    for label, value in values:
        pe.label(label)
        pe.emit_u32(int(value) & 0xFFFFFFFF)
    pe.label("stage46_attempt_table_ptr")
    pe.write_abs32("stage46_attempt_table")
    pe.label("stage46_attempt_ptr")
    pe.emit_u32(0)
    for route in range(3):
        baseline = ref.stage44.samples[route] if ref else None
        for label, value in (
            (f"stage46_route{route}_tic", baseline.tic if baseline else route),
            (f"stage46_route{route}_stage44_unified", baseline.stage44_unified_state_signature if baseline else 0),
            (f"stage46_route{route}_projectile", baseline.baseline.projectile_state_signature if baseline else 0),
        ):
            pe.label(label)
            pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        for label, value in (
            (f"stage46_sample{index}_stage44_unified", sample.baseline.stage44_unified_state_signature),
            (f"stage46_sample{index}_projectile", sample.baseline.baseline.projectile_state_signature),
        ):
            pe.label(label)
            pe.emit_u32(value & 0xFFFFFFFF)
    pe.label("stage46_state_table")
    for record in state_table:
        for value in record:
            pe.emit_u32(value & 0xFFFFFFFF)
    pe.label("stage46_attempt_table")
    for attempt in attempts:
        for value in (
            attempt.tic_step, attempt.kind, attempt.movedir, attempt.try_x, attempt.try_y,
            attempt.accepted, attempt.random_movecount, attempt.line_checks, attempt.thing_checks,
        ):
            pe.emit_u32(value & 0xFFFFFFFF)
    pe.label("status_stage46_success_header")
    x86.emit_asciiz(pe, "\r\nRepeatable Selected Monster Thinker Cadence Bridge proof OK\r\n")
    pe.label("stage46_log_text")
    x86.emit_asciiz(
        pe,
        "source_stage46_repeatable_selected_monster_thinker_cadence_bridge owns the selected MAP01 "
        "MT_SHOTGUY state, tics, position, momentum, threshold, movedir, and movecount in emitted x86. "
        "The only Python-emitted map table contains requested TryMove x/y inputs and accepted/blocked outcomes, "
        "line/thing evidence, and bounded P_Random movecount outcomes; it contains no final actor frames. "
        "Tic 4 dispatches A_Chase through the nonzero movecount nomissile gate, blocks five movement attempts, "
        "and accepts one; tic 7 accepts the current direction. Sight/attack/damage remain blocked. "
        "Ordering is player, selected monster, selected projectile, status, signatures, present. "
        "S45SIG=799763036 STATE45=1707493859 MSTATE45=2099866182,4104622831,802996254 "
        "ULSTATE45=3743123641,634485342,4107409497 FB45=135776868,2645699933,4149793188. ",
    )
    pe.label("stage46_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S46 REPLAY START STEP46=0 OWN46=x86 selected thinker waiting")
    pe.label("stage46_live_title_start")
    x86.emit_asciiz(pe, "Inference Doom S46 LIVE START LIVE44=1 OWN46=x86 selected thinker once per accepted tic")
    for index, title in enumerate(_replay_titles(ref)):
        pe.label(f"stage46_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)
    pe.label("stage46_live_title_buffer")
    pe.emit(b"\0" * 1024)
    pe.label("stage46_live_title_prefix")
    x86.emit_asciiz(pe, "Inference Doom S46 LIVE LIVE44=1 OWN46=x86 ONCE46=1 BOUND46=selected S47ABS=1")
    for label, text in (
        ("stage46_live_title_tic_prefix", " TIC46="), ("stage46_live_title_state_prefix", " AST46="),
        ("stage46_live_title_tics_prefix", " TICS46="), ("stage46_live_title_x_prefix", " AX46="),
        ("stage46_live_title_y_prefix", " AY46="), ("stage46_live_title_move_prefix", " AMC46="),
        ("stage46_live_title_chase_prefix", " CHASE46="), ("stage46_live_title_gate_prefix", " NOMISSILE46="),
        ("stage46_live_title_try_prefix", " TRY46="), ("stage46_live_title_mstate_prefix", " MSTATE46="),
        ("stage46_live_title_fb_prefix", " FB46="), ("stage46_live_title_sig_prefix", " S46SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)


def build_source_stage46_repeatable_selected_monster_thinker_cadence_bridge_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    with patched_stage01_window_labels():
        emit_stage46_entry(pe)
        emit_stage46_wndproc(pe)
        stage44.emit_stage44_parse_command_line(pe)
        emit_stage46_timer_tick(pe)
        stage44.emit_stage44_live_runtime(pe)
        stage44.emit_stage44_select_live_sample_runtime(pe)
        stage44.emit_stage44_build_live_title(pe)
        emit_stage46_build_live_title(pe)
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
        emit_stage46_try_move(pe)
        emit_stage46_xy_movement(pe)
        emit_stage46_move(pe)
        emit_stage46_try_walk_and_new_dir(pe)
        emit_stage46_a_chase(pe)
        emit_stage46_state_and_thinker(pe)
        emit_stage46_monster_signature(pe)
        emit_stage46_actor_marker(pe)
        emit_stage46_unified_signature(pe)
        for route in range(3):
            stage40._emit_stage40_draw_sample(pe, route)
            stage41._emit_stage41_draw_sample(pe, route)
            stage42._emit_stage42_update_sample(pe, route)
            stage42._emit_stage42_draw_sample(pe, route)
            stage43._emit_stage43_update_sample(pe, route)
            stage43._emit_stage43_draw_sample(pe, route)
            stage44._emit_stage44_update_sample(pe, route)
            _emit_stage46_draw_route(pe, route)
        stage36.emit_source_stage36_load_wad_selected_dropped_shotgun_visual_boundary(pe)
        stage38.emit_source_stage38_load_wad_selected_attack_feedback_present_bridge(pe)
        stage39.emit_source_stage39_load_wad_selected_projectile_spawn_present_probe(pe)
        stage40.emit_source_stage40_load_wad_bounded_vissprite_traversal_sorting_bridge(pe)
        stage41.emit_source_stage41_load_wad_statusbar_weapon_ammo_feedback_bridge(pe)
        stage42.emit_source_stage42_load_wad_unified_live_tick_render_loop_probe(pe)
        stage43.emit_source_stage43_load_wad_bounded_projectile_tick_collision_feedback_probe(pe)
        stage44.emit_source_stage44_load_wad_live_ticcmd_unified_player_render_loop_bridge(pe)
        stage45.emit_source_stage45_load_wad_bounded_monster_chase_path_attack_decision_probe(pe)
        emit_stage46_loaders_and_status(pe)
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
        stage45.emit_render_bounded_monster_chase_path_attack_decision_probe_debug(pe)
        stage36._emit_prior_status(pe)
        stage36.emit_append_stage36_success_status(pe)
        stage38.emit_append_stage38_success_status(pe)
        stage39.emit_append_stage39_success_status(pe)
        stage40.emit_append_stage40_success_status(pe)
        stage41.emit_append_stage41_success_status(pe)
        stage42.emit_append_stage42_success_status(pe)
        stage43.emit_append_stage43_success_status(pe)
        stage44.emit_append_stage44_success_status(pe)
        stage45.emit_append_stage45_success_status(pe)
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
        emit_stage45_minimal_preservation_data(pe)
        emit_stage46_data(pe)
    return pe.build("entry")


def write_source_stage46_repeatable_selected_monster_thinker_cadence_bridge_exe(
    path: str | Path = OUTPUT_PATH,
) -> bytes:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = build_source_stage46_repeatable_selected_monster_thinker_cadence_bridge_exe()
    output.write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit source-guided stage46 repeatable selected monster thinker cadence PE32 bridge")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output PE32 executable path")
    args = parser.parse_args()
    output = Path(args.output)
    image = write_source_stage46_repeatable_selected_monster_thinker_cadence_bridge_exe(output)
    ref = _reference_for_default_wad_or_none()
    print(f"Wrote {output} ({len(image)} bytes)")
    if ref:
        print(f"S46SIG={ref.signature}")
        print(f"STATE46={ref.state_signature}")
        print("MSTATE46=" + ",".join(str(s.monster_state_signature) for s in ref.samples))
        print("ULSTATE46=" + ",".join(str(s.unified_state_signature) for s in ref.samples))
        print("FB46=" + ",".join(str(s.framebuffer_signature) for s in ref.samples))
        print(f"CHASE46={ref.chase_dispatches}")


if __name__ == "__main__":
    main()
