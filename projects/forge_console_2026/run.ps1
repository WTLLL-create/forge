$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $here

$py = $env:FORGE_PYTHON
if (-not $py) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Python not found. Install Python 3.11+ and dependencies, or set FORGE_PYTHON."
    }
    $py = $cmd.Source
}
if (-not (Test-Path -LiteralPath $py)) {
    throw "Python runtime not found: $py. Set FORGE_PYTHON to a Python with requirements.txt installed."
}

& $py -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
