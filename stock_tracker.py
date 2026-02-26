#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import html
import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from io import StringIO
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import pandas as pd
import requests
try:
    import markdown
except Exception:  # pragma: no cover - optional dependency
    markdown = None
try:
    from xhtml2pdf import pisa
except Exception:  # pragma: no cover - optional dependency
    pisa = None


ROOT = Path(__file__).resolve().parent
DEFAULT_BASE = next((p for p in ROOT.glob("11.*") if p.is_dir()), ROOT / "11.idea_tracking")
BASE = Path(os.getenv("IDEA_TRACKER_BASE_DIR", str(DEFAULT_BASE)))
REPORT_DIR = BASE / "daily_reports"
WATCHLIST_PATH = BASE / "ideas_watchlist.json"
RUNNER_PATH = BASE / "run_daily_investment_tracker.cmd"
TASK_LOG_PATH = BASE / "daily_task.log"
DEFAULT_TASK_NAME = "AI_Investment_Idea_Tracker_9AM"

IDEA_TYPES = ["stock", "jp_stock", "fx", "etf", "crypto", "macro", "theme", "other"]
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

POS_WORDS = ["beat", "surge", "rally", "upgrade", "bullish", "growth", "record high"]
NEG_WORDS = ["miss", "drop", "fall", "plunge", "downgrade", "lawsuit", "probe", "warning"]
STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "stock",
    "stocks",
    "news",
    "market",
    "company",
    "latest",
    "share",
    "shares",
    "today",
    "said",
    "china",
    "japan",
    "price",
    "prices",
    "report",
    "analysis",
}
BIAS_ZH = {
    "positive": "\u504f\u6b63\u9762",
    "negative": "\u504f\u8d1f\u9762",
    "neutral": "\u4e2d\u6027",
}
SUMMARY_COMPANY_LINKS = 2
SUMMARY_INDUSTRY_LINKS = 2
HY_OAS_FRED_SERIES = "BAMLH0A0HYM2"
HY_OAS_LOOKBACK_MONTHS = 6
HY_OAS_TREND_THRESHOLD_PCT = 0.25

Z1_SHORT_DEBT_SHARE_SERIES = "BOGZ1FL104140006Q"
Z1_LIQUID_ASSETS_TO_STL_SERIES = "BOGZ1FL104001006Q"
Z1_INTEREST_PAID_SERIES = "BOGZ1FA106130001Q"
Z1_PROFITS_BEFORE_TAX_SERIES = "BOGZ1FA106060005Q"
Z1_CCA_SERIES = "BOGZ1FA106300015Q"
NET_OPERATING_SURPLUS_SERIES = "NCBOSNQ027S"


def now_local() -> datetime:
    return datetime.now().astimezone()


def now_str() -> str:
    return now_local().strftime("%Y-%m-%d %H:%M:%S")


def split_keywords(raw: str) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in re.split(r"[,，;；\n]+", raw):
        k = item.strip()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def to_float(v) -> float | None:
    try:
        if v in ("", None, "N/D", "No data"):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def fmt_num(v: float | None, digits: int = 2) -> str:
    return "N/A" if v is None else f"{v:,.{digits}f}"


def fmt_pct(v: float | None) -> str:
    return "N/A" if v is None else f"{v:+.2f}%"


def zh_bias(v: str) -> str:
    return BIAS_ZH.get((v or "").strip().lower(), "中性")


def parse_datetime(raw: str) -> datetime | None:
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone()
    except Exception:
        pass
    try:
        dt2 = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt2.tzinfo is None:
            dt2 = dt2.replace(tzinfo=timezone.utc)
        return dt2.astimezone()
    except Exception:
        return None


def ensure_storage() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if not WATCHLIST_PATH.exists():
        save_watchlist({"version": 2, "updated_at": now_str(), "ideas": []})


def load_watchlist() -> dict:
    ensure_storage()
    try:
        data = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {"version": 2, "updated_at": now_str(), "ideas": []}
    if "ideas" not in data or not isinstance(data["ideas"], list):
        data["ideas"] = []
    return data


def save_watchlist(data: dict) -> None:
    data["updated_at"] = now_str()
    WATCHLIST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def make_idea_id(seed: str, idea_type: str) -> str:
    h = hashlib.sha1(f"{idea_type}:{seed.strip().lower()}".encode("utf-8")).hexdigest()[:10]
    return f"{idea_type}-{h}"


def active_ideas(data: dict) -> list[dict]:
    return [x for x in data.get("ideas", []) if x.get("active", True)]


def find_idea_index(data: dict, idea_id: str, symbol: str, title: str) -> int | None:
    for i, x in enumerate(data.get("ideas", [])):
        if idea_id and str(x.get("id", "")) == idea_id:
            return i
        if symbol and str(x.get("symbol", "")).upper() == symbol.upper():
            return i
        if title and str(x.get("title", "")).strip().lower() == title.strip().lower():
            return i
    return None


def canonicalize_symbol(raw: str, idea_type: str, market_hint: str) -> tuple[str, str, str]:
    s = raw.strip().upper().replace(" ", "")
    market = market_hint.strip().upper() if market_hint else ""
    if not s:
        return "", market, ""

    if idea_type == "fx" or market == "FX":
        pair = s.replace("/", "")
        return pair, "FX", pair.lower()

    if s.endswith(".HK") or re.fullmatch(r"\d{4,5}", s):
        n = int(s.split(".")[0])
        return f"{n:04d}.HK", "HK", f"{n}.hk"
    if s.endswith((".JP", ".T")) or re.fullmatch(r"\d{4}", s):
        n = s.split(".")[0]
        return f"{n}.JP", "JP", f"{n}.jp"
    if s.endswith((".SS", ".SZ", ".BJ")) or re.fullmatch(r"\d{6}", s):
        n = s.split(".")[0]
        return f"{n}.CN", "CN", f"{n}.cn"

    us = s.replace(".US", "")
    return us, (market or "US"), f"{us.lower()}.us"


