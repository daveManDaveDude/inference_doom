import struct
import unittest

from tools.emit_pe32 import build_exit_process_exe


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


class PE32HeaderTests(unittest.TestCase):
    def test_minimal_exe_has_pe32_gui_headers(self) -> None:
        image = build_exit_process_exe()

        self.assertEqual(image[0:2], b"MZ")

        pe_offset = u32(image, 0x3C)
        self.assertEqual(image[pe_offset : pe_offset + 4], b"PE\x00\x00")
        self.assertEqual(u16(image, pe_offset + 4), 0x014C)

        optional_offset = pe_offset + 4 + 20
        self.assertEqual(u16(image, optional_offset), 0x010B)
        self.assertEqual(u16(image, optional_offset + 68), 2)

    def test_minimal_exe_has_import_directory_rva(self) -> None:
        image = build_exit_process_exe()

        pe_offset = u32(image, 0x3C)
        optional_offset = pe_offset + 4 + 20
        import_directory_offset = optional_offset + 96 + 8

        self.assertNotEqual(u32(image, import_directory_offset), 0)
        self.assertNotEqual(u32(image, import_directory_offset + 4), 0)


if __name__ == "__main__":
    unittest.main()
