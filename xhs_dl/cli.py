"""CLI 入口 - 命令行版本"""

import sys
import argparse
from pathlib import Path


def main():
    # Windows 旧式控制台可能使用 GBK；上游标题包含生僻字符时仍应安全显示。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(
        description="xhs-dl: 小红书无水印下载器 (V2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  xhs-dl "http://xhslink.com/o/xxxxx"
  xhs-dl "链接1" "链接2" "链接3"
  xhs-dl -f links.txt
  xhs-dl -f links.txt -o ./我的笔记
  xhs-dl -f links.txt --mode fast          # 快速模式(3-8秒)
  xhs-dl -f links.txt --mode cautious      # 保守模式(25-45秒,默认)
  xhs-dl -f links.txt --mode slow          # 慢速模式(55-85秒)

延迟模式:
  fast        3-8秒      测试少量用，风险高
  normal      8-15秒     日常 10 条以内
  cautious    35-55秒    稳定优先，20 条左右推荐 (默认)
  slow        55-85秒    50 条以上
  very-slow   110-160秒  已被风控过才用

支持直接粘贴整段分享文本，工具自动提取链接。

默认使用本地无水印引擎。需要旧版网页解析时可显式传 --engine v1。
        """
    )
    parser.add_argument("urls", nargs="*", help="小红书链接或分享文本")
    parser.add_argument("-f", "--file", help="从文件读取链接")
    parser.add_argument("-o", "--output", default="./xhs_downloads",
                        help="保存目录 (默认: ./xhs_downloads)")
    parser.add_argument("--mode", default="cautious",
                        choices=["fast", "normal", "cautious", "slow", "very-slow"],
                        help="延迟模式 (默认: cautious)")
    parser.add_argument("--engine", choices=["v2", "v1"], default="v2",
                        help="下载引擎：v2 无水印（默认），v1 旧版水印图")
    parser.add_argument("--engine-home",
                        help="XHS_Downloader 本地目录（通常无需填写）")
    parser.add_argument("--timeout", type=int, default=300,
                        help="每条笔记最大等待秒数（默认: 300）")
    args = parser.parse_args()

    # 无参数启动（例如双击启动文件）时，进入一次粘贴输入模式。
    if not args.urls and not args.file:
        try:
            pasted = input("请粘贴小红书分享文本或链接，然后按回车：\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            pasted = ""
        if pasted:
            args.urls.append(pasted)

    # 收集链接
    from xhs_dl.core.downloader import extract_urls_from_text, XhsDownloader, DELAY_MODES
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

    delay = DELAY_MODES[args.mode]
    print("=" * 60)
    print("  xhs-dl v2.3.1  小红书无水印下载器")
    print(f"  共 {len(all_urls)} 个链接 → {args.output}")
    print(f"  模式: {args.mode} (间隔 {delay[0]}-{delay[1]}秒)")
    if len(all_urls) > 1:
        est_min = delay[0] * (len(all_urls) - 1) // 60
        est_max = delay[1] * (len(all_urls) - 1) // 60
        print(f"  预计耗时: {est_min}-{est_max} 分钟 (仅笔记间隔)")
    print("=" * 60)

    def on_progress(nr, i, total):
        tag = "OK" if nr.success else "FAIL"
        name = (nr.title[:35] or nr.error) if not nr.success else nr.title[:35]
        extra = f" [{nr.image_success}图]" if nr.success and nr.image_count else ""
        print(f"  [{tag}] [{i}/{total}] {name}{extra}")

    if args.engine == "v1":
        print("  [提醒] 正在使用旧版 V1，引擎输出可能带平台水印。")
        dl = XhsDownloader(output_dir=args.output, delay=delay, on_progress=on_progress)
    else:
        from xhs_dl.core.v2_downloader import XhsV2Downloader, EngineNotReady
        try:
            dl = XhsV2Downloader(
                output_dir=args.output,
                delay=delay,
                on_progress=on_progress,
                engine_home=args.engine_home,
                timeout=args.timeout,
            )
        except EngineNotReady as exc:
            print(f"\n[错误] {exc}")
            sys.exit(2)
    result = dl.download(all_urls)

    print(f"\n{'='*60}")
    print(f"  完成  成功: {result.success_count}  失败: {result.fail_count}  总计: {result.total}")
    if result.success_count:
        print(f"  保存至: {result.output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
