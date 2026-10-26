"""Interface desktop 0.2: fluxos de controle financeiro e linguagem visual HIG."""
import base64, calendar, json, shutil, sqlite3, uuid
from datetime import date,datetime,timedelta
from pathlib import Path
from PySide6.QtCore import Qt,QDate,QTimer,QPropertyAnimation,QEasingCurve,QPoint
from PySide6.QtGui import QAction,QKeySequence,QFont,QPixmap,QPainter,QColor,QPalette
from PySide6.QtWidgets import *
import app as ui
from core import *
from ledger import Ledger,add_month,month_day
from finance import allocation,goal_assessment,recent_capacity,insights
from design import theme,tokens,icon,InteractiveChart,COLORS
ui.Chart=InteractiveChart
label,button,card,table,Form=ui.label,ui.button,ui.card,ui.table,ui.Form

class SmartForm(ui.Form):
    def __init__(self,title,fields,parent=None):
        super().__init__(title,fields,parent)
        for key,caption,value,options in fields:
            old=self.inputs[key];new=None
            if not options and key in ['day','deadline','purchase_day'] and value:
                new=QDateEdit();new.setCalendarPopup(True);new.setDisplayFormat('dd/MM/yyyy');new.setDateRange(QDate(1900,1,1),QDate(2200,12,31));new.setDate(QDate.fromString(str(value),'yyyy-MM-dd'))
            elif not options and key in ['closing_day','due_day','installments']:
                new=QSpinBox();new.setRange(1,120 if key=='installments' else 31);new.setValue(int(value or 1))
            if new:
                new.setAccessibleName(caption);old.parentWidget().layout().replaceWidget(old,new);old.hide();old.deleteLater();self.inputs[key]=new
    def values(self):
        return {k:(w.date().toString('yyyy-MM-dd') if isinstance(w,QDateEdit) else str(w.value()) if isinstance(w,QSpinBox) else w.currentText() if isinstance(w,QComboBox) else w.text()).strip() for k,w in self.inputs.items()}

ui.Form=SmartForm
Form=SmartForm

class EntryDialog(QDialog):
    def __init__(self,store,period,data=None,parent=None):
        super().__init__(parent);self.s=store;self.data=data or {};self.result_data=None;self.setWindowTitle('Editar lançamento' if data else 'Novo lançamento');self.setMinimumWidth(540);self.resize(600,680)
        layout=QVBoxLayout(self);layout.setContentsMargins(26,24,26,24);layout.setSpacing(16);layout.addWidget(label(self.windowTitle(),'section'))
        area=QScrollArea();area.setWidgetResizable(True);area.setFrameShape(QFrame.NoFrame);inner=QWidget();form=QFormLayout(inner);form.setSpacing(12);area.setWidget(inner);layout.addWidget(area)
        self.description=QLineEdit(self.data.get('description',''));self.amount=QLineEdit('' if self.data.get('amount') is None else str(self.data['amount']/100).replace('.',','));self.amount.setPlaceholderText('0,00');self.kind=QComboBox();self.kind.addItems([k for k in KINDS if k!='Pagamento de fatura']);self.kind.setCurrentText(self.data.get('kind','Despesa'))
        self.category=QComboBox();self.category.addItems(sorted(set(store.category_names()+[self.data.get('category','Outros')])));self.category.setCurrentText(self.data.get('category','Outros'));self.account=QComboBox();self.account.addItems(['']+[r['name'] for r in store.rows('SELECT name FROM accounts ORDER BY name')]);self.account.setEditable(False)
        if self.data.get('account') and self.account.findText(self.data['account'])<0:self.account.addItem(self.data['account'])
        self.account.setCurrentText(self.data.get('account',''));self.target=QComboBox();self.target.addItems(['']+[r['name'] for r in store.rows('SELECT name FROM accounts ORDER BY name')]);self.target.setCurrentText(self.data.get('target_account',''))
        self.day=QDateEdit();self.day.setCalendarPopup(True);self.day.setDisplayFormat('dd/MM/yyyy');self.day.setDateRange(QDate(1900,1,1),QDate(2200,12,31));self.day.setDate(QDate.fromString(self.data.get('day') or month_day(period,date.today().day),'yyyy-MM-dd'));self.unknown=QCheckBox('Sem data informada');self.unknown.setChecked(bool(data and not data.get('day')));self.day.setEnabled(not self.unknown.isChecked());self.unknown.toggled.connect(lambda checked:self.day.setEnabled(not checked))
        self.status=QComboBox();self.status.addItems(['Confirmado','Previsto','A revisar']);self.status.setCurrentText(self.data.get('status','Previsto' if self.day.date()>QDate.currentDate() else 'Confirmado'));self.due=QDateEdit();self.due.setCalendarPopup(True);self.due.setDisplayFormat('dd/MM/yyyy');self.due.setDate(QDate.fromString(self.data.get('due_day') or self.data.get('day') or date.today().isoformat(),'yyyy-MM-dd'))
        self.period=QLineEdit(self.data.get('period',period));self.tags=QLineEdit(self.data.get('tags',''));self.tags.setPlaceholderText('Ex.: casa, trabalho');self.note=QLineEdit(self.data.get('note',''));self.repeat=QSpinBox();self.repeat.setRange(1,60);self.repeat.setValue(1);self.repeat.setSuffix(' meses')
        for name,widget in [('Descrição',self.description),('Valor em reais',self.amount),('Tipo',self.kind),('Categoria',self.category),('Conta',self.account),('Destino da transferência',self.target),('Data',self.day),('',self.unknown),('Situação',self.status),('Vencimento',self.due)]:
            widget.setAccessibleName(name or 'Sem data informada');form.addRow(name,widget)
        advanced=QGroupBox('Detalhes e recorrência');advanced.setCheckable(True);advanced.setChecked(bool(data));advanced_layout=QVBoxLayout(advanced);advanced_content=QWidget();af=QFormLayout(advanced_content);advanced_layout.addWidget(advanced_content)
        for name,widget in [('Competência AAAA-MM',self.period),('Etiquetas',self.tags),('Observação',self.note),('Repetir',self.repeat)]:widget.setAccessibleName(name);af.addRow(name,widget)
        self.repeat.setEnabled(not bool(data));form.addRow(advanced);self.details=advanced
        advanced_content.setVisible(advanced.isChecked());advanced.toggled.connect(advanced_content.setVisible)
        self.error=label('','negative',True);layout.addWidget(self.error);box=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);box.button(QDialogButtonBox.Save).setText('Salvar lançamento');box.button(QDialogButtonBox.Cancel).setText('Cancelar');box.accepted.connect(self.validate);box.rejected.connect(self.reject);layout.addWidget(box)
        self.kind.currentTextChanged.connect(self.adjust);self.status.currentTextChanged.connect(self.adjust)
        if not data:self.day.dateChanged.connect(lambda d:self.period.setText(d.toString('yyyy-MM')))
        self.adjust();self.description.setFocus()
    def adjust(self,*_):
        self.target.setEnabled(self.kind.currentText()=='Transferência');self.category.setEnabled(self.kind.currentText()!='Transferência');self.due.setEnabled(self.status.currentText()=='Previsto')
    def validate(self):
        try:
            if not self.description.text().strip():raise ValueError('Informe uma descrição para reconhecer este lançamento.')
            amount=cents(self.amount.text()) if self.amount.text().strip() else None
            if amount is not None and amount<0:raise ValueError('Use valor positivo e escolha Receita ou Despesa.')
            if amount is None and self.status.currentText()=='Confirmado':raise ValueError('Informe o valor para confirmar o lançamento.')
            from ledger import check_period
            check_period(self.period.text().strip())
            if self.kind.currentText()=='Transferência' and (not self.account.currentText() or not self.target.currentText() or self.account.currentText()==self.target.currentText()):raise ValueError('Escolha contas diferentes para origem e destino.')
            self.result_data=dict(description=self.description.text().strip(),amount=amount,kind=self.kind.currentText(),category=self.category.currentText(),account=self.account.currentText(),target_account=self.target.currentText(),day=None if self.unknown.isChecked() else self.day.date().toString('yyyy-MM-dd'),period=self.period.text().strip(),status=self.status.currentText(),due_day=self.due.date().toString('yyyy-MM-dd') if self.status.currentText()=='Previsto' else self.data.get('due_day'),tags=', '.join(x.strip() for x in self.tags.text().split(',') if x.strip()),note=self.note.text().strip(),series_key=self.data.get('series_key',''),occurrence_index=self.data.get('occurrence_index',1));self.accept()
        except ValueError as e:self.error.setText(str(e))

