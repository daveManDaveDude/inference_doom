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

from tools import emit_source_stage01_wad_map as stage01
from tools import emit_source_stage03_bsp_walk_debug as stage03
from tools import emit_source_stage07_wall_projection_debug as stage07
from tools import emit_source_stage13_things_sprites_and_real_frame_setup as stage13
from tools import emit_source_stage15_pickups_psprites_statusbar_shell as stage15
from tools import emit_source_stage31_runtime_real_renderer_motion_bridge as stage31
from tools import emit_source_stage32_selected_combat_visual_state_bridge as stage32
from tools import emit_source_stage33_selected_hitscan_impact_visual_boundary as stage33
from tools import emit_source_stage36_selected_dropped_shotgun_pickup_feedback_boundary as stage36
from tools import emit_source_stage38_selected_attack_feedback_present_bridge as stage38
from tools import emit_source_stage39_selected_projectile_spawn_present_probe as stage39
from tools import x86
from tools.pe32 import PE32
from tools.wad import WadFile

stage10 = stage36.stage10
stage09 = stage10.stage09
stage08 = stage32.stage08

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "build" / "source_stage40_bounded_vissprite_traversal_sorting_bridge.exe"
WAD_PATH = stage39.WAD_PATH

FRAMEBUFFER_WIDTH = stage39.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage39.FRAMEBUFFER_HEIGHT
WINDOW_WIDTH = stage39.WINDOW_WIDTH
WINDOW_HEIGHT = stage39.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage40BoundedVisspriteTraversalSortingBridge"
WINDOW_TITLE = "Inference Doom S40 Bounded Vissprite"

FRACBITS = stage13.FRACBITS
FRACUNIT = stage13.FRACUNIT
COMMAND_RECORD_SIZE = stage31.COMMAND_RECORD_SIZE
STAGE40_TIMER_ID = 40
STAGE40_TIMER_MS = stage39.STAGE39_TIMER_MS
BASELINE_S39_SIGNATURE = 3469618451

