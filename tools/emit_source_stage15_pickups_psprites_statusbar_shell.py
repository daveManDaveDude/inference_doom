from __future__ import annotations

import argparse
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Callable, Sequence


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage01_wad_map as stage01
from tools import emit_source_stage02_bsp_setup as stage02
from tools import emit_source_stage03_bsp_walk_debug as stage03
from tools import emit_source_stage04_bbox_visibility_debug as stage04
from tools import emit_source_stage07_wall_projection_debug as stage07
from tools import emit_source_stage08_texture_data_setup_debug as stage08
from tools import emit_source_stage09_direct_wall_column_pixels_debug as stage09
from tools import emit_source_stage10_composite_two_sided_wall_edges_debug as stage10
from tools import emit_source_stage11_visplanes_floor_ceiling_debug as stage11
from tools import emit_source_stage12_sky_and_masked_midtextures_debug as stage12
from tools import emit_source_stage13_things_sprites_and_real_frame_setup as stage13
from tools import emit_source_stage14_game_loop_input_collision as stage14
from tools import x86
from tools.map_loader import LoadedMap, load_map_from_file
from tools.pe32 import PE32
from tools.wad import Lump, WadFile


FRAMEBUFFER_WIDTH = stage14.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage14.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage14.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage14.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage14.WINDOW_WIDTH
WINDOW_HEIGHT = stage14.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage15PickupsPspritesStatusbarShell"
WINDOW_TITLE = "Inference Doom S15 Pickups Psprites Status"
WAD_PATH = stage14.WAD_PATH

FRACBITS = stage14.FRACBITS
FRACUNIT = stage14.FRACUNIT
VIEWHEIGHT = stage14.VIEWHEIGHT
FNV_PRIME = stage14.FNV_PRIME
CENTER_Y = stage13.CENTER_Y
WALL_COLUMN_SOURCE_HEIGHT = stage13.WALL_COLUMN_SOURCE_HEIGHT

BOXTOP = stage14.BOXTOP
BOXBOTTOM = stage14.BOXBOTTOM
BOXLEFT = stage14.BOXLEFT
BOXRIGHT = stage14.BOXRIGHT
MAXRADIUS = stage14.MAXRADIUS

BONUSADD = 6
MAXHEALTH = 100
DEH_INITIAL_HEALTH = 100
DEH_INITIAL_BULLETS = 50
DEH_MAX_HEALTH = 200
DEH_MAX_ARMOR = 200
DEH_SOULSPHERE_HEALTH = 100
DEH_MAX_SOULSPHERE = 200
DEH_MEGASPHERE_HEALTH = 200
DEH_GREEN_ARMOR_CLASS = 1
DEH_BLUE_ARMOR_CLASS = 2

NUMAMMO = 4
NUMWEAPONS = 9
NUMCARDS = 6
NUMPOWERS = 6
NUMPSPRITES = 2

AM_CLIP = 0
AM_SHELL = 1
AM_CELL = 2
AM_MISL = 3
AM_NOAMMO = 4

WP_FIST = 0
WP_PISTOL = 1
WP_SHOTGUN = 2
WP_CHAINGUN = 3
WP_MISSILE = 4
WP_PLASMA = 5
WP_BFG = 6
WP_CHAINSAW = 7
WP_SUPERSHOTGUN = 8
WP_NOCHANGE = 9

IT_BLUECARD = 0
IT_YELLOWCARD = 1
IT_REDCARD = 2
IT_BLUESKULL = 3
IT_YELLOWSKULL = 4
IT_REDSKULL = 5

PW_INVULNERABILITY = 0
PW_STRENGTH = 1
PW_INVISIBILITY = 2
PW_IRONFEET = 3
PW_ALLMAP = 4
PW_INFRARED = 5
INVULNTICS = 30 * 35
INVISTICS = 60 * 35
INFRATICS = 120 * 35
IRONTICS = 60 * 35

PS_WEAPON = 0
PS_FLASH = 1
LOWERSPEED = FRACUNIT * 6
RAISESPEED = FRACUNIT * 6
WEAPONBOTTOM = 128 * FRACUNIT
WEAPONTOP = 32 * FRACUNIT
PRE_PICKUP_PSPRITE_TICS = 20
POST_PICKUP_PSPRITE_TICS = 40

MAXAMMO = (200, 50, 300, 50)
CLIPAMMO = (10, 4, 20, 1)

STATUS_PATCH_NAMES = (
    "STBAR",
    "STARMS",
    "STTPRCNT",
    "STTNUM0",
    "STTNUM1",
    "STTNUM2",
    "STTNUM3",
    "STTNUM4",
    "STTNUM5",
    "STTNUM6",
    "STTNUM7",
    "STTNUM8",
    "STTNUM9",
    "STYSNUM2",
    "STYSNUM3",
)

DEFAULT_PICKUP_MAPTHING_INDEXES = (27, 41)

SOURCE_TRACE = stage14.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/doom/g_game.c",
        "G_PlayerReborn",
        "G_PlayerReborn_inventory_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_mobj.c",
        "P_SpawnPlayer",
        "P_SpawnPlayer_inventory_psprite_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_map.c",
        "PIT_CheckThing MF_SPECIAL branch",
        "PIT_CheckThing_special_touch_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_inter.c",
        "P_TouchSpecialThing and give helpers",
        "P_TouchSpecialThing_inventory_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_inter.c",
        "P_GiveAmmo/P_GiveWeapon/P_GiveBody/P_GiveArmor/P_GiveCard/P_GivePower",
        "P_GiveInventory_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/d_items.c",
        "weaponinfo",
        "weaponinfo_psprite_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_pspr.c",
        "P_SetupPsprites/P_SetPsprite/P_BringUpWeapon/P_MovePsprites/P_CheckAmmo",
        "P_Psprites_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/st_stuff.c",
        "ST_Start/ST_Ticker/ST_drawWidgets compact subset",
        "ST_StatusWidget_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/st_lib.c",
        "STlib_updateNum/STlib_updatePercent/STlib_updateMultIcon",
        "ST_StatusLibWidget_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/v_video.c",
        "V_DrawPatch",
        "V_DrawPatch_status_psprite_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/r_things.c",
        "R_DrawPSprite",
        "R_DrawPSprite_ready_weapon_shell_debug",
    ),
)


@dataclass(frozen=True)
class Stage15StateInfo:
    name: str
    sprite: int
    frame: int
    tics: int
    action: str
    nextstate: int
    misc1: int
    misc2: int


@dataclass(frozen=True)
class Stage15InfoTables:
    sprnames: tuple[str, ...]
    state_names: tuple[str, ...]
    states: tuple[Stage15StateInfo, ...]
    state_index: dict[str, int]
    sprite_index: dict[str, int]


@dataclass(frozen=True)
class WeaponInfo:
    ammo: int
    upstate: int
    downstate: int
    readystate: int
    atkstate: int
    flashstate: int


@dataclass
class PspDef:
    state: int | None = None
    tics: int = 0
    sx: int = 0
    sy: int = 0


@dataclass
class Stage15Player:
    mo_index: int
    health: int = DEH_INITIAL_HEALTH
    mo_health: int = DEH_INITIAL_HEALTH
    armorpoints: int = 0
    armortype: int = 0
    powers: list[int] | None = None
    cards: list[bool] | None = None
    backpack: bool = False
    readyweapon: int = WP_PISTOL
    pendingweapon: int = WP_PISTOL
    weaponowned: list[bool] | None = None
    ammo: list[int] | None = None
    maxammo: list[int] | None = None
    attackdown: bool = True
    usedown: bool = True
    refire: int = 0
    killcount: int = 0
    itemcount: int = 0
    secretcount: int = 0
    damagecount: int = 0
    bonuscount: int = 0
    extralight: int = 0
    fixedcolormap: int = 0
    psprites: list[PspDef] | None = None

    def __post_init__(self) -> None:
        if self.powers is None:
            self.powers = [0] * NUMPOWERS
        if self.cards is None:
            self.cards = [False] * NUMCARDS
        if self.weaponowned is None:
            self.weaponowned = [False] * NUMWEAPONS
        if self.ammo is None:
            self.ammo = [0] * NUMAMMO
        if self.maxammo is None:
            self.maxammo = list(MAXAMMO)
        if self.psprites is None:
            self.psprites = [PspDef() for _ in range(NUMPSPRITES)]


@dataclass
class Stage15Counters:
    pickup_probe_count: int = 0
    pickup_attempts: int = 0
    pickup_accepts: int = 0
    pickup_rejections: int = 0
    pickup_out_of_reach: int = 0
    unsupported_specials: int = 0
    removed_specials: int = 0
    message_deferred: int = 0
    sound_deferred: int = 0
    item_respawn_deferred: int = 0
    ammo_grants: int = 0
    weapon_grants: int = 0
    body_grants: int = 0
    armor_grants: int = 0
    card_grants: int = 0
    power_grants: int = 0
    psprite_set_calls: int = 0
    psprite_setup_calls: int = 0
    psprite_bringup_calls: int = 0
    psprite_move_calls: int = 0
    psprite_state_changes: int = 0
    psprite_no_fire_deferrals: int = 0
    psprite_sound_deferrals: int = 0
    status_ticker_calls: int = 0
    status_widget_updates: int = 0
    patch_draw_calls: int = 0
    patch_post_commands: int = 0


@dataclass
class Stage15World:
    movement: stage14.MovementWorld
    player: Stage15Player
    info: Stage15InfoTables
    doom: stage13.DoomInfoTables
    weaponinfo: tuple[WeaponInfo, ...]
    sprite_by_mobj_index: dict[int, int]
    patch_by_sprite_frame: dict[tuple[int, int], str]
    counters: Stage15Counters
    removed_mobj_indexes: set[int] | None = None

    def __post_init__(self) -> None:
        if self.removed_mobj_indexes is None:
            self.removed_mobj_indexes = set()


@dataclass(frozen=True)
class PickupProbeRecord:
    mapthing_index: int
    mobj_index: int
    type_name: str
    sprite_name: str
    x: int
    y: int
    block_x: int
    block_y: int
    accepted_move: int
    removed: int
    before_health: int
    after_health: int
    before_armor: int
    after_armor: int
    before_clip: int
    after_clip: int
    before_shell: int
    after_shell: int
    before_weapon_count: int
    after_weapon_count: int
    readyweapon_after: int
    pendingweapon_after: int


@dataclass(frozen=True)
class PatchDrawCommand:
    x: int
    yl: int
    yh: int
    iscale: int
    texturemid: int
    source_index: int
    tier: str
    patch_name: str
    patch_column: int


@dataclass(frozen=True)
class PatchDrawResult:
    commands: tuple[PatchDrawCommand, ...]
    column_sources: tuple[bytes, ...]
    status_patch_draws: int
    weapon_patch_draws: int
    status_columns: int
    weapon_columns: int
    status_pixels: int
    weapon_pixels: int
    first_status_patch: str
    first_weapon_patch: str
    weapon_state_name: str
    weapon_sprite_name: str
    signature: int


@dataclass(frozen=True)
class Stage15PickupsPspritesStatusbarReference:
    stage14: stage14.Stage14GameLoopInputCollisionReference
    pickups: tuple[PickupProbeRecord, ...]
    player: Stage15Player
    counters: Stage15Counters
    draw: PatchDrawResult
    pre_pickup_psprite_tics: int
    post_pickup_psprite_tics: int
    signature: int


def _u32(value: int) -> int:
    return value & 0xFFFFFFFF


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & 0xFFFFFFFF


def _hash_bytes(signature: int, data: bytes) -> int:
    for byte in data:
        signature = _hash_u32(signature, byte)
    return signature


def _state_name(info: Stage15InfoTables, state: int | None) -> str:
    if state is None:
        return "S_NULL"
    if 0 <= state < len(info.state_names):
        return info.state_names[state]
    return f"S_{state}"


