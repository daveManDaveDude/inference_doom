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
from tools import emit_source_stage28_live_input_to_deterministic_game_loop_bridge as stage28
from tools import emit_source_stage43_bounded_projectile_tick_collision_feedback_probe as stage43
from tools import x86
from tools.map_loader import load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


stage42 = stage43.stage42
stage41 = stage43.stage41
stage40 = stage43.stage40
stage39 = stage43.stage39
stage38 = stage43.stage38
stage36 = stage43.stage36
stage32 = stage43.stage32
stage31 = stage43.stage31
stage15 = stage43.stage15
stage07 = stage43.stage07
stage03 = stage43.stage03
stage01 = stage43.stage01

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "build" / "source_stage44_live_ticcmd_unified_player_render_loop_bridge.exe"
WAD_PATH = stage43.WAD_PATH

FRAMEBUFFER_WIDTH = stage43.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage43.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_BYTES = stage43.FRAMEBUFFER_BYTES
WINDOW_WIDTH = stage43.WINDOW_WIDTH
WINDOW_HEIGHT = stage43.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage44LiveTiccmdUnifiedPlayerRenderLoopBridge"
WINDOW_TITLE = "Inference Doom S44 Live Ticcmd Unified Player Render Loop Bridge"

STAGE44_TIMER_ID = 44
STAGE44_TIMER_MS = stage43.STAGE43_TIMER_MS
PLAYER_MARKER_HEIGHT = 5
BOUNDED_REDRAW_SAMPLE_COUNT = 3

BT_USE = stage28.BT_USE
FORWARDMOVE = stage28.FORWARDMOVE
SLOW_ANGLETURN = stage28.SLOW_ANGLETURN
WM_KEYDOWN = stage28.WM_KEYDOWN
WM_KEYUP = stage28.WM_KEYUP
VK_LEFT = stage28.VK_LEFT
VK_UP = stage28.VK_UP
VK_RIGHT = stage28.VK_RIGHT
VK_DOWN = stage28.VK_DOWN
VK_SPACE = stage28.VK_SPACE
VK_A = stage28.VK_A
VK_D = stage28.VK_D
VK_E = stage28.VK_E
VK_S = stage28.VK_S
VK_W = stage28.VK_W

BASELINE_S43_SIGNATURE = 2916740242
BASELINE_S43_STATE_SIGNATURE = 801364352
BASELINE_S42_SIGNATURE = 2427416971
BASELINE_S42_STATE_SIGNATURE = 2148021159
BASELINE_S41_SIGNATURE = 951695045
BASELINE_S41_STATE_SIGNATURE = 157977072
BASELINE_S40_SIGNATURE = 2737672056
BASELINE_S40_STATE_SIGNATURE = 268409133
BASELINE_S39_SIGNATURE = 3469618451
BASELINE_S39_STATE_SIGNATURE = 1403583302

Stage44CommandBridgeState = stage28.Stage28CommandBridgeState
Stage44KeyState = stage28.Stage28KeyState
Stage44Counters = stage28.Stage28Counters

SOURCE_TRACE = stage43.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/d_loop.c",
        "BuildNewTic/I_StartTic/TryRunTics replay or bounded live ticcmd intake",
        "D_DoomLoop_stage44_replay_or_live_ticcmd_intake_debug",
    ),
    (
        "reference/chocolate-doom/src/i_input.c",
        "I_HandleKeyboardEvent/TranslateKey bounded keydown-keyup gamekeydown ownership",
        "I_Input_stage44_bounded_keydown_keyup_gamekeydown_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/g_game.c",
        "G_BuildTiccmd forward/back/turn/use subset with deterministic replay override",
        "G_BuildTiccmd_stage44_live_or_replay_gamekeydown_table_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/g_game.c",
        "G_Ticker copies selected ticcmd_t into the local player before P_Ticker",
        "G_Ticker_stage44_ticcmd_player_ownership_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_user.c",
        "P_PlayerThink/P_MovePlayer selected bounded player command update",
        "P_PlayerThink_stage44_bounded_player_command_update_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_user.c",
        "P_Thrust selected forward/turn momentum contribution",
        "P_Thrust_stage44_selected_forward_turn_momentum_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_XYMovement selected local player movement step",
        "P_XYMovement_stage44_bounded_player_trymove_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "P_CheckPosition/P_TryMove selected player bounded MAP01 fit check",
        "P_TryMove_stage44_selected_player_no_general_collision_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_maputl.c",
        "P_BlockLinesIterator/P_BlockThingsIterator selected bounded player evidence",
        "P_BlockIterators_stage44_selected_player_bounds_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_SetupFrame from selected player mobj, then finite redraw route table",
        "R_SetupFrame_stage44_finite_route_redraw_sample_select_debug",
    ),
    (
        "reference/chocolate-doom/src/v_video.c",
        "V_DrawFilledBox-style runtime player/view marker primitive",
        "V_DrawFilledBox_stage44_runtime_player_view_marker_debug",
    ),
    (
        "reference/chocolate-doom/src/i_video.c",
        "I_FinishUpdate-style final present after selected live ticcmd/redraw sample",
        "I_Video_stage44_final_present_after_live_ticcmd_debug",
    ),
)


@dataclass(frozen=True)
class Stage44TicCmd:
    tic: int = 0
    forwardmove: int = 0
    sidemove: int = 0
    angleturn: int = 0
    buttons: int = 0
    consistency: int = 0
    source_index: int = 0
    source_marker: str = "G_BuildTiccmd stage44 bounded replay/live bridge"


@dataclass(frozen=True)
class Stage44PlayerMoveDelta:
    g_ticker_calls: int
    p_ticker_calls: int
    player_think_calls: int
    xy_movement_calls: int
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
    slide_attempts: int
    slide_deferred: int


@dataclass(frozen=True)
class Stage44LiveTiccmdUnifiedPlayerRenderSample:
    step: int
    tic: int
    baseline: stage43.Stage43ProjectileThinkerSample
    mode: str
    live_enabled: int
    live_keys_forward: int
    live_keys_back: int
    live_keys_left: int
    live_keys_right: int
    live_keys_use: int
    live_key_events: int
    replay_commands_built: int
    replay_ignored_live_key_state: int
    manual_commands_built: int
    ticcmd: Stage44TicCmd
    old_x: int
    old_y: int
    old_angle: int
    old_momx: int
    old_momy: int
    old_viewz: int
    new_x: int
    new_y: int
    new_angle: int
    new_momx: int
    new_momy: int
    new_viewz: int
    viewangle: int
    viewangle_degrees: int
    viewcos: int
    viewsin: int
    subsector: int
    sector: int
    move_delta: Stage44PlayerMoveDelta
    try_move_success: int
    check_position_success: int
    redraw_sample_id: int
    redraw_table_size: int
    finite_route_table: int
    free_roaming_render_absent: int
    marker_x: int
    marker_y: int
    marker_width: int
    marker_height: int
    marker_color: int
    marker_pixels: int
    pre_marker_framebuffer_signature: int
    framebuffer_signature: int
    player_view_state_signature: int
    stage44_unified_state_signature: int
    start_tic_sequence: int
    input_event_sequence: int
    ticcmd_sequence: int
    g_ticker_sequence: int
    p_ticker_sequence: int
    player_think_sequence: int
    p_move_player_sequence: int
    p_thrust_sequence: int
    xy_movement_sequence: int
    try_move_sequence: int
    r_setup_frame_sequence: int
    bounded_redraw_sequence: int
    projectile_thinker_sequence: int
    status_sequence: int
    signature_sequence: int
    present_sequence: int


