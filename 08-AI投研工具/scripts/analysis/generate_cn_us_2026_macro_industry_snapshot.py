import json
import os
import shutil
import tempfile
import time
from datetime import datetime
from typing import Dict, List, Optional

import akshare as ak
import pandas as pd
import yfinance as yf


def set_ssl_cert_env() -> None:
    try:
        import certifi

        cacert_src = certifi.where()
        cacert_dst = os.path.join(tempfile.gettempdir(), "cacert.pem")
        if not os.path.exists(cacert_dst):
            shutil.copyfile(cacert_src, cacert_dst)
        os.environ["SSL_CERT_FILE"] = cacert_dst
        os.environ["REQUESTS_CA_BUNDLE"] = cacert_dst
        os.environ["CURL_CA_BUNDLE"] = cacert_dst
    except Exception:
        pass


def safe_float(value) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def get_yf_growth(ticker: str) -> Dict:
    out = {
        "ticker": ticker,
        "revenue_growth_0y": None,
        "eps_growth_0y": None,
        "rev_analysts": None,
        "eps_analysts": None,
        "short_name": None,
        "market_cap": None,
        "currency": None,
        "error": None,
    }
    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        out["short_name"] = info.get("shortName")
        out["market_cap"] = safe_float(info.get("marketCap"))
        out["currency"] = info.get("currency")

        rev = tk.revenue_estimate
        if rev is not None and not rev.empty and "0y" in rev.index:
            out["revenue_growth_0y"] = safe_float(rev.loc["0y", "growth"])
            if "numberOfAnalysts" in rev.columns:
                out["rev_analysts"] = safe_float(rev.loc["0y", "numberOfAnalysts"])

        eps = tk.earnings_estimate
        if eps is not None and not eps.empty and "0y" in eps.index:
            out["eps_growth_0y"] = safe_float(eps.loc["0y", "growth"])
            if "numberOfAnalysts" in eps.columns:
                out["eps_analysts"] = safe_float(eps.loc["0y", "numberOfAnalysts"])
    except Exception as e:
        out["error"] = str(e)
    return out


def get_yf_dividend_quality(ticker: str) -> Dict:
    out = {
        "ticker": ticker,
        "dividend_yield": None,
        "payout_ratio": None,
        "free_cash_flow": None,
        "cash_dividends_paid": None,
        "fcf_payout_ratio": None,
        "fcf_cover": None,
        "roe": None,
        "roa": None,
        "total_debt": None,
        "total_cash": None,
        "ebitda": None,
        "net_debt_ebitda": None,
        "short_name": None,
        "market_cap": None,
        "error": None,
    }
    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}

        out["short_name"] = info.get("shortName")
        out["market_cap"] = safe_float(info.get("marketCap"))
        out["dividend_yield"] = safe_float(info.get("dividendYield"))
        out["payout_ratio"] = safe_float(info.get("payoutRatio"))
        out["free_cash_flow"] = safe_float(info.get("freeCashflow"))
        out["roe"] = safe_float(info.get("returnOnEquity"))
        out["roa"] = safe_float(info.get("returnOnAssets"))
        out["total_debt"] = safe_float(info.get("totalDebt"))
        out["total_cash"] = safe_float(info.get("totalCash"))
        out["ebitda"] = safe_float(info.get("ebitda"))

        cf = tk.cashflow
        if cf is not None and not cf.empty and "Cash Dividends Paid" in cf.index:
            dividends = cf.loc["Cash Dividends Paid"].dropna()
            if not dividends.empty:
                out["cash_dividends_paid"] = abs(safe_float(dividends.iloc[0]))

        fcf = out["free_cash_flow"]
        div_paid = out["cash_dividends_paid"]
        if fcf is not None and fcf > 0 and div_paid is not None and div_paid >= 0:
            out["fcf_payout_ratio"] = div_paid / fcf
            if div_paid > 0:
                out["fcf_cover"] = fcf / div_paid

        debt = out["total_debt"]
        cash = out["total_cash"]
        ebitda = out["ebitda"]
        if debt is not None and cash is not None and ebitda is not None and ebitda != 0:
            out["net_debt_ebitda"] = (debt - cash) / ebitda
    except Exception as e:
        out["error"] = str(e)
    return out


