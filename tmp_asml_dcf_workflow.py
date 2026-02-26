import json
import os
import shutil
from datetime import datetime

import numpy as np
import pandas as pd
import certifi
import yfinance as yf


# Workaround for curl_cffi SSL issue on non-ASCII virtualenv paths
os.makedirs("C:/temp", exist_ok=True)
ascii_ca_path = "C:/temp/cacert.pem"
if not os.path.exists(ascii_ca_path):
    shutil.copyfile(certifi.where(), ascii_ca_path)
os.environ["SSL_CERT_FILE"] = ascii_ca_path
os.environ["REQUESTS_CA_BUNDLE"] = ascii_ca_path
os.environ["CURL_CA_BUNDLE"] = ascii_ca_path
os.environ["YF_USE_CURL"] = "0"


def to_float(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


asof = datetime.now().strftime("%Y-%m-%d")

# 1) Core ticker + comps for semiconductor equipment peer sanity
main_ticker = "ASML"
comps = ["AMAT", "LRCX", "KLAC", "TOELY", "TEL.OL"]

# 2) Fetch core market + financial data
main = yf.Ticker(main_ticker)
info = main.info or {}
price_hist = main.history(period="5d")
current_price = to_float(price_hist["Close"].iloc[-1]) if not price_hist.empty else to_float(info.get("currentPrice"))

market_cap = to_float(info.get("marketCap"))
shares = to_float(info.get("sharesOutstanding"))
if shares is None and market_cap and current_price:
    shares = market_cap / current_price

beta = to_float(info.get("beta")) or 1.05

# Balance-sheet style fields (best effort)
cash = to_float(info.get("totalCash")) or 0.0
debt = to_float(info.get("totalDebt")) or 0.0
net_debt = debt - cash

# 3) Pull statements for FCF base + trend
cf = main.cashflow
fin = main.financials
bs = main.balance_sheet

# yfinance uses row labels depending on locale/period; fallback map
possible_cfo = ["Operating Cash Flow", "Total Cash From Operating Activities"]
possible_capex = ["Capital Expenditure", "Capital Expenditures"]
possible_revenue = ["Total Revenue"]
possible_ebit = ["EBIT", "Operating Income"]


def pick_row(df, names):
    if df is None or df.empty:
        return None
    for n in names:
        if n in df.index:
            s = df.loc[n]
            if isinstance(s, pd.Series):
                return s.dropna()
    return None


cfo_s = pick_row(cf, possible_cfo)
capex_s = pick_row(cf, possible_capex)
rev_s = pick_row(fin, possible_revenue)
ebit_s = pick_row(fin, possible_ebit)

latest_revenue = to_float(rev_s.iloc[0]) if rev_s is not None and len(rev_s) > 0 else None
latest_ebit = to_float(ebit_s.iloc[0]) if ebit_s is not None and len(ebit_s) > 0 else None

if cfo_s is not None and capex_s is not None and len(cfo_s) > 0 and len(capex_s) > 0:
    latest_fcf = to_float(cfo_s.iloc[0] + capex_s.iloc[0])  # capex is usually negative
else:
    latest_fcf = None

# 4) If FCF unavailable, fallback from margin heuristic
if latest_fcf is None and latest_revenue is not None:
    fcf_margin_fallback = 0.27
    latest_fcf = latest_revenue * fcf_margin_fallback

if latest_revenue is None:
    raise RuntimeError("无法从 yfinance 获取 ASML 的营收数据，无法执行 DCF。")
if latest_fcf is None:
    raise RuntimeError("无法从 yfinance 获取或估算 ASML 的自由现金流，无法执行 DCF。")

# 5) Peer multiples to inform terminal exit multiple
peer_rows = []
for t in comps:
    try:
        ti = yf.Ticker(t).info or {}
        ev_to_ebitda = to_float(ti.get("enterpriseToEbitda"))
        fwd_pe = to_float(ti.get("forwardPE"))
        rev_growth = to_float(ti.get("revenueGrowth"))
        ebitda_margin = to_float(ti.get("ebitdaMargins"))
        if ev_to_ebitda is not None:
            peer_rows.append(
                {
                    "ticker": t,
                    "ev_to_ebitda": ev_to_ebitda,
                    "forward_pe": fwd_pe,
                    "revenue_growth": rev_growth,
                    "ebitda_margin": ebitda_margin,
                }
            )
    except Exception:
        continue

peer_df = pd.DataFrame(peer_rows)
if peer_df.empty:
    peer_median_ev_ebitda = 18.0
    peer_p25_ev_ebitda = 15.0
    peer_p75_ev_ebitda = 22.0
else:
    peer_positive = peer_df[peer_df["ev_to_ebitda"] > 0]["ev_to_ebitda"]
    if peer_positive.empty:
        peer_positive = peer_df["ev_to_ebitda"]
    peer_median_ev_ebitda = float(peer_positive.median())
    peer_p25_ev_ebitda = float(peer_positive.quantile(0.25))
    peer_p75_ev_ebitda = float(peer_positive.quantile(0.75))

# 6) WACC setup
# Risk-free (fixed proxy) + CAPM
risk_free = 0.043
erp = 0.055
cost_of_equity = risk_free + beta * erp

# Cost of debt (proxy)
pretax_cost_debt = 0.05
# Tax rate from company info or default
effective_tax = to_float(info.get("effectiveTaxRate"))
if effective_tax is None or effective_tax <= 0 or effective_tax >= 0.4:
    effective_tax = 0.20

after_tax_cost_debt = pretax_cost_debt * (1 - effective_tax)

if market_cap is None and shares and current_price:
    market_cap = shares * current_price
if market_cap is None:
    market_cap = 3.5e11

ev_for_weights = market_cap + max(net_debt, 0)
if ev_for_weights <= 0:
    ev_for_weights = market_cap

equity_w = market_cap / ev_for_weights
debt_w = max(net_debt, 0) / ev_for_weights

base_wacc = equity_w * cost_of_equity + debt_w * after_tax_cost_debt
if base_wacc < 0.07:
    base_wacc = 0.07
if base_wacc > 0.12:
    base_wacc = 0.12

# EBITDA margin proxy for exit-multiple terminal value
ebitda_margin_proxy = to_float(info.get("ebitdaMargins"))
if ebitda_margin_proxy is None or ebitda_margin_proxy <= 0:
    ebitda_margin_proxy = 0.37

# 7) Projection assumptions (comps-informed)
# ASML high-quality, but cyclical demand. 5-year explicit forecast.
scenarios = {
    "bear": {
        "growth": [0.06, 0.07, 0.07, 0.06, 0.05],
        "fcf_margin": [0.24, 0.25, 0.25, 0.24, 0.24],
        "wacc": base_wacc + 0.01,
        "tg": 0.025,
        "exit_multiple": peer_p25_ev_ebitda,
    },
    "base": {
        "growth": [0.10, 0.11, 0.10, 0.09, 0.08],
        "fcf_margin": [0.27, 0.28, 0.29, 0.29, 0.29],
        "wacc": base_wacc,
        "tg": 0.03,
        "exit_multiple": peer_median_ev_ebitda,
    },
    "bull": {
        "growth": [0.14, 0.14, 0.13, 0.11, 0.10],
        "fcf_margin": [0.30, 0.31, 0.31, 0.32, 0.32],
        "wacc": max(base_wacc - 0.01, 0.07),
        "tg": 0.035,
        "exit_multiple": peer_p75_ev_ebitda,
    },
}


def dcf_from_assumptions(rev0, shares_out, net_debt_value, growth, margins, wacc, tg, ebitda_margin, exit_multiple):
    rev = rev0
    fcfs = []
    ebitdas = []
    for g, m in zip(growth, margins):
        rev = rev * (1 + g)
        fcfs.append(rev * m)
        ebitdas.append(rev * ebitda_margin)

    pv_fcfs = 0.0
    for i, f in enumerate(fcfs, start=1):
        period = i - 0.5
        pv_fcfs += f / ((1 + wacc) ** period)

    terminal_fcf = fcfs[-1] * (1 + tg)
    terminal_value_perp = terminal_fcf / (wacc - tg)
    terminal_value_exit = ebitdas[-1] * exit_multiple
    terminal_value = 0.5 * terminal_value_perp + 0.5 * terminal_value_exit
    pv_terminal = terminal_value / ((1 + wacc) ** (len(fcfs) - 0.5))

    ev = pv_fcfs + pv_terminal
    eq = ev - net_debt_value
    px = eq / shares_out if shares_out and shares_out > 0 else None
    tv_pct = pv_terminal / ev if ev > 0 else None
    return {
        "enterprise_value": ev,
        "equity_value": eq,
        "implied_price": px,
        "pv_explicit_fcf": pv_fcfs,
        "pv_terminal": pv_terminal,
        "terminal_pct_ev": tv_pct,
        "terminal_fcf": terminal_fcf,
        "terminal_value_perpetuity": terminal_value_perp,
        "terminal_value_exit_multiple": terminal_value_exit,
        "exit_multiple_used": exit_multiple,
    }


results = {}
for name, s in scenarios.items():
    results[name] = dcf_from_assumptions(
        latest_revenue,
        shares,
        net_debt,
        s["growth"],
        s["fcf_margin"],
        s["wacc"],
        s["tg"],
        ebitda_margin_proxy,
        s["exit_multiple"],
    )

# 8) Sensitivity matrix (base growth/margins)
wacc_grid = [round(base_wacc - 0.01 + i * 0.005, 4) for i in range(5)]
tg_grid = [0.02, 0.025, 0.03, 0.035, 0.04]

sensitivity = []
for w in wacc_grid:
    row = {"wacc": w}
    for tg in tg_grid:
        if w <= tg + 0.005:
            row[f"tg_{tg:.3f}"] = None
            continue
        out = dcf_from_assumptions(
            latest_revenue,
            shares,
            net_debt,
            scenarios["base"]["growth"],
            scenarios["base"]["fcf_margin"],
            w,
            tg,
            ebitda_margin_proxy,
            scenarios["base"]["exit_multiple"],
        )
        row[f"tg_{tg:.3f}"] = out["implied_price"]
    sensitivity.append(row)

# 9) Cross-check implied terminal multiple in base case
# Approximate terminal EBITDA using EBITDA margin proxy from info
rev = latest_revenue
for g in scenarios["base"]["growth"]:
    rev = rev * (1 + g)
terminal_ebitda = rev * ebitda_margin_proxy
base_ev = results["base"]["enterprise_value"]
implied_terminal_ev_ebitda = base_ev / terminal_ebitda if terminal_ebitda > 0 else None

# 10) Build output payload
payload = {
    "asof": asof,
    "ticker": main_ticker,
    "current_price": current_price,
    "market_cap": market_cap,
    "shares_outstanding": shares,
    "beta": beta,
    "cash": cash,
    "debt": debt,
    "net_debt": net_debt,
    "latest_revenue": latest_revenue,
    "latest_fcf": latest_fcf,
    "tax_rate": effective_tax,
    "risk_free": risk_free,
    "erp": erp,
    "cost_of_equity": cost_of_equity,
    "after_tax_cost_debt": after_tax_cost_debt,
    "base_wacc": base_wacc,
    "peer_table": peer_df.to_dict(orient="records"),
    "peer_stats": {
        "median_ev_ebitda": peer_median_ev_ebitda,
        "p25_ev_ebitda": peer_p25_ev_ebitda,
        "p75_ev_ebitda": peer_p75_ev_ebitda,
    },
    "scenarios": scenarios,
    "dcf_results": results,
    "sensitivity_wacc_tg": sensitivity,
    "implied_terminal_ev_ebitda_base": implied_terminal_ev_ebitda,
}

with open("tmp_asml_dcf_output.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print("WROTE tmp_asml_dcf_output.json")
print(json.dumps({
    "asof": asof,
    "current_price": current_price,
    "base_price": results["base"]["implied_price"],
    "bear_price": results["bear"]["implied_price"],
    "bull_price": results["bull"]["implied_price"],
    "base_wacc": base_wacc,
    "base_tg": scenarios["base"]["tg"],
    "peer_median_ev_ebitda": peer_median_ev_ebitda,
    "implied_terminal_ev_ebitda_base": implied_terminal_ev_ebitda,
}, ensure_ascii=False, indent=2))