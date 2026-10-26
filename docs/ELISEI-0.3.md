# Elisei Finanças 0.3.0

## Identidade e direção de produto

Elisei é um nome criado a partir de Eliseu, ligado à evolução profissional em tecnologia e a metas de longo prazo. O símbolo é um E contínuo com ponto de chegada; o sistema visual usa superfícies claras, hierarquia tipográfica, azul como realce funcional, ícones próprios e navegação lateral. O SVG é editável em assets/elisei.svg. Não há vínculo com Apple ou uso de SF Symbols/fontes proprietárias. Não houve pesquisa jurídica de marca.

Referências modernas consultadas em outubro de 2026:
- Copilot Money para macOS: https://help.copilot.money/en/articles/6778561-copilot-money-for-macos
- Copilot: fluxo com navegação dos gráficos ao detalhe: https://help.copilot.money/en/articles/9682232-cash-flow-tab-overview
- Actual Budget desktop: https://actualbudget.org/download/
- Actual: relatórios: https://actualbudget.org/docs/reports/
- Budget Flow para macOS: https://apps.apple.com/us/app/budget-flow-expense-tracker/id1640091876?platform=mac
- Apple HIG: https://developer.apple.com/design/human-interface-guidelines/sidebars e https://developer.apple.com/design/human-interface-guidelines/charts

Essas fontes demonstram disponibilidade e funções atuais; não estabelecem ranking de popularidade. Conexões bancárias e recursos pagos dos produtos não foram copiados nem simulados.

## Carteira mês a mês

1. Cadastre o investimento com moeda, indexador e último saldo conhecido.
2. Escolha o mês no topo. Use Atualizar saldo para registrar uma conferência do extrato naquela data. Isso não cria receita nem aporte.
3. Use Registrar aporte / resgate para o movimento realizado. Pode criar lançamento em conta ou vincular um lançamento confirmado existente do mesmo mês, tipo e valor.
4. Ao vincular movimento que já está refletido no saldo conferido da mesma data, escolha Sim, já incluído no extrato. Isso evita somá-lo novamente ao saldo.
5. Consulte Histórico mensal para distinguir saldo anterior, aportes, resgates, saldo registrado e variação. Um saldo mensal só tem variação apurada se há base anterior e conferência no mês. A variação pode incluir câmbio, não equivale a taxa de retorno auditada.
6. A estimativa parte do último saldo e aplica a taxa aos intervalos entre movimentos. É um cenário bruto, sem novos aportes desconhecidos, com câmbio constante e convenções aproximadas já documentadas. Não é saldo consultado no banco.

A migração não inventa valores para janeiro ou qualquer mês anterior ao primeiro saldo conhecido. Meses sem base mostram Sem saldo registrado. Meses carregados exibem a última data de conferência. Histórico importado sem associação permanece disponível para conferência manual. A cobertura da curva pode variar conforme ativos ganham registros; ela não representa rentabilidade de uma carteira com composição constante.

Saldo conferido engloba movimentos até sua data. Aportes posteriores na mesma data são identificados por checkpoint; vinculação explícita de lançamento já incluído não elimina outros novos aportes. Desfazer o último movimento remove o lançamento somente se ele foi criado pela carteira; lançamento apenas vinculado é preservado. Após resgate, o custo pode exigir conferência manual em vez de inferir tributação ou custo de aquisição.

## Segurança e diagnóstico

Antes da migração para esquema 3, o banco existente recebe cópia antes-atualizacao-0.3-*.sqlite. O diagnóstico verifica integridade SQLite, chaves de relacionamento, datas, valores, consumo por mês, vínculo da carteira com caixa e saldo conhecido negativo. Seu JSON contém resultados e contagens, sem nomes, descrições financeiras, valores ou fotos. Não confirma saldo em banco ou a segurança do Windows.

Ocultar valores (Ctrl+Shift+P) mascara valores formatados e gráficos nas telas de consulta. Não anonimiza nomes/fotos, campos de edição ou exportações CSV. Não promete ocultação segura para compartilhar toda captura de tela.

Dados e backups SQLite continuam locais e não criptografados. Não há Open Finance, sincronização em nuvem, pagamento real ou senha/PIN que prometa proteger um arquivo sem criptografia. Backup e consentimento explícito na restauração continuam disponíveis.

## Atualização e compatibilidade

Faça backup no aplicativo, feche o programa e execute Elisei-Instalar-0.3.0-Windows-x64.exe. O mesmo AppId e diretório de instalação permitem substituir o Horizonte. A pasta de dados permanece %LOCALAPPDATA%/Horizonte para preservar os dados e backups existentes. O executável e os atalhos passam a se chamar Elisei.

A versão anterior não abre um banco migrado para esquema 3. Guarde a cópia anterior caso seja necessário retornar. A atualização usa instalador completo. O executável não possui assinatura digital de editor.

## Diagnósticos automatizados

A suíte cobre cálculos financeiros, parcelas, conciliação, importação, migração/restauração, fotos, datas, orçamentos, PDF, simulações, aporte/valor mensal e vínculo de caixa. Um teste percorre botões das 14 telas, verifica conexão de evento e executa cliques com diálogos de edição cancelados, arquivos isolados e rede simulada. Fluxos adicionais gravam formulários reais.

A contagem de botões é emitida como DIAGNOSTIC_BUTTON_ROUTES no teste. Essa verificação não substitui homologação de todos os controles nativos de arquivo, monitores e escalas de DPI. A suíte não usa contas ou valores pessoais.
  
