"""Entidades de domínio do marketplace Busca Peça."""
from dataclasses import dataclass, field
from typing import List, Optional

CONDICOES_VALIDAS = ("nova", "usada", "excedente")


@dataclass
class Peca:
    """Peça automotiva anunciada por uma oficina parceira."""
    nome: str
    categoria: str
    condicao: str
    preco: float
    quantidade: int
    oficina_id: int
    id: Optional[int] = None


@dataclass
class ItemPedido:
    peca_id: int
    quantidade: int
    preco_unitario: float

    def subtotal(self) -> float:
        return round(self.quantidade * self.preco_unitario, 2)


@dataclass
class Pedido:
    comprador_id: int
    itens: List[ItemPedido] = field(default_factory=list)
    status: str = "aberto"
    id: Optional[int] = None
