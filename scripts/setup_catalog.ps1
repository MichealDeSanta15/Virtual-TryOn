param([switch]$LegacyBrowsers)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Use the existing working EdgeAI .venv, or run setup_windows.ps1 first." }
& $python -m pip install -r requirements-catalog.txt
if ($LASTEXITCODE -ne 0) { throw "Catalog dependency install failed" }
if ($LegacyBrowsers) {
    & $python -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw "Chromium install failed" }
} else {
    Write-Host "Free live stores use HTTP feeds: Chromium is not required. Use -LegacyBrowsers for Amazon/Myntra/Ajio."
}
& $python -m pip install -e . --no-deps
if ($LASTEXITCODE -ne 0) { throw "Editable package update failed" }
Write-Host "Catalog added without changing the pinned torch/diffusers stack."
Write-Host '$env:EDGEAI_MEMORY="staged"'
Write-Host '.\.venv\Scripts\python.exe main.py'
