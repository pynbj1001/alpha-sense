#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动化投资体系 — 定时运行 + 弹窗提醒

三种模式：
  --mode macro   周日 20:00  宏观环境扫描
  --mode stock   周三 20:00  个股深度分析（弹窗输入标的）
  --mode review  周五 20:00  本周复盘提醒

用法：
  python tools/auto_investment_system.py --mode macro
  python tools/auto_investment_system.py --mode stock
  python tools/auto_investment_system.py --mode stock --ticker NVDA
  python tools/auto_investment_system.py --mode review
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime, date
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 路径设置
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
REPORT_DIR = ROOT / "10-研究报告输出"
LOG_DIR = ROOT / "tasks"

sys.path.insert(0, str(TOOLS_DIR))

# ---------------------------------------------------------------------------
# 延迟导入自有模块（容错）
# ---------------------------------------------------------------------------
try:
    from data_toolkit import (
        fetch_stock_snapshot,
        fetch_macro_snapshot,
        fetch_financial_statements,
        fetch_industry_comparison,
        snapshot_to_markdown,
        macro_to_markdown,
        comparison_to_markdown,
    )
    HAS_TOOLKIT = True
except ImportError:
    HAS_TOOLKIT = False

try:
    from report_templates import (
        generate_stock_research_report,
        generate_macro_outlook_report,
    )
    HAS_TEMPLATES = True
except ImportError:
    HAS_TEMPLATES = False


# ---------------------------------------------------------------------------
# GUI 工具类（tkinter）
# ---------------------------------------------------------------------------

def _ensure_tk():
    """确保 tkinter 可用"""
    import tkinter as tk
    return tk


def show_info(title: str, message: str) -> None:
    """显示信息弹窗"""
    tk = _ensure_tk()
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showinfo(title, message, parent=root)
    root.destroy()


def show_result_window(title: str, content: str, report_path: str | None = None) -> None:
    """显示带滚动条的结果展示窗口"""
    tk = _ensure_tk()
    from tkinter import scrolledtext

    root = tk.Tk()
    root.title(title)
    root.attributes("-topmost", True)
    root.geometry("900x700")
    root.configure(bg="#1a1a2e")

    # 标题
    header = tk.Frame(root, bg="#16213e", pady=10)
    header.pack(fill="x")
    tk.Label(
        header,
        text=f"📊 {title}",
        font=("Microsoft YaHei UI", 16, "bold"),
        fg="#e94560",
        bg="#16213e",
    ).pack()
    tk.Label(
        header,
        text=f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        font=("Microsoft YaHei UI", 10),
        fg="#a0a0a0",
        bg="#16213e",
    ).pack()

    # 内容区
    text_area = scrolledtext.ScrolledText(
        root,
        wrap="word",
        font=("Consolas", 11),
        bg="#0f3460",
        fg="#e0e0e0",
        insertbackground="white",
        padx=15,
        pady=15,
        relief="flat",
    )
    text_area.pack(fill="both", expand=True, padx=10, pady=5)
    text_area.insert("1.0", content)
    text_area.config(state="disabled")

    # 按钮区
    btn_frame = tk.Frame(root, bg="#1a1a2e", pady=10)
    btn_frame.pack(fill="x")

    if report_path and Path(report_path).exists():
        def open_report():
            os.startfile(str(report_path))

        tk.Button(
            btn_frame,
            text="📄 打开报告文件",
            font=("Microsoft YaHei UI", 11),
            bg="#e94560",
            fg="white",
            relief="flat",
            padx=20,
            pady=8,
            command=open_report,
        ).pack(side="left", padx=20)

    tk.Button(
        btn_frame,
        text="✅ 关闭",
        font=("Microsoft YaHei UI", 11),
        bg="#533483",
        fg="white",
        relief="flat",
        padx=20,
        pady=8,
        command=root.destroy,
    ).pack(side="right", padx=20)

    root.mainloop()


