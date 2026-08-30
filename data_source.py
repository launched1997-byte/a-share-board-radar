"""A-share market data adapter.

Default source: AKShare's Eastmoney spot/daily interfaces. The adapter is kept
separate from the scoring engine so the data vendor can be replaced later.
"""
import pandas as pd


def fetch_spot():
    import akshare as ak
    df = ak.stock_zh_a_spot_em()
    rename = {
        '代码': 'code', '名称': 'name', '最新价': 'close',
        '最高': 'high', '最低': 'low', '今开': 'open',
        '成交量': 'volume', '成交额': 'amount', '换手率': 'turnover',
    }
    df = df.rename(columns=rename)
    keep = list(rename.values())
    for c in keep:
        if c not in df.columns:
            df[c] = 0
    return df[keep]


def fetch_daily(code, start='20240101', end=None, adjust='qfq'):
    import akshare as ak
    end = end or pd.Timestamp.today().strftime('%Y%m%d')
    df = ak.stock_zh_a_hist(symbol=str(code), period='daily',
                            start_date=start, end_date=end, adjust=adjust)
    rename = {
        '日期':'date','股票代码':'code','股票名称':'name','开盘':'open',
        '收盘':'close','最高':'high','最低':'low','成交量':'volume',
        '成交额':'amount','换手率':'turnover'
    }
    df = df.rename(columns=rename)
    if 'code' not in df.columns:
        df['code'] = str(code)
    return df[[c for c in ['date','code','name','open','high','low','close','volume','amount','turnover'] if c in df.columns]]


def fetch_universe(start='20240101', end=None, limit=None):
    """Download daily history for the current A-share universe.

    limit is useful for testing. Set None for the full universe.
    """
    spot = fetch_spot()
    codes = spot['code'].astype(str).tolist()
    if limit:
        codes = codes[:limit]
    frames = []
    for i, code in enumerate(codes, 1):
        try:
            frames.append(fetch_daily(code, start=start, end=end))
            if i % 50 == 0:
                print(f'downloaded {i}/{len(codes)}')
        except Exception as e:
            print(f'skip {code}: {e}')
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
