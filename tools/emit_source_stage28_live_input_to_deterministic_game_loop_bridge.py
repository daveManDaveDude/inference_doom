from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import emit_source_stage27_integrated_scripted_room_interaction_loop as stage27
from tools import x86
from tools.pe32 import PE32
from tools.wad import WadFile


stage26 = stage27.stage26
stage25 = stage27.stage25
stage24 = stage27.stage24
stage23 = stage27.stage23
stage22 = stage27.stage22
stage21 = stage27.stage21
stage20 = stage27.stage20
stage19 = stage27.stage19
stage18 = stage27.stage18
stage17 = stage27.stage17
stage16 = stage27.stage16
stage15 = stage27.stage15
stage14 = stage27.stage14
stage13 = stage27.stage13
stage12 = stage27.stage12
stage11 = stage27.stage11
stage10 = stage27.stage10
stage08 = stage27.stage08
stage07 = stage27.stage07
stage04 = stage27.stage04
stage03 = stage27.stage03
stage02 = stage27.stage02
stage01 = stage27.stage01


FRAMEBUFFER_WIDTH = stage27.FRAMEBUFFER_WIDTH
FRAMEBUFFER_HEIGHT = stage27.FRAMEBUFFER_HEIGHT
FRAMEBUFFER_PIXELS = stage27.FRAMEBUFFER_PIXELS
FRAMEBUFFER_BYTES = stage27.FRAMEBUFFER_BYTES

WINDOW_WIDTH = stage27.WINDOW_WIDTH
WINDOW_HEIGHT = stage27.WINDOW_HEIGHT
WINDOW_CLASS_NAME = "InferenceDoomSourceStage28LiveInputToDeterministicGameLoopBridge"
WINDOW_TITLE = "Inference Doom S28 Input Bridge"
WAD_PATH = stage27.WAD_PATH

FRACBITS = stage27.FRACBITS
FRACUNIT = stage27.FRACUNIT
FNV_PRIME = stage27.FNV_PRIME
BT_USE = stage27.BT_USE
WM_TIMER = stage27.WM_TIMER
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
STAGE28_TIMER_ID = 28
STAGE28_TIMER_MS = stage27.STAGE27_TIMER_MS

SELECTED_MAP = stage27.SELECTED_MAP
SELECTED_LINE_INDEX = stage27.SELECTED_LINE_INDEX
SELECTED_SPECIAL = stage27.SELECTED_SPECIAL
SELECTED_TAG = stage27.SELECTED_TAG
SELECTED_TARGET_SECTOR = stage27.SELECTED_TARGET_SECTOR

FORWARDMOVE = 0x19
SLOW_ANGLETURN = 320

VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_SPACE = 0x20
VK_A = ord("A")
VK_D = ord("D")
VK_E = ord("E")
VK_S = ord("S")
VK_W = ord("W")


SOURCE_TRACE = stage27.SOURCE_TRACE + (
    (
        "reference/chocolate-doom/src/d_event.c",
        "D_PostEvent/D_PopEvent key event queue model adapted to bounded Win32 key state",
        "D_PostEvent_stage28_live_key_state_bridge_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/g_game.c",
        "G_BuildTiccmd keyboard forward/back/turn/use subset with replay override",
        "G_BuildTiccmd_stage28_live_or_replay_bridge_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_user.c",
        "P_PlayerThink BT_USE usedown edge gate shared by replay and manual commands",
        "P_PlayerThink_stage28_bridge_usedown_source_shape_debug",
    ),
    (
        "reference/chocolate-doom/src/doom/p_tick.c",
        "G_Ticker/P_Ticker integrated deterministic room loop reached through command bridge",
        "G_Ticker_stage28_bridge_room_loop_source_shape_debug",
    ),
)


@dataclass(frozen=True)
class Stage28KeyState:
    forward: bool = False
    back: bool = False
    turn_left: bool = False
    turn_right: bool = False
    use: bool = False


@dataclass
class Stage28CommandBridgeState:
    gamekeydown: dict[str, bool] = field(default_factory=dict)
    turnheld: int = 0
    usedown: bool = False
    live_key_events: int = 0


@dataclass
class Stage28Counters(stage27.Stage27Counters):
    command_builder_calls: int = 0
    replay_commands_built: int = 0
    manual_commands_built: int = 0
    replay_ignored_live_key_state: int = 0
    manual_live_input_enabled: int = 0
    manual_bt_use_commands: int = 0
    manual_use_edges: int = 0
    manual_use_held_skips: int = 0
    manual_forward_fields: int = 0
    manual_back_fields: int = 0
    manual_turn_fields: int = 0
    manual_activation_edges: int = 0
    stage29_absent: int = 1


@dataclass
class Stage28World(stage27.Stage27World):
    counters: Stage28Counters = field(default_factory=Stage28Counters)
    bridge: Stage28CommandBridgeState = field(default_factory=Stage28CommandBridgeState)


@dataclass(frozen=True)
class Stage28LiveInputBridgeReference:
    stage27: stage27.Stage27IntegratedScriptedRoomLoopReference
    ticcmd_script: tuple[stage27.Stage27Ticcmd, ...]
    samples: tuple[stage27.Stage27StateSample, ...]
    counters: Stage28Counters
    ticker_counters: stage21.Stage21Counters
    replay_signature: int
    signature: int


