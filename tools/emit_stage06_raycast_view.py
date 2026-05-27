from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import x86
from tools.pe32 import PE32


KERNEL32 = "KERNEL32.dll"
USER32 = "USER32.dll"
GDI32 = "GDI32.dll"

CS_VREDRAW = 0x0001
CS_HREDRAW = 0x0002
COLOR_WINDOW = 5
CW_USEDEFAULT = 0x80000000
DIB_RGB_COLORS = 0
BI_RGB = 0
SRCCOPY = 0x00CC0020
SW_SHOWNORMAL = 1
WM_DESTROY = 0x0002
WM_PAINT = 0x000F
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_TIMER = 0x0113
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_VISIBLE = 0x10000000

VK_ESCAPE = 0x1B
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_A = 0x41
VK_D = 0x44
VK_E = 0x45
VK_Q = 0x51
VK_S = 0x53
VK_W = 0x57

FRAMEBUFFER_WIDTH = 320
FRAMEBUFFER_HEIGHT = 200
FRAMEBUFFER_PIXELS = FRAMEBUFFER_WIDTH * FRAMEBUFFER_HEIGHT
FRAMEBUFFER_BYTES = FRAMEBUFFER_PIXELS * 4
HALF_FRAMEBUFFER_HEIGHT = FRAMEBUFFER_HEIGHT // 2
ROW_STRIDE_BYTES = FRAMEBUFFER_WIDTH * 4

WINDOW_WIDTH = 960
WINDOW_HEIGHT = 640
WINDOW_STYLE = WS_OVERLAPPEDWINDOW | WS_VISIBLE
WNDCLASSEXW_SIZE = 48
PAINTSTRUCT_SIZE = 64

ANGLE_COUNT = 256
ANGLE_MASK = ANGLE_COUNT - 1
TRIG_SCALE = 256
MAP_WIDTH = 16
MAP_HEIGHT = 16
MAP_SHIFT = 4
CELL_SHIFT = 8
CELL_SIZE = 1 << CELL_SHIFT
MAP_MAX_X = MAP_WIDTH * CELL_SIZE
MAP_MAX_Y = MAP_HEIGHT * CELL_SIZE

PLAYER_START_X = 3 * CELL_SIZE + CELL_SIZE // 2
PLAYER_START_Y = 3 * CELL_SIZE + CELL_SIZE // 2
PLAYER_START_ANGLE = 0
PLAYER_MOVE_SPEED = 18
PLAYER_STRAFE_SPEED = 16
PLAYER_TURN_SPEED = 3

FOV_ANGLE_UNITS = 48
RAY_START_DISTANCE = 16
RAY_STEP_DISTANCE = 16
RAY_MAX_DISTANCE = 4096
WALL_HEIGHT_NUMERATOR = 38000

COLOR_CEILING = 0x00151C2C
COLOR_FLOOR = 0x0037292D
COLOR_WALL = 0x00B7C3BA
COLOR_WALL_ALT = 0x00D0604E
COLOR_WALL_DARK = 0x006E8793

WINDOW_CLASS_NAME = "InferenceDoomStage06RaycastView"
WINDOW_TITLE = "Inference Doom - Stage 06 Raycast View"

KEY_STATE_BINDINGS = (
    (VK_UP, "key_forward"),
    (VK_W, "key_forward"),
    (VK_DOWN, "key_backward"),
    (VK_S, "key_backward"),
    (VK_LEFT, "key_turn_left"),
    (VK_Q, "key_turn_left"),
    (VK_RIGHT, "key_turn_right"),
    (VK_E, "key_turn_right"),
    (VK_A, "key_strafe_left"),
    (VK_D, "key_strafe_right"),
    (VK_ESCAPE, "key_escape"),
)

MAP_ROWS = (
    "1111111111111111",
    "1000000000000001",
    "1000200002000001",
    "1000000000000001",
    "1000111111000001",
    "1000100001000001",
    "1000100001000001",
    "1000100001111001",
    "1000100000001001",
    "1000111100001001",
    "1000000100001001",
    "1000000100000001",
    "1000000111111001",
    "1002000000000001",
    "1000000000000001",
    "1111111111111111",
)
WALL_MAP = bytes(int(cell) for row in MAP_ROWS for cell in row)
if len(WALL_MAP) != MAP_WIDTH * MAP_HEIGHT:
    raise AssertionError("hardcoded raycast map has the wrong size")


def build_trig_table(phase: float) -> list[int]:
    return [
        int(round(math.cos((index / ANGLE_COUNT) * math.tau + phase) * TRIG_SCALE))
        for index in range(ANGLE_COUNT)
    ]


COS_TABLE = build_trig_table(0.0)
SIN_TABLE = build_trig_table(-math.pi / 2.0)


def build_angle_offsets() -> bytes:
    offsets: list[int] = []
    for column in range(FRAMEBUFFER_WIDTH):
        signed_offset = round(
            ((column - (FRAMEBUFFER_WIDTH - 1) / 2) * FOV_ANGLE_UNITS)
            / FRAMEBUFFER_WIDTH
        )
        offsets.append(signed_offset & ANGLE_MASK)
    return bytes(offsets)


ANGLE_OFFSETS = build_angle_offsets()


