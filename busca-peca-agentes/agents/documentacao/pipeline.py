"""Agente de Documentação — pipeline pipe-and-filter (Template Method) com Builder."""
import argparse
import ast
import json
import shutil
from pathlib import Path

from agents.common.llm import criar_provedor
from agents.documentacao.scan_repo import cobertura_docstrings, varrer
from agents.documentacao.validate_doc import cadeia_padrao

MAX_PERGUNTAS = 5
REFERENCIAS_PADRAO = [
    "BASS, L.; CLEMENTS, P.; KAZMAN, R. Software architecture in practice. 3. ed. Boston: Addison-Wesley, 2012.",
    "GAMMA, E. et al. Padrões de projeto: soluções reutilizáveis de software orientado a objetos. Porto Alegre: Bookman, 2000.",
]
EXPLICACAO_CAMADA = {
    "apresentação": "recebe os pedidos de quem usa o sistema e devolve respostas",
    "negócio": "guarda as regras do marketplace (preço sugerido, estoque, frete)",
    "persistência": "salva e busca dados no banco",
    "segurança": "protege senhas e acessos",
    "domínio": "define o que é uma peça, um pedido e um item",
    "infraestrutura": "dá suporte técnico às demais partes",
}


# ---------------- Builder (GoF criação) ----------------
class DocumentoBuilder:
    def __init__(self):
        self.partes = []

    def titulo(self, modelo): ...
    def visao_geral(self, modelo): ...
    def modulos(self, modelo): ...
    def decisoes(self, modelo): ...

    def referencias(self, modelo):
        self.partes.append("## Referências\n" + "\n".join(f"- {r}" for r in modelo["referencias"]))

    def construir(self) -> str:
        return "\n\n".join(self.partes) + "\n"


class TecnicoBuilder(DocumentoBuilder):
    def titulo(self, m):
        self.partes.append(f"# {m['projeto']} — Documentação Técnica")

    def visao_geral(self, m):
        camadas = sorted({x["camada"] for x in m["modulos"]})
        mermaid = "```mermaid\nflowchart TD\n" + "\n".join(
            f"  {a}[{a}] --> {b}[{b}]" for a, b in [("apresentacao", "negocio"), ("negocio", "persistencia"),
                                                     ("negocio", "seguranca")]) + "\n```"
        self.partes.append(f"## Visão geral\n{m['proposito']}\n\nCamadas: {', '.join(camadas)}.\n\n{mermaid}")

    def modulos(self, m):
        linhas = ["## Módulos"]
        for mod in m["modulos"]:
            linhas.append(f"### `{mod['caminho']}` ({mod['camada']})\n{mod['responsabilidade']} _(fonte: {mod['fonte']})_")
            for c in mod["classes"]:
                metodos = ", ".join(f"`{f['nome']}({', '.join(f['args'])})`" for f in c["metodos"])
                linhas.append(f"- Classe `{c['nome']}`: {metodos or 'sem métodos públicos'}")
            for f in mod["funcoes"]:
                linhas.append(f"- Função `{f['nome']}({', '.join(f['args'])})` -> {f['retorno'] or 'None'}")
        self.partes.append("\n".join(linhas))

    def decisoes(self, m):
        linhas = ["## Decisões de arquitetura"] + [
            f"- **{a['titulo']}** ({a['status']}). Alternativas rejeitadas: {a['rejeitadas'] or 'não registradas'}"
            for a in m["adrs"]]
        self.partes.append("\n".join(linhas if m["adrs"] else linhas + ["- Nenhum ADR encontrado."]))


