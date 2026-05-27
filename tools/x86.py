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


def ret(out) -> None:
    out.emit(ret_bytes())


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