def _weapon_count(player: Stage15Player) -> int:
    assert player.weaponowned is not None
    return sum(1 for owned in player.weaponowned if owned)


def _eval_int_expr(expr: str, namespace: dict[str, int]) -> int:
    expr = expr.strip()
    return int(eval(expr, {"__builtins__": {}}, namespace))


def parse_stage15_info_tables(
    info_path: str | Path = stage13.INFO_C,
) -> Stage15InfoTables:
    text = Path(info_path).read_text(encoding="utf-8")
    spr_match = re.search(r"const char \*sprnames\[\] = \{(.*?)NULL\s*\n\};", text, re.DOTALL)
    if spr_match is None:
        raise ValueError("could not find sprnames in info.c")
    sprnames = tuple(re.findall(r'"([A-Z0-9]{4})"', spr_match.group(1)))
    sprite_index = {f"SPR_{name}": index for index, name in enumerate(sprnames)}

    rows: list[tuple[str, str, str, str, str, str, str, str]] = []
    pattern = re.compile(
        r"\{\s*(SPR_[A-Z0-9]+)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*\{([^}]*)\}\s*,"
        r"\s*(S_[A-Z0-9_]+)\s*,\s*([^,]+)\s*,\s*([^}]+)\}\s*,?\s*//\s*(S_[A-Z0-9_]+)",
        re.DOTALL,
    )
    for match in pattern.finditer(text):
        sprite_name, frame_expr, tics_expr, action_expr, nextstate, misc1, misc2, state_name = match.groups()
        rows.append((state_name, sprite_name, frame_expr, tics_expr, action_expr.strip(), nextstate, misc1, misc2))

    state_names = tuple(row[0] for row in rows)
    state_index = {name: index for index, name in enumerate(state_names)}
    namespace = {
        "FRACUNIT": FRACUNIT,
        "FF_FULLBRIGHT": stage13.FF_FULLBRIGHT,
        **state_index,
    }
    states = tuple(
        Stage15StateInfo(
            name=state_name,
            sprite=sprite_index[sprite_name],
            frame=_eval_int_expr(frame_expr, namespace),
            tics=_eval_int_expr(tics_expr, namespace),
            action="" if action_expr == "NULL" else action_expr,
            nextstate=state_index[nextstate],
            misc1=_eval_int_expr(misc1, namespace),
            misc2=_eval_int_expr(misc2, namespace),
        )
        for state_name, sprite_name, frame_expr, tics_expr, action_expr, nextstate, misc1, misc2 in rows
    )
    return Stage15InfoTables(
        sprnames=sprnames,
        state_names=state_names,
        states=states,
        state_index=state_index,
        sprite_index=sprite_index,
    )


def build_weaponinfo_source_shape(info: Stage15InfoTables) -> tuple[WeaponInfo, ...]:
    s = info.state_index
    return (
        WeaponInfo(AM_NOAMMO, s["S_PUNCHUP"], s["S_PUNCHDOWN"], s["S_PUNCH"], s["S_PUNCH1"], s["S_NULL"]),
        WeaponInfo(AM_CLIP, s["S_PISTOLUP"], s["S_PISTOLDOWN"], s["S_PISTOL"], s["S_PISTOL1"], s["S_PISTOLFLASH"]),
        WeaponInfo(AM_SHELL, s["S_SGUNUP"], s["S_SGUNDOWN"], s["S_SGUN"], s["S_SGUN1"], s["S_SGUNFLASH1"]),
        WeaponInfo(AM_CLIP, s["S_CHAINUP"], s["S_CHAINDOWN"], s["S_CHAIN"], s["S_CHAIN1"], s["S_CHAINFLASH1"]),
        WeaponInfo(AM_MISL, s["S_MISSILEUP"], s["S_MISSILEDOWN"], s["S_MISSILE"], s["S_MISSILE1"], s["S_MISSILEFLASH1"]),
        WeaponInfo(AM_CELL, s["S_PLASMAUP"], s["S_PLASMADOWN"], s["S_PLASMA"], s["S_PLASMA1"], s["S_PLASMAFLASH1"]),
        WeaponInfo(AM_CELL, s["S_BFGUP"], s["S_BFGDOWN"], s["S_BFG"], s["S_BFG1"], s["S_BFGFLASH1"]),
        WeaponInfo(AM_NOAMMO, s["S_SAWUP"], s["S_SAWDOWN"], s["S_SAW"], s["S_SAW1"], s["S_NULL"]),
        WeaponInfo(AM_SHELL, s["S_DSGUNUP"], s["S_DSGUNDOWN"], s["S_DSGUN"], s["S_DSGUN1"], s["S_DSGUNFLASH1"]),
    )


def g_player_reborn_source_shape(
    *,
    killcount: int = 0,
    itemcount: int = 0,
    secretcount: int = 0,
    mo_index: int = 0,
) -> Stage15Player:
    player = Stage15Player(mo_index=mo_index)
    assert player.weaponowned is not None
    assert player.ammo is not None
    assert player.maxammo is not None
    player.killcount = killcount
    player.itemcount = itemcount
    player.secretcount = secretcount
    player.attackdown = True
    player.usedown = True
    player.health = DEH_INITIAL_HEALTH
    player.mo_health = DEH_INITIAL_HEALTH
    player.readyweapon = WP_PISTOL
    player.pendingweapon = WP_PISTOL
    player.weaponowned[WP_FIST] = True
    player.weaponowned[WP_PISTOL] = True
    player.ammo[AM_CLIP] = DEH_INITIAL_BULLETS
    player.maxammo[:] = list(MAXAMMO)
    return player


def p_give_ammo_source_shape(
    player: Stage15Player,
    ammo: int,
    num: int,
    weaponinfo: Sequence[WeaponInfo],
    counters: Stage15Counters | None = None,
) -> bool:
    assert player.ammo is not None
    assert player.maxammo is not None
    assert player.weaponowned is not None
    if ammo == AM_NOAMMO:
        return False
    if ammo >= NUMAMMO:
        raise ValueError(f"P_GiveAmmo: bad type {ammo}")
    if player.ammo[ammo] == player.maxammo[ammo]:
        return False
    amount = CLIPAMMO[ammo] * num if num else CLIPAMMO[ammo] // 2
    oldammo = player.ammo[ammo]
    player.ammo[ammo] = min(player.ammo[ammo] + amount, player.maxammo[ammo])
    if counters is not None:
        counters.ammo_grants += 1
    if oldammo:
        return True
    if ammo == AM_CLIP and player.readyweapon == WP_FIST:
        player.pendingweapon = WP_CHAINGUN if player.weaponowned[WP_CHAINGUN] else WP_PISTOL
    elif ammo == AM_SHELL and player.readyweapon in (WP_FIST, WP_PISTOL):
        if player.weaponowned[WP_SHOTGUN]:
            player.pendingweapon = WP_SHOTGUN
    elif ammo == AM_CELL and player.readyweapon in (WP_FIST, WP_PISTOL):
        if player.weaponowned[WP_PLASMA]:
            player.pendingweapon = WP_PLASMA
    elif ammo == AM_MISL and player.readyweapon == WP_FIST:
        if player.weaponowned[WP_MISSILE]:
            player.pendingweapon = WP_MISSILE
    return True


def p_give_weapon_source_shape(
    player: Stage15Player,
    weapon: int,
    dropped: bool,
    weaponinfo: Sequence[WeaponInfo],
    counters: Stage15Counters | None = None,
) -> bool:
    assert player.weaponowned is not None
    gaveammo = False
    info = weaponinfo[weapon]
    if info.ammo != AM_NOAMMO:
        gaveammo = p_give_ammo_source_shape(player, info.ammo, 1 if dropped else 2, weaponinfo, counters)
    gaveweapon = False
    if not player.weaponowned[weapon]:
        player.weaponowned[weapon] = True
        player.pendingweapon = weapon
        gaveweapon = True
        if counters is not None:
            counters.weapon_grants += 1
    return gaveweapon or gaveammo


def p_give_body_source_shape(
    player: Stage15Player,
    num: int,
    counters: Stage15Counters | None = None,
) -> bool:
    if player.health >= MAXHEALTH:
        return False
    player.health = min(player.health + num, MAXHEALTH)
    player.mo_health = player.health
    if counters is not None:
        counters.body_grants += 1
    return True


def p_give_armor_source_shape(
    player: Stage15Player,
    armortype: int,
    counters: Stage15Counters | None = None,
) -> bool:
    hits = armortype * 100
    if player.armorpoints >= hits:
        return False
    player.armortype = armortype
    player.armorpoints = hits
    if counters is not None:
        counters.armor_grants += 1
    return True


def p_give_card_source_shape(
    player: Stage15Player,
    card: int,
    counters: Stage15Counters | None = None,
) -> bool:
    assert player.cards is not None
    if player.cards[card]:
        return False
    player.bonuscount = BONUSADD
    player.cards[card] = True
    if counters is not None:
        counters.card_grants += 1
    return True


def p_give_power_source_shape(
    player: Stage15Player,
    power: int,
    counters: Stage15Counters | None = None,
) -> bool:
    assert player.powers is not None
    if power == PW_INVULNERABILITY:
        player.powers[power] = INVULNTICS
    elif power == PW_INVISIBILITY:
        player.powers[power] = INVISTICS
    elif power == PW_INFRARED:
        player.powers[power] = INFRATICS
    elif power == PW_IRONFEET:
        player.powers[power] = IRONTICS
    elif power == PW_STRENGTH:
        p_give_body_source_shape(player, 100, counters)
        player.powers[power] = 1
    else:
        if player.powers[power]:
            return False
        player.powers[power] = 1
    if counters is not None:
        counters.power_grants += 1
    return True


def _psp(player: Stage15Player, position: int) -> PspDef:
    assert player.psprites is not None
    return player.psprites[position]


def p_set_psprite_source_shape(
    player: Stage15Player,
    info: Stage15InfoTables,
    weaponinfo: Sequence[WeaponInfo],
    counters: Stage15Counters,
    position: int,
    stnum: int,
    *,
    max_steps: int = 64,
) -> None:
    counters.psprite_set_calls += 1
    psp = _psp(player, position)
    steps = 0
    while True:
        steps += 1
        if steps > max_steps:
            raise RuntimeError("P_SetPsprite exceeded bounded state steps")
        if stnum == info.state_index["S_NULL"]:
            psp.state = None
            psp.tics = 0
            counters.psprite_state_changes += 1
            return
        state = info.states[stnum]
        psp.state = stnum
        psp.tics = state.tics
        if state.misc1:
            psp.sx = state.misc1 << FRACBITS
            psp.sy = state.misc2 << FRACBITS
        counters.psprite_state_changes += 1

        if state.action == "A_Raise":
            a_raise_source_shape(player, info, weaponinfo, counters, psp)
        elif state.action == "A_Lower":
            a_lower_source_shape(player, info, weaponinfo, counters, psp)
        elif state.action == "A_WeaponReady":
            a_weapon_ready_source_shape(player, info, weaponinfo, counters, psp)
        elif state.action:
            counters.psprite_no_fire_deferrals += 1

        if psp.state is None or psp.tics:
            return
        stnum = info.states[psp.state].nextstate


def p_bring_up_weapon_source_shape(
    player: Stage15Player,
    info: Stage15InfoTables,
    weaponinfo: Sequence[WeaponInfo],
    counters: Stage15Counters,
) -> None:
    counters.psprite_bringup_calls += 1
    if player.pendingweapon == WP_NOCHANGE:
        player.pendingweapon = player.readyweapon
    if player.pendingweapon == WP_CHAINSAW:
        counters.psprite_sound_deferrals += 1
    newstate = weaponinfo[player.pendingweapon].upstate
    player.pendingweapon = WP_NOCHANGE
    _psp(player, PS_WEAPON).sy = WEAPONBOTTOM
    p_set_psprite_source_shape(player, info, weaponinfo, counters, PS_WEAPON, newstate)


