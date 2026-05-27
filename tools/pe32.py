from __future__ import annotations

import struct
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path


IMAGE_BASE = 0x00400000
SECTION_RVA = 0x1000
SECTION_ALIGNMENT = 0x1000
FILE_ALIGNMENT = 0x200
GUI_SUBSYSTEM = 2
RESOURCE_DIRECTORY_INDEX = 2
RT_MANIFEST = 24
APPLICATION_MANIFEST_ID = 1
LANG_EN_US = 0x0409

AS_INVOKER_MANIFEST = (
    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
    b'<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">\r\n'
    b'  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">\r\n'
    b"    <security>\r\n"
    b"      <requestedPrivileges>\r\n"
    b'        <requestedExecutionLevel level="asInvoker" uiAccess="false"/>\r\n'
    b"      </requestedPrivileges>\r\n"
    b"    </security>\r\n"
    b"  </trustInfo>\r\n"
    b"</assembly>\r\n"
)


def align(value: int, alignment: int) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


@dataclass(frozen=True)
class Fixup:
    kind: str
    offset: int
    label: str


class PE32:
    """Small one-section PE32 writer for hand-emitted x86 programs."""

    def __init__(
        self,
        *,
        image_base: int = IMAGE_BASE,
        section_rva: int = SECTION_RVA,
        section_alignment: int = SECTION_ALIGNMENT,
        file_alignment: int = FILE_ALIGNMENT,
    ) -> None:
        self.image_base = image_base
        self.section_rva = section_rva
        self.section_alignment = section_alignment
        self.file_alignment = file_alignment

        self.section = bytearray()
        self._labels: dict[str, int] = {}
        self._fixups: list[Fixup] = []
        self._imports: OrderedDict[str, list[str]] = OrderedDict()

        self.import_directory_rva = 0
        self.import_directory_size = 0
        self.resource_directory_rva = 0
        self.resource_directory_size = 0
        self._manifest_resource: bytes | None = None
        self._imports_emitted = False
        self._resources_emitted = False
        self._built_image: bytes | None = None

    def tell(self) -> int:
        return len(self.section)

    def label(self, name: str) -> None:
        if name in self._labels:
            raise ValueError(f"label already defined: {name}")
        self._labels[name] = self.tell()

    def emit(self, data: bytes | bytearray) -> None:
        self.section.extend(data)

    def emit_u8(self, value: int) -> None:
        self.section.append(value & 0xFF)

    def emit_u16(self, value: int) -> None:
        self.section.extend(struct.pack("<H", value & 0xFFFF))

    def emit_u32(self, value: int) -> None:
        self.section.extend(struct.pack("<I", value & 0xFFFFFFFF))

    def emit_zeros(self, count: int) -> None:
        self.section.extend(b"\x00" * count)

    def align_section(self, alignment: int, fill: int = 0) -> None:
        while len(self.section) % alignment:
            self.emit_u8(fill)

    def write_abs32(self, label: str) -> int:
        offset = self.tell()
        self.emit_u32(0)
        self._fixups.append(Fixup("abs32", offset, label))
        return offset

    def write_rva32(self, label: str) -> int:
        offset = self.tell()
        self.emit_u32(0)
        self._fixups.append(Fixup("rva32", offset, label))
        return offset

    def write_rel32(self, label: str) -> int:
        offset = self.tell()
        self.emit_u32(0)
        self._fixups.append(Fixup("rel32", offset, label))
        return offset

    def label_offset(self, name: str) -> int:
        return self._labels[name]

    def rva_of(self, name: str) -> int:
        return self.section_rva + self.label_offset(name)

    def va_of(self, name: str) -> int:
        return self.image_base + self.rva_of(name)

    def import_label(self, dll: str, function: str) -> str:
        return f"__imp__{dll}!{function}"

    def add_import(self, dll: str, function: str) -> str:
        functions = self._imports.setdefault(dll, [])
        if function not in functions:
            functions.append(function)
        return self.import_label(dll, function)

    def add_as_invoker_manifest(self) -> None:
        if self._built_image is not None:
            raise ValueError("cannot add resources after build")
        self._manifest_resource = AS_INVOKER_MANIFEST

    def build(self, entry_label: str) -> bytes:
        if self._built_image is not None:
            return self._built_image
        if entry_label not in self._labels:
            raise ValueError(f"entry label not defined: {entry_label}")

        self._emit_import_table()
        self._emit_resource_table()
        self._apply_fixups()

        virtual_size = len(self.section)
        raw_size = align(virtual_size, self.file_alignment)
        size_of_headers = align(0x80 + 4 + 20 + 0xE0 + 40, self.file_alignment)
        size_of_image = align(self.section_rva + virtual_size, self.section_alignment)
        entry_rva = self.rva_of(entry_label)

        headers = self._headers(entry_rva, virtual_size, raw_size, size_of_headers, size_of_image)
        image = bytearray(headers)
        image.extend(self.section)
        image.extend(b"\x00" * (raw_size - len(self.section)))
        self._built_image = bytes(image)
        return self._built_image

    def write(self, path: str | Path, entry_label: str) -> bytes:
        image = self.build(entry_label)
        Path(path).write_bytes(image)
        return image

    def _emit_import_table(self) -> None:
        if self._imports_emitted:
            return
        self._imports_emitted = True
        if not self._imports:
            return

        self.align_section(4)
        import_start = self.tell()
        self.label("__import_directory")

        descriptor_offsets: list[int] = []
        for _dll in self._imports:
            descriptor_offsets.append(self.tell())
            self.emit_zeros(20)
        self.emit_zeros(20)

        descriptor_records: list[tuple[int, str, str, str]] = []
        for dll_index, (dll, functions) in enumerate(self._imports.items()):
            ilt_label = f"__import_ilt_{dll_index}"
            iat_label = f"__import_iat_{dll_index}"
            dll_name_label = f"__import_dll_name_{dll_index}"
            hint_labels = [f"__import_hint_{dll_index}_{i}" for i in range(len(functions))]

            self.align_section(4)
            self.label(ilt_label)
            for hint_label in hint_labels:
                self.write_rva32(hint_label)
            self.emit_u32(0)

            self.align_section(4)
            self.label(iat_label)
            for function, hint_label in zip(functions, hint_labels):
                self.label(self.import_label(dll, function))
                self.write_rva32(hint_label)
            self.emit_u32(0)

            for function, hint_label in zip(functions, hint_labels):
                self.align_section(2)
                self.label(hint_label)
                self.emit_u16(0)
                self.emit(function.encode("ascii") + b"\x00")

            self.align_section(2)
            self.label(dll_name_label)
            self.emit(dll.encode("ascii") + b"\x00")

            descriptor_records.append(
                (descriptor_offsets[dll_index], ilt_label, dll_name_label, iat_label)
            )

        for descriptor_offset, ilt_label, dll_name_label, iat_label in descriptor_records:
            struct.pack_into(
                "<IIIII",
                self.section,
                descriptor_offset,
                self.rva_of(ilt_label),
                0,
                0,
                self.rva_of(dll_name_label),
                self.rva_of(iat_label),
            )

        self.import_directory_rva = self.rva_of("__import_directory")
        self.import_directory_size = self.tell() - import_start

    def _emit_resource_table(self) -> None:
        if self._resources_emitted:
            return
        self._resources_emitted = True
        if self._manifest_resource is None:
            return

        self.align_section(4)
        resource_start = self.tell()
        root_rva = self.section_rva + resource_start

        root_offset = 0
        type_dir_offset = 24
        name_dir_offset = 48
        data_entry_offset = 72
        data_offset = 88

        self.emit(self._resource_directory_header(id_entries=1))
        self.emit_u32(RT_MANIFEST)
        self.emit_u32(0x80000000 | type_dir_offset)

        self.emit(self._resource_directory_header(id_entries=1))
        self.emit_u32(APPLICATION_MANIFEST_ID)
        self.emit_u32(0x80000000 | name_dir_offset)

        self.emit(self._resource_directory_header(id_entries=1))
        self.emit_u32(LANG_EN_US)
        self.emit_u32(data_entry_offset)

        manifest_rva = root_rva + data_offset
        self.emit_u32(manifest_rva)
        self.emit_u32(len(self._manifest_resource))
        self.emit_u32(0)
        self.emit_u32(0)

        if self.tell() - resource_start != data_offset:
            raise AssertionError("bad resource manifest layout")
        self.emit(self._manifest_resource)
        self.align_section(4)

        self.resource_directory_rva = root_rva + root_offset
        self.resource_directory_size = self.tell() - resource_start

    @staticmethod
    def _resource_directory_header(*, id_entries: int) -> bytes:
        return struct.pack("<IIHHHH", 0, 0, 0, 0, 0, id_entries)

    def _apply_fixups(self) -> None:
        for fixup in self._fixups:
            if fixup.label not in self._labels:
                raise ValueError(f"fixup target label not defined: {fixup.label}")

            target_rva = self.rva_of(fixup.label)
            if fixup.kind == "abs32":
                value = self.image_base + target_rva
                struct.pack_into("<I", self.section, fixup.offset, value)
            elif fixup.kind == "rva32":
                struct.pack_into("<I", self.section, fixup.offset, target_rva)
            elif fixup.kind == "rel32":
                next_rva = self.section_rva + fixup.offset + 4
                value = target_rva - next_rva
                struct.pack_into("<i", self.section, fixup.offset, value)
            else:
                raise ValueError(f"unknown fixup kind: {fixup.kind}")

    def _headers(
        self,
        entry_rva: int,
        virtual_size: int,
        raw_size: int,
        size_of_headers: int,
        size_of_image: int,
    ) -> bytes:
        dos = bytearray(0x80)
        dos[0:2] = b"MZ"
        struct.pack_into("<I", dos, 0x3C, 0x80)

        coff = struct.pack(
            "<HHIIIHH",
            0x014C,  # IMAGE_FILE_MACHINE_I386
            1,
            0,
            0,
            0,
            0xE0,
            0x010F,
        )

        optional = self._optional_header(
            entry_rva, raw_size, size_of_headers, size_of_image
        )

        section_header = bytearray()
        section_header.extend(b".text\x00\x00\x00")
        section_header.extend(
            struct.pack(
                "<IIIIIIHHI",
                virtual_size,
                self.section_rva,
                raw_size,
                size_of_headers,
                0,
                0,
                0,
                0,
                0xE0000020,
            )
        )

        headers = bytearray()
        headers.extend(dos)
        headers.extend(b"PE\x00\x00")
        headers.extend(coff)
        headers.extend(optional)
        headers.extend(section_header)
        headers.extend(b"\x00" * (size_of_headers - len(headers)))
        return bytes(headers)

    def _optional_header(
        self,
        entry_rva: int,
        size_of_code: int,
        size_of_headers: int,
        size_of_image: int,
    ) -> bytes:
        data = bytearray()

        def u8(value: int) -> None:
            data.append(value & 0xFF)

        def u16(value: int) -> None:
            data.extend(struct.pack("<H", value & 0xFFFF))

        def u32(value: int) -> None:
            data.extend(struct.pack("<I", value & 0xFFFFFFFF))

        u16(0x010B)
        u8(0)
        u8(0)
        u32(size_of_code)
        u32(0)
        u32(0)
        u32(entry_rva)
        u32(self.section_rva)
        u32(self.section_rva)
        u32(self.image_base)
        u32(self.section_alignment)
        u32(self.file_alignment)
        u16(4)
        u16(0)
        u16(0)
        u16(0)
        u16(4)
        u16(0)
        u32(0)
        u32(size_of_image)
        u32(size_of_headers)
        u32(0)
        u16(GUI_SUBSYSTEM)
        u16(0)
        u32(0x00100000)
        u32(0x00001000)
        u32(0x00100000)
        u32(0x00001000)
        u32(0)
        u32(16)

        for index in range(16):
            if index == 1:
                u32(self.import_directory_rva)
                u32(self.import_directory_size)
            elif index == RESOURCE_DIRECTORY_INDEX:
                u32(self.resource_directory_rva)
                u32(self.resource_directory_size)
            else:
                u32(0)
                u32(0)

        if len(data) != 0xE0:
            raise AssertionError(f"bad optional header size: {len(data)}")
        return bytes(data)
