"""
风控模块 (Risk Guardian)
─────────────────────────────────
风控不是一个模块，而是一种态度。

它体现在：
- 当判断和价格出现背离时，是否允许系统替你踩刹车
- 当频率开始异常时，是否有提醒让你及时发现
- 当执行完成后，是否有人把这一切如实记录下来

它更像一个始终站在旁边、不断发问的角色：
「你现在做的，还是你早上说的那件事吗？」
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from .llm_client import DeepSeekClient
from .models import (
    Judgment, DecisionBrief, TradeRecord, RiskAlert
)
from .config import RiskConfig

logger = logging.getLogger("agent_os.risk")

SYSTEM_PROMPT_RISK = """你是一位冷静、严格的风控守护者。你的职责不是阻止交易，而是确保每一笔交易都在认知边界之内。

你始终在问一个问题：「你现在做的，还是你早上说的那件事吗？真的做到了知行合一吗？」

审查维度：
1. 一致性检查：交易是否与既有判断方向一致
2. 仓位检查：是否超过单笔/总仓位限制
3. 频率检查：短时间内交易次数是否异常
4. 情绪检查：决策理由是否充分，还是冲动驱动
5. 止损检查：是否设定了合理的止损位
6. 回撤检查：当日是否已接近回撤上限

输出要求（JSON 格式）：
{
  "passed": true/false,
  "risk_score": 0.0-1.0,
  "checks": {
    "consistency": {"passed": true/false, "detail": ""},
    "position_limit": {"passed": true/false, "detail": ""},
    "frequency": {"passed": true/false, "detail": ""},
    "emotional": {"passed": true/false, "detail": ""},
    "stop_loss": {"passed": true/false, "detail": ""},
    "drawdown": {"passed": true/false, "detail": ""}
  },
  "critical_warnings": ["关键警告"],
  "must_answer": "交易者必须回答的问题（如有）",
  "recommendation": "放行/警告放行/阻止"
}"""


class RiskGuardian:
    """
    风控守护者 — 贯穿交易全流程
    不是简单的参数校验，而是持续的认知一致性检查
    """

    def __init__(self, llm: DeepSeekClient, config: RiskConfig):
        self.llm = llm
        self.config = config
        self.daily_trades: List[TradeRecord] = []
        self.daily_pnl: float = 0.0
        self.daily_alerts: List[RiskAlert] = []
        self._trade_timestamps: List[datetime] = []

    # ─── 核心风控审查 ───

    def review_decision(self, decision: DecisionBrief,
                         judgment: Judgment,
                         current_positions: List[Dict] = None,
                         portfolio_value: float = 1000000) -> Dict[str, Any]:
        """
        对 Decision Brief 进行全面风控审查

        这是交易执行前的最后一道门。
        """
        # 规则检查（硬性条件）
        rule_issues = self._rule_based_checks(
            decision, judgment, current_positions or [], portfolio_value
        )

        # AI 深度审查（逻辑与情绪）
        ai_result = self._ai_review(decision, judgment, current_positions or [])

        # 合并结果
        all_passed = ai_result.get("passed", False) and len(rule_issues) == 0

        # 如果规则检查未通过，覆盖 AI 结果
        if rule_issues:
            all_passed = False
            ai_result["passed"] = False
            existing_warnings = ai_result.get("critical_warnings", [])
            ai_result["critical_warnings"] = existing_warnings + rule_issues

        # 更新 decision
        decision.risk_check_passed = all_passed
        decision.risk_check_result = ai_result.get("recommendation", "未知")

        # 生成告警
        if not all_passed:
            alert = RiskAlert(
                alert_type="deviation_detected",
                severity="high",
                message=f"Decision {decision.id} 未通过风控: " +
                        "; ".join(ai_result.get("critical_warnings", [])),
                related_decision_id=decision.id,
                related_judgment_id=judgment.id,
            )
            self.daily_alerts.append(alert)

        logger.info(
            f"[风控] Decision {decision.id} 审查 → "
            f"{'✅ 通过' if all_passed else '❌ 未通过'} | "
            f"风险分 {ai_result.get('risk_score', 0):.2f}"
        )

        return ai_result

    def _rule_based_checks(self, decision: DecisionBrief,
                            judgment: Judgment,
                            positions: List[Dict],
                            portfolio_value: float) -> List[str]:
        """硬性规则检查"""
        issues = []

        # 1. 判断状态检查
        if judgment.status == "invalidated":
            issues.append("关联判断已被证伪，不应继续交易")
        elif judgment.status == "expired":
            issues.append("关联判断已过期")

        # 2. 单笔仓位检查
        if decision.position_size_pct > self.config.max_single_position_pct:
            issues.append(
                f"单笔仓位 {decision.position_size_pct:.1%} 超过上限 "
                f"{self.config.max_single_position_pct:.1%}"
            )

        # 3. 止损检查
        if not decision.stop_loss:
            issues.append("未设定止损位")

        # 4. 当日交易频率检查
        now = datetime.now()
        window = timedelta(minutes=self.config.frequency_alert_window_minutes)
        recent = [t for t in self._trade_timestamps if now - t < window]
        if len(recent) >= self.config.frequency_alert_count:
            issues.append(
                f"过去 {self.config.frequency_alert_window_minutes} 分钟内已交易 "
                f"{len(recent)} 次，可能存在频率异常"
            )

        # 5. 当日回撤检查
        if portfolio_value > 0:
            daily_loss_pct = abs(self.daily_pnl / portfolio_value) if self.daily_pnl < 0 else 0
            if daily_loss_pct >= self.config.max_daily_loss_pct:
                issues.append(
                    f"当日已亏损 {daily_loss_pct:.2%}，已达到日内最大亏损限制 "
                    f"{self.config.max_daily_loss_pct:.2%}"
                )

        # 6. 方向一致性
        if (decision.direction != judgment.direction
                and judgment.direction != "neutral"):
            issues.append(
                f"交易方向 ({decision.direction}) 与判断方向 ({judgment.direction}) 不一致"
            )

        return issues

    def _ai_review(self, decision: DecisionBrief,
                    judgment: Judgment,
                    positions: List[Dict]) -> Dict[str, Any]:
        """AI 深度审查"""
        user_prompt = (
            f"【Decision Brief】\n"
            f"  ID: {decision.id}\n"
            f"  标的: {decision.symbol} ({decision.symbol_name})\n"
            f"  方向: {decision.direction}\n"
            f"  置信度: {decision.confidence:.0%}\n"
            f"  决策理由: {decision.rationale}\n"
            f"  入场价: {decision.entry_price or '未指定'}\n"
            f"  止损: {decision.stop_loss or '未指定'}\n"
            f"  止盈: {decision.take_profit or '未指定'}\n"
            f"  仓位: {decision.position_size_pct:.1%}\n\n"
            f"【关联判断】\n"
            f"  状态: {judgment.status}\n"
            f"  核心逻辑: {judgment.thesis}\n"
            f"  关键变量: {', '.join(judgment.key_variables)}\n"
            f"  证伪条件: {', '.join(judgment.invalidation_conditions)}\n\n"
            f"【当日交易信息】\n"
            f"  已执行交易数: {len(self.daily_trades)}\n"
            f"  当日盈亏: {self.daily_pnl:+.2f}\n"
            f"  当前持仓数: {len(positions)}\n"
        )

        return self.llm.analyze_json(SYSTEM_PROMPT_RISK, user_prompt)

    # ─── 实时风控 ───

    def record_trade(self, trade: TradeRecord):
        """记录交易，更新风控状态"""
        self.daily_trades.append(trade)
        self._trade_timestamps.append(datetime.now())
        if trade.pnl is not None:
            self.daily_pnl += trade.pnl

    def check_portfolio_risk(self, positions: List[Dict],
                              portfolio_value: float) -> Dict[str, Any]:
        """组合级风险检查"""
        total_position_pct = sum(p.get("position_pct", 0) for p in positions)
        total_unrealized_pnl = sum(p.get("unrealized_pnl", 0) for p in positions)

        risk_issues = []
        if total_position_pct > 0.95:
            risk_issues.append(f"总仓位 {total_position_pct:.1%} 接近满仓")

        if portfolio_value > 0:
            drawdown = (self.daily_pnl + total_unrealized_pnl) / portfolio_value
            if drawdown < -self.config.max_drawdown_pct:
                risk_issues.append(f"组合回撤 {drawdown:.2%} 超过阈值 {self.config.max_drawdown_pct:.2%}")

        return {
            "total_position_pct": total_position_pct,
            "unrealized_pnl": total_unrealized_pnl,
            "daily_pnl": self.daily_pnl,
            "trade_count": len(self.daily_trades),
            "risk_issues": risk_issues,
            "status": "warning" if risk_issues else "normal",
        }

    def format_risk_dashboard(self) -> str:
        """输出风控仪表板"""
        lines = [
            "═" * 50,
            "  🛡 风控仪表板",
            "═" * 50,
            f"  当日交易: {len(self.daily_trades)} 笔",
            f"  当日盈亏: {self.daily_pnl:+.2f}",
            f"  未确认告警: {sum(1 for a in self.daily_alerts if not a.acknowledged)}",
        ]

        if self.daily_alerts:
            lines.append("\n  最近告警:")
            for a in self.daily_alerts[-5:]:
                ack = "✓" if a.acknowledged else "✗"
                lines.append(f"    [{ack}] {a.severity.upper()} | {a.message[:60]}")

        lines.append("═" * 50)
        return "\n".join(lines)

    def reset_daily(self):
        """每日重置"""
        self.daily_trades.clear()
        self.daily_pnl = 0.0
        self.daily_alerts.clear()
        self._trade_timestamps.clear()
