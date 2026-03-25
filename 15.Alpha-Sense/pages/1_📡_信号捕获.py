#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
📡 信号捕获页 — 一句话输入，AI 自动匹配催化剂、关联标的、生成论点
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import SIGNAL_TYPES, TECH_STAGES, TECH_CATALYSTS
from core.signal_capture import (
    capture_signal,
    list_signals,
    get_signal_stats,
    push_to_tracker,
    update_signal_status,
    match_tickers,
    match_catalysts,
    guess_tech_stage,
    suggest_prior,
    InvestmentSignal,
)

st.set_page_config(page_title="📡 信号捕获", page_icon="📡", layout="wide")

st.markdown("# 📡 信号捕获")
st.markdown("**一句话输入 → AI 自动匹配催化剂、标的、论点 → 推入贝叶斯追踪器**")
st.divider()

# ---------------------------------------------------------------------------
# 输入区
# ---------------------------------------------------------------------------

col_input, col_type = st.columns([3, 1])

with col_input:
    raw_input = st.text_area(
        "💡 你观察到了什么？",
        placeholder="例如: 4090显卡体验极好，AI推理需求爆炸性增长...\n"
                    "或: 今天读到一篇文章，比亚迪出海东南亚销量翻倍...\n"
                    "或: 朋友说他们公司全面切换到Azure，成本降了40%...",
        height=120,
    )

with col_type:
    signal_type = st.selectbox(
        "信号类型",
        options=list(SIGNAL_TYPES.keys()),
        format_func=lambda k: SIGNAL_TYPES[k],
    )

# ---------------------------------------------------------------------------
# 实时预览（输入时自动匹配）
# ---------------------------------------------------------------------------

if raw_input:
    st.markdown("### 🔍 AI 匹配预览")

    preview_cols = st.columns(3)

    tickers = match_tickers(raw_input)
    catalysts = match_catalysts(raw_input)
    stage = guess_tech_stage(raw_input)
    prior = suggest_prior(signal_type, len(catalysts), len(tickers))

    with preview_cols[0]:
        st.markdown("**关联标的**")
        if tickers:
            for t in tickers:
                st.code(t)
        else:
            st.warning("未自动匹配到标的，你可以手动添加")

    with preview_cols[1]:
        st.markdown("**匹配催化剂**")
        if catalysts:
            for c in catalysts:
                st.success(c)
        else:
            st.info("未匹配到明确催化剂")

    with preview_cols[2]:
        st.markdown("**技术革命阶段**")
        if stage:
            st.info(f"{TECH_STAGES.get(stage, stage)}")
        else:
            st.info("未识别阶段")
        st.markdown(f"**建议先验概率**: `{prior:.0%}`")

    st.divider()

    # --- 可调整参数 ---
    adj_col1, adj_col2 = st.columns(2)
    with adj_col1:
        manual_tickers = st.text_input(
            "手动添加标的（逗号分隔）",
            placeholder="NVDA, TSM, AMD",
        )
    with adj_col2:
        adjusted_prior = st.slider(
            "调整先验概率",
            min_value=0.30, max_value=0.70, value=prior, step=0.05,
        )

    # --- 捕获按钮 ---
    if st.button("🎯 捕获信号", type="primary", use_container_width=True):
        signal = capture_signal(raw_input, signal_type)

        # 合并手动添加的标的
        if manual_tickers:
            extra = [t.strip().upper() for t in manual_tickers.split(",") if t.strip()]
            signal.related_tickers = list(set(signal.related_tickers + extra))
        signal.initial_prior = adjusted_prior

        st.success(f"✅ 信号已捕获！ID: `{signal.id}`")
        st.json({
            "id": signal.id,
            "signal_type": SIGNAL_TYPES.get(signal.signal_type, signal.signal_type),
            "related_tickers": signal.related_tickers,
            "matched_catalysts": signal.matched_catalysts,
            "tech_stage": TECH_STAGES.get(signal.tech_stage, "未识别"),
            "thesis_draft": signal.thesis_draft,
            "initial_prior": f"{signal.initial_prior:.0%}",
        })

        # --- 推入追踪器 ---
        if signal.related_tickers:
            st.markdown("---")
            st.markdown("### 📊 推入贝叶斯追踪器")
            for ticker in signal.related_tickers:
                tcol1, tcol2 = st.columns([3, 1])
                with tcol1:
                    st.markdown(f"**{ticker}** — {signal.thesis_draft[:60]}")
                with tcol2:
                    if st.button(f"推入 {ticker}", key=f"push_{ticker}"):
                        ok = push_to_tracker(signal, ticker, prior=adjusted_prior)
                        if ok:
                            st.success(f"✅ {ticker} 已加入贝叶斯追踪器")
                        else:
                            st.warning(f"⚠️ {ticker} 已在追踪列表中")

st.divider()

# ---------------------------------------------------------------------------
# 信号历史
# ---------------------------------------------------------------------------

st.markdown("### 📜 信号历史")

# 筛选
filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    status_filter = st.selectbox(
        "状态筛选",
        ["全部", "new", "tracking", "researching", "positioned", "closed"],
    )
with filter_col2:
    stats = get_signal_stats()
    st.metric("信号总数", stats.get("total", 0))

signals = list_signals(status=None if status_filter == "全部" else status_filter)

if signals:
    for s in reversed(signals[-20:]):
        with st.expander(
            f"{'📡' if s['status']=='new' else '🔍' if s['status']=='tracking' else '📊'} "
            f"`{s.get('id', '')}` — {s.get('raw_input', '')[:60]}",
            expanded=False,
        ):
            ecol1, ecol2, ecol3 = st.columns(3)
            with ecol1:
                st.markdown(f"**类型**: {SIGNAL_TYPES.get(s.get('signal_type', ''), s.get('signal_type', ''))}")
                st.markdown(f"**状态**: `{s.get('status', 'new')}`")
            with ecol2:
                st.markdown(f"**标的**: {', '.join(s.get('related_tickers', []))}")
                st.markdown(f"**先验**: `{s.get('initial_prior', 0.5):.0%}`")
            with ecol3:
                st.markdown(f"**时间**: {s.get('created_at', '')[:16]}")
                stage_key = s.get("tech_stage", "")
                st.markdown(f"**阶段**: {TECH_STAGES.get(stage_key, '未识别')}")

            if s.get("matched_catalysts"):
                st.markdown(f"**催化剂**: {', '.join(s['matched_catalysts'])}")
            st.markdown(f"**论点**: {s.get('thesis_draft', '')}")

            # 状态更新
            new_status = st.selectbox(
                "更新状态",
                ["new", "tracking", "researching", "positioned", "closed"],
                index=["new", "tracking", "researching", "positioned", "closed"].index(
                    s.get("status", "new")
                ),
                key=f"status_{s.get('id', '')}",
            )
            if new_status != s.get("status", "new"):
                if st.button("更新", key=f"update_{s.get('id', '')}"):
                    update_signal_status(s.get("id", ""), new_status)
                    st.success(f"状态已更新为 `{new_status}`")
                    st.rerun()
else:
    st.info("暂无信号记录。在上方输入你的观察开始捕获信号！")
