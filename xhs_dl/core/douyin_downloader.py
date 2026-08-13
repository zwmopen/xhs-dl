"""Douyin public work downloader backed by a clean system Edge session.

The browser profile is temporary and carries no user login state.  It renders
the public detail page because a plain HTTP client receives an anti-bot shell.
Only the current work's public metadata and media URLs are read.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List
import requests

from .models import NoteResult
from .media_names import convert_image_file, media_filename
from .v2_downloader import EngineNotReady
from xhs_dl.storage import add_history


@dataclass(frozen=True)
class DouyinMedia:
    url: str
    kind: str
    extension: str


@dataclass(frozen=True)
class DouyinWork:
    source_url: str
    final_url: str
    note_id: str
    title: str
    author: str
    likes: str
    comments: str
    favorites: str
    shares: str
    published_at: str
    topics: List[str]
    media: List[DouyinMedia]

    @classmethod
    def from_page_payload(cls, source_url, payload):
        final_url = str(payload.get("final_url") or source_url)
        match = re.search(r"/(?:note|video)/(\d+)", final_url)
        title = str(payload.get("title") or "").strip()
        topics = list(dict.fromkeys(re.findall(r"#([^\s#]+)", title)))
        media = [
            DouyinMedia(
                url=str(item.get("url") or ""),
                kind=str(item.get("kind") or "image"),
                extension=str(item.get("extension") or "webp").lower().lstrip("."),
            )
            for item in payload.get("media") or []
            if item.get("url")
        ]
        return cls(
            source_url=source_url,
            final_url=final_url,
            note_id=match.group(1) if match else "",
            title=title,
            author=str(payload.get("author") or "").strip(),
            likes=str(payload.get("likes") or "未知"),
            comments=str(payload.get("comments") or "未知"),
            favorites=str(payload.get("favorites") or "未知"),
            shares=str(payload.get("shares") or "未知"),
            published_at=str(payload.get("published_at") or ""),
            topics=topics,
            media=media,
        )

    @staticmethod
    def _safe(value, limit):
        value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or "")).strip(" .-")
        return (value or "未知")[:limit]

    @property
    def folder_name(self):
        return (
            f"评{self._safe(self.comments, 12)}-赞{self._safe(self.likes, 12)}-"
            f"{self._safe(self.title or '未命名作品', 56)}-"
            f"{self._safe(self.author or '未知作者', 32)}"
        )

    @property
    def copy_text(self):
        topic_text = " ".join(f"#{topic}" for topic in self.topics) or "（无话题）"
        return (
            f"标题：{self.title}\n\n"
            f"正文：\n{self.title or '（正文为空）'}\n\n"
            f"话题：\n{topic_text}\n\n"
            f"作者：{self.author or '未知作者'}\n"
            f"点赞：{self.likes}\n"
            f"评论：{self.comments}\n"
            f"收藏：{self.favorites}\n"
            f"分享：{self.shares}\n"
            f"发布时间：{self.published_at or '未知'}\n\n"
            f"原始链接：{self.source_url}\n"
            f"作品 ID：{self.note_id}\n"
        )


class DouyinBrowserEngine:
    """Extract and download one public Douyin work without a login session."""

    PAGE_SCRIPT = r"""
