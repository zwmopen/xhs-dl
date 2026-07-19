"""集中保存应用设置和精简下载历史。"""

import json
import os
import threading
from pathlib import Path


_LOCK = threading.Lock()


def app_data_dir():
    root = os.environ.get("LOCALAPPDATA")
    path = Path(root) / "xhs-dl" if root else Path.home() / ".xhs-dl"
    path.mkdir(parents=True, exist_ok=True)
    return path


def history_path():
    return app_data_dir() / "history.json"


def settings_path():
    return app_data_dir() / "settings.json"


def _read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)


def add_history(download_url, note_id, title):
    item = {
        "下载网址": download_url,
        "笔记ID": note_id,
        "标题": title,
    }
    with _LOCK:
        path = history_path()
        items = _read_json(path, [])
        if not isinstance(items, list):
            items = []
        key = note_id or download_url
        items = [
            old for old in items
            if (old.get("笔记ID") or old.get("下载网址")) != key
        ]
        items.append(item)
        _write_json(path, items)
    return path


def load_settings():
    defaults = {
        "output_dir": str(Path.home() / "Downloads"),
        "mode": "auto",
        "auto_update": True,
        "theme": "neo",
    }
    with _LOCK:
        value = _read_json(settings_path(), {})
    if isinstance(value, dict):
        defaults.update(value)
    return defaults


def save_settings(value):
    allowed = {
        "output_dir": value.get("output_dir") or str(Path.home() / "Downloads"),
        "mode": value.get("mode", "auto"),
        "auto_update": bool(value.get("auto_update", True)),
        "theme": "glass" if value.get("theme") == "glass" else "neo",
    }
    with _LOCK:
        _write_json(settings_path(), allowed)
    return allowed
