#!/usr/bin/env python3
"""Check whether the local xhs-dl V2 engine is ready."""

import json
import sys


def main() -> int:
    status = {"ready": False, "version": "", "engine_home": "", "error": ""}
    try:
        import xhs_dl
        from xhs_dl.core.v2_downloader import LocalCliEngine

        engine = LocalCliEngine()
        status.update({
            "ready": True,
            "version": xhs_dl.__version__,
            "engine_home": str(engine.home),
        })
    except Exception as exc:
        status["error"] = str(exc)
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if status["ready"] else 2


if __name__ == "__main__":
    sys.exit(main())
