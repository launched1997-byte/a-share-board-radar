from datetime import datetime
import pandas as pd
from data_provider import get_spot_with_source,get_limit_up_pool,get_yesterday_limit_up,get_strong_pool,get_blown_pool

def f(v):
    try:return float(str(v).replace(',','').replace('%','')) if v not in (None,'') else 0.0
    except:return 0.0

def is_st(name):return 'ST' in str(name).upper() or '退' in str(name)

def _col(df,names):
    if df is None or df.empty:return None
    for n in names:
        if n in df.columns:return n
    return None

def _board_map(df):
    if df is None or df.empty:return {}
    code_col=_col(df,['代码','股票代码','code','证券代码']); n_col=_col(df,['连续涨停天数','连板数','连续涨停','连板'])
    if not code_col:return {}
    out={}
    for _,r in df.iterrows():
        code=str(r.get(code_col,'')).zfill(6)
        if len(code)==6:out[code]=max(1,int(f(r.get(n_col,1)))) if n_col else 1
    return out

def _pct_map(df):
    if df is None or df.empty:return {}
    code_col=_col(df,['代码','股票代码','code','证券代码']); pct_col=_col(df,['涨跌幅','涨幅','涨跌'])
    if not code_col or not pct_col:return {}
    return {str(r.get(code_col,'')).zfill(6):f(r.get(pct_col)) for _,r in df.iterrows()}

def _sentiment(today,previous,blown):
    prev_pct=_pct_map(previous); vals=list(prev_pct.values()); med=float(pd.Series(vals).median()) if vals else None; avg=float(pd.Series(vals).mean()) if vals else None
    today_n=len(today) if today is not None else 0; blown_n=len(blown) if blown is not None else 0; attempts=today_n+blown_n; blow_rate=blown_n/attempts*100 if attempts else None
    boards=_board_map(today); height=max(boards.values()) if boards else 0
    prev_boards=_board_map(previous)
    tiers={}
    for n in range(1,6):
        den=sum(1 for v in prev_boards.values() if v==n); num=sum(1 for v in boards.values() if v==n+1)
        tiers[f'{n}进{n+1}']=round(num/den*100,1) if den else None
    if med is None: label='数据不足'
    elif med>=3 and (blow_rate is None or blow_rate<20): label='高潮/强势'
    elif med>=0: label='修复/偏强'
    elif med>-2: label='分歧'
    else: label='退潮'
    return {'yesterday_median_pct':round(med,2) if med is not None else None,'yesterday_avg_pct':round(avg,2) if avg is not None else None,'blow_rate':round(blow_rate,1) if blow_rate is not None else None,'limit_up_count':today_n,'blown_count':blown_n,'height':height,'promotion_rate':tiers,'sentiment':label}

