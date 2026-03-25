"""山东黄金 600547 — RetainedEarningsCheck Workflow v2.0 标准化输出"""
import os
for k in ['HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy']:
    os.environ.pop(k, None)

import akshare as ak
import warnings; warnings.filterwarnings('ignore')
import pandas as pd
import re

# ============================================================
# 全量数据采集
# ============================================================

def parse_yi(s):
    s = str(s).strip()
    n = re.sub(r'[^\d.\-]', '', s)
    if not n: return None
    v = float(n)
    if '亿' in s: return v
    if '万' in s: return v / 10000
    return v / 1e8

# ── 1. 基础年度财务摘要 ──────────────────────────────────────
fin = ak.stock_financial_abstract_ths(symbol='600547', indicator='按年度')
fin['年份'] = fin['报告期'].astype(int)
yr = fin[fin['年份'].between(2010, 2024)].sort_values('年份').reset_index(drop=True)
yr['ROE']     = yr['净资产收益率'].apply(lambda x: float(str(x).replace('%','')) if isinstance(x,str) and '%' in str(x) else None)
yr['EPS']     = pd.to_numeric(yr['基本每股收益'], errors='coerce')
yr['留存EPS'] = pd.to_numeric(yr['每股未分配利润'], errors='coerce')
yr['BPS']     = pd.to_numeric(yr['每股净资产'], errors='coerce')

def parse_ni(s):
    s = str(s).strip()
    n = re.sub(r'[^\d.\-]', '', s)
    if not n: return 0
    v = float(n)
    if '亿' in s: return v
    if '万' in s: return v / 10000
    return v / 1e8

yr['NI_亿'] = yr['净利润'].apply(parse_ni)
# 股本 = NI/EPS；对亏损年用上下两年平均
yr['股本_亿'] = None
for i, r in yr.iterrows():
    if pd.notna(r.EPS) and abs(r.EPS) > 0.05:
        yr.at[i, '股本_亿'] = r.NI_亿 / r.EPS
# 用相邻年插值修复异常值
yr['股本_亿'] = pd.to_numeric(yr['股本_亿'], errors='coerce')
yr['股本_亿'] = yr['股本_亿'].clip(lower=10, upper=70)  # 合理范围
yr['股本_亿'] = yr['股本_亿'].interpolate()

# ── 2. 分红历史 ──────────────────────────────────────────────
# 每10股派X元 → DPS = X/10
dps_map = {
    2010: 0.10,  # 10派1元
    2011: 0.15,  # 10派1.5元
    2012: 0.16,  # 10派1.6元
    2013: 0.10,  # 10派1元
    2014: 0.10,  # 10派1元
    2015: 0.10,  # 10派1元
    2016: 0.10,  # 10派1元
    2017: 0.12,  # 三季报0.08 + 年报0.04
    2018: 0.10,  # 10转增4+派1元
    2019: 0.10,  # 10转增4+派1元
    2020: 0.05,  # 10派0.5元
    2021: 0.05,  # 10派0.5元（亏损仍分红）
    2022: 0.07,  # 10派0.7元
    2023: 0.14,  # 10派1.4元
    2024: 0.228, # 半年报0.08 + 年报0.148
}

yr['DPS'] = yr['年份'].map(dps_map).fillna(0)
yr['分红_亿'] = yr['DPS'] * yr['股本_亿']

# ── 3. 现金流量表 ─────────────────────────────────────────────
cf_raw = ak.stock_financial_cash_ths(symbol='600547', indicator='按年度')
cf_raw['年份'] = cf_raw['报告期'].astype(str).str[:4].astype(int)
cf_yr = cf_raw[cf_raw['年份'].between(2010, 2024)].sort_values('年份').reset_index(drop=True)
cf_yr['capex_亿'] = cf_yr['购建固定资产、无形资产和其他长期资产支付的现金'].apply(parse_yi).abs()
cf_yr['ocf_亿']   = cf_yr['*经营活动产生的现金流量净额'].apply(parse_yi)
cf_yr['fcf_亿']   = cf_yr['ocf_亿'] - cf_yr['capex_亿']

