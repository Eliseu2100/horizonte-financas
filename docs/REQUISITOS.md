# Requisitos e escopo

## Público e objetivo

Pessoas que desejam registrar gastos e planejar objetivos com clareza sobre aportes, prazos e recursos disponíveis. O aplicativo é instalado no Windows e guarda dados localmente. A demonstração de portfólio usa somente dados sintéticos.

## Jornadas principais

1. Registrar uma receita ou despesa e visualizar o impacto no mês.
2. Criar gastos recorrentes como previstos e confirmar sua realização.
3. Definir um orçamento por categoria e identificar excessos.
4. Cadastrar um ativo com instituição, tipo, custo conhecido, saldo, data de registro, taxa, vencimento e liquidez.
5. Projetar esse ativo com parâmetros de CDI, inflação e imposto explicitamente informados.
6. Criar uma meta, vincular ativos e verificar insuficiência, aporte necessário e disponibilidade no prazo.
7. Explorar cenários com aportes, bônus, retorno e retiradas.
8. Proteger os dados com backup e recuperar uma cópia válida.

## Regras de negócio

- Centavos inteiros no banco. Zero e valor ausente têm significados distintos.
- Confirmado e a revisar com valor entram no fluxo. Previsto não entra no realizado.
- Transferência é neutra no fluxo consolidado. Aporte/resgate afetam caixa, mas não atualizam automaticamente a posição de investimento.
- Importação preserva competência da aba e data original; data de saída não estruturada permanece ausente.
- Categorias inferidas são sugestões, nunca evidência de pagamento ou natureza definitiva.
- Um ativo não pode ser vinculado pela interface a duas metas.
- A vinculação de ativos substitui o valor reservado manual da meta; não o soma novamente.
- Ativos sem liquidez confirmada na data da meta ficam fora do total disponível, mas são mostrados como pendentes.
- Ativo vencido antes da meta permanece constante após vencimento, sem reinvestimento presumido.
- A taxa de novos aportes da meta é uma hipótese independente das taxas de cada ativo.
- O aplicativo não define exigência migratória ou momento ideal para vender criptomoedas.

## Limites desta versão

Gerenciamento detalhado de cartões/faturas não está implementado. As contas têm saldo conferido e incorporam novos movimentos confirmados posteriores ao ponto de conferência. Dados importados a revisar não alteram automaticamente os saldos dessas contas. Faturas agregadas devem ser revistas antes de registrar compras contidas nelas. O importador é específico para um layout mensal e não é um importador universal de Excel.


## Perfil, moedas e backup

Perfil opcional com foto PNG redimensionada no próprio banco. Contas e posições aceitam BRL, USD, EUR e JPY. Taxa de conversão em reais por unidade, informada manualmente; câmbio futuro não previsto. Backup completo diário na pasta escolhida, atualizado a cada 30 minutos de uso e ao fechar. Sem execução em segundo plano quando o app está fechado. Para trocar de computador, instalar e restaurar o arquivo SQLite.
