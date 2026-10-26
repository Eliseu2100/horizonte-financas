"""Histórico da carteira: aportes/resgates separados de saldos conferidos e estimativas."""
from datetime import date
from calendar import monthrange
from core import money

def end_month(period):
    y,m=map(int,period.split('-'));return date(y,m,monthrange(y,m)[1]).isoformat()

def migrate(store):
    store.db.executescript('''
    CREATE TABLE IF NOT EXISTS investment_events(id INTEGER PRIMARY KEY,position_id INTEGER NOT NULL REFERENCES positions(id) ON DELETE CASCADE,day TEXT NOT NULL,kind TEXT NOT NULL,amount INTEGER NOT NULL,native_amount INTEGER NOT NULL,fx_rate REAL NOT NULL,tx_id INTEGER UNIQUE REFERENCES tx(id) ON DELETE SET NULL,note TEXT DEFAULT '',principal_before INTEGER,owns_tx INTEGER DEFAULT 0,included_value_id INTEGER);
    CREATE TABLE IF NOT EXISTS investment_values(id INTEGER PRIMARY KEY,position_id INTEGER NOT NULL REFERENCES positions(id) ON DELETE CASCADE,day TEXT NOT NULL,value INTEGER NOT NULL,native_value INTEGER NOT NULL,fx_rate REAL NOT NULL,event_checkpoint INTEGER DEFAULT 0,origin TEXT DEFAULT 'Conferido',UNIQUE(position_id,day));
    CREATE INDEX IF NOT EXISTS ix_invest_events_position_day ON investment_events(position_id,day);
    CREATE INDEX IF NOT EXISTS ix_invest_values_position_day ON investment_values(position_id,day);
    ''')
    if 'owns_tx' not in {r[1] for r in store.db.execute('PRAGMA table_info(investment_events)')}:store.db.execute('ALTER TABLE investment_events ADD COLUMN owns_tx INTEGER DEFAULT 0')
    if 'included_value_id' not in {r[1] for r in store.db.execute('PRAGMA table_info(investment_events)')}:store.db.execute('ALTER TABLE investment_events ADD COLUMN included_value_id INTEGER')
    seed_positions(store);store.db.execute("INSERT OR REPLACE INTO settings VALUES('schema-version','3')");store.db.commit()

def seed_positions(store):
    for p in store.rows('SELECT * FROM positions WHERE id NOT IN (SELECT position_id FROM investment_values)'):
        if not p['day']:continue
        try:date.fromisoformat(p['day'])
        except ValueError:continue
        native=p['native_value'] if p.get('native_value') is not None else round(p['value']/max(.000001,p['fx_rate'] or 1))
        store.db.execute('INSERT INTO investment_values(position_id,day,value,native_value,fx_rate,origin) VALUES(?,?,?,?,?,?)',(p['id'],p['day'],p['value'],native,p['fx_rate'] or 1,'Saldo inicial registrado'))
    store.db.commit()

