import os
from flask import Flask, jsonify, render_template

app = Flask(__name__)

@app.get('/')
def index():
    return render_template('index.html')

@app.get('/api/scan')
def api_scan():
    try:
        from scanner import scan_market
        return jsonify(scan_market())
    except Exception as e:
        return jsonify({
            'ok': False,
            'updated_at': '',
            'candidates': [],
            'error': f'{type(e).__name__}: {e}'
        }), 200

@app.get('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'a-share-board-radar'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '10000')))
