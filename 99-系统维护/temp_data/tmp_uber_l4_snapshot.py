import json
import math
import os
import shutil
import tempfile
from datetime import datetime, timezone

import certifi
import requests
import yfinance as yf
import pandas as pd
from io import StringIO

ASOF = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
UBER = "UBER"
COMPS = ["LYFT", "DASH", "ABNB", "GRAB", "BKNG"]


def ensure_ca_bundle_ascii_path() -> str:
    src = certifi.where()
    dst = os.path.join(tempfile.gettempdir(), "cacert.pem")
    try:
        if (not os.path.exists(dst)) or (os.path.getsize(dst) != os.path.getsize(src)):
            shutil.copyfile(src, dst)
    except Exception:
        dst = src

    os.environ.setdefault("SSL_CERT_FILE", dst)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", dst)
    os.environ.setdefault("CURL_CA_BUNDLE", dst)
    return dst


def fnum(x):
    try:
        if x is None:
            return None
        if isinstance(x, float) and math.isnan(x):
            return None
        return float(x)
    except Exception:
        return None


def safe_get_series_value(df, row_name, col_idx=0):
    try:
        if df is None or df.empty:
            return None
        if row_name not in df.index:
            return None
        cols = list(df.columns)
        if not cols:
            return None
        val = df.loc[row_name, cols[col_idx]]
        return fnum(val)
    except Exception:
        return None


def safe_get_row_map(df, row_name):
    if df is None or df.empty or row_name not in df.index:
        return {}
    out = {}
    for col in df.columns:
        try:
            k = str(col.date())
        except Exception:
            k = str(col)
        out[k] = fnum(df.loc[row_name, col])
    return out


def cagr(start, end, years):
    if start is None or end is None or years <= 0:
        return None
    if start <= 0 or end <= 0:
        return None
    return (end / start) ** (1 / years) - 1