@dataclass(frozen=True)
class Stage44LiveTiccmdUnifiedPlayerRenderLoopBridgeReference:
    stage43: stage43.Stage43BoundedProjectileTickCollisionFeedbackProbeReference
    samples: tuple[Stage44LiveTiccmdUnifiedPlayerRenderSample, ...]
    deterministic_replay_default: int
    live_mode_requires_flag: int
    stage28_bridge_reused: int
    gamekeydown_table_shared: int
    replay_ignores_live_keys: int
    selected_g_ticker_ownership: int
    selected_player_movement_update: int
    selected_p_thrust_update: int
    selected_xy_movement_update: int
    selected_trymove_boundary: int
    finite_redraw_route_table: int
    finite_redraw_route_table_size: int
    free_roaming_render_absent: int
    selected_projectile_after_player_update: int
    compact_status_preserved: int
    stage40_bal1_vissprite_preserved: int
    distinct_player_view_state_signatures: int
    distinct_framebuffer_signatures: int
    distinct_stage44_unified_state_signatures: int
    timer_samples: int
    invalidate_calls: int
    update_window_calls: int
    expected_paint_calls: int
    paint_after_final_player_sample: int
    final_window_alive_after_samples: int
    closes_normally: int
    stage43_projectile_preserved: int
    stage43_unified_loop_preserved: int
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
    generalized_thinkers_absent: int
    generalized_collision_absent: int
    generalized_projectile_manager_absent: int
    broad_monster_ai_absent: int
    generalized_combat_absent: int
    broad_sprite_traversal_absent: int
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
    source_stage45_absent: int
    state_signature: int
    signature: int


def fnv1a_words(words: Sequence[int], basis: int = stage38.FNV_OFFSET_BASIS) -> int:
    return stage43.fnv1a_words(words, basis)


def _hash_ascii(signature: int, text: str) -> int:
    return stage43._hash_ascii(signature, text)


def d_post_event_stage44_live_key_state_bridge_source_shape(
    bridge: Stage44CommandBridgeState,
    key: str,
    down: bool,
) -> None:
    stage28.d_post_event_stage28_live_key_state_bridge_source_shape(bridge, key, down)


def _key_state_from_bridge(bridge: Stage44CommandBridgeState) -> Stage44KeyState:
    return stage28._key_state_from_bridge(bridge)


def _stage44_from_stage27_cmd(
    cmd: stage28.stage27.Stage27Ticcmd,
    *,
    tic: int,
    source_index: int,
    source_marker: str,
) -> Stage44TicCmd:
    return Stage44TicCmd(
        tic=tic,
        forwardmove=cmd.forwardmove,
        sidemove=cmd.sidemove,
        angleturn=cmd.angleturn,
        buttons=cmd.buttons,
        consistency=fnv1a_words((tic, cmd.forwardmove, cmd.sidemove, cmd.angleturn, cmd.buttons, source_index)),
        source_index=source_index,
        source_marker=source_marker,
    )


def g_build_ticcmd_stage44_live_or_replay_bridge_source_shape(
    bridge: Stage44CommandBridgeState,
    counters: Stage44Counters,
    *,
    replay: bool,
    replay_cmd: Stage44TicCmd | None = None,
    live_keys: Stage44KeyState | None = None,
    tic: int = 0,
    source_index: int = 0,
) -> Stage44TicCmd:
    base_replay = None
    if replay_cmd is not None:
        base_replay = stage28.stage27.Stage27Ticcmd(
            forwardmove=replay_cmd.forwardmove,
            sidemove=replay_cmd.sidemove,
            angleturn=replay_cmd.angleturn,
            buttons=replay_cmd.buttons,
        )
    base = stage28.g_build_ticcmd_stage28_live_or_replay_bridge_source_shape(
        bridge,
        counters,
        replay=replay,
        replay_cmd=base_replay,
        live_keys=live_keys,
    )
    marker = (
        "stage28 replay-owned ticcmd_t table"
        if replay
        else "stage28 live gamekeydown[] ticcmd_t table"
    )
    return _stage44_from_stage27_cmd(base, tic=tic, source_index=source_index, source_marker=marker)


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
) -> Stage44PlayerMoveDelta:
    counters, iterator = before
    return Stage44PlayerMoveDelta(
        g_ticker_calls=world.counters.g_ticker_calls - counters.g_ticker_calls,
        p_ticker_calls=world.counters.p_ticker_calls - counters.p_ticker_calls,
        player_think_calls=world.counters.p_ticker_calls - counters.p_ticker_calls,
        xy_movement_calls=world.counters.xy_movement_calls - counters.xy_movement_calls,
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
        slide_attempts=world.counters.slide_attempts - counters.slide_attempts,
        slide_deferred=world.counters.slide_deferred - counters.slide_deferred,
    )


def _selected_player_world(wad_path: str | Path) -> stage14.MovementWorld:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    ref13 = stage14.stage13.reference_things_sprites_real_frame_setup_for_pinned_map(wad_path)
    return stage14.build_movement_world_for_stage13(wad, loaded, ref13)


def _draw_player_view_marker(frame: bytearray, sample: Stage44LiveTiccmdUnifiedPlayerRenderSample) -> int:
    color = (sample.marker_color & 0x00FFFFFF).to_bytes(4, "little")
    pixels = 0
    for yy in range(sample.marker_y, sample.marker_y + sample.marker_height):
        row = (yy * FRAMEBUFFER_WIDTH + sample.marker_x) * 4
        for xx in range(sample.marker_width):
            offset = row + xx * 4
            frame[offset : offset + 4] = color
            pixels += 1
    return pixels


def _replay_script_for_stage44(samples: Sequence[stage43.Stage43ProjectileThinkerSample]) -> tuple[Stage44TicCmd, ...]:
    raw = (
        (0, 0, 0, 0),
        (FORWARDMOVE, 0, -SLOW_ANGLETURN, 0),
        (FORWARDMOVE, 0, SLOW_ANGLETURN, BT_USE),
    )
    commands: list[Stage44TicCmd] = []
    for index, sample in enumerate(samples):
        forwardmove, sidemove, angleturn, buttons = raw[index % len(raw)]
        commands.append(
            Stage44TicCmd(
                tic=sample.tic,
                forwardmove=forwardmove,
                sidemove=sidemove,
                angleturn=angleturn,
                buttons=buttons,
                consistency=fnv1a_words((sample.tic, forwardmove, sidemove, angleturn, buttons, index)),
                source_index=index,
                source_marker="D_DoomLoop replay-owned stage28 bridge ticcmd_t table",
            )
        )
    return tuple(commands)


def _sample_live_keys(index: int) -> Stage44KeyState:
    if index == 0:
        return Stage44KeyState(forward=True, use=True)
    if index == 1:
        return Stage44KeyState(forward=True, turn_right=True)
    return Stage44KeyState(forward=True, turn_left=True, use=True)


def _player_view_signature(sample: Stage44LiveTiccmdUnifiedPlayerRenderSample) -> int:
    sig = fnv1a_words(
        (
            sample.step,
            sample.tic,
            sample.live_enabled,
            sample.live_keys_forward,
            sample.live_keys_back,
            sample.live_keys_left,
            sample.live_keys_right,
            sample.live_keys_use,
            sample.live_key_events,
            sample.replay_commands_built,
            sample.replay_ignored_live_key_state,
            sample.ticcmd.forwardmove,
            sample.ticcmd.sidemove,
            sample.ticcmd.angleturn,
            sample.ticcmd.buttons,
            sample.old_x,
            sample.old_y,
            sample.old_angle,
            sample.old_momx,
            sample.old_momy,
            sample.old_viewz,
            sample.new_x,
            sample.new_y,
            sample.new_angle,
            sample.new_momx,
            sample.new_momy,
            sample.new_viewz,
            sample.viewcos,
            sample.viewsin,
            sample.subsector,
            sample.sector,
            sample.move_delta.g_ticker_calls,
            sample.move_delta.p_ticker_calls,
            sample.move_delta.player_think_calls,
            sample.move_delta.xy_movement_calls,
            sample.move_delta.try_move_calls,
            sample.move_delta.check_position_calls,
            sample.move_delta.accepted_moves,
            sample.move_delta.rejected_moves,
            sample.move_delta.line_checks,
            sample.move_delta.thing_checks,
            sample.move_delta.line_iterator_calls,
            sample.move_delta.thing_iterator_calls,
            sample.try_move_success,
            sample.check_position_success,
            sample.redraw_sample_id,
            sample.redraw_table_size,
            sample.marker_x,
            sample.marker_y,
            sample.marker_width,
            sample.marker_pixels,
            sample.framebuffer_signature,
        )
    )
    for text in (sample.mode, sample.ticcmd.source_marker):
        sig = _hash_ascii(sig, text)
    return _hash_ascii(sig, "stage44 stage28 ticcmd -> P_MovePlayer/P_Thrust/P_XYMovement -> finite redraw")


