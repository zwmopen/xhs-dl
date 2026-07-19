from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IOS = ROOT / "ios"
LEGACY = IOS / "RedSweetPotatoDownloadLegacy"


def test_ios_project_targets_iphone_6_and_builds_only_legacy_client():
    project = (IOS / "project.yml").read_text(encoding="utf-8")

    assert 'iOS: "12.0"' in project
    assert "path: RedSweetPotatoDownloadLegacy" in project
    assert "path: RedSweetPotatoDownload/Assets.xcassets" in project


def test_legacy_client_avoids_apis_unavailable_on_ios_12():
    swift_files = list(LEGACY.rglob("*.swift"))
    assert swift_files, "legacy iOS client is missing"
    source = "\n".join(path.read_text(encoding="utf-8") for path in swift_files)

    for forbidden in (
        "import SwiftUI",
        "import UniformTypeIdentifiers",
        " async ",
        " await ",
        "actor ",
        "Task {",
        "@main",
    ):
        assert forbidden not in source

    assert "@UIApplicationMain" in source
    assert "UIDocumentPickerViewController" in source


def test_legacy_interface_keeps_product_language_and_settings():
    html = (LEGACY / "Resources" / "index.html").read_text(encoding="utf-8")

    for label in (
        "红薯下载",
        "粘贴并采集",
        "开始采集",
        "设置",
        "选择下载目录",
        "检测更新",
        "使用说明",
    ):
        assert label in html


def test_ci_rejects_an_ipa_that_drops_iphone_6_support():
    workflow = (ROOT / ".github" / "workflows" / "ios-build.yml").read_text(
        encoding="utf-8"
    )

    assert 'info["MinimumOSVersion"] == "12.0"' in workflow
