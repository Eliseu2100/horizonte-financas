# Correções 0.2.1

Atualização sobre a 0.2.0, mantendo AppId e esquema de dados 2. Faça backup em Dados e backup, feche o aplicativo e execute o novo instalador na mesma pasta. Não precisa desinstalar.

## Problemas corrigidos

- Datas: campos compartilhados com digitação dd/MM/yyyy, calendário pt-BR e botão explícito. Vencimento opcional no investimento com opção de não informar. Competências e meses das simulações exibidos MM/yyyy, armazenados yyyy-MM. Datas e vencimento do lançamento sincronizam até que o usuário escolha datas distintas.
- Lançamento: vencimento editável em todas as situações; destino aparece somente para Transferência. Cadastro de conta disponível dentro do formulário. Filtros preservados ao salvar. A competência pode ser independente, de forma explícita.
- Agenda: incluir/editar compromissos, exibir valores ainda não preenchidos e tratar resgates como entradas. Confirmar exige valor preenchido. Confirmados saem da agenda.
- Orçamento: editar linha selecionada com valor existente, duplo clique para edição, remoção explícita e informação quando não há mês anterior para copiar. Limites principais somam subcategorias.
- Desenho: removido efeito de opacidade em páginas com tabelas, que podia interferir na pintura no Windows. Altura mínima de cabeçalhos/linhas e largura mínima de colunas; rolagem horizontal e métricas distribuídas em grade.
- Gráficos: fatias do anel respondem ao cursor/clique, além da legenda. Gastos abrem detalhamento com compras de cartão e despesas em conta. Série com ponto único é visível.
- Análises: média ignora meses somente previstos e inclui meses com consumo apenas em cartão. Projeção futura considera registros já confirmados no mês, além dos previstos.
- Relatórios: patrimônio líquido desconta cartões. PDF inclui indicadores e títulos das seções, dados por categoria e faturas.
- Simulações: seletores de mês, campos em duas colunas, erros no local e resultados antigos removidos quando as premissas são inválidas.
- Perfil: recorte com zoom/deslocamento, arraste e prévia circular. Reenquadramento usa a foto original reduzida guardada localmente. Escolher/remover foto não apaga nome, idade ou profissão ainda digitados. Foto e original acompanham backup.
- Diagnóstico: falhas inesperadas da interface deixam de ser silenciosas; são registradas em interface-error.txt na pasta dos dados. Temporizadores encerram com a janela.

## Verificação

Os testes de regressão exercitam cliques de calendário, gravação do vencimento no banco, orçamento selecionado, campos e conta do lançamento, agenda sem valor, clique de fatia, exportação PDF, recorte circular e erro/recuperação da simulação. Testes existentes de cálculos, cartões, backup, migração, temas e telas são mantidos. Nenhuma revisão usa ou publica dados reais no GitHub.

A verificação automatizada não equivale a homologação em todo monitor ou escala de DPI. O instalador continua sem assinatura digital de editor. Não há Open Finance nem envio de pagamentos reais.

Os 26 testes passaram localmente. As barras de ações agora quebram em linhas e as métricas se reorganizam ao reduzir a janela. Seletores de lista têm seta visível.
  
