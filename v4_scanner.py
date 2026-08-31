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
    if df is None or df.empty:return {'ok':False,'version':'6.0','source':source,'updated_at':now,'stats':{},'sector_rank':[],'top10':[],'candidates':[],'error':'行情源不可用：'+'；'.join(errors)}
    cols=df.columns
    def v(r,names):
        for x in names:
            if x in cols:return r.get(x)
        return 0
    out=[]
    for _,r in df.iterrows():
        code=str(v(r,['代码','code','symbol'])).zfill(6); name=v(r,['名称','name'])
        if len(code)!=6 or is_st(name):continue
        pct=f(v(r,['涨跌幅','pct_chg','change_percent'])); price=f(v(r,['最新价','trade','price','last'])); low=f(v(r,['最低','low'])); turnover=f(v(r,['换手率','turnover'])); ratio=f(v(r,['量比','ratio'])); amount=f(v(r,['成交额','amount']))
        intraday=(price/low-1)*100 if low>0 else 0; limit=lim_pct(code); distance=limit-pct
        pool='打板' if pct>=limit else '冲板' if pct>=5 and distance<=5 and intraday>=5 else '异动' if ((pct>=3 and intraday>=6 and ratio>=1.2) or (pct>=2 and intraday>=8 and amount>=1e8) or (pct>=4 and intraday>=10)) else None
        if not pool:continue
        momentum=min(25,(10 if pct>=8 else 7 if pct>=6 else 4 if pct>=4 else 2)+(8 if intraday>=12 else 6 if intraday>=9 else 3 if intraday>=6 else 0)+(7 if distance<=2 else 4 if distance<=4 else 0))
        liquidity=15 if amount>=5e8 else 11 if amount>=2e8 else 7 if amount>=1e8 else 3
        turn=15 if 8<=turnover<=25 else 11 if 5<=turnover<8 or 25<turnover<=32 else 6 if turnover>0 else 0
        vol=15 if 1.3<=ratio<=3.5 else 11 if 1.1<=ratio<1.3 or 3.5<ratio<=5 else 6 if ratio>0 else 0
        ladder=20 if pct>=limit else 15 if pct>=8 else 10 if pct>=6 else 6
        score=min(100,int(momentum+liquidity+turn+vol+ladder)); risk=min(100,(25 if turnover>35 else 10 if turnover>28 else 0)+(25 if ratio>5 else 10 if ratio>3.5 else 0)+(20 if amount<8e7 else 0))
        signal='强打候选' if pool=='打板' and score>=82 and risk<55 else '重点盯盘' if pool=='冲板' and score>=68 and risk<70 else '异动观察' if pool=='异动' and score>=62 and risk<75 else '等待确认'
        sector=v(r,['行业','所属行业','sector','industry','板块']); sector=str(sector) if sector not in (None,0,'') else '未分类'
        out.append({'code':code,'name':name,'sector':sector,'pool':pool,'ladder':('已涨停' if pool=='打板' else '冲板' if pool=='冲板' else '异动'),'board_text':'N板待历史确认','score':score,'risk':risk,'turnover':turnover,'volume_ratio':ratio,'amount':round(amount/1e8,2),'pct':pct,'intraday_gain':round(intraday,2),'distance_to_limit':round(max(0,distance),2),'signal':signal,'score_breakdown':{'动能':momentum,'流动性':liquidity,'换手':turn,'量能':vol,'梯度':ladder},'data_quality':'实时快照'})
    order={'打板':0,'冲板':1,'异动':2};out.sort(key=lambda x:(-x['score'],x['risk'],order[x['pool']]))
    sectors={}
    for x in out:
        s=sectors.setdefault(x['sector'],{'sector':x['sector'],'count':0,'score_sum':0,'best_score':0,'best_name':''});s['count']+=1;s['score_sum']+=x['score']
        if x['score']>s['best_score']:s['best_score']=x['score'];s['best_name']=x['name']
    sr=[dict(x,sector_score=round(x['score_sum']/x['count']+min(20,x['count']*2),1)) for x in sectors.values() if x['sector']!='未分类'];sr.sort(key=lambda x:(x['sector_score'],x['best_score']),reverse=True)
    return {'ok':True,'version':'6.0','source':source,'updated_at':now,'stats':{'limit_up':sum(x['pool']=='打板' for x in out),'surge':sum(x['pool']=='冲板' for x in out),'abnormal':sum(x['pool']=='异动' for x in out),'total':len(out)},'sector_rank':sr[:20],'top10':out[:10],'candidates':out[:150],'note':'V6最终决策版：板块→池→梯度→机会/风险分→Top10。精确N板、竞价、炸板/回封、Tick需真实历史/逐笔数据；当前缺失时不伪造。'}
