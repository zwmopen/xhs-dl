"""Windows 便携版入口：发现旁置引擎后启动桌面窗口。"""

import os
import sys
from pathlib import Path


def configure_engine_home(executable=None):
    executable = Path(executable or sys.executable).resolve()
    app_dir = executable.parent
    candidates = (
        app_dir / "XHS_Downloader",
        app_dir.parent / "XHS_Downloader",
        Path(r"D:\AICode\XHS_Downloader"),
    )
    for candidate in candidates:
        if (candidate / "main.py").is_file() and (candidate / "source").is_dir():
            os.environ["XHS_DOWNLOADER_HOME"] = str(candidate.resolve())
            return candidate.resolve()
    return None


def main():
    configure_engine_home()
    from xhs_dl.desktop.app import main as desktop_main

    desktop_main()


if __name__ == "__main__":
    main()
