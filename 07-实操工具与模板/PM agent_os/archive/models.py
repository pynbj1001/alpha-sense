"""
核心数据模型 — 系统中所有结构化数据的定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import uuid
import json


# ──────────────────────────────────────────────
# 枚举类型
# ──────────────────────────────────────────────

class MarketPhase(Enum):
    """市场阶段"""
    PRE_MARKET = "pre_market"       # 盘前
    INTRADAY = "intraday"           # 盘中
    POST_MARKET = "post_market"     # 盘后
    CLOSED = "closed"               # 休市


class Direction(Enum):
    """交易方向"""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class JudgmentStatus(Enum):
    """判断状态"""
    ACTIVE = "active"               # 判断仍然成立
    WEAKENED = "weakened"           # 判断出现松动
    INVALIDATED = "invalidated"     # 判断已被证伪
    EXPIRED = "expired"             # 判断已过期


class DecisionStatus(Enum):
    """决策状态"""
    DRAFT = "draft"                 # 草案
    PENDING_REVIEW = "pending"      # 等待审核
    APPROVED = "approved"           # 已批准
    REJECTED = "rejected"           # 已拒绝
    EXECUTED = "executed"           # 已执行
    CANCELLED = "cancelled"         # 已取消


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """告警类型"""
    JUDGMENT_WEAKENED = "judgment_weakened"
    JUDGMENT_INVALIDATED = "judgment_invalidated"
    FREQUENCY_ANOMALY = "frequency_anomaly"
    DRAWDOWN_WARNING = "drawdown_warning"
    POSITION_LIMIT = "position_limit"
    DEVIATION_DETECTED = "deviation_detected"
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"


# ──────────────────────────────────────────────
# 核心数据模型
# ──────────────────────────────────────────────

@dataclass
class Judgment:
    """
    判断 — 基金经理认知的最小单元
    每一个判断都有生命周期：创建 → 确认/松动 → 失效/过期
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # 判断内容
    symbol: str = ""                    # 标的代码
    symbol_name: str = ""               # 标的名称
    thesis: str = ""                    # 核心判断逻辑
    direction: str = "neutral"          # long / short / neutral
    confidence: float = 0.5             # 置信度 0-1
    time_horizon: str = ""              # 时间框架（日内/短期/中期）
    key_variables: List[str] = field(default_factory=list)  # 支撑判断的关键变量
    invalidation_conditions: List[str] = field(default_factory=list)  # 证伪条件

    # 状态
    status: str = "active"              # active / weakened / invalidated / expired
    status_reason: str = ""             # 状态变更原因

    # AI 评估
    ai_assessment: str = ""             # AI 对该判断的评估
    ai_risk_notes: str = ""             # AI 识别的风险

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "symbol": self.symbol,
            "symbol_name": self.symbol_name,
            "thesis": self.thesis,
            "direction": self.direction,
            "confidence": self.confidence,
            "time_horizon": self.time_horizon,
            "key_variables": self.key_variables,
            "invalidation_conditions": self.invalidation_conditions,
            "status": self.status,
            "status_reason": self.status_reason,
            "ai_assessment": self.ai_assessment,
            "ai_risk_notes": self.ai_risk_notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Judgment":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class DecisionBrief:
    """
    决策简报 — 判断到执行之间的桥梁
    每一次可能进入交易的行为，都必须先生成 Decision Brief
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # 关联
    judgment_id: str = ""               # 来源判断
    trader: str = ""                    # 交易者

    # 决策内容
    symbol: str = ""
    symbol_name: str = ""
    direction: str = "neutral"
    confidence: float = 0.5
    rationale: str = ""                 # 决策理由（必须写清楚）
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size_pct: float = 0.0      # 仓位占比

    # 审批
    requires_manual_confirm: bool = True   # 是否需要人工确认
    status: str = "draft"               # draft / pending / approved / rejected / executed / cancelled
    approved_at: Optional[str] = None
    rejected_reason: str = ""

    # AI 风控审查
    risk_check_result: str = ""         # 风控审查结论
    risk_check_passed: bool = False     # 风控是否放行

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "judgment_id": self.judgment_id,
            "trader": self.trader,
            "symbol": self.symbol,
            "symbol_name": self.symbol_name,
            "direction": self.direction,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_size_pct": self.position_size_pct,
            "requires_manual_confirm": self.requires_manual_confirm,
            "status": self.status,
            "approved_at": self.approved_at,
            "rejected_reason": self.rejected_reason,
            "risk_check_result": self.risk_check_result,
            "risk_check_passed": self.risk_check_passed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionBrief":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TradeRecord:
    """交易记录 — 每笔被执行的交易"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    decision_id: str = ""               # 关联的 Decision Brief
    judgment_id: str = ""               # 关联的判断
    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    symbol: str = ""
    direction: str = ""
    entry_price: float = 0.0
    quantity: int = 0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # 结果（平仓后填写）
    exit_price: Optional[float] = None
    exit_at: Optional[str] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    exit_reason: str = ""               # 止盈/止损/判断失效/手动平仓

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradeRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RiskAlert:
    """风险告警"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    alert_type: str = ""                # AlertType 的值
    severity: str = "medium"            # low / medium / high / critical
    message: str = ""
    related_judgment_id: str = ""
    related_decision_id: str = ""
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class DailySnapshot:
    """每日快照 — 收盘后归档到 Vault"""
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    market_phase_log: List[str] = field(default_factory=list)

    # 盘前
    pre_market_briefing: str = ""
    morning_judgments: List[Dict] = field(default_factory=list)
    boundary_conditions: List[str] = field(default_factory=list)  # 今天不应出手的条件

    # 盘中
    intraday_alerts: List[Dict] = field(default_factory=list)
    judgment_status_changes: List[Dict] = field(default_factory=list)

    # 决策与执行
    decisions: List[Dict] = field(default_factory=list)
    trades: List[Dict] = field(default_factory=list)

    # 盘后
    post_market_review: str = ""
    lessons_learned: List[str] = field(default_factory=list)
    ai_daily_summary: str = ""

    # 绩效
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
