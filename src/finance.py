"""Projeções determinísticas com premissas explícitas, sem chamadas a modelos de IA."""
from datetime import date, timedelta
from core import forecast, required_contribution, money

def position_projection(p, deadline, cdi=10.0, inflation=4.0):
    start=date.fromisoformat(p['day']);end=date.fromisoformat(deadline)
    maturity=date.fromisoformat(p['maturity']) if p.get('maturity') else None
    until=min(end,maturity) if maturity else end
    days=max(0,(until-start).days);mode=p.get('rate_mode','Não informada');rate=p.get('rate') or 0
    if mode=='% CDI':
        business=sum((start+timedelta(days=i)).weekday()<5 for i in range(1,days+1))
        daily=(1+cdi/100)**(1/252)-1;factor=(1+daily*rate/100)**business
    elif mode=='IPCA + % a.a.':factor=((1+inflation/100)*(1+rate/100))**(days/365)
    elif mode=='Prefixado % a.a.':factor=(1+rate/100)**(days/365)
    else:factor=1.0
    gross=round(p['value']*factor);cost=p['principal'] if p.get('principal') is not None else p['value'];gain=max(0,gross-cost);tax=round(gain*(p.get('tax') or 0)/100);net=gross-tax
    available=(maturity is not None and maturity<=end) or p.get('liquidity')=='Diária'
    warnings=[]
    if p.get('currency','BRL')!='BRL':warnings.append('Cotação BRL mantida constante; câmbio futuro não previsto.')
    if mode=='Não informada':warnings.append('Taxa ausente: saldo mantido constante.')
    if p.get('principal') is None:warnings.append('Custo desconhecido: imposto estimado apenas sobre crescimento futuro.')
    if maturity and maturity<end:warnings.append('Após o vencimento: saldo sem reinvestimento ou rendimento adicional.')
    if not available:warnings.append('Disponibilidade na data da meta não confirmada.')
    if 'Cripto' in p['asset_type'] or p['asset_type']=='Bitcoin':warnings.append('Cotação futura de cripto não prevista.')
    return dict(gross=gross,net=net,tax=tax,available=available,warnings=warnings)

def investment_projection(store,p,deadline,cdi=10.0,inflation=4.0):
    from investments import InvestmentBook
    result=position_projection(p,deadline,cdi,inflation);state=InvestmentBook(store).state(p['id'],deadline,True,cdi,inflation)
    if state:
        result['gross']=state['value'];base=p['principal'] if p['principal'] is not None else p['value'];result['tax']=round(max(0,state['value']-base)*(p.get('tax') or 0)/100);result['net']=result['gross']-result['tax']
    else:result.update(gross=0,net=0,tax=0,available=False);result['warnings'].append('Sem saldo conhecido até a data solicitada.')
    return result

def recent_capacity(store,period):
    periods=[p for p in store.periods() if p<=period and (store.rows("SELECT 1 FROM tx WHERE period=? AND amount IS NOT NULL AND status!='Previsto'",(p,)) or store.rows('SELECT 1 FROM card_items WHERE period=?',(p,)))][-3:]
    if not periods:return dict(income=0,expense=0,capacity=0,periods=[])
    sums=[store.summary(p) for p in periods];income=round(sum(s['Receita'] for s in sums)/len(sums));expense=round(sum(s['Despesa'] for s in sums)/len(sums))
    return dict(income=income,expense=expense,capacity=income-expense,periods=periods)

def goal_assessment(store,g,period,today=None):
    today=today or date.today();end=date.fromisoformat(g['deadline']);months=max(0,(end.year-today.year)*12+end.month-today.month)
    links=json_ids(store.setting('goal-links-'+str(g['id']),'[]'));positions=[p for p in store.rows('SELECT * FROM positions') if p['id'] in links]
    cdi=float(store.setting('assumed-cdi','10'));inflation=float(store.setting('assumed-inflation','4'))
    if positions:
        results=[investment_projection(store,p,g['deadline'],cdi,inflation) for p in positions];base=sum(p['value'] for p in positions);future=sum(r['net'] for r in results if r['available']);unavailable=sum(r['net'] for r in results if not r['available']);warnings=[p['name']+': '+w for p,r in zip(positions,results) for w in r['warnings']]
    else:base=g['saved'];future=forecast(base,0,g['annual'],months)[-1];unavailable=0;warnings=[]
    r=(1+g['annual']/100)**(1/12)-1;factor=((1+r)**months-1)/r if abs(r)>1e-12 else months
    need=max(0,round((g['target']-future)/factor)) if factor else max(0,g['target']-future)
    projected=future+round(g['contribution']*factor);capacity=recent_capacity(store,period)
    return dict(base=base,future=future,unavailable=unavailable,need=need,projected=projected,missing=max(0,g['target']-projected),months=months,warnings=warnings,capacity=capacity,linked=bool(positions))

