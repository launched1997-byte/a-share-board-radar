from data_catalog import THEMES

def score_stock(stock):
    return round(min(100, stock.get('trend', 0) * 0.35 + stock.get('strength', 0) * 0.35 + stock.get('catalyst', 0) * 0.30))

def build_panorama():
    themes = []
    candidates = []
    for raw in THEMES:
        theme = dict(raw)
        stocks = []
        for s in raw['stocks']:
            item = dict(s)
            item['score'] = score_stock(item)
            stocks.append(item)
            candidates.append({**item, 'theme': raw['name']})
        theme['stocks'] = sorted(stocks, key=lambda x: x['score'], reverse=True)
        theme['avg_score'] = round(sum(x['score'] for x in theme['stocks']) / max(1, len(theme['stocks'])))
        themes.append(theme)
    candidates.sort(key=lambda x: x['score'], reverse=True)
    sector_rank = sorted([{'name': x['name'], 'score': x['avg_score'], 'count': len(x['stocks'])} for x in themes], key=lambda x: x['score'], reverse=True)
    return {'ok': True, 'themes': themes, 'candidates': candidates[:20], 'sector_rank': sector_rank}
