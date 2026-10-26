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
    def __init__(self,value=None,parent=None,optional=False):
        super().__init__(parent=parent,optional=optional);self.editor.setDisplayFormat('MM/yyyy')
        if value:self.setText(value)
    def text(self):return self.date().toString('yyyy-MM')
    def iso(self):return self.text() if not self.enabled_box or self.enabled_box.isChecked() else ''
    def setText(self,value):self.set_iso(value+'-01')

class ResponsiveCards(QWidget):
    def __init__(self,cards):
        from PySide6.QtWidgets import QGridLayout,QSizePolicy
        super().__init__();self.cards=cards;self.columns=0;self.grid=QGridLayout(self);self.grid.setContentsMargins(0,0,0,0);self.grid.setSpacing(14);self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Minimum);self.reflow()
    def reflow(self):
        columns=min(len(self.cards),2 if self.width()<900 else 4)
        if columns==self.columns:return
        while self.grid.count():self.grid.takeAt(0)
        for i in range(4):self.grid.setColumnStretch(i,0)
        self.columns=columns
        for i,w in enumerate(self.cards):self.grid.addWidget(w,i//columns,i%columns)
        for i in range(columns):self.grid.setColumnStretch(i,1)
        self.updateGeometry()
    def resizeEvent(self,event):super().resizeEvent(event);self.reflow()

from PySide6.QtCore import QSize,QRect,QPoint,QPointF
from PySide6.QtGui import QPainter,QPolygonF
from PySide6.QtWidgets import QLayout,QWidgetItem,QComboBox
class FlowLayout(QLayout):
    def __init__(self):super().__init__();self.items=[];self.setContentsMargins(0,0,0,0);self.setSpacing(10)
    def addItem(self,item):self.items.append(item)
    def addWidget(self,widget,*args):super().addWidget(widget)
    def addStretch(self,*args):pass
    def setStretch(self,*args):pass
    def count(self):return len(self.items)
    def itemAt(self,index):return self.items[index] if 0<=index<len(self.items) else None
    def takeAt(self,index):return self.items.pop(index) if 0<=index<len(self.items) else None
    def expandingDirections(self):return Qt.Orientation(0)
    def hasHeightForWidth(self):return True
    def heightForWidth(self,width):return self.arrange(QRect(0,0,width,0),True)
    def setGeometry(self,rect):super().setGeometry(rect);self.arrange(rect,False)
    def sizeHint(self):return self.minimumSize()
    def minimumSize(self):
        size=QSize()
        for item in self.items:size=size.expandedTo(item.minimumSize())
        return size
    def arrange(self,rect,test):
        x=rect.x();y=rect.y();height=0
        for item in self.items:
            size=item.sizeHint();size.setWidth(min(size.width(),max(1,rect.width())))
            if x>rect.x() and x+size.width()>rect.right()+1:x=rect.x();y+=height+self.spacing();height=0
            if not test:item.setGeometry(QRect(QPoint(x,y),size))
            x+=size.width()+self.spacing();height=max(height,size.height())
        return y+height-rect.y()

class ChoiceBox(QComboBox):
    def paintEvent(self,event):
        super().paintEvent(event);p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setPen(Qt.NoPen);p.setBrush(self.palette().color(self.foregroundRole()));x=self.width()-15;y=self.height()/2;p.drawPolygon(QPolygonF([QPointF(x-4,y-2),QPointF(x+4,y-2),QPointF(x,y+3)]));p.end()
    
