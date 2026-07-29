from pathlib import Path


def test_detect_platform_supports_xhs_and_douyin_share_links():
    from xhs_dl.core.platforms import detect_platform

    assert detect_platform("https://v.douyin.com/VFppn9c-lds/") == "douyin"
    assert detect_platform("https://www.douyin.com/note/7663398572494336177") == "douyin"
    assert detect_platform("https://xhslink.com/o/70dt8TsFJon") == "xhs"
    assert detect_platform("https://www.xiaohongshu.com/explore/abc") == "xhs"
    assert detect_platform("https://example.com/file") == "unknown"


def test_group_urls_keeps_each_platform_separate_and_preserves_order():
    from xhs_dl.core.platforms import group_urls

    urls = [
        "https://v.douyin.com/one/",
        "https://xhslink.com/o/two",
        "https://www.douyin.com/note/3",
    ]
    assert group_urls(urls) == {
        "douyin": [urls[0], urls[2]],
        "xhs": [urls[1]],
        "unknown": [],
    }


def test_douyin_payload_becomes_download_work_with_expected_folder_and_copy():
    from xhs_dl.core.douyin_downloader import DouyinWork

    work = DouyinWork.from_page_payload(
        source_url="https://v.douyin.com/VFppn9c-lds/",
        payload={
            "final_url": "https://www.douyin.com/note/7663398572494336177",
            "title": "@蔡徐坤ㅤ 谁要进",
            "author": "🌧️",
            "likes": "495",
            "comments": "937",
            "favorites": "32",
            "shares": "42",
            "published_at": "2026-07-17 15:40:22",
            "media": [
                {
                    "url": "https://p3-pc-sign.douyinpic.com/a.webp",
                    "kind": "image",
                    "extension": "webp",
                }
            ],
        },
    )

    assert work.note_id == "7663398572494336177"
    assert work.folder_name == "评937-赞495-@蔡徐坤ㅤ 谁要进-🌧️"
    assert work.media[0].extension == "webp"
    assert "标题：@蔡徐坤ㅤ 谁要进" in work.copy_text
    assert "收藏：32" in work.copy_text
    assert "原始链接：https://v.douyin.com/VFppn9c-lds/" in work.copy_text


def test_douyin_engine_saves_media_copy_and_central_history(tmp_path, monkeypatch):
    from xhs_dl.core.douyin_downloader import DouyinBrowserEngine

    payload = {
        "final_url": "https://www.douyin.com/note/7662955671021581285",
        "title": "有IKUN要进来的吗 可以s我",
        "author": "KUN",
        "likes": "3369",
        "comments": "7091",
        "favorites": "166",
        "shares": "208",
        "published_at": "2026-07-16 11:01:42",
        "media": [
            {
                "url": "https://p3-pc-sign.douyinpic.com/b.webp",
                "kind": "image",
                "extension": "webp",
            }
        ],
    }
    monkeypatch.setattr(
        DouyinBrowserEngine,
        "_extract_page",
        lambda self, url: payload,
    )
    monkeypatch.setattr(
        DouyinBrowserEngine,
        "_download_media",
        lambda self, media, destination: (
            destination.write_bytes(b"RIFFfakeWEBP") and destination
        ),
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))

    result = DouyinBrowserEngine(image_format="keep").download_one(
        "https://v.douyin.com/I6mZaIkdiho/",
        tmp_path / "downloads",
    )

    assert result.success
    folder = Path(result.save_dir)
    assert folder.name == "评7091-赞3369-有IKUN要进来的吗 可以s我-KUN"
    assert (folder / "封面-有IKUN要进来的吗 可以s我.webp").read_bytes() == b"RIFFfakeWEBP"
    assert "正文：" in (folder / "文案.txt").read_text("utf-8-sig")
    assert not list(folder.glob("*.json"))
    assert (tmp_path / "appdata" / "xhs-dl" / "history.json").is_file()


def test_unified_downloader_routes_mixed_links_in_input_order(tmp_path):
    from xhs_dl.core.models import NoteResult
    from xhs_dl.core.unified_downloader import UnifiedDownloader

    calls = []

    class FakeEngine:
        def __init__(self, platform):
            self.platform = platform

        def download_one(self, url, output_dir):
            calls.append((self.platform, url, Path(output_dir)))
            return NoteResult(url=url, success=True, title=self.platform)

    urls = [
        "https://v.douyin.com/first/",
        "https://xhslink.com/o/second",
    ]
    progress = []
    result = UnifiedDownloader(
        output_dir=str(tmp_path),
        delay=(0, 0),
        engines={
            "douyin": FakeEngine("douyin"),
            "xhs": FakeEngine("xhs"),
        },
        on_progress=lambda item, index, total: progress.append(
            (item.title, index, total)
        ),
    ).download(urls)

    assert [item.title for item in result.results] == ["douyin", "xhs"]
    assert [(platform, url) for platform, url, _ in calls] == [
        ("douyin", urls[0]),
        ("xhs", urls[1]),
    ]
    assert progress == [("douyin", 1, 2), ("xhs", 2, 2)]