def cmd_add(args: argparse.Namespace) -> None:
    data = load_watchlist()
    idea_type = args.type.lower().strip()
    if idea_type not in IDEA_TYPES:
        raise ValueError(f"Unsupported type: {idea_type}")

    target = args.target.strip()
    symbol_input = (args.symbol or target).strip() if idea_type in {"stock", "jp_stock", "fx", "etf", "crypto"} else args.symbol.strip()
    symbol, market, stooq_symbol = canonicalize_symbol(symbol_input, idea_type, args.market)
    title = (args.title or target or symbol).strip()
    if not title:
        raise ValueError("target/title is required")

    idea_id = make_idea_id(symbol or title, idea_type)
    keywords = split_keywords(args.keywords) or [x for x in [title, symbol] if x]
    industry = split_keywords(args.industry)

    payload = {
        "id": idea_id,
        "title": title,
        "type": idea_type,
        "symbol": symbol,
        "stooq_symbol": stooq_symbol,
        "market": market,
        "keywords": keywords,
        "industry_keywords": industry,
        "note": args.note.strip(),
        "added_at": now_str(),
        "active": True,
    }

    idx = find_idea_index(data, idea_id, symbol, title)
    if idx is None:
        data["ideas"].append(payload)
        print(f"[OK] Added: {title} ({idea_id})")
    else:
        data["ideas"][idx].update(payload)
        data["ideas"][idx]["active"] = True
        print(f"[OK] Updated: {title} ({idea_id})")
    save_watchlist(data)


def cmd_remove(args: argparse.Namespace) -> None:
    data = load_watchlist()
    idx = find_idea_index(data, args.id, args.symbol, args.title)
    if idx is None:
        print("[WARN] Idea not found.")
        return
    data["ideas"][idx]["active"] = False
    save_watchlist(data)
    print(f"[OK] Removed: {data['ideas'][idx].get('title')}")


def cmd_list() -> None:
    rows = active_ideas(load_watchlist())
    if not rows:
        print("No active ideas.")
        return
    print(f"Active ideas: {len(rows)}")
    print("-" * 126)
    print(f"{'ID':<22} {'Type':<10} {'Title':<24} {'Symbol':<12} {'Market':<8} {'Keywords':<30} {'Industry'}")
    print("-" * 126)
    for x in rows:
        line = (
            f"{str(x.get('id', ''))[:22]:<22} "
            f"{str(x.get('type', ''))[:10]:<10} "
            f"{str(x.get('title', ''))[:24]:<24} "
            f"{str(x.get('symbol', ''))[:12]:<12} "
            f"{str(x.get('market', ''))[:8]:<8} "
            f"{','.join(x.get('keywords', [])[:3])[:30]:<30} "
            f"{','.join(x.get('industry_keywords', [])[:3])}"
        )
        print(line)


def fetch_stooq_snapshot(stooq_symbol: str) -> dict | None:
    if not stooq_symbol:
        return None
    url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2ohlcvn&e=csv"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    text = r.text.strip()
    if not text or "No data" in text:
        return None
    row = next(csv.reader([text]))
    if len(row) < 9:
        return None
    return {
        "source": "Stooq",
        "symbol": row[0],
        "date": row[1],
        "time": row[2],
        "open": to_float(row[3]),
        "high": to_float(row[4]),
        "low": to_float(row[5]),
        "close": to_float(row[6]),
        "volume": to_float(row[7]),
        "name": row[8],
    }


def fetch_stooq_history(stooq_symbol: str) -> dict | None:
    if not stooq_symbol:
        return None
    url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    text = r.text.strip()
    if not text or text.startswith("No data"):
        return None

    df = pd.read_csv(StringIO(text))
    if df.empty or "Date" not in df.columns or "Close" not in df.columns:
        return None
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.dropna(subset=["Date", "Close"]).sort_values("Date")
    if df.empty:
        return None

    close = df["Close"].reset_index(drop=True)
    latest = float(close.iloc[-1])

    def pct_back(days: int) -> float | None:
        if len(close) <= days:
            return None
        base = float(close.iloc[-1 - days])
        if base == 0:
            return None
        return (latest / base - 1) * 100

    return {
        "source": "Stooq",
        "latest_close": latest,
        "latest_date": df["Date"].iloc[-1].strftime("%Y-%m-%d"),
        "change_1d_pct": pct_back(1),
        "change_5d_pct": pct_back(5),
        "change_20d_pct": pct_back(20),
        "change_60d_pct": pct_back(60),
    }


def fetch_fx_frankfurter(symbol: str) -> dict | None:
    pair = symbol.replace("/", "").upper()
    if not re.fullmatch(r"[A-Z]{6}", pair):
        return None
    base, quote = pair[:3], pair[3:]
    url = f"https://api.frankfurter.app/latest?from={base}&to={quote}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    j = r.json()
    rate = to_float((j.get("rates", {}) or {}).get(quote))
    if rate is None:
        return None
    return {"source": "Frankfurter", "base": base, "quote": quote, "rate": rate, "date": str(j.get("date", ""))}


def fetch_fred_series(series_id: str) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={quote_plus(series_id)}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    raw = r.text.strip()
    if raw.startswith("<!DOCTYPE html>"):
        raise ValueError(f"FRED series unavailable: {series_id}")

    df = pd.read_csv(StringIO(raw))
    if df.empty or len(df.columns) < 2:
        raise ValueError(f"Invalid FRED payload: {series_id}")

    df = df.iloc[:, :2].copy()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"]).sort_values("date")
    if df.empty:
        raise ValueError(f"Empty FRED series after cleanup: {series_id}")
    return df