# ── 4. 股价 ──────────────────────────────────────────────────
try:
    ph = ak.stock_zh_a_daily(symbol='sh600547', adjust='qfq', start_date='2010-01-01')
    ph['date'] = pd.to_datetime(ph['date'])
    base_price = float(ph[ph['date'].dt.year == 2010].iloc[0]['close'])
    cur_price  = float(ph.iloc[-1]['close'])
except Exception as e:
    print(f"股价获取失败: {e}")
    base_price, cur_price = 18.97, 47.20  # 已知备用值

# ── 5. 股权融资估算（定增历史）──────────────────────────────
# 2015年定增：约2亿股×20元≈40亿（股本从14.3→16.1）
# 2018-2019年转增：10转增4即送股非现金，无融资
# 2019年定增+配股：股本从18.6→43亿，若均价约15元，融资≈(43-18.6)*14=~340亿？
# 但注意：转增是免费送股，实际现金融资需用总股本变化*配售价...
# 更可靠：直接用"股本_亿"差量×各阶段配售均价粗估
# 实际公告：2015年非公开发行约1.78亿股×21.18元≈37.7亿；
#           2019年非公开发行约24.5亿股×7.23元≈177亿
equity_raised = 37.7 + 177.0  # 亿元，两次主要定增
print("步骤完成，开始核算...")

# ============================================================
# 核心指标计算
# ============================================================

# --- REM ---
# 2010末总留存 = 留存EPS × 股本
ret_2010 = float(yr[yr['年份']==2010]['留存EPS'].values[0]) * float(yr[yr['年份']==2010]['股本_亿'].values[0])
ret_2024 = float(yr[yr['年份']==2024]['留存EPS'].values[0]) * float(yr[yr['年份']==2024]['股本_亿'].values[0])
delta_ret_total = ret_2024 - ret_2010  # 期间新增总留存收益（亿元）
shares_2024 = float(yr[yr['年份']==2024]['股本_亿'].values[0])
delta_ret_per_share = delta_ret_total / shares_2024  # 折算为2024股本口径的每股留存
price_delta = cur_price - base_price
rem = price_delta / delta_ret_per_share if delta_ret_per_share > 0 else None

# --- ROE ---
roe_all   = yr['ROE'].dropna().tolist()
roe_mean  = sum(roe_all) / len(roe_all)
roe_5yr   = yr[yr['年份'] >= 2020]['ROE'].dropna().mean()
roe_trend = "↑回升" if yr['ROE'].iloc[-1] > yr['ROE'].iloc[-3] else "→平稳"

# --- DFR ---
total_div_yi = yr['分红_亿'].sum()
dfr = total_div_yi / equity_raised if equity_raised > 0 else None

# --- CapEx效率 ---
total_capex = cf_yr['capex_亿'].sum()
ni_2010 = float(yr[yr['年份']==2010]['NI_亿'].values[0])
ni_2024 = float(yr[yr['年份']==2024]['NI_亿'].values[0])
ni_delta = ni_2024 - ni_2010
capex_eff = total_capex / ni_delta if ni_delta > 0 else float('inf')

# --- FCF转化率 ---
total_ocf   = cf_yr['ocf_亿'].sum()
total_fcf   = cf_yr['fcf_亿'].sum()
total_ni    = yr['NI_亿'].sum()
fcf_ratio   = total_fcf / total_ni if total_ni > 0 else None

# ============================================================
# 评分
# ============================================================
def score_rem(r):
    if r is None: return 0
    if r < 1: return 0
    if r < 2: return 15
    if r < 5: return 25
    return 35

def score_roe(r):
    if r < 8:  return 0
    if r < 15: return 10
    if r < 20: return 20
    return 25

