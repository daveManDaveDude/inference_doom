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
WM_PAINT = 0x000F
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_VISIBLE = 0x10000000

GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_BEGIN = 0
INVALID_HANDLE_VALUE = 0xFFFFFFFF

DT_WORDBREAK = 0x00000010
DT_EXPANDTABS = 0x00000040
DT_NOPREFIX = 0x00000800
DRAW_TEXT_FLAGS = DT_WORDBREAK | DT_EXPANDTABS | DT_NOPREFIX

WINDOW_WIDTH = 720
WINDOW_HEIGHT = 300
WINDOW_STYLE = WS_OVERLAPPEDWINDOW | WS_VISIBLE
WNDCLASSEXW_SIZE = 48
PAINTSTRUCT_SIZE = 64

WAD_HEADER_SIZE = 12
WAD_DIRECTORY_ENTRY_SIZE = 16
IWAD_MAGIC = 0x44415749
PWAD_MAGIC = 0x44415750

WINDOW_CLASS_NAME = "InferenceDoomStage03WadProbe"
WINDOW_TITLE = "Inference Doom - Stage 03 WAD Probe"
WAD_PATH = r"third_party\freedoom\freedoom2.wad"


def push_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\x68")
    pe.write_abs32(label)


def push_mem_abs32(pe: PE32, label: str) -> None:
    pe.emit(b"\xFF\x35")
    pe.write_abs32(label)


def mov_mem_abs32_eax(pe: PE32, label: str) -> None:
    pe.emit(b"\xA3")
    pe.write_abs32(label)


def mov_mem_abs32_abs32(pe: PE32, dst_label: str, src_label: str) -> None:
    pe.emit(b"\xC7\x05")
    pe.write_abs32(dst_label)
    pe.write_abs32(src_label)


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


def cmp_eax_imm32(pe: PE32, value: int) -> None:
    pe.emit(b"\x3D")
    pe.emit_u32(value)


def cmp_reg_imm32(pe: PE32, reg: str, value: int) -> None:
    pe.emit(bytes([0x81, x86.modrm(3, 7, reg)]))
    pe.emit_u32(value)


def cmp_reg_reg(pe: PE32, left: str, right: str) -> None:
    pe.emit(bytes([0x39, x86.modrm(3, right, left)]))


def test_eax_eax(pe: PE32) -> None:
    pe.emit(b"\x85\xC0")


def je_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x84")
    pe.write_rel32(label)


def jne_rel32(pe: PE32, label: str) -> None:
    pe.emit(b"\x0F\x85")
    pe.write_rel32(label)


def inc_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x40 + x86.reg_code(reg))


def dec_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x48 + x86.reg_code(reg))


def push_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x50 + x86.reg_code(reg))


def pop_reg(pe: PE32, reg: str) -> None:
    pe.emit_u8(0x58 + x86.reg_code(reg))


def mov_al_ptr_esi(pe: PE32) -> None:
    pe.emit(b"\x8A\x06")


def mov_ptr_edi_al(pe: PE32) -> None:
    pe.emit(b"\x88\x07")


def mov_dl_ptr_esi(pe: PE32) -> None:
    pe.emit(b"\x8A\x16")


def mov_ptr_esi_dl(pe: PE32) -> None:
    pe.emit(b"\x88\x16")


def mov_ptr_edi_dl(pe: PE32) -> None:
    pe.emit(b"\x88\x17")


def cmp_al_imm8(pe: PE32, value: int) -> None:
    pe.emit(b"\x3C")
    pe.emit_u8(value)


def add_dl_imm8(pe: PE32, value: int) -> None:
    pe.emit(b"\x80\xC2")
    pe.emit_u8(value)


def div_ecx(pe: PE32) -> None:
    pe.emit(b"\xF7\xF1")


def mov_byte_ptr_edi_imm8(pe: PE32, value: int) -> None:
    pe.emit(b"\xC6\x07")
    pe.emit_u8(value)


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


