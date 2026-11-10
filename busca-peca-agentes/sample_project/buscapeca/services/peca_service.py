"""Regras de negócio de anúncio e busca de peças (economia circular)."""
from typing import List

from buscapeca.models import CONDICOES_VALIDAS, Peca
from buscapeca.repositories.peca_repository import PecaRepository

FATOR_DEPRECIACAO = {"nova": 1.0, "excedente": 0.85, "usada": 0.6}


class PecaInvalidaError(ValueError):
    pass


class PecaService:
    def __init__(self, repositorio: PecaRepository):
        self.repositorio = repositorio

    def cadastrar_peca(self, peca: Peca) -> Peca:
        """Valida e persiste uma nova peça anunciada."""
        if not peca.nome.strip():
            raise PecaInvalidaError("nome obrigatório")
        if peca.condicao not in CONDICOES_VALIDAS:
            raise PecaInvalidaError("condição inválida")
        if peca.preco <= 0 or peca.quantidade < 0:
            raise PecaInvalidaError("preço ou quantidade inválidos")
        return self.repositorio.salvar(peca)

    def preco_sugerido(self, preco_novo: float, condicao: str) -> float:
        if condicao not in FATOR_DEPRECIACAO:
            raise PecaInvalidaError("condição inválida")
        return round(preco_novo * FATOR_DEPRECIACAO[condicao], 2)

    def buscar_disponiveis(self, categoria: str) -> List[Peca]:
        return [p for p in self.repositorio.buscar_por_categoria(categoria) if p.quantidade > 0]

    def pecas_reaproveitaveis(self) -> List[Peca]:
        """Lista excedentes de estoque disponíveis para reaproveitamento (ODS 12)."""
        return [p for p in self.repositorio.listar_excedentes() if p.quantidade > 0]
