"""Controles de data compartilhados, com calendário explícito e valor opcional."""
from datetime import date
from PySide6.QtCore import Qt,QDate,QLocale,Signal
from PySide6.QtWidgets import QWidget,QHBoxLayout,QVBoxLayout,QDateEdit,QPushButton,QCheckBox,QDialog,QCalendarWidget,QDialogButtonBox

class DateField(QWidget):
    dateChanged=Signal(QDate)
    def __init__(self,optional=False,parent=None):
        super().__init__(parent);self.optional=optional
        row=QHBoxLayout(self);row.setContentsMargins(0,0,0,0);row.setSpacing(6)
        self.enabled_box=QCheckBox('Informar data') if optional else None
        if self.enabled_box:row.addWidget(self.enabled_box);self.enabled_box.toggled.connect(self._toggle)
        self.editor=QDateEdit();self.editor.setCalendarPopup(True);self.editor.setDisplayFormat('dd/MM/yyyy');self.editor.setDateRange(QDate(1900,1,1),QDate(2200,12,31));self.editor.setDate(QDate.currentDate());self.editor.setLocale(QLocale('pt_BR'));self.editor.setKeyboardTracking(False);self.editor.setMinimumWidth(130);row.addWidget(self.editor,1)
        self.calendar_button=QPushButton('Calendário');self.calendar_button.setAutoDefault(False);self.calendar_button.setAccessibleName('Abrir calendário');self.calendar_button.clicked.connect(self.choose_date);row.addWidget(self.calendar_button)
        self.editor.dateChanged.connect(self.dateChanged.emit)
        if optional:self.enabled_box.setChecked(False);self._toggle(False)
    def _toggle(self,enabled):self.editor.setEnabled(enabled)
    def date(self):return self.editor.date()
    def setDate(self,value):self.editor.setDate(value)
    def setCalendarPopup(self,value):self.editor.setCalendarPopup(value)
    def setDisplayFormat(self,value):self.editor.setDisplayFormat(value)
    def setDateRange(self,low,high):self.editor.setDateRange(low,high)
    def set_iso(self,value):
        if value:
            parsed=QDate.fromString(value,'yyyy-MM-dd')
            if not parsed.isValid():raise ValueError('Data inválida: '+value)
            self.editor.setDate(parsed)
        if self.enabled_box:self.enabled_box.setChecked(bool(value))
    def iso(self):return self.date().toString('yyyy-MM-dd') if not self.enabled_box or self.enabled_box.isChecked() else ''
    def choose_date(self):
        dialog=QDialog(self);dialog.setWindowTitle('Escolher data');layout=QVBoxLayout(dialog);calendar=QCalendarWidget();calendar.setLocale(QLocale('pt_BR'));calendar.setMinimumDate(self.editor.minimumDate());calendar.setMaximumDate(self.editor.maximumDate());calendar.setSelectedDate(self.date());calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader);layout.addWidget(calendar)
        box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);box.button(QDialogButtonBox.Ok).setText('Usar data');box.button(QDialogButtonBox.Cancel).setText('Cancelar');box.accepted.connect(dialog.accept);box.rejected.connect(dialog.reject);calendar.activated.connect(lambda _:dialog.accept());layout.addWidget(box)
        if dialog.exec():
            if self.enabled_box:self.enabled_box.setChecked(True)
            self.setDate(calendar.selectedDate())

class MonthField(DateField):
    def __init__(self,value=None,parent=None):
        super().__init__(parent=parent);self.editor.setDisplayFormat('MM/yyyy')
        if value:self.setText(value)
    def text(self):return self.date().toString('yyyy-MM')
    def setText(self,value):self.set_iso(value+'-01')
  
