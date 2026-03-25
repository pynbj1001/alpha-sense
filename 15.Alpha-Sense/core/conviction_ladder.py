#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
信念升级阶梯 — 6 级从信号到重仓的系统化路径

概率门槛驱动，每一步有明确的行动指引和检查清单。
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import CONVICTION_LADDER, CONVICTION_LOG_FILE, DATA_DIR


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class UpgradeEvent:
    """信念阶梯升级事件"""
    ticker: str
    from_level: str
    to_level: str
    old_prob: float
    new_prob: float
    reason: str
    checklist_answers: list[str]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# 持久化
# ---------------------------------------------------------------------------

def _load_log() -> list[dict]:
    if not CONVICTION_LOG_FILE.exists():
        return []
    try:
        return json.loads(CONVICTION_LOG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_log(log: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONVICTION_LOG_FILE.write_text(
        json.dumps(log, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 核心逻辑
# ---------------------------------------------------------------------------

def get_stage(probability: float) -> dict:
    """根据概率返回当前所处阶梯"""
    for stage in reversed(CONVICTION_LADDER):
        if probability >= stage["prob_min"]:
            return stage
    return CONVICTION_LADDER[0]


def check_upgrade(ticker: str, old_prob: float, new_prob: float) -> dict | None:
    """
    检查概率变化是否跨越了阶梯门槛

    返回:
        升级建议 dict 或 None
    """
    old_stage = get_stage(old_prob)
    new_stage = get_stage(new_prob)

    if new_stage["level"] != old_stage["level"] and new_prob > old_prob:
        return {
            "ticker": ticker,
            "from_level": old_stage["level"],
            "from_name": old_stage["name"],
            "to_level": new_stage["level"],
            "to_name": new_stage["name"],
            "old_prob": old_prob,
            "new_prob": new_prob,
            "suggested_position": new_stage["position"],
            "suggested_action": new_stage["action"],
            "checklist": generate_entry_checklist(ticker, new_stage["level"]),
        }
    return None


def generate_entry_checklist(ticker: str, target_level: str) -> list[str]:
    """
    生成上车检查单 — 每次升级必须回答的 3 个问题
    """
    return [
        f"1. 与上次评估相比，什么新证据将 {ticker} 的概率推升至 {target_level}？",
        f"2. 如果 {ticker} 的论点是错的，最可能因为什么原因？",
        f"3. 市场对 {ticker} 当前定价了多少这个预期？（非共识程度如何？）",
    ]


def log_upgrade(
    ticker: str,
    from_level: str,
    to_level: str,
    old_prob: float,
    new_prob: float,
    reason: str,
    checklist_answers: list[str] | None = None,
) -> None:
    """记录升级事件"""
    event = UpgradeEvent(
        ticker=ticker,
        from_level=from_level,
        to_level=to_level,
        old_prob=old_prob,
        new_prob=new_prob,
        reason=reason,
        checklist_answers=checklist_answers or [],
    )
    log = _load_log()
    log.append(asdict(event))
    _save_log(log)


def get_all_positions(tracker_states: list) -> list[dict]:
    """
    获取所有标的的当前阶梯位置

    参数:
        tracker_states: TrackerState 列表或 dict 列表

    返回:
        [{"ticker": "NVDA", "probability": 0.68, "stage": {...}, ...}, ...]
    """
    positions = []
    for state in tracker_states:
        if isinstance(state, dict):
            ticker = state.get("ticker", "")
            prob = state.get("current_probability", 0.5)
            thesis = state.get("thesis", "")
            active = state.get("active", True)
        else:
            ticker = state.ticker
            prob = state.current_probability
            thesis = state.thesis
            active = state.active

        if not active:
            continue

        stage = get_stage(prob)
        positions.append({
            "ticker": ticker,
            "probability": prob,
            "stage_level": stage["level"],
            "stage_name": stage["name"],
            "position": stage["position"],
            "action": stage["action"],
            "color": stage["color"],
            "thesis": thesis,
        })

    return sorted(positions, key=lambda x: x["probability"], reverse=True)


def get_pending_upgrades(tracker_states: list) -> list[dict]:
    """找出概率已过门槛但尚未升级的标的"""
    log = _load_log()
    # 获取每个标的最后一次升级记录
    last_upgrades = {}
    for entry in log:
        t = entry.get("ticker", "")
        last_upgrades[t] = entry.get("to_level", "L0")

    pending = []
    positions = get_all_positions(tracker_states)
    for pos in positions:
        logged_level = last_upgrades.get(pos["ticker"], "L0")
        current_level = pos["stage_level"]
        if current_level != logged_level and current_level != "L0":
            pos["last_logged_level"] = logged_level
            pos["checklist"] = generate_entry_checklist(pos["ticker"], current_level)
            pending.append(pos)

    return pending


def get_upgrade_history() -> list[dict]:
    """返回升级日志"""
    return _load_log()
