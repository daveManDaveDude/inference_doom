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

from tools import emit_source_stage14_game_loop_input_collision as stage14
from tools import emit_source_stage42_unified_live_tick_render_loop_probe as stage42
from tools import x86
from tools.map_loader import load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


stage41 = stage42.stage41
stage40 = stage42.stage40
stage39 = stage42.stage39
stage38 = stage42.stage38
stage36 = stage42.stage36
stage32 = stage42.stage32
stage31 = stage42.stage31
stage15 = stage42.stage15
stage07 = stage42.stage07
stage03 = stage42.stage03
stage01 = stage42.stage01

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "build" / "source_stage43_bounded_projectile_tick_collision_feedback_probe.exe"
WAD_PATH = stage42.WAD_PATH

FRAMEBUFFER_WIDTH = stage42.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage42.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_BYTES = stage42.FRAMEBUFFER_BYTES
WINDOW_WIDTH = stage42.WINDOW_WIDTH
WINDOW_HEIGHT = stage42.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage43BoundedProjectileTickCollisionFeedbackProbe"
WINDOW_TITLE = "Inference Doom S43 Projectile Tick Collision Feedback"

STAGE43_TIMER_ID = 43
STAGE43_TIMER_MS = stage42.STAGE42_TIMER_MS
PROJECTILE_MARKER_HEIGHT = 5
BASELINE_S42_SIGNATURE = 2427416971
BASELINE_S42_STATE_SIGNATURE = 2148021159
BASELINE_S41_SIGNATURE = 951695045
BASELINE_S41_STATE_SIGNATURE = 157977072
BASELINE_S40_SIGNATURE = 2737672056
BASELINE_S40_STATE_SIGNATURE = 268409133
BASELINE_S39_SIGNATURE = 3469618451
BASELINE_S39_STATE_SIGNATURE = 1403583302

