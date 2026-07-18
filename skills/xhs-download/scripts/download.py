#!/usr/bin/env python3
"""Stable JSON interface for Codex and OpenClaw callers."""

import argparse
import json
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Download public Xiaohongshu notes")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Share text or one/more URLs")
    source.add_argument("--file", help="UTF-8 file containing share text or URLs")
    parser.add_argument("--output", default="./xhs_downloads")
    parser.add_argument(
        "--mode", default="cautious",
        choices=["fast", "normal", "cautious", "slow", "very-slow"],
    )
    parser.add_argument("--engine-home")
    parser.add_argument("--timeout", type=int, default=300)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        from xhs_dl.core.downloader import DELAY_MODES, extract_urls_from_text
        from xhs_dl.core.v2_downloader import EngineNotReady, XhsV2Downloader
    except ImportError as exc:
        print(json.dumps({
            "success": 0,
            "failed": 1,
            "error": f"xhs-dl is not installed: {exc}",
        }, ensure_ascii=False))
        return 2

    text = args.text
    if args.file:
        try:
            text = Path(args.file).read_text(encoding="utf-8")
        except OSError as exc:
            print(json.dumps({"success": 0, "failed": 1, "error": str(exc)}, ensure_ascii=False))
            return 2
    urls = extract_urls_from_text(text or "")
    if not urls:
        print(json.dumps({"success": 0, "failed": 1, "error": "No supported URL found"}, ensure_ascii=False))
        return 2

    try:
        downloader = XhsV2Downloader(
            output_dir=args.output,
            delay=DELAY_MODES[args.mode],
            engine_home=args.engine_home,
            timeout=args.timeout,
        )
        result = downloader.download(urls)
    except EngineNotReady as exc:
        print(json.dumps({"success": 0, "failed": len(urls), "error": str(exc)}, ensure_ascii=False))
        return 2

    payload = {
        "success": result.success_count,
        "failed": result.fail_count,
        "total": result.total,
        "output_dir": result.output_dir,
        "manifest": str(Path(result.output_dir) / "xhs-dl-batch.json"),
        "items": [
            {
                "url": item.url,
                "success": item.success,
                "title": item.title,
                "note_id": item.note_id,
                "save_dir": item.save_dir,
                "image_count": item.image_count,
                "media_format": item.media_format,
                "error": item.error,
            }
            for item in result.results
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if result.fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
