"""Agente de Code Review (ContextReview) — pipeline Template Method, somente leitura."""
import ast
import hashlib
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path

from agents.common.llm import criar_provedor

SEVERIDADES = ["Extra High", "High", "Medium", "Low", "Advice"]
NOME_SEGREDO = re.compile(r"(password|passwd|senha|secret|segredo|token|api_?key|chave)", re.IGNORECASE)
CONSTANTE = re.compile(r"^[A-Z][A-Z0-9_]*$")
MOTIVOS = {
    "SEC-SQL-INJECTION": "concatenar dados em SQL permite que um atacante altere a consulta (injeção de SQL).",
    "SEC-SEGREDO-HARDCODED": "credenciais no código vazam pelo controle de versão.",
    "SEC-EVAL": "eval/exec executa código arbitrário vindo de dados.",
    "SEC-SHELL": "shell=True permite injeção de comandos no sistema operacional.",
    "SEC-HASH-FRACO": "MD5/SHA1 são inadequados para senhas e integridade.",
    "COR-EXCEPT-SILENCIOSO": "engolir exceções esconde falhas e dificulta o diagnóstico.",
    "COR-DEFAULT-MUTAVEL": "o valor padrão mutável é compartilhado entre chamadas e causa efeitos colaterais.",
    "COR-COMPARACAO-NONE": "compare com None usando 'is', pois '==' pode ser sobrescrito.",
    "QUA-PRINT": "use logging estruturado em vez de print em código de produção.",
}


@dataclass
class Achado:
    regra: str
    categoria: str
    severidade: str
    confianca: float
    arquivo: str
    linha: int
    evidencia: str
    refutacao: str = ""
    explicacao: str = ""


@dataclass
class Revisao:  # Model
    escopo: list = field(default_factory=list)
    convencoes: dict = field(default_factory=dict)
    achados: list = field(default_factory=list)
    refutados: list = field(default_factory=list)
    erros: list = field(default_factory=list)


def _nome_chamada(no):
    f = no.func
    if isinstance(f, ast.Attribute):
        base = f.value.id if isinstance(f.value, ast.Name) else ""
        return f"{base}.{f.attr}" if base else f.attr
    return f.id if isinstance(f, ast.Name) else ""


class Detector(ast.NodeVisitor):
    """Etapa 3 — análise: Correção | Segurança | Qualidade."""

    def __init__(self, arquivo, linhas):
        self.arquivo, self.linhas, self.candidatos = arquivo, linhas, []

    def _add(self, regra, categoria, severidade, confianca, no, extra=None):
        self.candidatos.append((Achado(regra, categoria, severidade, confianca, self.arquivo, no.lineno,
                                       self.linhas[no.lineno - 1].strip()), extra))

    def visit_Call(self, no):
        nome = _nome_chamada(no)
        if nome.endswith("execute") or nome.endswith("executemany"):
            if no.args and isinstance(no.args[0], ast.JoinedStr) and any(isinstance(v, ast.FormattedValue) for v in no.args[0].values):
                self._add("SEC-SQL-INJECTION", "Segurança", "Extra High", 0.95, no, no.args[0])
            elif no.args and isinstance(no.args[0], ast.BinOp) and isinstance(no.args[0].op, (ast.Add, ast.Mod)):
                self._add("SEC-SQL-INJECTION", "Segurança", "Extra High", 0.9, no, no.args[0])
        elif nome in ("eval", "exec"):
            self._add("SEC-EVAL", "Segurança", "High", 0.9, no)
        elif nome.startswith("subprocess.") and any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in no.keywords):
            self._add("SEC-SHELL", "Segurança", "High", 0.9, no)
        elif nome in ("hashlib.md5", "hashlib.sha1"):
            self._add("SEC-HASH-FRACO", "Segurança", "Medium", 0.8, no)
        elif nome == "print":
            self._add("QUA-PRINT", "Qualidade", "Advice", 0.6, no)
        self.generic_visit(no)

    def visit_Assign(self, no):
        if isinstance(no.value, ast.Constant) and isinstance(no.value.value, str) and len(no.value.value) >= 4:
            for alvo in no.targets:
                nome = alvo.id if isinstance(alvo, ast.Name) else getattr(alvo, "attr", "")
                if nome and NOME_SEGREDO.search(nome):
                    self._add("SEC-SEGREDO-HARDCODED", "Segurança", "High", 0.85, no)
        self.generic_visit(no)

    def visit_ExceptHandler(self, no):
        if no.type is None or (len(no.body) == 1 and isinstance(no.body[0], ast.Pass)):
            self._add("COR-EXCEPT-SILENCIOSO", "Correção", "Medium", 0.85, no)
        self.generic_visit(no)

    def visit_FunctionDef(self, no):
        for padrao in no.args.defaults + no.args.kw_defaults:
            if isinstance(padrao, (ast.List, ast.Dict, ast.Set)):
                self._add("COR-DEFAULT-MUTAVEL", "Correção", "Medium", 0.9, padrao)
        self.generic_visit(no)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Compare(self, no):
        if any(isinstance(op, (ast.Eq, ast.NotEq)) for op in no.ops) and \
                any(isinstance(c, ast.Constant) and c.value is None for c in [no.left, *no.comparators]):
            self._add("COR-COMPARACAO-NONE", "Correção", "Low", 0.9, no)
        self.generic_visit(no)


