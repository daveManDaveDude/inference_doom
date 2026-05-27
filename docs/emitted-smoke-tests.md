# Emitted Executable Smoke Tests

These checks cover the no-compiler PE32 executables emitted directly by Python.

## Stage 01 Window

Build the executable from the repository root:

```powershell
py -3 .\tools\emit_stage01_window.py
```

Expected output:

```text
build/stage01_window.exe
```

Manual smoke test:

```powershell
.\build\stage01_window.exe
```

Expected result:

- A visible window opens.
- The title is `Inference Doom - Stage 01 Window`.
- Closing the window exits the process cleanly.

Scripted smoke test:

```powershell
$Exe = (Resolve-Path .\build\stage01_window.exe).Path
$Process = Start-Process -FilePath $Exe -PassThru
$Deadline = (Get-Date).AddSeconds(5)

do {
    Start-Sleep -Milliseconds 100
    $Process.Refresh()
} until ($Process.MainWindowTitle -eq "Inference Doom - Stage 01 Window" -or
         $Process.HasExited -or
         (Get-Date) -gt $Deadline)

if ($Process.HasExited) {
    throw "stage01_window.exe exited before the window appeared"
}

if ($Process.MainWindowTitle -ne "Inference Doom - Stage 01 Window") {
    Stop-Process -Id $Process.Id -Force
    throw "stage01_window.exe did not expose the expected window title"
}

$null = $Process.CloseMainWindow()
if (-not $Process.WaitForExit(3000)) {
    Stop-Process -Id $Process.Id -Force
    throw "stage01_window.exe did not close cleanly"
}

if ($Process.ExitCode -ne 0) {
    throw "stage01_window.exe exited with code $($Process.ExitCode)"
}
```

This path must not invoke a compiler, assembler, linker, CMake, MSBuild, Visual Studio, MinGW, NASM, or external binary tools.
