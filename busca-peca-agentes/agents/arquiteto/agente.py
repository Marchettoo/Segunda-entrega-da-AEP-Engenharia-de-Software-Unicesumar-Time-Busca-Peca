"""Agente Arquiteto (Rules/Steering) — microsserviço orientado a eventos.

Webhook (Pull Request) -> Controller (GRASP) -> Factory Method (analisador por tipo de arquivo)
-> Facade (análise estrutural via AST) -> Strategy (Regras x Orientação) -> View Markdown.
"""
import ast
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import PurePosixPath

CAMADA_POR_PASTA = {"controllers": "apresentacao", "services": "negocio", "repositories": "persistencia",
                    "security": "seguranca", "models": "dominio"}
DEPENDENCIAS_PERMITIDAS = {
    "apresentacao": {"negocio", "dominio"},
    "negocio": {"persistencia", "seguranca", "dominio"},
    "persistencia": {"dominio"},
    "seguranca": {"dominio"},
    "dominio": set(),
}
SQL = re.compile(r"\b(SELECT\b.+\bFROM|INSERT\s+INTO|UPDATE\b.+\bSET|DELETE\s+FROM|CREATE\s+TABLE|DROP\s+TABLE)\b",
                 re.IGNORECASE | re.DOTALL)
MODULOS_CRIPTO = {"hashlib", "hmac", "bcrypt", "cryptography", "jwt", "Crypto"}


class PayloadInvalido(ValueError):
    pass


@dataclass
class Achado:
    regra: str
    arquivo: str
    linha: int
    descricao: str
    severidade: str = ""


def camada_de(caminho: str):
    partes = PurePosixPath(caminho).parts
    for parte in partes:
        if parte in CAMADA_POR_PASTA:
            return CAMADA_POR_PASTA[parte]
    if partes and PurePosixPath(caminho).stem == "models":
        return "dominio"
    return None


def resolver_import(caminho: str, no) -> list:
    """Resolve imports absolutos e relativos para nomes de módulo pontuados."""
    if isinstance(no, ast.Import):
        return [a.name for a in no.names]
    base = list(PurePosixPath(caminho).parent.parts)
    if no.level:
        base = base[: len(base) - (no.level - 1)] if no.level > 1 else base
        modulo = ".".join(base + ([no.module] if no.module else []))
    else:
        modulo = no.module or ""
    return [modulo] + [f"{modulo}.{a.name}" for a in no.names]


# ---------------- Facade (GoF estrutural) ----------------
class AnaliseEstruturalFacade:
    """Esconde parsing AST, resolução de camadas e regras de dependência."""

    def analisar_python(self, caminho: str, codigo: str) -> list:
        arvore = ast.parse(codigo)
        origem = camada_de(caminho)
        achados = []
        for no in ast.walk(arvore):
            if isinstance(no, (ast.Import, ast.ImportFrom)):
                for nome in resolver_import(caminho, no):
                    destino = camada_de(nome.replace(".", "/"))
                    raiz = nome.split(".")[0]
                    if origem and destino and destino != origem and destino not in DEPENDENCIAS_PERMITIDAS[origem]:
                        achados.append(Achado("R1-dependencia-entre-camadas", caminho, no.lineno,
                                              f"camada '{origem}' não pode depender de '{destino}' ({nome})"))
                        break
                    if raiz in MODULOS_CRIPTO and origem not in (None, "seguranca"):
                        achados.append(Achado("R3-cripto-fora-da-seguranca", caminho, no.lineno,
                                              f"primitiva criptográfica '{raiz}' usada fora da camada de segurança"))
                        break
            elif isinstance(no, ast.Constant) and isinstance(no.value, str) and origem not in (None, "persistencia"):
                if SQL.search(no.value):
                    achados.append(Achado("R2-sql-fora-da-persistencia", caminho, no.lineno,
                                          f"SQL embutido na camada '{origem}'"))
        return achados

    def analisar_sql(self, caminho: str, conteudo: str) -> list:
        if not PurePosixPath(caminho).parts or "migrations" not in PurePosixPath(caminho).parts:
            return [Achado("R4-ddl-fora-de-migracoes", caminho, 1, "script SQL fora do diretório migrations/")]
        return []

    def analisar_manifesto(self, caminho: str, conteudo: str) -> list:
        return [Achado("R5-banco-exposto", caminho, i, "porta de banco de dados exposta publicamente no manifesto")
                for i, linha in enumerate(conteudo.splitlines(), 1)
                if re.search(r"[\"']?(0\.0\.0\.0:)?(5432|3306|27017):(5432|3306|27017)", linha)]


