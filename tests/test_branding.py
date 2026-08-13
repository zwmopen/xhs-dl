from pathlib import Path

from xhs_dl.branding import APP_NAME, LEGACY_APP_NAMES, SKILL_NAME


ROOT = Path(__file__).resolve().parents[1]


def test_primary_brand_is_universal_downloader():
    assert APP_NAME == "万能下载器"
    assert SKILL_NAME == "universal-downloader"
    assert "小红书抖音下载" in LEGACY_APP_NAMES


def test_windows_surfaces_use_primary_brand():
    desktop = (ROOT / "xhs_dl" / "desktop" / "app.py").read_text(encoding="utf-8")
    web = (ROOT / "xhs_dl" / "web" / "app.py").read_text(encoding="utf-8")
    build = (ROOT / "build-portable.ps1").read_text(encoding="utf-8")

    assert 'self.title(APP_NAME)' in desktop
    assert 'text=APP_NAME' in desktop
    assert "__APP_NAME__" in web
    assert 'universal-downloader-v$Version-windows-portable.zip' in build


def test_primary_skill_has_new_identity_and_legacy_skill_is_compatibility_only():
    primary = ROOT / "skills" / "universal-downloader"
    legacy = ROOT / "skills" / "xhs-download"
    primary_text = (primary / "SKILL.md").read_text(encoding="utf-8")
    legacy_text = (legacy / "SKILL.md").read_text(encoding="utf-8")

    assert "name: universal-downloader" in primary_text
    assert "# 万能下载器" in primary_text
    assert "name: xhs-download" in legacy_text
    assert "universal-downloader" in legacy_text
    assert not (legacy / "scripts" / "download.py").exists()


def test_mobile_display_names_are_updated_without_changing_app_identity():
    android_strings = (
        ROOT / "android" / "app" / "src" / "main" / "res" / "values" / "strings.xml"
    ).read_text(encoding="utf-8")
    android_build = (ROOT / "android" / "app" / "build.gradle").read_text(encoding="utf-8")
    ios_plist = (ROOT / "ios" / "RedSweetPotatoDownload" / "Info.plist").read_text(encoding="utf-8")
    ios_project = (ROOT / "ios" / "project.yml").read_text(encoding="utf-8")

    assert '<string name="app_name">万能下载器</string>' in android_strings
    assert "applicationId 'com.zwmopen.xhsdl'" in android_build
    assert "<string>万能下载器</string>" in ios_plist
    assert "PRODUCT_BUNDLE_IDENTIFIER: com.zwmopen.redsweetpotatodownload" in ios_project
