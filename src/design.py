"""Tokens visuais e gráficos nativos. Inspiração HIG adaptada ao Windows."""
import math
from PySide6.QtCore import Qt,QRectF,QPointF,Signal
from PySide6.QtGui import QColor,QPainter,QPen,QFont,QPainterPath,QPixmap,QIcon
from PySide6.QtWidgets import QWidget,QApplication,QToolTip
from core import money
COLORS=['#007AFF','#30A07A','#AC6CDB','#E49527','#D8596A','#4E9AA9','#7B87A8','#A07855']

def tokens(dark=False):
    return dict(bg='#101216',surface='#1b1e24',sidebar='#171a20',text='#f5f5f7',muted='#b2b9c6',line='#383e48',input='#242830',accent='#65adff',primary='#0067cf',selection='#243f5b',positive='#79d9b5',negative='#ff8998') if dark else dict(bg='#f5f5f7',surface='#ffffff',sidebar='#eceef2',text='#1d1d1f',muted='#59616f',line='#d5dae2',input='#ffffff',accent='#0065d4',primary='#0065d4',selection='#e1edff',positive='#13735a',negative='#b73349')

def theme(dark=False):
    t=tokens(dark)
    css='''
QWidget {font-family:'Segoe UI';font-size:14px;color:$text;} QMainWindow,QDialog,QScrollArea,QScrollArea>QWidget>QWidget {background:$bg;}
QFrame#sidebar {background:$sidebar;border-right:1px solid $line;} QFrame#sidebar QLabel {color:$muted;} QLabel#brand {font-size:23px;font-weight:700;color:$text;}
QPushButton {background:$surface;border:1px solid $line;border-radius:8px;padding:9px 14px;font-weight:600;min-height:18px;} QPushButton:hover {background:$selection;border-color:$accent;} QPushButton:focus {border:2px solid $accent;} QPushButton:pressed {background:$selection;} QPushButton:disabled {color:$muted;background:$sidebar;}
QPushButton#primary {background:$primary;color:white;border-color:$primary;} QPushButton#primary:hover {background:#0054b5;} QPushButton#nav {text-align:left;background:transparent;border:0;padding:9px 12px;font-weight:500;color:$text;} QPushButton#nav:hover {background:$selection;} QPushButton#nav:checked {background:$selection;color:$accent;font-weight:600;}
QLabel#title {font-size:29px;font-weight:700;color:$text;} QLabel#subtitle {color:$muted;} QLabel#small {font-size:12px;color:$muted;} QLabel#metric {font-size:28px;font-weight:600;color:$text;} QLabel#section {font-size:18px;font-weight:600;color:$text;} QLabel#positive {color:$positive;font-weight:600;} QLabel#negative {color:$negative;font-weight:600;}
QFrame#card {background:$surface;border:1px solid $line;border-radius:16px;} QFrame#banner {background:$selection;border:1px solid $line;border-radius:12px;}
QLineEdit,QComboBox,QDateEdit,QSpinBox,QDoubleSpinBox,QTextEdit,QListWidget {background:$input;border:1px solid $line;border-radius:8px;padding:8px;selection-background-color:$primary;selection-color:white;} QLineEdit:focus,QComboBox:focus,QDateEdit:focus,QSpinBox:focus {border:2px solid $accent;} QComboBox::drop-down {width:24px;border:0;} QComboBox QAbstractItemView {background:$surface;color:$text;selection-background-color:$selection;selection-color:$text;}
QTableWidget {background:$surface;border:0;gridline-color:$line;selection-background-color:$selection;selection-color:$text;alternate-background-color:$bg;} QTableWidget::item {padding:8px;} QHeaderView::section {background:$surface;color:$muted;padding:11px;border:0;border-bottom:1px solid $line;font-weight:600;} QProgressBar {background:$sidebar;border:0;border-radius:4px;max-height:8px;} QProgressBar::chunk {background:$primary;border-radius:4px;}
QScrollBar:vertical {width:9px;background:transparent;} QScrollBar::handle:vertical {background:$line;border-radius:4px;min-height:32px;} QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;} QCheckBox {spacing:8px;} QCheckBox::indicator {width:17px;height:17px;} QTabWidget::pane {border:0;} QTabBar::tab {background:$sidebar;padding:9px 18px;border-radius:6px;margin:3px;} QTabBar::tab:selected {background:$surface;color:$accent;} QToolTip {background:$surface;color:$text;border:1px solid $line;padding:8px;}
QCalendarWidget {background:$surface;} QCalendarWidget QToolButton {color:$text;background:$surface;padding:6px;min-width:28px;} QCalendarWidget QAbstractItemView {background:$surface;color:$text;selection-background-color:$primary;selection-color:white;}
QMenuBar,QMenu {background:$surface;color:$text;} QMenu::item:selected {background:$selection;} QStatusBar {background:$bg;color:$muted;border-top:1px solid $line;}
'''
    for key,value in t.items():css=css.replace('$'+key,value)
    return css

