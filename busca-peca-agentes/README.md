# Busca Peça — Ecossistema de Agentes (AEP · Entrega 2)

Protótipos funcionais dos 5 agentes especificados na Entrega 1, projeto-alvo, experimento controlado e resultados.
ODS 12 — Consumo e Produção Responsáveis.

## Estrutura
- `agents/documentacao/` — Agente de Documentação (pipe-and-filter, Builder, Chain of Responsibility, SKILL.md)
- `agents/validacao/` — Agente de Validação de Código / Clean Code (Chain of Responsibility, Decorator, Builder)
- `agents/arquiteto/` — Agente Arquiteto (microsserviço HTTP orientado a eventos; Factory Method, Facade, Strategy)
- `agents/code_review/` — Agente de Code Review / ContextReview (Template Method, somente leitura)
- `agents/qualitybridge/` — Agente de Testes QualityBridge (CLI; Factory Method, Adapter, Strategy, SQLite)
- `agents/common/` — Adapter de LLM (provedor determinístico ou API compatível com OpenAI) e medição
- `sample_project/` — backend mínimo do Busca Peça usado como alvo (21 testes)
- `experiments/` — fixtures rotuladas, `run_all.py` (46 casos) e `graficos.py`
- `results/` — dados brutos (`casos.csv`, `amostras_tempo.csv`), `metricas.json`, `graficos/`, `evidencias/`, `registro_ajustes.md`

## Reproduzir (Python 3.10+, PyYAML, Jinja2; pandas e matplotlib para os gráficos)
```
python -m experiments.run_all
python -m experiments.graficos
```

## Usar os agentes
```
python -m agents.documentacao.pipeline sample_project saida_docs --respostas experiments/fixtures/respostas_entrevista.json
python -m agents.validacao.agente sample_project
python -m agents.arquiteto.servidor 8081          # POST http://127.0.0.1:8081/webhook
python -m agents.code_review.agente experiments/fixtures/code_review/projeto
cd sample_project && python -m agents.qualitybridge.agente run --config qualitybridge.yaml
```
Para usar um LLM real nos agentes híbridos: defina `AEP_LLM_URL`, `AEP_LLM_KEY` e `AEP_LLM_MODEL`.
