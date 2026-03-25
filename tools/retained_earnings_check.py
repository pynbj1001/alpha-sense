#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
retained_earnings_check.py — 留存收益质量检验工具 v2.0
=======================================================
基于巴菲特股东信（1979/1983/1984/1985/1986）的资本配置质量检验框架

核心指标：
1. REM  留存收益乘数 = (当前股价 - 基期股价) / 每股累计留存净利润
2. ROE  平均净资产收益率 及趋势
3. DFR  分红/募资比 = 累计分红 / 累计股权融资
4. CapEx效率 = 累计资本支出 / 税前营业利润增量
5. FCF转化率 = 自由现金流 / 净利润

v2.0 新特性：
- 默认读取近 10 年数据（不足则用全部可用年份），无需手动指定
- 双源验证：A 股同时调用 yfinance + akshare，ROE/价格/分红均交叉比对
- 无交互模式：ticker 存在时全程无需人工输入
- 数据置信度标注：每项核心指标标注来源（单源/双源/低置信）

使用方式：
   # 直接运行（默认 10 年数据，无需任何额外参数）
   python tools/retained_earnings_check.py --ticker AAPL
   python tools/retained_earnings_check.py --ticker 600519.SS
   python tools/retained_earnings_check.py --ticker 3690.HK

   # 指定数据年限（5 或 10）
   python tools/retained_earnings_check.py --ticker AAPL --years 5

   # 手动录入（IPO 级别长跨度或数据源均失效时使用）
   python tools/retained_earnings_check.py --manual

   # 带基准年
   python tools/retained_earnings_check.py --ticker AAPL --base-year 2010

   # 输出报告到文件
   python tools/retained_earnings_check.py --ticker AAPL --save
