from __future__ import annotations

import struct


REG32 = {
    "eax": 0,
    "ecx": 1,
    "edx": 2,
    "ebx": 3,
    "esp": 4,
    "ebp": 5,
    "esi": 6,
    "edi": 7,
}


def reg_code(reg: str | int) -> int:
    if isinstance(reg, int):
        if 0 <= reg <= 7:
            return reg
        raise ValueError(f"bad register code: {reg}")
    try:
        return REG32[reg.lower()]
    except KeyError as exc:
        raise ValueError(f"unknown register: {reg}") from exc


def modrm(mod: int, reg: str | int, rm: str | int) -> int:
    return ((mod & 0x3) << 6) | ((reg_code(reg) & 0x7) << 3) | (reg_code(rm) & 0x7)


def ret_bytes() -> bytes:
    return b"\xC3"


def nop_bytes() -> bytes:
    return b"\x90"


def push_imm32_bytes(value: int) -> bytes:
    return b"\x68" + struct.pack("<I", value & 0xFFFFFFFF)


def push_imm8_bytes(value: int) -> bytes:
    return b"\x6A" + struct.pack("<b", value)


def mov_reg_imm32_bytes(reg: str | int, value: int) -> bytes:
    return bytes([0xB8 + reg_code(reg)]) + struct.pack("<I", value & 0xFFFFFFFF)


def xor_reg_reg_bytes(dst: str | int, src: str | int) -> bytes:
    return bytes([0x31, modrm(3, src, dst)])


def push_abs32(out, label: str) -> None:
    out.emit(b"\x68")
    out.write_abs32(label)


def push_mem_abs32(out, label: str) -> None:
    out.emit(b"\xFF\x35")
    out.write_abs32(label)


def push_reg(out, reg: str | int) -> None:
    out.emit_u8(0x50 + reg_code(reg))


def pop_reg(out, reg: str | int) -> None:
    out.emit_u8(0x58 + reg_code(reg))


def ret(out) -> None:
    out.emit(ret_bytes())


def ret_imm16(out, stack_bytes: int) -> None:
    out.emit(b"\xC2")
    out.emit_u16(stack_bytes)


def nop(out) -> None:
    out.emit(nop_bytes())


def push_imm32(out, value: int) -> None:
    out.emit(push_imm32_bytes(value))


def push_imm8(out, value: int) -> None:
    out.emit(push_imm8_bytes(value))


def mov_reg_imm32(out, reg: str | int, value: int) -> None:
    out.emit(mov_reg_imm32_bytes(reg, value))


def xor_reg_reg(out, dst: str | int, src: str | int) -> None:
    out.emit(xor_reg_reg_bytes(dst, src))


def mov_mem_abs32_eax(out, label: str) -> None:
    out.emit(b"\xA3")
    out.write_abs32(label)


def mov_mem_abs32_reg(out, label: str, reg: str | int) -> None:
    out.emit(bytes([0x89, modrm(0, reg, 5)]))
    out.write_abs32(label)


def mov_mem_abs32_imm32(out, label: str, value: int) -> None:
    out.emit(b"\xC7\x05")
    out.write_abs32(label)
    out.emit_u32(value)


def mov_mem_abs32_abs32(out, dst_label: str, src_label: str) -> None:
    out.emit(b"\xC7\x05")
    out.write_abs32(dst_label)
    out.write_abs32(src_label)


def mov_reg_abs32(out, reg: str | int, label: str) -> None:
    out.emit_u8(0xB8 + reg_code(reg))
    out.write_abs32(label)


def mov_reg_mem_abs32(out, reg: str | int, label: str) -> None:
    out.emit(bytes([0x8B, modrm(0, reg, 5)]))
    out.write_abs32(label)


def mov_reg_reg(out, dst: str | int, src: str | int) -> None:
    out.emit(bytes([0x8B, modrm(3, dst, src)]))


def mov_reg_ptr_reg(out, dst: str | int, base: str | int) -> None:
    out.emit(bytes([0x8B, modrm(0, dst, base)]))


def mov_reg_ptr_reg_disp8(
    out, dst: str | int, base: str | int, displacement: int
) -> None:
    out.emit(bytes([0x8B, modrm(1, dst, base), displacement & 0xFF]))


def mov_ptr_reg_eax(out, base: str | int) -> None:
    out.emit(bytes([0x89, modrm(0, "eax", base)]))


