#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
信号捕获引擎 — 一句话 → 结构化信号 → 入贝叶斯追踪器

核心职责：
1. 解析用户输入，提取关键实体
2. 匹配技术革命 5 阶段催化剂
3. 搜索关联标的
4. 生成论点草稿 + 先验概率
5. 推入贝叶斯追踪器
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

# 让 Python 找到 config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (
    SIGNALS_FILE,
    DATA_DIR,
    KEYWORD_TICKER_MAP,
    SIGNAL_TYPES,
    TECH_CATALYSTS,
    TECH_STAGES,
    TRACKER_DIR,
    WATCHLIST_PATH,
)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class InvestmentSignal:
    """一条投资信号"""
    id: str
    raw_input: str
    signal_type: str
    matched_catalysts: list[str] = field(default_factory=list)
    tech_stage: str = ""
    related_tickers: list[str] = field(default_factory=list)
    thesis_draft: str = ""
    initial_prior: float = 0.50
    created_at: str = ""
    status: str = "new"  # new / tracking / researching / positioned / closed

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# 信号存储
# ---------------------------------------------------------------------------

def _load_signals() -> list[dict]:
    """加载所有信号"""
    if not SIGNALS_FILE.exists():
        return []
    try:
        data = json.loads(SIGNALS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_signals(signals: list[dict]) -> None:
    """保存信号列表"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SIGNALS_FILE.write_text(
        json.dumps(signals, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 关键词匹配引擎
# ---------------------------------------------------------------------------

def match_tickers(text: str) -> list[str]:
    """从文本中匹配关联标的"""
    text_lower = text.lower()
    matched = set()

    # 1. 本地关键词库匹配
    for keyword, ticker in KEYWORD_TICKER_MAP.items():
        if keyword.lower() in text_lower:
            matched.add(ticker)

    # 2. 从 watchlist 匹配
    if WATCHLIST_PATH.exists():
        try:
            wl = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
            for idea in wl.get("ideas", []):
                if not idea.get("active", True):
                    continue
                keywords = idea.get("keywords", []) + idea.get("industry_keywords", [])
                for kw in keywords:
                    if kw.lower() in text_lower:
                        symbol = idea.get("symbol", "")
                        if symbol:
                            matched.add(symbol)
                            break
        except Exception:
            pass

    return sorted(matched)


def match_catalysts(text: str) -> list[str]:
    """匹配技术革命催化剂"""
    matched = []
    catalyst_keywords = {
        "技术可行性验证（10倍性能飞跃）": [
            "突破", "性能", "10倍", "飞跃", "革命", "颠覆", "首次", "创新",
            "breakthrough", "10x", "revolution", "leap",
        ],
        "规模化量产能力建成": [
            "量产", "产能", "工厂", "投产", "扩产", "产线", "规模化",
            "mass production", "capacity", "factory", "ramp",
        ],
        "业绩持续超预期（连续beat）": [
            "超预期", "beat", "超出", "增长", "营收", "利润", "翻倍",
            "earnings", "revenue", "profit", "surpass", "exceed",
        ],
    }
    text_lower = text.lower()
    for catalyst, keywords in catalyst_keywords.items():
        if any(kw.lower() in text_lower for kw in keywords):
            matched.append(catalyst)
    return matched


def guess_tech_stage(text: str) -> str:
    """推测技术革命阶段"""
    stage_keywords = {
        "irruption": ["新兴", "早期", "VC", "startup", "萌芽", "爆发", "首次"],
        "frenzy": ["泡沫", "疯狂", "炒作", "估值过高", "FOMO", "狂热", "热炒"],
        "turning": ["崩盘", "回调", "破裂", "出清", "泡沫破"],
        "synergy": ["普及", "规模", "盈利", "黄金", "协同", "大规模部署"],
        "maturity": ["成熟", "饱和", "放缓", "红利", "存量"],
    }
    text_lower = text.lower()
    for stage, keywords in stage_keywords.items():
        if any(kw.lower() in text_lower for kw in keywords):
            return stage
    return ""


def suggest_prior(signal_type: str, catalyst_count: int, ticker_count: int) -> float:
    """根据信号类型和匹配度建议先验概率"""
    base = 0.50
    # 产品直觉类信号基线更高（你用过的产品更可靠）
    type_bonus = {
        "product_intuition": 0.05,
        "reading_insight": 0.03,
        "data_anomaly": 0.04,
        "social_signal": 0.02,
        "framework_deduction": 0.05,
    }
    base += type_bonus.get(signal_type, 0)
    # 催化剂匹配越多，先验越高
    base += min(catalyst_count * 0.03, 0.09)
    # 多个标的关联 = 信号更广泛
    if ticker_count >= 3:
        base += 0.02
    return min(base, 0.65)


def generate_thesis(raw_input: str, tickers: list[str], catalysts: list[str]) -> str:
    """生成论点草稿"""
    ticker_str = " / ".join(tickers[:3]) if tickers else "待确定标的"
    catalyst_str = "；".join(catalysts) if catalysts else "待识别催化剂"
    return f"信号来源：{raw_input[:80]}... → 关联标的 {ticker_str}，匹配催化剂：{catalyst_str}"


# ---------------------------------------------------------------------------
# 核心 API
# ---------------------------------------------------------------------------

def capture_signal(
    raw_input: str,
    signal_type: str = "reading_insight",
) -> InvestmentSignal:
    """
    核心入口：一句话 → 结构化投资信号

    参数:
        raw_input: 用户原始输入
        signal_type: 信号类型 key

    返回:
        InvestmentSignal 结构化信号对象
    """
    tickers = match_tickers(raw_input)
    catalysts = match_catalysts(raw_input)
    stage = guess_tech_stage(raw_input)
    prior = suggest_prior(signal_type, len(catalysts), len(tickers))
    thesis = generate_thesis(raw_input, tickers, catalysts)

    signal = InvestmentSignal(
        id=str(uuid.uuid4())[:8],
        raw_input=raw_input,
        signal_type=signal_type,
        matched_catalysts=catalysts,
        tech_stage=stage,
        related_tickers=tickers,
        thesis_draft=thesis,
        initial_prior=prior,
    )

    # 持久化
    all_signals = _load_signals()
    all_signals.append(asdict(signal))
    _save_signals(all_signals)

    return signal


def push_to_tracker(signal: InvestmentSignal, ticker: str, thesis: str | None = None, prior: float | None = None) -> bool:
    """
    将信号推入贝叶斯追踪器

    参数:
        signal: 信号对象
        ticker: 目标标的
        thesis: 可选覆盖论点
        prior: 可选覆盖先验

    返回:
        是否成功
    """
    try:
        sys.path.insert(0, str(TRACKER_DIR))
        from bayesian_engine import TrackerState, TrackerStore

        store = TrackerStore(TRACKER_DIR / "data")
        existing = store.load(ticker.upper())
        if existing and existing.active:
            return False  # 已存在

        state = TrackerState(
            ticker=ticker.upper(),
            thesis=thesis or signal.thesis_draft,
            target=f"信号捕获 → {signal.signal_type}",
            prior=prior or signal.initial_prior,
            current_probability=prior or signal.initial_prior,
            tags=signal.matched_catalysts[:3],
        )
        store.save(state)

        # 更新信号状态
        update_signal_status(signal.id, "tracking")
        return True
    except Exception:
        return False


def update_signal_status(signal_id: str, new_status: str) -> bool:
    """更新信号状态"""
    all_signals = _load_signals()
    for s in all_signals:
        if s.get("id") == signal_id:
            s["status"] = new_status
            _save_signals(all_signals)
            return True
    return False


def list_signals(status: str | None = None) -> list[dict]:
    """列出信号（可按状态筛选）"""
    all_signals = _load_signals()
    if status:
        return [s for s in all_signals if s.get("status") == status]
    return all_signals


def get_signal_stats() -> dict:
    """信号统计摘要"""
    all_signals = _load_signals()
    stats = {"total": len(all_signals)}
    for s in all_signals:
        st = s.get("status", "unknown")
        stats[st] = stats.get(st, 0) + 1
    # 按信号类型统计
    type_counts = {}
    for s in all_signals:
        t = s.get("signal_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    stats["by_type"] = type_counts
    return stats