def push_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\x68")
    pe.write_abs32(label)


def push_mem_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\xFF\x35")
    pe.write_abs32(label)


def mov_mem_abs32_eax(pe: PE32, label: str) -> None:
    pe.emit(b"\xA3")
    pe.write_abs32(label)


def mov_mem_abs32_reg(pe: PE32, label: str, reg: str) -> None:
    pe.emit(bytes([0x89, x86.modrm(0, reg, 5)]))
    pe.write_abs32(label)


def mov_mem_abs32_imm32(pe: PE32, label: str, value: int) -> None:
    pe.emit(b"\xC7\x05")
    pe.write_abs32(label)
    pe.emit_u32(value)


def mov_reg_abs32(pe: PE32, reg: str, label: str) -> None:
    pe.emit_u8(0xB8 + x86.reg_code(reg))
    pe.write_abs32(label)


def mov_reg_mem_abs32(pe: PE32, reg: str, label: str) -> None:
    pe.emit(bytes([0x8B, x86.modrm(0, reg, 5)]))
    pe.write_abs32(label)


def mov_reg_ptr_reg(pe: PE32, dst: str, base: str) -> None:
    pe.emit(bytes([0x8B, x86.modrm(0, dst, base)]))


def mov_ptr_reg_eax(pe: PE32, base: str) -> None:
    pe.emit(bytes([0x89, x86.modrm(0, "eax", base)]))


def movzx_reg_byte_ptr_reg(pe: PE32, dst: str, base: str) -> None:
    pe.emit(bytes([0x0F, 0xB6, x86.modrm(0, dst, base)]))


def movsx_reg_word_ptr_reg(pe: PE32, dst: str, base: str) -> None:
    pe.emit(bytes([0x0F, 0xBF, x86.modrm(0, dst, base)]))


def push_ebp_disp8(pe: PE32, displacement: int) -> None:
    pe.emit(bytes([0xFF, 0x75, displacement & 0xFF]))


def mov_eax_ebp_disp8(pe: PE32, displacement: int) -> None:
    pe.emit(bytes([0x8B, 0x45, displacement & 0xFF]))


def mov_reg_reg(pe: PE32, dst: str, src: str) -> None:
    pe.emit(bytes([0x8B, x86.modrm(3, dst, src)]))


def add_reg_reg(pe: PE32, dst: str, src: str) -> None:
    pe.emit(bytes([0x01, x86.modrm(3, src, dst)]))


def add_reg_imm32(pe: PE32, reg: str, value: int) -> None:
    if x86.reg_code(reg) == x86.reg_code("eax"):
        pe.emit(b"\x05")
    else:
        pe.emit(bytes([0x81, x86.modrm(3, 0, reg)]))
    pe.emit_u32(value)


def add_reg_mem_abs32(pe: PE32, reg: str, label: str) -> None:
    pe.emit(bytes([0x03, x86.modrm(0, reg, 5)]))
    pe.write_abs32(label)


def add_mem_abs32_imm32(pe: PE32, label: str, value: int) -> None:
    pe.emit(b"\x81\x05")
    pe.write_abs32(label)
    pe.emit_u32(value)


def sub_reg_reg(pe: PE32, dst: str, src: str) -> None:
    pe.emit(bytes([0x29, x86.modrm(3, src, dst)]))


def sub_reg_imm32(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0x81, x86.modrm(3, 5, reg)]))
    pe.emit_u32(value)


def and_reg_imm32(pe: PE32, reg: str, value: int) -> None:
    if x86.reg_code(reg) == x86.reg_code("eax"):
        pe.emit(b"\x25")
    else:
        pe.emit(bytes([0x81, x86.modrm(3, 4, reg)]))
    pe.emit_u32(value)


def shl_reg_imm8(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0xC1, x86.modrm(3, 4, reg), value & 0xFF]))


def shr_reg_imm8(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0xC1, x86.modrm(3, 5, reg), value & 0xFF]))


def sar_reg_imm8(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0xC1, x86.modrm(3, 7, reg), value & 0xFF]))


def imul_reg_reg(pe: PE32, dst: str, src: str) -> None:
    pe.emit(bytes([0x0F, 0xAF, x86.modrm(3, dst, src)]))


def xor_reg_reg(pe: PE32, dst: str, src: str) -> None:
    x86.xor_reg_reg(pe, dst, src)


def inc_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x40 + x86.reg_code(reg))


def dec_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x48 + x86.reg_code(reg))


def inc_mem_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\xFF\x05")
    pe.write_abs32(label)


def push_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x50 + x86.reg_code(reg))


def pop_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x58 + x86.reg_code(reg))


def cmp_eax_imm32(pe: PE32, value: int) -> None:
    pe.emit(b"\x3D")
    pe.emit_u32(value)


def cmp_reg_imm32(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0x81, x86.modrm(3, 7, reg)]))
    pe.emit_u32(value)


def cmp_reg_mem_abs32(pe: PE32, reg: str, label: str) -> None:
    pe.emit(bytes([0x3B, x86.modrm(0, reg, 5)]))
    pe.write_abs32(label)


def test_eax_eax(pe: PE32) -> None:
    pe.emit(b"\x85\xC0")


