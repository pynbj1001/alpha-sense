#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
机构级报告模板生成器

生成标准化的投研报告 Markdown，供 AI Agent 和 VS Code 路由器调用。
所有报告遵循：封面 → 执行摘要 → 数据 → 框架分析 → 风险 → 附录。
"""

from __future__ import annotations

import json
from datetime import datetime, date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "10-研究报告输出"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return date.today().isoformat()


def _safe_name(text: str) -> str:
    banned = '\\/:*?"<>|'
    return "".join("_" if c in banned else c for c in text.strip()).replace(" ", "_") or "未命名"


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 报告通用组件
# ---------------------------------------------------------------------------

def _header(
    title: str,
    subtitle: str = "",
    report_type: str = "投资研究报告",
    confidentiality: str = "仅供内部参考",
) -> str:
    """生成机构级报告封面"""
    lines = [
        f"# {title}",
        "",
        "---",
        "",
        f"| 项目 | 内容 |",
        f"|:-----|:-----|",
        f"| 报告类型 | {report_type} |",
        f"| 生成时间 | {_now()} |",
        f"| 分析师 | AI Agent (自动生成) |",
        f"| 密级 | {confidentiality} |",
    ]
    if subtitle:
        lines.append(f"| 备注 | {subtitle} |")
    lines.extend(["", "---", ""])
    return "\n".join(lines)


def _executive_summary(points: list[str]) -> str:
    """生成执行摘要（≤3句）"""
    lines = [
        "## 📋 执行摘要",
        "",
    ]
    for i, p in enumerate(points[:3], 1):
        lines.append(f"{i}. {p}")
    lines.append("")
    return "\n".join(lines)


def _data_sources(sources: list[str], date_str: str = "") -> str:
    """生成数据来源附录"""
    lines = [
        "---",
        "",
        "## 📎 附录：数据来源与免责",
        "",
        f"- **数据来源**：{', '.join(sources) if sources else 'N/A'}",
        f"- **数据日期**：{date_str or _today()}",
        "- **免责声明**：本报告由 AI 自动生成，基于公开数据和量化模型，不构成投资建议。",
        "  投资有风险，入市须谨慎。结论用概率区间表达，请结合个人风险承受能力决策。",
        "",
    ]
    return "\n".join(lines)


def _frameworks_used(frameworks: list[dict]) -> str:
    """生成使用的框架引用"""
    lines = [
        "## 🔬 分析框架引用",
        "",
        "| 框架 | 来源文件 | 核心贡献 |",
        "|:-----|:---------|:---------|",
    ]
    for fw in frameworks:
        lines.append(f"| {fw.get('name', '')} | {fw.get('source', '')} | {fw.get('contribution', '')} |")
    lines.append("")
    return "\n".join(lines)


def _risk_disclaimer(risks: list[str]) -> str:
    """生成风险提示"""
    lines = [
        "## ⚠️ 风险提示",
        "",
    ]
    for r in risks:
        lines.append(f"- {r}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 报告模板：个股研究报告
# ---------------------------------------------------------------------------

def generate_stock_research_report(
    ticker: str,
    snapshot_md: str = "",
    executive_summary: list[str] | None = None,
    frameworks: list[dict] | None = None,
    analysis_sections: list[dict] | None = None,
    risks: list[str] | None = None,
    recommendation: dict | None = None,
    sources: list[str] | None = None,
    save: bool = True,
) -> str:
    """
    生成机构级个股研究报告。

    参数:
        ticker: 股票代码
        snapshot_md: 数据快照的 Markdown（来自 data_toolkit）
        executive_summary: 执行摘要要点（≤3条）
        frameworks: 使用的框架列表 [{"name": ..., "source": ..., "contribution": ...}]
        analysis_sections: 分析段落 [{"title": ..., "content": ...}]
        risks: 风险提示列表
        recommendation: 投资建议 {"action": ..., "position": ..., "confidence": ..., "target": ...}
        sources: 数据来源列表
        save: 是否保存到文件

    返回:
        str: 完整报告 Markdown
    """
    parts = []

    # 封面
    parts.append(_header(
        title=f"个股深度研究：{ticker}",
        report_type="个股深度研究报告",
    ))

    # 执行摘要
    if executive_summary:
        parts.append(_executive_summary(executive_summary))

    # 投资建议
    if recommendation:
        rec_lines = [
            "## 💡 投资建议",
            "",
            "| 项目 | 内容 |",
            "|:-----|:-----|",
            f"| 行动 | **{recommendation.get('action', '待定')}** |",
            f"| 建议仓位 | {recommendation.get('position', 'N/A')} |",
            f"| 置信度 | {recommendation.get('confidence', 'N/A')} |",
            f"| 目标价 | {recommendation.get('target', 'N/A')} |",
            f"| 时间框架 | {recommendation.get('timeframe', '12个月')} |",
            "",
        ]
        parts.append("\n".join(rec_lines))

    # 数据快照
    if snapshot_md:
        parts.append(snapshot_md)

    # 分析段落
    if analysis_sections:
        for section in analysis_sections:
            parts.append(f"## {section.get('title', '分析')}")
            parts.append("")
            parts.append(section.get("content", ""))
            parts.append("")

    # 框架引用
    if frameworks:
        parts.append(_frameworks_used(frameworks))

    # 风险提示
    parts.append(_risk_disclaimer(risks or [
        "本报告基于历史数据和模型推算，过去表现不代表未来",
        "宏观环境变化可能导致基本面假设失效",
        "地缘政治风险可能导致短期剧烈波动",
    ]))

    # 数据来源
    parts.append(_data_sources(sources or ["yfinance"]))

    report = "\n".join(parts)

    if save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / f"{_today()}-个股-{_safe_name(ticker)}-AI深度研究.md"
        _write(path, report)

    return report


# ---------------------------------------------------------------------------
# 报告模板：宏观展望报告
# ---------------------------------------------------------------------------

def generate_macro_outlook_report(
    macro_md: str = "",
    cycle_positions: dict | None = None,
    executive_summary: list[str] | None = None,
    analysis_sections: list[dict] | None = None,
    allocation: dict | None = None,
    sources: list[str] | None = None,
    save: bool = True,
) -> str:
    """
    生成宏观展望报告。

    参数:
        macro_md: 宏观数据的 Markdown
        cycle_positions: 周期定位 {"kondratieff": ..., "kuznets": ..., "juglar": ..., "kitchin": ...}
        executive_summary: 执行摘要
        analysis_sections: 分析段落
        allocation: 配置建议 {"stocks": ..., "bonds": ..., "gold": ..., "cash": ...}
        sources: 数据来源
        save: 是否保存

    返回:
        str
    """
    parts = []

    parts.append(_header(
        title="宏观展望与资产配置建议",
        report_type="宏观策略报告",
    ))

    if executive_summary:
        parts.append(_executive_summary(executive_summary))

    # 周期仪表盘
    if cycle_positions:
        cp_lines = [
            "## ⏱️ 周期仪表盘",
            "",
            "| 周期 | 当前阶段 | 置信度 |",
            "|:-----|:---------|:-----:|",
        ]
        for cycle_name, info in cycle_positions.items():
            if isinstance(info, dict):
                cp_lines.append(f"| {cycle_name} | {info.get('phase', 'N/A')} | {info.get('confidence', 'N/A')} |")
            else:
                cp_lines.append(f"| {cycle_name} | {info} | — |")
        cp_lines.append("")
        parts.append("\n".join(cp_lines))

    if macro_md:
        parts.append(macro_md)

    if analysis_sections:
        for section in analysis_sections:
            parts.append(f"## {section.get('title', '分析')}")
            parts.append("")
            parts.append(section.get("content", ""))
            parts.append("")

    # 配置建议
    if allocation:
        alloc_lines = [
            "## 💼 资产配置建议",
            "",
            "| 资产类别 | 权重 | 逻辑 |",
            "|:---------|-----:|:-----|",
        ]
        for asset, info in allocation.items():
            if isinstance(info, dict):
                alloc_lines.append(f"| {asset} | {info.get('weight', 'N/A')} | {info.get('rationale', '')} |")
            else:
                alloc_lines.append(f"| {asset} | {info} | |")
        alloc_lines.append("")
        parts.append("\n".join(alloc_lines))

    parts.append(_data_sources(sources or ["yfinance"]))

    report = "\n".join(parts)

    if save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / f"{_today()}-宏观-AI展望报告.md"
        _write(path, report)

    return report


# ---------------------------------------------------------------------------
# 报告模板：策略筛选报告
# ---------------------------------------------------------------------------

def generate_strategy_screening_report(
    ticker: str,
    snapshot_md: str = "",
    screening_results: list[dict] | None = None,
    strategy_name: str = "乱世投资策略",
    recommendation: dict | None = None,
    sources: list[str] | None = None,
    save: bool = True,
) -> str:
    """
    生成策略筛选报告（用于乱世投资策略等的标的检验）。

    参数:
        ticker: 股票代码
        snapshot_md: 数据快照
        screening_results: 筛选关卡结果 [{"gate": ..., "result": "✅/❌", "finding": ...}]
        strategy_name: 策略名称
        recommendation: 综合建议
        sources: 数据来源
        save: 是否保存

    返回:
        str
    """
    parts = []

    parts.append(_header(
        title=f"{strategy_name}筛选：{ticker}",
        report_type="策略筛选报告",
    ))

    if snapshot_md:
        parts.append(snapshot_md)

    # 筛选结果
    if screening_results:
        sr_lines = [
            "## 🔍 七道关卡筛选结果",
            "",
            "| 关卡 | 结果 | 关键发现 |",
            "|:-----|:----:|:---------|",
        ]
        for sr in screening_results:
            sr_lines.append(f"| {sr.get('gate', '')} | {sr.get('result', '—')} | {sr.get('finding', '')} |")
        sr_lines.append("")

        passed = sum(1 for sr in screening_results if sr.get("result") == "✅")
        total = len(screening_results)
        sr_lines.append(f"**通过率：{passed}/{total}**")
        sr_lines.append("")
        parts.append("\n".join(sr_lines))

    # 综合建议
    if recommendation:
        rec_lines = [
            "## 💡 综合建议",
            "",
            "| 项目 | 内容 |",
            "|:-----|:-----|",
            f"| 行动 | **{recommendation.get('action', '待定')}** |",
            f"| 建议仓位 | {recommendation.get('position', 'N/A')} |",
            f"| 置信度 | {recommendation.get('confidence', 'N/A')} |",
            "",
        ]
        if recommendation.get("rationale"):
            rec_lines.append(f"**理由**：{recommendation['rationale']}")
            rec_lines.append("")
        parts.append("\n".join(rec_lines))

    parts.append(_risk_disclaimer([
        "本筛选基于量化指标和框架规则，不替代完整尽调",
        "策略标准可能在极端市场环境下失效",
        "结论用概率区间表达，禁用绝对化措辞",
    ]))

    parts.append(_data_sources(sources or ["yfinance"]))

    report = "\n".join(parts)

    if save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / f"{_today()}-筛选-{_safe_name(ticker)}-{_safe_name(strategy_name)}.md"
        _write(path, report)

    return report


# ---------------------------------------------------------------------------
# 报告模板：组合审视报告
# ---------------------------------------------------------------------------

def generate_portfolio_review_report(
    holdings: list[dict],
    allocation_analysis: dict | None = None,
    executive_summary: list[str] | None = None,
    rebalance_suggestions: list[str] | None = None,
    sources: list[str] | None = None,
    save: bool = True,
) -> str:
    """
    生成组合审视报告。

    参数:
        holdings: 持仓列表 [{"ticker": ..., "weight": ..., "pnl": ..., "notes": ...}]
        allocation_analysis: 配置分析
        executive_summary: 执行摘要
        rebalance_suggestions: 再平衡建议
        sources: 数据来源
        save: 是否保存

    返回:
        str
    """
    parts = []

    parts.append(_header(
        title="投资组合定期审视报告",
        report_type="组合管理报告",
    ))

    if executive_summary:
        parts.append(_executive_summary(executive_summary))

    # 持仓明细
    if holdings:
        h_lines = [
            "## 📊 当前持仓",
            "",
            "| 标的 | 权重 | 盈亏 | 备注 |",
            "|:-----|-----:|-----:|:-----|",
        ]
        for h in holdings:
            h_lines.append(
                f"| {h.get('ticker', '')} "
                f"| {h.get('weight', 'N/A')} "
                f"| {h.get('pnl', 'N/A')} "
                f"| {h.get('notes', '')} |"
            )
        h_lines.append("")
        parts.append("\n".join(h_lines))

    # 配置分析
    if allocation_analysis:
        aa_lines = [
            "## 📋 配置分析",
            "",
        ]
        for key, val in allocation_analysis.items():
            aa_lines.append(f"- **{key}**：{val}")
        aa_lines.append("")
        parts.append("\n".join(aa_lines))

    # 再平衡建议
    if rebalance_suggestions:
        rb_lines = [
            "## 🔄 再平衡建议",
            "",
        ]
        for i, s in enumerate(rebalance_suggestions, 1):
            rb_lines.append(f"{i}. {s}")
        rb_lines.append("")
        parts.append("\n".join(rb_lines))

    parts.append(_data_sources(sources or ["yfinance"]))

    report = "\n".join(parts)

    if save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / f"{_today()}-组合-定期审视报告.md"
        _write(path, report)

    return report
