import time
from functools import lru_cache

import requests


HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://quote.eastmoney.com/",
}


def _request(url, params=None, timeout=12):
    last_error = None
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise ConnectionError(f"行情源连续3次请求失败: {last_error}")


def get_spot():
    import akshare as ak
    last_error = None
    for _ in range(2):
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                return df
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    raise ConnectionError(f"东方财富全市场行情不可用: {last_error}")


def get_limit_up_pool():
    import akshare as ak
    last_error = None
    for _ in range(2):
        try:
            df = ak.stock_zt_pool_em()
            if df is not None:
                return df
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    raise ConnectionError(f"涨停池不可用: {last_error}")


def get_yesterday_limit_up():
    import akshare as ak
    last_error = None
    for _ in range(2):
        try:
            df = ak.stock_zt_pool_previous_em()
            if df is not None:
                return df
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    raise ConnectionError(f"昨日涨停池不可用: {last_error}")
