---
name: agente-documentacao
description: Gera e atualiza a documentação técnica e didática do Busca Peça (README, docstrings, ADRs, relatório de lacunas).
---
# Agente de Documentação de Software (Controller GRASP + Facade GoF)
1. Execute `python -m agents.documentacao.pipeline <raiz> <saida> [--respostas respostas.json]`.
2. Filtro 1 (Coleta) roda `scan_repo.py`; Filtro 2 (Entrevista) faz no máximo 5 perguntas.
3. PORTÃO 1: mostre o esqueleto ao desenvolvedor e só continue com aprovação.
4. Filtros 3-4 (Síntese e Renderização) usam `templates.md` e o provedor LLM do host.
5. Filtro 5 (Validação) roda `validate_doc.py` (formato, completude, ABNT conforme `abnt.md`).
6. PORTÃO 2: sem lacunas bloqueantes -> gravar `README_tecnico.md`, `GUIA_didatico.md`, `LACUNAS.md`.