def test_reg_reg(pe: PE32, reg: str) -> None:
    pe.emit(bytes([0x85, x86.modrm(3, reg, reg)]))


def cdq(pe: PE32) -> None:
    pe.emit(b"\x99")


def div_ecx(pe: PE32) -> None:
    pe.emit(b"\xF7\xF1")


def je_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x84")
    pe.write_rel32(label)


def jne_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x85")
    pe.write_rel32(label)


def jb_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x82")
    pe.write_rel32(label)


def jae_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x83")
    pe.write_rel32(label)


def jbe_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x86")
    pe.write_rel32(label)


def emit_function_prologue(pe: PE32) -> None:
    pe.emit(b"\x55")  # push ebp
    pe.emit(b"\x89\xE5")  # mov ebp, esp


def emit_function_epilogue_ret(pe: PE32, stack_bytes: int) -> None:
    pe.emit(b"\xC9")  # leave
    pe.emit(b"\xC2")
    pe.emit_u16(stack_bytes)


def emit_utf16z(pe: PE32, value: str) -> None:
    pe.emit(value.encode("utf-16le"))
    pe.emit_u16(0)


def emit_i16_table(pe: PE32, values: list[int]) -> None:
    for value in values:
        pe.emit_u16(value & 0xFFFF)


def emit_entry(pe: PE32) -> None:
    pe.label("entry")

    x86.push_imm8(pe, 0)
    x86.call_import(pe, KERNEL32, "GetModuleHandleW")
    mov_mem_abs32_eax(pe, "wc_hInstance")

    push_abs32(pe, "window_class")
    x86.call_import(pe, USER32, "RegisterClassExW")
    test_eax_eax(pe)
    jne_rel32(pe, "class_registered")
    x86.push_imm8(pe, 1)
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("class_registered")
    x86.push_imm8(pe, 0)  # lpParam
    push_mem_abs32(pe, "wc_hInstance")
    x86.push_imm8(pe, 0)  # hMenu
    x86.push_imm8(pe, 0)  # hWndParent
    x86.push_imm32(pe, WINDOW_HEIGHT)
    x86.push_imm32(pe, WINDOW_WIDTH)
    x86.push_imm32(pe, CW_USEDEFAULT)
    x86.push_imm32(pe, CW_USEDEFAULT)
    x86.push_imm32(pe, WINDOW_STYLE)
    push_abs32(pe, "window_title")
    push_abs32(pe, "class_name")
    x86.push_imm8(pe, 0)  # dwExStyle
    x86.call_import(pe, USER32, "CreateWindowExW")
    test_eax_eax(pe)
    jne_rel32(pe, "window_created")
    x86.push_imm8(pe, 2)
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("window_created")
    mov_mem_abs32_eax(pe, "main_hwnd")
    x86.call_rel32(pe, "render_scene")
    x86.push_imm8(pe, SW_SHOWNORMAL)
    push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, USER32, "ShowWindow")
    push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, USER32, "UpdateWindow")

    x86.push_imm8(pe, 0)  # lpTimerFunc
    x86.push_imm8(pe, 16)  # uElapse
    x86.push_imm8(pe, 1)  # nIDEvent
    push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, USER32, "SetTimer")
    test_eax_eax(pe)
    jne_rel32(pe, "timer_created")
    x86.push_imm8(pe, 4)
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("timer_created")
    pe.label("message_loop")
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    x86.push_imm8(pe, 0)
    push_abs32(pe, "message")
    x86.call_import(pe, USER32, "GetMessageW")
    test_eax_eax(pe)
    je_rel32(pe, "clean_exit")
    cmp_eax_imm32(pe, 0xFFFFFFFF)
    je_rel32(pe, "message_error")

    push_abs32(pe, "message")
    x86.call_import(pe, USER32, "TranslateMessage")
    push_abs32(pe, "message")
    x86.call_import(pe, USER32, "DispatchMessageW")
    x86.jmp_rel32(pe, "message_loop")

    pe.label("clean_exit")
    push_mem_abs32(pe, "msg_wParam")
    x86.call_import(pe, KERNEL32, "ExitProcess")

    pe.label("message_error")
    x86.push_imm8(pe, 3)
    x86.call_import(pe, KERNEL32, "ExitProcess")


