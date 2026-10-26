"""Diagnóstico local sem exportar nomes, saldos, descrições ou fotos."""
from datetime import date,datetime
import sqlite3

def run_diagnostics(store):
    checks=[]
    def add(name,ok,detail=''):checks.append(dict(name=name,status='ok' if ok else 'falha',detail=detail))
    integrity=store.db.execute('PRAGMA integrity_check').fetchall();add('Integridade SQLite',len(integrity)==1 and integrity[0][0]=='ok')
    foreign=store.db.execute('PRAGMA foreign_key_check').fetchall();add('Vínculos entre tabelas',not foreign,str(len(foreign))+' inconsistências')
    add('Versão do esquema',store.setting('schema-version')=='3')
    bad=0
    for table,columns in [('tx',['day','due_day']),('positions',['day','maturity']),('goals',['deadline']),('investment_events',['day']),('investment_values',['day'])]:
        for row in store.rows('SELECT '+','.join(columns)+' FROM '+table):
            for key in columns:
                if row[key]:
                    try:date.fromisoformat(row[key])
                    except (TypeError,ValueError):bad+=1
    add('Datas válidas',bad==0,str(bad)+' datas inválidas')
    bad=store.rows("SELECT COUNT(*) n FROM tx WHERE amount<0 OR status NOT IN ('Confirmado','Previsto','A revisar')")[0]['n'];add('Valores e situações dos lançamentos',bad==0)
    from ledger import Ledger
    ledger=Ledger(store);mismatches=0
    for period in store.periods():
        if sum(ledger.category_spend(period).values())!=store.summary(period)['Despesa']:mismatches+=1
    add('Consumo por categoria e mês',mismatches==0)
    bad=store.rows('SELECT COUNT(*) n FROM investment_events e JOIN tx t ON t.id=e.tx_id WHERE e.kind!=t.kind OR e.amount!=t.amount OR t.status!=?',('Confirmado',))[0]['n'];add('Carteira e caixa sem divergência',bad==0)
    from investments import InvestmentBook
    book=InvestmentBook(store,seed=False);negative=0
    for p in store.rows('SELECT id FROM positions'):
        state=book.state(p['id'],date.today().isoformat())
        if state and state['value']<0:negative+=1
    add('Saldos conhecidos da carteira',negative==0)
    return dict(app='Elisei',schema=store.setting('schema-version'),generated_at=datetime.now().isoformat(),passed=all(x['status']=='ok' for x in checks),checks=checks,counts={table:store.rows('SELECT COUNT(*) n FROM '+table)[0]['n'] for table in ['tx','accounts','positions','investment_events','investment_values','cards','attachments']},scope='Integridade e coerência dos registros locais. Não confirma saldos bancários, preços de mercado ou segurança de todo o computador.')
  
