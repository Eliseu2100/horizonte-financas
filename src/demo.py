"""Dados sintéticos de demonstração. Nenhum registro representa uma pessoa real."""
from datetime import date
from core import Store

def seed_demo(store):
    if store.setting('demo')=='1':
        seed_demo_v2(store);seed_demo_v3(store);return
    if store.rows('SELECT id FROM tx') or store.rows('SELECT id FROM positions'):raise ValueError('Demonstração exige um banco separado sem dados pessoais.')
    today=date.today();year=today.year
    store.set('demo','1');store.set('display-name','Perfil demonstrativo')
    for offset in range(6):
        key=today.year*12+today.month-1-offset;y,m=divmod(key,12);period=f'{y:04d}-{m+1:02d}'
        for desc,kind,cat,value in [('Salário demonstrativo','Receita','Salário',600000),('Projeto avulso fictício','Receita','Receitas extras',50000),('Moradia e serviços','Despesa','Moradia e contas',160000),('Mercado e refeições','Despesa','Alimentação',85000+offset*2700),('Mobilidade','Despesa','Transporte',34000),('Cursos e livros','Despesa','Educação',28000),('Passeios','Despesa','Lazer',40000+offset*1300),('Serviços digitais','Despesa','Assinaturas',19000),('Aporte demonstrativo','Aporte','Investimentos',150000)]:
            store.save_tx(dict(period=period,day=period+'-05',description=desc,kind=kind,category=cat,amount=value,account='Conta demonstrativa',status='Confirmado',note='Dado fictício de demonstração'))
    sample=[('CDB demonstrativo A','Banco Exemplo A','CDB',2000000,2200000,'Prefixado % a.a.',10,15,'2030-01-01','Diária'),('LCI demonstrativa','Banco Exemplo B','LCI',800000,840000,'% CDI',90,0,'2029-06-01','No vencimento'),('LCA demonstrativa','Banco Exemplo C','LCA',400000,430000,'IPCA + % a.a.',5,0,'2029-08-01','No vencimento'),('Bitcoin demonstrativo','Corretora Exemplo','Bitcoin',300000,280000,'Não informada',0,0,'','A confirmar'),('Reserva demonstrativa','Banco Exemplo D','Reserva de emergência',900000,900000,'Não informada',0,0,'','Diária')]
    for name,bank,kind,cost,value,mode,rate,tax,maturity,liquid in sample:store.db.execute('INSERT INTO positions(name,institution,asset_type,principal,value,day,maturity,note,rate_mode,rate,tax,liquidity) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(name,bank,kind,cost,value,today.isoformat(),maturity,'Dado fictício. Taxas e tributos são hipóteses ilustrativas.',mode,rate,tax,liquid))
    store.db.execute('UPDATE goals SET name=?,target=?,saved=?,deadline=?,contribution=?,annual=? WHERE id=1',('Intercâmbio demonstrativo',15000000,0,'2030-03-01',150000,6))
    store.db.execute('INSERT OR REPLACE INTO budgets VALUES (?,?,?)',('Lazer',today.strftime('%Y-%m'),35000))
    last=store.rows('SELECT COALESCE(MAX(id),0) n FROM tx')[0]['n']
    store.db.execute('INSERT INTO accounts(name,institution,currency,balance,fx_rate,day,ledger_after,note) VALUES (?,?,?,?,?,?,?,?)',('Conta demonstrativa','Banco Exemplo E','BRL',750000,1,today.isoformat(),last,'Saldo fictício de demonstração'))
    store.db.execute('INSERT INTO positions(name,institution,asset_type,principal,value,day,maturity,note,rate_mode,rate,tax,liquidity,asset_group,currency,fx_rate,native_value) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',('Reserva em dólar fictícia','Corretora Exemplo F','Moeda estrangeira',200000,250000,today.isoformat(),'','Valor e cotação fictícios.','Não informada',0,0,'Diária','Moedas estrangeiras','USD',5,50000))
    store.set('profile-age','30');store.set('profile-profession','Perfil fictício')
    store.db.commit();store.set('goal-links-1','[1,2,3]');seed_demo_v2(store);seed_demo_v3(store)


def seed_demo_v2(store):
    if store.setting('demo-v2')=='1':return
    from ledger import Ledger
    from datetime import timedelta
    ledger=Ledger(store);today=date.today();period=today.strftime('%Y-%m');account='Conta demonstrativa'
    card=ledger.save_card(dict(name='Cartão demonstrativo',institution='Banco Exemplo E',limit_amount=600000,closing_day=20,due_day=28,payment_account=account,color='#007AFF'))
    ledger.add_purchase(card,'Notebook de demonstração',240000,period+'-05','Compras',6,period)
    ledger.add_purchase(card,'Mercado demonstrativo',42000,period+'-07','Alimentação',1,period)
    ledger.add_purchase(card,'Assinatura demonstrativa',5900,period+'-08','Assinaturas',1,period)
    ledger.pay_invoice(card,period,30000,today.isoformat(),account)
    due=(today+timedelta(days=3)).isoformat();store.save_tx(dict(period=due[:7],day=due,due_day=due,description='Internet demonstrativa',kind='Despesa',category='Moradia e contas',amount=12000,account=account,status='Previsto',note='Compromisso fictício para demonstrar a agenda.'))
    store.set('demo-v2','1')

def seed_demo_v3(store):
    if store.setting('demo-v3')=='1':return
    from investments import InvestmentBook,end_month
    from ledger import add_month
    book=InvestmentBook(store);positions=store.rows("SELECT * FROM positions WHERE asset_type='CDB' ORDER BY id LIMIT 1")
    if not positions:return
    ident=positions[0]['id'];period=date.today().strftime('%Y-%m')
    for i in range(6):
        month=add_month(period,i-5)
        if i:
            tx=store.rows("SELECT * FROM tx WHERE period=? AND kind='Aporte' AND description='Aporte demonstrativo'",(month,))
            if tx:book.add_event(ident,tx[0]['day'],'Aporte',150000,tx_id=tx[0]['id'])
        book.save_value(ident,min(end_month(month),date.today().isoformat()),1350000+i*170000,origin='Demonstração fictícia')
    store.set('demo-v3','1')
    
