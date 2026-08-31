from datetime import datetime
from data_provider import get_spot_with_source

def f(v):
    try:return float(str(v).replace(',','')) if v not in (None,'') else 0.0
    except:return 0.0

def lim_pct(code):
    c=str(code).zfill(6)
    return 19.0 if c.startswith(('300','301','688','689')) else 9.4

def is_st(name):return 'ST' in str(name).upper() or '退' in str(name)

def scan_market():
    df,source,errors=get_spot_with_source(); now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if df is None or df.empty:return {'ok':False,'version':'4.0','source':source,'updated_at':now,'stats':{},'candidates':[],'error':'行情源不可用：'+'；'.join(errors)}
    cols=df.columns
    def v(r,names):
        for x in names:
            if x in cols:return r.get(x)
        return 0
    out=[]
    for _,r in df.iterrows():
        code=str(v(r,['代码','code','symbol'])).zfill(6); name=v(r,['名称','name'])
        if not code or is_st(name):continue
        pct=f(v(r,['涨跌幅','pct_chg','change_percent'])); price=f(v(r,['最新价','trade','price','last'])); high=f(v(r,['最高','high'])); low=f(v(r,['最低','low'])); turnover=f(v(r,['换手率','turnover'])); ratio=f(v(r,['量比','ratio'])); amount=f(v(r,['成交额','amount']))
        intraday=(price/low-1)*100 if low>0 else 0; distance=lim_pct(code)-pct
        if pct>=lim_pct(code): stage='打板池'; score=min(100,int((18 if 8<=turnover<=25 else 12 if turnover>=5 else 5)+(15 if 1.2<=ratio<=3.8 else 5)+(12 if amount>=5e8 else 8 if amount>=3e8 else 4)+(15 if high and price/high>=.998 else 8)+40)); risk=min(100,(30 if turnover>40 else 18 if turnover>30 else 0)+(25 if ratio>5 else 12 if ratio>3.8 else 0)+(20 if amount<8e7 else 0))
        elif pct>=5 and distance<=4 and intraday>=6: stage='冲板池'; score=min(100,int((22 if pct>=8 else 18 if pct>=6 else 14)+(20 if intraday>=12 else 16 if intraday>=9 else 11)+(18 if ratio>=2 else 12 if ratio>=1.5 else 6)+(15 if amount>=5e8 else 10 if amount>=3e8 else 5)+(10 if turnover>=8 else 6)+(15 if distance<=2 else 10))); risk=min(100,(30 if ratio>5 else 15 if ratio>4 else 0)+(25 if turnover>35 else 12 if turnover>28 else 0))
        elif (pct>=3 and intraday>=8 and ratio>=1.5) or (pct>=2 and intraday>=10 and amount>=2e8): stage='异动池'; score=min(100,int((18 if pct>=6 else 12)+(20 if intraday>=12 else 14 if intraday>=9 else 8)+(18 if ratio>=2 else 10)+(15 if amount>=5e8 else 8)+(10 if turnover>=8 else 5))); risk=min(100,(30 if ratio>5 else 15 if ratio>4 else 0)+(25 if turnover>35 else 12 if turnover>28 else 0))
        else:continue
        signal='强打候选' if stage=='打板池' and score>=85 and risk<50 else '重点盯盘' if stage=='冲板池' and score>=75 and risk<65 else '异动观察' if stage=='异动池' and score>=70 and risk<70 else '等待确认'
        out.append({'code':code,'name':name,'stage':stage,'board_text':'历史N板待确认','score':score,'risk':risk,'turnover':turnover,'volume_ratio':ratio,'amount':round(amount/1e8,2),'pct':pct,'intraday_gain':round(intraday,2),'distance_to_limit':round(max(0,distance),2),'signal':signal,'data_quality':'实时快照'})
    order={'打板池':0,'冲板池':1,'异动池':2}; out.sort(key=lambda x:(order[x['stage']],-x['score'],x['risk'],-x['amount']))
    return {'ok':True,'version':'4.0','source':source,'updated_at':now,'stats':{'limit_up':sum(x['stage']=='打板池' for x in out),'surge':sum(x['stage']=='冲板池' for x in out),'abnormal':sum(x['stage']=='异动池' for x in out)},'candidates':out[:80],'note':'V4三层候选池：打板、冲板、异动。重点增加日内低点快速拉升且接近涨停的股票。精确N板/竞价/炸板/回封待历史或Tick数据，不伪造。'}
