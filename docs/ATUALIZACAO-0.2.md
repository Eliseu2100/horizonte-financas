# Atualizar para 0.2.0

1. Feche o Horizonte e faça uma cópia manual em Dados e backup.
2. Execute Horizonte-Instalar-0.2.0-Windows-x64.exe no mesmo usuário do Windows.
3. Mantenha a pasta da instalação anterior. O AppId foi preservado, permitindo atualizar por cima.
4. Abra o aplicativo. Antes da migração do banco 0.1, é criada uma cópia `antes-atualizacao-0.2-*.sqlite` na pasta de backups junto aos dados.
5. Confira perfil, contas, investimentos e lançamentos. O banco permanece em `%LOCALAPPDATA%/Horizonte/financas.sqlite`.

Não é necessário desinstalar a versão anterior. O pacote completo não substitui um banco existente e não inclui dados pessoais de exemplo reais. Ele também serve para uma instalação nova; nesse caso o usuário começa vazio ou restaura seu backup.

## Patch ou instalador completo?

Esta entrega usa um instalador completo de atualização. Não há patch diferencial ou atualizador em segundo plano. Um patch menor exigiria validar a versão de origem, os hashes de cada arquivo e um procedimento de retorno; o instalador completo é mais simples de verificar nesta fase.

Os backups da 0.1 podem ser restaurados pela 0.2, que migra uma cópia sem modificar o arquivo escolhido. A migração inversa para a 0.1 não é suportada. Guarde o backup anterior para eventual recuperação.

## Novas funções

Cartões manuais, compras parceladas, limite comprometido, pagamento parcial e integral de faturas; agenda de compromissos; categorias e subcategorias; cópia mensal de limites; etiquetas; comprovantes em PDF/PNG/JPEG; importação CSV/OFX para contas em reais com prévia e conciliação; temas e atalhos.

Consumo no cartão é contado por mês de fatura. O pagamento reduz caixa e dívida, sem registrar a despesa uma segunda vez. Confirme a primeira competência com a fatura do banco: a regra padrão coloca compras no dia de fechamento no ciclo seguinte. O cadastro não envia pagamentos ao banco.

Open Finance, OCR/IA de recibos, sincronização com celular e conexões com agentes externos não foram implementados. Esses serviços exigem infraestrutura, consentimento e orçamento próprios; não existem botões que simulem uma integração ativa.
  