def render_hy_oas_tracking_section(lookback_months: int = HY_OAS_LOOKBACK_MONTHS) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    try:
        df = fetch_fred_series(HY_OAS_FRED_SERIES)
        latest_date = df["date"].iloc[-1]
        latest_value = float(df["value"].iloc[-1])

        cutoff = latest_date - pd.DateOffset(months=lookback_months)
        window = df[df["date"] >= cutoff].copy()
        if len(window) < 2:
            window = df.tail(max(lookback_months * 21, 2)).copy()

        start_date = window["date"].iloc[0]
        start_value = float(window["value"].iloc[0])
        change_value = latest_value - start_value
        min_value = float(window["value"].min())
        max_value = float(window["value"].max())

        if change_value >= HY_OAS_TREND_THRESHOLD_PCT:
            trend_label = "走阔"
        elif change_value <= -HY_OAS_TREND_THRESHOLD_PCT:
            trend_label = "收窄"
        else:
            trend_label = "震荡"

        monthly = window.set_index("date")["value"].resample("ME").last().dropna().tail(lookback_months + 1)
        monthly_path = " | ".join([f"{idx.strftime('%Y-%m')}:{val:.2f}%" for idx, val in monthly.items()])
        if not monthly_path:
            monthly_path = "N/A"

        return (
            [
                "## HY OAS 每日跟踪",
                f"- 最新值: `{latest_value:.2f}%` ({latest_date.strftime('%Y-%m-%d')})",
                (
                    f"- 过去{lookback_months}个月: "
                    f"`{start_value:.2f}% -> {latest_value:.2f}%` "
                    f"(变动 `{change_value:+.2f}pct`，区间 `{min_value:.2f}%~{max_value:.2f}%`，趋势 `{trend_label}`)"
                ),
                f"- 月度轨迹: {monthly_path}",
            ],
            errors,
        )
    except Exception as exc:
        errors.append(f"HY OAS data failed: {exc}")
        return (
            [
                "## HY OAS 每日跟踪",
                "- 最新值: `N/A` (数据抓取失败)",
                f"- 过去{lookback_months}个月走势: `N/A`",
                "- 月度轨迹: N/A",
            ],
            errors,
        )



def fred_df_to_series(df: pd.DataFrame) -> pd.Series:
    s = df.set_index("date")["value"].sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s


def latest_with_change(series: pd.Series) -> tuple[pd.Timestamp | None, float | None, float | None]:
    if series.empty:
        return None, None, None
    latest_date = series.index[-1]
    latest_val = float(series.iloc[-1])
    if len(series) < 2:
        return latest_date, latest_val, None
    prev_val = float(series.iloc[-2])
    return latest_date, latest_val, latest_val - prev_val


def value_at_or_before(series: pd.Series, target_date: pd.Timestamp) -> float | None:
    idx = series.index[series.index <= target_date]
    if len(idx) == 0:
        return None
    return float(series.loc[idx[-1]])


def consecutive_quarters_both_positive(df: pd.DataFrame, col_a: str, col_b: str) -> int:
    streak = 0
    for _, row in df.iloc[::-1].iterrows():
        if float(row[col_a]) > 0 and float(row[col_b]) > 0:
            streak += 1
        else:
            break
    return streak


