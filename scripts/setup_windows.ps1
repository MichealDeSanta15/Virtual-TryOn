$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
function Invoke-Checked { param([scriptblock]$Command) & $Command; if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE" } }
Write-Host "FORM / EdgeAI - Windows setup (Python 3.11, NVIDIA RTX 50-series)"
Invoke-Checked { py -3.11 -m venv .venv }
$python = Join-Path $PWD ".venv\Scripts\python.exe"
Invoke-Checked { & $python -m pip install --upgrade pip }
# Keep this pair matched. CUDA 12.8 supports Blackwell; no local CUDA toolkit needed for wheels.
Invoke-Checked { & $python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128 }
Invoke-Checked { & $python -m pip install -r requirements-ai.txt -r requirements-dev.txt }
Invoke-Checked { & $python -m pip install -e . --no-deps }
Invoke-Checked { & $python -m pip check }
Write-Host "Environment installed. Review docs/LICENSES.md, then:"
Write-Host ".\.venv\Scripts\python.exe scripts\download_models.py --accept-research-licenses"
Write-Host ".\.venv\Scripts\python.exe scripts\doctor.py"
Write-Host ".\.venv\Scripts\python.exe main.py"
