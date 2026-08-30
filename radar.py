import numpy as np
import pandas as pd

REQUIRED = ['date','code','name','open','high','low','close','volume','amount','turnover']


def _safe_div(a, b):
    return np.where(np.asarray(b) == 0, np.nan, np.asarray(a) / np.asarray(b))


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate V1.0 daily indicators for each stock."""
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f'Missing columns: {missing}')
    x = df.copy()
    x['date'] = pd.to_datetime(x['date'])
    x = x.sort_values(['code','date']).reset_index(drop=True)
    g = x.groupby('code', group_keys=False)

    x['ma5'] = g['close'].transform(lambda s: s.rolling(5).mean())
    x['ma10'] = g['close'].transform(lambda s: s.rolling(10).mean())
    x['ma20'] = g['close'].transform(lambda s: s.rolling(20).mean())
    x['ma60'] = g['close'].transform(lambda s: s.rolling(60).mean())
    x['high20'] = g['high'].transform(lambda s: s.shift(1).rolling(20).max())
    x['low20'] = g['low'].transform(lambda s: s.shift(1).rolling(20).min())
    x['vol_ma5'] = g['volume'].transform(lambda s: s.rolling(5).mean())
    x['amount_ma5'] = g['amount'].transform(lambda s: s.rolling(5).mean())
    x['ret5'] = g['close'].transform(lambda s: s.pct_change(5))
    x['ret20'] = g['close'].transform(lambda s: s.pct_change(20))
    x['ret60'] = g['close'].transform(lambda s: s.pct_change(60))
    x['vol_ratio'] = _safe_div(x['volume'], x['vol_ma5'])
    x['amount_ratio'] = _safe_div(x['amount'], x['amount_ma5'])
    x['range_pct'] = _safe_div(x['high'] - x['low'], x['close'].shift(1))
    x['close_pos'] = _safe_div(x['close'] - x['low'], x['high'] - x['low'])
    x['turnover_ma5'] = g['turnover'].transform(lambda s: s.rolling(5).mean())
    return x


def score_row(r):
    """0-100 score. Higher means stronger setup, not guaranteed return."""
    trend = 0
    trend += 5 if r.close > r.ma20 else 0
    trend += 5 if r.ma20 > r.ma60 else 0
    trend += 5 if r.ma5 > r.ma10 else 0
    trend += 5 if r.ret20 > 0.05 else 0

    breakout = 0
    breakout += 12 if pd.notna(r.high20) and r.close > r.high20 else 0
    breakout += 4 if pd.notna(r.ma20) and r.close > r.ma20 * 1.03 else 0
    breakout += 4 if pd.notna(r.low20) and (r.close / r.low20 - 1) > 0.10 else 0

    volume = 0
    volume += 8 if pd.notna(r.vol_ratio) and 1.3 <= r.vol_ratio <= 3.5 else 0
    volume += 6 if pd.notna(r.close_pos) and r.close_pos >= 0.70 else 0
    volume += 6 if pd.notna(r.amount_ratio) and r.amount_ratio >= 1.3 else 0

    capital = 0
    capital += 10 if pd.notna(r.turnover) and pd.notna(r.turnover_ma5) and r.turnover > r.turnover_ma5 else 0
    capital += 5 if pd.notna(r.amount_ratio) and r.amount_ratio > 1.5 else 0
    capital += 5 if pd.notna(r.ret5) and r.ret5 > 0 else 0

    risk = 20
    if pd.notna(r.range_pct) and r.range_pct > 0.12:
        risk -= 8
    if pd.notna(r.ret20) and r.ret20 > 0.30:
        risk -= 6
    if pd.notna(r.vol_ratio) and r.vol_ratio > 5:
        risk -= 6
    if pd.notna(r.close) and pd.notna(r.ma20) and r.close < r.ma20:
        risk -= 8
    risk = max(0, risk)
    return trend + breakout + volume + capital + risk


def scan(df: pd.DataFrame, min_score=70):
    x = add_indicators(df)
    x['score'] = x.apply(score_row, axis=1)
    latest = x.sort_values('date').groupby('code', as_index=False).tail(1)
    latest = latest[latest['score'] >= min_score].sort_values(['score','amount'], ascending=[False,False])
    cols = ['date','code','name','close','score','ret5','ret20','vol_ratio','amount_ratio','turnover']
    return latest[[c for c in cols if c in latest.columns]].reset_index(drop=True)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--min-score', type=int, default=70)
    args = p.parse_args()
    data = pd.read_csv(args.input)
    print(scan(data, args.min_score).to_string(index=False))
