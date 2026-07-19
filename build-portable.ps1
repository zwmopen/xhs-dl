param(
    [string]$Version = "2.4.0"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path $PSScriptRoot).Path
$ProductName = -join ([char[]](0x7EA2, 0x85AF, 0x4E0B, 0x8F7D))
$BuildRoot = Join-Path $ProjectRoot "build\portable"
$OutputRoot = Join-Path $BuildRoot "output"
$StageRoot = Join-Path $BuildRoot "stage\$ProductName-portable-v$Version"
$InstallRoot = Join-Path $ProjectRoot "dist\$ProductName-v$Version-portable"
$ExeName = "$ProductName.exe"

foreach ($target in @($BuildRoot, $OutputRoot, $StageRoot, $InstallRoot)) {
    $full = [IO.Path]::GetFullPath($target)
    if (-not $full.StartsWith($ProjectRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe build path: $full"
    }
}

python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name $ProductName `
    --icon (Join-Path $ProjectRoot "assets\red-sweet-potato-download.ico") `
    --paths $ProjectRoot `
    --collect-all customtkinter `
    --add-data "$(Join-Path $ProjectRoot 'xhs_dl\engine_bridge.py');xhs_dl" `
    --distpath $OutputRoot `
    --workpath (Join-Path $BuildRoot "work") `
    --specpath (Join-Path $BuildRoot "spec") `
    (Join-Path $ProjectRoot "xhs_dl\portable.py")

if (Test-Path -LiteralPath $StageRoot) {
    Remove-Item -LiteralPath $StageRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $StageRoot -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $OutputRoot $ExeName) -Destination $StageRoot
Copy-Item -LiteralPath (Join-Path $ProjectRoot "setup-v2.ps1") -Destination $StageRoot
Copy-Item -LiteralPath (Join-Path $ProjectRoot "install-engine.bat") -Destination $StageRoot
Copy-Item -LiteralPath (Join-Path $ProjectRoot "PORTABLE-GUIDE.md") -Destination $StageRoot
Copy-Item -LiteralPath (Join-Path $ProjectRoot "LICENSE") -Destination $StageRoot

if (Test-Path -LiteralPath $InstallRoot) {
    Remove-Item -LiteralPath $InstallRoot -Recurse -Force
}
Copy-Item -LiteralPath $StageRoot -Destination $InstallRoot -Recurse

$Archive = Join-Path $ProjectRoot "dist\$ProductName-v$Version-portable-windows.zip"
if (Test-Path -LiteralPath $Archive) {
    Remove-Item -LiteralPath $Archive -Force
}
Compress-Archive -LiteralPath $StageRoot -DestinationPath $Archive -CompressionLevel Optimal
Write-Host "Portable package: $Archive"