() => {
  const current = location.href;
  const isNote = /\/note\//.test(current);
  const main = document.querySelector("main") || document.body;
  const text = main.innerText || "";
  const meta = document.querySelector('meta[name="description"]')?.content || "";
  let title = (document.title || "").replace(/\s*-\s*抖音\s*$/, "").trim();
  let author = "";
  for (const node of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      const value = JSON.parse(node.textContent || "{}");
      const item = value.itemListElement?.find(x => Number(x.position) === 2);
      if (item?.name) { author = String(item.name); break; }
    } catch (_) {}
  }
  if (!author && meta.includes(" - ")) {
    const tail = meta.split(" - ").slice(1).join(" - ");
    author = (tail.match(/^(.*?)于\d{8}发布/) || [])[1] || "";
  }
  if (author && meta.includes(` - ${author}于`)) {
    title = meta.split(` - ${author}于`, 1)[0].trim() || title;
  }
  const read = selector => {
    const node = main.querySelector(selector);
    return node ? (node.innerText || node.textContent || "").trim() : "";
  };
  const unique = new Map();
  if (isNote) {
    for (const image of main.querySelectorAll('img')) {
      const src = image.currentSrc || image.src || "";
      if (!src.includes("aweme-images")) continue;
      if (!unique.has(src)) unique.set(src, {
        url: src, kind: "image",
        extension: src.includes(".png") ? "png" : src.includes(".jpeg") || src.includes(".jpg") ? "jpg" : "webp"
      });
    }
  } else {
    for (const node of main.querySelectorAll("video, video source")) {
      const src = node.currentSrc || node.src || "";
      if (!/^https?:/.test(src) || unique.has(src)) continue;
      unique.set(src, {url: src, kind: "video", extension: "mp4"});
    }
  }
  const published = (text.match(/发布时间[：:]\s*([^\n]+)/) || [])[1] || "";
  return {
    final_url: current,
    title,
    author,
    likes: read('[data-e2e="video-player-digg"]') || "未知",
    comments: read('[data-e2e="feed-comment-icon"]') || (text.match(/评论\(([^)]+)\)/) || [])[1] || "未知",
    favorites: read('[data-e2e="video-player-collect"]') || "未知",
    shares: read('[data-e2e="video-player-share"]') || "未知",
    published_at: published.trim(),
    media: Array.from(unique.values())
  };
}
"""

    def __init__(self, timeout=75, image_format="jpg"):
        self.timeout = timeout
        self.image_format = image_format

    def _extract_page(self, url):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise EngineNotReady("抖音浏览器组件未安装，请重新安装最新版万能下载器。") from exc

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="msedge", headless=True)
                context = browser.new_context(
                    locale="zh-CN",
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0.0.0 Safari/537.36"
                    ),
                )
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                page.wait_for_function(
                    r"""() => {
                      const main = document.querySelector("main");
                      if (!main) return false;
                      if (/\/note\//.test(location.pathname)) {
                        return Array.from(main.querySelectorAll("img"))
                          .some(x => (x.currentSrc || x.src || "").includes("aweme-images"));
                      }
                      return Array.from(main.querySelectorAll("video, video source"))
                        .some(x => /^https?:/.test(x.currentSrc || x.src || ""));
                    }""",
                    timeout=min(self.timeout, 40) * 1000,
                )
                payload = page.evaluate(self.PAGE_SCRIPT)
                context.close()
                browser.close()
        except Exception as exc:
            detail = str(exc).splitlines()[0][:180]
            raise RuntimeError(f"抖音公开页面解析失败：{detail}") from exc
        if not payload or not payload.get("media"):
            raise RuntimeError("抖音公开页面已打开，但没有取得当前作品媒体；请稍后重试。")
        return payload

    def _download_media(self, media, destination):
        destination = Path(destination)
        partial = destination.with_name(destination.name + ".part")
        response = None
        size = 0
        try:
            response = requests.get(
                media.url,
                timeout=(20, 75),
                stream=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/126 Safari/537.36"
                    ),
                    "Referer": "https://www.douyin.com/",
                },
            )
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type.startswith(("text/", "application/json")):
                raise RuntimeError("抖音返回了网页而不是媒体文件，请稍后重试")
            with partial.open("wb") as stream:
                for chunk in response.iter_content(chunk_size=128 * 1024):
                    if chunk:
                        stream.write(chunk)
                        size += len(chunk)
            if size < 200:
                raise RuntimeError("抖音媒体返回内容过小")
            partial.replace(destination)
        except Exception:
            partial.unlink(missing_ok=True)
            raise
        finally:
            if response is not None:
                response.close()
        if media.kind != "video" and self.image_format != "keep":
            return convert_image_file(destination, self.image_format)
        return destination

    def download_one(self, url, output_dir):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        work = DouyinWork.from_page_payload(url, self._extract_page(url))
        note_dir = output_dir / work.folder_name
        note_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for index, media in enumerate(work.media, 1):
            extension = (
                self.image_format
                if media.kind != "video" and self.image_format != "keep"
                else media.extension
            )
            destination = note_dir / media_filename(
                index - 1,
                work.title,
                extension,
                is_video=media.kind == "video",
            )
            if not destination.exists():
                downloaded = note_dir / media_filename(
                    index - 1,
                    work.title,
                    media.extension,
                    is_video=media.kind == "video",
                )
                destination = self._download_media(media, downloaded)
            saved.append(destination)
        (note_dir / "文案.txt").write_text(work.copy_text, encoding="utf-8-sig")
        add_history(url, work.note_id, work.title)
        videos = [item for item in work.media if item.kind == "video"]
        images = [item for item in work.media if item.kind != "video"]
        return NoteResult(
            url=url,
            success=True,
            note_id=work.note_id,
            title=work.title,
            author=work.author,
            note_type="video" if videos else "normal",
            save_dir=str(note_dir),
            image_count=len(images),
            image_success=len(images),
            desc=work.title,
            topics=" ".join(work.topics),
            engine="douyin-edge",
            media_format=", ".join(sorted({path.suffix.lstrip(".").upper() for path in saved})),
        )
