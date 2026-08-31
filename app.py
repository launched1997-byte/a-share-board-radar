import os
from flask import Flask,jsonify,render_template
app=Flask(__name__)
@app.get('/')
def index(): return render_template('v6_index.html')
@app.get('/api/scan')
def api_scan():
    try:
        from v4_scanner import scan_market
        return jsonify(scan_market()),200
    except Exception as e:
        return jsonify({'ok':False,'version':'7.0','source':'服务器异常','stats':{},'sector_rank':[],'top10':[],'candidates':[],'error':f'{type(e).__name__}: {e}'}),200
@app.get('/api/status')
def api_status():
    try:
        from data_provider import provider_status
        return jsonify(provider_status()),200
    except Exception as e:return jsonify({'ok':False,'error':f'{type(e).__name__}: {e}'}),200
@app.get('/health')
def health():return jsonify({'status':'ok','service':'a-share-board-radar','version':'7.0'})
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','10000')))
