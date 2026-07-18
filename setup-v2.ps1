param(
    [string]$EnginePath = "$(Split-Path -Parent $PSScriptRoot)\XHS_Downloader"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath "$EnginePath\main.py")) {
    Write-Host "正在下载本地无水印引擎..."
    git clone --depth 1 https://github.com/JoeanAmier/XHS_Downloader.git $EnginePath
}

Write-Host "正在准备独立 Python 3.12 环境..."
python -m pip install --user uv
Push-Location $EnginePath
try {
    python -m uv python install 3.12
    python -m uv sync --no-dev
}
finally {
    Pop-Location
}

Write-Host "安装完成。引擎位置: $EnginePath"
Write-Host "可运行：python -m xhs_dl.cli \"小红书分享链接\""