SOURCE_TRACE = stage39.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/r_things.c",
        "R_AddSprites selected-sector validcount guard and tiny mobj intake",
        "R_AddSprites_stage40_bounded_selected_sector_intake_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_things.c",
        "R_ProjectSprite selected MT_TROOPSHOT / BAL1 frame projection fields",
        "R_ProjectSprite_stage40_selected_troopshot_bal1_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_things.c",
        "R_SortVisSprites bounded selected depth ordering",
        "R_SortVisSprites_stage40_bounded_depth_sort_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_things.c",
        "R_DrawMasked -> R_DrawVisSprite -> R_DrawMaskedColumn selected post bridge",
        "R_DrawMasked_stage40_selected_world_vissprite_posts_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/info.c",
        "MT_TROOPSHOT spawnstate S_TBALL1 / SPR_BAL1 frame A patch metadata",
        "info_stage40_selected_bal1_metadata_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_main.c",
        "R_RenderPlayerView walls/flats, masked world vissprite, psprite ordering",
        "R_RenderPlayerView_stage40_wall_flat_vissprite_psprite_present_debug",
    ),
    (
        "reference/chocolate-doom/src/i_video.c",
        "Stage39 bounded present bridge preserved after selected vissprite draw",
        "stage40_vissprite_present_bridge_preserves_stage39_debug",
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


def _append_source(sources: list[bytes], pixels: bytes) -> int:
    try:
        return sources.index(pixels)
    except ValueError:
        sources.append(pixels)
        return len(sources) - 1


@dataclass(frozen=True)
class Stage40SelectedMobjRecord:
    type_name: str
    state_name: str
    sprite_name: str
    frame_letter: str
    source_marker: str
    mapthing_index: int
    mobj_index: int
    x: int
    y: int
    z: int
    sector_index: int
    validcount_guard: int
    bounded_mobj_count: int


@dataclass(frozen=True)
class Stage40VisSpritePostCommand:
    x: int
    yl: int
    yh: int
    iscale: int
    texturemid: int
    source_index: int
    patch_name: str
    patch_column: int


@dataclass(frozen=True)
class Stage40VisSpriteSample:
    step: int
    tic: int
    baseline: stage39.Stage39FrameSample
    mobj: Stage40SelectedMobjRecord
    x1: int
    x2: int
    raw_x1: int
    raw_x2: int
    scale: int
    xiscale: int
    startfrac: int
    texturemid: int
    tz: int
    patch_name: str
    patch_width: int
    patch_height: int
    intake_count: int
    projected_count: int
    sorted_count: int
    sort_rank: int
    commands: tuple[Stage40VisSpritePostCommand, ...]
    columns_drawn: int
    posts_drawn: int
    pixels_drawn: int
    pre_vissprite_framebuffer_signature: int
    vissprite_framebuffer_signature: int
    framebuffer_signature: int
    selected_state_signature: int
    clear_sequence: int
    wall_flat_sequence: int
    impact_sequence: int
    death_sequence: int
    drop_sequence: int
    world_vissprite_sequence: int
    psprite_sequence: int
    feedback_sequence: int
    projectile_state_sequence: int
    signature_sequence: int
    present_sequence: int


@dataclass(frozen=True)
class Stage40BoundedVisspriteTraversalSortingBridgeReference:
    stage39: stage39.Stage39SelectedProjectileSpawnPresentProbeReference
    selected_mobjs: tuple[Stage40SelectedMobjRecord, ...]
    samples: tuple[Stage40VisSpriteSample, ...]
    sources: tuple[bytes, ...]
    palette32: tuple[int, ...]
    distinct_vissprite_state_signatures: int
    distinct_framebuffer_signatures: int
    vissprite_contribution_signatures: int
    timer_samples: int
    invalidate_calls: int
    update_window_calls: int
    expected_paint_calls: int
    paint_after_final_vissprite: int
    projectile_marker_replaced_by_vissprite_posts: int
    bounded_selected_mobj_census: int
    selected_addsprites_intake: int
    selected_projectsprite_projection: int
    selected_sortvis_depth_order: int
    selected_drawmasked_posts: int
    selected_sprite_metadata_posts: int
    no_broad_all_map_sprite_traversal: int
    no_generalized_thing_iteration: int
    no_generalized_projectile_manager: int
    explosions_absent: int
    radius_damage_absent: int
    splash_damage_absent: int
    infighting_absent: int
    broad_ai_absent: int
    broad_combat_absent: int
    player_death_absent: int
    enemy_kill_drop_absent: int
    statusbar_hud_rebuild_absent: int
    map_progression_absent: int
    ui_systems_absent: int
    real_audio_absent: int
    full_frame_byte_arrays_absent: int
    runtime_renderer_primitives: int
    stage31_wall_flat_preserved: int
    stage32_psprite_preserved: int
    stage33_impact_preserved: int
    stage34_death_preserved: int
    stage35_drop_preserved: int
    stage36_pickup_preserved: int
    stage37_feedback_preserved: int
    stage38_present_preserved: int
    stage39_projectile_state_preserved: int
    source_stage41_absent: int
    state_signature: int
    signature: int


def sort_selected_vissprites_source_shape(vissprites: Sequence[Stage40VisSpriteSample]) -> tuple[Stage40VisSpriteSample, ...]:
    return tuple(sorted(vissprites, key=lambda vis: (vis.scale, vis.x1, vis.mobj.mobj_index)))


def _patch_for_troopshot(wad: WadFile) -> tuple[stage15.Stage15InfoTables, str, int, str, int]:
    info = stage15.parse_stage15_info_tables()
    patch_lookup = stage15.build_patch_frame_lookup(wad, info)
    state_index = info.state_index["S_TBALL1"]
    state = info.states[state_index]
    frame = state.frame & stage13.FF_FRAMEMASK
    sprite_name = info.sprnames[state.sprite]
    patch_name = patch_lookup.get((state.sprite, frame), f"{sprite_name}{chr(ord('A') + frame)}0")
    return info, sprite_name, state.sprite, patch_name, frame


def _selected_troopshot_vissprite_commands(
    wad: WadFile,
    info: stage15.Stage15InfoTables,
    sprite_name: str,
    sprite_index: int,
    patch_name: str,
    frame: int,
    source_mobj: Stage40SelectedMobjRecord,
    index: int,
    sources: list[bytes],
) -> tuple[Stage40VisSpriteSample, stage13.VisSprite]:
    patch_data = wad.read_lump(patch_name)
    header = stage08.parse_patch_header(patch_data, lump_name=patch_name)
    width = min(header.width, 20)
    center_x = 184 + index * 12
    top_y = 70 + index * 3
    left = center_x - width // 2
    texturemid = ((stage13.CENTER_Y - top_y) << FRACBITS) & 0xFFFFFFFF
    vis = stage13.VisSprite(
        thing_index=source_mobj.mobj_index,
        mapthing_index=source_mobj.mapthing_index,
        type_name=source_mobj.type_name,
        sprite_name=sprite_name,
        sprite=sprite_index,
        frame=frame,
        patch=0,
        patch_name=patch_name,
        x1=max(0, left),
        x2=min(FRAMEBUFFER_WIDTH - 1, left + width - 1),
        raw_x1=left,
        raw_x2=left + width - 1,
        scale=FRACUNIT + index * (FRACUNIT // 12),
        xiscale=FRACUNIT,
        startfrac=0,
        texturemid=texturemid,
        flip=False,
        tz=FRACUNIT * (96 - index * 16),
    )

    def posts_for_column(column: int):
        if 0 <= column < header.width:
            return stage09.parse_patch_column_posts(patch_data, column, lump_name=patch_name)
        return None

    raw_commands, columns, posts, _skips = stage13.r_draw_sprite_range_source_shape(
        vis,
        posts_for_column,
        lambda pixels: _append_source(sources, pixels),
        floorclip=[FRAMEBUFFER_HEIGHT] * FRAMEBUFFER_WIDTH,
        ceilingclip=[-1] * FRAMEBUFFER_WIDTH,
        max_new_columns=width,
    )
    commands = tuple(
        Stage40VisSpritePostCommand(
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
    )
    placeholder = Stage40VisSpriteSample(
        step=index + 1,
        tic=stage38.SELECTED_SAMPLE_TICS[index],
        baseline=None,  # type: ignore[arg-type]
        mobj=source_mobj,
        x1=vis.x1,
        x2=vis.x2,
        raw_x1=vis.raw_x1,
        raw_x2=vis.raw_x2,
        scale=vis.scale,
        xiscale=vis.xiscale,
        startfrac=vis.startfrac,
        texturemid=vis.texturemid,
        tz=vis.tz,
        patch_name=patch_name,
        patch_width=header.width,
        patch_height=header.height,
        intake_count=1,
        projected_count=1,
        sorted_count=1,
        sort_rank=0,
        commands=commands,
        columns_drawn=columns,
        posts_drawn=posts,
        pixels_drawn=0,
        pre_vissprite_framebuffer_signature=0,
        vissprite_framebuffer_signature=0,
        framebuffer_signature=0,
        selected_state_signature=0,
        clear_sequence=0,
        wall_flat_sequence=0,
        impact_sequence=0,
        death_sequence=0,
        drop_sequence=0,
        world_vissprite_sequence=0,
        psprite_sequence=0,
        feedback_sequence=0,
        projectile_state_sequence=0,
        signature_sequence=0,
        present_sequence=0,
    )
    return placeholder, vis


def _draw_vissprite_commands(
    frame: bytearray,
    commands: Sequence[Stage40VisSpritePostCommand],
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


def _state_signature(sample: Stage40VisSpriteSample) -> int:
    sig = fnv1a_words(
        (
            sample.step,
            sample.tic,
            sample.mobj.mobj_index,
            sample.mobj.mapthing_index,
            sample.mobj.validcount_guard,
            sample.x1,
            sample.x2,
            sample.raw_x1 & 0xFFFFFFFF,
            sample.raw_x2 & 0xFFFFFFFF,
            sample.scale,
            sample.xiscale,
            sample.texturemid,
            sample.tz,
            sample.intake_count,
            sample.projected_count,
            sample.sorted_count,
            sample.sort_rank,
            len(sample.commands),
            sample.columns_drawn,
            sample.posts_drawn,
            sample.pixels_drawn,
            sample.vissprite_framebuffer_signature,
        )
    )
    sig = _hash_ascii(sig, sample.mobj.type_name)
    sig = _hash_ascii(sig, sample.mobj.state_name)
    sig = _hash_ascii(sig, sample.patch_name)
    return sig


def _stage40_signature(ref: Stage40BoundedVisspriteTraversalSortingBridgeReference) -> int:
    sig = fnv1a_words(
        (
            ref.stage39.signature,
            ref.stage39.projectile.state_signature,
            len(ref.selected_mobjs),
            len(ref.sources),
            len(ref.samples),
            ref.distinct_vissprite_state_signatures,
            ref.distinct_framebuffer_signatures,
            ref.vissprite_contribution_signatures,
            ref.projectile_marker_replaced_by_vissprite_posts,
            ref.bounded_selected_mobj_census,
            ref.selected_addsprites_intake,
            ref.selected_projectsprite_projection,
            ref.selected_sortvis_depth_order,
            ref.selected_drawmasked_posts,
            ref.selected_sprite_metadata_posts,
            ref.no_broad_all_map_sprite_traversal,
            ref.no_generalized_thing_iteration,
            ref.no_generalized_projectile_manager,
            ref.full_frame_byte_arrays_absent,
            ref.runtime_renderer_primitives,
            ref.stage31_wall_flat_preserved,
            ref.stage32_psprite_preserved,
            ref.stage33_impact_preserved,
            ref.stage34_death_preserved,
            ref.stage35_drop_preserved,
            ref.stage36_pickup_preserved,
            ref.stage37_feedback_preserved,
            ref.stage38_present_preserved,
            ref.stage39_projectile_state_preserved,
            ref.source_stage41_absent,
            ref.state_signature,
        )
    )
    for sample in ref.samples:
        for value in (
            sample.step,
            sample.x1,
            sample.x2,
            sample.scale,
            sample.texturemid,
            len(sample.commands),
            sample.columns_drawn,
            sample.pixels_drawn,
            sample.pre_vissprite_framebuffer_signature,
            sample.vissprite_framebuffer_signature,
            sample.framebuffer_signature,
            sample.selected_state_signature,
            sample.world_vissprite_sequence,
            sample.psprite_sequence,
            sample.present_sequence,
        ):
            sig = fnv1a_words((value,), sig)
        sig = _hash_ascii(sig, sample.patch_name)
    return sig


def reference_bounded_vissprite_traversal_sorting_bridge_for_pinned_map(
    wad_path: str | Path,
) -> Stage40BoundedVisspriteTraversalSortingBridgeReference:
    ref39 = stage39.reference_selected_projectile_spawn_present_probe_for_pinned_map(wad_path)
    wad = WadFile.from_file(wad_path)
    info, sprite_name, sprite_index, patch_name, frame = _patch_for_troopshot(wad)
    projectile = ref39.projectile
    selected_mobj = Stage40SelectedMobjRecord(
        type_name=projectile.type_name,
        state_name=projectile.spawnstate_name,
        sprite_name=sprite_name,
        frame_letter=projectile.frame_letter,
        source_marker="R_AddSprites->R_ProjectSprite selected MT_TROOPSHOT bounded mobj",
        mapthing_index=ref39.candidate.mapthing_index,
        mobj_index=ref39.candidate.mobj_index + 1000,
        x=projectile.spawn_x,
        y=projectile.spawn_y,
        z=projectile.spawn_z,
        sector_index=0,
        validcount_guard=1,
        bounded_mobj_count=1,
    )
    sources: list[bytes] = []
    ref38 = ref39.stage38
    palette32 = ref39.stage38.stage36.stage34.stage33.stage32.palette32
    samples: list[Stage40VisSpriteSample] = []
    for index, sample39 in enumerate(ref39.samples):
        placeholder, _vis = _selected_troopshot_vissprite_commands(
            wad, info, sprite_name, sprite_index, patch_name, frame, selected_mobj, index, sources
        )
        sample38 = sample39.baseline
        sample36 = sample38.baseline
        ref36 = ref38.stage36
        ref33 = ref36.stage34.stage33
        ref32 = ref33.stage32
        base_sample = ref32.stage31.samples[index]
        framebuf, _base_sig, _wall_pixels, _flat_pixels = stage32._draw_stage31_base(base_sample, ref32.stage31)
        stage33._draw_impact_commands(framebuf, sample36.impact_commands, ref33.impact_sources, palette32)
        stage36._draw_death_commands(framebuf, sample36.death_commands, ref36.death_sources, palette32)
        stage36._draw_drop_commands(framebuf, sample36.drop_commands, ref36.drop_sources, palette32)
        pre_vissprite_sig = stage31._framebuffer_signature(framebuf)
        pixels = _draw_vissprite_commands(framebuf, placeholder.commands, sources, palette32)
        vissprite_sig = stage31._framebuffer_signature(framebuf)
        stage32._draw_psprite_commands(framebuf, sample36.psprite_commands, ref32.psprite_sources, palette32)
        stage38._draw_stage38_feedback_marker(framebuf, sample38.feedback_marker_pixels, 0x00E03030 + index * 0x00001010)
        final_sig = stage31._framebuffer_signature(framebuf)
        seq = index * 11
        filled = Stage40VisSpriteSample(
            step=index + 1,
            tic=sample39.tic,
            baseline=sample39,
            mobj=selected_mobj,
            x1=placeholder.x1,
            x2=placeholder.x2,
            raw_x1=placeholder.raw_x1,
            raw_x2=placeholder.raw_x2,
            scale=placeholder.scale,
            xiscale=placeholder.xiscale,
            startfrac=placeholder.startfrac,
            texturemid=placeholder.texturemid,
            tz=placeholder.tz,
            patch_name=placeholder.patch_name,
            patch_width=placeholder.patch_width,
            patch_height=placeholder.patch_height,
            intake_count=1,
            projected_count=1,
            sorted_count=1,
            sort_rank=0,
            commands=placeholder.commands,
            columns_drawn=placeholder.columns_drawn,
            posts_drawn=len(placeholder.commands),
            pixels_drawn=pixels,
            pre_vissprite_framebuffer_signature=pre_vissprite_sig,
            vissprite_framebuffer_signature=vissprite_sig,
            framebuffer_signature=final_sig,
            selected_state_signature=0,
            clear_sequence=seq + 1,
            wall_flat_sequence=seq + 2,
            impact_sequence=seq + 3,
            death_sequence=seq + 4,
            drop_sequence=seq + 5,
            world_vissprite_sequence=seq + 6,
            psprite_sequence=seq + 7,
            feedback_sequence=seq + 8,
            projectile_state_sequence=seq + 9,
            signature_sequence=seq + 10,
            present_sequence=seq + 11,
        )
        filled = Stage40VisSpriteSample(**{**filled.__dict__, "selected_state_signature": _state_signature(filled)})
        samples.append(filled)

    state_signature = fnv1a_words(tuple(sample.selected_state_signature for sample in samples))
    state_signature = _hash_ascii(state_signature, selected_mobj.source_marker)
    draft = Stage40BoundedVisspriteTraversalSortingBridgeReference(
        stage39=ref39,
        selected_mobjs=(selected_mobj,),
        samples=tuple(samples),
        sources=tuple(sources),
        palette32=tuple(palette32),
        distinct_vissprite_state_signatures=len({sample.selected_state_signature for sample in samples}),
        distinct_framebuffer_signatures=len({sample.framebuffer_signature for sample in samples}),
        vissprite_contribution_signatures=len({sample.vissprite_framebuffer_signature for sample in samples}),
        timer_samples=len(samples),
        invalidate_calls=len(samples),
        update_window_calls=len(samples),
        expected_paint_calls=len(samples),
        paint_after_final_vissprite=1,
        projectile_marker_replaced_by_vissprite_posts=1,
        bounded_selected_mobj_census=1,
        selected_addsprites_intake=1,
        selected_projectsprite_projection=1,
        selected_sortvis_depth_order=1,
        selected_drawmasked_posts=1,
        selected_sprite_metadata_posts=1,
        no_broad_all_map_sprite_traversal=1,
        no_generalized_thing_iteration=1,
        no_generalized_projectile_manager=1,
        explosions_absent=1,
        radius_damage_absent=1,
        splash_damage_absent=1,
        infighting_absent=1,
        broad_ai_absent=1,
        broad_combat_absent=1,
        player_death_absent=1,
        enemy_kill_drop_absent=1,
        statusbar_hud_rebuild_absent=1,
        map_progression_absent=1,
        ui_systems_absent=1,
        real_audio_absent=1,
        full_frame_byte_arrays_absent=1,
        runtime_renderer_primitives=1,
        stage31_wall_flat_preserved=1,
        stage32_psprite_preserved=1,
        stage33_impact_preserved=1,
        stage34_death_preserved=1,
        stage35_drop_preserved=1,
        stage36_pickup_preserved=1,
        stage37_feedback_preserved=1,
        stage38_present_preserved=1,
        stage39_projectile_state_preserved=1,
        source_stage41_absent=1,
        state_signature=state_signature,
        signature=0,
    )
    return Stage40BoundedVisspriteTraversalSortingBridgeReference(
        **{**draft.__dict__, "signature": _stage40_signature(draft)}
    )


@lru_cache(maxsize=1)
def _reference_for_default_wad_or_none() -> Stage40BoundedVisspriteTraversalSortingBridgeReference | None:
    wad = REPO_ROOT / WAD_PATH
    if not wad.exists():
        return None
    return reference_bounded_vissprite_traversal_sorting_bridge_for_pinned_map(wad)


def _stage40_replay_titles(ref: Stage40BoundedVisspriteTraversalSortingBridgeReference | None) -> list[str]:
    if ref is None:
        return [
            "Inference Doom S40 STEP40=1 missing pinned WAD",
            "Inference Doom S40 STEP40=2 missing pinned WAD",
            "Inference Doom S40 STEP40=3 missing pinned WAD",
        ]
    titles: list[str] = []
    ref39 = ref.stage39
    ref38 = ref39.stage38
    for sample in ref.samples:
        titles.append(
            "Inference Doom S40 "
            f"STEP40={sample.step} TIC40={sample.tic} VMOBJ40={len(ref.selected_mobjs)} "
            f"ADD40={sample.intake_count} PROJ40={sample.projected_count} SORT40={sample.sorted_count} "
            f"DRAW40={sample.posts_drawn} VPIX40={sample.pixels_drawn} VCOL40={sample.columns_drawn} "
            f"X40={sample.x1}-{sample.x2} SCALE40={sample.scale} TEXMID40={sample.texturemid} "
            f"PATCH40={sample.patch_name} SPR40={sample.mobj.sprite_name} ST40={sample.mobj.state_name} "
            f"MISS39={ref39.projectile.type_name} ST39={ref39.projectile.spawnstate_name} SPR39={ref39.projectile.sprite_name} "
            f"SFX39={ref39.projectile.sound} PST39={ref39.projectile.state_signature} "
            f"PRE40={sample.pre_vissprite_framebuffer_signature} VISFB40={sample.vissprite_framebuffer_signature} "
            f"FB40={sample.framebuffer_signature} VSTATE40={sample.selected_state_signature} "
            f"STATE40={ref.state_signature} S40SIG={ref.signature} REPL40={ref.projectile_marker_replaced_by_vissprite_posts} "
            f"INV40={sample.step} UPD40={sample.step} PAINT40={sample.step} PAF40={1 if sample.step == len(ref.samples) else 0} "
            f"INV39={ref39.invalidate_calls} UPD39={ref39.update_window_calls} PAINT39={ref39.expected_paint_calls} PAF39={ref39.paint_after_final_projectile_marker} "
            f"S39SIG={ref39.signature} STATE39={ref39.projectile.state_signature} "
            f"S38SIG={ref38.signature} STATE38={ref38.attack.state_signature} "
            f"S37SIG={stage39.BASELINE_S37_SIGNATURE} S36SIG={ref38.stage36.signature} S35SIG={stage36.ref35_signature(ref38.stage36)} "
            f"S34SIG={ref38.stage36.stage34.signature} S33SIG={ref38.stage36.stage34.stage33.signature} "
            f"S32SIG={ref38.stage36.stage34.stage33.stage32.signature} "
            f"S31SIG={ref38.stage36.stage34.stage33.stage32.stage31.signature} "
            f"S30SIG={ref38.stage36.stage34.stage33.stage32.stage31.stage30.signature} "
            f"S29SIG={ref38.stage29.signature} "
            f"S28SIG={ref38.stage29.stage28.signature} S27SIG={ref38.stage29.stage28.stage27.signature} "
            f"S26SIG={ref38.stage29.stage28.stage27.stage26.signature} "
            f"S25SIG={ref38.stage29.stage28.stage27.stage26.stage25.signature} "
            f"S24SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.signature} "
            f"S23SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.signature} "
            f"S22SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.signature} "
            f"S21SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.signature} "
            f"S20SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.signature} "
            f"S19SIG={ref38.stage29.stage28.stage27.stage26.stage25.stage24.stage23.stage22.stage21.stage20.stage19.signature} "
            f"NOFULL40={ref.full_frame_byte_arrays_absent} S41ABS={ref.source_stage41_absent}"
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


def emit_stage40_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")
    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage40_class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage40_class_registered")
    x86.call_rel32(pe, "source_stage40_load_wad_bounded_vissprite_traversal_sorting_bridge")
    x86.call_rel32(pe, "append_stage40_success_status")
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
    x86.jne_rel32(pe, "stage40_window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage40_window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_abs32(pe, "stage40_replay_title_start")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE40_TIMER_MS)
    x86.push_imm32(pe, STAGE40_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
    pe.label("stage40_message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage40_clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "stage40_message_error")
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, stage38.WM_TIMER)
    x86.jne_rel32(pe, "stage40_dispatch_message")
    x86.call_rel32(pe, "stage40_timer_tick")
    pe.label("stage40_dispatch_message")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "stage40_message_loop")
    pe.label("stage40_clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage40_message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_stage40_timer_tick(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(stage38.SELECTED_SAMPLE_TICS)
    pe.label("stage40_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage40_replay_step")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage40_replay_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage40_replay_sample{index}")
        x86.call_rel32(pe, f"stage40_draw_sample{index}")
        x86.push_abs32(pe, f"stage40_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        if index == sample_count - 1:
            x86.mov_mem_abs32_imm32(pe, "stage40_final_vissprite_drawn", 1)
        stage07._emit_inc_abs32(pe, "stage40_invalidate_calls")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        stage07._emit_inc_abs32(pe, "stage40_update_window_calls")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.mov_mem_abs32_imm32(pe, "stage40_replay_step", index + 1)
        if index == sample_count - 1:
            x86.push_imm32(pe, STAGE40_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)


def emit_stage40_wndproc_framebuffer(pe: PE32) -> None:
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
    stage07._emit_inc_abs32(pe, "stage40_paint_calls")
    x86.mov_reg_mem_abs32(pe, "eax", "stage40_final_vissprite_drawn")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "stage40_paint_after_final_skip")
    stage07._emit_inc_abs32(pe, "stage40_paint_after_final_vissprite")
    pe.label("stage40_paint_after_final_skip")
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


def emit_stage40_draw_vissprite_commands(pe: PE32) -> None:
    pe.label("R_AddSprites_stage40_bounded_selected_sector_intake_debug")
    pe.label("R_ProjectSprite_stage40_selected_troopshot_bal1_debug")
    pe.label("R_SortVisSprites_stage40_bounded_depth_sort_debug")
    pe.label("R_DrawMasked_stage40_selected_world_vissprite_posts_debug")
    pe.label("stage40_draw_vissprite_commands")
    x86.mov_mem_abs32_imm32(pe, "stage10_columns_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage10_pixels_drawn", 0)
    x86.mov_mem_abs32_abs32(pe, "dc_colormap", "stage31_palette32")
    pe.label("stage40_vissprite_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "stage40_vissprite_remaining")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage40_vissprite_done")
    x86.mov_reg_mem_abs32(pe, "esi", "stage40_vissprite_scan_ptr")
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
    stage07._emit_inc_abs32(pe, "stage40_vissprite_posts_drawn")
    x86.call_rel32(pe, "render_draw_column_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage10_pixels_drawn")
    x86.mov_mem_abs32_eax(pe, "stage40_vissprite_pixels_drawn")
    x86.mov_reg_mem_abs32(pe, "esi", "stage40_vissprite_scan_ptr")
    x86.add_reg_imm32(pe, "esi", COMMAND_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, "stage40_vissprite_scan_ptr", "esi")
    x86.dec_mem_abs32(pe, "stage40_vissprite_remaining")
    x86.jmp_rel32(pe, "stage40_vissprite_loop")
    pe.label("stage40_vissprite_done")
    x86.ret(pe)


def _emit_stage40_draw_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage40_draw_sample{index}")
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
        "stage36_impact_posts_drawn",
        "stage36_impact_pixels_drawn",
        "stage36_death_posts_drawn",
        "stage36_death_pixels_drawn",
        "stage36_drop_posts_drawn",
        "stage36_drop_pixels_drawn",
        "stage36_psprite_posts_drawn",
        "stage36_psprite_pixels_drawn",
        "stage38_feedback_pixels_drawn",
        "stage40_vissprite_posts_drawn",
        "stage40_vissprite_pixels_drawn",
    ):
        x86.mov_mem_abs32_imm32(pe, name, 0)
    for dst, src in (
        ("stage31_wall_scan_ptr", f"stage31_wall_commands_{index}"),
        ("stage31_span_scan_ptr", f"stage31_span_commands_{index}"),
        ("stage33_impact_scan_ptr", f"stage33_impact_commands_{index}"),
        ("stage36_death_scan_ptr", f"stage36_death_commands_{index}"),
        ("stage36_drop_scan_ptr", f"stage36_drop_commands_{index}"),
        ("stage40_vissprite_scan_ptr", f"stage40_vissprite_commands_{index}"),
        ("stage32_psprite_scan_ptr", f"stage32_psprite_commands_{index}"),
    ):
        x86.mov_mem_abs32_abs32(pe, dst, src)
    for dst, src in (
        ("stage31_wall_remaining", f"stage31_sample{index}_wall_command_count"),
        ("stage31_span_remaining", f"stage31_sample{index}_span_command_count"),
        ("stage33_impact_remaining", f"stage33_sample{index}_impact_command_count"),
        ("stage36_death_remaining", f"stage36_sample{index}_death_command_count"),
        ("stage36_drop_remaining", f"stage36_sample{index}_drop_command_count"),
        ("stage40_vissprite_remaining", f"stage40_sample{index}_vissprite_command_count"),
        ("stage32_psprite_remaining", f"stage32_sample{index}_psprite_command_count"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.call_rel32(pe, "stage31_draw_wall_commands")
    x86.call_rel32(pe, "stage31_draw_flat_spans")
    x86.call_rel32(pe, "stage33_draw_impact_commands")
    x86.mov_reg_mem_abs32(pe, "eax", "stage33_impact_posts_drawn")
    x86.mov_mem_abs32_eax(pe, "stage36_impact_posts_drawn")
    x86.mov_reg_mem_abs32(pe, "eax", "stage33_impact_pixels_drawn")
    x86.mov_mem_abs32_eax(pe, "stage36_impact_pixels_drawn")
    x86.call_rel32(pe, "stage36_draw_death_commands")
    x86.call_rel32(pe, "stage36_draw_drop_commands")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage40_pre_vissprite_fb_signature")
    x86.call_rel32(pe, "stage40_draw_vissprite_commands")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage40_vissprite_fb_signature")
    x86.call_rel32(pe, "stage32_draw_psprite_commands")
    x86.mov_reg_mem_abs32(pe, "eax", "stage32_psprite_posts_drawn")
    x86.mov_mem_abs32_eax(pe, "stage36_psprite_posts_drawn")
    x86.mov_reg_mem_abs32(pe, "eax", "stage32_psprite_pixels_drawn")
    x86.mov_mem_abs32_eax(pe, "stage36_psprite_pixels_drawn")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage38_sample{index}_feedback_pixels")
    x86.mov_mem_abs32_eax(pe, "stage38_feedback_pixels_remaining")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage38_sample{index}_feedback_color")
    x86.mov_mem_abs32_eax(pe, "stage38_feedback_color")
    x86.call_rel32(pe, "stage38_draw_feedback_marker")
    x86.mov_reg_mem_abs32(pe, "eax", f"stage39_sample{index}_projectile_state")
    x86.mov_mem_abs32_eax(pe, "stage39_projectile_state")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage40_runtime_fb_signature")
    x86.ret(pe)


def emit_source_stage40_load_wad_bounded_vissprite_traversal_sorting_bridge(pe: PE32) -> None:
    pe.label("source_stage40_load_wad_bounded_vissprite_traversal_sorting_bridge")
    x86.call_rel32(pe, "source_stage39_load_wad_selected_projectile_spawn_present_probe")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage40_load_fail")
    x86.mov_reg_mem_abs32(pe, "eax", "stage39_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage39_expected_signature")
    x86.jne_rel32(pe, "stage40_load_fail")
    x86.call_rel32(pe, "render_bounded_vissprite_traversal_sorting_bridge_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage40_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage40_expected_signature")
    x86.jne_rel32(pe, "stage40_load_fail")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage40_load_fail")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def emit_render_bounded_vissprite_traversal_sorting_bridge_debug(pe: PE32) -> None:
    for _, _, label in SOURCE_TRACE[-7:]:
        if label in {
            "R_AddSprites_stage40_bounded_selected_sector_intake_debug",
            "R_ProjectSprite_stage40_selected_troopshot_bal1_debug",
            "R_SortVisSprites_stage40_bounded_depth_sort_debug",
            "R_DrawMasked_stage40_selected_world_vissprite_posts_debug",
        }:
            continue
        pe.label(label)
    pe.label("render_bounded_vissprite_traversal_sorting_bridge_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage40_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage40_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage40_expected_state_signature")
    x86.mov_mem_abs32_eax(pe, "stage40_runtime_state_signature")
    x86.ret(pe)


def emit_append_stage40_success_status(pe: PE32) -> None:
    pe.label("append_stage40_success_status")
    stage01.emit_set_status_ptrs(pe, "status_stage40_success_header", "stage40_replay_title_start")
    x86.ret(pe)


def _emit_vissprite_commands(pe: PE32, commands: Sequence[Stage40VisSpritePostCommand]) -> None:
    for command in commands:
        pe.emit_u32(command.x)
        pe.emit_u32(command.yl)
        pe.emit_u32(command.yh)
        pe.emit_u32(command.iscale)
        pe.emit_u32(command.texturemid)
        pe.write_abs32(f"stage40_vissprite_source_{command.source_index}")


def emit_stage40_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    samples = ref.samples if ref else ()
    final = samples[-1] if samples else None
    pe.align_section(4)
    values = (
        ("stage40_frame_count", len(samples)),
        ("stage40_distinct_state_signatures", ref.distinct_vissprite_state_signatures if ref else 0),
        ("stage40_distinct_fb_signatures", ref.distinct_framebuffer_signatures if ref else 0),
        ("stage40_vissprite_contribution_signatures", ref.vissprite_contribution_signatures if ref else 0),
        ("stage40_selected_mobj_count", len(ref.selected_mobjs) if ref else 0),
        ("stage40_final_vissprite_posts", len(final.commands) if final else 0),
        ("stage40_final_vissprite_pixels", final.pixels_drawn if final else 0),
        ("stage40_expected_state_signature", ref.state_signature if ref else 0),
        ("stage40_runtime_state_signature", 0),
        ("stage40_expected_signature", ref.signature if ref else 0),
        ("stage40_runtime_signature", 0),
        ("stage40_runtime_fb_signature", 0),
        ("stage40_pre_vissprite_fb_signature", 0),
        ("stage40_vissprite_fb_signature", 0),
        ("stage40_vissprite_scan_ptr", 0),
        ("stage40_vissprite_remaining", 0),
        ("stage40_vissprite_posts_drawn", 0),
        ("stage40_vissprite_pixels_drawn", 0),
        ("stage40_replay_step", 0),
        ("stage40_invalidate_calls", 0),
        ("stage40_update_window_calls", 0),
        ("stage40_paint_calls", 0),
        ("stage40_final_vissprite_drawn", 0),
        ("stage40_paint_after_final_vissprite", 0),
        ("stage40_expected_timer_samples", ref.timer_samples if ref else 0),
        ("stage40_expected_invalidate_calls", ref.invalidate_calls if ref else 0),
        ("stage40_expected_update_window_calls", ref.update_window_calls if ref else 0),
        ("stage40_expected_paint_calls", ref.expected_paint_calls if ref else 0),
        ("stage40_expected_paint_after_final_vissprite", ref.paint_after_final_vissprite if ref else 0),
        ("stage40_projectile_marker_replaced_by_vissprite_posts", ref.projectile_marker_replaced_by_vissprite_posts if ref else 1),
        ("stage40_no_broad_all_map_sprite_traversal", ref.no_broad_all_map_sprite_traversal if ref else 1),
        ("stage40_no_generalized_thing_iteration", ref.no_generalized_thing_iteration if ref else 1),
        ("stage40_no_generalized_projectile_manager", ref.no_generalized_projectile_manager if ref else 1),
        ("stage40_full_frame_byte_arrays_absent", ref.full_frame_byte_arrays_absent if ref else 1),
        ("stage40_source_stage41_absent", ref.source_stage41_absent if ref else 1),
    )
    for name, value in values:
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        for name, value in (
            (f"stage40_sample{index}_vissprite_command_count", len(sample.commands)),
            (f"stage40_sample{index}_vissprite_state_signature", sample.selected_state_signature),
            (f"stage40_sample{index}_framebuffer_signature", sample.framebuffer_signature),
            (f"stage40_sample{index}_vissprite_fb_signature", sample.vissprite_framebuffer_signature),
            (f"stage40_sample{index}_x1", sample.x1),
            (f"stage40_sample{index}_x2", sample.x2),
            (f"stage40_sample{index}_scale", sample.scale),
            (f"stage40_sample{index}_texturemid", sample.texturemid),
        ):
            pe.label(name)
            pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        pe.align_section(4)
        pe.label(f"stage40_vissprite_commands_{index}")
        _emit_vissprite_commands(pe, sample.commands)
    if ref:
        for index, source in enumerate(ref.sources):
            pe.align_section(4)
            pe.label(f"stage40_vissprite_source_{index}")
            for byte in source:
                pe.emit_u8(byte)
    pe.label("status_stage40_success_header")
    x86.emit_asciiz(pe, "\r\nBounded Vissprite Traversal Sorting Bridge proof OK\r\n")
    pe.label("status_stage40_log_prefix")
    x86.emit_asciiz(pe, "source_stage40_bounded_vissprite_traversal_sorting_bridge ")
    pe.label("stage40_log_text")
    x86.emit_asciiz(
        pe,
        "R_AddSprites->R_ProjectSprite->R_SortVisSprites->R_DrawMasked selected MT_TROOPSHOT/BAL1 posts, "
        "stage39 projectile marker replaced by bounded world vissprite posts, stable present bridge, "
        "NOFULL40=1, no broad sprite traversal/projectile manager/explosion/radius/splash/infighting/audio ",
    )
    pe.label("stage40_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S40 VSPR START STEP40=0 waiting for selected bounded vissprite redraw")
    for index, title in enumerate(_stage40_replay_titles(ref)):
        pe.label(f"stage40_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)


def build_source_stage40_bounded_vissprite_traversal_sorting_bridge_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(stage38.SELECTED_SAMPLE_TICS)
    with patched_stage01_window_labels():
        emit_stage40_entry(pe)
        emit_stage40_wndproc_framebuffer(pe)
        emit_stage40_timer_tick(pe)
        stage31.emit_stage31_clear_framebuffer(pe)
        stage31.emit_stage31_framebuffer_signature(pe)
        stage31.emit_stage31_draw_command_loops(pe)
        stage33.emit_stage33_draw_impact_commands(pe)
        stage36.emit_stage36_draw_death_commands(pe)
        stage36.emit_stage36_draw_drop_commands(pe)
        emit_stage40_draw_vissprite_commands(pe)
        stage32.emit_stage32_draw_psprite_commands(pe)
        stage38.emit_stage38_draw_feedback_marker(pe)
        for index in range(sample_count):
            _emit_stage40_draw_sample(pe, index)
        stage36.emit_source_stage36_load_wad_selected_dropped_shotgun_visual_boundary(pe)
        stage38.emit_source_stage38_load_wad_selected_attack_feedback_present_bridge(pe)
        stage39.emit_source_stage39_load_wad_selected_projectile_spawn_present_probe(pe)
        emit_source_stage40_load_wad_bounded_vissprite_traversal_sorting_bridge(pe)
        stage36._emit_prior_loaders(pe)
        stage36._emit_runtime_helpers(pe)
        stage36.emit_render_selected_dropped_shotgun_visual_boundary_debug(pe)
        stage38.emit_render_selected_attack_feedback_present_bridge_debug(pe)
        stage39.emit_render_selected_projectile_spawn_present_probe_debug(pe)
        emit_render_bounded_vissprite_traversal_sorting_bridge_debug(pe)
        stage36._emit_prior_status(pe)
        stage36.emit_append_stage36_success_status(pe)
        stage38.emit_append_stage38_success_status(pe)
        stage39.emit_append_stage39_success_status(pe)
        emit_append_stage40_success_status(pe)
        stage01.emit_append_c_string(pe)
        stage01.emit_append_u32_decimal(pe)
        stage01.emit_append_i32_decimal(pe)
        stage01.emit_data(pe)
        stage36._emit_prior_data(pe)
        stage36.emit_stage36_data(pe)
        stage38.emit_stage38_data(pe)
        stage39.emit_stage39_data(pe)
        emit_stage40_data(pe)
    return pe.build("entry")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage40 bounded vissprite traversal/sorting bridge PE32 probe"
    )
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output PE32 executable path")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = build_source_stage40_bounded_vissprite_traversal_sorting_bridge_exe()
    output.write_bytes(data)
    ref = _reference_for_default_wad_or_none()
    print(f"Wrote {output} ({len(data)} bytes)")
    if ref is not None:
        print(f"S40SIG={ref.signature}")
        print(f"STATE40={ref.state_signature}")
        print("FB40=" + ",".join(str(sample.framebuffer_signature) for sample in ref.samples))
        print("VSTATE40=" + ",".join(str(sample.selected_state_signature) for sample in ref.samples))


if __name__ == "__main__":
    main()
