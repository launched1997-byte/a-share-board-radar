from datetime import datetime
from data_provider import get_spot_with_source

def f(v):
    try:return float(str(v).replace(',','')) if v not in (None,'') else 0.0
    except:return 0.0

def lim_pct(code):
    c=str(code).zfill(6); return 19.0 if c.startswith(('300','301','688','689')) else 9.4

def is_st(name):return 'ST' in str(name).upper() or '退' in str(name)

def scan_market():
    df,source,errors=get_spot_with_source(); now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if df is None or df.empty:return {'ok':False,'version':'4.1','source':source,'updated_at':now,'stats':{},'candidates':[],'error':'行情源不可用：'+'；'.join(errors)}
    cols=df.columns
    def v(r,names):
        for x in names:
            if x in cols:return r.get(x)
        return 0
    out=[]
    for _,r in df.iterrows():
        code=str(v(r,['代码','code','symbol'])).zfill(6); name=v(r,['名称','name'])
        if not code or len(code)!=6 or is_st(name):continue
        pct=f(v(r,['涨跌幅','pct_chg','change_percent'])); price=f(v(r,['最新价','trade','price','last'])); high=f(v(r,['最高','high'])); low=f(v(r,['最低','low'])); turnover=f(v(r,['换手率','turnover'])); ratio=f(v(r,['量比','ratio'])); amount=f(v(r,['成交额','amount']))
        intraday=(price/low-1)*100 if low>0 else 0; distance=lim_pct(code)-pct
        stage=None; score=0; risk=0
        if pct>=lim_pct(code):
            stage='打板池'; score=min(100,int((18 if 6<=turnover<=28 else 12 if turnover>=3 else 5)+(15 if 1.1<=ratio<=4 else 7)+(12 if amount>=5e8 else 9 if amount>=2e8 else 4)+(15 if high and price/high>=.998 else 8)+40)); risk=min(100,(30 if turnover>45 else 18 if turnover>32 else 0)+(25 if ratio>5 else 12 if ratio>4 else 0)+(20 if amount<8e7 else 0))
        elif pct>=5 and distance<=5 and intraday>=5:
            stage='冲板池'; score=min(100,int((22 if pct>=8 else 18 if pct>=6 else 14)+(20 if intraday>=12 else 16 if intraday>=9 else 11)+(18 if ratio>=2 else 12 if ratio>=1.3 else 6)+(15 if amount>=5e8 else 10 if amount>=2e8 else 5)+(10 if turnover>=6 else 6)+(15 if distance<=2 else 10))); risk=min(100,(30 if ratio>5 else 15 if ratio>4 else 0)+(25 if turnover>35 else 12 if turnover>28 else 0))
        elif (pct>=3 and intraday>=6 and ratio>=1.2) or (pct>=2 and intraday>=8 and amount>=1e8) or (pct>=4 and intraday>=10):
            stage='异动池'; score=min(100,int((18 if pct>=6 else 12)+(20 if intraday>=12 else 14 if intraday>=9 else 8)+(18 if ratio>=2 else 10 if ratio>=1.2 else 5)+(15 if amount>=5e8 else 10 if amount>=2e8 else 6)+(10 if turnover>=6 else 5))); risk=min(100,(30 if ratio>5 else 15 if ratio>4 else 0)+(25 if turnover>35 else 12 if turnover>28 else 0))
        if not stage:continue
        signal='强打候选' if stage=='打板池' and score>=82 and risk<55 else '重点盯盘' if stage=='冲板池' and score>=70 and risk<70 else '异动观察' if stage=='异动池' and score>=65 and risk<75 else '等待确认'
        out.append({'code':code,'name':name,'stage':stage,'board_text':'历史N板待确认','score':score,'risk':risk,'turnover':turnover,'volume_ratio':ratio,'amount':round(amount/1e8,2),'pct':pct,'intraday_gain':round(intraday,2),'distance_to_limit':round(max(0,distance),2),'signal':signal,'data_quality':'实时快照'})
    order={'打板池':0,'冲板池':1,'异动池':2}; out.sort(key=lambda x:(order[x['stage']],-x['score'],x['risk'],-x['amount']))
    return {'ok':True,'version':'4.1','source':source,'updated_at':now,'stats':{'limit_up':sum(x['stage']=='打板池' for x in out),'surge':sum(x['stage']=='冲板池' for x in out),'abnormal':sum(x['stage']=='异动池' for x in out),'total':len(out)},'candidates':out[:150],'note':'V4.1扩大候选池：降低冲板/异动门槛，最多展示150只。重点捕捉日内低点快速拉升、接近涨停和量能异常股票。N板/竞价/炸板/回封在未接入真实历史/Tick前不伪造。'}
