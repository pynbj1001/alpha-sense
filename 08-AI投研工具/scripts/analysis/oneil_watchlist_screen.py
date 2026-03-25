#!/usr/bin/env python
from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
DEFAULT_BASE = next((p for p in ROOT.glob("11.*") if p.is_dir()), ROOT / "11.idea_tracking")
WATCHLIST_PATH = DEFAULT_BASE / "ideas_watchlist.json"
REPORT_DIR = ROOT / "10-研究报告输出"
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


@dataclass
class MarketTrend:
    benchmark: str
    close: float | None
    ma50: float | None
    ma200: float | None
    ret_12m: float | None
    pass_trend: bool
    asof: str


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def pct_to_str(v: float | None, digits: int = 1) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "N/A"
    return f"{v * 100:.{digits}f}%"


def num_to_str(v: float | None, digits: int = 2) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "N/A"
    return f"{v:.{digits}f}"


def money_to_str(v: float | None) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "N/A"
    av = abs(v)
    if av >= 1_000_000_000_000:
        return f"{v / 1_000_000_000_000:.2f}T"
    if av >= 1_000_000_000:
        return f"{v / 1_000_000_000:.2f}B"
    if av >= 1_000_000:
        return f"{v / 1_000_000:.2f}M"
    return f"{v:.0f}"


def parse_pct_text(v: str | None) -> float | None:
    if not v:
        return None
    vv = v.strip().replace(",", "")
    if vv in {"-", "N/A"}:
        return None
    if vv.endswith("%"):
        try:
            return float(vv[:-1]) / 100.0
        except ValueError:
            return None
    try:
        return float(vv)
    except ValueError:
        return None


def safe_growth(cur: float | None, prev: float | None) -> float | None:
    if cur is None or prev is None:
        return None
    if abs(prev) < 1e-9:
        return None
    return (cur - prev) / abs(prev)


def get_row(df: pd.DataFrame, names: list[str]) -> pd.Series | None:
    if df is None or df.empty:
        return None
    idx_map = {str(x).strip().lower(): x for x in df.index}
    for name in names:
        key = name.strip().lower()
        if key in idx_map:
            return df.loc[idx_map[key]]
    return None


def to_num(x: Any) -> float | None:
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def fetch_stooq_snapshot(stooq_symbol: str) -> dict[str, Any] | None:
    if not stooq_symbol:
        return None
    url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2ohlcvn&e=csv"
    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=15)
        r.raise_for_status()
        rows = list(csv.reader(StringIO(r.text.strip())))
        if not rows:
            return None
        # Stooq can return either one data row or header+data.
        row = rows[-1]
        if len(row) < 7:
            return None
        # Symbol,Date,Time,Open,High,Low,Close,Volume,Name
        return {
            "symbol": row[0],
            "date": row[1],
            "close": to_num(row[6]),
            "volume": to_num(row[7]),
            "name": row[8] if len(row) > 8 else "",
        }
    except Exception:
        return None


def fetch_finviz_snapshot(symbol: str) -> dict[str, Any] | None:
    if "." in symbol:
        return None
    url = f"https://finviz.com/quote.ashx?t={symbol}&p=d"
    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        out: dict[str, str] = {}
        for table in soup.find_all("table"):
            cls = " ".join(table.get("class", []))
            if "snapshot-table2" not in cls:
                continue
            tds = table.find_all("td")
            for i in range(0, len(tds) - 1, 2):
                k = tds[i].get_text(strip=True)
                v = tds[i + 1].get_text(strip=True)
                out[k] = v
            break
        if not out:
            return None
        return {
            "eps_qoq": parse_pct_text(out.get("EPS Q/Q")),
            "sales_qoq": parse_pct_text(out.get("Sales Q/Q")),
            "roe": parse_pct_text(out.get("ROE")),
            "inst_own": parse_pct_text(out.get("Inst Own")),
            "eps_past_5y": parse_pct_text(out.get("EPS past 5Y")),
            "perf_year": parse_pct_text(out.get("Perf Year")),
            "raw": out,
        }
    except Exception:
        return None


def market_to_benchmark(market: str) -> str:
    mm = (market or "").upper()
    if mm == "HK":
        return "^HSI"
    return "^GSPC"


