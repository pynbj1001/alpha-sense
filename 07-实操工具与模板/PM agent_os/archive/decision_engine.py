"""
Decision Brief 决策生成模块
─────────────────────────────────
核心职责：
每一次可能进入交易的行为，都必须先生成一份 Decision Brief。
它不是交易指令，而是一份判断说明。

Decision Brief 明确写下：
- 交易者在关注什么标的
- 现在倾向于哪个方向
- 对这个判断的置信度有多高
- 这个判断是否允许在没有人工确认的情况下被执行

只有当这份判断被系统接受、风险条件被确认，执行模块才有资格接手。
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .llm_client import DeepSeekClient
from .models import Judgment, DecisionBrief

logger = logging.getLogger("agent_os.decision")

SYSTEM_PROMPT_DECISION = """你是一位严格的决策审查官。交易者想要进行一笔交易，你需要帮助他把判断写清楚，并生成一份结构化的 Decision Brief。

你的核心原则：
1. 逻辑必须清晰 — 如果交易者的理由含混不清，你要追问
2. 置信度必须诚实 — 不允许模糊的"看好"或"看空"
3. 风险必须量化 — 止损位和仓位必须明确
4. 对齐判断 — 确保这次交易与已有判断一致

输出要求（JSON 格式）：
{
  "decision_quality": "high/medium/low",
  "rationale_clear": true/false,
  "rationale_assessment": "对交易理由的评估",
  "suggested_entry_price": null,
  "suggested_stop_loss": null,
  "suggested_take_profit": null,
  "suggested_position_pct": 0.0,
  "requires_manual_confirm": true,
  "auto_execute_eligible": false,
  "risk_warnings": ["风险提示1", ...],
  "questions_for_trader": ["需要回答的问题1", ...],
  "final_assessment": "最终评估和建议"
}"""


class DecisionEngine:
    """决策生成引擎"""

    def __init__(self, llm: DeepSeekClient, risk_config: Any = None):
        self.llm = llm
        self.risk_config = risk_config
        self.pending_decisions: List[DecisionBrief] = []
        self.completed_decisions: List[DecisionBrief] = []

    def create_decision_brief(self, trader: str, judgment: Judgment,
                                trade_idea: str,
                                entry_price: Optional[float] = None,
                                stop_loss: Optional[float] = None,
                                take_profit: Optional[float] = None,
                                position_pct: float = 0.05) -> DecisionBrief:
        """
        创建 Decision Brief
        
        交易者必须先把想法写清楚，系统才会进入审查流程。
        """
        # 构建 Decision Brief 基础
        brief = DecisionBrief(
            judgment_id=judgment.id,
            trader=trader,
            symbol=judgment.symbol,
            symbol_name=judgment.symbol_name,
            direction=judgment.direction,
            confidence=judgment.confidence,
            rationale=trade_idea,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size_pct=position_pct,
            status="draft",
        )

        # 使用 AI 审查
        assessment = self._ai_review(brief, judgment)

        # 更新 Brief
        brief.risk_check_result = assessment.get("final_assessment", "")
        questions = assessment.get("questions_for_trader", [])

        # 判断是否可以自动执行
        if (assessment.get("auto_execute_eligible", False)
                and assessment.get("decision_quality") == "high"
                and judgment.confidence >= (self.risk_config.confidence_threshold_auto
                                            if self.risk_config else 0.85)):
            brief.requires_manual_confirm = False
        else:
            brief.requires_manual_confirm = True

        # 应用 AI 建议的参数
        if assessment.get("suggested_stop_loss") and not stop_loss:
            brief.stop_loss = assessment["suggested_stop_loss"]
        if assessment.get("suggested_take_profit") and not take_profit:
            brief.take_profit = assessment["suggested_take_profit"]
        if assessment.get("suggested_position_pct") and position_pct == 0.05:
            brief.position_size_pct = assessment["suggested_position_pct"]

        brief.status = "pending"
        self.pending_decisions.append(brief)

        logger.info(
            f"[决策] Decision Brief 已生成: {brief.id} | "
            f"{brief.symbol} {brief.direction} | "
            f"需人工确认: {brief.requires_manual_confirm}"
        )

        return brief

    def _ai_review(self, brief: DecisionBrief, judgment: Judgment) -> Dict[str, Any]:
        """AI 审查决策"""
        user_prompt = (
            f"【交易者】{brief.trader}\n\n"
            f"【关联判断】\n"
            f"  判断ID: {judgment.id}\n"
            f"  标的: {judgment.symbol} ({judgment.symbol_name})\n"
            f"  方向: {judgment.direction}\n"
            f"  核心逻辑: {judgment.thesis}\n"
            f"  置信度: {judgment.confidence}\n"
            f"  关键变量: {', '.join(judgment.key_variables)}\n"
            f"  证伪条件: {', '.join(judgment.invalidation_conditions)}\n"
            f"  当前状态: {judgment.status}\n\n"
            f"【交易想法】\n{brief.rationale}\n\n"
            f"【拟定参数】\n"
            f"  入场价: {brief.entry_price or '未指定'}\n"
            f"  止损价: {brief.stop_loss or '未指定'}\n"
            f"  止盈价: {brief.take_profit or '未指定'}\n"
            f"  仓位占比: {brief.position_size_pct:.1%}\n"
        )

        result = self.llm.analyze_json(SYSTEM_PROMPT_DECISION, user_prompt)
        return result

    def approve_decision(self, decision_id: str) -> Optional[DecisionBrief]:
        """人工批准决策"""
        for d in self.pending_decisions:
            if d.id == decision_id and d.status == "pending":
                d.status = "approved"
                d.approved_at = datetime.now().isoformat()
                logger.info(f"[决策] ✅ Decision {d.id} 已批准")
                return d
        logger.warning(f"[决策] 未找到待审批的决策: {decision_id}")
        return None

    def reject_decision(self, decision_id: str, reason: str = "") -> Optional[DecisionBrief]:
        """拒绝决策"""
        for d in self.pending_decisions:
            if d.id == decision_id and d.status == "pending":
                d.status = "rejected"
                d.rejected_reason = reason
                self.completed_decisions.append(d)
                self.pending_decisions.remove(d)
                logger.info(f"[决策] ❌ Decision {d.id} 已拒绝: {reason}")
                return d
        return None

    def get_pending_decisions(self) -> List[DecisionBrief]:
        """获取所有待审批决策"""
        return [d for d in self.pending_decisions if d.status == "pending"]

    def format_decision_brief(self, brief: DecisionBrief, assessment: Dict = None) -> str:
        """格式化 Decision Brief 为可读文档"""
        status_icons = {
            "draft": "📝", "pending": "⏳", "approved": "✅",
            "rejected": "❌", "executed": "🔄", "cancelled": "🚫",
        }
        icon = status_icons.get(brief.status, "❓")

        lines = [
            "═" * 55,
            f"  {icon} DECISION BRIEF | {brief.id}",
            "═" * 55,
            f"  交易者: {brief.trader}",
            f"  时间:   {brief.created_at}",
            f"  状态:   {brief.status.upper()}",
            "─" * 55,
            f"  标的:     {brief.symbol} ({brief.symbol_name})",
            f"  方向:     {brief.direction}",
            f"  置信度:   {brief.confidence:.0%}",
            f"  入场价:   {brief.entry_price or '待定'}",
            f"  止损价:   {brief.stop_loss or '待定'}",
            f"  止盈价:   {brief.take_profit or '待定'}",
            f"  仓位占比: {brief.position_size_pct:.1%}",
            "─" * 55,
            f"  决策理由:",
            f"  {brief.rationale}",
            "─" * 55,
            f"  需人工确认: {'是' if brief.requires_manual_confirm else '否（满足自动执行条件）'}",
            f"  关联判断:   {brief.judgment_id}",
            "─" * 55,
            f"  风控审查:",
            f"  {brief.risk_check_result}",
            "═" * 55,
        ]
        return "\n".join(lines)

    def reset_daily(self):
        """每日重置"""
        # 将未完成的 pending 移到 completed 并标注取消
        for d in self.pending_decisions:
            if d.status == "pending":
                d.status = "cancelled"
                d.rejected_reason = "交易日结束自动取消"
                self.completed_decisions.append(d)
        self.pending_decisions.clear()
