# Validação

## Testes automatizados

Conversão para centavos e rejeição de valores inválidos; juros sem taxa e taxa efetiva; fluxo consolidado com previsto e transferência; backup; idempotência e interpretação de um arquivo sintético; prefixado com imposto manual; vencimento e liquidez; CDI e IPCA; dados fictícios sem arquivo pessoal.

## Verificações executadas localmente

- Reconciliação privada das saídas de dez abas mensais com seus respectivos totais da fonte, sem publicar a fonte ou os resultados pessoais.
- Cadastro, edição, busca e recorrência por meio dos formulários reais da interface.
- Renderização das onze telas em 1440×960 e 1080×740.
- Build PyInstaller de 64 bits com bibliotecas incluídas.
- Teste de inicialização do executável e renderização das telas.

Instalador compilado com Inno Setup e testado em pasta isolada: instalação retornou código 0, o executável instalado renderizou as telas, e a desinstalação retornou código 0 preservando o banco de uso. O teste não registrou atalhos nem entrada global de desinstalação. Não há afirmação de compatibilidade testada em toda edição do Windows ou de auditoria completa de acessibilidade.

## Aceitação

O usuário consegue lançar gastos sem planilha, visualizar seus efeitos, definir limites, cadastrar taxas e vencimentos, vincular investimentos a metas, simular o futuro e guardar backup. As informações ausentes e premissas precisam continuar visíveis. Nenhum dado financeiro pessoal deve entrar no GitHub público.

Testes adicionais locais: cadastro real de conta, movimentos de saldo, posição em USD, perfil, PDF e restauração/portabilidade de banco com perfil e contas.

No empacotamento, foi corrigida uma seleção incompatível de ICU: o build utiliza a ICU nativa do Windows 10 1903 ou posterior. O launcher registra falhas de inicialização em arquivo.


## Validação da versão 0.2.0

17 testes automatizados passaram: sete do domínio original, sete de cartões/conciliação/migração e três de interface. A interface foi renderizada nas 14 telas, em temas claro/escuro e tamanhos 1440×950 e 1000×680. Os formulários reais foram exercitados para recorrência e validação, além da paleta de ações e navegação.

O executável PyInstaller abriu e renderizou todas as telas. O instalador 0.1 foi executado em pasta isolada; o instalador 0.2 foi aplicado sobre essa mesma instalação. Todos os registros originais das tabelas financeiras e um marcador de configuração foram preservados. O banco migrou para esquema 2, com backup anterior criado. O executável atualizado renderizou as 14 telas. A desinstalação de teste preservou o banco. O pacote público não contém seed.sqlite pessoal.

A validação não equivale a homologação em todas as versões do Windows. O aplicativo não tem assinatura digital de editor. O build público em Actions repete testes, smoke test do executável e compilação do instalador.
  
