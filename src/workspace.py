"""Interface desktop 0.2: fluxos de controle financeiro e linguagem visual HIG."""
import base64, calendar, json, shutil, sqlite3, uuid
from datetime import date,datetime,timedelta
from pathlib import Path
from PySide6.QtCore import Qt,QDate,QTimer,QPropertyAnimation,QEasingCurve,QPoint
from PySide6.QtGui import QAction,QKeySequence,QFont,QPixmap,QPainter,QColor,QPalette
from PySide6.QtWidgets import *
import app as ui
from core import *
from widgets import DateField,MonthField,ResponsiveCards,FlowLayout,ChoiceBox
ui.QComboBox=ChoiceBox
QComboBox=ChoiceBox
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
            if not options and key in ['day','deadline','purchase_day','maturity']:
                new=DateField(optional=key=='maturity');new.set_iso(value or '')
            elif not options and key=='first_period':
                new=MonthField(value or None,optional=True)
            elif not options and key in ['closing_day','due_day','installments']:
                new=QSpinBox();new.setRange(1,120 if key=='installments' else 31);new.setValue(int(value or 1))
            if new:
                new.setAccessibleName(caption);old.parentWidget().layout().replaceWidget(old,new);old.hide();old.deleteLater();self.inputs[key]=new
    def values(self):
        return {k:(w.iso() if isinstance(w,DateField) else str(w.value()) if isinstance(w,QSpinBox) else w.currentText() if isinstance(w,QComboBox) else w.text()).strip() for k,w in self.inputs.items()}

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
        self.account.setCurrentText(self.data.get('account',''));self.account.setPlaceholderText('Selecione uma conta');self.account.setCurrentIndex(self.account.currentIndex() if self.data.get('account') else -1);self.target=QComboBox();self.target.addItems(['']+[r['name'] for r in store.rows('SELECT name FROM accounts ORDER BY name')]);self.target.setCurrentText(self.data.get('target_account',''));self.target.setPlaceholderText('Selecione a conta de destino');self.target.setCurrentIndex(self.target.currentIndex() if self.data.get('target_account') else -1)
        self.day=DateField();self.day.setCalendarPopup(True);self.day.setDisplayFormat('dd/MM/yyyy');self.day.setDateRange(QDate(1900,1,1),QDate(2200,12,31));self.day.setDate(QDate.fromString(self.data.get('day') or month_day(period,date.today().day),'yyyy-MM-dd'));self.unknown=QCheckBox('Sem data informada');self.unknown.setChecked(bool(data and not data.get('day')));self.day.setEnabled(not self.unknown.isChecked());self.unknown.toggled.connect(lambda checked:self.day.setEnabled(not checked))
        self.status=QComboBox();self.status.addItems(['Confirmado','Previsto','A revisar']);self.status.setCurrentText(self.data.get('status','Previsto' if self.day.date()>QDate.currentDate() else 'Confirmado'));self.due=DateField();self.due.setCalendarPopup(True);self.due.setDisplayFormat('dd/MM/yyyy');self.due.setDate(QDate.fromString(self.data.get('due_day') or self.data.get('day') or self.day.date().toString('yyyy-MM-dd'),'yyyy-MM-dd'))
        self.period=MonthField(self.data.get('period',period));self.independent_period=QCheckBox('Manter competência independente da data');self.independent_period.setChecked(bool(data and self.data.get('day') and self.data.get('period')!=self.data['day'][:7]));self.tags=QLineEdit(self.data.get('tags',''));self.tags.setPlaceholderText('Ex.: casa, trabalho');self.note=QLineEdit(self.data.get('note',''));self.repeat=QSpinBox();self.repeat.setRange(1,60);self.repeat.setValue(1);self.repeat.setSuffix(' meses')
        for name,widget in [('Descrição',self.description),('Valor em reais',self.amount),('Tipo',self.kind),('Categoria',self.category),('Conta',self.account),('Destino da transferência',self.target),('Data',self.day),('',self.unknown),('Situação',self.status),('Vencimento',self.due),('Competência (mês/ano)',self.period),('',self.independent_period)]:
            widget.setAccessibleName(name or 'Sem data informada');form.addRow(name,widget)
        account_note=label('A conta movimenta o saldo cadastrado. Para transferir, escolha o tipo Transferência. Use Previsto para mostrar o vencimento na agenda.','small',True);form.addRow(account_note);create_account=button('+ Cadastrar conta',self.create_account);form.addRow('',create_account)
        advanced=QGroupBox('Detalhes e recorrência');advanced.setCheckable(True);advanced.setChecked(bool(data));advanced_layout=QVBoxLayout(advanced);advanced_content=QWidget();af=QFormLayout(advanced_content);advanced_layout.addWidget(advanced_content)
        for name,widget in [('Etiquetas',self.tags),('Observação',self.note),('Repetir',self.repeat)]:widget.setAccessibleName(name);af.addRow(name,widget)
        self.repeat.setEnabled(not bool(data));form.addRow(advanced);self.details=advanced
        advanced_content.setVisible(advanced.isChecked());advanced.toggled.connect(advanced_content.setVisible)
        self.error=label('','negative',True);layout.addWidget(self.error);box=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);box.button(QDialogButtonBox.Save).setText('Salvar lançamento');box.button(QDialogButtonBox.Cancel).setText('Cancelar');box.accepted.connect(self.validate);box.rejected.connect(self.reject);layout.addWidget(box)
        self.kind.currentTextChanged.connect(self.adjust);self.status.currentTextChanged.connect(self.adjust)
        self.last_day=self.day.date();self.day.dateChanged.connect(self.sync_dates)
        self.adjust();self.description.setFocus()
    def create_account(self):
        owner=self.parentWidget();before={r['name'] for r in self.s.rows('SELECT name FROM accounts')}
        if not hasattr(owner,'edit_account'):return
        owner.edit_account()
        names=[r['name'] for r in self.s.rows('SELECT name FROM accounts ORDER BY name')];added=set(names)-before
        for combo in [self.account,self.target]:
            selected=combo.currentText();combo.clear();combo.addItems(['']+names);combo.setCurrentText(selected if selected in names else '')
        if added:self.account.setCurrentText(sorted(added)[0])
    def sync_dates(self,selected):
        if not self.independent_period.isChecked():self.period.setText(selected.toString('yyyy-MM'))
        if self.due.date()==self.last_day:self.due.setDate(selected)
        self.last_day=selected
    def adjust(self,*_):
        self.target.parentWidget().layout().setRowVisible(self.target,self.kind.currentText()=='Transferência');self.category.setEnabled(self.kind.currentText()!='Transferência');self.due.setEnabled(True)
    def validate(self):
        try:
            if not self.description.text().strip():raise ValueError('Informe uma descrição para reconhecer este lançamento.')
            amount=cents(self.amount.text()) if self.amount.text().strip() else None
            if amount is not None and amount<0:raise ValueError('Use valor positivo e escolha Receita ou Despesa.')
            if amount is None and self.status.currentText()=='Confirmado':raise ValueError('Informe o valor para confirmar o lançamento.')
            from ledger import check_period
            check_period(self.period.text().strip())
            if self.kind.currentText()=='Transferência' and (not self.account.currentText() or not self.target.currentText() or self.account.currentText()==self.target.currentText()):raise ValueError('Escolha contas diferentes para origem e destino.')
            self.result_data=dict(description=self.description.text().strip(),amount=amount,kind=self.kind.currentText(),category=self.category.currentText(),account=self.account.currentText(),target_account=self.target.currentText(),day=None if self.unknown.isChecked() else self.day.date().toString('yyyy-MM-dd'),period=self.period.text().strip(),status=self.status.currentText(),due_day=self.due.date().toString('yyyy-MM-dd'),tags=', '.join(x.strip() for x in self.tags.text().split(',') if x.strip()),note=self.note.text().strip(),series_key=self.data.get('series_key',''),occurrence_index=self.data.get('occurrence_index',1));self.accept()
        except ValueError as e:self.error.setText(str(e))

