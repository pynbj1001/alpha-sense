#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
行业 LR 模板库 — 四大行业似然比校准参数

为贝叶斯追踪器提供按行业预设的似然比(Likelihood Ratio)模板，
使概率更新更精确、更贴合行业特性。
"""

from __future__ import annotations

LR_TEMPLATES: dict[str, dict] = {
    "ai_semiconductor": {
        "name": "AI / 半导体",
        "icon": "🤖",
        "tickers": ["NVDA", "AMD", "TSM", "ASML", "MU", "AVGO", "ARM", "INTC"],
        "signals": {
            "earnings_beat": {"lr": 1.30, "desc": "业绩超预期（EPS beat ≥5%）"},
            "earnings_miss": {"lr": 0.75, "desc": "业绩不及预期"},
            "guidance_raise": {"lr": 1.25, "desc": "上调前瞻指引"},
            "guidance_cut": {"lr": 0.70, "desc": "下调前瞻指引"},
            "new_product_launch": {"lr": 1.15, "desc": "重大新品发布"},
            "design_win": {"lr": 1.25, "desc": "获得重要客户设计导入"},
            "supply_bottleneck": {"lr": 0.85, "desc": "供应链瓶颈/产能受限"},
            "customer_concentration": {"lr": 0.80, "desc": "客户集中度风险暴露"},
            "capex_cycle_peak": {"lr": 0.90, "desc": "行业资本开支周期见顶"},
            "export_restriction": {"lr": 0.80, "desc": "出口管制/地缘限制"},
            "data_center_demand": {"lr": 1.20, "desc": "数据中心需求加速"},
            "inventory_correction": {"lr": 0.85, "desc": "库存修正周期开始"},
        },
    },
    "consumer": {
        "name": "消费品",
        "icon": "🛒",
        "tickers": ["9992.HK", "PDD", "LULU", "NKE", "SBUX"],
        "signals": {
            "sssg_beat": {"lr": 1.25, "desc": "同店增长超预期"},
            "sssg_miss": {"lr": 0.80, "desc": "同店增长不及预期"},
            "channel_expansion": {"lr": 1.10, "desc": "渠道/门店快速扩张"},
            "brand_momentum": {"lr": 1.15, "desc": "品牌势能/社交媒体热度增强"},
            "competitor_entry": {"lr": 0.80, "desc": "强力竞品入侵"},
            "consumer_downgrade": {"lr": 0.85, "desc": "消费降级趋势"},
            "pricing_power": {"lr": 1.20, "desc": "展现定价权（提价不掉量）"},
            "margin_expansion": {"lr": 1.15, "desc": "利润率扩张"},
        },
    },
    "energy_cyclical": {
        "name": "能源 / 周期",
        "icon": "⛽",
        "tickers": ["0883.HK", "XOM", "CVX", "SLB"],
        "signals": {
            "commodity_breakout": {"lr": 1.20, "desc": "大宗商品突破关键价位"},
            "commodity_collapse": {"lr": 0.80, "desc": "大宗商品价格暴跌"},
            "inventory_anomaly": {"lr": 1.15, "desc": "库存数据意外下降"},
            "capex_discipline": {"lr": 1.15, "desc": "行业资本纪律改善"},
            "policy_shift": {"lr": 0.90, "desc": "能源政策风向变化"},
            "opec_cut": {"lr": 1.15, "desc": "OPEC减产"},
            "demand_surge": {"lr": 1.20, "desc": "需求端超预期增长"},
            "geopolitical_risk": {"lr": 1.10, "desc": "地缘风险推升溢价"},
        },
    },
    "macro_fx": {
        "name": "宏观 / 外汇",
        "icon": "🌐",
        "tickers": ["USDJPY", "DXY", "TLT", "GLD"],
        "signals": {
            "spread_widening": {"lr": 1.20, "desc": "利差走阔"},
            "spread_tightening": {"lr": 0.85, "desc": "利差收窄"},
            "central_bank_pivot": {"lr": 1.25, "desc": "央行政策转向"},
            "vix_spike": {"lr": 0.85, "desc": "VIX飙升（恐慌升温）"},
            "vix_collapse": {"lr": 1.10, "desc": "VIX回落（风险偏好修复）"},
            "liquidity_injection": {"lr": 1.15, "desc": "流动性注入"},
            "liquidity_drain": {"lr": 0.85, "desc": "流动性收缩"},
            "recession_signal": {"lr": 0.80, "desc": "衰退信号出现"},
        },
    },
}


def get_template_for_ticker(ticker: str) -> dict | None:
    """根据 ticker 自动匹配行业 LR 模板"""
    ticker_upper = ticker.upper()
    for _key, tmpl in LR_TEMPLATES.items():
        if ticker_upper in tmpl["tickers"]:
            return tmpl
    return None


def get_all_industries() -> list[dict]:
    """返回所有行业摘要"""
    return [
        {"key": k, "name": v["name"], "icon": v["icon"], "signal_count": len(v["signals"])}
        for k, v in LR_TEMPLATES.items()
    ]