def icon(name,color='#0065d4'):
    pix=QPixmap(24,24);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.setPen(QPen(QColor(color),1.7,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(Qt.NoBrush)
    if name in ['Visão geral','Orçamentos']:
        for x,y in [(4,4),(14,4),(4,14),(14,14)]:p.drawRoundedRect(QRectF(x,y,6,6),1.5,1.5)
    elif name in ['Contas bancárias','Cartões']:
        p.drawRoundedRect(QRectF(3,5,18,14),3,3);p.drawLine(3,10,21,10);p.drawLine(6,15,10,15)
    elif name in ['Agenda','Dados e backup']:
        p.drawRoundedRect(QRectF(4,5,16,16),3,3);p.drawLine(4,10,20,10);p.drawLine(8,3,8,7);p.drawLine(16,3,16,7);p.drawLine(8,15,11,18);p.drawLine(11,18,17,12)
    elif name in ['Investimentos','Relatórios','Análises','Simulações']:
        p.drawLine(4,20,20,20);p.drawLine(4,20,4,4);p.drawPolyline([QPointF(7,15),QPointF(11,11),QPointF(15,13),QPointF(20,5)])
    elif name=='Metas e câmbio':p.drawEllipse(QRectF(3,3,18,18));p.drawEllipse(QRectF(7,7,10,10));p.drawLine(12,12,21,3)
    elif name=='Perfil':p.drawEllipse(QRectF(8,3,8,8));p.drawArc(QRectF(4,13,16,12),0,180*16)
    elif name=='Categorias':
        p.drawPolygon([QPointF(3,5),QPointF(14,5),QPointF(22,13),QPointF(13,22),QPointF(3,12)]);p.drawEllipse(QRectF(7,8,2,2))
    else:
        for y in [6,12,18]:p.drawLine(5,y,20,y);p.drawPoint(2,y)
    p.end();return QIcon(pix)

class InteractiveChart(QWidget):
    selected=Signal(str)
    def __init__(self,mode,series,labels=None,height=240,center='Total'):
        super().__init__();self.mode=mode;self.series=series;self.labels=labels or [];self.center=center;self.hits=[];self.slices=[];self.setMouseTracking(True);self.setMinimumHeight(height);self.setMinimumWidth(230);self.setAccessibleName('Gráfico '+mode);self.setAccessibleDescription('\n'.join(n+': '+', '.join(money(round(v)) for v in values) for n,values in series))
    def hit_at(self,point):
        for rect,title,value in self.hits:
            if rect.contains(point):return title,value
        if self.mode=='donut' and self.slices:
            center,radius=self.donut_geometry;dx=point.x()-center.x();dy=point.y()-center.y();distance=math.hypot(dx,dy)
            if radius*.56<=distance<=radius:
                angle=math.degrees(math.atan2(dx,-dy))%360
                for start,end,title,value in self.slices:
                    if start<=angle<end:return title,value
        return None
    def mouseMoveEvent(self,event):
        hit=self.hit_at(event.position())
        if hit:QToolTip.showText(event.globalPosition().toPoint(),hit[0]+'\n'+money(round(hit[1])),self)
        else:QToolTip.hideText()
    def mousePressEvent(self,event):
        if event.button()!=Qt.LeftButton:return
        hit=self.hit_at(event.position())
        if hit:self.selected.emit(hit[0])
    def leaveEvent(self,event):QToolTip.hideText()
    def paintEvent(self,event):
        t=tokens(QApplication.instance().property('dark') is True);p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setFont(QFont('Segoe UI',9));p.setPen(QColor(t['muted']));self.hits=[];self.slices=[];w,h=self.width(),self.height()
        if not self.series or not any(any(v!=0 for v in values) for _,values in self.series):p.drawText(self.rect(),Qt.AlignCenter,'Sem valores neste período\nAdicione um lançamento para começar.');return
        if self.mode=='donut':
            vals=[(n,v[0]) for n,v in self.series if v and v[0]>0];total=sum(v for n,v in vals)
            if not total:return
            size=min(210,h-30,w*.45);rect=QRectF(6,10,size,size);start=90*16;angle=0;self.donut_geometry=(rect.center(),size/2)
            for i,(name,value) in enumerate(vals):
                span=-round(value/total*360*16);p.setPen(QPen(QColor(t['surface']),3));p.setBrush(QColor(COLORS[i%len(COLORS)]));p.drawPie(rect,start,span);start+=span;self.slices.append((angle,angle+value/total*360,name,value));angle+=value/total*360
            p.setPen(Qt.NoPen);p.setBrush(QColor(t['surface']));p.drawEllipse(rect.adjusted(size*.22,size*.22,-size*.22,-size*.22));p.setPen(QColor(t['text']));p.drawText(rect,Qt.AlignCenter,self.center+'\n'+money(round(total)))
            for i,(name,value) in enumerate(vals[:8]):
                x=size+26;y=24+i*25;p.fillRect(int(x),y-9,8,8,QColor(COLORS[i%len(COLORS)]));p.setPen(QColor(t['text']));available=max(0,w-x-36);text=p.fontMetrics().elidedText(f'{name}  {value/total:.0%}',Qt.ElideRight,int(available));p.drawText(int(x+16),y,text);self.hits.append((QRectF(x,y-16,w-x,24),name,value))
            if len(vals)>8:p.setPen(QColor(t['muted']));p.drawText(int(size+42),24+8*25,f'+{len(vals)-8} categorias no relatório')
            return
        allv=[v for _,values in self.series for v in values];lo=min(0,min(allv));hi=max(0,max(allv));span=(hi-lo)*1.15 or 1;left=74;right=w-18;top=40;bottom=h-34
        def yy(v):return bottom-(v-lo)/span*(bottom-top)
        for i in range(5):
            value=lo+span*i/4;y=yy(value);p.setPen(QPen(QColor(t['line']),1));p.drawLine(QPointF(left,y),QPointF(right,y));p.setPen(QColor(t['muted']));p.drawText(QRectF(0,y-9,left-10,20),Qt.AlignRight,f'{value/100:,.0f}'.replace(',','.'))
        n=max(len(v) for _,v in self.series)
        for index,(name,values) in enumerate(self.series):
            color=QColor(COLORS[index%len(COLORS)]);p.setPen(QPen(color,2.5));p.setBrush(color);lx=left+index*(right-left)/max(1,len(self.series));p.drawText(int(lx),18,name)
            if self.mode=='bar':
                cell=(right-left)/max(1,n);bw=cell/(len(self.series)+1)
                for i,value in enumerate(values):
                    x=left+i*cell+index*bw+4;y=yy(value);r=QRectF(x,min(y,yy(0)),max(2,bw-4),max(2,abs(y-yy(0))));p.drawRoundedRect(r,3,3);self.hits.append((r.adjusted(-2,-3,2,3),name+' • '+(self.labels[i] if i<len(self.labels) else str(i)),value))
            else:
                path=QPainterPath()
                for i,value in enumerate(values):
                    x=left+i*(right-left)/max(1,n-1);y=yy(value)
                    if i:path.lineTo(x,y)
                    else:path.moveTo(x,y)
                    self.hits.append((QRectF(x-7,y-8,14,16),name+' • '+(self.labels[i] if i<len(self.labels) else str(i)),value))
                p.setBrush(Qt.NoBrush);p.drawPath(path)
                if len(values)==1:p.setBrush(color);p.drawEllipse(QPointF(left,yy(values[0])),4,4)
        p.setPen(QColor(t['muted']))
        for i,text in enumerate(self.labels):
            if n>10 and i not in [0,n//4,n//2,3*n//4,n-1]:continue
            x=left+(i+.5)*(right-left)/max(1,n) if self.mode=='bar' else left+i*(right-left)/max(1,n-1);p.drawText(QRectF(x-32,bottom+10,64,20),Qt.AlignCenter,text)
    