def summarize_growth(df: pd.DataFrame) -> pd.DataFrame:
    work = df.dropna(subset=["revenue_growth_0y", "eps_growth_0y"]).copy()
    if work.empty:
        return pd.DataFrame()
    summary = (
        work.groupby(["country", "industry"], as_index=False)
        .agg(
            valid_tickers=("ticker", "count"),
            rev_growth_median=("revenue_growth_0y", "median"),
            eps_growth_median=("eps_growth_0y", "median"),
            rev_growth_mean=("revenue_growth_0y", "mean"),
            eps_growth_mean=("eps_growth_0y", "mean"),
        )
        .sort_values(["country", "rev_growth_median", "eps_growth_median"], ascending=[True, False, False])
    )
    summary["dual_growth_score"] = summary["rev_growth_median"] + summary["eps_growth_median"]
    return summary.sort_values(["country", "dual_growth_score"], ascending=[True, False])


def summarize_dividend(df: pd.DataFrame) -> pd.DataFrame:
    work = df.dropna(subset=["dividend_yield"]).copy()
    if work.empty:
        return pd.DataFrame()
    summary = (
        work.groupby(["country", "industry"], as_index=False)
        .agg(
            valid_tickers=("ticker", "count"),
            div_yield_median=("dividend_yield", "median"),
            div_yield_mean=("dividend_yield", "mean"),
            fcf_payout_median=("fcf_payout_ratio", "median"),
            fcf_cover_median=("fcf_cover", "median"),
            roe_median=("roe", "median"),
            net_debt_ebitda_median=("net_debt_ebitda", "median"),
        )
        .sort_values(["country", "div_yield_median"], ascending=[True, False])
    )
    return summary


def get_ak_eps_forecast(codes: List[str]) -> pd.DataFrame:
    raw = ak.stock_profit_forecast_em().copy()
    cols = list(raw.columns)
    code_col = cols[1]
    name_col = cols[2]
    report_col = cols[3]
    eps25_col = cols[10]
    eps26_col = cols[11]
    raw[code_col] = raw[code_col].astype(str).str.zfill(6)
    out = raw[raw[code_col].isin(set(codes))][[code_col, name_col, report_col, eps25_col, eps26_col]].copy()
    out.columns = ["code", "name", "report_count", "eps_2025_est", "eps_2026_est"]
    out["ak_eps_growth_26"] = out["eps_2026_est"] / out["eps_2025_est"] - 1
    return out


def get_ak_fin_indicators(codes: List[str]) -> pd.DataFrame:
    rows = []
    for code in codes:
        try:
            df = ak.stock_financial_analysis_indicator(symbol=code, start_year="2024")
            if df is None or df.empty:
                continue
            latest = df.iloc[0].to_dict()
            row = {"code": code}
            date_key = next((k for k in latest.keys() if "日期" in k), None)
            roe_key = next((k for k in latest.keys() if "净资产收益率(%)" in k), None)
            payout_key = next((k for k in latest.keys() if "股息发放率(%)" in k), None)
            rev_g_key = next((k for k in latest.keys() if "主营业务收入增长率(%)" in k), None)
            np_g_key = next((k for k in latest.keys() if "净利润增长率(%)" in k), None)
            row["date"] = latest.get(date_key) if date_key else None
            row["roe_pct"] = safe_float(latest.get(roe_key)) if roe_key else None
            row["dividend_payout_pct"] = safe_float(latest.get(payout_key)) if payout_key else None
            row["revenue_growth_pct"] = safe_float(latest.get(rev_g_key)) if rev_g_key else None
            row["net_profit_growth_pct"] = safe_float(latest.get(np_g_key)) if np_g_key else None
            rows.append(row)
        except Exception:
            continue
    return pd.DataFrame(rows)


def fetch_fred_series_latest(series_id: str) -> Dict:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    s = pd.read_csv(url)
    s.columns = ["date", "value"]
    s["date"] = pd.to_datetime(s["date"], errors="coerce")
    s["value"] = pd.to_numeric(s["value"], errors="coerce")
    s = s.dropna().sort_values("date")
    if s.empty:
        return {"series": series_id, "date": None, "value": None}
    last = s.iloc[-1]
    return {"series": series_id, "date": last["date"].strftime("%Y-%m-%d"), "value": float(last["value"])}