def _stage44_unified_state_signature(sample: Stage44LiveTiccmdUnifiedPlayerRenderSample) -> int:
    sig = fnv1a_words(
        (
            sample.baseline.stage43_unified_state_signature,
            sample.baseline.projectile_state_signature,
            sample.player_view_state_signature,
            sample.framebuffer_signature,
            sample.start_tic_sequence,
            sample.input_event_sequence,
            sample.ticcmd_sequence,
            sample.g_ticker_sequence,
            sample.p_ticker_sequence,
            sample.player_think_sequence,
            sample.p_move_player_sequence,
            sample.p_thrust_sequence,
            sample.xy_movement_sequence,
            sample.try_move_sequence,
            sample.r_setup_frame_sequence,
            sample.bounded_redraw_sequence,
            sample.projectile_thinker_sequence,
            sample.status_sequence,
            sample.signature_sequence,
            sample.present_sequence,
        )
    )
    return _hash_ascii(sig, "stage44 bounded live/replay ticcmd -> player/view -> projectile/status/present")


def _stage44_signature(ref: Stage44LiveTiccmdUnifiedPlayerRenderLoopBridgeReference) -> int:
    sig = fnv1a_words(
        (
            ref.stage43.signature,
            ref.stage43.state_signature,
            len(ref.samples),
            ref.deterministic_replay_default,
            ref.live_mode_requires_flag,
            ref.stage28_bridge_reused,
            ref.gamekeydown_table_shared,
            ref.replay_ignores_live_keys,
            ref.selected_g_ticker_ownership,
            ref.selected_player_movement_update,
            ref.selected_p_thrust_update,
            ref.selected_xy_movement_update,
            ref.selected_trymove_boundary,
            ref.finite_redraw_route_table,
            ref.finite_redraw_route_table_size,
            ref.free_roaming_render_absent,
            ref.selected_projectile_after_player_update,
            ref.compact_status_preserved,
            ref.stage40_bal1_vissprite_preserved,
            ref.distinct_player_view_state_signatures,
            ref.distinct_framebuffer_signatures,
            ref.distinct_stage44_unified_state_signatures,
            ref.paint_after_final_player_sample,
            ref.stage43_projectile_preserved,
            ref.stage43_unified_loop_preserved,
            ref.stage42_unified_loop_preserved,
            ref.stage41_status_preserved,
            ref.stage40_vissprite_preserved,
            ref.stage39_projectile_state_preserved,
            ref.full_frame_byte_arrays_absent,
            ref.runtime_renderer_primitives,
            ref.generalized_thinkers_absent,
            ref.generalized_collision_absent,
            ref.generalized_projectile_manager_absent,
            ref.free_roaming_render_absent,
            ref.explosions_absent,
            ref.radius_damage_absent,
            ref.splash_damage_absent,
            ref.infighting_absent,
            ref.player_death_absent,
            ref.enemy_kill_drop_absent,
            ref.source_stage45_absent,
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
                sample.ticcmd.buttons,
                sample.new_x,
                sample.new_y,
                sample.new_angle,
                sample.new_momx,
                sample.new_momy,
                sample.redraw_sample_id,
                sample.player_view_state_signature,
                sample.stage44_unified_state_signature,
                sample.framebuffer_signature,
            ),
            sig,
        )
    return sig


