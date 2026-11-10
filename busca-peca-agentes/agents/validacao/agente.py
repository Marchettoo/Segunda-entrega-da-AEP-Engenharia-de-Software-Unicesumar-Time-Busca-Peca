"""Agente de Validação de Código (Boas Práticas / Clean Code).

Pipe-and-filter encapsulado em microsserviço orientado a eventos:
Controller (webhook) -> Parser AST -> Chain of Responsibility (handlers) -> Builder (relatório) -> View Markdown.
"""
import ast
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from agents.common.llm import criar_provedor

LIMITES = {"complexidade": 10, "linhas_funcao": 30, "parametros": 5, "janela_duplicacao": 3}
NOMES_CURTOS_PERMITIDOS = {"i", "j", "k", "_", "e"}
SNAKE = re.compile(r"^_{0,2}[a-z][a-z0-9_]*_{0,2}$")
PASCAL = re.compile(r"^_?[A-Z][a-zA-Z0-9]*$")
DICAS = {
    "complexidade": "extraia condições para funções auxiliares ou use tabelas de decisão",
    "tamanho": "divida a função em passos menores com nomes descritivos",
    "parametros": "agrupe parâmetros relacionados em um objeto (Parameter Object)",
    "duplicacao": "extraia o bloco repetido para uma função reutilizável (DRY)",
    "nomenclatura": "use snake_case para funções/variáveis e PascalCase para classes, com nomes descritivos",
    "numero_magico": "substitua o literal por uma constante nomeada",
}


@dataclass
class Violacao:
    arquivo: str
    regra: str
    simbolo: str
    linha: int
    detalhe: str


# -------- Model: Chain of Responsibility --------
class Handler:
    def __init__(self, proximo=None):
        self.proximo = proximo

    def tratar(self, contexto: dict, achados: list) -> list:
        achados.extend(self.analisar(contexto))
        return self.proximo.tratar(contexto, achados) if self.proximo else achados

    def analisar(self, ctx):
        raise NotImplementedError


def funcoes(arvore):
    return [n for n in ast.walk(arvore) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


HOOKS_FRAMEWORK = {"setUp", "tearDown", "setUpClass", "tearDownClass", "setUpModule", "tearDownModule", "asyncSetUp"}


class NomenclaturaHandler(Handler):
    def __init__(self, proximo=None, ajustado=True):
        super().__init__(proximo)
        self.ajustado = ajustado  # ajuste Entrega 2: ignora hooks de framework e variáveis de compreensão

    def analisar(self, ctx):
        achados = []
        alvos_compreensao = {id(n) for c in ast.walk(ctx["arvore"]) if isinstance(c, ast.comprehension)
                             for n in ast.walk(c.target)} if self.ajustado else set()
        for no in ast.walk(ctx["arvore"]):
            if self.ajustado and id(no) in alvos_compreensao:
                continue
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and self.ajustado and no.name in HOOKS_FRAMEWORK:
                continue
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and not SNAKE.match(no.name):
                achados.append(Violacao(ctx["arquivo"], "nomenclatura", no.name, no.lineno, "função fora de snake_case"))
            elif isinstance(no, ast.ClassDef) and not PASCAL.match(no.name):
                achados.append(Violacao(ctx["arquivo"], "nomenclatura", no.name, no.lineno, "classe fora de PascalCase"))
            elif isinstance(no, ast.Name) and isinstance(no.ctx, ast.Store) and len(no.id) == 1 \
                    and no.id not in NOMES_CURTOS_PERMITIDOS:
                achados.append(Violacao(ctx["arquivo"], "nomenclatura", no.id, no.lineno, "nome de variável não descritivo"))
        return achados


class TamanhoHandler(Handler):
    def analisar(self, ctx):
        achados = []
        for f in funcoes(ctx["arvore"]):
            linhas = f.end_lineno - f.lineno + 1
            if linhas > LIMITES["linhas_funcao"]:
                achados.append(Violacao(ctx["arquivo"], "tamanho", f.name, f.lineno, f"{linhas} linhas (> {LIMITES['linhas_funcao']})"))
            n_param = len([a for a in f.args.args + f.args.kwonlyargs if a.arg not in ("self", "cls")])
            if n_param > LIMITES["parametros"]:
                achados.append(Violacao(ctx["arquivo"], "parametros", f.name, f.lineno, f"{n_param} parâmetros (> {LIMITES['parametros']})"))
        return achados


class _Normalizador(ast.NodeTransformer):
    def visit_Name(self, no):
        return ast.copy_location(ast.Name(id="_v", ctx=no.ctx), no)

    def visit_Constant(self, no):
        return ast.copy_location(ast.Constant(value="_c"), no)


class DuplicacaoHandler(Handler):
    def analisar(self, ctx):
        janela, vistos, achados, pares = LIMITES["janela_duplicacao"], {}, [], set()
        for f in funcoes(ctx["arvore"]):
            corpo = f.body
            for i in range(len(corpo) - janela + 1):
                bloco = corpo[i:i + janela]
                if bloco[-1].end_lineno - bloco[0].lineno + 1 < 4:
                    continue
                assinatura = hashlib.md5("".join(ast.dump(_Normalizador().visit(ast.parse(ast.unparse(s))))
                                                 for s in bloco).encode()).hexdigest()
                origem = vistos.setdefault(assinatura, f.name)
                if origem != f.name and (origem, f.name) not in pares:
                    pares.add((origem, f.name))
                    achados.append(Violacao(ctx["arquivo"], "duplicacao", f.name, bloco[0].lineno,
                                            f"bloco de {janela}+ instruções duplicado de `{origem}`"))
        return achados


def complexidade_ciclomatica(funcao) -> int:
    cc = 1
    for no in ast.walk(funcao):
        if isinstance(no, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp, ast.ExceptHandler, ast.Assert)):
            cc += 1
        elif isinstance(no, ast.BoolOp):
            cc += len(no.values) - 1
        elif isinstance(no, ast.comprehension):
            cc += 1 + len(no.ifs)
        elif isinstance(no, ast.match_case):
            cc += 1
    return cc