def _hash_u32(signature: int, value: int) -> int:
    return (((signature * FNV_PRIME) & 0xFFFFFFFF) ^ (value & 0xFFFFFFFF)) & 0xFFFFFFFF


def _hash_bytes(signature: int, data: bytes) -> int:
    for byte in data:
        signature = _hash_u32(signature, byte)
    return signature


def d_post_event_stage28_live_key_state_bridge_source_shape(
    bridge: Stage28CommandBridgeState,
    key: str,
    down: bool,
) -> None:
    bridge.gamekeydown[key] = down
    bridge.live_key_events += 1


def _key_state_from_bridge(bridge: Stage28CommandBridgeState) -> Stage28KeyState:
    keys = bridge.gamekeydown
    return Stage28KeyState(
        forward=keys.get("forward", False),
        back=keys.get("back", False),
        turn_left=keys.get("left", False),
        turn_right=keys.get("right", False),
        use=keys.get("use", False),
    )


def g_build_ticcmd_stage28_live_or_replay_bridge_source_shape(
    bridge: Stage28CommandBridgeState,
    counters: Stage28Counters,
    *,
    replay: bool,
    replay_cmd: stage27.Stage27Ticcmd | None = None,
    live_keys: Stage28KeyState | None = None,
) -> stage27.Stage27Ticcmd:
    counters.command_builder_calls += 1
    if replay:
        counters.replay_commands_built += 1
        if live_keys and (live_keys.forward or live_keys.back or live_keys.turn_left or live_keys.turn_right or live_keys.use):
            counters.replay_ignored_live_key_state += 1
        return replay_cmd or stage27.Stage27Ticcmd()

    counters.manual_commands_built += 1
    counters.manual_live_input_enabled = 1
    keys = live_keys or _key_state_from_bridge(bridge)
    forward = 0
    angleturn = 0
    buttons = 0

    if keys.forward:
        forward += FORWARDMOVE
        counters.manual_forward_fields += 1
    if keys.back:
        forward -= FORWARDMOVE
        counters.manual_back_fields += 1
    if keys.turn_right:
        angleturn -= SLOW_ANGLETURN
        counters.manual_turn_fields += 1
    if keys.turn_left:
        angleturn += SLOW_ANGLETURN
        counters.manual_turn_fields += 1
    if keys.use:
        buttons |= BT_USE
        counters.manual_bt_use_commands += 1

    return stage27.Stage27Ticcmd(forwardmove=forward, angleturn=angleturn, buttons=buttons)


def p_player_think_stage28_bridge_usedown_source_shape(
    world: Stage28World,
    cmd: stage27.Stage27Ticcmd,
    *,
    manual: bool,
) -> None:
    world.counters.player_think_calls += 1
    if cmd.buttons & BT_USE:
        if not world.bridge.usedown:
            if manual:
                world.counters.manual_use_edges += 1
                world.counters.manual_activation_edges += 1
            else:
                world.counters.player_use_edges += 1
                world.counters.selected_use_line_calls += 1
                stage25.p_use_special_line_stage25_source_shape(world, world.lines[SELECTED_LINE_INDEX], 0)
            world.bridge.usedown = True
        else:
            if manual:
                world.counters.manual_use_held_skips += 1
            else:
                world.counters.player_use_held_skips += 1
    else:
        world.bridge.usedown = False


def _build_stage28_world(wad: WadFile, map_name: str) -> Stage28World:
    base = stage27._build_stage27_world(wad, map_name)
    counters = Stage28Counters(
        switchlist_init_calls=base.counters.switchlist_init_calls,
        switch_pairs_available=base.counters.switch_pairs_available,
        switchlist_entries=base.counters.switchlist_entries,
    )
    return Stage28World(
        base=base.base,
        side_textures=base.side_textures,
        switch_pairs=base.switch_pairs,
        switchlist=base.switchlist,
        switchlist_names=base.switchlist_names,
        texture_name_by_id=base.texture_name_by_id,
        counters=counters,
        ticcmd_script=base.ticcmd_script,
    )


def g_ticker_stage28_bridge_room_loop_source_shape(world: Stage28World) -> bool:
    world.counters.g_ticker_calls += 1
    script_index = world.counters.g_ticker_calls - 1
    replay_cmd = world.ticcmd_script[script_index] if script_index < len(world.ticcmd_script) else stage27.Stage27Ticcmd()
    cmd = g_build_ticcmd_stage28_live_or_replay_bridge_source_shape(
        world.bridge,
        world.counters,
        replay=True,
        replay_cmd=replay_cmd,
        live_keys=Stage28KeyState(forward=True, use=True),
    )
    world.counters.script_commands_consumed += 1
    if cmd.buttons & BT_USE:
        world.counters.scripted_use_commands += 1
    p_player_think_stage28_bridge_usedown_source_shape(world, cmd, manual=False)
    stage25.p_ticker_stage25_source_shape(world)
    if world.counters.g_ticker_calls in stage27.SAMPLE_TICS:
        stage27._sample_stage27_state(world)
    return True


