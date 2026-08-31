from datetime import datetime
from data_provider import get_spot_with_source


def f(v):
    try:
        return float(str(v).replace(',', '').strip()) if v not in (None, '') else 0.0
    except Exception:
        return 0.0


def norm(df):
    if df is None or df.empty:
        return None
    df = df.copy()
    aliases = {
        '代码': ['代码', 'code', 'symbol'], '名称': ['名称', 'name'],
        '最新价': ['最新价', 'trade', 'price', 'last'], '涨跌幅': ['涨跌幅', 'pct_chg', 'change_percent'],
        '最高': ['最高', 'high'], '最低': ['最低', 'low'], '成交额': ['成交额', 'amount'],
        '换手率': ['换手率', 'turnover'], '量比': ['量比', 'ratio'], '成交量': ['成交量', 'volume']
    }
    for target, names in aliases.items():
        if target not in df.columns:
            for name in names:
                if name in df.columns:
                    df[target] = df[name]
                    break
        if target not in df.columns:
            df[target] = '' if target in ('代码', '名称') else 0
    df['代码'] = df['代码'].astype(str).str.extract(r'(\d{6})')[0].fillna('')
    return df[df['代码'] != ''].copy()


def is_st(name):
    return 'ST' in str(name).upper() or '退' in str(name)


def limit_threshold(code):
    code = str(code).zfill(6)
    if code.startswith(('300', '301', '688', '689')):
        return 19.0
    if code.startswith(('8', '4')):
        return 28.0
    return 9.4


def limit_up(r):
    if is_st(r.get('名称', '')):
        return False
    return f(r.get('涨跌幅')) >= limit_threshold(r.get('代码', ''))


def turnover_score(t):
    if 8 <= t <= 25: return 15
    if 5 <= t < 8 or 25 < t <= 35: return 10
    if 3 <= t < 5: return 6
    if 35 < t <= 45: return 3
    return 0


def volume_score(v):
    if 1.2 <= v <= 2.5: return 15
    if 2.5 < v <= 3.5: return 10
    if 0.9 <= v < 1.2: return 7
    if 3.5 < v <= 5: return 4
    return 0


def amount_score(a):
    if a >= 3e8: return 10
    if a >= 2e8: return 7
    if a >= 1e8: return 5
    return 0


def close_score(price, high):
    if high <= 0: return 0
    ratio = price / high
    if ratio >= .998: return 15
    if ratio >= .99: return 10
    if ratio >= .97: return 5
    return 0


def score(r):
    t, v, a = f(r.get('换手率')), f(r.get('量比')), f(r.get('成交额'))
    s = turnover_score(t) + volume_score(v) + amount_score(a)
    s += close_score(f(r.get('最新价')), f(r.get('最高')))
    s += 15 if limit_up(r) else 0
    s += 10 if a >= 3e8 else 5 if a >= 1e8 else 0
    return min(100, int(s))


def risk(r):
    t, v, a = f(r.get('换手率')), f(r.get('量比')), f(r.get('成交额'))
    x = 25 if t > 35 else 10 if t > 30 else 0
    x += 25 if v > 4 else 10 if v > 3.5 else 0
    x += 20 if a < 1e8 else 0
    return min(100, x)


def signal(s, rr):
    if s >= 85 and rr < 50: return '强接力'
    if s >= 80 and rr < 65: return '重点观察'
    if s >= 70: return '等确认'
    return '放弃'


def scan_market():
    spot, source, errors = get_spot_with_source()
    spot = norm(spot)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if spot is None:
        return {'ok': False, 'version': '2.1', 'updated_at': now, 'source': source,
                'source_errors': errors, 'limit_up': 0, 'yesterday_limit_up': None,
                'candidates': [], 'error': '所有行情源均不可用：' + '；'.join(errors)}

    pool = spot[spot.apply(limit_up, axis=1)].copy()
    out = []
    for _, r in pool.iterrows():
        s = score(r); rr = risk(r)
        t, v, a = f(r.get('换手率')), f(r.get('量比')), f(r.get('成交额'))
        out.append({
            'code': str(r.get('代码', '')).zfill(6), 'name': r.get('名称', ''),
            'board': None, 'board_text': '今日涨停', 'score': s, 'risk': rr,
            'turnover': t, 'volume_ratio': v, 'amount': round(a / 1e8, 2),
            'pct': f(r.get('涨跌幅')), 'signal': signal(s, rr),
            'data_quality': '换手/量比有效' if (t > 0 or v > 0) else '仅快照字段'
        })
    out.sort(key=lambda x: (x['score'], -x['risk'], x['amount']), reverse=True)
    return {'ok': True, 'version': '2.1', 'updated_at': now, 'source': source,
            'source_errors': errors, 'limit_up': len(pool), 'yesterday_limit_up': None,
            'candidates': out[:30],
            'note': 'V2.1：今日涨停 + 换手 + 量比 + 成交额 + 收盘强度 + 风险评分。当前数据源缺少可靠历史连续板字段，因此不伪造N板；后续接入历史/实时Tick后启用精确连板、竞价、炸板与回封。'}