def fetch_us_macro_snapshot() -> Dict:
    gdp = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDPC1")
    gdp.columns = ["date", "value"]
    gdp["date"] = pd.to_datetime(gdp["date"], errors="coerce")
    gdp["value"] = pd.to_numeric(gdp["value"], errors="coerce")
    gdp = gdp.dropna().sort_values("date")
    gdp["yoy"] = gdp["value"].pct_change(4)
    gdp_last = gdp.iloc[-1]

    core_cpi = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPILFESL")
    core_cpi.columns = ["date", "value"]
    core_cpi["date"] = pd.to_datetime(core_cpi["date"], errors="coerce")
    core_cpi["value"] = pd.to_numeric(core_cpi["value"], errors="coerce")
    core_cpi = core_cpi.dropna().sort_values("date")
    core_cpi["yoy"] = core_cpi["value"].pct_change(12)
    core_cpi_last = core_cpi.iloc[-1]

    fed_funds = fetch_fred_series_latest("DFF")
    t10y2y = fetch_fred_series_latest("T10Y2Y")
    unrate = fetch_fred_series_latest("UNRATE")

    return {
        "real_gdp_yoy": {
            "date": gdp_last["date"].strftime("%Y-%m-%d"),
            "value": float(gdp_last["yoy"]),
        },
        "core_cpi_yoy": {
            "date": core_cpi_last["date"].strftime("%Y-%m-%d"),
            "value": float(core_cpi_last["yoy"]),
        },
        "fed_funds": fed_funds,
        "term_spread_10y_2y": t10y2y,
        "unemployment_rate": unrate,
    }


def last_valid_ak_event(df: pd.DataFrame, value_col: str, date_col: str = "日期") -> Dict:
    work = df.copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    work = work.dropna(subset=[date_col, value_col]).sort_values(date_col)
    if work.empty:
        return {"date": None, "value": None}
    row = work.iloc[-1]
    return {"date": row[date_col].strftime("%Y-%m-%d"), "value": float(row[value_col])}


def fetch_cn_macro_snapshot() -> Dict:
    gdp = ak.macro_china_gdp_yearly()
    cpi = ak.macro_china_cpi_yearly()
    ppi = ak.macro_china_ppi_yearly()
    m2 = ak.macro_china_m2_yearly()
    pmi = ak.macro_china_pmi_yearly()
    lpr = ak.macro_china_lpr()
    lpr["TRADE_DATE"] = pd.to_datetime(lpr["TRADE_DATE"], errors="coerce")
    lpr = lpr.dropna(subset=["TRADE_DATE"]).sort_values("TRADE_DATE")
    lpr_last = lpr.iloc[-1]

    return {
        "gdp_yoy": last_valid_ak_event(gdp, value_col="今值", date_col="日期"),
        "cpi_yoy": last_valid_ak_event(cpi, value_col="今值", date_col="日期"),
        "ppi_yoy": last_valid_ak_event(ppi, value_col="今值", date_col="日期"),
        "m2_yoy": last_valid_ak_event(m2, value_col="今值", date_col="日期"),
        "official_pmi": last_valid_ak_event(pmi, value_col="今值", date_col="日期"),
        "lpr": {
            "date": lpr_last["TRADE_DATE"].strftime("%Y-%m-%d"),
            "lpr_1y": safe_float(lpr_last.get("LPR1Y")),
            "lpr_5y": safe_float(lpr_last.get("LPR5Y")),
        },
    }