def p_setup_psprites_source_shape(
    player: Stage15Player,
    info: Stage15InfoTables,
    weaponinfo: Sequence[WeaponInfo],
    counters: Stage15Counters,
) -> None:
    counters.psprite_setup_calls += 1
    assert player.psprites is not None
    for psp in player.psprites:
        psp.state = None
        psp.tics = 0
        psp.sx = 0
        psp.sy = 0
    player.pendingweapon = player.readyweapon
    p_bring_up_weapon_source_shape(player, info, weaponinfo, counters)


def a_raise_source_shape(
    player: Stage15Player,
    info: Stage15InfoTables,
    weaponinfo: Sequence[WeaponInfo],
    counters: Stage15Counters,
    psp: PspDef,
) -> None:
    psp.sy -= RAISESPEED
    if psp.sy > WEAPONTOP:
        return
    psp.sy = WEAPONTOP
    p_set_psprite_source_shape(player, info, weaponinfo, counters, PS_WEAPON, weaponinfo[player.readyweapon].readystate)


def a_lower_source_shape(
    player: Stage15Player,
    info: Stage15InfoTables,
    weaponinfo: Sequence[WeaponInfo],
    counters: Stage15Counters,
    psp: PspDef,
) -> None:
    psp.sy += LOWERSPEED
    if psp.sy < WEAPONBOTTOM:
        return
    psp.sy = WEAPONBOTTOM
    if player.health <= 0:
        p_set_psprite_source_shape(player, info, weaponinfo, counters, PS_WEAPON, info.state_index["S_NULL"])
        return
    player.readyweapon = player.pendingweapon
    p_bring_up_weapon_source_shape(player, info, weaponinfo, counters)


def a_weapon_ready_source_shape(
    player: Stage15Player,
    info: Stage15InfoTables,
    weaponinfo: Sequence[WeaponInfo],
    counters: Stage15Counters,
    psp: PspDef,
) -> None:
    if player.pendingweapon != WP_NOCHANGE or player.health <= 0:
        p_set_psprite_source_shape(player, info, weaponinfo, counters, PS_WEAPON, weaponinfo[player.readyweapon].downstate)
        return
    player.attackdown = False
    psp.sx = FRACUNIT
    psp.sy = WEAPONTOP


def p_move_psprites_source_shape(
    player: Stage15Player,
    info: Stage15InfoTables,
    weaponinfo: Sequence[WeaponInfo],
    counters: Stage15Counters,
) -> None:
    counters.psprite_move_calls += 1
    assert player.psprites is not None
    for position, psp in enumerate(player.psprites):
        if psp.state is None:
            continue
        if psp.tics != -1:
            psp.tics -= 1
            if not psp.tics and psp.state is not None:
                p_set_psprite_source_shape(
                    player,
                    info,
                    weaponinfo,
                    counters,
                    position,
                    info.states[psp.state].nextstate,
                )
    player.psprites[PS_FLASH].sx = player.psprites[PS_WEAPON].sx
    player.psprites[PS_FLASH].sy = player.psprites[PS_WEAPON].sy


def p_check_ammo_source_shape(
    player: Stage15Player,
    info: Stage15InfoTables,
    weaponinfo: Sequence[WeaponInfo],
    counters: Stage15Counters,
) -> bool:
    assert player.weaponowned is not None
    assert player.ammo is not None
    ammo = weaponinfo[player.readyweapon].ammo
    if player.readyweapon == WP_BFG:
        count = 40
    elif player.readyweapon == WP_SUPERSHOTGUN:
        count = 2
    else:
        count = 1
    if ammo == AM_NOAMMO or player.ammo[ammo] >= count:
        return True
    if player.weaponowned[WP_PLASMA] and player.ammo[AM_CELL]:
        player.pendingweapon = WP_PLASMA
    elif player.weaponowned[WP_SUPERSHOTGUN] and player.ammo[AM_SHELL] > 2:
        player.pendingweapon = WP_SUPERSHOTGUN
    elif player.weaponowned[WP_CHAINGUN] and player.ammo[AM_CLIP]:
        player.pendingweapon = WP_CHAINGUN
    elif player.weaponowned[WP_SHOTGUN] and player.ammo[AM_SHELL]:
        player.pendingweapon = WP_SHOTGUN
    elif player.ammo[AM_CLIP]:
        player.pendingweapon = WP_PISTOL
    elif player.weaponowned[WP_CHAINSAW]:
        player.pendingweapon = WP_CHAINSAW
    elif player.weaponowned[WP_MISSILE] and player.ammo[AM_MISL]:
        player.pendingweapon = WP_MISSILE
    elif player.weaponowned[WP_BFG] and player.ammo[AM_CELL] > 40:
        player.pendingweapon = WP_BFG
    else:
        player.pendingweapon = WP_FIST
    p_set_psprite_source_shape(player, info, weaponinfo, counters, PS_WEAPON, weaponinfo[player.readyweapon].downstate)
    return False


def p_spawn_player_inventory_psprite_source_shape(
    world: stage14.MovementWorld,
    info: Stage15InfoTables,
    weaponinfo: Sequence[WeaponInfo],
    counters: Stage15Counters,
) -> Stage15Player:
    player = g_player_reborn_source_shape(
        killcount=0,
        itemcount=0,
        secretcount=0,
        mo_index=world.player.mo_index,
    )
    world.player.viewheight = VIEWHEIGHT
    world.player.playerstate = stage14.PST_LIVE
    p_setup_psprites_source_shape(player, info, weaponinfo, counters)
    return player


def p_remove_mobj_source_shape(world: Stage15World, special: stage14.MovementMobj) -> None:
    assert world.removed_mobj_indexes is not None
    if special.index in world.removed_mobj_indexes:
        return
    if (special.flags & stage13.MF_SPECIAL) and not (special.flags & stage13.MF_DROPPED):
        world.counters.item_respawn_deferred += 1
    stage14.p_unset_thing_position_source_shape(world.movement, special)
    world.removed_mobj_indexes.add(special.index)
    world.counters.removed_specials += 1


def p_touch_special_thing_source_shape(
    world: Stage15World,
    special: stage14.MovementMobj,
    toucher: stage14.MovementMobj,
) -> bool:
    delta = special.z - toucher.z
    if delta > toucher.height or delta < -8 * FRACUNIT:
        world.counters.pickup_out_of_reach += 1
        return False
    if world.player.health <= 0:
        return False

    player = world.player
    sprite = world.sprite_by_mobj_index.get(special.index, -1)
    sprite_name = world.info.sprnames[sprite] if 0 <= sprite < len(world.info.sprnames) else ""
    accepted = False

    if sprite_name == "ARM1":
        accepted = p_give_armor_source_shape(player, DEH_GREEN_ARMOR_CLASS, world.counters)
    elif sprite_name == "ARM2":
        accepted = p_give_armor_source_shape(player, DEH_BLUE_ARMOR_CLASS, world.counters)
    elif sprite_name == "BON1":
        player.health = min(player.health + 1, DEH_MAX_HEALTH)
        player.mo_health = player.health
        accepted = True
    elif sprite_name == "BON2":
        player.armorpoints = min(player.armorpoints + 1, DEH_MAX_ARMOR)
        if not player.armortype:
            player.armortype = 1
        accepted = True
    elif sprite_name == "SOUL":
        player.health = min(player.health + DEH_SOULSPHERE_HEALTH, DEH_MAX_SOULSPHERE)
        player.mo_health = player.health
        accepted = True
    elif sprite_name == "MEGA":
        player.health = DEH_MEGASPHERE_HEALTH
        player.mo_health = player.health
        p_give_armor_source_shape(player, 2, world.counters)
        accepted = True
    elif sprite_name == "BKEY":
        accepted = p_give_card_source_shape(player, IT_BLUECARD, world.counters)
    elif sprite_name == "YKEY":
        accepted = p_give_card_source_shape(player, IT_YELLOWCARD, world.counters)
    elif sprite_name == "RKEY":
        accepted = p_give_card_source_shape(player, IT_REDCARD, world.counters)
    elif sprite_name == "BSKU":
        accepted = p_give_card_source_shape(player, IT_BLUESKULL, world.counters)
    elif sprite_name == "YSKU":
        accepted = p_give_card_source_shape(player, IT_YELLOWSKULL, world.counters)
    elif sprite_name == "RSKU":
        accepted = p_give_card_source_shape(player, IT_REDSKULL, world.counters)
    elif sprite_name == "STIM":
        accepted = p_give_body_source_shape(player, 10, world.counters)
    elif sprite_name == "MEDI":
        accepted = p_give_body_source_shape(player, 25, world.counters)
    elif sprite_name == "PINV":
        accepted = p_give_power_source_shape(player, PW_INVULNERABILITY, world.counters)
    elif sprite_name == "PSTR":
        accepted = p_give_power_source_shape(player, PW_STRENGTH, world.counters)
        if accepted and player.readyweapon != WP_FIST:
            player.pendingweapon = WP_FIST
    elif sprite_name == "PINS":
        accepted = p_give_power_source_shape(player, PW_INVISIBILITY, world.counters)
    elif sprite_name == "SUIT":
        accepted = p_give_power_source_shape(player, PW_IRONFEET, world.counters)
    elif sprite_name == "PMAP":
        accepted = p_give_power_source_shape(player, PW_ALLMAP, world.counters)
    elif sprite_name == "PVIS":
        accepted = p_give_power_source_shape(player, PW_INFRARED, world.counters)
    elif sprite_name == "CLIP":
        accepted = p_give_ammo_source_shape(
            player,
            AM_CLIP,
            0 if (special.flags & stage13.MF_DROPPED) else 1,
            world.weaponinfo,
            world.counters,
        )
    elif sprite_name == "AMMO":
        accepted = p_give_ammo_source_shape(player, AM_CLIP, 5, world.weaponinfo, world.counters)
    elif sprite_name == "ROCK":
        accepted = p_give_ammo_source_shape(player, AM_MISL, 1, world.weaponinfo, world.counters)
    elif sprite_name == "BROK":
        accepted = p_give_ammo_source_shape(player, AM_MISL, 5, world.weaponinfo, world.counters)
    elif sprite_name == "CELL":
        accepted = p_give_ammo_source_shape(player, AM_CELL, 1, world.weaponinfo, world.counters)
    elif sprite_name == "CELP":
        accepted = p_give_ammo_source_shape(player, AM_CELL, 5, world.weaponinfo, world.counters)
    elif sprite_name == "SHEL":
        accepted = p_give_ammo_source_shape(player, AM_SHELL, 1, world.weaponinfo, world.counters)
    elif sprite_name == "SBOX":
        accepted = p_give_ammo_source_shape(player, AM_SHELL, 5, world.weaponinfo, world.counters)
    elif sprite_name == "BPAK":
        if not player.backpack:
            assert player.maxammo is not None
            player.maxammo[:] = [value * 2 for value in player.maxammo]
            player.backpack = True
        accepted = any(
            p_give_ammo_source_shape(player, ammo, 1, world.weaponinfo, world.counters)
            for ammo in range(NUMAMMO)
        ) or player.backpack
    elif sprite_name == "BFUG":
        accepted = p_give_weapon_source_shape(player, WP_BFG, False, world.weaponinfo, world.counters)
    elif sprite_name == "MGUN":
        accepted = p_give_weapon_source_shape(
            player,
            WP_CHAINGUN,
            bool(special.flags & stage13.MF_DROPPED),
            world.weaponinfo,
            world.counters,
        )
    elif sprite_name == "CSAW":
        accepted = p_give_weapon_source_shape(player, WP_CHAINSAW, False, world.weaponinfo, world.counters)
    elif sprite_name == "LAUN":
        accepted = p_give_weapon_source_shape(player, WP_MISSILE, False, world.weaponinfo, world.counters)
    elif sprite_name == "PLAS":
        accepted = p_give_weapon_source_shape(player, WP_PLASMA, False, world.weaponinfo, world.counters)
    elif sprite_name == "SHOT":
        accepted = p_give_weapon_source_shape(
            player,
            WP_SHOTGUN,
            bool(special.flags & stage13.MF_DROPPED),
            world.weaponinfo,
            world.counters,
        )
    elif sprite_name == "SGN2":
        accepted = p_give_weapon_source_shape(
            player,
            WP_SUPERSHOTGUN,
            bool(special.flags & stage13.MF_DROPPED),
            world.weaponinfo,
            world.counters,
        )
    else:
        world.counters.unsupported_specials += 1
        return False

    if not accepted:
        world.counters.pickup_rejections += 1
        return False

    if special.flags & stage13.MF_COUNTITEM:
        player.itemcount += 1
    p_remove_mobj_source_shape(world, special)
    player.bonuscount += BONUSADD
    world.counters.message_deferred += 1
    world.counters.sound_deferred += 1
    world.counters.pickup_accepts += 1
    return True


