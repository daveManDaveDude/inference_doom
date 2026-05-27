# Build Reference Chocolate Doom on Windows

This Phase 1 reference path builds a normal Chocolate Doom executable on Windows and runs it with the pinned Freedoom IWADs. This is intentionally a compiled reference engine; later project phases handle emitted executables separately.

## Pinned Inputs

| Item | Pin |
| --- | --- |
| Freedoom | `v0.13.0` |
| Freedoom archive | `https://github.com/freedoom/freedoom/releases/download/v0.13.0/freedoom-0.13.0.zip` |
| Freedoom SHA256 | `3f9b264f3e3ce503b4fb7f6bdcb1f419d93c7b546f4df3e874dd878db9688f59` |
| Chocolate Doom | `chocolate-doom-3.1.1` |

## 1. Download Freedoom

From PowerShell at the repository root:

```powershell
.\scripts\setup_freedoom.ps1
```

If the local execution policy blocks direct script execution, use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_freedoom.ps1
```

Or call the Python script directly:

```powershell
py -3 .\scripts\setup_freedoom.py
```

The script verifies the archive SHA256 and writes:

```text
third_party\freedoom\freedoom1.wad
third_party\freedoom\freedoom2.wad
```

## 2. Install MSYS2

Install MSYS2 from `https://www.msys2.org/`, then open the MSYS2 shell and update packages:

```sh
pacman -Syu
```

If MSYS2 asks you to close the shell, close it, reopen MSYS2, and run:

```sh
pacman -Syu
```

For the build itself, open the `MSYS2 MinGW 32-bit` shell. The prompt should include `MINGW32`.

## 3. Install Build Dependencies

In the `MSYS2 MinGW 32-bit` shell:

```sh
pacman -S --needed base-devel msys2-devel mingw-w64-i686-toolchain \
  mingw-w64-i686-SDL2 mingw-w64-i686-SDL2_net \
  mingw-w64-i686-SDL2_mixer mingw-w64-i686-libpng \
  mingw-w64-i686-cmake mingw-w64-i686-ninja \
  automake-wrapper autoconf python zip git
```

Press Enter when `pacman` asks which packages from a group to install.

## 4. Clone and Build

Use the MSYS2 path for this repository. For `C:\vibe\inference_doom`, that path is `/c/vibe/inference_doom`.

```sh
cd /c/vibe/inference_doom
mkdir -p reference
cd reference

git clone https://github.com/chocolate-doom/chocolate-doom.git chocolate-doom
cd chocolate-doom
git checkout chocolate-doom-3.1.1

cmake -S . -B build-mingw32 -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/mingw32/bin/gcc.exe
cmake --build build-mingw32 --config Release

mkdir -p pkg/win32/staging-doom
cp build-mingw32/src/chocolate-doom.exe pkg/win32/staging-doom/
cp build-mingw32/src/chocolate-setup.exe pkg/win32/staging-doom/chocolate-doom-setup.exe
cp /mingw32/bin/libpng16-16.dll /mingw32/bin/SDL2.dll \
  /mingw32/bin/SDL2_mixer.dll /mingw32/bin/SDL2_net.dll \
  /mingw32/bin/libFLAC.dll /mingw32/bin/libgcc_s_dw2-1.dll \
  /mingw32/bin/libmpg123-0.dll /mingw32/bin/libogg-0.dll \
  /mingw32/bin/libopus-0.dll /mingw32/bin/libopusfile-0.dll \
  /mingw32/bin/libvorbis-0.dll /mingw32/bin/libvorbisfile-3.dll \
  /mingw32/bin/libwavpack-1.dll /mingw32/bin/libwinpthread-1.dll \
  /mingw32/bin/libxmp.dll /mingw32/bin/zlib1.dll \
  pkg/win32/staging-doom/
```

The Windows reference executable should be here:

```text
C:\vibe\inference_doom\reference\chocolate-doom\pkg\win32\staging-doom\chocolate-doom.exe
```

## 5. Run with Freedoom

From PowerShell at the repository root:

```powershell
& "C:\vibe\inference_doom\reference\chocolate-doom\pkg\win32\staging-doom\chocolate-doom.exe" -iwad "C:\vibe\inference_doom\third_party\freedoom\freedoom2.wad" -window
```

Phase 1 uses Freedoom as the legal asset source.

## Upstream References

- Freedoom download page: `https://freedoom.github.io/download.html`
- Freedoom release: `https://github.com/freedoom/freedoom/releases/tag/v0.13.0`
- Chocolate Doom Windows build guide: `https://www.chocolate-doom.org/wiki/index.php/Building_Chocolate_Doom_on_Windows`
- Chocolate Doom releases: `https://github.com/chocolate-doom/chocolate-doom/releases`
- MSYS2: `https://www.msys2.org/`
