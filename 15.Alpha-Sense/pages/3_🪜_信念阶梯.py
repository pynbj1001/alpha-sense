#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🪜 信念阶梯 — 6 级从信号到重仓的可视化管理
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import TRACKER_DIR, CONVICTION_LADDER
from core.conviction_ladder import (
    get_stage,
    get_all_positions,
    get_pending_upgrades,
    log_upgrade,
    get_upgrade_history,
    generate_entry_checklist,
)

st.set_page_config(page_title="🪜 信念阶梯", page_icon="🪜", layout="wide")

st.markdown("# 🪜 信念升级阶梯")
st.markdown("**从 L0 信号捕获到 HEAVY 重仓加码，每一步有明确的概率门槛和行动指引**")
st.divider()

# ---------------------------------------------------------------------------
# 加载追踪器数据
# ---------------------------------------------------------------------------

TRACKERS_FILE = TRACKER_DIR / "data" / "trackers.json"


def load_tracker_states() -> list[dict]:
    if not TRACKERS_FILE.exists():
        return []
    try:
        data = json.loads(TRACKERS_FILE.read_text(encoding="utf-8"))
        return [v for v in data.get("trackers", {}).values() if v.get("active", True)]
    except Exception:
        return []


states = load_tracker_states()

# ---------------------------------------------------------------------------
# 阶梯总览
# ---------------------------------------------------------------------------

st.markdown("### 📊 阶梯定义")

ladder_cols = st.columns(len(CONVICTION_LADDER))
for i, stage in enumerate(CONVICTION_LADDER):
    with ladder_cols[i]:
        # 计算此阶梯有多少标的
        count = sum(
            1 for s in states
            if get_stage(s.get("current_probability", 0.5))["level"] == stage["level"]
        )
        st.markdown(f"""
        <div style="text-align:center; padding:0.8rem; background:{stage['color']}22;
             border-radius:8px; border:2px solid {stage['color']};">
            <div style="font-weight:700; color:{stage['color']};">{stage['level']}</div>
            <div style="font-size:0.85rem; font-weight:600;">{stage['name']}</div>
            <div style="font-size:0.75rem; color:#aaa;">{stage['position']}</div>
            <div style="font-size:1.2rem; font-weight:700; margin-top:0.3rem;">{count}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# 标的阶梯分布
# ---------------------------------------------------------------------------

st.markdown("### 🎯 标的分布")

positions = get_all_positions(states)

if positions:
    import plotly.graph_objects as go

    level_order = [s["level"] for s in CONVICTION_LADDER]
    level_names = {s["level"]: s["name"] for s in CONVICTION_LADDER}
    level_colors = {s["level"]: s["color"] for s in CONVICTION_LADDER}

    fig = go.Figure()

    for pos in positions:
        level = pos["stage_level"]
        y_idx = level_order.index(level) if level in level_order else 0
        fig.add_trace(go.Scatter(
            x=[pos["probability"]],
            y=[f"{level} {level_names.get(level, '')}"],
            mode="markers+text",
            marker=dict(
                size=30,
                color=pos["color"],
                line=dict(width=2, color="white"),
            ),
            text=[pos["ticker"]],
            textposition="top center",
            textfont=dict(size=12, color="white"),
            showlegend=False,
            hovertext=f"{pos['ticker']}: {pos['probability']:.0%}<br>{pos['thesis'][:40]}",
        ))

    fig.update_layout(
        height=350,
        xaxis=dict(title="后验概率", tickformat=".0%", range=[0, 1]),
        yaxis=dict(
            categoryorder="array",
            categoryarray=[f"{s['level']} {s['name']}" for s in CONVICTION_LADDER],
        ),
        margin=dict(l=0, r=20, t=20, b=40),
    )

    # 添加阈值线
    for stage in CONVICTION_LADDER:
        if stage["prob_min"] > 0:
            fig.add_vline(
                x=stage["prob_min"],
                line_dash="dot",
                line_color=stage["color"],
                opacity=0.5,
            )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("暂无追踪标的")

st.divider()

# ---------------------------------------------------------------------------
# 待升级提醒
# ---------------------------------------------------------------------------

st.markdown("### ⚡ 待升级提醒")
st.markdown("*概率已跨越阶梯门槛但尚未确认升级的标的*")

pending = get_pending_upgrades(states)

if pending:
    for p in pending:
        with st.expander(
            f"🔔 **{p['ticker']}** — 概率 {p['probability']:.0%} → 建议 {p['stage_level']} {p['stage_name']}",
            expanded=True,
        ):
            st.markdown(f"**当前概率**: {p['probability']:.0%}")
            st.markdown(f"**建议仓位**: {p['position']}")
            st.markdown(f"**下一步行动**: {p['action']}")
            st.markdown(f"**投资论点**: {p.get('thesis', '')}")

            st.markdown("---")
            st.markdown("**📋 上车检查单（必须回答）**")
            answers = []
            for i, q in enumerate(p.get("checklist", [])):
                ans = st.text_area(q, key=f"checklist_{p['ticker']}_{i}", height=60)
                answers.append(ans)

            reason = st.text_input(
                "升级理由（一句话）",
                key=f"reason_{p['ticker']}",
                placeholder="例如：连续3个季度业绩beat，AI数据中心收入占比突破50%",
            )

            if st.button(f"✅ 确认升级 {p['ticker']} 到 {p['stage_level']}", key=f"upgrade_{p['ticker']}"):
                if reason:
                    log_upgrade(
                        ticker=p["ticker"],
                        from_level=p.get("last_logged_level", "L0"),
                        to_level=p["stage_level"],
                        old_prob=0,
                        new_prob=p["probability"],
                        reason=reason,
                        checklist_answers=answers,
                    )
                    st.success(f"✅ {p['ticker']} 已升级到 {p['stage_level']} {p['stage_name']}")
                    st.rerun()
                else:
                    st.warning("请填写升级理由")
else:
    st.success("✅ 所有标的阶梯状态已同步，无需升级")

st.divider()

# ---------------------------------------------------------------------------
# 升级历史
# ---------------------------------------------------------------------------

st.markdown("### 📜 升级历史")

history = get_upgrade_history()
if history:
    for h in reversed(history[-20:]):
        st.markdown(
            f"**{h.get('timestamp', '')[:16]}** — "
            f"`{h.get('ticker', '')}` "
            f"{h.get('from_level', '')} → **{h.get('to_level', '')}** — "
            f"{h.get('reason', '')}"
        )
else:
    st.info("暂无升级记录")
