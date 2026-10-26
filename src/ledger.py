"""Cartões, conciliação e organização financeira local do Horizonte."""
from datetime import date, timedelta, datetime
from pathlib import Path
import calendar, csv, hashlib, html, re, uuid
from core import CATEGORIES, KINDS, cents

def add_month(period,offset=1):
    y,m=map(int,period.split('-'));y,m=divmod(y*12+m-1+offset,12);return f'{y:04d}-{m+1:02d}'

def month_day(period,day):
    y,m=map(int,period.split('-'));return date(y,m,min(int(day),calendar.monthrange(y,m)[1])).isoformat()

def check_period(period):
    if not re.fullmatch(r'\d{4}-\d{2}',period):raise ValueError('Competência deve seguir AAAA-MM.')
    date.fromisoformat(period+'-01')

def migrate(store):
    db=store.db
    db.executescript('''
    CREATE TABLE IF NOT EXISTS categories(name TEXT PRIMARY KEY,parent TEXT DEFAULT '',color TEXT DEFAULT '#007AFF',archived INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS cards(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,institution TEXT,limit_amount INTEGER,closing_day INTEGER,due_day INTEGER,payment_account TEXT,color TEXT DEFAULT '#007AFF',archived INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS card_items(id INTEGER PRIMARY KEY,card_id INTEGER NOT NULL REFERENCES cards(id),purchase_day TEXT,period TEXT,description TEXT,category TEXT,amount INTEGER,installment INTEGER,installments INTEGER,batch_key TEXT,source_key TEXT UNIQUE,note TEXT);
    CREATE TABLE IF NOT EXISTS card_payments(id INTEGER PRIMARY KEY,card_id INTEGER REFERENCES cards(id),period TEXT,day TEXT,amount INTEGER,account TEXT,tx_id INTEGER UNIQUE REFERENCES tx(id));
    CREATE TABLE IF NOT EXISTS attachments(id INTEGER PRIMARY KEY,tx_id INTEGER REFERENCES tx(id) ON DELETE CASCADE,name TEXT,mime TEXT,data BLOB);
    CREATE INDEX IF NOT EXISTS ix_tx_period ON tx(period);
    CREATE INDEX IF NOT EXISTS ix_items_card_period ON card_items(card_id,period);
    ''')
    columns={r[1] for r in db.execute('PRAGMA table_info(tx)')}
    for key,definition in [('due_day','TEXT'),('tags',"TEXT DEFAULT ''"),('series_key',"TEXT DEFAULT ''"),('occurrence_index','INTEGER DEFAULT 1'),('invoice_card_id','INTEGER'),('invoice_period','TEXT')]:
        if key not in columns:db.execute('ALTER TABLE tx ADD COLUMN '+key+' '+definition)
    db.execute("UPDATE tx SET due_day=day WHERE due_day IS NULL AND status='Previsto'")
    if not db.execute('SELECT 1 FROM categories').fetchone():
        for n in CATEGORIES:db.execute('INSERT OR IGNORE INTO categories(name) VALUES (?)',(n,))
    for row in db.execute('SELECT DISTINCT category FROM tx UNION SELECT DISTINCT category FROM budgets'):
        if row[0]:db.execute('INSERT OR IGNORE INTO categories(name) VALUES (?)',(row[0],))
    from investments import migrate as migrate_investments
    migrate_investments(store)

