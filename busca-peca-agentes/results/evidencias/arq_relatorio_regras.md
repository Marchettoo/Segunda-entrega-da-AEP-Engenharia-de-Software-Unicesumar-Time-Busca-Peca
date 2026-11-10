## Relatório de Conformidade Arquitetural — PR #7
**Estratégia:** regras · **Status:** reprovado · **Achados:** 1
- **[BLOQUEANTE] R1-dependencia-entre-camadas** — `buscapeca/controllers/peca_controller.py:1`: camada 'apresentacao' não pode depender de 'persistencia' (buscapeca.repositories.peca_repository)
