import os, sys, json, csv, shutil, math, traceback
from pathlib import Path
from datetime import date, datetime
from PySide6.QtCore import Qt, QDate, QThread, Signal, QTimer, QRectF, QPointF, QLockFile
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QPainterPath, QIcon, QFontDatabase, QPixmap, QImage, QTextDocument
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QComboBox,QLineEdit,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QScrollArea,QFrame,QDialog,QFormLayout,QDialogButtonBox,QDateEdit,QDoubleSpinBox,QSpinBox,QMessageBox,QFileDialog,QProgressBar,QTextEdit,QCheckBox)
from core import *
from widgets import FlowLayout
from finance import position_projection, goal_assessment, recent_capacity, insights, allocation, asset_group
VERSION='0.2.1'
ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
PALETTE=['#14816e','#527bdd','#e5a64e','#9c77cf','#dd7787','#62a6b1','#829468','#aa8868']
STYLE='''
QWidget {font-family: 'Segoe UI';font-size:14px;color:#253b39;}
QMainWindow,QScrollArea,QScrollArea>QWidget>QWidget {background:#f4f7f6;}
QFrame#sidebar {background:#122e2b;} QFrame#sidebar QLabel {color:#bed0ca;} QLabel#brand {color:white;font-size:25px;font-weight:700;}
QPushButton {background:white;border:1px solid #d7e2de;border-radius:7px;padding:10px 16px;font-weight:600;} QPushButton:hover {background:#edf4f0;border-color:#14816e;} QPushButton:focus {border:2px solid #14816e;} QPushButton:pressed {background:#d8e8e0;}
QPushButton#primary {background:#167b66;color:white;border:1px solid #167b66;} QPushButton#primary:hover {background:#10634f;}
QPushButton#nav {text-align:left;color:#c6d7d1;background:transparent;border:0;padding:9px 16px;} QPushButton#nav:checked {background:#24473e;color:#d4f4a6;} QPushButton#nav:hover {background:#24473e;}
QLabel#title {font-size:29px;font-weight:700;color:#163c32;} QLabel#subtitle {color:#586f68;} QLabel#small {font-size:12px;color:#586f68;} QLabel#metric {font-size:27px;font-weight:700;} QLabel#section {font-size:18px;font-weight:600;}
QFrame#card {background:white;border:1px solid #dfe8e2;border-radius:12px;} QFrame#banner {background:#e7efdc;border:1px solid #ceddbb;border-radius:10px;}
QLineEdit,QComboBox,QDateEdit,QSpinBox,QDoubleSpinBox,QTextEdit {background:white;border:1px solid #becfc7;border-radius:6px;padding:8px;selection-background-color:#167b66;} QLineEdit:focus,QComboBox:focus {border:2px solid #167b66;}
QTableWidget {background:white;border:0;gridline-color:#e7eeea;selection-background-color:#dcece3;selection-color:#153d31;alternate-background-color:#f8faf8;}
QHeaderView::section {background:#f0f5f1;padding:11px;border:0;border-bottom:1px solid #dfe8e2;color:#50675e;font-weight:600;}
QTableWidget::item {padding:8px;} QProgressBar {background:#e8eee6;border:0;border-radius:4px;max-height:8px;} QProgressBar::chunk {background:#167b66;border-radius:4px;}
QScrollBar:vertical {width:10px;background:#f4f7f6;} QScrollBar::handle:vertical {background:#bccfc4;border-radius:5px;min-height:30px;} QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QDialog {background:#f4f7f6;}
'''
def label(text,kind=None,wrap=False):
    w=QLabel(str(text)); w.setWordWrap(wrap)
    if kind: w.setObjectName(kind)
    w.setTextInteractionFlags(Qt.TextSelectableByMouse); return w

def button(text,fn,primary=False):
    b=QPushButton(text); b.clicked.connect(fn)
    if primary:b.setObjectName('primary')
    return b

def card(title=None):
    w=QFrame(); w.setObjectName('card'); l=QVBoxLayout(w); l.setContentsMargins(20,18,20,18); l.setSpacing(14)
    if title:l.addWidget(label(title,'section'))
    return w,l

def table(headers,rows):
    t=QTableWidget(len(rows),len(headers)); t.setHorizontalHeaderLabels(headers); t.verticalHeader().hide(); t.setAlternatingRowColors(True); t.setShowGrid(False)
    t.setWordWrap(False);t.setTextElideMode(Qt.ElideRight);t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setSelectionMode(QAbstractItemView.SingleSelection)
    for i,row in enumerate(rows):
        for j,value in enumerate(row):
            item=QTableWidgetItem(str(value if value is not None else '—')); t.setItem(i,j,item)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);t.horizontalHeader().setMinimumSectionSize(120);t.horizontalHeader().setStretchLastSection(False);t.horizontalHeader().setMinimumHeight(max(46,t.fontMetrics().height()+24));t.verticalHeader().setDefaultSectionSize(max(48,t.fontMetrics().height()+24));t.verticalHeader().setMinimumSectionSize(max(48,t.fontMetrics().height()+24))
    t.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel);t.setMinimumHeight(240); return t