def emit_asciiz(pe: PE32, value: str) -> None:
    pe.emit(value.encode("ascii"))
    pe.emit_u8(0)


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
    x86.call_rel32(pe, "probe_wad")

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
    cmp_eax_imm32(pe, WM_DESTROY)
    je_rel32(pe, "wndproc_destroy")
    cmp_eax_imm32(pe, WM_PAINT)
    je_rel32(pe, "wndproc_paint")

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
    x86.xor_reg_reg(pe, "eax", "eax")
    emit_function_epilogue_ret(pe, 16)

    pe.label("wndproc_paint")
    push_abs32(pe, "paint_struct")
    push_ebp_disp8(pe, 8)  # hwnd
    x86.call_import(pe, USER32, "BeginPaint")
    mov_mem_abs32_eax(pe, "paint_hdc")

    push_abs32(pe, "client_rect")
    push_ebp_disp8(pe, 8)  # hwnd
    x86.call_import(pe, USER32, "GetClientRect")

    x86.push_imm32(pe, DRAW_TEXT_FLAGS)  # uFormat
    push_abs32(pe, "client_rect")  # lprc
    x86.push_imm32(pe, 0xFFFFFFFF)  # cchText = -1
    push_mem_abs32(pe, "status_text_ptr")  # lpchText
    push_mem_abs32(pe, "paint_hdc")  # hdc
    x86.call_import(pe, USER32, "DrawTextA")

    push_abs32(pe, "paint_struct")
    push_ebp_disp8(pe, 8)  # hwnd
    x86.call_import(pe, USER32, "EndPaint")
    x86.xor_reg_reg(pe, "eax", "eax")
    emit_function_epilogue_ret(pe, 16)


def set_status_ptr(pe: PE32, label: str) -> None:
    mov_mem_abs32_abs32(pe, "status_text_ptr", label)


def close_probe_file(pe: PE32) -> None:
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "CloseHandle")


def emit_probe_wad(pe: PE32) -> None:
    pe.label("probe_wad")

    x86.push_imm8(pe, 0)  # hTemplateFile
    x86.push_imm32(pe, FILE_ATTRIBUTE_NORMAL)
    x86.push_imm32(pe, OPEN_EXISTING)
    x86.push_imm8(pe, 0)  # lpSecurityAttributes
    x86.push_imm32(pe, FILE_SHARE_READ)
    x86.push_imm32(pe, GENERIC_READ)
    push_abs32(pe, "wad_path_w")
    x86.call_import(pe, KERNEL32, "CreateFileW")
    cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    jne_rel32(pe, "probe_file_opened")
    set_status_ptr(pe, "status_open_failed")
    x86.ret(pe)

    pe.label("probe_file_opened")
    mov_mem_abs32_eax(pe, "wad_file_handle")

    x86.push_imm8(pe, 0)  # lpOverlapped
    push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, WAD_HEADER_SIZE)
    push_abs32(pe, "wad_header")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    test_eax_eax(pe)
    je_rel32(pe, "probe_header_read_failed")
    mov_reg_mem_abs32(pe, "eax", "bytes_read")
    cmp_eax_imm32(pe, WAD_HEADER_SIZE)
    jne_rel32(pe, "probe_header_read_failed")

    mov_reg_mem_abs32(pe, "eax", "wad_kind")
    cmp_eax_imm32(pe, IWAD_MAGIC)
    je_rel32(pe, "probe_magic_ok")
    cmp_eax_imm32(pe, PWAD_MAGIC)
    je_rel32(pe, "probe_magic_ok")
    set_status_ptr(pe, "status_bad_magic")
    x86.jmp_rel32(pe, "probe_close_and_return")

    pe.label("probe_magic_ok")
    mov_reg_mem_abs32(pe, "eax", "wad_lump_count")
    test_eax_eax(pe)
    je_rel32(pe, "probe_empty_directory")
    mov_reg_mem_abs32(pe, "eax", "wad_directory_offset")
    test_eax_eax(pe)
    je_rel32(pe, "probe_directory_read_failed")

    x86.push_imm32(pe, FILE_BEGIN)
    x86.push_imm8(pe, 0)  # lpDistanceToMoveHigh
    push_mem_abs32(pe, "wad_directory_offset")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "SetFilePointer")
    cmp_eax_imm32(pe, INVALID_HANDLE_VALUE)
    je_rel32(pe, "probe_directory_read_failed")

    x86.push_imm8(pe, 0)  # lpOverlapped
    push_abs32(pe, "bytes_read")
    x86.push_imm32(pe, WAD_DIRECTORY_ENTRY_SIZE)
    push_abs32(pe, "directory_entry")
    push_mem_abs32(pe, "wad_file_handle")
    x86.call_import(pe, KERNEL32, "ReadFile")
    test_eax_eax(pe)
    je_rel32(pe, "probe_directory_read_failed")
    mov_reg_mem_abs32(pe, "eax", "bytes_read")
    cmp_eax_imm32(pe, WAD_DIRECTORY_ENTRY_SIZE)
    jne_rel32(pe, "probe_directory_read_failed")

    close_probe_file(pe)
    x86.call_rel32(pe, "build_success_status")
    x86.ret(pe)

    pe.label("probe_header_read_failed")
    set_status_ptr(pe, "status_header_read_failed")
    x86.jmp_rel32(pe, "probe_close_and_return")

    pe.label("probe_empty_directory")
    set_status_ptr(pe, "status_empty_directory")
    x86.jmp_rel32(pe, "probe_close_and_return")

    pe.label("probe_directory_read_failed")
    set_status_ptr(pe, "status_directory_read_failed")

    pe.label("probe_close_and_return")
    close_probe_file(pe)
    x86.ret(pe)