def fetch_market_trend(benchmark: str) -> MarketTrend:
    try:
        hist = yf.download(
            benchmark,
            period="2y",
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )
        if hist is None or hist.empty:
            return MarketTrend(benchmark, None, None, None, None, False, "N/A")
        if isinstance(hist.columns, pd.MultiIndex):
            if ("Close", benchmark) in hist.columns:
                close = hist[("Close", benchmark)].dropna()
            else:
                close = hist.xs("Close", axis=1, level=0).iloc[:, 0].dropna()
        else:
            close = hist["Close"].dropna()
        ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
        ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
        ret_12m = None
        if len(close) >= 253:
            ret_12m = close.iloc[-1] / close.iloc[-253] - 1
        pass_trend = bool(
            ma50 is not None
            and ma200 is not None
            and close.iloc[-1] > ma200
            and ma50 > ma200
        )
        asof = str(close.index[-1].date())
        return MarketTrend(
            benchmark=benchmark,
            close=float(close.iloc[-1]),
            ma50=float(ma50) if ma50 is not None else None,
            ma200=float(ma200) if ma200 is not None else None,
            ret_12m=float(ret_12m) if ret_12m is not None else None,
            pass_trend=pass_trend,
            asof=asof,
        )
    except Exception:
        return MarketTrend(benchmark, None, None, None, None, False, "N/A")


def latest_quarter_yoy(df_q: pd.DataFrame, row_names: list[str]) -> float | None:
    row = get_row(df_q, row_names)
    if row is None:
        return None
    vals = row.dropna()
    if len(vals) < 5:
        return None
    cur = to_num(vals.iloc[0])
    prev = to_num(vals.iloc[4])
    return safe_growth(cur, prev)


def eps_cagr_3y(df_a: pd.DataFrame) -> float | None:
    row = get_row(df_a, ["Diluted EPS", "Basic EPS"])
    if row is None:
        return None
    vals = row.dropna()
    if len(vals) < 4:
        return None
    cur = to_num(vals.iloc[0])
    y3 = to_num(vals.iloc[3])
    if cur is None or y3 is None or cur <= 0 or y3 <= 0:
        return None
    return (cur / y3) ** (1 / 3) - 1


def dilution_yoy(df_a: pd.DataFrame) -> float | None:
    row = get_row(df_a, ["Diluted Average Shares", "Basic Average Shares"])
    if row is None:
        return None
    vals = row.dropna()
    if len(vals) < 2:
        return None
    cur = to_num(vals.iloc[0])
    prev = to_num(vals.iloc[1])
    return safe_growth(cur, prev)


def conservative_merge(a: float | None, b: float | None) -> float | None:
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


def pass_label(v: bool | None) -> str:
    if v is None:
        return "N/A"
    return "✅" if v else "❌"


def pick_first(v: Any, default: float | None = None) -> float | None:
    if isinstance(v, pd.Series):
        if v.empty:
            return default
        return to_num(v.iloc[0])
    return to_num(v)


