## Agente de Validação de Código
**Arquivos analisados:** 1 · **Status:** ⚠️ 3 violação(ões)

| Arquivo | Linha | Regra | Símbolo | Detalhe |
|---|---|---|---|---|
| antes_pedido.py | 1 | nomenclatura | `processarPedido` | função fora de snake_case |
| antes_pedido.py | 1 | parametros | `processarPedido` | 6 parâmetros (> 5) |
| antes_pedido.py | 1 | complexidade | `processarPedido` | CC=12 (> 10) |

### Recomendações de refatoração
- Sugestão: nomenclatura em `processarPedido` — use snake_case para funções/variáveis e PascalCase para classes, com nomes descritivos
- Sugestão: parametros em `processarPedido` — agrupe parâmetros relacionados em um objeto (Parameter Object)
- Sugestão: complexidade em `processarPedido` — extraia condições para funções auxiliares ou use tabelas de decisão