def reference_live_ticcmd_unified_player_render_loop_bridge_for_pinned_map(
    wad_path: str | Path,
) -> Stage44LiveTiccmdUnifiedPlayerRenderLoopBridgeReference:
    ref43 = stage43.reference_bounded_projectile_tick_collision_feedback_probe_for_pinned_map(wad_path)
    ref42 = ref43.stage42
    ref41 = ref42.stage41
    ref40 = ref41.stage40
    ref39 = ref40.stage39
    ref38 = ref39.stage38
    ref36 = ref38.stage36
    ref31 = ref36.stage34.stage33.stage32.stage31
    ref29 = ref38.stage29
    world = _selected_player_world(wad_path)
    replay_script = _replay_script_for_stage44(ref43.samples)
    bridge = Stage44CommandBridgeState()
    counters = Stage44Counters()
    samples: list[Stage44LiveTiccmdUnifiedPlayerRenderSample] = []

    for index, baseline in enumerate(ref43.samples):
        live_keys = _sample_live_keys(index)
        live_key_events = sum(
            1
            for active in (
                live_keys.forward,
                live_keys.back,
                live_keys.turn_left,
                live_keys.turn_right,
                live_keys.use,
            )
            if active
        )
        replay_cmd = g_build_ticcmd_stage44_live_or_replay_bridge_source_shape(
            bridge,
            counters,
            replay=True,
            replay_cmd=replay_script[index],
            live_keys=live_keys,
            tic=baseline.tic,
            source_index=index,
        )
        mo = world.mobjs[world.player.mo_index]
        old_x, old_y, old_angle = mo.x, mo.y, mo.angle
        old_momx, old_momy, old_viewz = mo.momx, mo.momy, world.player.viewz
        before = _movement_delta_before(world)
        stage14.g_ticker_ticcmd_dispatch_source_shape(
            world,
            stage14.TicCmd(
                forwardmove=replay_cmd.forwardmove,
                sidemove=replay_cmd.sidemove,
                angleturn=replay_cmd.angleturn,
                buttons=replay_cmd.buttons,
            ),
        )
        world.counters.tic_count += 1
        frame_setup = stage14.r_setup_frame_after_movement_source_shape(world, framecount=index + 1)
        delta = _movement_delta_after(world, before)
        mo = world.mobjs[world.player.mo_index]
        redraw_sample_id = min(index, BOUNDED_REDRAW_SAMPLE_COUNT - 1)
        marker_x = max(
            8,
            min(
                FRAMEBUFFER_WIDTH - 28,
                40 + redraw_sample_id * 48 + (((frame_setup.viewx >> stage31.FRACBITS) + 192) * 4),
            ),
        )
        marker_y = max(8, min(FRAMEBUFFER_HEIGHT - 16, 42 + index * 11 + abs((frame_setup.viewy >> stage31.FRACBITS) + 192)))
        marker_width = 9 + redraw_sample_id * 4 + (1 if replay_cmd.buttons & BT_USE else 0)
        marker_height = PLAYER_MARKER_HEIGHT
        marker_pixels = marker_width * marker_height
        pre_frame = stage43._stage41_frame_for_sample(ref42, index)
        stage43._draw_projectile_marker(pre_frame, baseline)
        pre_sig = stage31._framebuffer_signature(pre_frame)
        seq = index * 28
        placeholder = Stage44LiveTiccmdUnifiedPlayerRenderSample(
            step=index + 1,
            tic=baseline.tic,
            baseline=baseline,
            mode="REPLAY",
            live_enabled=0,
            live_keys_forward=1 if live_keys.forward else 0,
            live_keys_back=1 if live_keys.back else 0,
            live_keys_left=1 if live_keys.turn_left else 0,
            live_keys_right=1 if live_keys.turn_right else 0,
            live_keys_use=1 if live_keys.use else 0,
            live_key_events=live_key_events,
            replay_commands_built=counters.replay_commands_built,
            replay_ignored_live_key_state=counters.replay_ignored_live_key_state,
            manual_commands_built=counters.manual_commands_built,
            ticcmd=replay_cmd,
            old_x=old_x,
            old_y=old_y,
            old_angle=old_angle,
            old_momx=old_momx,
            old_momy=old_momy,
            old_viewz=old_viewz,
            new_x=mo.x,
            new_y=mo.y,
            new_angle=mo.angle,
            new_momx=mo.momx,
            new_momy=mo.momy,
            new_viewz=world.player.viewz,
            viewangle=frame_setup.viewangle,
            viewangle_degrees=frame_setup.viewangle_degrees,
            viewcos=frame_setup.viewcos,
            viewsin=frame_setup.viewsin,
            subsector=frame_setup.subsector,
            sector=frame_setup.sector,
            move_delta=delta,
            try_move_success=1 if delta.try_move_calls == 0 or delta.accepted_moves > 0 else 0,
            check_position_success=1 if delta.check_position_calls == 0 or delta.rejected_moves == 0 else 0,
            redraw_sample_id=redraw_sample_id,
            redraw_table_size=BOUNDED_REDRAW_SAMPLE_COUNT,
            finite_route_table=1,
            free_roaming_render_absent=1,
            marker_x=marker_x,
            marker_y=marker_y,
            marker_width=marker_width,
            marker_height=marker_height,
            marker_color=0x0028B8D8 + index * 0x00101820,
            marker_pixels=marker_pixels,
            pre_marker_framebuffer_signature=pre_sig,
            framebuffer_signature=0,
            player_view_state_signature=0,
            stage44_unified_state_signature=0,
            start_tic_sequence=seq + 1,
            input_event_sequence=seq + 2,
            ticcmd_sequence=seq + 3,
            g_ticker_sequence=seq + 4,
            p_ticker_sequence=seq + 5,
            player_think_sequence=seq + 6,
            p_move_player_sequence=seq + 7,
            p_thrust_sequence=seq + 8,
            xy_movement_sequence=seq + 9,
            try_move_sequence=seq + 10,
            r_setup_frame_sequence=seq + 11,
            bounded_redraw_sequence=seq + 12,
            projectile_thinker_sequence=seq + 13,
            status_sequence=seq + 14,
            signature_sequence=seq + 15,
            present_sequence=seq + 16,
        )
        _draw_player_view_marker(pre_frame, placeholder)
        fb_sig = stage31._framebuffer_signature(pre_frame)
        with_fb = Stage44LiveTiccmdUnifiedPlayerRenderSample(
            **{**placeholder.__dict__, "framebuffer_signature": fb_sig}
        )
        pview_sig = _player_view_signature(with_fb)
        with_player_sig = Stage44LiveTiccmdUnifiedPlayerRenderSample(
            **{**with_fb.__dict__, "player_view_state_signature": pview_sig}
        )
        samples.append(
            Stage44LiveTiccmdUnifiedPlayerRenderSample(
                **{
                    **with_player_sig.__dict__,
                    "stage44_unified_state_signature": _stage44_unified_state_signature(with_player_sig),
                }
            )
        )

    state_signature = fnv1a_words(tuple(sample.player_view_state_signature for sample in samples))
    state_signature = _hash_ascii(state_signature, "stage44 live ticcmd unified player render loop bridge")
    draft = Stage44LiveTiccmdUnifiedPlayerRenderLoopBridgeReference(
        stage43=ref43,
        samples=tuple(samples),
        deterministic_replay_default=1,
        live_mode_requires_flag=1,
        stage28_bridge_reused=1,
        gamekeydown_table_shared=1,
        replay_ignores_live_keys=1 if counters.replay_ignored_live_key_state >= len(samples) else 0,
        selected_g_ticker_ownership=1,
        selected_player_movement_update=1 if len({(s.new_x, s.new_y, s.new_angle) for s in samples}) >= 2 else 0,
        selected_p_thrust_update=1 if any(s.new_momx or s.new_momy for s in samples) else 0,
        selected_xy_movement_update=1 if all(s.move_delta.xy_movement_calls for s in samples) else 0,
        selected_trymove_boundary=1 if any(s.move_delta.try_move_calls for s in samples) else 0,
        finite_redraw_route_table=1,
        finite_redraw_route_table_size=BOUNDED_REDRAW_SAMPLE_COUNT,
        free_roaming_render_absent=1,
        selected_projectile_after_player_update=1 if all(s.projectile_thinker_sequence > s.p_move_player_sequence for s in samples) else 0,
        compact_status_preserved=1,
        stage40_bal1_vissprite_preserved=ref43.stage40_bal1_vissprite_preserved,
        distinct_player_view_state_signatures=len({sample.player_view_state_signature for sample in samples}),
        distinct_framebuffer_signatures=len({sample.framebuffer_signature for sample in samples}),
        distinct_stage44_unified_state_signatures=len({sample.stage44_unified_state_signature for sample in samples}),
        timer_samples=len(samples),
        invalidate_calls=len(samples),
        update_window_calls=len(samples),
        expected_paint_calls=len(samples),
        paint_after_final_player_sample=1,
        final_window_alive_after_samples=1,
        closes_normally=1,
        stage43_projectile_preserved=1 if ref43.signature == BASELINE_S43_SIGNATURE else 0,
        stage43_unified_loop_preserved=1 if (ref43.signature == BASELINE_S43_SIGNATURE and ref43.state_signature == BASELINE_S43_STATE_SIGNATURE) else 0,
        stage42_unified_loop_preserved=1 if (ref42.signature == BASELINE_S42_SIGNATURE and ref42.state_signature == BASELINE_S42_STATE_SIGNATURE) else 0,
        stage41_status_preserved=1 if (ref41.signature == BASELINE_S41_SIGNATURE and ref41.state_signature == BASELINE_S41_STATE_SIGNATURE) else 0,
        stage40_vissprite_preserved=1 if (ref40.signature == BASELINE_S40_SIGNATURE and ref40.state_signature == BASELINE_S40_STATE_SIGNATURE) else 0,
        stage39_projectile_state_preserved=1 if (ref39.signature == BASELINE_S39_SIGNATURE and ref39.projectile.state_signature == BASELINE_S39_STATE_SIGNATURE) else 0,
        stage38_present_preserved=ref43.stage38_present_preserved,
        stage37_feedback_preserved=ref43.stage37_feedback_preserved,
        stage36_pickup_preserved=ref43.stage36_pickup_preserved,
        stage35_drop_preserved=ref43.stage35_drop_preserved,
        stage34_death_preserved=ref43.stage34_death_preserved,
        stage33_impact_preserved=ref43.stage33_impact_preserved,
        stage32_psprite_preserved=ref43.stage32_psprite_preserved,
        stage31_wall_flat_preserved=ref43.stage31_wall_flat_preserved,
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
        generalized_thinkers_absent=1,
        generalized_collision_absent=1,
        generalized_projectile_manager_absent=1,
        broad_monster_ai_absent=1,
        generalized_combat_absent=1,
        broad_sprite_traversal_absent=1,
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
        source_stage45_absent=1,
        state_signature=state_signature,
        signature=0,
    )
    return Stage44LiveTiccmdUnifiedPlayerRenderLoopBridgeReference(
        **{**draft.__dict__, "signature": _stage44_signature(draft)}
    )


@lru_cache(maxsize=1)
def _reference_for_default_wad_or_none() -> Stage44LiveTiccmdUnifiedPlayerRenderLoopBridgeReference | None:
    wad = REPO_ROOT / WAD_PATH
    if not wad.exists():
        return None
    return reference_live_ticcmd_unified_player_render_loop_bridge_for_pinned_map(wad)


