# Estudo de caso demonstrativo

## Problema

Uma pessoa acompanha gastos e investimentos, mas precisa entender se a capacidade mensal de poupar é suficiente para um objetivo futuro. O problema não é apenas exibir totais: é distinguir consumo, aporte, estoque de patrimônio e disponibilidade no prazo.

## Solução implementada

Um aplicativo desktop local reúne lançamentos, orçamento por categoria, carteira e metas. Gráficos mostram distribuição e evolução. As análises explicam limites ultrapassados e a distância entre aporte necessário e sobra registrada. Cada projeção mostra as hipóteses que a produzem.

## Decisões

Python aproveita conhecimento de programação aplicável a automações e cálculos. PySide6 oferece janelas desktop sem servidor local. SQLite mantém persistência sem infraestrutura. Dinheiro em centavos reduz erros de arredondamento na persistência. Regras determinísticas permitem conferir o motivo dos avisos e evitam custo de API de IA.

## Demonstração

A carteira de exemplo, instituições genéricas, receitas e despesas foram geradas para demonstrar a interface. Nenhum registro corresponde a um cliente ou usuário real. Não há clientes, depoimentos, métricas de economia ou resultados comerciais atribuídos ao projeto.

## Aprendizados e limitações

Importar uma fonte financeira exige interpretar corretamente estoque e fluxo. Um saldo antigo não é renda do mês, e aporte não é consumo. Liquidez e vencimento podem tornar uma projeção de patrimônio insuficiente para financiar uma meta na data pretendida. O simulador exige dados e hipóteses revisados; não substitui extrato, assessoria financeira ou confirmação de exigências migratórias.
