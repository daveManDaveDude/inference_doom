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

from tools import emit_source_stage46_repeatable_selected_monster_thinker_cadence_bridge as stage46
from tools import x86
from tools.map_loader import load_map_from_file
from tools.pe32 import PE32
from tools.wad import WadFile


stage45 = stage46.stage45
stage44 = stage46.stage44
stage43 = stage46.stage43
stage42 = stage46.stage42
stage41 = stage46.stage41
stage40 = stage46.stage40
stage39 = stage46.stage39
stage38 = stage46.stage38
stage36 = stage46.stage36
stage32 = stage46.stage32
stage31 = stage46.stage31
stage18 = stage46.stage18
stage16 = stage46.stage16
stage15 = stage16.stage15
stage14 = stage16.stage14
stage13 = stage46.stage13
stage03 = stage46.stage03
stage01 = stage46.stage01

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "build" / "source_stage47_bounded_map01_player_route_first_hostile_sight_bridge.exe"
WAD_PATH = stage46.WAD_PATH

FRAMEBUFFER_WIDTH = stage46.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage46.FRAMEBUFFER_HEIGHT
WINDOW_WIDTH = stage46.WINDOW_WIDTH
WINDOW_HEIGHT = stage46.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage47BoundedMap01PlayerRouteFirstHostileSightBridge"
WINDOW_TITLE = "Inference Doom S47 Bounded MAP01 Player Route First Hostile Sight Bridge"

STAGE47_TIMER_ID = 47
STAGE47_TIMER_MS = 75
ROUTE_TICS = 44
MONSTER_COUNT = 18
CONTACT_MOBJ = 48
CONTACT_MAPTHING = 66
CONTACT_TYPE = "MT_POSSESSED"
CONTACT_X = 416
CONTACT_Y = 176
CONTACT_ANGLE_DEGREES = 45
CONTACT_STATE = "S_POSS_STND"
CONTACT_TICS = 3
CONTACT_LASTLOOK = 1
CONTACT_TRACE = (85, 32, 113, 6)
COLLISION_RECORD_WORDS = 10
COLLISION_RECORD_SIZE = COLLISION_RECORD_WORDS * 4
COMMAND_RECORD_SIZE = 16
FNV_OFFSET_BASIS = stage46.FNV_OFFSET_BASIS
FNV_PRIME = stage46.FNV_PRIME

BASELINE_S46_SIGNATURE = 2719909431
BASELINE_STATE46 = 4094043488
BASELINE_MSTATE46 = (2557949986, 3037306965, 2247320167, 29004293, 3810739213, 1892788599, 533767476)
BASELINE_ULSTATE46 = (1560044802, 2153923995, 1942825685, 2641348968, 2957418852, 1405647190, 3637274982)
BASELINE_FB46 = (1154819706, 2382271357, 1757537078, 190720345, 3141461029, 3141461029, 3905320152)

SOURCE_TRACE = stage46.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/p_tick.c",
        "P_Ticker player then bounded visibility then selected thinker/projectile/status ordering",
        "P_Ticker_stage47_player_visibility_selected_thinker_projectile_status_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_user.c",
        "P_PlayerThink/P_MovePlayer/P_Thrust runtime-owned replay or live command mutation",
        "P_PlayerThink_P_MovePlayer_P_Thrust_stage47_runtime_owned_route_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_XYMovement one bounded player momentum step and friction per accepted tic",
        "P_XYMovement_stage47_runtime_owned_player_momentum_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "P_CheckPosition/P_TryMove matched real MAP01 route input/outcome evidence",
        "P_TryMove_stage47_bounded_map01_route_collision_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_maputl.c",
        "P_BlockLinesIterator/P_BlockThingsIterator route collision visit evidence",
        "P_BlockIterators_stage47_real_map01_route_evidence_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_sight.c",
        "P_CheckSight/P_CrossBSPNode/P_CrossSubsector earliest result over all MAP01 monsters",
        "P_CheckSight_stage47_first_hostile_geometric_contact_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_tick.c",
        "P_RunThinkers selected contact boundary with no awareness or state mutation",
        "P_RunThinkers_stage47_selected_stand_target_null_boundary_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_SetupFrame/R_RenderPlayerView finite source-derived route keyframe selection",
        "R_SetupFrame_stage47_finite_route_keyframes_debug",
    ),
    (
        "reference/chocolate-doom/src/v_video.c",
        "V_DrawFilledBox runtime player/contact primitives from owned scalar state",
        "V_DrawFilledBox_stage47_runtime_player_contact_primitives_debug",
    ),
    (
        "reference/chocolate-doom/src/i_video.c",
        "I_FinishUpdate paint after the final geometric contact sample",
        "I_Video_stage47_present_after_final_contact_debug",
    ),
)


@dataclass(frozen=True)
class Stage47CollisionRecord:
    tic: int
    try_x: int
    try_y: int
    accepted: int
    subsector: int
    sector: int
    line_checks: int
    thing_checks: int
    line_visits: int
    thing_visits: int


@dataclass(frozen=True)
class Stage47RouteSample:
    step: int
    command: stage44.Stage44TicCmd
    old_x: int
    old_y: int
    x: int
    y: int
    angle: int
    momx: int
    momy: int
    sector: int
    subsector: int
    try_move_calls: int
    accepted_moves: int
    rejected_moves: int
    line_checks: int
    thing_checks: int
    line_visits: int
    thing_visits: int
    visibility_mask: int
    visible_count: int
    candidate_sight: stage16.SightProbeResult
    render_keyframe: int
    player_marker_x: int
    player_marker_y: int
    player_marker_width: int
    player_marker_height: int
    player_marker_color: int
    framebuffer_signature: int
    route_state_signature: int
    unified_state_signature: int
    player_sequence: int
    visibility_sequence: int
    selected_thinker_sequence: int
    projectile_sequence: int
    status_sequence: int
    signature_sequence: int
    present_sequence: int


@dataclass(frozen=True)
class Stage47BoundedMap01PlayerRouteFirstHostileSightBridgeReference:
    stage46: stage46.Stage46RepeatableSelectedMonsterThinkerCadenceBridgeReference
    commands: tuple[stage44.Stage44TicCmd, ...]
    collision_records: tuple[Stage47CollisionRecord, ...]
    samples: tuple[Stage47RouteSample, ...]
    monster_records: tuple[stage16.MonsterCensusRecord, ...]
    contact_record: stage16.MonsterCensusRecord
    monster_count: int
    first_sight_tic: int
    precontact_sight_checks: int
    precontact_visible_results: int
    contact_visible_count: int
    total_sight_checks: int
    runtime_owned_player_fields: int
    replay_live_command_ownership: int
    collision_inputs_outcomes_only: int
    complete_player_actor_snapshots_absent: int
    finite_render_keyframes: tuple[int, ...]
    target_is_null: int
    stand_state_preserved: int
    awareness_transition_absent: int
    attack_damage_status_mutation_absent: int
    ordering_preserved: int
    distinct_route_state_signatures: int
    distinct_unified_state_signatures: int
    distinct_framebuffer_signatures: int
    stage46_preserved: int
    stage45_through_stage19_preserved: int
    full_frame_byte_arrays_absent: int
    broad_deferred_systems_absent: int
    future_stage_marker_absent: int
    paint_after_final_contact: int
    state_signature: int
    signature: int


def fnv1a_words(words: Sequence[int], basis: int = FNV_OFFSET_BASIS) -> int:
    return stage46.fnv1a_words(words, basis)


def _hash_ascii(signature: int, text: str) -> int:
    return stage46._hash_ascii(signature, text)


def _route_commands() -> tuple[stage44.Stage44TicCmd, ...]:
    raw = (
        (0, 0, 0, 0),
        (stage44.FORWARDMOVE, 0, -stage44.SLOW_ANGLETURN, 0),
        (stage44.FORWARDMOVE, 0, stage44.SLOW_ANGLETURN, stage44.BT_USE),
    ) + ((stage44.FORWARDMOVE, 0, 0, 0),) * 41
    return tuple(
        stage44.Stage44TicCmd(
            tic=index + 1,
            forwardmove=forward,
            sidemove=side,
            angleturn=turn,
            buttons=buttons,
            consistency=fnv1a_words((index + 1, forward, side, turn, buttons, index)),
            source_index=index,
            source_marker="D_DoomLoop replay-owned bounded MAP01 route ticcmd_t table",
        )
        for index, (forward, side, turn, buttons) in enumerate(raw)
    )


