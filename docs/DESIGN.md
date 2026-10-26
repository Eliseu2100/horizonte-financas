# Horizonte 0.2 — direção visual e referências

O produto continua sendo um aplicativo Windows nativo em PySide6. A referência Apple orienta hierarquia, consistência e comportamento; a interface mantém os controles de janela e a fonte disponíveis no Windows. Não usa fontes San Francisco, SF Symbols, logotipos Apple ou código privado do Organizze.

## Decisões implementadas

- Navegação lateral agrupada em dois níveis, rolável e ocultável.
- Superfícies neutras, realce azul funcional e números com hierarquia consistente.
- Temas claro/escuro com paleta aplicada aos controles nativos e gráficos.
- Calendários e campos numéricos para datas, parcelas e fechamento.
- Atalhos Ctrl+N, Ctrl+K, Ctrl+I, Ctrl+Shift+B e Ctrl+Q, expostos em menus.
- Animação breve de transição, desativável em Exibir > Reduzir movimento.
- Gráficos com valores ao passar o cursor, descrição acessível e tabelas nos relatórios.
- Mensagens de vazio, erros de validação e confirmações para alterações que removem registros.

Não é uma reprodução de Liquid Glass: o aplicativo usa superfícies discretas e controles Qt para manter legibilidade e compatibilidade no Windows.

## Fontes primárias consultadas

- [Apple: Designing for macOS](https://developer.apple.com/design/human-interface-guidelines/designing-for-macos/)
- [Apple: Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars)
- [Apple: Layout](https://developer.apple.com/design/human-interface-guidelines/layout)
- [Organizze: recursos](https://www.organizze.com.br/recursos)
- [Organizze: cadastro de cartão](https://ajuda.organizze.com.br/hc/pt-br/articles/6159569013907-Web-Cart%C3%A3o-de-cr%C3%A9dito-Adicionar-cart%C3%A3o)
- [Organizze: conciliação e retomada do uso](https://ajuda.organizze.com.br/hc/pt-br/articles/15705344876435-Como-retomar-o-uso-no-Organizze)

A skill UI/UX Pro Max foi usada para revisar contraste, foco, feedback e consistência. Suas sugestões genéricas de landing page não foram aplicadas ao desktop; as diretrizes Apple e o contexto real do aplicativo orientaram a seleção.
  