def render_credit_risk_dashboard() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    lines: list[str] = [
        "## \u4fe1\u7528\u98ce\u9669\u770b\u677f\uff08\u4e09\u56e0\u5b50\uff09",
        "- \u89e6\u53d1\u89c4\u5219\uff1a\u4ec5\u5f53\u4e09\u4e2a\u5b50\u9879\u540c\u65f6\u6076\u5316\uff0c\u201c\u98ce\u9669\u653e\u5927\u4fe1\u53f7\u201d\u624d\u4e3a ON\u3002",
    ]

    z1_worsening = False
    hy_worsening = False
    interest_worsening = False

    lines.extend(["", "### 1) Z.1 \u671f\u9650\u4e0e\u6d41\u52a8\u6027"])
    try:
        short_s = fred_df_to_series(fetch_fred_series(Z1_SHORT_DEBT_SHARE_SERIES))
        liq_s = fred_df_to_series(fetch_fred_series(Z1_LIQUID_ASSETS_TO_STL_SERIES))

        s_date, s_latest, s_qoq = latest_with_change(short_s)
        l_date, l_latest, l_qoq = latest_with_change(liq_s)

        lines.append(
            f"- \u77ed\u671f\u503a\u52a1/\u603b\u503a\u52a1\uff1a`{fmt_num(s_latest)}%`\uff08{s_date.strftime('%Y-%m-%d') if s_date is not None else 'N/A'}\uff09\uff0cQoQ `{f'{s_qoq:+.2f}pct' if s_qoq is not None else 'N/A'}`\u3002"
        )
        lines.append(
            f"- \u6d41\u52a8\u8d44\u4ea7/\u77ed\u671f\u8d1f\u503a\uff1a`{fmt_num(l_latest)}%`\uff08{l_date.strftime('%Y-%m-%d') if l_date is not None else 'N/A'}\uff09\uff0cQoQ `{f'{l_qoq:+.2f}pct' if l_qoq is not None else 'N/A'}`\u3002"
        )

        z1_worsening = (s_qoq is not None and s_qoq > 0) and (l_qoq is not None and l_qoq < 0)
        lines.append(
            f"- \u5b50\u9879\u72b6\u6001\uff1a`{'恶化' if z1_worsening else '未恶化'}`\uff08\u89c4\u5219\uff1a\u77ed\u503a\u5360\u6bd4\u4e0a\u5347\u4e14\u6d41\u52a8\u6027\u6bd4\u4f8b\u4e0b\u964d\uff09\u3002"
        )
    except Exception as exc:
        errors.append(f"Z.1 block failed: {exc}")
        lines.append("- Z.1 \u5b50\u9879\uff1a`N/A`\uff08\u6570\u636e\u6293\u53d6/\u8ba1\u7b97\u5931\u8d25\uff09\u3002")

    lines.extend(["", "### 2) HY OAS\uff08ICE BofA\uff09"])
    try:
        hy_s = fred_df_to_series(fetch_fred_series(HY_OAS_FRED_SERIES))
        h_date, h_latest, _ = latest_with_change(hy_s)
        if h_date is None or h_latest is None:
            raise ValueError("empty HY OAS series")

        six_m_ago_val = value_at_or_before(hy_s, h_date - pd.DateOffset(months=HY_OAS_LOOKBACK_MONTHS))
        hy_6m_chg = (h_latest - six_m_ago_val) if six_m_ago_val is not None else None

        if hy_6m_chg is None:
            hy_trend = "N/A"
        elif hy_6m_chg > HY_OAS_TREND_THRESHOLD_PCT:
            hy_trend = "\u8d70\u9614"
        elif hy_6m_chg < -HY_OAS_TREND_THRESHOLD_PCT:
            hy_trend = "\u6536\u7a84"
        else:
            hy_trend = "\u5e73\u7a33"

        hy_worsening = hy_6m_chg is not None and hy_6m_chg > HY_OAS_TREND_THRESHOLD_PCT
        lines.append(f"- \u6700\u65b0 HY OAS\uff1a`{h_latest:.2f}%`\uff08{h_date.strftime('%Y-%m-%d')}\uff09\u3002")
        lines.append(
            f"- 6\u4e2a\u6708\u53d8\u52a8\uff1a`{f'{hy_6m_chg:+.2f}pct' if hy_6m_chg is not None else 'N/A'}` \uff5c \u8d70\u52bf\uff1a`{hy_trend}`\u3002"
        )
        lines.append(
            f"- \u5b50\u9879\u72b6\u6001\uff1a`{'恶化' if hy_worsening else '未恶化'}`\uff08\u89c4\u5219\uff1a6\u4e2a\u6708\u5229\u5dee\u8d70\u9614 > {HY_OAS_TREND_THRESHOLD_PCT:.2f}pct\uff09\u3002"
        )
    except Exception as exc:
        errors.append(f"HY OAS block failed: {exc}")
        lines.append("- HY OAS \u5b50\u9879\uff1a`N/A`\uff08\u6570\u636e\u6293\u53d6/\u8ba1\u7b97\u5931\u8d25\uff09\u3002")

    lines.extend(["", "### 3) \u5229\u606f\u8d1f\u62c5\u7f3a\u53e3\uff08\u540c\u6bd4\uff09"])
    try:
        interest = fred_df_to_series(fetch_fred_series(Z1_INTEREST_PAID_SERIES))
        pbt = fred_df_to_series(fetch_fred_series(Z1_PROFITS_BEFORE_TAX_SERIES))
        cca = fred_df_to_series(fetch_fred_series(Z1_CCA_SERIES))
        nos = fred_df_to_series(fetch_fred_series(NET_OPERATING_SURPLUS_SERIES))

        q = pd.concat([interest, pbt, cca, nos], axis=1, join="inner").dropna()
        q.columns = ["interest_paid", "pbt", "cca", "net_operating_surplus"]
        q["ebitda_proxy"] = q["pbt"] + q["interest_paid"] + q["cca"]
        q["interest_yoy"] = q["interest_paid"].pct_change(4) * 100
        q["ebitda_yoy"] = q["ebitda_proxy"].pct_change(4) * 100
        q["nos_yoy"] = q["net_operating_surplus"].pct_change(4) * 100
        q["diff_vs_ebitda"] = q["interest_yoy"] - q["ebitda_yoy"]
        q["diff_vs_nos"] = q["interest_yoy"] - q["nos_yoy"]
        q = q.dropna(subset=["interest_yoy", "ebitda_yoy", "nos_yoy", "diff_vs_ebitda", "diff_vs_nos"])
        if q.empty:
            raise ValueError("empty interest-gap frame")

        latest = q.iloc[-1]
        latest_date = q.index[-1]
        streak = consecutive_quarters_both_positive(q, "diff_vs_ebitda", "diff_vs_nos")
        interest_worsening = (latest["diff_vs_ebitda"] > 0 and latest["diff_vs_nos"] > 0 and streak >= 2)

        tail = q[["diff_vs_ebitda", "diff_vs_nos"]].tail(4)
        diff_path = " | ".join(
            [
                f"{idx.year}Q{((idx.month - 1) // 3) + 1}: dE {row['diff_vs_ebitda']:+.2f}, dNOS {row['diff_vs_nos']:+.2f}"
                for idx, row in tail.iterrows()
            ]
        )

        lines.append(
            f"- \u6700\u65b0\uff08{latest_date.strftime('%Y-%m-%d')}\uff09\uff1a\u5229\u606f\u652f\u51fa\u540c\u6bd4 `{latest['interest_yoy']:+.2f}%`\uff0cEBITDA\u4ee3\u7406\u540c\u6bd4 `{latest['ebitda_yoy']:+.2f}%`\uff0c\u7ecf\u8425\u76c8\u4f59\u540c\u6bd4 `{latest['nos_yoy']:+.2f}%`\u3002"
        )
        lines.append(
            f"- \u7f3a\u53e3\uff1a\u5229\u606f-EBITDA `{latest['diff_vs_ebitda']:+.2f}pct`\uff0c\u5229\u606f-NOS `{latest['diff_vs_nos']:+.2f}pct`\uff1b\u53cc\u7f3a\u53e3>0\u7684\u8fde\u7eed\u5b63\u5ea6\u6570 `{streak}`\u3002"
        )
        lines.append(f"- \u6700\u8fd14\u4e2a\u5b63\u5ea6\u8def\u5f84\uff1a{diff_path}\u3002")
        lines.append(
            f"- \u5b50\u9879\u72b6\u6001\uff1a`{'恶化' if interest_worsening else '未恶化'}`\uff08\u89c4\u5219\uff1a\u4e24\u4e2a\u7f3a\u53e3\u540c\u65f6>0\u4e14\u8fde\u7eed>=2\u4e2a\u5b63\u5ea6\uff09\u3002"
        )
    except Exception as exc:
        errors.append(f"Interest-gap block failed: {exc}")
        lines.append("- \u5229\u606f\u7f3a\u53e3\u5b50\u9879\uff1a`N/A`\uff08\u6570\u636e\u6293\u53d6/\u8ba1\u7b97\u5931\u8d25\uff09\u3002")

    risk_amplification = z1_worsening and hy_worsening and interest_worsening
    lines.extend(
        [
            "",
            "### \u7efc\u5408\u4fe1\u53f7",
            f"- \u98ce\u9669\u653e\u5927\u4fe1\u53f7\uff1a`{'ON' if risk_amplification else 'OFF'}`\u3002",
            f"- \u5b50\u9879\u72b6\u6001\uff1aZ1=`{'恶化' if z1_worsening else '未恶化'}`\uff0cHY OAS=`{'恶化' if hy_worsening else '未恶化'}`\uff0c\u5229\u606f\u7f3a\u53e3=`{'恶化' if interest_worsening else '未恶化'}`\u3002",
        ]
    )
    return lines, errors

def optional_market_data(idea: dict) -> tuple[dict | None, list[str]]:
    errors: list[str] = []
    symbol = str(idea.get("symbol", "")).strip()
    stooq_symbol = str(idea.get("stooq_symbol", "")).strip()
    idea_type = str(idea.get("type", "")).lower()

    snapshot = None
    history = None
    fx_alt = None

    if stooq_symbol:
        try:
            snapshot = fetch_stooq_snapshot(stooq_symbol)
        except Exception as exc:
            errors.append(f"stooq snapshot failed: {exc}")
        try:
            history = fetch_stooq_history(stooq_symbol)
        except Exception as exc:
            errors.append(f"stooq history failed: {exc}")

    if idea_type == "fx" and symbol:
        try:
            fx_alt = fetch_fx_frankfurter(symbol)
        except Exception as exc:
            errors.append(f"frankfurter failed: {exc}")

    return {"snapshot": snapshot, "history": history, "fx_alt": fx_alt}, errors