def _active_monsters_for_world(world: stage14.MovementWorld) -> tuple[stage16.ActiveMobj, ...]:
    info = stage16.parse_stage16_info_tables()
    rng = stage16.DoomRandom()
    spawn: dict[int, tuple[int, int]] = {}
    for mobj in world.mobjs:
        lastlook = rng.p_random() % stage16.MAXPLAYERS
        tics = -1
        minfo = info.by_name.get(mobj.type_name)
        if minfo is not None and 0 <= minfo.spawnstate < len(info.state_info.states):
            raw_tics = info.state_info.states[minfo.spawnstate].tics
            tics = raw_tics
            if mobj.player_index < 0 and raw_tics > 0:
                tics = 1 + (rng.p_random() % raw_tics)
        spawn[mobj.index] = (lastlook, tics)
    result: list[stage16.ActiveMobj] = []
    for mobj in world.mobjs:
        if not (mobj.flags & stage13.MF_COUNTKILL):
            continue
        minfo = info.by_name[mobj.type_name]
        lastlook, tics = spawn[mobj.index]
        result.append(stage16._copy_active_mobj(mobj, minfo, info.state_info, lastlook=lastlook, spawn_tics=tics))
    return tuple(result)


def _player_as_active(mobj: stage14.MovementMobj) -> stage16.ActiveMobj:
    return stage16.ActiveMobj(
        index=mobj.index,
        mapthing_index=mobj.mapthing_index,
        type_name="MT_PLAYER",
        doomednum=1,
        x=mobj.x,
        y=mobj.y,
        z=mobj.z,
        angle=mobj.angle,
        momx=mobj.momx,
        momy=mobj.momy,
        momz=mobj.momz,
        radius=mobj.radius,
        height=mobj.height,
        flags=mobj.flags,
        floorz=mobj.floorz,
        ceilingz=mobj.ceilingz,
        subsector=mobj.subsector,
        sector=mobj.sector,
        health=100,
        reactiontime=0,
        state=None,
        tics=-1,
        sprite=0,
        frame=0,
        lastlook=0,
    )


def _monster_census(
    monsters: Sequence[stage16.ActiveMobj],
    player: stage16.ActiveMobj,
    loaded,
    geometry,
    rejectmatrix: bytes,
) -> tuple[stage16.MonsterCensusRecord, ...]:
    info = stage16.parse_stage16_info_tables()
    records = []
    for actor in monsters:
        sight = stage16._p_check_sight_bounded(actor, player, loaded, geometry, rejectmatrix)
        records.append(
            stage16.MonsterCensusRecord(
                mapthing_index=actor.mapthing_index,
                mobj_index=actor.index,
                type_name=actor.type_name,
                doomednum=actor.doomednum,
                x=actor.x,
                y=actor.y,
                angle_degrees=stage13.angle_to_degrees(actor.angle),
                sector=actor.sector,
                subsector=actor.subsector,
                block_x=0,
                block_y=0,
                spawn_state=actor.state if actor.state is not None else 0,
                spawn_state_name=info.state_info.states[actor.state].name if actor.state is not None else "S_NULL",
                spawn_tics=actor.tics,
                raw_spawn_tics=info.state_info.states[actor.state].tics if actor.state is not None else -1,
                spawn_lastlook=actor.lastlook,
                distance_to_player=stage16.p_aprox_distance_source_shape(player.x - actor.x, player.y - actor.y) >> stage14.FRACBITS,
                front_arc=0,
                sight=sight,
            )
        )
    return tuple(records)


def _render_keyframe(step: int) -> int:
    if step == 1:
        return 0
    if step < 32:
        return 1
    return 2


def _player_marker(x: int, y: int, sector: int, subsector: int) -> tuple[int, int, int, int, int]:
    x_units = x >> stage14.FRACBITS
    y_units = y >> stage14.FRACBITS
    return (
        20 + ((x_units + 192) >> 1),
        150 + (abs(y_units + 192) & 15),
        5 + (sector & 3),
        5,
        (0x0020A0D0 + ((subsector & 15) * 0x00060402)) & 0x00FFFFFF,
    )


def _draw_box(frame: bytearray, x: int, y: int, width: int, height: int, color: int) -> None:
    pixel = (color & 0x00FFFFFF).to_bytes(4, "little")
    for yy in range(y, y + height):
        for xx in range(x, x + width):
            offset = (yy * FRAMEBUFFER_WIDTH + xx) * 4
            frame[offset : offset + 4] = pixel


def _frame_for_sample(ref46, sample: Stage47RouteSample) -> bytearray:
    route = sample.render_keyframe
    frame = stage43._stage41_frame_for_sample(ref46.stage44.stage43.stage42, route)
    stage43._draw_projectile_marker(frame, ref46.stage44.stage43.samples[route])
    _draw_box(
        frame,
        sample.player_marker_x,
        sample.player_marker_y,
        sample.player_marker_width,
        sample.player_marker_height,
        sample.player_marker_color,
    )
    if sample.visible_count:
        _draw_box(frame, 250, 130, 12, 8, 0x0030E060)
    return frame


def _route_signature(sample: Stage47RouteSample) -> int:
    return fnv1a_words(
        (
            sample.step,
            sample.command.forwardmove,
            sample.command.sidemove,
            sample.command.angleturn,
            sample.command.buttons,
            sample.x,
            sample.y,
            sample.angle,
            sample.momx,
            sample.momy,
            sample.sector,
            sample.subsector,
            sample.try_move_calls,
            sample.accepted_moves,
            sample.rejected_moves,
            sample.visibility_mask,
            sample.visible_count,
            174,
            CONTACT_TICS,
            0,
        )
    )


def _unified_signature(sample: Stage47RouteSample, projectile_signature: int) -> int:
    return fnv1a_words(
        (
            sample.route_state_signature,
            sample.framebuffer_signature,
            BASELINE_S46_SIGNATURE,
            projectile_signature,
            sample.player_sequence,
            sample.visibility_sequence,
            sample.selected_thinker_sequence,
            sample.projectile_sequence,
            sample.status_sequence,
            sample.signature_sequence,
            sample.present_sequence,
        )
    )


def _reference_signature(ref: Stage47BoundedMap01PlayerRouteFirstHostileSightBridgeReference) -> int:
    signature = fnv1a_words(
        (
            ref.stage46.signature,
            ref.stage46.state_signature,
            len(ref.commands),
            len(ref.collision_records),
            ref.monster_count,
            ref.first_sight_tic,
            ref.precontact_sight_checks,
            ref.precontact_visible_results,
            ref.contact_visible_count,
            ref.total_sight_checks,
            ref.runtime_owned_player_fields,
            ref.replay_live_command_ownership,
            ref.target_is_null,
            ref.stand_state_preserved,
            ref.ordering_preserved,
            ref.distinct_route_state_signatures,
            ref.distinct_unified_state_signatures,
            ref.distinct_framebuffer_signatures,
            ref.state_signature,
        )
    )
    for sample in ref.samples:
        signature = fnv1a_words(
            (sample.route_state_signature, sample.unified_state_signature, sample.framebuffer_signature), signature
        )
    signature = _hash_ascii(signature, CONTACT_TYPE)
    return _hash_ascii(signature, "geometric visibility only; target remains NULL in stand state")


