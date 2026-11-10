"""Experimento controlado da Entrega 2 — executa todos os casos de teste dos 5 agentes.

Uso: python -m experiments.run_all
Saídas em results/: casos.csv, amostras_tempo.csv, metricas.json, evidencias/*.md
"""
import csv
import json
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from agents.arquiteto.agente import ArquitetoController, EstrategiaOrientacao, PayloadInvalido
from agents.arquiteto.servidor import criar_servidor
from agents.code_review.agente import PipelineRevisao
from agents.common.medicao import medir
from agents.documentacao.pipeline import PipelineDocumentacao
from agents.documentacao.scan_repo import cobertura_docstrings, elementos_publicos, varrer
from agents.documentacao.validate_doc import referencia_abnt_valida
from agents.qualitybridge import agente as qb
from agents.validacao.agente import ValidacaoController, complexidade_ciclomatica

BASE = Path(__file__).resolve().parents[1]
FX = BASE / "experiments" / "fixtures"
PROJETO = BASE / "sample_project"
RES = BASE / "results"
EVID = RES / "evidencias"
REPS = 30
REPS_QB = 10
TMP = Path(tempfile.mkdtemp(prefix="aep_"))

casos, amostras, metricas = [], [], {}


def registrar(agente, cid, tipo, cenario, esperado, obtido, passou, est):
    casos.append({"agente": agente, "caso": cid, "tipo": tipo, "cenario": cenario, "esperado": esperado,
                  "obtido": obtido, "passou": bool(passou), "n_rep": est["n"], "tempo_medio_ms": round(est["media_ms"], 3),
                  "tempo_dp_ms": round(est["dp_ms"], 3), "tempo_mediana_ms": round(est["mediana_ms"], 3),
                  "pico_memoria_kb": round(est["pico_memoria_kb"], 1)})
    amostras.extend({"agente": agente, "caso": cid, "tempo_ms": round(t, 4)} for t in est["amostras_ms"])
    print(f"  {cid:<7} {'PASSOU' if passou else 'FALHOU':<7} {est['media_ms']:9.2f} ms  {obtido[:90]}")


def prf(vp, fp, fn):
    precisao = vp / (vp + fp) if vp + fp else 1.0
    recall = vp / (vp + fn) if vp + fn else 1.0
    f1 = 2 * precisao * recall / (precisao + recall) if precisao + recall else 0.0
    return {"vp": vp, "fp": fp, "fn": fn, "precisao": precisao, "recall": recall, "f1": f1}


def salvar_evidencia(nome, texto):
    EVID.mkdir(parents=True, exist_ok=True)
    (EVID / nome).write_text(texto, encoding="utf-8")


