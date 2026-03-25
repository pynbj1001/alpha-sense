#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
投资数据工具包 — AI Agent 通用数据获取层

数据瀑布策略：yfinance → akshare → tushare
所有输出标注来源与日期。
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 可选依赖容错导入
# ---------------------------------------------------------------------------
try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

try:
    import akshare as ak
    HAS_AK = True
except ImportError:
    HAS_AK = False

try:
    import tushare as ts
    HAS_TS = True
except ImportError:
    HAS_TS = False

try:
    import pandas as pd
    HAS_PD = True
except ImportError:
    HAS_PD = False


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return date.today().isoformat()


def _try_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.{digits}f}"


def _fmt_pct(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.{digits}f}%"


def _fmt_cap(value: float | None) -> str:
    """格式化市值为可读字符串（亿美元/亿人民币）"""
    if value is None:
        return "N/A"
    if value >= 1e12:
        return f"{value / 1e12:.2f}万亿"
    if value >= 1e8:
        return f"{value / 1e8:.2f}亿"
    return f"{value:,.0f}"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class StockSnapshot:
    """个股估值快照"""
    ticker: str
    name: str = ""
    as_of: str = ""
    sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # 价格
    price: float | None = None
    currency: str = "USD"

    # 估值指标
    pe_ttm: float | None = None
    pe_forward: float | None = None
    pb: float | None = None
    ps: float | None = None
    ev_ebitda: float | None = None
    market_cap: float | None = None

    # 盈利指标
    roe: float | None = None
    roa: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None

    # 成长指标
    revenue_growth: float | None = None
    earnings_growth: float | None = None

    # 财务健康
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    interest_coverage: float | None = None

    # 股东回报
    dividend_yield: float | None = None
    payout_ratio: float | None = None
    buyback_yield: float | None = None

    # 派生指标
    pr_ratio: float | None = None       # 市赚率 = PE / (ROE*100)
    g_star: float | None = None          # 盈亏平衡增长率 = 1/PE - dividend_yield
    peg: float | None = None             # PEG = PE / (earnings_growth*100)

    def compute_derived(self) -> None:
        """计算派生指标"""
        pe = self.pe_ttm
        roe = self.roe
        dy = self.dividend_yield or 0.0
        eg = self.earnings_growth

        if pe and pe > 0 and roe and roe > 0:
            self.pr_ratio = pe / (roe * 100)
        if pe and pe > 0:
            self.g_star = (1 / pe) - dy
        if pe and pe > 0 and eg and eg > 0:
            self.peg = pe / (eg * 100)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MacroSnapshot:
    """宏观指标快照"""
    as_of: str = ""
    sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # 美国
    us_10y: float | None = None
    us_2y: float | None = None
    us_spread_10y_2y: float | None = None
    fed_rate: float | None = None
    vix: float | None = None
    us_cpi_yoy: float | None = None
    us_pmi: float | None = None
    dxy: float | None = None              # 美元指数

    # 中国
    cn_10y: float | None = None
    cn_pmi: float | None = None
    cn_cpi_yoy: float | None = None
    usdcny: float | None = None

    # 大宗
    gold: float | None = None
    oil_wti: float | None = None
    copper: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# 数据获取：个股快照
# ---------------------------------------------------------------------------

def fetch_stock_snapshot(ticker: str) -> StockSnapshot:
    """
    拉取个股估值快照，按瀑布策略尝试数据源。

    参数:
        ticker: 股票代码（如 AAPL, 600519.SS）

    返回:
        StockSnapshot 数据对象
    """
    snap = StockSnapshot(ticker=ticker, as_of=_now())

    # ---- yfinance（优先）----
    if HAS_YF:
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            snap.name = info.get("shortName", info.get("longName", ""))
            snap.price = _try_float(info.get("currentPrice") or info.get("regularMarketPrice"))
            snap.currency = info.get("currency", "USD")
            snap.pe_ttm = _try_float(info.get("trailingPE"))
            snap.pe_forward = _try_float(info.get("forwardPE"))
            snap.pb = _try_float(info.get("priceToBook"))
            snap.ps = _try_float(info.get("priceToSalesTrailing12Months"))
            snap.ev_ebitda = _try_float(info.get("enterpriseToEbitda"))
            snap.market_cap = _try_float(info.get("marketCap"))

            roe = _try_float(info.get("returnOnEquity"))
            if roe is not None and abs(roe) > 1:
                roe = roe / 100.0
            snap.roe = roe

            snap.roa = _try_float(info.get("returnOnAssets"))
            snap.gross_margin = _try_float(info.get("grossMargins"))
            snap.operating_margin = _try_float(info.get("operatingMargins"))
            snap.net_margin = _try_float(info.get("profitMargins"))
            snap.revenue_growth = _try_float(info.get("revenueGrowth"))
            snap.earnings_growth = _try_float(info.get("earningsGrowth"))
            snap.debt_to_equity = _try_float(info.get("debtToEquity"))
            snap.current_ratio = _try_float(info.get("currentRatio"))

            dy = _try_float(info.get("dividendYield"))
            if dy is not None and abs(dy) > 1:
                dy = dy / 100.0
            snap.dividend_yield = dy
            snap.payout_ratio = _try_float(info.get("payoutRatio"))

            snap.sources.append("yfinance")
        except Exception as e:
            snap.warnings.append(f"yfinance 拉取失败: {e}")

    # ---- 补充缺失字段告警 ----
    if snap.pe_ttm is None:
        snap.warnings.append("PE(TTM) 缺失，估值判断不完整")
    if snap.roe is None:
        snap.warnings.append("ROE 缺失，质量评估不完整")

    snap.compute_derived()
    return snap


