import json
import math
import os
import shutil
import tempfile
from datetime import datetime, timezone

import certifi
import requests
import yfinance as yf

TICKER = "LLY"
ASOF = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _ensure_ca_bundle_path_safe_for_libcurl() -> str:
    """libcurl on Windows can fail when CAfile path contains non-ASCII characters.

    yfinance (via curl-cffi) ultimately relies on libcurl. If certifi.where() points
    to a path with Chinese characters / spaces, libcurl may throw curl(77).
    We copy the CA bundle to a pure-ASCII temp path and point env vars to it.
    """

    src = certifi.where()
    dst = os.path.join(tempfile.gettempdir(), "cacert.pem")

    try:
        if (not os.path.exists(dst)) or (os.path.getsize(dst) != os.path.getsize(src)):
            shutil.copyfile(src, dst)
    except Exception:
        # If copy fails for any reason, fall back to original path.
        dst = src

    os.environ.setdefault("SSL_CERT_FILE", dst)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", dst)
    os.environ.setdefault("CURL_CA_BUNDLE", dst)
    return dst


def _safe_float(x):
    try:
        if x is None:
            return None
        if isinstance(x, float) and math.isnan(x):
            return None
        return float(x)
    except Exception:
        return None


def yfinance_snapshot(ticker: str) -> dict:
    t = yf.Ticker(ticker)

    try:
        info = t.get_info()
    except Exception:
        info = getattr(t, "info", {}) or {}

    try:
        fast = dict(getattr(t, "fast_info", {}) or {})
    except Exception:
        fast = {}

    price = fast.get("last_price") or info.get("currentPrice") or info.get("regularMarketPrice")

    snap = {
        "source": "yfinance",
        "asof_local": ASOF,
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName"),
        "currency": info.get("currency"),
        "exchange": info.get("exchange") or info.get("fullExchangeName"),
        "price": _safe_float(price),
        "52w_low": _safe_float(fast.get("year_low")) or _safe_float(info.get("fiftyTwoWeekLow")),
        "52w_high": _safe_float(fast.get("year_high")) or _safe_float(info.get("fiftyTwoWeekHigh")),
        "market_cap": _safe_float(info.get("marketCap")),
        "enterprise_value": _safe_float(info.get("enterpriseValue")),
        "beta": _safe_float(info.get("beta")),
        "trailing_pe": _safe_float(info.get("trailingPE")),
        "forward_pe": _safe_float(info.get("forwardPE")),
        "peg": _safe_float(info.get("pegRatio")),
        "price_to_book": _safe_float(info.get("priceToBook")),
        "ev_to_ebitda": _safe_float(info.get("enterpriseToEbitda")),
        "profit_margin": _safe_float(info.get("profitMargins")),
        "operating_margin": _safe_float(info.get("operatingMargins")),
        "gross_margin": _safe_float(info.get("grossMargins")),
        "roe": _safe_float(info.get("returnOnEquity")),
        "roa": _safe_float(info.get("returnOnAssets")),
        "debt_to_equity": _safe_float(info.get("debtToEquity")),
        "total_cash": _safe_float(info.get("totalCash")),
        "total_debt": _safe_float(info.get("totalDebt")),
        "operating_cashflow": _safe_float(info.get("operatingCashflow")),
        "free_cashflow": _safe_float(info.get("freeCashflow")),
        "dividend_rate": _safe_float(info.get("dividendRate")),
        "dividend_yield": _safe_float(info.get("dividendYield")),
        "trailing_annual_dividend_rate": _safe_float(info.get("trailingAnnualDividendRate")),
        "trailing_annual_dividend_yield": _safe_float(info.get("trailingAnnualDividendYield")),
        "five_year_avg_dividend_yield": _safe_float(info.get("fiveYearAvgDividendYield")),
        "payout_ratio": _safe_float(info.get("payoutRatio")),
        "shares_outstanding": _safe_float(info.get("sharesOutstanding")),
    }
    if snap["total_debt"] is not None and snap["total_cash"] is not None:
        snap["net_debt"] = snap["total_debt"] - snap["total_cash"]
    else:
        snap["net_debt"] = None

    return snap


def _sec_get_json(url: str, headers: dict, timeout: int = 20):
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()