def fetch_rss_items(feed_url: str, feed_name: str) -> list[dict]:
    req = Request(feed_url, headers=HTTP_HEADERS)
    with urlopen(req, timeout=3) as resp:
        xml_data = resp.read()
    root = ET.fromstring(xml_data)
    out: list[dict] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_raw = (item.findtext("pubDate") or item.findtext("published") or "").strip()
        dt = parse_datetime(pub_raw)
        pub = dt.strftime("%Y-%m-%d %H:%M") if dt else (pub_raw or "N/A")
        source_node = item.find("source")
        source = (source_node.text or "").strip() if source_node is not None else ""
        if not source:
            m = re.search(r"\s-\s([^-]+)$", title)
            if m:
                source = m.group(1).strip()
        if title and link:
            out.append(
                {
                    "title": title,
                    "link": link,
                    "source": source or feed_name,
                    "published": pub,
                    "published_dt": dt,
                    "feed": feed_name,
                }
            )
    return out


def fetch_latest_news(query: str, limit: int) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    if not query.strip():
        return [], ["empty query"]

    q_with_time = quote_plus(f"{query} when:7d")
    feeds = [
        (f"https://www.bing.com/news/search?q={quote_plus(query)}&format=RSS", "BingNews"),
    ]

    items: list[dict] = []
    for url, name in feeds:
        try:
            items.extend(fetch_rss_items(url, name))
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    dedup: dict[str, dict] = {}
    for it in items:
        key = re.sub(r"\s+", " ", it["title"].strip().lower()) + "|" + it["link"].strip()
        if key not in dedup:
            dedup[key] = it
    merged = list(dedup.values())
    cutoff = now_local() - timedelta(days=10)
    merged = [x for x in merged if (x.get("published_dt") is None or x.get("published_dt") >= cutoff)]
    merged.sort(
        key=lambda x: (
            x["published_dt"] is not None,
            x["published_dt"] or datetime(1970, 1, 1, tzinfo=timezone.utc),
        ),
        reverse=True,
    )
    return merged[:limit], errors


def news_stats(items: list[dict]) -> dict:
    now = now_local()
    c24 = 0
    c72 = 0
    latest_dt = None
    pos = 0
    neg = 0
    tok = Counter()

    for it in items:
        dt = it.get("published_dt")
        if dt:
            if latest_dt is None or dt > latest_dt:
                latest_dt = dt
            if dt >= now - timedelta(hours=24):
                c24 += 1
            if dt >= now - timedelta(hours=72):
                c72 += 1

        title_lower = str(it.get("title", "")).lower()
        if any(w in title_lower for w in POS_WORDS):
            pos += 1
        if any(w in title_lower for w in NEG_WORDS):
            neg += 1

        for word in re.findall(r"[A-Za-z]{4,}|[\u4e00-\u9fff]{2,}", str(it.get("title", ""))):
            w2 = word.lower()
            if w2 in STOP_WORDS:
                continue
            tok[w2] += 1

    bias = "neutral"
    if pos - neg >= 2:
        bias = "positive"
    elif neg - pos >= 2:
        bias = "negative"
    return {
        "count_total": len(items),
        "count_24h": c24,
        "count_72h": c72,
        "latest_time": latest_dt.strftime("%Y-%m-%d %H:%M") if latest_dt else "N/A",
        "pos_hits": pos,
        "neg_hits": neg,
        "bias": bias,
        "top_terms": [w for w, _ in tok.most_common(6)],
    }


def compose_news_queries(idea: dict) -> tuple[str, str]:
    title = str(idea.get("title", "")).strip()
    symbol = str(idea.get("symbol", "")).strip()
    idea_type = str(idea.get("type", "")).strip().lower()
    keywords = list(idea.get("keywords", []))
    industry = list(idea.get("industry_keywords", []))

    base_parts = [x for x in [title, symbol] + keywords[:3] if x]
    company_query = " ".join(dict.fromkeys(base_parts)).strip()

    if industry:
        industry_query = " ".join(industry[:4])
    elif idea_type == "fx":
        industry_query = f"{symbol or title} forex central bank inflation rate"
    elif idea_type == "jp_stock":
        industry_query = f"{title or symbol} Japan industry supply chain"
    elif idea_type in {"stock", "etf", "crypto"}:
        industry_query = f"{title or symbol} industry competition"
    elif idea_type == "macro":
        industry_query = f"{title} macro policy inflation growth"
    else:
        industry_query = f"{title or symbol} industry"

    if not company_query:
        company_query = industry_query
    return company_query, industry_query


def md_news(items: list[dict]) -> str:
    if not items:
        return "- 未抓取到相关新闻。\n"
    lines = []
    for it in items:
        title = str(it.get("title", "")).replace("\n", " ").strip()
        link = str(it.get("link", ""))
        source = str(it.get("source", ""))
        pub = str(it.get("published", ""))
        meta = " | ".join([x for x in [pub, source] if x])
        lines.append(f"- [{title}]({link})  ({meta})")
    return "\n".join(lines) + "\n"


def classify_clue_tag(title: str) -> str:
    t = (title or "").lower()
    rules = [
        ("\u8d22\u62a5/\u4e1a\u7ee9", ["earnings", "revenue", "profit", "guidance", "??", "??", "??", "??"]),
        ("\u878d\u8d44/\u8d44\u672c\u5f00\u652f", ["bond", "debt", "funding", "capex", "issuance", "??", "??", "??", "????"]),
        ("\u4ea7\u54c1/\u6280\u672f", ["ai", "chip", "hbm", "product", "launch", "fsd", "??", "??", "??", "??"]),
        ("\u653f\u7b56/\u76d1\u7ba1", ["regulator", "policy", "tariff", "lawsuit", "probe", "boj", "fed", "??", "??", "??", "??"]),
        ("\u884c\u4e1a\u4f9b\u9700", ["demand", "supply", "industry", "capacity", "??", "??", "??", "??", "??"]),
        ("\u4ef7\u683c/\u5e02\u573a\u8868\u73b0", ["stock", "shares", "rally", "drop", "surge", "plunge", "??", "??", "??"]),
    ]
    for label, patterns in rules:
        if any(p in t for p in patterns):
            return label
    return "\u5176\u4ed6"

