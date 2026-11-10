from buscapeca.services.pedido_service import EstoqueInsuficienteError, PedidoService


class PedidoController:
    def __init__(self, servico: PedidoService):
        self.servico = servico

    def post_pedido(self, corpo: dict) -> dict:
        try:
            itens = [(i["peca_id"], i["quantidade"]) for i in corpo["itens"]]
            pedido = self.servico.criar_pedido(corpo["comprador_id"], itens)
            return {"status": 201, "id": pedido.id}
        except (EstoqueInsuficienteError, KeyError) as erro:
            return {"status": 409, "erro": str(erro)}
