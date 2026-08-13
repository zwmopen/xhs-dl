from pathlib import Path
import plistlib
import re


ROOT = Path(__file__).resolve().parents[1]
IOS = ROOT / "ios"


def test_ios_display_name_is_xiaohongshu_douyin_download():
    with (IOS / "RedSweetPotatoDownload" / "Info.plist").open("rb") as stream:
        info = plistlib.load(stream)

    assert info["CFBundleDisplayName"] == "万能下载器"


def test_ios_bundle_id_is_unique_and_not_album_identity():
    project = (IOS / "project.yml").read_text(encoding="utf-8")
    match = re.search(r"PRODUCT_BUNDLE_IDENTIFIER:\s*([^\s]+)", project)

    assert match is not None
    bundle_id = match.group(1)
    assert bundle_id == "com.zwmopen.redsweetpotatodownload"
    assert not bundle_id.startswith("com.zwm.album")


def test_ci_verifies_the_real_display_name_and_unique_bundle_id():
    workflow = (ROOT / ".github" / "workflows" / "ios-build.yml").read_text(
        encoding="utf-8"
    )

    assert 'info["CFBundleDisplayName"] == "万能下载器"' in workflow
    assert (
        'info["CFBundleIdentifier"] == "com.zwmopen.redsweetpotatodownload"'
        in workflow
    )


def test_ios_douyin_parser_uses_nonpersistent_web_data():
    parser = (
        IOS / "RedSweetPotatoDownloadLegacy" / "DouyinParser.swift"
    ).read_text(encoding="utf-8")
    controller = (
        IOS / "RedSweetPotatoDownloadLegacy" / "MainViewController.swift"
    ).read_text(encoding="utf-8")

    assert "configuration.websiteDataStore = .nonPersistent()" in parser
    assert "PlatformRouter.platform(for: url)" in controller
    assert "cookie" not in parser.lower()


def test_ios_release_version_and_workflow_match():
    project = (IOS / "project.yml").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "ios-build.yml").read_text(
        encoding="utf-8"
    )

    assert "MARKETING_VERSION: 0.3.2" in project
    assert 'info["CFBundleShortVersionString"] == "0.3.2"' in workflow


def test_ios_update_checker_finds_ipa_inside_unified_product_release():
    legacy = (IOS / "RedSweetPotatoDownloadLegacy" / "UpdateChecker.swift").read_text(
        encoding="utf-8"
    )

    assert 'range(of: "ios-v"' in legacy
    assert 'hasSuffix(".ipa")' in legacy
    assert 'hasPrefix("ios-v")' not in legacy
