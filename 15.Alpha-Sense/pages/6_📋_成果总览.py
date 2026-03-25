#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
📋 成果总览 — 所有环节的成果汇总与统计
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (
    TRACKER_DIR,
    SIGNALS_FILE,
    REGRETS_FILE,
    CONVICTION_LOG_FILE,
    WEEKLY_REVIEWS_DIR,
    REPORTS_DIR,
    DATA_DIR,
)
from core.signal_capture import get_signal_stats
from core.regret_engine import get_statistics as get_regret_stats
from core.conviction_ladder import get_upgrade_history
from core.weekly_review import list_past_reviews

st.set_page_config(page_title="📋 成果总览", page_icon="📋", layout="wide")

st.markdown("# 📋 成果总览")
st.markdown("**Alpha Sense 各环节的产出统计与成果列表**")
st.divider()

# ---------------------------------------------------------------------------
# 总览统计
# ---------------------------------------------------------------------------

# 各模块计数
signal_stats = get_signal_stats()
regret_stats = get_regret_stats()
upgrade_history = get_upgrade_history()
past_reviews = list_past_reviews()

# 追踪器
trackers_file = TRACKER_DIR / "data" / "trackers.json"
tracker_count = 0
tracker_data = []
if trackers_file.exists():
    try:
        data = json.loads(trackers_file.read_text(encoding="utf-8"))
        tracker_data = [v for v in data.get("trackers", {}).values() if v.get("active", True)]
        tracker_count = len(tracker_data)
    except Exception:
        pass

# 研报
report_count = 0
report_files = []
if REPORTS_DIR.exists():
    report_files = sorted(REPORTS_DIR.glob("*.md"), reverse=True)
    report_count = len(report_files)

st.markdown("### 🏆 系统总览")

m_cols = st.columns(6)
metrics = [
    ("📡 信号捕获", signal_stats.get("total", 0), "累计捕获的投资信号"),
    ("📊 贝叶斯追踪", tracker_count, "当前活跃追踪标的"),
    ("🪜 信念升级", len(upgrade_history), "已确认的阶梯升级事件"),
    ("😤 遗憾复盘", regret_stats.get("total", 0), "已复盘的遗憾案例"),
    ("📮 周度复盘", len(past_reviews), "已生成的 AI 周报"),
    ("📑 研究报告", report_count, "投研报告总数"),
]
for col, (label, value, help_text) in zip(m_cols, metrics):
    with col:
        st.metric(label, value, help=help_text)

st.divider()

# ---------------------------------------------------------------------------
# Phase 1: 信号捕获成果
# ---------------------------------------------------------------------------

st.markdown("### 📡 Phase 1 — 信号捕获成果")

if signal_stats.get("total", 0) > 0:
    scol1, scol2 = st.columns(2)
    with scol1:
        st.markdown("**按状态分布**")
        for status in ["new", "tracking", "researching", "positioned", "closed"]:
            count = signal_stats.get(status, 0)
            if count > 0:
                st.markdown(f"- `{status}`: **{count}** 条")

    with scol2:
        st.markdown("**按类型分布**")
        from config import SIGNAL_TYPES
        by_type = signal_stats.get("by_type", {})
        for t, c in by_type.items():
            label = SIGNAL_TYPES.get(t, t).split("—")[0].strip()
            st.markdown(f"- {label}: **{c}** 条")
else:
    st.info("暂无信号记录")

st.divider()

# ---------------------------------------------------------------------------
# Phase 2: 贝叶斯追踪成果
# ---------------------------------------------------------------------------

st.markdown("### 📊 Phase 2 — 贝叶斯追踪成果")