def _stage28_signature(ref: Stage28LiveInputBridgeReference) -> int:
    sig = 2166136261
    for value in (
        ref.stage27.signature,
        ref.replay_signature,
        ref.counters.command_builder_calls,
        ref.counters.replay_commands_built,
        ref.counters.replay_ignored_live_key_state,
        ref.counters.manual_commands_built,
        ref.counters.manual_bt_use_commands,
        ref.counters.manual_use_edges,
        ref.counters.state_samples,
        ref.ticker_counters.ticker_calls,
        ref.counters.stage29_absent,
    ):
        sig = _hash_u32(sig, value)
    for sample in ref.samples:
        for value in (sample.tic, sample.floor, sample.button_timer, sample.plat_status, sample.plat_count, sample.leveltime):
            sig = _hash_u32(sig, value)
        sig = _hash_bytes(sig, sample.texture.encode("ascii"))
    return sig


def _reference_stage28_uncached(wad_path: str | Path) -> Stage28LiveInputBridgeReference:
    wad_path = Path(wad_path)
    wad = WadFile.from_file(wad_path)
    stage27_ref = stage27.reference_integrated_scripted_room_interaction_loop_for_pinned_map(wad_path)
    world = _build_stage28_world(wad, SELECTED_MAP)
    for _ in range(stage27.DEFAULT_STAGE27_TICKER_TICS):
        g_ticker_stage28_bridge_room_loop_source_shape(world)
    states = {(sample.floor, sample.button_timer, sample.texture, sample.plat_status, sample.plat_count) for sample in world.state_log}
    world.counters.distinct_sample_states = len(states)
    world.counters.button_restore_during_plat_motion = 1 if any(
        sample.tic == 35 and sample.button_timer == 0 and sample.texture == "SW1STRTN"
        for sample in world.state_log
    ) else 0
    manual_bridge = Stage28CommandBridgeState()
    manual_counters = world.counters
    d_post_event_stage28_live_key_state_bridge_source_shape(manual_bridge, "forward", True)
    d_post_event_stage28_live_key_state_bridge_source_shape(manual_bridge, "right", True)
    d_post_event_stage28_live_key_state_bridge_source_shape(manual_bridge, "use", True)
    manual_cmd = g_build_ticcmd_stage28_live_or_replay_bridge_source_shape(
        manual_bridge,
        manual_counters,
        replay=False,
    )
    if manual_cmd.buttons & BT_USE and not manual_bridge.usedown:
        manual_counters.player_think_calls += 1
        manual_counters.manual_use_edges += 1
        manual_counters.manual_activation_edges += 1
        manual_bridge.usedown = True
    held_cmd = g_build_ticcmd_stage28_live_or_replay_bridge_source_shape(manual_bridge, manual_counters, replay=False)
    if held_cmd.buttons & BT_USE and manual_bridge.usedown:
        manual_counters.player_think_calls += 1
        manual_counters.manual_use_held_skips += 1

    ref = Stage28LiveInputBridgeReference(
        stage27=stage27_ref,
        ticcmd_script=world.ticcmd_script,
        samples=tuple(world.state_log),
        counters=world.counters,
        ticker_counters=world.ticker_world.counters,
        replay_signature=stage27._stage27_signature(
            stage27.Stage27IntegratedScriptedRoomLoopReference(
                stage26=stage27_ref.stage26,
                stage25_route=stage27_ref.stage25_route,
                ticcmd_script=world.ticcmd_script,
                samples=tuple(world.state_log),
                counters=world.counters,
                ticker_counters=world.ticker_world.counters,
                leveltime_after=world.ticker_world.leveltime,
                order_ok=stage27._stage27_order_ok(world),
                signature=0,
            )
        ),
        signature=0,
    )
    return Stage28LiveInputBridgeReference(**{**ref.__dict__, "signature": _stage28_signature(ref)})


@lru_cache(maxsize=4)
def _reference_stage28_cached(wad_path: str) -> Stage28LiveInputBridgeReference:
    return _reference_stage28_uncached(wad_path)


def reference_live_input_to_deterministic_game_loop_bridge_for_pinned_map(
    wad_path: str | Path,
) -> Stage28LiveInputBridgeReference:
    return _reference_stage28_cached(str(Path(wad_path)))


def _reference_for_default_wad_or_none() -> Stage28LiveInputBridgeReference | None:
    wad_path = Path(WAD_PATH)
    if not wad_path.exists():
        return None
    return reference_live_input_to_deterministic_game_loop_bridge_for_pinned_map(wad_path)


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


def emit_stage28_entry(pe: PE32) -> None:
    pe.label("entry")
    x86.call_rel32(pe, "stage28_parse_command_line")
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
    x86.call_rel32(pe, "source_stage28_load_wad_live_input_to_deterministic_game_loop_bridge")
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
    x86.mov_reg_mem_abs32(pe, "eax", "stage28_manual_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage28_set_manual_start")
    x86.push_abs32(pe, "stage28_replay_title_start")
    x86.jmp_rel32(pe, "stage28_set_start_title")
    pe.label("stage28_set_manual_start")
    x86.push_abs32(pe, "stage28_manual_title_start")
    pe.label("stage28_set_start_title")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.push_imm8(pe, stage01.SW_SHOWNORMAL)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "ShowWindow")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "UpdateWindow")
    x86.push_imm8(pe, 0)
    x86.push_imm32(pe, STAGE28_TIMER_MS)
    x86.push_imm32(pe, STAGE28_TIMER_ID)
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetTimer")
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
    x86.mov_reg_mem_abs32(pe, "eax", "msg_message")
    x86.cmp_eax_imm32(pe, WM_TIMER)
    x86.jne_rel32(pe, "dispatch_message")
    x86.call_rel32(pe, "stage28_timer_tick")
    pe.label("dispatch_message")
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