def yfinance_snapshot(ticker: str):
    t = yf.Ticker(ticker)
    try:
        info = t.get_info()
    except Exception:
        info = getattr(t, "info", {}) or {}

    try:
        fast = dict(getattr(t, "fast_info", {}) or {})
    except Exception:
        fast = {}

    financials = t.financials
    cashflow = t.cashflow
    balance = t.balance_sheet
    qf = t.quarterly_financials

    last_price = (
        fast.get("last_price")
        or fast.get("lastPrice")
        or info.get("currentPrice")
        or info.get("regularMarketPrice")
    )

    rev_map = safe_get_row_map(financials, "Total Revenue")
    gp_map = safe_get_row_map(financials, "Gross Profit")
    operating_income_map = safe_get_row_map(financials, "Operating Income") or safe_get_row_map(
        financials, "Total Operating Income As Reported"
    )
    ebit_map = safe_get_row_map(financials, "EBIT")
    ni_map = safe_get_row_map(
        financials, "Net Income From Continuing Operation Net Minority Interest"
    ) or safe_get_row_map(financials, "Net Income")
    fcf_map = safe_get_row_map(cashflow, "Free Cash Flow")
    cfo_map = safe_get_row_map(cashflow, "Operating Cash Flow")
    capex_map = safe_get_row_map(cashflow, "Capital Expenditure")
    debt_map = safe_get_row_map(balance, "Total Debt")
    cash_map = safe_get_row_map(balance, "Cash And Cash Equivalents")
    equity_map = safe_get_row_map(balance, "Stockholders Equity")
    assets_map = safe_get_row_map(balance, "Total Assets")

    # Revenue CAGR using available annual columns (latest vs 3 years ago).
    rev_years = sorted(rev_map.keys())
    rev_cagr_3y = None
    if len(rev_years) >= 4:
        start_key = rev_years[-4]
        end_key = rev_years[-1]
        rev_cagr_3y = cagr(rev_map[start_key], rev_map[end_key], 3)

    # Latest year metrics from annual statements.
    latest_year = sorted(rev_map.keys())[-1] if rev_map else None
    revenue_latest = rev_map.get(latest_year) if latest_year else None
    gross_profit_latest = gp_map.get(latest_year) if latest_year else None
    operating_income_latest = (
        operating_income_map.get(latest_year) if latest_year else None
    )
    ebit_latest = ebit_map.get(latest_year) if latest_year else None
    ni_latest = ni_map.get(latest_year) if latest_year else None
    fcf_latest = fcf_map.get(latest_year) if latest_year else None
    cfo_latest = cfo_map.get(latest_year) if latest_year else None
    capex_latest = capex_map.get(latest_year) if latest_year else None
    debt_latest = debt_map.get(latest_year) if latest_year else None
    cash_latest = cash_map.get(latest_year) if latest_year else None
    equity_latest = equity_map.get(latest_year) if latest_year else None
    assets_latest = assets_map.get(latest_year) if latest_year else None
    net_debt_latest = (
        (debt_latest - cash_latest)
        if (debt_latest is not None and cash_latest is not None)
        else None
    )

    # Fallback for tickers where annual statements are incomplete (e.g., some ADRs).
    quality_flags = []
    if revenue_latest is None:
        revenue_latest = fnum(info.get("totalRevenue"))
        if revenue_latest is not None:
            quality_flags.append("revenue_fallback_info_totalRevenue")
    if fcf_latest is None:
        fcf_latest = fnum(info.get("freeCashflow"))
        if fcf_latest is not None:
            quality_flags.append("fcf_fallback_info_freeCashflow")
    if cfo_latest is None:
        cfo_latest = fnum(info.get("operatingCashflow"))
        if cfo_latest is not None:
            quality_flags.append("cfo_fallback_info_operatingCashflow")
    if debt_latest is None:
        debt_latest = fnum(info.get("totalDebt"))
        if debt_latest is not None:
            quality_flags.append("debt_fallback_info_totalDebt")
    if cash_latest is None:
        cash_latest = fnum(info.get("totalCash"))
        if cash_latest is not None:
            quality_flags.append("cash_fallback_info_totalCash")

    gross_margin = (
        gross_profit_latest / revenue_latest
        if (gross_profit_latest and revenue_latest)
        else None
    )
    operating_margin = (
        operating_income_latest / revenue_latest
        if (operating_income_latest and revenue_latest)
        else None
    )
    ebit_margin = (
        ebit_latest / revenue_latest
        if (ebit_latest and revenue_latest)
        else None
    )
    net_margin = ni_latest / revenue_latest if (ni_latest and revenue_latest) else None
    fcf_margin = (
        fcf_latest / revenue_latest if (fcf_latest and revenue_latest) else None
    )
    if gross_margin is None:
        gross_margin = fnum(info.get("grossMargins"))
        if gross_margin is not None:
            quality_flags.append("gross_margin_fallback_info")
    if operating_margin is None:
        operating_margin = fnum(info.get("operatingMargins"))
        if operating_margin is not None:
            quality_flags.append("operating_margin_fallback_info")
    if net_margin is None:
        net_margin = fnum(info.get("profitMargins"))
        if net_margin is not None:
            quality_flags.append("net_margin_fallback_info")

    market_cap = fnum(info.get("marketCap"))
    enterprise_value = fnum(info.get("enterpriseValue"))
    fcf_yield = fcf_latest / market_cap if (fcf_latest and market_cap) else None

    # DuPont for latest annual year.
    roe_dupont = None
    if ni_latest and revenue_latest and assets_latest and equity_latest and equity_latest != 0:
        net_profit_margin = ni_latest / revenue_latest
        asset_turnover = revenue_latest / assets_latest
        equity_multiplier = assets_latest / equity_latest
        roe_dupont = net_profit_margin * asset_turnover * equity_multiplier

    # Approx ROIC and MROIC proxy.
    invested_capital = None
    roic = None
    if debt_latest is not None and equity_latest is not None and cash_latest is not None:
        invested_capital = debt_latest + equity_latest - cash_latest
    if operating_income_latest is not None and invested_capital not in (None, 0):
        nopat = operating_income_latest * (1 - 0.21)
        roic = nopat / invested_capital

    # quarterly revenue run-rate
    qrev_map = safe_get_row_map(qf, "Total Revenue")

    return {
        "source": "yfinance",
        "asof_local": ASOF,
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName"),
        "currency": info.get("currency"),
        "exchange": info.get("exchange") or info.get("fullExchangeName"),
        "price": fnum(last_price),
        "market_cap": market_cap,
        "enterprise_value": enterprise_value,
        "trailing_pe": fnum(info.get("trailingPE")),
        "forward_pe": fnum(info.get("forwardPE")),
        "price_to_book": fnum(info.get("priceToBook")),
        "price_to_sales_ttm": fnum(info.get("priceToSalesTrailing12Months")),
        "ev_to_ebitda": fnum(info.get("enterpriseToEbitda")),
        "analyst_target_mean_price": fnum(info.get("targetMeanPrice")),
        "analyst_count": fnum(info.get("numberOfAnalystOpinions")),
        "recommendation_mean": fnum(info.get("recommendationMean")),
        "recommendation_key": info.get("recommendationKey"),
        "shares_outstanding": fnum(info.get("sharesOutstanding")),
        "latest_annual_year": latest_year,
        "latest_annual": {
            "revenue": revenue_latest,
            "gross_profit": gross_profit_latest,
            "operating_income": operating_income_latest,
            "ebit": ebit_latest,
            "net_income": ni_latest,
            "operating_cashflow": cfo_latest,
            "free_cashflow": fcf_latest,
            "capex": capex_latest,
            "total_debt": debt_latest,
            "cash": cash_latest,
            "net_debt": net_debt_latest,
            "equity": equity_latest,
            "assets": assets_latest,
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "ebit_margin": ebit_margin,
            "net_margin": net_margin,
            "fcf_margin": fcf_margin,
            "fcf_yield": fcf_yield,
            "roic_proxy": roic,
            "dupont_roe_proxy": roe_dupont,
        },
        "revenue_cagr_3y": rev_cagr_3y,
        "annual_series": {
            "revenue": rev_map,
            "gross_profit": gp_map,
            "operating_income": operating_income_map,
            "ebit": ebit_map,
            "net_income": ni_map,
            "operating_cashflow": cfo_map,
            "free_cashflow": fcf_map,
            "capex": capex_map,
            "total_debt": debt_map,
            "cash": cash_map,
            "equity": equity_map,
            "assets": assets_map,
        },
        "quarterly_revenue": qrev_map,
        "data_quality_flags": quality_flags,
    }