def fetch_price_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> dict:
    """
    获取历史价格数据。

    参数:
        ticker: 股票代码
        period: 时间范围（1mo/3mo/6mo/1y/2y/5y/10y/max）
        interval: 数据频率（1d/1wk/1mo）

    返回:
        dict 包含 dates, closes, highs, lows, volumes
    """
    result: dict[str, Any] = {
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "source": "N/A",
        "as_of": _now(),
        "dates": [],
        "closes": [],
        "highs": [],
        "lows": [],
        "volumes": [],
    }

    if HAS_YF:
        try:
            t = yf.Ticker(ticker)
            df = t.history(period=period, interval=interval)
            if not df.empty:
                result["dates"] = [d.strftime("%Y-%m-%d") for d in df.index]
                result["closes"] = [round(x, 2) for x in df["Close"].tolist()]
                result["highs"] = [round(x, 2) for x in df["High"].tolist()]
                result["lows"] = [round(x, 2) for x in df["Low"].tolist()]
                result["volumes"] = df["Volume"].tolist()
                result["source"] = "yfinance"
        except Exception:
            pass

    return result


def fetch_financial_statements(ticker: str, period: str = "annual") -> dict:
    """
    获取三大财务报表摘要。

    参数:
        ticker: 股票代码
        period: annual 或 quarterly

    返回:
        dict 包含 income_statement, balance_sheet, cash_flow 的关键指标
    """
    result: dict[str, Any] = {
        "ticker": ticker,
        "period": period,
        "source": "N/A",
        "as_of": _now(),
        "income_statement": {},
        "balance_sheet": {},
        "cash_flow": {},
    }

    if HAS_YF:
        try:
            t = yf.Ticker(ticker)
            # 利润表
            inc = t.income_stmt if period == "annual" else t.quarterly_income_stmt
            if inc is not None and not inc.empty:
                latest = inc.iloc[:, 0]
                result["income_statement"] = {
                    "total_revenue": _try_float(latest.get("Total Revenue")),
                    "gross_profit": _try_float(latest.get("Gross Profit")),
                    "operating_income": _try_float(latest.get("Operating Income")),
                    "net_income": _try_float(latest.get("Net Income")),
                    "ebitda": _try_float(latest.get("EBITDA")),
                    "period_end": str(inc.columns[0].date()) if hasattr(inc.columns[0], "date") else str(inc.columns[0]),
                }
            # 资产负债表
            bs = t.balance_sheet if period == "annual" else t.quarterly_balance_sheet
            if bs is not None and not bs.empty:
                latest = bs.iloc[:, 0]
                result["balance_sheet"] = {
                    "total_assets": _try_float(latest.get("Total Assets")),
                    "total_liabilities": _try_float(latest.get("Total Liabilities Net Minority Interest")),
                    "total_equity": _try_float(latest.get("Stockholders Equity")),
                    "cash": _try_float(latest.get("Cash And Cash Equivalents")),
                    "total_debt": _try_float(latest.get("Total Debt")),
                }
            # 现金流量表
            cf = t.cashflow if period == "annual" else t.quarterly_cashflow
            if cf is not None and not cf.empty:
                latest = cf.iloc[:, 0]
                result["cash_flow"] = {
                    "operating_cf": _try_float(latest.get("Operating Cash Flow")),
                    "capex": _try_float(latest.get("Capital Expenditure")),
                    "free_cash_flow": _try_float(latest.get("Free Cash Flow")),
                }
            result["source"] = "yfinance"
        except Exception:
            pass

    return result


# ---------------------------------------------------------------------------
# 数据获取：宏观快照
# ---------------------------------------------------------------------------

