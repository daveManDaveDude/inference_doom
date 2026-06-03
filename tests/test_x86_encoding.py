import unittest

from tools import x86
from tools.pe32 import PE32


class X86EncodingTests(unittest.TestCase):
    def test_basic_instruction_bytes(self) -> None:
        self.assertEqual(
            x86.mov_reg_imm32_bytes("eax", 0x12345678),
            b"\xB8\x78\x56\x34\x12",
        )
        self.assertEqual(x86.mov_reg_imm32_bytes("ecx", 0), b"\xB9\x00\x00\x00\x00")
        self.assertEqual(x86.push_imm32_bytes(0xAABBCCDD), b"\x68\xDD\xCC\xBB\xAA")
        self.assertEqual(x86.xor_reg_reg_bytes("eax", "eax"), b"\x31\xC0")
        self.assertEqual(x86.ret_bytes(), b"\xC3")

    def test_stage_helper_instruction_bytes(self) -> None:
        class Sink:
            def __init__(self) -> None:
                self.data = bytearray()

            def emit(self, data: bytes) -> None:
                self.data.extend(data)

            def emit_u8(self, value: int) -> None:
                self.data.append(value & 0xFF)

            def emit_u32(self, value: int) -> None:
                self.data.extend((value & 0xFFFFFFFF).to_bytes(4, "little"))

        sink = Sink()
        x86.movsx_reg_word_ptr_reg_disp8(sink, "eax", "esi", 2)
        x86.mov_word_ptr_reg_disp8_ax(sink, "edi", 16)
        x86.imul_reg_reg_imm32(sink, "ebx", "eax", 40)
        x86.movzx_reg_byte_ptr_reg(sink, "eax", "esi")

        self.assertEqual(
            bytes(sink.data),
            b"\x0F\xBF\x46\x02\x66\x89\x47\x10\x69\xD8\x28\x00\x00\x00\x0F\xB6\x06",
        )

    def test_stage03_fixedmul_helper_instruction_bytes(self) -> None:
        class Sink:
            def __init__(self) -> None:
                self.data = bytearray()

            def emit(self, data: bytes) -> None:
                self.data.extend(data)

        sink = Sink()
        x86.imul_reg(sink, "ecx")
        x86.shrd_reg_reg_imm8(sink, "eax", "edx", 16)
        x86.shld_reg_reg_imm8(sink, "edx", "eax", 16)

        self.assertEqual(bytes(sink.data), b"\xF7\xE9\x0F\xAC\xD0\x10\x0F\xA4\xC2\x10")

    def test_rel32_fixup_points_to_label(self) -> None:
        pe = PE32()

        pe.label("entry")
        x86.call_rel32(pe, "target")
        x86.ret(pe)
        pe.label("target")
        x86.ret(pe)

        pe.build("entry")

        self.assertEqual(pe.section[:7], b"\xE8\x01\x00\x00\x00\xC3\xC3")


if __name__ == "__main__":
    unittest.main()