# =====================================================================
# Agente 1 — Documentação
# =====================================================================
def agente_documentacao():
    print("\n[Agente 1] Documentação de Software")
    ag = "Documentação"
    respostas = json.loads((FX / "respostas_entrevista.json").read_text(encoding="utf-8"))

    def pipeline(raiz, saida, **kw):
        return PipelineDocumentacao(respostas=kw.pop("respostas", respostas), **kw).executar(raiz, saida)

    # Oráculo independente: contagem por expressão regular de elementos públicos
    esperado_elems = 0
    for p in (PROJETO / "buscapeca").rglob("*.py"):
        if p.name == "__init__.py":
            continue
        esperado_elems += 1 + len(re.findall(r"^\s*(?:def|class) (?!_)\w+", p.read_text(encoding="utf-8"), re.M))
    inv, est = medir(lambda: varrer(PROJETO), REPS)
    obtidos = len(list(elementos_publicos(inv)))
    registrar(ag, "DOC-01", "típico", "Coleta: inventário de módulos, classes e funções públicas do projeto",
              f"{esperado_elems} elementos (oráculo regex)", f"{obtidos} elementos inventariados", obtidos == esperado_elems, est)

    saida = TMP / "doc_out"
    r, est = medir(lambda: pipeline(PROJETO, saida), REPS)
    lac_estruturais = [l for l in r["lacunas"] if l["tipo"] in ("formato", "completude")]
    n_mod = len(r["modelo"]["modulos"])
    cobertos = sum(1 for m in r["modelo"]["modulos"] if m["caminho"] in r["docs"]["tecnico"] and m["caminho"] in r["docs"]["didatico"])
    registrar(ag, "DOC-02", "típico", "Pipeline completo: views técnica e didática do mesmo código",
              "2 views geradas, 100% dos módulos citados, 0 lacunas de formato/completude",
              f"2 views, {cobertos}/{n_mod} módulos citados, {len(lac_estruturais)} lacunas estruturais",
              cobertos == n_mod and not lac_estruturais, est)
    salvar_evidencia("doc_README_tecnico.md", (saida / "README_tecnico.md").read_text(encoding="utf-8"))
    salvar_evidencia("doc_GUIA_didatico.md", (saida / "GUIA_didatico.md").read_text(encoding="utf-8"))
    salvar_evidencia("doc_LACUNAS.md", (saida / "LACUNAS.md").read_text(encoding="utf-8"))

    antes, depois = r["cobertura_antes"], r["cobertura_depois"]
    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                          cwd=saida / "codigo_documentado", capture_output=True, text=True)
    testes_ok = proc.returncode == 0
    registrar(ag, "DOC-03", "típico", "Inserção de docstrings preservando o comportamento do código",
              "cobertura = 100% e 21/21 testes do projeto passando",
              f"cobertura {antes:.1f}% → {depois:.1f}%; testes {'OK' if testes_ok else 'FALHARAM'} ({r['docstrings_inseridas']} docstrings)",
              depois == 100.0 and testes_ok, est)
    src = (PROJETO / "buscapeca/services/pedido_service.py").read_text(encoding="utf-8").splitlines()
    dst = (saida / "codigo_documentado/buscapeca/services/pedido_service.py").read_text(encoding="utf-8").splitlines()
    salvar_evidencia("doc_antes_depois.txt", "ANTES\n" + "\n".join(src[:24]) + "\n\nDEPOIS\n" + "\n".join(dst[:30]))

    refs = json.loads((FX / "referencias_abnt.json").read_text(encoding="utf-8"))
    res, est = medir(lambda: [referencia_abnt_valida(x["ref"]) for x in refs], REPS)
    acertos = sum(1 for x, ok in zip(refs, res) if ok == x["valida"])
    vp = sum(1 for x, ok in zip(refs, res) if not ok and not x["valida"])  # positivo = referência fora do padrão
    fp = sum(1 for x, ok in zip(refs, res) if not ok and x["valida"])
    fn = sum(1 for x, ok in zip(refs, res) if ok and not x["valida"])
    acuracia_abnt = acertos / len(refs)
    registrar(ag, "DOC-04", "típico", f"Validador ABNT sobre {len(refs)} referências rotuladas (7 válidas, 7 inválidas)",
              "acurácia ≥ 90%", f"{acertos}/{len(refs)} classificadas corretamente ({acuracia_abnt:.0%})", acuracia_abnt >= 0.9, est)

    vazio = TMP / "repo_vazio"; vazio.mkdir(exist_ok=True)
    r5, est = medir(lambda: pipeline(vazio, TMP / "doc_vazio"), REPS)
    ok5 = r5["status"] == "gravado" and any("nenhum módulo" in l["detalhe"] for l in r5["lacunas"])
    registrar(ag, "DOC-05", "borda", "Repositório vazio (sem nenhum arquivo .py)",
              "pipeline conclui sem exceção e registra lacuna 'nenhum módulo'",
              f"status '{r5['status']}', {len(r5['lacunas'])} lacuna(s) registrada(s)", ok5, est)

    quebrado = TMP / "repo_quebrado"
    shutil.copytree(PROJETO, quebrado, dirs_exist_ok=True)
    (quebrado / "buscapeca/services/legado.py").write_text("def calcular(valor\n    return valor\n", encoding="utf-8")
    r6, est = medir(lambda: pipeline(quebrado, TMP / "doc_quebrado"), REPS)
    ok6 = any("legado.py" in l["detalhe"] for l in r6["lacunas"]) and len(r6["modelo"]["modulos"]) == n_mod
    registrar(ag, "DOC-06", "borda", "Arquivo com erro de sintaxe no meio do repositório",
              f"erro registrado em lacunas e {n_mod} módulos válidos documentados",
              f"lacuna de coleta registrada; {len(r6['modelo']['modulos'])} módulos documentados", ok6, est)

    muitos = TMP / "repo_sem_docs"; (muitos / "pkg").mkdir(parents=True, exist_ok=True)
    for i in range(8):
        (muitos / f"pkg/modulo_{i}.py").write_text(f"def funcao_{i}():\n    return {i}\n", encoding="utf-8")
    r7, est = medir(lambda: pipeline(muitos, TMP / "doc_muitos", respostas={}), REPS)
    registrar(ag, "DOC-07", "borda", "8 módulos sem docstring e sem README (9 perguntas possíveis)",
              "entrevista limitada a no máximo 5 perguntas", f"{len(r7['perguntas'])} perguntas feitas",
              len(r7["perguntas"]) <= 5, est)

    rejeita = TMP / "doc_rejeitado"
    r8, est = medir(lambda: PipelineDocumentacao(respostas, aprovar=lambda p, d: p != "portao1").executar(PROJETO, rejeita), REPS)
    registrar(ag, "DOC-08", "borda", "Portão humano 1 reprova o esqueleto",
              "pipeline interrompido sem gravar artefatos", f"status '{r8['status']}'; artefatos gravados: {rejeita.exists()}",
              r8["status"].startswith("interrompido") and not rejeita.exists(), est)

    metricas[ag] = {"cobertura_docstrings_antes": antes, "cobertura_docstrings_depois": depois,
                    "acuracia_abnt": acuracia_abnt, "abnt": prf(vp, fp, fn),
                    "modulos_documentados_pct": 100 * cobertos / n_mod, "docstrings_inseridas": r["docstrings_inseridas"],
                    "fontes_responsabilidade": {f: sum(1 for m in r["modelo"]["modulos"] if m["fonte"] == f)
                                                for f in ("docstring", "entrevista", "inferida")}}


# =====================================================================
# Agente 2 — Validação de Código (Boas Práticas / Clean Code)
# =====================================================================
def ler(pasta, *nomes):
    return {n: (pasta / n).read_text(encoding="utf-8") for n in nomes}