def fetch_macro_snapshot() -> MacroSnapshot:
    """
    拉取宏观指标快照。

    返回:
        MacroSnapshot 数据对象
    """
    macro = MacroSnapshot(as_of=_now())

    if HAS_YF:
        try:
            tickers_map = {
                "^TNX": "us_10y",       # US 10Y
                "^IRX": "us_2y_proxy",  # US 3M (proxy)
                "^VIX": "vix",          # VIX
                "GC=F": "gold",         # Gold
                "CL=F": "oil_wti",      # WTI Oil
                "HG=F": "copper",       # Copper
                "DX-Y.NYB": "dxy",      # US Dollar Index
                "CNY=X": "usdcny",      # USD/CNY
            }
            for yf_ticker, attr_name in tickers_map.items():
                try:
                    t = yf.Ticker(yf_ticker)
                    info = t.info or {}
                    price = _try_float(
                        info.get("regularMarketPrice")
                        or info.get("previousClose")
                    )
                    if price is not None and attr_name == "us_10y":
                        macro.us_10y = price / 100 if price > 1 else price
                    elif price is not None and attr_name == "vix":
                        macro.vix = price
                    elif price is not None and attr_name == "gold":
                        macro.gold = price
                    elif price is not None and attr_name == "oil_wti":
                        macro.oil_wti = price
                    elif price is not None and attr_name == "copper":
                        macro.copper = price
                    elif price is not None and attr_name == "dxy":
                        macro.dxy = price
                    elif price is not None and attr_name == "usdcny":
                        macro.usdcny = price
                except Exception:
                    pass
            macro.sources.append("yfinance")
        except Exception as e:
            macro.warnings.append(f"yfinance 宏观数据拉取失败: {e}")

    if macro.us_10y is not None and macro.us_2y is not None:
        macro.us_spread_10y_2y = macro.us_10y - macro.us_2y

    return macro


# ---------------------------------------------------------------------------
# 数据获取：同行业对比
# ---------------------------------------------------------------------------

def fetch_industry_comparison(ticker: str, peers: list[str] | None = None) -> list[dict]:
    """
    拉取同行业对比数据。

    参数:
        ticker: 主标的代码
        peers: 对比标的列表（若为空则尝试自动发现）

    返回:
        list[dict] 每个标的的关键指标
    """
    if peers is None:
        peers = []

    all_tickers = [ticker] + peers
    results = []
    for t in all_tickers:
        snap = fetch_stock_snapshot(t)
        results.append({
            "ticker": snap.ticker,
            "name": snap.name,
            "price": snap.price,
            "market_cap": snap.market_cap,
            "pe": snap.pe_ttm,
            "pb": snap.pb,
            "roe": snap.roe,
            "gross_margin": snap.gross_margin,
            "revenue_growth": snap.revenue_growth,
            "dividend_yield": snap.dividend_yield,
            "debt_to_equity": snap.debt_to_equity,
        })

    return results


# ---------------------------------------------------------------------------
# 格式化输出
# ---------------------------------------------------------------------------