def mov_ptr_reg_disp8_eax(out, base: str | int, displacement: int) -> None:
    out.emit(bytes([0x89, modrm(1, "eax", base), displacement & 0xFF]))


def mov_ptr_reg_disp8_reg(
    out, base: str | int, displacement: int, src: str | int
) -> None:
    out.emit(bytes([0x89, modrm(1, src, base), displacement & 0xFF]))


def mov_word_ptr_reg_disp8_ax(out, base: str | int, displacement: int) -> None:
    out.emit(bytes([0x66, 0x89, modrm(1, "eax", base), displacement & 0xFF]))


def movzx_reg_word_ptr_reg(out, dst: str | int, base: str | int) -> None:
    out.emit(bytes([0x0F, 0xB7, modrm(0, dst, base)]))


def movzx_reg_word_ptr_reg_disp8(
    out, dst: str | int, base: str | int, displacement: int
) -> None:
    out.emit(bytes([0x0F, 0xB7, modrm(1, dst, base), displacement & 0xFF]))


def movzx_reg_byte_ptr_reg(out, dst: str | int, base: str | int) -> None:
    out.emit(bytes([0x0F, 0xB6, modrm(0, dst, base)]))


def movsx_reg_word_ptr_reg(out, dst: str | int, base: str | int) -> None:
    out.emit(bytes([0x0F, 0xBF, modrm(0, dst, base)]))


def movsx_reg_word_ptr_reg_disp8(
    out, dst: str | int, base: str | int, displacement: int
) -> None:
    out.emit(bytes([0x0F, 0xBF, modrm(1, dst, base), displacement & 0xFF]))


def mov_reg_ebp_disp8(out, reg: str | int, displacement: int) -> None:
    out.emit(bytes([0x8B, modrm(1, reg, "ebp"), displacement & 0xFF]))


def mov_eax_ebp_disp8(out, displacement: int) -> None:
    mov_reg_ebp_disp8(out, "eax", displacement)


def push_ebp_disp8(out, displacement: int) -> None:
    out.emit(bytes([0xFF, 0x75, displacement & 0xFF]))


def add_reg_reg(out, dst: str | int, src: str | int) -> None:
    out.emit(bytes([0x01, modrm(3, src, dst)]))


def add_reg_imm32(out, reg: str | int, value: int) -> None:
    if reg_code(reg) == reg_code("eax"):
        out.emit(b"\x05")
    else:
        out.emit(bytes([0x81, modrm(3, 0, reg)]))
    out.emit_u32(value)


def add_reg_mem_abs32(out, reg: str | int, label: str) -> None:
    out.emit(bytes([0x03, modrm(0, reg, 5)]))
    out.write_abs32(label)


def sub_reg_reg(out, dst: str | int, src: str | int) -> None:
    out.emit(bytes([0x29, modrm(3, src, dst)]))


def sub_reg_mem_abs32(out, reg: str | int, label: str) -> None:
    out.emit(bytes([0x2B, modrm(0, reg, 5)]))
    out.write_abs32(label)


def and_reg_imm32(out, reg: str | int, value: int) -> None:
    if reg_code(reg) == reg_code("eax"):
        out.emit(b"\x25")
    else:
        out.emit(bytes([0x81, modrm(3, 4, reg)]))
    out.emit_u32(value)


def shl_reg_imm8(out, reg: str | int, value: int) -> None:
    out.emit(bytes([0xC1, modrm(3, 4, reg), value & 0xFF]))


def shr_reg_imm8(out, reg: str | int, value: int) -> None:
    out.emit(bytes([0xC1, modrm(3, 5, reg), value & 0xFF]))


def sar_reg_imm8(out, reg: str | int, value: int) -> None:
    out.emit(bytes([0xC1, modrm(3, 7, reg), value & 0xFF]))


def imul_reg_reg_imm32(
    out, dst: str | int, src: str | int, value: int
) -> None:
    out.emit(bytes([0x69, modrm(3, dst, src)]))
    out.emit_u32(value)


def imul_reg(out, src: str | int) -> None:
    out.emit(bytes([0xF7, modrm(3, 5, src)]))


def shrd_reg_reg_imm8(
    out, dst: str | int, src: str | int, value: int
) -> None:
    out.emit(bytes([0x0F, 0xAC, modrm(3, src, dst), value & 0xFF]))


def shld_reg_reg_imm8(
    out, dst: str | int, src: str | int, value: int
) -> None:
    out.emit(bytes([0x0F, 0xA4, modrm(3, src, dst), value & 0xFF]))


