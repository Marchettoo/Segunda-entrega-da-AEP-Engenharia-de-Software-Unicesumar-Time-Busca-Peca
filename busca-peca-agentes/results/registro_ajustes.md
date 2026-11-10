# Registro de ajustes identificados durante os testes (Entrega 2)
- DOC: primeira execução sobre o projeto-alvo elevou a cobertura de docstrings de 15,6% para 86,7% (não 100%):
  o gerador inseria docstrings só em classes/funções, não em módulos. Ajuste: o filtro de renderização passou a
  receber o Model sintetizado e a inserir docstring de módulo com a responsabilidade (docstring/entrevista/inferida).
- VAL: execução sobre o projeto-alvo reportou 6 violações, todas falsos positivos: `setUp` (hook obrigatório do
  unittest) e variável `p` de list comprehension. Ajuste: o NomenclaturaHandler passou a ignorar hooks de framework
  e alvos de compreensão. Métricas medidas nas duas versões (inicial x ajustada) sobre o corpus rotulado.
- VAL (antes/depois): a verificação automática de equivalência comportamental (3 pedidos de exemplo) detectou que a
  primeira refatoração manual de `processarPedido` alterava o retorno quando `observacao` era None (devolvia "").
  Corrigido antes da medição final. Lição: refatoração sugerida pelo agente precisa de teste de regressão.