def norm_title_for_dedup(title: str) -> str:
    x = re.sub(r"\s+", " ", (title or "").strip().lower())
    x = re.sub(r"\s*-\s*[^-]{1,40}$", "", x)
    return x


def select_key_clues(company_news: list[dict], industry_news: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []

    def pick(items: list[dict], domain: str, limit: int) -> None:
        cnt = 0
        for it in items:
            key = norm_title_for_dedup(str(it.get("title", "")))
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "domain": domain,
                    "title": str(it.get("title", "")).strip(),
                    "link": str(it.get("link", "")).strip(),
                    "source": str(it.get("source", "")).strip(),
                    "published": str(it.get("published", "")).strip(),
                    "published_dt": it.get("published_dt"),
                    "tag": classify_clue_tag(str(it.get("title", ""))),
                }
            )
            cnt += 1
            if cnt >= limit:
                break

    pick(company_news, "标的", SUMMARY_COMPANY_LINKS)
    pick(industry_news, "行业", SUMMARY_INDUSTRY_LINKS)
    out.sort(
        key=lambda x: (
            x.get("published_dt") is not None,
            x.get("published_dt") or datetime(1970, 1, 1, tzinfo=timezone.utc),
        ),
        reverse=True,
    )
    return out


def clue_focus_summary(clues: list[dict]) -> str:
    if not clues:
        return "N/A"
    c = Counter([str(x.get("tag", "\u5176\u4ed6")) for x in clues])
    return "\u3001".join([f"{k}x{v}" for k, v in c.most_common(3)])


def short_title(text: str, max_len: int = 88) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "?"


def clean_news_title(text: str) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    t = re.sub(r"\s*-\s*[^-]{1,40}$", "", t)
    return t.strip(" -|")


def brief_title(text: str, max_len: int = 96) -> str:
    t = clean_news_title(text)
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "?"


def build_idea_overview_lines(
    idea: dict,
    company_stats: dict,
    industry_stats: dict,
    clues: list[dict],
) -> list[str]:
    name = str(idea.get("title", "")).strip() or "\u8be5\u6807\u7684"
    company_kw = "\u3001".join(company_stats.get("top_terms", [])[:3]) if company_stats.get("top_terms") else "\u65e0\u660e\u663e\u96c6\u4e2d"
    industry_kw = "\u3001".join(industry_stats.get("top_terms", [])[:3]) if industry_stats.get("top_terms") else "\u65e0\u660e\u663e\u96c6\u4e2d"
    focus = clue_focus_summary(clues)
    total_72h = int(company_stats.get("count_72h", 0)) + int(industry_stats.get("count_72h", 0))

    sentence_1 = (
        f"\u5173\u4e8e {name}\uff0c\u8fc7\u53bb24\u5c0f\u65f6\u6211\u626b\u63cf\u5230 {company_stats.get('count_24h', 0)} \u6761\u6807\u7684\u76f8\u5173\u52a8\u6001\uff0c"
        f"\u4ee5\u53ca {industry_stats.get('count_24h', 0)} \u6761\u884c\u4e1a\u60c5\u62a5\u3002"
    )
    sentence_2 = (
        f"\u4ece\u5e02\u573a\u60c5\u7eea\u6765\u770b\uff0c\u6807\u7684\u7aef{zh_bias(company_stats.get('bias', 'neutral'))}"
        f"\uff08{company_stats.get('pos_hits', 0)}\u6b63/{company_stats.get('neg_hits', 0)}\u8d1f\uff09\uff0c"
        f"\u884c\u4e1a\u7aef{zh_bias(industry_stats.get('bias', 'neutral'))}"
        f"\uff08{industry_stats.get('pos_hits', 0)}\u6b63/{industry_stats.get('neg_hits', 0)}\u8d1f\uff09\u3002"
    )
    sentence_3 = f"\u5927\u5bb6\u4e3b\u8981\u5728\u8ba8\u8bba **{focus}**\u3002\u6807\u7684\u70ed\u8bcd\u6d89\u53ca\u201c{company_kw}\u201d\uff0c\u884c\u4e1a\u70ed\u8bcd\u5219\u662f\u201c{industry_kw}\u201d\u3002"
    return [sentence_1, sentence_2, sentence_3]


def render_idea_section(
    idea: dict,
    company_news: list[dict],
    industry_news: list[dict],
    company_stats: dict,
    industry_stats: dict,
    errors: list[str],
) -> str:
    clues = select_key_clues(company_news, industry_news)
    overview_lines = build_idea_overview_lines(idea, company_stats, industry_stats, clues)

    lines = [
        f"## {idea.get('title', '')}",
        "",
        f"> \u6807\u8bc6 `{idea.get('id', '')}` | \u7c7b\u578b `{idea.get('type', '')}` | \u4ee3\u7801 `{idea.get('symbol', 'N/A')}` | \u5e02\u573a `{idea.get('market', 'N/A')}`",
        "",
        f"**\u8001\u677f\u8bf7\u770b\u91cd\u70b9\uff1a** {overview_lines[0]}",
        "",
        "### \u8be6\u7ec6\u60c5\u51b5\u6c47\u62a5",
        f"- {overview_lines[1]}",
        f"- {overview_lines[2]}",
        "",
        "### \u539f\u6587\u7ebf\u7d22\u5907\u67e5\uff08Top Clues\uff09",
    ]

    if clues:
        for idx, x in enumerate(clues, 1):
            title = brief_title(str(x.get("title", "")))
            source = x.get("source") or "\u672a\u77e5\u6765\u6e90"
            published = x.get("published") or "N/A"
            lines.append(
                f"{idx}. **{x['domain']} / {x['tag']}**\uff1a{title}\uff08{published}\uff0c{source}\uff09[\u539f\u6587\u94fe\u63a5]({x['link']})"
            )
    else:
        lines.append("- \u8001\u677f\uff0c\u4eca\u65e5\u6682\u672a\u53d1\u73b0\u6709\u4ef7\u503c\u7684\u65b0\u95fb\u7ebf\u7d22\u3002")

    lines.append("")
    if errors:
        lines.append("### \u6293\u53d6\u5907\u6ce8\uff08\u975e\u963b\u585e\uff09")
        lines.extend([f"- {e}" for e in errors[:3]])
        lines.append("")

    lines.extend(["---", ""])
    return "\n".join(lines)