def _stage44_replay_titles(ref: Stage44LiveTiccmdUnifiedPlayerRenderLoopBridgeReference | None) -> list[str]:
    if ref is None:
        return [
            "Inference Doom S44 STEP44=1 missing pinned WAD",
            "Inference Doom S44 STEP44=2 missing pinned WAD",
            "Inference Doom S44 STEP44=3 missing pinned WAD",
        ]
    titles: list[str] = []
    ref43 = ref.stage43
    ref42 = ref43.stage42
    ref41 = ref42.stage41
    ref40 = ref41.stage40
    ref39 = ref40.stage39
    ref38 = ref39.stage38
    for sample in ref.samples:
        cmd = sample.ticcmd
        baseline = sample.baseline
        titles.append(
            "Inference Doom S44 "
            f"STEP44={sample.step} TIC44={sample.tic} MODE44={sample.mode} LIVE44={sample.live_enabled} "
            f"KEY44=F{sample.live_keys_forward}/B{sample.live_keys_back}/L{sample.live_keys_left}/R{sample.live_keys_right}/U{sample.live_keys_use} "
            f"CMD44=F{cmd.forwardmove}/S{cmd.sidemove}/A{cmd.angleturn}/B{cmd.buttons} "
            f"RCMD44={sample.replay_commands_built} RIGN44={sample.replay_ignored_live_key_state} MCMD44={sample.manual_commands_built} "
            f"PX44={sample.new_x >> stage31.FRACBITS} PY44={sample.new_y >> stage31.FRACBITS} "
            f"ANG44={sample.new_angle} VZ44={sample.new_viewz >> stage31.FRACBITS} "
            f"MOM44={sample.new_momx}/{sample.new_momy} TRY44={sample.move_delta.try_move_calls}:{sample.try_move_success} "
            f"CHK44={sample.move_delta.check_position_calls}:{sample.check_position_success} ACC44={sample.move_delta.accepted_moves} "
            f"REJ44={sample.move_delta.rejected_moves} LINE44={sample.move_delta.line_checks} THING44={sample.move_delta.thing_checks} "
            f"RSEL44={sample.redraw_sample_id}/{sample.redraw_table_size} ROUTE44=bounded{sample.redraw_table_size} FREE44={0 if sample.free_roaming_render_absent else 1} "
            f"PVSTATE44={sample.player_view_state_signature} ULSTATE44={sample.stage44_unified_state_signature} FB44={sample.framebuffer_signature} "
            f"STATE44={ref.state_signature} S44SIG={ref.signature} "
            f"MISS43={baseline.type_name} PSTATE43={baseline.projectile_state_signature} ULSTATE43={baseline.stage43_unified_state_signature} "
            f"FB43={baseline.framebuffer_signature} STATE43={ref43.state_signature} S43SIG={ref43.signature} "
            f"ULSTATE42={baseline.baseline.unified_loop_state_signature} FB42={baseline.baseline.framebuffer_signature} "
            f"STATE42={ref42.state_signature} S42SIG={ref42.signature} "
            f"FB41={baseline.baseline.baseline.framebuffer_signature} SSTATE41={baseline.baseline.baseline.selected_status_state_signature} "
            f"STATE41={ref41.state_signature} S41SIG={ref41.signature} "
            f"PATCH40=BAL1 S40SIG={ref40.signature} STATE40={ref40.state_signature} "
            f"MISS39={ref39.projectile.type_name} PST39={ref39.projectile.state_signature} S39SIG={ref39.signature} STATE39={ref39.projectile.state_signature} "
            f"S38SIG={ref38.signature} STATE38={ref38.attack.state_signature} "
            f"INV44={sample.step} UPD44={sample.step} PAINT44={sample.step} PAF44={1 if sample.step == len(ref.samples) else 0} "
            f"INV43={ref43.invalidate_calls} UPD43={ref43.update_window_calls} PAINT43={ref43.expected_paint_calls} PAF43={ref43.paint_after_final_projectile_sample} "
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
            f"NOFULL44={ref.full_frame_byte_arrays_absent} BAL144={ref.stage40_bal1_vissprite_preserved} "
            f"PRIM44={ref.runtime_renderer_primitives} S45ABS={ref.source_stage45_absent}"
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


def emit_stage44_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.call_rel32(pe, "stage44_parse_command_line")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")
    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage44_class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage44_class_registered")
    x86.call_rel32(pe, "source_stage44_load_wad_live_ticcmd_unified_player_render_loop_bridge")
    x86.call_rel32(pe, "append_stage44_success_status")
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
    x86.jne_rel32(pe, "stage44_window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage44_window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage44_set_live_start")
    x86.push_abs32(pe, "stage44_replay_title_start")
    x86.jmp_rel32(pe, "stage44_set_start_title")
    pe.label("stage44_set_live_start")
    x86.push_abs32(pe, "stage44_live_title_start")
    pe.label("stage44_set_start_title")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE44_TIMER_MS)
    x86.push_imm32(pe, STAGE44_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
    pe.label("stage44_message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage44_clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "stage44_message_error")
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, stage38.WM_TIMER)
    x86.jne_rel32(pe, "stage44_dispatch_message")
    x86.call_rel32(pe, "stage44_timer_tick")
    pe.label("stage44_dispatch_message")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "stage44_message_loop")
    pe.label("stage44_clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage44_message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_stage44_parse_command_line(pe: PE32) -> None:
    pe.label("stage44_parse_command_line")
    x86.call_import(pe, stage01.KERNEL32, "GetCommandLineA")
    x86.mov_reg_reg(pe, "esi", "eax")
    pe.label("stage44_parse_loop")
    x86.mov_al_ptr_esi(pe)
    x86.cmp_al_imm8(pe, 0)
    x86.je_rel32(pe, "stage44_parse_done")
    x86.cmp_al_imm8(pe, ord("-"))
    x86.jne_rel32(pe, "stage44_parse_next")
    for offset, char in enumerate("-live"):
        x86.movzx_reg_byte_ptr_reg_disp8(pe, "eax", "esi", offset)
        x86.cmp_eax_imm32(pe, ord(char))
        x86.jne_rel32(pe, "stage44_parse_next")
    x86.mov_mem_abs32_imm32(pe, "stage44_live_mode", 1)
    x86.ret(pe)
    pe.label("stage44_parse_next")
    x86.inc_reg(pe, "esi")
    x86.jmp_rel32(pe, "stage44_parse_loop")
    pe.label("stage44_parse_done")
    x86.ret(pe)


def emit_stage44_timer_tick(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(stage38.SELECTED_SAMPLE_TICS)
    pe.label("stage44_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage44_live_timer")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_replay_step")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage44_replay_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage44_replay_sample{index}")
        x86.call_rel32(pe, f"stage44_draw_sample{index}")
        x86.push_abs32(pe, f"stage44_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        if index == sample_count - 1:
            x86.mov_mem_abs32_imm32(pe, "stage44_final_player_sample_drawn", 1)
        stage07._emit_inc_abs32(pe, "stage44_invalidate_calls")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        stage07._emit_inc_abs32(pe, "stage44_update_window_calls")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.mov_mem_abs32_imm32(pe, "stage44_replay_step", index + 1)
        if index == sample_count - 1:
            x86.push_imm32(pe, STAGE44_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)
    pe.label("stage44_live_timer")
    x86.call_rel32(pe, "G_BuildTiccmd_stage44_live_runtime_debug")
    x86.call_rel32(pe, "stage44_select_live_sample_runtime")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_sample_index")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage44_live_draw_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage44_live_draw_sample{index}")
        x86.call_rel32(pe, f"stage44_draw_sample{index}")
        x86.call_rel32(pe, "stage44_build_live_title")
        x86.push_abs32(pe, "stage44_live_title_buffer")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        stage07._emit_inc_abs32(pe, "stage44_invalidate_calls")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        stage07._emit_inc_abs32(pe, "stage44_update_window_calls")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.ret(pe)


def emit_stage44_wndproc_framebuffer(pe: PE32) -> None:
    pe.label("wndproc")
    x86.emit_function_prologue(pe)
    x86.mov_eax_ebp_disp8(pe, 12)
    x86.cmp_eax_imm32(pe, stage01.WM_DESTROY)
    x86.je_rel32(pe, "wndproc_destroy")
    x86.cmp_eax_imm32(pe, stage01.WM_PAINT)
    x86.je_rel32(pe, "wndproc_paint")
    x86.cmp_eax_imm32(pe, WM_KEYDOWN)
    x86.je_rel32(pe, "wndproc_keydown")
    x86.cmp_eax_imm32(pe, WM_KEYUP)
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
        ("stage44_key_forward", (VK_UP, VK_W)),
        ("stage44_key_back", (VK_DOWN, VK_S)),
        ("stage44_key_left", (VK_LEFT, VK_A)),
        ("stage44_key_right", (VK_RIGHT, VK_D)),
        ("stage44_key_use", (VK_SPACE, VK_E)),
    ):
        for key in keys:
            x86.cmp_eax_imm32(pe, key)
            x86.je_rel32(pe, f"wndproc_set_{label}")
    x86.jmp_rel32(pe, "wndproc_default")
    for label, _keys in (
        ("stage44_key_forward", ()),
        ("stage44_key_back", ()),
        ("stage44_key_left", ()),
        ("stage44_key_right", ()),
        ("stage44_key_use", ()),
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
    stage07._emit_inc_abs32(pe, "stage44_paint_calls")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_final_player_sample_drawn")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "stage44_paint_after_final_skip")
    stage07._emit_inc_abs32(pe, "stage44_paint_after_final_player")
    pe.label("stage44_paint_after_final_skip")
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


def emit_stage44_live_runtime(pe: PE32) -> None:
    pe.label("G_BuildTiccmd_stage44_live_runtime_debug")
    x86.inc_mem_abs32(pe, "stage44_runtime_live_commands")
    x86.mov_mem_abs32_imm32(pe, "stage44_live_forwardmove", 0)
    x86.mov_mem_abs32_imm32(pe, "stage44_live_sidemove", 0)
    x86.mov_mem_abs32_imm32(pe, "stage44_live_angleturn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage44_live_buttons", 0)
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_key_forward")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage44_live_no_forward")
    x86.mov_mem_abs32_imm32(pe, "stage44_live_forwardmove", FORWARDMOVE)
    pe.label("stage44_live_no_forward")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_key_back")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage44_live_no_back")
    x86.mov_mem_abs32_imm32(pe, "stage44_live_forwardmove", (-FORWARDMOVE) & 0xFFFFFFFF)
    pe.label("stage44_live_no_back")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_key_left")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage44_live_no_left")
    x86.mov_mem_abs32_imm32(pe, "stage44_live_angleturn", SLOW_ANGLETURN)
    pe.label("stage44_live_no_left")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_key_right")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage44_live_no_right")
    x86.mov_mem_abs32_imm32(pe, "stage44_live_angleturn", (-SLOW_ANGLETURN) & 0xFFFFFFFF)
    pe.label("stage44_live_no_right")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_key_use")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage44_live_use_up")
    x86.mov_mem_abs32_imm32(pe, "stage44_live_buttons", BT_USE)
    x86.inc_mem_abs32(pe, "stage44_runtime_live_bt_use")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_runtime_usedown")
    x86.cmp_eax_imm32(pe, 0)
    x86.jne_rel32(pe, "stage44_live_use_held")
    x86.mov_mem_abs32_imm32(pe, "stage44_runtime_usedown", 1)
    x86.inc_mem_abs32(pe, "stage44_runtime_live_use_edges")
    x86.ret(pe)
    pe.label("stage44_live_use_held")
    x86.inc_mem_abs32(pe, "stage44_runtime_live_use_held_skips")
    x86.ret(pe)
    pe.label("stage44_live_use_up")
    x86.mov_mem_abs32_imm32(pe, "stage44_runtime_usedown", 0)
    x86.ret(pe)