def main() -> None:
    set_ssl_cert_env()

    output_dir = "10-研究报告输出"
    os.makedirs(output_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    growth_map = {
        "US": {
            "AI半导体与存储": ["NVDA", "AMD", "AVGO", "MU", "MRVL"],
            "电网与数据中心电力设备": ["VRT", "ETN", "HUBB", "PWR", "GEV"],
            "网络安全SaaS": ["CRWD", "PANW", "FTNT", "ZS", "NET"],
        },
        "CN": {
            "算力硬件与光模块": ["300308.SZ", "300502.SZ", "002371.SZ", "601138.SS", "000977.SZ"],
            "动力电池与电车部件": ["300750.SZ", "300014.SZ", "002594.SZ", "002460.SZ", "603799.SS"],
            "消费电子升级链": ["1810.HK", "002475.SZ", "002384.SZ", "000063.SZ"],
        },
    }

    dividend_map = {
        "US": {
            "综合能源与中游管道": ["XOM", "CVX", "COP", "EOG", "KMI", "ET"],
            "电信运营商": ["VZ", "T", "TMUS"],
            "公用事业": ["SO", "DUK", "AEP", "XEL", "NEE"],
        },
        "CN": {
            "国有大型银行": ["601398.SS", "601288.SS", "601939.SS", "601988.SS", "601658.SS"],
            "电信运营商": ["600941.SS", "601728.SS", "600050.SS", "0941.HK", "0728.HK"],
            "能源煤炭石油": ["601088.SS", "601225.SS", "600188.SS", "601898.SS", "0883.HK", "0386.HK"],
        },
    }

    growth_rows = []
    for country, industries in growth_map.items():
        for industry, tickers in industries.items():
            for ticker in tickers:
                row = get_yf_growth(ticker)
                row["country"] = country
                row["industry"] = industry
                growth_rows.append(row)
                time.sleep(0.1)
    growth_df = pd.DataFrame(growth_rows)
    growth_summary = summarize_growth(growth_df)

    dividend_rows = []
    for country, industries in dividend_map.items():
        for industry, tickers in industries.items():
            for ticker in tickers:
                row = get_yf_dividend_quality(ticker)
                row["country"] = country
                row["industry"] = industry
                dividend_rows.append(row)
                time.sleep(0.1)
    dividend_df = pd.DataFrame(dividend_rows)
    dividend_summary = summarize_dividend(dividend_df)

    cn_growth_codes = sorted({t.split(".")[0] for inds in growth_map["CN"].values() for t in inds if t.endswith(".SS") or t.endswith(".SZ")})
    cn_div_codes = sorted({t.split(".")[0] for inds in dividend_map["CN"].values() for t in inds if t.endswith(".SS") or t.endswith(".SZ")})
    ak_eps_check = get_ak_eps_forecast(cn_growth_codes)
    ak_fin_check = get_ak_fin_indicators(sorted(set(cn_growth_codes + cn_div_codes)))

    us_macro = fetch_us_macro_snapshot()
    cn_macro = fetch_cn_macro_snapshot()

    growth_path = os.path.join(output_dir, f"{today}-中美行业增长-明细.csv")
    growth_summary_path = os.path.join(output_dir, f"{today}-中美行业增长-汇总.csv")
    div_path = os.path.join(output_dir, f"{today}-中美行业分红-明细.csv")
    div_summary_path = os.path.join(output_dir, f"{today}-中美行业分红-汇总.csv")
    ak_eps_path = os.path.join(output_dir, f"{today}-中概A股-盈利预测交叉验证.csv")
    ak_fin_path = os.path.join(output_dir, f"{today}-A股财务指标交叉验证.csv")
    snapshot_path = os.path.join(output_dir, f"{today}-中美宏观产业-数据快照.json")

    growth_df.to_csv(growth_path, index=False, encoding="utf-8-sig")
    growth_summary.to_csv(growth_summary_path, index=False, encoding="utf-8-sig")
    dividend_df.to_csv(div_path, index=False, encoding="utf-8-sig")
    dividend_summary.to_csv(div_summary_path, index=False, encoding="utf-8-sig")
    ak_eps_check.to_csv(ak_eps_path, index=False, encoding="utf-8-sig")
    ak_fin_check.to_csv(ak_fin_path, index=False, encoding="utf-8-sig")

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data_window_note": "yfinance 0y growth interpreted as current fiscal year consensus (2026 in current context); dividend_yield is forward yield field from provider.",
        "growth_summary": growth_summary.to_dict(orient="records"),
        "dividend_summary": dividend_summary.to_dict(orient="records"),
        "us_macro_snapshot": us_macro,
        "cn_macro_snapshot": cn_macro,
        "file_outputs": {
            "growth_detail_csv": growth_path,
            "growth_summary_csv": growth_summary_path,
            "dividend_detail_csv": div_path,
            "dividend_summary_csv": div_summary_path,
            "ak_eps_check_csv": ak_eps_path,
            "ak_fin_check_csv": ak_fin_path,
        },
    }
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Generated files:")
    for p in [growth_path, growth_summary_path, div_path, div_summary_path, ak_eps_path, ak_fin_path, snapshot_path]:
        print(p)

    print("\nTop growth sectors by country:")
    if not growth_summary.empty:
        top_growth = growth_summary.sort_values(["country", "dual_growth_score"], ascending=[True, False]).groupby("country").head(3)
        print(top_growth.to_string(index=False))

    print("\nTop dividend sectors by country:")
    if not dividend_summary.empty:
        top_div = dividend_summary.sort_values(["country", "div_yield_median"], ascending=[True, False]).groupby("country").head(3)
        print(top_div.to_string(index=False))


if __name__ == "__main__":
    main()
