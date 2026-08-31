import os
import time
import requests
import pandas as pd

TIMEOUT = 8
UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1'

def _session():
    s = requests.Session(); s.headers.update({'User-Agent': UA, 'Accept': '*/*', 'Connection': 'close'}); return s

def _num(v):
    try: return float(str(v).replace(',', '').strip())
    except Exception: return 0.0

def _sina_snapshot():
    s=_session(); errors=[]; rows=[]
    for market in ('sh','sz','bj'):
        try:
            url=f'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=5000&sort=code&asc=1&node={market}_a'
            r=s.get(url,timeout=TIMEOUT); r.raise_for_status(); arr=r.json()
            if isinstance(arr,list):
                for x in arr:
                    code=str(x.get('code','')).zfill(6); price=_num(x.get('trade') or x.get('price')); prev=_num(x.get('settlement') or x.get('pre_close'))
                    if not code or price<=0: continue
                    rows.append({'代码':code,'名称':x.get('name') or x.get('symbol') or '','最新价':price,'涨跌幅':((price/prev)-1)*100 if prev>0 else 0,'最高':_num(x.get('high')),'最低':_num(x.get('low')),'成交量':_num(x.get('volume')),'成交额':_num(x.get('amount')),'换手率':_num(x.get('turnover')),'量比':_num(x.get('ratio'))})
        except Exception as e: errors.append(f'新浪-{market}: {type(e).__name__}: {e}')
    if not rows: raise ConnectionError('；'.join(errors) or '新浪没有有效报价')
    return pd.DataFrame(rows),'新浪财经（直接接口）'

def _eastmoney_snapshot():
    s=_session(); url='https://push2.eastmoney.com/api/qt/clist/get'; params={'pn':1,'pz':6000,'po':1,'np':1,'fltt':2,'invt':2,'fid':'f3','fs':'m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23','fields':'f12,f14,f2,f3,f4,f5,f6,f8,f10,f15,f16,f17,f18'}
    r=s.get(url,params=params,timeout=TIMEOUT); r.raise_for_status(); data=(r.json().get('data') or {}).get('diff') or []
    if not data: raise ConnectionError('东方财富返回空行情')
    return pd.DataFrame([{'代码':str(x.get('f12','')).zfill(6),'名称':x.get('f14',''),'最新价':_num(x.get('f2')),'涨跌幅':_num(x.get('f3')),'成交量':_num(x.get('f5')),'成交额':_num(x.get('f6')),'换手率':_num(x.get('f8')),'量比':_num(x.get('f10')),'最高':_num(x.get('f15')),'最低':_num(x.get('f16')),'今开':_num(x.get('f17')),'昨收':_num(x.get('f18'))} for x in data]),'东方财富（直接接口）'

def _itick_snapshot():
    token=os.getenv('ITICK_TOKEN','').strip(); url=os.getenv('ITICK_A_SHARE_SNAPSHOT_URL','').strip()
    if not token: raise ConnectionError('未配置 ITICK_TOKEN')
    if not url: raise ConnectionError('已配置 ITICK_TOKEN，但未配置 ITICK_A_SHARE_SNAPSHOT_URL')
    r=_session().get(url,headers={'token':token,'accept':'application/json'},timeout=TIMEOUT); r.raise_for_status(); payload=r.json(); data=payload.get('data',payload)
    if isinstance(data,dict): data=data.get('list',data.get('items',[]))
    if not isinstance(data,list) or not data: raise ConnectionError('iTick 返回空行情')
    return pd.DataFrame(data),'iTick'

def get_spot_with_source():
    errors=[]
    for name,fn in [('iTick',_itick_snapshot),('新浪',_sina_snapshot),('东方财富',_eastmoney_snapshot)]:
        for attempt in range(2):
            try:
                df,label=fn()
                if df is not None and not df.empty: return df,label,errors
            except Exception as e: errors.append(f'{name}: {type(e).__name__}: {e}'); time.sleep(0.8*(attempt+1))
    return pd.DataFrame(),'无可用行情源',errors

def get_spot():
    df,source,errors=get_spot_with_source()
    if df.empty: raise ConnectionError('；'.join(errors) or '没有可用行情源')
    return df

def _ak_pool(name):
    try:
        import akshare as ak
        df=getattr(ak,name)()
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def get_limit_up_pool(): return _ak_pool('stock_zt_pool_em')
def get_yesterday_limit_up(): return _ak_pool('stock_zt_pool_previous_em')
def get_strong_pool(): return _ak_pool('stock_zt_pool_strong_em')

def provider_status():
    result={'ok':False,'providers':[]}
    for name,fn in [('iTick',_itick_snapshot),('新浪',_sina_snapshot),('东方财富',_eastmoney_snapshot)]:
        try:
            df,label=fn(); ok=df is not None and not df.empty; result['providers'].append({'name':label,'ok':ok,'rows':int(len(df)) if df is not None else 0}); result['ok']|=ok
        except Exception as e: result['providers'].append({'name':name,'ok':False,'error':f'{type(e).__name__}: {e}'})
    strong=get_strong_pool(); ok=strong is not None and not strong.empty; result['providers'].append({'name':'AKShare-涨停强势池','ok':ok,'rows':int(len(strong))}); result['ok']|=ok
    return result