def sec_snapshot(ticker: str):
    headers = {
        "User-Agent": "InvestmentResearchBot/1.0 (contact: research@example.com)",
        "Accept-Encoding": "gzip, deflate",
    }
    tickers = requests.get(
        "https://www.sec.gov/files/company_tickers.json", headers=headers, timeout=30
    ).json()

    row = None
    for _, v in tickers.items():
        if str(v.get("ticker", "")).upper() == ticker.upper():
            row = v
            break
    if not row:
        raise RuntimeError(f"Cannot find CIK for {ticker}")

    cik = str(row["cik_str"]).zfill(10)
    facts = requests.get(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
        headers=headers,
        timeout=30,
    ).json()

    def latest_fact(ns, key, unit):
        unit_map = facts["facts"][ns][key]["units"]
        arr = unit_map.get(unit) or unit_map[next(iter(unit_map.keys()))]
        arr = [x for x in arr if x.get("val") is not None and (x.get("end") or x.get("instant"))]
        arr.sort(key=lambda x: x.get("end") or x.get("instant") or "")
        return arr[-1] if arr else None

    def maybe(ns, key, unit):
        try:
            return latest_fact(ns, key, unit)
        except Exception:
            return None

    return {
        "source": "sec_companyfacts",
        "asof_local": ASOF,
        "ticker": ticker,
        "cik": cik,
        "company": row.get("title"),
        "revenue_latest": maybe("us-gaap", "Revenues", "USD"),
        "gross_profit_latest": maybe("us-gaap", "GrossProfit", "USD"),
        "operating_income_latest": maybe("us-gaap", "OperatingIncomeLoss", "USD"),
        "net_income_latest": maybe("us-gaap", "NetIncomeLoss", "USD"),
        "shares_outstanding_latest": maybe(
            "dei", "EntityCommonStockSharesOutstanding", "shares"
        ),
    }


