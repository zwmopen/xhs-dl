import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from xhs_dl.core.downloader import extract_urls_from_text

def test_extract_urls():
    text = """
    快存下！vivo X300隐藏功能！ http://xhslink.com/o/70dt8TsFJon
    【小红书】里的笔记已备好，复制后快来~红米 Watch 6 19个隐藏功能 http://xhslink.com/o/4FGTfCCdPew
    """
    urls = extract_urls_from_text(text)
    assert len(urls) == 2
    assert urls[0] == "http://xhslink.com/o/70dt8TsFJon"
    assert urls[1] == "http://xhslink.com/o/4FGTfCCdPew"
    print("extract_urls: PASS")

def test_parse_note_id():
    from xhs_dl.core.downloader import XhsDownloader
    assert XhsDownloader._parse_note_id(
        "https://www.xiaohongshu.com/discovery/item/6a50b32f000000000603721e?xsec_token=xxx"
    ) == "6a50b32f000000000603721e"
    assert XhsDownloader._parse_note_id(
        "https://www.xiaohongshu.com/explore/6a4dc64100000000220147df"
    ) == "6a4dc64100000000220147df"
    assert XhsDownloader._parse_note_id("https://example.com") == ""
    print("parse_note_id: PASS")

def test_sanitize():
    from xhs_dl.core.downloader import XhsDownloader
    assert XhsDownloader._sanitize('A<B>C:D/E\\F|G?H*I')
    assert XhsDownloader._sanitize("") == "untitled"
    long_name = "x" * 100
    assert len(XhsDownloader._sanitize(long_name)) == 60
    print("sanitize: PASS")

def test_extract_ssr_state():
    from xhs_dl.core.downloader import XhsDownloader
    html = '<script>window.__INITIAL_STATE__={"a":1,"b":{"c":2}}</script>'
    state = XhsDownloader._extract_ssr_state(html)
    assert state == {"a": 1, "b": {"c": 2}}
    print("extract_ssr_state: PASS")

if __name__ == "__main__":
    test_extract_urls()
    test_parse_note_id()
    test_sanitize()
    test_extract_ssr_state()
    print("\nAll tests passed!")