def json_ids(s):
    import json
    return json.loads(s)

def insights(store,period):
    cap=recent_capacity(store,period);out=[];summary=store.summary(period)
    pending=store.rows("SELECT COUNT(*) n FROM tx WHERE period=? AND (status='A revisar' OR amount IS NULL)",(period,))[0]['n']
    if pending:out.append(('Conferir dados',f'{pending} registros do mês precisam de revisão. Diagnósticos usam valores preenchidos, inclusive os importados a revisar.'))
    if cap['periods']:
        if cap['capacity']<0:out.append(('Déficit recorrente',f'Nos últimos {len(cap["periods"])} meses com dados, as despesas superam receitas em média por {money(-cap["capacity"])}. Reduzir gastos ou ampliar receita vem antes de aumentar aportes.'))
        else:out.append(('Capacidade de aporte',f'Sobra média antes de aportes: {money(cap["capacity"])} por mês, com base em {len(cap["periods"])} meses cadastrados. Essa média não garante renda futura.'))
    if summary['Aporte']>max(0,summary['Receita']-summary['Despesa']):out.append(('Aporte acima da sobra',f'O aporte deste mês excede a diferença entre receitas e despesas. Confirme se utilizou saldo anterior ou precisa ajustar o orçamento.'))
    from ledger import Ledger
    spent_categories=Ledger(store).category_spend(period)
    for b in store.rows('SELECT * FROM budgets WHERE period=?',(period,)):
        spent=Ledger(store).budget_spend(period,b['category'])
        if spent>b['amount']:out.append(('Limite ultrapassado',b['category']+': '+money(spent-b['amount'])+' acima do limite. Revise as próximas compras dessa categoria.'))
    cats=sorted([dict(category=k,n=v) for k,v in spent_categories.items()],key=lambda r:r['n'],reverse=True)
    if cats and cats[0]['n']:
        cat=cats[0];out.append(('Onde revisar primeiro',f'{cat["category"]} concentra {money(cat["n"])}. Uma redução hipotética de 10% liberaria {money(round(cat["n"]*.1))} por mês; confira o detalhamento antes de cortar.'))
    emergency=sum(p['value'] for p in store.rows('SELECT * FROM positions') if p['asset_type']=='Reserva de emergência' or 'Reserva de emergência' in p['note'])
    if cap['expense']>0:out.append(('Cobertura da reserva',f'A reserva identificada cobre {emergency/cap["expense"]:.1f} meses da despesa média cadastrada. Defina uma cobertura compatível com sua estabilidade de renda.'))
    for g in store.rows('SELECT * FROM goals'):
        a=goal_assessment(store,g,period)
        if not a['base']:out.append(('Vincular recursos à meta',g['name']+': nenhum valor reservado nem ativo vinculado. Escolha os investimentos destinados à meta para uma análise útil.'))
        if a['missing']:out.append(('Meta com insuficiência',g['name']+f": faltam {money(a['missing'])} no cenário atual. Aporte calculado: {money(a['need'])}/mês. "+(f"Supera a sobra média em {money(a['need']-max(0,cap['capacity']))}. Ajuste prazo, objetivo, gastos ou receita." if a['need']>max(0,cap['capacity']) else 'Cabe na sobra média informada, se ela se mantiver.')))
        else:out.append(('Meta coberta no cenário',g['name']+': a projeção cobre o valor nominal com as premissas cadastradas. Reavalie custos e câmbio periodicamente.'))
        if a['unavailable']:out.append(('Liquidez pendente',g['name']+': '+money(a['unavailable'])+' projetados não foram considerados disponíveis por vencimento ou liquidez não confirmada.'))
    return out
def asset_group(position):
    explicit=position.get('asset_group','A classificar')
    if explicit and explicit!='A classificar':return explicit
    kind=position['asset_type']
    if position.get('currency','BRL')!='BRL':return 'Moedas estrangeiras'
    if kind in ['CDB','LCI','LCA','CDB / liquidez a revisar','Renda fixa a classificar','Reserva de emergência']:return 'Renda fixa'
    if kind in ['Bitcoin','Cripto a classificar','Criptomoeda']:return 'Criptomoedas'
    if kind in ['Ações','ETF','FII','Renda variável']:return 'Renda variável'
    return 'Outros'

def allocation(store):
    result={}
    for p in store.rows('SELECT * FROM positions'):
        group=asset_group(p);result[group]=result.get(group,0)+p['value']
    for a in store.rows('SELECT * FROM accounts'):
        group='Saldo em conta' if a['currency']=='BRL' else 'Moedas estrangeiras';result[group]=result.get(group,0)+store.account_balance(a)
    return result
    