def agente_validacao():
    print("\n[Agente 2] Validação de Código (Boas Práticas / Clean Code)")
    ag = "Validação de Código"
    corpus = FX / "validacao" / "corpus"
    ctl = ValidacaoController()

    def chaves(r, regra=None):
        return {(v["arquivo"], v["regra"], v["simbolo"]) for v in r["violacoes"] if regra is None or v["regra"] == regra}

    r, est = medir(lambda: ctl.analisar_fontes(ler(corpus, "complexo.py")), REPS)
    ok = ("complexo.py", "complexidade", "classificar_frete") in chaves(r)
    cc = {f: complexidade_ciclomatica(n) for f, n in [(n.name, n) for n in __import__("ast").parse(
        (corpus / "complexo.py").read_text()).body]}
    registrar(ag, "VAL-01", "típico", "Função com complexidade ciclomática acima do limite (10)",
              "violação 'complexidade' em classificar_frete (CC=11)",
              f"CC medida={cc['classificar_frete']}; {len(chaves(r, 'complexidade'))} violação(ões) de complexidade", ok, est)
    registrar(ag, "VAL-02", "borda", "Função exatamente no limite (CC=10) e função com exatamente 30 linhas",
              "nenhuma violação (limite inclusivo)",
              f"classificar_peca CC={cc['classificar_peca']}: {'reportada' if ('complexo.py','complexidade','classificar_peca') in chaves(r) else 'não reportada'}; "
              f"montar_resumo: {'reportada' if any(v['simbolo']=='montar_resumo' for v in ctl.analisar_fontes(ler(corpus,'grande.py'))['violacoes']) else 'não reportada'}",
              ("complexo.py", "complexidade", "classificar_peca") not in chaves(r) and
              not any(v["simbolo"] == "montar_resumo" for v in ctl.analisar_fontes(ler(corpus, "grande.py"))["violacoes"]), est)

    r, est = medir(lambda: ctl.analisar_fontes(ler(corpus, "duplicado.py")), REPS)
    registrar(ag, "VAL-03", "típico", "Bloco de código duplicado com nomes de variáveis diferentes (DRY)",
              "1 violação 'duplicacao' em total_pedido_online", f"{len(chaves(r, 'duplicacao'))} duplicação(ões): "
              + ", ".join(s for *_, s in chaves(r, "duplicacao")),
              chaves(r, "duplicacao") == {("duplicado.py", "duplicacao", "total_pedido_online")}, est)

    r, est = medir(lambda: ctl.analisar_fontes(ler(corpus, "nomes.py")), REPS)
    esperado = {("nomes.py", "nomenclatura", s) for s in ("calcularTotal", "item_pedido", "x")}
    registrar(ag, "VAL-04", "típico", "Nomenclatura: camelCase, classe minúscula, variável 'x'; setUp e compreensão válidos",
              "3 violações, 0 falsos positivos", f"{len(chaves(r))} violações: " + ", ".join(sorted(s for *_, s in chaves(r))),
              chaves(r) == esperado, est)

    r, est = medir(lambda: ctl.analisar_fontes(ler(corpus, "grande.py")), REPS)
    esperado = {("grande.py", "tamanho", "gerar_relatorio_estoque"), ("grande.py", "parametros", "cadastrar_anuncio")}
    registrar(ag, "VAL-05", "típico", "Função com 34 linhas e função com 7 parâmetros",
              "violações 'tamanho' e 'parametros'", f"{len(chaves(r))} violações: " +
              ", ".join(sorted(f'{g}:{s}' for _, g, s in chaves(r))), chaves(r) == esperado, est)

    r, est = medir(lambda: ctl.analisar_fontes(ler(corpus, "limpo.py")), REPS)
    registrar(ag, "VAL-06", "típico", "Código limpo (controle de falso positivo)", "0 violações",
              f"{len(r['violacoes'])} violações", not r["violacoes"], est)

    r, est = medir(lambda: ctl.analisar_fontes(ler(corpus, "vazio.py")), REPS)
    registrar(ag, "VAL-07", "borda", "Arquivo vazio", "0 violações, sem erro",
              f"{len(r['violacoes'])} violações, {len(r['erros'])} erros", not r["violacoes"] and not r["erros"], est)

    r, est = medir(lambda: ctl.analisar_fontes(ler(corpus, "quebrado.py", "misto.py")), REPS)
    registrar(ag, "VAL-08", "borda", "Arquivo com sintaxe inválida junto de arquivo válido",
              "erro controlado no inválido e análise normal do válido",
              f"erros: {r['erros']}; {len(r['violacoes'])} violações no arquivo válido",
              len(r["erros"]) == 1 and len(r["violacoes"]) == 3, est)

    ctl_dec = ValidacaoController(regras_extras=True)
    r, est = medir(lambda: ctl_dec.analisar_fontes(ler(corpus, "misto.py")), REPS)
    magicos = [v for v in r["violacoes"] if v["regra"] == "numero_magico"]
    registrar(ag, "VAL-09", "típico", "Decorator: regra opcional de número mágico acoplada em tempo de execução",
              "3 violações base + ≥1 'numero_magico'", f"{len(r['violacoes']) - len(magicos)} base + {len(magicos)} número(s) mágico(s)",
              len(magicos) >= 1 and len(r["violacoes"]) - len(magicos) == 3, est)

    evento = {"pull_request": {"number": 42}, "files": [
        {"filename": "app/misto.py", "content": (corpus / "misto.py").read_text()},
        {"filename": "README.md", "content": "# doc"}, {"filename": "logo.png", "content": ""}]}
    r, est = medir(lambda: ctl.on_webhook(evento), REPS)
    registrar(ag, "VAL-10", "borda", "Evento de webhook com arquivos não-Python (.md, .png)",
              "apenas o .py analisado (3 violações)", f"{len(r['violacoes'])} violações; relatório com {len(r['relatorio_md'])} caracteres",
              len(r["violacoes"]) == 3, est)
    salvar_evidencia("val_relatorio_pr.md", r["relatorio_md"])

    gt = {(g["arquivo"], g["regra"], g["simbolo"]) for g in json.loads((FX / "validacao/ground_truth.json").read_text())}
    todos = ler(corpus, *[p.name for p in sorted(corpus.glob("*.py"))])
    comparacao = {}
    for rotulo, controlador in (("inicial", ValidacaoController(ajustado=False)), ("ajustada", ctl)):
        obtidos = chaves(controlador.analisar_fontes(todos))
        comparacao[rotulo] = prf(len(obtidos & gt), len(obtidos - gt), len(gt - obtidos))
        comparacao[rotulo]["falsos_positivos"] = sorted("/".join(x) for x in obtidos - gt)
        comparacao[rotulo]["falsos_negativos"] = sorted("/".join(x) for x in gt - obtidos)
    projeto_ini = ValidacaoController(ajustado=False).analisar_diretorio(PROJETO)
    projeto_aj = ctl.analisar_diretorio(PROJETO)

    ad = FX / "validacao" / "antes_depois"
    antes = ctl.analisar_fontes(ler(ad, "antes_pedido.py"))
    depois = ctl.analisar_fontes(ler(ad, "depois_pedido.py"))
    ns_a, ns_d = {}, {}
    exec((ad / "antes_pedido.py").read_text(), ns_a)
    exec((ad / "depois_pedido.py").read_text(), ns_d)
    pedidos = [({"pedidos": 7}, [{"preco": 100, "qtd": 2}, {"preco": 50, "qtd": 0}], "FIDELIDADE", {"uf": "AM"}, "pix", "ok"),
               ({"pedidos": 1}, [{"preco": 80, "qtd": 1}], "PRIMEIRA", {"uf": "PR"}, "cartao", "x" * 250),
               ({"pedidos": 3}, [{"preco": 30, "qtd": 3}], None, {"uf": "SP"}, "boleto", None)]
    equivalentes = all(ns_a["processarPedido"](*p) == ns_d["processar_pedido"](dict(zip(
        ("cliente", "itens", "cupom", "endereco", "pagamento", "observacao"), p))) for p in pedidos)
    cc_a = max(complexidade_ciclomatica(n) for n in __import__("ast").walk(__import__("ast").parse((ad / "antes_pedido.py").read_text()))
               if n.__class__.__name__ == "FunctionDef")
    cc_d = max(complexidade_ciclomatica(n) for n in __import__("ast").walk(__import__("ast").parse((ad / "depois_pedido.py").read_text()))
               if n.__class__.__name__ == "FunctionDef")
    salvar_evidencia("val_antes.md", antes["relatorio_md"])
    salvar_evidencia("val_depois.md", depois["relatorio_md"])
    metricas[ag] = {"corpus": comparacao, "projeto_violacoes_inicial": len(projeto_ini["violacoes"]),
                    "projeto_violacoes_ajustada": len(projeto_aj["violacoes"]),
                    "antes_depois": {"violacoes_antes": len(antes["violacoes"]), "violacoes_depois": len(depois["violacoes"]),
                                     "cc_max_antes": cc_a, "cc_max_depois": cc_d, "comportamento_equivalente": equivalentes}}