def emit_build_success_status(pe: PE32) -> None:
    pe.label("build_success_status")
    mov_reg_abs32(pe, "edi", "status_success_buffer")

    mov_reg_abs32(pe, "esi", "status_ok_prefix")
    x86.call_rel32(pe, "append_c_string")

    mov_reg_abs32(pe, "esi", "wad_kind")
    x86.mov_reg_imm32(pe, "ecx", 4)
    pe.label("append_kind_loop")
    mov_al_ptr_esi(pe)
    mov_ptr_edi_al(pe)
    inc_reg(pe, "esi")
    inc_reg(pe, "edi")
    dec_reg(pe, "ecx")
    jne_rel32(pe, "append_kind_loop")

    mov_reg_abs32(pe, "esi", "status_lumps_prefix")
    x86.call_rel32(pe, "append_c_string")
    mov_reg_mem_abs32(pe, "eax", "wad_lump_count")
    x86.call_rel32(pe, "append_u32_decimal")

    mov_reg_abs32(pe, "esi", "status_directory_prefix")
    x86.call_rel32(pe, "append_c_string")
    mov_reg_mem_abs32(pe, "eax", "wad_directory_offset")
    x86.call_rel32(pe, "append_u32_decimal")

    mov_reg_abs32(pe, "esi", "status_path_prefix")
    x86.call_rel32(pe, "append_c_string")
    mov_byte_ptr_edi_imm8(pe, 0)
    set_status_ptr(pe, "status_success_buffer")
    x86.ret(pe)


def emit_append_c_string(pe: PE32) -> None:
    pe.label("append_c_string")
    push_reg(pe, "eax")

    pe.label("append_c_string_loop")
    mov_al_ptr_esi(pe)
    cmp_al_imm8(pe, 0)
    je_rel32(pe, "append_c_string_done")
    mov_ptr_edi_al(pe)
    inc_reg(pe, "esi")
    inc_reg(pe, "edi")
    x86.jmp_rel32(pe, "append_c_string_loop")

    pe.label("append_c_string_done")
    pop_reg(pe, "eax")
    x86.ret(pe)


