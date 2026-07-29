"""Windows 便携版入口：发现旁置引擎后启动桌面窗口。"""

import os
import sys
import json
from pathlib import Path


def configure_engine_home(executable=None):
    executable = Path(executable or sys.executable).resolve()
    app_dir = executable.parent
    candidates = (
        app_dir / "XHS_Downloader",
        app_dir.parent / "XHS_Downloader",
        Path(r"D:\AICode\工具开发\projects\XHS_Downloader"),
    )
    for candidate in candidates:
        if (candidate / "main.py").is_file() and (candidate / "source").is_dir():
            os.environ["XHS_DOWNLOADER_HOME"] = str(candidate.resolve())
            return candidate.resolve()
    return None


def main():
    configure_engine_home()
    if "--headless-download" in sys.argv:
        run_headless_download()
        return
    from xhs_dl.desktop.app import main as desktop_main

    desktop_main()


def run_headless_download():
    """Small packaged smoke-test/automation entry used by local AI tools."""
    import argparse

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--headless-download", action="store_true")
    parser.add_argument("--output", required=True)
    parser.add_argument("--result-json")
    parser.add_argument("urls", nargs="+")
    args = parser.parse_args()

    from xhs_dl.core.unified_downloader import UnifiedDownloader

    result = UnifiedDownloader(output_dir=args.output, delay=(0, 0)).download(args.urls)
    payload = {
        "success": result.success_count,
        "failed": result.fail_count,
        "total": result.total,
        "output_dir": result.output_dir,
        "items": [
            {
                "url": item.url,
                "success": item.success,
                "title": item.title,
                "save_dir": item.save_dir,
                "error": item.error,
            }
            for item in result.results
        ],
    }
    if args.result_json:
        Path(args.result_json).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    raise SystemExit(0 if result.fail_count == 0 else 1)


if __name__ == "__main__":
    main()
