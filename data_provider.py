import os
import re
import time
import requests
import pandas as pd

TIMEOUT = 8
UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1'


def _session():
    s = requests.Session()
    s.headers.update({'User-Agent': UA, 'Accept': '*/*', 'Connection': 'close'})
    return s


def _num(v):
    try:
        return float(str(v).replace(',', '').strip())
    except Exception:
        return 0.0


def _sina_snapshot():
    # Sina's quote endpoint needs a symbol list. We first obtain the public A-share list
    # from Sina's stock list endpoint, then batch quote requests.
    s = _session()
    errors = []
    symbols = []
    for market in ('sh', 'sz', 'bj'):
        try:
            url = f'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=5000&sort=code&asc=1&node={market}_a'
            r = s.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            arr = r.json()
            if isinstance(arr, list):
                for x in arr:
                    code = str(x.get('code', '')).zfill(6)
                    if code:
                        symbols.append((market, code, x))
        except Exception as e:
            errors.append(f'新浪股票列表-{market}: {type(e).__name__}: {e}')
    if not symbols:
        raise ConnectionError('；'.join(errors) or '新浪股票列表为空')

    rows = []
    # The list endpoint already contains quote fields on many deployments; use it first.
    for market, code, x in symbols:
        name = x.get('name') or x.get('symbol') or ''
        price = _num(x.get('trade') or x.get('price'))
        prev = _num(x.get('settlement') or x.get('pre_close'))
        high = _num(x.get('high'))
        low = _num(x.get('low'))
        volume = _num(x.get('volume'))
        amount = _num(x.get('amount'))
        if price <= 0:
            continue
        pct = (price / prev - 1) * 100 if prev > 0 else 0
        rows.append({'代码': code, '名称': name, '最新价': price, '涨跌幅': pct,
                     '最高': high, '最低': low, '成交量': volume, '成交额': amount,
                     '换手率': _num(x.get('turnover')), '量比': _num(x.get('ratio'))})
    if not rows:
        raise ConnectionError('新浪返回了股票列表，但没有有效报价')
    return pd.DataFrame(rows), '新浪财经（直接接口）'


def _eastmoney_snapshot():
    # Direct Eastmoney push2 endpoint; no AKShare dependency on the request path.
    s = _session()
    url = 'https://push2.eastmoney.com/api/qt/clist/get'
    params = {
        'pn': 1, 'pz': 6000, 'po': 1, 'np': 1, 'fltt': 2,
        'invt': 2, 'fid': 'f3', 'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
        'fields': 'f12,f14,f2,f3,f4,f5,f6,f8,f10,f15,f16,f17,f18'
    }
    r = s.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json().get('data') or {}
    diff = data.get('diff') or []
    if not diff:
        raise ConnectionError('东方财富返回空行情')
    rows = []
    for x in diff:
        rows.append({'代码': str(x.get('f12','')).zfill(6), '名称': x.get('f14',''),
                     '最新价': _num(x.get('f2')), '涨跌幅': _num(x.get('f3')),
                     '成交量': _num(x.get('f5')), '成交额': _num(x.get('f6')),
                     '换手率': _num(x.get('f8')), '量比': _num(x.get('f10')),
                     '最高': _num(x.get('f15')), '最低': _num(x.get('f16')),
                     '今开': _num(x.get('f17')), '昨收': _num(x.get('f18'))})
    return pd.DataFrame(rows), '东方财富（直接接口）'


def _itick_snapshot():
    token = os.getenv('ITICK_TOKEN', '').strip()
    if not token:
        raise ConnectionError('未配置 ITICK_TOKEN')
    # iTick full-market endpoints vary by plan. Keep this adapter isolated so a valid token
    # can be enabled without changing the scanner.
    url = os.getenv('ITICK_A_SHARE_SNAPSHOT_URL', '').strip()
    if not url:
        raise ConnectionError('已配置 ITICK_TOKEN，但未配置 ITICK_A_SHARE_SNAPSHOT_URL')
    s = _session()
    r = s.get(url, headers={'token': token, 'accept': 'application/json'}, timeout=TIMEOUT)
    r.raise_for_status()
    payload = r.json()
    data = payload.get('data', payload)
    if isinstance(data, dict):
        data = data.get('list', data.get('items', []))
    if not isinstance(data, list) or not data:
        raise ConnectionError('iTick 返回空行情')
    return pd.DataFrame(data), 'iTick'


def get_spot_with_source():
    errors = []
    providers = [
        ('iTick', _itick_snapshot),
        ('新浪', _sina_snapshot),
        ('东方财富', _eastmoney_snapshot),
    ]
    for _, fn in providers:
        try:
            df, label = fn()
            if df is not None and not df.empty:
                return df, label, errors
            errors.append(f'{_}: 返回为空')
        except Exception as e:
            errors.append(f'{_}: {type(e).__name__}: {e}')
    return pd.DataFrame(), '无可用行情源', errors


def get_spot():
    df, source, errors = get_spot_with_source()
    if df.empty:
        raise ConnectionError('；'.join(errors) or '没有可用行情源')
    return df


def provider_status():
    result = {'ok': False, 'providers': []}
    for name, fn in [('iTick', _itick_snapshot), ('新浪', _sina_snapshot), ('东方财富', _eastmoney_snapshot)]:
        try:
            df, label = fn()
            result['providers'].append({'name': label, 'ok': bool(df is not None and not df.empty), 'rows': int(len(df)) if df is not None else 0})
            if df is not None and not df.empty:
                result['ok'] = True
        except Exception as e:
            result['providers'].append({'name': name, 'ok': False, 'error': f'{type(e).__name__}: {e}'})
    return result


def get_limit_up_pool():
    # Derived in scanner from the full snapshot. This avoids a second fragile endpoint.
    return pd.DataFrame()


def get_yesterday_limit_up():
    return pd.DataFrame()


def itick_quote(region: str, code: str):
    token = os.getenv('ITICK_TOKEN', '').strip()
    if not token:
        return None, 'ITICK_TOKEN 未配置'
    try:
        r = requests.get('https://api.itick.io/stock/quote', params={'region': region, 'code': code},
                         headers={'accept': 'application/json', 'token': token}, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json().get('data'), None
    except Exception as exc:
        return None, f'{type(exc).__name__}: {exc}'
