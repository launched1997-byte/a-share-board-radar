from datetime import datetime

from data_provider import get_spot_with_source, get_limit_up_pool, get_yesterday_limit_up


def f(v):
    try:
        if v is None or v == "":
            return 0.0
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


def normalize_columns(df):
    if df is None or df.empty:
        return df
    rename = {"涨幅": "涨跌幅", "成交额": "成交额", "换手": "换手率", "成交量": "成交量"}
    return df.rename(columns=rename)


def is_limit_up(row):
    # Practical proxy from price change; special boards are kept conservative in V1.1.
    pct = f(row.get("涨跌幅"))
    code = str(row.get("代码", "")).zfill(6)
    name = str(row.get("名称", ""))
    if "ST" in name.upper() or "*ST" in name.upper():
        return False
    if code.startswith(("300", "301", "688")):
        return pct >= 19.5
    if code.startswith(("8", "4")):
        return pct >= 29.0
    return pct >= 9.5


def score_stock(row):
    turnover = f(row.get("换手率"))
    volume_ratio = f(row.get("量比"))
    amount = f(row.get("成交额"))
    high = f(row.get("最高"))
    price = f(row.get("最新价"))
    pct = f(row.get("涨跌幅"))

    score = turnover_score(turnover)
    score += volume_score(volume_ratio)
    score += amount_score(amount)

    if high > 0:
        close_strength = price / high
        score += 15 if close_strength >= .998 else 10 if close_strength >= .99 else 5 if close_strength >= .97 else 0

    if is_limit_up(row):
        score += 15

    if amount >= 300000000:
        score += 10
    elif amount >= 100000000:
        score += 5

    return min(score, 100)


def scan_market():
    spot, source, source_errors = get_spot_with_source()
    limit_up = get_limit_up_pool()
    yesterday = get_yesterday_limit_up()

    if spot is None or spot.empty:
        return {
            "ok": False,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "source_errors": source_errors,
            "candidates": [],
            "error": "全市场行情为空；" + "；".join(source_errors),
        }

    spot = normalize_columns(spot.copy())
    for df in (spot, limit_up, yesterday):
        if not df.empty and "代码" in df.columns:
            df["代码"] = df["代码"].astype(str).str.extract(r"(\d{6})")[0].fillna("")

    # If the Eastmoney limit-up pool is unavailable, derive a daily limit-up candidate pool from the full spot feed.
    if limit_up is None or limit_up.empty:
        limit_up = spot[spot.apply(is_limit_up, axis=1)].copy()

    yesterday_codes = set(yesterday["代码"]) if not yesterday.empty and "代码" in yesterday.columns else set()
    candidates = []

    for _, lr in limit_up.iterrows():
        code = str(lr.get("代码", "")).zfill(6)
        rows = spot[spot["代码"] == code]
        if rows.empty:
            row = lr
        else:
            row = rows.iloc[0]

        if not is_limit_up(row):
            continue

        board = 2 if code in yesterday_codes else 1
        score = score_stock(row)
        risk = 0
        turnover = f(row.get("换手率"))
        volume_ratio = f(row.get("量比"))
        amount = f(row.get("成交额"))
        if turnover > 35: risk += 25
        if volume_ratio > 4: risk += 25
        if amount < 100000000: risk += 20
        if board >= 4: risk += 15
        risk = min(risk, 100)
        signal = "强接力" if score >= 85 and risk < 50 else "重点观察" if score >= 80 and risk < 65 else "等确认" if score >= 70 else "放弃"
        candidates.append({
            "code": code,
            "name": row.get("名称", lr.get("名称", "")),
            "board": board,
            "score": score,
            "risk": risk,
            "turnover": turnover,
            "volume_ratio": volume_ratio,
            "amount": round(amount / 100000000, 2),
            "pct": f(row.get("涨跌幅")),
            "signal": signal,
        })

    candidates.sort(key=lambda x: (x["score"], -x["risk"]), reverse=True)
    return {
        "ok": True,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "source_errors": source_errors,
        "limit_up": len(limit_up),
        "yesterday_limit_up": len(yesterday),
        "candidates": candidates[:10],
        "note": "V1.1：多行情源 + 涨停池故障降级 + 风险评分。N板精确历史识别、竞价和盘中逐笔/回封仍需后续实时数据源。",
    }