class ModernWindow(ui.Window):
    GROUPS=[('Seu dia',['Visão geral','Lançamentos','Agenda']),('Organizar',['Contas bancárias','Cartões','Orçamentos','Categorias']),('Planejar',['Investimentos','Metas e câmbio','Simulações']),('Entender',['Análises','Relatórios']),('Preferências',['Perfil','Dados e backup'])]
    def __init__(self,store):
        QMainWindow.__init__(self);self.s=store;self.ledger=Ledger(store);self.page='Visão geral';self.p=date.today().strftime('%Y-%m');self.fx=None;self.anim=None;self.setWindowTitle('Horizonte • Finanças pessoais');self.setWindowIcon(ui.QIcon(str(ui.ROOT/'horizonte.ico')));self.resize(1440,950);self.setMinimumSize(1000,680);self.apply_theme()
        root=QWidget();self.setCentralWidget(root);row=QHBoxLayout(root);row.setContentsMargins(0,0,0,0);row.setSpacing(0);self.sidebar=QFrame();self.sidebar.setObjectName('sidebar');self.sidebar.setFixedWidth(226);sl=QVBoxLayout(self.sidebar);sl.setContentsMargins(18,24,18,14);sl.setSpacing(6);sl.addWidget(label('horizonte','brand'));sl.addWidget(label('Seu planejamento pessoal','small'))
        sc=QScrollArea();sc.setWidgetResizable(True);sc.setFrameShape(QFrame.NoFrame);navwidget=QWidget();navlayout=QVBoxLayout(navwidget);navlayout.setContentsMargins(0,8,0,0);navlayout.setSpacing(2);self.nav={}
        for title,names in self.GROUPS:
            heading=label(title.upper(),'small');heading.setContentsMargins(10,16,0,3);navlayout.addWidget(heading)
            for name in names:
                b=QPushButton(name);b.setObjectName('nav');b.setCheckable(True);b.setIcon(icon(name));b.setAccessibleName(name);b.clicked.connect(lambda _,n=name:self.go(n));navlayout.addWidget(b);self.nav[name]=b
        navlayout.addStretch();sc.setWidget(navwidget);sl.addWidget(sc,1);self.avatar=QLabel();self.avatar.setFixedSize(40,40);self.profile_name=label(store.setting('display-name','Meu perfil'));foot=QHBoxLayout();foot.addWidget(self.avatar);foot.addWidget(self.profile_name,1);sl.addLayout(foot);self.update_avatar();row.addWidget(self.sidebar)
        area=QWidget();al=QVBoxLayout(area);al.setContentsMargins(30,20,30,20);al.setSpacing(20);self.top=QHBoxLayout();toggle=button('Painel lateral',self.toggle_sidebar);toggle.setToolTip('Mostrar ou ocultar navegação • Ctrl+\\');self.top.addWidget(toggle);self.top.addWidget(button('Buscar ações  Ctrl+K',self.command_palette));self.top.addStretch();self.top.addWidget(button('‹',lambda:self.change_month(-1)));self.period=QComboBox();self.period.setMinimumWidth(170);self.refresh_periods();self.period.currentIndexChanged.connect(self.render);self.top.addWidget(self.period);self.top.addWidget(button('›',lambda:self.change_month(1)));self.top.addWidget(button('+ Lançamento',self.edit_tx,True));al.addLayout(self.top)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame);al.addWidget(self.scroll);row.addWidget(area,1);self.make_menus();self.render();self.backup_timer=QTimer(self);self.backup_timer.timeout.connect(self.automatic_backup);self.backup_timer.start(30*60*1000);QTimer.singleShot(1000,self.automatic_backup);self.statusBar().showMessage('Dados locais • Horizonte '+ui.VERSION)
    def apply_theme(self):
        dark=self.s.setting('theme','light')=='dark';application=QApplication.instance();application.setProperty('dark',dark);application.setStyleSheet(theme(dark));t=tokens(dark);palette=QPalette()
        for role,key in [(QPalette.Window,'bg'),(QPalette.WindowText,'text'),(QPalette.Base,'surface'),(QPalette.AlternateBase,'bg'),(QPalette.Text,'text'),(QPalette.Button,'surface'),(QPalette.ButtonText,'text'),(QPalette.Highlight,'primary')]:palette.setColor(role,QColor(t[key]))
        palette.setColor(QPalette.HighlightedText,QColor('white'));application.setPalette(palette)
    def update_avatar(self):
        data=self.s.setting('profile-photo');pix=QPixmap()
        if data and pix.loadFromData(base64.b64decode(data)):self.avatar.setPixmap(pix.scaled(self.avatar.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
        else:self.avatar.clear();self.avatar.setText((self.s.setting('display-name') or 'H')[:1].upper());self.avatar.setAlignment(Qt.AlignCenter);self.avatar.setStyleSheet('background:#dbeaff;border-radius:20px;color:#0056b3;font-size:20px;font-weight:600;')
    def make_menus(self):
        menu=self.menuBar().addMenu('Arquivo')
        for title,shortcut,fn in [('Novo lançamento','Ctrl+N',self.edit_tx),('Importar extrato','Ctrl+I',self.import_statement_ui),('Criar backup','Ctrl+Shift+B',self.backup)]:a=QAction(title,self);a.setShortcut(shortcut);a.triggered.connect(fn);menu.addAction(a)
        menu.addSeparator();a=QAction('Sair',self);a.setShortcut('Ctrl+Q');a.triggered.connect(self.close);menu.addAction(a);view=self.menuBar().addMenu('Exibir')
        a=QAction('Mostrar painel lateral',self);a.setShortcut('Ctrl+\\');a.triggered.connect(self.toggle_sidebar);view.addAction(a);a=QAction('Buscar ações',self);a.setShortcut('Ctrl+K');a.triggered.connect(self.command_palette);view.addAction(a)
        a=QAction('Aparência escura',self);a.setCheckable(True);a.setChecked(self.s.setting('theme')=='dark');a.triggered.connect(lambda value:self.set_theme(value));view.addAction(a)
        a=QAction('Reduzir movimento',self);a.setCheckable(True);a.setChecked(self.s.setting('reduce-motion')=='1');a.triggered.connect(lambda value:self.s.set('reduce-motion','1' if value else '0'));view.addAction(a)
    def set_theme(self,dark):self.s.set('theme','dark' if dark else 'light');self.apply_theme();self.render()
    def toggle_sidebar(self):self.sidebar.setVisible(not self.sidebar.isVisible())
    def notify(self,text):self.statusBar().showMessage(text,6000)
    def command_palette(self):
        d=QDialog(self);d.setWindowTitle('Buscar ações');d.resize(500,450);l=QVBoxLayout(d);search=QLineEdit();search.setPlaceholderText('Ir para uma tela ou criar lançamento');search.setAccessibleName('Buscar ações');l.addWidget(search);items=QListWidget();l.addWidget(items);choices=['Novo lançamento','Importar extrato']+list(self.nav)
        def fill(text):items.clear();items.addItems([x for x in choices if text.casefold() in x.casefold()]);items.setCurrentRow(0)
        def run():
            if not items.currentItem():return
            name=items.currentItem().text();d.accept()
            if name=='Novo lançamento':self.edit_tx()
            elif name=='Importar extrato':self.import_statement_ui()
            else:self.go(name)
        search.textChanged.connect(fill);search.returnPressed.connect(run);items.itemActivated.connect(lambda _:run());fill('');search.setFocus();d.exec()
    def change_month(self,offset):
        period=add_month(self.period.currentData(),offset);idx=self.period.findData(period)
        if idx<0:self.period.addItem(month_label(period),period);idx=self.period.findData(period)
        self.period.setCurrentIndex(idx)
    def render(self,*_):
        for n,b in self.nav.items():b.setChecked(n==self.page)
        w=QWidget();self.body=QVBoxLayout(w);self.body.setContentsMargins(0,0,0,0);self.body.setSpacing(20);self.body.addWidget(label(self.page,'title'));self.p=self.period.currentData() or date.today().strftime('%Y-%m')
        if self.s.setting('demo')=='1':self.body.addWidget(label('Demonstração • dados fictícios','small'))
        views={'Visão geral':self.overview,'Lançamentos':self.transactions,'Agenda':self.agenda,'Cartões':self.cards_page,'Categorias':self.categories_page,'Contas bancárias':self.accounts,'Orçamentos':self.budgets,'Investimentos':self.portfolio,'Metas e câmbio':self.goals,'Simulações':self.simulations,'Análises':self.analysis,'Relatórios':self.reports,'Perfil':self.profile,'Dados e backup':self.data_page};views[self.page]();self.body.addStretch();self.scroll.setWidget(w)
        due=[x for x in self.ledger.due() if x['day']<=date.today().isoformat()];self.nav['Agenda'].setText('Agenda'+('  '+str(len(due)) if due else ''))
    def go(self,name):
        old=self.page;self.page=name;self.render()
        if old!=name and self.s.setting('reduce-motion')!='1' and QApplication.platformName()!='offscreen':
            effect=QGraphicsOpacityEffect(self.scroll.widget());self.scroll.widget().setGraphicsEffect(effect);self.anim=QPropertyAnimation(effect,b'opacity');self.anim.setDuration(130);self.anim.setStartValue(.55);self.anim.setEndValue(1.0);self.anim.start()
    def overview(self):
        sm=self.s.summary(self.p);assets=sum(allocation(self.s).values());debt=self.ledger.outstanding();self.hint(month_label(self.p)+' • O essencial para decidir seu próximo passo.')
        self.metrics([('Patrimônio líquido',money(assets-debt),'Ativos menos parcelas de cartão em aberto'),('Receitas',money(sm['Receita']),'Valores confirmados ou a revisar'),('Despesas do mês',money(sm['Despesa']),'Consumo em conta + compras na fatura'),('Fluxo de caixa',money(sm['livre']),'Entradas menos saídas efetivas registradas')])
        due=[x for x in self.ledger.due() if x['day']<=(date.today()+timedelta(days=7)).isoformat()];row=QHBoxLayout();a,l=card('Atrasados e próximos 7 dias');l.addWidget(label(money(sum(x['amount'] for x in due if x['kind']!='Receita')),'metric'));l.addWidget(label(str(len(due))+' contas ou faturas para conferir','subtitle'));l.addWidget(button('Ver agenda',lambda:self.go('Agenda')));row.addWidget(a)
        g=self.s.rows('SELECT * FROM goals ORDER BY id LIMIT 1')[0];assessment=goal_assessment(self.s,g,self.p);a,l=card(g['name']);l.addWidget(label(money(assessment['base'])+' de '+money(g['target']),'section'));progress=QProgressBar();progress.setTextVisible(False);progress.setRange(0,1000);progress.setValue(min(1000,round(assessment['base']/g['target']*1000)));l.addWidget(progress);l.addWidget(label('Aporte calculado: '+money(assessment['need'])+'/mês','subtitle'));l.addWidget(button('Entender minha meta',lambda:self.go('Metas e câmbio')));row.addWidget(a);row.setStretch(0,1);row.setStretch(1,1);self.body.addLayout(row)
        row=QHBoxLayout();a,l=card('Receitas e despesas');periods=[p for p in self.s.periods() if p<=self.p][-6:];stats=[self.s.summary(p) for p in periods];l.addWidget(InteractiveChart('bar',[('Receitas',[x['Receita'] for x in stats]),('Despesas',[x['Despesa'] for x in stats])],[p[5:]+'/'+p[2:4] for p in periods]));row.addWidget(a,1)
        a,l=card('Onde você gastou');spent=self.ledger.category_spend(self.p);chart=InteractiveChart('donut',[(k,[v]) for k,v in sorted(spent.items(),key=lambda x:x[1],reverse=True)],center='Despesas');chart.selected.connect(lambda _:self.go('Lançamentos'));l.addWidget(chart);l.addWidget(label('Passe o cursor para ver valores. Clique para abrir lançamentos.','small'));row.addWidget(a,1);self.body.addLayout(row)
        a,l=card('Seu dinheiro hoje');groups=allocation(self.s);l.addWidget(InteractiveChart('donut',[(k,[v]) for k,v in groups.items() if v>0],center='Ativos'));l.addWidget(label('Patrimônio bruto: '+money(assets)+' • Cartões a quitar: '+money(debt),'small',True));self.body.addWidget(a)
        notes=insights(self.s,self.p)
        if notes:a,l=card(notes[0][0]);l.addWidget(label(notes[0][1],None,True));l.addWidget(button('Ver todas as análises',lambda:self.go('Análises')));self.body.addWidget(a)
    def transactions(self):
        self.hint('Registre o que entrou, saiu e ainda vai vencer. Compras de cartão ficam na tela Cartões; o pagamento da fatura aparece aqui sem duplicar o consumo.')
        row=QHBoxLayout();self.search=QLineEdit();self.search.setAccessibleName('Buscar lançamentos');self.search.setPlaceholderText('Buscar descrição, categoria, etiqueta ou conta');row.addWidget(self.search,1);row.addWidget(button('Importar extrato',self.import_statement_ui));self.body.addLayout(row)
        row=QHBoxLayout();self.kind_filter=QComboBox();self.kind_filter.addItems(['Todos os tipos']+KINDS);self.status_filter=QComboBox();self.status_filter.addItems(['Todas as situações','Confirmado','Previsto','A revisar','Sem valor']);self.account_filter=QComboBox();self.account_filter.addItems(['Todas as contas']+[x['name'] for x in self.s.rows('SELECT name FROM accounts ORDER BY name')]);self.category_filter=QComboBox();self.category_filter.addItems(['Todas as categorias']+self.s.category_names())
        for name,w in [('Tipo',self.kind_filter),('Situação',self.status_filter),('Conta',self.account_filter),('Categoria',self.category_filter)]:w.setAccessibleName('Filtrar por '+name);row.addWidget(w)
        self.body.addLayout(row);self.tx_table=table(['Data','Descrição','Tipo','Categoria','Valor','Conta','Situação'],[]);self.tx_table.setMinimumHeight(360);self.tx_table.cellDoubleClicked.connect(lambda *_:self.edit_selected());self.tx_table.itemSelectionChanged.connect(self.tx_detail);self.body.addWidget(self.tx_table)
        row=QHBoxLayout()
        for text,fn in [('Editar',self.edit_selected),('Confirmar pagamento',self.confirm_selected),('Comprovantes',self.attachments_ui),('Excluir',self.delete_selected)]:row.addWidget(button(text,fn))
        row.addStretch();self.body.addLayout(row);self.tx_info=label('Selecione um lançamento para ver sua origem e observações.','small',True);self.body.addWidget(self.tx_info)
        self.search.textChanged.connect(self.fill_transactions)
        for combo in [self.kind_filter,self.status_filter,self.account_filter,self.category_filter]:combo.currentTextChanged.connect(self.fill_transactions)
        self.fill_transactions()
    def fill_transactions(self,*_):
        query=self.search.text().casefold();kind=self.kind_filter.currentText();status=self.status_filter.currentText();account=self.account_filter.currentText();category=self.category_filter.currentText();rows=self.s.rows('SELECT * FROM tx WHERE period=? ORDER BY COALESCE(day,period) DESC,id DESC',(self.p,));self.tx_rows=[x for x in rows if (kind=='Todos os tipos' or x['kind']==kind) and (status=='Todas as situações' or (x['amount'] is None if status=='Sem valor' else x['status']==status)) and (account=='Todas as contas' or account==x['account'] or account==x['target_account']) and (category=='Todas as categorias' or category==x['category']) and query in ' '.join(str(x.get(k) or '') for k in ['description','category','account','tags','note']).casefold()]
        self.tx_table.setRowCount(len(self.tx_rows))
        for i,x in enumerate(self.tx_rows):
            for j,v in enumerate([x['day'] or 'Sem data',x['description'],x['kind'],x['category'],money(x['amount']) if x['amount'] is not None else 'Sem valor',x['account'] or 'Não definida',x['status']]):item=QTableWidgetItem(str(v));item.setToolTip(x['note'] or '');self.tx_table.setItem(i,j,item)
        self.tx_table.setAccessibleDescription(str(len(self.tx_rows))+' lançamentos encontrados')
    def tx_detail(self):
        i=self.tx_table.currentRow()
        if i<0 or i>=len(getattr(self,'tx_rows',[])):return
        row=self.tx_rows[i];self.tx_info.setText(' • '.join(str(x) for x in [row['source'] or 'Cadastro manual',row['tags'],row['note']] if x))
    def edit_tx(self,data=None):
        if not isinstance(data,dict):data=None
        if data and data['kind']=='Pagamento de fatura':QMessageBox.information(self,'Pagamento de fatura','Consulte ou desfaça esse registro na tela Cartões.');return
        f=EntryDialog(self.s,self.p,data,self)
        if not f.exec():return
        try:
            values=f.result_data;repeat=f.repeat.value() if not data else 1
            if repeat>1:values['series_key']=uuid.uuid4().hex
            with self.s.db:
                self.s.save_tx(values,data.get('id') if data else None,commit=False)
                for i in range(1,repeat):
                    v=dict(values);v['period']=add_month(values['period'],i);v['status']='Previsto';v['occurrence_index']=i+1
                    for key in ['day','due_day']:
                        if values.get(key):v[key]=month_day(add_month(values[key][:7],i),date.fromisoformat(values[key]).day)
                    self.s.save_tx(v,commit=False)
            self.refresh_periods();self.render();self.notify('Lançamento salvo'+(' e recorrências previstas criadas.' if repeat>1 else '.'))
        except (ValueError,sqlite3.Error) as e:QMessageBox.warning(self,'Lançamento',str(e))
    def confirm_selected(self):
        i=self.tx_table.currentRow()
        if i<0:return
        try:self.ledger.confirm_tx(self.tx_rows[i]['id']);self.render();self.notify('Pagamento ou recebimento confirmado na data de hoje.')
        except ValueError as e:QMessageBox.warning(self,'Confirmar',str(e))
    def delete_selected(self):
        i=self.tx_table.currentRow()
        if i<0:return
        row=self.tx_rows[i]
        if QMessageBox.question(self,'Excluir lançamento','Excluir este registro? Se for pagamento de fatura, o saldo pendente será reaberto.')!=QMessageBox.Yes:return
        if row['kind']=='Pagamento de fatura':self.ledger.delete_payment(row['id'])
        else:
            with self.s.db:self.s.db.execute('DELETE FROM tx WHERE id=?',(row['id'],))
        self.render();self.notify('Registro excluído.')
    def attachments_ui(self):
        i=self.tx_table.currentRow()
        if i<0:return
        tx_id=self.tx_rows[i]['id'];d=QDialog(self);d.setWindowTitle('Comprovantes');d.resize(620,440);layout=QVBoxLayout(d);layout.addWidget(label(self.tx_rows[i]['description'],'section'));lst=QListWidget();layout.addWidget(lst);files=[]
        def fill():
            nonlocal files
            files=self.s.rows('SELECT id,name,mime FROM attachments WHERE tx_id=?',(tx_id,));lst.clear();lst.addItems([r['name'] for r in files])
        def add():
            path,_=QFileDialog.getOpenFileName(d,'Adicionar comprovante','','Comprovante (*.pdf *.png *.jpg *.jpeg)')
            if path:
                try:self.ledger.attach(tx_id,path);fill()
                except ValueError as e:QMessageBox.warning(d,'Comprovante',str(e))
        def export():
            idx=lst.currentRow()
            if idx<0:return
            row=self.s.rows('SELECT * FROM attachments WHERE id=?',(files[idx]['id'],))[0];path,_=QFileDialog.getSaveFileName(d,'Salvar comprovante',Path(row['name']).name)
            if path:
                try:Path(path).write_bytes(row['data'])
                except OSError as e:QMessageBox.warning(d,'Comprovante',str(e))
        row=QHBoxLayout();row.addWidget(button('Adicionar PDF ou imagem',add));row.addWidget(button('Salvar arquivo selecionado',export));layout.addLayout(row);layout.addWidget(label('Os comprovantes ficam no banco local e acompanham o backup. Limite: 10 MB por arquivo.','small',True));fill();d.exec()
    def agenda(self):
        self.hint('Contas previstas e faturas em aberto. Confirmar um registro aqui apenas atualiza o Horizonte; nenhum pagamento é enviado ao banco.')
        all_items=self.ledger.due();self.agenda_rows=[x for x in all_items if x['day'][:7]<=self.p];overdue=[x for x in self.agenda_rows if x['status']=='Atrasado'];self.metrics([('Em atraso',money(sum(x['amount'] for x in overdue if x['kind']!='Receita')),str(len(overdue))+' registros para conferir'),('A pagar',money(sum(x['amount'] for x in self.agenda_rows if x['kind']!='Receita')),'Até o mês selecionado'),('A receber',money(sum(x['amount'] for x in self.agenda_rows if x['kind']=='Receita')),'Receitas previstas')])
        self.agenda_table=table(['Vencimento','Descrição','Tipo','Valor','Conta','Situação'],[[x['day'],x['description'],x['kind'],money(x['amount']),x['account'],x['status']] for x in self.agenda_rows]);self.body.addWidget(self.agenda_table);self.body.addWidget(button('Registrar pagamento ou recebimento',self.agenda_confirm,True));self.hint('A agenda mostra o mês selecionado e atrasados anteriores. Previsões posteriores aparecem ao avançar o mês no topo.')
    def agenda_confirm(self):
        i=self.agenda_table.currentRow()
        if i<0:return
        row=self.agenda_rows[i]
        if row['type']=='card':self.pay_card(row['id'],row['period'])
        else:
            try:self.ledger.confirm_tx(row['id']);self.render();self.notify('Registro confirmado hoje.')
            except ValueError as e:QMessageBox.warning(self,'Agenda',str(e))
    def categories_page(self):
        self.hint('Organize suas próprias categorias e subcategorias. Renomear uma categoria atualiza seu histórico e seus limites.')
        self.category_rows=self.ledger.categories(archived=True);self.cat_table=table(['Categoria','Grupo','Cor','Situação'],[[x['name'],x['parent'] or 'Principal',x['color'],'Arquivada' if x['archived'] else 'Ativa'] for x in self.category_rows]);self.body.addWidget(self.cat_table);row=QHBoxLayout();row.addWidget(button('+ Categoria',self.edit_category,True));row.addWidget(button('Editar',self.edit_category_selected));row.addWidget(button('Arquivar ou reativar',self.archive_category));row.addStretch();self.body.addLayout(row)
    def edit_category_selected(self):
        i=self.cat_table.currentRow()
        if i>=0:self.edit_category(self.category_rows[i])
    def edit_category(self,data=None):
        if not isinstance(data,dict):data={}
        roots=['']+[x['name'] for x in self.ledger.categories() if not x['parent'] and x['name']!=data.get('name')];f=Form('Categoria',[('name','Nome',data.get('name',''),None),('parent','Categoria principal (opcional)',data.get('parent',''),roots),('color','Cor hexadecimal',data.get('color','#007AFF'),None)],self)
        while f.exec():
            try:v=f.values();self.ledger.save_category(v['name'],v['parent'],v['color'],data.get('name'));self.render();break
            except (ValueError,sqlite3.Error) as e:f.error.setText(str(e))
    def archive_category(self):
        i=self.cat_table.currentRow()
        if i<0:return
        row=self.category_rows[i]
        if not row['archived'] and self.s.rows('SELECT 1 FROM categories WHERE parent=? AND archived=0',(row['name'],)):QMessageBox.information(self,'Categoria principal','Arquive as subcategorias antes da principal.');return
        with self.s.db:self.s.db.execute('UPDATE categories SET archived=? WHERE name=?',(0 if row['archived'] else 1,row['name']))
        self.render()
    def budgets(self):
        self.hint('Acompanhe consumo em conta e compras por fatura, sem contar o pagamento do cartão novamente.')
        row=QHBoxLayout();row.addWidget(button('Definir limite',self.edit_budget,True));row.addWidget(button('Copiar mês anterior',self.copy_budgets_ui));row.addWidget(button('Remover limite',self.remove_budget));row.addStretch();self.body.addLayout(row)
        budgets={r['category']:r['amount'] for r in self.s.rows('SELECT * FROM budgets WHERE period=?',(self.p,))};spent=self.ledger.category_spend(self.p);self.budget_rows=sorted(set(budgets)|set(spent));rows=[]
        for name in self.budget_rows:
            limit=budgets.get(name);used=spent.get(name,0);rows.append([name,money(used),money(limit) if limit is not None else 'Não definido',money(limit-used) if limit is not None else '—','Acima do limite' if limit is not None and used>limit else 'Dentro do limite' if limit is not None else 'Definir limite'])
        self.budget_table=table(['Categoria','Consumido','Limite','Disponível','Situação'],rows);self.body.addWidget(self.budget_table)
    def copy_budgets_ui(self):
        if self.s.rows('SELECT 1 FROM budgets WHERE period=?',(self.p,)) and QMessageBox.question(self,'Copiar limites','Substituir limites deste mês pelos do mês anterior?')!=QMessageBox.Yes:return
        self.ledger.copy_budgets(add_month(self.p,-1),self.p);self.render();self.notify('Limites copiados do mês anterior.')
    def cards_page(self):
        self.hint('Compras e parcelas são despesas de consumo. Registrar pagamento reduz a conta e a dívida, sem gerar outra despesa.')
        cards=self.s.rows('SELECT * FROM cards WHERE archived=0 ORDER BY name');row=QHBoxLayout();row.addWidget(button('+ Cartão',self.edit_card,True))
        if not cards:
            self.body.addLayout(row);w,l=card('Organize seus cartões');l.addWidget(label('Cadastre nome, limite, fechamento e vencimento. Depois registre uma compra à vista ou parcelada para acompanhar as faturas futuras.',None,True));self.body.addWidget(w);return
        combo=QComboBox()
        for c in cards:combo.addItem(c['name'],c['id'])
        idx=combo.findData(getattr(self,'selected_card',cards[0]['id']));combo.setCurrentIndex(max(0,idx));self.selected_card=combo.currentData();card_data=next(c for c in cards if c['id']==self.selected_card);combo.currentIndexChanged.connect(lambda _:self.select_card(combo.currentData()));row.addWidget(combo,1);row.addWidget(button('Editar cartão',lambda:self.edit_card(card_data)));row.addWidget(button('Arquivar',lambda:self.archive_card(card_data)));self.body.addLayout(row)
        inv=self.ledger.invoice(self.selected_card,self.p);outstanding=self.ledger.outstanding(self.selected_card);self.metrics([('Fatura de '+month_label(self.p),money(inv['remaining']),'Vencimento: '+inv['due_day']),('Limite disponível',money(card_data['limit_amount']-outstanding),'Considera todas as parcelas em aberto'),('Total parcelado a quitar',money(outstanding),'Inclui faturas futuras')])
        if outstanding>card_data['limit_amount']:self.banner('O total registrado ultrapassa o limite cadastrado. Confira os dados e novas compras.')
        row=QHBoxLayout();row.addWidget(button('+ Compra no cartão',self.purchase_ui,True));row.addWidget(button('Registrar pagamento',lambda:self.pay_card(self.selected_card,self.p)));row.addStretch();self.body.addLayout(row)
        items=self.s.rows('SELECT * FROM card_items WHERE card_id=? AND period=? ORDER BY purchase_day DESC,id DESC',(self.selected_card,self.p));self.card_items=items;self.card_table=table(['Compra','Descrição','Categoria','Parcela','Valor'],[[r['purchase_day'],r['description'],r['category'],str(r['installment'])+'/'+str(r['installments']),money(r['amount'])] for r in items]);self.body.addWidget(self.card_table);self.body.addWidget(button('Excluir compra selecionada e suas parcelas',self.remove_purchase_ui))
        w,l=card('Próximas faturas');periods=[add_month(self.p,i) for i in range(12)];l.addWidget(InteractiveChart('bar',[('Em aberto',[self.ledger.invoice(self.selected_card,p)['remaining'] for p in periods])],[p[5:]+'/'+p[2:4] for p in periods]));self.body.addWidget(w)
        payments=self.s.rows('SELECT * FROM card_payments WHERE card_id=? AND period=? ORDER BY day DESC',(self.selected_card,self.p));self.payments=payments;self.pay_table=table(['Pagamento registrado','Conta','Valor'],[[r['day'],r['account'],money(r['amount'])] for r in payments]);self.body.addWidget(self.pay_table);self.body.addWidget(button('Desfazer pagamento selecionado',self.undo_payment_ui));self.hint('Compras no dia do fechamento entram no ciclo seguinte. Você pode ajustar a primeira competência da compra conforme a fatura real do banco.')
    def select_card(self,ident):self.selected_card=ident;self.render()
    def edit_card(self,data=None):
        if not isinstance(data,dict):data={}
        accounts=['']+[r['name'] for r in self.s.rows("SELECT name FROM accounts WHERE currency='BRL' ORDER BY name")];f=Form('Dados do cartão',[('name','Nome',data.get('name',''),None),('institution','Instituição',data.get('institution',''),None),('limit_amount','Limite em R$',str(data.get('limit_amount',0)/100).replace('.',','),None),('closing_day','Dia de fechamento',data.get('closing_day',20),None),('due_day','Dia de vencimento',data.get('due_day',28),None),('payment_account','Conta de pagamento',data.get('payment_account',''),accounts)],self)
        while f.exec():
            try:
                v=f.values();v['limit_amount']=cents(v['limit_amount']);v['closing_day']=int(v['closing_day']);v['due_day']=int(v['due_day']);v['color']='#007AFF';self.selected_card=self.ledger.save_card(v,data.get('id'));self.render();break
            except (ValueError,sqlite3.Error) as e:f.error.setText(str(e))
    def archive_card(self,card_data):
        if self.ledger.outstanding(card_data['id']):QMessageBox.information(self,'Cartão em aberto','Registre a quitação das faturas antes de arquivar.');return
        if QMessageBox.question(self,'Arquivar cartão','Arquivar este cartão e preservar seu histórico?')==QMessageBox.Yes:
            with self.s.db:self.s.db.execute('UPDATE cards SET archived=1 WHERE id=?',(card_data['id'],))
            self.render()
    def purchase_ui(self):
        card_id=self.selected_card;f=Form('Compra no cartão',[('description','Descrição','',None),('amount','Valor TOTAL da compra em R$','',None),('purchase_day','Data AAAA-MM-DD',date.today().isoformat(),None),('category','Categoria','Compras',self.s.category_names()),('installments','Número de parcelas',1,None),('first_period','Primeira fatura AAAA-MM (opcional)','',None),('note','Observações','',None)],self)
        while f.exec():
            try:
                v=f.values();self.ledger.add_purchase(card_id,v['description'],cents(v['amount']),v['purchase_day'],v['category'],int(v['installments']),v['first_period'] or None,v['note']);self.refresh_periods();self.render();self.notify('Compra e parcelas registradas.');break
            except (ValueError,sqlite3.Error) as e:f.error.setText(str(e))
    def pay_card(self,ident,period):
        remaining=self.ledger.invoice(ident,period)['remaining'];accounts=[r['name'] for r in self.s.rows("SELECT name FROM accounts WHERE currency='BRL' ORDER BY name")]
        if not accounts:QMessageBox.information(self,'Conta de pagamento','Cadastre uma conta em reais antes de registrar o pagamento.');return
        if remaining<=0:QMessageBox.information(self,'Fatura quitada','Não há saldo a registrar neste período.');return
        card_data=self.s.rows('SELECT * FROM cards WHERE id=?',(ident,))[0];f=Form('Registrar pagamento da fatura',[('amount','Valor pago em R$',str(remaining/100).replace('.',','),None),('day','Data AAAA-MM-DD',date.today().isoformat(),None),('account','Conta',card_data['payment_account'] or accounts[0],accounts)],self)
        while f.exec():
            try:
                v=f.values();self.ledger.pay_invoice(ident,period,cents(v['amount']),v['day'],v['account']);self.refresh_periods();self.render();self.notify('Pagamento registrado localmente.');break
            except (ValueError,sqlite3.Error) as e:f.error.setText(str(e))
    def remove_purchase_ui(self):
        i=self.card_table.currentRow()
        if i<0:return
        if QMessageBox.question(self,'Excluir compra','Excluir a compra selecionada e todas as suas parcelas futuras?')!=QMessageBox.Yes:return
        try:self.ledger.delete_purchase(self.card_items[i]['batch_key']);self.render()
        except ValueError as e:QMessageBox.warning(self,'Compra',str(e))
    def undo_payment_ui(self):
        i=self.pay_table.currentRow()
        if i<0:return
        if QMessageBox.question(self,'Desfazer registro','Desfazer este registro local e reabrir o saldo da fatura? Isso não estorna um pagamento no banco real.')==QMessageBox.Yes:self.ledger.delete_payment(self.payments[i]['tx_id']);self.render()
    def import_statement_ui(self,*_):
        accounts=[r['name'] for r in self.s.rows("SELECT name FROM accounts WHERE currency='BRL' ORDER BY name")]
        if not accounts:QMessageBox.information(self,'Conta necessária','Cadastre uma conta em reais para importar e conciliar seu extrato.');return
        f=Form('Conferir extrato',[('account','Conta do extrato',accounts[0],accounts)],self)
        if not f.exec():return
        path,_=QFileDialog.getOpenFileName(self,'Abrir extrato','','Extrato (*.csv *.ofx)')
        if not path:return
        try:rows=self.ledger.preview_statement(path,f.values()['account'])
        except (ValueError,OSError) as e:QMessageBox.warning(self,'Extrato',str(e));return
        d=QDialog(self);d.setWindowTitle('Conferir antes de importar');d.resize(1000,680);layout=QVBoxLayout(d);layout.addWidget(label('Conciliação do extrato','section'));layout.addWidget(label('Novos registros vêm selecionados. Itens já importados ficam bloqueados; possíveis correspondências manuais exigem sua escolha.',None,True));t=table(['Usar','Data','Descrição','Tipo','Valor','Conferência'],[]);t.setRowCount(len(rows))
        for i,r in enumerate(rows):
            check=QTableWidgetItem();check.setFlags(Qt.ItemIsUserCheckable|Qt.ItemIsEnabled if not r['duplicate'] else Qt.NoItemFlags);check.setCheckState(Qt.Checked if not r['duplicate'] and not r['match_id'] else Qt.Unchecked);t.setItem(i,0,check)
            for j,v in enumerate([r['day'],r['description'],r['kind'],money(r['amount']),'Já importado' if r['duplicate'] else 'Possível correspondência' if r['match_id'] else 'Novo'],1):t.setItem(i,j,QTableWidgetItem(str(v)))
        layout.addWidget(t);reconcile=QCheckBox('Conciliar correspondências selecionadas em vez de criar outro lançamento');layout.addWidget(reconcile);error=label('','negative',True);layout.addWidget(error);box=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);box.button(QDialogButtonBox.Save).setText('Aplicar seleção');box.button(QDialogButtonBox.Cancel).setText('Cancelar');box.rejected.connect(d.reject)
        def save():
            selected=[i for i in range(len(rows)) if t.item(i,0).checkState()==Qt.Checked]
            if any(rows[i]['match_id'] for i in selected) and not reconcile.isChecked():error.setText('Marque a opção de conciliação para confirmar as correspondências selecionadas.');return
            try:
                count,matched=self.ledger.import_statement(rows,selected,reconcile.isChecked());d.accept();self.refresh_periods();self.render();self.notify(f'{count} novos registros e {matched} correspondências conciliadas.')
            except (ValueError,sqlite3.Error) as e:error.setText(str(e))
        box.accepted.connect(save);layout.addWidget(box);d.exec()
    def data_page(self):
        super().data_page();self.body.insertWidget(2,button('Importar ou conciliar CSV/OFX',self.import_statement_ui,True))
    def restore(self):
        path,_=QFileDialog.getOpenFileName(self,'Restaurar backup','','SQLite (*.sqlite)')
        if not path:return
        if QMessageBox.question(self,'Restaurar backup','Substituir os dados atuais por esta cópia? Será feito um backup antes da restauração. Cópias da versão 0.1 são migradas automaticamente.')!=QMessageBox.Yes:return
        try:
            previous=self.ledger.restore_backup(path);self.refresh_periods();self.profile_name.setText(self.s.setting('display-name','Meu perfil'));self.update_avatar();self.apply_theme();self.render();self.notify('Backup restaurado. Cópia anterior: '+str(previous))
        except (ValueError,OSError,sqlite3.Error) as e:QMessageBox.warning(self,'Backup',str(e))
    def reports(self):
        super().reports();w,l=card('Cartões e faturas');rows=[]
        for c in self.s.rows('SELECT * FROM cards ORDER BY name'):
            inv=self.ledger.invoice(c['id'],self.p);rows.append([c['name'],money(inv['total']),money(inv['paid']),money(inv['remaining']),inv['due_day']])
        l.addWidget(table(['Cartão','Compras','Pago','Em aberto','Vencimento'],rows));self.body.addWidget(w)
    def analysis(self):
        self.hint('Leituras locais e explicáveis, com base nos registros disponíveis. Valores a revisar e meses incompletos limitam a precisão das médias.')
        cap=recent_capacity(self.s,self.p);self.metrics([('Receita média',money(cap['income']),'Até três meses com dados'),('Consumo médio',money(cap['expense']),'Conta + compras de cartão'),('Capacidade média de aporte',money(cap['capacity']),'Receita menos consumo registrado')])
        for title,text in insights(self.s,self.p):w,l=card(title);l.addWidget(label(text,None,True));self.body.addWidget(w)
        periods=cap['periods'];direct=round(sum(self.s.summary(p)['Despesa em conta'] for p in periods)/len(periods)) if periods else 0;rows=[];values=[];labels=[];cumulative=0
        for i in range(1,13):
            period=add_month(self.p,i);planned={r['kind']:r['n'] or 0 for r in self.s.rows("SELECT kind,SUM(amount) n FROM tx WHERE period=? AND status='Previsto' GROUP BY kind",(period,))};revenue=planned.get('Receita',cap['income']);expense=planned.get('Despesa',direct);card_due=sum(self.ledger.invoice(c['id'],period)['remaining'] for c in self.s.rows('SELECT id FROM cards'));aporte=planned.get('Aporte',0);net=revenue-expense-card_due-aporte+planned.get('Resgate',0);cumulative+=net;values.append(cumulative);labels.append(period[2:]);rows.append([period,money(revenue),money(expense),money(card_due),money(aporte),money(net),money(cumulative)])
        w,l=card('Compromissos dos próximos 12 meses');l.addWidget(InteractiveChart('line',[('Fluxo acumulado',values)],labels));l.addWidget(table(['Mês','Receita','Gastos em conta','Faturas conhecidas','Aportes','Fluxo','Acumulado'],rows));l.addWidget(label('Receitas e gastos diretos usam o previsto daquele tipo no mês, se existente; caso contrário usam a média histórica. Faturas incluem apenas compras já registradas. Aportes previstos são separados. O acumulado começa em zero e não é patrimônio.','small',True));self.body.addWidget(w)
