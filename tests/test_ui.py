import os,sys,tempfile,unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QTimer,QPointF,Qt
from PySide6.QtTest import QTest
from core import Store
from demo import seed_demo
from workspace import ModernWindow,EntryDialog
class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        for font in ['segoeui.ttf','segoeuib.ttf']:QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+font)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=Store(Path(self.temp.name)/'db.sqlite');seed_demo(self.store);self.win=ModernWindow(self.store);self.win.show();self.app.processEvents()
    def tearDown(self):self.win.close();self.app.processEvents();self.temp.cleanup()
    def test_entry_inline_validation_and_recurrence(self):
        def complete():
            dialog=self.app.activeModalWidget();self.assertIsInstance(dialog,EntryDialog);dialog.description.setText('Conta recorrente de teste');dialog.amount.setText('125,50');dialog.repeat.setValue(3);dialog.status.setCurrentText('Previsto');dialog.validate()
        QTimer.singleShot(50,complete);self.win.edit_tx();rows=self.store.rows("SELECT * FROM tx WHERE description='Conta recorrente de teste'");self.assertEqual(len(rows),3);self.assertEqual(len({r['series_key'] for r in rows}),1);self.assertTrue(all(r['status']=='Previsto' for r in rows))
        dialog=EntryDialog(self.store,self.win.p,parent=self.win);dialog.description.setText('Teste');dialog.amount.setText('inválido');dialog.validate();self.assertIsNone(dialog.result_data);self.assertTrue(dialog.error.text());dialog.reject()
    def test_all_screens_light_dark_two_sizes(self):
        for dark in [False,True]:
            self.win.set_theme(dark)
            for width,height in [(1440,950),(1000,680)]:
                self.win.resize(width,height)
                for name in self.win.nav:
                    self.win.go(name);self.app.processEvents();self.assertGreater(self.win.scroll.widget().layout().count(),1,name)
                self.win.go('Lançamentos');self.win.search.setText('inexistente-123');self.app.processEvents();self.assertEqual(self.win.tx_table.rowCount(),0)
        self.win.go('Cartões');self.app.processEvents();self.assertGreater(self.win.card_table.rowCount(),0)
    def test_shortcuts_palette_and_sidebar(self):
        self.win.toggle_sidebar();self.assertFalse(self.win.sidebar.isVisible());self.win.toggle_sidebar();self.assertTrue(self.win.sidebar.isVisible())
        def select():
            dialog=self.app.activeModalWidget();from PySide6.QtWidgets import QLineEdit,QListWidget
            search=dialog.findChild(QLineEdit);search.setText('Agenda');items=dialog.findChild(QListWidget);self.assertEqual(items.count(),1);items.setFocus();QTest.keyClick(items,Qt.Key_Return)
        QTimer.singleShot(50,select);self.win.command_palette();self.assertEqual(self.win.page,'Agenda')
if __name__=='__main__':unittest.main()

