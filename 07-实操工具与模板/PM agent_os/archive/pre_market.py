"""
盘前研判模块 (Pre-Market Analyst)
─────────────────────────────────
核心职责：
1. 扫描隔夜市场变化
2. 逐一检查昨日判断是否仍然成立
3. 生成今日边界条件（什么情况下不应该动手）
4. 输出「晨间研判简报」
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from .llm_client import DeepSeekClient
from .models import Judgment, DailySnapshot

logger = logging.getLogger("agent_os.premarket")

# ── 系统提示词 ──

SYSTEM_PROMPT_BRIEFING = """你是一位资深基金经理的盘前助手。你的职责不是推荐交易机会，而是帮助基金经理在开盘前完成认知校准。

你需要完成以下工作：
1. 分析隔夜市场的关键变化（美股、港股、大宗商品、汇率、重要事件）
2. 识别哪些变量已经发生了变化
3. 判断这些变化对已有判断的影响
4. 明确今日的边界条件：在什么情况下，不应该采取行动

输出要求（JSON 格式）：
{
  "market_overview": "隔夜市场概况（3-5句话）",
  "key_changes": ["变化1", "变化2", ...],
  "risk_events": ["风险事件1", ...],
  "boundary_conditions": ["今日不应出手的条件1", "条件2", ...],
  "sentiment": "谨慎/中性/积极",
  "briefing_summary": "一段话总结今日开盘前的整体判断环境"
}"""

SYSTEM_PROMPT_JUDGMENT_CHECK = """你是一位严格的判断审查员。给定一个交易判断和当前的市场环境信息，你需要评估这个判断是否仍然成立。

你的评估必须诚实且严格。不要因为判断者有偏好就迎合。

评估维度：
1. 判断所依赖的关键变量是否仍然成立
2. 是否出现了原本设定的证伪条件
3. 判断的置信度是否应该调整

输出要求（JSON 格式）：
{
  "judgment_id": "判断ID",
  "still_valid": true/false,
  "new_status": "active/weakened/invalidated",
  "confidence_adjustment": 0.0,
  "reasoning": "详细分析",
  "warning_signs": ["松动迹象1", ...],
  "recommendation": "建议"
}"""


class PreMarketAnalyst:
    """盘前研判 Agent"""

    def __init__(self, llm: DeepSeekClient):
        self.llm = llm

    def generate_morning_briefing(self, market_context: str = "",
                                   previous_snapshot: Dict = None) -> Dict[str, Any]:
        """
        生成晨间研判简报
        
        Args:
            market_context: 用户提供的市场信息（隔夜动态、新闻等）
            previous_snapshot: 前一交易日快照
        """
        user_prompt_parts = []

        if market_context:
            user_prompt_parts.append(f"【用户提供的市场信息】\n{market_context}")
        else:
            user_prompt_parts.append("【注意】用户未提供具体市场数据，请基于你的知识生成一般性框架分析。")

        if previous_snapshot:
            prev_judgments = previous_snapshot.get("morning_judgments", [])
            prev_trades = previous_snapshot.get("trades", [])
            prev_lessons = previous_snapshot.get("lessons_learned", [])
            user_prompt_parts.append(
                f"【昨日信息】\n"
                f"- 昨日判断数: {len(prev_judgments)}\n"
                f"- 昨日交易数: {len(prev_trades)}\n"
                f"- 昨日教训: {prev_lessons}\n"
                f"- 昨日盈亏: {previous_snapshot.get('daily_pnl_pct', 0):.2%}"
            )

        user_prompt_parts.append(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        user_prompt = "\n\n".join(user_prompt_parts)

        logger.info("[盘前] 正在生成晨间研判简报...")
        result = self.llm.analyze_json(SYSTEM_PROMPT_BRIEFING, user_prompt)
        logger.info("[盘前] 晨间简报生成完成")
        return result

    def check_judgment(self, judgment: Judgment, market_context: str = "") -> Dict[str, Any]:
        """
        检查单个判断是否仍然成立
        
        Args:
            judgment: 待检查的判断
            market_context: 最新市场信息
        """
        user_prompt = (
            f"【待检查的判断】\n"
            f"判断ID: {judgment.id}\n"
            f"标的: {judgment.symbol} ({judgment.symbol_name})\n"
            f"方向: {judgment.direction}\n"
            f"核心逻辑: {judgment.thesis}\n"
            f"置信度: {judgment.confidence}\n"
            f"关键变量: {', '.join(judgment.key_variables)}\n"
            f"证伪条件: {', '.join(judgment.invalidation_conditions)}\n"
            f"创建时间: {judgment.created_at}\n"
            f"\n【当前市场环境】\n{market_context if market_context else '用户未提供具体数据，请基于判断逻辑自身进行审查'}"
        )

        logger.info(f"[盘前] 正在审查判断 {judgment.id}: {judgment.symbol}...")
        result = self.llm.analyze_json(SYSTEM_PROMPT_JUDGMENT_CHECK, user_prompt)
        return result

    def check_all_judgments(self, judgments: List[Judgment],
                            market_context: str = "") -> List[Dict[str, Any]]:
        """批量检查所有活跃判断"""
        results = []
        for j in judgments:
            if j.status in ("active", "weakened"):
                result = self.check_judgment(j, market_context)
                results.append(result)
        return results

    def format_briefing_report(self, briefing: Dict[str, Any],
                                judgment_checks: List[Dict] = None) -> str:
        """将研判结果格式化为可读报告"""
        lines = [
            "═" * 60,
            "         📋 盘前研判简报",
            f"         {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "═" * 60,
            "",
            "▎市场概况",
            f"  {briefing.get('market_overview', '暂无')}",
            "",
            "▎情绪判断",
            f"  {briefing.get('sentiment', '未知')}",
            "",
            "▎关键变化",
        ]
        for change in briefing.get("key_changes", []):
            lines.append(f"  • {change}")

        lines.append("")
        lines.append("▎风险事件")
        for risk in briefing.get("risk_events", []):
            lines.append(f"  ⚠ {risk}")

        lines.append("")
        lines.append("▎今日边界条件（以下情况不应出手）")
        for boundary in briefing.get("boundary_conditions", []):
            lines.append(f"  🚫 {boundary}")

        if judgment_checks:
            lines.append("")
            lines.append("─" * 60)
            lines.append("▎判断状态检查")
            for check in judgment_checks:
                status_icon = "✅" if check.get("still_valid") else "❌"
                new_status = check.get("new_status", "unknown")
                lines.append(f"  {status_icon} [{check.get('judgment_id', '?')}] → {new_status}")
                if check.get("warning_signs"):
                    for w in check["warning_signs"]:
                        lines.append(f"      ⚡ {w}")
                lines.append(f"      💬 {check.get('recommendation', '')}")

        lines.append("")
        lines.append("▎综合摘要")
        lines.append(f"  {briefing.get('briefing_summary', '暂无')}")
        lines.append("═" * 60)

        return "\n".join(lines)
