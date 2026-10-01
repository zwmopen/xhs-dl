from pathlib import Path


def test_desktop_build_defaults_to_onedir_and_keeps_onefile_option():
    script = (Path(__file__).resolve().parents[1] / 'build-portable.ps1').read_text(encoding='utf-8')
    assert '[string]$Layout = "onedir"' in script
    assert '"--$Layout"' in script
    assert 'Copy-Item -LiteralPath $BuiltApp -Destination $StageRoot -Recurse' in script