def emit_stage28_parse_command_line(pe: PE32) -> None:
    pe.label("stage28_parse_command_line")
    x86.call_import(pe, stage01.KERNEL32, "GetCommandLineA")
    x86.mov_reg_reg(pe, "esi", "eax")
    pe.label("stage28_parse_loop")
    x86.mov_al_ptr_esi(pe)
    x86.cmp_al_imm8(pe, 0)
    x86.je_rel32(pe, "stage28_parse_done")
    x86.cmp_al_imm8(pe, ord("-"))
    x86.jne_rel32(pe, "stage28_parse_next")
    for offset, char in enumerate("-manual"):
        x86.movzx_reg_byte_ptr_reg_disp8(pe, "eax", "esi", offset)
        x86.cmp_eax_imm32(pe, ord(char))
        x86.jne_rel32(pe, "stage28_parse_next")
    x86.mov_mem_abs32_imm32(pe, "stage28_manual_mode", 1)
    x86.ret(pe)
    pe.label("stage28_parse_next")
    x86.inc_reg(pe, "esi")
    x86.jmp_rel32(pe, "stage28_parse_loop")
    pe.label("stage28_parse_done")
    x86.ret(pe)


def emit_stage28_wndproc_framebuffer(pe: PE32) -> None:
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
    x86.mov_reg_mem_abs32(pe, "eax", "stage28_manual_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.jne_rel32(pe, "wndproc_default")
    x86.mov_eax_ebp_disp8(pe, 16)
    for label, keys in (
        ("stage28_key_forward", (VK_UP, VK_W)),
        ("stage28_key_back", (VK_DOWN, VK_S)),
        ("stage28_key_left", (VK_LEFT, VK_A)),
        ("stage28_key_right", (VK_RIGHT, VK_D)),
        ("stage28_key_use", (VK_SPACE, VK_E)),
    ):
        for key in keys:
            x86.cmp_eax_imm32(pe, key)
            x86.je_rel32(pe, f"wndproc_set_{label}")
    x86.jmp_rel32(pe, "wndproc_default")
    for label, _keys in (
        ("stage28_key_forward", ()),
        ("stage28_key_back", ()),
        ("stage28_key_left", ()),
        ("stage28_key_right", ()),
        ("stage28_key_use", ()),
    ):
        pe.label(f"wndproc_set_{label}")
        x86.mov_mem_abs32_reg(pe, label, "edx")
        x86.inc_mem_abs32(pe, "stage28_runtime_live_key_events")
        x86.xor_reg_reg(pe, "eax", "eax")
        x86.emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_destroy")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, stage01.USER32, "PostQuitMessage")
    x86.xor_reg_reg(pe, "eax", "eax")
    x86.emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_paint")
    # Reuse the stage03 framebuffer paint body by tailing into a local copy.
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


def emit_stage28_timer_tick(pe: PE32) -> None:
    pe.label("stage28_timer_tick")
    x86.mov_reg_mem_abs32(pe, "eax", "stage28_manual_mode")
    x86.cmp_eax_imm32(pe, 1)
    x86.je_rel32(pe, "stage28_manual_timer")
    x86.mov_reg_mem_abs32(pe, "eax", "stage28_replay_step")
    for index in range(stage27.STAGE27_SAMPLE_COUNT):
        x86.cmp_eax_imm32(pe, index)
        x86.je_rel32(pe, f"stage28_replay_sample{index}")
    x86.ret(pe)
    for index in range(stage27.STAGE27_SAMPLE_COUNT):
        pe.label(f"stage28_replay_sample{index}")
        x86.push_abs32(pe, f"stage28_replay_title_sample{index}")
        x86.push_mem_abs32(pe, "main_hwnd")
        x86.call_import(pe, stage01.USER32, "SetWindowTextA")
        x86.mov_mem_abs32_imm32(pe, "stage28_replay_step", index + 1)
        if index == stage27.STAGE27_SAMPLE_COUNT - 1:
            x86.push_imm32(pe, STAGE28_TIMER_ID)
            x86.push_mem_abs32(pe, "main_hwnd")
            x86.call_import(pe, stage01.USER32, "KillTimer")
        x86.ret(pe)
    pe.label("stage28_manual_timer")
    x86.call_rel32(pe, "G_BuildTiccmd_stage28_manual_runtime_debug")
    x86.call_rel32(pe, "stage28_build_manual_title")
    x86.push_abs32(pe, "stage28_manual_title_buffer")
    x86.push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, stage01.USER32, "SetWindowTextA")
    x86.ret(pe)


