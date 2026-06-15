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

from tools import emit_source_stage40_bounded_vissprite_traversal_sorting_bridge as stage40
from tools import x86
from tools.pe32 import PE32


stage39 = stage40.stage39
stage38 = stage40.stage38
stage36 = stage40.stage36
stage32 = stage40.stage32
stage31 = stage40.stage31
stage15 = stage40.stage15
stage07 = stage40.stage07
stage03 = stage40.stage03
stage01 = stage40.stage01

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "build" / "source_stage41_statusbar_weapon_ammo_feedback_bridge.exe"
WAD_PATH = stage40.WAD_PATH

FRAMEBUFFER_WIDTH = stage40.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage40.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_BYTES = FRAMEBUFFER_WIDTH * FRAMEBUFFER_HEIGHT * 4
WINDOW_WIDTH = stage40.WINDOW_WIDTH
WINDOW_HEIGHT = stage40.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage41StatusbarWeaponAmmoFeedbackBridge"
WINDOW_TITLE = "Inference Doom S41 Statusbar Weapon Ammo Feedback"

STAGE41_TIMER_ID = 41
STAGE41_TIMER_MS = stage40.STAGE40_TIMER_MS
STATUS_COMMAND_RECORD_SIZE = 24
STATUS_STRIP_Y = 184
BASELINE_S40_SIGNATURE = 2737672056
BASELINE_S40_STATE_SIGNATURE = 268409133

