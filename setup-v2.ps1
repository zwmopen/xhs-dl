param(
    [string]$EnginePath = "$(Split-Path -Parent $PSScriptRoot)\XHS_Downloader",
    [string]$EngineRef = "50f9579746de2fbb5bb46c244f680327280c019e"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath "$EnginePath\main.py")) {
    Write-Host "Downloading the local original-media engine..."
    git clone https://github.com/JoeanAmier/XHS_Downloader.git $EnginePath
    git -C $EnginePath checkout --detach $EngineRef
}
else {
    $CurrentRef = (git -C $EnginePath rev-parse HEAD).Trim()
    if ($CurrentRef -ne $EngineRef) {
        throw "Existing engine $CurrentRef differs from verified ref $EngineRef. Review it and pass -EngineRef explicitly."
    }
}

Write-Host "Preparing an isolated Python 3.12 environment..."
python -m pip install --user uv
Push-Location $EnginePath
try {
    python -m uv python install 3.12
    python -m uv sync --no-dev
}
finally {
    Pop-Location
}

Write-Host "Engine setup completed: $EnginePath"
Write-Host "Next: python -m pip install -e $PSScriptRoot"
