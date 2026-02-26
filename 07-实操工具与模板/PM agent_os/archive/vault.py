"""
盘后复盘与 Vault 存储模块
─────────────────────────────────
收盘后，才是真正决定长期收益的时刻。

每一天的判断、执行、结果，都必须被完整地保存下来。
不是为了回看收益，而是为了回看：
- 当时的判断环境是什么
- 当时你为什么会这么想
- 以及哪些错误，是可以避免的

这些内容会进入一个长期保存的 Vault，
可以被回放、被复盘、被重新理解。
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .llm_client import DeepSeekClient
from .models import (
    Judgment, DecisionBrief, TradeRecord, RiskAlert, DailySnapshot
)

logger = logging.getLogger("agent_os.vault")

SYSTEM_PROMPT_REVIEW = """你是一位资深的交易复盘分析师。你的职责是对交易者一天的工作进行客观、深入的复盘分析。

复盘不是庆功，也不是批判。它是对认知过程的诚实回顾。

你需要分析：
1. 今日的判断质量 — 判断是否清晰、逻辑是否自洽
2. 执行一致性 — 交易执行是否与判断一致，是否偏离了计划
3. 风控表现 — 是否在该止损时止损，是否控制了冲动
4. 情绪管理 — 是否有被情绪驱动的决策
5. 可改进之处 — 具体的、可操作的改进建议