def ask_ticker() -> str | None:
    """弹窗询问用户要分析的股票代码"""
    tk = _ensure_tk()

    result = {"ticker": None}

    root = tk.Tk()
    root.title("📈 投资体系 — 本周分析标的")
    root.attributes("-topmost", True)
    root.geometry("500x350")
    root.configure(bg="#1a1a2e")

    tk.Label(
        root,
        text="📈 本周深度分析",
        font=("Microsoft YaHei UI", 18, "bold"),
        fg="#e94560",
        bg="#1a1a2e",
    ).pack(pady=(25, 5))

    tk.Label(
        root,
        text="请输入你本周想要深度分析的股票代码：",
        font=("Microsoft YaHei UI", 12),
        fg="#e0e0e0",
        bg="#1a1a2e",
    ).pack(pady=10)

    tk.Label(
        root,
        text="示例：NVDA, AAPL, MSFT, GOOGL, 600519.SS",
        font=("Microsoft YaHei UI", 9),
        fg="#a0a0a0",
        bg="#1a1a2e",
    ).pack()

    entry = tk.Entry(
        root,
        font=("Consolas", 16),
        bg="#0f3460",
        fg="#e0e0e0",
        insertbackground="white",
        justify="center",
        relief="flat",
    )
    entry.pack(pady=15, padx=50, fill="x")
    entry.focus_set()

    def on_submit():
        ticker = entry.get().strip().upper()
        if ticker:
            result["ticker"] = ticker
            root.destroy()

    def on_skip():
        root.destroy()

    entry.bind("<Return>", lambda e: on_submit())

    btn_frame = tk.Frame(root, bg="#1a1a2e")
    btn_frame.pack(pady=10)

    tk.Button(
        btn_frame,
        text="🚀 开始分析",
        font=("Microsoft YaHei UI", 12),
        bg="#e94560",
        fg="white",
        relief="flat",
        padx=25,
        pady=8,
        command=on_submit,
    ).pack(side="left", padx=15)

    tk.Button(
        btn_frame,
        text="⏭ 本周跳过",
        font=("Microsoft YaHei UI", 12),
        bg="#533483",
        fg="white",
        relief="flat",
        padx=25,
        pady=8,
        command=on_skip,
    ).pack(side="left", padx=15)

    root.mainloop()
    return result["ticker"]