def sec_segment_revenue_uber():
    # Parse XBRL-rendered table from 10-K filing package.
    base = "https://www.sec.gov/Archives/edgar/data/1543151/000154315126000015/"
    url = base + "R44.htm"
    r = requests.get(
        url,
        headers={"User-Agent": "InvestmentResearchBot/1.0 (contact: research@example.com)"},
        timeout=30,
    )
    r.raise_for_status()
    tables = pd.read_html(StringIO(r.text))

    out = {}
    for t in tables:
        if t.shape[0] < 4 or t.shape[1] < 23:
            continue
        row1 = " ".join([str(x) for x in t.iloc[1].tolist() if str(x) != "nan"])
        if "Year Ended December 31" not in row1:
            continue
        # detect year
        year = None
        for y in ["2025", "2024", "2023"]:
            if y in row1:
                year = y
                break
        if year is None:
            continue
        # Revenue row with fixed column blocks in SEC-rendered table.
        r3 = t.iloc[3].tolist()
        label = str(r3[0]).strip().lower()
        if "revenue" not in label:
            continue

        def to_num(v):
            try:
                s = str(v).replace(",", "").replace("$", "").strip()
                if s == "" or s.lower() == "nan":
                    return None
                return float(s)
            except Exception:
                return None

        mobility = to_num(r3[4])
        delivery = to_num(r3[10])
        freight = to_num(r3[16])
        total = to_num(r3[22])
        out[year] = {
            "mobility_revenue_musd": mobility,
            "delivery_revenue_musd": delivery,
            "freight_revenue_musd": freight,
            "total_revenue_musd": total,
        }
    return out


def stooq_quote(ticker: str):
    url = f"https://stooq.com/q/l/?s={ticker.lower()}.us&i=d"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    text = r.text.strip()
    # CSV: SYMBOL,DATE,TIME,OPEN,HIGH,LOW,CLOSE,VOLUME
    parts = text.split(",")
    if len(parts) < 8:
        raise RuntimeError(f"Unexpected stooq response for {ticker}: {text[:120]}")
    return {
        "source": "stooq",
        "ticker": ticker,
        "date": parts[1],
        "open": fnum(parts[3]),
        "high": fnum(parts[4]),
        "low": fnum(parts[5]),
        "close": fnum(parts[6]),
        "volume_k": fnum(parts[7]),
    }


def pct_diff(a, b):
    if a is None or b is None or b == 0:
        return None
    return (a - b) / b


def fred_series_latest(series_id: str):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    lines = [x.strip() for x in r.text.splitlines() if x.strip()]
    # header + values
    vals = []
    for line in lines[1:]:
        try:
            dt, raw = line.split(",")
        except ValueError:
            continue
        if raw == ".":
            continue
        try:
            vals.append((dt, float(raw)))
        except Exception:
            continue
    if not vals:
        return None
    return {"date": vals[-1][0], "value": vals[-1][1]}


def macro_snapshot():
    unrate = fred_series_latest("UNRATE")
    fedfunds = fred_series_latest("FEDFUNDS")
    dgs10 = fred_series_latest("DGS10")
    cpi = None
    cpi_yoy = None
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL"
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        lines = [x.strip() for x in r.text.splitlines() if x.strip()][1:]
        vals = []
        for line in lines:
            dt, raw = line.split(",")
            if (raw == ".") or (raw == ""):
                continue
            vals.append((dt, float(raw)))
        if vals:
            cpi = {"date": vals[-1][0], "value": vals[-1][1]}
        if len(vals) >= 13:
            curr = vals[-1][1]
            prev = vals[-13][1]
            cpi_yoy = {"date": vals[-1][0], "value": (curr / prev - 1) if prev else None}
    except Exception:
        pass

    return {
        "source": "fred",
        "unrate": unrate,
        "fedfunds": fedfunds,
        "dgs10": dgs10,
        "cpi_aucsl": cpi,
        "cpi_yoy": cpi_yoy,
    }


