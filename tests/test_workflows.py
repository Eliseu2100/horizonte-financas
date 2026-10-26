import os,sys,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from PySide6.QtCore import Qt,QEvent,QTimer,QDate
from PySide6.QtWidgets import QApplication,QPushButton,QDialog,QMessageBox,QTableWidget,QDialogButtonBox
from PySide6.QtTest import QTest
from core import Store
from demo import seed_demo
from workspace import ModernWindow,SmartForm
from widgets import ResponsiveCards
from investments import InvestmentBook

class WorkflowDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.s=Store(Path(self.temp.name)/'db.sqlite');seed_demo(self.s);self.w=ModernWindow(self.s);self.w.show();self.app.processEvents();self.errors=[];self.hook=sys.excepthook;sys.excepthook=lambda *args:self.errors.append(str(args[1]))
    def tearDown(self):
        self.w.close();self.w.deleteLater();self.app.sendPostedEvents(None,QEvent.DeferredDelete);self.app.processEvents();sys.excepthook=self.hook;self.temp.cleanup();self.assertEqual(self.errors,[])
    def modal(self,fn):
        def run():
            d=self.app.activeModalWidget()
            try:fn(d)
            except Exception as e:
                self.errors.append(str(e))
                if d:d.reject()
        QTimer.singleShot(40,run)
    def click(self,text):
        b=next(b for b in self.w.scroll.widget().findChildren(QPushButton) if b.text()==text);self.w.scroll.ensureWidgetVisible(b);QTest.mouseClick(b,Qt.LeftButton);self.app.processEvents()
    def test_every_visible_page_button_routes_without_exception(self):
        from PySide6.QtCore import SIGNAL
        inventory=[]
        with patch('workspace.QDialog.exec',return_value=0),patch('workspace.QFileDialog.getOpenFileName',return_value=('','')),patch('workspace.QFileDialog.getSaveFileName',return_value=('','')),patch('workspace.QFileDialog.getExistingDirectory',return_value=''),patch('workspace.QMessageBox.question',return_value=QMessageBox.No),patch('workspace.QMessageBox.information'),patch('workspace.QMessageBox.warning'),patch('app.FXWorker.start',lambda worker:worker.done.emit({'rate':30,'date':'2026-10-01'})):
            for page in list(self.w.nav):
                self.w.go(page);self.app.processEvents();names=[b.text() for b in self.w.scroll.widget().findChildren(QPushButton) if b.isEnabled()]
                for text in dict.fromkeys(names):
                    self.w.go(page);self.app.processEvents()
                    for table in self.w.scroll.widget().findChildren(QTableWidget):
                        if table.rowCount():table.selectRow(0)
                    matches=[b for b in self.w.scroll.widget().findChildren(QPushButton) if b.text()==text and b.isEnabled()]
                    if not matches:continue
                    b=matches[0];self.assertGreater(b.receivers(SIGNAL('clicked(bool)')),0,(page,text));self.w.scroll.ensureWidgetVisible(b);QTest.mouseClick(b,Qt.LeftButton);self.app.processEvents();inventory.append((page,text))
        self.assertGreaterEqual(len(inventory),50);self.assertEqual(self.errors,[])
        print('DIAGNOSTIC_BUTTON_ROUTES='+str(len(inventory)))
    def test_asset_contribution_balance_history_and_cash_through_forms(self):
        self.w.go('Investimentos');self.w.position_table.selectRow(0);p=self.w.positions[0];book=InvestmentBook(self.s);before=book.state(p['id'],QDate.currentDate().toString('yyyy-MM-dd'))['value']
        def movement(d):
            self.assertIsInstance(d,SmartForm);d.inputs['day'].set_iso(QDate.currentDate().toString('yyyy-MM-dd'));d.inputs['amount'].setText('250,00');d.inputs['account'].setCurrentIndex(1);d.accept()
        self.modal(movement);self.click('Registrar aporte / resgate');self.assertEqual(book.state(p['id'],QDate.currentDate().toString('yyyy-MM-dd'))['value'],before+25000)
        def balance(d):d.inputs['amount'].setText(str((before+27500)/100).replace('.',','));d.accept()
        self.modal(balance);self.click('Atualizar saldo');self.assertEqual(book.state(p['id'],QDate.currentDate().toString('yyyy-MM-dd'))['value'],before+27500)
        def history(d):self.assertIn('Histórico',d.windowTitle());self.assertGreater(len(d.findChildren(QTableWidget)),2);d.accept()
        self.modal(history);self.click('Histórico mensal')
    def test_categories_cards_purchases_payments_and_goal_forms(self):
        self.w.go('Categorias')
        def cat(d):d.inputs['name'].setText('Categoria do diagnóstico');d.accept()
        self.modal(cat);self.click('+ Categoria');self.assertTrue(self.s.rows("SELECT 1 FROM categories WHERE name='Categoria do diagnóstico'"))
        self.w.go('Cartões')
        def card(d):d.inputs['name'].setText('Cartão do diagnóstico');d.inputs['institution'].setText('Banco teste');d.inputs['limit_amount'].setText('5000');d.inputs['payment_account'].setCurrentIndex(1);d.accept()
        self.modal(card);self.click('+ Cartão');card_id=self.s.rows("SELECT id FROM cards WHERE name='Cartão do diagnóstico'")[0]['id'];self.w.selected_card=card_id;self.w.render()
        def purchase(d):d.inputs['description'].setText('Compra de diagnóstico');d.inputs['amount'].setText('120,00');d.inputs['first_period'].setText(self.w.p);d.accept()
        self.modal(purchase);self.click('+ Compra no cartão');self.assertEqual(self.s.rows('SELECT SUM(amount) n FROM card_items WHERE card_id=?',(card_id,))[0]['n'],12000)
        def pay(d):d.accept()
        self.modal(pay);self.click('Registrar pagamento');self.assertTrue(self.s.rows('SELECT 1 FROM card_payments WHERE card_id=?',(card_id,)))
        self.w.go('Metas e câmbio')
        def goal(d):d.inputs['name'].setText('Meta do diagnóstico');d.inputs['target'].setText('1000');d.inputs['saved'].setText('0');d.accept()
        self.modal(goal);self.click('+ Nova meta');self.assertTrue(self.s.rows("SELECT 1 FROM goals WHERE name='Meta do diagnóstico'"))
    def test_responsive_metrics_and_privacy(self):
        self.w.go('Visão geral');self.w.resize(1000,680);self.app.processEvents();grids=self.w.scroll.widget().findChildren(ResponsiveCards);self.assertTrue(grids);self.assertEqual(grids[0].columns,2);self.w.set_privacy(True);self.assertFalse(any('53.621' in x.text() for x in self.w.scroll.widget().findChildren(__import__('PySide6.QtWidgets',fromlist=['QLabel']).QLabel)));self.w.set_privacy(False)
    def test_diagnostic_dialog_and_export_is_private(self):
        self.w.go('Dados e backup')
        def inspect(d):self.assertIn('Diagnóstico',d.windowTitle());self.assertGreater(d.findChild(QTableWidget).rowCount(),5);d.accept()
        self.modal(inspect);self.click('Verificar integridade e consistência')
        from diagnostics import run_diagnostics
        report=run_diagnostics(self.s);encoded=json.dumps(report);self.assertNotIn('CDB demonstrativo',encoded);self.assertNotIn('Perfil demonstrativo',encoded);self.assertTrue(report['passed'])
    def test_csv_backup_and_restore_use_isolated_files(self):
        csv=Path(self.temp.name)/'export.csv';backup=Path(self.temp.name)/'backup.sqlite'
        with patch('workspace.QFileDialog.getSaveFileName',return_value=(str(csv),'CSV')),patch('workspace.QMessageBox.information'):self.w.export_csv()
        self.assertIn('Competência',csv.read_text(encoding='utf-8-sig'))
        with patch('workspace.QFileDialog.getSaveFileName',return_value=(str(backup),'SQLite')),patch('workspace.QMessageBox.information'):self.w.backup()
        count=len(self.s.rows('SELECT * FROM tx'));self.s.save_tx(dict(period=self.w.p,day=self.w.p+'-01',description='Registro posterior ao backup',kind='Despesa',category='Outros',amount=100,account='',status='Confirmado',note=''))
        with patch('workspace.QFileDialog.getOpenFileName',return_value=(str(backup),'SQLite')),patch('workspace.QMessageBox.question',return_value=QMessageBox.Yes):self.w.restore()
        self.assertEqual(len(self.s.rows('SELECT * FROM tx')),count)
if __name__=='__main__':unittest.main()
  
