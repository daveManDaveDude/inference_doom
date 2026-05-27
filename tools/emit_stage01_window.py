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

CS_VREDRAW = 0x0001
CS_HREDRAW = 0x0002
COLOR_WINDOW = 5
CW_USEDEFAULT = 0x80000000
SW_SHOWNORMAL = 1
WM_DESTROY = 0x0002
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_VISIBLE = 0x10000000

WINDOW_WIDTH = 640
WINDOW_HEIGHT = 480
WINDOW_STYLE = WS_OVERLAPPEDWINDOW | WS_VISIBLE
WNDCLASSEXW_SIZE = 48

WINDOW_CLASS_NAME = "InferenceDoomStage01Window"
WINDOW_TITLE = "Inference Doom - Stage 01 Window"


def push_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\x68")
    pe.write_abs32(label)


def push_mem_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\xFF\x35")
    pe.write_abs32(label)


def mov_mem_abs32_eax(pe: PE32, label: str) -> None:
    pe.emit(b"\xA3")
    pe.write_abs32(label)


def push_ebp_disp8(pe: PE32, displacement: int) -> None:
    pe.emit(bytes([0xFF, 0x75, displacement & 0xFF]))


def mov_eax_ebp_disp8(pe: PE32, displacement: int) -> None:
    pe.emit(bytes([0x8B, 0x45, displacement & 0xFF]))


def cmp_eax_imm8(pe: PE32, value: int) -> None:
    pe.emit(bytes([0x83, 0xF8, value & 0xFF]))


def cmp_eax_imm32(pe: PE32, value: int) -> None:
    pe.emit(b"\x3D")
    pe.emit_u32(value)


def test_eax_eax(pe: PE32) -> None:
    pe.emit(b"\x85\xC0")


def je_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x84")
    pe.write_rel32(label)


def jne_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x85")
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
    x86.push_imm8(pe, SW_SHOWNORMAL)
    push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, USER32, "ShowWindow")
    push_mem_abs32(pe, "main_hwnd")
    x86.call_import(pe, USER32, "UpdateWindow")

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
    cmp_eax_imm8(pe, WM_DESTROY)
    je_rel32(pe, "wndproc_destroy")

    push_ebp_disp8(pe, 20)  # LPARAM lParam
    push_ebp_disp8(pe, 16)  # WPARAM wParam
    push_ebp_disp8(pe, 12)  # UINT message
    push_ebp_disp8(pe, 8)  # HWND hwnd
    x86.call_import(pe, USER32, "DefWindowProcW")
    emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_destroy")
    x86.push_imm8(pe, 0)
    x86.call_import(pe, USER32, "PostQuitMessage")
    x86.xor_reg_reg(pe, "eax", "eax")
    emit_function_epilogue_ret(pe, 16)


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

    pe.align_section(2)
    pe.label("class_name")
    emit_utf16z(pe, WINDOW_CLASS_NAME)
    pe.label("window_title")
    emit_utf16z(pe, WINDOW_TITLE)


def build_stage01_window_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    emit_wndproc(pe)
    emit_data(pe)
    return pe.build("entry")


def write_stage01_window_exe(path: str | Path) -> bytes:
    image = build_stage01_window_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the Phase 3 PE32 x86 Win32 window executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/stage01_window.exe",
        help="path to write, default: build/stage01_window.exe",
    )
    args = parser.parse_args()
    write_stage01_window_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
