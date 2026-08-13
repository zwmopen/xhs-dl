import importlib.util
import io
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "universal-downloader" / "scripts" / "download.py"


def _load_skill_entry():
    spec = importlib.util.spec_from_file_location("xhs_download_skill_entry", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_skill_json_output_is_utf8_even_when_windows_console_defaults_to_gbk(monkeypatch):
    module = _load_skill_entry()
    raw = io.BytesIO()
    gbk_stdout = io.TextIOWrapper(raw, encoding="gbk", errors="strict")
    monkeypatch.setattr(module.sys, "stdout", gbk_stdout)

    module.emit_payload({"title": "山野小院🍃"})
    gbk_stdout.flush()

    assert "山野小院🍃" in raw.getvalue().decode("utf-8")


def test_skill_uses_core_url_parser_for_chinese_share_punctuation():
    module = _load_skill_entry()
    text = "先复制一下，打开【小红书】看看这篇好文！http://xhslink.cn/o/97Pz4siAYx4》"

    assert module.extract_urls(text) == ["http://xhslink.cn/o/97Pz4siAYx4"]
