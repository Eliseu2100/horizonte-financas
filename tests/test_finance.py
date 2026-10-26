import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from core import Store,cents,forecast
from finance import position_projection,insights,goal_assessment
from demo import seed_demo
from openpyxl import Workbook
class FinanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'test.sqlite')
    def tearDown(self):self.store.db.close();self.tmp.cleanup()
    def test_cents_and_growth(self):
        self.assertEqual(cents('1.234,56'),123456)
        self.assertEqual(forecast(10000,1000,0,12)[-1],22000)
        self.assertAlmostEqual(forecast(100000,0,12,12)[-1],112000,delta=1)
        with self.assertRaises(ValueError):cents('NaN')
    def test_synthetic_import(self):
        book=Workbook();sheet=book.active;sheet.title='JANEIRO 2026'
        from datetime import datetime
        for row in [('ENTRADAS',),('Data',None,'Conta','Valor'),(datetime(2026,1,1),'CONTA','Conta fictícia',100),(datetime(2026,1,5),None,'Salario',2000),('TOTAL DE ENTRADAS',None,2100),('SAIDAS',),('DESCRIÇÃO',None,'VALOR'),('Entrega de compras',None,50),('SOFISA 08/01',None,100),('Sem valor',None,None),('TOTAL DE SAIDAS',None,150)]:sheet.append(row)
        path=Path(self.tmp.name)/'source.xlsx';book.save(path);self.store.import_excel(path);self.store.import_excel(path)
        self.assertEqual(len(self.store.rows('SELECT * FROM tx')),4)
        s=self.store.summary('2026-01');self.assertEqual(s['Receita'],200000);self.assertEqual(s['Despesa'],5000);self.assertEqual(s['Aporte'],10000)
    def test_planned_does_not_inflate_actual(self):
        tx=dict(period='2026-01',day='2026-01-05',description='Teste',kind='Receita',category='Outros',amount=100000,account='Exemplo',status='Previsto',note='')
        self.store.save_tx(tx);self.assertEqual(self.store.summary('2026-01')['Receita'],0)
    def test_fixed_rate_and_liquidity(self):
        p=dict(name='Exemplo',day='2026-01-01',maturity='2027-01-01',value=100000,principal=100000,rate_mode='Prefixado % a.a.',rate=10,tax=15,liquidity='No vencimento',asset_type='CDB')
        r=position_projection(p,'2027-01-01');self.assertEqual(r['net'],108500);self.assertTrue(r['available'])
        self.assertFalse(position_projection(p,'2026-05-01')['available'])
        self.assertEqual(position_projection(p,'2029-01-01')['net'],108500)
    def test_demo_and_insights(self):
        seed_demo(self.store);count=len(self.store.rows('SELECT * FROM tx'));seed_demo(self.store);self.assertEqual(len(self.store.rows('SELECT * FROM tx')),count)
        from datetime import date
        p=date.today().strftime('%Y-%m');self.assertTrue(insights(self.store,p));g=self.store.rows('SELECT * FROM goals')[0];self.assertTrue(goal_assessment(self.store,g,p)['linked'])
    def test_accounts_transfer_and_daily_backup(self):
        from datetime import date
        day=date.today().isoformat();period=day[:7]
        for name,value in [('Origem',100000),('Destino',0)]:self.store.db.execute('INSERT INTO accounts(name,institution,currency,balance,fx_rate,day,ledger_after,note) VALUES (?,?,?,?,?,?,?,?)',(name,'Banco fictício','BRL',value,1,day,0,''))
        self.store.db.commit()
        self.store.save_tx(dict(period=period,day=day,description='Transferência teste',kind='Transferência',category='Outros',amount=25000,account='Origem',target_account='Destino',status='Confirmado',note=''))
        accounts=self.store.rows('SELECT * FROM accounts ORDER BY id');self.assertEqual(self.store.account_balance(accounts[0]),75000);self.assertEqual(self.store.account_balance(accounts[1]),25000);self.assertEqual(self.store.summary(period)['livre'],0)
        self.store.set('profile-photo','base64-ficticio');backup=self.store.daily_backup();other=Store(backup)
        self.assertEqual(other.setting('profile-photo'),'base64-ficticio');self.assertEqual(len(other.rows('SELECT * FROM accounts')),2);other.db.close()
    def test_backup(self):
        target=Path(self.tmp.name)/'copy.sqlite';self.store.backup(target);other=Store(target);self.assertEqual(len(other.rows('SELECT * FROM goals')),1);other.db.close()
if __name__=='__main__':unittest.main()
