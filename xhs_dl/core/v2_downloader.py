# -*- coding: utf-8 -*-
"""V2 无水印下载器。

通过独立安装的 XHS-Downloader CLI 获取原始媒体。第三方引擎保持独立目录，
避免把 GPL 源码复制进本项目；本模块只负责进程调用、逐条进度与本地结果清单。
"""

import json
import logging
import os
import random
import re
import subprocess
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from .downloader import DELAY_MODES, extract_urls_from_text
from .models import DownloadResult, NoteResult
from xhs_dl.storage import add_history

logger = logging.getLogger(__name__)

MEDIA_EXTENSIONS = {".png", ".webp", ".jpg", ".jpeg", ".heic", ".mp4", ".mov"}
VIDEO_EXTENSIONS = {".mp4", ".mov"}
METADATA_MARKER = "__XHS_DL_METADATA__"


class EngineNotReady(RuntimeError):
    """本地无水印引擎尚未安装或不可运行。"""


class LocalCliEngine:
    """XHS-Downloader 的本地 CLI 适配器。"""

    def __init__(self, home: Optional[str] = None, timeout: int = 300):
        self.home = self._discover_home(home)
        self.timeout = timeout
        self.python = self._discover_python()

    @staticmethod
    def _discover_home(explicit: Optional[str]) -> Path:
        candidates = []
        if explicit:
            candidates.append(Path(explicit))
        if os.environ.get("XHS_DOWNLOADER_HOME"):
            candidates.append(Path(os.environ["XHS_DOWNLOADER_HOME"]))

        project_root = Path(__file__).resolve().parents[2]
        candidates.extend([
            project_root / "vendor" / "XHS_Downloader",
            project_root.parent / "XHS_Downloader",
            Path(r"D:\AICode\XHS_Downloader"),
        ])
        for path in candidates:
            path = path.expanduser().resolve()
            if (path / "main.py").is_file() and (path / "source").is_dir():
                return path
        raise EngineNotReady(
            "未找到本地无水印引擎。请先运行 setup-v2.ps1，或用 "
            "--engine-home 指定 XHS_Downloader 目录。"
        )

    def _discover_python(self) -> Path:
        candidates = [
            self.home / ".venv" / "Scripts" / "python.exe",
            self.home / "venv" / "Scripts" / "python.exe",
        ]
        for path in candidates:
            if path.is_file():
                return path
        raise EngineNotReady(
            f"{self.home} 缺少隔离运行环境。请在该目录运行 python -m uv sync --no-dev。"
        )

    @staticmethod
    def _media_files(root: Path) -> dict:
        if not root.exists():
            return {}
        result = {}
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS:
                stat = path.stat()
                result[path.resolve()] = (stat.st_size, stat.st_mtime_ns)
        return result

    def download_one(self, url: str, output_dir: Path) -> NoteResult:
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        before = self._media_files(output_dir)
        bridge = Path(__file__).resolve().parents[1] / "engine_bridge.py"
        command = [
            str(self.python), str(bridge),
            "--url", url,
            "--work-path", str(output_dir.parent),
            "--folder-name", output_dir.name,
        ]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(self.home)
        try:
            completed = subprocess.run(
                command,
                cwd=str(self.home),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env=environment,
            )
        except subprocess.TimeoutExpired:
            self._remove_engine_database(output_dir)
            return NoteResult(url=url, error=f"本地引擎超过 {self.timeout} 秒未完成", engine="local-cli")
        self._remove_engine_database(output_dir)

        stdout = (completed.stdout or "") + (completed.stderr or "")
        clean_stdout = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", stdout)
        metadata = self._extract_metadata(clean_stdout)
        after = self._media_files(output_dir)
        new_files = sorted(
            path for path, signature in after.items()
            if path not in before or before[path] != signature
        )
        note_id_match = re.search(r"开始处理作品[：:]\s*([a-f0-9]{24})", clean_stdout)
        note_id = str(metadata.get("作品ID") or (note_id_match.group(1) if note_id_match else ""))

        # 上游会主动跳过已存在文件。通过输出中的完整文件名映射回本地结果，
        # 让重复运行成为成功的幂等操作，而不是误报“未生成文件”。
        selected_files = new_files
        if not selected_files and "文件已存在" in clean_stdout:
            selected_files = sorted(
                path for path in after
                if path.name in clean_stdout
            )

        if not selected_files:
            detail = self._last_useful_line(clean_stdout)
            return NoteResult(
                url=url,
                note_id=note_id,
                error=detail or f"本地引擎未生成媒体文件（退出码 {completed.returncode}）",
                engine="local-cli",
            )

        note_dirs = [p.parent for p in selected_files]
        note_dir = max(set(note_dirs), key=note_dirs.count)
        note_dir, selected_files = self._rename_note_folder(note_dir, selected_files, metadata)
        image_files = [p for p in selected_files if p.suffix.lower() not in VIDEO_EXTENSIONS]
        title = str(metadata.get("作品标题") or self._title_from_folder(note_dir.name))
        author = str(metadata.get("作者昵称") or "")
        description = str(metadata.get("作品描述") or "")
        topics = str(metadata.get("作品标签") or "")
        result = NoteResult(
            url=url,
            success=True,
            note_id=note_id,
            title=title,
            author=author,
            note_type="video" if any(p.suffix.lower() in VIDEO_EXTENSIONS for p in selected_files) else "normal",
            save_dir=str(note_dir),
            image_count=len(image_files),
            image_success=len(image_files),
            desc=description,
            topics=topics,
            engine="local-cli",
            media_format=", ".join(sorted({p.suffix.lstrip(".").upper() for p in selected_files})),
        )
        self._write_copy_text(note_dir, result)
        add_history(url, result.note_id, result.title)
        return result

    @staticmethod
    def _remove_engine_database(output_dir: Path) -> None:
        database = output_dir / "ExploreData.db"
        try:
            if database.is_file():
                database.unlink()
        except OSError:
            logger.warning("无法清理上游空数据文件：%s", database)

    @staticmethod
    def _extract_metadata(text: str) -> dict:
        for line in reversed(text.splitlines()):
            if line.startswith(METADATA_MARKER):
                try:
                    value = json.loads(line[len(METADATA_MARKER):])
                    return value if isinstance(value, dict) else {}
                except json.JSONDecodeError:
                    return {}
        return {}

    @staticmethod
    def _safe_name(value: str, limit: int = 56) -> str:
        value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or "")).strip(" .-")
        return value[:limit] or "未知"

    @classmethod
    def _rename_note_folder(cls, note_dir: Path, files: List[Path], metadata: dict):
        if not metadata:
            return note_dir, files
        comments = cls._safe_name(metadata.get("评论数量") or "未知", 16)
        likes = cls._safe_name(metadata.get("点赞数量") or "未知", 16)
        title = cls._safe_name(metadata.get("作品标题") or "未命名笔记")
        author = cls._safe_name(metadata.get("作者昵称") or "未知作者", 32)
        desired = note_dir.parent / f"评{comments}-赞{likes}-{title}-{author}"
        if desired != note_dir:
            if desired.exists():
                merged = []
                for path in files:
                    target = desired / path.relative_to(note_dir)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        path.unlink()
                    else:
                        path.rename(target)
                    merged.append(target)
                try:
                    note_dir.rmdir()
                except OSError:
                    pass
                files = merged
            else:
                note_dir.rename(desired)
                files = [desired / path.relative_to(note_dir) for path in files]
            note_dir = desired
        return note_dir, files

    @staticmethod
    def _last_useful_line(text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines[-1][:300] if lines else ""

    @staticmethod
    def _title_from_folder(name: str) -> str:
        # 默认命名是“日期_时间_作者_标题”；仅剥离稳定的日期时间前缀。
        return re.sub(r"^\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}\.\d{2}_", "", name)

    @staticmethod
    def _write_copy_text(note_dir: Path, result: NoteResult) -> None:
        topics = " ".join(
            topic if topic.startswith("#") else "#" + topic
            for topic in result.topics.split()
        )
        content = (
            f"标题：{result.title}\n\n"
            f"正文：\n{result.desc or '（正文为空）'}\n\n"
            f"话题：{topics or '（无话题）'}\n"
        )
        (note_dir / "文案.txt").write_text(content, encoding="utf-8-sig")


class XhsV2Downloader:
    """逐条调用本地无水印引擎，支持批量、去重、延时与进度回调。"""

    def __init__(self, output_dir: str = "./xhs_downloads",
                 delay: Tuple[float, float] = DELAY_MODES["cautious"],
                 on_progress: Optional[Callable] = None,
                 engine_home: Optional[str] = None,
                 timeout: int = 300):
        self.output_dir = output_dir
        self.delay = delay
        self.on_progress = on_progress
        self.engine = LocalCliEngine(engine_home, timeout=timeout)

    def download_text(self, text: str) -> DownloadResult:
        return self.download(extract_urls_from_text(text))

    def download(self, urls: List[str]) -> DownloadResult:
        seen = set()
        unique = []
        for url in urls:
            key = url.rstrip("/")
            if key not in seen:
                seen.add(key)
                unique.append(url)

        root = Path(self.output_dir)
        root.mkdir(parents=True, exist_ok=True)
        result = DownloadResult(output_dir=str(root.resolve()))
        for index, url in enumerate(unique, 1):
            note_result = self.engine.download_one(url, root)
            result.results.append(note_result)
            if self.on_progress:
                self.on_progress(note_result, index, len(unique))
            if index < len(unique):
                time.sleep(random.uniform(*self.delay))
        return result
