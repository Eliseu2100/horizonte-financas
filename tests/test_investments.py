import os,sys,tempfile,unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from core import Store
from investments import InvestmentBook
from diagnostics import run_diagnostics

class InvestmentHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.s=Store(Path(self.temp.name)/'db.sqlite');self.s.db.execute("INSERT INTO accounts(name,institution,currency,balance,fx_rate,day,ledger_after) VALUES('Conta','Banco','BRL',2000000,1,'2026-01-01',0)");self.s.db.execute("INSERT INTO positions(name,institution,asset_type,principal,value,day,maturity,note,rate_mode,rate,tax,liquidity,currency,fx_rate,native_value) VALUES('CDB de teste','Banco','CDB',1000000,1000000,'2026-01-01','','','Prefixado % a.a.',12,0,'Diária','BRL',1,1000000)");self.s.db.commit();self.book=InvestmentBook(self.s);self.ident=self.s.rows('SELECT id FROM positions')[0]['id']
    def tearDown(self):self.s.db.close();self.temp.cleanup()
    def test_monthly_flow_and_market_change_are_separate(self):
        self.book.save_value(self.ident,'2026-01-31',1000000);self.book.add_event(self.ident,'2026-02-05','Aporte',100000,account='Conta');self.book.save_value(self.ident,'2026-02-28',1125000)
        row=self.book.monthly('2026-02',self.ident)[0];self.assertEqual((row['opening'],row['contribution'],row['closing'],row['gain']),(1000000,100000,1125000,25000));self.assertEqual(self.s.summary('2026-02')['Aporte'],100000);self.assertEqual(self.s.summary('2026-02')['Despesa'],0)
    def test_same_day_checkpoint_does_not_duplicate_contribution(self):
        self.book.save_value(self.ident,'2026-02-01',1000000);self.book.add_event(self.ident,'2026-02-01','Aporte',100000,account='Conta');self.assertEqual(self.book.state(self.ident,'2026-02-01')['value'],1100000);self.book.save_value(self.ident,'2026-02-01',1105000);self.assertEqual(self.book.state(self.ident,'2026-02-01')['value'],1105000)
    def test_existing_transaction_can_be_linked_without_duplicate_cash_or_balance(self):
        self.book.save_value(self.ident,'2026-02-01',1000000);self.book.add_event(self.ident,'2026-02-01','Aporte',50000,account='Conta');self.s.save_tx(dict(period='2026-02',day='2026-02-01',description='Aporte que já estava no extrato',kind='Aporte',category='Investimentos',amount=100000,account='Conta',status='Confirmado',note=''));tx=self.s.rows('SELECT MAX(id) n FROM tx')[0]['n'];count=len(self.s.rows('SELECT * FROM tx'));self.book.add_event(self.ident,'2026-02-01','Aporte',100000,tx_id=tx,included_in_balance=True);self.assertEqual(len(self.s.rows('SELECT * FROM tx')),count);self.assertEqual(self.book.state(self.ident,'2026-02-01')['value'],1050000);self.book.delete_latest_event(self.ident);self.assertTrue(self.s.rows('SELECT * FROM tx WHERE id=?',(tx,)))
    def test_estimate_is_distinct_and_does_not_write_new_quote(self):
        before=len(self.s.rows('SELECT * FROM investment_values'));recorded=self.book.state(self.ident,'2026-02-01');estimated=self.book.state(self.ident,'2026-02-01',True);self.assertEqual(recorded['value'],1000000);self.assertGreater(estimated['value'],recorded['value']);self.assertTrue(estimated['estimated']);self.assertEqual(len(self.s.rows('SELECT * FROM investment_values')),before);self.assertIsNone(self.book.monthly('2026-02',self.ident)[0]['gain'])
    def test_no_history_is_not_backfilled_with_current_balance(self):
        self.assertIsNone(self.book.state(self.ident,'2025-12-31'));self.assertIsNone(self.book.monthly('2025-12',self.ident)[0]['closing'])
    def test_undo_owned_transaction_restores_cash(self):
        account=self.s.rows('SELECT * FROM accounts')[0];before=self.s.account_balance(account);self.book.add_event(self.ident,'2026-02-01','Aporte',50000,account='Conta');self.assertEqual(self.s.account_balance(account),before-50000);self.book.delete_latest_event(self.ident);self.assertEqual(self.s.account_balance(account),before)
    def test_unsafe_withdrawal_future_value_and_invalid_link_do_not_mutate(self):
        before=len(self.s.rows('SELECT * FROM investment_events'))
        with self.assertRaises(ValueError):self.book.add_event(self.ident,'2026-02-01','Resgate',999999999,account='Conta')
        with self.assertRaises(ValueError):self.book.save_value(self.ident,'2199-01-01',1)
        with self.assertRaises(ValueError):self.book.add_event(self.ident,'2026-02-01','Aporte',1000,tx_id=999)
        self.assertEqual(len(self.s.rows('SELECT * FROM investment_events')),before)
    def test_backup_preserves_history_and_diagnostics_detect_corrupted_link(self):
        self.book.add_event(self.ident,'2026-02-01','Aporte',1000,account='Conta');self.assertTrue(run_diagnostics(self.s)['passed']);dest=Path(self.temp.name)/'copy.sqlite';self.s.backup(dest);copy=Store(dest);self.assertEqual(len(copy.rows('SELECT * FROM investment_events')),1);copy.db.close();self.s.db.execute('UPDATE tx SET amount=amount+1');self.s.db.commit();self.assertFalse(run_diagnostics(self.s)['passed'])
    def test_projection_includes_growth_before_a_later_contribution(self):
        self.book.add_event(self.ident,'2026-02-01','Aporte',100000,account='Conta')
        from finance import investment_projection
        result=investment_projection(self.s,self.book.position(self.ident),'2026-02-01')
        self.assertGreater(result['gross'],1109000)
        self.assertLess(result['gross'],1111000)
    def test_foreign_currency_uses_last_quote_until_new_confirmation(self):
        self.s.db.execute("INSERT INTO positions(name,institution,asset_type,value,day,currency,fx_rate,native_value,note) VALUES('USD','Banco','Moeda estrangeira',50000,'2026-01-01','USD',5,10000,'')");self.s.db.commit();book=InvestmentBook(self.s);ident=self.s.rows("SELECT id FROM positions WHERE name='USD'")[0]['id'];book.save_value(ident,'2026-01-31',10000,5);book.add_event(ident,'2026-02-01','Aporte',5000,6,account='Conta');state=book.state(ident,'2026-02-01');self.assertEqual((state['value'],state['native_value']),(75000,15000));book.save_value(ident,'2026-02-28',15000,6);self.assertEqual(book.monthly('2026-02',ident)[0]['gain'],10000)
if __name__=='__main__':unittest.main()
  
