#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "10-研究报告输出"


def now_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def safe_name(text: str) -> str:
    banned = "\\/:*?\"<>|"
    out = "".join("_" if c in banned else c for c in text.strip())
    out = out.replace(" ", "_")
    return out or "未命名"


def run_python_script(script: str, args: list[str]) -> tuple[int, str, str]:
    script_path = ROOT / script
    if not script_path.exists():
        return 2, "", f"脚本不存在: {script_path}"

    proc = subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _try_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.{digits}f}"


def _fmt_pct(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.{digits}f}%"


def fetch_valuation_snapshot(symbol: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "symbol": symbol,
        "as_of": now_ts(),
        "source": [],
        "price": None,
        "pe": None,
        "pb": None,
        "roe": None,
        "dividend_yield": None,
        "pr": None,
        "g_star": None,
        "market_cap": None,
        "revenue_growth": None,
        "earnings_growth": None,
        "gross_margin": None,
        "operating_margin": None,
        "debt_to_equity": None,
        "current_ratio": None,
        "warnings": [],
    }

    try:
        import yfinance as yf

        t = yf.Ticker(symbol)
        info = t.info or {}
        result["price"] = _try_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        result["pe"] = _try_float(info.get("trailingPE") or info.get("forwardPE"))
        result["pb"] = _try_float(info.get("priceToBook"))
        result["market_cap"] = _try_float(info.get("marketCap"))

        roe_raw = _try_float(info.get("returnOnEquity"))
        if roe_raw is not None and abs(roe_raw) > 1:
            roe_raw = roe_raw / 100.0
        result["roe"] = roe_raw

        dy = _try_float(info.get("dividendYield"))
        if dy is not None and abs(dy) > 1:
            dy = dy / 100.0
        result["dividend_yield"] = dy
        result["revenue_growth"] = _try_float(info.get("revenueGrowth"))
        result["earnings_growth"] = _try_float(info.get("earningsGrowth"))
        result["gross_margin"] = _try_float(info.get("grossMargins"))
        result["operating_margin"] = _try_float(info.get("operatingMargins"))
        result["debt_to_equity"] = _try_float(info.get("debtToEquity"))
        result["current_ratio"] = _try_float(info.get("currentRatio"))
        result["source"].append("yfinance")
    except Exception as exc:
        result["warnings"].append(f"yfinance 拉取失败: {exc}")

    pe = result["pe"]
    roe = result["roe"]
    dy = result["dividend_yield"] or 0.0
    if pe is not None and pe > 0 and roe is not None and roe > 0:
        result["pr"] = pe / (roe * 100)
    if pe is not None and pe > 0:
        result["g_star"] = (1 / pe) - dy

    if result["pe"] is None or result["roe"] is None:
        result["warnings"].append("关键估值字段缺失（PE/ROE），建议补充 akshare 或手工核验。")

    return result


def valuation_markdown(snapshot: dict[str, Any]) -> str:
    lines = [
        "## 数据快照（自动生成）",
        "",
        f"- 标的：{snapshot['symbol']}",
        f"- 获取时间：{snapshot['as_of']}",
        f"- 数据源：{', '.join(snapshot['source']) if snapshot['source'] else 'N/A'}",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| Price | {_fmt_num(snapshot['price'])} |",
        f"| PE | {_fmt_num(snapshot['pe'])} |",
        f"| PB | {_fmt_num(snapshot['pb'])} |",
        f"| Market Cap | {_fmt_num(snapshot['market_cap'])} |",
        f"| ROE | {_fmt_pct(snapshot['roe'])} |",
        f"| Revenue Growth | {_fmt_pct(snapshot['revenue_growth'])} |",
        f"| Earnings Growth | {_fmt_pct(snapshot['earnings_growth'])} |",
        f"| Gross Margin | {_fmt_pct(snapshot['gross_margin'])} |",
        f"| Operating Margin | {_fmt_pct(snapshot['operating_margin'])} |",
        f"| Debt/Equity | {_fmt_num(snapshot['debt_to_equity'])} |",
        f"| Current Ratio | {_fmt_num(snapshot['current_ratio'])} |",
        f"| Dividend Yield | {_fmt_pct(snapshot['dividend_yield'])} |",
        f"| 市赚率 PR = PE / (ROE×100) | {_fmt_num(snapshot['pr'], 3)} |",
        f"| 盈亏平衡增长率 g* = 1/PE - d | {_fmt_pct(snapshot['g_star'])} |",
        "",
    ]

    warnings = snapshot.get("warnings", [])
    if warnings:
        lines.append("### 数据告警")
        lines.extend(f"- {w}" for w in warnings)
        lines.append("")

    return "\n".join(lines)