class PipelineRevisao:
    """Template Method: o esqueleto é fixo; detectores/refutadores podem variar por linguagem."""

    def __init__(self, llm=None):
        self.llm = llm or criar_provedor()

    def revisar(self, raiz, arquivos=None) -> dict:
        raiz = Path(raiz)
        hashes_antes = self._hashes(raiz)
        revisao = Revisao()
        self.compreender(raiz, revisao)
        self.definir_escopo(raiz, arquivos, revisao)
        for rel in revisao.escopo:
            candidatos = self.analisar(raiz, rel, revisao)
            self.evidenciar_e_refutar(rel, candidatos, revisao)
        self.classificar(revisao)
        relatorio = self.construir_relatorio(revisao)
        integro = hashes_antes == self._hashes(raiz)
        return {"achados": [asdict(a) for a in revisao.achados], "refutados": [asdict(a) for a in revisao.refutados],
                "erros": revisao.erros, "convencoes": revisao.convencoes, "somente_leitura_ok": integro,
                "relatorio_md": relatorio}

    @staticmethod
    def _hashes(raiz):
        return {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raiz.rglob("*")) if p.is_file()}

    def compreender(self, raiz, rev):
        extensoes = {}
        for p in raiz.rglob("*"):
            if p.is_file():
                extensoes[p.suffix or "(sem)"] = extensoes.get(p.suffix or "(sem)", 0) + 1
        rev.convencoes = {"linguagens": extensoes, "tem_testes": any(raiz.rglob("test_*.py")),
                          "pasta_testes": "tests" if (raiz / "tests").exists() else None}

    def definir_escopo(self, raiz, arquivos, rev):
        todos = sorted(p.relative_to(raiz).as_posix() for p in raiz.rglob("*.py"))
        rev.escopo = [a for a in todos if arquivos is None or a in arquivos]

    def analisar(self, raiz, rel, rev):
        codigo = (raiz / rel).read_text(encoding="utf-8")
        try:
            arvore = ast.parse(codigo)
        except SyntaxError as e:
            rev.erros.append(f"{rel}: sintaxe inválida (linha {e.lineno})")
            return []
        detector = Detector(rel, codigo.splitlines())
        detector.visit(arvore)
        return detector.candidatos

    def evidenciar_e_refutar(self, rel, candidatos, rev):
        """Etapa 4 — tenta refutar cada achado antes de registrá-lo."""
        eh_teste = rel.startswith("tests/") or "/tests/" in rel or Path(rel).name.startswith("test_")
        for achado, extra in candidatos:
            if "# nosec" in achado.evidencia:
                achado.refutacao = "supressão explícita '# nosec' revisada pelo autor"
                rev.refutados.append(achado)
                continue
            if achado.regra == "SEC-SQL-INJECTION" and isinstance(extra, ast.JoinedStr):
                valores = [v.value for v in extra.values if isinstance(v, ast.FormattedValue)]
                if all(isinstance(v, ast.Name) and CONSTANTE.match(v.id) for v in valores):
                    achado.refutacao = "interpolação usa apenas constantes do módulo (sem dado externo)"
                    rev.refutados.append(achado)
                    continue
            if eh_teste and achado.categoria in ("Segurança", "Qualidade"):
                achado.severidade, achado.confianca = "Advice", round(achado.confianca * 0.5, 2)
                achado.refutacao = "parcial: ocorre em código de teste, risco reduzido"
            achado.explicacao = self.llm.completar("explicacao_achado", {"motivo": MOTIVOS[achado.regra]})
            rev.achados.append(achado)

    def classificar(self, rev):
        rev.achados.sort(key=lambda a: (SEVERIDADES.index(a.severidade), -a.confianca, a.arquivo, a.linha))

    def construir_relatorio(self, rev):  # Builder/View
        linhas = ["# Relatório de Code Review (ContextReview)",
                  f"Arquivos no escopo: {len(rev.escopo)} · Achados: {len(rev.achados)} · Refutados: {len(rev.refutados)}"]
        for sev in SEVERIDADES:
            grupo = [a for a in rev.achados if a.severidade == sev]
            if grupo:
                linhas.append(f"\n## {sev} ({len(grupo)})")
                for a in grupo:
                    linhas.append(f"- **{a.regra}** ({a.categoria}, confiança {a.confianca:.2f}) — `{a.arquivo}:{a.linha}`\n"
                                  f"  - Evidência: `{a.evidencia}`\n  - {a.explicacao}"
                                  + (f"\n  - Refutação: {a.refutacao}" if a.refutacao else ""))
        if rev.refutados:
            linhas.append("\n## Hipóteses refutadas")
            linhas += [f"- {a.regra} em `{a.arquivo}:{a.linha}` — {a.refutacao}" for a in rev.refutados]
        if rev.erros:
            linhas.append("\n## Arquivos não analisados")
            linhas += [f"- {e}" for e in rev.erros]
        return "\n".join(linhas) + "\n"


if __name__ == "__main__":
    import sys
    print(PipelineRevisao().revisar(sys.argv[1])["relatorio_md"])