def show_loading(title: str = "分析中...") -> tuple:
    """显示加载动画窗口，返回 (root, stop_event)"""
    tk = _ensure_tk()
    stop_event = threading.Event()

    def _run():
        root = tk.Tk()
        root.title(title)
        root.attributes("-topmost", True)
        root.geometry("400x150")
        root.configure(bg="#1a1a2e")
        root.overrideredirect(True)

        # 居中显示
        root.update_idletasks()
        w, h = 400, 150
        x = (root.winfo_screenwidth() // 2) - (w // 2)
        y = (root.winfo_screenheight() // 2) - (h // 2)
        root.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(
            root,
            text="⏳ 正在获取数据并生成报告...",
            font=("Microsoft YaHei UI", 14),
            fg="#e94560",
            bg="#1a1a2e",
        ).pack(pady=30)

        dots = tk.Label(
            root,
            text="请稍候",
            font=("Microsoft YaHei UI", 11),
            fg="#a0a0a0",
            bg="#1a1a2e",
        )
        dots.pack()

        frame_count = [0]
        anim_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        def animate():
            if stop_event.is_set():
                root.destroy()
                return
            frame_count[0] = (frame_count[0] + 1) % len(anim_chars)
            dots.config(text=f"{anim_chars[frame_count[0]]} 数据拉取中，请稍候...")
            root.after(120, animate)

        animate()
        root.mainloop()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t, stop_event


# ---------------------------------------------------------------------------
# 模式一：宏观扫描
# ---------------------------------------------------------------------------

def run_macro() -> None:
    """周日宏观环境扫描"""
    if not HAS_TOOLKIT:
        show_info("❌ 错误", "data_toolkit.py 未找到或无法导入。\n请确保 tools/ 目录下有该文件。")
        return

    # 显示加载
    loader, stop = show_loading("宏观扫描中...")

    try:
        # 拉取数据
        macro = fetch_macro_snapshot()
        macro_md = macro_to_markdown(macro)

        # 生成报告
        report_path = None
        if HAS_TEMPLATES:
            report_content = generate_macro_outlook_report(
                macro_md=macro_md,
                executive_summary=[
                    f"宏观数据截至 {datetime.now().strftime('%Y-%m-%d %H:%M')}，数据源：{', '.join(macro.sources) or 'N/A'}",
                    f"VIX 恐慌指数：{macro.vix or 'N/A'} | 黄金：${macro.gold or 'N/A'}/oz | 原油：${macro.oil_wti or 'N/A'}/bbl",
                    "请结合周金涛周期+李蓓宏观对冲框架判断当前周期位置。",
                ],
                sources=macro.sources,
                save=True,
            )
            report_path = str(REPORT_DIR / f"{date.today().isoformat()}-宏观-AI展望报告.md")

        # 构建展示内容
        display = [
            "=" * 60,
            "  📊 本周宏观环境扫描结果",
            "=" * 60,
            "",
            macro_md,
            "",
            "─" * 60,
            "💡 下一步建议：",
            "  1. 对照周金涛周期框架，确认当前在第六波康波的哪个阶段",
            "  2. 用李蓓的宏观对冲体系判断信用/利率/权益三维信号",
            "  3. 检查乱世策略的配置比例是否需要调整",
            "─" * 60,
        ]
    finally:
        stop.set()

    show_result_window(
        "本周宏观环境扫描",
        "\n".join(display),
        report_path,
    )


# ---------------------------------------------------------------------------
# 模式二：个股深度分析
# ---------------------------------------------------------------------------

def run_stock(ticker: str | None = None) -> None:
    """周三个股深度分析"""
    if not HAS_TOOLKIT:
        show_info("❌ 错误", "data_toolkit.py 未找到或无法导入。")
        return

    # 如果没有预设标的，弹窗询问
    if not ticker:
        ticker = ask_ticker()
    if not ticker:
        show_info("⏭ 已跳过", "本周未选择分析标的。下周三会再次提醒。")
        return

    # 加载动画
    loader, stop = show_loading(f"分析 {ticker} 中...")

    try:
        # 拉取全量数据
        snap = fetch_stock_snapshot(ticker)
        snap_md = snapshot_to_markdown(snap)
        fin = fetch_financial_statements(ticker)

        # 生成报告
        report_path = None
        if HAS_TEMPLATES:
            from data_toolkit import _fmt_num, _fmt_pct

            summary_points = [
                f"{snap.ticker} ({snap.name}) 当前价格 {_fmt_num(snap.price)} {snap.currency}，PE(TTM) {_fmt_num(snap.pe_ttm)}",
            ]
            if snap.roe:
                summary_points.append(f"ROE {_fmt_pct(snap.roe)}，毛利率 {_fmt_pct(snap.gross_margin)}，盈利增速 {_fmt_pct(snap.earnings_growth)}")
            summary_points.append("请结合多框架验证（巴菲特护城河+戴维斯双击+周期定位）后再做决策。")

            generate_stock_research_report(
                ticker=ticker,
                snapshot_md=snap_md,
                executive_summary=summary_points,
                sources=snap.sources,
                save=True,
            )
            safe_ticker = ticker.replace(".", "_")
            report_path = str(REPORT_DIR / f"{date.today().isoformat()}-个股-{safe_ticker}-AI深度研究.md")

        # 构建展示内容
        display = [
            "=" * 60,
            f"  📊 {ticker} ({snap.name}) 深度分析结果",
            "=" * 60,
            "",
            snap_md,
            "",
        ]

        # 财务报表摘要
        if fin.get("income_statement"):
            inc = fin["income_statement"]
            display.append("### 📋 最新财务报表摘要")
            display.append("")
            if inc.get("total_revenue"):
                display.append(f"  营收：{_fmt_num(inc['total_revenue'])}")
            if inc.get("net_income"):
                display.append(f"  净利：{_fmt_num(inc['net_income'])}")
            if inc.get("period_end"):
                display.append(f"  报告期：{inc['period_end']}")
            display.append("")

        # 七道关卡快速检查
        display.extend([
            "─" * 60,
            "🔍 乱世策略七道关卡（快速预检）：",
            "",
            f"  ① 周期对齐  → 第六波康波导入期，{'AI/科技标的对齐 ✅' if snap.revenue_growth and snap.revenue_growth > 0.1 else '需核实周期位置 ⚠️'}",
            f"  ② 护城河    → ROE {_fmt_pct(snap.roe)}{'，>15% ✅' if snap.roe and snap.roe > 0.15 else '，需深入评估 ⚠️'}",
            f"  ③ 拐点确认  → 盈利增速 {_fmt_pct(snap.earnings_growth)}{'，正增长 ✅' if snap.earnings_growth and snap.earnings_growth > 0 else '，关注拐点 ⚠️'}",
            f"  ④ 估值评估  → PE {_fmt_num(snap.pe_ttm)}{'，<25 合理 ✅' if snap.pe_ttm and snap.pe_ttm < 25 else '，需结合成长性判断 ⚠️'}",
            f"  ⑤ 地缘风险  → 需人工评估（美元指数/制裁/供应链）",
            f"  ⑥ 仓位适配  → 建议初始仓位 3-5%",
            f"  ⑦ Kill-Switch → {'无明显红线' if snap.current_ratio and snap.current_ratio > 0.5 else '注意流动性指标 ⚠️'}",
            "",
            "─" * 60,
            "💡 下一步建议：",
            "  1. 运行 @分析 深度了解公司基本面",
            "  2. 运行 @估值 做 DCF + Comps 多方法估值",
            "  3. 运行 @陷阱 检查价值陷阱",
            "  4. 在 @日志 中记录你的判断和理由",
            "─" * 60,
        ])
    finally:
        stop.set()

    show_result_window(
        f"{ticker} 深度分析",
        "\n".join(display),
        report_path,
    )


# ---------------------------------------------------------------------------
# 模式三：本周复盘
# ---------------------------------------------------------------------------

def run_review() -> None:
    """周五复盘提醒"""
    tk = _ensure_tk()

    # 检查本周生成的报告
    reports = []
    if REPORT_DIR.exists():
        today = date.today()
        week_start = today.isoformat()[:8]  # 同月份的近期文件
        for f in sorted(REPORT_DIR.glob("*.md"), reverse=True):
            if f.name.startswith(str(today.year)):
                reports.append(f.name)
            if len(reports) >= 10:
                break

    # 构建复盘提示内容
    display = [
        "=" * 60,
        "  📓 本周投资复盘提醒",
        "=" * 60,
        "",
        f"日期：{date.today().isoformat()}（周五）",
        "",
        "─" * 60,
        "📋 本周需要复盘的问题：",
        "",
        "  1. 本周的宏观环境有什么变化？",
        "  2. 关注的标的发生了什么新信息？",
        "  3. 本周有没有做交易？为什么？",
        "  4. 有没有偏离了自己的投资铁律？",
        "  5. 有没有出现情绪化决策？（恐惧/贪婪）",
        "  6. 下周需要关注什么事件/催化剂？",
        "",
        "─" * 60,
        "📂 本期间生成的报告：",
        "",
    ]
    if reports:
        for r in reports[:10]:
            display.append(f"  • {r}")
    else:
        display.append("  （本周暂无自动生成的报告）")

    display.extend([
        "",
        "─" * 60,
        "💡 建议操作：",
        "  1. 在对话框中运行 @日志，记录本周思考",
        "  2. 打开 tasks/lessons.md，记录经验教训",
        "  3. 检查持仓是否需要调整仓位",
        "─" * 60,
    ])

    # 弹窗展示
    root = tk.Tk()
    root.title("📓 本周投资复盘")
    root.attributes("-topmost", True)
    root.geometry("700x600")
    root.configure(bg="#1a1a2e")

    from tkinter import scrolledtext

    # 标题
    header = tk.Frame(root, bg="#16213e", pady=10)
    header.pack(fill="x")
    tk.Label(
        header,
        text="📓 本周投资复盘时间",
        font=("Microsoft YaHei UI", 16, "bold"),
        fg="#e94560",
        bg="#16213e",
    ).pack()

    # 内容
    text = scrolledtext.ScrolledText(
        root,
        wrap="word",
        font=("Consolas", 11),
        bg="#0f3460",
        fg="#e0e0e0",
        padx=15,
        pady=15,
        relief="flat",
    )
    text.pack(fill="both", expand=True, padx=10, pady=5)
    text.insert("1.0", "\n".join(display))
    text.config(state="disabled")

    # 按钮
    btn_frame = tk.Frame(root, bg="#1a1a2e", pady=10)
    btn_frame.pack(fill="x")

    def open_log():
        log_file = LOG_DIR / "lessons.md"
        if not log_file.exists():
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_file.write_text(f"# 投资经验教训日志\n\n## {date.today().isoformat()}\n\n- \n", encoding="utf-8")
        os.startfile(str(log_file))

    def open_reports():
        if REPORT_DIR.exists():
            os.startfile(str(REPORT_DIR))

    tk.Button(
        btn_frame,
        text="📝 打开教训日志",
        font=("Microsoft YaHei UI", 11),
        bg="#e94560",
        fg="white",
        relief="flat",
        padx=15,
        pady=8,
        command=open_log,
    ).pack(side="left", padx=10)

    tk.Button(
        btn_frame,
        text="📂 打开报告文件夹",
        font=("Microsoft YaHei UI", 11),
        bg="#0f3460",
        fg="white",
        relief="flat",
        padx=15,
        pady=8,
        command=open_reports,
    ).pack(side="left", padx=10)

    tk.Button(
        btn_frame,
        text="✅ 关闭",
        font=("Microsoft YaHei UI", 11),
        bg="#533483",
        fg="white",
        relief="flat",
        padx=15,
        pady=8,
        command=root.destroy,
    ).pack(side="right", padx=10)

    root.mainloop()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="自动化投资体系 — 定时运行 + 弹窗提醒",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["macro", "stock", "review"],
        required=True,
        help=(
            "运行模式：\n"
            "  macro   宏观环境扫描（周日20:00）\n"
            "  stock   个股深度分析（周三20:00）\n"
            "  review  本周复盘提醒（周五20:00）"
        ),
    )
    parser.add_argument(
        "--ticker",
        default=None,
        help="个股分析时的股票代码（可选，不填则弹窗询问）",
    )

    args = parser.parse_args()

    if args.mode == "macro":
        run_macro()
    elif args.mode == "stock":
        run_stock(args.ticker)
    elif args.mode == "review":
        run_review()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