# =====================================================================
# Agente 3 — Arquiteto
# =====================================================================
CONTROLLER_OK = "from buscapeca.services.peca_service import PecaService\n\nclass C:\n    pass\n"
SERVICE_OK = "from buscapeca.repositories.peca_repository import PecaRepository\nfrom buscapeca.models import Peca\n"
PRS = {
    "ARQ-01": ("típico", "PR conforme: controller→service e service→repository", [
        ("buscapeca/controllers/anuncio_controller.py", CONTROLLER_OK), ("buscapeca/services/anuncio_service.py", SERVICE_OK)], set()),
    "ARQ-02": ("típico", "Controller importando repositório diretamente (pula a camada de negócio)", [
        ("buscapeca/controllers/peca_controller.py", "from buscapeca.repositories.peca_repository import PecaRepository\n")],
        {("buscapeca/controllers/peca_controller.py", "R1-dependencia-entre-camadas")}),
    "ARQ-03": ("típico", "SQL embutido na camada de negócio", [
        ("buscapeca/services/relatorio_service.py", "def total(con):\n    return con.execute('SELECT SUM(preco) FROM pecas').fetchone()\n")],
        {("buscapeca/services/relatorio_service.py", "R2-sql-fora-da-persistencia")}),
    "ARQ-04": ("típico", "Primitiva criptográfica (hashlib) usada fora da camada de segurança", [
        ("buscapeca/services/cadastro_service.py", "import hashlib\n\ndef h(s):\n    return hashlib.sha256(s.encode()).hexdigest()\n")],
        {("buscapeca/services/cadastro_service.py", "R3-cripto-fora-da-seguranca")}),
    "ARQ-05": ("típico", "Dependência invertida: repositório importando controller", [
        ("buscapeca/repositories/log_repository.py", "from buscapeca.controllers.peca_controller import PecaController\n")],
        {("buscapeca/repositories/log_repository.py", "R1-dependencia-entre-camadas")}),
    "ARQ-06": ("borda", "Import relativo (from ..repositories) que esconde a violação", [
        ("buscapeca/controllers/pedido_controller.py", "from ..repositories.pedido_repository import PedidoRepository\n")],
        {("buscapeca/controllers/pedido_controller.py", "R1-dependencia-entre-camadas")}),
    "ARQ-07": ("borda", "Infraestrutura: DDL fora de migrations/ e porta do banco exposta no manifesto", [
        ("scripts/cria_tabelas.sql", "CREATE TABLE x (id int);"), ("docker-compose.yml", "ports:\n  - \"5432:5432\"\n")],
        {("scripts/cria_tabelas.sql", "R4-ddl-fora-de-migracoes"), ("docker-compose.yml", "R5-banco-exposto")}),
}