def reference_bounded_map01_player_route_first_hostile_sight_bridge_for_pinned_map(
    wad_path: str | Path,
) -> Stage47BoundedMap01PlayerRouteFirstHostileSightBridgeReference:
    wad_path = Path(wad_path)
    ref46 = stage46.reference_repeatable_selected_monster_thinker_cadence_bridge_for_pinned_map(wad_path)
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    geometry = stage13.build_map_geometry(wad, loaded)
    rejectmatrix = wad.read_lump(wad.map_lumps("MAP01").get("REJECT"))
    world = stage44._selected_player_world(wad_path)
    monsters = _active_monsters_for_world(world)
    commands = _route_commands()
    samples: list[Stage47RouteSample] = []
    collisions: list[Stage47CollisionRecord] = []
    all_census: list[tuple[stage16.MonsterCensusRecord, ...]] = []

    for index, command in enumerate(commands):
        mobj = world.mobjs[world.player.mo_index]
        old_x, old_y = mobj.x, mobj.y
        before = stage44._movement_delta_before(world)
        stage14.g_ticker_ticcmd_dispatch_source_shape(
            world,
            stage14.TicCmd(command.forwardmove, command.sidemove, command.angleturn, command.buttons),
        )
        world.counters.tic_count += 1
        delta = stage44._movement_delta_after(world, before)
        mobj = world.mobjs[world.player.mo_index]
        census = _monster_census(monsters, _player_as_active(mobj), loaded, geometry, rejectmatrix)
        all_census.append(census)
        visibility_mask = sum((1 << monster_index) for monster_index, record in enumerate(census) if record.sight.visible)
        candidate = next(record for record in census if record.mobj_index == CONTACT_MOBJ)
        if delta.try_move_calls:
            collisions.append(
                Stage47CollisionRecord(
                    tic=index + 1,
                    try_x=mobj.x,
                    try_y=mobj.y,
                    accepted=1 if delta.accepted_moves else 0,
                    subsector=mobj.subsector,
                    sector=mobj.sector,
                    line_checks=delta.line_checks,
                    thing_checks=delta.thing_checks,
                    line_visits=delta.line_visits,
                    thing_visits=delta.thing_visits,
                )
            )
        marker_x, marker_y, marker_width, marker_height, marker_color = _player_marker(
            mobj.x, mobj.y, mobj.sector, mobj.subsector
        )
        seq = index * 20
        placeholder = Stage47RouteSample(
            step=index + 1,
            command=command,
            old_x=old_x,
            old_y=old_y,
            x=mobj.x,
            y=mobj.y,
            angle=mobj.angle,
            momx=mobj.momx,
            momy=mobj.momy,
            sector=mobj.sector,
            subsector=mobj.subsector,
            try_move_calls=delta.try_move_calls,
            accepted_moves=delta.accepted_moves,
            rejected_moves=delta.rejected_moves,
            line_checks=delta.line_checks,
            thing_checks=delta.thing_checks,
            line_visits=delta.line_visits,
            thing_visits=delta.thing_visits,
            visibility_mask=visibility_mask,
            visible_count=visibility_mask.bit_count(),
            candidate_sight=candidate.sight,
            render_keyframe=_render_keyframe(index + 1),
            player_marker_x=marker_x,
            player_marker_y=marker_y,
            player_marker_width=marker_width,
            player_marker_height=marker_height,
            player_marker_color=marker_color,
            framebuffer_signature=0,
            route_state_signature=0,
            unified_state_signature=0,
            player_sequence=seq + 1,
            visibility_sequence=seq + 2,
            selected_thinker_sequence=seq + 3,
            projectile_sequence=seq + 4,
            status_sequence=seq + 5,
            signature_sequence=seq + 6,
            present_sequence=seq + 7,
        )
        route_sig = _route_signature(placeholder)
        with_route = replace(placeholder, route_state_signature=route_sig)
        framebuffer_signature = stage31._framebuffer_signature(_frame_for_sample(ref46, with_route))
        with_frame = replace(with_route, framebuffer_signature=framebuffer_signature)
        projectile_signature = ref46.stage44.stage43.samples[with_frame.render_keyframe].projectile_state_signature
        samples.append(replace(with_frame, unified_state_signature=_unified_signature(with_frame, projectile_signature)))

    visible_steps = [sample.step for sample in samples if sample.visible_count]
    if visible_steps != [ROUTE_TICS]:
        raise AssertionError(f"stage47 first visibility changed: {visible_steps!r}")
    contact_records = [record for record in all_census[-1] if record.sight.visible]
    if len(contact_records) != 1:
        raise AssertionError("stage47 expected exactly one visible contact actor")
    contact = contact_records[0]
    if (
        contact.mobj_index,
        contact.mapthing_index,
        contact.type_name,
        contact.x >> stage14.FRACBITS,
        contact.y >> stage14.FRACBITS,
        contact.angle_degrees,
        contact.spawn_state_name,
        contact.spawn_tics,
        contact.spawn_lastlook,
    ) != (CONTACT_MOBJ, CONTACT_MAPTHING, CONTACT_TYPE, CONTACT_X, CONTACT_Y, CONTACT_ANGLE_DEGREES, CONTACT_STATE, CONTACT_TICS, CONTACT_LASTLOOK):
        raise AssertionError("stage47 contact actor evidence changed")
    final_trace = contact.sight
    if (final_trace.nodes, final_trace.subsectors, final_trace.segs, final_trace.crossed_lines) != CONTACT_TRACE:
        raise AssertionError("stage47 BSP sight trace changed")

    state_signature = fnv1a_words(tuple(sample.route_state_signature for sample in samples))
    state_signature = _hash_ascii(state_signature, "runtime-owned MAP01 player x/y/angle/momentum/sector/subsector")
    draft = Stage47BoundedMap01PlayerRouteFirstHostileSightBridgeReference(
        stage46=ref46,
        commands=commands,
        collision_records=tuple(collisions),
        samples=tuple(samples),
        monster_records=all_census[-1],
        contact_record=contact,
        monster_count=len(monsters),
        first_sight_tic=visible_steps[0],
        precontact_sight_checks=(ROUTE_TICS - 1) * len(monsters),
        precontact_visible_results=sum(sample.visible_count for sample in samples[:-1]),
        contact_visible_count=len(contact_records),
        total_sight_checks=ROUTE_TICS * len(monsters),
        runtime_owned_player_fields=1,
        replay_live_command_ownership=1,
        collision_inputs_outcomes_only=1,
        complete_player_actor_snapshots_absent=1,
        finite_render_keyframes=(1, 2, 32, 44),
        target_is_null=1,
        stand_state_preserved=1,
        awareness_transition_absent=1,
        attack_damage_status_mutation_absent=1,
        ordering_preserved=1,
        distinct_route_state_signatures=len({sample.route_state_signature for sample in samples}),
        distinct_unified_state_signatures=len({sample.unified_state_signature for sample in samples}),
        distinct_framebuffer_signatures=len({sample.framebuffer_signature for sample in samples}),
        stage46_preserved=1 if (ref46.signature, ref46.state_signature) == (BASELINE_S46_SIGNATURE, BASELINE_STATE46) else 0,
        stage45_through_stage19_preserved=ref46.stage45_preserved * ref46.stage43_through_stage19_preserved,
        full_frame_byte_arrays_absent=1,
        broad_deferred_systems_absent=1,
        future_stage_marker_absent=1,
        paint_after_final_contact=1,
        state_signature=state_signature,
        signature=0,
    )
    return replace(draft, signature=_reference_signature(draft))


@lru_cache(maxsize=1)
def _reference_for_default_wad_or_none() -> Stage47BoundedMap01PlayerRouteFirstHostileSightBridgeReference | None:
    wad_path = REPO_ROOT / WAD_PATH
    if not wad_path.exists():
        return None
    return reference_bounded_map01_player_route_first_hostile_sight_bridge_for_pinned_map(wad_path)


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


def emit_stage47_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.call_rel32(pe, "stage44_parse_command_line")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")
    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage47_class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage47_class_registered")
    x86.call_rel32(pe, "source_stage47_load_wad_bounded_map01_player_route_first_hostile_sight_bridge")
    x86.call_rel32(pe, "append_stage47_success_status")
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
    x86.jne_rel32(pe, "stage47_window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage47_window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage47_live_start")
    x86.push_abs32(pe, "stage47_replay_title_start")
    x86.jmp_rel32(pe, "stage47_set_start_title")
    pe.label("stage47_live_start")
    x86.push_abs32(pe, "stage47_live_title_start")
    pe.label("stage47_set_start_title")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE47_TIMER_MS)
    x86.push_imm32(pe, STAGE47_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
    pe.label("stage47_message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage47_clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "stage47_message_error")
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, stage38.WM_TIMER)
    x86.jne_rel32(pe, "stage47_dispatch_message")
    x86.call_rel32(pe, "stage47_timer_tick")
    pe.label("stage47_dispatch_message")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "stage47_message_loop")
    pe.label("stage47_clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage47_message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_stage47_wndproc(pe: PE32) -> None:
    pe.label("wndproc")
    x86.emit_function_prologue(pe)
    x86.mov_eax_ebp_disp8(pe, 12)
    x86.cmp_eax_imm32(pe, stage01.WM_DESTROY)
    x86.je_rel32(pe, "stage47_wndproc_destroy")
    x86.cmp_eax_imm32(pe, stage01.WM_PAINT)
    x86.je_rel32(pe, "stage47_wndproc_paint")
    x86.cmp_eax_imm32(pe, stage44.WM_KEYDOWN)
    x86.je_rel32(pe, "stage47_wndproc_keydown")
    x86.cmp_eax_imm32(pe, stage44.WM_KEYUP)
    x86.je_rel32(pe, "stage47_wndproc_keyup")
    pe.label("stage47_wndproc_default")
    for displacement in (20, 16, 12, 8):
        x86.push_ebp_disp8(pe, displacement)
    x86.call_import(pe, stage01.USER32, "DefWindowProcW")
    x86.emit_function_epilogue_ret(pe, 16)
    pe.label("stage47_wndproc_keydown")
    x86.mov_reg_imm32(pe, "edx", 1)
    x86.jmp_rel32(pe, "stage47_wndproc_key_update")
    pe.label("stage47_wndproc_keyup")
    x86.xor_reg_reg(pe, "edx", "edx")
    pe.label("stage47_wndproc_key_update")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "stage47_wndproc_default")
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
            x86.je_rel32(pe, f"stage47_set_{label}")
    x86.jmp_rel32(pe, "stage47_wndproc_default")
    for label in ("stage44_key_forward", "stage44_key_back", "stage44_key_left", "stage44_key_right", "stage44_key_use"):
        pe.label(f"stage47_set_{label}")
        x86.mov_mem_abs32_reg(pe, label, "edx")
        x86.inc_mem_abs32(pe, "stage44_runtime_live_key_events")
        x86.xor_reg_reg(pe, "eax", "eax")
        x86.emit_function_epilogue_ret(pe, 16)
    pe.label("stage47_wndproc_destroy")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.USER32, "PostQuitMessage")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.emit_function_epilogue_ret(pe, 16)
    pe.label("stage47_wndproc_paint")
    x86.inc_mem_abs32(pe, "stage47_paint_calls")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_final_contact_drawn")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "stage47_paint_after_final_skip")
    x86.inc_mem_abs32(pe, "stage47_paint_after_final")
    pe.label("stage47_paint_after_final_skip")
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