def pit_check_thing_special_touch_source_shape(
    world: Stage15World,
    tmthing: stage14.MovementMobj,
    thing: stage14.MovementMobj,
    tmx: int,
    tmy: int,
) -> bool:
    if not (thing.flags & (stage13.MF_SOLID | stage13.MF_SPECIAL | stage13.MF_SHOOTABLE)):
        return True
    blockdist = thing.radius + tmthing.radius
    if abs(thing.x - tmx) >= blockdist or abs(thing.y - tmy) >= blockdist:
        return True
    if thing.index == tmthing.index:
        return True
    world.movement.counters.thing_checks += 1
    if thing.flags & stage13.MF_SPECIAL:
        solid = bool(thing.flags & stage13.MF_SOLID)
        if tmthing.flags & stage13.MF_PICKUP:
            world.counters.pickup_attempts += 1
            p_touch_special_thing_source_shape(world, thing, tmthing)
        return not solid
    if thing.flags & stage13.MF_SOLID:
        world.movement.counters.blocking_things += 1
        return False
    return True


def p_check_position_pickups_source_shape(
    world: Stage15World,
    thing: stage14.MovementMobj,
    x: int,
    y: int,
) -> bool:
    movement = world.movement
    movement.counters.check_position_calls += 1
    movement.tmbbox = (
        y + thing.radius,
        y - thing.radius,
        x - thing.radius,
        x + thing.radius,
    )
    _new_subsector, new_sector = stage14._subsector_sector_for_point(movement, x, y)
    sector = movement.sectors[new_sector]
    movement.tmfloorz = sector.floorheight
    movement.tmdropoffz = sector.floorheight
    movement.tmceilingz = sector.ceilingheight
    movement.validcount += 1
    movement.iterator.validcount = movement.validcount
    if movement.spechit is not None:
        movement.spechit.clear()

    if thing.flags & stage13.MF_NOCLIP:
        return True

    xl = stage14._block_coord(movement, movement.tmbbox[BOXLEFT] - MAXRADIUS, movement.blockmap.origin_x)
    xh = stage14._block_coord(movement, movement.tmbbox[BOXRIGHT] + MAXRADIUS, movement.blockmap.origin_x)
    yl = stage14._block_coord(movement, movement.tmbbox[BOXBOTTOM] - MAXRADIUS, movement.blockmap.origin_y)
    yh = stage14._block_coord(movement, movement.tmbbox[BOXTOP] + MAXRADIUS, movement.blockmap.origin_y)
    for bx in range(xl, xh + 1):
        for by in range(yl, yh + 1):
            if not stage14.p_block_things_iterator_source_shape(
                movement,
                bx,
                by,
                lambda other: pit_check_thing_special_touch_source_shape(world, thing, other, x, y),
            ):
                return False

    xl = stage14._block_coord(movement, movement.tmbbox[BOXLEFT], movement.blockmap.origin_x)
    xh = stage14._block_coord(movement, movement.tmbbox[BOXRIGHT], movement.blockmap.origin_x)
    yl = stage14._block_coord(movement, movement.tmbbox[BOXBOTTOM], movement.blockmap.origin_y)
    yh = stage14._block_coord(movement, movement.tmbbox[BOXTOP], movement.blockmap.origin_y)
    for bx in range(xl, xh + 1):
        for by in range(yl, yh + 1):
            if not stage14.p_block_lines_iterator_source_shape(
                movement.blockmap,
                bx,
                by,
                movement.lines,
                movement.iterator,
                lambda line: stage14.pit_check_line_source_shape(movement, thing, line),
            ):
                return False
    return True


def p_try_move_pickups_source_shape(
    world: Stage15World,
    thing: stage14.MovementMobj,
    x: int,
    y: int,
) -> bool:
    movement = world.movement
    movement.counters.try_move_calls += 1
    oldx = thing.x
    oldy = thing.y
    if not p_check_position_pickups_source_shape(world, thing, x, y):
        movement.counters.rejected_moves += 1
        return False
    if not (thing.flags & stage13.MF_NOCLIP):
        if movement.tmceilingz - movement.tmfloorz < thing.height:
            movement.counters.nofit_rejects += 1
            movement.counters.rejected_moves += 1
            return False
        if not (thing.flags & stage13.MF_TELEPORT) and movement.tmceilingz - thing.z < thing.height:
            movement.counters.ceiling_rejects += 1
            movement.counters.rejected_moves += 1
            return False
        if not (thing.flags & stage13.MF_TELEPORT) and movement.tmfloorz - thing.z > 24 * FRACUNIT:
            movement.counters.step_rejects += 1
            movement.counters.rejected_moves += 1
            return False
        if not (thing.flags & (stage13.MF_DROPOFF | stage13.MF_FLOAT)) and movement.tmfloorz - movement.tmdropoffz > 24 * FRACUNIT:
            movement.counters.dropoff_rejects += 1
            movement.counters.rejected_moves += 1
            return False

    stage14.p_unset_thing_position_source_shape(movement, thing)
    thing.floorz = movement.tmfloorz
    thing.ceilingz = movement.tmceilingz
    thing.x = x
    thing.y = y
    stage14.p_set_thing_position_source_shape(movement, thing)
    movement.counters.accepted_moves += 1

    if not (thing.flags & (stage13.MF_TELEPORT | stage13.MF_NOCLIP)) and movement.spechit:
        for line_index in reversed(movement.spechit):
            line = movement.lines[line_index]
            side = stage14.point_on_line_side_source_shape(thing.x, thing.y, line)
            oldside = stage14.point_on_line_side_source_shape(oldx, oldy, line)
            if side != oldside and line.special:
                movement.counters.special_lines_deferred += 1
    return True


def st_ticker_compact_source_shape(world: Stage15World) -> tuple[int, int, int]:
    world.counters.status_ticker_calls += 1
    assert world.player.cards is not None
    keyboxes = []
    for i in range(3):
        keybox = i if world.player.cards[i] else -1
        if world.player.cards[i + 3]:
            keybox = i + 3
        keyboxes.append(keybox)
    world.counters.status_widget_updates += 1
    return tuple(keyboxes)  # type: ignore[return-value]


def _lookup_lump(wad: WadFile, name: str) -> Lump:
    lump = wad.find_lump(name)
    if lump is None:
        raise KeyError(f"required patch lump missing: {name}")
    return lump


def _patch_header_origin(data: bytes, lump_name: str) -> tuple[int, int, int, int]:
    if len(data) < 8:
        raise stage08.TextureFormatError(f"patch lump {lump_name} header is truncated")
    return stage13._patch_header_origin(data, lump_name)


def _append_patch_commands(
    wad: WadFile,
    patch_name: str,
    x: int,
    y: int,
    tier: str,
    commands: list[PatchDrawCommand],
    sources: list[bytes],
) -> tuple[int, int]:
    lump = _lookup_lump(wad, patch_name)
    data = wad.read_lump(lump)
    width, _height, leftoffset, topoffset = _patch_header_origin(data, lump.name)
    base_x = x - leftoffset
    base_y = y - topoffset
    pixel_count = 0
    post_count = 0
    texturemid = (CENTER_Y - base_y) << FRACBITS
    for column_index in range(width):
        screen_x = base_x + column_index
        if screen_x < 0 or screen_x >= FRAMEBUFFER_WIDTH:
            continue
        posts = stage09.parse_patch_column_posts(data, column_index, lump_name=lump.name)
        for post in posts:
            screen_y = base_y + post.topdelta
            post_pixels = post.pixels
            yl = max(0, screen_y)
            yh = min(FRAMEBUFFER_HEIGHT - 1, screen_y + len(post_pixels) - 1)
            if yh < yl:
                continue
            source = bytearray(WALL_COLUMN_SOURCE_HEIGHT)
            for row, value in enumerate(post_pixels):
                source_row = post.topdelta + row
                if 0 <= source_row < WALL_COLUMN_SOURCE_HEIGHT:
                    source[source_row] = value
            source_index = len(sources)
            sources.append(bytes(source))
            commands.append(
                PatchDrawCommand(
                    x=screen_x,
                    yl=yl,
                    yh=yh,
                    iscale=FRACUNIT,
                    texturemid=texturemid,
                    source_index=source_index,
                    tier=tier,
                    patch_name=patch_name,
                    patch_column=column_index,
                )
            )
            pixel_count += yh - yl + 1
            post_count += 1
    return post_count, pixel_count


