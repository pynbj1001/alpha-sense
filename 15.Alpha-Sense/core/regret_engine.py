#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
遗憾复盘引擎 — 系统化追踪"看对了但没买/没买够"的案例

五类根因分析 + 防错规则生成 + 统计。
"""

from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import REGRETS_FILE, DATA_DIR, REGRET_ROOT_CAUSES, LESSONS_PATH

# 可选 yfinance
try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class RegretCase:
    """一条遗憾案例"""
    id: str
    ticker: str
    company_name: str
    first_noticed: str     # 最早感知日期 YYYY-MM-DD
    price_at_notice: float
    current_price: float
    missed_return_pct: float
    root_cause: str        # key from REGRET_ROOT_CAUSES
    narrative: str         # 故事描述
    lesson: str
    prevention_rule: str
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# 持久化
# ---------------------------------------------------------------------------

def _load_regrets() -> list[dict]:
    if not REGRETS_FILE.exists():
        return []
    try:
        return json.loads(REGRETS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_regrets(regrets: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REGRETS_FILE.write_text(
        json.dumps(regrets, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 价格获取
# ---------------------------------------------------------------------------

def _fetch_current_price(ticker: str) -> float | None:
    """获取当前价格"""
    if not HAS_YF:
        return None
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        return float(info.get("lastPrice", 0) or info.get("last_price", 0))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 核心 API
# ---------------------------------------------------------------------------

def add_regret(
    ticker: str,
    company_name: str,
    first_noticed: str,
    price_at_notice: float,
    root_cause: str,
    narrative: str,
    current_price: float | None = None,
) -> RegretCase:
    """
    创建遗憾案例

    参数:
        ticker: 标的代码
        company_name: 公司名
        first_noticed: 最早感知日期 (YYYY-MM-DD)
        price_at_notice: 当时价格
        root_cause: 根因 key (no_capture / no_track / no_research / no_position / too_light)
        narrative: 故事描述
        current_price: 当前价格（如不提供则自动获取）

    返回:
        RegretCase 对象
    """
    if current_price is None:
        current_price = _fetch_current_price(ticker) or 0.0

    missed = ((current_price - price_at_notice) / price_at_notice * 100) if price_at_notice > 0 else 0.0

    # 生成教训和防错规则
    lesson = _generate_lesson(ticker, company_name, root_cause, narrative, missed)
    rule = _generate_prevention_rule(root_cause, ticker)

    case = RegretCase(
        id=str(uuid.uuid4())[:8],
        ticker=ticker,
        company_name=company_name,
        first_noticed=first_noticed,
        price_at_notice=price_at_notice,
        current_price=current_price,
        missed_return_pct=round(missed, 1),
        root_cause=root_cause,
        narrative=narrative,
        lesson=lesson,
        prevention_rule=rule,
    )

    # 保存
    regrets = _load_regrets()
    regrets.append(asdict(case))
    _save_regrets(regrets)

    # 追加到 lessons.md
    _append_to_lessons(case)

    return case


def _generate_lesson(ticker: str, name: str, root_cause: str, narrative: str, missed_pct: float) -> str:
    """生成教训文本"""
    cause_desc = REGRET_ROOT_CAUSES.get(root_cause, root_cause)
    return (
        f"在 {name}({ticker}) 上错过了 {missed_pct:+.1f}% 的涨幅。"
        f"根本原因：{cause_desc}。"
        f"背景：{narrative[:100]}"
    )


def _generate_prevention_rule(root_cause: str, ticker: str) -> str:
    """根据根因生成防错规则"""
    rules = {
        "no_capture": "任何引起注意的产品/技术/新闻，立即用 @信号 指令捕获，不超过当天",
        "no_track": "信号捕获后 3 天内必须加入贝叶斯追踪器，设置初始先验",
        "no_research": "追踪标的概率 ≥60% 时，必须在一周内启动 @估值 或 @护城河 中度研究",
        "no_position": "L5 CIO备忘录完成后，如安全边际充足，48小时内必须建立至少1%试探仓",
        "too_light": "当贝叶斯概率 ≥75% 且3+框架共识时，仓位应升至目标区间，不低于10%",
    }
    return rules.get(root_cause, f"复盘 {ticker} 并制定明确的行动SOP")


def _append_to_lessons(case: RegretCase) -> None:
    """追加遗憾教训到 tasks/lessons.md"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        line = (
            f"\n- ❌ `[{today}]` [遗憾] {case.company_name}({case.ticker}) "
            f"错过 {case.missed_return_pct:+.1f}% | "
            f"根因：{REGRET_ROOT_CAUSES.get(case.root_cause, case.root_cause)} | "
            f"防错规则：{case.prevention_rule}\n"
        )
        if LESSONS_PATH.exists():
            with open(LESSONS_PATH, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception:
        pass  # 非关键操作


def list_regrets() -> list[dict]:
    """列出所有遗憾案例"""
    return _load_regrets()


def get_statistics() -> dict:
    """遗憾统计"""
    regrets = _load_regrets()
    stats = {
        "total": len(regrets),
        "total_missed_return": 0.0,
        "by_root_cause": {},
    }
    for r in regrets:
        rc = r.get("root_cause", "unknown")
        stats["by_root_cause"][rc] = stats["by_root_cause"].get(rc, 0) + 1
        stats["total_missed_return"] += r.get("missed_return_pct", 0)

    stats["avg_missed_return"] = (
        stats["total_missed_return"] / stats["total"] if stats["total"] > 0 else 0
    )
    return stats