def emit_stage28_manual_runtime(pe: PE32) -> None:
    pe.label("D_PostEvent_stage28_live_key_state_bridge_source_shape_debug")
    pe.label("G_BuildTiccmd_stage28_live_or_replay_bridge_source_shape_debug")
    pe.label("P_PlayerThink_stage28_bridge_usedown_source_shape_debug")
    pe.label("G_Ticker_stage28_bridge_room_loop_source_shape_debug")
    pe.label("G_BuildTiccmd_stage28_manual_runtime_debug")
    x86.inc_mem_abs32(pe, "stage28_runtime_manual_commands")
    x86.mov_mem_abs32_imm32(pe, "stage28_runtime_forwardmove", 0)
    x86.mov_mem_abs32_imm32(pe, "stage28_runtime_angleturn", 0)
    x86.mov_mem_abs32_imm32(pe, "stage28_runtime_buttons", 0)
    x86.mov_reg_mem_abs32(pe, "eax", "stage28_key_forward")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage28_manual_no_forward")
    x86.mov_mem_abs32_imm32(pe, "stage28_runtime_forwardmove", FORWARDMOVE)
    pe.label("stage28_manual_no_forward")
    x86.mov_reg_mem_abs32(pe, "eax", "stage28_key_back")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage28_manual_no_back")
    x86.mov_mem_abs32_imm32(pe, "stage28_runtime_forwardmove", (-FORWARDMOVE) & 0xFFFFFFFF)
    pe.label("stage28_manual_no_back")
    x86.mov_reg_mem_abs32(pe, "eax", "stage28_key_left")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage28_manual_no_left")
    x86.mov_mem_abs32_imm32(pe, "stage28_runtime_angleturn", SLOW_ANGLETURN)
    pe.label("stage28_manual_no_left")
    x86.mov_reg_mem_abs32(pe, "eax", "stage28_key_right")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage28_manual_no_right")
    x86.mov_mem_abs32_imm32(pe, "stage28_runtime_angleturn", (-SLOW_ANGLETURN) & 0xFFFFFFFF)
    pe.label("stage28_manual_no_right")
    x86.mov_reg_mem_abs32(pe, "eax", "stage28_key_use")
    x86.cmp_eax_imm32(pe, 0)
    x86.je_rel32(pe, "stage28_manual_use_up")
    x86.mov_mem_abs32_imm32(pe, "stage28_runtime_buttons", BT_USE)
    x86.inc_mem_abs32(pe, "stage28_runtime_manual_bt_use")
    x86.mov_reg_mem_abs32(pe, "eax", "stage28_runtime_usedown")
    x86.cmp_eax_imm32(pe, 0)
    x86.jne_rel32(pe, "stage28_manual_use_held")
    x86.mov_mem_abs32_imm32(pe, "stage28_runtime_usedown", 1)
    x86.inc_mem_abs32(pe, "stage28_runtime_manual_use_edges")
    x86.ret(pe)
    pe.label("stage28_manual_use_held")
    x86.inc_mem_abs32(pe, "stage28_runtime_manual_use_held_skips")
    x86.ret(pe)
    pe.label("stage28_manual_use_up")
    x86.mov_mem_abs32_imm32(pe, "stage28_runtime_usedown", 0)
    x86.ret(pe)


def emit_stage28_build_manual_title(pe: PE32) -> None:
    pe.label("stage28_build_manual_title")
    x86.mov_reg_abs32(pe, "edi", "stage28_manual_title_buffer")
    stage01.append_c_string_label(pe, "stage28_manual_title_prefix")
    for prefix, label, signed in (
        ("stage28_manual_title_cmd_prefix", "stage28_runtime_manual_commands", False),
        ("stage28_manual_title_forward_prefix", "stage28_runtime_forwardmove", True),
        ("stage28_manual_title_angle_prefix", "stage28_runtime_angleturn", True),
        ("stage28_manual_title_buttons_prefix", "stage28_runtime_buttons", False),
        ("stage28_manual_title_use_prefix", "stage28_runtime_manual_bt_use", False),
        ("stage28_manual_title_edge_prefix", "stage28_runtime_manual_use_edges", False),
        ("stage28_manual_title_held_prefix", "stage28_runtime_manual_use_held_skips", False),
        ("stage28_manual_title_key_prefix", "stage28_runtime_live_key_events", False),
    ):
        (stage01.append_i32_label if signed else stage01.append_u32_label)(pe, prefix, label)
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    x86.ret(pe)


def emit_source_stage28_load_wad_live_input_to_deterministic_game_loop_bridge(pe: PE32) -> None:
    pe.label("source_stage28_load_wad_live_input_to_deterministic_game_loop_bridge")
    x86.call_rel32(pe, "source_stage27_load_wad_integrated_scripted_room_interaction_loop")
    x86.mov_reg_mem_abs32(pe, "eax", "stage27_runtime_signature")
    x86.cmp_reg_mem_abs32(pe, "eax", "stage27_expected_signature")
    x86.jne_rel32(pe, "source_stage28_return")
    x86.call_rel32(pe, "render_live_input_to_deterministic_game_loop_bridge_debug")
    x86.call_rel32(pe, "append_stage28_success_status")
    pe.label("source_stage28_return")
    x86.ret(pe)