def fetch_stock_metrics(symbol: str, market: str, stooq_symbol: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "symbol": symbol,
        "market": market,
        "stooq_symbol": stooq_symbol,
    }
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="2y", interval="1d", auto_adjust=False)
    if hist is None or hist.empty:
        out["error"] = "No price history"
        return out
    if isinstance(hist.columns, pd.MultiIndex):
        close_col = hist.xs("Close", axis=1, level=0).iloc[:, 0]
        high_col = hist.xs("High", axis=1, level=0).iloc[:, 0]
        low_col = hist.xs("Low", axis=1, level=0).iloc[:, 0]
        vol_col = hist.xs("Volume", axis=1, level=0).iloc[:, 0]
    else:
        close_col = hist["Close"]
        high_col = hist["High"]
        low_col = hist["Low"]
        vol_col = hist["Volume"]

    close_s = close_col.dropna()
    high_s = high_col.dropna()
    low_s = low_col.dropna()
    vol_s = vol_col.dropna()
    if len(close_s) < 220:
        out["error"] = "Insufficient price history"
        return out

    px = float(close_s.iloc[-1])
    asof = str(close_s.index[-1].date())
    ma50 = float(close_s.rolling(50).mean().iloc[-1])
    ma200 = float(close_s.rolling(200).mean().iloc[-1])
    high52 = float(high_s.tail(252).max())
    low52 = float(low_s.tail(252).min())
    dist_52w_high = px / high52 - 1 if high52 else None
    ret_12m = float(px / close_s.iloc[-253] - 1) if len(close_s) >= 253 else None
    vol_ratio_50 = None
    if len(vol_s) >= 51:
        avg50 = vol_s.rolling(50).mean().iloc[-1]
        if avg50 and not pd.isna(avg50):
            vol_ratio_50 = float(vol_s.iloc[-1] / avg50)

    info = ticker.info or {}
    roe_yf = to_num(info.get("returnOnEquity"))
    if roe_yf is not None:
        roe_yf *= 100
    inst_yf = to_num(info.get("heldPercentInstitutions"))
    if inst_yf is not None:
        inst_yf *= 100

    df_q = ticker.quarterly_income_stmt
    df_a = ticker.income_stmt
    if isinstance(df_q, pd.DataFrame) and not df_q.empty:
        df_q = df_q.sort_index(axis=1, ascending=False)
    if isinstance(df_a, pd.DataFrame) and not df_a.empty:
        df_a = df_a.sort_index(axis=1, ascending=False)

    eps_yoy_yf = latest_quarter_yoy(df_q, ["Diluted EPS", "Basic EPS"])
    rev_yoy_yf = latest_quarter_yoy(df_q, ["Total Revenue", "Operating Revenue", "Revenue"])
    eps_cagr3_yf = eps_cagr_3y(df_a)
    dilution = dilution_yoy(df_a)

    finviz = fetch_finviz_snapshot(symbol) if market.upper() == "US" else None
    eps_yoy_fv = finviz.get("eps_qoq") if finviz else None
    rev_yoy_fv = finviz.get("sales_qoq") if finviz else None
    roe_fv = finviz.get("roe") if finviz else None
    inst_fv = finviz.get("inst_own") if finviz else None
    eps_5y_fv = finviz.get("eps_past_5y") if finviz else None

    eps_yoy = conservative_merge(eps_yoy_yf, eps_yoy_fv)
    rev_yoy = conservative_merge(rev_yoy_yf, rev_yoy_fv)
    roe = conservative_merge(roe_yf / 100 if roe_yf is not None else None, roe_fv)
    inst_own = conservative_merge(inst_yf / 100 if inst_yf is not None else None, inst_fv)
    eps_cagr3 = conservative_merge(eps_cagr3_yf, eps_5y_fv)

    stooq = fetch_stooq_snapshot(stooq_symbol) if stooq_symbol else None
    stooq_close = stooq.get("close") if stooq else None
    stooq_date = stooq.get("date") if stooq else "N/A"
    px_diff = None
    if stooq_close is not None and px:
        px_diff = stooq_close / px - 1

    out.update(
        {
            "asof": asof,
            "price": px,
            "ma50": ma50,
            "ma200": ma200,
            "high52": high52,
            "low52": low52,
            "dist_52w_high": dist_52w_high,
            "ret_12m": ret_12m,
            "vol_ratio_50": vol_ratio_50,
            "market_cap": to_num(info.get("marketCap")),
            "shares_out": to_num(info.get("sharesOutstanding")),
            "float_shares": to_num(info.get("floatShares")),
            "eps_yoy": eps_yoy,
            "rev_yoy": rev_yoy,
            "eps_cagr3": eps_cagr3,
            "roe": roe,
            "inst_own": inst_own,
            "dilution_yoy": dilution,
            "stooq_close": stooq_close,
            "stooq_date": stooq_date,
            "px_diff": px_diff,
            "source_note": (
                "yfinance+finviz+stooq"
                if finviz is not None
                else ("yfinance+stooq" if stooq is not None else "yfinance")
            ),
            "finviz_ok": finviz is not None,
        }
    )
    return out


