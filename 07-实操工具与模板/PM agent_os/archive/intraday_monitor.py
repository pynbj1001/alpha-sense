"""
盘中监控模块 (Intraday Monitor)
─────────────────────────────────
核心职责：
1. 监控判断是否正在被市场破坏（不是盯涨跌）
2. 检测交易者行为是否偏离晨间设定的边界
3. 识别属于自己风格的机会
4. 生成实时告警

盘中本质上是监控，而不是行动。
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .llm_client import DeepSeekClient
from .models import Judgment, RiskAlert, DecisionBrief

logger = logging.getLogger("agent_os.intraday")

SYSTEM_PROMPT_MONITOR = """你是一位盘中认知守护者。你的职责不是分析行情走势，而是持续回答一个核心问题：
「早上的判断，还站得住吗？」

你需要基于以下信息做出分析：
1. 晨间的判断和边界条件
2. 用户提供的盘中最新信息
3. 当前价格与判断预期的关系

重要原则：
- 价格上涨 ≠ 判断正确
- 价格下跌 ≠ 判断错误
- 真正危险的是：判断逻辑出现松动迹象，却被情绪遮蔽

输出要求（JSON 格式）：
{
  "timestamp": "当前时间",
  "judgments_check": [
    {
      "judgment_id": "ID",
      "status": "intact/weakening/broken",
      "evidence": "支撑/否定判断的盘中证据",
      "action_suggestion": "继续持有/减仓/离场/无需操作"
    }
  ],
  "boundary_violations": ["是否触碰了晨间设定的不操作条件"],
  "opportunity_detected": false,
  "opportunity_description": "",
  "overall_assessment": "一句话总结当前状态",
  "risk_level": "low/medium/high/critical"
}"""

SYSTEM_PROMPT_DEVIATION = """你是一位行为偏差检测器。你需要判断交易者当前的行为是否偏离了他早上制定的计划。

偏差的常见表现：
1. 想要交易的标的不在晨间判断列表中
2. 方向与判断不一致
3. 交易频率异常升高
4. 在边界条件触发时仍想交易
5. 置信度不足但急于出手