def sec_snapshot(ticker: str) -> dict:
    headers = {
        "User-Agent": "InvestmentResearchBot/1.0 (contact: research@example.com)",
        "Accept-Encoding": "gzip, deflate",
    }

    tickers_url = "https://www.sec.gov/files/company_tickers.json"
    tickers = _sec_get_json(tickers_url, headers=headers, timeout=30)

    row = None
    for _, v in tickers.items():
        if str(v.get("ticker", "")).upper() == ticker.upper():
            row = v
            break
    if not row:
        raise RuntimeError(f"Cannot find CIK for {ticker}")

    cik = str(row["cik_str"]).zfill(10)
    title = row.get("title")

    facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    facts = _sec_get_json(facts_url, headers=headers, timeout=30)

    def latest_fact_us_gaap(us_gaap_key: str, preferred_units: str):
        try:
            unit_map = facts["facts"]["us-gaap"][us_gaap_key]["units"]
            arr = None
            if preferred_units in unit_map:
                arr = unit_map[preferred_units]
            else:
                # pick first unit key
                arr = unit_map[next(iter(unit_map.keys()))]
            arr2 = [x for x in arr if x.get("val") is not None and x.get("end")]
            arr2.sort(key=lambda x: x.get("end", ""))
            return arr2[-1] if arr2 else None
        except Exception:
            return None

    def latest_fact_dei(dei_key: str, preferred_units: str):
        try:
            unit_map = facts["facts"]["dei"][dei_key]["units"]
            arr = None
            if preferred_units in unit_map:
                arr = unit_map[preferred_units]
            else:
                arr = unit_map[next(iter(unit_map.keys()))]
            arr2 = [x for x in arr if x.get("val") is not None and (x.get("end") or x.get("instant"))]
            # dei entries often use 'instant'
            def _date(x):
                return x.get("end") or x.get("instant") or ""

            arr2.sort(key=_date)
            return arr2[-1] if arr2 else None
        except Exception:
            return None

    def latest_shares():
        # Prefer DEI if present; fall back to us-gaap.
        fact = latest_fact_dei("EntityCommonStockSharesOutstanding", preferred_units="shares")
        if fact:
            return fact
        for k in ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"]:
            fact2 = latest_fact_us_gaap(k, preferred_units="shares")
            if fact2:
                return fact2
        return None

    return {
        "source": "sec_companyfacts",
        "asof_local": ASOF,
        "ticker": ticker,
        "cik": cik,
        "company": title,
        "revenue_latest": latest_fact_us_gaap("Revenues", preferred_units="USD"),
        "net_income_latest": latest_fact_us_gaap("NetIncomeLoss", preferred_units="USD"),
        "operating_income_latest": latest_fact_us_gaap("OperatingIncomeLoss", preferred_units="USD"),
        "shares_outstanding_latest": latest_shares(),
    }


def main():
    _ensure_ca_bundle_path_safe_for_libcurl()
    yf_snap = yfinance_snapshot(TICKER)

    try:
        sec_snap = sec_snapshot(TICKER)
        sec_error = None
    except Exception as e:
        sec_snap = None
        sec_error = repr(e)

    snapshot = {
        "asof_local": ASOF,
        "ticker": TICKER,
        "yfinance": yf_snap,
        "sec": sec_snap,
        "sec_error": sec_error,
    }

    out_path = os.path.join(os.getcwd(), "tmp_lly_snapshot.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    print("=== LLY Snapshot ===")
    print("As of:", ASOF)
    print("Name:", yf_snap.get("name"))
    print("Price:", yf_snap.get("price"), yf_snap.get("currency"))
    print("MarketCap:", yf_snap.get("market_cap"))
    print("PE (ttm/fwd):", yf_snap.get("trailing_pe"), yf_snap.get("forward_pe"))
    print("EV/EBITDA:", yf_snap.get("ev_to_ebitda"))
    print("Margins (gross/op/profit):", yf_snap.get("gross_margin"), yf_snap.get("operating_margin"), yf_snap.get("profit_margin"))
    print("ROE:", yf_snap.get("roe"), "Debt/Equity:", yf_snap.get("debt_to_equity"))
    print("FCF:", yf_snap.get("free_cashflow"), "OCF:", yf_snap.get("operating_cashflow"))
    print("DivYield:", yf_snap.get("dividend_yield"), "Payout:", yf_snap.get("payout_ratio"))
    print("Shares (yfinance):", yf_snap.get("shares_outstanding"))

    if sec_error:
        print("--- SEC facts: FAILED ---")
        print(sec_error)
    else:
        rev = (sec_snap or {}).get("revenue_latest") or {}
        ni = (sec_snap or {}).get("net_income_latest") or {}
        sh = (sec_snap or {}).get("shares_outstanding_latest") or {}
        print("--- SEC latest facts ---")
        print("CIK:", (sec_snap or {}).get("cik"), "Company:", (sec_snap or {}).get("company"))
        print("Revenue:", rev.get("val"), rev.get("end"), rev.get("fy"), rev.get("fp"), rev.get("form"))
        print("NetIncome:", ni.get("val"), ni.get("end"), ni.get("fy"), ni.get("fp"), ni.get("form"))
        print("Shares:", sh.get("val"), sh.get("end"), sh.get("fy"), sh.get("fp"), sh.get("form"))

    print("Saved:", out_path)


if __name__ == "__main__":
    main()
