from flask import Flask, jsonify, render_template
from scanner import scan_market

app = Flask(__name__)

@app.get('/')
def index():
    return render_template('index.html')

@app.get('/api/scan')
def api_scan():
    try:
        return jsonify(scan_market())
    except Exception as e:
        return jsonify({'error': str(e), 'candidates': []}), 500

@app.get('/health')
def health():
    return {'status': 'ok'}

if __name__ == '__main__':
    import os
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '10000')))
