import os
import sys
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
    assert XhsDownloader._is_short_url("http://xhslink.cn/o/zzz")
    assert not XhsDownloader._is_short_url("https://www.xiaohongshu.com/explore/xxx")

    assert XhsDownloader._is_long_url("https://www.xiaohongshu.com/explore/6a4dc64100000000220147df?xsec_token=xxx")
    assert XhsDownloader._is_long_url("https://www.xiaohongshu.com/discovery/item/6a50b32f000000000603721e")
    assert not XhsDownloader._is_long_url("http://xhslink.com/o/xxx")


def test_local_cli_canonicalizes_xhslink_cn_for_legacy_upstream():
    from xhs_dl.core.v2_downloader import LocalCliEngine

    assert LocalCliEngine._canonicalize_source_url(
        "http://xhslink.cn/o/97Pz4siAYx4"
    ) == "http://xhslink.com/o/97Pz4siAYx4"
    assert LocalCliEngine._canonicalize_source_url(
        "https://www.xhslink.cn/o/97Pz4siAYx4"
    ) == "https://www.xhslink.com/o/97Pz4siAYx4"
    assert LocalCliEngine._canonicalize_source_url(
        "https://www.xiaohongshu.com/explore/abc"
    ) == "https://www.xiaohongshu.com/explore/abc"
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
    """不访问网络，验证元数据、文案、命名和集中历史。"""
    from xhs_dl.core.v2_downloader import LocalCliEngine
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        engine_home = root / "engine"
        (engine_home / "source").mkdir(parents=True)
        (engine_home / ".venv" / "Scripts").mkdir(parents=True)
        (engine_home / "main.py").write_text("", encoding="utf-8")
        (engine_home / ".venv" / "Scripts" / "python.exe").write_bytes(b"")
        output = root / "downloads"
        metadata = {
            "作品ID": "6a4dc64100000000220147df",
            "作品标题": "测试标题",
            "作品描述": "这是正文",
            "作品标签": "数码 技巧",
            "作者昵称": "作者",
            "评论数量": "128",
            "点赞数量": "3560",
        }

        def fake_run(command, **kwargs):
            from PIL import Image
            assert "--work-path" in command and "--folder-name" in command
            assert kwargs["env"]["PYTHONPATH"] == str(engine_home.resolve())
            note_dir = output / "2026-07-18_12.00.00_作者_测试标题"
            note_dir.mkdir(parents=True)
            Image.new("RGB", (2, 2), (20, 40, 60)).save(note_dir / "图片_1.png")
            return SimpleNamespace(
                returncode=0,
                stdout=("开始处理作品：6a4dc64100000000220147df\n"
                        "__XHS_DL_METADATA__" + json.dumps(metadata, ensure_ascii=False)),
                stderr="",
            )

        engine = LocalCliEngine(str(engine_home))
        with patch.dict(os.environ, {"LOCALAPPDATA": str(root / "appdata")}), \
                patch("xhs_dl.core.v2_downloader.subprocess.run", side_effect=fake_run):
            result = engine.download_one("http://xhslink.com/o/test", output)
        assert result.success
        assert result.note_id == "6a4dc64100000000220147df"
        assert result.image_count == 1
        assert Path(result.save_dir).name == "评128-赞3560-测试标题-作者"
        assert (Path(result.save_dir) / "封面-测试标题.jpg").is_file()
        copy_text = (Path(result.save_dir) / "文案.txt").read_text(encoding="utf-8-sig")
        assert "标题：测试标题" in copy_text and "正文：\n这是正文" in copy_text
        assert "#数码 #技巧" in copy_text
        assert not list(output.rglob("*.json"))
        assert not list(output.rglob("*.db"))
        history = json.loads((root / "appdata" / "xhs-dl" / "history.json").read_text("utf-8"))
        assert history == [{"下载网址": "http://xhslink.com/o/test", "笔记ID": result.note_id, "标题": "测试标题"}]
        def fake_skip(command, **kwargs):
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "开始处理作品：6a4dc64100000000220147df\n"
                    "图片_1.png 文件已存在，跳过下载\n"
                    "__XHS_DL_METADATA__" + json.dumps(metadata, ensure_ascii=False)
                ),
                stderr="",
            )

        with patch.dict(os.environ, {"LOCALAPPDATA": str(root / "appdata")}), \
                patch("xhs_dl.core.v2_downloader.subprocess.run", side_effect=fake_skip):
            repeated = engine.download_one("http://xhslink.com/o/test", output)
        assert repeated.success and repeated.image_count == 1
    print("v2_local_cli_adapter: PASS")