def emit_wndproc(pe: PE32) -> None:
    pe.label("wndproc")
    emit_function_prologue(pe)

    mov_eax_ebp_disp8(pe, 12)  # UINT message
    cmp_eax_imm32(pe, WM_DESTROY)
    je_rel32(pe, "wndproc_destroy")
    cmp_eax_imm32(pe, WM_PAINT)
    je_rel32(pe, "wndproc_paint")
    cmp_eax_imm32(pe, WM_TIMER)
    je_rel32(pe, "wndproc_timer")
    cmp_eax_imm32(pe, WM_KEYDOWN)
    je_rel32(pe, "wndproc_keydown")
    cmp_eax_imm32(pe, WM_KEYUP)
    je_rel32(pe, "wndproc_keyup")

    pe.label("wndproc_default")
    push_ebp_disp8(pe, 20)  # LPARAM lParam
    push_ebp_disp8(pe, 16)  # WPARAM wParam
    push_ebp_disp8(pe, 12)  # UINT message
    push_ebp_disp8(pe, 8)  # HWND hwnd
    x86.call_import(pe, USER32, "DefWindowProcW")
    emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_destroy")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, USER32, "PostQuitMessage")
    xor_reg_reg(pe, "eax", "eax")
    emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_timer")
    inc_mem_abs32(pe, "frame_index")
    x86.call_rel32(pe, "update_player")
    x86.call_rel32(pe, "render_scene")
    x86.push_imm8(pe, 0)  # bErase
    x86.push_imm8(pe, 0)  # lpRect
    push_ebp_disp8(pe, 8)  # hwnd
    x86.call_import(pe, USER32, "InvalidateRect")
    push_ebp_disp8(pe, 8)  # hwnd
    x86.call_import(pe, USER32, "UpdateWindow")
    xor_reg_reg(pe, "eax", "eax")
    emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_paint")
    push_abs32(pe, "paint_struct")
    push_ebp_disp8(pe, 8)  # hwnd
    x86.call_import(pe, USER32, "BeginPaint")
    mov_mem_abs32_eax(pe, "paint_hdc")

    push_abs32(pe, "client_rect")
    push_ebp_disp8(pe, 8)  # hwnd
    x86.call_import(pe, USER32, "GetClientRect")

    x86.push_imm32(pe, SRCCOPY)  # rop
    x86.push_imm8(pe, DIB_RGB_COLORS)  # iUsage
    push_abs32(pe, "bitmap_info")
    push_abs32(pe, "framebuffer")
    x86.push_imm32(pe, FRAMEBUFFER_HEIGHT)
    x86.push_imm32(pe, FRAMEBUFFER_WIDTH)
    x86.push_imm8(pe, 0)  # ySrc
    x86.push_imm8(pe, 0)  # xSrc
    push_mem_abs32(pe, "client_bottom")  # DestHeight
    push_mem_abs32(pe, "client_right")  # DestWidth
    x86.push_imm8(pe, 0)  # yDest
    x86.push_imm8(pe, 0)  # xDest
    push_mem_abs32(pe, "paint_hdc")
    x86.call_import(pe, GDI32, "StretchDIBits")

    push_abs32(pe, "paint_struct")
    push_ebp_disp8(pe, 8)  # hwnd
    x86.call_import(pe, USER32, "EndPaint")
    xor_reg_reg(pe, "eax", "eax")
    emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_keydown")
    mov_eax_ebp_disp8(pe, 16)  # WPARAM virtual key
    for virtual_key, state_label in KEY_STATE_BINDINGS:
        cmp_eax_imm32(pe, virtual_key)
        je_rel32(pe, f"keydown_{state_label}_{virtual_key:02x}")
    x86.jmp_rel32(pe, "wndproc_default")

    for virtual_key, state_label in KEY_STATE_BINDINGS:
        pe.label(f"keydown_{state_label}_{virtual_key:02x}")
        mov_mem_abs32_imm32(pe, state_label, 1)
        if state_label == "key_escape":
            x86.push_imm8(pe, 0)
            x86.call_import(pe, USER32, "PostQuitMessage")
        xor_reg_reg(pe, "eax", "eax")
        emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_keyup")
    mov_eax_ebp_disp8(pe, 16)  # WPARAM virtual key
    for virtual_key, state_label in KEY_STATE_BINDINGS:
        cmp_eax_imm32(pe, virtual_key)
        je_rel32(pe, f"keyup_{state_label}_{virtual_key:02x}")
    x86.jmp_rel32(pe, "wndproc_default")

    for virtual_key, state_label in KEY_STATE_BINDINGS:
        pe.label(f"keyup_{state_label}_{virtual_key:02x}")
        mov_mem_abs32_imm32(pe, state_label, 0)
        xor_reg_reg(pe, "eax", "eax")
        emit_function_epilogue_ret(pe, 16)


def emit_set_move_angle_from_player(pe: PE32, delta: int) -> None:
    mov_reg_mem_abs32(pe, "eax", "player_angle")
    if delta > 0:
        add_reg_imm32(pe, "eax", delta)
    elif delta < 0:
        sub_reg_imm32(pe, "eax", -delta)
    and_reg_imm32(pe, "eax", ANGLE_MASK)
    mov_mem_abs32_eax(pe, "move_angle")