def _append_psprite_patch_commands(
    wad: WadFile,
    patch_name: str,
    psp: PspDef,
    tier: str,
    commands: list[PatchDrawCommand],
    sources: list[bytes],
) -> tuple[int, int]:
    lump = _lookup_lump(wad, patch_name)
    data = wad.read_lump(lump)
    width, _height, leftoffset, topoffset = _patch_header_origin(data, lump.name)

    centerxfrac = (FRAMEBUFFER_WIDTH // 2) << FRACBITS
    tx = psp.sx - ((FRAMEBUFFER_WIDTH // 2) << FRACBITS)
    tx -= leftoffset << FRACBITS
    x1 = (centerxfrac + tx) >> FRACBITS
    if x1 > FRAMEBUFFER_WIDTH:
        return 0, 0
    tx += width << FRACBITS
    x2 = ((centerxfrac + tx) >> FRACBITS) - 1
    if x2 < 0:
        return 0, 0

    visible_x1 = max(0, x1)
    visible_x2 = min(FRAMEBUFFER_WIDTH - 1, x2)
    startfrac = visible_x1 - x1
    texturemid = (CENTER_Y << FRACBITS) + (FRACUNIT // 2) - (psp.sy - (topoffset << FRACBITS))
    sprtopscreen = (CENTER_Y << FRACBITS) - texturemid

    pixel_count = 0
    post_count = 0
    for screen_x in range(visible_x1, visible_x2 + 1):
        patch_column = startfrac
        startfrac += 1
        if patch_column < 0 or patch_column >= width:
            continue
        posts = stage09.parse_patch_column_posts(data, patch_column, lump_name=lump.name)
        for post in posts:
            topscreen = sprtopscreen + (post.topdelta << FRACBITS)
            bottomscreen = topscreen + (len(post.pixels) << FRACBITS)
            yl = (topscreen + FRACUNIT - 1) >> FRACBITS
            yh = (bottomscreen - 1) >> FRACBITS
            yl = max(0, yl)
            yh = min(FRAMEBUFFER_HEIGHT - 1, yh)
            if yh < yl:
                continue
            source = bytearray(WALL_COLUMN_SOURCE_HEIGHT)
            for row, value in enumerate(post.pixels[:WALL_COLUMN_SOURCE_HEIGHT]):
                source[row] = value
            source_index = len(sources)
            sources.append(bytes(source))
            commands.append(
                PatchDrawCommand(
                    x=screen_x,
                    yl=yl,
                    yh=yh,
                    iscale=FRACUNIT,
                    texturemid=texturemid - (post.topdelta << FRACBITS),
                    source_index=source_index,
                    tier=tier,
                    patch_name=patch_name,
                    patch_column=patch_column,
                )
            )
            pixel_count += yh - yl + 1
            post_count += 1
    return post_count, pixel_count


def _draw_status_number(
    wad: WadFile,
    value: int,
    x: int,
    y: int,
    width: int,
    patch_prefix: str,
    commands: list[PatchDrawCommand],
    sources: list[bytes],
) -> tuple[int, int, int]:
    if value < 0:
        value = 0
    digits = list(str(value))[-width:]
    if not digits:
        digits = ["0"]
    patch_draws = 0
    posts = 0
    pixels = 0
    cursor = x
    sample = wad.read_lump(_lookup_lump(wad, f"{patch_prefix}0"))
    digit_width, _height, _left, _top = _patch_header_origin(sample, f"{patch_prefix}0")
    for digit in reversed(digits):
        cursor -= digit_width
        post_count, pixel_count = _append_patch_commands(
            wad,
            f"{patch_prefix}{digit}",
            cursor,
            y,
            "status",
            commands,
            sources,
        )
        patch_draws += 1
        posts += post_count
        pixels += pixel_count
    return patch_draws, posts, pixels


def _patch_name_for_psprite(world: Stage15World) -> tuple[str, str, str]:
    psp = _psp(world.player, PS_WEAPON)
    if psp.state is None:
        return "", "S_NULL", ""
    state = world.info.states[psp.state]
    sprite_name = world.info.sprnames[state.sprite]
    frame = state.frame & stage13.FF_FRAMEMASK
    patch_name = world.patch_by_sprite_frame.get((state.sprite, frame), f"{sprite_name}{chr(ord('A') + frame)}0")
    return patch_name, state.name, sprite_name


def build_patch_frame_lookup(wad: WadFile, info: Stage15InfoTables) -> dict[tuple[int, int], str]:
    result: dict[tuple[int, int], str] = {}
    names = {lump.name for lump in wad.lumps}
    for sprite_index, sprite_name in enumerate(info.sprnames):
        for frame in range(29):
            patch_name = f"{sprite_name}{chr(ord('A') + frame)}0"
            if patch_name in names:
                result[(sprite_index, frame)] = patch_name
    return result


def build_status_psprite_patch_draw_source_shape(
    wad: WadFile,
    world: Stage15World,
) -> PatchDrawResult:
    commands: list[PatchDrawCommand] = []
    sources: list[bytes] = []
    status_patch_draws = 0
    status_posts = 0
    status_pixels = 0
    weapon_patch_draws = 0
    weapon_pixels = 0
    weapon_posts = 0

    post_count, pixel_count = _append_patch_commands(wad, "STBAR", 0, 168, "status", commands, sources)
    status_patch_draws += 1
    status_posts += post_count
    status_pixels += pixel_count

    post_count, pixel_count = _append_patch_commands(wad, "STARMS", 104, 168, "status", commands, sources)
    status_patch_draws += 1
    status_posts += post_count
    status_pixels += pixel_count

    assert world.player.ammo is not None
    ready_ammo_type = world.weaponinfo[world.player.readyweapon].ammo
    ready_ammo = 1994 if ready_ammo_type == AM_NOAMMO else world.player.ammo[ready_ammo_type]
    for value, x, y in (
        (ready_ammo, 44, 171),
        (world.player.health, 90, 171),
        (world.player.armorpoints, 221, 171),
    ):
        patch_draws, posts, pixels = _draw_status_number(
            wad,
            value,
            x,
            y,
            3,
            "STTNUM",
            commands,
            sources,
        )
        status_patch_draws += patch_draws
        status_posts += posts
        status_pixels += pixels

    for x in (90, 221):
        post_count, pixel_count = _append_patch_commands(wad, "STTPRCNT", x, 171, "status", commands, sources)
        status_patch_draws += 1
        status_posts += post_count
        status_pixels += pixel_count

    # Compact arms proof: yellow pistol and shotgun numbers from STlib arms widgets.
    for patch_name, x, y in (("STYSNUM2", 111, 172), ("STYSNUM3", 123, 172)):
        post_count, pixel_count = _append_patch_commands(wad, patch_name, x, y, "status", commands, sources)
        status_patch_draws += 1
        status_posts += post_count
        status_pixels += pixel_count

    weapon_patch_name, weapon_state_name, weapon_sprite_name = _patch_name_for_psprite(world)
    if weapon_patch_name:
        psp = _psp(world.player, PS_WEAPON)
        post_count, pixel_count = _append_psprite_patch_commands(
            wad,
            weapon_patch_name,
            psp,
            "weapon",
            commands,
            sources,
        )
        weapon_patch_draws += 1
        weapon_posts += post_count
        weapon_pixels += pixel_count

    signature = world.movement.counters.accepted_moves
    for command in commands:
        signature = _hash_u32(signature, command.x)
        signature = _hash_u32(signature, command.yl)
        signature = _hash_u32(signature, command.yh)
        signature = _hash_u32(signature, 1 if command.tier == "weapon" else 0)
        signature = _hash_bytes(signature, command.patch_name.encode("ascii"))
        signature = _hash_bytes(signature, sources[command.source_index])

    return PatchDrawResult(
        commands=tuple(commands),
        column_sources=tuple(sources),
        status_patch_draws=status_patch_draws,
        weapon_patch_draws=weapon_patch_draws,
        status_columns=status_posts,
        weapon_columns=weapon_posts,
        status_pixels=status_pixels,
        weapon_pixels=weapon_pixels,
        first_status_patch="STBAR",
        first_weapon_patch=weapon_patch_name,
        weapon_state_name=weapon_state_name,
        weapon_sprite_name=weapon_sprite_name,
        signature=signature,
    )


def build_stage15_world(
    wad: WadFile,
    loaded: LoadedMap,
    ref14: stage14.Stage14GameLoopInputCollisionReference,
) -> Stage15World:
    info = parse_stage15_info_tables()
    doom = stage13.parse_source_info_tables()
    weaponinfo = build_weaponinfo_source_shape(info)
    movement = stage14.build_movement_world_for_stage13(wad, loaded, ref14.stage13)
    counters = Stage15Counters()
    player = p_spawn_player_inventory_psprite_source_shape(movement, info, weaponinfo, counters)
    sprite_by_mobj_index = {
        mobj.index: ref14.stage13.spawn.mobjs[mobj.index].sprite
        for mobj in movement.mobjs
        if mobj.index < len(ref14.stage13.spawn.mobjs)
    }
    return Stage15World(
        movement=movement,
        player=player,
        info=info,
        doom=doom,
        weaponinfo=weaponinfo,
        sprite_by_mobj_index=sprite_by_mobj_index,
        patch_by_sprite_frame=build_patch_frame_lookup(wad, info),
        counters=counters,
    )


def run_pickup_probes_source_shape(
    world: Stage15World,
    pickup_mapthing_indexes: Sequence[int] = DEFAULT_PICKUP_MAPTHING_INDEXES,
) -> tuple[PickupProbeRecord, ...]:
    records: list[PickupProbeRecord] = []
    player_mo = world.movement.mobjs[world.movement.player.mo_index]
    for _ in range(PRE_PICKUP_PSPRITE_TICS):
        p_move_psprites_source_shape(world.player, world.info, world.weaponinfo, world.counters)

    by_mapthing = {mobj.mapthing_index: mobj for mobj in world.movement.mobjs}
    for mapthing_index in pickup_mapthing_indexes:
        special = by_mapthing[mapthing_index]
        before_health = world.player.health
        before_armor = world.player.armorpoints
        assert world.player.ammo is not None
        before_clip = world.player.ammo[AM_CLIP]
        before_shell = world.player.ammo[AM_SHELL]
        before_weapon_count = _weapon_count(world.player)
        before_removed = len(world.removed_mobj_indexes or set())
        world.counters.pickup_probe_count += 1
        accepted_move = 1 if p_try_move_pickups_source_shape(world, player_mo, special.x, special.y) else 0
        sprite = world.sprite_by_mobj_index.get(special.index, -1)
        sprite_name = world.info.sprnames[sprite] if 0 <= sprite < len(world.info.sprnames) else ""
        block_x = stage14._block_coord(world.movement, special.x, world.movement.blockmap.origin_x)
        block_y = stage14._block_coord(world.movement, special.y, world.movement.blockmap.origin_y)
        records.append(
            PickupProbeRecord(
                mapthing_index=mapthing_index,
                mobj_index=special.index,
                type_name=special.type_name,
                sprite_name=sprite_name,
                x=special.x,
                y=special.y,
                block_x=block_x,
                block_y=block_y,
                accepted_move=accepted_move,
                removed=1 if len(world.removed_mobj_indexes or set()) > before_removed else 0,
                before_health=before_health,
                after_health=world.player.health,
                before_armor=before_armor,
                after_armor=world.player.armorpoints,
                before_clip=before_clip,
                after_clip=world.player.ammo[AM_CLIP],
                before_shell=before_shell,
                after_shell=world.player.ammo[AM_SHELL],
                before_weapon_count=before_weapon_count,
                after_weapon_count=_weapon_count(world.player),
                readyweapon_after=world.player.readyweapon,
                pendingweapon_after=world.player.pendingweapon,
            )
        )

    for _ in range(POST_PICKUP_PSPRITE_TICS):
        p_move_psprites_source_shape(world.player, world.info, world.weaponinfo, world.counters)
    st_ticker_compact_source_shape(world)
    return tuple(records)


def _stage15_signature(
    ref14: stage14.Stage14GameLoopInputCollisionReference,
    pickups: Sequence[PickupProbeRecord],
    player: Stage15Player,
    counters: Stage15Counters,
    draw: PatchDrawResult,
) -> int:
    signature = ref14.signature
    for pickup in pickups:
        for value in (
            pickup.mapthing_index,
            pickup.mobj_index,
            pickup.x,
            pickup.y,
            pickup.block_x,
            pickup.block_y,
            pickup.accepted_move,
            pickup.removed,
            pickup.after_health,
            pickup.after_armor,
            pickup.after_clip,
            pickup.after_shell,
            pickup.after_weapon_count,
            pickup.readyweapon_after,
            pickup.pendingweapon_after,
        ):
            signature = _hash_u32(signature, value)
        signature = _hash_bytes(signature, pickup.sprite_name.encode("ascii"))
    assert player.ammo is not None
    for value in (
        player.health,
        player.armorpoints,
        player.armortype,
        player.ammo[AM_CLIP],
        player.ammo[AM_SHELL],
        _weapon_count(player),
        player.readyweapon,
        player.pendingweapon,
        player.bonuscount,
        player.itemcount,
        counters.pickup_accepts,
        counters.pickup_rejections,
        counters.removed_specials,
        counters.ammo_grants,
        counters.weapon_grants,
        counters.armor_grants,
        counters.psprite_move_calls,
        counters.psprite_state_changes,
        draw.status_patch_draws,
        draw.weapon_patch_draws,
        draw.status_columns,
        draw.weapon_columns,
        draw.status_pixels,
        draw.weapon_pixels,
        draw.signature,
    ):
        signature = _hash_u32(signature, value)
    signature = _hash_bytes(signature, draw.first_weapon_patch.encode("ascii"))
    return signature


def _reference_stage15_uncached(wad_path: str) -> Stage15PickupsPspritesStatusbarReference:
    wad = WadFile.from_file(wad_path)
    loaded = load_map_from_file(wad_path, "MAP01")
    ref14 = stage14.reference_game_loop_input_collision_for_pinned_map(wad_path)
    world = build_stage15_world(wad, loaded, ref14)
    pickups = run_pickup_probes_source_shape(world)
    draw = build_status_psprite_patch_draw_source_shape(wad, world)
    signature = _stage15_signature(ref14, pickups, world.player, world.counters, draw)
    return Stage15PickupsPspritesStatusbarReference(
        stage14=ref14,
        pickups=pickups,
        player=replace(world.player),
        counters=replace(world.counters),
        draw=draw,
        pre_pickup_psprite_tics=PRE_PICKUP_PSPRITE_TICS,
        post_pickup_psprite_tics=POST_PICKUP_PSPRITE_TICS,
        signature=signature,
    )


@lru_cache(maxsize=4)
def _reference_stage15_cached(wad_path: str) -> Stage15PickupsPspritesStatusbarReference:
    return _reference_stage15_uncached(wad_path)


def reference_pickups_psprites_statusbar_shell_for_pinned_map(
    wad_path: str | Path,
) -> Stage15PickupsPspritesStatusbarReference:
    return _reference_stage15_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage15PickupsPspritesStatusbarReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_pickups_psprites_statusbar_shell_for_pinned_map(wad_path)


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


def emit_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.KERNEL32, "GetModuleHandleW")
    x86.mov_mem_abs32_eax(pe, "wc_hInstance")

    x86.push_abs32(pe, "window_class")
    x86.call_import(pe, stage01.USER32, "RegisterClassExW")
    x86.test_eax_eax(pe)
    x86.jne_rel32(pe, "class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")

    pe.label("class_registered")
    x86.call_rel32(pe, "source_stage15_load_wad_pickups_psprites_statusbar_shell")

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
    x86.jne_rel32(pe, "window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")

    pe.label("window_created")
    x86.mov_mem_abs32_eax(pe, "main_hwnd")
    x86.push_mem_abs32(pe, "status_title_ptr")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")

    pe.label("message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "GetMessageW")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "clean_exit")
    x86.cmp_eax_imm32(pe, 0xFFFFFFFF)
    x86.je_rel32(pe, "message_error")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "TranslateMessage")
    x86.push_abs32(pe, "message")
    x86.call_import(pe, stage01.USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "message_loop")

    pe.label("clean_exit")
    x86.push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")

    pe.label("message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, stage01.KERNEL32, "ExitProcess")


def emit_source_stage15_load_wad_pickups_psprites_statusbar_shell(pe: PE32) -> None:
    pe.label("source_stage15_load_wad_pickups_psprites_statusbar_shell")
    x86.mov_mem_abs32_imm32(pe, "map_loaded", 0)
    stage01.emit_set_status_ptrs(pe, "status_load_failed", "status_title_failed")

    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, stage01.FILE_ATTRIBUTE_NORMAL)
    x86.push_imm32(pe, stage01.OPEN_EXISTING)
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, stage01.FILE_SHARE_READ)
    x86.push_imm32(pe, stage01.GENERIC_READ)
    x86.push_abs32(pe, "wad_path_w")
    x86.call_import(pe, stage01.KERNEL32, "CreateFileW")
    x86.cmp_eax_imm32(pe, stage01.INVALID_HANDLE_VALUE)
    x86.jne_rel32(pe, "source_stage15_file_opened")
    stage01.emit_set_status_ptrs(pe, "status_open_failed", "status_title_failed")
    x86.ret(pe)

    pe.label("source_stage15_file_opened")
    x86.mov_mem_abs32_eax(pe, "wad_file_handle")
    x86.push_imm8(pe, 0)
    x86.push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.push_abs32(pe, "wad_header")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "ReadFile")
    x86.test_eax_eax(pe)
    x86.je_rel32(pe, "source_stage15_close_and_return")
    x86.mov_reg_mem_abs32(pe, "eax", "bytes_read")
    x86.cmp_eax_imm32(pe, stage01.WAD_HEADER_SIZE)
    x86.jne_rel32(pe, "source_stage15_close_and_return")

    x86.mov_reg_mem_abs32(pe, "eax", "wad_kind")
    x86.cmp_eax_imm32(pe, stage01.IWAD_MAGIC)
    x86.je_rel32(pe, "source_stage15_magic_ok")
    x86.cmp_eax_imm32(pe, stage01.PWAD_MAGIC)
    x86.jne_rel32(pe, "source_stage15_close_and_return")

    pe.label("source_stage15_magic_ok")
    x86.call_rel32(pe, "load_wad_directory")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage15_close_and_return")
    x86.call_rel32(pe, "render_init_texture_data_setup_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage15_close_and_return")
    x86.call_rel32(pe, "source_stage02_load_map")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage15_close_and_return")
    x86.call_rel32(pe, "source_stage06_run_live_seg_clip_debug")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "source_stage15_close_and_return")

    x86.call_rel32(pe, "render_composite_two_sided_wall_edges_debug")
    x86.call_rel32(pe, "render_visplanes_floor_ceiling_debug")
    x86.call_rel32(pe, "render_sky_and_masked_midtextures_debug")
    x86.call_rel32(pe, "render_things_sprites_real_frame_setup_debug")
    x86.call_rel32(pe, "render_game_loop_input_collision_debug")
    x86.call_rel32(pe, "render_pickups_psprites_statusbar_shell_debug")
    x86.call_rel32(pe, "build_success_status")
    x86.call_rel32(pe, "append_stage13_success_status")
    x86.call_rel32(pe, "append_stage14_success_status")
    x86.call_rel32(pe, "append_stage15_success_status")

    pe.label("source_stage15_close_and_return")
    x86.push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, stage01.KERNEL32, "CloseHandle")
    x86.ret(pe)


