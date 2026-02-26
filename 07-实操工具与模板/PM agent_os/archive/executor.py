"""
交易执行模块 (Executor)
─────────────────────────────────
执行不是结果，而是一种被批准、可溯源的行为。

只有当：
1. Decision Brief 已生成
2. 风控审查已通过
3. 人工确认（如需要）已完成
执行模块才有资格接手。

本模块是模拟执行器，不对接真实交易所。
如需接入实盘，只需替换 _execute_order 方法。
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .models import DecisionBrief, TradeRecord, Judgment
from .risk_guardian import RiskGuardian

logger = logging.getLogger("agent_os.executor")


class TradeExecutor:
    """
    交易执行器 — 被批准的行为执行者
    
    执行的前提：Decision Brief 已被批准 + 风控已放行
    所有执行都有完整的审计轨迹
    """

    def __init__(self, risk_guardian: RiskGuardian):
        self.risk_guardian = risk_guardian
        self.executed_trades: List[TradeRecord] = []
        self.execution_log: List[Dict[str, Any]] = []

    def execute(self, decision: DecisionBrief,
                judgment: Judgment,
                current_price: Optional[float] = None) -> Optional[TradeRecord]:
        """
        执行交易
        
        严格校验前置条件后才会执行
        
        Args:
            decision: 已批准的 Decision Brief
            judgment: 关联的判断
            current_price: 当前市场价格（模拟执行用）
        
        Returns:
            TradeRecord 如果执行成功，None 如果被拒绝
        """
        # ── 前置校验 ──
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "decision_id": decision.id,
            "action": "execute_attempt",
        }

        # 检查决策状态
        if decision.status != "approved":
            msg = f"Decision {decision.id} 状态为 {decision.status}，不是 approved，拒绝执行"
            logger.warning(f"[执行] ❌ {msg}")
            log_entry["result"] = "rejected"
            log_entry["reason"] = msg
            self.execution_log.append(log_entry)
            return None

        # 检查风控是否放行
        if not decision.risk_check_passed:
            msg = f"Decision {decision.id} 未通过风控审查，拒绝执行"
            logger.warning(f"[执行] ❌ {msg}")
            log_entry["result"] = "rejected"
            log_entry["reason"] = msg
            self.execution_log.append(log_entry)
            return None

        # 检查判断是否仍有效
        if judgment.status == "invalidated":
            msg = f"判断 {judgment.id} 已被证伪，拒绝执行"
            logger.warning(f"[执行] ❌ {msg}")
            log_entry["result"] = "rejected"
            log_entry["reason"] = msg
            self.execution_log.append(log_entry)
            return None

        # ── 执行交易 ──
        entry_price = current_price or decision.entry_price or 0.0
        trade = TradeRecord(
            decision_id=decision.id,
            judgment_id=judgment.id,
            symbol=decision.symbol,
            direction=decision.direction,
            entry_price=entry_price,
            quantity=self._calc_quantity(decision, entry_price),
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
        )

        # 模拟执行
        success = self._execute_order(trade)

        if success:
            decision.status = "executed"
            self.executed_trades.append(trade)
            self.risk_guardian.record_trade(trade)

            log_entry["result"] = "executed"
            log_entry["trade_id"] = trade.id
            log_entry["entry_price"] = trade.entry_price

            logger.info(
                f"[执行] ✅ 交易已执行 | {trade.symbol} {trade.direction} | "
                f"价格 {trade.entry_price} | 数量 {trade.quantity} | "
                f"Trade ID: {trade.id}"
            )
        else:
            log_entry["result"] = "failed"
            log_entry["reason"] = "执行失败（模拟/接口错误）"
            logger.error(f"[执行] ❌ 交易执行失败: {decision.id}")

        self.execution_log.append(log_entry)
        return trade if success else None

    def close_trade(self, trade_id: str, exit_price: float,
                     reason: str = "手动平仓") -> Optional[TradeRecord]:
        """
        平仓
        
        Args:
            trade_id: 交易记录 ID
            exit_price: 平仓价格
            reason: 平仓原因
        """
        trade = None
        for t in self.executed_trades:
            if t.id == trade_id and t.exit_price is None:
                trade = t
                break

        if not trade:
            logger.warning(f"[执行] 未找到可平仓的交易: {trade_id}")
            return None

        trade.exit_price = exit_price
        trade.exit_at = datetime.now().isoformat()
        trade.exit_reason = reason

        # 计算盈亏
        if trade.direction == "long":
            trade.pnl = (exit_price - trade.entry_price) * trade.quantity
        else:
            trade.pnl = (trade.entry_price - exit_price) * trade.quantity

        if trade.entry_price > 0:
            trade.pnl_pct = trade.pnl / (trade.entry_price * trade.quantity)

        # 更新风控
        self.risk_guardian.daily_pnl += trade.pnl

        logger.info(
            f"[执行] 📤 交易已平仓 | {trade.symbol} | "
            f"盈亏 {trade.pnl:+.2f} ({trade.pnl_pct:+.2%}) | "
            f"原因: {reason}"
        )

        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "trade_id": trade_id,
            "action": "close",
            "exit_price": exit_price,
            "pnl": trade.pnl,
            "reason": reason,
        })

        return trade

    def _calc_quantity(self, decision: DecisionBrief, price: float,
                       portfolio_value: float = 1000000) -> int:
        """计算交易数量（A 股按手，每手 100 股）"""
        if price <= 0:
            return 0
        position_value = portfolio_value * decision.position_size_pct
        shares = int(position_value / price)
        # A 股取整到 100 股（1手）
        lots = shares // 100
        return lots * 100

    def _execute_order(self, trade: TradeRecord) -> bool:
        """
        执行下单（模拟）
        
        生产环境中替换此方法为真实接口调用
        """
        logger.info(f"[执行] 📋 模拟下单: {trade.symbol} {trade.direction} "
                     f"@ {trade.entry_price} x {trade.quantity}")
        # 模拟：总是成功
        return True

    def get_open_positions(self) -> List[TradeRecord]:
        """获取当前持仓（未平仓交易）"""
        return [t for t in self.executed_trades if t.exit_price is None]

    def format_execution_summary(self) -> str:
        """执行摘要"""
        open_trades = self.get_open_positions()
        closed_trades = [t for t in self.executed_trades if t.exit_price is not None]

        lines = [
            "─" * 50,
            "  📊 执行摘要",
            "─" * 50,
            f"  总执行: {len(self.executed_trades)} 笔",
            f"  持仓中: {len(open_trades)} 笔",
            f"  已平仓: {len(closed_trades)} 笔",
        ]

        if open_trades:
            lines.append("\n  【持仓中】")
            for t in open_trades:
                lines.append(
                    f"    {t.symbol} | {t.direction} | "
                    f"入场 {t.entry_price} | 数量 {t.quantity}"
                )

        if closed_trades:
            total_pnl = sum(t.pnl or 0 for t in closed_trades)
            lines.append(f"\n  【已平仓盈亏】{total_pnl:+.2f}")

        lines.append("─" * 50)
        return "\n".join(lines)

    def reset_daily(self):
        """每日重置执行日志（交易记录保留）"""
        self.execution_log.clear()