class DidaticoBuilder(DocumentoBuilder):
    def __init__(self, llm):
        super().__init__()
        self.llm = llm

    def titulo(self, m):
        self.partes.append(f"# {m['projeto']} — Guia Didático para Novos Integrantes")

    def visao_geral(self, m):
        self.partes.append("## Visão geral\n" + self.llm.completar("explicacao_didatica", {
            "explicacao": f"{m['proposito']} O código é dividido em partes com papéis bem definidos."}))

    def modulos(self, m):
        linhas = ["## Módulos"]
        for mod in m["modulos"]:
            linhas.append(f"- `{mod['caminho']}`: esta parte {EXPLICACAO_CAMADA[mod['camada']]}. "
                          f"{mod['responsabilidade']}")
        self.partes.append("\n".join(linhas))

    def decisoes(self, m):
        linhas = ["## Decisões de arquitetura"]
        for a in m["adrs"]:
            rejeitada = (a["rejeitadas"] or "não registrada").rstrip(".")
            linhas.append(f"- {a['titulo']}: a equipe escolheu este caminho e descartou a alternativa {rejeitada}.")
        self.partes.append("\n".join(linhas if m["adrs"] else linhas + ["- Ainda não há decisões registradas."]))


def dirigir(builder: DocumentoBuilder, modelo: dict) -> str:
    for etapa in (builder.titulo, builder.visao_geral, builder.modulos, builder.decisoes, builder.referencias):
        etapa(modelo)
    return builder.construir()


# ---------------- docstrings ----------------
def texto_docstring(no) -> str:
    acao = no.name.replace("_", " ").strip().capitalize()
    args = [a.arg for a in no.args.args if a.arg != "self"]
    partes = [f"{acao}."]
    if args:
        partes.append(f"Parâmetros: {', '.join(args)}.")
    if no.returns is not None:
        partes.append(f"Retorna: {ast.unparse(no.returns)}.")
    return " ".join(partes)


def inserir_docstrings(origem: Path, destino: Path, resumos: dict = None) -> int:
    """Copia o código para `destino` inserindo docstrings ausentes; retorna quantas foram inseridas."""
    inseridas, resumos = 0, resumos or {}
    for arquivo in origem.rglob("*.py"):
        alvo = destino / arquivo.relative_to(origem)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        fonte = arquivo.read_text(encoding="utf-8")
        try:
            arvore = ast.parse(fonte)
        except SyntaxError:
            alvo.write_text(fonte, encoding="utf-8")
            continue
        linhas = fonte.splitlines()
        pontos = []
        for no in ast.walk(arvore):
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not no.name.startswith("_") \
                    and ast.get_docstring(no) is None:
                corpo = no.body[0]
                texto = texto_docstring(no) if not isinstance(no, ast.ClassDef) else f"Classe {no.name}."
                pontos.append((corpo.lineno - 1, " " * corpo.col_offset + f'"""{texto}"""'))
        rel = arquivo.relative_to(origem).as_posix()
        if rel in resumos and ast.get_docstring(arvore) is None:  # ajuste Entrega 2: docstring de módulo
            pontos.append((0, f'"""{resumos[rel]}"""'))
        for indice, linha in sorted(pontos, key=lambda p: p[0], reverse=True):
            linhas.insert(indice, linha)
        inseridas += len(pontos)
        alvo.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return inseridas