输出要求（JSON 格式）：
{
  "deviation_detected": true/false,
  "deviation_type": "偏差类型",
  "deviation_severity": 0.0-1.0,
  "explanation": "详细解释",
  "question_to_trader": "需要交易者回答的问题（逼他想清楚）"
}"""


class IntradayMonitor:
    """盘中监控 Agent"""

    def __init__(self, llm: DeepSeekClient):
        self.llm = llm
        self.alerts: List[RiskAlert] = []
        self._check_count = 0

    def monitor_judgments(self, judgments: List[Judgment],
                          market_update: str,
                          boundary_conditions: List[str] = None) -> Dict[str, Any]:
        """
        执行一次判断状态监控
        
        Args:
            judgments: 当日活跃判断列表
            market_update: 用户提供的最新盘面信息
            boundary_conditions: 晨间设定的边界条件
        """
        self._check_count += 1

        judgments_info = []
        for j in judgments:
            if j.status in ("active", "weakened"):
                judgments_info.append({
                    "id": j.id,
                    "symbol": f"{j.symbol} ({j.symbol_name})",
                    "direction": j.direction,
                    "thesis": j.thesis,
                    "confidence": j.confidence,
                    "key_variables": j.key_variables,
                    "invalidation_conditions": j.invalidation_conditions,
                    "current_status": j.status,
                })

        user_prompt = (
            f"【第 {self._check_count} 次盘中检查】\n"
            f"时间: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"【当日活跃判断】\n"
            + "\n".join(
                f"  [{j['id']}] {j['symbol']} | {j['direction']} | "
                f"置信度 {j['confidence']} | {j['thesis']}"
                for j in judgments_info
            )
            + f"\n\n【晨间边界条件】\n"
            + "\n".join(f"  🚫 {b}" for b in (boundary_conditions or []))
            + f"\n\n【最新盘面信息】\n{market_update}"
        )

        logger.info(f"[盘中] 第 {self._check_count} 次监控检查...")
        result = self.llm.analyze_json(SYSTEM_PROMPT_MONITOR, user_prompt)

        # 根据结果生成告警
        self._process_alerts(result)
        return result

    def check_deviation(self, intended_action: str,
                         active_judgments: List[Judgment],
                         boundary_conditions: List[str],
                         recent_trade_count: int = 0) -> Dict[str, Any]:
        """
        检测交易者行为是否偏离计划
        
        Args:
            intended_action: 交易者想要执行的操作描述
            active_judgments: 当日活跃判断
            boundary_conditions: 边界条件
            recent_trade_count: 近期交易次数
        """
        user_prompt = (
            f"【交易者想要执行的操作】\n{intended_action}\n\n"
            f"【今日活跃判断】\n"
            + "\n".join(
                f"  [{j.id}] {j.symbol} | {j.direction} | {j.thesis}"
                for j in active_judgments if j.status in ("active", "weakened")
            )
            + f"\n\n【今日边界条件】\n"
            + "\n".join(f"  {b}" for b in boundary_conditions)
            + f"\n\n【今日已交易次数】{recent_trade_count}"
        )

        logger.info("[盘中] 执行行为偏差检测...")
        result = self.llm.analyze_json(SYSTEM_PROMPT_DEVIATION, user_prompt)

        if result.get("deviation_detected"):
            alert = RiskAlert(
                alert_type="deviation_detected",
                severity="high" if result.get("deviation_severity", 0) > 0.7 else "medium",
                message=result.get("explanation", "检测到行为偏差"),
            )
            self.alerts.append(alert)
            logger.warning(f"[盘中] ⚠ 行为偏差告警: {alert.message}")

        return result

    def _process_alerts(self, monitor_result: Dict[str, Any]):
        """从监控结果中提取并记录告警"""
        # 判断松动告警
        for jc in monitor_result.get("judgments_check", []):
            if jc.get("status") == "weakening":
                alert = RiskAlert(
                    alert_type="judgment_weakened",
                    severity="medium",
                    message=f"判断 [{jc.get('judgment_id')}] 出现松动: {jc.get('evidence', '')}",
                    related_judgment_id=jc.get("judgment_id", ""),
                )
                self.alerts.append(alert)
            elif jc.get("status") == "broken":
                alert = RiskAlert(
                    alert_type="judgment_invalidated",
                    severity="high",
                    message=f"判断 [{jc.get('judgment_id')}] 已被破坏: {jc.get('evidence', '')}",
                    related_judgment_id=jc.get("judgment_id", ""),
                )
                self.alerts.append(alert)

        # 边界条件违反
        for violation in monitor_result.get("boundary_violations", []):
            if violation:
                alert = RiskAlert(
                    alert_type="deviation_detected",
                    severity="high",
                    message=f"边界条件被触碰: {violation}",
                )
                self.alerts.append(alert)

        # 风险等级告警
        risk_level = monitor_result.get("risk_level", "low")
        if risk_level in ("high", "critical"):
            alert = RiskAlert(
                alert_type="drawdown_warning",
                severity=risk_level,
                message=f"当前风险等级: {risk_level} - {monitor_result.get('overall_assessment', '')}",
            )
            self.alerts.append(alert)

    def get_unacknowledged_alerts(self) -> List[RiskAlert]:
        """获取所有未确认的告警"""
        return [a for a in self.alerts if not a.acknowledged]

    def acknowledge_alert(self, alert_id: str):
        """确认告警"""
        for a in self.alerts:
            if a.id == alert_id:
                a.acknowledged = True
                a.acknowledged_at = datetime.now().isoformat()
                break

    def format_monitor_report(self, result: Dict[str, Any]) -> str:
        """格式化监控报告"""
        lines = [
            "─" * 50,
            f"  🔍 盘中监控报告 | {datetime.now().strftime('%H:%M:%S')}",
            "─" * 50,
        ]

        risk_icons = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
        risk_level = result.get("risk_level", "low")
        lines.append(f"  风险等级: {risk_icons.get(risk_level, '⚪')} {risk_level.upper()}")
        lines.append(f"  {result.get('overall_assessment', '')}")
        lines.append("")

        for jc in result.get("judgments_check", []):
            status_icons = {"intact": "✅", "weakening": "⚡", "broken": "❌"}
            icon = status_icons.get(jc.get("status", ""), "❓")
            lines.append(f"  {icon} [{jc.get('judgment_id', '?')}] {jc.get('status', '?')}")
            lines.append(f"      证据: {jc.get('evidence', '无')}")
            lines.append(f"      建议: {jc.get('action_suggestion', '无')}")

        for v in result.get("boundary_violations", []):
            if v:
                lines.append(f"  🚫 边界触碰: {v}")

        if result.get("opportunity_detected"):
            lines.append(f"\n  💡 机会识别: {result.get('opportunity_description', '')}")

        # 未确认告警
        unack = self.get_unacknowledged_alerts()
        if unack:
            lines.append(f"\n  ⚠ {len(unack)} 条未确认告警")
            for a in unack[-3:]:
                lines.append(f"      [{a.id}] {a.message}")

        lines.append("─" * 50)
        return "\n".join(lines)

    def reset_daily(self):
        """每日重置"""
        self.alerts.clear()
        self._check_count = 0