def evento(nome, arquivos, numero=7):
    return {"pull_request": {"number": numero, "title": nome},
            "files": [{"filename": f, "status": "modified", "content": c} for f, c in arquivos]}


def agente_arquiteto():
    print("\n[Agente 3] Arquiteto (Rules/Steering)")
    ag = "Arquiteto"
    ctl = ArquitetoController()
    vp = fp = fn = 0
    for cid, (tipo, cenario, arquivos, esperado) in PRS.items():
        r, est = medir(lambda: ctl.receber_evento(evento(cenario, arquivos)), REPS)
        obtido = {(a["arquivo"], a["regra"]) for a in r["achados"]}
        vp += len(obtido & esperado); fp += len(obtido - esperado); fn += len(esperado - obtido)
        registrar(ag, cid, tipo, cenario, f"{len(esperado)} violação(ões)" + (": " + ", ".join(sorted(r_ for _, r_ in esperado)) if esperado else ""),
                  f"status '{r['status']}', {len(obtido)} achado(s)" + (": " + ", ".join(sorted(r_ for _, r_ in obtido)) if obtido else ""),
                  obtido == esperado, est)
        if cid == "ARQ-02":
            salvar_evidencia("arq_relatorio_regras.md", r["relatorio_md"])

    arqs = [("README.md", "# x"), ("docs/logo.png", ""), ("buscapeca/services/s.py", SERVICE_OK)]
    r, est = medir(lambda: ctl.receber_evento(evento("tipos", arqs)), REPS)
    registrar(ag, "ARQ-08", "borda", "PR com arquivos de tipo não suportado (.md, .png)",
              "arquivos ignorados com aviso, 0 achados", f"{len(r['ignorados'])} ignorado(s), {len(r['achados'])} achado(s)",
              len(r["ignorados"]) == 2 and not r["achados"], est)

    orient = ArquitetoController(EstrategiaOrientacao())
    r, est = medir(lambda: orient.receber_evento(evento("orientação", PRS["ARQ-02"][2])), REPS)
    registrar(ag, "ARQ-09", "típico", "Strategy 'Orientação' aplicada à mesma violação do ARQ-02",
              "status 'aprovado com avisos' e severidade AVISO", f"status '{r['status']}', severidade {r['achados'][0]['severidade']}",
              r["status"] == "aprovado com avisos" and r["achados"][0]["severidade"] == "AVISO", est)
    salvar_evidencia("arq_relatorio_orientacao.md", r["relatorio_md"])

    servidor = criar_servidor(8099)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()

    def post(corpo: bytes):
        req = urllib.request.Request("http://127.0.0.1:8099/webhook", data=corpo, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.load(resp)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    (st, corpo), est = medir(lambda: post(b'{"files": "nao-e-lista"}'), REPS)
    registrar(ag, "ARQ-10", "borda", "Webhook HTTP com payload malformado", "HTTP 400 com mensagem de erro",
              f"HTTP {st}: {corpo.get('erro', '')[:50]}", st == 400, est)
    corpo_pr = json.dumps(evento("http", PRS["ARQ-02"][2] + PRS["ARQ-03"][2])).encode()
    (st, corpo), est = medir(lambda: post(corpo_pr), REPS)
    registrar(ag, "ARQ-11", "típico", "Webhook HTTP real (microsserviço) com PR de 2 arquivos violando regras",
              "HTTP 200, status 'reprovado', 2 achados", f"HTTP {st}, status '{corpo['status']}', {len(corpo['achados'])} achados",
              st == 200 and corpo["status"] == "reprovado" and len(corpo["achados"]) == 2, est)
    servidor.shutdown()

    pr_antes = evento("antes", PRS["ARQ-02"][2] + PRS["ARQ-03"][2] + PRS["ARQ-04"][2], 15)
    pr_depois = evento("depois", [
        ("buscapeca/controllers/peca_controller.py", "from buscapeca.services.peca_service import PecaService\n"),
        ("buscapeca/repositories/relatorio_repository.py", "def total(con):\n    return con.execute('SELECT SUM(preco) FROM pecas').fetchone()\n"),
        ("buscapeca/services/cadastro_service.py", "from buscapeca.security.crypto import hash_senha\n")], 15)
    a, d = ctl.receber_evento(pr_antes), ctl.receber_evento(pr_depois)
    salvar_evidencia("arq_antes.md", a["relatorio_md"]); salvar_evidencia("arq_depois.md", d["relatorio_md"])
    projeto = ctl.receber_evento({"pull_request": {"number": 0}, "files": [
        {"filename": p.relative_to(PROJETO).as_posix(), "content": p.read_text(encoding="utf-8")} for p in PROJETO.rglob("*.py")]})
    metricas[ag] = {"deteccao": prf(vp, fp, fn), "antes_depois": {"achados_antes": len(a["achados"]), "achados_depois": len(d["achados"]),
                    "status_antes": a["status"], "status_depois": d["status"]}, "projeto_real_achados": len(projeto["achados"])}


# =====================================================================
# Agente 4 — Code Review (ContextReview)
# =====================================================================
def agente_code_review():
    print("\n[Agente 4] Code Review (ContextReview)")
    ag = "Code Review"
    proj = FX / "code_review" / "projeto"
    gt = json.loads((FX / "code_review/ground_truth.json").read_text())
    rev = PipelineRevisao()

    def chaves(r):
        return {(a["arquivo"], a["regra"], a["linha"]) for a in r["achados"]}

    def sev(r):
        return {(a["arquivo"], a["regra"], a["linha"]): a["severidade"] for a in r["achados"]}

    r, est = medir(lambda: rev.revisar(proj, ["app/busca_repo.py"]), REPS)
    s = sev(r)
    registrar(ag, "CR-01", "típico", "Injeção de SQL via f-string e via concatenação",
              "2 achados Extra High (linhas 7 e 11)", ", ".join(f"L{l}:{v}" for (_, _, l), v in sorted(s.items())),
              s == {("app/busca_repo.py", "SEC-SQL-INJECTION", 7): "Extra High", ("app/busca_repo.py", "SEC-SQL-INJECTION", 11): "Extra High"}, est)
    ref = {(a["arquivo"], a["linha"]) for a in r["refutados"]}
    registrar(ag, "CR-02", "borda", "f-string SQL que interpola apenas constante do módulo (TABELA)",
              "hipótese refutada, não reportada como achado", f"linha 15 {'refutada' if ('app/busca_repo.py', 15) in ref else 'reportada'}",
              ("app/busca_repo.py", 15) in ref and ("app/busca_repo.py", "SEC-SQL-INJECTION", 15) not in chaves(r), est)

    r, est = medir(lambda: rev.revisar(proj, ["app/config.py"]), REPS)
    esperado = {("app/config.py", "SEC-SEGREDO-HARDCODED", 4): "High", ("app/config.py", "SEC-SEGREDO-HARDCODED", 5): "High",
                ("app/config.py", "SEC-HASH-FRACO", 10): "Medium", ("app/config.py", "SEC-SHELL", 14): "High"}
    registrar(ag, "CR-03", "típico", "Segredos hardcoded, MD5 e subprocess com shell=True",
              "3 High + 1 Medium", f"{len(sev(r))} achados: " + ", ".join(f"{list(sev(r).values()).count(n)} {n}" for n in ("Extra High", "High", "Medium", "Low", "Advice") if n in sev(r).values()),
              sev(r) == esperado, est)

    r, est = medir(lambda: rev.revisar(proj, ["app/pedidos.py"]), REPS)
    esperado_ped = {("app/pedidos.py", "COR-DEFAULT-MUTAVEL", 6), ("app/pedidos.py", "COR-EXCEPT-SILENCIOSO", 14),
                    ("app/pedidos.py", "COR-COMPARACAO-NONE", 19), ("app/pedidos.py", "SEC-EVAL", 25), ("app/pedidos.py", "QUA-PRINT", 33)}
    registrar(ag, "CR-04", "típico", "Correção: default mutável, except genérico, == None, eval e print",
              "5 achados (Medium, Medium, Low, High, Advice)", f"{len(chaves(r))} achados; extras: " +
              (", ".join(f"L{l}:{g}" for _, g, l in sorted(chaves(r) - esperado_ped)) or "nenhum"), chaves(r) == esperado_ped, est)
    ref = {(a["arquivo"], a["linha"]) for a in r["refutados"]}
    registrar(ag, "CR-05", "borda", "Linha com supressão explícita '# nosec' revisada", "hipótese refutada",
              f"linha 36 {'refutada' if ('app/pedidos.py', 36) in ref else 'reportada'}", ("app/pedidos.py", 36) in ref, est)
    falso = ("app/pedidos.py", "COR-EXCEPT-SILENCIOSO", 31) in chaves(r)
    registrar(ag, "CR-06", "borda", "except KeyError: pass após log (exceção específica, aceitável)",
              "não reportar", "reportado como Medium (falso positivo)" if falso else "não reportado", not falso, est)

    r, est = medir(lambda: rev.revisar(proj, ["tests/test_config.py"]), REPS)
    registrar(ag, "CR-07", "borda", "Senha fictícia em arquivo de teste", "rebaixado para Advice com refutação parcial",
              ", ".join(f"{a['severidade']} (conf. {a['confianca']})" for a in r["achados"]),
              len(r["achados"]) == 1 and r["achados"][0]["severidade"] == "Advice", est)

    r, est = medir(lambda: rev.revisar(FX / "code_review" / "limpo"), REPS)
    registrar(ag, "CR-08", "típico", "Código limpo (controle de falso positivo)", "0 achados", f"{len(r['achados'])} achados",
              not r["achados"], est)

    copia = TMP / "cr_copia"; shutil.copytree(proj, copia)
    (copia / "app/quebrado.py").write_text("def x(:\n", encoding="utf-8")
    r, est = medir(lambda: rev.revisar(copia), REPS)
    registrar(ag, "CR-09", "borda", "Projeto completo com 1 arquivo de sintaxe inválida; verificação de somente leitura",
              "erro registrado, demais arquivos revisados, hashes SHA-256 idênticos antes/depois",
              f"{len(r['erros'])} erro(s), {len(r['achados'])} achados, somente leitura: {r['somente_leitura_ok']}",
              len(r["erros"]) == 1 and r["somente_leitura_ok"] and len(r["achados"]) >= 12, est)

    r = rev.revisar(proj)
    salvar_evidencia("cr_relatorio.md", r["relatorio_md"])
    positivos = {(p["arquivo"], p["regra"], p["linha"]): p["severidade"] for p in gt["positivos"]}
    obtidos = sev(r)
    vp = set(obtidos) & set(positivos)
    sev_ok = sum(1 for k in vp if obtidos[k] == positivos[k])
    com_evidencia = sum(1 for a in r["achados"] if a["evidencia"] and a["linha"] > 0)
    refutados_ok = sum(1 for x in gt["devem_ser_refutados"] if (x["arquivo"], x["linha"]) in {(a["arquivo"], a["linha"]) for a in r["refutados"]})
    metricas[ag] = {"deteccao": prf(len(vp), len(set(obtidos) - set(positivos)), len(set(positivos) - set(obtidos))),
                    "acuracia_severidade": sev_ok / len(vp) if vp else 0, "achados_com_evidencia_pct": 100 * com_evidencia / len(r["achados"]),
                    "refutacoes_corretas": f"{refutados_ok}/{len(gt['devem_ser_refutados'])}", "somente_leitura_ok": r["somente_leitura_ok"],
                    "por_severidade": {s_: sum(1 for v in obtidos.values() if v == s_) for s_ in ("Extra High", "High", "Medium", "Low", "Advice")},
                    "projeto_real_achados": len(rev.revisar(PROJETO)["achados"])}


# =====================================================================
# Agente 5 — QualityBridge
# =====================================================================
def oraculo_unittest(raiz, caminho="tests"):
    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", caminho, "-t", "."], cwd=raiz,
                          capture_output=True, text=True)
    total = int(re.search(r"Ran (\d+) test", proc.stderr).group(1))
    m = re.search(r"failures=(\d+)", proc.stderr)
    return total, int(m.group(1)) if m else 0