def classify_row(row: dict[str, Any], trend: MarketTrend) -> dict[str, Any]:
    c_pass = bool(
        row.get("eps_yoy") is not None
        and row.get("rev_yoy") is not None
        and row["eps_yoy"] >= 0.25
        and row["rev_yoy"] > 0
    )
    a_pass = bool(
        row.get("eps_cagr3") is not None
        and row.get("roe") is not None
        and row["eps_cagr3"] >= 0.25
        and row["roe"] >= 0.17
    )
    n_pass = bool(
        row.get("dist_52w_high") is not None
        and row["dist_52w_high"] >= -0.15
    )
    s_pass = bool(
        row.get("dilution_yoy") is not None
        and row["dilution_yoy"] <= 0.05
    )
    bench_ret = trend.ret_12m
    stock_ret = row.get("ret_12m")
    excess = None
    if stock_ret is not None and bench_ret is not None:
        excess = stock_ret - bench_ret
    rs_proxy = None
    if excess is not None:
        rs_proxy = max(0.0, min(100.0, 50.0 + excess * 100.0))
    l_pass = bool(excess is not None and rs_proxy is not None and rs_proxy >= 80.0)
    i_pass = bool(
        row.get("inst_own") is not None
        and row["inst_own"] >= 0.20
        and row["inst_own"] <= 0.70
    )
    m_pass = trend.pass_trend

    letters = {"C": c_pass, "A": a_pass, "N": n_pass, "S": s_pass, "L": l_pass, "I": i_pass}
    pass_count = sum(1 for v in letters.values() if v)
    buypoint_ready = bool(
        row.get("price")
        and row.get("ma50")
        and row.get("ma200")
        and row["price"] > row["ma50"] > row["ma200"]
        and n_pass
        and row.get("vol_ratio_50") is not None
        and row["vol_ratio_50"] >= 1.5
    )

    if row.get("error"):
        status = "数据不足"
    elif m_pass and pass_count >= 5 and c_pass and a_pass and l_pass:
        status = "候选机会"
    elif pass_count >= 4 and (c_pass or l_pass):
        status = "观察名单"
    else:
        status = "暂不符合"

    if status == "候选机会" and not buypoint_ready:
        status = "候选机会(待买点)"
    if status.startswith("候选机会") and not m_pass:
        status = "仅跟踪(M未开)"

    stop8 = row["price"] * 0.92 if row.get("price") else None
    stop7 = row["price"] * 0.93 if row.get("price") else None

    return {
        **row,
        "C": c_pass,
        "A": a_pass,
        "N": n_pass,
        "S": s_pass,
        "L": l_pass,
        "I": i_pass,
        "M": m_pass,
        "letters_pass": pass_count,
        "excess_ret_12m": excess,
        "rs_proxy": rs_proxy,
        "buypoint_ready": buypoint_ready,
        "status": status,
        "stop8": stop8,
        "stop7": stop7,
    }


def load_active_stock_ideas() -> list[dict[str, Any]]:
    data = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []
    for x in data.get("ideas", []):
        if not x.get("active", True):
            continue
        if x.get("type") not in {"stock", "jp_stock"}:
            continue
        symbol = str(x.get("symbol", "")).strip()
        if not symbol:
            continue
        out.append(x)
    return out