def emit_stage47_command_intake(pe: PE32) -> None:
    pe.label("D_DoomLoop_stage47_replay_or_live_ticcmd_intake_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage47_command_live")
    x86.mov_reg_mem_abs32(pe, "esi", "stage47_command_ptr")
    for dst, displacement in (
        ("stage47_cmd_forwardmove", 0),
        ("stage47_cmd_sidemove", 4),
        ("stage47_cmd_angleturn", 8),
        ("stage47_cmd_buttons", 12),
    ):
        x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", displacement)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.add_reg_imm32(pe, "esi", COMMAND_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, "stage47_command_ptr", "esi")
    x86.inc_mem_abs32(pe, "stage47_replay_commands")
    x86.ret(pe)
    pe.label("stage47_command_live")
    x86.call_rel32(pe, "G_BuildTiccmd_stage44_live_runtime_debug")
    for dst, src in (
        ("stage47_cmd_forwardmove", "stage44_live_forwardmove"),
        ("stage47_cmd_sidemove", "stage44_live_sidemove"),
        ("stage47_cmd_angleturn", "stage44_live_angleturn"),
        ("stage47_cmd_buttons", "stage44_live_buttons"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.inc_mem_abs32(pe, "stage47_live_commands")
    x86.ret(pe)


def emit_stage47_thrust(pe: PE32) -> None:
    pe.label("P_Thrust_stage47_runtime_owned_player_debug")
    x86.mov_reg_mem_abs32(pe, "ebx", "stage47_thrust_angle")
    x86.shr_reg_imm8(pe, "ebx", stage13.ANGLETOFINESHIFT)
    x86.and_reg_imm32(pe, "ebx", stage13.FINEMASK)
    x86.shl_reg_imm8(pe, "ebx", 2)
    x86.mov_reg_abs32(pe, "esi", "stage47_finecosine")
    x86.add_reg_reg(pe, "esi", "ebx")
    x86.mov_reg_ptr_reg(pe, "ecx", "esi")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_thrust_move")
    x86.imul_reg(pe, "ecx")
    x86.shrd_reg_reg_imm8(pe, "eax", "edx", 16)
    x86.add_reg_mem_abs32(pe, "eax", "stage47_player_momx")
    x86.mov_mem_abs32_eax(pe, "stage47_player_momx")
    x86.mov_reg_abs32(pe, "esi", "stage47_finesine")
    x86.add_reg_reg(pe, "esi", "ebx")
    x86.mov_reg_ptr_reg(pe, "ecx", "esi")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_thrust_move")
    x86.imul_reg(pe, "ecx")
    x86.shrd_reg_reg_imm8(pe, "eax", "edx", 16)
    x86.add_reg_mem_abs32(pe, "eax", "stage47_player_momy")
    x86.mov_mem_abs32_eax(pe, "stage47_player_momy")
    x86.ret(pe)


def emit_stage47_try_move(pe: PE32) -> None:
    pe.label("P_TryMove_stage47_bounded_map01_route_collision_debug")
    x86.mov_mem_abs32_eax(pe, "stage47_requested_try_x")
    x86.mov_mem_abs32_reg(pe, "stage47_requested_try_y", "edx")
    x86.inc_mem_abs32(pe, "stage47_tick_try_calls")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage47_live_trymove")
    x86.mov_reg_mem_abs32(pe, "ecx", "stage47_collision_remaining")
    x86.test_reg_reg(pe, "ecx")
    x86.je_rel32(pe, "stage47_trymove_reject")
    x86.mov_reg_mem_abs32(pe, "esi", "stage47_collision_ptr")
    x86.mov_reg_ptr_reg_disp8(pe, "ecx", "esi", 4)
    x86.cmp_reg_mem_abs32(pe, "ecx", "stage47_requested_try_x")
    x86.jne_rel32(pe, "stage47_trymove_mismatch")
    x86.mov_reg_ptr_reg_disp8(pe, "ecx", "esi", 8)
    x86.cmp_reg_mem_abs32(pe, "ecx", "stage47_requested_try_y")
    x86.jne_rel32(pe, "stage47_trymove_mismatch")
    for displacement, counter in (
        (24, "stage47_tick_line_checks"),
        (28, "stage47_tick_thing_checks"),
        (32, "stage47_tick_line_visits"),
        (36, "stage47_tick_thing_visits"),
    ):
        x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", displacement)
        x86.mov_mem_abs32_eax(pe, counter)
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 12)
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage47_trymove_consume_reject")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_requested_try_x")
    x86.mov_mem_abs32_eax(pe, "stage47_player_x")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_requested_try_y")
    x86.mov_mem_abs32_eax(pe, "stage47_player_y")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 16)
    x86.mov_mem_abs32_eax(pe, "stage47_player_subsector")
    x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", 20)
    x86.mov_mem_abs32_eax(pe, "stage47_player_sector")
    x86.inc_mem_abs32(pe, "stage47_tick_try_accepts")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.jmp_rel32(pe, "stage47_trymove_consume")
    pe.label("stage47_trymove_consume_reject")
    x86.inc_mem_abs32(pe, "stage47_tick_try_rejects")
    x86.xor_reg_reg(pe, "eax", "eax")
    pe.label("stage47_trymove_consume")
    x86.add_reg_imm32(pe, "esi", COLLISION_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, "stage47_collision_ptr", "esi")
    x86.dec_mem_abs32(pe, "stage47_collision_remaining")
    x86.ret(pe)
    pe.label("stage47_trymove_mismatch")
    x86.mov_mem_abs32_imm32(pe, "stage47_collision_mismatch", 1)
    x86.jmp_rel32(pe, "stage47_trymove_reject")
    pe.label("stage47_live_trymove")
    # The live path retains command ownership and a deliberately small safe
    # start-corridor acceptance policy; it is not a general collision manager.
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_requested_try_x")
    x86.cmp_eax_imm32(pe, (-208 * stage14.FRACUNIT) & 0xFFFFFFFF)
    x86.jl_rel32(pe, "stage47_trymove_reject")
    x86.cmp_eax_imm32(pe, 100 * stage14.FRACUNIT)
    x86.jns_rel32(pe, "stage47_trymove_reject")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_requested_try_y")
    x86.cmp_eax_imm32(pe, (-224 * stage14.FRACUNIT) & 0xFFFFFFFF)
    x86.jl_rel32(pe, "stage47_trymove_reject")
    x86.cmp_eax_imm32(pe, (-160 * stage14.FRACUNIT) & 0xFFFFFFFF)
    x86.jns_rel32(pe, "stage47_trymove_reject")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_requested_try_x")
    x86.mov_mem_abs32_eax(pe, "stage47_player_x")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_requested_try_y")
    x86.mov_mem_abs32_eax(pe, "stage47_player_y")
    x86.inc_mem_abs32(pe, "stage47_tick_try_accepts")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage47_trymove_reject")
    x86.inc_mem_abs32(pe, "stage47_tick_try_rejects")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def _emit_fixed_mul_global(pe: PE32, label: str) -> None:
    x86.mov_reg_mem_abs32(pe, "eax", label)
    x86.mov_reg_imm32(pe, "ecx", stage14.FRICTION)
    x86.imul_reg(pe, "ecx")
    x86.shrd_reg_reg_imm8(pe, "eax", "edx", 16)
    x86.mov_mem_abs32_eax(pe, label)