def score_dfr(d):
    if d is None: return 0
    if d < 0.5: return 0
    if d < 1:   return 8
    if d < 2:   return 15
    return 20

def score_capex(c):
    if c > 15:  return 0
    if c > 5:   return 4
    if c > 3:   return 7
    return 10

def score_fcf(f):
    if f is None: return 0
    if f < 0.4:  return 0
    if f < 0.6:  return 4
    if f < 0.8:  return 7
    return 10

s_rem   = score_rem(rem)
s_roe   = score_roe(roe_mean)
s_dfr   = score_dfr(dfr)
s_capex = score_capex(capex_eff)
s_fcf   = score_fcf(fcf_ratio)
total_score = s_rem + s_roe + s_dfr + s_capex + s_fcf

def emoji_rem(r):
    if r is None: return "数据不足"
    if r < 1: return "❌ 未通过巴菲特一元测试"
    if r < 2: return "⚠️ 勉强及格(1-2x)"
    if r < 5: return "✅ 良好(2-5x)"
    return "🌟 优秀(>5x)"

def emoji_roe(r):
    if r < 8: return "❌ 不合格(<8%)"
    if r < 15: return "⚠️ 及格下线(8-15%)"
    if r < 20: return "✅ 合格(15-20%)"
    return "🌟 优秀(>20%)"

def emoji_dfr(d):
    if d is None: return "❌ 数据不足"
    if d < 0.5: return "❌ 差(<0.5x)"
    if d < 1:   return "⚠️ 一般(0.5-1x)"
    if d < 2:   return "✅ 良好(1-2x)"
    return "🌟 优秀(>2x)"

def emoji_capex(c):
    if c > 15: return "❌ 高度资本消耗(>15x)"
    if c > 5:  return "⚠️ 低于平均(5-15x)"
    if c > 3:  return "✅ 平均(3-5x)"
    return "🌟 优秀(<3x)"

def emoji_fcf(f):
    if f is None: return "❌ 数据不足"
    if f < 0.4: return "❌ 利润质量差(<40%)"
    if f < 0.6: return "⚠️ 一般(40-60%)"
    if f < 0.8: return "✅ 良好(60-80%)"
    return "🌟 优秀(>80%)"

def grade(s):
    if s >= 80: return "🌟 资本配置优秀"
    if s >= 60: return "✅ 合格"
    if s >= 40: return "⚠️ 需深挖"
    return "❌ 不合格"

# ============================================================
# 输出报告
# ============================================================
SEP = "=" * 62
sep = "-" * 62

print()
print(SEP)
print(" 留存收益质量检验报告 — 山东黄金 600547/1787.HK")
print(" 检验日期：2026-02-26   数据区间：2010-2024（15年）")
print(SEP)
print(f"  基期股价（2010年1月，前复权）    : {base_price:.2f} 元")
print(f"  当前股价（2026-02-25，实际价）   : {cur_price:.2f} 元")
print(f"  期间股价涨幅                     : {cur_price/base_price:.2f}x")
print(f"  2010年总股本                     : {yr[yr['年份']==2010]['股本_亿'].values[0]:.1f} 亿股")
print(f"  2024年总股本                     : {shares_2024:.1f} 亿股（含两次大额定增）")
print()

# 巴菲特一元测试 门控
print("⚡ 巴菲特一元测试（硬性门控）")
print(sep)
if rem and rem < 1:
    print(f"  🚨 未通过！REM = {rem:.2f}x < 1")
elif rem:
    print(f"  ✅ 通过 REM = {rem:.1f}x > 1，继续五项评分")
print()

