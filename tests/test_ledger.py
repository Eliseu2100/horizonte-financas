import sys,unittest,tempfile,sqlite3
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from core import Store
from ledger import Ledger,add_month
class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'financas.sqlite';self.s=Store(self.path);self.l=Ledger(self.s)
        self.s.db.execute('INSERT INTO accounts(name,institution,currency,balance,fx_rate,day,ledger_after,note) VALUES (?,?,?,?,?,?,?,?)',('Conta','Banco fictício','BRL',200000,1,'2026-01-01',0,''));self.s.db.commit()
        self.card=self.l.save_card(dict(name='Cartão teste',institution='Banco fictício',limit_amount=100000,closing_day=20,due_day=28,payment_account='Conta',color='#007AFF'))
    def tearDown(self):self.s.db.close();self.temp.cleanup()
    def test_installment_rounding_cycles_and_periods(self):
        self.l.add_purchase(self.card,'Compra',10000,'2026-01-05','Compras',3)
        items=self.s.rows('SELECT * FROM card_items ORDER BY period');self.assertEqual([x['amount'] for x in items],[3334,3333,3333]);self.assertEqual(sum(x['amount'] for x in items),10000);self.assertIn('2026-03',self.s.periods())
        card=self.s.rows('SELECT * FROM cards')[0];card['closing_day']=25;card['due_day']=5
        self.assertEqual(self.l.invoice_period(card,'2026-01-24'),'2026-02');self.assertEqual(self.l.invoice_period(card,'2026-01-25'),'2026-03')
        card['closing_day']=31;self.assertEqual(self.l.invoice_period(card,'2028-02-29'),'2028-04')
    def test_card_payment_does_not_duplicate_consumption(self):
        batch=self.l.add_purchase(self.card,'Compra',60000,'2026-01-05','Compras',3);a=self.s.rows('SELECT * FROM accounts')[0]
        net_before=self.s.account_balance(a)-self.l.outstanding();self.assertEqual(self.s.summary('2026-01')['Despesa'],20000)
        tx=self.l.pay_invoice(self.card,'2026-01',10000,'2026-01-10','Conta');net_after=self.s.account_balance(a)-self.l.outstanding();self.assertEqual(net_before,net_after);self.assertEqual(self.s.summary('2026-01')['Despesa'],20000);self.assertEqual(self.s.summary('2026-01')['livre'],-10000);self.assertEqual(self.l.invoice(self.card,'2026-01')['remaining'],10000)
        with self.assertRaises(ValueError):self.l.pay_invoice(self.card,'2026-01',10001,'2026-01-10','Conta')
        with self.assertRaises(ValueError):self.l.delete_purchase(batch)
        self.l.delete_payment(tx);self.assertEqual(self.s.account_balance(a),200000);self.l.delete_purchase(batch);self.assertEqual(self.l.outstanding(),0)
    def test_custom_category_history_and_restart(self):
        self.l.save_category('Mercado','Alimentação');self.l.add_purchase(self.card,'Compra',12000,'2026-01-05','Mercado');self.s.db.execute('INSERT INTO budgets VALUES (?,?,?)',('Mercado','2026-01',15000));self.s.db.commit();self.l.save_category('Supermercado','Alimentação',old='Mercado');self.assertEqual(self.l.category_spend('2026-01')['Supermercado'],12000);self.l.copy_budgets('2026-01','2026-02');self.assertEqual(self.s.rows("SELECT amount FROM budgets WHERE period='2026-02'")[0]['amount'],15000)
        self.l.save_category('Passeios',old='Lazer');self.s.db.close();self.s=Store(self.path);self.assertFalse(self.s.rows("SELECT 1 FROM categories WHERE name='Lazer'"))
    def test_csv_preview_duplicate_and_reconcile(self):
        path=Path(self.temp.name)/'extrato.csv';path.write_text('Data;Descrição;Valor\n05/01/2026;Mercado;-50,00\n06/01/2026;Salário;2000,00\n',encoding='utf-8')
        rows=self.l.preview_statement(path,'Conta');self.assertEqual(self.l.import_statement(rows,[0,1]),(2,0));self.assertTrue(all(r['duplicate'] for r in self.l.preview_statement(path,'Conta')))
        self.s.db.execute("UPDATE accounts SET name='Conta nova' WHERE name='Conta'");self.s.db.execute("UPDATE tx SET account='Conta nova' WHERE account='Conta'");self.s.db.commit();self.assertTrue(all(r['duplicate'] for r in self.l.preview_statement(path,'Conta nova')))
    def test_ofx_and_manual_match(self):
        path=Path(self.temp.name)/'extrato.ofx';path.write_text('<OFX><CURDEF>BRL<STMTTRN><DTPOSTED>20260105<TRNAMT>-50.00<FITID>one<MEMO>Mercado &amp; Cia</STMTTRN></OFX>')
        self.s.save_tx(dict(period='2026-01',day='2026-01-05',description='Mercado manual',kind='Despesa',category='Alimentação',amount=5000,account='Conta',status='A revisar',note=''))
        rows=self.l.preview_statement(path,'Conta');self.assertIsNotNone(rows[0]['match_id']);self.assertEqual(rows[0]['description'],'Mercado & Cia');self.assertEqual(self.l.import_statement(rows,[0],reconcile=True),(0,1));self.assertEqual(len(self.s.rows('SELECT * FROM tx')),1)
    def test_agenda_confirmation_and_backup_attachments(self):
        self.s.save_tx(dict(period='2026-01',day='2026-01-05',due_day='2026-01-05',description='Conta',kind='Despesa',category='Outros',amount=1000,account='Conta',status='Previsto',note=''))
        tx=self.s.rows('SELECT * FROM tx')[0];self.assertEqual(self.l.due(date(2026,1,6))[0]['status'],'Atrasado');self.l.confirm_tx(tx['id'],'2026-01-06');self.assertEqual(self.l.due(),[])
        receipt=Path(self.temp.name)/'receipt.pdf';receipt.write_bytes(b'%PDF-1.4\nArquivo sintetico');self.l.attach(tx['id'],receipt);backup=self.s.daily_backup();copy=Store(backup)
        try:self.assertEqual(copy.rows('SELECT name FROM attachments')[0]['name'],'receipt.pdf')
        finally:copy.db.close()
    def test_old_backup_migration_preserves_values(self):
        old=Path(self.temp.name)/'old.sqlite';db=sqlite3.connect(old)
        db.executescript('''CREATE TABLE tx(id INTEGER PRIMARY KEY,period TEXT,day TEXT,description TEXT,kind TEXT,category TEXT,amount INTEGER,account TEXT,status TEXT,source TEXT,source_key TEXT UNIQUE,note TEXT);CREATE TABLE snapshots(id INTEGER PRIMARY KEY,period TEXT,day TEXT,name TEXT,group_name TEXT,amount INTEGER,source TEXT,source_key TEXT UNIQUE);CREATE TABLE positions(id INTEGER PRIMARY KEY,name TEXT,institution TEXT,asset_type TEXT,principal INTEGER,value INTEGER,day TEXT,maturity TEXT,note TEXT);CREATE TABLE budgets(category TEXT,period TEXT,amount INTEGER,PRIMARY KEY(category,period));CREATE TABLE goals(id INTEGER PRIMARY KEY,name TEXT,target INTEGER,saved INTEGER,deadline TEXT,contribution INTEGER,annual REAL);CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);CREATE TABLE imports(hash TEXT PRIMARY KEY,name TEXT,stamp TEXT,report TEXT);CREATE TABLE accounts(id INTEGER PRIMARY KEY,name TEXT UNIQUE,institution TEXT,currency TEXT,balance INTEGER,fx_rate REAL,day TEXT,ledger_after INTEGER,note TEXT);''')
        db.execute("INSERT INTO goals VALUES (1,'Meta teste',100000,20000,'2030-03-01',1000,0)");db.execute("INSERT INTO settings VALUES ('display-name','Perfil de teste')");db.execute("INSERT INTO settings VALUES ('profile-photo','imagem-ficticia')");db.commit();db.close()
        self.l.restore_backup(old);self.assertEqual(self.s.setting('schema-version'),'3');self.assertEqual(self.s.setting('profile-photo'),'imagem-ficticia');self.assertEqual(self.s.rows('SELECT saved FROM goals')[0]['saved'],20000);self.assertTrue(list((Path(self.temp.name)/'backups').glob('antes-atualizacao-0.3-*.sqlite')))
        original=sqlite3.connect(old);self.assertIsNone(original.execute("SELECT value FROM settings WHERE key='schema-version'").fetchone());original.close()
if __name__=='__main__':unittest.main()
    
