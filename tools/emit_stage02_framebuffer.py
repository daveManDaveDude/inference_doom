from __future__ import annotations

import argparse
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
VK_S = 0x53
VK_W = 0x57

FRAMEBUFFER_WIDTH = 320
FRAMEBUFFER_HEIGHT = 200
FRAMEBUFFER_BYTES = FRAMEBUFFER_WIDTH * FRAMEBUFFER_HEIGHT * 4
PLAYER_SIZE = 16
PLAYER_MOVE_SPEED = 2
PLAYER_TURN_SPEED = 4
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 640
WINDOW_STYLE = WS_OVERLAPPEDWINDOW | WS_VISIBLE
WNDCLASSEXW_SIZE = 48
PAINTSTRUCT_SIZE = 64

WINDOW_CLASS_NAME = "InferenceDoomStage02Framebuffer"
WINDOW_TITLE = "Inference Doom - Stage 02 Framebuffer"

KEY_STATE_BINDINGS = (
    (VK_UP, "key_forward"),
    (VK_W, "key_forward"),
    (VK_DOWN, "key_backward"),
    (VK_S, "key_backward"),
    (VK_LEFT, "key_turn_left"),
    (VK_RIGHT, "key_turn_right"),
    (VK_A, "key_strafe_left"),
    (VK_D, "key_strafe_right"),
    (VK_ESCAPE, "key_escape"),
)


def push_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\x68")
    pe.write_abs32(label)


def push_mem_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\xFF\x35")
    pe.write_abs32(label)


def mov_mem_abs32_eax(pe: PE32, label: str) -> None:
    pe.emit(b"\xA3")
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


def add_mem_abs32_imm32(pe: PE32, label: str, value: int) -> None:
    pe.emit(b"\x81\x05")
    pe.write_abs32(label)
    pe.emit_u32(value)


def sub_mem_abs32_imm32(pe: PE32, label: str, value: int) -> None:
    pe.emit(b"\x81\x2D")
    pe.write_abs32(label)
    pe.emit_u32(value)


def and_reg_imm32(pe: PE32, reg: str, value: int) -> None:
    if x86.reg_code(reg) == x86.reg_code("eax"):
        pe.emit(b"\x25")
    else:
        pe.emit(bytes([0x81, x86.modrm(3, 4, reg)]))
    pe.emit_u32(value)


def shl_reg_imm8(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0xC1, x86.modrm(3, 4, reg), value & 0xFF]))


def or_reg_reg(pe: PE32, dst: str, src: str) -> None:
    pe.emit(bytes([0x09, x86.modrm(3, src, dst)]))


def or_reg_imm32(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0x81, x86.modrm(3, 1, reg)]))
    pe.emit_u32(value)


def xor_reg_reg(pe: PE32, dst: str, src: str) -> None:
    x86.xor_reg_reg(pe, dst, src)


def inc_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x40 + x86.reg_code(reg))


def inc_mem_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\xFF\x05")
    pe.write_abs32(label)


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
    x86.call_rel32(pe, "render_pattern")
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
    x86.call_rel32(pe, "update_input")
    x86.call_rel32(pe, "render_pattern")
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


def emit_update_input(pe: PE32) -> None:
    pe.label("update_input")

    mov_reg_mem_abs32(pe, "eax", "key_forward")
    test_eax_eax(pe)
    je_rel32(pe, "input_backward")
    mov_reg_mem_abs32(pe, "eax", "player_y")
    cmp_reg_imm32(pe, "eax", PLAYER_MOVE_SPEED - 1)
    jbe_rel32(pe, "input_backward")
    sub_mem_abs32_imm32(pe, "player_y", PLAYER_MOVE_SPEED)

    pe.label("input_backward")
    mov_reg_mem_abs32(pe, "eax", "key_backward")
    test_eax_eax(pe)
    je_rel32(pe, "input_strafe_left")
    mov_reg_mem_abs32(pe, "eax", "player_y")
    cmp_reg_imm32(pe, "eax", FRAMEBUFFER_HEIGHT - PLAYER_SIZE - PLAYER_MOVE_SPEED)
    jae_rel32(pe, "input_strafe_left")
    add_mem_abs32_imm32(pe, "player_y", PLAYER_MOVE_SPEED)

    pe.label("input_strafe_left")
    mov_reg_mem_abs32(pe, "eax", "key_strafe_left")
    test_eax_eax(pe)
    je_rel32(pe, "input_strafe_right")
    mov_reg_mem_abs32(pe, "eax", "player_x")
    cmp_reg_imm32(pe, "eax", PLAYER_MOVE_SPEED - 1)
    jbe_rel32(pe, "input_strafe_right")
    sub_mem_abs32_imm32(pe, "player_x", PLAYER_MOVE_SPEED)

    pe.label("input_strafe_right")
    mov_reg_mem_abs32(pe, "eax", "key_strafe_right")
    test_eax_eax(pe)
    je_rel32(pe, "input_turn_left")
    mov_reg_mem_abs32(pe, "eax", "player_x")
    cmp_reg_imm32(pe, "eax", FRAMEBUFFER_WIDTH - PLAYER_SIZE - PLAYER_MOVE_SPEED)
    jae_rel32(pe, "input_turn_left")
    add_mem_abs32_imm32(pe, "player_x", PLAYER_MOVE_SPEED)

    pe.label("input_turn_left")
    mov_reg_mem_abs32(pe, "eax", "key_turn_left")
    test_eax_eax(pe)
    je_rel32(pe, "input_turn_right")
    sub_mem_abs32_imm32(pe, "player_angle", PLAYER_TURN_SPEED)

    pe.label("input_turn_right")
    mov_reg_mem_abs32(pe, "eax", "key_turn_right")
    test_eax_eax(pe)
    je_rel32(pe, "input_refresh_bounds")
    add_mem_abs32_imm32(pe, "player_angle", PLAYER_TURN_SPEED)

    pe.label("input_refresh_bounds")
    mov_reg_mem_abs32(pe, "eax", "player_angle")
    and_reg_imm32(pe, "eax", 0xFF)
    mov_mem_abs32_eax(pe, "player_angle")

    mov_reg_mem_abs32(pe, "eax", "player_x")
    add_reg_imm32(pe, "eax", PLAYER_SIZE)
    mov_mem_abs32_eax(pe, "player_right")

    mov_reg_mem_abs32(pe, "eax", "player_y")
    add_reg_imm32(pe, "eax", PLAYER_SIZE)
    mov_mem_abs32_eax(pe, "player_bottom")

    x86.ret(pe)