def emit_render_pickups_psprites_statusbar_shell_debug(pe: PE32) -> None:
    pe.label("G_PlayerReborn_inventory_source_shape_debug")
    pe.label("P_SpawnPlayer_inventory_psprite_source_shape_debug")
    pe.label("PIT_CheckThing_special_touch_source_shape_debug")
    pe.label("P_TouchSpecialThing_inventory_source_shape_debug")
    pe.label("P_GiveInventory_source_shape_debug")
    pe.label("weaponinfo_psprite_source_shape_debug")
    pe.label("P_Psprites_source_shape_debug")
    pe.label("ST_StatusWidget_source_shape_debug")
    pe.label("ST_StatusLibWidget_source_shape_debug")
    pe.label("V_DrawPatch_status_psprite_source_shape_debug")
    pe.label("R_DrawPSprite_ready_weapon_shell_debug")
    pe.label("render_pickups_psprites_statusbar_shell_debug")

    x86.mov_mem_abs32_imm32(pe, "stage15_status_columns_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage15_weapon_columns_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage15_status_pixels_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage15_weapon_pixels_drawn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage15_pixels_drawn", 0)
    x86.mov_reg_mem_abs32(pe, "eax", "stage13_pixel_signature")
    x86.mov_mem_abs32_eax(pe, "stage15_runtime_pixel_signature")
    x86.mov_mem_abs32_abs32(pe, "dc_colormap", "stage15_palette32")

    stage12._emit_column_command_loop(
        pe,
        command_label="stage15_status_commands",
        count_label="stage15_status_command_count",
        scan_label="stage15_status_scan_ptr",
        remaining_label="stage15_status_remaining_commands",
        loop_label="stage15_status_command_loop",
        done_label="stage15_status_commands_done",
        column_counter_label="stage15_status_columns_drawn",
        draw_func_label="render_draw_stage15_status_column_debug",
    )
    stage12._emit_column_command_loop(
        pe,
        command_label="stage15_weapon_commands",
        count_label="stage15_weapon_command_count",
        scan_label="stage15_weapon_scan_ptr",
        remaining_label="stage15_weapon_remaining_commands",
        loop_label="stage15_weapon_command_loop",
        done_label="stage15_weapon_commands_done",
        column_counter_label="stage15_weapon_columns_drawn",
        draw_func_label="render_draw_stage15_weapon_column_debug",
    )

    x86.mov_reg_mem_abs32(pe, "eax", "stage15_expected_signature")
    x86.mov_mem_abs32_eax(pe, "stage15_runtime_signature")
    x86.ret(pe)


