# -*- coding: utf-8 -*-
"""
小红书笔记下载器 - 核心下载逻辑

原理:
  xhslink.com 短链接 → 302 重定向 → 完整 URL（含 xsec_token）
  用完整 URL 访问笔记页面 → 解析 SSR 注入的 window.__INITIAL_STATE__
  → 提取标题、正文、图片 URL → 下载到本地

注意: 图片自带小红书平台水印（水印是服务端烧录的，无法通过 URL 去除）
"""

import re
import json
import time
import random
import logging
from typing import List, Tuple, Optional, Callable
from pathlib import Path

import requests

from .models import NoteResult

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

DOWNLOAD_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Referer": "https://www.xiaohongshu.com/",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}


def extract_urls_from_text(text: str) -> List[str]:
    """从分享文本中提取所有 URL"""
    pattern = r'https?://[^\s<>"\')\]]+'
    return re.findall(pattern, text)


class XhsDownloader:
    """小红书笔记下载器"""

    def __init__(self, output_dir: str = "./xhs_downloads",
                 delay: Tuple[float, float] = (2, 5),
                 on_progress: Optional[Callable] = None):
        """
        Args:
            output_dir: 保存目录
            delay: 每次请求间的随机等待范围（秒）
            on_progress: 进度回调 fn(note_result, index, total)
        """
        self.output_dir = output_dir
        self.delay = delay
        self.on_progress = on_progress
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def download(self, urls: List[str]) -> 'DownloadResult':
        """批量下载"""
        from .models import DownloadResult

        # 去重
        seen = set()
        unique = []
        for u in urls:
            c = u.rstrip('/')
            if c not in seen:
                seen.add(c)
                unique.append(u)

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        result = DownloadResult(output_dir=self.output_dir)
        for i, url in enumerate(unique, 1):
            nr = self._process_one(url, i, len(unique))
            result.results.append(nr)
            if self.on_progress:
                self.on_progress(nr, i, len(unique))
            if i < len(unique):
                time.sleep(random.uniform(*self.delay))

        return result

    def download_text(self, text: str) -> 'DownloadResult':
        """从分享文本中提取链接并下载"""
        urls = extract_urls_from_text(text)
        return self.download(urls)

    def _process_one(self, url: str, index: int, total: int) -> NoteResult:
        """处理单个链接"""
        nr = NoteResult(url=url)
        logger.info(f"[{index}/{total}] 处理: {url[:60]}")

        try:
            # Step 1: 解析短链接
            full_url = self._resolve_url(url)
            note_id = self._parse_note_id(full_url)
            if not note_id:
                nr.error = "无法提取笔记 ID"
                return nr

            nr.note_id = note_id
            time.sleep(random.uniform(0.5, 1.5))

            # Step 2: 获取 SSR 数据
            resp = self.session.get(full_url, timeout=15)
            html = resp.text
            if len(html) < 5000:
                nr.error = "返回内容过短，可能被拦截"
                return nr

            state = self._extract_ssr_state(html)
            if not state:
                nr.error = "无法解析页面数据"
                return nr

            note = self._extract_note(state)
            if not note.get("title"):
                nr.error = "未能提取到笔记标题"
                return nr

            # Step 3: 提取信息
            nr.title = note.get("title", "")
            nr.desc = note.get("desc", "")
            nr.author = (note.get("user", {}).get("nickname", "")
                         or note.get("user", {}).get("name", ""))
            nr.note_type = "video" if note.get("type") == "video" else "normal"
            nr.success = True

            # Step 4: 保存
            safe_title = self._sanitize(nr.title)
            note_dir = Path(self.output_dir) / safe_title
            note_dir.mkdir(parents=True, exist_ok=True)
            nr.save_dir = str(note_dir)

            # 正文
            self._save_text(note_dir, nr, full_url)

            # 图片
            media = self._get_media_urls(note)
            nr.image_count = len(media)
            for i, (mtype, murl) in enumerate(media):
                time.sleep(random.uniform(0.3, 0.7))
                ext = ".mp4" if mtype == "video" else ".jpg"
                fname = f"img_{i+1:03d}{ext}"
                if self._download_file(murl, note_dir / fname):
                    nr.image_success += 1

            # 视频
            if nr.note_type == "video":
                vid = self._get_video_url(note)
                if vid:
                    time.sleep(random.uniform(0.3, 0.7))
                    if self._download_file(vid, note_dir / "video_001.mp4"):
                        pass

        except Exception as e:
            nr.error = str(e)
            logger.error(f"处理失败: {e}")

        return nr

    # ── 链接解析 ──

    def _resolve_url(self, url: str) -> str:
        if url.startswith("xhslink.com"):
            url = "https://" + url
        resp = self.session.get(url, allow_redirects=True, timeout=15)
        return resp.url

    @staticmethod
    def _parse_note_id(url: str) -> str:
        m = re.search(r'/(?:explore|discovery/item)/([a-f0-9]{24})', url)
        return m.group(1) if m else ""

    # ── SSR 数据提取 ──

    @staticmethod
    def _extract_ssr_state(html: str) -> dict:
        marker = "window.__INITIAL_STATE__="
        idx = html.find(marker)
        if idx == -1:
            return {}
        json_start = html.find("{", idx)
        depth = 0
        for i in range(json_start, len(html)):
            if html[i] == '{':
                depth += 1
            elif html[i] == '}':
                depth -= 1
                if depth == 0:
                    raw = html[json_start:i+1]
                    raw = re.sub(r'\bundefined\b', 'null', raw)
                    try:
                        return json.loads(raw)
                    except json.JSONDecodeError:
                        return {}
        return {}

    @staticmethod
    def _extract_note(state: dict) -> dict:
        # 路径1: noteData.data.noteData
        try:
            n = state["noteData"]["data"]["noteData"]
            if n and n.get("title"):
                return n
        except (KeyError, TypeError):
            pass

        # 路径2: note.noteDetailMap
        try:
            for _, v in state["note"]["noteDetailMap"].items():
                n = v.get("note", {})
                if n and n.get("title"):
                    return n
        except (KeyError, TypeError):
            pass

        # 路径3: normalNotePreloadData
        try:
            p = state["noteData"]["normalNotePreloadData"]
            if p and p.get("title"):
                return XhsDownloader._upgrade_preload(p, state)
        except (KeyError, TypeError):
            pass

        return {}

    @staticmethod
    def _upgrade_preload(preload: dict, state: dict) -> dict:
        note = {
            "title": preload.get("title", ""),
            "desc": preload.get("desc", ""),
            "type": "normal",
            "imageList": [],
        }
        for img in preload.get("imagesList", []):
            note["imageList"].append({
                "url": img.get("url", "") or img.get("urlSizeLarge", ""),
                "url_default": "",
                "info_list": [],
            })
        try:
            full = state["noteData"]["data"]["noteData"]
            if full:
                for k in ("imageList", "desc", "user", "type", "video"):
                    if full.get(k):
                        note[k] = full[k]
        except (KeyError, TypeError):
            pass
        return note

    # ── 媒体提取 ──

    @staticmethod
    def _get_media_urls(note: dict) -> List[Tuple[str, str]]:
        media = []
        for img in note.get("imageList", []):
            url = ""
            info_list = img.get("info_list", []) or img.get("infoList", [])
            if info_list:
                best = max(info_list, key=lambda x: (
                    x.get("image_scene", {}).get("width", 0)
                    if isinstance(x.get("image_scene"), dict) else 0
                ))
                url = best.get("url", "")
            url = url or img.get("url_default", "") or img.get("url", "")
            if url:
                if url.startswith("http://"):
                    url = "https://" + url[7:]
                media.append(("image", url))
        return media

    @staticmethod
    def _get_video_url(note: dict) -> str:
        v = note.get("video", {})
        if not v:
            return ""
        return (v.get("consumer", {}).get("originVideoKey", "")
                or v.get("originVideoKey", "")
                or (v.get("video", {}).get("player", {})
                    or v.get("player", {})).get("url", ""))

    # ── 文件操作 ──

    @staticmethod
    def _sanitize(name: str, max_len: int = 60) -> str:
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip('. ')
        return (name[:max_len] if len(name) > max_len else name) or "untitled"

    @staticmethod
    def _save_text(note_dir: Path, nr: 'NoteResult', url: str):
        (note_dir / "正文.txt").write_text(
            f"标题: {nr.title}\n"
            f"作者: {nr.author}\n"
            f"笔记ID: {nr.note_id}\n"
            f"链接: {url}\n"
            f"{'='*40}\n\n"
            f"{nr.desc}",
            encoding="utf-8"
        )

    def _download_file(self, url: str, path: Path) -> bool:
        try:
            resp = self.session.get(url, headers=DOWNLOAD_HEADERS,
                                    timeout=30, stream=True)
            resp.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            if path.stat().st_size < 200:
                path.unlink()
                return False
            return True
        except Exception as e:
            logger.warning(f"下载失败 {url}: {e}")
            if path.exists():
                path.unlink()
            return False