def emit_update_player(pe: PE32) -> None:
    pe.label("update_player")

    mov_reg_mem_abs32(pe, "eax", "player_angle")

    mov_reg_mem_abs32(pe, "ecx", "key_turn_left")
    test_reg_reg(pe, "ecx")
    je_rel32(pe, "update_check_turn_right")
    sub_reg_imm32(pe, "eax", PLAYER_TURN_SPEED)

    pe.label("update_check_turn_right")
    mov_reg_mem_abs32(pe, "ecx", "key_turn_right")
    test_reg_reg(pe, "ecx")
    je_rel32(pe, "update_store_angle")
    add_reg_imm32(pe, "eax", PLAYER_TURN_SPEED)

    pe.label("update_store_angle")
    and_reg_imm32(pe, "eax", ANGLE_MASK)
    mov_mem_abs32_eax(pe, "player_angle")

    mov_reg_mem_abs32(pe, "eax", "player_x")
    mov_mem_abs32_eax(pe, "candidate_x")
    mov_reg_mem_abs32(pe, "eax", "player_y")
    mov_mem_abs32_eax(pe, "candidate_y")

    mov_reg_mem_abs32(pe, "eax", "key_forward")
    test_eax_eax(pe)
    je_rel32(pe, "update_backward")
    emit_set_move_angle_from_player(pe, 0)
    mov_mem_abs32_imm32(pe, "move_speed", PLAYER_MOVE_SPEED)
    x86.call_rel32(pe, "add_move_vector")

    pe.label("update_backward")
    mov_reg_mem_abs32(pe, "eax", "key_backward")
    test_eax_eax(pe)
    je_rel32(pe, "update_strafe_left")
    emit_set_move_angle_from_player(pe, 0)
    mov_mem_abs32_imm32(pe, "move_speed", -PLAYER_MOVE_SPEED)
    x86.call_rel32(pe, "add_move_vector")

    pe.label("update_strafe_left")
    mov_reg_mem_abs32(pe, "eax", "key_strafe_left")
    test_eax_eax(pe)
    je_rel32(pe, "update_strafe_right")
    emit_set_move_angle_from_player(pe, -64)
    mov_mem_abs32_imm32(pe, "move_speed", PLAYER_STRAFE_SPEED)
    x86.call_rel32(pe, "add_move_vector")

    pe.label("update_strafe_right")
    mov_reg_mem_abs32(pe, "eax", "key_strafe_right")
    test_eax_eax(pe)
    je_rel32(pe, "update_commit_move")
    emit_set_move_angle_from_player(pe, 64)
    mov_mem_abs32_imm32(pe, "move_speed", PLAYER_STRAFE_SPEED)
    x86.call_rel32(pe, "add_move_vector")

    pe.label("update_commit_move")
    x86.call_rel32(pe, "try_commit_move")
    x86.ret(pe)


def emit_load_trig_value(pe: PE32, table_label: str, angle_label: str, dest: str) -> None:
    mov_reg_mem_abs32(pe, "eax", angle_label)
    shl_reg_imm8(pe, "eax", 1)
    mov_reg_abs32(pe, "esi", table_label)
    add_reg_reg(pe, "esi", "eax")
    movsx_reg_word_ptr_reg(pe, dest, "esi")


def emit_add_move_vector(pe: PE32) -> None:
    pe.label("add_move_vector")
    push_reg(pe, "ecx")
    push_reg(pe, "esi")

    emit_load_trig_value(pe, "cos_table", "move_angle", "eax")
    mov_reg_mem_abs32(pe, "ecx", "move_speed")
    imul_reg_reg(pe, "eax", "ecx")
    sar_reg_imm8(pe, "eax", CELL_SHIFT)
    add_reg_mem_abs32(pe, "eax", "candidate_x")
    mov_mem_abs32_eax(pe, "candidate_x")

    emit_load_trig_value(pe, "sin_table", "move_angle", "eax")
    mov_reg_mem_abs32(pe, "ecx", "move_speed")
    imul_reg_reg(pe, "eax", "ecx")
    sar_reg_imm8(pe, "eax", CELL_SHIFT)
    add_reg_mem_abs32(pe, "eax", "candidate_y")
    mov_mem_abs32_eax(pe, "candidate_y")

    pop_reg(pe, "esi")
    pop_reg(pe, "ecx")
    x86.ret(pe)


