"""Filtro 5 — Validação: Chain of Responsibility (formato -> completude -> ABNT)."""
import re

SECOES_OBRIGATORIAS = ["## Visão geral", "## Módulos", "## Decisões de arquitetura", "## Referências"]
AUTOR = re.compile(r"^[A-ZÀ-Ý]{2,}[A-ZÀ-Ý'\- ]*(, [A-ZÀ-Ý]|\. )")
EDICAO_OK = re.compile(r"\b\d+\. ed\.")
EDICAO_QUALQUER = re.compile(r"\b(ed|edição)\b", re.IGNORECASE)
FIM_LIVRO = re.compile(r": [^:]+, \d{4}\.$")
FIM_ONLINE = re.compile(r"Disponível em: \S+\. Acesso em: \d{1,2} [a-z]{3}\. \d{4}\.$")


def referencia_abnt_valida(ref: str) -> bool:
    ref = ref.strip()
    if not AUTOR.match(ref):
        return False
    if EDICAO_QUALQUER.search(ref) and not EDICAO_OK.search(ref):
        return False
    if "Disponível em:" in ref:
        return bool(FIM_ONLINE.search(ref))
    return bool(FIM_LIVRO.search(ref))


class Validador:
    def __init__(self, proximo=None):
        self.proximo = proximo

    def validar(self, doc: str, inventario: dict, lacunas: list) -> list:
        lacunas.extend(self.verificar(doc, inventario))
        return self.proximo.validar(doc, inventario, lacunas) if self.proximo else lacunas

    def verificar(self, doc, inventario):
        raise NotImplementedError


class ValidadorFormato(Validador):
    def verificar(self, doc, inventario):
        erros = [] if doc.lstrip().startswith("# ") else [("formato", "documento sem título de nível 1")]
        return erros + [("formato", f"seção ausente: {s}") for s in SECOES_OBRIGATORIAS if s not in doc]


class ValidadorCompletude(Validador):
    def verificar(self, doc, inventario):
        return [("completude", f"módulo não documentado: {m['caminho']}")
                for m in inventario["modulos"] if m["caminho"] not in doc]


class ValidadorABNT(Validador):
    def verificar(self, doc, inventario):
        if "## Referências" not in doc:
            return []
        bloco = doc.split("## Referências", 1)[1].split("\n## ", 1)[0]
        refs = [l[2:] for l in bloco.splitlines() if l.startswith("- ")]
        return [("abnt", f"referência fora do padrão: {r[:60]}") for r in refs if not referencia_abnt_valida(r)]


def cadeia_padrao() -> Validador:
    return ValidadorFormato(ValidadorCompletude(ValidadorABNT()))