SOURCE_TRACE = stage42.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_MobjThinker/P_XYMovement selected MT_TROOPSHOT momentum tick",
        "P_MobjThinker_stage43_selected_troopshot_tick_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "P_CheckPosition/P_TryMove selected missile no-collision result",
        "P_TryMove_stage43_selected_missile_no_collision_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "PIT_CheckThing selected missile source skip and no player damage",
        "PIT_CheckThing_stage43_selected_source_skip_no_damage_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_maputl.c",
        "P_BlockLinesIterator/P_BlockThingsIterator bounded MAP01 check",
        "P_BlockIterators_stage43_selected_projectile_bounds_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/info.c",
        "MT_TROOPSHOT S_TBALL1/S_TBALL2 SPR_BAL1 tic metadata",
        "info_stage43_selected_troopshot_tic_metadata_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_RenderPlayerView stage42 order preserved with projectile feedback marker",
        "R_RenderPlayerView_stage43_projectile_feedback_order_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/st_stuff.c",
        "ST_updateWidgets compact status preserved because missile causes no damage",
        "ST_updateWidgets_stage43_no_damage_status_preserved_debug",
    ),
    (
        "reference/chocolate-doom/src/i_video.c",
        "Stage42 invalidate/update/paint bridge preserved after final projectile tick",
        "I_Video_stage43_projectile_tick_present_debug",
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
class Stage43MoveDelta:
    try_move_calls: int
    check_position_calls: int
    accepted_moves: int
    rejected_moves: int
    line_checks: int
    thing_checks: int
    blocking_lines: int
    blocking_things: int
    line_iterator_calls: int
    thing_iterator_calls: int
    line_visits: int
    thing_visits: int
    line_duplicate_skips: int
    source_thing_skips: int
    player_touch_checks: int
    player_collision: int


@dataclass(frozen=True)
class Stage43ProjectileThinkerSample:
    step: int
    tic: int
    thinker_tic: int
    baseline: stage42.Stage42UnifiedLoopSample
    type_name: str
    state_name: str
    next_state_name: str
    sprite_name: str
    frame_letter: str
    old_x: int
    old_y: int
    old_z: int
    new_x: int
    new_y: int
    new_z: int
    momx: int
    momy: int
    momz: int
    tics_before: int
    tics_after: int
    alive: int
    present: int
    try_move_success: int
    check_position_success: int
    no_collision: int
    no_damage: int
    impact: int
    exploded: int
    player_health_before: int
    player_health_after: int
    player_damagecount_before: int
    player_damagecount_after: int
    source_mobj_index: int
    target_player_index: int
    target_distance_x: int
    target_distance_y: int
    target_radius_sum: int
    move_delta: Stage43MoveDelta
    marker_x: int
    marker_y: int
    marker_width: int
    marker_height: int
    marker_color: int
    marker_pixels: int
    pre_marker_framebuffer_signature: int
    framebuffer_signature: int
    projectile_state_signature: int
    stage43_unified_state_signature: int
    p_ticker_sequence: int
    p_runthinkers_sequence: int
    mobj_thinker_sequence: int
    xy_movement_sequence: int
    check_position_sequence: int
    try_move_sequence: int
    state_tic_sequence: int
    no_collision_feedback_sequence: int
    render_sequence: int
    status_sequence: int
    signature_sequence: int
    present_sequence: int


@dataclass(frozen=True)
class Stage43BoundedProjectileTickCollisionFeedbackProbeReference:
    stage42: stage42.Stage42UnifiedLiveTickRenderLoopProbeReference
    samples: tuple[Stage43ProjectileThinkerSample, ...]
    deterministic_projectile_thinker_samples: int
    projectile_advanced_after_launch: int
    selected_mobj_thinker_boundary: int
    selected_xy_movement_boundary: int
    selected_trymove_boundary: int
    selected_checkposition_boundary: int
    selected_block_iterator_boundary: int
    selected_source_skip_boundary: int
    selected_no_collision_result: int
    selected_no_damage_feedback: int
    compact_status_preserved_because_no_damage: int
    stage40_bal1_vissprite_preserved: int
    distinct_projectile_state_signatures: int
    distinct_framebuffer_signatures: int
    distinct_stage43_unified_state_signatures: int
    timer_samples: int
    invalidate_calls: int
    update_window_calls: int
    expected_paint_calls: int
    paint_after_final_projectile_sample: int
    final_window_alive_after_samples: int
    closes_normally: int
    stage42_unified_loop_preserved: int
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
    broad_monster_ai_absent: int
    broad_inventory_absent: int
    broad_hud_ui_absent: int
    player_death_absent: int
    enemy_kill_drop_absent: int
    explosions_absent: int
    radius_damage_absent: int
    splash_damage_absent: int
    infighting_absent: int
    map_progression_absent: int
    save_load_absent: int
    networking_absent: int
    music_absent: int
    real_audio_absent: int
    mixer_device_playback_absent: int
    source_stage44_absent: int
    state_signature: int
    signature: int


def _movement_delta_before(
    world: stage14.MovementWorld,
) -> tuple[stage14.MovementCounters, stage14.BlockIteratorState]:
    counters = stage14.MovementCounters(**world.counters.__dict__)
    iterator = stage14.BlockIteratorState(
        validcount=world.iterator.validcount,
        line_validcounts=dict(world.iterator.line_validcounts or {}),
        line_iterator_calls=world.iterator.line_iterator_calls,
        thing_iterator_calls=world.iterator.thing_iterator_calls,
        line_out_of_bounds=world.iterator.line_out_of_bounds,
        thing_out_of_bounds=world.iterator.thing_out_of_bounds,
        line_visits=world.iterator.line_visits,
        thing_visits=world.iterator.thing_visits,
        line_duplicate_skips=world.iterator.line_duplicate_skips,
        line_overflows=world.iterator.line_overflows,
        thing_overflows=world.iterator.thing_overflows,
    )
    return counters, iterator


def _movement_delta_after(
    world: stage14.MovementWorld,
    before: tuple[stage14.MovementCounters, stage14.BlockIteratorState],
    *,
    source_thing_skips: int,
    player_touch_checks: int,
    player_collision: int,
) -> Stage43MoveDelta:
    counters, iterator = before
    return Stage43MoveDelta(
        try_move_calls=world.counters.try_move_calls - counters.try_move_calls,
        check_position_calls=world.counters.check_position_calls - counters.check_position_calls,
        accepted_moves=world.counters.accepted_moves - counters.accepted_moves,
        rejected_moves=world.counters.rejected_moves - counters.rejected_moves,
        line_checks=world.counters.line_checks - counters.line_checks,
        thing_checks=world.counters.thing_checks - counters.thing_checks,
        blocking_lines=world.counters.blocking_lines - counters.blocking_lines,
        blocking_things=world.counters.blocking_things - counters.blocking_things,
        line_iterator_calls=world.iterator.line_iterator_calls - iterator.line_iterator_calls,
        thing_iterator_calls=world.iterator.thing_iterator_calls - iterator.thing_iterator_calls,
        line_visits=world.iterator.line_visits - iterator.line_visits,
        thing_visits=world.iterator.thing_visits - iterator.thing_visits,
        line_duplicate_skips=world.iterator.line_duplicate_skips - iterator.line_duplicate_skips,
        source_thing_skips=source_thing_skips,
        player_touch_checks=player_touch_checks,
        player_collision=player_collision,
    )


def _zero_move_delta() -> Stage43MoveDelta:
    return Stage43MoveDelta(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def _draw_projectile_marker(frame: bytearray, sample: Stage43ProjectileThinkerSample) -> int:
    color = (sample.marker_color & 0x00FFFFFF).to_bytes(4, "little")
    pixels = 0
    for yy in range(sample.marker_y, sample.marker_y + sample.marker_height):
        row = (yy * FRAMEBUFFER_WIDTH + sample.marker_x) * 4
        for xx in range(sample.marker_width):
            offset = row + xx * 4
            frame[offset : offset + 4] = color
            pixels += 1
    return pixels


def _stage41_frame_for_sample(
    ref42: stage42.Stage42UnifiedLiveTickRenderLoopProbeReference,
    index: int,
) -> bytearray:
    ref41 = ref42.stage41
    ref40 = ref41.stage40
    ref39 = ref40.stage39
    ref38 = ref39.stage38
    ref36 = ref38.stage36
    ref33 = ref36.stage34.stage33
    ref32 = ref33.stage32
    sample41 = ref41.samples[index]
    sample40 = ref40.samples[index]
    sample38 = ref39.samples[index].baseline
    sample36 = sample38.baseline
    base_sample = ref32.stage31.samples[index]
    framebuf, _base_sig, _wall_pixels, _flat_pixels = stage32._draw_stage31_base(base_sample, ref32.stage31)
    stage40.stage33._draw_impact_commands(framebuf, sample36.impact_commands, ref33.impact_sources, ref40.palette32)
    stage36._draw_death_commands(framebuf, sample36.death_commands, ref36.death_sources, ref40.palette32)
    stage36._draw_drop_commands(framebuf, sample36.drop_commands, ref36.drop_sources, ref40.palette32)
    stage40._draw_vissprite_commands(framebuf, sample40.commands, ref40.sources, ref40.palette32)
    stage32._draw_psprite_commands(framebuf, sample36.psprite_commands, ref32.psprite_sources, ref40.palette32)
    stage38._draw_stage38_feedback_marker(framebuf, sample38.feedback_marker_pixels, 0x00E03030 + index * 0x00001010)
    stage41._draw_status_rects(framebuf, sample41.commands)
    return framebuf


def _projectile_state_signature(sample: Stage43ProjectileThinkerSample) -> int:
    sig = fnv1a_words(
        (
            sample.step,
            sample.tic,
            sample.thinker_tic,
            sample.old_x,
            sample.old_y,
            sample.old_z,
            sample.new_x,
            sample.new_y,
            sample.new_z,
            sample.momx,
            sample.momy,
            sample.momz,
            sample.tics_before,
            sample.tics_after,
            sample.alive,
            sample.present,
            sample.try_move_success,
            sample.check_position_success,
            sample.no_collision,
            sample.no_damage,
            sample.impact,
            sample.exploded,
            sample.target_distance_x,
            sample.target_distance_y,
            sample.target_radius_sum,
            sample.move_delta.try_move_calls,
            sample.move_delta.check_position_calls,
            sample.move_delta.accepted_moves,
            sample.move_delta.rejected_moves,
            sample.move_delta.line_checks,
            sample.move_delta.thing_checks,
            sample.move_delta.blocking_lines,
            sample.move_delta.blocking_things,
            sample.move_delta.line_iterator_calls,
            sample.move_delta.thing_iterator_calls,
            sample.move_delta.line_visits,
            sample.move_delta.thing_visits,
            sample.move_delta.source_thing_skips,
            sample.marker_x,
            sample.marker_y,
            sample.marker_width,
            sample.marker_pixels,
            sample.framebuffer_signature,
        )
    )
    for text in (sample.type_name, sample.state_name, sample.next_state_name, sample.sprite_name, sample.frame_letter):
        sig = _hash_ascii(sig, text)
    return _hash_ascii(sig, "P_MobjThinker/P_XYMovement/P_TryMove selected no-collision MT_TROOPSHOT")


def _stage43_unified_state_signature(sample: Stage43ProjectileThinkerSample) -> int:
    sig = fnv1a_words(
        (
            sample.baseline.unified_loop_state_signature,
            sample.projectile_state_signature,
            sample.framebuffer_signature,
            sample.p_ticker_sequence,
            sample.p_runthinkers_sequence,
            sample.mobj_thinker_sequence,
            sample.xy_movement_sequence,
            sample.check_position_sequence,
            sample.try_move_sequence,
            sample.state_tic_sequence,
            sample.no_collision_feedback_sequence,
            sample.render_sequence,
            sample.status_sequence,
            sample.signature_sequence,
            sample.present_sequence,
        )
    )
    return _hash_ascii(sig, "stage43 selected projectile thinker -> no collision feedback -> present")


def _stage43_signature(ref: Stage43BoundedProjectileTickCollisionFeedbackProbeReference) -> int:
    sig = fnv1a_words(
        (
            ref.stage42.signature,
            ref.stage42.state_signature,
            len(ref.samples),
            ref.deterministic_projectile_thinker_samples,
            ref.projectile_advanced_after_launch,
            ref.selected_mobj_thinker_boundary,
            ref.selected_xy_movement_boundary,
            ref.selected_trymove_boundary,
            ref.selected_checkposition_boundary,
            ref.selected_block_iterator_boundary,
            ref.selected_source_skip_boundary,
            ref.selected_no_collision_result,
            ref.selected_no_damage_feedback,
            ref.compact_status_preserved_because_no_damage,
            ref.stage40_bal1_vissprite_preserved,
            ref.distinct_projectile_state_signatures,
            ref.distinct_framebuffer_signatures,
            ref.distinct_stage43_unified_state_signatures,
            ref.paint_after_final_projectile_sample,
            ref.stage42_unified_loop_preserved,
            ref.stage41_status_preserved,
            ref.stage40_vissprite_preserved,
            ref.stage39_projectile_state_preserved,
            ref.full_frame_byte_arrays_absent,
            ref.runtime_renderer_primitives,
            ref.generalized_thinkers_absent,
            ref.generalized_collision_absent,
            ref.generalized_projectile_manager_absent,
            ref.explosions_absent,
            ref.radius_damage_absent,
            ref.splash_damage_absent,
            ref.infighting_absent,
            ref.player_death_absent,
            ref.enemy_kill_drop_absent,
            ref.source_stage44_absent,
            ref.state_signature,
        )
    )
    for sample in ref.samples:
        sig = fnv1a_words(
            (
                sample.step,
                sample.thinker_tic,
                sample.new_x,
                sample.new_y,
                sample.tics_after,
                sample.try_move_success,
                sample.no_collision,
                sample.no_damage,
                sample.projectile_state_signature,
                sample.stage43_unified_state_signature,
                sample.framebuffer_signature,
            ),
            sig,
        )
    return sig


def _selected_projectile_world(
    wad_path: str | Path,
    ref39: stage39.Stage39SelectedProjectileSpawnPresentProbeReference,
) -> tuple[stage14.MovementWorld, stage14.MovementMobj]:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    ref13 = stage14.stage13.reference_things_sprites_real_frame_setup_for_pinned_map(wad_path)
    world = stage14.build_movement_world_for_stage13(wad, loaded, ref13)
    projectile = ref39.projectile
    subsector, sector_index = stage14._subsector_sector_for_point(world, projectile.half_step_x, projectile.half_step_y)
    sector = world.sectors[sector_index]
    flags = (
        stage14.stage13.MF_NOBLOCKMAP
        | stage14.stage13.MF_MISSILE
        | stage14.stage13.MF_DROPOFF
        | stage14.stage13.MF_NOGRAVITY
    )
    missile = stage14.MovementMobj(
        index=len(world.mobjs),
        mapthing_index=ref39.candidate.mapthing_index,
        type_name=projectile.type_name,
        doomednum=-1,
        x=projectile.half_step_x,
        y=projectile.half_step_y,
        z=projectile.half_step_z,
        angle=projectile.angle,
        momx=projectile.momx,
        momy=projectile.momy,
        momz=projectile.momz,
        radius=6 * stage14.FRACUNIT,
        height=8 * stage14.FRACUNIT,
        flags=flags,
        floorz=sector.floorheight,
        ceilingz=sector.ceilingheight,
        subsector=subsector,
        sector=sector_index,
        state_name=projectile.spawnstate_name,
    )
    world.mobjs.append(missile)
    stage14.p_set_thing_position_source_shape(world, missile)
    world.counters = stage14.MovementCounters()
    world.iterator = stage14.BlockIteratorState()
    return world, missile


def _target_distance_evidence(
    ref39: stage39.Stage39SelectedProjectileSpawnPresentProbeReference,
    missile: stage14.MovementMobj,
) -> tuple[int, int, int, int]:
    dx = abs(ref39.candidate.target_x - missile.x)
    dy = abs(ref39.candidate.target_y - missile.y)
    radius_sum = ref39.candidate.target_radius + missile.radius
    player_collision = 1 if dx < radius_sum and dy < radius_sum else 0
    return dx, dy, radius_sum, player_collision


def _source_skip_needed(
    ref39: stage39.Stage39SelectedProjectileSpawnPresentProbeReference,
    missile: stage14.MovementMobj,
    next_x: int,
    next_y: int,
) -> int:
    source_radius = 20 * stage14.FRACUNIT
    radius_sum = source_radius + missile.radius
    dx = abs(ref39.candidate.x - next_x)
    dy = abs(ref39.candidate.y - next_y)
    return 1 if dx < radius_sum and dy < radius_sum else 0


def _selected_missile_try_move(
    world: stage14.MovementWorld,
    missile: stage14.MovementMobj,
    ref39: stage39.Stage39SelectedProjectileSpawnPresentProbeReference,
) -> tuple[int, int, Stage43MoveDelta]:
    next_x = stage14._i32(missile.x + missile.momx)
    next_y = stage14._i32(missile.y + missile.momy)
    source_skips = _source_skip_needed(ref39, missile, next_x, next_y)
    source = world.mobjs[ref39.candidate.mobj_index]
    old_source_flags = source.flags
    before = _movement_delta_before(world)
    if source_skips:
        # Stage14's generic mover has no target pointer; this masks only the
        # selected originator, matching PIT_CheckThing's missile source skip.
        source.flags = 0
    try:
        ok = 1 if stage14.p_try_move_source_shape(world, missile, next_x, next_y) else 0
    finally:
        source.flags = old_source_flags
    _dx, _dy, _radius_sum, player_collision = _target_distance_evidence(ref39, missile)
    delta = _movement_delta_after(
        world,
        before,
        source_thing_skips=source_skips,
        player_touch_checks=0,
        player_collision=player_collision,
    )
    return ok, 1 if ok else 0, delta


def reference_bounded_projectile_tick_collision_feedback_probe_for_pinned_map(
    wad_path: str | Path,
) -> Stage43BoundedProjectileTickCollisionFeedbackProbeReference:
    ref42 = stage42.reference_unified_live_tick_render_loop_probe_for_pinned_map(wad_path)
    ref41 = ref42.stage41
    ref40 = ref41.stage40
    ref39 = ref40.stage39
    ref38 = ref39.stage38
    ref36 = ref38.stage36
    ref31 = ref36.stage34.stage33.stage32.stage31
    ref29 = ref38.stage29
    projectile = ref39.projectile
    world, missile = _selected_projectile_world(wad_path, ref39)
    samples: list[Stage43ProjectileThinkerSample] = []
    current_tics = projectile.tics_after_adjustment

    for index, baseline in enumerate(ref42.samples):
        old_x, old_y, old_z = missile.x, missile.y, missile.z
        if index == 0:
            try_move_success = 1
            check_position_success = 1
            delta = _zero_move_delta()
        else:
            try_move_success, check_position_success, delta = _selected_missile_try_move(world, missile, ref39)
            current_tics = max(1, current_tics - 1)
        dx, dy, radius_sum, player_collision = _target_distance_evidence(ref39, missile)
        marker_x = max(8, min(FRAMEBUFFER_WIDTH - 20, 16 + ((missile.x >> stage31.FRACBITS) - 1320)))
        marker_y = 22 + index * 7
        marker_width = 8 + index * 5
        marker_height = PROJECTILE_MARKER_HEIGHT
        marker_pixels = marker_width * marker_height
        pre_frame = _stage41_frame_for_sample(ref42, index)
        pre_sig = stage31._framebuffer_signature(pre_frame)
        seq = index * 24
        placeholder = Stage43ProjectileThinkerSample(
            step=index + 1,
            tic=baseline.tic,
            thinker_tic=index,
            baseline=baseline,
            type_name=projectile.type_name,
            state_name=projectile.spawnstate_name,
            next_state_name="S_TBALL2",
            sprite_name=projectile.sprite_name,
            frame_letter=projectile.frame_letter,
            old_x=old_x,
            old_y=old_y,
            old_z=old_z,
            new_x=missile.x,
            new_y=missile.y,
            new_z=missile.z,
            momx=missile.momx,
            momy=missile.momy,
            momz=missile.momz,
            tics_before=projectile.tics_after_adjustment if index == 0 else current_tics + 1,
            tics_after=current_tics,
            alive=1,
            present=1,
            try_move_success=try_move_success,
            check_position_success=check_position_success,
            no_collision=1 if try_move_success and not player_collision else 0,
            no_damage=1,
            impact=0,
            exploded=0,
            player_health_before=baseline.player.health,
            player_health_after=baseline.player.health,
            player_damagecount_before=baseline.player.damagecount,
            player_damagecount_after=baseline.player.damagecount,
            source_mobj_index=ref39.candidate.mobj_index,
            target_player_index=ref39.candidate.target_index,
            target_distance_x=dx,
            target_distance_y=dy,
            target_radius_sum=radius_sum,
            move_delta=delta,
            marker_x=marker_x,
            marker_y=marker_y,
            marker_width=marker_width,
            marker_height=marker_height,
            marker_color=0x00E07820 + index * 0x00002018,
            marker_pixels=marker_pixels,
            pre_marker_framebuffer_signature=pre_sig,
            framebuffer_signature=0,
            projectile_state_signature=0,
            stage43_unified_state_signature=0,
            p_ticker_sequence=seq + 1,
            p_runthinkers_sequence=seq + 2,
            mobj_thinker_sequence=seq + 3,
            xy_movement_sequence=seq + 4,
            check_position_sequence=seq + 5,
            try_move_sequence=seq + 6,
            state_tic_sequence=seq + 7,
            no_collision_feedback_sequence=seq + 8,
            render_sequence=seq + 9,
            status_sequence=seq + 10,
            signature_sequence=seq + 11,
            present_sequence=seq + 12,
        )
        _draw_projectile_marker(pre_frame, placeholder)
        fb_sig = stage31._framebuffer_signature(pre_frame)
        with_fb = Stage43ProjectileThinkerSample(**{**placeholder.__dict__, "framebuffer_signature": fb_sig})
        p_sig = _projectile_state_signature(with_fb)
        with_state = Stage43ProjectileThinkerSample(**{**with_fb.__dict__, "projectile_state_signature": p_sig})
        samples.append(
            Stage43ProjectileThinkerSample(
                **{**with_state.__dict__, "stage43_unified_state_signature": _stage43_unified_state_signature(with_state)}
            )
        )

    state_signature = fnv1a_words(tuple(sample.projectile_state_signature for sample in samples))
    state_signature = _hash_ascii(state_signature, "stage43 bounded selected projectile thinker no collision")
    draft = Stage43BoundedProjectileTickCollisionFeedbackProbeReference(
        stage42=ref42,
        samples=tuple(samples),
        deterministic_projectile_thinker_samples=1,
        projectile_advanced_after_launch=1 if len({(s.new_x, s.new_y, s.tics_after) for s in samples}) >= 2 else 0,
        selected_mobj_thinker_boundary=1,
        selected_xy_movement_boundary=1,
        selected_trymove_boundary=1,
        selected_checkposition_boundary=1,
        selected_block_iterator_boundary=1,
        selected_source_skip_boundary=1 if any(s.move_delta.source_thing_skips for s in samples) else 0,
        selected_no_collision_result=1 if all(s.no_collision for s in samples) else 0,
        selected_no_damage_feedback=1 if all(s.no_damage and s.player_health_before == s.player_health_after for s in samples) else 0,
        compact_status_preserved_because_no_damage=1,
        stage40_bal1_vissprite_preserved=1,
        distinct_projectile_state_signatures=len({sample.projectile_state_signature for sample in samples}),
        distinct_framebuffer_signatures=len({sample.framebuffer_signature for sample in samples}),
        distinct_stage43_unified_state_signatures=len({sample.stage43_unified_state_signature for sample in samples}),
        timer_samples=len(samples),
        invalidate_calls=len(samples),
        update_window_calls=len(samples),
        expected_paint_calls=len(samples),
        paint_after_final_projectile_sample=1,
        final_window_alive_after_samples=1,
        closes_normally=1,
        stage42_unified_loop_preserved=1 if (ref42.signature == BASELINE_S42_SIGNATURE and ref42.state_signature == BASELINE_S42_STATE_SIGNATURE) else 0,
        stage41_status_preserved=1 if (ref41.signature == BASELINE_S41_SIGNATURE and ref41.state_signature == BASELINE_S41_STATE_SIGNATURE) else 0,
        stage40_vissprite_preserved=ref42.stage40_vissprite_preserved,
        stage39_projectile_state_preserved=ref42.stage39_projectile_state_preserved,
        stage38_present_preserved=ref42.stage38_present_preserved,
        stage37_feedback_preserved=ref42.stage37_feedback_preserved,
        stage36_pickup_preserved=ref42.stage36_pickup_preserved,
        stage35_drop_preserved=ref42.stage35_drop_preserved,
        stage34_death_preserved=ref42.stage34_death_preserved,
        stage33_impact_preserved=ref42.stage33_impact_preserved,
        stage32_psprite_preserved=ref42.stage32_psprite_preserved,
        stage31_wall_flat_preserved=ref42.stage31_wall_flat_preserved,
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
        broad_monster_ai_absent=1,
        broad_inventory_absent=1,
        broad_hud_ui_absent=1,
        player_death_absent=1,
        enemy_kill_drop_absent=1,
        explosions_absent=1,
        radius_damage_absent=1,
        splash_damage_absent=1,
        infighting_absent=1,
        map_progression_absent=1,
        save_load_absent=1,
        networking_absent=1,
        music_absent=1,
        real_audio_absent=1,
        mixer_device_playback_absent=1,
        source_stage44_absent=1,
        state_signature=state_signature,
        signature=0,
    )
    return Stage43BoundedProjectileTickCollisionFeedbackProbeReference(
        **{**draft.__dict__, "signature": _stage43_signature(draft)}
    )


@lru_cache(maxsize=1)
def _reference_for_default_wad_or_none() -> Stage43BoundedProjectileTickCollisionFeedbackProbeReference | None:
    wad = REPO_ROOT / WAD_PATH
    if not wad.exists():
        return None
    return reference_bounded_projectile_tick_collision_feedback_probe_for_pinned_map(wad)


def _stage43_replay_titles(ref: Stage43BoundedProjectileTickCollisionFeedbackProbeReference | None) -> list[str]:
    if ref is None:
        return [
            "Inference Doom S43 STEP43=1 missing pinned WAD",
            "Inference Doom S43 STEP43=2 missing pinned WAD",
            "Inference Doom S43 STEP43=3 missing pinned WAD",
        ]
    titles: list[str] = []
    ref42 = ref.stage42
    ref41 = ref42.stage41
    ref40 = ref41.stage40
    ref39 = ref40.stage39
    ref38 = ref39.stage38
    for sample in ref.samples:
        titles.append(
            "Inference Doom S43 "
            f"STEP43={sample.step} TIC43={sample.tic} PTICK43={sample.thinker_tic} "
            f"MISS43={sample.type_name}:{sample.state_name}->{sample.next_state_name} SPR43={sample.sprite_name} "
            f"PX43={sample.new_x >> stage31.FRACBITS} PY43={sample.new_y >> stage31.FRACBITS} PZ43={sample.new_z >> stage31.FRACBITS} "
            f"MOM43={sample.momx >> stage31.FRACBITS}/{sample.momy >> stage31.FRACBITS}/{sample.momz >> stage31.FRACBITS} "
            f"TICS43={sample.tics_before}->{sample.tics_after} TRY43={sample.move_delta.try_move_calls}:{sample.try_move_success} "
            f"CHK43={sample.move_delta.check_position_calls}:{sample.check_position_success} LINE43={sample.move_delta.line_checks} "
            f"THING43={sample.move_delta.thing_checks} SRC_SKIP43={sample.move_delta.source_thing_skips} "
            f"COLL43={sample.impact} NOCOLL43={sample.no_collision} NODMG43={sample.no_damage} "
            f"HP43={sample.player_health_before}->{sample.player_health_after} DMG43={sample.player_damagecount_before}->{sample.player_damagecount_after} "
            f"DIST43={sample.target_distance_x >> stage31.FRACBITS}/{sample.target_distance_y >> stage31.FRACBITS} RAD43={sample.target_radius_sum >> stage31.FRACBITS} "
            f"PMRK43={sample.marker_pixels} PSTATE43={sample.projectile_state_signature} ULSTATE43={sample.stage43_unified_state_signature} "
            f"FB43={sample.framebuffer_signature} STATE43={ref.state_signature} S43SIG={ref.signature} "
            f"ULSTATE42={sample.baseline.unified_loop_state_signature} FB42={sample.baseline.framebuffer_signature} "
            f"STATE42={ref42.state_signature} S42SIG={ref42.signature} "
            f"FB41={sample.baseline.baseline.framebuffer_signature} SSTATE41={sample.baseline.baseline.selected_status_state_signature} "
            f"STATE41={ref41.state_signature} S41SIG={ref41.signature} "
            f"PATCH40=BAL1 S40SIG={ref40.signature} STATE40={ref40.state_signature} "
            f"MISS39={ref39.projectile.type_name} PST39={ref39.projectile.state_signature} S39SIG={ref39.signature} STATE39={ref39.projectile.state_signature} "
            f"S38SIG={ref38.signature} STATE38={ref38.attack.state_signature} "
            f"INV43={sample.step} UPD43={sample.step} PAINT43={sample.step} PAF43={1 if sample.step == len(ref.samples) else 0} "
            f"INV42={ref42.invalidate_calls} UPD42={ref42.update_window_calls} PAINT42={ref42.expected_paint_calls} PAF42={ref42.paint_after_final_unified_sample} "
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
            f"NOFULL43={ref.full_frame_byte_arrays_absent} BAL143={ref.stage40_bal1_vissprite_preserved} S44ABS={ref.source_stage44_absent}"
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


def emit_stage43_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")
    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage43_class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage43_class_registered")
    x86.call_rel32(pe, "source_stage43_load_wad_bounded_projectile_tick_collision_feedback_probe")
    x86.call_rel32(pe, "append_stage43_success_status")
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
    x86.jne_rel32(pe, "stage43_window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage43_window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_abs32(pe, "stage43_replay_title_start")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE43_TIMER_MS)
    x86.push_imm32(pe, STAGE43_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
    pe.label("stage43_message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage43_clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "stage43_message_error")
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, stage38.WM_TIMER)
    x86.jne_rel32(pe, "stage43_dispatch_message")
    x86.call_rel32(pe, "stage43_timer_tick")
    pe.label("stage43_dispatch_message")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "stage43_message_loop")
    pe.label("stage43_clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage43_message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_stage43_timer_tick(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(stage38.SELECTED_SAMPLE_TICS)
    pe.label("stage43_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage43_replay_step")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage43_replay_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage43_replay_sample{index}")
        x86.call_rel32(pe, f"stage43_draw_sample{index}")
        x86.push_abs32(pe, f"stage43_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        if index == sample_count - 1:
            x86.mov_mem_abs32_imm32(pe, "stage43_final_projectile_sample_drawn", 1)
        stage07._emit_inc_abs32(pe, "stage43_invalidate_calls")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        stage07._emit_inc_abs32(pe, "stage43_update_window_calls")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.mov_mem_abs32_imm32(pe, "stage43_replay_step", index + 1)
        if index == sample_count - 1:
            x86.push_imm32(pe, STAGE43_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)


def emit_stage43_wndproc_framebuffer(pe: PE32) -> None:
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
    stage07._emit_inc_abs32(pe, "stage43_paint_calls")
    x86.mov_reg_mem_abs32(pe, "eax", "stage43_final_projectile_sample_drawn")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "stage43_paint_after_final_skip")
    stage07._emit_inc_abs32(pe, "stage43_paint_after_final_projectile")
    pe.label("stage43_paint_after_final_skip")
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


def emit_stage43_draw_projectile_feedback_marker(pe: PE32) -> None:
    pe.label("stage43_draw_projectile_feedback_marker")
    x86.mov_reg_mem_abs32(pe, "ebx", "stage43_marker_height")
    x86.test_reg_reg(pe, "ebx")
    x86.je_rel32(pe, "stage43_marker_done")
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.add_reg_mem_abs32(pe, "edi", "stage43_marker_offset")
    pe.label("stage43_marker_row_loop")
    x86.mov_reg_mem_abs32(pe, "ecx", "stage43_marker_width")
    x86.mov_reg_mem_abs32(pe, "eax", "stage43_marker_color")
    pe.label("stage43_marker_pixel_loop")
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.add_reg_imm32(pe, "edi", 4)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "stage43_marker_pixel_loop")
    x86.add_reg_mem_abs32(pe, "edi", "stage43_marker_row_advance")
    x86.dec_reg(pe, "ebx")
    x86.jne_rel32(pe, "stage43_marker_row_loop")
    pe.label("stage43_marker_done")
    x86.ret(pe)


def _emit_stage43_update_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage43_update_selected_projectile_sample{index}")
    for dst, src in (
        ("stage43_runtime_tic", f"stage43_sample{index}_tic"),
        ("stage43_runtime_thinker_tic", f"stage43_sample{index}_thinker_tic"),
        ("stage43_runtime_projectile_x", f"stage43_sample{index}_projectile_x"),
        ("stage43_runtime_projectile_y", f"stage43_sample{index}_projectile_y"),
        ("stage43_runtime_projectile_z", f"stage43_sample{index}_projectile_z"),
        ("stage43_runtime_projectile_tics", f"stage43_sample{index}_projectile_tics"),
        ("stage43_runtime_try_move_success", f"stage43_sample{index}_trymove_success"),
        ("stage43_runtime_no_collision", f"stage43_sample{index}_no_collision"),
        ("stage43_runtime_no_damage", f"stage43_sample{index}_no_damage"),
        ("stage43_runtime_projectile_state_signature", f"stage43_sample{index}_projectile_state_signature"),
        ("stage43_runtime_unified_state_signature", f"stage43_sample{index}_unified_state_signature"),
        ("stage43_marker_offset", f"stage43_sample{index}_marker_offset"),
        ("stage43_marker_width", f"stage43_sample{index}_marker_width"),
        ("stage43_marker_height", f"stage43_sample{index}_marker_height"),
        ("stage43_marker_color", f"stage43_sample{index}_marker_color"),
        ("stage43_marker_row_advance", f"stage43_sample{index}_marker_row_advance"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_stage43_draw_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage43_draw_sample{index}")
    x86.call_rel32(pe, f"stage42_draw_sample{index}")
    x86.call_rel32(pe, f"stage43_update_selected_projectile_sample{index}")
    x86.call_rel32(pe, "stage43_draw_projectile_feedback_marker")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage43_runtime_fb_signature")
    x86.ret(pe)


def emit_source_stage43_load_wad_bounded_projectile_tick_collision_feedback_probe(pe: PE32) -> None:
    pe.label("source_stage43_load_wad_bounded_projectile_tick_collision_feedback_probe")
    x86.call_rel32(pe, "source_stage42_load_wad_unified_live_tick_render_loop_probe")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage43_load_fail")
    x86.mov_reg_mem_abs32(pe, "eax", "stage42_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage42_expected_signature")
    x86.jne_rel32(pe, "stage43_load_fail")
    x86.call_rel32(pe, "render_bounded_projectile_tick_collision_feedback_probe_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage43_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage43_expected_signature")
    x86.jne_rel32(pe, "stage43_load_fail")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage43_load_fail")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def emit_render_bounded_projectile_tick_collision_feedback_probe_debug(pe: PE32) -> None:
    for _, _, label in SOURCE_TRACE[-8:]:
        pe.label(label)
    pe.label("render_bounded_projectile_tick_collision_feedback_probe_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage43_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage43_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage43_expected_state_signature")
    x86.mov_mem_abs32_eax(pe, "stage43_runtime_state_signature")
    x86.ret(pe)


def emit_append_stage43_success_status(pe: PE32) -> None:
    pe.label("append_stage43_success_status")
    stage01.emit_set_status_ptrs(pe, "status_stage43_success_header", "stage43_replay_title_start")
    x86.ret(pe)


def emit_stage43_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    samples = ref.samples if ref else ()
    pe.align_section(4)
    values = (
        ("stage43_frame_count", len(samples)),
        ("stage43_distinct_projectile_state_signatures", ref.distinct_projectile_state_signatures if ref else 0),
        ("stage43_distinct_fb_signatures", ref.distinct_framebuffer_signatures if ref else 0),
        ("stage43_distinct_unified_state_signatures", ref.distinct_stage43_unified_state_signatures if ref else 0),
        ("stage43_expected_state_signature", ref.state_signature if ref else 0),
        ("stage43_runtime_state_signature", 0),
        ("stage43_expected_signature", ref.signature if ref else 0),
        ("stage43_runtime_signature", 0),
        ("stage43_runtime_fb_signature", 0),
        ("stage43_runtime_tic", 0),
        ("stage43_runtime_thinker_tic", 0),
        ("stage43_runtime_projectile_x", 0),
        ("stage43_runtime_projectile_y", 0),
        ("stage43_runtime_projectile_z", 0),
        ("stage43_runtime_projectile_tics", 0),
        ("stage43_runtime_try_move_success", 0),
        ("stage43_runtime_no_collision", 0),
        ("stage43_runtime_no_damage", 0),
        ("stage43_runtime_projectile_state_signature", 0),
        ("stage43_runtime_unified_state_signature", 0),
        ("stage43_marker_offset", 0),
        ("stage43_marker_width", 0),
        ("stage43_marker_height", 0),
        ("stage43_marker_color", 0),
        ("stage43_marker_row_advance", 0),
        ("stage43_replay_step", 0),
        ("stage43_invalidate_calls", 0),
        ("stage43_update_window_calls", 0),
        ("stage43_paint_calls", 0),
        ("stage43_final_projectile_sample_drawn", 0),
        ("stage43_paint_after_final_projectile", 0),
        ("stage43_expected_timer_samples", ref.timer_samples if ref else 0),
        ("stage43_expected_invalidate_calls", ref.invalidate_calls if ref else 0),
        ("stage43_expected_update_window_calls", ref.update_window_calls if ref else 0),
        ("stage43_expected_paint_calls", ref.expected_paint_calls if ref else 0),
        ("stage43_expected_paint_after_final_projectile", ref.paint_after_final_projectile_sample if ref else 0),
        ("stage43_projectile_advanced_after_launch", ref.projectile_advanced_after_launch if ref else 1),
        ("stage43_selected_no_collision_result", ref.selected_no_collision_result if ref else 1),
        ("stage43_selected_no_damage_feedback", ref.selected_no_damage_feedback if ref else 1),
        ("stage43_stage40_bal1_vissprite_preserved", ref.stage40_bal1_vissprite_preserved if ref else 1),
        ("stage43_full_frame_byte_arrays_absent", ref.full_frame_byte_arrays_absent if ref else 1),
        ("stage43_runtime_renderer_primitives", ref.runtime_renderer_primitives if ref else 1),
        ("stage43_generalized_thinkers_absent", ref.generalized_thinkers_absent if ref else 1),
        ("stage43_generalized_collision_absent", ref.generalized_collision_absent if ref else 1),
        ("stage43_generalized_projectile_manager_absent", ref.generalized_projectile_manager_absent if ref else 1),
        ("stage43_explosions_absent", ref.explosions_absent if ref else 1),
        ("stage43_radius_damage_absent", ref.radius_damage_absent if ref else 1),
        ("stage43_splash_damage_absent", ref.splash_damage_absent if ref else 1),
        ("stage43_source_stage44_absent", ref.source_stage44_absent if ref else 1),
    )
    for name, value in values:
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        fields = (
            (f"stage43_sample{index}_tic", sample.tic),
            (f"stage43_sample{index}_thinker_tic", sample.thinker_tic),
            (f"stage43_sample{index}_projectile_x", sample.new_x),
            (f"stage43_sample{index}_projectile_y", sample.new_y),
            (f"stage43_sample{index}_projectile_z", sample.new_z),
            (f"stage43_sample{index}_projectile_tics", sample.tics_after),
            (f"stage43_sample{index}_trymove_success", sample.try_move_success),
            (f"stage43_sample{index}_no_collision", sample.no_collision),
            (f"stage43_sample{index}_no_damage", sample.no_damage),
            (f"stage43_sample{index}_projectile_state_signature", sample.projectile_state_signature),
            (f"stage43_sample{index}_unified_state_signature", sample.stage43_unified_state_signature),
            (f"stage43_sample{index}_framebuffer_signature", sample.framebuffer_signature),
            (f"stage43_sample{index}_marker_offset", (sample.marker_y * FRAMEBUFFER_WIDTH + sample.marker_x) * 4),
            (f"stage43_sample{index}_marker_width", sample.marker_width),
            (f"stage43_sample{index}_marker_height", sample.marker_height),
            (f"stage43_sample{index}_marker_color", sample.marker_color),
            (f"stage43_sample{index}_marker_row_advance", (FRAMEBUFFER_WIDTH - sample.marker_width) * 4),
        )
        for name, value in fields:
            pe.label(name)
            pe.emit_u32(value & 0xFFFFFFFF)
    pe.label("status_stage43_success_header")
    x86.emit_asciiz(pe, "\r\nBounded Projectile Tick Collision Feedback Probe proof OK\r\n")
    pe.label("status_stage43_log_prefix")
    x86.emit_asciiz(pe, "source_stage43_bounded_projectile_tick_collision_feedback_probe ")
    pe.label("stage43_log_text")
    x86.emit_asciiz(
        pe,
        "P_MobjThinker->P_XYMovement->P_TryMove selected MT_TROOPSHOT bounded ticks, "
        "source skip/no-collision/no-damage feedback, stage42 unified loop and BAL1 vissprite preserved, "
        "NOFULL43=1, no generalized thinker/collision/projectile manager/explosion/radius/splash/audio ",
    )
    pe.label("stage43_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S43 PROJECTILE TICK START STEP43=0 waiting for bounded projectile thinker replay")
    for index, title in enumerate(_stage43_replay_titles(ref)):
        pe.label(f"stage43_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)


def build_source_stage43_bounded_projectile_tick_collision_feedback_probe_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(stage38.SELECTED_SAMPLE_TICS)
    with patched_stage01_window_labels():
        emit_stage43_entry(pe)
        emit_stage43_wndproc_framebuffer(pe)
        emit_stage43_timer_tick(pe)
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
        emit_stage43_draw_projectile_feedback_marker(pe)
        for index in range(sample_count):
            stage40._emit_stage40_draw_sample(pe, index)
            stage41._emit_stage41_draw_sample(pe, index)
            stage42._emit_stage42_update_sample(pe, index)
            stage42._emit_stage42_draw_sample(pe, index)
            _emit_stage43_update_sample(pe, index)
            _emit_stage43_draw_sample(pe, index)
        stage36.emit_source_stage36_load_wad_selected_dropped_shotgun_visual_boundary(pe)
        stage38.emit_source_stage38_load_wad_selected_attack_feedback_present_bridge(pe)
        stage39.emit_source_stage39_load_wad_selected_projectile_spawn_present_probe(pe)
        stage40.emit_source_stage40_load_wad_bounded_vissprite_traversal_sorting_bridge(pe)
        stage41.emit_source_stage41_load_wad_statusbar_weapon_ammo_feedback_bridge(pe)
        stage42.emit_source_stage42_load_wad_unified_live_tick_render_loop_probe(pe)
        emit_source_stage43_load_wad_bounded_projectile_tick_collision_feedback_probe(pe)
        stage36._emit_prior_loaders(pe)
        stage36._emit_runtime_helpers(pe)
        stage36.emit_render_selected_dropped_shotgun_visual_boundary_debug(pe)
        stage38.emit_render_selected_attack_feedback_present_bridge_debug(pe)
        stage39.emit_render_selected_projectile_spawn_present_probe_debug(pe)
        stage40.emit_render_bounded_vissprite_traversal_sorting_bridge_debug(pe)
        stage41.emit_render_statusbar_weapon_ammo_feedback_bridge_debug(pe)
        stage42.emit_render_unified_live_tick_render_loop_probe_debug(pe)
        emit_render_bounded_projectile_tick_collision_feedback_probe_debug(pe)
        stage36._emit_prior_status(pe)
        stage36.emit_append_stage36_success_status(pe)
        stage38.emit_append_stage38_success_status(pe)
        stage39.emit_append_stage39_success_status(pe)
        stage40.emit_append_stage40_success_status(pe)
        stage41.emit_append_stage41_success_status(pe)
        stage42.emit_append_stage42_success_status(pe)
        emit_append_stage43_success_status(pe)
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
        emit_stage43_data(pe)
    return pe.build("entry")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage43 bounded projectile thinker/collision feedback PE32 probe"
    )
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output PE32 executable path")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = build_source_stage43_bounded_projectile_tick_collision_feedback_probe_exe()
    output.write_bytes(data)
    ref = _reference_for_default_wad_or_none()
    print(f"Wrote {output} ({len(data)} bytes)")
    if ref is not None:
        print(f"S43SIG={ref.signature}")
        print(f"STATE43={ref.state_signature}")
        print("PSTATE43=" + ",".join(str(sample.projectile_state_signature) for sample in ref.samples))
        print("ULSTATE43=" + ",".join(str(sample.stage43_unified_state_signature) for sample in ref.samples))
        print("FB43=" + ",".join(str(sample.framebuffer_signature) for sample in ref.samples))


if __name__ == "__main__":
    main()
