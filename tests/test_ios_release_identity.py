from pathlib import Path
import plistlib
import re


ROOT = Path(__file__).resolve().parents[1]
IOS = ROOT / "ios"


def test_ios_display_name_is_red_sweet_potato_download():
    with (IOS / "RedSweetPotatoDownload" / "Info.plist").open("rb") as stream:
        info = plistlib.load(stream)

    assert info["CFBundleDisplayName"] == "红薯下载"


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

    assert 'info["CFBundleDisplayName"] == "红薯下载"' in workflow
    assert (
        'info["CFBundleIdentifier"] == "com.zwmopen.redsweetpotatodownload"'
        in workflow
    )