def snapshot_to_markdown(snap: StockSnapshot) -> str:
    """将 StockSnapshot 格式化为机构级 Markdown 表格"""
    lines = [
        "## 📊 数据快照",
        "",
        f"| 项目 | 信息 |",
        f"|:-----|:-----|",
        f"| 标的 | **{snap.ticker}** {snap.name} |",
        f"| 时间 | {snap.as_of} |",
        f"| 数据源 | {', '.join(snap.sources) or 'N/A'} |",
        f"| 货币 | {snap.currency} |",
        "",
        "### 估值指标",
        "",
        "| 指标 | 数值 | 说明 |",
        "|:-----|-----:|:-----|",
        f"| 现价 | {_fmt_num(snap.price)} | |",
        f"| 市值 | {_fmt_cap(snap.market_cap)} | |",
        f"| PE (TTM) | {_fmt_num(snap.pe_ttm)} | 静态市盈率 |",
        f"| PE (Forward) | {_fmt_num(snap.pe_forward)} | 预期市盈率 |",
        f"| PB | {_fmt_num(snap.pb)} | 市净率 |",
        f"| PS | {_fmt_num(snap.ps)} | 市销率 |",
        f"| EV/EBITDA | {_fmt_num(snap.ev_ebitda)} | 企业价值倍数 |",
        f"| 市赚率 (PR) | {_fmt_num(snap.pr_ratio, 3)} | PE/(ROE×100) |",
        f"| PEG | {_fmt_num(snap.peg, 2)} | PE/盈利增速 |",
        f"| g* | {_fmt_pct(snap.g_star)} | 盈亏平衡增长率 |",
        "",
        "### 盈利质量",
        "",
        "| 指标 | 数值 |",
        "|:-----|-----:|",
        f"| ROE | {_fmt_pct(snap.roe)} |",
        f"| ROA | {_fmt_pct(snap.roa)} |",
        f"| 毛利率 | {_fmt_pct(snap.gross_margin)} |",
        f"| 营业利润率 | {_fmt_pct(snap.operating_margin)} |",
        f"| 净利率 | {_fmt_pct(snap.net_margin)} |",
        "",
        "### 成长与回报",
        "",
        "| 指标 | 数值 |",
        "|:-----|-----:|",
        f"| 营收增速 | {_fmt_pct(snap.revenue_growth)} |",
        f"| 盈利增速 | {_fmt_pct(snap.earnings_growth)} |",
        f"| 股息率 | {_fmt_pct(snap.dividend_yield)} |",
        f"| 派息率 | {_fmt_pct(snap.payout_ratio)} |",
        "",
        "### 财务健康",
        "",
        "| 指标 | 数值 |",
        "|:-----|-----:|",
        f"| 资产负债率 (D/E) | {_fmt_num(snap.debt_to_equity)} |",
        f"| 流动比率 | {_fmt_num(snap.current_ratio)} |",
        "",
    ]

    if snap.warnings:
        lines.append("### ⚠️ 数据告警")
        lines.append("")
        for w in snap.warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def macro_to_markdown(macro: MacroSnapshot) -> str:
    """将 MacroSnapshot 格式化为 Markdown"""
    lines = [
        "## 🌐 宏观指标快照",
        "",
        f"- 时间：{macro.as_of}",
        f"- 数据源：{', '.join(macro.sources) or 'N/A'}",
        "",
        "### 利率与汇率",
        "",
        "| 指标 | 数值 |",
        "|:-----|-----:|",
        f"| 美国10年期国债 | {_fmt_pct(macro.us_10y)} |",
        f"| 美联储基准利率 | {_fmt_pct(macro.fed_rate)} |",
        f"| 10Y-2Y利差 | {_fmt_pct(macro.us_spread_10y_2y)} |",
        f"| 美元指数 (DXY) | {_fmt_num(macro.dxy)} |",
        f"| USD/CNY | {_fmt_num(macro.usdcny, 4)} |",
        "",
        "### 风险与情绪",
        "",
        "| 指标 | 数值 |",
        "|:-----|-----:|",
        f"| VIX恐慌指数 | {_fmt_num(macro.vix)} |",
        "",
        "### 大宗商品",
        "",
        "| 指标 | 数值 |",
        "|:-----|-----:|",
        f"| 黄金 (USD/oz) | {_fmt_num(macro.gold)} |",
        f"| WTI原油 (USD/bbl) | {_fmt_num(macro.oil_wti)} |",
        f"| 铜 (USD/lb) | {_fmt_num(macro.copper)} |",
        "",
    ]

    if macro.warnings:
        lines.append("### ⚠️ 告警")
        for w in macro.warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def comparison_to_markdown(data: list[dict]) -> str:
    """将同行业对比数据格式化为 Markdown 表格"""
    lines = [
        "## 📋 同行业对比",
        "",
        "| 标的 | 名称 | 现价 | 市值 | PE | PB | ROE | 毛利率 | 营收增速 | 股息率 | D/E |",
        "|:-----|:-----|-----:|-----:|---:|---:|----:|------:|-------:|------:|----:|",
    ]
    for d in data:
        lines.append(
            f"| {d['ticker']} "
            f"| {d.get('name', '')} "
            f"| {_fmt_num(d.get('price'))} "
            f"| {_fmt_cap(d.get('market_cap'))} "
            f"| {_fmt_num(d.get('pe'))} "
            f"| {_fmt_num(d.get('pb'))} "
            f"| {_fmt_pct(d.get('roe'))} "
            f"| {_fmt_pct(d.get('gross_margin'))} "
            f"| {_fmt_pct(d.get('revenue_growth'))} "
            f"| {_fmt_pct(d.get('dividend_yield'))} "
            f"| {_fmt_num(d.get('debt_to_equity'))} |"
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行测试入口"""
    import argparse

    parser = argparse.ArgumentParser(description="投资数据工具包")
    sub = parser.add_subparsers(dest="command")

    # 个股快照
    p_stock = sub.add_parser("stock", help="个股快照")
    p_stock.add_argument("ticker", help="股票代码")

    # 宏观快照
    sub.add_parser("macro", help="宏观指标快照")

    # 对比
    p_comp = sub.add_parser("compare", help="同行业对比")
    p_comp.add_argument("tickers", nargs="+", help="股票代码列表")

    # 财务报表
    p_fin = sub.add_parser("financials", help="三大财务报表")
    p_fin.add_argument("ticker", help="股票代码")

    args = parser.parse_args()

    if args.command == "stock":
        snap = fetch_stock_snapshot(args.ticker)
        print(snapshot_to_markdown(snap))
    elif args.command == "macro":
        macro = fetch_macro_snapshot()
        print(macro_to_markdown(macro))
    elif args.command == "compare":
        data = fetch_industry_comparison(args.tickers[0], args.tickers[1:])
        print(comparison_to_markdown(data))
    elif args.command == "financials":
        data = fetch_financial_statements(args.ticker)
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