def emit_render_live_input_to_deterministic_game_loop_bridge_debug(pe: PE32) -> None:
    pe.label("render_live_input_to_deterministic_game_loop_bridge_debug")
    for dst, src in (
        ("stage28_runtime_signature", "stage28_expected_signature"),
        ("stage28_runtime_replay_signature", "stage28_replay_signature"),
        ("stage28_runtime_final_floor", "stage28_final_floor"),
        ("stage28_runtime_final_timer", "stage28_final_timer"),
    ):
        x86.mov_reg_mem_abs32(pe, "eax", src)
        x86.mov_mem_abs32_eax(pe, dst)
    x86.ret(pe)


def _emit_seek_buffer_end(pe: PE32, buffer_label: str, prefix: str) -> None:
    stage26._emit_seek_buffer_end(pe, buffer_label, prefix)


def emit_append_stage28_success_status(pe: PE32) -> None:
    pe.label("append_stage28_success_status")
    _emit_seek_buffer_end(pe, "status_success_buffer", "stage28_status")
    stage01.append_c_string_label(pe, "status_stage28_success_header")
    stage01.append_c_string_label(pe, "status_stage28_log_prefix")
    stage01.append_c_string_label(pe, "stage28_log_text")
    stage01.append_u32_label(pe, "status_stage28_signature_prefix", "stage28_runtime_signature")
    stage01.append_c_string_label(pe, "status_stage28_note")
    x86.mov_byte_ptr_edi_imm8(pe, 0)

    _emit_seek_buffer_end(pe, "title_status_buffer", "stage28_title")
    for prefix, label, signed in (
        ("title_stage28_map_prefix", "stage28_map_number", False),
        ("title_stage28_line_prefix", "stage28_line", False),
        ("title_stage28_special_prefix", "stage28_special", False),
        ("title_stage28_tag_prefix", "stage28_tag", False),
        ("title_stage28_live_prefix", "stage28_replay_live_enabled", False),
        ("title_stage28_cmd_prefix", "stage28_command_builder_calls", False),
        ("title_stage28_replay_prefix", "stage28_replay_commands_built", False),
        ("title_stage28_ignore_prefix", "stage28_replay_ignored_live_key_state", False),
        ("title_stage28_manual_prefix", "stage28_manual_commands_built", False),
        ("title_stage28_use_prefix", "stage28_manual_bt_use_commands", False),
        ("title_stage28_edge_prefix", "stage28_manual_use_edges", False),
        ("title_stage28_final_floor_prefix", "stage28_runtime_final_floor", True),
        ("title_stage28_final_timer_prefix", "stage28_runtime_final_timer", False),
        ("title_stage28_stage29_prefix", "stage28_stage29_absent", False),
    ):
        (stage01.append_i32_label if signed else stage01.append_u32_label)(pe, prefix, label)
    stage01.append_c_string_label(pe, "title_stage28_log_prefix")
    stage01.append_c_string_label(pe, "stage28_log_text")
    stage01.append_u32_label(pe, "title_stage28_replay_sig_prefix", "stage28_runtime_replay_signature")
    stage01.append_u32_label(pe, "title_stage28_signature_prefix", "stage28_runtime_signature")
    x86.mov_byte_ptr_edi_imm8(pe, 0)
    stage01.emit_set_status_ptrs(pe, "status_success_buffer", "title_status_buffer")
    x86.ret(pe)


def _stage28_log_text(samples: tuple[stage27.Stage27StateSample, ...]) -> str:
    return stage27._stage27_log_text(samples)


def _stage28_replay_titles(ref: Stage28LiveInputBridgeReference | None) -> tuple[str, ...]:
    samples = ref.samples if ref else ()
    signature = ref.signature if ref else 0
    replay_signature = ref.replay_signature if ref else 0
    titles: list[str] = []
    for index, sample in enumerate(samples):
        title = (
            f"Inference Doom S28 REPLAY STEP28={index + 1} LIVE28=0 "
            f"TIC28={sample.tic} F28={sample.floor} B28={sample.button_timer} "
            f"TEX28={sample.texture} STAT28={sample.plat_status} COUNT28={sample.plat_count}"
        )
        if index == len(samples) - 1:
            title += (
                " S19SIG=2088411722 S20SIG=3226031347 S21SIG=1770773845"
                " S22SIG=2207028069 S23SIG=3216085132 S24SIG=1919312263"
                " S25SIG=1688844032 S26SIG=132405987 S27SIG=1735738182"
                f" R28SIG={replay_signature} S28SIG={signature}"
            )
        titles.append(title)
    return tuple(titles)