# ---------------- Factory Method (GoF criação) ----------------
class Analisador(ABC):
    def __init__(self, fachada: AnaliseEstruturalFacade):
        self.fachada = fachada

    @abstractmethod
    def analisar(self, caminho: str, conteudo: str) -> list:
        ...


class AnalisadorPython(Analisador):
    def analisar(self, caminho, conteudo):
        try:
            return self.fachada.analisar_python(caminho, conteudo)
        except SyntaxError as e:
            return [Achado("R0-arquivo-invalido", caminho, e.lineno or 1, "arquivo Python com sintaxe inválida")]


class AnalisadorSQL(Analisador):
    def analisar(self, caminho, conteudo):
        return self.fachada.analisar_sql(caminho, conteudo)


class AnalisadorManifesto(Analisador):
    def analisar(self, caminho, conteudo):
        return self.fachada.analisar_manifesto(caminho, conteudo)


class FabricaAnalisadores:
    def __init__(self):
        self.fachada = AnaliseEstruturalFacade()

    def criar(self, caminho: str):
        sufixo = PurePosixPath(caminho).suffix.lower()
        if sufixo == ".py":
            return AnalisadorPython(self.fachada)
        if sufixo == ".sql":
            return AnalisadorSQL(self.fachada)
        if sufixo in (".yml", ".yaml"):
            return AnalisadorManifesto(self.fachada)
        return None


# ---------------- Strategy (GoF comportamental) ----------------
class EstrategiaValidacao(ABC):
    nome = ""

    @abstractmethod
    def aplicar(self, achados: list) -> str:
        ...


class EstrategiaRegras(EstrategiaValidacao):
    nome = "regras"

    def aplicar(self, achados):
        for a in achados:
            a.severidade = "BLOQUEANTE"
        return "reprovado" if achados else "aprovado"


class EstrategiaOrientacao(EstrategiaValidacao):
    nome = "orientacao"

    def aplicar(self, achados):
        for a in achados:
            a.severidade = "AVISO"
        return "aprovado com avisos" if achados else "aprovado"


# ---------------- View ----------------
def view_markdown(pr: dict, status: str, achados: list, ignorados: list, estrategia: str) -> str:
    linhas = [f"## Relatório de Conformidade Arquitetural — PR #{pr.get('number', '?')}",
              f"**Estratégia:** {estrategia} · **Status:** {status} · **Achados:** {len(achados)}"]
    for a in achados:
        linhas.append(f"- **[{a.severidade}] {a.regra}** — `{a.arquivo}:{a.linha}`: {a.descricao}")
    if ignorados:
        linhas.append("_Arquivos ignorados (tipo não suportado): " + ", ".join(ignorados) + "_")
    if not achados:
        linhas.append("Nenhuma violação dos limites arquiteturais encontrada.")
    return "\n".join(linhas) + "\n"


# ---------------- Controller (GRASP) ----------------
class ArquitetoController:
    def __init__(self, estrategia: EstrategiaValidacao = None):
        self.estrategia = estrategia or EstrategiaRegras()
        self.fabrica = FabricaAnalisadores()

    def receber_evento(self, evento) -> dict:
        if not isinstance(evento, dict) or "pull_request" not in evento or not isinstance(evento.get("files"), list):
            raise PayloadInvalido("payload deve conter 'pull_request' e lista 'files'")
        achados, ignorados = [], []
        for arquivo in evento["files"]:
            if not isinstance(arquivo, dict) or "filename" not in arquivo:
                raise PayloadInvalido("item de 'files' sem 'filename'")
            if arquivo.get("status") == "removed":
                continue
            analisador = self.fabrica.criar(arquivo["filename"])
            if analisador is None:
                ignorados.append(arquivo["filename"])
                continue
            achados += analisador.analisar(arquivo["filename"], arquivo.get("content", ""))
        status = self.estrategia.aplicar(achados)
        return {"status": status, "achados": [asdict(a) for a in achados], "ignorados": ignorados,
                "relatorio_md": view_markdown(evento["pull_request"], status, achados, ignorados, self.estrategia.nome)}