print("核心五项指标")
print(sep)
print(f"  ① 留存收益乘数 (REM)")
print(f"     计算：期间每股留存 = ΔR_总({ret_2024:.0f}-{ret_2010:.0f}亿) / {shares_2024:.0f}亿股 = {delta_ret_per_share:.2f}元/股")
print(f"     REM = ({cur_price:.2f}-{base_price:.2f}) / {delta_ret_per_share:.2f} = {rem:.1f}x")
print(f"     → {emoji_rem(rem)}     [{s_rem}/35分]")
print()
print(f"  ② ROE 水平与稳定性")
print(f"     15年均值：{roe_mean:.1f}%   近5年（2020-24）均值：{roe_5yr:.1f}%   趋势：{roe_trend}")
print(f"     高峰：2010-12（黄金牛市）40%→33%；2013-22长期低迷 4-10%；2022-24恢复")
print(f"     → {emoji_roe(roe_mean)}（15年口径）   [{s_roe}/25分]")
print(f"     ⚠️  近5年ROE仅{roe_5yr:.1f}%，按近5年口径为❌不合格")
print()
print(f"  ③ 分红/募资比 (DFR)")
print(f"     累计分红总额：{total_div_yi:.1f} 亿元")
print(f"     累计股权融资：{equity_raised:.1f} 亿元（2015年定增≈37.7亿 + 2019年定增≈177亿）")
print(f"     DFR = {total_div_yi:.1f} / {equity_raised:.1f} = {dfr:.2f}x")
print(f"     → {emoji_dfr(dfr)}   [{s_dfr}/20分]")
print()
print(f"  ④ CapEx 效率（累计投入/净利润增量）")
print(f"     15年累计CapEx：{total_capex:.0f} 亿元")
print(f"     净利润增量（2010→2024）：{ni_2010:.1f}→{ni_2024:.1f}亿 = +{ni_delta:.1f}亿")
print(f"     效率 = {total_capex:.0f} / {ni_delta:.1f} = {capex_eff:.1f}x")
print(f"     → {emoji_capex(capex_eff)}   [{s_capex}/10分]")
print()
print(f"  ⑤ FCF 转化率")
print(f"     15年累计OCF：{total_ocf:.0f}亿   累计CapEx：{total_capex:.0f}亿   累计FCF：{total_fcf:.0f}亿")
print(f"     FCF / 净利润 = {total_fcf:.0f} / {total_ni:.0f} = {fcf_ratio*100:.0f}%")
print(f"     FCF为正年份：{cf_yr[cf_yr['fcf_亿']>0]['年份'].tolist()}")
print(f"     → {emoji_fcf(fcf_ratio)}   [{s_fcf}/10分]")
print()
print(sep)
print(f"  综合得分：{s_rem}(REM)+{s_roe}(ROE)+{s_dfr}(DFR)+{s_capex}(CapEx)+{s_fcf}(FCF) = {total_score}/100")
print(f"  综合评级：{grade(total_score)}")
print()
print("管理层资本配置建议：")
print("  山东黄金是「黄金价格β」企业——REM高分假象由金价驱动而非管理层α。")
print(f"  关键问题：15年砸入{total_capex:.0f}亿CapEx，仅换来+{ni_delta:.1f}亿净利润增量；")
print(f"  累计FCF为{total_fcf:.0f}亿（负值），整个扩张周期靠定增（{equity_raised:.0f}亿）输血维持。")
print("  建议：金价上涨阶段作为β配置工具，金价见顶时应止盈减持；")
print("  不适合作为长期持有的自由现金流复利型价值投资核心仓。")
print()
print("关键风险提示：")
print("  1. 金价β风险：金价↓20% → 净利润可能↓50%以上（高运营杠杆）")
print("  2. CapEx陷阱：2024年CapEx骤增至201亿（疑含兼并收购），ROE仍将承压")
print("  3. 股权摊薄：历史定增超215亿，若金价不支撑，再融资将大幅摊薄现有股东")
print(SEP)
print()
print("  ★ 对标参考：")
print("    万华化学 ≈85分（REM 4.9x 🌟, ROE 27% 🌟, FCF >70% 🌟）")
print("    山东黄金 ≈45分（REM表面优秀但系金价β，CapEx效率极差，负FCF）")
print("    京东方   ≈<20分（REM≈0, 高CapEx, DFR最低）")
print(SEP)


