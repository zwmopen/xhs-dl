# -*- coding: utf-8 -*-
"""V2 无水印下载器。

通过独立安装的 XHS-Downloader CLI 获取原始媒体。第三方引擎保持独立目录，
避免把 GPL 源码复制进本项目；本模块只负责进程调用、逐条进度与本地结果清单。
"""

import json
import locale
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

logger = logging.getLogger(__name__)

MEDIA_EXTENSIONS = {".png", ".webp", ".jpg", ".jpeg", ".heic", ".mp4", ".mov"}
VIDEO_EXTENSIONS = {".mp4", ".mov"}


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
        command = [
            str(self.python), str(self.home / "main.py"),
            "--url", url,
            "--work_path", str(output_dir.parent),
            "--folder_name", output_dir.name,
            "--image_format", "PNG",
            "--record_data", "false",
            "--download_record", "false",
            "--folder_mode", "true",
            "--author_archive", "false",
            "--language", "zh_CN",
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=str(self.home),
                capture_output=True,
                text=True,
                encoding=locale.getpreferredencoding(False),
                errors="replace",
                timeout=self.timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired:
            return NoteResult(url=url, error=f"本地引擎超过 {self.timeout} 秒未完成", engine="local-cli")

        stdout = (completed.stdout or "") + (completed.stderr or "")
        clean_stdout = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", stdout)
        after = self._media_files(output_dir)
        new_files = sorted(
            path for path, signature in after.items()
            if path not in before or before[path] != signature
        )
        note_id_match = re.search(r"开始处理作品[：:]\s*([a-f0-9]{24})", clean_stdout)

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
                note_id=note_id_match.group(1) if note_id_match else "",
                error=detail or f"本地引擎未生成媒体文件（退出码 {completed.returncode}）",
                engine="local-cli",
            )

        note_dirs = [p.parent for p in selected_files]
        note_dir = max(set(note_dirs), key=note_dirs.count)
        image_files = [p for p in selected_files if p.suffix.lower() not in VIDEO_EXTENSIONS]
        title = self._title_from_folder(note_dir.name)
        result = NoteResult(
            url=url,
            success=True,
            note_id=note_id_match.group(1) if note_id_match else "",
            title=title,
            note_type="video" if any(p.suffix.lower() in VIDEO_EXTENSIONS for p in selected_files) else "normal",
            save_dir=str(note_dir),
            image_count=len(image_files),
            image_success=len(image_files),
            engine="local-cli",
            media_format=", ".join(sorted({p.suffix.lstrip(".").upper() for p in selected_files})),
        )
        self._write_manifest(note_dir, result, selected_files)
        return result

    @staticmethod
    def _last_useful_line(text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines[-1][:300] if lines else ""

    @staticmethod
    def _title_from_folder(name: str) -> str:
        # 默认命名是“日期_时间_作者_标题”；仅剥离稳定的日期时间前缀。
        return re.sub(r"^\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}\.\d{2}_", "", name)

    @staticmethod
    def _write_manifest(note_dir: Path, result: NoteResult, files: List[Path]) -> None:
        payload = {
            "version": 2,
            "engine": result.engine,
            "source_url": result.url,
            "note_id": result.note_id,
            "title": result.title,
            "media_format": result.media_format,
            "files": [p.name for p in files],
        }
        (note_dir / "xhs-dl-result.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )


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
            self._write_batch_manifest(root, result)
            if self.on_progress:
                self.on_progress(note_result, index, len(unique))
            if index < len(unique):
                time.sleep(random.uniform(*self.delay))
        return result

    @staticmethod
    def _write_batch_manifest(root: Path, result: DownloadResult) -> None:
        payload = {
            "version": 2,
            "success": result.success_count,
            "failed": result.fail_count,
            "total": result.total,
            "items": [
                {
                    "url": item.url,
                    "success": item.success,
                    "note_id": item.note_id,
                    "title": item.title,
                    "save_dir": item.save_dir,
                    "image_count": item.image_count,
                    "media_format": item.media_format,
                    "engine": item.engine,
                    "error": item.error,
                }
                for item in result.results
            ],
        }
        (root / "xhs-dl-batch.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