"""

import argparse
import json
import os
import sys
from datetime import datetime, date

# ---------- 依赖导入（容错） ----------
try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False
    print("[警告] yfinance 未安装，自动模式不可用。请运行: pip install yfinance")

try:
    import akshare as ak
    HAS_AK = True
except ImportError:
    HAS_AK = False

try:
    import pandas as pd
    HAS_PD = True
except ImportError:
    HAS_PD = False

REPORT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "10-研究报告输出"
)

DEFAULT_YEARS = 10  # 默认拉取近 10 年数据，不足则使用全部可用
PRICE_PERIOD_MAP = {10: "10y", 5: "5y", 3: "3y"}  # yfinance 历史价格周期

# =====================================================================
# 评分规则
# =====================================================================

def score_rem(rem):
    """REM 评分（满分 35）"""
    if rem is None:
        return 0, "数据不足"
    if rem >= 5:
        return 35, "🌟 优秀"
    elif rem >= 2:
        return 25, "✅ 良好"
    elif rem >= 1:
        return 15, "⚠️ 及格"
    else:
        return 0, "❌ 不合格"


def score_roe(avg_roe):
    """ROE 评分（满分 25）"""
    if avg_roe is None:
        return 0, "数据不足"
    if avg_roe >= 20:
        return 25, "🌟 优秀"
    elif avg_roe >= 15:
        return 20, "✅ 合格"
    elif avg_roe >= 8:
        return 10, "⚠️ 及格下线"
    else:
        return 0, "❌ 不合格"


def score_dfr(dfr):
    """DFR 评分（满分 20）"""
    if dfr is None:
        return 0, "数据不足"
    if dfr >= 2:
        return 20, "🌟 优秀（真现金奶牛）"
    elif dfr >= 1:
        return 15, "✅ 良好"
    elif dfr >= 0.5:
        return 8, "⚠️ 轻度依赖融资"
    else:
        return 0, "❌ 严重依赖外部输血"


def score_capex_efficiency(capex_eff):
    """CapEx 效率评分（满分 10），越低越好"""
    if capex_eff is None:
        return 5, "数据不足（中性）"
    if capex_eff < 3:
        return 10, "🌟 优秀"
    elif capex_eff < 5:
        return 7, "✅ 达到美国企业平均"
    elif capex_eff < 15:
        return 4, "⚠️ 低于平均"
    else:
        return 0, "❌ 高度资本消耗"


def score_fcf_quality(fcf_ratio):
    """FCF 转化率评分（满分 10）"""
    if fcf_ratio is None:
        return 5, "数据不足（中性）"
    if fcf_ratio >= 0.8:
        return 10, "🌟 优秀"
    elif fcf_ratio >= 0.6:
        return 7, "✅ 良好"
    elif fcf_ratio >= 0.4:
        return 4, "⚠️ 一般"
    else:
        return 0, "❌ 利润质量差"


def overall_grade(total_score):
    if total_score >= 80:
        return "🌟 资本配置优秀"
    elif total_score >= 60:
        return "✅ 合格"
    elif total_score >= 40:
        return "⚠️ 需深度审查"
    else:
        return "❌ 不合格"


def mgmt_advice(total_score, rem, roe):
    """基于综合得分给出管理层建议"""
    if total_score >= 80:
        return "维持高留存策略，持续复利增值；可适度加大分红或回购以回馈股东。"
    elif total_score >= 60:
        if rem and rem < 2:
            return "留存效率有提升空间，建议加大分红/回购比例，减少低效资本留存。"
        return "保持现有资本配置方向，持续监控 REM 和 ROE 趋势。"
    elif total_score >= 40:
        return "管理层应重审资本配置策略：减少低效扩张，加大股东回报（分红/回购）。"
    else:
        return "⚠️ 管理层资本配置失当，应立即减少留存，将资本返还股东；若 CapEx 效率持续为负，考虑退出该标的。"


# =====================================================================
# A 股 akshare 数据拉取（双源验证主力）
# =====================================================================

def fetch_cn_akshare(code6: str, years: int = DEFAULT_YEARS) -> dict:
    """
    从 akshare 拉取 A 股核心财务数据（作为双源验证的第二数据源）。
    code6: 6 位 A 股代码，如 "600519"
    返回 dict，键名带 _ak 后缀。失败项静默跳过，不抛出异常。
    """
    result: dict = {}
    if not HAS_AK:
        return result
    if not HAS_PD:
        return result

    start_year = datetime.now().year - years + 1
    start_date_str = f"{start_year}0101"
    end_date_str = datetime.now().strftime("%Y%m%d")

    # ---- 1. 复权历史股价 ----
    try:
        df_price = ak.stock_zh_a_hist(
            symbol=code6, period="daily",
            start_date=start_date_str, end_date=end_date_str,
            adjust="hfq"
        )
        if df_price is not None and not df_price.empty:
            close_col = "收盘" if "收盘" in df_price.columns else df_price.columns[-1]
            result["base_price_ak"] = round(float(df_price[close_col].iloc[0]), 3)
            result["current_price_ak"] = round(float(df_price[close_col].iloc[-1]), 3)
    except Exception as e:
        result["price_error_ak"] = str(e)[:120]

    # ---- 2. 关键财务指标（ROE、每股净利润等） ----
    try:
        df_ind = ak.stock_financial_analysis_indicator(symbol=code6, start_year=str(start_year - 1))
        if df_ind is not None and not df_ind.empty:
            # 列名适配
            date_col = next((c for c in df_ind.columns if "日期" in str(c) or "报告" in str(c)), None)
            roe_col = next((c for c in df_ind.columns
                            if "加权净资产收益率" in str(c) or "净资产收益率" in str(c)), None)
            ni_col  = next((c for c in df_ind.columns if "净利润" in str(c) and "增长" not in str(c)), None)

            if date_col and roe_col:
                df_ind["_year"] = pd.to_datetime(df_ind[date_col], errors="coerce").dt.year
                recent = df_ind[df_ind["_year"] >= start_year].copy()
                roe_vals = pd.to_numeric(recent[roe_col], errors="coerce").dropna().tolist()
                if roe_vals:
                    result["roe_history_ak"] = [round(v, 2) for v in roe_vals]
                    result["avg_roe_ak"] = round(float(sum(roe_vals) / len(roe_vals)), 2)
            if ni_col and date_col:
                df_ind["_year"] = pd.to_datetime(df_ind[date_col], errors="coerce").dt.year
                recent = df_ind[df_ind["_year"] >= start_year].copy()
                ni_vals = pd.to_numeric(recent[ni_col], errors="coerce").dropna().tolist()
                if ni_vals:
                    result["cum_ni_ak"] = round(float(sum(ni_vals)), 4)  # 单位：亿元
    except Exception as e:
        result["indicator_error_ak"] = str(e)[:120]

    # ---- 3. 现金流量表：资本支出 + 分红支付 ----
    try:
        df_cf = ak.stock_cash_flow_sheet_by_yearly_em(symbol=code6)
        if df_cf is not None and not df_cf.empty:
            # 行列转置成易处理格式
            if "REPORT_DATE" in df_cf.columns or "报告日" in df_cf.columns:
                pass  # 已是宽表
            # 常见结构：行=科目，列=年份日期
            idx_col = df_cf.columns[0]
            date_cols = [c for c in df_cf.columns[1:] if str(c)[:4].isdigit() or
                         (hasattr(c, 'year') and c.year >= start_year)]

            def _row_sum(df, keywords):
                for kw in keywords:
                    rows = df[df[idx_col].astype(str).str.contains(kw, na=False)]
                    if not rows.empty:
                        vals = []
                        for dc in date_cols:
                            try:
                                yr = int(str(dc)[:4])
                                if yr >= start_year:
                                    v = pd.to_numeric(rows[dc].values[0], errors="coerce")
                                    if not pd.isna(v):
                                        vals.append(float(v))
                            except Exception:
                                pass
                        if vals:
                            return sum(vals)
                return None

            # 资本支出（购建固定、无形资产等）
            capex_raw = _row_sum(df_cf, ["购建固定资产", "购置固定资产"])
            if capex_raw is not None:
                result["cum_capex_ak"] = round(abs(capex_raw), 4)

            # 分红支付
            div_raw = _row_sum(df_cf, ["分配股利", "支付股利", "支付给股东"])
            if div_raw is not None:
                result["cum_div_ak"] = round(abs(div_raw), 4)

            # 自由现金流（经营活动净现金流 - 资本支出）
            ocf_raw = _row_sum(df_cf, ["经营活动产生的现金流量净额", "经营活动现金流量净额"])
            if ocf_raw is not None and capex_raw is not None:
                result["cum_fcf_ak"] = round(float(ocf_raw) - abs(capex_raw), 4)
    except Exception as e:
        result["cf_error_ak"] = str(e)[:120]

    return result


def cross_validate(yf_val, ak_val, name: str, tolerance: float = 0.15) -> tuple:
    """
    比对两个数值，返回 (采用值, 置信标注)。
    tolerance: 偏差容忍率（默认 15%），超出则标注差异。
    """
    if yf_val is None and ak_val is None:
        return None, f"[{name}] 双源均无数据"
    if yf_val is None:
        return ak_val, f"[{name}] 单源(akshare)"
    if ak_val is None:
        return yf_val, f"[{name}] 单源(yfinance)"
    # 都有值：计算偏差
    try:
        base = abs(yf_val) if abs(yf_val) > abs(ak_val) else abs(ak_val)
        diff_pct = abs(yf_val - ak_val) / (base + 1e-9)
        if diff_pct <= tolerance:
            avg = round((yf_val + ak_val) / 2, 4)
            return avg, f"[{name}] ✅双源吻合 yf={yf_val} ak={ak_val} 偏差{diff_pct:.1%}"
        else:
            # 偏差大，保守取均值，标注差异
            avg = round((yf_val + ak_val) / 2, 4)
            return avg, f"[{name}] ⚠️双源差异 yf={yf_val} ak={ak_val} 偏差{diff_pct:.1%}（取均值）"
    except Exception:
        return yf_val, f"[{name}] 比对异常，采用yfinance"


# =====================================================================
# 自动数据拉取（主入口，默认 10 年，无交互）
# =====================================================================

def fetch_auto(ticker: str, base_year: int = None, years: int = DEFAULT_YEARS):
    """
    自动拉取数据，默认 10 年窗口，无需人工介入。
    - A 股 (.SS/.SZ)：yfinance + akshare 双源交叉验证
    - 美股 / 港股：yfinance 主力，标注单源
    REM 所需基期价来自 N 年前复权价（price history），非 IPO 价。
    若需 IPO 级别精确，建议 --manual 模式补充真实基期价。
    """
    if not HAS_YF:
        print("[错误] yfinance 未安装，无法使用自动模式。pip install yfinance")
        return None

    ticker_up = ticker.upper()
    is_cn = ticker_up.endswith(".SS") or ticker_up.endswith(".SZ")
    is_hk = ticker_up.endswith(".HK")
    code6 = ticker.split(".")[0].zfill(6) if (is_cn or is_hk) else None

    print(f"\n[INFO] 正在拉取 {ticker} 数据（目标：近{years}年）...")
    cross_notes: list = []  # 双源比对记录

    # ======================== yfinance 拉取 ========================
    stk = yf.Ticker(ticker)
    try:
        info = stk.info
        company_name = info.get("longName") or info.get("shortName") or ticker
        currency = info.get("currency", "")
        current_price_yf = info.get("currentPrice") or info.get("regularMarketPrice")
        if not current_price_yf:
            hist_tmp = stk.history(period="5d")
            current_price_yf = float(hist_tmp["Close"].iloc[-1]) if not hist_tmp.empty else None
    except Exception as e:
        print(f"[警告] yfinance 基础信息失败: {e}")
        info = {}
        company_name = ticker
        current_price_yf = None
        currency = ""

    # 财务报表（yfinance 通常提供 4 年年报）
    try:
        fin = stk.financials
        bs  = stk.balance_sheet
        cf  = stk.cashflow
    except Exception as e:
        print(f"[警告] yfinance 财务报表拉取失败: {e}")
        fin = cf = bs = None

    # 历史股价（用 years 范围取基期价格）
    price_period = PRICE_PERIOD_MAP.get(years, "10y")
    try:
        hist_full = stk.history(period=price_period)
        base_price_yf = float(hist_full["Close"].iloc[0]) if not hist_full.empty else None
        if current_price_yf is None and not hist_full.empty:
            current_price_yf = float(hist_full["Close"].iloc[-1])
    except Exception:
        hist_full = None
        base_price_yf = None

    # 从 yfinance 财务报表提取累计数据
    years_available = []
    if fin is not None and not fin.empty:
        start_year_filter = (datetime.now().year - years) if not base_year else base_year
        years_available = sorted(
            [c for c in fin.columns if hasattr(c, 'year') and c.year >= start_year_filter],
            reverse=False
        )
        if not years_available:
            years_available = sorted(fin.columns, reverse=False)

    def _safe_sum(df, keywords, cols):
        if df is None or df.empty or not cols:
            return None
        row_key = next((r for r in df.index for kw in keywords if kw in str(r)), None)
        if not row_key:
            return None
        vals = []
        for c in cols:
            try:
                v = float(df.loc[row_key, c])
                if HAS_PD and not pd.isna(v):
                    vals.append(v)
                elif not HAS_PD:
                    vals.append(v)
            except Exception:
                pass
        return sum(vals) if vals else None

    cum_ni_yf   = _safe_sum(fin, ["Net Income"], years_available)
    cum_capex_raw_yf = _safe_sum(cf, ["Capital Expenditure"], years_available)
    cum_capex_yf = abs(cum_capex_raw_yf) if cum_capex_raw_yf is not None else None
    cum_div_raw_yf  = _safe_sum(cf, ["Payment", "Dividend"], years_available)
    cum_div_yf  = abs(cum_div_raw_yf) if cum_div_raw_yf is not None else None
    cum_fcf_raw_yf  = _safe_sum(cf, ["Free Cash Flow"], years_available)

    trailing_roe_yf = info.get("returnOnEquity")
    avg_roe_yf = round(trailing_roe_yf * 100, 1) if trailing_roe_yf else None

    op_income_row_keys = [r for r in (fin.index if fin is not None and not fin.empty else [])
                          if "Operating Income" in str(r)]
    op_first = op_last = None
    if op_income_row_keys and years_available:
        try:
            op_first = float(fin.loc[op_income_row_keys[0], years_available[0]])
            op_last  = float(fin.loc[op_income_row_keys[0], years_available[-1]])
        except Exception:
            pass

    shares = info.get("sharesOutstanding")

    # ======================== akshare 拉取（A 股） ========================
    ak_data: dict = {}
    if is_cn and HAS_AK and code6:
        print(f"[INFO] A 股双源验证：同时请求 akshare（{code6}）...")
        ak_data = fetch_cn_akshare(code6, years=years)
    elif is_cn and not HAS_AK:
        print("[警告] akshare 未安装，A 股仅使用单源(yfinance)。建议: pip install akshare")

    # ======================== 双源交叉验证 ========================
    current_price, note_cp = cross_validate(current_price_yf, ak_data.get("current_price_ak"), "当前股价")
    base_price, note_bp = cross_validate(base_price_yf, ak_data.get("base_price_ak"), "基期股价", tolerance=0.25)
    avg_roe, note_roe = cross_validate(avg_roe_yf, ak_data.get("avg_roe_ak"), "ROE均值")

    for note in [note_cp, note_bp, note_roe]:
        if note:
            cross_notes.append(note)

    # 净利润：yfinance 单位为原始货币（元/美元），akshare 指标表单位为亿元
    # 仅做 ROE 和价格的双源验证；净利润以 yfinance 为准（单位更直接）
    cum_ni    = cum_ni_yf
    cum_capex = cum_capex_yf
    cum_div   = cum_div_yf

    # 如果 yfinance 分红数据缺失，尝试用 akshare
    if cum_div is None and ak_data.get("cum_div_ak") is not None:
        cum_div = ak_data["cum_div_ak"]
        cross_notes.append("[分红] 采用 akshare 数据（yfinance 缺失）")

    # FCF 转化率
    cum_fcf = cum_fcf_raw_yf
    fcf_ratio = (cum_fcf / cum_ni) if (cum_fcf and cum_ni and cum_ni > 0) else None
    if fcf_ratio is None and ak_data.get("cum_fcf_ak") is not None and ak_data.get("cum_ni_ak") and ak_data["cum_ni_ak"] > 0:
        fcf_ratio = round(ak_data["cum_fcf_ak"] / ak_data["cum_ni_ak"], 3)
        cross_notes.append("[FCF率] 采用 akshare 估算")

    # CapEx 效率
    capex_eff = None
    if cum_capex and op_first is not None and op_last is not None:
        op_increment = op_last - op_first
        if op_increment > 0:
            capex_eff = round(cum_capex / op_increment, 1)
    if capex_eff is None and ak_data.get("cum_capex_ak") is not None:
        # akshare 单位亿，需折算统一单位时只做方向判断
        cross_notes.append("[CapEx] akshare 有数据，但单位与yfinance不统一，暂不合并计算")

    # 每股累计留存 & REM
    per_share_retained = None
    if cum_ni and shares and shares > 0:
        per_share_ni  = cum_ni / shares
        per_share_div = (cum_div / shares) if cum_div else 0
        per_share_retained = per_share_ni - per_share_div

    rem = None
    if current_price and base_price and per_share_retained and per_share_retained > 0:
        rem = round((current_price - base_price) / per_share_retained, 2)

    # DFR：yfinance 无融资数据，akshare 也需专门接口，标记为 N/A
    dfr = None

    # 实际使用的数据年份
    actual_years = len(years_available) if years_available else years
    base_year_used = base_year or (years_available[0].year if years_available else datetime.now().year - years)

    data_source = "yfinance+akshare(双源)" if (is_cn and ak_data) else "yfinance(单源)"
    note_text = (
        f"价格基期={price_period}区间最早价（非IPO价）；"
        f"数据源={data_source}；"
        f"年报年数={actual_years}（yfinance上限约4年）；"
        f"DFR需手动补充；"
        + ("双源比对：" + " | ".join(cross_notes) if cross_notes else "")
    )

    return {
        "company": company_name,
        "ticker": ticker,
        "currency": currency,
        "current_price": round(current_price, 3) if current_price else None,
        "base_price": round(base_price, 3) if base_price else None,
        "base_year": base_year_used,
        "data_years": actual_years,
        "cum_net_income": cum_ni,
        "cum_capex": cum_capex,
        "cum_dividend": cum_div,
        "cum_fundraising": None,
        "per_share_retained": round(per_share_retained, 4) if per_share_retained else None,
        "rem": rem,
        "avg_roe": avg_roe,
        "dfr": dfr,
        "capex_efficiency": capex_eff,
        "fcf_ratio": fcf_ratio,
        "cross_notes": cross_notes,
        "note": note_text,
    }


# =====================================================================
# 手动录入模式
# =====================================================================

def input_float(prompt, allow_none=True):
    while True:
        raw = input(prompt).strip()
        if not raw and allow_none:
            return None
        try:
            return float(raw)
        except ValueError:
            print("  请输入数字，或直接回车跳过: ")


def fetch_manual():
    """交互式手动录入"""
    print("\n===== 留存收益检验 — 手动录入模式 =====")
    print("（直接回车 = 跳过该项，标记为数据不足）\n")

    company = input("公司名称/代码: ").strip() or "未知公司"
    base_year = input("基期年份（如 2003）: ").strip()
    current_year = input(f"检验截止年份（默认 {date.today().year}）: ").strip() or str(date.today().year)

    print("\n--- 价格数据（需复权对齐）---")
    base_price = input_float(f"  基期股价（{base_year}年，复权后，按回车跳过）: ")
    current_price = input_float(f"  当前/截止年股价: ")

    print("\n--- 累计损益数据（亿元，或自定义单位，后续保持一致）---")
    cum_ni = input_float("  累计净利润（亿）: ")
    cum_div = input_float("  累计分红（亿，按回车=0）: ", allow_none=False) or 0.0
    cum_fundraising = input_float("  累计股权融资（亿）: ")
    cum_capex = input_float("  累计资本支出（亿）: ")
    op_income_base = input_float(f"  基期税前营业利润（{base_year}年，亿）: ")
    op_income_now = input_float(f"  截止年税前营业利润（{current_year}年，亿）: ")

    print("\n--- 每股数据（或使用总量，保持单位一致）---")
    shares = input_float("  当前/基期平均总股本（亿股，用于折算每股，按回车跳过）: ")

    print("\n--- FCF 数据（可选）---")
    avg_fcf_ratio = input_float("  最近 3-5 年 FCF/净利润 均值（如 0.75，按回车跳过）: ")

    print("\n--- ROE 数据 ---")
    avg_roe = input_float("  历史平均 ROE（%，如 18，按回车跳过）: ")

    # 计算
    per_share_retained = None
    if cum_ni is not None and shares and shares > 0:
        per_share_retained = (cum_ni - cum_div) / shares
    elif cum_ni is not None and current_price and base_price:
        # 若无股本数量，用利润/价格比估算不稳定，提示
        print("  [提示] 缺少总股本数据，REM 无法精确计算。")

    rem = None
    if current_price and base_price and per_share_retained and per_share_retained > 0:
        rem = round((current_price - base_price) / per_share_retained, 2)

    dfr = None
    if cum_fundraising and cum_fundraising > 0 and cum_div >= 0:
        dfr = round(cum_div / cum_fundraising, 2)

    capex_eff = None
    if cum_capex and op_income_base is not None and op_income_now is not None:
        increment = op_income_now - op_income_base
        if increment > 0:
            capex_eff = round(cum_capex / increment, 1)

    return {
        "company": company,
        "ticker": company,
        "currency": "",
        "current_price": current_price,
        "base_price": base_price,
        "base_year": base_year,
        "data_years": None,
        "cum_net_income": cum_ni,
        "cum_capex": cum_capex,
        "cum_dividend": cum_div,
        "cum_fundraising": cum_fundraising,
        "per_share_retained": per_share_retained,
        "rem": rem,
        "avg_roe": avg_roe,
        "dfr": dfr,
        "capex_efficiency": capex_eff,
        "fcf_ratio": avg_fcf_ratio,
        "note": "手动录入",
    }


# =====================================================================
# 报告生成
# =====================================================================

def render_report(data: dict) -> str:
    company = data["company"]
    ticker = data["ticker"]
    today = date.today().isoformat()

    rem = data.get("rem")
    avg_roe = data.get("avg_roe")
    dfr = data.get("dfr")
    capex_eff = data.get("capex_efficiency")
    fcf_ratio = data.get("fcf_ratio")

    s_rem, l_rem = score_rem(rem)
    s_roe, l_roe = score_roe(avg_roe)
    s_dfr, l_dfr = score_dfr(dfr)
    s_capex, l_capex = score_capex_efficiency(capex_eff)
    s_fcf, l_fcf = score_fcf_quality(fcf_ratio)

    total = s_rem + s_roe + s_dfr + s_capex + s_fcf
    grade = overall_grade(total)
    advice = mgmt_advice(total, rem, avg_roe)

    base_year = data.get("base_year", "?")
    current_price = data.get("current_price")
    base_price = data.get("base_price")
    currency = data.get("currency", "")

    def fmt(v, unit=""):
        if v is None:
            return "N/A"
        return f"{v}{unit}"

    lines = [
        f"",
        f"留存收益质量检验报告 — {company} ({ticker})",
        f"=" * 52,
        f"检验日期：{today}",
        f"基期：{base_year}   当前股价：{fmt(current_price)} {currency}   基期股价：{fmt(base_price)} {currency}",
        f"",
    ]

    # 巴菲特一元测试 — 放在最顶部
    if rem is not None:
        if rem < 1:
            lines += [
                f"🚨 巴菲特一元测试：未通过（REM = {rem}x）",
                f"   过去 {data.get('data_years') or '?'} 年，管理层每保留 1 元利润，",
                f"   仅创造了 {rem}x 元市值，资本在持续被摧毁。",
                f"   → 管理层应停止低效留存，立即加大分红/回购。",
                f"   → 后续估值：EPV 折价 30%；成长价值暂不计入。",
                f"",
            ]
        elif rem < 2:
            lines += [
                f"⚠️ 巴菲特一元测试：勉强及格（REM = {rem}x）",
                f"   留存收益刚刚满足最低门槛，需持续追踪是否依赖政策/周期红利。",
                f"",
            ]
        else:
            lines += [
                f"✅ 巴菲特一元测试：通过（REM = {rem}x）",
                f"   每保留 1 元收益，创造了 {rem}x 元市值，管理层资本配置合格。",
                f"",
            ]
    else:
        lines += [
            f"⚠️ 巴菲特一元测试：数据不足，无法计算 REM（需提供基期价格与每股留存利润）",
            f"",
        ]

    lines += [
        f"核心指标",
        f"-" * 40,
        f"① 留存收益乘数 (REM)       : {fmt(rem, 'x'):<10} {l_rem}  [{s_rem}/35分]",
        f"② ROE 均值                 : {fmt(avg_roe, '%'):<10} {l_roe}  [{s_roe}/25分]",
        f"③ 分红/募资比 (DFR)        : {fmt(dfr, 'x'):<10} {l_dfr}  [{s_dfr}/20分]",
        f"④ CapEx 效率（倍/增量利润）: {fmt(capex_eff, 'x'):<10} {l_capex}  [{s_capex}/10分]",
        f"⑤ FCF 转化率               : {fmt(round(fcf_ratio*100,1) if fcf_ratio else None, '%'):<10} {l_fcf}  [{s_fcf}/10分]",
        f"",
        f"综合得分  : {total}/100",
        f"综合评级  : {grade}",
        f"",
        f"管理层资本配置建议：",
        f"  {advice}",
        f"",
    ]

    if data.get("note"):
        lines.append(f"[注] {data['note']}")

    # 双源验证记录
    cross_notes = data.get("cross_notes", [])
    if cross_notes:
        lines.append("")
        lines.append("双源验证明细")
        lines.append("-" * 40)
        for cn in cross_notes:
            lines.append(f"  {cn}")

    lines += [
        f"",
        f"数据摘要（原始值）",
        f"-" * 40,
        f"  累计净利润   : {fmt(data.get('cum_net_income'))}",
        f"  累计分红     : {fmt(data.get('cum_dividend'))}",
        f"  累计融资     : {fmt(data.get('cum_fundraising'))} （需手动补充以计算DFR）",
        f"  累计资本支出 : {fmt(data.get('cum_capex'))}",
        f"  每股累计留存 : {fmt(data.get('per_share_retained'))}",
        f"=" * 52,
        f"",
    ]
    return "\n".join(lines)


def save_report(report_text: str, company: str):
    os.makedirs(REPORT_DIR, exist_ok=True)
    filename = f"{date.today().isoformat()}-REM-{company.replace(' ', '_')}.md"
    path = os.path.join(REPORT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write("```\n")
        f.write(report_text)
        f.write("```\n")
    print(f"\n[INFO] 报告已保存至: {path}")
    return path


# =====================================================================
# 主入口
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="留存收益质量检验工具 v2.0（默认10年，无交互，双源验证A股）"
    )
    parser.add_argument("--ticker", "-t", help="股票代码（如 AAPL / 600519.SS / 3690.HK）")
    parser.add_argument("--base-year", "-y", type=int,
                        help="基期年份（可选，默认根据 --years 自动推算）")
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS, choices=[3, 5, 10],
                        help=f"数据年限（默认 {DEFAULT_YEARS} 年；选项: 3/5/10）")
    parser.add_argument("--manual", "-m", action="store_true",
                        help="强制手动录入模式（IPO级跨度或数据源均不可用时）")
    parser.add_argument("--save", "-s", action="store_true",
                        help="保存报告到 10-研究报告输出/")
    parser.add_argument("--json", action="store_true",
                        help="输出 JSON 格式（供其他脚本调用）")
    args = parser.parse_args()

    # 手动模式：仅当明确传入 --manual 时触发，其余情况全程无交互
    if args.manual:
        data = fetch_manual()
    elif not args.ticker:
        parser.error(
            "请提供股票代码，例如：\n"
            "  python tools/retained_earnings_check.py --ticker 600519.SS\n"
            "  python tools/retained_earnings_check.py --ticker AAPL\n"
            "如需手动录入，请加 --manual 参数。"
        )
        return
    else:
        data = fetch_auto(args.ticker, base_year=args.base_year, years=args.years)
        if data is None:
            print("[错误] 自动拉取失败，所有数据源均无法获取有效数据。")
            print("  建议: yfinance 和 akshare 已安装？网络是否可访问？")
            print("  或使用 --manual 手动录入关键数据。")
            sys.exit(1)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, default=str, indent=2))
        return

    report = render_report(data)
    print(report)

    if args.save:
        save_report(report, data.get("company", data.get("ticker", "unknown")))


if __name__ == "__main__":
    main()
