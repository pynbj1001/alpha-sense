"""
配置管理 — 加载并校验系统配置
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class DeepSeekConfig:
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.3
    max_tokens: int = 4096


@dataclass
class TradingHours:
    pre_market_start: str = "08:00"
    morning_open: str = "09:30"
    morning_close: str = "11:30"
    afternoon_open: str = "13:00"
    afternoon_close: str = "15:00"
    post_market_end: str = "17:00"


@dataclass
class TradingConfig:
    market: str = "A股"
    trading_hours: TradingHours = field(default_factory=TradingHours)
    max_positions: int = 10
    max_single_position_pct: float = 0.20
    max_daily_trades: int = 5
    default_stop_loss_pct: float = 0.05
    default_take_profit_pct: float = 0.10


@dataclass
class RiskConfig:
    max_drawdown_pct: float = 0.10
    max_daily_loss_pct: float = 0.03
    confidence_threshold_auto: float = 0.85
    frequency_alert_count: int = 3
    frequency_alert_window_minutes: int = 30
    deviation_alert_threshold: float = 0.6


@dataclass
class VaultConfig:
    storage_dir: str = "vault"
    enable_daily_snapshot: bool = True
    retention_days: int = 365


@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_dir: str = "logs"
    console_output: bool = True


class Config:
    """系统配置中心"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self._raw: Dict[str, Any] = {}
        self.deepseek = DeepSeekConfig()
        self.trading = TradingConfig()
        self.risk = RiskConfig()
        self.vault = VaultConfig()
        self.logging = LoggingConfig()
        self._load()

    def _load(self):
        path = Path(self.config_path)
        if not path.exists():
            print(f"[Config] 配置文件 {self.config_path} 不存在，使用默认配置")
            return

        with open(path, "r", encoding="utf-8") as f:
            self._raw = json.load(f)

        # DeepSeek
        ds = self._raw.get("deepseek", {})
        # 优先从环境变量读取 API Key
        api_key = os.environ.get("DEEPSEEK_API_KEY", ds.get("api_key", ""))
        self.deepseek = DeepSeekConfig(
            api_key=api_key,
            base_url=ds.get("base_url", "https://api.deepseek.com"),
            model=ds.get("model", "deepseek-chat"),
            temperature=ds.get("temperature", 0.3),
            max_tokens=ds.get("max_tokens", 4096),
        )

        # Trading
        td = self._raw.get("trading", {})
        th = td.get("trading_hours", {})
        self.trading = TradingConfig(
            market=td.get("market", "A股"),
            trading_hours=TradingHours(**th) if th else TradingHours(),
            max_positions=td.get("max_positions", 10),
            max_single_position_pct=td.get("max_single_position_pct", 0.20),
            max_daily_trades=td.get("max_daily_trades", 5),
            default_stop_loss_pct=td.get("default_stop_loss_pct", 0.05),
            default_take_profit_pct=td.get("default_take_profit_pct", 0.10),
        )

        # Risk
        rk = self._raw.get("risk", {})
        self.risk = RiskConfig(
            max_drawdown_pct=rk.get("max_drawdown_pct", 0.10),
            max_daily_loss_pct=rk.get("max_daily_loss_pct", 0.03),
            confidence_threshold_auto=rk.get("confidence_threshold_auto", 0.85),
            frequency_alert_count=rk.get("frequency_alert_count", 3),
            frequency_alert_window_minutes=rk.get("frequency_alert_window_minutes", 30),
            deviation_alert_threshold=rk.get("deviation_alert_threshold", 0.6),
        )

        # Vault
        vt = self._raw.get("vault", {})
        self.vault = VaultConfig(
            storage_dir=vt.get("storage_dir", "vault"),
            enable_daily_snapshot=vt.get("enable_daily_snapshot", True),
            retention_days=vt.get("retention_days", 365),
        )

        # Logging
        lg = self._raw.get("logging", {})
        self.logging = LoggingConfig(
            level=lg.get("level", "INFO"),
            log_dir=lg.get("log_dir", "logs"),
            console_output=lg.get("console_output", True),
        )

    def validate(self) -> list[str]:
        """校验配置，返回问题列表"""
        issues = []
        if not self.deepseek.api_key or self.deepseek.api_key == "YOUR_DEEPSEEK_API_KEY":
            issues.append("DeepSeek API Key 未配置，请在 config.json 或环境变量 DEEPSEEK_API_KEY 中设置")
        if self.risk.max_drawdown_pct <= 0 or self.risk.max_drawdown_pct > 1:
            issues.append("最大回撤比例应在 (0, 1] 范围内")
        if self.trading.max_single_position_pct <= 0 or self.trading.max_single_position_pct > 1:
            issues.append("单笔最大仓位比例应在 (0, 1] 范围内")
        return issues