class ModernWindow(ui.Window):
    GROUPS=[('Seu dia',['Visão geral','Lançamentos','Agenda']),('Organizar',['Contas bancárias','Cartões','Orçamentos','Categorias']),('Planejar',['Investimentos','Metas e câmbio','Simulações']),('Entender',['Análises','Relatórios']),('Preferências',['Perfil','Dados e backup'])]
    def __init__(self,store):
        QMainWindow.__init__(self);self.s=store;self.ledger=Ledger(store);self.page='Visão geral';self.p=date.today().strftime('%Y-%m');self.fx=None;self.anim=None;self.setWindowTitle('Elisei • Finanças pessoais');self.setWindowIcon(ui.QIcon(str(ui.ROOT/'elisei.ico')));self.resize(1440,950);self.setMinimumSize(1000,680);self.apply_theme()
        root=QWidget();self.setCentralWidget(root);row=QHBoxLayout(root);row.setContentsMargins(0,0,0,0);row.setSpacing(0);self.sidebar=QFrame();self.sidebar.setObjectName('sidebar');self.sidebar.setFixedWidth(226);sl=QVBoxLayout(self.sidebar);sl.setContentsMargins(18,24,18,14);sl.setSpacing(6);brand=QHBoxLayout();mark=QLabel();mark.setPixmap(ui.QIcon(str(ui.ROOT/'elisei.ico')).pixmap(36,36));brand.addWidget(mark);brand.addWidget(label('elisei','brand'));brand.addStretch();sl.addLayout(brand);sl.addWidget(label('Finanças para o seu próximo passo','small',True))
        sc=QScrollArea();sc.setWidgetResizable(True);sc.setFrameShape(QFrame.NoFrame);navwidget=QWidget();navlayout=QVBoxLayout(navwidget);navlayout.setContentsMargins(0,8,0,0);navlayout.setSpacing(2);self.nav={}
        for title,names in self.GROUPS:
            heading=label(title.upper(),'small');heading.setContentsMargins(10,16,0,3);navlayout.addWidget(heading)
            for name in names:
                b=QPushButton(name);b.setObjectName('nav');b.setCheckable(True);b.setIcon(icon(name));b.setAccessibleName(name);b.clicked.connect(lambda _,n=name:self.go(n));navlayout.addWidget(b);self.nav[name]=b
        navlayout.addStretch();sc.setWidget(navwidget);sl.addWidget(sc,1);self.avatar=QLabel();self.avatar.setFixedSize(40,40);self.profile_name=label(store.setting('display-name','Meu perfil'));foot=QHBoxLayout();foot.addWidget(self.avatar);foot.addWidget(self.profile_name,1);sl.addLayout(foot);self.update_avatar();row.addWidget(self.sidebar)
        area=QWidget();al=QVBoxLayout(area);al.setContentsMargins(30,20,30,20);al.setSpacing(20);self.top=FlowLayout();toggle=button('Painel lateral',self.toggle_sidebar);toggle.setToolTip('Mostrar ou ocultar navegação • Ctrl+\\');self.top.addWidget(toggle);self.top.addWidget(button('Buscar ações  Ctrl+K',self.command_palette));self.top.addStretch();self.top.addWidget(button('‹',lambda:self.change_month(-1)));self.period=QComboBox();self.period.setMinimumWidth(170);self.refresh_periods();self.period.currentIndexChanged.connect(self.render);self.top.addWidget(self.period);self.top.addWidget(button('›',lambda:self.change_month(1)));self.top.addWidget(button('+ Lançamento',self.edit_tx,True));al.addLayout(self.top)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame);al.addWidget(self.scroll);row.addWidget(area,1);self.make_menus();self.render();self.backup_timer=QTimer(self);self.backup_timer.timeout.connect(self.automatic_backup);self.backup_timer.start(30*60*1000);QTimer.singleShot(1000,self.automatic_backup);self.statusBar().showMessage('Dados locais • Elisei '+ui.VERSION)
    def apply_theme(self):
        import core
        core.PRIVACY_MODE=self.s.setting('privacy-mode')=='1'
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
        privacy=QAction('Ocultar valores',self);privacy.setCheckable(True);privacy.setChecked(self.s.setting('privacy-mode')=='1');privacy.setShortcut('Ctrl+Shift+P');privacy.triggered.connect(self.set_privacy);view.addAction(privacy)
        a=QAction('Aparência escura',self);a.setCheckable(True);a.setChecked(self.s.setting('theme')=='dark');a.triggered.connect(lambda value:self.set_theme(value));view.addAction(a)
    def set_privacy(self,enabled):
        import core
        core.PRIVACY_MODE=enabled;QToolTip.hideText();self.s.set('privacy-mode','1' if enabled else '0');self.render()
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
        if getattr(self,'_rendered_page',None)=='Lançamentos' and self.page=='Lançamentos':
            self.tx_filter_state=(self.search.text(),self.kind_filter.currentText(),self.status_filter.currentText(),self.account_filter.currentText(),self.category_filter.currentText())
        elif self.page=='Lançamentos':self.tx_filter_state=None
        self._rendered_page=self.page
        for n,b in self.nav.items():b.setChecked(n==self.page)
        w=QWidget();self.body=QVBoxLayout(w);self.body.setContentsMargins(0,0,0,0);self.body.setSpacing(20);self.body.addWidget(label(self.page,'title'));self.p=self.period.currentData() or date.today().strftime('%Y-%m')
        if self.s.setting('demo')=='1':self.body.addWidget(label('Demonstração • dados fictícios','small'))
        views={'Visão geral':self.overview,'Lançamentos':self.transactions,'Agenda':self.agenda,'Cartões':self.cards_page,'Categorias':self.categories_page,'Contas bancárias':self.accounts,'Orçamentos':self.budgets,'Investimentos':self.portfolio,'Metas e câmbio':self.goals,'Simulações':self.simulations,'Análises':self.analysis,'Relatórios':self.reports,'Perfil':self.profile,'Dados e backup':self.data_page};views[self.page]();self.body.addStretch();self.scroll.setWidget(w)
        due=[x for x in self.ledger.due() if x['day']<=date.today().isoformat()];self.nav['Agenda'].setText('Agenda'+('  '+str(len(due)) if due else ''))
    def go(self,name):
        # Efeitos de opacidade no conteúdo rolável causavam artefatos nas tabelas em Windows.
        if self.anim:self.anim.stop()
        self.page=name;self.render()
    def overview(self):
        sm=self.s.summary(self.p);assets=sum(allocation(self.s).values());debt=self.ledger.outstanding();self.hint(month_label(self.p)+' • O essencial para decidir seu próximo passo.')
        self.metrics([('Patrimônio líquido atual',money(assets-debt),'Ativos menos parcelas de cartão em aberto'),('Receitas',money(sm['Receita']),'Valores confirmados ou a revisar'),('Despesas do mês',money(sm['Despesa']),'Consumo em conta + compras na fatura'),('Fluxo de caixa',money(sm['livre']),'Entradas menos saídas efetivas registradas')])
        due=[x for x in self.ledger.due() if x['day']<=(date.today()+timedelta(days=7)).isoformat()];row=QHBoxLayout();a,l=card('Atrasados e próximos 7 dias');l.addWidget(label(money(sum((x['amount'] or 0) for x in due if x['kind'] not in ['Receita','Resgate'])),'metric'));l.addWidget(label(str(len(due))+' contas ou faturas para conferir','subtitle'));l.addWidget(button('Ver agenda',lambda:self.go('Agenda')));row.addWidget(a)
        g=self.s.rows('SELECT * FROM goals ORDER BY id LIMIT 1')[0];assessment=goal_assessment(self.s,g,self.p);a,l=card(g['name']);l.addWidget(label(money(assessment['base'])+' de '+money(g['target']),'section'));progress=QProgressBar();progress.setTextVisible(False);progress.setRange(0,1000);progress.setValue(min(1000,max(0,round(assessment['base']/max(1,g['target'])*1000))));l.addWidget(progress);l.addWidget(label('Aporte calculado: '+money(assessment['need'])+'/mês','subtitle'));l.addWidget(button('Entender minha meta',lambda:self.go('Metas e câmbio')));row.addWidget(a);row.setStretch(0,1);row.setStretch(1,1);self.body.addLayout(row)
        row=QHBoxLayout();a,l=card('Receitas e despesas');periods=[p for p in self.s.periods() if p<=self.p][-6:];stats=[self.s.summary(p) for p in periods];chart=InteractiveChart('bar',[('Receitas',[x['Receita'] for x in stats]),('Despesas',[x['Despesa'] for x in stats])],[p[5:]+'/'+p[2:4] for p in periods]);chart.setCursor(Qt.PointingHandCursor);chart.selected.connect(lambda selected:self.flow_chart_detail(selected,periods));l.addWidget(chart);row.addWidget(a,1)
        a,l=card('Onde você gastou');spent=self.ledger.category_spend(self.p);chart=InteractiveChart('donut',[(k,[v]) for k,v in sorted(spent.items(),key=lambda x:x[1],reverse=True)],center='Despesas');chart.selected.connect(self.spending_detail);l.addWidget(chart);l.addWidget(label('Passe o cursor para ver valores. Clique para abrir lançamentos.','small'));row.addWidget(a,1);self.body.addLayout(row)
        a,l=card('Seu dinheiro hoje');groups=allocation(self.s);l.addWidget(InteractiveChart('donut',[(k,[v]) for k,v in groups.items() if v>0],center='Ativos'));l.addWidget(label('Patrimônio bruto: '+money(assets)+' • Cartões a quitar: '+money(debt),'small',True));self.body.addWidget(a)
        notes=insights(self.s,self.p)
        if notes:a,l=card(notes[0][0]);l.addWidget(label(notes[0][1],None,True));l.addWidget(button('Ver todas as análises',lambda:self.go('Análises')));self.body.addWidget(a)
    def transactions(self):
        self.hint('Registre o que entrou, saiu e ainda vai vencer. Compras de cartão ficam na tela Cartões; o pagamento da fatura aparece aqui sem duplicar o consumo.')
        row=QHBoxLayout();self.search=QLineEdit();self.search.setAccessibleName('Buscar lançamentos');self.search.setPlaceholderText('Buscar descrição, categoria, etiqueta ou conta');row.addWidget(self.search,1);row.addWidget(button('Importar extrato',self.import_statement_ui));self.body.addLayout(row)
        row=FlowLayout();self.kind_filter=QComboBox();self.kind_filter.addItems(['Todos os tipos']+KINDS);self.status_filter=QComboBox();self.status_filter.addItems(['Todas as situações','Confirmado','Previsto','A revisar','Sem valor']);self.account_filter=QComboBox();self.account_filter.addItems(['Todas as contas']+[x['name'] for x in self.s.rows('SELECT name FROM accounts ORDER BY name')]);self.category_filter=QComboBox();self.category_filter.addItems(['Todas as categorias']+self.s.category_names())
        for name,w in [('Tipo',self.kind_filter),('Situação',self.status_filter),('Conta',self.account_filter),('Categoria',self.category_filter)]:w.setAccessibleName('Filtrar por '+name);row.addWidget(w)
        self.body.addLayout(row);self.tx_table=table(['Data','Descrição','Tipo','Categoria','Valor','Conta','Situação'],[]);self.tx_table.setMinimumHeight(360);self.tx_table.cellDoubleClicked.connect(lambda *_:self.edit_selected());self.tx_table.itemSelectionChanged.connect(self.tx_detail);self.body.addWidget(self.tx_table)
        row=QHBoxLayout()
        for text,fn in [('Editar',self.edit_selected),('Confirmar pagamento',self.confirm_selected),('Comprovantes',self.attachments_ui),('Excluir',self.delete_selected)]:row.addWidget(button(text,fn))
        row.addStretch();self.body.addLayout(row);self.tx_info=label('Selecione um lançamento para ver sua origem e observações.','small',True);self.body.addWidget(self.tx_info)
        state=getattr(self,'tx_filter_state',None)
        if state:
            self.search.setText(state[0])
            for combo,value in zip([self.kind_filter,self.status_filter,self.account_filter,self.category_filter],state[1:]):
                if combo.findText(value)>=0:combo.setCurrentText(value)
        self.search.textChanged.connect(self.fill_transactions)
        for combo in [self.kind_filter,self.status_filter,self.account_filter,self.category_filter]:combo.currentTextChanged.connect(self.fill_transactions)
        self.fill_transactions()
    def fill_transactions(self,*_):
        query=self.search.text().casefold();kind=self.kind_filter.currentText();status=self.status_filter.currentText();account=self.account_filter.currentText();category=self.category_filter.currentText();rows=self.s.rows('SELECT * FROM tx WHERE period=? ORDER BY COALESCE(day,period) DESC,id DESC',(self.p,));self.tx_rows=[x for x in rows if (kind=='Todos os tipos' or x['kind']==kind) and (status=='Todas as situações' or (x['amount'] is None if status=='Sem valor' else x['status']==status)) and (account=='Todas as contas' or account==x['account'] or account==x['target_account']) and (category=='Todas as categorias' or category==x['category']) and query in ' '.join(str(x.get(k) or '') for k in ['description','category','account','tags','note']).casefold()]
        self.tx_table.blockSignals(True);self.tx_table.clearSelection();self.tx_table.setRowCount(len(self.tx_rows))
        for i,x in enumerate(self.tx_rows):
            for j,v in enumerate([x['day'] or 'Sem data',x['description'],x['kind'],x['category'],money(x['amount']) if x['amount'] is not None else 'Sem valor',x['account'] or 'Não definida',x['status']]):item=QTableWidgetItem(str(v));item.setToolTip(x['note'] or '');self.tx_table.setItem(i,j,item)
        self.tx_table.blockSignals(False);self.tx_info.setText(str(len(self.tx_rows))+' lançamentos encontrados. Selecione uma linha para editar, confirmar ou adicionar comprovantes.');self.tx_table.setAccessibleDescription(str(len(self.tx_rows))+' lançamentos encontrados')
    def tx_detail(self):
        i=self.tx_table.currentRow()
        if i<0 or i>=len(getattr(self,'tx_rows',[])):return
        row=self.tx_rows[i];self.tx_info.setText(' • '.join(str(x) for x in [row['source'] or 'Cadastro manual',row['tags'],row['note']] if x))
    def edit_tx(self,data=None,scheduled=False):
        if not isinstance(data,dict):data=None
        if data and data['kind']=='Pagamento de fatura':QMessageBox.information(self,'Pagamento de fatura','Consulte ou desfaça esse registro na tela Cartões.');return
        f=EntryDialog(self.s,self.p,data,self)
        if scheduled:f.status.setCurrentText('Previsto')
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
        if self.s.rows('SELECT 1 FROM investment_events WHERE tx_id=?',(row['id'],)):QMessageBox.information(self,'Movimento da carteira','Desfaça este movimento no Histórico mensal de Investimentos para manter caixa e carteira coerentes.');return
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
        self.body.addWidget(button('+ Agendar compromisso',lambda:self.edit_tx(scheduled=True),True))
        self.hint('Contas previstas e faturas em aberto. Confirmar um registro aqui apenas atualiza o Horizonte; nenhum pagamento é enviado ao banco.')
        all_items=self.ledger.due();self.agenda_rows=[x for x in all_items if x['day'][:7]<=self.p];overdue=[x for x in self.agenda_rows if x['status']=='Atrasado'];self.metrics([('Em atraso',money(sum((x['amount'] or 0) for x in overdue if x['kind'] not in ['Receita','Resgate'])),str(len(overdue))+' registros para conferir'),('A pagar',money(sum((x['amount'] or 0) for x in self.agenda_rows if x['kind'] not in ['Receita','Resgate'])),'Até o mês selecionado'),('A receber',money(sum((x['amount'] or 0) for x in self.agenda_rows if x['kind'] in ['Receita','Resgate'])),'Receitas previstas')])
        self.agenda_table=table(['Vencimento','Descrição','Tipo','Valor','Conta','Situação'],[[x['day'],x['description'],x['kind'],money(x['amount']) if x['amount'] is not None else 'Sem valor',x['account'],x['status']] for x in self.agenda_rows]);self.body.addWidget(self.agenda_table);self.agenda_table.cellDoubleClicked.connect(lambda *_:self.agenda_edit());self.body.addWidget(button('Editar compromisso',self.agenda_edit));self.body.addWidget(button('Registrar pagamento ou recebimento',self.agenda_confirm,True));self.hint('A agenda mostra o mês selecionado e atrasados anteriores. Previsões posteriores aparecem ao avançar o mês no topo.')
    def agenda_confirm(self):
        i=self.agenda_table.currentRow()
        if i<0:self.notify('Selecione um compromisso na tabela.');return
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
        row=FlowLayout();row.addWidget(button('Definir limite',self.edit_budget,True));row.addWidget(button('Copiar mês anterior',self.copy_budgets_ui));row.addWidget(button('Remover limite',self.remove_budget));row.addStretch();self.body.addLayout(row)
        budgets={r['category']:r['amount'] for r in self.s.rows('SELECT * FROM budgets WHERE period=?',(self.p,))};spent=self.ledger.category_spend(self.p);self.budget_rows=sorted(set(budgets)|set(spent));rows=[]
        for name in self.budget_rows:
            limit=budgets.get(name);used=self.ledger.budget_spend(self.p,name) if limit is not None else spent.get(name,0);rows.append([name,money(used),money(limit) if limit is not None else 'Não definido',money(limit-used) if limit is not None else '—','Acima do limite' if limit is not None and used>limit else 'Dentro do limite' if limit is not None else 'Definir limite'])
        self.budget_table=table(['Categoria','Consumido','Limite','Disponível','Situação'],rows);self.budget_table.cellDoubleClicked.connect(lambda *_:self.edit_budget());self.body.addWidget(self.budget_table)
    def copy_budgets_ui(self):
        if self.s.rows('SELECT 1 FROM budgets WHERE period=?',(self.p,)) and QMessageBox.question(self,'Copiar limites','Substituir limites deste mês pelos do mês anterior?')!=QMessageBox.Yes:return
        if not self.s.rows('SELECT 1 FROM budgets WHERE period=?',(add_month(self.p,-1),)):self.notify('O mês anterior não tem limites para copiar.');return
        self.ledger.copy_budgets(add_month(self.p,-1),self.p);self.render();self.notify('Limites copiados do mês anterior.')
    def cards_page(self):
        self.hint('Compras e parcelas são despesas de consumo. Registrar pagamento reduz a conta e a dívida, sem gerar outra despesa.')
        cards=self.s.rows('SELECT * FROM cards WHERE archived=0 ORDER BY name');row=FlowLayout();row.addWidget(button('+ Cartão',self.edit_card,True))
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
        super().data_page();self.body.insertWidget(2,button('Verificar integridade e consistência',self.run_diagnostics_ui,True));self.body.insertWidget(3,button('Importar ou conciliar CSV/OFX',self.import_statement_ui))
    def restore(self):
        path,_=QFileDialog.getOpenFileName(self,'Restaurar backup','','SQLite (*.sqlite)')
        if not path:return
        if QMessageBox.question(self,'Restaurar backup','Substituir os dados atuais por esta cópia? Será feito um backup antes da restauração. Cópias da versão 0.1 são migradas automaticamente.')!=QMessageBox.Yes:return
        try:
            previous=self.ledger.restore_backup(path);self._profile_draft={};self.refresh_periods();self.profile_name.setText(self.s.setting('display-name','Meu perfil'));self.update_avatar();self.apply_theme();self.render();self.notify('Backup restaurado. Cópia anterior: '+str(previous))
        except (ValueError,OSError,sqlite3.Error) as e:QMessageBox.warning(self,'Backup',str(e))
    def reports(self):
        super().reports()
        w,l=card('Despesas por categoria • '+month_label(self.p));spent=self.ledger.category_spend(self.p);l.addWidget(table(['Categoria','Consumo'],[[k,money(v)] for k,v in sorted(spent.items(),key=lambda x:x[1],reverse=True)]));self.body.addWidget(w)
        w,l=card('Cartões e faturas');rows=[]
        for c in self.s.rows('SELECT * FROM cards ORDER BY name'):
            inv=self.ledger.invoice(c['id'],self.p);rows.append([c['name'],money(inv['total']),money(inv['paid']),money(inv['remaining']),inv['due_day']])
        l.addWidget(table(['Cartão','Compras','Pago','Em aberto','Vencimento'],rows));self.body.addWidget(w)
        from investments import InvestmentBook
        w,l=card('Carteira mês a mês • '+month_label(self.p));monthly=InvestmentBook(self.s).monthly(self.p);l.addWidget(table(['Ativo','Saldo anterior','Aportes','Resgates','Saldo registrado','Variação'],[[r['position']['name']]+[money(r[k]) if r[k] is not None else 'Sem base' for k in ['opening','contribution','withdrawal','closing','gain']] for r in monthly]));self.body.addWidget(w)

    def analysis(self):
        self.hint('Leituras locais e explicáveis, com base nos registros disponíveis. Valores a revisar e meses incompletos limitam a precisão das médias.')
        cap=recent_capacity(self.s,self.p);self.metrics([('Receita média',money(cap['income']),'Até três meses com dados'),('Consumo médio',money(cap['expense']),'Conta + compras de cartão'),('Capacidade média de aporte',money(cap['capacity']),'Receita menos consumo registrado')])
        for title,text in insights(self.s,self.p):w,l=card(title);l.addWidget(label(text,None,True));self.body.addWidget(w)
        periods=cap['periods'];direct=round(sum(self.s.summary(p)['Despesa em conta'] for p in periods)/len(periods)) if periods else 0;rows=[];values=[];labels=[];cumulative=0
        for i in range(1,13):
            period=add_month(self.p,i);planned={r['kind']:r['n'] or 0 for r in self.s.rows("SELECT kind,SUM(amount) n FROM tx WHERE period=? GROUP BY kind",(period,))};revenue=planned.get('Receita',cap['income']);expense=planned.get('Despesa',direct);card_due=sum(self.ledger.invoice(c['id'],period)['remaining'] for c in self.s.rows('SELECT id FROM cards'))+planned.get('Pagamento de fatura',0);aporte=planned.get('Aporte',0);net=revenue-expense-card_due-aporte+planned.get('Resgate',0);cumulative+=net;values.append(cumulative);labels.append(period[2:]);rows.append([period,money(revenue),money(expense),money(card_due),money(aporte),money(net),money(cumulative)])
        w,l=card('Compromissos dos próximos 12 meses');l.addWidget(InteractiveChart('line',[('Fluxo acumulado',values)],labels));l.addWidget(table(['Mês','Receita','Gastos em conta','Faturas conhecidas','Aportes','Fluxo','Acumulado'],rows));l.addWidget(label('Receitas e gastos diretos usam os registros confirmados, a revisar e previstos daquele tipo no mês, se existentes; caso contrário usam a média histórica. Faturas incluem apenas compras já registradas. Aportes previstos são separados. O acumulado começa em zero e não é patrimônio.','small',True));self.body.addWidget(w)

    def spending_detail(self,category):
        d=QDialog(self);d.setWindowTitle('Gastos de '+category);d.resize(900,560);layout=QVBoxLayout(d);layout.addWidget(label(category+' • '+month_label(self.p),'section'))
        direct=self.s.rows("SELECT day,description,amount,account FROM tx WHERE period=? AND category=? AND kind='Despesa' AND status!='Previsto'",(self.p,category))
        purchases=self.s.rows('SELECT purchase_day AS day,description,amount,card_id FROM card_items WHERE period=? AND category=?',(self.p,category))
        rows=[[x['day'] or 'Sem data',x['description'],money(x['amount']) if x['amount'] is not None else 'Sem valor',x['account'],'Em conta'] for x in direct]
        rows += [[x['day'],x['description'],money(x['amount']),self.s.rows('SELECT name FROM cards WHERE id=?',(x['card_id'],))[0]['name'],'Compra no cartão'] for x in purchases]
        layout.addWidget(table(['Data','Descrição','Valor','Conta / cartão','Origem'],rows));layout.addWidget(label('Consumo por competência. O pagamento da fatura não é contado novamente.','small',True));layout.addWidget(button('Fechar',d.accept));d.exec()
    def agenda_edit(self):
        i=self.agenda_table.currentRow()
        if i<0:self.notify('Selecione um compromisso na tabela.');return
        row=self.agenda_rows[i]
        if row['type']=='card':
            self.selected_card=row['id'];idx=self.period.findData(row['period'])
            if idx>=0:self.period.setCurrentIndex(idx)
            self.go('Cartões')
        else:self.edit_tx(self.s.rows('SELECT * FROM tx WHERE id=?',(row['id'],))[0])
    def edit_budget(self):
        i=self.budget_table.currentRow();category=self.budget_rows[i] if i>=0 else 'Alimentação'
        options=sorted(set(self.s.category_names()+[category]));existing=self.s.rows('SELECT amount FROM budgets WHERE category=? AND period=?',(category,self.p));amount=existing[0]['amount'] if existing else 0
        f=Form('Orçamento de '+month_label(self.p),[('category','Categoria',category,options),('amount','Limite em R$',str(amount/100).replace('.',','),None)],self)
        while f.exec():
            try:
                v=f.values();amount=cents(v['amount'])
                if amount<0:raise ValueError('O limite deve ser positivo ou zero.')
                with self.s.db:self.s.db.execute('INSERT OR REPLACE INTO budgets VALUES (?,?,?)',(v['category'],self.p,amount))
                self.render();self.notify('Limite salvo para '+v['category']+'.');break
            except (ValueError,sqlite3.Error) as e:f.error.setText(str(e))
    def remove_budget(self):
        i=self.budget_table.currentRow()
        if i<0:self.notify('Selecione uma categoria na tabela.');return
        category=self.budget_rows[i]
        if not self.s.rows('SELECT 1 FROM budgets WHERE category=? AND period=?',(category,self.p)):self.notify('Esta categoria ainda não tem limite definido.');return
        if QMessageBox.question(self,'Remover limite','Remover somente o limite de '+category+' neste mês? Os gastos serão preservados.')!=QMessageBox.Yes:return
        with self.s.db:self.s.db.execute('DELETE FROM budgets WHERE category=? AND period=?',(category,self.p))
        self.render();self.notify('Limite removido; gastos preservados.')
    def metrics(self,items):
        cards=[]
        for title,value,note in items:
            w,l=card();l.addWidget(label(title,'subtitle',True));l.addWidget(label(value,'metric',True));l.addWidget(label(note,'small',True));cards.append(w)
        self.body.addWidget(ResponsiveCards(cards))
    def report_document(self):
        from html import escape
        from PySide6.QtCore import QUrl
        doc=ui.QTextDocument();doc.setDefaultFont(QFont('Segoe UI',9));parts=['<h1>Elisei — relatório financeiro</h1>','<p>Competência: '+escape(month_label(self.p))+' • Gerado em '+date.today().isoformat()+'</p>']
        if self.s.setting('demo')=='1':parts.append('<p>DEMONSTRAÇÃO: dados fictícios.</p>')
        parts.append('<p>Ativos e dívidas representam a posição atual cadastrada; fluxos e consumo respeitam a competência selecionada.</p>')
        index=0
        for frame in self.scroll.widget().findChildren(QFrame):
            if frame.objectName()!='card':continue
            titles=[x.text() for x in frame.findChildren(QLabel) if x.objectName() in ['section','subtitle']];metrics=[x.text() for x in frame.findChildren(QLabel) if x.objectName()=='metric']
            if titles:parts.append('<h2>'+escape(titles[0])+'</h2>')
            for value in metrics:parts.append('<p><strong>'+escape(value)+'</strong></p>')
            for t in frame.findChildren(QTableWidget):
                parts.append('<table border="1" cellpadding="5" cellspacing="0" width="100%"><tr>'+''.join('<th>'+escape(t.horizontalHeaderItem(j).text())+'</th>' for j in range(t.columnCount()))+'</tr>')
                for i in range(t.rowCount()):parts.append('<tr>'+''.join('<td>'+escape(t.item(i,j).text() if t.item(i,j) else '')+'</td>' for j in range(t.columnCount()))+'</tr>')
                parts.append('</table><br>')
            for chart in frame.findChildren(InteractiveChart):
                image=chart.grab().toImage();key='chart'+str(index);index+=1;doc.addResource(ui.QTextDocument.ImageResource,QUrl(key),image);parts.append('<p><img src="'+key+'" width="680" height="'+str(round(image.height()*680/max(1,image.width())))+'" /></p>')
        parts.append('<p>Pagamentos de fatura reduzem caixa e dívida; não duplicam o consumo. Projeções são hipóteses nominais. Confira saldos e datas no banco real.</p>');doc.setHtml(''.join(parts));return doc
    def export_report(self):
        from PySide6.QtPrintSupport import QPrinter
        from PySide6.QtGui import QPageLayout
        path,_=QFileDialog.getSaveFileName(self,'Relatório PDF','Elisei-'+self.p+'.pdf','PDF (*.pdf)')
        if not path:return
        if not path.lower().endswith('.pdf'):path+='.pdf'
        try:
            printer=QPrinter(QPrinter.HighResolution);printer.setOutputFormat(QPrinter.PdfFormat);printer.setPageOrientation(QPageLayout.Landscape);printer.setOutputFileName(path);self.report_document().print_(printer);QMessageBox.information(self,'Relatório','PDF salvo com indicadores, seções, tabelas e gráficos.')
        except Exception as e:QMessageBox.warning(self,'Relatório',str(e))
    def automatic_backup(self):
        if not getattr(self,'_closing',False):super().automatic_backup()
    def closeEvent(self,event):
        self._closing=True;self.backup_timer.stop()
        if self.anim:self.anim.stop()
        super().closeEvent(event)
    def update_avatar(self):
        from photos import circle_pixmap
        data=self.s.setting('profile-photo');image=ui.QImage.fromData(base64.b64decode(data)) if data else ui.QImage()
        if not image.isNull():self.avatar.setStyleSheet('');self.avatar.setPixmap(circle_pixmap(image,40))
        else:
            self.avatar.clear();self.avatar.setText((self.s.setting('display-name') or 'H')[:1].upper());self.avatar.setAlignment(Qt.AlignCenter);self.avatar.setStyleSheet('background:#dbeaff;border-radius:20px;color:#0056b3;font-size:20px;font-weight:600;')
    def profile(self):
        from photos import circle_pixmap
        super().profile();frame=self.body.itemAt(self.body.count()-1).widget();self.profile_photo=next(x for x in frame.findChildren(QLabel) if x.width()==120 and x.height()==120);data=self.s.setting('profile-photo')
        if data:self.profile_photo.setPixmap(circle_pixmap(ui.QImage.fromData(base64.b64decode(data)),120))
        else:self.profile_photo.setStyleSheet('border:2px solid #0065d4;border-radius:60px;');self.profile_photo.setText('Sua foto')
        frame.layout().addWidget(button('Ajustar enquadramento',self.reframe_photo))
        for key,value in getattr(self,'_profile_draft',{}).items():self.profile_fields[key].setText(value)
    def remember_profile(self):self._profile_draft={k:w.text() for k,w in self.profile_fields.items()}
    def choose_photo(self):
        from PySide6.QtGui import QImageReader
        path,_=QFileDialog.getOpenFileName(self,'Foto de perfil','','Imagem (*.png *.jpg *.jpeg *.webp)')
        if not path:return
        try:
            if Path(path).stat().st_size>10*1024*1024:raise ValueError('Escolha uma imagem de até 10 MB.')
            reader=QImageReader(path);reader.setAutoTransform(True);size=reader.size()
            if size.width()*size.height()>40000000:raise ValueError('Escolha uma foto de até 40 megapixels.')
            if max(size.width(),size.height())>2048:size.scale(2048,2048,Qt.KeepAspectRatio);reader.setScaledSize(size)
            image=reader.read()
            if image.isNull():raise ValueError('Não foi possível abrir a imagem.')
            self.crop_photo(image)
        except (ValueError,OSError) as e:QMessageBox.warning(self,'Foto',str(e))
    def reframe_photo(self):
        data=self.s.setting('profile-photo-source') or self.s.setting('profile-photo')
        if not data:self.choose_photo();return
        self.crop_photo(ui.QImage.fromData(base64.b64decode(data)))
    def crop_photo(self,image):
        from photos import PhotoCropDialog
        from PySide6.QtCore import QBuffer,QIODevice
        if image.isNull():return
        dialog=PhotoCropDialog(image,self)
        if not dialog.exec():return
        def encode(im):
            buffer=QBuffer();buffer.open(QIODevice.WriteOnly);im.save(buffer,'PNG');return base64.b64encode(bytes(buffer.data())).decode('ascii')
        self.remember_profile();self.s.set('profile-photo-source',encode(image));self.s.set('profile-photo',encode(dialog.preview.cropped()));self.update_avatar();self.render()
    def remove_photo(self):
        self.remember_profile();self.s.set('profile-photo','');self.s.set('profile-photo-source','');self.update_avatar();self.render()
    def save_profile(self):
        self.remember_profile();super().save_profile()
    def portfolio(self):
        from investments import InvestmentBook,end_month
        self.book=InvestmentBook(self.s);all_positions=self.s.rows('SELECT * FROM positions ORDER BY institution,name');filter_type=getattr(self,'asset_filter','Todos');self.positions=[p for p in all_positions if filter_type=='Todos' or p['asset_type']==filter_type];monthly={r['position']['id']:r for r in self.book.monthly(self.p)};self.monthly_positions=[monthly[p['id']] for p in self.positions]
        total=sum(r['closing'] or 0 for r in self.monthly_positions);contributions=sum(r['contribution'] for r in self.monthly_positions);withdrawals=sum(r['withdrawal'] for r in self.monthly_positions);known=[r for r in self.monthly_positions if r['gain'] is not None];gain=sum(r['gain'] for r in known);unknown=sum(r['closing'] is None for r in self.monthly_positions)
        self.hint(month_label(self.p)+' • Aporte movimenta capital. Saldo conferido registra o valor do investimento. Estimativa não substitui o extrato.')
        self.metrics([('Saldo registrado',money(total),'Posição até o fim do mês selecionado'+(' • '+str(unknown)+' sem histórico' if unknown else '')),('Aportes do mês',money(contributions),'Movimentos vinculados aos ativos'),('Resgates do mês',money(withdrawals),'Saídas dos investimentos'),('Variação apurada',money(gain) if known else 'Sem base anterior',str(len(known))+' ativos com saldo anterior e conferência no mês')])
        unlinked=self.book.unlinked(self.p)
        if unlinked:self.banner(str(len(unlinked))+' aportes/resgates deste mês ainda não estão vinculados a um ativo. Em Registrar movimento, selecione o lançamento existente para evitar duplicar o caixa.')
        tools=FlowLayout();filterbox=QComboBox();filterbox.addItems(['Todos']+sorted(set(p['asset_type'] for p in all_positions)));filterbox.setCurrentText(filter_type);filterbox.currentTextChanged.connect(self.filter_assets);tools.addWidget(filterbox)
        for text,fn,primary in [('+ Adicionar posição',self.edit_position,False),('Atualizar saldo',self.invest_value_ui,True),('Registrar aporte / resgate',self.invest_event_ui,False),('Histórico mensal',self.invest_history_ui,False),('Editar posição',self.edit_position_selected,False),('Projetar ativo selecionado',self.project_position,False),('Excluir posição',self.delete_position,False)]:tools.addWidget(button(text,fn,primary))
        self.body.addLayout(tools)
        rows=[]
        for r in self.monthly_positions:
            p=r['position'];rows.append([p['name'],p['institution'],money(r['closing']) if r['closing'] is not None else 'Sem saldo registrado',money(r['contribution']),money(r['withdrawal']),money(r['gain']) if r['gain'] is not None else 'Não apurada',date.fromisoformat(r['quote_day']).strftime('%d/%m/%Y') if r['quote_day'] else 'Não informado'])
        self.position_table=table(['Investimento','Instituição','Saldo registrado','Aportes do mês','Resgates','Variação*','Último saldo'],rows);self.position_table.cellDoubleClicked.connect(lambda *_:self.invest_history_ui());self.body.addWidget(self.position_table);self.invest_detail=label('Selecione um investimento para ver indexador, vencimento e estimativa.','small',True);self.body.addWidget(self.invest_detail);self.position_table.itemSelectionChanged.connect(self.invest_selection)
        if self.positions:self.position_table.selectRow(0)
        self.hint('* Variação = saldo registrado − saldo anterior − aportes + resgates. Só é apurada quando há base anterior e uma conferência no mês. Pode incluir câmbio; não equivale a uma taxa de rentabilidade auditada. Sem conferência nova, o saldo é carregado e identificado pela data.')
        self.invest_monthly_chart()
        snap=self.s.rows('SELECT * FROM snapshots WHERE period=?',(self.p,))
        if snap:
            w,l=card('Histórico importado sem vínculo automático');l.addWidget(button('Associar saldo histórico ao ativo selecionado',self.link_imported_value));l.addWidget(label('Registros originais preservados. Associe conferências ao ativo correto; o aplicativo não inventa aportes ou saldos entre datas.','small',True));l.addWidget(table(['Descrição original','Grupo sugerido','Valor'],[[x['name'],x['group_name'],money(x['amount']) if x['amount'] is not None else 'Ausente'] for x in snap]));self.body.addWidget(w)
    def selected_investment(self):
        i=self.position_table.currentRow()
        if i<0 or i>=len(self.positions):self.notify('Selecione um investimento na tabela.');return None
        return self.positions[i]
    def invest_selection(self):
        p=self.selected_investment()
        if not p:return
        from investments import InvestmentBook,end_month
        state=InvestmentBook(self.s).state(p['id'],min(end_month(self.p),date.today().isoformat()),True);maturity=date.fromisoformat(p['maturity']).strftime('%d/%m/%Y') if p['maturity'] else 'Não informado';estimate=money(state['value']) if state else 'Sem base'
        self.invest_detail.setText(p['asset_type']+' • '+p['rate_mode']+' '+str(p['rate'])+' • Vencimento: '+maturity+' • Liquidez: '+p['liquidity']+' • Estimativa até a data de referência: '+estimate+' (hipótese sem novos aportes não registrados; câmbio constante; antes de tributos).')
    def invest_value_ui(self,*_,quote=None):
        p=self.selected_investment()
        if not p:return
        from investments import InvestmentBook,end_month
        book=InvestmentBook(self.s);day=quote['day'] if quote else min(end_month(self.p),date.today().isoformat());state=book.state(p['id'],day);native=quote['native_value'] if quote else state['native_value'] if state else 0;fx=quote['fx_rate'] if quote else state['fx_rate'] if state else p['fx_rate']
        f=Form('Conferir saldo • '+p['name'],[('day','Data do saldo',day,None),('amount','Saldo no extrato em '+p['currency'],str(native/100).replace('.',','),None),('fx_rate','Reais por unidade da moeda',fx,None)],self)
        while f.exec():
            try:
                v=f.values();book.save_value(p['id'],v['day'],cents(v['amount']),float(v['fx_rate'].replace(',','.')));self.refresh_periods();self.render();self.notify('Saldo conferido salvo no histórico. Não foi registrado como aporte.');break
            except (ValueError,OverflowError,sqlite3.Error) as e:f.error.setText(str(e))
    def invest_event_ui(self):
        p=self.selected_investment()
        if not p:return
        from investments import InvestmentBook,end_month
        book=InvestmentBook(self.s);unlinked=book.unlinked(self.p);choices={'Lançamento #'+str(r['id'])+' • '+r['description']+' • '+money(r['amount']):r for r in unlinked};options=['Criar lançamento vinculado','Sem novo lançamento de caixa']+list(choices);accounts=['']+[r['name'] for r in self.s.rows("SELECT name FROM accounts WHERE currency='BRL' ORDER BY name")];f=Form('Movimento • '+p['name'],[('kind','Movimento','Aporte',['Aporte','Resgate']),('day','Data realizada',min(end_month(self.p),date.today().isoformat()),None),('amount','Valor em '+p['currency'],'',None),('fx_rate','Reais por unidade da moeda',p['fx_rate'],None),('link','Registro no caixa',options[0],options),('in_balance','Conferência de saldo','Não, somar ao saldo',['Não, somar ao saldo','Sim, já incluído no extrato']),('account','Conta em reais (opcional)','',accounts),('note','Observações','',None)],self)
        def choose(text):
            source=choices.get(text)
            if source:
                f.inputs['in_balance'].setCurrentText('Sim, já incluído no extrato');f.inputs['kind'].setCurrentText(source['kind']);f.inputs['amount'].setText(str(round(source['amount']/max(.000001,p['fx_rate']))/100).replace('.',','));f.inputs['day'].set_iso(source['day'] if source['day'] and source['day'][:7]==self.p else min(end_month(self.p),date.today().isoformat()));f.inputs['account'].setCurrentText(source['account'])
        f.inputs['link'].currentTextChanged.connect(choose)
        while f.exec():
            try:
                v=f.values();source=choices.get(v['link']);book.add_event(p['id'],v['day'],v['kind'],cents(v['amount']),float(v['fx_rate'].replace(',','.')),v['account'],source['id'] if source else None,v['note'],v['link']==options[0],v['in_balance'].startswith('Sim'));self.refresh_periods();self.render();self.notify('Movimento registrado no mês, sem duplicar o lançamento vinculado.');break
            except (ValueError,OverflowError,sqlite3.Error) as e:f.error.setText(str(e))
    def invest_monthly_chart(self):
        from investments import InvestmentBook
        from ledger import add_month
        book=InvestmentBook(self.s);periods=[add_month(self.p,i) for i in range(-11,1)];monthly=[book.monthly(p) for p in periods];points=[(p,rows) for p,rows in zip(periods,monthly) if any(r['closing'] is not None for r in rows)];w,l=card('Evolução da carteira registrada')
        l.addWidget(InteractiveChart('line',[('Saldo registrado',[sum(r['closing'] or 0 for r in rows) for _,rows in points])],[p[5:]+'/'+p[2:4] for p,_ in points],height=230));l.addWidget(label('Meses sem base não viram saldo zero. Saldos carregados mantêm sua data de conferência na tabela.','small',True));self.body.addWidget(w)
    def invest_history_ui(self):
        p=self.selected_investment()
        if not p:return
        from investments import InvestmentBook
        from ledger import add_month
        book=InvestmentBook(self.s);d=QDialog(self);d.setWindowTitle('Histórico • '+p['name']);d.resize(1050,740);layout=QVBoxLayout(d);layout.addWidget(label(p['name'],'section'));tabs=QTabWidget();layout.addWidget(tabs);periods=[add_month(self.p,i) for i in range(-11,1)];history=[book.monthly(period,p['id'])[0] for period in periods];monthly=QWidget();ml=QVBoxLayout(monthly);known=[(period,r) for period,r in zip(periods,history) if r['closing'] is not None];ml.addWidget(InteractiveChart('line',[('Saldo registrado',[r['closing'] for _,r in known])],[x[0][5:]+'/'+x[0][2:4] for x in known],height=190));ml.addWidget(table(['Mês','Saldo anterior','Aportes','Resgates','Saldo registrado','Variação'],[[period]+[money(r[k]) if r[k] is not None else 'Sem base' for k in ['opening','contribution','withdrawal','closing','gain']] for period,r in zip(periods,history)]));tabs.addTab(monthly,'Mês a mês')
        events=self.s.rows('SELECT e.*,t.account FROM investment_events e LEFT JOIN tx t ON t.id=e.tx_id WHERE e.position_id=? ORDER BY e.day DESC,e.id DESC',(p['id'],));event_page=QWidget();el=QVBoxLayout(event_page);el.addWidget(table(['Data','Tipo','Valor BRL','Conta','Lançamento'],[[date.fromisoformat(x['day']).strftime('%d/%m/%Y'),x['kind'],money(x['amount']),x['account'] or 'Não vinculada','#'+str(x['tx_id']) if x['tx_id'] else 'Sem caixa'] for x in events]))
        def undo():
            if QMessageBox.question(d,'Desfazer movimento','Desfazer o último movimento cadastrado neste ativo? Um lançamento criado pela carteira também será removido; um lançamento apenas vinculado será preservado.')!=QMessageBox.Yes:return
            try:book.delete_latest_event(p['id']);d.accept();self.render()
            except ValueError as e:QMessageBox.warning(d,'Movimento',str(e))
        el.addWidget(button('Desfazer último movimento',undo));tabs.addTab(event_page,'Movimentos')
        quotes=self.s.rows('SELECT * FROM investment_values WHERE position_id=? ORDER BY day DESC,id DESC',(p['id'],));page=QWidget();ql=QVBoxLayout(page);qt=table(['Data','Saldo BRL','Origem'],[[date.fromisoformat(q['day']).strftime('%d/%m/%Y'),money(q['value']),q['origin']] for q in quotes]);ql.addWidget(qt)
        def edit_quote():
            i=qt.currentRow()
            if i<0:return
            d.accept();self.invest_value_ui(quote=quotes[i])
        def remove_quote():
            i=qt.currentRow()
            if i<0:return
            if QMessageBox.question(d,'Excluir conferência','Excluir somente esse saldo do histórico?')!=QMessageBox.Yes:return
            try:book.delete_value(quotes[i]['id']);d.accept();self.render()
            except ValueError as e:QMessageBox.warning(d,'Conferência',str(e))
        ql.addWidget(button('Editar saldo selecionado',edit_quote));ql.addWidget(button('Excluir saldo selecionado',remove_quote));tabs.addTab(page,'Saldos conferidos');layout.addWidget(button('Fechar',d.accept));d.exec()
    def edit_position(self,data=None):
        from investments import InvestmentBook
        before={p['id']:p for p in self.s.rows('SELECT * FROM positions')};InvestmentBook(self.s);super().edit_position(data)
        for p in self.s.rows('SELECT * FROM positions'):
            previous=before.get(p['id'])
            if not previous or any(p[k]!=previous[k] for k in ['value','native_value','fx_rate','day']):InvestmentBook(self.s).save_value(p['id'],p['day'],p['native_value'] if p['native_value'] is not None else p['value'],p['fx_rate'])
        self.refresh_periods();self.render()
    def run_diagnostics_ui(self):
        from diagnostics import run_diagnostics
        report=run_diagnostics(self.s);d=QDialog(self);d.setWindowTitle('Diagnóstico do Elisei');d.resize(780,580);layout=QVBoxLayout(d);layout.addWidget(label('Verificações concluídas' if report['passed'] else 'Há registros para revisar','section'));layout.addWidget(table(['Verificação','Resultado','Detalhe'],[[x['name'],'OK' if x['status']=='ok' else 'Revisar',x['detail']] for x in report['checks']]));layout.addWidget(label(report['scope'],'small',True))
        def save():
            path,_=QFileDialog.getSaveFileName(d,'Salvar diagnóstico','Elisei-diagnostico.json','JSON (*.json)')
            if path:
                try:Path(path).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');QMessageBox.information(d,'Diagnóstico','Relatório salvo sem nomes, valores financeiros ou fotos.')
                except OSError as e:QMessageBox.warning(d,'Diagnóstico',str(e))
        layout.addWidget(button('Salvar diagnóstico',save));layout.addWidget(button('Fechar',d.accept));d.exec()

    def edit_selected(self):
        i=self.tx_table.currentRow()
        if i<0:self.notify('Selecione um lançamento na tabela.');return
        row=self.tx_rows[i]
        if self.s.rows('SELECT 1 FROM investment_events WHERE tx_id=?',(row['id'],)):QMessageBox.information(self,'Movimento vinculado','Esse registro está ligado à carteira. Use Histórico mensal para desfazer o movimento e cadastrá-lo corretamente.');return
        self.edit_tx(row)
    def link_imported_value(self):
        p=self.selected_investment()
        if not p:return
        snapshots=self.s.rows('SELECT * FROM snapshots WHERE period=? AND amount IS NOT NULL AND amount>=0 ORDER BY id',(self.p,))
        if not snapshots:QMessageBox.information(self,'Histórico importado','Não há saldo histórico preenchido neste mês. Use Atualizar saldo para registrar uma conferência.');return
        choices={'#'+str(x['id'])+' • '+x['name']+' • '+money(x['amount']):x for x in snapshots};f=Form('Associar saldo histórico • '+p['name'],[('source','Saldo importado',next(iter(choices)),list(choices)),('day','Confirme a data real do saldo',self.p+'-01',None)],self)
        while f.exec():
            try:
                from investments import InvestmentBook
                v=f.values();source=choices[v['source']]
                if v['day'][:7]!=self.p:raise ValueError('A data deve pertencer ao mês do registro importado.')
                # Fontes importadas são em BRL; para outra moeda a conversão exige conferência individual.
                if p['currency']!='BRL':raise ValueError('Esse histórico está em reais. Use Atualizar saldo para informar moeda e câmbio individualmente.')
                InvestmentBook(self.s).save_value(p['id'],v['day'],source['amount'],1,'Histórico importado #'+str(source['id']));self.refresh_periods();self.render();break
            except (ValueError,sqlite3.Error) as e:f.error.setText(str(e))

    def flow_chart_detail(self,selected,periods):
        if ' • ' not in selected:return
        kind,stamp=selected.split(' • ',1);lookup={p[5:]+'/'+p[2:4]:p for p in periods};period=lookup.get(stamp)
        if not period:return
        flow='Receita' if kind=='Receitas' else 'Despesa';rows=[[r['day'] or 'Sem data',r['description'],r['category'],money(r['amount']) if r['amount'] is not None else 'Sem valor',r['account'] or 'Não definida'] for r in self.s.rows("SELECT * FROM tx WHERE period=? AND kind=? AND status!='Previsto'",(period,flow))]
        if flow=='Despesa':rows += [[r['purchase_day'],r['description'],r['category'],money(r['amount']),'Compra no cartão'] for r in self.s.rows('SELECT * FROM card_items WHERE period=?',(period,))]
        d=QDialog(self);d.setWindowTitle(kind+' • '+month_label(period));d.resize(950,560);layout=QVBoxLayout(d);layout.addWidget(label(d.windowTitle(),'section'));layout.addWidget(table(['Data','Descrição','Categoria','Valor','Conta / origem'],rows));layout.addWidget(button('Fechar',d.accept));d.exec()
    
