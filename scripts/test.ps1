# Run the dependency check and the full test suite with the repo-local venv.
#
#   powershell -ExecutionPolicy Bypass -File scripts\test.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "No .venv found. Run scripts\setup_local.ps1 first."
    exit 1
}

& $VenvPython scripts\check_deps.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $VenvPython -m pytest -q
exit $LASTEXITCODE
