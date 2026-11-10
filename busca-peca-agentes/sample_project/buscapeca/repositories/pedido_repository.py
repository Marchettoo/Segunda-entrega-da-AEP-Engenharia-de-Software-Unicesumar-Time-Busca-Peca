from buscapeca.models import Pedido


class PedidoRepository:
    def __init__(self, conexao):
        self.conexao = conexao

    def salvar(self, pedido: Pedido, total: float) -> Pedido:
        cursor = self.conexao.execute(
            "INSERT INTO pedidos (comprador_id, status, total) VALUES (?, ?, ?)",
            (pedido.comprador_id, pedido.status, total),
        )
        pedido.id = cursor.lastrowid
        return pedido

    def atualizar_status(self, pedido_id: int, status: str) -> None:
        self.conexao.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))
