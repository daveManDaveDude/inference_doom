from __future__ import annotations

import argparse
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import x86
from tools.pe32 import PE32


def build_exit_process_exe() -> bytes:
    pe = PE32()

    pe.label("entry")
    x86.push_imm32(pe, 0)
    x86.call_import(pe, "KERNEL32.dll", "ExitProcess")
    x86.ret(pe)

    return pe.build("entry")


def write_exit_process_exe(path: str | Path) -> bytes:
    image = build_exit_process_exe()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(image)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit a tiny PE32 GUI executable with an explicit import table."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="build/phase02_exit.exe",
        help="path to write, default: build/phase02_exit.exe",
    )
    args = parser.parse_args()
    write_exit_process_exe(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
