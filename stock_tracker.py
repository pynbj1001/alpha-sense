#!/usr/bin/env python
from __future__ import annotations

import importlib.util
import os
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent
TRACKER_BASE = WORKSPACE_ROOT / "11.投资机会跟踪报告"
SCRIPT_PATH = WORKSPACE_ROOT / "08-AI投研工具" / "scripts" / "analysis" / "stock_tracker.py"


def load_tracker_module():
    spec = importlib.util.spec_from_file_location("workspace_stock_tracker", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载日报脚本: {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    os.environ.setdefault("IDEA_TRACKER_BASE_DIR", str(TRACKER_BASE))
    module = load_tracker_module()
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())