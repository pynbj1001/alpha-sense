"""
主控 Agent 调度引擎 (Agent OS Core)
─────────────────────────────────
协调所有模块，管理完整的交易日生命周期：
盘前研判 → 盘中监控 → 决策生成 → 风控审查 → 执行 → 盘后复盘

这是整个系统的中枢，负责：
1. 初始化所有模块
2. 管理当日状态（判断、决策、交易）
3. 提供统一的操作接口
4. 驱动完整的日内工作流
"""

import logging
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .config import Config
from .llm_client import DeepSeekClient
from .models import (
    Judgment, DecisionBrief, TradeRecord, DailySnapshot, RiskAlert
)
from .pre_market import PreMarketAnalyst
from .intraday_monitor import IntradayMonitor
from .decision_engine import DecisionEngine
from .risk_guardian import RiskGuardian
from .executor import TradeExecutor
from .vault import PostMarketVault

logger = logging.getLogger("agent_os")


class AgentOS:
    """
    Agent OS — 基金经理认知守护系统
    
    它不会替你做决策，但它会：
    - 在你最想冲动的时候逼你把逻辑写清楚
    - 在你最自信的时候提醒你检查风险
    - 在你最疲惫的时候帮你完整复盘
    """

    def __init__(self, config_path: str = "config.json"):
        # 加载配置
        self.config = Config(config_path)
        issues = self.config.validate()
        if issues:
            for issue in issues:
                logger.warning(f"[配置警告] {issue}")

        # 初始化 LLM
        self.llm = DeepSeekClient(
            api_key=self.config.deepseek.api_key,
            base_url=self.config.deepseek.base_url,
            model=self.config.deepseek.model,
            temperature=self.config.deepseek.temperature,
            max_tokens=self.config.deepseek.max_tokens,
        )

        # 初始化模块
        self.pre_market = PreMarketAnalyst(self.llm)
        self.intraday = IntradayMonitor(self.llm)
        self.decision_engine = DecisionEngine(self.llm, self.config.risk)
        self.risk_guardian = RiskGuardian(self.llm, self.config.risk)
        self.executor = TradeExecutor(self.risk_guardian)
        self.vault = PostMarketVault(self.llm, self.config.vault.storage_dir)

        # 当日状态
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.judgments: List[Judgment] = []
        self.daily_snapshot = DailySnapshot(date=self.today)
        self.trader_name: str = ""
        self.boundary_conditions: List[str] = []

        # 设置日志
        self._setup_logging()
        logger.info(f"[Agent OS] 系统初始化完成 | {self.today}")

    def _setup_logging(self):
        """配置日志"""
        log_dir = Path(self.config.logging.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        log_format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
        log_level = getattr(logging, self.config.logging.level, logging.INFO)

        # 文件日志
        file_handler = logging.FileHandler(
            log_dir / f"{self.today}.log", encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(log_format))

        # 根 Logger
        root_logger = logging.getLogger("agent_os")
        root_logger.setLevel(log_level)
        root_logger.addHandler(file_handler)

        if self.config.logging.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(console_handler)

    # ═══════════════════════════════════════════════
    #  Phase 1: 盘前研判
    # ═══════════════════════════════════════════════

    def morning_briefing(self, market_context: str = "") -> str:
        """
        执行盘前研判流程
        
        基金经理的一天，从确认边界开始。
        第一件事不是问今天买什么，而是问：
        今天在什么情况下，我不应该动手。
        """
        logger.info("[Agent OS] ═══ 开始盘前研判 ═══")

        # 加载昨日快照
        recent = self.vault.get_recent_snapshots(1)
        prev_snapshot = None
        if recent:
            prev = self.vault.load_snapshot(recent[0])
            if prev:
                prev_snapshot = prev.to_dict()

        # 生成晨间简报
        briefing = self.pre_market.generate_morning_briefing(
            market_context=market_context,
            previous_snapshot=prev_snapshot,
        )

        # 检查已有判断
        judgment_checks = []
        if self.judgments:
            judgment_checks = self.pre_market.check_all_judgments(
                self.judgments, market_context
            )
            # 更新判断状态
            for check in judgment_checks:
                self._apply_judgment_check(check)

        # 记录边界条件
        self.boundary_conditions = briefing.get("boundary_conditions", [])

        # 更新快照
        self.daily_snapshot.pre_market_briefing = briefing.get("briefing_summary", "")
        self.daily_snapshot.boundary_conditions = self.boundary_conditions
        self.daily_snapshot.morning_judgments = [j.to_dict() for j in self.judgments]

        # 格式化报告
        report = self.pre_market.format_briefing_report(briefing, judgment_checks)
        logger.info("[Agent OS] ═══ 盘前研判完成 ═══")
        return report

    # ═══════════════════════════════════════════════
    #  判断管理
    # ═══════════════════════════════════════════════

    def add_judgment(self, symbol: str, symbol_name: str,
                      direction: str, thesis: str,
                      confidence: float = 0.5,
                      time_horizon: str = "日内",
                      key_variables: List[str] = None,
                      invalidation_conditions: List[str] = None) -> Judgment:
        """
        添加一个新的判断
        
        每一个判断都必须包含证伪条件 —— 
        你必须提前说明，在什么情况下你会认为自己错了。
        """
        judgment = Judgment(
            symbol=symbol,
            symbol_name=symbol_name,
            direction=direction,
            thesis=thesis,
            confidence=confidence,
            time_horizon=time_horizon,
            key_variables=key_variables or [],
            invalidation_conditions=invalidation_conditions or [],
        )

        # AI 评估判断质量
        assessment = self.pre_market.check_judgment(
            judgment, "新增判断，请评估判断的质量和完备性"
        )
        judgment.ai_assessment = assessment.get("reasoning", "")
        judgment.ai_risk_notes = "; ".join(assessment.get("warning_signs", []))

        self.judgments.append(judgment)
        logger.info(
            f"[Agent OS] 新增判断: {judgment.id} | "
            f"{symbol} {direction} | 置信度 {confidence:.0%}"
        )
        return judgment

    def list_judgments(self, status_filter: str = None) -> List[Judgment]:
        """列出判断"""
        if status_filter:
            return [j for j in self.judgments if j.status == status_filter]
        return self.judgments

    def update_judgment(self, judgment_id: str, **kwargs) -> Optional[Judgment]:
        """更新判断"""
        for j in self.judgments:
            if j.id == judgment_id:
                for k, v in kwargs.items():
                    if hasattr(j, k):
                        setattr(j, k, v)
                j.updated_at = datetime.now().isoformat()
                return j
        return None

    def _apply_judgment_check(self, check: Dict[str, Any]):
        """应用判断检查结果"""
        jid = check.get("judgment_id", "")
        for j in self.judgments:
            if j.id == jid:
                new_status = check.get("new_status", j.status)
                if new_status != j.status:
                    old_status = j.status
                    j.status = new_status
                    j.status_reason = check.get("reasoning", "")
                    j.updated_at = datetime.now().isoformat()
                    logger.info(
                        f"[Agent OS] 判断 {jid} 状态变更: {old_status} → {new_status}"
                    )
                    self.daily_snapshot.judgment_status_changes.append({
                        "judgment_id": jid,
                        "from": old_status,
                        "to": new_status,
                        "reason": check.get("reasoning", ""),
                        "timestamp": datetime.now().isoformat(),
                    })

                # 调整置信度
                adj = check.get("confidence_adjustment", 0)
                if adj:
                    j.confidence = max(0, min(1, j.confidence + adj))
                break

    # ═══════════════════════════════════════════════
    #  Phase 2: 盘中监控
    # ═══════════════════════════════════════════════

    def intraday_check(self, market_update: str) -> str:
        """
        执行盘中监控
        
        盘中最重要的不是涨跌，而是判断是否被破坏。
        """
        result = self.intraday.monitor_judgments(
            judgments=self.judgments,
            market_update=market_update,
            boundary_conditions=self.boundary_conditions,
        )

        # 应用判断状态变更
        for jc in result.get("judgments_check", []):
            status_map = {"intact": "active", "weakening": "weakened", "broken": "invalidated"}
            mapped_status = status_map.get(jc.get("status", ""), None)
            if mapped_status:
                self._apply_judgment_check({
                    "judgment_id": jc.get("judgment_id", ""),
                    "new_status": mapped_status,
                    "reasoning": jc.get("evidence", ""),
                })

        # 记录告警
        new_alerts = self.intraday.get_unacknowledged_alerts()
        for alert in new_alerts:
            self.daily_snapshot.intraday_alerts.append(alert.to_dict())

        return self.intraday.format_monitor_report(result)

    def check_my_action(self, intended_action: str) -> str:
        """
        在你想要操作之前，先让系统检查：
        你现在做的，还是你早上说的那件事吗？
        """
        result = self.intraday.check_deviation(
            intended_action=intended_action,
            active_judgments=self.judgments,
            boundary_conditions=self.boundary_conditions,
            recent_trade_count=len(self.executor.executed_trades),
        )

        lines = ["─" * 50, "  🔍 行为偏差检测结果", "─" * 50]

        if result.get("deviation_detected"):
            severity = result.get("deviation_severity", 0)
            lines.append(f"  ⚠ 检测到偏差! 严重度: {severity:.0%}")
            lines.append(f"  类型: {result.get('deviation_type', '未知')}")
            lines.append(f"  说明: {result.get('explanation', '')}")
            lines.append(f"\n  ❓ 系统提问: {result.get('question_to_trader', '')}")
        else:
            lines.append("  ✅ 未检测到偏差，行为与计划一致")

        lines.append("─" * 50)
        return "\n".join(lines)

    # ═══════════════════════════════════════════════
    #  Phase 3: 决策与执行
    # ═══════════════════════════════════════════════

    def create_trade_decision(self, judgment_id: str,
                                trade_idea: str,
                                entry_price: float = None,
                                stop_loss: float = None,
                                take_profit: float = None,
                                position_pct: float = 0.05) -> str:
        """
        创建交易决策
        
        每一次可能进入交易的行为，都必须先生成 Decision Brief。
        它不是交易指令，而是一份判断说明。
        """
        # 找到关联判断
        judgment = None
        for j in self.judgments:
            if j.id == judgment_id:
                judgment = j
                break

        if not judgment:
            return f"❌ 未找到判断 {judgment_id}。请先通过 add_judgment 创建判断。"

        if judgment.status == "invalidated":
            return f"❌ 判断 {judgment_id} 已被证伪，不能基于已失效的判断创建交易。"

        # 生成 Decision Brief
        brief = self.decision_engine.create_decision_brief(
            trader=self.trader_name or "默认交易者",
            judgment=judgment,
            trade_idea=trade_idea,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_pct=position_pct,
        )

        # 风控审查
        risk_result = self.risk_guardian.review_decision(
            decision=brief,
            judgment=judgment,
            current_positions=[],
        )

        # 记录到快照
        self.daily_snapshot.decisions.append(brief.to_dict())

        # 格式化输出
        output = self.decision_engine.format_decision_brief(brief)

        # 追加风控结果
        if risk_result.get("must_answer"):
            output += f"\n\n  ❓ 风控提问: {risk_result['must_answer']}"

        if brief.requires_manual_confirm:
            output += f"\n\n  ⏳ 需要人工确认。执行: approve_decision('{brief.id}')"
        else:
            output += "\n\n  🤖 满足自动执行条件"

        return output

    def approve_decision(self, decision_id: str,
                          current_price: float = None) -> str:
        """
        批准并执行决策
        
        在这里，执行不是结果，而是一种被批准、可溯源的行为。
        """
        # 批准
        decision = self.decision_engine.approve_decision(decision_id)
        if not decision:
            return f"❌ 未找到待审批的决策: {decision_id}"

        # 检查风控是否放行
        if not decision.risk_check_passed:
            return (
                f"⚠ Decision {decision_id} 已批准但风控未放行。\n"
                f"风控结论: {decision.risk_check_result}\n"
                f"如需强制执行，请使用 force_execute('{decision_id}')"
            )

        # 找到关联判断
        judgment = None
        for j in self.judgments:
            if j.id == decision.judgment_id:
                judgment = j
                break

        if not judgment:
            return f"❌ 关联判断 {decision.judgment_id} 不存在"

        # 执行
        trade = self.executor.execute(decision, judgment, current_price)

        if trade:
            self.daily_snapshot.trades.append(trade.to_dict())
            return (
                f"✅ 交易已执行!\n"
                f"  Trade ID: {trade.id}\n"
                f"  {trade.symbol} {trade.direction}\n"
                f"  入场价: {trade.entry_price}\n"
                f"  数量: {trade.quantity}\n"
                f"  止损: {trade.stop_loss or '未设置'}\n"
                f"  止盈: {trade.take_profit or '未设置'}"
            )
        else:
            return f"❌ 交易执行失败，请查看日志"

    def reject_decision(self, decision_id: str, reason: str = "") -> str:
        """拒绝决策"""
        decision = self.decision_engine.reject_decision(decision_id, reason)
        if decision:
            return f"❌ Decision {decision_id} 已拒绝。原因: {reason or '未说明'}"
        return f"未找到待审批的决策: {decision_id}"

    def close_position(self, trade_id: str, exit_price: float,
                        reason: str = "手动平仓") -> str:
        """平仓"""
        trade = self.executor.close_trade(trade_id, exit_price, reason)
        if trade:
            # 更新快照中的交易记录
            for i, t in enumerate(self.daily_snapshot.trades):
                if t.get("id") == trade_id:
                    self.daily_snapshot.trades[i] = trade.to_dict()
                    break
            return (
                f"📤 已平仓 | {trade.symbol}\n"
                f"  盈亏: {trade.pnl:+.2f} ({trade.pnl_pct:+.2%})\n"
                f"  原因: {reason}"
            )
        return f"❌ 未找到可平仓的交易: {trade_id}"

    # ═══════════════════════════════════════════════
    #  Phase 4: 盘后复盘
    # ═══════════════════════════════════════════════

    def end_of_day(self) -> str:
        """
        执行盘后复盘流程
        
        收盘后决定的，往往是你未来几年的曲线形态。
        """
        logger.info("[Agent OS] ═══ 开始盘后复盘 ═══")

        # 更新快照
        self.daily_snapshot.morning_judgments = [j.to_dict() for j in self.judgments]
        self.daily_snapshot.intraday_alerts = [
            a.to_dict() for a in self.intraday.alerts
        ]
        self.daily_snapshot.decisions = [
            d.to_dict() for d in
            (self.decision_engine.pending_decisions + self.decision_engine.completed_decisions)
        ]
        self.daily_snapshot.trades = [
            t.to_dict() for t in self.executor.executed_trades
        ]

        # 计算盈亏
        total_pnl = sum(
            (t.pnl or 0) for t in self.executor.executed_trades
            if t.pnl is not None
        )
        self.daily_snapshot.daily_pnl = total_pnl

        # 生成 AI 复盘
        review = self.vault.generate_daily_review(self.daily_snapshot)

        # 保存到 Vault
        self.daily_snapshot.post_market_review = review.get("detailed_review", "")
        self.daily_snapshot.lessons_learned = review.get("key_lessons", [])
        self.daily_snapshot.ai_daily_summary = review.get("detailed_review", "")
        self.vault.save_snapshot(self.daily_snapshot, review)

        # 格式化报告
        report = self.vault.format_review_report(review)

        # 重置模块
        self.intraday.reset_daily()
        self.decision_engine.reset_daily()
        self.risk_guardian.reset_daily()
        self.executor.reset_daily()

        logger.info("[Agent OS] ═══ 盘后复盘完成，数据已归档 ═══")
        return report

    # ═══════════════════════════════════════════════
    #  查询与工具方法
    # ═══════════════════════════════════════════════

    def status(self) -> str:
        """输出当前系统状态总览"""
        active_judgments = [j for j in self.judgments if j.status == "active"]
        weakened_judgments = [j for j in self.judgments if j.status == "weakened"]
        pending_decisions = self.decision_engine.get_pending_decisions()
        open_positions = self.executor.get_open_positions()
        unack_alerts = self.intraday.get_unacknowledged_alerts()

        lines = [
            "═" * 55,
            f"  🖥 Agent OS 状态总览 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "═" * 55,
            f"  交易者: {self.trader_name or '未设定'}",
            f"  交易市场: {self.config.trading.market}",
            "",
            f"  📊 判断: {len(active_judgments)} 活跃 / {len(weakened_judgments)} 松动 / {len(self.judgments)} 总计",
            f"  📋 待审决策: {len(pending_decisions)}",
            f"  📈 持仓: {len(open_positions)}",
            f"  ⚠ 未确认告警: {len(unack_alerts)}",
            f"  💰 当日盈亏: {self.risk_guardian.daily_pnl:+.2f}",
        ]

        if self.boundary_conditions:
            lines.append(f"\n  🚫 边界条件 ({len(self.boundary_conditions)}):")
            for b in self.boundary_conditions[:3]:
                lines.append(f"    • {b}")

        if active_judgments:
            lines.append(f"\n  ✅ 活跃判断:")
            for j in active_judgments:
                lines.append(
                    f"    [{j.id}] {j.symbol} {j.direction} | "
                    f"置信度 {j.confidence:.0%}"
                )

        if weakened_judgments:
            lines.append(f"\n  ⚡ 松动判断:")
            for j in weakened_judgments:
                lines.append(
                    f"    [{j.id}] {j.symbol} | 原因: {j.status_reason[:50]}"
                )

        lines.append("═" * 55)
        return "\n".join(lines)

    def risk_dashboard(self) -> str:
        """风控仪表板"""
        return self.risk_guardian.format_risk_dashboard()

    def execution_summary(self) -> str:
        """执行摘要"""
        return self.executor.format_execution_summary()

    def replay_day(self, date: str) -> str:
        """回放指定日期的交易记录"""
        snapshot = self.vault.load_snapshot(date)
        if not snapshot:
            return f"❌ 未找到 {date} 的记录"

        review = self.vault.load_review(date)
        lines = [f"═══ 回放: {date} ═══"]

        if snapshot.pre_market_briefing:
            lines.append(f"\n▎盘前简报:\n  {snapshot.pre_market_briefing}")

        if snapshot.morning_judgments:
            lines.append(f"\n▎判断 ({len(snapshot.morning_judgments)}):")
            for j in snapshot.morning_judgments:
                lines.append(f"  [{j.get('id')}] {j.get('symbol')} {j.get('direction')}")

        if snapshot.trades:
            lines.append(f"\n▎交易 ({len(snapshot.trades)}):")
            for t in snapshot.trades:
                lines.append(
                    f"  {t.get('symbol')} | 盈亏: {t.get('pnl', '?')}"
                )

        if review:
            lines.append(f"\n▎复盘评级: {review.get('overall_grade', '?')}")
            for lesson in review.get("key_lessons", []):
                lines.append(f"  • {lesson}")

        return "\n".join(lines)

    def search_history(self, keyword: str) -> str:
        """在历史记录中搜索"""
        results = self.vault.search_vault(keyword)
        if not results:
            return f"未找到包含 '{keyword}' 的记录"

        lines = [f"找到 {len(results)} 条相关记录:"]
        for r in results[:10]:
            lines.append(f"  [{r['date']}] ({r['type']}) {r['preview'][:80]}...")
        return "\n".join(lines)

    def shutdown(self):
        """关闭系统"""
        self.llm.close()
        logger.info("[Agent OS] 系统已关闭")