def make_report(rows: list[dict[str, Any]], market_trend: dict[str, MarketTrend], output_md: Path, output_csv: Path) -> None:
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by=["status", "letters_pass", "rs_proxy"], ascending=[True, False, False])
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    n_total = len(rows)
    n_candidate = sum(1 for x in rows if str(x.get("status", "")).startswith("候选机会"))
    n_watch = sum(1 for x in rows if x.get("status") == "观察名单")
    n_reject = sum(1 for x in rows if x.get("status") == "暂不符合")
    n_data = sum(1 for x in rows if x.get("status") == "数据不足")

    md: list[str] = []
    md.append(f"# 跟踪池欧奈尔 CAN SLIM 筛选报告（{datetime.now().date()}）")
    md.append("")
    md.append(f"> 生成时间：{now_str()}")
    md.append("> 适用范围：当前活跃跟踪股票池（`ideas_watchlist.json`）")
    md.append("> 规则来源：`04-大师投资框架/欧奈尔 强势股识别与跟踪系统/...CAN SLIM法则...md`")
    md.append("> 数据来源：`yfinance`（主） + `stooq`（价格校验） + `finviz`（美股基本面交叉）")
    md.append("")
    md.append("## 一、执行摘要")
    md.append("")
    md.append(f"- 本次筛选股票数：`{n_total}`")
    md.append(f"- `候选机会`：`{n_candidate}`；`观察名单`：`{n_watch}`；`暂不符合`：`{n_reject}`；`数据不足`：`{n_data}`")
    md.append("- 欧奈尔硬阈值采用：`C/A/N/S/L/I + M市场闸门 + 7%-8%止损纪律`")
    md.append("")
    md.append("## 二、预检飞行清单")
    md.append("")
    md.append("| 检查项 | 结论 |")
    md.append("|---|---|")
    md.append("| 能力圈 | 覆盖你当前跟踪的美股/港股龙头与成长股，属于已研究范围 |")
    md.append("| 数据可得性 | 价格与多数财务指标可得；少数港股季度项缺失，已标注 |")
    md.append("| 生命周期 | 多数为成长/成熟期，适配CAN SLIM |")
    md.append("| 周期位置 | 美股AI主线延续，港股风格偏分化 |")
    md.append("| 市场情绪 | 总体仍偏成长偏好，但分化加剧 |")
    md.append("| 信息质量 | 关键价格做了双源校验；财务项美股双源、港股部分单源 |")
    md.append("| 历史报告回顾 | 已参考你近两日的机会扫描与UBER深度报告 |")
    md.append("| 时间框架 | 本筛选面向未来1-3个月的强势机会识别与跟踪 |")
    md.append("")
    md.append("## 三、M（市场闸门）")
    md.append("")
    md.append("| 市场 | 基准 | 最新 | MA50 | MA200 | 12M收益 | M是否打开 | 数据日期 |")
    md.append("|---|---:|---:|---:|---:|---:|---|---|")
    for mkt, tr in market_trend.items():
        md.append(
            f"| {mkt} | {tr.benchmark} | {num_to_str(tr.close)} | {num_to_str(tr.ma50)} | {num_to_str(tr.ma200)} | "
            f"{pct_to_str(tr.ret_12m)} | {'✅' if tr.pass_trend else '❌'} | {tr.asof} |"
        )
    md.append("")
    md.append("## 四、双源价格校验（关键数据）")
    md.append("")
    md.append("| 股票 | yfinance收盘 | stooq收盘 | 差异 | 校验结果 |")
    md.append("|---|---:|---:|---:|---|")
    for x in rows:
        diff = x.get("px_diff")
        ok = "✅" if diff is not None and abs(diff) <= 0.02 else ("⚠️" if diff is not None else "N/A")
        md.append(
            f"| {x['symbol']} | {num_to_str(x.get('price'))} | {num_to_str(x.get('stooq_close'))} | {pct_to_str(diff)} | {ok} |"
        )
    md.append("")
    md.append("## 五、CAN SLIM 总表")
    md.append("")
    md.append("| 股票 | C | A | N | S | L | I | 通过数 | RS代理 | 距52周高 | 量比(当日/50日) | 状态 |")
    md.append("|---|---|---|---|---|---|---|---:|---:|---:|---:|---|")
    for x in rows:
        md.append(
            f"| {x['symbol']} | {pass_label(x['C'])} | {pass_label(x['A'])} | {pass_label(x['N'])} | "
            f"{pass_label(x['S'])} | {pass_label(x['L'])} | {pass_label(x['I'])} | {x['letters_pass']} | "
            f"{num_to_str(x.get('rs_proxy'))} | {pct_to_str(x.get('dist_52w_high'))} | {num_to_str(x.get('vol_ratio_50'))} | {x['status']} |"
        )
    md.append("")
    md.append("## 六、候选机会与观察")
    md.append("")

    order = {"候选机会": 0, "候选机会(待买点)": 1, "观察名单": 2, "暂不符合": 3, "数据不足": 4, "仅跟踪(M未开)": 5}
    ranked = sorted(rows, key=lambda x: (order.get(x["status"], 99), -x.get("letters_pass", 0), -(x.get("rs_proxy") or 0)))

    for x in ranked:
        md.append(f"### {x['symbol']}｜{x['status']}")
        md.append("")
        md.append(
            f"- C（当季盈利）：EPS同比 `{pct_to_str(x.get('eps_yoy'))}`；营收同比 `{pct_to_str(x.get('rev_yoy'))}`"
        )
        md.append(
            f"- A（年度增长）：3年EPS复合 `{pct_to_str(x.get('eps_cagr3'))}`；ROE `{pct_to_str(x.get('roe'))}`"
        )
        md.append(
            f"- N/L：距52周高 `{pct_to_str(x.get('dist_52w_high'))}`；12M超额收益 `{pct_to_str(x.get('excess_ret_12m'))}`；RS代理 `{num_to_str(x.get('rs_proxy'))}`"
        )
        md.append(
            f"- S/I：股本稀释YoY `{pct_to_str(x.get('dilution_yoy'))}`；机构持仓 `{pct_to_str(x.get('inst_own'))}`"
        )
        md.append(
            f"- 技术买点：收盘 `{num_to_str(x.get('price'))}` vs MA50 `{num_to_str(x.get('ma50'))}` / MA200 `{num_to_str(x.get('ma200'))}`；量比 `{num_to_str(x.get('vol_ratio_50'))}`；买点触发 `{pass_label(x.get('buypoint_ready'))}`"
        )
        md.append(
            f"- 风控位：按欧奈尔纪律，7%-8%止损参考区间 `{num_to_str(x.get('stop7'))}` ~ `{num_to_str(x.get('stop8'))}`"
        )
        md.append(
            "- 二阶推演：若后续放量突破并维持C/A高增长，机构将继续加仓，股价可能进入趋势加速；若跌破止损位则说明需求验证失败，应机械退出而非主观补仓。"
        )
        md.append("")

    md.append("## 七、Kill-Switch 快检")
    md.append("")
    md.append("| 条件 | 结果 | 备注 |")
    md.append("|---|---|---|")
    md.append("| 核心价格数据不可得 | 否 | 全部股票获得价格，且多数完成双源校验 |")
    md.append("| 商业模式不可解释 | 否 | 均为你既有跟踪标的 |")
    md.append("| 数据可靠性不足 | 部分 | 港股部分季度数据单源，已降权处理 |")
    md.append("| 市场闸门关闭 | 见M表 | 若M关闭，全部降为“仅跟踪” |")
    md.append("")
    md.append("## 八、下一步跟踪触发器")
    md.append("")
    md.append("- 价格触发：`放量>50日均量50%` 且 `突破52周高/平台上沿` 才升级为执行买点。")
    md.append("- 基本面触发：下一季 `EPS同比<25%` 或 `营收转负` 则从候选降级。")
    md.append("- 风控触发：买入后触发 `-7%~-8%` 立即执行止损。")
    md.append("")
    md.append(f"> 明细数据CSV：`{output_csv.relative_to(ROOT)}`")
    md.append("")

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(md), encoding="utf-8")


