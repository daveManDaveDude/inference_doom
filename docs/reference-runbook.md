# Reference Runbook

This runbook is the Phase 1 smoke path for proving the compiled reference engine starts with the downloaded Freedoom IWAD.

## Expected Paths

After running `.\scripts\setup_freedoom.ps1`, the asset paths printed by the script should include:

```text
C:\vibe\inference_doom\third_party\freedoom\freedoom1.wad
C:\vibe\inference_doom\third_party\freedoom\freedoom2.wad
```

After building Chocolate Doom with `docs\build-reference-chocolate-doom.md`, the reference executable should be:

```text
C:\vibe\inference_doom\reference\chocolate-doom\pkg\win32\staging-doom\chocolate-doom.exe
```

## Quick Checks

From PowerShell at the repository root:

```powershell
Test-Path .\third_party\freedoom\freedoom1.wad
Test-Path .\third_party\freedoom\freedoom2.wad
Test-Path .\reference\chocolate-doom\pkg\win32\staging-doom\chocolate-doom.exe
Test-Path .\reference\chocolate-doom\pkg\win32\staging-doom\SDL2.dll
```

Each command should print `True`.

## Run Phase 2 IWAD

```powershell
& "C:\vibe\inference_doom\reference\chocolate-doom\pkg\win32\staging-doom\chocolate-doom.exe" -iwad "C:\vibe\inference_doom\third_party\freedoom\freedoom2.wad" -window
```

Expected result:

- A Chocolate Doom window opens.
- Freedoom starts from `freedoom2.wad`.
- The game reaches the title screen or attract/demo loop.

## Run Phase 1 IWAD

```powershell
& "C:\vibe\inference_doom\reference\chocolate-doom\pkg\win32\staging-doom\chocolate-doom.exe" -iwad "C:\vibe\inference_doom\third_party\freedoom\freedoom1.wad" -window
```

Expected result:

- A Chocolate Doom window opens.
- Freedoom starts from `freedoom1.wad`.
- The game reaches the title screen or attract/demo loop.

## Portable PowerShell Form

If the repository is not at `C:\vibe\inference_doom`, use resolved paths:

```powershell
$Repo = (Resolve-Path .).Path
$Engine = Join-Path $Repo "reference\chocolate-doom\pkg\win32\staging-doom\chocolate-doom.exe"
$Iwad = Join-Path $Repo "third_party\freedoom\freedoom2.wad"
& $Engine -iwad $Iwad -window
```

## Proof Notes

When the reference engine starts successfully, record:

```text
Date:
Chocolate Doom tag: chocolate-doom-3.1.1
Freedoom release: v0.13.0
IWAD used:
Command:
Observed result:
Screenshot path, if captured:
```

Commercial DOOM WADs are not required and must not be committed.