def emit_render_pattern(pe: PE32) -> None:
    pe.label("render_pattern")
    pe.emit(b"\x53")  # push ebx
    pe.emit(b"\x56")  # push esi
    pe.emit(b"\x57")  # push edi
    pe.emit(b"\xFC")  # cld; make stosd walk forward through the framebuffer
    mov_reg_abs32(pe, "edi", "framebuffer")
    mov_reg_mem_abs32(pe, "ebx", "frame_index")
    xor_reg_reg(pe, "esi", "esi")  # y = 0

    pe.label("render_y_loop")
    xor_reg_reg(pe, "ecx", "ecx")  # x = 0

    pe.label("render_x_loop")
    mov_reg_reg(pe, "eax", "ecx")
    xor_reg_reg(pe, "eax", "esi")
    add_reg_reg(pe, "eax", "ebx")
    and_reg_imm32(pe, "eax", 0xFF)
    shl_reg_imm8(pe, "eax", 16)

    mov_reg_reg(pe, "edx", "esi")
    shl_reg_imm8(pe, "edx", 1)
    add_reg_reg(pe, "edx", "ebx")
    and_reg_imm32(pe, "edx", 0xFF)
    shl_reg_imm8(pe, "edx", 8)
    or_reg_reg(pe, "eax", "edx")

    mov_reg_reg(pe, "edx", "ecx")
    add_reg_reg(pe, "edx", "ebx")
    and_reg_imm32(pe, "edx", 0xFF)
    or_reg_reg(pe, "eax", "edx")

    cmp_reg_mem_abs32(pe, "ecx", "player_x")
    jb_rel32(pe, "render_store_pixel")
    cmp_reg_mem_abs32(pe, "ecx", "player_right")
    jae_rel32(pe, "render_store_pixel")
    cmp_reg_mem_abs32(pe, "esi", "player_y")
    jb_rel32(pe, "render_store_pixel")
    cmp_reg_mem_abs32(pe, "esi", "player_bottom")
    jae_rel32(pe, "render_store_pixel")
    mov_reg_mem_abs32(pe, "eax", "player_angle")
    and_reg_imm32(pe, "eax", 0xFF)
    shl_reg_imm8(pe, "eax", 16)
    or_reg_imm32(pe, "eax", 0x0000FF00)

    pe.label("render_store_pixel")
    pe.emit(b"\xAB")  # stosd
    inc_reg(pe, "ecx")
    cmp_reg_imm32(pe, "ecx", FRAMEBUFFER_WIDTH)
    jne_rel32(pe, "render_x_loop")

    inc_reg(pe, "esi")
    cmp_reg_imm32(pe, "esi", FRAMEBUFFER_HEIGHT)
    jne_rel32(pe, "render_y_loop")

    pe.emit(b"\x5F")  # pop edi
    pe.emit(b"\x5E")  # pop esi
    pe.emit(b"\x5B")  # pop ebx
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
    pe.emit_u32((FRAMEBUFFER_WIDTH - PLAYER_SIZE) // 2)
    pe.label("player_y")
    pe.emit_u32((FRAMEBUFFER_HEIGHT - PLAYER_SIZE) // 2)
    pe.label("player_right")
    pe.emit_u32(((FRAMEBUFFER_WIDTH - PLAYER_SIZE) // 2) + PLAYER_SIZE)
    pe.label("player_bottom")
    pe.emit_u32(((FRAMEBUFFER_HEIGHT - PLAYER_SIZE) // 2) + PLAYER_SIZE)
    pe.label("player_angle")
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
    pe.label("framebuffer")
    pe.emit_zeros(FRAMEBUFFER_BYTES)


def build_stage02_framebuffer_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    emit_wndproc(pe)
    emit_update_input(pe)
    emit_render_pattern(pe)
    emit_data(pe)
    return pe.build("entry")


def write_stage02_framebuffer_exe(path: str | Path) -> bytes:
    image = build_stage02_framebuffer_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the Phase 4 PE32 x86 Win32 framebuffer executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/stage02_framebuffer.exe",
        help="path to write, default: build/stage02_framebuffer.exe",
    )
    args = parser.parse_args()
    write_stage02_framebuffer_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