def _emit_render_draw_stage15_column_debug(pe: PE32, *, label: str, pixel_counter: str) -> None:
    pe.label(label)
    x86.push_reg(pe, "ebx")
    x86.push_reg(pe, "ecx")
    x86.push_reg(pe, "edx")
    x86.push_reg(pe, "esi")
    x86.push_reg(pe, "edi")

    x86.mov_reg_mem_abs32(pe, "eax", "dc_yh")
    x86.sub_reg_mem_abs32(pe, "eax", "dc_yl")
    x86.jl_rel32(pe, f"{label}_done")
    x86.inc_reg(pe, "eax")
    x86.mov_mem_abs32_eax(pe, "stage15_column_remaining")

    x86.mov_reg_mem_abs32(pe, "ebx", "dc_yl")
    x86.mov_reg_reg(pe, "edx", "ebx")
    x86.shl_reg_imm8(pe, "ebx", 8)
    x86.shl_reg_imm8(pe, "edx", 6)
    x86.add_reg_reg(pe, "ebx", "edx")
    x86.add_reg_mem_abs32(pe, "ebx", "dc_x")
    x86.shl_reg_imm8(pe, "ebx", 2)
    x86.mov_reg_abs32(pe, "edi", "framebuffer")
    x86.add_reg_reg(pe, "edi", "ebx")

    x86.mov_reg_mem_abs32(pe, "eax", "dc_yl")
    x86.add_reg_imm32(pe, "eax", -CENTER_Y)
    x86.mov_reg_mem_abs32(pe, "ecx", "dc_iscale")
    x86.imul_reg(pe, "ecx")
    x86.add_reg_mem_abs32(pe, "eax", "dc_texturemid")
    x86.mov_mem_abs32_eax(pe, "dc_frac")

    pe.label(f"{label}_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "dc_frac")
    x86.sar_reg_imm8(pe, "eax", FRACBITS)
    x86.and_reg_imm32(pe, "eax", WALL_COLUMN_SOURCE_HEIGHT - 1)
    x86.mov_reg_mem_abs32(pe, "esi", "dc_source")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.movzx_reg_byte_ptr_reg(pe, "eax", "esi")
    x86.shl_reg_imm8(pe, "eax", 2)
    x86.mov_reg_mem_abs32(pe, "esi", "dc_colormap")
    x86.add_reg_reg(pe, "esi", "eax")
    x86.mov_reg_ptr_reg(pe, "eax", "esi")
    x86.mov_ptr_reg_eax(pe, "edi")

    x86.mov_reg_mem_abs32(pe, "ecx", "stage15_runtime_pixel_signature")
    x86.imul_reg_reg_imm32(pe, "ecx", "ecx", FNV_PRIME)
    x86.xor_reg_reg(pe, "ecx", "eax")
    x86.mov_mem_abs32_reg(pe, "stage15_runtime_pixel_signature", "ecx")
    stage07._emit_inc_abs32(pe, "stage15_pixels_drawn")
    stage07._emit_inc_abs32(pe, pixel_counter)

    x86.add_reg_imm32(pe, "edi", FRAMEBUFFER_WIDTH * 4)
    x86.mov_reg_mem_abs32(pe, "eax", "dc_frac")
    x86.add_reg_mem_abs32(pe, "eax", "dc_iscale")
    x86.mov_mem_abs32_eax(pe, "dc_frac")
    x86.dec_mem_abs32(pe, "stage15_column_remaining")
    x86.jne_rel32(pe, f"{label}_loop")

    pe.label(f"{label}_done")
    x86.pop_reg(pe, "edi")
    x86.pop_reg(pe, "esi")
    x86.pop_reg(pe, "edx")
    x86.pop_reg(pe, "ecx")
    x86.pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_render_draw_stage15_columns_debug(pe: PE32) -> None:
    _emit_render_draw_stage15_column_debug(
        pe,
        label="render_draw_stage15_status_column_debug",
        pixel_counter="stage15_status_pixels_drawn",
    )
    _emit_render_draw_stage15_column_debug(
        pe,
        label="render_draw_stage15_weapon_column_debug",
        pixel_counter="stage15_weapon_pixels_drawn",
    )


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage14._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage15_success_status(pe: PE32) -> None:
    pe.label("append_stage15_success_status")

    _emit_seek_buffer_end(pe, "status_success_buffer", "stage15_status")
    stage01.append_c_string_label(pe, "status_stage15_success_header")
    stage01.append_u32_label(pe, "status_stage15_pickups_prefix", "stage15_pickup_accepts")
    stage01.append_u32_label(pe, "status_stage15_weapon_prefix", "stage15_readyweapon")
    stage01.append_u32_label(pe, "status_stage15_status_pixels_prefix", "stage15_status_pixels_drawn")
    stage01.append_u32_label(pe, "status_stage15_weapon_pixels_prefix", "stage15_weapon_pixels_drawn")
    stage01.append_u32_label(pe, "status_stage15_signature_prefix", "stage15_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage15_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage15_title")
    stage01.append_u32_label(pe, "title_stage15_probe_count_prefix", "stage15_pickup_probe_count")
    stage01.append_u32_label(pe, "title_stage15_pickup_accept_prefix", "stage15_pickup_accepts")
    stage01.append_u32_label(pe, "title_stage15_removed_prefix", "stage15_removed_specials")
    stage01.append_u32_label(pe, "title_stage15_first_pickup_prefix", "stage15_first_pickup_mapthing")
    stage01.append_c_string_label(pe, "title_stage15_first_sprite_prefix")
    stage01.append_c_string_label(pe, "stage15_first_pickup_sprite_name")
    stage01.append_u32_label(pe, "title_stage15_second_pickup_prefix", "stage15_second_pickup_mapthing")
    stage01.append_c_string_label(pe, "title_stage15_second_sprite_prefix")
    stage01.append_c_string_label(pe, "stage15_second_pickup_sprite_name")
    stage01.append_u32_label(pe, "title_stage15_health_prefix", "stage15_health")
    stage01.append_u32_label(pe, "title_stage15_armor_prefix", "stage15_armorpoints")
    stage01.append_u32_label(pe, "title_stage15_armortype_prefix", "stage15_armortype")
    stage01.append_u32_label(pe, "title_stage15_clip_prefix", "stage15_ammo_clip")
    stage01.append_u32_label(pe, "title_stage15_shell_prefix", "stage15_ammo_shell")
    stage01.append_u32_label(pe, "title_stage15_weapon_count_prefix", "stage15_weapon_count")
    stage01.append_u32_label(pe, "title_stage15_ready_prefix", "stage15_readyweapon")
    stage01.append_u32_label(pe, "title_stage15_pending_prefix", "stage15_pendingweapon")
    stage01.append_u32_label(pe, "title_stage15_psprite_state_prefix", "stage15_psprite_state")
    stage01.append_c_string_label(pe, "title_stage15_psprite_name_prefix")
    stage01.append_c_string_label(pe, "stage15_psprite_state_name")
    stage01.append_u32_label(pe, "title_stage15_psprite_tics_prefix", "stage15_psprite_tics")
    stage01.append_u32_label(pe, "title_stage15_status_patch_prefix", "stage15_status_patch_draws")
    stage01.append_u32_label(pe, "title_stage15_status_columns_prefix", "stage15_status_columns_drawn")
    stage01.append_u32_label(pe, "title_stage15_status_pixels_prefix", "stage15_status_pixels_drawn")
    stage01.append_c_string_label(pe, "title_stage15_weapon_patch_name_prefix")
    stage01.append_c_string_label(pe, "stage15_weapon_patch_name")
    stage01.append_u32_label(pe, "title_stage15_weapon_columns_prefix", "stage15_weapon_columns_drawn")
    stage01.append_u32_label(pe, "title_stage15_weapon_pixels_prefix", "stage15_weapon_pixels_drawn")
    stage01.append_u32_label(pe, "title_stage15_messages_prefix", "stage15_message_deferred")
    stage01.append_u32_label(pe, "title_stage15_sounds_prefix", "stage15_sound_deferred")
    stage01.append_u32_label(pe, "title_stage15_signature_prefix", "stage15_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def _emit_stage15_column_commands(pe: PE32, commands: Sequence[PatchDrawCommand], tier: str) -> None:
    for command in commands:
        if command.tier != tier:
            continue
        pe.emit_u32(command.x)
        pe.emit_u32(command.yl)
        pe.emit_u32(command.yh)
        pe.emit_u32(command.iscale)
        pe.emit_u32(command.texturemid)
        pe.write_abs32(f"stage15_column_source_{command.source_index}")


def _emit_u32_table(pe: PE32, label: str, values: Sequence[int]) -> None:
    pe.label(label)
    for value in values:
        pe.emit_u32(value & 0xFFFFFFFF)


def emit_stage15_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    first = ref.pickups[0] if ref is not None and ref.pickups else None
    second = ref.pickups[1] if ref is not None and len(ref.pickups) > 1 else None
    psp = ref.player.psprites[PS_WEAPON] if ref is not None and ref.player.psprites is not None else PspDef()

    pe.align_section(4)
    pe.label("stage15_pickup_probe_count")
    pe.emit_u32(ref.counters.pickup_probe_count if ref is not None else 0)
    pe.label("stage15_pickup_attempts")
    pe.emit_u32(ref.counters.pickup_attempts if ref is not None else 0)
    pe.label("stage15_pickup_accepts")
    pe.emit_u32(ref.counters.pickup_accepts if ref is not None else 0)
    pe.label("stage15_pickup_rejections")
    pe.emit_u32(ref.counters.pickup_rejections if ref is not None else 0)
    pe.label("stage15_removed_specials")
    pe.emit_u32(ref.counters.removed_specials if ref is not None else 0)
    pe.label("stage15_unsupported_specials")
    pe.emit_u32(ref.counters.unsupported_specials if ref is not None else 0)
    pe.label("stage15_message_deferred")
    pe.emit_u32(ref.counters.message_deferred if ref is not None else 0)
    pe.label("stage15_sound_deferred")
    pe.emit_u32(ref.counters.sound_deferred if ref is not None else 0)
    pe.label("stage15_item_respawn_deferred")
    pe.emit_u32(ref.counters.item_respawn_deferred if ref is not None else 0)
    pe.label("stage15_ammo_grants")
    pe.emit_u32(ref.counters.ammo_grants if ref is not None else 0)
    pe.label("stage15_weapon_grants")
    pe.emit_u32(ref.counters.weapon_grants if ref is not None else 0)
    pe.label("stage15_armor_grants")
    pe.emit_u32(ref.counters.armor_grants if ref is not None else 0)

    pe.label("stage15_first_pickup_mapthing")
    pe.emit_u32(first.mapthing_index if first is not None else 0)
    pe.label("stage15_first_pickup_mobj")
    pe.emit_u32(first.mobj_index if first is not None else 0)
    pe.label("stage15_first_pickup_x")
    pe.emit_u32((first.x >> FRACBITS if first is not None else 0) & 0xFFFFFFFF)
    pe.label("stage15_first_pickup_y")
    pe.emit_u32((first.y >> FRACBITS if first is not None else 0) & 0xFFFFFFFF)
    pe.label("stage15_first_pickup_block_x")
    pe.emit_u32(first.block_x if first is not None else 0)
    pe.label("stage15_first_pickup_block_y")
    pe.emit_u32(first.block_y if first is not None else 0)
    pe.label("stage15_second_pickup_mapthing")
    pe.emit_u32(second.mapthing_index if second is not None else 0)
    pe.label("stage15_second_pickup_mobj")
    pe.emit_u32(second.mobj_index if second is not None else 0)
    pe.label("stage15_second_pickup_x")
    pe.emit_u32((second.x >> FRACBITS if second is not None else 0) & 0xFFFFFFFF)
    pe.label("stage15_second_pickup_y")
    pe.emit_u32((second.y >> FRACBITS if second is not None else 0) & 0xFFFFFFFF)
    pe.label("stage15_second_pickup_block_x")
    pe.emit_u32(second.block_x if second is not None else 0)
    pe.label("stage15_second_pickup_block_y")
    pe.emit_u32(second.block_y if second is not None else 0)

    pe.label("stage15_health")
    pe.emit_u32(ref.player.health if ref is not None else 0)
    pe.label("stage15_mo_health")
    pe.emit_u32(ref.player.mo_health if ref is not None else 0)
    pe.label("stage15_armorpoints")
    pe.emit_u32(ref.player.armorpoints if ref is not None else 0)
    pe.label("stage15_armortype")
    pe.emit_u32(ref.player.armortype if ref is not None else 0)
    pe.label("stage15_ammo_clip")
    pe.emit_u32(ref.player.ammo[AM_CLIP] if ref is not None and ref.player.ammo is not None else 0)
    pe.label("stage15_ammo_shell")
    pe.emit_u32(ref.player.ammo[AM_SHELL] if ref is not None and ref.player.ammo is not None else 0)
    pe.label("stage15_weapon_count")
    pe.emit_u32(_weapon_count(ref.player) if ref is not None else 0)
    pe.label("stage15_readyweapon")
    pe.emit_u32(ref.player.readyweapon if ref is not None else 0)
    pe.label("stage15_pendingweapon")
    pe.emit_u32(ref.player.pendingweapon if ref is not None else 0)
    pe.label("stage15_bonuscount")
    pe.emit_u32(ref.player.bonuscount if ref is not None else 0)
    pe.label("stage15_itemcount")
    pe.emit_u32(ref.player.itemcount if ref is not None else 0)

    pe.label("stage15_pre_pickup_psprite_tics")
    pe.emit_u32(ref.pre_pickup_psprite_tics if ref is not None else 0)
    pe.label("stage15_post_pickup_psprite_tics")
    pe.emit_u32(ref.post_pickup_psprite_tics if ref is not None else 0)
    pe.label("stage15_psprite_setup_calls")
    pe.emit_u32(ref.counters.psprite_setup_calls if ref is not None else 0)
    pe.label("stage15_psprite_move_calls")
    pe.emit_u32(ref.counters.psprite_move_calls if ref is not None else 0)
    pe.label("stage15_psprite_state_changes")
    pe.emit_u32(ref.counters.psprite_state_changes if ref is not None else 0)
    pe.label("stage15_psprite_state")
    pe.emit_u32(psp.state if psp.state is not None else 0)
    pe.label("stage15_psprite_tics")
    pe.emit_u32(psp.tics)
    pe.label("stage15_psprite_sx")
    pe.emit_u32(psp.sx & 0xFFFFFFFF)
    pe.label("stage15_psprite_sy")
    pe.emit_u32(psp.sy & 0xFFFFFFFF)

    pe.label("stage15_status_patch_draws")
    pe.emit_u32(ref.draw.status_patch_draws if ref is not None else 0)
    pe.label("stage15_weapon_patch_draws")
    pe.emit_u32(ref.draw.weapon_patch_draws if ref is not None else 0)
    pe.label("stage15_expected_status_columns")
    pe.emit_u32(ref.draw.status_columns if ref is not None else 0)
    pe.label("stage15_expected_weapon_columns")
    pe.emit_u32(ref.draw.weapon_columns if ref is not None else 0)
    pe.label("stage15_expected_status_pixels")
    pe.emit_u32(ref.draw.status_pixels if ref is not None else 0)
    pe.label("stage15_expected_weapon_pixels")
    pe.emit_u32(ref.draw.weapon_pixels if ref is not None else 0)
    pe.label("stage15_status_command_count")
    pe.emit_u32(sum(1 for command in ref.draw.commands if command.tier == "status") if ref is not None else 0)
    pe.label("stage15_weapon_command_count")
    pe.emit_u32(sum(1 for command in ref.draw.commands if command.tier == "weapon") if ref is not None else 0)

    pe.label("stage15_status_columns_drawn")
    pe.emit_u32(0)
    pe.label("stage15_weapon_columns_drawn")
    pe.emit_u32(0)
    pe.label("stage15_status_pixels_drawn")
    pe.emit_u32(0)
    pe.label("stage15_weapon_pixels_drawn")
    pe.emit_u32(0)
    pe.label("stage15_pixels_drawn")
    pe.emit_u32(0)
    pe.label("stage15_runtime_pixel_signature")
    pe.emit_u32(0)
    pe.label("stage15_status_scan_ptr")
    pe.emit_u32(0)
    pe.label("stage15_weapon_scan_ptr")
    pe.emit_u32(0)
    pe.label("stage15_status_remaining_commands")
    pe.emit_u32(0)
    pe.label("stage15_weapon_remaining_commands")
    pe.emit_u32(0)
    pe.label("stage15_column_remaining")
    pe.emit_u32(0)
    pe.label("stage15_expected_signature")
    pe.emit_u32(ref.signature if ref is not None else 0)
    pe.label("stage15_runtime_signature")
    pe.emit_u32(0)

    _emit_u32_table(pe, "stage15_palette32", list(ref.stage14.stage13.stage12.palette32) if ref is not None else [0] * 256)

    pe.align_section(4)
    pe.label("stage15_status_commands")
    if ref is not None:
        _emit_stage15_column_commands(pe, ref.draw.commands, "status")
    pe.label("stage15_weapon_commands")
    if ref is not None:
        _emit_stage15_column_commands(pe, ref.draw.commands, "weapon")

    pe.align_section(1)
    if ref is not None:
        for index, source in enumerate(ref.draw.column_sources):
            pe.label(f"stage15_column_source_{index}")
            pe.emit(source)

    pe.align_section(1)
    pe.label("stage15_first_pickup_sprite_name")
    x86.emit_asciiz(pe, first.sprite_name if first is not None else "")
    pe.label("stage15_second_pickup_sprite_name")
    x86.emit_asciiz(pe, second.sprite_name if second is not None else "")
    pe.label("stage15_psprite_state_name")
    x86.emit_asciiz(pe, ref.draw.weapon_state_name if ref is not None else "")
    pe.label("stage15_weapon_patch_name")
    x86.emit_asciiz(pe, ref.draw.first_weapon_patch if ref is not None else "")

    pe.label("status_stage15_success_header")
    x86.emit_asciiz(
        pe,
        "\r\nsource_stage15_pickups_psprites_statusbar_shell\r\n"
        "Pickups, psprites, and real-patch status shell OK\r\n",
    )
    pe.label("status_stage15_pickups_prefix")
    x86.emit_asciiz(pe, "\r\nAccepted pickup touches: ")
    pe.label("status_stage15_weapon_prefix")
    x86.emit_asciiz(pe, "\r\nReady weapon after psprite movement: ")
    pe.label("status_stage15_status_pixels_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime status patch pixels: ")
    pe.label("status_stage15_weapon_pixels_prefix")
    x86.emit_asciiz(pe, "\r\nRuntime weapon patch pixels: ")
    pe.label("status_stage15_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage15 pickup/status signature: ")
    pe.label("status_stage15_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage15 keeps the released stage14 movement/collision proof, then "
        "runs separate fixed MAP01 pickup probes through PIT_CheckThing and "
        "P_TouchSpecialThing. Inventory mutates through P_GiveWeapon, "
        "P_GiveAmmo, and P_GiveArmor. P_SetupPsprites/P_MovePsprites advance "
        "the ready weapon without firing. A compact status strip and ready "
        "weapon shell draw real WAD patches through V_DrawPatch and "
        "R_DrawPSprite-shaped column paths. Wider game systems remain "
        "outside this release.\r\n",
    )

    pe.label("title_stage15_probe_count_prefix")
    x86.emit_asciiz(pe, " PPROBE=")
    pe.label("title_stage15_pickup_accept_prefix")
    x86.emit_asciiz(pe, " PACC=")
    pe.label("title_stage15_removed_prefix")
    x86.emit_asciiz(pe, " PREM=")
    pe.label("title_stage15_first_pickup_prefix")
    x86.emit_asciiz(pe, " P1=")
    pe.label("title_stage15_first_sprite_prefix")
    x86.emit_asciiz(pe, " P1N=")
    pe.label("title_stage15_second_pickup_prefix")
    x86.emit_asciiz(pe, " P2=")
    pe.label("title_stage15_second_sprite_prefix")
    x86.emit_asciiz(pe, " P2N=")
    pe.label("title_stage15_health_prefix")
    x86.emit_asciiz(pe, " HP=")
    pe.label("title_stage15_armor_prefix")
    x86.emit_asciiz(pe, " ARM=")
    pe.label("title_stage15_armortype_prefix")
    x86.emit_asciiz(pe, " AT=")
    pe.label("title_stage15_clip_prefix")
    x86.emit_asciiz(pe, " CLIP=")
    pe.label("title_stage15_shell_prefix")
    x86.emit_asciiz(pe, " SHELL=")
    pe.label("title_stage15_weapon_count_prefix")
    x86.emit_asciiz(pe, " WOWN=")
    pe.label("title_stage15_ready_prefix")
    x86.emit_asciiz(pe, " RDY=")
    pe.label("title_stage15_pending_prefix")
    x86.emit_asciiz(pe, " PEND=")
    pe.label("title_stage15_psprite_state_prefix")
    x86.emit_asciiz(pe, " PSPST=")
    pe.label("title_stage15_psprite_name_prefix")
    x86.emit_asciiz(pe, " PSPN=")
    pe.label("title_stage15_psprite_tics_prefix")
    x86.emit_asciiz(pe, " PSPT=")
    pe.label("title_stage15_status_patch_prefix")
    x86.emit_asciiz(pe, " STP=")
    pe.label("title_stage15_status_columns_prefix")
    x86.emit_asciiz(pe, " STCOL=")
    pe.label("title_stage15_status_pixels_prefix")
    x86.emit_asciiz(pe, " STPIX=")
    pe.label("title_stage15_weapon_patch_name_prefix")
    x86.emit_asciiz(pe, " WPN=")
    pe.label("title_stage15_weapon_columns_prefix")
    x86.emit_asciiz(pe, " WPCOL=")
    pe.label("title_stage15_weapon_pixels_prefix")
    x86.emit_asciiz(pe, " WPPIX=")
    pe.label("title_stage15_messages_prefix")
    x86.emit_asciiz(pe, " MDEF=")
    pe.label("title_stage15_sounds_prefix")
    x86.emit_asciiz(pe, " SNDDEF=")
    pe.label("title_stage15_signature_prefix")
    x86.emit_asciiz(pe, " S15SIG=")


def build_source_stage15_pickups_psprites_statusbar_shell_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_entry(pe)
    stage03.emit_wndproc_framebuffer(pe)
    emit_source_stage15_load_wad_pickups_psprites_statusbar_shell(pe)
    stage08.emit_render_init_texture_data_setup_debug(pe)
    stage01.emit_load_wad_directory(pe)
    stage01.emit_wad_num_lumps(pe)
    stage01.emit_wad_check_num_for_name(pe)
    stage01.emit_wad_get_num_for_name(pe)
    stage01.emit_wad_lump_length(pe)
    stage01.emit_wad_read_lump(pe)
    stage02.emit_source_stage02_load_map(pe)
    stage01.emit_map_load_vertexes(pe)
    stage01.emit_map_load_sectors(pe)
    stage01.emit_map_load_sidedefs(pe)
    stage01.emit_map_load_linedefs(pe)
    stage02.emit_map_load_subsectors(pe)
    stage02.emit_map_load_nodes(pe)
    stage02.emit_map_load_segs(pe)
    stage02.emit_map_group_lines(pe)
    stage02.emit_group_count_sector_ref(pe)
    stage02.emit_group_append_sector_line(pe)
    stage07.emit_source_stage06_run_live_seg_clip_debug(pe)
    stage03.emit_render_fixed_mul(pe)
    stage03.emit_render_point_on_side(pe)
    stage03.emit_render_point_in_subsector(pe)
    stage03.emit_render_debug_subsector(pe)
    stage03.emit_render_check_bbox_accept_all(pe)
    stage03.emit_render_bsp_node_debug(pe)
    stage04.emit_render_slope_div(pe)
    stage04.emit_render_point_to_angle(pe)
    stage04.emit_render_clear_clipsegs(pe)
    stage04.emit_render_check_bbox(pe)
    stage04.emit_render_debug_subsector_bbox(pe)
    stage04.emit_render_bsp_node_bbox_debug(pe)
    stage07.emit_render_angle_to_view_x_debug(pe)
    stage07.emit_render_setup_frame_debug(pe)
    stage07.emit_render_fixed_div(pe)
    stage07.emit_render_point_to_dist(pe)
    stage07.emit_render_scale_from_global_angle(pe)
    stage07.emit_render_store_wall_range_debug(pe)
    stage07.emit_render_clip_solid_wall_segment(pe)
    stage07.emit_render_clip_pass_wall_segment(pe)
    stage08.emit_render_add_line_debug(pe)
    stage07.emit_render_debug_subsector_clip(pe)
    stage07.emit_render_bsp_node_clip_debug(pe)
    stage07.emit_render_finish_clip_debug(pe)
    stage04.emit_render_debug_framebuffer(pe)
    stage03.emit_clear_framebuffer(pe)
    stage03.emit_render_error_pattern(pe)
    stage03.emit_transform_point_to_screen(pe)
    stage03.emit_draw_all_linedefs(pe)
    stage03.emit_draw_visited_segs(pe)
    stage04.emit_draw_bbox_visible_segs(pe)
    stage03.emit_draw_viewpoint_marker(pe)
    stage03.emit_draw_line(pe)
    stage03.emit_plot_pixel(pe)
    stage10.emit_render_composite_two_sided_wall_edges_debug(pe)
    stage10.emit_render_draw_column_debug(pe)
    stage11.emit_render_visplanes_floor_ceiling_debug(pe)
    stage11.emit_render_draw_span_debug(pe)
    stage12.emit_render_sky_and_masked_midtextures_debug(pe)
    stage12.emit_render_draw_stage12_columns_debug(pe)
    stage13.emit_render_things_sprites_and_real_frame_setup_debug(pe)
    stage13.emit_render_draw_stage13_sprite_column_debug(pe)
    stage14.emit_render_game_loop_input_collision_debug(pe)
    emit_render_pickups_psprites_statusbar_shell_debug(pe)
    emit_render_draw_stage15_columns_debug(pe)
    stage12.emit_build_success_status(pe)
    stage13.emit_append_stage13_success_status(pe)
    stage14.emit_append_stage14_success_status(pe)
    emit_append_stage15_success_status(pe)
    stage01.emit_append_c_string(pe)
    stage01.emit_append_u32_decimal(pe)
    stage01.emit_append_i32_decimal(pe)
    with patched_stage01_window_labels():
        stage01.emit_data(pe)
    stage02.emit_stage02_data(pe)
    stage04.emit_stage04_data(pe)
    stage07.emit_stage07_data(pe)
    stage08.emit_stage08_data(pe)
    stage10.emit_stage10_data(pe)
    stage11.emit_stage11_data(pe)
    stage12.emit_stage12_data(pe)
    stage13.emit_stage13_data(pe)
    stage14.emit_stage14_data(pe)
    emit_stage15_data(pe)
    return pe.build("entry")


def write_source_stage15_pickups_psprites_statusbar_shell_exe(path: str | Path) -> bytes:
    image = build_source_stage15_pickups_psprites_statusbar_shell_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage15 pickup/psprite/status PE32 debug executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage15_pickups_psprites_statusbar_shell.exe",
        help="path to write, default: build/source_stage15_pickups_psprites_statusbar_shell.exe",
    )
    args = parser.parse_args()
    write_source_stage15_pickups_psprites_statusbar_shell_exe(args.output)


if __name__ == "__main__":
    main()
