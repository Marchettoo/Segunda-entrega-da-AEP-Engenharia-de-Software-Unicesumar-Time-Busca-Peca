# Relatório de Code Review (ContextReview)
Arquivos no escopo: 4 · Achados: 13 · Refutados: 2

## Extra High (2)
- **SEC-SQL-INJECTION** (Segurança, confiança 0.95) — `app/busca_repo.py:7`
  - Evidência: `return conexao.execute(f"SELECT * FROM pecas WHERE nome = '{nome}'").fetchall()`
  - Por que isso importa: concatenar dados em SQL permite que um atacante altere a consulta (injeção de SQL).
- **SEC-SQL-INJECTION** (Segurança, confiança 0.90) — `app/busca_repo.py:11`
  - Evidência: `return conexao.execute("SELECT * FROM pecas WHERE oficina_id = " + str(oficina_id)).fetchall()`
  - Por que isso importa: concatenar dados em SQL permite que um atacante altere a consulta (injeção de SQL).

## High (4)
- **SEC-SHELL** (Segurança, confiança 0.90) — `app/config.py:14`
  - Evidência: `subprocess.run(f"tar -czf {destino} dados/", shell=True)`
  - Por que isso importa: shell=True permite injeção de comandos no sistema operacional.
- **SEC-EVAL** (Segurança, confiança 0.90) — `app/pedidos.py:25`
  - Evidência: `return eval(expressao, {}, contexto)`
  - Por que isso importa: eval/exec executa código arbitrário vindo de dados.
- **SEC-SEGREDO-HARDCODED** (Segurança, confiança 0.85) — `app/config.py:4`
  - Evidência: `DB_PASSWORD = "buscapeca@2026"`
  - Por que isso importa: credenciais no código vazam pelo controle de versão.
- **SEC-SEGREDO-HARDCODED** (Segurança, confiança 0.85) — `app/config.py:5`
  - Evidência: `API_KEY_FRETE = "sk-live-9f8e7d6c"`
  - Por que isso importa: credenciais no código vazam pelo controle de versão.

## Medium (4)
- **COR-DEFAULT-MUTAVEL** (Correção, confiança 0.90) — `app/pedidos.py:6`
  - Evidência: `def adicionar_item(item, carrinho=[]):`
  - Por que isso importa: o valor padrão mutável é compartilhado entre chamadas e causa efeitos colaterais.
- **COR-EXCEPT-SILENCIOSO** (Correção, confiança 0.85) — `app/pedidos.py:14`
  - Evidência: `except:`
  - Por que isso importa: engolir exceções esconde falhas e dificulta o diagnóstico.
- **COR-EXCEPT-SILENCIOSO** (Correção, confiança 0.85) — `app/pedidos.py:31`
  - Evidência: `except KeyError:`
  - Por que isso importa: engolir exceções esconde falhas e dificulta o diagnóstico.
- **SEC-HASH-FRACO** (Segurança, confiança 0.80) — `app/config.py:10`
  - Evidência: `return hashlib.md5(open(caminho, "rb").read()).hexdigest()`
  - Por que isso importa: MD5/SHA1 são inadequados para senhas e integridade.

## Low (1)
- **COR-COMPARACAO-NONE** (Correção, confiança 0.90) — `app/pedidos.py:19`
  - Evidência: `if pedido.get("pago") == None:`
  - Por que isso importa: compare com None usando 'is', pois '==' pode ser sobrescrito.

## Advice (2)
- **QUA-PRINT** (Qualidade, confiança 0.60) — `app/pedidos.py:33`
  - Evidência: `print("notificado", pedido)`
  - Por que isso importa: use logging estruturado em vez de print em código de produção.
- **SEC-SEGREDO-HARDCODED** (Segurança, confiança 0.42) — `tests/test_config.py:3`
  - Evidência: `SENHA_TESTE = "senha-de-teste-123"`
  - Por que isso importa: credenciais no código vazam pelo controle de versão.
  - Refutação: parcial: ocorre em código de teste, risco reduzido

## Hipóteses refutadas
- SEC-SQL-INJECTION em `app/busca_repo.py:15` — interpolação usa apenas constantes do módulo (sem dado externo)
- COR-DEFAULT-MUTAVEL em `app/pedidos.py:36` — supressão explícita '# nosec' revisada pelo autor