def emit_append_u32_decimal(pe: PE32) -> None:
    pe.label("append_u32_decimal")
    push_reg(pe, "eax")
    push_reg(pe, "ebx")
    push_reg(pe, "ecx")
    push_reg(pe, "edx")
    push_reg(pe, "esi")

    test_eax_eax(pe)
    jne_rel32(pe, "append_decimal_nonzero")
    mov_byte_ptr_edi_imm8(pe, ord("0"))
    inc_reg(pe, "edi")
    x86.jmp_rel32(pe, "append_decimal_done")

    pe.label("append_decimal_nonzero")
    mov_reg_abs32(pe, "esi", "number_scratch_end")
    x86.mov_reg_imm32(pe, "ecx", 10)

    pe.label("append_decimal_divide_loop")
    x86.xor_reg_reg(pe, "edx", "edx")
    div_ecx(pe)
    dec_reg(pe, "esi")
    add_dl_imm8(pe, ord("0"))
    mov_ptr_esi_dl(pe)
    test_eax_eax(pe)
    jne_rel32(pe, "append_decimal_divide_loop")

    mov_reg_abs32(pe, "ebx", "number_scratch_end")

    pe.label("append_decimal_copy_loop")
    cmp_reg_reg(pe, "esi", "ebx")
    je_rel32(pe, "append_decimal_done")
    mov_dl_ptr_esi(pe)
    mov_ptr_edi_dl(pe)
    inc_reg(pe, "esi")
    inc_reg(pe, "edi")
    x86.jmp_rel32(pe, "append_decimal_copy_loop")

    pe.label("append_decimal_done")
    pop_reg(pe, "esi")
    pop_reg(pe, "edx")
    pop_reg(pe, "ecx")
    pop_reg(pe, "ebx")
    pop_reg(pe, "eax")
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
    pe.label("paint_hdc")
    pe.emit_u32(0)
    pe.label("wad_file_handle")
    pe.emit_u32(0)
    pe.label("bytes_read")
    pe.emit_u32(0)
    pe.label("status_text_ptr")
    pe.write_abs32("status_not_run")

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
    pe.emit_zeros(PAINTSTRUCT_SIZE)

    pe.align_section(4)
    pe.label("client_rect")
    pe.label("client_left")
    pe.emit_u32(12)
    pe.label("client_top")
    pe.emit_u32(12)
    pe.label("client_right")
    pe.emit_u32(0)
    pe.label("client_bottom")
    pe.emit_u32(0)

    pe.align_section(4)
    pe.label("wad_header")
    pe.label("wad_kind")
    pe.emit_u32(0)
    pe.label("wad_lump_count")
    pe.emit_u32(0)
    pe.label("wad_directory_offset")
    pe.emit_u32(0)

    pe.align_section(4)
    pe.label("directory_entry")
    pe.emit_zeros(WAD_DIRECTORY_ENTRY_SIZE)

    pe.align_section(2)
    pe.label("class_name")
    emit_utf16z(pe, WINDOW_CLASS_NAME)
    pe.label("window_title")
    emit_utf16z(pe, WINDOW_TITLE)
    pe.label("wad_path_w")
    emit_utf16z(pe, WAD_PATH)

    pe.align_section(1)
    pe.label("status_not_run")
    emit_asciiz(pe, "WAD probe has not run yet.")
    pe.label("status_open_failed")
    emit_asciiz(pe, f"WAD FAIL: could not open {WAD_PATH}")
    pe.label("status_header_read_failed")
    emit_asciiz(pe, "WAD FAIL: could not read the 12-byte WAD header.")
    pe.label("status_bad_magic")
    emit_asciiz(pe, "WAD FAIL: header is not IWAD or PWAD.")
    pe.label("status_empty_directory")
    emit_asciiz(pe, "WAD FAIL: header reports an empty WAD directory.")
    pe.label("status_directory_read_failed")
    emit_asciiz(pe, "WAD FAIL: could not seek to and read the first directory entry.")
    pe.label("status_ok_prefix")
    emit_asciiz(pe, "WAD OK\r\ntype: ")
    pe.label("status_lumps_prefix")
    emit_asciiz(pe, "\r\nlumps: ")
    pe.label("status_directory_prefix")
    emit_asciiz(pe, "\r\ndirectory offset: ")
    pe.label("status_path_prefix")
    emit_asciiz(pe, f"\r\npath: {WAD_PATH}")

    pe.align_section(4)
    pe.label("number_scratch")
    pe.emit_zeros(16)
    pe.label("number_scratch_end")

    pe.align_section(4)
    pe.label("status_success_buffer")
    pe.emit_zeros(256)


def build_stage03_wad_probe_exe() -> bytes:
    pe = PE32()
    emit_entry(pe)
    emit_wndproc(pe)
    emit_probe_wad(pe)
    emit_build_success_status(pe)
    emit_append_c_string(pe)
    emit_append_u32_decimal(pe)
    emit_data(pe)
    return pe.build("entry")


def write_stage03_wad_probe_exe(path: str | Path) -> bytes:
    image = build_stage03_wad_probe_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the Phase 7 PE32 x86 Win32 WAD probe executable."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/stage03_wad_probe.exe",
        help="path to write, default: build/stage03_wad_probe.exe",
    )
    args = parser.parse_args()
    write_stage03_wad_probe_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
