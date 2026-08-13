"""Supported share-link platform detection."""

from urllib.parse import urlparse


XHS_HOSTS = {
    "xhslink.com",
    "www.xhslink.com",
    "xhslink.cn",
    "www.xhslink.cn",
    "xiaohongshu.com",
    "www.xiaohongshu.com",
    "xiaohongshu.cn",
    "www.xiaohongshu.cn",
    "rednote.com",
    "www.rednote.com",
}
DOUYIN_HOSTS = {
    "v.douyin.com",
    "douyin.com",
    "www.douyin.com",
    "iesdouyin.com",
    "www.iesdouyin.com",
}
GENERIC_HOSTS = {
    "x.com", "www.x.com", "twitter.com", "www.twitter.com",
    "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
    "bilibili.com", "www.bilibili.com", "b23.tv",
    "tiktok.com", "www.tiktok.com", "vm.tiktok.com", "vt.tiktok.com",
    "instagram.com", "www.instagram.com",
    "facebook.com", "www.facebook.com", "fb.watch",
    "pinterest.com", "www.pinterest.com", "pin.it",
    "reddit.com", "www.reddit.com", "old.reddit.com", "redd.it",
    "vimeo.com", "www.vimeo.com",
    "bsky.app", "www.bsky.app",
}


def detect_platform(url):
    host = (urlparse(url).hostname or "").lower()
    if host in DOUYIN_HOSTS:
        return "douyin"
    if host in XHS_HOSTS:
        return "xhs"
    if host in GENERIC_HOSTS:
        return "generic"
    return "unknown"


def group_urls(urls):
    grouped = {"douyin": [], "xhs": [], "generic": [], "unknown": []}
    for url in urls:
        grouped[detect_platform(url)].append(url)
    return grouped
