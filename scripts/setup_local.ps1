# Bootstrap a repo-local virtual environment and install every dev dependency.
#
# Deterministic on Windows even when the WindowsApps `python` launcher is
# unavailable (it can fail with a "terminated logon session" in some sessions):
# this script discovers a real interpreter, creates `.venv`, and installs
# requirements-dev.txt into it.
#
#   powershell -ExecutionPolicy Bypass -File scripts\setup_local.ps1
#   .\.venv\Scripts\python.exe scripts\check_deps.py
#   .\.venv\Scripts\python.exe -m pytest

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$env:PYTHONUTF8 = "1"

function Find-Python {
    $store = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.1*\python.exe" `
        -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
    if ($store) { return $store.FullName }
    $launcher = Get-Command python -ErrorAction SilentlyContinue
    if ($launcher) { return $launcher.Source }
    throw "No usable Python interpreter found. Install Python 3.11+."
}

if (-not (Test-Path $VenvPython)) {
    $Python = Find-Python
    Write-Host "Creating .venv from $Python"
    & $Python -m venv (Join-Path $Root ".venv")
    if (-not (Test-Path $VenvPython)) { throw ".venv creation failed" }
}

Write-Host "Installing development dependencies..."
& $VenvPython -m pip install --quiet --upgrade pip
& $VenvPython -m pip install --quiet -r (Join-Path $Root "requirements-dev.txt")

Write-Host ""
Write-Host "Provisioned: $VenvPython"
Write-Host "Verify:      .\.venv\Scripts\python.exe scripts\check_deps.py"
Write-Host "Run tests:   .\.venv\Scripts\python.exe -m pytest"