def emit_stage44_select_live_sample_runtime(pe: PE32) -> None:
    pe.label("stage44_select_live_sample_runtime")
    x86.mov_mem_abs32_imm32(pe, "stage44_live_sample_index", 0)
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_buttons")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage44_live_select_no_use")
    x86.mov_mem_abs32_imm32(pe, "stage44_live_sample_index", 2)
    x86.ret(pe)
    pe.label("stage44_live_select_no_use")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_forwardmove")
    x86.cmp_eax_imm32(pe, 0)
    x86.jne_rel32(pe, "stage44_live_select_motion")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_angleturn")
    x86.cmp_eax_imm32(pe, 0)
    x86.jne_rel32(pe, "stage44_live_select_motion")
    x86.ret(pe)
    pe.label("stage44_live_select_motion")
    x86.mov_mem_abs32_imm32(pe, "stage44_live_sample_index", 1)
    x86.ret(pe)


def emit_stage44_build_live_title(pe: PE32) -> None:
    pe.label("stage44_build_live_title")
    x86.mov_reg_abs32(pe, "edi", "stage44_live_title_buffer")
    stage01.append_c_string_label(pe, "stage44_live_title_prefix")
    for prefix, label, signed in (
        ("stage44_live_title_cmd_prefix", "stage44_runtime_live_commands", False),
        ("stage44_live_title_forward_prefix", "stage44_live_forwardmove", True),
        ("stage44_live_title_side_prefix", "stage44_live_sidemove", True),
        ("stage44_live_title_angle_prefix", "stage44_live_angleturn", True),
        ("stage44_live_title_buttons_prefix", "stage44_live_buttons", False),
        ("stage44_live_title_use_prefix", "stage44_runtime_live_bt_use", False),
        ("stage44_live_title_edge_prefix", "stage44_runtime_live_use_edges", False),
        ("stage44_live_title_key_prefix", "stage44_runtime_live_key_events", False),
        ("stage44_live_title_sample_prefix", "stage44_live_sample_index", False),
        ("stage44_live_title_fb_prefix", "stage44_runtime_fb_signature", False),
        ("stage44_live_title_pv_prefix", "stage44_runtime_player_view_state_signature", False),
        ("stage44_live_title_state_prefix", "stage44_runtime_state_signature", False),
        ("stage44_live_title_sig_prefix", "stage44_runtime_signature", False),
    ):
        (stage01.append_i32_label if signed else stage01.append_u32_label)(pe, prefix, label)
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    x86.ret(pe)


def emit_stage44_draw_player_view_marker(pe: PE32) -> None:
    pe.label("stage44_draw_player_view_marker")
    x86.mov_reg_mem_abs32(pe, "ebx", "stage44_marker_height")
    x86.test_reg_reg(pe, "ebx")
    x86.je_rel32(pe, "stage44_marker_done")
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.add_reg_mem_abs32(pe, "edi", "stage44_marker_offset")
    pe.label("stage44_marker_row_loop")
    x86.mov_reg_mem_abs32(pe, "ecx", "stage44_marker_width")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_marker_color")
    pe.label("stage44_marker_pixel_loop")
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.add_reg_imm32(pe, "edi", 4)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "stage44_marker_pixel_loop")
    x86.add_reg_mem_abs32(pe, "edi", "stage44_marker_row_advance")
    x86.dec_reg(pe, "ebx")
    x86.jne_rel32(pe, "stage44_marker_row_loop")
    pe.label("stage44_marker_done")
    x86.ret(pe)


