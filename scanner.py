from datetime import datetime
from data_provider import get_spot_with_source

def f(v):
    try:
        return float(str(v).replace(',','').strip()) if v not in (None,'') else 0.0
    except Exception:
        return 0.0

def norm(df):
    if df is None or df.empty: return None
    df=df.copy()
    for c in ['代码','名称','最新价','涨跌幅','最高','成交额','换手率','量比']:
        if c not in df.columns: df[c]=0 if c!='名称' else ''
    df['代码']=df['代码'].astype(str).str.extract(r'(\d{6})')[0].fillna('')
    return df

def limit_up(r):
    code=str(r.get('代码','')).zfill(6); name=str(r.get('名称','')); pct=f(r.get('涨跌幅'))
    if 'ST' in name.upper(): return False
    if code.startswith(('300','301','688','689')): return pct>=19.0
    if code.startswith(('8','4')): return pct>=28.0
    return pct>=9.4

def score(r):
    t,v,a=f(r.get('换手率')),f(r.get('量比')),f(r.get('成交额')); p,h=f(r.get('最新价')),f(r.get('最高'))
    s=15 if 8<=t<=25 else 10 if 5<=t<8 or 25<t<=35 else 6 if 3<=t<5 else 0
    s+=15 if 1.2<=v<=2.5 else 10 if 2.5<v<=3.5 else 7 if .9<=v<1.2 else 4 if 3.5<v<=5 else 0
    s+=10 if a>=3e8 else 7 if a>=2e8 else 5 if a>=1e8 else 0
    if h>0: s+=15 if p/h>=.998 else 10 if p/h>=.99 else 5 if p/h>=.97 else 0
    if limit_up(r): s+=15
    s+=10 if a>=3e8 else 5 if a>=1e8 else 0
    return min(100,int(s))

def risk(r):
    t,v,a=f(r.get('换手率')),f(r.get('量比')),f(r.get('成交额')); x=25 if t>35 else 10 if t>30 else 0
    x+=25 if v>4 else 10 if v>3.5 else 0
    x+=20 if a<1e8 else 0
    return min(100,x)

def scan_market():
    spot,source,errors=get_spot_with_source(); spot=norm(spot)
    now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if spot is None:
        return {'ok':False,'updated_at':now,'source':source,'source_errors':errors,'limit_up':0,'yesterday_limit_up':0,'candidates':[],'error':'所有行情源均不可用：'+'；'.join(errors)}
    pool=spot[spot.apply(limit_up,axis=1)]
    out=[]
    for _,r in pool.iterrows():
        s=score(r); rr=risk(r)
        out.append({'code':str(r.get('代码','')).zfill(6),'name':r.get('名称',''),'board':1,'score':s,'risk':rr,'turnover':f(r.get('换手率')),'volume_ratio':f(r.get('量比')),'amount':round(f(r.get('成交额'))/1e8,2),'pct':f(r.get('涨跌幅')),'signal':'强接力' if s>=85 and rr<50 else '重点观察' if s>=80 and rr<65 else '等确认' if s>=70 else '放弃'})
    out.sort(key=lambda x:(x['score'],-x['risk']),reverse=True)
    return {'ok':True,'updated_at':now,'source':source,'source_errors':errors,'limit_up':len(pool),'yesterday_limit_up':0,'candidates':out[:30],'note':'V2.0：多源容错；当前按全市场快照识别今日涨停。精确N板、竞价、炸板和回封将在实时历史数据接入后启用。'}