# ---------------- Pipeline (Template Method) ----------------
class PipelineDocumentacao:
    def __init__(self, respostas=None, aprovar=None, llm=None):
        self.respostas = respostas or {}
        self.aprovar = aprovar or (lambda portao, dados: True)
        self.llm = llm or criar_provedor()

    def executar(self, raiz, saida) -> dict:
        raiz, saida = Path(raiz), Path(saida)
        inventario = self.coletar(raiz)
        perguntas = self.entrevistar(inventario)
        if not self.aprovar("portao1", {"inventario": inventario, "perguntas": perguntas}):
            return {"status": "interrompido no portão 1", "perguntas": perguntas}
        modelo = self.sintetizar(inventario, perguntas)
        docs = self.renderizar(modelo)
        lacunas = self.validar(docs, inventario)
        aprovado = self.aprovar("portao2", {"lacunas": lacunas})
        resultado = {"status": "gravado" if aprovado else "devolvido para correção", "inventario": inventario,
                     "perguntas": perguntas, "lacunas": lacunas, "modelo": modelo, "docs": docs,
                     "cobertura_antes": cobertura_docstrings(inventario)}
        if aprovado:
            self.gravar(raiz, saida, docs, lacunas, resultado)
        return resultado

    def coletar(self, raiz):
        return varrer(raiz)

    def entrevistar(self, inv):
        pendencias = [("proposito", "Qual é o propósito do projeto e quem são os usuários?")] if not inv["readme"] else []
        pendencias += [(m["caminho"], f"Qual a responsabilidade do módulo {m['caminho']}?")
                       for m in inv["modulos"] if not m["docstring"]]
        return [{"id": pid, "pergunta": txt, "resposta": self.respostas.get(pid)} for pid, txt in pendencias[:MAX_PERGUNTAS]]

    def sintetizar(self, inv, perguntas):
        respostas = {p["id"]: p["resposta"] for p in perguntas if p["resposta"]}
        modulos = []
        for m in inv["modulos"]:
            if m["docstring"]:
                resp, fonte = m["docstring"].splitlines()[0], "docstring"
            elif m["caminho"] in respostas:
                resp, fonte = respostas[m["caminho"]], "entrevista"
            else:
                resp, fonte = f"Componente da camada de {m['camada']} (responsabilidade inferida pela estrutura).", "inferida"
            modulos.append({**m, "responsabilidade": resp, "fonte": fonte})
        return {"projeto": "Busca Peça", "modulos": modulos, "adrs": inv["adrs"],
                "proposito": respostas.get("proposito", "Propósito não informado na entrevista."),
                "referencias": REFERENCIAS_PADRAO}

    def renderizar(self, modelo):
        return {"tecnico": dirigir(TecnicoBuilder(), modelo), "didatico": dirigir(DidaticoBuilder(self.llm), modelo)}

    def validar(self, docs, inv):
        lacunas = []
        for nome, texto in docs.items():
            lacunas += [{"documento": nome, "tipo": t, "detalhe": d} for t, d in cadeia_padrao().validar(texto, inv, [])]
        lacunas += [{"documento": "código", "tipo": "coleta", "detalhe": f"{e['arquivo']}: {e['erro']}"} for e in inv["erros"]]
        lacunas += [{"documento": "entrevista", "tipo": "resposta pendente", "detalhe": p["pergunta"]}
                    for p in self.entrevistar(inv) if not p["resposta"]]
        if not inv["modulos"]:
            lacunas.append({"documento": "código", "tipo": "coleta", "detalhe": "nenhum módulo Python encontrado"})
        return lacunas

    def gravar(self, raiz, saida, docs, lacunas, resultado):
        if saida.exists():
            shutil.rmtree(saida)
        saida.mkdir(parents=True)
        (saida / "README_tecnico.md").write_text(docs["tecnico"], encoding="utf-8")
        (saida / "GUIA_didatico.md").write_text(docs["didatico"], encoding="utf-8")
        (saida / "LACUNAS.md").write_text("# Relatório de lacunas\n" + "\n".join(
            f"- [{l['documento']}] {l['tipo']}: {l['detalhe']}" for l in lacunas) + "\n", encoding="utf-8")
        resultado["docstrings_inseridas"] = inserir_docstrings(
            raiz, saida / "codigo_documentado",
            {m["caminho"]: m["responsabilidade"] for m in resultado["modelo"]["modulos"]}) if \
            any(raiz.rglob("*.py")) else 0
        resultado["cobertura_depois"] = cobertura_docstrings(varrer(saida / "codigo_documentado")) if \
            (saida / "codigo_documentado").exists() else 0.0


def main():
    ap = argparse.ArgumentParser(description="Agente de Documentação de Software")
    ap.add_argument("raiz"); ap.add_argument("saida"); ap.add_argument("--respostas")
    a = ap.parse_args()
    respostas = json.loads(Path(a.respostas).read_text(encoding="utf-8")) if a.respostas else {}
    r = PipelineDocumentacao(respostas).executar(a.raiz, a.saida)
    print(f"status={r['status']} lacunas={len(r['lacunas'])} cobertura {r['cobertura_antes']:.1f}% -> "
          f"{r.get('cobertura_depois', 0):.1f}%")


if __name__ == "__main__":
    main()
