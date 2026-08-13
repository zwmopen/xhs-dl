"""万能下载器公共 Python 接口。"""

from xhs_dl.core.downloader import XhsDownloader, extract_urls_from_text
from xhs_dl.core.v2_downloader import XhsV2Downloader, LocalCliEngine, EngineNotReady
from xhs_dl.core.models import NoteResult, DownloadResult

__version__ = "2.8.2"
__all__ = ["XhsDownloader", "XhsV2Downloader", "LocalCliEngine", "EngineNotReady",
           "extract_urls_from_text", "NoteResult", "DownloadResult"]
