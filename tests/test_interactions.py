import os,sys,tempfile,unittest,math
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from PySide6.QtCore import Qt,QDate,QTimer,QEvent,QPoint
from PySide6.QtGui import QImage,QColor
from PySide6.QtWidgets import QApplication,QPushButton,QCalendarWidget,QDialogButtonBox,QDialog,QLabel,QTableWidget
from PySide6.QtTest import QTest
from core import Store,money
from demo import seed_demo
from workspace import ModernWindow,EntryDialog,SmartForm
from widgets import DateField
from photos import PhotoCropDialog,circle_pixmap
from finance import recent_capacity,allocation

class InteractionFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.s=Store(Path(self.temp.name)/'financas.sqlite');seed_demo(self.s);self.w=ModernWindow(self.s);self.w.show();self.app.processEvents();self.errors=[];self.old_hook=sys.excepthook
        sys.excepthook=lambda *args:self.errors.append(str(args[1]))
    def tearDown(self):
        self.w.close();self.w.deleteLater();self.app.sendPostedEvents(None,QEvent.DeferredDelete);self.app.processEvents();sys.excepthook=self.old_hook;self.temp.cleanup();self.assertEqual(self.errors,[])
    def click(self,text):
        matches=[b for b in self.w.scroll.widget().findChildren(QPushButton) if b.text()==text];self.assertTrue(matches,text);QTest.mouseClick(matches[0],Qt.LeftButton)
    def modal(self,callback):
        def invoke():
            d=self.app.activeModalWidget()
            try:callback(d)
            except Exception as e:
                self.errors.append(str(e))
                if d:d.reject()
        QTimer.singleShot(40,invoke)
    def test_investment_maturity_calendar_click_and_save(self):
        self.w.go('Investimentos')
        def fill(d):
            self.assertIsInstance(d,SmartForm);d.inputs['name'].setText('CDB teste de calendário');d.inputs['value'].setText('1500,00');field=d.inputs['maturity'];self.assertIsInstance(field,DateField)
            def choose(cal):
                c=cal.findChild(QCalendarWidget);c.setSelectedDate(QDate(2029,7,15));QTest.mouseClick(cal.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok),Qt.LeftButton)
            self.modal(choose);QTest.mouseClick(field.calendar_button,Qt.LeftButton);self.assertEqual(field.iso(),'2029-07-15');self.assertEqual(field.editor.displayFormat(),'dd/MM/yyyy');QTest.mouseClick(d.findChild(QDialogButtonBox).button(QDialogButtonBox.Save),Qt.LeftButton)
        self.modal(fill);self.click('+ Adicionar posição');row=self.s.rows("SELECT * FROM positions WHERE name='CDB teste de calendário'")[0];self.assertEqual(row['maturity'],'2029-07-15')
    def test_budget_opens_selected_value_and_saves(self):
        self.s.db.execute('INSERT OR REPLACE INTO budgets VALUES (?,?,?)',('Lazer',self.w.p,12345));self.s.db.commit();self.w.go('Orçamentos');self.w.budget_table.selectRow(self.w.budget_rows.index('Lazer'))
        def fill(d):
            self.assertEqual(d.inputs['category'].currentText(),'Lazer');self.assertEqual(d.inputs['amount'].text(),'123,45');d.inputs['amount'].setText('321,90');d.accept()
        self.modal(fill);self.click('Definir limite');self.assertEqual(self.s.rows("SELECT amount FROM budgets WHERE category='Lazer' AND period=?",(self.w.p,))[0]['amount'],32190)
    def test_dates_destination_accounts_and_filter_retention(self):
        d=EntryDialog(self.s,self.w.p,parent=self.w);self.assertTrue(d.due.isEnabled());d.kind.setCurrentText('Transferência');self.assertFalse(d.target.isHidden());d.account.setCurrentIndex(1);d.target.setCurrentIndex(1);d.description.setText('Teste');d.amount.setText('10');d.validate();self.assertIsNone(d.result_data);d.reject()
        d=EntryDialog(self.s,self.w.p,parent=self.w);d.day.setDate(QDate(2027,5,20));self.assertEqual(d.period.text(),'2027-05');self.assertEqual(d.due.date(),QDate(2027,5,20));d.due.setDate(QDate(2027,6,10));d.day.setDate(QDate(2027,5,21));self.assertEqual(d.due.date(),QDate(2027,6,10));d.reject()
        self.w.go('Lançamentos');self.w.search.setText('mercado');self.w.status_filter.setCurrentText('Confirmado');self.w.render();self.assertEqual(self.w.search.text(),'mercado');self.assertEqual(self.w.status_filter.currentText(),'Confirmado')
    def test_create_account_from_launch_without_losing_fields(self):
        self.w.go('Lançamentos');d=EntryDialog(self.s,self.w.p,parent=self.w);d.description.setText('Não perder descrição');d.show();self.app.processEvents()
        def fill(form):form.inputs['name'].setText('Conta nova no lançamento');form.inputs['institution'].setText('Banco teste');form.accept()
        self.modal(fill);d.create_account();self.assertEqual(d.account.currentText(),'Conta nova no lançamento');self.assertEqual(d.description.text(),'Não perder descrição');d.close();d.deleteLater()
    def test_agenda_pending_amount_and_redemption(self):
        self.s.save_tx(dict(period=self.w.p,day=self.w.p+'-10',due_day=self.w.p+'-15',description='Valor ainda não informado',kind='Despesa',category='Outros',amount=None,account='',status='Previsto',note=''))
        self.s.save_tx(dict(period=self.w.p,day=self.w.p+'-10',description='Resgate previsto',kind='Resgate',category='Investimentos',amount=70000,account='',status='Previsto',note=''))
        self.w.go('Agenda');self.assertTrue(any(r['amount'] is None for r in self.w.agenda_rows));self.assertTrue(any(self.w.agenda_table.item(i,3).text()=='Sem valor' for i in range(self.w.agenda_table.rowCount())))
        rows=[r for r in self.w.agenda_rows if r['description']=='Resgate previsto'];self.assertEqual(len(rows),1)
        self.assertTrue(any(b.text()=='+ Agendar compromisso' for b in self.w.scroll.widget().findChildren(QPushButton)))
    def test_donut_sector_click_opens_detail_and_pdf_has_sections(self):
        self.w.go('Visão geral');from design import InteractiveChart
        chart=next(c for c in self.w.scroll.widget().findChildren(InteractiveChart) if c.center=='Despesas');chart.grab();start,end,name,value=chart.slices[0];center,radius=chart.donut_geometry;angle=math.radians((start+end)/2);point=QPoint(round(center.x()+math.sin(angle)*radius*.8),round(center.y()-math.cos(angle)*radius*.8))
        def inspect(d):self.assertIn(name,d.windowTitle());self.assertIsNotNone(d.findChild(QTableWidget));d.accept()
        self.modal(inspect);QTest.mouseClick(chart,Qt.LeftButton,pos=point)
        self.w.go('Relatórios');plain=self.w.report_document().toPlainText();self.assertIn('Patrimônio líquido',plain);self.assertIn('Despesas por categoria',plain);self.assertIn('Cartões e faturas',plain)
        dest=Path(self.temp.name)/'relatorio.pdf'
        with patch('workspace.QFileDialog.getSaveFileName',return_value=(str(dest),'PDF')),patch('workspace.QMessageBox.information'),patch('workspace.QMessageBox.warning') as error:self.click('Exportar relatório em PDF');error.assert_not_called()
        self.assertTrue(dest.read_bytes().startswith(b'%PDF'))
    def test_photo_crop_circle_and_unsaved_profile(self):
        self.w.go('Perfil');self.w.profile_fields['display-name'].setText('Nome digitado');image=QImage(800,400,QImage.Format_ARGB32);image.fill(QColor('red'))
        def crop(d):self.assertIsInstance(d,PhotoCropDialog);d.sliders['zoom'].setValue(150);d.sliders['x'].setValue(40);QTest.mouseClick(d.findChild(QDialogButtonBox).button(QDialogButtonBox.Save),Qt.LeftButton)
        self.modal(crop);self.w.crop_photo(image);self.assertEqual(self.w.profile_fields['display-name'].text(),'Nome digitado');self.assertTrue(self.s.setting('profile-photo-source'));pix=circle_pixmap(image,120).toImage();self.assertEqual(pix.pixelColor(0,0).alpha(),0);self.assertGreater(pix.pixelColor(60,60).alpha(),0)
    def test_simulation_invalid_input_clears_result_and_can_recover(self):
        self.w.go('Simulações');self.w.sim['rate'].setText('inválido');self.click('Calcular e salvar premissas');self.assertTrue(self.w.sim_error.text());self.assertEqual(self.w.sim_layout.count(),0);self.w.sim['rate'].setText('0');self.click('Calcular e salvar premissas');self.assertFalse(self.w.sim_error.text());self.assertGreater(self.w.sim_layout.count(),0);self.assertEqual(self.w.sim['start'].editor.displayFormat(),'MM/yyyy')
    def test_capacity_ignores_only_planned_month_and_includes_card_only(self):
        other=Store(Path(self.temp.name)/'capacity.sqlite');period=self.w.p
        other.save_tx(dict(period=period,day=period+'-01',description='Previsto',kind='Receita',category='Salário',amount=100000,account='',status='Previsto',note=''))
        self.assertEqual(recent_capacity(other,period)['periods'],[])
        from ledger import Ledger
        ledger=Ledger(other);c=ledger.save_card(dict(name='Teste',institution='Teste',limit_amount=100000,closing_day=20,due_day=28,payment_account='',color='#0065d4'));ledger.add_purchase(c,'Só cartão',20000,period+'-02','Lazer',1,period);self.assertEqual(recent_capacity(other,period)['expense'],20000);other.db.close()
if __name__=='__main__':unittest.main()
  
