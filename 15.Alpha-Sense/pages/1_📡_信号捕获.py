#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
📡 信号捕获页 — 一句话输入 / 文章链接 → AI 自动匹配催化剂、关联标的、生成论点
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
from core.article_reader import read_and_analyze, HAS_REQUESTS, HAS_BS4

st.set_page_config(page_title="📡 信号捕获", page_icon="📡", layout="wide")

st.markdown("# 📡 信号捕获")
st.markdown("**一句话输入 / 文章链接 → AI 自动匹配催化剂、标的、论点 → 推入贝叶斯追踪器**")

# ===========================================================================
# 两种输入模式：手动输入 / 文章链接
# ===========================================================================
tab_manual, tab_article = st.tabs(["💡 手动输入", "🔗 文章链接"])

# ---------------------------------------------------------------------------
# Tab 1: 手动输入（原有逻辑）
# ---------------------------------------------------------------------------
with tab_manual:
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

    # --- 实时预览 ---
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

# ---------------------------------------------------------------------------
# Tab 2: 文章链接解读
# ---------------------------------------------------------------------------
with tab_article:
    # 依赖检查
    if not HAS_REQUESTS or not HAS_BS4:
        missing = []
        if not HAS_REQUESTS:
            missing.append("requests")
        if not HAS_BS4:
            missing.append("beautifulsoup4")
        st.error(f"⚠️ 缺少依赖: {', '.join(missing)}。请运行: `pip install {' '.join(missing)}`")
    else:
        url_input = st.text_input(
            "📎 粘贴文章链接",
            placeholder="https://mp.weixin.qq.com/s/... 或任意文章 URL",
        )

        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            analyze_btn = st.button("🚀 解读文章", type="primary", use_container_width=True)
        with col_info:
            st.caption("支持微信公众号、财经媒体、研报链接等")

        if analyze_btn and url_input:
            url = url_input.strip()

            with st.spinner("🔄 正在抓取文章内容..."):
                article, art_signal = read_and_analyze(url)

            if not article.success:
                st.error(f"❌ 抓取失败: {article.error}")
            else:
                st.success(f"✅ 成功抓取: {article.title or '(无标题)'}")

                # 元信息
                meta_cols = st.columns(3)
                with meta_cols[0]:
                    st.metric("来源", article.source or "未知")
                with meta_cols[1]:
                    st.metric("发布日期", article.publish_date or "未识别")
                with meta_cols[2]:
                    st.metric("文本长度", f"{len(article.text):,} 字")

                # 文章正文（可折叠）
                with st.expander("📄 文章全文", expanded=False):
                    st.text(article.text[:5000])
                    if len(article.text) > 5000:
                        st.caption(f"... 全文共 {len(article.text):,} 字，仅展示前 5000 字")

                if art_signal is not None:
                    st.divider()
                    st.markdown("### 📊 投资信号分析")

                    # 信号强度
                    strength_map = {
                        "strong": "🔴 强信号",
                        "medium": "🟡 中等信号",
                        "weak": "🟢 弱信号",
                    }
                    sig_cols = st.columns(4)
                    with sig_cols[0]:
                        st.markdown(f"**信号强度**: {strength_map.get(art_signal.signal_strength, '⚪ 未知')}")
                    with sig_cols[1]:
                        st.metric("利好信号", f"{len(art_signal.bullish_signals)} 条")
                    with sig_cols[2]:
                        st.metric("利空信号", f"{len(art_signal.bearish_signals)} 条")
                    with sig_cols[3]:
                        st.metric("建议先验", f"{art_signal.suggested_prior:.0%}")

                    # 关联标的
                    st.markdown("**🏷️ 关联标的**")
                    if art_signal.related_tickers:
                        st.code(", ".join(art_signal.related_tickers), language=None)
                    else:
                        st.info("未自动匹配到标的")

                    art_manual = st.text_input(
                        "➕ 手动补充标的（逗号分隔）",
                        placeholder="NVDA, MSFT, AAPL",
                        key="art_manual_tickers",
                    )
                    if art_manual:
                        extra = [t.strip().upper() for t in art_manual.split(",") if t.strip()]
                        art_signal.related_tickers = list(set(art_signal.related_tickers + extra))

                    # 催化剂 & 阶段
                    cat_col, stage_col = st.columns(2)
                    with cat_col:
                        st.markdown("**⚡ 催化剂**")
                        if art_signal.matched_catalysts:
                            for c in art_signal.matched_catalysts:
                                st.success(c)
                        else:
                            st.info("未匹配")
                    with stage_col:
                        st.markdown("**🔄 技术阶段**")
                        if art_signal.tech_stage:
                            st.info(TECH_STAGES.get(art_signal.tech_stage, art_signal.tech_stage))
                        else:
                            st.info("未识别")

                    # 关键数据点
                    if art_signal.key_data_points:
                        with st.expander("📈 关键数据点", expanded=True):
                            for dp in art_signal.key_data_points:
                                st.markdown(f"- {dp}")

                    # 利好/利空
                    bull_col, bear_col = st.columns(2)
                    with bull_col:
                        with st.expander(f"🟢 利好 ({len(art_signal.bullish_signals)})", expanded=False):
                            for i, bs in enumerate(art_signal.bullish_signals[:10], 1):
                                st.markdown(f"{i}. {bs}")
                    with bear_col:
                        with st.expander(f"🔴 利空 ({len(art_signal.bearish_signals)})", expanded=False):
                            for i, bs in enumerate(art_signal.bearish_signals[:10], 1):
                                st.markdown(f"{i}. {bs}")

                    st.divider()

                    # 保存为信号
                    art_prior = st.slider(
                        "调整先验概率",
                        min_value=0.30, max_value=0.70,
                        value=art_signal.suggested_prior,
                        step=0.05,
                        key="art_prior_slider",
                    )

                    if st.button("📡 保存为投资信号", type="primary", use_container_width=True):
                        raw_text = f"[文章] {art_signal.title}\n{art_signal.summary[:200]}"
                        saved = capture_signal(raw_text, "reading_insight")
                        saved.related_tickers = art_signal.related_tickers
                        saved.matched_catalysts = art_signal.matched_catalysts
                        saved.tech_stage = art_signal.tech_stage
                        saved.initial_prior = art_prior

                        st.success(f"✅ 信号已保存！ID: `{saved.id}`")

                        if art_signal.related_tickers:
                            st.markdown("**推入贝叶斯追踪器：**")
                            for ticker in art_signal.related_tickers:
                                at1, at2 = st.columns([3, 1])
                                with at1:
                                    st.markdown(f"**{ticker}** — 先验 {art_prior:.0%}")
                                with at2:
                                    if st.button(f"追踪 {ticker}", key=f"art_push_{ticker}"):
                                        ok = push_to_tracker(saved, ticker, prior=art_prior)
                                        if ok:
                                            st.success(f"✅ {ticker} 已加入追踪")
                                        else:
                                            st.warning(f"⚠️ {ticker} 已在追踪中")

        elif analyze_btn and not url_input:
            st.warning("⚠️ 请先粘贴文章链接")

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