def agente_qualitybridge():
    print("\n[Agente 5] Testes de Software (QualityBridge)")
    ag = "Testes (QualityBridge)"
    proj = TMP / "qb_proj"; shutil.copytree(PROJETO, proj)
    cfg = proj / "qualitybridge.yaml"

    def rodar(estrategia="completa", config=cfg):
        return qb.QualityBridge(qb.carregar_configuracao(config), estrategia).executar()

    total_or, falhas_or = oraculo_unittest(proj)
    _, est_or = medir(lambda: oraculo_unittest(proj), REPS_QB)
    e, est = medir(rodar, REPS_QB)
    t = e["totais"]
    registrar(ag, "QB-01", "típico", "Estratégia completa a partir do qualitybridge.yaml",
              f"{total_or} testes e {falhas_or} falhas (oráculo: unittest direto)", f"{t['total']} testes, {t['falhou']} falhas, status {e['status']}",
              t["total"] == total_or and t["falhou"] == falhas_or, est)
    duracao_completa = est["media_ms"]

    unit_or, _ = oraculo_unittest(proj, "tests/unit")
    e2, est = medir(lambda: rodar("rapida"), REPS_QB)
    registrar(ag, "QB-02", "típico", "Strategy 'rápida' (somente suítes marcadas como rápidas)",
              f"{unit_or} testes unitários, sem integração", f"{e2['totais']['total']} testes em {len(e2['suites'])} suíte(s)",
              e2["totais"]["total"] == unit_or and len(e2["suites"]) == 1, est)
    duracao_rapida = est["media_ms"]

    def ler_html():
        html = (proj / "qb_relatorios/relatorio.html").read_text(encoding="utf-8")
        return {k: int(re.search(rf'id="{k}">(\d+)<', html).group(1)) for k in ("total", "passou", "falhou")}
    rodar()
    js = json.loads((proj / "qb_relatorios/relatorio.json").read_text())
    h, est = medir(ler_html, REPS_QB)
    junit = qb.ET.parse(proj / "qb_relatorios/junit.xml").getroot()
    registrar(ag, "QB-03", "típico", "Relatório HTML/JSON/JUnit consolidado sem perda de informação",
              "totais idênticos nos 3 formatos", f"HTML {h['total']}/{h['passou']}, JSON {js['totais']['total']}/{js['totais']['passou']}, JUnit tests={junit.get('tests')}",
              h["total"] == js["totais"]["total"] == int(junit.get("tests")) and h["passou"] == js["totais"]["passou"], est)

    banco = proj / "qualitybridge.db"
    antes = sqlite3.connect(banco).execute("SELECT COUNT(*) FROM execucoes").fetchone()[0]
    _, est = medir(rodar, 3)
    depois = sqlite3.connect(banco).execute("SELECT COUNT(*) FROM execucoes").fetchone()[0]
    registrar(ag, "QB-04", "típico", "Persistência do histórico de execuções em SQLite local",
              "+4 registros (3 medições + 1 execução de memória)", f"{antes} → {depois} registros (+{depois - antes})", depois - antes == 4, est)

    ruim = proj / "invalido.yaml"; ruim.write_text("suites: [nome: x\n  executor", encoding="utf-8")
    codigo, est = medir(lambda: qb.main(["run", "--config", str(ruim)]), REPS_QB)
    registrar(ag, "QB-05", "borda", "YAML de configuração com sintaxe inválida", "erro controlado, código de saída 2",
              f"código de saída {codigo}", codigo == 2, est)

    falho = TMP / "qb_falho"; shutil.copytree(PROJETO, falho)
    (falho / "tests/unit/test_regressao.py").write_text(
        "import unittest\nfrom buscapeca.services.peca_service import FATOR_DEPRECIACAO\n\n\nclass TestRegressao(unittest.TestCase):\n"
        "    def test_fator_usada_regrediu(self):\n        self.assertEqual(FATOR_DEPRECIACAO['usada'], 0.7)\n", encoding="utf-8")
    tot_f, fal_f = oraculo_unittest(falho)
    e6, est = medir(lambda: rodar(config=falho / "qualitybridge.yaml"), REPS_QB)
    falhas = [t_["nome"] for s in e6["suites"] for t_ in s["testes"] if t_["status"] == "falhou"]
    jf = qb.ET.parse(falho / "qb_relatorios/junit.xml").getroot()
    registrar(ag, "QB-06", "borda", "Suíte com 1 teste de regressão falhando",
              f"status FALHOU, {fal_f} falha listada, JUnit failures={fal_f}", f"status {e6['status']}, falhas: {[f.split('.')[-1] for f in falhas]}, JUnit failures={jf.get('failures')}",
              e6["status"] == "FALHOU" and len(falhas) == fal_f == 1 and jf.get("failures") == "1", est)

    e7 = rodar()
    indisp = [s for s in e7["suites"] if s["situacao"] == "indisponivel"]
    _, est = medir(lambda: qb.FabricaExecutores.criar("playwright").rodar(qb.Suite("e2e-web", "playwright", "e2e"), proj), REPS)
    registrar(ag, "QB-07", "borda", "Executor Playwright indisponível no ambiente (Factory Method)",
              "suíte marcada 'indisponível' sem interromper as demais", f"{len(indisp)} suíte indisponível; {e7['totais']['total']} testes executados nas demais",
              len(indisp) == 1 and e7["totais"]["total"] == total_or, est)

    vazia = proj / "vazia.yaml"
    (proj / "tests/vazia").mkdir(exist_ok=True)
    vazia.write_text("projeto: vazio\nsuites:\n  - nome: vazia\n    executor: unittest\n    caminho: tests/vazia\n", encoding="utf-8")
    e8, est = medir(lambda: rodar(config=vazia), REPS_QB)
    registrar(ag, "QB-08", "borda", "Suíte configurada sem nenhum teste", "0 testes, status PASSOU, sem exceção",
              f"{e8['totais']['total']} testes, status {e8['status']}", e8["totais"]["total"] == 0 and e8["status"] == "PASSOU", est)

    proc = subprocess.run([sys.executable, "-m", "agents.qualitybridge.agente", "run", "--config", str(cfg)], cwd=BASE,
                          capture_output=True, text=True)
    salvar_evidencia("qb_saida_cli.txt", "$ python -m agents.qualitybridge.agente run --config qualitybridge.yaml\n" + proc.stdout)
    salvar_evidencia("qb_relatorio.html", (proj / "qb_relatorios/relatorio.html").read_text(encoding="utf-8"))
    metricas[ag] = {"fidelidade_contagens_pct": 100.0 if t["total"] == total_or else 100 * t["total"] / total_or,
                    "tempo_completa_ms": duracao_completa, "tempo_rapida_ms": duracao_rapida, "tempo_oraculo_ms": est_or["media_ms"],
                    "overhead_ms": duracao_completa - est_or["media_ms"], "reducao_rapida_pct": 100 * (1 - duracao_rapida / duracao_completa),
                    "testes_projeto": total_or}


def main():
    RES.mkdir(exist_ok=True); EVID.mkdir(parents=True, exist_ok=True)
    print(f"Ambiente: Python {platform.python_version()} · {platform.system()} {platform.machine()} · {datetime.now():%d/%m/%Y %H:%M}")
    agente_documentacao(); agente_validacao(); agente_arquiteto(); agente_code_review(); agente_qualitybridge()
    with open(RES / "casos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(casos[0]), delimiter=";"); w.writeheader(); w.writerows(casos)
    with open(RES / "amostras_tempo.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["agente", "caso", "tempo_ms"], delimiter=";"); w.writeheader(); w.writerows(amostras)
    metricas["_ambiente"] = {"python": platform.python_version(), "so": f"{platform.system()} {platform.release()}",
                             "cpu": platform.machine(), "data": datetime.now().isoformat(timespec="seconds"),
                             "repeticoes": REPS, "repeticoes_qb": REPS_QB}
    (RES / "metricas.json").write_text(json.dumps(metricas, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    passou = sum(c["passou"] for c in casos)
    print(f"\nTOTAL: {passou}/{len(casos)} casos aprovados")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
