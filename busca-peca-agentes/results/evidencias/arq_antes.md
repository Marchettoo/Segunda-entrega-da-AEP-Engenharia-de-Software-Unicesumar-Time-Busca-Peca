## Relatório de Conformidade Arquitetural — PR #15
**Estratégia:** regras · **Status:** reprovado · **Achados:** 3
- **[BLOQUEANTE] R1-dependencia-entre-camadas** — `buscapeca/controllers/peca_controller.py:1`: camada 'apresentacao' não pode depender de 'persistencia' (buscapeca.repositories.peca_repository)
- **[BLOQUEANTE] R2-sql-fora-da-persistencia** — `buscapeca/services/relatorio_service.py:2`: SQL embutido na camada 'negocio'
- **[BLOQUEANTE] R3-cripto-fora-da-seguranca** — `buscapeca/services/cadastro_service.py:1`: primitiva criptográfica 'hashlib' usada fora da camada de segurança
