import struct
import unittest

from tools.emit_pe32 import build_exit_process_exe
from tools.pe32 import IMAGE_BASE


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def read_c_string(data: bytes, offset: int) -> bytes:
    end = data.index(b"\x00", offset)
    return data[offset:end]


def section_bounds(image: bytes) -> tuple[int, int, int, int]:
    pe_offset = u32(image, 0x3C)
    section_header = pe_offset + 4 + 20 + 0xE0
    virtual_size = u32(image, section_header + 8)
    virtual_address = u32(image, section_header + 12)
    raw_size = u32(image, section_header + 16)
    raw_offset = u32(image, section_header + 20)
    return virtual_address, max(virtual_size, raw_size), raw_offset, raw_size


def rva_to_file_offset(image: bytes, rva: int) -> int:
    virtual_address, mapped_size, raw_offset, _raw_size = section_bounds(image)
    if virtual_address <= rva < virtual_address + mapped_size:
        return raw_offset + (rva - virtual_address)
    raise ValueError(f"RVA is outside .text: 0x{rva:08x}")


def import_directory(image: bytes) -> tuple[int, int]:
    pe_offset = u32(image, 0x3C)
    optional_offset = pe_offset + 4 + 20
    data_directory = optional_offset + 96 + 8
    return u32(image, data_directory), u32(image, data_directory + 4)


class EmittedImportTests(unittest.TestCase):
    def test_import_descriptor_names_exit_process(self) -> None:
        image = build_exit_process_exe()
        import_rva, import_size = import_directory(image)

        self.assertNotEqual(import_rva, 0)
        self.assertNotEqual(import_size, 0)

        descriptor_offset = rva_to_file_offset(image, import_rva)
        original_first_thunk, _stamp, _chain, name_rva, first_thunk = struct.unpack_from(
            "<IIIII", image, descriptor_offset
        )

        self.assertNotEqual(original_first_thunk, 0)
        self.assertNotEqual(first_thunk, 0)
        self.assertEqual(
            read_c_string(image, rva_to_file_offset(image, name_rva)),
            b"KERNEL32.dll",
        )
        self.assertEqual(image[descriptor_offset + 20 : descriptor_offset + 40], b"\x00" * 20)

        hint_name_rva = u32(image, rva_to_file_offset(image, first_thunk))
        hint_name_offset = rva_to_file_offset(image, hint_name_rva)
        self.assertEqual(u16(image, hint_name_offset), 0)
        self.assertEqual(read_c_string(image, hint_name_offset + 2), b"ExitProcess")

    def test_iat_call_uses_absolute_iat_slot(self) -> None:
        image = build_exit_process_exe()
        import_rva, _import_size = import_directory(image)
        descriptor_offset = rva_to_file_offset(image, import_rva)
        first_thunk = u32(image, descriptor_offset + 16)

        _va, _mapped_size, raw_offset, raw_size = section_bounds(image)
        text = image[raw_offset : raw_offset + raw_size]
        call_offset = text.index(b"\xFF\x15")
        called_address = u32(image, raw_offset + call_offset + 2)

        self.assertEqual(called_address, IMAGE_BASE + first_thunk)


if __name__ == "__main__":
    unittest.main()
