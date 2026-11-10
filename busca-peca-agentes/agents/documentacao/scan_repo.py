"""Filtro 1 — Coleta: varredura determinística do repositório (Pure Fabrication)."""
import ast
from pathlib import Path

CAMADAS = {"controllers": "apresentação", "services": "negócio", "repositories": "persistência",
           "security": "segurança"}


def _publico(nome: str) -> bool:
    return not nome.startswith("_")


def _funcao(no) -> dict:
    return {"nome": no.name, "args": [a.arg for a in no.args.args if a.arg != "self"],
            "retorno": ast.unparse(no.returns) if no.returns else None,
            "docstring": ast.get_docstring(no), "linha": no.lineno}


def camada_de(caminho: str) -> str:
    for parte, camada in CAMADAS.items():
        if f"/{parte}/" in "/" + caminho:
            return camada
    return "domínio" if caminho.endswith("models.py") else "infraestrutura"


def varrer(raiz) -> dict:
    raiz = Path(raiz)
    inventario = {"modulos": [], "adrs": [], "erros": [], "readme": (raiz / "README.md").exists()}
    for arquivo in sorted(raiz.rglob("*.py")):
        rel = arquivo.relative_to(raiz).as_posix()
        if rel.startswith("tests/") or arquivo.name == "__init__.py":
            continue
        try:
            arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        except SyntaxError as erro:
            inventario["erros"].append({"arquivo": rel, "erro": f"sintaxe inválida (linha {erro.lineno})"})
            continue
        modulo = {"caminho": rel, "camada": camada_de(rel), "docstring": ast.get_docstring(arvore),
                  "classes": [], "funcoes": []}
        for no in arvore.body:
            if isinstance(no, ast.ClassDef) and _publico(no.name):
                metodos = [_funcao(m) for m in no.body
                           if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and _publico(m.name)]
                modulo["classes"].append({"nome": no.name, "docstring": ast.get_docstring(no),
                                          "linha": no.lineno, "metodos": metodos})
            elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and _publico(no.name):
                modulo["funcoes"].append(_funcao(no))
        inventario["modulos"].append(modulo)
    for adr in sorted((raiz / "docs" / "adr").glob("*.md")) if (raiz / "docs" / "adr").exists() else []:
        linhas = adr.read_text(encoding="utf-8").splitlines()
        status = next((l.split(":", 1)[1].strip() for l in linhas if l.lower().startswith("status")), "indefinido")
        rejeitadas = next((l.split(":", 1)[1].strip() for l in linhas if l.lower().startswith("alternativas")), "")
        inventario["adrs"].append({"arquivo": adr.name, "titulo": linhas[0].lstrip("# ").strip(),
                                   "status": status, "rejeitadas": rejeitadas})
    return inventario


def elementos_publicos(inventario: dict):
    """Gera (tipo, identificador, documentado?) para cada elemento público."""
    for m in inventario["modulos"]:
        yield "modulo", m["caminho"], bool(m["docstring"])
        for c in m["classes"]:
            yield "classe", f'{m["caminho"]}::{c["nome"]}', bool(c["docstring"])
            for f in c["metodos"]:
                yield "funcao", f'{m["caminho"]}::{c["nome"]}.{f["nome"]}', bool(f["docstring"])
        for f in m["funcoes"]:
            yield "funcao", f'{m["caminho"]}::{f["nome"]}', bool(f["docstring"])


def cobertura_docstrings(inventario: dict) -> float:
    elementos = list(elementos_publicos(inventario))
    return 100.0 * sum(1 for *_, ok in elementos if ok) / len(elementos) if elementos else 0.0
