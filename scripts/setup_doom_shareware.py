#!/usr/bin/env python3
"""Download and extract the pinned Doom shareware IWAD."""

from __future__ import annotations

import argparse
import hashlib
import io
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path


PACKAGE_VERSION = "1.9.fixed-5"
PACKAGE_NAME = f"doom-wad-shareware_{PACKAGE_VERSION}_all.deb"
PACKAGE_URL = (
    "https://ftp.debian.org/debian/pool/non-free/d/doom-wad-shareware/"
    f"{PACKAGE_NAME}"
)
PACKAGE_SHA256 = "5802f176c0303e228095b5312def53de602781cf4c53e79842257484a0d9e938"
DOOM1_WAD_SHA256 = "1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771"
DOOM1_WAD_MEMBER = "./usr/share/games/doom/doom1.wad"
AR_MAGIC = b"!<arch>\n"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_package_path() -> Path:
    return Path(tempfile.gettempdir()) / "inference_doom" / PACKAGE_NAME


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_name(destination.name + ".tmp")
    if temp_path.exists():
        temp_path.unlink()

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "inference_doom shareware setup"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        with temp_path.open("wb") as output:
            shutil.copyfileobj(response, output)

    temp_path.replace(destination)


def verify_package(path: Path) -> str:
    actual = sha256_file(path)
    if actual.lower() != PACKAGE_SHA256:
        raise RuntimeError(
            "SHA256 mismatch for "
            f"{path}\nexpected: {PACKAGE_SHA256}\nactual:   {actual}"
        )
    return actual


def ar_members(path: Path) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    with path.open("rb") as handle:
        if handle.read(len(AR_MAGIC)) != AR_MAGIC:
            raise RuntimeError(f"Not a Debian ar archive: {path}")

        while True:
            header = handle.read(60)
            if not header:
                break
            if len(header) != 60:
                raise RuntimeError(f"Truncated ar header in {path}")

            name = header[0:16].decode("ascii").strip().rstrip("/")
            size_text = header[48:58].decode("ascii").strip()
            try:
                size = int(size_text)
            except ValueError as error:
                raise RuntimeError(f"Invalid ar member size: {size_text!r}") from error

            data = handle.read(size)
            if len(data) != size:
                raise RuntimeError(f"Truncated ar member: {name}")
            members[name] = data

            if size % 2:
                handle.seek(1, 1)

    return members


def extract_iwad(package_path: Path, destination: Path) -> Path:
    members = ar_members(package_path)
    data_tar = members.get("data.tar.xz")
    if data_tar is None:
        raise RuntimeError(f"Missing data.tar.xz in {package_path}")

    destination.mkdir(parents=True, exist_ok=True)
    target = destination / "doom1.wad"
    temp_target = target.with_name(target.name + ".tmp")
    if temp_target.exists():
        temp_target.unlink()

    with tarfile.open(fileobj=io.BytesIO(data_tar), mode="r:xz") as archive:
        try:
            member = archive.getmember(DOOM1_WAD_MEMBER)
        except KeyError:
            normalized_target = DOOM1_WAD_MEMBER.lstrip("./")
            member = next(
                (
                    item
                    for item in archive.getmembers()
                    if item.name.lstrip("./") == normalized_target
                ),
                None,
            )
            if member is None:
                raise RuntimeError(f"Missing {DOOM1_WAD_MEMBER} in data.tar.xz")

        source = archive.extractfile(member)
        if source is None:
            raise RuntimeError(f"Archive member is not a file: {member.name}")

        with source, temp_target.open("wb") as output:
            shutil.copyfileobj(source, output)

    actual_wad_sha256 = sha256_file(temp_target)
    if actual_wad_sha256.lower() != DOOM1_WAD_SHA256:
        temp_target.unlink(missing_ok=True)
        raise RuntimeError(
            "SHA256 mismatch for extracted doom1.wad\n"
            f"expected: {DOOM1_WAD_SHA256}\nactual:   {actual_wad_sha256}"
        )

    temp_target.replace(target)
    return target.resolve()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download the Debian Doom shareware package, verify SHA256, "
            "and extract doom1.wad."
        )
    )
    parser.add_argument(
        "--package",
        type=Path,
        help="Use an existing .deb package instead of downloading the pinned one.",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=repo_root() / "third_party" / "doom_shareware",
        help="Directory where doom1.wad is written.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Redownload the pinned package even if a cached copy is present.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.package:
        package_path = args.package.resolve()
        if not package_path.exists():
            raise FileNotFoundError(f"Package not found: {package_path}")
    else:
        package_path = default_package_path()
        if args.force_download or not package_path.exists():
            print(f"Downloading Doom shareware package: {PACKAGE_URL}")
            download_file(PACKAGE_URL, package_path)
        else:
            try:
                verify_package(package_path)
                print(f"Using cached package: {package_path}")
            except RuntimeError:
                print(f"Cached package failed verification, redownloading: {package_path}")
                download_file(PACKAGE_URL, package_path)

    actual_package_sha256 = verify_package(package_path)
    iwad_path = extract_iwad(package_path, args.destination.resolve())

    print()
    print(f"Doom shareware package: {PACKAGE_NAME}")
    print(f"Source URL: {PACKAGE_URL}")
    print(f"Package path: {package_path.resolve()}")
    print(f"Package SHA256 verified: {actual_package_sha256}")
    print(f"IWAD SHA256 verified: {DOOM1_WAD_SHA256}")
    print("Extracted IWAD path:")
    print(f"  {iwad_path}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