输出要求（JSON 格式）：
{
  "date": "日期",
  "overall_grade": "A/B/C/D/F",
  "judgment_quality": {
    "score": 0-10,
    "analysis": "分析"
  },
  "execution_consistency": {
    "score": 0-10,
    "analysis": "分析"
  },
  "risk_management": {
    "score": 0-10,
    "analysis": "分析"
  },
  "emotional_control": {
    "score": 0-10,
    "analysis": "分析"
  },
  "key_lessons": ["教训1", "教训2"],
  "mistakes_to_avoid": ["错误1", "错误2"],
  "positive_highlights": ["做得好的地方"],
  "tomorrow_focus": "明天应该重点关注什么",
  "detailed_review": "完整的复盘叙述（3-5段）"
}"""


class PostMarketVault:
    """盘后复盘与长期存储"""

    def __init__(self, llm: DeepSeekClient, storage_dir: str = "vault"):
        self.llm = llm
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def generate_daily_review(self, snapshot: DailySnapshot) -> Dict[str, Any]:
        """
        生成每日复盘报告
        
        将一天的所有判断、决策、交易、告警汇总后交给 AI 分析
        """
        user_prompt = self._build_review_prompt(snapshot)

        logger.info(f"[复盘] 正在生成 {snapshot.date} 每日复盘...")
        result = self.llm.analyze_json(SYSTEM_PROMPT_REVIEW, user_prompt)
        logger.info(f"[复盘] 复盘生成完成，评级: {result.get('overall_grade', '?')}")
        return result

    def _build_review_prompt(self, snapshot: DailySnapshot) -> str:
        """构建复盘提示词"""
        parts = [
            f"【日期】{snapshot.date}\n",
            f"【盘前简报】\n{snapshot.pre_market_briefing}\n",
        ]

        # 判断
        if snapshot.morning_judgments:
            parts.append("【今日判断】")
            for j in snapshot.morning_judgments:
                parts.append(
                    f"  [{j.get('id', '?')}] {j.get('symbol', '?')} | "
                    f"{j.get('direction', '?')} | 置信度 {j.get('confidence', '?')} | "
                    f"逻辑: {j.get('thesis', '?')} | 最终状态: {j.get('status', '?')}"
                )

        # 边界条件
        if snapshot.boundary_conditions:
            parts.append("\n【边界条件】")
            for b in snapshot.boundary_conditions:
                parts.append(f"  🚫 {b}")

        # 告警
        if snapshot.intraday_alerts:
            parts.append(f"\n【盘中告警 ({len(snapshot.intraday_alerts)} 条)】")
            for a in snapshot.intraday_alerts[:10]:
                parts.append(f"  ⚠ {a.get('alert_type', '?')}: {a.get('message', '?')}")

        # 决策
        if snapshot.decisions:
            parts.append(f"\n【决策 ({len(snapshot.decisions)} 份)】")
            for d in snapshot.decisions:
                parts.append(
                    f"  [{d.get('id', '?')}] {d.get('symbol', '?')} {d.get('direction', '?')} | "
                    f"状态: {d.get('status', '?')} | 理由: {d.get('rationale', '?')[:80]}"
                )

        # 交易
        if snapshot.trades:
            parts.append(f"\n【交易 ({len(snapshot.trades)} 笔)】")
            total_pnl = 0
            for t in snapshot.trades:
                pnl = t.get('pnl', 0) or 0
                total_pnl += pnl
                parts.append(
                    f"  {t.get('symbol', '?')} {t.get('direction', '?')} | "
                    f"入场 {t.get('entry_price', '?')} → 出场 {t.get('exit_price', '?')} | "
                    f"盈亏 {pnl:+.2f} | 原因: {t.get('exit_reason', '未平仓')}"
                )
            parts.append(f"  总盈亏: {total_pnl:+.2f}")
        else:
            parts.append("\n【交易】无交易")

        # 盈亏
        parts.append(f"\n【当日盈亏】{snapshot.daily_pnl:+.2f} ({snapshot.daily_pnl_pct:+.2%})")

        return "\n".join(parts)

    def save_snapshot(self, snapshot: DailySnapshot, review: Dict[str, Any] = None):
        """
        将每日快照存入 Vault
        
        Vault 结构：
        vault/
          2026/
            02/
              2026-02-08.json
              2026-02-08_review.json
        """
        date = snapshot.date
        year = date[:4]
        month = date[5:7]

        # 创建目录
        day_dir = self.storage_dir / year / month
        day_dir.mkdir(parents=True, exist_ok=True)

        # 保存快照
        snapshot_path = day_dir / f"{date}.json"
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"[Vault] 快照已保存: {snapshot_path}")

        # 保存复盘报告
        if review:
            review_path = day_dir / f"{date}_review.json"
            with open(review_path, "w", encoding="utf-8") as f:
                json.dump(review, f, ensure_ascii=False, indent=2)
            logger.info(f"[Vault] 复盘报告已保存: {review_path}")

    def load_snapshot(self, date: str) -> Optional[DailySnapshot]:
        """从 Vault 加载指定日期的快照"""
        year = date[:4]
        month = date[5:7]
        path = self.storage_dir / year / month / f"{date}.json"

        if not path.exists():
            logger.info(f"[Vault] 未找到 {date} 的快照")
            return None

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        snapshot = DailySnapshot()
        for k, v in data.items():
            if hasattr(snapshot, k):
                setattr(snapshot, k, v)
        return snapshot

    def load_review(self, date: str) -> Optional[Dict[str, Any]]:
        """从 Vault 加载指定日期的复盘报告"""
        year = date[:4]
        month = date[5:7]
        path = self.storage_dir / year / month / f"{date}_review.json"

        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_recent_snapshots(self, days: int = 7) -> List[str]:
        """获取最近 N 天的快照日期列表"""
        dates = []
        for root, dirs, files in os.walk(self.storage_dir):
            for f in files:
                if f.endswith(".json") and not f.endswith("_review.json"):
                    dates.append(f.replace(".json", ""))
        dates.sort(reverse=True)
        return dates[:days]

    def format_review_report(self, review: Dict[str, Any]) -> str:
        """格式化复盘报告"""
        grade_colors = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🟠", "F": "🔴"}
        grade = review.get("overall_grade", "?")
        icon = grade_colors.get(grade, "⚪")

        lines = [
            "═" * 60,
            f"  📖 每日复盘报告 | {review.get('date', '?')}",
            f"  {icon} 综合评级: {grade}",
            "═" * 60,
        ]

        # 四维评分
        dims = [
            ("判断质量", "judgment_quality"),
            ("执行一致性", "execution_consistency"),
            ("风险管理", "risk_management"),
            ("情绪控制", "emotional_control"),
        ]
        for label, key in dims:
            dim = review.get(key, {})
            score = dim.get("score", 0)
            bar = "█" * score + "░" * (10 - score)
            lines.append(f"  {label}: [{bar}] {score}/10")
            lines.append(f"    {dim.get('analysis', '无')}")

        # 教训
        lines.append("\n  📌 关键教训:")
        for lesson in review.get("key_lessons", []):
            lines.append(f"    • {lesson}")

        # 应避免的错误
        lines.append("\n  ⛔ 应避免的错误:")
        for mistake in review.get("mistakes_to_avoid", []):
            lines.append(f"    • {mistake}")

        # 做得好的
        lines.append("\n  ✨ 做得好的地方:")
        for highlight in review.get("positive_highlights", []):
            lines.append(f"    • {highlight}")

        # 明日关注
        lines.append(f"\n  🔮 明日重点: {review.get('tomorrow_focus', '暂无')}")

        # 详细复盘
        lines.append("\n" + "─" * 60)
        lines.append("  📝 详细复盘:")
        lines.append(f"  {review.get('detailed_review', '暂无')}")

        lines.append("═" * 60)
        return "\n".join(lines)

    def search_vault(self, keyword: str) -> List[Dict[str, Any]]:
        """在 Vault 中搜索包含关键词的记录"""
        results = []
        for root, dirs, files in os.walk(self.storage_dir):
            for f in files:
                if not f.endswith(".json"):
                    continue
                fpath = Path(root) / f
                try:
                    with open(fpath, "r", encoding="utf-8") as fp:
                        content = fp.read()
                    if keyword.lower() in content.lower():
                        data = json.loads(content)
                        results.append({
                            "file": str(fpath),
                            "date": f.replace(".json", "").replace("_review", ""),
                            "type": "review" if "_review" in f else "snapshot",
                            "preview": content[:200],
                        })
                except Exception:
                    pass
        return results
