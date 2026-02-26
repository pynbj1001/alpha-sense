#!/usr/bin/env python
"""
buyside_daily_data.py — 买方日报数据拉取工具
====================================================
用途：为买方机构级日报（buyside-daily-monitor skill）提供实时价格/估值快照。
运行：python tools/buyside_daily_data.py [--output json|md] [--tickers TICKER1 TICKER2 ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_PATH = ROOT / "11.投资机会跟踪报告" / "ideas_watchlist.json"
REPORT_DIR = ROOT / "11.投资机会跟踪报告" / "daily_reports"
OUTPUT_DIR = ROOT / "11.投资机会跟踪报告" / "daily_reports"

# ─── 依赖检查 ────────────────────────────────────────────────────────────────
try:
    import yfinance as yf  # type: ignore
except ImportError:
    print("❌ 需要安装 yfinance：pip install yfinance", file=sys.stderr)
    sys.exit(1)


# ─── 数据拉取 ─────────────────────────────────────────────────────────────────

def load_watchlist() -> dict:
    """读取 ideas_watchlist.json"""
    if not WATCHLIST_PATH.exists():
        print(f"⚠️  未找到 watchlist：{WATCHLIST_PATH}", file=sys.stderr)
        return {}
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_price_snapshot(tickers: list[str]) -> dict[str, dict]:
    """
    批量拉取美股/港股价格快照。
    返回：{ ticker: {price, pct_52w_percentile, pe_ttm, pb, ev_ebitda, target_mean, data_date} }
    """
    result: dict[str, dict] = {}
    for t in tickers:
        try:
            ticker_obj = yf.Ticker(t)
            info = ticker_obj.info
            hist = ticker_obj.history(period="52wk")

            cur = info.get("currentPrice") or info.get("regularMarketPrice")
            if hist.empty or cur is None:
                result[t] = {"error": "无价格数据", "data_date": datetime.now().strftime("%Y-%m-%d")}
                continue

            w52_low = float(hist["Close"].min())
            w52_high = float(hist["Close"].max())
            pct_52w = (
                round((cur - w52_low) / (w52_high - w52_low) * 100, 1)
                if (w52_high - w52_low) > 0
                else None
            )

            # 5日涨跌幅
            hist5 = ticker_obj.history(period="5d")
            price_5d_ago = float(hist5["Close"].iloc[0]) if len(hist5) >= 2 else None
            change_5d = (
                round((cur - price_5d_ago) / price_5d_ago * 100, 2)
                if price_5d_ago
                else None
            )

            result[t] = {
                "price": round(float(cur), 2),
                "change_5d_pct": change_5d,
                "52w_low": round(w52_low, 2),
                "52w_high": round(w52_high, 2),
                "pct_52w_percentile": pct_52w,
                "pe_ttm": info.get("trailingPE"),
                "pe_fwd": info.get("forwardPE"),
                "pb": info.get("priceToBook"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "target_mean": info.get("targetMeanPrice"),
                "target_upside_pct": (
                    round((info["targetMeanPrice"] / cur - 1) * 100, 1)
                    if info.get("targetMeanPrice") and cur
                    else None
                ),
                "currency": info.get("currency", "USD"),
                "sector": info.get("sector", "N/A"),
                "data_date": datetime.now().strftime("%Y-%m-%d"),
            }
        except Exception as e:
            result[t] = {"error": str(e), "data_date": datetime.now().strftime("%Y-%m-%d")}
    return result


def locate_latest_tracker_report() -> Path | None:
    """定位最新的 stock_tracker 原料文件（无时间戳后缀版）"""
    reports = sorted(
        REPORT_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-investment-idea-tracking-report.md")
    )
    return reports[-1] if reports else None


# ─── 报告生成 ─────────────────────────────────────────────────────────────────

def format_md_snapshot(snapshot: dict[str, dict], watchlist: dict) -> str:
    """将价格快照格式化为买方日报 Step 3 所需的 Markdown 表格"""
    idea_map = {i.get("ticker", ""): i for i in watchlist.get("ideas", [])}

    lines = [
        "## 持仓/观察池价格快照",
        f"> 数据拉取时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 数据源：yfinance",
        "",
        "| 标的 | 持仓级别 | 最新价 | 5日% | 52W位置 | PE(TTM) | PE(Fwd) | EV/EBITDA | 分析师PT | 隐含空间 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for ticker, d in snapshot.items():
        idea = idea_map.get(ticker, {})
        level = idea.get("position", "观察")
        if "error" in d:
            lines.append(f"| {ticker} | {level} | ❌{d['error']} | — | — | — | — | — | — | — |")
            continue

        def fmt(v, suffix="", na="N/A"):
            return f"{v}{suffix}" if v is not None else na

        lines.append(
            f"| **{ticker}** | {level} "
            f"| {fmt(d.get('price'), ' ' + d.get('currency',''))} "
            f"| {fmt(d.get('change_5d_pct'), '%')} "
            f"| {fmt(d.get('pct_52w_percentile'), '%ile')} "
            f"| {fmt(d.get('pe_ttm'))} "
            f"| {fmt(d.get('pe_fwd'))} "
            f"| {fmt(d.get('ev_ebitda'))} "
            f"| {fmt(d.get('target_mean'))} "
            f"| {fmt(d.get('target_upside_pct'), '%')} |"
        )

    return "\n".join(lines)


# ─── CLI 入口 ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="买方日报数据拉取工具")
    parser.add_argument("--output", choices=["json", "md", "both"], default="md",
                        help="输出格式（默认 md）")
    parser.add_argument("--tickers", nargs="*", help="手动指定 ticker 列表，不填则从 watchlist 读取")
    parser.add_argument("--save", action="store_true", help="保存输出到 daily_reports/ 目录")
    args = parser.parse_args()

    # 1. 读取 watchlist
    wl = load_watchlist()
    if args.tickers:
        tickers = args.tickers
    else:
        tickers = [
            idea["ticker"]
            for idea in wl.get("ideas", [])
            if idea.get("ticker") and idea.get("market") in ("US", "HK")
        ]

    if not tickers:
        print("⚠️  未找到任何有效 ticker，请检查 ideas_watchlist.json 或通过 --tickers 手动指定")
        sys.exit(0)

    print(f"📡 正在拉取 {len(tickers)} 个标的的数据：{tickers}")
    snapshot = get_price_snapshot(tickers)

    # 2. 输出
    today = datetime.now().strftime("%Y-%m-%d")

    if args.output in ("json", "both"):
        json_str = json.dumps(snapshot, ensure_ascii=False, indent=2)
        if args.save:
            out = OUTPUT_DIR / f"{today}-buyside-snapshot.json"
            out.write_text(json_str, encoding="utf-8")
            print(f"✅ JSON 已保存：{out}")
        else:
            print(json_str)

    if args.output in ("md", "both"):
        md_str = format_md_snapshot(snapshot, wl)

        # 附加最新原料文件信息
        latest_report = locate_latest_tracker_report()
        md_str += f"\n\n> 📰 最新新闻原料文件：`{latest_report.name if latest_report else '未找到'}`"

        if args.save:
            out = OUTPUT_DIR / f"{today}-buyside-snapshot.md"
            out.write_text(md_str, encoding="utf-8")
            print(f"✅ Markdown 已保存：{out}")
        else:
            print(md_str)


if __name__ == "__main__":
    main()
