# Arquitetura e modelo financeiro

## Componentes

- `src/app.py`: janela, navegação, formulários, gráficos QPainter, importação/exportação e consulta de câmbio em QThread.
- `src/core.py`: SQLite, migrações, leitura do layout opcional de Excel, conversão monetária e matemática de juros compostos.
- `src/finance.py`: projeções por ativo, capacidade de aporte, avaliação de metas e diagnósticos determinísticos.
- `src/demo.py`: gerador de dados sintéticos em banco separado.

SQLite possui tabelas de lançamentos, posições históricas, carteira, orçamentos, metas, configurações e histórico de importações, além de contas bancárias. Perfil e foto em base64 ficam nas configurações do banco. Não existe serviço HTTP local. A única requisição externa do produto consulta BRL/JPY sem enviar saldos ou gastos.

## Definições

Fluxo disponível = receitas − despesas em conta − aportes + resgates − pagamentos de fatura. Compras no cartão entram no consumo do mês de fatura, enquanto o pagamento reduz caixa e dívida sem duplicar o consumo. Transferências não alteram esse total. Esse fluxo não é patrimônio nem saldo bancário conciliado.

Capacidade de aporte = receita média − despesa média dos últimos até três meses com dados, até a competência selecionada. Inclui registros a revisar preenchidos; o app sinaliza essa condição. Meses parciais ou registros ausentes limitam a qualidade da análise.

Meta = recursos disponíveis projetados + valor futuro de novos aportes. O aporte necessário é calculado pela diferença entre objetivo e recursos projetados, dividida pelo fator de acumulação de aportes no fim do mês. Quando não há ativos vinculados, usa-se o reservado manual e a taxa da meta.

## Convenções das projeções

Prefixado: saldo × (1 + taxa anual)^(dias corridos/365).

IPCA + spread: saldo × [(1 + IPCA) × (1 + spread)]^(dias corridos/365).

Percentual do CDI: converte CDI anual em taxa diária de 252 dias; multiplica a taxa diária pelo percentual contratado; capitaliza pelos dias de segunda a sexta do intervalo. Não desconta feriados. Trata-se de aproximação, não extrato bancário.

Imposto = máximo(0, saldo bruto projetado − custo informado) × alíquota manual. Sem custo, considera o saldo informado como base e avisa que só estima imposto sobre crescimento futuro. IOF, taxas e mudanças legais não são inferidos.

No cenário mensal, a taxa incide sobre o capital do início do mês, seguida por aporte, bônus e retirada. A reserva preservada é subtraída do capital simulado e não rende dentro do cenário. Não há ajuste por inflação nessa tela.

## Persistência e privacidade

Não há credenciais ou telemetria. Dados locais não criptografados. Backup usa a API de backup do SQLite. Restauração verifica integridade, tabelas e colunas e faz cópia automática antes da substituição. CSV neutraliza células iniciadas por caracteres de fórmula. A importação usa hash de arquivo e chave de origem por aba/linha para evitar duplicação; versões alteradas não sobrescrevem linhas já importadas.


## Saldos em conta

Saldo conferido em moeda nativa convertido para BRL + lançamentos confirmados novos após o ID de conferência e a partir da data informada. Receita/resgate creditam; despesa/aporte debitam. Transferência debita origem e credita destino. Ao conferir um novo saldo, todos os lançamentos existentes são considerados já refletidos. Posições de investimentos precisam ser atualizadas separadamente após aporte/resgate. Para contas em moeda estrangeira, movimentos são em BRL; requer conferência após câmbio.

## Backup automático

Na abertura, a cada 30 minutos e no encerramento normal, grava uma cópia completa com nome por dia. Um arquivo temporário é produzido pela API SQLite e substitui atomicamente a cópia do dia. Não remove dias antigos. A pasta padrão fica junto aos dados e pode ser trocada na interface. Perfil, foto e configurações são portáveis no mesmo arquivo. Sem agendador externo.


## Evolução 0.2

`workspace.py` organiza a janela e os novos fluxos. `design.py` centraliza temas, ícones próprios e gráficos nativos interativos. `ledger.py` implementa categorias, cartões, parcelas, pagamentos, agenda, comprovantes e conciliação CSV/OFX.

Parcelas são divididas em centavos com distribuição exata do resto. A competência da primeira fatura pode ser ajustada. Dívida de cartão é descontada do patrimônio consolidado. Extratos usam chave estável por conta e identificador da origem; correspondências com lançamentos manuais exigem conciliação explícita.

A versão do esquema é 2. Antes da primeira migração de banco 0.1, uma cópia é criada em backups. A restauração migra uma cópia candidata antes de substituir o banco em uso. O mesmo AppId do instalador permite atualizar sobre a 0.1. Dados ficam fora da pasta do programa. Um lock por banco impede duas instâncias simultâneas.


## Elisei 0.3

`investments.py` adiciona investment_events e investment_values no esquema 3. A posição mantém o último estado conhecido para compatibilidade com metas e relatórios atuais; a tela da carteira usa saldos até o mês escolhido. `diagnostics.py` verifica coerência sem exportar dados financeiros. `widgets.py` reúne calendário, seletor de mês, quebra de ações e grade adaptável. `photos.py` faz recorte e prévia circular. O documento ELISEI-0.3.md especifica regras e limites.
  
