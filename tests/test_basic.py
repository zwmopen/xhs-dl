import sys, os
import tempfile
import json
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.request import Request, urlopen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from xhs_dl.core.downloader import extract_urls_from_text

def test_extract_urls():
    text = """
    快存下！vivo X300隐藏功能！ http://xhslink.com/o/70dt8TsFJon
    【小红书】里的笔记已备好，复制后快来~红米 Watch 6 19个隐藏功能 http://xhslink.com/o/4FGTfCCdPew
    """
    urls = extract_urls_from_text(text)
    assert len(urls) == 2
    assert urls[0] == "http://xhslink.com/o/70dt8TsFJon"
    assert urls[1] == "http://xhslink.com/o/4FGTfCCdPew"
    print("extract_urls (短链接): PASS")

def test_extract_long_urls():
    """测试长链接（xiaohongshu.com）提取"""
    text = """
    https://www.xiaohongshu.com/explore/6a4dc64100000000220147df?xsec_token=CB8ns82QDJ4nkHiWJ_xCz5VrB6Pngw2UdacVqKbz8Qm2w%3D&xsec_source=app_share
    另一个 https://www.xiaohongshu.com/discovery/item/6a50b32f000000000603721e?xsec_token=xxx
    """
    urls = extract_urls_from_text(text)
    assert len(urls) == 2
    assert "6a4dc64100000000220147df" in urls[0]
    assert "6a50b32f000000000603721e" in urls[1]
    print("extract_urls (长链接): PASS")

def test_extract_urls_with_trailing_punctuation():
    """测试 URL 后面带中英文标点能正确清理"""
    text = "看这个 http://xhslink.com/o/70dt8TsFJon，快来！还有 https://www.xiaohongshu.com/explore/6a4dc64100000000220147df?xsec_token=abc。"
    urls = extract_urls_from_text(text)
    assert urls[0] == "http://xhslink.com/o/70dt8TsFJon", f"got: {urls[0]}"
    assert urls[1] == "https://www.xiaohongshu.com/explore/6a4dc64100000000220147df?xsec_token=abc", f"got: {urls[1]}"
    print("extract_urls (尾部标点清理): PASS")

def test_parse_note_id():
    from xhs_dl.core.downloader import XhsDownloader
    # discovery/item 路径
    assert XhsDownloader._parse_note_id(
        "https://www.xiaohongshu.com/discovery/item/6a50b32f000000000603721e?xsec_token=xxx"
    ) == "6a50b32f000000000603721e"
    # explore 路径
    assert XhsDownloader._parse_note_id(
        "https://www.xiaohongshu.com/explore/6a4dc64100000000220147df"
    ) == "6a4dc64100000000220147df"
    assert XhsDownloader._parse_note_id("https://example.com") == ""
    print("parse_note_id: PASS")

def test_url_type_detection():
    """测试短链接/长链接识别"""
    from xhs_dl.core.downloader import XhsDownloader
    assert XhsDownloader._is_short_url("http://xhslink.com/o/xxx")
    assert XhsDownloader._is_short_url("https://xhslink.com/a/yyy")
    assert not XhsDownloader._is_short_url("https://www.xiaohongshu.com/explore/xxx")

    assert XhsDownloader._is_long_url("https://www.xiaohongshu.com/explore/6a4dc64100000000220147df?xsec_token=xxx")
    assert XhsDownloader._is_long_url("https://www.xiaohongshu.com/discovery/item/6a50b32f000000000603721e")
    assert not XhsDownloader._is_long_url("http://xhslink.com/o/xxx")
    print("url_type_detection: PASS")

def test_sanitize():
    from xhs_dl.core.downloader import XhsDownloader
    assert XhsDownloader._sanitize('A<B>C:D/E\\F|G?H*I')
    assert XhsDownloader._sanitize("") == "untitled"
    long_name = "x" * 100
    assert len(XhsDownloader._sanitize(long_name)) == 60
    print("sanitize: PASS")