class Ledger:
    def __init__(self,store):self.s=store
    def categories(self,archived=False):return self.s.rows('SELECT * FROM categories'+('' if archived else ' WHERE archived=0')+' ORDER BY parent,name')
    def save_category(self,name,parent='',color='#007AFF',old=None):
        name=name.strip();parent=parent.strip()
        if not name or len(name)>60:raise ValueError('Nome da categoria: de 1 a 60 caracteres.')
        if parent==name or parent==old:raise ValueError('A categoria não pode ser sua própria subcategoria.')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('Use uma cor hexadecimal, como #007AFF.')
        if parent:
            row=self.s.rows('SELECT * FROM categories WHERE name=? AND archived=0',(parent,))
            if not row or row[0]['parent']:raise ValueError('Escolha uma categoria principal, sem outro nível acima.')
            if old and self.s.rows('SELECT 1 FROM categories WHERE parent=?',(old,)):raise ValueError('Uma categoria com filhos precisa permanecer principal.')
        with self.s.db:
            if old:
                self.s.db.execute('UPDATE categories SET name=?,parent=?,color=? WHERE name=?',(name,parent,color,old))
                if name!=old:
                    for table in ['tx','budgets','card_items']:self.s.db.execute('UPDATE '+table+' SET category=? WHERE category=?',(name,old))
                    self.s.db.execute('UPDATE categories SET parent=? WHERE parent=?',(name,old))
            else:self.s.db.execute('INSERT INTO categories(name,parent,color) VALUES (?,?,?)',(name,parent,color))
    def category_spend(self,period):
        result={}
        for row in self.s.rows("SELECT category,SUM(amount) n FROM tx WHERE period=? AND kind='Despesa' AND status!='Previsto' GROUP BY category",(period,))+self.s.rows('SELECT category,SUM(amount) n FROM card_items WHERE period=? GROUP BY category',(period,)):
            result[row['category']]=result.get(row['category'],0)+(row['n'] or 0)
        return result
    def budget_spend(self,period,category):
        names=[category]+[r['name'] for r in self.s.rows('SELECT name FROM categories WHERE parent=?',(category,))]
        spent=self.category_spend(period);return sum(spent.get(name,0) for name in names)
    def save_card(self,data,ident=None):
        data=dict(data);data['name']=data['name'].strip()
        if not data['name']:raise ValueError('Informe o nome do cartão.')
        if not 1<=data['closing_day']<=31 or not 1<=data['due_day']<=31:raise ValueError('Fechamento e vencimento precisam estar entre 1 e 31.')
        if data['limit_amount']<=0:raise ValueError('O limite precisa ser positivo.')
        if data.get('payment_account') and not self.s.rows("SELECT id FROM accounts WHERE name=? AND currency='BRL'",(data['payment_account'],)):raise ValueError('Selecione uma conta em reais para pagamento.')
        keys=['name','institution','limit_amount','closing_day','due_day','payment_account','color'];args=[data.get(k,'') for k in keys]
        with self.s.db:
            if ident:self.s.db.execute('UPDATE cards SET '+','.join(k+'=?' for k in keys)+' WHERE id=?',args+[ident]);return ident
            return self.s.db.execute('INSERT INTO cards ('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',args).lastrowid
    def invoice_period(self,card,purchase_day):
        d=date.fromisoformat(purchase_day);closing=d.strftime('%Y-%m')
        if d.isoformat()>=month_day(closing,card['closing_day']):closing=add_month(closing)
        return add_month(closing) if card['due_day']<=card['closing_day'] else closing
    def add_purchase(self,card_id,description,amount,purchase_day,category,installments=1,first_period=None,note=''):
        cards=self.s.rows('SELECT * FROM cards WHERE id=? AND archived=0',(card_id,))
        if not cards:raise ValueError('Cartão não encontrado ou arquivado.')
        date.fromisoformat(purchase_day)
        if not description.strip() or amount<=0:raise ValueError('Descrição e valor total positivo são obrigatórios.')
        if not 1<=installments<=120 or amount<installments:raise ValueError('Use de 1 a 120 parcelas, com pelo menos um centavo por parcela.')
        first=first_period or self.invoice_period(cards[0],purchase_day);check_period(first)
        batch=uuid.uuid4().hex;part,remainder=divmod(amount,installments)
        with self.s.db:
            for index in range(installments):self.s.db.execute('INSERT INTO card_items(card_id,purchase_day,period,description,category,amount,installment,installments,batch_key,note) VALUES (?,?,?,?,?,?,?,?,?,?)',(card_id,purchase_day,add_month(first,index),description.strip(),category,part+(index<remainder),index+1,installments,batch,note))
        return batch
    def invoice(self,card_id,period):
        card=self.s.rows('SELECT * FROM cards WHERE id=?',(card_id,))[0]
        total=self.s.rows('SELECT COALESCE(SUM(amount),0) n FROM card_items WHERE card_id=? AND period=?',(card_id,period))[0]['n'];paid=self.s.rows('SELECT COALESCE(SUM(amount),0) n FROM card_payments WHERE card_id=? AND period=?',(card_id,period))[0]['n']
        return dict(total=total,paid=paid,remaining=total-paid,due_day=month_day(period,card['due_day']),closing_day=month_day(add_month(period,-1) if card['due_day']<=card['closing_day'] else period,card['closing_day']))
    def outstanding(self,card_id=None):
        args=(card_id,) if card_id else ();suffix=' WHERE card_id=?' if card_id else ''
        total=self.s.rows('SELECT COALESCE(SUM(amount),0) n FROM card_items'+suffix,args)[0]['n'];paid=self.s.rows('SELECT COALESCE(SUM(amount),0) n FROM card_payments'+suffix,args)[0]['n'];return total-paid
    def pay_invoice(self,card_id,period,amount,day,account):
        date.fromisoformat(day);check_period(period)
        if amount<=0 or amount>self.invoice(card_id,period)['remaining']:raise ValueError('O pagamento deve ser positivo e não pode superar o saldo da fatura.')
        if not self.s.rows("SELECT id FROM accounts WHERE name=? AND currency='BRL'",(account,)):raise ValueError('Cadastre ou selecione uma conta em reais.')
        card=self.s.rows('SELECT * FROM cards WHERE id=?',(card_id,))[0]
        with self.s.db:
            tx=self.s.db.execute("INSERT INTO tx(period,day,description,kind,category,amount,account,status,note,invoice_card_id,invoice_period) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(day[:7],day,'Pagamento de fatura • '+card['name'],'Pagamento de fatura','Faturas a detalhar',amount,account,'Confirmado','Registro local de pagamento. Não movimenta o banco real.',card_id,period)).lastrowid
            self.s.db.execute('INSERT INTO card_payments(card_id,period,day,amount,account,tx_id) VALUES (?,?,?,?,?,?)',(card_id,period,day,amount,account,tx))
        return tx
    def delete_payment(self,tx_id):
        with self.s.db:self.s.db.execute('DELETE FROM card_payments WHERE tx_id=?',(tx_id,));self.s.db.execute('DELETE FROM tx WHERE id=?',(tx_id,))
    def delete_purchase(self,batch):
        rows=self.s.rows('SELECT DISTINCT card_id,period FROM card_items WHERE batch_key=?',(batch,))
        if any(self.invoice(r['card_id'],r['period'])['paid']>0 for r in rows):raise ValueError('A compra participa de fatura com pagamento registrado. Desfaça o registro de pagamento antes de excluir a compra.')
        with self.s.db:self.s.db.execute('DELETE FROM card_items WHERE batch_key=?',(batch,))
    def due(self,today=None):
        today=today or date.today();items=[]
        for row in self.s.rows("SELECT * FROM tx WHERE status='Previsto' AND kind!='Transferência' ORDER BY COALESCE(due_day,day,period)"):
            deadline=row['due_day'] or row['day'] or row['period']+'-01';items.append(dict(type='tx',id=row['id'],description=row['description'],kind=row['kind'],day=deadline,amount=row['amount'],account=row['account'],status='Atrasado' if deadline<today.isoformat() else 'Hoje' if deadline==today.isoformat() else 'A vencer'))
        for row in self.s.rows('SELECT DISTINCT card_id,period FROM card_items ORDER BY period'):
            inv=self.invoice(row['card_id'],row['period'])
            if inv['remaining']>0:
                card=self.s.rows('SELECT * FROM cards WHERE id=?',(row['card_id'],))[0];deadline=inv['due_day'];items.append(dict(type='card',id=row['card_id'],period=row['period'],description='Fatura '+card['name'],kind='Cartão',day=deadline,amount=inv['remaining'],account=card['payment_account'],status='Atrasado' if deadline<today.isoformat() else 'Hoje' if deadline==today.isoformat() else 'A vencer'))
        return sorted(items,key=lambda x:x['day'])
    def confirm_tx(self,ident,day=None):
        row=self.s.rows('SELECT * FROM tx WHERE id=?',(ident,))
        if not row or row[0]['amount'] is None:raise ValueError('Preencha o valor antes de confirmar.')
        if row[0]['status']=='Confirmado':return
        when=day or (row[0]['day'] if row[0]['status']=='A revisar' and row[0]['day'] else date.today().isoformat());date.fromisoformat(when)
        with self.s.db:self.s.db.execute("UPDATE tx SET status='Confirmado',day=? WHERE id=?",(when,ident))
    def copy_budgets(self,source,target):
        check_period(source);check_period(target)
        if source==target:raise ValueError('Escolha meses diferentes.')
        with self.s.db:
            self.s.db.execute('INSERT OR REPLACE INTO budgets(category,period,amount) SELECT category,?,amount FROM budgets WHERE period=?',(target,source))
    def attach(self,tx_id,path):
        p=Path(path);data=p.read_bytes()
        if len(data)>10*1024*1024:raise ValueError('Limite de 10 MB por comprovante.')
        mime='application/pdf' if data.startswith(b'%PDF') else 'image/png' if data.startswith(b'\x89PNG') else 'image/jpeg' if data.startswith(b'\xff\xd8\xff') else None
        if not mime:raise ValueError('Use um arquivo PDF, PNG ou JPEG válido.')
        if not self.s.rows('SELECT id FROM tx WHERE id=?',(tx_id,)):raise ValueError('Lançamento não encontrado.')
        with self.s.db:self.s.db.execute('INSERT INTO attachments(tx_id,name,mime,data) VALUES (?,?,?,?)',(tx_id,p.name,mime,data))
    def parse_statement(self,path):
        p=Path(path)
        if p.stat().st_size>8*1024*1024:raise ValueError('Extrato acima de 8 MB. Divida o arquivo antes de importar.')
        raw=p.read_bytes()
        try:text=raw.decode('utf-8-sig')
        except UnicodeDecodeError:text=raw.decode('cp1252')
        result=[]
        if p.suffix.lower()=='.ofx':
            currency=re.search(r'<CURDEF>\s*([^<\r\n]+)',text,re.I)
            if currency and currency.group(1).strip().upper()!='BRL':raise ValueError('Nesta versão, a conciliação aceita extratos em BRL.')
            for block in re.findall(r'<STMTTRN>(.*?)</STMTTRN>',text,re.I|re.S):
                def tag(name):
                    m=re.search('<'+name+r'>\s*([^<\r\n]*)',block,re.I);return html.unescape(m.group(1).strip()) if m else ''
                day=datetime.strptime(tag('DTPOSTED')[:8],'%Y%m%d').date().isoformat();signed=cents(tag('TRNAMT'));description=tag('MEMO') or tag('NAME') or 'Movimentação do extrato';fit=tag('FITID')
                result.append(dict(day=day,description=description,kind='Receita' if signed>=0 else 'Despesa',amount=abs(signed),external_id=fit or hashlib.sha256((day+description+str(signed)).encode()).hexdigest(),category='Outros'))
        elif p.suffix.lower()=='.csv':
            import io,unicodedata
            def key(s):return ''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if not unicodedata.combining(c)).strip()
            sample=text[:4096]
            try:dialect=csv.Sniffer().sniff(sample,delimiters=';,\t')
            except csv.Error:dialect=csv.excel;dialect.delimiter=';'
            for row in csv.DictReader(io.StringIO(text),dialect=dialect):
                row={key(k):v for k,v in row.items() if k};day=row.get('data','').strip();description=row.get('descricao',row.get('description','')).strip();value=row.get('valor',row.get('valor brl','')).strip();kind=row.get('tipo','').strip()
                if not day or not description or not value:raise ValueError('CSV precisa de Data, Descrição e Valor preenchidos em todas as linhas.')
                if re.fullmatch(r'\d{2}/\d{2}/\d{4}',day):day=datetime.strptime(day,'%d/%m/%Y').date().isoformat()
                date.fromisoformat(day);signed=cents(value)
                if kind and kind not in ['Receita','Despesa','Aporte','Resgate']:raise ValueError('CSV: transferências e pagamentos de cartão exigem conferência manual; importe somente receitas, despesas, aportes e resgates.')
                kind=kind or ('Receita' if signed>=0 else 'Despesa');external=row.get('id','') or hashlib.sha256((day+description+kind+str(signed)).encode()).hexdigest();result.append(dict(day=day,description=description,kind=kind,amount=abs(signed),external_id=external,category=row.get('categoria','Outros') or 'Outros'))
        else:raise ValueError('Escolha um arquivo CSV ou OFX.')
        if not result:raise ValueError('Nenhuma movimentação reconhecida.')
        if len(result)>4000:raise ValueError('Limite de 4.000 linhas por importação.')
        return result
    def preview_statement(self,path,account):
        account_rows=self.s.rows("SELECT id FROM accounts WHERE name=? AND currency='BRL'",(account,))
        if not account_rows:raise ValueError('Selecione uma conta em reais.')
        account_id=account_rows[0]['id'];result=self.parse_statement(path);seen=set()
        for row in result:
            key='statement:'+str(account_id)+':'+row['external_id'];row['source_key']=key;row['account']=account;row['duplicate']=bool(self.s.rows('SELECT id FROM tx WHERE source_key=?',(key,))) or key in seen;seen.add(key)
            candidates=self.s.rows("SELECT id FROM tx WHERE account=? AND day=? AND kind=? AND amount=? AND source_key IS NULL",(account,row['day'],row['kind'],row['amount']));row['match_id']=candidates[0]['id'] if len(candidates)==1 else None
        return result
    def import_statement(self,rows,selected,reconcile=False):
        count=matched=0
        with self.s.db:
            for i in selected:
                row=rows[i]
                if row['duplicate'] or self.s.rows('SELECT id FROM tx WHERE source_key=?',(row['source_key'],)):continue
                if row['match_id']:
                    if not reconcile:continue
                    exists=self.s.rows('SELECT source_key,day,kind,amount,account FROM tx WHERE id=?',(row['match_id'],))
                    if not exists or exists[0]['source_key'] or any(exists[0][k]!=row[k] for k in ['day','kind','amount','account']):raise ValueError('Um candidato mudou durante a conferência. Reabra a prévia.')
                    self.s.db.execute("UPDATE tx SET source_key=?,status='Confirmado' WHERE id=?",(row['source_key'],row['match_id']));matched+=1
                else:
                    self.s.db.execute("INSERT INTO tx(period,day,description,kind,category,amount,account,status,source,source_key) VALUES (?,?,?,?,?,?,?,?,?,?)",(row['day'][:7],row['day'],row['description'],row['kind'],row['category'],row['amount'],row['account'],'Confirmado','Extrato importado e conferido',row['source_key']));count+=1
        return count,matched
    def restore_backup(self,path):
        import sqlite3
        from core import Store
        path=Path(path)
        if path.resolve()==self.s.path.resolve():raise ValueError('Escolha uma cópia diferente do banco em uso.')
        source=sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True);candidate=self.s.path.parent/('restore-'+uuid.uuid4().hex+'.sqlite')
        try:
            if source.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup corrompido.')
            required={'tx','settings','goals','positions','budgets','snapshots','imports','accounts'};found={r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not required<=found or not source.execute('SELECT 1 FROM goals').fetchone():raise ValueError('Este arquivo não é um backup compatível do Horizonte.')
            version=source.execute("SELECT value FROM settings WHERE key='schema-version'").fetchone()
            if version and int(version[0])>3:raise ValueError('Backup de uma versão mais nova. Atualize o aplicativo primeiro.')
            tmp=sqlite3.connect(candidate)
            try:source.backup(tmp)
            finally:tmp.close()
            upgraded=Store(candidate)
            try:
                previous=self.s.path.parent/('antes-restauracao-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.sqlite');self.s.backup(previous);upgraded.db.backup(self.s.db)
            finally:upgraded.db.close()
            return previous
        finally:
            source.close()
            if candidate.exists():candidate.unlink()
    