def write_file(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _score_qgpr(snapshot: dict[str, Any]) -> dict[str, Any]:
    roe = snapshot.get("roe")
    gross_margin = snapshot.get("gross_margin")
    op_margin = snapshot.get("operating_margin")
    debt_to_equity = snapshot.get("debt_to_equity")
    rev_g = snapshot.get("revenue_growth")
    earn_g = snapshot.get("earnings_growth")
    pe = snapshot.get("pe")
    pb = snapshot.get("pb")
    pr = snapshot.get("pr")

    q = 50.0
    if roe is not None:
        q += (roe - 0.10) * 220
    if gross_margin is not None:
        q += (gross_margin - 0.35) * 80
    if op_margin is not None:
        q += (op_margin - 0.12) * 80
    if debt_to_equity is not None:
        q -= max(0.0, debt_to_equity - 120.0) * 0.08
    q = _clamp(q)

    g = 50.0
    if rev_g is not None:
        g += (rev_g - 0.10) * 180
    if earn_g is not None:
        g += (earn_g - 0.10) * 140
    g = _clamp(g)

    p = 50.0
    if pr is not None:
        p += (1.1 - pr) * 30
    if pe is not None:
        p -= max(0.0, pe - 28.0) * 1.2
    if pb is not None:
        p -= max(0.0, pb - 6.0) * 3.0
    p = _clamp(p)

    r = 65.0
    if debt_to_equity is not None:
        r -= max(0.0, debt_to_equity - 100.0) * 0.1
    if snapshot.get("warnings"):
        r -= min(15, len(snapshot.get("warnings", [])) * 4)
    if earn_g is not None and earn_g < 0:
        r -= 8
    r = _clamp(r)

    total = round(0.32 * q + 0.28 * g + 0.20 * p + 0.20 * r, 1)
    return {
        "Q": round(q, 1),
        "G": round(g, 1),
        "P": round(p, 1),
        "R": round(r, 1),
        "Total": total,
    }


def _rating_by_total(total: float) -> str:
    if total >= 80:
        return "A（高确定性）"
    if total >= 70:
        return "B（可跟踪建仓）"
    if total >= 60:
        return "C（观察）"
    return "D（回避）"


def _find_latest_for_symbol(symbol: str, keyword: str) -> Path | None:
    symbol_safe = safe_name(symbol)
    candidates = sorted(
        OUTPUT_DIR.glob(f"*-{symbol_safe}-*{keyword}*.md"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return candidates[0] if candidates else None


def generate_moat_report(symbol: str) -> Path:
    ensure_output_dir()
    s = fetch_valuation_snapshot(symbol)
    out = OUTPUT_DIR / f"{now_date()}-护城河-{safe_name(symbol)}-自动评估.md"
    moat_score = 45.0
    if s.get("gross_margin") is not None:
        moat_score += (s["gross_margin"] - 0.35) * 90
    if s.get("operating_margin") is not None:
        moat_score += (s["operating_margin"] - 0.12) * 70
    if s.get("roe") is not None:
        moat_score += (s["roe"] - 0.12) * 120
    moat_score = round(_clamp(moat_score), 1)
    confidence = "60-75%" if not s.get("warnings") else "45-65%"

    content = "\n".join(
        [
            f"# 护城河评估：{symbol}",
            "",
            f"- 生成时间：{now_ts()}",
            f"- 护城河综合评分：{moat_score}/100",
            f"- 置信区间：{confidence}",
            "",
            valuation_markdown(s),
            "## 巴菲特式五维检查",
            "| 维度 | 判断 | 证据 |",
            "|---|---|---|",
            f"| 规模/网络效应 | {'偏强' if (s.get('market_cap') or 0) > 2e11 else '中性'} | Market Cap |",
            f"| 成本优势 | {'偏强' if (s.get('gross_margin') or 0) > 0.45 else '中性'} | Gross Margin |",
            f"| 品牌/粘性 | {'偏强' if (s.get('roe') or 0) > 0.15 else '中性'} | ROE |",
            f"| 切换成本 | {'偏强' if (s.get('operating_margin') or 0) > 0.20 else '中性'} | Operating Margin |",
            f"| 资本回报持续性 | {'偏强' if (s.get('roe') or 0) > 0.18 else '待验证'} | ROE |",
            "",
            "## 可证伪条件",
            "- 若未来 2-3 个季度 ROE 连续跌破 10%，则护城河结论降级。",
            "- 若毛利率显著下行并伴随份额流失，说明竞争壁垒在削弱。",
            "",
        ]
    )
    return write_file(out, content)


def generate_score_report(symbol: str) -> Path:
    ensure_output_dir()
    s = fetch_valuation_snapshot(symbol)
    score = _score_qgpr(s)
    out = OUTPUT_DIR / f"{now_date()}-打分-{safe_name(symbol)}-QGPR.md"
    rating = _rating_by_total(score["Total"])

    content = "\n".join(
        [
            f"# Q-G-P-R 打分：{symbol}",
            "",
            f"- 生成时间：{now_ts()}",
            f"- 总分：**{score['Total']} / 100**",
            f"- 评级：{rating}",
            "",
            valuation_markdown(s),
            "## 分项评分",
            "| 维度 | 分数 | 解释 |",
            "|---|---:|---|",
            f"| Q（质量） | {score['Q']} | ROE/利润率/杠杆 |",
            f"| G（成长） | {score['G']} | 营收与盈利增长 |",
            f"| P（价格） | {score['P']} | PE/PB/PR 估值压力 |",
            f"| R（风险） | {score['R']} | 杠杆、数据告警、盈利波动 |",
            "",
            "## 结论",
            "- 该分数用于排序与跟踪，不替代完整尽调。",
            "- 若总分<60，默认降级为观察；若总分>80，可进入 L5 深化。",
            "",
        ]
    )
    return write_file(out, content)


def generate_scenario_report(symbol: str) -> Path:
    ensure_output_dir()
    s = fetch_valuation_snapshot(symbol)
    out = OUTPUT_DIR / f"{now_date()}-情景-{safe_name(symbol)}-TSR分解.md"

    pe = s.get("pe") or 20.0
    dy = s.get("dividend_yield") or 0.0
    base_g = s.get("earnings_growth")
    if base_g is None:
        base_g = s.get("revenue_growth") or 0.10

    scenarios = [
        ("牛市", 0.25, max(base_g + 0.06, 0.12), pe * 1.20),
        ("基准", 0.50, max(base_g, 0.08), pe),
        ("熊市", 0.20, max(base_g - 0.06, -0.02), pe * 0.82),
        ("黑天鹅", 0.05, min(base_g - 0.15, -0.08), pe * 0.62),
    ]

    rows = []
    expected = 0.0
    for name, p, g, pe_next in scenarios:
        pe_change = (pe_next / pe) - 1 if pe > 0 else 0.0
        tsr = g + dy + pe_change
        expected += p * tsr
        rows.append((name, p, g, dy, pe_change, tsr))

    lines = [
        f"# 情景分析：{symbol}",
        "",
        f"- 生成时间：{now_ts()}",
        f"- 期望年化 TSR（概率加权）：{_fmt_pct(expected)}",
        "",
        valuation_markdown(s),
        "## TSR 分解（TSR = g + d + ΔPE）",
        "| 情景 | 概率 | g | d | ΔPE | TSR |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, p, g, d, dpe, tsr in rows:
        lines.append(
            f"| {name} | {p:.0%} | {_fmt_pct(g)} | {_fmt_pct(d)} | {_fmt_pct(dpe)} | {_fmt_pct(tsr)} |"
        )

    lines.extend(
        [
            "",
            "## 触发信号",
            "- 牛市触发：盈利增速与利润率同步上修，且估值扩张。",
            "- 熊市触发：盈利指引下修或行业景气拐头。",
            "- 黑天鹅触发：监管/产品/诉讼等非线性冲击。",
            "",
        ]
    )
    return write_file(out, "\n".join(lines))


def generate_trap_report(symbol: str) -> Path:
    ensure_output_dir()
    s = fetch_valuation_snapshot(symbol)
    out = OUTPUT_DIR / f"{now_date()}-陷阱-{safe_name(symbol)}-六类检查.md"

    pe = s.get("pe")
    roe = s.get("roe")
    dte = s.get("debt_to_equity")
    rev_g = s.get("revenue_growth")
    earn_g = s.get("earnings_growth")

    checks = [
        ("倍数幻觉", "警告" if (pe is not None and pe > 55 and (earn_g or 0) < 0.15) else "通过", "高估值但盈利兑现不足"),
        ("杠杆驱动", "警告" if (dte is not None and dte > 220) else "通过", "Debt/Equity 过高"),
        ("伪成长", "警告" if (rev_g is not None and earn_g is not None and rev_g > 0 and earn_g < 0) else "通过", "收入增但利润不增"),
        ("深度价值陷阱", "警告" if (pe is not None and pe < 10 and (roe or 0) < 0.08) else "通过", "低估值但低回报"),
        ("并表型增长", "待核验", "需少数股东权益与并购拆解数据"),
        ("单一依赖", "待核验", "需客户/产品集中度数据"),
    ]

    triggered = [name for name, state, _ in checks if state == "警告"]
    status = "观察" if triggered else "可继续"

    lines = [
        f"# 六类负范式陷阱检查：{symbol}",
        "",
        f"- 生成时间：{now_ts()}",
        f"- 当前结论：{status}",
        f"- 已触发：{', '.join(triggered) if triggered else '无'}",
        "",
        valuation_markdown(s),
        "## 检查明细",
        "| 陷阱 | 状态 | 依据 |",
        "|---|---|---|",
    ]
    for name, state, reason in checks:
        lines.append(f"| {name} | {state} | {reason} |")

    lines.extend(
        [
            "",
            "## Kill-Switch 建议",
            "- 若触发 ≥2 项警告，建议降级为‘观察’并降低仓位。",
            "- 待核验项未补齐前，不给出高置信度结论。",
            "",
        ]
    )
    return write_file(out, "\n".join(lines))


def generate_l5_report(symbol: str) -> Path:
    ensure_output_dir()
    s = fetch_valuation_snapshot(symbol)
    score = _score_qgpr(s)
    out = OUTPUT_DIR / f"{now_date()}-个股-{safe_name(symbol)}-L5决策备忘录-路由版.md"
    content = "\n".join(
        [
            f"# L5 决策备忘录（路由版）：{symbol}",
            "",
            f"- 生成时间：{now_ts()}",
            f"- QGPR 总分：{score['Total']}（{_rating_by_total(score['Total'])}）",
            "- 目标：聚焦 Key Variable、赔率、仓位与触发器",
            "",
            valuation_markdown(s),
            "## Key Variables（关键变量）",
            "1. 盈利增速是否持续高于市场隐含 g*",
            "2. 资本回报率（ROE/ROIC proxy）是否保持高位",
            "3. 估值再定价路径（PE 变化）",
            "",
            "## UE 模型推演（待填）",
            "- CAC：",
            "- LTV：",
            "- LTV/CAC：",
            "- 单位毛利/单店回收周期：",
            "",
            "## 敏感性测试（1% 变动影响）",
            "| 变量 | 方向 | 对估值影响 |",
            "|---|---|---:|",
            "| 盈利增速 g | +1% |  |",
            "| 折现率 r | +1% |  |",
            "| 终值倍数 | +1x |  |",
            "",
            "## 仓位与执行",
            "- 初始仓位：",
            "- 加仓触发：",
            "- 减仓/退出触发：",
            "",
        ]
    )
    return write_file(out, content)


def generate_l6_report(symbol: str) -> Path:
    ensure_output_dir()
    s = fetch_valuation_snapshot(symbol)
    l5_ref = _find_latest_for_symbol(symbol, "L5")
    out = OUTPUT_DIR / f"{now_date()}-个股-{safe_name(symbol)}-L6沙盘推演-路由版.md"

    lines = [
        f"# L6 沙盘推演（路由版）：{symbol}",
        "",
        f"- 生成时间：{now_ts()}",
        f"- L5 先验：{l5_ref if l5_ref else '未发现对应 L5 文件，建议先执行 @L5'}",
        "",
        valuation_markdown(s),
        "## 红蓝军对抗",
        "### 蓝军（做多）核心论点",
        "- 护城河与规模效应继续强化",
        "- 盈利增长可覆盖估值压力",
        "",
        "### 红军（做空）核心论点",
        "- 高估值透支未来 2-3 年兑现",
        "- 行业竞争/监管导致利润率下修",
        "",
        "## 战局推演（T+1 / T+3 / T+5）",
        "| 时点 | 关键矛盾 | 领先指标 | 触发动作 |",
        "|---|---|---|---|",
        "| T+1年 | 增长与估值匹配 | 增速/指引修订 | 调整仓位 |",
        "| T+3年 | 资本效率拐点 | ROE/FCF 转折 | 再平衡 |",
        "| T+5年 | 终局份额与回报 | 市占率与利润率 | 退出或长期持有 |",
        "",
        "## 末日协议（黑天鹅）",
        "- 风险阈值：单日/单周最大容忍回撤、基本面 Tripwire",
        "- 对冲方案：指数/行业对冲、仓位降杠杆",
        "",
        "## 执行兵法",
        "- 建仓：分三段，先小后大",
        "- 持仓：跟踪领先指标，触发式再评估",
        "- 退出：估值过热或逻辑证伪",
        "",
    ]
    return write_file(out, "\n".join(lines))


def generate_decision_log() -> Path:
    ensure_output_dir()
    path = OUTPUT_DIR / f"{now_date()}-投资决策日志.md"
    content = "\n".join(
        [
            f"# 投资决策日志（{now_date()}）",
            "",
            "## 今日观察",
            "- 市场状态：",
            "- 主要机会：",
            "- 主要风险：",
            "",
            "## 今日动作",
            "| 标的 | 动作 | 仓位变化 | 触发逻辑 | 可证伪条件 |",
            "|---|---|---:|---|---|",
            "|  |  |  |  |  |",
            "",
            "## 复盘",
            "- 做对了什么：",
            "- 做错了什么：",
            "- 明日关键跟踪：",
            "",
            "## Kill-Switch 检查",
            "- [ ] 数据缺失",
            "- [ ] 能力圈越界",
            "- [ ] 管理层红旗",
            "- [ ] 杠杆红线",
            "- [ ] 安全边际不足",
            "- [ ] 单一依赖",
            "- [ ] 全面共识",
            "",
        ]
    )
    return write_file(path, content)


def generate_valuation_report(symbol: str) -> Path:
    ensure_output_dir()
    symbol_safe = safe_name(symbol)
    out = OUTPUT_DIR / f"{now_date()}-估值-{symbol_safe}-自动快照.md"
    snapshot = fetch_valuation_snapshot(symbol)
    content = "\n".join(
        [
            f"# 估值快照报告：{symbol}",
            "",
            "本报告由 VS Code 非 Claude 路由器自动生成，用于快速校验估值与预期增长。",
            "",
            valuation_markdown(snapshot),
            "## 快速解读",
            "- 先看 PE、ROE、PR 三项是否匹配你的范式（质量复利/GARP/低估催化）。",
            "- 再看 g* 是否高于你对未来 3-5 年可持续增长的判断。",
            "- 若关键字段缺失或冲突，降级为“观察”，不要直接下结论。",
            "",
        ]
    )
    return write_file(out, content)


def generate_analysis_report(symbol: str) -> Path:
    ensure_output_dir()
    symbol_safe = safe_name(symbol)
    out = OUTPUT_DIR / f"{now_date()}-个股-{symbol_safe}-非Claude路由版.md"
    snapshot = fetch_valuation_snapshot(symbol)
    content = "\n".join(
        [
            f"# 个股研究草案：{symbol}",
            "",
            f"- 生成时间：{now_ts()}",
            "- 场景：S1 个股深度分析（非 Claude 路由器）",
            "- 默认深度：L2-L3 过渡版",
            "",
            "## 预检飞行清单",
            "- [ ] 能力圈检查",
            "- [ ] 数据可得性",
            "- [ ] 生命周期判断",
            "- [ ] 周期位置判断",
            "- [ ] 市场情绪快照",
            "- [ ] 信息质量评估",
            "- [ ] 历史报告回顾",
            "- [ ] 时间框架对齐",
            "",
            valuation_markdown(snapshot),
            "## 多框架分析矩阵（待补）",
            "| 维度 | 框架 | 核心结论 | 置信度 | 可证伪条件 |",
            "|---|---|---|---:|---|",
            "| 价值 | 三重估值/市赚率 |  |  |  |",
            "| 成长 | 10X Alpha/贝叶斯拐点 |  |  |  |",
            "| 宏观 | 周期/利率/信用 |  |  |  |",
            "",
            "## 情景分析",
            "| 情景 | 概率 | 关键假设 | 预期回报 | 触发信号 |",
            "|---|---:|---|---:|---|",
            "| 牛市 | 25% |  |  |  |",
            "| 基准 | 50% |  |  |  |",
            "| 熊市 | 20% |  |  |  |",
            "| 黑天鹅 | 5% |  |  |  |",
            "",
            "## Kill-Switch 结果",
            "- [ ] 数据缺失",
            "- [ ] 能力圈越界",
            "- [ ] 管理层红旗",
            "- [ ] 杠杆红线",
            "- [ ] 安全边际不足",
            "- [ ] 单一依赖",
            "- [ ] 全面共识",
            "",
            "## 结论（待补）",
            "- 评级：",
            "- 仓位建议：",
            "- 跟踪触发器：",
            "",
        ]
    )
    return write_file(out, content)


def generate_macro_snapshot() -> Path:
    ensure_output_dir()
    code, out, err = run_python_script("bond_data.py", ["--all"])
    path = OUTPUT_DIR / f"{now_date()}-宏观-债券快照-非Claude路由版.md"
    body = [
        f"# 宏观债券快照（{now_date()}）",
        "",
        f"- 生成时间：{now_ts()}",
        f"- 执行状态：{'成功' if code == 0 else '失败'}",
        "",
    ]
    if out:
        body.extend(["## bond_data.py 输出", "", "```text", out, "```", ""])
    if err:
        body.extend(["## 错误输出", "", "```text", err, "```", ""])
    if not out and not err:
        body.append("- 无输出，请手工检查 `bond_data.py`。")
    return write_file(path, "\n".join(body))


def run_idea_scan() -> str:
    code, out, err = run_python_script("stock_tracker.py", ["run-daily", "--news-limit", "8"])
    if code == 0:
        return out or "已执行 stock_tracker run-daily"
    return f"执行失败\nSTDOUT:\n{out}\n\nSTDERR:\n{err}"


@dataclass
class RouteResult:
    ok: bool
    message: str


def execute_query(query: str) -> RouteResult:
    tokens = shlex.split(query)
    if not tokens:
        return RouteResult(False, "空指令。示例：@分析 MSFT")

    cmd = tokens[0]
    arg = tokens[1] if len(tokens) > 1 else ""

    if cmd == "@宏观":
        path = generate_macro_snapshot()
        return RouteResult(True, f"已生成宏观快照：{path}")

    if cmd in {"@日志", "@决策日志"}:
        path = generate_decision_log()
        return RouteResult(True, f"已生成决策日志：{path}")

    if cmd in {"@估值", "@valuation"}:
        if not arg:
            return RouteResult(False, "缺少标的。示例：@估值 MSFT")
        path = generate_valuation_report(arg)
        return RouteResult(True, f"已生成估值快照：{path}")

    if cmd in {"@分析", "@analysis"}:
        if not arg:
            return RouteResult(False, "缺少标的。示例：@分析 GOOGL")
        path = generate_analysis_report(arg)
        return RouteResult(True, f"已生成分析草案：{path}")

    if cmd in {"@机会", "@扫描", "@watchlist"}:
        msg = run_idea_scan()
        return RouteResult(True, msg)

    if cmd in {"@护城河", "@moat"}:
        if not arg:
            return RouteResult(False, "缺少标的。示例：@护城河 MSFT")
        path = generate_moat_report(arg)
        return RouteResult(True, f"已生成护城河评估：{path}")

    if cmd in {"@打分", "@score"}:
        if not arg:
            return RouteResult(False, "缺少标的。示例：@打分 MSFT")
        path = generate_score_report(arg)
        return RouteResult(True, f"已生成QGPR打分：{path}")

    if cmd in {"@情景", "@scenario"}:
        if not arg:
            return RouteResult(False, "缺少标的。示例：@情景 MSFT")
        path = generate_scenario_report(arg)
        return RouteResult(True, f"已生成情景分析：{path}")

    if cmd in {"@陷阱", "@trap"}:
        if not arg:
            return RouteResult(False, "缺少标的。示例：@陷阱 MSFT")
        path = generate_trap_report(arg)
        return RouteResult(True, f"已生成陷阱检查：{path}")

    if cmd in {"@L5", "@l5"}:
        if not arg:
            return RouteResult(False, "缺少标的。示例：@L5 MSFT")
        path = generate_l5_report(arg)
        return RouteResult(True, f"已生成L5备忘录：{path}")

    if cmd in {"@L6", "@沙盘", "@推演", "@l6"}:
        if not arg:
            return RouteResult(False, "缺少标的。示例：@L6 MSFT")
        path = generate_l6_report(arg)
        return RouteResult(True, f"已生成L6沙盘推演：{path}")

    if cmd in {"@支持", "@help"}:
        supported = {
            "supported": [
                "@分析 [标的]",
                "@估值 [标的]",
                "@护城河 [标的]",
                "@打分 [标的]",
                "@情景 [标的]",
                "@陷阱 [标的]",
                "@L5 [标的]",
                "@L6 [标的]",
                "@宏观",
                "@日志",
                "@机会",
            ]
        }
        return RouteResult(True, json.dumps(supported, ensure_ascii=False, indent=2))

    return RouteResult(
        False,
        "不支持的指令。可用：@分析/@估值/@护城河/@打分/@情景/@陷阱/@L5/@L6/@宏观/@日志/@机会/@支持",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="VS Code 非 Claude 投研指令路由器")
    parser.add_argument("--query", required=True, help="例如：@分析 MSFT")
    args = parser.parse_args()

    ensure_output_dir()
    result = execute_query(args.query.strip())
    print(result.message)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
