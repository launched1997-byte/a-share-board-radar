import os
import time

import requests
import pandas as pd


HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json,text/plain,*/*",
}


def _try(fn, label, errors):
    try:
        df = fn()
        if df is not None and not df.empty:
            return df, label
        errors.append(f"{label}: 返回为空")
    except Exception as exc:
        errors.append(f"{label}: {type(exc).__name__}: {exc}")
    return None, None


def get_spot_with_source():
    errors = []

    # 1) Sina: full A-share spot list through AKShare, used as the main alternate source.
    import akshare as ak
    df, label = _try(ak.stock_zh_a_spot, "新浪财经（AKShare）", errors)
    if df is not None:
        return df, label, errors

    # 2) Eastmoney: fallback only.
    df, label = _try(ak.stock_zh_a_spot_em, "东方财富（AKShare）", errors)
    if df is not None:
        return df, label, errors

    return pd.DataFrame(), "无可用行情源", errors


def get_spot():
    df, _, errors = get_spot_with_source()
    if df.empty:
        raise ConnectionError("；".join(errors) or "没有可用的A股行情源")
    return df


def get_limit_up_pool():
    # Supplementary source. If unavailable, scanner will derive a limit-up proxy from spot prices.
    import akshare as ak
    try:
        df = ak.stock_zt_pool_em()
        if df is not None:
            return df
    except Exception:
        pass
    return pd.DataFrame()


def get_yesterday_limit_up():
    import akshare as ak
    try:
        df = ak.stock_zt_pool_previous_em()
        if df is not None:
            return df
    except Exception:
        pass
    return pd.DataFrame()


def itick_quote(region: str, code: str):
    token = os.getenv("ITICK_TOKEN", "").strip()
    if not token:
        return None, "ITICK_TOKEN 未配置"
    try:
        r = requests.get(
            "https://api.itick.io/stock/quote",
            params={"region": region, "code": code},
            headers={"accept": "application/json", "token": token},
            timeout=8,
        )
        r.raise_for_status()
        payload = r.json()
        return payload.get("data"), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def source_capabilities():
    return {
        "sina": "full A-share spot list via AKShare",
        "eastmoney": "full A-share spot/list and limit-up pools via AKShare fallback",
        "itick": "optional real-time quote/depth/tick via API token",
        "tushare": "optional historical/daily-basic data adapter to add later",
        "ifind": "professional paid API; credentials required and not enabled by default",
        "tencent": "historical/tick data available via AKShare adapters; not the primary live full-market source here",
    }
