#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alpha Sense — 投资嗅觉升级系统

从"看对"到"大赚"的系统化管道：
信号捕获 → 贝叶斯追踪 → 信念阶梯 → 遗憾复盘 → AI猎手

启动: cd 15.Alpha-Sense && streamlit run app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# 路径与导入
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from config import TRACKER_DIR, DATA_DIR, SIGNALS_FILE, REGRETS_FILE, CONVICTION_LOG_FILE

# ---------------------------------------------------------------------------
# 页面配置
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Alpha Sense — 投资嗅觉升级系统",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 自定义样式
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #888;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #30475e;
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #00d2ff;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #aaa;
        margin-top: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------


def _count_json_list(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return len(data) if isinstance(data, list) else 0
    except Exception:
        return 0


def _load_tracker_count() -> int:
    trackers_file = TRACKER_DIR / "data" / "trackers.json"
    if not trackers_file.exists():
        return 0
    try:
        data = json.loads(trackers_file.read_text(encoding="utf-8"))
        return sum(1 for v in data.get("trackers", {}).values() if v.get("active", True))
    except Exception:
        return 0


def _load_recent_activity() -> list[dict]:
    """汇聚所有模块最近活动"""
    activities = []

    # 信号
    if SIGNALS_FILE.exists():
        try:
            signals = json.loads(SIGNALS_FILE.read_text(encoding="utf-8"))
            for s in (signals[-5:] if isinstance(signals, list) else []):
                activities.append({
                    "time": s.get("created_at", "")[:16],
                    "type": "📡 信号",
                    "detail": f"{s.get('signal_type', '')} — {s.get('raw_input', '')[:50]}",
                })
        except Exception:
            pass

    # 遗憾
    if REGRETS_FILE.exists():
        try:
            regrets = json.loads(REGRETS_FILE.read_text(encoding="utf-8"))
            for r in (regrets[-3:] if isinstance(regrets, list) else []):
                activities.append({
                    "time": r.get("created_at", "")[:16],
                    "type": "😤 遗憾",
                    "detail": f"{r.get('ticker', '')} 错过 {r.get('missed_return_pct', 0):+.1f}%",
                })
        except Exception:
            pass

    # 升级
    if CONVICTION_LOG_FILE.exists():
        try:
            log = json.loads(CONVICTION_LOG_FILE.read_text(encoding="utf-8"))
            for e in (log[-3:] if isinstance(log, list) else []):
                activities.append({
                    "time": e.get("timestamp", "")[:16],
                    "type": "🪜 升级",
                    "detail": f"{e.get('ticker', '')} {e.get('from_level', '')} → {e.get('to_level', '')}",
                })
        except Exception:
            pass

    activities.sort(key=lambda x: x["time"], reverse=True)
    return activities[:10]


# ---------------------------------------------------------------------------
# 主页面
# ---------------------------------------------------------------------------

st.markdown('<div class="main-header">🧠 Alpha Sense</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">投资嗅觉升级系统 — 从"看对"到"大赚"的系统化管道</div>', unsafe_allow_html=True)

# --- 核心指标卡片 ---
signal_count = _count_json_list(SIGNALS_FILE)
tracker_count = _load_tracker_count()
regret_count = _count_json_list(REGRETS_FILE)
upgrade_count = _count_json_list(CONVICTION_LOG_FILE)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📡 捕获信号", signal_count, help="通过信号捕获引擎录入的投资线索")
with col2:
    st.metric("📊 追踪标的", tracker_count, help="贝叶斯追踪器中活跃追踪的标的数")
with col3:
    st.metric("🪜 信念升级", upgrade_count, help="信念阶梯升级事件总数")
with col4:
    st.metric("😤 遗憾案例", regret_count, help="已复盘的遗憾投资案例")

st.divider()

# --- 系统管道流程 ---
st.markdown("### 🔄 投资嗅觉管道")
pipeline_cols = st.columns(6)
pipeline_items = [
    ("📡", "信号捕获", "一句话输入\n自动匹配标的"),
    ("📊", "贝叶斯追踪", "五维信号\n概率更新"),
    ("🪜", "信念阶梯", "概率驱动\n阶梯式加仓"),
    ("😤", "遗憾复盘", "根因分析\n防错规则"),
    ("🔭", "AI 猎手", "主动扫描\n机会预警"),
    ("📋", "成果总览", "全局统计\n一目了然"),
]
for col, (icon, name, desc) in zip(pipeline_cols, pipeline_items):
    with col:
        st.markdown(f"""
        <div style="text-align:center; padding:1rem; background:#16213e; border-radius:10px; border:1px solid #30475e;">
            <div style="font-size:2rem;">{icon}</div>
            <div style="font-weight:600; margin:0.3rem 0;">{name}</div>
            <div style="font-size:0.75rem; color:#aaa;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# --- 最近活动 ---
st.markdown("### 📅 最近活动")
activities = _load_recent_activity()
if activities:
    for act in activities:
        st.markdown(
            f"**{act['time']}** &nbsp; {act['type']} &nbsp; | &nbsp; {act['detail']}"
        )
else:
    st.info("暂无活动记录。从左侧导航开始使用各个模块吧！")

st.divider()

# --- 快速操作 ---
st.markdown("### ⚡ 快速操作")
qcol1, qcol2, qcol3 = st.columns(3)
with qcol1:
    if st.button("📡 捕获新信号", use_container_width=True):
        st.switch_page("pages/1_📡_信号捕获.py")
with qcol2:
    if st.button("📊 查看概率面板", use_container_width=True):
        st.switch_page("pages/2_📊_贝叶斯面板.py")
with qcol3:
    if st.button("😤 录入遗憾", use_container_width=True):
        st.switch_page("pages/4_😤_遗憾复盘.py")

# --- 侧栏 ---
with st.sidebar:
    st.markdown("---")
    st.markdown("#### 🧠 Alpha Sense v1.0")
    st.markdown(
        "**核心理念**: 把投资直觉系统化，"
        "让每一个洞察都不被浪费。"
    )
    st.markdown("---")
    st.markdown("**数据源**")
    st.markdown(f"- 贝叶斯追踪器: `14.贝叶斯追踪器/`")
    st.markdown(f"- Watchlist: `11.投资机会跟踪报告/`")
    st.markdown(f"- 研报输出: `10-研究报告输出/`")
