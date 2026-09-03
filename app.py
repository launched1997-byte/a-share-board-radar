import os
from flask import Flask, jsonify, render_template, request
from v4_scanner import scan_market
from scanner_v2 import build_panorama

app = Flask(__name__)

@app.get('/')
def index():
    return render_template('index.html')

@app.get('/api/scan')
def api_scan():
    try:
        return jsonify(scan_market()), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}', 'candidates': [], 'top10': [], 'sector_rank': []}), 200

@app.get('/api/panorama')
def panorama():
    try:
        return jsonify(build_panorama())
    except Exception as e:
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}', 'themes': []}), 200

@app.get('/api/search')
def search():
    q = request.args.get('q', '').strip().lower()
    data = build_panorama()
    if not q:
        return jsonify([])
    results = []
    for theme in data['themes']:
        for stock in theme['stocks']:
            hay = ' '.join([stock['code'], stock['name'], theme['name'], *stock['tags']]).lower()
            if q in hay:
                results.append({**stock, 'theme': theme['name']})
    return jsonify(results[:30])

@app.get('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'a-share-board-radar', 'version': '8.0'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '10000')))
