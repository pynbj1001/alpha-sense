#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
😤 遗憾复盘 — 系统化追踪"看对了但没赚到"的案例
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import REGRET_ROOT_CAUSES
from core.regret_engine import add_regret, list_regrets, get_statistics

st.set_page_config(page_title="😤 遗憾复盘", page_icon="😤", layout="wide")

st.markdown("# 😤 遗憾复盘")
st.markdown('**把"看对了但没赚到"的痛转化为下一次的行动力**')
st.divider()

# ---------------------------------------------------------------------------
# 新增遗憾
# ---------------------------------------------------------------------------

st.markdown("### 📝 录入遗憾案例")

with st.form("regret_form"):
    fcol1, fcol2 = st.columns(2)
    with fcol1:
        ticker = st.text_input("标的代码", placeholder="NVDA")
        company_name = st.text_input("公司名称", placeholder="英伟达")
        first_noticed = st.date_input("最早感知时间")
    with fcol2:
        price_at_notice = st.number_input("当时价格", min_value=0.0, step=0.01)
        current_price_input = st.number_input(
            "当前价格 (留空自动获取)", min_value=0.0, step=0.01, value=0.0,
        )
        root_cause = st.selectbox(
            "根本原因",
            options=list(REGRET_ROOT_CAUSES.keys()),
            format_func=lambda k: REGRET_ROOT_CAUSES[k],
        )

    narrative = st.text_area(
        "故事描述 — 当时发生了什么？你想了什么？",
        placeholder="例如：2023年初买了4090显卡，性能惊人，明知AI需求爆炸但没买NVDA股票...",
        height=100,
    )

    submitted = st.form_submit_button("😤 录入遗憾", type="primary", use_container_width=True)

    if submitted:
        if not ticker or not company_name or price_at_notice <= 0:
            st.error("请填写标的代码、公司名称和当时价格")
        else:
            case = add_regret(
                ticker=ticker.strip().upper(),
                company_name=company_name.strip(),
                first_noticed=first_noticed.strftime("%Y-%m-%d"),
                price_at_notice=price_at_notice,
                root_cause=root_cause,
                narrative=narrative,
                current_price=current_price_input if current_price_input > 0 else None,
            )
            st.success(
                f"✅ 遗憾已录入 — {case.company_name}({case.ticker}) "
                f"错过涨幅 **{case.missed_return_pct:+.1f}%**"
            )
            st.markdown(f"**教训**: {case.lesson}")
            st.markdown(f"**防错规则**: {case.prevention_rule}")
            st.info("已自动追加到 `tasks/lessons.md`")

st.divider()

# ---------------------------------------------------------------------------
# 统计
# ---------------------------------------------------------------------------

stats = get_statistics()

st.markdown("### 📊 遗憾统计")

stat_cols = st.columns(3)
with stat_cols[0]:
    st.metric("遗憾总数", stats.get("total", 0))
with stat_cols[1]:
    st.metric("平均错过涨幅", f"{stats.get('avg_missed_return', 0):.1f}%")
with stat_cols[2]:
    st.metric("累计错过涨幅", f"{stats.get('total_missed_return', 0):.0f}%")

# 根因分布
by_cause = stats.get("by_root_cause", {})
if by_cause:
    st.markdown("**根因分布**")
    import plotly.graph_objects as go

    labels = [REGRET_ROOT_CAUSES.get(k, k).split("—")[0].strip() for k in by_cause.keys()]
    values = list(by_cause.values())

    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values,
        hole=0.4,
        marker_colors=["#dc3545", "#fd7e14", "#ffc107", "#28a745", "#17a2b8"],
    )])
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=20, b=0),
        showlegend=True,
        legend=dict(orientation="h", y=-0.1),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# 案例列表
# ---------------------------------------------------------------------------

st.markdown("### 📜 遗憾案例")

regrets = list_regrets()
if regrets:
    for r in reversed(regrets):
        missed = r.get("missed_return_pct", 0)
        severity = "🔴" if missed > 100 else "🟡" if missed > 50 else "⚪"

        with st.expander(
            f"{severity} **{r.get('company_name', '')}** ({r.get('ticker', '')}) — "
            f"错过 {missed:+.1f}%",
            expanded=False,
        ):
            dcol1, dcol2 = st.columns(2)
            with dcol1:
                st.markdown(f"**最早感知**: {r.get('first_noticed', '')}")
                st.markdown(f"**当时价格**: ${r.get('price_at_notice', 0):.2f}")
                st.markdown(f"**当前价格**: ${r.get('current_price', 0):.2f}")
            with dcol2:
                st.markdown(f"**错过涨幅**: {missed:+.1f}%")
                rc = r.get("root_cause", "")
                st.markdown(f"**根因**: {REGRET_ROOT_CAUSES.get(rc, rc)}")
                st.markdown(f"**录入时间**: {r.get('created_at', '')[:10]}")

            st.markdown(f"**故事**: {r.get('narrative', '')}")
            st.markdown(f"**教训**: {r.get('lesson', '')}")
            st.error(f"**防错规则**: {r.get('prevention_rule', '')}")
else:
    st.info("暂无遗憾案例。希望永远用不上这个页面...但诚实面对是进步的开始。")

st.divider()

# ---------------------------------------------------------------------------
# 防错规则清单
# ---------------------------------------------------------------------------

st.markdown("### 🛡️ 防错规则清单")
if regrets:
    for i, r in enumerate(regrets, 1):
        st.markdown(
            f"**{i}.** `{r.get('ticker', '')}` → {r.get('prevention_rule', '')}"
        )
else:
    st.info("录入遗憾后会自动生成防错规则")
