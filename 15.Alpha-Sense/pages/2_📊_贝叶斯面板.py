#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
📊 贝叶斯面板 — 概率追踪仪表盘
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import TRACKER_DIR, CONVICTION_LADDER

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

st.set_page_config(page_title="📊 贝叶斯面板", page_icon="📊", layout="wide")

st.markdown("# 📊 贝叶斯概率追踪面板")
st.markdown("**实时查看所有追踪标的的后验概率、五维信号、阶段判断**")
st.divider()

# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------

TRACKERS_FILE = TRACKER_DIR / "data" / "trackers.json"


@st.cache_data(ttl=3600)
def get_stock_name(ticker: str) -> str:
    """通过 yfinance 获取股票简称，缓存1小时"""
    if not HAS_YF:
        return ""
    try:
        info = yf.Ticker(ticker).info
        return info.get("shortName") or info.get("longName") or ""
    except Exception:
        return ""


def display_label(ticker: str) -> str:
    """返回 'TICKER (简称)' 或仅 'TICKER'"""
    name = get_stock_name(ticker)
    return f"{ticker} ({name})" if name else ticker


def load_trackers() -> list[dict]:
    if not TRACKERS_FILE.exists():
        return []
    try:
        data = json.loads(TRACKERS_FILE.read_text(encoding="utf-8"))
        trackers = data.get("trackers", {})
        return sorted(
            [v for v in trackers.values() if v.get("active", True)],
            key=lambda x: x.get("current_probability", 0.5),
            reverse=True,
        )
    except Exception:
        return []


def get_verdict(prob: float) -> str:
    if prob >= 0.75:
        return "🔥 扣动扳机 — 买入"
    if prob >= 0.65:
        return "📈 论点强化"
    if prob >= 0.45:
        return "📊 持续跟踪"
    if prob >= 0.25:
        return "⚠️ 论点动摇"
    return "🔴 扣动扳机 — 卖出"


def prob_color(prob: float) -> str:
    if prob >= 0.75:
        return "#dc3545"
    if prob >= 0.65:
        return "#fd7e14"
    if prob >= 0.45:
        return "#28a745"
    if prob >= 0.25:
        return "#ffc107"
    return "#6c757d"

# ---------------------------------------------------------------------------
# 操作区
# ---------------------------------------------------------------------------

op_col1, op_col2, op_col3 = st.columns([1, 1, 2])

with op_col1:
    if st.button("🔄 运行全量更新", type="primary", use_container_width=True):
        with st.spinner("正在收集五维信号并更新概率..."):
            try:
                result = subprocess.run(
                    [sys.executable, str(TRACKER_DIR / "tracker.py"), "run-all"],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(TRACKER_DIR),
                )
                st.success("✅ 更新完成")
                if result.stdout:
                    with st.expander("更新日志"):
                        st.code(result.stdout[-3000:])
                st.rerun()
            except subprocess.TimeoutExpired:
                st.error("⏰ 更新超时，请稍后重试")
            except Exception as e:
                st.error(f"更新失败: {e}")

with op_col2:
    if st.button("🔃 刷新数据", use_container_width=True):
        st.rerun()

# ---------------------------------------------------------------------------
# 概率排行卡片
# ---------------------------------------------------------------------------

trackers = load_trackers()

if not trackers:
    st.warning("暂无追踪标的，请先通过信号捕获页添加。")
    st.stop()

st.markdown(f"### 🎯 活跃追踪标的 ({len(trackers)})")

# --- 概率变化 TOP ---
prob_changes = []
for t in trackers:
    snapshots = t.get("daily_snapshots", [])
    if len(snapshots) >= 2:
        change = snapshots[-1].get("probability", 0.5) - snapshots[-2].get("probability", 0.5)
    else:
        change = 0
    prob_changes.append({"ticker": t["ticker"], "change": change})

top_movers = sorted(prob_changes, key=lambda x: abs(x["change"]), reverse=True)[:3]
if any(m["change"] != 0 for m in top_movers):
    st.markdown("**📈 近期变化最大**")
    mcols = st.columns(3)
    for i, m in enumerate(top_movers):
        with mcols[i]:
            arrow = "🔼" if m["change"] > 0 else "🔽" if m["change"] < 0 else "➡️"
            st.metric(display_label(m["ticker"]), f"{m['change']:+.1%}", label_visibility="visible")

st.divider()

# --- 标的卡片 ---
for t in trackers:
    prob = t.get("current_probability", 0.5)
    ticker = t.get("ticker", "")
    thesis = t.get("thesis", "")
    verdict = get_verdict(prob)
    color = prob_color(prob)

    label = display_label(ticker)
    with st.expander(
        f"{'🔥' if prob >= 0.75 else '📈' if prob >= 0.65 else '📊' if prob >= 0.45 else '⚠️'} "
        f"**{label}** — {prob:.0%} — {verdict}",
        expanded=(prob >= 0.65),
    ):
        card_cols = st.columns([1, 2, 1])

        with card_cols[0]:
            st.markdown(f"""
            <div style="text-align:center;">
                <div style="font-size:3rem; font-weight:700; color:{color};">{prob:.0%}</div>
                <div style="color:#aaa;">后验概率</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"**先验**: {t.get('prior', 0.5):.0%}")
            st.markdown(f"**方向**: {'📈 做多' if t.get('direction', 'long') == 'long' else '📉 做空'}")

        with card_cols[1]:
            st.markdown(f"**投资论点**: {thesis}")
            st.markdown(f"**目标**: {t.get('target', '')}")
            st.markdown(f"**创建**: {t.get('created_at', '')[:10]} | "
                       f"**更新**: {t.get('updated_at', '')[:10]}")
            tags = t.get("tags", [])
            if tags:
                st.markdown("**标签**: " + " ".join(f"`{tag}`" for tag in tags))

        with card_cols[2]:
            # 阶梯位置
            from core.conviction_ladder import get_stage
            stage = get_stage(prob)
            st.markdown(f"**信念阶梯**: `{stage['level']}` {stage['name']}")
            st.markdown(f"**建议仓位**: {stage['position']}")
            st.markdown(f"**下一步**: {stage['action']}")

        # 概率趋势图
        snapshots = t.get("daily_snapshots", [])
        if snapshots:
            import plotly.graph_objects as go
            dates = [s["date"] for s in snapshots]
            probs = [s["probability"] for s in snapshots]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates, y=probs, mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=4),
                name="概率",
            ))
            fig.add_hline(y=0.75, line_dash="dot", line_color="red", annotation_text="买入")
            fig.add_hline(y=0.25, line_dash="dot", line_color="gray", annotation_text="卖出")
            fig.update_layout(
                height=200, margin=dict(l=0, r=0, t=20, b=0),
                yaxis=dict(tickformat=".0%", range=[0, 1]),
                xaxis=dict(title=""),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, key=f"prob_trend_{ticker}")

        # 最近信号
        recent_signals = t.get("signals_history", [])[-5:]
        if recent_signals:
            st.markdown("**最近信号**")
            dim_icons = {
                "price": "📈", "fundamental": "📊", "news": "📰",
                "macro": "🌐", "technical": "📐",
            }
            for sig in reversed(recent_signals):
                icon = dim_icons.get(sig.get("dimension", ""), "❓")
                lr = sig.get("likelihood_ratio", 1.0)
                arrow = "↑" if lr > 1 else "↓" if lr < 1 else "→"
                st.markdown(
                    f"  {icon} {sig.get('name', '')} — LR={lr:.2f} {arrow} — "
                    f"{sig.get('description', '')[:50]}"
                )