def emit_try_commit_move(pe: PE32) -> None:
    pe.label("try_commit_move")
    push_reg(pe, "ebx")
    push_reg(pe, "edi")

    mov_reg_mem_abs32(pe, "eax", "candidate_x")
    cmp_reg_imm32(pe, "eax", MAP_MAX_X)
    jae_rel32(pe, "try_commit_done")
    mov_reg_mem_abs32(pe, "eax", "candidate_y")
    cmp_reg_imm32(pe, "eax", MAP_MAX_Y)
    jae_rel32(pe, "try_commit_done")

    mov_reg_mem_abs32(pe, "eax", "candidate_y")
    shr_reg_imm8(pe, "eax", CELL_SHIFT)
    shl_reg_imm8(pe, "eax", MAP_SHIFT)
    mov_reg_mem_abs32(pe, "ebx", "candidate_x")
    shr_reg_imm8(pe, "ebx", CELL_SHIFT)
    add_reg_reg(pe, "eax", "ebx")
    mov_reg_abs32(pe, "edi", "wall_map")
    add_reg_reg(pe, "edi", "eax")
    movzx_reg_byte_ptr_reg(pe, "eax", "edi")
    test_eax_eax(pe)
    jne_rel32(pe, "try_commit_done")

    mov_reg_mem_abs32(pe, "eax", "candidate_x")
    mov_mem_abs32_eax(pe, "player_x")
    mov_reg_mem_abs32(pe, "eax", "candidate_y")
    mov_mem_abs32_eax(pe, "player_y")

    pe.label("try_commit_done")
    pop_reg(pe, "edi")
    pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_render_scene(pe: PE32) -> None:
    pe.label("render_scene")
    push_reg(pe, "ebx")
    push_reg(pe, "ecx")
    push_reg(pe, "edx")
    push_reg(pe, "esi")
    push_reg(pe, "edi")

    x86.call_rel32(pe, "clear_view")

    xor_reg_reg(pe, "ebx", "ebx")
    pe.label("render_column_loop")
    mov_mem_abs32_reg(pe, "ray_column", "ebx")

    mov_reg_abs32(pe, "esi", "angle_offsets")
    add_reg_reg(pe, "esi", "ebx")
    movzx_reg_byte_ptr_reg(pe, "eax", "esi")
    add_reg_mem_abs32(pe, "eax", "player_angle")
    and_reg_imm32(pe, "eax", ANGLE_MASK)
    mov_mem_abs32_eax(pe, "ray_angle")

    x86.call_rel32(pe, "cast_ray")
    x86.call_rel32(pe, "draw_wall_column")

    inc_reg(pe, "ebx")
    cmp_reg_imm32(pe, "ebx", FRAMEBUFFER_WIDTH)
    jne_rel32(pe, "render_column_loop")

    pop_reg(pe, "edi")
    pop_reg(pe, "esi")
    pop_reg(pe, "edx")
    pop_reg(pe, "ecx")
    pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_clear_view(pe: PE32) -> None:
    pe.label("clear_view")
    push_reg(pe, "edi")
    pe.emit(b"\xFC")  # cld
    mov_reg_abs32(pe, "edi", "framebuffer")
    x86.mov_reg_imm32(pe, "eax", COLOR_CEILING)
    x86.mov_reg_imm32(pe, "ecx", FRAMEBUFFER_WIDTH * HALF_FRAMEBUFFER_HEIGHT)
    pe.emit(b"\xF3\xAB")  # rep stosd
    x86.mov_reg_imm32(pe, "eax", COLOR_FLOOR)
    x86.mov_reg_imm32(pe, "ecx", FRAMEBUFFER_WIDTH * HALF_FRAMEBUFFER_HEIGHT)
    pe.emit(b"\xF3\xAB")  # rep stosd
    pop_reg(pe, "edi")
    x86.ret(pe)


