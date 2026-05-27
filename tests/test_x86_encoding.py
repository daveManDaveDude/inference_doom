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