def build_report_html(markdown_text: str) -> str:
    if markdown is not None:
        body_html = markdown.markdown(
            markdown_text,
            extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
        )
    else:
        body_html = "<pre>" + html.escape(markdown_text) + "</pre>"

    css = f"""
    <style>
      @page {{ size: A4; margin: 1.6cm; }}
      body {{
        font-family: STSong-Light, "Microsoft YaHei", "SimHei", Arial, sans-serif;
        color: #1f2937;
        line-height: 1.55;
        font-size: 12px;
      }}
      h1 {{
        font-size: 24px;
        color: #0f766e;
        border-bottom: 3px solid #0f766e;
        padding-bottom: 8px;
      }}
      h2 {{
        font-size: 18px;
        color: #155e75;
        margin-top: 20px;
      }}
      h3 {{
        font-size: 14px;
        color: #0f172a;
        margin-top: 14px;
      }}
      table {{
        border-collapse: collapse;
        width: 100%;
        margin: 8px 0 14px 0;
      }}
      th, td {{
        border: 1px solid #cbd5e1;
        padding: 6px 8px;
        text-align: left;
      }}
      th {{
        background: #ecfeff;
        color: #134e4a;
      }}
      code {{
        background: #f1f5f9;
        padding: 1px 4px;
      }}
      a {{
        color: #0369a1;
        text-decoration: none;
      }}
      a:hover {{
        text-decoration: underline;
      }}
    </style>
    """

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        + css
        + "</head><body>"
        + body_html
        + "</body></html>"
    )


def export_html_pdf(md_path: Path) -> tuple[Path, Path | None, list[str]]:
    notes: list[str] = []
    markdown_text = md_path.read_text(encoding="utf-8")
    html_path = md_path.with_suffix(".html")
    pdf_path = md_path.with_suffix(".pdf")
    html_doc = build_report_html(markdown_text)
    html_path.write_text(html_doc, encoding="utf-8")

    if pisa is None:
        notes.append("未安装 xhtml2pdf，已跳过 PDF 导出。")
        return html_path, None, notes

    try:
        with open(pdf_path, "wb") as f:
            status = pisa.CreatePDF(html_doc, dest=f, encoding="utf-8")
        if status.err:
            notes.append(f"PDF 导出失败，错误数: {status.err}")
            try:
                if pdf_path.exists():
                    pdf_path.unlink()
            except Exception:
                pass
            return html_path, None, notes
        return html_path, pdf_path, notes
    except Exception as exc:
        notes.append(f"PDF 导出异常: {exc}")
        try:
            if pdf_path.exists():
                pdf_path.unlink()
        except Exception:
            pass
        return html_path, None, notes


def generate_daily_report(news_limit: int) -> dict | None:
    rows = active_ideas(load_watchlist())
    if not rows:
        print("没有活跃跟踪标的，请先使用 add 添加。")
        return None

    day = now_local().strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"{day}-investment-idea-tracking-report.md"
    if report_path.exists():
        report_path = REPORT_DIR / f"{day}-investment-idea-tracking-report-{now_local().strftime('%H%M%S')}.md"

    sections: list[str] = []
    total_news = 0
    total_errors = 0
    heat_rows: list[tuple[int, str, str, str]] = []

    for idea in rows:
        errors: list[str] = []
        q_company, q_industry = compose_news_queries(idea)

        company_news, c_err = fetch_latest_news(q_company, limit=news_limit)
        industry_news, i_err = fetch_latest_news(q_industry, limit=news_limit)
        errors.extend([f"标的新闻: {x}" for x in c_err])
        errors.extend([f"行业新闻: {x}" for x in i_err])

        c_stats = news_stats(company_news)
        i_stats = news_stats(industry_news)
        total_news += len(company_news) + len(industry_news)
        heat_rows.append(
            (
                c_stats["count_24h"] + i_stats["count_24h"],
                str(idea.get("title", "")),
                zh_bias(c_stats["bias"]),
                zh_bias(i_stats["bias"]),
            )
        )

        total_errors += len(errors)

        sections.append(
            render_idea_section(
                idea=idea,
                company_news=company_news,
                industry_news=industry_news,
                company_stats=c_stats,
                industry_stats=i_stats,
                errors=errors,
            )
        )

    heat_rows.sort(key=lambda x: x[0], reverse=True)
    top_heat = heat_rows[:3]
    credit_section, credit_errors = render_credit_risk_dashboard()
    total_errors += len(credit_errors)
    header = [
        "# 老板，这是今日的投资机会跟踪日报",
        "",
        f"> **汇报时间**：{now_str()}",
        f"> **跟踪范围**：覆盖 {len(rows)} 个核心标的，今日共扫描 {total_news} 条动态",
        "",
        "## 老板，今日重点摘要（Executive Summary）",
    ]
    if top_heat:
        for score, name, cb, ib in top_heat:
            header.append(f"- **{name}**：今日关注度较高，近24h有 {score} 条线索（{cb} / {ib}）。")
    else:
        header.append("- 老板，今日市场消息面比较清淡，暂无显著热点。")
    
    top_names = "、".join([x[1] for x in top_heat]) if top_heat else "热点较为分散"
    
    header.extend(
        [
            "",
            "### 总体情况汇报",
            f"老板好，为您呈上今日市场动态。今天我们重点跟踪了 {len(rows)} 个关注标的。从热度来看，**{top_names}** 是今天市场关注的焦点。",
            "您可以先浏览下方的“一句话综述”快速掌握要点，若对细节感兴趣，再查看具体的“重点新闻摘要”。",
        ]
    )

    if credit_section:
        header.extend(["", *credit_section])
    header.extend(
        [
        "",
        "---",
        "",
        ]
    )
    md_text = "\n".join(header + sections)
    report_path.write_text(md_text, encoding="utf-8")
    html_path, pdf_path, export_notes = export_html_pdf(report_path)

    print(f"[OK] 已生成 Markdown 报告: {report_path}")
    print(f"[OK] 已生成 HTML 报告: {html_path}")
    if pdf_path:
        print(f"[OK] 已生成 PDF 报告: {pdf_path}")
    else:
        print("[WARN] PDF 报告未生成。")
    for note in export_notes:
        print(f"[WARN] {note}")

    return {"md": report_path, "html": html_path, "pdf": pdf_path, "notes": export_notes}


