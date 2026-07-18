"""CLI 入口 - 命令行版本"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="xhs-dl: 小红书笔记下载器 (V1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  xhs-dl "http://xhslink.com/o/xxxxx"
  xhs-dl "链接1" "链接2" "链接3"
  xhs-dl -f links.txt
  xhs-dl -f links.txt -o ./我的笔记

支持直接粘贴整段分享文本，工具自动提取链接。

注意: 下载的图片带有小红书平台水印（服务端烧录，无法去除）。
        """
    )
    parser.add_argument("urls", nargs="*", help="小红书链接或分享文本")
    parser.add_argument("-f", "--file", help="从文件读取链接")
    parser.add_argument("-o", "--output", default="./xhs_downloads",
                        help="保存目录 (默认: ./xhs_downloads)")
    args = parser.parse_args()

    # 收集链接
    from xhs_dl.core.downloader import extract_urls_from_text, XhsDownloader
    all_urls = []
    for arg in args.urls:
        found = extract_urls_from_text(arg)
        if found:
            all_urls.extend(found)
        elif arg.startswith("http") or arg.startswith("xhslink"):
            all_urls.append(arg)
    if args.file:
        p = Path(args.file)
        if not p.exists():
            print(f"[错误] 文件不存在: {args.file}")
            sys.exit(1)
        all_urls.extend(extract_urls_from_text(p.read_text("utf-8")))

    if not all_urls:
        parser.print_help()
        print("\n[提示] 未检测到链接。")
        sys.exit(1)

    print("=" * 60)
    print("  xhs-dl v1.0  小红书笔记下载器")
    print(f"  共 {len(all_urls)} 个链接 → {args.output}")
    print("=" * 60)

    def on_progress(nr, i, total):
        tag = "OK" if nr.success else "FAIL"
        name = (nr.title[:35] or nr.error) if not nr.success else nr.title[:35]
        extra = f" [{nr.image_success}图]" if nr.success and nr.image_count else ""
        print(f"  [{tag}] [{i}/{total}] {name}{extra}")

    dl = XhsDownloader(output_dir=args.output, on_progress=on_progress)
    result = dl.download(all_urls)

    print(f"\n{'='*60}")
    print(f"  完成  成功: {result.success_count}  失败: {result.fail_count}  总计: {result.total}")
    if result.success_count:
        print(f"  保存至: {result.output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()