from pathlib import Path


def test_generic_engine_saves_media_copy_and_central_history(tmp_path, monkeypatch):
    from xhs_dl.core.generic_downloader import YtDlpEngine

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=True):
            output = Path(self.options["paths"]["home"])
            (output / "12345.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42fake")
            return {
                "id": "12345",
                "title": "公开演示 😊",
                "uploader": "示例作者",
                "description": "一段公开作品说明 #测试",
                "like_count": 3560,
                "comment_count": 128,
                "webpage_url": url,
                "extractor_key": "Twitter",
                "requested_downloads": [{"filepath": str(output / "12345.mp4")}],
            }

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    result = YtDlpEngine(youtube_dl_class=FakeYoutubeDL).download_one(
        "https://x.com/example/status/123",
        tmp_path / "downloads",
    )

    assert result.success
    folder = Path(result.save_dir)
    assert folder.name == "评128-赞3560-公开演示 😊-示例作者"
    assert (folder / "视频-公开演示 😊.mp4").is_file()
    copy = (folder / "文案.txt").read_text("utf-8-sig")
    assert "标题：公开演示 😊" in copy
    assert "正文：一段公开作品说明 #测试" in copy
    assert "原始链接：https://x.com/example/status/123" in copy
    assert not list(folder.glob("*.json"))
    assert (tmp_path / "appdata" / "xhs-dl" / "history.json").is_file()


def test_generic_engine_reports_missing_runtime_without_reading_browser_cookies(tmp_path):
    from xhs_dl.core.generic_downloader import YtDlpEngine

    engine = YtDlpEngine(youtube_dl_class=None, import_error=ImportError("missing"))
    result = engine.download_one(
        "https://www.youtube.com/watch?v=abc",
        tmp_path,
    )

    assert not result.success
    assert "yt-dlp" in result.error


def test_generic_engine_passes_bundled_ffmpeg_to_yt_dlp(tmp_path, monkeypatch):
    from xhs_dl.core.generic_downloader import YtDlpEngine

    captured = {}

    class FakeYoutubeDL:
        def __init__(self, options):
            captured.update(options)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=True):
            output = Path(captured["paths"]["home"])
            (output / "one.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42fake")
            return {"id": "one", "title": "演示", "webpage_url": url}

    monkeypatch.setattr(YtDlpEngine, "_bundled_ffmpeg", lambda self: "C:/app/ffmpeg.exe")
    result = YtDlpEngine(youtube_dl_class=FakeYoutubeDL).download_one(
        "https://x.com/example/status/123", tmp_path
    )

    assert result.success
    assert captured["ffmpeg_location"] == "C:/app/ffmpeg.exe"
    assert captured["noprogress"] is True


def test_generic_engine_converts_webp_images_to_selected_format(tmp_path):
    from PIL import Image
    from xhs_dl.core.generic_downloader import YtDlpEngine

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=True):
            output = Path(self.options["paths"]["home"])
            Image.new("RGB", (3, 2), "orange").save(output / "cover.webp", "WEBP")
            return {
                "id": "cover",
                "title": "通用图片 😊",
                "uploader": "示例作者",
                "description": "公开图片",
            }

    result = YtDlpEngine(
        youtube_dl_class=FakeYoutubeDL,
        image_format="jpg",
    ).download_one("https://x.com/example/status/123", tmp_path)

    assert result.success
    folder = Path(result.save_dir)
    output = folder / "封面-通用图片 😊.jpg"
    assert output.is_file()
    assert Image.open(output).format == "JPEG"
    assert not (folder / "封面-通用图片 😊.webp").exists()
