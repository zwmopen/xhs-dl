"""
小红书笔记下载器
"""

from xhs_dl.core.downloader import XhsDownloader, extract_urls_from_text
from xhs_dl.core.models import NoteResult, DownloadResult

__version__ = "1.0.0"
__all__ = ["XhsDownloader", "extract_urls_from_text", "NoteResult", "DownloadResult"]