def scan_market():
    df,source,errors=get_spot_with_source();now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if df is None or df.empty:return {'ok':False,'version':'8.0','source':source,'updated_at':now,'stats':{},'sector_rank':[],'top10':[],'candidates':[],'error':'行情源不可用：'+'；'.join(errors)}
    limit_df=get_limit_up_pool();prev_df=get_yesterday_limit_up();strong_df=get_strong_pool();blown_df=get_blown_pool()
    boards=_board_map(limit_df);prev_boards=_board_map(prev_df);strong=set(_board_map(strong_df));sentiment=_sentiment(limit_df,prev_df,blown_df)
    cols=df.columns;out=[]
    def v(r,names):
        for x in names:
            if x in cols:return r.get(x)
        return 0
    for _,r in df.iterrows():
        code=str(v(r,['代码','code','symbol'])).zfill(6);name=v(r,['名称','name'])
        if len(code)!=6 or is_st(name):continue
        pct=f(v(r,['涨跌幅','pct_chg','change_percent']));price=f(v(r,['最新价','trade','price','last']));low=f(v(r,['最低','low']));turnover=f(v(r,['换手率','turnover']));ratio=f(v(r,['量比','ratio']));amount=f(v(r,['成交额','amount']))
        intraday=(price/low-1)*100 if low>0 else 0;board=boards.get(code,0);limit=19 if code.startswith(('300','301','688','689')) else 9.4;distance=limit-pct
        pool='打板' if pct>=limit else '冲板' if pct>=5 and distance<=5 and intraday>=5 else '异动' if ((pct>=3 and intraday>=6 and ratio>=1.2) or (pct>=2 and intraday>=8 and amount>=1e8) or (pct>=4 and intraday>=10)) else None
        if not pool:continue
        momentum=min(25,(10 if pct>=8 else 7 if pct>=6 else 4 if pct>=4 else 2)+(8 if intraday>=12 else 6 if intraday>=9 else 3 if intraday>=6 else 0)+(7 if distance<=2 else 4 if distance<=4 else 0))
        liquidity=15 if amount>=5e8 else 11 if amount>=2e8 else 7 if amount>=1e8 else 3
        turn=15 if 8<=turnover<=25 else 11 if 5<=turnover<8 or 25<turnover<=32 else 6 if turnover>0 else 0
        vol=15 if 1.3<=ratio<=3.5 else 11 if 1.1<=ratio<1.3 or 3.5<ratio<=5 else 6 if ratio>0 else 0
        ladder=20 if board>=4 else 17 if board==3 else 13 if board==2 else 9 if pct>=limit else 5
        if code in strong:ladder=min(20,ladder+3)
        risk=min(100,(25 if turnover>35 else 10 if turnover>28 else 0)+(25 if ratio>5 else 10 if ratio>3.5 else 0)+(20 if amount<8e7 else 0))
        score=min(100,int(momentum+liquidity+turn+vol+ladder-max(0,risk-20)*0.25))
        signal='强打候选' if pool=='打板' and score>=82 and risk<55 else '重点盯盘' if pool=='冲板' and score>=68 and risk<70 else '异动观察' if pool=='异动' and score>=62 and risk<75 else '等待确认'
        sector=v(r,['行业','所属行业','sector','industry','板块']);sector=str(sector) if sector not in (None,0,'') else '未分类'
        out.append({'code':code,'name':name,'sector':sector,'pool':pool,'ladder':f'{board}板' if board else ('冲板' if pool=='冲板' else '异动'),'board':board,'score':score,'risk':risk,'turnover':turnover,'volume_ratio':ratio,'amount':round(amount/1e8,2),'pct':pct,'intraday_gain':round(intraday,2),'distance_to_limit':round(max(0,distance),2),'signal':signal,'score_breakdown':{'动能':momentum,'流动性':liquidity,'换手':turn,'量能':vol,'连板梯度':ladder},'data_quality':'实时快照+AKShare涨停池'})
    out.sort(key=lambda x:(-x['score'],x['risk'],-x['board']))
    sectors={}
    for x in out:
        s=sectors.setdefault(x['sector'],{'sector':x['sector'],'count':0,'score_sum':0,'best_score':0,'best_name':''});s['count']+=1;s['score_sum']+=x['score']
        if x['score']>s['best_score']:s['best_score']=x['score'];s['best_name']=x['name']
    sr=[dict(x,sector_score=round(x['score_sum']/x['count']+min(20,x['count']*2),1)) for x in sectors.values() if x['sector']!='未分类'];sr.sort(key=lambda x:(x['sector_score'],x['best_score']),reverse=True)
    return {'ok':True,'version':'8.0','source':source,'updated_at':now,'stats':{'limit_up':sum(x['pool']=='打板' for x in out),'surge':sum(x['pool']=='冲板' for x in out),'abnormal':sum(x['pool']=='异动' for x in out),'total':len(out),'confirmed_board':sum(x['board']>0 for x in out)},'sentiment':sentiment,'sector_rank':sr[:20],'top10':out[:10],'candidates':out[:150],'note':'V8：移植连板系统最有价值的硬指标——分层晋级率、昨日涨停赚钱效应中位数、炸板率、空间板高度、梯队结构。缺少分钟/Tick时不伪造封板时间和回封数据。'}