def test_extract_ssr_state():
    from xhs_dl.core.downloader import XhsDownloader
    html = '<script>window.__INITIAL_STATE__={"a":1,"b":{"c":2}}</script>'
    state = XhsDownloader._extract_ssr_state(html)
    assert state == {"a": 1, "b": {"c": 2}}
    print("extract_ssr_state: PASS")

def test_v2_local_cli_adapter():
    """不访问网络，验证 V2 CLI 参数、结果识别和本地清单。"""
    from xhs_dl.core.v2_downloader import LocalCliEngine
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        engine_home = root / "engine"
        (engine_home / "source").mkdir(parents=True)
        (engine_home / ".venv" / "Scripts").mkdir(parents=True)
        (engine_home / "main.py").write_text("", encoding="utf-8")
        (engine_home / ".venv" / "Scripts" / "python.exe").write_bytes(b"")
        output = root / "downloads"

        def fake_run(command, **kwargs):
            assert "--image_format" in command and "PNG" in command
            note_dir = output / "2026-07-18_12.00.00_作者_测试标题"
            note_dir.mkdir(parents=True)
            (note_dir / "图片_1.png").write_bytes(b"fake-png")
            return SimpleNamespace(
                returncode=0,
                stdout="开始处理作品：6a4dc64100000000220147df\n作品处理完成",
                stderr="",
            )

        engine = LocalCliEngine(str(engine_home))
        with patch("xhs_dl.core.v2_downloader.subprocess.run", side_effect=fake_run):
            result = engine.download_one("http://xhslink.com/o/test", output)
        assert result.success
        assert result.note_id == "6a4dc64100000000220147df"
        assert result.image_count == 1
        assert (Path(result.save_dir) / "xhs-dl-result.json").is_file()

        def fake_skip(command, **kwargs):
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "开始处理作品：6a4dc64100000000220147df\n"
                    "图片_1.png 文件已存在，跳过下载\n作品处理完成"
                ),
                stderr="",
            )

        with patch("xhs_dl.core.v2_downloader.subprocess.run", side_effect=fake_skip):
            repeated = engine.download_one("http://xhslink.com/o/test", output)
        assert repeated.success and repeated.image_count == 1
    print("v2_local_cli_adapter: PASS")

def test_web_job_api():
    """验证可视化界面的后台任务创建与轮询协议。"""
    from http.server import HTTPServer
    from xhs_dl.web import app

    class FakeDownloader:
        def __init__(self, **kwargs):
            pass

    app.JOBS.clear()
    server = HTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        root = f"http://127.0.0.1:{server.server_port}"
        page = urlopen(root + "/", timeout=5).read().decode("utf-8")
        assert 'data-theme="neo"' in page
        assert "xhs-dl-theme" in page

        payload = json.dumps({
            "text": "http://xhslink.com/o/testcode",
            "output_dir": "./test-output",
            "mode": "cautious",
        }).encode("utf-8")
        request = Request(
            root + "/api/jobs", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with patch("xhs_dl.web.app.XhsV2Downloader", FakeDownloader), \
                patch("xhs_dl.web.app.threading.Thread.start", return_value=None):
            response = urlopen(request, timeout=5)
            created = json.loads(response.read().decode("utf-8"))
        assert response.status == 202
        job = json.loads(urlopen(root + "/api/jobs/" + created["job_id"], timeout=5).read().decode("utf-8"))
        assert job["status"] == "queued" and job["total"] == 1
    finally:
        server.shutdown()
        server.server_close()
    print("web_job_api: PASS")

if __name__ == "__main__":
    test_extract_urls()
    test_extract_long_urls()
    test_extract_urls_with_trailing_punctuation()
    test_parse_note_id()
    test_url_type_detection()
    test_sanitize()
    test_extract_ssr_state()
    test_v2_local_cli_adapter()
    test_web_job_api()
    print("\nAll tests passed!")
