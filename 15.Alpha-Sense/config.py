#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alpha Sense — 全局配置

路径、阈值、常量统一管理。
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------

# Alpha-Sense 自身根目录
ALPHA_DIR = Path(__file__).resolve().parent

# 投资框架工作区根目录
WORKSPACE_ROOT = ALPHA_DIR.parent

# 现有子系统路径
TRACKER_DIR = WORKSPACE_ROOT / "14.贝叶斯追踪器"
WATCHLIST_PATH = WORKSPACE_ROOT / "11.投资机会跟踪报告" / "ideas_watchlist.json"
REPORTS_DIR = WORKSPACE_ROOT / "10-研究报告输出"
LESSONS_PATH = WORKSPACE_ROOT / "tasks" / "lessons.md"

# Alpha-Sense 数据目录
DATA_DIR = ALPHA_DIR / "data"
SIGNALS_FILE = DATA_DIR / "signals.json"
REGRETS_FILE = DATA_DIR / "regrets.json"
CONVICTION_LOG_FILE = DATA_DIR / "conviction_log.json"
WEEKLY_REVIEWS_DIR = DATA_DIR / "weekly_reviews"

# ---------------------------------------------------------------------------
# 信念升级阶梯阈值
# ---------------------------------------------------------------------------

CONVICTION_LADDER = [
    {
        "level": "L0",
        "name": "信号捕获",
        "prob_min": 0.00,
        "prob_max": 0.55,
        "position": "0%",
        "action": "@信号 自动入库",
        "color": "#6c757d",
    },
    {
        "level": "L1",
        "name": "快速扫描",
        "prob_min": 0.55,
        "prob_max": 0.60,
        "position": "0%",
        "action": "AI拉基本面快照",
        "color": "#17a2b8",
    },
    {
        "level": "L2",
        "name": "中度研究",
        "prob_min": 0.60,
        "prob_max": 0.65,
        "position": "1-3%",
        "action": "@估值 / @护城河",
        "color": "#28a745",
    },
    {
        "level": "L3",
        "name": "深度研报",
        "prob_min": 0.65,
        "prob_max": 0.70,
        "position": "5-8%",
        "action": "@分析 [公司] 全套",
        "color": "#ffc107",
    },
    {
        "level": "L5",
        "name": "买方决策",
        "prob_min": 0.70,
        "prob_max": 0.80,
        "position": "10-15%",
        "action": "@L5 CIO备忘录",
        "color": "#fd7e14",
    },
    {
        "level": "HEAVY",
        "name": "重仓加码",
        "prob_min": 0.80,
        "prob_max": 1.00,
        "position": "20-25%",
        "action": "@L6 沙盘 + @辩论",
        "color": "#dc3545",
    },
]

# ---------------------------------------------------------------------------
# 技术革命框架常量
# ---------------------------------------------------------------------------

TECH_STAGES = {
    "irruption": "导入期 — 新技术喷涌",
    "frenzy": "狂热期 — 泡沫膨胀",
    "turning": "转折点 — 泡沫破裂",
    "synergy": "协同期 — 黄金时代",
    "maturity": "成熟期 — 增长放缓",
}

TECH_CATALYSTS = [
    "技术可行性验证（10倍性能飞跃）",
    "规模化量产能力建成",
    "业绩持续超预期（连续beat）",
]

# ---------------------------------------------------------------------------
# 信号类型
# ---------------------------------------------------------------------------

SIGNAL_TYPES = {
    "product_intuition": "🎮 产品直觉 — 作为用户感受到的产品力",
    "reading_insight": "📚 阅读洞察 — 高质量文章中发现的拐点",
    "data_anomaly": "📊 数据异常 — 日报中出现的异常指标",
    "social_signal": "👥 社交信号 — 行业朋友/专家的一手信息",
    "framework_deduction": "🧠 框架推演 — 技术革命框架推导出的机会",
}

# ---------------------------------------------------------------------------
# 遗憾根因
# ---------------------------------------------------------------------------

REGRET_ROOT_CAUSES = {
    "no_capture": "❌ 没有信号捕获 — 感知到了但没记录",
    "no_track": "📭 没有持续跟踪 — 捕获了但没跟进",
    "no_research": "🔍 没有深度研究 — 跟踪了但没升级分析",
    "no_position": "😰 犹豫没建仓 — 研究了但没下手",
    "too_light": "🪶 仓位太轻 — 建仓了但份量不够",
}

# ---------------------------------------------------------------------------
# 常用标的关键词映射（信号捕获自动匹配用）
# ---------------------------------------------------------------------------

KEYWORD_TICKER_MAP = {
    # AI / 半导体
    "nvidia": "NVDA", "英伟达": "NVDA", "显卡": "NVDA", "gpu": "NVDA",
    "cuda": "NVDA", "4090": "NVDA", "h100": "NVDA", "b200": "NVDA",
    "amd": "AMD", "mi300": "AMD",
    "tsmc": "TSM", "台积电": "TSM",
    "asml": "ASML", "光刻机": "ASML",
    "micron": "MU", "hbm": "MU", "内存": "MU",
    "broadcom": "AVGO", "博通": "AVGO",
    "arm": "ARM",
    # 大科技
    "google": "GOOGL", "谷歌": "GOOGL", "gemini": "GOOGL",
    "apple": "AAPL", "苹果": "AAPL", "iphone": "AAPL",
    "microsoft": "MSFT", "微软": "MSFT", "azure": "MSFT",
    "amazon": "AMZN", "亚马逊": "AMZN", "aws": "AMZN",
    "meta": "META", "facebook": "META",
    "tesla": "TSLA", "特斯拉": "TSLA", "robotaxi": "TSLA",
    # 中国科技
    "腾讯": "0700.HK", "tencent": "0700.HK", "微信": "0700.HK",
    "阿里": "9988.HK", "alibaba": "9988.HK",
    "比亚迪": "1211.HK", "byd": "1211.HK",
    "泡泡玛特": "9992.HK", "pop mart": "9992.HK",
    # 能源
    "中海油": "0883.HK", "cnooc": "0883.HK",
    # 其他
    "uber": "UBER", "比特币": "BTC-USD", "bitcoin": "BTC-USD",
}