def notify_popup(title: str, message: str) -> bool:
    if os.name != "nt":
        return False
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x00001040)
        return True
    except Exception:
        return False


def open_report(path: Path) -> bool:
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
            return True
    except Exception:
        return False
    return False


def cmd_run_daily(args: argparse.Namespace) -> int:
    reports = generate_daily_report(news_limit=max(1, int(args.news_limit)))
    if reports is None:
        return 1
    md_report = reports.get("md")
    html_report = reports.get("html")
    pdf_report = reports.get("pdf")
    if args.notify:
        notify_popup(
            "投资机会跟踪提醒",
            (
                f"报告已生成:\n"
                f"Markdown: {md_report.name if md_report else 'N/A'}\n"
                f"HTML: {html_report.name if html_report else 'N/A'}\n"
                f"PDF: {pdf_report.name if pdf_report else '未生成'}\n\n"
                "请复盘今日跟踪要点。"
            ),
        )
    if args.open_report:
        open_report(pdf_report or html_report or md_report)
    return 0


def validate_hhmm(value: str) -> str:
    if not re.fullmatch(r"\d{2}:\d{2}", value):
        raise ValueError("time must be HH:MM")
    h, m = map(int, value.split(":"))
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("time out of range")
    return f"{h:02d}:{m:02d}"


def write_runner(news_limit: int, notify: bool, auto_open: bool) -> Path:
    args = ["run-daily", "--news-limit", str(news_limit)]
    if notify:
        args.append("--notify")
    if auto_open:
        args.append("--open-report")
    cmdline = " ".join(args)
    content = "\n".join(
        [
            "@echo off",
            "setlocal",
            "pushd \"%~dp0..\"",
            f"python \"stock_tracker.py\" {cmdline} >> \"%~dp0daily_task.log\" 2>&1",
            f"if errorlevel 9009 py -3 \"stock_tracker.py\" {cmdline} >> \"%~dp0daily_task.log\" 2>&1",
            "popd",
            "endlocal",
        ]
    )
    RUNNER_PATH.write_text(content + "\n", encoding="utf-8")
    return RUNNER_PATH


def cmd_setup_task(args: argparse.Namespace) -> int:
    if os.name != "nt":
        print("Task scheduler setup is only supported on Windows.")
        return 1
    run_time = validate_hhmm(args.time)
    runner = write_runner(args.news_limit, args.notify, args.open_report)
    tr_value = f'"{runner}"'
    cmd = [
        "schtasks",
        "/Create",
        "/F",
        "/SC",
        "DAILY",
        "/ST",
        run_time,
        "/TN",
        args.task_name,
        "/TR",
        tr_value,
    ]
    print("Command:")
    print(" ".join(cmd))
    print(f"Runner: {runner}")
    if args.dry_run:
        print("[DRY-RUN] Task not created.")
        return 0
    res = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    if res.returncode == 0:
        print(f"[OK] Task created: {args.task_name} @ {run_time}")
        return 0
    print("[ERROR] Task creation failed.")
    if res.stdout.strip():
        print(res.stdout.strip())
    if res.stderr.strip():
        print(res.stderr.strip())
    return res.returncode or 1


def cmd_remove_task(args: argparse.Namespace) -> int:
    if os.name != "nt":
        print("Task scheduler setup is only supported on Windows.")
        return 1
    cmd = ["schtasks", "/Delete", "/F", "/TN", args.task_name]
    res = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    if res.returncode == 0:
        print(f"[OK] Task deleted: {args.task_name}")
        return 0
    print("[WARN] Task delete failed or task not found.")
    if res.stdout.strip():
        print(res.stdout.strip())
    if res.stderr.strip():
        print(res.stderr.strip())
    return res.returncode or 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Investment idea tracker (news-first)")
    sub = p.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add an idea")
    p_add.add_argument("target", help="Symbol or idea title")
    p_add.add_argument("--type", default="stock", choices=IDEA_TYPES)
    p_add.add_argument("--symbol", default="")
    p_add.add_argument("--title", default="")
    p_add.add_argument("--market", default="", help="US/HK/CN/JP/FX etc")
    p_add.add_argument("--keywords", default="", help="Comma separated")
    p_add.add_argument("--industry", default="", help="Comma separated")
    p_add.add_argument("--note", default="")

    p_rm = sub.add_parser("remove", help="Soft remove an idea")
    p_rm.add_argument("--id", default="")
    p_rm.add_argument("--symbol", default="")
    p_rm.add_argument("--title", default="")

    sub.add_parser("list", help="List active ideas")

    p_run = sub.add_parser("run-daily", help="Generate daily report now")
    p_run.add_argument("--news-limit", type=int, default=8)
    p_run.add_argument("--notify", action="store_true")
    p_run.add_argument("--open-report", action="store_true")

    p_setup = sub.add_parser("setup-task", help="Setup Windows 09:00 task")
    p_setup.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    p_setup.add_argument("--time", default="09:00", help="HH:MM")
    p_setup.add_argument("--news-limit", type=int, default=8)
    p_setup.add_argument("--notify", action=argparse.BooleanOptionalAction, default=True)
    p_setup.add_argument("--open-report", action=argparse.BooleanOptionalAction, default=False)
    p_setup.add_argument("--dry-run", action="store_true")

    p_del = sub.add_parser("remove-task", help="Remove Windows task")
    p_del.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    return p


def main() -> int:
    ensure_storage()
    args = build_parser().parse_args()
    if args.command == "add":
        cmd_add(args)
        return 0
    if args.command == "remove":
        cmd_remove(args)
        return 0
    if args.command == "list":
        cmd_list()
        return 0
    if args.command == "run-daily":
        return cmd_run_daily(args)
    if args.command == "setup-task":
        return cmd_setup_task(args)
    if args.command == "remove-task":
        return cmd_remove_task(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