def neg_reg(out, reg: str | int) -> None:
    out.emit(bytes([0xF7, modrm(3, 3, reg)]))


def cdq(out) -> None:
    out.emit(b"\x99")


def div_reg(out, reg: str | int) -> None:
    out.emit(bytes([0xF7, modrm(3, 6, reg)]))


def idiv_reg(out, reg: str | int) -> None:
    out.emit(bytes([0xF7, modrm(3, 7, reg)]))


def inc_reg(out, reg: str | int) -> None:
    out.emit_u8(0x40 + reg_code(reg))


def dec_reg(out, reg: str | int) -> None:
    out.emit_u8(0x48 + reg_code(reg))


def dec_mem_abs32(out, label: str) -> None:
    out.emit(b"\xFF\x0D")
    out.write_abs32(label)


def cmp_eax_imm32(out, value: int) -> None:
    out.emit(b"\x3D")
    out.emit_u32(value)


def cmp_reg_imm32(out, reg: str | int, value: int) -> None:
    out.emit(bytes([0x81, modrm(3, 7, reg)]))
    out.emit_u32(value)


def cmp_reg_reg(out, left: str | int, right: str | int) -> None:
    out.emit(bytes([0x39, modrm(3, right, left)]))


def cmp_reg_mem_abs32(out, reg: str | int, label: str) -> None:
    out.emit(bytes([0x3B, modrm(0, reg, 5)]))
    out.write_abs32(label)


def test_eax_eax(out) -> None:
    out.emit(b"\x85\xC0")


def test_reg_reg(out, reg: str | int) -> None:
    out.emit(bytes([0x85, modrm(3, reg, reg)]))


def je_rel32(out, label: str) -> None:
    out.emit(b"\x0F\x84")
    out.write_rel32(label)


def jne_rel32(out, label: str) -> None:
    out.emit(b"\x0F\x85")
    out.write_rel32(label)


def jb_rel32(out, label: str) -> None:
    out.emit(b"\x0F\x82")
    out.write_rel32(label)


def ja_rel32(out, label: str) -> None:
    out.emit(b"\x0F\x87")
    out.write_rel32(label)


def jae_rel32(out, label: str) -> None:
    out.emit(b"\x0F\x83")
    out.write_rel32(label)


def jbe_rel32(out, label: str) -> None:
    out.emit(b"\x0F\x86")
    out.write_rel32(label)


def jl_rel32(out, label: str) -> None:
    out.emit(b"\x0F\x8C")
    out.write_rel32(label)


def jns_rel32(out, label: str) -> None:
    out.emit(b"\x0F\x89")
    out.write_rel32(label)


def emit_function_prologue(out) -> None:
    out.emit(b"\x55")
    out.emit(b"\x89\xE5")


def emit_function_epilogue_ret(out, stack_bytes: int) -> None:
    out.emit(b"\xC9")
    ret_imm16(out, stack_bytes)


def emit_utf16z(out, value: str) -> None:
    out.emit(value.encode("utf-16le"))
    out.emit_u16(0)


def emit_asciiz(out, value: str) -> None:
    out.emit(value.encode("ascii"))
    out.emit_u8(0)


def mov_al_ptr_esi(out) -> None:
    out.emit(b"\x8A\x06")


def mov_dl_ptr_esi(out) -> None:
    out.emit(b"\x8A\x16")


def mov_ptr_edi_al(out) -> None:
    out.emit(b"\x88\x07")


def mov_ptr_edi_dl(out) -> None:
    out.emit(b"\x88\x17")


def mov_ptr_esi_dl(out) -> None:
    out.emit(b"\x88\x16")


def cmp_al_imm8(out, value: int) -> None:
    out.emit(b"\x3C")
    out.emit_u8(value)


def add_dl_imm8(out, value: int) -> None:
    out.emit(b"\x80\xC2")
    out.emit_u8(value)


def mov_byte_ptr_edi_imm8(out, value: int) -> None:
    out.emit(b"\xC6\x07")
    out.emit_u8(value)


def call_rel32(out, label: str) -> None:
    out.emit(b"\xE8")
    out.write_rel32(label)


def jmp_rel32(out, label: str) -> None:
    out.emit(b"\xE9")
    out.write_rel32(label)


def call_abs32_ptr(out, label: str) -> None:
    out.emit(b"\xFF\x15")
    out.write_abs32(label)


def call_import(out, dll: str, function: str) -> None:
    call_abs32_ptr(out, out.add_import(dll, function))