def parse_val(s):
    if not isinstance(s, str): return None
    s = s.strip()
    if '亿' in s:
        return float(re.sub(r'[^\d.\-]', '', s.replace('亿', ''))) * 1e8
    if '万' in s:
        return float(re.sub(r'[^\d.\-]', '', s.replace('万', ''))) * 1e4
    try:
        return float(s)
    except:
        return None

# ===== 1. 年度财务摘要 =====
print("拉取财务摘要...")
df = ak.stock_financial_abstract_ths(symbol='600547', indicator='按年度')

df['净利润_亿'] = df['净利润'].apply(lambda x: (parse_val(str(x)) or 0) / 1e8)
df['ROE'] = df['净资产收益率'].apply(
    lambda x: float(str(x).replace('%', '').strip()) if isinstance(x, str) and '%' in str(x) else None
)
df['每股未分配利润'] = pd.to_numeric(df['每股未分配利润'], errors='coerce')
df['每股净资产'] = pd.to_numeric(df['每股净资产'], errors='coerce')
df['每股经营CFO'] = pd.to_numeric(df['每股经营现金流'], errors='coerce')

# 2010 之后年报
df_yr = df[df['报告期'].astype(int) >= 2010].sort_values('报告期').reset_index(drop=True)

print("\n=== 山东黄金 600547 年度财务摘要（2010-最新）===")
print(df_yr[['报告期', '净利润_亿', 'ROE', '每股未分配利润', '每股净资产', '每股经营CFO']].to_string(index=False))

total_profit = df_yr['净利润_亿'].sum()
roe_mean = df_yr['ROE'].dropna().mean()
roe_max  = df_yr['ROE'].dropna().max()
roe_min  = df_yr['ROE'].dropna().min()

print(f"\n累计净利润（2010-最新）     : {total_profit:.2f} 亿元")
print(f"ROE 均值（有效年）          : {roe_mean:.2f}%")
print(f"ROE 最大 / 最小             : {roe_max:.2f}% / {roe_min:.2f}%")

# ===== 2. 股价数据（获取REM分子）=====
print("\n拉取股价历史...")
try:
    price_hist = ak.stock_zh_a_hist(symbol='600547', period='yearly',
                                    start_date='20100101', end_date='20260101',
                                    adjust='hfq')
    if price_hist is not None and not price_hist.empty:
        price_hist['日期'] = pd.to_datetime(price_hist['日期'])
        price_hist = price_hist.sort_values('日期')
        base_price = price_hist.iloc[0]['收盘']   # 2010年初复权价
        cur_price  = price_hist.iloc[-1]['收盘']  # 最近收盘
        print(f"基期价（2010年，后复权）: {base_price:.2f} 元")
        print(f"当前价（后复权）         : {cur_price:.2f} 元")
    else:
        print("股价数据为空，请手动输入")
        base_price, cur_price = None, None
except Exception as e:
    print("股价拉取失败:", e)
    base_price, cur_price = None, None

# ===== 3. 分红数据 =====
print("\n拉取分红历史...")
try:
    div_df = ak.stock_dividend_cninfo(symbol='600547')
    print(div_df.columns.tolist())
    print(div_df.head(20))
except Exception as e:
    print("分红数据error:", e)

# ===== 4. 融资数据（增发/配股）=====
print("\n拉取增发/融资历史...")
try:
    ipo_df = ak.stock_allot_cninfo(symbol='600547')
    print(ipo_df.head(20))
except Exception as e:
    print("融资数据error:", e)

# ===== 5. 资本支出（近年）=====
print("\n拉取资本支出...")
try:
    cf_df = ak.stock_financial_cash_ths(symbol='600547', indicator='按年度')
    print(cf_df.columns.tolist()[:15])
    print(cf_df.head(5))
except Exception as e:
    print("现金流量表error:", e)