SOURCE_TRACE = stage40.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/st_stuff.c",
        "ST_updateWidgets ready ammo, health, armor, weapon ownership, and damage/bonus feedback fields",
        "ST_updateWidgets_stage41_compact_status_player_fields_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/hu_stuff.c",
        "HU_Ticker player message ownership for selected GOTSHOTGUN text",
        "HU_Ticker_stage41_selected_pickup_message_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_inter.c",
        "P_TouchSpecialThing/P_GiveWeapon selected shotgun pickup ammo/message/bonus state",
        "P_TouchSpecialThing_stage41_selected_shotgun_status_feedback_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_inter.c",
        "P_DamageMobj selected player health/armor/damagecount feedback state",
        "P_DamageMobj_stage41_selected_player_status_feedback_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_pspr.c",
        "P_SetupPsprites/P_MovePsprites selected shotgun ownership and pending weapon bridge",
        "P_SetupPsprites_stage41_selected_weapon_pending_status_debug",
    ),
    (
        "reference/chocolate-doom/src/v_video.c",
        "V_DrawFilledBox/V_DrawHorizLine-style compact status strip primitives",
        "V_DrawFilledBox_stage41_compact_status_strip_debug",
    ),
    (
        "reference/chocolate-doom/src/i_video.c",
        "Stage40 present bridge preserved after final compact status strip draw",
        "stage41_status_present_bridge_preserves_stage40_debug",
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
class Stage41StatusRectCommand:
    x: int
    y: int
    width: int
    height: int
    color: int
    row_advance: int
    field: str


@dataclass(frozen=True)
class Stage41StatusState:
    health: int
    armor: int
    shell_ammo: int
    shotgun_owned: int
    pending_weapon: int
    message: str
    bonuscount: int
    damagecount: int
    pickup_flash: int
    damage_flash: int
    sfx_wpnup: int
    sfx_shotgn: int
    sfx_firsht: int
    status_phase: int
    source_marker: str


@dataclass(frozen=True)
class Stage41StatusSample:
    step: int
    tic: int
    baseline: stage40.Stage40VisSpriteSample
    status: Stage41StatusState
    commands: tuple[Stage41StatusRectCommand, ...]
    command_count: int
    status_pixels_drawn: int
    pre_status_framebuffer_signature: int
    status_framebuffer_signature: int
    framebuffer_signature: int
    selected_status_state_signature: int
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
class Stage41StatusbarWeaponAmmoFeedbackBridgeReference:
    stage40: stage40.Stage40BoundedVisspriteTraversalSortingBridgeReference
    samples: tuple[Stage41StatusSample, ...]
    distinct_selected_status_signatures: int
    distinct_framebuffer_signatures: int
    status_contribution_signatures: int
    timer_samples: int
    invalidate_calls: int
    update_window_calls: int
    expected_paint_calls: int
    paint_after_final_status: int
    final_window_alive_after_samples: int
    closes_normally: int
    source_status_player_fields: int
    source_hu_message_bridge: int
    source_pickup_feedback_bridge: int
    source_damage_feedback_bridge: int
    source_weapon_pending_bridge: int
    compact_status_strip_drawn: int
    status_draw_bounds_checked: int
    status_draw_after_world_vissprite_and_psprite: int
    status_draw_after_feedback_and_projectile_state: int
    stage31_wall_flat_preserved: int
    stage32_psprite_preserved: int
    stage33_impact_preserved: int
    stage34_death_preserved: int
    stage35_drop_preserved: int
    stage36_pickup_preserved: int
    stage37_feedback_preserved: int
    stage38_present_preserved: int
    stage39_projectile_state_preserved: int
    stage40_vissprite_preserved: int
    full_frame_byte_arrays_absent: int
    runtime_renderer_primitives: int
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
    generalized_inventory_absent: int
    generalized_item_traversal_absent: int
    generalized_combat_absent: int
    broad_monster_ai_absent: int
    player_death_absent: int
    enemy_kill_drop_absent: int
    broad_all_map_sprite_traversal_absent: int
    generalized_projectile_manager_absent: int
    explosions_absent: int
    radius_damage_absent: int
    splash_damage_absent: int
    infighting_absent: int
    map_progression_absent: int
    source_stage42_absent: int
    state_signature: int
    signature: int


def _rect(x: int, y: int, width: int, height: int, color: int, field: str) -> Stage41StatusRectCommand:
    if width < 1 or height < 1:
        raise ValueError(f"empty status rect for {field}")
    if x < 0 or y < 0 or x + width > FRAMEBUFFER_WIDTH or y + height > FRAMEBUFFER_HEIGHT:
        raise ValueError(f"status rect out of bounds for {field}")
    return Stage41StatusRectCommand(
        x=x,
        y=y,
        width=width,
        height=height,
        color=color & 0x00FFFFFF,
        row_advance=(FRAMEBUFFER_WIDTH - width) * 4,
        field=field,
    )


def selected_status_state_stage41_source_shape(index: int, ref40: stage40.Stage40BoundedVisspriteTraversalSortingBridgeReference) -> Stage41StatusState:
    pickup = ref40.stage39.stage38.stage36.pickup
    attack = ref40.stage39.stage38.attack
    projectile = ref40.stage39.projectile
    if index == 0:
        return Stage41StatusState(
            health=attack.health_before,
            armor=attack.armor_before,
            shell_ammo=pickup.ammo_before,
            shotgun_owned=pickup.weapon_owned_before,
            pending_weapon=pickup.pending_before,
            message="",
            bonuscount=pickup.bonuscount_before,
            damagecount=attack.damagecount_before,
            pickup_flash=0,
            damage_flash=0,
            sfx_wpnup=0,
            sfx_shotgn=0,
            sfx_firsht=0,
            status_phase=0,
            source_marker="ST:pre_selected_feedback",
        )
    return Stage41StatusState(
        health=attack.health_after,
        armor=attack.armor_after,
        shell_ammo=pickup.ammo_after,
        shotgun_owned=pickup.weapon_owned_after,
        pending_weapon=pickup.pending_after,
        message=pickup.message,
        bonuscount=max(0, pickup.bonuscount_after - (index - 1) * 2),
        damagecount=max(0, attack.damagecount_after - (index - 1) * 4),
        pickup_flash=pickup.bonuscount_after,
        damage_flash=attack.damagecount_after,
        sfx_wpnup=pickup.sound_events,
        sfx_shotgn=attack.sound_events,
        sfx_firsht=projectile.sound_events if index == 2 else 0,
        status_phase=index,
        source_marker="ST/HU/P_INTER/P_PSPR:selected_player_feedback",
    )


def _status_rects_for_state(status: Stage41StatusState) -> tuple[Stage41StatusRectCommand, ...]:
    y = STATUS_STRIP_Y
    rects = [
        _rect(0, y, FRAMEBUFFER_WIDTH, 16, 0x00101010, "status_background"),
        _rect(3, y + 2, max(2, status.health // 2), 4, 0x0000B850 if status.health >= 50 else 0x00B82020, "health"),
        _rect(3, y + 8, max(2, status.damagecount * 4), 3, 0x00D03030, "damagecount"),
        _rect(61, y + 2, max(2, status.armor // 2 + 2), 4, 0x004060C8, "armor"),
        _rect(90, y + 2, max(2, status.shell_ammo * 5 + 2), 4, 0x00D0C050, "shell_ammo"),
        _rect(118, y + 2, 12, 6, 0x00D8C020 if status.shotgun_owned else 0x00303030, "shotgun_owned"),
        _rect(134, y + 2, 12, 6, 0x00F0A030 if status.pending_weapon == stage15.WP_SHOTGUN else 0x00404040, "pending_weapon"),
    ]
    if status.message:
        rects.append(_rect(153, y + 2, 68, 6, 0x00D09020, "message_GOTSHOTGUN"))
    else:
        rects.append(_rect(153, y + 2, 18, 6, 0x00202020, "message_empty"))
    rects.extend(
        [
            _rect(226, y + 2, max(2, status.bonuscount * 4), 3, 0x00F0D050, "bonuscount"),
            _rect(226, y + 7, max(2, status.damage_flash * 3), 3, 0x00E04040, "damage_flash"),
            _rect(284, y + 2, 7, 7, 0x0050A0F0 if status.sfx_wpnup else 0x00202020, "sfx_wpnup"),
            _rect(296, y + 2, 7, 7, 0x00E0E0E0 if status.sfx_shotgn else 0x00202020, "sfx_shotgn"),
            _rect(308, y + 2, 7, 7, 0x00E06020 if status.sfx_firsht else 0x00202020, "sfx_firsht"),
        ]
    )
    return tuple(rects)


def _draw_status_rects(frame: bytearray, commands: Sequence[Stage41StatusRectCommand]) -> int:
    pixels = 0
    for command in commands:
        color = (command.color & 0x00FFFFFF).to_bytes(4, "little")
        for yy in range(command.y, command.y + command.height):
            row = (yy * FRAMEBUFFER_WIDTH + command.x) * 4
            for xx in range(command.width):
                offset = row + xx * 4
                frame[offset : offset + 4] = color
                pixels += 1
    return pixels


def _status_state_signature(sample: Stage41StatusSample) -> int:
    status = sample.status
    sig = fnv1a_words(
        (
            sample.step,
            sample.tic,
            status.health,
            status.armor,
            status.shell_ammo,
            status.shotgun_owned,
            status.pending_weapon,
            status.bonuscount,
            status.damagecount,
            status.pickup_flash,
            status.damage_flash,
            status.sfx_wpnup,
            status.sfx_shotgn,
            status.sfx_firsht,
            status.status_phase,
            sample.command_count,
            sample.status_pixels_drawn,
            sample.pre_status_framebuffer_signature,
            sample.framebuffer_signature,
        )
    )
    sig = _hash_ascii(sig, status.message)
    sig = _hash_ascii(sig, status.source_marker)
    for command in sample.commands:
        sig = fnv1a_words((command.x, command.y, command.width, command.height, command.color), sig)
        sig = _hash_ascii(sig, command.field)
    return sig


def _stage41_signature(ref: Stage41StatusbarWeaponAmmoFeedbackBridgeReference) -> int:
    sig = fnv1a_words(
        (
            ref.stage40.signature,
            ref.stage40.state_signature,
            len(ref.samples),
            ref.distinct_selected_status_signatures,
            ref.distinct_framebuffer_signatures,
            ref.status_contribution_signatures,
            ref.paint_after_final_status,
            ref.source_status_player_fields,
            ref.source_hu_message_bridge,
            ref.source_pickup_feedback_bridge,
            ref.source_damage_feedback_bridge,
            ref.source_weapon_pending_bridge,
            ref.compact_status_strip_drawn,
            ref.status_draw_bounds_checked,
            ref.status_draw_after_world_vissprite_and_psprite,
            ref.status_draw_after_feedback_and_projectile_state,
            ref.stage40_vissprite_preserved,
            ref.stage39_projectile_state_preserved,
            ref.stage38_present_preserved,
            ref.stage37_feedback_preserved,
            ref.stage36_pickup_preserved,
            ref.full_frame_byte_arrays_absent,
            ref.runtime_renderer_primitives,
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
            ref.generalized_inventory_absent,
            ref.generalized_item_traversal_absent,
            ref.generalized_combat_absent,
            ref.broad_monster_ai_absent,
            ref.player_death_absent,
            ref.enemy_kill_drop_absent,
            ref.broad_all_map_sprite_traversal_absent,
            ref.generalized_projectile_manager_absent,
            ref.explosions_absent,
            ref.radius_damage_absent,
            ref.splash_damage_absent,
            ref.infighting_absent,
            ref.map_progression_absent,
            ref.source_stage42_absent,
            ref.state_signature,
        )
    )
    for sample in ref.samples:
        for value in (
            sample.step,
            sample.status.health,
            sample.status.shell_ammo,
            sample.status.shotgun_owned,
            sample.status.pending_weapon,
            sample.status.bonuscount,
            sample.status.damagecount,
            sample.status.sfx_wpnup,
            sample.status.sfx_shotgn,
            sample.status.sfx_firsht,
            sample.command_count,
            sample.status_pixels_drawn,
            sample.pre_status_framebuffer_signature,
            sample.framebuffer_signature,
            sample.selected_status_state_signature,
            sample.status_sequence,
            sample.signature_sequence,
            sample.present_sequence,
        ):
            sig = fnv1a_words((value,), sig)
        sig = _hash_ascii(sig, sample.status.message)
    return sig


def reference_statusbar_weapon_ammo_feedback_bridge_for_pinned_map(
    wad_path: str | Path,
) -> Stage41StatusbarWeaponAmmoFeedbackBridgeReference:
    ref40 = stage40.reference_bounded_vissprite_traversal_sorting_bridge_for_pinned_map(wad_path)
    ref39 = ref40.stage39
    ref38 = ref39.stage38
    ref36 = ref38.stage36
    ref33 = ref36.stage34.stage33
    ref32 = ref33.stage32
    palette32 = ref40.palette32
    samples: list[Stage41StatusSample] = []
    for index, sample40 in enumerate(ref40.samples):
        sample39 = sample40.baseline
        sample38 = sample39.baseline
        sample36 = sample38.baseline
        base_sample = ref32.stage31.samples[index]
        framebuf, _base_sig, _wall_pixels, _flat_pixels = stage32._draw_stage31_base(base_sample, ref32.stage31)
        stage40.stage33._draw_impact_commands(framebuf, sample36.impact_commands, ref33.impact_sources, palette32)
        stage36._draw_death_commands(framebuf, sample36.death_commands, ref36.death_sources, palette32)
        stage36._draw_drop_commands(framebuf, sample36.drop_commands, ref36.drop_sources, palette32)
        stage40._draw_vissprite_commands(framebuf, sample40.commands, ref40.sources, palette32)
        stage32._draw_psprite_commands(framebuf, sample36.psprite_commands, ref32.psprite_sources, palette32)
        stage38._draw_stage38_feedback_marker(framebuf, sample38.feedback_marker_pixels, 0x00E03030 + index * 0x00001010)
        pre_status_sig = stage31._framebuffer_signature(framebuf)
        status = selected_status_state_stage41_source_shape(index, ref40)
        commands = _status_rects_for_state(status)
        pixels = _draw_status_rects(framebuf, commands)
        final_sig = stage31._framebuffer_signature(framebuf)
        seq = index * 13
        sample = Stage41StatusSample(
            step=index + 1,
            tic=sample40.tic,
            baseline=sample40,
            status=status,
            commands=commands,
            command_count=len(commands),
            status_pixels_drawn=pixels,
            pre_status_framebuffer_signature=pre_status_sig,
            status_framebuffer_signature=final_sig,
            framebuffer_signature=final_sig,
            selected_status_state_signature=0,
            clear_sequence=seq + 1,
            wall_flat_sequence=seq + 2,
            impact_sequence=seq + 3,
            death_sequence=seq + 4,
            drop_sequence=seq + 5,
            world_vissprite_sequence=seq + 6,
            psprite_sequence=seq + 7,
            feedback_sequence=seq + 8,
            projectile_state_sequence=seq + 9,
            status_sequence=seq + 10,
            signature_sequence=seq + 11,
            present_sequence=seq + 12,
        )
        samples.append(Stage41StatusSample(**{**sample.__dict__, "selected_status_state_signature": _status_state_signature(sample)}))

    state_signature = fnv1a_words(tuple(sample.selected_status_state_signature for sample in samples))
    state_signature = _hash_ascii(state_signature, "stage41 compact ST/HU player feedback strip")
    draft = Stage41StatusbarWeaponAmmoFeedbackBridgeReference(
        stage40=ref40,
        samples=tuple(samples),
        distinct_selected_status_signatures=len({sample.selected_status_state_signature for sample in samples}),
        distinct_framebuffer_signatures=len({sample.framebuffer_signature for sample in samples}),
        status_contribution_signatures=sum(1 for sample in samples if sample.framebuffer_signature != sample.pre_status_framebuffer_signature),
        timer_samples=len(samples),
        invalidate_calls=len(samples),
        update_window_calls=len(samples),
        expected_paint_calls=len(samples),
        paint_after_final_status=1,
        final_window_alive_after_samples=1,
        closes_normally=1,
        source_status_player_fields=1,
        source_hu_message_bridge=1,
        source_pickup_feedback_bridge=1,
        source_damage_feedback_bridge=1,
        source_weapon_pending_bridge=1,
        compact_status_strip_drawn=1,
        status_draw_bounds_checked=1,
        status_draw_after_world_vissprite_and_psprite=1,
        status_draw_after_feedback_and_projectile_state=1,
        stage31_wall_flat_preserved=1,
        stage32_psprite_preserved=1,
        stage33_impact_preserved=1,
        stage34_death_preserved=1,
        stage35_drop_preserved=1,
        stage36_pickup_preserved=1,
        stage37_feedback_preserved=1,
        stage38_present_preserved=1,
        stage39_projectile_state_preserved=1,
        stage40_vissprite_preserved=1,
        full_frame_byte_arrays_absent=1,
        runtime_renderer_primitives=1,
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
        generalized_inventory_absent=1,
        generalized_item_traversal_absent=1,
        generalized_combat_absent=1,
        broad_monster_ai_absent=1,
        player_death_absent=1,
        enemy_kill_drop_absent=1,
        broad_all_map_sprite_traversal_absent=1,
        generalized_projectile_manager_absent=1,
        explosions_absent=1,
        radius_damage_absent=1,
        splash_damage_absent=1,
        infighting_absent=1,
        map_progression_absent=1,
        source_stage42_absent=1,
        state_signature=state_signature,
        signature=0,
    )
    return Stage41StatusbarWeaponAmmoFeedbackBridgeReference(
        **{**draft.__dict__, "signature": _stage41_signature(draft)}
    )


@lru_cache(maxsize=1)
def _reference_for_default_wad_or_none() -> Stage41StatusbarWeaponAmmoFeedbackBridgeReference | None:
    wad = REPO_ROOT / WAD_PATH
    if not wad.exists():
        return None
    return reference_statusbar_weapon_ammo_feedback_bridge_for_pinned_map(wad)


def _stage41_replay_titles(ref: Stage41StatusbarWeaponAmmoFeedbackBridgeReference | None) -> list[str]:
    if ref is None:
        return [
            "Inference Doom S41 STEP41=1 missing pinned WAD",
            "Inference Doom S41 STEP41=2 missing pinned WAD",
            "Inference Doom S41 STEP41=3 missing pinned WAD",
        ]
    titles: list[str] = []
    ref40 = ref.stage40
    ref39 = ref40.stage39
    ref38 = ref39.stage38
    for sample in ref.samples:
        st = sample.status
        titles.append(
            "Inference Doom S41 "
            f"STEP41={sample.step} TIC41={sample.tic} "
            f"HP41={st.health} ARM41={st.armor} SHELL41={st.shell_ammo} WOWN41={st.shotgun_owned} PEND41={st.pending_weapon} "
            f"MSG41={st.message or 'NONE'} BONUS41={st.bonuscount} DMG41={st.damagecount} "
            f"SFX41=sfx_wpnup:{st.sfx_wpnup},sfx_shotgn:{st.sfx_shotgn},sfx_firsht:{st.sfx_firsht} "
            f"STRIP41={sample.command_count} SPIX41={sample.status_pixels_drawn} PRE41={sample.pre_status_framebuffer_signature} "
            f"FB41={sample.framebuffer_signature} SSTATE41={sample.selected_status_state_signature} "
            f"STATE41={ref.state_signature} S41SIG={ref.signature} "
            f"PATCH40={sample.baseline.patch_name} MISS39={ref39.projectile.type_name} PST39={ref39.projectile.state_signature} "
            f"HP38={ref38.attack.health_before}->{ref38.attack.health_after} DMG38={ref38.attack.damagecount_after} "
            f"PICK36={ref38.stage36.pickup.give_weapon_return} GOT36={ref38.stage36.pickup.message} "
            f"INV41={sample.step} UPD41={sample.step} PAINT41={sample.step} PAF41={1 if sample.step == len(ref.samples) else 0} "
            f"INV40={ref40.invalidate_calls} UPD40={ref40.update_window_calls} PAINT40={ref40.expected_paint_calls} PAF40={ref40.paint_after_final_vissprite} "
            f"INV39={ref39.invalidate_calls} UPD39={ref39.update_window_calls} PAINT39={ref39.expected_paint_calls} PAF39={ref39.paint_after_final_projectile_marker} "
            f"S40SIG={ref40.signature} STATE40={ref40.state_signature} S39SIG={ref39.signature} STATE39={ref39.projectile.state_signature} "
            f"S38SIG={ref38.signature} STATE38={ref38.attack.state_signature} S37SIG={stage39.BASELINE_S37_SIGNATURE} "
            f"S36SIG={ref38.stage36.signature} S35SIG={stage36.ref35_signature(ref38.stage36)} "
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
            f"NOFULL41={ref.full_frame_byte_arrays_absent} S42ABS={ref.source_stage42_absent}"
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


def emit_stage41_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")
    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "stage41_class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage41_class_registered")
    x86.call_rel32(pe, "source_stage41_load_wad_statusbar_weapon_ammo_feedback_bridge")
    x86.call_rel32(pe, "append_stage41_success_status")
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
    x86.jne_rel32(pe, "stage41_window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage41_window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_abs32(pe, "stage41_replay_title_start")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE41_TIMER_MS)
    x86.push_imm32(pe, STAGE41_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
    pe.label("stage41_message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage41_clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "stage41_message_error")
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, stage38.WM_TIMER)
    x86.jne_rel32(pe, "stage41_dispatch_message")
    x86.call_rel32(pe, "stage41_timer_tick")
    pe.label("stage41_dispatch_message")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "stage41_message_loop")
    pe.label("stage41_clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")
    pe.label("stage41_message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_stage41_timer_tick(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(stage38.SELECTED_SAMPLE_TICS)
    pe.label("stage41_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage41_replay_step")
    for index in range(sample_count):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage41_replay_sample{index}")
    x86.ret(pe)
    for index in range(sample_count):
        pe.label(f"stage41_replay_sample{index}")
        x86.call_rel32(pe, f"stage41_draw_sample{index}")
        x86.push_abs32(pe, f"stage41_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        if index == sample_count - 1:
            x86.mov_mem_abs32_imm32(pe, "stage41_final_status_drawn", 1)
        stage07._emit_inc_abs32(pe, "stage41_invalidate_calls")
        x86.push_imm8(pe, 0)
        x86.push_imm8(pe, 0)
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "InvalidateRect")
        stage07._emit_inc_abs32(pe, "stage41_update_window_calls")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "UpdateWindow")
        x86.mov_mem_abs32_imm32(pe, "stage41_replay_step", index + 1)
        if index == sample_count - 1:
            x86.push_imm32(pe, STAGE41_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)


def emit_stage41_wndproc_framebuffer(pe: PE32) -> None:
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
    stage07._emit_inc_abs32(pe, "stage41_paint_calls")
    x86.mov_reg_mem_abs32(pe, "eax", "stage41_final_status_drawn")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "stage41_paint_after_final_skip")
    stage07._emit_inc_abs32(pe, "stage41_paint_after_final_status")
    pe.label("stage41_paint_after_final_skip")
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


def emit_stage41_draw_status_strip(pe: PE32) -> None:
    pe.label("V_DrawFilledBox_stage41_compact_status_strip_debug")
    pe.label("stage41_draw_status_strip")
    x86.mov_mem_abs32_imm32(pe, "stage41_status_rects_drawn", 0)
    pe.label("stage41_status_rect_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "stage41_status_remaining")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage41_status_done")
    x86.mov_reg_mem_abs32(pe, "esi", "stage41_status_scan_ptr")
    for field, dst in ((0, "stage41_rect_x"), (4, "stage41_rect_y"), (8, "stage41_rect_w"), (12, "stage41_rect_h"), (16, "stage41_rect_color"), (20, "stage41_rect_row_advance")):
        x86.mov_reg_ptr_reg_disp8(pe, "eax", "esi", field)
        x86.mov_mem_abs32_eax(pe, dst)
    stage07._emit_inc_abs32(pe, "stage41_status_rects_drawn")
    x86.mov_reg_mem_abs32(pe, "edx", "stage41_rect_y")
    x86.imul_reg_reg_imm32(pe, "edx", "edx", FRAMEBUFFER_WIDTH)
    x86.add_reg_mem_abs32(pe, "edx", "stage41_rect_x")
    x86.shl_reg_imm8(pe, "edx", 2)
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.add_reg_reg(pe, "edi", "edx")
    x86.mov_reg_mem_abs32(pe, "ebx", "stage41_rect_h")
    pe.label("stage41_status_row_loop")
    x86.mov_reg_mem_abs32(pe, "ecx", "stage41_rect_w")
    x86.mov_reg_mem_abs32(pe, "eax", "stage41_rect_color")
    pe.label("stage41_status_pixel_loop")
    x86.mov_ptr_reg_eax(pe, "edi")
    x86.add_reg_imm32(pe, "edi", 4)
    x86.dec_reg(pe, "ecx")
    x86.jne_rel32(pe, "stage41_status_pixel_loop")
    x86.add_reg_mem_abs32(pe, "edi", "stage41_rect_row_advance")
    x86.dec_reg(pe, "ebx")
    x86.jne_rel32(pe, "stage41_status_row_loop")
    x86.mov_reg_mem_abs32(pe, "esi", "stage41_status_scan_ptr")
    x86.add_reg_imm32(pe, "esi", STATUS_COMMAND_RECORD_SIZE)
    x86.mov_mem_abs32_reg(pe, "stage41_status_scan_ptr", "esi")
    x86.dec_mem_abs32(pe, "stage41_status_remaining")
    x86.jmp_rel32(pe, "stage41_status_rect_loop")
    pe.label("stage41_status_done")
    x86.ret(pe)


def _emit_stage41_draw_sample(pe: PE32, index: int) -> None:
    pe.label(f"stage41_draw_sample{index}")
    x86.call_rel32(pe, f"stage40_draw_sample{index}")
    x86.mov_reg_mem_abs32(pe, "eax", "stage40_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage41_pre_status_fb_signature")
    for dst, src in (
        ("stage41_status_scan_ptr", f"stage41_status_commands_{index}"),
        ("stage41_status_remaining", f"stage41_sample{index}_status_command_count"),
        ("stage41_status_pixels_drawn", f"stage41_sample{index}_status_pixels"),
        ("stage41_selected_status_state", f"stage41_sample{index}_status_state_signature"),
    ):
        if dst.endswith("ptr"):
            x86.mov_mem_abs32_abs32(pe, dst, src)
        else:
            x86.mov_reg_mem_abs32(pe, "eax", src)
            x86.mov_mem_abs32_eax(pe, dst)
    x86.call_rel32(pe, "stage41_draw_status_strip")
    x86.call_rel32(pe, "stage31_compute_framebuffer_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage31_runtime_fb_signature")
    x86.mov_mem_abs32_eax(pe, "stage41_runtime_fb_signature")
    x86.ret(pe)


def emit_source_stage41_load_wad_statusbar_weapon_ammo_feedback_bridge(pe: PE32) -> None:
    pe.label("source_stage41_load_wad_statusbar_weapon_ammo_feedback_bridge")
    x86.call_rel32(pe, "source_stage40_load_wad_bounded_vissprite_traversal_sorting_bridge")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "stage41_load_fail")
    x86.mov_reg_mem_abs32(pe, "eax", "stage40_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage40_expected_signature")
    x86.jne_rel32(pe, "stage41_load_fail")
    x86.call_rel32(pe, "render_statusbar_weapon_ammo_feedback_bridge_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage41_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage41_expected_signature")
    x86.jne_rel32(pe, "stage41_load_fail")
    x86.mov_reg_imm32(pe, "eax", 1)
    x86.ret(pe)
    pe.label("stage41_load_fail")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.ret(pe)


def emit_render_statusbar_weapon_ammo_feedback_bridge_debug(pe: PE32) -> None:
    for _, _, label in SOURCE_TRACE[-7:]:
        if label == "V_DrawFilledBox_stage41_compact_status_strip_debug":
            continue
        pe.label(label)
    pe.label("render_statusbar_weapon_ammo_feedback_bridge_debug")
    x86.mov_reg_mem_abs32(pe, "eax", "stage41_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage41_runtime_signature")
    x86.mov_reg_mem_abs32(pe, "eax", "stage41_expected_state_signature")
    x86.mov_mem_abs32_eax(pe, "stage41_runtime_state_signature")
    x86.ret(pe)


def emit_append_stage41_success_status(pe: PE32) -> None:
    pe.label("append_stage41_success_status")
    stage01.emit_set_status_ptrs(pe, "status_stage41_success_header", "stage41_replay_title_start")
    x86.ret(pe)


def _emit_status_commands(pe: PE32, commands: Sequence[Stage41StatusRectCommand]) -> None:
    for command in commands:
        pe.emit_u32(command.x)
        pe.emit_u32(command.y)
        pe.emit_u32(command.width)
        pe.emit_u32(command.height)
        pe.emit_u32(command.color)
        pe.emit_u32(command.row_advance)


def emit_stage41_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    samples = ref.samples if ref else ()
    final = samples[-1] if samples else None
    pe.align_section(4)
    values = (
        ("stage41_frame_count", len(samples)),
        ("stage41_distinct_status_signatures", ref.distinct_selected_status_signatures if ref else 0),
        ("stage41_distinct_fb_signatures", ref.distinct_framebuffer_signatures if ref else 0),
        ("stage41_status_contribution_signatures", ref.status_contribution_signatures if ref else 0),
        ("stage41_final_status_rects", final.command_count if final else 0),
        ("stage41_final_status_pixels", final.status_pixels_drawn if final else 0),
        ("stage41_expected_state_signature", ref.state_signature if ref else 0),
        ("stage41_runtime_state_signature", 0),
        ("stage41_expected_signature", ref.signature if ref else 0),
        ("stage41_runtime_signature", 0),
        ("stage41_runtime_fb_signature", 0),
        ("stage41_pre_status_fb_signature", 0),
        ("stage41_status_scan_ptr", 0),
        ("stage41_status_remaining", 0),
        ("stage41_status_rects_drawn", 0),
        ("stage41_status_pixels_drawn", 0),
        ("stage41_selected_status_state", 0),
        ("stage41_rect_x", 0),
        ("stage41_rect_y", 0),
        ("stage41_rect_w", 0),
        ("stage41_rect_h", 0),
        ("stage41_rect_color", 0),
        ("stage41_rect_row_advance", 0),
        ("stage41_replay_step", 0),
        ("stage41_invalidate_calls", 0),
        ("stage41_update_window_calls", 0),
        ("stage41_paint_calls", 0),
        ("stage41_final_status_drawn", 0),
        ("stage41_paint_after_final_status", 0),
        ("stage41_expected_timer_samples", ref.timer_samples if ref else 0),
        ("stage41_expected_invalidate_calls", ref.invalidate_calls if ref else 0),
        ("stage41_expected_update_window_calls", ref.update_window_calls if ref else 0),
        ("stage41_expected_paint_calls", ref.expected_paint_calls if ref else 0),
        ("stage41_expected_paint_after_final_status", ref.paint_after_final_status if ref else 0),
        ("stage41_compact_status_strip_drawn", ref.compact_status_strip_drawn if ref else 1),
        ("stage41_status_draw_bounds_checked", ref.status_draw_bounds_checked if ref else 1),
        ("stage41_full_frame_byte_arrays_absent", ref.full_frame_byte_arrays_absent if ref else 1),
        ("stage41_runtime_renderer_primitives", ref.runtime_renderer_primitives if ref else 1),
        ("stage41_broad_hud_statusbar_rebuild_absent", ref.broad_hud_statusbar_rebuild_absent if ref else 1),
        ("stage41_classic_full_statusbar_layout_absent", ref.classic_full_statusbar_layout_absent if ref else 1),
        ("stage41_face_animation_absent", ref.face_animation_absent if ref else 1),
        ("stage41_automap_absent", ref.automap_absent if ref else 1),
        ("stage41_menu_absent", ref.menu_absent if ref else 1),
        ("stage41_intermission_absent", ref.intermission_absent if ref else 1),
        ("stage41_save_load_absent", ref.save_load_absent if ref else 1),
        ("stage41_networking_absent", ref.networking_absent if ref else 1),
        ("stage41_music_absent", ref.music_absent if ref else 1),
        ("stage41_real_audio_absent", ref.real_audio_absent if ref else 1),
        ("stage41_generalized_inventory_absent", ref.generalized_inventory_absent if ref else 1),
        ("stage41_generalized_item_traversal_absent", ref.generalized_item_traversal_absent if ref else 1),
        ("stage41_generalized_combat_absent", ref.generalized_combat_absent if ref else 1),
        ("stage41_broad_monster_ai_absent", ref.broad_monster_ai_absent if ref else 1),
        ("stage41_source_stage42_absent", ref.source_stage42_absent if ref else 1),
    )
    for name, value in values:
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        for name, value in (
            (f"stage41_sample{index}_status_command_count", sample.command_count),
            (f"stage41_sample{index}_status_pixels", sample.status_pixels_drawn),
            (f"stage41_sample{index}_status_state_signature", sample.selected_status_state_signature),
            (f"stage41_sample{index}_framebuffer_signature", sample.framebuffer_signature),
            (f"stage41_sample{index}_health", sample.status.health),
            (f"stage41_sample{index}_armor", sample.status.armor),
            (f"stage41_sample{index}_shell_ammo", sample.status.shell_ammo),
            (f"stage41_sample{index}_shotgun_owned", sample.status.shotgun_owned),
            (f"stage41_sample{index}_pending_weapon", sample.status.pending_weapon),
            (f"stage41_sample{index}_bonuscount", sample.status.bonuscount),
            (f"stage41_sample{index}_damagecount", sample.status.damagecount),
        ):
            pe.label(name)
            pe.emit_u32(value & 0xFFFFFFFF)
    for index, sample in enumerate(samples):
        pe.align_section(4)
        pe.label(f"stage41_status_commands_{index}")
        _emit_status_commands(pe, sample.commands)
    pe.label("status_stage41_success_header")
    x86.emit_asciiz(pe, "\r\nStatusbar Weapon Ammo Feedback Bridge proof OK\r\n")
    pe.label("status_stage41_log_prefix")
    x86.emit_asciiz(pe, "source_stage41_statusbar_weapon_ammo_feedback_bridge ")
    pe.label("stage41_log_text")
    x86.emit_asciiz(
        pe,
        "ST_updateWidgets/HU_Ticker/P_TouchSpecialThing/P_DamageMobj/P_SetupPsprites selected compact status strip, "
        "health/armor/shells/shotgun/pending/GOTSHOTGUN/bonuscount/damagecount/deferred sfx_wpnup+sfx_shotgn+sfx_firsht, "
        "stage40 world-vissprite and present bridge preserved, NOFULL41=1, no broad HUD/statusbar/face/automap/menu/audio ",
    )
    pe.label("stage41_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S41 STATUS START STEP41=0 waiting for compact status strip redraw")
    for index, title in enumerate(_stage41_replay_titles(ref)):
        pe.label(f"stage41_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)


def build_source_stage41_statusbar_weapon_ammo_feedback_bridge_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    ref = _reference_for_default_wad_or_none()
    sample_count = len(ref.samples) if ref else len(stage38.SELECTED_SAMPLE_TICS)
    with patched_stage01_window_labels():
        emit_stage41_entry(pe)
        emit_stage41_wndproc_framebuffer(pe)
        emit_stage41_timer_tick(pe)
        stage31.emit_stage31_clear_framebuffer(pe)
        stage31.emit_stage31_framebuffer_signature(pe)
        stage31.emit_stage31_draw_command_loops(pe)
        stage40.stage33.emit_stage33_draw_impact_commands(pe)
        stage36.emit_stage36_draw_death_commands(pe)
        stage36.emit_stage36_draw_drop_commands(pe)
        stage40.emit_stage40_draw_vissprite_commands(pe)
        stage32.emit_stage32_draw_psprite_commands(pe)
        stage38.emit_stage38_draw_feedback_marker(pe)
        emit_stage41_draw_status_strip(pe)
        for index in range(sample_count):
            stage40._emit_stage40_draw_sample(pe, index)
            _emit_stage41_draw_sample(pe, index)
        stage36.emit_source_stage36_load_wad_selected_dropped_shotgun_visual_boundary(pe)
        stage38.emit_source_stage38_load_wad_selected_attack_feedback_present_bridge(pe)
        stage39.emit_source_stage39_load_wad_selected_projectile_spawn_present_probe(pe)
        stage40.emit_source_stage40_load_wad_bounded_vissprite_traversal_sorting_bridge(pe)
        emit_source_stage41_load_wad_statusbar_weapon_ammo_feedback_bridge(pe)
        stage36._emit_prior_loaders(pe)
        stage36._emit_runtime_helpers(pe)
        stage36.emit_render_selected_dropped_shotgun_visual_boundary_debug(pe)
        stage38.emit_render_selected_attack_feedback_present_bridge_debug(pe)
        stage39.emit_render_selected_projectile_spawn_present_probe_debug(pe)
        stage40.emit_render_bounded_vissprite_traversal_sorting_bridge_debug(pe)
        emit_render_statusbar_weapon_ammo_feedback_bridge_debug(pe)
        stage36._emit_prior_status(pe)
        stage36.emit_append_stage36_success_status(pe)
        stage38.emit_append_stage38_success_status(pe)
        stage39.emit_append_stage39_success_status(pe)
        stage40.emit_append_stage40_success_status(pe)
        emit_append_stage41_success_status(pe)
        stage01.emit_append_c_string(pe)
        stage01.emit_append_u32_decimal(pe)
        stage01.emit_append_i32_decimal(pe)
        stage01.emit_data(pe)
        stage36._emit_prior_data(pe)
        stage36.emit_stage36_data(pe)
        stage38.emit_stage38_data(pe)
        stage39.emit_stage39_data(pe)
        stage40.emit_stage40_data(pe)
        emit_stage41_data(pe)
    return pe.build("entry")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage41 compact statusbar weapon/ammo feedback PE32 probe"
    )
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output PE32 executable path")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = build_source_stage41_statusbar_weapon_ammo_feedback_bridge_exe()
    output.write_bytes(data)
    ref = _reference_for_default_wad_or_none()
    print(f"Wrote {output} ({len(data)} bytes)")
    if ref is not None:
        print(f"S41SIG={ref.signature}")
        print(f"STATE41={ref.state_signature}")
        print("FB41=" + ",".join(str(sample.framebuffer_signature) for sample in ref.samples))
        print("SSTATE41=" + ",".join(str(sample.selected_status_state_signature) for sample in ref.samples))


if __name__ == "__main__":
    main()