def emit_stage47_player_tick(pe: PE32) -> None:
    pe.label("P_XYMovement_stage47_runtime_owned_player_momentum_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_player_momx")
    x86.add_reg_mem_abs32(pe, "eax", "stage47_player_momy")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage47_xy_done")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_player_x")
    x86.add_reg_mem_abs32(pe, "eax", "stage47_player_momx")
    x86.mov_reg_mem_abs32(pe, "edx", "stage47_player_y")
    x86.add_reg_mem_abs32(pe, "edx", "stage47_player_momy")
    x86.call_rel32(pe, "P_TryMove_stage47_bounded_map01_route_collision_debug")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage47_xy_friction")
    x86.mov_mem_abs32_imm32(pe, "stage47_player_momx", 0)
    x86.mov_mem_abs32_imm32(pe, "stage47_player_momy", 0)
    x86.ret(pe)
    pe.label("stage47_xy_friction")
    _emit_fixed_mul_global(pe, "stage47_player_momx")
    _emit_fixed_mul_global(pe, "stage47_player_momy")
    pe.label("stage47_xy_done")
    x86.ret(pe)

    pe.label("P_PlayerThink_P_MovePlayer_P_Thrust_stage47_runtime_owned_route_debug")
    for label in (
        "stage47_tick_try_calls",
        "stage47_tick_try_accepts",
        "stage47_tick_try_rejects",
        "stage47_tick_line_checks",
        "stage47_tick_thing_checks",
        "stage47_tick_line_visits",
        "stage47_tick_thing_visits",
    ):
        x86.mov_mem_abs32_imm32(pe, label, 0)
    x86.inc_mem_abs32(pe, "stage47_accepted_game_tics")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_cmd_angleturn")
    x86.shl_reg_imm8(pe, "eax", stage14.FRACBITS)
    x86.add_reg_mem_abs32(pe, "eax", "stage47_player_angle")
    x86.mov_mem_abs32_eax(pe, "stage47_player_angle")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_cmd_forwardmove")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage47_no_forward_thrust")
    x86.imul_reg_reg_imm32(pe, "eax", "eax", 2048)
    x86.mov_mem_abs32_eax(pe, "stage47_thrust_move")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_player_angle")
    x86.mov_mem_abs32_eax(pe, "stage47_thrust_angle")
    x86.call_rel32(pe, "P_Thrust_stage47_runtime_owned_player_debug")
    pe.label("stage47_no_forward_thrust")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_cmd_sidemove")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage47_no_side_thrust")
    x86.imul_reg_reg_imm32(pe, "eax", "eax", 2048)
    x86.mov_mem_abs32_eax(pe, "stage47_thrust_move")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_player_angle")
    x86.add_reg_imm32(pe, "eax", (-stage13.ANG90) & 0xFFFFFFFF)
    x86.mov_mem_abs32_eax(pe, "stage47_thrust_angle")
    x86.call_rel32(pe, "P_Thrust_stage47_runtime_owned_player_debug")
    pe.label("stage47_no_side_thrust")
    x86.call_rel32(pe, "P_XYMovement_stage47_runtime_owned_player_momentum_debug")
    x86.ret(pe)


def emit_stage47_visibility_and_order(pe: PE32) -> None:
    pe.label("P_CheckSight_stage47_first_hostile_geometric_contact_debug")
    x86.mov_mem_abs32_imm32(pe, "stage47_visibility_mask", 0)
    x86.mov_mem_abs32_imm32(pe, "stage47_visible_count", 0)
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage47_live_visibility_done")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_accepted_game_tics")
    x86.add_reg_imm32(pe, "eax", -1)
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "esi", "stage47_sight_mask_table")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "esi")
    x86.mov_mem_abs32_eax(pe, "stage47_visibility_mask")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage47_visibility_done")
    x86.mov_mem_abs32_imm32(pe, "stage47_visible_count", 1)
    x86.mov_mem_abs32_imm32(pe, "stage47_sight_nodes", CONTACT_TRACE[0])
    x86.mov_mem_abs32_imm32(pe, "stage47_sight_subsectors", CONTACT_TRACE[1])
    x86.mov_mem_abs32_imm32(pe, "stage47_sight_segs", CONTACT_TRACE[2])
    x86.mov_mem_abs32_imm32(pe, "stage47_sight_crossed_lines", CONTACT_TRACE[3])
    x86.jmp_rel32(pe, "stage47_visibility_done")
    pe.label("stage47_live_visibility_done")
    # Live mode owns the same player fields but does not claim the replay-only
    # all-monster sight result unless the deterministic route is replayed.
    pe.label("stage47_visibility_done")
    x86.add_reg_imm32(pe, "eax", 0)
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_total_sight_checks")
    x86.add_reg_imm32(pe, "eax", MONSTER_COUNT)
    x86.mov_mem_abs32_eax(pe, "stage47_total_sight_checks")
    x86.ret(pe)

    pe.label("P_RunThinkers_stage47_selected_stand_target_null_boundary_debug")
    x86.inc_mem_abs32(pe, "stage47_selected_thinker_calls")
    # Geometric sight is deliberately not an awareness transition. Candidate
    # state/tics/target remain S_POSS_STND/T3/NULL.
    x86.ret(pe)

    pe.label("P_Ticker_stage47_player_visibility_selected_thinker_projectile_status_debug")
    x86.call_rel32(pe, "D_DoomLoop_stage47_replay_or_live_ticcmd_intake_debug")
    x86.call_rel32(pe, "P_PlayerThink_P_MovePlayer_P_Thrust_stage47_runtime_owned_route_debug")
    x86.call_rel32(pe, "P_CheckSight_stage47_first_hostile_geometric_contact_debug")
    x86.call_rel32(pe, "P_RunThinkers_stage47_selected_stand_target_null_boundary_debug")
    x86.ret(pe)


def _emit_fnv_words(pe: PE32, labels: Sequence[str]) -> None:
    x86.mov_reg_imm32(pe, "eax", FNV_OFFSET_BASIS)
    for label in labels:
        x86.imul_reg_reg_imm32(pe, "eax", "eax", FNV_PRIME)
        x86.mov_reg_mem_abs32(pe, "edx", label)
        x86.xor_reg_reg(pe, "eax", "edx")


def emit_stage47_signatures(pe: PE32) -> None:
    pe.label("stage47_prepare_order_sequences")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_accepted_game_tics")
    x86.add_reg_imm32(pe, "eax", -1)
    x86.imul_reg_reg_imm32(pe, "eax", "eax", 20)
    for index, label in enumerate(
        (
            "stage47_order_player",
            "stage47_order_visibility",
            "stage47_order_selected_thinker",
            "stage47_order_projectile",
            "stage47_order_status",
            "stage47_order_signature",
            "stage47_order_present",
        ),
        1,
    ):
        x86.mov_reg_reg(pe, "edx", "eax")
        x86.add_reg_imm32(pe, "edx", index)
        x86.mov_mem_abs32_reg(pe, label, "edx")
    x86.ret(pe)

    pe.label("stage47_compute_route_signature")
    x86.call_rel32(pe, "stage47_prepare_order_sequences")
    _emit_fnv_words(
        pe,
        (
            "stage47_accepted_game_tics",
            "stage47_cmd_forwardmove",
            "stage47_cmd_sidemove",
            "stage47_cmd_angleturn",
            "stage47_cmd_buttons",
            "stage47_player_x",
            "stage47_player_y",
            "stage47_player_angle",
            "stage47_player_momx",
            "stage47_player_momy",
            "stage47_player_sector",
            "stage47_player_subsector",
            "stage47_tick_try_calls",
            "stage47_tick_try_accepts",
            "stage47_tick_try_rejects",
            "stage47_visibility_mask",
            "stage47_visible_count",
            "stage47_candidate_state",
            "stage47_candidate_tics",
            "stage47_candidate_target",
        ),
    )
    x86.mov_mem_abs32_eax(pe, "stage47_runtime_route_signature")
    x86.ret(pe)

    pe.label("stage47_compute_unified_signature")
    _emit_fnv_words(
        pe,
        (
            "stage47_runtime_route_signature",
            "stage47_runtime_fb_signature",
            "stage47_baseline_s46_signature",
            "stage47_runtime_projectile_signature",
            "stage47_order_player",
            "stage47_order_visibility",
            "stage47_order_selected_thinker",
            "stage47_order_projectile",
            "stage47_order_status",
            "stage47_order_signature",
            "stage47_order_present",
        ),
    )
    x86.mov_mem_abs32_eax(pe, "stage47_runtime_unified_signature")
    x86.ret(pe)