if tracker_data:
    import plotly.graph_objects as go

    tickers = [t.get("ticker", "") for t in tracker_data]
    probs = [t.get("current_probability", 0.5) for t in tracker_data]
    colors = []
    for p in probs:
        if p >= 0.75:
            colors.append("#dc3545")
        elif p >= 0.65:
            colors.append("#fd7e14")
        elif p >= 0.45:
            colors.append("#28a745")
        elif p >= 0.25:
            colors.append("#ffc107")
        else:
            colors.append("#6c757d")

    fig = go.Figure(data=[go.Bar(
        x=tickers, y=probs,
        marker_color=colors,
        text=[f"{p:.0%}" for p in probs],
        textposition="outside",
    )])
    fig.add_hline(y=0.75, line_dash="dot", line_color="red", annotation_text="买入线")
    fig.add_hline(y=0.25, line_dash="dot", line_color="gray", annotation_text="卖出线")
    fig.update_layout(
        height=350,
        yaxis=dict(title="后验概率", tickformat=".0%", range=[0, 1]),
        xaxis=dict(title=""),
        margin=dict(l=0, r=0, t=20, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    # 详情表
    st.markdown("**标的详情**")
    table_data = []
    for t in tracker_data:
        from core.conviction_ladder import get_stage
        stage = get_stage(t.get("current_probability", 0.5))
        table_data.append({
            "标的": t.get("ticker", ""),
            "概率": f"{t.get('current_probability', 0.5):.0%}",
            "阶段": f"{stage['level']} {stage['name']}",
            "建议仓位": stage["position"],
            "论点": t.get("thesis", "")[:40],
            "更新": t.get("updated_at", "")[:10],
        })
    st.dataframe(table_data, use_container_width=True)
else:
    st.info("暂无追踪标的")

st.divider()

# ---------------------------------------------------------------------------
# Phase 3: 信念阶梯成果
# ---------------------------------------------------------------------------

st.markdown("### 🪜 Phase 3 — 信念升级成果")

if upgrade_history:
    st.markdown(f"**累计升级事件: {len(upgrade_history)}**")
    for h in reversed(upgrade_history[-10:]):
        st.markdown(
            f"- **{h.get('timestamp', '')[:16]}** — "
            f"`{h.get('ticker', '')}` "
            f"{h.get('from_level', '')} → **{h.get('to_level', '')}** — "
            f"{h.get('reason', '')}"
        )
else:
    st.info("暂无升级记录")

st.divider()

# ---------------------------------------------------------------------------
# Phase 4: 遗憾复盘成果
# ---------------------------------------------------------------------------

st.markdown("### 😤 Phase 4 — 遗憾复盘成果")

if regret_stats.get("total", 0) > 0:
    rcol1, rcol2 = st.columns(2)
    with rcol1:
        st.metric("累计错过涨幅", f"{regret_stats.get('total_missed_return', 0):.0f}%")
        st.metric("平均错过", f"{regret_stats.get('avg_missed_return', 0):.1f}%")
    with rcol2:
        st.markdown("**根因分布**")
        from config import REGRET_ROOT_CAUSES
        for cause, count in regret_stats.get("by_root_cause", {}).items():
            label = REGRET_ROOT_CAUSES.get(cause, cause).split("—")[0].strip()
            st.markdown(f"- {label}: **{count}** 次")
else:
    st.info("暂无遗憾案例（好事！）")

st.divider()

# ---------------------------------------------------------------------------
# Phase 5: AI 猎手成果
# ---------------------------------------------------------------------------

st.markdown("### 🔭 Phase 5 — AI 猎手成果")

if past_reviews:
    st.markdown(f"**已生成 {len(past_reviews)} 份周报**")
    for r in past_reviews[:5]:
        s = r.get("summary", {})
        st.markdown(
            f"- **{r['week_end']}** — "
            f"追踪 {s.get('active_trackers', 0)} / "
            f"新信号 {s.get('new_signals_this_week', 0)} / "
            f"被忽略 {s.get('ignored_count', 0)}"
        )
else:
    st.info("尚未生成周报")

st.divider()

# ---------------------------------------------------------------------------
# 最近研报
# ---------------------------------------------------------------------------

st.markdown("### 📑 最近研究报告")

if report_files:
    for f in report_files[:10]:
        st.markdown(f"- 📄 `{f.name}`")
else:
    st.info("暂无研报输出")

st.divider()

# ---------------------------------------------------------------------------
# 数据导出
# ---------------------------------------------------------------------------

st.markdown("### 💾 数据导出")

if st.button("📦 导出系统数据摘要", use_container_width=True):
    export = {
        "exported_at": datetime.now().isoformat(),
        "signal_stats": signal_stats,
        "tracker_count": tracker_count,
        "upgrade_count": len(upgrade_history),
        "regret_stats": regret_stats,
        "weekly_reviews": len(past_reviews),
        "report_count": report_count,
    }
    st.json(export)
    st.download_button(
        "📥 下载 JSON",
        data=json.dumps(export, ensure_ascii=False, indent=2),
        file_name=f"alpha-sense-export-{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
    )
