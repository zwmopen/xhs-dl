"""由 XHS-Downloader 的隔离 Python 调用：一次完成下载并返回笔记元数据。"""

import argparse
import asyncio
import json
import os
import sys


MARKER = "__XHS_DL_METADATA__"


async def run(url, work_path, folder_name):
    sys.path.insert(0, os.getcwd())
    from source import XHS

    async with XHS(
        work_path=work_path,
        folder_name=folder_name,
        image_format="PNG",
        folder_mode=True,
        record_data=False,
        download_record=False,
        author_archive=False,
        language="zh_CN",
    ) as client:
        items = await client.extract(url, download=True, data=True)
    payload = items[0] if items else {}
    print(MARKER + json.dumps(payload, ensure_ascii=False, default=str))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--work-path", required=True)
    parser.add_argument("--folder-name", required=True)
    args = parser.parse_args()
    asyncio.run(run(args.url, args.work_path, args.folder_name))


if __name__ == "__main__":
    main()