def emit_cast_ray(pe: PE32) -> None:
    pe.label("cast_ray")
    push_reg(pe, "ebx")
    push_reg(pe, "ecx")
    push_reg(pe, "edx")
    push_reg(pe, "esi")
    push_reg(pe, "edi")

    mov_mem_abs32_imm32(pe, "ray_distance", RAY_START_DISTANCE)
    mov_mem_abs32_imm32(pe, "ray_hit_tile", 0)
    mov_mem_abs32_imm32(pe, "ray_hit_color", COLOR_WALL_DARK)

    pe.label("cast_ray_loop")
    emit_load_trig_value(pe, "cos_table", "ray_angle", "eax")
    mov_reg_mem_abs32(pe, "ecx", "ray_distance")
    imul_reg_reg(pe, "eax", "ecx")
    sar_reg_imm8(pe, "eax", CELL_SHIFT)
    add_reg_mem_abs32(pe, "eax", "player_x")
    mov_mem_abs32_eax(pe, "sample_x")

    emit_load_trig_value(pe, "sin_table", "ray_angle", "eax")
    mov_reg_mem_abs32(pe, "ecx", "ray_distance")
    imul_reg_reg(pe, "eax", "ecx")
    sar_reg_imm8(pe, "eax", CELL_SHIFT)
    add_reg_mem_abs32(pe, "eax", "player_y")
    mov_mem_abs32_eax(pe, "sample_y")

    mov_reg_mem_abs32(pe, "eax", "sample_x")
    cmp_reg_imm32(pe, "eax", MAP_MAX_X)
    jae_rel32(pe, "cast_ray_boundary")
    mov_reg_mem_abs32(pe, "eax", "sample_y")
    cmp_reg_imm32(pe, "eax", MAP_MAX_Y)
    jae_rel32(pe, "cast_ray_boundary")

    mov_reg_mem_abs32(pe, "eax", "sample_y")
    shr_reg_imm8(pe, "eax", CELL_SHIFT)
    shl_reg_imm8(pe, "eax", MAP_SHIFT)
    mov_reg_mem_abs32(pe, "ebx", "sample_x")
    shr_reg_imm8(pe, "ebx", CELL_SHIFT)
    add_reg_reg(pe, "eax", "ebx")
    mov_mem_abs32_eax(pe, "sample_index")

    mov_reg_abs32(pe, "edi", "wall_map")
    add_reg_mem_abs32(pe, "edi", "sample_index")
    movzx_reg_byte_ptr_reg(pe, "eax", "edi")
    test_eax_eax(pe)
    jne_rel32(pe, "cast_ray_hit_wall")

    add_mem_abs32_imm32(pe, "ray_distance", RAY_STEP_DISTANCE)
    mov_reg_mem_abs32(pe, "eax", "ray_distance")
    cmp_reg_imm32(pe, "eax", RAY_MAX_DISTANCE)
    jbe_rel32(pe, "cast_ray_loop")
    x86.jmp_rel32(pe, "cast_ray_done")

    pe.label("cast_ray_boundary")
    x86.mov_reg_imm32(pe, "eax", 1)

    pe.label("cast_ray_hit_wall")
    mov_mem_abs32_eax(pe, "ray_hit_tile")
    cmp_eax_imm32(pe, 2)
    je_rel32(pe, "cast_ray_alt_color")
    cmp_eax_imm32(pe, 3)
    je_rel32(pe, "cast_ray_dark_color")
    mov_mem_abs32_imm32(pe, "ray_hit_color", COLOR_WALL)
    x86.jmp_rel32(pe, "cast_ray_done")

    pe.label("cast_ray_alt_color")
    mov_mem_abs32_imm32(pe, "ray_hit_color", COLOR_WALL_ALT)
    x86.jmp_rel32(pe, "cast_ray_done")

    pe.label("cast_ray_dark_color")
    mov_mem_abs32_imm32(pe, "ray_hit_color", COLOR_WALL_DARK)

    pe.label("cast_ray_done")
    pop_reg(pe, "edi")
    pop_reg(pe, "esi")
    pop_reg(pe, "edx")
    pop_reg(pe, "ecx")
    pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_draw_wall_column(pe: PE32) -> None:
    pe.label("draw_wall_column")
    push_reg(pe, "ebx")
    push_reg(pe, "ecx")
    push_reg(pe, "edx")
    push_reg(pe, "edi")

    mov_reg_mem_abs32(pe, "eax", "ray_hit_tile")
    test_eax_eax(pe)
    je_rel32(pe, "draw_wall_done")

    xor_reg_reg(pe, "edx", "edx")
    x86.mov_reg_imm32(pe, "eax", WALL_HEIGHT_NUMERATOR)
    mov_reg_mem_abs32(pe, "ecx", "ray_distance")
    div_ecx(pe)
    cmp_reg_imm32(pe, "eax", FRAMEBUFFER_HEIGHT)
    jbe_rel32(pe, "draw_wall_height_ok")
    x86.mov_reg_imm32(pe, "eax", FRAMEBUFFER_HEIGHT)

    pe.label("draw_wall_height_ok")
    mov_mem_abs32_eax(pe, "column_height")

    x86.mov_reg_imm32(pe, "ebx", FRAMEBUFFER_HEIGHT)
    sub_reg_reg(pe, "ebx", "eax")
    shr_reg_imm8(pe, "ebx", 1)
    mov_mem_abs32_reg(pe, "wall_top", "ebx")

    add_reg_reg(pe, "ebx", "eax")
    cmp_reg_imm32(pe, "ebx", FRAMEBUFFER_HEIGHT)
    jbe_rel32(pe, "draw_wall_bottom_ok")
    x86.mov_reg_imm32(pe, "ebx", FRAMEBUFFER_HEIGHT)

    pe.label("draw_wall_bottom_ok")
    mov_mem_abs32_reg(pe, "wall_bottom", "ebx")

    mov_reg_mem_abs32(pe, "ecx", "wall_bottom")
    mov_reg_mem_abs32(pe, "eax", "wall_top")
    sub_reg_reg(pe, "ecx", "eax")
    test_reg_reg(pe, "ecx")
    je_rel32(pe, "draw_wall_done")

    mov_reg_reg(pe, "ebx", "eax")
    shl_reg_imm8(pe, "ebx", 8)
    mov_reg_reg(pe, "edx", "eax")
    shl_reg_imm8(pe, "edx", 6)
    add_reg_reg(pe, "ebx", "edx")
    add_reg_mem_abs32(pe, "ebx", "ray_column")
    shl_reg_imm8(pe, "ebx", 2)

    mov_reg_abs32(pe, "edi", "framebuffer")
    add_reg_reg(pe, "edi", "ebx")
    mov_reg_mem_abs32(pe, "eax", "ray_hit_color")

    pe.label("draw_wall_loop")
    mov_ptr_reg_eax(pe, "edi")
    add_reg_imm32(pe, "edi", ROW_STRIDE_BYTES)
    dec_reg(pe, "ecx")
    jne_rel32(pe, "draw_wall_loop")

    pe.label("draw_wall_done")
    pop_reg(pe, "edi")
    pop_reg(pe, "edx")
    pop_reg(pe, "ecx")
    pop_reg(pe, "ebx")
    x86.ret(pe)