def test_v2_subprocess_environment_removes_httpx_invalid_ipv6_no_proxy():
    """httpx 0.28 cannot parse bare IPv6 entries inherited through NO_PROXY."""
    from xhs_dl.core.v2_downloader import LocalCliEngine

    value = "127.0.0.1,localhost,::1,127.0.0.0/8,::1/128,example.com"
    with patch.dict(os.environ, {"NO_PROXY": value}, clear=False):
        environment = LocalCliEngine._subprocess_environment(Path("D:/engine"))

    no_proxy = next(
        item for key, item in environment.items() if key.lower() == "no_proxy"
    )
    assert no_proxy == "127.0.0.1,localhost,127.0.0.0/8,example.com"


def test_v2_error_detail_does_not_expose_empty_metadata_marker():
    from xhs_dl.core.v2_downloader import LocalCliEngine

    output = "请求未返回公开作品数据\n__XHS_DL_METADATA__{}\n"
    assert LocalCliEngine._last_useful_line(output) == "请求未返回公开作品数据"

def test_web_job_api():
    """验证可视化界面的后台任务创建与轮询协议。"""
    from http.server import HTTPServer
    from xhs_dl.web import app

    app.JOBS.clear()
    server = HTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        root = f"http://127.0.0.1:{server.server_port}"
        page = urlopen(root + "/", timeout=5).read().decode("utf-8")
        assert 'data-theme="neo"' in page
        assert "xhs-dl-theme" in page
        assert json.dumps(str(Path.home() / "Downloads"), ensure_ascii=False) in page
        assert "MIN_PROGRESS_MS=1100" in page
        assert '<details class="advanced">' in page

        payload = json.dumps({
            "text": "http://xhslink.com/o/testcode",
            "output_dir": "./test-output",
            "mode": "cautious",
        }).encode("utf-8")
        request = Request(
            root + "/api/jobs", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with patch("xhs_dl.web.app.threading.Thread.start", return_value=None):
            response = urlopen(request, timeout=5)
            created = json.loads(response.read().decode("utf-8"))
        assert response.status == 202
        job = json.loads(urlopen(root + "/api/jobs/" + created["job_id"], timeout=5).read().decode("utf-8"))
        assert job["status"] == "queued" and job["total"] == 1
    finally:
        server.shutdown()
        server.server_close()
    print("web_job_api: PASS")


def test_portable_and_update_versions():
    from xhs_dl.desktop.app import automatic_mode, version_tuple
    from xhs_dl.portable import configure_engine_home

    assert version_tuple("v2.3.0") > version_tuple("2.2.1")
    assert automatic_mode(1) == "cautious"
    assert automatic_mode(20) == "cautious"
    assert automatic_mode(21) == "slow"
    assert automatic_mode(51) == "very-slow"
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        executable = root / "app" / "小红书无水印下载器.exe"
        engine = root / "XHS_Downloader"
        (engine / "source").mkdir(parents=True)
        (engine / "main.py").write_text("", encoding="utf-8")
        with patch.dict(os.environ, {}, clear=False):
            assert configure_engine_home(executable) == engine.resolve()


def test_desktop_theme_setting_is_persistent_and_validated():
    from xhs_dl.storage import load_settings, save_settings

    with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"LOCALAPPDATA": temp}):
        assert load_settings()["theme"] == "neo"
        save_settings({"output_dir": temp, "mode": "auto", "theme": "glass"})
        assert load_settings()["theme"] == "glass"
        save_settings({"output_dir": temp, "mode": "auto", "theme": "unknown"})
        assert load_settings()["theme"] == "neo"


def test_invalid_persisted_settings_fall_back_without_crashing():
    from xhs_dl.storage import load_settings, settings_path

    with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"LOCALAPPDATA": temp}):
        settings_path().write_text(
            json.dumps({
                "output_dir": ["not", "a", "path"],
                "mode": "turbo",
                "auto_update": "false",
                "theme": "neon",
                "image_format": "webp-only",
            }),
            encoding="utf-8",
        )
        settings = load_settings()
        assert settings["output_dir"] == str(Path.home() / "Downloads")
        assert settings["mode"] == "auto"
        assert settings["auto_update"] is True
        assert settings["theme"] == "neo"
        assert settings["image_format"] == "jpg"


def test_desktop_worker_delivers_background_exception_to_ui(monkeypatch, tmp_path):
    from xhs_dl.desktop import app as desktop

    class BrokenDownloader:
        def __init__(self, **kwargs):
            pass

        def download(self, urls):
            raise RuntimeError("可读错误")

    class FakeApp:
        settings = {"output_dir": str(tmp_path), "image_format": "jpg"}
        received = ""

        def after(self, delay, callback):
            callback()

        def _fail_download(self, message):
            self.received = message

    monkeypatch.setattr(desktop, "UnifiedDownloader", BrokenDownloader)
    fake = FakeApp()

    desktop.DesktopApp._download_worker(fake, ["https://v.douyin.com/test/"], "cautious")

    assert fake.received == "可读错误"

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