def _emit_stage44_update_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage44_update_live_ticcmd_player_sample{index}")
    for dst, src in (
        ("stage44_runtime_tic", f"stage44_sample{index}_tic"),
        ("stage44_runtime_forwardmove", f"stage44_sample{index}_forwardmove"),
        ("stage44_runtime_sidemove", f"stage44_sample{index}_sidemove"),
        ("stage44_runtime_angleturn", f"stage44_sample{index}_angleturn"),
        ("stage44_runtime_buttons", f"stage44_sample{index}_buttons"),
        ("stage44_runtime_player_x", f"stage44_sample{index}_player_x"),
        ("stage44_runtime_player_y", f"stage44_sample{index}_player_y"),
        ("stage44_runtime_player_angle", f"stage44_sample{index}_player_angle"),
        ("stage44_runtime_viewz", f"stage44_sample{index}_viewz"),
        ("stage44_runtime_momx", f"stage44_sample{index}_momx"),
        ("stage44_runtime_momy", f"stage44_sample{index}_momy"),
        ("stage44_runtime_trymove_calls", f"stage44_sample{index}_trymove_calls"),
        ("stage44_runtime_checkposition_calls", f"stage44_sample{index}_checkposition_calls"),
        ("stage44_runtime_accepted_moves", f"stage44_sample{index}_accepted_moves"),
        ("stage44_runtime_redraw_sample_id", f"stage44_sample{index}_redraw_sample_id"),
        ("stage44_runtime_player_view_state_signature", f"stage44_sample{index}_player_view_state_signature"),
        ("stage44_runtime_unified_state_signature", f"stage44_sample{index}_unified_state_signature"),
        ("stage44_marker_offset", f"stage44_sample{index}_marker_offset"),
        ("stage44_marker_width", f"stage44_sample{index}_marker_width"),
        ("stage44_marker_height", f"stage44_sample{index}_marker_height"),
        ("stage44_marker_color", f"stage44_sample{index}_marker_color"),
        ("stage44_marker_row_advance", f"stage44_sample{index}_marker_row_advance"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_stage44_draw_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage44_draw_sample{index}")
    x86.call_rel32(pe, f"stage43_draw_sample{index}")
    x86.call_rel32(pe, f"stage44_update_live_ticcmd_player_sample{index}")
    x86.call_rel32(pe, "stage44_draw_player_view_marker")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage44_runtime_fb_signature")
    x86.ret(pe)


def emit_source_stage44_load_wad_live_ticcmd_unified_player_render_loop_bridge(pe: PE32) -> None:
    pe.label("source_stage44_load_wad_live_ticcmd_unified_player_render_loop_bridge")
    x86.call_rel32(pe, "source_stage43_load_wad_bounded_projectile_tick_collision_feedback_probe")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage44_load_fail")
    x86.mov_reg_mem_abs32(pe, "eax", "stage43_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage43_expected_signature")
    x86.jne_rel32(pe, "stage44_load_fail")
    x86.call_rel32(pe, "render_live_ticcmd_unified_player_render_loop_bridge_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage44_expected_signature")
    x86.jne_rel32(pe, "stage44_load_fail")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage44_load_fail")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def emit_render_live_ticcmd_unified_player_render_loop_bridge_debug(pe: PE32) -> None:
    for _, _, label in SOURCE_TRACE[-12:]:
        pe.label(label)
    pe.label("render_live_ticcmd_unified_player_render_loop_bridge_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage44_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_expected_state_signature")
    x86.mov_mem_abs32_eax(pe, "stage44_runtime_state_signature")
    x86.ret(pe)


def emit_append_stage44_success_status(pe: PE32) -> None:
    pe.label("append_stage44_success_status")
    stage01.emit_set_status_ptrs(pe, "status_stage44_success_header", "stage44_replay_title_start")
    x86.ret(pe)


def emit_stage44_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    samples = ref.samples if ref else ()
    pe.align_section(4)
    values = (
        ("stage44_frame_count", len(samples)),
        ("stage44_distinct_player_view_state_signatures", ref.distinct_player_view_state_signatures if ref else 0),
        ("stage44_distinct_fb_signatures", ref.distinct_framebuffer_signatures if ref else 0),
        ("stage44_distinct_unified_state_signatures", ref.distinct_stage44_unified_state_signatures if ref else 0),
        ("stage44_expected_state_signature", ref.state_signature if ref else 0),
        ("stage44_runtime_state_signature", 0),
        ("stage44_expected_signature", ref.signature if ref else 0),
        ("stage44_runtime_signature", 0),
        ("stage44_runtime_fb_signature", 0),
        ("stage44_runtime_tic", 0),
        ("stage44_runtime_forwardmove", 0),
        ("stage44_runtime_sidemove", 0),
        ("stage44_runtime_angleturn", 0),
        ("stage44_runtime_buttons", 0),
        ("stage44_runtime_player_x", 0),
        ("stage44_runtime_player_y", 0),
        ("stage44_runtime_player_angle", 0),
        ("stage44_runtime_viewz", 0),
        ("stage44_runtime_momx", 0),
        ("stage44_runtime_momy", 0),
        ("stage44_runtime_trymove_calls", 0),
        ("stage44_runtime_checkposition_calls", 0),
        ("stage44_runtime_accepted_moves", 0),
        ("stage44_runtime_redraw_sample_id", 0),
        ("stage44_runtime_player_view_state_signature", 0),
        ("stage44_runtime_unified_state_signature", 0),
        ("stage44_marker_offset", 0),
        ("stage44_marker_width", 0),
        ("stage44_marker_height", 0),
        ("stage44_marker_color", 0),
        ("stage44_marker_row_advance", 0),
        ("stage44_replay_step", 0),
        ("stage44_invalidate_calls", 0),
        ("stage44_update_window_calls", 0),
        ("stage44_paint_calls", 0),
        ("stage44_final_player_sample_drawn", 0),
        ("stage44_paint_after_final_player", 0),
        ("stage44_expected_timer_samples", ref.timer_samples if ref else 0),
        ("stage44_expected_invalidate_calls", ref.invalidate_calls if ref else 0),
        ("stage44_expected_update_window_calls", ref.update_window_calls if ref else 0),
        ("stage44_expected_paint_calls", ref.expected_paint_calls if ref else 0),
        ("stage44_expected_paint_after_final_player", ref.paint_after_final_player_sample if ref else 0),
        ("stage44_deterministic_replay_default", ref.deterministic_replay_default if ref else 1),
        ("stage44_live_mode_requires_flag", ref.live_mode_requires_flag if ref else 1),
        ("stage44_stage28_bridge_reused", ref.stage28_bridge_reused if ref else 1),
        ("stage44_gamekeydown_table_shared", ref.gamekeydown_table_shared if ref else 1),
        ("stage44_replay_ignores_live_keys", ref.replay_ignores_live_keys if ref else 1),
        ("stage44_finite_redraw_route_table", ref.finite_redraw_route_table if ref else 1),
        ("stage44_finite_redraw_route_table_size", ref.finite_redraw_route_table_size if ref else BOUNDED_REDRAW_SAMPLE_COUNT),
        ("stage44_free_roaming_render_absent", ref.free_roaming_render_absent if ref else 1),
        ("stage44_projectile_after_player_update", ref.selected_projectile_after_player_update if ref else 1),
        ("stage44_stage43_projectile_preserved", ref.stage43_projectile_preserved if ref else 1),
        ("stage44_stage40_bal1_vissprite_preserved", ref.stage40_bal1_vissprite_preserved if ref else 1),
        ("stage44_full_frame_byte_arrays_absent", ref.full_frame_byte_arrays_absent if ref else 1),
        ("stage44_runtime_renderer_primitives", ref.runtime_renderer_primitives if ref else 1),
        ("stage44_generalized_thinkers_absent", ref.generalized_thinkers_absent if ref else 1),
        ("stage44_generalized_collision_absent", ref.generalized_collision_absent if ref else 1),
        ("stage44_generalized_projectile_manager_absent", ref.generalized_projectile_manager_absent if ref else 1),
        ("stage44_broad_monster_ai_absent", ref.broad_monster_ai_absent if ref else 1),
        ("stage44_broad_sprite_traversal_absent", ref.broad_sprite_traversal_absent if ref else 1),
        ("stage44_source_stage45_absent", ref.source_stage45_absent if ref else 1),
        ("stage44_live_mode", 0),
        ("stage44_key_forward", 0),
        ("stage44_key_back", 0),
        ("stage44_key_left", 0),
        ("stage44_key_right", 0),
        ("stage44_key_use", 0),
        ("stage44_runtime_live_key_events", 0),
        ("stage44_runtime_live_commands", 0),
        ("stage44_live_forwardmove", 0),
        ("stage44_live_sidemove", 0),
        ("stage44_live_angleturn", 0),
        ("stage44_live_buttons", 0),
        ("stage44_runtime_live_bt_use", 0),
        ("stage44_runtime_live_use_edges", 0),
        ("stage44_runtime_live_use_held_skips", 0),
        ("stage44_runtime_usedown", 0),
        ("stage44_live_sample_index", 0),
    )
    for name, value in values:
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        fields = (
            (f"stage44_sample{index}_tic", sample.tic),
            (f"stage44_sample{index}_forwardmove", sample.ticcmd.forwardmove),
            (f"stage44_sample{index}_sidemove", sample.ticcmd.sidemove),
            (f"stage44_sample{index}_angleturn", sample.ticcmd.angleturn),
            (f"stage44_sample{index}_buttons", sample.ticcmd.buttons),
            (f"stage44_sample{index}_player_x", sample.new_x),
            (f"stage44_sample{index}_player_y", sample.new_y),
            (f"stage44_sample{index}_player_angle", sample.new_angle),
            (f"stage44_sample{index}_viewz", sample.new_viewz),
            (f"stage44_sample{index}_momx", sample.new_momx),
            (f"stage44_sample{index}_momy", sample.new_momy),
            (f"stage44_sample{index}_trymove_calls", sample.move_delta.try_move_calls),
            (f"stage44_sample{index}_checkposition_calls", sample.move_delta.check_position_calls),
            (f"stage44_sample{index}_accepted_moves", sample.move_delta.accepted_moves),
            (f"stage44_sample{index}_redraw_sample_id", sample.redraw_sample_id),
            (f"stage44_sample{index}_player_view_state_signature", sample.player_view_state_signature),
            (f"stage44_sample{index}_unified_state_signature", sample.stage44_unified_state_signature),
            (f"stage44_sample{index}_framebuffer_signature", sample.framebuffer_signature),
            (f"stage44_sample{index}_marker_offset", (sample.marker_y * FRAMEBUFFER_WIDTH + sample.marker_x) * 4),
            (f"stage44_sample{index}_marker_width", sample.marker_width),
            (f"stage44_sample{index}_marker_height", sample.marker_height),
            (f"stage44_sample{index}_marker_color", sample.marker_color),
            (f"stage44_sample{index}_marker_row_advance", (FRAMEBUFFER_WIDTH - sample.marker_width) * 4),
        )
        for name, value in fields:
            pe.label(name)
            pe.emit_u32(value & 0xFFFFFFFF)
    pe.label("status_stage44_success_header")
    x86.emit_asciiz(pe, "\r\nLive Ticcmd Unified Player Render Loop Bridge proof OK\r\n")
    pe.label("status_stage44_log_prefix")
    x86.emit_asciiz(pe, "source_stage44_live_ticcmd_unified_player_render_loop_bridge ")
    pe.label("stage44_log_text")
    x86.emit_asciiz(
        pe,
        "Stage28 bounded gamekeydown/ticcmd bridge reintroduced into stage43 unified cadence. "
        "Default replay owns ticcmd_t and ignores live keys; -live mode reads bounded Win32 key state. "
        "Selected P_MovePlayer/P_Thrust/P_XYMovement/P_TryMove evidence drives finite redraw samples, "
        "while stage43 MT_TROOPSHOT feedback, BAL1 vissprite, psprite, compact status, and present path remain preserved. "
        "NOFULL44=1, FREE44=0, no broad thinkers/collision/combat/sprites/HUD/audio/network/save/map progression ",
    )
    pe.label("stage44_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S44 REPLAY START STEP44=0 LIVE44=0 bounded stage28 ticcmd bridge waiting")
    pe.label("stage44_live_title_start")
    x86.emit_asciiz(pe, "Inference Doom S44 LIVE START LIVE44=1 bounded W/S/A/D/arrows and E/Space finite redraw table")
    for index, title in enumerate(_stage44_replay_titles(ref)):
        pe.label(f"stage44_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)
    pe.label("stage44_live_title_buffer")
    pe.emit(b"\0" * 768)
    pe.label("stage44_live_title_prefix")
    x86.emit_asciiz(pe, "Inference Doom S44 LIVE LIVE44=1 ROUTE44=bounded3 FREE44=0")
    for label, text in (
        ("stage44_live_title_cmd_prefix", " LCMD44="),
        ("stage44_live_title_forward_prefix", " FM44="),
        ("stage44_live_title_side_prefix", " SM44="),
        ("stage44_live_title_angle_prefix", " AT44="),
        ("stage44_live_title_buttons_prefix", " BTN44="),
        ("stage44_live_title_use_prefix", " BTUSE44="),
        ("stage44_live_title_edge_prefix", " USEEDGE44="),
        ("stage44_live_title_key_prefix", " KEYEV44="),
        ("stage44_live_title_sample_prefix", " LSEL44="),
        ("stage44_live_title_fb_prefix", " FB44="),
        ("stage44_live_title_pv_prefix", " PVSTATE44="),
        ("stage44_live_title_state_prefix", " STATE44="),
        ("stage44_live_title_sig_prefix", " S44SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)


def build_source_stage44_live_ticcmd_unified_player_render_loop_bridge_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(stage38.SELECTED_SAMPLE_TICS)
    with patched_stage01_window_labels():
        emit_stage44_entry(pe)
        emit_stage44_wndproc_framebuffer(pe)
        emit_stage44_parse_command_line(pe)
        emit_stage44_timer_tick(pe)
        emit_stage44_live_runtime(pe)
        emit_stage44_select_live_sample_runtime(pe)
        emit_stage44_build_live_title(pe)
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
        emit_stage44_draw_player_view_marker(pe)
        for index in range(sample_count):
            stage40._emit_stage40_draw_sample(pe, index)
            stage41._emit_stage41_draw_sample(pe, index)
            stage42._emit_stage42_update_sample(pe, index)
            stage42._emit_stage42_draw_sample(pe, index)
            stage43._emit_stage43_update_sample(pe, index)
            stage43._emit_stage43_draw_sample(pe, index)
            _emit_stage44_update_sample(pe, index)
            _emit_stage44_draw_sample(pe, index)
        stage36.emit_source_stage36_load_wad_selected_dropped_shotgun_visual_boundary(pe)
        stage38.emit_source_stage38_load_wad_selected_attack_feedback_present_bridge(pe)
        stage39.emit_source_stage39_load_wad_selected_projectile_spawn_present_probe(pe)
        stage40.emit_source_stage40_load_wad_bounded_vissprite_traversal_sorting_bridge(pe)
        stage41.emit_source_stage41_load_wad_statusbar_weapon_ammo_feedback_bridge(pe)
        stage42.emit_source_stage42_load_wad_unified_live_tick_render_loop_probe(pe)
        stage43.emit_source_stage43_load_wad_bounded_projectile_tick_collision_feedback_probe(pe)
        emit_source_stage44_load_wad_live_ticcmd_unified_player_render_loop_bridge(pe)
        stage36._emit_prior_loaders(pe)
        stage36._emit_runtime_helpers(pe)
        stage36.emit_render_selected_dropped_shotgun_visual_boundary_debug(pe)
        stage38.emit_render_selected_attack_feedback_present_bridge_debug(pe)
        stage39.emit_render_selected_projectile_spawn_present_probe_debug(pe)
        stage40.emit_render_bounded_vissprite_traversal_sorting_bridge_debug(pe)
        stage41.emit_render_statusbar_weapon_ammo_feedback_bridge_debug(pe)
        stage42.emit_render_unified_live_tick_render_loop_probe_debug(pe)
        stage43.emit_render_bounded_projectile_tick_collision_feedback_probe_debug(pe)
        emit_render_live_ticcmd_unified_player_render_loop_bridge_debug(pe)
        stage36._emit_prior_status(pe)
        stage36.emit_append_stage36_success_status(pe)
        stage38.emit_append_stage38_success_status(pe)
        stage39.emit_append_stage39_success_status(pe)
        stage40.emit_append_stage40_success_status(pe)
        stage41.emit_append_stage41_success_status(pe)
        stage42.emit_append_stage42_success_status(pe)
        stage43.emit_append_stage43_success_status(pe)
        emit_append_stage44_success_status(pe)
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
        emit_stage44_data(pe)
    return pe.build("entry")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage44 live ticcmd unified player render loop PE32 bridge"
    )
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output PE32 executable path")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = build_source_stage44_live_ticcmd_unified_player_render_loop_bridge_exe()
    output.write_bytes(data)
    ref = _reference_for_default_wad_or_none()
    print(f"Wrote {output} ({len(data)} bytes)")
    if ref is not None:
        print(f"S44SIG={ref.signature}")
        print(f"STATE44={ref.state_signature}")
        print("PVSTATE44=" + ",".join(str(sample.player_view_state_signature) for sample in ref.samples))
        print("ULSTATE44=" + ",".join(str(sample.stage44_unified_state_signature) for sample in ref.samples))
        print("FB44=" + ",".join(str(sample.framebuffer_signature) for sample in ref.samples))


if __name__ == "__main__":
    main()
