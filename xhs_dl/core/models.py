"""
数据模型
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class NoteResult:
    """单个笔记的下载结果"""
    url: str = ""
    success: bool = False
    note_id: str = ""
    title: str = ""
    author: str = ""
    note_type: str = ""  # "normal" | "video"
    error: str = ""
    save_dir: str = ""
    image_count: int = 0
    image_success: int = 0
    desc: str = ""
    engine: str = ""
    media_format: str = ""


@dataclass
class DownloadResult:
    """批量下载结果"""
    results: List[NoteResult] = field(default_factory=list)
    output_dir: str = ""

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def fail_count(self) -> int:
        return len(self.results) - self.success_count

    @property
    def total(self) -> int:
        return len(self.results)
