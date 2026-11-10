from buscapeca.models import ItemPedido, Pedido
from buscapeca.repositories.peca_repository import PecaRepository
from buscapeca.repositories.pedido_repository import PedidoRepository

FRETE_FIXO = 15.0
LIMITE_FRETE_GRATIS = 300.0


class EstoqueInsuficienteError(Exception):
    pass


class PedidoService:
    def __init__(self, pecas: PecaRepository, pedidos: PedidoRepository):
        self.pecas = pecas
        self.pedidos = pedidos

    def calcular_total(self, pedido: Pedido) -> float:
        subtotal = sum(item.subtotal() for item in pedido.itens)
        frete = 0.0 if subtotal >= LIMITE_FRETE_GRATIS else FRETE_FIXO
        return round(subtotal + frete, 2)

    def criar_pedido(self, comprador_id: int, itens: list) -> Pedido:
        pedido = Pedido(comprador_id=comprador_id)
        for peca_id, quantidade in itens:
            peca = self.pecas.buscar_por_id(peca_id)
            if peca is None or peca.quantidade < quantidade:
                raise EstoqueInsuficienteError(f"peça {peca_id} sem estoque")
            pedido.itens.append(ItemPedido(peca_id, quantidade, peca.preco))
            self.pecas.atualizar_quantidade(peca_id, peca.quantidade - quantidade)
        return self.pedidos.salvar(pedido, self.calcular_total(pedido))

    def cancelar(self, pedido: Pedido) -> Pedido:
        if pedido.status == "entregue":
            raise ValueError("pedido entregue não pode ser cancelado")
        pedido.status = "cancelado"
        self.pedidos.atualizar_status(pedido.id, pedido.status)
        return pedido
