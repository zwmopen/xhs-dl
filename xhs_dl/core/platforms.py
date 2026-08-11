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


def detect_platform(url):
    host = (urlparse(url).hostname or "").lower()
    if host in DOUYIN_HOSTS:
        return "douyin"
    if host in XHS_HOSTS:
        return "xhs"
    return "unknown"


def group_urls(urls):
    grouped = {"douyin": [], "xhs": [], "unknown": []}
    for url in urls:
        grouped[detect_platform(url)].append(url)
    return grouped
