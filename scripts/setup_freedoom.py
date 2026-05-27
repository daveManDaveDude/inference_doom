#!/usr/bin/env python3
"""Download and extract the pinned Freedoom IWAD assets."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


FREEDOOM_VERSION = "0.13.0"
FREEDOOM_ARCHIVE = f"freedoom-{FREEDOOM_VERSION}.zip"
FREEDOOM_URL = (
    "https://github.com/freedoom/freedoom/releases/download/"
    f"v{FREEDOOM_VERSION}/{FREEDOOM_ARCHIVE}"
)
FREEDOOM_SHA256 = "3f9b264f3e3ce503b4fb7f6bdcb1f419d93c7b546f4df3e874dd878db9688f59"
FREEDOOM_ARCHIVE_ROOT = f"freedoom-{FREEDOOM_VERSION}"
IWAD_NAMES = ("freedoom1.wad", "freedoom2.wad")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_archive_path() -> Path:
    return Path(tempfile.gettempdir()) / "inference_doom" / FREEDOOM_ARCHIVE


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
        headers={"User-Agent": "inference_doom phase1 setup"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        with temp_path.open("wb") as output:
            shutil.copyfileobj(response, output)

    temp_path.replace(destination)


def verify_archive(path: Path) -> str:
    actual = sha256_file(path)
    if actual.lower() != FREEDOOM_SHA256:
        raise RuntimeError(
            "SHA256 mismatch for "
            f"{path}\nexpected: {FREEDOOM_SHA256}\nactual:   {actual}"
        )
    return actual


def find_iwad_member(archive: zipfile.ZipFile, iwad_name: str) -> zipfile.ZipInfo:
    expected = f"{FREEDOOM_ARCHIVE_ROOT}/{iwad_name}"
    try:
        member = archive.getinfo(expected)
    except KeyError as error:
        raise RuntimeError(f"Missing {expected} in {FREEDOOM_ARCHIVE}") from error

    if member.is_dir():
        raise RuntimeError(f"Archive member is a directory, not a WAD: {expected}")

    return member


def extract_iwads(archive_path: Path, destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []

    with zipfile.ZipFile(archive_path) as archive:
        for iwad_name in IWAD_NAMES:
            member = find_iwad_member(archive, iwad_name)
            target = destination / iwad_name
            temp_target = target.with_name(target.name + ".tmp")

            if temp_target.exists():
                temp_target.unlink()

            with archive.open(member) as source, temp_target.open("wb") as output:
                shutil.copyfileobj(source, output)

            temp_target.replace(target)
            extracted.append(target.resolve())

    return extracted


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download Freedoom "
            f"{FREEDOOM_VERSION}, verify SHA256, and extract IWADs."
        )
    )
    parser.add_argument(
        "--archive",
        type=Path,
        help="Use an existing archive instead of downloading the pinned release.",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=repo_root() / "third_party" / "freedoom",
        help="Directory where freedoom1.wad and freedoom2.wad are written.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Redownload the pinned archive even if a cached copy is present.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.archive:
        archive_path = args.archive.resolve()
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")
    else:
        archive_path = default_archive_path()
        if args.force_download or not archive_path.exists():
            print(f"Downloading Freedoom {FREEDOOM_VERSION}: {FREEDOOM_URL}")
            download_file(FREEDOOM_URL, archive_path)
        else:
            try:
                verify_archive(archive_path)
                print(f"Using cached archive: {archive_path}")
            except RuntimeError:
                print(f"Cached archive failed verification, redownloading: {archive_path}")
                download_file(FREEDOOM_URL, archive_path)

    actual_sha256 = verify_archive(archive_path)
    iwad_paths = extract_iwads(archive_path, args.destination.resolve())

    print()
    print(f"Freedoom release: {FREEDOOM_VERSION}")
    print(f"Source URL: {FREEDOOM_URL}")
    print(f"Archive path: {archive_path.resolve()}")
    print(f"Archive SHA256 verified: {actual_sha256}")
    print("Extracted IWAD paths:")
    for path in iwad_paths:
        print(f"  {path}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
