"""Local yt-dlp adapter for public media on supported social platforms."""

import re
import shutil
import tempfile
from pathlib import Path

from .media_names import convert_image_file, media_filename, media_sort_key, safe_title
from .models import NoteResult
from xhs_dl.storage import add_history


IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif", "avif"}


def _count(value):
    if value is None or value == "":
        return "未知"
    return str(value)


class YtDlpEngine:
    """Download one public work without importing browser cookies."""

    def __init__(
        self,
        timeout=300,
        image_format="jpg",
        youtube_dl_class="auto",
        import_error=None,
    ):
        self.timeout = timeout
        self.image_format = image_format
        self.import_error = import_error
        if youtube_dl_class == "auto":
            try:
                from yt_dlp import YoutubeDL
            except ImportError as exc:
                self.youtube_dl_class = None
                self.import_error = exc
            else:
                self.youtube_dl_class = YoutubeDL
        else:
            self.youtube_dl_class = youtube_dl_class

    def _bundled_ffmpeg(self):
        try:
            import imageio_ffmpeg

            path = Path(imageio_ffmpeg.get_ffmpeg_exe())
            return str(path) if path.is_file() else None
        except (ImportError, OSError, RuntimeError):
            return None

    @staticmethod
    def _folder_name(info):
        comments = safe_title(_count(info.get("comment_count")), 12)
        likes = safe_title(_count(info.get("like_count")), 12)
        title = safe_title(info.get("title") or "未命名作品", 56)
        author = safe_title(
            info.get("uploader") or info.get("channel") or info.get("creator") or "未知作者",
            32,
        )
        return f"评{comments}-赞{likes}-{title}-{author}"

    @staticmethod
    def _copy_text(info, source_url):
        description = str(info.get("description") or "").strip() or "（正文为空）"
        topics = list(dict.fromkeys(re.findall(r"#([^\s#]+)", description)))
        topic_text = " ".join(f"#{topic}" for topic in topics) or "（无话题）"
        author = info.get("uploader") or info.get("channel") or info.get("creator") or "未知作者"
        return (
            f"标题：{info.get('title') or '未命名作品'}\n\n"
            f"正文：{description}\n\n"
            f"话题：{topic_text}\n\n"
            f"作者：{author}\n"
            f"点赞：{_count(info.get('like_count'))}\n"
            f"评论：{_count(info.get('comment_count'))}\n"
            f"发布时间：{info.get('upload_date') or info.get('timestamp') or '未知'}\n"
            f"来源平台：{info.get('extractor_key') or info.get('extractor') or '通用平台'}\n\n"
            f"原始链接：{source_url}\n"
            f"作品 ID：{info.get('id') or ''}\n"
        )

    def download_one(self, url, output_dir):
        if self.youtube_dl_class is None:
            return NoteResult(
                url=url,
                error="通用平台组件 yt-dlp 未安装，请安装或更新正式版后重试。",
                engine="yt-dlp",
            )

        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".xhs-dl-yt-", dir=root))
        try:
            options = {
                "paths": {"home": str(staging)},
                "outtmpl": {"default": "%(id)s.%(ext)s"},
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
                "socket_timeout": min(max(int(self.timeout), 10), 300),
                "retries": 3,
                "fragment_retries": 3,
                "format": "bestvideo*+bestaudio/best",
                "merge_output_format": "mp4",
                "writethumbnail": False,
                "writeinfojson": False,
            }
            ffmpeg = self._bundled_ffmpeg()
            if ffmpeg:
                options["ffmpeg_location"] = ffmpeg
            with self.youtube_dl_class(options) as downloader:
                info = downloader.extract_info(url, download=True)
            if not isinstance(info, dict):
                raise RuntimeError("平台没有返回可识别的公开媒体信息")

            files = sorted(
                (
                    path for path in staging.iterdir()
                    if path.is_file() and not path.name.endswith((".part", ".ytdl", ".json"))
                ),
                key=media_sort_key,
            )
            if not files:
                raise RuntimeError("该公开链接没有解析到可下载媒体")

            folder = root / self._folder_name(info)
            folder.mkdir(parents=True, exist_ok=True)
            title = info.get("title") or "未命名作品"
            image_index = 0
            video_index = 0
            for source in files:
                extension = source.suffix.lstrip(".").lower() or "bin"
                is_image = extension in IMAGE_EXTENSIONS
                if is_image and self.image_format != "keep":
                    source = convert_image_file(source, self.image_format)
                    extension = source.suffix.lstrip(".").lower()
                index = image_index if is_image else video_index
                target = folder / media_filename(
                    index, title, extension, is_video=not is_image
                )
                if is_image:
                    image_index += 1
                else:
                    video_index += 1
                source.replace(target)

            (folder / "文案.txt").write_text(
                self._copy_text(info, url), encoding="utf-8-sig"
            )
            note_id = str(info.get("id") or "")
            add_history(url, note_id, str(title))
            return NoteResult(
                url=url,
                success=True,
                note_id=note_id,
                title=str(title),
                author=str(info.get("uploader") or info.get("channel") or ""),
                note_type="video" if video_index else "normal",
                save_dir=str(folder.resolve()),
                image_count=image_index,
                image_success=image_index,
                desc=str(info.get("description") or ""),
                engine="yt-dlp",
                media_format="mixed" if image_index and video_index else ("image" if image_index else "video"),
            )
        except Exception as exc:
            return NoteResult(url=url, error=str(exc), engine="yt-dlp")
        finally:
            shutil.rmtree(staging, ignore_errors=True)
