# -*- coding: utf-8 -*-
"""
万能素材剪贴板智能采集守护神 (向后兼容入口)
已正式升级为 universal_clipboard_collector.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from universal_clipboard_collector import main

if __name__ == "__main__":
    main()