class ComplexidadeHandler(Handler):
    def analisar(self, ctx):
        return [Violacao(ctx["arquivo"], "complexidade", f.name, f.lineno, f"CC={cc} (> {LIMITES['complexidade']})")
                for f in funcoes(ctx["arvore"]) if (cc := complexidade_ciclomatica(f)) > LIMITES["complexidade"]]


# -------- Decorator (GoF estrutural): regras opcionais acopladas dinamicamente --------
class Analisador:
    def __init__(self, ajustado=True):
        self.cadeia = NomenclaturaHandler(TamanhoHandler(DuplicacaoHandler(ComplexidadeHandler())), ajustado)

    def analisar(self, ctx):
        return self.cadeia.tratar(ctx, [])


class RegraDecorator(Analisador):
    def __init__(self, interno: Analisador):
        self.interno = interno

    def analisar(self, ctx):
        return self.interno.analisar(ctx) + self.extra(ctx)


class NumeroMagicoDecorator(RegraDecorator):
    PERMITIDOS = {0, 1, -1, 2, 100}

    def extra(self, ctx):
        achados = []
        for f in funcoes(ctx["arvore"]):
            for no in ast.walk(f):
                if isinstance(no, ast.Compare):
                    for c in [no.left, *no.comparators]:
                        if isinstance(c, ast.Constant) and isinstance(c.value, (int, float)) \
                                and not isinstance(c.value, bool) and c.value not in self.PERMITIDOS:
                            achados.append(Violacao(ctx["arquivo"], "numero_magico", f.name, c.lineno, f"literal {c.value}"))
        return achados


# -------- Builder (GoF criação) + View --------
class RelatorioBuilder:
    def __init__(self, llm):
        self.llm, self.secoes = llm, []

    def cabecalho(self, arquivos, achados):
        status = "✅ aprovado" if not achados else f"⚠️ {len(achados)} violação(ões)"
        self.secoes.append(f"## Agente de Validação de Código\n**Arquivos analisados:** {arquivos} · **Status:** {status}")
        return self

    def tabela(self, achados):
        if achados:
            self.secoes.append("| Arquivo | Linha | Regra | Símbolo | Detalhe |\n|---|---|---|---|---|\n" + "\n".join(
                f"| {v.arquivo} | {v.linha} | {v.regra} | `{v.simbolo}` | {v.detalhe} |" for v in achados))
        return self

    def recomendacoes(self, achados):
        if achados:
            self.secoes.append("### Recomendações de refatoração\n" + "\n".join(
                "- " + self.llm.completar("sugestao_refatoracao", {"regra": v.regra, "simbolo": v.simbolo, "dica": DICAS[v.regra]})
                for v in achados))
        return self

    def erros(self, erros):
        if erros:
            self.secoes.append("### Arquivos não analisados\n" + "\n".join(f"- {e}" for e in erros))
        return self

    def construir(self):
        return "\n\n".join(self.secoes) + "\n"


# -------- Controller (GRASP) --------
class ValidacaoController:
    def __init__(self, regras_extras=False, llm=None, ajustado=True):
        base = Analisador(ajustado)
        self.analisador = NumeroMagicoDecorator(base) if regras_extras else base
        self.llm = llm or criar_provedor()

    def analisar_fontes(self, fontes: dict) -> dict:
        achados, erros = [], []
        for nome, codigo in fontes.items():
            try:
                arvore = ast.parse(codigo)
            except SyntaxError as e:
                erros.append(f"{nome}: sintaxe inválida na linha {e.lineno}")
                continue
            achados += self.analisador.analisar({"arquivo": nome, "arvore": arvore})
        relatorio = RelatorioBuilder(self.llm).cabecalho(len(fontes), achados).tabela(achados) \
            .recomendacoes(achados).erros(erros).construir()
        return {"violacoes": [asdict(v) for v in achados], "erros": erros, "relatorio_md": relatorio}

    def on_webhook(self, evento: dict) -> dict:
        """Evento de push em Pull Request: {'pull_request': {...}, 'files': [{'filename','content'}]}."""
        arquivos = {f["filename"]: f["content"] for f in evento.get("files", []) if f["filename"].endswith(".py")}
        return self.analisar_fontes(arquivos)

    def analisar_diretorio(self, raiz) -> dict:
        raiz = Path(raiz)
        return self.analisar_fontes({p.relative_to(raiz).as_posix(): p.read_text(encoding="utf-8")
                                     for p in sorted(raiz.rglob("*.py"))})


if __name__ == "__main__":
    import sys
    r = ValidacaoController().analisar_diretorio(sys.argv[1])
    print(r["relatorio_md"])