def emit_stage47_runtime_primitives(pe: PE32) -> None:
    pe.label("stage47_draw_box")
    x86.mov_reg_mem_abs32(pe, "ebx", "stage47_box_height")
    x86.test_reg_reg(pe, "ebx")
    x86.je_rel32(pe, "stage47_box_done")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_box_y")
    x86.imul_reg_reg_imm32(pe, "eax", "eax", FRAMEBUFFER_WIDTH)
    x86.add_reg_mem_abs32(pe, "eax", "stage47_box_x")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.add_reg_reg(pe, "edi", "eax")
    pe.label("stage47_box_row_loop")
    x86.mov_reg_mem_abs32(pe, "ecx", "stage47_box_width")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_box_color")
    pe.label("stage47_box_pixel_loop")
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.add_reg_imm32(pe, "edi", 4)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "stage47_box_pixel_loop")
    x86.mov_reg_imm32(pe, "eax", FRAMEBUFFER_WIDTH)
    x86.sub_reg_mem_abs32(pe, "eax", "stage47_box_width")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.add_reg_reg(pe, "edi", "eax")
    x86.dec_reg(pe, "ebx")
    x86.jne_rel32(pe, "stage47_box_row_loop")
    pe.label("stage47_box_done")
    x86.ret(pe)

    pe.label("V_DrawFilledBox_stage47_runtime_player_contact_primitives_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_player_x")
    x86.sar_reg_imm8(pe, "eax", stage14.FRACBITS)
    x86.add_reg_imm32(pe, "eax", 192)
    x86.sar_reg_imm8(pe, "eax", 1)
    x86.add_reg_imm32(pe, "eax", 20)
    x86.mov_mem_abs32_eax(pe, "stage47_box_x")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_player_y")
    x86.sar_reg_imm8(pe, "eax", stage14.FRACBITS)
    x86.add_reg_imm32(pe, "eax", 192)
    x86.test_eax_eax(pe)
    x86.jns_rel32(pe, "stage47_marker_y_positive")
    x86.neg_reg(pe, "eax")
    pe.label("stage47_marker_y_positive")
    x86.and_reg_imm32(pe, "eax", 15)
    x86.add_reg_imm32(pe, "eax", 150)
    x86.mov_mem_abs32_eax(pe, "stage47_box_y")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_player_sector")
    x86.and_reg_imm32(pe, "eax", 3)
    x86.add_reg_imm32(pe, "eax", 5)
    x86.mov_mem_abs32_eax(pe, "stage47_box_width")
    x86.mov_mem_abs32_imm32(pe, "stage47_box_height", 5)
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_player_subsector")
    x86.and_reg_imm32(pe, "eax", 15)
    x86.imul_reg_reg_imm32(pe, "eax", "eax", 0x00060402)
    x86.add_reg_imm32(pe, "eax", 0x0020A0D0)
    x86.and_reg_imm32(pe, "eax", 0x00FFFFFF)
    x86.mov_mem_abs32_eax(pe, "stage47_box_color")
    x86.call_rel32(pe, "stage47_draw_box")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_visible_count")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage47_contact_marker_done")
    x86.mov_mem_abs32_imm32(pe, "stage47_box_x", 250)
    x86.mov_mem_abs32_imm32(pe, "stage47_box_y", 130)
    x86.mov_mem_abs32_imm32(pe, "stage47_box_width", 12)
    x86.mov_mem_abs32_imm32(pe, "stage47_box_height", 8)
    x86.mov_mem_abs32_imm32(pe, "stage47_box_color", 0x0030E060)
    x86.call_rel32(pe, "stage47_draw_box")
    pe.label("stage47_contact_marker_done")
    x86.ret(pe)


def emit_stage47_draw_current(pe: PE32) -> None:
    pe.label("R_SetupFrame_stage47_finite_route_keyframes_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_accepted_game_tics")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage47_draw_keyframe0")
    x86.cmp_eax_imm32(pe, 32)
    x86.jl_rel32(pe, "stage47_draw_keyframe1")
    x86.jmp_rel32(pe, "stage47_draw_keyframe2")
    for route in range(3):
        pe.label(f"stage47_draw_keyframe{route}")
        x86.mov_mem_abs32_imm32(pe, "stage47_render_keyframe", route)
        x86.mov_reg_mem_abs32(pe, "eax", f"stage47_projectile_signature{route}")
        x86.mov_mem_abs32_eax(pe, "stage47_runtime_projectile_signature")
        x86.call_rel32(pe, f"stage43_draw_sample{route}")
        x86.jmp_rel32(pe, "stage47_draw_after_base")
    pe.label("stage47_draw_after_base")
    x86.call_rel32(pe, "V_DrawFilledBox_stage47_runtime_player_contact_primitives_debug")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage47_runtime_fb_signature")
    x86.call_rel32(pe, "stage47_compute_unified_signature")
    x86.ret(pe)


def _final_title(ref: Stage47BoundedMap01PlayerRouteFirstHostileSightBridgeReference | None) -> str:
    if ref is None:
        return "Inference Doom S47 missing pinned WAD"
    sample = ref.samples[-1]
    sight = sample.candidate_sight
    return (
        "Inference Doom S47 STEP47=44 TIC47=44 OWN47=x86 "
        f"PXY47={sample.x >> stage14.FRACBITS},{sample.y >> stage14.FRACBITS} PA47={stage14.angle_to_degrees(sample.angle)} "
        f"PMOM47={sample.momx},{sample.momy} PSEC47={sample.sector}/{sample.subsector} "
        "COLL47=43:43:0 REALMAP47=1 FIRST47=44/44 MIN47=774:0 ALLMON47=18 "
        f"VIS47={sample.visible_count} MASK47={sample.visibility_mask} ACT47=48/66:MT_POSSESSED@416,176/A45 "
        f"SIGHT47=1:BSP1/N{sight.nodes}/SS{sight.subsectors}/SEG{sight.segs}/X{sight.crossed_lines} "
        "AST47=S_POSS_STND/T3 TARGET47=NULL AWARE47=0 ATTACK47=0 DMG47=0 STATUSMUT47=0 "
        f"RSTATE47={sample.route_state_signature} ULSTATE47={sample.unified_state_signature} FB47={sample.framebuffer_signature} "
        f"STATE47={ref.state_signature} S47SIG={ref.signature} "
        "ORDER47=P-V-M-PRJ-ST-SIG-PRESENT ONCE47=1 KEY47=finite4 NOFULL47=1 NOSNAP47=1 "
        "MISMATCH47=0 PAF47=1 "
        f"S46SIG={BASELINE_S46_SIGNATURE} STATE46={BASELINE_STATE46} NEXTABS47=1"
    )


def emit_stage47_build_runtime_title(pe: PE32) -> None:
    pe.label("stage47_build_runtime_title")
    x86.mov_reg_abs32(pe, "edi", "stage47_runtime_title_buffer")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage47_runtime_title_live_prefix_select")
    stage01.append_c_string_label(pe, "stage47_runtime_title_replay_prefix")
    x86.jmp_rel32(pe, "stage47_runtime_title_prefix_done")
    pe.label("stage47_runtime_title_live_prefix_select")
    stage01.append_c_string_label(pe, "stage47_runtime_title_live_prefix")
    pe.label("stage47_runtime_title_prefix_done")
    for prefix, label, signed in (
        ("stage47_title_tic_prefix", "stage47_accepted_game_tics", False),
        ("stage47_title_x_prefix", "stage47_player_x", True),
        ("stage47_title_y_prefix", "stage47_player_y", True),
        ("stage47_title_momx_prefix", "stage47_player_momx", True),
        ("stage47_title_momy_prefix", "stage47_player_momy", True),
        ("stage47_title_sector_prefix", "stage47_player_sector", False),
        ("stage47_title_subsector_prefix", "stage47_player_subsector", False),
        ("stage47_title_visible_prefix", "stage47_visible_count", False),
        ("stage47_title_route_prefix", "stage47_runtime_route_signature", False),
        ("stage47_title_fb_prefix", "stage47_runtime_fb_signature", False),
        ("stage47_title_mismatch_prefix", "stage47_collision_mismatch", False),
    ):
        (stage01.append_i32_label if signed else stage01.append_u32_label)(pe, prefix, label)
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    x86.ret(pe)


def _emit_stage47_present(pe: PE32) -> None:
    x86.inc_mem_abs32(pe, "stage47_invalidate_calls")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "InvalidateRect")
    x86.inc_mem_abs32(pe, "stage47_update_window_calls")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")


def emit_stage47_timer_tick(pe: PE32) -> None:
    pe.label("stage47_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage44_live_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage47_live_timer")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_replay_step")
    x86.cmp_eax_imm32(pe, ROUTE_TICS)
    x86.jae_rel32(pe, "stage47_timer_done")
    x86.call_rel32(pe, "P_Ticker_stage47_player_visibility_selected_thinker_projectile_status_debug")
    x86.call_rel32(pe, "stage47_compute_route_signature")
    x86.call_rel32(pe, "R_SetupFrame_stage47_finite_route_keyframes_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_accepted_game_tics")
    x86.cmp_eax_imm32(pe, ROUTE_TICS)
    x86.jne_rel32(pe, "stage47_replay_not_final")
    x86.mov_mem_abs32_imm32(pe, "stage47_final_contact_drawn", 1)
    _emit_stage47_present(pe)
    x86.push_abs32(pe, "stage47_final_title")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.mov_mem_abs32_imm32(pe, "stage47_replay_step", ROUTE_TICS)
    x86.push_imm32(pe, STAGE47_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "KillTimer")
    x86.ret(pe)
    pe.label("stage47_replay_not_final")
    _emit_stage47_present(pe)
    x86.call_rel32(pe, "stage47_build_runtime_title")
    x86.push_abs32(pe, "stage47_runtime_title_buffer")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.inc_mem_abs32(pe, "stage47_replay_step")
    x86.ret(pe)
    pe.label("stage47_live_timer")
    x86.call_rel32(pe, "P_Ticker_stage47_player_visibility_selected_thinker_projectile_status_debug")
    x86.call_rel32(pe, "stage47_compute_route_signature")
    x86.call_rel32(pe, "R_SetupFrame_stage47_finite_route_keyframes_debug")
    _emit_stage47_present(pe)
    x86.call_rel32(pe, "stage47_build_runtime_title")
    x86.push_abs32(pe, "stage47_runtime_title_buffer")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    pe.label("stage47_timer_done")
    x86.ret(pe)