class InvestmentBook:
    def __init__(self,store,seed=True):
        self.s=store
        if seed:seed_positions(store)
    def position(self,ident):
        rows=self.s.rows('SELECT * FROM positions WHERE id=?',(ident,))
        if not rows:raise ValueError('Investimento não encontrado.')
        return rows[0]
    def state(self,ident,cutoff,estimate=False,cdi=None,inflation=None):
        date.fromisoformat(cutoff);p=self.position(ident);quotes=self.s.rows('SELECT * FROM investment_values WHERE position_id=? AND day<=? ORDER BY day DESC,id DESC LIMIT 1',(ident,cutoff))
        if not quotes:return None
        quote=quotes[0];balance=quote['value'];native=quote['native_value'];last=quote['day'];events=self.s.rows('SELECT * FROM investment_events WHERE position_id=? AND day<=? AND (day>? OR (day=? AND id>?)) AND COALESCE(included_value_id,0)<>? ORDER BY day,id',(ident,cutoff,quote['day'],quote['day'],quote['event_checkpoint'],quote['id']))
        from finance import position_projection
        def grow(value,start,end):
            if not estimate or end<=start:return value
            projected=dict(p,value=value,day=start,principal=None,tax=0)
            return position_projection(projected,end,float(self.s.setting('assumed-cdi','10')) if cdi is None else cdi,float(self.s.setting('assumed-inflation','4')) if inflation is None else inflation)['gross']
        for event in events:
            balance=grow(balance,last,event['day']);sign=1 if event['kind']=='Aporte' else -1;balance+=sign*event['amount'];native+=sign*event['native_amount'];last=event['day']
        balance=grow(balance,last,cutoff)
        return dict(value=balance,native_value=native,fx_rate=quote['fx_rate'],quote_day=quote['day'],asof=last,estimated=estimate and cutoff>quote['day'],quote_id=quote['id'])
    def save_value(self,ident,day,native_value,fx_rate=1,origin='Conferido'):
        p=self.position(ident);date.fromisoformat(day)
        if day>date.today().isoformat():raise ValueError('Saldo conferido não pode ter data futura. Use a estimativa para projeções.')
        if native_value<0 or fx_rate<=0:raise ValueError('Saldo não negativo e câmbio positivo são obrigatórios.')
        import math
        if not math.isfinite(fx_rate):raise ValueError('Cotação inválida.')
        if round(native_value*fx_rate)>10**13:raise ValueError('Valor convertido acima do limite suportado.')
        if p['currency']=='BRL':fx_rate=1
        checkpoint=self.s.rows('SELECT COALESCE(MAX(id),0) n FROM investment_events WHERE position_id=? AND day<=?',(ident,day))[0]['n']
        with self.s.db:
            self.s.db.execute('INSERT INTO investment_values(position_id,day,value,native_value,fx_rate,event_checkpoint,origin) VALUES(?,?,?,?,?,?,?) ON CONFLICT(position_id,day) DO UPDATE SET value=excluded.value,native_value=excluded.native_value,fx_rate=excluded.fx_rate,event_checkpoint=excluded.event_checkpoint,origin=excluded.origin',(ident,day,round(native_value*fx_rate),native_value,fx_rate,checkpoint,origin))
        self.sync(ident)
    def sync(self,ident):
        state=self.state(ident,date.today().isoformat())
        if state:
            with self.s.db:self.s.db.execute('UPDATE positions SET value=?,native_value=?,fx_rate=?,day=? WHERE id=?',(state['value'],state['native_value'],state['fx_rate'],state['asof'],ident))
    def add_event(self,ident,day,kind,native_amount,fx_rate=1,account='',tx_id=None,note='',create_tx=True,included_in_balance=False):
        import math
        p=self.position(ident);date.fromisoformat(day)
        if day>date.today().isoformat():raise ValueError('Use lançamentos previstos na agenda para aportes futuros. Aqui registre movimentos já realizados.')
        if kind not in ['Aporte','Resgate'] or native_amount<=0:raise ValueError('Escolha aporte/resgate e um valor positivo.')
        if p['currency']=='BRL':fx_rate=1
        if not math.isfinite(fx_rate) or fx_rate<=0:raise ValueError('Cotação inválida.')
        if round(native_amount*fx_rate)>10**13:raise ValueError('Valor convertido acima do limite suportado.')
        amount=round(native_amount*fx_rate);state=self.state(ident,day)
        if kind=='Resgate' and (not state or amount>state['value']):raise ValueError('Resgate acima do saldo conhecido. Confira o saldo antes de registrar.')
        if kind=='Aporte' and p['maturity'] and p['maturity']<day and p['asset_type'] in ['CDB','LCI','LCA']:raise ValueError('O título já venceu. Cadastre o novo contrato para novos aportes.')
        if included_in_balance and not tx_id and create_tx:raise ValueError('Saldo já incluído só se aplica a lançamento existente.')
        linked_existing=bool(tx_id);latest=self.s.rows('SELECT * FROM investment_values WHERE position_id=? AND day>=? ORDER BY day DESC LIMIT 1',(ident,day));included_value_id=latest[0]['id'] if included_in_balance and latest and latest[0]['day']==day else None
        owns_tx=not tx_id and create_tx
        with self.s.db:
            if tx_id:
                rows=self.s.rows('SELECT * FROM tx WHERE id=?',(tx_id,))
                if not rows or rows[0]['kind']!=kind or rows[0]['amount']!=amount or rows[0]['status']!='Confirmado' or rows[0]['period']!=day[:7]:raise ValueError('O lançamento existente precisa ter o mesmo tipo, valor, mês e estar confirmado.')
                if self.s.rows('SELECT 1 FROM investment_events WHERE tx_id=?',(tx_id,)):raise ValueError('Esse lançamento já está vinculado à carteira.')
            elif create_tx:
                if account and not self.s.rows("SELECT 1 FROM accounts WHERE name=? AND currency='BRL'",(account,)):raise ValueError('Para movimentar caixa, selecione uma conta em reais.')
                tx_id=self.s.db.execute('INSERT INTO tx(period,day,description,kind,category,amount,account,status,source,note) VALUES(?,?,?,?,?,?,?,?,?,?)',(day[:7],day,kind+' • '+p['name'],kind,'Investimentos',amount,account,'Confirmado','Carteira mensal',note)).lastrowid
            if not state:self.s.db.execute('INSERT INTO investment_values(position_id,day,value,native_value,fx_rate,origin) VALUES(?,?,?,?,?,?)',(ident,day,0,0,fx_rate,'Abertura antes do primeiro movimento'))
            event=self.s.db.execute('INSERT INTO investment_events(position_id,day,kind,amount,native_amount,fx_rate,tx_id,note,principal_before,owns_tx,included_value_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(ident,day,kind,amount,native_amount,fx_rate,tx_id,note,p['principal'],int(owns_tx),included_value_id)).lastrowid
            principal=p['principal'] if (included_in_balance or (latest and latest[0]['day']>day)) else ((p['principal']+amount) if kind=='Aporte' and p['principal'] is not None else None)
            self.s.db.execute('UPDATE positions SET principal=? WHERE id=?',(principal,ident))
        self.sync(ident);return event
    def delete_latest_event(self,ident):
        rows=self.s.rows('SELECT * FROM investment_events WHERE position_id=? ORDER BY id DESC LIMIT 1',(ident,))
        if not rows:raise ValueError('Não há movimento para desfazer.')
        event=rows[0]
        with self.s.db:
            self.s.db.execute('DELETE FROM investment_events WHERE id=?',(event['id'],))
            if event['tx_id'] and event['owns_tx']:self.s.db.execute('DELETE FROM tx WHERE id=?',(event['tx_id'],))
            self.s.db.execute('UPDATE positions SET principal=? WHERE id=?',(event['principal_before'],ident))
        self.sync(ident)
    def monthly(self,period,ident=None):
        from ledger import add_month
        positions=self.s.rows('SELECT * FROM positions'+(' WHERE id=?' if ident else ''),(ident,) if ident else ());rows=[]
        for p in positions:
            opening=self.state(p['id'],end_month(add_month(period,-1)));closing=self.state(p['id'],end_month(period));events=self.s.rows('SELECT * FROM investment_events WHERE position_id=? AND substr(day,1,7)=?',(p['id'],period));aporte=sum(x['amount'] for x in events if x['kind']=='Aporte');resgate=sum(x['amount'] for x in events if x['kind']=='Resgate');confirmed=bool(closing and closing['quote_day'][:7]==period)
            gain=closing['value']-opening['value']-aporte+resgate if confirmed and opening else None
            rows.append(dict(position=p,opening=opening['value'] if opening else None,closing=closing['value'] if closing else None,contribution=aporte,withdrawal=resgate,gain=gain,quote_day=closing['quote_day'] if closing else '',confirmed=confirmed))
        return rows
    def unlinked(self,period):return self.s.rows("SELECT * FROM tx WHERE period=? AND kind IN ('Aporte','Resgate') AND status='Confirmado' AND amount IS NOT NULL AND id NOT IN(SELECT tx_id FROM investment_events WHERE tx_id IS NOT NULL) ORDER BY day,id",(period,))

    def delete_value(self,ident):
        rows=self.s.rows('SELECT * FROM investment_values WHERE id=?',(ident,))
        if not rows:raise ValueError('Saldo não encontrado.')
        quote=rows[0]
        if self.s.rows('SELECT COUNT(*) n FROM investment_values WHERE position_id=?',(quote['position_id'],))[0]['n']<=1:raise ValueError('Mantenha um saldo inicial. Você pode corrigir seu valor ou sua data.')
        with self.s.db:self.s.db.execute('DELETE FROM investment_values WHERE id=?',(ident,))
        self.sync(quote['position_id'])
  
