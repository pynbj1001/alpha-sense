# -*- coding: utf-8 -*-
"""
自动化投研看板生成脚本
功能：扫描 11.投资机会跟踪报告 和 05-个股与公司研究，生成 DASHBOARD.md
"""

import os
import re
from pathlib import Path
from datetime import datetime


def generate_dashboard():
    # 获取脚本所在位置，向上三级到达项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(script_dir))))
    dashboard_path = project_root / "DASHBOARD.md"

    # 扫描目录
    research_dirs = [
        project_root / "10-研究报告输出",
        project_root / "10-研究报告输出/存量报告",
        project_root / "11.投资机会跟踪报告",
        project_root / "11.投资机会跟踪报告/daily_reports",
        project_root / "05-个股与公司研究",
    ]

    stocks = {}

    # 更健壮的解析：先提取日期，再提取股票名和Level
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    level_pattern = re.compile(r"(L\d)")
    # 匹配 "个股-" 后面的完整名称（中文+英文+代码）
    stock_pattern = re.compile(r"个股[-.]\s*(.+?)(?:-(?:L\d|多框架|六层|价值投资|fsp))", re.IGNORECASE)
    # 从名称中提取纯ticker（2-5个大写字母）
    ticker_pattern = re.compile(r"\b([A-Z]{2,5})\b")
    # 从名称中提取中文部分
    cn_name_pattern = re.compile(r"([\u4e00-\u9fff]+)")

    for r_dir in research_dirs:
        if not r_dir.exists():
            continue
        
        for item in r_dir.iterdir():
            if item.is_file() and item.suffix in [".pdf", ".docx", ".txt", ".md"]:
                name = item.name
                
                if "个股" not in name and not any(lvl in name for lvl in ["L1", "L2", "L3", "L4", "L5", "L6"]):
                    continue

                # 提取日期
                date_match = date_pattern.search(name)
                date_str = date_match.group(1) if date_match else datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d")
                
                # 提取Level
                level_match = level_pattern.search(name)
                level = level_match.group(1) if level_match else "L?"
                
                # 提取股票名称
                stock_match = stock_pattern.search(name)
                if stock_match:
                    raw_name = stock_match.group(1).strip(" -_")
                else:
                    raw_name = name.split("-")[-1].split(".")[0] if "-" in name else name.split(".")[0]
                
                # 从名称提取ticker和中文名
                ticker_match = ticker_pattern.search(raw_name)
                ticker = ticker_match.group(1) if ticker_match else ""
                cn_match = cn_name_pattern.search(raw_name)
                cn_name = cn_match.group(1) if cn_match else ""
                
                # 组合显示名
                if cn_name and ticker:
                    display_name = f"{cn_name} ({ticker})"
                elif cn_name:
                    display_name = cn_name
                elif ticker:
                    display_name = ticker
                else:
                    display_name = raw_name
                
                # 使用ticker（如有）或中文名作为聚合key
                key = ticker if ticker else (cn_name if cn_name else raw_name)
                
                if key not in stocks:
                    stocks[key] = {"name": display_name, "ticker": ticker, "levels": {}, "last_updated": date_str}
                
                if level not in stocks[key]["levels"]:
                    stocks[key]["levels"][level] = []
                
                stocks[key]["levels"][level].append({"name": name, "path": os.path.relpath(item, project_root), "date": date_str})
                
                # 更新最新日期
                if date_str > stocks[key]["last_updated"]:
                    stocks[key]["last_updated"] = date_str

    # 按最新日期降序排序
    sorted_stocks = sorted(stocks.values(), key=lambda x: x["last_updated"], reverse=True)

    # 生成 Markdown 内容
    lines = [
        f"# 🚀 投研机会看板 (Dashboard)\n",
        f"> **自动更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"> 本看板通过扫描 `11.投资机会跟踪报告` 及 `05-个股与公司研究` 自动生成。\n\n",
        "## 📈 核心研究覆盖矩阵\n\n",
        "| 个股 | 代码 | 最新更新 | 研究进度 | 核心研报汇总 |\n",
        "| :--- | :--- | :--- | :--- | :--- |\n"
    ]

    for s in sorted_stocks:
        levels_str = " ".join([f"`{lvl}`" for lvl in sorted(s["levels"].keys())])
        links = []
        # 每个级别取一个最新的链接
        for lvl in sorted(s["levels"].keys(), reverse=True):
            latest_file = sorted(s["levels"][lvl], key=lambda x: x["date"], reverse=True)[0]
            link_name = f"{lvl}研报"
            links.append(f"[{link_name}]({latest_file['path'].replace(os.sep, '/')})")
        
        lines.append(f"| {s['name']} | `{s['ticker']}` | {s['last_updated']} | {levels_str} | {' | '.join(links[:3])} |\n")

    lines.append("\n---\n\n")
    lines.append("## 📅 近期研究产出动态\n\n")
    
    # 列出最近 20 个文件
    all_files = []
    for s in stocks.values():
        for lvl_files in s["levels"].values():
            all_files.extend(lvl_files)
    
    sorted_files = sorted(all_files, key=lambda x: x["date"], reverse=True)[:20]
    
    for f in sorted_files:
        lines.append(f"- **[{f['date']}]** [{f['name']}]({f['path'].replace(os.sep, '/')})\n")

    lines.append(f"\n\n*提示：如需更新看板，请在根目录运行: `python \"08-AI投研工具/scripts/system/generate_dashboard.py\"`*")

    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    print(f"✅ 看板已更新: {dashboard_path}")


if __name__ == "__main__":
    generate_dashboard()
