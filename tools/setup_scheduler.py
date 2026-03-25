#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
定时任务注册器 — 将投资体系注册到 Windows 任务计划程序

用法：
  python tools/setup_scheduler.py install    注册定时任务
  python tools/setup_scheduler.py uninstall  卸载定时任务
  python tools/setup_scheduler.py status     查看任务状态

定时任务：
  InvestSystem_Macro   每周日 20:00 宏观扫描
  InvestSystem_Stock   每周三 20:00 个股分析
  InvestSystem_Review  每周五 20:00 本周复盘
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
MAIN_SCRIPT = TOOLS_DIR / "auto_investment_system.py"

# 尝试定位 Python 解释器
PYTHON_EXE = None
for candidate in [
    ROOT / ".venv-1" / "Scripts" / "python.exe",
    ROOT / ".venv" / "Scripts" / "python.exe",
    Path(sys.executable),
]:
    if candidate.exists():
        PYTHON_EXE = str(candidate)
        break

if PYTHON_EXE is None:
    PYTHON_EXE = sys.executable

TASKS = [
    {
        "name": "InvestSystem_Macro",
        "desc": "投资体系：每周日宏观环境扫描",
        "day": "SUN",
        "time": "20:00",
        "mode": "macro",
    },
    {
        "name": "InvestSystem_Stock",
        "desc": "投资体系：每周三个股深度分析",
        "day": "WED",
        "time": "20:00",
        "mode": "stock",
    },
    {
        "name": "InvestSystem_Review",
        "desc": "投资体系：每周五复盘提醒",
        "day": "FRI",
        "time": "20:00",
        "mode": "review",
    },
]


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """运行命令"""
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def install() -> None:
    """注册定时任务"""
    print("=" * 50)
    print("  📅 注册投资体系定时任务")
    print("=" * 50)
    print()
    print(f"  Python: {PYTHON_EXE}")
    print(f"  脚本:   {MAIN_SCRIPT}")
    print()

    for task in TASKS:
        cmd = [
            "schtasks", "/Create",
            "/TN", task["name"],
            "/TR", f'"{PYTHON_EXE}" "{MAIN_SCRIPT}" --mode {task["mode"]}',
            "/SC", "WEEKLY",
            "/D", task["day"],
            "/ST", task["time"],
            "/F",  # 覆盖已有任务
        ]
        try:
            result = _run(cmd)
            print(f"  ✅ {task['name']} — {task['desc']} ({task['day']} {task['time']})")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ {task['name']} 注册失败: {e.stderr}")

    print()
    print("  ✅ 全部注册完成！")
    print()
    print("  定时任务运行时间：")
    print("    📊 周日 20:00 — 宏观环境扫描")
    print("    📈 周三 20:00 — 个股深度分析（弹窗输入标的）")
    print("    📓 周五 20:00 — 本周复盘提醒")
    print()
    print("  你也可以随时手动运行：")
    print(f'    {PYTHON_EXE} "{MAIN_SCRIPT}" --mode macro')
    print(f'    {PYTHON_EXE} "{MAIN_SCRIPT}" --mode stock --ticker NVDA')
    print(f'    {PYTHON_EXE} "{MAIN_SCRIPT}" --mode review')


def uninstall() -> None:
    """卸载定时任务"""
    print("=" * 50)
    print("  🗑️ 卸载投资体系定时任务")
    print("=" * 50)
    print()

    for task in TASKS:
        try:
            _run(["schtasks", "/Delete", "/TN", task["name"], "/F"])
            print(f"  ✅ 已删除: {task['name']}")
        except subprocess.CalledProcessError:
            print(f"  ⚠️ {task['name']} 不存在或已删除")

    print()
    print("  ✅ 卸载完成")


def status() -> None:
    """查看任务状态"""
    print("=" * 50)
    print("  📋 投资体系定时任务状态")
    print("=" * 50)
    print()

    for task in TASKS:
        try:
            result = _run(
                ["schtasks", "/Query", "/TN", task["name"], "/FO", "LIST"],
                check=False,
            )
            if result.returncode == 0:
                # 提取关键信息
                lines = result.stdout.strip().split("\n")
                status_line = ""
                next_run = ""
                for line in lines:
                    if "状态" in line or "Status" in line:
                        status_line = line.strip()
                    if "下次运行" in line or "Next Run" in line:
                        next_run = line.strip()
                print(f"  ✅ {task['name']} ({task['desc']})")
                if status_line:
                    print(f"     {status_line}")
                if next_run:
                    print(f"     {next_run}")
            else:
                print(f"  ❌ {task['name']} — 未注册")
        except Exception as e:
            print(f"  ❌ {task['name']} — 查询失败: {e}")

    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="投资体系定时任务管理")
    parser.add_argument(
        "action",
        choices=["install", "uninstall", "status"],
        help="install=注册, uninstall=卸载, status=查看状态",
    )
    args = parser.parse_args()

    if args.action == "install":
        install()
    elif args.action == "uninstall":
        uninstall()
    elif args.action == "status":
        status()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
