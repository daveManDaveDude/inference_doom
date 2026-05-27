# Shareware Doom Pipeline

This pipeline downloads the Doom shareware IWAD, verifies it, builds the Windows reference engine, and runs the shareware episode.

The original id Software Doom source release is GPL licensed, but the released code is the Linux source tree, not the original DOS or Windows executable source. On Windows, this repository uses the source-built Chocolate Doom reference engine to run the original Doom shareware IWAD faithfully.

## Inputs

| Item | Pin |
| --- | --- |
| Doom shareware package | `doom-wad-shareware_1.9.fixed-5_all.deb` |
| Package URL | `https://ftp.debian.org/debian/pool/non-free/d/doom-wad-shareware/doom-wad-shareware_1.9.fixed-5_all.deb` |
| Package SHA256 | `5802f176c0303e228095b5312def53de602781cf4c53e79842257484a0d9e938` |
| Extracted IWAD | `doom1.wad` |
| IWAD SHA256 | `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771` |
| Reference engine | `chocolate-doom-3.1.1` |

## One Command

From PowerShell at the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_shareware_doom.ps1 -Launch
```

If MSYS2 dependencies still need to be installed, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_shareware_doom.ps1 -InstallDependencies -Launch
```

## Separate Steps

Download and verify the IWAD:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_doom_shareware.ps1
```

Build and stage the reference engine:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_reference_chocolate_doom.ps1
```

Run Doom shareware:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_doom_shareware.ps1
```

The launcher defaults to `-nosound` because that is the most reliable smoke-test mode on this Windows setup. To try audio, pass `-Sound`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_doom_shareware.ps1 -Sound
```

Or run the executable directly:

```powershell
& "C:\vibe\inference_doom\reference\chocolate-doom\pkg\win32\staging-doom\chocolate-doom.exe" -iwad "C:\vibe\inference_doom\third_party\doom_shareware\doom1.wad" -window -nosound
```

## Expected Paths

```text
C:\vibe\inference_doom\third_party\doom_shareware\doom1.wad
C:\vibe\inference_doom\reference\chocolate-doom\pkg\win32\staging-doom\chocolate-doom.exe
```

## Notes

`doom1.wad` is the shareware IWAD and contains only the first episode. It should stay out of git along with other downloaded game data.

## Sources

- Debian `doom-wad-shareware` package: `https://packages.debian.org/sid/games/doom-wad-shareware`
- Debian package pool: `https://ftp.debian.org/debian/pool/non-free/d/doom-wad-shareware/`
- DoomWiki `DOOM1.WAD` hashes: `https://doomwiki.org/wiki/DOOM1.WAD`
- id Software Doom source release: `https://github.com/id-Software/DOOM`
