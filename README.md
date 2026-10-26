# Horizonte Finanças

Aplicativo desktop para Windows de controle de gastos, investimentos e planejamento por metas. Construído com Python, PySide6 e SQLite. A interface usa janelas nativas de desktop e funciona sem navegador ou servidor local.

**Projeto demonstrativo de portfólio, em desenvolvimento. Todos os dados da demonstração são fictícios.** O repositório não contém extratos, planilhas, bancos de dados ou saldos pessoais.

![Dashboard com dados fictícios](https://github.com/user-attachments/assets/378ce541-7f67-4126-b833-dc2816dc8b93)

## O problema

Registros de gastos, posições de investimento e objetivos futuros ficam difíceis de comparar quando tratados separadamente. O Horizonte organiza essas informações e explica quando o aporte necessário para uma meta supera a sobra mensal registrada.

## Funcionalidades implementadas

- Receitas, despesas, aportes, resgates e transferências, com edição, pesquisa e filtros.
- Competência mensal independente da data, categorias e situações confirmado, previsto e a revisar.
- Recorrências mensais: meses futuros criados como previstos, sem inflar o realizado.
- Limites por categoria e alertas de estouro do orçamento.
- Dashboard com evolução de receitas/despesas e distribuição de gastos.
- Análises de déficit, capacidade de aporte, concentração de gastos e cobertura da reserva.
- Carteira com CDB, LCI, LCA, Bitcoin e outros ativos, filtros e projeção individual.
- Indexadores prefixado, percentual do CDI e IPCA + spread, com vencimento e liquidez.
- Metas com ativos vinculados, capital disponível no prazo, aporte necessário e gráfico futuro.
- Simulador com aportes em duas fases, bônus, retorno mensal e retirada extraordinária.
- Projeção de fluxo de caixa dos próximos 12 meses e memória mensal dos cenários.
- Contas bancárias com saldo conferido e movimentos confirmados posteriores, incluindo transferências.
- Patrimônio por renda fixa, variável, cripto, moedas e saldo em conta.
- Posições e contas em BRL, USD, EUR e JPY com conversão manual para consolidar valores.
- Perfil com nome, idade, profissão e foto armazenada junto aos dados.
- Relatórios por classe, instituição, moeda, fluxo mensal e vencimentos, com exportação PDF.
- Backup automático diário, atualizado ao abrir, durante o uso e ao encerrar.
- Câmbio BRL/JPY diário por consulta explícita, cache e hipótese manual.
- Backup/restauração SQLite, exportação CSV e importador opcional de um layout mensal de Excel.

## Executar

Windows 10 (1903 ou posterior)/11 de 64 bits e Python 3.12 ou posterior:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python src\app.py --demo
```

A demonstração usa `%LOCALAPPDATA%\HorizonteDemo`. Para iniciar sem dados de exemplo, execute sem `--demo`: o banco fica em `%LOCALAPPDATA%\Horizonte`. A variável `HORIZONTE_DATA_DIR` permite usar outra pasta. O modo demonstração deve usar um banco próprio vazio.

## Gerar executável

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\scripts\build.ps1
```

Abra `dist\Horizonte\Horizonte.exe`. A pasta inteira é necessária na versão portátil. Com o compilador oficial Inno Setup disponível, `ISCC scripts\installer.iss` gera o instalador em `release\`. Nenhum dado pessoal é incluído no build público. O script usa a .venv e reconstitui o ícone a partir de scripts/prepare_assets.py.

## Testes

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
```

A documentação de [validação](docs/VALIDACAO.md) separa os testes automatizados das verificações de interface e do instalador.

## Decisões e limites

As análises são regras locais explicáveis, sem chamadas a modelos de IA. Valores monetários são armazenados em centavos. Aportes não são despesas de consumo; saldos de abertura não são receitas. A carteira é atualizada por posições informadas, sem inferir saldo ou rendimento a partir do fluxo de caixa.

As projeções são estimativas nominais. CDI e inflação futuros são hipóteses editáveis; imposto é um percentual manual sobre ganho. Não há cálculo automático de IOF, tabela tributária regressiva, feriados bancários ou recomendação de compra/venda. Cripto sem hipótese de taxa fica com valor constante. Uma meta não coberta produz diagnóstico de insuficiência, não uma previsão de impossibilidade absoluta.

Não há integração bancária/Open Finance, sincronização em nuvem, autenticação ou criptografia do arquivo local nesta versão. Esses recursos não são anunciados como implementados.

## Planejamento e estudo de caso

- [Requisitos e escopo](docs/REQUISITOS.md)
- [Arquitetura e modelo financeiro](docs/ARQUITETURA.md)
- [Critérios de aceitação e validação](docs/VALIDACAO.md)
- [Evolução planejada](docs/ROADMAP.md)
- [Estudo de caso para portfólio](docs/ESTUDO-DE-CASO.md)

Referências de produto: organização por categorias e planejamento do [Mobills](https://www.mobills.com.br/blog/mobills/como-utilizar-o-mobills/). Câmbio: [Frankfurter](https://frankfurter.dev/). Identidade e interface próprias, sem vínculo com esses serviços. O template Financial Budget foi consultado como referência de separação entre realizado, premissas e projeções; o produto entregue é um aplicativo desktop.

Licenças de terceiros: [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt). Código disponibilizado para demonstração e estudo; licença própria de distribuição comercial ainda não definida pelo autor.