class Chart(QWidget):
    def __init__(self,mode,series,labels=None,height=230):
        super().__init__(); self.mode=mode; self.series=series; self.labels=labels or []; self.setMinimumHeight(height); self.setMinimumWidth(200)
        self.setToolTip('\n'.join(f'{name}: '+', '.join(money(round(v)) for v in vals) for name,vals in series))
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setFont(QFont('Segoe UI',9)); w,h=self.width(),self.height(); p.setPen(QColor('#586f68'))
        if not self.series or not any(any(v!=0 for v in vals) for _,vals in self.series): p.drawText(self.rect(),Qt.AlignCenter,'Sem valores para este período'); return
        if self.mode=='donut':
            vals=[(n,v[0]) for n,v in self.series if v[0]>0]; total=sum(v for _,v in vals)
            size=min(h-32,w*.48,210); rect=QRectF(8,12,size,size); start=90*16
            for i,(name,value) in enumerate(vals):
                span=-round(value/total*360*16); p.setPen(QPen(QColor('white'),2)); p.setBrush(QColor(PALETTE[i%len(PALETTE)])); p.drawPie(rect,start,span); start+=span
            p.setPen(Qt.NoPen); p.setBrush(QColor('white')); p.drawEllipse(rect.adjusted(size*.24,size*.24,-size*.24,-size*.24)); p.setPen(QColor('#253b39')); p.drawText(rect,Qt.AlignCenter,'Despesas\n'+money(round(total)))
            x=size+30
            for i,(name,value) in enumerate(vals[:9]):
                y=25+i*24; p.fillRect(int(x),y-9,9,9,QColor(PALETTE[i%len(PALETTE)])); p.setPen(QColor('#405d52')); p.drawText(int(x+17),y,f'{name[:24]}  {value/total:.0%}')
            return
        allv=[v for _,vals in self.series for v in vals]; lo=min(0,min(allv)); hi=max(allv)*1.12 or 1; span=hi-lo or 1; left=68; right=w-18; top=25; bottom=h-38
        def yy(v):return bottom-(v-lo)/span*(bottom-top)
        for i in range(5):
            v=lo+span*i/4; y=yy(v); p.setPen(QPen(QColor('#e6ede8'),1)); p.drawLine(QPointF(left,y),QPointF(right,y)); p.setPen(QColor('#61766a')); p.drawText(QRectF(0,y-9,left-8,20),Qt.AlignRight,f'{v/100:,.0f}'.replace(',','.'))
        n=max(len(v) for _,v in self.series)
        for s,(name,values) in enumerate(self.series):
            col=QColor(PALETTE[s%len(PALETTE)]); p.setPen(QPen(col,3)); p.setBrush(col)
            if self.mode=='bar':
                cell=(right-left)/max(n,1); bw=cell/(len(self.series)+1)
                for i,value in enumerate(values):
                    x=left+i*cell+s*bw+6; y=yy(value); p.drawRoundedRect(QRectF(x,min(y,yy(0)),max(2,bw-4),max(1,abs(yy(0)-y))),3,3)
            else:
                path=QPainterPath()
                for i,value in enumerate(values):
                    x=left+i*(right-left)/max(1,n-1); y=yy(value)
                    if i==0:path.moveTo(x,y)
                    else:path.lineTo(x,y)
                p.setBrush(Qt.NoBrush);p.drawPath(path)
            p.setPen(col); p.drawText(left+s*170,14,name)
        p.setPen(QColor('#61766a'))
        for i,text in enumerate(self.labels):
            if n>15 and i not in [0,n//4,n//2,3*n//4,n-1]:continue
            x=left+(i+.5)*(right-left)/max(n,1) if self.mode=='bar' else left+i*(right-left)/max(1,n-1)
            p.drawText(QRectF(x-32,bottom+12,64,20),Qt.AlignCenter,str(text))

class Form(QDialog):
    def __init__(self,title,fields,parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.setMinimumWidth(530); self.inputs={}; layout=QVBoxLayout(self); layout.setContentsMargins(24,24,24,24); layout.addWidget(label(title,'section')); area=QScrollArea();area.setWidgetResizable(True);area.setFrameShape(QFrame.NoFrame);inner=QWidget();form=QFormLayout(inner);form.setSpacing(12);form.setRowWrapPolicy(QFormLayout.WrapLongRows);area.setWidget(inner);layout.addWidget(area);self.resize(620,min(740,QApplication.primaryScreen().availableGeometry().height()-80))
        for key,title,value,options in fields:
            if options:
                w=QComboBox();w.addItems(options);w.setCurrentText(str(value))
            else:w=QLineEdit('' if value is None else str(value))
            w.setAccessibleName(title.replace(' AAAA-MM-DD',' (dia/mês/ano)').replace(' AAAA-MM',' (mês/ano)'));form.addRow(title.replace(' AAAA-MM-DD',' (dia/mês/ano)').replace(' AAAA-MM',' (mês/ano)'),w);self.inputs[key]=w
        self.error=label('','negative',True);layout.addWidget(self.error)
        box=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);box.button(QDialogButtonBox.Save).setText('Salvar');box.button(QDialogButtonBox.Cancel).setText('Cancelar');box.accepted.connect(self.accept);box.rejected.connect(self.reject);layout.addWidget(box)
    def values(self):return {k:(w.currentText() if isinstance(w,QComboBox) else w.text()).strip() for k,w in self.inputs.items()}

class FXWorker(QThread):
    done=Signal(object)
    def run(self):
        import urllib.request
        try:
            req=urllib.request.Request('https://api.frankfurter.dev/v2/rate/brl/jpy',headers={'User-Agent':'Horizonte/0.1'})
            with urllib.request.urlopen(req,timeout=15) as r:data=json.load(r)
            if not isinstance(data.get('rate'),(float,int)) or data['rate']<=0:raise ValueError('Cotação inválida')
            self.done.emit(data)
        except Exception as e:self.done.emit({'error':str(e)})

class Window(QMainWindow):
    def __init__(self,store):
        super().__init__();self.s=store;self.page='Visão geral';self.fx=None;self.setWindowTitle('Horizonte • Finanças pessoais');self.resize(1440,960);self.setMinimumSize(1080,740)
        self.setWindowIcon(QIcon(str(ROOT/'horizonte.ico')))
        root=QWidget();self.setCentralWidget(root);row=QHBoxLayout(root);row.setContentsMargins(0,0,0,0);row.setSpacing(0)
        side=QFrame();side.setObjectName('sidebar');side.setFixedWidth(225);sl=QVBoxLayout(side);sl.setContentsMargins(20,30,20,24);sl.setSpacing(4)
        sl.addWidget(label('horizonte','brand'));sl.addWidget(label('FINANÇAS PESSOAIS','small'));sl.addSpacing(18);self.nav={}
        for name in ['Visão geral','Lançamentos','Análises','Orçamentos','Contas bancárias','Investimentos','Metas e câmbio','Relatórios','Simulações','Perfil','Dados e backup']:
            b=QPushButton(name);b.setObjectName('nav');b.setCheckable(True);b.clicked.connect(lambda _,n=name:self.go(n));sl.addWidget(b);self.nav[name]=b
        sl.addStretch();self.avatar=QLabel();self.avatar.setFixedSize(48,48);sl.addWidget(self.avatar);self.profile_name=label(self.s.setting('display-name','Meu planejamento'));sl.addWidget(self.profile_name);self.update_avatar();sl.addWidget(label('Dados locais • versão '+VERSION,'small'));row.addWidget(side)
        area=QWidget();al=QVBoxLayout(area);al.setContentsMargins(28,22,28,22);al.setSpacing(18);self.top=QHBoxLayout();self.top.addWidget(label('Seu dinheiro, com clareza.','subtitle'));self.top.addStretch()
        self.period=QComboBox();self.period.setMinimumWidth(195);self.refresh_periods();self.period.currentIndexChanged.connect(self.render);self.top.addWidget(self.period);self.top.addWidget(button('+ Novo lançamento',self.edit_tx,True));al.addLayout(self.top)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame);al.addWidget(self.scroll);row.addWidget(area,1)
        self.render();self.backup_timer=QTimer(self);self.backup_timer.timeout.connect(self.automatic_backup);self.backup_timer.start(30*60*1000);QTimer.singleShot(1000,self.automatic_backup)
    def refresh_periods(self):
        old=self.period.currentData() if hasattr(self,'period') else None;self.period.blockSignals(True);self.period.clear()
        for p in self.s.periods():self.period.addItem(month_label(p),p)
        idx=self.period.findData(old or date.today().strftime('%Y-%m'));self.period.setCurrentIndex(max(0,idx));self.period.blockSignals(False)
    def go(self,name):self.page=name;self.render()
    def render(self,*_):
        for n,b in self.nav.items():b.setChecked(n==self.page)
        w=QWidget();self.body=QVBoxLayout(w);self.body.setContentsMargins(0,0,0,0);self.body.setSpacing(20);self.body.addWidget(label(self.page,'title'))
        if self.s.setting('demo')=='1':self.body.addWidget(label('DEMONSTRAÇÃO • Todos os valores e registros são fictícios.','subtitle'))
        self.p=self.period.currentData() or date.today().strftime('%Y-%m')
        {'Visão geral':self.overview,'Lançamentos':self.transactions,'Análises':self.analysis,'Orçamentos':self.budgets,'Contas bancárias':self.accounts,'Investimentos':self.portfolio,'Metas e câmbio':self.goals,'Simulações':self.simulations,'Relatórios':self.reports,'Perfil':self.profile,'Dados e backup':self.data_page}[self.page]()
        self.body.addStretch();self.scroll.setWidget(w)
    def hint(self,text):self.body.addWidget(label(text,'subtitle',True))
    def banner(self,text):
        w=QFrame();w.setObjectName('banner');l=QVBoxLayout(w);l.setContentsMargins(18,14,18,14);l.addWidget(label(text,None,True));self.body.addWidget(w)
    def metrics(self,items):
        row=QHBoxLayout();row.setSpacing(14)
        for title,value,note in items:
            w,l=card();l.addWidget(label(title,'subtitle'));l.addWidget(label(value,'metric'));l.addWidget(label(note,'small',True));row.addWidget(w)
        self.body.addLayout(row)
    def overview(self):
        sm=self.s.summary(self.p);self.hint(month_label(self.p)+' • Fluxo do mês por competência. Valores a revisar são incluídos; previstos e valores ausentes ficam fora dos totais.')
        self.banner('Patrimônio cadastrado: '+money(sum(allocation(self.s).values()))+' • Investimentos e saldos em conta. Consulte as datas de atualização.')
        self.metrics([('Receitas',money(sm['Receita']),'Salário e outras entradas'),('Despesas',money(sm['Despesa']),'Consumo, contas e faturas'),('Aportes',money(sm['Aporte']),'Movimentação para investimentos'),('Fluxo disponível',money(sm['livre']),'Receitas − despesas − aportes + resgates')])
        history=[p for p in self.s.periods() if p<=self.p][-10:];summaries=[self.s.summary(p) for p in history]
        grid=QHBoxLayout();a,l=card('Receitas e despesas no tempo');l.addWidget(Chart('bar',[('Receitas',[x['Receita'] for x in summaries]),('Despesas',[x['Despesa'] for x in summaries])],[p[5:]+'/'+p[2:4] for p in history]));grid.addWidget(a,3)
        cats=self.s.rows("SELECT category,SUM(amount) AS v FROM tx WHERE period=? AND kind='Despesa' AND status!='Previsto' AND amount IS NOT NULL GROUP BY category ORDER BY v DESC",(self.p,));b,l=card('Para onde foi o dinheiro');l.addWidget(Chart('donut',[(x['category'],[x['v']]) for x in cats]));grid.addWidget(b,3);self.body.addLayout(grid)
        positions=self.s.rows('SELECT * FROM positions');total=sum(x['value'] for x in positions)
        g=self.s.rows('SELECT * FROM goals ORDER BY id LIMIT 1')[0];goal_a=goal_assessment(self.s,g,self.p);row=QHBoxLayout();a,l=card('Seu próximo horizonte');l.addWidget(label(g['name'],'section'));l.addWidget(label(money(goal_a['base'])+' de '+money(g['target']),'metric'));bar=QProgressBar();bar.setRange(0,1000);bar.setValue(min(1000,round(goal_a['base']/max(1,g['target'])*1000)));bar.setTextVisible(False);l.addWidget(bar);l.addWidget(label('Ativos vinculados ou valor reservado manual. Veja a projeção na tela de metas.','small',True));l.addWidget(button('Acompanhar metas',lambda:self.go('Metas e câmbio')));row.addWidget(a)
        b,l=card('Leituras do mês');review=self.s.rows("SELECT COUNT(*) AS n FROM tx WHERE period=? AND status='A revisar'",(self.p,))[0]['n'];missing=self.s.rows('SELECT COUNT(*) AS n FROM tx WHERE period=? AND amount IS NULL',(self.p,))[0]['n']
        lines=[f'{review} lançamentos aguardam revisão; {missing} têm valor ausente.',f'Carteira informada: {money(total)}. Veja a data de cada posição em Investimentos.']
        if cats:lines.append(f"Maior categoria: {cats[0]['category']} ({money(cats[0]['v'])}).")
        if sm['Receita']:lines.append(f"Despesas representam {sm['Despesa']/sm['Receita']:.1%} das receitas do mês.")
        lines.append('Faturas importadas são agregadas. Revise antes de registrar as mesmas compras individualmente.')
        for line in lines:l.addWidget(label(line,None,True))
        row.addWidget(b);row.setStretch(0,1);row.setStretch(1,1);self.body.addLayout(row)
        w,l=card('Onde está seu dinheiro hoje');l.addWidget(Chart('donut',[(k,[v]) for k,v in allocation(self.s).items() if v>0]));l.addWidget(label('Saldos negativos não entram no gráfico de composição. O patrimônio total inclui esses saldos.','small',True));self.body.addWidget(w)
        w,l=card('Últimos lançamentos');rows=self.s.rows('SELECT * FROM tx WHERE period=? ORDER BY id DESC LIMIT 6',(self.p,));l.addWidget(table(['Descrição','Tipo','Categoria','Valor','Situação'],[[x['description'],x['kind'],x['category'],money(x['amount']) if x['amount'] is not None else 'Sem valor',x['status']] for x in rows]));self.body.addWidget(w)
    def transactions(self):
        self.hint('Cadastre receitas, gastos, aportes, resgates e transferências. Dê dois cliques em uma linha para revisar ou editar.')
        tools=FlowLayout();self.search=QLineEdit();self.search.setPlaceholderText('Buscar descrição, conta ou categoria');self.search.setAccessibleName('Buscar lançamentos');tools.addWidget(self.search,1)
        self.kind_filter=QComboBox();self.kind_filter.addItems(['Todos os tipos']+KINDS);tools.addWidget(self.kind_filter)
        self.status_filter=QComboBox();self.status_filter.addItems(['Todas as situações','A revisar','Confirmado','Previsto','Sem valor']);tools.addWidget(self.status_filter)
        tools.addWidget(button('Editar',self.edit_selected));tools.addWidget(button('Excluir',self.delete_selected));self.body.addLayout(tools)
        self.tx_table=table(['Data','Descrição','Tipo','Categoria','Valor','Conta','Situação'],[]);self.tx_table.setMinimumHeight(470);self.tx_table.cellDoubleClicked.connect(lambda *_:self.edit_selected());self.body.addWidget(self.tx_table)
        self.search.textChanged.connect(self.fill_transactions);self.kind_filter.currentTextChanged.connect(self.fill_transactions);self.status_filter.currentTextChanged.connect(self.fill_transactions);self.fill_transactions()
        self.hint('Transferências são neutras neste fluxo consolidado. Aporte e resgate alteram o fluxo, mas a carteira exige atualização de posição separada. Recorrências criadas como previstas só entram no fluxo após confirmação.')
    def fill_transactions(self,*_):
        query=self.search.text().casefold();kind=self.kind_filter.currentText();status=self.status_filter.currentText();data=self.s.rows('SELECT * FROM tx WHERE period=? ORDER BY COALESCE(day,period) DESC,id DESC',(self.p,))
        self.tx_rows=[x for x in data if (kind=='Todos os tipos' or x['kind']==kind) and (status=='Todas as situações' or (x['amount'] is None if status=='Sem valor' else x['status']==status)) and query in (x['description']+' '+x['category']+' '+x['account']).casefold()]
        self.tx_table.setRowCount(len(self.tx_rows))
        for i,x in enumerate(self.tx_rows):
            vals=[x['day'] or 'Sem dia',x['description'],x['kind'],x['category'],money(x['amount']) if x['amount'] is not None else 'Sem valor',x['account'],x['status']]
            for j,v in enumerate(vals):
                it=QTableWidgetItem(str(v));it.setToolTip((x['source'] or 'Cadastro manual')+'\n'+(x['note'] or ''));self.tx_table.setItem(i,j,it)
    def edit_selected(self):
        i=self.tx_table.currentRow()
        if i>=0:self.edit_tx(self.tx_rows[i])
    def delete_selected(self):
        i=self.tx_table.currentRow()
        if i>=0 and QMessageBox.question(self,'Excluir lançamento','Excluir este lançamento? Faça backup para guardar uma cópia.')==QMessageBox.Yes:
            self.s.db.execute('DELETE FROM tx WHERE id=?',(self.tx_rows[i]['id'],));self.s.db.commit();self.render()
    def edit_tx(self,data=None):
        if not isinstance(data,dict):data={}
        fields=[('description','Descrição',data.get('description',''),None),('amount','Valor em R$ (vazio = ausente)',str(data['amount']/100).replace('.',',') if data.get('amount') is not None else '',None),('kind','Tipo',data.get('kind','Despesa'),KINDS),('category','Categoria',data.get('category','Outros'),self.s.category_names()),('day','Data AAAA-MM-DD (opcional)',data.get('day',date.today().isoformat()),None),('period','Competência AAAA-MM',data.get('period',self.p),None),('account','Conta de origem',data.get('account',''),['']+sorted(set([a['name'] for a in self.s.rows('SELECT name FROM accounts')]+([data['account']] if data.get('account') else [])))),('target_account','Destino (transferência)',data.get('target_account',''),['']+sorted(set([a['name'] for a in self.s.rows('SELECT name FROM accounts')]+([data['target_account']] if data.get('target_account') else [])))),('status','Situação',data.get('status','Confirmado'),['Confirmado','A revisar','Previsto']),('note','Observações',data.get('note',''),None)]
        if not data:fields.append(('repeat','Repetir por meses (1 a 60)',1,None))
        f=Form('Editar lançamento' if data else 'Novo lançamento',fields,self)
        while f.exec():
            try:
                v=f.values();v['amount']=cents(v['amount']) if v['amount'] else None;v['day']=v['day'] or None
                repeat=int(v.pop('repeat',1))
                if not 1<=repeat<=60:raise ValueError('Recorrência entre 1 e 60 meses.')
                self.s.save_tx(v,data.get('id'))
                if repeat>1:
                    import calendar
                    base=date.fromisoformat(v['period']+'-01'); original=date.fromisoformat(v['day']) if v['day'] else None
                    for offset in range(1,repeat):
                        k=base.year*12+base.month-1+offset;y,m=divmod(k,12);m+=1;n=dict(v);n['period']=f'{y:04d}-{m:02d}';n['day']=f'{y:04d}-{m:02d}-{min(original.day,calendar.monthrange(y,m)[1]):02d}' if original else None;n['status']='Previsto';self.s.save_tx(n)
                self.refresh_periods();self.render();break
            except (ValueError,sqlite3.Error) as e:f.error.setText(str(e))
    def budgets(self):
        self.hint('Defina limites de despesas para o mês selecionado. As categorias da importação são sugestões e podem ser corrigidas nos lançamentos.')
        tools=FlowLayout();tools.addWidget(button('Definir limite',self.edit_budget,True));tools.addWidget(button('Remover limite',self.remove_budget));tools.addStretch();self.body.addLayout(tools)
        budgets={x['category']:x['amount'] for x in self.s.rows('SELECT * FROM budgets WHERE period=?',(self.p,))};spent={x['category']:x['v'] for x in self.s.rows("SELECT category,SUM(amount) AS v FROM tx WHERE period=? AND kind='Despesa' AND status!='Previsto' GROUP BY category",(self.p,))}
        self.budget_rows=sorted(set(budgets)|set(spent));rows=[]
        for cat in self.budget_rows:
            limit=budgets.get(cat);used=spent.get(cat) or 0
            rows.append([cat,money(used),money(limit) if limit is not None else 'Não definido',money(limit-used) if limit is not None else '—',f'{used/limit:.0%}' if limit else '—','Acima do limite' if limit is not None and used>limit else 'Dentro do limite' if limit is not None else 'Definir orçamento'])
        self.budget_table=table(['Categoria','Gasto','Limite','Restante','Utilização','Leitura'],rows);self.budget_table.setMinimumHeight(430);self.body.addWidget(self.budget_table)
    def edit_budget(self):
        f=Form('Orçamento de '+month_label(self.p),[('category','Categoria','Alimentação',self.s.category_names()),('amount','Limite em R$','500,00',None)],self)
        while f.exec():
            try:
                v=f.values();amount=cents(v['amount'])
                if amount<0:raise ValueError('O limite deve ser positivo ou zero.')
                self.s.db.execute('INSERT OR REPLACE INTO budgets VALUES (?,?,?)',(v['category'],self.p,amount));self.s.db.commit();self.render();break
            except ValueError as e:f.error.setText(str(e))
    def remove_budget(self):
        i=self.budget_table.currentRow()
        if i>=0:self.s.db.execute('DELETE FROM budgets WHERE category=? AND period=?',(self.budget_rows[i],self.p));self.s.db.commit();self.render()
    def portfolio(self):
        self.hint('Carteira informada • posições independentes do filtro mensal. Atualize os saldos após aportes, resgates ou valorização. Custo de aquisição ausente não vira rendimento.')
        all_positions=self.s.rows('SELECT * FROM positions ORDER BY value DESC');filter_type=getattr(self,'asset_filter','Todos');self.positions=[p for p in all_positions if filter_type=='Todos' or p['asset_type']==filter_type];total=sum(x['value'] for x in self.positions);known=[x for x in self.positions if x['principal'] is not None]
        self.metrics([('Total informado',money(total),'Consulte as datas na tabela'),('Resultado com custo conhecido',money(sum(x['value']-x['principal'] for x in known)),f'{len(known)} posições com custo informado'),('Reserva de emergência',money(sum(x['value'] for x in self.positions if 'Reserva de emergência' in x['note'])),'Identificada nas observações')])
        tools=FlowLayout();filterbox=QComboBox();filterbox.addItems(['Todos']+sorted(set(p['asset_type'] for p in all_positions)));filterbox.setCurrentText(filter_type);filterbox.currentTextChanged.connect(self.filter_assets);tools.addWidget(filterbox);tools.addWidget(button('+ Adicionar posição',self.edit_position,True));tools.addWidget(button('Editar posição',self.edit_position_selected));tools.addWidget(button('Excluir posição',self.delete_position));tools.addWidget(button('Projetar ativo selecionado',self.project_position));tools.addStretch();self.body.addLayout(tools)
        self.position_table=table(['Ativo','Instituição','Tipo','Custo','Saldo informado','Indexador','Taxa','Liquidez','Registro','Vencimento'],[[x['name'],x['institution'],x['asset_type'],money(x['principal']) if x['principal'] is not None else 'Não informado',money(x['value']),x['rate_mode'],str(x['rate'])+'%',x['liquidity'],x['day'],x['maturity'] or '—'] for x in self.positions]);self.position_table.cellDoubleClicked.connect(lambda *_:self.edit_position_selected());self.body.addWidget(self.position_table)
        w,l=card('Distribuição da carteira');l.addWidget(Chart('bar',[('Saldo',[x['value'] for x in self.positions])],[x['institution'] for x in self.positions]));self.body.addWidget(w)
        w,l=card('Posições históricas da planilha • '+month_label(self.p));snap=self.s.rows('SELECT * FROM snapshots WHERE period=?',(self.p,));l.addWidget(label('Histórico de abertura; não é somado à carteira acima. Tipo do investimento precisa de confirmação.','small',True));l.addWidget(table(['Descrição original','Grupo sugerido','Valor','Data original'],[[x['name'],x['group_name'],money(x['amount']) if x['amount'] is not None else 'Ausente',x['day']] for x in snap]));self.body.addWidget(w)
    def filter_assets(self,value):
        self.asset_filter=value;self.render()
    def edit_position_selected(self):
        i=self.position_table.currentRow()
        if i>=0:self.edit_position(self.positions[i])
    def delete_position(self):
        i=self.position_table.currentRow()
        if i>=0 and QMessageBox.question(self,'Excluir posição','Excluir esta posição da carteira?')==QMessageBox.Yes:self.s.db.execute('DELETE FROM positions WHERE id=?',(self.positions[i]['id'],));self.s.db.commit();self.render()
    def edit_position(self,data=None):
        if not isinstance(data,dict):data={}
        f=Form('Posição de investimento',[('name','Nome do ativo',data.get('name',''),None),('institution','Instituição',data.get('institution',''),None),('asset_type','Tipo',data.get('asset_type','CDB'),['CDB','LCI','LCA','Bitcoin','Cripto a classificar','Reserva de emergência','CDB / liquidez a revisar','Renda fixa a classificar','Ações','ETF','FII','Renda variável','Criptomoeda','Moeda estrangeira','Outros']),('principal','Custo aplicado BRL (opcional)',str(data['principal']/100).replace('.',',') if data.get('principal') is not None else '',None),('value','Saldo na moeda do ativo',str((data.get('native_value') if data.get('native_value') is not None else data.get('value',0))/100).replace('.',','),None),('day','Data de registro',data.get('day',date.today().isoformat()),None),('maturity','Vencimento (opcional)',data.get('maturity',''),None),('asset_group','Classe patrimonial',data.get('asset_group','A classificar'),['A classificar','Renda fixa','Renda variável','Criptomoedas','Moedas estrangeiras','Outros']),('currency','Moeda do saldo',data.get('currency','BRL'),['BRL','USD','EUR','JPY']),('fx_rate','Reais por unidade da moeda',data.get('fx_rate',1),None),('note','Observações',data.get('note',''),None),('rate_mode','Indexador',data.get('rate_mode','Não informada'),['Não informada','Prefixado % a.a.','% CDI','IPCA + % a.a.']),('rate','Taxa (15,10 / 109 / IPCA + spread)',data.get('rate',0),None),('tax','Imposto hipotético sobre lucro %',data.get('tax',0),None),('liquidity','Liquidez',data.get('liquidity','A confirmar'),['A confirmar','Diária','No vencimento'])],self)
        while f.exec():
            try:
                v=f.values();v['value']=cents(v['value']);v['principal']=cents(v['principal']) if v['principal'] else None
                v['rate']=float(v['rate'].replace(',','.'));v['tax']=float(v['tax'].replace(',','.'));v['fx_rate']=float(v['fx_rate'].replace(',','.'))
                if not math.isfinite(v['fx_rate']) or v['fx_rate']<=0:raise ValueError('A cotação precisa ser positiva.')
                if v['currency']=='BRL':v['fx_rate']=1
                v['native_value']=v['value'];v['value']=round(v['native_value']*v['fx_rate'])
                if not math.isfinite(v['rate']) or not -99<v['rate']<=1000 or not 0<=v['tax']<=100:raise ValueError('Revise taxa e imposto (0 a 100%).')
                if not v['name'] or v['value']<0 or (v['principal'] is not None and v['principal']<0):raise ValueError('Nome obrigatório e valores não negativos.')
                date.fromisoformat(v['day'])
                if v['maturity']:date.fromisoformat(v['maturity'])
                keys=list(v);args=list(v.values())
                if data:self.s.db.execute('UPDATE positions SET '+','.join(k+'=?' for k in keys)+' WHERE id=?',args+[data['id']])
                else:self.s.db.execute('INSERT INTO positions ('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',args)
                self.s.db.commit();self.render();break
            except ValueError as e:f.error.setText(str(e))
    def goals(self):
        self.hint('Vincule os ativos destinados a cada objetivo. A análise considera liquidez, vencimento, taxa individual e capacidade de aporte dos últimos três meses com dados.')
        self.body.addWidget(button('+ Nova meta',lambda:self.edit_goal(),True))
        for g in self.s.rows('SELECT * FROM goals ORDER BY id'):
            a=goal_assessment(self.s,g,self.p);w,l=card(g['name']);l.addWidget(label(money(a['base'])+' destinados de '+money(g['target']),'metric'))
            progress=QProgressBar();progress.setRange(0,1000);progress.setValue(min(1000,round(a['base']/max(1,g['target'])*1000)));progress.setTextVisible(False);l.addWidget(progress)
            l.addWidget(label(f"Prazo: {g['deadline']} • {a['months']} aportes considerados • novos aportes a {g['annual']:.2f}% a.a. (hipótese)",'small',True))
            l.addWidget(label('Saldo disponível projetado: '+money(a['projected'])+' • Falta no cenário: '+money(a['missing']),None,True))
            l.addWidget(label('Aporte mensal necessário: '+money(a['need'])+' • Sobra média antes de aportes: '+money(a['capacity']['capacity']),None,True))
            if a['need']>max(0,a['capacity']['capacity']):l.addWidget(label('O aporte necessário supera a sobra média. Revise despesas, renda, prazo ou valor da meta.',None,True))
            if a['unavailable']:l.addWidget(label(money(a['unavailable'])+' projetados ficam fora do saldo disponível por liquidez ou vencimento não confirmados.',None,True))
            if a['warnings']:l.addWidget(label(' / '.join(a['warnings']),'small',True))
            row=FlowLayout();row.addWidget(button('Editar meta',lambda _,x=g:self.edit_goal(x)));row.addWidget(button('Vincular investimentos',lambda _,x=g:self.link_goal(x)));row.addWidget(button('Excluir meta',lambda _,x=g:self.delete_goal(x)));row.addStretch();l.addLayout(row)
            linked=json.loads(self.s.setting('goal-links-'+str(g['id']),'[]'));holdings=[p for p in self.s.rows('SELECT * FROM positions') if p['id'] in linked]
            if holdings:
                series=[];labs=[];today=date.today()
                for idx in range(a['months']+1):
                    k=today.year*12+today.month-1+idx;y,m=divmod(k,12);labs.append(f'{m+1:02d}/{str(y)[2:]}');dt=f'{y:04d}-{m+1:02d}-01'
                    future=sum(position_projection(p,dt,float(self.s.setting('assumed-cdi','10')),float(self.s.setting('assumed-inflation','4')))['net'] for p in holdings if position_projection(p,g['deadline'])['available'])
                    new=forecast(0,g['contribution'],g['annual'],idx)[-1];series.append(future+new)
                l.addWidget(Chart('line',[('Disponível + aportes',series),('Meta',[g['target']]*len(series))],labs,260))
            else:
                vals=forecast(g['saved'],g['contribution'],g['annual'],a['months']);l.addWidget(Chart('line',[('Reservado + aportes',vals),('Meta',[g['target']]*len(vals))],[str(i) for i in range(len(vals))],240))
            self.body.addWidget(w)
        w,l=card('Câmbio BRL → JPY');self.fx_label=label(self.fx_text(),None,True);l.addWidget(self.fx_label);row=QHBoxLayout();self.fx_btn=button('Atualizar cotação',self.fetch_fx,True);row.addWidget(self.fx_btn);row.addWidget(button('Informar cotação manual',self.manual_fx));row.addStretch();l.addLayout(row);l.addWidget(label('Referência diária Frankfurter. Não inclui spread, IOF ou tarifas. Cotação armazenada com data.','small',True));self.body.addWidget(w)
        self.banner('O valor da meta é seu objetivo pessoal de planejamento. Não é uma exigência migratória validada. A conversão para ienes depende do câmbio e dos custos da operação.')
    def link_goal(self,g):
        d=QDialog(self);d.setWindowTitle('Investimentos destinados à meta');d.setMinimumWidth(600);layout=QVBoxLayout(d);layout.addWidget(label('Os ativos vinculados substituem o valor reservado manual nesta meta. Cada ativo pode pertencer a uma meta. A reserva de emergência não é selecionada automaticamente.',None,True))
        selected=json.loads(self.s.setting('goal-links-'+str(g['id']),'[]'));other=set()
        for goal in self.s.rows('SELECT id FROM goals WHERE id!=?',(g['id'],)):other.update(json.loads(self.s.setting('goal-links-'+str(goal['id']),'[]')))
        checks=[]
        for p in self.s.rows('SELECT * FROM positions'):
            b=QCheckBox(p['name']+' • '+money(p['value']));b.setChecked(p['id'] in selected);b.setEnabled(p['id'] not in other)
            if p['id'] in other:b.setText(b.text()+' (vinculado a outra meta)')
            layout.addWidget(b);checks.append((p['id'],b))
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);buttons.accepted.connect(d.accept);buttons.rejected.connect(d.reject);layout.addWidget(buttons)
        if d.exec():self.s.set('goal-links-'+str(g['id']),json.dumps([i for i,b in checks if b.isChecked()]));self.render()
    def project_position(self):
        i=self.position_table.currentRow()
        if i<0:QMessageBox.information(self,'Escolha um ativo','Selecione uma posição na tabela para projetar.');return
        p=self.positions[i];f=Form('Projeção de '+p['name'],[('deadline','Data futura AAAA-MM-DD','2030-03-01',None),('cdi','CDI hipotético % a.a.',self.s.setting('assumed-cdi','10'),None),('inflation','IPCA hipotético % a.a.',self.s.setting('assumed-inflation','4'),None)],self)
        while f.exec():
            try:
                v=f.values();date.fromisoformat(v['deadline']);cdi=float(v['cdi'].replace(',','.'));inflation=float(v['inflation'].replace(',','.'))
                if not 0<=cdi<=100 or not -20<=inflation<=100:raise ValueError('Revise os indexadores hipotéticos.')
                result=position_projection(p,v['deadline'],cdi,inflation);self.s.set('assumed-cdi',cdi);self.s.set('assumed-inflation',inflation)
                d=QDialog(self);d.setWindowTitle('Resultado estimado');d.resize(700,500);l=QVBoxLayout(d);l.addWidget(label(p['name'],'title'));l.addWidget(label('Saldo líquido estimado: '+money(result['net']),'metric'));l.addWidget(label('Bruto: '+money(result['gross'])+' • Imposto hipotético: '+money(result['tax']),None,True));l.addWidget(label('Indexador: '+p['rate_mode']+' • Taxa: '+str(p['rate'])+' • Imposto configurado: '+str(p['tax'])+'%',None,True))
                labs=[];values=[];start=date.fromisoformat(p['day']);end=date.fromisoformat(v['deadline']);n=max(0,(end.year-start.year)*12+end.month-start.month)
                if n>600:raise ValueError('Prazo máximo de 50 anos.')
                for offset in range(n+1):
                    key=start.year*12+start.month-1+offset;y,m=divmod(key,12);day=f'{y:04d}-{m+1:02d}-01';labs.append(day[2:7]);values.append(position_projection(p,day,cdi,inflation)['net'])
                l.addWidget(Chart('line',[('Saldo estimado',values)],labs));l.addWidget(label(' '.join(result['warnings'])+' Prefixado/IPCA: dias corridos / 365. CDI: dias de segunda a sexta / 252, sem feriados. Imposto é uma hipótese manual; IOF e tarifas não calculados. Valores nominais.','small',True));l.addWidget(button('Fechar',d.accept));d.exec();break
            except (ValueError,OverflowError) as e:f.error.setText(str(e))
    def analysis(self):
        self.hint('Diagnósticos calculados a partir dos seus registros e premissas. Não usam API de IA nem enviam informações financeiras para servidores.')
        cap=recent_capacity(self.s,self.p);self.metrics([('Receita média',money(cap['income']),'Últimos três meses com dados'),('Despesa média',money(cap['expense']),'Exclui aportes e transferências'),('Sobra antes de aportes',money(cap['capacity']),'Base para avaliar a capacidade futura')])
        for title,text in insights(self.s,self.p):
            w,l=card(title);l.addWidget(label(text,None,True));self.body.addWidget(w)
        w,l=card('Fluxo projetado dos próximos 12 meses');vals=[];labs=[];rows=[];cumulative=0;y,m=map(int,self.p.split('-'))
        for i in range(1,13):
            key=y*12+m-1+i;year,month=divmod(key,12);period=f'{year:04d}-{month+1:02d}';planned=self.s.rows("SELECT kind,SUM(amount) n FROM tx WHERE period=? AND status='Previsto' GROUP BY kind",(period,));rules={r['kind']:r['n'] or 0 for r in planned}
            inc=rules.get('Receita',cap['income']);exp=rules.get('Despesa',cap['expense']);aporte=rules.get('Aporte',0);net=inc-exp-aporte+rules.get('Resgate',0);cumulative+=net;vals.append(cumulative);labs.append(period[2:]);rows.append([period,money(inc),money(exp),money(aporte),money(net),money(cumulative)])
        l.addWidget(Chart('line',[('Fluxo acumulado',vals)],labs));l.addWidget(table(['Mês','Receitas','Despesas','Aportes','Fluxo mensal','Acumulado'],rows));l.addWidget(label('Para cada tipo: usa o total previsto cadastrado quando existente; caso contrário, repete a média histórica para receitas e despesas. Acumulado parte de zero e não representa patrimônio. Cadastre todas as recorrências do tipo para substituir a média integral.','small',True));self.body.addWidget(w)
    def edit_goal(self,g=None):
        if not isinstance(g,dict):g={}
        f=Form('Planejar meta',[('name','Nome',g.get('name',''),None),('target','Objetivo em R$',str(g.get('target',0)/100).replace('.',','),None),('saved','Valor já reservado em R$',str(g.get('saved',0)/100).replace('.',','),None),('deadline','Prazo AAAA-MM-DD',g.get('deadline','2030-03-01'),None),('contribution','Aporte mensal R$',str(g.get('contribution',0)/100).replace('.',','),None),('annual','Taxa líquida hipotética % a.a.',g.get('annual',0),None)],self)
        while f.exec():
            try:
                v=f.values()
                for k in ['target','saved','contribution']:v[k]=cents(v[k])
                v['annual']=float(v['annual'].replace(',','.'));date.fromisoformat(v['deadline'])
                if abs(date.fromisoformat(v['deadline']).year-date.today().year)>50:raise ValueError('Use um prazo de até 50 anos.')
                if not v['name'] or v['target']<=0 or v['saved']<0 or v['contribution']<0 or not -99<=v['annual']<=100:raise ValueError('Revise nome, valores e taxa (-99 a 100% a.a.).')
                if sum(x['saved'] for x in self.s.rows('SELECT saved FROM goals WHERE id!=?',(g.get('id',0),)))+v['saved']>sum(x['value'] for x in self.s.rows('SELECT value FROM positions')):
                    if QMessageBox.question(self,'Reservas das metas','A soma reservada nas metas supera a carteira cadastrada. Salvar mesmo assim?')!=QMessageBox.Yes:continue
                keys=list(v);args=list(v.values())
                if g:self.s.db.execute('UPDATE goals SET '+','.join(k+'=?' for k in keys)+' WHERE id=?',args+[g['id']])
                else:self.s.db.execute('INSERT INTO goals ('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',args)
                self.s.db.commit();self.render();break
            except ValueError as e:f.error.setText(str(e))
    def delete_goal(self,g):
        if len(self.s.rows('SELECT id FROM goals'))<=1:QMessageBox.information(self,'Meta principal','Mantenha pelo menos uma meta. Você pode editar seu nome e seus valores.');return
        if QMessageBox.question(self,'Excluir meta','Excluir esta meta? Isso não altera a carteira.')==QMessageBox.Yes:self.s.db.execute('DELETE FROM goals WHERE id=?',(g['id'],));self.s.db.commit();self.render()
    def fx_text(self):
        data=json.loads(self.s.setting('fx','{}'))
        if not data:return 'Nenhuma cotação consultada. Atualize pela internet ou informe uma hipótese manual.'
        rate=data['rate'];goal=self.s.rows('SELECT * FROM goals ORDER BY id LIMIT 1')[0]
        return f"1 BRL = {rate:.4f} JPY • data: {data.get('date','não informada')} • {data.get('source','Frankfurter')}\nMeta de {money(goal['target'])} equivale a aproximadamente ¥ {goal['target']/100*rate:,.0f}.\n5.000.000 JPY equivalem a {money(round(5000000/rate*100))}, antes dos custos de conversão."
    def fetch_fx(self):
        if self.fx and self.fx.isRunning():return
        self.fx_btn.setEnabled(False);self.fx_label.setText('Consultando cotação diária…');self.fx=FXWorker();self.fx.done.connect(self.fx_done);self.fx.start()
    def fx_done(self,data):
        if 'error' in data:QMessageBox.warning(self,'Cotação indisponível','Não foi possível consultar. A cotação anterior foi mantida.\n'+data['error'])
        else:data['source']='Frankfurter, referência diária';self.s.set('fx',json.dumps(data))
        if self.page=='Metas e câmbio':self.fx_btn.setEnabled(True);self.fx_label.setText(self.fx_text())
    def manual_fx(self):
        f=Form('Hipótese de câmbio',[('rate','Ienes por 1 real','',None)],self)
        while f.exec():
            try:
                rate=float(f.values()['rate'].replace(',','.'))
                if not math.isfinite(rate) or not 0<rate<10000:raise ValueError('Informe uma cotação positiva válida.')
                self.s.set('fx',json.dumps({'rate':rate,'date':date.today().isoformat(),'source':'Hipótese manual'}));self.render();break
            except ValueError as e:f.error.setText(str(e))
    def simulations(self):
        self.hint('Planejamento por cenário • simulação mensal com aportes no fim de cada mês. Todos os parâmetros são editáveis e não alteram lançamentos ou investimentos.')
        w,l=card('Premissas do cenário');grid=QGridLayout();self.sim={}
        total=sum(x['value'] for x in self.s.rows('SELECT value FROM positions'));saved=json.loads(self.s.setting('simulation','{}'))
        specs=[('initial','Capital inicial R$',str(total/100).replace('.',',')),('start','Primeiro mês AAAA-MM','2026-10'),('end','Último mês AAAA-MM','2030-03'),('early','Aporte até dez/2026 R$','1000,00'),('later','Aporte desde jan/2027 R$','1500,00'),('rate','Retorno líquido hipotético % ao mês','1,05'),('bonus','Bônus em dezembro de 2026 a 2029 R$','3000,00'),('reserve','Reserva preservada R$','5000,00'),('withdraw','Gasto extraordinário R$','8000,00'),('withdraw_month','Mês do gasto AAAA-MM','2028-01'),('income','Receita mensal futura R$','5000,00'),('expense','Despesa mensal futura R$','3500,00')]
        for i,(key,title,default) in enumerate(specs):
            col=i%2;row=(i//2)*2;grid.addWidget(label(title.replace(' AAAA-MM',' (mês/ano)'),'small',True),row,col);edit=__import__('widgets').MonthField(str(saved.get(key,default))) if key in ['start','end','withdraw_month'] else QLineEdit(str(saved.get(key,default)));edit.setAccessibleName(title);grid.addWidget(edit,row+1,col);self.sim[key]=edit
        l.addLayout(grid);self.exclude_reserve=QCheckBox('Preservar a reserva de emergência fora do capital simulado');self.exclude_reserve.setChecked(saved.get('exclude_reserve',True));l.addWidget(self.exclude_reserve)
        self.include_withdraw=QCheckBox('Incluir o gasto extraordinário na projeção');self.include_withdraw.setChecked(saved.get('include_withdraw',False));l.addWidget(self.include_withdraw)
        l.addWidget(button('Calcular e salvar premissas',self.calculate_sim,True));l.addWidget(button('Usar médias dos últimos três meses',self.use_recent_sim));self.body.addWidget(w);self.sim_out=QWidget();self.sim_layout=QVBoxLayout(self.sim_out);self.sim_layout.setContentsMargins(0,0,0,0);self.sim_layout.setSpacing(16);self.body.addWidget(self.sim_out);self.sim_error=label('','negative',True);self.body.addWidget(self.sim_error);self.calculate_sim()
    def use_recent_sim(self):
        cap=recent_capacity(self.s,self.p)
        self.sim['income'].setText(str(cap['income']/100).replace('.',','));self.sim['expense'].setText(str(cap['expense']/100).replace('.',','));self.calculate_sim()
    def calculate_sim(self):
        self.sim_error.clear()
        try:
            v={k:e.text().strip() for k,e in self.sim.items()};start=date.fromisoformat(v['start']+'-01');end=date.fromisoformat(v['end']+'-01');n=(end.year-start.year)*12+end.month-start.month+1
            if not 1<=n<=120:raise ValueError('Escolha um intervalo de 1 a 120 meses.')
            annual_month=float(v['rate'].replace(',','.'))/100
            if not math.isfinite(annual_month) or not -.2<=annual_month<=.2:raise ValueError('Use uma taxa mensal entre -20% e 20%.')
            amounts={k:cents(v[k]) for k in ['initial','early','later','bonus','reserve','withdraw','income','expense']}
            if any(x<0 for x in amounts.values()):raise ValueError('Os valores devem ser não negativos.')
            withdrawal_date=date.fromisoformat(v['withdraw_month']+'-01')
            if self.include_withdraw.isChecked() and not start<=withdrawal_date<=end:raise ValueError('O mês do gasto deve estar dentro do intervalo simulado.')
            initial=amounts['initial']-(amounts['reserve'] if self.exclude_reserve.isChecked() else 0)
            if initial<0:raise ValueError('A reserva preservada supera o capital inicial.')
            rates=[0,annual_month,annual_month-.005];names=['Sem rendimento','Taxa informada','Taxa mensal −0,5 p.p.'];series=[];rows=[]
            for rate in rates:
                balance=initial;values=[];paid=0;bonus_sum=0;withdraw_sum=0
                for i in range(n):
                    key=start.year*12+start.month-1+i;y,m=divmod(key,12);m+=1;p=f'{y:04d}-{m:02d}';contribution=amounts['early'] if p<='2026-12' else amounts['later'];bonus=amounts['bonus'] if m==12 and 2026<=y<=2029 else 0
                    withdrawal=amounts['withdraw'] if self.include_withdraw.isChecked() and p==v['withdraw_month'] else 0
                    earnings=round(balance*rate);balance+=earnings+contribution+bonus-withdrawal;paid+=contribution;bonus_sum+=bonus;withdraw_sum+=withdrawal;values.append(balance)
                    if len(series)==1:rows.append([p,contribution,bonus,earnings,withdrawal,balance,amounts['income']-amounts['expense']-contribution-bonus])
                series.append(values)
            while self.sim_layout.count():
                item=self.sim_layout.takeAt(0)
                if item.widget():item.widget().deleteLater()
            w,l=card('Resultado do cenário');final=series[1][-1];target=self.s.rows('SELECT target FROM goals ORDER BY id LIMIT 1')[0]['target'];l.addWidget(label(money(final),'metric'));l.addWidget(label(f"Capital inicial simulado: {money(initial)} • Aportes: {money(paid)} • Bônus: {money(bonus_sum)} • Retiradas: {money(withdraw_sum)}",None,True));l.addWidget(label(f"Taxa anual equivalente da hipótese mensal: {((1+annual_month)**12-1)*100:.2f}% a.a. • Margem sobre a meta de {money(target)}: {money(final-target)}",None,True));l.addWidget(Chart('line',list(zip(names,series)),[r[0][2:] for r in rows],280));self.sim_layout.addWidget(w)
            if rows:
                dec=next((r for r in rows if r[0]=='2026-12'),None)
                if dec:l.addWidget(label('Saldo projetado em dezembro/2026: '+money(dec[5]),None,True))
            warning='Cenários hipotéticos. A taxa é aplicada a todo o capital simulado, inclusive cripto se incluída. O aplicativo não prevê o preço do Bitcoin nem uma janela ideal de venda. A reserva preservada não rende dentro desta simulação. Bônus devem ter uma fonte de renda própria.'
            box,bl=card('Viabilidade do fluxo');bl.addWidget(label(warning,None,True));negative=[r for r in rows if r[6]<0]
            bl.addWidget(label(f"{len(negative)} meses têm aportes + bônus superiores à receita menos despesas informadas. Ajuste o orçamento ou inclua a renda extraordinária na hipótese de receita.",None,True));self.sim_layout.addWidget(box)
            box,bl=card('Memória de cálculo mensal');bl.addWidget(table(['Mês','Aporte','Bônus','Rendimento','Retirada','Saldo projetado','Sobra de caixa*'],[[r[0]]+[money(x) for x in r[1:]] for r in rows]));bl.addWidget(label('* Receita mensal − despesa mensal − aporte − bônus. Não inclui o gasto extraordinário, que sai do capital simulado. Valores nominais, sem ajuste inflacionário.','small',True));self.sim_layout.addWidget(box)
            v['exclude_reserve']=self.exclude_reserve.isChecked();v['include_withdraw']=self.include_withdraw.isChecked();self.s.set('simulation',json.dumps(v))
        except (ValueError,OverflowError) as e:
            self.sim_error.setText(str(e))
            while self.sim_layout.count():
                item=self.sim_layout.takeAt(0)
                if item.widget():item.widget().deleteLater()
    def automatic_backup(self):
        try:
            self.s.daily_backup()
            self.backup_error=''
        except Exception as e:
            self.backup_error=str(e)
            if '--smoke-test' not in sys.argv:QMessageBox.warning(self,'Backup automático não realizado','Não foi possível salvar a cópia. Escolha outra pasta em Dados e backup.\n'+str(e))
    def choose_backup_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Pasta para cópias automáticas',str(self.s.path.parent))
        if folder:
            self.s.set('backup-folder',folder);self.automatic_backup();self.render()
    def update_avatar(self):
        import base64
        data=self.s.setting('profile-photo')
        if data:
            pix=QPixmap()
            if pix.loadFromData(base64.b64decode(data)):self.avatar.setPixmap(pix.scaled(48,48,Qt.KeepAspectRatio,Qt.SmoothTransformation));return
        self.avatar.clear();self.avatar.setText(self.s.setting('display-name','H')[:1].upper());self.avatar.setAlignment(Qt.AlignCenter);self.avatar.setStyleSheet('background:#24473e;border-radius:24px;color:white;font-size:24px;')
    def profile(self):
        self.hint('Seu perfil fica no banco local e acompanha os backups. Nome, idade, profissão e foto são opcionais.')
        w,l=card('Seu perfil');self.profile_fields={};form=QFormLayout()
        for key,title in [('display-name','Nome'),('profile-age','Idade'),('profile-profession','Profissão')]:
            edit=QLineEdit(self.s.setting(key));edit.setAccessibleName(title);form.addRow(title,edit);self.profile_fields[key]=edit
        l.addLayout(form);photo=QLabel();photo.setFixedSize(120,120);photo.setAlignment(Qt.AlignCenter)
        import base64
        data=self.s.setting('profile-photo')
        if data:
            pix=QPixmap();pix.loadFromData(base64.b64decode(data));photo.setPixmap(pix.scaled(120,120,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        else:photo.setText('Sem foto')
        l.addWidget(photo);row=FlowLayout();row.addWidget(button('Escolher foto',self.choose_photo));row.addWidget(button('Remover foto',self.remove_photo));row.addStretch();l.addLayout(row);l.addWidget(button('Salvar perfil',self.save_profile,True));self.body.addWidget(w)
    def choose_photo(self):
        path,_=QFileDialog.getOpenFileName(self,'Foto de perfil','','Imagem (*.png *.jpg *.jpeg *.webp)')
        if not path:return
        try:
            if Path(path).stat().st_size>10*1024*1024:raise ValueError('Escolha uma imagem de até 10 MB.')
            im=QImage(path)
            if im.isNull():raise ValueError('Não foi possível abrir esta imagem.')
            im=im.scaled(256,256,Qt.KeepAspectRatio,Qt.SmoothTransformation)
            from PySide6.QtCore import QBuffer,QByteArray,QIODevice
            import base64
            buffer=QBuffer();buffer.open(QIODevice.WriteOnly);im.save(buffer,'PNG');self.s.set('profile-photo',base64.b64encode(bytes(buffer.data())).decode('ascii'));self.update_avatar();self.render()
        except (ValueError,OSError) as e:QMessageBox.warning(self,'Foto de perfil',str(e))
    def remove_photo(self):self.s.set('profile-photo','');self.update_avatar();self.render()
    def save_profile(self):
        values={k:w.text().strip() for k,w in self.profile_fields.items()}
        if len(values['display-name'])>60 or len(values['profile-profession'])>100:QMessageBox.warning(self,'Perfil','Nome: até 60 caracteres. Profissão: até 100.');return
        age=values['profile-age']
        if age and (not age.isdigit() or not 0<=int(age)<=120):QMessageBox.warning(self,'Perfil','Idade deve ser um número de 0 a 120 ou ficar vazia.');return
        for k,v in values.items():self.s.set(k,v)
        self.profile_name.setText(values['display-name'] or 'Meu planejamento');self.update_avatar();QMessageBox.information(self,'Perfil','Perfil salvo neste computador.')
    def accounts(self):
        self.hint('Cadastre somente saldo em conta, separado de CDBs e outros investimentos. O saldo conferido incorpora os registros já existentes; novos lançamentos confirmados na conta passam a movimentá-lo.')
        self.bank_rows=self.s.rows('SELECT * FROM accounts ORDER BY institution,name');total=sum(self.s.account_balance(a) for a in self.bank_rows)
        self.metrics([('Contas cadastradas',str(len(self.bank_rows)),'Instituições e contas informadas'),('Saldo total em BRL',money(total),'Inclui conversão manual de moeda estrangeira')])
        row=FlowLayout();row.addWidget(button('+ Adicionar conta',self.edit_account,True));row.addWidget(button('Conferir ou editar saldo',self.edit_account_selected));row.addWidget(button('Excluir conta',self.delete_account));row.addStretch();self.body.addLayout(row)
        self.bank_table=table(['Conta','Banco / instituição','Moeda','Saldo na moeda','Equivalente BRL','Cotação BRL/un.','Conferência'],[[a['name'],a['institution'],a['currency'],f"{self.s.account_balance(a)/a['fx_rate']/100:,.2f}",money(self.s.account_balance(a)),a['fx_rate'],a['day']] for a in self.bank_rows]);self.bank_table.cellDoubleClicked.connect(lambda *_:self.edit_account_selected());self.body.addWidget(self.bank_table)
        w,l=card('Saldo por instituição');groups={}
        for a in self.bank_rows:groups[a['institution']]=groups.get(a['institution'],0)+self.s.account_balance(a)
        l.addWidget(Chart('bar',[('Saldo BRL',list(groups.values()))],list(groups)));self.body.addWidget(w)
        self.hint('Lançamentos são registrados em reais. Para conta em moeda estrangeira, a cotação manual converte o saldo informado para BRL; os movimentos são mantidos em BRL. Confira o saldo após operações de câmbio. Não é conciliação automática com o banco.')
    def edit_account_selected(self):
        i=self.bank_table.currentRow()
        if i>=0:self.edit_account(self.bank_rows[i])
    def edit_account(self,a=None):
        if not isinstance(a,dict):a={}
        current=self.s.account_balance(a)/a['fx_rate'] if a else 0
        f=Form('Saldo e dados da conta',[('name','Nome da conta',a.get('name',''),None),('institution','Banco / instituição',a.get('institution',''),None),('currency','Moeda',a.get('currency','BRL'),['BRL','USD','EUR','JPY']),('balance','Saldo conferido na moeda',str(round(current)/100).replace('.',','),None),('fx_rate','Reais por unidade da moeda',a.get('fx_rate',1),None),('day','Data de conferência AAAA-MM-DD',date.today().isoformat(),None),('note','Observações',a.get('note',''),None)],self)
        while f.exec():
            try:
                v=f.values();v['balance']=cents(v['balance']);v['fx_rate']=float(v['fx_rate'].replace(',','.'));date.fromisoformat(v['day'])
                if not v['name'] or not v['institution']:raise ValueError('Preencha nome da conta e instituição.')
                if not math.isfinite(v['fx_rate']) or v['fx_rate']<=0:raise ValueError('Cotação deve ser positiva.')
                if v['currency']=='BRL':v['fx_rate']=1
                v['ledger_after']=self.s.rows('SELECT COALESCE(MAX(id),0) n FROM tx')[0]['n'];keys=list(v);args=list(v.values())
                with self.s.db:
                    if a:
                        self.s.db.execute('UPDATE accounts SET '+','.join(k+'=?' for k in keys)+' WHERE id=?',args+[a['id']]);self.s.db.execute('UPDATE tx SET account=? WHERE account=?',(v['name'],a['name']));self.s.db.execute('UPDATE tx SET target_account=? WHERE target_account=?',(v['name'],a['name']))
                    else:self.s.db.execute('INSERT INTO accounts ('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',args)
                self.render();break
            except (ValueError,sqlite3.Error) as e:f.error.setText(str(e))
    def delete_account(self):
        i=self.bank_table.currentRow()
        if i<0:return
        a=self.bank_rows[i]
        if self.s.rows('SELECT id FROM tx WHERE account=? OR target_account=?',(a['name'],a['name'])):QMessageBox.information(self,'Conta com histórico','Esta conta tem lançamentos vinculados. Reclassifique os lançamentos antes de excluir a conta.');return
        if QMessageBox.question(self,'Excluir conta','Excluir esta conta cadastrada?')==QMessageBox.Yes:self.s.db.execute('DELETE FROM accounts WHERE id=?',(a['id'],));self.s.db.commit();self.render()
    def reports(self):
        self.hint('Relatórios por competência e fotografia atual do patrimônio. Valores de moedas estrangeiras usam a cotação manual cadastrada no ativo ou conta.')
        self.body.addWidget(button('Exportar relatório em PDF',self.export_report,True));self.report_charts=[]
        groups=allocation(self.s);self.metrics([('Patrimônio líquido',money(sum(groups.values())-__import__('ledger').Ledger(self.s).outstanding()),'Ativos menos dívida de cartões'),('Ativos brutos',money(sum(groups.values())),'Contas + posições, após conversão para BRL'),('Investimentos',money(sum(p['value'] for p in self.s.rows('SELECT value FROM positions'))),'Posições informadas'),('Bancos e contas',money(sum(self.s.account_balance(a) for a in self.s.rows('SELECT * FROM accounts'))),'Saldo conferido + novos movimentos')])
        w,l=card('Distribuição por classe');chart=Chart('donut',[(k,[v]) for k,v in groups.items() if v>0]);l.addWidget(chart);self.report_charts.append(chart);l.addWidget(table(['Classe patrimonial','Valor BRL','Participação'],[[k,money(v),f'{v/sum(groups.values()):.1%}' if sum(groups.values()) else '—'] for k,v in groups.items()]));self.body.addWidget(w)
        periods=[p for p in self.s.periods() if p<=self.p][-12:];data=[self.s.summary(p) for p in periods];w,l=card('Receitas, consumo e aportes');chart=Chart('bar',[('Receitas',[d['Receita'] for d in data]),('Despesas',[d['Despesa'] for d in data]),('Aportes',[d['Aporte'] for d in data])],[p[2:] for p in periods],260);l.addWidget(chart);self.report_charts.append(chart);l.addWidget(table(['Mês','Receitas','Despesas','Aportes','Resgates','Fluxo disponível'],[[p]+[money(d[k]) for k in ['Receita','Despesa','Aporte','Resgate','livre']] for p,d in zip(periods,data)]));self.body.addWidget(w)
        currencies={};institutions={}
        for p in self.s.rows('SELECT * FROM positions'):
            currencies[p['currency']]=currencies.get(p['currency'],0)+p['value'];institutions[p['institution']]=institutions.get(p['institution'],0)+p['value']
        for a in self.s.rows('SELECT * FROM accounts'):
            currencies[a['currency']]=currencies.get(a['currency'],0)+self.s.account_balance(a);institutions[a['institution']]=institutions.get(a['institution'],0)+self.s.account_balance(a)
        for title,values in [('Exposição por moeda (equivalente BRL)',currencies),('Distribuição por instituição',institutions)]:
            w,l=card(title);chart=Chart('bar',[('Valor BRL',list(values.values()))],list(values),240);l.addWidget(chart);self.report_charts.append(chart);l.addWidget(table(['Item','Valor BRL'],[[k,money(v)] for k,v in values.items()]));self.body.addWidget(w)
        w,l=card('Agenda de vencimentos');positions=self.s.rows("SELECT * FROM positions WHERE maturity!='' ORDER BY maturity");l.addWidget(table(['Ativo','Tipo','Vencimento','Saldo informado'],[[p['name'],p['asset_type'],p['maturity'],money(p['value'])] for p in positions]));self.body.addWidget(w)
    def export_report(self):
        path,_=QFileDialog.getSaveFileName(self,'Relatório PDF','Horizonte-'+self.p+'.pdf','PDF (*.pdf)')
        if not path:return
        try:
            from PySide6.QtPrintSupport import QPrinter
            from html import escape
            from PySide6.QtCore import QUrl
            doc=QTextDocument();html='<h1>Horizonte — relatório financeiro</h1><p>Competência: '+escape(month_label(self.p))+' • Gerado em '+date.today().isoformat()+'</p>'
            if self.s.setting('demo')=='1':html+='<p>DEMONSTRAÇÃO: dados fictícios.</p>'
            for child in self.scroll.widget().findChildren(QTableWidget):
                html+='<table border="1" cellpadding="6" cellspacing="0" width="100%"><tr>'
                for col in range(child.columnCount()):html+='<th>'+escape(child.horizontalHeaderItem(col).text())+'</th>'
                html+='</tr>'
                for row in range(child.rowCount()):
                    html+='<tr>'
                    for col in range(child.columnCount()):html+='<td>'+escape(child.item(row,col).text() if child.item(row,col) else '')+'</td>'
                    html+='</tr>'
                html+='</table><br>'
            for i,chart in enumerate(self.report_charts):
                url=QUrl('chart'+str(i));doc.addResource(QTextDocument.ImageResource,url,chart.grab().toImage());html+=f'<p><img src="chart{i}" width="640" /></p>'
            html+='<p>Valores informados. Conversões por cotação cadastrada; não incluem tarifas. O fluxo não representa saldo bancário. Patrimônio considera saldos em conta e posições de investimento, que devem ser cadastrados sem duplicação.</p>';doc.setHtml(html);printer=QPrinter(QPrinter.HighResolution);printer.setOutputFormat(QPrinter.PdfFormat);printer.setOutputFileName(path);doc.print_(printer);QMessageBox.information(self,'Relatório','PDF salvo.')
        except Exception as e:QMessageBox.warning(self,'Relatório',str(e))

    def data_page(self):
        self.hint('Seu banco fica neste computador. Faça cópias de segurança antes de revisar grandes conjuntos de registros.')
        w,l=card('Importação e conferência');l.addWidget(label('A importação opcional reconhece o layout mensal documentado. Saldos de abertura ficam separados das receitas, saídas para Sofisa/Cofrinho são sugestões de aporte e todos os registros entram como A revisar.','subtitle',True));l.addWidget(button('Importar planilha Excel',self.import_file,True));self.body.addWidget(w)
        reports=self.s.rows('SELECT * FROM imports ORDER BY stamp DESC')
        if reports:
            w,l=card('Relatório da última importação');text=QTextEdit();text.setReadOnly(True);text.setPlainText(reports[0]['report']);text.setMinimumHeight(270);l.addWidget(text);self.body.addWidget(w)
        w,l=card('Cópias e portabilidade');row=FlowLayout();row.addWidget(button('Criar backup .sqlite',self.backup));row.addWidget(button('Restaurar backup',self.restore));row.addWidget(button('Pasta de backup automático',self.choose_backup_folder));row.addWidget(button('Exportar lançamentos CSV',self.export_csv));l.addLayout(row);l.addWidget(label('Local dos dados: '+str(self.s.path),'small',True));l.addWidget(label('Backup automático: '+self.s.setting('backup-folder',str(self.s.path.parent/'backups'))+' • Última cópia: '+self.s.setting('last-backup','ainda não realizada'),'small',True));l.addWidget(label('Backup inclui perfil, foto, contas, lançamentos, metas, carteira, limites e premissas. Arquivos locais não são criptografados. A exportação CSV contém apenas lançamentos.','small',True));self.body.addWidget(w)
        w,l=card('Sobre esta versão');l.addWidget(label('Horizonte '+VERSION+' • aplicativo desktop para Windows. Não exige navegador, conta, assinatura ou API paga. Câmbio é consultado apenas quando solicitado. Não possui conexão bancária automática, sincronização, tributação automática ou cotação de cripto em tempo real.','subtitle',True));l.addWidget(label('Fontes de referência: Mobills (organização por categorias e orçamento); Financial Budget (realizado, premissas e previsões); Frankfurter (câmbio diário). Interface própria.','small',True));self.body.addWidget(w)
    def import_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Importar planilha','','Excel (*.xlsx)')
        if not path:return
        try:
            report=self.s.import_excel(path);self.refresh_periods();self.render();QMessageBox.information(self,'Importação concluída',report)
        except Exception as e:QMessageBox.warning(self,'Não foi possível importar',str(e))
    def backup(self):
        path,_=QFileDialog.getSaveFileName(self,'Criar backup','Horizonte-'+date.today().isoformat()+'.sqlite','SQLite (*.sqlite)')
        if path:
            try:self.s.backup(path);QMessageBox.information(self,'Backup','Cópia de segurança criada.')
            except Exception as e:QMessageBox.warning(self,'Backup',str(e))
    def restore(self):
        path,_=QFileDialog.getOpenFileName(self,'Restaurar backup','','SQLite (*.sqlite)')
        if not path:return
        check=None
        try:
            check=sqlite3.connect('file:'+Path(path).as_posix()+'?mode=ro',uri=True)
            if check.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Banco corrompido.')
            expected={'tx','snapshots','positions','goals','settings','budgets','imports','accounts'};actual={r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not expected<=actual:raise ValueError('Este arquivo não é um backup do Horizonte.')
            # Validate every column used by this version before replacing the database.
            for name in expected:
                required={r[1] for r in self.s.db.execute('PRAGMA table_info('+name+')')};found={r[1] for r in check.execute('PRAGMA table_info('+name+')')}
                if not required<=found:raise ValueError('Backup incompatível: '+name)
            if not check.execute('SELECT 1 FROM goals').fetchone():raise ValueError('Backup sem meta principal.')
            if QMessageBox.question(self,'Restaurar dados','Substituir os dados atuais pelo backup? Uma cópia automática dos dados atuais será guardada na pasta de dados.')!=QMessageBox.Yes:return
            auto=self.s.path.parent/('antes-restauracao-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.sqlite');self.s.backup(auto);check.backup(self.s.db);self.s.db.commit();self.refresh_periods();self.render();QMessageBox.information(self,'Restauração','Dados restaurados. Backup anterior: '+str(auto))
        except Exception as e:QMessageBox.warning(self,'Restauração',str(e))
        finally:
            if check:check.close()
    def export_csv(self):
        path,_=QFileDialog.getSaveFileName(self,'Exportar todos os lançamentos','lancamentos.csv','CSV (*.csv)')
        if not path:return
        try:
            with open(path,'w',encoding='utf-8-sig',newline='') as f:
                writer=csv.writer(f,delimiter=';');writer.writerow(['Competência','Data','Descrição','Tipo','Categoria','Valor BRL','Conta','Situação','Origem','Observações'])
                for x in self.s.rows('SELECT * FROM tx ORDER BY period,id'):
                    values=[x['period'],x['day'],x['description'],x['kind'],x['category'],f"{x['amount']/100:.2f}".replace('.',',') if x['amount'] is not None else '',x['account'],x['status'],x['source'],x['note']]
                    writer.writerow([("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v) for v in values])
            QMessageBox.information(self,'Exportação','Lançamentos exportados.')
        except OSError as e:QMessageBox.warning(self,'Exportação',str(e))
    def closeEvent(self,event):
        if self.fx and self.fx.isRunning():self.fx.requestInterruption();self.fx.wait(16000)
        try:self.s.daily_backup()
        except OSError:pass
        self.s.db.close();event.accept()

def main():
    app=QApplication(sys.argv)
    for fontfile in ['segoeui.ttf','segoeuib.ttf']:
        QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/fontfile))
    app.setFont(QFont('Segoe UI',10));app.setStyle('Fusion');app.setStyleSheet(STYLE)
    folder=Path(os.environ.get('HORIZONTE_DATA_DIR',str(Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / ('HorizonteDemo' if '--demo' in sys.argv else 'Horizonte'))));folder.mkdir(parents=True,exist_ok=True);database=folder/'financas.sqlite'
    def ui_error(kind,error,tb):
        log=folder/'interface-error.txt'
        with log.open('a',encoding='utf-8') as output:output.write(datetime.now().isoformat()+'\n'+''.join(traceback.format_exception(kind,error,tb))+'\n')
        if '--smoke-test' in sys.argv:app.exit(1)
        else:QMessageBox.critical(None,'Não foi possível concluir a ação','A ação encontrou um erro. Detalhes foram registrados em '+str(log)+'\n'+str(error))
    sys.excepthook=ui_error
    lock=QLockFile(str(folder/'session.lock'));lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        QMessageBox.information(None,'Horizonte já está aberto','Feche a outra janela do Horizonte antes de abrir este banco novamente.');return
    if '--demo' not in sys.argv and not database.exists() and (ROOT/'seed.sqlite').exists():shutil.copy2(ROOT/'seed.sqlite',database)
    store=Store(database)
    if '--demo' in sys.argv:
        from demo import seed_demo
        seed_demo(store)
    from workspace import ModernWindow
    win=ModernWindow(store);win.show()
    if '--smoke-test' in sys.argv:
        def smoke():
            try:
                for page in list(win.nav):win.go(page);app.processEvents()
                win.go('Visão geral');app.processEvents();win.grab().save(str(folder/'screenshot.png'));(folder/'smoke-ok.txt').write_text('Todas as telas renderizadas.',encoding='utf-8');win.close()
            except Exception:(folder/'smoke-error.txt').write_text(traceback.format_exc(),encoding='utf-8');app.exit(1)
        QTimer.singleShot(600,smoke)
    sys.exit(app.exec())
if __name__=='__main__':
    sys.modules.setdefault('app',sys.modules[__name__])
    main()

    
