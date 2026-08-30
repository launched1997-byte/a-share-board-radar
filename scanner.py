from datetime import datetime
from data_provider import get_spot, get_limit_up_pool, get_yesterday_limit_up


def f(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def turnover_score(x):
    if 8 <= x <= 25: return 15
    if 5 <= x < 8: return 11
    if 25 < x <= 35: return 8
    if 35 < x <= 50: return 3
    return 0


def volume_score(x):
    if 1.2 <= x <= 2.5: return 15
    if 2.5 < x <= 3.5: return 10
    if 0.9 <= x < 1.2: return 7
    if 3.5 < x <= 5: return 4
    return 0


def amount_score(x):
    b = x / 100000000
    if b >= 3: return 10
    if b >= 2: return 7
    if b >= 1: return 5
    return 0


def score_stock(row):
    turnover = f(row.get('换手率'))
    volume_ratio = f(row.get('量比'))
    amount = f(row.get('成交额'))
    score = turnover_score(turnover) + volume_score(volume_ratio) + amount_score(amount)
    high, price = f(row.get('最高')), f(row.get('最新价'))
    if high > 0:
        r = price / high
        score += 15 if r >= .998 else 10 if r >= .99 else 5 if r >= .97 else 0
    if f(row.get('涨跌幅')) >= 9.5: score += 15
    if amount >= 300000000: score += 10
    elif amount >= 100000000: score += 5
    return min(score, 100)


def scan_market():
    spot = get_spot()
    limit_up = get_limit_up_pool()
    yesterday = get_yesterday_limit_up()
    if spot.empty:
        return {'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'candidates': [], 'error': '行情为空'}
    for df in (spot, limit_up, yesterday):
        if not df.empty and '代码' in df.columns:
            df['代码'] = df['代码'].astype(str).str.zfill(6)
    yesterday_codes = set(yesterday['代码']) if '代码' in yesterday.columns else set()
    candidates = []
    for _, lr in limit_up.iterrows():
        code = str(lr.get('代码', '')).zfill(6)
        rows = spot[spot['代码'] == code]
        if rows.empty: continue
        row = rows.iloc[0]
        board = 2 if code in yesterday_codes else 1
        score = score_stock(row)
        signal = '强接力' if score >= 85 else '重点观察' if score >= 80 else '等确认' if score >= 70 else '放弃'
        candidates.append({'code': code, 'name': row.get('名称', lr.get('名称', '')), 'board': board, 'score': score, 'turnover': f(row.get('换手率')), 'volume_ratio': f(row.get('量比')), 'amount': round(f(row.get('成交额'))/100000000, 2), 'pct': f(row.get('涨跌幅')), 'signal': signal})
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return {'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'limit_up': len(limit_up), 'yesterday_limit_up': len(yesterday), 'candidates': candidates[:10], 'note': 'V1.0为收盘规则评分，不代表实际盈利概率。'}