def build_cross_validation(yf_uber, sec_uber, stooq_uber):
    y = yf_uber["latest_annual"]
    sec_rev = fnum((sec_uber.get("revenue_latest") or {}).get("val"))
    sec_op = fnum((sec_uber.get("operating_income_latest") or {}).get("val"))
    sec_ni = fnum((sec_uber.get("net_income_latest") or {}).get("val"))
    sec_shares = fnum((sec_uber.get("shares_outstanding_latest") or {}).get("val"))

    return {
        "revenue_yfinance_vs_sec": {
            "yfinance": y.get("revenue"),
            "sec": sec_rev,
            "pct_diff": pct_diff(y.get("revenue"), sec_rev),
        },
        "operating_income_yfinance_vs_sec": {
            "yfinance": y.get("operating_income"),
            "sec": sec_op,
            "pct_diff": pct_diff(y.get("operating_income"), sec_op),
        },
        "net_income_yfinance_vs_sec": {
            "yfinance": y.get("net_income"),
            "sec": sec_ni,
            "pct_diff": pct_diff(y.get("net_income"), sec_ni),
        },
        "shares_yfinance_vs_sec": {
            "yfinance": yf_uber.get("shares_outstanding"),
            "sec": sec_shares,
            "pct_diff": pct_diff(yf_uber.get("shares_outstanding"), sec_shares),
        },
        "price_yfinance_vs_stooq": {
            "yfinance": yf_uber.get("price"),
            "stooq_close": stooq_uber.get("close"),
            "stooq_date": stooq_uber.get("date"),
            "pct_diff": pct_diff(yf_uber.get("price"), stooq_uber.get("close")),
        },
    }


def main():
    ensure_ca_bundle_ascii_path()

    tickers = [UBER] + COMPS
    yfs = {}
    stooq = {}
    errors = {}

    for t in tickers:
        try:
            yfs[t] = yfinance_snapshot(t)
        except Exception as e:
            errors[f"yfinance_{t}"] = repr(e)

        try:
            stooq[t] = stooq_quote(t)
        except Exception as e:
            errors[f"stooq_{t}"] = repr(e)

    try:
        sec = sec_snapshot(UBER)
    except Exception as e:
        sec = None
        errors["sec_UBER"] = repr(e)

    try:
        sec_segment = sec_segment_revenue_uber()
    except Exception as e:
        sec_segment = None
        errors["sec_segment_UBER"] = repr(e)

    cross_validation = None
    if UBER in yfs and sec and UBER in stooq:
        cross_validation = build_cross_validation(yfs[UBER], sec, stooq[UBER])

    try:
        macro = macro_snapshot()
    except Exception as e:
        macro = None
        errors["macro_fred"] = repr(e)

    payload = {
        "asof_local": ASOF,
        "ticker": UBER,
        "comps": COMPS,
        "yfinance": yfs,
        "sec": sec,
        "sec_segment_revenue_musd": sec_segment,
        "stooq": stooq,
        "cross_validation": cross_validation,
        "macro": macro,
        "errors": errors,
    }

    out_path = os.path.join(os.getcwd(), "tmp_uber_l4_snapshot.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Saved:", out_path)
    print("As of:", ASOF)
    if UBER in yfs:
        y = yfs[UBER]
        la = y["latest_annual"]
        print(
            "UBER price(yf):",
            y.get("price"),
            "| stooq:",
            stooq.get(UBER, {}).get("close"),
            "(",
            stooq.get(UBER, {}).get("date"),
            ")",
        )
        print(
            "Revenue FY",
            y.get("latest_annual_year"),
            ":",
            la.get("revenue"),
            "| FCF:",
            la.get("free_cashflow"),
            "| EBIT:",
            la.get("ebit"),
        )
        print(
            "Margins:",
            "Gross",
            la.get("gross_margin"),
            "EBIT",
            la.get("ebit_margin"),
            "Net",
            la.get("net_margin"),
            "FCF",
            la.get("fcf_margin"),
        )
    print("Errors:", errors)


if __name__ == "__main__":
    main()
