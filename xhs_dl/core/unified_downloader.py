"""One ordered downloader for Xiaohongshu and Douyin share links."""

import random
import time
from pathlib import Path

from .douyin_downloader import DouyinBrowserEngine
from .generic_downloader import YtDlpEngine
from .models import DownloadResult, NoteResult
from .platforms import detect_platform
from .v2_downloader import LocalCliEngine


class UnifiedDownloader:
    def __init__(
        self,
        output_dir="./downloads",
        delay=(35, 55),
        on_progress=None,
        engine_home=None,
        timeout=300,
        image_format="jpg",
        engines=None,
    ):
        self.output_dir = output_dir
        self.delay = delay
        self.on_progress = on_progress
        self.engine_home = engine_home
        self.timeout = timeout
        self.image_format = image_format
        self.engines = dict(engines or {})

    def _engine(self, platform):
        if platform not in self.engines:
            if platform == "xhs":
                self.engines[platform] = LocalCliEngine(
                    self.engine_home, timeout=self.timeout, image_format=self.image_format
                )
            elif platform == "douyin":
                self.engines[platform] = DouyinBrowserEngine(
                    timeout=min(self.timeout, 90), image_format=self.image_format
                )
            elif platform == "generic":
                self.engines[platform] = YtDlpEngine(timeout=self.timeout)
        return self.engines.get(platform)

    def download(self, urls):
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
            platform = detect_platform(url)
            engine = self._engine(platform)
            if engine is None:
                item = NoteResult(url=url, error="暂不支持这个链接来源")
            else:
                try:
                    item = engine.download_one(url, root)
                except Exception as exc:
                    item = NoteResult(url=url, error=str(exc), engine=platform)
            result.results.append(item)
            if self.on_progress:
                self.on_progress(item, index, len(unique))
            if index < len(unique):
                time.sleep(random.uniform(*self.delay))
        return result