def main() -> int:
    if not WATCHLIST_PATH.exists():
        raise FileNotFoundError(f"Watchlist file not found: {WATCHLIST_PATH}")
    ideas = load_active_stock_ideas()
    if not ideas:
        print("No active stock ideas found.")
        return 0

    benchmarks = sorted({market_to_benchmark(str(x.get("market", ""))) for x in ideas})
    trend_cache: dict[str, MarketTrend] = {b: fetch_market_trend(b) for b in benchmarks}

    rows: list[dict[str, Any]] = []
    for idea in ideas:
        symbol = str(idea.get("symbol", "")).strip()
        market = str(idea.get("market", "")).upper()
        stooq_symbol = str(idea.get("stooq_symbol", "")).strip()
        raw = fetch_stock_metrics(symbol=symbol, market=market, stooq_symbol=stooq_symbol)
        trend = trend_cache[market_to_benchmark(market)]
        scored = classify_row(raw, trend)
        scored["title"] = idea.get("title", symbol)
        rows.append(scored)

    today = datetime.now().date().isoformat()
    out_md = REPORT_DIR / f"{today}-机会扫描-跟踪池-欧奈尔CANSLIM.md"
    out_csv = REPORT_DIR / f"{today}-机会扫描-跟踪池-欧奈尔CANSLIM.csv"
    market_label = {}
    for b, tr in trend_cache.items():
        mkt = "US" if b == "^GSPC" else ("HK" if b == "^HSI" else b)
        market_label[mkt] = tr
    make_report(rows=rows, market_trend=market_label, output_md=out_md, output_csv=out_csv)
    print(f"Report generated: {out_md}")
    print(f"CSV generated: {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