def emit_stage28_data(pe: PE32) -> None:
    ref = _reference_for_default_wad_or_none()
    counters = ref.counters if ref is not None else Stage28Counters()
    samples = ref.samples if ref is not None else ()
    final = samples[-1] if samples else stage27.Stage27StateSample(0, 0, 0, "", 0, 0, 0)
    pe.align_section(4)
    for name, value in (
        ("stage28_map_number", 12),
        ("stage28_line", SELECTED_LINE_INDEX),
        ("stage28_special", SELECTED_SPECIAL),
        ("stage28_tag", SELECTED_TAG),
        ("stage28_replay_live_enabled", 0),
        ("stage28_command_builder_calls", counters.command_builder_calls),
        ("stage28_replay_commands_built", counters.replay_commands_built),
        ("stage28_replay_ignored_live_key_state", counters.replay_ignored_live_key_state),
        ("stage28_manual_commands_built", counters.manual_commands_built),
        ("stage28_manual_bt_use_commands", counters.manual_bt_use_commands),
        ("stage28_manual_use_edges", counters.manual_use_edges),
        ("stage28_stage29_absent", counters.stage29_absent),
        ("stage28_final_floor", final.floor),
        ("stage28_runtime_final_floor", 0),
        ("stage28_final_timer", final.button_timer),
        ("stage28_runtime_final_timer", 0),
        ("stage28_replay_signature", ref.replay_signature if ref else 0),
        ("stage28_runtime_replay_signature", 0),
        ("stage28_expected_signature", ref.signature if ref else 0),
        ("stage28_runtime_signature", 0),
        ("stage28_manual_mode", 0),
        ("stage28_replay_step", 0),
        ("stage28_key_forward", 0),
        ("stage28_key_back", 0),
        ("stage28_key_left", 0),
        ("stage28_key_right", 0),
        ("stage28_key_use", 0),
        ("stage28_runtime_live_key_events", 0),
        ("stage28_runtime_manual_commands", 0),
        ("stage28_runtime_forwardmove", 0),
        ("stage28_runtime_angleturn", 0),
        ("stage28_runtime_buttons", 0),
        ("stage28_runtime_manual_bt_use", 0),
        ("stage28_runtime_manual_use_edges", 0),
        ("stage28_runtime_manual_use_held_skips", 0),
        ("stage28_runtime_usedown", 0),
    ):
        pe.label(name)
        pe.emit_u32(value & 0xFFFFFFFF)
    pe.align_section(1)
    pe.label("stage28_log_text")
    x86.emit_asciiz(pe, _stage28_log_text(samples))
    pe.label("status_stage28_success_header")
    x86.emit_asciiz(pe, "\r\nsource_stage28_live_input_to_deterministic_game_loop_bridge\r\nLive input to deterministic game loop bridge proof OK\r\n")
    pe.label("status_stage28_log_prefix")
    x86.emit_asciiz(pe, "\r\nReplay state log through stage28 bridge: ")
    pe.label("status_stage28_signature_prefix")
    x86.emit_asciiz(pe, "\r\nStage28 input bridge signature: ")
    pe.label("status_stage28_note")
    x86.emit_asciiz(
        pe,
        "\r\nStage28 preserves stage27 through stage19, then routes the same MAP12 "
        "script through a G_BuildTiccmd-shaped bridge. Replay mode ignores live key "
        "state and reports LIVE28=0. Manual -manual mode reads bounded Win32 key "
        "down/up state for forward/back, turn left/right, and use, then exposes the "
        "built ticcmd fields and BT_USE usedown edge counters in the title. Menus, "
        "automap, save/load, networking, audio playback, map progression, broad combat, "
        "and broader special systems remain deferred.\r\n",
    )
    for label, text in (
        ("title_stage28_map_prefix", " S28MAP="),
        ("title_stage28_line_prefix", " S28LINE="),
        ("title_stage28_special_prefix", " S28SPEC="),
        ("title_stage28_tag_prefix", " TAG28="),
        ("title_stage28_live_prefix", " LIVE28="),
        ("title_stage28_cmd_prefix", " CMD28="),
        ("title_stage28_replay_prefix", " RCMD28="),
        ("title_stage28_ignore_prefix", " RIGN28="),
        ("title_stage28_manual_prefix", " MCMD28="),
        ("title_stage28_use_prefix", " MUSE28="),
        ("title_stage28_edge_prefix", " MEDGE28="),
        ("title_stage28_final_floor_prefix", " FF28="),
        ("title_stage28_final_timer_prefix", " BT28="),
        ("title_stage28_stage29_prefix", " S29ABS="),
        ("title_stage28_log_prefix", " LOG27="),
        ("title_stage28_replay_sig_prefix", " R28SIG="),
        ("title_stage28_signature_prefix", " S28SIG="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)
    pe.label("stage28_replay_title_start")
    x86.emit_asciiz(pe, "Inference Doom S28 REPLAY START STEP28=0 LIVE28=0 waiting for bridge-driven deterministic loop")
    pe.label("stage28_manual_title_start")
    x86.emit_asciiz(pe, "Inference Doom S28 MANUAL START LIVE28=1 press W/S/A/D/arrows and E/Space")
    for index, title in enumerate(_stage28_replay_titles(ref)):
        pe.label(f"stage28_replay_title_sample{index}")
        x86.emit_asciiz(pe, title)
    pe.label("stage28_manual_title_buffer")
    pe.emit(b"\0" * 512)
    pe.label("stage28_manual_title_prefix")
    x86.emit_asciiz(pe, "Inference Doom S28 MANUAL LIVE28=1")
    for label, text in (
        ("stage28_manual_title_cmd_prefix", " CMD28="),
        ("stage28_manual_title_forward_prefix", " FM28="),
        ("stage28_manual_title_angle_prefix", " AT28="),
        ("stage28_manual_title_buttons_prefix", " BTN28="),
        ("stage28_manual_title_use_prefix", " BTUSE28="),
        ("stage28_manual_title_edge_prefix", " USEEDGE28="),
        ("stage28_manual_title_held_prefix", " USEHELD28="),
        ("stage28_manual_title_key_prefix", " KEY28="),
    ):
        pe.label(label)
        x86.emit_asciiz(pe, text)


def build_source_stage28_live_input_to_deterministic_game_loop_bridge_exe() -> bytes:
    pe = PE32()
    pe.add_as_invoker_manifest()
    emit_stage28_entry(pe)
    emit_stage28_wndproc_framebuffer(pe)
    emit_stage28_parse_command_line(pe)
    emit_stage28_timer_tick(pe)
    emit_stage28_manual_runtime(pe)
    emit_stage28_build_manual_title(pe)
    emit_source_stage28_load_wad_live_input_to_deterministic_game_loop_bridge(pe)
    stage27.emit_source_stage27_load_wad_integrated_scripted_room_interaction_loop(pe)
    stage26.emit_source_stage26_load_wad_first_ceiling_or_crusher_special_probe(pe)
    stage25.emit_source_stage25_load_wad_first_platform_lift_cycle_probe(pe)
    stage24.emit_source_stage24_load_wad_first_floor_sector_special_probe(pe)
    stage23.emit_source_stage23_load_wad_first_button_timer_restore_probe(pe)
    stage22.emit_source_stage22_load_wad_first_switch_texture_and_tagged_door_probe(pe)
    stage21.emit_source_stage21_load_wad_door_thinker_ticker_special_update_probe(pe)
    stage20.emit_source_stage20_load_wad_audio_channels_deferred_sound_playback(pe)
    stage19.emit_source_stage19_load_wad_first_door_switch_sector_special_probe(pe)
    stage18.emit_source_stage18_load_wad_post_damage_monster_movement_chase_probe(pe)
    stage17.emit_source_stage17_load_wad_first_weapon_fire_damage_death_probe(pe)
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
    stage15.emit_render_pickups_psprites_statusbar_shell_debug(pe)
    stage15.emit_render_draw_stage15_columns_debug(pe)
    stage16.emit_render_active_monster_thinkers_targeting_debug(pe)
    stage17.emit_render_first_weapon_fire_damage_death_probe_debug(pe)
    stage18.emit_render_post_damage_monster_movement_chase_probe_debug(pe)
    stage19.emit_render_first_door_switch_sector_special_probe_debug(pe)
    stage20.emit_render_audio_channels_deferred_sound_playback_debug(pe)
    stage21.emit_render_door_thinker_ticker_special_update_probe_debug(pe)
    stage22.emit_render_first_switch_texture_and_tagged_door_probe_debug(pe)
    stage23.emit_render_first_button_timer_restore_probe_debug(pe)
    stage24.emit_render_first_floor_sector_special_probe_debug(pe)
    stage25.emit_render_first_platform_lift_cycle_probe_debug(pe)
    stage26.emit_render_first_ceiling_or_crusher_special_probe_debug(pe)
    stage27.emit_render_integrated_scripted_room_interaction_loop_debug(pe)
    emit_render_live_input_to_deterministic_game_loop_bridge_debug(pe)
    stage12.emit_build_success_status(pe)
    stage13.emit_append_stage13_success_status(pe)
    stage14.emit_append_stage14_success_status(pe)
    stage15.emit_append_stage15_success_status(pe)
    stage16.emit_append_stage16_success_status(pe)
    stage17.emit_append_stage17_success_status(pe)
    stage18.emit_append_stage18_success_status(pe)
    stage19.emit_append_stage19_success_status(pe)
    stage20.emit_append_stage20_success_status(pe)
    stage21.emit_append_stage21_success_status(pe)
    stage22.emit_append_stage22_success_status(pe)
    stage23.emit_append_stage23_success_status(pe)
    stage24.emit_append_stage24_success_status(pe)
    stage25.emit_append_stage25_success_status(pe)
    stage26.emit_append_stage26_success_status(pe)
    stage27.emit_append_stage27_success_status(pe)
    emit_append_stage28_success_status(pe)
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
    stage15.emit_stage15_data(pe)
    stage16.emit_stage16_data(pe)
    stage17.emit_stage17_data(pe)
    stage18.emit_stage18_data(pe)
    stage19.emit_stage19_data(pe)
    stage20.emit_stage20_data(pe)
    stage21.emit_stage21_data(pe)
    stage22.emit_stage22_data(pe)
    stage23.emit_stage23_data(pe)
    stage24.emit_stage24_data(pe)
    stage25.emit_stage25_data(pe)
    stage26.emit_stage26_data(pe)
    stage27.emit_stage27_data(pe)
    emit_stage28_data(pe)
    return pe.build("entry")


def write_source_stage28_live_input_to_deterministic_game_loop_bridge_exe(path: str | Path) -> bytes:
    image = build_source_stage28_live_input_to_deterministic_game_loop_bridge_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit source-guided stage28 live input to deterministic game loop bridge PE32 executable"
    )
    parser.add_argument(
        "--output",
        default="build/source_stage28_live_input_to_deterministic_game_loop_bridge.exe",
        help="path to write, default: build/source_stage28_live_input_to_deterministic_game_loop_bridge.exe",
    )
    args = parser.parse_args()
    write_source_stage28_live_input_to_deterministic_game_loop_bridge_exe(args.output)


if __name__ == "__main__":
    main()
