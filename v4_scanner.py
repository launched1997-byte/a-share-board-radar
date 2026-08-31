from datetime import datetime
from data_provider import get_spot_with_source

def f(v):
    try:return float(str(v).replace(',','')) if v not in (None,'') else 0.0
    except:return 0.0

def lim_pct(code):
    c=str(code).zfill(6); return 19.0 if c.startswith(('300','301','688','689')) else 9.4

def is_st(name):return 'ST' in str(name).upper() or '退' in str(name)

def ladder(pct,intraday,distance):
    if pct>=9.4:return 'A·打板'
    if pct>=7 and distance<=3:return 'B·冲板'
    if pct>=5 and intraday>=10:return 'C·强势'
    if pct>=3 and intraday>=8:return 'D·异动'
    return 'E·观察'

def score_parts(pct,turnover,ratio,amount,intraday,distance):
    momentum=min(25,(10 if pct>=8 else 7 if pct>=6 else 4 if pct>=4 else 2)+(8 if intraday>=12 else 6 if intraday>=9 else 3 if intraday>=6 else 0)+(7 if distance<=2 else 4 if distance<=4 else 0))
    liquidity=15 if amount>=5e8 else 11 if amount>=2e8 else 7 if amount>=1e8 else 3
    turn=15 if 8<=turnover<=25 else 11 if 5<=turnover<8 or 25<turnover<=32 else 6 if turnover>0 else 0
    vol=15 if 1.3<=ratio<=3.5 else 11 if 1.1<=ratio<1.3 or 3.5<ratio<=5 else 6 if ratio>0 else 0
    board=20 if pct>=9.4 else 15 if pct>=8 else 10 if pct>=6 else 6
    return min(100,int(momentum+liquidity+turn+vol+board)),momentum,liquidity,turn,vol,board

def scan_market():
    df,source,errors=get_spot_with_source(); now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if df is None or df.empty:return {'ok':False,'version':'5.0','source':source,'updated_at':now,'stats':{},'candidates':[],'sector_rank':[],'top10':[],'error':'行情源不可用：'+'；'.join(errors)}
    cols=df.columns
    def v(r,names):
        for x in names:
            if x in cols:return r.get(x)
        return 0
    out=[]
    for _,r in df.iterrows():
        code=str(v(r,['代码','code','symbol'])).zfill(6); name=v(r,['名称','name'])
        if len(code)!=6 or is_st(name):continue
        pct=f(v(r,['涨跌幅','pct_chg','change_percent'])); price=f(v(r,['最新价','trade','price','last'])); high=f(v(r,['最高','high'])); low=f(v(r,['最低','low'])); turnover=f(v(r,['换手率','turnover'])); ratio=f(v(r,['量比','ratio'])); amount=f(v(r,['成交额','amount']))
        intraday=(price/low-1)*100 if low>0 else 0; distance=lim_pct(code)-pct
        stage='打板池' if pct>=lim_pct(code) else '冲板池' if pct>=5 and distance<=5 and intraday>=5 else '异动池' if ((pct>=3 and intraday>=6 and ratio>=1.2) or (pct>=2 and intraday>=8 and amount>=1e8) or (pct>=4 and intraday>=10)) else None
        if not stage:continue
        score,momentum,liquidity,turn_s,vol_s,board_s=score_parts(pct,turnover,ratio,amount,intraday,distance)
        risk=min(100,(25 if turnover>35 else 10 if turnover>28 else 0)+(25 if ratio>5 else 10 if ratio>3.5 else 0)+(20 if amount<8e7 else 0))
        signal='强打候选' if stage=='打板池' and score>=82 and risk<55 else '重点盯盘' if stage=='冲板池' and score>=68 and risk<70 else '异动观察' if stage=='异动池' and score>=62 and risk<75 else '等待确认'
        sector=v(r,['行业','所属行业','sector','industry','板块']); sector=str(sector) if sector not in (None,0,'') else '未分类'
        out.append({'code':code,'name':name,'sector':sector,'stage':stage,'ladder':ladder(pct,intraday,distance),'board_text':'N板待历史确认','score':score,'risk':risk,'turnover':turnover,'volume_ratio':ratio,'amount':round(amount/1e8,2),'pct':pct,'intraday_gain':round(intraday,2),'distance_to_limit':round(max(0,distance),2),'signal':signal,'score_breakdown':{'动能':momentum,'流动性':liquidity,'换手':turn_s,'量能':vol_s,'涨停/梯度':board_s},'data_quality':'实时快照'})
    stage_order={'打板池':0,'冲板池':1,'异动池':2}; out.sort(key=lambda x:(-x['score'],x['risk'],stage_order[x['stage']]))
    sectors={}
    for x in out:
        s=x['sector']; z=sectors.setdefault(s,{'sector':s,'count':0,'best_score':0,'best_name':''}); z['count']+=1
        if x['score']>z['best_score']:z['best_score']=x['score'];z['best_name']=x['name']
    sector_rank=sorted([z for z in sectors.values() if z['sector']!='未分类'],key=lambda z:(z['best_score'],z['count']),reverse=True)[:20]
    top10=sorted(out,key=lambda x:(-x['score'],x['risk'],stage_order[x['stage']]))[:10]
    return {'ok':True,'version':'5.0','source':source,'updated_at':now,'stats':{'limit_up':sum(x['stage']=='打板池' for x in out),'surge':sum(x['stage']=='冲板池' for x in out),'abnormal':sum(x['stage']=='异动池' for x in out),'total':len(out)},'sector_rank':sector_rank,'top10':top10,'candidates':out[:150],'note':'V5：板块→梯度→分数→Top10。实时源缺少板块字段时明确显示未分类；精确N板、竞价、炸板/回封仍需历史/Tick数据，不伪造。'}