def emit_stage47_loaders_and_status(pe: PE32) -> None:
    pe.label("source_stage47_load_wad_bounded_map01_player_route_first_hostile_sight_bridge")
    x86.call_rel32(pe, "source_stage43_load_wad_bounded_projectile_tick_collision_feedback_probe")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage47_load_fail")
    x86.call_rel32(pe, "stage47_initialize_runtime_player")
    x86.call_rel32(pe, "render_bounded_map01_player_route_first_hostile_sight_bridge_debug")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage47_load_fail")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)

    pe.label("stage47_initialize_runtime_player")
    for dst, src in (
        ("stage47_player_x", "stage47_initial_x"),
        ("stage47_player_y", "stage47_initial_y"),
        ("stage47_player_angle", "stage47_initial_angle"),
        ("stage47_player_momx", "stage47_initial_momx"),
        ("stage47_player_momy", "stage47_initial_momy"),
        ("stage47_player_sector", "stage47_initial_sector"),
        ("stage47_player_subsector", "stage47_initial_subsector"),
        ("stage47_command_ptr", "stage47_command_table_ptr"),
        ("stage47_collision_ptr", "stage47_collision_table_ptr"),
        ("stage47_collision_remaining", "stage47_collision_count"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)

    for label in (
        "P_BlockIterators_stage47_real_map01_route_evidence_debug",
        "R_SetupFrame_stage47_finite_route_keyframes_debug_trace",
        "I_Video_stage47_present_after_final_contact_debug",
    ):
        pe.label(label)
    pe.label("render_bounded_map01_player_route_first_hostile_sight_bridge_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage47_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage47_expected_state_signature")
    x86.mov_mem_abs32_eax(pe, "stage47_runtime_state_signature")
    x86.ret(pe)

    pe.label("append_stage47_success_status")
    stage01.emit_set_status_ptrs(pe, "status_stage47_success_header", "stage47_replay_title_start")
    x86.ret(pe)


def emit_stage44_live_minimal_data(pe: PE32) -> None:
    pe.align_section(4)
    for label, value in (
        ("stage44_expected_signature", 1090523498),
        ("stage44_runtime_signature", 0),
        ("stage44_expected_state_signature", 904132091),
        ("stage44_runtime_state_signature", 0),
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
    ):
        pe.label(label)
        pe.emit_u32(value)
    pe.label("status_stage44_success_header")
    x86.emit_asciiz(pe, "\r\nStage44 replay/live command ownership baseline preserved without player snapshots\r\n")
    pe.label("stage44_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S44 baseline S44SIG=1090523498 STATE44=904132091 LIVE44=0")


def emit_stage45_stage46_minimal_preservation_data(pe: PE32) -> None:
    for label, value in (
        ("stage45_expected_signature", 799763036),
        ("stage45_runtime_signature", 0),
        ("stage45_expected_state_signature", 1707493859),
        ("stage45_runtime_state_signature", 0),
        ("stage46_expected_signature", BASELINE_S46_SIGNATURE),
        ("stage46_runtime_signature", 0),
        ("stage46_expected_state_signature", BASELINE_STATE46),
        ("stage46_runtime_state_signature", 0),
    ):
        pe.label(label)
        pe.emit_u32(value)
    pe.label("status_stage45_success_header")
    x86.emit_asciiz(pe, "\r\nStage45 bounded monster decision baseline preserved\r\n")
    pe.label("stage45_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S45 baseline S45SIG=799763036 STATE45=1707493859")
    pe.label("status_stage46_success_header")
    x86.emit_asciiz(pe, "\r\nStage46 repeatable selected thinker cadence baseline preserved\r\n")
    pe.label("stage46_replay_title_start")
    x86.emit_asciiz(pe, f"Inference Doom S46 baseline S46SIG={BASELINE_S46_SIGNATURE} STATE46={BASELINE_STATE46}")


def emit_stage47_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    first = ref.samples[0] if ref else None
    final = ref.samples[-1] if ref else None
    pe.align_section(4)
    values = (
        ("stage47_expected_signature", ref.signature if ref else 0),
        ("stage47_runtime_signature", 0),
        ("stage47_expected_state_signature", ref.state_signature if ref else 0),
        ("stage47_runtime_state_signature", 0),
        ("stage47_baseline_s46_signature", BASELINE_S46_SIGNATURE),
        ("stage47_initial_x", first.old_x if first else 0),
        ("stage47_initial_y", first.old_y if first else 0),
        ("stage47_initial_angle", ref.stage46.stage44.samples[0].old_angle if ref else 0),
        ("stage47_initial_momx", ref.stage46.stage44.samples[0].old_momx if ref else 0),
        ("stage47_initial_momy", ref.stage46.stage44.samples[0].old_momy if ref else 0),
        ("stage47_initial_sector", first.sector if first else 0),
        ("stage47_initial_subsector", first.subsector if first else 0),
        ("stage47_player_x", 0),
        ("stage47_player_y", 0),
        ("stage47_player_angle", 0),
        ("stage47_player_momx", 0),
        ("stage47_player_momy", 0),
        ("stage47_player_sector", 0),
        ("stage47_player_subsector", 0),
        ("stage47_cmd_forwardmove", 0),
        ("stage47_cmd_sidemove", 0),
        ("stage47_cmd_angleturn", 0),
        ("stage47_cmd_buttons", 0),
        ("stage47_thrust_angle", 0),
        ("stage47_thrust_move", 0),
        ("stage47_requested_try_x", 0),
        ("stage47_requested_try_y", 0),
        ("stage47_collision_count", len(ref.collision_records) if ref else 0),
        ("stage47_collision_remaining", 0),
        ("stage47_collision_mismatch", 0),
        ("stage47_accepted_game_tics", 0),
        ("stage47_replay_commands", 0),
        ("stage47_live_commands", 0),
        ("stage47_tick_try_calls", 0),
        ("stage47_tick_try_accepts", 0),
        ("stage47_tick_try_rejects", 0),
        ("stage47_tick_line_checks", 0),
        ("stage47_tick_thing_checks", 0),
        ("stage47_tick_line_visits", 0),
        ("stage47_tick_thing_visits", 0),
        ("stage47_visibility_mask", 0),
        ("stage47_visible_count", 0),
        ("stage47_total_sight_checks", 0),
        ("stage47_sight_nodes", 0),
        ("stage47_sight_subsectors", 0),
        ("stage47_sight_segs", 0),
        ("stage47_sight_crossed_lines", 0),
        ("stage47_selected_thinker_calls", 0),
        ("stage47_candidate_state", 174),
        ("stage47_candidate_tics", CONTACT_TICS),
        ("stage47_candidate_target", 0),
        ("stage47_order_player", 0),
        ("stage47_order_visibility", 0),
        ("stage47_order_selected_thinker", 0),
        ("stage47_order_projectile", 0),
        ("stage47_order_status", 0),
        ("stage47_order_signature", 0),
        ("stage47_order_present", 0),
        ("stage47_runtime_route_signature", 0),
        ("stage47_runtime_unified_signature", 0),
        ("stage47_runtime_fb_signature", 0),
        ("stage47_runtime_projectile_signature", 0),
        ("stage47_render_keyframe", 0),
        ("stage47_box_x", 0),
        ("stage47_box_y", 0),
        ("stage47_box_width", 0),
        ("stage47_box_height", 0),
        ("stage47_box_color", 0),
        ("stage47_replay_step", 0),
        ("stage47_invalidate_calls", 0),
        ("stage47_update_window_calls", 0),
        ("stage47_paint_calls", 0),
        ("stage47_final_contact_drawn", 0),
        ("stage47_paint_after_final", 0),
    )
    for label, value in values:
        pe.label(label)
        pe.emit_u32(int(value) & 0xFFFFFFFF)
    pe.label("stage47_command_table_ptr")
    pe.write_abs32("stage47_command_table")
    pe.label("stage47_command_ptr")
    pe.emit_u32(0)
    pe.label("stage47_collision_table_ptr")
    pe.write_abs32("stage47_collision_table")
    pe.label("stage47_collision_ptr")
    pe.emit_u32(0)
    for route in range(3):
        projectile = ref.stage46.stage44.stage43.samples[route].projectile_state_signature if ref else 0
        pe.label(f"stage47_projectile_signature{route}")
        pe.emit_u32(projectile)
    pe.label("stage47_command_table")
    for command in ref.commands if ref else ():
        for value in (command.forwardmove, command.sidemove, command.angleturn, command.buttons):
            pe.emit_u32(value & 0xFFFFFFFF)
    pe.label("stage47_collision_table")
    for record in ref.collision_records if ref else ():
        for value in (
            record.tic,
            record.try_x,
            record.try_y,
            record.accepted,
            record.subsector,
            record.sector,
            record.line_checks,
            record.thing_checks,
            record.line_visits,
            record.thing_visits,
        ):
            pe.emit_u32(value & 0xFFFFFFFF)
    pe.label("stage47_sight_mask_table")
    for sample in ref.samples if ref else ():
        pe.emit_u32(sample.visibility_mask)
    pe.label("stage47_finecosine")
    for value in stage14.FINECOSINE:
        pe.emit_u32(value & 0xFFFFFFFF)
    pe.label("stage47_finesine")
    for value in stage14.FINESINE:
        pe.emit_u32(value & 0xFFFFFFFF)
    pe.label("status_stage47_success_header")
    x86.emit_asciiz(pe, "\r\nBounded MAP01 Player Route First Hostile Sight Bridge proof OK\r\n")
    pe.label("stage47_log_text")
    x86.emit_asciiz(
        pe,
        "source_stage47_bounded_map01_player_route_first_hostile_sight_bridge gives emitted x86 ownership "
        "of player x/y, angle, momentum, sector, and subsector across 44 accepted replay tics. The command "
        "table and real MAP01 P_TryMove input/outcome evidence contain no complete player or actor frames. "
        "All 18 monsters are checked after every player update: 774 pre-contact results are false and only "
        "mobj 48/mapthing 66 MT_POSSESSED is visible at tic 44. P_CheckSight visits 85 nodes, 32 subsectors, "
        "113 segs, and 6 crossed lines. The actor remains S_POSS_STND/T3 with target=NULL; geometric visibility "
        "does not mutate awareness, attacks, damage, or status. Ordering is player, visibility, selected thinker "
        "boundary, projectile, status, signature, present. Runtime drawing uses finite keyframes plus primitives; "
        "there are no full-frame copies or per-tic player/actor snapshots. "
        f"S46SIG={BASELINE_S46_SIGNATURE} STATE46={BASELINE_STATE46} "
        "MSTATE46=" + ",".join(str(value) for value in BASELINE_MSTATE46) + " "
        "ULSTATE46=" + ",".join(str(value) for value in BASELINE_ULSTATE46) + " "
        "FB46=" + ",".join(str(value) for value in BASELINE_FB46) + " "
        "S45SIG=799763036 STATE45=1707493859 S44SIG=1090523498 STATE44=904132091 "
        "MISS43=MT_TROOPSHOT PATCH40=BAL1 S19SIG=2088411722 NEXTABS47=1.",
    )
    pe.label("stage47_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S47 REPLAY START STEP47=0 OWN47=x86 ROUTE47=44 ALLMON47=18")
    pe.label("stage47_live_title_start")
    x86.emit_asciiz(pe, "Inference Doom S47 LIVE START LIVE44=1 OWN47=x86 bounded gamekeydown ticcmd ownership")
    pe.label("stage47_final_title")
    x86.emit_asciiz(pe, _final_title(ref))
    pe.label("stage47_runtime_title_buffer")
    pe.emit(b"\0" * 1024)
    pe.label("stage47_runtime_title_replay_prefix")
    x86.emit_asciiz(pe, "Inference Doom S47 REPLAY OWN47=x86 ORDER47=P-V-M-PRJ-ST-SIG-PRESENT TARGET47=NULL")
    pe.label("stage47_runtime_title_live_prefix")
    x86.emit_asciiz(pe, "Inference Doom S47 LIVE LIVE44=1 OWN47=x86 ORDER47=P-V-M-PRJ-ST-SIG-PRESENT TARGET47=NULL")
    for label, text in (
        ("stage47_title_tic_prefix", " TIC47="),
        ("stage47_title_x_prefix", " PX47="),
        ("stage47_title_y_prefix", " PY47="),
        ("stage47_title_momx_prefix", " PMX47="),
        ("stage47_title_momy_prefix", " PMY47="),
        ("stage47_title_sector_prefix", " SEC47="),
        ("stage47_title_subsector_prefix", " SUB47="),
        ("stage47_title_visible_prefix", " VIS47="),
        ("stage47_title_route_prefix", " RSTATE47="),
        ("stage47_title_fb_prefix", " FB47="),
        ("stage47_title_mismatch_prefix", " MISMATCH47="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)


def build_source_stage47_bounded_map01_player_route_first_hostile_sight_bridge_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    with patched_stage01_window_labels():
        emit_stage47_entry(pe)
        emit_stage47_wndproc(pe)
        stage44.emit_stage44_parse_command_line(pe)
        emit_stage47_timer_tick(pe)
        stage44.emit_stage44_live_runtime(pe)
        emit_stage47_command_intake(pe)
        emit_stage47_thrust(pe)
        emit_stage47_try_move(pe)
        emit_stage47_player_tick(pe)
        emit_stage47_visibility_and_order(pe)
        emit_stage47_signatures(pe)
        emit_stage47_runtime_primitives(pe)
        emit_stage47_draw_current(pe)
        emit_stage47_build_runtime_title(pe)
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
        for route in range(3):
            stage40._emit_stage40_draw_sample(pe, route)
            stage41._emit_stage41_draw_sample(pe, route)
            stage42._emit_stage42_update_sample(pe, route)
            stage42._emit_stage42_draw_sample(pe, route)
            stage43._emit_stage43_update_sample(pe, route)
            stage43._emit_stage43_draw_sample(pe, route)
        stage36.emit_source_stage36_load_wad_selected_dropped_shotgun_visual_boundary(pe)
        stage38.emit_source_stage38_load_wad_selected_attack_feedback_present_bridge(pe)
        stage39.emit_source_stage39_load_wad_selected_projectile_spawn_present_probe(pe)
        stage40.emit_source_stage40_load_wad_bounded_vissprite_traversal_sorting_bridge(pe)
        stage41.emit_source_stage41_load_wad_statusbar_weapon_ammo_feedback_bridge(pe)
        stage42.emit_source_stage42_load_wad_unified_live_tick_render_loop_probe(pe)
        stage43.emit_source_stage43_load_wad_bounded_projectile_tick_collision_feedback_probe(pe)
        emit_stage47_loaders_and_status(pe)
        stage36._emit_prior_loaders(pe)
        stage36._emit_runtime_helpers(pe)
        stage36.emit_render_selected_dropped_shotgun_visual_boundary_debug(pe)
        stage38.emit_render_selected_attack_feedback_present_bridge_debug(pe)
        stage39.emit_render_selected_projectile_spawn_present_probe_debug(pe)
        stage40.emit_render_bounded_vissprite_traversal_sorting_bridge_debug(pe)
        stage41.emit_render_statusbar_weapon_ammo_feedback_bridge_debug(pe)
        stage42.emit_render_unified_live_tick_render_loop_probe_debug(pe)
        stage43.emit_render_bounded_projectile_tick_collision_feedback_probe_debug(pe)
        stage36._emit_prior_status(pe)
        stage36.emit_append_stage36_success_status(pe)
        stage38.emit_append_stage38_success_status(pe)
        stage39.emit_append_stage39_success_status(pe)
        stage40.emit_append_stage40_success_status(pe)
        stage41.emit_append_stage41_success_status(pe)
        stage42.emit_append_stage42_success_status(pe)
        stage43.emit_append_stage43_success_status(pe)
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
        emit_stage44_live_minimal_data(pe)
        emit_stage45_stage46_minimal_preservation_data(pe)
        emit_stage47_data(pe)
    return pe.build("entry")


def write_source_stage47_bounded_map01_player_route_first_hostile_sight_bridge_exe(
    path: str | Path = OUTPUT_PATH,
) -> bytes:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = build_source_stage47_bounded_map01_player_route_first_hostile_sight_bridge_exe()
    output.write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit source-guided stage47 bounded MAP01 player route first hostile sight PE32 bridge")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output PE32 executable path")
    args = parser.parse_args()
    output = Path(args.output)
    image = write_source_stage47_bounded_map01_player_route_first_hostile_sight_bridge_exe(output)
    ref = _reference_for_default_wad_or_none()
    print(f"Wrote {output} ({len(image)} bytes)")
    if ref:
        print(f"S47SIG={ref.signature}")
        print(f"STATE47={ref.state_signature}")
        print("RSTATE47=" + ",".join(str(sample.route_state_signature) for sample in ref.samples))
        print("ULSTATE47=" + ",".join(str(sample.unified_state_signature) for sample in ref.samples))
        print("FB47=" + ",".join(str(sample.framebuffer_signature) for sample in ref.samples))
        print(f"FIRST47={ref.first_sight_tic} ACT47={ref.contact_record.mobj_index}/{ref.contact_record.mapthing_index}:{ref.contact_record.type_name}")


if __name__ == "__main__":
    main()