def emit_data(pe: PE32) -> None:
    pe.align_section(4)
    pe.label("window_class")
    pe.label("wc_cbSize")
    pe.emit_u32(WNDCLASSEXW_SIZE)
    pe.label("wc_style")
    pe.emit_u32(CS_HREDRAW | CS_VREDRAW)
    pe.label("wc_lpfnWndProc")
    pe.write_abs32("wndproc")
    pe.label("wc_cbClsExtra")
    pe.emit_u32(0)
    pe.label("wc_cbWndExtra")
    pe.emit_u32(0)
    pe.label("wc_hInstance")
    pe.emit_u32(0)
    pe.label("wc_hIcon")
    pe.emit_u32(0)
    pe.label("wc_hCursor")
    pe.emit_u32(0)
    pe.label("wc_hbrBackground")
    pe.emit_u32(COLOR_WINDOW + 1)
    pe.label("wc_lpszMenuName")
    pe.emit_u32(0)
    pe.label("wc_lpszClassName")
    pe.write_abs32("class_name")
    pe.label("wc_hIconSm")
    pe.emit_u32(0)

    pe.label("main_hwnd")
    pe.emit_u32(0)
    pe.label("frame_index")
    pe.emit_u32(0)
    pe.label("key_forward")
    pe.emit_u32(0)
    pe.label("key_backward")
    pe.emit_u32(0)
    pe.label("key_turn_left")
    pe.emit_u32(0)
    pe.label("key_turn_right")
    pe.emit_u32(0)
    pe.label("key_strafe_left")
    pe.emit_u32(0)
    pe.label("key_strafe_right")
    pe.emit_u32(0)
    pe.label("key_escape")
    pe.emit_u32(0)

    pe.label("player_x")
    pe.emit_u32(PLAYER_START_X)
    pe.label("player_y")
    pe.emit_u32(PLAYER_START_Y)
    pe.label("player_angle")
    pe.emit_u32(PLAYER_START_ANGLE)
    pe.label("candidate_x")
    pe.emit_u32(PLAYER_START_X)
    pe.label("candidate_y")
    pe.emit_u32(PLAYER_START_Y)
    pe.label("move_angle")
    pe.emit_u32(0)
    pe.label("move_speed")
    pe.emit_u32(0)

    pe.label("ray_column")
    pe.emit_u32(0)
    pe.label("ray_angle")
    pe.emit_u32(0)
    pe.label("ray_distance")
    pe.emit_u32(RAY_START_DISTANCE)
    pe.label("ray_hit_tile")
    pe.emit_u32(0)
    pe.label("ray_hit_color")
    pe.emit_u32(COLOR_WALL)
    pe.label("sample_x")
    pe.emit_u32(0)
    pe.label("sample_y")
    pe.emit_u32(0)
    pe.label("sample_index")
    pe.emit_u32(0)
    pe.label("column_height")
    pe.emit_u32(0)
    pe.label("wall_top")
    pe.emit_u32(0)
    pe.label("wall_bottom")
    pe.emit_u32(0)

    pe.align_section(4)
    pe.label("message")
    pe.label("msg_hwnd")
    pe.emit_u32(0)
    pe.label("msg_message")
    pe.emit_u32(0)
    pe.label("msg_wParam")
    pe.emit_u32(0)
    pe.label("msg_lParam")
    pe.emit_u32(0)
    pe.label("msg_time")
    pe.emit_u32(0)
    pe.label("msg_pt_x")
    pe.emit_u32(0)
    pe.label("msg_pt_y")
    pe.emit_u32(0)

    pe.align_section(4)
    pe.label("paint_struct")
    pe.label("paint_hdc")
    pe.emit_u32(0)
    pe.emit_zeros(PAINTSTRUCT_SIZE - 4)

    pe.align_section(4)
    pe.label("client_rect")
    pe.label("client_left")
    pe.emit_u32(0)
    pe.label("client_top")
    pe.emit_u32(0)
    pe.label("client_right")
    pe.emit_u32(0)
    pe.label("client_bottom")
    pe.emit_u32(0)

    pe.align_section(4)
    pe.label("bitmap_info")
    pe.label("bmi_header")
    pe.emit_u32(40)
    pe.emit_u32(FRAMEBUFFER_WIDTH)
    pe.emit_u32((-FRAMEBUFFER_HEIGHT) & 0xFFFFFFFF)
    pe.emit_u16(1)
    pe.emit_u16(32)
    pe.emit_u32(BI_RGB)
    pe.emit_u32(FRAMEBUFFER_BYTES)
    pe.emit_u32(0)
    pe.emit_u32(0)
    pe.emit_u32(0)
    pe.emit_u32(0)

    pe.align_section(2)
    pe.label("class_name")
    emit_utf16z(pe, WINDOW_CLASS_NAME)
    pe.label("window_title")
    emit_utf16z(pe, WINDOW_TITLE)

    pe.align_section(4)
    pe.label("angle_offsets")
    pe.emit(ANGLE_OFFSETS)

    pe.align_section(2)
    pe.label("cos_table")
    emit_i16_table(pe, COS_TABLE)
    pe.label("sin_table")
    emit_i16_table(pe, SIN_TABLE)

    pe.align_section(1)
    pe.label("wall_map")
    pe.emit(WALL_MAP)

    pe.align_section(4)
    pe.label("framebuffer")
    pe.emit_zeros(FRAMEBUFFER_BYTES)


def build_stage06_raycast_view_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    emit_wndproc(pe)
    emit_update_player(pe)
    emit_add_move_vector(pe)
    emit_try_commit_move(pe)
    emit_render_scene(pe)
    emit_clear_view(pe)
    emit_cast_ray(pe)
    emit_draw_wall_column(pe)
    emit_data(pe)
    return pe.build("entry")


def write_stage06_raycast_view_exe(path: str | Path) -> bytes:
    image = build_stage06_raycast_view_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the Phase 11 PE32 x86 Win32 tiny first-person renderer."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/stage06_raycast_view.exe",
        help="path to write, default: build/stage06_raycast_view.exe",
    )
    args = parser.parse_args()
    write_stage06_raycast_view_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
