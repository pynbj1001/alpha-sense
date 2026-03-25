#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🔭 AI 猎手 — 主动扫描被忽略的机会 + 周度复盘信
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import TRACKER_DIR, WATCHLIST_PATH
from core.weekly_review import (
    generate_weekly_review,
    detect_ignored_opportunities,
    save_review,
    list_past_reviews,
)

st.set_page_config(page_title="🔭 AI 猎手", page_icon="🔭", layout="wide")

st.markdown("# 🔭 AI 猎手")
st.markdown("**不等你发现信号，系统主动扫描你可能忽略的机会**")
st.divider()

# ---------------------------------------------------------------------------
# 被忽略的机会
# ---------------------------------------------------------------------------

st.markdown("### ⚠️ 被忽略的机会")
st.markdown("*概率 ≥ 60% 但尚未启动深度研究的标的*")

ignored = detect_ignored_opportunities()

if ignored:
    for opp in ignored:
        st.warning(
            f"**{opp['ticker']}** — 概率 {opp['probability']:.0%}  \n"
            f"论点: {opp['thesis']}  \n"
            f"💡 {opp['suggestion']}"
        )
else:
    st.success("✅ 暂无被忽略的机会 — 所有高概率标的均已跟进")

st.divider()

# ---------------------------------------------------------------------------
# Watchlist 覆盖率检查
# ---------------------------------------------------------------------------

st.markdown("### 📋 Watchlist 覆盖率")
st.markdown("*你的 Watchlist 中有多少标的已加入贝叶斯追踪器？*")

# 加载 watchlist
wl_tickers = set()
if WATCHLIST_PATH.exists():
    try:
        wl = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
        for idea in wl.get("ideas", []):
            if idea.get("active", True) and idea.get("type") == "stock":
                symbol = idea.get("symbol", "")
                if symbol:
                    wl_tickers.add(symbol.upper())
    except Exception:
        pass

# 加载追踪器
tracker_tickers = set()
trackers_file = TRACKER_DIR / "data" / "trackers.json"
if trackers_file.exists():
    try:
        data = json.loads(trackers_file.read_text(encoding="utf-8"))
        for v in data.get("trackers", {}).values():
            if v.get("active", True):
                tracker_tickers.add(v.get("ticker", "").upper())
    except Exception:
        pass

covered = wl_tickers & tracker_tickers
uncovered = wl_tickers - tracker_tickers

cov_cols = st.columns(3)
with cov_cols[0]:
    st.metric("Watchlist 标的", len(wl_tickers))
with cov_cols[1]:
    st.metric("已追踪", len(covered))
with cov_cols[2]:
    coverage_pct = len(covered) / len(wl_tickers) * 100 if wl_tickers else 0
    st.metric("覆盖率", f"{coverage_pct:.0f}%")

if uncovered:
    with st.expander(f"📭 未追踪的 Watchlist 标的 ({len(uncovered)})", expanded=False):
        for t in sorted(uncovered):
            st.markdown(f"- `{t}` → 可通过信号捕获页添加到追踪器")

st.divider()

# ---------------------------------------------------------------------------
# 周度复盘信
# ---------------------------------------------------------------------------

st.markdown("### 📮 周度复盘信")

if st.button("📮 生成本周复盘信", type="primary", use_container_width=True):
    with st.spinner("正在汇总本周数据..."):
        review = generate_weekly_review()
        filepath = save_review(review)

    st.success(f"✅ 周报已生成并保存: `{filepath.name}`")

    sections = review.get("sections", {})
    summary = sections.get("summary", {})

    # 概览
    sum_cols = st.columns(5)
    with sum_cols[0]:
        st.metric("活跃追踪", summary.get("active_trackers", 0))
    with sum_cols[1]:
        st.metric("本周新信号", summary.get("new_signals_this_week", 0))
    with sum_cols[2]:
        st.metric("本周升级", summary.get("upgrades_this_week", 0))
    with sum_cols[3]:
        st.metric("被忽略", summary.get("ignored_count", 0))
    with sum_cols[4]:
        st.metric("信号总量", summary.get("total_signals", 0))

    # 概率变化
    movers = sections.get("probability_movers", [])
    if movers:
        st.markdown("**📈 概率变化 TOP 5**")
        for m in movers:
            change = m.get("change_7d", 0)
            arrow = "🔼" if change > 0 else "🔽" if change < 0 else "➡️"
            st.markdown(
                f"  {arrow} **{m['ticker']}** — {m['probability']:.0%} "
                f"(周变化 {change:+.1%}) — {m.get('thesis', '')}"
            )

    # 新信号
    new_sigs = sections.get("new_signals_detail", [])
    if new_sigs:
        st.markdown("**📡 本周新信号**")
        for s in new_sigs:
            st.markdown(
                f"  - `{s.get('id', '')}` {s.get('raw_input', '')[:50]} "
                f"→ {', '.join(s.get('related_tickers', []))}"
            )

st.divider()

# --- 历史周报 ---
st.markdown("### 📚 历史周报")
past = list_past_reviews()
if past:
    for r in past[:10]:
        s = r.get("summary", {})
        st.markdown(
            f"**{r['week_end']}** — "
            f"追踪 {s.get('active_trackers', 0)} | "
            f"新信号 {s.get('new_signals_this_week', 0)} | "
            f"升级 {s.get('upgrades_this_week', 0)} | "
            f"被忽略 {s.get('ignored_count', 0)}"
        )
else:
    st.info("点击上方按钮生成第一份周报")
