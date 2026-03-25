#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
周度 AI 复盘引擎 — 自动化投资嗅觉周报

每周汇总：概率变化 / 新信号 / 被忽略的机会 / 行动建议
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (
    DATA_DIR,
    WEEKLY_REVIEWS_DIR,
    TRACKER_DIR,
    WATCHLIST_PATH,
    SIGNALS_FILE,
    CONVICTION_LOG_FILE,
)


# ---------------------------------------------------------------------------
# 数据加载辅助
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> list | dict:
    if not path.exists():
        return [] if path.suffix == ".json" else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _load_tracker_states() -> list[dict]:
    """加载贝叶斯追踪器所有活跃状态"""
    trackers_file = TRACKER_DIR / "data" / "trackers.json"
    if not trackers_file.exists():
        return []
    try:
        data = json.loads(trackers_file.read_text(encoding="utf-8"))
        trackers = data.get("trackers", {})
        return [v for v in trackers.values() if v.get("active", True)]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# 核心 API
# ---------------------------------------------------------------------------

def generate_weekly_review(week_end_date: str | None = None) -> dict:
    """
    生成周度复盘信

    参数:
        week_end_date: 周结束日期(YYYY-MM-DD)，默认当天

    返回:
        结构化复盘数据
    """
    if not week_end_date:
        week_end_date = datetime.now().strftime("%Y-%m-%d")

    review = {
        "week_end": week_end_date,
        "generated_at": datetime.now().isoformat(),
        "sections": {},
    }

    # 1. 概率变化 TOP 5
    states = _load_tracker_states()
    prob_rankings = []
    for s in states:
        snapshots = s.get("daily_snapshots", [])
        if len(snapshots) >= 2:
            latest = snapshots[-1].get("probability", 0.5)
            week_ago = snapshots[-min(7, len(snapshots))].get("probability", 0.5)
            change = latest - week_ago
        else:
            latest = s.get("current_probability", 0.5)
            change = 0
        prob_rankings.append({
            "ticker": s.get("ticker", ""),
            "probability": latest,
            "change_7d": round(change, 4),
            "thesis": s.get("thesis", "")[:60],
        })

    prob_rankings.sort(key=lambda x: abs(x["change_7d"]), reverse=True)
    review["sections"]["probability_movers"] = prob_rankings[:5]

    # 2. 本周新信号
    signals = _load_json(SIGNALS_FILE)
    if isinstance(signals, list):
        week_start = (datetime.strptime(week_end_date, "%Y-%m-%d") - timedelta(days=7)).isoformat()
        new_signals = [
            s for s in signals
            if s.get("created_at", "") >= week_start
        ]
    else:
        new_signals = []
    review["sections"]["new_signals"] = len(new_signals)
    review["sections"]["new_signals_detail"] = new_signals[:10]

    # 3. 信念阶梯升级记录
    conv_log = _load_json(CONVICTION_LOG_FILE)
    if isinstance(conv_log, list):
        week_start_str = (datetime.strptime(week_end_date, "%Y-%m-%d") - timedelta(days=7)).isoformat()
        recent_upgrades = [
            e for e in conv_log
            if e.get("timestamp", "") >= week_start_str
        ]
    else:
        recent_upgrades = []
    review["sections"]["upgrades"] = recent_upgrades

    # 4. 被忽略的机会
    ignored = detect_ignored_opportunities(states)
    review["sections"]["ignored_opportunities"] = ignored

    # 5. 汇总统计
    review["sections"]["summary"] = {
        "active_trackers": len(states),
        "total_signals": len(signals) if isinstance(signals, list) else 0,
        "new_signals_this_week": len(new_signals),
        "upgrades_this_week": len(recent_upgrades),
        "ignored_count": len(ignored),
    }

    return review


def detect_ignored_opportunities(states: list[dict] | None = None) -> list[dict]:
    """
    检测被忽略的机会：概率 ≥ 60% 但尚未有深度研究记录的标的
    """
    if states is None:
        states = _load_tracker_states()

    conv_log = _load_json(CONVICTION_LOG_FILE)
    researched_tickers = set()
    if isinstance(conv_log, list):
        for entry in conv_log:
            if entry.get("to_level", "") in ("L3", "L5", "HEAVY"):
                researched_tickers.add(entry.get("ticker", ""))

    ignored = []
    for s in states:
        prob = s.get("current_probability", 0.5)
        ticker = s.get("ticker", "")
        if prob >= 0.60 and ticker not in researched_tickers:
            ignored.append({
                "ticker": ticker,
                "probability": prob,
                "thesis": s.get("thesis", ""),
                "suggestion": f"概率已达 {prob:.0%}，建议启动 @估值 {ticker} 或 @护城河 {ticker} 中度研究",
            })

    return sorted(ignored, key=lambda x: x["probability"], reverse=True)


def save_review(review: dict) -> Path:
    """保存周度复盘"""
    WEEKLY_REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"weekly-review-{review['week_end']}.json"
    filepath = WEEKLY_REVIEWS_DIR / filename
    filepath.write_text(
        json.dumps(review, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return filepath


def list_past_reviews() -> list[dict]:
    """列出历史周报"""
    if not WEEKLY_REVIEWS_DIR.exists():
        return []
    reviews = []
    for f in sorted(WEEKLY_REVIEWS_DIR.glob("weekly-review-*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            reviews.append({
                "file": f.name,
                "week_end": data.get("week_end", ""),
                "summary": data.get("sections", {}).get("summary", {}),
            })
        except Exception:
            pass
    return reviews
