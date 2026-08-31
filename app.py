import os
import traceback
from flask import Flask, jsonify, render_template

app = Flask(__name__)

@app.get('/')
def index():
    return render_template('index.html')

@app.get('/api/scan')
def api_scan():
    # API endpoint must always return JSON, even when every market provider fails.
    try:
        from scanner import scan_market
        result = scan_market()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'ok': False,
            'updated_at': '',
            'source': '服务器异常',
            'source_errors': [f'{type(e).__name__}: {e}'],
            'limit_up': 0,
            'yesterday_limit_up': 0,
            'candidates': [],
            'error': f'{type(e).__name__}: {e}',
            'note': '后端已捕获异常；没有使用模拟行情。'
        }), 200

@app.get('/api/status')
def api_status():
    try:
        from data_provider import provider_status
        return jsonify(provider_status()), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}'}), 200

@app.get('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'a-share-board-radar', 'version': '2.0'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '10000')))
